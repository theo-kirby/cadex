// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The review page. Polls /api/project for the run list (each run's telemetry
// as a bounded summary) and /api/run/<selected> for the one run whose
// histories and verified checkpoints are on screen (ADR-321); lets the reader
// pick the accepted project or one recorded run (and, on the Evaluation tab,
// one evaluation of a policy against its success spec), and shows exactly what the
// record says: a historical run is labelled as such and drawn from its own
// retained mesh, never from today's script. Its writes — a parameter slider
// a design turn, a comment and a revision verdict — are `cadex` commands the server runs (ADR-503 to ADR-506). Poll work is bounded: the run list is rebuilt only when it
// changes, and the telemetry panel only when the selected run's telemetry
// does, so an idle poll over a long history touches a constant number of
// nodes.
(function () {
  'use strict';

  // Served alone (`cadex review`) the page is at `/`; served from a projects
  // directory (`cadex app`) it is at `/p/<name>/`, and every request it makes
  // carries that prefix.
  var BASE = (location.pathname.match(/^\/p\/[^/]+(?=\/)/) || [''])[0];
  var POLL_MS = 2000;
  // A running turn's transcript is read this often; an idle read is a few bytes.
  var TURN_POLL_MS = 1000;
  var state = { review: null, selected: 'accepted', lastOk: null, stale: false, model: null, viewer: null,
                error: null, following: true, docKey: null, docRequest: 0, detail: null, showProxies: false,
                showDimensions: true };
  var pendingPoll = null;
  // This launch's write token, written into the page by the server; every
  // POST carries it (ADR-503).
  var WRITE_TOKEN = (document.querySelector('meta[name="cadex-write-token"]') || {}).content || '';
  var paramsKey = null, writing = null, lastWrite = null;
  // The last poll's measured cost, for the operator and the regression suite:
  // bytes of the run list, bytes of the selected run's detail, wall time.
  var lastPoll = { project_bytes: 0, detail_bytes: 0, ms: 0 };
  var sidebarKey = null, telemetryKey = null, detailRequest = 0;
  var readyResolve;
  var ready = new Promise(function (resolve) { readyResolve = resolve; });

  function $(id) { return document.getElementById(id); }
  function text(id, value) { $(id).textContent = value == null ? '' : String(value); }
  function clearChildren(el) { while (el.firstChild) el.removeChild(el.firstChild); }
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
  function bytes(value) {
    if (value == null || !isFinite(value)) return '—';
    var units = ['B', 'KB', 'MB', 'GB', 'TB'], n = value, i = 0;
    while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
    return (i ? n.toFixed(1) : String(n)) + ' ' + units[i];
  }
  function fmt(value) {
    if (value == null) return '—';
    if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toPrecision(5);
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  }

  function fetchJson(url, measure) {
    return fetch(url, { cache: 'no-store' }).then(function (response) {
      if (!response.ok) throw new Error(url + ': HTTP ' + response.status);
      return response.text();
    }).then(function (body) {
      if (measure) lastPoll[measure] = body.length;
      return JSON.parse(body);
    });
  }

  function renderFreshness() {
    var node = $('freshness');
    if (!state.lastOk) { node.dataset.state = 'loading'; node.textContent = 'loading…'; return; }
    var stamp = state.lastOk.toLocaleTimeString();
    if (state.stale) { node.dataset.state = 'stale'; node.textContent = 'stale: server unreachable, last update ' + stamp; }
    else { node.dataset.state = 'live'; node.textContent = 'live: updated ' + stamp; }
  }

  function renderHeader() {
    var review = state.review, accepted = review.accepted;
    text('project-name', review.project + ' — review');
    document.title = review.project + ' — Cadex review';
    text('accepted-line', accepted.available
      ? 'accepted now: revision ' + short(accepted.revision) + ' · digest ' + short(accepted.digest) +
        (accepted.updated_at ? ' · updated ' + accepted.updated_at : '') + ' · ' + review.runs.length + ' run(s)'
      : 'nothing accepted: ' + accepted.reason + ' · ' + review.runs.length + ' run(s)');
  }

  function tone(run) {
    if (run.status === 'ok') return 'ok';
    if (run.status === 'failed' || run.status === 'unreadable') return 'bad';
    return 'warn';
  }

  function currentView() {
    // The reader returns records oldest first, with run name breaking time ties.
    var runs = state.review.runs;
    var active = runs.filter(function (run) {
      return ['running', 'pending'].includes(run.status) &&
        ['starting', 'training'].includes((run.telemetry || {}).state);
    });
    var candidates = active.length ? active : runs;
    return candidates.length ? candidates[candidates.length - 1].run : 'accepted';
  }

  function renderSidebar() {
    var current = currentView();
    text('current-run', 'Current run: ' + current);
    // The phone's disclosure line (DASHBOARD.md §6): what is current and
    // how many runs there are, readable while the list is closed.
    text('runs-summary', 'Runs · current: ' + current + ' · ' + state.review.runs.length + ' recorded');
    var accepted = state.review.accepted;
    // Rebuilt only when what it shows changes: a poll over an unchanged
    // history adds no nodes here however many runs there are.
    var key = JSON.stringify([state.selected, current, accepted.available && accepted.revision, state.review.runs.map(function (run) {
      return [run.run, run.relation, run.status, run.recorded_at, (run.model || {}).accepted_revision];
    })]);
    if (key === sidebarKey) return;
    sidebarKey = key;
    var list = $('views');
    clearChildren(list);
    list.appendChild(el('li', { 'data-view': 'accepted', 'data-selected': String(state.selected === 'accepted'), onclick: function () { select('accepted'); } }, [
      el('div', { className: 'name', text: 'Accepted now' }),
      el('div', { className: 'muted small', text: accepted.available ? short(accepted.revision) : 'nothing accepted' })
    ]));
    state.review.runs.forEach(function (run) {
      list.appendChild(el('li', { 'data-view': 'run', 'data-run': run.run, 'data-relation': run.relation, 'data-status': run.status,
                                  'data-selected': String(state.selected === run.run), 'data-current': String(run.run === current),
                                  onclick: function () { select(run.run); } }, [
        el('div', { className: 'name', text: run.run }),
        el('div', { className: 'badges' }, [
          el('span', { className: 'badge', 'data-tone': run.relation, text: run.relation }),
          el('span', { className: 'badge', 'data-tone': tone(run), text: run.status })
        ]),
        el('div', { className: 'muted small', text: (run.recorded_at || 'no record time') + ' · ' + short((run.model || {}).accepted_revision) })
      ]));
    });
  }

  function selectedRun() {
    if (state.selected === 'accepted') return null;
    return state.review.runs.filter(function (run) { return run.run === state.selected; })[0] || null;
  }

  var originKey = null, originRequest = 0;
  function renderPolicyOrigin(force) {
    var run = selectedRun();
    var key = JSON.stringify([state.selected, run && run.policy, run && run.training, run && run.status]);
    if (!force && key === originKey) return;
    originKey = key;
    var request = ++originRequest, line = $('policy-origin');
    line.dataset.run = ''; line.dataset.tone = ''; line.dataset.sourceAgrees = '';
    $('check-policy-origin').hidden = !run;
    if (!run) { line.dataset.state = 'unselected'; line.textContent = 'select a run'; return; }
    line.dataset.state = 'pending'; line.textContent = 'checking retained policy bytes…';
    fetchJson(BASE + '/api/policy-origin/' + encodeURIComponent(run.run)).then(function (data) {
      if (request !== originRequest) return;
      var origin = data.origin;
      line.dataset.state = origin ? 'resolved' : 'unresolved';
      line.dataset.run = origin ? origin.run : '';
      line.dataset.sourceAgrees = String(data.source_agrees);
      line.dataset.tone = data.source_agrees === false ? 'bad' : '';
      line.textContent = 'Checked on selection/request: ' + (origin
        ? origin.run + ' · ' + origin.kind + (origin.iteration != null ? ' · iteration ' + origin.iteration : '')
        : data.reason);
      if (data.recorded_source_run) line.textContent += ' · declared source: ' + data.recorded_source_run;
      if (data.source_agrees === false) line.textContent += ' · SOURCE-NAME DISAGREEMENT: retained bytes identify ' + origin.run;
      line.textContent += ' · snapshot; Check again to re-read retained files';
    }).catch(function (error) {
      if (request !== originRequest) return;
      line.dataset.state = 'failed'; line.dataset.tone = 'bad';
      line.textContent = 'policy origin check failed: ' + error.message + ' · Check again to retry';
    });
  }

  // The project's engine budgets (ADR-517), read-only: stored with
  // `cadex budgets --set`, overridden per call by --engine-timeout/-memory.
  function budgetsText(budgets) {
    var stored = (budgets && budgets.stored) || {}, parts = [];
    if (stored.timeout_seconds) parts.push(stored.timeout_seconds + ' s');
    if (stored.memory_limit_mb) parts.push(stored.memory_limit_mb + ' MB');
    var unset = (!stored.timeout_seconds ? 1 : 0) + (!stored.memory_limit_mb ? 1 : 0);
    if (!parts.length) return 'engine defaults (none stored)';
    return parts.join(' · ') + (unset ? ' · engine default for the other' : '');
  }

  function renderIdentity() {
    var accepted = state.review.accepted, run = selectedRun();
    text('view-budgets', budgetsText(state.review.budgets));
    var kind = $('view-kind'), relation = $('view-relation'), status = $('view-status');
    if (!run) {
      kind.textContent = 'ACCEPTED NOW'; kind.dataset.tone = 'accepted';
      relation.textContent = ''; status.textContent = '';
      text('view-revision', accepted.available ? accepted.revision : 'none');
      text('view-digest', accepted.available ? accepted.digest : 'none');
      text('view-identity-source', accepted.available ? 'project manifest (script.json), read-only' : accepted.reason);
      text('view-recorded', accepted.available ? (accepted.updated_at || '—') : '—');
      text('view-note', accepted.available ? 'the project as it stands; selecting a run shows that run\'s recorded revision instead'
                                            : 'no accepted revision: run `cadex -p` or `cadex script --set` to accept one');
      $('view-policy-store').dataset.state = ''; text('view-policy-store', '—');
      return;
    }
    var model = run.model || {};
    kind.textContent = 'RUN ' + run.run; kind.dataset.tone = 'accepted';
    if (run.relation === 'historical') {
      relation.textContent = 'HISTORICAL — recorded at ' + short(model.accepted_revision) + ', accepted now is ' + short(accepted.revision);
    } else if (run.relation === 'current') {
      relation.textContent = 'CURRENT — this run\'s revision is the accepted revision now';
    } else {
      relation.textContent = 'RELATION UNKNOWN — ' + (model.accepted_revision ? 'nothing accepted now' : 'no revision recorded for this run');
    }
    relation.dataset.tone = run.relation;
    status.textContent = run.outcome || run.status; status.dataset.tone = tone(run);
    text('view-revision', model.accepted_revision || 'not recorded');
    text('view-digest', model.digest || 'not recorded');
    text('view-identity-source', model.identity_source || 'not recorded');
    text('view-recorded', (run.recorded_at || 'no record time') + (run.mode ? ' · mode ' + run.mode : '') +
                          (run.walk_seconds != null ? ' · ' + run.walk_seconds + ' s' : ''));
    var note = run.error ? 'error: ' + run.error : '';
    var telemetry = telemetryFor(run), store = run.policy_store || { state: 'none', reason: 'no policy recorded' };
    if (run.status === 'running') note += (note ? ' · ' : '') + 'if no walk is running, this run was interrupted: start a new `cadex walk --out runs/<new-name>`';
    if (run.status === 'failed' && telemetry.state === 'done') {
      // The trainer reached its terminal state and saved its policy; what
      // failed came after it (an observation, a rollout, a store write).
      note += (note ? ' · ' : '') + 'training itself finished (iteration ' + fmt(telemetry.iteration) + ' of ' + fmt(telemetry.total) +
        (store.name ? ', policy ' + store.name + ' saved by the trainer' : '') + '): this run failed after that, in its observation or recording, not in the trainer';
    }
    if (run.status === 'unrecorded') note += (note ? ' · ' : '') + 'recorded before run records existed: identity from review.json only';
    text('view-note', note || '—');
    var storeLine = $('view-policy-store');
    storeLine.dataset.state = store.state;
    storeLine.textContent = store.state + ' — ' + store.reason +
      (store.retained ? ' · trainer copy retained at ' + store.retained : '') +
      (store.next_action ? ' · next: ' + store.next_action : '');
  }

  function renderParams() {
    var run = selectedRun(), values, specs, source;
    if (!run) {
      var accepted = state.review.accepted;
      values = accepted.available ? accepted.param_values : {}; specs = accepted.available ? accepted.param_specs : null;
      source = accepted.available ? 'project manifest at the accepted revision' : accepted.reason;
    } else {
      values = (run.params || {}).values || {}; specs = (run.params || {}).specs; source = (run.params || {}).specs_source;
    }
    var byName = {};
    (Array.isArray(specs) ? specs : []).forEach(function (spec) { if (spec && spec.name) byName[spec.name] = spec; });
    var names = Object.keys(values);
    Object.keys(byName).forEach(function (name) { if (names.indexOf(name) < 0) names.push(name); });
    // Rebuilt only when what it shows changes, and never under a write in
    // flight, so a poll does not snatch a slider from the hand moving it.
    var key = JSON.stringify([state.selected, values, specs]);
    if (writing || key === paramsKey) return;
    paramsKey = key;
    var body = $('params').querySelector('tbody');
    clearChildren(body);
    names.sort().forEach(function (name) {
      var spec = byName[name] || {};
      body.appendChild(el('tr', { 'data-param': name }, [
        el('td', { text: name }), el('td', {}, [paramValue(name, values[name], spec, !run)]), el('td', { text: fmt(spec.default) }),
        el('td', { text: fmt(spec.min) }), el('td', { text: fmt(spec.max) }), el('td', { text: fmt(spec.unit) }),
        el('td', { text: fmt(spec.label) })
      ]));
    });
    text('params-note', Array.isArray(specs)
      ? 'specs from ' + source + (names.length ? '' : ' (no parameters declared)')
      : 'specs unavailable' + (source ? ': ' + source : '') + (names.length ? ' — values only' : ''));
  }

  // A declared number with a range is a slider on the accepted view: the
  // project as it stands now is the only thing a write can change. A run's
  // parameters are a record and stay text.
  // A parameter never set reads at its declared default, and says so.
  function paramValue(name, value, spec, writable) {
    var current = typeof value === 'number' ? value : spec.default;
    var bounded = typeof current === 'number' && isFinite(spec.min) && isFinite(spec.max) && spec.max > spec.min;
    if (!writable || !bounded || !WRITE_TOKEN) return el('span', { text: fmt(value) });
    var shown = el('output', { text: fmt(current) + (value == null ? ' (default)' : '') });
    value = current;
    var slider = el('input', { type: 'range', min: String(spec.min), max: String(spec.max),
                               step: String(spec.step > 0 ? spec.step : 'any'), value: String(value),
                               'data-param': name, title: 'set ' + name + ' (runs cadex params --set)' });
    slider.setAttribute('aria-label', name);
    slider.addEventListener('input', function () { shown.textContent = fmt(Number(slider.value)); });
    // One write per release, not one per pixel of the drag.
    slider.addEventListener('change', function () { writeParams(name, Number(slider.value)); });
    return el('span', { className: 'param-slider' }, [slider, shown]);
  }

  function writeParams(name, value) {
    var status = $('params-write'), started = performance.now(), values = {};
    values[name] = value;
    writing = { name: name, value: value };
    paramsKey = null;
    $('params').querySelectorAll('input[type=range]').forEach(function (input) { input.disabled = true; });
    status.dataset.state = 'pending';
    status.textContent = 'cadex params --set ' + name + '=' + fmt(value) + ' …';
    var reply = null;
    return fetch(BASE + '/api/params', {
      method: 'POST', cache: 'no-store',
      headers: { 'Content-Type': 'application/json', 'X-Cadex-Token': WRITE_TOKEN },
      body: JSON.stringify({ values: values })
    }).then(function (response) {
      return response.json().then(function (body) { reply = body; });
    }).then(function () {
      writing = null;
      if (!reply.ok) throw new Error(reply.error || 'exit ' + reply.exit);
      // A poll already in flight may predate the write; the next one cannot.
      return (pendingPoll || Promise.resolve()).catch(function () {}).then(poll);
    }).then(function () {
      lastWrite = { ok: true, name: name, value: value, revision: reply.accepted_revision, digest: reply.digest,
                    server_s: reply.seconds, total_ms: performance.now() - started };
      status.dataset.state = 'done';
      status.textContent = name + ' = ' + fmt(value) + ': accepted at ' + short(reply.accepted_revision) +
        ' in ' + reply.seconds.toFixed(2) + ' s (model shown after ' + (lastWrite.total_ms / 1000).toFixed(2) + ' s)';
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

  // What the turn cost, as Claude Code reported it (ADR-523); nothing when unpriced.
  function turnCost(usage) {
    if (!usage) return '';
    var tokens = (usage.input_tokens || 0) + (usage.cached_tokens || 0) + (usage.output_tokens || 0);
    return ' · ' + tokens.toLocaleString('en-US') + ' tokens' +
      (typeof usage.cost_usd === 'number' ? ', $' + usage.cost_usd.toFixed(2) : '');
  }

  function renderTurn() {
    var status = $('turn-status'), transcript = $('turn-transcript'), running = turn.state === 'running';
    status.dataset.state = turn.state;
    $('turn-start').disabled = running;
    $('turn-prompt').disabled = running;
    $('turn-attach').disabled = running;
    if (turn.state === 'idle') status.textContent = '';
    else if (running) status.textContent = 'running: ' + turn.prompt +
      (turn.images && turn.images.length ? ' (with ' + turn.images.map(function (image) { return image.name; }).join(', ') + ')' : '');
    else if (turn.reply && turn.reply.ok) status.textContent = 'accepted at ' + short(turn.reply.accepted_revision) +
      ' in ' + Number(turn.reply.seconds || 0).toFixed(1) + ' s' + turnCost(turn.reply.usage);
    else status.textContent = ((turn.reply && turn.reply.error) || 'the turn failed') + turnCost(turn.reply && turn.reply.usage);
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
      var wasRunning = turn.state === 'running' && turn.id === reply.id;
      if (reply.id !== turn.id) {
        // Another turn: its transcript starts over, so read it from the top.
        turn = { id: reply.id, state: reply.state, text: '', next: 0, reply: null, prompt: reply.prompt,
                 images: reply.images || [] };
        turnRequest = null;
        return pollTurn();
      }
      turn.text += reply.text; turn.next = reply.next; turn.state = reply.state; turn.reply = reply.reply;
      renderTurn();
      // The turn ended: the accepted revision may have moved under the model.
      if (wasRunning && reply.state !== 'running') return (pendingPoll || Promise.resolve()).catch(function () {}).then(poll);
    }).catch(function () {}).finally(function () { turnRequest = null; });
    return turnRequest;
  }

  // Images attached to the next prompt (ADR-507), as {name, data: base64}.
  var turnImages = [];

  function renderTurnImages() {
    var line = $('turn-images');
    line.hidden = !turnImages.length;
    line.textContent = turnImages.length ? 'attached: ' + turnImages.map(function (image) { return image.name; }).join(', ') : '';
    $('turn-attach').textContent = turnImages.length ? 'Remove image' + (turnImages.length > 1 ? 's' : '') : 'Attach image';
  }

  function attachImages(files) {
    return Promise.all(Array.prototype.map.call(files, function (file) {
      return new Promise(function (resolve, reject) {
        var reader = new FileReader();
        reader.onload = function () { resolve({ name: file.name, data: String(reader.result).split(',')[1] || '' }); };
        reader.onerror = function () { reject(reader.error); };
        reader.readAsDataURL(file);
      });
    })).then(function (images) {
      turnImages = images;
      renderTurnImages();
      return images.length;
    });
  }

  function startTurn(prompt, resume) {
    var status = $('turn-status');
    status.dataset.state = 'pending';
    status.textContent = 'starting cadex -p …';
    return fetch(BASE + '/api/turn', {
      method: 'POST', cache: 'no-store',
      headers: { 'Content-Type': 'application/json', 'X-Cadex-Token': WRITE_TOKEN },
      body: JSON.stringify({ prompt: prompt, resume: !!resume, images: turnImages })
    }).then(function (response) {
      return response.json();
    }).then(function (reply) {
      if (!reply.ok) throw new Error(reply.error || 'refused');
      turnImages = [];
      $('turn-image').value = '';
      renderTurnImages();
      turn = { id: reply.turn.id, state: reply.turn.state, text: reply.turn.text, next: reply.turn.next,
               reply: reply.turn.reply, prompt: reply.turn.prompt, images: reply.turn.images || [] };
      renderTurn();
      return reply.turn;
    }).catch(function (error) {
      status.dataset.state = 'error';
      status.textContent = 'not started: ' + error.message;
      return null;
    });
  }

  // Comments (ADR-505): on the whole design, or on the part last clicked in
  // the model. Each is `cadex comment` run by the server; the next design
  // turn receives every one not yet delivered.
  var commentPart = '', commentsKey = null, lastComment = null;

  function renderCommentTarget() {
    var target = $('comment-target');
    target.dataset.part = commentPart;
    target.textContent = commentPart ? 'on part ' + commentPart : 'on the whole design · click a part in the model to pick it';
    $('comment-whole').hidden = !commentPart;
  }

  function pickPart(name) {
    commentPart = name || '';
    if (state.viewer && state.viewer.highlight) state.viewer.highlight(commentPart || null);
    renderCommentTarget();
  }

  function renderComments() {
    var comments = (state.review && state.review.comments) || [];
    var key = JSON.stringify(comments);
    if (key === commentsKey) return;
    commentsKey = key;
    var list = $('comment-list');
    clearChildren(list);
    comments.slice().reverse().forEach(function (comment) {
      list.appendChild(el('li', { 'data-comment': comment.id, 'data-part': comment.part, 'data-delivered': String(!!comment.delivered) }, [
        el('span', { text: (comment.part ? comment.part + ': ' : '') + comment.text }),
        el('span', { className: 'muted small', text: ' · ' + (comment.delivered ? 'received by a turn' : 'waiting for the next turn') })
      ]));
    });
  }

  // An answer to an agent note (ADR-512) is the same write with `reply_to`,
  // reported in the note panel rather than the comment box.
  function sendComment(text, part, replyTo) {
    var prefix = replyTo ? 'note' : 'comment';
    var status = $(prefix + '-status');
    status.dataset.state = 'pending';
    status.textContent = 'running cadex comment …';
    $(prefix + '-send').disabled = true;
    return fetch(BASE + '/api/comment', {
      method: 'POST', cache: 'no-store',
      headers: { 'Content-Type': 'application/json', 'X-Cadex-Token': WRITE_TOKEN },
      body: JSON.stringify(replyTo ? { text: text, reply_to: replyTo } : { text: text, part: part || '' })
    }).then(function (response) {
      return response.json();
    }).then(function (reply) {
      if (!reply.ok) throw new Error(reply.error || 'refused');
      lastComment = reply.comment;
      status.dataset.state = 'done';
      status.textContent = (replyTo ? 'answered' : 'left ' + (reply.comment.part ? 'on part ' + reply.comment.part : 'on the whole design')) + '; the next turn receives it';
      $(prefix + '-text').value = '';
      return (pendingPoll || Promise.resolve()).catch(function () {}).then(poll).then(function () { return reply.comment; });
    }).catch(function (error) {
      status.dataset.state = 'error';
      status.textContent = 'not left: ' + error.message;
      return null;
    }).finally(function () { $(prefix + '-send').disabled = false; });
  }

  // Notes from the agent (ADR-512): what its leave_note tool flagged for
  // review or asked, newest first. The agent never waited for these; an
  // answer is a comment the next turn receives, quoting the note.
  var notesKey = null, answerTo = '';

  function answerNote(id) {
    answerTo = id || '';
    var note = ((state.review && state.review.notes) || []).filter(function (n) { return n.id === answerTo; })[0];
    $('note-answer').hidden = !note;
    $('note-target').dataset.note = note ? note.id : '';
    $('note-target').textContent = note ? 'answering: ' + note.text : 'answering —';
  }

  function renderNotes() {
    var notes = (state.review && state.review.notes) || [];
    var key = JSON.stringify(notes);
    if (key === notesKey) return;
    notesKey = key;
    var list = $('note-list');
    clearChildren(list);
    $('note-empty').hidden = notes.length > 0;
    notes.slice().reverse().forEach(function (note) {
      var about = [note.type === 'question' ? 'question' : 'flagged for review',
                   note.artifact ? note.artifact : 'revision ' + short(note.revision), note.at];
      var children = [
        el('span', { className: 'note-type', text: note.type === 'question' ? '? ' : '⚑ ' }),
        el('span', { text: note.text }),
        el('div', { className: 'muted small', text: about.join(' · ') })
      ];
      if (note.url) children.push(el('a', { className: 'note-artifact small', href: note.url, target: '_blank', text: 'open ' + note.artifact }));
      note.answers.forEach(function (answer) {
        children.push(el('div', { className: 'note-reply small', 'data-answer': answer.id, text: '↳ ' + answer.text }));
      });
      var button = el('button', { type: 'button', className: 'note-reply-button', text: note.answers.length ? 'Answer again' : 'Answer' });
      button.addEventListener('click', function () { answerNote(note.id); $('note-text').focus(); });
      children.push(button);
      list.appendChild(el('li', { 'data-note': note.id, 'data-type': note.type, 'data-answered': String(note.answers.length > 0) }, children));
    });
    if (answerTo) answerNote(answerTo);
  }

  // Revisions (ADR-506): the owner's verdict on the accepted revision, and
  // any stored one put back. Each is `cadex revision` run by the server; a
  // reject or restore rebuilds, and the next poll draws what it accepted.
  var revisionsKey = null, lastRevision = null, revisionWriting = false;

  function verdicts() {
    var latest = {};
    ((state.review && state.review.comments) || []).forEach(function (comment) {
      if (comment.verdict) latest[comment.revision] = comment.verdict;
    });
    return latest;
  }

  function renderRevisions() {
    var trail = (state.review && state.review.revisions) || [];
    var current = state.review && state.review.accepted && state.review.accepted.revision;
    var marks = verdicts();
    var key = JSON.stringify([trail, current, marks, revisionWriting]);
    if (key === revisionsKey) return;
    revisionsKey = key;
    $('revision-current').textContent = current
      ? 'accepted ' + short(current) + (marks[current] ? ' · ' + marks[current] + ' by the owner' : ' · not yet reviewed')
      : 'no accepted revision yet';
    $('revision-accept').disabled = revisionWriting || !current;
    $('revision-reject').disabled = revisionWriting || !current || trail.length < 2;
    var list = $('revision-list');
    clearChildren(list);
    trail.forEach(function (entry) {
      var here = entry.revision === current;
      var item = el('li', { 'data-revision': entry.revision, 'data-ordinal': String(entry.ordinal),
                            'data-current': String(here), 'data-verdict': marks[entry.revision] || '' }, [
        el('span', { text: '#' + entry.ordinal + ' ' + short(entry.revision) }),
        el('span', { className: 'muted small', text: ' · ' + (here ? 'accepted now' : (entry.saved_at || '')) +
                     (marks[entry.revision] ? ' · ' + marks[entry.revision] : '') })
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
    var status = $('revision-status'), note = $('revision-note').value.trim();
    revisionWriting = true; revisionsKey = null; renderRevisions();
    status.dataset.state = 'pending';
    status.textContent = 'cadex revision ' + action + (revision ? ' ' + revision : '') + ' …';
    return fetch(BASE + '/api/revision', {
      method: 'POST', cache: 'no-store',
      headers: { 'Content-Type': 'application/json', 'X-Cadex-Token': WRITE_TOKEN },
      body: JSON.stringify({ action: action, revision: revision || '', note: note })
    }).then(function (response) {
      return response.json();
    }).then(function (reply) {
      if (!reply.ok) throw new Error(reply.error || 'exit ' + reply.exit);
      lastRevision = reply;
      var change = reply.revisions || {};
      status.dataset.state = 'done';
      status.textContent = action === 'accept' ? 'accepted ' + short(change.target) + '; the next turn is told'
        : (action === 'reject' ? 'rejected ' + short(change.from) + '; ' : '') + 'put back #' + change.ordinal + ' as ' +
          short(reply.accepted_revision) + (change.exact ? '' : change.same_geometry ? ' (same geometry)' : ' (not the same revision)');
      $('revision-note').value = '';
      revisionWriting = false;
      return (pendingPoll || Promise.resolve()).catch(function () {}).then(poll).then(function () { return reply; });
    }).catch(function (error) {
      revisionWriting = false; revisionsKey = null;
      status.dataset.state = 'error';
      status.textContent = action + ' refused: ' + error.message;
      if (state.review) renderRevisions();
      return null;
    });
  }

  // Export (ADR-509): `cadex export` run by the server for the accepted
  // revision, into the project's ignored review/export/<revision>/; the
  // files it wrote are listed for download from the project block.
  var exportsKey = null, lastExport = null, exportWriting = false;

  function renderExports() {
    var shown = (state.review && state.review.exports) || { available: false, reason: 'no export block' };
    var current = state.review && state.review.accepted && state.review.accepted.revision;
    var key = JSON.stringify([shown, current, exportWriting]);
    if (key === exportsKey) return;
    exportsKey = key;
    $('export-run').disabled = exportWriting || !current;
    var list = $('export-list');
    clearChildren(list);
    if (!shown.available) {
      list.appendChild(el('li', { className: 'muted small', text: shown.reason || 'nothing exported' }));
      return;
    }
    shown.files.forEach(function (file) {
      list.appendChild(el('li', { 'data-name': file.name }, [
        el('a', { href: BASE + '/' + file.url + '?download=1', download: file.name, text: file.name }),
        el('span', { className: 'muted small', text: ' · ' + bytes(file.bytes) })
      ]));
    });
  }

  // Drawings (ADR-516): blueprint sheets the agent stored with the project,
  // newest first, each linked; the newest is shown. Nothing here writes.
  var drawingsKey = null;

  function renderDrawings() {
    var shown = (state.review && state.review.drawings) || { available: false, reason: 'no drawings block', sheets: [] };
    var key = JSON.stringify(shown);
    if (key === drawingsKey) return;
    drawingsKey = key;
    var list = $('drawing-list'), link = $('drawing-latest-link');
    clearChildren(list);
    if (!shown.available) {
      link.hidden = true;
      list.appendChild(el('li', { className: 'muted small', text: shown.reason || 'no drawings' }));
      return;
    }
    var newest = shown.sheets[0];
    link.hidden = false;
    link.href = BASE + '/' + newest.url;
    $('drawing-latest').src = BASE + '/' + newest.url;
    shown.sheets.forEach(function (sheet) {
      list.appendChild(el('li', { 'data-file': sheet.file, 'data-relation': sheet.relation }, [
        el('a', { href: BASE + '/' + sheet.url, target: '_blank', rel: 'noopener', text: sheet.name + ' v' + sheet.version }),
        el('span', { className: 'muted small', text: ' · ' + short(sheet.revision) + (sheet.relation === 'current' ? '' : ' (earlier design)') + ' · ' }),
        el('a', { href: BASE + '/' + sheet.url + '?download=1', download: sheet.file, text: 'download' })
      ]));
    });
  }

  function writeExport(formats) {
    var status = $('export-status');
    formats = formats || ['step', 'stl'];
    exportWriting = true; exportsKey = null; renderExports();
    status.dataset.state = 'pending';
    status.textContent = 'cadex export --format ' + formats.join(',') + ' …';
    return fetch(BASE + '/api/export', {
      method: 'POST', cache: 'no-store',
      headers: { 'Content-Type': 'application/json', 'X-Cadex-Token': WRITE_TOKEN },
      body: JSON.stringify({ formats: formats })
    }).then(function (response) {
      return response.json();
    }).then(function (reply) {
      if (!reply.ok) throw new Error(reply.error || 'exit ' + reply.exit);
      lastExport = reply;
      status.dataset.state = 'done';
      status.textContent = 'exported ' + short(reply.revision) + ' in ' + reply.seconds.toFixed(1) + ' s';
      exportWriting = false;
      return (pendingPoll || Promise.resolve()).catch(function () {}).then(poll).then(function () { return reply; });
    }).catch(function (error) {
      exportWriting = false; exportsKey = null;
      status.dataset.state = 'error';
      status.textContent = 'export refused: ' + error.message;
      if (state.review) renderExports();
      return null;
    });
  }

  // Explode (DASHBOARD.md §24): the engine's exploded-view frames, frame 0 the
  // assembled model. A slider value t in [0, stages] sits between frame floor(t)
  // and the next: positions are lerped, rotations slerped, as the stages move.
  var explodeT = 0;

  function slerp(a, b, f) {
    var d = a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3], s = d < 0 ? -1 : 1;
    d = Math.abs(d);
    if (d > 0.9995) {
      var q = a.map(function (v, i) { return v + f * (s * b[i] - v); }), n = Math.hypot.apply(null, q);
      return q.map(function (v) { return v / n; });
    }
    var th = Math.acos(d), w0 = Math.sin((1 - f) * th) / Math.sin(th), w1 = s * Math.sin(f * th) / Math.sin(th);
    return a.map(function (v, i) { return w0 * v + w1 * b[i]; });
  }

  function explodedView() {
    var views = (state.model && state.model.available && state.model.exploded) || [];
    return views[Number($('explode-view').value) || 0] || null;
  }

  // Two pose sets blended a fraction f of the way: positions lerped, rotations slerped.
  function blendPoses(a, b, f) {
    var poses = {};
    Object.keys(a).forEach(function (name) {
      var p = a[name], q = b[name] || p;
      poses[name] = { position_mm: p.position_mm.map(function (v, k) { return v + f * (q.position_mm[k] - v); }),
                      rotation_xyzw: slerp(p.rotation_xyzw, q.rotation_xyzw, f) };
    });
    return poses;
  }

  function explodePoses(view, t) {
    var i = Math.min(Math.floor(t), view.stages - 1), a = view.frames[Math.max(0, i)], b = view.frames[Math.max(0, i) + 1] || a;
    if (t >= view.stages) return view.frames[view.stages];
    return blendPoses(a, b, t - i);
  }

  function setExplode(t) {
    var view = explodedView(), slider = $('explode-amount');
    if (!view || !state.viewer.available) return null;
    explodeT = Math.max(0, Math.min(view.stages, Number(t) || 0));
    slider.value = String(explodeT);
    state.viewer.setPoses(explodePoses(view, explodeT));
    state.viewer.showLines(explodeT > 0);
    $('explode-note').textContent = explodeT > 0 ? 'stage ' + explodeT.toFixed(2) + ' of ' + view.stages + ' · ' + view.output : 'assembled';
    return explodeT;
  }

  function renderExplode(manifest, index) {
    var views = (manifest && manifest.available && manifest.exploded) || [], slider = $('explode-amount'), pick = $('explode-view');
    explodeT = 0;
    clearChildren(pick);
    views.forEach(function (view, index) { pick.appendChild(el('option', { value: String(index), text: view.output })); });
    index = Math.max(0, Math.min(views.length - 1, Number(index) || 0));
    pick.value = String(index);
    pick.hidden = views.length < 2;
    slider.disabled = !views.length || !state.viewer.available;
    slider.value = '0';
    var view = views[index];
    slider.max = view ? String(view.stages) : '1';
    if (view && state.viewer.available) state.viewer.setLines(view.lines);
    $('explode-note').textContent = view ? 'assembled · ' + views.length + ' exploded view(s) from the engine' :
      'no exploded view: the script declares no assembly.exploded_view';
  }

  // Playback (DASHBOARD.md §25): a run's rollout trace, served as its timed
  // frames. The slider is simulation seconds, not frame numbers; between two
  // frames the poses are blended, and at a frame's own time they are the
  // trace's. A command holds over the interval it was applied (zero order
  // hold): in (t[i-1], t[i]] it is frame i's, and the reset frame has none.
  var playback = null, playT = 0, playing = null, playbackKey = null;

  function playFrame(t) {
    var times = playback.times_s, i = 0;
    while (i + 1 < times.length && times[i + 1] <= t) i++;
    return i;
  }

  function setPlay(t) {
    if (!playback || !state.viewer.available) return null;
    var times = playback.times_s, last = times.length - 1;
    playT = Math.max(times[0], Math.min(times[last], Number(t) || 0));
    var i = playFrame(playT), j = i, poses = playback.frames[i];
    if (i < last && playT > times[i]) {
      j = i + 1;
      poses = blendPoses(playback.frames[i], playback.frames[j], (playT - times[i]) / (times[j] - times[i]));
    }
    $('play-time').value = String(playT);
    state.viewer.setPoses(poses);
    state.viewer.setClock(playT);
    var command = playback.commands[j], channels = playback.channels || [];
    $('play-note').textContent = 't = ' + playT.toFixed(3) + ' s of ' + num(times[last]) + ' · frame ' + (i + 1) + ' of ' + times.length +
      ' · ' + (command ? channels.map(function (c, k) { return c.actuator + ' ' + num(command[k]) + ' ' + c.unit + ' (' + num(c.low) + '..' + num(c.high) + ')'; }).join(', ') || 'command ' + command.join(', ')
                       : 'no command yet (reset pose)');
    return { t: playT, frame: i, command: command };
  }

  function stopPlay() {
    if (playing) window.cancelAnimationFrame(playing);
    playing = null;
    $('play-toggle').textContent = 'Play';
  }

  function togglePlay() {
    if (playing) { stopPlay(); return false; }
    if (!playback) return false;
    var times = playback.times_s, start = playT >= times[times.length - 1] ? times[0] : playT, origin = null;
    $('play-toggle').textContent = 'Pause';
    function step(now) {
      if (origin === null) origin = now - (start - times[0]) * 1000;
      setPlay(times[0] + (now - origin) / 1000);
      if (playT >= times[times.length - 1]) { stopPlay(); return; }
      playing = window.requestAnimationFrame(step);
    }
    playing = window.requestAnimationFrame(step);
    return true;
  }

  function renderPlayback(manifest) {
    var info = (manifest && manifest.available && manifest.playback) || null, slider = $('play-time'), button = $('play-toggle');
    var key = info && info.available ? info.url : null;
    stopPlay();
    if (state.viewer.available) state.viewer.setClock(null);
    if (key !== playbackKey) playback = null;
    playbackKey = key;
    slider.disabled = button.disabled = true;
    if (!key) {
      $('play-note').textContent = info ? 'no rollout to play: ' + info.reason : 'no rollout to play: select a run that rolled out';
      return Promise.resolve(null);
    }
    $('play-note').textContent = 'loading ' + info.frames + ' frame(s)…';
    return fetchJson(BASE + key).then(function (served) {
      if (key !== playbackKey) return null;
      if (!served.available) { $('play-note').textContent = 'no rollout to play: ' + served.reason; return null; }
      playback = served;
      slider.min = String(served.times_s[0]); slider.max = String(served.times_s[served.times_s.length - 1]);
      slider.disabled = button.disabled = !state.viewer.available;
      return setPlay(served.times_s[0]);
    }).catch(function (error) { $('play-note').textContent = 'rollout failed to load: ' + error.message; return null; });
  }

  // Section (DASHBOARD.md §24): Cut is `cadex section` run by the server; the
  // page shows the SVG it drew and clips the viewer's solids at the same plane
  // and offset. The listing is the accepted revision's cuts, newest first.
  var sectionsKey = null, lastSection = null, sectionWriting = false, activeCut = null;

  function showCut(cut) {
    activeCut = cut || null;
    var figure = $('section-figure');
    if (state.viewer.available) state.viewer.setSection(cut ? cut.plane : null, cut ? cut.offset_mm : NaN);
    $('section-clear').disabled = !cut;
    Array.prototype.forEach.call(document.querySelectorAll('#section-list li[data-cut]'), function (li) {
      li.dataset.active = String(!!cut && li.dataset.cut === cut.name);
    });
    figure.hidden = !cut;
    if (!cut) { $('section-svg').removeAttribute('src'); return; }
    $('section-svg').src = BASE + '/' + cut.svg;
    $('section-caption').textContent = cut.plane + ' ' + cut.offset_mm + ' mm (' + cut.offset_source + ') · ' + cut.status + ' · ' +
      cut.objects_cut + '/' + cut.objects + ' objects cut' + (cut.missed.length ? ' · missed: ' + cut.missed.join(', ') : '') +
      ' · viewer clipped at the same plane · ' + cut.approximation;
  }

  function renderSections() {
    var shown = (state.review && state.review.sections) || { available: false, reason: 'no section block', cuts: [] };
    var current = state.review && state.review.accepted && state.review.accepted.revision;
    var key = JSON.stringify([shown, current, sectionWriting, state.selected]);
    if (key === sectionsKey) return;
    sectionsKey = key;
    $('section-cut').disabled = sectionWriting || !current || state.selected !== 'accepted';
    var list = $('section-list');
    clearChildren(list);
    if (activeCut && !shown.cuts.some(function (cut) { return cut.name === activeCut.name; })) showCut(null);
    if (!shown.available) { list.appendChild(el('li', { className: 'muted small', text: shown.reason || 'no cut' })); return; }
    shown.cuts.forEach(function (cut) {
      list.appendChild(el('li', { 'data-cut': cut.name, 'data-active': String(!!activeCut && activeCut.name === cut.name) }, [
        el('a', { href: '#', text: cut.plane + ' ' + cut.offset_mm + ' mm', onclick: function (event) { event.preventDefault(); showCut(cut); } }),
        el('span', { className: 'muted small', text: ' · ' + cut.offset_source + ' · ' + cut.objects_cut + '/' + cut.objects + ' cut' })
      ]));
    });
  }

  function writeSection(plane, offset) {
    var status = $('section-status'), body = { plane: plane };
    if (offset !== null && offset !== undefined && offset !== '') body.offset_mm = Number(offset);
    sectionWriting = true; sectionsKey = null; renderSections();
    status.dataset.state = 'pending';
    status.textContent = 'cadex section --plane ' + plane + (body.offset_mm === undefined ? ' (derived offset)' : ' --offset-mm=' + body.offset_mm) + ' …';
    return fetch(BASE + '/api/section', {
      method: 'POST', cache: 'no-store',
      headers: { 'Content-Type': 'application/json', 'X-Cadex-Token': WRITE_TOKEN },
      body: JSON.stringify(body)
    }).then(function (response) {
      return response.json();
    }).then(function (reply) {
      if (!reply.ok) throw new Error(reply.error || 'exit ' + reply.exit);
      lastSection = reply;
      sectionWriting = false;
      status.dataset.state = 'done';
      status.textContent = 'cut ' + reply.cut.plane + ' ' + reply.cut.offset_mm + ' mm in ' + reply.seconds.toFixed(1) + ' s';
      if (state.review) state.review.sections = reply.sections;
      sectionsKey = null; renderSections(); showCut(reply.cut);
      return reply;
    }).catch(function (error) {
      sectionWriting = false; sectionsKey = null;
      status.dataset.state = 'error';
      status.textContent = 'section refused: ' + error.message;
      if (state.review) renderSections();
      return null;
    });
  }

  function telemetryFor(run) {
    // The selected run's detail (histories, verified checkpoints) when it has
    // arrived for this run; otherwise the list's summary, which carries the
    // same state and latest metrics with sample counts in place of samples.
    if (!run) return {state: 'unselected'};
    if (state.detail && state.detail.run === run.run && state.detail.telemetry) return state.detail.telemetry;
    return run.telemetry || {state: 'missing'};
  }

  function renderTelemetry(run) {
    var panel = $('telemetry');
    var data = telemetryFor(run);
    var key = JSON.stringify([run && run.run, data, state.detail && state.detail.run], function (k, v) { return k === 'age_s' ? undefined : v; });
    if (key === telemetryKey) return;
    telemetryKey = key;
    clearChildren(panel);
    panel.dataset.state = data.state;
    panel.dataset.detail = !run ? '' : data.summary ? 'pending' : 'loaded';
    panel.appendChild(el('p', {text: 'Training telemetry: ' + data.state + (data.reason ? ' — ' + data.reason : '')}));
    if (!run) return;
    if (['missing', 'invalid', 'stale', 'failed', 'unknown'].includes(data.state)) {
      panel.appendChild(el('p', {text: 'Inspect the CLI training output; if the run stopped, start a new cadex walk --out runs/<new-name>. Stale data does not prove interruption.'}));
    }
    // The stat row: each metric's text stays "key: value" (the suites read
    // it whole); the two spans only let the stylesheet set the value large.
    var stats = el('div', {className: 'stats'});
    ['iteration', 'total', 'reward_per_step', 'loss', 'episode_steps'].forEach(function (key) {
      stats.appendChild(el('div', {'data-metric': key}, [el('span', {className: 'k', text: key + ': '}), el('span', {className: 'v', text: fmt(data[key])})]));
    });
    panel.appendChild(stats);
    var histories = el('div', {className: 'histories'});
    [['curve', 'Reward per step'], ['loss_curve', 'Loss'], ['episode_steps_curve', 'Episode length (steps)']].forEach(function (item) {
      var points = data[item[0]] || [], count = data.summary ? ((data.samples || {})[item[0]] || 0) : points.length;
      var block = el('div', {'data-history': item[0], 'data-points': String(count)});
      block.appendChild(el('p', {text: item[1] + (count ? ' · ' + count + ' retained samples' + (data.summary ? ' · loading history…' : '') : ' — history missing')}));
      if (points.length) {
        var xs = points.map(function (p) {return p[0];}), ys = points.map(function (p) {return p[1];});
        var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs), y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
        var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('viewBox', '0 0 400 100');
        svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', item[1] + ' by iteration');
        var line = document.createElementNS(svg.namespaceURI, 'polyline');
        line.setAttribute('points', points.map(function (p) {return (5 + 390 * (p[0]-x0)/(x1-x0 || 1)) + ',' + (95 - 90 * (p[1]-y0)/(y1-y0 || 1));}).join(' '));
        svg.appendChild(line); block.appendChild(svg);
        block.appendChild(el('small', {text: 'iterations ' + x0 + '–' + x1 + ' · range ' + fmt(y0) + '–' + fmt(y1)}));
      }
      histories.appendChild(block);
    });
    panel.appendChild(histories);
    if (data.summary) {
      // Same shape as the detail below, so a reader (or a test) waiting on
      // the provenance line sees "pending", never a missing element.
      panel.appendChild(el('p', {id: 'checkpoint-source', 'data-state': 'pending', 'data-run': '',
        text: 'Checkpoints: ' + fmt(data.checkpoints_reported) + ' reported · loading verification…'}));
      panel.appendChild(el('ul', {id: 'checkpoints'}, [el('li', {'data-status': 'pending', 'data-source': '', text: 'checkpoints: verification pending'})]));
      return;
    }
    var source = data.checkpoint_source || {state: 'none', run: null, reason: ''};
    var sourceLine = el('p', {id: 'checkpoint-source', 'data-state': source.state, 'data-run': source.run || ''});
    if (source.state === 'none') sourceLine.textContent = 'Checkpoints: this run\'s own train/ directory';
    else if (source.state === 'resolved') sourceLine.textContent = 'Checkpoints: this run\'s train/, then recorded training run ' + source.run;
    else sourceLine.textContent = 'Checkpoints: recorded training run ' + source.run + ' ' + source.state + ' — ' + source.reason;
    panel.appendChild(sourceLine);
    var checkpoints = el('ul', {id: 'checkpoints'});
    (data.checkpoints || []).forEach(function (item) {
      var where = item.source == null ? (item.status === 'refused' ? '' : ' · not found in this project')
        : (item.source === 'run' ? '' : ' · from training run ' + item.source);
      checkpoints.appendChild(el('li', {'data-status': item.status, 'data-source': item.source == null ? '' : item.source,
        text: item.path + ' · iteration ' + fmt(item.iteration) + ' · ' + item.status + where + ' · sha256 ' + item.sha256}));
    });
    if (!(data.checkpoints || []).length) checkpoints.appendChild(el('li', {text: 'checkpoints: none reported'}));
    panel.appendChild(checkpoints);
  }

  function renderTraining() {
    var body = $('training').querySelector('tbody');
    clearChildren(body);
    var run = selectedRun();
    renderTelemetry(run);
    function row(key, value) { body.appendChild(el('tr', { 'data-key': key }, [el('th', { text: key }), el('td', { text: value })])); }
    if (!run) { row('training', 'select a run to see its training and rollout'); return; }
    var training = run.training || {}, requested = training.requested || {}, receipt = training.receipt || {};
    var task = run.task || {}, policy = run.policy || {}, rollout = run.rollout || {};
    if (!Object.keys(requested).length && !Object.keys(receipt).length) row('training', 'not recorded');
    Object.keys(requested).sort().forEach(function (key) { row('requested ' + key, fmt(requested[key])); });
    Object.keys(receipt).sort().forEach(function (key) { row('receipt ' + key, fmt(receipt[key])); });
    row('task sha256', task.sha256 || 'not recorded');
    row('policy', (policy.name || 'not recorded') + (policy.sha256 ? ' · ' + policy.sha256 : ''));
    row('rollout seed', fmt(rollout.seed));
    row('rollout total reward', fmt(rollout.total_reward));
    // The verdict the reward cannot give (ADR-409): a tumble scores too.
    var gait = rollout.gait;
    if (gait && gait.available) {
      row('rollout gait', gait.walked ? 'walked' : 'did not walk \u2014 ' + gait.findings.join('; '));
      row('rollout body travel', fmt(gait.planar_travel_mm) + ' mm \u00b7 tilt \u2264 ' + fmt(gait.max_tilt_deg) + '\u00b0 \u00b7 heading ' + fmt(gait.heading_final_deg) + '\u00b0');
    } else if (gait) row('rollout gait', 'not judged: ' + (gait.reason || 'unavailable'));
  }

  function diskFor(run) {
    // The selected run's disk use travels with its detail (ADR-322), never
    // with the run list; until it arrives the panel says so.
    if (!run) return null;
    if (state.detail && state.detail.run === run.run && state.detail.disk) return state.detail.disk;
    return { state: 'pending' };
  }

  var diskKey = null;
  function sizeCell(sized) {
    // Partial directory sizes remain visibly lower bounds, including zero.
    if (!sized) return el('td', { className: 'muted', 'data-size': 'pending', text: '…' });
    if (sized.status === 'retained' || sized.status === 'truncated') return el('td', { 'data-size': String(sized.bytes), 'data-lower-bound': String(!!sized.lower_bound), text: (sized.lower_bound ? 'at least ' : '') + bytes(sized.bytes) + (sized.status === 'truncated' ? ' · truncated' : '') + (sized.files > 1 ? ' · ' + sized.files + ' files' : '') });
    if (sized.status === 'missing') return el('td', { className: 'status-missing', 'data-size': 'missing', text: 'missing — nothing on disk' });
    if (sized.status === 'refused') return el('td', { className: 'status-error', 'data-size': 'refused', text: 'refused — not read' });
    return el('td', { className: 'status-none', 'data-size': 'none', text: '—' });
  }

  function renderDisk(run) {
    var disk = diskFor(run), panel = $('disk'), summary = $('disk-summary'), dirs = $('disk-dirs'), shared = $('disk-shared');
    var key = JSON.stringify([run && run.run, disk]);
    if (key === diskKey) return;
    diskKey = key;
    clearChildren(dirs); clearChildren(shared);
    summary.dataset.bytes = ''; summary.dataset.files = ''; summary.dataset.sharedBytes = '';
    if (!disk) { panel.dataset.state = 'unselected'; summary.textContent = 'select a run to see what it keeps on disk'; return; }
    panel.dataset.state = disk.state;
    if (disk.state === 'pending') { summary.textContent = 'Disk use: counting…'; return; }
    if (disk.state === 'unreadable') { summary.textContent = 'Disk use: not counted — ' + disk.reason; return; }
    summary.dataset.bytes = String(disk.bytes); summary.dataset.files = String(disk.files); summary.dataset.sharedBytes = String(disk.shared_bytes);
    summary.textContent = 'Disk use: ' + bytes(disk.bytes) + ' in ' + disk.files + ' file(s) under runs/' + run.run + '/' +
      (disk.hardlinked_entries ? ' · ' + disk.hardlinked_entries + ' hard-linked entr' + (disk.hardlinked_entries === 1 ? 'y' : 'ies') + ' counted once' : '') +
      (disk.skipped_count ? ' · ' + disk.skipped_count + ' entr' + (disk.skipped_count === 1 ? 'y' : 'ies') + ' skipped (symlinks are never followed)' : '') +
      (disk.state === 'truncated' ? ' · TRUNCATED: ' + disk.reason : '') +
      ' · apparent sizes, counted from this run\'s permitted files only';
    Object.keys(disk.by_dir || {}).sort().forEach(function (dir) {
      var entry = disk.by_dir[dir];
      dirs.appendChild(el('li', { 'data-dir': dir, 'data-bytes': String(entry.bytes), text: (dir === '.' ? '(run root)' : dir + '/') + ' · ' + bytes(entry.bytes) + ' · ' + entry.files + ' file(s)' }));
    });
    (disk.skipped || []).forEach(function (item) {
      dirs.appendChild(el('li', { className: 'status-missing', 'data-skipped': item.path, text: item.path + ' · skipped: ' + item.reason }));
    });
    var references = (disk.references || {}).project_artifacts || {};
    Object.keys(references).sort().forEach(function (key) {
      var item = references[key];
      if (!['retained', 'truncated'].includes(item.status) || item.in_run) return;
      var who = item.shared_with || [];
      shared.appendChild(el('li', { 'data-key': key, 'data-shared': String(who.length > 0), 'data-bytes': String(item.bytes),
        text: 'project ' + key + ' ' + item.path + ' · ' + (item.lower_bound ? 'at least ' : '') + bytes(item.bytes) + (item.status === 'truncated' ? ' · truncated' : '') + ' · outside this run, not in its total' +
              (who.length ? ' · shared with ' + who.join(', ') + ' (counted once for the project)' : ' · cited by this run only') }));
    });
    if (disk.shared_bytes || disk.shared_lower_bound) shared.appendChild(el('li', { className: 'muted', 'data-shared-total': String(disk.shared_bytes), text: 'project references outside this run: ' + (disk.shared_lower_bound ? 'at least ' : '') + bytes(disk.shared_bytes) + ' (each file counted once however many runs cite it)' }));
  }

  function renderArtifacts() {
    var run = selectedRun();
    var problems = $('problems'), body = $('artifacts').querySelector('tbody'), videos = $('videos');
    clearChildren(problems); clearChildren(body);
    renderDisk(run);
    if (!run) { clearChildren(videos); delete videos.dataset.key; body.appendChild(el('tr', {}, [el('td', { text: 'select a run to see its retained artifacts' }), el('td'), el('td'), el('td')])); return; }
    (run.problems || []).forEach(function (problem) { problems.appendChild(el('li', { text: problem })); });
    var resolved = run.resolved || { artifacts: {}, project_artifacts: {}, videos: [] };
    var disk = diskFor(run), sizes = disk && disk.references ? disk.references : null;
    function rows(group, prefix) {
      Object.keys(resolved[group] || {}).sort().forEach(function (key) {
        var item = resolved[group][key];
        var status, cls, link = null;
        if (item.path == null) { status = 'not recorded'; cls = 'status-none'; }
        else if (item.error) { status = 'refused: ' + item.error; cls = 'status-error'; }
        else if (!item.exists) { status = 'missing'; cls = 'status-missing'; }
        else { status = 'retained'; cls = 'status-retained'; if (key !== 'project_docs') link = prefix + encodeURIComponent(run.run) + '/' + key; }
        var cell = el('td', { className: cls, 'data-status': status.split(':')[0] });
        if (link) { cell.appendChild(el('a', { href: link, text: status })); cell.appendChild(document.createTextNode(' · ')); cell.appendChild(el('a', { href: link + '?download=1', text: 'download' })); }
        else cell.textContent = status;
        var sized = sizes ? (key === 'project_docs' && group === 'artifacts' ? sizes.project_docs : (sizes[group] || {})[key]) : null;
        body.appendChild(el('tr', { 'data-group': group, 'data-key': key }, [el('td', { text: group + '.' + key }), el('td', { className: 'mono', text: item.path == null ? '—' : item.path }), cell, sizeCell(sized)]));
      });
    }
    rows('artifacts', BASE + '/artifact/run/');
    rows('project_artifacts', BASE + '/artifact/project/');
    var videoSizes = sizes ? sizes.videos || [] : [];
    function updateVideoSizes() {
      videos.querySelectorAll('[data-video-size]').forEach(function (node) {
        var sized = videoSizes[Number(node.dataset.videoSize)];
        node.textContent = sized && sized.status === 'retained' ? ' · ' + bytes(sized.bytes) : '';
      });
    }
    var videoKey = JSON.stringify([run.run, run.videos, resolved.videos, run.video_render]);
    if (videos.dataset.key === videoKey) { updateVideoSizes(); return; }
    videos.dataset.key = videoKey;
    clearChildren(videos);
    var recorded = run.videos || [];
    if (recorded.length) {
      var available = recorded.filter(function (_, index) {
        var item = (resolved.videos || [])[index] || {};
        return item.exists && !item.error;
      }).length;
      var availability = available === recorded.length ? 'available' : available ? 'partly available' : 'unavailable';
      videos.appendChild(el('li', { 'data-video-availability': availability,
        className: available === recorded.length ? 'status-retained' : 'status-missing',
        text: 'Video files: ' + availability + ' (' + available + '/' + recorded.length + ' retained)' }));
    }
    if (run.video_render) videos.appendChild(el('li', {text: 'Recorded video render: ' + run.video_render.state + (run.video_render.error ? ' — ' + run.video_render.error + '. Retry the CLI video command after fixing the retained inputs or encoder.' : '')}));
    if (!recorded.length) videos.appendChild(el('li', { className: 'muted', text: 'videos: none recorded for this run' }));
    recorded.forEach(function (video, index) {
      var item = (resolved.videos || [])[index] || {};
      var line = el('li', { 'data-video': String(index) });
      var label = 'video ' + index + ' · ' + (video.path || '?') + ' · revision ' + short(video.accepted_revision || (run.model || {}).accepted_revision) + ' · policy ' + short(video.policy_sha256) + ' · seed ' + fmt(video.seed) + ' · ' + fmt(video.sim_seconds) + ' s · ' + (video.style || 'historical legacy style') + ' · showing ' + (video.showing || 'not recorded (recorded before videos named what they show)');
      line.setAttribute('data-showing', video.showing ? 'solids' : 'unrecorded');
      if (item.exists && !item.error) {
        var url = BASE + '/video/run/' + encodeURIComponent(run.run) + '/' + index;
        var player = el('video', { controls: true, preload: 'metadata', src: url });
        // A play control of the page's own, sized for a finger (DASHBOARD.md
        // §5): the native controls' tap targets are not the same on every phone.
        var play = el('button', { type: 'button', className: 'video-play', 'data-video-play': String(index), text: 'Play' });
        play.addEventListener('click', function () { if (player.paused) player.play(); else player.pause(); });
        ['play', 'pause', 'ended'].forEach(function (event) {
          player.addEventListener(event, function () { play.textContent = player.paused ? 'Play' : 'Pause'; });
        });
        line.appendChild(player);
        line.appendChild(el('div', { className: 'caption' }, [play, el('span', { text: label }), el('span', { 'data-video-size': String(index) }),
                                                            document.createTextNode(' · '), el('a', { href: url + '?download=1', text: 'download' })]));
      } else {
        line.appendChild(el('span', { className: 'status-missing', text: label + ' — ' + (item.error ? 'refused: ' + item.error : 'missing') + '. Retry the CLI video command after restoring the retained inputs.' }));
      }
      videos.appendChild(line);
    });
    updateVideoSizes();
  }

  function showDoc(url, title) {
    var view = $('doc-view'), request = ++state.docRequest;
    state.following = false;
    view.classList.remove('hidden');
    view.textContent = 'loading ' + title + '…';
    fetch(url, { cache: 'no-store' }).then(function (response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.text();
    }).then(function (body) {
      if (request === state.docRequest) view.textContent = '# ' + title + '\nLoaded on open; click the document again to refresh.\n\n' + body;
    }).catch(function (error) {
      if (request === state.docRequest) view.textContent = title + ': ' + error.message;
    });
  }

  function renderDocs() {
    var run = selectedRun(), docs = $('docs'), decisions = $('decisions');
    clearChildren(docs); clearChildren(decisions);
    var key = JSON.stringify([state.selected, run ? (run.model || {}).accepted_revision : state.review.accepted.revision]);
    if (key !== state.docKey) {
      state.docKey = key;
      state.docRequest++;
      $('doc-view').classList.add('hidden');
      $('doc-view').textContent = '';
    }
    if (!run) {
      var review = state.review;
      var names = ['ARCHITECTURE.md', 'DECISIONS.md', 'PROGRESS.md'].filter(function (name) { return review.docs[name]; }).concat(review.docs.domain || []);
      text('docs-note', names.length ? 'project documents now (current, not a snapshot)' : 'no project documents');
      names.forEach(function (name) {
        docs.appendChild(el('li', { 'data-doc': name }, [el('a', { href: '#', text: name, onclick: function (event) { event.preventDefault(); showDoc(BASE + '/doc/current/' + name, name); } })]));
      });
      (review.decisions || []).forEach(function (heading) { decisions.appendChild(el('li', { 'data-decision': heading, text: heading })); });
      if (!(review.decisions || []).length) decisions.appendChild(el('li', { className: 'muted', text: 'no decisions recorded' }));
      return;
    }
    var snapshot = run.project_docs || {};
    var files = Object.keys(snapshot.files || {}).sort();
    text('docs-note', files.length ? 'snapshot taken when this run was recorded — ' + (snapshot.note || '') : 'no document snapshot for this run (' + (snapshot.note || 'none') + ')');
    files.forEach(function (name) {
      docs.appendChild(el('li', { 'data-doc': name }, [el('a', { href: '#', text: name, onclick: function (event) { event.preventDefault(); showDoc(BASE + '/doc/run/' + encodeURIComponent(run.run) + '/' + name, name + ' (snapshot)'); } })]));
    });
    (snapshot.skipped || []).forEach(function (item) { docs.appendChild(el('li', { className: 'status-missing', text: item.path + ': skipped (' + item.reason + ')' })); });
    decisions.appendChild(el('li', { className: 'muted', text: 'decisions as of this run are in the DECISIONS.md snapshot above' }));
  }

  // The parts roster (ADR-522): each part's appearance role and where it came from, printed or
  // purchased, and whether the engine's printable roster has it. A summary line leads.
  function partLooks(component) {
    if (!component.role) return '';
    return ' · ' + component.role + (component.role_source === 'declared' ? ' (declared)' : '') + ' · ' + component.supplier +
      (component.printable ? ' · printable' : '');
  }

  function renderModelComponents(manifest, loaded) {
    var list = $('model-components'), looks = manifest.appearance || {};
    clearChildren(list);
    var components = manifest.components || [];
    if (manifest.available) {
      var printed = components.filter(function (c) { return c.supplier === 'printed'; }).length;
      var bought = components.filter(function (c) { return c.supplier === 'purchased'; }).length;
      var printable = components.filter(function (c) { return c.printable; }).length;
      list.appendChild(el('li', { id: 'parts-summary', className: 'muted', 'data-appearance': looks.available ? 'roles' : 'index', title: looks.source || '',
        text: looks.available
          ? 'parts: ' + printed + ' printed, ' + bought + ' purchased, ' + printable + ' printable · colours by role: ' +
            Object.keys(looks.palette).map(function (role) { return role + ' ' + looks.palette[role]; }).join(', ')
          : 'parts: ' + printable + ' printable · index colours (' + looks.reason + ')' }));
    }
    components.forEach(function (component, index) {
      var mesh = loaded.filter(function (entry) { return entry.name === component.name; })[0];
      var line = el('li', { 'data-component': component.name, 'data-mesh': component.mesh_status,
        'data-role': component.role || '', 'data-supplier': component.supplier || '', 'data-printable': String(!!component.printable) });
      if (mesh) { var swatch = el('span', { className: 'swatch' }); swatch.style.background = 'rgb(' + mesh.color.join(',') + ')'; line.appendChild(swatch); }
      line.appendChild(document.createTextNode(component.name + (component.output && component.output !== component.name ? ' ← ' + component.output : '') +
        partLooks(component) + ' · mesh ' + component.mesh_status + (mesh ? ' (' + mesh.triangles + ' triangles)' : '') + ' · placement: ' + component.placement_source +
        ' · collision: ' + proxySummary(manifest, component.name)));
      list.appendChild(line);
    });
  }

  // What the simulation collides with, per component, from the manifest's collision block
  // (the run's own retained MJCF): a summary for the list and the geoms for the viewer.
  function proxySummary(manifest, name) {
    var collision = manifest.collision || {};
    if (!collision.available) return 'not retained';
    var kinds = {};
    (collision.geoms || []).forEach(function (geom) { if (geom.component === name) kinds[geom.type] = (kinds[geom.type] || 0) + 1; });
    var parts = Object.keys(kinds).sort().map(function (kind) { return kinds[kind] + ' ' + kind; });
    return parts.length ? parts.join(', ') : 'none declared';
  }

  // Which parts' collision shapes touch at rest (ADR-508): the export's t=0 contacts, one
  // line per pair, interpenetrating pairs first. The agent reads the same block through
  // `inspect scope=contacts`.
  function renderContacts(manifest) {
    var list = $('collision-contacts'), contacts = (manifest && manifest.contacts) || {};
    clearChildren(list);
    if (!manifest || !manifest.available) { list.dataset.state = 'none'; return; }
    if (!contacts.available) {
      list.dataset.state = 'unavailable';
      list.appendChild(el('li', { className: 'muted', text: 'touching at rest (t=0): not measured \u2014 ' + contacts.reason }));
      return;
    }
    var pairs = contacts.pairs || [];
    list.dataset.state = pairs.some(function (pair) { return pair.penetrating; }) ? 'penetrating' : (pairs.length ? 'touching' : 'clear');
    list.appendChild(el('li', { className: 'muted', title: contacts.source, text: pairs.length
      ? 'touching at rest (t=0): ' + pairs.length + ' pair(s), ' + contacts.count + ' contact point(s) between collision shapes' +
        (contacts.omitted ? ' (' + contacts.omitted + ' points past the listing; pairs may be incomplete)' : '')
      : 'touching at rest (t=0): nothing \u2014 no collision shapes touch at the starting pose' }));
    pairs.forEach(function (pair) {
      var depth = pair.deepest_mm === null ? '?' : Math.abs(pair.deepest_mm).toFixed(1);
      list.appendChild(el('li', {
        'data-pair': pair.components.join('|'), 'data-penetrating': String(pair.penetrating),
        className: pair.penetrating ? 'status-missing' : '',
        text: pair.components.join(' \u00b7 ') + ' \u2014 ' + (pair.penetrating ? 'interpenetrating ' + depth + ' mm' : 'resting (' + depth + ' mm)') +
          ', ' + pair.points + ' point(s)' }));
    });
  }

  function renderShowing() {
    var status = $('model-status'), toggle = $('show-collision'), note = $('collision-note');
    var manifest = state.model, collision = (manifest && manifest.collision) || {};
    var stats = state.viewer.available ? state.viewer.stats() : null;
    var drawable = !!(manifest && manifest.available && collision.available && stats && stats.proxies.drawn > 0);
    toggle.disabled = !drawable;
    toggle.checked = state.showProxies;
    renderContacts(manifest);
    if (!manifest || !manifest.available) { note.textContent = ''; status.removeAttribute('data-showing'); return; }
    if (!collision.available) note.textContent = '(none retained: ' + collision.reason + ')';
    else if (!drawable) note.textContent = '(' + collision.geoms.length + ' listed, none drawable)';
    else note.textContent = '(' + stats.proxies.drawn + ' proxies from ' + collision.source + ')';
    var showing = stats ? stats.showing : 'nothing drawn';
    status.dataset.showing = state.showProxies && drawable ? 'solids+proxies' : 'solids';
    status.textContent = status.textContent.replace(/ · showing: .*$/, '') + ' · showing: ' + showing +
      (state.showProxies && drawable ? ' (' + stats.proxies.drawn + ' outlines from ' + collision.source + ')' : '');
  }

  // Dimensions (DASHBOARD.md §31, ADR-524): the script's declared part.measurement records,
  // measured by the engine on the exact BREP. Each is drawn on the component that shows its
  // output, re-laid-out in screen space on every frame the viewer draws, so it follows orbit,
  // zoom, explode and playback. A record the view cannot place this frame is listed, not drawn.
  var SVG = 'http://www.w3.org/2000/svg';
  function drawDimensions() {
    var overlay = $('dimension-overlay'), manifest = state.model, block = (manifest && manifest.measurements) || {};
    clearChildren(overlay);
    var placed = 0;
    if (state.showDimensions && manifest && manifest.available && block.available && state.viewer.available) {
      (block.records || []).forEach(function (record) {
        if (!record.drawn) return;
        var shape = window.CadexViewer.dimensionLayout(record, function (point) { return state.viewer.toScreen(record.component, point); });
        if (!shape) return;
        var group = document.createElementNS(SVG, 'g');
        group.setAttribute('data-measurement', record.name);
        group.setAttribute('data-form', shape.form);
        shape.lines.forEach(function (l) {
          var line = document.createElementNS(SVG, 'line');
          line.setAttribute('x1', l[0].toFixed(1)); line.setAttribute('y1', l[1].toFixed(1));
          line.setAttribute('x2', l[2].toFixed(1)); line.setAttribute('y2', l[3].toFixed(1));
          group.appendChild(line);
        });
        var label = document.createElementNS(SVG, 'text');
        label.setAttribute('x', shape.at[0].toFixed(1)); label.setAttribute('y', shape.at[1].toFixed(1));
        label.setAttribute('text-anchor', shape.anchor);
        label.textContent = shape.text;
        group.appendChild(label);
        overlay.appendChild(group);
        placed++;
      });
    }
    overlay.dataset.drawn = String(placed);
  }

  function renderDimensions() {
    var manifest = state.model, block = (manifest && manifest.measurements) || {}, list = $('dimension-list');
    var toggle = $('show-dimensions'), note = $('dimension-note');
    var records = block.available ? block.records : [];
    var drawable = records.filter(function (r) { return r.drawn; }).length;
    toggle.disabled = !(manifest && manifest.available && drawable);
    toggle.checked = state.showDimensions;
    clearChildren(list);
    if (!manifest || !manifest.available) note.textContent = '';
    else if (!block.available) note.textContent = '(none: ' + block.reason + ')';
    else note.textContent = '(' + records.length + ' declared, ' + drawable + ' drawable; measured by the engine on the exact BREP)';
    records.forEach(function (record) {
      list.appendChild(el('li', { 'data-measurement': record.name, 'data-drawn': String(record.drawn),
        text: record.name + (record.label ? ' (' + record.label + ')' : '') + ': ' + record.text + ' · ' + record.kind +
          ' · ' + record.frame + (record.reason ? ' · ' + record.reason : '') }));
    });
    drawDimensions();
  }

  function loadModel() {
    var run = selectedRun();
    var url = run ? BASE + '/api/model/run/' + encodeURIComponent(run.run) : BASE + '/api/model/accepted';
    var status = $('model-status');
    status.dataset.state = 'loading'; status.textContent = 'loading model…';
    clearChildren($('model-components'));
    var token = state.selected;
    return fetchJson(url).then(function (manifest) {
      if (token !== state.selected) return;
      state.model = manifest;
      if (!manifest.available) {
        state.viewer.clear();
        status.dataset.state = 'missing';
        status.textContent = 'no model to show: ' + manifest.reason + ' (revision ' + short(manifest.revision) + ')';
        renderModelComponents(manifest, []);
        renderShowing();
        renderDimensions();
        renderExplode(manifest);
        renderPlayback(manifest);
        return;
      }
      if (!state.viewer.available) {
        status.dataset.state = 'error';
        status.textContent = 'WebGL unavailable in this browser; the model is listed but not drawn';
        renderModelComponents(manifest, []);
        return;
      }
      // Mesh URLs in the manifest are server-absolute; BASE mounts them.
      return state.viewer.load(manifest, function (url, options) { return window.fetch(BASE + url, options); }).then(function (loaded) {
        if (token !== state.selected) return;
        // The proxies ride along, hidden unless the toggle is on: the solids are what is shown.
        state.viewer.setProxies(manifest.collision && manifest.collision.available ? manifest.collision.geoms : []);
        state.viewer.showProxies(state.showProxies);
        // A reload keeps the pick when the part is still there, and drops it when it is not.
        if (commentPart) pickPart(state.viewer.highlight(commentPart));
        var stats = state.viewer.stats();
        status.dataset.state = 'loaded';
        status.textContent = (run ? (run.relation === 'historical' ? 'HISTORICAL model ' : 'model ') + 'of run ' + run.run : 'accepted model') +
          ' at revision ' + short(manifest.revision) + ' · ' + stats.components + ' component(s), ' + stats.triangles + ' triangles · from ' + manifest.source +
          ' · placements: ' + manifest.placement_source;
        renderModelComponents(manifest, loaded);
        renderShowing();
        renderDimensions();
        renderExplode(manifest);
        renderPlayback(manifest);
      });
    }).catch(function (error) {
      status.dataset.state = 'error';
      status.textContent = 'model failed to load: ' + error.message;
    });
  }

  // The concept sheet (DASHBOARD.md §14, ADR-430): the project's studio
  // hero and sheet as the last `cadex render` drew them, named by the
  // revision they were drawn from and its relation to the accepted one now.
  // The stage leads with it once, on the first poll that finds one.
  var conceptKey = null, conceptLed = false;
  function renderPresentation() {
    var shown = state.review.presentation || { available: false, reason: 'no presentation block' };
    var key = JSON.stringify([shown.available, shown.revision, shown.relation, shown.files]);
    if (key === conceptKey) return;
    conceptKey = key;
    var status = $('concept-status'), figure = $('concept-figure');
    status.dataset.state = shown.available ? shown.relation : 'empty';
    if (!shown.available) {
      status.textContent = shown.reason || 'no concept sheet';
      figure.hidden = true;
      $('concept-sheet').removeAttribute('src');
      return;
    }
    var numbers = shown.numbers || {}, stamp = '?r=' + encodeURIComponent(shown.revision) + '-' + shown.files.sheet.bytes;
    status.textContent = shown.relation === 'current'
      ? 'the accepted design, drawn from revision ' + short(shown.revision)
      : shown.relation + ': drawn from revision ' + short(shown.revision) + ', not the accepted one';
    $('concept-sheet').src = BASE + '/presentation/sheet.png' + stamp;
    $('concept-open').href = BASE + '/presentation/sheet.png' + stamp;
    $('concept-hero').hidden = !shown.files.hero;
    text('concept-caption', [numbers.name,
      numbers.mass_kg == null ? 'mass —' : numbers.mass_kg.toFixed(2) + ' kg',
      numbers.servo_count == null ? 'servos —' : numbers.servo_count + ' servos',
      (numbers.size_mm || []).map(function (v) { return Math.round(v); }).join(' × ') + ' mm'].join(' · '));
    figure.hidden = false;
    if (!conceptLed && window.cadexFrame) { conceptLed = true; window.cadexFrame.show('concept'); }
  }

  // The evaluation (DASHBOARD.md §17, ADR-459): a policy held to its
  // task's success spec on every frozen seed, as `cadex evaluate` wrote it.
  // /api/project lists each evaluation as a summary; the one on screen is
  // fetched whole from /api/evaluation/<name>, once per file identity. The
  // one shown is the reader's pick, else the newest of the selected run's
  // policy, else the newest at the accepted revision, else the newest.
  var evaluationKey = null, evaluationRequest = 0, evaluationPicked = null, evaluationShown = null;
  function evaluationRows() { return (state.review && state.review.evaluations) || []; }
  function shownEvaluation() {
    var rows = evaluationRows();
    if (!rows.length) return null;
    var picked = rows.filter(function (row) { return row.name === evaluationPicked; })[0];
    if (picked) return picked;
    var run = selectedRun(), sha = run && run.policy && run.policy.sha256;
    var ofRun = sha ? rows.filter(function (row) { return row.policy_sha256 === sha; }) : [];
    var current = rows.filter(function (row) { return row.relation === 'current'; });
    var pool = ofRun.length ? ofRun : current.length ? current : rows;
    return pool[pool.length - 1];
  }
  // Five significant figures with no trailing zeros: 0.15, 6.26, 835.98.
  function num(value) { return value == null ? '—' : typeof value === 'number' ? String(Number(value.toPrecision(5))) : String(value); }
  function bound(row) {
    var parts = [];
    if (row.min != null) parts.push('≥ ' + num(row.min));
    if (row.max != null) parts.push('≤ ' + num(row.max));
    return parts.join(' and ') || '—';
  }
  function cell(value, attrs) {
    var node = el('td', attrs || {});
    node.textContent = num(value);
    return node;
  }
  function fillTable(id, head, rows) {
    var table = $(id), thead = table.querySelector('thead'), body = table.querySelector('tbody');
    if (head) { clearChildren(thead); thead.appendChild(el('tr', {}, head.map(function (name) { return el('th', { text: String(name) }); }))); }
    clearChildren(body);
    rows.forEach(function (row) { body.appendChild(row); });
  }
  function ended(episode) {
    return (episode.termination || (episode.truncated ? 'horizon' : 'ended')) + ' at ' + num(episode.duration_s) + ' s';
  }
  function drawEvaluation(shown, detail) {
    var report = detail.report, summary = report.summary || {}, seeds = report.seeds || [];
    var film = report.film || { state: 'none', seeds: [] };
    var filmed = {};
    (film.seeds || []).forEach(function (row) { filmed[row.seed] = row; });
    var base = BASE + '/evaluation/' + encodeURIComponent(detail.name) + '/';
    fillTable('evaluation-predicates', null, (summary.predicates || []).map(function (row) {
      var value = row.value || {}, passing = !(row.failed_seeds || []).length;
      return el('tr', { 'data-predicate': row.id }, [cell(row.id), cell(row.metric), cell(bound(row)),
        cell(row.passed + ' of ' + summary.seeds, { 'data-pass': String(passing) }),
        cell(row.value ? value.min : 'not measured'), cell(row.value ? value.median : null), cell(row.value ? value.max : null)]);
    }));
    var ids = (summary.predicates || []).map(function (row) { return row.id; });
    fillTable('evaluation-seeds', ['seed', 'verdict', 'ended'].concat(ids), seeds.map(function (row) {
      var byId = {};
      (row.predicates || []).forEach(function (item) { byId[item.id] = item; });
      var first = cell(row.seed);
      if (filmed[row.seed]) first.addEventListener('click', function () {
        var target = $('evaluation-film').querySelector('[data-film-seed="' + row.seed + '"]');
        if (target) target.scrollIntoView({ block: 'start' });
      });
      return el('tr', { 'data-seed': String(row.seed), 'data-filmed': String(!!filmed[row.seed]) }, [first,
        cell(row.void ? 'void: ' + row.void : row.pass ? 'pass' : 'fail', { 'data-pass': String(!!row.pass) }),
        cell(ended(row.episode || {}))].concat(ids.map(function (id) {
          var item = byId[id];
          if (!item) return cell(null);
          return cell(item.value == null ? 'not measured' : item.value, { 'data-pass': String(!!item.pass), title: item.why || '' });
        })));
    }));
    var head = ['seed'].concat(seeds.map(function (row) { return row.seed; }));
    var names = [];
    seeds.forEach(function (row) { Object.keys(row.metrics || {}).forEach(function (name) { if (names.indexOf(name) < 0) names.push(name); }); });
    fillTable('evaluation-metrics', head, names.map(function (name) {
      return el('tr', { 'data-metric-row': name }, [cell(name)].concat(seeds.map(function (row) { return cell((row.metrics || {})[name]); })));
    }));
    var terms = [];
    seeds.forEach(function (row) { ((row.reward || {}).terms || []).forEach(function (term) { if (terms.indexOf(term.label) < 0) terms.push(term.label); }); });
    fillTable('evaluation-reward', head, terms.map(function (label) {
      return el('tr', { 'data-term': label }, [cell(label)].concat(seeds.map(function (row) {
        var term = ((row.reward || {}).terms || []).filter(function (item) { return item.label === label; })[0];
        return cell(term ? term.total : null);
      })));
    }).concat([el('tr', { 'data-term': 'total' }, [cell('total')].concat(seeds.map(function (row) { return cell((row.reward || {}).total); })))]));
    var note = film.state === 'ready' ? 'Drawn from the traces this evaluation kept, on the dark prototype floor; every frame carries its simulation time. Materials: ' + ((film.materials || {}).source || 'not recorded') + '.'
      : film.state === 'failed' ? 'The film was not completed: ' + film.error
      : film.state === 'skipped' ? 'No seed was filmed (cadex evaluate --film none).'
      : 'This evaluation has no film: it was written before evaluations were filmed. Run cadex evaluate --film-only.';
    text('evaluation-film-note', note);
    var list = $('evaluation-film');
    clearChildren(list);
    (film.seeds || []).forEach(function (row) {
      var line = el('li', { 'data-film-seed': String(row.seed) }, [el('h3', { text: 'Seed ' + row.seed })]);
      [['overview', 'Overview'], ['detail', 'Detail']].forEach(function (pair) {
        var item = row[pair[0]], file = item && (detail.files || {})[item.file];
        if (!item) return;
        var times = item.times_s || [], caption = pair[1] + ' · ' + item.frames + ' frames, ' + num(times[0]) + ' to ' + num(times[times.length - 1]) + ' s · ' + item.view;
        if (file && file.exists) {
          var url = base + item.file + '?v=' + item.sha256.slice(0, 12);
          line.appendChild(el('a', { href: url, target: '_blank', rel: 'noopener' }, [el('img', { src: url, alt: pair[1] + ' filmstrip of seed ' + row.seed, 'data-film': pair[0], loading: 'lazy' })]));
          line.appendChild(el('div', { className: 'caption', text: caption + ' · ' + bytes(file.bytes) }));
        } else line.appendChild(el('div', { className: 'caption status-missing', text: caption + ' — missing' }));
      });
      if (row.video) {
        var clip = (detail.files || {})[row.video.file], label = 'Video · ' + num(row.video.sim_seconds) + ' s at ' + row.video.fps + ' frames a second';
        if (clip && clip.exists) {
          var src = base + row.video.file;
          line.appendChild(el('video', { controls: true, preload: 'metadata', src: src + '?v=' + row.video.sha256.slice(0, 12), 'data-film': 'video' }));
          line.appendChild(el('div', { className: 'caption' }, [el('span', { text: label + ' · ' + bytes(clip.bytes) + ' · ' }), el('a', { href: src + '?download=1', text: 'download' })]));
        } else line.appendChild(el('div', { className: 'caption status-missing', text: label + ' — missing' }));
      }
      list.appendChild(line);
    });
    $('evaluation-download').href = base + 'evaluation.json?download=1';
    $('evaluation-body').hidden = false;
    evaluationShown = { name: detail.name, verdict: report.verdict, seeds: seeds.length, film: film.state, filmed: (film.seeds || []).map(function (row) { return row.seed; }) };
  }
  function renderEvaluation() {
    var rows = evaluationRows(), shown = shownEvaluation();
    var key = JSON.stringify([rows.map(function (row) { return [row.name, row.stamp, row.relation]; }), shown && shown.name]);
    if (key === evaluationKey) return;
    evaluationKey = key;
    var status = $('evaluation-status'), dot = $('evaluation-dot'), list = $('evaluation-list');
    clearChildren(list);
    if (rows.length > 1) rows.slice().reverse().forEach(function (row) {
      var button = el('button', { type: 'button', 'data-evaluation': row.name,
        text: short(row.accepted_revision) + ' · ' + (row.policy_output || 'policy') + ' · ' + row.verdict + ' ' + row.passed + '/' + row.seeds + ' · ' + row.relation,
        onclick: function () { evaluationPicked = row.name; renderEvaluation(); } });
      button.setAttribute('aria-pressed', String(!!shown && row.name === shown.name));
      list.appendChild(el('li', {}, [button]));
    });
    if (!shown) {
      status.dataset.state = 'empty';
      status.textContent = 'no evaluation: cadex evaluate holds the accepted policy to its task\'s success spec and writes one here';
      $('evaluation-body').hidden = true;
      delete dot.dataset.state; dot.title = '';
      evaluationShown = null; evaluationRequest++;
      return;
    }
    var verdict = shown.verdict === 'pass' ? 'pass' : 'fail';
    status.dataset.state = dot.dataset.state = verdict;
    dot.title = 'evaluation: ' + verdict;
    status.textContent = [verdict + ': ' + shown.passed + ' of ' + shown.seeds + ' seeds pass',
      'policy ' + (shown.policy_output || '?') + ' (' + short(shown.policy_sha256) + ') on task ' + (shown.task_output || '?'),
      'revision ' + short(shown.accepted_revision) + (shown.relation === 'current' ? ', the accepted design' : ', ' + shown.relation + ': not the accepted design'),
      'evaluated ' + shown.evaluated_at].concat(shown.failing.length ? ['failing ' + shown.failing.join(', ')] : []).join(' · ');
    var request = ++evaluationRequest;
    fetchJson(BASE + '/api/evaluation/' + encodeURIComponent(shown.name)).then(function (detail) {
      if (request === evaluationRequest) drawEvaluation(shown, detail);
    }).catch(function (error) {
      if (request !== evaluationRequest) return;
      // A report that vanished between polls: say so, and let the next poll try again.
      $('evaluation-body').hidden = true;
      status.textContent += ' — ' + error.message;
      evaluationKey = null; evaluationShown = null;
    });
  }

  function render() {
    renderFreshness();
    if (!state.review) return;
    if (state.selected !== 'accepted' && !selectedRun()) state.selected = 'accepted';
    renderHeader(); renderSidebar(); renderIdentity(); renderPolicyOrigin(); renderParams(); renderTraining(); renderArtifacts(); renderDocs();
    renderNotes();
    renderComments();
    renderRevisions();
    renderExports();
    renderDrawings();
    renderSections();
    renderPresentation();
    renderEvaluation();
  }

  function loadDetail() {
    // One run's histories and verified checkpoints, for the selected run only.
    var run = selectedRun(), request = ++detailRequest;
    if (!run) { state.detail = null; lastPoll.detail_bytes = 0; return Promise.resolve(); }
    return fetchJson(BASE + '/api/run/' + encodeURIComponent(run.run), 'detail_bytes').then(function (detail) {
      if (request !== detailRequest) return;
      state.detail = detail;
    }).catch(function () {
      // A run that vanished between polls, or an unreachable server: the
      // list's summary stays on screen and the next poll tries again.
      if (request === detailRequest) state.detail = null;
    });
  }

  function select(view) {
    state.following = false;
    state.selected = view;
    originKey = null;
    render();
    return Promise.all([loadModel(), loadDetail().then(function () { renderTraining(); renderArtifacts(); })]);
  }

  function modelIdentity() {
    if (!state.review) return null;
    var run = selectedRun(), model = run ? (run.model || {}) : state.review.accepted;
    return JSON.stringify([state.selected, run ? model.accepted_revision : model.revision, model.digest]);
  }

  function poll() {
    if (pendingPoll) return pendingPoll;
    var started = performance.now();
    pendingPoll = fetchJson(BASE + '/api/project', 'project_bytes').then(function (review) {
      var previousModel = modelIdentity();
      if (Array.from($('videos').querySelectorAll('video')).some(function (video) {
        return !video.paused && !video.ended;
      })) state.following = false;
      state.review = review; state.lastOk = new Date(); state.stale = false; state.error = null;
      if (state.following) state.selected = currentView();
      if (state.selected !== 'accepted' && !selectedRun()) state.selected = 'accepted';
      return loadDetail().then(function () {
        render();
        lastPoll.ms = performance.now() - started;
        if (previousModel !== modelIdentity()) return loadModel();
      });
    }).catch(function (error) {
      state.stale = true; state.error = error.message;
      renderFreshness();
    }).finally(function () { pendingPoll = null; });
    return pendingPoll;
  }

  function initialize() {
    $('check-policy-origin').addEventListener('click', function () { renderPolicyOrigin(true); });
    state.viewer = window.CadexViewer.create($('viewer'));
    state.viewer.setOnDraw(drawDimensions);
    $('current-run').addEventListener('click', function () {
      if (!state.review) return;
      select(currentView());
      state.following = true;
    });
    $('model-fit').addEventListener('click', function () { state.viewer.fit(); });
    $('show-dimensions').addEventListener('change', function (event) {
      state.showDimensions = !!event.target.checked;
      drawDimensions();
    });
    $('show-collision').addEventListener('change', function (event) {
      state.showProxies = !!event.target.checked;
      state.viewer.showProxies(state.showProxies);
      renderShowing();
    });
    // The run list is a sidebar at desk and a closed disclosure on a phone
    // (DASHBOARD.md §6); crossing the breakpoint resets it, a tap on the
    // summary toggles it. Only the media query decides, never the run count.
    var phone = window.matchMedia('(max-width: 599px)');
    function foldRuns() { $('runs').open = !phone.matches; }
    foldRuns();
    phone.addEventListener('change', foldRuns);
    $('turn-start').addEventListener('click', function () {
      var prompt = $('turn-prompt').value.trim();
      if (prompt) startTurn(prompt, $('turn-resume').checked);
    });
    $('turn-attach').addEventListener('click', function () {
      if (turnImages.length) { turnImages = []; $('turn-image').value = ''; renderTurnImages(); }
      else $('turn-image').click();
    });
    $('turn-image').addEventListener('change', function () { attachImages($('turn-image').files); });
    if (state.viewer.setOnPick) state.viewer.setOnPick(pickPart);
    $('comment-whole').addEventListener('click', function () { pickPart(''); });
    $('note-send').addEventListener('click', function () {
      var text = $('note-text').value.trim();
      if (text && answerTo) sendComment(text, '', answerTo);
    });
    $('comment-send').addEventListener('click', function () {
      var text = $('comment-text').value.trim();
      if (text) sendComment(text, commentPart);
    });
    $('revision-accept').addEventListener('click', function () { writeRevision('accept', ''); });
    $('revision-reject').addEventListener('click', function () { writeRevision('reject', ''); });
    $('export-run').addEventListener('click', function () { writeExport(); });
    $('explode-amount').addEventListener('input', function (event) { setExplode(event.target.value); });
    $('explode-view').addEventListener('change', function () { renderExplode(state.model, this.value); });
    $('play-toggle').addEventListener('click', togglePlay);
    $('play-time').addEventListener('input', function (event) { stopPlay(); setPlay(event.target.value); });
    $('section-cut').addEventListener('click', function () { writeSection($('section-plane').value, $('section-offset').value.trim()); });
    $('section-clear').addEventListener('click', function () { showCut(null); });
    poll().then(function () { readyResolve(true); });
    setInterval(poll, POLL_MS);
    pollTurn();
    setInterval(pollTurn, TURN_POLL_MS);
  }

  window.cadexReview = {
    ready: ready,
    select: select,
    refresh: poll,
    setParam: writeParams,
    lastWrite: function () { return lastWrite; },
    startTurn: startTurn,
    turn: function () { return { id: turn.id, state: turn.state, text: turn.text, reply: turn.reply, images: turn.images || [] }; },
    attachImages: attachImages,
    attached: function () { return turnImages.map(function (image) { return image.name; }); },
    comment: sendComment,
    lastComment: function () { return lastComment; },
    commentPart: function () { return commentPart; },
    answerNote: answerNote,
    revision: writeRevision,
    lastRevision: function () { return lastRevision; },
    exportModel: writeExport,
    lastExport: function () { return lastExport; },
    explode: setExplode,
    play: setPlay,
    togglePlay: togglePlay,
    playing: function () { return !!playing; },
    playback: function () { return playback && { times_s: playback.times_s, source: playback.source, t: playT }; },
    section: writeSection,
    showCut: showCut,
    lastSection: function () { return lastSection; },
    viewer: function () { return state.viewer; },
    lastPoll: function () { return { project_bytes: lastPoll.project_bytes, detail_bytes: lastPoll.detail_bytes, ms: lastPoll.ms }; },
    state: function () {
      var run = selectedRun();
      return { selected: state.selected, stale: state.stale, error: state.error,
               detail: state.detail ? state.detail.run : null,
               disk: state.detail && state.detail.disk ? { state: state.detail.disk.state, bytes: state.detail.disk.bytes, files: state.detail.disk.files, shared_bytes: state.detail.disk.shared_bytes } : null,
               revision: run ? (run.model || {}).accepted_revision : (state.review && state.review.accepted.revision),
               concept: state.review && state.review.presentation ? { available: state.review.presentation.available, revision: state.review.presentation.revision, relation: state.review.presentation.relation } : null,
               evaluation: evaluationShown,
               relation: run ? run.relation : 'accepted', model: state.model && { available: state.model.available, reason: state.model.reason, revision: state.model.revision },
               runs: state.review ? state.review.runs.map(function (r) { return r.run; }) : [] };
    }
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize);
  else initialize();
})();

// The desk frame (DASHBOARD.md §12): two sidebars whose inner edges drag
// to resize or fold them away, sections that fold under their headings, and
// the stage's tabs. It is presentation only — it reads nothing from the
// server, and remembers the reader's widths, folds and nothing else in this
// browser's localStorage. On a phone held landscape (§13) the same frame
// opens its sidebars as drawers over the model, one at a time and closed by
// default; that open state is not remembered. Below both, the stylesheet
// dissolves the frame and none of this has any visible effect.
(function () {
  'use strict';

  var FRAME = window.matchMedia('(min-width: 1000px), (min-width: 600px) and (max-height: 560px) and (orientation: landscape)');
  var COMPACT = window.matchMedia('(max-width: 999px) and (min-width: 600px) and (max-height: 560px) and (orientation: landscape)');
  var STORE = 'cadex-review-frame';
  var MIN = 200, FOLD_AT = 120, STAGE_MIN = 360;
  var DEFAULTS = { left: 264, right: 340 };
  var saved = {};
  try { saved = JSON.parse(localStorage.getItem(STORE) || '{}') || {}; } catch (_) { saved = {}; }
  var layout = {
    left: { width: +saved.leftWidth || DEFAULTS.left, open: saved.leftOpen !== false },
    right: { width: +saved.rightWidth || DEFAULTS.right, open: saved.rightOpen !== false },
    folded: saved.folded && typeof saved.folded === 'object' ? saved.folded : {},
    drawer: { left: false, right: false }
  };
  // Whether a side is open in the frame as it is now laid out.
  function isOpen(side) { return COMPACT.matches ? layout.drawer[side] : layout[side].open; }
  function setOpen(side, open) {
    if (!COMPACT.matches) { layout[side].open = open; return; }
    layout.drawer[side] = open;
    if (open) layout.drawer[side === 'left' ? 'right' : 'left'] = false;   // one drawer at a time
  }

  function $(id) { return document.getElementById(id); }
  function persist() {
    try {
      localStorage.setItem(STORE, JSON.stringify({ leftWidth: layout.left.width, leftOpen: layout.left.open,
        rightWidth: layout.right.width, rightOpen: layout.right.open, folded: layout.folded }));
    } catch (_) { /* a private window: the layout simply is not remembered */ }
  }
  // The widest a sidebar may be: whatever leaves the stage its minimum beside
  // the other sidebar as it is now.
  // A drawer only has to leave a strip of the model to tap beside it.
  function widest(side) {
    if (COMPACT.matches) return Math.max(MIN, Math.min(420, window.innerWidth - 72));
    var other = side === 'left' ? layout.right : layout.left;
    return Math.max(MIN, window.innerWidth - STAGE_MIN - (other.open ? other.width : 0));
  }
  function apply() {
    var frame = $('frame');
    ['left', 'right'].forEach(function (side) {
      // The remembered width is the reader's; a narrow window only caps what
      // is drawn, so widening the window again gives it back.
      // A drawer keeps its width while closed, so it slides rather than shrinks.
      var pane = layout[side], open = isOpen(side), width = Math.min(Math.max(pane.width, MIN), widest(side));
      frame.style.setProperty('--' + side + '-w', (open || COMPACT.matches ? width : 0) + 'px');
      frame.dataset[side] = open ? 'open' : 'collapsed';
      $('toggle-' + side).setAttribute('aria-expanded', String(open));
      var handle = frame.querySelector('.resizer[data-side="' + side + '"]');
      handle.setAttribute('aria-valuenow', String(open ? Math.round(width) : 0));
      handle.setAttribute('aria-valuemin', '0');
      handle.setAttribute('aria-valuemax', String(Math.round(widest(side))));
    });
  }
  function toggle(side, open) {
    setOpen(side, open == null ? !isOpen(side) : !!open);
    apply(); persist();
  }

  function dragHandle(handle) {
    var side = handle.dataset.side, pointer = null, grab = 0, start = 0;
    function reach(event) {
      var box = $('frame').getBoundingClientRect();
      return side === 'left' ? event.clientX - box.left : box.right - event.clientX;
    }
    handle.addEventListener('pointerdown', function (event) {
      if (!FRAME.matches || event.button > 0) return;
      pointer = event.pointerId;
      // Hold the edge where it was grabbed, so it does not jump to the pointer.
      grab = (isOpen(side) ? parseFloat(getComputedStyle($('frame')).getPropertyValue('--' + side + '-w')) : 0) - reach(event);
      start = layout[side].width;
      handle.setPointerCapture(pointer);
      handle.classList.add('active');
      $('frame').classList.add('dragging');
      document.body.classList.add('resizing');
      event.preventDefault();
    });
    handle.addEventListener('pointermove', function (event) {
      if (event.pointerId !== pointer) return;
      var raw = reach(event) + grab;
      // Dragged most of the way shut, the sidebar folds away; dragged back
      // out past the same point, it opens at the width under the pointer.
      if (raw < FOLD_AT) setOpen(side, false);
      else { setOpen(side, true); layout[side].width = Math.min(Math.max(raw, MIN), widest(side)); }
      apply();
    });
    function release(event) {
      if (event.pointerId !== pointer) return;
      pointer = null;
      // A drag that ends folded keeps the width the sidebar had before it, so
      // reopening gives back what the reader was using, not the last few
      // pixels it passed through on the way shut.
      if (!isOpen(side)) { layout[side].width = start; apply(); }
      handle.classList.remove('active');
      $('frame').classList.remove('dragging');
      document.body.classList.remove('resizing');
      persist();
    }
    handle.addEventListener('pointerup', release);
    handle.addEventListener('pointercancel', release);
    handle.addEventListener('dblclick', function () { toggle(side); });
    handle.addEventListener('keydown', function (event) {
      // Arrow keys move the edge the way the arrow points; Enter folds.
      var step = event.shiftKey ? 64 : 16, grow = side === 'left' ? 1 : -1;
      if (event.key === 'Enter' || event.key === ' ') toggle(side);
      else if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
        var delta = (event.key === 'ArrowRight' ? step : -step) * grow;
        if (!isOpen(side)) { if (delta > 0) setOpen(side, true); }
        else if (layout[side].width + delta < MIN) setOpen(side, false);
        else layout[side].width = Math.min(layout[side].width + delta, widest(side));
        apply(); persist();
      } else return;
      event.preventDefault();
    });
  }

  function foldable(panel) {
    var heading = panel.querySelector(':scope > h2');
    if (!panel.id || !heading) return;
    if (layout.folded[panel.id]) panel.dataset.folded = 'true';
    heading.setAttribute('role', 'button');
    heading.tabIndex = 0;
    function flip() {
      if (!FRAME.matches) return;
      var folded = panel.dataset.folded !== 'true';
      if (folded) { panel.dataset.folded = 'true'; layout.folded[panel.id] = true; }
      else { delete panel.dataset.folded; delete layout.folded[panel.id]; }
      heading.setAttribute('aria-expanded', String(!folded));
      persist();
    }
    heading.setAttribute('aria-expanded', String(panel.dataset.folded !== 'true'));
    heading.addEventListener('click', flip);
    heading.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); flip(); }
    });
  }

  // The stage shows one panel at a time: the model unless the reader picks
  // another. A document opened from the sidebar comes onto the stage, and
  // leaves it when the view changes and the page closes it.
  function stage() {
    var root = $('stage'), tabs = Array.from(root.querySelectorAll('[role="tab"]'));
    function show(name) {
      root.dataset.active = name;
      tabs.forEach(function (tab) { tab.setAttribute('aria-selected', String(tab.dataset.stage === name)); });
    }
    tabs.forEach(function (tab) { tab.addEventListener('click', function () { show(tab.dataset.stage); }); });
    var doc = $('doc-view');
    new MutationObserver(function () {
      var open = !doc.classList.contains('hidden');
      var wasOpen = !$('doc-tab').hidden;
      $('doc-tab').hidden = !open;
      if (open && !wasOpen) show('doc');
      if (!open && root.dataset.active === 'doc') show('model');
    }).observe(doc, { attributes: true, attributeFilter: ['class'] });
    $('doc-close').addEventListener('click', function () {
      doc.classList.add('hidden');
    });
    // Each tab says what is behind it without being opened: the training
    // state as a dot, the number of playable clips as a count.
    new MutationObserver(function () {
      var value = $('telemetry').dataset.state;
      if (value && value !== 'unselected') $('curves-dot').dataset.state = value;
      else delete $('curves-dot').dataset.state;
      $('curves-dot').title = value ? 'training telemetry: ' + value : '';
    }).observe($('telemetry'), { attributes: true, attributeFilter: ['data-state'] });
    new MutationObserver(function () {
      var clips = $('videos').querySelectorAll('li[data-video]').length;
      $('videos-count').textContent = clips ? String(clips) : '';
    }).observe($('videos'), { childList: true });
    return show;
  }

  function initialize() {
    apply();
    document.querySelectorAll('.resizer').forEach(dragHandle);
    document.querySelectorAll('.rail .panel').forEach(foldable);
    $('toggle-left').addEventListener('click', function () { toggle('left'); });
    $('toggle-right').addEventListener('click', function () { toggle('right'); });
    window.addEventListener('resize', apply);
    COMPACT.addEventListener('change', apply);
    // A tap on the model beside an open drawer closes it.
    document.querySelector('.scrim').addEventListener('click', function () {
      layout.drawer.left = layout.drawer.right = false; apply();
    });
    var show = stage();
    // The canvas follows its box, which a sidebar drag changes without any
    // window resize; redraw whenever the box does.
    if (window.ResizeObserver) {
      new ResizeObserver(function () {
        var viewer = window.cadexReview && window.cadexReview.viewer();
        if (viewer && viewer.draw) viewer.draw();
      }).observe($('viewer'));
    }
    window.cadexFrame = {
      layout: function () {
        return { left: { width: layout.left.width, open: layout.left.open }, right: { width: layout.right.width, open: layout.right.open },
                 drawers: COMPACT.matches ? { left: layout.drawer.left, right: layout.drawer.right } : null,
                 stage: $('stage').dataset.active };
      },
      toggle: toggle,
      show: show
    };
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize);
  else initialize();
})();
