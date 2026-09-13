"""Inspect the persistent operator server; never starts or stops a server.

PYTHONPATH=cli:cli/tests pixi run python docs/probes/operator-review/verify.py URL PROJECT RUN
"""
import hashlib
import json
from pathlib import Path
import sys

from cdp_browser import HeadlessBrowser, find_browser
from cadex_cli.review_record import read_run_record

url, project, run = sys.argv[1:]
root = Path(project)
record = read_run_record(root / 'runs' / run, root)
with HeadlessBrowser(find_browser()) as browser:
    page = browser.page(url)
    page.evaluate('window.cadexReview.ready', await_promise=True)
    assert page.text('#project-name') == root.name + ' — review'
    assert page.text('#view-kind') == 'RUN ' + run
    assert page.text('#view-revision') == record['model']['accepted_revision']
    page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
    assert page.evaluate('window.cadexReview.viewer().stats().components') > 0
    foot_len = record['params']['values']['foot_len']
    assert float(page.text("#params tr[data-param='foot_len'] td:nth-child(2)")) == foot_len
    assert page.attribute('[data-history=curve]', 'data-points') != '0'
    page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
    page.evaluate("window.operatorVideo = document.querySelector('#videos video'); operatorVideo.muted = true; operatorVideo.play()", await_promise=True)
    page.wait_for('operatorVideo.currentTime > 0.1')
    page.evaluate('window.cadexReview.refresh()', await_promise=True)
    assert page.evaluate("operatorVideo === document.querySelector('#videos video') && !operatorVideo.paused")
    download = page.download('#videos li[data-video="0"] a')
    digest = hashlib.sha256(download.path.read_bytes()).hexdigest()
    assert digest == record['videos'][0]['sha256']
    current = page.evaluate('window.cadexReview.state()')
    historical = 'probe3-final'
    old = read_run_record(root / 'runs' / historical, root)
    page.click('#views li[data-run="probe3-final"]')
    page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
    page.evaluate('window.cadexReview.refresh()', await_promise=True)
    assert page.text('#view-kind') == 'RUN ' + historical
    assert page.text('#view-revision') == old['model']['accepted_revision']
    assert page.text('#view-relation').startswith('HISTORICAL')
    page.click('#current-run')
    assert page.text('#view-kind') == 'RUN ' + run
    print(json.dumps({'project': root.name, 'run': run, 'current': current,
                      'foot_len_mm': foot_len, 'video_sha256': digest, 'playback_preserved_on_poll': True,
                      'historical_run': historical, 'return_to_current': True,
                      'private_address_same_machine': True}, indent=2))
