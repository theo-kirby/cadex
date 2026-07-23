#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Self-test registered issue classification validation behavior."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

import validate_registered_issue_classifications as validator


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def base_summary(work_dir: Path) -> dict[str, Any]:
    log = work_dir / "BadSuite.log"
    log.write_text("Traceback (most recent call last):\nRequired evidence text\nTODO\n", encoding="utf-8")
    silent_log = work_dir / "SilentOkSuite.log"
    silent_log.write_text(
        "OK label with hidden traceback\nSilent traceback evidence\n",
        encoding="utf-8",
    )
    return {
        "results": [
            {
                "suite": "GoodSuite",
                "result": "ok",
                "log": str(work_dir / "GoodSuite.log"),
            },
            {
                "suite": "BadSuite",
                "result": "traceback",
                "log": str(log),
                "deleted_object_reference_errors": 0,
                "quantity_slot_type_errors": 0,
                "ran_tests": 1,
                "returncode": 0,
                "segmentation_fault": False,
                "timeout": False,
                "traceback_count": 1,
            },
            {
                "suite": "SilentOkSuite",
                "result": "ok",
                "log": str(silent_log),
                "deleted_object_reference_errors": 0,
                "quantity_slot_type_errors": 0,
                "ran_tests": 1,
                "returncode": 0,
                "segmentation_fault": False,
                "timeout": False,
                "traceback_count": 1,
            },
        ]
    }


def valid_classification() -> dict[str, Any]:
    return {
        "schema": validator.SCHEMA,
        "issues": [
            {
                "suite": "BadSuite",
                "expected_result": "traceback",
                "reason": "Synthetic traceback issue for validator self-test.",
                "required_evidence": ["Required evidence text"],
                "expected_counts": {
                    "deleted_object_reference_errors": 0,
                    "quantity_slot_type_errors": 0,
                    "returncode": 0,
                    "segmentation_fault": False,
                    "timeout": False,
                    "traceback_count": 1,
                },
                "hard_blocker": True,
            },
            {
                "suite": "SilentOkSuite",
                "expected_result": "ok",
                "reason": "Synthetic ok-labeled suite still carries traceback evidence and must be explicit.",
                "required_evidence": ["Silent traceback evidence"],
                "expected_counts": {
                    "deleted_object_reference_errors": 0,
                    "quantity_slot_type_errors": 0,
                    "returncode": 0,
                    "segmentation_fault": False,
                    "timeout": False,
                    "traceback_count": 1,
                },
                "hard_blocker": True,
            }
        ],
    }


def range_classification() -> dict[str, Any]:
    classification = valid_classification()
    counts = classification["issues"][0]["expected_counts"]
    counts.pop("traceback_count")
    classification["issues"][0]["expected_count_ranges"] = {
        "traceback_count": {"min": 1, "max": 3}
    }
    return classification


def run_case(name: str, summary: dict[str, Any], classifications: dict[str, Any], expected_result: str, expected_error_kind: str | None) -> dict[str, Any]:
    report = validator.validate(summary, classifications)
    error_kinds = sorted({error.get("kind") for error in report.get("errors", []) if error.get("kind")})
    ok = report.get("result") == expected_result
    if expected_error_kind is not None:
        ok = ok and expected_error_kind in error_kinds
    matched_evidence = []
    if report.get("classified_issues"):
        matched_evidence = report["classified_issues"][0].get("matched_required_evidence", [])
    if expected_result == "ok":
        matched_needles = {
            evidence.get("needle")
            for issue in report.get("classified_issues", [])
            for evidence in issue.get("matched_required_evidence", [])
        }
        ok = ok and {
            "Required evidence text",
            "Silent traceback evidence",
        }.issubset(matched_needles)
    return {
        "ok": ok,
        "expected_result": expected_result,
        "expected_error_kind": expected_error_kind,
        "actual_result": report.get("result"),
        "error_kinds": error_kinds,
        "matched_required_evidence": matched_evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/freecad-test-results/registered-classification-selftest.json"))
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="registered-classification-selftest-") as temp:
        work_dir = Path(temp)
        summary = base_summary(work_dir)

        cases: dict[str, tuple[dict[str, Any], str, str | None]] = {}
        cases["valid_classification_passes"] = (valid_classification(), "ok", None)
        cases["count_range_classification_passes"] = (range_classification(), "ok", None)

        unclassified = valid_classification()
        unclassified["issues"] = []
        cases["unclassified_issue_fails"] = (unclassified, "failed", "unclassified_issue")

        silent_unclassified = valid_classification()
        silent_unclassified["issues"] = [
            item for item in silent_unclassified["issues"] if item["suite"] != "SilentOkSuite"
        ]
        cases["ok_result_with_traceback_requires_classification"] = (
            silent_unclassified,
            "failed",
            "unclassified_issue",
        )

        stale = valid_classification()
        stale["issues"] = [*stale["issues"], {**stale["issues"][0], "suite": "GoneSuite"}]
        cases["stale_classification_fails"] = (stale, "failed", "stale_classification")

        mismatch = valid_classification()
        mismatch["issues"][0]["expected_result"] = "process_failed"
        cases["result_mismatch_fails"] = (mismatch, "failed", "result_mismatch")

        missing_evidence = valid_classification()
        missing_evidence["issues"][0]["required_evidence"] = ["Needle not in log"]
        cases["missing_evidence_fails"] = (missing_evidence, "failed", "missing_evidence")

        duplicate = valid_classification()
        duplicate["issues"] = [*duplicate["issues"], dict(duplicate["issues"][0])]
        cases["duplicate_classification_fails"] = (duplicate, "failed", "duplicate_classification")

        missing_reason = valid_classification()
        missing_reason["issues"][0]["reason"] = ""
        cases["missing_reason_fails"] = (missing_reason, "failed", "missing_reason")

        placeholder_reason = valid_classification()
        placeholder_reason["issues"][0]["reason"] = "TODO"
        cases["placeholder_reason_fails"] = (placeholder_reason, "failed", "placeholder_reason")

        missing_evidence_list = valid_classification()
        missing_evidence_list["issues"][0].pop("required_evidence")
        cases["missing_required_evidence_list_fails"] = (
            missing_evidence_list,
            "failed",
            "missing_required_evidence_list",
        )

        missing_expected_counts = valid_classification()
        missing_expected_counts["issues"][0].pop("expected_counts")
        cases["missing_expected_counts_fails"] = (
            missing_expected_counts,
            "failed",
            "missing_expected_counts",
        )

        changed_expected_count = valid_classification()
        changed_expected_count["issues"][0]["expected_counts"]["traceback_count"] = 2
        cases["expected_count_mismatch_fails"] = (
            changed_expected_count,
            "failed",
            "expected_count_mismatch",
        )

        changed_expected_count_range = range_classification()
        changed_expected_count_range["issues"][0]["expected_count_ranges"]["traceback_count"] = {
            "min": 2,
            "max": 4,
        }
        cases["expected_count_range_mismatch_fails"] = (
            changed_expected_count_range,
            "failed",
            "expected_count_range_mismatch",
        )

        unknown_expected_count = valid_classification()
        unknown_expected_count["issues"][0]["expected_counts"]["surprise_count"] = 1
        cases["unknown_expected_count_field_fails"] = (
            unknown_expected_count,
            "failed",
            "unknown_expected_count_field",
        )

        unknown_expected_count_range = range_classification()
        unknown_expected_count_range["issues"][0]["expected_count_ranges"]["surprise_count"] = {
            "min": 1,
            "max": 2,
        }
        cases["unknown_expected_count_range_field_fails"] = (
            unknown_expected_count_range,
            "failed",
            "unknown_expected_count_range_field",
        )

        invalid_expected_count_range = range_classification()
        invalid_expected_count_range["issues"][0]["expected_count_ranges"]["traceback_count"] = {
            "min": 3,
            "max": 1,
        }
        cases["invalid_expected_count_range_fails"] = (
            invalid_expected_count_range,
            "failed",
            "invalid_expected_count_range",
        )

        blank_required_evidence = valid_classification()
        blank_required_evidence["issues"][0]["required_evidence"] = [""]
        cases["blank_required_evidence_fails"] = (
            blank_required_evidence,
            "failed",
            "blank_required_evidence",
        )

        placeholder_required_evidence = valid_classification()
        placeholder_required_evidence["issues"][0]["required_evidence"] = ["TODO"]
        cases["placeholder_required_evidence_fails"] = (
            placeholder_required_evidence,
            "failed",
            "placeholder_required_evidence",
        )

        nonblocking_hard_failure = valid_classification()
        nonblocking_hard_failure["issues"][0]["hard_blocker"] = False
        cases["nonblocking_hard_failure_fails"] = (
            nonblocking_hard_failure,
            "failed",
            "nonblocking_hard_failure",
        )

        results = {
            name: run_case(name, summary, classification, expected_result, expected_error_kind)
            for name, (classification, expected_result, expected_error_kind) in cases.items()
        }

    failed = [name for name, result in results.items() if not result["ok"]]
    report = {
        "schema": "freecad-registered-classification-selftest-v1",
        "result": "ok" if not failed else "failed",
        "scenario_count": len(results),
        "scenario_names": sorted(results),
        "failed_scenarios": failed,
        "scenarios": results,
    }
    write_json(args.output, report)
    return 0 if report["result"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
