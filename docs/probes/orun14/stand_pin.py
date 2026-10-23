"""orun14 B1: leo v03's stand on the free paw pin, and the clip's spine coupling.

usage: stand_pin.py TASK.json MODEL.xml

Holds the keyframe pose for 3 s on every drive (orun13's stand_hold.py) and
reports the chest frame's height (scan_4's origin), the body pitch, each hind
paw pin's angle and speed, and the hind heel, pad and toe heights. Then reads
the bundled gallop clip: j_spine2 against j_spine, and the clip's pin samples.
"""
import json
import sys

import mujoco
import numpy as np

t = json.load(open(sys.argv[1]))
m = mujoco.MjModel.from_xml_path(sys.argv[2])
d = mujoco.MjData(m)


def jid(n):
    return mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n)


def bid(n):
    return mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, n)


def lowest_mm(body):
    """The lowest point of a body's collision geoms (AABB, world z), mm."""
    b = bid(body)
    zs = [d.geom_xpos[g][2] - m.geom_rbound[g] if m.geom_type[g] != mujoco.mjtGeom.mjGEOM_CAPSULE
          else d.geom_xpos[g][2] - abs(d.geom_xmat[g].reshape(3, 3)[2, 2]) * m.geom_size[g][1] - m.geom_size[g][0]
          for g in range(m.ngeom) if m.geom_bodyid[g] == b and m.geom_contype[g]]
    return 1000 * min(zs) if zs else float("nan")


PINS = {k: jid("j_pawpin_" + k) for k in ("l", "r")}
assert min(PINS.values()) >= 0, "no j_pawpin_* joints: not a v03 model"
for k, j in PINS.items():
    print("j_pawpin_%s range deg" % k, np.round(np.degrees(m.jnt_range[j]), 1),
          "damping", m.dof_damping[m.jnt_dofadr[j]], "frictionloss", m.dof_frictionloss[m.jnt_dofadr[j]],
          "stiffness", m.jnt_stiffness[j])

mujoco.mj_resetDataKeyframe(m, d, 0)
for i in range(m.nu):
    j = m.actuator_trnid[i, 0]
    d.ctrl[i] = d.qpos[m.jnt_qposadr[j]] if m.actuator_trntype[i] == 0 else 0.0
mujoco.mj_forward(m, d)
chest = bid("c_chest_frame")
print("keyframe chest z mm %.1f" % (1000 * d.xpos[chest][2]))
peak_pin = {k: 0.0 for k in PINS}
rows = []
for k in range(int(3.0 / m.opt.timestep)):
    mujoco.mj_step(m, d)
    for s, j in PINS.items():
        peak_pin[s] = max(peak_pin[s], abs(np.degrees(d.qvel[m.jnt_dofadr[j]])))
    if k % int(0.5 / m.opt.timestep) == int(0.5 / m.opt.timestep) - 1:
        pitch = np.degrees(np.arcsin(2 * (d.qpos[3] * d.qpos[5] - d.qpos[4] * d.qpos[6])))
        pins = [np.degrees(d.qpos[m.jnt_qposadr[j]]) for j in PINS.values()]
        rows.append((round((k + 1) * m.opt.timestep, 1), round(1000 * d.xpos[chest][2], 1), round(pitch, 1),
                     [round(p, 1) for p in pins]))
for r in rows:
    print("t %.1f s  chest z %.1f mm  pitch %.1f deg  pin l/r deg %s" % r)
print("NaN", bool(np.isnan(d.qpos).any()), " pin peak speed l/r deg/s %.0f / %.0f" % (peak_pin["l"], peak_pin["r"]))
for s in ("hl", "hr"):
    print("%s lowest mm: heel %.1f  paw %.1f  claws/toes %.1f" % (
        s, lowest_mm("c_heel_" + s), lowest_mm("c_paw_" + s), lowest_mm("c_claws_" + s)))

r = t["reference"]
J = r["joints"]
a = np.degrees(np.asarray(r["joint_angles_rad"], float))
i1, i2 = J.index("j_spine"), J.index("j_spine2")
print("clip", a.shape, "j_spine %.2f..%.2f deg" % (a[:, i1].min(), a[:, i1].max()),
      "max |j_spine2 - j_spine| %.3f deg" % np.abs(a[:, i2] - a[:, i1]).max())
for k in ("l", "r"):
    n = "j_pawpin_" + k
    if n in J:
        print("clip %s %.1f..%.1f deg" % (n, a[:, J.index(n)].min(), a[:, J.index(n)].max()))
    else:
        print("clip carries no %s (passive, not referenced)" % n)
