# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``cadex walk``: the lifecycle walk as one command (ADR-199).

The walk — design, assembly, MJCF and task, local toy-scale training,
policy verify, rollout, review — existed leg by leg after ADR-189 to
ADR-195 (``docs/MUJOCO.md`` §7c), and ``docs/CLI.md`` §2 documented it as
"four commands and one digest edit". The digest edit was the one leg that
was still a person's or a ``sed``'s: after ``cadex train --put`` reports
the stored policy's sha256, somebody has to write it into the script's
``assembly.policy(weights=…, sha256=…)`` call before the engine will
verify and roll the policy out. This module is that edit, and the order of
the legs around it, so the whole walk is one entry point a pipeline or a
person runs with nothing to type in between.

It runs each leg as a **child ``cadex`` command** rather than calling the
engine itself, on purpose: every leg then lands the ``PROGRESS.md`` row and
the project commit it always lands (ADR-193, ADR-194), the artifacts are
the ones the documented commands write, and the walk adds no second way of
doing any of them. The GUI-attached and remote-training modes share the
shape because they share the legs, not because they share this file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Sequence

#: The switch parameter the iterate convention names (ADR-192): the policy
#: is declared only while it reads 1, so a sweep can blank it and the walk
#: turns it back on after the re-declare.
POLICY_SWITCH = "policy_on"

#: Where the walk's own files go under ``--out``: the sweep's bundle (only
#: with ``--set``), the training bundle and policy, the rewritten script,
#: the verified rollout, and the review — the numbers, as one file beside
#: the artifacts they were read from, so a walk run under the project
#: (``--out <project>/runs/<name>``) leaves its review in the project.
SWEEP_DIRNAME = "sweep"
TRAIN_DIRNAME = "train"
ROLLOUT_DIRNAME = "rollout"
SCRIPT_FILENAME = "script.py"
REVIEW_FILENAME = "review.json"

_CLI_DIR = Path(__file__).resolve().parents[1]


class WalkError(RuntimeError):
    """A leg refused, or the script cannot carry the declaration."""


def cadex_command() -> list[str]:
    """How a leg is spawned: this interpreter, this package.

    The same thing ``./cadex`` execs, so a leg resolves the engine, the
    trainer venv and the project exactly as the command typed by hand
    would. Tests replace this with a script that answers in envelopes.
    """

    return [sys.executable, "-m", "cadex_cli"]


@dataclass
class Leg:
    """One child command: what was run, how it ended, what it reported."""

    name: str
    argv: list[str]
    code: int = 0
    seconds: float = 0.0
    envelope: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "leg": self.name,
            "argv": list(self.argv),
            "exit": int(self.code),
            "seconds": round(float(self.seconds), 2),
        }
        for key in ("accepted_revision", "digest", "error"):
            if self.envelope.get(key):
                payload[key] = self.envelope[key]
        return payload


def run_leg(name: str, argv: Sequence[str], *, capture: bool = True) -> Leg:
    """Run one leg and return it with its envelope (or its printed text).

    Stderr passes straight through — the legs' progress lines and the
    trainer's reward curve belong there. Stdout is the leg's ``--json``
    envelope, or with ``capture`` false the raw text (``cadex script``
    prints the source and nothing else), kept under ``"text"``.
    """

    command = [*cadex_command(), *argv]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_CLI_DIR) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=None, text=True, env=env
        )
    except OSError as exc:
        raise WalkError(f"{name}: could not run {command[0]}: {exc}") from exc
    leg = Leg(name=name, argv=list(argv), code=completed.returncode,
              seconds=time.monotonic() - started)
    if not capture:
        leg.envelope = {"text": completed.stdout}
        return leg
    try:
        parsed = json.loads(completed.stdout)
    except ValueError:
        parsed = None
    if isinstance(parsed, dict):
        leg.envelope = parsed
    elif completed.returncode == 0:
        raise WalkError(
            f"{name}: the leg exited 0 but printed no envelope: "
            + completed.stdout.strip()[-400:]
        )
    return leg


_SWITCH_RE = re.compile(rf"\b{POLICY_SWITCH}\s*=\s*num\s*\(")
_CALL_RE = re.compile(r"\bassembly\.policy\s*\(")


def _call_span(source: str, start: int) -> int:
    """Index one past the ``)`` that closes the call opened at ``start``."""

    depth = 0
    quote = ""
    index = start
    while index < len(source):
        char = source[index]
        if quote:
            if char == "\\":
                index += 1
            elif char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    raise WalkError("the assembly.policy(...) call never closes.")


def _replace_keyword(call: str, keyword: str, value: str) -> str:
    pattern = re.compile(rf"(\b{keyword}\s*=\s*)(['\"])(?:\\.|(?!\2).)*\2")
    match = pattern.search(call)
    if match is None:
        raise WalkError(
            f"the assembly.policy(...) call carries no {keyword}=\"…\" string "
            "to rewrite (docs/CLI.md §2, the iterate convention)."
        )
    return call[: match.start()] + match.group(1) + json.dumps(value) + call[match.end():]


def declare_policy(source: str, weights: str, sha256: str) -> str:
    """The script with its one policy declaration re-pointed.

    The iterate convention (ADR-192) is what makes this a rewrite rather
    than an authoring step: the script already carries ``policy_on`` and
    one ``assembly.policy(task, weights="…", sha256="…")`` call behind it,
    so the walk changes two string literals and nothing else. A script
    without the convention is refused with the convention named — the
    walk does not guess where a policy belongs in a script it did not
    write.
    """

    if _SWITCH_RE.search(source) is None:
        raise WalkError(
            f"the script declares no {POLICY_SWITCH}=num(...) parameter: the "
            "walk needs the iterate convention (docs/CLI.md §2, ADR-192) — "
            "a numeric switch in front of assembly.policy and assembly.rollout."
        )
    calls = list(_CALL_RE.finditer(source))
    if len(calls) != 1:
        raise WalkError(
            "the script must carry exactly one assembly.policy(...) call for "
            f"the walk to re-point; it has {len(calls)}."
        )
    start = calls[0].start()
    end = _call_span(source, calls[0].end() - 1)
    call = source[start:end]
    call = _replace_keyword(call, "weights", weights)
    call = _replace_keyword(call, "sha256", sha256)
    return source[:start] + call + source[end:]


def review_from_outputs(outputs: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """The rollout's numbers, read from the exported trace.

    The trace's ``policy`` block is where a run's number lives (§7c row 7):
    ``total_reward``, the per-term ``reward_totals``, the policy's sha256.
    No trace is an empty review, and the walk says so rather than
    inventing a zero.
    """

    for output in outputs:
        files = output.get("files") if isinstance(output, dict) else None
        for path in (files or {}).values():
            path = str(path)
            if not path.endswith(".json") or "trace" not in Path(path).name:
                continue
            try:
                payload = json.loads(Path(path).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            policy = payload.get("policy") if isinstance(payload, dict) else None
            if not isinstance(policy, dict):
                continue
            review: dict[str, Any] = {"trace": path}
            for key in ("total_reward", "reward_totals", "policy_sha256",
                        "steps", "frames"):
                if policy.get(key) is not None:
                    review[key] = policy[key]
            return review
    return {}


def write_review(
    out_dir: Path,
    *,
    review: dict[str, Any],
    legs: Sequence[dict[str, Any]],
    training: dict[str, Any],
    params: dict[str, Any],
) -> Path:
    """Land the walk's review as ``review.json`` under ``--out``.

    What a reader of the project needs without the envelope: the policy
    that was verified, the trace's numbers, the trainer's receipt figures,
    the parameters the rollout ran at, and the legs in order with their
    exit codes and timings. Paths are written relative to ``out_dir``
    where they fall under it, so the file reads the same from any clone.
    """

    def relative(value: Any) -> Any:
        try:
            return str(Path(str(value)).resolve().relative_to(out_dir.resolve()))
        except (ValueError, OSError):
            return value

    payload: dict[str, Any] = {
        "schema": "cadex-walk-review-v1",
        "weights": review.get("weights"),
        "sha256": review.get("sha256"),
        "total_reward": review.get("total_reward"),
        "reward_totals": review.get("reward_totals"),
        "trace": relative(review["trace"]) if review.get("trace") else None,
        "params": dict(params),
        "training": {
            key: training.get(key)
            for key in ("reward_per_step", "wall_time_s", "device", "task_sha256",
                        "witness_error", "parameters")
            if training.get(key) is not None
        },
        "legs": [
            {key: value for key, value in leg.items() if key != "argv"}
            for leg in legs
        ],
    }
    path = out_dir / REVIEW_FILENAME
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return path
