// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The Activations and Network editors (ADR-727, ADR-728; docs/DASHBOARD.md §27): what the motors
// and the policy's network are doing at the moment the 3D viewport's rollout is showing.
//
//   Activations  the motors, each view on its own switch:
//     Gauges     one per actuated joint: the needle is where the joint is, within its command
//                range; a dot is the command the rollout recorded and a ring the command the
//                network gives for this frame; the arc is the joint's effort against its rating.
//     Bars       the same, one row per motor laid sideways, for a long list read at a glance.
//     Drivers    which inputs drive the picked motor most (input × gradient).
//   Network      the policy, each view on its own switch:
//     Layers     every layer, inputs to motor commands, each neuron a cell in the heat colours;
//                the picked motor's strongest last-layer contributions drawn to its output.
//     Paths      the picked motor's strongest paths back through the layers to the inputs: a few
//                neurons a layer, sized by how much they move its command, joined by what flows
//                between them.
//   Hovering a neuron in either shows what silencing it would do to each motor.
//   Viewport     each 3D viewport's own Activations switch (ADR-770; this editor's "Show in
//                viewport" until then) paints each motor's housing and the parts it moves in the
//                heat colours (review_scene.js setHeat); hovering a neuron paints its influence instead.
//
// The colours are heat.js's, which the Settings editor picks. The network is the rollout's own
// policy (`api/policy/...`), run here on inputs rebuilt from the trace: joint positions,
// velocities and efforts as recorded, the IMU's orientation from its part's pose, its rate from
// the poses either side, the gait clock from the time. The trace is kept at 25 fps and the
// policy runs faster behind a slew limit, so this is a reconstruction: the status line says how
// well the rebuilt commands match the recorded ones. Writes nothing.
(function () {
  'use strict';

  var SVG = 'http://www.w3.org/2000/svg';
  var DEG = 180 / Math.PI;
  var heat = window.CadexHeat;
  // The curve that takes a load onto the heat colours: 1 - e^(-k·u) with u = |effort| / rated, so
  // the rating lands at 0.8 and the peak saturates rather than clipping.
  var CURVE = -Math.log(1 - 0.8);
  // How quickly the viewport's heat follows a change, seconds: it rises and falls along this
  // curve rather than flickering frame to frame.
  var EASE_S = 0.12;
  var KEY = 'cadex.activations.views';

  function curve(u) { return 1 - Math.exp(-CURVE * Math.max(0, u)); }
  function rampHex(t) { return heat.hex(t); }
  function rampCss(t) { return heat.css(t); }
  function withAlpha(hex, a) {
    var n = parseInt(hex.slice(1), 16);
    return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a.toFixed(2) + ')';
  }
  function el(tag, attrs, ns) {
    var node = ns ? document.createElementNS(SVG, tag) : document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    return node;
  }
  function shortName(joint) { return String(joint || '').replace(/^j_/, '').replace(/_/g, ' '); }
  function shown(node) { return !!(node && node.isConnected && node.offsetParent); }


  // -- the network ---------------------------------------------------------------------------
  function decode(b64) {
    var raw = atob(b64), bytes = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
    return new Float32Array(bytes.buffer);
  }
  function Network(policy) {
    var w = decode(policy.weights), cursor = 0, net = policy.network;
    this.layers = net.layers.map(function (shape) {
      var n = shape[0], m = shape[1], W = w.subarray(cursor, cursor + n * m); cursor += n * m;
      var b = w.subarray(cursor, cursor + m); cursor += m;
      return { n: n, m: m, W: W, b: b };
    });
    this.activation = net.activation;
    this.scale = net.output_scale; this.bias = net.output_bias;
    this.mean = policy.normaliser.mean; this.std = policy.normaliser.std;
  }
  Network.prototype.act = function (x) {
    if (this.activation === 'swish') return x / (1 + Math.exp(-x));
    if (this.activation === 'tanh') return Math.tanh(x);
    return x > 0 ? x : 0;
  };
  Network.prototype.dact = function (x) {
    if (this.activation === 'swish') { var s = 1 / (1 + Math.exp(-x)); return s * (1 + x * (1 - s)); }
    if (this.activation === 'tanh') { var t = Math.tanh(x); return 1 - t * t; }
    return x > 0 ? 1 : 0;
  };
  // Every layer's pre-activations and activations from layer `from` on, `start` being that
  // layer's input: the inputs normalised for from = 0.
  Network.prototype.run = function (start, from) {
    var pre = [], post = [], a = start, last = this.layers.length - 1;
    for (var l = from; l <= last; l++) {
      var L = this.layers[l], z = new Float32Array(L.m);
      for (var j = 0; j < L.m; j++) z[j] = L.b[j];
      for (var i = 0; i < L.n; i++) {
        var ai = a[i]; if (!ai) continue;
        var row = i * L.m;
        for (var k = 0; k < L.m; k++) z[k] += ai * L.W[row + k];
      }
      var out = new Float32Array(L.m);
      for (var q = 0; q < L.m; q++) out[q] = l < last ? this.act(z[q]) : Math.tanh(z[q]);
      pre.push(z); post.push(out); a = out;
    }
    return { pre: pre, post: post };
  };
  Network.prototype.forward = function (x) {
    var input = new Float32Array(x.length);
    for (var i = 0; i < x.length; i++) input[i] = (x[i] - this.mean[i]) / (this.std[i] || 1);
    var r = this.run(input, 0);
    return { input: input, pre: r.pre, post: r.post, command: this.command(r.post[r.post.length - 1]) };
  };
  Network.prototype.command = function (tanhOut) {
    var self = this;
    return Array.prototype.map.call(tanhOut, function (v, m) { return v * self.scale[m] + self.bias[m]; });
  };
  // d command_m by backpropagation through the frame's pre-activations: against the (normalised)
  // inputs, against each hidden layer's activations (post) and each layer's pre-activations (z).
  Network.prototype.gradients = function (frame, m) {
    var last = this.layers.length - 1, t = frame.post[last][m], post = [], z = [];
    var g = new Float32Array(this.layers[last].m); g[m] = (1 - t * t) * this.scale[m];
    for (var l = last; l >= 0; l--) {
      var L = this.layers[l], below = new Float32Array(L.n);
      if (l < last) { post[l] = Float32Array.from(g); for (var q = 0; q < L.m; q++) g[q] *= this.dact(frame.pre[l][q]); }
      z[l] = g;
      for (var i = 0; i < L.n; i++) {
        var s = 0, row = i * L.m;
        for (var k = 0; k < L.m; k++) s += L.W[row + k] * g[k];
        below[i] = s;
      }
      g = below;
    }
    return { input: g, post: post, z: z };
  };
  Network.prototype.gradient = function (frame, m) { return this.gradients(frame, m).input; };
  // Each motor's command with hidden neuron (layer l, index j) silenced, minus as it is.
  Network.prototype.ablate = function (frame, l, j) {
    var a = Float32Array.from(frame.post[l]); a[j] = 0;
    var r = this.run(a, l + 1), out = this.command(r.post[r.post.length - 1]);
    return out.map(function (v, m) { return v - frame.command[m]; });
  };

  // -- rebuilding the policy's inputs from a trace ---------------------------------------------
  function qmul(a, b) {
    return [a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3], a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2],
            a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1], a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0]];
  }
  function wxyz(p) { var r = p.rotation_xyzw; return [r[3], r[0], r[1], r[2]]; }
  function Inputs(policy, playback) {
    var index = {};
    (playback.channels || []).forEach(function (c, i) {
      index[c.joint || String(c.actuator).split('/')[0]] = i;
    });
    this.rows = policy.inputs.map(function (row) {
      var at = index[row.target];
      var ok = row.kind === 'clock' ? !!policy.clock
             : row.kind === 'component_orientation' || row.kind === 'component_angular_velocity' ? !!(playback.frames[0] || {})[row.target]
             : row.kind === 'position' ? at != null && !!playback.joints
             : row.kind === 'velocity' ? at != null && !!playback.velocities
             : row.kind === 'actuator_force' ? at != null && !!playback.efforts : false;
      return { channel: row.channel, kind: row.kind, target: row.target, unit: row.unit, index: row.index, at: at, rebuilt: ok };
    });
    this.missing = this.rows.filter(function (r) { return !r.rebuilt; }).map(function (r) { return r.channel; });
    this.policy = policy; this.playback = playback;
  }
  Inputs.prototype.at = function (k) {
    var p = this.playback, policy = this.policy, last = p.times_s.length - 1;
    return this.rows.map(function (r, i) {
      if (!r.rebuilt) return policy.normaliser.mean[i];
      if (r.kind === 'position') return p.joints[k][r.at];
      if (r.kind === 'velocity') return p.velocities[k][r.at];
      if (r.kind === 'actuator_force') return p.efforts[k][r.at];
      if (r.kind === 'clock') {
        var phase = 2 * Math.PI * p.times_s[k] / policy.clock.period_s;
        return r.index === 0 ? Math.sin(phase) : Math.cos(phase);
      }
      if (r.kind === 'component_orientation') {
        var q = wxyz(p.frames[k][r.target]); if (q[0] < 0) q = q.map(function (v) { return -v; });
        return q[r.index];
      }
      // The rate in the part's own frame, from its poses a frame either side.
      var a = Math.max(0, k - 1), b = Math.min(last, k + 1), dt = p.times_s[b] - p.times_s[a];
      var qa = wxyz(p.frames[a][r.target]), qb = wxyz(p.frames[b][r.target]);
      var d = qmul([qa[0], -qa[1], -qa[2], -qa[3]], qb); if (d[0] < 0) d = d.map(function (v) { return -v; });
      var rate = dt > 0 ? 2 * d[1 + r.index] / dt : 0;
      return /deg/.test(r.unit || '') ? rate * DEG : rate;
    });
  };

  function pearson(xs, ys) {
    var n = xs.length; if (n < 3) return null;
    var mx = 0, my = 0; for (var i = 0; i < n; i++) { mx += xs[i]; my += ys[i]; } mx /= n; my /= n;
    var sxy = 0, sx = 0, sy = 0;
    for (var j = 0; j < n; j++) { var a = xs[j] - mx, b = ys[j] - my; sxy += a * b; sx += a * a; sy += b * b; }
    return sx > 0 && sy > 0 ? sxy / Math.sqrt(sx * sy) : null;
  }

  // -- the editors -----------------------------------------------------------------------------
  // One core reads the rollout and its policy and runs the network once; any number of panels
  // (ADR-729) draw it: Activations panels the motors, Network panels the network. The picked
  // motor and a hovered neuron are the core's, so every panel shows the same moment the same
  // way; which views are on, and whether a panel paints the viewport, is each panel's own.
  var WARM = [255, 80, 100], COOL = [90, 130, 255];
  function sign(c, a) { var k = c > 0 ? WARM : COOL; return 'rgba(' + k[0] + ',' + k[1] + ',' + k[2] + ',' + a.toFixed(2) + ')'; }
  var DEFAULT_VIEWS = { gauges: true, bars: false, drivers: true, layers: true, paths: true };
  function keptViews() {
    var views = Object.assign({}, DEFAULT_VIEWS);
    try { var kept = JSON.parse(localStorage.getItem(KEY) || 'null'); if (kept) Object.keys(views).forEach(function (k) { if (typeof kept[k] === 'boolean') views[k] = kept[k]; }); } catch (_) { /* defaults */ }
    return views;
  }

  function create(o) {
    // The 3D viewports, each with whether it paints the heat: [{viewer, heat}] (ADR-770).
    var viewports = o.viewports || function () { return []; };
    var policyUrl = null, playback = null, policy = null, net = null, inputs = null;
    var frames = [], scales = [], match = [], motors = [], selected = 0, hover = null, frameAt = 0, blendAt = null;
    var eased = {}, easedAt = 0, ticket = 0, grads = null, panels = [], statusLine = { text: '', state: 'empty' };

    function say(text, state) {
      statusLine = { text: text, state: state || '' };
      panels.forEach(function (p) { if (p.status) { p.status.textContent = text; p.status.dataset.state = state || ''; if (p.kind === 'motors') p.status.hidden = !text; } });
    }
    function anyViewport() { return viewports().some(function (v) { return v.heat; }); }
    var viewportState = 'off';

    function setPlayback(served) {
      ticket++;
      playback = served && served.available ? served : null;
      var url = playback && playback.policy;
      motors = [];
      if (playback) {
        motors = (playback.channels || []).map(function (c) {
          return { name: shortName(c.joint || String(c.actuator).split('/')[0]), joint: c.joint || String(c.actuator),
                   low: Number(c.low), high: Number(c.high), rated: Number(c.effort_rated) || null, unit: c.joint_unit || c.unit || '' };
        });
      }
      panels.forEach(buildMotors);
      if (!playback) { reset('Play a rollout in the 3D viewport — a checkpoint or a run’s own — to see its motors and its network.'); return; }
      if (!url) { dropNetwork('This rollout has no policy file beside it, so only its motors are shown.'); setFrame(0, 0, 0); return; }
      if (url === policyUrl && policy) { attach(policy); return; }
      var mine = ticket; policyUrl = url; policy = null; net = null;
      say('loading the policy…', 'loading');
      fetch(url, { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (served) {
        if (mine !== ticket) return;
        if (!served.available) { dropNetwork('The policy could not be read: ' + served.reason); return; }
        attach(served);
      }).catch(function (e) { if (mine === ticket) dropNetwork('The policy could not be loaded: ' + e.message); });
    }
    function reset(text) {
      policyUrl = null; policy = null; net = null; frames = []; playback = null; grads = null;
      say(text, 'empty'); render(); paintViewport(true);
    }
    function dropNetwork(text) { policy = null; net = null; frames = []; grads = null; say(text, 'warn'); render(); }

    function attach(served) {
      policy = served; net = new Network(served); inputs = new Inputs(served, playback);
      // Every frame's pass now, once: a rollout is a few hundred frames and a pass well under a
      // millisecond, and the layers' scales and the match need them all.
      frames = playback.times_s.map(function (_, k) { return net.forward(inputs.at(k)); });
      // Each layer's scale is the 95th percentile of its |activation| over the rollout, so a
      // typical neuron reads and a rare spike saturates rather than dimming the rest.
      scales = net.layers.map(function (_, l) {
        var all = [];
        frames.forEach(function (f) { var a = f.post[l]; for (var i = 0; i < a.length; i += 3) all.push(Math.abs(a[i])); });
        all.sort(function (x, y) { return x - y; });
        return all[Math.floor(all.length * 0.95)] || 1;
      });
      // Frame k's inputs make the command frame k+1 records.
      match = served.actions.map(function (_, m) {
        var xs = [], ys = [];
        for (var k = 0; k + 1 < frames.length; k++) {
          var c = playback.commands[k + 1]; if (c && c[m] != null) { xs.push(frames[k].command[m]); ys.push(c[m]); }
        }
        return pearson(xs, ys);
      });
      var known = match.filter(function (r) { return r != null; });
      var mean = known.length ? known.reduce(function (a, b) { return a + b; }, 0) / known.length : null;
      panels.forEach(function (p) { if (p.kind === 'motors') p.body.dataset.match = mean == null ? '' : mean.toFixed(2); });
      var shape = [served.network.layers[0][0]].concat(served.network.layers.map(function (s) { return s[1]; })).join(' → ');
      say((served.label ? served.label + ' · ' : '') + shape + (mean == null ? '' : ' · rebuilt commands match the recorded ones at r ' + mean.toFixed(2))
          + (inputs.missing.length ? ' · not rebuilt: ' + inputs.missing.join(', ') : ''), 'ready');
      panels.forEach(titleGauges);
      setFrame(frameAt, frameAt, 0);
    }
    function titleGauges(p) {
      (p.gauges || []).forEach(function (g, m) { g.box.title = motors[m].joint + (match[m] == null ? '' : ' · rebuilt vs recorded r ' + match[m].toFixed(2)); });
    }

    // -- motors: gauges and bars -------------------------------------------------------------
    var R = 34, CX = 50, CY = 48, SWEEP = 270, START = 135;
    function polar(deg, r) { var a = deg * Math.PI / 180; return [CX + r * Math.cos(a), CY + r * Math.sin(a)]; }
    function arc(a0, a1, r) {
      if (a1 < a0) { var t = a0; a0 = a1; a1 = t; }
      var p = polar(a0, r), q = polar(a1, r);
      return 'M' + p[0].toFixed(2) + ' ' + p[1].toFixed(2) + 'A' + r + ' ' + r + ' 0 ' + (a1 - a0 > 180 ? 1 : 0) + ' 1 ' + q[0].toFixed(2) + ' ' + q[1].toFixed(2);
    }
    function buildMotors(p) {
      if (p.kind !== 'motors') return;
      p.gauges = []; p.motorsBox.textContent = ''; if (p.barsBox) p.barsBox.textContent = '';
      motors.forEach(function (mo, m) {
        var box = el('figure', { class: 'gauge', 'data-motor': String(m), 'data-joint': mo.joint });
        var svg = el('svg', { viewBox: '0 0 100 100', 'aria-hidden': 'true' }, true);
        var track = el('path', { class: 'gauge-track', d: arc(START, START + SWEEP, R) }, true);
        var load = el('path', { class: 'gauge-load' }, true);
        var needle = el('line', { class: 'gauge-needle', x1: CX, y1: CY }, true);
        var cmd = el('circle', { class: 'gauge-command', r: 3.2 }, true);
        var pred = el('circle', { class: 'gauge-network', r: 4.6 }, true);
        var value = el('text', { class: 'gauge-value', x: CX, y: 80, 'text-anchor': 'middle' }, true);
        var effort = el('text', { class: 'gauge-effort', x: CX, y: 96, 'text-anchor': 'middle' }, true);
        svg.appendChild(track); svg.appendChild(load); svg.appendChild(cmd); svg.appendChild(pred);
        svg.appendChild(needle); svg.appendChild(el('circle', { class: 'gauge-hub', cx: CX, cy: CY, r: 3 }, true));
        svg.appendChild(value); svg.appendChild(effort);
        var caption = el('figcaption'); caption.textContent = mo.name;
        box.appendChild(svg); box.appendChild(caption);
        box.addEventListener('click', function () { selected = m; render(); });
        p.motorsBox.appendChild(box);
        // The same motor laid sideways: its name, the range as a track filled from zero to the
        // joint, the recorded command a dot and the network's a ring, and the angle and load.
        var row = el('div', { class: 'mbar', 'data-motor': String(m) });
        var label = el('span', { class: 'mbar-name' }); label.textContent = mo.name;
        var barTrack = el('span', { class: 'mbar-track' }), fill = el('span', { class: 'mbar-fill' });
        var zeroTick = el('span', { class: 'mbar-zero' }), bcmd = el('span', { class: 'mbar-command' }), bnet = el('span', { class: 'mbar-network' });
        barTrack.appendChild(fill); barTrack.appendChild(zeroTick); barTrack.appendChild(bcmd); barTrack.appendChild(bnet);
        var readout = el('span', { class: 'mbar-value' });
        row.appendChild(label); row.appendChild(barTrack); row.appendChild(readout);
        row.addEventListener('click', function () { selected = m; render(); });
        if (p.barsBox) p.barsBox.appendChild(row);
        p.gauges.push({ box: box, load: load, needle: needle, cmd: cmd, pred: pred, value: value, effort: effort,
                        row: row, fill: fill, zero: zeroTick, bcmd: bcmd, bnet: bnet, readout: readout });
      });
      titleGauges(p);
    }
    function angleOf(g, v) {
      var span = g.high - g.low || 1, t = Math.max(-0.04, Math.min(1.04, (v - g.low) / span));
      return START + SWEEP * t;
    }
    function fraction(g, v) { var span = g.high - g.low || 1; return Math.max(0, Math.min(1, (v - g.low) / span)); }
    function lerp(rows, lo, hi, f, m) {
      var a = rows && rows[lo], b = rows && rows[hi];
      if (!a || a[m] == null) return null;
      return b && b[m] != null ? a[m] + (b[m] - a[m]) * f : a[m];
    }
    function loadOf(m) {
      var g = motors[m], e = blendAt && lerp(playback.efforts, blendAt.lo, blendAt.hi, blendAt.f, m);
      return e == null || !g.rated ? null : Math.abs(e) / g.rated;
    }
    // What a motor reads at this moment, for the gauges and the bars alike.
    function reading(m) {
      var g = motors[m], lo = blendAt.lo, hi = blendAt.hi, influence = hoverInfluence(), u = loadOf(m);
      return { q: lerp(playback.joints, lo, hi, blendAt.f, m), c: (playback.commands[hi] || playback.commands[lo] || [])[m],
               n: frames[lo] ? frames[lo].command[m] : null, u: u,
               heat: influence ? influence[m] : u == null ? null : curve(u),
               note: influence ? 'Δ ' + Math.round(hover.delta[m]) + '°' : u == null ? '' : Math.round(u * 100) + '% rated',
               deg: /deg/.test(g.unit) ? '°' : '' };
    }
    function paintGauges(p, readings) {
      p.gauges.forEach(function (g, m) {
        var r = readings[m], mo = motors[m];
        var zero = angleOf(mo, Math.max(mo.low, Math.min(mo.high, 0)));
        if (r.q != null) {
          var a = angleOf(mo, r.q), tip = polar(a, R - 6);
          g.needle.setAttribute('x2', tip[0].toFixed(2)); g.needle.setAttribute('y2', tip[1].toFixed(2));
          g.load.setAttribute('d', Math.abs(a - zero) > 0.5 ? arc(zero, a, R) : '');
          g.value.textContent = Math.round(r.q) + r.deg;
        }
        g.load.style.stroke = r.heat == null ? 'var(--ink-2)' : rampCss(r.heat);
        g.box.style.setProperty('--heat', r.heat == null ? 'transparent' : rampCss(r.heat));
        if (r.c != null) { var pc = polar(angleOf(mo, r.c), R); g.cmd.setAttribute('cx', pc[0].toFixed(2)); g.cmd.setAttribute('cy', pc[1].toFixed(2)); }
        g.cmd.style.display = r.c == null ? 'none' : '';
        if (r.n != null) { var pn = polar(angleOf(mo, r.n), R); g.pred.setAttribute('cx', pn[0].toFixed(2)); g.pred.setAttribute('cy', pn[1].toFixed(2)); }
        g.pred.style.display = r.n == null ? 'none' : '';
        g.effort.textContent = r.note;
        g.effort.style.fill = r.heat == null ? '' : rampCss(r.heat);
        g.box.dataset.selected = String(m === selected);
        g.box.dataset.over = String(r.u != null && r.u > 1);
      });
    }
    function paintBars(p, readings) {
      p.gauges.forEach(function (g, m) {
        var r = readings[m], mo = motors[m], z = fraction(mo, Math.max(mo.low, Math.min(mo.high, 0)));
        if (r.q != null) {
          var q = fraction(mo, r.q);
          g.fill.style.left = (100 * Math.min(z, q)).toFixed(2) + '%';
          g.fill.style.width = (100 * Math.abs(q - z)).toFixed(2) + '%';
        }
        g.zero.style.left = (100 * z).toFixed(2) + '%';
        g.fill.style.background = r.heat == null ? 'var(--ink-2)' : rampCss(r.heat);
        g.bcmd.style.left = r.c == null ? '' : (100 * fraction(mo, r.c)).toFixed(2) + '%';
        g.bcmd.hidden = r.c == null;
        g.bnet.style.left = r.n == null ? '' : (100 * fraction(mo, r.n)).toFixed(2) + '%';
        g.bnet.hidden = r.n == null;
        g.readout.textContent = (r.q == null ? '—' : Math.round(r.q) + r.deg) + (r.note ? ' · ' + r.note : '');
        g.readout.style.color = r.heat == null ? '' : rampCss(r.heat);
        g.row.dataset.selected = String(m === selected);
        g.row.dataset.over = String(r.u != null && r.u > 1);
      });
    }

    // -- the network: layers -----------------------------------------------------------------
    // Columns: inputs, each hidden layer folded into a block of cells, the motor commands.
    function columns() {
      if (!net) return [];
      var cols = [{ kind: 'input', n: net.layers[0].n }];
      net.layers.forEach(function (L, l) { cols.push({ kind: l < net.layers.length - 1 ? 'hidden' : 'output', n: L.m, layer: l }); });
      return cols;
    }
    function layout(width, height) {
      var cols = columns(), gap = 18, pad = 6, boxes = [];
      if (!cols.length) return boxes;
      // Thin columns for inputs and outputs, square-ish blocks for the hidden layers.
      var weights = cols.map(function (c) { return c.kind === 'hidden' ? Math.sqrt(c.n) / 4 : 1; });
      var total = weights.reduce(function (a, b) { return a + b; }, 0), usable = width - 2 * pad - gap * (cols.length - 1), x = pad;
      cols.forEach(function (c, i) {
        var w = usable * weights[i] / total, h = height - 2 * pad - 16;
        var across = c.kind === 'hidden' ? Math.max(1, Math.round(Math.sqrt(c.n * w / h))) : 1;
        var down = Math.ceil(c.n / across), cw = w / across, ch = h / down;
        boxes.push({ col: c, x: x, y: pad + 16, w: w, h: h, across: across, down: down, cw: cw, ch: ch });
        x += w + gap;
      });
      return boxes;
    }
    function cellCentre(b, i) { return [b.x + (i % b.across + 0.5) * b.cw, b.y + (Math.floor(i / b.across) + 0.5) * b.ch]; }
    function valuesOf(b, frame) { return b.col.kind === 'input' ? frame.input : frame.post[b.col.layer]; }
    function cellHeat(kind, layer, v) {
      if (kind === 'input') return Math.min(1, Math.abs(v) / 3);
      if (kind === 'output') return Math.abs(v);
      return Math.min(1, Math.abs(v) / scales[layer]);
    }
    function prepare(canvas) {
      var ctx = canvas.getContext('2d'), dpr = Math.min(2, window.devicePixelRatio || 1);
      var w = canvas.clientWidth || 300, h = canvas.clientHeight || 200;
      if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) { canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr); }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, w, h);
      ctx.font = '12px ' + (getComputedStyle(document.body).fontFamily || 'sans-serif'); ctx.textBaseline = 'top';
      return { ctx: ctx, w: w, h: h, ink2: getComputedStyle(document.documentElement).getPropertyValue('--ink-2').trim() || '#999' };
    }
    function drawLayers(p) {
      p.cellBoxes = [];
      if (!p.views.layers || !shown(p.layers)) return;
      var d = prepare(p.layers), ctx = d.ctx, frame = frames[frameAt];
      if (!net || !frame) return;
      var boxes = layout(d.w, d.h); p.cellBoxes = boxes;
      ctx.fillStyle = d.ink2;
      var names = { input: 'inputs ' + net.layers[0].n, output: 'motors ' + net.layers[net.layers.length - 1].m };
      // Each column's name over it, or just its width where the name would run into the next.
      boxes.forEach(function (b) {
        var name = b.col.kind === 'hidden' ? 'layer ' + (b.col.layer + 1) + ' · ' + b.col.n : names[b.col.kind];
        ctx.fillText(ctx.measureText(name).width > b.w + 14 ? String(b.col.n) : name, b.x, 0);
      });
      var outBox = boxes[boxes.length - 1], lastHidden = boxes[boxes.length - 2], attribution = selectedAttribution(frame);
      boxes.forEach(function (b) {
        var values = valuesOf(b, frame), gapPx = b.cw > 4 && b.ch > 4 ? 1 : 0;
        for (var i = 0; i < b.col.n; i++) {
          var c = cellCentre(b, i), t = cellHeat(b.col.kind, b.col.layer, values[i]);
          if (b.col.kind === 'input' && attribution) t = Math.min(1, Math.abs(attribution.inputs[i]) / attribution.inputMax);
          ctx.fillStyle = rampCss(t); ctx.globalAlpha = 0.18 + 0.82 * t;
          ctx.fillRect(c[0] - b.cw / 2 + gapPx / 2, c[1] - b.ch / 2 + gapPx / 2, Math.max(1, b.cw - gapPx), Math.max(1, b.ch - gapPx));
        }
        ctx.globalAlpha = 1;
      });
      // The picked motor: the last hidden layer's strongest contributions to it, as lines over the
      // cells, warm where a neuron pushes the command up and cool where it pulls it down.
      if (attribution && lastHidden) {
        var target = cellCentre(outBox, selected);
        attribution.top.slice().reverse().forEach(function (t) {
          var from = cellCentre(lastHidden, t.j), k = Math.abs(t.c) / attribution.max;
          ctx.strokeStyle = sign(t.c, 0.35 + 0.65 * k); ctx.lineWidth = 0.75 + 2.25 * k;
          ctx.beginPath(); ctx.moveTo(from[0] + lastHidden.cw / 2, from[1]);
          ctx.bezierCurveTo(from[0] + lastHidden.cw / 2 + 30, from[1], target[0] - outBox.cw / 2 - 30, target[1], target[0] - outBox.cw / 2, target[1]);
          ctx.stroke();
          ctx.strokeStyle = 'rgba(237,237,237,' + (0.4 + 0.6 * k).toFixed(2) + ')'; ctx.lineWidth = 1;
          ctx.strokeRect(from[0] - lastHidden.cw / 2 + .5, from[1] - lastHidden.ch / 2 + .5, lastHidden.cw - 1, lastHidden.ch - 1);
        });
      }
      var s = cellCentre(outBox, selected);
      ctx.strokeStyle = '#ededed'; ctx.lineWidth = 1.5; ctx.strokeRect(outBox.x + 0.75, s[1] - outBox.ch / 2 + 0.75, outBox.cw - 1.5, outBox.ch - 1.5);
      if (hover) { var hb = boxes[hover.layer + 1], hp = cellCentre(hb, hover.i); ctx.strokeStyle = '#ededed'; ctx.strokeRect(hp[0] - hb.cw / 2, hp[1] - hb.ch / 2, hb.cw, hb.ch); }
    }
    // The picked motor's gradients at this frame, computed once a render and shared.
    function gradsOf(frame) {
      if (!net || !frame || selected == null) return null;
      if (!grads || grads.frame !== frame || grads.m !== selected) grads = { frame: frame, m: selected, g: net.gradients(frame, selected) };
      return grads.g;
    }
    function selectedAttribution(frame) {
      var G = gradsOf(frame); if (!G) return null;
      var l = net.layers.length - 1, L = net.layers[l], a = frame.post[l - 1], c = [];
      for (var j = 0; j < L.n; j++) c.push({ j: j, c: a[j] * L.W[j * L.m + selected] });
      c.sort(function (x, y) { return Math.abs(y.c) - Math.abs(x.c); });
      var top = c.slice(0, 16), max = Math.abs(top[0] && top[0].c) || 1, inputs = [], inputMax = 0;
      for (var i = 0; i < G.input.length; i++) { inputs.push(G.input[i] * frame.input[i]); inputMax = Math.max(inputMax, Math.abs(inputs[i])); }
      return { top: top, max: max, inputs: inputs, inputMax: inputMax || 1 };
    }

    // -- the network: paths ------------------------------------------------------------------
    // For the picked motor, each column's few units that move its command most (activation ×
    // gradient: the inputs, then each hidden layer), largest first, joined by what flows between
    // them (the lower unit's activation × the weight × the upper unit's gradient), to the motor.
    var PER_COLUMN = 8;
    function paths(frame) {
      var G = gradsOf(frame); if (!G) return null;
      var last = net.layers.length - 1, cols = [];
      function pick(values, rel) {
        var all = []; for (var i = 0; i < rel.length; i++) all.push({ i: i, r: rel[i], v: values[i] });
        all.sort(function (x, y) { return Math.abs(y.r) - Math.abs(x.r); });
        return all.slice(0, PER_COLUMN);
      }
      var relIn = []; for (var i = 0; i < frame.input.length; i++) relIn.push(frame.input[i] * G.input[i]);
      cols.push({ kind: 'input', units: pick(frame.input, relIn) });
      for (var l = 0; l < last; l++) {
        var rel = []; for (var j = 0; j < frame.post[l].length; j++) rel.push(frame.post[l][j] * G.post[l][j]);
        cols.push({ kind: 'hidden', layer: l, units: pick(frame.post[l], rel) });
      }
      cols.push({ kind: 'output', units: [{ i: selected, r: 1, v: frame.post[last][selected] }] });
      // The flow between consecutive columns' units: column c feeds layer c's pre-activations.
      var links = [];
      for (var c = 0; c + 1 < cols.length; c++) {
        var L = net.layers[c], below = cols[c].units, above = cols[c + 1].units, gz = G.z[c], from = c === 0 ? frame.input : frame.post[c - 1], pair = [], max = 0;
        below.forEach(function (u) {
          above.forEach(function (v) { var f = from[u.i] * L.W[u.i * L.m + v.i] * gz[v.i]; pair.push({ a: u, b: v, f: f }); max = Math.max(max, Math.abs(f)); });
        });
        links.push({ pairs: pair, max: max || 1 });
      }
      return { cols: cols, links: links };
    }
    function drawPaths(p) {
      p.pathNodes = [];
      if (!p.views.paths || !shown(p.paths)) return;
      var d = prepare(p.paths), ctx = d.ctx, frame = frames[frameAt], P = net && frame ? paths(frame) : null;
      if (!P) return;
      var labelW = Math.min(150, Math.max.apply(null, P.cols[0].units.map(function (u) { return ctx.measureText(policy.observations[u.i] || '').width; })) + 12);
      var g = motors[selected], motor = (g ? g.name : 'motor ' + selected) + '  ' + Math.round(frame.command[selected]) + '°';
      var rightW = Math.min(160, ctx.measureText(motor).width + 16), top = 22, bottom = d.h - 8;
      var x0 = labelW + 10, x1 = d.w - rightW - 10, n = P.cols.length;
      var xs = P.cols.map(function (_, c) { return x0 + (x1 - x0) * c / (n - 1); });
      // Each unit's place, largest first from the top; the motor centred.
      P.cols.forEach(function (col, c) {
        var max = Math.max.apply(null, col.units.map(function (u) { return Math.abs(u.r); })) || 1;
        col.units.forEach(function (u, i) {
          u.x = xs[c]; u.y = col.kind === 'output' ? (top + bottom) / 2 : top + (bottom - top) * (i + 0.5) / PER_COLUMN;
          u.rad = col.kind === 'output' ? 10 : 3 + 7 * Math.sqrt(Math.abs(u.r) / max);
          u.share = Math.abs(u.r) / max;
        });
      });
      ctx.fillStyle = d.ink2;
      P.cols.forEach(function (col, c) {
        var name = col.kind === 'input' ? 'inputs' : col.kind === 'output' ? 'motor' : 'layer ' + (col.layer + 1);
        ctx.textAlign = 'center'; ctx.fillText(name, xs[c], 2);
      });
      // Links under the units, faint to strong; a link under a twentieth of its pair's largest is left out.
      P.links.forEach(function (L) {
        L.pairs.sort(function (x, y) { return Math.abs(x.f) - Math.abs(y.f); }).forEach(function (pr) {
          var k = Math.abs(pr.f) / L.max; if (k < 0.05) return;
          ctx.strokeStyle = sign(pr.f, 0.15 + 0.75 * k); ctx.lineWidth = 0.5 + 3.5 * k;
          var mx = (pr.a.x + pr.b.x) / 2;
          ctx.beginPath(); ctx.moveTo(pr.a.x, pr.a.y); ctx.bezierCurveTo(mx, pr.a.y, mx, pr.b.y, pr.b.x, pr.b.y); ctx.stroke();
        });
      });
      P.cols.forEach(function (col) {
        col.units.forEach(function (u) {
          var t = col.kind === 'input' ? u.share : cellHeat(col.kind, col.layer, u.v);
          ctx.beginPath(); ctx.arc(u.x, u.y, u.rad, 0, 2 * Math.PI);
          ctx.fillStyle = rampCss(t); ctx.fill();
          ctx.lineWidth = hover && col.kind === 'hidden' && hover.layer === col.layer && hover.i === u.i ? 2.5 : 1.25;
          ctx.strokeStyle = ctx.lineWidth > 2 ? '#ededed' : sign(u.r, 0.95); ctx.stroke();
          p.pathNodes.push({ x: u.x, y: u.y, r: Math.max(6, u.rad), kind: col.kind, layer: col.layer, i: u.i, v: u.v, rel: u.r });
        });
      });
      ctx.textBaseline = 'middle'; ctx.fillStyle = '#d6d6d6';
      ctx.textAlign = 'right';
      P.cols[0].units.forEach(function (u) { ctx.fillText(policy.observations[u.i] || ('input ' + u.i), u.x - u.rad - 6, u.y); });
      ctx.textAlign = 'left';
      var out = P.cols[n - 1].units[0]; ctx.fillText(motor, out.x + out.rad + 6, out.y);
      ctx.textAlign = 'start'; ctx.textBaseline = 'top';
    }

    function renderDetail(p) {
      p.detail.textContent = '';
      var frame = frames[frameAt];
      if (!p.views.drivers || !net || !frame || !motors[selected]) return;
      var g = motors[selected], att = selectedAttribution(frame);
      var head = el('p'); head.className = 'activations-pick';
      head.textContent = g.name + ': network ' + Math.round(frame.command[selected]) + '°' +
        (match[selected] == null ? '' : ' · rebuilt vs recorded r ' + match[selected].toFixed(2)) + ' · driven most by';
      p.detail.appendChild(head);
      var order = att.inputs.map(function (v, i) { return { i: i, v: v }; }).sort(function (x, y) { return Math.abs(y.v) - Math.abs(x.v); });
      var total = order.reduce(function (s, x) { return s + Math.abs(x.v); }, 0) || 1, list = el('ol');
      list.className = 'activations-drivers';
      order.slice(0, 6).forEach(function (x) {
        var li = el('li'), bar = el('span'), name = el('span'), share = el('span');
        name.textContent = policy.observations[x.i]; share.textContent = Math.round(100 * Math.abs(x.v) / total) + '%';
        bar.className = 'bar'; bar.style.width = (100 * Math.abs(x.v) / Math.abs(order[0].v || 1)).toFixed(1) + '%';
        bar.style.background = sign(x.v, 1);
        li.appendChild(name); li.appendChild(share); li.appendChild(bar); list.appendChild(li);
      });
      p.detail.appendChild(list);
    }

    // Hover: what silencing a hidden neuron would do to each motor, as heat on the gauges and parts.
    function setHover(layer, i) {
      var frame = frames[frameAt];
      if (!net || !frame) return null;
      var delta = net.ablate(frame, layer, i), span = motors.map(function (g) { return Math.abs(g.high - g.low) || 1; });
      hover = { layer: layer, i: i, delta: delta, heat: delta.map(function (d, m) { return Math.min(1, Math.abs(d) / span[m] * 4); }) };
      return delta;
    }
    function hoverTitle(layer, i) {
      return 'layer ' + (layer + 1) + ' neuron ' + i + ' · ' + frames[frameAt].post[layer][i].toFixed(2) + ' · silenced, it would move each motor by Δ';
    }
    function hoverInfluence() { return hover ? hover.heat : null; }

    // -- the viewport ----------------------------------------------------------------------
    function paintViewport(now) {
      var all = viewports().filter(function (v) { return v.viewer && v.viewer.setHeat; });
      var on = anyViewport() && playback && motors.length;
      if (!on) { all.forEach(function (v) { v.viewer.setHeat(null); }); viewportState = 'off'; return; }
      var parts = (policy && policy.parts) || {}, influence = hoverInfluence(), map = {};
      var t = performance.now() / 1000, k = now ? 1 : 1 - Math.exp(-(t - easedAt) / EASE_S); easedAt = t;
      motors.forEach(function (g, m) {
        var u = loadOf(m), target = influence ? influence[m] : u == null ? 0 : curve(u);
        var h = eased[m] == null || now ? target : eased[m] + (target - eased[m]) * k; eased[m] = h;
        var own = parts[g.joint] || {};
        (own.segment || []).forEach(function (name) { if (map[name] == null) map[name] = rampHex(h); });
        // A motor's housing shows its own joint, over the segment it rides on.
        (own.motor || []).forEach(function (name) { map[name] = rampHex(h); });
      });
      var painted = Object.keys(map).length ? map : null;
      viewportState = painted ? 'on' : 'unmapped';
      all.forEach(function (v) { v.viewer.setHeat(v.heat ? painted : null); });
    }

    function render() {
      var readings = playback && blendAt && motors.length ? motors.map(function (_, m) { return reading(m); }) : null;
      panels.forEach(function (p) {
        if (!shown(p.body)) return;
        if (p.kind === 'motors') {
          if (!readings) { p.detail.textContent = ''; return; }
          if (p.views.gauges) paintGauges(p, readings);
          if (p.views.bars) paintBars(p, readings);
          renderDetail(p);
        } else { drawLayers(p); drawPaths(p); }
      });
      if (readings) paintViewport(false);
    }
    // The 3D viewport's playback calls this on every seek: between frames lo and hi at f.
    function setFrame(lo, hi, f) {
      if (!playback) return;
      frameAt = lo; blendAt = { lo: lo, hi: hi, f: f };
      if (!panels.some(function (p) { return shown(p.body); })) { paintViewport(false); return; }
      render();
    }
    heat.onChange(function () { panels.forEach(paintRamp); render(); paintViewport(true); });
    function paintRamp(p) { if (p.ramp) p.ramp.style.background = heat.gradient(); }

    // -- panels ----------------------------------------------------------------------------
    // The views a panel shows, each a switch in its header; the first panel of a kind keeps its
    // choice in this browser, a copy starts from the first's.
    function wireViews(p, group, keep) {
      p.views = keep ? keptViews() : Object.assign({}, panels.filter(function (q) { return q.views; })[0] ? panels.filter(function (q) { return q.views; })[0].views : DEFAULT_VIEWS);
      function apply() {
        if (!group) return;
        group.querySelectorAll('button[data-view]').forEach(function (b) {
          b.setAttribute('aria-pressed', String(!!p.views[b.dataset.view]));
          p.body.dataset[b.dataset.view] = String(!!p.views[b.dataset.view]);
        });
      }
      if (group) group.addEventListener('click', function (e) {
        var b = e.target.closest('button[data-view]'); if (!b) return;
        p.views[b.dataset.view] = !p.views[b.dataset.view];
        if (keep) {
          try { var all = keptViews(); all[b.dataset.view] = p.views[b.dataset.view]; localStorage.setItem(KEY, JSON.stringify(all)); } catch (_) { /* this visit only */ }
        }
        apply(); render();
      });
      apply();
    }
    function observe(nodes) {
      if (!window.ResizeObserver) return;
      var ro = new ResizeObserver(function () { render(); });
      nodes.forEach(function (n) { if (n) ro.observe(n); });
    }
    function addMotors(e) {
      var p = { kind: 'motors', body: e.body, motorsBox: e.motors, barsBox: e.bars, detail: e.detail, status: e.status,
                ramp: e.ramp, gauges: [] };
      wireViews(p, e.views, !!e.keep);
      panels.push(p);
      paintRamp(p); buildMotors(p); say(statusLine.text, statusLine.state);
      if (net) p.body.dataset.match = panels[0].body.dataset.match || '';
      observe([p.body]);
      render();
      return p;
    }
    function addNetwork(e) {
      var p = { kind: 'network', body: e.network, status: e.networkStatus, layers: e.layers, paths: e.paths, cellBoxes: [], pathNodes: [] };
      wireViews(p, e.networkViews, !!e.keep);
      panels.push(p);
      say(statusLine.text, statusLine.state);
      // A view's corner button maximizes it over the editor, and restores it (ADR-770).
      var maxButtons = p.body.querySelectorAll('button[data-max]');
      function maximize(view) {
        p.body.dataset.max = view || '';
        maxButtons.forEach(function (b) {
          var on = b.dataset.max === view, label = (on ? 'Restore the ' : 'Maximize the ') + b.dataset.max;
          b.setAttribute('aria-pressed', String(on)); b.title = label; b.setAttribute('aria-label', label);
        });
        render();
      }
      maxButtons.forEach(function (b) {
        b.addEventListener('click', function () { maximize(p.body.dataset.max === b.dataset.max ? '' : b.dataset.max); });
      });
      p.maximize = maximize;
      if (p.layers) {
        p.layers.addEventListener('pointermove', function (ev) {
          var r = p.layers.getBoundingClientRect(), x = ev.clientX - r.left, y = ev.clientY - r.top, found = null;
          p.cellBoxes.forEach(function (b) {
            if (found || x < b.x || x > b.x + b.w || y < b.y || y > b.y + b.h) return;
            var i = Math.floor((y - b.y) / b.ch) * b.across + Math.floor((x - b.x) / b.cw);
            if (i >= 0 && i < b.col.n) found = { i: i, b: b };
          });
          var before = hover && hover.layer + ':' + hover.i;
          if (!found || found.b.col.kind !== 'hidden') {
            hover = null;
            p.layers.title = found ? (found.b.col.kind === 'input' ? policy.observations[found.i] : (motors[found.i] || {}).name || '') : '';
          } else { setHover(found.b.col.layer, found.i); p.layers.title = hoverTitle(found.b.col.layer, found.i); }
          if ((hover && hover.layer + ':' + hover.i) !== before) render();
        });
        p.layers.addEventListener('pointerleave', function () { if (hover) { hover = null; render(); } });
        // A press on a motor's output cell picks it, as its gauge does.
        p.layers.addEventListener('pointerdown', function (ev) {
          var r = p.layers.getBoundingClientRect(), x = ev.clientX - r.left, y = ev.clientY - r.top, b = p.cellBoxes[p.cellBoxes.length - 1];
          if (b && x >= b.x && x <= b.x + b.w && y >= b.y && y <= b.y + b.h) { selected = Math.min(b.col.n - 1, Math.floor((y - b.y) / b.ch)); render(); }
        });
      }
      if (p.paths) {
        p.paths.addEventListener('pointermove', function (ev) {
          var r = p.paths.getBoundingClientRect(), x = ev.clientX - r.left, y = ev.clientY - r.top, found = null;
          p.pathNodes.forEach(function (u) { if (!found && Math.hypot(x - u.x, y - u.y) <= u.r) found = u; });
          var before = hover && hover.layer + ':' + hover.i;
          if (found && found.kind === 'hidden') { setHover(found.layer, found.i); p.paths.title = hoverTitle(found.layer, found.i); }
          else { hover = null; p.paths.title = found && found.kind === 'input' ? policy.observations[found.i] + ' · ' + found.v.toFixed(2) : ''; }
          if ((hover && hover.layer + ':' + hover.i) !== before) render();
        });
        p.paths.addEventListener('pointerleave', function () { if (hover) { hover = null; render(); } });
      }
      observe([p.body, p.layers, p.paths]);
      render();
      return p;
    }
    // The first Activations and Network editors, from the page's own markup.
    var first = o.body ? addMotors({ body: o.body, motors: o.motors, bars: o.bars, detail: o.detail, status: o.status,
                                     views: o.views, ramp: o.ramp, keep: true }) : null;
    var firstNet = o.network ? addNetwork({ network: o.network, networkStatus: o.networkStatus, layers: o.layers, paths: o.paths,
                                            networkViews: o.networkViews, keep: true }) : null;

    return {
      setPlayback: setPlayback, setFrame: setFrame, addMotors: addMotors, addNetwork: addNetwork,
      // A viewport's Activations switch moved: paint again now, from the current loads.
      repaintViewports: function () { eased = {}; paintViewport(true); return viewportState; },
      viewportState: function () { return viewportState; },
      select: function (m) { selected = m; render(); return selected; },
      hoverNeuron: function (layer, i) { var d = setHover(layer, i); render(); return d; },
      clearHover: function () { hover = null; render(); },
      paths: function () { var f = frames[frameAt]; var P = net && f ? paths(f) : null; return P && P.cols.map(function (c) { return { kind: c.kind, layer: c.layer, units: c.units.map(function (u) { return u.i; }) }; }); },
      views: function () { return Object.assign({}, first ? first.views : DEFAULT_VIEWS, firstNet ? { layers: firstNet.views.layers, paths: firstNet.views.paths } : {}); },
      panels: function () { return panels.map(function (p) { return { kind: p.kind, views: Object.assign({}, p.views), maximized: p.kind === 'network' ? p.body.dataset.max || null : null }; }); },
      maximizeNetwork: function (view) { if (firstNet) firstNet.maximize(view || ''); return firstNet ? firstNet.body.dataset.max || null : null; },
      state: function () {
        return { policy: policyUrl, ready: !!net, frame: frameAt, selected: selected, motors: motors.length,
                 match: match.slice(), missing: inputs ? inputs.missing.slice() : [], viewport: anyViewport(),
                 command: frames[frameAt] ? frames[frameAt].command.slice() : null, views: this.views() };
      }
    };
  }

  window.CadexActivations = { create: create, ramp: rampCss, curve: curve };
})();
