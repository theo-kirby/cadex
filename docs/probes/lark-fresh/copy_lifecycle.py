# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Real whole-project copy lifecycle with the original path unavailable (D7).

PYTHONPATH=cli:cli/tests pixi run python copy_lifecycle.py \\
    ORIGINAL COPY OPERATOR_URL LABEL DEFAULT_RUN PARAM=OLD:NEW [PARAM=OLD:NEW ...]

First copy the stopped-writer project to COPY and switch the persistent
operator server to COPY. The copy must still be an intact copy; ORIGINAL must
still carry the OLD values. The script renames ORIGINAL away, edits COPY
through the public CLI, reopens it through two fresh engine processes, checks
a separately started server and the persistent one in headless Chromium
against every retained run (its own revision, digest, parameters, curves,
served meshes and, where recorded, video playback and download), then puts
ORIGINAL back and proves its whole inventory is byte-identical. Nothing named
here belongs to one project: DEFAULT_RUN is the run a fresh visit must select
and the parameter changes are given on the command line.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

from cdp_browser import HeadlessBrowser, find_browser
from test_review_lifecycle import ReviewCommand


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def inventory(root):
    return {str(p.relative_to(root)): sha(p.read_bytes())
            for p in sorted(root.rglob('*')) if p.is_file()}


def values(manifest):
    return {**{s['name']: s['default'] for s in manifest['param_specs']},
            **manifest['param_values']}


def parse_changes(args):
    changes = {}
    for arg in args:
        name, span = arg.split('=')
        old, new = (float(v) for v in span.split(':'))
        changes[name] = [old, new]
    assert changes
    return changes


def check_page(browser, url, root, out, label, default_run, changes):
    page = browser.page(url)
    page.evaluate('window.cadexReview.ready', await_promise=True)
    assert page.text('#project-name') == root.name + ' — review'
    assert page.text('#view-kind') == 'RUN ' + default_run
    runs = sorted(page.evaluate('window.cadexReview.state().runs'))
    assert runs == sorted(p.parent.name for p in (root / 'runs').glob('*/run.json'))
    param = sorted(changes)[0]
    retained = {}
    for run in runs:
        record = read(root / 'runs' / run / 'run.json')
        page.evaluate('window.cadexReview.select(' + json.dumps(run) + ')', await_promise=True)
        page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
        assert page.text('#view-revision') == record['model']['accepted_revision']
        assert page.text('#view-digest') == record['model']['digest']
        assert page.text('#view-relation').startswith('HISTORICAL')
        model = json.loads(urllib.request.urlopen(url + 'api/model/run/' + run).read())
        assert model['revision'] == record['model']['accepted_revision'] and model['available']
        assert page.evaluate('cadexReview.viewer().stats().components') == len(model['components']) > 0
        defaults = {s['name']: s['default'] for s in record['params']['specs']}
        shown = record['params']['values'].get(param, defaults[param])
        column = 2 if param in record['params']['values'] else 3
        assert float(page.text(f"#params tr[data-param='{param}'] td:nth-child({column})")) == shown
        assert shown == changes[param][0], (run, shown)
        points = {h: int(page.attribute('[data-history=' + h + ']', 'data-points'))
                  for h in ('curve', 'loss_curve', 'episode_steps_curve')}
        progress = read(root / 'runs' / run / 'train/progress.json')
        assert points == {h: len(progress[h]) for h in points}
        assert all(n > 0 for n in points.values())
        item = {'revision': record['model']['accepted_revision'], 'digest': record['model']['digest'],
                param: shown, 'curves': points,
                'mesh_sha256': {c['output']: sha(urllib.request.urlopen(url.rstrip('/') + c['mesh']).read())
                                for c in model['components']}}
        video_file = root / 'runs' / run / 'video.json'
        if video_file.exists():
            video = read(video_file)['videos'][0]
            page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
            assert video['policy_sha256'][:12] in page.text('#videos')
            page.evaluate("window.copyVideo=document.querySelector('#videos video'); copyVideo.muted=true; copyVideo.loop=true; copyVideo.play()", await_promise=True)
            page.wait_for('copyVideo.currentTime > 0.1')
            page.evaluate('window.cadexReview.refresh()', await_promise=True)
            assert page.evaluate("copyVideo === document.querySelector('#videos video') && !copyVideo.paused")
            download = page.download('#videos a')
            assert sha(download.path.read_bytes()) == video['sha256']
            item['video'] = {k: video[k] for k in ('sha256', 'policy_sha256', 'seed', 'sim_seconds')}
            item['playback_download_poll'] = True
        retained[run] = item
    page.evaluate("window.cadexReview.select('accepted')", await_promise=True)
    page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
    manifest = read(root / 'script.json')
    assert page.text('#view-revision') == manifest['accepted_revision']
    for name, (_, new) in changes.items():
        assert float(page.text(f"#params tr[data-param='{name}'] td:nth-child(2)")) == new
    assert page.evaluate('cadexReview.viewer().stats().components') == len(retained[default_run]['mesh_sha256'])
    assert page.evaluate("document.querySelectorAll('#videos video').length") == 0
    page.screenshot(out / (label + '-accepted.png'))
    page.click('#current-run')
    assert page.text('#view-kind') == 'RUN ' + default_run
    assert page.text('#view-relation').startswith('HISTORICAL')
    return retained


def main():
    original, copy = (Path(p).resolve() for p in sys.argv[1:3])
    url = sys.argv[3].rstrip('/') + '/'
    label, default_run = sys.argv[4:6]
    changes = parse_changes(sys.argv[6:])
    assert original != copy and original.parent == copy.parent
    unavailable = original.with_name(original.name + '-unavailable-' + label)
    assert not unavailable.exists()
    before = inventory(original)
    copied = inventory(copy)
    assert all(copied.get(k) == v for k, v in before.items()), 'not an intact copy'
    old = read(original / 'script.json')
    assert all(values(old)[k] == v[0] for k, v in changes.items()), values(old)
    out = copy / 'evidence' / label
    out.mkdir(parents=True, exist_ok=False)
    (out / 'original-inventory.json').write_text(json.dumps(before, indent=2) + '\n')
    repo = Path(__file__).resolve().parents[3]
    receipt = {'original': original.name, 'copy': copy.name, 'source_files': len(before),
               'source_inventory_sha256': sha(json.dumps(before, sort_keys=True).encode()),
               'original_revision': old['accepted_revision'], 'original_digest': old['accepted_digest'],
               'default_run': default_run}
    server = None
    original.rename(unavailable)
    try:
        assert not original.exists()
        sets = [a for k, (_, new) in sorted(changes.items()) for a in ('--set', f'{k}={new:g}')]
        for name, args in [('params', ['params', *sets, '--out', str(out / 'export')]), ('render', ['render'])]:
            result = subprocess.run([str(repo / 'cadex'), '--project', str(copy), *args, '--json'],
                                    capture_output=True, text=True, timeout=240)
            (out / (name + '.stdout')).write_text(result.stdout)
            (out / (name + '.stderr')).write_text(result.stderr)
            assert result.returncode == 0, result.stdout + result.stderr
        changed = read(copy / 'script.json')
        assert {k: [values(old)[k], v] for k, v in values(changed).items() if values(old)[k] != v} == changes
        assert changed['accepted_revision'] != old['accepted_revision']
        assert changed['accepted_digest'] != old['accepted_digest']
        # Fresh engine restore, twice, with the source still unavailable.
        subprocess.run([sys.executable, str(repo / 'docs/probes/wren-fresh/restore.py'), str(copy), label + '-restore'],
                       check=True, timeout=240, stdout=subprocess.DEVNULL)
        server = ReviewCommand(copy, 0)
        with HeadlessBrowser(find_browser()) as browser:
            receipt['second_server'] = check_page(browser, server.url, copy, out, 'second', default_run, changes)
            receipt['persistent_server'] = check_page(browser, url, copy, out, 'persistent', default_run, changes)
        assert receipt['second_server'] == receipt['persistent_server']
        assert not original.exists()
        assert inventory(unavailable) == before
        after = inventory(copy)
        retained = {k: v for k, v in before.items() if k.startswith(('runs/', 'assets/'))}
        assert all(after[k] == v for k, v in retained.items())
        receipt.update(copy_revision=changed['accepted_revision'], copy_digest=changed['accepted_digest'],
                       changes=changes, source_unavailable_during_edit_restore_browser=True, original_unchanged=True,
                       retained_files=len(retained), retained_sha256=sha(json.dumps(retained, sort_keys=True).encode()),
                       persistent_url_host=url.split('//')[1].rstrip('/'),
                       persistent_private_address_same_machine=True, product_agent_authorship=False,
                       retraining=False, screenshots={p.name: sha(p.read_bytes()) for p in out.glob('*.png')})
    finally:
        try:
            if server:
                assert server.stop()[0] == 0
        finally:
            unavailable.rename(original)
    assert inventory(original) == before
    receipt['ok'] = True
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
