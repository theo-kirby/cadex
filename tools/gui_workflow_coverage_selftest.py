#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Self-test config-driven GUI workflow coverage requirements."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

import evaluate_ui_style_gate


SCHEMA = "freecad-gui-workflow-coverage-selftest-v1"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_coverage_config(output_dir: Path, repo_tools: Path, workflow_config: Path) -> Path:
    config = read_json(repo_tools / "ui_style_coverage.default.json")
    config["fixture_scene_config"] = str(repo_tools / config["fixture_scene_config"])
    config["dialog_scene_config"] = str(repo_tools / config["dialog_scene_config"])
    config["task_scene_config"] = str(repo_tools / config["task_scene_config"])
    config["variant_config"] = str(repo_tools / config["variant_config"])
    config["workflow_config"] = str(workflow_config)
    path = output_dir / "coverage.json"
    write_json(path, config)
    return path


def scenario(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "result": "pass" if passed else "fail", "details": details}


def load_events(summary: dict[str, Any]) -> list[dict[str, Any]]:
    path = Path(summary["gui_workflows_venv"]["events_path"])
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def write_events(path: Path, events: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=Path("/tmp/freecad-test-results/baseline-summary.json"))
    parser.add_argument("--results-dir", type=Path, default=Path("/tmp/freecad-test-results"))
    parser.add_argument("--output", type=Path, default=Path("/tmp/freecad-test-results/gui-workflow-coverage-selftest.json"))
    args = parser.parse_args()

    summary = read_json(args.summary)
    summary["gui_workflow_coverage_selftest"] = {
        "present": True,
        "result": "ok",
        "scenario_count": len(evaluate_ui_style_gate.REQUIRED_WORKFLOW_COVERAGE_SELFTEST_SCENARIOS),
        "scenario_names": sorted(evaluate_ui_style_gate.REQUIRED_WORKFLOW_COVERAGE_SELFTEST_SCENARIOS),
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
    default_gate = default_report["gates"]["gui_exercise"]
    scenarios.append(
        scenario(
            "default_required_workflows_pass",
            default_gate["status"] == "pass",
            {
                "status": default_gate["status"],
                "passed_workflows": default_gate.get("evidence", {}).get("passed_workflows"),
                "required_workflows": default_gate.get("evidence", {}).get("required_workflows"),
            },
        )
    )

    with tempfile.TemporaryDirectory(prefix="freecad-gui-workflow-coverage-selftest-") as temp:
        temp_dir = Path(temp)
        baseline_events = load_events(summary)
        workflow_config = read_json(repo_tools / "gui_workflows.default.json")
        workflow_config["required_workflows"] = list(workflow_config["required_workflows"]) + [
            "selftest_missing_workflow"
        ]
        workflow_path = temp_dir / "workflows.json"
        write_json(workflow_path, workflow_config)
        coverage_path = build_coverage_config(temp_dir, repo_tools, workflow_path)
        mutated_coverage = evaluate_ui_style_gate.load_coverage_spec(coverage_path)
        mutated_report = evaluate_ui_style_gate.evaluate(
            summary, repo_root, args.results_dir, mutated_coverage
        )
        mutated_gate = mutated_report["gates"]["gui_exercise"]
        scenarios.append(
            scenario(
                "new_required_workflow_without_detail_contract_fails_config",
                mutated_gate["status"] == "fail"
                and any(
                    "missing_required_workflow_details:selftest_missing_workflow" in error
                    for error in mutated_gate.get("evidence", {}).get("workflow_config_errors", [])
                ),
                {
                    "status": mutated_gate["status"],
                    "workflow_config_errors": mutated_gate.get("evidence", {}).get(
                        "workflow_config_errors", []
                    ),
                },
            )
        )

        specified_missing_config = read_json(repo_tools / "gui_workflows.default.json")
        specified_missing_config["required_workflows"] = list(
            specified_missing_config["required_workflows"]
        ) + ["selftest_missing_workflow"]
        specified_missing_config["required_workflow_details"] = {
            **specified_missing_config["required_workflow_details"],
            "selftest_missing_workflow": [
                {
                    "status": "workflow_detail",
                    "fields_equal": {
                        "marker": "selftest"
                    },
                }
            ],
        }
        specified_missing_path = temp_dir / "specified-missing-workflows.json"
        write_json(specified_missing_path, specified_missing_config)
        specified_missing_coverage_path = build_coverage_config(
            temp_dir, repo_tools, specified_missing_path
        )
        specified_missing_report = evaluate_ui_style_gate.evaluate(
            summary,
            repo_root,
            args.results_dir,
            evaluate_ui_style_gate.load_coverage_spec(specified_missing_coverage_path),
        )
        specified_missing_gate = specified_missing_report["gates"]["gui_exercise"]
        scenarios.append(
            scenario(
                "new_required_workflow_with_detail_contract_fails_without_runtime_events",
                specified_missing_gate["status"] == "fail"
                and "selftest_missing_workflow"
                in specified_missing_gate.get("evidence", {}).get("missing_workflows", [])
                and any(
                    failure.get("workflow") == "selftest_missing_workflow"
                    for failure in specified_missing_gate.get("evidence", {}).get("detail_failures", [])
                ),
                {
                    "status": specified_missing_gate["status"],
                    "missing_workflows": specified_missing_gate.get("evidence", {}).get(
                        "missing_workflows", []
                    ),
                    "detail_failures": specified_missing_gate.get("evidence", {}).get(
                        "detail_failures", []
                    ),
                },
            )
        )

        missing_detail_summary = json.loads(json.dumps(summary))
        missing_detail_events = [
            event
            for event in baseline_events
            if not (
                event.get("workflow") == "create_body"
                and event.get("status") == "workflow_detail"
            )
        ]
        missing_detail_events_path = temp_dir / "missing-detail-events.jsonl"
        write_events(missing_detail_events_path, missing_detail_events)
        missing_detail_summary["gui_workflows_venv"]["events_path"] = str(missing_detail_events_path)
        missing_detail_report = evaluate_ui_style_gate.evaluate(
            missing_detail_summary, repo_root, args.results_dir, default_coverage
        )
        missing_detail_gate = missing_detail_report["gates"]["gui_exercise"]
        scenarios.append(
            scenario(
                "missing_required_workflow_detail_fails_gate",
                missing_detail_gate["status"] == "fail"
                and any(
                    failure.get("workflow") == "create_body"
                    for failure in missing_detail_gate.get("evidence", {}).get("detail_failures", [])
                ),
                {
                    "status": missing_detail_gate["status"],
                    "detail_failures": missing_detail_gate.get("evidence", {}).get("detail_failures", []),
                },
            )
        )

        out_of_window_detail_summary = json.loads(json.dumps(summary))
        create_body_detail = next(
            event
            for event in baseline_events
            if event.get("workflow") == "create_body"
            and event.get("status") == "workflow_detail"
        )
        out_of_window_events = [
            create_body_detail,
            *[
                event
                for event in baseline_events
                if event is not create_body_detail
            ],
        ]
        out_of_window_events_path = temp_dir / "out-of-window-detail-events.jsonl"
        write_events(out_of_window_events_path, out_of_window_events)
        out_of_window_detail_summary["gui_workflows_venv"]["events_path"] = str(
            out_of_window_events_path
        )
        out_of_window_detail_report = evaluate_ui_style_gate.evaluate(
            out_of_window_detail_summary, repo_root, args.results_dir, default_coverage
        )
        out_of_window_detail_gate = out_of_window_detail_report["gates"]["gui_exercise"]
        scenarios.append(
            scenario(
                "workflow_detail_outside_start_pass_window_fails_gate",
                out_of_window_detail_gate["status"] == "fail"
                and any(
                    failure.get("workflow") == "create_body"
                    for failure in out_of_window_detail_gate.get("evidence", {}).get("detail_failures", [])
                ),
                {
                    "status": out_of_window_detail_gate["status"],
                    "detail_failures": out_of_window_detail_gate.get("evidence", {}).get("detail_failures", []),
                    "workflow_windows": out_of_window_detail_gate.get("evidence", {}).get("workflow_windows", {}),
                },
            )
        )

        failing_event_summary = json.loads(json.dumps(summary))
        failing_events = list(baseline_events) + [
            {
                "status": "workflow_fail",
                "workflow": "create_body",
                "error": "selftest injected failure",
            }
        ]
        failing_events_path = temp_dir / "failing-events.jsonl"
        write_events(failing_events_path, failing_events)
        failing_event_summary["gui_workflows_venv"]["events_path"] = str(failing_events_path)
        failing_event_report = evaluate_ui_style_gate.evaluate(
            failing_event_summary, repo_root, args.results_dir, default_coverage
        )
        failing_event_gate = failing_event_report["gates"]["gui_exercise"]
        scenarios.append(
            scenario(
                "workflow_fail_event_fails_gate",
                failing_event_gate["status"] == "fail"
                and "create_body" in failing_event_gate.get("evidence", {}).get("failed_workflows", []),
                {
                    "status": failing_event_gate["status"],
                    "failed_workflows": failing_event_gate.get("evidence", {}).get("failed_workflows", []),
                },
            )
        )

        duplicate_start_summary = json.loads(json.dumps(summary))
        create_body_start = next(
            event
            for event in baseline_events
            if event.get("workflow") == "create_body"
            and event.get("status") == "workflow_started"
        )
        duplicate_start_events = list(baseline_events) + [create_body_start]
        duplicate_start_events_path = temp_dir / "duplicate-start-events.jsonl"
        write_events(duplicate_start_events_path, duplicate_start_events)
        duplicate_start_summary["gui_workflows_venv"]["events_path"] = str(
            duplicate_start_events_path
        )
        duplicate_start_report = evaluate_ui_style_gate.evaluate(
            duplicate_start_summary, repo_root, args.results_dir, default_coverage
        )
        duplicate_start_gate = duplicate_start_report["gates"]["gui_exercise"]
        scenarios.append(
            scenario(
                "duplicate_workflow_start_event_fails_gate",
                duplicate_start_gate["status"] == "fail"
                and any(
                    failure.get("workflow") == "create_body"
                    and len(failure.get("start_indices", [])) > 1
                    for failure in duplicate_start_gate.get("evidence", {}).get(
                        "duplicate_event_failures", []
                    )
                ),
                {
                    "status": duplicate_start_gate["status"],
                    "duplicate_event_failures": duplicate_start_gate.get("evidence", {}).get(
                        "duplicate_event_failures", []
                    ),
                },
            )
        )

        duplicate_pass_summary = json.loads(json.dumps(summary))
        create_body_pass = next(
            event
            for event in baseline_events
            if event.get("workflow") == "create_body"
            and event.get("status") == "workflow_pass"
        )
        duplicate_pass_events = list(baseline_events) + [create_body_pass]
        duplicate_pass_events_path = temp_dir / "duplicate-pass-events.jsonl"
        write_events(duplicate_pass_events_path, duplicate_pass_events)
        duplicate_pass_summary["gui_workflows_venv"]["events_path"] = str(
            duplicate_pass_events_path
        )
        duplicate_pass_report = evaluate_ui_style_gate.evaluate(
            duplicate_pass_summary, repo_root, args.results_dir, default_coverage
        )
        duplicate_pass_gate = duplicate_pass_report["gates"]["gui_exercise"]
        scenarios.append(
            scenario(
                "duplicate_workflow_pass_event_fails_gate",
                duplicate_pass_gate["status"] == "fail"
                and any(
                    failure.get("workflow") == "create_body"
                    and len(failure.get("pass_indices", [])) > 1
                    for failure in duplicate_pass_gate.get("evidence", {}).get(
                        "duplicate_event_failures", []
                    )
                ),
                {
                    "status": duplicate_pass_gate["status"],
                    "duplicate_event_failures": duplicate_pass_gate.get("evidence", {}).get(
                        "duplicate_event_failures", []
                    ),
                },
            )
        )

        invalid_json_event_summary = json.loads(json.dumps(summary))
        invalid_json_events_path = temp_dir / "invalid-json-events.jsonl"
        invalid_json_events_path.write_text(
            json.dumps(baseline_events[0], sort_keys=True) + "\nnot json\n",
            encoding="utf-8",
        )
        invalid_json_event_summary["gui_workflows_venv"]["events_path"] = str(
            invalid_json_events_path
        )
        invalid_json_event_report = evaluate_ui_style_gate.evaluate(
            invalid_json_event_summary, repo_root, args.results_dir, default_coverage
        )
        invalid_json_event_gate = invalid_json_event_report["gates"]["gui_exercise"]
        scenarios.append(
            scenario(
                "invalid_workflow_event_json_fails_gate",
                invalid_json_event_gate["status"] == "fail"
                and any(
                    "invalid_workflow_event_json" in error
                    for error in invalid_json_event_gate.get("evidence", {}).get("event_errors", [])
                ),
                {
                    "status": invalid_json_event_gate["status"],
                    "event_errors": invalid_json_event_gate.get("evidence", {}).get("event_errors", []),
                },
            )
        )

        event_path_directory_summary = json.loads(json.dumps(summary))
        event_path_directory = temp_dir / "events-path-is-directory"
        event_path_directory.mkdir()
        event_path_directory_summary["gui_workflows_venv"]["events_path"] = str(event_path_directory)
        event_path_directory_report = evaluate_ui_style_gate.evaluate(
            event_path_directory_summary, repo_root, args.results_dir, default_coverage
        )
        event_path_directory_gate = event_path_directory_report["gates"]["gui_exercise"]
        scenarios.append(
            scenario(
                "workflow_event_directory_path_fails_gate",
                event_path_directory_gate["status"] == "fail"
                and any(
                    "workflow_events_path_not_file" in error
                    for error in event_path_directory_gate.get("evidence", {}).get("event_errors", [])
                ),
                {
                    "status": event_path_directory_gate["status"],
                    "event_errors": event_path_directory_gate.get("evidence", {}).get("event_errors", []),
                },
            )
        )

        invalid_detail_config = read_json(repo_tools / "gui_workflows.default.json")
        invalid_detail_config["required_workflow_details"] = {
            **invalid_detail_config["required_workflow_details"],
            "create_body": [
                {
                    "status": "",
                    "fields_present": "object",
                    "fields_equal": [],
                }
            ],
        }
        invalid_detail_path = temp_dir / "invalid-detail-workflows.json"
        write_json(invalid_detail_path, invalid_detail_config)
        invalid_detail_coverage_path = build_coverage_config(
            temp_dir, repo_tools, invalid_detail_path
        )
        invalid_detail_report = evaluate_ui_style_gate.evaluate(
            summary,
            repo_root,
            args.results_dir,
            evaluate_ui_style_gate.load_coverage_spec(invalid_detail_coverage_path),
        )
        invalid_detail_gate = invalid_detail_report["gates"]["gui_exercise"]
        invalid_detail_errors = invalid_detail_gate.get("evidence", {}).get("workflow_config_errors", [])
        scenarios.append(
            scenario(
                "invalid_required_workflow_detail_config_fails_gate",
                invalid_detail_gate["status"] == "fail"
                and any("missing_workflow_detail_status:create_body:0" in error for error in invalid_detail_errors)
                and any("workflow_detail_fields_equal_must_be_object:create_body:0" in error for error in invalid_detail_errors),
                {
                    "status": invalid_detail_gate["status"],
                    "workflow_config_errors": invalid_detail_errors,
                },
            )
        )

        duplicate_config = read_json(repo_tools / "gui_workflows.default.json")
        duplicate_config["required_workflows"] = list(duplicate_config["required_workflows"]) + [
            duplicate_config["required_workflows"][0]
        ]
        duplicate_path = temp_dir / "duplicate-workflows.json"
        write_json(duplicate_path, duplicate_config)
        duplicate_coverage_path = build_coverage_config(temp_dir, repo_tools, duplicate_path)
        duplicate_report = evaluate_ui_style_gate.evaluate(
            summary,
            repo_root,
            args.results_dir,
            evaluate_ui_style_gate.load_coverage_spec(duplicate_coverage_path),
        )
        duplicate_gate = duplicate_report["gates"]["gui_exercise"]
        scenarios.append(
            scenario(
                "duplicate_required_workflow_fails_config",
                duplicate_gate["status"] == "fail"
                and any(
                    "duplicate_required_workflow" in error
                    for error in duplicate_gate.get("evidence", {}).get("workflow_config_errors", [])
                ),
                {
                    "status": duplicate_gate["status"],
                    "workflow_config_errors": duplicate_gate.get("evidence", {}).get(
                        "workflow_config_errors", []
                    ),
                },
            )
        )

        blank_config = read_json(repo_tools / "gui_workflows.default.json")
        blank_config["required_workflows"] = list(blank_config["required_workflows"]) + [""]
        blank_path = temp_dir / "blank-workflows.json"
        write_json(blank_path, blank_config)
        blank_coverage_path = build_coverage_config(temp_dir, repo_tools, blank_path)
        blank_report = evaluate_ui_style_gate.evaluate(
            summary,
            repo_root,
            args.results_dir,
            evaluate_ui_style_gate.load_coverage_spec(blank_coverage_path),
        )
        blank_gate = blank_report["gates"]["gui_exercise"]
        scenarios.append(
            scenario(
                "blank_required_workflow_fails_config",
                blank_gate["status"] == "fail"
                and any(
                    "blank_required_workflow" in error
                    for error in blank_gate.get("evidence", {}).get("workflow_config_errors", [])
                ),
                {
                    "status": blank_gate["status"],
                    "workflow_config_errors": blank_gate.get("evidence", {}).get(
                        "workflow_config_errors", []
                    ),
                },
            )
        )

    failed = [item["name"] for item in scenarios if item["result"] != "pass"]
    report = {
        "schema": SCHEMA,
        "result": "ok" if not failed else "failed",
        "scenario_count": len(scenarios),
        "scenario_names": [item["name"] for item in scenarios],
        "failed_scenarios": failed,
        "scenarios": scenarios,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, report)
    return 0 if report["result"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
