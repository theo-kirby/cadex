#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Evaluate final UI/style baseline runner step statuses."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SCHEMA = "freecad-ui-style-run-status-v1"

DEFAULT_RUNNER = Path(__file__).resolve().with_name("run_ui_test_baseline.sh")
CONDITIONALLY_APPROVED_STEPS = {
    "ctest-not-run-approve",
    "gui-visual-approve",
    "gui-visual-fixtures-approve",
    "gui-visual-matrix-approve",
    "gui-visual-dialogs-approve",
    "gui-visual-tasks-approve",
}


def parse_runner_steps(runner: Path) -> list[str]:
    text = runner.read_text(encoding="utf-8")
    steps = re.findall(r"^\s*run_step\s+([A-Za-z0-9_.-]+)\b", text, flags=re.MULTILINE)
    deduped = []
    seen = set()
    for step in steps:
        if step in seen:
            continue
        seen.add(step)
        deduped.append(step)
    return deduped


def duplicate_runner_steps(runner: Path) -> list[str]:
    text = runner.read_text(encoding="utf-8")
    steps = re.findall(r"^\s*run_step\s+([A-Za-z0-9_.-]+)\b", text, flags=re.MULTILINE)
    seen = set()
    duplicates = []
    for step in steps:
        if step in seen and step not in duplicates:
            duplicates.append(step)
        seen.add(step)
    return duplicates


def read_current_run_id(results_dir: Path) -> str | None:
    path = results_dir / "run.id"
    if not path.exists():
        return None
    value = path.read_text(encoding="utf-8", errors="replace").strip()
    return value or None


def read_status(results_dir: Path, step: str, current_run_id: str | None) -> dict[str, Any]:
    path = results_dir / f"{step}.status"
    command_path = results_dir / f"{step}.command"
    run_id_path = results_dir / f"{step}.run_id"
    command_present = command_path.exists()
    step_run_id = (
        run_id_path.read_text(encoding="utf-8", errors="replace").strip()
        if run_id_path.exists()
        else None
    )
    if not path.exists():
        return {
            "step": step,
            "status": "missing",
            "ok": False,
            "path": str(path),
            "command_path": str(command_path),
            "command_present": command_present,
            "run_id_path": str(run_id_path),
            "run_id": step_run_id,
            "expected_run_id": current_run_id,
            "failure_reasons": ["missing_status"],
        }
    raw = path.read_text(encoding="utf-8", errors="replace").strip()
    failure_reasons = []
    if raw != "0":
        failure_reasons.append("nonzero_status")
    if current_run_id is None:
        failure_reasons.append("missing_current_run_id")
    if step_run_id is None:
        failure_reasons.append("missing_step_run_id")
    elif current_run_id is not None and step_run_id != current_run_id:
        failure_reasons.append("stale_step_run_id")
    if not command_present:
        failure_reasons.append("missing_command")
    return {
        "step": step,
        "status": raw,
        "ok": not failure_reasons,
        "path": str(path),
        "command_path": str(command_path),
        "command_present": command_present,
        "run_id_path": str(run_id_path),
        "run_id": step_run_id,
        "expected_run_id": current_run_id,
        "failure_reasons": failure_reasons,
    }


def step_required(step: str, results_dir: Path) -> bool:
    if step not in CONDITIONALLY_APPROVED_STEPS:
        return True
    return (results_dir / f"{step}.status").exists()


def build_report(
    results_dir: Path,
    required_steps: list[str] | None = None,
    runner: Path | None = DEFAULT_RUNNER,
) -> dict[str, Any]:
    discovered_steps = required_steps or parse_runner_steps(runner or DEFAULT_RUNNER)
    duplicate_steps = [] if required_steps is not None else duplicate_runner_steps(runner or DEFAULT_RUNNER)
    steps = [step for step in discovered_steps if step_required(step, results_dir)]
    current_run_id = read_current_run_id(results_dir)
    statuses = [read_status(results_dir, step, current_run_id) for step in steps]
    failures = [
        {
            "step": item["step"],
            "status": item["status"],
            "path": item["path"],
            "command_path": item["command_path"],
            "run_id_path": item["run_id_path"],
            "run_id": item["run_id"],
            "expected_run_id": item["expected_run_id"],
            "failure_reasons": item.get("failure_reasons", []),
        }
        for item in statuses
        if not item["ok"]
    ]
    failures.extend(
        {
            "step": step,
            "status": "duplicate_runner_step",
            "path": str(runner) if runner else None,
            "command_path": None,
            "run_id_path": None,
            "run_id": current_run_id,
            "expected_run_id": current_run_id,
            "failure_reasons": ["duplicate_runner_step"],
        }
        for step in duplicate_steps
    )
    return {
        "schema": SCHEMA,
        "result": "ok" if not failures else "failed",
        "ready_for_sweeping_style_change": not failures,
        "runner": str(runner) if runner else None,
        "run_id": current_run_id,
        "discovered_step_count": len(discovered_steps),
        "duplicate_runner_steps": duplicate_steps,
        "required_steps": steps,
        "failure_count": len(failures),
        "failures": failures,
        "statuses": statuses,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=Path("/tmp/freecad-test-results"))
    parser.add_argument("--runner", type=Path, default=DEFAULT_RUNNER)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = build_report(args.results_dir, runner=args.runner)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if report["result"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
