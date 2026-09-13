"""Observe a real trainer across private-address dashboard restart.

Run from the checkout with PYTHONPATH=cli:cli/tests pixi run python ... PROJECT RUN.
Only the review servers are stopped; trainer lifetime belongs to its launcher.
"""
import json
from pathlib import Path
import signal
import subprocess
import sys
import time
from cdp_browser import HeadlessBrowser, find_browser

root = Path(sys.argv[1]).resolve()
run = sys.argv[2]
progress = root / 'runs' / run / 'train/progress.json'
host = subprocess.check_output(['tailscale', 'ip', '-4'], text=True).strip()

def trainers():
    result = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            args = (entry / 'cmdline').read_bytes().split(b'\0')
            if len(args) > 1 and args[1].endswith(b'/cadex_train.py'):
                stat = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
                result.append({'pid': int(entry.name), 'start_ticks': stat[19]})
        except OSError:
            pass
    return sorted(result, key=lambda x: x['pid'])

def snapshot():
    return json.loads(progress.read_text())

def start(port):
    proc = subprocess.Popen(['./cadex', 'review', '--project', str(root),
                             '--host', host, '--port', str(port), '--json'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    line = proc.stderr.readline()
    assert ' at http://' in line, line
    return proc, line.split(' at ')[1].split(' ')[0]

def stop(proc):
    if proc.poll() is None:
        proc.send_signal(signal.SIGINT)
    out, err = proc.communicate(timeout=20)
    assert proc.returncode == 0, out + err

result = {'run': run, 'same_machine_private_address': True}
first = second = None
try:
    deadline = time.monotonic() + 300
    while snapshot().get('iteration', -1) < 3:
        assert time.monotonic() < deadline
        time.sleep(.5)
    identity = trainers()
    assert len(identity) == 1, identity
    before = snapshot()
    assert before['state'] == 'training'
    first, url = start(0)
    port = int(url.rstrip('/').rsplit(':', 1)[1])
    with HeadlessBrowser(find_browser()) as browser:
        page = browser.page(url)
        page.evaluate('window.cadexReview.ready', await_promise=True)
        page.click("#views li[data-run='%s']" % run)
        page.wait_for("document.getElementById('telemetry').dataset.state === 'training'")
        page.wait_for("['loaded','missing','error'].includes(document.getElementById('model-status').dataset.state)")
        result["training_model_state"] = page.attribute("#model-status", "data-state")
        result["training_model_message"] = page.text("#model-status")
        revision = page.text('#view-revision')
        assert revision == json.loads((root / 'runs' / run / 'run.json').read_text())['model']['accepted_revision']
        page.evaluate("window.restartMarker='same document'")
        stop(first)
        page.evaluate('window.cadexReview.refresh()', await_promise=True)
        assert page.attribute('#freshness', 'data-state') == 'stale'
        assert trainers() == identity
        second, reopened_url = start(port)
        assert url == reopened_url
        page.wait_for("document.getElementById('freshness').dataset.state === 'live'", timeout=10)
        assert page.evaluate('window.restartMarker') == 'same document'
        assert page.text('#view-revision') == revision
        samples = []
        deadline = time.monotonic() + 30
        while len(samples) < 4:
            assert time.monotonic() < deadline
            current = snapshot()
            assert current['state'] == 'training'
            assert trainers() == identity
            shown = int(page.text('[data-metric=iteration]').split(': ')[1])
            if not samples or shown != samples[-1]['page_iteration']:
                samples.append({'page_iteration': shown, 'file_iteration': current['iteration'],
                                'loss_points': page.attribute('[data-history=loss_curve]', 'data-points')})
            time.sleep(.25)
        after = snapshot()
        assert after['iteration'] > before['iteration']
        assert page.evaluate("performance.getEntriesByType('navigation').length") == 1
        result.update(ok=True, trainer_before=identity, trainer_after=trainers(),
                      iteration_before=before['iteration'], iteration_after=after['iteration'],
                      accepted_revision=revision, samples=samples, stale_during_outage=True,
                      recovered_without_reload=True, server_pids=[first.pid, second.pid])
finally:
    for proc in (first, second):
        if proc is not None and proc.poll() is None:
            stop(proc)
    (root / 'evidence' / (run + '-restart.json')).write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
