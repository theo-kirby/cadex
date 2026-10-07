// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The screen as areas (ADR-534), after Blender's: the window is tiled by
// areas, each showing one editor. A gutter between two areas resizes them;
// an area's header picks its editor, splits it, maximizes it or closes it;
// dragging a header onto another area docks it beside that area (an edge) or
// swaps the two (the middle). Each editor is shown at most once, so picking
// one shown elsewhere swaps the two areas' editors. An area may also be
// empty, showing only its editor picker, so a preset can have more areas
// than there are editors (ADR-573).
//
// A preset (ADR-573) replaces the whole tree in one step: single, side by
// side, stacked, 2 over 1, 1 over 2, three columns, three rows or quad, its
// areas filled with the editors in their order and any left over empty.
//
// The layout is a tree: a split {dir: 'row'|'col', sizes, children} or an
// area {editor}. It is this browser's own, kept in localStorage; a browser
// that refuses storage gets the default every visit. Below 700 px there is
// no room to tile, so one editor fills the screen and a tab bar picks it.
(function () {
  'use strict';

  var MIN_PX = 120, DRAG_PX = 6, EMPTY = 'empty';
  // Each preset's shape: a slot is an area, filled in reading order.
  var PRESETS = {
    single: 0,
    side: { dir: 'row', children: [0, 0] },
    stacked: { dir: 'col', children: [0, 0] },
    two_over_one: { dir: 'col', children: [{ dir: 'row', children: [0, 0] }, 0] },
    one_over_two: { dir: 'col', children: [0, { dir: 'row', children: [0, 0] }] },
    columns: { dir: 'row', children: [0, 0, 0] },
    rows: { dir: 'col', children: [0, 0, 0] },
    quad: { dir: 'col', children: [{ dir: 'row', children: [0, 0] }, { dir: 'row', children: [0, 0] }] }
  };
  var ZONES = { center: 'Swap', left: 'Dock left', right: 'Dock right', top: 'Dock above', bottom: 'Dock below' };
  var ICONS = {
    row: '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="1.5" y="2.5" width="13" height="11" rx="1.5"/><path d="M8 2.5v11"/></svg>',
    col: '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="1.5" y="2.5" width="13" height="11" rx="1.5"/><path d="M1.5 8h13"/></svg>',
    max: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 6V2h4M10 2h4v4M14 10v4h-4M6 14H2v-4"/></svg>',
    close: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8"/></svg>'
  };

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }
  function iconButton(name, title, onClick) {
    var button = el('button', 'icon-button area-' + name);
    button.type = 'button';
    button.title = title;
    button.setAttribute('aria-label', title);
    button.innerHTML = ICONS[name];
    button.addEventListener('click', onClick);
    return button;
  }
  function grow(share) { return (share * 1000).toFixed(2) + ' 1 0'; }
  function sum(list) { return list.reduce(function (a, b) { return a + b; }, 0); }

  function create(options) {
    var root = options.root, shelf = options.shelf, editors = options.editors, order = options.order;
    var storageKey = options.storageKey, onChange = options.onChange || function () {};
    var narrow = window.matchMedia('(max-width: 699px)');
    var seq = 0, tree = null, maximized = null, tab = order[0], hovered = null;

    function uid() { seq += 1; return 'a' + seq; }
    function stamp(node) {
      node.id = uid();
      if (node.children) node.children.forEach(stamp);
      return node;
    }
    function strip(node) {
      return node.editor ? { editor: node.editor }
        : { dir: node.dir, sizes: node.sizes.map(function (s) { return Number(s.toFixed(4)); }), children: node.children.map(strip) };
    }
    function valid(node, seen) {
      if (!node || typeof node !== 'object') return false;
      if (node.editor === EMPTY) return true;
      if (typeof node.editor === 'string') {
        if (!editors[node.editor] || seen[node.editor]) return false;
        seen[node.editor] = true;
        return true;
      }
      return (node.dir === 'row' || node.dir === 'col') && Array.isArray(node.children) && node.children.length >= 2
        && Array.isArray(node.sizes) && node.sizes.length === node.children.length
        && node.sizes.every(function (s) { return typeof s === 'number' && s > 0 && isFinite(s); })
        && node.children.every(function (child) { return valid(child, seen); });
    }
    function load() {
      try {
        var stored = JSON.parse(localStorage.getItem(storageKey));
        if (valid(stored, {})) return normalize(stamp(stored));
      } catch (_) { /* the default, below */ }
      return normalize(stamp(JSON.parse(JSON.stringify(options.defaultLayout))));
    }
    function save() {
      try { localStorage.setItem(storageKey, JSON.stringify(strip(tree))); } catch (_) { /* this visit only */ }
    }

    function find(id, node, parent) {
      node = node || tree;
      if (node.id === id) return { node: node, parent: parent || null };
      for (var i = 0; node.children && i < node.children.length; i++) {
        var found = find(id, node.children[i], node);
        if (found) return found;
      }
      return null;
    }
    function areas(node, out) {
      node = node || tree; out = out || [];
      if (node.editor) out.push(node);
      else node.children.forEach(function (child) { areas(child, out); });
      return out;
    }
    function shown() { return areas().map(function (area) { return area.editor; }).filter(function (type) { return type !== EMPTY; }); }
    function hidden() { var on = shown(); return order.filter(function (type) { return on.indexOf(type) < 0; }); }

    // A split of one child is that child; a split inside a split of the same
    // direction is folded into it, so the tree stays as shallow as it looks.
    function normalize(node) {
      if (node.editor) return node;
      var children = [], sizes = [];
      node.children.map(normalize).forEach(function (child, i) {
        if (!child.editor && child.dir === node.dir) {
          var total = sum(child.sizes);
          child.children.forEach(function (grandchild, j) {
            children.push(grandchild); sizes.push(node.sizes[i] * child.sizes[j] / total);
          });
        } else { children.push(child); sizes.push(node.sizes[i]); }
      });
      // Shares sum to one, so a flex-grow below one never leaves the split short.
      var total = sum(sizes);
      node.children = children; node.sizes = sizes.map(function (size) { return size / total; });
      return children.length === 1 ? children[0] : node;
    }
    function detach(id) {
      var found = find(id);
      if (!found || !found.parent) return false;
      var index = found.parent.children.indexOf(found.node);
      found.parent.children.splice(index, 1);
      found.parent.sizes.splice(index, 1);
      tree = normalize(tree);
      return true;
    }
    function insertBeside(targetId, node, zone) {
      var dir = zone === 'left' || zone === 'right' ? 'row' : 'col', after = zone === 'right' || zone === 'bottom';
      var found = find(targetId), target = found.node, parent = found.parent;
      if (parent && parent.dir === dir) {
        var index = parent.children.indexOf(target), half = parent.sizes[index] / 2;
        parent.sizes[index] = half;
        parent.children.splice(after ? index + 1 : index, 0, node);
        parent.sizes.splice(after ? index + 1 : index, 0, half);
      } else {
        var split = { id: uid(), dir: dir, sizes: [1, 1], children: after ? [target, node] : [node, target] };
        if (!parent) tree = split;
        else parent.children[parent.children.indexOf(target)] = split;
      }
      tree = normalize(tree);
    }
    function commit() { save(); render(); onChange(); }

    // -- the operations ------------------------------------------------------
    function setEditor(id, type) {
      var found = find(id);
      if (!found || !found.node.editor || !(editors[type] || type === EMPTY) || found.node.editor === type) return false;
      var other = type === EMPTY ? null : areas().filter(function (area) { return area.editor === type; })[0];
      if (other) other.editor = found.node.editor;
      found.node.editor = type;
      commit();
      return true;
    }
    function split(id, dir, type) {
      type = type || hidden()[0];
      if (!type || shown().indexOf(type) >= 0 || !find(id)) return false;
      insertBeside(id, { id: uid(), editor: type }, dir === 'row' ? 'right' : 'bottom');
      commit();
      return true;
    }
    function close(id) {
      if (areas().length < 2 || !find(id)) return false;
      if (maximized === id) maximized = null;
      detach(id);
      commit();
      return true;
    }
    function move(sourceId, targetId, zone) {
      var source = find(sourceId), target = find(targetId);
      if (!source || !target || sourceId === targetId) return false;
      if (zone === 'center') {
        var editor = source.node.editor;
        source.node.editor = target.node.editor;
        target.node.editor = editor;
      } else {
        detach(sourceId);
        insertBeside(targetId, { id: uid(), editor: source.node.editor }, zone);
      }
      commit();
      return true;
    }
    function maximize(id) {
      maximized = maximized === id || !find(id) ? null : id;
      render(); onChange();
      return maximized;
    }
    // Bring an editor into view: its tab on a phone; at desk, in an empty
    // area, or else beside the largest area, when it is not already shown.
    function show(type) {
      if (!editors[type]) return false;
      if (narrow.matches) { tab = type; render(); onChange(); return true; }
      if (shown().indexOf(type) >= 0) return true;
      var empty = areas().filter(function (area) { return area.editor === EMPTY; })[0];
      if (empty) return setEditor(empty.id, type);
      var largest = null, best = -1;
      root.querySelectorAll('.area').forEach(function (node) {
        var r = node.getBoundingClientRect();
        if (r.width * r.height > best) { best = r.width * r.height; largest = node; }
      });
      var rect = largest ? largest.getBoundingClientRect() : { width: 1, height: 0 };
      return split(largest ? largest.dataset.area : areas()[0].id, rect.width >= rect.height ? 'row' : 'col', type);
    }
    // Fill a preset's slots with the editors in order; past the last editor
    // a slot is an empty area. Shares are equal.
    function preset(name) {
      if (!Object.prototype.hasOwnProperty.call(PRESETS, name)) return false;
      var next = 0;
      function fill(shape) {
        if (!shape) { var type = order[next] || EMPTY; next += 1; return { editor: type }; }
        return { dir: shape.dir, sizes: shape.children.map(function () { return 1; }), children: shape.children.map(fill) };
      }
      tree = normalize(stamp(fill(PRESETS[name])));
      maximized = null;
      commit();
      return true;
    }
    function reset() {
      try { localStorage.removeItem(storageKey); } catch (_) { /* nothing kept */ }
      tree = stamp(JSON.parse(JSON.stringify(options.defaultLayout)));
      maximized = null;
      render(); onChange();
    }

    // -- drawing -------------------------------------------------------------
    function shelve() {
      order.forEach(function (type) {
        var editor = editors[type];
        editor.home.appendChild(editor.tools);
        editor.home.appendChild(editor.body);
      });
    }
    function render() {
      shelve();
      root.textContent = '';
      root.dataset.mode = narrow.matches ? 'tabs' : 'areas';
      if (narrow.matches) { renderTabs(); return; }
      var top = (maximized && find(maximized)) ? find(maximized).node : tree;
      if (top === tree) maximized = null;
      root.dataset.maximized = maximized ? 'true' : 'false';
      root.appendChild(build(top, null));
    }
    function build(node) {
      if (node.editor) return buildArea(node);
      var box = el('div', 'split split-' + node.dir);
      box.dataset.split = node.id;
      node.children.forEach(function (child, i) {
        if (i) box.appendChild(gutter(node, i, box));
        var part = build(child);
        part.style.flex = grow(node.sizes[i]);
        box.appendChild(part);
      });
      return box;
    }
    function typeSelect(current, onPick) {
      var select = el('select', 'area-type');
      select.setAttribute('aria-label', 'Editor');
      order.concat(current === EMPTY ? [EMPTY] : []).forEach(function (type) {
        var option = el('option', '', type === EMPTY ? 'Empty' : editors[type].title);
        option.value = type;
        select.appendChild(option);
      });
      select.value = current;
      select.addEventListener('change', function () { onPick(select.value); });
      return select;
    }
    // An empty area has a picker and a line saying so, and nothing to move.
    function emptyEditor() {
      var body = el('div', 'editor-body area-empty');
      body.appendChild(el('p', 'muted', 'Empty area: pick an editor from the menu at the top left.'));
      return { tools: el('div', 'editor-tools'), body: body };
    }
    function buildArea(node) {
      var editor = node.editor === EMPTY ? emptyEditor() : editors[node.editor];
      var area = el('section', 'area');
      area.dataset.area = node.id;
      area.dataset.editor = node.editor;
      var header = el('header', 'area-header');
      var grip = el('span', 'area-grip');
      grip.title = 'Drag onto another area to move this one';
      grip.setAttribute('aria-hidden', 'true');
      header.appendChild(grip);
      header.appendChild(typeSelect(node.editor, function (type) { setEditor(node.id, type); }));
      header.appendChild(editor.tools);
      var actions = el('span', 'area-actions');
      var free = hidden().length > 0, alone = areas().length < 2;
      var splitRow = iconButton('row', 'Split left and right', function () { split(node.id, 'row'); });
      var splitCol = iconButton('col', 'Split top and bottom', function () { split(node.id, 'col'); });
      splitRow.disabled = splitCol.disabled = !free || !!maximized;
      var max = iconButton('max', maximized ? 'Restore the layout (Ctrl+Space)' : 'Maximize (Ctrl+Space)', function () { maximize(node.id); });
      max.setAttribute('aria-pressed', maximized ? 'true' : 'false');
      var shut = iconButton('close', 'Close this area', function () { close(node.id); });
      shut.disabled = alone || !!maximized;
      [splitRow, splitCol, max, shut].forEach(function (button) { actions.appendChild(button); });
      header.appendChild(actions);
      area.appendChild(header);
      area.appendChild(editor.body);
      area.addEventListener('pointerenter', function () { hovered = node.id; });
      dragHeader(header, node);
      return area;
    }
    function renderTabs() {
      var editor = editors[tab];
      var area = el('section', 'area area-tab');
      area.dataset.editor = tab;
      var header = el('header', 'area-header');
      header.appendChild(el('span', 'area-title', editor.title));
      header.appendChild(editor.tools);
      area.appendChild(header);
      area.appendChild(editor.body);
      var tabs = el('nav', 'tabs');
      tabs.setAttribute('aria-label', 'Editors');
      order.forEach(function (type) {
        var button = el('button', 'tab', editors[type].short || editors[type].title);
        button.type = 'button';
        button.dataset.editor = type;
        button.setAttribute('aria-pressed', type === tab ? 'true' : 'false');
        button.addEventListener('click', function () { tab = type; render(); onChange(); });
        tabs.appendChild(button);
      });
      root.appendChild(area);
      root.appendChild(tabs);
    }

    // A gutter moves the boundary between its two neighbours and nothing else.
    function gutter(node, i, box) {
      var bar = el('div', 'gutter gutter-' + node.dir);
      bar.setAttribute('role', 'separator');
      bar.setAttribute('aria-orientation', node.dir === 'row' ? 'vertical' : 'horizontal');
      bar.addEventListener('pointerdown', function (event) {
        if (event.button !== 0) return;
        event.preventDefault();
        bar.setPointerCapture(event.pointerId);
        var parts = Array.prototype.filter.call(box.children, function (child) { return !child.classList.contains('gutter'); });
        var a = parts[i - 1], b = parts[i], across = node.dir === 'row';
        var start = across ? event.clientX : event.clientY;
        var sizeA = across ? a.getBoundingClientRect().width : a.getBoundingClientRect().height;
        var sizeB = across ? b.getBoundingClientRect().width : b.getBoundingClientRect().height;
        var pair = node.sizes[i - 1] + node.sizes[i];
        root.classList.add('resizing');
        function moved(e) {
          var delta = (across ? e.clientX : e.clientY) - start;
          var nextA = Math.max(MIN_PX, Math.min(sizeA + sizeB - MIN_PX, sizeA + delta));
          node.sizes[i - 1] = pair * nextA / (sizeA + sizeB);
          node.sizes[i] = pair - node.sizes[i - 1];
          a.style.flex = grow(node.sizes[i - 1]);
          b.style.flex = grow(node.sizes[i]);
        }
        function lifted() {
          bar.removeEventListener('pointermove', moved);
          bar.removeEventListener('pointerup', lifted);
          bar.removeEventListener('pointercancel', lifted);
          root.classList.remove('resizing');
          save(); onChange();
        }
        bar.addEventListener('pointermove', moved);
        bar.addEventListener('pointerup', lifted);
        bar.addEventListener('pointercancel', lifted);
      });
      return bar;
    }

    // Dragging a header: the drop hint shows where the area would land.
    function zoneAt(rect, x, y) {
      var fx = (x - rect.left) / rect.width, fy = (y - rect.top) / rect.height;
      if (fx > 0.3 && fx < 0.7 && fy > 0.3 && fy < 0.7) return 'center';
      var edges = { left: fx, right: 1 - fx, top: fy, bottom: 1 - fy };
      return Object.keys(edges).sort(function (p, q) { return edges[p] - edges[q]; })[0];
    }
    function hintBox(rect, zone) {
      var box = { left: rect.left, top: rect.top, width: rect.width, height: rect.height };
      if (zone === 'left' || zone === 'right') box.width = rect.width / 2;
      if (zone === 'right') box.left = rect.left + rect.width / 2;
      if (zone === 'top' || zone === 'bottom') box.height = rect.height / 2;
      if (zone === 'bottom') box.top = rect.top + rect.height / 2;
      return box;
    }
    function dragHeader(header, node) {
      header.addEventListener('pointerdown', function (event) {
        var target = event.target;
        if (event.button !== 0 || maximized) return;
        if (target !== header && !target.classList.contains('area-grip') && !target.classList.contains('editor-tools')) return;
        var startX = event.clientX, startY = event.clientY, dragging = false, drop = null, hint = null;
        header.setPointerCapture(event.pointerId);
        function moved(e) {
          if (!dragging) {
            if (Math.hypot(e.clientX - startX, e.clientY - startY) < DRAG_PX) return;
            dragging = true;
            root.classList.add('dragging');
            hint = el('div', 'drop-hint');
            hint.appendChild(el('span', 'drop-label'));
            document.body.appendChild(hint);
          }
          var under = document.elementFromPoint(e.clientX, e.clientY);
          var area = under && under.closest ? under.closest('.area') : null;
          if (!area || !root.contains(area) || area.dataset.area === node.id) { drop = null; hint.hidden = true; return; }
          var rect = area.getBoundingClientRect(), zone = zoneAt(rect, e.clientX, e.clientY), box = hintBox(rect, zone);
          drop = { id: area.dataset.area, zone: zone };
          hint.hidden = false;
          hint.dataset.zone = zone;
          hint.firstChild.textContent = ZONES[zone];
          hint.style.left = box.left + 'px'; hint.style.top = box.top + 'px';
          hint.style.width = box.width + 'px'; hint.style.height = box.height + 'px';
        }
        function lifted() {
          header.removeEventListener('pointermove', moved);
          header.removeEventListener('pointerup', lifted);
          header.removeEventListener('pointercancel', lifted);
          root.classList.remove('dragging');
          if (hint) hint.remove();
          if (dragging && drop) move(node.id, drop.id, drop.zone);
        }
        header.addEventListener('pointermove', moved);
        header.addEventListener('pointerup', lifted);
        header.addEventListener('pointercancel', lifted);
      });
    }

    // Ctrl+Space maximizes the area under the pointer, as in Blender.
    document.addEventListener('keydown', function (event) {
      if (event.code !== 'Space' || !event.ctrlKey || narrow.matches) return;
      var id = maximized || hovered;
      if (!id || !find(id)) return;
      event.preventDefault();
      maximize(id);
    });
    narrow.addEventListener('change', function () { render(); onChange(); });

    tree = load();
    render();
    return {
      render: render, reset: reset, preset: preset, presets: Object.keys(PRESETS), setEditor: setEditor, split: split, close: close, move: move,
      maximize: maximize, show: show,
      tree: function () { return strip(tree); },
      areas: function () { return areas().map(function (area) { return { id: area.id, editor: area.editor }; }); },
      shown: function () { return narrow.matches ? [tab] : (maximized ? [find(maximized).node.editor] : shown()); },
      mode: function () { return narrow.matches ? 'tabs' : 'areas'; }
    };
  }

  window.CadexLayout = { create: create };
})();
