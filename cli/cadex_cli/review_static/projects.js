// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The projects index: lists /api/projects, one link per project, and polls so
// a project created while the page is open appears. Writes nothing.
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

  function poll() {
    fetch('api/projects', { cache: 'no-store' }).then(function (response) {
      if (!response.ok) throw new Error('api/projects: HTTP ' + response.status);
      return response.json();
    }).then(render).catch(function (error) {
      document.getElementById('projects-root').textContent = 'unavailable: ' + error.message;
    }).then(function () { setTimeout(poll, POLL_MS); });
  }

  poll();
}());
