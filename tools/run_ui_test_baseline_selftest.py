#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Self-test baseline runner shell behavior."""

from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


SCHEMA = "freecad-run-ui-test-baseline-selftest-v1"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def extract_run_step(runner: Path) -> str:
    lines = runner.read_text(encoding="utf-8").splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == "run_step() {":
            start = index
            break
    if start is None:
        raise ValueError("run_step function not found")
    body = []
    for line in lines[start:]:
        body.append(line)
        if line == "}":
            break
    if not body or body[-1] != "}":
        raise ValueError("run_step function end not found")
    return "\n".join(body) + "\n"


def strict_json(path: Path) -> tuple[bool, str | None]:
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True, None
    except Exception as exc:
        return False, str(exc)


def run_step_output_case(work_dir: Path, runner: Path) -> dict[str, Any]:
    results_dir = work_dir / "results"
    results_dir.mkdir()
    script = work_dir / "runner-selftest.sh"
    run_step_function = extract_run_step(runner)
    script.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -u",
                f"results_dir={str(results_dir)!r}",
                "run_id=selftest-run",
                'runner_log="$results_dir/run-ui-test-baseline.log"',
                ': > "$runner_log"',
                run_step_function,
                (
                    "run_step json-clean python3 -c "
                    "'import json; print(json.dumps({\"result\":\"ok\"}))' "
                    '>"$results_dir/json-clean.json" 2>&1'
                ),
                (
                    "run_step json-fail python3 -c "
                    "'import json, sys; print(json.dumps({\"result\":\"failed\"})); sys.exit(7)' "
                    '>"$results_dir/json-fail.json" 2>&1'
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        ["bash", str(script)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )

    clean_json_ok, clean_json_error = strict_json(results_dir / "json-clean.json")
    fail_json_ok, fail_json_error = strict_json(results_dir / "json-fail.json")
    runner_log = (results_dir / "run-ui-test-baseline.log").read_text(encoding="utf-8")
    clean_text = (results_dir / "json-clean.json").read_text(encoding="utf-8")
    fail_text = (results_dir / "json-fail.json").read_text(encoding="utf-8")
    clean_status = (results_dir / "json-clean.status").read_text(encoding="utf-8").strip()
    fail_status = (results_dir / "json-fail.status").read_text(encoding="utf-8").strip()
    clean_output_mtime = (results_dir / "json-clean.json").stat().st_mtime
    clean_run_id_mtime = (results_dir / "json-clean.run_id").stat().st_mtime
    fail_output_mtime = (results_dir / "json-fail.json").stat().st_mtime
    fail_run_id_mtime = (results_dir / "json-fail.run_id").stat().st_mtime
    run_id_markers_after_outputs = (
        clean_run_id_mtime + 1.0 >= clean_output_mtime
        and fail_run_id_mtime + 1.0 >= fail_output_mtime
    )

    return {
        "ok": (
            completed.returncode == 0
            and clean_json_ok
            and fail_json_ok
            and clean_status == "0"
            and fail_status == "7"
            and run_id_markers_after_outputs
            and clean_text.startswith("{")
            and fail_text.startswith("{")
            and "== json-clean ==" in runner_log
            and "== json-fail ==" in runner_log
            and "json-fail exited with status 7" in runner_log
        ),
        "script_returncode": completed.returncode,
        "script_output": completed.stdout,
        "clean_json_ok": clean_json_ok,
        "clean_json_error": clean_json_error,
        "fail_json_ok": fail_json_ok,
        "fail_json_error": fail_json_error,
        "clean_status": clean_status,
        "fail_status": fail_status,
        "run_id_markers_after_outputs": run_id_markers_after_outputs,
        "clean_output_mtime": clean_output_mtime,
        "clean_run_id_mtime": clean_run_id_mtime,
        "fail_output_mtime": fail_output_mtime,
        "fail_run_id_mtime": fail_run_id_mtime,
        "clean_prefix": clean_text[:80],
        "fail_prefix": fail_text[:80],
        "runner_log": runner_log,
    }


def cleanup_scope_case(runner: Path) -> dict[str, Any]:
    text = runner.read_text(encoding="utf-8")
    start = text.find("cleanup_step_artifacts()")
    end = text.find('run_id="$(date -u', start)
    cleanup_block = text[start:end] if start != -1 and end != -1 else ""
    forbidden = [
        "-approved.json",
        "doc-inventory",
        "probe",
    ]
    hits = [item for item in forbidden if item in cleanup_block]
    return {
        "ok": bool(cleanup_block) and not hits,
        "cleanup_block_found": bool(cleanup_block),
        "forbidden_hits": hits,
    }


def gui_interaction_driver_safety_case(runner: Path) -> dict[str, Any]:
    driver = runner.with_name("gui_interaction_driver.py")
    text = driver.read_text(encoding="utf-8")
    required = {
        "file_dialog_detection": "def is_file_or_native_dialog" in text,
        "file_dialog_closed_event": "file_dialog_closed" in text,
        "conservative_combo_skip": "QtWidgets.QComboBox, QtWidgets.QAbstractItemView" in text,
        "conservative_skip_event": "skipped_conservative_widget" in text,
        "unmanaged_dialog_state_skip": "skipped_unmanaged_dialog_state" in text,
    }
    forbidden = {
        "combo_index_mutation": "isinstance(widget, QtWidgets.QComboBox) and widget.count() > 1" in text,
        "item_view_selection_mutation": "widget.setCurrentIndex(index)" in text,
    }
    return {
        "ok": all(required.values()) and not any(forbidden.values()),
        "required": required,
        "forbidden": forbidden,
    }


def visual_approval_requires_metadata_case(runner: Path) -> dict[str, Any]:
    text = runner.read_text(encoding="utf-8")
    approval_calls = text.count("tools/gui_visual_regression.py approve")
    reviewer_args = text.count('--reviewer "$approval_reviewer"')
    note_args = text.count('--approval-note "$approval_note"')
    required = {
        "approval_env_guard": "FREECAD_BASELINE_APPROVE_MISSING=1 requires FREECAD_BASELINE_APPROVER" in text,
        "approval_reviewer_env": 'approval_reviewer="${FREECAD_BASELINE_APPROVER:-}"' in text,
        "approval_note_env": 'approval_note="${FREECAD_BASELINE_APPROVAL_NOTE:-}"' in text,
        "all_approval_calls_have_reviewer": approval_calls > 0 and reviewer_args == approval_calls,
        "all_approval_calls_have_note": approval_calls > 0 and note_args == approval_calls,
    }
    return {
        "ok": all(required.values()),
        "approval_calls": approval_calls,
        "reviewer_args": reviewer_args,
        "note_args": note_args,
        "required": required,
    }


def visual_approval_docs_require_metadata_case(runner: Path) -> dict[str, Any]:
    docs_path = runner.resolve().parent.parent / "docs" / "ui-style-test-baseline.md"
    text = docs_path.read_text(encoding="utf-8") if docs_path.exists() else ""
    approve_blocks = [
        block
        for block in re.findall(r"```sh\n(.*?)\n```", text, flags=re.DOTALL)
        if "tools/gui_visual_regression.py approve" in block
    ]
    missing_metadata = [
        block
        for block in approve_blocks
        if "--reviewer" not in block or "--approval-note" not in block
    ]
    return {
        "ok": bool(approve_blocks) and not missing_metadata,
        "docs_path": str(docs_path),
        "approve_block_count": len(approve_blocks),
        "missing_metadata_count": len(missing_metadata),
        "missing_metadata_examples": missing_metadata[:3],
    }


def approval_guard_runtime_case(work_dir: Path, runner: Path) -> dict[str, Any]:
    text = runner.read_text(encoding="utf-8")
    start = text.find('repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"')
    end = text.find("cleanup_step_artifacts()")
    if start == -1 or end == -1 or end <= start:
        return {"ok": False, "error": "approval guard header block not found"}
    header = text[start:end]
    repo_root = runner.resolve().parent.parent
    header = header.replace(
        'repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"',
        f"repo_root={str(repo_root)!r}",
    )
    results_dir = work_dir / "approval-guard-results"
    script = work_dir / "approval-guard-selftest.sh"
    script.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -u",
                f"FREECAD_BASELINE_RESULTS_DIR={str(results_dir)!r}",
                header,
                'echo "guard passed"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    missing = subprocess.run(
        ["bash", str(script)],
        env={**dict(), "PATH": "/usr/bin:/bin", "FREECAD_BASELINE_APPROVE_MISSING": "1"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    complete = subprocess.run(
        ["bash", str(script)],
        env={
            **dict(),
            "PATH": "/usr/bin:/bin",
            "FREECAD_BASELINE_APPROVE_MISSING": "1",
            "FREECAD_BASELINE_APPROVER": "runner self-test",
            "FREECAD_BASELINE_APPROVAL_NOTE": "approval metadata guard runtime test",
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    disabled = subprocess.run(
        ["bash", str(script)],
        env={**dict(), "PATH": "/usr/bin:/bin", "FREECAD_BASELINE_APPROVE_MISSING": "0"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return {
        "ok": (
            missing.returncode == 2
            and "requires FREECAD_BASELINE_APPROVER" in missing.stdout
            and complete.returncode == 0
            and "guard passed" in complete.stdout
            and disabled.returncode == 0
            and "guard passed" in disabled.stdout
            and repo_root.exists()
        ),
        "missing_returncode": missing.returncode,
        "missing_output": missing.stdout,
        "complete_returncode": complete.returncode,
        "complete_output": complete.stdout,
        "disabled_returncode": disabled.returncode,
        "disabled_output": disabled.stdout,
        "repo_root": str(repo_root),
    }


def visual_manifest_reapproval_detection_case(work_dir: Path, runner: Path) -> dict[str, Any]:
    text = runner.read_text(encoding="utf-8")
    start = text.find("manifest_needs_approval()")
    end = text.find("ctest_inventory_manifest_needs_approval()", start)
    if start == -1 or end == -1 or end <= start:
        return {"ok": False, "error": "manifest_needs_approval function block not found"}
    function_block = text[start:end]
    manifest_dir = work_dir / "visual-manifests"
    manifest_dir.mkdir()

    def write_manifest(name: str, manifest: dict[str, Any]) -> Path:
        path = manifest_dir / name
        write_json(path, manifest)
        return path

    complete_manifest = {
        "format": 2,
        "approval": {
            "reviewer": "runner self-test",
            "note": "complete visual approval manifest",
            "approved_utc": "2026-01-01T00:00:00+00:00",
            "source_capture_dir": "visual-current",
        },
        "policy": {
            "max_changed_ratio": 0.03,
            "max_rms": 8.0,
            "new_findings_fail": True,
            "baseline_images_are_portable": True,
        },
        "scenes": {
            "scene": {
                "screenshot": "approved.baseline-images/scene.png",
                "scene_context_fingerprint": "fingerprint",
                "scene_context_identity": {"scene": "scene"},
            }
        },
    }
    missing_approval = copy.deepcopy(complete_manifest)
    missing_approval.pop("approval", None)
    missing_identity = copy.deepcopy(complete_manifest)
    missing_identity["scenes"]["scene"].pop("scene_context_identity", None)
    lax_policy = copy.deepcopy(complete_manifest)
    lax_policy["policy"]["max_changed_ratio"] = 0.5
    absolute_screenshot = copy.deepcopy(complete_manifest)
    absolute_screenshot["scenes"]["scene"]["screenshot"] = "/tmp/scene.png"

    manifests = {
        "complete": write_manifest("complete.json", complete_manifest),
        "missing_approval": write_manifest("missing-approval.json", missing_approval),
        "missing_identity": write_manifest("missing-identity.json", missing_identity),
        "lax_policy": write_manifest("lax-policy.json", lax_policy),
        "absolute_screenshot": write_manifest("absolute-screenshot.json", absolute_screenshot),
        "missing_file": manifest_dir / "missing.json",
    }
    script = work_dir / "manifest-needs-approval-selftest.sh"
    script.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -u",
                function_block,
                "for manifest in \"$@\"; do",
                "  if manifest_needs_approval \"$manifest\"; then",
                "    echo \"$manifest:needs\"",
                "  else",
                "    echo \"$manifest:current\"",
                "  fi",
                "done",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        ["bash", str(script), *(str(path) for path in manifests.values())],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    observed = {}
    for line in completed.stdout.splitlines():
        if ":" not in line:
            continue
        path, status = line.rsplit(":", 1)
        observed[path] = status
    expected = {
        str(manifests["complete"]): "current",
        str(manifests["missing_approval"]): "needs",
        str(manifests["missing_identity"]): "needs",
        str(manifests["lax_policy"]): "needs",
        str(manifests["absolute_screenshot"]): "needs",
        str(manifests["missing_file"]): "needs",
    }
    return {
        "ok": completed.returncode == 0 and observed == expected,
        "returncode": completed.returncode,
        "output": completed.stdout,
        "observed": observed,
        "expected": expected,
    }


def final_exit_requires_final_statuses_case(runner: Path) -> dict[str, Any]:
    text = runner.read_text(encoding="utf-8")
    run_status_index = text.find("run_status=$?")
    final_audit_index = text.find("final_audit_status=$?")
    final_json_index = text.find("final_json_status=$?")
    final_integrity_include_run_status_index = text.find("--include ui-style-run-status.json")
    required = {
        "run_status_captured": "run_status=$?" in text,
        "final_audit_status_captured": "final_audit_status=$?" in text,
        "final_json_status_captured": "final_json_status=$?" in text,
        "final_json_runs_after_final_audit": (
            run_status_index != -1
            and final_audit_index != -1
            and final_json_index != -1
            and run_status_index < final_audit_index < final_json_index
        ),
        "final_json_includes_run_status": final_integrity_include_run_status_index > final_audit_index,
        "exit_requires_all_three": (
            '[[ "$run_status" == "0" && "$final_audit_status" == "0" && "$final_json_status" == "0" ]]'
            in text
        ),
        "final_audit_not_ignored": "ui-style-requirement-audit-final.log\" 2>&1 || true" not in text,
        "failure_message_names_all_three": (
            "ui-style-run-status.json, $results_dir/ui-style-requirement-audit.json, and $results_dir/json-artifact-integrity-final.json"
            in text
        ),
    }
    return {
        "ok": all(required.values()),
        "required": required,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runner",
        type=Path,
        default=Path(__file__).resolve().with_name("run_ui_test_baseline.sh"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/freecad-test-results/run-ui-test-baseline-selftest.json"),
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="freecad-run-ui-test-baseline-selftest-") as temp:
        scenarios = {
            "run_step_keeps_redirected_json_clean": run_step_output_case(Path(temp), args.runner),
            "startup_cleanup_preserves_approved_and_unrelated_artifacts": cleanup_scope_case(args.runner),
            "gui_interaction_driver_keeps_broad_exercise_conservative": gui_interaction_driver_safety_case(args.runner),
            "visual_approval_requires_reviewer_and_note": visual_approval_requires_metadata_case(args.runner),
            "visual_approval_docs_require_reviewer_and_note": visual_approval_docs_require_metadata_case(args.runner),
            "visual_approval_guard_runtime_behavior": approval_guard_runtime_case(Path(temp), args.runner),
            "visual_manifest_reapproval_detects_legacy_metadata": visual_manifest_reapproval_detection_case(Path(temp), args.runner),
            "final_exit_requires_final_statuses": final_exit_requires_final_statuses_case(args.runner),
        }

    failed = [name for name, result in scenarios.items() if not result["ok"]]
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
