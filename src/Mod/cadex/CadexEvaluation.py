# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""What a rollout did, as numbers a success spec can be held against (ADR-455).

A reward says what a policy was paid for, and a policy that was paid and
shuffled is the failure this module exists to see. It reads a rollout trace
(``cadex-assembly-simulation-trace-v1``: every component's pose at every
control step) and a handful of facts about the model it ran, and returns
**behaviour metrics**: what the mechanism did, none of them the reward.

Four families, and nothing in the module knows which behaviour it is
reading -- each family is asked for by what the caller names, not by a task
kind:

* **posture**, for anything with a floating base: tilt, heading, drift from
  where it started, and the time it takes to come back to rest after a shove;
* **gait**, for anything with feet: steps as opposed to chatter, foot
  clearance, stance slip, duty factor, how deep a foot went into the floor,
  and how well a commanded speed was tracked;
* **reach**, for anything with a tip and a target: final error, time to
  target and overshoot, per target;
* **motion**, for any body and a point it is judged about: net signed turns
  and laps about an axis through the point, and the body's distance from it
  -- what a body did over the episode, not only where it ended (ADR-587);
* **drive**, for any trace that records its drives (ADR-694): how smooth the
  commands and the joints were, how hard each drive was pushed against its
  clamp and its continuous rating (ADR-707), and what the motion cost per
  unit of weight and distance (ADR-704);
* **tracking**, for a floating base and the commands an episode issued
  (ADR-721): how closely the base's forward speed and yaw rate followed a
  commanded speed and yaw rate that change during the episode, outside a
  settling window after each change, and how far a commanded 180-degree
  turn was from done when the command said it should be;
* **reference**, for feet and a task's gait reference (ADR-703): the
  footfall against the reference's phase offsets and duty factor, the stride
  frequency against its, and the joints' RMS error from it, phase-aligned
  stride by stride (ADR-705); and how smooth the drives were against the
  clip's own smoothness on the same drives (ADR-708).

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
#: A drive is at its clamp when its effort is within this share of the
#: limit. MuJoCo clamps exactly, so a clamped sample equals the limit, and
#: the share only absorbs the float rounding of the gear and the unit.
CLAMP_TOLERANCE = 1.0e-3
#: Command power above this multiple of the stride frequency is not the
#: gait: a stride's own shape lives in its first few harmonics, and what is
#: above them is jitter (ADR-704).
HIGH_FREQUENCY_STRIDE_MULTIPLE = 3.0

#: Command tracking (ADR-721) reads the base's speed and yaw rate over a
#: centred window this long -- about a stride at the gaits it is read on, so
#: the surge and sway inside one stride are not charged as tracking error --
#: and skips this long after every change of any command, which is the time
#: a policy is given to respond to it.
TRACKING_WINDOW_S = 0.5
TRACKING_SETTLE_S = 0.5
#: A reversal is a held yaw-rate command that turns the commanded heading
#: through this much; it is judged at the moment the command has done so.
REVERSAL_DEG = 180.0

#: How close a base must come to a ground point to have reached it
#: (ADR-751): 0.3 m, the bar orun8's charter sets for its cat (C2).
WAYPOINT_REACH_MM = 300.0

#: The foot whose touch-downs are a reference's clock: the left hind, the
#: foot every phase offset is stated after (Hildebrand's convention).
REFERENCE_ANCHOR = "LH"
#: A biped reference's clock: its left foot (ADR-754).
BIPED_REFERENCE_ANCHOR = "L"

#: A fall (ADR-718): the base tilted this far from its reference pose, or its
#: centre of mass came down to this share of its starting height above the
#: ground under it. Either is a robot on the ground, whatever its task's own
#: terminations say.
FALL_TILT_DEG = 60.0
FALL_HEIGHT_SHARE = 0.5
#: A foot that does not touch down exactly once within half a stride of
#: where the reference puts it has missed that stride by this much: as far
#: out of phase as a periodic event can be.
FOOTFALL_MISSED = 0.5

#: Every metric a success predicate may bound, and what measuring it needs
#: (ADR-456). This is the whole vocabulary of a success spec: a name that is
#: not here is not a behaviour metric, and the task's reward, its reward
#: terms and its observation channels are deliberately not here.
#:
#: The needs are facts about the spec and the model, never about a
#: behaviour: ``base`` is a floating base, ``floor`` the one plane it stands
#: on, ``feet`` and ``tip`` what the spec names, ``shove`` a timed
#: disturbance in the spec's conditions, ``command`` a speed goal the task
#: states, ``turn`` a yaw-rate goal it states (ADR-721) and ``target`` a
#: point goal it states (ADR-462). ``body`` is a body the spec names to be
#: judged about a centre (ADR-587). ``appendage`` is a chain of bodies the
#: spec names that hangs from the base and is not a leg -- a tail, a trunk,
#: a mast (ADR-722).
METRICS: dict[str, tuple[str, tuple[str, ...]]] = {
    "completed": ("episode", ()),
    "duration_s": ("episode", ()),
    "max_tilt_deg": ("posture", ("base",)),
    "max_heading_deg": ("posture", ("base",)),
    "final_heading_deg": ("posture", ("base",)),
    "max_drift_mm": ("posture", ("base",)),
    "final_drift_mm": ("posture", ("base",)),
    "mean_speed_mm_s": ("posture", ("base",)),
    "distance_made_good_mm": ("posture", ("base",)),
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
    "speed_error_rms_mm_s": ("tracking", ("base", "command")),
    "yaw_rate_error_rms_deg_s": ("tracking", ("base", "turn")),
    "reversal_heading_error_deg_max": ("tracking", ("base", "turn")),
    "waypoint_miss_mm_max": ("waypoint", ("base", "waypoint")),
    "waypoints_reached": ("waypoint", ("base", "waypoint")),
    "speed_ratio": ("gait", ("feet", "command")),
    "lateral_ratio": ("gait", ("feet", "command")),
    "final_error_mm_max": ("reach", ("tip", "target")),
    "final_error_arm_lengths_max": ("reach", ("tip", "target")),
    "time_to_target_s_max": ("reach", ("tip", "target")),
    "overshoot_ratio_max": ("reach", ("tip", "target")),
    "turns": ("motion", ("body",)),
    "laps": ("motion", ("body",)),
    "final_distance_mm": ("motion", ("body",)),
    "mean_distance_mm": ("motion", ("body",)),
    "max_distance_mm": ("motion", ("body",)),
    "command_rate_rms": ("drive", ()),
    "joint_acceleration_rms_deg_s2": ("drive", ()),
    "command_high_frequency_share": ("drive", ("feet",)),
    "effort_rms_clamp_ratio_max": ("drive", ()),
    "effort_clamp_share_max": ("drive", ()),
    "effort_rms_rated_ratio_max": ("drive", ()),
    "cost_of_transport": ("drive", ("base",)),
    "footfall_phase_error_max": ("reference", ("feet", "reference")),
    "duty_factor_error_max": ("reference", ("feet", "reference")),
    "stride_frequency_ratio": ("reference", ("feet", "reference")),
    "reference_joint_rms_deg": ("reference", ("feet", "reference")),
    "command_rate_reference_ratio": ("reference", ("feet", "reference")),
    "joint_acceleration_reference_ratio": ("reference", ("feet", "reference")),
    "appendage_ground_contact_share": ("appendage", ("base", "appendage")),
    "appendage_pitch_parent_correlation": ("appendage", ("base", "appendage")),
    "appendage_yaw_turn_correlation": ("appendage", ("base", "appendage", "turn")),
    "falls": ("terrain", ("base",)),
    "steps_crossed": ("terrain", ("base", "terrain")),
    "slopes_crossed": ("terrain", ("base", "terrain")),
    "largest_step_crossed_mm": ("terrain", ("base", "terrain")),
    "steepest_slope_crossed_deg": ("terrain", ("base", "terrain")),
    "platforms_crossed": ("terrain", ("base", "terrain")),
    "highest_platform_crossed_mm": ("terrain", ("base", "terrain")),
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
        "drives": drive_series(raw["frames"], raw.get("actuator_channels") or ()),
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
    ahead, end = base["forward"][0], base["point"][-1]
    return {
        # ADR-718: net plan travel along the heading the episode started on.
        "distance_made_good_mm": ((end[0] - start[0]) * ahead[0]
                                  + (end[1] - start[1]) * ahead[1]),
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
            "lift_s": float(time[start]), "land_s": float(time[end + 1]),
            "airborne_s": (end - start + 1) * dt,
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
        # Each step's landing: the first stance frame after it (ADR-705).
        "touchdowns_s": [s["land_s"] for s in steps],
        # The frame interval the landings lie on, so a timing read in
        # frames is whole frames (ADR-719).
        "frame_s": dt,
        # Steps begun after the settle, per settled second: one step per
        # stride, so this is the foot's stride frequency (ADR-704).
        "step_rate_hz": (
            sum(1 for s in steps if s["lift_s"] >= settle_s - _EPS) / (time[-1] - settle_s)
            if time[-1] - settle_s > _EPS else None
        ),
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


def waypoint_metrics(samples, rig: Mapping[str, Any],
                     waypoints: Sequence[Mapping[str, Any]], *,
                     reach_mm: float = WAYPOINT_REACH_MM) -> dict[str, Any]:
    """How close a floating base came to each ground point it was sent to (ADR-751).

    ``waypoints`` is ``[{"start_s", "end_s", "point_mm": [x, y]}]``: the
    world point in force over each stretch of the episode. A frame on a
    boundary belongs to the stretch that starts there; a stretch the episode
    ended before is not read. The base is its centre of mass in plan.

    * ``waypoint_miss_mm_max``: for each stretch read, the closest the base
      came to its point while it was up; the worst one. ``None`` when no
      stretch was read.
    * ``waypoints_reached``: how many stretches came within ``reach_mm``.
    """

    base = base_series(samples, rig)
    times, points = base["time"], base["point"]
    end = times[-1] if times else 0.0
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(waypoints):
        start, stop = float(row["start_s"]), float(row["end_s"])
        if start > end + _EPS:
            continue
        x, y = (float(value) for value in row["point_mm"])
        last = index == len(waypoints) - 1
        held = [i for i, moment in enumerate(times)
                if start - _EPS <= moment and (last or moment < stop - _EPS)]
        if not held:
            continue
        closest = min(held, key=lambda i: math.hypot(points[i][0] - x, points[i][1] - y))
        miss = math.hypot(points[closest][0] - x, points[closest][1] - y)
        rows.append({"start_s": start, "end_s": stop, "point_mm": [x, y],
                     "miss_mm": miss, "closest_s": times[closest],
                     "reached": miss <= reach_mm})
    return {
        "waypoint_miss_mm_max": max(row["miss_mm"] for row in rows) if rows else None,
        "waypoints_reached": float(sum(1 for row in rows if row["reached"])),
        "waypoints": rows,
    }


def tracking_metrics(samples, rig: Mapping[str, Any],
                     commands: Mapping[str, Sequence[float]], *,
                     settle_s: float = SETTLE_S, window_s: float = TRACKING_WINDOW_S,
                     change_settle_s: float = TRACKING_SETTLE_S,
                     reversal_deg: float = REVERSAL_DEG) -> dict[str, Any]:
    """How closely a floating base followed commands that change (ADR-721).

    ``commands`` maps ``"speed"`` (mm/s, forward along the base's heading)
    and ``"yaw_rate"`` (deg/s about world +Z, anticlockwise positive) to the
    value in force at each sample, one per sample; either may be absent.

    The base's speed and yaw rate at a frame are read over a centred window
    of ``window_s``: the speed as each frame's step along that frame's
    heading, summed, so a base on a curve is not read as slow. A frame is counted when the window fits inside the
    episode, the frame is past ``settle_s``, and no command of either kind
    changed from ``change_settle_s`` before it to the end of its window --
    so a policy is not charged for the moment it is told something new, and
    a frame is not read against a command its window has already left.

    * ``speed_error_rms_mm_s`` and ``yaw_rate_error_rms_deg_s``: the RMS of
      measured minus commanded over the counted frames.
    * ``reversal_heading_error_deg_max``: for every held yaw-rate command
      that turns the commanded heading through ``reversal_deg`` before it
      changes, the base's heading error at the moment the command has done
      so (``reversal_deg / |rate|`` after it was issued) -- a 180-degree
      turn at 60 deg/s is judged 3 s after it is commanded. The worst one;
      ``None`` when the episode commanded none, or ended first.

    Each is ``None`` when nothing could be counted, which a predicate reads
    as a failure.
    """

    base = base_series(samples, rig)
    times, n = base["time"], len(base["time"])
    series = {kind: [float(value) for value in values]
              for kind, values in commands.items() if values is not None}
    for kind, values in series.items():
        if len(values) != n:
            raise ValueError(f"{kind} commands hold {len(values)} values for {n} samples")
    half = max(1, int(round(0.5 * window_s / base["dt"]))) if n > 1 else 1
    changes = sorted({times[i] for values in series.values()
                      for i in range(1, n) if values[i] != values[i - 1]})

    def counted(i: int) -> bool:
        if i - half < 0 or i + half >= n or times[i] < settle_s - _EPS:
            return False
        return not any(times[i] - change_settle_s < moment <= times[i + half] + _EPS
                       for moment in changes)

    frames = [i for i in range(n) if counted(i)]
    speed_errors, yaw_errors = [], []
    for i in frames:
        a, b = i - half, i + half
        span = times[b] - times[a]
        if "speed" in series:
            # Each frame's step along that frame's own heading: a chord
            # across the window would read a turning base as slow.
            along = sum(
                (base["point"][k + 1][0] - base["point"][k][0]) * base["forward"][k][0]
                + (base["point"][k + 1][1] - base["point"][k][1]) * base["forward"][k][1]
                for k in range(a, b)
            ) / span
            speed_errors.append(along - series["speed"][i])
        if "yaw_rate" in series:
            yaw_errors.append((base["heading"][b] - base["heading"][a]) / span
                              - series["yaw_rate"][i])

    reversals: list[dict[str, Any]] = []
    rates = series.get("yaw_rate")
    if rates:
        starts = [0] + [i for i in range(1, n) if rates[i] != rates[i - 1]]
        for k, start in enumerate(starts):
            rate = rates[start]
            if abs(rate) < _EPS:
                continue
            due = times[start] + reversal_deg / abs(rate)
            # The command holds until the next one is issued; the last one
            # holds to the episode's end.
            until = times[starts[k + 1]] if k + 1 < len(starts) else times[-1]
            if due > until + _EPS:
                continue
            at = min(range(start, n), key=lambda i: abs(times[i] - due))
            turned = base["heading"][at] - base["heading"][start]
            reversals.append({
                "start_s": times[start], "due_s": times[at], "yaw_rate_deg_s": rate,
                "turned_deg": turned,
                "heading_error_deg": abs(turned - math.copysign(reversal_deg, rate)),
            })
    return {
        "speed_error_rms_mm_s": _rms(speed_errors) if "speed" in series else None,
        "yaw_rate_error_rms_deg_s": _rms(yaw_errors) if "yaw_rate" in series else None,
        "reversal_heading_error_deg_max": (
            max(row["heading_error_deg"] for row in reversals) if reversals else None
        ),
        "tracking": {"frames_counted": len(frames), "frames": n,
                     "command_changes_s": changes, "reversals": reversals},
    }


# -- an appendage -----------------------------------------------------------

def _pearson(a: Sequence[float], b: Sequence[float]) -> float | None:
    """Pearson's r, or ``None`` when either series does not vary."""

    if len(a) < 2:
        return None
    mean_a, mean_b = sum(a) / len(a), sum(b) / len(b)
    da = [x - mean_a for x in a]
    db = [y - mean_b for y in b]
    spread = math.sqrt(sum(x * x for x in da) * sum(y * y for y in db))
    if spread <= _EPS:
        return None
    return sum(x * y for x, y in zip(da, db)) / spread


def appendage_metrics(samples, rig: Mapping[str, Any], *,
                      yaw_rates: Sequence[float] | None = None,
                      ground: Any = None, settle_s: float = SETTLE_S,
                      contact_mm: float = STANCE_MM) -> dict[str, Any]:
    """What a chain hanging from the base did that is not a leg's (ADR-722).

    ``rig["appendage"]`` is ``{"bodies": [root, ..., last], "geoms": {body:
    [geom, ...]}, "parent": body}``: the chain from the body nearest the base
    outward, each body's collision primitives (as a foot's), and the body the
    root hangs from. ``ground(x_mm, y_mm)`` is the ground's height, as
    :func:`terrain_metrics` takes; ``None`` is the rig's floor.

    * ``appendage_ground_contact_share``: the share of frames in which any
      collision primitive of the chain is within ``contact_mm`` of the
      ground under its lowest point -- a tail that strikes the floor once a
      stride reads its stance share, and one carried clear reads 0.
    * ``appendage_pitch_parent_correlation``: Pearson's r, over the frames
      past ``settle_s``, between the root's pitch and its parent's. A body's
      pitch is the elevation of the base's starting forward direction as
      that body carries it, so the two are compared on one axis whatever
      each body's own frame is. Near 1 is a chain carried rigidly by the
      body it hangs from (it rises and falls with the hips); near 0, its
      root joint works against that body's pitch.
    * ``appendage_yaw_turn_correlation``: with ``yaw_rates`` (the commanded
      yaw rate at each sample, deg/s), the magnitude of Pearson's r between
      that command and the chain's yaw relative to the base -- the plan
      bearing from the root's origin to the centre of the last body's last
      primitive, against the base's heading -- over the frames past
      ``settle_s``. Its magnitude, because whether a tail swings into a turn
      or out of it is the mechanism's choice; the sign and the slope are in
      the detail. ``None`` when the command never changed.

    Each is ``None`` when it cannot be read, which a predicate reads as a
    failure.
    """

    chain = rig["appendage"]
    bodies = [str(name) for name in chain["bodies"]]
    floor = float(rig.get("floor_mm") or 0.0)
    level = (lambda x, y: floor) if ground is None else ground
    reference = matrix(rig["reference_xyzw"])
    times, clearance, root_pitch, parent_pitch, yaw = [], [], [], [], []
    carried: dict[str, Vector] = {}
    last = bodies[-1]
    tail_geom = (chain["geoms"].get(last) or [None])[-1]
    for time_s, placements in samples:
        times.append(float(time_s))
        low = math.inf
        for name in bodies:
            rotation, origin = _pose(placements, name)
            for geom in chain["geoms"].get(name) or ():
                point = _lowest(geom, rotation, origin)[1]
                low = min(low, point[2] - float(level(point[0], point[1])))
        clearance.append(low)
        base_rotation, _ = _pose(placements, rig["base"])
        if not carried:
            ahead = forward(base_rotation, reference)
            start = (ahead[0], ahead[1], 0.0)
            for name in (bodies[0], str(chain["parent"])):
                carried[name] = _apply_inverse(_pose(placements, name)[0], start)
        pitches = []
        for name in (bodies[0], str(chain["parent"])):
            rotation, _ = _pose(placements, name)
            axis = _apply(rotation, carried[name])
            pitches.append(math.degrees(math.atan2(axis[2], math.hypot(axis[0], axis[1]))))
        root_pitch.append(pitches[0])
        parent_pitch.append(pitches[1])
        root_rotation, root_origin = _pose(placements, bodies[0])
        last_rotation, last_origin = _pose(placements, last)
        end = (last_origin if tail_geom is None
               else _add(_apply(last_rotation, tail_geom["pos_mm"]), last_origin))
        ahead = forward(base_rotation, reference)
        bearing = math.degrees(math.atan2(end[1] - root_origin[1], end[0] - root_origin[0])
                               - math.atan2(ahead[1], ahead[0]))
        if yaw:
            bearing += 360.0 * round((yaw[-1] - bearing) / 360.0)
        yaw.append(bearing)
    late = [i for i, moment in enumerate(times) if moment >= settle_s - _EPS]
    measured = [value for value in clearance if math.isfinite(value)]
    read: dict[str, Any] = {
        "appendage_ground_contact_share": (
            sum(1 for value in measured if value <= contact_mm) / len(measured)
            if measured else None
        ),
        "appendage_pitch_parent_correlation": _pearson(
            [root_pitch[i] for i in late], [parent_pitch[i] for i in late]),
    }
    detail: dict[str, Any] = {
        "bodies": bodies, "parent": str(chain["parent"]),
        "min_clearance_mm": min(measured) if measured else None,
        "root_pitch_sd_deg": statistics.pstdev([root_pitch[i] for i in late]) if late else None,
        "parent_pitch_sd_deg": statistics.pstdev([parent_pitch[i] for i in late]) if late else None,
        "yaw_sd_deg": statistics.pstdev([yaw[i] for i in late]) if late else None,
    }
    if yaw_rates is not None:
        if len(yaw_rates) != len(times):
            raise ValueError(f"yaw rates hold {len(yaw_rates)} values for {len(times)} samples")
        command = [float(yaw_rates[i]) for i in late]
        swing = [yaw[i] for i in late]
        r = _pearson(command, swing)
        read["appendage_yaw_turn_correlation"] = None if r is None else abs(r)
        detail["yaw_turn_r"] = r
        if r is not None:
            mean_c = sum(command) / len(command)
            mean_s = sum(swing) / len(swing)
            detail["yaw_deg_per_deg_s"] = (
                sum((c - mean_c) * (y - mean_s) for c, y in zip(command, swing))
                / sum((c - mean_c) ** 2 for c in command))
    read["appendage"] = detail
    return read


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
    segment that starts there. A segment with ``"frame"`` holds its target
    in that body's frame (ADR-592), so the tip is read in the same frame at
    every frame of the trace: the distance is the one to where the target
    really was at that moment, however the body carrying it moved.

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
    times, world = tip_series(samples, rig["tip"])
    framed: dict[str, list[Vector]] = {}
    rows = []
    for index, segment in enumerate(segments):
        start_s, end_s = float(segment["start_s"]), float(segment["end_s"])
        target = tuple(float(v) for v in segment["target_mm"])
        frame = segment.get("frame")
        if frame is not None and frame not in framed:
            framed[frame] = [
                _apply_inverse(rotation, _sub(point, origin))
                for point, (rotation, origin) in zip(
                    world, (_pose(placements, frame) for _time, placements in samples),
                    strict=True,
                )
            ]
        points = world if frame is None else framed[frame]
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
            **({"frame": frame} if frame is not None else {}),
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


# -- a tool along a path, and over an area (ADR-645) -------------------------
#
# The machine readings of a trace: a tool point (``tip_series``'s point) held
# against a declared polyline, and swept over a declared region. Pure and
# in millimetres like the rest; a success spec does not name them yet --
# they are read by whoever holds the path or the region (ADR-645 says what
# wiring them into api.success needs).


def _point_to_segment(point: Sequence[float], a: Sequence[float], b: Sequence[float]) -> tuple[float, float]:
    """Distance from ``point`` to segment ``ab``, and how far along it (0-1) the foot lies."""

    ab = _sub(b, a)
    length2 = sum(v * v for v in ab)
    t = 0.0 if length2 <= _EPS else max(0.0, min(1.0, sum(x * y for x, y in zip(_sub(point, a), ab)) / length2))
    foot = tuple(a[i] + t * ab[i] for i in range(3))
    return math.dist(point, foot), t


def path_metrics(points: Sequence[Sequence[float]], path_mm: Sequence[Sequence[float]]) -> dict[str, Any]:
    """How closely a tool followed a polyline, and how much of it it covered.

    ``points`` are the tool point per frame (``tip_series``) and ``path_mm``
    the polyline's vertices, both in one frame. ``max_path_error_mm`` and
    ``mean_path_error_mm`` are the tool's distance to the nearest point of
    the polyline; ``path_progress`` is the share of the polyline's length
    up to the furthest point the tool came within ``tolerance`` of, so a
    tool that stays on the line but stops halfway reads 0.5.
    """

    if len(path_mm) < 2:
        raise ValueError("a path needs at least two vertices")
    vertices = [tuple(float(v) for v in p) for p in path_mm]
    lengths = [math.dist(a, b) for a, b in zip(vertices, vertices[1:])]
    total = sum(lengths)
    errors, furthest = [], 0.0
    for point in points:
        best, along = math.inf, 0.0
        start = 0.0
        for (a, b), length in zip(zip(vertices, vertices[1:]), lengths):
            distance, t = _point_to_segment(point, a, b)
            if distance < best - _EPS:
                best, along = distance, start + t * length
            start += length
        errors.append(best)
        furthest = max(furthest, along)
    return {
        "max_path_error_mm": max(errors) if errors else None,
        "mean_path_error_mm": sum(errors) / len(errors) if errors else None,
        "path_progress": furthest / total if total > _EPS else None,
        "path_length_mm": total,
    }


def coverage_metrics(points: Sequence[Sequence[float]], region_mm: Sequence[Sequence[float]], *,
                     footprint_mm: float, cell_mm: float | None = None) -> dict[str, Any]:
    """The share of a plan region a tool's footprint swept (a mower, a sprayer).

    ``region_mm`` is a polygon in XY (counter-clockwise or not); the tool's
    footprint is a disc of diameter ``footprint_mm`` about its point, swept
    between frames along the straight line joining them. The region is
    rasterised at ``cell_mm`` (default a quarter of the footprint) and a
    cell is covered when its centre came within half the footprint of the
    tool's path. ``coverage`` is covered cells over cells inside the region.
    """

    radius = float(footprint_mm) / 2.0
    if radius <= 0.0:
        raise ValueError("footprint_mm must be positive")
    cell = float(cell_mm) if cell_mm else radius / 2.0
    polygon = [(float(p[0]), float(p[1])) for p in region_mm]
    if len(polygon) < 3:
        raise ValueError("a region needs at least three vertices")

    def inside(x: float, y: float) -> bool:
        crossing = False
        for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1]):
            if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                crossing = not crossing
        return crossing

    xs, ys = [p[0] for p in polygon], [p[1] for p in polygon]
    track = [(float(p[0]), float(p[1]), 0.0) for p in points]
    cells = covered = 0
    y = min(ys) + cell / 2.0
    while y < max(ys):
        x = min(xs) + cell / 2.0
        while x < max(xs):
            if inside(x, y):
                cells += 1
                centre = (x, y, 0.0)
                if any(_point_to_segment(centre, a, b)[0] <= radius
                       for a, b in zip(track, track[1:] or track)):
                    covered += 1
            x += cell
        y += cell
    return {"coverage": covered / cells if cells else None, "cells": cells, "cell_mm": cell,
            "footprint_mm": float(footprint_mm)}


# -- a body about a centre --------------------------------------------------

#: A body this close to the axis has no bearing about it, and a frame there
#: does not advance the turn count either way.
MOTION_AXIS_MM = 1.0e-6


def _unit(vector: Sequence[float]) -> Vector:
    length = math.sqrt(sum(float(v) * float(v) for v in vector))
    if length <= _EPS:
        raise ValueError("a motion axis must not be zero")
    return (float(vector[0]) / length, float(vector[1]) / length, float(vector[2]) / length)


def _cross(a: Sequence[float], b: Sequence[float]) -> Vector:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def body_in_centre(samples, body: Mapping[str, Any],
                   centre: Mapping[str, Any]) -> tuple[list[float], list[Vector]]:
    """The body's point relative to the centre, in the centre's frame, per frame.

    ``body`` is ``{"body", "local_mm"}``: a fixed point on one body.
    ``centre`` is ``{"frame", "point_mm", "axis"}``: ``frame`` names the body
    whose frame the point and axis are fixed in, or is ``None`` for the
    world. A centre on a plate that tilts and turns moves with it, so a ball
    held still on the plate reads as still.
    """

    point = tuple(float(v) for v in centre.get("point_mm") or (0.0, 0.0, 0.0))
    frame = centre.get("frame")
    times, rows = [], []
    for time_s, placements in samples:
        rotation, origin = _pose(placements, body["body"])
        world = _add(_apply(rotation, body.get("local_mm") or (0.0, 0.0, 0.0)), origin)
        if frame is not None:
            frame_rotation, frame_origin = _pose(placements, frame)
            world = _apply_inverse(frame_rotation, _sub(world, frame_origin))
        times.append(float(time_s))
        rows.append(_sub(world, point))
    return times, rows


def turns_about(relative: Sequence[Sequence[float]], axis: Sequence[float]) -> float:
    """Net signed turns of a path about an axis through the origin.

    Right-handed about ``axis``: anticlockwise seen from its tip is positive.
    Each frame adds the bearing change from the last, wrapped to half a turn
    either way, so a body that goes round twice reads 2.0 and one that rocks
    out along an arc and back reads about zero, however far the arc.
    """

    axis = _unit(axis)
    seed = (1.0, 0.0, 0.0) if abs(axis[0]) < 0.9 else (0.0, 1.0, 0.0)
    u = _unit(_cross(axis, _cross(seed, axis)))
    v = _cross(axis, u)
    total, last = 0.0, None
    for row in relative:
        x = sum(a * b for a, b in zip(row, u))
        y = sum(a * b for a, b in zip(row, v))
        if math.hypot(x, y) <= MOTION_AXIS_MM:
            continue
        bearing = math.atan2(y, x)
        if last is not None:
            step = bearing - last
            step -= 2.0 * math.pi * round(step / (2.0 * math.pi))
            total += step
        last = bearing
    return total / (2.0 * math.pi)


def motion_metrics(samples, rig: Mapping[str, Any], *, completed: bool) -> dict[str, Any]:
    """How a body moved about a centre over the episode (ADR-587).

    * ``turns``: net signed turns about the centre's axis -- positive
      anticlockwise seen from the axis tip;
    * ``laps``: whole turns completed in the net direction, ``floor(|turns|)``;
    * ``final_distance_mm``, ``mean_distance_mm``, ``max_distance_mm``: the
      body's straight distance from the centre point at the last frame, on
      average over the frames, and at its furthest.

    These are measurements of *the episode*, and **an episode that did not
    run to its horizon was not one**: every metric is then ``None``, so a
    spec bounding any of them fails, as ADR-586 fails a reach that ended
    before its window. What was played is kept in ``motion`` for the report
    either way, marked ``partial``. Fewer than two frames is also unmeasured.
    """

    times, relative = body_in_centre(samples, rig["body"], rig["centre"])
    distances = [math.sqrt(sum(v * v for v in row)) for row in relative]
    played: dict[str, Any] = {"frames": len(relative), "partial": not completed}
    if len(relative) >= 2:
        turns = turns_about(relative, rig["centre"].get("axis") or (0.0, 0.0, 1.0))
        played.update({
            "turns": turns,
            "laps": float(math.floor(abs(turns) + _EPS)),
            "final_distance_mm": distances[-1],
            "mean_distance_mm": sum(distances) / len(distances),
            "max_distance_mm": max(distances),
            "duration_s": times[-1] - times[0],
        })
    names = ("turns", "laps", "final_distance_mm", "mean_distance_mm", "max_distance_mm")
    measured = completed and len(relative) >= 2
    return {**{name: played[name] if measured else None for name in names}, "motion": played}


# -- the episode, and a spec held against all of it -------------------------

# -- drives -----------------------------------------------------------------

def drive_series(frames: Sequence[Mapping[str, Any]],
                 channels: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    """Each drive's command, joint state and effort, per solved frame (ADR-694).

    ``frames`` are a trace's frames and ``channels`` its
    ``actuator_channels``. A command and an effort are ``None`` on the reset
    frame, where no action has been taken. ``None`` back means the trace does
    not record its drives -- one written before ADR-694 -- so the drive
    family is not read from it, rather than read as a mechanism that held
    still.
    """

    solved = [frame for frame in frames if frame.get("frame_kind") == "solver_output"]
    if (not channels or not solved
            or any("joint_positions" not in f or "joint_velocities" not in f for f in solved)):
        return None

    def row(frame: Mapping[str, Any], key: str) -> list[float] | None:
        return None if key not in frame else [float(value) for value in frame[key]]

    return {
        "channels": [dict(channel) for channel in channels],
        "time": [float(frame["nominal_time_s"]) for frame in solved],
        "positions": [row(frame, "joint_positions") for frame in solved],
        "velocities": [row(frame, "joint_velocities") for frame in solved],
        "commands": [row(frame, "actuator_commands") for frame in solved],
        "efforts": [row(frame, "actuator_efforts") for frame in solved],
    }


def _rms(values: Sequence[float]) -> float | None:
    return math.sqrt(sum(v * v for v in values) / len(values)) if values else None


def power_spectrum(values: Sequence[float]) -> list[float]:
    """Power per frequency bin ``k = 1 .. n//2`` of a Hann-windowed series.

    The mean is removed first, so bin 0 (the held part of a command) is not
    power. Bin ``k`` is ``k / (n * dt)`` hertz. The window keeps a stride
    that does not fit the record a whole number of times from leaking its
    fundamental into every bin above it, which would read as jitter.
    """

    n = len(values)
    mean = sum(values) / n
    x = [(v - mean) * (0.5 - 0.5 * math.cos(2.0 * math.pi * i / n))
         for i, v in enumerate(values)]
    cos_t = [math.cos(2.0 * math.pi * i / n) for i in range(n)]
    sin_t = [math.sin(2.0 * math.pi * i / n) for i in range(n)]
    power = []
    for k in range(1, n // 2 + 1):
        real = imag = 0.0
        for i, v in enumerate(x):
            j = (k * i) % n
            real += v * cos_t[j]
            imag -= v * sin_t[j]
        power.append(real * real + imag * imag)
    return power


def drive_metrics(drives: Mapping[str, Any], *, weight_n: float | None = None,
                  travel: tuple[float, float] | None = None,
                  stride_hz: float | None = None, settle_s: float = SETTLE_S,
                  clamp_tolerance: float = CLAMP_TOLERANCE,
                  high_frequency_multiple: float = HIGH_FREQUENCY_STRIDE_MULTIPLE) -> dict[str, Any]:
    """How smoothly the drives moved, how hard they worked, and what it cost.

    Read from :func:`drive_series`. Smoothness and cost are read after the
    settle, like the gait, so the landing from the reset lift is not jitter;
    effort is read over every frame that has one, because a drive at its
    clamp while the robot lands is at its clamp.

    * ``command_rate_rms``: the RMS over every channel and settled frame of
      the command's change per second, in **channel ranges per second** --
      a command over the width of its own range, so a torque drive and a
      position drive pool on one scale.
    * ``joint_acceleration_rms_deg_s2``: the RMS of each angular joint's
      velocity change per second, pooled; ``None`` with no angular drive.
    * ``command_high_frequency_share``: of the command power (each channel
      in its own ranges, Hann-windowed, mean removed), the share above
      ``high_frequency_multiple`` times ``stride_hz``. ``None`` without a
      stride, or when that frequency is above the frames' Nyquist limit and
      nothing above it was recorded.
    * ``effort_rms_clamp_ratio_max`` and ``effort_clamp_share_max``: the
      worst drive's RMS effort over its clamp, and its share of samples
      within ``clamp_tolerance`` of the clamp. A drive the model does not
      limit has no clamp and is not among them.
    * ``effort_rms_rated_ratio_max``: the worst drive's RMS effort over its
      continuous rating (ADR-707), over the whole episode like the clamp
      ratio. ``None`` when no drive declares a rating, so a spec bounding it
      fails rather than passes on a model that never said.
    * ``cost_of_transport``: mean mechanical power, the sum over drives of
      ``|effort x joint velocity|``, over weight times speed, where the
      speed is ``travel`` -- the base's net plan distance over the settled
      seconds. ``None`` with no base, no weight, or no net travel.

    ``drives`` in the result keeps each drive's own figures, the stride
    frequency used and the mean power, in N·mm/s (this module converts no
    unit; a watt is a thousand of them).
    """

    channels = drives["channels"]
    times = drives["time"]
    settled = [i for i, moment in enumerate(times) if moment >= settle_s - _EPS]
    commanded = [i for i in settled if drives["commands"][i] is not None]
    pairs = [(a, b) for a, b in zip(commanded, commanded[1:]) if b == a + 1]
    rows: list[dict[str, Any]] = []
    rate_sq: list[float] = []
    accel_sq: list[float] = []
    clamp_ratios: list[float] = []
    clamp_shares: list[float] = []
    rated_ratios: list[float] = []
    hf_power = total_power = 0.0
    dt = _frame_interval(times) if len(times) > 1 else 0.0
    cutoff = None if stride_hz is None or stride_hz <= 0.0 else high_frequency_multiple * stride_hz
    resolvable = cutoff is not None and dt > 0.0 and cutoff < 0.5 / dt and len(commanded) >= 8
    for c, channel in enumerate(channels):
        width = float(channel["high"]) - float(channel["low"])
        width = width if width > _EPS else 1.0
        rates = [(drives["commands"][b][c] - drives["commands"][a][c])
                 / (times[b] - times[a]) / width for a, b in pairs]
        rate_sq.extend(r * r for r in rates)
        rotary = str(channel.get("motion_type")) == "angular"
        accels = [(drives["velocities"][i + 1][c] - drives["velocities"][i][c])
                  / (times[i + 1] - times[i])
                  for i in settled if i + 1 < len(times)]
        if rotary:
            accel_sq.extend(a * a for a in accels)
        efforts = [row[c] for row in drives["efforts"] if row is not None]
        effort_rms = _rms(efforts)
        low, high = channel.get("effort_low"), channel.get("effort_high")
        limit = max(abs(float(v)) for v in (low, high) if v is not None) if (
            low is not None or high is not None) else None
        share = ratio = None
        if limit and efforts:
            at = sum(1 for e in efforts
                     if (high is not None and e >= float(high) - clamp_tolerance * abs(float(high)))
                     or (low is not None and e <= float(low) + clamp_tolerance * abs(float(low))))
            share, ratio = at / len(efforts), effort_rms / limit
            clamp_shares.append(share)
            clamp_ratios.append(ratio)
        rated = channel.get("effort_rated")
        rated_ratio = (effort_rms / float(rated)
                       if rated is not None and float(rated) > _EPS and efforts else None)
        if rated_ratio is not None:
            rated_ratios.append(rated_ratio)
        channel_hf = None
        if resolvable:
            power = power_spectrum([drives["commands"][i][c] / width for i in commanded])
            n = len(commanded)
            above = sum(p for k, p in enumerate(power, start=1) if k / (n * dt) > cutoff)
            hf_power += above
            total_power += sum(power)
            channel_hf = above / sum(power) if sum(power) > _EPS else None
        rows.append({
            "actuator": str(channel.get("actuator", "")),
            "joint": str(channel.get("joint", "")),
            "command_rate_rms": _rms(rates),
            "joint_acceleration_rms": _rms(accels),
            "effort_rms": effort_rms,
            "effort_limit": limit,
            "effort_rms_clamp_ratio": ratio,
            "effort_clamp_share": share,
            "effort_rated": None if rated is None else float(rated),
            "effort_rms_rated_ratio": rated_ratio,
            "command_high_frequency_share": channel_hf,
        })
    # In the trace's own units -- N·mm times rad/s (or N times mm/s) is
    # N·mm/s, over newtons times mm/s -- so the ratio needs no factor.
    power = []
    for i in settled:
        effort, velocity = drives["efforts"][i], drives["velocities"][i]
        if effort is None:
            continue
        power.append(sum(
            abs(e * (math.radians(v) if str(ch.get("motion_type")) == "angular" else v))
            for e, v, ch in zip(effort, velocity, channels)))
    mean_power = (sum(power) / len(power)) if power else None
    cost = None
    if mean_power is not None and weight_n and travel is not None and travel[1] > _EPS:
        speed_mm_s = travel[0] / travel[1]
        if speed_mm_s > _EPS:
            cost = mean_power / (float(weight_n) * speed_mm_s)
    return {
        "command_rate_rms": math.sqrt(sum(rate_sq) / len(rate_sq)) if rate_sq else None,
        "joint_acceleration_rms_deg_s2": (
            math.sqrt(sum(accel_sq) / len(accel_sq)) if accel_sq else None),
        "command_high_frequency_share": (
            hf_power / total_power if resolvable and total_power > _EPS else None),
        "effort_rms_clamp_ratio_max": max(clamp_ratios) if clamp_ratios else None,
        "effort_clamp_share_max": max(clamp_shares) if clamp_shares else None,
        "effort_rms_rated_ratio_max": max(rated_ratios) if rated_ratios else None,
        "cost_of_transport": cost,
        "drives": {"stride_hz": stride_hz, "high_frequency_hz": cutoff,
                   "mean_power_nmm_s": mean_power,
                   "travel_mm": None if travel is None else travel[0],
                   "channels": rows},
    }

# -- against a gait reference (ADR-705) ---------------------------------------

def _reference_angle(angles: Sequence[Sequence[float]], column: int, phase: float) -> float:
    """A clip column at ``phase`` of its stride, linear between samples, wrapping."""

    n = len(angles)
    x = (phase % 1.0) * n
    k = int(math.floor(x)) % n
    w = x - math.floor(x)
    return (1.0 - w) * float(angles[k][column]) + w * float(angles[(k + 1) % n][column])


def reference_metrics(feet: Mapping[str, Mapping[str, Any]], reference: Mapping[str, Any], *,
                      drives: Mapping[str, Any] | None = None,
                      settle_s: float = SETTLE_S) -> dict[str, Any]:
    """How the gait compares with a task's gait reference, stride by stride.

    ``feet`` is :func:`gait_metrics`' per-foot detail, keyed by the names the
    reference's ``legs`` give as ``foot_body``; ``reference`` is the task's
    ``cadex-gait-clip-v1`` clip (ADR-702, ADR-703). Nothing here needs a gait
    clock in the task: **the anchor foot's touch-downs are the clock.** Each
    settled pair of the left hind's landings is one measured stride, and a
    moment inside it is at phase ``(t - landing) / stride`` past the
    reference's own left-hind touch-down. So a policy that strides slower or
    longer than its reference is still compared pose for pose through its
    stride, and its timing is a separate number:

    * ``stride_frequency_ratio``: the median measured stride's frequency over
      the reference's;
    * ``footfall_phase_error_max``: per foot, the median over strides of how
      far, in cycles, its landing fell from where the reference's phase
      offsets put it, counted in whole frames of the landings' grid
      (ADR-719). A foot that did not land exactly once within half a
      stride of that moment missed the stride, and the miss is
      :data:`FOOTFALL_MISSED`. The worst foot is the metric;
    * ``duty_factor_error_max``: the worst foot's settled duty factor less
      the reference's, in absolute value;
    * ``reference_joint_rms_deg``: the RMS over every settled frame inside a
      measured stride, and every angular drive whose joint the clip poses, of
      the joint's angle less the clip's at that phase. ``None`` without the
      drives' record (a trace from before ADR-694).
    * ``command_rate_reference_ratio`` and
      ``joint_acceleration_reference_ratio`` (ADR-708): the rollout's settled
      command-rate and joint-acceleration RMS over the clip's own
      (:func:`reference_smoothness`), both over the angular drives the clip
      poses. 1.0 is as smooth as the motion asked for; a raw RMS grows with
      stride and speed, a ratio does not. ``None`` without the drives' record.

    Every metric is ``None`` when fewer than two anchor landings fall after
    the settle (no stride was measured), or when a foot the reference names
    is not among ``feet`` (``detail["missing_feet"]``).
    """

    parameters = reference["parameters"]
    offsets = {str(k): float(v) for k, v in parameters["phase_offsets"].items()}
    duty = float(parameters["duty_factor"])
    names = {label: str(leg["foot_body"]) for label, leg in reference["legs"].items()}
    missing = sorted(name for name in names.values() if name not in feet)
    if missing:
        return {"footfall_phase_error_max": None, "duty_factor_error_max": None,
                "stride_frequency_ratio": None, "reference_joint_rms_deg": None,
                "command_rate_reference_ratio": None,
                "joint_acceleration_reference_ratio": None,
                "reference": {"gait": reference.get("gait"), "missing_feet": missing}}
    anchor_label = REFERENCE_ANCHOR if REFERENCE_ANCHOR in names else BIPED_REFERENCE_ANCHOR
    anchor = [t for t in feet[names[anchor_label]]["touchdowns_s"] if t >= settle_s - _EPS]
    strides = [(a, b - a) for a, b in zip(anchor, anchor[1:]) if b - a > _EPS]
    detail: dict[str, Any] = {
        "gait": reference.get("gait"), "anchor": names[anchor_label],
        "strides": len(strides),
        "reference_stride_hz": float(parameters["stride_frequency_hz"]),
        "stride_hz": None, "feet": {}, "joints": [],
    }
    empty = {"footfall_phase_error_max": None, "duty_factor_error_max": None,
             "stride_frequency_ratio": None, "reference_joint_rms_deg": None,
             "command_rate_reference_ratio": None, "joint_acceleration_reference_ratio": None,
             "reference": detail}
    if not strides:
        return empty
    period = float(statistics.median(length for _, length in strides))
    detail["stride_hz"] = 1.0 / period

    # ADR-719: landings lie on the frame grid, so timing is counted in whole
    # frames and only the division by the stride's frames is inexact; a
    # 2-frame offset in a 20-frame stride reads 0.1, not 0.1 + 3e-17.
    frame_s = float(feet[names[anchor_label]]["frame_s"])

    def on_grid(moment: float) -> int:
        return round(moment / frame_s)

    grid = [(on_grid(start), on_grid(start + length) - on_grid(start)) for start, length in strides]
    phase_errors, duty_errors = [], []
    for label, name in names.items():
        expected = (offsets[label] - offsets[anchor_label]) % 1.0
        landings = [on_grid(t) for t in feet[name]["touchdowns_s"]]
        errors = []
        for start, length in grid:
            due = expected * length  # frames after the anchor's landing
            near = [t - start for t in landings if abs(t - start - due) < 0.5 * length]
            errors.append(abs(near[0] - due) / length if len(near) == 1 else FOOTFALL_MISSED)
        error = float(statistics.median(errors))
        measured_duty = feet[name].get("duty_factor")
        duty_error = None if measured_duty is None else abs(float(measured_duty) - duty)
        phase_errors.append(error)
        duty_errors.append(duty_error)
        detail["feet"][label] = {
            "foot": name, "expected_phase": expected, "phase_error": error,
            "missed_strides": sum(1 for e in errors if e >= FOOTFALL_MISSED),
            "duty_factor": measured_duty, "reference_duty_factor": duty,
            "duty_factor_error": duty_error,
        }

    joint_rms = None
    if drives is not None:
        columns = {str(name): i for i, name in enumerate(reference["joints"])}
        angles = reference["joint_angles_rad"]
        start_phase = offsets[anchor_label]
        pooled: list[float] = []
        for c, channel in enumerate(drives["channels"]):
            column = columns.get(str(channel.get("joint", "")))
            if column is None or str(channel.get("motion_type")) != "angular":
                continue
            errors = []
            for moment, row in zip(drives["time"], drives["positions"]):
                stride = next(((a, n) for a, n in strides if a <= moment < a + n), None)
                if stride is None or row is None:
                    continue
                phase = start_phase + (moment - stride[0]) / stride[1]
                errors.append(float(row[c]) - math.degrees(_reference_angle(angles, column, phase)))
            if errors:
                pooled.extend(errors)
                detail["joints"].append({"joint": str(channel["joint"]), "rms_deg": _rms(errors)})
        joint_rms = _rms(pooled)
        # ADR-708: smooth as the reference it tracks, on the same drives.
        ratios = _reference_smoothness_ratios(
            drive_metrics(drives, settle_s=settle_s)["drives"]["channels"],
            reference_smoothness(reference, drives["channels"]))
        detail["smoothness"] = ratios.pop("smoothness")
    else:
        ratios = {"command_rate_reference_ratio": None,
                  "joint_acceleration_reference_ratio": None}

    return {
        "footfall_phase_error_max": max(phase_errors),
        "duty_factor_error_max": (None if any(e is None for e in duty_errors)
                                  else max(duty_errors)),
        "stride_frequency_ratio": detail["stride_hz"] / detail["reference_stride_hz"],
        "reference_joint_rms_deg": joint_rms,
        **ratios,
        "reference": detail,
    }


def reference_smoothness(reference: Mapping[str, Any],
                         channels: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """How smooth the reference clip itself is, on the drives it poses (ADR-708).

    The clip's own command rate and joint acceleration, read the way
    :func:`drive_metrics` reads a rollout's, over every angular drive in
    ``channels`` (a trace's ``actuator_channels``, or a bundle's ``actions``)
    whose joint the clip poses: the joint angle as the command a drive that
    followed the clip exactly would be given, each in its channel's range
    widths, differenced over the clip's own sample interval and wrapped,
    because the clip is periodic. A raw RMS grows with stride and speed, so
    this is the yardstick a policy's smoothness is held against at the
    clip's speed, not a number to bound on its own.

    ``drives`` keeps each channel's index in ``channels`` and its two RMS
    figures, so a rollout can be compared on exactly the same drives.
    ``None`` figures when the clip poses no angular drive.
    """

    columns = {str(name): i for i, name in enumerate(reference["joints"])}
    angles = reference["joint_angles_rad"]
    n = len(angles)
    parameters = reference["parameters"]
    period = parameters.get("period_s") or 1.0 / float(parameters["stride_frequency_hz"])
    dt = float(reference.get("sample_dt_s") or float(period) / max(n, 1))
    rows: list[dict[str, Any]] = []
    rate_sq: list[float] = []
    accel_sq: list[float] = []
    for c, channel in enumerate(channels):
        column = columns.get(str(channel.get("joint", "")))
        if column is None or str(channel.get("motion_type")) != "angular" or n < 2:
            continue
        width = float(channel["high"]) - float(channel["low"])
        width = width if width > _EPS else 1.0
        q = [math.degrees(float(row[column])) for row in angles]
        rates = [(q[(k + 1) % n] - q[k]) / dt / width for k in range(n)]
        accels = [(q[(k + 1) % n] - 2.0 * q[k] + q[k - 1]) / (dt * dt) for k in range(n)]
        rate_sq.extend(r * r for r in rates)
        accel_sq.extend(a * a for a in accels)
        rows.append({"index": c, "joint": str(channel["joint"]),
                     "command_rate_rms": _rms(rates), "joint_acceleration_rms": _rms(accels)})
    return {
        "command_rate_rms": math.sqrt(sum(rate_sq) / len(rate_sq)) if rate_sq else None,
        "joint_acceleration_rms_deg_s2": (
            math.sqrt(sum(accel_sq) / len(accel_sq)) if accel_sq else None),
        # The clip's own unit; this module converts none (ADR-704).
        "speed_m_s": (None if parameters.get("speed_m_s") is None
                      else float(parameters["speed_m_s"])),
        "sample_dt_s": dt,
        "drives": rows,
    }


def _reference_smoothness_ratios(rows: Sequence[Mapping[str, Any]],
                                 clip: Mapping[str, Any]) -> dict[str, Any]:
    """A rollout's smoothness over its clip's, on the drives the clip poses.

    ``rows`` are :func:`drive_metrics`' per-channel rows. Every channel has
    the same number of settled samples, so the pooled RMS over a subset is
    the root mean square of its channels' own RMS figures.
    """

    def pooled(values: list[float | None]) -> float | None:
        if not values or any(v is None for v in values):
            return None
        return math.sqrt(sum(float(v) ** 2 for v in values) / len(values))

    picked = [rows[row["index"]] for row in clip["drives"]]
    rate = pooled([row["command_rate_rms"] for row in picked])
    accel = pooled([row["joint_acceleration_rms"] for row in picked])
    clip_rate, clip_accel = clip["command_rate_rms"], clip["joint_acceleration_rms_deg_s2"]
    return {
        "command_rate_reference_ratio": (
            rate / clip_rate if rate is not None and clip_rate and clip_rate > _EPS else None),
        "joint_acceleration_reference_ratio": (
            accel / clip_accel if accel is not None and clip_accel and clip_accel > _EPS
            else None),
        "smoothness": {**clip, "rollout_command_rate_rms": rate,
                       "rollout_joint_acceleration_rms_deg_s2": accel},
    }


def terrain_metrics(samples, rig: Mapping[str, Any], *,
                    terrain: Mapping[str, Any] | None = None,
                    ground: Any = None) -> dict[str, Any]:
    """Falls, and the steps and slopes a base crossed (ADR-718).

    ``ground(x_mm, y_mm)`` is the height of the ground the episode stood on
    (the engine's reading of the course; ``None`` is the plane at z = 0) and
    ``terrain`` that course's descriptor, whose ``features`` are counted.

    * ``falls``: 1.0 when, at any frame, the base tilted
      :data:`FALL_TILT_DEG` or more or its centre of mass came down to
      :data:`FALL_HEIGHT_SHARE` of its first frame's height above the ground
      under it; else 0.0. Measured from poses, so it holds whatever the
      task terminates on.
    * ``steps_crossed`` and ``slopes_crossed``: the course's steps (at
      ``x_mm``) and slopes (by ``to_x_mm``, their far end) that lie ahead of
      the centre of mass's first plan x and at or behind its last: crossed,
      and stayed across. Courses run along +x (ADR-714).
    * ``largest_step_crossed_mm`` and ``steepest_slope_crossed_deg``: the
      largest magnitude among them, up or down; 0.0 when none was crossed.
    * ``platforms_crossed`` and ``highest_platform_crossed_mm`` (ADR-749):
      the platforms whose footprint the centre of mass was over at some
      frame and whose far end (along +x) it ended beyond: up, across and
      down. Bumps and rock patches are not counted.

    Without ``terrain`` only ``falls`` is read.
    """

    reference = matrix(rig["reference_xyzw"])
    local = rig["base_com_local_mm"]
    level = (lambda x, y: 0.0) if ground is None else ground
    points, lowest_share, steepest_tilt = [], None, 0.0
    first = None
    for _, placements in samples:
        rotation, origin = _pose(placements, rig["base"])
        point = _add(_apply(rotation, local), origin)
        points.append(point)
        height = point[2] - float(level(point[0], point[1]))
        if first is None:
            first = height
        if first > _EPS:
            share = height / first
            lowest_share = share if lowest_share is None else min(lowest_share, share)
        steepest_tilt = max(steepest_tilt, tilt_degrees(rotation, reference))
    fell = steepest_tilt >= FALL_TILT_DEG or (
        lowest_share is not None and lowest_share <= FALL_HEIGHT_SHARE)
    read: dict[str, Any] = {"falls": 1.0 if fell else 0.0}
    detail: dict[str, Any] = {"max_tilt_deg": steepest_tilt,
                              "lowest_height_share": lowest_share}
    if terrain is not None and points:
        x_start, x_end = points[0][0], points[-1][0]
        crossed, platforms = [], []
        for feature in terrain.get("features") or ():
            if feature["kind"] == "platform":
                half_x, half_y = feature["length_mm"] / 2.0, feature["width_mm"] / 2.0
                far = float(feature["x_mm"]) + half_x
                over = any(abs(p[0] - feature["x_mm"]) <= half_x
                           and abs(p[1] - feature["y_mm"]) <= half_y for p in points)
                if over and x_end > far:
                    platforms.append(dict(feature))
                continue
            if feature["kind"] not in ("step", "slope"):
                continue
            edge = float(feature["x_mm"] if feature["kind"] == "step" else feature["to_x_mm"])
            if x_start < edge <= x_end:
                crossed.append(dict(feature))
        steps = [abs(float(f["height_mm"])) for f in crossed if f["kind"] == "step"]
        slopes = [abs(float(f["grade_deg"])) for f in crossed if f["kind"] == "slope"]
        read.update({
            "steps_crossed": float(len(steps)),
            "slopes_crossed": float(len(slopes)),
            "largest_step_crossed_mm": max(steps, default=0.0),
            "steepest_slope_crossed_deg": max(slopes, default=0.0),
            "platforms_crossed": float(len(platforms)),
            "highest_platform_crossed_mm": max(
                (float(f["height_mm"]) for f in platforms), default=0.0),
        })
        detail.update(crossed=crossed + platforms, course=terrain.get("course"),
                      features=sum(1 for f in terrain.get("features") or ()
                                   if f["kind"] in ("step", "slope", "platform")))
    read["terrain"] = detail
    return read


def episode_metrics(episode: Mapping[str, Any]) -> dict[str, Any]:
    """How the episode ended. ``completed`` is 1.0 only for a run to the horizon."""

    ended = bool(episode.get("truncated")) and not episode.get("termination")
    return {"completed": 1.0 if ended else 0.0, "duration_s": episode.get("duration_s"),
            "termination": str(episode.get("termination") or "")}


def measure(samples, episode: Mapping[str, Any], rig: Mapping[str, Any], *,
            shoves=(), command_mm_s: float | None = None,
            segments: Sequence[Mapping[str, Any]] = (),
            drives: Mapping[str, Any] | None = None,
            reference: Mapping[str, Any] | None = None,
            terrain: Mapping[str, Any] | None = None,
            ground: Any = None,
            commands: Mapping[str, Sequence[float]] | None = None,
            waypoints: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """Every behaviour metric one rollout can be read for, as one flat table.

    Which families are read is decided by what the rig and the episode
    carry, never by what the behaviour is called: a floating base is read
    for posture, named feet for gait, a tip with targets for reach, and a
    shove for the recovery from it, a body with a centre for its motion
    about it. ``metrics`` holds the names in
    :data:`METRICS` and nothing else, so it is exactly what a predicate may
    bound; a family that was not read is absent from it, and :func:`check`
    fails a predicate on an absent metric. ``detail`` keeps what a report
    shows beside the table: each foot's own figures, each shove's recovery,
    each target's row.

    ``shoves`` is ``[(onset_s, duration_s)]``, ``command_mm_s`` the forward
    speed the episode asked for and ``segments`` the targets it held -- what
    the episode applied, handed in by whoever ran it. ``drives`` is the
    trace's :func:`drive_series`; a trace that records none is not read for
    the drive family. Its stride frequency is the median foot's settled step
    rate, and its travel the base's net plan distance after the settle.
    ``reference`` is the task's gait reference clip; with feet it is read
    for the reference family (ADR-705). A floating base is read for the
    terrain family (ADR-718): ``ground`` is the height of the ground it
    stood on and ``terrain`` the course, as :func:`terrain_metrics` takes.
    ``commands`` is the speed and yaw rate in force at each sample, as
    :func:`tracking_metrics` takes; with a floating base it is read for the
    tracking family (ADR-721). A rig with an ``appendage`` on a floating
    base is read for the appendage family (ADR-722), against the yaw-rate
    command when ``commands`` carries one. ``waypoints`` are the ground
    points the episode sent the base to, as :func:`waypoint_metrics` takes;
    with a floating base they are read for the waypoint family (ADR-751).
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
        read.update(terrain_metrics(samples, rig, terrain=terrain, ground=ground))
        if commands:
            read.update(tracking_metrics(samples, rig, commands))
        if waypoints:
            read.update(waypoint_metrics(samples, rig, waypoints))
        if rig.get("appendage"):
            read.update(appendage_metrics(
                samples, rig, ground=ground,
                yaw_rates=(commands or {}).get("yaw_rate")))
    if rig.get("tip") is not None and segments:
        read.update(reach_metrics(samples, rig, segments))
    if rig.get("body") is not None:
        read.update(motion_metrics(samples, rig, completed=bool(read["completed"])))
    if drives is not None:
        travel = None
        if rig.get("base") is not None:
            base = base_series(samples, rig)
            late = [i for i, moment in enumerate(base["time"]) if moment >= SETTLE_S - _EPS]
            if len(late) > 1:
                a, b = base["point"][late[0]], base["point"][late[-1]]
                travel = (math.hypot(b[0] - a[0], b[1] - a[1]),
                          base["time"][late[-1]] - base["time"][late[0]])
        rates = [foot.get("step_rate_hz") for foot in (read.get("feet") or {}).values()]
        stride = (float(statistics.median(rates))
                  if rates and all(r is not None for r in rates) else None)
        read.update(drive_metrics(drives, weight_n=rig.get("weight_n"), travel=travel,
                                  stride_hz=stride))
    if reference is not None and read.get("feet"):
        read.update(reference_metrics(read["feet"], reference, drives=drives))
    for key in ("recovery_s", "feet", "segments", "travel_mm", "motion", "drives", "reference",
                "terrain", "tracking", "appendage", "waypoints"):
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
