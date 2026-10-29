#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Runpod workers for Cadex's existing remote training workflow (ADR-872).

Stdlib only. RUNPOD_API_KEY is read from the environment, never saved locally.
Use --help and training/SETUP.md. No engine or cloud SDK is imported.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
API = 'https://rest.runpod.io/v1'
REMOTE = '/workspace/cadex'
IMAGE = 'nvidia/cuda:12.6.3-base-ubuntu24.04'


class CloudError(RuntimeError):
    pass


def api(method: str, path: str, payload=None):
    key = os.environ.get('RUNPOD_API_KEY', '').strip()
    if not key:
        raise CloudError('Set RUNPOD_API_KEY in your terminal (do not put it in the repo).')
    request = urllib.request.Request(API + path, method=method,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json',
                 'User-Agent': 'cadex-runpod/1.0'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
        return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        # Provider responses may echo request bodies. Never print them or the key.
        raise CloudError(f'Runpod {method} {path}: HTTP {exc.code}; check the console.') from None
    except (OSError, ValueError) as exc:
        raise CloudError(f'Runpod {method} {path}: {type(exc).__name__}; check the console before retrying a create.') from None


def save(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    with temp.open('w') as file:
        os.chmod(temp, 0o600)
        json.dump(data, file, indent=2)
        file.write('\n')
    temp.replace(path)


@contextmanager
def worker_lock(path: Path):
    """Serialize billable lifecycle changes for one local worker locator."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix('.lock').open('a') as file:
        try:
            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise CloudError('Another process is changing this worker; wait for it to finish.') from None
        yield


def load(path: Path):
    try:
        state = json.loads(path.read_text())
    except (OSError, ValueError):
        raise CloudError(f'No valid worker state at {path}; run up first.') from None
    if not re.fullmatch(r'[A-Za-z0-9_-]+', state.get('pod_id', '')):
        raise CloudError('Invalid Pod ID in worker state.')
    return state


def ssh(state, command, *, input=None, capture=False, check=True, timeout=60):
    return subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
        '-o', 'StrictHostKeyChecking=accept-new', '-i', state['ssh_key'],
        '-p', str(state['port']), 'root@' + state['host'], command],
        input=input, text=True, capture_output=capture, check=check, timeout=timeout)


def env_for(state):
    env = os.environ.copy()
    env.update(CADEX_TRAIN_SSH_HOST=state['host'], CADEX_TRAIN_SSH_USER='root',
        CADEX_TRAIN_SSH_PORT=str(state['port']), CADEX_TRAIN_SSH_KEY=state['ssh_key'],
        CADEX_TRAIN_REPO=state['remote_repo'], CADEX_TRAIN_VENV=state['remote_venv'],
        CADEX_TRAIN_WORK=REMOTE + '/jobs')
    return env


def create_spec(args):
    public = Path(str(Path(args.ssh_key).expanduser()) + '.pub').read_text().strip()
    if '\n' in public or not public.startswith(('ssh-ed25519 ', 'ssh-rsa ', 'ecdsa-')):
        raise CloudError('Expected one OpenSSH public key beside --ssh-key, with suffix .pub.')
    startup = '''set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends openssh-server rsync python3 python3-venv ca-certificates libegl1 libgl1
mkdir -p /run/sshd /root/.ssh
chmod 700 /root/.ssh
printf '%s\\n' "$PUBLIC_KEY" > /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
mkdir -p /workspace/cadex/ssh
if [ ! -f /workspace/cadex/ssh/host_ed25519 ]; then
    ssh-keygen -q -t ed25519 -N '' -f /workspace/cadex/ssh/host_ed25519
fi
cp /workspace/cadex/ssh/host_ed25519 /etc/ssh/cadex_host_ed25519
chmod 600 /etc/ssh/cadex_host_ed25519
exec /usr/sbin/sshd -D -e -h /etc/ssh/cadex_host_ed25519
'''
    spec = dict(name=args.name, imageName=IMAGE, cloudType='SECURE', computeType='GPU',
        gpuTypeIds=[args.gpu], gpuCount=1, interruptible=False,
        supportPublicIp=True, ports=['22/tcp'], containerDiskInGb=20,
        volumeInGb=40, volumeMountPath='/workspace',
        dockerEntrypoint=['/bin/bash', '-c'], dockerStartCmd=[startup],
        env={'PUBLIC_KEY': public, 'NVIDIA_VISIBLE_DEVICES': 'all',
             'NVIDIA_DRIVER_CAPABILITIES': 'compute,utility'})
    if args.data_center:
        spec['dataCenterIds'] = [args.data_center]
    return spec


def connect(state, state_path, wait_s=900):
    end = time.monotonic() + wait_s
    while time.monotonic() < end:
        pod = api('GET', '/pods/' + state['pod_id'])
        port = (pod.get('portMappings') or {}).get('22')
        host = pod.get('publicIp')
        if host and port:
            ipaddress.ip_address(host)
            if not 0 < int(port) < 65536:
                raise CloudError('Invalid SSH port returned by Runpod.')
            state.update(host=host, port=int(port))
            save(state_path, state)
            if ssh(state, 'true', capture=True, check=False).returncode == 0:
                return
        print('Waiting for the Pod and full SSH...', file=sys.stderr, flush=True)
        time.sleep(10)
    raise CloudError('Pod did not become SSH-ready in 15 minutes.')


def upload(state, sources, destination):
    transport = shlex.join(['ssh', '-o', 'BatchMode=yes', '-i', state['ssh_key'],
                            '-p', str(state['port'])])
    subprocess.run(['rsync', '-rt', '-e', transport, *map(str, sources),
                    f"root@{state['host']}:{destination}/"], check=True, timeout=120)


def arm_lease(state):
    """Send credentials through encrypted stdin, only to the watchdog's memory."""
    launcher = '''import json, subprocess, sys, time, pathlib
config = json.load(sys.stdin)
log = open('/tmp/cadex-lease.log', 'a')
p = subprocess.Popen(['python3', '/workspace/cadex/runpod_worker.py', '--lease'],
    stdin=subprocess.PIPE, stdout=log, stderr=log, start_new_session=True, text=True)
p.stdin.write(json.dumps(config)); p.stdin.close()
for _ in range(50):
    marker = pathlib.Path('/tmp/cadex-lease.json')
    if marker.exists() and json.loads(marker.read_text()).get('pid') == p.pid:
        print('Pod shutdown watchdog armed'); sys.exit(0)
    if p.poll() is not None: sys.exit(1)
    time.sleep(.1)
sys.exit(1)
'''
    config = dict(pod_id=state['pod_id'], deadline=state['deadline'],
                  api_key=os.environ['RUNPOD_API_KEY'])
    ssh(state, 'python3 -c ' + shlex.quote(launcher), input=json.dumps(config))


def setup(state, state_path):
    ssh(state, 'mkdir -p /workspace/cadex/jobs')
    upload(state, [HERE / 'runpod_worker.py'], REMOTE)
    arm_lease(state)
    # Content-address the environment and trainer so setup never changes an active run.
    files = [HERE / name for name in (
        'cadex_train.py', 'cadex_goto.py', 'requirements.txt', 'runpod_worker.py')]
    digest = hashlib.sha256(b''.join(p.read_bytes() for p in files)).hexdigest()[:16]
    state['remote_repo'] = f'{REMOTE}/releases/{digest}'
    state['remote_venv'] = state['remote_repo'] + '/venv'
    target = state['remote_repo'] + '/training'
    ssh(state, 'mkdir -p ' + shlex.quote(target))
    upload(state, files, target)
    python = state['remote_venv'] + '/bin/python'
    cmd = f'''set -eu
python3 -m venv {shlex.quote(state['remote_venv'])}
{shlex.quote(python)} -m pip install -r {shlex.quote(target + '/requirements.txt')} 'jax[cuda12]==0.7.2'
{shlex.quote(python)} -c 'import jax; assert jax.default_backend() == "gpu", jax.devices(); print(jax.devices())'
'''
    ssh(state, cmd, timeout=max(60, int(state['deadline'] - time.time())))
    subprocess.run(['bash', str(HERE / 'remote_train.sh'), 'check'],
                   env=env_for(state), check=True, timeout=120)
    state['ready'] = True
    save(state_path, state)


def stop_pod(state):
    api('POST', '/pods/' + state['pod_id'] + '/stop')
    print('Pod stop requested. Its persistent disk is retained and still incurs storage charges.')


def up(args):
    if args.dry_run:
        return create_worker(args)
    with worker_lock(args.state):
        return create_worker(args)


def create_worker(args):
    if args.state.exists() and not args.dry_run:
        raise CloudError('Worker state already exists. Use start/status; do not overwrite a rented Pod.')
    key = Path(args.ssh_key).expanduser().resolve()
    if not key.is_file() or any(c.isspace() for c in str(key)):
        raise CloudError('--ssh-key must be an existing private key path without whitespace.')
    spec = create_spec(args)
    if args.dry_run:
        print(json.dumps({'request': spec, 'max_hours': args.max_hours,
                          'state': str(args.state), 'executed': False}, indent=2))
        return
    pod = api('POST', '/pods', spec)
    state = dict(pod_id=pod['id'], ssh_key=str(key), ready=False,
                 deadline=time.time() + args.max_hours * 3600)
    # Save immediately: even a failed bootstrap leaves a recoverable Pod locator.
    try:
        save(args.state, state)
        print('Created Pod ' + state['pod_id'], flush=True)
        connect(state, args.state)
        setup(state, args.state)
    except BaseException:
        stop_pod(state)
        raise
    print('Worker ready. Use train; status and stop also accept this --state path.')


def train(args, state):
    if not state.get('ready'):
        raise CloudError('Worker is not prepared; use start first.')
    if time.time() + args.budget_s + 120 >= state['deadline']:
        raise CloudError('Training budget exceeds the remaining Pod lease (including 2 minutes to collect).')
    probe = "import json,os,time; d=json.load(open('/tmp/cadex-lease.json')); os.kill(d['pid'],0); assert d['deadline'] > time.time()"
    ssh(state, 'python3 -c ' + shlex.quote(probe))
    project = args.project.expanduser().resolve()
    if not re.fullmatch(r'[a-z0-9][a-z0-9._-]*', args.run):
        raise CloudError('Use a short run name with lowercase letters, numbers, dots, underscores or hyphens.')
    out = project / 'runs' / args.run
    if out.exists():
        raise CloudError(f'Run already exists: {out}')
    flags = args.flags[1:] if args.flags[:1] == ['--'] else args.flags
    forbidden = ('--project', '--out', '--remote', '--detach', '--complete', '--dry-run', '--allow-cpu')
    if any(flag.split('=')[0] in forbidden for flag in flags):
        raise CloudError('Pass only trainer settings after --; project, output and remote mode are managed here.')
    env = env_for(state)
    env['CADEX_TRAIN_BUDGET_S'] = str(args.budget_s)
    save(out / 'cloud.json', {'pod_id': state['pod_id'], 'state_file': str(args.state),
                              'budget_s': args.budget_s})
    subprocess.run([str(REPO / 'cadex'), 'walk', '--project', str(project),
        '--out', str(out), '--remote', '--detach', *flags], env=env, check=True)
    print(f'Run dispatched. Collect with: python3 training/runpod.py --state {shlex.quote(str(args.state))} collect --project {shlex.quote(str(project))} --run {args.run}')


def collect(args, state):
    if not re.fullmatch(r'[a-z0-9][a-z0-9._-]*', args.run):
        raise CloudError('Invalid run name.')
    out = args.project.expanduser().resolve() / 'runs' / args.run
    marker = json.loads((out / 'walk-pending.json').read_text())
    cloud = json.loads((out / 'cloud.json').read_text())
    if cloud['pod_id'] != state['pod_id']:
        raise CloudError('This run belongs to a different Pod; use its recorded state file.')
    run_id = marker['training']['run_id']
    if not re.fullmatch(r'[A-Za-z0-9._-]+', run_id):
        raise CloudError('Invalid remote run ID.')
    dest = Path(marker['training'].get('destination') or out / 'train').resolve()
    if not dest.is_relative_to(out):
        raise CloudError('Collection destination is outside this run.')
    env = env_for(state)
    dispatcher = ['bash', str(HERE / 'remote_train.sh')]
    env['CADEX_TRAIN_STRICT_SYNC'] = '1'
    while True:
        pod = api('GET', '/pods/' + state['pod_id'])
        if pod.get('desiredStatus') != 'RUNNING':
            raise CloudError('Pod is stopped. Use start to retrieve its retained files, then collect again.')
        fetched = subprocess.run([*dispatcher, 'pull', run_id, str(dest)], env=env, timeout=90)
        if fetched.returncode == 0:
            progress = json.loads((dest / 'training-progress.json').read_text())
            print(f"Training: {progress.get('state')}, iteration {progress.get('iteration')}", flush=True)
            if progress.get('state') == 'failed':
                raise CloudError(f"Training failed: {progress.get('error')}. Checkpoints and logs retained in {dest}.")
            if progress.get('state') == 'done':
                break
        if not args.watch:
            raise CloudError('No complete result yet; collect --watch to follow this run.')
        time.sleep(10)
    subprocess.run([str(REPO / 'cadex'), 'walk', '--complete', '--project',
                    str(args.project.resolve()), '--out', str(out)], env=env, check=True)
    if args.stop:
        stop_pod(state)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, default=HERE / '.runpod.json')
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('up', help='Rent and prepare one on-demand GPU Pod')
    create.add_argument('--ssh-key', required=True)
    create.add_argument('--gpu', default='NVIDIA GeForce RTX 4090')
    create.add_argument('--name', default='cadex-training')
    create.add_argument('--data-center')
    create.add_argument('--max-hours', type=float, default=2)
    create.add_argument('--dry-run', action='store_true')
    start = commands.add_parser('start', help='Resume the retained Pod and rearm its lease')
    start.add_argument('--max-hours', type=float, default=2)
    commands.add_parser('status', help='Show status without revealing provider environment variables')
    commands.add_parser('stop', help='Stop GPU billing; retain the Pod disk')
    run = commands.add_parser('train', help='Export locally and dispatch a bounded detached walk')
    run.add_argument('--project', type=Path, required=True)
    run.add_argument('--run', required=True)
    run.add_argument('--budget-s', type=int, required=True)
    run.add_argument('flags', nargs=argparse.REMAINDER)
    pull = commands.add_parser('collect', help='Pull results, verify locally, optionally stop the Pod')
    pull.add_argument('--project', type=Path, required=True)
    pull.add_argument('--run', required=True)
    pull.add_argument('--watch', action='store_true')
    pull.add_argument('--stop', action='store_true')
    args = parser.parse_args(argv)
    args.state = args.state.expanduser().resolve()
    try:
        if hasattr(args, 'max_hours') and not 0 < args.max_hours <= 24:
            raise CloudError('--max-hours must be greater than zero and at most 24.')
        if hasattr(args, 'budget_s') and args.budget_s < 1:
            raise CloudError('--budget-s must be positive.')
        if args.command == 'up':
            up(args)
            return 0
        state = load(args.state)
        if args.command == 'status':
            pod = api('GET', '/pods/' + state['pod_id'])
            print(json.dumps({key: pod.get(key) for key in
                ('id', 'name', 'desiredStatus', 'costPerHr', 'publicIp', 'portMappings')}, indent=2))
        elif args.command == 'stop':
            stop_pod(state)
        elif args.command == 'start':
            with worker_lock(args.state):
                state = load(args.state)
                pod = api('GET', '/pods/' + state['pod_id'])
                if pod.get('desiredStatus') == 'RUNNING':
                    raise CloudError('Pod is already running; stop it before renewing its lease.')
                api('POST', '/pods/' + state['pod_id'] + '/start')
                state.update(ready=False, deadline=time.time() + args.max_hours * 3600)
                try:
                    save(args.state, state)
                    connect(state, args.state)
                    setup(state, args.state)
                except BaseException:
                    stop_pod(state)
                    raise
        elif args.command == 'train':
            train(args, state)
        elif args.command == 'collect':
            collect(args, state)
        return 0
    except (CloudError, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f'runpod: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
