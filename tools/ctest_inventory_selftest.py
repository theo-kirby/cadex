#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Self-test CTest disabled/skipped inventory regression checks."""

from __future__ import annotations

import argparse
import copy
import json
import tempfile
from pathlib import Path
from typing import Any

import ctest_inventory_regression as inventory


SCHEMA = "freecad-ctest-inventory-selftest-v1"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def summary(not_run: list[dict[str, Any]]) -> dict[str, Any]:
    return {"ctest": {"not_run": not_run}}


def run_check(work_dir: Path, current: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    summary_path = work_dir / "summary.json"
    manifest_path = work_dir / "manifest.json"
    write_json(summary_path, current)
    write_json(manifest_path, manifest)
    current_tests, current_errors = inventory.current_not_run_with_errors(summary_path)
    approved = manifest.get("approved_not_run", {})
    failures = [*inventory.manifest_policy_failures(manifest), *current_errors]
    if not isinstance(approved, dict):
        approved = {}
    for name, item in sorted(current_tests.items()):
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
    newly_runnable = sorted(set(approved) - set(current_tests))
    return {
        "result": "failed" if failures else "ok",
        "failure_kinds": sorted({failure["kind"] for failure in failures}),
        "failure_count": len(failures),
        "newly_runnable_count": len(newly_runnable),
    }


def run_case(
    name: str,
    work_dir: Path,
    current: dict[str, Any],
    manifest: dict[str, Any],
    expected_result: str,
    expected_failure_kind: str | None = None,
    expected_newly_runnable_count: int | None = None,
) -> dict[str, Any]:
    report = run_check(work_dir / name, current, manifest)
    ok = report["result"] == expected_result
    if expected_failure_kind:
        ok = ok and expected_failure_kind in report["failure_kinds"]
    if expected_newly_runnable_count is not None:
        ok = ok and report["newly_runnable_count"] == expected_newly_runnable_count
    return {
        "ok": ok,
        "expected_result": expected_result,
        "expected_failure_kind": expected_failure_kind,
        "expected_newly_runnable_count": expected_newly_runnable_count,
        **report,
    }


def base_manifest() -> dict[str, Any]:
    return {
        "format": 1,
        "policy": {
            "new_disabled_or_skipped_tests_fail": True,
            "removed_disabled_or_skipped_tests_are_ok": True,
            "reason_changes_fail": True,
        },
        "approved_not_run": {
            "KnownDisabled": {
                "reason": "Disabled",
                "id_at_approval": 1,
            }
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/freecad-test-results/ctest-inventory-selftest.json"))
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="freecad-ctest-inventory-selftest-") as temp:
        work_dir = Path(temp)
        current = summary([{"id": 1, "name": "KnownDisabled", "reason": "Disabled"}])
        manifest = base_manifest()

        new_not_run = summary(
            [
                {"id": 1, "name": "KnownDisabled", "reason": "Disabled"},
                {"id": 2, "name": "NewSkipped", "reason": "Skipped"},
            ]
        )
        reason_changed = summary([{"id": 1, "name": "KnownDisabled", "reason": "Skipped"}])
        removed = summary([])
        lax_policy = copy.deepcopy(manifest)
        lax_policy["policy"]["new_disabled_or_skipped_tests_fail"] = False
        duplicate_current = summary(
            [
                {"id": 1, "name": "KnownDisabled", "reason": "Disabled"},
                {"id": 2, "name": "KnownDisabled", "reason": "Disabled"},
            ]
        )
        placeholder_manifest_reason = copy.deepcopy(manifest)
        placeholder_manifest_reason["approved_not_run"]["KnownDisabled"]["reason"] = "TODO"

        scenarios = {
            "valid_inventory_passes": run_case(
                "valid_inventory_passes", work_dir, current, manifest, "ok"
            ),
            "new_not_run_test_fails": run_case(
                "new_not_run_test_fails",
                work_dir,
                new_not_run,
                manifest,
                "failed",
                "new_not_run_test",
            ),
            "reason_change_fails": run_case(
                "reason_change_fails",
                work_dir,
                reason_changed,
                manifest,
                "failed",
                "not_run_reason_changed",
            ),
            "removed_not_run_test_passes": run_case(
                "removed_not_run_test_passes",
                work_dir,
                removed,
                manifest,
                "ok",
                expected_newly_runnable_count=1,
            ),
            "lax_manifest_policy_fails": run_case(
                "lax_manifest_policy_fails",
                work_dir,
                current,
                lax_policy,
                "failed",
                "manifest_policy",
            ),
            "duplicate_current_not_run_test_fails": run_case(
                "duplicate_current_not_run_test_fails",
                work_dir,
                duplicate_current,
                manifest,
                "failed",
                "duplicate_current_not_run_test",
            ),
            "placeholder_manifest_reason_fails": run_case(
                "placeholder_manifest_reason_fails",
                work_dir,
                current,
                placeholder_manifest_reason,
                "failed",
                "manifest_policy",
            ),
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
