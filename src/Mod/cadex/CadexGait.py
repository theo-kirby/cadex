# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""A procedural gait reference: one stride of a legged robot, from biomechanics (ADR-702).

A reward that *describes* a gait pays for the cheapest motion that satisfies
the description; a reward that *shows* one has something to track. This
module produces the thing to track. It takes a gait (a name from
:data:`GAITS`, or explicit footfall parameters), a forward speed and the
robot's own leg chains, and returns **one periodic stride**: joint angles,
foot positions, the contact schedule, and body height and pitch, sampled
over exactly one period.

Nothing here is motion capture. A stride is built in three steps:

1. **Footfall.** Each foot touches down at its phase offset, a fraction of
   the stride after the left hind's (Hildebrand's convention), and stays
   down for the duty factor. The named gaits' offsets follow Hildebrand
   (1965, symmetrical gaits; 1977, asymmetrical gaits); their default duty
   factors are typical of the gait, and every one may be overridden.
2. **Scale.** Stride length follows Alexander's dynamic-similarity
   relation, ``lambda / h = 2.3 * Fr ** 0.3`` with ``Fr = v**2 / (g h)``
   and ``h`` the hip height (Alexander 1976; Alexander & Jayes 1983), and
   the stride frequency is ``v / lambda``. ``h`` is measured on the robot,
   so a short robot strides short and quick, as a small animal does. The
   Froude range each gait is natural over is reported beside the result,
   not enforced: a robot may trot faster than a horse would.
3. **Inverse kinematics.** Each foot's world path (fixed while it is down;
   a minimum-jerk arc while it swings, so its velocity is continuous at
   lift-off and touch-down) is solved onto that leg's own joints by damped
   least squares with a weak pull toward the home pose, **inside every
   joint limit**. A foot the leg cannot reach within tolerance is a
   :class:`GaitUnreachable` naming the leg, the moment in the stride, the
   miss and the joints that were at a stop. Nothing is clamped silently.

Axes are the model's: +x forward, +y left, +z up, as a Cadex assembly is
built. A leg chain is every hinge or slide joint between the foot body and
the floating base. A joint that more than one chain passes through (a spine)
is a body joint: it holds its home angle, or follows ``spine_amplitude_deg``
when it is named as ``spine_joint``.

This is the one module beside ``CadexDynamics`` that drives a ``MjModel``,
and it does not import ``mujoco`` itself: the module comes from
``CadexDynamics``'s single import site, or from the caller. It is outside
the service's closure; ``cadexd`` never imports it.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

#: The clip's schema name.
SCHEMA = "cadex-gait-clip-v1"

#: Standard gravity, m/s^2, for the Froude number.
GRAVITY = 9.80665

#: Foot labels: left/right, fore/hind. The left hind is the phase reference.
FEET = ("LF", "RF", "LH", "RH")

#: The named gaits. ``offsets`` is each foot's touch-down as a fraction of
#: the stride after the left hind's; ``duty`` the share of the stride each
#: foot is down; ``froude`` the range the gait is natural over (reported,
#: not enforced); ``pitch_deg`` and ``spine_deg`` the default body-pitch
#: and spine-flexion amplitudes. Asymmetric gaits are given with the right
#: limbs leading. Offsets: Hildebrand 1965 (Science 150:701) for the
#: symmetrical gaits, Hildebrand 1977 (J. Mammalogy 58:131) for the
#: asymmetrical; transitions near Fr 0.5 (walk to trot) and Fr 2-3 (trot to
#: gallop) from Alexander & Jayes 1983 (J. Zool. 201:135).
GAITS: dict[str, dict[str, Any]] = {
    "walk": {"offsets": {"LH": 0.0, "LF": 0.25, "RH": 0.5, "RF": 0.75},
             "duty": 0.65, "froude": (0.0, 0.5), "pitch_deg": 0.0, "spine_deg": 0.0},
    "trot": {"offsets": {"LH": 0.0, "RF": 0.0, "RH": 0.5, "LF": 0.5},
             "duty": 0.45, "froude": (0.3, 3.0), "pitch_deg": 0.0, "spine_deg": 0.0},
    "pace": {"offsets": {"LH": 0.0, "LF": 0.0, "RH": 0.5, "RF": 0.5},
             "duty": 0.45, "froude": (0.3, 3.0), "pitch_deg": 0.0, "spine_deg": 0.0},
    "canter": {"offsets": {"LH": 0.0, "RH": 0.3, "LF": 0.3, "RF": 0.6},
               "duty": 0.4, "froude": (1.0, 3.0), "pitch_deg": 3.0, "spine_deg": 4.0},
    "transverse_gallop": {"offsets": {"LH": 0.0, "RH": 0.1, "LF": 0.5, "RF": 0.6},
                          "duty": 0.3, "froude": (2.5, math.inf), "pitch_deg": 5.0, "spine_deg": 8.0},
    "rotary_gallop": {"offsets": {"LH": 0.0, "RH": 0.1, "RF": 0.5, "LF": 0.6},
                      "duty": 0.25, "froude": (2.5, math.inf), "pitch_deg": 5.0, "spine_deg": 10.0},
    "half_bound": {"offsets": {"LH": 0.0, "RH": 0.0, "LF": 0.5, "RF": 0.6},
                   "duty": 0.3, "froude": (2.0, math.inf), "pitch_deg": 6.0, "spine_deg": 10.0},
    "bound": {"offsets": {"LH": 0.0, "RH": 0.0, "LF": 0.5, "RF": 0.5},
              "duty": 0.3, "froude": (2.0, math.inf), "pitch_deg": 6.0, "spine_deg": 10.0},
}

#: What the clip cites, carried in it so a reader need not find this file.
SOURCES = (
    "Hildebrand M. 1965. Symmetrical gaits of horses. Science 150:701-708.",
    "Hildebrand M. 1977. Analysis of asymmetrical gaits. J. Mammalogy 58:131-156.",
    "Alexander R.McN. 1976. Estimates of speeds of dinosaurs. Nature 261:129-130 "
    "(stride length / hip height = 2.3 Fr^0.3).",
    "Alexander R.McN., Jayes A.S. 1983. A dynamic similarity hypothesis for the gaits "
    "of quadrupedal mammals. J. Zool. 201:135-152.",
)

#: IK acceptance: a foot further than this from its target is unreachable.
TOLERANCE_M = 1e-3

#: The largest joint step one IK iteration takes, rad.
MAX_STEP_RAD = 0.05


class GaitError(ValueError):
    """A gait request that cannot be honoured, with a machine-readable reason."""

    def __init__(self, message: str, *, reason: str, **detail: Any) -> None:
        super().__init__(message)
        self.reason = reason
        self.detail = detail

    def as_dict(self) -> dict[str, Any]:
        return {"reason": self.reason, "message": str(self), **self.detail}


class GaitUnreachable(GaitError):
    """A foot target a leg cannot reach inside its joint limits."""


def gait_parameters(gait: str | Mapping[str, Any]) -> dict[str, Any]:
    """A named gait's footfall, or explicit ``offsets`` and ``duty``, checked."""

    if isinstance(gait, str):
        if gait not in GAITS:
            raise GaitError(f"unknown gait {gait!r}; known: {sorted(GAITS)}",
                            reason="unknown_gait", gait=gait)
        base = dict(GAITS[gait], name=gait)
    else:
        base = dict(GAITS.get(str(gait.get("name", "")), {}))
        base.update(gait)
        base.setdefault("name", "custom")
        base.setdefault("froude", (0.0, math.inf))
        base.setdefault("pitch_deg", 0.0)
        base.setdefault("spine_deg", 0.0)
    offsets = dict(base.get("offsets") or {})
    if sorted(offsets) != sorted(FEET):
        raise GaitError(f"offsets must name exactly {FEET}, got {sorted(offsets)}",
                        reason="bad_offsets", offsets=offsets)
    duty = float(base.get("duty", float("nan")))
    if not 0.0 < duty < 1.0:
        raise GaitError(f"duty factor must lie in (0, 1), got {duty}",
                        reason="bad_duty", duty=duty)
    base["offsets"] = {foot: float(offsets[foot]) % 1.0 for foot in FEET}
    base["duty"] = duty
    return base


def stride(speed_m_s: float, hip_height_m: float, *,
           stride_length_m: float | None = None) -> dict[str, float]:
    """Stride length, frequency and period at a speed, by dynamic similarity."""

    if not (speed_m_s > 0.0 and math.isfinite(speed_m_s)):
        raise GaitError("a gait reference needs a positive forward speed",
                        reason="bad_speed", speed_m_s=speed_m_s)
    if not hip_height_m > 0.0:
        raise GaitError("hip height must be positive", reason="bad_hip_height",
                        hip_height_m=hip_height_m)
    froude = speed_m_s ** 2 / (GRAVITY * hip_height_m)
    length = (float(stride_length_m) if stride_length_m is not None
              else 2.3 * hip_height_m * froude ** 0.3)
    if not length > 0.0:
        raise GaitError("stride length must be positive", reason="bad_stride",
                        stride_length_m=length)
    return {"froude": froude, "stride_length_m": length,
            "stride_frequency_hz": speed_m_s / length,
            "period_s": length / speed_m_s}


def contact_schedule(offsets: Mapping[str, float], duty: float,
                     samples: int) -> dict[str, list[int]]:
    """Each foot's down (1) or up (0) at ``samples`` even phases of one stride."""

    out: dict[str, list[int]] = {}
    for foot in FEET:
        out[foot] = [int(((k / samples - offsets[foot]) % 1.0) < duty - 1e-12)
                     for k in range(samples)]
    return out


def _minimum_jerk(u: float) -> float:
    return u * u * u * (10.0 - 15.0 * u + 6.0 * u * u)


def foot_path(phase: float, offset: float, duty: float, stride_length_m: float,
              swing_height_m: float) -> tuple[float, float, bool]:
    """A foot's forward travel since its stance centre, its lift, and whether it is down.

    The forward value is in the world frame and relative to the foot's
    position at the middle of the stance that began at ``offset``, so the
    caller adds the body's travel to that moment. Down, the foot does not
    move; up, it travels one stride on a minimum-jerk profile and lifts on a
    raised cosine, both with zero velocity at each end.
    """

    s = (phase - offset) % 1.0
    if s < duty:
        return 0.0, 0.0, True
    u = (s - duty) / (1.0 - duty)
    return (stride_length_m * _minimum_jerk(u), swing_height_m * 0.5 * (1.0 - math.cos(2.0 * math.pi * u)),
            False)


def _mujoco(module: Any | None) -> Any:
    if module is not None:
        return module
    import CadexDynamics  # noqa: PLC0415 - the single mujoco import site

    return CadexDynamics._mujoco_module()


def leg_chains(model: Any, legs: Mapping[str, str], *, mujoco: Any | None = None) -> dict[str, Any]:
    """Each leg's own joints (root to foot), and the body joints legs share.

    ``legs`` maps each of :data:`FEET` to its foot body's name. A chain is
    every hinge or slide joint on the path from the foot body to the base;
    a joint on more than one path is a body joint, not a leg's.
    """

    mj = _mujoco(mujoco)
    if sorted(legs) != sorted(FEET):
        raise GaitError(f"legs must name exactly {FEET}, got {sorted(legs)}",
                        reason="bad_legs", legs=dict(legs))
    paths: dict[str, list[int]] = {}
    for foot, body_name in legs.items():
        body = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, body_name)
        if body < 0:
            raise GaitError(f"leg {foot}: no body named {body_name!r}",
                            reason="unknown_body", leg=foot, body=body_name)
        joints: list[int] = []
        b = body
        while b > 0:
            start, count = int(model.body_jntadr[b]), int(model.body_jntnum[b])
            for j in range(start + count - 1, start - 1, -1):
                if int(model.jnt_type[j]) in (int(mj.mjtJoint.mjJNT_HINGE), int(mj.mjtJoint.mjJNT_SLIDE)):
                    joints.append(j)
            b = int(model.body_parentid[b])
        paths[foot] = joints[::-1]
    seen: dict[int, int] = {}
    for joints in paths.values():
        for j in joints:
            seen[j] = seen.get(j, 0) + 1
    shared = sorted(j for j, n in seen.items() if n > 1)
    chains = {foot: [j for j in joints if j not in shared] for foot, joints in paths.items()}
    for foot, joints in chains.items():
        if len(joints) < 3:
            raise GaitError(f"leg {foot} has {len(joints)} joints of its own; placing a foot in "
                            "space takes at least 3", reason="short_chain", leg=foot,
                            joints=[model.joint(j).name for j in joints])
    return {"chains": chains, "body_joints": shared}


def _foot_point(model: Any, data: Any, body: int) -> Any:
    """The foot's contact point in its body frame: its lowest collision geom's centre."""

    import numpy as np  # noqa: PLC0415

    best = None
    for g in range(model.ngeom):
        if int(model.geom_bodyid[g]) != body:
            continue
        if not (int(model.geom_contype[g]) or int(model.geom_conaffinity[g])):
            continue
        if best is None or data.geom_xpos[g][2] < data.geom_xpos[best][2]:
            best = g
    if best is None:
        return np.zeros(3)
    rot = data.xmat[body].reshape(3, 3)
    return rot.T @ (data.geom_xpos[best] - data.xpos[body])


def _pitch_quaternion(home: Any, pitch_rad: float) -> Any:
    """``home`` rotated nose-up by ``pitch_rad`` about the world's lateral (+y) axis."""

    import numpy as np  # noqa: PLC0415

    half = -0.5 * pitch_rad
    q = np.array([math.cos(half), 0.0, math.sin(half), 0.0])
    w1, x1, y1, z1 = q
    w2, x2, y2, z2 = home
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
                     w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                     w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def generate(model: Any, legs: Mapping[str, str], gait: str | Mapping[str, Any], speed_m_s: float, *,
             stride_length_m: float | None = None, swing_height_m: float | None = None,
             pitch_amplitude_deg: float | None = None, spine_joint: str | None = None,
             spine_amplitude_deg: float | None = None, sample_hz: float = 50.0,
             home_qpos: Sequence[float] | None = None, mujoco: Any | None = None) -> dict[str, Any]:
    """One stride of ``gait`` at ``speed_m_s`` on ``model``'s own legs, or a :class:`GaitError`.

    ``home_qpos`` is the standing pose the stride is built about (default:
    the model's first keyframe, else ``qpos0``); it must stand on the floor,
    since each foot's home height is taken as the ground. Returns a
    ``cadex-gait-clip-v1`` dictionary, plain JSON.
    """

    import numpy as np  # noqa: PLC0415

    mj = _mujoco(mujoco)
    params = gait_parameters(gait)
    duty, offsets = params["duty"], params["offsets"]
    structure = leg_chains(model, legs, mujoco=mj)
    chains, body_joints = structure["chains"], structure["body_joints"]
    if model.nq < 7 or int(model.jnt_type[0]) != int(mj.mjtJoint.mjJNT_FREE):
        raise GaitError("a gait reference needs a floating base (a free joint first)",
                        reason="no_floating_base")

    spine = None
    spine_amp = 0.0
    if spine_joint is not None:
        spine = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, spine_joint)
        if spine < 0 or spine not in body_joints:
            raise GaitError(f"spine joint {spine_joint!r} is not a joint the legs share",
                            reason="bad_spine_joint", spine_joint=spine_joint,
                            body_joints=[model.joint(j).name for j in body_joints])
        spine_amp = math.radians(params["spine_deg"] if spine_amplitude_deg is None else spine_amplitude_deg)
    elif spine_amplitude_deg:
        raise GaitError("spine flexion was asked for but no spine joint was named",
                        reason="no_spine_joint", spine_amplitude_deg=spine_amplitude_deg,
                        body_joints=[model.joint(j).name for j in body_joints])

    data = mj.MjData(model)
    if home_qpos is not None:
        home = np.asarray(home_qpos, dtype=float).copy()
    elif model.nkey:
        home = np.asarray(model.key_qpos[0], dtype=float).copy()
    else:
        home = np.asarray(model.qpos0, dtype=float).copy()
    data.qpos[:] = home
    mj.mj_kinematics(model, data)

    feet_body = {foot: mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, legs[foot]) for foot in FEET}
    point_local = {foot: _foot_point(model, data, feet_body[foot]) for foot in FEET}

    def world_point(foot: str) -> Any:
        b = feet_body[foot]
        return data.xpos[b] + data.xmat[b].reshape(3, 3) @ point_local[foot]

    base_home = home[:3].copy()
    quat_home = home[3:7].copy()
    foot_home = {foot: world_point(foot) - base_home for foot in FEET}
    hips = {foot: float(data.xanchor[chains[foot][0]][2] - world_point(foot)[2]) for foot in FEET}
    hip_height = float(np.mean(list(hips.values())))

    s = stride(speed_m_s, hip_height, stride_length_m=stride_length_m)
    period, length = s["period_s"], s["stride_length_m"]
    swing = 0.08 * hip_height if swing_height_m is None else float(swing_height_m)
    pitch_amp = math.radians(params["pitch_deg"] if pitch_amplitude_deg is None else pitch_amplitude_deg)
    samples = max(8, int(round(period * sample_hz)))
    dt = period / samples

    limits = {}
    for joints in chains.values():
        for j in joints:
            lo, hi = model.jnt_range[j]
            limits[j] = (float(lo), float(hi)) if model.jnt_limited[j] else (-math.inf, math.inf)

    qpos = np.zeros((samples, model.nq))
    targets = {foot: np.zeros((samples, 3)) for foot in FEET}
    residual = {foot: 0.0 for foot in FEET}
    body_x = np.zeros(samples)
    body_z = np.zeros(samples)
    body_pitch = np.zeros(samples)
    contact = contact_schedule(offsets, duty, samples)
    q = home.copy()
    jacp = np.zeros((3, model.nv))
    damping, posture = 1e-6, 0.1
    for k in range(samples):
        t = k * dt
        phase = k / samples
        x = speed_m_s * t
        pitch = pitch_amp * math.sin(2.0 * math.pi * phase)
        q[:3] = base_home + np.array([x, 0.0, 0.0])
        q[3:7] = _pitch_quaternion(quat_home, pitch)
        if spine is not None:
            q[model.jnt_qposadr[spine]] = home[model.jnt_qposadr[spine]] + spine_amp * math.sin(
                2.0 * math.pi * phase)
        for foot in FEET:
            travel, lift, _down = foot_path(phase, offsets[foot], duty, length, swing)
            # the stance this foot is in (or swinging from) began at its offset;
            # its centre is duty/2 later, and the foot sat at home under the body then
            since = (phase - offsets[foot]) % 1.0
            centre_t = t - since * period + 0.5 * duty * period
            target = base_home + foot_home[foot] + np.array([speed_m_s * centre_t + travel, 0.0, lift])
            targets[foot][k] = target
        # solve every leg against its own targets with the base and spine set
        for _ in range(400):
            data.qpos[:] = q
            mj.mj_kinematics(model, data)
            mj.mj_comPos(model, data)
            worst = 0.0
            for foot in FEET:
                err = targets[foot][k] - world_point(foot)
                worst = max(worst, float(np.linalg.norm(err)))
                if np.linalg.norm(err) < 1e-6:
                    continue
                b = feet_body[foot]
                mj.mj_jac(model, data, jacp, None, world_point(foot), b)
                joints = chains[foot]
                cols = [int(model.jnt_dofadr[j]) for j in joints]
                adrs = [int(model.jnt_qposadr[j]) for j in joints]
                # an active set: a joint at a stop that the step would push
                # further is taken out, and the rest re-solve without it
                free = list(range(len(joints)))
                for _pass in range(len(joints)):
                    J = jacp[:, [cols[i] for i in free]]
                    pinv = J.T @ np.linalg.inv(J @ J.T + damping * np.eye(3))
                    pull = posture * (home[[adrs[i] for i in free]] - q[[adrs[i] for i in free]])
                    # the error by damped least squares; the pull toward home only in
                    # the null space, so it never trades against the foot
                    dq = pinv @ err + (np.eye(len(free)) - pinv @ J) @ pull
                    pinned = []
                    for n, i in enumerate(free):
                        lo, hi = limits[joints[i]]
                        v = q[adrs[i]]
                        if (v <= lo + 1e-9 and dq[n] < 0.0) or (v >= hi - 1e-9 and dq[n] > 0.0):
                            pinned.append(i)
                    if not pinned or len(free) - len(pinned) < 1:
                        break
                    free = [i for i in free if i not in pinned]
                # a trust region: a long step overshoots into the stops
                biggest = float(np.max(np.abs(dq))) if len(dq) else 0.0
                if biggest > MAX_STEP_RAD:
                    dq = dq * (MAX_STEP_RAD / biggest)
                for n, i in enumerate(free):
                    lo, hi = limits[joints[i]]
                    q[adrs[i]] = min(hi, max(lo, q[adrs[i]] + dq[n]))
            if worst < 1e-5:
                break
        data.qpos[:] = q
        mj.mj_kinematics(model, data)
        for foot in FEET:
            miss = float(np.linalg.norm(targets[foot][k] - world_point(foot)))
            residual[foot] = max(residual[foot], miss)
            if miss > TOLERANCE_M:
                stops = []
                for j in chains[foot]:
                    lo, hi = limits[j]
                    v = q[model.jnt_qposadr[j]]
                    if v <= lo + 1e-6 or v >= hi - 1e-6:
                        stops.append(model.joint(j).name)
                raise GaitUnreachable(
                    f"leg {foot} cannot reach its {('stance' if contact[foot][k] else 'swing')} target "
                    f"at {phase:.3f} of the stride: it misses by {1000 * miss:.1f} mm"
                    + (f" with {', '.join(stops)} at a stop" if stops else "")
                    + f" (stride {1000 * length:.0f} mm, swing {1000 * swing:.0f} mm)",
                    reason="unreachable", leg=foot, phase=phase, miss_mm=1000 * miss,
                    joints_at_stop=stops, stride_length_m=length, swing_height_m=swing,
                    target_m=[float(v) for v in targets[foot][k]])
        qpos[k] = q
        body_x[k], body_z[k], body_pitch[k] = q[0], q[2], pitch

    joint_ids = sorted({j for joints in chains.values() for j in joints} | set(body_joints))
    lo_nat, hi_nat = params["froude"]
    return {
        "schema": SCHEMA,
        "gait": params["name"],
        "parameters": {
            "speed_m_s": float(speed_m_s), "duty_factor": duty, "phase_offsets": dict(offsets),
            "hip_height_m": hip_height, "froude": s["froude"],
            "froude_natural_range": [lo_nat, None if math.isinf(hi_nat) else hi_nat],
            "froude_in_natural_range": bool(lo_nat <= s["froude"] <= hi_nat),
            "stride_length_m": length, "stride_frequency_hz": s["stride_frequency_hz"],
            "period_s": period, "swing_height_m": swing,
            "stride_length_source": "given" if stride_length_m is not None else "alexander_1976",
            "pitch_amplitude_deg": math.degrees(pitch_amp),
            "spine_joint": spine_joint, "spine_amplitude_deg": math.degrees(spine_amp),
        },
        "sources": list(SOURCES),
        "sample_dt_s": dt,
        "samples": samples,
        "legs": {foot: {"foot_body": legs[foot],
                        "joints": [model.joint(j).name for j in chains[foot]]} for foot in FEET},
        "body_joints": [model.joint(j).name for j in body_joints],
        "joints": [model.joint(j).name for j in joint_ids],
        "joint_angles_rad": [[float(qpos[k][model.jnt_qposadr[j]]) for j in joint_ids]
                             for k in range(samples)],
        "joint_limits_rad": [[float(model.jnt_range[j][0]), float(model.jnt_range[j][1])]
                             if model.jnt_limited[j] else None for j in joint_ids],
        "qpos": qpos.tolist(),
        "foot_positions_m": {foot: targets[foot].tolist() for foot in FEET},
        "contact": contact,
        "body": {"x_m": body_x.tolist(), "z_m": body_z.tolist(),
                 "pitch_deg": [math.degrees(p) for p in body_pitch]},
        "ik": {"tolerance_m": TOLERANCE_M, "max_miss_m": {foot: residual[foot] for foot in FEET}},
    }
