#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Launch FreeCAD and exercise/discover GUI controls.

The harness starts a FreeCAD GUI binary with an isolated profile, runs
gui_interaction_driver.py inside the application, and writes JSON reports.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import shutil
import subprocess
import sys
import tempfile
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
    freecad = find_freecad(args.freecad)
    command = [freecad, str(driver)]
    if args.no_xvfb or os.environ.get("DISPLAY"):
        return command
    xvfb = shutil.which("xvfb-run")
    if xvfb:
        return [xvfb, "-a", *command]
    return command


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("freecad", nargs="?", help="FreeCAD binary or build/install directory")
    parser.add_argument("--output-dir", type=Path, help="Report directory")
    parser.add_argument("--mode", choices=("survey", "exercise", "workflows"), default="exercise")
    parser.add_argument("--max-workbenches", type=int, default=0, help="0 means all registered workbenches")
    parser.add_argument("--max-interactions", type=int, default=500)
    parser.add_argument("--max-targets", type=int, default=0, help="0 means no target scan cap")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--allow-risky", action="store_true", help="Do not skip file/session/destructive actions")
    parser.add_argument("--no-xvfb", action="store_true", help="Do not wrap with xvfb-run when DISPLAY is unset")
    args = parser.parse_args(argv[1:])

    script_dir = Path(__file__).resolve().parent
    driver = script_dir / "gui_interaction_driver.py"
    output_dir = args.output_dir or Path.cwd() / "gui-interaction-report"
    output_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "allow_risky": args.allow_risky,
        "max_interactions": args.max_interactions,
        "max_targets": args.max_targets,
        "max_workbenches": args.max_workbenches,
        "mode": args.mode,
        "output_dir": str(output_dir),
    }

    with tempfile.TemporaryDirectory(prefix="freecad-gui-harness-") as temp:
        temp_path = Path(temp)
        config_path = temp_path / "config.json"
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        user_home = temp_path / "user"
        user_home.mkdir()
        env = os.environ.copy()
        env.update(
            {
                "FREECAD_GUI_HARNESS_CONFIG": str(config_path),
                "FREECAD_USER_HOME": str(user_home),
                "BROWSER": "/bin/false",
                "HOME": str(temp_path / "home"),
                "XDG_CACHE_HOME": str(temp_path / "cache"),
                "XDG_CONFIG_HOME": str(temp_path / "config"),
            }
        )
        for key in ("HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME"):
            Path(env[key]).mkdir(parents=True, exist_ok=True)

        command = build_command(args, driver)
        print("Running:", " ".join(command))
        print("Reports:", output_dir)
        process = subprocess.Popen(command, env=env, start_new_session=True)
        try:
            returncode = process.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            print(f"FreeCAD GUI harness timed out after {args.timeout}s", file=sys.stderr)
            return 124

    summary_path = output_dir / "summary.json"
    if summary_path.exists():
        if returncode != 0:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["result"] = "process_failed"
            summary["process_returncode"] = returncode
            summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        print(summary_path.read_text(encoding="utf-8"))
    else:
        print(f"No summary produced in {output_dir}", file=sys.stderr)
        return 2
    return returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
