# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The drive proxy loop (ADR-710): screen drives and masses without a CAD rebuild.

A design change to a drive or a mass costs a full rebuild and an export
before anything can train on it. This edits the *exported* model instead:

- ``drives`` swaps a joint's drive for another datasheet drive. The clamp
  becomes its peak torque, the joint's damping its peak over its no-load
  speed (the straight torque-speed line ``lib.qdd`` models), the armature its
  rotor inertia times the gear ratio squared, the friction loss its
  back-drive torque, and the mass difference lands on the body that carries
  the housing (the joint's parent body, welded to it).
- ``move_mass`` moves kilograms, or a fraction of a body's mass, between two bodies (a drive moved inboard on
  a belt or pushrod, ADR-593's closed linkages, screened as mass only).
- ``mass_scale`` scales every body's mass and inertia.

Then it **screens** the edited model by replaying the task's gait reference
(ADR-706) as position targets with a virtual support on the root body: a PD
wrench toward the reference's base trajectory, so the replay measures what
the drives must deliver to follow the clip, not whether an open-loop clip
balances (it does not, record ``silent-leaf-7077``). ``support="full"``
also carries weight; ``support="attitude"`` holds only attitude and
horizontal position, so the legs carry all the weight; ``support="height"``
holds attitude and height and leaves the horizontal path free, so the stance
feet never fight a prescribed forward position; ``support="posture"`` holds
attitude only, so the legs carry all the weight *and* set the pace (ADR-711:
``attitude`` minus ``posture`` is what the prescribed path costs the
drives); ``support="swing"``
is ``full`` with gravity and contact switched off, so what is left is what
swinging the legs along the clip costs (their inertia, the drives' rotors and
the servo), the part a lighter distal leg buys back. It reports, per
drive, RMS torque over the datasheet rating, the share of steps at the peak
clamp, the peak needed, and the joint speed over the no-load speed.

A screen is a necessary condition, not a policy: a configuration that cannot
follow the clip inside its ratings while held will not track it free.

Like ``cadex_train.py`` it imports only the standard library at module scope;
``mujoco`` and ``numpy`` are imported where they are used.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

RPM = 2.0 * math.pi / 60.0
SUPPORTS = ("full", "attitude", "height", "posture", "swing")
#: Which translational axes each support holds (x forward, y lateral, z up);
#: every support holds attitude.
HELD_AXES = {"full": (1.0, 1.0, 1.0), "attitude": (1.0, 1.0, 0.0), "height": (0.0, 0.0, 1.0),
             "posture": (0.0, 0.0, 0.0), "swing": (1.0, 1.0, 1.0)}
#: The PD support per unit of gain: N/m, N*s/m, N*m/rad, N*m*s/rad.
SUPPORT_GAINS = (4000.0, 200.0, 400.0, 20.0)
#: A configuration holds the gait when every drive is at or under these.
#: Not a support: the screen that follows the clip exactly (``inverse``).
INVERSE = "inverse"
HOLD_RMS_OVER_RATED = 1.0
HOLD_PEAK_SHARE = 0.10
HOLD_SPEED_OVER_NO_LOAD = 1.0


class ProxyError(ValueError):
    pass


def drive_constants(spec: Mapping[str, Any]) -> dict[str, float]:
    """A datasheet drive as the model sees it, in SI at the joint."""

    for key in ("rated_torque_nm", "peak_torque_nm", "no_load_speed_rpm",
                "gear_ratio", "rotor_inertia_gcm2", "mass_g"):
        if not isinstance(spec.get(key), (int, float)) or float(spec[key]) <= 0.0:
            raise ProxyError(f"drive {spec.get('model', '?')!r} needs a positive {key}")
    if float(spec["rated_torque_nm"]) > float(spec["peak_torque_nm"]):
        raise ProxyError(f"drive {spec.get('model', '?')!r} is rated above its peak")
    peak = float(spec["peak_torque_nm"])
    omega = float(spec["no_load_speed_rpm"]) * RPM
    back = spec.get("back_drive_torque_nm")
    return {
        "peak_nm": peak,
        "rated_nm": float(spec["rated_torque_nm"]),
        "no_load_rad_s": omega,
        "damping": peak / omega,
        "armature": float(spec["rotor_inertia_gcm2"]) * 1e-7 * float(spec["gear_ratio"]) ** 2,
        "frictionloss": None if back is None else float(back),
        "mass_kg": float(spec["mass_g"]) / 1000.0,
    }


def identify_drive(library: Mapping[str, Mapping[str, Any]], peak_nm: float,
                   rated_nm: float | None) -> str | None:
    """The library drive whose peak (and rating, when known) a clamp matches."""

    hits = [key for key, spec in sorted(library.items())
            if abs(float(spec["peak_torque_nm"]) - peak_nm) < 1e-3
            and (rated_nm is None or abs(float(spec["rated_torque_nm"]) - rated_nm) < 1e-3)]
    return hits[0] if len(hits) == 1 else None


def _body(mujoco: Any, model: Any, name: str) -> int:
    index = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
    if index < 0:
        raise ProxyError(f"no body named {name!r} in the model")
    return index


def _add_mass(model: Any, body: int, kg: float, what: str) -> None:
    mass = float(model.body_mass[body])
    if mass + kg < -1e-9 or mass <= 0.0:
        raise ProxyError(f"{what} would leave body {body} with {mass + kg:.4f} kg")
    # The inertia scales with the mass about the body's own COM: the moved
    # mass is spread like the body's, an approximation the record states.
    model.body_inertia[body] *= max(mass + kg, 0.0) / mass
    model.body_mass[body] = max(mass + kg, 0.0)


def apply(mujoco: Any, model: Any, task: Mapping[str, Any], config: Mapping[str, Any],
          library: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Edit ``model`` in place to ``config``; one row per task action.

    Each row carries the action's drive after the edit: its peak, rating and
    no-load speed (``None`` where the model's drive is not in the library),
    which ``screen`` rates against.
    """

    unknown = set(config) - {"name", "drives", "move_mass", "mass_scale", "note"}
    if unknown:
        raise ProxyError(f"unknown configuration keys {sorted(unknown)}")
    actions = list(task["actions"])
    by_joint = {str(a["joint"]): a for a in actions}
    rows = []
    for action in actions:
        slot = int(action["index"])
        peak = abs(float(model.actuator_forcerange[slot][1]) * float(model.actuator_gear[slot][0]))
        rated = action.get("rated_effort")
        rated_nm = None if rated is None else float(rated) / 1000.0
        key = identify_drive(library, peak, rated_nm)
        no_load = None if key is None else drive_constants(library[key])["no_load_rad_s"]
        rows.append({"joint": str(action["joint"]), "slot": slot, "drive": key,
                     "peak_nm": peak, "rated_nm": rated_nm, "no_load_rad_s": no_load})
    row_of = {row["joint"]: row for row in rows}

    for joint, key in dict(config.get("drives", {})).items():
        if joint not in by_joint:
            raise ProxyError(f"{joint!r} is not a joint this task actuates")
        if key not in library:
            raise ProxyError(f"drive {key!r} is not in the drive library")
        row = row_of[joint]
        if row["drive"] is None:
            raise ProxyError(f"the drive on {joint!r} matches no library drive, so its "
                             "mass cannot be swapped")
        new = drive_constants(library[key])
        old = drive_constants(library[row["drive"]])
        slot = row["slot"]
        gear = float(model.actuator_gear[slot][0])
        model.actuator_forcerange[slot] = [-new["peak_nm"] / gear, new["peak_nm"] / gear]
        j = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint)
        dof = int(model.jnt_dofadr[j])
        model.dof_damping[dof] = new["damping"]
        model.dof_armature[dof] = new["armature"]
        if new["frictionloss"] is not None:
            model.dof_frictionloss[dof] = new["frictionloss"]
        housing = int(model.body_parentid[int(model.jnt_bodyid[j])])
        _add_mass(model, housing, new["mass_kg"] - old["mass_kg"], f"swapping {joint}'s drive")
        row.update(drive=key, peak_nm=new["peak_nm"], rated_nm=new["rated_nm"],
                   no_load_rad_s=new["no_load_rad_s"])

    for move in config.get("move_mass", ()):
        source = _body(mujoco, model, str(move["from"]))
        if ("kg" in move) == ("fraction" in move):
            raise ProxyError("move_mass takes one of kg or fraction (of the from body's mass)")
        kg = float(move["kg"]) if "kg" in move else float(move["fraction"]) * float(model.body_mass[source])
        if kg <= 0.0 or float(move.get("fraction", 0.0)) > 1.0:
            raise ProxyError("move_mass moves a positive mass, at most all of the from body's")
        _add_mass(model, source, -kg, f"moving {kg} kg")
        _add_mass(model, _body(mujoco, model, str(move["to"])), kg, f"moving {kg} kg")

    scale = float(config.get("mass_scale", 1.0))
    if scale <= 0.0:
        raise ProxyError("mass_scale must be positive")
    model.body_mass[1:] *= scale
    model.body_inertia[1:] *= scale
    return rows


def _root_body(mujoco: Any, model: Any) -> int:
    for j in range(model.njnt):
        if int(model.jnt_type[j]) == int(mujoco.mjtJoint.mjJNT_FREE):
            return int(model.jnt_bodyid[j])
    raise ProxyError("the model has no free joint, so there is no base to support")


def screen(mujoco: Any, np: Any, model: Any, task: Mapping[str, Any],
           rows: Sequence[Mapping[str, Any]], seed: int, *, support: str = "full",
           gain: float = 1.0, steps: int | None = None, fall_tilt_deg: float = 31.8,
           fall_height: float = 0.5) -> dict[str, Any]:
    """Replay the task's gait reference on ``model`` from a seeded start.

    The start is ``random.Random(seed).randrange(samples)`` — the trainer's
    distribution, not its exact draw stream. The run ends early when the
    root tilts past ``fall_tilt_deg`` or its COM drops below ``fall_height``
    of where it started.
    """

    if support not in SUPPORTS:
        raise ProxyError(f"support must be one of {SUPPORTS}")
    tracking = task.get("tracking")
    if not tracking:
        raise ProxyError("the task carries no gait reference to replay (ADR-706)")
    table, samples = tracking["table"], int(tracking["samples"])
    columns = list(tracking["channels"])[2:]  # the table holds these; the clock pair is computed
    actions = list(task["actions"])
    try:
        cols = [columns.index(f"q_{str(a['joint'])[2:]}_ref") for a in actions]
    except ValueError as exc:
        raise ProxyError(f"the reference does not pose every action: {exc}") from None
    reference = task["reference"]
    speed = float(reference["parameters"]["speed_m_s"])
    if support == "swing":  # edits this model: a screen is given a model of its own
        model.opt.gravity[:] = 0.0
        model.opt.disableflags |= int(mujoco.mjtDisableBit.mjDSBL_CONTACT)
    data = mujoco.MjData(model)
    mujoco.mj_setConst(model, data)  # subtree masses after apply's edits; uses data as scratch
    mujoco.mj_resetData(model, data)
    start = random.Random(seed).randrange(samples)
    if tracking.get("reset_qpos"):
        data.qpos[:] = tracking["reset_qpos"][start]
        data.qvel[:] = tracking["reset_qvel"][start]
    else:
        key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, task["episode"]["reset_keyframe"])
        mujoco.mj_resetDataKeyframe(model, data, key)
    mujoco.mj_forward(model, data)
    root = _root_body(mujoco, model)
    adr = int(model.jnt_qposadr[int(model.body_jntadr[root])])
    vadr = int(model.jnt_dofadr[int(model.body_jntadr[root])])
    p0 = data.qpos[adr:adr + 3].copy()
    z0 = float(data.subtree_com[root][2])
    weight = float(model.body_subtreemass[root]) * 9.81  # nominal, so a gravity-free diagnostic still divides
    kp, kd, kr, kdr = (g * gain for g in SUPPORT_GAINS)
    sub = int(task["episode"]["solver_steps_per_action"])
    total = int(steps if steps is not None else task["episode"]["max_steps"])
    slots = [int(r["slot"]) for r in rows]
    gear = np.array([float(model.actuator_gear[s][0]) for s in slots])
    dofs = [int(model.jnt_dofadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, r["joint"])])
            for r in rows]
    qadrs = [int(model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, r["joint"])])
             for r in rows]
    cos_tip = math.cos(math.radians(fall_tilt_deg))
    held = np.array(HELD_AXES[support])
    efforts, speeds, lift, push, misses = [], [], [], [], []
    tilt, ended = 0.0, None
    for k in range(total):
        sample = table[(start + k) % samples]
        targets = []
        for action, col, slot in zip(actions, cols, slots):
            target = min(max(float(sample[col]), float(action["low"])), float(action["high"]))
            data.ctrl[slot] = target * float(action["scale"])
            targets.append(target * float(action["scale"]))
        for _ in range(sub):
            if gain > 0.0:
                want = p0 + np.array([speed * data.time, 0.0, 0.0])
                force = kp * (want - data.qpos[adr:adr + 3]) - kd * (
                    data.qvel[vadr:vadr + 3] - np.array([speed, 0.0, 0.0]))
                force *= held  # a free axis is the legs' to carry
                err = np.zeros(3)
                mujoco.mju_quat2Vel(err, data.qpos[adr + 3:adr + 7], 1.0)
                data.xfrc_applied[root, :3] = force
                data.xfrc_applied[root, 3:] = -kr * err - kdr * data.qvel[vadr + 3:vadr + 6]
            mujoco.mj_step(model, data)
        q = data.qpos[adr + 3:adr + 7]
        up = 1.0 - 2.0 * (float(q[1]) ** 2 + float(q[2]) ** 2)
        tilt = max(tilt, math.degrees(math.acos(max(-1.0, min(1.0, up)))))
        efforts.append(np.array([float(data.actuator_force[s]) for s in slots]) * gear)
        speeds.append(np.array([abs(float(data.qvel[d])) for d in dofs]))
        # How far each joint is from the pose it was sent, after the step.
        misses.append(np.array([float(data.qpos[a]) for a in qadrs]) - np.array(targets))
        lift.append(float(data.xfrc_applied[root, 2]))
        push.append(float(data.xfrc_applied[root, 0]))
        if up < cos_tip or float(data.subtree_com[root][2]) < fall_height * z0:
            ended = k + 1
            break
    effort, speed_abs = np.array(efforts), np.array(speeds)
    rms = np.sqrt((effort ** 2).mean(axis=0))
    miss = np.degrees(np.sqrt((np.array(misses) ** 2).mean(axis=0)))
    drives = []
    for i, row in enumerate(rows):
        rated, peak, omega = row["rated_nm"], row["peak_nm"], row["no_load_rad_s"]
        drives.append({
            "joint": row["joint"], "drive": row["drive"],
            "rms_nm": float(rms[i]),
            "track_rms_deg": float(miss[i]),
            "rms_over_rated": None if not rated else float(rms[i]) / rated,
            "peak_share": float((np.abs(effort[:, i]) >= 0.99 * peak).mean()),
            "peak_needed_over_peak": float(np.abs(effort[:, i]).max()) / peak,
            "speed_over_no_load": None if not omega else float(speed_abs[:, i].max()) / omega,
        })
    interval = float(task["episode"]["control_interval_s"])
    travelled = float(data.qpos[adr] - p0[0])
    return {
        "seed": seed, "start_sample": start,
        "survived_s": (ended if ended is not None else total) * interval,
        "completed": ended is None,
        "max_tilt_deg": tilt,
        "support_lift_mean_pct_weight": 100.0 * statistics.fmean(lift) / weight,
        # The forward force the support spends holding the prescribed path:
        # its RMS, and its mean (negative: the support brakes the gait).
        "support_push_rms_pct_weight": 100.0 * math.sqrt(statistics.fmean(f * f for f in push)) / weight,
        "support_push_mean_pct_weight": 100.0 * statistics.fmean(push) / weight,
        "speed_mean_m_s": travelled / float(data.time) if data.time > 0.0 else 0.0,
        "mass_kg": float(model.body_subtreemass[root]),
        "drives": drives,
    }


def inverse(mujoco: Any, np: Any, model: Any, task: Mapping[str, Any],
            rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """What following the clip *exactly* asks of each drive (ADR-711).

    The held replays above measure a position servo, and the exported servo
    (kp about 60 N*m/rad on the cat) lags a 1.7 Hz stride by a large share of
    its swing, so their torques are what a lagging servo spends, not what the
    gait costs. This is floating-base inverse dynamics on the reference itself:

    - ``qvel`` and ``qacc`` are central differences of the clip's ``qpos``
      round the stride (``mj_differentiatePos``), and ``mj_inverse`` with
      contacts and constraints off gives every DOF's generalised force,
      gravity, the drives' armature and their torque-speed damping included
      (so comparing to the peak *is* comparing to the torque-speed line);
      joint friction loss is not counted;
    - the base's six rows must come from the feet the clip has down. A
      kinematic clip does not fall in its flight phases, so the base wrench
      of the samples with no foot down is spread evenly over the samples
      with one, which keeps the stride's impulse (gravity's above all) and
      is the standard duty-factor scaling of stance force;
    - each sample's wrench goes to its stance feet as point forces at the
      foot bodies' centres of mass (an exported body's frame is the
      assembly's origin, not the part), the least-norm solution, and each joint's torque
      is its generalised force less what those forces carry.

    Reported per drive as ``screen`` does, over the stride's samples, with
    ``peak_share`` the share of samples asking more than the peak; plus the
    base wrench the stance feet cannot supply (a residual, % weight), the
    share of stance samples with a foot pulling on the ground, and the share
    of the stride with no foot down.
    """

    reference = task["reference"]
    samples = int(reference["samples"])
    dt = float(reference["sample_dt_s"])
    lap = float(reference["parameters"]["speed_m_s"]) * dt * samples
    qpos = np.array(reference["qpos"], dtype=float)
    feet = sorted(reference["legs"])
    foot_body = {f: _body(mujoco, model, str(reference["legs"][f]["foot_body"])) for f in feet}
    down = {f: [bool(v) for v in reference["contact"][f]] for f in feet}
    root = _root_body(mujoco, model)
    vadr = int(model.jnt_dofadr[int(model.body_jntadr[root])])
    base = slice(vadr, vadr + 6)
    model.opt.disableflags |= int(mujoco.mjtDisableBit.mjDSBL_CONTACT) | int(
        mujoco.mjtDisableBit.mjDSBL_CONSTRAINT)
    data = mujoco.MjData(model)
    mujoco.mj_setConst(model, data)
    weight = float(model.body_subtreemass[root]) * float(np.linalg.norm(model.opt.gravity))

    def at(k: int) -> Any:
        laps, i = divmod(k, samples)
        row = qpos[i].copy()
        row[int(model.jnt_qposadr[int(model.body_jntadr[root])])] += laps * lap
        return row

    def velocity(a: Any, b: Any, h: float) -> Any:
        out = np.zeros(model.nv)
        mujoco.mj_differentiatePos(model, out, h, a, b)
        return out

    forces, stance, vels = [], [], []
    for k in range(samples):
        v_minus, v_plus = velocity(at(k - 1), at(k), dt), velocity(at(k), at(k + 1), dt)
        data.qpos[:] = at(k)
        data.qvel[:] = (v_minus + v_plus) / 2.0
        data.qacc[:] = (v_plus - v_minus) / dt
        mujoco.mj_inverse(model, data)
        forces.append(data.qfrc_inverse.copy())
        stance.append([f for f in feet if down[f][k]])
        vels.append(data.qvel.copy())
    forces = np.array(forces)
    flight = [k for k in range(samples) if not stance[k]]
    held = [k for k in range(samples) if stance[k]]
    if not held:
        raise ProxyError("the reference never puts a foot down, so nothing can carry the base")
    spread = forces[flight][:, base].sum(axis=0) / len(held) if flight else np.zeros(6)
    efforts, residual, pulling = [], [], 0
    dofs = [int(model.jnt_dofadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, r["joint"])])
            for r in rows]
    jac = np.zeros((3, model.nv))
    for k in held:
        data.qpos[:] = at(k)
        mujoco.mj_kinematics(model, data)
        mujoco.mj_comPos(model, data)
        jacs = []
        for f in stance[k]:
            mujoco.mj_jac(model, data, jac, None, data.xipos[foot_body[f]], foot_body[f])
            jacs.append(jac.copy())
        contact = np.vstack(jacs)  # (3 * feet) x nv
        wrench = forces[k][base] + spread
        f, *_ = np.linalg.lstsq(contact[:, base].T, wrench, rcond=None)
        residual.append(float(np.linalg.norm(contact[:, base].T @ f - wrench)))
        pulling += int(any(f[3 * i + 2] < 0.0 for i in range(len(stance[k]))))
        tau = forces[k] - contact.T @ f
        efforts.append(np.array([float(tau[d]) for d in dofs]))
    for k in flight:  # no foot down: the legs swing free, the base is spread above
        efforts.insert(k, np.array([float(forces[k][d]) for d in dofs]))
    effort = np.array(efforts)
    speed_abs = np.abs(np.array(vels))[:, dofs]
    rms = np.sqrt((effort ** 2).mean(axis=0))
    drives = []
    for i, row in enumerate(rows):
        rated, peak, omega = row["rated_nm"], row["peak_nm"], row["no_load_rad_s"]
        drives.append({
            "joint": row["joint"], "drive": row["drive"], "rms_nm": float(rms[i]),
            "mean_nm": float(effort[:, i].mean()),
            "rms_over_rated": None if not rated else float(rms[i]) / rated,
            "peak_share": float((np.abs(effort[:, i]) >= peak).mean()),
            "peak_needed_over_peak": float(np.abs(effort[:, i]).max()) / peak,
            "speed_over_no_load": None if not omega else float(speed_abs[:, i].max()) / omega,
        })
    return {
        "seed": None, "completed": True, "survived_s": samples * dt,
        "mass_kg": float(model.body_subtreemass[root]),
        "flight_share": len(flight) / samples,
        "pulling_share": pulling / len(held),
        "residual_mean_pct_weight": 100.0 * statistics.fmean(residual) / weight,
        "drives": drives,
    }


def summarise(name: str, runs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Medians over seeds per drive, the worst drive, and the verdict."""

    def med(values):
        values = [v for v in values if v is not None]
        return statistics.median(values) if values else None

    drives = []
    for i, first in enumerate(runs[0]["drives"]):
        drives.append({"joint": first["joint"], "drive": first["drive"],
                       **{k: med([r["drives"][i].get(k) for r in runs])
                          for k in ("rms_nm", "track_rms_deg", "rms_over_rated", "peak_share",
                                    "peak_needed_over_peak", "speed_over_no_load")}})
    rated = [d for d in drives if d["rms_over_rated"] is not None]
    worst = max(rated, key=lambda d: d["rms_over_rated"]) if rated else None
    completed = all(r["completed"] for r in runs)
    holds = completed and all(
        (d["rms_over_rated"] is None or d["rms_over_rated"] <= HOLD_RMS_OVER_RATED)
        and d["peak_share"] <= HOLD_PEAK_SHARE
        and (d["speed_over_no_load"] is None or d["speed_over_no_load"] <= HOLD_SPEED_OVER_NO_LOAD)
        for d in drives)
    return {
        "name": name, "seeds": [r["seed"] for r in runs],
        "mass_kg": runs[0]["mass_kg"], "completed": completed,
        "completed_seeds": sum(1 for r in runs if r["completed"]),
        "survived_s": med([r["survived_s"] for r in runs]),
        **{key: med([r.get(key) for r in runs])
           for key in ("max_tilt_deg", "support_lift_mean_pct_weight", "support_push_rms_pct_weight",
                       "speed_mean_m_s", "flight_share", "pulling_share", "residual_mean_pct_weight")},
        "worst_joint": None if worst is None else worst["joint"],
        "worst_rms_over_rated": None if worst is None else worst["rms_over_rated"],
        "drives_over_rated": sum(1 for d in rated if d["rms_over_rated"] > HOLD_RMS_OVER_RATED),
        "peak_share_max": max(d["peak_share"] for d in drives),
        "speed_over_no_load_max": max((d["speed_over_no_load"] for d in drives
                                       if d["speed_over_no_load"] is not None), default=None),
        "holds": holds,
        "drives": drives,
    }


def markdown(rows: Sequence[Mapping[str, Any]], joints: Sequence[str]) -> str:
    """The sweep as a table: per configuration, the named joints' numbers."""

    head = ["config", "support", "kg", "completes", "survives s", "worst RMS/rated", "over rated",
            "max at-peak", "max speed/no-load", "lift % wt", "push RMS % wt", "m/s",
            "unsupplied % wt"]
    head += [f"{j} RMS/rated · at-peak" for j in joints]
    head.append("holds")
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]

    def f(v, digits=2):
        return "–" if v is None else f"{v:.{digits}f}"

    for row in rows:
        by = {d["joint"]: d for d in row["drives"]}
        cells = [row["name"], row["support"], f(row["mass_kg"], 1),
                 f"{row['completed_seeds']}/{len(row['seeds'])}", f(row["survived_s"], 1),
                 f(row["worst_rms_over_rated"]) + f" ({row['worst_joint']})",
                 str(row["drives_over_rated"]), f(row["peak_share_max"]),
                 f(row["speed_over_no_load_max"]), f(row["support_lift_mean_pct_weight"], 1),
                 f(row.get("support_push_rms_pct_weight"), 1), f(row.get("speed_mean_m_s")),
                 f(row.get("residual_mean_pct_weight"), 1)]
        cells += [f"{f(by[j]['rms_over_rated'])} · {f(by[j]['peak_share'])}" for j in joints]
        cells.append("**yes**" if row["holds"] else "no")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def load(bundle: str) -> tuple[dict[str, Any], bytes]:
    """The task and its model's bytes, resolved as ``cadex_train.load_bundle`` does."""

    path = Path(bundle).resolve()
    task = json.loads(path.read_text(encoding="utf-8"))
    relative = Path(str(task["model"]["path"]))
    for candidate in (path.parent.parent / relative, path.parent / relative.name):
        if candidate.exists():
            return task, candidate.read_bytes()
    raise ProxyError(f"the model {relative} is not beside {path}")


def sweep(task: Mapping[str, Any], xml: bytes, configs: Sequence[Mapping[str, Any]],
          library: Mapping[str, Mapping[str, Any]], seeds: Sequence[int],
          supports: Sequence[str], **options: Any) -> list[dict[str, Any]]:
    import mujoco
    import numpy as np

    out = []
    for config in configs:
        for support in supports:
            runs = []
            for seed in ([None] if support == INVERSE else seeds):
                model = mujoco.MjModel.from_xml_string(xml.decode("utf-8"))
                rows = apply(mujoco, model, task, config, library)
                runs.append(inverse(mujoco, np, model, task, rows) if support == INVERSE else
                            screen(mujoco, np, model, task, rows, seed, support=support, **options))
            row = summarise(str(config.get("name", "config")), runs)
            row["support"] = support
            row["config"] = dict(config)
            out.append(row)
            print(json.dumps({k: row[k] for k in ("name", "support", "mass_kg", "survived_s",
                                                  "worst_joint", "worst_rms_over_rated",
                                                  "peak_share_max", "holds")}), flush=True)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("bundle", help="a cadex-training-task-v1 bundle with a gait reference")
    parser.add_argument("--drives", required=True, help="drive library JSON: key -> datasheet spec")
    parser.add_argument("--configs", required=True, help="JSON list of configurations")
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(1001, 1011)))
    parser.add_argument("--support", nargs="+", default=["full"], choices=SUPPORTS + (INVERSE,),
                        help=f"held replays, or {INVERSE!r}: inverse dynamics on the clip itself")
    parser.add_argument("--gain", type=float, default=1.0)
    parser.add_argument("--joints", nargs="*", default=[], help="joints to tabulate")
    parser.add_argument("--reference", help="a cadex-gait-clip-v1 JSON (CadexGait.generate on the "
                        "bundle's model) the inverse screen follows instead of the bundle's clip")
    parser.add_argument("--out", required=True, help="writes OUT.json and OUT.md")
    args = parser.parse_args(argv)
    task, xml = load(args.bundle)
    library = json.loads(Path(args.drives).read_text(encoding="utf-8"))
    library = {k: v for k, v in library.items() if not k.startswith("_")}
    configs = json.loads(Path(args.configs).read_text(encoding="utf-8"))
    if args.reference:
        if set(args.support) != {INVERSE}:
            parser.error("--reference replaces the clip only the inverse screen reads")
        task = dict(task, reference=json.loads(Path(args.reference).read_text(encoding="utf-8")))
    try:
        rows = sweep(task, xml, configs, library, args.seeds, args.support, gain=args.gain)
    except ProxyError as exc:
        print(f"cadex_proxy: {exc}", file=sys.stderr)
        return 2
    Path(args.out + ".json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    Path(args.out + ".md").write_text(markdown(rows, args.joints), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
