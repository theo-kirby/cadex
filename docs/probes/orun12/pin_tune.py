"""The hind paw pin's damping and stops, measured on the trained model (orun12 Q2, O9).

usage: pixi run python docs/probes/orun12/pin_tune.py MODEL_XML

A candidate for O1's pin tuning (``pin_damp``, the pin's limit time
constant and impedance), measured before it is trained on. It loads the
run's MJCF and, for each candidate, plays the pin alone: every other degree
of freedom is held at the keyframe pose each step, gravity and contacts are
off, and the paw's own inertia about the pin is the model's (``M`` of the
pin's dof with the rest held). Two cases per candidate, per hind leg:

- ``snap``: the pin starts at its spring rest moving 2,000 deg/s toward its
  toes-up stop, the worst rate ``paw_pin.py`` reads on the v07 traces. It
  reports how far it runs past the stop, its rate 20 ms later (one trace
  frame).
- ``loaded``: the pin starts at rest at its spring rest under a constant
  toes-up torque (0.5, 1 and 2 N*m; the floor's push on the paw in
  stance). It reports the peak rate and how far it runs past the stop.

The damping ratio ``zeta = c / (2 sqrt(k I))`` is printed alongside. Nothing
is changed on the project.
"""

from __future__ import annotations

import math
import sys

import mujoco
import numpy as np

SNAP_DEG_S = 2000.0
LOADS = (0.5, 1.0, 2.0)   # N*m toes-up on the pin: the floor under a share of the cat's weight
# (label, damping N*m*s/rad, solreflimit time constant s, solimplimit dmin, dmax)
NMM_PER_DEG = 1e-3 * 180.0 / math.pi   # N*mm*(s) per deg -> N*m*(s) per rad
CANDIDATES = (
    ("now: pin_damp 0.4, tau 4 ms", 0.4 * NMM_PER_DEG, 0.004, 0.9, 0.95),
    ("pin_damp 1.5", 1.5 * NMM_PER_DEG, 0.004, 0.9, 0.95),
    ("pin_damp 3.0", 3.0 * NMM_PER_DEG, 0.004, 0.9, 0.95),
    ("pin_damp 5.0 (max)", 5.0 * NMM_PER_DEG, 0.004, 0.9, 0.95),
    ("pin_damp 0.4, stop impedance 0.99", 0.4 * NMM_PER_DEG, 0.004, 0.99, 0.999),
    ("pin_damp 3.0, stop impedance 0.99", 3.0 * NMM_PER_DEG, 0.004, 0.99, 0.999),
)


def play(model, data, dof, qadr, q0, start, rate, steps, torque=0.0):
    data.qfrc_applied[:] = 0.0
    data.qfrc_applied[dof] = torque
    data.qpos[:] = q0
    data.qvel[:] = 0.0
    data.qpos[qadr] = start
    data.qvel[dof] = rate
    out = []
    for _ in range(steps):
        held_q, held_v = data.qpos[qadr], data.qvel[dof]
        data.qpos[:] = q0
        data.qvel[:] = 0.0
        data.qpos[qadr], data.qvel[dof] = held_q, held_v
        mujoco.mj_step(model, data)
        out.append((float(data.qpos[qadr]), float(data.qvel[dof])))
    data.qfrc_applied[:] = 0.0
    return out


def main(path: str) -> None:
    model = mujoco.MjModel.from_xml_path(path)
    model.opt.gravity[:] = 0.0
    model.opt.disableflags |= int(mujoco.mjtDisableBit.mjDSBL_CONTACT)
    data = mujoco.MjData(model)
    if model.nkey:
        mujoco.mj_resetDataKeyframe(model, data, 0)
    mujoco.mj_forward(model, data)
    q0 = data.qpos.copy()
    dt = model.opt.timestep
    print(f"timestep {dt * 1e3:.1f} ms")
    print("| leg | candidate | zeta | I g*cm^2 | snap: past stop deg | snap: rate 20 ms on deg/s | "
          + " | ".join(f"{t:g} N*m: peak deg/s / past stop deg" for t in LOADS) + " |")
    print("|---|---|---|---|---|---|" + "---|" * len(LOADS))
    for leg in ("l", "r"):
        j = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "j_pawpin_" + leg)
        dof, qadr = int(model.jnt_dofadr[j]), int(model.jnt_qposadr[j])
        k, ref = float(model.jnt_stiffness[j]), float(model.qpos_spring[qadr])
        lo, hi = (float(v) for v in model.jnt_range[j])
        mujoco.mj_forward(model, data)
        full = np.zeros((model.nv, model.nv))
        mujoco.mj_fullM(model, data, full)
        inertia = float(full[dof, dof])
        # toes-up is +y on the left and -y on the right (the right's axis is -y)
        up, stop = (1.0, hi) if leg == "l" else (-1.0, lo)
        for label, c, tau, dmin, dmax in CANDIDATES:
            model.dof_damping[dof] = c
            model.jnt_solref[j][:] = (tau, 1.0)
            model.jnt_solimp[j][:2] = (dmin, dmax)
            zeta = c / (2.0 * math.sqrt(k * inertia))
            snap = play(model, data, dof, qadr, q0, ref, up * math.radians(SNAP_DEG_S), int(0.3 / dt))
            past = max(0.0, max(up * (q - stop) for q, _ in snap))
            frame = abs(snap[int(round(0.02 / dt)) - 1][1])
            cells = []
            for torque in LOADS:
                run = play(model, data, dof, qadr, q0, ref, 0.0, int(0.3 / dt), up * torque)
                peak = max(abs(v) for _, v in run)
                over = max(0.0, max(up * (q - stop) for q, _ in run))
                cells.append(f"{math.degrees(peak):.0f} / {math.degrees(over):.1f}")
            print(f"| {leg.upper()}H | {label} | {zeta:.2f} | {inertia * 1e7:.1f} | {math.degrees(past):.1f} | "
                  f"{math.degrees(frame):.0f} | " + " | ".join(cells) + " |")
        model.dof_damping[dof] = CANDIDATES[0][1]


if __name__ == "__main__":
    main(sys.argv[1])
