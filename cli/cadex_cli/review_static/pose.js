// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The Pose editor (ADR-969; docs/DASHBOARD.md §29): move the model by its joints, through their
// ranges, to see what poses it can reach. Posing is view state, like the camera: it never writes
// the script, and Rest puts the model back where it was built (ADR-537).
//
//   Joints     one row per hinge and slide of the model's MJCF export, in the export's order: a
//              slider over the joint's range (±180° or ±100 mm where it has none), its value, its
//              stops and what moves it: a motor, nothing (passive), another joint (a coupling,
//              <equality><joint>), or the linkage it closes (<equality><connect>).
//   Walk       the page walks the joint tree itself (`collision.kinematics`, review_server.py
//              mjcf_kinematics), each body by its frame and its joints as MuJoCo does; each root
//              stays where the model rests. A coupled joint follows its driver by the coupling's
//              polynomial; a closed loop is closed again by moving its passive joints (damped
//              least squares over the loop's gap), and the status says the gap when it cannot.
//   Sweep      the picked joint swings between its stops, so its range is seen moving.
//   Mirror     a joint on one side moves its partner on the other (`_l`/`_r`, `fl`/`fr`, …), the
//              same way when their axes are mirror images, the other way when they are opposed.
//   Saved      the poses `cadex pose save` stored (`/api/project`'s `poses`), applied by name.
//   Copy, Download  the pose as a `cadex-pose-v1` JSON for `cadex pose save`: the page hands it
//              over and the CLI stores it, since the dashboard writes nothing.
(function () {
  'use strict';

  var DEG = 180 / Math.PI;
  var SWEEP_S = 3;
  var LOOP_TOLERANCE_MM = 0.05, LOOP_REPORT_MM = 0.5;

  // -- rigid transforms in mm and xyzw ----------------------------------------------------------
  function qmul(a, b) {
    return [a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1],
            a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0],
            a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3],
            a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2]];
  }
  function qrot(q, v) {
    var t = qmul(qmul(q, [v[0], v[1], v[2], 0]), [-q[0], -q[1], -q[2], q[3]]);
    return [t[0], t[1], t[2]];
  }
  function qaxis(axis, angle) {
    var s = Math.sin(angle / 2);
    return [axis[0] * s, axis[1] * s, axis[2] * s, Math.cos(angle / 2)];
  }
  var IDENTITY = { p: [0, 0, 0], q: [0, 0, 0, 1] };
  function compose(a, b) { var r = qrot(a.q, b.p); return { p: [a.p[0] + r[0], a.p[1] + r[1], a.p[2] + r[2]], q: qmul(a.q, b.q) }; }
  function inverse(a) { var q = [-a.q[0], -a.q[1], -a.q[2], a.q[3]], p = qrot(q, a.p); return { p: [-p[0], -p[1], -p[2]], q: q }; }
  function apply(a, v) { var r = qrot(a.q, v); return [a.p[0] + r[0], a.p[1] + r[1], a.p[2] + r[2]]; }

  // -- the joint tree ---------------------------------------------------------------------------
  // A tree built once per model: bodies parent-first, each with its joints; the movable joints;
  // the couplings in an order that resolves chains; the loops with their passive joints.
  function buildTree(k) {
    var bodies = k.bodies.map(function (b) { return { name: b.name, parent: b.parent, local: { p: b.pos_mm, q: b.rotation_xyzw }, joints: [] }; });
    var byBody = {}; bodies.forEach(function (b) { byBody[b.name] = b; });
    var joints = [], byName = {};
    k.joints.forEach(function (j) {
      var joint = { name: j.name, body: j.body, type: j.type, axis: j.axis, anchor: j.pos_mm, range: j.range, ref: j.ref || 0,
                    actuated: !!j.actuated, rest: typeof j.rest === 'number' ? j.rest : (j.ref || 0) };
      if (byBody[j.body]) byBody[j.body].joints.push(joint);
      byName[j.name] = joint;
      if (j.type === 'hinge' || j.type === 'slide') joints.push(joint);
    });
    bodies.forEach(function (b) { b.root = b.parent && byBody[b.parent] ? byBody[b.parent].root : b.name; });
    var couplings = (k.couplings || []).filter(function (c) { return byName[c.joint] && byName[c.driver]; });
    couplings.forEach(function (c) { byName[c.joint].follows = c; });
    // Each loop's passive joints: those on the two bodies' paths up to where they meet.
    function chain(name) { var out = []; for (var b = byBody[name]; b; b = byBody[b.parent]) out.push(b.name); return out; }
    var loops = (k.loops || []).filter(function (l) { return byBody[l.body1] && byBody[l.body2]; }).map(function (l) {
      var up1 = chain(l.body1), up2 = chain(l.body2), meet = up1.filter(function (n) { return up2.indexOf(n) >= 0; })[0];
      var path = up1.slice(0, up1.indexOf(meet) < 0 ? up1.length : up1.indexOf(meet))
        .concat(up2.slice(0, up2.indexOf(meet) < 0 ? up2.length : up2.indexOf(meet)));
      var free = [];
      path.forEach(function (n) { byBody[n].joints.forEach(function (j) { if ((j.type === 'hinge' || j.type === 'slide') && !j.actuated && !j.follows) free.push(j); }); });
      free.forEach(function (j) { j.linkage = l.name || (l.body1 + '–' + l.body2); });
      return { name: l.name, body1: l.body1, body2: l.body2, point1: l.point1_mm, point2: l.point2_mm, free: free };
    });
    var segments = {};
    bodies.forEach(function (b) { segments[b.name] = [b.name]; });
    // A body's welded children (no joint of their own) move with it, and are lit with it.
    bodies.slice().reverse().forEach(function (b) {
      if (b.parent && byBody[b.parent] && !b.joints.length) segments[b.parent] = segments[b.parent].concat(segments[b.name]);
    });
    return { bodies: bodies, byBody: byBody, joints: joints, byName: byName, couplings: couplings, loops: loops, segments: segments };
  }

  // Every body's frame for the joint values q (by name), in the export's world.
  function walk(tree, q) {
    var out = {};
    tree.bodies.forEach(function (b) {
      var w = b.parent && out[b.parent] ? compose(out[b.parent], b.local) : b.local;
      b.joints.forEach(function (j) {
        var v = (j.name in q ? q[j.name] : j.rest) - j.ref;
        if (j.type === 'hinge') {
          w = compose(compose(compose(w, { p: j.anchor, q: IDENTITY.q }), { p: [0, 0, 0], q: qaxis(j.axis, v) }),
                      { p: [-j.anchor[0], -j.anchor[1], -j.anchor[2]], q: IDENTITY.q });
        } else if (j.type === 'slide') {
          w = compose(w, { p: [j.axis[0] * v * 1000, j.axis[1] * v * 1000, j.axis[2] * v * 1000], q: IDENTITY.q });
        }
      });
      out[b.name] = w;
    });
    return out;
  }

  function clampTo(j, v) { return j.range ? Math.max(j.range[0], Math.min(j.range[1], v)) : v; }
  // A coupled joint's value from its driver's: MuJoCo's y - y0 = Σ cᵢ (x - x0)ⁱ.
  function couple(tree, q) {
    for (var pass = 0; pass <= tree.couplings.length; pass += 1) {
      var moved = false;
      tree.couplings.forEach(function (c) {
        var y = tree.byName[c.joint], x = tree.byName[c.driver], d = (q[c.driver] - x.ref), v = y.ref, power = 1;
        c.polycoef.forEach(function (a) { v += a * power; power *= d; });
        if (Math.abs((q[c.joint] || 0) - v) > 1e-12) { q[c.joint] = v; moved = true; }
      });
      if (!moved) break;
    }
  }
  function gaps(tree, q) {
    var frames = walk(tree, q), r = [];
    tree.loops.forEach(function (l) {
      var a = apply(frames[l.body1], l.point1), b = apply(frames[l.body2], l.point2);
      r.push(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
    });
    return r;
  }
  function norm(r) { return Math.sqrt(r.reduce(function (s, v) { return s + v * v; }, 0)); }
  // Close every loop by its passive joints: damped least squares on the gap, the Jacobian taken
  // numerically, each step held inside the joints' stops. Returns the gap left, mm.
  function closeLoops(tree, q) {
    var free = [];
    tree.loops.forEach(function (l) { l.free.forEach(function (j) { if (free.indexOf(j) < 0) free.push(j); }); });
    if (!tree.loops.length) return 0;
    var r = gaps(tree, q), lambda = 1e-2;
    for (var it = 0; it < 40 && free.length && norm(r) > LOOP_TOLERANCE_MM; it += 1) {
      var n = free.length, J = [];
      free.forEach(function (j) {
        var h = j.type === 'slide' ? 1e-6 : 1e-5, keep = q[j.name];
        q[j.name] = keep + h; var r2 = gaps(tree, q); q[j.name] = keep;
        J.push(r2.map(function (v, i) { return (v - r[i]) / h; }));
      });
      // (JᵀJ + λ·diag) dx = -Jᵀr, by Gaussian elimination: n is a handful.
      var A = [], g = [];
      for (var a = 0; a < n; a += 1) {
        A.push([]);
        for (var b = 0; b < n; b += 1) A[a].push(J[a].reduce(function (s, v, i) { return s + v * J[b][i]; }, 0));
        A[a][a] += lambda * (A[a][a] || 1);
        g.push(-J[a].reduce(function (s, v, i) { return s + v * r[i]; }, 0));
      }
      var dx = solve(A, g);
      if (!dx) break;
      var before = free.map(function (j) { return q[j.name]; });
      free.forEach(function (j, i) { q[j.name] = clampTo(j, q[j.name] + dx[i]); });
      var r2 = gaps(tree, q);
      if (norm(r2) < norm(r)) { r = r2; lambda = Math.max(1e-6, lambda / 3); }
      else { free.forEach(function (j, i) { q[j.name] = before[i]; }); lambda *= 10; }
    }
    return norm(r);
  }
  function solve(A, b) {
    var n = b.length, M = A.map(function (row, i) { return row.concat([b[i]]); });
    for (var c = 0; c < n; c += 1) {
      var p = c;
      for (var r = c + 1; r < n; r += 1) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
      if (Math.abs(M[p][c]) < 1e-14) return null;
      var t = M[c]; M[c] = M[p]; M[p] = t;
      for (r = c + 1; r < n; r += 1) { var f = M[r][c] / M[c][c]; for (var k = c; k <= n; k += 1) M[r][k] -= f * M[c][k]; }
    }
    var x = new Array(n);
    for (var i = n - 1; i >= 0; i -= 1) { var s = M[i][n]; for (var j = i + 1; j < n; j += 1) s -= M[i][j] * x[j]; x[i] = s / M[i][i]; }
    return x;
  }

  // The joint on the other side: each `_`-separated token `l`/`r`, `left`/`right`, or a leg's
  // `fl`/`fr`, `hl`/`hr`, `rl`/`rr` swapped; null when no token says a side.
  var SIDES = { l: 'r', r: 'l', left: 'right', right: 'left' };
  function partnerName(name) {
    var swapped = false;
    var out = String(name).split('_').map(function (t) {
      if (SIDES[t]) { swapped = true; return SIDES[t]; }
      if (/^[fhr][lr]$/.test(t)) { swapped = true; return t[0] + SIDES[t[1]]; }
      return t;
    }).join('_');
    return swapped ? out : null;
  }

  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    if (text != null) node.textContent = text;
    return node;
  }
  function shortName(joint) { return String(joint || '').replace(/^j_/, '').replace(/_/g, ' '); }
  // A joint's value as shown, and back: degrees for a hinge, mm for a slide.
  function shown(j, v) { return j.type === 'slide' ? v * 1000 : v * DEG; }
  function stored(j, v) { return j.type === 'slide' ? v / 1000 : v / DEG; }
  function unit(j) { return j.type === 'slide' ? ' mm' : '°'; }
  function span(j) { return j.range || (j.type === 'slide' ? [-0.1, 0.1] : [-Math.PI, Math.PI]); }

  function create(opts) {
    var tree = null, q = {}, restFrames = null, anchors = {}, active = false, picked = null, sweep = null, mirror = false;
    var kinematics = null, identity = {}, rows = {}, saved = [], gapMm = 0, note = '';

    function status(text, state) { opts.status.textContent = text; opts.status.dataset.state = state || 'ready'; }
    function counts() {
      var motors = tree.joints.filter(function (j) { return j.actuated; }).length;
      return tree.joints.length + ' joints · ' + motors + ' motors' + (tree.couplings.length ? ' · ' + tree.couplings.length + ' couplings' : '')
        + (tree.loops.length ? ' · ' + tree.loops.length + ' linkages' : '');
    }
    function renderStatus() {
      if (!tree) return;
      var text = (active ? 'posing · ' : 'at rest · ') + counts();
      if (gapMm > LOOP_REPORT_MM) { status(text + ' · a linkage cannot close here: ' + gapMm.toFixed(1) + ' mm apart', 'warn'); return; }
      status(text + (note ? ' · ' + note : ''), note ? 'warn' : 'ready');
    }

    function setModel(manifest) {
      stopSweep(); active = false; picked = null; tree = null; q = {}; rows = {}; gapMm = 0; note = '';
      opts.joints.textContent = '';
      var collision = manifest && manifest.available ? manifest.collision : null;
      kinematics = collision && collision.kinematics;
      identity = collision && collision.available ? { source: collision.source, sha256: collision.sha256 } : {};
      setEnabled(false);
      if (!manifest || !manifest.available) { status('Load a model to pose it.', 'empty'); return; }
      if (!kinematics) { status('Nothing to pose: ' + ((collision && collision.reason) || 'this model carries no MJCF export') + '.', 'empty'); return; }
      if (!kinematics.available) { status('Nothing to pose: ' + kinematics.reason + '.', 'empty'); return; }
      tree = buildTree(kinematics);
      if (!tree.joints.length) { tree = null; status('Nothing to pose: the model has no hinge or slide joint.', 'empty'); return; }
      tree.joints.forEach(function (j) { q[j.name] = j.rest; });
      tree.loops.forEach(function (l) {
        if (l.point2) return;
        var frames = walk(tree, q);
        l.point2 = apply(inverse(frames[l.body2]), apply(frames[l.body1], l.point1));
      });
      restFrames = walk(tree, q);
      // Each root is held where the model rests: its rest placement over its rest frame.
      var rest = opts.rest(), worst = 0;
      anchors = {};
      tree.bodies.forEach(function (b) {
        if (!b.parent && rest[b.name]) anchors[b.name] = compose({ p: rest[b.name].position_mm, q: rest[b.name].rotation_xyzw }, inverse(restFrames[b.name]));
      });
      tree.bodies.forEach(function (b) {
        var at = rest[b.name], f = placed(b, restFrames);
        if (at && f) worst = Math.max(worst, Math.hypot(at.position_mm[0] - f.position_mm[0], at.position_mm[1] - f.position_mm[1], at.position_mm[2] - f.position_mm[2]));
      });
      if (worst > 1) note = 'the model shown rests ' + worst.toFixed(0) + ' mm from its export\'s rest; posed from the export';
      renderRows(); setEnabled(true); renderSaved(); renderStatus();
    }
    function placed(b, frames) {
      var a = anchors[b.root];
      if (!a) return null;
      var w = compose(a, frames[b.name]);
      return { position_mm: w.p, rotation_xyzw: w.q };
    }

    function renderRows() {
      opts.joints.textContent = '';
      tree.joints.forEach(function (j) {
        var range = span(j), row = el('div', { class: 'pose-joint', role: 'listitem', 'data-joint': j.name });
        var name = el('button', { type: 'button', class: 'pose-name', title: j.name + ': pick it (Sweep swings the picked joint)' }, shortName(j.name));
        var kind = el('span', { class: 'pose-kind' },
          j.follows ? 'follows ' + shortName(j.follows.driver) : j.linkage ? 'linkage' : j.actuated ? 'motor' : 'passive');
        var slider = el('input', { type: 'range', min: String(shown(j, range[0])), max: String(shown(j, range[1])), step: j.type === 'slide' ? '0.1' : '0.5',
                                   'aria-label': shortName(j.name) });
        var value = el('output', { class: 'pose-value' });
        var stops = el('span', { class: 'pose-stops' }, j.range ? shown(j, j.range[0]).toFixed(0) + ' … ' + shown(j, j.range[1]).toFixed(0) + unit(j) : 'no stops');
        if (j.follows || j.linkage) slider.disabled = true;
        name.addEventListener('click', function () { pick(picked === j.name ? null : j.name); });
        slider.addEventListener('input', function () { stopSweep(); set(j.name, stored(j, parseFloat(slider.value))); });
        row.append(name, kind, slider, value, stops);
        opts.joints.appendChild(row);
        rows[j.name] = { row: row, slider: slider, value: value };
      });
      renderValues();
    }
    function renderValues() {
      tree.joints.forEach(function (j) {
        var r = rows[j.name], v = q[j.name], s = shown(j, v);
        if (document.activeElement !== r.slider) r.slider.value = String(s);
        r.value.textContent = s.toFixed(1) + unit(j);
        var limit = j.range && (v <= j.range[0] + 1e-4 || v >= j.range[1] - 1e-4);
        r.row.dataset.stop = limit ? 'true' : 'false';
        r.row.dataset.picked = String(picked === j.name);
      });
    }
    function setEnabled(on) {
      [opts.on, opts.restButton, opts.sweep, opts.mirror, opts.saved, opts.copy, opts.download, opts.name].forEach(function (c) { if (c) c.disabled = !on; });
      opts.on.setAttribute('aria-pressed', String(active));
      opts.sweep.disabled = !on || !picked;
    }

    function draw() {
      couple(tree, q);
      gapMm = closeLoops(tree, q);
      couple(tree, q);
      var frames = walk(tree, q), poses = opts.rest(), out = {};
      Object.keys(poses).forEach(function (n) { out[n] = poses[n]; });
      tree.bodies.forEach(function (b) { var p = placed(b, frames); if (p) out[b.name] = p; });
      opts.viewer.setPoses(out);
      renderValues(); renderStatus();
    }
    function enter() {
      if (active || !tree) return;
      active = true; opts.on.setAttribute('aria-pressed', 'true'); opts.hold(true);
    }
    function leave() {
      if (!active) return;
      stopSweep(); active = false; opts.on.setAttribute('aria-pressed', 'false'); opts.hold(false); renderStatus();
    }
    function set(name, value) {
      if (!tree) return;
      var j = tree.byName[name];
      enter();
      q[name] = clampTo(j, value);
      if (mirror) {
        var other = partnerName(name), p = other && tree.byName[other];
        if (p && !p.follows && !p.linkage && p.type === j.type) {
          // Mirrored in Y: a hinge axis (x, y, z) goes to (-x, y, -z), a slide axis to (x, -y, z).
          var a = qrot(restFrames[j.body].q, j.axis), b = qrot(restFrames[p.body].q, p.axis);
          var m = j.type === 'hinge' ? [-a[0], a[1], -a[2]] : [a[0], -a[1], a[2]];
          var sign = m[0] * b[0] + m[1] * b[1] + m[2] * b[2] < 0 ? -1 : 1;
          q[other] = clampTo(p, p.ref + sign * (q[name] - j.ref));
        }
      }
      draw();
    }
    function toRest() {
      if (!tree) return;
      stopSweep();
      tree.joints.forEach(function (j) { q[j.name] = j.rest; });
      if (active) draw(); else renderValues();
      leave();
    }
    function pick(name) {
      picked = name;
      opts.sweep.disabled = !picked;
      if (!picked) stopSweep();
      var sel = picked ? tree.segments[tree.byName[picked].body] : opts.selection();
      opts.viewer.select(sel || []);
      renderValues();
    }

    function stopSweep() {
      if (sweep) cancelAnimationFrame(sweep.frame);
      sweep = null;
      if (opts.sweep) opts.sweep.setAttribute('aria-pressed', 'false');
    }
    function startSweep() {
      if (!picked || !tree) return;
      var j = tree.byName[picked], range = span(j), origin = performance.now();
      stopSweep();
      opts.sweep.setAttribute('aria-pressed', 'true');
      sweep = {};
      (function step(now) {
        var t = ((now - origin) / 1000) / SWEEP_S, f = 0.5 - 0.5 * Math.cos(2 * Math.PI * t);
        set(j.name, range[0] + (range[1] - range[0]) * f);
        if (sweep) sweep.frame = requestAnimationFrame(step);
      })(origin);
    }

    // -- saved poses, and handing a pose over ---------------------------------------------------
    function setSaved(list) {
      var next = JSON.stringify((list || []).map(function (p) { return [p.name, p.saved_at, p.error]; }));
      if (next === JSON.stringify(saved.map(function (p) { return [p.name, p.saved_at, p.error]; }))) return;
      saved = list || [];
      renderSaved();
    }
    function renderSaved() {
      var box = opts.saved;
      box.textContent = '';
      box.appendChild(el('option', { value: '' }, saved.length ? 'Saved poses (' + saved.length + ')' : 'No saved poses'));
      saved.forEach(function (p) {
        var o = el('option', { value: p.name }, p.name + (p.error ? ' (unreadable)' : ''));
        if (p.error) o.disabled = true;
        box.appendChild(o);
      });
      box.disabled = !tree || !saved.length;
    }
    function applySaved(name) {
      var pose = saved.filter(function (p) { return p.name === name; })[0];
      if (!pose || !tree) return null;
      stopSweep();
      var used = 0, missing = 0;
      Object.keys(pose.joints || {}).forEach(function (n) {
        if (tree.byName[n] && (tree.byName[n].type === 'hinge' || tree.byName[n].type === 'slide')) { q[n] = clampTo(tree.byName[n], pose.joints[n]); used += 1; }
        else missing += 1;
      });
      enter(); draw();
      if (opts.name) opts.name.value = pose.name;
      note = missing ? missing + ' of the pose\'s joints are not in this model' : '';
      renderStatus();
      return { used: used, missing: missing };
    }
    function pose() {
      var joints = {};
      (tree ? tree.joints : []).forEach(function (j) { joints[j.name] = Math.round(q[j.name] * 1e6) / 1e6; });
      var name = (opts.name && opts.name.value.trim()) || 'pose';
      var out = { schema: 'cadex-pose-v1', name: name, note: '', joints: joints, model: {} };
      if (identity.source) out.model.source = identity.source;
      if (identity.sha256) out.model.sha256 = identity.sha256;
      return out;
    }
    function text() { return JSON.stringify(pose(), null, 2) + '\n'; }
    function download() {
      var p = pose(), url = URL.createObjectURL(new Blob([text()], { type: 'application/json' }));
      var a = el('a', { href: url, download: p.name + '.json' });
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
      status('Downloaded ' + p.name + '.json. Store it with: cadex pose save ' + p.name + '.json --project <project>', 'ready');
    }
    function copy() {
      var p = pose();
      if (!navigator.clipboard || !window.isSecureContext) { download(); return Promise.resolve(false); }
      return navigator.clipboard.writeText(text()).then(function () {
        status('Copied ' + p.name + '. Store it with: cadex pose save - --project <project>, pasting it in (or ask your agent).', 'ready');
        return true;
      }, function () { download(); return false; });
    }

    opts.on.addEventListener('click', function () { if (active) toRest(); else if (tree) { enter(); draw(); } });
    opts.restButton.addEventListener('click', toRest);
    opts.sweep.addEventListener('click', function () { if (sweep) stopSweep(); else startSweep(); });
    opts.mirror.addEventListener('change', function () { mirror = opts.mirror.checked; });
    opts.saved.addEventListener('change', function () { if (opts.saved.value) applySaved(opts.saved.value); opts.saved.value = ''; });
    opts.copy.addEventListener('click', copy);
    opts.download.addEventListener('click', download);
    status('Load a model to pose it.', 'empty');
    setEnabled(false);

    return {
      setModel: setModel, setSaved: setSaved, leave: leave,
      active: function () { return active; },
      // For the page's tests and for an agent driving the browser.
      set: function (name, value) { if (tree && tree.byName[name]) set(name, value); return tree ? Object.assign({}, q) : null; },
      apply: applySaved, pose: pose, rest: toRest, pick: pick,
      state: function () {
        return { available: !!tree, active: active, picked: picked, sweeping: !!sweep, mirror: mirror, gap_mm: gapMm,
                 joints: tree ? tree.joints.map(function (j) { return { name: j.name, value: q[j.name], range: j.range, actuated: j.actuated,
                                                                        follows: j.follows ? j.follows.driver : null, linkage: j.linkage || null }; }) : [],
                 saved: saved.map(function (p) { return p.name; }) };
      }
    };
  }

  window.CadexPose = { create: create, partners: partnerName };
})();
