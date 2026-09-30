# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``cadex evaluate``: the accepted policy against its task's success spec (ADR-457).

A task declares what its behaviour must measurably be -- ``assembly.success``
(ADR-456): predicates on behaviour metrics, the frozen evaluation seeds and
the conditions an evaluation episode runs under. This is the one command
that holds a policy to it. It reads the **retained accepted artifacts** the
way ``cadex smoke`` does -- never restoring, rebuilding or accepting a
script -- finds the policy the accepted revision verified, and runs
:mod:`evaluate_runner` under the engine's own interpreter: one rollout per
seed, in the engine's episode loop, measured by the engine's metrics.

Nothing here knows what the behaviour is. The spec names the metrics, the
engine reads the families the mechanism has, and a walk, a reach and a
balance are three specs through one path.

The report is ``evaluation.json`` (``cadex-evaluation-v1``) in the project:
pass or fail per seed and per predicate, the behaviour metrics, the reward
term by term, how each episode ended, and every value each seed drew. A
failed evaluation is a verdict, not a command failure: the exit code is
zero and the verdict is in the report. No spec, no policy or a child that
could not run is a failure with the reason.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Mapping

from .engine import Engine
from .smoke import SmokeError, retained_attempt, smoke_interpreter
from .train import TASK_KIND

#: The child, run by path under :func:`smoke_interpreter`.
EVALUATE_SCRIPT = Path(__file__).resolve().with_name("evaluate_runner.py")
POLICY_KIND = "assembly_policy_receipt_json"
MJCF_KIND = "assembly_mjcf_xml"
REPORT_NAME = "evaluation.json"
REPORT_SCHEMA = "cadex-evaluation-v1"
#: Where an evaluation lands when ``--out`` is not given, under the project.
EVALUATIONS_DIR = "evaluations"
#: Ten ten-second episodes of a sixty-part quadruped take about a minute;
#: this is a bound on a child that hung, not a budget.
DEFAULT_TIMEOUT_S = 1800.0
MAXIMUM_TIMEOUT_S = 7200.0
#: How many failing predicates a progress cell or a note names.
_NAMED = 4


class EvaluateError(RuntimeError):
    """The evaluation could not run: nothing to evaluate, or the child failed."""


class EvaluateRefused(EvaluateError):
    """The accepted revision has nothing this command can evaluate."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _retained_file(staging: Path, item: Mapping[str, Any]) -> Path:
    """One retained artifact, inside the attempt and matching its digest."""

    path = (staging / str(item.get("artifact_path") or "")).resolve()
    if not path.is_relative_to(staging) or not path.is_file():
        raise EvaluateError(f"missing or escaping retained artifact: {item.get('name')}")
    if item.get("artifact_sha256") and _sha256(path) != item["artifact_sha256"]:
        raise EvaluateError(f"retained artifact digest mismatch: {item.get('name')}")
    return path


def retained_inputs(root: Path, *, task_name: str = "", policy_name: str = "") -> dict[str, Any]:
    """What the accepted revision retained for one evaluation.

    The policy is the one the accepted script declared and the engine
    verified: its receipt names the task it was verified against and the
    weights it read. Several policies are a choice, made with ``--policy``
    (the output's name) or ``--task``; exactly one must remain. The weights
    are read from the attempt's own staged assets and must hash to what the
    receipt recorded, so the file evaluated is the file verified.
    """

    try:
        state, staging, result = retained_attempt(root)
    except SmokeError as exc:
        raise EvaluateRefused(str(exc)) from exc
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise EvaluateRefused(f"cannot read the retained accepted attempt: {exc}") from exc
    items = {str(item["name"]): item for item in result["outputs"]}
    policies = [item for item in items.values() if item.get("artifact_kind") == POLICY_KIND]
    if not policies:
        raise EvaluateRefused(
            "the accepted revision declares no policy: train one (cadex train "
            "--put) and name it with assembly.policy(task, weights=..., sha256=...)."
        )
    receipts = {str(item["name"]): json.loads(_retained_file(staging, item).read_text(encoding="utf-8"))
                for item in policies}
    chosen = [name for name, receipt in receipts.items()
              if (not policy_name or name == policy_name)
              and (not task_name or str(receipt.get("task_output")) == task_name)]
    if len(chosen) != 1:
        listing = ", ".join(f"{name} (task {receipt.get('task_output')})"
                            for name, receipt in receipts.items())
        raise EvaluateRefused(
            ("no declared policy matches" if not chosen else "more than one declared policy matches")
            + f"; pick one with --policy NAME or --task NAME: {listing}."
        )
    receipt = receipts[chosen[0]]
    task_item = items.get(str(receipt.get("task_output")))
    if task_item is None or task_item.get("artifact_kind") != TASK_KIND:
        raise EvaluateError(f"policy {chosen[0]} names no retained task bundle")
    task_path = _retained_file(staging, task_item)
    task = json.loads(task_path.read_text(encoding="utf-8"))
    if not isinstance(task.get("success"), Mapping):
        raise EvaluateRefused(
            f"task {task_item['name']} declares no success spec, so there are no "
            "seeds, conditions or predicates to evaluate against. Give it one: "
            "assembly.task(..., success=assembly.success(predicates=[...], seeds=[...]))."
        )
    model_item = items.get(str((task.get("model") or {}).get("output")))
    if model_item is None or model_item.get("artifact_kind") != MJCF_KIND:
        raise EvaluateError(f"task {task_item['name']} names no retained MJCF model")
    weights = (staging / "assets" / str(receipt.get("weights") or "")).resolve()
    if weights.parent != staging / "assets" or not weights.is_file():
        raise EvaluateError(f"policy {chosen[0]} has no staged weights {receipt.get('weights')!r}")
    if _sha256(weights) != str(receipt.get("policy_sha256")):
        raise EvaluateError(
            f"the staged weights {weights.name} are not the file policy {chosen[0]} was verified with"
        )
    return {
        "accepted_revision": str(state["accepted_revision"]),
        "accepted_digest": str(state.get("accepted_digest") or ""),
        "policy_output": chosen[0],
        "task_output": str(task_item["name"]),
        "model_output": str(model_item["name"]),
        "policy": weights,
        "policy_sha256": str(receipt["policy_sha256"]),
        "weights": str(receipt["weights"]),
        "trained_task_sha256": str(receipt.get("task_sha256") or ""),
        "task": task_path,
        "model": _retained_file(staging, model_item),
        "components": [str(name) for name in
                       (model_item.get("assembly_data") or {}).get("component_outputs") or []],
        "seeds": [int(seed) for seed in task["success"].get("seeds") or []],
    }


def default_out(root: Path, inputs: Mapping[str, Any]) -> Path:
    """``evaluations/<revision>-<policy>``: one accepted revision and one
    policy are one evaluation, and running it again is the same episodes."""

    return root / EVALUATIONS_DIR / (
        f"{str(inputs['accepted_revision'])[:12]}-{str(inputs['policy_sha256'])[:12]}"
    )


def check_out(root: Path, out: Path) -> Path:
    """``out`` resolved, and never over the project's own state."""

    out = out.expanduser().resolve()
    root = root.resolve()
    if out == root or any(out.is_relative_to(root / protected)
                          for protected in ("script_artifacts", "assets", ".git")):
        raise EvaluateError("--out must not overwrite the project root or accepted artifacts")
    return out


def run_evaluation(engine: Engine, inputs: Mapping[str, Any], out: Path, *,
                   timeout: float = DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    """Run the child over ``inputs`` into ``out`` and return the report it measured.

    The child's stderr -- one line per seed -- passes straight through, as
    the trainer's does. The report is written last and atomically, so a
    killed evaluation leaves no ``evaluation.json`` that looks complete.
    """

    out.mkdir(parents=True, exist_ok=True)
    report_path = out / REPORT_NAME
    report_path.unlink(missing_ok=True)
    for stale in out.glob("seed-*-trace.json"):
        stale.unlink()
    measured_name = "evaluation-measured.json"
    plan = {
        "module_dir": str(engine.module_dir),
        "model": str(inputs["model"]),
        "task": str(inputs["task"]),
        "policy": str(inputs["policy"]),
        "components": list(inputs["components"]),
        "out": str(out),
        "measured": measured_name,
    }
    python = smoke_interpreter(engine)
    with tempfile.TemporaryDirectory(prefix="cadex-evaluate-") as scratch:
        plan_path = Path(scratch) / "plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        try:
            completed = subprocess.run(
                [str(python), str(EVALUATE_SCRIPT), str(plan_path)],
                stdout=subprocess.PIPE, text=True, timeout=timeout,
            )
        except OSError as exc:
            raise EvaluateError(f"could not run the evaluation: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise EvaluateError(
                f"the evaluation ran past its bound of {timeout:g} s and was killed (--timeout)."
            ) from exc
    measured_path = out / measured_name
    try:
        measured = json.loads(measured_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise EvaluateError(
            f"the evaluation exited {completed.returncode} and wrote no readable result."
        ) from exc
    finally:
        measured_path.unlink(missing_ok=True)
    if completed.returncode != 0 or measured.get("error"):
        text = str(measured.get("error") or f"exit {completed.returncode}")
        if measured.get("correction"):
            text += " " + str(measured["correction"])
        if completed.returncode == 3:
            raise EvaluateRefused(f"the evaluation was refused: {text}")
        raise EvaluateError(f"the evaluation failed: {text}")
    if measured.get("schema") != REPORT_SCHEMA or not isinstance(measured.get("seeds"), list):
        raise EvaluateError(f"{measured_path} is not an evaluation report.")
    if measured.get("policy_sha256") != inputs["policy_sha256"]:
        raise EvaluateError("the evaluation ran a policy other than the accepted one")
    summary = measured["summary"]
    report = {
        "schema": REPORT_SCHEMA,
        "verdict": "pass" if summary["pass"] else "fail",
        "accepted_revision": inputs["accepted_revision"],
        "accepted_digest": inputs["accepted_digest"],
        "policy_output": inputs["policy_output"],
        "task_output": inputs["task_output"],
        "model_output": inputs["model_output"],
        "weights": inputs["weights"],
        "trained_task_sha256": inputs["trained_task_sha256"],
        "engine": engine.describe(),
        **measured,
    }
    scratch_path = report_path.with_suffix(".json.tmp")
    scratch_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    scratch_path.replace(report_path)
    return report


def failing_predicates(report: Mapping[str, Any]) -> list[str]:
    """``id (n of m)`` for every predicate a seed failed, worst first.

    Void seeds lead the list: a simulation that went unstable is why a seed
    failed even when every predicate read as met.
    """

    summary = report.get("summary") or {}
    seeds = int(summary.get("seeds") or 0)
    rows = [row for row in summary.get("predicates") or [] if row.get("failed_seeds")]
    rows.sort(key=lambda row: -len(row["failed_seeds"]))
    void = summary.get("void") or []
    return ([f"unstable simulation ({len(void)} of {seeds})"] if void else []) + [
        f"{row['id']} ({len(row['failed_seeds'])} of {seeds})" for row in rows]


def evaluation_cell(report: Mapping[str, Any]) -> str:
    """The ``PROGRESS.md`` numbers cell: the verdict and what failed."""

    summary = report.get("summary") or {}
    head = "evaluation {:s} {:d}/{:d} seeds".format(
        str(report.get("verdict") or "?"), len(summary.get("passed") or []),
        int(summary.get("seeds") or 0))
    failing = failing_predicates(report)
    if not failing:
        return head
    return head + ": " + "; ".join(failing[:_NAMED]) + (
        f" (+{len(failing) - _NAMED} more)" if len(failing) > _NAMED else "")


def human_lines(report: Mapping[str, Any]) -> list[str]:
    """The prose block: the verdict, each predicate's tally, each seed's failures."""

    summary = report.get("summary") or {}
    lines = ["evaluate {:s}  {:d} of {:d} seeds pass  policy {:s}  task {:s}".format(
        str(report.get("verdict") or "?"), len(summary.get("passed") or []),
        int(summary.get("seeds") or 0), str(report.get("policy_sha256") or "")[:12],
        str(report.get("task_output") or ""))]
    for row in summary.get("predicates") or []:
        value = row.get("value")
        bound = " ".join(f"{word} {row[key]:g}" for word, key in (("≥", "min"), ("≤", "max"))
                         if row.get(key) is not None)
        spread = "not measured" if not value else "{:.4g} … {:.4g}".format(value["min"], value["max"])
        lines.append("  {:s} {:s} {:s}: {:d} of {:d}  ({:s})".format(
            "ok  " if not row.get("failed_seeds") else "FAIL", str(row.get("id")),
            f"{row.get('metric')} {bound}", int(row.get("passed") or 0),
            int(summary.get("seeds") or 0), spread))
    causes = summary.get("terminations") or {}
    if causes:
        lines.append("  ended: " + ", ".join(f"{cause} ×{count}" for cause, count in causes.items()))
    if summary.get("void"):
        lines.append("  void: the simulation went unstable on seed(s) "
                     + ", ".join(str(seed) for seed in summary["void"]))
    return lines

