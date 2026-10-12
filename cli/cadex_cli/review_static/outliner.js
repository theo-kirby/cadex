// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The Outliner (ADR-676; docs/DASHBOARD.md §25), after Blender's: every part of the model the 3D
// viewport shows, in groups, each with an eye that shows or hides it and a row that selects it.
//
//   Groups     by type (printed, purchased, hardware, boards -- the default), by appearance role,
//              or none; a group folds, and its eye shows or hides all of it. Hardware starts folded.
//   Rows       a click selects the part (and the viewport glows it); Shift or Ctrl adds or
//              removes one, Shift a run; a double click frames it. The eye hides it; Ctrl on the
//              eye isolates it (or its group). A click on a solid in the viewport selects its row.
//   Keys       over the viewport or the Outliner, as in Blender: H hides the selection, Shift+H
//              hides everything else, Alt+H shows everything, F frames the selection (or all), Esc
//              clears the selection.
//
// What is hidden and selected is the viewer's (review_scene.js setHidden/select), kept by part
// name, so it outlives the agent's next write; it is this page's own and never written anywhere
// (ADR-537). The group choice and the folded groups are this browser's, in localStorage.
(function () {
  'use strict';

  var GROUPINGS = ['type', 'role', 'none'];
  var TYPES = [['printed', 'Printed parts'], ['purchased', 'Purchased parts'], ['hardware', 'Hardware'], ['board', 'Boards']];
  var ROLES = [['shell', 'Shell'], ['mechanism', 'Mechanism'], ['accent', 'Accent']];
  var EYE = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M1.5 8s2.4-4.5 6.5-4.5S14.5 8 14.5 8 12.1 12.5 8 12.5 1.5 8 1.5 8z"/><circle cx="8" cy="8" r="2"/></svg>';
  var EYE_OFF = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2.5 10.2C1.8 9.2 1.5 8 1.5 8S3.9 3.5 8 3.5c1 0 1.9.3 2.7.7M13.5 5.8c.7 1 1 2.2 1 2.2s-2.4 4.5-6.5 4.5c-1 0-1.9-.3-2.7-.7M2.5 13.5l11-11"/></svg>';
  var FOLD = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6 4l4 4-4 4"/></svg>';

  function readStored(key) { try { return localStorage.getItem(key); } catch (_) { return null; } }
  function writeStored(key, value) { try { localStorage.setItem(key, value); } catch (_) { /* this visit only */ } }
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }
  function typeOf(part) {
    var finish = part.finish || (part.supplier === 'purchased' ? 'purchased' : 'printed');
    return finish === 'hardware' || finish === 'board' || finish === 'purchased' ? finish : 'printed';
  }
  function detailOf(part) {
    var bits = [], catalog = part.catalog || {};
    if (catalog.family) bits.push(catalog.family + (catalog.part_number ? ' ' + catalog.part_number : ''));
    else bits.push(typeOf(part));
    if (part.role) bits.push(part.role);
    return bits.join(' · ');
  }

  // options: tree, filter, group, showAll, summary (elements); viewer() -> the 3D viewer;
  // frameScope (the element keys work over besides the tree).
  function create(options) {
    var grouping = GROUPINGS.indexOf(readStored('cadex.outliner.group')) >= 0 ? readStored('cadex.outliner.group') : 'type';
    var folded = {};
    try { folded = JSON.parse(readStored('cadex.outliner.folded')) || {}; } catch (_) { folded = {}; }
    if (typeof folded !== 'object' || Array.isArray(folded)) folded = {};
    var parts = [], hidden = {}, selected = [], anchor = null, filter = '', drawnKey = null, over = false;

    function viewer() { var v = options.viewer(); return v && v.available ? v : null; }
    function push() {
      var v = viewer();
      if (!v) return;
      v.setHidden(Object.keys(hidden));
      v.select(selected);
    }
    function names() { return parts.map(function (p) { return p.name; }); }

    // The parts as the model lists them, world geometry left out; what was hidden or selected
    // stays so where a part of that name is still there.
    function setModel(manifest) {
      var list = manifest && manifest.available ? (manifest.components || []).filter(function (c) { return c.mesh && c.world !== true; }) : [];
      parts = list.map(function (c) {
        return { name: c.name, finish: c.finish || null, supplier: c.supplier || null, role: c.role || null, color: c.color || null,
                 catalog: c.catalog || null };
      });
      var here = {};
      parts.forEach(function (p) { here[p.name] = true; });
      Object.keys(hidden).forEach(function (n) { if (!here[n]) delete hidden[n]; });
      selected = selected.filter(function (n) { return here[n]; });
      push();
      render();
    }

    function groups() {
      var shown = parts.filter(function (p) { return !filter || p.name.toLowerCase().indexOf(filter) >= 0; });
      if (grouping === 'none') return [{ key: 'all', label: 'All parts', parts: shown, flat: true }];
      var table = grouping === 'type' ? TYPES : ROLES, out = [];
      table.forEach(function (entry) {
        var members = shown.filter(function (p) { return (grouping === 'type' ? typeOf(p) : p.role) === entry[0]; });
        if (members.length) out.push({ key: grouping + ':' + entry[0], label: entry[1], parts: members });
      });
      var rest = shown.filter(function (p) {
        return grouping === 'role' && ROLES.every(function (entry) { return entry[0] !== p.role; });
      });
      if (rest.length) out.push({ key: grouping + ':other', label: 'No role', parts: rest });
      return out;
    }
    function isFolded(group) {
      if (group.flat) return false;
      if (Object.prototype.hasOwnProperty.call(folded, group.key)) return !!folded[group.key];
      return group.key === 'type:hardware';
    }

    function eyeButton(visible, title) {
      var button = el('button', 'icon-button outliner-eye');
      button.type = 'button';
      button.innerHTML = visible ? EYE : EYE_OFF;
      button.title = title;
      button.setAttribute('aria-label', title);
      button.setAttribute('aria-pressed', visible ? 'true' : 'false');
      return button;
    }
    function render() {
      var key = JSON.stringify([parts, hidden, selected, filter, grouping, folded]);
      if (key === drawnKey) return;
      drawnKey = key;
      var tree = options.tree, scroll = tree.scrollTop;
      tree.textContent = '';
      options.group.value = grouping;
      var chosen = {};
      selected.forEach(function (n) { chosen[n] = true; });
      groups().forEach(function (group) {
        var item = el('li', 'outliner-group');
        item.dataset.group = group.key;
        if (!group.flat) {
          var shut = isFolded(group), anyShown = group.parts.some(function (p) { return !hidden[p.name]; });
          var head = el('div', 'outliner-row outliner-head');
          var fold = el('button', 'icon-button outliner-fold');
          fold.type = 'button';
          fold.innerHTML = FOLD;
          fold.setAttribute('aria-expanded', shut ? 'false' : 'true');
          fold.title = shut ? 'Unfold' : 'Fold';
          fold.setAttribute('aria-label', (shut ? 'Unfold ' : 'Fold ') + group.label);
          fold.addEventListener('click', function () { folded[group.key] = !shut; writeStored('cadex.outliner.folded', JSON.stringify(folded)); render(); });
          var eye = eyeButton(anyShown, (anyShown ? 'Hide ' : 'Show ') + group.label + ' (Ctrl: isolate)');
          eye.addEventListener('click', function (event) {
            var members = group.parts.map(function (p) { return p.name; });
            if (event.ctrlKey || event.metaKey) isolate(members);
            else setVisible(members, !anyShown);
          });
          head.appendChild(fold);
          head.appendChild(eye);
          var label = el('span', 'outliner-name', group.label);
          head.appendChild(label);
          head.appendChild(el('span', 'outliner-count', String(group.parts.length)));
          head.addEventListener('click', function (event) {
            if (event.target.closest('button')) return;
            var members = group.parts.map(function (p) { return p.name; });
            setSelection(event.shiftKey || event.ctrlKey || event.metaKey ? selected.concat(members) : members);
          });
          item.appendChild(head);
          if (shut) { tree.appendChild(item); return; }
        }
        var list = el('ul', 'outliner-parts');
        group.parts.forEach(function (part) {
          var row = el('li', 'outliner-row outliner-part');
          row.dataset.part = part.name;
          row.setAttribute('aria-selected', chosen[part.name] ? 'true' : 'false');
          row.dataset.hidden = hidden[part.name] ? 'true' : 'false';
          var eye = eyeButton(!hidden[part.name], (hidden[part.name] ? 'Show ' : 'Hide ') + part.name + ' (Ctrl: isolate)');
          eye.addEventListener('click', function (event) {
            if (event.ctrlKey || event.metaKey) isolate([part.name]);
            else setVisible([part.name], !!hidden[part.name]);
          });
          var swatch = el('span', 'outliner-swatch');
          swatch.style.background = part.color || 'var(--ink-2)';
          row.appendChild(eye);
          row.appendChild(swatch);
          row.appendChild(el('span', 'outliner-name', part.name));
          row.appendChild(el('span', 'outliner-meta', detailOf(part)));
          row.title = part.name + ' — ' + detailOf(part);
          row.addEventListener('click', function (event) { if (!event.target.closest('button')) clickPart(part.name, event); });
          row.addEventListener('dblclick', function (event) { if (!event.target.closest('button')) frame([part.name]); });
          list.appendChild(row);
        });
        item.appendChild(list);
        tree.appendChild(item);
      });
      if (!parts.length) tree.appendChild(el('li', 'outliner-empty muted', 'No parts: the model has not loaded, or has none.'));
      else if (!tree.querySelector('.outliner-group')) tree.appendChild(el('li', 'outliner-empty muted', 'No part matches the filter.'));
      tree.scrollTop = scroll;
      summary();
    }
    function summary() {
      var hiddenCount = Object.keys(hidden).length, line;
      if (selected.length === 1) {
        var part = parts.filter(function (p) { return p.name === selected[0]; })[0];
        line = part ? part.name + ' · ' + detailOf(part) : '';
      } else {
        line = parts.length + ' part' + (parts.length === 1 ? '' : 's') + (hiddenCount ? ' · ' + hiddenCount + ' hidden' : '') +
               (selected.length ? ' · ' + selected.length + ' selected' : '');
      }
      options.summary.textContent = parts.length ? line : '';
      options.showAll.disabled = !hiddenCount;
    }

    // -- the operations -----------------------------------------------------------------
    function setVisible(list, visible) {
      list.forEach(function (n) { if (visible) delete hidden[n]; else hidden[n] = true; });
      // A part hidden leaves the selection: what cannot be seen is not acted on.
      if (!visible) selected = selected.filter(function (n) { return !hidden[n]; });
      push(); render();
      return Object.keys(hidden);
    }
    function isolate(list) {
      var keep = {};
      list.forEach(function (n) { keep[n] = true; });
      hidden = {};
      parts.forEach(function (p) { if (!keep[p.name]) hidden[p.name] = true; });
      selected = selected.filter(function (n) { return keep[n]; });
      push(); render();
      return Object.keys(hidden);
    }
    function showAll() { hidden = {}; push(); render(); return []; }
    function setSelection(list) {
      var here = {}, seen = {};
      parts.forEach(function (p) { here[p.name] = true; });
      selected = (list || []).filter(function (n) { return here[n] && !hidden[n] && !seen[n] && (seen[n] = true); });
      anchor = selected.length ? selected[selected.length - 1] : null;
      push(); render();
      reveal();
      return selected.slice();
    }
    function clickPart(name, event) {
      if (event.shiftKey && anchor) {
        // A run, in the order the tree shows it.
        var order = [];
        groups().forEach(function (g) { if (!isFolded(g)) g.parts.forEach(function (p) { order.push(p.name); }); });
        var a = order.indexOf(anchor), b = order.indexOf(name);
        if (a >= 0 && b >= 0) {
          var run = order.slice(Math.min(a, b), Math.max(a, b) + 1), keep = anchor;
          setSelection(selected.concat(run.filter(function (n) { return selected.indexOf(n) < 0; })));
          anchor = keep;
          return;
        }
      }
      if (event.ctrlKey || event.metaKey || event.shiftKey) {
        var at = selected.indexOf(name);
        setSelection(at >= 0 ? selected.filter(function (n) { return n !== name; }) : selected.concat([name]));
      } else setSelection([name]);
    }
    // A click on the viewport: a solid selects its row, empty space clears (unless adding).
    function pick(name, add) {
      if (!name) { if (!add) setSelection([]); return selected.slice(); }
      if (!add) return setSelection([name]);
      var at = selected.indexOf(name);
      return setSelection(at >= 0 ? selected.filter(function (n) { return n !== name; }) : selected.concat([name]));
    }
    // The selected row scrolls into view, its group unfolding.
    function reveal() {
      var last = selected[selected.length - 1];
      if (!last) return;
      var shut = groups().filter(function (g) { return isFolded(g) && g.parts.some(function (p) { return p.name === last; }); })[0];
      if (shut) { folded[shut.key] = false; writeStored('cadex.outliner.folded', JSON.stringify(folded)); render(); }
      var row = options.tree.querySelector('.outliner-part[data-part="' + (window.CSS && CSS.escape ? CSS.escape(last) : last) + '"]');
      if (row && row.scrollIntoView) row.scrollIntoView({ block: 'nearest' });
    }
    function frame(list) {
      var v = viewer();
      if (!v) return false;
      var visible = (list && list.length ? list : names()).filter(function (n) { return !hidden[n]; });
      return visible.length ? v.fitTo(visible) : false;
    }
    function setGrouping(name) {
      if (GROUPINGS.indexOf(name) < 0) return grouping;
      grouping = name;
      writeStored('cadex.outliner.group', name);
      render();
      return grouping;
    }

    // -- wiring --------------------------------------------------------------------------
    options.filter.addEventListener('input', function () { filter = options.filter.value.trim().toLowerCase(); render(); });
    options.group.addEventListener('change', function () { setGrouping(options.group.value); });
    options.showAll.addEventListener('click', showAll);
    [options.tree, options.scope].forEach(function (node) {
      node.addEventListener('pointerenter', function () { over = true; });
      node.addEventListener('pointerleave', function () { over = false; });
    });
    document.addEventListener('keydown', function (event) {
      var target = event.target, typing = target && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName));
      if (typing || !parts.length || (!over && !options.tree.contains(document.activeElement))) return;
      var key = event.key.toLowerCase(), done = true;
      if (key === 'h' && event.altKey) showAll();
      else if (key === 'h' && event.shiftKey) { if (selected.length) isolate(selected); }
      else if (key === 'h' && !event.ctrlKey && !event.metaKey) { if (selected.length) setVisible(selected.slice(), false); }
      else if (key === 'f' && !event.ctrlKey && !event.metaKey && !event.altKey) frame(selected);
      else if (key === 'escape' && selected.length) setSelection([]);
      else done = false;
      if (done) event.preventDefault();
    });
    render();

    return {
      setModel: setModel, render: render, pick: pick, select: setSelection, setVisible: setVisible,
      hide: function (list) { return setVisible(list || [], false); }, show: function (list) { return setVisible(list || [], true); },
      isolate: isolate, showAll: showAll, frame: frame, setGrouping: setGrouping,
      state: function () {
        return { parts: names(), hidden: Object.keys(hidden), selected: selected.slice(), grouping: grouping, filter: filter,
                 groups: groups().map(function (g) { return { key: g.key, label: g.label, count: g.parts.length, folded: isFolded(g) }; }) };
      }
    };
  }

  window.CadexOutliner = { create: create, groupings: GROUPINGS.slice() };
})();
