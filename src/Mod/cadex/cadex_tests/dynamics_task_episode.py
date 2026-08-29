# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""One task bundle, one episode, and a MuJoCo that never heard of Cadex.

**This file is M6's exit criterion, and it is also the environment.** M7
becomes dispatch rather than debugging because this already exists: a
process that reads a bundle off disk, loads the model beside it, resets to
the solved keyframe, acts, observes, accumulates reward and terminates --
using nothing but ``mujoco`` and the standard library.

The sibling of :mod:`dynamics_mjcf_digest`, and it keeps that file's
discipline. It imports **only** ``json``, ``math``, ``ast``, ``random``,
``hashlib``, ``pathlib``, ``sys`` and ``mujoco``, and it reports whether
``CadexDynamics`` was importable at all, so a test can assert the negative
rather than trust the invocation: run under ``python -P`` with a scrubbed
``PYTHONPATH`` this is ``false``, and if it ever comes back ``true`` the
subprocess was not stock and the result proves nothing.

Floats are serialised with ``repr``, which round-trips exactly in Python 3,
so a difference against the engine's own episode is a *number* difference
and never a formatting one.

What the comparison against ``CadexDynamics.evaluate_episode`` proves, and
what it does not:

* It **does** prove the task spec is complete and unambiguous. Both sides
  read the same JSON and the same XML, and neither can consult anything
  else, so agreement means every number a trainer needs is in the files.
* It does **not** re-prove M5's physics. The engine evaluates its episode on
  the *reloaded exported bytes* too, so the model is not a variable in this
  comparison -- which is exactly what makes the comparison about the task.

The evaluator below is deliberately a second implementation rather than a
shared one. That is the point: two evaluators is where a whitelist drifts,
so the bundle ships its ``functions`` array and a test asserts this file's
globals equal it.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path
import random
import sys
from typing import Any, Sequence

#: Everything a reward or termination expression may call. Built here from
#: scratch rather than imported, and checked against the bundle's own
#: ``functions`` array before anything is evaluated -- so a task written
#: against an engine that knows a function this runner does not is a loud
#: refusal instead of a NameError halfway through an episode.
GLOBALS: dict[str, Any] = {
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


def function_names() -> list[str]:
    """The sorted callables this runner offers an expression."""

    return sorted(
        name
        for name, value in GLOBALS.items()
        if callable(value) and not name.startswith("__")
    )


def compile_expression(formula: str, names: Sequence[str]) -> Any:
    """One expression, checked against the channels and the whitelist."""

    allowed = set(names) | {
        name for name in GLOBALS if not name.startswith("__")
    }
    tree = ast.parse(str(formula), mode="eval")
    unknown = sorted(
        {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name) and node.id not in allowed
        }
    )
    if unknown:
        raise SystemExit(
            f"expression {formula!r} names {unknown}, which this bundle does "
            "not declare"
        )
    return compile(tree, filename="<reward>", mode="eval")


def channels(task: dict) -> list[str]:
    return [
        str(channel)
        for record in task["observations"]
        for channel in record["channels"]
    ]


def observation_values(task: dict, sensordata: Any) -> dict[str, float]:
    """Raw ``sensordata`` as the named, scaled channels of the task.

    The whole of the engine's units boundary, on this side, as one multiply.
    ``adr`` and ``dim`` say which slice, ``scale`` says what to multiply by,
    ``channels`` say what to call the results -- and every one of those three
    is in the file. Nothing here knows what a degree is.
    """

    values: dict[str, float] = {}
    for record in task["observations"]:
        adr = int(record["adr"])
        dim = int(record["dim"])
        scale = float(record["scale"])
        for offset, channel in enumerate(record["channels"][:dim]):
            values[str(channel)] = float(sensordata[adr + offset]) * scale
    return values


def draw_variation(task: dict, rng: Any) -> dict[str, list]:
    """The bundle's ``variation_algorithm``, reproduced from its own text.

    A second implementation of the per-episode draw, written here for the
    reason every other second implementation in this file is written: the
    bundle states an algorithm, and a stated algorithm nobody reproduces is
    a comment. Number for number against ``CadexDynamics`` from one seed, or
    the bundle does not say enough for a trainer to run the task.

    Note what is *not* branched on: three draws per disturbance whether or
    not it is sustained, eight per reset variation whatever its ranges --
    including the two the linear velocity takes from a bundle that declares
    none. A stream whose position depends on a branch is a stream two
    implementations get wrong differently.
    """

    variations = []
    for entry in task.get("reset_variation") or []:
        tilt = rng.uniform(float(entry["tilt_low_rad"]), float(entry["tilt_high_rad"]))
        azimuth = rng.uniform(0.0, 2.0 * math.pi)
        height = rng.uniform(float(entry["height_low_m"]),
                             float(entry["height_high_m"]))
        angular = [
            rng.uniform(float(entry["angular_velocity_low_rad_s"]),
                        float(entry["angular_velocity_high_rad_s"]))
            for _ in range(3)
        ]
        speed = rng.uniform(float(entry.get("linear_velocity_low_m_s") or 0.0),
                            float(entry.get("linear_velocity_high_m_s") or 0.0))
        speed_azimuth = rng.uniform(0.0, 2.0 * math.pi)
        variations.append({"label": str(entry["label"]), "tilt_rad": tilt,
                           "azimuth_rad": azimuth, "height_m": height,
                           "angular_velocity_rad_s": angular,
                           "linear_speed_m_s": speed,
                           "linear_azimuth_rad": speed_azimuth,
                           # World frame -- the other half of the same six
                           # numbers, which MuJoCo keeps in the body's.
                           "linear_velocity_m_s": [
                               speed * math.cos(speed_azimuth),
                               speed * math.sin(speed_azimuth),
                               0.0]})
    pushes = []
    for entry in task.get("disturbance") or []:
        magnitude = rng.uniform(float(entry["newtons_low"]),
                                float(entry["newtons_high"]))
        drawn = rng.uniform(0.0, 2.0 * math.pi)
        # Folded into the declared arc, which takes no draw of its own. The
        # full circle is the identity, exactly, so a task with no arc gets
        # the numbers it always did.
        arc_low = float(entry.get("azimuth_low_rad") or 0.0)
        arc_high = float(entry.get("azimuth_high_rad", 2.0 * math.pi))
        # The ratio first: `drawn * span / (2*pi)` rounds twice and lands an
        # ulp away from what the same seed used to produce.
        azimuth = arc_low + drawn * ((arc_high - arc_low) / (2.0 * math.pi))
        start = rng.uniform(float(entry["at_low_s"]), float(entry["at_high_s"]))
        if str(entry["direction"]) == "vertical":
            sign = 1.0 if azimuth < math.pi else -1.0
            force = [0.0, 0.0, magnitude * sign]
        else:
            force = [magnitude * math.cos(azimuth), magnitude * math.sin(azimuth),
                     0.0]
        pushes.append({"label": str(entry["label"]), "newtons": magnitude,
                       "azimuth_rad": azimuth, "start_s": start,
                       "force_n": force})
    return {"reset_variation": variations, "disturbance": pushes}


def write_variation(data: Any, entry: dict, draw: dict) -> None:
    """One drawn reset variation, into ``qpos`` and ``qvel``.

    The tilt quaternion is left-multiplied onto the base's own, which is a
    world-frame rotation about the base's frame origin because the position
    is untouched -- so the whole mechanism swings rigidly and every joint
    angle stays exactly where the solve left it. The Hamilton product is
    written out because MuJoCo's helper is not available to all three
    evaluators, and the horizontal tilt axis makes its z term zero.
    """

    address = int(entry["qpos_adr"])
    half = 0.5 * float(draw["tilt_rad"])
    sine = math.sin(half)
    tw = math.cos(half)
    tx = sine * math.cos(float(draw["azimuth_rad"]))
    ty = sine * math.sin(float(draw["azimuth_rad"]))
    qw = float(data.qpos[address + 3])
    qx = float(data.qpos[address + 4])
    qy = float(data.qpos[address + 5])
    qz = float(data.qpos[address + 6])
    data.qpos[address + 3] = tw * qw - tx * qx - ty * qy
    data.qpos[address + 4] = tw * qx + tx * qw - ty * qz
    data.qpos[address + 5] = tw * qy + tx * qz + ty * qw
    data.qpos[address + 6] = tw * qz - tx * qy + ty * qx
    data.qpos[address + 2] = float(data.qpos[address + 2]) + float(draw["height_m"])
    velocity = int(entry["qvel_adr"])
    linear = draw.get("linear_velocity_m_s") or (0.0, 0.0, 0.0)
    for axis in range(3):
        # Linear first, then angular: world frame and body frame, side by
        # side in one array, which is MuJoCo's asymmetry.
        data.qvel[velocity + axis] = float(linear[axis])
        data.qvel[velocity + 3 + axis] = float(draw["angular_velocity_rad_s"][axis])


def push(data: Any, task: dict, variation: dict, time_s: float) -> None:
    """This control step's applied forces, from zero, at the centre of mass."""

    entries = task.get("disturbance") or []
    if not entries:
        return
    data.xfrc_applied[:] = 0.0
    for entry, draw in zip(entries, variation["disturbance"]):
        if not bool(entry["sustained"]):
            start = float(draw["start_s"])
            if not start <= time_s < start + float(entry["duration_s"]):
                continue
        body = int(entry["body_id"])
        for axis in range(3):
            data.xfrc_applied[body, axis] += float(draw["force_n"][axis])


def run_episode(bundle_path: str, seed: int | None = None) -> dict[str, Any]:
    """One episode of one bundle, in an interpreter that has no Cadex."""

    import mujoco

    try:
        import CadexDynamics  # noqa: F401
    except Exception:
        cadex_importable = False
    else:
        cadex_importable = True

    path = Path(bundle_path).resolve()
    task = json.loads(path.read_text(encoding="utf-8"))
    if str(task.get("schema")) != "cadex-training-task-v1":
        raise SystemExit(f"unknown task schema {task.get('schema')!r}")

    # The model is referenced by a path relative to the *project root*, and
    # the bundle itself lives at ``outputs/<name>-task.json`` under that
    # root -- so the root is two levels up. The flat fallback is for a
    # bundle sitting beside its model with no outputs directory, which is
    # what a hand-assembled fixture looks like.
    reference = task["model"]
    relative = Path(str(reference["path"]))
    model_path = path.parent.parent / relative
    if not model_path.exists():
        model_path = path.parent / relative.name
    if not model_path.exists():
        raise SystemExit(
            f"the model {reference['path']!r} this bundle references is not "
            f"beside it: looked in {path.parent.parent} and {path.parent}"
        )
    xml = model_path.read_bytes()
    digest = hashlib.sha256(xml).hexdigest()
    if digest != str(reference["sha256"]):
        raise SystemExit(
            f"the model at {model_path} does not match the digest the bundle "
            f"recorded: {digest} vs {reference['sha256']}"
        )

    # The whitelist check, before an expression is compiled. Two evaluators
    # is where a function set drifts, and this is the seam it would drift at.
    if function_names() != [str(name) for name in task["functions"]]:
        raise SystemExit(
            "this runner's function whitelist differs from the bundle's: "
            f"{function_names()} vs {list(task['functions'])}"
        )

    names = channels(task)
    reward_terms = [
        (str(term["label"]), float(term["weight"]),
         compile_expression(str(term["expression"]), names))
        for term in task["reward"]
    ]
    termination_terms = [
        (str(rule["label"]), rule.get("above"), rule.get("below"),
         compile_expression(str(rule["expression"]), names))
        for rule in task["termination"]
    ]
    fallbacks = [
        compile_expression(str(action["fallback"]), ["time"])
        for action in task["actions"]
    ]

    model = mujoco.MjModel.from_xml_string(xml.decode("utf-8"))
    data = mujoco.MjData(model)

    drawn: list[dict[str, Any]] = []
    variation: dict[str, list] = {"reset_variation": [], "disturbance": []}
    if seed is not None:
        # The stated algorithm, reproduced: random.Random(seed) drawing
        # uniform(low, high) in bundle order. "Whatever the RNG did" is not
        # reproducible across two implementations; this is. The per-episode
        # draws continue the same stream, which is why they are not a second
        # Random(seed) -- that would hand them the numbers the randomisation
        # already used.
        rng = random.Random(int(seed))
        for entry in task.get("randomisation") or []:
            factor = rng.uniform(float(entry["low"]), float(entry["high"]))
            for field in entry["fields"]:
                getattr(model, str(field["field"])).flat[int(field["index"])] *= factor
            drawn.append({"label": str(entry["label"]), "factor": repr(factor)})
        if drawn:
            mujoco.mj_setConst(model, data)
        variation = draw_variation(task, rng)

    episode = task["episode"]
    key = mujoco.mj_name2id(
        model, mujoco.mjtObj.mjOBJ_KEY, str(episode["reset_keyframe"])
    )
    if key < 0:
        raise SystemExit(
            f"the model carries no {episode['reset_keyframe']!r} keyframe"
        )
    mujoco.mj_resetDataKeyframe(model, data, key)
    mujoco.mj_forward(model, data)
    if variation["reset_variation"]:
        for entry, draw in zip(task["reset_variation"], variation["reset_variation"]):
            write_variation(data, entry, draw)
        mujoco.mj_forward(model, data)

    per_action = int(episode["solver_steps_per_action"])
    interval = float(episode["control_interval_s"])
    steps: list[dict[str, Any]] = []
    total = 0.0
    terminated_step: int | None = None
    termination_label = ""
    for step in range(int(episode["max_steps"])):
        time_s = step * interval
        push(data, task, variation, time_s)
        applied: list[float] = []
        for action, code in zip(task["actions"], fallbacks):
            value = float(eval(code, GLOBALS, {"time": time_s}))
            clamped = min(max(value, float(action["low"])), float(action["high"]))
            applied.append(clamped)
            data.ctrl[int(action["index"])] = clamped * float(action["scale"])
        for _ in range(per_action):
            mujoco.mj_step(model, data)

        landed = observation_values(task, data.sensordata)
        reward = 0.0
        contributions = []
        for label, weight, code in reward_terms:
            raw = float(eval(code, GLOBALS, dict(landed)))
            contributions.append({"label": label, "value": repr(raw),
                                  "weighted": repr(weight * raw)})
            reward += weight * raw
        total += reward
        reason = ""
        for label, above, below, code in termination_terms:
            value = float(eval(code, GLOBALS, dict(landed)))
            if (above is not None and value > float(above)) or (
                below is not None and value < float(below)
            ):
                reason = label
                break
        steps.append(
            {
                "step": step,
                "action": [repr(value) for value in applied],
                "observation": {
                    name: repr(value) for name, value in landed.items()
                },
                "reward": repr(reward),
                "reward_terms": contributions,
                "terminated": bool(reason),
                "termination": reason,
            }
        )
        if reason:
            terminated_step = step
            termination_label = reason
            break

    return {
        "cadex_importable": cadex_importable,
        "mujoco_version": str(getattr(mujoco, "__version__", "unknown")),
        "model_sha256": digest,
        "model_path": str(model_path),
        "functions": function_names(),
        "label": str(task.get("label") or ""),
        "steps": steps,
        "step_count": len(steps),
        "total_reward": repr(total),
        "terminated_step": terminated_step,
        "termination": termination_label,
        "truncated": terminated_step is None,
        "randomisation": drawn,
        # `repr` for the same reason every other float here is: a difference
        # against the engine's own draw has to be a number difference and
        # never a formatting one.
        "reset_variation": [
            {
                "label": str(draw["label"]),
                "tilt_rad": repr(draw["tilt_rad"]),
                "azimuth_rad": repr(draw["azimuth_rad"]),
                "height_m": repr(draw["height_m"]),
                "angular_velocity_rad_s": [
                    repr(value) for value in draw["angular_velocity_rad_s"]
                ],
            }
            for draw in variation["reset_variation"]
        ],
        "disturbance": [
            {
                "label": str(draw["label"]),
                "newtons": repr(draw["newtons"]),
                "azimuth_rad": repr(draw["azimuth_rad"]),
                "start_s": repr(draw["start_s"]),
                "force_n": [repr(value) for value in draw["force_n"]],
            }
            for draw in variation["disturbance"]
        ],
        "seed": None if seed is None else int(seed),
    }


def main(argv: Sequence[str]) -> int:
    if len(argv) < 2:
        print(
            "usage: dynamics_task_episode.py <task.json> [seed]",
            file=sys.stderr,
        )
        return 2
    seed = int(argv[2]) if len(argv) > 2 and argv[2] != "-" else None
    print(json.dumps(run_episode(argv[1], seed), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
