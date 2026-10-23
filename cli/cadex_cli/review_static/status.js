// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The Status editor (ADR-542; an editor since ADR-572; redrawn by ADR-606):
// what the project is doing and what the agent last did. And the Training
// editor (ADR-732), from the same poll: how the run Status reads is training
// -- reward, loss, episode length and action std, each on its own axes, the
// best iteration and the checkpoints marked -- the latest evaluation
// predicate by predicate, and every run with its outcome, its evaluation and
// how its best moved against the run before.
//
// Project (ADR-607): a project whose agent wrote `status.html` shows it in
// Status, under the stage and the activity, in a
// sandboxed iframe with an opaque origin that can fetch nothing; this page
// posts it the project's data, a `cadex-status-panel-v1` message, on every
// poll (docs/DASHBOARD.md, "The agent's Status panel").
//
// review.js calls CadexStatus.render(review) on each poll. Everything is
// drawn only when what it shows changed, so an idle poll adds no nodes.
(function () {
  'use strict';

  var STAGE_LABELS = { idle: 'idle', designing: 'designing', training: 'training', evaluating: 'evaluating', stopped: 'stopped', failed: 'failed' };
  var ACTIVITY_IDLE_S = 300, ACTIVITY_LIST = 5;
  var PANEL_SCHEMA = 'cadex-status-panel-v1';
  // The run detail (its full histories) is read for the panel at most this often.
  var PANEL_DETAIL_MS = 10000;
  var RUNS_LISTED = 40;
  var CHARTS = [
    { id: 'training-reward', key: 'curve', label: 'reward per step', marks: true },
    { id: 'training-loss', key: 'loss_curve', label: 'loss' },
    { id: 'training-episode', key: 'episode_steps_curve', label: 'episode length' },
    { id: 'training-std', key: 'action_std_curve', label: 'action std' }
  ];
  var TOKENS = ['--bg', '--surface', '--surface-2', '--surface-3', '--rule', '--rule-strong', '--ink', '--ink-2', '--accent',
                '--ok', '--warn', '--bad', '--info', '--select', '--font', '--mono', '--fs-0', '--fs-1', '--fs-2', '--fs-3'];
  var NS = 'http://www.w3.org/2000/svg';
  var review = null, activityKey = null, runsKey = null, evalKey = null, chartKeys = {};
  // The run the Training editor reads (ADR-790): the one picked as the 3D viewport's source, else
  // the stage's. A picked run that is not the stage's is read whole from api/run, again only
  // when its record moves.
  var picked = { run: null, key: null, t: null };
  var evalDetail = { name: null, stamp: null, summary: null };
  var panel = { url: null, frame: null, detail: null, detailKey: null, detailAt: 0, message: null, posted: 0 };

  function $(id) { return document.getElementById(id); }
  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (key) {
      if (key === 'text') node.textContent = attrs[key];
      else if (key === 'class') node.className = attrs[key];
      else if (key.indexOf('data-') === 0) node.setAttribute(key, attrs[key]);
      else node[key] = attrs[key];
    });
    (children || []).forEach(function (child) { if (child) node.appendChild(typeof child === 'string' ? document.createTextNode(child) : child); });
    return node;
  }
  function svg(tag, attrs, text) {
    var n = document.createElementNS(NS, tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (text != null) n.textContent = text;
    return n;
  }
  function setText(id, value) { var node = $(id); if (node.textContent !== value) node.textContent = value; return node; }
  function setHidden(id, hidden) { var node = $(id); if (node.hidden !== hidden) node.hidden = hidden; return node; }
  function fmt(value) {
    if (value == null || (typeof value === 'number' && !isFinite(value))) return '—';
    if (typeof value === 'number') return Number.isInteger(value) ? String(value) : String(Number(value.toPrecision(4)));
    return String(value);
  }
  function signed(value) { return value == null ? '' : (value > 0 ? '+' : value < 0 ? '−' : '±') + tickText(Math.abs(Number(value.toPrecision(3)))); }
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
  // This browser's arrangement of the Training cards; a browser that refuses storage gets the default.
  function readStored(key) { try { return localStorage.getItem(key); } catch (_) { return null; } }
  function writeStored(key, value) { try { localStorage.setItem(key, value); } catch (_) { /* this visit only */ } }
  function json(url) {
    return fetch(url, { cache: 'no-store' }).then(function (response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.json();
    });
  }

  // A run's full telemetry in the stage's shape: its curves as the charts' sparks, and the
  // reward chart's marks where its checkpoints were written.
  function pickedTelemetry(full) {
    var t = {}, reward = {};
    Object.keys(full).forEach(function (k) {
      if (k !== 'curve' && k !== 'checkpoints' && k !== 'checkpoint_source' && !/_curve$/.test(k)) t[k] = full[k];
    });
    t.spark = {};
    CHARTS.forEach(function (c) { t.spark[c.key] = full[c.key] || []; });
    (full.curve || []).forEach(function (p) { if (Array.isArray(p)) reward[p[0]] = p[1]; });
    t.marks = (full.checkpoints || []).filter(function (c) { return typeof c.iteration === 'number'; })
      .map(function (c) { return [c.iteration, reward[c.iteration] == null ? null : reward[c.iteration]]; });
    return t;
  }
  function refreshPicked() {
    var stage = review.stage || {};
    if (!picked.run || picked.run === stage.run) return;
    var name = picked.run, run = (review.runs || []).filter(function (r) { return r.run === name; })[0];
    if (!run) { picked = { run: null, key: null, t: null }; return; }
    var tel = run.telemetry || {}, key = JSON.stringify([name, run.status, tel.iteration, tel.state]);
    if (key === picked.key) return;
    picked.key = key;
    json('api/run/' + encodeURIComponent(name)).then(function (record) {
      if (picked.run !== name) return;
      var full = record.telemetry || {};
      picked.t = full.state && full.state !== 'missing' ? pickedTelemetry(full) : null;
      chartKeys = {};
      if (review) render(review);
    }).catch(function () { if (picked.run === name) picked.key = null; });
  }
  // What the Training editor shows: the stage's run and its telemetry, or the picked one's.
  function shown() {
    var stage = (review && review.stage) || {};
    if (!picked.run || picked.run === stage.run) return { run: stage.run, t: stage.training || null, own: true };
    return { run: picked.run, t: picked.t, own: false };
  }

  // -- the head: stage, line, run, activity, warning ------------------------------
  function renderHead(stage, t, now, view) {
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
    var bar = name === 'training' && t && t.total ? Math.max(0, Math.min(1, ((t.iteration || 0) + 1) / t.total)) : null;
    setHidden('status-progress', bar == null);
    if (bar != null) fillBar('status-progress', bar);
    renderTrainingHead(view.own ? name : 'idle', view.t, line);
    renderActivity(now);
    // The run it reads, named when there is more than one to choose from.
    setHidden('status-run', !(stage.run && stage.runs > 1));
    var run = stage.run ? 'run ' + stage.run + (t && name !== 'training' ? ' · ' + t.state : '') : '';
    setText('status-run', run);
    var trained = view.own ? run : 'run ' + view.run + (view.t ? ' · ' + view.t.state : ' · reading…');
    setText('training-run', trained || 'no runs').title = trained;
    var warning = t ? (t.warning || (t.state === 'stale' ? t.reason : '')) : '';
    setHidden('status-warning', !warning);
    setText('status-warning', warning);
  }

  function fillBar(id, share) {
    var width = (share * 100).toFixed(1) + '%', fill = $(id).firstElementChild;
    if (fill.style.width !== width) fill.style.width = width;
  }
  // Training's own head (ADR-770): Status's line and bar while the run trains; once it has ended,
  // how far it got and how it ended, on a bar that no longer moves.
  function renderTrainingHead(name, t, line) {
    setHidden('training-head', !t);
    if (!t) return;
    var live = name === 'training', reached = t.iteration != null && t.iteration >= 0;
    var text = live ? line : (reached ? 'iteration ' + (t.iteration + 1) + (t.total ? ' / ' + fmt(t.total) : '') : 'no iteration reported') + (t.state ? ' · ' + t.state : '');
    setText('training-line', text).title = text;
    var share = t.total ? Math.max(0, Math.min(1, ((reached ? t.iteration : -1) + 1) / t.total)) : null;
    setHidden('training-progress', share == null);
    if (share == null) return;
    fillBar('training-progress', share);
    if ($('training-progress').dataset.live !== String(live)) $('training-progress').dataset.live = String(live);
  }

  // The agent's newest call through cadex mcp (ADR-550), timed against the server's
  // clock. A call still running is logged as such (ADR-553) and is never idle; past
  // ACTIVITY_IDLE_S with no call in flight, the line reads as idle.
  function activityText(e) {
    return e.tool + (e.args ? ' ' + e.args : '')
      + (e.outcome === 'error' ? ' · failed' + (e.detail ? ': ' + e.detail : '')
         : e.outcome === 'lost' ? ' · did not return' : e.outcome === 'running' ? ' · running' : '');
  }
  function renderActivity(now) {
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

  // -- the numbers and the charts ---------------------------------------------
  function renderStats(t, name) {
    setHidden('training-board', !t);
    if (!t) return;
    setText('training-reward-now', fmt(t.reward_per_step));
    setText('training-best', t.best_reward_per_step == null ? '—' : fmt(t.best_reward_per_step) + ' @ ' + (t.best_iteration + 1));
    setText('training-loss-now', fmt(t.loss));
    setText('training-episode-now', fmt(t.episode_steps));
    setText('training-std-now', fmt(t.action_std));
    setText('training-eta', name === 'training' && t.eta_s ? duration(t.eta_s) : '—');
    setHidden('training-eta-tile', name !== 'training');
  }

  function ticks(lo, hi, want) {
    var span = hi - lo;
    if (!(span > 0)) return [lo];
    var step = Math.pow(10, Math.floor(Math.log10(span / want))), err = span / want / step;
    step *= err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1;
    var out = [];
    for (var v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) out.push(Number(v.toPrecision(12)));
    return out;
  }
  function tickText(v) {
    var a = Math.abs(v);
    if (a >= 1e4 || (a > 0 && a < 1e-3)) return Number(v.toPrecision(3)).toExponential().replace('e+', 'e');
    return String(Number(v.toPrecision(4)));
  }

  // One measure on its own axes: y ticks and grid, x ticks in iterations (one-based,
  // as Status counts), the line, and for reward the best iteration and the checkpoints.
  // A centred mean over ``half`` samples either side, shrinking at the ends
  // so the first and last points stay where the run was.
  function rollingMean(points, half) {
    if (half < 1 || points.length < 3) return points;
    return points.map(function (p, i) {
      var k = Math.min(half, i, points.length - 1 - i), sum = 0;
      for (var j = i - k; j <= i + k; j++) sum += points[j][1];
      return [p[0], sum / (2 * k + 1)];
    });
  }

  // Drawn at its card's size (ADR-770): the width the grid gives it, the height it was resized to,
  // or the whole editor while maximized.
  function drawChart(spec, points, t) {
    var node = $(spec.id), box = node.getBoundingClientRect(), width = Math.round(box.width), height = Math.round(box.height);
    var marks = spec.marks ? (t.marks || []) : [];
    var key = JSON.stringify([width, height, points, spec.marks ? [t.best_iteration, t.best_reward_per_step, marks] : 0, t.total, (review.stage || {}).state]);
    if (chartKeys[spec.id] === key) return;
    chartKeys[spec.id] = key;
    while (node.firstChild) node.removeChild(node.firstChild);
    node.setAttribute('viewBox', '0 0 ' + Math.max(width, 1) + ' ' + Math.max(height, 1));
    var figure = node.closest('figure');
    figure.dataset.empty = points.length > 1 ? 'false' : 'true';
    if (!width || height < 40) return;
    if (points.length < 2) {
      node.appendChild(svg('text', { x: width / 2, y: height / 2, class: 'chart-empty', 'text-anchor': 'middle' },
                           points.length ? 'one sample so far' : 'not reported by this run'));
      return;
    }
    var L = 46, R = 10, T = 8, B = 20;
    var xs = points.map(function (p) { return p[0]; }), ys = points.map(function (p) { return p[1]; });
    // While the run trains, the axis runs to its total so the unrun part
    // shows; once it has ended, to the last iteration it reached.
    var live = (review.stage || {}).state === 'training' && shown().own;
    var x0 = 0, x1 = Math.max(Math.max.apply(null, xs), live ? (t.total || 0) - 1 : 0, 1);
    var y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
    if (y1 === y0) { y0 -= Math.abs(y0) * 0.1 || 1; y1 += Math.abs(y1) * 0.1 || 1; }
    var pad = (y1 - y0) * 0.08; y0 -= pad; y1 += pad;
    var sx = function (x) { return L + (x - x0) / (x1 - x0) * (width - L - R); };
    var sy = function (y) { return height - B - (y - y0) / (y1 - y0) * (height - T - B); };
    var grid = svg('g', { class: 'chart-grid' }), labels = svg('g', { class: 'chart-label' });
    ticks(y0, y1, Math.max(2, Math.min(8, Math.round((height - T - B) / 28)))).forEach(function (y) {
      grid.appendChild(svg('line', { x1: L, x2: width - R, y1: sy(y).toFixed(1), y2: sy(y).toFixed(1) }));
      labels.appendChild(svg('text', { x: L - 6, y: sy(y).toFixed(1), 'text-anchor': 'end', 'dominant-baseline': 'middle' }, tickText(y)));
    });
    ticks(x0 + 1, x1 + 1, Math.max(2, Math.round((width - L - R) / 70))).forEach(function (x) {
      labels.appendChild(svg('text', { x: sx(x - 1).toFixed(1), y: height - 5, 'text-anchor': 'middle' }, tickText(x)));
    });
    node.appendChild(grid);
    node.appendChild(svg('line', { class: 'chart-axis', x1: L, x2: width - R, y1: height - B, y2: height - B }));
    node.appendChild(labels);
    marks.forEach(function (m) {
      if (m[0] < x0 || m[0] > x1) return;
      node.appendChild(svg('line', { class: 'chart-checkpoint', x1: sx(m[0]).toFixed(1), x2: sx(m[0]).toFixed(1),
                                     y1: height - B, y2: height - B - 5 }));
    });
    // The samples as they are, faint, and their rolling mean as the line:
    // a batch of episodes that end together swings the raw series between
    // two levels, and the trend is what the reader needs to follow.
    var line = function (series) { return series.map(function (p) {
      return sx(p[0]).toFixed(1) + ',' + sy(p[1]).toFixed(1); }).join(' '); };
    var smooth = rollingMean(points, Math.max(1, Math.round(points.length / 24)));
    node.appendChild(svg('polyline', { class: 'chart-raw', points: line(points) }));
    node.appendChild(svg('polyline', { class: 'chart-line', points: line(smooth) }));
    if (spec.marks && t.best_iteration != null && t.best_iteration >= 0 && t.best_reward_per_step != null) {
      var bx = sx(t.best_iteration), by = sy(t.best_reward_per_step);
      node.appendChild(svg('line', { class: 'chart-best-rule', x1: bx.toFixed(1), x2: bx.toFixed(1), y1: T, y2: height - B }));
      node.appendChild(svg('circle', { class: 'chart-best', cx: bx.toFixed(1), cy: by.toFixed(1), r: 4 }));
      var right = bx > width - 90;
      node.appendChild(svg('text', { class: 'chart-best-label', x: (bx + (right ? -7 : 7)).toFixed(1), y: Math.max(T + 9, by - 6).toFixed(1),
                                     'text-anchor': right ? 'end' : 'start' }, 'best ' + tickText(t.best_reward_per_step) + ' @ ' + (t.best_iteration + 1)));
    }
    // Hover: a crosshair on the nearest sample, its iteration and value.
    var hover = svg('g', { class: 'chart-hover', visibility: 'hidden' });
    var rule = svg('line', { y1: T, y2: height - B }), dot = svg('circle', { r: 3.5 }), tip = svg('text', { y: T + 10 });
    hover.appendChild(rule); hover.appendChild(dot); hover.appendChild(tip);
    node.appendChild(hover);
    node.onpointermove = function (event) {
      var box = node.getBoundingClientRect(), x = (event.clientX - box.left) * (width / box.width);
      var at = x0 + (x - L) / (width - L - R) * (x1 - x0), best = points[0];
      points.forEach(function (p) { if (Math.abs(p[0] - at) < Math.abs(best[0] - at)) best = p; });
      var px = sx(best[0]), py = sy(best[1]), right = px > width / 2;
      rule.setAttribute('x1', px); rule.setAttribute('x2', px);
      dot.setAttribute('cx', px); dot.setAttribute('cy', py);
      tip.setAttribute('x', right ? px - 6 : px + 6);
      tip.setAttribute('text-anchor', right ? 'end' : 'start');
      tip.textContent = 'iteration ' + (best[0] + 1) + ' · ' + tickText(best[1]);
      hover.setAttribute('visibility', 'visible');
    };
    node.onpointerleave = function () { hover.setAttribute('visibility', 'hidden'); };
  }

  function renderCharts(t) {
    if (!t) return;
    var spark = t.spark || {};
    CHARTS.forEach(function (spec) {
      var points = (spark[spec.key] || []).filter(function (p) { return Array.isArray(p) && isFinite(p[0]) && isFinite(p[1]); });
      drawChart(spec, points, t);
    });
  }

  // -- the cards: arranged by hand, kept by this browser (ADR-770) ----------------------
  // Every stat and chart is a card on one grid of narrow columns: dragged by its title to a new
  // place (onto the pinned strip, which stays at the top of the editor while the rest scrolls, to
  // pin it), resized from its corner in whole columns and in pixels of height, hidden from its
  // corner and shown again from the header's Cards menu; a chart maximizes to fill the editor.
  var CARD_COL = 104, CARD_GAP = 8, CARD_DRAG_PX = 5;
  var CARD_SIZES = { stat: { span: 1, h: 64, min: 48 }, chart: { span: 3, h: 132, min: 80 } };
  var CARD_ICONS = {
    pin: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6 2.5h4M7 2.5v4L4.5 9h7L9 6.5v-4M8 9v4.5"/></svg>',
    hide: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8"/></svg>',
    max: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 6V2h4M10 2h4v4M14 10v4h-4M6 14H2v-4"/></svg>'
  };
  var board = { order: [], pinned: {}, hidden: {}, size: {}, max: null };

  function cards() { return Array.prototype.slice.call(document.querySelectorAll('#training-board .card[data-card]')); }
  function card(id) { return document.querySelector('#training-board .card[data-card="' + id + '"]'); }
  function kindOf(node) { return node.classList.contains('chart') ? 'chart' : 'stat'; }
  function cardTitle(node) { return node.querySelector('.card-title').textContent; }
  function sizeOf(node) {
    var kept = board.size[node.dataset.card], own = CARD_SIZES[kindOf(node)];
    return { span: kept ? kept[0] : own.span, h: kept ? kept[1] : own.h };
  }
  function loadBoard() {
    var defaults = cards().map(function (node) { return node.dataset.card; }), kept = null;
    try { kept = JSON.parse(readStored('cadex.training.cards') || 'null'); } catch (_) { kept = null; }
    kept = kept && typeof kept === 'object' ? kept : {};
    var order = (Array.isArray(kept.order) ? kept.order : []).filter(function (id) { return defaults.indexOf(id) >= 0; });
    defaults.forEach(function (id) { if (order.indexOf(id) < 0) order.push(id); });
    var flags = function (list) {
      var out = {};
      (Array.isArray(list) ? list : []).forEach(function (id) { if (defaults.indexOf(id) >= 0) out[id] = true; });
      return out;
    };
    var size = {};
    Object.keys(kept.size && typeof kept.size === 'object' ? kept.size : {}).forEach(function (id) {
      var s = kept.size[id];
      if (defaults.indexOf(id) >= 0 && Array.isArray(s) && s.every(function (v) { return typeof v === 'number' && isFinite(v) && v > 0; })) size[id] = [Math.round(s[0]), Math.round(s[1])];
    });
    board = { order: order, pinned: flags(kept.pinned), hidden: flags(kept.hidden), size: size, max: null };
  }
  function saveBoard() {
    writeStored('cadex.training.cards', JSON.stringify({ order: board.order, pinned: Object.keys(board.pinned), hidden: Object.keys(board.hidden), size: board.size }));
  }
  // The columns a grid has at its width, so a card never spans more than there are.
  function columns(grid) { return Math.max(1, Math.floor(((grid.clientWidth || $('training').clientWidth) + CARD_GAP) / (CARD_COL + CARD_GAP))); }
  function applySpans() {
    var cols = columns($('training-cards'));
    cards().forEach(function (node) {
      var s = sizeOf(node), span = 'span ' + Math.min(s.span, cols), h = s.h + 'px';
      if (node.style.gridColumn !== span) node.style.gridColumn = span;
      if (node.style.getPropertyValue('--h') !== h) node.style.setProperty('--h', h);
    });
  }
  function applyBoard() {
    var pinnedGrid = $('training-pinned'), mainGrid = $('training-cards'), shownPinned = 0;
    board.order.forEach(function (id) {
      var node = card(id); if (!node) return;
      (board.pinned[id] ? pinnedGrid : mainGrid).appendChild(node);
      var off = !!board.hidden[id];
      if ((node.dataset.off === 'true') !== off) node.dataset.off = String(off);
      if (board.pinned[id] && !off) shownPinned += 1;
      var pin = node.querySelector('.card-pin');
      if (pin) { pin.setAttribute('aria-pressed', String(!!board.pinned[id])); pin.title = board.pinned[id] ? 'Unpin' : 'Pin to the top'; pin.setAttribute('aria-label', pin.title); }
      var max = node.querySelector('.card-max');
      if (max) {
        var on = board.max === id;
        max.setAttribute('aria-pressed', String(on)); max.title = on ? 'Restore' : 'Maximize'; max.setAttribute('aria-label', max.title);
        if (on) node.dataset.max = 'true'; else delete node.dataset.max;
      }
    });
    pinnedGrid.dataset.empty = String(!shownPinned);
    if (board.max) $('training').dataset.max = board.max; else delete $('training').dataset.max;
    applySpans();
    renderCardsMenu();
    if (review) { chartKeys = {}; renderCharts(shown().t); }
  }
  function setCard(id, change) {
    if (!card(id)) return false;
    if ('pinned' in change) { if (change.pinned) board.pinned[id] = true; else delete board.pinned[id]; }
    if ('hidden' in change) { if (change.hidden) board.hidden[id] = true; else delete board.hidden[id]; if (change.hidden && board.max === id) board.max = null; }
    if ('size' in change) board.size[id] = [change.size.span, change.size.h];
    if ('max' in change) board.max = change.max ? id : (board.max === id ? null : board.max);
    // A card pinned or unpinned goes to the end of the other group.
    if ('pinned' in change) { board.order.splice(board.order.indexOf(id), 1); board.order.push(id); }
    saveBoard(); applyBoard();
    return true;
  }
  function resetBoard() {
    board = { order: cards().map(function (node) { return node.dataset.card; }), pinned: {}, hidden: {}, size: {}, max: null };
    board.order.sort(function (a, b) { return defaultOrder.indexOf(a) - defaultOrder.indexOf(b); });
    writeStored('cadex.training.cards', '{}');
    applyBoard();
  }
  function renderCardsMenu() {
    var list = $('training-cards-list');
    list.textContent = '';
    defaultOrder.forEach(function (id) {
      var node = card(id), box = el('input', { type: 'checkbox', checked: !board.hidden[id] });
      box.addEventListener('change', function () { setCard(id, { hidden: !box.checked }); });
      list.appendChild(el('li', {}, [el('label', {}, [box, ' ' + cardTitle(node)]),
                                      board.pinned[id] ? el('span', { class: 'muted small', text: 'pinned' }) : null]));
    });
    var hiddenCount = Object.keys(board.hidden).length;
    setText('training-cards-button', hiddenCount ? 'Cards · ' + hiddenCount + ' hidden' : 'Cards');
  }
  // Drag a card by its title: it moves among the others as the pointer goes, and lands where it is
  // let go; over the pinned strip it is pinned, over the rest unpinned.
  function dragCard(node, start) {
    var startX = start.clientX, startY = start.clientY, dragging = false;
    function moved(e) {
      if (!dragging) {
        if (Math.hypot(e.clientX - startX, e.clientY - startY) < CARD_DRAG_PX) return;
        dragging = true; node.dataset.dragging = 'true'; $('training-board').dataset.arranging = 'true';
      }
      e.preventDefault();
      var under = document.elementFromPoint(e.clientX, e.clientY), other = under && under.closest('#training-board .card');
      if (other && other !== node) {
        var r = other.getBoundingClientRect(), before = e.clientX < r.left + r.width / 2;
        other.parentNode.insertBefore(node, before ? other : other.nextSibling);
      } else if (!other) {
        var grid = under && under.closest('#training-board .card-grid');
        if (grid && node.parentNode !== grid) grid.appendChild(node);
      }
    }
    function lifted() {
      document.removeEventListener('pointermove', moved);
      document.removeEventListener('pointerup', lifted);
      document.removeEventListener('pointercancel', lifted);
      if (!dragging) return;
      delete node.dataset.dragging; delete $('training-board').dataset.arranging;
      var pinnedNow = {};
      $('training-pinned').querySelectorAll('.card[data-card]').forEach(function (n) { pinnedNow[n.dataset.card] = true; });
      board.order = cards().map(function (n) { return n.dataset.card; });
      board.pinned = pinnedNow;
      saveBoard(); applyBoard();
    }
    document.addEventListener('pointermove', moved);
    document.addEventListener('pointerup', lifted);
    document.addEventListener('pointercancel', lifted);
  }
  // Resize from the corner: across in whole columns, down in pixels.
  function resizeCard(node, start) {
    var grid = node.parentNode, cols = columns(grid), colW = (grid.clientWidth - CARD_GAP * (cols - 1)) / cols;
    var s = sizeOf(node), startW = node.getBoundingClientRect().width, min = CARD_SIZES[kindOf(node)].min;
    var startX = start.clientX, startY = start.clientY;
    node.dataset.resizing = 'true';
    function moved(e) {
      e.preventDefault();
      var span = Math.max(1, Math.min(cols, Math.round((startW + e.clientX - startX + CARD_GAP) / (colW + CARD_GAP))));
      var h = Math.max(min, Math.min(1200, Math.round(s.h + e.clientY - startY)));
      board.size[node.dataset.card] = [span, h];
      applySpans();
      if (review && kindOf(node) === 'chart') renderCharts(shown().t);
    }
    function lifted() {
      document.removeEventListener('pointermove', moved);
      document.removeEventListener('pointerup', lifted);
      document.removeEventListener('pointercancel', lifted);
      delete node.dataset.resizing;
      saveBoard();
    }
    document.addEventListener('pointermove', moved);
    document.addEventListener('pointerup', lifted);
    document.addEventListener('pointercancel', lifted);
  }
  function cardButton(name, title, onClick) {
    var b = el('button', { type: 'button', class: 'icon-button card-' + name, title: title });
    b.setAttribute('aria-label', title);
    b.innerHTML = CARD_ICONS[name];
    b.addEventListener('click', function (e) { e.stopPropagation(); onClick(); });
    return b;
  }
  var defaultOrder = [];
  function wireBoard() {
    defaultOrder = cards().map(function (node) { return node.dataset.card; });
    cards().forEach(function (node) {
      var id = node.dataset.card, tools = el('span', { class: 'card-tools' });
      // Focusable, so a tap on a card on a touch screen shows its tools (review.css).
      node.tabIndex = -1;
      tools.appendChild(cardButton('pin', 'Pin to the top', function () { setCard(id, { pinned: !board.pinned[id] }); }));
      if (kindOf(node) === 'chart') tools.appendChild(cardButton('max', 'Maximize', function () { setCard(id, { max: board.max !== id }); }));
      tools.appendChild(cardButton('hide', 'Hide', function () { setCard(id, { hidden: true }); }));
      node.appendChild(tools);
      var grip = el('span', { class: 'card-resize', title: 'Drag to resize' });
      node.appendChild(grip);
      node.querySelector('.card-title').title = 'Drag to move';
      node.querySelector('.card-title').addEventListener('pointerdown', function (e) {
        if (e.button !== 0 || board.max) return;
        e.preventDefault();
        dragCard(node, e);
      });
      grip.addEventListener('pointerdown', function (e) {
        if (e.button !== 0 || board.max) return;
        e.preventDefault(); e.stopPropagation();
        resizeCard(node, e);
      });
    });
    $('training-cards-reset').addEventListener('click', resetBoard);
    // The menu is a popover, over the area that would clip it, opened under its button.
    var menu = $('training-cards-menu');
    menu.addEventListener('toggle', function (e) {
      if (e.newState !== 'open') return;
      var r = $('training-cards-button').getBoundingClientRect(), w = menu.offsetWidth;
      menu.style.left = Math.max(8, Math.min(window.innerWidth - w - 8, r.left)) + 'px';
      menu.style.top = Math.min(window.innerHeight - menu.offsetHeight - 8, r.bottom + 4) + 'px';
    });
    // Escape restores a maximized chart.
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && board.max) { board.max = null; applyBoard(); } });
    loadBoard();
    applyBoard();
  }

  // -- the latest evaluation, predicate by predicate ---------------------------------
  function bound(p) {
    var unit = p.metric ? ' ' + p.metric : '';
    if (p.min != null && p.max != null) return fmt(p.min) + ' – ' + fmt(p.max) + unit;
    if (p.min != null) return '≥ ' + fmt(p.min) + unit;
    if (p.max != null) return '≤ ' + fmt(p.max) + unit;
    return p.metric || '';
  }
  function renderEvaluation(now) {
    var rows = review.evaluations || [], latest = rows[rows.length - 1];
    setHidden('training-eval', !latest);
    if (!latest) return;
    if (evalDetail.name !== latest.name || evalDetail.stamp !== latest.stamp) {
      evalDetail = { name: latest.name, stamp: latest.stamp, summary: null };
      json('api/evaluation/' + encodeURIComponent(latest.name)).then(function (detail) {
        if (evalDetail.name !== latest.name) return;
        evalDetail.summary = (detail.report || {}).summary || {};
        evalKey = null;
        renderEvaluation(Date.parse(review.served_at) || Date.now());
        postPanel();
      }).catch(function () { /* the failing list stands in */ });
    }
    var key = JSON.stringify([latest, !!evalDetail.summary, Math.round(now / 60000)]);
    if (key === evalKey) return;
    evalKey = key;
    var chip = $('training-eval-verdict');
    chip.textContent = latest.verdict + ' ' + latest.passed + '/' + latest.seeds;
    chip.dataset.tone = latest.verdict === 'pass' ? 'ok' : 'bad';
    var ends = Object.keys(latest.terminations || {}).map(function (k) { return k + ' ' + latest.terminations[k]; }).join(', ');
    $('training-eval-line').textContent = [latest.task_label || latest.task_output, latest.policy_output,
      ago(latest.evaluated_at, now), latest.relation === 'historical' ? 'an earlier revision' : '',
      ends ? 'episodes ended: ' + ends : ''].filter(Boolean).join(' · ');
    var body = $('training-eval-list').tBodies[0];
    body.textContent = '';
    var predicates = (evalDetail.summary || {}).predicates;
    if (Array.isArray(predicates)) {
      predicates.forEach(function (p) {
        var passed = Number(p.passed) || 0, seeds = latest.seeds || 0, share = seeds ? passed / seeds : 0;
        var meter = el('span', { class: 'meter' }, [el('span', {})]);
        meter.firstChild.style.width = (share * 100).toFixed(0) + '%';
        meter.dataset.tone = passed === seeds ? 'ok' : passed === 0 ? 'bad' : 'warn';
        var median = p.value && typeof p.value === 'object' ? p.value.median : p.value;
        body.appendChild(el('tr', { 'data-pass': String(passed === seeds) }, [
          el('td', { class: 'mono', text: p.id }), el('td', { class: 'muted', text: bound(p) }),
          el('td', {}, [meter, el('span', { class: 'meter-text', text: passed + '/' + seeds })]),
          el('td', { class: 'num', text: fmt(median) })]));
      });
    } else {
      (latest.failing || []).forEach(function (text) {
        body.appendChild(el('tr', { 'data-pass': 'false' }, [el('td', { class: 'mono', text: text, colSpan: 4 })]));
      });
    }
  }

  // -- every run: what it reached, how it ended, how its evaluation went --------------
  var OUTCOMES = { ok: ['done', 'ok'], failed: ['failed', 'bad'], stopped: ['stopped', 'warn'], running: ['running', 'info'],
                   pending: ['pending', 'info'] };
  function runEvaluations(runs, rows) {
    // A run's evaluation: one of its own policy's by digest, else the first made
    // after it ended and before the next run did.
    var found = {};
    runs.forEach(function (run, index) {
      var sha = (run.policy || {}).sha256, own = rows.filter(function (e) { return sha && e.policy_sha256 === sha; });
      if (!own.length) {
        var from = Date.parse(run.recorded_at), next = runs[index + 1] ? Date.parse(runs[index + 1].recorded_at) : Infinity;
        own = rows.filter(function (e) { var at = Date.parse(e.evaluated_at); return at >= from && at < next; });
      }
      if (own.length) found[run.run] = own[own.length - 1];
    });
    return found;
  }
  function compactRuns() {
    return (review.runs || []).map(function (run) {
      var t = run.telemetry || {}, requested = (run.training || {}).requested || {};
      return { run: run.run, status: run.status, outcome: run.outcome, mode: run.mode || null, recorded_at: run.recorded_at || null,
               label: t.label || '', reason: typeof requested.reason === 'string' ? requested.reason.slice(0, 600) : '',
               telemetry_state: t.state, iteration: t.iteration, total: t.total, reward_per_step: t.reward_per_step,
               best_reward_per_step: t.best_reward_per_step, best_iteration: t.best_iteration, wall_time_s: t.wall_time_s,
               policy_sha256: (run.policy || {}).sha256 || null };
    });
  }
  function renderRuns(now) {
    var runs = review.runs || [];
    setHidden('training-runs', !runs.length);
    var key = JSON.stringify([compactRuns(), (review.evaluations || []).map(function (e) { return [e.name, e.stamp]; }), (review.stage || {}).run]);
    if (key === runsKey) return;
    runsKey = key;
    setText('training-runs-count', runs.length ? String(runs.length) : '');
    var evaluated = runEvaluations(runs, review.evaluations || []), body = $('training-runs-body'), previous = null;
    var rows = runs.map(function (run) {
      var t = run.telemetry || {}, best = t.best_reward_per_step, delta = best != null && previous != null ? best - previous : null;
      if (best != null) previous = best;
      var outcome = OUTCOMES[run.status] || [run.status || 'unknown', ''], e = evaluated[run.run];
      var reason = ((run.training || {}).requested || {}).reason;
      var name = el('td', { class: 'run-name' }, [el('span', { class: 'mono', text: run.run }),
        t.label && t.label !== run.run ? el('span', { class: 'muted', text: ' ' + t.label }) : null,
        typeof reason === 'string' && reason ? el('span', { class: 'run-reason muted', text: reason, title: reason }) : null]);
      var tr = el('tr', { 'data-run': run.run, 'data-current': String(run.run === (review.stage || {}).run) }, [
        name,
        el('td', { class: 'num c-iter', text: t.iteration != null && t.iteration >= 0 ? (t.iteration + 1) + (t.total ? ' / ' + t.total : '') : '—' }),
        el('td', { class: 'num', text: best == null ? '—' : fmt(best), title: best == null ? '' : 'iteration ' + (t.best_iteration + 1) }),
        el('td', { class: 'num delta', text: delta == null ? '' : signed(delta), 'data-sign': delta == null ? '' : delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat' }),
        el('td', {}, [el('span', { class: 'chip', 'data-tone': outcome[1], text: outcome[0], title: run.error || run.outcome || '' })]),
        el('td', {}, [e ? el('span', { class: 'chip', 'data-tone': e.verdict === 'pass' ? 'ok' : 'bad',
                                        text: e.verdict + ' ' + e.passed + '/' + e.seeds, title: (e.failing || []).join(', ') }) : el('span', { class: 'muted', text: '—' })])]);
      return tr;
    });
    body.textContent = '';
    rows.reverse().slice(0, RUNS_LISTED).forEach(function (tr) { body.appendChild(tr); });
  }

  // -- Project: the agent's own panel (ADR-607) ----------------------------------------
  function themeTokens() {
    var style = getComputedStyle(document.documentElement), tokens = {};
    TOKENS.forEach(function (name) { tokens[name] = style.getPropertyValue(name).trim(); });
    return tokens;
  }
  function panelMessage() {
    var stage = review.stage || {}, t = stage.training || null, training = null;
    if (t) {
      training = {};
      Object.keys(t).forEach(function (k) { if (k !== 'spark' && k !== 'marks') training[k] = t[k]; });
      var full = panel.detail && panel.detail.run === stage.run ? panel.detail.telemetry : null;
      training.curves = {};
      CHARTS.forEach(function (c) { training.curves[c.key] = full ? full[c.key] || [] : (t.spark || {})[c.key] || []; });
      training.resolution = full ? 'full' : 'sketch';
      training.checkpoints = full ? (full.checkpoints || []).map(function (c) { return { iteration: c.iteration, path: c.path, status: c.status }; })
                                  : (t.marks || []).map(function (m) { return { iteration: m[0], reward_per_step: m[1] }; });
    }
    var runs = compactRuns(), newest = (review.runs || [])[(review.runs || []).length - 1];
    var rows = (review.evaluations || []).map(function (e) {
      return { name: e.name, verdict: e.verdict, passed: e.passed, seeds: e.seeds, failing: e.failing, terminations: e.terminations,
               task_output: e.task_output, task_label: e.task_label, policy_output: e.policy_output, policy_sha256: e.policy_sha256,
               evaluated_at: e.evaluated_at, relation: e.relation };
    });
    var latest = rows[rows.length - 1];
    if (latest && evalDetail.name === latest.name && evalDetail.summary) latest.summary = evalDetail.summary;
    return {
      type: 'cadex-status', schema: PANEL_SCHEMA, project: review.project, served_at: review.served_at,
      theme: { name: document.documentElement.dataset.theme || 'dark', tokens: themeTokens() },
      accepted: review.accepted ? { available: review.accepted.available, revision: review.accepted.revision,
                                    digest: review.accepted.digest, updated_at: review.accepted.updated_at } : null,
      revisions: (review.revisions || []).slice(0, 64).map(function (r) { return { ordinal: r.ordinal, revision: r.revision, saved_at: r.saved_at }; }),
      stage: { state: stage.state, reason: stage.reason, since: stage.since, run: stage.run, runs: stage.runs },
      training: training, runs: runs, evaluations: rows,
      params: newest && newest.params ? newest.params : null,
      activity: ((review.activity || {}).entries || []).slice(0, ACTIVITY_LIST).map(function (e) {
        return { t: e.t, tool: e.tool, args: e.args, outcome: e.outcome, detail: e.detail }; })
    };
  }
  function postPanel() {
    if (!panel.frame || !panel.frame.contentWindow || !review) return;
    panel.message = panelMessage();
    // The frame's origin is opaque ("null"), so the message cannot be addressed to it by origin.
    panel.frame.contentWindow.postMessage(panel.message, '*');
    panel.posted += 1;
  }
  function refreshDetail() {
    // The panel gets the run's full histories, read at most every PANEL_DETAIL_MS
    // and only when the run has moved since.
    var stage = review.stage || {}, t = stage.training;
    if (!t || !stage.run || !panel.frame) return;
    var key = JSON.stringify([stage.run, t.iteration, t.state]);
    if (key === panel.detailKey || Date.now() - panel.detailAt < PANEL_DETAIL_MS) return;
    panel.detailKey = key; panel.detailAt = Date.now();
    json('api/run/' + encodeURIComponent(stage.run)).then(function (record) {
      panel.detail = { run: record.run, telemetry: record.telemetry || {} };
      postPanel();
    }).catch(function () { panel.detailKey = null; });
  }
  function renderPanel() {
    var info = (review.stage || {}).panel || { available: false };
    setHidden('status-panel', !info.available);
    if (!info.available) {
      if (panel.frame) { $('status-panel').textContent = ''; panel.frame = null; panel.url = null; }
      return;
    }
    if (panel.url !== info.url) {
      panel.url = info.url;
      var frame = el('iframe', { id: 'status-panel-frame', title: 'Project status panel, written by the agent', src: info.url });
      // An opaque origin that may run its own script and nothing more: no same-origin,
      // no forms, no popups, no top navigation (ADR-607).
      frame.setAttribute('sandbox', 'allow-scripts');
      frame.setAttribute('referrerpolicy', 'no-referrer');
      frame.addEventListener('load', postPanel);
      $('status-panel').textContent = '';
      $('status-panel').appendChild(frame);
      panel.frame = frame;
    }
  }
  function render(next) {
    review = next;
    var stage = review.stage || { state: 'idle', training: null, runs: 0 }, t = stage.training;
    var now = Date.parse(review.served_at) || Date.now(), name = STAGE_LABELS[stage.state] ? stage.state : 'idle';
    refreshPicked();
    var view = shown();
    renderHead(stage, t, now, view);
    renderPanel();
    renderStats(view.t, view.own ? name : 'idle');
    renderCharts(view.t);
    renderEvaluation(now);
    renderRuns(now);
    if (panel.frame) { refreshDetail(); postPanel(); }
  }

  function wire() {
    wireBoard();
    // The cards follow the area's width.
    if (window.ResizeObserver) new ResizeObserver(function () { applySpans(); if (review) renderCharts(shown().t); }).observe($('training'));
    document.addEventListener('cadex-theme', postPanel);
    // A panel may ask for the newest message once its script is listening.
    window.addEventListener('message', function (event) {
      if (!panel.frame || event.source !== panel.frame.contentWindow) return;
      if (event.data && event.data.type === 'cadex-status-ready') postPanel();
    });
  }
  wire();

  window.CadexStatus = {
    render: render,
    // The run picked as the 3D viewport's source, or null for the stage's (ADR-790).
    select: function (run) {
      run = run || null;
      if (picked.run === run) return;
      picked = { run: run, key: null, t: null };
      chartKeys = {};
    },
    shown: function () { var v = shown(); return { run: v.run, own: v.own, iteration: v.t ? v.t.iteration : null }; },
    // The Training cards (ADR-770): their arrangement, and a change to one card as its buttons make it.
    cards: function () {
      return { order: board.order.slice(), pinned: Object.keys(board.pinned), hidden: Object.keys(board.hidden), max: board.max,
               size: cards().reduce(function (o, node) { o[node.dataset.card] = sizeOf(node); return o; }, {}) };
    },
    setCard: setCard,
    resetCards: resetBoard,
    panel: function () { return { url: panel.url, posted: panel.posted, message: panel.message }; },
    message: function () { return review ? panelMessage() : null; }
  };
})();
