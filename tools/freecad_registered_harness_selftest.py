#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Self-test registered FreeCAD split harness result classification."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import freecad_registered_test_harness as harness


SCHEMA = "freecad-registered-harness-selftest-v1"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def classify(work_dir: Path, name: str, returncode: int, output: str) -> dict[str, Any]:
    log_path = work_dir / f"{name}.log"
    log_path.write_text(output, encoding="utf-8")
    return harness.classify_suite(
        name,
        ["FreeCAD", "-t", name],
        returncode,
        output,
        0.1,
        log_path,
    )


def run_case(
    work_dir: Path,
    name: str,
    returncode: int,
    output: str,
    expected_result: str,
    expected_flags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = classify(work_dir, name, returncode, output)
    expected_flags = expected_flags or {}
    ok = result.get("result") == expected_result
    for key, expected in expected_flags.items():
        ok = ok and result.get(key) == expected
    return {
        "ok": ok,
        "expected_result": expected_result,
        "actual_result": result.get("result"),
        "expected_flags": expected_flags,
        "actual": {
            "returncode": result.get("returncode"),
            "traceback_count": result.get("traceback_count"),
            "quantity_slot_type_errors": result.get("quantity_slot_type_errors"),
            "deleted_object_reference_errors": result.get("deleted_object_reference_errors"),
            "segmentation_fault": result.get("segmentation_fault"),
            "timeout": result.get("timeout"),
            "ran_tests": result.get("ran_tests"),
        },
    }


def reset_output_dir_case(work_dir: Path) -> dict[str, Any]:
    output_dir = work_dir / "registered-output"
    stale_file = output_dir / "stale.log"
    stale_nested = output_dir / "nested" / "old.json"
    stale_nested.parent.mkdir(parents=True)
    stale_file.write_text("old", encoding="utf-8")
    stale_nested.write_text("old", encoding="utf-8")

    harness.reset_output_dir(output_dir)
    remaining = sorted(str(path.relative_to(output_dir)) for path in output_dir.rglob("*"))
    return {
        "ok": output_dir.exists() and remaining == [],
        "remaining": remaining,
    }


def process_group_timeout_case(work_dir: Path) -> dict[str, Any]:
    child_pid_path = work_dir / "child.pid"
    sleeper = work_dir / "sleep_tree.py"
    sleeper.write_text(
        "\n".join(
            [
                "import pathlib, subprocess, sys, time",
                f"pid_path = pathlib.Path({str(child_pid_path)!r})",
                "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])",
                "pid_path.write_text(str(child.pid), encoding='utf-8')",
                "try:",
                "    time.sleep(30)",
                "finally:",
                "    child.terminate()",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    returncode, output, duration = harness.run_command([sys.executable, str(sleeper)], timeout=1)
    child_pid = int(child_pid_path.read_text(encoding="utf-8"))
    child_alive = True
    for _ in range(20):
        try:
            os.kill(child_pid, 0)
        except ProcessLookupError:
            child_alive = False
            break
        time.sleep(0.1)
    if child_alive:
        try:
            os.kill(child_pid, signal.SIGKILL)
        except ProcessLookupError:
            child_alive = False
    return {
        "ok": returncode == 124 and not child_alive and "TIMEOUT after 1s" in output,
        "returncode": returncode,
        "duration_seconds": round(duration, 3),
        "child_pid": child_pid,
        "child_alive_after_timeout": child_alive,
        "output_excerpt": output[-200:],
    }


def suite_preflight_case(discovered: list[str], selected: list[str], expected_errors: list[str]) -> dict[str, Any]:
    result = harness.suite_preflight(discovered, selected)
    actual_errors = result.get("errors", [])
    return {
        "ok": actual_errors == expected_errors,
        "expected_errors": expected_errors,
        "actual_errors": actual_errors,
        "preflight": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/freecad-test-results/freecad-registered-harness-selftest.json"))
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="freecad-registered-harness-selftest-") as temp:
        work_dir = Path(temp)
        cases = {
            "ok_summary_classifies_ok": run_case(
                work_dir,
                "OkSuite",
                0,
                "\nRan 1 test in 0.001s\n\nOK\n",
                "ok",
                {"ran_tests": 1},
            ),
            "failed_summary_classifies_failed": run_case(
                work_dir,
                "FailedSuite",
                0,
                "\nRan 1 test in 0.001s\n\nFAILED (failures=1)\n",
                "failed",
            ),
            "traceback_classifies_traceback": run_case(
                work_dir,
                "TracebackSuite",
                0,
                "Traceback (most recent call last):\n  synthetic traceback\nSyntheticError\n",
                "traceback",
                {"traceback_count": 1},
            ),
            "quantity_error_classifies_process_error": run_case(
                work_dir,
                "QuantitySuite",
                0,
                'TypeError: Cannot call meta function "slot(Base::Quantity)"\n\nOK\n',
                "ok_with_process_errors",
                {"quantity_slot_type_errors": 1},
            ),
            "deleted_object_reference_classifies_process_error": run_case(
                work_dir,
                "DeletedObjectSuite",
                0,
                "ReferenceError: Cannot access attribute 'ShowSunPosition' of deleted object\n\nOK\n",
                "ok_with_process_errors",
                {"deleted_object_reference_errors": 1},
            ),
            "nonzero_exit_classifies_process_failed": run_case(
                work_dir,
                "ProcessFailedSuite",
                2,
                "\nRan 1 test in 0.001s\n\nOK\n",
                "process_failed",
            ),
            "segv_output_classifies_crash": run_case(
                work_dir,
                "CrashSuite",
                1,
                "Program received signal SIGSEGV, Segmentation fault.\n",
                "crash",
                {"segmentation_fault": True},
            ),
            "timeout_classifies_timeout": run_case(
                work_dir,
                "TimeoutSuite",
                124,
                "TIMEOUT after 180s\n",
                "timeout",
                {"timeout": True},
            ),
            "unrecognized_zero_exit_classifies_unknown": run_case(
                work_dir,
                "UnknownSuite",
                0,
                "suite produced no unittest summary\n",
                "unknown",
            ),
            "reset_output_dir_removes_stale_artifacts": reset_output_dir_case(work_dir),
            "timeout_kills_process_group_children": process_group_timeout_case(work_dir),
            "preflight_allows_unique_suites": suite_preflight_case(
                ["App", "Gui", "Part"],
                ["App", "Gui"],
                [],
            ),
            "preflight_rejects_duplicate_discovered_suites": suite_preflight_case(
                ["App", "Gui", "Gui"],
                ["App"],
                ["duplicate_discovered_suites", "discovered_log_slug_collisions"],
            ),
            "preflight_rejects_duplicate_selected_suites": suite_preflight_case(
                ["App", "Gui"],
                ["Gui", "Gui"],
                ["duplicate_selected_suites", "selected_log_slug_collisions"],
            ),
            "preflight_rejects_log_slug_collisions": suite_preflight_case(
                ["A/B", "A:B"],
                ["A/B", "A:B"],
                ["discovered_log_slug_collisions", "selected_log_slug_collisions"],
            ),
            "preflight_rejects_empty_log_slug": suite_preflight_case(
                ["!!!"],
                ["!!!"],
                ["discovered_log_slug_collisions", "selected_log_slug_collisions"],
            ),
        }

    failed = [name for name, result in cases.items() if not result["ok"]]
    report = {
        "schema": SCHEMA,
        "result": "ok" if not failed else "failed",
        "scenario_count": len(cases),
        "failed_scenarios": failed,
        "scenarios": cases,
    }
    write_json(args.output, report)
    return 0 if report["result"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
