// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The home page (ADR-533, ADR-605): /api/projects, the most recently active
// project in the spotlight, then a card per project newest first, PAGE_SIZE
// to a page, the page and the filter kept in the URL (?page=N, ?q=text).
// Polls so a new project, a stage or a picture appears; a card is rebuilt
// only when what it shows changed. Writes nothing.
(function () {
  'use strict';

  var POLL_MS = 5000;
  var PAGE_SIZE = 24;
  var STAGES = { idle: 1, designing: 1, training: 1, evaluating: 1, stopped: 1, failed: 1 };
  var params = new URLSearchParams(location.search);
  var projects = [], shown = [], servedAt = Date.now(), lastOk = null, failed = null;
  var page = Math.max(1, parseInt(params.get('page'), 10) || 1);
  var filter = params.get('q') || '';
  var cardKeys = {}, spotlightKey = null;

  function $(id) { return document.getElementById(id); }
  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (key) {
      if (key === 'text') node.textContent = attrs[key];
      else if (key === 'class') node.className = attrs[key];
      else if (key.indexOf('data-') === 0 || key.indexOf('aria-') === 0) node.setAttribute(key, attrs[key]);
      else node[key] = attrs[key];
    });
    (children || []).forEach(function (child) { if (child) node.appendChild(child); });
    return node;
  }
  function ago(stamp) {
    var t = stamp ? Date.parse(stamp) : NaN;
    if (isNaN(t)) return '';
    var s = Math.max(0, (servedAt - t) / 1000);
    if (s < 60) return 'just now';
    if (s < 3600) return Math.round(s / 60) + ' min ago';
    if (s < 86400) return Math.round(s / 3600) + ' h ago';
    if (s < 86400 * 14) return Math.round(s / 86400) + ' d ago';
    return new Date(t).toLocaleDateString([], { dateStyle: 'medium' });
  }
  function plural(n, word) { return n + ' ' + word + (n === 1 ? '' : 's'); }
  function stageOf(p) { var s = (p.stage || {}).state; return STAGES[s] ? s : 'idle'; }
  function progress(p) {
    var s = p.stage || {};
    return stageOf(p) === 'training' && s.total ? Math.max(0, Math.min(1, ((s.iteration || 0) + 1) / s.total)) : null;
  }
  function stageLine(p) {
    var s = p.stage || {}, name = stageOf(p);
    if (name === 'training') {
      return s.iteration != null && s.iteration >= 0
        ? 'iteration ' + (s.iteration + 1) + ' of ' + s.total + (s.reward_per_step != null ? ' · reward ' + Number(s.reward_per_step.toPrecision(4)) : '')
        : 'starting';
    }
    if (name === 'idle') {
      var e = p.latest_evaluation;
      if (e) return (e.task_label ? e.task_label + ' · ' : '') + (e.failing && e.failing.length ? 'failing ' + e.failing.join(', ') : 'every predicate passed');
      return p.accepted && p.accepted.available ? 'revision accepted ' + ago(p.accepted.updated_at) : 'nothing accepted yet';
    }
    return s.reason || '';
  }
  function verdict(p) {
    var e = p.latest_evaluation;
    return e ? { tone: e.verdict === 'pass' ? 'ok' : 'bad', text: e.verdict + ' ' + e.passed + '/' + e.seeds } : null;
  }

  // A picture: the project's hero, an evaluation's hero, or a film sheet
  // cropped to its first frame; else a drawn placeholder.
  function media(holder, p) {
    holder.textContent = '';
    var t = p.thumbnail;
    holder.dataset.source = t ? t.source : 'none';
    if (!t) {
      holder.appendChild(placeholder());
      return;
    }
    var img = el('img', { src: t.url, alt: p.name, loading: 'lazy', decoding: 'async', draggable: false });
    img.addEventListener('error', function () { holder.textContent = ''; holder.dataset.source = 'none'; holder.appendChild(placeholder()); });
    if (!t.tile) { holder.appendChild(img); return; }
    // A film sheet is a grid of frames: show its first, without its time label.
    var frame = el('div', { class: 'tile-frame' }, [img]);
    img.className = 'tile';
    img.style.width = (t.tile[0] * 100) + '%';
    img.addEventListener('load', function () {
      var w = img.naturalWidth / t.tile[0], h = img.naturalHeight / t.tile[1] * TILE_SHOWN;
      if (w && h) frame.style.aspectRatio = w + ' / ' + h;
    });
    holder.appendChild(frame);
  }
  var TILE_SHOWN = 0.86;
  function placeholder() {
    var NS = 'http://www.w3.org/2000/svg', svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 120 90');
    svg.setAttribute('class', 'placeholder');
    svg.setAttribute('aria-hidden', 'true');
    // An isometric box on the floor: a project with nothing drawn yet.
    [['path', 'M60 22 L84 36 L84 60 L60 74 L36 60 L36 36 Z', 'edge'],
     ['path', 'M36 36 L60 50 L84 36 M60 50 L60 74', 'edge'],
     ['path', 'M20 66 L60 88 L100 66', 'floor']].forEach(function (d) {
      var n = document.createElementNS(NS, d[0]);
      n.setAttribute('d', d[1]); n.setAttribute('class', d[2]);
      svg.appendChild(n);
    });
    return svg;
  }

  function counts(p) {
    return [['revisions', p.revisions || 0, 'revision'], ['runs', p.runs || 0, 'run'], ['evaluations', p.evaluations || 0, 'evaluation']];
  }

  function card(p) {
    var v = verdict(p), bar = progress(p);
    var thumb = el('div', { class: 'thumb' });
    media(thumb, p);
    var chips = el('div', { class: 'chips' }, [
      el('span', { class: 'chip', 'data-stage': stageOf(p), text: stageOf(p) }),
      v ? el('span', { class: 'chip', 'data-tone': v.tone, text: v.text }) : null]);
    var body = el('div', { class: 'card-body' }, [
      el('div', { class: 'card-head' }, [el('span', { class: 'card-name', text: p.name }),
                                         el('span', { class: 'card-ago muted small', text: ago(p.active_at) })]),
      chips,
      bar == null ? null : el('div', { class: 'progress', 'aria-label': 'training progress' }, [el('span', { style: 'width:' + (bar * 100).toFixed(1) + '%' })]),
      el('p', { class: 'card-line muted small', text: stageLine(p), title: stageLine(p) }),
      el('p', { class: 'card-counts muted small', text: counts(p).map(function (c) { return plural(c[1], c[2]); }).join(' · ') })]);
    var link = el('a', { class: 'card', href: p.url }, [thumb, body]);
    var item = el('li', { 'data-project': p.name, 'data-stage': stageOf(p) }, [link]);
    if (bar != null) item.querySelector('.progress span').style.width = (bar * 100).toFixed(1) + '%';
    return item;
  }

  function pages() { return Math.max(1, Math.ceil(shown.length / PAGE_SIZE)); }

  function renderSpotlight() {
    var top = !filter && page === 1 ? projects.filter(function (p) { return p.active_at; })[0] : null;
    $('spotlight').hidden = !top;
    if (!top) { spotlightKey = null; return; }
    var key = JSON.stringify([top, Math.round(servedAt / 60000)]);
    if (key === spotlightKey) return;
    spotlightKey = key;
    var v = verdict(top), bar = progress(top);
    media($('spotlight-media'), top);
    ['spotlight-media', 'spotlight-link', 'spotlight-open'].forEach(function (id) { $(id).href = top.url; });
    $('spotlight-link').textContent = top.name;
    $('spotlight-ago').textContent = ago(top.active_at);
    $('spotlight-stage').textContent = stageOf(top);
    $('spotlight-stage').dataset.stage = stageOf(top);
    $('spotlight-verdict').hidden = !v;
    if (v) { $('spotlight-verdict').textContent = 'latest evaluation ' + v.text; $('spotlight-verdict').dataset.tone = v.tone; }
    $('spotlight-progress').hidden = bar == null;
    if (bar != null) $('spotlight-progress').firstElementChild.style.width = (bar * 100).toFixed(1) + '%';
    $('spotlight-line').textContent = stageLine(top);
    var dl = $('spotlight-counts');
    dl.textContent = '';
    counts(top).forEach(function (c) {
      dl.appendChild(el('div', {}, [el('dt', { text: c[0] }), el('dd', { text: String(c[1]) })]));
    });
  }

  function renderProjects() {
    var needle = filter.trim().toLowerCase();
    shown = needle ? projects.filter(function (p) { return p.name.toLowerCase().indexOf(needle) >= 0; }) : projects;
    page = Math.min(page, pages());
    var list = $('projects'), wanted = shown.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
    var existing = {};
    Array.prototype.forEach.call(list.children, function (item) { existing[item.dataset.project] = item; });
    var keep = {};
    wanted.forEach(function (p, index) {
      // A card is rebuilt only when what it shows changed: an idle poll adds no nodes.
      var key = JSON.stringify([p, Math.round(servedAt / 60000)]), item = existing[p.name];
      if (!item || cardKeys[p.name] !== key) {
        var fresh = card(p);
        if (item) list.replaceChild(fresh, item);
        item = fresh;
        cardKeys[p.name] = key;
      }
      keep[p.name] = true;
      if (list.children[index] !== item) list.insertBefore(item, list.children[index] || null);
    });
    Object.keys(existing).forEach(function (name) { if (!keep[name]) { list.removeChild(existing[name]); delete cardKeys[name]; } });
    $('projects-count').textContent = projects.length ? String(projects.length) : '';
    $('projects-empty').hidden = projects.length > 0;
    $('projects-none').hidden = !(projects.length && !shown.length);
    $('pager').hidden = pages() < 2;
    $('page-at').textContent = page + ' of ' + pages();
    $('page-prev').disabled = page <= 1;
    $('page-next').disabled = page >= pages();
    renderSpotlight();
  }

  function remember() {
    var url = new URL(location.href);
    if (page > 1) url.searchParams.set('page', String(page)); else url.searchParams.delete('page');
    if (filter) url.searchParams.set('q', filter); else url.searchParams.delete('q');
    history.replaceState(null, '', url);
  }

  function go(to) {
    page = Math.min(Math.max(1, to), pages());
    remember();
    renderProjects();
    window.scrollTo(0, 0);
  }

  function render(data) {
    servedAt = Date.parse(data.served_at) || Date.now();
    // Most recently active first; a project with no recorded time sorts last, by name.
    projects = data.projects.slice().sort(function (a, b) {
      var x = a.active_at || '', y = b.active_at || '';
      if (x !== y) return x < y ? 1 : -1;
      return a.name.localeCompare(b.name);
    });
    renderProjects();
  }

  function renderFreshness() {
    var node = $('freshness');
    if (failed) { node.dataset.state = 'stale'; node.textContent = 'offline'; node.title = failed; }
    else if (lastOk) { node.dataset.state = 'live'; node.textContent = 'live'; node.title = 'updated ' + lastOk.toLocaleTimeString(); }
  }

  function getJson(url) {
    return fetch(url, { cache: 'no-store' }).then(function (response) {
      if (!response.ok) throw new Error(url + ': HTTP ' + response.status);
      return response.json();
    });
  }

  function poll() {
    getJson('api/projects').then(function (data) {
      failed = null; lastOk = new Date();
      render(data);
    }).catch(function (error) {
      failed = error.message;
    }).then(function () { renderFreshness(); setTimeout(poll, POLL_MS); });
  }

  $('page-prev').addEventListener('click', function () { go(page - 1); });
  $('page-next').addEventListener('click', function () { go(page + 1); });
  $('projects-filter').value = filter;
  $('projects-filter').addEventListener('input', function () {
    filter = $('projects-filter').value;
    page = 1;
    remember();
    renderProjects();
  });
  $('theme-toggle').addEventListener('click', function () {
    window.cadexTheme.set(window.cadexTheme.theme() === 'dark' ? 'light' : 'dark');
  });
  window.cadexProjects = { shown: function () { return shown.map(function (p) { return p.name; }); } };
  poll();
}());
