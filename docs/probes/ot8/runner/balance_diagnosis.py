# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Why does a free-base design fail its own bounded smoke?

The ot8 charter's G4 asks one question about a machine whose ordinary
``cadex smoke`` fails, and it asks it in three parts: is this a geometry or
export mismatch, a defect in the design, or behaviour the design declares and
cannot produce without feedback control it does not have? Arguing the answer
is worthless; each part is a measurement, and this is that measurement.

It reads a retained model, the task beside it and the smoke receipt that
failed, and it changes nothing: no rebuild, no re-acceptance, no controller,
no training. Every number below comes from the model's own mass properties,
from MuJoCo's own contact set at the accepted pose, or from replaying the
same zero-command rollout the smoke ran.

What it measures, and why each one separates a cause from a cause:

* **the support set** -- the floor contacts at the accepted pose. Two contact
  points are a *line*, not a polygon: a machine resting on one line has no
  static margin about it at all, whatever its mass distribution. The line is
  found from the contacts rather than from any part's name, so the tool has
  no idea what a wheel is.
* **the lever arm and the holding torque** -- how far the whole-body centre of
  mass lies off that line, and the gravity torque that offset makes. Against
  the torque the design's own actuators declare about the same axis, this
  separates *cannot hold itself up* (a design defect: the motors are too
  small, or the mass is too far out) from *could hold itself up if something
  commanded it to* (a control requirement).
* **the unstable eigenvalue** -- ``sqrt(m g h / I)`` about that line, the rate
  at which the free response departs -- the rigid fixed-pivot idealisation,
  so a model that also rolls and pivots at its axles departs in the same rate
  class rather than at the same number. Against the replayed rollout's
  measured growth it says the fall is the model's own physics; against the
  task's declared control interval it says how many commands a controller
  would get per e-fold, which is the one number a missing control contract
  must carry.
* **the standing contact depth** -- MuJoCo's contact spring is a spring, so a
  machine at rest sinks into the floor by a load-dependent depth that is not
  a geometric intersection. Measured at the accepted pose and under scaled
  load, it says whether a floor-penetration breach is an intersection or a
  compliance.

    pixi run python docs/probes/ot8/runner/balance_diagnosis.py MODEL.xml \\
        --task TASK.json --smoke smoke.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

#: MJCF speaks metres and newton-metres; a Cadex receipt speaks millimetres
#: and newton-millimetres, and the report is read beside the receipt.
MM_PER_M = 1000.0
NMM_PER_NM = 1000.0

#: The floor the engine writes into every exported model.
FLOOR_GEOM = "environment/floor"

#: Contact points this far apart in the horizontal plane are one point, and
#: a support set whose points all lie this close to one line is a line. A
#: millimetre is far below any real wheelbase and far above solver noise.
COLLINEAR_TOLERANCE_M = 1.0e-3

#: A torque margin at or under this cannot be called control authority: the
#: motors are inside a factor of two of the gravity torque they would have to
#: oppose just to stand still, and the design, not the missing controller, is
#: what the smoke is reporting.
AUTHORITY_MARGIN = 2.0

#: Loads the standing contact depth is remeasured at, as multiples of the
#: design's own mass. They say whether a floor breach is compliance (depth
#: follows load) or an intersection (depth does not).
LOAD_SCALES = (0.25, 0.5, 1.0, 2.0, 4.0)


def _mujoco():
    """Imported here so the module can be read and tested for its arithmetic
    without a MuJoCo in the interpreter."""

    import mujoco  # noqa: PLC0415 - deliberately deferred

    return mujoco


def digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _sub(a, b):
    return [x - y for x, y in zip(a, b)]


def support_set(model, data) -> dict:
    """The floor contacts at the pose the data is currently at.

    Returns the contact points, the shape of what they support on -- a point,
    a line or a polygon -- and, for a line, its horizontal direction. The
    direction is the axis the machine is free to topple about, and the whole
    diagnosis hangs off it.
    """

    mujoco = _mujoco()
    floor = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, FLOOR_GEOM)
    points, geoms = [], []
    for index in range(data.ncon):
        contact = data.contact[index]
        if floor not in (contact.geom1, contact.geom2):
            continue
        other = contact.geom2 if contact.geom1 == floor else contact.geom1
        points.append([float(v) for v in contact.pos])
        geoms.append(str(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, int(other)) or ""))
    if not points:
        return {"kind": "none", "points": [], "geoms": []}
    plane_z = sum(point[2] for point in points) / len(points)
    unique = []
    for point in points:
        if not any(math.dist(point[:2], seen[:2]) <= COLLINEAR_TOLERANCE_M for seen in unique):
            unique.append(point)
    result = {
        "points_mm": [[v * MM_PER_M for v in point] for point in points],
        "geoms": geoms,
        "plane_z_mm": plane_z * MM_PER_M,
        "distinct_points": len(unique),
    }
    if len(unique) < 2:
        result["kind"] = "point"
        return result
    # The longest span fixes the candidate line; anything off it makes a polygon.
    pairs = [(a, b) for i, a in enumerate(unique) for b in unique[i + 1:]]
    first, second = max(pairs, key=lambda pair: math.dist(pair[0][:2], pair[1][:2]))
    span = _sub(second[:2], first[:2])
    length = math.hypot(*span)
    direction = [span[0] / length, span[1] / length]
    normal = [-direction[1], direction[0]]
    off_line = max(abs(_dot(_sub(point[:2], first[:2]), normal)) for point in unique)
    result.update(
        kind="line" if off_line <= COLLINEAR_TOLERANCE_M else "polygon",
        span_mm=length * MM_PER_M,
        direction=direction,
        normal=normal,
        off_line_mm=off_line * MM_PER_M,
    )
    return result


def inertia_about(model, data, point, axis) -> float:
    """The whole model's moment of inertia about the world line through
    ``point`` along the unit ``axis``, by the parallel-axis theorem over every
    body's own inertial frame."""

    inertia = 0.0
    for body in range(1, model.nbody):
        mass = float(model.body_mass[body])
        if mass == 0.0:
            continue
        position = [float(v) for v in data.xipos[body]]
        rotation = [float(v) for v in data.ximat[body]]
        principal = [float(v) for v in model.body_inertia[body]]
        # axis expressed in the body's inertial frame: R^T a, R row-major 3x3
        local = [sum(rotation[row * 3 + column] * axis[row] for row in range(3)) for column in range(3)]
        inertia += sum(principal[k] * local[k] ** 2 for k in range(3))
        offset = _sub(position, point)
        perpendicular = _sub(offset, [_dot(offset, axis) * component for component in axis])
        inertia += mass * _dot(perpendicular, perpendicular)
    return inertia


def actuator_authority(model, axis) -> dict:
    """The torque the design's own actuators declare about ``axis``.

    Only an actuator driving a hinge whose axis is parallel to the topple
    line can oppose the gravity torque about it, so an actuator pointing
    elsewhere contributes nothing and is listed rather than counted.
    """

    mujoco = _mujoco()
    counted, ignored = [], []
    total = 0.0
    for act in range(model.nu):
        name = str(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, act) or "")
        if int(model.actuator_trntype[act]) != int(mujoco.mjtTrn.mjTRN_JOINT):
            ignored.append({"actuator": name, "why": "not a joint transmission"})
            continue
        joint = int(model.actuator_trnid[act, 0])
        if int(model.jnt_type[joint]) != int(mujoco.mjtJoint.mjJNT_HINGE):
            ignored.append({"actuator": name, "why": "not a hinge"})
            continue
        joint_axis = [float(v) for v in model.jnt_axis[joint]]
        alignment = abs(_dot(joint_axis, list(axis)))
        if alignment < 0.99:
            ignored.append({"actuator": name, "why": "axis not parallel to the topple line"})
            continue
        limit = float(model.actuator_forcerange[act][1]) if bool(model.actuator_forcelimited[act]) else math.inf
        counted.append({"actuator": name, "torque_limit_nmm": limit * NMM_PER_NM})
        total += limit
    return {"about_axis": list(axis), "actuators": counted, "ignored": ignored,
            "torque_limit_nmm": total * NMM_PER_NM}


def mechanism(model, data) -> dict:
    """The static and modal facts a free-base design stands or falls by."""

    mujoco = _mujoco()
    support = support_set(model, data)
    if support["kind"] not in ("line", "polygon"):
        return {"support": support, "measurable": False}
    axis = [support["direction"][0], support["direction"][1], 0.0]
    normal = [support["normal"][0], support["normal"][1], 0.0]
    root = 1
    for body in range(1, model.nbody):
        if int(model.body_parentid[body]) == 0:
            root = body
            break
    com = [float(v) for v in data.subtree_com[root]]
    mass = float(model.body_subtreemass[root])
    gravity = abs(float(model.opt.gravity[2]))
    first_point = [v / MM_PER_M for v in support["points_mm"][0]]
    lever = _dot(_sub(com[:2], first_point[:2]), support["normal"])
    height = com[2] - support["plane_z_mm"] / MM_PER_M
    point = [first_point[0], first_point[1], support["plane_z_mm"] / MM_PER_M]
    axis_inertia = inertia_about(model, data, point, axis)
    holding = mass * gravity * abs(lever)
    authority = actuator_authority(model, axis)
    limit_nm = authority["torque_limit_nmm"] / NMM_PER_NM
    reach = math.hypot(lever, height)
    # Statically, gravity's torque about the line is m g L sin(theta + phi),
    # where phi is the lean the centre of mass already carries. The tilt at
    # which the declared motors run out is where that equals their limit.
    phi = math.atan2(lever, height)
    ratio = limit_nm / (mass * gravity * reach) if mass * gravity * reach else math.inf
    static_tilt = (math.degrees(math.asin(min(1.0, ratio))) - math.degrees(phi)
                   if ratio <= 1.0 else 90.0 - math.degrees(phi))
    eigenvalue = math.sqrt(mass * gravity * height / axis_inertia) if axis_inertia > 0 else math.inf
    return {
        "measurable": True,
        "support": support,
        "mass_kg": mass,
        "centre_of_mass_mm": [v * MM_PER_M for v in com],
        "lever_arm_mm": lever * MM_PER_M,
        "height_above_support_mm": height * MM_PER_M,
        "inertia_about_support_kg_m2": axis_inertia,
        "holding_torque_nmm": holding * NMM_PER_NM,
        "declared_torque_nmm": authority["torque_limit_nmm"],
        "torque_margin": (limit_nm / holding) if holding > 0 else math.inf,
        "static_tilt_authority_degrees": static_tilt,
        "unstable_eigenvalue_per_s": eigenvalue,
        "time_constant_s": 1.0 / eigenvalue if eigenvalue else math.inf,
        "authority": authority,
    }


def replicate(model, data, *, seconds: float, fps: int) -> dict:
    """Replay the smoke's own zero-command rollout and measure it.

    The smoke commands zero to every actuator that is not a position servo,
    so replaying it needs no controller and invents nothing: it is the model's
    free response. What the replay adds over the receipt is time series the
    receipt summarises -- how the tilt grows, and whether a floor penetration
    settles or deepens.
    """

    mujoco = _mujoco()
    floor = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, FLOOR_GEOM)
    steps = max(1, int(round((1.0 / fps) / float(model.opt.timestep))))
    samples = int(math.floor(seconds * fps + 1e-9)) + 1
    root = next(body for body in range(1, model.nbody) if int(model.body_parentid[body]) == 0)
    tilt, depths, standing = [], {}, {}
    for sample in range(samples):
        mujoco.mj_forward(model, data)
        quaternion = [float(v) for v in data.xquat[root]]
        angle = math.degrees(2.0 * math.acos(max(-1.0, min(1.0, abs(quaternion[0])))))
        tilt.append({"t_s": round(float(data.time), 4), "tilt_degrees": angle,
                     "z_mm": float(data.xpos[root][2]) * MM_PER_M})
        for index in range(data.ncon):
            contact = data.contact[index]
            if floor not in (contact.geom1, contact.geom2):
                continue
            other = contact.geom2 if contact.geom1 == floor else contact.geom1
            name = str(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, int(other)) or "")
            depth = -float(contact.dist) * MM_PER_M
            worst = depths.get(name)
            if worst is None or depth > worst["depth_mm"]:
                depths[name] = {"depth_mm": depth, "t_s": round(float(data.time), 4)}
            standing[name] = depth
        for _ in range(steps):
            mujoco.mj_step(model, data)
    growth = _growth_rate(tilt)
    return {"seconds": seconds, "fps": fps, "samples": samples,
            "final_tilt_degrees": tilt[-1]["tilt_degrees"],
            "measured_growth_rate_per_s": growth,
            "worst_floor_depth_mm": depths,
            "final_floor_depth_mm": standing,
            "tilt": tilt}


def _growth_rate(tilt) -> float | None:
    """The exponent of the tilt's growth while it is still small.

    A least squares fit of ``log(theta)`` against time over the band where
    the linearisation holds. Below half a degree the signal is solver noise
    and above fifteen the small-angle model is gone, so the band is fixed
    rather than fitted.
    """

    band = [(row["t_s"], row["tilt_degrees"]) for row in tilt
            if 0.5 <= row["tilt_degrees"] <= 15.0]
    if len(band) < 2:
        return None
    times = [row[0] for row in band]
    logs = [math.log(row[1]) for row in band]
    mean_t = sum(times) / len(times)
    mean_l = sum(logs) / len(logs)
    denominator = sum((t - mean_t) ** 2 for t in times)
    if denominator == 0:
        return None
    return sum((t - mean_t) * (l - mean_l) for t, l in zip(times, logs)) / denominator


def contact_compliance(path: Path, *, settle_s: float = 0.3) -> dict:
    """The standing floor depth at the design's load and at scaled loads.

    MuJoCo's contact is a spring with a fixed time constant, so a resting
    machine sinks. If the depth follows the load it is compliance and no
    geometry is intersecting; if it does not, something is.
    """

    mujoco = _mujoco()
    text = Path(path).read_text(encoding="utf-8")
    rows = []
    for scale in LOAD_SCALES:
        model = mujoco.MjModel.from_xml_string(text)
        model.body_mass[:] = model.body_mass * scale
        model.body_inertia[:] = model.body_inertia * scale
        data = mujoco.MjData(model)
        mujoco.mj_resetDataKeyframe(model, data, 0)
        floor = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, FLOOR_GEOM)
        for _ in range(int(round(settle_s / float(model.opt.timestep)))):
            mujoco.mj_step(model, data)
        mujoco.mj_forward(model, data)
        deepest = 0.0
        for index in range(data.ncon):
            contact = data.contact[index]
            if floor in (contact.geom1, contact.geom2):
                deepest = max(deepest, -float(contact.dist) * MM_PER_M)
        root = next(body for body in range(1, model.nbody) if int(model.body_parentid[body]) == 0)
        quaternion = float(data.xquat[root][0])
        rows.append({
            "load_scale": scale,
            "standing_depth_mm": deepest,
            # Scaling every mass and inertia together leaves the rigid-body
            # motion almost unchanged, so each load is measured at the same
            # pose and the depths are comparable rather than merely listed.
            "tilt_degrees": math.degrees(2.0 * math.acos(max(-1.0, min(1.0, abs(quaternion))))),
        })
    return {"settled_after_s": settle_s, "loads": rows}


def control_contract(task: dict, eigenvalue: float) -> dict:
    """What a controller for this design would have to read, command and beat.

    Every field comes from the design's own task bundle; none of it is
    proposed here. The one derived number is the pairing of the declared
    control interval with the measured instability, because a contract that
    does not say how fast is not a contract.
    """

    episode = dict(task.get("episode") or {})
    interval = float(episode.get("control_interval_s") or 0.0)
    channels = [channel for row in task.get("observations") or [] for channel in row.get("channels") or []]
    actions = [{"actuator": row.get("actuator"), "low": row.get("low"), "high": row.get("high"),
                "unit": row.get("unit")} for row in task.get("actions") or []]
    growth = math.exp(eigenvalue * interval) if interval and math.isfinite(eigenvalue) else None
    return {
        "reads": channels,
        "commands": actions,
        "control_hz": episode.get("control_hz"),
        "control_interval_s": interval or None,
        "episode_seconds": episode.get("episode_seconds"),
        "reset_keyframe": episode.get("reset_keyframe"),
        "must_hold": task.get("termination") or [],
        "reset_variation": task.get("reset_variation") or [],
        "samples_per_e_fold": (1.0 / (eigenvalue * interval)) if interval and eigenvalue else None,
        "tilt_growth_per_interval": growth,
    }


def diagnose(model_path: Path, task_path: Path | None, smoke_path: Path | None,
             *, seconds: float = 1.0, fps: int = 50) -> dict:
    """The three-part answer, as measurements and one verdict."""

    mujoco = _mujoco()
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    mujoco.mj_forward(model, data)
    facts = mechanism(model, data)
    replay = replicate(model, data, seconds=seconds, fps=fps)
    task = json.loads(Path(task_path).read_text(encoding="utf-8")) if task_path else {}
    receipt = json.loads(Path(smoke_path).read_text(encoding="utf-8")) if smoke_path else {}
    contract = control_contract(task, facts.get("unstable_eigenvalue_per_s", math.inf)) if task else {}
    report = {
        "schema": "ot8-balance-diagnosis-v1",
        "model": {"path": str(model_path), "sha256": digest(model_path)},
        "task": {"path": str(task_path), "sha256": digest(task_path)} if task_path else None,
        "smoke": {
            "path": str(smoke_path) if smoke_path else None,
            "verdict": receipt.get("verdict"),
            "mode": receipt.get("mode"),
            "seconds": receipt.get("seconds"),
            "failing": receipt.get("failing") or [],
            "components_pass": ((receipt.get("checks") or {}).get("components") or {}).get("pass"),
            "initial_pose_agrees": ((receipt.get("checks") or {}).get("components") or {}).get("initial_pose_agrees"),
        },
        "mechanism": facts,
        "replication": replay,
        "contact_compliance": contact_compliance(model_path),
        "control_contract": contract,
    }
    report.update(verdict(report))
    return report


def verdict(report: dict) -> dict:
    """Which of G4's three causes the measurements name, and why.

    The order is the order of cheapness to rule out: a model that does not
    carry the geometry its own solve published is measuring nothing, a
    machine that cannot hold itself up is a design defect whatever a
    controller would do, and what is left -- an unstable equilibrium the
    declared actuators have the authority to hold and nothing to command
    them with -- is a control requirement.
    """

    facts = report["mechanism"]
    smoke = report["smoke"]
    reasons = []
    if smoke.get("components_pass") is False or smoke.get("initial_pose_agrees") is False:
        reasons.append("the smoke's own exact-geometry check fails, so the model and the "
                       "solved assembly disagree before any dynamics")
        return {"verdict": "geometry_mismatch", "reasons": reasons}
    if not facts.get("measurable"):
        reasons.append("the accepted pose has no floor contact set to measure a support line from")
        return {"verdict": "not_measurable", "reasons": reasons}
    margin = facts["torque_margin"]
    if margin <= AUTHORITY_MARGIN:
        reasons.append(
            f"the declared actuators reach {facts['declared_torque_nmm']:.3f} N.mm about the "
            f"support line and holding the accepted pose already needs "
            f"{facts['holding_torque_nmm']:.3f} N.mm (margin {margin:.2f}x)")
        return {"verdict": "design_defect", "reasons": reasons}
    reasons.append(
        f"the machine rests on a {facts['support']['kind']} of {facts['support']['distinct_points']} "
        f"contact points, so it has no static margin about that axis")
    reasons.append(
        f"its centre of mass is {abs(facts['lever_arm_mm']):.3f} mm off that line and "
        f"{facts['height_above_support_mm']:.2f} mm above it: an inverted pendulum with an "
        f"unstable time constant of {facts['time_constant_s'] * 1000:.1f} ms")
    reasons.append(
        f"the declared actuators have {margin:.1f}x the torque needed to hold it and could "
        f"oppose gravity statically out to {facts['static_tilt_authority_degrees']:.1f} degrees, "
        f"so authority is not what is missing")
    reasons.append(
        "the smoke commands zero to both, because a torque motor has no pose to hold, so the "
        "rollout is the free response and the fall is what the model declares")
    return {"verdict": "missing_feedback_control", "reasons": reasons}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path, help="an exported *-model.xml")
    parser.add_argument("--task", type=Path, default=None, help="the *-task.json beside it")
    parser.add_argument("--smoke", type=Path, default=None, help="the smoke.json receipt that failed")
    parser.add_argument("--seconds", type=float, default=1.0)
    parser.add_argument("--fps", type=int, default=50)
    parser.add_argument("--out", type=Path, default=None, help="write the full report here")
    args = parser.parse_args(argv)
    report = diagnose(args.model, args.task, args.smoke, seconds=args.seconds, fps=args.fps)
    if args.out:
        args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = {key: report[key] for key in ("schema", "verdict", "reasons")}
    summary["mechanism"] = {key: report["mechanism"][key] for key in (
        "mass_kg", "lever_arm_mm", "height_above_support_mm", "holding_torque_nmm",
        "declared_torque_nmm", "torque_margin", "static_tilt_authority_degrees",
        "unstable_eigenvalue_per_s", "time_constant_s") if key in report["mechanism"]}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
