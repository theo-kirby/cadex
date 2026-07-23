#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Self-test strict JSON artifact integrity checks."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

import json_artifact_integrity


SCHEMA = "freecad-json-artifact-integrity-selftest-v1"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/freecad-test-results/json-artifact-integrity-selftest.json"),
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="freecad-json-artifact-integrity-selftest-") as temp:
        root = Path(temp)
        good = root / "good.json"
        prefixed = root / "prefixed.json"
        nested = root / "nested" / "summary.json"
        output = root / "report.json"
        write_json(good, {"result": "ok"})
        write_json(nested, {"result": "ok"})
        prefixed.write_text('== prefixed ==\n{"result": "ok"}\n', encoding="utf-8")

        report = json_artifact_integrity.validate_json_artifacts(root, output)
        included_report = json_artifact_integrity.validate_json_artifacts(
            root,
            output,
            ["good.json", "nested/summary.json"],
        )
        duplicate_include_report = json_artifact_integrity.validate_json_artifacts(
            root,
            output,
            ["good.json", "good.json"],
        )
        escaping_include_report = json_artifact_integrity.validate_json_artifacts(
            root,
            output,
            ["../outside.json"],
        )
        scenarios = {
            "strict_json_files_are_accepted": {
                "ok": report["checked_count"] == 3
                and report["checked"] == ["good.json", "nested/summary.json", "prefixed.json"],
                "checked_count": report["checked_count"],
                "checked": report["checked"],
            },
            "prefixed_json_is_rejected": {
                "ok": report["failure_count"] == 1 and report["failures"][0]["path"] == "prefixed.json",
                "failure_count": report["failure_count"],
                "failures": report["failures"],
            },
            "include_list_ignores_unowned_json_files": {
                "ok": included_report["result"] == "ok"
                and included_report["checked_count"] == 2
                and included_report["checked"] == ["good.json", "nested/summary.json"],
                "result": included_report["result"],
                "checked_count": included_report["checked_count"],
                "checked": included_report["checked"],
                "failure_count": included_report["failure_count"],
            },
            "duplicate_include_pattern_is_rejected": {
                "ok": duplicate_include_report["result"] == "failed"
                and any(
                    failure["error"] == "duplicate include pattern"
                    for failure in duplicate_include_report["failures"]
                ),
                "result": duplicate_include_report["result"],
                "failures": duplicate_include_report["failures"],
            },
            "escaping_include_pattern_is_rejected": {
                "ok": escaping_include_report["result"] == "failed"
                and any(
                    failure["error"] == "include pattern must stay within results-dir"
                    for failure in escaping_include_report["failures"]
                ),
                "result": escaping_include_report["result"],
                "failures": escaping_include_report["failures"],
            },
        }

    failed = [name for name, result in scenarios.items() if not result["ok"]]
    final_report = {
        "schema": SCHEMA,
        "result": "ok" if not failed else "failed",
        "scenario_count": len(scenarios),
        "scenario_names": sorted(scenarios),
        "failed_scenarios": failed,
        "scenarios": scenarios,
    }
    write_json(args.output, final_report)
    return 0 if final_report["result"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
