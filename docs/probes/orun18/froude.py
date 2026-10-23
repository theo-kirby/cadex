"""orun18 B2: hind hip height at the model's first keyframe, and a speed's Froude number.

    pixi run python docs/probes/orun18/froude.py MODEL.xml JOINT[,JOINT] SPEED_M_S [SPEED_M_S ...]

Hip height is each named hind hip joint's anchor height above the lowest
point of the collision geoms in that joint's body subtree (the foot), at
``key_qpos[0]``, averaged over the joints. A geom's lowest point is read
from its local AABB's corners in world frame. Fr = v^2 / (g h) (Alexander &
Jayes 1983), the measure equal gaits share across sizes.
"""

from __future__ import annotations

import itertools
import json
import sys

import mujoco as mj
import numpy as np


def subtree(model, root: int) -> list[int]:
    return [b for b in range(model.nbody) if b == root or _under(model, b, root)]


def _under(model, body: int, root: int) -> bool:
    while body > 0:
        body = int(model.body_parentid[body])
        if body == root:
            return True
    return False


def lowest(model, data, bodies: list[int]) -> float:
    low = np.inf
    for g in range(model.ngeom):
        if int(model.geom_bodyid[g]) not in bodies or not (model.geom_contype[g] or model.geom_conaffinity[g]):
            continue
        center, half = model.geom_aabb[g][:3], model.geom_aabb[g][3:]
        rot = data.geom_xmat[g].reshape(3, 3)
        for signs in itertools.product((-1.0, 1.0), repeat=3):
            low = min(low, float((data.geom_xpos[g] + rot @ (center + np.array(signs) * half))[2]))
    return low


def main(argv):
    model = mj.MjModel.from_xml_path(argv[0])
    data = mj.MjData(model)
    data.qpos[:] = model.key_qpos[0] if model.nkey else model.qpos0
    mj.mj_kinematics(model, data)
    rows = {}
    for name in argv[1].split(","):
        j = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, name)
        if j < 0:
            raise SystemExit(f"no joint {name}")
        anchor = float(data.xanchor[j][2])
        rows[name] = {"anchor_z_m": anchor, "foot_low_z_m": lowest(model, data, subtree(model, int(model.jnt_bodyid[j])))}
    h = float(np.mean([r["anchor_z_m"] - r["foot_low_z_m"] for r in rows.values()]))
    out = {"model": argv[0], "joints": rows, "hip_height_m": h,
           "froude": {f"{float(v):.3f}": float(v) ** 2 / (9.81 * h) for v in argv[2:]}}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
