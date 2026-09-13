# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Real sequential GPU interruption/retry on the persistent review server.

PYTHONPATH=cli:cli/tests pixi run python interruption.py PROJECT URL PREFIX
Requires the existing offboard venv and systemd user manager. Never starts or
stops the dashboard. Outputs and failed probes remain under the project.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

from cdp_browser import HeadlessBrowser, find_browser
from cadex_cli.review_record import write_run_record
from cadex_cli.review_server import retain_training_view
from cadex_cli.session import project_lock


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '.git' not in p.relative_to(root).parts}


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')



def check_terminal(page, interrupted):
    # Telemetry and the supervisor record are separate atomic publications.
    state = 'failed' if interrupted else 'done'
    outcome = 'failed' if interrupted else 'completed'
    page.wait_for("document.getElementById('telemetry').dataset.state === " + json.dumps(state), timeout=15)
    page.wait_for("document.getElementById('view-status').textContent === " + json.dumps(outcome), timeout=15)
    if interrupted:
        page.wait_for("document.getElementById('view-note').textContent.includes('Controlled interruption')", timeout=15)
        assert 'start a new cadex walk' in page.text('#telemetry')


def main():
    project, url, prefix = sys.argv[1:]
    p = Path(project).resolve()
    assert Path(prefix).name == prefix
    ev = p / 'evidence' / prefix
    ev.mkdir(exist_ok=False)
    before = inventory(p / 'runs')
    original = p.with_name('ot5-wren')
    original_before = inventory(original)
    save(ev / 'runs-before.json', before)
    save(ev / 'original-before.json', original_before)
    results = []
    env = dict(os.environ, XLA_PYTHON_CLIENT_MEM_FRACTION='0.45')
    with HeadlessBrowser(find_browser()) as browser:
        for interrupted in (True, False):
            name = prefix + ('-interrupt' if interrupted else '-retry')
            run = p / 'runs' / name
            train = run / 'train'
            train.mkdir(parents=True, exist_ok=False)
            with (ev / (name + '-export.log')).open('w') as log:
                export = subprocess.run(['./cadex', '--project', str(p), 'export', '--out', str(train), '--json'],
                                        text=True, stdout=subprocess.PIPE, stderr=log, timeout=300)
            save(ev / (name + '-export.json'), json.loads(export.stdout))
            assert export.returncode == 0, export.stdout
            m = read(p / 'script.json')
            shutil.copyfile(p / 'script.py', run / 'script.py')
            with project_lock(p):
                retain_training_view(p, run)
            frozen = read(run / 'training-view.json')
            assert frozen['model']['available']
            iterations = 60 if interrupted else 12
            base = dict(project_root=p, mode='bounded-interruption-lifecycle',
                        accepted_revision=m['accepted_revision'], digest=m['accepted_digest'],
                        params=m['param_values'], param_specs=m['param_specs'],
                        identity_source='accepted manifest and public export',
                        requested=dict(iterations=iterations, envs=1024, seed=0,
                                       timeout_seconds=900, memory_max_bytes=20 * 1024**3,
                                       controlled_interrupt=interrupted),
                        task_bundle=train / 'wren_walk-task.json',
                        task_sha256=sha(train / 'wren_walk-task.json'),
                        model_xml=train / 'wren_model-model.xml', snapshot_docs=True)
            write_run_record(run, status='running', **base)
            unit = 'cadex-' + name
            command = ['systemd-run', '--user', '--scope', '--unit=' + unit, '-p', 'MemoryMax=20G',
                       'timeout', '--signal=TERM', '--kill-after=20s', '900',
                       str(Path.home() / 'cadex-train-venv/bin/python'), 'training/cadex_train.py',
                       str(train / 'wren_walk-task.json'), '--out', str(train / (name + '.cxpolicy')),
                       '--iterations', str(iterations), '--envs', '1024', '--seed', '0']
            log = (ev / (name + '-trainer.log')).open('w')
            proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env)
            start = time.monotonic()
            print(name + ' started', flush=True)
            try:
                page = browser.page(url)
                page.evaluate('window.cadexReview.ready', await_promise=True)
                assert page.text('#project-name') == p.name + ' — review'
                assert page.text('#view-kind') == 'RUN ' + name
                page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
                assert page.text('#view-revision') == base['accepted_revision']
                assert float(page.text("#params tr[data-param='foot_len'] td:nth-child(2)")) == 110
                assert page.evaluate('cadexReview.viewer().stats().components') == 8
                page.screenshot(ev / (name + '-start.png'))
                samples = []
                peak = 0
                while True:
                    assert time.monotonic() - start < 880, 'probe deadline'
                    q = read(train / 'progress.json') if (train / 'progress.json').exists() else {}
                    shown = page.text('[data-metric=iteration]')
                    if q.get('iteration', -1) >= 0 and (not samples or samples[-1]['page'] != shown):
                        samples.append(dict(file=q['iteration'], page=shown, state=page.attribute('#telemetry', 'data-state')))
                    bound = subprocess.check_output(['systemctl', '--user', 'show', unit + '.scope',
                                                     '-p', 'MemoryCurrent', '-p', 'MemoryMax', '-p', 'ControlGroup'], text=True)
                    bounds = dict(line.split('=', 1) for line in bound.strip().splitlines())
                    if bounds.get('MemoryCurrent', '').isdigit():
                        peak = max(peak, int(bounds['MemoryCurrent']))
                    if interrupted and q.get('iteration', -1) >= 5 and len(samples) >= 3:
                        assert proc.poll() is None
                        assert bounds['MemoryMax'] == str(20 * 1024**3)
                        cgroup = Path('/sys/fs/cgroup') / bounds['ControlGroup'].lstrip('/')
                        targets = []
                        for pid in (cgroup / 'cgroup.procs').read_text().split():
                            cmdline = (Path('/proc') / pid / 'cmdline').read_bytes().split(b'\0')
                            if b'training/cadex_train.py' in cmdline and Path(os.fsdecode(cmdline[0])).name.startswith('python'):
                                targets.append(int(pid))
                        assert len(targets) == 1, targets
                        os.kill(targets[0], signal.SIGINT)
                        save(ev / 'signal.json', dict(signal='SIGINT', iteration=q['iteration'], trainer_pid=targets[0]))
                        break
                    if proc.poll() is not None:
                        break
                    time.sleep(.5)
                code = proc.wait(timeout=60)
                final = read(train / 'progress.json')
                if interrupted:
                    assert code != 0 and final['state'] == 'failed' and 'KeyboardInterrupt' in final['error']
                    assert not (train / (name + '.cxpolicy')).exists()
                    error = 'Controlled interruption: SIGINT after real GPU updates; start a new cadex walk --out runs/<new-name>.'
                    write_run_record(run, status='failed', error=error, legs=[dict(leg='train', exit=code)], **base)
                else:
                    assert code == 0 and final['state'] == 'done' and final['iteration'] == iterations - 1
                    assert (train / (name + '.cxpolicy')).is_file()
                    write_run_record(run, status='ok', legs=[dict(leg='train', exit=0)], **base)
                assert final['device'] == 'gpu'
                assert peak > 0 and peak < 20 * 1024**3
                check_terminal(page, interrupted)
                assert page.text('#view-kind') == 'RUN ' + name
                assert page.evaluate("performance.getEntriesByType('navigation').length") == 1
                assert page.evaluate("document.querySelectorAll('#videos video').length") == 0
                page.screenshot(ev / (name + '-finished.png'))
                fresh = browser.page(url)
                fresh.evaluate('window.cadexReview.ready', await_promise=True)
                assert fresh.text('#view-kind') == 'RUN ' + name
                result = dict(run=name, exit=code, final=final, samples=samples, host_peak_bytes=peak,
                              elapsed_s=round(time.monotonic()-start, 3), fresh_selection=fresh.text('#view-kind'),
                              telemetry=page.text('#telemetry'), note=page.text('#view-note'),
                              accepted_revision=base['accepted_revision'], digest=base['digest'])
                results.append(result)
                save(ev / 'attempts.json', results)
                print(name + ' finished: ' + str(code), flush=True)
            finally:
                log.close()
                if proc.poll() is None:
                    print('Trainer remains under its independent 900-second timeout', flush=True)
            # Old videos remain deliberately selectable after either outcome.
            for old in ('wren1-checkpoint20', 'wren1-final', 'wren2-checkpoint20', 'wren2-final'):
                subprocess.run(['pixi', 'run', 'python', str(Path(__file__).with_name('check_video.py')),
                                str(p), old, url, '--historical'], check=True, timeout=180,
                               stdout=(ev / (name + '-' + old + '-video.log')).open('w'))
        page.evaluate('cadexReview.select(' + json.dumps(prefix + '-interrupt') + ')', await_promise=True)
        assert 'Controlled interruption' in page.text('#view-note')
        page.evaluate('cadexReview.refresh()', await_promise=True)
        assert page.text('#view-kind') == 'RUN ' + prefix + '-interrupt'
        page.click('#current-run')
        page.wait_for("document.getElementById('view-kind').textContent === " + json.dumps('RUN ' + prefix + '-retry'))
    assert all(sha(p / 'runs' / path) == digest for path, digest in before.items())
    assert inventory(original) == original_before
    save(ev / 'result.json', dict(project=p.name, attempts=results, prior_run_files_preserved=len(before),
                                 original_files_preserved=len(original_before), four_videos_checked_after_each=True,
                                 historical_interruption_preserved=True, persistent_server=True,
                                 same_machine_private_network=True))
    print('interruption lifecycle passed', flush=True)


if __name__ == '__main__':
    main()
