// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The colour theme (ADR-534): dark, light, or the system's. Loaded as a
// plain script in every page's <head>, so the first paint is already in the
// chosen theme. The choice is this browser's own, kept in localStorage; a
// browser that refuses storage gets dark every time.
(function () {
  'use strict';

  var KEY = 'cadex.theme', CHOICES = ['dark', 'light', 'system'];
  var root = document.documentElement, query = window.matchMedia('(prefers-color-scheme: light)');

  function read() {
    try { var value = localStorage.getItem(KEY); return CHOICES.indexOf(value) >= 0 ? value : 'dark'; }
    catch (_) { return 'dark'; }
  }
  function resolve(choice) { return choice === 'system' ? (query.matches ? 'light' : 'dark') : choice; }
  function apply(choice) {
    var theme = resolve(choice), changed = root.dataset.theme !== theme;
    root.dataset.theme = theme;
    root.dataset.themeChoice = choice;
    if (changed) document.dispatchEvent(new CustomEvent('cadex-theme', { detail: { theme: theme, choice: choice } }));
  }

  window.cadexTheme = {
    choices: CHOICES.slice(),
    choice: read,
    theme: function () { return root.dataset.theme; },
    set: function (choice) {
      if (CHOICES.indexOf(choice) < 0) return;
      try { localStorage.setItem(KEY, choice); } catch (_) { /* this visit only */ }
      apply(choice);
      document.dispatchEvent(new CustomEvent('cadex-theme-choice', { detail: { choice: choice } }));
    }
  };
  query.addEventListener('change', function () { if (read() === 'system') apply('system'); });
  apply(read());
})();
