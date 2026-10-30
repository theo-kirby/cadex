// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The app (ADR-534): three editors tiled by layout.js, after Blender's areas,
// under a menu bar (ADR-539).
//
//   3D viewport  the accepted model or a run's, shaded or wireframe, a
//                run's rollout played back, a training run's checkpoints looped
//                as they land (ADR-545), the design's revisions with a ghost and
//                a tint (ADR-547), the rollout's trail on the ground (ADR-770) --
//                most of the screen by default;
//   Version      which of those every 3D viewport shows and when: the source,
//                the revision scrubber, the checkpoints and the rollout's
//                timeline (ADR-770) -- a strip under the 3D viewport;
//   Status       what the project is doing, how training is going and what
//                the agent last did (ADR-542, ADR-550; an editor since
//                ADR-572) -- an area beside the 3D viewport by default;
//   2D viewport  the project's drawings, images, documents, evaluation films and training plots,
//                a split away;
//   Outliner     every part the 3D viewport shows, to show, hide, isolate,
//                select and frame (ADR-676; outliner.js) -- above Status by default;
//   Menu bar     File (the project), Revisions (the trail), View (theme,
//                render style, lighting, occlusion, surface detail, mesh
//                lines, reflections, layout presets and reset, ADR-573,
//                ADR-602, ADR-676).
//
// Read-only (ADR-537): the agent working the project changes it, through
// the CLI or `cadex mcp`, and the page follows. Polls /api/project for what
// changed and reloads the model only when what it shows moves.
(function () {
  'use strict';

  // Every URL the page fetches or links is relative to the page itself, so
  // the page works unchanged under any path prefix (ADR-551). Served alone
  // (`cadex review`) it is a project's root; served from a projects directory
  // (`cadex app`) it is `p/<name>/` under the index, and NAME is that project.
  var NAME = (location.pathname.match(/\/p\/([^/]+)\/(?:index\.html)?$/) || [null, null])[1];
  var POLL_MS = 2000;
  var ORDER = ['view3d', 'version', 'status', 'training', 'view2d', 'outliner', 'activations', 'network', 'settings'];
  // The 3D viewport over a strip of Version, as Blender has its timeline under the viewport, with
  // the Outliner over Status over Training beside them, as Blender has its Outliner over its
  // Properties; split an area for the 2D one.
  var DEFAULT_LAYOUT = { dir: 'row', sizes: [0.72, 0.28], children: [
    { dir: 'col', sizes: [0.86, 0.14], children: [{ editor: 'view3d' }, { editor: 'version' }] },
    { dir: 'col', sizes: [0.3, 0.2, 0.5], children: [{ editor: 'outliner' }, { editor: 'status' }, { editor: 'training' }] }] };
  var STYLES = ['shaded', 'wireframe'];
  // The shaded look (ADR-676): four lighting setups and two matcaps (shading.js LOOKS).
  var LOOKS = ['studio', 'softbox', 'dramatic', 'daylight', 'aluminium', 'clay'];
  // The trail's styles (ADR-770; review_scene.js setTrailStyle).
  var TRAILS = ['off', 'line', 'dashed', 'dots', 'ribbon', 'footprints'];
  var state = { review: null, lastOk: null, stale: false, error: null, model: null, viewer: null, layout: null, outliner: null };
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
  function readStored(key) {
    try { return localStorage.getItem(key); } catch (_) { return null; }
  }
  function readPref(key, choices, fallback) {
    var value = readStored(key);
    return choices.indexOf(value) >= 0 ? value : fallback;
  }
  function writePref(key, value) { try { localStorage.setItem(key, value); } catch (_) { /* this visit only */ } }
  // A stored number within [lo, hi], or the fallback.
  function readNumber(key, lo, hi, fallback) {
    var value = readStored(key), number = value === null || value === '' ? NaN : Number(value);
    return isFinite(number) ? Math.max(lo, Math.min(hi, number)) : fallback;
  }
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

  // -- Menu bar: revisions --------------------------------------------------------
  // The trail the agent's accepted writes left, newest first.
  var revisionsKey = null;

  function renderRevisions() {
    var trail = state.review.revisions || [], current = state.review.accepted && state.review.accepted.revision;
    var key = JSON.stringify([trail, current]);
    if (key === revisionsKey) return;
    revisionsKey = key;
    var list = $('revision-list');
    $('revision-empty').hidden = trail.length > 0;
    list.textContent = '';
    // The trail comes newest first.
    trail.forEach(function (entry) {
      var here = entry.revision === current;
      var item = el('li', { value: entry.ordinal, 'data-revision': entry.revision, 'data-ordinal': String(entry.ordinal), 'data-current': String(here) }, [
        el('span', { text: here ? 'current' : brief(entry.saved_at),
                     title: when(entry.saved_at) + ' · ' + entry.revision + (entry.retained ? '' : ' · ' + (entry.retained_reason || 'model not retained')) })
      ]);
      // A row opens that revision on the 3D viewport's timeline: a view, never a restore.
      item.setAttribute('data-retained', String(!!entry.retained));
      list.appendChild(item);
    });
  }

  // -- Menu bar: the project and the view -----------------------------------------
  function loadProjects() {
    if (NAME == null) {
      // `cadex review` serves one project: there is nothing to switch to.
      ['project-field', 'project-open', 'project-all'].forEach(function (id) { $(id).hidden = true; });
      return Promise.resolve();
    }
    return json('../../api/projects').then(function (listing) {
      var select = $('project-select'), here = decodeURIComponent(NAME);
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
    if (name && name !== decodeURIComponent(NAME)) location.href = '../' + encodeURIComponent(name) + '/';
  }
  // One menu open at a time; a click outside or Escape closes it.
  function wireMenus() {
    var menus = Array.prototype.slice.call(document.querySelectorAll('#menubar details.menu'));
    function closeAll(except) { menus.forEach(function (menu) { if (menu !== except) menu.open = false; }); }
    menus.forEach(function (menu) {
      menu.addEventListener('toggle', function () { if (menu.open) closeAll(menu); });
      // Hovering across the bar while one is open moves to the next, as a menu bar does.
      menu.querySelector('summary').addEventListener('pointerenter', function () {
        if (menus.some(function (other) { return other.open && other !== menu; })) menu.open = true;
      });
    });
    document.addEventListener('pointerdown', function (event) {
      if (!event.target.closest('#menubar')) closeAll(null);
    });
    document.addEventListener('keydown', function (event) { if (event.key === 'Escape') closeAll(null); });
  }
  function renderThemeChoice() { pressed('theme-choice', 'data-choice', window.cadexTheme.choice()); }

  // -- 3D viewport -------------------------------------------------------------------
  // The source is the accepted model or one run's; a run's model plays its
  // rollout when the run kept one.
  var source = 'accepted', sourcesKey = null, modelKey = null, modelLoad = 0, modelAbort = null;
  // A failed load is tried again on a later poll, waiting longer each time.
  var modelFailures = 0, modelRetryAt = 0;
  // The render style; 'hairline', the wireframe's name before ADR-602, is read as it and kept so.
  var renderStyle = readPref('cadex.render', STYLES.concat(['hairline']), 'shaded');
  if (renderStyle === 'hairline') { renderStyle = 'wireframe'; writePref('cadex.render', renderStyle); }
  // The viewport's look (ADR-601, ADR-602): the wireframe's mesh lines and the shaded
  // solids' reflections, this browser's own.
  var meshLines = { shown: readPref('cadex.meshlines', ['on', 'off'], 'on') === 'on',
                    strength: readNumber('cadex.meshlines.strength', 0, 1, 0.12) };
  var reflections = readNumber('cadex.reflections', 0, 2, 1);
  var look = { name: readPref('cadex.look', LOOKS, 'studio'), occlusion: readPref('cadex.occlusion', ['on', 'off'], 'on') === 'on',
               detail: readPref('cadex.detail', ['on', 'off'], 'on') === 'on' };

  // A gait reference (ADR-703) is the accepted model posed by the task's
  // generated stride: the motion asked for, shown before anything trains.
  function referenceOf(value) {
    if (!state.review || value.indexOf('reference:') !== 0) return null;
    var task = value.slice(10);
    return (state.review.references || []).filter(function (r) { return r.task === task; })[0] || null;
  }

  function renderSources() {
    var runs = (state.review.runs || []).map(function (run) { return run.run; });
    var history = (state.review.revisions || []).length > 0;
    var refs = (state.review.references || []).map(function (r) { return [r.task, r.label, r.gait]; });
    var key = JSON.stringify([runs, history, refs]);
    if (key === sourcesKey) return;
    sourcesKey = key;
    var select = $('view3d-source');
    select.textContent = '';
    select.appendChild(el('option', { value: 'accepted', text: 'Accepted model' }));
    if (history) select.appendChild(el('option', { value: 'revisions', text: 'Revision history' }));
    if (runs.length) {
      var group = el('optgroup', { label: 'Runs' });
      runs.forEach(function (run) { group.appendChild(el('option', { value: 'run:' + run, text: run })); });
      select.appendChild(group);
    }
    if (refs.length) {
      var refGroup = el('optgroup', { label: 'Gait references' });
      refs.forEach(function (r) { refGroup.appendChild(el('option', { value: 'reference:' + r[0], text: r[1] + ' (' + r[0] + ')' })); });
      select.appendChild(refGroup);
    }
    var gone = source === 'revisions' ? !history
             : source.indexOf('reference:') === 0 ? !referenceOf(source)
             : source !== 'accepted' && runs.indexOf(source.slice(4)) < 0;
    if (gone) { source = 'accepted'; modelKey = null; }
    select.value = source;
  }

  // What the model shown is, as the poll reads it: a load is started only when it changes. The
  // accepted model moves with every write; a run's moves when the walk lands its export or its
  // own rollout, which adds the final policy's stop (ADR-554).
  function sourceKey(review) {
    return source === 'accepted' ? JSON.stringify([review.accepted.revision, review.accepted.digest])
         : source.indexOf('reference:') === 0 ? JSON.stringify([source, review.accepted.revision, review.accepted.digest])
         : source === 'revisions' ? revisionKey() : runModelKey(review, source.slice(4));
  }
  function setSource(value) {
    source = value;
    $('view3d-source').value = value;
    // The key of the model this load shows, so the next poll does not load it a second time
    // (and drop the rollout it has just started playing).
    modelKey = state.review ? sourceKey(state.review) : null; modelFailures = 0; modelRetryAt = 0;
    renderStatus();
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
    var reference = referenceOf(source);
    var path = source === 'accepted' || reference ? 'api/model/accepted'
             : source === 'revisions' ? 'api/model/revision/' + revisionShown()
             : 'api/model/run/' + encodeURIComponent(source.slice(4));
    if (modelAbort) modelAbort.abort();
    var controller = modelAbort = new AbortController(), signal = controller.signal;
    status.dataset.state = 'loading'; status.textContent = 'loading model…';
    stopPlayback(); playback = null; looping = false; ckpt.shown = null; $('playback').hidden = true; state.activations.setPlayback(null); refreshTrail(); if (state.viewer) state.viewer.setTargets(null); $('play-goto').hidden = true;
    return fetchRetry(path, signal, 2).then(function (response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.json();
    }).then(function (manifest) {
      if (ticket !== modelLoad) return;
      state.model = manifest;
      renderPrimitives();
      if (manifest.view === 'revision') renderRevisionTimeline();
      if (!manifest.available) {
        state.viewer.clear();
        state.outliner.setModel(null);
        status.dataset.state = 'missing';
        status.textContent = 'no model: ' + manifest.reason;
        return;
      }
      if (!state.viewer.available) {
        status.dataset.state = 'error';
        status.textContent = 'WebGL is unavailable in this browser';
        return;
      }
      // Mesh URLs in the manifest are relative to the page. Until every mesh
      // is in, the model drawn is the one before.
      var fetchMesh = function (url) { return fetchRetry(url, signal, 2); };
      if (manifest.view === 'revision') manifest = tintRevision(manifest);
      return state.viewer.load(manifest, fetchMesh).then(function () {
        if (ticket !== modelLoad) return;
        state.viewer.setTerrain(modelTerrain());
        state.outliner.setModel(manifest);
        if (manifest.view === 'revision') return state.viewer.loadGhost(ghostOf(manifest), fetchMesh, parseInt(token('--ink-2').slice(1), 16), 0.22);
      }).then(function () {
        if (ticket !== modelLoad) return;
        modelFailures = 0;
        // A trainer's run says what its model is (ADR-838): a concept, or CAD on its bodies.
        status.dataset.state = 'loaded';
        status.textContent = manifest.tier && manifest.tier.label ? manifest.tier.label : '';
        status.dataset.tier = manifest.tier ? manifest.tier.name : '';
        // A run with checkpoint rollouts plays them, its own rollout last.
        if (checkpointItems().items.length || ckpt.film) { renderCheckpoints(); return null; }
        // A reference loops from the start, as soon as it is in.
        if (reference) return loadPlayback({ playback: { url: reference.url } }, ticket, true);
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

  // Each 3D viewport has its own style and lighting (ADR-729): the View menu sets every one, a
  // viewport's header its own. The first viewport's are the ones this browser keeps.
  function views() { return state.views ? state.views.views() : []; }
  function firstView() { return state.views && state.views.first(); }
  function setViewStyle(view, name) {
    view.style = name;
    view.viewer.setStyle(name, { paper: token('--paper'), ink: token('--paper-ink') });
    view.styleGroup.querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.style === name)); });
    view.lookSelect.disabled = name !== 'shaded';
  }
  function refreshLookControls() {
    var all = views(), wire = all.some(function (v) { return v.style === 'wireframe'; }), shade = all.some(function (v) { return v.style === 'shaded'; });
    if (!all.length) { wire = renderStyle === 'wireframe'; shade = !wire; }
    $('mesh-lines').disabled = !wire;
    $('mesh-strength').disabled = !wire || !meshLines.shown;
    $('reflections').disabled = !shade || look.name === 'aluminium' || look.name === 'clay';
    ['look-choice', 'occlusion', 'detail'].forEach(function (id) { $(id).disabled = !shade; });
  }
  function applyStyle(name, only) {
    if (name === 'hairline') name = 'wireframe';
    if (STYLES.indexOf(name) < 0) return renderStyle;
    var first = firstView();
    if (!only || only === first) { renderStyle = name; writePref('cadex.render', name); pressed('style-choice', 'data-style', name); }
    (only ? [only] : views()).forEach(function (v) { setViewStyle(v, name); });
    if (!views().length) pressed('view3d-style', 'data-style', name);
    refreshLookControls();
    return name;
  }
  // The shaded look: a lighting setup or a matcap, occlusion and surface detail; any may be left out.
  function applyLook(next, only) {
    next = next || {};
    if (only && only !== firstView()) {
      if (LOOKS.indexOf(next.name) >= 0) { only.look = next.name; only.lookSelect.value = next.name; only.viewer.setLook(next.name); }
      return { name: only.look, occlusion: look.occlusion, detail: look.detail };
    }
    var named = LOOKS.indexOf(next.name) >= 0;
    if (named) look.name = next.name;
    if (typeof next.occlusion === 'boolean') look.occlusion = next.occlusion;
    if (typeof next.detail === 'boolean') look.detail = next.detail;
    writePref('cadex.look', look.name);
    writePref('cadex.occlusion', look.occlusion ? 'on' : 'off');
    writePref('cadex.detail', look.detail ? 'on' : 'off');
    $('view3d-look').value = look.name; $('look-choice').value = look.name;
    $('occlusion').checked = look.occlusion; $('detail').checked = look.detail;
    // A name from the menu is every view's; from the first view's header, its own.
    views().forEach(function (v) {
      if (named && (!only || v === only)) { v.look = look.name; v.lookSelect.value = look.name; v.viewer.setLook(look.name); }
    });
    if (state.viewer && state.viewer.setOcclusion) { state.viewer.setOcclusion(look.occlusion); state.viewer.setDetail(look.detail); }
    refreshLookControls();
    return { name: look.name, occlusion: look.occlusion, detail: look.detail };
  }
  // Mesh lines: on or off, and how strong, of the ink (0-1). Either may be left out.
  function applyMeshLines(next) {
    next = next || {};
    if (typeof next.shown === 'boolean') meshLines.shown = next.shown;
    if (next.strength != null && isFinite(Number(next.strength))) meshLines.strength = Math.max(0, Math.min(1, Number(next.strength)));
    writePref('cadex.meshlines', meshLines.shown ? 'on' : 'off');
    writePref('cadex.meshlines.strength', String(meshLines.strength));
    $('mesh-lines').checked = meshLines.shown;
    $('mesh-strength').value = String(meshLines.strength);
    refreshLookControls();
    if (state.viewer && state.viewer.setMeshLines) state.viewer.setMeshLines(meshLines);
    return { shown: meshLines.shown, strength: meshLines.strength };
  }
  // Reflections: the shaded solids' environment, 0-2 times each finish's own.
  function applyReflections(value) {
    if (value != null && isFinite(Number(value))) reflections = Math.max(0, Math.min(2, Number(value)));
    writePref('cadex.reflections', String(reflections));
    $('reflections').value = String(reflections);
    if (state.viewer && state.viewer.setReflections) state.viewer.setReflections(reflections);
    return reflections;
  }

  // Playback: the trace's own placements, blended between the two frames
  // either side of the time shown. Nothing is simulated here.
  var playback = null, playT = 0, playing = null, looping = false;

  // The follow camera (DASHBOARD.md §5): while a rollout plays, the view travels with the design,
  // so it can be watched close up as it runs. Its track is the design's centre at each frame,
  // smoothed over about half a second either way (Hann, zero-phase, as the capture rig's) so the
  // stride's bob and sway do not shake the view; the camera moves by the track's motion, and the
  // person's orbit, zoom and pan stay theirs.
  var followCam = readPref('cadex.follow', ['on', 'off'], 'off') === 'on', track = null;
  function trackOf(served) {
    var raw = served.frames.map(function (frame) { return state.viewer.centreAt(frame); });
    if (!raw.length || raw.some(function (p) { return !p; })) return null;
    var times = served.times_s, dt = (times[times.length - 1] - times[0]) / Math.max(1, times.length - 1);
    var W = Math.max(0, Math.min(120, Math.round(0.5 / Math.max(dt, 1e-3))));
    // The window narrows symmetrically at either end of the rollout, so the track never lags
    // the design there: a one-sided window would trail a running design out of a close view.
    return raw.map(function (_, i) {
      var acc = [0, 0, 0], sum = 0, w = Math.min(W, i, raw.length - 1 - i);
      for (var k = i - w; k <= i + w; k++) {
        var wt = 0.5 * (1 + Math.cos(Math.PI * (k - i) / (w + 1)));
        acc[0] += wt * raw[k][0]; acc[1] += wt * raw[k][1]; acc[2] += wt * raw[k][2]; sum += wt;
      }
      return acc.map(function (v) { return v / sum; });
    });
  }
  function trackAt(lo, hi, f) {
    if (!track) return null;
    var a = track[lo], b = track[hi];
    return a.map(function (v, i) { return v + (b[i] - v) * f; });
  }
  // Follow is each 3D viewport's own (ADR-729): the first's is the one this browser keeps.
  function anyFollow() { return views().length ? views().some(function (v) { return v.follow; }) : followCam; }
  function applyFollow(on, view) {
    view = view || firstView();
    if (!view) return followCam;
    view.follow = !!on;
    view.followButton.setAttribute('aria-pressed', String(view.follow));
    if (view === firstView()) { followCam = view.follow; writePref('cadex.follow', followCam ? 'on' : 'off'); }
    if (!view.follow) { view.viewer.followTo(null); return view.follow; }
    if (playback) {
      if (!track) track = trackOf(playback);
      var point = pointAt(playT);
      if (point) { view.viewer.followTo(point, true); view.viewer.draw(); }
    }
    return view.follow;
  }
  function pointAt(t) {
    if (!playback || !track) return null;
    var times = playback.times_s, last = times.length - 1, lo = 0, hi = last;
    t = Math.max(times[0], Math.min(times[last], t));
    while (hi - lo > 1) { var mid = (lo + hi) >> 1; if (times[mid] <= t) lo = mid; else hi = mid; }
    var span = times[hi] - times[lo];
    return trackAt(lo, hi, span > 0 ? Math.max(0, Math.min(1, (t - times[lo]) / span)) : 0);
  }

  function loadPlayback(manifest, ticket, loop) {
    var info = manifest.playback;
    if (!info || !info.url) return null;
    return json(info.url).then(function (served) {
      if (ticket !== modelLoad || !served.available || !served.times_s || served.times_s.length < 2) return;
      showPlayback(served);
      if (loop) { looping = true; togglePlayback(); }
    }).catch(function () { /* the model stands without its rollout */ });
  }
  // The course the model stands on (ADR-734): its export's course 0, until a playback says which
  // course its episode stood on.
  function modelTerrain() { return (state.model && state.model.collision && state.model.collision.terrain) || null; }
  function showPlayback(served) {
    playback = served;
    state.viewer.setTerrain(served.terrain || modelTerrain());
    // A go-to-point episode's points (ADR-839), lit as the episode lit them.
    state.viewer.setTargets(served.goto ? served.goto.points : null);
    $('play-goto').hidden = !served.goto;
    var slider = $('play-time'), times = served.times_s;
    slider.min = String(times[0]); slider.max = String(times[times.length - 1]);
    $('playback').hidden = false;
    // A new rollout puts the followed view back on the design.
    track = anyFollow() ? trackOf(served) : null;
    state.viewer.followTo(null);
    state.activations.setPlayback(served);
    if (anyFollow() && track) state.viewer.followTo(track[0], true);
    refreshTrail();
    seek(times[0]);
  }

  // The trail (ADR-770): each 3D viewport's own style, the first's kept by this browser; the course
  // is the rollout's, worked out once for every viewport: the design's smoothed centre at each
  // frame (the follow camera's track) and, when a viewport draws prints, its footfalls.
  var trailPref = readPref('cadex.trail', TRAILS, 'off'), trailCourse = { served: null, prints: false };
  function refreshTrail() {
    if (!state.viewer) return;
    if (!playback) {
      if (trailCourse.served) { trailCourse = { served: null, prints: false }; state.viewer.setTrail(null); }
      return;
    }
    var styles = views().map(function (v) { return v.trail; });
    var prints = styles.indexOf('footprints') >= 0;
    if (!styles.some(function (s) { return s !== 'off'; })) return;
    if (trailCourse.served === playback && (trailCourse.prints || !prints)) return;
    var centres = trackOf(playback);
    if (!centres) return;
    trailCourse = { served: playback, prints: prints };
    state.viewer.setTrail({ times_s: playback.times_s, path_mm: centres,
                            prints: prints ? state.viewer.footfalls(playback.frames, playback.times_s) : [] });
    state.viewer.showTrail(playT);
  }
  function applyTrail(name, view) {
    view = view || firstView();
    if (!view || TRAILS.indexOf(name) < 0) return view ? view.trail : trailPref;
    view.trail = name;
    view.trailSelect.value = name;
    if (view === firstView()) { trailPref = name; writePref('cadex.trail', name); }
    refreshTrail();
    view.viewer.setTrailStyle(name);
    return name;
  }
  // Activations in the viewport (ADR-770): each viewport paints the rollout's motor loads on the
  // parts they move, or not, by its own switch; the Activations editor works them out once.
  function applyHeat(on, view) {
    view = view || firstView();
    if (!view) return false;
    view.heat = !!on;
    view.heatButton.setAttribute('aria-pressed', String(view.heat));
    if (state.activations) state.activations.repaintViewports();
    return view.heat;
  }
  // A training model's primitives outlined over its CAD (ADR-838), or not (ADR-901): each viewport's
  // own switch, the first's kept by this browser, offered only while the model shown has them.
  var primitivesPref = readPref('cadex.primitives', ['on', 'off'], 'on') === 'on';
  function hasPrimitives() {
    return !!(state.model && state.model.available && (state.model.components || []).some(function (c) { return c.outline && c.cad && c.cad.length; }));
  }
  function applyPrimitives(on, view) {
    view = view || firstView();
    if (!view) return primitivesPref;
    view.primitives = !!on;
    view.primitivesButton.setAttribute('aria-pressed', String(view.primitives));
    if (view === firstView()) { primitivesPref = view.primitives; writePref('cadex.primitives', on ? 'on' : 'off'); }
    view.viewer.showPrimitives(view.primitives);
    return view.primitives;
  }
  function renderPrimitives() { var offered = hasPrimitives(); views().forEach(function (v) { v.primitivesButton.hidden = !offered; }); }
  // The axes gizmo folds away to a caret, and back (ADR-770); each viewport's own, the first's kept.
  var gizmoPref = readPref('cadex.gizmo', ['on', 'off'], 'on') === 'on';
  function applyGizmo(on, view) {
    view = view || firstView();
    if (!view) return gizmoPref;
    view.gizmoOn = !!on;
    view.body.dataset.gizmo = on ? 'on' : 'off';
    var label = on ? 'Hide the axes' : 'Show the axes';
    view.gizmoToggle.setAttribute('aria-pressed', String(!!on));
    view.gizmoToggle.title = label; view.gizmoToggle.setAttribute('aria-label', label);
    if (view === firstView()) { gizmoPref = !!on; writePref('cadex.gizmo', on ? 'on' : 'off'); }
    return view.gizmoOn;
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
    f = Math.max(0, Math.min(1, f));
    if (anyFollow() && track) state.viewer.followTo(trackAt(lo, hi, f));
    if (trailCourse.served === playback) state.viewer.showTrail(playT);
    state.viewer.setPoses(blend(playback.frames[lo], playback.frames[hi], f));
    state.activations.setFrame(lo, hi, f);
    if (playback.goto) showGoto(playback.goto, playback.goto.frames[lo]);
    $('play-time').value = String(playT);
    $('play-clock').textContent = playT.toFixed(2) + ' s';
  }
  // The lit point in words beside the clock: which, its band and speed, and how far its hold has run.
  function showGoto(goto, at) {
    state.viewer.showTargets(at);
    var n = goto.points.length, i = at ? at.index : 0, p = goto.points[Math.min(i, n - 1)];
    // A gate course (ADR-902): which gate, and the speed made on the leg to the last one passed.
    if (p && p.radius_m > 0) {
      var last = i > 0 ? goto.points[Math.min(i, n) - 1] : null;
      $('play-goto').textContent = !at ? '' : (i >= n ? 'all ' + n + ' gates' : 'gate ' + (i + 1) + '/' + n)
        + (last ? ' · last leg ' + last.speed_mps.toFixed(2) + ' m/s' : '');
      return;
    }
    $('play-goto').textContent = !at ? '' : i >= n ? 'all ' + n + ' points done'
      : 'point ' + (i + 1) + '/' + n + ' · ' + (p.band ? p.band + ' ' : '') + p.speed_mps.toFixed(2) + ' m/s'
        + (p.hold_s > 0 ? ' · hold ' + p.hold_s.toFixed(1) + ' s' + (at.arrived ? ' ' + Math.round(at.hold * 100) + '%' : '') : '');
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
      if (t >= end && looping) { from = times[0]; origin = now; t = from; }
      seek(t);
      if (t >= end) { stopPlayback(); return; }
      playing = requestAnimationFrame(step);
    }
    playing = requestAnimationFrame(step);
  }

  // -- 3D viewport: checkpoint rollouts (ADR-545) -------------------------------------
  // The run Status reads lists its checkpoints in `stage.checkpoints`,
  // each rolled out by the engine as it landed (ADR-544). While that run is
  // the model shown, the newest one loops; the scrubber picks an older one,
  // and moving it back to the newest end follows new ones again. While the
  // run trains, the viewport turns to it unless a source was picked by hand.
  var ckpt = { items: [], films: [], pending: 0, pinned: null, film: null, shown: null, playing: null, paused: false, chosenSource: false };

  // Any run picked as the source scrubs its own checkpoints (ADR-790): the stage carries the
  // run it reads, and any other is read from its own route when picked, and again while it moves.
  var otherCkpt = { run: null, block: null, at: 0, busy: false };
  function checkpointBlock(name) {
    var stage = state.review.stage || {};
    if (name === stage.run) return stage.checkpoints;
    if (otherCkpt.run !== name) otherCkpt = { run: name, block: null, at: 0, busy: false };
    var run = (state.review.runs || []).filter(function (r) { return r.run === name; })[0];
    var moving = (run && run.status === 'running') || (otherCkpt.block && otherCkpt.block.pending > 0);
    if (!otherCkpt.busy && (!otherCkpt.at || (moving && Date.now() - otherCkpt.at > 15000))) {
      otherCkpt.busy = true;
      json('api/checkpoints/' + encodeURIComponent(name)).then(function (block) {
        if (otherCkpt.run !== name) return;
        otherCkpt.block = block; otherCkpt.at = Date.now(); otherCkpt.busy = false;
        renderCheckpoints();
      }).catch(function () {
        if (otherCkpt.run === name) { otherCkpt.busy = false; otherCkpt.at = Date.now(); }
      });
    }
    return otherCkpt.block;
  }
  function checkpointItems() {
    if (!state.review || source.indexOf('run:') !== 0) return { items: [], pending: 0, films: [] };
    var block = checkpointBlock(source.slice(4)), filmed = filmItems(source.slice(4));
    var items = ((block && block.items) || []).slice(), own = state.model && state.model.available && state.model.playback;
    // The run's own rollout, once it has one, is its newest policy.
    if ((items.length || filmed.length) && own && own.available && own.url) {
      items.push({ stem: 'final', tag: 'final', state: 'ready', url: own.url, iteration: null, reward_per_step: null, final: true });
    }
    return { items: items, pending: (block && block.pending) || 0, films: filmed };
  }
  // -- 3D viewport: films (ADR-901) ---------------------------------------------------
  // Whole episodes something other than the run's trainer filmed under it (a project's judge's
  // `judge-export/best/s3/view/`), read from `/api/films/<run>` when the run is picked and every
  // 30 s after, are stops beside its checkpoints. A picked film stays picked until a checkpoint is
  // picked or its run no longer lists it; new checkpoints landing never take its place.
  var films = { run: null, block: null, at: 0, busy: false };
  function filmItems(name) {
    if (films.run !== name) { films = { run: name, block: null, at: 0, busy: false }; ckpt.film = null; }
    if (!films.busy && (!films.at || Date.now() - films.at > 30000)) {
      films.busy = true;
      json('api/films/' + encodeURIComponent(name)).then(function (block) {
        if (films.run !== name) return;
        films.block = block; films.at = Date.now(); films.busy = false;
        renderCheckpoints();
      }).catch(function () {
        if (films.run === name) { films.busy = false; films.at = Date.now(); }
      });
    }
    return ((films.block && films.block.items) || []).map(function (f) {
      return { stem: 'film:' + f.film, film: f.film, group: f.group, name: f.name, state: f.state === 'ready' ? 'ready' : 'failed',
               reason: f.reason, error: '', url: f.url, duration_s: f.duration_s, points: f.goto ? f.points : 0, bytes: f.bytes };
    });
  }
  function followTraining() {
    var stage = state.review.stage || {}, block = stage.checkpoints;
    if (ckpt.chosenSource || stage.state !== 'training' || !block || !stage.run || source === 'run:' + stage.run) return;
    if (!(block.items || []).some(function (item) { return item.state === 'ready'; })) return;
    source = 'run:' + stage.run;
    $('view3d-source').value = source;
  }
  function checkpointName(item) {
    if (item.final) return 'final policy';
    if (item.film) return item.film;
    return 'iteration ' + (item.iteration + 1) + ' · reward ' + (item.reward_per_step == null ? '—' : fmt(item.reward_per_step));
  }
  function restPoses() {
    var poses = {};
    ((state.model && state.model.components) || []).forEach(function (c) { if (c.placement) poses[c.name] = c.placement; });
    return poses;
  }
  function renderCheckpoints() {
    var got = checkpointItems(), items = got.items, filmed = got.films, box = $('checkpoints');
    ckpt.items = items; ckpt.films = filmed; ckpt.pending = got.pending;
    setHidden('checkpoints', !items.length && !filmed.length);
    if (!items.length && !filmed.length) { setHidden('checkpoint-status', true); ckpt.shown = null; ckpt.playing = null; return; }
    var stems = items.map(function (item) { return item.stem; });
    if (ckpt.pinned && stems.indexOf(ckpt.pinned) < 0) ckpt.pinned = null;
    var film = ckpt.film ? filmed.filter(function (f) { return f.film === ckpt.film; })[0] : null;
    if (ckpt.film && !film && films.block) ckpt.film = null;
    var index = ckpt.pinned ? stems.indexOf(ckpt.pinned) : items.length - 1, item = film || items[index] || null;
    renderStops(items, filmed, item);
    var pick = $('checkpoint-pick');
    if (box.dataset.follow !== String(!ckpt.pinned && !film)) box.dataset.follow = String(!ckpt.pinned && !film);
    box.querySelector('.timeline-name').textContent = film ? 'Film' : 'Checkpoint';
    // Films and no checkpoint, rollout or pick: the model stands, and the picker offers the films.
    if (!item) { pick.title = filmed.length + ' film' + (filmed.length > 1 ? 's' : '') + ' under this run'; setHidden('checkpoint-status', true); return; }
    if (box.dataset.state !== item.state) box.dataset.state = item.state;
    $('checkpoint-status').dataset.state = item.state;
    pick.title = film ? 'Film ' + film.film + ', one of ' + filmed.length
                      : 'Checkpoint ' + (index + 1) + ' of ' + items.length + (ckpt.pinned ? '' : ', following the newest');
    var note = item.state === 'failed' ? (film ? 'film unplayable: ' : 'rollout failed: ') + item.reason + (item.error ? ' — ' + item.error : '')
             : got.pending ? got.pending + ' newer checkpoint' + (got.pending > 1 ? 's' : '') + ' rolling out' : '';
    setText('checkpoint-status', note).title = note;
    setHidden('checkpoint-status', !note);
    var key = item.stem + ':' + item.state + ':' + (item.sha256 || item.url || '') + ':' + (item.bytes || '');
    // Poses go onto that run's own model, once it is drawn.
    var drawn = state.model && state.model.run === source.slice(4) && $('model-status').dataset.state === 'loaded';
    if (key === ckpt.shown || !drawn) return;
    ckpt.shown = key;
    showCheckpoint(item, key);
  }

  // -- the stop picker (ADR-901) ------------------------------------------------------
  // One button names the stop shown; it opens a popover over the area that would clip it (as
  // Training's Cards menu does) holding a filter and a listbox: the checkpoints newest first, then
  // each directory's films, each stop with its length and, for a go-to-point episode, its points.
  // Typing filters (every word must match the stop's group and name), the arrows and Page keys
  // move through what is shown, Enter picks and Escape closes.
  function stopSeconds(d) { return d == null ? '' : (d < 10 ? d.toFixed(1) : String(Math.round(d))) + ' s'; }
  function stopMeta(item) {
    var parts = [];
    if (item.state === 'failed') parts.push('failed');
    else if (item.state !== 'ready') parts.push(item.state);
    if (item.duration_s != null) parts.push(stopSeconds(item.duration_s));
    if (item.points) parts.push(item.points + ' point' + (item.points > 1 ? 's' : ''));
    return parts.join(' · ');
  }
  function renderStops(items, filmed, current) {
    var groups = [];
    if (items.length) {
      groups.push({ name: 'Checkpoints', stops: items.map(function (it, i) {
        return { item: it, label: checkpointName(it) + (i === items.length - 1 ? ' · newest' : '') };
      }).reverse() });
    }
    filmed.forEach(function (f) {
      var last = groups[groups.length - 1], name = f.group || 'films';
      if (!last || !last.films || last.name !== name) groups.push(last = { name: name, films: true, stops: [] });
      last.stops.push({ item: f, label: f.name });
    });
    var list = $('checkpoint-list'), optionsKey = JSON.stringify(groups.map(function (g) {
      return [g.name, g.stops.map(function (s) { return [s.item.stem, s.label, stopMeta(s.item)]; })];
    }));
    if (list.dataset.options !== optionsKey) {
      var active = stopActive(), keep = active && active.dataset.stop, n = 0;
      list.dataset.options = optionsKey;
      list.textContent = '';
      groups.forEach(function (g) {
        var row = document.createElement('li'), head = document.createElement('div'), group = document.createElement('ul');
        row.className = 'stop-group'; row.setAttribute('role', 'presentation');
        head.className = 'stop-group-name'; head.setAttribute('aria-hidden', 'true');
        head.textContent = g.name + (g.films ? ' · ' + g.stops.length : '');
        group.setAttribute('role', 'group'); group.setAttribute('aria-label', g.name);
        g.stops.forEach(function (s) {
          var option = document.createElement('li'), name = document.createElement('span'), meta = document.createElement('span');
          option.id = 'checkpoint-stop-' + (n++); option.setAttribute('role', 'option');
          option.dataset.stop = s.item.stem; option.dataset.state = s.item.state;
          option.dataset.search = (g.name + ' ' + (s.item.film || '') + ' ' + s.label).toLowerCase();
          name.className = 'stop-name'; name.textContent = s.label; name.title = s.item.film || s.label;
          meta.className = 'stop-meta'; meta.textContent = stopMeta(s.item);
          option.appendChild(name); option.appendChild(meta); group.appendChild(option);
        });
        row.appendChild(head); row.appendChild(group); list.appendChild(row);
      });
      filterStops();
      if (keep) setStopActive(list.querySelector('[data-stop="' + CSS.escape(keep) + '"]'));
    }
    list.querySelectorAll('[role="option"]').forEach(function (option) {
      var chosen = String(!!current && option.dataset.stop === current.stem);
      if (option.getAttribute('aria-selected') !== chosen) option.setAttribute('aria-selected', chosen);
    });
    var pick = $('checkpoint-pick'), label = current ? checkpointName(current) + (current === items[items.length - 1] && !current.film ? ' · newest' : '') : 'pick a film';
    if (pick.querySelector('.stop-label').textContent !== label) pick.querySelector('.stop-label').textContent = label;
    var meta = current ? stopMeta(current) : filmed.length + ' film' + (filmed.length > 1 ? 's' : '');
    if (pick.querySelector('.stop-meta').textContent !== meta) pick.querySelector('.stop-meta').textContent = meta;
  }
  function shownStops() {
    return Array.prototype.filter.call($('checkpoint-list').querySelectorAll('[role="option"]'), function (o) { return !o.hidden && !o.parentNode.parentNode.hidden; });
  }
  function stopActive() {
    var id = $('checkpoint-filter').getAttribute('aria-activedescendant');
    return id ? document.getElementById(id) : null;
  }
  function setStopActive(option) {
    var before = stopActive();
    if (before) before.classList.remove('active');
    if (!option) { $('checkpoint-filter').removeAttribute('aria-activedescendant'); return; }
    option.classList.add('active');
    $('checkpoint-filter').setAttribute('aria-activedescendant', option.id);
    option.scrollIntoView({ block: 'nearest' });
  }
  function filterStops() {
    var words = $('checkpoint-filter').value.toLowerCase().split(/\s+/).filter(Boolean), shown = 0;
    $('checkpoint-list').querySelectorAll('.stop-group').forEach(function (row) {
      var any = false;
      row.querySelectorAll('[role="option"]').forEach(function (option) {
        var hit = words.every(function (w) { return option.dataset.search.indexOf(w) >= 0; });
        option.hidden = !hit;
        if (hit) { any = true; shown += 1; }
      });
      row.hidden = !any;
    });
    $('checkpoint-empty').hidden = shown > 0;
    var active = stopActive();
    if (!active || active.hidden || active.parentNode.parentNode.hidden) setStopActive(shownStops()[0] || null);
  }
  function placeStops() {
    // On the side of the button with more room (the Version strip is low on the screen), as wide
    // as a phone allows inside a 16 px gutter.
    var menu = $('checkpoint-menu'), r = $('checkpoint-pick').getBoundingClientRect(), w = window.innerWidth, h = window.innerHeight;
    var width = Math.min(440, w - 32), below = h - r.bottom - 12, above = r.top - 12, up = above > below;
    menu.style.width = width + 'px'; menu.style.right = 'auto';
    menu.style.left = Math.max(16, Math.min(w - width - 16, r.left)) + 'px';
    menu.style.maxHeight = Math.max(160, Math.min(520, up ? above : below)) + 'px';
    if (up) { menu.style.top = 'auto'; menu.style.bottom = (h - r.top + 4) + 'px'; }
    else { menu.style.bottom = 'auto'; menu.style.top = (r.bottom + 4) + 'px'; }
  }
  function chooseStop(stem) {
    var menu = $('checkpoint-menu');
    if (menu.matches(':popover-open')) { menu.hidePopover(); $('checkpoint-pick').focus(); }
    if (stem.indexOf('film:') === 0) return pickFilm(stem.slice(5));
    return pickCheckpoint(ckpt.items.map(function (item) { return item.stem; }).indexOf(stem));
  }
  function pickFilm(film) {
    if (!ckpt.films.some(function (f) { return f.film === film; })) return null;
    ckpt.film = film;
    renderCheckpoints();
    return ckpt.film;
  }
  var stopSeed = '';
  function wireStops() {
    var pick = $('checkpoint-pick'), menu = $('checkpoint-menu'), filter = $('checkpoint-filter');
    pick.addEventListener('keydown', function (e) {
      // The arrows open it, as a select's do; a letter opens it filtering by that letter.
      var letter = e.key.length === 1 && e.key !== ' ' && !e.ctrlKey && !e.metaKey && !e.altKey;
      if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp' && !letter) return;
      e.preventDefault();
      stopSeed = letter ? e.key : '';
      if (!menu.matches(':popover-open')) menu.showPopover();
    });
    menu.addEventListener('toggle', function (e) {
      pick.setAttribute('aria-expanded', String(e.newState === 'open'));
      if (e.newState !== 'open') return;
      filter.value = stopSeed; stopSeed = '';
      filterStops();
      placeStops();
      var chosen = $('checkpoint-list').querySelector('[aria-selected="true"]');
      setStopActive(chosen && !chosen.hidden ? chosen : shownStops()[0] || null);
      filter.focus();
    });
    filter.addEventListener('input', filterStops);
    filter.addEventListener('keydown', function (e) {
      var shown = shownStops(), at = shown.indexOf(stopActive()), step = { ArrowDown: 1, ArrowUp: -1, PageDown: 8, PageUp: -8 }[e.key];
      if (step) {
        e.preventDefault();
        if (shown.length) setStopActive(shown[Math.max(0, Math.min(shown.length - 1, at < 0 ? 0 : at + step))]);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (at >= 0) chooseStop(shown[at].dataset.stop);
      } else if (e.key === 'Escape') {
        // A search field would only clear itself on the first Escape.
        e.preventDefault();
        menu.hidePopover(); pick.focus();
      }
    });
    $('checkpoint-list').addEventListener('click', function (e) {
      var option = e.target.closest('[role="option"]');
      if (option) chooseStop(option.dataset.stop);
    });
  }
  function showCheckpoint(item, key) {
    var ticket = modelLoad;
    stopPlayback(); playback = null; ckpt.playing = null; state.activations.setPlayback(null); refreshTrail(); if (state.viewer) state.viewer.setTargets(null); $('play-goto').hidden = true;
    if (item.state !== 'ready') {
      $('playback').hidden = true;
      state.viewer.setPoses(restPoses()); state.viewer.setTerrain(modelTerrain());
      return null;
    }
    return json(item.url).then(function (served) {
      if (ticket !== modelLoad || ckpt.shown !== key) return;
      if (!served.available || !served.times_s || served.times_s.length < 2) {
        $('playback').hidden = true;
        setText('checkpoint-status', 'rollout unplayable: ' + (served.reason || 'no frames')).hidden = false;
        return;
      }
      looping = true; ckpt.playing = item.stem;
      showPlayback(served);
      if (!ckpt.paused) togglePlayback();
    }).catch(function (error) {
      if (ckpt.shown !== key) return;
      ckpt.shown = null;  // tried again on the next poll
      setText('checkpoint-status', 'rollout failed to load (' + error.message + '); trying again').hidden = false;
    });
  }
  function pickCheckpoint(index) {
    var items = ckpt.items;
    if (!items.length) return null;
    ckpt.film = null;
    index = Math.max(0, Math.min(items.length - 1, Math.round(index)));
    ckpt.pinned = index === items.length - 1 ? null : items[index].stem;
    renderCheckpoints();
    return ckpt.pinned;
  }

  // -- 3D viewport: the revision timeline (ADR-547) -----------------------------------
  // While the source is the revision history, each stored revision is a stop,
  // oldest to newest, drawn from the model kept when it was accepted
  // (ADR-546). The newest is shown and followed; picking an older one keeps
  // it, and back at the newest end it follows again. The revision before the
  // one shown is a ghost where it differs, and parts whose digest changed are
  // tinted. A revision whose model was not kept says why and draws nothing.
  var rev = { pinned: null };

  function revisionStops() { return ((state.review && state.review.revisions) || []).slice().reverse(); }
  function revisionShown() {
    var stops = revisionStops();
    if (rev.pinned != null && stops.some(function (s) { return s.ordinal === rev.pinned; })) return rev.pinned;
    rev.pinned = null;
    return stops.length ? stops[stops.length - 1].ordinal : null;
  }
  // Unchanged parts in the diagram's ink, changed ones in --info.
  function tintRevision(manifest) {
    var same = token('--paper-ink'), changed = token('--info');
    return Object.assign({}, manifest, { components: manifest.components.map(function (c) {
      return Object.assign({}, c, { color: c.changed ? changed : same });
    }) });
  }
  // The previous revision where it is not the model itself: a part kept as
  // it was, where it was, would only lie on top of its own copy.
  function ghostOf(manifest) {
    var prev = manifest.previous;
    if (!prev || !prev.available) return [];
    var now = {};
    manifest.components.forEach(function (c) { now[c.name] = c; });
    return prev.components.filter(function (c) {
      var here = now[c.name];
      return !here || here.sha256 !== c.sha256 || JSON.stringify(here.placement) !== JSON.stringify(c.placement);
    });
  }
  function renderRevisionTimeline() {
    var box = $('revision-timeline'), stops = revisionStops(), on = source === 'revisions' && stops.length > 0;
    setHidden('revision-timeline', !on);
    if (!on) { setHidden('revision-status', true); return; }
    var ordinal = revisionShown(), index = 0, current = state.review.accepted && state.review.accepted.revision;
    stops.forEach(function (s, i) { if (s.ordinal === ordinal) index = i; });
    var stop = stops[index], pick = $('revision-pick');
    if (pick.max !== String(stops.length - 1)) pick.max = String(stops.length - 1);
    if (pick.value !== String(index)) pick.value = String(index);
    if (box.dataset.follow !== String(rev.pinned == null)) box.dataset.follow = String(rev.pinned == null);
    var retained = !!stop.retained, stateName = retained ? 'retained' : 'missing';
    if (box.dataset.state !== stateName) box.dataset.state = stateName;
    $('revision-status').dataset.state = stateName;
    box.dataset.ordinal = String(stop.ordinal);
    var named = 'revision ' + stop.ordinal + (stop.revision === current ? ' · current' : ' · ' + brief(stop.saved_at)) +
                ' · ' + (index + 1) + '/' + stops.length + (rev.pinned == null ? ' · newest' : '');
    setText('revision-label', named).title = named;
    var model = state.model && state.model.view === 'revision' && state.model.ordinal === stop.ordinal ? state.model : null, note;
    if (!retained) note = 'not shown: ' + (stop.retained_reason || 'its model was not retained');
    else if (!model) note = '';
    else if (model.changed) {
      note = (model.changed.length ? 'changed: ' + model.changed.join(', ') : 'no part changed') + ' · ' + model.compare;
      if (model.changed.length || ghostOf(model).length) note += ' · ghost: revision ' + model.previous.ordinal;
    } else note = model.compare || '';
    setText('revision-status', note).title = note;
    setHidden('revision-status', !note);
  }
  function pickRevision(index) {
    var stops = revisionStops();
    if (!stops.length) return null;
    index = Math.max(0, Math.min(stops.length - 1, Math.round(index)));
    rev.pinned = index === stops.length - 1 ? null : stops[index].ordinal;
    if (source !== 'revisions') { source = 'revisions'; $('view3d-source').value = source; }
    renderRevisionTimeline();
    modelKey = revisionKey(); modelFailures = 0; modelRetryAt = 0;
    loadModel();
    return rev.pinned;
  }
  function showRevision(ordinal) {
    var stops = revisionStops(), index = -1;
    stops.forEach(function (s, i) { if (s.ordinal === ordinal) index = i; });
    return index < 0 ? undefined : pickRevision(index);
  }
  function revisionKey() {
    var ordinal = revisionShown(), stop = revisionStops().filter(function (s) { return s.ordinal === ordinal; })[0];
    return JSON.stringify(['revisions', ordinal, !!(stop && stop.retained)]);
  }

  // -- Status (ADR-542, an editor since ADR-572, drawn by status.js since ADR-606) -----
  // What the project is doing and how training is going, from /api/project's
  // `stage` on the page's own poll.
  // The Training editor reads the run picked as the 3D source, else the stage's (ADR-790).
  function renderStatus() {
    if (!window.CadexStatus || !state.review) return;
    window.CadexStatus.select(source.indexOf('run:') === 0 ? source.slice(4) : null);
    window.CadexStatus.render(state.review);
  }

  // Text and attributes are written only when they change, so an idle poll adds no nodes.
  function setText(id, value) { var node = $(id); if (node.textContent !== value) node.textContent = value; return node; }
  function setHidden(id, hidden) { var node = $(id); if (node.hidden !== hidden) node.hidden = hidden; }

  // -- 2D viewport -------------------------------------------------------------------
  // Everything flat the project has: its drawings, its presentation images,
  // its documents, its evaluations' films, and each run's training curves.
  // Images pan and zoom; a rollout video plays in place.
  var sheet = { key: null, shownKey: null, list: [], kind: null, view: { scale: 1, x: 0, y: 0, fitted: true } };
  var CURVES = [['curve', 'reward'], ['loss_curve', 'loss'], ['episode_steps_curve', 'episode length'], ['action_std_curve', 'action std']];

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
    // Newest first: a pass's two heroes (ADR-570), then each filmed seed's
    // rollout video and its two sheets (ADR-541).
    (review.evaluations || []).slice().reverse().forEach(function (e) {
      var film = e.film || {}, heroes = e.heroes || {};
      var title = (e.task_label || e.task_output || e.name) + ' ' + e.verdict + ' ' + e.passed + '/' + e.seeds +
                  (e.relation === 'historical' ? ' (earlier)' : '');
      [['hero', 'hero'], ['print_bed', 'print bed']].forEach(function (part) {
        if (e.verdict !== 'pass' || !heroes[part[0]]) return;
        list.push({ key: 'hero:' + e.name + ':' + heroes[part[0]], group: 'Evaluations', kind: 'image',
                    url: 'evaluation/' + encodeURIComponent(e.name) + '/' + encodeURIComponent(heroes[part[0]]) + '?v=' + e.stamp,
                    label: title + ' · ' + part[1] });
      });
      // ...and its shove video, with the pushes and the ending beside it (ADR-571).
      var shove = e.shove || {};
      if (e.verdict === 'pass' && shove.video) {
        list.push({ key: 'shove:' + e.name + ':' + shove.video, group: 'Evaluations', kind: 'video',
                    url: 'evaluation/' + encodeURIComponent(e.name) + '/' + encodeURIComponent(shove.video) + '?v=' + e.stamp,
                    label: title + ' · shoves', caption: shove.caption || '' });
      }
      if (film.state !== 'ready') return;
      (film.sheets || []).forEach(function (s) {
        [['video', 'video', 'video'], ['overview', 'image', 'filmstrip'], ['detail', 'image', 'detail']].forEach(function (part) {
          if (!s[part[0]]) return;
          list.push({ key: 'film:' + e.name + ':' + s[part[0]], group: 'Evaluations', kind: part[1],
                      url: 'evaluation/' + encodeURIComponent(e.name) + '/' + encodeURIComponent(s[part[0]]) + '?v=' + e.stamp,
                      label: title + ' · seed ' + s.seed + ' · ' + part[2] });
        });
      });
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
    if (item.kind === 'video') {
      stage.appendChild(el('video', { src: item.url, controls: true, loop: true, muted: true, playsInline: true,
                                      autoplay: true, id: 'sheet-video', ariaLabel: item.label }));
      if (item.caption) stage.appendChild(el('p', { id: 'sheet-caption', text: item.caption }));
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
    return json('api/run/' + encodeURIComponent(item.run)).then(function (record) {
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
    renderHeader(); renderRevisions(); renderSources(); followTraining(); renderStatus(); renderCheckpoints(); renderRevisionTimeline(); renderSheetSources();
  }

  function runModelKey(review, name) {
    var run = (review.runs || []).filter(function (r) { return r.run === name; })[0] || {};
    var artifacts = (run.resolved && run.resolved.artifacts) || {};
    return JSON.stringify(['run:' + name, run.status, artifacts.trace || null, artifacts.model_xml || null]);
  }

  // The poll is the project read alone: a model it starts loading is
  // handed back to the caller but never holds up the next poll, so the page stays live while a large model comes in.
  function poll() {
    if (pendingPoll) return pendingPoll;
    var started = performance.now(), model = null;
    var read = fetch('api/project', { cache: 'no-store' }).then(function (response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.text();
    }).then(function (body) {
      lastPoll.project_bytes = body.length;
      var review = JSON.parse(body);
      state.review = review; state.lastOk = new Date(); state.stale = false; state.error = null;
      render();
      lastPoll.ms = performance.now() - started;
      var key = sourceKey(review);
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

  // A 3D viewport: its own viewer, camera, gizmo, style, lighting, follow and trail, over the one model.
  function addView(ref, tools) {
    var canvas = ref('viewer'), viewer = window.CadexViewer.create(canvas);
    var view = { viewer: viewer, canvas: canvas, tools: tools, body: ref('model'), follow: false, style: renderStyle, look: look.name,
                 styleGroup: ref('view3d-style'), lookSelect: ref('view3d-look'), followButton: ref('play-follow'),
                 trail: 'off', trailSelect: ref('view3d-trail'), gizmoOn: true, gizmoToggle: ref('view3d-gizmo-toggle'),
                 heat: false, heatButton: ref('view3d-heat'), primitives: true, primitivesButton: ref('view3d-primitives') };
    view.gizmo = window.CadexGizmo.create(viewer, ref('view3d-gizmo'), canvas);
    var first = !state.views.first();
    view.styleGroup.addEventListener('click', function (event) {
      var button = event.target.closest('button');
      if (button) applyStyle(button.dataset.style, view);
    });
    view.lookSelect.addEventListener('change', function () { applyLook({ name: view.lookSelect.value }, view); });
    ref('model-fit').addEventListener('click', function () { viewer.fit(); });
    view.followButton.addEventListener('click', function (event) { event.stopPropagation(); applyFollow(!view.follow, view); });
    if (window.ResizeObserver) new ResizeObserver(function () { viewer.draw(); }).observe(canvas);
    view.trailSelect.addEventListener('change', function () { applyTrail(view.trailSelect.value, view); });
    view.gizmoToggle.addEventListener('click', function () { applyGizmo(!view.gizmoOn, view); });
    view.heatButton.addEventListener('click', function () { applyHeat(!view.heat, view); });
    view.primitivesButton.addEventListener('click', function () { applyPrimitives(!view.primitives, view); });
    if (first) view.follow = followCam;
    view.followButton.setAttribute('aria-pressed', String(view.follow));
    state.views.add(view);
    viewer.setLook(view.look); setViewStyle(view, view.style);
    if (!first && view.follow && playback && track) viewer.followTo(pointAt(playT), true);
    // A copy starts from the first's trail and axes; the first from what this browser kept.
    var lead = first ? null : firstView();
    applyTrail(lead ? lead.trail : trailPref, view);
    applyGizmo(lead ? lead.gizmoOn : gizmoPref, view);
    applyPrimitives(lead ? lead.primitives : primitivesPref, view);
    view.primitivesButton.hidden = !hasPrimitives();
    return view;
  }
  // A copy of an editor that may be shown more than once (ADR-729), from its pristine markup.
  var templates = {}, shared = {}, MULTI = { view3d: true, activations: true, network: true };
  function makeCopy(type) {
    var copy = window.CadexViewports.copy(templates[type]), ref = function (name) { return window.CadexViewports.ref(copy.home, name); };
    $('editor-shelf').appendChild(copy.home);
    if (type === 'view3d') {
      addView(ref, copy.tools);
      // The model's status line is the first viewport's (the source, the scrubbers and the
      // timeline are the Version editor's, ADR-770). The first's element as kept at the start: a
      // copy is made while the layout builds its areas, when the first may not be in the page.
      window.CadexViewports.mirror(shared.timelines, copy.body.querySelector('.timelines'));
    } else if (type === 'activations') {
      state.activations.addMotors({ body: ref('activations'), motors: ref('activations-motors'), bars: ref('activations-bars'),
                                    detail: ref('activations-detail'), status: ref('activations-status'),
                                    views: ref('activations-views'), ramp: copy.body.querySelector('.ramp-bar') });
    } else if (type === 'network') {
      state.activations.addNetwork({ network: ref('network'), networkStatus: ref('network-status'), layers: ref('network-layers'),
                                     paths: ref('network-paths'), networkViews: ref('network-views') });
    }
    return { title: $('editor-' + type).dataset.title, short: $('editor-' + type).dataset.short, home: copy.home, tools: copy.tools, body: copy.body };
  }

  function initialize() {
    if (NAME == null) $('home').hidden = true;
    var editors = {};
    ORDER.forEach(function (type) {
      var home = $('editor-' + type);
      editors[type] = { title: home.dataset.title, short: home.dataset.short, home: home,
                        tools: home.querySelector('.editor-tools'), body: home.querySelector('.editor-body') };
      if (MULTI[type]) {
        templates[type] = home.cloneNode(true);
        var made = {};
        editors[type].multi = true;
        editors[type].instance = function (k) { return made[k] || (made[k] = makeCopy(type)); };
        editors[type].copies = function () { return Object.keys(made).map(function (k) { return made[k]; }); };
      }
    });
    shared = { timelines: $('model').querySelector('.timelines') };
    state.views = window.CadexViewports.group();
    state.viewer = state.views.viewer;
    var firstRef = function (name) { return $(name); };
    addView(firstRef, editors.view3d.tools);
    state.gizmo = firstView().gizmo;
    state.activations = window.CadexActivations.create({ viewports: function () { return views().map(function (v) { return { viewer: v.viewer, heat: v.heat }; }); },
                                                         body: $('activations'),
                                                         motors: $('activations-motors'), bars: $('activations-bars'),
                                                         detail: $('activations-detail'), status: $('activations-status'),
                                                         views: $('activations-views'),
                                                         network: $('network'), networkStatus: $('network-status'),
                                                         layers: $('network-layers'), paths: $('network-paths'),
                                                         networkViews: $('network-views'), ramp: document.querySelector('.activations-ramp .ramp-bar') });
    state.settings = window.CadexSettings.create({ preset: $('settings-heat-preset'), count: $('settings-heat-count'),
                                                   low: $('settings-heat-low'), mid: $('settings-heat-mid'), high: $('settings-heat-high'),
                                                   preview: $('settings-heat-preview'), reset: $('settings-heat-reset') });
    state.trailSettings = window.CadexSettings.createTrail({ mode: $('settings-trail-mode'), solid: $('settings-trail-solid'),
                                                             solidRow: $('settings-trail-solid-row'), age: $('settings-trail-age'),
                                                             preset: $('settings-trail-preset'), count: $('settings-trail-count'),
                                                             old: $('settings-trail-old'), mid: $('settings-trail-mid'), newest: $('settings-trail-new'),
                                                             preview: $('settings-trail-preview'), reset: $('settings-trail-reset') });
    // The trail's colours are every viewport's, from Settings.
    state.viewer.setTrailColours(window.CadexTrailColours.get());
    window.CadexTrailColours.onChange(function (c) { state.viewer.setTrailColours(c); });
    state.layout = window.CadexLayout.create({ root: $('screen'), shelf: $('editor-shelf'), editors: editors, order: ORDER,
                                               storageKey: 'cadex.layout.v7', defaultLayout: DEFAULT_LAYOUT, onChange: onLayout,
                                               companions: { view3d: 'version' } });
    state.outliner = window.CadexOutliner.create({ tree: $('outliner-tree'), filter: $('outliner-filter'), group: $('outliner-group'),
                                                   showAll: $('outliner-show-all'), summary: $('outliner-summary'), scope: $('model'),
                                                   viewer: function () { return state.viewer; } });
    // A click on a solid selects its row; Shift, Ctrl or Cmd adds or removes it.
    if (state.viewer.setOnPick) state.viewer.setOnPick(function (name, how) { state.outliner.pick(name, !!(how && how.add)); });
    applyMeshLines();
    applyReflections();
    applyLook();
    applyStyle(renderStyle);

    $('view3d-source').addEventListener('change', function () { ckpt.chosenSource = true; setSource($('view3d-source').value); });
    $('style-choice').addEventListener('click', function (event) {
      var button = event.target.closest('button');
      if (button) applyStyle(button.dataset.style);
    });
    $('mesh-lines').addEventListener('change', function () { applyMeshLines({ shown: $('mesh-lines').checked }); });
    $('mesh-strength').addEventListener('input', function () { applyMeshLines({ strength: $('mesh-strength').value }); });
    $('reflections').addEventListener('input', function () { applyReflections($('reflections').value); });
    $('look-choice').addEventListener('change', function () { applyLook({ name: $('look-choice').value }); });
    $('occlusion').addEventListener('change', function () { applyLook({ occlusion: $('occlusion').checked }); });
    $('detail').addEventListener('change', function () { applyLook({ detail: $('detail').checked }); });
    $('play-toggle').addEventListener('click', function () { ckpt.paused = !!playing; togglePlayback(); });
    wireStops();
    $('revision-pick').addEventListener('input', function () { pickRevision(Number($('revision-pick').value)); });
    $('revision-list').addEventListener('click', function (event) {
      var row = event.target.closest('li[data-ordinal]');
      if (!row) return;
      ckpt.chosenSource = true;
      showRevision(Number(row.dataset.ordinal));
      $('revision-panel').open = false;
    });
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
    document.addEventListener('cadex-theme', function () {
      views().forEach(function (v) { if (v.style === 'wireframe') setViewStyle(v, 'wireframe'); });
    });
    renderThemeChoice();
    $('layout-reset').addEventListener('click', function () { state.layout.reset(); });
    $('layout-presets').addEventListener('click', function (event) {
      var button = event.target.closest('button[data-preset]');
      if (!button) return;
      state.layout.preset(button.dataset.preset);
      $('view-panel').open = false;
    });
    wireMenus();

    // Each canvas follows its box; redraw whenever the box changes.
    if (window.ResizeObserver) {
      new ResizeObserver(onLayout).observe($('sheet-stage'));
    }
    loadProjects();
    poll().then(function () { readyResolve(true); });
    setInterval(poll, POLL_MS);
  }

  window.cadexReview = {
    ready: ready,
    // A read that starts after this call: a poll already in flight may have asked before the
    // change the caller is waiting for, so it is waited out, not returned.
    refresh: function () { return (pendingPoll || Promise.resolve()).then(function () { return poll(); }); },
    viewer: function () { return state.viewer; },
    layout: function () { return state.layout; },
    gizmo: function () { return state.gizmo; },
    activations: function () { return state.activations; },
    setStyle: applyStyle,
    renderStyle: function () { return renderStyle; },
    setMeshLines: applyMeshLines,
    meshLines: function () { return { shown: meshLines.shown, strength: meshLines.strength }; },
    setReflections: applyReflections,
    reflections: function () { return reflections; },
    setLook: applyLook,
    look: function () { return { name: look.name, occlusion: look.occlusion, detail: look.detail }; },
    outliner: function () { return state.outliner; },
    setSource: function (value) { ckpt.chosenSource = true; return setSource(value); },
    setSheet: setSheet,
    sheets: function () { return sheet.list.map(function (item) { return { key: item.key, group: item.group, kind: item.kind, label: item.label }; }); },
    playback: function () { return playback && { times_s: playback.times_s, t: playT, playing: !!playing, looping: looping, checkpoint: ckpt.playing,
                                                  reference: playback.reference ? playback.task : null,
                                                  goto: playback.goto ? { points: playback.goto.points.length, label: $('play-goto').textContent } : null }; },
    checkpoints: function () {
      return { items: ckpt.items.map(function (item) { return { stem: item.stem, state: item.state, iteration: item.iteration, reward_per_step: item.reward_per_step }; }),
               pending: ckpt.pending, pinned: ckpt.pinned, playing: ckpt.playing, source: source,
               film: ckpt.film, films: ckpt.films.map(function (f) { return { film: f.film, group: f.group, name: f.name, state: f.state, duration_s: f.duration_s, points: f.points }; }) };
    },
    pickCheckpoint: pickCheckpoint,
    pickFilm: pickFilm,
    revisions: function () {
      var current = state.review && state.review.accepted.revision, model = state.model && state.model.view === 'revision' ? state.model : null;
      return { stops: revisionStops().map(function (s) { return { ordinal: s.ordinal, revision: s.revision, retained: !!s.retained, current: s.revision === current }; }),
               pinned: rev.pinned, shown: source === 'revisions' ? revisionShown() : null, source: source,
               model: model && { ordinal: model.ordinal, available: model.available, changed: model.changed,
                                 previous: model.previous && model.previous.ordinal,
                                 parts: model.components.reduce(function (o, c) { o[c.name] = c.sha256; return o; }, {}) } };
    },
    pickRevision: pickRevision,
    showRevision: showRevision,
    seek: seek,
    setTrail: applyTrail,
    trail: function () { return { style: trailPref, course: !!trailCourse.served, prints: trailCourse.prints, scene: state.viewer.trail && state.viewer.trail() }; },
    setGizmo: applyGizmo,
    setHeat: function (on, i) { return applyHeat(on, views()[i || 0]); },
    setPrimitives: function (on, i) { return applyPrimitives(on, views()[i || 0]); },
    setFollow: applyFollow,
    follow: function () { return { on: followCam, tracked: !!track, camera: state.viewer.camera && state.viewer.camera() }; },
    view: function (i) { var v = views()[i]; return v ? v.viewer : null; },
    views: function () {
      return views().map(function (v) { return { style: v.style, look: v.look, follow: v.follow, trail: v.trail, axes: v.gizmoOn, heat: v.heat, primitives: { on: v.primitives, offered: !v.primitivesButton.hidden }, camera: v.viewer.camera(), gizmo: v.gizmo }; });
    },
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
