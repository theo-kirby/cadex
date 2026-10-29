# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Offboard process supervisor and Pod lease watchdog (ADR-872). Stdlib only."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request


def atomic_json(path: Path, value: dict) -> None:
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value) + '\n')
    tmp.replace(path)


def supervise(seconds: int, command: list[str]) -> int:
    """Bound the actual trainer, preserving its stdout receipt and progress."""
    env = os.environ.copy()
    env.setdefault('CADEX_JAX_CACHE', '/workspace/cadex/cache/jax')
    process = subprocess.Popen(command, start_new_session=True, env=env)
    stopped = False

    def stop(signum, frame):
        nonlocal stopped
        stopped = True
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    deadline = time.monotonic() + seconds
    reason = ''
    while process.poll() is None:
        if stopped or time.monotonic() >= deadline:
            reason = 'stopped' if stopped else 'budget_exhausted'
            stop(None, None)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            break
        time.sleep(0.2)
    code = process.returncode
    if code or reason:
        path = Path('progress.json')
        try:
            progress = json.loads(path.read_text())
        except (OSError, ValueError):
            progress = {'schema': 'cadex-training-progress-v1'}
        progress.update(state='failed', error=reason or f'trainer exited {code}',
                        updated_at=time.time())
        atomic_json(path, progress)
    atomic_json(Path('worker-exit.json'), {'returncode': code, 'reason': reason,
                                         'finished_at': time.time()})
    return 1 if reason else code


def lease(config: dict) -> None:
    """Keep the key in memory only; retry stop on transient provider failures.

    This is a best-effort billing guard, not a provider-enforced spending cap.
    Pod disks survive stop. We never delete a Pod or its files.
    """
    deadline = float(config['deadline'])
    pod_id = config['pod_id']
    key = config.pop('api_key')
    marker = Path('/tmp/cadex-lease.json')
    atomic_json(marker, {'pid': os.getpid(), 'deadline': deadline, 'pod_id': pod_id})
    while time.time() < deadline:
        time.sleep(min(10, max(0, deadline - time.time())))
    request = urllib.request.Request(
        f'https://rest.runpod.io/v1/pods/{pod_id}/stop', data=b'', method='POST',
        headers={'Authorization': f'Bearer {key}', 'User-Agent': 'cadex-runpod/1.0'})
    while True:
        try:
            with urllib.request.urlopen(request, timeout=30):
                pass
            # Keep retrying until the provider actually stops this process.
            time.sleep(30)
        except Exception as exc:
            print(f'Pod stop retry: {type(exc).__name__}', file=sys.stderr, flush=True)
            time.sleep(30)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lease', action='store_true')
    parser.add_argument('--seconds', type=int)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.lease:
        lease(json.load(sys.stdin))
    else:
        if not args.seconds or args.seconds < 1:
            parser.error('--seconds must be positive')
        command = args.command[1:] if args.command[:1] == ['--'] else args.command
        if not command:
            parser.error('a trainer command is required')
        sys.exit(supervise(args.seconds, command))
