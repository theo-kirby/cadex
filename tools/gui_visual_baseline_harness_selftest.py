#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Self-test visual baseline harness safeguards."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

import gui_visual_baseline_harness as harness


SCHEMA = "freecad-gui-visual-baseline-harness-selftest-v1"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def reset_output_dir_case(work_dir: Path) -> dict[str, Any]:
    output_dir = work_dir / "visual-output"
    stale_summary = output_dir / "summary.json"
    stale_capture = output_dir / "old-scene.png"
    stale_variant = output_dir / "large-font" / "summary.json"
    stale_variant.parent.mkdir(parents=True)
    stale_summary.write_text('{"result": "ok"}\n', encoding="utf-8")
    stale_capture.write_bytes(b"not a current screenshot")
    stale_variant.write_text('{"result": "ok"}\n', encoding="utf-8")

    harness.reset_output_dir(output_dir)
    remaining = sorted(str(path.relative_to(output_dir)) for path in output_dir.rglob("*"))
    return {
        "ok": output_dir.exists() and remaining == [],
        "remaining": remaining,
    }


def visual_preflight_case(config: dict[str, Any], variants: list[dict[str, Any]], expected_errors: list[str]) -> dict[str, Any]:
    result = harness.visual_preflight(config, variants)
    actual_errors = result.get("errors", [])
    return {
        "ok": actual_errors == expected_errors,
        "expected_errors": expected_errors,
        "actual_errors": actual_errors,
        "preflight": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/freecad-test-results/gui-visual-baseline-harness-selftest.json"),
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="freecad-visual-baseline-harness-selftest-") as temp:
        work_dir = Path(temp)
        scenarios = {
            "reset_output_dir_removes_stale_summary_screenshots_and_variants": reset_output_dir_case(work_dir),
            "preflight_allows_unique_scene_outputs_and_variants": visual_preflight_case(
                {
                    "scenes": [{"name": "part"}, {"name": "sketcher"}],
                    "dialog_scenes": [{"name": "preferences"}],
                    "task_scenes": [{"name": "partdesign-pad"}],
                    "workbenches": ["PartWorkbench", "SketcherWorkbench"],
                },
                [{"name": "default"}, {"name": "large-font"}],
                [],
            ),
            "preflight_rejects_duplicate_fixture_scene_names": visual_preflight_case(
                {"scenes": [{"name": "part"}, {"name": "part"}]},
                [],
                ["duplicate_fixture_scene_names", "fixture_scene_output_name_collisions"],
            ),
            "preflight_rejects_fixture_output_name_collisions": visual_preflight_case(
                {"scenes": [{"name": "part/detail"}, {"name": "part:detail"}]},
                [],
                ["fixture_scene_output_name_collisions"],
            ),
            "preflight_rejects_dialog_output_name_collisions": visual_preflight_case(
                {"dialog_scenes": [{"name": "file/open"}, {"name": "file:open"}]},
                [],
                ["dialog_scene_output_name_collisions"],
            ),
            "preflight_rejects_task_output_name_collisions": visual_preflight_case(
                {"task_scenes": [{"name": "pad/edit"}, {"name": "pad:edit"}]},
                [],
                ["task_scene_output_name_collisions"],
            ),
            "preflight_rejects_empty_scene_output_name": visual_preflight_case(
                {"scenes": [{"name": "!!!"}]},
                [],
                ["fixture_scene_output_name_collisions"],
            ),
            "preflight_rejects_duplicate_workbench_names": visual_preflight_case(
                {"workbenches": ["PartWorkbench", "PartWorkbench"]},
                [],
                ["duplicate_workbench_names"],
            ),
            "preflight_rejects_duplicate_variant_slugs": visual_preflight_case(
                {},
                [{"name": "Large Font"}, {"name": "large-font"}],
                ["duplicate_variant_slugs"],
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
