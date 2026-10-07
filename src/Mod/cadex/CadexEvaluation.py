# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""What a rollout did, as numbers a success spec can be held against (ADR-455).

A reward says what a policy was paid for, and a policy that was paid and
shuffled is the failure this module exists to see. It reads a rollout trace
(``cadex-assembly-simulation-trace-v1``: every component's pose at every
control step) and a handful of facts about the model it ran, and returns
**behaviour metrics**: what the mechanism did, none of them the reward.

Three families, and nothing in the module knows which behaviour it is
reading -- each family is asked for by what the caller names, not by a task
kind:

* **posture**, for anything with a floating base: tilt, heading, drift from
  where it started, and the time it takes to come back to rest after a shove;
* **gait**, for anything with feet: steps as opposed to chatter, foot
  clearance, stance slip, duty factor, how deep a foot went into the floor,
  and how well a commanded speed was tracked;
* **reach**, for anything with a tip and a target: final error, time to
  target and overshoot, per target.

:func:`check` then holds a flat table of those metrics against a list of
predicates (``metric``, ``min``, ``max``). A predicate names a metric and a
bound and nothing else, so a success spec is data, and a spec for closing a
hand is a different list rather than a different code path.

**Pure standard library, millimetres and degrees throughout.** The model
facts arrive as plain numbers (``CadexDynamics.evaluation_rig`` reads them,
because that module is the only one allowed to import ``mujoco`` and the only
one allowed to convert a unit), so this can be loaded by path by a client
with no engine built -- ``CadexStudio``'s standing (ADR-445). It is outside
the service's closure: ``cadexd`` never imports it.

Three definitions are what an eye sees and a lift line on a part's centre
does not. A foot's height is the lowest point of its collision geoms above
the floor, so stance is a fact about geometry. A *step* is an airborne run
that lasts and lands somewhere else, so chatter is not counted. Slip is the
travel of the material point that was on the floor, so a round foot that
rolls through its stance is not charged for it.
"""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "cadex-evaluation-metrics-v1"

#: A foot is in stance when its lowest point is at most this far above the
#: floor. Soft contact rests a foot a fraction of a millimetre into the
#: plane, so zero would read a standing foot as flying on float noise.
STANCE_MM = 1.0
#: Speed is the plan displacement over this window, divided by it. A single
#: control step's difference is contact noise; a fifth of a second is a
#: velocity.
SPEED_WINDOW_S = 0.20
#: A swing shorter than this is chatter, however many of them there are.
SWING_MIN_S = 0.10
#: ...and one that lands nearer than this to where it lifted went nowhere.
STEP_ADVANCE_HIP_HEIGHTS = 0.15
#: Speed, lateral drift, duty factor and how deep a foot goes into the floor
#: are read after this much settling, so the drop from the reset pose is not
#: read as gait (ADR-467: a robot holding its pose lands from a reset lift
#: deeper than it ever stands).
SETTLE_S = 1.0
#: Rest, for recovery from a shove: upright enough, slow enough, for long
#: enough. Speed is in COM heights per second so one number fits any size.
REST_TILT_DEG = 10.0
REST_SPEED_COM_HEIGHTS_PER_S = 1.0
REST_HOLD_S = 1.0
#: A tip has arrived when it is within this of the target, in arm lengths,
#: and the final error is the worst distance over the last window.
REACH_TOLERANCE_ARM_LENGTHS = 0.05
REACH_FINAL_WINDOW_S = 1.0

#: Every metric a success predicate may bound, and what measuring it needs
#: (ADR-456). This is the whole vocabulary of a success spec: a name that is
#: not here is not a behaviour metric, and the task's reward, its reward
#: terms and its observation channels are deliberately not here.
#:
#: The needs are facts about the spec and the model, never about a
#: behaviour: ``base`` is a floating base, ``floor`` the one plane it stands
#: on, ``feet`` and ``tip`` what the spec names, ``shove`` a timed
#: disturbance in the spec's conditions, ``command`` a speed goal the task
#: states and ``target`` a point goal it states (ADR-462).
METRICS: dict[str, tuple[str, tuple[str, ...]]] = {
    "completed": ("episode", ()),
    "duration_s": ("episode", ()),
    "max_tilt_deg": ("posture", ("base",)),
    "max_heading_deg": ("posture", ("base",)),
    "final_heading_deg": ("posture", ("base",)),
    "max_drift_mm": ("posture", ("base",)),
    "final_drift_mm": ("posture", ("base",)),
    "mean_speed_mm_s": ("posture", ("base",)),
    "max_drift_com_heights": ("posture", ("base", "floor")),
    "recovery_s_max": ("posture", ("base", "floor", "shove")),
    "mean_forward_speed_mm_s": ("gait", ("feet",)),
    "mean_lateral_speed_mm_s": ("gait", ("feet",)),
    "steps_min": ("gait", ("feet",)),
    "step_count_ratio": ("gait", ("feet",)),
    "step_share_min": ("gait", ("feet",)),
    "step_clearance_hip_heights_min": ("gait", ("feet",)),
    "slip_share_max": ("gait", ("feet",)),
    "duty_factor_min": ("gait", ("feet",)),
    "duty_factor_max": ("gait", ("feet",)),
    "foot_lowest_hip_heights_min": ("gait", ("feet",)),
    "speed_ratio": ("gait", ("feet", "command")),
    "lateral_ratio": ("gait", ("feet", "command")),
    "final_error_mm_max": ("reach", ("tip", "target")),
    "final_error_arm_lengths_max": ("reach", ("tip", "target")),
    "time_to_target_s_max": ("reach", ("tip", "target")),
    "overshoot_ratio_max": ("reach", ("tip", "target")),
}

_EPS = 1.0e-9

Vector = tuple[float, float, float]
Matrix = tuple[Vector, Vector, Vector]


# -- rotations (trace quaternions are [x, y, z, w]) -------------------------

def matrix(quat_xyzw: Sequence[float]) -> Matrix:
    """One trace quaternion as a rotation matrix, rows first."""

    x, y, z, w = (float(v) for v in quat_xyzw)
    n = math.sqrt(x * x + y * y + z * z + w * w)
    x, y, z, w = x / n, y / n, z / n, w / n
    return (
        (1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
        (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
        (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)),
    )


def _apply(rotation: Matrix, vector: Sequence[float]) -> Vector:
    return tuple(sum(row[i] * float(vector[i]) for i in range(3)) for row in rotation)


def _apply_inverse(rotation: Matrix, vector: Sequence[float]) -> Vector:
    return tuple(sum(rotation[j][i] * float(vector[j]) for j in range(3)) for i in range(3))


def _compose(first: Matrix, second: Matrix) -> Matrix:
    return tuple(
        tuple(sum(first[i][k] * second[k][j] for k in range(3)) for j in range(3))
        for i in range(3)
    )


def _column(rotation: Matrix, index: int) -> Vector:
    return (rotation[0][index], rotation[1][index], rotation[2][index])


def _add(a: Sequence[float], b: Sequence[float]) -> Vector:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: Sequence[float], b: Sequence[float]) -> Vector:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _pose(placements: Mapping[str, Any], name: str) -> tuple[Matrix, Vector]:
    pose = placements[name]
    return matrix(pose["rotation_xyzw"]), tuple(float(v) for v in pose["position_mm"])


def tilt_degrees(rotation: Matrix, reference: Matrix) -> float:
    """The angle between a body's local +Z now and in its reference attitude."""

    dot = sum(a * b for a, b in zip(_column(rotation, 2), _column(reference, 2)))
    return math.degrees(math.acos(max(-1.0, min(1.0, dot))))


def forward(rotation: Matrix, reference: Matrix) -> tuple[float, float]:
    """World +X of the reference pose, carried with the body, flattened to plan."""

    # (rotation @ reference.T)[:, 0]
    axis = tuple(sum(rotation[i][k] * reference[0][k] for k in range(3)) for i in range(2))
    length = math.hypot(axis[0], axis[1])
    return (axis[0] / length, axis[1] / length)


# -- traces -----------------------------------------------------------------

def read_trace(raw: Mapping[str, Any]) -> dict[str, Any]:
    """The timed frames, the episode and the digests of one exported trace."""

    policy, dynamics = raw.get("policy") or {}, raw.get("dynamics") or {}
    samples = [(float(f["nominal_time_s"]), f["component_placements"])
               for f in raw["frames"] if f.get("frame_kind") == "solver_output"]
    hz, steps = dynamics.get("control_hz"), policy.get("step_count")
    return {
        "samples": samples,
        "episode": {
            "seed": policy.get("seed"), "steps": steps, "control_hz": hz,
            "steps_per_frame": dynamics.get("steps_per_frame"),
            "duration_s": (steps / hz) if steps is not None and hz else None,
            "termination": str(policy.get("termination") or ""),
            "truncated": bool(policy.get("truncated")),
        },
        "digests": {"policy_sha256": policy.get("policy_sha256"),
                    "mjcf_sha256": policy.get("model_sha256"),
                    "task_sha256": policy.get("task_sha256")},
    }


def load_trace(path: Path | str) -> dict[str, Any]:
    return read_trace(json.loads(Path(path).read_text(encoding="utf-8")))


def _frame_interval(times: Sequence[float]) -> float:
    return float(statistics.median(b - a for a, b in zip(times, times[1:])))


# -- the base ---------------------------------------------------------------

def base_series(samples, rig: Mapping[str, Any], *,
                speed_window_s: float = SPEED_WINDOW_S) -> dict[str, Any]:
    """Time, base point (plan), tilt, heading and windowed velocity per frame.

    The base point is the base body's own centre of mass, so a body that
    pitches about its origin is not read as travelling. Heading is unwrapped
    and relative to the first frame. ``velocity`` is ``None`` for the frames
    before a full window exists.
    """

    reference = matrix(rig["reference_xyzw"])
    local = rig["base_com_local_mm"]
    times, points, tilts, headings, forwards = [], [], [], [], []
    for time_s, placements in samples:
        rotation, origin = _pose(placements, rig["base"])
        point = _add(_apply(rotation, local), origin)
        times.append(float(time_s))
        points.append((point[0], point[1]))
        tilts.append(tilt_degrees(rotation, reference))
        ahead = forward(rotation, reference)
        forwards.append(ahead)
        angle = math.degrees(math.atan2(ahead[1], ahead[0]))
        if headings:
            # Unwrapped: a robot that turns through 180 degrees has turned
            # 181, not -179.
            angle += 360.0 * round((headings[-1] - angle) / 360.0)
        headings.append(angle)
    headings = [angle - headings[0] for angle in headings]
    dt = _frame_interval(times)
    lag = max(1, int(round(speed_window_s / dt)))
    velocity: list[tuple[float, float] | None] = [None] * len(points)
    for i in range(lag, len(points)):
        velocity[i] = ((points[i][0] - points[i - lag][0]) / (lag * dt),
                       (points[i][1] - points[i - lag][1]) / (lag * dt))
    return {"time": times, "point": points, "tilt": tilts, "heading": headings,
            "forward": forwards, "velocity": velocity, "dt": dt}


def posture(base: Mapping[str, Any], com_height_mm: float | None) -> dict[str, Any]:
    """Tilt, heading and drift over a whole episode, from one base series.

    ``com_height_mm`` is ``None`` for a base with no floor under it; the
    drift in COM heights is then not measured, and the rest still is.
    """

    start = base["point"][0]
    drift = [math.hypot(p[0] - start[0], p[1] - start[1]) for p in base["point"]]
    speeds = [math.hypot(*v) for v in base["velocity"] if v is not None]
    return {
        "max_tilt_deg": max(base["tilt"]),
        "max_heading_deg": max(abs(h) for h in base["heading"]),
        "final_heading_deg": base["heading"][-1],
        "max_drift_mm": max(drift),
        "final_drift_mm": drift[-1],
        "max_drift_com_heights": max(drift) / com_height_mm if com_height_mm else None,
        "mean_speed_mm_s": (sum(speeds) / len(speeds)) if speeds else None,
    }


def recovery(time, tilt, speed, shove_end_s: float, *, com_height_mm: float,
             tilt_deg_max: float = REST_TILT_DEG,
             speed_com_heights_per_s_max: float = REST_SPEED_COM_HEIGHTS_PER_S,
             hold_s: float = REST_HOLD_S) -> float | None:
    """Seconds from a shove's end to the first frame that starts a full rest.

    ``speed`` may hold ``None`` where no window exists yet; that is not rest.
    ``None`` back means it never came to rest inside the episode.
    """

    limit = speed_com_heights_per_s_max * com_height_mm
    quiet = [t <= tilt_deg_max and s is not None and s <= limit for t, s in zip(tilt, speed)]
    hold = int(round(hold_s / _frame_interval(time)))
    for i, moment in enumerate(time):
        if moment < shove_end_s - _EPS:
            continue
        if i + hold >= len(time):
            return None
        if all(quiet[i:i + hold + 1]):
            return float(moment - shove_end_s)
    return None


def balance_metrics(samples, rig: Mapping[str, Any], shoves=(), *,
                    speed_window_s: float = SPEED_WINDOW_S,
                    rest_tilt_deg: float = REST_TILT_DEG,
                    rest_speed_com_heights_per_s: float = REST_SPEED_COM_HEIGHTS_PER_S,
                    rest_hold_s: float = REST_HOLD_S) -> dict[str, Any]:
    """Posture, plus the recovery time from each shove the episode applied.

    ``shoves`` is ``[(onset_s, duration_s)]``. ``recovery_s_max`` is ``None``
    when there was no shove to recover from, or when one was never recovered
    from; ``recovery_s`` says which.
    """

    base = base_series(samples, rig, speed_window_s=speed_window_s)
    com = float(rig["com_height_mm"])
    speed = [None if v is None else math.hypot(*v) for v in base["velocity"]]
    times = [recovery(base["time"], base["tilt"], speed, onset + duration, com_height_mm=com,
                      tilt_deg_max=rest_tilt_deg,
                      speed_com_heights_per_s_max=rest_speed_com_heights_per_s,
                      hold_s=rest_hold_s)
             for onset, duration in shoves]
    recovered = bool(times) and all(t is not None for t in times)
    return {
        **posture(base, com),
        "com_height_mm": com,
        "shoves": len(times),
        "recovery_s": times,
        "recovery_s_max": max(times) if recovered else None,
    }


# -- feet -------------------------------------------------------------------

def _lowest(geom: Mapping[str, Any], rotation: Matrix, origin: Vector) -> tuple[Vector, Vector]:
    """One geom's centre and lowest point in the world, from its body's pose."""

    centre = _add(_apply(rotation, geom["pos_mm"]), origin)
    size = geom["size_mm"]
    if geom["kind"] == "sphere":
        return centre, (centre[0], centre[1], centre[2] - size[0])
    turn = _compose(rotation, matrix(geom["quat_xyzw"]))
    if geom["kind"] == "capsule":
        axis = _column(turn, 2)
        reach = math.copysign(size[1], axis[2])
        end = (centre[0] - reach * axis[0], centre[1] - reach * axis[1], centre[2] - reach * axis[2])
        return centre, (end[0], end[1], end[2] - size[0])
    corner = list(centre)
    for i in range(3):
        half = math.copysign(size[i], turn[2][i])
        for k in range(3):
            corner[k] -= half * turn[k][i]
    return centre, (corner[0], corner[1], corner[2])


def foot_series(samples, name: str, geoms: Sequence[Mapping[str, Any]],
                floor_mm: float) -> dict[str, Any]:
    """Height, plan point and frame-to-frame contact-point travel of one foot.

    ``contact_travel[i]`` is how far, in plan, the material point that was
    lowest in frame ``i`` had moved by frame ``i + 1``.
    """

    heights, points, travel = [], [], []
    previous = None
    for _, placements in samples:
        rotation, origin = _pose(placements, name)
        lows = [_lowest(geom, rotation, origin) for geom in geoms]
        centre = lows[0][0]
        low = min((pair[1] for pair in lows), key=lambda point: point[2])
        heights.append(low[2] - floor_mm)
        points.append((centre[0], centre[1]))
        if previous is not None:
            # Where the material point that was lowest a frame ago is now.
            moved = _add(_apply(rotation, previous["local"]), origin)
            travel.append(math.hypot(moved[0] - previous["low"][0], moved[1] - previous["low"][1]))
        previous = {"low": low, "local": _apply_inverse(rotation, _sub(low, origin))}
    return {"height": heights, "point": points, "contact_travel": travel}


def _median(values: Sequence[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def gait(time, foot: Mapping[str, Any], hip_height_mm: float, *,
         settle_s: float = SETTLE_S, stance_mm: float = STANCE_MM,
         swing_min_s: float = SWING_MIN_S,
         step_advance_hip_heights: float = STEP_ADVANCE_HIP_HEIGHTS) -> dict[str, Any]:
    """Steps, clearance, slip and duty factor of one foot."""

    height, point = foot["height"], foot["point"]
    dt = _frame_interval(time)
    stance = [h <= stance_mm for h in height]
    segment = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(point, point[1:])]
    total = float(sum(segment))
    slip = float(sum(travel for i, travel in enumerate(foot["contact_travel"])
                     if stance[i] and stance[i + 1]))
    swings, steps = [], []
    i, n = 0, len(stance)
    while i < n:
        if stance[i]:
            i += 1
            continue
        start = i
        while i < n and not stance[i]:
            i += 1
        if start == 0 or i == n:
            continue  # touches an end of the episode: not a whole swing
        end = i - 1
        swing = {
            "lift_s": float(time[start]), "airborne_s": (end - start + 1) * dt,
            "peak_mm": float(max(height[start:end + 1])),
            "advance_mm": math.hypot(point[end + 1][0] - point[start - 1][0],
                                     point[end + 1][1] - point[start - 1][1]),
            "path_mm": float(sum(segment[start - 1:end + 1])),
        }
        swings.append(swing)
        if (swing["airborne_s"] >= swing_min_s - _EPS
                and swing["advance_mm"] >= step_advance_hip_heights * hip_height_mm):
            steps.append(swing)
    settled = [s for moment, s in zip(time, stance) if moment >= settle_s]
    settled_low = min((h for moment, h in zip(time, height) if moment >= settle_s), default=None)
    clearance = _median([s["peak_mm"] for s in steps])
    return {
        "swings": len(swings),
        "steps": len(steps),
        "path_mm": total,
        "step_share": (sum(s["path_mm"] for s in steps) / total) if total > _EPS else 0.0,
        "slip_mm": slip,
        "slip_share": (slip / total) if total > _EPS else 0.0,
        "median_step_clearance_mm": clearance,
        "median_step_clearance_hip_heights": None if clearance is None else clearance / hip_height_mm,
        "median_swing_peak_mm": _median([s["peak_mm"] for s in swings]),
        "median_swing_airborne_s": _median([s["airborne_s"] for s in swings]),
        "median_step_advance_mm": _median([s["advance_mm"] for s in steps]),
        "peak_height_mm": float(max(height)),
        "lowest_height_mm": float(min(height)),
        "lowest_height_hip_heights": float(min(height)) / hip_height_mm,
        "settled_lowest_height_mm": None if settled_low is None else float(settled_low),
        "settled_lowest_height_hip_heights": (
            None if settled_low is None else float(settled_low) / hip_height_mm
        ),
        "duty_factor": (sum(settled) / len(settled)) if settled else None,
    }


def gait_metrics(samples, rig: Mapping[str, Any], command_mm_s: float | None = None, *,
                 settle_s: float = SETTLE_S, speed_window_s: float = SPEED_WINDOW_S,
                 stance_mm: float = STANCE_MM, swing_min_s: float = SWING_MIN_S,
                 step_advance_hip_heights: float = STEP_ADVANCE_HIP_HEIGHTS) -> dict[str, Any]:
    """Posture, speed tracking and every foot's gait, with the worst foot named flat.

    ``command_mm_s`` is the forward speed the episode asked for, in the
    base's heading frame. An episode that asked for none has no speed to
    track: ``speed_ratio`` and ``lateral_ratio`` are then ``None`` and the
    speeds themselves are still measured. A spec bounds the flat keys -- ``steps_min`` is the
    foot that stepped least, ``slip_share_max`` the foot that slid most -- so
    "every foot" is one number; ``feet`` keeps each foot's own figures for
    the report. A flat key is ``None`` when it could not be measured (no foot
    stepped, or the episode ended inside the settle), which a predicate reads
    as a failure rather than as zero.
    """

    hip = float(rig["hip_height_mm"])
    base = base_series(samples, rig, speed_window_s=speed_window_s)
    along, across = [], []
    for moment, velocity, ahead in zip(base["time"], base["velocity"], base["forward"]):
        if moment >= settle_s and velocity is not None:
            along.append(velocity[0] * ahead[0] + velocity[1] * ahead[1])
            across.append(velocity[1] * ahead[0] - velocity[0] * ahead[1])
    # An episode that ends inside the settle has no speed to read; that is
    # nothing measured, never a number.
    mean_along = (sum(along) / len(along)) if along else None
    mean_across = (sum(across) / len(across)) if across else None
    feet = {
        name: gait(base["time"], foot_series(samples, name, geoms, rig["floor_mm"]), hip,
                   settle_s=settle_s, stance_mm=stance_mm, swing_min_s=swing_min_s,
                   step_advance_hip_heights=step_advance_hip_heights)
        for name, geoms in rig["feet"].items()
    }

    def worst(key: str, pick) -> float | None:
        values = [foot[key] for foot in feet.values()]
        return None if any(v is None for v in values) else pick(values)

    counts = [foot["steps"] for foot in feet.values()]
    travel = (base["point"][-1][0] - base["point"][0][0], base["point"][-1][1] - base["point"][0][1])
    return {
        **posture(base, float(rig["com_height_mm"])),
        "command_mm_s": None if command_mm_s is None else float(command_mm_s),
        "hip_height_mm": hip,
        "mean_forward_speed_mm_s": mean_along,
        "mean_lateral_speed_mm_s": mean_across,
        "speed_ratio": (
            None if mean_along is None or command_mm_s is None else mean_along / command_mm_s
        ),
        "lateral_ratio": (
            None if mean_across is None or command_mm_s is None
            else abs(mean_across) / command_mm_s
        ),
        "travel_mm": [travel[0], travel[1]],
        "steps_min": min(counts),
        "step_count_ratio": (max(counts) / min(counts)) if min(counts) else None,
        "step_share_min": worst("step_share", min),
        "step_clearance_hip_heights_min": worst("median_step_clearance_hip_heights", min),
        "slip_share_max": worst("slip_share", max),
        "duty_factor_min": worst("duty_factor", min),
        "duty_factor_max": worst("duty_factor", max),
        "foot_lowest_hip_heights_min": worst("settled_lowest_height_hip_heights", min),
        "feet": feet,
    }


def settled_command(commands, *, settle_s: float = SETTLE_S) -> float | None:
    """The commanded speed a gait is read against: its mean over the settled frames.

    ``commands`` is ``[(time_s, command_mm_s)]``, one per frame, as a
    rollout's frames carry the goal. A command held for the episode is that
    command exactly. One that changes is averaged over the same frames the
    measured speed is, so ``speed_ratio`` compares a mean with a mean; it
    does not say how quickly a change was followed. ``None`` when the
    episode ended inside the settle.
    """

    held = [float(command) for moment, command in commands if float(moment) >= settle_s]
    if not held:
        return None
    return held[0] if min(held) == max(held) else sum(held) / len(held)


# -- a tip and its targets --------------------------------------------------

def tip_series(samples, tip: Mapping[str, Any]) -> tuple[list[float], list[Vector]]:
    """The tip point in the world per frame: a fixed point on one body."""

    times, points = [], []
    for time_s, placements in samples:
        rotation, origin = _pose(placements, tip["body"])
        times.append(float(time_s))
        points.append(_add(_apply(rotation, tip["local_mm"]), origin))
    return times, points


def reach_metrics(samples, rig: Mapping[str, Any], segments: Sequence[Mapping[str, Any]], *,
                  tolerance_arm_lengths: float = REACH_TOLERANCE_ARM_LENGTHS,
                  final_window_s: float = REACH_FINAL_WINDOW_S) -> dict[str, Any]:
    """Final error, time to target and overshoot, for each target in turn.

    ``segments`` is ``[{"start_s", "end_s", "target_mm"}]``: the target held
    over each stretch of the episode. A frame on a boundary belongs to the
    segment that starts there.

    * **final error** is the largest tip-to-target distance over the last
      ``final_window_s`` of the segment -- the largest, so a tip that is
      still swinging through the target is not read at its best moment,
      and ``None`` when the episode ended before that window began;
    * **time to target** runs from the segment's start until the tip is
      inside the tolerance *and stays there to the segment's end*, and is
      ``None`` if it never does;
    * **overshoot** is the furthest the tip gets past the target along the
      line from where it was when the segment began, as a ratio of that
      line's length.

    The flat keys are the worst segment. ``time_to_target_s_max`` is ``None``
    when any target was not reached.
    """

    arm = float(rig["arm_length_mm"])
    tolerance = tolerance_arm_lengths * arm
    times, points = tip_series(samples, rig["tip"])
    rows = []
    for index, segment in enumerate(segments):
        start_s, end_s = float(segment["start_s"]), float(segment["end_s"])
        target = tuple(float(v) for v in segment["target_mm"])
        last = index == len(segments) - 1
        inside = [i for i, moment in enumerate(times)
                  if moment >= start_s - _EPS and (moment < end_s - _EPS or (last and moment <= end_s + _EPS))]
        if not inside:
            rows.append({"start_s": start_s, "end_s": end_s, "target_mm": list(target), "frames": 0,
                         "final_error_mm": None, "final_error_arm_lengths": None,
                         "time_to_target_s": None, "overshoot_ratio": None})
            continue
        origin = points[inside[0]]
        distance = [math.dist(points[i], target) for i in inside]
        final = [d for i, d in zip(inside, distance) if times[i] >= end_s - final_window_s - _EPS]
        outside = [k for k, d in enumerate(distance) if d > tolerance]
        if not outside:
            arrival = 0.0
        elif outside[-1] == len(inside) - 1:
            arrival = None
        else:
            arrival = times[inside[outside[-1] + 1]] - start_s
        line = _sub(target, origin)
        length = math.sqrt(sum(v * v for v in line))
        if length > _EPS:
            past = max(sum(a * b for a, b in zip(_sub(points[i], origin), line)) / length - length
                       for i in inside)
            overshoot = max(0.0, past) / length
        else:
            overshoot = None
        rows.append({
            "start_s": start_s, "end_s": end_s, "target_mm": list(target), "frames": len(inside),
            "start_distance_mm": length,
            # An episode that ended before the segment's final window has
            # no final error: unmeasured, so a spec bounding it fails.
            "final_error_mm": max(final) if final else None,
            "final_error_arm_lengths": max(final) / arm if final else None,
            "closest_mm": min(distance),
            "time_to_target_s": arrival, "overshoot_ratio": overshoot,
        })

    def worst(key: str) -> float | None:
        values = [row[key] for row in rows]
        return None if not values or any(v is None for v in values) else max(values)

    return {
        "arm_length_mm": arm,
        "tolerance_mm": tolerance,
        "targets": len(rows),
        "final_error_mm_max": worst("final_error_mm"),
        "final_error_arm_lengths_max": worst("final_error_arm_lengths"),
        "time_to_target_s_max": worst("time_to_target_s"),
        "overshoot_ratio_max": worst("overshoot_ratio"),
        "segments": rows,
    }


# -- the episode, and a spec held against all of it -------------------------

def episode_metrics(episode: Mapping[str, Any]) -> dict[str, Any]:
    """How the episode ended. ``completed`` is 1.0 only for a run to the horizon."""

    ended = bool(episode.get("truncated")) and not episode.get("termination")
    return {"completed": 1.0 if ended else 0.0, "duration_s": episode.get("duration_s"),
            "termination": str(episode.get("termination") or "")}


def measure(samples, episode: Mapping[str, Any], rig: Mapping[str, Any], *,
            shoves=(), command_mm_s: float | None = None,
            segments: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """Every behaviour metric one rollout can be read for, as one flat table.

    Which families are read is decided by what the rig and the episode
    carry, never by what the behaviour is called: a floating base is read
    for posture, named feet for gait, a tip with targets for reach, and a
    shove for the recovery from it. ``metrics`` holds the names in
    :data:`METRICS` and nothing else, so it is exactly what a predicate may
    bound; a family that was not read is absent from it, and :func:`check`
    fails a predicate on an absent metric. ``detail`` keeps what a report
    shows beside the table: each foot's own figures, each shove's recovery,
    each target's row.

    ``shoves`` is ``[(onset_s, duration_s)]``, ``command_mm_s`` the forward
    speed the episode asked for and ``segments`` the targets it held -- what
    the episode applied, handed in by whoever ran it.
    """

    read: dict[str, Any] = dict(episode_metrics(episode))
    detail: dict[str, Any] = {}
    if rig.get("base") is not None:
        if rig.get("com_height_mm") is not None:
            read.update(balance_metrics(samples, rig, shoves))
        else:
            read.update(posture(base_series(samples, rig), None))
        if rig.get("feet"):
            read.update(gait_metrics(samples, rig, command_mm_s))
    if rig.get("tip") is not None and segments:
        read.update(reach_metrics(samples, rig, segments))
    for key in ("recovery_s", "feet", "segments", "travel_mm"):
        if key in read:
            detail[key] = read[key]
    return {"metrics": {name: read[name] for name in METRICS if name in read},
            "detail": detail}


def _spread(values: Sequence[float]) -> dict[str, Any]:
    return {"min": min(values), "median": float(statistics.median(values)), "max": max(values)}


def summarise(seeds: Sequence[Mapping[str, Any]],
              predicates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """What a set of evaluated seeds says together.

    ``seeds`` are per-seed rows carrying ``seed``, ``pass``, ``predicates``
    (from :func:`check`), ``metrics``, ``episode`` and ``reward``. **Every
    seed must pass**: nothing here averages a verdict, and the spreads below
    are for reading a failure, never for deciding one. A metric's spread is
    over the seeds that measured it, and ``measured`` says how many did. A
    row may carry ``void``, the reason its episode is not a measurement at
    all; such a seed is listed and is never among the passed.
    """

    held = []
    for index, predicate in enumerate(predicates):
        rows = [seed["predicates"][index] for seed in seeds]
        values = [row["value"] for row in rows if row["value"] is not None]
        held.append({
            "id": rows[0]["id"] if rows else str(predicate.get("id", predicate["metric"])),
            "metric": str(predicate["metric"]),
            "min": predicate.get("min"), "max": predicate.get("max"),
            "passed": sum(1 for row in rows if row["pass"]),
            "failed_seeds": [seed["seed"] for seed, row in zip(seeds, rows) if not row["pass"]],
            "value": _spread(values) if values else None,
        })
    causes: dict[str, int] = {}
    for seed in seeds:
        cause = str(seed["episode"].get("termination") or "") or "horizon"
        causes[cause] = causes.get(cause, 0) + 1
    names = [name for name in METRICS if any(name in seed["metrics"] for seed in seeds)]
    metrics = {}
    for name in names:
        values = [seed["metrics"][name] for seed in seeds
                  if isinstance(seed["metrics"].get(name), (int, float))]
        metrics[name] = {"measured": len(values), **(_spread(values) if values else {})}
    labels: list[str] = []
    for seed in seeds:
        labels.extend(term["label"] for term in seed["reward"]["terms"] if term["label"] not in labels)
    terms = [{"label": label, **_spread([term["total"] for seed in seeds
                                         for term in seed["reward"]["terms"] if term["label"] == label])}
             for label in labels]
    passed = [seed["seed"] for seed in seeds if seed["pass"]]
    return {
        "seeds": len(seeds),
        "passed": passed,
        "failed": [seed["seed"] for seed in seeds if not seed["pass"]],
        "void": [seed["seed"] for seed in seeds if seed.get("void")],
        "pass": bool(seeds) and len(passed) == len(seeds),
        "predicates": held,
        "terminations": causes,
        "reward": {"total": _spread([seed["reward"]["total"] for seed in seeds]) if seeds else None,
                   "terms": terms},
        "metrics": metrics,
    }


def check(predicates: Sequence[Mapping[str, Any]], metrics: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Hold named metrics against their bounds: one row per predicate.

    A predicate is ``{"id", "metric", "min"?, "max"?}`` with at least one
    bound. It passes when the metric was measured and lies inside the bounds,
    inclusive. **A metric that is missing or ``None`` fails**, and the row
    says so: a spec that named something nobody measured has not been met,
    and a foot that took no step has no clearance to pass on.
    """

    rows = []
    for predicate in predicates:
        name = str(predicate["metric"])
        low, high = predicate.get("min"), predicate.get("max")
        if low is None and high is None:
            raise ValueError(f"predicate {predicate.get('id', name)!r} states no bound")
        value = metrics.get(name)
        why = ""
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            passed, value = False, None
            why = f"{name} was not measured"
        else:
            passed = (low is None or value >= low) and (high is None or value <= high)
            if not passed:
                why = f"{name} is {value:.4g}, " + (
                    f"under {low:g}" if low is not None and value < low else f"over {high:g}")
        rows.append({"id": str(predicate.get("id", name)), "metric": name, "value": value,
                     "min": low, "max": high, "pass": passed, "why": why})
    return rows
