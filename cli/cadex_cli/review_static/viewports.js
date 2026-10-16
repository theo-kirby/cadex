// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// More than one of an editor at once (ADR-729; docs/DASHBOARD.md §12): the pieces review.js
// builds the copies from.
//
//   group()      every 3D viewport as one viewer: what the model is (load, ghost, poses, the
//                hidden and selected parts, the heat) goes to all of them, and a viewport added
//                later is brought up to date; what a view is (its camera, style and lighting) is
//                each one's own, and a question about it is asked of the first. Follow is each
//                view's own: followTo moves only the cameras that follow.
//   copy()       an editor's markup copied from its pristine template: every id becomes a
//                data-ref, so the copy carries no id of its own and the page's hooks still name
//                the first.
//   mirror()     a copy's shared controls (the source, the scrubbers, the status lines) kept as
//                the first's are, and worked through the first's own: its scrubber moves the
//                first's, so there is one timeline whichever is touched.
(function () {
  'use strict';

  // What the model is: sent to every viewer, and replayed onto one added later.
  var MODEL = ['clear', 'load', 'loadGhost', 'setGhost', 'setPoses', 'setHidden', 'select', 'setHeat',
               'setMeshLines', 'setReflections', 'setOcclusion', 'setDetail', 'setProxies', 'setTerrain', 'setSection', 'setLines'];
  var EVERY = MODEL.concat(['draw', 'highlight', 'setOnPick', 'showProxies', 'showLines']);

  // A fetch that reads each URL once for every viewer that asks: the meshes come down once.
  function shared(fetchImpl) {
    var cache = {};
    return function (url) {
      if (!cache[url]) {
        cache[url] = fetchImpl(url).then(function (r) {
          if (!r.ok) return { ok: false, status: r.status };
          return r.arrayBuffer().then(function (buffer) { return { ok: true, status: r.status, buffer: buffer }; });
        });
      }
      return cache[url].then(function (got) {
        return { ok: got.ok, status: got.status, arrayBuffer: function () { return Promise.resolve(got.buffer.slice(0)); } };
      });
    };
  }

  function group() {
    var views = [], last = {}, model = null;
    function each(name, args) {
      var out;
      views.forEach(function (v, i) {
        var f = v.viewer[name];
        if (typeof f !== 'function') return;
        var r = f.apply(v.viewer, args);
        if (i === 0) out = r;
      });
      return out;
    }
    var facade = {};
    EVERY.forEach(function (name) {
      facade[name] = function () {
        var args = Array.prototype.slice.call(arguments);
        if (name === 'load' || name === 'loadGhost') {
          var fetchImpl = shared(args[1] || window.fetch.bind(window));
          args = [args[0], fetchImpl].concat(args.slice(2));
          if (name === 'load') { model = { name: name, args: args }; delete last.loadGhost; delete last.setGhost; }
          else last.loadGhost = args;
          return Promise.all(views.map(function (v) { return v.viewer[name].apply(v.viewer, args); })).then(function (all) { return all[0]; });
        }
        if (name === 'clear') { model = { name: name, args: args }; delete last.loadGhost; delete last.setGhost; }
        else if (MODEL.indexOf(name) >= 0) { last[name] = args; if (name === 'setGhost') delete last.loadGhost; }
        else if (name === 'setOnPick') last.setOnPick = args;
        return each(name, args);
      };
    });
    // The follow camera: each view that follows moves with the point; the rest let go.
    facade.followTo = function (point, snap) {
      var out = null;
      views.forEach(function (v, i) {
        var r = v.follow && point ? v.viewer.followTo(point, snap) : v.viewer.followTo(null);
        if (i === 0) out = r;
      });
      return out;
    };
    // Everything else is the first view's.
    var proxy = typeof Proxy === 'function' ? new Proxy(facade, {
      get: function (target, name) {
        if (name in target) return target[name];
        var first = views[0] && views[0].viewer, value = first && first[name];
        return typeof value === 'function' ? value.bind(first) : value;
      }
    }) : facade;
    return {
      viewer: proxy,
      views: function () { return views.slice(); },
      first: function () { return views[0] || null; },
      // A view joins showing what the others show: the model, then its ghost, poses, parts and heat.
      add: function (view) {
        views.push(view);
        var v = view.viewer;
        if (views.length === 1) return Promise.resolve(view);
        if (last.setOnPick) v.setOnPick.apply(v, last.setOnPick);
        var ready = model ? Promise.resolve(v[model.name].apply(v, model.args)) : Promise.resolve();
        return ready.then(function () {
          if (last.loadGhost) return v.loadGhost.apply(v, last.loadGhost);
          if (last.setGhost) v.setGhost.apply(v, last.setGhost);
        }).then(function () {
          MODEL.forEach(function (name) {
            if (name === 'clear' || name === 'load' || name === 'loadGhost' || name === 'setGhost' || !last[name]) return;
            if (typeof v[name] === 'function') v[name].apply(v, last[name]);
          });
          return view;
        }).catch(function () { return view; });
      }
    };
  }

  // -- copies of an editor's markup -----------------------------------------------------------
  function copy(template) {
    var home = template.cloneNode(true);
    home.removeAttribute('id');
    home.querySelectorAll('[id]').forEach(function (node) { node.setAttribute('data-ref', node.id); node.removeAttribute('id'); });
    // A label's `for` named an id the copy no longer has.
    home.querySelectorAll('label[for]').forEach(function (label) { label.removeAttribute('for'); });
    return { home: home, tools: home.querySelector('.editor-tools'), body: home.querySelector('.editor-body') };
  }
  // An element of an editor, the first's by id or a copy's by its data-ref.
  function ref(root, name) {
    if (!root) return null;
    if (root.id === name || root.getAttribute && root.getAttribute('data-ref') === name) return root;
    return root.querySelector('#' + name + ', [data-ref="' + name + '"]');
  }

  // -- shared controls ------------------------------------------------------------------------
  var mirrors = [];
  function pairs(a, b, skip, out) {
    out.push([a, b]);
    if (a.tagName === 'SELECT') return out;   // its options are copied whole
    var ka = a.children, kb = b.children;
    for (var i = 0; i < ka.length && i < kb.length; i++) {
      if (skip && kb[i].matches(skip)) continue;
      pairs(ka[i], kb[i], skip, out);
    }
    return out;
  }
  function sync(m, full) {
    m.pairs.forEach(function (pair) {
      var a = pair[0], b = pair[1];
      Array.prototype.forEach.call(a.attributes, function (at) {
        if (at.name === 'id' || at.name === 'for') return;
        if (b.getAttribute(at.name) !== at.value) b.setAttribute(at.name, at.value);
      });
      Array.prototype.slice.call(b.attributes).forEach(function (at) {
        if (at.name !== 'data-ref' && !a.hasAttribute(at.name)) b.removeAttribute(at.name);
      });
      if (b.hidden !== a.hidden) b.hidden = a.hidden;
      if (a.tagName === 'SELECT') {
        if (full && b.innerHTML !== a.innerHTML) b.innerHTML = a.innerHTML;
        if (b.value !== a.value) b.value = a.value;
      } else if (a.tagName === 'INPUT') {
        if (document.activeElement !== b && b.value !== a.value) b.value = a.value;
      } else if (!a.children.length && b.textContent !== a.textContent) b.textContent = a.textContent;
    });
  }
  var frame = 0, running = false;
  function tick() {
    frame += 1;
    mirrors = mirrors.filter(function (m) { return m.alive(); });
    mirrors.forEach(function (m) { if (m.copy.isConnected) sync(m, frame % 10 === 0); });
    running = mirrors.length > 0;
    if (running) requestAnimationFrame(tick);
  }
  // Keep `copy` as `first` is, every frame; `skip` names the copy's elements that are its own.
  function mirror(first, copyRoot, skip, alive) {
    var m = { first: first, copy: copyRoot, pairs: pairs(first, copyRoot, skip, []), alive: alive || function () { return true; } };
    sync(m, true);
    // A copy's control works the first's.
    m.pairs.forEach(function (pair) {
      var a = pair[0], b = pair[1];
      if (b.tagName === 'INPUT' || b.tagName === 'SELECT') {
        ['input', 'change'].forEach(function (type) {
          b.addEventListener(type, function () { a.value = b.value; a.dispatchEvent(new Event(type, { bubbles: true })); });
        });
      } else if (b.tagName === 'BUTTON') {
        b.addEventListener('click', function (e) { e.stopPropagation(); a.click(); });
      }
    });
    mirrors.push(m);
    if (!running) { running = true; requestAnimationFrame(tick); }
    return m;
  }

  window.CadexViewports = { group: group, copy: copy, ref: ref, mirror: mirror };
})();
