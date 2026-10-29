# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""T1: terrain levels and the curriculum on points reached (ADR-856).

Run from ~/cadex-train-venv:

    python docs/probes/orun21/t1_levels.py bundle OUT      # write the Go1 screen's bundle
    python docs/probes/orun21/t1_levels.py levels PROGRESS # the level distribution over a run

``bundle`` swaps the orun18 Go1's plane for a leveled random box pool drawn by
``CadexDynamics.terrain_grid`` (the one engine source) and stood in the model
by the engine's own ``_environment_box_course``, every terrain geom on the
Go1 floor's contact (feet only, friction 0.6). Kinds a sphere foot may meet:
steps, slopes, bumps, platforms, rock patches and tile patches; walls are
left to T2, where points steer round them. ``levels`` reads a run's
``progress.json`` and prints the per-level counts at a few iterations and
the mean level.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src" / "Mod" / "cadex"))
import CadexDynamics  # noqa: E402

GO1 = Path.home() / "cadex-projects/orun21-lab/go1/outputs/go1-model.xml"

POOL = {
    "form": "boxes", "x_range_mm": [-2000.0, 12000.0], "y_range_mm": [-4000.0, 4000.0],
    "random": {"seed": 856, "courses": 64, "levels": 8, "clear_mm": 600.0,
               "run_mm": [500.0, 1200.0],
               "step_mm": [10.0, 130.0], "grade_deg": [2.0, 20.0],
               "bump_mm": [10.0, 90.0], "bump_radius_mm": [300.0, 600.0], "bumps": 4,
               "platform_mm": [10.0, 150.0], "platforms": 1,
               "rock_mm": [10.0, 60.0], "rock_radius_mm": [250.0, 400.0], "rocks": 1,
               "tile_mm": [10.0, 80.0], "tile_size_mm": [800.0, 1200.0],
               "tile_cell_mm": [300.0, 400.0], "tiles": 1},
}


def bundle(out: Path) -> None:
    import mujoco

    task = json.loads((GO1.parent / "go1_joystick-task.json").read_text())
    descriptor = CadexDynamics.terrain_grid(POOL)["descriptor"]
    spec = mujoco.MjSpec.from_file(str(GO1))
    for geom in list(spec.geoms):
        if geom.type == mujoco.mjtGeom.mjGEOM_PLANE:
            spec.delete(geom)
    CadexDynamics._environment_box_course(mujoco, spec, descriptor)
    for geom in spec.geoms:
        if geom.name.startswith(CadexDynamics.ENVIRONMENT_TERRAIN_GEOM):
            # The Go1 floor's contact: only the feet touch it (Playground's model).
            geom.contype, geom.conaffinity, geom.priority = 1, 0, 1
            geom.friction = [0.6, 0.005, 0.0001]
            geom.condim = 3
    spec.compile()
    xml = spec.to_xml().encode()
    out.mkdir(parents=True, exist_ok=True)
    (out / "go1-levels-model.xml").write_bytes(xml)
    task["model"] = dict(task["model"], path="go1-levels-model.xml", bytes=len(xml),
                         sha256=hashlib.sha256(xml).hexdigest())
    task["terrain"] = descriptor
    task["label"] = "go1 joystick on a leveled box pool (orun21 T1, ADR-856)"
    (out / "go1-levels-task.json").write_text(json.dumps(task, indent=1))
    by_level: dict[int, list[float]] = {}
    for course in descriptor["pool"]:
        by_level.setdefault(course["level"], []).append(
            course["highest_mm"] - course["lowest_mm"])
    print(json.dumps({"slots": descriptor["slots"], "dome_slots": descriptor["dome_slots"],
                      "courses": len(descriptor["pool"]),
                      "relief_mm_by_level": {k: [round(min(v)), round(max(v))]
                                             for k, v in sorted(by_level.items())}}))


def levels(progress: Path) -> None:
    data = json.loads(progress.read_text())
    curve = data.get("terrain_levels_curve") or []
    if not curve:
        raise SystemExit(f"{progress} carries no terrain_levels_curve")
    picks = sorted({0, len(curve) // 8, len(curve) // 4, len(curve) // 2,
                    3 * len(curve) // 4, len(curve) - 1})
    for index in picks:
        iteration, counts = curve[index]
        total = sum(counts)
        mean = sum(level * count for level, count in enumerate(counts)) / total
        print(f"iteration {iteration:5d}  mean level {mean:5.2f}  "
              + " ".join(f"{int(c):5d}" for c in counts))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("verb", choices=("bundle", "levels"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    (bundle if args.verb == "bundle" else levels)(args.path)


if __name__ == "__main__":
    main()
