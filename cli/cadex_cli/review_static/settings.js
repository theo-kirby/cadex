// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The Settings editor (ADR-728; docs/DASHBOARD.md §28): this browser's own preferences, which
// change how the page draws and never the project (ADR-537): the heat colours (heat.js), as a
// preset or as two or three colours picked by hand, and the trail's colours (trailcolours.js,
// ADR-770), one colour or a ramp by age, picked the same way.
(function () {
  'use strict';

  function create(o) {
    var heat = window.CadexHeat;
    if (!heat || !o.preset) return null;
    var preset = o.preset, count = o.count, pickers = [o.low, o.mid, o.high], preview = o.preview;

    heat.presets().forEach(function (p) {
      var option = document.createElement('option'); option.value = p.key; option.textContent = p.name; preset.appendChild(option);
    });
    var custom = document.createElement('option'); custom.value = 'custom'; custom.textContent = 'Custom'; preset.appendChild(custom);

    function mix(a, b) {
      var x = parseInt(a.slice(1), 16), y = parseInt(b.slice(1), 16);
      return '#' + [16, 8, 0].map(function (s) {
        return ('0' + Math.round((((x >> s) & 255) + ((y >> s) & 255)) / 2).toString(16)).slice(-2);
      }).join('');
    }
    function show(theme) {
      var three = theme.stops.length === 3;
      preset.value = theme.preset;
      count.querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-pressed', String(Number(b.dataset.count) === theme.stops.length)); });
      pickers[0].value = theme.stops[0];
      pickers[1].value = three ? theme.stops[1] : mix(theme.stops[0], theme.stops[1]);
      pickers[2].value = theme.stops[theme.stops.length - 1];
      pickers[1].closest('label').hidden = !three;
      preview.style.background = heat.gradient();
    }
    function picked() {
      var three = count.querySelector('button[aria-pressed="true"]').dataset.count === '3';
      return three ? [pickers[0].value, pickers[1].value, pickers[2].value] : [pickers[0].value, pickers[2].value];
    }

    preset.addEventListener('change', function () {
      show(preset.value === 'custom' ? heat.set({ preset: 'custom', stops: heat.get().stops }) : heat.set(preset.value));
    });
    count.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-count]'); if (!b) return;
      count.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
      show(heat.set({ preset: 'custom', stops: picked() }));
    });
    pickers.forEach(function (p) {
      p.addEventListener('input', function () { show(heat.set({ preset: 'custom', stops: picked() })); });
    });
    if (o.reset) o.reset.addEventListener('click', function () { show(heat.set(heat.defaultPreset)); });
    show(heat.get());
    return { show: function () { show(heat.get()); } };
  }

  // The trail's colours: one colour, or by age through a preset or two or three colours.
  function createTrail(o) {
    var trail = window.CadexTrailColours;
    if (!trail || !o.mode) return null;
    var pickers = [o.old, o.mid, o.newest];
    trail.presets().forEach(function (p) {
      var option = document.createElement('option'); option.value = p.key; option.textContent = p.name; o.preset.appendChild(option);
    });
    var custom = document.createElement('option'); custom.value = 'custom'; custom.textContent = 'Custom'; o.preset.appendChild(custom);
    function mix(a, b) {
      var x = parseInt(a.slice(1), 16), y = parseInt(b.slice(1), 16);
      return '#' + [16, 8, 0].map(function (s) { return ('0' + Math.round((((x >> s) & 255) + ((y >> s) & 255)) / 2).toString(16)).slice(-2); }).join('');
    }
    function show(c) {
      var three = c.stops.length === 3;
      o.mode.querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.mode === c.mode)); });
      o.count.querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-pressed', String(Number(b.dataset.count) === c.stops.length)); });
      o.solid.value = c.solid;
      o.preset.value = c.preset;
      pickers[0].value = c.stops[0];
      pickers[1].value = three ? c.stops[1] : mix(c.stops[0], c.stops[1]);
      pickers[2].value = c.stops[c.stops.length - 1];
      pickers[1].closest('label').hidden = !three;
      o.solidRow.hidden = c.mode !== 'solid';
      o.age.hidden = c.mode !== 'age';
      o.preview.style.background = c.mode === 'solid' ? c.solid : trail.gradient();
    }
    function picked() {
      var three = o.count.querySelector('button[aria-pressed="true"]').dataset.count === '3';
      return three ? [pickers[0].value, pickers[1].value, pickers[2].value] : [pickers[0].value, pickers[2].value];
    }
    o.mode.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-mode]'); if (b) show(trail.set({ mode: b.dataset.mode }));
    });
    o.solid.addEventListener('input', function () { show(trail.set({ solid: o.solid.value })); });
    o.preset.addEventListener('change', function () {
      if (o.preset.value !== 'custom') show(trail.set({ preset: o.preset.value }));
    });
    o.count.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-count]'); if (!b) return;
      o.count.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
      show(trail.set({ stops: picked() }));
    });
    pickers.forEach(function (p) { p.addEventListener('input', function () { show(trail.set({ stops: picked() })); }); });
    if (o.reset) o.reset.addEventListener('click', function () { show(trail.set('default')); });
    trail.onChange(show);
    show(trail.get());
    return { show: function () { show(trail.get()); } };
  }

  window.CadexSettings = { create: create, createTrail: createTrail };
})();
