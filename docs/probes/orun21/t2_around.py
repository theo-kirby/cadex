# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""T2: terrain round the start, so go-to-point legs meet it (ADR-857).

Run from ~/cadex-train-venv:

    python docs/probes/orun21/t2_around.py legs           # how often a leg meets terrain, ADR-856's pool and this one
    python docs/probes/orun21/t2_around.py bundle OUT     # write the Go1 screen's bundle on this pool

``legs`` draws the first ``--legs`` legs of ``--sequences`` train-split
go-to-point sequences (``cadex_goto.sequence``, the trainer's own draw) over
every course of each pool and reports the share of legs whose ground, read
by ``CadexDynamics.terrain_box_ground_mm`` every 50 mm, rises or falls more
than 10 mm, and the share of points that lie off the extent. ``bundle`` is
``t1_levels.py bundle`` on :data:`POOL`.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src" / "Mod" / "cadex"))
sys.path.insert(0, str(REPO / "training"))
sys.path.insert(0, str(HERE))
import CadexDynamics  # noqa: E402
import cadex_goto  # noqa: E402
import t1_levels  # noqa: E402

BANDS = "walk:0.4-0.7,run:1.0-1.5"

#: ADR-856's kinds and level bands, laid round the start on a 24 m square
#: that holds the third point of 90% of train sequences; longer runs and
#: fewer patches keep the slots near ADR-856's (41 against 29).
POOL = {
    "form": "boxes", "x_range_mm": [-12000.0, 12000.0], "y_range_mm": [-12000.0, 12000.0],
    "random": {"seed": 857, "courses": 64, "levels": 8, "clear_mm": 600.0, "around": True,
               "run_mm": [1500.0, 3000.0],
               "step_mm": [10.0, 130.0], "grade_deg": [2.0, 20.0], "slope_mm": [400.0, 1000.0],
               "bump_mm": [10.0, 90.0], "bump_radius_mm": [300.0, 600.0], "bumps": 12,
               "platform_mm": [10.0, 150.0], "platforms": 2,
               "rock_mm": [10.0, 60.0], "rock_radius_mm": [250.0, 400.0], "rocks": 1,
               "tile_mm": [10.0, 80.0], "tile_size_mm": [800.0, 1200.0],
               "tile_cell_mm": [300.0, 400.0], "tiles": 1},
}


def legs(sequences: int, count: int) -> None:
    bands = cadex_goto.parse_bands(BANDS)
    plans = [cadex_goto.sequence(seed, split="train", bands=bands)["points"][:count]
             for seed in range(sequences)]
    for name, pool in (("ADR-856", t1_levels.POOL), ("ADR-857", POOL)):
        descriptor = CadexDynamics.terrain_grid(pool)["descriptor"]
        (x0, x1), (y0, y1) = descriptor["x_range_mm"], descriptor["y_range_mm"]
        met = [[0, 0] for _ in range(count)]
        off = [0] * count
        for index, plan in enumerate(plans):
            course = descriptor["pool"][index % len(descriptor["pool"])]
            ax = ay = 0.0
            for leg, point in enumerate(plan):
                bx, by = (1000.0 * v for v in point["xy_m"])
                off[leg] += not (x0 <= bx <= x1 and y0 <= by <= y1)
                steps = max(1, int(math.hypot(bx - ax, by - ay) // 50.0))
                heights = [CadexDynamics.terrain_box_ground_mm(
                    course, ax + (bx - ax) * i / steps, ay + (by - ay) * i / steps)
                    for i in range(steps + 1)]
                met[leg][0] += max(heights) - min(heights) > 10.0
                met[leg][1] += 1
                ax, ay = bx, by
        print(json.dumps({"pool": name, "slots": descriptor["slots"],
                          "dome_slots": descriptor["dome_slots"],
                          "leg_meets_terrain": [round(a / b, 3) for a, b in met],
                          "point_off_extent": [round(v / len(plans), 3) for v in off]}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("verb", choices=("legs", "bundle"))
    parser.add_argument("path", type=Path, nargs="?")
    parser.add_argument("--sequences", type=int, default=640)
    parser.add_argument("--legs", type=int, default=4)
    args = parser.parse_args()
    if args.verb == "legs":
        legs(args.sequences, args.legs)
    else:
        if args.path is None:
            parser.error("bundle needs OUT")
        t1_levels.POOL = POOL
        t1_levels.bundle(args.path)


if __name__ == "__main__":
    main()
