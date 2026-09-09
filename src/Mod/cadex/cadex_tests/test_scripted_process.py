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


def test_worker_environment_pins_the_blas_thread_pool(tmp_path, monkeypatch) -> None:
    """A worker's BLAS pool is sized by us, never by the host's core count.

    OpenBLAS reserves a per-thread scratch buffer when its shared object is
    loaded, so on a many-core host `import numpy` -- which `assembly.mjcf`
    reaches through mujoco -- reserved 4.4 GB of address space before doing
    any arithmetic, overran the worker's RLIMIT_AS, and spun in OpenBLAS's
    allocation retry loop until RLIMIT_CPU killed the worker (ADR-250).
    """

    from CadexScriptedRuntime import WORKER_BLAS_THREADS, worker_environment

    monkeypatch.setenv("OPENBLAS_NUM_THREADS", "128")
    environment = worker_environment(tmp_path)

    assert environment["OPENBLAS_NUM_THREADS"] == str(WORKER_BLAS_THREADS)
    assert 1 <= WORKER_BLAS_THREADS <= 8


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX resource limits")
def test_a_cpu_cap_kill_is_a_budget_refusal_not_a_missing_result(tmp_path) -> None:
    """SIGXCPU is a cap being enforced, and the failure has to say which cap.

    `RLIMIT_CPU` is charged in CPU-seconds across every thread, while
    `run_process`'s watchdog counts the same number in wall-clock seconds,
    so a parallel worker reaches the kernel's limit first. It then dies
    leaving no `result.json`, and that used to surface as the generic
    "exited without a result" -- a crash, as far as any reader could tell.
    """

    from CadexScriptedRuntime import _resource_signal_failure

    burn = (
        "import resource;"
        "resource.setrlimit(resource.RLIMIT_CPU, (1, resource.getrlimit(resource.RLIMIT_CPU)[1]));"
        "\nwhile True: pass"
    )
    process = run_process(
        [sys.executable, "-c", burn],
        cwd=tmp_path,
        environment=dict(os.environ),
        cancellation_check=None,
        timeout_seconds=60.0,
        memory_limit_bytes=0,
    )

    assert process["started"] is True
    assert process["timed_out"] is False
    assert process["returncode"] == -signal.SIGXCPU

    failure = _resource_signal_failure(process, {"tool_name": "write_script", "timeout_seconds": 300.0})

    assert failure is not None
    assert failure["ok"] is False
    assert failure["failure_code"] == "DOMAIN_CPU_LIMIT_EXCEEDED"
    assert "300 CPU-seconds" in failure["error"]
    assert "wall-clock" in failure["error"]
    assert failure["observed"]["returncode"] == -signal.SIGXCPU

    clean = dict(process, returncode=0)
    assert _resource_signal_failure(clean, {"tool_name": "write_script", "timeout_seconds": 300.0}) is None
