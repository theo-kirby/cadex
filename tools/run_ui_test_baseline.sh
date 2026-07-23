#!/usr/bin/env bash
# SPDX-License-Identifier: LGPL-2.1-or-later
set -u

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${FREECAD_BASELINE_BUILD_DIR:-$repo_root/build/release}"
results_dir="${FREECAD_BASELINE_RESULTS_DIR:-/tmp/freecad-test-results}"
jobs="${FREECAD_BASELINE_JOBS:-8}"
registered_timeout="${FREECAD_BASELINE_REGISTERED_TIMEOUT:-900}"
registered_suite_timeout="${FREECAD_BASELINE_REGISTERED_SUITE_TIMEOUT:-180}"
registered_split_max_suites="${FREECAD_BASELINE_REGISTERED_SPLIT_MAX_SUITES:-0}"
survey_timeout="${FREECAD_BASELINE_SURVEY_TIMEOUT:-900}"
exercise_timeout="${FREECAD_BASELINE_EXERCISE_TIMEOUT:-1200}"
exercise_interactions="${FREECAD_BASELINE_EXERCISE_INTERACTIONS:-50}"
exercise_targets="${FREECAD_BASELINE_EXERCISE_TARGETS:-500}"
visual_timeout="${FREECAD_BASELINE_VISUAL_TIMEOUT:-600}"
fixture_visual_timeout="${FREECAD_BASELINE_FIXTURE_VISUAL_TIMEOUT:-900}"
matrix_visual_timeout="${FREECAD_BASELINE_MATRIX_VISUAL_TIMEOUT:-900}"
dialog_visual_timeout="${FREECAD_BASELINE_DIALOG_VISUAL_TIMEOUT:-300}"
task_visual_timeout="${FREECAD_BASELINE_TASK_VISUAL_TIMEOUT:-300}"
visual_width="${FREECAD_BASELINE_VISUAL_WIDTH:-1600}"
visual_height="${FREECAD_BASELINE_VISUAL_HEIGHT:-1000}"
fixture_visual_scenes="${FREECAD_BASELINE_FIXTURE_VISUAL_SCENES:-tools/gui_visual_scenes.default.json}"
dialog_visual_scenes="${FREECAD_BASELINE_DIALOG_VISUAL_SCENES:-tools/gui_visual_dialogs.default.json}"
task_visual_scenes="${FREECAD_BASELINE_TASK_VISUAL_SCENES:-tools/gui_visual_tasks.default.json}"
visual_variants="${FREECAD_BASELINE_VISUAL_VARIANTS:-tools/gui_visual_variants.default.json}"
layout_assertions="${FREECAD_BASELINE_LAYOUT_ASSERTIONS:-tools/gui_layout_assertions.default.json}"
approve_missing="${FREECAD_BASELINE_APPROVE_MISSING:-0}"
approval_reviewer="${FREECAD_BASELINE_APPROVER:-}"
approval_note="${FREECAD_BASELINE_APPROVAL_NOTE:-}"

mkdir -p "$results_dir"
cd "$repo_root" || exit 2

if [[ "$approve_missing" == "1" ]]; then
    if [[ -z "$approval_reviewer" || -z "$approval_note" ]]; then
        echo "FREECAD_BASELINE_APPROVE_MISSING=1 requires FREECAD_BASELINE_APPROVER and FREECAD_BASELINE_APPROVAL_NOTE" >&2
        exit 2
    fi
fi

cleanup_step_artifacts() {
    local step
    for step in "$@"; do
        rm -f \
            "$results_dir/$step.command" \
            "$results_dir/$step.run_id" \
            "$results_dir/$step.status" \
            "$results_dir/$step.log" \
            "$results_dir/$step.json"
    done
}

cleanup_step_artifacts \
    ctest-N \
    ctest \
    freecad-startup-smoke \
    freecad-dependency-smoke \
    dependency-smoke-selftest \
    gui-layout-assertion-smoke \
    freecad-t0 \
    freecad-registered-split \
    freecad-registered-issue-classification \
    registered-classification-selftest \
    registered-harness-selftest \
    gui-visual-baseline-harness-selftest \
    gui-survey-venv \
    gui-exercise-venv \
    gui-workflows-venv \
    gui-visual-venv \
    gui-visual-fixtures \
    gui-visual-matrix \
    gui-visual-dialogs \
    gui-visual-dialogs-native \
    gui-visual-tasks \
    gui-visual-approve \
    gui-visual-regression-check \
    gui-visual-fixtures-approve \
    gui-visual-fixtures-regression-check \
    gui-visual-matrix-approve \
    gui-visual-matrix-regression-check \
    gui-visual-dialogs-approve \
    gui-visual-dialogs-regression-check \
    gui-visual-tasks-approve \
    gui-visual-tasks-regression-check \
    gui-screenshot-integrity \
    gui-screenshot-integrity-selftest \
    gui-visual-regression-selftest \
    baseline-summary \
    ctest-not-run-approve \
    ctest-not-run-check \
    ctest-inventory-selftest \
    baseline-summary-final \
    manual-smoke-selftest \
    ui-style-coverage-selftest \
    gui-workflow-coverage-selftest \
    gui-layout-assertion-coverage-selftest \
    ui-style-requirement-audit-selftest \
    ui-style-run-status-selftest \
    ui-style-gate-selftest \
    artifact-provenance-selftest \
    run-ui-test-baseline-selftest \
    json-artifact-integrity-selftest \
    json-artifact-integrity \
    baseline-summary-selftests \
    ui-style-gate \
    ui-style-requirement-audit \
    json-artifact-integrity-final

rm -f \
    "$results_dir/baseline-summary.json" \
    "$results_dir/ui-style-gate.json" \
    "$results_dir/ui-style-requirement-audit.json" \
    "$results_dir/ui-style-run-status.json" \
    "$results_dir/freecad-dependency-smoke-selftest.json" \
    "$results_dir/freecad-registered-harness-selftest.json" \
    "$results_dir/run-ui-test-baseline.log"

rm -rf \
    "$results_dir/freecad-registered-split" \
    "$results_dir/gui-survey-venv" \
    "$results_dir/gui-exercise-venv" \
    "$results_dir/gui-workflows-venv" \
    "$results_dir/gui-visual-venv" \
    "$results_dir/gui-visual-fixtures" \
    "$results_dir/gui-visual-matrix" \
    "$results_dir/gui-visual-dialogs" \
    "$results_dir/gui-visual-dialogs-native" \
    "$results_dir/gui-visual-tasks" \
    "$results_dir/gui-visual-diffs" \
    "$results_dir/gui-visual-fixtures-diffs" \
    "$results_dir/gui-visual-matrix-diffs" \
    "$results_dir/gui-visual-dialogs-diffs" \
    "$results_dir/gui-visual-tasks-diffs"

run_id="$(date -u +"%Y%m%dT%H%M%SZ")-$$"
echo "$run_id" > "$results_dir/run.id"
runner_log="$results_dir/run-ui-test-baseline.log"
: > "$runner_log"

run_step() {
    local name="$1"
    shift
    echo "== $name ==" >> "$runner_log"
    echo "$*" > "$results_dir/$name.command"
    "$@"
    local status=$?
    echo "$run_id" > "$results_dir/$name.run_id"
    echo "$status" > "$results_dir/$name.status"
    if [[ "$status" -ne 0 ]]; then
        echo "$name exited with status $status" >> "$runner_log"
    fi
    return 0
}

step_status() {
    local name="$1"
    local path="$results_dir/$name.status"
    if [[ -f "$path" ]]; then
        tr -d '[:space:]' < "$path"
    else
        echo "missing"
    fi
}

manifest_needs_approval() {
    local manifest="$1"
    python3 - "$manifest" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
if not path.exists():
    raise SystemExit(0)
try:
    manifest = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(0)
if manifest.get("format") != 2:
    raise SystemExit(0)
approval = manifest.get("approval")
if not isinstance(approval, dict):
    raise SystemExit(0)
placeholder = {"todo", "tbd", "n/a", "none", "placeholder"}
for field in ("reviewer", "note", "approved_utc", "source_capture_dir"):
    value = str(approval.get(field) or "").strip()
    if not value or value.lower() in placeholder:
        raise SystemExit(0)
policy = manifest.get("policy") or {}
try:
    max_changed_ratio = float(policy.get("max_changed_ratio"))
    max_rms = float(policy.get("max_rms"))
except (TypeError, ValueError):
    raise SystemExit(0)
if max_changed_ratio > 0.03 or max_rms > 8.0:
    raise SystemExit(0)
if policy.get("new_findings_fail") is not True:
    raise SystemExit(0)
if policy.get("baseline_images_are_portable") is not True:
    raise SystemExit(0)
scenes = manifest.get("scenes") or {}
if not scenes:
    raise SystemExit(0)
for scene in scenes.values():
    screenshot = pathlib.Path(str(scene.get("screenshot", "")))
    if not str(screenshot) or screenshot.is_absolute():
        raise SystemExit(0)
    if not scene.get("scene_context_fingerprint"):
        raise SystemExit(0)
    if not scene.get("scene_context_identity"):
        raise SystemExit(0)
raise SystemExit(1)
PY
}

ctest_inventory_manifest_needs_approval() {
    local manifest="$1"
    [[ ! -f "$manifest" ]]
}

run_step ctest-N \
    ctest --test-dir "$build_dir" -N \
    >"$results_dir/ctest-N.log" 2>&1

run_step ctest \
    ctest --test-dir "$build_dir" --output-on-failure -j"$jobs" \
    >"$results_dir/ctest.log" 2>&1

run_step freecad-startup-smoke \
    tools/freecad_startup_smoke.py tools/freecadcmd_venv.sh \
        --output "$results_dir/freecad-startup-smoke.json" \
    >"$results_dir/freecad-startup-smoke.log" 2>&1

run_step freecad-dependency-smoke \
    tools/freecad_dependency_smoke.py \
        --config tools/optional_dependencies.default.json \
        --output "$results_dir/freecad-dependency-smoke.json" \
    >"$results_dir/freecad-dependency-smoke.log" 2>&1

run_step dependency-smoke-selftest \
    python3 tools/freecad_dependency_smoke_selftest.py \
        --output "$results_dir/freecad-dependency-smoke-selftest.json" \
    >"$results_dir/freecad-dependency-smoke-selftest.log" 2>&1

run_step gui-layout-assertion-smoke \
    tools/gui_layout_assertion_smoke.py tools/freecad_venv.sh \
        --required-config "$layout_assertions" \
        --output "$results_dir/gui-layout-assertion-smoke.json" \
    >"$results_dir/gui-layout-assertion-smoke.log" 2>&1

run_step freecad-t0 \
    timeout "${registered_timeout}s" xvfb-run -a tools/freecad_venv.sh -t 0 \
    >"$results_dir/freecad-t0.log" 2>&1

registered_split_args=(
    tools/freecad_registered_test_harness.py
    tools/freecad_venv.sh
    --output-dir "$results_dir/freecad-registered-split"
    --timeout-per-suite "$registered_suite_timeout"
)
if [[ "$registered_split_max_suites" != "0" ]]; then
    registered_split_args+=(--max-suites "$registered_split_max_suites")
fi

run_step freecad-registered-split \
    python3 "${registered_split_args[@]}" \
    >"$results_dir/freecad-registered-split.log" 2>&1

run_step freecad-registered-issue-classification \
    python3 tools/validate_registered_issue_classifications.py \
        --summary "$results_dir/freecad-registered-split/summary.json" \
        --classifications tools/freecad_registered_issue_classifications.default.json \
        --output "$results_dir/freecad-registered-issue-classification.json" \
    >"$results_dir/freecad-registered-issue-classification.log" 2>&1

run_step registered-classification-selftest \
    tools/registered_classification_selftest.py \
        --output "$results_dir/registered-classification-selftest.json" \
    >"$results_dir/registered-classification-selftest.log" 2>&1

run_step registered-harness-selftest \
    python3 tools/freecad_registered_harness_selftest.py \
        --output "$results_dir/freecad-registered-harness-selftest.json" \
    >"$results_dir/freecad-registered-harness-selftest.log" 2>&1

run_step gui-visual-baseline-harness-selftest \
    python3 tools/gui_visual_baseline_harness_selftest.py \
        --output "$results_dir/gui-visual-baseline-harness-selftest.json" \
    >"$results_dir/gui-visual-baseline-harness-selftest.log" 2>&1

run_step gui-survey-venv \
    tools/gui_interaction_harness.py tools/freecad_venv.sh \
        --output-dir "$results_dir/gui-survey-venv" \
        --mode survey \
        --max-workbenches 0 \
        --timeout "$survey_timeout" \
    >"$results_dir/gui-survey-venv.log" 2>&1

run_step gui-exercise-venv \
    tools/gui_interaction_harness.py tools/freecad_venv.sh \
        --output-dir "$results_dir/gui-exercise-venv" \
        --mode exercise \
        --max-workbenches 0 \
        --max-interactions "$exercise_interactions" \
        --max-targets "$exercise_targets" \
        --timeout "$exercise_timeout" \
    >"$results_dir/gui-exercise-venv.log" 2>&1

run_step gui-workflows-venv \
    tools/gui_interaction_harness.py tools/freecad_venv.sh \
        --output-dir "$results_dir/gui-workflows-venv" \
        --mode workflows \
        --timeout "$exercise_timeout" \
    >"$results_dir/gui-workflows-venv.log" 2>&1

run_step gui-visual-venv \
    tools/gui_visual_baseline_harness.py tools/freecad_venv.sh \
        --output-dir "$results_dir/gui-visual-venv" \
        --max-workbenches 0 \
        --window-size "$visual_width" "$visual_height" \
        --timeout "$visual_timeout" \
    >"$results_dir/gui-visual-venv.log" 2>&1

run_step gui-visual-fixtures \
    tools/gui_visual_baseline_harness.py tools/freecad_venv.sh \
        --output-dir "$results_dir/gui-visual-fixtures" \
        --scene-config "$fixture_visual_scenes" \
        --no-workbenches \
        --window-size "$visual_width" "$visual_height" \
        --timeout "$fixture_visual_timeout" \
    >"$results_dir/gui-visual-fixtures.log" 2>&1

run_step gui-visual-matrix \
    tools/gui_visual_baseline_harness.py tools/freecad_venv.sh \
        --output-dir "$results_dir/gui-visual-matrix" \
        --scene-config "$fixture_visual_scenes" \
        --dialog-config "$dialog_visual_scenes" \
        --task-config "$task_visual_scenes" \
        --variant-config "$visual_variants" \
        --max-workbenches 0 \
        --window-size "$visual_width" "$visual_height" \
        --timeout "$matrix_visual_timeout" \
    >"$results_dir/gui-visual-matrix.log" 2>&1

run_step gui-visual-dialogs \
    tools/gui_visual_baseline_harness.py tools/freecad_venv.sh \
        --output-dir "$results_dir/gui-visual-dialogs" \
        --dialog-config "$dialog_visual_scenes" \
        --no-workbenches \
        --window-size "$visual_width" "$visual_height" \
        --timeout "$dialog_visual_timeout" \
    >"$results_dir/gui-visual-dialogs.log" 2>&1

run_step gui-visual-dialogs-native \
    tools/gui_visual_baseline_harness.py "$build_dir/bin/FreeCAD" \
        --output-dir "$results_dir/gui-visual-dialogs-native" \
        --dialog-config "$dialog_visual_scenes" \
        --no-workbenches \
        --window-size "$visual_width" "$visual_height" \
        --timeout "$dialog_visual_timeout" \
    >"$results_dir/gui-visual-dialogs-native.log" 2>&1

run_step gui-visual-tasks \
    tools/gui_visual_baseline_harness.py tools/freecad_venv.sh \
        --output-dir "$results_dir/gui-visual-tasks" \
        --task-config "$task_visual_scenes" \
        --no-workbenches \
        --window-size "$visual_width" "$visual_height" \
        --timeout "$task_visual_timeout" \
    >"$results_dir/gui-visual-tasks.log" 2>&1

if [[ "$approve_missing" == "1" ]] && manifest_needs_approval "$results_dir/gui-visual-approved.json"; then
    run_step gui-visual-approve \
        tools/gui_visual_regression.py approve \
            --capture-dir "$results_dir/gui-visual-venv" \
            --manifest "$results_dir/gui-visual-approved.json" \
            --reviewer "$approval_reviewer" \
            --approval-note "$approval_note" \
        >"$results_dir/gui-visual-approve.log" 2>&1
fi

run_step gui-visual-regression-check \
    tools/gui_visual_regression.py check \
        --capture-dir "$results_dir/gui-visual-venv" \
        --manifest "$results_dir/gui-visual-approved.json" \
        --diff-dir "$results_dir/gui-visual-diffs" \
    >"$results_dir/gui-visual-regression-check.json" 2>&1

if [[ "$approve_missing" == "1" ]] && manifest_needs_approval "$results_dir/gui-visual-fixtures-approved.json"; then
    run_step gui-visual-fixtures-approve \
        tools/gui_visual_regression.py approve \
            --capture-dir "$results_dir/gui-visual-fixtures" \
            --manifest "$results_dir/gui-visual-fixtures-approved.json" \
            --reviewer "$approval_reviewer" \
            --approval-note "$approval_note" \
        >"$results_dir/gui-visual-fixtures-approve.log" 2>&1
fi

run_step gui-visual-fixtures-regression-check \
    tools/gui_visual_regression.py check \
        --capture-dir "$results_dir/gui-visual-fixtures" \
        --manifest "$results_dir/gui-visual-fixtures-approved.json" \
        --diff-dir "$results_dir/gui-visual-fixtures-diffs" \
    >"$results_dir/gui-visual-fixtures-regression-check.json" 2>&1

if [[ "$approve_missing" == "1" ]] && manifest_needs_approval "$results_dir/gui-visual-matrix-approved.json"; then
    run_step gui-visual-matrix-approve \
        tools/gui_visual_regression.py approve \
            --capture-dir "$results_dir/gui-visual-matrix" \
            --manifest "$results_dir/gui-visual-matrix-approved.json" \
            --reviewer "$approval_reviewer" \
            --approval-note "$approval_note" \
        >"$results_dir/gui-visual-matrix-approve.log" 2>&1
fi

run_step gui-visual-matrix-regression-check \
    tools/gui_visual_regression.py check \
        --capture-dir "$results_dir/gui-visual-matrix" \
        --manifest "$results_dir/gui-visual-matrix-approved.json" \
        --diff-dir "$results_dir/gui-visual-matrix-diffs" \
    >"$results_dir/gui-visual-matrix-regression-check.json" 2>&1

if [[ "$approve_missing" == "1" ]] && manifest_needs_approval "$results_dir/gui-visual-dialogs-approved.json"; then
    run_step gui-visual-dialogs-approve \
        tools/gui_visual_regression.py approve \
            --capture-dir "$results_dir/gui-visual-dialogs" \
            --manifest "$results_dir/gui-visual-dialogs-approved.json" \
            --reviewer "$approval_reviewer" \
            --approval-note "$approval_note" \
        >"$results_dir/gui-visual-dialogs-approve.log" 2>&1
fi

run_step gui-visual-dialogs-regression-check \
    tools/gui_visual_regression.py check \
        --capture-dir "$results_dir/gui-visual-dialogs" \
        --manifest "$results_dir/gui-visual-dialogs-approved.json" \
        --diff-dir "$results_dir/gui-visual-dialogs-diffs" \
    >"$results_dir/gui-visual-dialogs-regression-check.json" 2>&1

if [[ "$approve_missing" == "1" ]] && manifest_needs_approval "$results_dir/gui-visual-tasks-approved.json"; then
    run_step gui-visual-tasks-approve \
        tools/gui_visual_regression.py approve \
            --capture-dir "$results_dir/gui-visual-tasks" \
            --manifest "$results_dir/gui-visual-tasks-approved.json" \
            --reviewer "$approval_reviewer" \
            --approval-note "$approval_note" \
        >"$results_dir/gui-visual-tasks-approve.log" 2>&1
fi

run_step gui-visual-tasks-regression-check \
    tools/gui_visual_regression.py check \
        --capture-dir "$results_dir/gui-visual-tasks" \
        --manifest "$results_dir/gui-visual-tasks-approved.json" \
        --diff-dir "$results_dir/gui-visual-tasks-diffs" \
    >"$results_dir/gui-visual-tasks-regression-check.json" 2>&1

run_step gui-screenshot-integrity \
    tools/gui_screenshot_integrity.py \
        --capture-dir "$results_dir/gui-visual-venv" \
        --capture-dir "$results_dir/gui-visual-fixtures" \
        --capture-dir "$results_dir/gui-visual-matrix" \
        --capture-dir "$results_dir/gui-visual-dialogs" \
        --capture-dir "$results_dir/gui-visual-tasks" \
        --output "$results_dir/gui-screenshot-integrity.json" \
    >"$results_dir/gui-screenshot-integrity.log" 2>&1

run_step gui-screenshot-integrity-selftest \
    tools/gui_screenshot_integrity_selftest.py \
        --output "$results_dir/gui-screenshot-integrity-selftest.json" \
    >"$results_dir/gui-screenshot-integrity-selftest.log" 2>&1

run_step gui-visual-regression-selftest \
    tools/gui_visual_regression_selftest.py \
        --output "$results_dir/gui-visual-regression-selftest.json" \
    >"$results_dir/gui-visual-regression-selftest.log" 2>&1

run_step baseline-summary \
    tools/collect_ui_test_baseline.py \
        --results-dir "$results_dir" \
        --build-dir "$build_dir" \
        --output "$results_dir/baseline-summary.json" \
    >"$results_dir/baseline-summary.log" 2>&1

if [[ "$approve_missing" == "1" ]] && ctest_inventory_manifest_needs_approval "$results_dir/ctest-not-run-approved.json"; then
    run_step ctest-not-run-approve \
        tools/ctest_inventory_regression.py approve \
            --summary "$results_dir/baseline-summary.json" \
            --manifest "$results_dir/ctest-not-run-approved.json" \
        >"$results_dir/ctest-not-run-approve.log" 2>&1
fi

run_step ctest-not-run-check \
    tools/ctest_inventory_regression.py check \
        --summary "$results_dir/baseline-summary.json" \
        --manifest "$results_dir/ctest-not-run-approved.json" \
    >"$results_dir/ctest-not-run-check.json" 2>&1

run_step ctest-inventory-selftest \
    python3 tools/ctest_inventory_selftest.py \
        --output "$results_dir/ctest-inventory-selftest.json" \
    >"$results_dir/ctest-inventory-selftest.log" 2>&1

run_step baseline-summary-final \
    tools/collect_ui_test_baseline.py \
        --results-dir "$results_dir" \
        --build-dir "$build_dir" \
        --output "$results_dir/baseline-summary.json" \
    >"$results_dir/baseline-summary-final.log" 2>&1

run_step manual-smoke-selftest \
    python3 tools/manual_smoke_selftest.py \
        --summary "$results_dir/baseline-summary.json" \
        --output "$results_dir/manual-smoke-selftest.json" \
    >"$results_dir/manual-smoke-selftest.log" 2>&1

run_step ui-style-coverage-selftest \
    python3 tools/ui_style_coverage_selftest.py \
        --summary "$results_dir/baseline-summary.json" \
        --results-dir "$results_dir" \
        --output "$results_dir/ui-style-coverage-selftest.json" \
    >"$results_dir/ui-style-coverage-selftest.log" 2>&1

run_step gui-workflow-coverage-selftest \
    python3 tools/gui_workflow_coverage_selftest.py \
        --summary "$results_dir/baseline-summary.json" \
        --results-dir "$results_dir" \
        --output "$results_dir/gui-workflow-coverage-selftest.json" \
    >"$results_dir/gui-workflow-coverage-selftest.log" 2>&1

run_step gui-layout-assertion-coverage-selftest \
    python3 tools/gui_layout_assertion_coverage_selftest.py \
        --summary "$results_dir/baseline-summary.json" \
        --results-dir "$results_dir" \
        --output "$results_dir/gui-layout-assertion-coverage-selftest.json" \
    >"$results_dir/gui-layout-assertion-coverage-selftest.log" 2>&1

run_step ui-style-requirement-audit-selftest \
    python3 tools/ui_style_requirement_audit_selftest.py \
        --output "$results_dir/ui-style-requirement-audit-selftest.json" \
    >"$results_dir/ui-style-requirement-audit-selftest.log" 2>&1

run_step ui-style-run-status-selftest \
    python3 tools/ui_style_run_status_selftest.py \
        --output "$results_dir/ui-style-run-status-selftest.json" \
    >"$results_dir/ui-style-run-status-selftest.log" 2>&1

run_step ui-style-gate-selftest \
    python3 tools/ui_style_gate_selftest.py \
        --coverage-config tools/ui_style_coverage.default.json \
        --output "$results_dir/ui-style-gate-selftest.json" \
    >"$results_dir/ui-style-gate-selftest.log" 2>&1

run_step artifact-provenance-selftest \
    python3 tools/artifact_provenance_selftest.py \
        --output "$results_dir/artifact-provenance-selftest.json" \
    >"$results_dir/artifact-provenance-selftest.log" 2>&1

run_step run-ui-test-baseline-selftest \
    python3 tools/run_ui_test_baseline_selftest.py \
        --runner tools/run_ui_test_baseline.sh \
        --output "$results_dir/run-ui-test-baseline-selftest.json" \
    >"$results_dir/run-ui-test-baseline-selftest.log" 2>&1

run_step json-artifact-integrity-selftest \
    python3 tools/json_artifact_integrity_selftest.py \
        --output "$results_dir/json-artifact-integrity-selftest.json" \
    >"$results_dir/json-artifact-integrity-selftest.log" 2>&1

json_artifact_integrity_args=(
    tools/json_artifact_integrity.py
    --results-dir "$results_dir"
    --output "$results_dir/json-artifact-integrity.json"
    --include freecad-startup-smoke.json
    --include freecad-dependency-smoke.json
    --include freecad-dependency-smoke-selftest.json
    --include gui-layout-assertion-smoke.json
    --include freecad-registered-split/summary.json
    --include freecad-registered-issue-classification.json
    --include registered-classification-selftest.json
    --include freecad-registered-harness-selftest.json
    --include gui-visual-baseline-harness-selftest.json
    --include gui-survey-venv/summary.json
    --include gui-exercise-venv/summary.json
    --include gui-workflows-venv/summary.json
    --include gui-visual-venv/summary.json
    --include gui-visual-fixtures/summary.json
    --include gui-visual-matrix/summary.json
    --include gui-visual-dialogs/summary.json
    --include gui-visual-dialogs-native/summary.json
    --include gui-visual-tasks/summary.json
    --include gui-visual-regression-check.json
    --include gui-visual-fixtures-regression-check.json
    --include gui-visual-matrix-regression-check.json
    --include gui-visual-dialogs-regression-check.json
    --include gui-visual-tasks-regression-check.json
    --include gui-screenshot-integrity.json
    --include gui-screenshot-integrity-selftest.json
    --include gui-visual-regression-selftest.json
    --include ctest-not-run-check.json
    --include ctest-inventory-selftest.json
    --include manual-smoke-selftest.json
    --include ui-style-coverage-selftest.json
    --include gui-workflow-coverage-selftest.json
    --include gui-layout-assertion-coverage-selftest.json
    --include ui-style-requirement-audit-selftest.json
    --include ui-style-run-status-selftest.json
    --include ui-style-gate-selftest.json
    --include artifact-provenance-selftest.json
    --include run-ui-test-baseline-selftest.json
    --include json-artifact-integrity-selftest.json
)

run_step json-artifact-integrity \
    python3 "${json_artifact_integrity_args[@]}" \
    >"$results_dir/json-artifact-integrity.log" 2>&1

run_step baseline-summary-selftests \
    tools/collect_ui_test_baseline.py \
        --results-dir "$results_dir" \
        --build-dir "$build_dir" \
        --output "$results_dir/baseline-summary.json" \
    >"$results_dir/baseline-summary-selftests.log" 2>&1

run_step ui-style-gate \
    python3 tools/evaluate_ui_style_gate.py \
        --summary "$results_dir/baseline-summary.json" \
        --repo-root "$repo_root" \
        --results-dir "$results_dir" \
        --coverage-config tools/ui_style_coverage.default.json \
        --output "$results_dir/ui-style-gate.json" \
    >"$results_dir/ui-style-gate.log" 2>&1

run_step ui-style-requirement-audit \
    python3 tools/ui_style_requirement_audit.py \
        --summary "$results_dir/baseline-summary.json" \
        --gate "$results_dir/ui-style-gate.json" \
        --coverage-selftest "$results_dir/ui-style-coverage-selftest.json" \
        --gate-selftest "$results_dir/ui-style-gate-selftest.json" \
        --requirement-audit-selftest "$results_dir/ui-style-requirement-audit-selftest.json" \
        --output "$results_dir/ui-style-requirement-audit.json" \
    >"$results_dir/ui-style-requirement-audit.log" 2>&1

echo "Baseline artifacts written to $results_dir"
echo "Summary: $results_dir/baseline-summary.json"
echo "Gate verdict: $results_dir/ui-style-gate.json"
echo "Gate self-test: $results_dir/ui-style-gate-selftest.json"
echo "Registered harness self-test: $results_dir/freecad-registered-harness-selftest.json"
echo "Visual baseline harness self-test: $results_dir/gui-visual-baseline-harness-selftest.json"
echo "CTest inventory self-test: $results_dir/ctest-inventory-selftest.json"
echo "Dependency smoke self-test: $results_dir/freecad-dependency-smoke-selftest.json"
echo "Coverage self-test: $results_dir/ui-style-coverage-selftest.json"
echo "Workflow coverage self-test: $results_dir/gui-workflow-coverage-selftest.json"
echo "Layout assertion coverage self-test: $results_dir/gui-layout-assertion-coverage-selftest.json"
echo "Screenshot integrity: $results_dir/gui-screenshot-integrity.json"
echo "Native dialog visual summary: $results_dir/gui-visual-dialogs-native/summary.json"
echo "Screenshot integrity self-test: $results_dir/gui-screenshot-integrity-selftest.json"
echo "Manual smoke self-test: $results_dir/manual-smoke-selftest.json"
echo "Requirement audit self-test: $results_dir/ui-style-requirement-audit-selftest.json"
echo "Run status self-test: $results_dir/ui-style-run-status-selftest.json"
echo "Runner self-test: $results_dir/run-ui-test-baseline-selftest.json"
echo "JSON artifact integrity: $results_dir/json-artifact-integrity.json"
echo "Final JSON artifact integrity: $results_dir/json-artifact-integrity-final.json"
echo "JSON artifact integrity self-test: $results_dir/json-artifact-integrity-selftest.json"
echo "Requirement audit: $results_dir/ui-style-requirement-audit.json"
echo "Run status: $results_dir/ui-style-run-status.json"

python3 tools/ui_style_run_status.py \
    --results-dir "$results_dir" \
    --output "$results_dir/ui-style-run-status.json"
run_status=$?

python3 tools/ui_style_requirement_audit.py \
    --summary "$results_dir/baseline-summary.json" \
    --gate "$results_dir/ui-style-gate.json" \
    --coverage-selftest "$results_dir/ui-style-coverage-selftest.json" \
    --gate-selftest "$results_dir/ui-style-gate-selftest.json" \
    --requirement-audit-selftest "$results_dir/ui-style-requirement-audit-selftest.json" \
    --run-status "$results_dir/ui-style-run-status.json" \
    --run-status-selftest "$results_dir/ui-style-run-status-selftest.json" \
    --output "$results_dir/ui-style-requirement-audit.json" \
    >"$results_dir/ui-style-requirement-audit-final.log" 2>&1
final_audit_status=$?

json_artifact_integrity_final_args=(
    tools/json_artifact_integrity.py
    --results-dir "$results_dir"
    --output "$results_dir/json-artifact-integrity-final.json"
    --include baseline-summary.json
    --include ui-style-gate.json
    --include ui-style-run-status.json
    --include ui-style-requirement-audit.json
    --include json-artifact-integrity.json
    --include artifact-provenance-selftest.json
    --include run-ui-test-baseline-selftest.json
    --include json-artifact-integrity-selftest.json
)

python3 "${json_artifact_integrity_final_args[@]}" \
    >"$results_dir/json-artifact-integrity-final.log" 2>&1
final_json_status=$?

if [[ "$run_status" == "0" && "$final_audit_status" == "0" && "$final_json_status" == "0" ]]; then
    echo "UI/style readiness gate passed"
    exit 0
fi

echo "UI/style readiness gate failed; see $results_dir/ui-style-run-status.json, $results_dir/ui-style-requirement-audit.json, and $results_dir/json-artifact-integrity-final.json" >&2
exit 1
