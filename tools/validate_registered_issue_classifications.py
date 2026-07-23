#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Validate registered-test issue classifications against split artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCHEMA = "freecad-registered-issue-classifications-v1"
HARD_BLOCKING_RESULTS = {
    "crash",
    "ok_with_process_errors",
    "process_failed",
    "timeout",
    "traceback",
}
PLACEHOLDER_TEXT = {"todo", "tbd", "n/a", "none", "placeholder"}
EXPECTED_COUNT_FIELDS = {
    "deleted_object_reference_errors",
    "quantity_slot_type_errors",
    "ran_tests",
    "returncode",
    "segmentation_fault",
    "timeout",
    "traceback_count",
}


def safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def has_hard_process_signal(result: dict[str, Any]) -> bool:
    return (
        bool(result.get("segmentation_fault"))
        or bool(result.get("timeout"))
        or safe_int(result.get("returncode")) != 0
        or safe_int(result.get("traceback_count")) > 0
        or safe_int(result.get("deleted_object_reference_errors")) > 0
        or safe_int(result.get("quantity_slot_type_errors")) > 0
    )


def validate_count_range(
    suite: str,
    field: str,
    spec: Any,
    actual_value: Any,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    if field not in EXPECTED_COUNT_FIELDS:
        errors.append({"kind": "unknown_expected_count_range_field", "suite": suite, "field": field})
        return {}
    if not isinstance(spec, dict):
        errors.append({"kind": "invalid_expected_count_range", "suite": suite, "field": field})
        return {}

    allowed_keys = {"min", "max"}
    unknown_keys = sorted(set(spec) - allowed_keys)
    if unknown_keys:
        errors.append(
            {
                "kind": "invalid_expected_count_range",
                "suite": suite,
                "field": field,
                "unknown_keys": unknown_keys,
            }
        )
    if "min" not in spec and "max" not in spec:
        errors.append({"kind": "invalid_expected_count_range", "suite": suite, "field": field})
        return {}

    lower = spec.get("min")
    upper = spec.get("max")
    if lower is not None and not isinstance(lower, (int, float)):
        errors.append({"kind": "invalid_expected_count_range", "suite": suite, "field": field, "bound": "min"})
    if upper is not None and not isinstance(upper, (int, float)):
        errors.append({"kind": "invalid_expected_count_range", "suite": suite, "field": field, "bound": "max"})
    if isinstance(lower, (int, float)) and isinstance(upper, (int, float)) and lower > upper:
        errors.append({"kind": "invalid_expected_count_range", "suite": suite, "field": field, "message": "min exceeds max"})

    mismatch = False
    if isinstance(actual_value, bool) or not isinstance(actual_value, (int, float)):
        mismatch = True
    if isinstance(lower, (int, float)) and not mismatch and actual_value < lower:
        mismatch = True
    if isinstance(upper, (int, float)) and not mismatch and actual_value > upper:
        mismatch = True
    if mismatch:
        errors.append(
            {
                "kind": "expected_count_range_mismatch",
                "suite": suite,
                "field": field,
                "expected": spec,
                "actual": actual_value,
            }
        )
    return {"min": lower, "max": upper}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def evidence_excerpt(log: str, needle: str, radius: int = 180) -> str | None:
    index = log.find(needle)
    if index < 0:
        return None
    start = max(0, index - radius)
    end = min(len(log), index + len(needle) + radius)
    excerpt = log[start:end].replace("\r", "")
    lines = [line.rstrip() for line in excerpt.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def validate(summary: dict[str, Any], classifications: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    classified: list[dict[str, Any]] = []

    if classifications.get("schema") != SCHEMA:
        errors.append({"kind": "schema", "message": f"schema must be {SCHEMA}"})

    issue_results = {}
    for result in summary.get("results", []):
        if result.get("result") != "ok" or has_hard_process_signal(result):
            issue_results[result.get("suite")] = result
    classification_items = classifications.get("issues", [])
    if not isinstance(classification_items, list):
        errors.append({"kind": "classification_shape", "message": "issues must be a list"})
        classification_items = []

    classification_by_suite = {}
    for item in classification_items:
        suite = item.get("suite")
        if not suite:
            errors.append({"kind": "classification_missing_suite", "classification": item})
            continue
        if suite in classification_by_suite:
            errors.append({"kind": "duplicate_classification", "suite": suite})
        classification_by_suite[suite] = item

    for suite, result in sorted(issue_results.items()):
        item = classification_by_suite.get(suite)
        if item is None:
            errors.append({"kind": "unclassified_issue", "suite": suite, "result": result.get("result")})
            continue
        expected = item.get("expected_result")
        if result.get("result") != expected:
            errors.append(
                {
                    "kind": "result_mismatch",
                    "suite": suite,
                    "expected_result": expected,
                    "actual_result": result.get("result"),
                }
            )
        reason = str(item.get("reason", "")).strip()
        if not reason:
            errors.append({"kind": "missing_reason", "suite": suite})
        elif reason.lower() in PLACEHOLDER_TEXT:
            errors.append({"kind": "placeholder_reason", "suite": suite})

        log = read_text(Path(result.get("log", "")))
        required_evidence = item.get("required_evidence")
        if not isinstance(required_evidence, list) or not required_evidence:
            errors.append({"kind": "missing_required_evidence_list", "suite": suite})
            required_evidence = []
        elif not all(str(needle).strip() for needle in required_evidence):
            errors.append({"kind": "blank_required_evidence", "suite": suite})
        elif any(str(needle).strip().lower() in PLACEHOLDER_TEXT for needle in required_evidence):
            errors.append({"kind": "placeholder_required_evidence", "suite": suite})
        missing_evidence = [
            needle
            for needle in required_evidence
            if needle not in log
        ]
        matched_evidence = [
            {
                "needle": needle,
                "excerpt": evidence_excerpt(log, needle),
            }
            for needle in required_evidence
            if needle in log
        ]
        if missing_evidence:
            errors.append({"kind": "missing_evidence", "suite": suite, "missing": missing_evidence})
        expected_counts = item.get("expected_counts")
        expected_count_ranges = item.get("expected_count_ranges")
        if expected_counts is None:
            expected_counts = {}
        if expected_count_ranges is None:
            expected_count_ranges = {}
        if not isinstance(expected_counts, dict):
            errors.append({"kind": "invalid_expected_counts", "suite": suite})
            expected_counts = {}
        if not isinstance(expected_count_ranges, dict):
            errors.append({"kind": "invalid_expected_count_ranges", "suite": suite})
            expected_count_ranges = {}
        if not expected_counts and not expected_count_ranges:
            errors.append({"kind": "missing_expected_counts", "suite": suite})
        for field, expected_value in expected_counts.items():
            if field not in EXPECTED_COUNT_FIELDS:
                errors.append({"kind": "unknown_expected_count_field", "suite": suite, "field": field})
                continue
            actual_value = result.get(field)
            if actual_value != expected_value:
                errors.append(
                    {
                        "kind": "expected_count_mismatch",
                        "suite": suite,
                        "field": field,
                        "expected": expected_value,
                        "actual": actual_value,
                    }
                )
        normalized_count_ranges = {
            field: validate_count_range(suite, field, spec, result.get(field), errors)
            for field, spec in expected_count_ranges.items()
        }
        configured_hard_blocker = bool(item.get("hard_blocker", True))
        required_hard_blocker = (
            result.get("result") in HARD_BLOCKING_RESULTS
            or has_hard_process_signal(result)
        )
        if required_hard_blocker and not configured_hard_blocker:
            errors.append(
                {
                    "kind": "nonblocking_hard_failure",
                    "suite": suite,
                    "result": result.get("result"),
                    "message": "Observed hard failure classes cannot be marked non-blocking",
                }
            )
        classified.append(
            {
                "suite": suite,
                "result": result.get("result"),
                "reason": item.get("reason"),
                "expected_result": expected,
                "matched_required_evidence": matched_evidence,
                "expected_counts": expected_counts,
                "expected_count_ranges": normalized_count_ranges,
                "observed_counts": {
                    field: result.get(field)
                    for field in sorted(EXPECTED_COUNT_FIELDS)
                    if field in result
                },
                "log": result.get("log"),
                "hard_blocker": configured_hard_blocker or required_hard_blocker,
                "hard_blocker_required_by_result": required_hard_blocker,
            }
        )

    stale = sorted(set(classification_by_suite) - set(issue_results))
    for suite in stale:
        errors.append({"kind": "stale_classification", "suite": suite})

    hard_blockers = [item for item in classified if item.get("hard_blocker")]
    return {
        "schema": "freecad-registered-issue-classification-report-v1",
        "result": "ok" if not errors else "failed",
        "classified_issue_count": len(classified),
        "unclassified_issue_count": len([error for error in errors if error.get("kind") == "unclassified_issue"]),
        "hard_blocker_count": len(hard_blockers),
        "classified_issues": classified,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=Path("/tmp/freecad-test-results/freecad-registered-split/summary.json"))
    parser.add_argument("--classifications", type=Path, default=Path("tools/freecad_registered_issue_classifications.default.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = validate(read_json(args.summary), read_json(args.classifications))
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if report["result"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
