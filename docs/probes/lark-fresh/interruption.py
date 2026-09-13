# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Real sequential GPU interruption/retry on the persistent review server,
followed by a verified video of the retry's saved policy (D8, D7, D10).

PYTHONPATH=cli:cli/tests pixi run python interruption.py PROJECT URL PREFIX ORIGINAL [RETRY_ITERATIONS]

This is the Wren driver (``../wren-fresh/interruption.py``) with nothing named
after a project: the model and task bundle are found by kind in the public
``cadex export`` envelope, the parameter the browser is held to is every
declared value of the accepted manifest, the component count comes from the
frozen training view, the retained videos to re-check are every run that has
one, and ORIGINAL names the source project whose inventory must not change
while the copy retrains. Requires the existing offboard venv and systemd user
manager. Never starts or stops the dashboard. Outputs and failed probes remain
under the project; the trainer's own progress snapshot is never written here.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import threading
import time

from cdp_browser import HeadlessBrowser, find_browser
from cadex_cli.review_record import write_run_record
from cadex_cli.review_server import retain_training_view
from cadex_cli.session import project_lock
from cadex_cli.walk import review_from_outputs, write_review

GENERIC = Path(__file__).resolve().parent.parent / 'wren-fresh'   # check_video.py is project-agnostic


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '.git' not in p.relative_to(root).parts}


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def trainers(proc_root=Path('/proc')):
    """Read Python trainers and pytest runners, regardless of GPU/CPU selection.

    Pytest is excluded too: tests can invoke training inside their own process.
    Match argv tokens, not shell/timeout wrappers mentioning the script.
    Unreadable live processes fail closed; disappearing processes are normal.
    """
    found = []
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            argv = [os.fsdecode(a) for a in (entry / 'cmdline').read_bytes().split(b'\0') if a]
            if not argv or not Path(argv[0]).name.startswith('python'):
                continue
            if not (any(Path(a).name in ('cadex_train.py', 'pytest') for a in argv[1:]) or
                    any(argv[i:i+2] == ['-m', 'training.cadex_train'] for i in range(len(argv)-1))):
                continue
            groups = (entry / 'cgroup').read_text().splitlines()
            found.append(dict(pid=int(entry.name), scopes=[g.rsplit('/', 1)[-1] for g in groups]))
        except (FileNotFoundError, ProcessLookupError):
            continue
    return sorted(found, key=lambda row: row['pid'])


class TrainerGuard:
    """Sample throughout blocking browser calls; latch any overlap or read error."""
    def __init__(self, receipt, unit, scan=trainers, stop_scope=None):
        self.receipt, self.unit, self.scan = receipt, unit, scan
        self.stop_scope = stop_scope
        self.stop_event = threading.Event()
        self.report = dict(interval_seconds=.05, scans=0, max_trainers=0,
                           observed_pids=[], violation=None, max_scan_gap_seconds=0)
        self.last_scan = None
        self.thread = None

    def sample(self, preflight=False):
        now = time.monotonic()
        if self.last_scan is not None:
            self.report['max_scan_gap_seconds'] = max(self.report['max_scan_gap_seconds'], now-self.last_scan)
        self.last_scan = now
        rows = self.scan()
        self.report['scans'] += 1
        self.report['max_trainers'] = max(self.report['max_trainers'], len(rows))
        self.report['observed_pids'] = sorted(set(self.report['observed_pids']) | {r['pid'] for r in rows})
        foreign = [r for r in rows if self.unit + '.scope' not in r['scopes']]
        if (preflight and rows) or foreign or len(rows) > 1:
            raise RuntimeError('Trainer exclusion violated: ' + json.dumps(rows))

    def start(self):
        try:
            self.sample(preflight=True)
        except Exception as exc:
            self.report['violation'] = str(exc)
            save(self.receipt, self.report)
            raise
        save(self.receipt, self.report)
        self.thread = threading.Thread(target=self.watch, daemon=True)
        self.thread.start()

    def watch(self):
        while not self.stop_event.wait(self.report['interval_seconds']):
            try:
                self.sample()
            except Exception as exc:
                self.report['violation'] = str(exc)
                save(self.receipt, self.report)
                if self.stop_scope:
                    self.stop_scope()
                return

    def check(self):
        if self.report['violation']:
            raise RuntimeError(self.report['violation'])

    def close(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join()
        save(self.receipt, self.report)
        self.check()


def check_terminal(page, interrupted):
    # Telemetry and the supervisor record are separate atomic publications.
    state = 'failed' if interrupted else 'done'
    outcome = 'failed' if interrupted else 'completed'
    page.wait_for("document.getElementById('telemetry').dataset.state === " + json.dumps(state), timeout=15)
    page.wait_for("document.getElementById('view-status').textContent === " + json.dumps(outcome), timeout=15)
    if interrupted:
        page.wait_for("document.getElementById('view-note').textContent.includes('Controlled interruption')", timeout=15)
        assert 'start a new cadex walk' in page.text('#telemetry')


def output_file(envelope, kind, key):
    """The one staged output of ``kind`` in a CLI envelope, by the protocol's own kind names."""
    (entry,) = [o for o in envelope['outputs'] if o.get('kind') == kind]
    return Path(entry['files'][key])


def check_page_identity(page, p, name, revision, params, components):
    page.evaluate('window.cadexReview.ready', await_promise=True)
    assert page.text('#project-name') == p.name + ' — review'
    assert page.text('#view-kind') == 'RUN ' + name
    page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
    assert page.text('#view-revision') == revision
    for key, value in params.items():
        shown = float(page.text("#params tr[data-param=%s] td:nth-child(2)" % json.dumps(key)))
        assert shown == float(value), (key, shown, value)
    assert page.evaluate('cadexReview.viewer().stats().components') == components


def playback(p, ev, url, source_run, policy, pname, cli, model_xml, task_json):
    """Declare the retry's saved policy in the copy's script, roll it out through
    the public CLI, render a video and check it in the browser. This is the
    final-policy branch of ``train.py`` with the run naming as an argument."""
    train = p / 'runs' / source_run / 'train'
    digest = sha(policy)
    source = (p / 'script.py').read_text()
    cli(pname + '-asset', 'asset', '--put', policy, '--name', policy.name)
    script, substitutions = re.subn(r'weights="[^"]+",\s*sha256="[a-f0-9]+"',
                                    'weights=' + json.dumps(policy.name) + ', sha256=' + json.dumps(digest), source)
    assert substitutions == 1, substitutions   # the script's one policy declaration
    scriptpath = ev / (pname + '-script.py')
    scriptpath.write_text(script)
    cli(pname + '-declare', 'script', '--set', scriptpath)
    r = p / 'runs' / pname
    e = cli(pname + '-rollout', 'params', '--set', 'policy_on=1', '--out', r / 'rollout')
    cli(pname + '-render', 'render')
    receipt = read(output_file(e, 'assembly_policy_receipt_json', 'json'))
    trace_path = r / 'rollout/assembly-simulation-trace.json'
    assert receipt['witness_error'] < receipt['witness_tolerance']
    t = read(trace_path)
    assert t['policy']['policy_sha256'] == digest
    for n in (model_xml.name, task_json.name):
        assert (r / 'rollout' / n).read_bytes() == (train / n).read_bytes()
    shutil.copyfile(p / 'script.py', r / 'script.py')
    shutil.copytree(p / 'review/render', r / 'render')
    (r / 'train').mkdir()
    shutil.copyfile(train / 'progress.json', r / 'train/progress.json')
    review = review_from_outputs(e['outputs'])
    review['render'] = {'path': f'runs/{pname}/render'}
    review['provenance'] = {'source_run': source_run, 'checkpoint': policy.name, 'training_active_at_start': False,
                            'design_authored_by': 'copy-only CLI edit of the product agent\'s Lark revision (ADR-314): foot_len 90 mm'}
    legs = [{'leg': 'rollout', 'exit': 0, 'accepted_revision': e['accepted_revision'], 'digest': e['digest']}]
    write_review(r, review=review, legs=legs, training={}, params=e['params'])
    write_run_record(r, project_root=p, status='ok', mode='final-policy-playback', legs=legs,
                     accepted_revision=e['accepted_revision'], digest=e['digest'], params=e['params'],
                     param_specs=read(p / 'script.json')['param_specs'], specs_source='successful rollout envelope',
                     requested=review['provenance'], policy_name=policy.name, policy_sha256=digest,
                     task_bundle=r / 'rollout' / task_json.name, task_sha256=sha(task_json),
                     model_xml=r / 'rollout' / model_xml.name, trace=trace_path, review=review, snapshot_docs=True)
    render_start = time.time()
    subprocess.run(['pixi', 'run', 'python', '-m', 'cadex_cli.video', '--project', str(p), '--run', pname],
                   check=True, env=dict(os.environ, PYTHONPATH='cli'), timeout=600)
    render_seconds = round(time.time() - render_start, 3)
    video = read(r / 'video.json')['videos'][0]
    with (ev / (pname + '-video.log')).open('w') as log:
        check = subprocess.run(['pixi', 'run', 'python', str(GENERIC / 'check_video.py'), str(p), pname, url],
                               env=dict(os.environ, PYTHONPATH='cli:cli/tests'), timeout=180, stdout=log, stderr=subprocess.STDOUT)
    assert check.returncode == 0, 'browser video check failed'
    browser = read(p / 'evidence' / (pname + '-check.json'))
    assert browser['fresh_selection'] == 'RUN ' + pname, browser['fresh_selection']
    assert browser['download_sha256'] == video['sha256']
    return dict(run=pname, policy_sha256=digest, witness=receipt, render_seconds=render_seconds,
                video={k: video.get(k) for k in ('path', 'sha256', 'frames', 'duration_seconds', 'sim_seconds', 'style', 'renderer', 'accepted_revision', 'seed')},
                browser=browser, accepted_revision=e['accepted_revision'], digest=e['digest'],
                trace=dict(observed_s=t['parameters']['end_time_s'], termination=t['policy']['termination'],
                           fell=t['policy']['termination'] == 'fell', time_limit_reached=t['policy']['truncated'],
                           step_count=t['policy']['step_count'], total_reward=t['policy']['total_reward'], seed=t['policy']['seed']))


def main():
    project, url, prefix, original = sys.argv[1:5]
    retry_iterations = int(sys.argv[5]) if len(sys.argv) > 5 else 40
    p = Path(project).resolve()
    original = Path(original).resolve()
    assert Path(prefix).name == prefix and original != p
    ev = p / 'evidence' / prefix
    ev.mkdir(exist_ok=False)
    before = inventory(p / 'runs')
    assets_before = inventory(p / 'assets') if (p / 'assets').is_dir() else {}
    original_before = inventory(original)
    save(ev / 'runs-before.json', before)
    save(ev / 'assets-before.json', assets_before)
    save(ev / 'original-before.json', original_before)
    old_videos = sorted(d.name for d in (p / 'runs').iterdir() if (d / 'video.json').is_file())
    assert old_videos
    results = []
    env = dict(os.environ, XLA_PYTHON_CLIENT_MEM_FRACTION='0.45')

    def cli(label, *args):
        with (ev / (label + '.stderr')).open('w') as err:
            r = subprocess.run(['./cadex', '--project', str(p), *map(str, args), '--json'],
                               stdout=subprocess.PIPE, stderr=err, text=True, timeout=300)
        (ev / (label + '.json')).write_text(r.stdout)
        assert r.returncode == 0, (label, r.returncode)
        e = json.loads(r.stdout)
        assert e['ok'], e
        return e

    with HeadlessBrowser(find_browser()) as browser:
        for interrupted in (True, False):
            name = prefix + ('-interrupt' if interrupted else '-retry')
            run = p / 'runs' / name
            train = run / 'train'
            train.mkdir(parents=True, exist_ok=False)
            export = cli(name + '-export', 'export', '--out', train)
            model_xml = output_file(export, 'assembly_mjcf_xml', 'xml')
            task_json = output_file(export, 'assembly_training_task_json', 'json')
            assert model_xml.parent == train and task_json.parent == train
            m = read(p / 'script.json')
            shutil.copyfile(p / 'script.py', run / 'script.py')
            with project_lock(p):
                retain_training_view(p, run)
            frozen = read(run / 'training-view.json')
            assert frozen['model']['available']
            components = len(frozen['model']['components'])
            iterations = 60 if interrupted else retry_iterations
            base = dict(project_root=p, mode='bounded-interruption-lifecycle',
                        accepted_revision=m['accepted_revision'], digest=m['accepted_digest'],
                        params=m['param_values'], param_specs=m['param_specs'],
                        identity_source='accepted manifest and public export',
                        requested=dict(iterations=iterations, envs=1024, seed=0,
                                       timeout_seconds=900, memory_max_bytes=20 * 1024**3,
                                       controlled_interrupt=interrupted),
                        task_bundle=task_json, task_sha256=sha(task_json),
                        model_xml=model_xml, snapshot_docs=True)
            unit = 'cadex-' + name

            def stop_scope():
                subprocess.run(['systemctl', '--user', 'kill', '--signal=SIGTERM', unit + '.scope'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
            guard = TrainerGuard(ev / (name + '-exclusion.json'), unit, stop_scope=stop_scope)
            command = ['systemd-run', '--user', '--scope', '--unit=' + unit, '-p', 'MemoryMax=20G',
                       'timeout', '--signal=TERM', '--kill-after=20s', '900',
                       str(Path.home() / 'cadex-train-venv/bin/python'), 'training/cadex_train.py',
                       str(task_json), '--out', str(train / (name + '.cxpolicy')),
                       '--iterations', str(iterations), '--envs', '1024', '--seed', '0']
            log = (ev / (name + '-trainer.log')).open('w')
            proc = None
            start = time.monotonic()
            print(name + ' started', flush=True)
            try:
                guard.start()
                write_run_record(run, status='running', **base)
                guard.check()
                proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env)
                page = browser.page(url)
                check_page_identity(page, p, name, base['accepted_revision'], base['params'], components)
                page.screenshot(ev / (name + '-start.png'))
                samples = []
                peak = 0
                while True:
                    guard.check()
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
                guard.close()
                assert guard.report['max_trainers'] == 1
                assert len(guard.report['observed_pids']) == 1
                final = read(train / 'progress.json')
                if interrupted:
                    assert code != 0 and final['state'] == 'failed' and 'KeyboardInterrupt' in final['error']
                    assert not (train / (name + '.cxpolicy')).exists()
                    error = 'Controlled interruption: SIGINT after real GPU updates; start a new cadex walk --out runs/<new-name>.'
                    write_run_record(run, status='failed', error=error, legs=[dict(leg='train', exit=code)], **base)
                else:
                    assert code == 0 and final['state'] == 'done' and final['iteration'] == iterations - 1
                    assert (train / (name + '.cxpolicy')).is_file()
                    write_run_record(run, status='ok', legs=[dict(leg='train', exit=0)],
                                     policy_name=name + '.cxpolicy', policy_sha256=sha(train / (name + '.cxpolicy')), **base)
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
                result = dict(exclusion=guard.report, run=name, exit=code, final=final, samples=samples, host_peak_bytes=peak,
                              elapsed_s=round(time.monotonic()-start, 3), fresh_selection=fresh.text('#view-kind'),
                              telemetry=page.text('#telemetry'), note=page.text('#view-note'), components=components,
                              accepted_revision=base['accepted_revision'], digest=base['digest'],
                              model_sha256=sha(model_xml), task_sha256=sha(task_json))
                results.append(result)
                save(ev / 'attempts.json', results)
                print(name + ' finished: ' + str(code), flush=True)
            except Exception as exc:
                stop_scope()
                if proc is not None:
                    proc.wait(timeout=60)
                write_run_record(run, status='failed', error='Probe failed: ' + str(exc), **base)
                raise
            finally:
                log.close()
                guard.close()
            # Old videos remain deliberately selectable after either outcome.
            for old in old_videos:
                with (ev / (name + '-' + old + '-video.log')).open('w') as vlog:
                    subprocess.run(['pixi', 'run', 'python', str(GENERIC / 'check_video.py'), str(p), old, url, '--not-default'],
                                   check=True, timeout=180, env=dict(os.environ, PYTHONPATH='cli:cli/tests'),
                                   stdout=vlog, stderr=subprocess.STDOUT)
        retry = prefix + '-retry'
        video = playback(p, ev, url, retry, p / 'runs' / retry / 'train' / (retry + '.cxpolicy'),
                         retry + '-video', cli, model_xml, task_json)
        save(ev / 'video.json', video)
        page.evaluate('cadexReview.select(' + json.dumps(prefix + '-interrupt') + ')', await_promise=True)
        assert 'Controlled interruption' in page.text('#view-note')
        assert page.text('#view-status') == 'failed'
        assert page.evaluate("document.querySelectorAll('#videos video').length") == 0
        page.evaluate('cadexReview.refresh()', await_promise=True)
        assert page.text('#view-kind') == 'RUN ' + prefix + '-interrupt'
        page.screenshot(ev / (prefix + '-interrupt-historical.png'))
        page.click('#current-run')
        page.wait_for("document.getElementById('view-kind').textContent === " + json.dumps('RUN ' + retry + '-video'))
    assert all(sha(p / 'runs' / path) == digest for path, digest in before.items())
    assert all(sha(p / 'assets' / path) == digest for path, digest in assets_before.items())
    original_after = inventory(original)
    assert original_after == original_before
    save(ev / 'result.json', dict(project=p.name, original=original.name, attempts=results, video=video,
                                 old_videos_checked_after_each=old_videos, retry_iterations=retry_iterations,
                                 prior_run_files_preserved=len(before), prior_asset_files_preserved=len(assets_before),
                                 original_files_preserved=len(original_before), original_unchanged_after_retraining=True,
                                 historical_interruption_preserved=True, returned_to_current='RUN ' + retry + '-video',
                                 persistent_server=True, same_machine_private_network=True))
    print('interruption lifecycle passed', flush=True)


if __name__ == '__main__':
    main()
