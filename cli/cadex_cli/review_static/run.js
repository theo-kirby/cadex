// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// One Ouroboros run (ADR-513): reads api/run and draws its iterations,
// newest first, with the critic's verdict, reason and what it saw done; the
// critic's message to the next iteration folds under each row. Polls, so a
// live run's next iteration appears. Writes nothing.
(function () {
  'use strict';

  var POLL_MS = 10000;
  var TONES = { 'continue': 'ok', 'done_accepted': 'ok', 'answer': 'current', 'reject': 'bad',
                'done_rejected': 'bad', 'stuck': 'warn', 'looping': 'warn' };

  function badge(text, tone) {
    var span = document.createElement('span');
    span.className = 'badge';
    span.dataset.tone = tone || 'historical';
    span.textContent = text;
    return span;
  }

  function cell(row, child) {
    var td = document.createElement('td');
    if (typeof child === 'string') td.textContent = child; else if (child) td.appendChild(child);
    row.appendChild(td);
    return td;
  }

  function render(run) {
    document.title = 'Cadex run ' + run.name;
    document.getElementById('run-name').textContent = run.name + ' — run';
    var parts = [run.state, run.branch, run.iteration_count + ' iteration(s)'];
    if (typeof run.cost_usd === 'number') parts.push('$' + run.cost_usd.toFixed(2));
    if (run.updated) parts.push('updated ' + run.updated);
    document.getElementById('run-line').textContent = parts.join(' · ');
    var tally = document.getElementById('run-tally');
    tally.textContent = '';
    Object.keys(run.verdicts).sort().forEach(function (verdict) {
      tally.appendChild(badge(run.verdicts[verdict] + ' ' + verdict, TONES[verdict]));
    });
    var body = document.getElementById('iterations');
    body.textContent = '';
    run.iterations.slice().reverse().forEach(function (item) {
      var row = document.createElement('tr');
      row.dataset.iteration = String(item.iteration);
      row.dataset.verdict = item.verdict || '';
      cell(row, String(item.iteration) + (item.housekeeping ? ' · housekeeping' : ''));
      cell(row, item.verdict ? badge(item.verdict, TONES[item.verdict]) : 'pending');
      var critic = item.critic || {};
      var saw = cell(row, null);
      var did = document.createElement('div');
      did.className = 'did';
      did.textContent = critic.did || (item.critique && item.critique.reason) || '';
      saw.appendChild(did);
      var reason = critic.reason || (item.critique && item.critique.reason) || '';
      if (reason && reason !== did.textContent) {
        var why = document.createElement('div');
        why.className = 'muted small reason';
        why.textContent = reason;
        saw.appendChild(why);
      }
      if (critic.reply) {
        var fold = document.createElement('details');
        var summary = document.createElement('summary');
        summary.className = 'small';
        summary.textContent = 'message to the next iteration';
        var reply = document.createElement('p');
        reply.className = 'small reply';
        reply.style.whiteSpace = 'pre-wrap';
        reply.textContent = critic.reply;
        fold.appendChild(summary);
        fold.appendChild(reply);
        saw.appendChild(fold);
      }
      var commit = item.commit && item.commit.sha ? item.commit.sha.slice(0, 10) : '—';
      if (item.commit && item.commit.recorded) commit += ' · recorded';
      cell(row, commit).className = 'small';
      body.appendChild(row);
    });
    document.getElementById('iterations-empty').hidden = run.iterations.length > 0;
  }

  function poll() {
    fetch('api/run', { cache: 'no-store' }).then(function (response) {
      if (!response.ok) throw new Error('api/run: HTTP ' + response.status);
      return response.json();
    }).then(render).catch(function (error) {
      document.getElementById('run-line').textContent = 'unavailable: ' + error.message;
    }).then(function () { setTimeout(poll, POLL_MS); });
  }

  poll();
}());
