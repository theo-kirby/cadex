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
        name = TRACE_NAME.format(seed=seed)
        (out / name).write_bytes(encoded)
        traces[seed] = {"file": name, "sha256": _sha256(encoded), "bytes": len(encoded)}
        sys.stderr.write(f" · seed {seed}  {time.monotonic() - started:.1f} s\n")
        sys.stderr.flush()

    measured = CadexDynamics.evaluate_success(
        model_bytes, task, container, components=list(plan["components"]),
        identity=digests, on_trace=retain, context="the evaluation",
    )
    for row in measured["seeds"]:
        row["trace"] = traces[row["seed"]]
    header = container["header"]
    measured.update({
        **digests,
        "task_semantic_sha256": CadexDynamics.task_semantic_digest(task),
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
