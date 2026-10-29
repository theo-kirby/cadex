# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""orun21 G2: play a policy through ``cadex_goto play`` on held-out sequences and sum them up.

    ~/cadex-train-venv/bin/python docs/probes/orun21/g2_judge.py POLICY TASK OUT [--seeds 10]
        [--level L | --flat]

Each seed's ``goto.json`` and ``view/`` go to ``OUT/s<seed>/``; ``OUT/summary.json``
holds G2's bar per seed and the time per leg, by band and bearing.

On a bundle with a drawn terrain pool (T2, ADR-858), ``--level L`` plays seed
``s`` on ``CadexDynamics.terrain_evaluation_course(terrain, s, level=L)``, a
course from the held-out stream the trainer never drew, and ``--flat`` on an
empty course (every slot parked, the plane at z = 0). Without either, the
model plays as it is, which on a pooled bundle is its course 0.
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
    options = parser.parse_args()
    out = Path(options.out)
    terrain = None
    if options.level is not None or options.flat:
        sys.path.insert(0, str(REPO / "src" / "Mod" / "cadex"))
        import CadexDynamics

        terrain = json.loads(Path(options.task).read_text())["terrain"]
    seeds, legs = [], []
    for seed in range(options.seeds):
        here = out / f"s{seed}"
        extra = []
        if terrain is not None:
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
                        "--view-dir", str(here / "view"), *extra], check=True, stdout=subprocess.DEVNULL)
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
                      "fell": result["fell"], "pass": result["pass"],
                      "course": result.get("course"), "reach_fail": [
                          r["point"] for r in rows if not r["reached"] or r["closest_m"] is None
                          or r["closest_m"] > result["thresholds"]["reach_m"]]})
        legs += [{"band": r["band"], "bearing": r["bearing"], "leg_s": r["leg_s"]} for r in rows]
    by = {}
    for leg in legs:
        if leg["leg_s"] is not None:
            by.setdefault(f"{leg['band']}/{leg['bearing']}", []).append(leg["leg_s"])
    ratios = [s for row in seeds for s in row["speed_ratios"]]
    summary = {"policy": options.policy, "level": options.level, "flat": options.flat, "seeds": seeds,
               "pass_parts": {part: sum(row["pass"][part] for row in seeds)
                              for part in ("reach", "hold", "speed", "no_fall")},
               "passes": sum(row["pass"]["all"] for row in seeds),
               "falls": sum(row["fell"] for row in seeds),
               "seconds_total": round(sum(row["seconds"] for row in seeds), 2),
               "speed_ratio_range": [min(ratios), max(ratios)] if ratios else None,
               "legs_read": {band: [sum(row["read_legs"][band][0] for row in seeds),
                                    sum(row["read_legs"][band][1] for row in seeds)] for band in ("walk", "run")},
               "leg_s_mean": {key: round(statistics.mean(v), 2) for key, v in sorted(by.items())}}
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: summary[k] for k in ("passes", "pass_parts", "falls", "seconds_total", "speed_ratio_range",
                                              "legs_read", "leg_s_mean")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
