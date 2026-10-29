# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Cloud billing, transfer and supervisor boundaries; no account or GPU needed."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

import runpod


def options(tmp_path):
    key = tmp_path / 'key'
    key.write_text('private fixture, not a real key')
    key.with_suffix('.pub').write_text('ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest fixture')
    return argparse.Namespace(state=tmp_path / 'worker.json', ssh_key=str(key),
        gpu='NVIDIA GeForce RTX 4090', name='test', data_center=None,
        max_hours=2, dry_run=False)


def test_plan_has_no_credentials_or_billable_call(tmp_path, monkeypatch, capsys):
    args = options(tmp_path)
    args.dry_run = True
    monkeypatch.setenv('RUNPOD_API_KEY', 'secret-sentinel')
    monkeypatch.setattr(runpod, 'api', lambda *a: pytest.fail('plan called provider'))
    runpod.up(args)
    output = capsys.readouterr().out
    plan = json.loads(output)
    assert not plan['executed'] and 'secret-sentinel' not in output
    assert plan['request']['interruptible'] is False
    assert plan['request']['volumeInGb'] > 0
    assert not args.state.exists()


def test_failed_bootstrap_stops_and_retains_locator(tmp_path, monkeypatch):
    args = options(tmp_path)
    calls = []
    def api(method, path, payload=None):
        calls.append((method, path))
        return {'id': 'test-pod'}
    monkeypatch.setattr(runpod, 'api', api)
    def fail(*args):
        raise runpod.CloudError('bootstrap failed')
    monkeypatch.setattr(runpod, 'connect', fail)
    with pytest.raises(runpod.CloudError, match='bootstrap failed'):
        runpod.up(args)
    assert json.loads(args.state.read_text())['pod_id'] == 'test-pod'
    assert calls == [('POST', '/pods'), ('POST', '/pods/test-pod/stop')]
    assert args.state.stat().st_mode & 0o777 == 0o600


def test_budget_rejected_before_dispatch(tmp_path, monkeypatch):
    args = argparse.Namespace(budget_s=1000)
    monkeypatch.setattr(runpod, 'ssh', lambda *a, **k: pytest.fail('contacted worker'))
    with pytest.raises(runpod.CloudError, match='remaining Pod lease'):
        runpod.train(args, {'ready': True, 'deadline': time.time() + 100})


def test_supervisor_budget_kills_trainer_and_preserves_checkpoint(tmp_path):
    checkpoint = tmp_path / 'best.cxpolicy'
    checkpoint.write_bytes(b'checkpoint-fixture')
    worker = Path(runpod.HERE) / 'runpod_worker.py'
    result = subprocess.run([sys.executable, str(worker), '--seconds', '1', '--',
        sys.executable, '-c', 'import time; time.sleep(30)'], cwd=tmp_path, timeout=15)
    assert result.returncode != 0
    progress = json.loads((tmp_path / 'progress.json').read_text())
    assert progress['state'] == 'failed' and progress['error'] == 'budget_exhausted'
    assert checkpoint.read_bytes() == b'checkpoint-fixture'


def test_supervisor_keeps_success_receipt(tmp_path):
    result = subprocess.run([sys.executable, str(runpod.HERE / 'runpod_worker.py'),
        '--seconds', '10', '--', sys.executable, '-c',
        'print(\'{"device":"gpu","sha256":"fixture"}\')'],
        cwd=tmp_path, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0
    assert json.loads(result.stdout)['device'] == 'gpu'
    assert json.loads((tmp_path / 'worker-exit.json').read_text())['returncode'] == 0
    assert not (tmp_path / 'progress.json').exists()


def test_remote_sync_publishes_previews_and_dashboard_snapshot(tmp_path):
    # Run the real Bash sync function against an rsync stand-in, then force
    # a transfer failure. Never publish a new progress snapshot on failure.
    script = (runpod.HERE / 'remote_train.sh').read_text()
    body = script[script.index('sync_run() {'):script.index('\n# Read one field', script.index('sync_run() {'))]
    dest = tmp_path / 'train'
    dest.mkdir()
    harness = '''set -eu
rsync_ssh=ssh; target=box
rsync() {
    case "$*" in
        *progress.json*) printf '{"state":"done"}' > "${@: -1}" ;;
        *) if [ "${FAIL:-0}" = 1 ]; then return 1; fi
           mkdir -p "$DEST/view"; echo mesh > "$DEST/view/body.stl"
           echo policy > "$DEST/result.cxpolicy" ;;
    esac
}
'''
    command = harness + body + '\nsync_run /remote "$DEST"\n'
    env = dict(os.environ, DEST=str(dest))
    subprocess.run(['bash', '-c', command], env=env, check=True)
    assert (dest / 'view/body.stl').exists()
    assert (dest / 'progress.json').read_bytes() == (dest / 'training-progress.json').read_bytes()
    (dest / 'progress.json').write_text('{"state":"training"}')
    result = subprocess.run(['bash', '-c', command], env=dict(env, FAIL='1'))
    assert result.returncode != 0
    assert json.loads((dest / 'progress.json').read_text())['state'] == 'training'


def test_failed_collection_never_stops_pod(tmp_path, monkeypatch):
    out = tmp_path / 'runs/smoke'
    out.mkdir(parents=True)
    (out / 'cloud.json').write_text(json.dumps({'pod_id': 'test-pod'}))
    (out / 'walk-pending.json').write_text(json.dumps({'training': {'run_id': 'remote-1'}}))
    state = dict(pod_id='test-pod', host='127.0.0.1', port=22, ssh_key='/key',
                 remote_repo='/repo', remote_venv='/venv')
    args = argparse.Namespace(project=tmp_path, run='smoke', watch=False, stop=True)
    monkeypatch.setattr(runpod, 'api', lambda *a: {'desiredStatus': 'RUNNING'})
    def failed_pull(*a, **kw):
        return subprocess.CompletedProcess(a[0], 1)
    monkeypatch.setattr(runpod.subprocess, 'run', failed_pull)
    monkeypatch.setattr(runpod, 'stop_pod', lambda *a: pytest.fail('stopped with uncollected results'))
    with pytest.raises(runpod.CloudError, match='No complete result'):
        runpod.collect(args, state)


def test_stopped_pod_does_not_poll_forever(tmp_path, monkeypatch):
    out = tmp_path / 'runs/smoke'
    out.mkdir(parents=True)
    (out / 'cloud.json').write_text(json.dumps({'pod_id': 'test-pod'}))
    (out / 'walk-pending.json').write_text(json.dumps({'training': {'run_id': 'remote-1'}}))
    state = dict(pod_id='test-pod', host='127.0.0.1', port=22, ssh_key='/key',
                 remote_repo='/repo', remote_venv='/venv')
    args = argparse.Namespace(project=tmp_path, run='smoke', watch=True, stop=True)
    monkeypatch.setattr(runpod, 'api', lambda *a: {'desiredStatus': 'EXITED'})
    monkeypatch.setattr(runpod.subprocess, 'run', lambda *a, **k: pytest.fail('attempted SSH to stopped Pod'))
    with pytest.raises(runpod.CloudError, match='Pod is stopped'):
        runpod.collect(args, state)


def test_lease_key_only_travels_on_stdin(monkeypatch):
    monkeypatch.setenv('RUNPOD_API_KEY', 'private-sentinel')
    calls = []
    monkeypatch.setattr(runpod, 'ssh', lambda *a, **kw: calls.append((a, kw)))
    runpod.arm_lease({'pod_id': 'test', 'deadline': 123})
    args, kw = calls[0]
    assert 'private-sentinel' not in repr(args)
    assert json.loads(kw['input'])['api_key'] == 'private-sentinel'


def test_worker_signal_stops_process_group(tmp_path):
    # An actual child process writes its PID, then ignores TERM: verify the
    # supervisor's escalation ends the child, not just its wrapping process.
    child = "import os,time,signal; signal.signal(signal.SIGTERM,signal.SIG_IGN); open('child.pid','w').write(str(os.getpid())); time.sleep(60)"
    worker = subprocess.Popen([sys.executable, str(runpod.HERE / 'runpod_worker.py'),
        '--seconds', '60', '--', sys.executable, '-c', child], cwd=tmp_path)
    try:
        end = time.monotonic() + 5
        while not (tmp_path / 'child.pid').exists() and time.monotonic() < end:
            time.sleep(.05)
        child_pid = int((tmp_path / 'child.pid').read_text())
        worker.terminate()
        assert worker.wait(timeout=15) != 0
        with pytest.raises(ProcessLookupError):
            os.kill(child_pid, 0)
        assert json.loads((tmp_path / 'progress.json').read_text())['error'] == 'stopped'
    finally:
        if worker.poll() is None:
            worker.kill()
            worker.wait()


def test_runpod_mount_regressions(tmp_path, monkeypatch):
    """Live A40: mounted disk reports 0666 and refuses rsync chown."""
    spec = runpod.create_spec(options(tmp_path))
    startup = spec['dockerStartCmd'][0]
    assert 'cp /workspace/cadex/ssh/host_ed25519 /etc/ssh/cadex_host_ed25519' in startup
    assert 'chmod 600 /etc/ssh/cadex_host_ed25519' in startup
    assert 'sshd -D -e -h /etc/ssh/cadex_host_ed25519' in startup
    # The live host advertised CUDA 13.2; enumerating future driver versions
    # falsely rejected compatible hardware before the actual GPU check.
    assert 'allowedCudaVersions' not in spec
    calls = []
    monkeypatch.setattr(runpod.subprocess, 'run', lambda args, **kw: calls.append(args))
    runpod.upload({'ssh_key': '/key', 'port': 22, 'host': 'example'}, ['/file'], '/workspace')
    assert calls[0][1] == '-rt'


def test_provider_request_sets_user_agent(monkeypatch):
    """The live provider returned 403 for urllib's default User-Agent."""
    monkeypatch.setenv('RUNPOD_API_KEY', 'fixture')
    requests = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'[]'
    def open_request(request, **kwargs):
        requests.append(request)
        return Response()
    monkeypatch.setattr(runpod.urllib.request, 'urlopen', open_request)
    assert runpod.api('GET', '/pods') == []
    assert requests[0].get_header('User-agent') == 'cadex-runpod/1.0'


def test_preflight_accepts_uploaded_trainer_without_git(tmp_path):
    """Live upload has matching trainer bytes but no optional Git 'at' row."""
    source = (runpod.HERE / 'remote_train.sh').read_text()
    body = source[source.index('cmd_check() {'):source.index('\n# ---------------------------------------------------------------------------\n# train')]
    import hashlib
    digest = hashlib.sha256((runpod.HERE / 'cadex_train.py').read_bytes()).hexdigest()
    report = '\n'.join(['host fixture', 'repo ok', 'work ok', 'venv ok',
                         'trainer ' + digest, 'backend gpu', 'pkg jaxlib 0.7.2'] +
                        ['pkg ' + line.replace('==', ' ') for line in
                         (runpod.HERE / 'requirements.txt').read_text().splitlines()
                         if line and not line.startswith('#') and '==' in line])
    fixture = tmp_path / 'probe'
    fixture.write_text(report)
    harness = '''set -euo pipefail
load_config() { :; }
require() { :; }
resolve_remote_paths() { :; }
shquote() { printf %s "$1"; }
on_box() { cat "$PROBE"; }
sha256_of() { shasum -a 256 "$1" | cut -c1-64; }
target=fixture; remote_repo=/repo; remote_venv=/venv; remote_work=/work
here="$TRAINING"; requirements="$here/requirements.txt"
'''
    result = subprocess.run(['bash', '-c', harness + body + '\ncmd_check\n'],
        env={**os.environ, 'PROBE': str(fixture), 'TRAINING': str(runpod.HERE)},
        capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '==> ready.' in result.stdout
