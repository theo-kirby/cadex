# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Check checkpoint provenance on the persistent server for a playback run.

PYTHONPATH=cli:cli/tests pixi run python checkpoints.py URL PROJECT RUN LABEL
Selects RUN in an open page, reads its checkpoint provenance and statuses,
returns to the current run, writes evidence/RUN-LABEL-checkpoints.json and a
screenshot. A playback run (its record names ``source_run``) must resolve
through that training run; any other run resolves in its own train/. A
snapshot that lists no checkpoints is reported as such, not failed. Never
starts or stops a server.
"""
import json
from pathlib import Path
import sys
from cdp_browser import HeadlessBrowser, find_browser

url, project, run, label = sys.argv[1:]
p = Path(project).resolve()
assert Path(run).name == run and Path(label).name == label
record = json.loads((p / 'runs' / run / 'run.json').read_text())
source = (record['training'].get('requested') or {}).get('source_run')
expected_state, expected_from = ('resolved', source) if source else ('none', 'run')
with HeadlessBrowser(find_browser()) as browser:
    page = browser.page(url)
    page.evaluate('window.cadexReview.ready', await_promise=True)
    page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
    default_run = page.text('#view-kind')
    page.click("#views li[data-run='" + run + "']")
    page.wait_for("document.getElementById('view-kind').textContent === 'RUN " + run + "'")
    page.wait_for("document.getElementById('checkpoint-source').dataset.state === '" + expected_state + "'")
    items = page.evaluate("Array.from(document.querySelectorAll('#checkpoints li[data-status]')).map(function (li) {"
                          "return {status: li.dataset.status, source: li.dataset.source, text: li.textContent};})")
    result = {'url_project': page.text('#project-name'), 'default_view': default_run, 'run': run,
              'relation': page.text('#view-relation'), 'revision': page.text('#view-revision'),
              'telemetry_state': page.attribute('#telemetry', 'data-state'),
              'checkpoint_source': {'state': page.attribute('#checkpoint-source', 'data-state'),
                                    'run': page.attribute('#checkpoint-source', 'data-run'),
                                    'text': page.text('#checkpoint-source')},
              'checkpoints': items, 'checkpoints_reported': bool(items),
              'snapshot_iteration': page.text('[data-metric=iteration]'),
              'private_address_same_machine': True, 'persistent_server': True}
    assert result['revision'] == record['model']['accepted_revision']
    assert result['checkpoint_source']['state'] == expected_state
    assert result['checkpoint_source']['run'] == (source or '')
    assert all(i['status'] == 'retained' and i['source'] == expected_from for i in items)
    page.screenshot(p / 'evidence' / (run + '-' + label + '-checkpoints.png'))
    page.click('#current-run')
    page.wait_for("document.getElementById('view-kind').textContent === " + json.dumps(default_run))
    result['returned_to'] = page.text('#view-kind')
    (p / 'evidence' / (run + '-' + label + '-checkpoints.json')).write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=1))
