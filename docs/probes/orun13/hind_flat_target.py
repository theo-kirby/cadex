"""orun13 (O2, O7): where leo's rigid hind foot is flat, in hind_flat's and heel_pitch's readings.

    pixi run python docs/probes/orun13/hind_flat_target.py RUN/train/gallop-task.json

``hind_flat`` pays a hind paw in contact for ``2 qw qy`` of its body's world
quaternion (the paw's pitch sine) near a target, 0.588 (36 deg), which was
feline v07's sprung paw lying flat. ``heel_pitch`` pays the metatarsus's
world pitch, computed from observed joints, near 0 deg (full at 10 or less).
On leo the paw, heel and metatarsus are one rigid foot, so both read the
same thing: how far the sole is from flat.

From each clip sample, and that sample held under its drives for 2 s (the
push-rod loop is an equality, so only loop-closed poses move the paw), it reads
the paw's ``2 qw qy``, the heel_pitch angle from the bundle's own
expression terms, and the sole tilt: the paw's lowest collision point
minus the heel's (mm; 0 is flat, positive is toes up). The flat sole is
where the tilt crosses 0; the readings there are the targets.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import mujoco
import numpy as np

CHEST_Z_DEG = 63.9  # heel_pitch's offset in leo's script


def lowest(model, data, body):
    b = model.body(body).id
    z = []
    for g in range(model.ngeom):
        if int(model.geom_bodyid[g]) != b or not (model.geom_contype[g] or model.geom_conaffinity[g]):
            continue
        p, R, s = data.geom_xpos[g], data.geom_xmat[g].reshape(3, 3), model.geom_size[g]
        t = int(model.geom_type[g])
        if t == mujoco.mjtGeom.mjGEOM_SPHERE:
            z.append(p[2] - s[0])
        elif t == mujoco.mjtGeom.mjGEOM_CAPSULE:
            z.append(p[2] - abs(R[2, 2]) * s[1] - s[0])
        elif t == mujoco.mjtGeom.mjGEOM_BOX:
            z.append(p[2] - float(np.abs(R[2, :]) @ s[:3]))
    return 1000 * min(z)


def deg(model, data, joint):
    return math.degrees(float(data.qpos[model.jnt_qposadr[model.joint(joint).id]]))


def geoms_in(model, data, frame, body):
    """A body's collision geoms in another body's frame (rigid foot: constant)."""
    Rf, pf = data.xmat[model.body(frame).id].reshape(3, 3), data.xpos[model.body(frame).id]
    b = model.body(body).id
    out = []
    for g in range(model.ngeom):
        if int(model.geom_bodyid[g]) != b or not (model.geom_contype[g] or model.geom_conaffinity[g]):
            continue
        out.append((int(model.geom_type[g]), Rf.T @ (data.geom_xpos[g] - pf),
                    Rf.T @ data.geom_xmat[g].reshape(3, 3), model.geom_size[g].copy()))
    return out


def low(geoms, R):
    z = []
    for t, p, Rg, s in geoms:
        pz, Rz = (R @ p)[2], (R @ Rg)[2, :]
        if t == mujoco.mjtGeom.mjGEOM_SPHERE:
            z.append(pz - s[0])
        elif t == mujoco.mjtGeom.mjGEOM_CAPSULE:
            z.append(pz - abs(Rz[2]) * s[1] - s[0])
        elif t == mujoco.mjtGeom.mjGEOM_BOX:
            z.append(pz - float(np.abs(Rz) @ s[:3]))
    return 1000 * min(z)


def main(argv):
    bundle = Path(argv[0]).expanduser()
    task = json.loads(bundle.read_text())
    model = mujoco.MjModel.from_xml_string((bundle.parent / Path(task["model"]["path"]).name).read_text())
    data = mujoco.MjData(model)
    tr = task["tracking"]
    for side in ("l", "r"):
        paw, heel = "c_paw_h" + side, "c_heel_h" + side
        # Heel and paw geoms in the paw body's frame, from each clip sample:
        # the spread says whether the foot is rigid.
        shapes, spread = None, 0.0
        for qpos in tr["reset_qpos"]:
            data.qpos[:] = qpos
            mujoco.mj_forward(model, data)
            here = geoms_in(model, data, paw, heel)
            if shapes is None:
                shapes = (geoms_in(model, data, paw, paw), here)
            spread = max(spread, max(float(np.linalg.norm(a[1] - b[1])) for a, b in zip(shapes[1], here)))
        print(f"hind {side.upper()}: heel geoms move {1000 * spread:.2f} mm in the paw frame over the clip samples")
        # The paw body pitched by theta about world y, no roll or yaw:
        # 2 qw qy = sin(theta); heel_pitch, a metatarsus pitch, differs by a constant.
        rows = []
        for th in np.arange(-90.0, 90.01, 0.5):
            c, s_ = math.cos(math.radians(th)), math.sin(math.radians(th))
            R = np.array([[c, 0, s_], [0, 1, 0], [-s_, 0, c]])
            rows.append((th, low(shapes[0], R) - low(shapes[1], R)))
        flat = [(a, b) for a, b in zip(rows, rows[1:]) if a[1] * b[1] <= 0]
        for a, b in flat:
            th = a[0] + a[1] / (a[1] - b[1]) * (b[0] - a[0])
            print(f"  sole flat at paw pitch {th:+.1f} deg: 2 qw qy = {math.sin(math.radians(th)):+.3f} "
                  f"(hind_flat's target 0.588 = {math.degrees(math.asin(0.588)):+.1f} deg)")
        for th, tilt in rows[::20]:
            print(f"  paw pitch {th:+6.1f} deg (2qwqy {math.sin(math.radians(th)):+.3f}): tilt {tilt:+6.1f} mm")
        # And heel_pitch at the flat sole, from the loop-closed clip samples:
        # its reading against the paw body's pitch is a constant offset.
        offs = []
        for qpos in tr["reset_qpos"]:
            data.qpos[:] = qpos
            mujoco.mj_forward(model, data)
            _, _, meta, _ = reading(model, data, side)
            R = data.xmat[model.body(paw).id].reshape(3, 3)
            offs.append(meta - math.degrees(math.atan2(R[0, 2], R[0, 0])))
        print(f"  heel_pitch minus paw pitch over the clip samples: median {np.median(offs):+.1f} deg "
              f"[{min(offs):+.1f}, {max(offs):+.1f}]")
        for (a, b) in flat:
            th = a[0] + a[1] / (a[1] - b[1]) * (b[0] - a[0])
            print(f"  so the sole is flat at heel_pitch {th + np.median(offs):+.1f} deg")


def reading(model, data, side):
    paw, heel = "c_paw_h" + side, "c_heel_h" + side
    w, _, y, _ = data.xquat[model.body(paw).id]
    imu = data.xquat[model.body("c_imu").id]
    chest = math.degrees(math.asin(2 * (imu[0] * imu[2] - imu[1] * imu[3])))
    spine = deg(model, data, "j_spine")
    if side == "l":
        meta = chest + 2 * spine + deg(model, data, "j_hip_l") - deg(model, data, "j_knee_l") \
            + deg(model, data, "j_hock_l") + CHEST_Z_DEG
    else:
        meta = chest + 2 * spine - deg(model, data, "j_hip_r") + deg(model, data, "j_knee_r") \
            - deg(model, data, "j_hock_r") + CHEST_Z_DEG
    return (deg(model, data, "j_hock_" + side), 2 * w * y, meta,
            lowest(model, data, paw) - lowest(model, data, heel))




if __name__ == "__main__":
    main(sys.argv[1:])
