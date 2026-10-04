// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// One Ouroboros run (ADR-513, cut by ADR-533): reads api/run and draws the
// charter's done criteria, ticked or not, and the iterations newest first
// with the critic's verdict and reason. Polls, so a live run's next
// iteration appears. Writes nothing.
(function () {
  'use strict';

  var POLL_MS = 10000;
  var TONES = { 'continue': 'ok', 'done_accepted': 'ok', 'answer': 'current', 'reject': 'bad',
                'done_rejected': 'bad', 'stuck': 'warn', 'looping': 'warn' };

  function $(id) { return document.getElementById(id); }
  function cell(row, text, className) {
    var td = document.createElement('td');
    td.textContent = text;
    if (className) td.className = className;
    row.appendChild(td);
    return td;
  }

  function renderCharter(charter) {
    charter = charter || { available: false, criteria: [], reason: 'this server reports no charter' };
    var list = $('charter');
    list.textContent = '';
    $('charter-count').textContent = charter.total ? charter.checked + ' of ' + charter.total + ' ticked' : '';
    charter.criteria.forEach(function (item) {
      var li = document.createElement('li');
      li.dataset.criterion = item.id || '';
      li.dataset.checked = item.checked ? 'true' : 'false';
      li.title = item.markdown || '';
      li.textContent = (item.checked ? '✓ ' : '') + (item.id ? item.id + '  ' : '') + item.title;
      list.appendChild(li);
    });
    var empty = $('charter-empty');
    empty.hidden = charter.criteria.length > 0;
    empty.textContent = charter.reason ? 'No charter criteria: ' + charter.reason + '.' : '';
  }

  function render(run) {
    renderCharter(run.charter);
    document.title = run.name + ' — Cadex';
    $('run-name').textContent = run.name;
    $('run-line').textContent = [run.state, run.iteration_count + ' iterations'].join(' · ');
    var body = $('iterations');
    body.textContent = '';
    run.iterations.slice().reverse().forEach(function (item) {
      var row = document.createElement('tr');
      row.dataset.iteration = String(item.iteration);
      row.dataset.verdict = item.verdict || '';
      cell(row, String(item.iteration), 'muted');
      var verdict = cell(row, item.verdict || 'pending', 'verdict');
      verdict.dataset.tone = TONES[item.verdict] || '';
      var critic = item.critic || {};
      cell(row, critic.reason || critic.did || (item.critique && item.critique.reason) || '');
      body.appendChild(row);
    });
    $('iterations-empty').hidden = run.iterations.length > 0;
  }

  function poll() {
    fetch('api/run', { cache: 'no-store' }).then(function (response) {
      if (!response.ok) throw new Error('api/run: HTTP ' + response.status);
      return response.json();
    }).then(render).catch(function (error) {
      $('run-line').textContent = 'unavailable: ' + error.message;
    }).then(function () { setTimeout(poll, POLL_MS); });
  }

  poll();
}());
