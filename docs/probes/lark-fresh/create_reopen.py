# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Create/save/reopen check for a fresh, run-less, agent-authored project on
the persistent operator server. Never starts or stops a server.

PYTHONPATH=cli:cli/tests pixi run python docs/probes/lark-fresh/create_reopen.py \\
    URL PROJECT EVIDENCE_NAME [--intact OTHER_PROJECT=SNAPSHOT.json ...]

The project must have been created by one ``cadex -p`` turn whose receipt is
``PROJECT/evidence/create.json`` (its prompt beside it), and the persistent
server must already be serving PROJECT. The probe records the browser's view of
the accepted model and specs, reopens the project **in place** through two
fresh engine processes, then checks the same page after a poll and a fresh
visit against what it recorded before: identity, every parameter, every
component and its served mesh bytes, placements and viewer statistics.

``--intact`` names an earlier project that must be byte-for-byte what a
snapshot (``{relative path: sha256}``, ``.git`` excluded) recorded before the
creation turn started, so the new project provably used none of it.

Writes ``PROJECT/evidence/EVIDENCE_NAME/create_reopen.json`` and screenshots
beside it, and prints the compact receipt.
"""
import base64
import hashlib
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

from cadex_cli.client import CadexdClient, open_project
from cadex_cli.engine import resolve_engine
from cdp_browser import HeadlessBrowser, find_browser

FOREIGN = re.compile(r'wren|reed|mg[-_]?legs|ot5-biped|ot4-|cdx-rl', re.IGNORECASE)


def inventory(root, exclude=None):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file() and '.git' not in p.parts
            and (exclude is None or not p.is_relative_to(exclude))}


def accepted_manifest(root):
    data = json.loads((root / 'script.json').read_text())
    data.pop('updated_at', None)
    for key in ('accepted_attempt', 'latest_candidate'):
        for field in ('attempt_id', 'staging'):
            data.get(key, {}).pop(field, None)
    return data


def fetch(url, path):
    return urllib.request.urlopen(url.rstrip('/') + path, timeout=15).read()


def served_model(url):
    model = json.loads(fetch(url, '/api/model/accepted'))
    assert model['available'] and model['view'] == 'accepted' and model['run'] is None, model
    components = {}
    for component in model['components']:
        assert component['mesh_status'] == 'retained', component
        components[component['name']] = {
            'output': component['output'], 'placement': component['placement'],
            'mesh_sha256': hashlib.sha256(fetch(url, component['mesh'])).hexdigest()}
    return {'revision': model['revision'], 'digest': model['digest'], 'components': components}


def inspect_page(page, root, manifest, expected_values):
    """Assert the accepted view and return what the browser showed."""
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
    listed = page.evaluate("Array.from(document.querySelectorAll('#model-components li[data-component]')).map(n => [n.dataset.component, n.dataset.mesh])")
    assert listed and all(mesh == 'retained' for _, mesh in listed), listed
    assert page.text('#params-note') == 'specs from project manifest at the accepted revision'
    shown = page.evaluate("Array.from(document.querySelectorAll('#params tr[data-param]')).map(r => [r.dataset.param, r.children[1].textContent, r.children[2].textContent])")
    assert {k: float(default if v == '—' else v) for k, v, default in shown} == expected_values, shown
    assert {k: float(v) for k, v, default in shown if v != '—'} == manifest['param_values'], shown
    assert page.attribute('#telemetry', 'data-state') == 'unselected'
    assert page.evaluate("document.querySelectorAll('#videos li').length") == 0
    assert page.attribute('#freshness', 'data-state') == 'live'
    decisions = page.evaluate("Array.from(document.querySelectorAll('#decisions li')).map(n => n.textContent)")
    docs = page.evaluate("Array.from(document.querySelectorAll('#docs li[data-doc]')).map(n => n.dataset.doc)")
    return {'components': [name for name, _ in listed], 'stats': {k: stats[k] for k in ('components', 'triangles', 'bounds', 'style')},
            'drawn_pixels': drawn, 'params_shown': len(shown), 'model_status': page.text('#model-status'),
            'decisions': decisions, 'documents': docs}


def same_view(a, b):
    return {k: a[k] for k in ('components', 'stats', 'params_shown', 'decisions', 'documents')} == \
        {k: b[k] for k in ('components', 'stats', 'params_shown', 'decisions', 'documents')}


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

# The creation turn: one fresh product-agent conversation, accepted, no runs.
creation = json.loads((root / 'evidence' / 'create.json').read_text())
prompt = (root / 'evidence' / 'create.prompt.txt').read_text()
assert creation['ok'] is True and creation.get('error') is None, creation.get('error')
assert Path(creation['project_root']).resolve() == root
manifest = accepted_manifest(root)
assert creation['accepted_revision'] == manifest['accepted_revision'] == creation['revision']
assert creation['digest'] == manifest['accepted_digest']
script = (root / 'script.py').read_text()
assert not FOREIGN.search(script), 'the fresh script names an earlier project or mechanism: ' + FOREIGN.search(script).group(0)
assert not FOREIGN.search(prompt), 'the prompt names an earlier project or mechanism'
assert not (root / 'runs').exists() or not any((root / 'runs').iterdir())
assert not list(root.glob('assets/*.cxpolicy'))
expected_values = {**{p['name']: p['default'] for p in manifest['param_specs']}, **manifest['param_values']}
receipt = {'project': root.name, 'url_host': url.split('//')[1].split('/')[0], 'evidence': name,
           'accepted_revision': manifest['accepted_revision'], 'accepted_digest': manifest['accepted_digest'],
           'creation': {'session_id': creation['session_id'], 'model': creation['model'], 'exit': int((root / 'evidence' / 'create.exit').read_text()),
                        'started': (root / 'evidence' / 'create.started').read_text().strip(),
                        'finished': (root / 'evidence' / 'create.finished').read_text().strip(),
                        'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                        'outputs': sorted(o['name'] if isinstance(o, dict) and 'name' in o else str(o) for o in creation['outputs']),
                        'foreign_references_in_script': False, 'runs': 0, 'policies': 0},
           'param_values': expected_values, 'declared_params': [p['name'] for p in manifest['param_specs']],
           'engine_opens': [], 'intact': {}}
before = inventory(root, exclude=out)

# What the dashboard showed straight after creation, and the documented remedy
# that gave the fresh design its tessellation (both recorded before this probe).
receipt['after_creation'] = {}
for label in ('pre-fix', 'post-fix-pre-render'):
    path = out / (label + '.json')
    if path.exists():
        receipt['after_creation'][label] = json.loads(path.read_text())
rendered = out / 'render.json'
if rendered.exists():
    render = json.loads(rendered.read_text())
    assert render['ok'] and render['accepted_revision'] == manifest['accepted_revision'] and render['digest'] == manifest['accepted_digest'], render
    receipt['after_creation']['render'] = {'command': 'cadex --project PROJECT render --json', 'ok': True,
                                           'accepted_revision_unchanged': True, 'digest_unchanged': True,
                                           'exit': int((out / 'render.exit').read_text()) if (out / 'render.exit').exists() else 0}
receipt['accepted_attempt_staging'] = json.loads((root / 'script.json').read_text())['accepted_attempt']['staging']
receipt['staging_dir_is_accepted_revision'] = Path(receipt['accepted_attempt_staging']).parts[1] == manifest['accepted_revision']

api = json.loads(fetch(url, '/api/project'))
assert api['project'] == root.name, api['project']
assert api['accepted']['available'] and api['accepted']['revision'] == manifest['accepted_revision']
assert api['accepted']['digest'] == manifest['accepted_digest'] and api['runs'] == []
served_before = served_model(url)
assert served_before['revision'] == manifest['accepted_revision'] and served_before['digest'] == manifest['accepted_digest']
receipt['served_model'] = served_before

with HeadlessBrowser(find_browser()) as browser:
    started = time.monotonic()
    page = browser.page(url)
    page.evaluate('window.cadexReview.ready', await_promise=True)
    receipt['ready_seconds'] = round(time.monotonic() - started, 2)
    assert page.evaluate('location.host') == receipt['url_host']
    view_before = inspect_page(page, root, manifest, expected_values)
    assert sorted(view_before['components']) == sorted(served_before['components'])
    assert view_before['stats']['components'] == len(served_before['components'])
    # Real pointer orbit and wheel zoom, then fit back, before the reopen.
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
    assert page.evaluate('window.cadexReview.viewer().nonBackgroundPixels()') > 1000
    receipt['orbit'] = {'default': camera0, 'after_drag': orbited, 'after_zoom': zoomed}
    page.click('#model-fit')
    page.wait_for('window.cadexReview.viewer().camera().distance === ' + repr(camera0['distance']))
    (out / 'before-reopen-accepted.png').write_bytes(base64.b64decode(page.evaluate('cadexReview.viewer().png()')))
    page.screenshot(out / 'before-reopen-page.png')
    receipt['before_reopen'] = view_before

    # Reopen IN PLACE through two fresh engine processes while the page is open.
    staging = root / json.loads((root / 'script.json').read_text())['accepted_attempt']['staging']
    retained_before = inventory(staging)
    for _ in range(2):
        with CadexdClient(resolve_engine()) as client:
            pid = client._process.pid
            reply = open_project(client, root, restore=True)
        assert reply['restore']['matches_accepted'] is True, reply
        assert accepted_manifest(root) == manifest, 'restore changed accepted identity'
        assert inventory(staging) == retained_before, 'restore changed retained accepted artifacts'
        receipt['engine_opens'].append({'pid': pid, 'matches_accepted': True,
                                       'restore': {k: v for k, v in reply['restore'].items() if k != 'outputs'}})
    assert receipt['engine_opens'][0]['pid'] != receipt['engine_opens'][1]['pid']
    receipt['engine_reopen_scope'] = 'in place; retained accepted artifacts byte-checked'
    receipt['retained_attempt_files'] = len(retained_before)

    # The open page, after a poll: same identity, same model, same specs.
    page.evaluate('window.cadexReview.refresh()', await_promise=True)
    state = page.evaluate('window.cadexReview.state()')
    assert state['selected'] == 'accepted' and not state['stale'] and state['error'] is None and state['runs'] == []
    polled = inspect_page(page, root, manifest, expected_values)
    assert same_view(view_before, polled), (view_before, polled)
    receipt['after_reopen_poll'] = polled
    receipt['page_state'] = state
    # A fresh visit after the reopen.
    fresh = browser.page(url)
    fresh.evaluate('window.cadexReview.ready', await_promise=True)
    revisited = inspect_page(fresh, root, manifest, expected_values)
    assert same_view(view_before, revisited), (view_before, revisited)
    assert revisited['drawn_pixels'] > 1000
    (out / 'after-reopen-accepted.png').write_bytes(base64.b64decode(fresh.evaluate('cadexReview.viewer().png()')))
    fresh.screenshot(out / 'after-reopen-page.png')
    receipt['after_reopen_fresh_visit'] = revisited

served_after = served_model(url)
assert served_after == served_before, 'served meshes or placements changed across the reopen'
receipt['served_model_unchanged_after_reopen'] = True
receipt['viewport_png_identical'] = hashlib.sha256((out / 'before-reopen-accepted.png').read_bytes()).hexdigest() == \
    hashlib.sha256((out / 'after-reopen-accepted.png').read_bytes()).hexdigest()
receipt['screenshots'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.png'))}

for other, snapshot in intact.items():
    now = inventory(Path(other))
    assert now == snapshot, f'{other} changed: ' + str(sorted(set(now.items()) ^ set(snapshot.items()))[:5])
    receipt['intact'][Path(other).name] = {'files': len(snapshot), 'unchanged': True}
# Restore replays stage a fresh candidate attempt each time and the store's
# garbage collector prunes unpinned ones; the accepted attempt (pinned) and
# every source, history and document file must be untouched.
after = inventory(root, exclude=out)
changed_paths = sorted({path for path, _ in set(before.items()) ^ set(after.items())})
accepted_staging = receipt['accepted_attempt_staging']
for path in changed_paths:
    assert path == 'script.json' or (path.startswith('script_artifacts/') and not path.startswith(accepted_staging + '/')), path
assert {k: v for k, v in before.items() if not k.startswith('script_artifacts/')} == \
    {k: v for k, v in after.items() if not k.startswith('script_artifacts/') and k != 'script.json'} | {'script.json': before['script.json']}
receipt['files_changed_by_reopen'] = {'script.json': 'script.json' in changed_paths,
                                      'unpinned_attempt_files': len([p for p in changed_paths if p != 'script.json']),
                                      'accepted_attempt_files': 0, 'source_history_document_files': 0}
receipt['retained_files'] = len(before)
receipt['private_address_same_machine'] = True
(out / 'create_reopen.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: receipt[k] for k in ('project', 'url_host', 'accepted_revision', 'accepted_digest', 'declared_params', 'retained_files',
                                          'retained_attempt_files', 'files_changed_by_reopen', 'viewport_png_identical', 'intact', 'ready_seconds')}, indent=2))
print(json.dumps(receipt['before_reopen']['stats'], indent=2))
