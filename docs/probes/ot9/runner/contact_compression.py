# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""How far do Robin's wheels sink into the floor? Contact spring, not geometry.

The ot9 charter asks for standing contact compression to be reported apart
from geometry intersections, because the two are different quantities. An
intersection is exact BREP overlap between two printed or purchased parts,
measured by the engine's clearance check. A compression is how far a MuJoCo
collision sphere sits below the floor plane when soft contact is carrying
the robot's weight. It follows the applied load and says nothing about the
parts.

This reads that compression from traces that were already exported. For
every sphere collision geom in the MJCF, the sphere's centre is placed from
its body's world pose in each ``solver_output`` frame (``position_mm`` plus
``rotation_xyzw``, the same poses ``balance_eval.py`` reads). The compression
is ``radius - (centre_z - floor_z)``: positive means the sphere overlaps the
floor, and negative means the gap above it. It also reports the gap at the
model's ``solved`` keyframe, from MuJoCo's own ``contact.dist``, which is the
design at rest before any load is carried. Nothing is rebuilt or rolled out.

    pixi run python docs/probes/ot9/runner/contact_compression.py \\
        --model robin_model-model.xml TRACE.json [TRACE.json ...] \\
        [--settled-after 1.0] [--out report.json]
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

SCHEMA = "ot9-contact-compression-v1"


def _mujoco():
    import mujoco  # noqa: PLC0415 - deferred like balance_eval's

    return mujoco


def rotate(quat_xyzw, vector) -> list[float]:
    x, y, z, w = (float(v) for v in quat_xyzw)
    vx, vy, vz = (float(v) for v in vector)
    # v + 2w(q x v) + 2 q x (q x v)
    cx, cy, cz = y * vz - z * vy, z * vx - x * vz, x * vy - y * vx
    ddx, ddy, ddz = y * cz - z * cy, z * cx - x * cz, x * cy - y * cx
    return [vx + 2.0 * (w * cx + ddx), vy + 2.0 * (w * cy + ddy), vz + 2.0 * (w * cz + ddz)]


def floor_and_spheres(model_path: Path, keyframe: str = "solved") -> dict[str, Any]:
    """The world floor plane's height, every sphere geom, and the keyframe gap.

    Only a world plane with its normal on +Z counts as the floor. Any other
    plane cannot be turned into one number, so it is refused rather than
    guessed.
    """

    mujoco = _mujoco()
    model = mujoco.MjModel.from_xml_path(str(model_path))
    planes = [g for g in range(model.ngeom)
              if model.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE and model.geom_bodyid[g] == 0]
    if len(planes) != 1:
        raise SystemExit(f"{model_path} has {len(planes)} world planes; this reads exactly one floor")
    plane = planes[0]
    if [round(float(v), 12) for v in model.geom_quat[plane]] != [1.0, 0.0, 0.0, 0.0]:
        raise SystemExit(f"{model_path}'s floor plane is not level; this reads a +Z floor only")
    spheres = []
    for g in range(model.ngeom):
        if model.geom_type[g] != mujoco.mjtGeom.mjGEOM_SPHERE or model.geom_bodyid[g] == 0:
            continue
        spheres.append({
            "geom": str(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, g)),
            "body": str(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, int(model.geom_bodyid[g]))),
            "local_mm": [float(v) * 1000.0 for v in model.geom_pos[g]],
            "radius_mm": float(model.geom_size[g][0]) * 1000.0,
        })
    data = mujoco.MjData(model)
    key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, keyframe)
    if key < 0:
        raise SystemExit(f"{model_path} carries no {keyframe!r} keyframe")
    mujoco.mj_resetDataKeyframe(model, data, key)
    mujoco.mj_forward(model, data)
    names = {s["geom"] for s in spheres}
    keyframe_gaps = {}
    for index in range(int(data.ncon)):
        contact = data.contact[index]
        pair = {int(contact.geom1), int(contact.geom2)}
        if plane not in pair:
            continue
        other = (pair - {plane}).pop()
        name = str(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, other))
        if name in names:
            keyframe_gaps[name] = float(contact.dist) * 1000.0
    return {"floor_z_mm": float(model.geom_pos[plane][2]) * 1000.0, "spheres": spheres,
            "keyframe": keyframe, "keyframe_contact_dist_mm": keyframe_gaps}


def compression(trace_path: Path, floor: dict[str, Any], settled_after_s: float = 1.0) -> dict[str, Any]:
    """Peak compression over every frame, plus the settled spread after ``settled_after_s``."""

    raw = json.loads(Path(trace_path).read_text(encoding="utf-8"))
    frames = [f for f in raw["frames"] if f.get("frame_kind") == "solver_output"]
    peak = None
    settled = []
    for frame in frames:
        time_s = float(frame["nominal_time_s"])
        for sphere in floor["spheres"]:
            pose = frame["component_placements"][sphere["body"]]
            offset = rotate(pose["rotation_xyzw"], sphere["local_mm"])
            centre_z = float(pose["position_mm"][2]) + offset[2]
            value = sphere["radius_mm"] - (centre_z - floor["floor_z_mm"])
            if peak is None or value > peak["compression_mm"]:
                peak = {"compression_mm": value, "geom": sphere["geom"], "at_s": time_s}
            if time_s >= settled_after_s:
                settled.append(value)
    return {
        "trace": str(trace_path), "frames": len(frames), "peak": peak,
        "settled_after_s": settled_after_s,
        "settled": ({"median_mm": statistics.median(settled), "max_mm": max(settled),
                     "min_mm": min(settled), "samples": len(settled)} if settled else None),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("traces", nargs="+", type=Path)
    parser.add_argument("--model", type=Path, required=True, help="the MJCF the traces ran")
    parser.add_argument("--settled-after", type=float, default=1.0)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    floor = floor_and_spheres(args.model)
    result = {"schema": SCHEMA, "floor": floor,
              "traces": [compression(t, floor, args.settled_after) for t in args.traces]}
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
