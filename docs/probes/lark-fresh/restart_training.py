# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Bounded real D6 probe; restart only the persistent review service.

PYTHONPATH=cli:cli/tests pixi run python docs/probes/lark-fresh/restart_training.py PROJECT URL RUN HISTORY
Retains all evidence in PROJECT/evidence; requires the existing training venv.
A finished training is stored as a project asset through the public CLI before
the run record is written (ADR-327), so the record names a store copy that exists.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from interruption import (TrainerGuard, check_page_identity, inventory,
                          output_file, read, save, sha)
from cadex_cli.review_record import write_run_record
from cadex_cli.review_server import retain_training_view
from cadex_cli.session import project_lock
from cdp_browser import HeadlessBrowser, find_browser


def main(project, url, name, history):
    p = Path(project).resolve()
    run = p / 'runs' / name
    train = run / 'train'
    ev = p / 'evidence'
    assert Path(name).name == name
    assert read(p / 'runs' / history / 'run.json')['model']['accepted_revision'] != read(p / 'script.json')['accepted_revision'], 'Choose a historical model revision for the observer'
    before = inventory(p / 'runs')
    train.mkdir(parents=True, exist_ok=False)
    result = dict(project=p.name, run=name, history=history, iterations=100,
                  timeout_seconds=900, memory_max_bytes=20 * 1024**3)
    export = subprocess.run(['./cadex', '--project', str(p), 'export', '--out', str(train), '--json'],
                            capture_output=True, text=True, timeout=300)
    assert export.returncode == 0, export.stderr
    envelope = json.loads(export.stdout)
    assert envelope['ok']
    model = output_file(envelope, 'assembly_mjcf_xml', 'xml')
    task = output_file(envelope, 'assembly_training_task_json', 'json')
    m = read(p / 'script.json')
    manifest_before = sha(p / 'script.json')
    shutil.copyfile(p / 'script.py', run / 'script.py')
    with project_lock(p):
        retain_training_view(p, run)
    frozen = read(run / 'training-view.json')
    assert frozen['model']['available']
    base = dict(project_root=p, mode='bounded-dashboard-restart',
                accepted_revision=m['accepted_revision'], digest=m['accepted_digest'],
                params=m['param_values'], param_specs=m['param_specs'],
                identity_source='accepted manifest and public export',
                requested=result.copy(), task_bundle=task, task_sha256=sha(task),
                model_xml=model, snapshot_docs=True)
    unit = 'cadex-' + name
    guard = TrainerGuard(ev / (name + '-exclusion.json'), unit)
    guard.start()
    proc = None
    try:
        write_run_record(run, status='running', **base)
        command = ['systemd-run', '--user', '--scope', '--unit=' + unit, '-p', 'MemoryMax=20G',
                   'timeout', '--signal=TERM', '--kill-after=20s', '900',
                   str(Path.home() / 'cadex-train-venv/bin/python'), 'training/cadex_train.py',
                   str(task), '--out', str(train / (name + '.cxpolicy')),
                   '--iterations', '100', '--envs', '1024', '--seed', '0']
        with (ev / (name + '-trainer.log')).open('w') as log:
            proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                    env=dict(os.environ, XLA_PYTHON_CLIENT_MEM_FRACTION='0.45'))
        observer = Path(__file__).resolve().parent.parent / 'wren-fresh/restart_training.py'
        with (ev / (name + '-observer.log')).open('w') as log:
            observed = subprocess.Popen([sys.executable, str(observer), url, str(p), name, history],
                                        stdout=log, stderr=subprocess.STDOUT)
        peak = 0
        bounds = {}
        while proc.poll() is None:
            guard.check()
            raw = subprocess.check_output(['systemctl', '--user', 'show', unit + '.scope',
                                          '-p', 'MemoryCurrent', '-p', 'MemoryMax'], text=True)
            values = dict(line.split('=', 1) for line in raw.strip().splitlines())
            if values.get('MemoryCurrent', '').isdigit():
                peak = max(peak, int(values['MemoryCurrent']))
                bounds = values
            time.sleep(.5)
        result['trainer_exit'] = proc.wait()
        result['observer_exit'] = observed.wait(timeout=60)
        final = read(train / 'progress.json')
        policy = train / (name + '.cxpolicy')
        success = result['trainer_exit'] == 0 and final['state'] == 'done' and policy.is_file()
        if success:
            # Store the policy through the public CLI before the record is
            # written, so the record names a store copy that exists and the
            # run is never listed as a retention gap (ADR-327).
            with (ev / (name + '-asset.stderr')).open('w') as err:
                put = subprocess.run(['./cadex', '--project', str(p), 'asset', '--put', str(policy),
                                      '--name', policy.name, '--json'],
                                     stdout=subprocess.PIPE, stderr=err, text=True, timeout=300)
            (ev / (name + '-asset.json')).write_text(put.stdout)
            stored = json.loads(put.stdout) if put.returncode == 0 and put.stdout else {}
            result['store'] = dict(exit=put.returncode, ok=stored.get('ok'), name=policy.name,
                                   sha256_matches=any(row.get('sha256') == sha(policy) for row in stored.get('assets') or []))
            success = put.returncode == 0 and stored.get('ok') is True and result['store']['sha256_matches']
        write_run_record(run, status='ok' if success else 'failed',
                         legs=[dict(leg='train', exit=result['trainer_exit'])],
                         **(dict(policy_name=policy.name, policy_sha256=sha(policy)) if success else
                            dict(error='Bounded restart experiment training failed; inspect retained trainer log.' if result.get('store') is None else 'Training finished but the policy could not be stored as a project asset; inspect the retained asset stderr.')),
                         **base)
        result.update(peak_memory_bytes=peak, enforced_memory_max=bounds.get('MemoryMax'),
                      final_state=final['state'], final_iteration=final['iteration'], device=final['device'],
                      revision=m['accepted_revision'], policy_sha256=sha(policy) if policy.exists() else None)
        assert success and final['iteration'] == 99 and final['device'] == 'gpu'
        assert bounds['MemoryMax'] == str(20 * 1024**3) and 0 < peak < 20 * 1024**3
        assert result['observer_exit'] == 0, 'see retained observer receipt/log'
        result['restart'] = read(ev / (name + '-restart-training.json'))
        after = inventory(p / 'runs')
        assert all(after.get(k) == v for k, v in before.items())
        assert sha(p / 'script.json') == manifest_before
        result['prior_run_files_unchanged'] = len(before)
        result['accepted_manifest_unchanged'] = True
        with HeadlessBrowser(find_browser()) as browser:
            page = browser.page(url)
            check_page_identity(page, p, name, m['accepted_revision'], m['param_values'], len(frozen['model']['components']))
            page.wait_for("document.getElementById('telemetry').dataset.state === 'done'")
            assert page.text('#view-status') == 'completed'
            result['completion_default'] = page.text('#view-kind')
            page.screenshot(ev / (name + '-completed.png'))
        result['service_active'] = subprocess.check_output(['systemctl', '--user', 'is-active', 'cadex-operator-review'], text=True).strip()
        assert result['service_active'] == 'active'
        result['ok'] = True
    except Exception as exc:
        result['failure'] = repr(exc)
        raise
    finally:
        # The trainer owns its timeout even if observation fails.
        guard.close()
        result['exclusion'] = guard.report
        save(ev / (name + '-evidence.json'), result)


if __name__ == '__main__':
    main(*sys.argv[1:])
