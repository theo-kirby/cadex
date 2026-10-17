// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The trail's colours (ADR-770; docs/DASHBOARD.md §28): the 3D viewport's trail drawn in one
// colour, white by default, or by age -- a ramp of two or three colours from the oldest of the
// trail shown to the newest, at the design, as the heat colours ramp from idle to peak. The
// Settings editor picks them; the choice is this browser's own (`localStorage`
// cadex.trail.colours). The scene asks for them through onChange.
(function () {
  'use strict';

  var KEY = 'cadex.trail.colours';
  // Oldest to newest.
  var PRESETS = {
    'fade': { name: 'Fade in', stops: ['#2a2a2a', '#ffffff'] },
    'ice': { name: 'Ice', stops: ['#1d3557', '#6ff0f0', '#ffffff'] },
    'ember': { name: 'Ember', stops: ['#3a0d12', '#d42a3c', '#ffd27a'] },
    'viridis': { name: 'Viridis', stops: ['#440154', '#21918c', '#fde725'] },
    'cool-warm': { name: 'Cool to warm', stops: ['#2f6bff', '#f2f2f2', '#d42a3c'] }
  };
  var DEFAULT = { mode: 'solid', solid: '#ffffff', preset: 'fade', stops: PRESETS.fade.stops.slice() };
  var listeners = [];

  function hex(value) { return /^#[0-9a-f]{6}$/i.test(String(value || '')) ? String(value).toLowerCase() : null; }
  function copy(c) { return { mode: c.mode, solid: c.solid, preset: c.preset, stops: c.stops.slice() }; }
  // A choice as kept or asked for, made whole: anything missing or malformed is the default's.
  function whole(next, base) {
    var out = copy(base || DEFAULT);
    if (!next || typeof next !== 'object') return out;
    if (next.mode === 'solid' || next.mode === 'age') out.mode = next.mode;
    if (hex(next.solid)) out.solid = hex(next.solid);
    if (typeof next.preset === 'string' && PRESETS[next.preset] && !Array.isArray(next.stops)) {
      out.preset = next.preset; out.stops = PRESETS[next.preset].stops.slice();
    } else if (Array.isArray(next.stops) && next.stops.length >= 2 && next.stops.length <= 3 && next.stops.every(hex)) {
      out.stops = next.stops.map(hex);
      out.preset = PRESETS[next.preset] && PRESETS[next.preset].stops.join() === out.stops.join() ? next.preset : 'custom';
    }
    return out;
  }
  function load() {
    try { return whole(JSON.parse(localStorage.getItem(KEY) || 'null')); } catch (_) { return copy(DEFAULT); }
  }
  var colours = load();

  function set(next) {
    colours = next === 'default' ? copy(DEFAULT) : whole(next, colours);
    try { localStorage.setItem(KEY, JSON.stringify(colours)); } catch (_) { /* this visit only */ }
    listeners.slice().forEach(function (fn) { try { fn(get()); } catch (_) { /* one painter's fault stays its own */ } });
    return get();
  }
  function get() { return copy(colours); }
  // The ramp as a CSS gradient, for the preview.
  function gradient() {
    return 'linear-gradient(90deg, ' + colours.stops.map(function (s, i) {
      return s + ' ' + Math.round(100 * i / (colours.stops.length - 1)) + '%';
    }).join(', ') + ')';
  }

  window.CadexTrailColours = {
    presets: function () {
      return Object.keys(PRESETS).map(function (k) { return { key: k, name: PRESETS[k].name, stops: PRESETS[k].stops.slice() }; });
    },
    get: get, set: set, gradient: gradient, onChange: function (fn) { listeners.push(fn); }
  };
})();
