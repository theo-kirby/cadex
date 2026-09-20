# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The smoke rollout's child: stock MuJoCo over an exported model (ADR-352).

Run **by path** under the engine's own interpreter, the way ``cadex train``
runs the trainer: it imports nothing from ``cadex_cli`` and nothing from the
engine. What it reads is the MJCF the accepted revision exported and, when
there is one, the task bundle beside it; ``mujoco`` is the module the
engine's own rollouts use (ADR-076), so a model that plays here plays there.

Four checks, each a fixture's known answer (``cli/tests/test_smoke.py``):

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
  ``training/cadex_train.py`` evaluates it.

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


def _channels(task: dict[str, Any]) -> list[tuple[str, int, float]]:
    """``(channel, sensordata address, scale)`` per observation channel."""

    found: list[tuple[str, int, float]] = []
    for record in task.get("observations") or []:
        adr = int(record["adr"])
        scale = float(record.get("scale", 1.0))
        for offset, channel in enumerate(record["channels"]):
            found.append((str(channel), adr + offset, scale))
    return found


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
    channels = _channels(task) if task else []
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

    def observe_contacts(time_s: float) -> bool:
        touching_floor = False
        for index in range(int(data.ncon)):
            contact = data.contact[index]
            g1, g2 = int(contact.geom1), int(contact.geom2)
            if floor in (g1, g2) and float(contact.dist) <= 0.0:
                touching_floor = True
            if floor not in (g1, g2):
                continue  # Component fit comes from exact BREP, not collision proxies.
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
        values = {name: float(data.sensordata[adr]) * scale for name, adr, scale in channels}
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
        elapsed = (step + 1) * timestep
        if elapsed + 1e-9 >= next_sample or step == total_steps - 1:
            mujoco.mj_forward(model, data)
            touching_floor = observe_contacts(elapsed)
            observe_termination(elapsed)
            snapshot()
            sampled += 1
            next_sample = (math.floor(elapsed * fps + 1e-9) + 1) / fps
    Path(args.out).with_name("smoke-trace.json").write_text(json.dumps(trace, allow_nan=False))

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

    if free_joints:
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

    checks = {
        "finite": finite,
        "penetration": penetration,
        "support": support,
        "termination": termination,
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
