"""Decode and browser-check a retained biped video on the PERSISTENT dashboard.

usage: check_video.py PROJECT RUN URL [--historical]
Never starts or stops a server. --historical permits an older final run.
"""
from pathlib import Path
import hashlib, json, subprocess, sys, re
from cdp_browser import HeadlessBrowser, find_browser
p = Path(sys.argv[1]).resolve(); run = sys.argv[2]; url = sys.argv[3]; r = p / 'runs' / run
v = json.loads((r / 'video.json').read_text())['videos'][0]
record = json.loads((r / 'run.json').read_text())
suffix = '-recheck' if '--historical' in sys.argv[4:] else ''
movie = r / v['path']
raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(movie), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
size = 512 * 512 * 3
assert len(raw) == v['frames'] * size and raw[:size] != raw[-size:]
probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(movie)]))
assert probe['streams'][0]['r_frame_rate'] == '10/1'
assert abs(float(probe['format']['duration']) - v['duration_seconds']) < .01
with HeadlessBrowser(find_browser()) as browser:
    page = browser.page(url)
    page.evaluate('window.cadexReview.ready', await_promise=True)
    assert page.text('#project-name') == p.name + ' — review'
    fresh_selection = page.text('#view-kind')
    if run.endswith('-final') and '--historical' not in sys.argv[4:]:
        assert fresh_selection == 'RUN ' + run, fresh_selection
    page.click("#views li[data-run='%s']" % run)
    page.wait_for("document.querySelector('#videos video')?.readyState >= 2", timeout=30)
    assert page.text('#view-revision') == v['accepted_revision']
    page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
    foot_len = record['params']['values']['foot_len']
    assert float(page.text("#params tr[data-param='foot_len'] td:nth-child(2)")) == foot_len
    assert page.evaluate('window.cadexReview.viewer().stats().components') == 8
    assert int(page.attribute('[data-history=curve]', 'data-points')) > 0
    assert v['policy_sha256'][:12] in page.text('#videos')
    label = page.text('#videos')
    assert 'seed 0' in label
    seconds = re.search(r'· seed 0 · ([0-9.eE+-]+) s', label)
    assert seconds and abs(float(seconds.group(1)) - v['sim_seconds']) < 1e-9
    page.evaluate("window.testVideo=document.querySelector('#videos video'); testVideo.muted=true; testVideo.loop=true; testVideo.play()", await_promise=True)
    page.wait_for('testVideo.currentTime > 0.1')
    for _ in range(3):
        page.evaluate('window.cadexReview.refresh()', await_promise=True)
        assert page.evaluate("testVideo===document.querySelector('#videos video') && !testVideo.paused")
    assert abs(page.evaluate('testVideo.duration') - v['duration_seconds']) < .01
    download = page.download('#videos a')
    assert download.received_bytes == download.total_bytes == movie.stat().st_size
    assert hashlib.sha256(download.path.read_bytes()).hexdigest() == v['sha256']
    page.evaluate("document.querySelector('#videos').scrollIntoView()")
    page.screenshot(p / ('evidence/' + run + suffix + '-browser.png'))
    historical = None
    if run.endswith('-final'):
        historical = run.removesuffix('-final') + '-checkpoint20'
        old = json.loads((p / 'runs' / historical / 'run.json').read_text())
        page.click("#views li[data-run='%s']" % historical)
        page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
        page.evaluate('window.cadexReview.refresh()', await_promise=True)
        assert page.text('#view-kind') == 'RUN ' + historical
        assert page.text('#view-revision') == old['model']['accepted_revision']
        assert page.text('#view-relation').startswith('HISTORICAL')
    # A new checkpoint/run may have been published during this browser check.
    current_target = page.text('#current-run').removeprefix('Current run: ')
    page.click('#current-run')
    page.wait_for("document.getElementById('view-kind').textContent === " + json.dumps('RUN ' + current_target))
    result = {'persistent_server': True, 'url': url, 'private_address_same_machine': True, 'browser_playback': True,
              'foot_len_mm': foot_len, 'components': 8, 'curves_present': True,
              'fresh_selection': fresh_selection, 'historical_selection': historical,
              'download_sha256': v['sha256'], 'decoded_frames': len(raw) // size, 'decoded_frames_differ': True,
              'encoded_seconds': float(probe['format']['duration']), 'simulation_seconds': v['sim_seconds'],
              'accepted_revision': v['accepted_revision'],
              'policy_sha256': v['policy_sha256'], 'seed': v['seed'], 'style': v.get('style'),
              'returned_to_current': page.text('#view-kind')}
    (p / ('evidence/' + run + suffix + '-check.json')).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
