# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A CPU refusal names where the budget went, and fit stops paying for proved zeros (ADR-436).

``ot10-hexapod-10`` met ``DOMAIN_CPU_LIMIT_EXCEEDED`` six times. The
refusal named no stage, so the agent could only guess what to cut. Measured
with the ledger, the build spent 119 CPU-s on geometry and then ran out in
the static fit: ``common`` on its tub and dome, which sit 2.4 mm apart, ran
past 137 CPU-s on a volume the distance had already proved to be zero.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import sys
from types import SimpleNamespace

import pytest

import cadex_assembly_worker
import cadex_domain_worker
from CadexScriptedProcess import run_process
from CadexScriptedRuntime import _resource_signal_failure

MODULE_DIR = Path(cadex_domain_worker.__file__).resolve().parent


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    path = tmp_path / "progress.json"
    monkeypatch.setenv(cadex_domain_worker.PROGRESS_ENV, str(path))
    monkeypatch.setattr(cadex_domain_worker, "_progress", {"current": None, "finished": []})
    return path


class _Box:
    XMin = YMin = ZMin = 0.0
    XMax = YMax = ZMax = 100.0

    def intersect(self, _other):
        return True


class _Shell:
    """A hollow solid whose box encloses everything: every pair is near."""

    Solids = [object()]
    BoundBox = _Box()

    def __init__(self, distance):
        self.distance = distance
        self.commons = 0

    def isNull(self):
        return False

    def optimalBoundingBox(self, *_args):
        return _Box()

    def distToShape(self, _other):
        return (self.distance,)

    def common(self, _other):
        self.commons += 1
        return SimpleNamespace(Volume=5.0)


def _measure(monkeypatch, shapes):
    monkeypatch.setattr(cadex_assembly_worker, "_component_world_shape", lambda component: shapes[component])
    monkeypatch.setattr(cadex_assembly_worker, "_boundary_distance",
                        lambda first, second: first.distToShape(second)[0])
    return cadex_assembly_worker._measure_clearance({name: name for name in shapes})


def test_a_pair_measured_apart_is_not_intersected(monkeypatch, ledger):
    tub, dome = _Shell(2.4), _Shell(2.4)

    row, = _measure(monkeypatch, {"c_tub": tub, "c_dome": dome})

    assert "error" not in row
    assert row["distance_mm"] == 2.4
    assert row["common_volume_mm3"] == 0.0
    assert tub.commons == dome.commons == 0


def test_a_touching_pair_is_still_intersected(monkeypatch, ledger):
    tub, deck = _Shell(0.0), _Shell(0.0)

    row, = _measure(monkeypatch, {"c_tub": tub, "c_deck": deck})

    assert row["common_volume_mm3"] == 5.0
    assert tub.commons == 1


def test_each_measured_pair_is_a_ledger_stage(monkeypatch, ledger):
    _measure(monkeypatch, {"c_tub": _Shell(2.4), "c_dome": _Shell(2.4)})

    progress = json.loads(ledger.read_text(encoding="utf-8"))
    assert progress["current"]["stage"] == "static fit c_tub / c_dome"


def test_the_ledger_keeps_the_costliest_finished_stages(ledger, monkeypatch):
    clock = iter([0.0, 75.0, 76.0, 128.0] + [128.0 + index for index in range(1, 9)])
    monkeypatch.setattr(cadex_domain_worker.time, "process_time", lambda: next(clock))
    for stage in ["output tub", "output deck", "static fit c_tub / c_visor"] + [f"output leg_{i}" for i in range(9)]:
        cadex_domain_worker.cpu_stage(stage)

    progress = json.loads(ledger.read_text(encoding="utf-8"))
    finished = progress["finished"]
    assert len(finished) == cadex_domain_worker.PROGRESS_KEPT_STAGES
    assert finished[0] == {"stage": "output tub", "cpu_seconds": 75.0}
    assert finished[1] == {"stage": "static fit c_tub / c_visor", "cpu_seconds": 52.0}
    assert progress["current"]["stage"] == "output leg_8"


def test_no_ledger_without_the_environment(tmp_path, monkeypatch):
    monkeypatch.delenv(cadex_domain_worker.PROGRESS_ENV, raising=False)
    cadex_domain_worker.cpu_stage("output tub")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX resource limits")
def test_a_cpu_refusal_names_the_stage_it_died_in(tmp_path) -> None:
    """The ledger is written before the stage runs, so it survives SIGXCPU."""

    burn = (
        "import sys, resource;"
        f"sys.path.insert(0, {str(MODULE_DIR)!r});"
        "from cadex_domain_worker import cpu_stage;"
        "cpu_stage('output tub');"
        "cpu_stage('static fit c_tub / c_dome');"
        "resource.setrlimit(resource.RLIMIT_CPU, (1, resource.getrlimit(resource.RLIMIT_CPU)[1]));"
        "\nwhile True: pass"
    )
    process = run_process(
        [sys.executable, "-c", burn],
        cwd=tmp_path,
        environment={**os.environ, cadex_domain_worker.PROGRESS_ENV: str(tmp_path / "progress.json")},
        cancellation_check=None,
        timeout_seconds=60.0,
        memory_limit_bytes=0,
    )
    assert process["returncode"] == -signal.SIGXCPU

    failure = _resource_signal_failure(
        process, {"tool_name": "write_script", "timeout_seconds": 300.0, "staging": str(tmp_path)}
    )

    assert failure["failure_code"] == "DOMAIN_CPU_LIMIT_EXCEEDED"
    assert "It was in 'static fit c_tub / c_dome'" in failure["error"]
    assert "'static fit A / B' stage is the exact fit check" in failure["error"]
    assert failure["observed"]["cpu_ledger"]["current"]["stage"] == "static fit c_tub / c_dome"
    assert failure["observed"]["returncode"] == -signal.SIGXCPU


def test_a_cpu_refusal_names_the_costliest_stages(tmp_path) -> None:
    (tmp_path / "progress.json").write_text(json.dumps({
        "current": {"stage": "static fit c_tub / c_hip_servo_lr", "started_cpu_seconds": 298.47},
        "finished": [
            {"stage": "output tub", "cpu_seconds": 75.01},
            {"stage": "static fit c_tub / c_visor", "cpu_seconds": 52.85},
            {"stage": "output deck", "cpu_seconds": 0.4},
        ],
    }), encoding="utf-8")

    failure = _resource_signal_failure(
        {"returncode": -signal.SIGXCPU},
        {"tool_name": "write_script", "timeout_seconds": 300.0, "staging": str(tmp_path)},
    )

    assert ("Costliest finished stages, in CPU-seconds: 'output tub' 75.01, "
            "'static fit c_tub / c_visor' 52.85.") in failure["error"]
    assert "output deck" not in failure["error"]


def test_a_refusal_without_a_ledger_is_unchanged(tmp_path) -> None:
    failure = _resource_signal_failure(
        {"returncode": -signal.SIGXCPU},
        {"tool_name": "write_script", "timeout_seconds": 300.0, "staging": str(tmp_path)},
    )
    assert failure["error"].endswith("wall-clock timeout.")
    assert "cpu_ledger" not in failure["observed"]
