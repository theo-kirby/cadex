# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Did it walk with real steps? Did it balance in place? One trace, read
against the frozen ot11 contract.

The ot11 contract (``docs/probes/ot11/README.md``, ``contract.json``) states a
success spec for each behaviour as predicates on a rollout trace, none of
which reads the reward. This reads the walk and balance predicates from the
trace the engine exported and the model it ran, and changes nothing: no
rebuild, no rollout, no training. It exists so the known negatives could be
measured before anything was built; the product's own evaluation command is
P2's.

What the ot10 gait check could not see is what this reads. A foot's height is
the lowest point of its collision geoms above the floor, so stance is a fact
about geometry and not a lift line on a part's centre; a *step* is an airborne
run that lasts and lands somewhere else, so chatter is not counted; and slip is
the travel of the material point that was on the floor, so a round foot that
rolls through its stance is not charged for it.

    pixi run python docs/probes/ot11/runner/measure.py walk \\
        --model model-model.xml --foot c_foot_fl --foot c_foot_fr ... \\
        --command-mm-s 80 [--off-contract] TRACE.json [TRACE.json ...]
    pixi run python docs/probes/ot11/runner/measure.py balance \\
        --model robin_model-model.xml [--off-contract] TRACE.json [...]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

SCHEMA = "ot11-measure-v1"
CONTRACT = Path(__file__).resolve().parents[1] / "contract.json"
STANCE_MM = 1.0
SPEED_WINDOW_S = 0.20
SWING_MIN_S = 0.10
STEP_ADVANCE_HIP_HEIGHTS = 0.15


def contract() -> dict[str, Any]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def predicate(behaviour: str, identifier: str) -> dict[str, Any]:
    rows = contract()["behaviours"][behaviour]["predicates"]
    return next(row for row in rows if row["id"] == identifier)


def digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# -- rotations (trace quaternions are [x, y, z, w]) -------------------------

def matrix(quat_xyzw) -> np.ndarray:
    x, y, z, w = (float(v) for v in quat_xyzw)
    n = math.sqrt(x * x + y * y + z * z + w * w)
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def tilt_degrees(rotation: np.ndarray, reference: np.ndarray) -> float:
    dot = float(rotation[:, 2] @ reference[:, 2])
    return math.degrees(math.acos(max(-1.0, min(1.0, dot))))


def forward(rotation: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """World +X of the solved pose, carried with the base, flattened to plan."""

    axis = (rotation @ reference.T)[:, 0]
    plan = np.array([axis[0], axis[1]])
    return plan / np.linalg.norm(plan)


# -- the model's facts ------------------------------------------------------

def rig(model_path: Path, feet=(), keyframe: str = "solved") -> dict[str, Any]:
    """Everything the predicates need from the model, as plain numbers in mm."""

    import mujoco  # noqa: PLC0415 - deferred so the arithmetic tests need none

    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, keyframe)
    if key < 0:
        raise SystemExit(f"{model_path} carries no {keyframe!r} keyframe")
    mujoco.mj_resetDataKeyframe(model, data, key)
    mujoco.mj_forward(model, data)
    free = [j for j in range(model.njnt) if model.jnt_type[j] == mujoco.mjtJoint.mjJNT_FREE]
    if len(free) != 1:
        raise SystemExit(f"{model_path} has {len(free)} free joints; the spec reads exactly one base")
    base = int(model.jnt_bodyid[free[0]])
    planes = [g for g in range(model.ngeom) if model.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE]
    if len(planes) != 1:
        raise SystemExit(f"{model_path} has {len(planes)} floor planes; the spec reads exactly one")
    floor = float(data.geom_xpos[planes[0]][2]) * 1000.0
    w, x, y, z = (float(v) for v in data.xquat[base])
    kinds = {int(mujoco.mjtGeom.mjGEOM_SPHERE): "sphere", int(mujoco.mjtGeom.mjGEOM_CAPSULE): "capsule",
             int(mujoco.mjtGeom.mjGEOM_BOX): "box"}
    out_feet: dict[str, Any] = {}
    hips: list[float] = []
    for name in feet:
        body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
        if body < 0:
            raise SystemExit(f"{model_path} carries no body {name!r}")
        geoms = []
        for g in range(model.ngeom):
            if int(model.geom_bodyid[g]) != body or not (model.geom_contype[g] or model.geom_conaffinity[g]):
                continue
            kind = kinds.get(int(model.geom_type[g]))
            if kind is None:
                raise SystemExit(f"foot {name!r} has a collision geom that is not a sphere, capsule or box")
            gw, gx, gy, gz = (float(v) for v in model.geom_quat[g])
            geoms.append({"kind": kind, "size_mm": [float(v) * 1000.0 for v in model.geom_size[g]],
                          "pos_mm": [float(v) * 1000.0 for v in model.geom_pos[g]],
                          "quat_xyzw": [gx, gy, gz, gw]})
        if not geoms:
            raise SystemExit(f"foot {name!r} has no collision geom")
        out_feet[name] = geoms
        link = body
        while int(model.body_parentid[link]) != base:
            link = int(model.body_parentid[link])
            if link == 0:
                raise SystemExit(f"foot {name!r} does not hang from the base")
        joints = [j for j in range(model.njnt) if int(model.jnt_bodyid[j]) == link]
        if not joints:
            raise SystemExit(f"no joint between the base and foot {name!r}")
        hips.append(float(data.xanchor[joints[0]][2]) * 1000.0 - floor)
    mass = float(model.body_subtreemass[base])
    return {
        "base": str(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, base)),
        "reference_xyzw": [x, y, z, w],
        "base_com_local_mm": [float(v) * 1000.0 for v in model.body_ipos[base]],
        "floor_mm": floor,
        "mass_kg": mass,
        "weight_n": mass * 9.81,
        "com_height_mm": float(data.subtree_com[base][2]) * 1000.0 - floor,
        "hip_height_mm": (sum(hips) / len(hips)) if hips else None,
        "feet": out_feet,
    }


# -- traces -----------------------------------------------------------------

def load_trace(path: Path) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
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


def base_series(samples, the_rig) -> dict[str, np.ndarray]:
    """Time, base point (plan), tilt, heading and windowed speed per frame."""

    reference = matrix(the_rig["reference_xyzw"])
    local = np.array(the_rig["base_com_local_mm"])
    times, points, tilts, headings, forwards = [], [], [], [], []
    for time_s, placements in samples:
        pose = placements[the_rig["base"]]
        rotation = matrix(pose["rotation_xyzw"])
        times.append(time_s)
        points.append((rotation @ local + np.array(pose["position_mm"], dtype=float))[:2])
        tilts.append(tilt_degrees(rotation, reference))
        ahead = forward(rotation, reference)
        forwards.append(ahead)
        headings.append(math.degrees(math.atan2(ahead[1], ahead[0])))
    times, points = np.array(times), np.array(points)
    headings = np.degrees(np.unwrap(np.radians(headings)))
    headings = headings - headings[0]
    dt = float(np.median(np.diff(times)))
    lag = max(1, int(round(SPEED_WINDOW_S / dt)))
    velocity = np.full_like(points, np.nan)
    velocity[lag:] = (points[lag:] - points[:-lag]) / (lag * dt)
    return {"time": times, "point": points, "tilt": np.array(tilts), "heading": headings,
            "forward": np.array(forwards), "velocity": velocity, "dt": dt}


def _lowest(geom: dict[str, Any], rotation: np.ndarray, origin: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """One geom's centre and lowest point in the world, from its body's pose."""

    centre = rotation @ np.array(geom["pos_mm"]) + origin
    turn = rotation @ matrix(geom["quat_xyzw"])
    size = geom["size_mm"]
    down = np.array([0.0, 0.0, -1.0])
    if geom["kind"] == "sphere":
        return centre, centre + size[0] * down
    if geom["kind"] == "capsule":
        axis = turn[:, 2]
        end = centre - math.copysign(size[1], axis[2]) * axis
        return centre, end + size[0] * down
    corner = centre.copy()
    for i in range(3):
        corner -= math.copysign(size[i], turn[2, i]) * turn[:, i]
    return centre, corner


def foot_series(samples, geoms, floor_mm: float) -> dict[str, np.ndarray]:
    """Height, plan point and frame-to-frame contact-point travel of one foot."""

    def pose(placements, name):
        p = placements[name]
        return matrix(p["rotation_xyzw"]), np.array(p["position_mm"], dtype=float)

    raise_name = geoms["name"]
    heights, points, travel = [], [], []
    previous = None
    for _, placements in samples:
        rotation, origin = pose(placements, raise_name)
        lows = [_lowest(g, rotation, origin) for g in geoms["geoms"]]
        centre = lows[0][0]
        low = min((pair[1] for pair in lows), key=lambda point: point[2])
        heights.append(float(low[2]) - floor_mm)
        points.append(centre[:2])
        if previous is not None:
            # Where the material point that was lowest a frame ago is now.
            moved = rotation @ previous["local"] + origin
            travel.append(float(np.linalg.norm((moved - previous["low"])[:2])))
        previous = {"low": low, "local": rotation.T @ (low - origin)}
    return {"height": np.array(heights), "point": np.array(points), "contact_travel": np.array(travel)}


def gait(time, foot, hip_height_mm: float, settle_s: float) -> dict[str, Any]:
    """Steps, clearance, slip and duty factor of one foot."""

    height, point = foot["height"], foot["point"]
    dt = float(np.median(np.diff(time)))
    stance = height <= STANCE_MM
    segment = np.linalg.norm(np.diff(point, axis=0), axis=1)
    total = float(segment.sum())
    both = stance[:-1] & stance[1:]
    slip = float(foot["contact_travel"][both].sum())
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
            "peak_mm": float(height[start:end + 1].max()),
            "advance_mm": float(np.linalg.norm(point[end + 1] - point[start - 1])),
            "path_mm": float(segment[start - 1:end + 1].sum()),
        }
        swings.append(swing)
        if (swing["airborne_s"] >= SWING_MIN_S - 1e-9
                and swing["advance_mm"] >= STEP_ADVANCE_HIP_HEIGHTS * hip_height_mm):
            steps.append(swing)
    settled = time >= settle_s
    peaks = [s["peak_mm"] for s in steps]
    return {
        "swings": len(swings),
        "steps": len(steps),
        "path_mm": total,
        "step_share": (sum(s["path_mm"] for s in steps) / total) if total > 1e-9 else 0.0,
        "slip_mm": slip,
        "slip_share": (slip / total) if total > 1e-9 else 0.0,
        "median_step_clearance_mm": float(np.median(peaks)) if peaks else None,
        "median_step_clearance_hip_heights": (float(np.median(peaks)) / hip_height_mm) if peaks else None,
        "median_swing_peak_mm": float(np.median([s["peak_mm"] for s in swings])) if swings else None,
        "median_swing_airborne_s": float(np.median([s["airborne_s"] for s in swings])) if swings else None,
        "median_step_advance_mm": float(np.median([s["advance_mm"] for s in steps])) if steps else None,
        "peak_height_mm": float(height.max()),
        "duty_factor": float(stance[settled].mean()),
    }


def _row(behaviour: str, identifier: str, passed: bool | None, value: Any, why: str = "") -> dict[str, Any]:
    spec = predicate(behaviour, identifier)
    limit = {k: spec[k] for k in ("min", "max", "max_s", "rest") if k in spec}
    return {"id": identifier, "name": spec["name"], "pass": passed, "value": value, "limit": limit, "why": why}


def _completes(behaviour: str, identifier: str, episode, off_contract: bool) -> dict[str, Any]:
    wanted = contract()["behaviours"][behaviour]["episode_seconds"]
    ended = episode["truncated"] and not episode["termination"]
    value = {"duration_s": episode["duration_s"], "termination": episode["termination"],
             "truncated": episode["truncated"]}
    if not ended:
        return _row(behaviour, identifier, False, value, f"ended by {episode['termination'] or 'no truncation'}")
    if episode["duration_s"] != wanted:
        if off_contract:
            return _row(behaviour, identifier, None, value,
                        f"ran its own task's {episode['duration_s']} s horizon, not the contract's {wanted} s")
        return _row(behaviour, identifier, False, value, f"ran {episode['duration_s']} s, contract {wanted} s")
    return _row(behaviour, identifier, True, value)


def walk(samples, the_rig, command_mm_s: float, episode, *, off_contract: bool = False) -> dict[str, Any]:
    spec = contract()["behaviours"]["walk"]
    settle = float(spec["settle_s"])
    hip = float(the_rig["hip_height_mm"])
    base = base_series(samples, the_rig)
    settled = (base["time"] >= settle) & ~np.isnan(base["velocity"][:, 0])
    ahead = base["forward"]
    along = (base["velocity"] * ahead).sum(axis=1)
    across = base["velocity"][:, 1] * ahead[:, 0] - base["velocity"][:, 0] * ahead[:, 1]
    speed_ratio = float(along[settled].mean()) / command_mm_s
    lateral_ratio = abs(float(across[settled].mean())) / command_mm_s
    feet = {name: gait(base["time"], foot_series(samples, {"name": name, "geoms": geoms}, the_rig["floor_mm"]),
                       hip, settle)
            for name, geoms in the_rig["feet"].items()}
    counts = [f["steps"] for f in feet.values()]

    def per_foot(key):
        return {name: f[key] for name, f in feet.items()}

    def limits(identifier):
        return predicate("walk", identifier)

    max_tilt, max_heading = float(base["tilt"].max()), float(np.abs(base["heading"]).max())
    w5, w6, w7, w8 = limits("W5"), limits("W6"), limits("W7"), limits("W8")
    clear = per_foot("median_step_clearance_hip_heights")
    rows = [
        _completes("walk", "W1", episode, off_contract),
        _row("walk", "W2", max_tilt <= limits("W2")["max"], max_tilt),
        _row("walk", "W3", limits("W3")["min"] <= speed_ratio <= limits("W3")["max"], speed_ratio),
        _row("walk", "W4", lateral_ratio <= limits("W4")["max"][0] and max_heading <= limits("W4")["max"][1],
             {"lateral_ratio": lateral_ratio, "max_heading_deg": max_heading}),
        _row("walk", "W5", all(f["steps"] >= w5["min"][0] and f["step_share"] >= w5["min"][1] for f in feet.values()),
             {"steps": per_foot("steps"), "step_share": per_foot("step_share")}),
        _row("walk", "W6", all(v is not None and v >= w6["min"] for v in clear.values()), clear,
             "" if all(v is not None for v in clear.values()) else "a foot took no step, so it has no step clearance"),
        _row("walk", "W7", all(f["slip_share"] <= w7["max"] for f in feet.values()), per_foot("slip_share")),
        _row("walk", "W8", all(w8["min"] <= f["duty_factor"] <= w8["max"] for f in feet.values()),
             per_foot("duty_factor")),
        _row("walk", "W9", min(counts) > 0 and max(counts) / min(counts) <= limits("W9")["max"],
             (max(counts) / min(counts)) if min(counts) else None,
             "" if min(counts) else "a foot took no step"),
    ]
    travel = base["point"][-1] - base["point"][0]
    return {
        "predicates": rows,
        "metrics": {
            "command_mm_s": command_mm_s, "hip_height_mm": hip,
            "mean_forward_speed_mm_s": float(along[settled].mean()),
            "mean_lateral_speed_mm_s": float(across[settled].mean()),
            "travel_mm": [float(travel[0]), float(travel[1])],
            "max_tilt_deg": max_tilt, "max_heading_deg": max_heading,
            "step_min_advance_mm": STEP_ADVANCE_HIP_HEIGHTS * hip,
            "clearance_min_mm": w6["min"] * hip,
            "feet": feet,
        },
    }


def recovery(time, tilt, speed, shove_end_s: float, rest: dict[str, Any], com_height_mm: float) -> float | None:
    """Seconds from a shove's end to the first frame that starts a full rest."""

    quiet = (tilt <= rest["tilt_deg_max"]) & (np.nan_to_num(speed, nan=np.inf)
                                              <= rest["speed_com_heights_per_s_max"] * com_height_mm)
    dt = float(np.median(np.diff(time)))
    hold = int(round(rest["hold_s"] / dt))
    for i in np.flatnonzero(time >= shove_end_s - 1e-9):
        if i + hold >= len(time):
            return None
        if quiet[i:i + hold + 1].all():
            return float(time[i] - shove_end_s)
    return None


def balance(samples, the_rig, shoves, episode, *, off_contract: bool = False) -> dict[str, Any]:
    """``shoves`` is ``[(onset_s, duration_s)]``: what the episode applied."""

    base = base_series(samples, the_rig)
    com = float(the_rig["com_height_mm"])
    drift = np.linalg.norm(base["point"] - base["point"][0], axis=1)
    speed = np.linalg.norm(base["velocity"], axis=1)
    max_tilt, max_heading = float(base["tilt"].max()), float(np.abs(base["heading"]).max())
    max_drift = float(drift.max())
    b5 = predicate("balance", "B5")
    times = [recovery(base["time"], base["tilt"], speed, onset + duration, b5["rest"], com)
             for onset, duration in shoves]
    if shoves:
        recovered = _row("balance", "B5", all(t is not None and t <= b5["max_s"] for t in times), times)
    else:
        recovered = _row("balance", "B5", None, [], "the episode applied no shove")
    rows = [
        _completes("balance", "B1", episode, off_contract),
        _row("balance", "B2", max_tilt <= predicate("balance", "B2")["max"], max_tilt),
        _row("balance", "B3", max_drift / com <= predicate("balance", "B3")["max"], max_drift / com),
        _row("balance", "B4", max_heading <= predicate("balance", "B4")["max"], max_heading),
        recovered,
    ]
    return {
        "predicates": rows,
        "metrics": {
            "com_height_mm": com, "max_tilt_deg": max_tilt, "max_heading_deg": max_heading,
            "final_heading_deg": float(base["heading"][-1]),
            "max_drift_mm": max_drift, "final_drift_mm": float(drift[-1]),
            "drift_limit_mm": predicate("balance", "B3")["max"] * com,
            "mean_speed_mm_s": float(np.nanmean(speed)),
            "recovery_s": times,
        },
    }


def report(behaviour: str, trace_path: Path, model_path: Path, the_rig, *, off_contract: bool,
           command_mm_s: float | None = None, shoves=()) -> dict[str, Any]:
    """One trace's verdict: every predicate, the numbers behind it, and why."""

    trace = load_trace(trace_path)
    episode, digests = trace["episode"], trace["digests"]
    the_contract = contract()
    void: list[str] = []
    model_sha = digest(model_path)
    if digests["mjcf_sha256"] != model_sha:
        void.append(f"the trace ran model {digests['mjcf_sha256']}, not the model read ({model_sha})")
    if not digests["policy_sha256"]:
        void.append("no policy: only a policy rollout is evaluated")
    if episode["steps_per_frame"] != 1 or (episode["control_hz"] or 0) < the_contract["trace"]["min_frame_rate_hz"]:
        void.append("frames are not one per control step at 50 Hz or more")
    if not off_contract and episode["seed"] not in the_contract["evaluation_seeds"]:
        void.append(f"seed {episode['seed']} is not a contract seed")
    if behaviour == "walk":
        measured = walk(trace["samples"], the_rig, float(command_mm_s), episode, off_contract=off_contract)
    else:
        measured = balance(trace["samples"], the_rig, list(shoves), episode, off_contract=off_contract)
    rows = measured["predicates"]
    return {
        "schema": SCHEMA, "behaviour": behaviour, "trace": str(trace_path),
        "conditions": "off-contract: a trace that predates the contract, run under its own task's conditions"
                      if off_contract else "contract",
        "seed": episode["seed"], **digests, "void": void,
        **measured,
        "failing": [row["id"] for row in rows if row["pass"] is False],
        "not_measured": [row["id"] for row in rows if row["pass"] is None],
        "pass": not void and not off_contract and all(row["pass"] is True for row in rows),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("behaviour", choices=("walk", "balance"))
    parser.add_argument("traces", nargs="+", type=Path)
    parser.add_argument("--model", type=Path, required=True, help="the MJCF the traces ran")
    parser.add_argument("--foot", action="append", default=[], help="a foot body (walk); repeat per foot")
    parser.add_argument("--command-mm-s", type=float, help="the commanded forward speed (walk)")
    parser.add_argument("--shove", action="append", default=[], metavar="ONSET:DURATION",
                        help="a shove the episode applied, in seconds (balance); repeat per shove")
    parser.add_argument("--off-contract", action="store_true",
                        help="the trace predates the contract; report the predicates, never a pass")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if args.behaviour == "walk" and (not args.foot or args.command_mm_s is None):
        parser.error("walk needs --foot for every foot and --command-mm-s")
    the_rig = rig(args.model, args.foot)
    shoves = [tuple(float(v) for v in text.split(":")) for text in args.shove]
    reports = [report(args.behaviour, t, args.model, the_rig, off_contract=args.off_contract,
                      command_mm_s=args.command_mm_s, shoves=shoves) for t in args.traces]
    facts = {k: v for k, v in the_rig.items() if k != "feet"}
    result = {"schema": SCHEMA, "behaviour": args.behaviour, "rig": facts, "traces": reports,
              "pass": bool(reports) and all(r["pass"] for r in reports)}
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
