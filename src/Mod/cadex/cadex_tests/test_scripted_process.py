# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Process-isolation checks for scripted CAD workers."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import time
import signal

import pytest

from CadexScriptedProcess import run_process


def test_large_worker_output_cannot_fill_a_parent_pipe(tmp_path: Path) -> None:
    command = [
        sys.executable,
        "-c",
        (
            "import sys;"
            "sys.stdout.write('o' * 2_000_000 + 'STDOUT_END\\n');"
            "sys.stderr.write('e' * 2_000_000 + 'STDERR_END\\n')"
        ),
    ]

    result = run_process(
        command,
        cwd=tmp_path,
        environment=dict(os.environ),
        cancellation_check=None,
        timeout_seconds=10.0,
        memory_limit_bytes=0,
    )

    assert result["started"] is True
    assert result["returncode"] == 0
    assert result["timed_out"] is False
    assert result["stdout"].endswith(f"STDOUT_END{os.linesep}")
    assert result["stderr"].endswith(f"STDERR_END{os.linesep}")
    assert len(result["stdout"]) <= 16_000
    assert len(result["stderr"]) <= 16_000


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process groups")
def test_cancel_kills_a_nested_worker_that_ignores_sigterm(tmp_path):
    ready = tmp_path / "ready"
    heartbeat = tmp_path / "heartbeat"
    child = (
        "import os,signal,time; from pathlib import Path; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        f"Path({str(ready)!r}).write_text(str(os.getpid())); "
        f"\nwhile True: Path({str(heartbeat)!r}).write_text(str(time.monotonic())); time.sleep(.01)"
    )
    leader = ("import subprocess,sys,time; "
              f"subprocess.Popen([sys.executable, '-c', {child!r}]); time.sleep(30)")
    try:
        result = run_process([sys.executable, "-c", leader], cwd=tmp_path,
                             environment=dict(os.environ),
                             cancellation_check=lambda: heartbeat.exists(),
                             timeout_seconds=10, memory_limit_bytes=0)
        assert result["cancelled"], result
        time.sleep(.1)
        last = heartbeat.read_text()
        time.sleep(.15)
        assert heartbeat.read_text() == last, "nested worker survived cancellation"
    finally:
        if ready.exists():
            try:
                os.kill(int(ready.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass
