#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Self-test final UI/style runner status evaluation."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

import ui_style_run_status


SCHEMA = "freecad-ui-style-run-status-selftest-v1"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_statuses(
    results_dir: Path,
    statuses: dict[str, str],
    run_id: str | None = "selftest-run",
    step_run_ids: dict[str, str | None] | None = None,
) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    if run_id is not None:
        (results_dir / "run.id").write_text(run_id + "\n", encoding="utf-8")
    for step, status in statuses.items():
        (results_dir / f"{step}.command").write_text(f"synthetic {step}\n", encoding="utf-8")
        step_run_id = (step_run_ids or {}).get(step, run_id)
        if step_run_id is not None:
            (results_dir / f"{step}.run_id").write_text(step_run_id + "\n", encoding="utf-8")
        (results_dir / f"{step}.status").write_text(status + "\n", encoding="utf-8")


def scenario(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "result": "pass" if passed else "fail", "details": details}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/freecad-test-results/ui-style-run-status-selftest.json"))
    args = parser.parse_args()

    scenarios = []
    required = ["gate", "audit", "selftest"]
    with tempfile.TemporaryDirectory(prefix="freecad-ui-style-run-status-selftest-") as temp:
        temp_dir = Path(temp)

        all_ok = temp_dir / "all-ok"
        write_statuses(all_ok, {step: "0" for step in required})
        report = ui_style_run_status.build_report(all_ok, required)
        scenarios.append(
            scenario(
                "all_zero_statuses_pass",
                report["result"] == "ok" and report["failure_count"] == 0,
                {"result": report["result"], "failure_count": report["failure_count"]},
            )
        )

        runner = temp_dir / "runner.sh"
        runner.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env bash",
                    "run_step first-step true",
                    "if something; then",
                    "    run_step optional-approve true",
                    "fi",
                    "run_step second-step true",
                    "run_step second-step true",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        parsed = ui_style_run_status.parse_runner_steps(runner)
        scenarios.append(
            scenario(
                "runner_steps_are_discovered_and_deduped",
                parsed == ["first-step", "optional-approve", "second-step"],
                {"parsed": parsed},
            )
        )

        duplicate_runner_results = temp_dir / "duplicate-runner-results"
        write_statuses(duplicate_runner_results, {"first-step": "0", "optional-approve": "0", "second-step": "0"})
        report = ui_style_run_status.build_report(duplicate_runner_results, runner=runner)
        scenarios.append(
            scenario(
                "duplicate_runner_step_fails",
                report["result"] == "failed"
                and "second-step" in report.get("duplicate_runner_steps", [])
                and any(
                    item["step"] == "second-step"
                    and "duplicate_runner_step" in item.get("failure_reasons", [])
                    for item in report["failures"]
                ),
                {
                    "result": report["result"],
                    "duplicate_runner_steps": report.get("duplicate_runner_steps", []),
                    "failures": report["failures"],
                },
            )
        )

        dynamic = temp_dir / "dynamic"
        write_statuses(dynamic, {"first-step": "0", "second-step": "0"})
        report = ui_style_run_status.build_report(
            dynamic,
            runner=runner,
        )
        scenarios.append(
            scenario(
                "conditional_approve_step_is_not_required_when_absent",
                report["result"] == "failed"
                and any(
                    item["step"] == "optional-approve" and item["status"] == "missing"
                    for item in report["failures"]
                ),
                {"result": report["result"], "failures": report["failures"]},
            )
        )

        approve_runner = temp_dir / "approve-runner.sh"
        approve_runner.write_text(
            "run_step gui-visual-approve true\nrun_step required-step true\n",
            encoding="utf-8",
        )
        approve_absent = temp_dir / "approve-absent"
        write_statuses(approve_absent, {"required-step": "0"})
        report = ui_style_run_status.build_report(approve_absent, runner=approve_runner)
        scenarios.append(
            scenario(
                "known_approve_step_is_optional_when_absent",
                report["result"] == "ok"
                and report["required_steps"] == ["required-step"],
                {"result": report["result"], "required_steps": report["required_steps"]},
            )
        )

        approve_present = temp_dir / "approve-present"
        write_statuses(approve_present, {"required-step": "0", "gui-visual-approve": "1"})
        report = ui_style_run_status.build_report(approve_present, runner=approve_runner)
        scenarios.append(
            scenario(
                "known_approve_step_is_checked_when_present",
                report["result"] == "failed"
                and any(item["step"] == "gui-visual-approve" for item in report["failures"]),
                {"result": report["result"], "failures": report["failures"]},
            )
        )

        missing = temp_dir / "missing"
        write_statuses(missing, {"gate": "0", "audit": "0"})
        report = ui_style_run_status.build_report(missing, required)
        scenarios.append(
            scenario(
                "missing_status_fails",
                report["result"] == "failed"
                and any(item["step"] == "selftest" and item["status"] == "missing" for item in report["failures"]),
                {"result": report["result"], "failures": report["failures"]},
            )
        )

        nonzero = temp_dir / "nonzero"
        write_statuses(nonzero, {"gate": "0", "audit": "1", "selftest": "0"})
        report = ui_style_run_status.build_report(nonzero, required)
        scenarios.append(
            scenario(
                "nonzero_status_fails",
                report["result"] == "failed"
                and any(item["step"] == "audit" and item["status"] == "1" for item in report["failures"]),
                {"result": report["result"], "failures": report["failures"]},
            )
        )

        missing_run_id = temp_dir / "missing-run-id"
        write_statuses(missing_run_id, {step: "0" for step in required}, run_id=None)
        report = ui_style_run_status.build_report(missing_run_id, required)
        scenarios.append(
            scenario(
                "missing_current_run_id_fails",
                report["result"] == "failed"
                and any(
                    "missing_current_run_id" in item.get("failure_reasons", [])
                    for item in report["failures"]
                ),
                {"result": report["result"], "failures": report["failures"]},
            )
        )

        stale_run_id = temp_dir / "stale-run-id"
        write_statuses(
            stale_run_id,
            {step: "0" for step in required},
            run_id="current-run",
            step_run_ids={"audit": "old-run"},
        )
        report = ui_style_run_status.build_report(stale_run_id, required)
        scenarios.append(
            scenario(
                "stale_step_run_id_fails",
                report["result"] == "failed"
                and any(
                    item["step"] == "audit"
                    and "stale_step_run_id" in item.get("failure_reasons", [])
                    for item in report["failures"]
                ),
                {"result": report["result"], "failures": report["failures"]},
            )
        )

        missing_command = temp_dir / "missing-command"
        write_statuses(missing_command, {step: "0" for step in required})
        (missing_command / "audit.command").unlink()
        report = ui_style_run_status.build_report(missing_command, required)
        scenarios.append(
            scenario(
                "missing_command_fails",
                report["result"] == "failed"
                and any(
                    item["step"] == "audit"
                    and "missing_command" in item.get("failure_reasons", [])
                    for item in report["failures"]
                ),
                {"result": report["result"], "failures": report["failures"]},
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
    write_json(args.output, report)
    return 0 if report["result"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
