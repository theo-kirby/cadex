# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The evaluation's child: one policy on its task's frozen seeds (ADR-457).

Run **by path** under the engine's own interpreter, the way the smoke
rollout is: it imports nothing from ``cadex_cli``. Unlike the smoke child it
does import the engine -- ``CadexDynamics`` from the module directory the
plan names -- because the episode loop, the policy's forward pass and the
behaviour metrics are engine code (ADR-455), and a second copy of any of
them here would be a second reading of what a policy did.

The one argument is a plan: the engine's module directory, the three files
the accepted revision retained (model, task bundle, policy weights), the
component names a trace carries, and where to write. It writes one
``seed-<n>-trace.json`` per seed and the measured report, and prints one
line per seed on stderr.

A plan with ``shove`` set plays the **shove episode** a passed evaluation is
filmed taking (ADR-571) instead: the spec's first seed, under the spec's
conditions, with the shoves the task was trained against (:func:`shove_task`)
in place of the spec's own. It is the same engine call on a narrowed spec, so
the pushes, the recovery from each and how the episode ended are the engine's
own reading, and its one trace is the file the plan names.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

#: The per-seed trace's name. ``*-trace.json`` is what a project's own
#: repository ignores, so an evaluation's frames never enter it.
TRACE_NAME = "seed-{seed}-trace.json"
#: How many pushes each of the task's shoves becomes in the shove episode:
#: its start window cut into this many equal slices, one push drawn in each.
SHOVES_PER_ENTRY = 3


def shove_task(task: dict[str, Any], maximum: int) -> dict[str, Any]:
    """``task`` with its spec narrowed to the shove episode (ADR-571).

    The spec keeps its predicates, horizon, randomisation, reset variation,
    goals and sustained disturbances, and its first seed only. Its own
    shoves are replaced by the **task's**: each shove the policy was trained
    against, its start window cut into :data:`SHOVES_PER_ENTRY` equal slices
    no shorter than the push, one push drawn from the entry's own force,
    direction and duration in each, so the pushes land in order and never
    overlap. A window that runs past the spec's horizon is cut back to it.
    At most ``maximum`` disturbances in all, the engine's own cap. A task
    that trained against no shove has none to film: ``ValueError``.
    """

    spec = dict(task["success"])
    horizon = float(spec["episode"]["episode_seconds"])
    kept = [dict(entry) for entry in spec.get("disturbance") or () if entry.get("sustained")]
    pushes: list[dict[str, Any]] = []
    for entry in task.get("disturbance") or ():
        if entry.get("sustained"):
            continue
        duration = float(entry["duration_s"])
        low = float(entry["at_low_s"])
        high = min(float(entry["at_high_s"]), horizon - duration)
        if high < low:
            continue
        slices = max(1, min(SHOVES_PER_ENTRY, math.floor((high - low + duration) / duration + 1e-9)))
        span = (high - low + duration) / slices
        for at in range(slices):
            start = low + at * span
            pushes.append({**entry, "label": f"{entry['label']} {at + 1}",
                           "at_low_s": start, "at_high_s": max(start, start + span - duration)})
    if not pushes:
        raise ValueError("the task trained against no shove inside the evaluation's horizon, "
                         "so there is no shove to film")
    room = max(0, int(maximum) - len(kept))
    spec["disturbance"] = kept + pushes[:room]
    spec["seeds"] = [int(spec["seeds"][0])]
    return {**task, "success": spec}


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


def evaluate(plan: dict[str, Any]) -> dict[str, Any]:
    sys.path.insert(0, str(plan["module_dir"]))
    import CadexDynamics  # noqa: PLC0415 - the plan says where the engine is

    out = Path(plan["out"])
    model_bytes = Path(plan["model"]).read_bytes()
    task_bytes = Path(plan["task"]).read_bytes()
    policy_bytes = Path(plan["policy"]).read_bytes()
    task = json.loads(task_bytes.decode("utf-8"))
    semantic = CadexDynamics.task_semantic_digest(task)
    shove = bool(plan.get("shove"))
    if shove:
        try:
            task = shove_task(task, CadexDynamics.MAXIMUM_DISTURBANCES)
        except ValueError as exc:
            raise CadexDynamics.DynamicsError(str(exc), reason="no_shove_to_film") from exc
    digests = {
        "policy_sha256": _sha256(policy_bytes),
        "task_sha256": _sha256(task_bytes),
        "model_sha256": _sha256(model_bytes),
    }
    declared = str((task.get("model") or {}).get("sha256") or "")
    if declared != digests["model_sha256"]:
        raise CadexDynamics.DynamicsError(
            "The model beside this task is not the one its bundle recorded.",
            reason="evaluation_model_mismatch",
            observed={"declared_sha256": declared,
                      "observed_sha256": digests["model_sha256"]},
        )
    container = CadexDynamics.decode_policy(policy_bytes, context="the evaluated policy")
    traces: dict[int, dict[str, Any]] = {}
    started = time.monotonic()

    def retain(seed: int, document: dict[str, Any]) -> None:
        encoded = json.dumps(document, ensure_ascii=True, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
        name = str(plan["trace"]) if shove else TRACE_NAME.format(seed=seed)
        (out / name).write_bytes(encoded)
        traces[seed] = {"file": name, "sha256": _sha256(encoded), "bytes": len(encoded)}
        sys.stderr.write(f" · seed {seed}  {time.monotonic() - started:.1f} s\n")
        sys.stderr.flush()

    measured = CadexDynamics.evaluate_success(
        model_bytes, task, container, components=list(plan["components"]),
        identity=digests, on_trace=retain,
        context="the shove episode" if shove else "the evaluation",
    )
    for row in measured["seeds"]:
        row["trace"] = traces[row["seed"]]
    header = container["header"]
    measured.update({
        **digests,
        "task_semantic_sha256": semantic,
        "policy_label": str(header.get("label") or ""),
        "mujoco_version": str(task.get("mujoco_version") or ""),
        "wall_time_s": time.monotonic() - started,
    })
    return finite(measured)


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        sys.stderr.write("usage: evaluate_runner.py PLAN.json\n")
        return 2
    plan = json.loads(Path(arguments[0]).read_text(encoding="utf-8"))
    out = Path(plan["out"])
    try:
        report = evaluate(plan)
    except Exception as error:  # noqa: BLE001 - the reason goes to the parent
        reason = getattr(error, "reason", "") or error.__class__.__name__
        refusal = {"error": str(error), "reason": str(reason),
                   "correction": str(getattr(error, "correction", "") or "")}
        (out / plan["measured"]).write_text(json.dumps(refusal) + "\n", encoding="utf-8")
        sys.stderr.write(f"evaluation refused: {error}\n")
        return 3 if hasattr(error, "reason") else 1
    (out / plan["measured"]).write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
