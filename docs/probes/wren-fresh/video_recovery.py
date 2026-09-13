# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""D8 browser lifecycle using a disposable full copy of retained project artifacts.

PYTHONPATH=cli:cli/tests pixi run python video_recovery.py URL PROJECT OUTPUT [CURRENT PRIOR]
OUTPUT must be a new directory outside PROJECT. Never changes the operator server.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from urllib.parse import urlsplit

from cadex_cli.review_server import serve
from cdp_browser import HeadlessBrowser, find_browser


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inventory(root):
    return {str(p.relative_to(root)): sha(p.read_bytes())
            for p in root.rglob('*') if p.is_file()}


def play(page, expected):
    page.send("Page.bringToFront")
    page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
    assert page.text('#videos > li') == 'Video files: available (1/1 retained)'
    assert page.text('#view-revision') == expected['accepted_revision']
    assert expected['policy_sha256'][:12] in page.text('#videos')
    page.evaluate("window.testVideo=document.querySelector('#videos video');"
                  "testVideo.muted=true; testVideo.loop=true; testVideo.play()", await_promise=True)
    page.wait_for('testVideo.currentTime > 0.1')
    for _ in range(2):
        page.evaluate('cadexReview.refresh()', await_promise=True)
        assert page.evaluate("testVideo===document.querySelector('#videos video') && !testVideo.paused")
    download = page.download('#videos a')
    assert sha(download.path.read_bytes()) == expected['sha256']
    return {'revision': expected['accepted_revision'], 'policy_sha256': expected['policy_sha256'],
            'download_sha256': expected['sha256'], 'playback_poll_preserved': True}


def main():
    url, project, output = sys.argv[1:4]
    current, prior = sys.argv[4:] or ('wren71-final', 'wren66-final')
    root, out = Path(project).resolve(), Path(output).resolve()
    assert not out.is_relative_to(root)
    out.mkdir(parents=True, exist_ok=False)
    before = inventory(root)
    result = {'schema': 'wren-video-recovery-v1', 'project': root.name,
              'current': current, 'prior': prior, 'faults': [], 'same_machine_private_address': True}
    with HeadlessBrowser(find_browser()) as browser:
        operator = browser.page(url)
        operator.evaluate('cadexReview.ready', await_promise=True)
        assert operator.text('#project-name') == root.name + ' — review'
        assert operator.text('#view-kind') == 'RUN ' + current
        with tempfile.TemporaryDirectory(prefix='review-video-fault-', dir=root.parent) as temp:
            copy = Path(temp) / 'review-fault-copy'
            shutil.copytree(root, copy)
            assert inventory(copy) == before
            run = copy / 'runs' / current
            receipt = run / 'video.json'
            saved_receipt = receipt.read_bytes()
            status = json.loads(saved_receipt)
            video = run / status['videos'][0]['path']
            original = video.read_bytes()
            old = json.loads((copy / 'runs' / prior / 'video.json').read_text())['videos'][0]
            server, thread = serve(copy, urlsplit(url).hostname, 0)
            try:
                page = browser.page(server.url)
                page.evaluate('cadexReview.ready', await_promise=True)
                assert page.text('#project-name') == copy.name + ' — review'
                assert page.text('#view-kind') == 'RUN ' + current
                result['baseline'] = play(page, status['videos'][0])
                for fault, message in [('missing', 'missing'), ('partial', 'digest mismatch'),
                                       ('failed', 'Recorded video render: failed')]:
                    if fault == 'missing':
                        video.unlink()
                    elif fault == 'partial':
                        video.write_bytes(original[:64])
                    else:
                        status.update(state='failed', error='injected encoder failure')
                        receipt.write_text(json.dumps(status))
                    # Observe automatic polling on the already-open page.
                    page.wait_for("document.getElementById('videos').textContent.includes(" + json.dumps(message) + ")")
                    assert page.text('#videos > li') == 'Video files: unavailable (0/1 retained)'
                    assert ('Recorded video render: ' + ('failed' if fault == 'failed' else 'ready')) in page.text('#videos')
                    assert page.text('#view-kind') == 'RUN ' + current
                    assert not page.evaluate("!!document.querySelector('#videos video, #videos a')")
                    assert 'Retry the CLI video command' in page.text('#videos')
                    http = page.evaluate(f"fetch('/video/run/{current}/0').then(r=>r.status)", await_promise=True)
                    assert http == 404
                    observed = {'fault': fault, 'label': page.text('#videos'), 'http_status': http,
                                'unavailable': True, 'cli_guidance': True}
                    page.screenshot(out / (fault + '.png'))
                    # Prior results must actually play while the current output is broken.
                    page.click("#views li[data-run='" + prior + "']")
                    assert page.text('#view-relation').startswith('HISTORICAL')
                    observed['prior'] = play(page, old)
                    assert page.text('#view-kind') == 'RUN ' + prior
                    page.click('#current-run')
                    page.wait_for("document.getElementById('videos').textContent.includes(" + json.dumps(message) + ")")
                    assert page.text('#view-kind') == 'RUN ' + current
                    result['faults'].append(observed)
                video.write_bytes(original)
                receipt.write_bytes(saved_receipt)
                page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
                result['restored'] = play(page, status['videos'][0])
                assert inventory(copy) == before
                result['copy_restored_files'] = len(before)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
        operator.evaluate('cadexReview.refresh()', await_promise=True)
        assert operator.text('#project-name') == root.name + ' — review'
        assert operator.text('#view-kind') == 'RUN ' + current
        result['operator'] = play(operator, status['videos'][0])
        result['operator_unchanged'] = True
    assert inventory(root) == before
    result['original_files_unchanged'] = len(before)
    result['screenshots'] = {p.name: sha(p.read_bytes()) for p in out.glob('*.png')}
    (out / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
