// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The review page. Polls /api/project, lets the reader pick the accepted
// project or one recorded run, and shows exactly what the record says: a
// historical run is labelled as such and drawn from its own retained mesh,
// never from today's script. Nothing here writes anything anywhere.
(function () {
  'use strict';

  var POLL_MS = 2000;
  var state = { review: null, selected: 'accepted', lastOk: null, stale: false, model: null, viewer: null,
                error: null };
  var pendingPoll = null;
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
  function fmt(value) {
    if (value == null) return '—';
    if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toPrecision(5);
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  }

  function fetchJson(url) {
    return fetch(url, { cache: 'no-store' }).then(function (response) {
      if (!response.ok) throw new Error(url + ': HTTP ' + response.status);
      return response.json();
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

  function renderSidebar() {
    var list = $('views');
    clearChildren(list);
    var accepted = state.review.accepted;
    list.appendChild(el('li', { 'data-view': 'accepted', 'data-selected': String(state.selected === 'accepted'), onclick: function () { select('accepted'); } }, [
      el('div', { className: 'name', text: 'Accepted now' }),
      el('div', { className: 'muted small', text: accepted.available ? short(accepted.revision) : 'nothing accepted' })
    ]));
    state.review.runs.forEach(function (run) {
      list.appendChild(el('li', { 'data-view': 'run', 'data-run': run.run, 'data-relation': run.relation, 'data-status': run.status,
                                  'data-selected': String(state.selected === run.run), onclick: function () { select(run.run); } }, [
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
    if (run.status === 'running') note += (note ? ' · ' : '') + 'if no walk is running, this run was interrupted: start a new `cadex walk --out runs/<new-name>`';
    if (run.status === 'unrecorded') note += (note ? ' · ' : '') + 'recorded before run records existed: identity from review.json only';
    text('view-note', note || '—');
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

  function renderTelemetry(run) {
    var panel = $('telemetry');
    clearChildren(panel);
    var data = run ? (run.telemetry || {state: 'missing'}) : {state: 'unselected'};
    panel.dataset.state = data.state;
    panel.appendChild(el('p', {text: 'Training telemetry: ' + data.state + (data.reason ? ' — ' + data.reason : '')}));
    if (!run) return;
    if (['missing', 'invalid', 'stale', 'failed', 'unknown'].includes(data.state)) {
      panel.appendChild(el('p', {text: 'Inspect the CLI training output; if the run stopped, start a new cadex walk --out runs/<new-name>. Stale data does not prove interruption.'}));
    }
    ['iteration', 'total', 'reward_per_step', 'loss', 'episode_steps'].forEach(function (key) {
      panel.appendChild(el('div', {'data-metric': key, text: key + ': ' + fmt(data[key])}));
    });
    [['curve', 'Reward per step'], ['loss_curve', 'Loss'], ['episode_steps_curve', 'Episode length (steps)']].forEach(function (item) {
      var points = data[item[0]] || [], block = el('div', {'data-history': item[0], 'data-points': String(points.length)});
      block.appendChild(el('p', {text: item[1] + (points.length ? ' · ' + points.length + ' retained samples' : ' — history missing')}));
      if (points.length) {
        var xs = points.map(function (p) {return p[0];}), ys = points.map(function (p) {return p[1];});
        var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs), y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
        var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('viewBox', '0 0 400 100'); svg.style.width = '100%'; svg.style.maxWidth = '600px';
        svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', item[1] + ' by iteration');
        var line = document.createElementNS(svg.namespaceURI, 'polyline');
        line.setAttribute('points', points.map(function (p) {return (5 + 390 * (p[0]-x0)/(x1-x0 || 1)) + ',' + (95 - 90 * (p[1]-y0)/(y1-y0 || 1));}).join(' '));
        line.setAttribute('fill', 'none'); line.setAttribute('stroke', '#4da6ff'); line.setAttribute('stroke-width', '2');
        svg.appendChild(line); block.appendChild(svg);
        block.appendChild(el('small', {text: 'iterations ' + x0 + '–' + x1 + ' · range ' + fmt(y0) + '–' + fmt(y1)}));
      }
      panel.appendChild(block);
    });
    var checkpoints = el('ul', {id: 'checkpoints'});
    (data.checkpoints || []).forEach(function (item) {
      checkpoints.appendChild(el('li', {'data-status': item.status, text: item.path + ' · iteration ' + fmt(item.iteration) + ' · ' + item.status + ' · sha256 ' + item.sha256}));
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

  function renderArtifacts() {
    var run = selectedRun();
    var problems = $('problems'), body = $('artifacts').querySelector('tbody'), videos = $('videos');
    clearChildren(problems); clearChildren(body);
    if (!run) { clearChildren(videos); delete videos.dataset.key; body.appendChild(el('tr', {}, [el('td', { text: 'select a run to see its retained artifacts' }), el('td'), el('td')])); return; }
    (run.problems || []).forEach(function (problem) { problems.appendChild(el('li', { text: problem })); });
    var resolved = run.resolved || { artifacts: {}, project_artifacts: {}, videos: [] };
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
        body.appendChild(el('tr', { 'data-group': group, 'data-key': key }, [el('td', { text: group + '.' + key }), el('td', { className: 'mono', text: item.path == null ? '—' : item.path }), cell]));
      });
    }
    rows('artifacts', '/artifact/run/');
    rows('project_artifacts', '/artifact/project/');
    var videoKey = JSON.stringify([run.run, run.videos, resolved.videos, run.video_render]);
    if (videos.dataset.key === videoKey) return;
    videos.dataset.key = videoKey;
    clearChildren(videos);
    if (run.video_render) videos.appendChild(el('li', {text: 'Video render: ' + run.video_render.state + (run.video_render.error ? ' — ' + run.video_render.error + '. Retry the CLI video command after fixing the retained inputs or encoder.' : '')}));
    var recorded = run.videos || [];
    if (!recorded.length) videos.appendChild(el('li', { className: 'muted', text: 'videos: none recorded for this run' }));
    recorded.forEach(function (video, index) {
      var item = (resolved.videos || [])[index] || {};
      var line = el('li', { 'data-video': String(index) });
      var label = 'video ' + index + ' · ' + (video.path || '?') + ' · revision ' + short(video.accepted_revision || (run.model || {}).accepted_revision) + ' · policy ' + short(video.policy_sha256) + ' · seed ' + fmt(video.seed) + ' · ' + fmt(video.sim_seconds) + ' s';
      if (item.exists && !item.error) {
        var url = '/video/run/' + encodeURIComponent(run.run) + '/' + index;
        line.appendChild(el('div', { text: label }));
        line.appendChild(el('video', { controls: true, preload: 'metadata', src: url, width: 480 }));
        line.appendChild(el('a', { href: url + '?download=1', text: 'download' }));
      } else {
        line.appendChild(el('span', { className: 'status-missing', text: label + ' — ' + (item.error ? 'refused: ' + item.error : 'missing') + '. Retry the CLI video command after restoring the retained inputs.' }));
      }
      videos.appendChild(line);
    });
  }

  function showDoc(url, title) {
    var view = $('doc-view');
    view.classList.remove('hidden');
    view.textContent = 'loading ' + title + '…';
    fetch(url, { cache: 'no-store' }).then(function (response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.text();
    }).then(function (body) { view.textContent = '# ' + title + '\n\n' + body; })
      .catch(function (error) { view.textContent = title + ': ' + error.message; });
  }

  function renderDocs() {
    var run = selectedRun(), docs = $('docs'), decisions = $('decisions');
    clearChildren(docs); clearChildren(decisions);
    $('doc-view').classList.add('hidden');
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
    renderHeader(); renderSidebar(); renderIdentity(); renderParams(); renderTraining(); renderArtifacts(); renderDocs();
  }

  function select(view) {
    state.selected = view;
    render();
    return loadModel();
  }

  function poll() {
    if (pendingPoll) return pendingPoll;
    pendingPoll = fetchJson('/api/project').then(function (review) {
      var first = !state.review;
      state.review = review; state.lastOk = new Date(); state.stale = false; state.error = null;
      render();
      if (first) return loadModel();
    }).catch(function (error) {
      state.stale = true; state.error = error.message;
      renderFreshness();
    }).finally(function () { pendingPoll = null; });
    return pendingPoll;
  }

  document.addEventListener('DOMContentLoaded', function () {
    state.viewer = window.CadexViewer.create($('viewer'));
    $('model-fit').addEventListener('click', function () { state.viewer.fit(); });
    poll().then(function () { readyResolve(true); });
    setInterval(poll, POLL_MS);
  });

  window.cadexReview = {
    ready: ready,
    select: select,
    refresh: poll,
    viewer: function () { return state.viewer; },
    state: function () {
      var run = selectedRun();
      return { selected: state.selected, stale: state.stale, error: state.error,
               revision: run ? (run.model || {}).accepted_revision : (state.review && state.review.accepted.revision),
               relation: run ? run.relation : 'accepted', model: state.model && { available: state.model.available, reason: state.model.reason, revision: state.model.revision },
               runs: state.review ? state.review.runs.map(function (r) { return r.run; }) : [] };
    }
  };
})();
