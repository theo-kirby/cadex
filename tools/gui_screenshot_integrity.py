#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Validate captured GUI screenshot artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageStat


SCHEMA = "freecad-gui-screenshot-integrity-v1"


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(base: Path, value: Any) -> Path:
    path = Path(str(value or ""))
    if path.is_absolute():
        return path
    return base / path


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def image_metrics(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        stat = ImageStat.Stat(rgb)
        extrema = rgb.getextrema()
        colors = rgb.resize((min(rgb.width, 128), min(rgb.height, 128))).getcolors(maxcolors=128 * 128)
        unique_color_count = len(colors or [])
        return {
            "size": [rgb.width, rgb.height],
            "mode": image.mode,
            "stddev_max": max(stat.stddev) if stat.stddev else 0,
            "extrema": [list(item) for item in extrema],
            "sample_unique_color_count": unique_color_count,
        }


def validate_scene(capture_dir: Path, scene: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    scene_name = str(scene.get("scene") or "<unnamed>")
    screenshot = resolve_path(capture_dir, scene.get("screenshot"))
    metadata_path = resolve_path(capture_dir, scene.get("metadata"))
    failures: list[str] = []
    metrics: dict[str, Any] = {}
    screenshot_within_capture = is_within(screenshot, capture_dir) if scene.get("screenshot") else True
    metadata_within_capture = is_within(metadata_path, capture_dir) if scene.get("metadata") else True
    metadata = read_json(metadata_path) if scene.get("metadata") and metadata_within_capture else None

    if not scene.get("screenshot"):
        failures.append("missing_screenshot_path")
    elif not screenshot_within_capture:
        failures.append("screenshot_path_outside_capture_dir")
    elif not screenshot.exists():
        failures.append("screenshot_file_missing")
    else:
        try:
            metrics = image_metrics(screenshot)
        except Exception as exc:
            failures.append("screenshot_unreadable")
            metrics = {"error": repr(exc)}

    size = metrics.get("size") or [0, 0]
    width = int(size[0] or 0)
    height = int(size[1] or 0)
    if width < args.min_width or height < args.min_height:
        failures.append("screenshot_too_small")

    if metrics and metrics.get("stddev_max", 0) < args.min_stddev:
        failures.append("screenshot_low_variance")
    if metrics and metrics.get("sample_unique_color_count", 0) < args.min_unique_colors:
        failures.append("screenshot_too_few_colors")

    if scene.get("metadata") and not metadata_within_capture:
        failures.append("metadata_path_outside_capture_dir")
    elif scene.get("metadata") and metadata is None:
        failures.append("metadata_file_missing_or_unreadable")
    if metadata:
        expected_size = metadata.get("screen_size")
        if expected_size and [width, height] != expected_size:
            failures.append("metadata_screen_size_mismatch")
        if not metadata.get("captured_widget"):
            failures.append("metadata_missing_captured_widget")
        if int(metadata.get("visible_widget_count") or 0) < args.min_visible_widgets:
            failures.append("visible_widget_count_too_low")

    return {
        "scene": scene_name,
        "screenshot": str(screenshot),
        "metadata": str(metadata_path) if scene.get("metadata") else None,
        "result": "ok" if not failures else "fail",
        "failures": failures,
        "metrics": metrics,
        "visible_widget_count": scene.get("visible_widget_count"),
    }


def validate_capture_dir(capture_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    summary_path = capture_dir / "summary.json"
    summary = read_json(summary_path)
    if summary is None:
        return {
            "capture_dir": str(capture_dir),
            "summary": str(summary_path),
            "result": "fail",
            "scene_count": 0,
            "failure_count": 1,
            "failures": [{"scene": "<summary>", "failures": ["summary_missing_or_unreadable"]}],
        }

    scenes = [
        scene for scene in summary.get("scenes", [])
        if isinstance(scene, dict) and not scene.get("error")
    ]
    scene_reports = [validate_scene(capture_dir, scene, args) for scene in scenes]
    screenshot_paths = [
        str(resolve_path(capture_dir, scene.get("screenshot")).resolve())
        for scene in scenes
        if scene.get("screenshot")
    ]
    metadata_paths = [
        str(resolve_path(capture_dir, scene.get("metadata")).resolve())
        for scene in scenes
        if scene.get("metadata")
    ]
    duplicate_screenshot_paths = sorted(
        path for path in set(screenshot_paths) if screenshot_paths.count(path) > 1
    )
    duplicate_metadata_paths = sorted(
        path for path in set(metadata_paths) if metadata_paths.count(path) > 1
    )
    summary_failures = []
    if summary.get("result") != "ok":
        summary_failures.append(
            {
                "scene": "<summary>",
                "failures": ["source_result_not_ok"],
                "source_result": summary.get("result"),
                "screenshot": None,
                "metadata": None,
            }
        )
    summary_failures.extend(
        {
            "scene": str(scene.get("scene") or "<unnamed>"),
            "failures": ["scene_error"],
            "error": scene.get("error"),
            "screenshot": scene.get("screenshot"),
            "metadata": scene.get("metadata"),
        }
        for scene in summary.get("scenes", [])
        if isinstance(scene, dict) and scene.get("error")
    )
    if duplicate_screenshot_paths:
        summary_failures.append(
            {
                "scene": "<summary>",
                "failures": ["duplicate_screenshot_paths"],
                "paths": duplicate_screenshot_paths,
                "screenshot": None,
                "metadata": None,
            }
        )
    if duplicate_metadata_paths:
        summary_failures.append(
            {
                "scene": "<summary>",
                "failures": ["duplicate_metadata_paths"],
                "paths": duplicate_metadata_paths,
                "screenshot": None,
                "metadata": None,
            }
        )
    failures = [
        {
            "scene": item["scene"],
            "failures": item["failures"],
            "screenshot": item["screenshot"],
            "metadata": item["metadata"],
        }
        for item in scene_reports
        if item["result"] != "ok"
    ]
    failures = summary_failures + failures
    return {
        "capture_dir": str(capture_dir),
        "summary": str(summary_path),
        "source_result": summary.get("result"),
        "result": "ok" if not failures else "fail",
        "scene_count": len(scene_reports),
        "failure_count": len(failures),
        "failures": failures,
    }


def build_report(capture_dirs: list[Path], args: argparse.Namespace) -> dict[str, Any]:
    captures = [validate_capture_dir(path, args) for path in capture_dirs]
    failures = [
        {
            "capture_dir": capture["capture_dir"],
            "failure_count": capture["failure_count"],
            "failures": capture["failures"][:10],
        }
        for capture in captures
        if capture["result"] != "ok"
    ]
    return {
        "schema": SCHEMA,
        "result": "ok" if not failures else "fail",
        "capture_count": len(captures),
        "scene_count": sum(capture.get("scene_count", 0) for capture in captures),
        "failure_count": sum(capture.get("failure_count", 0) for capture in captures),
        "thresholds": {
            "min_width": args.min_width,
            "min_height": args.min_height,
            "min_stddev": args.min_stddev,
            "min_unique_colors": args.min_unique_colors,
            "min_visible_widgets": args.min_visible_widgets,
        },
        "captures": captures,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-dir", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--min-width", type=int, default=64)
    parser.add_argument("--min-height", type=int, default=64)
    parser.add_argument("--min-stddev", type=float, default=1.0)
    parser.add_argument("--min-unique-colors", type=int, default=8)
    parser.add_argument("--min-visible-widgets", type=int, default=1)
    args = parser.parse_args()

    report = build_report(args.capture_dir, args)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if report["result"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
