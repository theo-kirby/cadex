"""Measure synthetic retained-video hashing, optionally with browser telemetry.

PYTHONPATH=cli:cli/tests pixi run python docs/probes/video-history/measure.py \
    ~/cadex-projects/video-history --output /tmp/video-history.json --browser

The project directory must not exist. Sparse zero files are hashing workloads,
not playable videos or real training evidence. No original project is touched.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.request

from cadex_cli.review_server import serve
from cdp_browser import HeadlessBrowser, find_browser
from test_review_server import _training_run
from test_review_record import REVISION_B, _manifest

parser = argparse.ArgumentParser()
parser.add_argument('project', type=Path)
parser.add_argument('--output', required=True, type=Path)
parser.add_argument('--browser', action='store_true')
args = parser.parse_args()
root = args.project.resolve()
root.mkdir(parents=True, exist_ok=False)
_manifest(root, REVISION_B)
size = 256 * 1024 * 1024
h = hashlib.sha256()
for _ in range(256):
    h.update(bytes(1024 * 1024))
for index in range(64):
    run = root / 'runs' / f'history-{index:03d}'
    run.mkdir(parents=True)
    with (run / 'synthetic.mp4').open('wb') as stream:
        stream.truncate(size)
    (run / 'run.json').write_text(json.dumps({
        'schema': 'cadex-run-record-v1', 'run': run.name, 'status': 'ok',
        'videos': [{'path': 'synthetic.mp4', 'sha256': h.hexdigest()}],
    }))
active = _training_run(root, 'active', revision=REVISION_B)
progress = active / 'train/progress.json'
def update(iteration):
    data = {'schema': 'cadex-training-progress-v1', 'state': 'training',
            'updated_at': time.time(), 'task_sha256': 't' * 64,
            'iteration': iteration, 'total': 40, 'reward_per_step': 0.1 * iteration,
            'loss': 2.0, 'episode_steps': 30, 'curve': [[iteration, 0.1 * iteration]],
            'loss_curve': [[iteration, 2.0]], 'episode_steps_curve': [[iteration, 30]],
            'checkpoints': []}
    temporary = progress.with_suffix('.partial')
    temporary.write_text(json.dumps(data))
    temporary.replace(progress)
update(0)
result = {'synthetic': True, 'historical_runs': 64, 'bytes_per_video': size,
          'logical_video_bytes': 64 * size, 'http_seconds': []}
server, _ = serve(root, '127.0.0.1', 0)
try:
    for _ in range(3):
        start = time.monotonic()
        with urllib.request.urlopen(server.url + 'api/project') as response:
            review = json.load(response)
        result['http_seconds'].append(time.monotonic() - start)
        assert len(review['runs']) == 65
        assert all(not r['problems'] for r in review['runs'] if r['run'].startswith('history-'))
    if args.browser:
        with HeadlessBrowser(find_browser()) as browser:
            page = browser.page(server.url)
            page.evaluate('window.cadexReview.ready', await_promise=True)
            page.click("#views li[data-run='active']")
            result['browser_update_seconds'] = []
            for iteration in (1, 2, 3):
                start = time.monotonic()
                update(iteration)
                page.wait_for("document.querySelector('[data-metric=iteration]')?.textContent === "
                              + json.dumps(f'iteration: {iteration}'), timeout=90)
                result['browser_update_seconds'].append(time.monotonic() - start)
            assert page.attribute('#telemetry', 'data-state') == 'training'
finally:
    server.shutdown()
    server.server_close()
args.output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
