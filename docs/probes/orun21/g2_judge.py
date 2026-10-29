# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""orun21 G2: play a policy through ``cadex_goto play`` on held-out sequences and sum them up.

    ~/cadex-train-venv/bin/python docs/probes/orun21/g2_judge.py POLICY TASK OUT [--seeds 10]

Each seed's ``goto.json`` and ``view/`` go to ``OUT/s<seed>/``; ``OUT/summary.json``
holds G2's bar per seed and the time per leg, by band and bearing.
"""

import argparse
import json
from pathlib import Path
import statistics
import subprocess
import sys

GOTO = Path(__file__).resolve().parents[3] / "training" / "cadex_goto.py"
BANDS = "walk:0.4-0.7,run:1.0-1.5"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("policy")
    parser.add_argument("task")
    parser.add_argument("out")
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--bands", default=BANDS)
    options = parser.parse_args()
    out = Path(options.out)
    seeds, legs = [], []
    for seed in range(options.seeds):
        here = out / f"s{seed}"
        subprocess.run([sys.executable, str(GOTO), "play", options.policy, "--task", options.task,
                        "--seed", str(seed), "--split", "heldout", "--bands", options.bands,
                        "--view-dir", str(here / "view")], check=True, stdout=subprocess.DEVNULL)
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
                      "fell": result["fell"], "pass": result["pass"]})
        legs += [{"band": r["band"], "bearing": r["bearing"], "leg_s": r["leg_s"]} for r in rows]
    by = {}
    for leg in legs:
        if leg["leg_s"] is not None:
            by.setdefault(f"{leg['band']}/{leg['bearing']}", []).append(leg["leg_s"])
    ratios = [s for row in seeds for s in row["speed_ratios"]]
    summary = {"policy": options.policy, "seeds": seeds,
               "passes": sum(row["pass"]["all"] for row in seeds),
               "falls": sum(row["fell"] for row in seeds),
               "seconds_total": round(sum(row["seconds"] for row in seeds), 2),
               "speed_ratio_range": [min(ratios), max(ratios)] if ratios else None,
               "legs_read": {band: [sum(row["read_legs"][band][0] for row in seeds),
                                    sum(row["read_legs"][band][1] for row in seeds)] for band in ("walk", "run")},
               "leg_s_mean": {key: round(statistics.mean(v), 2) for key, v in sorted(by.items())}}
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: summary[k] for k in ("passes", "falls", "seconds_total", "speed_ratio_range",
                                              "legs_read", "leg_s_mean")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
