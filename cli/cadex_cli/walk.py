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

from contextlib import contextmanager
from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time
from typing import Any, Sequence
import xml.etree.ElementTree as ElementTree

from .project_docs import DECLARED_NOTE_SUBJECTS

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


#: How long any one leg may run before the walk stops it, in seconds.
#: The two design turns this run measured took 629.6 s and 1,014.2 s, so an
#: hour is far above anything a leg has ever legitimately needed and still
#: bounds a machine that would otherwise wait forever on a provider that
#: stalls rather than refusing. ``--leg-timeout 0`` restores no limit.
DEFAULT_LEG_TIMEOUT_S = 3600.0

#: How long a stopped leg has to die on ``SIGTERM`` before it is killed.
LEG_TERMINATION_GRACE_S = 5.0

#: How long the walk will wait to drain a stopped leg's stdout. The pipe is
#: inherited by everything the leg started, so a survivor the kill could not
#: reach — a process stopped, uninterruptibly blocked, or in another session
#: of its own — would otherwise hold the read open forever and hang the walk
#: at exactly the point the timeout was meant to save it. The stopped leg's
#: envelope is synthesised, so whatever text is lost here was never read.
LEG_DRAIN_S = 10.0

#: A trainer bounded by ``--timeout`` still has to write its policy and its
#: receipt afterwards, so the walk's own bound never undercuts the trainer's.
TRAIN_LEG_GRACE_S = 300.0

#: The exit code a stopped leg is reported with — GNU ``timeout``'s, so a
#: reader who knows one knows the other. It is not ``EXIT_USAGE`` or
#: ``EXIT_REJECTED``, so the walk fails through its ordinary ``failed(...)``
#: path at ``EXIT_FAILURE``: running out of time is a leg that did not
#: succeed, not a new kind of refusal.
EXIT_LEG_TIMEOUT = 124


def train_leg_timeout(leg_timeout: float, trainer_timeout: float) -> float:
    """The train leg's bound: the walk's, but never under the trainer's.

    ``--timeout`` is the trainer's internal limit and ``--leg-timeout`` is
    the walk's limit on the whole child command; a caller who asks for a
    45-minute training run should not have it shot at the hour by a default
    they never typed, so the train leg gets whichever is larger, plus the
    grace the receipt and the ``--put`` copy need.
    """

    if leg_timeout <= 0:
        return 0.0
    if trainer_timeout <= 0:
        return leg_timeout
    return max(leg_timeout, trainer_timeout + TRAIN_LEG_GRACE_S)


def leg_pgid(process: "subprocess.Popen[str]") -> int | None:
    """The leg's process group, read while the leg is certainly alive.

    It has to be taken before the child can exit: once ``wait`` has reaped
    it, ``os.getpgid(process.pid)`` raises and the group — which may still
    hold the grandchild that was the thing actually hanging — becomes
    unreachable. ``start_new_session`` makes this the child's own pid, so a
    stale group id would need a full pid wraparound to alias anything.
    """

    try:
        return os.getpgid(process.pid)
    except (AttributeError, OSError):
        return None


def _signal_leg(
    process: "subprocess.Popen[str]", number: int, pgid: int | None = None
) -> None:
    """Signal the leg's whole group, or the leg alone where there is none."""

    if pgid is None:
        pgid = leg_pgid(process)
    if pgid is not None:
        try:
            os.killpg(pgid, number)
            return
        except OSError:
            pass
    try:
        process.send_signal(number)
    except (OSError, ValueError):
        pass


def _stop_leg(process: "subprocess.Popen[str]", pgid: int | None = None) -> None:
    """End a leg that ran out of time, and everything under it.

    ``SIGTERM`` to the group first, so a leg that has a chance to close its
    engine session takes it; ``SIGKILL`` to the group after the grace —
    **unconditionally**, not only when the direct child is still running.
    The group is the point: the child is a ``cadex`` command that has itself
    spawned the agent CLI or the trainer, and the hang that matters is the
    one where the direct child dies politely and the grandchild ignores
    ``SIGTERM``, survives, and goes on holding the captured stdout. Waiting
    on the direct child alone reports that leg as stopped while the machine
    is still occupied and the walk is still blocked on the pipe.
    """

    if pgid is None:
        pgid = leg_pgid(process)
    _signal_leg(process, signal.SIGTERM, pgid)
    try:
        process.wait(timeout=LEG_TERMINATION_GRACE_S)
    except subprocess.TimeoutExpired:
        pass
    _signal_leg(process, signal.SIGKILL, pgid)
    try:
        process.wait(timeout=LEG_TERMINATION_GRACE_S)
    except subprocess.TimeoutExpired:
        pass


@contextmanager
def _relaying_signals(
    process: "subprocess.Popen[str]", pgid: int | None = None
) -> Any:
    """Ctrl-C still reaches a leg that is a session of its own.

    ``start_new_session`` is what lets the timeout stop the leg's whole
    subtree, and it also takes the leg out of the terminal's foreground
    group, so an interactive ``SIGINT`` would no longer reach it. Relaying
    the two signals a person or a supervisor actually sends puts that back,
    and puts it back wider than it was: the relay goes to the session, so
    the agent CLI or trainer under the leg stops too.
    """

    if threading.current_thread() is not threading.main_thread():
        yield
        return
    previous: dict[int, Any] = {}

    def relay(number: int, frame: Any) -> None:
        _signal_leg(process, number, pgid)
        signal.signal(number, previous.get(number, signal.SIG_DFL))
        os.kill(os.getpid(), number)

    try:
        for number in (signal.SIGINT, signal.SIGTERM):
            previous[number] = signal.signal(number, relay)
        yield
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def _drain(process: "subprocess.Popen[str]") -> str:
    """Read what is left of a stopped leg's stdout, without waiting forever.

    Whatever arrived is returned; a pipe still held open past
    :data:`LEG_DRAIN_S` is abandoned and closed, because the alternative is
    the hang the bound exists to prevent.
    """

    try:
        stdout, _ = process.communicate(timeout=LEG_DRAIN_S)
    except subprocess.TimeoutExpired as expired:
        stdout = expired.stdout or ""
        if isinstance(stdout, bytes):  # pragma: no cover - text=True here
            stdout = stdout.decode("utf-8", "replace")
        if process.stdout is not None:
            try:
                process.stdout.close()
            except OSError:  # pragma: no cover - closing a dead pipe
                pass
    return stdout or ""


def run_leg(
    name: str, argv: Sequence[str], *, capture: bool = True, timeout: float = 0.0
) -> Leg:
    """Run one leg and return it with its envelope (or its printed text).

    Stderr passes straight through — the legs' progress lines and the
    trainer's reward curve belong there. Stdout is the leg's ``--json``
    envelope, or with ``capture`` false the raw text (``cadex script``
    prints the source and nothing else), kept under ``"text"``.

    ``timeout`` bounds the leg in wall clock; zero is no limit. A leg that
    runs out of time is stopped, subtree and all, and comes back as an
    ordinary failed leg — exit :data:`EXIT_LEG_TIMEOUT`, the reason in its
    envelope's ``error`` — so the walk ends through the same path a
    refusing leg ends it through. This is what makes the walk safe to run
    with nobody watching: every leg spawns something the walk does not
    control, and before this each of them could hang the run forever.
    """

    command = [*cadex_command(), *argv]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_CLI_DIR) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=None, text=True, env=env,
            start_new_session=True,
        )
    except OSError as exc:
        raise WalkError(f"{name}: could not run {command[0]}: {exc}") from exc
    pgid = leg_pgid(process)
    stopped = False
    with _relaying_signals(process, pgid):
        try:
            stdout, _ = process.communicate(timeout=timeout or None)
        except subprocess.TimeoutExpired:
            stopped = True
            _stop_leg(process, pgid)
            stdout = _drain(process)
    leg = Leg(name=name, argv=list(argv), code=process.returncode,
              seconds=time.monotonic() - started)
    if stopped:
        leg.code = EXIT_LEG_TIMEOUT
        leg.envelope = {"error": (
            f"the {name} leg was stopped after {timeout:g}s (--leg-timeout); "
            "it and everything under it were killed."
        )}
        return leg
    if not capture:
        leg.envelope = {"text": stdout}
        return leg
    try:
        parsed = json.loads(stdout)
    except ValueError:
        parsed = None
    if isinstance(parsed, dict):
        leg.envelope = parsed
    elif process.returncode == 0:
        raise WalkError(
            f"{name}: the leg exited 0 but printed no envelope: "
            + stdout.strip()[-400:]
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


#: The MJCF the training bundle names, as it lands under ``--out/train``
#: (``docs/CLI.md`` §2: ``<name>-model.xml`` beside ``<name>-task.json``).
MODEL_GLOB = "*-model.xml"


def declared_note_subjects(train_dir: Path | str) -> tuple[list[str], Path | None]:
    """The domain-note subjects the model the walk trained on declares.

    Read from the exported MJCF rather than from the script, because that
    file is what the trainer and the rollout actually ran: an ``<actuator>``
    section with children means the mechanism is driven, a ``<sensor>``
    section means it is observed, and each asks the project for the note
    the authoring contract names (``docs/actuators.md``, ``docs/sensors.md``
    -- ADR-245, ADR-256). No bundle, no declaration and no finding: the
    subjects are empty and the walk says nothing rather than guessing.
    """

    try:
        models = sorted(Path(train_dir).glob(MODEL_GLOB))
    except OSError:
        return [], None
    for path in models:
        try:
            root = ElementTree.parse(path).getroot()
        except (OSError, ElementTree.ParseError):
            continue
        subjects = [
            subject
            for section, subject in DECLARED_NOTE_SUBJECTS.items()
            if any(len(node) for node in root.iter(section))
        ]
        return subjects, path
    return [], None


#: The frame kind the assembly trace uses for the pose the solver was
#: *given* rather than one it produced. It is frame 0 on both documented
#: examples (27 raw frames = 1 input + 26 solved), it carries
#: ``nominal_time_s: None``, and counting it would report the solver's
#: input as if it were an output — so travel is measured over the solved
#: frames only, against the first of them.
INPUT_FRAME_KIND = "input"


def _quaternion_swing_deg(first: Sequence[float], other: Sequence[float]) -> float:
    """The angle between two orientations, in degrees.

    ``2·acos(|q0·q|)`` — the absolute value because ``q`` and ``-q`` are the
    same orientation, and the clamp because a dot product of two unit
    quaternions can land a hair outside [-1, 1] in floating point and
    ``acos`` would raise.
    """

    dot = abs(sum(a * b for a, b in zip(first, other)))
    return 2.0 * math.degrees(math.acos(min(1.0, max(-1.0, dot))))


def motion_from_trace(payload: dict[str, Any]) -> dict[str, Any]:
    """How far, and how much, each component actually moved in the rollout.

    Two channels, because one of them alone is a wrong answer rather than a
    partial one: the repository's own hinged-arm example travels **0.0000
    mm** and rotates **178.8334°**, so a displacement-only report says a
    working revolute mechanism never moved. Per component this reports the
    per-axis position range, the largest displacement from the reference
    pose, and the largest rotation swing away from the reference
    orientation.

    The reference is the **first solved frame**, and only solved frames are
    counted (see :data:`INPUT_FRAME_KIND`). Placements are absolute world
    poses, not offsets — the hinged arm's ``swing`` starts at
    ``[12, 0, 6]`` — so every figure here is a difference against that
    first solved pose and never against the origin.

    A trace with no frames is unavailable and says why. A trace whose
    frames are all identical is **zero travel**, which is a measurement,
    not a missing one.
    """

    frames = payload.get("frames")
    if not isinstance(frames, list) or not frames:
        return {"available": False, "reason": "the trace exported no frames."}
    solved = [
        frame for frame in frames
        if isinstance(frame, dict) and frame.get("frame_kind") != INPUT_FRAME_KIND
    ]
    excluded = len(frames) - len(solved)
    if not solved:
        return {
            "available": False,
            "reason": "the trace exported {:d} frame(s), all of kind {!r}.".format(
                len(frames), INPUT_FRAME_KIND,
            ),
        }
    reference = solved[0].get("component_placements")
    if not isinstance(reference, dict) or not reference:
        return {"available": False, "reason": "the solved frames placed no components."}

    components: dict[str, Any] = {}
    for name, place in sorted(reference.items()):
        position0 = [float(value) for value in place.get("position_mm") or (0.0, 0.0, 0.0)]
        rotation0 = [float(value) for value in place.get("rotation_xyzw") or (0.0, 0.0, 0.0, 1.0)]
        lows, highs = list(position0), list(position0)
        displacement = 0.0
        swing = 0.0
        for frame in solved:
            place = (frame.get("component_placements") or {}).get(name)
            if not isinstance(place, dict):
                continue
            position = [float(value) for value in place.get("position_mm") or position0]
            rotation = [float(value) for value in place.get("rotation_xyzw") or rotation0]
            for axis in range(3):
                lows[axis] = min(lows[axis], position[axis])
                highs[axis] = max(highs[axis], position[axis])
            displacement = max(displacement, math.dist(position, position0))
            swing = max(swing, _quaternion_swing_deg(rotation0, rotation))
        components[name] = {
            "position_range_mm": [high - low for low, high in zip(lows, highs)],
            "max_displacement_mm": displacement,
            "max_rotation_deg": swing,
        }

    def largest(key: str, unit: str) -> dict[str, Any]:
        # Ties break on the name so the block is stable across runs.
        name = max(components, key=lambda item: (components[item][key], item))
        return {"component": name, unit: components[name][key]}

    times = [
        float(frame["nominal_time_s"]) for frame in solved
        if isinstance(frame.get("nominal_time_s"), (int, float))
    ]
    return {
        "available": True,
        "reference": "first solved frame",
        "frames_counted": len(solved),
        "frames_excluded": excluded,
        "excluded_frame_kind": INPUT_FRAME_KIND if excluded else None,
        "duration_s": (max(times) - min(times)) if times else None,
        "components": components,
        "largest_translation": largest("max_displacement_mm", "millimetres"),
        "largest_rotation": largest("max_rotation_deg", "degrees"),
        # Millimetres and degrees do not compare, and inventing a scale to
        # make them compare would rank a carriage free-falling 4,739 mm on
        # an ideal guide above a swing arm doing its job through 178.8°.
        # Both channels are named; neither is a score.
        "ranking": "declined: millimetres and degrees are not comparable, "
                   "so both largest movers are named",
    }


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
            # The same file carries the poses, so the travel is read here
            # rather than opening the trace a second time.
            review["motion"] = motion_from_trace(payload)
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

    documentation = dict(review.get("documentation") or {})
    if documentation.get("model"):
        documentation["model"] = relative(documentation["model"])

    payload: dict[str, Any] = {
        "schema": "cadex-walk-review-v1",
        "documentation": documentation,
        "inventory": dict(review.get("inventory") or {}),
        "render": dict(review.get("render") or {}),
        "section": dict(review.get("section") or {}),
        "walk_seconds": review.get("walk_seconds"),
        "clearance": dict(review.get("clearance") or {}),
        "motion": dict(review.get("motion") or {"available": False,
                                                "reason": "no trace was exported."}),
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
