# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The checkpoint rollout's child: one checkpoint, one nominal episode (ADR-544).

Run **by path** under the engine's own interpreter, the way the evaluation's
child is, and for the same reason: the episode loop and the policy's forward
pass are engine code (``CadexDynamics.rollout_policy``), and a second copy
of either here would be a second reading of what a checkpoint does. It
imports nothing from ``cadex_cli``.

The one argument is a plan: the engine's module directory, the run's model
and task bundle, the checkpoint, the tag the trainer gave it with the
iteration and reward the trainer's progress recorded for it, and where to
write. The episode is the **nominal** one -- no seed, so no randomisation,
no reset variation and no shove -- which makes every checkpoint of a run the
same episode with a different policy in it. That is what makes a scrubber
across them a comparison and not a lottery.

It writes one ``cadex-assembly-simulation-trace-v1`` document, atomically,
or a failure record with the reason; never both, and never a partial trace.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Any

TRACE_SCHEMA = "cadex-assembly-simulation-trace-v1"
FAILURE_SCHEMA = "cadex-checkpoint-rollout-failure-v1"
#: The highest frame rate a checkpoint trace is sampled at. A rollout is a
#: view, and 25 frames a second of a 50 Hz policy is half the bytes of
#: every control step with nothing a person watching could miss.
MAXIMUM_FPS = 30


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def finite(value: Any) -> Any:
    """``value`` with every non-finite number as ``None``: not measured."""

    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: finite(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite(item) for item in value]
    return value


def frame_rate(control_hz: int) -> int:
    """The largest whole divisor of ``control_hz`` at or under the cap."""

    return max(rate for rate in range(1, min(control_hz, MAXIMUM_FPS) + 1)
               if control_hz % rate == 0)


def _write_atomically(path: Path, data: bytes) -> None:
    partial = path.with_name(path.name + ".partial")
    partial.write_bytes(data)
    os.replace(partial, path)


def roll_out(plan: dict[str, Any]) -> dict[str, Any]:
    sys.path.insert(0, str(plan["module_dir"]))
    import CadexDynamics  # noqa: PLC0415 - the plan says where the engine is

    model_bytes = Path(plan["model"]).read_bytes()
    task_bytes = Path(plan["task"]).read_bytes()
    policy_bytes = Path(plan["checkpoint"]).read_bytes()
    task = json.loads(task_bytes.decode("utf-8"))
    container = CadexDynamics.decode_policy(policy_bytes, context="the checkpoint")
    model = CadexDynamics.load_model(model_bytes)
    mujoco = CadexDynamics._mujoco_module()
    # Every named body is a component: the export names a body after the
    # component it carries, so these are the names the page draws by.
    names = [name for name in (
        mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, index)
        for index in range(1, int(model.nbody))) if name]
    control_hz = int(task["episode"]["control_hz"])
    rate = frame_rate(control_hz)
    started = time.monotonic()
    run = CadexDynamics.rollout_policy(
        model, task, container, components=names, frames_per_second=rate,
        seed=None, context=f"the {plan['tag']} checkpoint's rollout")
    episode = run["episode"]
    return finite({
        "schema": TRACE_SCHEMA,
        "simulation_output": "checkpoint",
        "component_outputs": names,
        "motion_outputs": [],
        "parameters": {
            "start_time_s": 0.0,
            "end_time_s": float(episode["episode_seconds"]),
            "time_step_s": float(run["frame_interval_s"]),
            "error_tolerance": float(run["solver_tolerance"]),
            "frames_per_second": rate,
        },
        "frames": run["frames"],
        "actuator_channels": list(run["actuator_channels"]),
        **({"goal_channels": list(run["goal_channels"])} if "goal_channels" in run else {}),
        "dynamics": {
            "solver": "mujoco",
            "solver_step_s": float(run["solver_step_s"]),
            "control_hz": control_hz,
            "frames_per_second": rate,
            "steps_per_frame": int(run["steps_per_frame"]),
            "component_outputs": names,
            "mujoco_version": str(task.get("mujoco_version") or ""),
        },
        "policy": {
            "policy_sha256": _sha256(policy_bytes),
            "task_sha256": _sha256(task_bytes),
            "model_sha256": _sha256(model_bytes),
            "seed": None,
            "label": str(episode["label"]),
            "total_reward": float(episode["total_reward"]),
            "step_count": int(episode["step_count"]),
            "termination": str(episode["termination"]),
            "truncated": bool(episode["truncated"]),
            "solver_warnings": list(episode["solver_warnings"]),
        },
        "checkpoint": {
            "file": Path(plan["checkpoint"]).name,
            "tag": str(plan["tag"]),
            "iteration": plan.get("iteration"),
            "reward_per_step": plan.get("reward_per_step"),
            "sha256": _sha256(policy_bytes),
            "rollout_wall_time_s": time.monotonic() - started,
        },
    })


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        sys.stderr.write("usage: checkpoint_runner.py PLAN.json\n")
        return 2
    plan = json.loads(Path(arguments[0]).read_text(encoding="utf-8"))
    try:
        document = roll_out(plan)
    except Exception as error:  # noqa: BLE001 - the reason goes to the parent
        failure = {"schema": FAILURE_SCHEMA, "checkpoint": Path(plan["checkpoint"]).name,
                   "tag": str(plan["tag"]), "iteration": plan.get("iteration"),
                   "reason": str(getattr(error, "reason", "") or error.__class__.__name__),
                   "error": str(error)}
        _write_atomically(Path(plan["failure"]), json.dumps(failure, indent=2).encode() + b"\n")
        return 1
    _write_atomically(Path(plan["trace"]), json.dumps(
        document, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        allow_nan=False).encode("utf-8"))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
