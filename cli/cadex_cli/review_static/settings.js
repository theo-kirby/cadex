// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The Settings editor (ADR-728; docs/DASHBOARD.md §28): this browser's own preferences, which
// change how the page draws and never the project (ADR-537). For now one: the heat colours
// (heat.js), as a preset or as two or three colours picked by hand.
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

  window.CadexSettings = { create: create };
})();
