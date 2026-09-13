# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Observe a real trainer across a persistent dashboard restart.

PYTHONPATH=cli:cli/tests pixi run python restart_training.py URL PROJECT RUN HISTORY
Run alongside train.py. Waits for real updates, opens live and historical pages,
restarts only cadex-operator-review, and records automatic recovery and playback.
Failure never signals the independently bounded trainer. Linux /proc supplies
PID plus process start ticks, and counts all real cadex_train.py interpreters.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from cdp_browser import HeadlessBrowser, find_browser


def trainers():
    found = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            argv = (p / 'cmdline').read_bytes().split(b'\0')
            if len(argv) > 1 and Path(argv[1].decode()).name == 'cadex_train.py':
                # Fields after comm start with field 3; starttime is field 22.
                ticks = (p / 'stat').read_text().rsplit(')', 1)[1].split()[19]
                found.append({'pid': int(p.name), 'start_ticks': ticks})
        except (OSError, UnicodeError):
            continue
    return sorted(found, key=lambda x: x['pid'])


def main(url, project, run, history):
    root = Path(project).resolve()
    progress = root / 'runs' / run / 'train/progress.json'
    out = root / 'evidence' / (run + '-restart-training.json')
    result = {'schema': 'cadex-training-restart-evidence-v1', 'project': root.name,
              'run': run, 'history': history, 'persistent_port': 8765,
              'private_address_same_machine': True, 'samples': []}
    def read():
        return json.loads(progress.read_text())
    def pid():
        return subprocess.check_output(['systemctl', '--user', 'show', 'cadex-operator-review', '-p', 'MainPID', '--value'], text=True).strip()
    def iteration(page):
        return int(page.text('[data-metric=iteration]').split(': ')[1])
    try:
        deadline = time.monotonic() + 420
        while not progress.exists() or read().get('iteration', -1) < 4:
            assert time.monotonic() < deadline, 'training did not reach iteration 4'
            time.sleep(.25)
        before = read()
        assert before['state'] == 'training'
        original = trainers()
        assert len(original) == 1, original
        result['trainers_before'] = original
        record = json.loads((root / 'runs' / run / 'run.json').read_text())
        old = json.loads((root / 'runs' / history / 'video.json').read_text())['videos'][0]
        result['revision'] = record['model']['accepted_revision']
        with HeadlessBrowser(find_browser()) as browser:
            live = browser.page(url)
            live.evaluate('window.cadexReview.ready', await_promise=True)
            live.wait_for("document.getElementById('model-status').dataset.state === 'loaded'", timeout=60)
            assert live.text('#project-name') == root.name + ' — review'
            assert live.text('#view-kind') == 'RUN ' + run
            assert live.text('#view-revision') == result['revision']
            live.wait_for("document.getElementById('telemetry').dataset.state === 'training'")
            past = browser.page(url)
            past.evaluate('window.cadexReview.ready', await_promise=True)
            past.evaluate('window.cadexReview.select(%s)' % json.dumps(history), await_promise=True)
            past.wait_for("document.querySelector('#videos video')?.readyState >= 2")
            past.evaluate("window.keptVideo = document.querySelector('#videos video'); keptVideo.muted = true; keptVideo.loop = true; keptVideo.play()", await_promise=True)
            past.wait_for('!keptVideo.paused && keptVideo.currentTime > 0.1')
            history_revision = past.text('#view-revision')
            assert past.text('#view-relation').startswith('HISTORICAL')
            result['historical_revision'] = history_revision
            result['historical_video_sha256'] = old['sha256']
            start_iteration = iteration(live)
            old_pid = pid()
            started = time.monotonic()
            # No manual refresh: recovery and live data use the page's own poll.
            subprocess.run(['systemctl', '--user', 'restart', 'cadex-operator-review'], check=True, timeout=60)
            result['restart_command_seconds'] = round(time.monotonic() - started, 3)
            new_pid = pid()
            assert new_pid not in ('0', old_pid)
            result['service_pids'] = [old_pid, new_pid]
            seen = {}
            recovered = None
            while len(result['samples']) < 7:
                assert time.monotonic() - started < 90, 'seven resumed updates not observed'
                data = read()
                assert data['state'] == 'training'
                assert trainers() == original, 'trainer stopped or duplicated'
                seen[data['iteration']] = data['updated_at']
                shown = iteration(live)
                if shown > start_iteration and live.attribute('#freshness', 'data-state') == 'live':
                    if recovered is None:
                        recovered = round(time.monotonic() - started, 3)
                    if shown in seen and not any(s['iteration'] == shown for s in result['samples']):
                        lag = round(time.time() - seen[shown], 3)
                        assert 0 <= lag < 5, lag
                        result['samples'].append({'iteration': shown, 'commit_to_page_seconds': lag,
                            'reward': live.text('[data-metric=reward_per_step]'), 'loss': live.text('[data-metric=loss]'),
                            'episode_steps': live.text('[data-metric=episode_steps]'),
                            'points': [int(live.attribute('[data-history=' + k + ']', 'data-points')) for k in ('curve', 'loss_curve', 'episode_steps_curve')]})
                time.sleep(.1)
            assert recovered < 5, recovered
            result['first_resumed_update_seconds'] = recovered
            result['iteration_before'] = start_iteration
            result['iteration_after'] = iteration(live)
            result['trainers_after'] = trainers()
            assert live.text('#view-kind') == 'RUN ' + run
            assert live.text('#view-revision') == result['revision']
            assert past.text('#view-kind') == 'RUN ' + history
            assert past.text('#view-revision') == history_revision
            assert past.evaluate("keptVideo === document.querySelector('#videos video') && !keptVideo.paused && keptVideo.readyState >= 2")
            t = past.evaluate('keptVideo.currentTime')
            past.wait_for('keptVideo.currentTime !== ' + str(t))
            for page in (past, live):
                assert page.evaluate("performance.getEntriesByType('navigation').length") == 1
            download = past.download('#videos a')
            assert hashlib.sha256(download.path.read_bytes()).hexdigest() == old['sha256']
            fresh = browser.page(url)
            fresh.evaluate('window.cadexReview.ready', await_promise=True)
            assert fresh.text('#view-kind') == 'RUN ' + run
            assert fresh.text('#view-revision') == result['revision']
            past.click('#current-run')
            past.wait_for("document.getElementById('view-kind').textContent === " + json.dumps('RUN ' + run))
            result.update(historical_playback_preserved=True, historical_download_verified=True,
                          no_navigation=True, fresh_default='RUN ' + run, return_to_current='RUN ' + run)
            live.screenshot(root / 'evidence' / (run + '-restart-live.png'))
            assert read()['state'] == 'training' and trainers() == original
            result['ok'] = True
    except Exception as exc:
        result['failure'] = repr(exc)
        raise
    finally:
        out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main(*sys.argv[1:])
