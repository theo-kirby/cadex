# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The smoke rollout's child: stock MuJoCo over an exported model (ADR-352).

Run **by path** under the engine's own interpreter, the way ``cadex train``
runs the trainer: it imports nothing from ``cadex_cli`` and nothing from the
engine. What it reads is the MJCF the accepted revision exported and, when
there is one, the task bundle beside it; ``mujoco`` is the module the
engine's own rollouts use (ADR-076), so a model that plays here plays there.

Five checks, each a fixture's known answer (``cli/tests/test_smoke.py``):

* **finite** -- every solver-step state is finite and MuJoCo raised no warning
  (a bad ``qacc`` resets the state to zero, so the counters are the only
  honest witness of a blow-up);
* **penetration** -- no floor collision proxy penetrates the environment
  deeper than the tolerance at any sample. Exact component-pair geometry
  is checked separately by smoke_geometry.py, including excluded contacts.
  MuJoCo's soft contact lets a resting part sink about 0.1--0.2 mm at the
  default ``solref``, which is why the default tolerance is above that;
* **support** -- something of a free base's design (ADR-335) is touching the
  environment floor at the end, the base's linear speed is under the rest
  threshold, and the base still holds the attitude its accepted keyframe gave
  it, within ``--max-tilt-degrees`` (ADR-377: a design that toppled and
  settled satisfies the first two and is not standing); a grounded design
  holds its grounded bodies by construction, and says which;
* **termination** -- when a task was exported, none of its own declared
  termination rules fires over the trace. This is the design's own
  statement of what "holding its pose" means, evaluated exactly the way
  ``training/cadex_train.py`` evaluates it;
* **closure** -- every loop closure the export wrote as an ``equality``
  between two sites (ADR-593) stays shut: the gap between its two sites, at
  every solver step, within the MJCF's pose contract (ADR-584). A closure
  is soft with a two-step time constant, so how far it opens goes as the
  step squared; a failure names the step that would hold it (ADR-594).

Two modes. ``hold`` gives every position actuator its joint's keyframe value
as the command, so servos hold the solved pose; every other actuator gets
zero. ``zero`` gives every actuator zero. The receipt is one JSON object,
written to ``--out`` and printed on the last stdout line.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

SCHEMA = "cadex-smoke-dynamics-v1"
ENVIRONMENT_FLOOR_GEOM = "environment/floor"
DEFAULT_KEYFRAME = "solved"
#: How many penetrating pairs the receipt lists, worst first.
MAXIMUM_REPORTED_PAIRS = 32
#: ``CadexDynamics.MJCF_POSE_TOLERANCE_MM``, restated: this child imports
#: nothing from the engine. A loop open by more than this has a pose the
#: export's own contract would not accept (ADR-584).
CLOSURE_TOLERANCE_MM = 1.0e-2
#: The driven loop probe (ADR-599): one sweep of this period, and the
#: amplitude for an actuator with no command range.
DRIVE_PERIOD_S = 2.0
DRIVE_UNLIMITED_RAD = 0.3


def closure_step_s(step_s: float, worst_mm: float, tolerance_mm: float = CLOSURE_TOLERANCE_MM) -> float:
    """The largest 1-2-5 step under which a loop open ``worst_mm`` at
    ``step_s`` would hold ``tolerance_mm``.

    The closure's time constant is two steps, so its stiffness goes as one
    over the step squared and so does how far a given load holds it open:
    measured on driven four-bars: the headless fixture opened 0.045,
    0.0062 and 0.0012 mm at 2, 1 and 0.5 ms (ADR-593), the live one 0.70,
    0.0061 and 0.0013 mm at 2, 0.5 and 0.25 ms -- steeper than step
    squared, so the step this names is conservative (ADR-594,
    docs/MUJOCO.md). Rounded *down* to 1, 2 or 5 of a decade, so the step
    named is one a person would write and is not borderline.
    """

    exact = step_s * math.sqrt(tolerance_mm / worst_mm)
    decade = 10.0 ** math.floor(math.log10(exact))
    for mantissa in (5.0, 2.0, 1.0):
        if mantissa * decade <= exact * (1.0 + 1e-9):
            return mantissa * decade
    return decade


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _table() -> dict[str, Any]:
    """What a termination expression may call -- the trainer's whitelist,
    in the standard library (``globals_for`` in ``training/cadex_train.py``)."""

    return {
        "__builtins__": {},
        "pi": math.pi,
        "abs": abs,
        "sin": math.sin,
        "cos": math.cos,
        "asin": math.asin,
        "arcsin": math.asin,
        "arctan": math.atan,
        "exp": math.exp,
        "sqrt": math.sqrt,
        "tanh": math.tanh,
    }


def _observe(task: dict[str, Any], sensordata: Any) -> dict[str, float]:
    """Every observation channel by name, as ``CadexDynamics.observation_values``.

    A tracked position (ADR-588) reads as its tracker reports it: rounded to
    the resolution, and zeros with ``_in_range`` 0 when the body is outside
    the declared range; a load (ADR-591) as its load sensor reports it. No
    noise -- this is a check, not a training draw.
    """

    values: dict[str, float] = {}
    for record in task.get("observations") or []:
        adr = int(record["adr"])
        dim = int(record.get("dim", len(record["channels"])))
        scale = float(record.get("scale", 1.0))
        read = [float(sensordata[adr + offset]) * scale for offset in range(dim)]
        tracker = record.get("tracker")
        if tracker and record.get("in_range_of"):
            # ADR-590: a differenced velocity, zeros while its position is lost.
            step = float(tracker["resolution_mm"]) * float(tracker["rate_hz"])
            seen = values.get(f"{record['in_range_of']}_in_range") == 1.0
            read = [round(value / step) * step if seen else 0.0 for value in read]
        elif tracker:
            inside = all(float(low) <= value <= float(high)
                         for value, (low, high) in zip(read, tracker["range_mm"]))
            step = float(tracker["resolution_mm"])
            read = ([round(value / step) * step for value in read] + [1.0]
                    if inside else [0.0, 0.0, 0.0, 0.0])
        elif record.get("load"):
            # ADR-591: held within the stall line, rounded to the resolution.
            load = record["load"]
            full = float(load["full_scale"])
            step = float(load["resolution"])
            read = [round(min(max(read[0], -full), full) / step) * step]
        for channel, value in zip(record["channels"], read):
            values[str(channel)] = value
    return values


def _up_vector(quat_wxyz: Any) -> tuple[float, float, float]:
    """A body's local +Z in world coordinates: its rotation matrix's third column."""

    w, x, y, z = (float(v) for v in quat_wxyz)
    return (2.0 * (x * z + w * y), 2.0 * (y * z - w * x), 1.0 - 2.0 * (x * x + y * y))


def _angle_between_degrees(first: Any, second: Any) -> float:
    """The angle between two unit vectors, in degrees."""

    dot = sum(float(a) * float(b) for a, b in zip(first, second))
    return math.degrees(math.acos(max(-1.0, min(1.0, dot))))


def _quat_tilt_degrees(quat_wxyz: Any) -> float:
    """The angle between a body's local +Z and the world's +Z."""

    return _angle_between_degrees(_up_vector(quat_wxyz), (0.0, 0.0, 1.0))


def run(args: argparse.Namespace) -> dict[str, Any]:
    import mujoco
    import numpy as np

    started = time.monotonic()
    model_path = Path(args.model)
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)

    task: dict[str, Any] | None = None
    task_block: dict[str, Any] | None = None
    keyframe_name = DEFAULT_KEYFRAME
    if args.task:
        task_path = Path(args.task)
        task = json.loads(task_path.read_text(encoding="utf-8"))
        if task.get("model", {}).get("sha256") and task["model"]["sha256"] != _sha256(model_path):
            raise SystemExit("the task does not belong to the selected model")
        keyframe_name = str((task.get("episode") or {}).get("reset_keyframe") or DEFAULT_KEYFRAME)
        task_block = {
            "path": task_path.name,
            "sha256": _sha256(task_path),
            "label": task.get("label"),
        }

    key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, keyframe_name)
    if key < 0:
        raise SystemExit(
            f"the model carries no {keyframe_name!r} keyframe; a smoke rollout "
            "starts from the solved pose and nothing else."
        )
    mujoco.mj_resetDataKeyframe(model, data, key)

    def body_name(index: int) -> str:
        return str(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, int(index)) or "")

    def geom_name(index: int) -> str:
        return str(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, int(index)) or "")

    floor = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, ENVIRONMENT_FLOOR_GEOM)

    def geom_label(index: int) -> str:
        # The floor belongs to the world body; name it as the floor rather
        # than as "world" so a receipt reads the way the manifest does.
        return ENVIRONMENT_FLOOR_GEOM if index == floor else body_name(model.geom_bodyid[index])

    # -- the loops -------------------------------------------------------
    # What the export writes for a loop closure: a connect or a weld between
    # two sites. A gear or belt is an equality too, but between joints, and
    # it has no gap to measure.
    closures: list[dict[str, Any]] = []
    for eq in range(int(model.neq)):
        if int(model.eq_objtype[eq]) != int(mujoco.mjtObj.mjOBJ_SITE):
            continue
        if int(model.eq_type[eq]) not in (int(mujoco.mjtEq.mjEQ_CONNECT), int(mujoco.mjtEq.mjEQ_WELD)):
            continue
        closures.append({
            "closure": str(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_EQUALITY, eq) or ""),
            "kind": "connect" if int(model.eq_type[eq]) == int(mujoco.mjtEq.mjEQ_CONNECT) else "weld",
            "sites": (int(model.eq_obj1id[eq]), int(model.eq_obj2id[eq])),
            "worst_mm": 0.0,
            "time_s": 0.0,
        })

    def observe_closures(time_s: float) -> None:
        for closure in closures:
            first, second = closure["sites"]
            gap_mm = float(np.linalg.norm(data.site_xpos[first] - data.site_xpos[second])) * 1000.0
            if gap_mm > closure["worst_mm"]:
                closure["worst_mm"] = gap_mm
                closure["time_s"] = time_s

    # -- the command -----------------------------------------------------
    held: list[dict[str, Any]] = []
    for act in range(model.nu):
        target = 0.0
        is_position = (
            model.actuator_biastype[act] == mujoco.mjtBias.mjBIAS_AFFINE
            and model.actuator_trntype[act] == mujoco.mjtTrn.mjTRN_JOINT
            and abs(float(model.actuator_gainprm[act, 0]) + float(model.actuator_biasprm[act, 1])) < 1e-9
        )
        if args.mode == "hold" and is_position:
            joint = int(model.actuator_trnid[act, 0])
            target = float(data.qpos[model.jnt_qposadr[joint]])
        data.ctrl[act] = target
        held.append({
            "actuator": str(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, act) or ""),
            "kind": "position" if is_position else "other",
            "ctrl": target,
        })

    # -- the base ----------------------------------------------------------
    free_joints = [j for j in range(model.njnt) if model.jnt_type[j] == mujoco.mjtJoint.mjJNT_FREE]
    grounded = [
        body_name(b) for b in range(1, model.nbody)
        if int(model.body_parentid[b]) == 0 and int(model.body_jntnum[b]) == 0
    ]

    # -- the schedule ------------------------------------------------------
    timestep = float(model.opt.timestep)
    fps = int(args.fps)
    steps_per_sample = max(1, int(round((1.0 / fps) / timestep)))
    samples = int(math.floor(float(args.seconds) * fps + 1e-9))

    trace = []

    # -- the trace ---------------------------------------------------------
    worst: dict[tuple[str, str], dict[str, Any]] = {}
    nonfinite_at: float | None = None
    termination_rules: list[dict[str, Any]] = []
    table = _table()
    if task:
        for rule in task.get("termination") or []:
            termination_rules.append({
                "label": str(rule.get("label") or ""),
                "expression": str(rule.get("expression") or ""),
                "above": rule.get("above"),
                "below": rule.get("below"),
                "code": compile(str(rule.get("expression") or "0"), "<termination>", "eval"),
                "fired_at_s": None,
                "value": None,
                "error": None,
            })

    touches: dict[tuple[str, str], float] = {}

    def observe_contacts(time_s: float) -> bool:
        touching_floor = False
        for index in range(int(data.ncon)):
            contact = data.contact[index]
            g1, g2 = int(contact.geom1), int(contact.geom2)
            if floor in (g1, g2) and float(contact.dist) <= 0.0:
                touching_floor = True
            if floor not in (g1, g2):
                # Component fit comes from exact BREP, not collision proxies;
                # the contact's depth only bounds what the exact check allows
                # a pair the simulator holds in contact (ADR-599).
                depth_mm = -float(contact.dist) * 1000.0
                bodies = tuple(sorted((body_name(model.geom_bodyid[g1]), body_name(model.geom_bodyid[g2]))))
                if depth_mm > 0.0 and bodies[0] != bodies[1]:
                    touches[bodies] = max(depth_mm, touches.get(bodies, 0.0))
                continue
            depth_mm = -float(contact.dist) * 1000.0
            if depth_mm <= 0.0:
                continue
            pair = tuple(sorted((geom_label(g1), geom_label(g2))))
            if pair not in worst or depth_mm > worst[pair]["depth_mm"]:
                worst[pair] = {
                    "first": pair[0], "second": pair[1],
                    "depth_mm": depth_mm, "time_s": time_s,
                    "geoms": [geom_name(g1), geom_name(g2)],
                }
        return touching_floor

    def observe_termination(time_s: float) -> None:
        if not termination_rules:
            return
        values = _observe(task, data.sensordata)
        for rule in termination_rules:
            if rule["fired_at_s"] is not None or rule["error"] is not None:
                continue
            try:
                value = float(eval(rule["code"], table, dict(values)))
            except Exception as exc:  # a rule that cannot be read is not a pass
                rule["error"] = f"{type(exc).__name__}: {exc}"
                continue
            fired = (rule["above"] is not None and value > float(rule["above"])) or (
                rule["below"] is not None and value < float(rule["below"]))
            if fired:
                rule["fired_at_s"] = time_s
                rule["value"] = value

    def state_is_finite() -> bool:
        return bool(np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()
                    and np.isfinite(data.qacc).all() and np.isfinite(data.act).all()
                    and np.isfinite(data.ctrl).all() and math.isfinite(float(data.time)))

    def snapshot():
        trace.append({"time_s": float(data.time), "placements": {
            body_name(b): {"position_mm": [float(v) * 1000 for v in data.xpos[b]],
                           "rotation_xyzw": [float(v) for v in data.xquat[b][[1, 2, 3, 0]]]}
            for b in range(1, model.nbody)}})

    mujoco.mj_forward(model, data)
    observe_closures(0.0)
    touching_floor = observe_contacts(0.0)
    observe_termination(0.0)
    nonfinite_at = None if state_is_finite() else 0.0
    if nonfinite_at is None:
        snapshot()
    sampled = 1
    next_sample = 1.0 / fps
    total_steps = int(math.ceil(float(args.seconds) / timestep - 1e-9))
    warning_counts = [0] * int(mujoco.mjtWarning.mjNWARNING)
    for step in range(total_steps):
        if nonfinite_at is not None:
            break
        mujoco.mj_step(model, data)
        for i in range(len(warning_counts)):
            warning_counts[i] = max(warning_counts[i], int(data.warning[i].number))
        if not state_is_finite():
            nonfinite_at = float(data.time)
            break
        # mj_step leaves the sites where the step began: every state the
        # rollout passed through is measured, not only the sampled ones.
        observe_closures(step * timestep)
        elapsed = (step + 1) * timestep
        if elapsed + 1e-9 >= next_sample or step == total_steps - 1:
            mujoco.mj_forward(model, data)
            touching_floor = observe_contacts(elapsed)
            observe_termination(elapsed)
            observe_closures(elapsed)
            snapshot()
            sampled += 1
            next_sample = (math.floor(elapsed * fps + 1e-9) + 1) / fps
    # -- the loops, driven ----------------------------------------------
    # Held still, a driven loop never opens, so a step too coarse for its
    # motion would pass (ADR-599). On a fresh state from the same keyframe,
    # each position actuator sweeps sinusoidally about what it holds --
    # 40 % of its command range's half-span, one 2 s period -- and every
    # closure's gap is measured through that motion.
    swept = [(i, row["ctrl"]) for i, row in enumerate(held) if row["kind"] == "position"]
    if closures and swept and nonfinite_at is None:
        probe = mujoco.MjData(model)
        mujoco.mj_resetDataKeyframe(model, probe, key)
        mujoco.mj_forward(model, probe)
        period = DRIVE_PERIOD_S
        for step in range(int(math.ceil(period / timestep - 1e-9))):
            phase = math.sin(2.0 * math.pi * step * timestep / period)
            for act, centre in swept:
                if model.actuator_ctrllimited[act]:
                    low, high = (float(v) for v in model.actuator_ctrlrange[act])
                    reach = 0.4 * (high - low) / 2.0
                    probe.ctrl[act] = min(high, max(low, centre + reach * phase))
                else:
                    probe.ctrl[act] = centre + DRIVE_UNLIMITED_RAD * phase
            mujoco.mj_step(model, probe)
            if not (np.isfinite(probe.qpos).all() and np.isfinite(probe.qvel).all()):
                break
            for closure in closures:
                first, second = closure["sites"]
                gap_mm = float(np.linalg.norm(probe.site_xpos[first] - probe.site_xpos[second])) * 1000.0
                if gap_mm > closure.get("driven_mm", 0.0):
                    closure["driven_mm"] = gap_mm
                    closure["driven_time_s"] = step * timestep
        for closure in closures:
            if closure.get("driven_mm", 0.0) > closure["worst_mm"]:
                closure["worst_mm"], closure["time_s"] = closure["driven_mm"], closure["driven_time_s"]
                closure["while_driven"] = True

    Path(args.out).with_name("smoke-trace.json").write_text(json.dumps(trace, allow_nan=False))
    Path(args.out).with_name("smoke-contacts.json").write_text(json.dumps(
        [{"first": a, "second": b, "depth_mm": d} for (a, b), d in sorted(touches.items())],
        allow_nan=False))

    warnings = [
        {"warning": mujoco.mjtWarning(i).name, "count": warning_counts[i]}
        for i in range(int(mujoco.mjtWarning.mjNWARNING))
        if warning_counts[i] > 0
    ]

    # -- the four checks ---------------------------------------------------
    failing: list[str] = []

    finite = {
        "pass": nonfinite_at is None and not warnings,
        "nonfinite_at_s": nonfinite_at,
        "warnings": warnings,
    }
    if nonfinite_at is not None:
        failing.append(f"finite: the state is not finite at {nonfinite_at:.3f} s")
    for item in warnings:
        failing.append(f"finite: MuJoCo warned {item['warning']} x{item['count']}")

    tolerance = float(args.penetration_mm)
    ranked = sorted(worst.values(), key=lambda row: -row["depth_mm"])
    breaches = [row for row in ranked if row["depth_mm"] > tolerance]
    penetration = {
        "pass": not breaches,
        "tolerance_mm": tolerance,
        "pairs_touching": len(ranked),
        "breaches": len(breaches),
        "worst": ranked[:MAXIMUM_REPORTED_PAIRS],
        "omitted": max(0, len(ranked) - MAXIMUM_REPORTED_PAIRS),
    }
    for row in breaches:
        failing.append(
            f"penetration: {row['first']} ∩ {row['second']} {row['depth_mm']:.3f} mm "
            f"at {row['time_s']:.3f} s (tolerance {tolerance:g} mm)"
        )

    # A free body in a rig with grounded bodies is a payload -- a ball on a
    # plate -- not a base that must stand on the floor (ADR-599).
    payloads = [body_name(model.jnt_bodyid[j]) for j in free_joints] if grounded else []
    if free_joints and not grounded:
        joint = free_joints[0]
        qadr, dofadr = int(model.jnt_qposadr[joint]), int(model.jnt_dofadr[joint])
        base = body_name(model.jnt_bodyid[joint])
        speed_mm_s = float(np.linalg.norm(data.qvel[dofadr:dofadr + 3])) * 1000.0
        z_start = float(model.key_qpos[key][qadr + 2]) * 1000.0
        z_end = float(data.qpos[qadr + 2]) * 1000.0
        rest_speed = float(args.rest_speed_mm_s)
        at_rest = speed_mm_s <= rest_speed
        # How far the base turned away from the attitude its accepted
        # keyframe gave it (ADR-377). Measured against the keyframe rather
        # than the world, so a design whose base is modelled lying down and
        # holds that pose reads zero, and one that toppled reads its topple.
        tilt_from_start = _angle_between_degrees(
            _up_vector(model.key_qpos[key][qadr + 3:qadr + 7]),
            _up_vector(data.qpos[qadr + 3:qadr + 7]))
        maximum_tilt = float(args.max_tilt_degrees)
        held_attitude = tilt_from_start <= maximum_tilt
        support = {
            "kind": "free",
            "pass": (floor >= 0 and touching_floor and at_rest and held_attitude
                     and nonfinite_at is None),
            "base": base,
            "floor": ENVIRONMENT_FLOOR_GEOM if floor >= 0 else None,
            "touching_floor_at_end": bool(touching_floor),
            "speed_mm_s": speed_mm_s,
            "rest_speed_mm_s": rest_speed,
            "z_start_mm": z_start,
            "z_end_mm": z_end,
            "drop_mm": z_start - z_end,
            "tilt_degrees": _quat_tilt_degrees(data.qpos[qadr + 3:qadr + 7]),
            "tilt_from_start_degrees": tilt_from_start,
            "max_tilt_degrees": maximum_tilt,
        }
        if floor < 0:
            failing.append("support: the free base has no environment floor to rest on")
        elif not touching_floor:
            failing.append(f"support: {base} is not touching {ENVIRONMENT_FLOOR_GEOM} at the end")
        if not at_rest:
            failing.append(
                f"support: {base} is still moving at {speed_mm_s:.1f} mm/s "
                f"(rest is {rest_speed:g} mm/s)"
            )
        if not held_attitude:
            failing.append(
                f"support: {base} has turned {tilt_from_start:.1f}° away from its "
                f"accepted pose (limit {maximum_tilt:g}°)"
            )
    else:
        support = {
            "kind": "grounded",
            "pass": bool(grounded),
            "grounded": grounded,
            "note": "grounded bodies are static in the model; they hold by construction",
            "payloads": payloads,
        }

    if not free_joints and not grounded:
        failing.append("support: no free base or grounded body")

    fired = [r for r in termination_rules if r["fired_at_s"] is not None]
    broken = [r for r in termination_rules if r["error"] is not None]
    termination = {
        "pass": not fired and not broken,
        "rules": len(termination_rules),
        "fired": [
            {"label": r["label"], "expression": r["expression"], "at_s": r["fired_at_s"],
             "value": r["value"], "above": r["above"], "below": r["below"]}
            for r in fired
        ],
        "errors": [{"label": r["label"], "error": r["error"]} for r in broken],
        "note": None if task else "no task exported; nothing declared",
    }
    for r in fired:
        failing.append(
            f"termination: {r['label'] or r['expression']} fired at {r['fired_at_s']:.3f} s "
            f"(value {r['value']:.6g})"
        )
    for r in broken:
        failing.append(f"termination: {r['label'] or r['expression']} could not be read ({r['error']})")

    open_loops = [c for c in closures if c["worst_mm"] > CLOSURE_TOLERANCE_MM]
    worst_loop = max(closures, key=lambda c: c["worst_mm"], default=None)
    closure = {
        "pass": not open_loops,
        "tolerance_mm": CLOSURE_TOLERANCE_MM,
        "closures": [
            {"closure": c["closure"], "kind": c["kind"], "worst_mm": c["worst_mm"], "time_s": c["time_s"],
             "while_driven": bool(c.get("while_driven"))}
            for c in sorted(closures, key=lambda c: -c["worst_mm"])
        ],
        "worst_mm": worst_loop["worst_mm"] if worst_loop else None,
        "solver_step_s": timestep,
        "suggested_step_s": (
            closure_step_s(timestep, worst_loop["worst_mm"]) if open_loops else None),
        "note": None if closures else "no loop closures in the model",
    }
    for c in open_loops:
        failing.append(
            f"closure: loop {c['closure']!r} opens {c['worst_mm']:.4g} mm at {c['time_s']:.3f} s "
            + ("of the driven sweep " if c.get("while_driven") else "") +
            f"(contract {CLOSURE_TOLERANCE_MM:g} mm at a {timestep * 1000.0:g} ms step); a closure "
            f"is soft and opens as the step squared: export with "
            f"solver_step_s={closure_step_s(timestep, c['worst_mm']):g} or finer"
        )

    checks = {
        "finite": finite,
        "penetration": penetration,
        "support": support,
        "termination": termination,
        "closure": closure,
    }
    return {
        "schema": SCHEMA,
        "verdict": "pass" if all(check["pass"] for check in checks.values()) else "fail",
        "mode": args.mode,
        "seconds": float(args.seconds),
        "simulated_seconds": total_steps * timestep,
        "frames_per_second": fps,
        "samples": sampled,
        "solver_step_s": timestep,
        "steps_per_sample": steps_per_sample,
        "keyframe": keyframe_name,
        "model": {"path": model_path.name, "sha256": _sha256(model_path)},
        "task": task_block,
        "actuators": held,
        "checks": checks,
        "failing": failing,
        "mujoco_version": str(mujoco.__version__),
        "wall_time_s": time.monotonic() - started,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", required=True)
    parser.add_argument("--task", default="")
    parser.add_argument("--out", required=True)
    parser.add_argument("--seconds", type=float, required=True)
    parser.add_argument("--mode", choices=("hold", "zero"), required=True)
    parser.add_argument("--penetration-mm", dest="penetration_mm", type=float, required=True)
    parser.add_argument("--rest-speed-mm-s", dest="rest_speed_mm_s", type=float, required=True)
    parser.add_argument("--max-tilt-degrees", dest="max_tilt_degrees", type=float, required=True)
    parser.add_argument("--fps", type=int, required=True)
    args = parser.parse_args(argv)
    receipt = run(args)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
