// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The app (ADR-534): three editors tiled by layout.js, after Blender's areas,
// under a menu bar (ADR-539).
//
//   3D viewport  the accepted model or a run's, shaded or hairline, a
//                run's rollout played back on a timeline, a training run's
//                checkpoints looped as they land (ADR-545), the design's
//                revisions on a timeline with a ghost and a tint (ADR-547) -- most
//                of the screen by default;
//   Status       what the project is doing, how training is going and what
//                the agent last did (ADR-542, ADR-550; an editor since
//                ADR-572) -- an area beside the 3D viewport by default;
//   2D viewport  the project's drawings, images, documents, evaluation films and training plots,
//                a split away;
//   Menu bar     File (the project), Revisions (the trail), View (theme,
//                render style, layout presets and reset, ADR-573).
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
  var ORDER = ['view3d', 'status', 'view2d'];
  // The 3D viewport with Status beside it; split an area for the 2D one.
  var DEFAULT_LAYOUT = { dir: 'row', sizes: [0.75, 0.25], children: [{ editor: 'view3d' }, { editor: 'status' }] };
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
  var renderStyle = readPref('cadex.render', STYLES, 'shaded');

  function renderSources() {
    var runs = (state.review.runs || []).map(function (run) { return run.run; });
    var history = (state.review.revisions || []).length > 0;
    var key = JSON.stringify([runs, history]);
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
    if (source === 'revisions' ? !history : source !== 'accepted' && runs.indexOf(source.slice(4)) < 0) { source = 'accepted'; modelKey = null; }
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
    var path = source === 'accepted' ? 'api/model/accepted'
             : source === 'revisions' ? 'api/model/revision/' + revisionShown()
             : 'api/model/run/' + encodeURIComponent(source.slice(4));
    if (modelAbort) modelAbort.abort();
    var controller = modelAbort = new AbortController(), signal = controller.signal;
    status.dataset.state = 'loading'; status.textContent = 'loading model…';
    stopPlayback(); playback = null; looping = false; ckpt.shown = null; $('playback').hidden = true;
    return fetchRetry(path, signal, 2).then(function (response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.json();
    }).then(function (manifest) {
      if (ticket !== modelLoad) return;
      state.model = manifest;
      if (manifest.view === 'revision') renderRevisionTimeline();
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
      // Mesh URLs in the manifest are relative to the page. Until every mesh
      // is in, the model drawn is the one before.
      var fetchMesh = function (url) { return fetchRetry(url, signal, 2); };
      if (manifest.view === 'revision') manifest = tintRevision(manifest);
      return state.viewer.load(manifest, fetchMesh).then(function () {
        if (ticket !== modelLoad) return;
        if (manifest.view === 'revision') return state.viewer.loadGhost(ghostOf(manifest), fetchMesh, parseInt(token('--ink-2').slice(1), 16), 0.22);
      }).then(function () {
        if (ticket !== modelLoad) return;
        modelFailures = 0;
        status.dataset.state = 'loaded';
        status.textContent = '';
        // A run with checkpoint rollouts plays them, its own rollout last.
        if (checkpointItems().items.length) { renderCheckpoints(); return null; }
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
  var playback = null, playT = 0, playing = null, looping = false;

  function loadPlayback(manifest, ticket) {
    var info = manifest.playback;
    if (!info || !info.url) return null;
    return json(info.url).then(function (served) {
      if (ticket !== modelLoad || !served.available || !served.times_s || served.times_s.length < 2) return;
      showPlayback(served);
    }).catch(function () { /* the model stands without its rollout */ });
  }
  function showPlayback(served) {
    playback = served;
    var slider = $('play-time'), times = served.times_s;
    slider.min = String(times[0]); slider.max = String(times[times.length - 1]);
    $('playback').hidden = false;
    seek(times[0]);
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
  var ckpt = { items: [], pending: 0, pinned: null, shown: null, playing: null, paused: false, chosenSource: false };

  function checkpointItems() {
    var stage = (state.review && state.review.stage) || {}, block = stage.checkpoints;
    if (!block || !stage.run || source !== 'run:' + stage.run) return { items: [], pending: 0 };
    var items = (block.items || []).slice(), own = state.model && state.model.available && state.model.playback;
    // The run's own rollout, once it has one, is its newest policy.
    if (items.length && own && own.available && own.url) {
      items.push({ stem: 'final', tag: 'final', state: 'ready', url: own.url, iteration: null, reward_per_step: null, final: true });
    }
    return { items: items, pending: block.pending || 0 };
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
    return 'iteration ' + (item.iteration + 1) + ' · reward ' + (item.reward_per_step == null ? '—' : fmt(item.reward_per_step));
  }
  function restPoses() {
    var poses = {};
    ((state.model && state.model.components) || []).forEach(function (c) { if (c.placement) poses[c.name] = c.placement; });
    return poses;
  }
  function renderCheckpoints() {
    var got = checkpointItems(), items = got.items, box = $('checkpoints');
    ckpt.items = items; ckpt.pending = got.pending;
    setHidden('checkpoints', !items.length);
    if (!items.length) { ckpt.shown = null; ckpt.playing = null; return; }
    var stems = items.map(function (item) { return item.stem; });
    if (ckpt.pinned && stems.indexOf(ckpt.pinned) < 0) ckpt.pinned = null;
    var index = ckpt.pinned ? stems.indexOf(ckpt.pinned) : items.length - 1, item = items[index];
    var pick = $('checkpoint-pick');
    if (pick.max !== String(items.length - 1)) pick.max = String(items.length - 1);
    if (pick.value !== String(index)) pick.value = String(index);
    if (box.dataset.follow !== String(!ckpt.pinned)) box.dataset.follow = String(!ckpt.pinned);
    if (box.dataset.state !== item.state) box.dataset.state = item.state;
    setText('checkpoint-label', checkpointName(item) + ' · ' + (index + 1) + '/' + items.length + (ckpt.pinned ? '' : ' · newest'));
    var note = item.state === 'failed' ? 'rollout failed: ' + item.reason + (item.error ? ' — ' + item.error : '')
             : got.pending ? got.pending + ' newer checkpoint' + (got.pending > 1 ? 's' : '') + ' rolling out' : '';
    setText('checkpoint-status', note).title = note;
    setHidden('checkpoint-status', !note);
    var key = item.stem + ':' + item.state + ':' + (item.sha256 || item.url || '');
    // Poses go onto that run's own model, once it is drawn.
    var drawn = state.model && state.model.run === source.slice(4) && $('model-status').dataset.state === 'loaded';
    if (key === ckpt.shown || !drawn) return;
    ckpt.shown = key;
    showCheckpoint(item, key);
  }
  function showCheckpoint(item, key) {
    var ticket = modelLoad;
    stopPlayback(); playback = null; ckpt.playing = null;
    if (item.state !== 'ready') {
      $('playback').hidden = true;
      state.viewer.setPoses(restPoses());
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
    if (!on) return;
    var ordinal = revisionShown(), index = 0, current = state.review.accepted && state.review.accepted.revision;
    stops.forEach(function (s, i) { if (s.ordinal === ordinal) index = i; });
    var stop = stops[index], pick = $('revision-pick');
    if (pick.max !== String(stops.length - 1)) pick.max = String(stops.length - 1);
    if (pick.value !== String(index)) pick.value = String(index);
    if (box.dataset.follow !== String(rev.pinned == null)) box.dataset.follow = String(rev.pinned == null);
    var retained = !!stop.retained, stateName = retained ? 'retained' : 'missing';
    if (box.dataset.state !== stateName) box.dataset.state = stateName;
    box.dataset.ordinal = String(stop.ordinal);
    setText('revision-label', 'revision ' + stop.ordinal + (stop.revision === current ? ' · current' : ' · ' + brief(stop.saved_at)) +
            ' · ' + (index + 1) + '/' + stops.length + (rev.pinned == null ? ' · newest' : ''));
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

  // -- Status (ADR-542, an editor since ADR-572) --------------------------------------
  // What the project is doing and how training is going, from /api/project's
  // `stage` on the page's own poll.
  var STAGE_LABELS = { idle: 'idle', designing: 'designing', training: 'training', evaluating: 'evaluating', stopped: 'stopped', failed: 'failed' };

  // Text and attributes are written only when they change, so an idle poll adds no nodes.
  function setText(id, value) { var node = $(id); if (node.textContent !== value) node.textContent = value; return node; }
  function setHidden(id, hidden) { var node = $(id); if (node.hidden !== hidden) node.hidden = hidden; }
  function ago(stamp, now) {
    var t = stamp ? Date.parse(stamp) : NaN;
    if (isNaN(t)) return '';
    var s = Math.max(0, (now - t) / 1000);
    return s < 60 ? 'just now' : s < 3600 ? Math.round(s / 60) + ' min ago'
         : s < 86400 ? Math.round(s / 3600) + ' h ago' : Math.round(s / 86400) + ' d ago';
  }
  function duration(seconds) {
    if (seconds == null || !isFinite(seconds)) return '—';
    var s = Math.round(seconds);
    return s < 60 ? s + ' s' : s < 3600 ? Math.round(s / 60) + ' min' : (s / 3600).toFixed(1) + ' h';
  }
  function spark(id, points) {
    var line = $(id).querySelector('polyline'), values = (points || []).map(function (p) { return p[1]; });
    var out = '';
    if (values.length > 1) {
      var lo = Math.min.apply(null, values), hi = Math.max.apply(null, values), span = hi - lo || 1;
      out = values.map(function (v, i) {
        return (i / (values.length - 1) * 100).toFixed(1) + ',' + (22 - (v - lo) / span * 20).toFixed(1);
      }).join(' ');
    }
    if (line.getAttribute('points') !== out) line.setAttribute('points', out);
  }

  function renderStatus() {
    var review = state.review, stage = review.stage || { state: 'idle', training: null, runs: 0 };
    var t = stage.training, now = Date.parse(review.served_at) || Date.now();
    var node = $('status'), name = STAGE_LABELS[stage.state] ? stage.state : 'idle';
    if (node.dataset.stage !== name) node.dataset.stage = name;
    setText('status-stage', STAGE_LABELS[name]).dataset.stage = name;
    var trail = review.revisions || [], line;
    if (name === 'training' && t) {
      line = t.iteration != null && t.iteration >= 0
        ? 'iteration ' + (t.iteration + 1) + ' / ' + fmt(t.total) + (t.eta_s ? ' · ETA ' + duration(t.eta_s) : '')
        : 'starting';
      if (t.state === 'stale') line += ' · no update ' + duration(t.age_s);
    } else if (name === 'designing') {
      line = (stage.reason || 'revision accepted') + ' · ' + ago(stage.since, now);
    } else if (name === 'evaluating') {
      var began = Date.parse(stage.since);
      line = (stage.reason || 'evaluating') + (isNaN(began) ? '' : ' · ' + duration(Math.max(0, (now - began) / 1000)));
    } else if (name === 'idle') {
      line = trail.length ? 'revision ' + trail[0].ordinal + ' accepted ' + ago(trail[0].saved_at, now) : 'nothing accepted yet';
    } else {
      line = stage.reason || '';
    }
    setText('status-line', line).title = line;
    renderActivity(review, now);
    // The run it reads, named when there is more than one to choose from.
    setHidden('status-run', !(stage.run && stage.runs > 1));
    setText('status-run', stage.run ? 'run ' + stage.run + (t && name !== 'training' ? ' · ' + t.state : '') : '');
    setHidden('status-stats', !t);
    setHidden('status-sparks', !t);
    var warning = t ? (t.warning || (t.state === 'stale' ? t.reason : '')) : '';
    setHidden('status-warning', !warning);
    setText('status-warning', warning);
    if (!t) return;
    setText('status-reward-now', fmt(t.reward_per_step));
    setText('status-best', t.best_reward_per_step == null ? '—' : fmt(t.best_reward_per_step) + ' @ ' + (t.best_iteration + 1));
    setText('status-loss-now', fmt(t.loss));
    setText('status-eta', name === 'training' && t.eta_s ? duration(t.eta_s) : '—');
    spark('status-reward', (t.spark || {}).curve);
    spark('status-loss', (t.spark || {}).loss_curve);
  }
  // The agent's newest call through cadex mcp (ADR-550), timed against the server's
  // clock. A call still running is logged as such (ADR-553) and is never idle; past
  // ACTIVITY_IDLE_S with no call in flight, the line reads as idle.
  var ACTIVITY_IDLE_S = 300, ACTIVITY_LIST = 5, activityKey = null;
  function activityText(e) {
    return e.tool + (e.args ? ' ' + e.args : '')
      + (e.outcome === 'error' ? ' · failed' + (e.detail ? ': ' + e.detail : '')
         : e.outcome === 'lost' ? ' · did not return' : e.outcome === 'running' ? ' · running' : '');
  }
  function renderActivity(review, now) {
    var activity = review.activity || {}, entries = activity.available ? activity.entries || [] : [];
    var newest = entries[0], node = $('status-activity'), name, line;
    if (!newest) {
      name = 'none'; line = activity.reason || 'no agent activity logged';
    } else {
      var t = Date.parse(newest.t), quiet = isNaN(t) ? Infinity : (now - t) / 1000;
      if (newest.outcome === 'running') {
        name = 'running'; line = activityText(newest) + ' ' + duration(isFinite(quiet) ? Math.max(0, quiet) : null);
      } else if (quiet > ACTIVITY_IDLE_S) {
        name = 'idle'; line = 'agent idle · last call ' + newest.tool + ' ' + ago(newest.t, now);
      } else {
        name = newest.outcome === 'error' || newest.outcome === 'lost' ? 'error' : 'active'; line = activityText(newest) + ' · ' + ago(newest.t, now);
      }
    }
    if (node.dataset.state !== name) node.dataset.state = name;
    setText('status-activity-line', line).title = line;
    setHidden('status-activity-log', entries.length < 2);
    var shown = entries.slice(0, ACTIVITY_LIST), key = JSON.stringify(shown);
    if (key === activityKey) return;
    activityKey = key;
    var list = $('status-activity-list');
    list.textContent = '';
    shown.forEach(function (e) {
      var item = document.createElement('li'), clock = (e.t || '').slice(11, 19);
      item.dataset.outcome = e.outcome;
      item.textContent = (clock ? clock + ' ' : '') + activityText(e);
      item.title = item.textContent;
      list.appendChild(item);
    });
  }

  // -- 2D viewport -------------------------------------------------------------------
  // Everything flat the project has: its drawings, its presentation images,
  // its documents, its evaluations' films, and each run's training curves.
  // Images pan and zoom; a rollout video plays in place.
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
    renderHeader(); renderRevisions(); renderStatus(); renderSources(); followTraining(); renderCheckpoints(); renderRevisionTimeline(); renderSheetSources();
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
      // The accepted model moves with every write; a run's moves when the
      // walk lands its export or its own rollout, which adds the final
      // policy's stop (ADR-554).
      var key = source === 'accepted' ? JSON.stringify([review.accepted.revision, review.accepted.digest])
              : source === 'revisions' ? revisionKey() : runModelKey(review, source.slice(4));
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
    if (NAME == null) $('home').hidden = true;
    var editors = {};
    ORDER.forEach(function (type) {
      var home = $('editor-' + type);
      editors[type] = { title: home.dataset.title, short: home.dataset.short, home: home,
                        tools: home.querySelector('.editor-tools'), body: home.querySelector('.editor-body') };
    });
    state.layout = window.CadexLayout.create({ root: $('screen'), shelf: $('editor-shelf'), editors: editors, order: ORDER,
                                               storageKey: 'cadex.layout.v4', defaultLayout: DEFAULT_LAYOUT, onChange: onLayout });
    state.viewer = window.CadexViewer.create($('viewer'));
    applyStyle(renderStyle);

    $('model-fit').addEventListener('click', function () { state.viewer.fit(); });
    $('view3d-source').addEventListener('change', function () { ckpt.chosenSource = true; setSource($('view3d-source').value); });
    [$('view3d-style'), $('style-choice')].forEach(function (group) {
      group.addEventListener('click', function (event) {
        var button = event.target.closest('button');
        if (button) applyStyle(button.dataset.style);
      });
    });
    $('play-toggle').addEventListener('click', function () { ckpt.paused = !!playing; togglePlayback(); });
    $('checkpoint-pick').addEventListener('input', function () { pickCheckpoint(Number($('checkpoint-pick').value)); });
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
    document.addEventListener('cadex-theme', function () { if (renderStyle === 'hairline') applyStyle('hairline'); });
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
    setSource: function (value) { ckpt.chosenSource = true; return setSource(value); },
    setSheet: setSheet,
    sheets: function () { return sheet.list.map(function (item) { return { key: item.key, group: item.group, kind: item.kind, label: item.label }; }); },
    playback: function () { return playback && { times_s: playback.times_s, t: playT, playing: !!playing, looping: looping, checkpoint: ckpt.playing }; },
    checkpoints: function () {
      return { items: ckpt.items.map(function (item) { return { stem: item.stem, state: item.state, iteration: item.iteration, reward_per_step: item.reward_per_step }; }),
               pending: ckpt.pending, pinned: ckpt.pinned, playing: ckpt.playing, source: source };
    },
    pickCheckpoint: pickCheckpoint,
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
