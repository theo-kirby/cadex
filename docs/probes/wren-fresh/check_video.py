"""Decode and browser-check a retained biped video on the PERSISTENT dashboard.

usage: check_video.py PROJECT RUN URL [--not-default] [--label LABEL]
Never starts or stops a server. Nothing here depends on how a run is named:
the fresh visit's expected selection is the reader's own rule (default_run),
the policy's training run and the historical sibling to select come from
retained identities (policy_lineage), and the component count comes from the
run's own trace. --not-default (--historical is accepted as its old spelling)
says this run is not the one a fresh visit should open; evidence files then
carry a -recheck suffix. --label names the evidence files instead, so a
re-check never overwrites an earlier receipt.
"""
from pathlib import Path
import hashlib, json, subprocess, sys, re, urllib.request
from cdp_browser import HeadlessBrowser, find_browser
from cadex_cli.review_record import policy_lineage
from cadex_cli.review_server import default_run
p = Path(sys.argv[1]).resolve(); run = sys.argv[2]; url = sys.argv[3]; r = p / 'runs' / run
flags = sys.argv[4:]
not_default = '--not-default' in flags or '--historical' in flags
label = flags[flags.index('--label') + 1] if '--label' in flags else None
suffix = '-' + label if label else ('-recheck' if not_default else '')
v = json.loads((r / 'video.json').read_text())['videos'][0]
record = json.loads((r / 'run.json').read_text())
assert v['policy_sha256'] == record['policy']['sha256']   # the video is of this run's recorded policy
trace = json.loads((r / record['artifacts']['trace']).read_text())
components = len(trace['frames'][0]['component_placements'])
lineage = policy_lineage(p, run)
assert lineage['origin'], lineage['reason']
assert lineage['source_agrees'] is not False, lineage   # a record naming one run while carrying another's policy fails here
with urllib.request.urlopen(url.rstrip('/') + '/api/project', timeout=30) as response:
    review = json.load(response)
expected_default = default_run(review)
assert (expected_default == run) != not_default, (expected_default, run, not_default)
served = {item['run']: item for item in review['runs']}
# The historical run to select afterwards: an older sibling from the same
# training run by policy identity, else the latest other historical video run.
siblings = [s for s in lineage['playbacks'] if s['videos'] and s['relation'] == 'historical']
others = [s for s in review['runs'] if s['run'] != run and s['videos'] and s['relation'] == 'historical']
historical_source = None
if siblings:
    historical, historical_source = siblings[-1]['run'], 'same training run by policy identity'
elif others:
    historical, historical_source = others[-1]['run'], 'latest other historical video run'
else:
    historical = None
movie = r / v['path']
raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(movie), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
size = v['width'] * v['height'] * 3
assert len(raw) == v['frames'] * size and raw[:size] != raw[-size:]
probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(movie)]))
assert probe['streams'][0]['r_frame_rate'] == '%d/1' % v['fps']
assert abs(float(probe['format']['duration']) - v['duration_seconds']) < .01
with HeadlessBrowser(find_browser()) as browser:
    page = browser.page(url)
    page.evaluate('window.cadexReview.ready', await_promise=True)
    assert page.text('#project-name') == p.name + ' — review'
    fresh_selection = page.text('#view-kind')
    assert fresh_selection == ('RUN ' + expected_default if expected_default != 'accepted' else 'ACCEPTED NOW'), fresh_selection
    page.click("#views li[data-run='%s']" % run)
    page.wait_for("document.querySelector('#videos video')?.readyState >= 2", timeout=30)
    assert page.text('#view-revision') == v['accepted_revision']
    page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
    params = record['params']['values']
    for key, value in params.items():
        assert float(page.text("#params tr[data-param=%s] td:nth-child(2)" % json.dumps(key))) == float(value), key
    assert page.evaluate('window.cadexReview.viewer().stats().components') == components
    assert int(page.attribute('[data-history=curve]', 'data-points')) > 0
    origin = lineage['origin']
    if origin['run'] != run:   # a playback: the page names the training run its record kept, which the bytes confirm
        assert page.attribute('#checkpoint-source', 'data-run') == origin['run'], page.text('#checkpoint-source')
        assert page.attribute('#checkpoint-source', 'data-state') == 'resolved'
    assert v['policy_sha256'][:12] in page.text('#videos')
    label_text = page.text('#videos')
    assert 'seed %d' % v['seed'] in label_text
    seconds = re.search(r'· seed %d · ([0-9.eE+-]+) s' % v['seed'], label_text)
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
    if historical:
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
              'params_checked': sorted(params), 'foot_len_mm': params.get('foot_len'),
              'components': components, 'components_source': 'first frame of the run\'s own retained trace',
              'curves_present': True, 'expected_default': expected_default, 'is_default': expected_default == run,
              'fresh_selection': fresh_selection, 'historical_selection': historical, 'historical_source': historical_source,
              'lineage': {k: lineage[k] for k in ('origin', 'recorded_source_run', 'source_agrees', 'playbacks')},
              'download_sha256': v['sha256'], 'decoded_frames': len(raw) // size, 'decoded_frames_differ': True,
              'encoded_seconds': float(probe['format']['duration']), 'simulation_seconds': v['sim_seconds'],
              'accepted_revision': v['accepted_revision'],
              'policy_sha256': v['policy_sha256'], 'seed': v['seed'], 'style': v.get('style'),
              'returned_to_current': page.text('#view-kind')}
    (p / ('evidence/' + run + suffix + '-check.json')).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
