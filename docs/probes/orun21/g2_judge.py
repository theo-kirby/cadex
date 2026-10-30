# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""orun21 G2: play a policy through ``cadex_goto play`` on held-out sequences and sum them up.

    ~/cadex-train-venv/bin/python docs/probes/orun21/g2_judge.py POLICY TASK OUT [--seeds 10]
        [--level L [--maze] | --flat]

Each seed's ``goto.json`` and ``view/`` go to ``OUT/s<seed>/``; ``OUT/summary.json``
holds G2's bar per seed, the time per leg, by band and bearing, and each seed's
drive RMS with the worst over all seeds (``drive_rms_worst``, ADR-952).

On a bundle with a drawn terrain pool (T2, ADR-858), ``--level L`` plays seed
``s`` on ``CadexDynamics.terrain_evaluation_course(terrain, s, level=L)``, a
course from the held-out stream the trainer never drew, and ``--flat`` on an
empty course (every slot parked, the plane at z = 0). Without either, the
model plays as it is, which on a pooled bundle is its course 0.

``--maze`` (T2, ADR-860) turns the pool's walls on (``wall_mm`` WALL_MM,
``maze_cells`` MAZE_CELLS) and plays, from the held-out stream at ``--level``,
the first ``--seeds`` evaluation seeds whose course holds a maze, each on
``cadex_goto.maze_route``'s way through it and back; the course's ``walls``
name the maze's slots, so the player reads any body inside one.
"""

import argparse
import json
from pathlib import Path
import statistics
import subprocess
import sys

REPO = Path(__file__).resolve().parents[3]
GOTO = REPO / "training" / "cadex_goto.py"
BANDS = "walk:0.4-0.7,run:1.0-1.5"
#: Walls the Go1 (trunk about 0.3 m up) cannot step over, and a maze with a turn.
WALL_MM = [400.0, 500.0]
MAZE_CELLS = [2, 3]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("policy")
    parser.add_argument("task")
    parser.add_argument("out")
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--bands", default=BANDS)
    ground = parser.add_mutually_exclusive_group()
    ground.add_argument("--level", type=int, default=None)
    ground.add_argument("--flat", action="store_true")
    parser.add_argument("--maze", action="store_true")
    parser.add_argument("--other-model", action="store_true",
                        help="judge on a model the policy did not train on (a cut's policy on its export)")
    options = parser.parse_args()
    if options.maze and options.level is None:
        parser.error("--maze needs --level")
    out = Path(options.out)
    terrain = None
    if options.level is not None or options.flat:
        sys.path.insert(0, str(REPO / "src" / "Mod" / "cadex"))
        import CadexDynamics

        terrain = json.loads(Path(options.task).read_text())["terrain"]
        if options.maze:
            sys.path.insert(0, str(GOTO.parent))
            import cadex_goto

            terrain = {**terrain, "random": {**terrain["random"], "wall_mm": WALL_MM,
                                             "maze_cells": MAZE_CELLS}}
    seeds, legs = [], []
    order = range(options.seeds) if not options.maze else range(10 * options.seeds)
    for seed in order:
        if len(seeds) == options.seeds:
            break
        here = out / f"s{seed}"
        extra = []
        if options.maze:
            course = CadexDynamics.terrain_evaluation_course(terrain, seed, level=options.level)
            mazes = [f for f in course["features"] if f["kind"] == "maze"]
            if not mazes:
                continue
            maze = mazes[0]
            ground = CadexDynamics._terrain_profile_mm(course["features"], maze["x_mm"])
            blocks = CadexDynamics.terrain_maze_walls(maze, ground)
            course["walls"] = [i for i, box in enumerate(course["boxes"]) if any(
                box["shape"] == "block" and box["x_range_mm"] == list(xs) and box["y_range_mm"] == list(ys)
                and box["top_mm"][0] == top for xs, ys, top in blocks)]
            if len(course["walls"]) != len(blocks):
                raise SystemExit(f"seed {seed}: {len(blocks)} walls, {len(course['walls'])} found in the boxes")
            plan = cadex_goto.maze_route(maze, blocks, seed, split="heldout",
                                         bands=cadex_goto.parse_bands(options.bands))
            course["drawing"] = CadexDynamics.terrain_drawing(course)
            here.mkdir(parents=True, exist_ok=True)
            (here / "course.json").write_text(json.dumps(course))
            (here / "sequence.json").write_text(json.dumps(plan, indent=1))
            extra = ["--course", str(here / "course.json"), "--sequence", str(here / "sequence.json")]
        elif terrain is not None:
            if options.flat:
                course = {key: value for key, value in terrain.items() if key != "pool"}
                course.update(features=[], boxes=[], domes=[], lowest_mm=0.0, highest_mm=0.0,
                              course={"flat": True})
            else:
                course = CadexDynamics.terrain_evaluation_course(terrain, seed, level=options.level)
            course["drawing"] = CadexDynamics.terrain_drawing(course)
            here.mkdir(parents=True, exist_ok=True)
            (here / "course.json").write_text(json.dumps(course))
            extra = ["--course", str(here / "course.json")]
        subprocess.run([sys.executable, str(GOTO), "play", options.policy, "--task", options.task,
                        "--seed", str(seed), "--split", "heldout", "--bands", options.bands,
                        "--view-dir", str(here / "view"), *extra,
                        *(["--other-model"] if options.other_model else [])], check=True, stdout=subprocess.DEVNULL)
        result = json.loads((here / "goto.json").read_text())
        rows = result["points"]
        holds = [r["hold_worst_m"] for r in rows if r["hold_worst_m"] is not None]
        seeds.append({"seed": seed, "seconds": result["seconds"], "reached": result["reached"],
                      "of": len(rows), "behind": sum(r["bearing"] == "behind" for r in rows),
                      "closest_max_m": max(r["closest_m"] for r in rows if r["closest_m"] is not None),
                      "hold_worst_m": max(holds) if holds else None,
                      "speed_ratios": result["speed_ratios"],
                      "read_legs": {band: [sum("speed_ratio" in r for r in rows if r["band"] == band),
                                           sum(r["band"] == band for r in rows)] for band in ("walk", "run")},
                      "fell": result["fell"], "pass": result["pass"], "walls": result.get("walls"),
                      "drive_rms_nm": (result.get("drives") or {}).get("rms_nm"),
                      "drive_worst": (result.get("drives") or {}).get("worst"),
                      "drive_worst_rms_nm": (result.get("drives") or {}).get("worst_rms_nm"),
                      "course": result.get("course"), "reach_fail": [
                          r["point"] for r in rows if not r["reached"] or r["closest_m"] is None
                          or r["closest_m"] > result["thresholds"]["reach_m"]]})
        legs += [{"band": r["band"], "bearing": r["bearing"], "leg_s": r["leg_s"]} for r in rows]
    by = {}
    for leg in legs:
        if leg["leg_s"] is not None:
            by.setdefault(f"{leg['band']}/{leg['bearing']}", []).append(leg["leg_s"])
    ratios = [s for row in seeds for s in row["speed_ratios"]]
    summary = {"policy": options.policy, "level": options.level, "flat": options.flat,
               "maze": options.maze, "seeds": seeds,
               "pass_parts": {part: sum(row["pass"][part] for row in seeds)
                              for part in ("reach", "hold", "speed", "no_fall", "clear_walls")},
               "passes": sum(row["pass"]["all"] for row in seeds),
               "falls": sum(row["fell"] for row in seeds),
               "seconds_total": round(sum(row["seconds"] for row in seeds), 2),
               "speed_ratio_range": [min(ratios), max(ratios)] if ratios else None,
               "legs_read": {band: [sum(row["read_legs"][band][0] for row in seeds),
                                    sum(row["read_legs"][band][1] for row in seeds)] for band in ("walk", "run")},
               "leg_s_mean": {key: round(statistics.mean(v), 2) for key, v in sorted(by.items())}}
    # ADR-952: the worst drive's RMS over any one episode, for a rating check.
    rated = [row for row in seeds if row["drive_worst_rms_nm"] is not None]
    worst = max(rated, key=lambda row: row["drive_worst_rms_nm"]) if rated else None
    summary["drive_rms_worst"] = None if worst is None else {
        "nm": worst["drive_worst_rms_nm"], "drive": worst["drive_worst"], "seed": worst["seed"]}
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: summary[k] for k in ("passes", "pass_parts", "falls", "seconds_total", "speed_ratio_range",
                                              "legs_read", "leg_s_mean", "drive_rms_worst")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
