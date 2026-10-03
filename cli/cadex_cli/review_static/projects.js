// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The projects index: lists /api/projects, one link per project, and beside
// them /api/runs, one link per Ouroboros run (ADR-513). Polls so a project
// created, or a run iteration finished, while the page is open appears.
// Writes nothing.
(function () {
  'use strict';

  var POLL_MS = 5000;

  function render(data) {
    document.getElementById('projects-root').textContent = data.root + ' · ' + data.projects.length + ' project(s)';
    var list = document.getElementById('projects');
    list.textContent = '';
    data.projects.forEach(function (project) {
      var item = document.createElement('li');
      item.dataset.project = project.name;
      var link = document.createElement('a');
      link.href = project.url;
      link.textContent = project.name;
      var detail = document.createElement('span');
      detail.className = 'muted small';
      var accepted = project.accepted.available ? 'accepted ' + project.accepted.revision.slice(0, 12) : project.accepted.reason;
      detail.textContent = ' · ' + accepted + ' · ' + project.runs + ' run(s)';
      item.appendChild(link);
      item.appendChild(detail);
      list.appendChild(item);
    });
    document.getElementById('projects-empty').hidden = data.projects.length > 0;
  }

  function renderRuns(data) {
    var list = document.getElementById('runs');
    list.textContent = '';
    data.runs.forEach(function (run) {
      var item = document.createElement('li');
      item.dataset.run = run.name;
      var link = document.createElement('a');
      link.href = run.url;
      link.textContent = run.name;
      var detail = document.createElement('span');
      detail.className = 'muted small';
      var tally = Object.keys(run.verdicts).sort().map(function (verdict) {
        return run.verdicts[verdict] + ' ' + verdict;
      }).join(', ');
      detail.textContent = ' · ' + run.state + ' · ' + run.iteration_count + ' iteration(s)' + (tally ? ' · ' + tally : '');
      item.appendChild(link);
      item.appendChild(detail);
      list.appendChild(item);
    });
    document.getElementById('runs-empty').hidden = data.runs.length > 0;
  }

  function getJson(url) {
    return fetch(url, { cache: 'no-store' }).then(function (response) {
      if (!response.ok) throw new Error(url + ': HTTP ' + response.status);
      return response.json();
    });
  }

  function poll() {
    Promise.all([
      getJson('api/projects').then(render).catch(function (error) {
        document.getElementById('projects-root').textContent = 'unavailable: ' + error.message;
      }),
      getJson('api/runs').then(renderRuns).catch(function () {})
    ]).then(function () { setTimeout(poll, POLL_MS); });
  }

  poll();
}());
