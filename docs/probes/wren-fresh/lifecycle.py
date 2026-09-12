# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Reopen a fresh, run-less project through the engine and inspect it on the
persistent operator server; never starts or stops a server.

PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/lifecycle.py \\
    URL PROJECT EVIDENCE_NAME [--intact OTHER_PROJECT=SNAPSHOT.json ...]

``--intact`` names a project that must be byte-for-byte what a snapshot (a
``{relative path: sha256}`` map, ``.git`` excluded) recorded before the switch.
Writes ``PROJECT/evidence/EVIDENCE_NAME/lifecycle.json`` and a screenshot beside
it, and prints the compact receipt.
"""
import base64
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

from cadex_cli.client import CadexdClient, open_project
from cadex_cli.engine import resolve_engine
from cdp_browser import HeadlessBrowser, find_browser


def inventory(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file() and '.git' not in p.parts}


def accepted_manifest(root):
    data = json.loads((root / 'script.json').read_text())
    data.pop('updated_at', None)
    for key in ('accepted_attempt', 'latest_candidate'):
        for field in ('attempt_id', 'staging'):
            data.get(key, {}).pop(field, None)
    return data


args = sys.argv[1:]
intact = {}
while '--intact' in args:
    i = args.index('--intact')
    other, snapshot = args[i + 1].split('=', 1)
    intact[str(Path(other).resolve())] = json.loads(Path(snapshot).read_text())
    del args[i:i + 2]
url, project, name = args
root = Path(project).resolve()
out = root / 'evidence' / name
out.mkdir(parents=True, exist_ok=True)
manifest = accepted_manifest(root)
before = inventory(root)
receipt = {'project': root.name, 'url_host': url.split('//')[1].split('/')[0], 'evidence': name,
           'accepted_revision': manifest['accepted_revision'], 'accepted_digest': manifest['accepted_digest'],
           'param_values': manifest['param_values'], 'engine_opens': [], 'intact': {}}

# Save/reopen: the accepted revision restores through two fresh engine processes.
for _ in range(2):
    with CadexdClient(resolve_engine()) as client:
        pid = client._process.pid
        reply = open_project(client, root, restore=True)
    assert reply['restore']['matches_accepted'] is True, reply
    receipt['engine_opens'].append({'pid': pid, 'matches_accepted': True,
                                    'restore': {k: v for k, v in reply['restore'].items() if k != 'outputs'}})
    assert inventory(root) == before, 'restore changed retained inputs'
    assert accepted_manifest(root) == manifest, 'restore changed the accepted manifest'
assert receipt['engine_opens'][0]['pid'] != receipt['engine_opens'][1]['pid']

# The server's own view of the project, before the page reads it.
api = json.loads(urllib.request.urlopen(url.rstrip('/') + '/api/review', timeout=15).read())
assert api['accepted']['available'] and api['accepted']['revision'] == manifest['accepted_revision']
assert api['accepted']['digest'] == manifest['accepted_digest']
assert api['runs'] == [], api['runs']
receipt['api_runs'] = 0

with HeadlessBrowser(find_browser()) as browser:
    started = time.monotonic()
    page = browser.page(url)
    page.evaluate('window.cadexReview.ready', await_promise=True)
    receipt['ready_seconds'] = round(time.monotonic() - started, 2)
    assert page.evaluate('location.host') == receipt['url_host']
    assert page.text('#project-name') == root.name + ' — review'
    assert page.text('#view-kind') == 'ACCEPTED NOW'
    assert page.text('#view-relation') == '' and page.text('#view-status') == ''
    assert page.text('#view-revision') == manifest['accepted_revision']
    assert page.text('#view-digest') == manifest['accepted_digest']
    assert page.text('#view-identity-source') == 'project manifest (script.json), read-only'
    assert page.text('#current-run') == 'Current run: accepted'
    assert '0 run(s)' in page.text('#accepted-line')
    assert page.evaluate("document.querySelectorAll('#views li[data-run]').length") == 0
    assert page.attribute("#views li[data-view='accepted']", 'data-selected') == 'true'
    page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
    stats = page.evaluate('window.cadexReview.viewer().stats()')
    assert stats['components'] > 0 and stats['triangles'] > 0
    drawn = page.evaluate('window.cadexReview.viewer().nonBackgroundPixels()')
    assert drawn > 1000, 'the model is not drawn'
    receipt['model'] = {'components': stats['components'], 'triangles': stats['triangles'],
                        'bounds': stats['bounds'], 'style': stats['style'], 'drawn_pixels': drawn,
                        'status': page.text('#model-status')}
    assert page.text('#params-note') == 'specs from project manifest at the accepted revision'
    shown = page.evaluate("Array.from(document.querySelectorAll('#params tr[data-param]')).map(r => [r.dataset.param, r.children[1].textContent])")
    assert {k: float(v) for k, v in shown} == {k: float(v) for k, v in manifest['param_values'].items()}, shown
    receipt['params_shown'] = len(shown)
    assert page.attribute('#telemetry', 'data-state') == 'unselected'
    assert page.text('#telemetry').startswith('Training telemetry: unselected')
    assert page.text("#training tr[data-key='training'] td") == 'select a run to see its training and rollout'
    assert 'select a run to see its retained artifacts' in page.text('#artifacts')
    assert page.evaluate("document.querySelectorAll('#videos li').length") == 0
    assert page.attribute('#freshness', 'data-state') == 'live'
    docs = page.evaluate("Array.from(document.querySelectorAll('#docs li[data-doc]')).map(n => n.dataset.doc)")
    receipt['documents'] = docs
    # Real pointer orbit and wheel zoom on the accepted model, then fit back.
    page.scroll_into_view('#viewer')
    rect = page.rect('#viewer')
    cx, cy = rect['x'] + rect['width'] / 2, rect['y'] + rect['height'] / 2
    camera0 = page.evaluate('window.cadexReview.viewer().camera()')
    page.drag(cx, cy, cx + 150, cy - 40)
    orbited = page.wait_for("(function(){var c=window.cadexReview.viewer().camera();"
                            f"return (c.yaw !== {camera0['yaw']} && c.pitch !== {camera0['pitch']}) && c}})()")
    assert orbited['distance'] == camera0['distance']
    page.wheel(cx, cy, -240)
    zoomed = page.wait_for("(function(){var c=window.cadexReview.viewer().camera();"
                           f"return c.distance < {orbited['distance']} && c}})()")
    drawn_after = page.evaluate('window.cadexReview.viewer().nonBackgroundPixels()')
    assert drawn_after > 1000
    receipt['orbit'] = {'default': camera0, 'after_drag': orbited, 'after_zoom': zoomed, 'drawn_pixels': drawn_after}
    page.click('#model-fit')
    page.wait_for('window.cadexReview.viewer().camera().distance === ' + repr(camera0['distance']))
    shot = out / 'persistent-accepted.png'
    shot.write_bytes(base64.b64decode(page.evaluate('cadexReview.viewer().png()')))
    page.screenshot(out / 'persistent-page.png')
    receipt['screenshots'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (shot, out / 'persistent-page.png')}
    # A poll keeps the same identity and the same empty run state.
    page.evaluate('window.cadexReview.refresh()', await_promise=True)
    state = page.evaluate('window.cadexReview.state()')
    assert state['selected'] == 'accepted' and not state['stale'] and state['error'] is None and state['runs'] == []
    assert page.text('#view-revision') == manifest['accepted_revision']
    receipt['page_state'] = state

for other, snapshot in intact.items():
    now = inventory(Path(other))
    assert now == snapshot, f'{other} changed: ' + str(sorted(set(now.items()) ^ set(snapshot.items()))[:5])
    receipt['intact'][Path(other).name] = {'files': len(snapshot), 'unchanged': True}
assert inventory(root) == before
receipt['retained_files'] = len(before)
receipt['private_address_same_machine'] = True
(out / 'lifecycle.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: receipt[k] for k in ('project', 'url_host', 'accepted_revision', 'api_runs', 'params_shown',
                                          'retained_files', 'intact', 'ready_seconds')}, indent=2))
