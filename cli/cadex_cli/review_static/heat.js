// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The heat colours (ADR-728; docs/DASHBOARD.md §27, §28): the ramp the Activations and Network
// editors and the 3D viewport's "Show in viewport" paint a load or an activation in, from 0
// (idle) to 1 (peak). A theme is two or three colours, low to high through an optional middle,
// mixed in sRGB; the Settings editor picks a preset or the colours, and the choice is this
// browser's own (`localStorage` cadex.heat). Every painter asks for the colour each time it
// paints, and onChange tells it to paint again.
(function () {
  'use strict';

  var KEY = 'cadex.heat';
  // Blue fading through white into faint red and then dark red: the middle is at 0.5, and a
  // motor at its rating (0.8 on the load curve) already reads red.
  var PRESETS = {
    'blue-white-red': { name: 'Blue–white–red', stops: ['#2f6bff', '#f2f2f2', '#9e0b1f'] },
    'green-red': { name: 'Green–red', stops: ['#20b46a', '#f0d24a', '#d42a3c'] },
    'viridis': { name: 'Viridis', stops: ['#440154', '#21918c', '#fde725'] },
    'blue-red': { name: 'Blue–red', stops: ['#2f6bff', '#d42a3c'] }
  };
  var DEFAULT = 'blue-white-red';
  var listeners = [];

  function parse(hex) {
    var m = /^#?([0-9a-f]{6})$/i.exec(String(hex || '').trim());
    if (!m) return null;
    var n = parseInt(m[1], 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function valid(theme) {
    return theme && Array.isArray(theme.stops) && theme.stops.length >= 2 && theme.stops.length <= 3
      && theme.stops.every(function (s) { return !!parse(s); });
  }
  function fromPreset(key) { return { preset: key, stops: PRESETS[key].stops.slice() }; }
  function load() {
    try {
      var kept = JSON.parse(localStorage.getItem(KEY) || 'null');
      if (kept && PRESETS[kept.preset]) return fromPreset(kept.preset);
      if (kept && kept.preset === 'custom' && valid(kept)) return { preset: 'custom', stops: kept.stops.slice() };
    } catch (_) { /* the default, below */ }
    return fromPreset(DEFAULT);
  }

  var theme = load(), rgb = theme.stops.map(parse);

  function rampRGB(t) {
    t = Math.max(0, Math.min(1, Number(t) || 0));
    var n = rgb.length - 1, at = Math.min(n - 1, Math.floor(t * n)), f = t * n - at;
    var a = rgb[at], b = rgb[at + 1];
    return [0, 1, 2].map(function (k) { return Math.round(a[k] + (b[k] - a[k]) * f); });
  }
  function css(t) { var c = rampRGB(t); return 'rgb(' + c[0] + ',' + c[1] + ',' + c[2] + ')'; }
  function hex(t) { var c = rampRGB(t); return (c[0] << 16) | (c[1] << 8) | c[2]; }
  // The ramp as a CSS gradient, for a legend or a preview.
  function gradient() {
    return 'linear-gradient(90deg, ' + theme.stops.map(function (s, i) {
      return s + ' ' + Math.round(100 * i / (theme.stops.length - 1)) + '%';
    }).join(', ') + ')';
  }
  // The two ends: what a negative and a positive contribution are drawn in.
  function ends() { return { low: theme.stops[0], high: theme.stops[theme.stops.length - 1] }; }

  function set(next) {
    if (typeof next === 'string' && PRESETS[next]) next = fromPreset(next);
    else if (next && valid(next)) next = { preset: PRESETS[next.preset] ? next.preset : 'custom', stops: next.stops.map(function (s) { return s.toLowerCase(); }) };
    else return get();
    theme = next; rgb = theme.stops.map(parse);
    try { localStorage.setItem(KEY, JSON.stringify(theme)); } catch (_) { /* this visit only */ }
    listeners.slice().forEach(function (fn) { try { fn(get()); } catch (_) { /* one painter's fault stays its own */ } });
    return get();
  }
  function get() { return { preset: theme.preset, stops: theme.stops.slice() }; }
  function onChange(fn) { listeners.push(fn); }

  window.CadexHeat = {
    presets: function () {
      return Object.keys(PRESETS).map(function (k) { return { key: k, name: PRESETS[k].name, stops: PRESETS[k].stops.slice() }; });
    },
    preset: function (key) { return PRESETS[key] ? PRESETS[key].stops.slice() : null; },
    defaultPreset: DEFAULT,
    get: get, set: set, onChange: onChange, css: css, hex: hex, rgb: rampRGB, gradient: gradient, ends: ends
  };
})();
