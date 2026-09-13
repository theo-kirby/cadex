# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Controlled encoder failure during train.py's real GPU experiment.

usage: render_failure.py PROJECT TRAINING_RUN URL PRIOR_RUN
PRIOR_RUN is an earlier run with a retained video that must stay playable
while the checkpoint re-render is failed; the project decides which, so the
same observer serves any fresh project (Wren, Lark, ...).

Only the render subprocess sees a temporary ffmpeg that exits 73. No project
artifact or trainer telemetry is edited to simulate failure. The ordinary
renderer publishes its own failure receipt; this observer then retries normally.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from cdp_browser import HeadlessBrowser, find_browser
from video_recovery import play
from restart_training import trainers


def exercise(project, training_run, checkpoint_run, url, trainer, prior):
    project = Path(project)
    progress = project / 'runs' / training_run / 'train/progress.json'
    receipt = project / 'runs' / checkpoint_run / 'video.json'
    output = project / 'evidence' / (checkpoint_run + '-render-failure.json')
    read = lambda path: json.loads(path.read_text())
    original_trainers = trainers()
    assert len(original_trainers) == 1, original_trainers
    result = {'trainers_before': original_trainers, 'project': project.name, 'training_run': training_run,
              'checkpoint_run': checkpoint_run, 'prior_run': prior, 'persistent_server': True,
              'private_address_same_machine': True, 'fault': 'encoder exits 73',
              'before': read(progress), 'observations': []}
    try:
        assert trainer.poll() is None and result['before']['state'] == 'training'
        with tempfile.TemporaryDirectory(prefix='cadex-encoder-fault-') as temp:
            encoder = Path(temp) / 'ffmpeg'
            encoder.write_text('#!/bin/sh\nexit 73\n')
            encoder.chmod(0o700)
            started = time.time()
            failed = subprocess.run(
                [sys.executable, '-m', 'cadex_cli.video', '--project', str(project),
                 '--run', checkpoint_run], capture_output=True, text=True, timeout=600,
                env=dict(os.environ, PATH=temp + os.pathsep + os.environ['PATH'], PYTHONPATH='cli'))
            result['failure_seconds'] = round(time.time() - started, 3)
        result['render_exit'] = failed.returncode
        result['render_stderr'] = failed.stderr
        result['failure_receipt'] = read(receipt)
        assert failed.returncode == 1 and 'FFmpeg encoding failed' in failed.stderr
        assert result['failure_receipt']['state'] == 'failed'
        assert trainer.poll() is None and read(progress)['state'] == 'training'
        with HeadlessBrowser(find_browser()) as browser:
            live = browser.page(url)
            live.evaluate('cadexReview.ready', await_promise=True)
            assert live.text('#project-name') == project.name + ' — review'
            assert live.text('#view-kind') == 'RUN ' + training_run
            checkpoint = browser.page(url)
            checkpoint.evaluate('cadexReview.ready', await_promise=True)
            checkpoint.click("#views li[data-run='" + checkpoint_run + "']")
            checkpoint.wait_for("document.querySelector('#videos').textContent.includes('FFmpeg encoding failed')")
            result['failure_label'] = checkpoint.text('#videos')
            assert 'Retry the CLI video command' in result['failure_label']
            # A failed re-render must preserve its earlier verified recording.
            result['retained_checkpoint'] = play(checkpoint, result['failure_receipt']['videos'][0])
            checkpoint.screenshot(project / 'evidence' / (checkpoint_run + '-render-failure.png'))
            # Keep the failed view open while another page observes real committed
            # updates through ordinary polling, without invoking refresh or reload.
            seen = set()
            deadline = time.monotonic() + 90
            while len(seen) < 4 and time.monotonic() < deadline:
                assert trainer.poll() is None
                assert trainers() == original_trainers, 'trainer stopped or duplicated'
                committed = read(progress)
                assert committed['state'] == 'training'
                shown = int(live.text('[data-metric=iteration]').split(': ')[1])
                if shown not in seen:
                    seen.add(shown)
                    result['observations'].append({'page_iteration': shown,
                        'committed_iteration': committed['iteration'],
                        'telemetry_state': live.attribute('#telemetry', 'data-state'),
                        'reward_points': live.attribute('[data-history=curve]', 'data-points'),
                        'loss_points': live.attribute('[data-history=loss_curve]', 'data-points')})
                time.sleep(.25)
            assert len(seen) == 4
            # The first page sample can still be the pre-failure checkpoint
            # publication pause; require three subsequent committed updates.
            assert len([i for i in seen if i > result['before']['iteration']]) >= 3
            assert live.evaluate("performance.getEntriesByType('navigation').length") == 1
            assert checkpoint.text('#view-kind') == 'RUN ' + checkpoint_run
            assert 'FFmpeg encoding failed' in checkpoint.text('#videos')
            # An earlier run's retained recording, named by the caller rather
            # than by fixture: history must stay playable during the fault.
            checkpoint.click("#views li[data-run='" + prior + "']")
            result['prior_playback'] = play(checkpoint, read(project / 'runs' / prior / 'video.json')['videos'][0])
            result['after'] = read(progress)
            result['trainers_after'] = trainers()
            assert result['trainers_after'] == original_trainers
            result['trainer_active_after_browser'] = trainer.poll() is None
            assert result['trainer_active_after_browser'] and result['after']['state'] == 'training'
            result['ok'] = True
    finally:
        output.write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    # Standalone observer waits for train.py's first verified publication. It
    # deliberately fails a re-render of that checkpoint, then retries the same
    # retained inputs. Renderer locking keeps publication serialized.
    project, training_run, url, prior = sys.argv[1:]
    project = Path(project).resolve()
    assert (project / 'runs' / prior / 'video.json').is_file(), prior
    checkpoint_run = training_run + '-checkpoint20'

    class Trainer:
        def poll(self):
            progress = json.loads((project / 'runs' / training_run / 'train/progress.json').read_text())
            return None if progress['state'] == 'training' else 1

    deadline = time.monotonic() + 900
    publication = project / 'evidence' / (checkpoint_run + '-publication.json')
    while not publication.exists():
        assert time.monotonic() < deadline, 'checkpoint publication timeout'
        time.sleep(.5)
    exercise(project, training_run, checkpoint_run, url, Trainer(), prior)
    subprocess.run([sys.executable, '-m', 'cadex_cli.video', '--project', str(project),
                    '--run', checkpoint_run], check=True, timeout=600)
    # The recovery check keeps its own evidence label so it neither overwrites
    # train.py's publication-time check (the ``-recheck`` files) nor is read
    # under a name check_video.py does not write.
    subprocess.run([sys.executable, str(Path(__file__).with_name('check_video.py')),
                    str(project), checkpoint_run, url, '--not-default', '--label', 'render-recovery'],
                   check=True, timeout=180)
    assert Trainer().poll() is None, 'training ended before recovery'
    receipt = project / 'evidence' / (checkpoint_run + '-render-failure.json')
    result = json.loads(receipt.read_text())
    result['recovered'] = json.loads((project / 'evidence' / (checkpoint_run + '-render-recovery-check.json')).read_text())
    result['training_after_recovery'] = json.loads((project / 'runs' / training_run / 'train/progress.json').read_text())
    receipt.write_text(json.dumps(result, indent=2) + '\n')
