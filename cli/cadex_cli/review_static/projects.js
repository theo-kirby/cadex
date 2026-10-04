// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The projects index (ADR-533): /api/projects newest first, PAGE_SIZE to a
// page, the page kept in the URL (?page=N). Polls so a new project appears.
// Writes nothing.
(function () {
  'use strict';

  var POLL_MS = 5000;
  var PAGE_SIZE = 20;
  var projects = [];
  var page = Math.max(1, parseInt(new URLSearchParams(location.search).get('page'), 10) || 1);

  function $(id) { return document.getElementById(id); }
  function when(stamp) {
    var date = stamp ? new Date(stamp) : null;
    return date && !isNaN(date) ? date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : '';
  }
  function row(dataset, href, name, detail) {
    var item = document.createElement('li');
    Object.keys(dataset).forEach(function (key) { item.dataset[key] = dataset[key]; });
    var link = document.createElement('a');
    link.href = href;
    link.textContent = name;
    var small = document.createElement('span');
    small.className = 'muted small';
    small.textContent = detail;
    item.appendChild(link);
    item.appendChild(small);
    return item;
  }

  function pages() { return Math.max(1, Math.ceil(projects.length / PAGE_SIZE)); }

  function renderProjects() {
    page = Math.min(page, pages());
    var list = $('projects');
    list.textContent = '';
    projects.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE).forEach(function (project) {
      list.appendChild(row({ project: project.name }, project.url, project.name,
        project.accepted.available ? when(project.accepted.updated_at) : 'nothing accepted'));
    });
    $('projects-count').textContent = projects.length ? String(projects.length) : '';
    $('projects-empty').hidden = projects.length > 0;
    $('pager').hidden = pages() < 2;
    $('page-at').textContent = page + ' of ' + pages();
    $('page-prev').disabled = page <= 1;
    $('page-next').disabled = page >= pages();
  }

  function go(to) {
    page = Math.min(Math.max(1, to), pages());
    var url = new URL(location.href);
    if (page > 1) url.searchParams.set('page', String(page)); else url.searchParams.delete('page');
    history.replaceState(null, '', url);
    renderProjects();
    window.scrollTo(0, 0);
  }

  function render(data) {
    // Newest accepted first; a project with nothing accepted sorts last.
    projects = data.projects.slice().sort(function (a, b) {
      var x = (a.accepted.available && a.accepted.updated_at) || '', y = (b.accepted.available && b.accepted.updated_at) || '';
      return x === y ? a.name.localeCompare(b.name) : (x < y ? 1 : -1);
    });
    renderProjects();
  }

  function getJson(url) {
    return fetch(url, { cache: 'no-store' }).then(function (response) {
      if (!response.ok) throw new Error(url + ': HTTP ' + response.status);
      return response.json();
    });
  }

  function poll() {
    getJson('api/projects').then(render).catch(function (error) {
      $('projects-count').textContent = 'unavailable: ' + error.message;
    }).then(function () { setTimeout(poll, POLL_MS); });
  }

  $('page-prev').addEventListener('click', function () { go(page - 1); });
  $('page-next').addEventListener('click', function () { go(page + 1); });
  poll();
}());
