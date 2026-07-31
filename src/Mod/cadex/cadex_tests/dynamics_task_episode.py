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
    if seed is not None:
        # The stated algorithm, reproduced: random.Random(seed) drawing
        # uniform(low, high) in bundle order. "Whatever the RNG did" is not
        # reproducible across two implementations; this is.
        rng = random.Random(int(seed))
        for entry in task.get("randomisation") or []:
            factor = rng.uniform(float(entry["low"]), float(entry["high"]))
            for field in entry["fields"]:
                getattr(model, str(field["field"])).flat[int(field["index"])] *= factor
            drawn.append({"label": str(entry["label"]), "factor": repr(factor)})
        if drawn:
            mujoco.mj_setConst(model, data)

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

    per_action = int(episode["solver_steps_per_action"])
    interval = float(episode["control_interval_s"])
    steps: list[dict[str, Any]] = []
    total = 0.0
    terminated_step: int | None = None
    termination_label = ""
    for step in range(int(episode["max_steps"])):
        time_s = step * interval
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
