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

**Two feet (ADR-754).** ``legs`` keyed ``L`` and ``R`` instead builds a
biped's stride from :data:`BIPED_GAITS`: the left foot is the phase
reference, and the same dynamic-similarity scale and inverse kinematics
apply, Alexander's relation having been fitted across bipeds and
quadrupeds alike. The four-foot path is unchanged by it.

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

#: A biped's foot labels (ADR-754). The left foot is the phase reference.
BIPED_FEET = ("L", "R")

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

#: A biped's named gaits (ADR-754), on the same terms as :data:`GAITS`: the
#: feet alternate half a stride apart; a walk keeps a foot down more than
#: half the stride (double support), a run less (an aerial phase). The
#: walk-to-run change near Fr 0.5 and the duty factors either side of 0.5
#: follow Alexander 1984 (Int. J. Robotics Research 3:49).
BIPED_GAITS: dict[str, dict[str, Any]] = {
    "walk": {"offsets": {"L": 0.0, "R": 0.5},
             "duty": 0.6, "froude": (0.0, 0.5), "pitch_deg": 0.0, "spine_deg": 0.0},
    "run": {"offsets": {"L": 0.0, "R": 0.5},
            "duty": 0.35, "froude": (0.5, math.inf), "pitch_deg": 0.0, "spine_deg": 0.0},
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

#: What a biped's clip cites (ADR-754).
BIPED_SOURCES = (
    SOURCES[2],
    "Alexander R.McN. 1984. The gaits of bipedal and quadrupedal animals. "
    "Int. J. Robotics Research 3(2):49-59 (walk to run near Fr 0.5; duty factor "
    "above 0.5 walking, below it running).",
)

#: IK acceptance: a foot further than this from its target is unreachable.
TOLERANCE_M = 1e-3

#: How much more a loop closure's row weighs in the solve than a foot's (ADR-776).
CLOSURE_WEIGHT = 30.0

#: Solver iterations per sample.
IK_ITERATIONS = 400

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


def feet_of(legs: Mapping[str, Any]) -> tuple[str, ...]:
    """The foot labels ``legs`` is keyed by: :data:`FEET`, or :data:`BIPED_FEET` (ADR-754)."""

    for feet in (FEET, BIPED_FEET):
        if sorted(legs) == sorted(feet):
            return feet
    raise GaitError(f"legs must name exactly {FEET}, or {BIPED_FEET} for a biped, "
                    f"got {sorted(legs)}", reason="bad_legs", legs=dict(legs))


def gait_parameters(gait: str | Mapping[str, Any],
                    feet: tuple[str, ...] = FEET) -> dict[str, Any]:
    """A named gait's footfall, or explicit ``offsets`` and ``duty``, checked.

    ``feet`` picks the table: :data:`GAITS` for four, :data:`BIPED_GAITS` for two.
    """

    table = BIPED_GAITS if feet == BIPED_FEET else GAITS
    if isinstance(gait, str):
        if gait not in table:
            raise GaitError(f"unknown gait {gait!r}; known: {sorted(table)}",
                            reason="unknown_gait", gait=gait)
        base = dict(table[gait], name=gait)
    else:
        base = dict(table.get(str(gait.get("name", "")), {}))
        base.update(gait)
        base.setdefault("name", "custom")
        base.setdefault("froude", (0.0, math.inf))
        base.setdefault("pitch_deg", 0.0)
        base.setdefault("spine_deg", 0.0)
    offsets = dict(base.get("offsets") or {})
    if sorted(offsets) != sorted(feet):
        raise GaitError(f"offsets must name exactly {feet}, got {sorted(offsets)}",
                        reason="bad_offsets", offsets=offsets)
    duty = float(base.get("duty", float("nan")))
    if not 0.0 < duty < 1.0:
        raise GaitError(f"duty factor must lie in (0, 1), got {duty}",
                        reason="bad_duty", duty=duty)
    base["offsets"] = {foot: float(offsets[foot]) % 1.0 for foot in feet}
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


def contact_schedule(offsets: Mapping[str, float], duty: float, samples: int,
                     feet: tuple[str, ...] = FEET) -> dict[str, list[int]]:
    """Each foot's down (1) or up (0) at ``samples`` even phases of one stride."""

    out: dict[str, list[int]] = {}
    for foot in feet:
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

    ``legs`` maps each of :data:`FEET` (or :data:`BIPED_FEET`) to its foot
    body's name. A chain is
    every hinge or slide joint on the path from the foot body to the base;
    a joint on more than one path is a body joint, not a leg's.
    """

    mj = _mujoco(mujoco)
    feet_of(legs)
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


def _lowest_geom(model: Any, data: Any, body: int) -> int | None:
    """The body's lowest collision geom at the current pose, or ``None``."""

    best = None
    for g in range(model.ngeom):
        if int(model.geom_bodyid[g]) != body:
            continue
        if not (int(model.geom_contype[g]) or int(model.geom_conaffinity[g])):
            continue
        if best is None or data.geom_xpos[g][2] < data.geom_xpos[best][2]:
            best = g
    return best


def _foot_point(model: Any, data: Any, body: int) -> Any:
    """The foot's contact point in its body frame: its lowest collision geom's centre."""

    import numpy as np  # noqa: PLC0415

    best = _lowest_geom(model, data, body)
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


def _below_centre(model: Any, data: Any, geom: int, mj: Any) -> float:
    """How far a collision geom reaches below its centre at the current pose, m (ADR-776)."""

    import numpy as np  # noqa: PLC0415

    kind, size = int(model.geom_type[geom]), model.geom_size[geom]
    up = data.geom_xmat[geom].reshape(3, 3)[2]       # the world z of each geom axis
    if kind == int(mj.mjtGeom.mjGEOM_SPHERE):
        return float(size[0])
    if kind == int(mj.mjtGeom.mjGEOM_CAPSULE):
        return float(size[0] + size[1] * abs(up[2]))
    if kind == int(mj.mjtGeom.mjGEOM_CYLINDER):
        return float(size[0] * math.sqrt(max(0.0, 1.0 - up[2] ** 2)) + size[1] * abs(up[2]))
    if kind == int(mj.mjtGeom.mjGEOM_BOX):
        return float(np.sum(np.abs(up) * size[:3]))
    if kind == int(mj.mjtGeom.mjGEOM_ELLIPSOID):
        return float(np.sqrt(np.sum((up * size[:3]) ** 2)))
    raise GaitError(f"geom {model.geom(geom).name!r} is a shape whose lowest point the generator "
                    "does not read (a sphere, capsule, cylinder, box or ellipsoid is)",
                    reason="heel_geom", geom=model.geom(geom).name)


def _path_joints(model: Any, body: int, mj: Any) -> list[int]:
    """Every hinge or slide joint between ``body`` and the world, root first."""

    joints: list[int] = []
    b = body
    while b > 0:
        start, count = int(model.body_jntadr[b]), int(model.body_jntnum[b])
        for j in range(start + count - 1, start - 1, -1):
            if int(model.jnt_type[j]) in (int(mj.mjtJoint.mjJNT_HINGE), int(mj.mjtJoint.mjJNT_SLIDE)):
                joints.append(j)
        b = int(model.body_parentid[b])
    return joints[::-1]


def leg_closures(model: Any, chains: Mapping[str, Sequence[int]], body_joints: Sequence[int], *,
                 mujoco: Any | None = None) -> dict[str, dict[str, Any]]:
    """Each leg's loop closures and joint couplings, and the joints they add (ADR-776).

    An active ``equality/connect`` belongs to a leg when the joints between
    its two anchors and the base are that leg's own, the body joints, and
    joints no foot's path passes through (a rod's pins, hanging off the
    leg). Those last are the leg's **passive** joints: the solver moves them
    with the leg's, so the loop stays closed. An active ``equality/joint``
    belongs to a leg when both its joints are the leg's own or passive. A
    row that touches no leg (a tail's cable coupling) is left alone.
    """

    mj = _mujoco(mujoco)
    legged = {j for joints in chains.values() for j in joints} | set(body_joints)
    out: dict[str, dict[str, Any]] = {foot: {"connects": [], "couplings": [], "passive": []}
                                      for foot in chains}
    pending_joint_rows = []
    for i in range(model.neq):
        if not int(model.eq_active0[i]):
            continue
        kind = int(model.eq_type[i])
        if kind == int(mj.mjtEq.mjEQ_CONNECT):
            if int(model.eq_objtype[i]) == int(mj.mjtObj.mjOBJ_SITE):
                bodies = [int(model.site_bodyid[model.eq_obj1id[i]]), int(model.site_bodyid[model.eq_obj2id[i]])]
            else:
                bodies = [int(model.eq_obj1id[i]), int(model.eq_obj2id[i])]
            path = set(_path_joints(model, bodies[0], mj)) | set(_path_joints(model, bodies[1], mj))
            for foot, joints in chains.items():
                own = path & set(joints)
                extra = path - legged
                if own and not (path - set(joints) - set(body_joints) - extra):
                    out[foot]["connects"].append(i)
                    for j in sorted(extra):
                        if j not in out[foot]["passive"]:
                            out[foot]["passive"].append(j)
        elif kind == int(mj.mjtEq.mjEQ_JOINT):
            pending_joint_rows.append(i)
    for i in pending_joint_rows:
        j1, j2 = int(model.eq_obj1id[i]), int(model.eq_obj2id[i])
        for foot, joints in chains.items():
            variables = set(joints) | set(out[foot]["passive"])
            if j1 in variables and (j2 < 0 or j2 in variables):
                out[foot]["couplings"].append(i)
    return out


def _leg_rows(model: Any, data: Any, mj: Any, foot: str, target: Any, point: Any, body: int,
              closure: Mapping[str, Any], jacp: Any, heel: int | None, ground: float) -> tuple[list, list]:
    """One leg's residual rows and their Jacobians (ADR-776), at the current pose.

    First the foot (3 rows), then, in stance with a heel, the heel's lowest
    point against the ground (1), then each loop closure (3) and joint
    coupling (1). ``jacp=None`` returns only the residuals.
    """

    import numpy as np  # noqa: PLC0415

    errs, jacs = [target - point], []
    want = jacp is not None
    if want:
        mj.mj_jac(model, data, jacp, None, point, body)
        jacs.append(jacp.copy())
    if heel is not None:
        lowest = float(data.geom_xpos[heel][2] - _below_centre(model, data, heel, mj))
        errs.append(np.array([ground - lowest]))
        if want:
            mj.mj_jac(model, data, jacp, None, data.geom_xpos[heel], int(model.geom_bodyid[heel]))
            jacs.append(jacp[2:3].copy())
    for i in closure["connects"]:
        if int(model.eq_objtype[i]) == int(mj.mjtObj.mjOBJ_SITE):
            s1, s2 = int(model.eq_obj1id[i]), int(model.eq_obj2id[i])
            a, b = data.site_xpos[s1].copy(), data.site_xpos[s2].copy()
            ba, bb = int(model.site_bodyid[s1]), int(model.site_bodyid[s2])
        else:
            ba, bb = int(model.eq_obj1id[i]), int(model.eq_obj2id[i])
            a = data.xpos[ba] + data.xmat[ba].reshape(3, 3) @ model.eq_data[i][0:3]
            b = data.xpos[bb] + data.xmat[bb].reshape(3, 3) @ model.eq_data[i][3:6]
        errs.append(b - a)
        if want:
            mj.mj_jac(model, data, jacp, None, a, ba)
            ja = jacp.copy()
            mj.mj_jac(model, data, jacp, None, b, bb)
            jacs.append(ja - jacp)
    for i in closure["couplings"]:
        j1, j2 = int(model.eq_obj1id[i]), int(model.eq_obj2id[i])
        a1 = int(model.jnt_qposadr[j1])
        q1 = float(data.qpos[a1] - model.qpos0[a1])
        c = model.eq_data[i]
        row = np.zeros((1, model.nv))
        if j2 >= 0:
            a2 = int(model.jnt_qposadr[j2])
            q2 = float(data.qpos[a2] - model.qpos0[a2])
            target2 = c[0] + c[1] * q2 + c[2] * q2 ** 2 + c[3] * q2 ** 3 + c[4] * q2 ** 4
            row[0, int(model.jnt_dofadr[j2])] = -(c[1] + 2 * c[2] * q2 + 3 * c[3] * q2 ** 2 + 4 * c[4] * q2 ** 3)
        else:
            target2 = c[0]
        row[0, int(model.jnt_dofadr[j1])] = 1.0
        errs.append(np.array([target2 - q1]))
        if want:
            jacs.append(row)
    return errs, jacs


def generate(model: Any, legs: Mapping[str, str], gait: str | Mapping[str, Any], speed_m_s: float, *,
             stride_length_m: float | None = None, swing_height_m: float | None = None,
             pitch_amplitude_deg: float | None = None, spine_joint: str | None = None,
             spine_amplitude_deg: float | None = None, sample_hz: float = 50.0,
             samples: int | None = None, home_qpos: Sequence[float] | None = None,
             heels: Mapping[str, str] | None = None, body_drop_m: float = 0.0,
             body_pitch_deg: float = 0.0, stance_shift_m: Mapping[str, float] | None = None,
             heel_from: float = 0.0, mujoco: Any | None = None) -> dict[str, Any]:
    """One stride of ``gait`` at ``speed_m_s`` on ``model``'s own legs, or a :class:`GaitError`.

    ``home_qpos`` is the standing pose the stride is built about (default:
    the model's first keyframe, else ``qpos0``); it must stand on the floor,
    since each foot's home height is taken as the ground. ``samples`` fixes
    the stride's sample count instead of ``sample_hz`` (ADR-773: the clips of
    a speed schedule share one phase grid). Returns a
    ``cadex-gait-clip-v1`` dictionary, plain JSON.

    **Closed legs (ADR-776).** The model's loop closures and joint couplings
    on a leg (:func:`leg_closures`) are held by the same solve: each is rows
    beside the foot's, and a rod's own pins are solved with the leg's
    joints, so a coupled paw takes the angle its linkage gives it. A loop
    the solve cannot close is refused as a :class:`GaitUnreachable`.
    ``heels`` maps a foot (``LH``, say) to a body above it; while that foot
    is down, the heel body's lowest collision point is held on the ground
    too: the plantigrade stance, the whole foot down to the heel. With
    ``heel_from`` the heel is held down only from that share of the stance
    to toe-off: the foot lands on its toes and lays down to push off.
    ``body_drop_m`` lowers the trunk that far below its standing height for
    the whole stride, and ``body_pitch_deg`` pitches it nose-up about the
    base's origin by that much more than the stride's own pitch: the crouch,
    and the lower hips, a foot laid flat to the heel needs.
    ``stance_shift_m`` moves a foot's stance forward of its standing place
    (``{"LH": 0.06}``): where a gallop's hind feet land, under the belly.
    ``assembly.gait`` passes them as ``heels``, ``heel_from``,
    ``body_drop_mm``, ``body_pitch_deg`` and ``stance_shift_mm`` (ADR-777).
    """

    import numpy as np  # noqa: PLC0415

    mj = _mujoco(mujoco)
    feet = feet_of(legs)
    params = gait_parameters(gait, feet)
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

    feet_body = {foot: mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, legs[foot]) for foot in feet}
    point_local = {foot: _foot_point(model, data, feet_body[foot]) for foot in feet}
    foot_geom = {foot: _lowest_geom(model, data, feet_body[foot]) for foot in feet}
    # the ground under each foot: its lowest collision point, standing at home
    ground = {foot: float(data.geom_xpos[foot_geom[foot]][2] - _below_centre(model, data, foot_geom[foot], mj))
              if foot_geom[foot] is not None else 0.0 for foot in feet}
    closures = leg_closures(model, chains, body_joints, mujoco=mj)
    heel_geom: dict[str, int] = {}
    for foot, name in dict(heels or {}).items():
        if foot not in feet:
            raise GaitError(f"heels names {foot!r}, which is not one of {feet}",
                            reason="bad_heel", foot=foot)
        body = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, str(name))
        if body < 0:
            raise GaitError(f"heel of {foot}: no body named {name!r}", reason="unknown_body",
                            leg=foot, body=str(name))
        allowed = set(chains[foot]) | set(body_joints) | set(closures[foot]["passive"])
        if not set(_path_joints(model, body, mj)) <= allowed or not set(_path_joints(model, body, mj)) & set(chains[foot]):
            raise GaitError(f"heel of {foot}: {name!r} is not carried by that leg",
                            reason="bad_heel", leg=foot, body=str(name))
        g = _lowest_geom(model, data, body)
        if g is None:
            raise GaitError(f"heel of {foot}: {name!r} has no collision geom to stand on",
                            reason="bad_heel", leg=foot, body=str(name))
        _below_centre(model, data, g, mj)
        heel_geom[foot] = g

    def world_point(foot: str) -> Any:
        b = feet_body[foot]
        return data.xpos[b] + data.xmat[b].reshape(3, 3) @ point_local[foot]

    base_home = home[:3].copy()
    quat_home = home[3:7].copy()
    foot_home = {foot: world_point(foot) - base_home for foot in feet}
    shift = dict(stance_shift_m or {})
    for foot, value in shift.items():
        if foot not in feet:
            raise GaitError(f"stance_shift_m names {foot!r}, which is not one of {feet}",
                            reason="bad_stance_shift", foot=foot)
        foot_home[foot] = foot_home[foot] + np.array([float(value), 0.0, 0.0])
    hips = {foot: float(data.xanchor[chains[foot][0]][2] - world_point(foot)[2]) for foot in feet}
    hip_height = float(np.mean(list(hips.values())))

    s = stride(speed_m_s, hip_height, stride_length_m=stride_length_m)
    period, length = s["period_s"], s["stride_length_m"]
    swing = 0.08 * hip_height if swing_height_m is None else float(swing_height_m)
    pitch_amp = math.radians(params["pitch_deg"] if pitch_amplitude_deg is None else pitch_amplitude_deg)
    samples = max(8, int(samples) if samples is not None else int(round(period * sample_hz)))
    dt = period / samples

    limits = {}
    for foot, joints in chains.items():
        for j in list(joints) + closures[foot]["passive"]:
            lo, hi = model.jnt_range[j]
            limits[j] = (float(lo), float(hi)) if model.jnt_limited[j] else (-math.inf, math.inf)

    qpos = np.zeros((samples, model.nq))
    targets = {foot: np.zeros((samples, 3)) for foot in feet}
    residual = {foot: 0.0 for foot in feet}
    closure_miss = {foot: 0.0 for foot in feet}
    heel_height = {foot: np.zeros(samples) for foot in heel_geom}
    body_x = np.zeros(samples)
    body_z = np.zeros(samples)
    body_pitch = np.zeros(samples)
    contact = contact_schedule(offsets, duty, samples, feet)
    if not 0.0 <= float(heel_from) < 1.0:
        raise GaitError(f"heel_from is a share of the stance in [0, 1), got {heel_from}",
                        reason="bad_heel_from", heel_from=heel_from)
    heel_down = {foot: [int(bool(contact[foot][k]) and ((k / samples - offsets[foot]) % 1.0)
                            >= float(heel_from) * duty - 1e-12) for k in range(samples)]
                 for foot in heel_geom}
    q = home.copy()
    jacp = np.zeros((3, model.nv))
    damping, posture = 1e-6, 0.1
    for k in range(samples):
        t = k * dt
        phase = k / samples
        x = speed_m_s * t
        pitch = math.radians(body_pitch_deg) + pitch_amp * math.sin(2.0 * math.pi * phase)
        q[:3] = base_home + np.array([x, 0.0, -float(body_drop_m)])
        q[3:7] = _pitch_quaternion(quat_home, pitch)
        if spine is not None:
            q[model.jnt_qposadr[spine]] = home[model.jnt_qposadr[spine]] + spine_amp * math.sin(
                2.0 * math.pi * phase)
        for foot in feet:
            travel, lift, _down = foot_path(phase, offsets[foot], duty, length, swing)
            # the stance this foot is in (or swinging from) began at its offset;
            # its centre is duty/2 later, and the foot sat at home under the body then
            since = (phase - offsets[foot]) % 1.0
            centre_t = t - since * period + 0.5 * duty * period
            target = base_home + foot_home[foot] + np.array([speed_m_s * centre_t + travel, 0.0, lift])
            targets[foot][k] = target
        # solve every leg against its own targets with the base and spine set
        for _ in range(IK_ITERATIONS):
            data.qpos[:] = q
            mj.mj_kinematics(model, data)
            mj.mj_comPos(model, data)
            worst = 0.0
            for foot in feet:
                rows_err, rows_jac = _leg_rows(model, data, mj, foot, targets[foot][k], world_point(foot),
                                               feet_body[foot], closures[foot], jacp,
                                               heel_geom.get(foot) if heel_down.get(foot, [0] * samples)[k] else None,
                                               ground[foot])
                err = np.concatenate(rows_err)
                worst = max(worst, float(np.linalg.norm(err)))
                n_loops = len(closures[foot]["connects"]) + len(closures[foot]["couplings"])
                if np.linalg.norm(err) < 1e-6:
                    continue
                joints = list(chains[foot]) + closures[foot]["passive"]
                cols = [int(model.jnt_dofadr[j]) for j in joints]
                adrs = [int(model.jnt_qposadr[j]) for j in joints]
                # a loop is a hard constraint, the feet are targets: the closure
                # rows weigh CLOSURE_WEIGHT times a foot's, so a foot the leg
                # cannot reach is missed at the foot, not by opening the loop
                weight = np.concatenate([np.full(len(e), CLOSURE_WEIGHT if n >= len(rows_err) - n_loops else 1.0)
                                         for n, e in enumerate(rows_err)])
                err = err * weight
                full = np.vstack(rows_jac) * weight[:, None]
                rows = len(err)
                # an active set: a joint at a stop that the step would push
                # further is taken out, and the rest re-solve without it
                free = list(range(len(joints)))
                for _pass in range(len(joints)):
                    J = full[:, [cols[i] for i in free]]
                    pinv = J.T @ np.linalg.inv(J @ J.T + damping * np.eye(rows))
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
        for foot in feet:
            rows_err, _jac = _leg_rows(model, data, mj, foot, targets[foot][k], world_point(foot),
                                       feet_body[foot], closures[foot], None,
                                       heel_geom.get(foot) if heel_down.get(foot, [0] * samples)[k] else None,
                                       ground[foot])
            held = bool(heel_down.get(foot, [0] * samples)[k])
            loop = float(max((np.max(np.abs(e)) for e in rows_err[1 + held:]), default=0.0))
            closure_miss[foot] = max(closure_miss[foot], loop)
            if foot in heel_geom:
                g = heel_geom[foot]
                heel_height[foot][k] = float(data.geom_xpos[g][2] - _below_centre(model, data, g, mj) - ground[foot])
            miss = float(np.linalg.norm(targets[foot][k] - world_point(foot)))
            if held:
                miss = max(miss, abs(float(heel_height[foot][k])))
            miss = max(miss, loop)
            residual[foot] = max(residual[foot], miss)
            if miss > TOLERANCE_M:
                stops = []
                for j in chains[foot]:
                    lo, hi = limits[j]
                    v = q[model.jnt_qposadr[j]]
                    if v <= lo + 1e-6 or v >= hi - 1e-6:
                        stops.append(model.joint(j).name)
                what = ("close its linkage" if loop > TOLERANCE_M else
                        "put its heel down" if held and abs(float(heel_height[foot][k])) > TOLERANCE_M else
                        f"reach its {('stance' if contact[foot][k] else 'swing')} target")
                raise GaitUnreachable(
                    f"leg {foot} cannot {what} "
                    f"at {phase:.3f} of the stride: it misses by {1000 * miss:.1f} mm"
                    + (f" with {', '.join(stops)} at a stop" if stops else "")
                    + f" (stride {1000 * length:.0f} mm, swing {1000 * swing:.0f} mm)",
                    reason="unreachable", leg=foot, phase=phase, miss_mm=1000 * miss,
                    joints_at_stop=stops, stride_length_m=length, swing_height_m=swing,
                    target_m=[float(v) for v in targets[foot][k]])
        qpos[k] = q
        body_x[k], body_z[k], body_pitch[k] = q[0], q[2], pitch

    # a rod's passive pins are in ``qpos`` and named under ``ik.closures``, not posed
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
            **({"body_drop_m": float(body_drop_m)} if body_drop_m else {}),
            **({"body_pitch_deg": float(body_pitch_deg)} if body_pitch_deg else {}),
            **({"stance_shift_m": {foot: float(v) for foot, v in shift.items()}} if shift else {}),
        },
        "sources": list(BIPED_SOURCES if feet == BIPED_FEET else SOURCES),
        "sample_dt_s": dt,
        "samples": samples,
        "legs": {foot: {"foot_body": legs[foot],
                        "joints": [model.joint(j).name for j in chains[foot]]} for foot in feet},
        "body_joints": [model.joint(j).name for j in body_joints],
        "joints": [model.joint(j).name for j in joint_ids],
        "joint_angles_rad": [[float(qpos[k][model.jnt_qposadr[j]]) for j in joint_ids]
                             for k in range(samples)],
        "joint_limits_rad": [[float(model.jnt_range[j][0]), float(model.jnt_range[j][1])]
                             if model.jnt_limited[j] else None for j in joint_ids],
        "qpos": qpos.tolist(),
        "foot_positions_m": {foot: targets[foot].tolist() for foot in feet},
        "contact": contact,
        "body": {"x_m": body_x.tolist(), "z_m": body_z.tolist(),
                 "pitch_deg": [math.degrees(p) for p in body_pitch]},
        "ik": {"tolerance_m": TOLERANCE_M, "max_miss_m": {foot: residual[foot] for foot in feet},
               **({"closures": {foot: {
                   "rows": [mj.mj_id2name(model, mj.mjtObj.mjOBJ_EQUALITY, i) or f"equality {i}"
                            for i in closures[foot]["connects"] + closures[foot]["couplings"]],
                   "passive_joints": [model.joint(j).name for j in closures[foot]["passive"]],
                   "max_error": closure_miss[foot]}
                   for foot in feet if closures[foot]["connects"] or closures[foot]["couplings"]}}
                  if any(c["connects"] or c["couplings"] for c in closures.values()) else {})},
        **({"heels": {foot: {"body": model.body(int(model.geom_bodyid[g])).name,
                             "from_stance_share": float(heel_from), "down": heel_down[foot],
                             "height_m": heel_height[foot].tolist()}
                      for foot, g in heel_geom.items()}} if heel_geom else {}),
    }


def placements(model: Any, clip: Mapping[str, Any], *, mujoco: Any | None = None) -> list[dict[str, Any]]:
    """Every named body's world pose at each sample of ``clip`` (ADR-703).

    The clip's ``qpos`` rows put through forward kinematics: per sample, a
    map from body name to ``position_mm`` and ``rotation_xyzw``, the shape a
    simulation trace's ``component_placements`` has, so the dashboard plays a
    reference the way it plays a rollout. Nothing is simulated: this is the
    pose the reference asks for, not a pose the dynamics reached.
    """

    import numpy as np  # noqa: PLC0415

    mj = _mujoco(mujoco)
    rows = clip.get("qpos") or ()
    if any(len(row) != model.nq for row in rows):
        raise GaitError(f"the clip's qpos rows do not match this model's {model.nq} coordinates",
                        reason="clip_model_mismatch", nq=int(model.nq))
    names = [(b, model.body(b).name) for b in range(1, model.nbody) if model.body(b).name]
    data = mj.MjData(model)
    out = []
    for row in rows:
        data.qpos[:] = np.asarray(row, dtype=float)
        mj.mj_kinematics(model, data)
        frame = {}
        for b, name in names:
            w, x, y, z = (float(v) for v in data.xquat[b])
            frame[name] = {"position_mm": [round(1000.0 * float(v), 4) for v in data.xpos[b]],
                           "rotation_xyzw": [round(v, 7) for v in (x, y, z, w)]}
        out.append(frame)
    return out
