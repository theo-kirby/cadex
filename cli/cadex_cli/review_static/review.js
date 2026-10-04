// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The project page (ADR-533): the accepted model, and the three ways to
// steer it — a design turn, a parameter slider, a revision verdict — each a
// `cadex` command the server runs (ADR-503, ADR-504, ADR-506). Polls
// /api/project for what changed and reloads the model only when the accepted
// revision moves.
(function () {
  'use strict';

  // Served alone (`cadex review`) the page is at `/`; served from a projects
  // directory (`cadex app`) it is at `/p/<name>/`, and every request it makes
  // carries that prefix.
  var BASE = (location.pathname.match(/^\/p\/[^/]+(?=\/)/) || [''])[0];
  var POLL_MS = 2000;
  // A running turn's transcript is read this often; an idle read is a few bytes.
  var TURN_POLL_MS = 1000;
  // This launch's write token, written into the page by the server; every
  // POST carries it (ADR-503).
  var WRITE_TOKEN = (document.querySelector('meta[name="cadex-write-token"]') || {}).content || '';
  var state = { review: null, lastOk: null, stale: false, error: null, model: null, viewer: null };
  var pendingPoll = null, modelKey = null;
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
  function post(path, body) {
    return fetch(BASE + path, {
      method: 'POST', cache: 'no-store',
      headers: { 'Content-Type': 'application/json', 'X-Cadex-Token': WRITE_TOKEN },
      body: JSON.stringify(body)
    }).then(function (response) { return response.json(); });
  }
  // A poll already in flight may predate a write; the next one cannot.
  function repoll() { return (pendingPoll || Promise.resolve()).catch(function () {}).then(poll); }

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

  // Parameters: a declared number with a range is a slider; anything else
  // reads as its value. A parameter never set reads at its default.
  var paramsKey = null, writing = null, lastWrite = null;

  function renderParams() {
    var accepted = state.review.accepted;
    var values = accepted.available ? accepted.param_values || {} : {}, specs = accepted.available ? accepted.param_specs : null;
    var byName = {};
    (Array.isArray(specs) ? specs : []).forEach(function (spec) { if (spec && spec.name) byName[spec.name] = spec; });
    var names = Object.keys(values);
    Object.keys(byName).forEach(function (name) { if (names.indexOf(name) < 0) names.push(name); });
    // Rebuilt only when what it shows changes, and never under a write in
    // flight, so a poll does not snatch a slider from the hand moving it.
    var key = JSON.stringify([values, specs]);
    if (writing || key === paramsKey) return;
    paramsKey = key;
    var body = $('params').querySelector('tbody');
    body.textContent = '';
    names.sort().forEach(function (name) {
      var spec = byName[name] || {};
      body.appendChild(el('tr', { 'data-param': name }, [
        el('th', { text: spec.label || name, title: name + (spec.unit ? ' (' + spec.unit + ')' : '') }),
        el('td', {}, [paramValue(name, values[name], spec)])
      ]));
    });
    $('params-empty').hidden = names.length > 0;
  }

  function paramValue(name, value, spec) {
    var current = typeof value === 'number' ? value : spec.default;
    var bounded = typeof current === 'number' && isFinite(spec.min) && isFinite(spec.max) && spec.max > spec.min;
    var unit = spec.unit ? ' ' + spec.unit : '';
    if (!bounded || !WRITE_TOKEN) return el('span', { text: fmt(value) + unit });
    var shown = el('output', { text: fmt(current) + unit });
    var slider = el('input', { type: 'range', min: String(spec.min), max: String(spec.max),
                               step: String(spec.step > 0 ? spec.step : 'any'), value: String(current), 'data-param': name });
    slider.setAttribute('aria-label', spec.label || name);
    slider.addEventListener('input', function () { shown.textContent = fmt(Number(slider.value)) + unit; });
    // One write per release, not one per pixel of the drag.
    slider.addEventListener('change', function () { writeParams(name, Number(slider.value)); });
    return el('span', { className: 'param-slider' }, [slider, shown]);
  }

  function writeParams(name, value) {
    var status = $('params-write'), started = performance.now(), values = {}, reply = null;
    values[name] = value;
    writing = { name: name, value: value };
    paramsKey = null;
    $('params').querySelectorAll('input[type=range]').forEach(function (input) { input.disabled = true; });
    status.dataset.state = 'pending';
    status.textContent = 'rebuilding…';
    return post('/api/params', { values: values }).then(function (body) {
      reply = body;
      writing = null;
      if (!reply.ok) throw new Error(reply.error || 'exit ' + reply.exit);
      return repoll();
    }).then(function () {
      lastWrite = { ok: true, name: name, value: value, revision: reply.accepted_revision, digest: reply.digest,
                    server_s: reply.seconds, total_ms: performance.now() - started };
      status.dataset.state = 'idle';
      status.textContent = '';
    }).catch(function (error) {
      writing = null; paramsKey = null;
      lastWrite = { ok: false, name: name, value: value, error: error.message };
      status.dataset.state = 'error';
      status.textContent = name + ' = ' + fmt(value) + ' refused: ' + error.message;
      if (state.review) renderParams();
    });
  }

  // The design turn (ADR-504): one `cadex -p` child per project, started
  // here or by another page on this server; its transcript is read from an
  // offset, so each read carries only what arrived since the last.
  var turn = { id: null, state: 'idle', text: '', next: 0, reply: null, prompt: '' }, turnRequest = null;

  function renderTurn() {
    var status = $('turn-status'), transcript = $('turn-transcript'), running = turn.state === 'running';
    status.dataset.state = turn.state;
    $('turn-start').disabled = running;
    $('turn-prompt').disabled = running;
    if (turn.state === 'idle') status.textContent = '';
    else if (running) status.textContent = 'running…';
    else if (turn.state === 'interrupted') status.textContent = 'interrupted';
    else if (turn.reply && turn.reply.ok) status.textContent = 'done';
    else status.textContent = (turn.reply && turn.reply.error) || 'the turn failed';
    transcript.hidden = !turn.text;
    if (transcript.textContent !== turn.text) {
      var pinned = transcript.scrollTop + transcript.clientHeight >= transcript.scrollHeight - 4;
      transcript.textContent = turn.text;
      if (pinned) transcript.scrollTop = transcript.scrollHeight;
    }
  }

  function pollTurn() {
    if (turnRequest) return turnRequest;
    turnRequest = fetch(BASE + '/api/turn?since=' + turn.next, { cache: 'no-store' }).then(function (response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.json();
    }).then(function (reply) {
      if (reply.state === 'idle') return;
      var wasRunning = turn.state === 'running';
      if (reply.id !== turn.id) {
        // Another turn, or this one now read from the project's store: its
        // transcript starts over, so read it from the top.
        turn = { id: reply.id, state: wasRunning ? 'running' : reply.state, text: '', next: 0, reply: null,
                 prompt: reply.prompt, source: reply.source };
        turnRequest = null;
        return pollTurn();
      }
      turn.text += reply.text; turn.next = reply.next; turn.state = reply.state; turn.reply = reply.reply; turn.source = reply.source;
      renderTurn();
      // The turn ended: the accepted revision may have moved under the model.
      if (wasRunning && reply.state !== 'running') return repoll();
    }).catch(function () {}).finally(function () { turnRequest = null; });
    return turnRequest;
  }

  function startTurn(prompt, resume) {
    var status = $('turn-status');
    status.dataset.state = 'pending';
    status.textContent = 'starting…';
    return post('/api/turn', { prompt: prompt, resume: !!resume, images: [] }).then(function (reply) {
      if (!reply.ok) throw new Error(reply.error || 'refused');
      turn = { id: reply.turn.id, state: reply.turn.state, text: reply.turn.text, next: reply.turn.next,
               reply: reply.turn.reply, prompt: reply.turn.prompt };
      $('turn-prompt').value = '';
      renderTurn();
      return reply.turn;
    }).catch(function (error) {
      status.dataset.state = 'error';
      status.textContent = 'not started: ' + error.message;
      return null;
    });
  }

  // Revisions (ADR-506): accept the current one, reject it for the one
  // before, or restore any earlier one.
  var revisionsKey = null, revisionWriting = false, lastRevision = null;

  function renderRevisions() {
    var trail = state.review.revisions || [], current = state.review.accepted && state.review.accepted.revision;
    var key = JSON.stringify([trail, current, revisionWriting]);
    if (key === revisionsKey) return;
    revisionsKey = key;
    $('revision-accept').disabled = revisionWriting || !current;
    $('revision-reject').disabled = revisionWriting || !current || trail.length < 2;
    var list = $('revision-list');
    list.textContent = '';
    // The trail comes newest first.
    trail.forEach(function (entry) {
      var here = entry.revision === current;
      var item = el('li', { value: entry.ordinal, 'data-revision': entry.revision, 'data-ordinal': String(entry.ordinal), 'data-current': String(here) }, [
        el('span', { text: here ? 'current' : when(entry.saved_at), title: entry.revision })
      ]);
      if (!here) {
        var restore = el('button', { type: 'button', className: 'revision-restore', text: 'Restore' });
        restore.disabled = revisionWriting;
        restore.addEventListener('click', function () { writeRevision('restore', String(entry.ordinal)); });
        item.appendChild(restore);
      }
      list.appendChild(item);
    });
  }

  function writeRevision(action, revision) {
    var status = $('revision-status');
    revisionWriting = true; revisionsKey = null; renderRevisions();
    status.dataset.state = 'pending';
    status.textContent = action + '…';
    return post('/api/revision', { action: action, revision: revision || '', note: '' }).then(function (reply) {
      if (!reply.ok) throw new Error(reply.error || 'exit ' + reply.exit);
      lastRevision = reply;
      status.dataset.state = 'idle';
      status.textContent = '';
      revisionWriting = false;
      return repoll().then(function () { return reply; });
    }).catch(function (error) {
      revisionWriting = false; revisionsKey = null;
      status.dataset.state = 'error';
      status.textContent = action + ' refused: ' + error.message;
      if (state.review) renderRevisions();
      return null;
    });
  }

  function loadModel() {
    var status = $('model-status');
    status.dataset.state = 'loading'; status.textContent = 'loading model…';
    return fetch(BASE + '/api/model/accepted', { cache: 'no-store' }).then(function (response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.json();
    }).then(function (manifest) {
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
      // Mesh URLs in the manifest are server-absolute; BASE mounts them.
      return state.viewer.load(manifest, function (url, options) { return window.fetch(BASE + url, options); }).then(function () {
        status.dataset.state = 'loaded';
        status.textContent = '';
      });
    }).catch(function (error) {
      status.dataset.state = 'error';
      status.textContent = 'model failed to load: ' + error.message;
    });
  }

  function render() {
    renderFreshness();
    if (!state.review) return;
    renderHeader(); renderParams(); renderRevisions();
  }

  function poll() {
    if (pendingPoll) return pendingPoll;
    var started = performance.now();
    pendingPoll = fetch(BASE + '/api/project', { cache: 'no-store' }).then(function (response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.text();
    }).then(function (body) {
      lastPoll.project_bytes = body.length;
      var review = JSON.parse(body);
      state.review = review; state.lastOk = new Date(); state.stale = false; state.error = null;
      render();
      lastPoll.ms = performance.now() - started;
      var key = JSON.stringify([review.accepted.revision, review.accepted.digest]);
      if (key !== modelKey) { modelKey = key; return loadModel(); }
    }).catch(function (error) {
      state.stale = true; state.error = error.message;
      renderFreshness();
    }).finally(function () { pendingPoll = null; });
    return pendingPoll;
  }

  function initialize() {
    if (!BASE) $('home').hidden = true;
    state.viewer = window.CadexViewer.create($('viewer'));
    $('model-fit').addEventListener('click', function () { state.viewer.fit(); });
    $('turn-start').addEventListener('click', function () {
      var prompt = $('turn-prompt').value.trim();
      if (prompt) startTurn(prompt, $('turn-resume').checked);
    });
    $('revision-accept').addEventListener('click', function () { writeRevision('accept', ''); });
    $('revision-reject').addEventListener('click', function () { writeRevision('reject', ''); });
    // The canvas follows its box; redraw whenever the box changes.
    if (window.ResizeObserver) new ResizeObserver(function () { if (state.viewer.draw) state.viewer.draw(); }).observe($('viewer'));
    poll().then(function () { readyResolve(true); });
    setInterval(poll, POLL_MS);
    pollTurn();
    setInterval(pollTurn, TURN_POLL_MS);
  }

  window.cadexReview = {
    ready: ready,
    refresh: poll,
    setParam: writeParams,
    lastWrite: function () { return lastWrite; },
    startTurn: startTurn,
    turn: function () { return { id: turn.id, state: turn.state, text: turn.text, reply: turn.reply, source: turn.source }; },
    revision: writeRevision,
    lastRevision: function () { return lastRevision; },
    viewer: function () { return state.viewer; },
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
