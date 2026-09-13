# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Check the persistent server's default run at experiment boundaries.

PYTHONPATH=cli:cli/tests pixi run python current.py URL PROJECT RUN LABEL
Writes evidence/RUN-LABEL-browser.json and a screenshot, never starts a server.
"""
import json
from pathlib import Path
import sys
from cdp_browser import HeadlessBrowser, find_browser

url, project, run, label = sys.argv[1:]
p = Path(project).resolve()
assert Path(run).name == run and Path(label).name == label
record = json.loads((p / 'runs' / run / 'run.json').read_text())
with HeadlessBrowser(find_browser()) as browser:
    page = browser.page(url)
    page.evaluate('window.cadexReview.ready', await_promise=True)
    page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
    result = {k: page.text('#' + k) for k in
              ('project-name', 'view-kind', 'view-revision', 'current-run', 'params', 'telemetry')}
    assert result['project-name'] == p.name + ' — review'
    assert result['view-kind'] == 'RUN ' + run
    assert result['view-revision'] == record['model']['accepted_revision']
    foot_len = record['params']['values']['foot_len']
    assert float(page.text("#params tr[data-param='foot_len'] td:nth-child(2)")) == foot_len
    result.update(private_address_same_machine=True, persistent_server=True, foot_len_mm=foot_len)
    page.screenshot(p / 'evidence' / (run + '-' + label + '-browser.png'))
    (p / 'evidence' / (run + '-' + label + '-browser.json')).write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result))
