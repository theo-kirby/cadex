// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The navigation gizmo (ADR-720; docs/DASHBOARD.md §5), after Blender's: the model's X, Y and Z
// axes as seen from the 3D viewport's camera, in its top right corner, turning as the view orbits.
// The positive end of each axis is a lettered ball on a stem, the negative end a ring; the ends
// nearer the camera are drawn over the far ones. A click on an end glides the camera round to look
// along that axis, keeping its target and distance (Y up for top and bottom); a click on the view
// already shown turns to the opposite one. The glide is about 0.4 s, eased, and instant under
// prefers-reduced-motion; a press, pinch or wheel on the canvas takes the camera back mid-glide.
// It works while a rollout plays and the view follows it (ADR-723): follow moves the target, the
// gizmo the direction, and each leaves the other's alone.
//
// It reads and sets the viewer's camera (review_scene.js camera/setCamera) and repaints on its
// draws; it writes nothing (ADR-537).
(function () {
  'use strict';

  var SVG = 'http://www.w3.org/2000/svg';
  var SIZE = 88, R = 30, BALL = 9, RING = 7;
  var TOP = Math.PI / 2 - 1e-3;   // a hair off the pole, so the camera's up stays defined
  var GLIDE_MS = 420;
  // Each end: the camera's offset direction from the target when looking along it.
  var ENDS = [
    { key: '+x', axis: 0, sign: 1, label: 'X', view: { yaw: 0, pitch: 0 }, name: 'Right' },
    { key: '+y', axis: 1, sign: 1, label: 'Y', view: { yaw: Math.PI / 2, pitch: 0 }, name: 'Back' },
    { key: '+z', axis: 2, sign: 1, label: 'Z', view: { yaw: -Math.PI / 2, pitch: TOP }, name: 'Top' },
    { key: '-x', axis: 0, sign: -1, view: { yaw: Math.PI, pitch: 0 }, name: 'Left' },
    { key: '-y', axis: 1, sign: -1, view: { yaw: -Math.PI / 2, pitch: 0 }, name: 'Front' },
    { key: '-z', axis: 2, sign: -1, view: { yaw: -Math.PI / 2, pitch: -TOP }, name: 'Bottom' }
  ];
  var OPPOSITE = { '+x': '-x', '-x': '+x', '+y': '-y', '-y': '+y', '+z': '-z', '-z': '+z' };

  function el(name, attrs) {
    var node = document.createElementNS(SVG, name);
    Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    return node;
  }
  // The shortest turn from a to b, radians.
  function turn(a, b) { var d = (b - a) % (2 * Math.PI); return d > Math.PI ? d - 2 * Math.PI : d < -Math.PI ? d + 2 * Math.PI : d; }
  function ease(t) { return t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }
  function still() { return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches; }

  function create(viewer, root, canvas) {
    if (!viewer || !viewer.available || !root) return null;
    root.setAttribute('viewBox', [-SIZE / 2, -SIZE / 2, SIZE, SIZE].join(' '));
    root.appendChild(el('circle', { class: 'gizmo-disc', r: SIZE / 2 - 1 }));
    var stems = {}, ends = {};
    ENDS.forEach(function (end) {
      if (end.sign > 0) stems[end.key] = el('line', { class: 'gizmo-stem', 'data-axis': end.label.toLowerCase(), x1: 0, y1: 0 });
      var g = el('g', { class: 'gizmo-end', 'data-end': end.key, 'data-axis': 'xyz'[end.axis], tabindex: '-1' });
      var title = el('title'); title.textContent = end.name + ' view'; g.appendChild(title);
      g.appendChild(el('circle', { r: end.sign > 0 ? BALL : RING }));
      if (end.label) { var t = el('text', { 'text-anchor': 'middle', 'dominant-baseline': 'central' }); t.textContent = end.label; g.appendChild(t); }
      // A press and a release on the same end snap, rather than a click: the ends are restacked
      // as the view turns, and a click is lost when its target moves between the two.
      g.addEventListener('pointerdown', function (e) { e.stopPropagation(); pressed = end.key; });
      g.addEventListener('pointerup', function (e) { e.stopPropagation(); if (pressed === end.key) snap(end); pressed = null; });
      ends[end.key] = g;
    });
    root.removeAttribute('hidden');   // an SVG element has no hidden property, only the attribute

    var glide = null, shown = '', stacked = '', pressed = null;
    root.addEventListener('pointerleave', function () { pressed = null; });
    function paint() {
      var c = viewer.camera(), sy = Math.sin(c.yaw), cy = Math.cos(c.yaw), sp = Math.sin(c.pitch), cp = Math.cos(c.pitch);
      // The camera's right, up and toward-the-camera vectors in the model's z-up frame.
      var right = [-sy, cy, 0], up = [-sp * cy, -sp * sy, cp], toward = [cp * cy, cp * sy, sp];
      var order = ENDS.map(function (end) {
        var x = end.sign * right[end.axis] * R, y = -end.sign * up[end.axis] * R;
        ends[end.key].setAttribute('transform', 'translate(' + x.toFixed(2) + ' ' + y.toFixed(2) + ')');
        if (stems[end.key]) { stems[end.key].setAttribute('x2', x.toFixed(2)); stems[end.key].setAttribute('y2', y.toFixed(2)); }
        return { end: end, depth: end.sign * toward[end.axis] };
      }).sort(function (a, b) { return a.depth - b.depth; });
      // Far to near, each stem just under its ball, so a near end is never hidden by a far one;
      // only when the order changes, so a view redrawn every frame (playing, following) leaves
      // the ends where a press found them.
      var key = order.map(function (o) { return o.end.key; }).join(' ');
      if (key !== stacked) {
        stacked = key;
        order.forEach(function (o) {
          if (stems[o.end.key]) root.appendChild(stems[o.end.key]);
          root.appendChild(ends[o.end.key]);
        });
      }
      shown = ENDS.filter(function (end) {
        return Math.abs(turn(c.yaw, end.view.yaw)) < 1e-3 && Math.abs(c.pitch - end.view.pitch) < 1e-3
          || Math.abs(end.view.pitch) > 1.5 && Math.abs(c.pitch - end.view.pitch) < 1e-3;
      }).map(function (end) { return end.key; })[0] || '';
      root.dataset.view = shown;
    }
    function snap(end) {
      if (shown === end.key) end = ENDS.filter(function (e) { return e.key === OPPOSITE[end.key]; })[0];
      var from = viewer.camera(), to = { yaw: end.view.yaw, pitch: end.view.pitch };
      var dyaw = turn(from.yaw, to.yaw), dpitch = to.pitch - from.pitch;
      stop();
      if (still()) { from.yaw += dyaw; from.pitch = to.pitch; viewer.setCamera(from); return; }
      var t0 = performance.now();
      glide = { frame: 0 };
      (function step(now) {
        var t = Math.max(0, Math.min(1, (now - t0) / GLIDE_MS)), k = ease(t), c = viewer.camera();
        c.yaw = from.yaw + dyaw * k; c.pitch = from.pitch + dpitch * k;
        viewer.setCamera(c);
        glide.frame = t < 1 ? requestAnimationFrame(step) : 0;
        if (!glide.frame) glide = null;
      })(t0);
    }
    function stop() { if (glide) { cancelAnimationFrame(glide.frame); glide = null; } }
    // The person's own hand on the camera wins over a glide.
    if (canvas) ['pointerdown', 'wheel'].forEach(function (type) { canvas.addEventListener(type, stop, { passive: true }); });
    viewer.setOnDraw(paint);
    paint();
    return { paint: paint, snap: function (key) { ENDS.forEach(function (e) { if (e.key === key) snap(e); }); },
             gliding: function () { return !!glide; }, view: function () { return shown; } };
  }

  window.CadexGizmo = { create: create };
})();
