#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Self-test manual smoke artifact validation behavior."""

from __future__ import annotations

import argparse
import copy
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import manual_smoke


SCHEMA = "freecad-ui-style-manual-smoke-selftest-v1"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def valid_artifact(expected_build: dict[str, str], expected_run: dict[str, str], evidence_dir: Path) -> dict[str, Any]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    artifact = manual_smoke.template()
    artifact["created_utc"] = (now - timedelta(minutes=10)).isoformat()
    artifact["completed_utc"] = now.isoformat()
    artifact["tester"] = "manual smoke validator self-test"
    artifact["build"] = dict(expected_build)
    artifact["baseline_run"] = dict(expected_run)
    artifact["environment"] = {
        "display": "xvfb",
        "theme": "default",
        "dpi_scale": "1.0",
        "font_size": "default",
    }
    for name, item in artifact["checks"].items():
        evidence_path = evidence_dir / f"{name}.txt"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(f"Manual smoke self-test evidence for {name}\n", encoding="utf-8")
        item["status"] = "pass"
        item["notes"] = f"Synthetic pass for {name}"
        item["evidence"] = [str(evidence_path)]
    return artifact


def run_case(
    name: str,
    artifact: dict[str, Any],
    expected_build: dict[str, str],
    expected_run: dict[str, str],
    expected_ok: bool,
    expected_error: str | None = None,
) -> dict[str, Any]:
    ok, errors = manual_smoke.validate(
        artifact,
        expected_build=expected_build,
        expected_run=expected_run,
    )
    matched_error = expected_error is None or any(expected_error in error for error in errors)
    return {
        "ok": ok == expected_ok and matched_error,
        "expected_ok": expected_ok,
        "actual_ok": ok,
        "expected_error": expected_error,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=Path("/tmp/freecad-test-results/baseline-summary.json"))
    parser.add_argument("--output", type=Path, default=Path("/tmp/freecad-test-results/manual-smoke-selftest.json"))
    args = parser.parse_args()

    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    expected_build = manual_smoke.expected_build_from_summary(summary)
    expected_run = manual_smoke.expected_run_from_summary(summary)
    evidence_dir = args.output.with_suffix("").with_name(args.output.stem + "-evidence")
    base = valid_artifact(expected_build, expected_run, evidence_dir)

    stale_build = copy.deepcopy(base)
    stale_build["build"]["git_revision"] = "not-the-current-build"

    stale_run = copy.deepcopy(base)
    stale_run["baseline_run"]["run_id"] = "not-the-current-run"

    missing_run = copy.deepcopy(base)
    missing_run.pop("baseline_run", None)

    future_completion = copy.deepcopy(base)
    future_completion["completed_utc"] = (
        datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=1)
    ).isoformat()

    missing_evidence = copy.deepcopy(base)
    first_check = next(iter(missing_evidence["checks"].values()))
    first_check["evidence"] = []

    blocked_status = copy.deepcopy(base)
    first_check = next(iter(blocked_status["checks"].values()))
    first_check["status"] = "blocked"

    fail_status = copy.deepcopy(base)
    first_check = next(iter(fail_status["checks"].values()))
    first_check["status"] = "fail"

    missing_required_check = copy.deepcopy(base)
    missing_required_check["checks"].pop("open_sample_files", None)

    wrong_description = copy.deepcopy(base)
    first_check = next(iter(wrong_description["checks"].values()))
    first_check["description"] = "This description no longer proves the required manual workflow."

    placeholder_evidence = copy.deepcopy(base)
    first_check = next(iter(placeholder_evidence["checks"].values()))
    first_check["evidence"] = ["synthetic://placeholder"]

    missing_path_evidence = copy.deepcopy(base)
    first_check = next(iter(missing_path_evidence["checks"].values()))
    first_check["evidence"] = [str(evidence_dir / "missing-evidence-file.txt")]

    unsupported_uri_evidence = copy.deepcopy(base)
    first_check = next(iter(unsupported_uri_evidence["checks"].values()))
    first_check["evidence"] = ["manual-smoke-selftest://open_sample_files"]

    placeholder_notes = copy.deepcopy(base)
    first_check = next(iter(placeholder_notes["checks"].values()))
    first_check["notes"] = "TODO"

    stale_evidence_hint = copy.deepcopy(base)
    first_check = next(iter(stale_evidence_hint["checks"].values()))
    first_check["evidence_hint"] = "anything goes"

    stale_file_evidence = copy.deepcopy(base)
    first_check = next(iter(stale_file_evidence["checks"].values()))
    stale_path = evidence_dir / "stale-file-evidence.txt"
    stale_path.write_text("Stale manual smoke evidence from an older run.\n", encoding="utf-8")
    stale_mtime = (datetime.fromisoformat(stale_file_evidence["created_utc"]) - timedelta(minutes=1)).timestamp()
    os.utime(stale_path, (stale_mtime, stale_mtime))
    first_check["evidence"] = [str(stale_path)]

    too_new_file_evidence = copy.deepcopy(base)
    first_check = next(iter(too_new_file_evidence["checks"].values()))
    too_new_path = evidence_dir / "too-new-file-evidence.txt"
    too_new_path.write_text("Manual smoke evidence written after completion.\n", encoding="utf-8")
    too_new_mtime = (
        datetime.fromisoformat(too_new_file_evidence["completed_utc"]) + timedelta(minutes=2)
    ).timestamp()
    os.utime(too_new_path, (too_new_mtime, too_new_mtime))
    first_check["evidence"] = [str(too_new_path)]

    extra_check = copy.deepcopy(base)
    extra_check["checks"]["unrecognized_manual_step"] = {
        "description": "This should not be accepted.",
        "status": "pass",
        "notes": "Extra check should fail.",
        "evidence": ["manual-smoke-selftest://extra"],
    }

    scenarios = {
        "valid_current_build_passes": run_case(
            "valid_current_build_passes",
            base,
            expected_build,
            expected_run,
            True,
        ),
        "stale_build_fails": run_case(
            "stale_build_fails",
            stale_build,
            expected_build,
            expected_run,
            False,
            "build.git_revision must match current baseline",
        ),
        "stale_run_fails": run_case(
            "stale_run_fails",
            stale_run,
            expected_build,
            expected_run,
            False,
            "baseline_run.run_id must match current baseline",
        ),
        "missing_run_fails": run_case(
            "missing_run_fails",
            missing_run,
            expected_build,
            expected_run,
            False,
            "baseline_run object is required",
        ),
        "future_completion_fails": run_case(
            "future_completion_fails",
            future_completion,
            expected_build,
            expected_run,
            False,
            "completed_utc must not be in the future",
        ),
        "missing_evidence_fails": run_case(
            "missing_evidence_fails",
            missing_evidence,
            expected_build,
            expected_run,
            False,
            "evidence must contain at least one entry",
        ),
        "blocked_status_fails": run_case(
            "blocked_status_fails",
            blocked_status,
            expected_build,
            expected_run,
            False,
            "status is blocked, expected pass",
        ),
        "fail_status_fails": run_case(
            "fail_status_fails",
            fail_status,
            expected_build,
            expected_run,
            False,
            "status is fail, expected pass",
        ),
        "missing_required_check_fails": run_case(
            "missing_required_check_fails",
            missing_required_check,
            expected_build,
            expected_run,
            False,
            "checks.open_sample_files is required",
        ),
        "wrong_description_fails": run_case(
            "wrong_description_fails",
            wrong_description,
            expected_build,
            expected_run,
            False,
            "description must match required smoke description",
        ),
        "placeholder_evidence_fails": run_case(
            "placeholder_evidence_fails",
            placeholder_evidence,
            expected_build,
            expected_run,
            False,
            "evidence contains placeholder entry",
        ),
        "missing_path_evidence_fails": run_case(
            "missing_path_evidence_fails",
            missing_path_evidence,
            expected_build,
            expected_run,
            False,
            "path evidence does not exist",
        ),
        "unsupported_uri_evidence_fails": run_case(
            "unsupported_uri_evidence_fails",
            unsupported_uri_evidence,
            expected_build,
            expected_run,
            False,
            "unsupported evidence URI scheme",
        ),
        "placeholder_notes_fails": run_case(
            "placeholder_notes_fails",
            placeholder_notes,
            expected_build,
            expected_run,
            False,
            "notes must not be placeholder text",
        ),
        "stale_evidence_hint_fails": run_case(
            "stale_evidence_hint_fails",
            stale_evidence_hint,
            expected_build,
            expected_run,
            False,
            "evidence_hint must describe auditable evidence requirements",
        ),
        "stale_file_evidence_fails": run_case(
            "stale_file_evidence_fails",
            stale_file_evidence,
            expected_build,
            expected_run,
            False,
            "file evidence is older than created_utc",
        ),
        "too_new_file_evidence_fails": run_case(
            "too_new_file_evidence_fails",
            too_new_file_evidence,
            expected_build,
            expected_run,
            False,
            "file evidence is newer than completed_utc",
        ),
        "extra_check_fails": run_case(
            "extra_check_fails",
            extra_check,
            expected_build,
            expected_run,
            False,
            "checks contains unrecognized entries",
        ),
    }
    failed = [name for name, scenario in scenarios.items() if not scenario["ok"]]
    report = {
        "schema": SCHEMA,
        "result": "ok" if not failed else "failed",
        "scenario_count": len(scenarios),
        "scenario_names": sorted(scenarios),
        "failed_scenarios": failed,
        "expected_build": expected_build,
        "expected_run": expected_run,
        "scenarios": scenarios,
    }
    write_json(args.output, report)
    return 0 if report["result"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
