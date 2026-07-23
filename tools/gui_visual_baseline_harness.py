#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Launch FreeCAD and capture deterministic GUI visual baseline artifacts."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path


def find_freecad(value: str | None) -> str:
    if not value:
        return "FreeCAD"
    path = Path(value)
    if path.is_dir():
        candidate = path / "bin" / "FreeCAD"
        if candidate.exists():
            return str(candidate)
    return str(path)


def build_command(args, driver: Path) -> list[str]:
    command = [find_freecad(args.freecad), str(driver)]
    if args.no_xvfb or os.environ.get("DISPLAY"):
        return command
    xvfb = shutil.which("xvfb-run")
    if xvfb:
        return [xvfb, "-a", "-s", f"-screen 0 {args.window_size[0]}x{args.window_size[1]}x24", *command]
    return command


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def reset_output_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_preference_pack(variant: dict, repo_root: Path, user_home: Path) -> None:
    pack = variant.get("preference_pack")
    if not pack:
        return
    pack_path = Path(pack)
    if not pack_path.is_absolute():
        pack_path = repo_root / pack_path
    if not pack_path.exists():
        raise FileNotFoundError(pack_path)
    shutil.copyfile(pack_path, user_home / "user.cfg")


def load_allowlist(path: Path | None) -> list[re.Pattern[str]]:
    if not path:
        return []
    patterns = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(re.compile(line, re.MULTILINE | re.DOTALL))
    return patterns


def traceback_blocks(text: str) -> list[str]:
    pattern = re.compile(
        r"^Traceback \(most recent call last\):\n"
        r"(?:^[ \t].*\n)+"
        r"^(?:<class '[^']+'>: .+|[A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception|Warning): .+)",
        re.MULTILINE,
    )
    return [match.group(0).strip() for match in pattern.finditer(text)]


def classify_tracebacks(text: str, allowlist: list[re.Pattern[str]]) -> dict:
    blocks = traceback_blocks(text)
    unallowed = [
        block
        for block in blocks
        if not any(pattern.search(block) for pattern in allowlist)
    ]
    return {
        "traceback_count": len(blocks),
        "unallowed_traceback_count": len(unallowed),
        "unallowed_traceback_examples": unallowed[:5],
    }


def update_process_summary(output_dir: Path, returncode: int, log_path: Path, tracebacks: dict) -> None:
    summary_path = output_dir / "summary.json"
    if summary_path.exists():
        summary = load_json(summary_path)
    else:
        summary = {"result": "missing_summary", "scenes": []}

    summary["process_returncode"] = returncode
    summary["process_log"] = str(log_path)
    summary.update(tracebacks)
    failed_scenes = [
        {"scene": scene.get("scene"), "error": scene.get("error")}
        for scene in summary.get("scenes", [])
        if isinstance(scene, dict) and scene.get("error")
    ]
    summary["failed_scene_count"] = len(failed_scenes)
    summary["failed_scenes"] = failed_scenes
    if returncode != 0 or tracebacks["unallowed_traceback_count"]:
        summary["result"] = "process_failed"
    elif failed_scenes:
        summary["result"] = "scene_failed"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def variant_slug(variant: dict, index: int) -> str:
    raw = variant.get("name") or f"variant-{index:02d}"
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in raw).strip("-")
    return cleaned or f"variant-{index:02d}"


def scene_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in value).strip("-")


def duplicate_values(values: list[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)


def duplicate_output_names(prefix: str, scenes: list[dict], fallback_prefix: str) -> dict[str, list[str]]:
    by_output: dict[str, list[str]] = {}
    for index, scene in enumerate(scenes, start=1):
        raw_name = str(scene.get("name") or f"{fallback_prefix}-{index:03d}")
        output_name = f"{prefix}-{scene_slug(raw_name)}"
        by_output.setdefault(output_name, []).append(raw_name)
    return {
        output_name: names
        for output_name, names in sorted(by_output.items())
        if not output_name.split("-", 1)[-1] or len(names) > 1
    }


def visual_preflight(config: dict, variants: list[dict]) -> dict:
    errors: list[str] = []
    details: dict[str, object] = {}

    checks = [
        ("fixture", list(config.get("scenes") or []), "scene"),
        ("dialog", list(config.get("dialog_scenes") or []), "dialog"),
        ("task", list(config.get("task_scenes") or []), "task"),
    ]
    for prefix, scenes, fallback_prefix in checks:
        names = [str(scene.get("name")) for scene in scenes if scene.get("name") is not None]
        duplicates = duplicate_values(names)
        collisions = duplicate_output_names(prefix, scenes, fallback_prefix)
        if duplicates:
            errors.append(f"duplicate_{prefix}_scene_names")
            details[f"duplicate_{prefix}_scene_names"] = duplicates
        if collisions:
            errors.append(f"{prefix}_scene_output_name_collisions")
            details[f"{prefix}_scene_output_name_collisions"] = collisions

    workbenches = [str(workbench) for workbench in config.get("workbenches") or []]
    duplicate_workbenches = duplicate_values(workbenches)
    if duplicate_workbenches:
        errors.append("duplicate_workbench_names")
        details["duplicate_workbench_names"] = duplicate_workbenches

    variant_slugs = [variant_slug(variant, index) for index, variant in enumerate(variants, start=1)]
    duplicate_variant_slugs = duplicate_values(variant_slugs)
    if duplicate_variant_slugs:
        errors.append("duplicate_variant_slugs")
        details["duplicate_variant_slugs"] = duplicate_variant_slugs

    return {
        "result": "failed" if errors else "ok",
        "errors": errors,
        **details,
    }


def write_preflight_failure(output_dir: Path, preflight: dict) -> None:
    summary = {
        "result": "preflight_failed",
        "preflight": preflight,
        "scenes": [],
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def run_one_capture(
    args,
    driver: Path,
    base_config: dict,
    variant: dict | None,
    output_dir: Path,
    allowlist: list[re.Pattern[str]],
) -> int:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    config = dict(base_config)
    if variant:
        config["variant"] = variant
        if "font_scale" in variant:
            config["font_scale"] = variant["font_scale"]
    config["output_dir"] = str(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="freecad-visual-baseline-") as temp:
        temp_path = Path(temp)
        config_path = temp_path / "config.json"
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        env = os.environ.copy()
        env.update(
            {
                "FREECAD_VISUAL_BASELINE_CONFIG": str(config_path),
                "FREECAD_USER_HOME": str(temp_path / "user"),
                "HOME": str(temp_path / "home"),
                "XDG_CACHE_HOME": str(temp_path / "cache"),
                "XDG_CONFIG_HOME": str(temp_path / "config"),
            }
        )
        for key in ("FREECAD_USER_HOME", "HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME"):
            Path(env[key]).mkdir(parents=True, exist_ok=True)

        if variant:
            copy_preference_pack(variant, repo_root, Path(env["FREECAD_USER_HOME"]))
            for key, value in (variant.get("env") or {}).items():
                env[str(key)] = str(value)

        command = build_command(args, driver)
        print("Running:", " ".join(command))
        print("Reports:", output_dir)
        log_path = output_dir / "freecad.log"
        try:
            completed = subprocess.run(
                command,
                env=env,
                check=False,
                timeout=args.timeout,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
            )
            output = completed.stdout or ""
            log_path.write_text(output, encoding="utf-8", errors="replace")
            if output:
                print(output, end="" if output.endswith("\n") else "\n")
            tracebacks = classify_tracebacks(output, allowlist)
            update_process_summary(output_dir, completed.returncode, log_path, tracebacks)
            if tracebacks["unallowed_traceback_count"]:
                return 3
            return completed.returncode
        except subprocess.TimeoutExpired as exc:
            output = exc.output or ""
            if isinstance(output, bytes):
                output = output.decode("utf-8", errors="replace")
            log_path.write_text(output, encoding="utf-8", errors="replace")
            tracebacks = classify_tracebacks(output, allowlist)
            update_process_summary(output_dir, 124, log_path, tracebacks)
            print(f"FreeCAD visual baseline timed out after {args.timeout}s", file=sys.stderr)
            return 124


def write_variant_summary(output_dir: Path, variant_results: list[dict]) -> None:
    scenes = []
    result = "ok"
    for item in variant_results:
        variant = item["variant"]
        slug = item["slug"]
        summary_path = item["summary"]
        if item["returncode"] != 0:
            result = "failed"
        if not summary_path.exists():
            result = "failed"
            scenes.append(
                {
                    "scene": f"variant-{slug}",
                    "variant": variant,
                    "error": "missing_summary",
                    "returncode": item["returncode"],
                }
            )
            continue
        summary = load_json(summary_path)
        if summary.get("result") != "ok":
            result = "failed"
        for scene in summary.get("scenes", []):
            merged = dict(scene)
            merged["scene"] = f"variant-{slug}-{scene.get('scene', 'scene')}"
            merged["variant"] = variant
            scenes.append(merged)

    aggregate = {
        "result": result,
        "variant_count": len(variant_results),
        "scene_count": len(scenes),
        "variants": [
            {
                "name": item["variant"].get("name", item["slug"]),
                "slug": item["slug"],
                "config": item["variant"],
                "returncode": item["returncode"],
                "summary": str(item["summary"]),
                "traceback_count": item.get("traceback_count"),
                "unallowed_traceback_count": item.get("unallowed_traceback_count"),
            }
            for item in variant_results
        ],
        "scenes": scenes,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(aggregate, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("freecad", nargs="?", help="FreeCAD binary or build/install directory")
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/freecad-visual-baseline"))
    parser.add_argument("--max-workbenches", type=int, default=0, help="0 means all registered workbenches")
    parser.add_argument("--max-scenes", type=int, default=0, help="0 means all configured fixture scenes")
    parser.add_argument("--max-dialogs", type=int, default=0, help="0 means all configured dialog scenes")
    parser.add_argument("--max-tasks", type=int, default=0, help="0 means all configured task scenes")
    parser.add_argument("--workbench", action="append", dest="workbenches", help="Workbench to include")
    parser.add_argument("--scene-config", type=Path, help="JSON file with fixture-backed visual scenes")
    parser.add_argument("--dialog-config", type=Path, help="JSON file with dialog/task visual scenes")
    parser.add_argument("--task-config", type=Path, help="JSON file with task-panel visual scenes")
    parser.add_argument(
        "--task",
        dest="task_names",
        action="append",
        default=[],
        help="Only run configured task scene names listed here; can be passed more than once",
    )
    parser.add_argument("--variant-config", type=Path, help="JSON file with theme/DPI/font variants")
    parser.add_argument(
        "--traceback-allowlist",
        type=Path,
        help="Regex allowlist file for expected Python tracebacks in FreeCAD process output",
    )
    parser.add_argument(
        "--no-workbenches",
        action="store_true",
        help="Capture only configured fixture scenes, not empty workbench scenes",
    )
    parser.add_argument("--window-size", nargs=2, type=int, default=[1600, 1000], metavar=("W", "H"))
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--no-xvfb", action="store_true")
    args = parser.parse_args(argv[1:])

    script_dir = Path(__file__).resolve().parent
    driver = script_dir / "gui_visual_baseline_driver.py"
    reset_output_dir(args.output_dir)

    config = {
        "include_workbenches": not args.no_workbenches,
        "max_workbenches": args.max_workbenches,
        "max_scenes": args.max_scenes,
        "max_dialogs": args.max_dialogs,
        "max_tasks": args.max_tasks,
        "repo_root": str(script_dir.parent),
        "window_size": args.window_size,
        "workbenches": args.workbenches or [],
    }
    if args.scene_config:
        scene_config = load_json(args.scene_config)
        config["scenes"] = scene_config.get("scenes", scene_config)
    if args.dialog_config:
        dialog_config = load_json(args.dialog_config)
        config["dialog_scenes"] = dialog_config.get("dialog_scenes", dialog_config)
    if args.task_config:
        task_config = load_json(args.task_config)
        task_scenes = task_config.get("task_scenes", task_config)
        if args.task_names:
            wanted = set(args.task_names)
            task_scenes = [scene for scene in task_scenes if scene.get("name") in wanted]
        config["task_scenes"] = task_scenes

    variants = []
    if args.variant_config:
        variant_config = load_json(args.variant_config)
        variants = variant_config.get("variants", variant_config)

    preflight = visual_preflight(config, variants)
    if preflight["result"] != "ok":
        write_preflight_failure(args.output_dir, preflight)
        print((args.output_dir / "summary.json").read_text(encoding="utf-8"))
        return 1

    if variants:
        results = []
        allowlist = load_allowlist(args.traceback_allowlist)
        for index, variant in enumerate(variants, start=1):
            slug = variant_slug(variant, index)
            variant_dir = args.output_dir / slug
            returncode = run_one_capture(args, driver, config, variant, variant_dir, allowlist)
            variant_summary = load_json(variant_dir / "summary.json") if (variant_dir / "summary.json").exists() else {}
            results.append(
                {
                    "variant": variant,
                    "slug": slug,
                    "returncode": returncode,
                    "summary": variant_dir / "summary.json",
                    "traceback_count": variant_summary.get("traceback_count"),
                    "unallowed_traceback_count": variant_summary.get("unallowed_traceback_count"),
                }
            )
        write_variant_summary(args.output_dir, results)
        completed_returncode = 0 if all(item["returncode"] == 0 for item in results) else 1
    else:
        completed_returncode = run_one_capture(
            args,
            driver,
            config,
            None,
            args.output_dir,
            load_allowlist(args.traceback_allowlist),
        )

    summary = args.output_dir / "summary.json"
    if summary.exists():
        print(summary.read_text(encoding="utf-8"))
    else:
        print(f"No summary produced in {args.output_dir}", file=sys.stderr)
        return 2
    return completed_returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
