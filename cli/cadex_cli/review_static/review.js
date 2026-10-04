// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The app (ADR-534): three editors tiled by layout.js, after Blender's areas.
//
//   3D viewport  the accepted model or a run's, shaded or hairline, and a
//                run's rollout played back on a timeline;
//   2D viewport  the project's drawings, images, documents and training plots;
//   Settings     the project, its revisions, and the view.
//
// Read-only (ADR-537): the agent working the project changes it, through
// the CLI or `cadex mcp`, and the page follows. Polls /api/project for what
// changed and reloads the model only when what it shows moves.
(function () {
  'use strict';

  // Served alone (`cadex review`) the page is at `/`; served from a projects
  // directory (`cadex app`) it is at `/p/<name>/`, and every request it makes
  // carries that prefix.
  var BASE = (location.pathname.match(/^\/p\/[^/]+(?=\/)/) || [''])[0];
  var POLL_MS = 2000;
  var ORDER = ['view3d', 'view2d', 'settings'];
  // Settings down the left, the two viewports stacked beside it.
  var DEFAULT_LAYOUT = { dir: 'row', sizes: [0.22, 0.78], children: [
    { editor: 'settings' },
    { dir: 'col', sizes: [0.64, 0.36], children: [{ editor: 'view3d' }, { editor: 'view2d' }] }
  ] };
  var STYLES = ['shaded', 'hairline'];
  var state = { review: null, lastOk: null, stale: false, error: null, model: null, viewer: null, layout: null };
  var pendingPoll = null;
  var lastPoll = { project_bytes: 0, ms: 0 };
  var readyResolve;
  var ready = new Promise(function (resolve) { readyResolve = resolve; });

  function $(id) { return document.getElementById(id); }
  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (key) {
      if (key === 'text') node.textContent = attrs[key];
      else if (key.indexOf('data-') === 0) node.setAttribute(key, attrs[key]);
      else node[key] = attrs[key];
    });
    (children || []).forEach(function (child) { node.appendChild(child); });
    return node;
  }
  function short(value) { return value ? String(value).slice(0, 12) : '—'; }
  function fmt(value) {
    if (value == null) return '—';
    if (typeof value === 'number') return Number.isInteger(value) ? String(value) : String(Number(value.toPrecision(5)));
    return String(value);
  }
  function when(stamp) {
    var date = stamp ? new Date(stamp) : null;
    return date && !isNaN(date) ? date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : '';
  }
  function brief(stamp) {
    var date = stamp ? new Date(stamp) : null;
    return date && !isNaN(date) ? date.toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) : '';
  }
  function json(url) {
    return fetch(url, { cache: 'no-store' }).then(function (response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.json();
    });
  }
  // This browser's view preferences; a browser that refuses storage gets the defaults.
  function readPref(key, choices, fallback) {
    try { var value = localStorage.getItem(key); return choices.indexOf(value) >= 0 ? value : fallback; }
    catch (_) { return fallback; }
  }
  function writePref(key, value) { try { localStorage.setItem(key, value); } catch (_) { /* this visit only */ } }
  function token(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function pressed(group, attribute, value) {
    $(group).querySelectorAll('button').forEach(function (button) {
      button.setAttribute('aria-pressed', button.getAttribute(attribute) === value ? 'true' : 'false');
    });
  }

  // -- the top bar ------------------------------------------------------------
  function renderFreshness() {
    var node = $('freshness');
    if (!state.lastOk) { node.dataset.state = 'loading'; node.textContent = 'loading…'; }
    else if (state.stale) { node.dataset.state = 'stale'; node.textContent = 'offline'; node.title = state.error || ''; }
    else { node.dataset.state = 'live'; node.textContent = 'live'; node.title = 'updated ' + state.lastOk.toLocaleTimeString(); }
  }

  function renderHeader() {
    var review = state.review, accepted = review.accepted;
    $('project-name').textContent = review.project;
    document.title = review.project + ' — Cadex';
    var trail = review.revisions || [], current = trail.filter(function (entry) { return entry.revision === accepted.revision; })[0];
    $('accepted-line').textContent = accepted.available
      ? (current ? 'revision ' + current.ordinal : 'revision ' + short(accepted.revision)) + (accepted.updated_at ? ' · ' + when(accepted.updated_at) : '')
      : 'nothing accepted yet';
  }

  // -- Settings: revisions --------------------------------------------------------
  // The trail the agent's accepted writes left, newest first.
  var revisionsKey = null;

  function renderRevisions() {
    var trail = state.review.revisions || [], current = state.review.accepted && state.review.accepted.revision;
    var key = JSON.stringify([trail, current]);
    if (key === revisionsKey) return;
    revisionsKey = key;
    var list = $('revision-list');
    list.textContent = '';
    // The trail comes newest first.
    trail.forEach(function (entry) {
      var here = entry.revision === current;
      list.appendChild(el('li', { value: entry.ordinal, 'data-revision': entry.revision, 'data-ordinal': String(entry.ordinal), 'data-current': String(here) }, [
        el('span', { text: here ? 'current' : brief(entry.saved_at), title: when(entry.saved_at) + ' · ' + entry.revision })
      ]));
    });
  }

  // -- Settings: the project and the view -----------------------------------------
  function loadProjects() {
    if (!BASE) {
      // `cadex review` serves one project: there is nothing to switch to.
      ['project-field', 'project-open', 'project-all'].forEach(function (id) { $(id).hidden = true; });
      return Promise.resolve();
    }
    return json('../../api/projects').then(function (listing) {
      var select = $('project-select'), here = decodeURIComponent(BASE.slice(3));
      var stamp = function (p) { return (p.accepted && p.accepted.updated_at) || ''; };
      select.textContent = '';
      listing.projects.slice().sort(function (a, b) {
        return stamp(b) < stamp(a) ? -1 : stamp(b) > stamp(a) ? 1 : a.name < b.name ? -1 : 1;
      }).forEach(function (project) { select.appendChild(el('option', { value: project.name, text: project.name })); });
      select.value = here;
    }).catch(function () { $('project-field').hidden = true; $('project-open').hidden = true; });
  }
  function openProject() {
    var name = $('project-select').value;
    if (name && name !== decodeURIComponent(BASE.slice(3))) location.href = '../' + encodeURIComponent(name) + '/';
  }
  function renderThemeChoice() { pressed('theme-choice', 'data-choice', window.cadexTheme.choice()); }

  // -- 3D viewport -------------------------------------------------------------------
  // The source is the accepted model or one run's; a run's model plays its
  // rollout when the run kept one.
  var source = 'accepted', sourcesKey = null, modelKey = null, modelLoad = 0, modelAbort = null;
  // A failed load is tried again on a later poll, waiting longer each time.
  var modelFailures = 0, modelRetryAt = 0;
  var renderStyle = readPref('cadex.render', STYLES, 'shaded');

  function renderSources() {
    var runs = (state.review.runs || []).map(function (run) { return run.run; });
    var key = JSON.stringify(runs);
    if (key === sourcesKey) return;
    sourcesKey = key;
    var select = $('view3d-source');
    select.textContent = '';
    select.appendChild(el('option', { value: 'accepted', text: 'Accepted model' }));
    if (runs.length) {
      var group = el('optgroup', { label: 'Runs' });
      runs.forEach(function (run) { group.appendChild(el('option', { value: 'run:' + run, text: run })); });
      select.appendChild(group);
    }
    if (source !== 'accepted' && runs.indexOf(source.slice(4)) < 0) { source = 'accepted'; modelKey = null; }
    select.value = source;
  }

  function setSource(value) {
    source = value;
    $('view3d-source').value = value;
    modelKey = null; modelFailures = 0; modelRetryAt = 0;
    return loadModel();
  }

  // A request that fails on the way (a dropped connection, a 5xx) is tried
  // twice more; one superseded by a newer load is aborted, not finished.
  function fetchRetry(url, signal, tries) {
    return fetch(url, { signal: signal }).then(function (response) {
      if (response.status >= 500) throw new Error('HTTP ' + response.status);
      return response;
    }).catch(function (error) {
      if (signal.aborted || tries <= 0) throw error;
      return new Promise(function (resolve) { setTimeout(resolve, 700); }).then(function () { return fetchRetry(url, signal, tries - 1); });
    });
  }

  function loadModel() {
    var status = $('model-status'), ticket = ++modelLoad;
    var path = source === 'accepted' ? '/api/model/accepted' : '/api/model/run/' + encodeURIComponent(source.slice(4));
    if (modelAbort) modelAbort.abort();
    var controller = modelAbort = new AbortController(), signal = controller.signal;
    status.dataset.state = 'loading'; status.textContent = 'loading model…';
    stopPlayback(); playback = null; $('playback').hidden = true;
    return fetchRetry(BASE + path, signal, 2).then(function (response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.json();
    }).then(function (manifest) {
      if (ticket !== modelLoad) return;
      state.model = manifest;
      if (!manifest.available) {
        state.viewer.clear();
        status.dataset.state = 'missing';
        status.textContent = 'no model: ' + manifest.reason;
        return;
      }
      if (!state.viewer.available) {
        status.dataset.state = 'error';
        status.textContent = 'WebGL is unavailable in this browser';
        return;
      }
      // Mesh URLs in the manifest are server-absolute; BASE mounts them. Until
      // every mesh is in, the model drawn is the one before.
      return state.viewer.load(manifest, function (url) { return fetchRetry(BASE + url, signal, 2); }).then(function () {
        if (ticket !== modelLoad) return;
        modelFailures = 0;
        status.dataset.state = 'loaded';
        status.textContent = '';
        return loadPlayback(manifest, ticket);
      });
    }).catch(function (error) {
      if (ticket !== modelLoad) return;
      modelFailures += 1;
      modelKey = null;
      modelRetryAt = Date.now() + Math.min(30000, 2000 * Math.pow(2, modelFailures - 1));
      status.dataset.state = 'error';
      status.textContent = 'model failed to load (' + error.message + '); trying again';
    }).finally(function () { if (modelAbort === controller) modelAbort = null; });
  }

  function applyStyle(name) {
    if (STYLES.indexOf(name) < 0) return renderStyle;
    renderStyle = name;
    writePref('cadex.render', name);
    pressed('view3d-style', 'data-style', name);
    pressed('style-choice', 'data-style', name);
    if (state.viewer) state.viewer.setStyle(name, { paper: token('--paper'), ink: token('--paper-ink') });
    return name;
  }

  // Playback: the trace's own placements, blended between the two frames
  // either side of the time shown. Nothing is simulated here.
  var playback = null, playT = 0, playing = null;

  function loadPlayback(manifest, ticket) {
    var info = manifest.playback;
    if (!info || !info.url) return null;
    return json(BASE + info.url).then(function (served) {
      if (ticket !== modelLoad || !served.available || !served.times_s || served.times_s.length < 2) return;
      playback = served;
      var slider = $('play-time'), times = served.times_s;
      slider.min = String(times[0]); slider.max = String(times[times.length - 1]);
      $('playback').hidden = false;
      seek(times[0]);
    }).catch(function () { /* the model stands without its rollout */ });
  }
  function blend(a, b, f) {
    var out = {};
    Object.keys(a).forEach(function (name) {
      var p = a[name], q = b[name] || p, qa = p.rotation_xyzw, qb = q.rotation_xyzw.slice();
      if (qa[0] * qb[0] + qa[1] * qb[1] + qa[2] * qb[2] + qa[3] * qb[3] < 0) qb = qb.map(function (v) { return -v; });
      var r = qa.map(function (v, i) { return v + (qb[i] - v) * f; }), n = Math.hypot.apply(null, r) || 1;
      out[name] = { position_mm: p.position_mm.map(function (v, i) { return v + (q.position_mm[i] - v) * f; }),
                    rotation_xyzw: r.map(function (v) { return v / n; }) };
    });
    return out;
  }
  function seek(t) {
    if (!playback) return;
    var times = playback.times_s, last = times.length - 1;
    playT = Math.max(times[0], Math.min(times[last], t));
    var lo = 0, hi = last;
    while (hi - lo > 1) { var mid = (lo + hi) >> 1; if (times[mid] <= playT) lo = mid; else hi = mid; }
    var span = times[hi] - times[lo], f = span > 0 ? (playT - times[lo]) / span : 0;
    state.viewer.setPoses(blend(playback.frames[lo], playback.frames[hi], Math.max(0, Math.min(1, f))));
    $('play-time').value = String(playT);
    $('play-clock').textContent = playT.toFixed(2) + ' s';
  }
  function stopPlayback() {
    if (playing) cancelAnimationFrame(playing);
    playing = null;
    $('play-toggle').textContent = 'Play';
  }
  function togglePlayback() {
    if (!playback) return;
    if (playing) { stopPlayback(); return; }
    var times = playback.times_s, end = times[times.length - 1];
    var from = playT >= end ? times[0] : playT, origin = performance.now();
    $('play-toggle').textContent = 'Pause';
    function step(now) {
      var t = from + (now - origin) / 1000;
      seek(t);
      if (t >= end) { stopPlayback(); return; }
      playing = requestAnimationFrame(step);
    }
    playing = requestAnimationFrame(step);
  }

  // -- 2D viewport -------------------------------------------------------------------
  // Everything flat the project has: its drawings, its presentation images,
  // its documents, and each run's training curves. Images pan and zoom.
  var sheet = { key: null, shownKey: null, list: [], kind: null, view: { scale: 1, x: 0, y: 0, fitted: true } };
  var CURVES = [['curve', 'reward'], ['loss_curve', 'loss'], ['episode_steps_curve', 'episode length']];

  function sheetSources(review) {
    var list = [];
    ((review.drawings || {}).sheets || []).forEach(function (s) {
      list.push({ key: 'sheet:' + s.file, group: 'Drawings', kind: 'image', url: s.url,
                  label: s.name + (s.version > 1 ? ' v' + s.version : '') + (s.relation === 'earlier' ? ' (earlier)' : '') });
    });
    var presentation = review.presentation || {};
    Object.keys(presentation.available ? presentation.files || {} : {}).forEach(function (name) {
      list.push({ key: 'image:' + name, group: 'Images', kind: 'image', label: name,
                  url: presentation.files[name].url + '?v=' + short(presentation.digest) });
    });
    var docs = review.docs || {};
    Object.keys(docs).forEach(function (name) {
      if (docs[name] === true) list.push({ key: 'doc:' + name, group: 'Documents', kind: 'doc', label: name, url: 'doc/current/' + name });
    });
    (Array.isArray(docs.domain) ? docs.domain : []).forEach(function (path) {
      list.push({ key: 'doc:' + path, group: 'Documents', kind: 'doc', label: path.replace(/^docs\//, ''), url: 'doc/current/' + path });
    });
    (review.runs || []).forEach(function (run) {
      var samples = (run.telemetry || {}).samples || {};
      CURVES.forEach(function (curve) {
        if (samples[curve[0]] > 1) list.push({ key: 'plot:' + run.run + ':' + curve[0], group: 'Plots', kind: 'plot', run: run.run,
                                                curve: curve[0], label: run.run + ' · ' + curve[1] });
      });
    });
    return list;
  }

  function renderSheetSources() {
    var list = sheetSources(state.review), select = $('view2d-source');
    var key = JSON.stringify(list);
    if (key !== JSON.stringify(sheet.list)) {
      sheet.list = list;
      select.textContent = '';
      var groups = {};
      list.forEach(function (item) {
        if (!groups[item.group]) { groups[item.group] = el('optgroup', { label: item.group }); select.appendChild(groups[item.group]); }
        groups[item.group].appendChild(el('option', { value: item.key, text: item.label }));
      });
    }
    var keys = list.map(function (item) { return item.key; });
    if (keys.indexOf(sheet.key) < 0) sheet.key = keys[0] || null;
    select.value = sheet.key || '';
    select.disabled = !list.length;
    $('sheet-empty').hidden = list.length > 0;
    $('sheet-stage').hidden = !list.length;
    showSheet();
  }

  function setSheet(key) { sheet.key = key; $('view2d-source').value = key; return showSheet(); }

  function showSheet() {
    var item = sheet.list.filter(function (entry) { return entry.key === sheet.key; })[0];
    var shownKey = item ? JSON.stringify(item) : null;
    if (shownKey === sheet.shownKey) return Promise.resolve();
    sheet.shownKey = shownKey;
    var stage = $('sheet-stage');
    stage.textContent = '';
    sheet.kind = item ? item.kind : null;
    stage.dataset.kind = sheet.kind || '';
    $('view2d-fit').hidden = sheet.kind !== 'image';
    if (!item) return Promise.resolve();
    if (item.kind === 'image') {
      var img = el('img', { src: item.url, alt: item.label, draggable: false, id: 'sheet-image' });
      img.addEventListener('load', fitSheet);
      stage.appendChild(img);
      return Promise.resolve();
    }
    if (item.kind === 'doc') {
      return fetch(item.url, { cache: 'no-store' }).then(function (response) {
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.text();
      }).then(function (text) {
        if (sheet.shownKey === shownKey) stage.appendChild(markdown(text));
      }).catch(function (error) { stage.appendChild(el('p', { className: 'empty', text: item.label + ': ' + error.message })); });
    }
    return json(BASE + '/api/run/' + encodeURIComponent(item.run)).then(function (record) {
      if (sheet.shownKey !== shownKey) return;
      sheet.points = ((record.telemetry || {})[item.curve] || []).filter(function (p) { return Array.isArray(p) && isFinite(p[0]) && isFinite(p[1]); });
      sheet.plotLabel = item.label;
      drawPlot();
    }).catch(function (error) { stage.appendChild(el('p', { className: 'empty', text: item.label + ': ' + error.message })); });
  }

  function placeSheet() {
    var img = $('sheet-image'), v = sheet.view;
    if (img) img.style.transform = 'translate(' + v.x + 'px,' + v.y + 'px) scale(' + v.scale + ')';
  }
  function fitSheet() {
    var img = $('sheet-image'), stage = $('sheet-stage');
    if (!img || !img.naturalWidth || !stage.clientWidth) return;
    var scale = Math.min(stage.clientWidth / img.naturalWidth, stage.clientHeight / img.naturalHeight) * 0.96;
    sheet.view = { scale: scale, x: (stage.clientWidth - img.naturalWidth * scale) / 2,
                   y: (stage.clientHeight - img.naturalHeight * scale) / 2, fitted: true };
    placeSheet();
  }
  function wireSheetStage() {
    var stage = $('sheet-stage'), drag = null;
    stage.addEventListener('wheel', function (event) {
      if (sheet.kind !== 'image') return;
      event.preventDefault();
      var r = stage.getBoundingClientRect(), v = sheet.view, f = Math.exp(-event.deltaY * 0.0015);
      var px = event.clientX - r.left, py = event.clientY - r.top;
      v.x = px - (px - v.x) * f; v.y = py - (py - v.y) * f; v.scale *= f; v.fitted = false;
      placeSheet();
    }, { passive: false });
    stage.addEventListener('pointerdown', function (event) {
      if (sheet.kind !== 'image' || event.button !== 0) return;
      stage.setPointerCapture(event.pointerId);
      drag = [event.clientX, event.clientY];
    });
    stage.addEventListener('pointermove', function (event) {
      if (!drag) return;
      sheet.view.x += event.clientX - drag[0]; sheet.view.y += event.clientY - drag[1]; sheet.view.fitted = false;
      drag = [event.clientX, event.clientY];
      placeSheet();
    });
    ['pointerup', 'pointercancel'].forEach(function (type) { stage.addEventListener(type, function () { drag = null; }); });
    stage.addEventListener('dblclick', function () { if (sheet.kind === 'image') fitSheet(); });
  }

  // A document is markdown, drawn with textContent only: nothing in it runs.
  function inline(text, parent) {
    var pattern = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\[[^\]]+\]\([^)\s]+\))/g, last = 0, match;
    while ((match = pattern.exec(text))) {
      if (match.index > last) parent.appendChild(document.createTextNode(text.slice(last, match.index)));
      var part = match[0];
      if (match[1]) parent.appendChild(el('code', { text: part.slice(1, -1) }));
      else if (match[2]) parent.appendChild(el('strong', { text: part.slice(2, -2) }));
      else {
        var link = /^\[([^\]]+)\]\(([^)\s]+)\)$/.exec(part);
        parent.appendChild(/^https?:\/\//.test(link[2])
          ? el('a', { text: link[1], href: link[2], target: '_blank', rel: 'noopener' })
          : el('span', { text: link[1], title: link[2] }));
      }
      last = pattern.lastIndex;
    }
    if (last < text.length) parent.appendChild(document.createTextNode(text.slice(last)));
    return parent;
  }
  function markdown(source) {
    var root = el('div', { className: 'doc' }), lines = source.replace(/\r/g, '').split('\n'), i = 0, para = [];
    var item = /^\s*([-*]|\d+\.)\s+/;
    function flush() { if (para.length) { root.appendChild(inline(para.join(' '), el('p'))); para = []; } }
    while (i < lines.length) {
      var line = lines[i], heading = /^(#{1,6})\s+(.*)$/.exec(line);
      if (/^```/.test(line)) {
        flush();
        var code = [];
        for (i++; i < lines.length && !/^```/.test(lines[i]); i++) code.push(lines[i]);
        root.appendChild(el('pre', { text: code.join('\n') }));
        i++;
      } else if (heading) {
        flush();
        root.appendChild(inline(heading[2], el('div', { className: 'md-h md-h' + heading[1].length })));
        i++;
      } else if (item.test(line)) {
        flush();
        var list = el(/^\s*\d+\./.test(line) ? 'ol' : 'ul');
        for (; i < lines.length && item.test(lines[i]); i++) list.appendChild(inline(lines[i].replace(item, ''), el('li')));
        root.appendChild(list);
      } else if (/^\|/.test(line)) {
        flush();
        var table = el('table');
        for (; i < lines.length && /^\|/.test(lines[i]); i++) {
          if (/^\|[\s:|-]+\|?\s*$/.test(lines[i])) continue;
          var row = el('tr');
          lines[i].trim().replace(/^\||\|$/g, '').split('|').forEach(function (cell) { row.appendChild(inline(cell.trim(), el('td'))); });
          table.appendChild(row);
        }
        root.appendChild(table);
      } else if (!line.trim()) { flush(); i++; }
      else { para.push(line.trim().replace(/^>\s?/, '')); i++; }
    }
    flush();
    return root;
  }

  // A plot is drawn at the stage's own size, so its type stays the page's.
  function ticks(lo, hi, want) {
    var step = Math.pow(10, Math.floor(Math.log10((hi - lo) / want))), err = (hi - lo) / want / step;
    step *= err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1;
    var out = [];
    for (var v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) out.push(Number(v.toPrecision(12)));
    return out;
  }
  function drawPlot() {
    var stage = $('sheet-stage'), points = sheet.points || [];
    if (sheet.kind !== 'plot') return;
    stage.textContent = '';
    if (points.length < 2) { stage.appendChild(el('p', { className: 'empty', text: 'No samples to plot.' })); return; }
    var NS = 'http://www.w3.org/2000/svg', W = Math.max(240, stage.clientWidth), H = Math.max(160, stage.clientHeight);
    var L = 64, R = 20, T = 36, B = 36;
    var xs = points.map(function (p) { return p[0]; }), ys = points.map(function (p) { return p[1]; });
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs), y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
    if (x1 === x0) x1 = x0 + 1;
    if (y1 === y0) { y0 -= 1; y1 += 1; }
    var pad = (y1 - y0) * 0.06; y0 -= pad; y1 += pad;
    var sx = function (x) { return L + (x - x0) / (x1 - x0) * (W - L - R); };
    var sy = function (y) { return H - B - (y - y0) / (y1 - y0) * (H - T - B); };
    function node(tag, attrs, text) {
      var n = document.createElementNS(NS, tag);
      Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
      if (text != null) n.textContent = text;
      return n;
    }
    var svg = node('svg', { viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, class: 'plot', role: 'img', 'aria-label': sheet.plotLabel });
    ticks(y0, y1, 5).forEach(function (y) {
      svg.appendChild(node('line', { x1: L, x2: W - R, y1: sy(y), y2: sy(y), class: 'plot-grid' }));
      svg.appendChild(node('text', { x: L - 8, y: sy(y), class: 'plot-label', 'text-anchor': 'end', 'dominant-baseline': 'middle' }, fmt(y)));
    });
    ticks(x0, x1, 6).forEach(function (x) {
      svg.appendChild(node('text', { x: sx(x), y: H - B + 18, class: 'plot-label', 'text-anchor': 'middle' }, fmt(x)));
    });
    svg.appendChild(node('line', { x1: L, x2: W - R, y1: H - B, y2: H - B, class: 'plot-axis' }));
    svg.appendChild(node('polyline', { points: points.map(function (p) { return sx(p[0]).toFixed(1) + ',' + sy(p[1]).toFixed(1); }).join(' '), class: 'plot-line' }));
    svg.appendChild(node('text', { x: L, y: 20, class: 'plot-title' }, sheet.plotLabel + ' by iteration'));
    stage.appendChild(svg);
  }

  // -- the loop -----------------------------------------------------------------------
  function render() {
    renderFreshness();
    if (!state.review) return;
    renderHeader(); renderRevisions(); renderSources(); renderSheetSources();
  }

  // The poll is the project read alone: a model it starts loading is
  // handed back to the caller but never holds up the next poll, so the page stays live while a large model comes in.
  function poll() {
    if (pendingPoll) return pendingPoll;
    var started = performance.now(), model = null;
    var read = fetch(BASE + '/api/project', { cache: 'no-store' }).then(function (response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.text();
    }).then(function (body) {
      lastPoll.project_bytes = body.length;
      var review = JSON.parse(body);
      state.review = review; state.lastOk = new Date(); state.stale = false; state.error = null;
      render();
      lastPoll.ms = performance.now() - started;
      // A run's model is fixed; the accepted one moves with every write.
      var key = source === 'accepted' ? JSON.stringify([review.accepted.revision, review.accepted.digest]) : source;
      if (key !== modelKey && Date.now() >= modelRetryAt) { modelKey = key; model = loadModel(); }
    }).catch(function (error) {
      state.stale = true; state.error = error.message;
      renderFreshness();
    }).finally(function () { if (pendingPoll === whole) pendingPoll = null; });
    var whole = pendingPoll = read.then(function () { return model; });
    return whole;
  }

  function onLayout() {
    if (state.viewer && state.viewer.draw) state.viewer.draw();
    if (sheet.kind === 'image' && sheet.view.fitted) fitSheet();
    if (sheet.kind === 'plot') drawPlot();
  }

  function initialize() {
    if (!BASE) $('home').hidden = true;
    var editors = {};
    ORDER.forEach(function (type) {
      var home = $('editor-' + type);
      editors[type] = { title: home.dataset.title, short: home.dataset.short, home: home,
                        tools: home.querySelector('.editor-tools'), body: home.querySelector('.editor-body') };
    });
    state.layout = window.CadexLayout.create({ root: $('screen'), shelf: $('editor-shelf'), editors: editors, order: ORDER,
                                               storageKey: 'cadex.layout.v2', defaultLayout: DEFAULT_LAYOUT, onChange: onLayout });
    state.viewer = window.CadexViewer.create($('viewer'));
    applyStyle(renderStyle);

    $('model-fit').addEventListener('click', function () { state.viewer.fit(); });
    $('view3d-source').addEventListener('change', function () { setSource($('view3d-source').value); });
    [$('view3d-style'), $('style-choice')].forEach(function (group) {
      group.addEventListener('click', function (event) {
        var button = event.target.closest('button');
        if (button) applyStyle(button.dataset.style);
      });
    });
    $('play-toggle').addEventListener('click', togglePlayback);
    $('play-time').addEventListener('input', function () { stopPlayback(); seek(Number($('play-time').value)); });

    $('view2d-source').addEventListener('change', function () { setSheet($('view2d-source').value); });
    $('view2d-fit').addEventListener('click', fitSheet);
    wireSheetStage();

    $('project-open').addEventListener('click', openProject);
    $('theme-choice').addEventListener('click', function (event) {
      var button = event.target.closest('button');
      if (button) window.cadexTheme.set(button.dataset.choice);
    });
    $('theme-toggle').addEventListener('click', function () {
      window.cadexTheme.set(window.cadexTheme.theme() === 'dark' ? 'light' : 'dark');
    });
    document.addEventListener('cadex-theme-choice', renderThemeChoice);
    // The diagram's paper and ink are the theme's.
    document.addEventListener('cadex-theme', function () { if (renderStyle === 'hairline') applyStyle('hairline'); });
    renderThemeChoice();
    $('layout-reset').addEventListener('click', function () { state.layout.reset(); });

    // Each canvas follows its box; redraw whenever the box changes.
    if (window.ResizeObserver) {
      new ResizeObserver(function () { if (state.viewer.draw) state.viewer.draw(); }).observe($('viewer'));
      new ResizeObserver(onLayout).observe($('sheet-stage'));
    }
    loadProjects();
    poll().then(function () { readyResolve(true); });
    setInterval(poll, POLL_MS);
  }

  window.cadexReview = {
    ready: ready,
    refresh: poll,
    viewer: function () { return state.viewer; },
    layout: function () { return state.layout; },
    setStyle: applyStyle,
    renderStyle: function () { return renderStyle; },
    setSource: setSource,
    setSheet: setSheet,
    sheets: function () { return sheet.list.map(function (item) { return { key: item.key, group: item.group, kind: item.kind, label: item.label }; }); },
    playback: function () { return playback && { times_s: playback.times_s, t: playT, playing: !!playing }; },
    seek: seek,
    lastPoll: function () { return { project_bytes: lastPoll.project_bytes, ms: lastPoll.ms }; },
    state: function () {
      return { stale: state.stale, error: state.error,
               revision: state.review && state.review.accepted.revision,
               model: state.model && { available: state.model.available, reason: state.model.reason, revision: state.model.revision } };
    }
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize);
  else initialize();
})();
