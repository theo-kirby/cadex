#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Self-test config-driven layout assertion coverage requirements."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

import evaluate_ui_style_gate


SCHEMA = "freecad-gui-layout-assertion-coverage-selftest-v1"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_coverage_config(output_dir: Path, repo_tools: Path, layout_config: Path) -> Path:
    config = read_json(repo_tools / "ui_style_coverage.default.json")
    for key in (
        "fixture_scene_config",
        "dialog_scene_config",
        "task_scene_config",
        "variant_config",
        "workflow_config",
    ):
        config[key] = str(repo_tools / config[key])
    config["layout_assertion_config"] = str(layout_config)
    path = output_dir / "coverage.json"
    write_json(path, config)
    return path


def scenario(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "result": "pass" if passed else "fail", "details": details}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=Path("/tmp/freecad-test-results/baseline-summary.json"))
    parser.add_argument("--results-dir", type=Path, default=Path("/tmp/freecad-test-results"))
    parser.add_argument("--output", type=Path, default=Path("/tmp/freecad-test-results/gui-layout-assertion-coverage-selftest.json"))
    args = parser.parse_args()

    summary = read_json(args.summary)
    summary["layout_assertion_coverage_selftest"] = {
        "present": True,
        "result": "ok",
        "scenario_count": 0,
        "failed_scenarios": [],
        "report": str(args.output),
    }
    repo_tools = Path(__file__).resolve().parent
    repo_root = repo_tools.parent
    scenarios = []

    default_coverage = evaluate_ui_style_gate.load_coverage_spec(
        repo_tools / "ui_style_coverage.default.json"
    )
    default_report = evaluate_ui_style_gate.evaluate(
        summary, repo_root, args.results_dir, default_coverage
    )
    default_gate = default_report["gates"]["layout_assertions"]
    scenarios.append(
        scenario(
            "default_required_layout_assertions_pass",
            default_gate["status"] == "pass",
            {
                "status": default_gate["status"],
                "observed": default_gate.get("evidence", {}).get("observed"),
                "required": default_gate.get("evidence", {}).get("required"),
            },
        )
    )

    with tempfile.TemporaryDirectory(prefix="freecad-layout-assertion-coverage-selftest-") as temp:
        temp_dir = Path(temp)
        layout_config = read_json(repo_tools / "gui_layout_assertions.default.json")
        layout_config["required_assertions"] = list(layout_config["required_assertions"]) + [
            "selftest_missing_layout_assertion"
        ]
        layout_path = temp_dir / "layout.json"
        write_json(layout_path, layout_config)
        coverage_path = build_coverage_config(temp_dir, repo_tools, layout_path)
        mutated_report = evaluate_ui_style_gate.evaluate(
            summary,
            repo_root,
            args.results_dir,
            evaluate_ui_style_gate.load_coverage_spec(coverage_path),
        )
        mutated_gate = mutated_report["gates"]["layout_assertions"]
        scenarios.append(
            scenario(
                "new_required_layout_assertion_fails_gate",
                mutated_gate["status"] == "fail"
                and "selftest_missing_layout_assertion"
                in mutated_gate.get("evidence", {}).get("missing", []),
                {
                    "status": mutated_gate["status"],
                    "missing": mutated_gate.get("evidence", {}).get("missing", []),
                },
            )
        )

        duplicate_config = read_json(repo_tools / "gui_layout_assertions.default.json")
        duplicate_config["required_assertions"] = list(duplicate_config["required_assertions"]) + [
            duplicate_config["required_assertions"][0]
        ]
        duplicate_path = temp_dir / "duplicate-layout.json"
        write_json(duplicate_path, duplicate_config)
        duplicate_coverage_path = build_coverage_config(temp_dir, repo_tools, duplicate_path)
        duplicate_report = evaluate_ui_style_gate.evaluate(
            summary,
            repo_root,
            args.results_dir,
            evaluate_ui_style_gate.load_coverage_spec(duplicate_coverage_path),
        )
        duplicate_gate = duplicate_report["gates"]["layout_assertions"]
        scenarios.append(
            scenario(
                "duplicate_required_layout_assertion_fails_config",
                duplicate_gate["status"] == "fail"
                and any(
                    "duplicate_required_assertion" in error
                    for error in duplicate_gate.get("evidence", {}).get("layout_config_errors", [])
                ),
                {
                    "status": duplicate_gate["status"],
                    "layout_config_errors": duplicate_gate.get("evidence", {}).get(
                        "layout_config_errors", []
                    ),
                },
            )
        )

        blank_config = read_json(repo_tools / "gui_layout_assertions.default.json")
        blank_config["required_assertions"] = list(blank_config["required_assertions"]) + [""]
        blank_path = temp_dir / "blank-layout.json"
        write_json(blank_path, blank_config)
        blank_coverage_path = build_coverage_config(temp_dir, repo_tools, blank_path)
        blank_report = evaluate_ui_style_gate.evaluate(
            summary,
            repo_root,
            args.results_dir,
            evaluate_ui_style_gate.load_coverage_spec(blank_coverage_path),
        )
        blank_gate = blank_report["gates"]["layout_assertions"]
        scenarios.append(
            scenario(
                "blank_required_layout_assertion_fails_config",
                blank_gate["status"] == "fail"
                and any(
                    "blank_required_assertion" in error
                    for error in blank_gate.get("evidence", {}).get("layout_config_errors", [])
                ),
                {
                    "status": blank_gate["status"],
                    "layout_config_errors": blank_gate.get("evidence", {}).get(
                        "layout_config_errors", []
                    ),
                },
            )
        )

        failed_smoke_summary = json.loads(json.dumps(summary))
        failed_smoke_summary["layout_assertion_smoke"]["result"] = "process_failed"
        failed_smoke_summary["layout_assertion_smoke"]["process_returncode"] = 1
        failed_smoke_report = evaluate_ui_style_gate.evaluate(
            failed_smoke_summary,
            repo_root,
            args.results_dir,
            default_coverage,
        )
        failed_smoke_gate = failed_smoke_report["gates"]["layout_assertions"]
        scenarios.append(
            scenario(
                "failed_layout_smoke_result_fails_gate",
                failed_smoke_gate["status"] == "fail"
                and failed_smoke_gate.get("evidence", {}).get("smoke_result") == "process_failed",
                {
                    "status": failed_smoke_gate["status"],
                    "smoke_result": failed_smoke_gate.get("evidence", {}).get("smoke_result"),
                    "process_returncode": failed_smoke_gate.get("evidence", {}).get("process_returncode"),
                },
            )
        )

    failed = [item["name"] for item in scenarios if item["result"] != "pass"]
    report = {
        "schema": SCHEMA,
        "result": "ok" if not failed else "failed",
        "scenario_count": len(scenarios),
        "failed_scenarios": failed,
        "scenarios": scenarios,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, report)
    return 0 if report["result"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
