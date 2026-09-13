# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Read-only lifecycle review on the persistent URL; no training or restart.

PYTHONPATH=cli:cli/tests pixi run python report.py URL PROJECT EVIDENCE_NAME
Prints a portable receipt; raw screenshots stay in PROJECT/evidence/NAME.
"""
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

from cdp_browser import HeadlessBrowser, find_browser


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    url, project, name = sys.argv[1:]
    root = Path(project).resolve()
    assert Path(name).name == name
    out = root / 'evidence' / name
    out.mkdir(parents=True, exist_ok=False)
    inventory = lambda: {str(p.relative_to(root)): sha(p.read_bytes())
                         for folder in ('runs', 'assets') for p in (root / folder).rglob('*') if p.is_file()}
    before = inventory()
    data = json.load(urllib.request.urlopen(url.rstrip('/') + '/api/project', timeout=30))
    runs = {r['run']: r for r in data['runs']}
    current = next(r['run'] for r in data['runs'] if r['relation'] == 'current')
    assert current == 'wren71-final', 'report describes the completed wren71 repeat'
    names = ['wren1-final', 'wren2-final', 'wren57-retry', 'wren66-checkpoint20', 'wren66-final', current]
    receipt = {'schema': 'wren-lifecycle-review-v1', 'project': root.name, 'current': current,
               'persistent_private_address_same_machine': True, 'run_count': len(runs), 'views': {}}
    with HeadlessBrowser(find_browser()) as browser:
        page = browser.page(url)
        page.evaluate('window.cadexReview.ready', await_promise=True)
        assert page.text('#project-name') == root.name + ' — review'
        assert page.text('#view-kind') == 'RUN ' + current
        for name in names:
            run = runs[name]
            page.click("#views li[data-run='%s']" % name)
            page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'", timeout=60)
            assert page.text('#view-revision') == run['model']['accepted_revision']
            assert page.text('#view-digest') == run['model']['digest']
            assert page.text('#view-relation').startswith('CURRENT' if name == current else 'HISTORICAL')
            assert page.evaluate('window.cadexReview.viewer().stats().components') == 8
            foot = float(page.text("#params tr[data-param='foot_len'] td:nth-child(2)"))
            assert foot == run['params']['values']['foot_len']
            points = {k: int(page.attribute('[data-history=%s]' % k, 'data-points'))
                      for k in ('curve', 'loss_curve', 'episode_steps_curve')}
            assert all(n == len(run['telemetry'][k]) and n > 0 for k, n in points.items())
            docs = {}
            for doc, digest in run['project_docs']['files'].items():
                body = (root / 'runs' / name / run['project_docs']['dir'] / doc).read_bytes()
                assert sha(body) == digest
                page.click('#docs li[data-doc=%s] a' % json.dumps(doc))
                expected = '# ' + doc + ' (snapshot)\nLoaded on open; click the document again to refresh.\n\n' + body.decode()
                page.wait_for('document.getElementById("doc-view").textContent === ' + json.dumps(expected))
                docs[doc] = digest
            page.scroll_into_view('#viewer')
            rect = page.rect('#viewer')
            x, y = rect['x'] + rect['width']/2, rect['y'] + rect['height']/2
            camera = page.evaluate('window.cadexReview.viewer().camera()')
            page.drag(x, y, x + 100, y - 30)
            page.wait_for('window.cadexReview.viewer().camera().yaw !== ' + repr(camera['yaw']))
            page.wheel(x, y, -180)
            page.wait_for('window.cadexReview.viewer().camera().distance < ' + repr(camera['distance']))
            page.click('#model-fit')
            v = run['videos'][0]
            page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
            assert v['policy_sha256'] == run['policy']['sha256']
            assert v['accepted_revision'] == run['model']['accepted_revision']
            assert v['policy_sha256'][:12] in page.text('#videos')
            page.evaluate("window.testVideo=document.querySelector('#videos video'); testVideo.muted=true; testVideo.loop=true; testVideo.play()", await_promise=True)
            page.wait_for('testVideo.currentTime > 0.1')
            for _ in range(3):
                page.evaluate('window.cadexReview.refresh()', await_promise=True)
                assert page.text('#view-kind') == 'RUN ' + name
                assert page.evaluate("testVideo === document.querySelector('#videos video') && !testVideo.paused")
            download = page.download('#videos a')
            assert sha(download.path.read_bytes()) == sha((root / 'runs' / name / v['path']).read_bytes()) == v['sha256']
            page.screenshot(out / (name + '.png'))
            receipt['views'][name] = {'revision': run['model']['accepted_revision'], 'digest': run['model']['digest'],
                'foot_len_mm': foot, 'components': 8, 'history_points': points, 'telemetry_state': run['telemetry']['state'],
                'documents': docs, 'relation': run['relation'], 'video_sha256': v['sha256'],
                'policy_sha256': v['policy_sha256'], 'seed': v['seed'], 'sim_seconds': v['sim_seconds'],
                'style': v['style'], 'style_sha256': v['style_sha256'], 'playback_download_poll_preserved': True, 'orbit_zoom': True,
                'screenshot_sha256': sha((out / (name + '.png')).read_bytes())}
        page.click('#current-run')
        page.wait_for('document.getElementById("view-kind").textContent === ' + json.dumps('RUN ' + current))
        receipt['return_to_current'] = True
        receipt['navigations'] = page.evaluate("performance.getEntriesByType('navigation').length")
        assert receipt['navigations'] == 1
    assert inventory() == before
    receipt['run_asset_files_unchanged'] = len(before)
    (out / 'report.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
