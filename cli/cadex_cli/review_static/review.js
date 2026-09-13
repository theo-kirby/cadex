// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The review page. Polls /api/project for the run list (each run's telemetry
// as a bounded summary) and /api/run/<selected> for the one run whose
// histories and verified checkpoints are on screen (ADR-321); lets the reader
// pick the accepted project or one recorded run, and shows exactly what the
// record says: a historical run is labelled as such and drawn from its own
// retained mesh, never from today's script. Nothing here writes anything
// anywhere. Poll work is bounded: the run list is rebuilt only when it
// changes, and the telemetry panel only when the selected run's telemetry
// does, so an idle poll over a long history touches a constant number of
// nodes.
(function () {
  'use strict';

  var POLL_MS = 2000;
  var state = { review: null, selected: 'accepted', lastOk: null, stale: false, model: null, viewer: null,
                error: null, following: true, docKey: null, docRequest: 0, detail: null };
  var pendingPoll = null;
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
    // The phone's disclosure line (REVIEW-DESIGN.md §6): what is current and
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
    fetchJson('/api/policy-origin/' + encodeURIComponent(run.run)).then(function (data) {
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

  function renderIdentity() {
    var accepted = state.review.accepted, run = selectedRun();
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
    var body = $('params').querySelector('tbody');
    clearChildren(body);
    names.sort().forEach(function (name) {
      var spec = byName[name] || {};
      body.appendChild(el('tr', { 'data-param': name }, [
        el('td', { text: name }), el('td', { text: fmt(values[name]) }), el('td', { text: fmt(spec.default) }),
        el('td', { text: fmt(spec.min) }), el('td', { text: fmt(spec.max) }), el('td', { text: fmt(spec.unit) }),
        el('td', { text: fmt(spec.label) })
      ]));
    });
    text('params-note', Array.isArray(specs)
      ? 'specs from ' + source + (names.length ? '' : ' (no parameters declared)')
      : 'specs unavailable' + (source ? ': ' + source : '') + (names.length ? ' — values only' : ''));
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
    rows('artifacts', '/artifact/run/');
    rows('project_artifacts', '/artifact/project/');
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
      var label = 'video ' + index + ' · ' + (video.path || '?') + ' · revision ' + short(video.accepted_revision || (run.model || {}).accepted_revision) + ' · policy ' + short(video.policy_sha256) + ' · seed ' + fmt(video.seed) + ' · ' + fmt(video.sim_seconds) + ' s · ' + (video.style || 'historical legacy style');
      if (item.exists && !item.error) {
        var url = '/video/run/' + encodeURIComponent(run.run) + '/' + index;
        var player = el('video', { controls: true, preload: 'metadata', src: url });
        // A play control of the page's own, sized for a finger (REVIEW-DESIGN.md
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
        docs.appendChild(el('li', { 'data-doc': name }, [el('a', { href: '#', text: name, onclick: function (event) { event.preventDefault(); showDoc('/doc/current/' + name, name); } })]));
      });
      (review.decisions || []).forEach(function (heading) { decisions.appendChild(el('li', { 'data-decision': heading, text: heading })); });
      if (!(review.decisions || []).length) decisions.appendChild(el('li', { className: 'muted', text: 'no decisions recorded' }));
      return;
    }
    var snapshot = run.project_docs || {};
    var files = Object.keys(snapshot.files || {}).sort();
    text('docs-note', files.length ? 'snapshot taken when this run was recorded — ' + (snapshot.note || '') : 'no document snapshot for this run (' + (snapshot.note || 'none') + ')');
    files.forEach(function (name) {
      docs.appendChild(el('li', { 'data-doc': name }, [el('a', { href: '#', text: name, onclick: function (event) { event.preventDefault(); showDoc('/doc/run/' + encodeURIComponent(run.run) + '/' + name, name + ' (snapshot)'); } })]));
    });
    (snapshot.skipped || []).forEach(function (item) { docs.appendChild(el('li', { className: 'status-missing', text: item.path + ': skipped (' + item.reason + ')' })); });
    decisions.appendChild(el('li', { className: 'muted', text: 'decisions as of this run are in the DECISIONS.md snapshot above' }));
  }

  function renderModelComponents(manifest, loaded) {
    var list = $('model-components');
    clearChildren(list);
    (manifest.components || []).forEach(function (component, index) {
      var mesh = loaded.filter(function (entry) { return entry.name === component.name; })[0];
      var line = el('li', { 'data-component': component.name, 'data-mesh': component.mesh_status });
      if (mesh) { var swatch = el('span', { className: 'swatch' }); swatch.style.background = 'rgb(' + mesh.color.join(',') + ')'; line.appendChild(swatch); }
      line.appendChild(document.createTextNode(component.name + (component.output && component.output !== component.name ? ' ← ' + component.output : '') +
        ' · mesh ' + component.mesh_status + (mesh ? ' (' + mesh.triangles + ' triangles)' : '') + ' · placement: ' + component.placement_source));
      list.appendChild(line);
    });
  }

  function loadModel() {
    var run = selectedRun();
    var url = run ? '/api/model/run/' + encodeURIComponent(run.run) : '/api/model/accepted';
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
        return;
      }
      if (!state.viewer.available) {
        status.dataset.state = 'error';
        status.textContent = 'WebGL unavailable in this browser; the model is listed but not drawn';
        renderModelComponents(manifest, []);
        return;
      }
      return state.viewer.load(manifest).then(function (loaded) {
        if (token !== state.selected) return;
        var stats = state.viewer.stats();
        status.dataset.state = 'loaded';
        status.textContent = (run ? (run.relation === 'historical' ? 'HISTORICAL model ' : 'model ') + 'of run ' + run.run : 'accepted model') +
          ' at revision ' + short(manifest.revision) + ' · ' + stats.components + ' component(s), ' + stats.triangles + ' triangles · from ' + manifest.source +
          ' · placements: ' + manifest.placement_source;
        renderModelComponents(manifest, loaded);
      });
    }).catch(function (error) {
      status.dataset.state = 'error';
      status.textContent = 'model failed to load: ' + error.message;
    });
  }

  function render() {
    renderFreshness();
    if (!state.review) return;
    if (state.selected !== 'accepted' && !selectedRun()) state.selected = 'accepted';
    renderHeader(); renderSidebar(); renderIdentity(); renderPolicyOrigin(); renderParams(); renderTraining(); renderArtifacts(); renderDocs();
  }

  function loadDetail() {
    // One run's histories and verified checkpoints, for the selected run only.
    var run = selectedRun(), request = ++detailRequest;
    if (!run) { state.detail = null; lastPoll.detail_bytes = 0; return Promise.resolve(); }
    return fetchJson('/api/run/' + encodeURIComponent(run.run), 'detail_bytes').then(function (detail) {
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
    pendingPoll = fetchJson('/api/project', 'project_bytes').then(function (review) {
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
    $('current-run').addEventListener('click', function () {
      if (!state.review) return;
      select(currentView());
      state.following = true;
    });
    $('model-fit').addEventListener('click', function () { state.viewer.fit(); });
    // The run list is a sidebar at desk and a closed disclosure on a phone
    // (REVIEW-DESIGN.md §6); crossing the breakpoint resets it, a tap on the
    // summary toggles it. Only the media query decides, never the run count.
    var phone = window.matchMedia('(max-width: 599px)');
    function foldRuns() { $('runs').open = !phone.matches; }
    foldRuns();
    phone.addEventListener('change', foldRuns);
    poll().then(function () { readyResolve(true); });
    setInterval(poll, POLL_MS);
  }

  window.cadexReview = {
    ready: ready,
    select: select,
    refresh: poll,
    viewer: function () { return state.viewer; },
    lastPoll: function () { return { project_bytes: lastPoll.project_bytes, detail_bytes: lastPoll.detail_bytes, ms: lastPoll.ms }; },
    state: function () {
      var run = selectedRun();
      return { selected: state.selected, stale: state.stale, error: state.error,
               detail: state.detail ? state.detail.run : null,
               disk: state.detail && state.detail.disk ? { state: state.detail.disk.state, bytes: state.detail.disk.bytes, files: state.detail.disk.files, shared_bytes: state.detail.disk.shared_bytes } : null,
               revision: run ? (run.model || {}).accepted_revision : (state.review && state.review.accepted.revision),
               relation: run ? run.relation : 'accepted', model: state.model && { available: state.model.available, reason: state.model.reason, revision: state.model.revision },
               runs: state.review ? state.review.runs.map(function (r) { return r.run; }) : [] };
    }
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize);
  else initialize();
})();
