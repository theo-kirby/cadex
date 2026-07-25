#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Part Design eval runner (plain Python, no bpy). Spawns one headless Blender
per case, then aggregates a scorecard. Makes REAL Claude API calls — run by
hand, never in CI. See README.md.

    tests/eval/mesh_agent_cad/runner.py --blender <path/to/blender> \
        [--cases single_gear,gear_pair_plate] [--model claude-opus-4-8]
"""

import argparse
import json
import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import cases  # noqa: E402

# Generous outer timeout: the in-Blender turn timeout is 600 s, plus startup
# and scoring.
CASE_TIMEOUT = 700


def run_case(blender, case_id, model, results_dir):
    command = [
        blender, "--background", "--factory-startup",
        "--python", os.path.join(_HERE, "eval_blender.py"), "--",
        "--case", case_id,
        "--model", model,
        "--results-dir", results_dir,
    ]
    started = time.monotonic()
    try:
        process = subprocess.run(command, capture_output=True, text=True,
                                 timeout=CASE_TIMEOUT)
        crashed = process.returncode != 0
        tail = (process.stdout + process.stderr)[-2000:]
    except subprocess.TimeoutExpired:
        crashed = True
        tail = "runner: case timed out after {:d}s".format(CASE_TIMEOUT)
    elapsed = time.monotonic() - started

    path = os.path.join(results_dir, case_id + ".json")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as file:
            result = json.load(file)
        result["runner_elapsed_s"] = round(elapsed, 1)
        if crashed:
            result["runner_note"] = "blender exited abnormally"
        return result
    return {
        "case": case_id,
        "model": model,
        "score": 0,
        "breakdown": {},
        "completed": False,
        "backend_error": "no result file written",
        "runner_elapsed_s": round(elapsed, 1),
        "runner_note": tail,
    }


def write_scorecard(results, results_dir):
    scorecard = {
        "total": sum(result["score"] for result in results),
        "max": 100 * len(results),
        "cases": results,
    }
    json_path = os.path.join(results_dir, "scorecard.json")
    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(scorecard, file, indent=1)

    columns = ("completed", "deterministic_rebuild", "geometry",
               "part_count", "params", "bbox", "stl_export")
    lines = [
        "# Part Design eval scorecard",
        "",
        "Total: **{:d} / {:d}**".format(scorecard["total"], scorecard["max"]),
        "",
        "| case | score | " + " | ".join(columns) + " | wall (s) |",
        "|---" * (len(columns) + 3) + "|",
    ]
    for result in results:
        breakdown = result.get("breakdown", {})
        lines.append("| {:s} | {:d} | {:s} | {!s} |".format(
            result["case"], result["score"],
            " | ".join(str(breakdown.get(column, "-")) for column in columns),
            result.get("wall_time_s", "-")))
    md_path = os.path.join(results_dir, "scorecard.md")
    with open(md_path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")
    return json_path, md_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", required=True,
                        help="Path to the Blender executable to test")
    parser.add_argument("--cases", default="",
                        help="Comma-separated case ids (default: all)")
    parser.add_argument("--model", default="claude-fable-5")
    parser.add_argument("--results-dir",
                        default=os.path.join(_HERE, "results"))
    args = parser.parse_args()

    all_ids = [case["id"] for case in cases.CASES]
    ids = [cid for cid in args.cases.split(",") if cid] or all_ids
    unknown = [cid for cid in ids if cid not in all_ids]
    if unknown:
        parser.error("unknown case(s): {:s}; known: {:s}".format(
            ", ".join(unknown), ", ".join(all_ids)))

    os.makedirs(args.results_dir, exist_ok=True)
    results = []
    for index, case_id in enumerate(ids):
        print("[{:d}/{:d}] {:s} ...".format(index + 1, len(ids), case_id),
              flush=True)
        result = run_case(args.blender, case_id, args.model, args.results_dir)
        print("    {:d}/100 ({:.0f}s){:s}".format(
            result["score"], result.get("runner_elapsed_s", 0),
            "  [" + result["runner_note"] + "]" if "runner_note" in result
            else ""), flush=True)
        results.append(result)

    json_path, md_path = write_scorecard(results, args.results_dir)
    print("\nScorecard: {:s}\n           {:s}".format(json_path, md_path))


if __name__ == "__main__":
    main()
