# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Trainer guard tests use fake /proc entries; they never launch training."""
import json
from pathlib import Path
import threading

import pytest

from interruption import TrainerGuard, trainers


def process(root, pid, argv, scope='tests.scope'):
    entry = root / str(pid)
    entry.mkdir()
    (entry / 'cmdline').write_bytes(b'\0'.join(a.encode() for a in argv) + b'\0')
    (entry / 'cgroup').write_text('0::/user.slice/' + scope + '\n')


def test_scan_includes_cpu_absolute_and_module_trainers_but_not_wrappers(tmp_path):
    process(tmp_path, 1, ['/venv/bin/python', '/repo/training/cadex_train.py', '--device', 'cpu'])
    process(tmp_path, 2, ['python3', 'training/cadex_train.py'])
    process(tmp_path, 3, ['python', '-m', 'training.cadex_train'])
    process(tmp_path, 4, ['timeout', '900', 'python', 'training/cadex_train.py'])
    process(tmp_path, 5, ['bash', '-c', 'python training/cadex_train.py'])
    process(tmp_path, 6, ['python', '-m', 'pytest'])
    (tmp_path / '7').mkdir()  # exited during scan
    assert [r['pid'] for r in trainers(tmp_path)] == [1, 2, 3, 6]


def test_preflight_refuses_even_one_existing_cpu_trainer(tmp_path):
    process(tmp_path, 1, ['python', 'training/cadex_train.py', '--device', 'cpu'])
    receipt = tmp_path / 'receipt.json'
    guard = TrainerGuard(receipt, 'probe', scan=lambda: trainers(tmp_path))
    with pytest.raises(RuntimeError, match='exclusion violated'):
        guard.start()
    assert guard.thread is None
    assert json.loads(receipt.read_text())['max_trainers'] == 1


def test_background_guard_latches_cpu_overlap_while_caller_is_blocked(tmp_path):
    rows = []
    stopped = threading.Event()
    guard = TrainerGuard(tmp_path / 'receipt.json', 'probe', scan=lambda: list(rows), stop_scope=stopped.set)
    guard.start()
    rows[:] = [dict(pid=1, scopes=['probe.scope']), dict(pid=2, scopes=['tests.scope'])]
    assert stopped.wait(2), 'monitor must detect overlap without caller polling'
    rows.clear()  # a later clean scan must not erase the violation
    with pytest.raises(RuntimeError, match='exclusion violated'):
        guard.close()
    assert guard.report['max_trainers'] == 2
    assert guard.report['observed_pids'] == [1, 2]


def test_own_scope_is_allowed_but_duplicate_trainers_are_not(tmp_path):
    rows = [dict(pid=1, scopes=['probe.scope'])]
    guard = TrainerGuard(tmp_path / 'receipt.json', 'probe', scan=lambda: rows)
    guard.sample()
    rows.append(dict(pid=2, scopes=['probe.scope']))
    with pytest.raises(RuntimeError, match='exclusion violated'):
        guard.sample()


def test_unreadable_scan_fails_closed(tmp_path):
    def denied():
        raise PermissionError('unreadable process')
    guard = TrainerGuard(tmp_path / 'receipt.json', 'probe', scan=denied)
    with pytest.raises(PermissionError):
        guard.start()
    assert 'unreadable process' in guard.report['violation']
