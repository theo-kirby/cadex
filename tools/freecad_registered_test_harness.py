#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Run registered FreeCAD test units one suite at a time.

This makes ``FreeCAD -t 0`` failures actionable by isolating which registered
unit passes, fails, times out, or emits unclassified process errors.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


TEST_LIST_RE = re.compile(r"^Registered test units:\s*$")


def slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in value).strip("-")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def reset_output_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def run_command(command: list[str], timeout: int) -> tuple[int, str, float]:
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        start_new_session=True,
    )
    try:
        output, _ = process.communicate(timeout=timeout)
        return process.returncode, output or "", time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            output, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            output, _ = process.communicate()
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        output = output or ""
        return 124, output + f"\nTIMEOUT after {timeout}s\n", time.monotonic() - started


def command_for(freecad: Path, suite: str | None = None, use_xvfb: bool = True) -> list[str]:
    command = [str(freecad)]
    if suite is None:
        command.append("-t")
    else:
        command.extend(["-t", suite])
    if use_xvfb:
        return ["xvfb-run", "-a", *command]
    return command


def parse_registered_units(output: str) -> list[str]:
    units: list[str] = []
    in_list = False
    for line in output.splitlines():
        stripped = line.strip()
        if TEST_LIST_RE.match(stripped):
            in_list = True
            continue
        if not in_list:
            continue
        if not stripped:
            continue
        if stripped.startswith("Please choose one") or stripped.startswith("-"):
            break
        units.append(stripped)
    return units


def list_registered_units(freecad: Path, timeout: int, use_xvfb: bool) -> tuple[list[str], dict[str, Any]]:
    command = command_for(freecad, None, use_xvfb)
    returncode, output, duration = run_command(command, timeout)
    units = parse_registered_units(output)
    return units, {
        "command": command,
        "duration_seconds": round(duration, 3),
        "returncode": returncode,
        "unit_count": len(units),
    }


def skip_reasons(output: str) -> dict[str, int]:
    reasons: dict[str, int] = {}
    for reason in re.findall(r"skipped '([^']+)'", output):
        reasons[reason] = reasons.get(reason, 0) + 1
    return reasons


def classify_suite(name: str, command: list[str], returncode: int, output: str, duration: float, log_path: Path) -> dict[str, Any]:
    traceback_count = output.count("Traceback (most recent call last):")
    quantity_errors = output.count('TypeError: Cannot call meta function "slot(Base::Quantity)"')
    deleted_reference_errors = output.count("ReferenceError: Cannot access attribute")
    segv = "SIGSEGV" in output or "Segmentation fault" in output
    timeout = returncode == 124 or "TIMEOUT after" in output
    ok_summary = re.search(r"\nOK(?:\s|\n|$)", output[-4000:]) is not None
    failed_summary = re.search(r"\nFAILED \(", output[-4000:]) is not None
    ran_match = re.search(r"\nRan (?P<count>\d+) tests? in (?P<seconds>[0-9.]+)s", output[-4000:])

    if timeout:
        result = "timeout"
    elif segv:
        result = "crash"
    elif returncode != 0:
        result = "process_failed"
    elif traceback_count:
        result = "traceback"
    elif failed_summary:
        result = "failed"
    elif quantity_errors or deleted_reference_errors:
        result = "ok_with_process_errors"
    elif ok_summary:
        result = "ok"
    else:
        result = "unknown"

    return {
        "suite": name,
        "command": command,
        "duration_seconds": round(duration, 3),
        "returncode": returncode,
        "result": result,
        "log": str(log_path),
        "ran_tests": int(ran_match.group("count")) if ran_match else None,
        "ok_line_count": len(re.findall(r"\.\.\. ok(?:\n|$)", output)),
        "skipped_line_count": len(re.findall(r"\.\.\. skipped", output)),
        "skip_reasons": skip_reasons(output),
        "traceback_count": traceback_count,
        "quantity_slot_type_errors": quantity_errors,
        "deleted_object_reference_errors": deleted_reference_errors,
        "segmentation_fault": segv,
        "timeout": timeout,
    }


def duplicate_values(values: list[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)


def slug_collisions(values: list[str]) -> dict[str, list[str]]:
    by_slug: dict[str, list[str]] = {}
    for value in values:
        by_slug.setdefault(slug(value), []).append(value)
    return {
        slug_value: sorted(set(names))
        for slug_value, names in by_slug.items()
        if not slug_value or len(set(names)) > 1 or len(names) > 1
    }


def suite_preflight(discovered: list[str], selected: list[str]) -> dict[str, Any]:
    duplicate_discovered = duplicate_values(discovered)
    duplicate_selected = duplicate_values(selected)
    discovered_slug_collisions = slug_collisions(discovered)
    selected_slug_collisions = slug_collisions(selected)

    errors = []
    if duplicate_discovered:
        errors.append("duplicate_discovered_suites")
    if duplicate_selected:
        errors.append("duplicate_selected_suites")
    if discovered_slug_collisions:
        errors.append("discovered_log_slug_collisions")
    if selected_slug_collisions:
        errors.append("selected_log_slug_collisions")

    return {
        "result": "failed" if errors else "ok",
        "errors": errors,
        "duplicate_discovered_suites": duplicate_discovered,
        "duplicate_selected_suites": duplicate_selected,
        "discovered_log_slug_collisions": discovered_slug_collisions,
        "selected_log_slug_collisions": selected_slug_collisions,
    }


def run_suite(freecad: Path, suite: str, output_dir: Path, timeout: int, use_xvfb: bool) -> dict[str, Any]:
    command = command_for(freecad, suite, use_xvfb)
    returncode, output, duration = run_command(command, timeout)
    log_path = output_dir / f"{slug(suite)}.log"
    log_path.write_text(output, encoding="utf-8", errors="replace")
    return classify_suite(suite, command, returncode, output, duration, log_path)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("freecad", type=Path, nargs="?", default=Path("tools/freecad_venv.sh"))
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/freecad-test-results/freecad-registered-split"))
    parser.add_argument("--suite", dest="suites", action="append", default=[], help="Suite to run; may be passed more than once")
    parser.add_argument("--max-suites", type=int, default=0, help="Run at most this many discovered suites; 0 means all selected")
    parser.add_argument("--list-timeout", type=int, default=60)
    parser.add_argument("--timeout-per-suite", type=int, default=180)
    parser.add_argument("--no-xvfb", action="store_true")
    args = parser.parse_args(argv[1:])

    reset_output_dir(args.output_dir)
    use_xvfb = not args.no_xvfb

    discovered, list_result = list_registered_units(args.freecad, args.list_timeout, use_xvfb)
    suites = args.suites or discovered
    if args.max_suites > 0:
        suites = suites[: args.max_suites]

    preflight = suite_preflight(discovered, suites)
    if preflight["result"] != "ok":
        summary = {
            "freecad": str(args.freecad),
            "output_dir": str(args.output_dir),
            "list": list_result,
            "discovered_suites": discovered,
            "selected_suite_count": len(suites),
            "preflight": preflight,
            "result_counts": {},
            "results": [],
        }
        (args.output_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 1

    results = []
    for suite in suites:
        if suite not in discovered:
            results.append({"suite": suite, "result": "not_registered"})
            continue
        print(f"running {suite}", flush=True)
        results.append(run_suite(args.freecad, suite, args.output_dir, args.timeout_per_suite, use_xvfb))

    result_counts: dict[str, int] = {}
    for result in results:
        key = result.get("result", "unknown")
        result_counts[key] = result_counts.get(key, 0) + 1

    summary = {
        "freecad": str(args.freecad),
        "output_dir": str(args.output_dir),
        "list": list_result,
        "discovered_suites": discovered,
        "selected_suite_count": len(suites),
        "preflight": preflight,
        "result_counts": result_counts,
        "results": results,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if all(result.get("result") == "ok" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
