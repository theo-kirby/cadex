"""Cancel a retained-video download FROM THE BROWSER on the PERSISTENT dashboard, then download it again.

usage: browser_abort_download.py PROJECT RUN URL SERVER_LOG [--label LABEL] [--throughput BYTES_PER_S]
Never starts or stops a server. Opens URL in headless Chromium, plays the
run's first retained video, then throttles the page's network so the real
file — a few KB, written whole by the server before any cancel can reach it —
takes seconds to arrive in the browser, starts its download and cancels it
through the browser's own download manager part-way through. Then lifts the
throttle and downloads the same file fresh, byte-identical, while the page
kept polling and the video kept playing. Reports what the browser received
before cancelling, that the server's log gained no traceback, and the fresh
download's identity. Prints one JSON object; the caller composes the receipt.
"""
from pathlib import Path
import hashlib, json, sys, time
from cdp_browser import HeadlessBrowser, find_browser
from cadex_cli.review_server import default_run
import urllib.request

project = Path(sys.argv[1]).resolve(); run = sys.argv[2]; url = sys.argv[3].rstrip('/') + '/'; log = Path(sys.argv[4])
flags = sys.argv[5:]
label = flags[flags.index('--label') + 1] if '--label' in flags else 'abort'
throughput = int(flags[flags.index('--throughput') + 1]) if '--throughput' in flags else 1024
video = json.loads((project / 'runs' / run / 'video.json').read_text())['videos'][0]
movie = project / 'runs' / run / video['path']
retained = movie.read_bytes()
assert hashlib.sha256(retained).hexdigest() == video['sha256']
with urllib.request.urlopen(url + 'api/project', timeout=30) as response:
    review = json.load(response)
expected_default = default_run(review)
log_before = log.read_text()

with HeadlessBrowser(find_browser()) as browser:
    page = browser.page(url)
    page.evaluate('window.cadexReview.ready', await_promise=True)
    assert page.text('#project-name') == project.name + ' — review'
    fresh_selection = page.text('#view-kind')
    assert fresh_selection == 'RUN ' + expected_default, (fresh_selection, expected_default)
    if expected_default != run:
        page.click("#views li[data-run='%s']" % run)
    page.wait_for("document.querySelector('#videos video')?.readyState >= 2", timeout=30)
    assert page.text('#view-kind') == 'RUN ' + run
    assert video['policy_sha256'][:12] in page.text('#videos')
    page.evaluate("window.testVideo=document.querySelector('#videos video'); testVideo.muted=true; testVideo.loop=true; testVideo.play()", await_promise=True)
    page.wait_for('testVideo.currentTime > 0.1')
    page.evaluate("window.polls=0; window.originalFetch=window.fetch;"
                  "window.fetch=async (...args) => { const response=await originalFetch(...args);"
                  "if(String(args[0]).includes('api/project')) polls++; return response; }")
    directory = browser.download_dir()
    page.send('Browser.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': str(directory), 'eventsEnabled': True})
    page.send('Network.enable')
    page.send('Network.emulateNetworkConditions', {'offline': False, 'latency': 0,
                                                    'downloadThroughput': throughput, 'uploadThroughput': -1})
    t0 = time.monotonic()
    page.click('#videos a')
    begin = browser.wait_event('Browser.downloadWillBegin', page.session, timeout=30)
    guid = begin['guid']
    partial = browser.wait_event('Browser.downloadProgress', page.session, timeout=60,
                                 predicate=lambda p: p.get('guid') == guid and
                                 (p.get('state') != 'inProgress' or 0 < p.get('receivedBytes', 0) < p.get('totalBytes', 0)))
    state_at_cancel = partial['state']
    cancelled_after = None
    if partial['state'] == 'inProgress':
        page.send('Browser.cancelDownload', {'guid': guid})
        final = browser.wait_event('Browser.downloadProgress', page.session, timeout=30,
                                   predicate=lambda p: p.get('guid') == guid and p.get('state') in ('completed', 'canceled'))
        state_at_cancel = final['state']
        cancelled_after = time.monotonic() - t0
    else:
        final = partial
    cancel = {'download_url_path': begin['url'].split(url.rstrip('/'), 1)[-1], 'suggested_filename': begin['suggestedFilename'],
              'browser_received_bytes_at_cancel': int(partial.get('receivedBytes', 0)),
              'total_bytes': int(partial.get('totalBytes', 0)), 'final_state': final['state'],
              'seconds_from_click_to_cancel': None if cancelled_after is None else round(cancelled_after, 3),
              'throttle_bytes_per_second': throughput}
    assert cancel['final_state'] == 'canceled', cancel
    assert 0 < cancel['browser_received_bytes_at_cancel'] < cancel['total_bytes'] == len(retained), cancel
    polls_at_cancel = page.evaluate('polls')
    page.send('Network.emulateNetworkConditions', {'offline': False, 'latency': 0,
                                                    'downloadThroughput': -1, 'uploadThroughput': -1})
    # Two automatic polls after the cancellation, never refresh() from here.
    polls_after_cancel = page.wait_for(f'polls >= {polls_at_cancel + 2} && polls', timeout=20)
    assert page.attribute('#freshness', 'data-state') == 'live'
    assert page.text('#view-kind') == 'RUN ' + run
    assert page.evaluate("testVideo===document.querySelector('#videos video') && !testVideo.paused && testVideo.currentTime > 0.1")
    leftovers = sorted(p.name for p in directory.iterdir())
    download = page.download('#videos a', timeout=60)
    fresh = download.path.read_bytes()
    assert download.received_bytes == download.total_bytes == len(retained) == len(fresh)
    assert download.path.name == movie.name, download.path.name
    assert hashlib.sha256(fresh).hexdigest() == video['sha256']
    assert page.evaluate("testVideo===document.querySelector('#videos video') && !testVideo.paused")
    page.evaluate("document.querySelector('#videos').scrollIntoView()")
    page.screenshot(project / 'evidence' / f'{run}-{label}-browser.png')
    returned = page.text('#view-kind')

log_after = log.read_text()
added = log_after[len(log_before):]
assert 'Traceback' not in log_after and 'Exception occurred' not in log_after, log_after[-2000:]
result = {'run': run, 'video': movie.name, 'bytes': len(retained), 'sha256': video['sha256'],
          'fresh_selection': fresh_selection, 'expected_default': expected_default,
          'browser_playback_before_cancel': True, 'cancel': cancel,
          'polls_before_cancel': polls_at_cancel, 'polls_after_cancel': polls_after_cancel, 'freshness_after_cancel': 'live',
          'playback_kept_through_cancel_and_fresh_download': True,
          'partial_files_left_in_download_dir': leftovers,
          'fresh_download': {'filename': download.path.name, 'bytes': download.received_bytes,
                             'sha256': hashlib.sha256(fresh).hexdigest(), 'matches_retained': fresh == retained},
          'server_log': log.name, 'server_log_lines_before': log_before.count('\n'),
          'server_log_lines_added': added.count('\n'), 'server_log_has_traceback': False,
          'view_after': returned}
(project / 'evidence' / f'{run}-{label}-abort.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
