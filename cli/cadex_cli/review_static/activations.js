// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The Activations editor (ADR-721; docs/DASHBOARD.md §27): what the motors and the policy's
// network are doing at the moment the 3D viewport's rollout is showing.
//
//   Motors    one gauge per actuated joint: the needle is where the joint is, within its command
//             range; a dot is the command the rollout recorded and a ring the command the network
//             gives for this frame; the arc is the joint's effort against its rating, blue to red.
//   Network   the policy's layers, inputs to motor commands, each neuron a cell in the same ramp.
//             Pick a motor (its gauge or its output cell) to see the last layer's strongest
//             contributions to it and which inputs drive it (input × gradient); hover a neuron to
//             see what silencing it would do to each motor.
//   Viewport  "Show in viewport" paints each motor's housing and the parts it moves in the ramp
//             (review_scene.js setHeat); hovering a neuron paints its influence instead.
//
// The network is the rollout's own policy (`api/policy/...`), run here on inputs rebuilt from
// the trace: joint positions, velocities and efforts as recorded, the IMU's orientation from its
// part's pose, its rate from the poses either side, the gait clock from the time. The trace is
// kept at 25 fps and the policy runs faster behind a slew limit, so this is a reconstruction:
// the header says how well the rebuilt commands match the recorded ones. Writes nothing.
(function () {
  'use strict';

  var SVG = 'http://www.w3.org/2000/svg';
  var DEG = 180 / Math.PI;
  // The ramp, blue through violet to red, and the curve that takes a load onto it: 1 - e^(-k·u)
  // with u = |effort| / rated, so the rating lands at 0.8 and the peak saturates rather than
  // clipping. The same ramp colours the network's cells by |activation| / the layer's scale.
  var STOPS = [[0, [43, 92, 255]], [0.45, [140, 70, 255]], [0.8, [255, 54, 96]], [1, [255, 122, 40]]];
  var CURVE = -Math.log(1 - 0.8);
  // How quickly the viewport's heat follows a change, seconds: it rises and falls along this
  // curve rather than flickering frame to frame.
  var EASE_S = 0.12;

  function curve(u) { return 1 - Math.exp(-CURVE * Math.max(0, u)); }
  function rampRGB(t) {
    t = Math.max(0, Math.min(1, t));
    for (var i = 1; i < STOPS.length; i++) {
      if (t <= STOPS[i][0]) {
        var a = STOPS[i - 1], b = STOPS[i], f = (t - a[0]) / (b[0] - a[0]);
        return a[1].map(function (v, k) { return Math.round(v + (b[1][k] - v) * f); });
      }
    }
    return STOPS[STOPS.length - 1][1];
  }
  function rampHex(t) { var c = rampRGB(t); return (c[0] << 16) | (c[1] << 8) | c[2]; }
  function rampCss(t) { var c = rampRGB(t); return 'rgb(' + c[0] + ',' + c[1] + ',' + c[2] + ')'; }
  function el(tag, attrs, ns) {
    var node = ns ? document.createElementNS(SVG, tag) : document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    return node;
  }
  function shortName(joint) { return String(joint || '').replace(/^j_/, '').replace(/_/g, ' '); }

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
  // d command_m / d input (normalised), by backpropagation through the frame's pre-activations.
  Network.prototype.gradient = function (frame, m) {
    var last = this.layers.length - 1, t = frame.post[last][m];
    var g = new Float32Array(this.layers[last].m); g[m] = (1 - t * t) * this.scale[m];
    for (var l = last; l >= 0; l--) {
      var L = this.layers[l], below = new Float32Array(L.n);
      if (l < last) for (var q = 0; q < L.m; q++) g[q] *= this.dact(frame.pre[l][q]);
      for (var i = 0; i < L.n; i++) {
        var s = 0, row = i * L.m;
        for (var k = 0; k < L.m; k++) s += L.W[row + k] * g[k];
        below[i] = s;
      }
      g = below;
    }
    return g;
  };
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

  // -- the editor ------------------------------------------------------------------------------
  function create(o) {
    var viewer = o.viewer, body = o.body;
    var motorsBox = o.motors, canvas = o.canvas, detail = o.detail, status = o.status, toggle = o.toggle;
    var policyUrl = null, playback = null, policy = null, net = null, inputs = null;
    var frames = [], scales = [], match = [], gauges = [], selected = 0, hover = null, frameAt = 0, blendAt = null;
    var showInViewport = false, eased = {}, easedAt = 0, ticket = 0, cellBoxes = [];

    toggle.addEventListener('click', function () {
      showInViewport = !showInViewport;
      toggle.setAttribute('aria-pressed', String(showInViewport));
      eased = {}; paintViewport(true);
    });

    function say(text, state) { status.textContent = text; status.dataset.state = state || ''; status.hidden = !text; }

    function setPlayback(served) {
      ticket++;
      playback = served && served.available ? served : null;
      var url = playback && playback.policy;
      gauges = []; motorsBox.textContent = '';
      if (!playback) { reset('Play a rollout in the 3D viewport — a checkpoint or a run’s own — to see its motors and its network.'); return; }
      buildGauges();
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
      policyUrl = null; policy = null; net = null; frames = []; playback = null;
      say(text, 'empty'); detail.textContent = ''; drawNetwork(); paintViewport(true);
    }
    function dropNetwork(text) { policy = null; net = null; frames = []; say(text, 'warn'); detail.textContent = ''; drawNetwork(); }

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
      body.dataset.match = mean == null ? '' : mean.toFixed(2);
      var shape = [served.network.layers[0][0]].concat(served.network.layers.map(function (s) { return s[1]; })).join(' → ');
      say((served.label ? served.label + ' · ' : '') + shape + (mean == null ? '' : ' · rebuilt commands match the recorded ones at r ' + mean.toFixed(2))
          + (inputs.missing.length ? ' · not rebuilt: ' + inputs.missing.join(', ') : ''), 'ready');
      gauges.forEach(function (g, m) { g.box.title = g.joint + (match[m] == null ? '' : ' · rebuilt vs recorded r ' + match[m].toFixed(2)); });
      setFrame(frameAt, frameAt, 0);
    }

    // -- motors ----------------------------------------------------------------------------
    var R = 34, CX = 50, CY = 48, SWEEP = 270, START = 135;
    function polar(deg, r) { var a = deg * Math.PI / 180; return [CX + r * Math.cos(a), CY + r * Math.sin(a)]; }
    function arc(a0, a1, r) {
      if (a1 < a0) { var t = a0; a0 = a1; a1 = t; }
      var p = polar(a0, r), q = polar(a1, r);
      return 'M' + p[0].toFixed(2) + ' ' + p[1].toFixed(2) + 'A' + r + ' ' + r + ' 0 ' + (a1 - a0 > 180 ? 1 : 0) + ' 1 ' + q[0].toFixed(2) + ' ' + q[1].toFixed(2);
    }
    function buildGauges() {
      (playback.channels || []).forEach(function (c, m) {
        var box = el('figure', { class: 'gauge', 'data-motor': String(m), 'data-joint': c.joint || '' });
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
        var caption = el('figcaption'); caption.textContent = shortName(c.joint || String(c.actuator).split('/')[0]);
        box.appendChild(svg); box.appendChild(caption);
        box.addEventListener('click', function () { selected = m; render(); });
        motorsBox.appendChild(box);
        gauges.push({ box: box, load: load, needle: needle, cmd: cmd, pred: pred, value: value, effort: effort,
                      joint: c.joint || String(c.actuator), low: Number(c.low), high: Number(c.high),
                      rated: Number(c.effort_rated) || null, unit: c.joint_unit || c.unit || '' });
      });
    }
    function angleOf(g, v) {
      var span = g.high - g.low || 1, t = Math.max(-0.04, Math.min(1.04, (v - g.low) / span));
      return START + SWEEP * t;
    }
    function lerp(rows, lo, hi, f, m) {
      var a = rows && rows[lo], b = rows && rows[hi];
      if (!a || a[m] == null) return null;
      return b && b[m] != null ? a[m] + (b[m] - a[m]) * f : a[m];
    }
    function loadOf(m) {
      var g = gauges[m], e = blendAt && lerp(playback.efforts, blendAt.lo, blendAt.hi, blendAt.f, m);
      return e == null || !g.rated ? null : Math.abs(e) / g.rated;
    }
    function paintGauges() {
      var influence = hoverInfluence();
      gauges.forEach(function (g, m) {
        var lo = blendAt.lo, hi = blendAt.hi, f = blendAt.f;
        var q = lerp(playback.joints, lo, hi, f, m), c = (playback.commands[hi] || playback.commands[lo] || [])[m];
        var u = loadOf(m), heat = influence ? influence[m] : u == null ? null : curve(u);
        var zero = angleOf(g, Math.max(g.low, Math.min(g.high, 0)));
        if (q != null) {
          var a = angleOf(g, q), tip = polar(a, R - 6);
          g.needle.setAttribute('x2', tip[0].toFixed(2)); g.needle.setAttribute('y2', tip[1].toFixed(2));
          g.load.setAttribute('d', Math.abs(a - zero) > 0.5 ? arc(zero, a, R) : '');
          g.value.textContent = Math.round(q) + (/deg/.test(g.unit) ? '°' : '');
        }
        g.load.style.stroke = heat == null ? 'var(--ink-2)' : rampCss(heat);
        g.box.style.setProperty('--heat', heat == null ? 'transparent' : rampCss(heat));
        if (c != null) { var pc = polar(angleOf(g, c), R); g.cmd.setAttribute('cx', pc[0].toFixed(2)); g.cmd.setAttribute('cy', pc[1].toFixed(2)); }
        g.cmd.style.display = c == null ? 'none' : '';
        var n = frames[lo] && frames[lo].command[m];
        if (n != null) { var pn = polar(angleOf(g, n), R); g.pred.setAttribute('cx', pn[0].toFixed(2)); g.pred.setAttribute('cy', pn[1].toFixed(2)); }
        g.pred.style.display = n == null ? 'none' : '';
        g.effort.textContent = influence ? 'Δ ' + Math.round(hover.delta[m]) + '°' : u == null ? '' : Math.round(u * 100) + '% rated';
        g.effort.style.fill = heat == null ? '' : rampCss(heat);
        g.box.dataset.selected = String(m === selected);
        g.box.dataset.over = String(u != null && u > 1);
      });
    }

    // -- the network -----------------------------------------------------------------------
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
        var w = usable * weights[i] / total, h = height - 2 * pad - 14;
        var across = c.kind === 'hidden' ? Math.max(1, Math.round(Math.sqrt(c.n * w / h))) : 1;
        var down = Math.ceil(c.n / across), cw = w / across, ch = h / down;
        boxes.push({ col: c, x: x, y: pad + 14, w: w, h: h, across: across, down: down, cw: cw, ch: ch });
        x += w + gap;
      });
      return boxes;
    }
    function cellCentre(b, i) { return [b.x + (i % b.across + 0.5) * b.cw, b.y + (Math.floor(i / b.across) + 0.5) * b.ch]; }
    function valuesOf(b, frame) {
      if (b.col.kind === 'input') return frame.input;
      return frame.post[b.col.layer];
    }
    function cellHeat(b, v) {
      if (b.col.kind === 'input') return Math.min(1, Math.abs(v) / 3);
      if (b.col.kind === 'output') return Math.abs(v);
      return Math.min(1, Math.abs(v) / scales[b.col.layer]);
    }
    function drawNetwork() {
      var ctx = canvas.getContext('2d'), dpr = Math.min(2, window.devicePixelRatio || 1);
      var w = canvas.clientWidth || 300, h = canvas.clientHeight || 200;
      if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) { canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr); }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, w, h);
      cellBoxes = [];
      var frame = frames[frameAt];
      if (!net || !frame) return;
      var boxes = layout(w, h); cellBoxes = boxes;
      var ink2 = getComputedStyle(document.documentElement).getPropertyValue('--ink-2').trim() || '#999';
      ctx.font = '12px ' + (getComputedStyle(document.body).fontFamily || 'sans-serif'); ctx.fillStyle = ink2; ctx.textBaseline = 'top';
      var names = { input: 'inputs ' + net.layers[0].n, output: 'motors ' + net.layers[net.layers.length - 1].m };
      boxes.forEach(function (b) { ctx.fillText(b.col.kind === 'hidden' ? String(b.col.n) : names[b.col.kind], b.x, 0); });
      var outBox = boxes[boxes.length - 1], lastHidden = boxes[boxes.length - 2], attribution = selectedAttribution(frame);
      boxes.forEach(function (b) {
        var values = valuesOf(b, frame), gapPx = b.cw > 4 && b.ch > 4 ? 1 : 0;
        for (var i = 0; i < b.col.n; i++) {
          var p = cellCentre(b, i), heat = cellHeat(b, values[i]);
          if (b.col.kind === 'input' && attribution) heat = Math.min(1, Math.abs(attribution.inputs[i]) / attribution.inputMax);
          ctx.fillStyle = rampCss(heat); ctx.globalAlpha = 0.18 + 0.82 * heat;
          ctx.fillRect(p[0] - b.cw / 2 + gapPx / 2, p[1] - b.ch / 2 + gapPx / 2, Math.max(1, b.cw - gapPx), Math.max(1, b.ch - gapPx));
        }
        ctx.globalAlpha = 1;
      });
      // The picked motor: the last hidden layer's strongest contributions to it, as lines over the
      // cells, red where a neuron pushes the command up and blue where it pulls it down.
      if (attribution && lastHidden) {
        var target = cellCentre(outBox, selected);
        attribution.top.slice().reverse().forEach(function (t) {
          var from = cellCentre(lastHidden, t.j), k = Math.abs(t.c) / attribution.max;
          ctx.strokeStyle = (t.c > 0 ? 'rgba(255,80,100,' : 'rgba(90,130,255,') + (0.35 + 0.65 * k).toFixed(2) + ')';
          ctx.lineWidth = 0.75 + 2.25 * k;
          ctx.beginPath(); ctx.moveTo(from[0] + lastHidden.cw / 2, from[1]);
          ctx.bezierCurveTo(from[0] + lastHidden.cw / 2 + 30, from[1], target[0] - outBox.cw / 2 - 30, target[1], target[0] - outBox.cw / 2, target[1]);
          ctx.stroke();
          ctx.strokeStyle = 'rgba(237,237,237,' + (0.4 + 0.6 * k).toFixed(2) + ')'; ctx.lineWidth = 1;
          ctx.strokeRect(from[0] - lastHidden.cw / 2 + .5, from[1] - lastHidden.ch / 2 + .5, lastHidden.cw - 1, lastHidden.ch - 1);
        });
      }
      var s = cellCentre(outBox, selected);
      ctx.strokeStyle = '#ededed'; ctx.lineWidth = 1.5; ctx.strokeRect(outBox.x + 0.75, s[1] - outBox.ch / 2 + 0.75, outBox.cw - 1.5, outBox.ch - 1.5);
      if (hover) { var hb = boxes[hover.box], hp = cellCentre(hb, hover.i); ctx.strokeStyle = '#ededed'; ctx.strokeRect(hp[0] - hb.cw / 2, hp[1] - hb.ch / 2, hb.cw, hb.ch); }
    }
    function selectedAttribution(frame) {
      if (!net || !frame || selected == null) return null;
      var l = net.layers.length - 1, L = net.layers[l], a = frame.post[l - 1], c = [];
      for (var j = 0; j < L.n; j++) c.push({ j: j, c: a[j] * L.W[j * L.m + selected] });
      c.sort(function (x, y) { return Math.abs(y.c) - Math.abs(x.c); });
      var top = c.slice(0, 16), max = Math.abs(top[0] && top[0].c) || 1;
      var g = net.gradient(frame, selected), inputs = [], inputMax = 0;
      for (var i = 0; i < g.length; i++) { inputs.push(g[i] * frame.input[i]); inputMax = Math.max(inputMax, Math.abs(inputs[i])); }
      return { top: top, max: max, inputs: inputs, inputMax: inputMax || 1 };
    }
    function renderDetail() {
      var frame = frames[frameAt];
      detail.textContent = '';
      if (!net || !frame || !gauges[selected]) return;
      var g = gauges[selected], att = selectedAttribution(frame);
      var head = el('p'); head.className = 'activations-pick';
      head.textContent = shortName(g.joint) + ': network ' + Math.round(frame.command[selected]) + '°' +
        (match[selected] == null ? '' : ' · rebuilt vs recorded r ' + match[selected].toFixed(2)) + ' · driven most by';
      detail.appendChild(head);
      var order = att.inputs.map(function (v, i) { return { i: i, v: v }; }).sort(function (x, y) { return Math.abs(y.v) - Math.abs(x.v); });
      var total = order.reduce(function (s, x) { return s + Math.abs(x.v); }, 0) || 1, list = el('ol');
      list.className = 'activations-drivers';
      order.slice(0, 6).forEach(function (x) {
        var li = el('li'), bar = el('span'), name = el('span'), share = el('span');
        name.textContent = policy.observations[x.i]; share.textContent = Math.round(100 * Math.abs(x.v) / total) + '%';
        bar.className = 'bar'; bar.style.width = (100 * Math.abs(x.v) / Math.abs(order[0].v || 1)).toFixed(1) + '%';
        bar.style.background = x.v > 0 ? 'rgb(255,70,90)' : 'rgb(70,110,255)';
        li.appendChild(name); li.appendChild(share); li.appendChild(bar); list.appendChild(li);
      });
      detail.appendChild(list);
    }

    // Hover: what silencing that neuron would do to each motor, as heat on the gauges and parts.
    canvas.addEventListener('pointermove', function (e) {
      var r = canvas.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top, found = null;
      cellBoxes.forEach(function (b, bi) {
        if (found || x < b.x || x > b.x + b.w || y < b.y || y > b.y + b.h) return;
        var i = Math.floor((y - b.y) / b.ch) * b.across + Math.floor((x - b.x) / b.cw);
        if (i >= 0 && i < b.col.n) found = { box: bi, i: i, b: b };
      });
      var before = hover && hover.box + ':' + hover.i;
      if (!found || found.b.col.kind !== 'hidden') {
        hover = null;
        canvas.title = found ? (found.b.col.kind === 'input' ? policy.observations[found.i] : shortName(gauges[found.i] && gauges[found.i].joint)) : '';
      } else {
        var frame = frames[frameAt], delta = net.ablate(frame, found.b.col.layer, found.i);
        var span = gauges.map(function (g) { return Math.abs(g.high - g.low) || 1; });
        hover = { box: found.box, i: found.i, layer: found.b.col.layer, delta: delta,
                  heat: delta.map(function (d, m) { return Math.min(1, Math.abs(d) / span[m] * 4); }) };
        canvas.title = 'layer ' + (found.b.col.layer + 1) + ' neuron ' + found.i + ' · ' + frame.post[found.b.col.layer][found.i].toFixed(2) + ' · silenced, it would move each motor by Δ';
      }
      if ((hover && hover.box + ':' + hover.i) !== before) render();
    });
    canvas.addEventListener('pointerleave', function () { if (hover) { hover = null; render(); } });
    // A press on a motor's output cell picks it, as its gauge does.
    canvas.addEventListener('pointerdown', function (e) {
      var r = canvas.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top, b = cellBoxes[cellBoxes.length - 1];
      if (b && x >= b.x && x <= b.x + b.w && y >= b.y && y <= b.y + b.h) { selected = Math.min(b.col.n - 1, Math.floor((y - b.y) / b.ch)); render(); }
    });
    function hoverInfluence() { return hover ? hover.heat : null; }

    // -- the viewport ----------------------------------------------------------------------
    function paintViewport(now) {
      var v = viewer && viewer();
      if (!v || !v.setHeat) return;
      if (!showInViewport || !playback || !gauges.length) { v.setHeat(null); body.dataset.viewport = 'off'; return; }
      var parts = (policy && policy.parts) || {}, influence = hoverInfluence(), map = {};
      var t = performance.now() / 1000, k = now ? 1 : 1 - Math.exp(-(t - easedAt) / EASE_S); easedAt = t;
      gauges.forEach(function (g, m) {
        var u = loadOf(m), target = influence ? influence[m] : u == null ? 0 : curve(u);
        var heat = eased[m] == null || now ? target : eased[m] + (target - eased[m]) * k; eased[m] = heat;
        var own = parts[g.joint] || {};
        (own.segment || []).forEach(function (name) { if (map[name] == null) map[name] = rampHex(heat); });
        // A motor's housing shows its own joint, over the segment it rides on.
        (own.motor || []).forEach(function (name) { map[name] = rampHex(heat); });
      });
      body.dataset.viewport = Object.keys(map).length ? 'on' : 'unmapped';
      v.setHeat(Object.keys(map).length ? map : null);
    }

    function render() {
      if (!playback || !blendAt) return;
      paintGauges(); drawNetwork(); renderDetail(); paintViewport(false);
    }
    // The 3D viewport's playback calls this on every seek: between frames lo and hi at f.
    function setFrame(lo, hi, f) {
      if (!playback) return;
      frameAt = lo; blendAt = { lo: lo, hi: hi, f: f };
      if (!body.isConnected || !body.offsetParent) { paintViewport(false); return; }
      render();
    }
    if (window.ResizeObserver) new ResizeObserver(function () { drawNetwork(); }).observe(canvas);

    return {
      setPlayback: setPlayback, setFrame: setFrame,
      setViewport: function (on) { if (!!on !== showInViewport) toggle.click(); return showInViewport; },
      select: function (m) { selected = m; render(); return selected; },
      hoverNeuron: function (layer, i) {
        if (!net || !frames[frameAt]) return null;
        var delta = net.ablate(frames[frameAt], layer, i), span = gauges.map(function (g) { return Math.abs(g.high - g.low) || 1; });
        hover = { box: layer + 1, i: i, layer: layer, delta: delta, heat: delta.map(function (d, m) { return Math.min(1, Math.abs(d) / span[m] * 4); }) };
        render(); return delta;
      },
      clearHover: function () { hover = null; render(); },
      state: function () {
        return { policy: policyUrl, ready: !!net, frame: frameAt, selected: selected, motors: gauges.length,
                 match: match.slice(), missing: inputs ? inputs.missing.slice() : [], viewport: showInViewport,
                 command: frames[frameAt] ? frames[frameAt].command.slice() : null };
      }
    };
  }

  window.CadexActivations = { create: create, ramp: rampCss, curve: curve };
})();
