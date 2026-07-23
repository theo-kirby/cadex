#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Self-test baseline artifact provenance calculation."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import collect_ui_test_baseline


SCHEMA = "freecad-artifact-provenance-selftest-v1"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str, mtime: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    os.utime(path, (mtime, mtime))


def create_complete_results(results_dir: Path, run_id: str = "selftest-run") -> None:
    for step in collect_ui_test_baseline.REQUIRED_PROVENANCE_STEPS:
        write_text(results_dir / f"{step}.run_id", run_id + "\n", 1000.0)
        for relative in collect_ui_test_baseline.PROVENANCE_ARTIFACTS.get(step, []):
            write_text(results_dir / relative, "{}\n", 1000.0)


def run_summary(results_dir: Path, run_id: str = "selftest-run") -> dict[str, Any]:
    return collect_ui_test_baseline.artifact_provenance_summary(results_dir, run_id)


def clean_case(work_dir: Path) -> dict[str, Any]:
    results_dir = work_dir / "clean"
    create_complete_results(results_dir)
    report = run_summary(results_dir)
    return {
        "ok": report["all_required_steps_match"] is True
        and not report["missing_steps"]
        and not report["stale_steps"]
        and not report["missing_artifact_steps"]
        and not report["modified_after_run_id_steps"],
        "report": {
            key: report[key]
            for key in [
                "required_step_count",
                "missing_steps",
                "stale_steps",
                "missing_artifact_steps",
                "modified_after_run_id_steps",
                "all_required_steps_match",
            ]
        },
    }


def missing_run_marker_case(work_dir: Path) -> dict[str, Any]:
    results_dir = work_dir / "missing-run-marker"
    create_complete_results(results_dir)
    (results_dir / "ctest.run_id").unlink()
    report = run_summary(results_dir)
    return {
        "ok": report["all_required_steps_match"] is False
        and "ctest" in report["missing_steps"]
        and report["steps"]["ctest"]["present"] is False,
        "missing_steps": report["missing_steps"],
        "ctest": report["steps"]["ctest"],
    }


def stale_run_marker_case(work_dir: Path) -> dict[str, Any]:
    results_dir = work_dir / "stale-run-marker"
    create_complete_results(results_dir)
    write_text(results_dir / "ctest.run_id", "older-run\n", 1000.0)
    report = run_summary(results_dir)
    return {
        "ok": report["all_required_steps_match"] is False
        and "ctest" in report["stale_steps"]
        and report["steps"]["ctest"]["matches_current_run"] is False,
        "stale_steps": report["stale_steps"],
        "ctest": report["steps"]["ctest"],
    }


def missing_artifact_case(work_dir: Path) -> dict[str, Any]:
    results_dir = work_dir / "missing-artifact"
    create_complete_results(results_dir)
    (results_dir / "ctest.log").unlink()
    report = run_summary(results_dir)
    return {
        "ok": report["all_required_steps_match"] is False
        and "ctest" in report["missing_artifact_steps"]
        and report["steps"]["ctest"]["artifacts_present"] is False,
        "missing_artifact_steps": report["missing_artifact_steps"],
        "ctest": report["steps"]["ctest"],
    }


def directory_run_marker_case(work_dir: Path) -> dict[str, Any]:
    results_dir = work_dir / "directory-run-marker"
    create_complete_results(results_dir)
    (results_dir / "ctest.run_id").unlink()
    (results_dir / "ctest.run_id").mkdir()
    report = run_summary(results_dir)
    return {
        "ok": report["all_required_steps_match"] is False
        and "ctest" in report["missing_steps"]
        and report["steps"]["ctest"]["present"] is False,
        "missing_steps": report["missing_steps"],
        "ctest": report["steps"]["ctest"],
    }


def directory_artifact_case(work_dir: Path) -> dict[str, Any]:
    results_dir = work_dir / "directory-artifact"
    create_complete_results(results_dir)
    (results_dir / "ctest.log").unlink()
    (results_dir / "ctest.log").mkdir()
    report = run_summary(results_dir)
    ctest_artifacts = report["steps"]["ctest"]["artifacts"]
    return {
        "ok": report["all_required_steps_match"] is False
        and "ctest" in report["missing_artifact_steps"]
        and report["steps"]["ctest"]["artifacts_present"] is False
        and ctest_artifacts
        and ctest_artifacts[0]["is_file"] is False,
        "missing_artifact_steps": report["missing_artifact_steps"],
        "ctest": report["steps"]["ctest"],
    }


def modified_after_run_marker_case(work_dir: Path) -> dict[str, Any]:
    results_dir = work_dir / "modified-after-run-marker"
    create_complete_results(results_dir)
    write_text(results_dir / "ctest.log", "{}\n", 1002.5)
    report = run_summary(results_dir)
    return {
        "ok": report["all_required_steps_match"] is False
        and "ctest" in report["modified_after_run_id_steps"]
        and report["steps"]["ctest"]["modified_after_run_id"] is True,
        "modified_after_run_id_steps": report["modified_after_run_id_steps"],
        "ctest": report["steps"]["ctest"],
    }


def empty_current_run_id_case(work_dir: Path) -> dict[str, Any]:
    results_dir = work_dir / "empty-current-run-id"
    create_complete_results(results_dir)
    report = run_summary(results_dir, run_id="")
    return {
        "ok": report["all_required_steps_match"] is False
        and report["stale_steps"] == collect_ui_test_baseline.REQUIRED_PROVENANCE_STEPS,
        "stale_step_count": len(report["stale_steps"]),
        "required_step_count": report["required_step_count"],
        "all_required_steps_match": report["all_required_steps_match"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/freecad-test-results/artifact-provenance-selftest.json"),
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="freecad-artifact-provenance-selftest-") as temp:
        work_dir = Path(temp)
        scenarios = {
            "clean_provenance_passes": clean_case(work_dir),
            "missing_run_marker_fails": missing_run_marker_case(work_dir),
            "stale_run_marker_fails": stale_run_marker_case(work_dir),
            "missing_required_artifact_fails": missing_artifact_case(work_dir),
            "directory_run_marker_fails": directory_run_marker_case(work_dir),
            "directory_required_artifact_fails": directory_artifact_case(work_dir),
            "modified_after_run_marker_fails": modified_after_run_marker_case(work_dir),
            "empty_current_run_id_fails": empty_current_run_id_case(work_dir),
        }

    failed = [name for name, result in scenarios.items() if not result["ok"]]
    report = {
        "schema": SCHEMA,
        "result": "ok" if not failed else "failed",
        "scenario_count": len(scenarios),
        "scenario_names": sorted(scenarios),
        "failed_scenarios": failed,
        "scenarios": scenarios,
    }
    write_json(args.output, report)
    return 0 if report["result"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
