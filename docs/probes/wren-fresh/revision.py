# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Verify Wren's foot revision and retained history on the persistent server.

PYTHONPATH=cli:cli/tests pixi run python revision.py URL PROJECT
Requires evidence/revision50/runs-before.json, captured before the CLI edit.
Reads project state; writes receipts/screenshots only under evidence/revision50.
"""
import base64
import hashlib
import json
import re
import struct
import sys
import urllib.request
from pathlib import Path

from cdp_browser import HeadlessBrowser, find_browser


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


url, project = sys.argv[1:]
root = Path(project).resolve()
out = root / 'evidence/revision50'
before = read(out / 'runs-before.json')
manifest = read(root / 'script.json')
params = read(out / 'params.json')
assert params['ok'] and manifest['accepted_revision'] == params['accepted_revision']
assert (root / 'script.py').read_bytes() == (out / 'script-before.py').read_bytes()
old = read(out / 'manifest-before.json')
effective = lambda m: {**{s['name']: s['default'] for s in m['param_specs']}, **m['param_values']}
changes = {k: [effective(old)[k], v] for k, v in effective(manifest).items() if effective(old)[k] != v}
assert changes == {'foot_len': [85.0, 105.0], 'policy_on': [1.0, 0.0]}
task_before = read(root / 'runs/wren1/train/wren_walk-task.json')
task_after = read(out / 'export/wren_walk-task.json')
assert {k for k in task_before.keys() | task_after.keys()
        if task_before.get(k) != task_after.get(k)} == {'model'}


def inventory():
    return {str(f.relative_to(root)): sha(f.read_bytes())
            for f in sorted((root / 'runs').rglob('*')) if f.is_file()}


assert inventory() == before, 'retained run bytes changed'
receipt = {'project': root.name, 'accepted_revision': manifest['accepted_revision'],
           'accepted_digest': manifest['accepted_digest'], 'changes': changes,
           'script_text_unchanged': True, 'task_changed_fields': ['model'],
           'retained_files': len(before), 'retained_inventory_sha256': sha(json.dumps(before, sort_keys=True).encode()),
           'comparison': read(out / 'comparison.json'), 'historical': {},
           'persistent_server': True, 'private_address_same_machine': True}


def get(route):
    return urllib.request.urlopen(url.rstrip('/') + route, timeout=15).read()


def foot_mesh(route, revision, length):
    model = json.loads(get(route))
    assert model['available'] and model['revision'] == revision
    result = {}
    for component in model['components']:
        if component['output'] not in ('foot_l', 'foot_r'):
            continue
        data = get(component['mesh'])
        count = struct.unpack_from('<I', data, 80)[0]
        if len(data) == 84 + count * 50:
            xs = [struct.unpack_from('<f', data, 84 + i * 50 + 12 + j * 12)[0]
                  for i in range(count) for j in range(3)]
        else:
            xs = [float(x) for x in re.findall(r'^\s*vertex\s+(\S+)', data.decode('ascii'), re.M)]
        assert len(xs) >= 3
        assert abs(max(xs) - min(xs) - length) < 1e-5
        result[component['output']] = {'sha256': sha(data), 'length_mm': max(xs) - min(xs)}
    assert len(result) == 2
    return result


with HeadlessBrowser(find_browser()) as browser:
    page = browser.page(url)
    page.evaluate('window.cadexReview.ready', await_promise=True)
    assert page.text('#project-name') == root.name + ' — review'
    assert page.text('#view-kind') == 'RUN wren1-final'
    assert page.text('#view-relation').startswith('HISTORICAL')
    receipt['default_run'] = 'wren1-final'
    for run in ('wren1-checkpoint20', 'wren1-final'):
        r = read(root / 'runs' / run / 'run.json')
        v = read(root / 'runs' / run / 'video.json')['videos'][0]
        assert sha((root / r['policy']['asset']).read_bytes()) == v['policy_sha256']
        page.click('#views li[data-run="' + run + '"]')
        page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
        assert page.text('#view-revision') == r['model']['accepted_revision'] == v['accepted_revision']
        assert page.text('#view-digest') == r['model']['digest']
        assert page.text('#view-relation').startswith('HISTORICAL')
        assert float(page.text("#params tr[data-param='foot_len'] td:nth-child(2)")) == 85
        assert page.evaluate('window.cadexReview.viewer().stats().components') == 8
        assert page.attribute('[data-history=curve]', 'data-points') != '0'
        page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
        assert v['policy_sha256'][:12] in page.text('#videos')
        page.evaluate("window.savedVideo=document.querySelector('#videos video'); savedVideo.muted=true; savedVideo.loop=true; savedVideo.play()", await_promise=True)
        page.wait_for('savedVideo.currentTime > 0.1')
        for _ in range(3):
            page.evaluate('window.cadexReview.refresh()', await_promise=True)
            assert page.text('#view-kind') == 'RUN ' + run
            assert page.evaluate("savedVideo===document.querySelector('#videos video') && !savedVideo.paused")
        download = page.download('#videos a')
        assert sha(download.path.read_bytes()) == v['sha256']
        page.screenshot(out / (run + '.png'))
        receipt['historical'][run] = {'revision': r['model']['accepted_revision'],
            'digest': r['model']['digest'], 'policy_sha256': v['policy_sha256'],
            'download_sha256': v['sha256'], 'seed': v['seed'], 'sim_seconds': v['sim_seconds'],
            'playback_and_polling': True, 'feet': foot_mesh('/api/model/run/' + run, v['accepted_revision'], 85)}
    page.click('#views li[data-view="accepted"]')
    page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
    assert page.text('#view-revision') == manifest['accepted_revision']
    assert float(page.text("#params tr[data-param='foot_len'] td:nth-child(2)")) == 105
    assert float(page.text("#params tr[data-param='policy_on'] td:nth-child(2)")) == 0
    assert page.evaluate('window.cadexReview.viewer().stats().components') == 8
    assert page.evaluate("document.querySelectorAll('#videos video').length") == 0
    page.evaluate('window.cadexReview.refresh()', await_promise=True)
    assert page.text('#view-kind') == 'ACCEPTED NOW'
    receipt['accepted_feet'] = foot_mesh('/api/model/accepted', manifest['accepted_revision'], 105)
    assert page.evaluate('window.cadexReview.viewer().nonBackgroundPixels()') > 1000
    (out / 'accepted-model.png').write_bytes(base64.b64decode(page.evaluate('cadexReview.viewer().png()')))
    page.screenshot(out / 'accepted-page.png')
    page.click('#current-run')
    assert page.text('#view-kind') == 'RUN wren1-final'
    receipt['return_to_current'] = True
assert inventory() == before, 'browser changed retained runs'
receipt['screenshots'] = {f.name: sha(f.read_bytes()) for f in sorted(out.glob('*.png'))}
receipt['ok'] = True
(out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
