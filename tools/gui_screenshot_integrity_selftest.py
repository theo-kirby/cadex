#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Self-test GUI screenshot integrity validation."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

import gui_screenshot_integrity as integrity


SCHEMA = "freecad-gui-screenshot-integrity-selftest-v1"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_capture(root: Path, image: Image.Image | None, scene: str = "scene-a") -> Path:
    capture_dir = root / scene
    capture_dir.mkdir()
    screenshot = capture_dir / f"{scene}.png"
    metadata = capture_dir / f"{scene}.json"
    if image is not None:
        image.save(screenshot)
    write_json(
        metadata,
        {
            "scene": scene,
            "screen_size": [image.width, image.height] if image is not None else [128, 128],
            "visible_widget_count": 3,
            "captured_widget": {"class": "QWidget", "geometry": {"local": [0, 0, 128, 128]}},
        },
    )
    write_json(
        capture_dir / "summary.json",
        {
            "result": "ok",
            "scene_count": 1,
            "scenes": [
                {
                    "scene": scene,
                    "screenshot": str(screenshot),
                    "metadata": str(metadata),
                    "visible_widget_count": 3,
                }
            ],
        },
    )
    return capture_dir


def update_metadata(capture_dir: Path, scene: str, updates: dict[str, Any]) -> None:
    metadata = capture_dir / f"{scene}.json"
    payload = json.loads(metadata.read_text(encoding="utf-8"))
    for key, value in updates.items():
        if value is None:
            payload.pop(key, None)
        else:
            payload[key] = value
    write_json(metadata, payload)


def update_summary(capture_dir: Path, updates: dict[str, Any]) -> None:
    summary_path = capture_dir / "summary.json"
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    for key, value in updates.items():
        if value is None:
            payload.pop(key, None)
        else:
            payload[key] = value
    write_json(summary_path, payload)


def patterned_image() -> Image.Image:
    image = Image.new("RGB", (128, 96), "white")
    draw = ImageDraw.Draw(image)
    for index in range(0, 128, 8):
        draw.rectangle([index, 0, index + 3, 95], fill=(index * 2 % 255, 80, 200))
    draw.rectangle([12, 16, 116, 80], outline="black", width=3)
    return image


def run_case(name: str, capture_dir: Path, expected: str) -> dict[str, Any]:
    args = argparse.Namespace(
        min_width=64,
        min_height=64,
        min_stddev=1.0,
        min_unique_colors=8,
        min_visible_widgets=1,
    )
    report = integrity.build_report([capture_dir], args)
    return {
        "name": name,
        "result": "pass" if report["result"] == expected else "fail",
        "expected": expected,
        "actual": report["result"],
        "failure_count": report["failure_count"],
        "failures": report["failures"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="freecad-screenshot-integrity-selftest-") as temp:
        root = Path(temp)
        valid = make_capture(root, patterned_image(), "valid")
        blank = make_capture(root, Image.new("RGB", (128, 96), "white"), "blank")
        missing = make_capture(root, None, "missing")
        tiny = make_capture(root, patterned_image().resize((16, 16)), "tiny")
        metadata_mismatch = make_capture(root, patterned_image(), "metadata-mismatch")
        update_metadata(metadata_mismatch, "metadata-mismatch", {"screen_size": [96, 128]})
        missing_widget = make_capture(root, patterned_image(), "missing-widget")
        update_metadata(missing_widget, "missing-widget", {"captured_widget": None})
        low_visible_widgets = make_capture(root, patterned_image(), "low-visible-widgets")
        update_metadata(low_visible_widgets, "low-visible-widgets", {"visible_widget_count": 0})
        failed_source = make_capture(root, patterned_image(), "failed-source")
        update_summary(failed_source, {"result": "process_failed"})
        scene_error = make_capture(root, patterned_image(), "scene-error")
        scene_error_summary = json.loads((scene_error / "summary.json").read_text(encoding="utf-8"))
        scene_error_summary["scenes"][0]["error"] = "synthetic scene capture failure"
        write_json(scene_error / "summary.json", scene_error_summary)
        outside_screenshot = make_capture(root, patterned_image(), "outside-screenshot")
        outside_image = root / "outside-image.png"
        patterned_image().save(outside_image)
        outside_screenshot_summary = json.loads((outside_screenshot / "summary.json").read_text(encoding="utf-8"))
        outside_screenshot_summary["scenes"][0]["screenshot"] = str(outside_image)
        write_json(outside_screenshot / "summary.json", outside_screenshot_summary)
        outside_metadata = make_capture(root, patterned_image(), "outside-metadata")
        outside_metadata_file = root / "outside-metadata.json"
        write_json(
            outside_metadata_file,
            {
                "scene": "outside-metadata",
                "screen_size": [128, 96],
                "visible_widget_count": 3,
                "captured_widget": {"class": "QWidget"},
            },
        )
        outside_metadata_summary = json.loads((outside_metadata / "summary.json").read_text(encoding="utf-8"))
        outside_metadata_summary["scenes"][0]["metadata"] = str(outside_metadata_file)
        write_json(outside_metadata / "summary.json", outside_metadata_summary)
        duplicate_paths = make_capture(root, patterned_image(), "duplicate-paths")
        duplicate_paths_summary = json.loads((duplicate_paths / "summary.json").read_text(encoding="utf-8"))
        duplicate_paths_summary["scenes"].append(
            {
                "scene": "duplicate-paths-second",
                "screenshot": duplicate_paths_summary["scenes"][0]["screenshot"],
                "metadata": duplicate_paths_summary["scenes"][0]["metadata"],
                "visible_widget_count": 3,
            }
        )
        duplicate_paths_summary["scene_count"] = 2
        write_json(duplicate_paths / "summary.json", duplicate_paths_summary)

        scenarios = [
            run_case("valid_capture_passes", valid, "ok"),
            run_case("blank_capture_fails", blank, "fail"),
            run_case("missing_screenshot_fails", missing, "fail"),
            run_case("too_small_capture_fails", tiny, "fail"),
            run_case("metadata_screen_size_mismatch_fails", metadata_mismatch, "fail"),
            run_case("missing_captured_widget_metadata_fails", missing_widget, "fail"),
            run_case("visible_widget_count_too_low_fails", low_visible_widgets, "fail"),
            run_case("failed_source_result_fails", failed_source, "fail"),
            run_case("scene_error_fails", scene_error, "fail"),
            run_case("outside_screenshot_path_fails", outside_screenshot, "fail"),
            run_case("outside_metadata_path_fails", outside_metadata, "fail"),
            run_case("duplicate_screenshot_and_metadata_paths_fail", duplicate_paths, "fail"),
        ]

    failed = [item for item in scenarios if item["result"] != "pass"]
    report = {
        "schema": SCHEMA,
        "result": "ok" if not failed else "fail",
        "scenario_count": len(scenarios),
        "scenario_names": [item["name"] for item in scenarios],
        "failed_scenarios": [item["name"] for item in failed],
        "scenarios": scenarios,
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if report["result"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
