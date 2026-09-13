# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Bounded real D6 probe: kill the cadexd engine and restart it during training.

PYTHONPATH=cli:cli/tests pixi run python docs/probes/lark-fresh/engine_restart.py PROJECT URL RUN

The engine is one ``cadexd`` per CLI invocation: ``./cadex`` starts it, drives
it over stdio and stops it. So "restart the engine mid-run" is, through the
public CLI alone, one ``cadex export`` whose engine is SIGKILLed while it is
working, followed by another ``cadex export`` that starts a fresh engine. The
trainer is offboard and never talks to an engine; the persistent dashboard
opens none. This probe records both engine PIDs, the killed CLI's exit and
error, that no engine or worker process outlives the kill, that the restarted
engine reproduces the exported model and task bytes, that the one trainer keeps
its PID and start ticks throughout, that the already-open page keeps receiving
committed telemetry without a reload, and that a fresh visit still selects the
active run. The dashboard service is never restarted here. Retains all
evidence in PROJECT/evidence; requires the existing training venv.
"""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

from interruption import (TrainerGuard, check_page_identity, inventory,
                          output_file, read, save, sha)
from cadex_cli.review_record import write_run_record
from cadex_cli.review_server import retain_training_view
from cadex_cli.session import project_lock
from cdp_browser import HeadlessBrowser, find_browser

ENGINE_EXECUTABLES = ('FreeCADCmd', 'CadexGeometryWorker')
SERVICE = 'cadex-operator-review'


def live_processes():
    """pid, ppid, start ticks and argv of every readable process (Linux /proc)."""
    rows = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            argv = [os.fsdecode(a) for a in (entry / 'cmdline').read_bytes().split(b'\0') if a]
            fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
        except (OSError, UnicodeError):
            continue
        if argv:
            rows.append(dict(pid=int(entry.name), ppid=int(fields[1]), start_ticks=fields[19], argv=argv))
    return sorted(rows, key=lambda r: r['pid'])


def engine_processes():
    return [r for r in live_processes() if Path(r['argv'][0]).name in ENGINE_EXECUTABLES]


def trainer_identity():
    found = [dict(pid=r['pid'], start_ticks=r['start_ticks']) for r in live_processes()
             if Path(r['argv'][0]).name.startswith('python') and any(Path(a).name == 'cadex_train.py' for a in r['argv'][1:])]
    assert len(found) == 1, found
    return found[0]


def descendants(rows, root):
    parents = {r['pid']: r['ppid'] for r in rows}
    out = []
    for r in rows:
        pid = r['pid']
        while pid in parents and pid != root:
            pid = parents[pid]
        if pid == root and r['pid'] != root:
            out.append(dict(pid=r['pid'], ppid=r['ppid'], executable=Path(r['argv'][0]).name))
    return out


def service(prop):
    return subprocess.check_output(['systemctl', '--user', 'show', SERVICE, '-p', prop, '--value'], text=True).strip()


def cli_export(p, ev, label, kill_after=None):
    """One public ``cadex export`` whose engine child is observed and, when
    ``kill_after`` is given, SIGKILLed that many seconds after it appears."""
    out = ev / (label + '-out')
    shutil.rmtree(out, ignore_errors=True)
    started = time.monotonic()
    with (ev / (label + '.stderr')).open('w') as err:
        proc = subprocess.Popen(['./cadex', '--project', str(p), 'export', '--out', str(out), '--json'],
                                stdout=subprocess.PIPE, stderr=err, text=True)
        engine = None
        while engine is None and proc.poll() is None and time.monotonic() - started < 60:
            for r in engine_processes():
                if r['ppid'] == proc.pid and 'import cadexd' in ' '.join(r['argv']):
                    engine = r
            time.sleep(.005)
        assert engine, 'no engine child observed'
        row = dict(label=label, cli_pid=proc.pid, engine_pid=engine['pid'], engine_start_ticks=engine['start_ticks'],
                   engine_seen_seconds=round(time.monotonic() - started, 3))
        if kill_after is not None:
            time.sleep(kill_after)
            row['engine_workers_at_kill'] = descendants(engine_processes(), engine['pid'])
            os.kill(engine['pid'], signal.SIGKILL)
            row['killed_seconds'] = round(time.monotonic() - started, 3)
        stdout, _ = proc.communicate(timeout=300)
    row['exit'] = proc.returncode
    row['wall_seconds'] = round(time.monotonic() - started, 3)
    (ev / (label + '.json')).write_text(stdout)
    envelope = json.loads(stdout)
    row.update(ok=envelope['ok'], error=envelope.get('error'), accepted_revision=envelope.get('accepted_revision'),
               digest=envelope.get('digest'), outputs=len(envelope.get('outputs') or []),
               out_files=sorted(x.name for x in out.iterdir()) if out.is_dir() else None)
    time.sleep(2)
    row['engine_processes_after'] = [dict(pid=r['pid'], ppid=r['ppid'], executable=Path(r['argv'][0]).name) for r in engine_processes()]
    assert row['engine_processes_after'] == [], 'engine or worker outlived the CLI'
    return row, envelope


def main(project, url, name):
    p = Path(project).resolve()
    run = p / 'runs' / name
    train = run / 'train'
    ev = p / 'evidence'
    assert Path(name).name == name
    m = read(p / 'script.json')
    identity = dict(accepted_revision=m['accepted_revision'], accepted_digest=m['accepted_digest'])
    before = inventory(p / 'runs')
    train.mkdir(parents=True, exist_ok=False)
    result = dict(schema='cadex-engine-restart-evidence-v1', project=p.name, run=name, url=url,
                  persistent_port=8765, private_address_same_machine=True, iterations=100,
                  timeout_seconds=900, memory_max_bytes=20 * 1024**3, **identity,
                  service=dict(unit=SERVICE, state_before=subprocess.run(['systemctl', '--user', 'is-active', SERVICE], capture_output=True, text=True).stdout.strip(),
                               main_pid_before=service('MainPID')))
    export = subprocess.run(['./cadex', '--project', str(p), 'export', '--out', str(train), '--json'],
                            capture_output=True, text=True, timeout=300)
    assert export.returncode == 0, export.stderr
    envelope = json.loads(export.stdout)
    assert envelope['ok'] and envelope['accepted_revision'] == identity['accepted_revision']
    model = output_file(envelope, 'assembly_mjcf_xml', 'xml')
    task = output_file(envelope, 'assembly_training_task_json', 'json')
    manifest_after_export = sha(p / 'script.json')
    shutil.copyfile(p / 'script.py', run / 'script.py')
    with project_lock(p):
        retain_training_view(p, run)
    frozen = read(run / 'training-view.json')
    assert frozen['model']['available']
    components = len(frozen['model']['components'])
    base = dict(project_root=p, mode='bounded-engine-restart',
                accepted_revision=m['accepted_revision'], digest=m['accepted_digest'],
                params=m['param_values'], param_specs=m['param_specs'],
                identity_source='accepted manifest and public export',
                requested={k: result[k] for k in ('project', 'run', 'iterations', 'timeout_seconds', 'memory_max_bytes')},
                task_bundle=task, task_sha256=sha(task), model_xml=model, snapshot_docs=True)
    unit = 'cadex-' + name
    guard = TrainerGuard(ev / (name + '-exclusion.json'), unit)
    guard.start()
    proc = None

    def iteration(page):
        return int(page.text('[data-metric=iteration]').split(': ')[1])

    def progress():
        return read(train / 'progress.json')

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
        deadline = time.monotonic() + 420
        while not (train / 'progress.json').exists() or progress().get('iteration', -1) < 4:
            assert proc.poll() is None, 'trainer exited early'
            assert time.monotonic() < deadline, 'training did not reach iteration 4'
            time.sleep(.25)
        trainer = trainer_identity()
        result['trainer'] = trainer
        with HeadlessBrowser(find_browser()) as browser:
            live = browser.page(url)
            check_page_identity(live, p, name, identity['accepted_revision'], m['param_values'], components)
            live.wait_for("document.getElementById('telemetry').dataset.state === 'training'")
            start_iteration = iteration(live)
            result['page_before'] = dict(iteration=start_iteration, freshness=live.attribute('#freshness', 'data-state'))
            # Fault: the engine of a public CLI invocation dies mid-work.
            killed, _ = cli_export(p, ev, name + '-engine-killed', kill_after=.4)
            assert killed['exit'] == 1 and killed['ok'] is False, killed
            assert 'closed its protocol stream' in killed['error'], killed['error']
            assert trainer_identity() == trainer, 'trainer changed across the engine kill'
            mid = read(p / 'script.json')
            assert mid['accepted_revision'] == identity['accepted_revision'] and mid['accepted_digest'] == identity['accepted_digest']
            result['manifest_after_kill'] = dict(sha256=sha(p / 'script.json'), bytes_equal_to_after_export=sha(p / 'script.json') == manifest_after_export)
            # Restart: the next CLI invocation starts a fresh engine.
            restarted, again = cli_export(p, ev, name + '-engine-restarted')
            assert restarted['exit'] == 0 and again['ok'], restarted
            assert restarted['engine_pid'] != killed['engine_pid']
            assert again['accepted_revision'] == identity['accepted_revision'] and again['digest'] == identity['accepted_digest']
            model2 = output_file(again, 'assembly_mjcf_xml', 'xml')
            task2 = output_file(again, 'assembly_training_task_json', 'json')
            assert model2.read_bytes() == model.read_bytes() and task2.read_bytes() == task.read_bytes()
            assert trainer_identity() == trainer, 'trainer changed across the engine restart'
            result['engine'] = dict(killed=killed, restarted=restarted, re_export_bytes_identical=True,
                                    trainer_after_restart=trainer_identity())
            # The open page keeps receiving committed updates, with no reload.
            samples = []
            seen = {}
            window = time.monotonic()
            while len(samples) < 7:
                assert time.monotonic() - window < 120, 'seven resumed updates not observed'
                data = progress()
                assert data['state'] == 'training'
                assert trainer_identity() == trainer, 'trainer stopped or duplicated'
                seen[data['iteration']] = data['updated_at']
                shown = iteration(live)
                if shown > start_iteration and live.attribute('#freshness', 'data-state') == 'live':
                    if shown in seen and not any(s['iteration'] == shown for s in samples):
                        lag = round(time.time() - seen[shown], 3)
                        assert 0 <= lag < 5, lag
                        samples.append(dict(iteration=shown, commit_to_page_seconds=lag,
                                            reward=live.text('[data-metric=reward_per_step]'), loss=live.text('[data-metric=loss]'),
                                            episode_steps=live.text('[data-metric=episode_steps]'),
                                            points=[int(live.attribute('[data-history=' + k + ']', 'data-points')) for k in ('curve', 'loss_curve', 'episode_steps_curve')]))
                time.sleep(.1)
            result['samples'] = samples
            result['iteration_after'] = iteration(live)
            assert live.evaluate("performance.getEntriesByType('navigation').length") == 1
            assert live.text('#view-kind') == 'RUN ' + name and live.text('#view-revision') == identity['accepted_revision']
            result['no_navigation'] = True
            fresh = browser.page(url)
            fresh.evaluate('window.cadexReview.ready', await_promise=True)
            assert fresh.text('#view-kind') == 'RUN ' + name and fresh.text('#view-revision') == identity['accepted_revision']
            result['fresh_default'] = fresh.text('#view-kind')
            live.screenshot(ev / (name + '-live.png'))
        peak = 0
        bounds = {}
        while proc.poll() is None:
            guard.check()
            raw = subprocess.check_output(['systemctl', '--user', 'show', unit + '.scope', '-p', 'MemoryCurrent', '-p', 'MemoryMax'], text=True)
            values = dict(line.split('=', 1) for line in raw.strip().splitlines())
            if values.get('MemoryCurrent', '').isdigit():
                peak = max(peak, int(values['MemoryCurrent']))
                bounds = values
            time.sleep(.5)
        result['trainer_exit'] = proc.wait()
        final = progress()
        policy = train / (name + '.cxpolicy')
        success = result['trainer_exit'] == 0 and final['state'] == 'done' and policy.is_file()
        write_run_record(run, status='ok' if success else 'failed',
                         legs=[dict(leg='train', exit=result['trainer_exit'])],
                         **(dict(policy_name=policy.name, policy_sha256=sha(policy)) if success else
                            dict(error='Bounded engine-restart experiment training failed; inspect retained trainer log.')),
                         **base)
        result.update(peak_memory_bytes=peak, enforced_memory_max=bounds.get('MemoryMax'),
                      final_state=final['state'], final_iteration=final['iteration'], device=final['device'],
                      policy_sha256=sha(policy) if policy.exists() else None)
        assert success and final['iteration'] == 99 and final['device'] == 'gpu'
        assert bounds['MemoryMax'] == str(20 * 1024**3) and 0 < peak < 20 * 1024**3
        after = inventory(p / 'runs')
        assert all(after.get(k) == v for k, v in before.items())
        result['prior_run_files_unchanged'] = len(before)
        last = read(p / 'script.json')
        assert last['accepted_revision'] == identity['accepted_revision'] and last['accepted_digest'] == identity['accepted_digest']
        result['manifest'] = dict(accepted_identity_unchanged=True, bytes_changed_keys=sorted(k for k in m if m[k] != last.get(k)))
        with HeadlessBrowser(find_browser()) as browser:
            page = browser.page(url)
            check_page_identity(page, p, name, identity['accepted_revision'], m['param_values'], components)
            page.wait_for("document.getElementById('telemetry').dataset.state === 'done'")
            assert page.text('#view-status') == 'completed'
            result['completion_default'] = page.text('#view-kind')
            page.screenshot(ev / (name + '-completed.png'))
        result['service'].update(state_after=subprocess.check_output(['systemctl', '--user', 'is-active', SERVICE], text=True).strip(),
                                 main_pid_after=service('MainPID'))
        assert result['service']['state_after'] == 'active' and result['service']['main_pid_after'] == result['service']['main_pid_before']
        result['ok'] = True
    except Exception as exc:
        result['failure'] = repr(exc)
        raise
    finally:
        # The trainer owns its timeout even if observation fails. The receipt
        # is written whatever the guard concludes, and a violation still fails.
        try:
            guard.close()
        except Exception as exc:
            result.setdefault('failure', repr(exc))
            result.pop('ok', None)
            raise
        finally:
            result['exclusion'] = guard.report
            save(ev / (name + '-evidence.json'), result)


if __name__ == '__main__':
    main(*sys.argv[1:])
