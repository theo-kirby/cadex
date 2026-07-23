#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Approve or check CTest disabled/skipped inventory.

The check is intentionally change-tolerant for forward progress:

* approved disabled/skipped tests may become runnable without failing;
* new disabled/skipped tests fail until fixed or explicitly approved;
* reason changes fail because they can hide a test becoming more disabled.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PLACEHOLDER_TEXT = {"todo", "tbd", "n/a", "none", "placeholder"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def current_not_run_with_errors(summary_path: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    summary = read_json(summary_path)
    tests: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, Any]] = []
    not_run = summary.get("ctest", {}).get("not_run", [])
    if not isinstance(not_run, list):
        return tests, [{"kind": "current_inventory_shape", "message": "ctest.not_run must be a list"}]
    for index, item in enumerate(not_run):
        if not isinstance(item, dict):
            errors.append({"kind": "current_not_run_shape", "index": index})
            continue
        name = item.get("name")
        reason = item.get("reason")
        if not name or not reason:
            errors.append({"kind": "current_not_run_missing_name_or_reason", "index": index})
            continue
        if str(reason).strip().lower() in PLACEHOLDER_TEXT:
            errors.append({"kind": "current_not_run_placeholder_reason", "name": name})
        if name in tests:
            errors.append({"kind": "duplicate_current_not_run_test", "name": name})
        tests[name] = {
            "name": name,
            "reason": reason,
            "id": item.get("id"),
        }
    return tests, errors


def current_not_run(summary_path: Path) -> dict[str, dict[str, Any]]:
    tests, _ = current_not_run_with_errors(summary_path)
    return tests


def approve(summary_path: Path, manifest_path: Path) -> None:
    tests = current_not_run(summary_path)
    manifest = {
        "format": 1,
        "policy": {
            "new_disabled_or_skipped_tests_fail": True,
            "removed_disabled_or_skipped_tests_are_ok": True,
            "reason_changes_fail": True,
        },
        "source_summary": str(summary_path),
        "approved_not_run": {
            name: {
                "reason": item["reason"],
                "id_at_approval": item.get("id"),
            }
            for name, item in sorted(tests.items())
        },
    }
    write_json(manifest_path, manifest)


def manifest_policy_failures(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    if manifest.get("format") != 1:
        failures.append({"kind": "manifest_policy", "field": "format", "message": "format must be 1"})
    policy = manifest.get("policy", {})
    required_true = {
        "new_disabled_or_skipped_tests_fail",
        "removed_disabled_or_skipped_tests_are_ok",
        "reason_changes_fail",
    }
    for field in sorted(required_true):
        if policy.get(field) is not True:
            failures.append(
                {
                    "kind": "manifest_policy",
                    "field": field,
                    "message": f"{field} must be true",
                }
            )
    approved = manifest.get("approved_not_run", {})
    if not isinstance(approved, dict):
        failures.append({"kind": "manifest_policy", "field": "approved_not_run", "message": "approved_not_run must be an object"})
        return failures
    for name, item in approved.items():
        if not isinstance(item, dict):
            failures.append({"kind": "manifest_policy", "field": f"approved_not_run.{name}", "message": "approved entry must be an object"})
            continue
        reason = str(item.get("reason") or "").strip()
        if not reason:
            failures.append({"kind": "manifest_policy", "field": f"approved_not_run.{name}.reason", "message": "reason is required"})
        elif reason.lower() in PLACEHOLDER_TEXT:
            failures.append({"kind": "manifest_policy", "field": f"approved_not_run.{name}.reason", "message": "reason must not be placeholder text"})
    return failures


def check(summary_path: Path, manifest_path: Path) -> int:
    current, current_errors = current_not_run_with_errors(summary_path)
    manifest = read_json(manifest_path)
    approved = manifest.get("approved_not_run", {})

    failures: list[dict[str, Any]] = [*manifest_policy_failures(manifest), *current_errors]
    if not isinstance(approved, dict):
        approved = {}
    for name, item in sorted(current.items()):
        approved_item = approved.get(name)
        if approved_item is None:
            failures.append({"kind": "new_not_run_test", "name": name, "reason": item["reason"]})
            continue
        if approved_item.get("reason") != item["reason"]:
            failures.append(
                {
                    "kind": "not_run_reason_changed",
                    "name": name,
                    "approved_reason": approved_item.get("reason"),
                    "current_reason": item["reason"],
                }
            )

    newly_runnable = sorted(set(approved) - set(current))
    report = {
        "result": "failed" if failures else "ok",
        "failure_count": len(failures),
        "failures": failures,
        "approved_not_run_count": len(approved),
        "current_not_run_count": len(current),
        "newly_runnable_count": len(newly_runnable),
        "newly_runnable": newly_runnable,
        "policy": manifest.get("policy", {}),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    approve_parser = sub.add_parser("approve", help="Approve current disabled/skipped inventory")
    approve_parser.add_argument("--summary", type=Path, required=True)
    approve_parser.add_argument("--manifest", type=Path, required=True)

    check_parser = sub.add_parser("check", help="Check current disabled/skipped inventory")
    check_parser.add_argument("--summary", type=Path, required=True)
    check_parser.add_argument("--manifest", type=Path, required=True)

    args = parser.parse_args()
    try:
        if args.command == "approve":
            approve(args.summary, args.manifest)
            return 0
        if args.command == "check":
            return check(args.summary, args.manifest)
    except FileNotFoundError as exc:
        print(
            json.dumps(
                {
                    "result": "failed",
                    "failure_count": 1,
                    "failures": [{"kind": "FileNotFoundError", "message": str(exc)}],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
