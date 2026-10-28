#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""One task bundle in, one ``.cxpolicy`` out, on a machine that has a GPU.

**This program is not part of the engine and is never installed into the
payload.** It lives at the repository root because it is a thing you *copy*
to another machine: ``pixi`` never sees it, CMake never installs it, and its
dependencies are pinned in ``training/requirements.txt`` and installed into
a venv on whatever box does the training. ``CARRIED_PYPI_PACKAGES`` stays
one entry long, which is what ADR-076 named that constant for.

Held to a strict import discipline: it imports only ``jax``, ``mujoco``,
``mujoco.mjx``, ``numpy``, Brax's PPO (``brax``, ``flax``, ``optax``;
ADR-712) and the standard library, and it reports whether
``CadexDynamics`` was importable so a test can assert the negative. Run
under ``python -P`` with a scrubbed ``PYTHONPATH`` that is ``false``; if it
ever comes back ``true`` the process was not stock and the run proves
nothing about what a trainer can do with the bundle alone.

**Why training is offboard.** MJX needs JAX-on-GPU, ``jax-metal`` is 0.1.0,
and the published reference for a humanoid gait is 4096 parallel
environments on an RTX 4090. ADR-075 recorded that as a design constraint
rather than a temporary one, and M7 does not build dispatch machinery for
it: no network I/O, no new op, no daemon. You scp two files to a box, run
this, and scp one file back. What comes home enters the project the way
every other byte does -- through ``put_asset`` (ADR-043).

**Two evaluators.** ``CadexDynamics`` compiles reward expressions, and this
compiles them again under ``jax.numpy`` so they vectorise. Two is where a
whitelist drifts, so the bundle ships its ``functions`` array, this
file builds its own from scratch, and it **refuses outright** when the two
differ rather than failing partway through a training run.

**The container this writes is byte-identical to what the engine writes.**
``encode_policy`` in ``CadexDynamics`` and :func:`encode_policy` here are
two implementations of one format; no test compares their bytes since
ADR-725, so change them together. That is the same move the reward whitelist
gets, for the same reason: this file
cannot import the engine, so the second copy is written down and pinned.

Usage::

    python cadex_train.py <root>/outputs/<name>-task.json \\
        --seed 0 --iterations 200 --out walk.cxpolicy
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import sys
import time
from typing import Any, Sequence
from xml.etree import ElementTree

TASK_SCHEMA = "cadex-training-task-v1"
POLICY_SCHEMA = "cadex-policy-v1"
POLICY_MAGIC = b"CXPOLICY1\n"

#: The digest of the code this process runs, taken once at import. Hashing
#: the file at save time instead let a run that straddled an edit stamp its
#: later checkpoints with code it never executed (ADR-466).
TRAINER_SHA256 = hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()

#: Which fields of an action row have to agree for a policy to belong to a
#: bundle. The engine's ``CadexDynamics._POLICY_ACTION_FIELDS``, copied here
#: because this file may not import it, and pinned equal by
#: ``test_the_trainers_action_fields_agree_with_the_engines``.
#:
#: Note what is *absent*: ``source``. Two bundles that derive the same
#: numbers by different routes -- a joint's limits, or a declared command
#: range that happens to coincide with them -- describe the same action space
#: and verify the same policy. That is deliberate (ADR-131).
_POLICY_ACTION_FIELDS = ("actuator", "index", "unit", "low", "high", "scale")

#: The schema of ``progress.json`` -- the one artifact a run publishes while
#: it is still running, and the only thing ``remote_train.sh watch`` and the
#: dashboard read. Versioned like every other file this tree
#: writes, because two of its three readers are on other machines.
PROGRESS_SCHEMA = "cadex-training-progress-v1"

#: The most reward-curve points ``progress.json`` carries. 512 pairs is
#: ~12 KB of JSON rewritten per iteration and more x-resolution than any
#: panel has pixels for; the full-fidelity curve still exists in memory and
#: on stderr, this is only what the progress file republishes.
CURVE_POINTS_CAP = 512


def decimated_curve(curve, cap=CURVE_POINTS_CAP, key="reward_per_step"):
    """A metric history as ``[[iteration, value], ...]``, capped.

    Uniform stride with the first and last points always kept, so the
    shape survives and the newest point is always the real newest point.
    Pure stdlib on plain dicts, so the static half of the trainer suite can
    pin it without jax in the room.
    """

    points = [
        [int(entry["iteration"]), float(entry[key])]
        for entry in curve if entry.get(key) is not None
    ]
    if cap < 2 or len(points) <= cap:
        return points
    last = len(points) - 1
    return [points[round(index * last / (cap - 1))] for index in range(cap)]


#: Mirrors ``CadexDynamics.MAXIMUM_POLICY_BYTES``. Checked here so a run that
#: would produce a file the engine refuses fails at the end of training
#: rather than at the end of the trip home.
MAXIMUM_POLICY_BYTES = 4 * 1024 * 1024

#: Mirrors ``CadexDynamics.MINIMUM_POLICY_WITNESS_SAMPLES`` /
#: ``MAXIMUM_POLICY_WITNESS_SAMPLES``.
WITNESS_SAMPLES = 32

#: Mirrors ``CadexDynamics.POLICY_WITNESS_TOLERANCE``.
#:
#: Checked *here*, against this file's own float64 forward pass, before the
#: container is written. The engine applies the same number hours later and
#: on another machine, and a run that fails it has to be thrown away -- so
#: the cost of not checking is the whole run. Measured: a 2000-iteration
#: legs run came home at 1.43e-4 and was refused after 3 h 49 m of GPU time
#: that a millisecond of arithmetic here would have condemned at minute one.
POLICY_WITNESS_TOLERANCE = 1.0e-4


# ---------------------------------------------------------------------------
# The expression evaluator, built from scratch and checked against the bundle.
# ---------------------------------------------------------------------------


def globals_for(jnp: Any) -> dict[str, Any]:
    """Everything a reward or termination expression may call, in ``jax.numpy``.

    Written out rather than derived, so that this file's whitelist is a
    thing a reader can compare against ``CadexDynamics._REWARD_GLOBALS`` by
    eye.

    ``asin`` and ``arcsin`` are both here and both are ``jnp.arcsin``: the
    engine offers both spellings, so a task written against one must not
    fail here.
    """

    return {
        "__builtins__": {},
        "pi": math.pi,
        "abs": jnp.abs,
        "sin": jnp.sin,
        "cos": jnp.cos,
        "asin": jnp.arcsin,
        "arcsin": jnp.arcsin,
        "arctan": jnp.arctan,
        "exp": jnp.exp,
        "sqrt": jnp.sqrt,
        "tanh": jnp.tanh,
    }


def function_names(table: dict[str, Any]) -> list[str]:
    """The sorted callables this trainer offers an expression."""

    return sorted(
        name
        for name, value in table.items()
        if callable(value) and not name.startswith("__")
    )


def compile_expression(formula: str, names: Sequence[str], table: dict[str, Any]) -> Any:
    """One expression, checked against the channels and the whitelist."""

    allowed = set(names) | {name for name in table if not name.startswith("__")}
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


# ---------------------------------------------------------------------------
# The container. A second implementation of CadexDynamics.encode_policy,
# byte-for-byte, because this file may not import it.
# ---------------------------------------------------------------------------


def encode_policy(header: dict[str, Any], weights: Sequence[float]) -> bytes:
    """``CXPOLICY1\\n | <u64 LE header length> | <canonical JSON> | <f32 LE>``.

    Not ``np.savez``. The plan that scoped M7 expected a zip container to
    stamp an mtime and so not be byte-deterministic; measured, it *is*
    deterministic, so that argument does not hold. What decides it is that
    the engine reads this file inside a sandbox with no numpy import in
    ``CadexDynamics`` at all -- a length-prefixed header and a flat float32
    blob need neither a zip parser nor an ``allow_pickle`` flag that has to
    stay false.
    """

    import struct

    payload = json.dumps(
        header,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("ascii")
    values = [float(value) for value in weights]
    return b"".join(
        (
            POLICY_MAGIC,
            len(payload).to_bytes(8, "little"),
            payload,
            struct.pack(f"<{len(values)}f", *values),
        )
    )


def decode_policy(blob: bytes, *, context: str = "this policy") -> dict[str, Any]:
    """The inverse of :func:`encode_policy`: header, and the flat float32 blob.

    **A third implementation of the same eight lines**, and worth being
    uncomfortable about. ``CadexDynamics.decode_policy`` is the engine's, and
    this file may not import it -- ``test_dynamics_policy_trainer`` asserts
    that ``CadexDynamics`` appears only as a deferred, caught import, and
    that is the discipline that keeps the trainer a thing you copy to a box.
    So the container is written twice and now read twice, and the only
    honest mitigation is the agreement test beside the two encoder-agreement
    tests: ``test_the_trainers_decoder_agrees_with_the_engines``.

    ``struct`` is imported here rather than at module scope for the same
    reason :func:`encode_policy` does it: the guardrail allows it deferred
    and refuses it at column zero.
    """

    import struct

    if not blob.startswith(POLICY_MAGIC):
        raise SystemExit(
            f"{context} is not a .cxpolicy container: it does not begin with "
            f"{POLICY_MAGIC!r}."
        )
    start = len(POLICY_MAGIC)
    if len(blob) < start + 8:
        raise SystemExit(f"{context} is truncated: no header length.")
    length = int.from_bytes(blob[start:start + 8], "little")
    head = start + 8
    if len(blob) < head + length:
        raise SystemExit(
            f"{context} is truncated: header claims {length} bytes and "
            f"{len(blob) - head} remain."
        )
    try:
        header = json.loads(blob[head:head + length].decode("ascii"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise SystemExit(f"{context} has an unreadable header: {exc}") from exc
    if not isinstance(header, dict):
        raise SystemExit(f"{context} has a header that is not an object.")
    rest = blob[head + length:]
    if len(rest) % 4:
        raise SystemExit(
            f"{context} has a weight blob of {len(rest)} bytes, which is not "
            "a whole number of float32."
        )
    count = len(rest) // 4
    weights = list(struct.unpack(f"<{count}f", rest))
    return {"header": header, "weights": weights}


def unflatten_parameters(np: Any, weights: Sequence[float], shapes):
    """The blob back into layers, in the layout :func:`flat_parameters` wrote.

    Per layer, in order: the weight matrix ``(inputs, outputs)`` row-major,
    then the bias. The same unpack loop exists in ``rollout``'s replay and in
    the engine; this is the one the trainer warm-starts from.
    """

    expected = sum(inputs * outputs + outputs for inputs, outputs in shapes)
    if len(weights) != expected:
        raise SystemExit(
            f"the policy's weight blob holds {len(weights)} floats and this "
            f"network needs {expected}."
        )
    flat = np.asarray(weights, dtype=np.float32)
    parameters = []
    offset = 0
    for inputs, outputs in shapes:
        size = inputs * outputs
        weight = flat[offset:offset + size].reshape((inputs, outputs))
        offset += size
        bias = flat[offset:offset + outputs]
        offset += outputs
        parameters.append((weight, bias))
    return parameters


#: ADR-161: the top-level bundle keys a CURRICULUM may move.
#:
#: :func:`check_policy_fits` compares the bundle's WHOLE-FILE digest, which is
#: the right default and the wrong floor. It makes a curriculum impossible:
#: training a walker against a harder shove band is the ordinary way to teach
#: a recovery step, and this trainer could reach that band only from a fresh
#: network. cdx-rl's experiment 022 spent 10.63 GPU-hours establishing what
#: that costs -- a band whose median shove demands a step, learned COLD, is a
#: wall and not a curriculum, and the run finished BELOW the incumbent's own
#: zero-shot score on the same bundle.
#:
#: What may move is bounded by one question: does the change alter what the
#: network READS or what it EMITS?
#:
#: * ``disturbance`` does not. There is no disturbance channel among the
#:   observations -- a shove reaches the policy only through the state it
#:   produces, which is the same 39 numbers either way.
#: * ``reward`` does not. It changes the gradient, which is the point.
#: * ``episode`` does not, for the horizon, and the engine says so in its own
#:   words (ADR-136): "the policy cannot see it, because an observation is
#:   sensor channels and carries no clock."
#: * ``randomisation``, ``reset_variation`` and ``termination`` do not: they
#:   move the distribution of states, not the vector describing one.
#: * ``success`` does not (ADR-597). It is the bar an evaluation judges the
#:   policy against; the trainer reads it only to refuse a ``--seed`` that is
#:   an evaluation seed, and that check runs on the child's spec. A tightened
#:   bar on the same task is the ordinary next step after a pass.
#:
#: ``observations``, ``actions``, ``model``, ``functions`` and ``schema`` are
#: absent BECAUSE they do exactly that -- and every one of them keeps being
#: checked independently below. This flag skips the whole-file digest and
#: nothing else.
CURRICULUM_TASK_KEYS = frozenset({
    "disturbance",
    "episode",
    "label",
    "randomisation",
    "reset_variation",
    "reward",
    "success",
    "termination",
    # ADR-755: the canonical body names what the network reads and drives;
    # it moves neither.
    "body",
})

#: The ``episode`` sub-keys a curriculum may move.
#:
#: The horizon is invisible to the policy (ADR-136). The CADENCE is not: it
#: sets what one action *means* in time, so a policy warmed across it was
#: trained by a different controller than the one now running. cdx-rl's
#: experiment 016 measured that directly -- the same policy dropped zero-shot
#: from 50 Hz into 25 Hz survives 3 of 12 where it survived 7 of 12 at its own
#: rate. That is a distribution shift big enough to be its own experiment, so
#: it does not get to ride along inside somebody's band change.
CURRICULUM_EPISODE_KEYS = frozenset({"episode_seconds", "max_steps"})

#: ADR-791: the keys of a ``goal`` entry a curriculum may move -- where the
#: goal is drawn from, never its channels, kind, unit, period or ramp. The
#: actor reads the drawn value as it is, so 5000 mm/s means the same thing
#: whichever range it was drawn from.
CURRICULUM_GOAL_KEYS = frozenset({"low", "high", "nominal", "sequence"})

#: ADR-736: the keys a step onto (or between) courses moves. They may move
#: only together with the conditions :func:`check_curriculum_change` holds:
#: the robot is the same (:func:`robot_xml`), and what the actor reads is
#: unchanged (checked in :func:`check_policy_fits`). ``observations`` may
#: gain or lose only privileged rows -- a privileged height scan -- which the
#: critic reads and the actor does not (a ``role: policy`` scan, ADR-748,
#: moves the actor's inputs and is refused there); the critic is not carried by a warm
#: start, so a wider critic input costs nothing.
CURRICULUM_COURSE_KEYS = frozenset({"model", "terrain", "scans", "observations"})

#: The world-body geoms and assets an environment adds (ADR-714, ADR-716):
#: everything named under ``environment/``.
ENVIRONMENT_PREFIX = "environment/"


def robot_xml(xml: bytes) -> bytes:
    """An exported model less its environment, canonically serialised.

    Two exports whose robots are the same body for body, joint for joint and
    actuator for actuator, and differ only in the ground the world body
    carries (a plane, a heightfield, a box course), give equal bytes here.
    A policy trained on one is the same controller on the other."""

    root = ElementTree.fromstring(xml)
    for parent in root.iter():
        for child in list(parent):
            if (child.tag in ("geom", "hfield")
                    and str(child.get("name") or "").startswith(ENVIRONMENT_PREFIX)):
                parent.remove(child)
    return ElementTree.tostring(root, encoding="utf-8")


def _bundle_model_bytes(bundle_path: Path, task: dict[str, Any]) -> bytes | None:
    """The model a bundle references, found as :func:`load_bundle` finds it."""

    relative = Path(str((task.get("model") or {}).get("path") or ""))
    for candidate in (bundle_path.parent.parent / relative, bundle_path.parent / relative.name):
        if candidate.is_file():
            return candidate.read_bytes()
    return None


def check_curriculum_change(
    header_task: dict[str, Any],
    bundle: dict[str, Any],
    options: argparse.Namespace,
    reason: str,
) -> list[str]:
    """ADR-161: which keys moved, having refused the ones that may not.

    Returns the sorted list of differing top-level keys, for the run record.

    The parent bundle is supplied rather than reconstructed, because a
    ``.cxpolicy`` header carries its task's *digest and label* and not its
    content -- and it is **tied to that digest here**, so the file handed in
    cannot quietly be a different bundle that happens to parse.
    """

    def refuse(message: str) -> None:
        raise SystemExit(
            f"--init-from-task-change: {message}\n"
            "A curriculum step may change the task the network is being "
            "trained AGAINST. It may not change what the network reads or "
            "emits -- those weights would mean something else."
        )

    supplied = str(getattr(options, "init_from_parent_task", "") or "").strip()
    if not supplied:
        refuse(
            "--init-from-parent-task is required beside it. The policy's "
            "header records its task's digest, not its content, so the only "
            "way to say WHICH keys moved is to be handed the bundle it "
            "trained on."
        )
    parent_path = Path(supplied).expanduser()
    try:
        parent_bytes = parent_path.read_bytes()
    except OSError as exc:
        refuse(f"cannot read --init-from-parent-task {parent_path}: {exc}")
    parent_digest = hashlib.sha256(parent_bytes).hexdigest()
    if parent_digest != str(header_task.get("sha256")):
        refuse(
            f"the bundle at {parent_path} is not the one this policy trained "
            f"on.\n"
            f"  policy's task: {header_task.get('sha256')}\n"
            f"  file supplied: {parent_digest}"
        )
    try:
        parent = json.loads(parent_bytes.decode("utf-8"))
    except ValueError as exc:
        refuse(f"--init-from-parent-task {parent_path} is not JSON: {exc}")

    child = bundle["task"]
    changed = sorted(
        key for key in set(parent) | set(child)
        if parent.get(key) != child.get(key)
    )
    if not changed:
        # The digests differ and no key does, so the difference is whitespace
        # or key order. That is a REAL difference to every digest in the
        # calling repository and the flag is being used to paper over it.
        refuse(
            "the two bundles differ as bytes and agree on every top-level "
            "key, so the difference is formatting. Re-emit the child through "
            "the same serialiser rather than warm-starting across it."
        )
    if "tracking" in changed:
        # ADR-752: a step onto (or off) a speed cadence moves only how fast
        # the clock turns; the actor reads the same two channels of it.
        def clip(task: dict[str, Any]) -> dict[str, Any]:
            return {key: value for key, value in (task.get("tracking") or {}).items()
                    if key != "cadence"}

        if clip(parent) == clip(child):
            changed = [key for key in changed if key != "tracking"] + ["tracking.cadence"]
            changed.sort()
    if "goal" in changed:
        # ADR-791: a step that moves only where a goal is drawn from. The
        # actor reads the drawn value itself, through the running normaliser
        # a warm start carries and keeps updating, so a wider range is new
        # values on an input it already has, as a harder shove band is new
        # states.
        def bounds(task: dict[str, Any]) -> list[dict[str, Any]]:
            return [{key: value for key, value in entry.items()
                     if key not in CURRICULUM_GOAL_KEYS}
                    for entry in task.get("goal") or ()]

        if bounds(parent) == bounds(child):
            changed = [key for key in changed if key != "goal"] + ["goal.range"]
            changed.sort()
    disallowed = sorted(set(changed) - CURRICULUM_TASK_KEYS - CURRICULUM_COURSE_KEYS
                        - {"tracking.cadence", "goal.range"})
    if disallowed:
        refuse(
            f"these keys moved and may not: {disallowed}. A curriculum may "
            f"move {sorted(CURRICULUM_TASK_KEYS)}."
        )
    if "model" in changed:
        # ADR-736: a step onto another course. The robot must be the same.
        parent_xml = _bundle_model_bytes(parent_path.resolve(), parent)
        if parent_xml is None:
            refuse(
                f"the model {(parent.get('model') or {}).get('path')!r} the parent bundle "
                f"references is not beside {parent_path}, so there is no way to show the "
                "robot is the same one. Keep the parent's model beside its bundle."
            )
        if hashlib.sha256(parent_xml).hexdigest() != str((parent.get("model") or {}).get("sha256")):
            refuse(f"the model beside {parent_path} is not the one its bundle recorded.")
        if robot_xml(parent_xml) != robot_xml(bundle["model_xml"]):
            refuse(
                "the model moved, and not only its ground: less everything named "
                f"{ENVIRONMENT_PREFIX!r}, the two exports still differ. A warm start may "
                "move the robot onto another course, never change the robot."
            )
    if "observations" in changed:
        def rows(task: dict[str, Any], privileged: bool) -> list[Any]:
            return [row for row in task.get("observations") or ()
                    if (str(row.get("role") or "policy") == "privileged") == privileged]

        if rows(parent, False) != rows(child, False):
            refuse(
                "the observations the policy reads moved. Only privileged rows (a "
                "height scan, ADR-715) may come or go across a curriculum step: the "
                "critic reads them and the actor never does."
            )
    if "episode" in changed:
        parent_episode = dict(parent.get("episode") or {})
        child_episode = dict(child.get("episode") or {})
        moved = sorted(
            key for key in set(parent_episode) | set(child_episode)
            if parent_episode.get(key) != child_episode.get(key)
        )
        cadence = sorted(set(moved) - CURRICULUM_EPISODE_KEYS)
        if cadence:
            refuse(
                f"these episode keys moved and may not: {cadence}. Only the "
                f"HORIZON is invisible to the policy (ADR-136); the control "
                f"and solver cadence is what one action means in time, and "
                f"warming across it trains one controller and scores another."
            )
    return changed


#: ``--initial-std``'s value when it is not given and nothing is carried.
DEFAULT_INITIAL_STD = 0.3


def starting_log_std(
    options: argparse.Namespace,
    header: dict[str, Any] | None,
    action_count: int,
) -> tuple[list[float], str]:
    """The exploration width a run starts at, and where it came from (ADR-471).

    ``log_std`` is a *trained* parameter (ADR-103) and the container carries
    it, per action, as the header's ``exploration.log_std``. A warm start that
    restored the actor and reset σ to ``--initial-std`` was handing a trained
    mean a fresh exploration width -- ot11's r21b warmed r19's actor, whose σ
    had narrowed from 0.30 to 0.177, back at 0.30 and lost r19's gait. So,
    in order:

    * ``--initial-std`` given explicitly wins, warm or cold: ``"flag"``;
    * otherwise a warm start carries the source's width: ``"init_from"``;
    * otherwise the default: ``"default"``.

    A source with no usable ``exploration`` block (written before ADR-103, or
    the wrong length, or not finite) is refused rather than silently given
    the default: the run was asked to continue a policy, and it would not be.
    The critic is not carried because the container does not hold it.
    """

    explicit = getattr(options, "initial_std", None)
    if explicit is not None:
        std = float(explicit)
        if not (math.isfinite(std) and std > 0.0):
            raise SystemExit("--initial-std must be a finite positive number.")
        return [math.log(std)] * int(action_count), "flag"
    if header is None:
        return [math.log(DEFAULT_INITIAL_STD)] * int(action_count), "default"
    exploration = header.get("exploration") or {}
    carried = exploration.get("log_std")
    if (not isinstance(carried, list) or len(carried) != int(action_count)
            or exploration.get("space", "pre_activation") != "pre_activation"):
        raise SystemExit(
            "--init-from: the policy carries no per-action exploration width "
            f"for {int(action_count)} actions (header 'exploration.log_std'), "
            "so it cannot be continued at the width it trained to. Pass "
            "--initial-std to choose one explicitly."
        )
    values = [float(v) for v in carried]
    if not all(math.isfinite(v) for v in values):
        raise SystemExit("--init-from: the policy's exploration.log_std is "
                         "not finite. Pass --initial-std to choose one.")
    return values, "init_from"


def source_normaliser_count(header: dict[str, Any]) -> int:
    """How many observations a policy's normaliser statistics rest on.

    A policy written since ADR-753 records it. An older one is credited
    with the samples its own run collected, ``iterations x envs x unroll``:
    a lower bound, since what its own warm start carried is not recorded.
    """

    recorded = (header.get("normaliser") or {}).get("count")
    if recorded is not None:
        return max(int(recorded), 1)
    training = header.get("training") or {}
    hyper = training.get("hyperparameters") or {}
    try:
        samples = (int(training.get("iterations") or hyper.get("iterations") or 0)
                   * int(hyper.get("envs") or 0) * int(hyper.get("unroll") or 0))
    except (TypeError, ValueError):
        samples = 0
    return max(samples, 1)


# ---------------------------------------------------------------------------
# The canonical body (ADR-755): a warm start across robots of one family.
# ---------------------------------------------------------------------------

#: The families a bundle's ``body`` block may name, and its version.
BODY_FAMILIES = {"quadruped": ("fl", "fr", "hl", "hr"), "biped": ("l", "r")}
BODY_VERSION = 1


def body_layout(task: dict[str, Any]) -> dict[str, Any] | None:
    """What a policy on ``task`` reads and drives, by canonical name.

    ``inputs`` has one ``[name, gain, centre]`` per actor channel, in
    order, so the canonical value of channel ``x`` is ``gain * (x -
    centre)``: a joint slot's angle and rate in radians from the bundle's
    ``sign``, ``offset`` and the channel's scale; the IMU's quaternion and
    rates; a goal, clock or command channel by its own name; a height-scan
    channel by its index on a grid named by its offsets; any other channel
    by its kind, its target and its place in the row. ``outputs`` has one
    ``[name, sign]`` per action: ``<leg>.<slot>`` for a mapped joint,
    ``joint.<name>`` otherwise. A name absent on one side is an input that
    side lacks. ``None`` when the bundle maps no body. The engine resolves
    the block (``CadexDynamics._body_records``); this only reads it.
    """

    body = task.get("body")
    if not body:
        return None
    rows = {str(channel): (row, index)
            for row in task["observations"]
            if str(row.get("role") or "policy") == "policy"
            for index, channel in enumerate(row["channels"])}
    named: dict[str, tuple[str, float, float]] = {}
    sign_of: dict[int, tuple[str, int]] = {}
    for leg, slots in sorted((body.get("legs") or {}).items()):
        for slot, record in sorted(slots.items()):
            q_scale = float(rows[str(record["q"])][0]["scale"])
            dq_scale = float(rows[str(record["dq"])][0]["scale"])
            sign = 1.0 if int(record["sign"]) > 0 else -1.0
            named[str(record["q"])] = (f"{leg}.{slot}.q", sign / q_scale,
                                       float(record["offset"]))
            named[str(record["dq"])] = (f"{leg}.{slot}.dq", sign / dq_scale, 0.0)
            sign_of[int(record["action"])] = (f"{leg}.{slot}", int(sign))
    imu = body.get("body") or {}
    for part, axes in (("quat", "wxyz"), ("gyro", "xyz")):
        for axis, channel in zip(axes, imu.get(part) or ()):
            named[str(channel)] = (f"body.{part}.{axis}",
                                   1.0 / float(rows[str(channel)][0]["scale"]), 0.0)
    inputs: list[list[Any]] = []
    for channel in actor_channels(task):
        if channel in named:
            name, gain, centre = named[channel]
        elif channel in rows:
            row, index = rows[channel]
            name, gain, centre = (f"obs.{row['kind']}.{row['target']}.{index}",
                                  1.0 / float(row["scale"]), 0.0)
        elif channel in goal_channels(task):
            name, gain, centre = f"goal.{channel}", 1.0, 0.0
        elif channel in tracking_channels(task, policy_only=True):
            name, gain, centre = f"clock.{channel}", 1.0, 0.0
        elif channel in command_channels(task, policy_only=True):
            name, gain, centre = f"command.{channel}", 1.0, 0.0
        else:
            grid = name = None
            for record in task.get("scans") or ():
                if channel in record["channels"]:
                    grid = hashlib.sha256(json.dumps(
                        record["offsets_mm"]).encode("ascii")).hexdigest()[:12]
                    name = f"scan.{grid}.{record['channels'].index(channel)}"
                    gain, centre = 1.0 / float(record["scale"]), 0.0
            if name is None:
                raise SystemExit(f"the canonical body cannot name channel {channel!r}.")
        inputs.append([name, gain, centre])
    outputs = [list(sign_of.get(index, (f"joint.{action['joint']}", 1)))
               for index, action in enumerate(task["actions"])]
    return {"family": str(body["family"]), "version": int(body.get("version", 0)),
            "legs": sorted(body.get("legs") or {}),
            "inputs": inputs, "outputs": outputs,
            **({"morph": body["morph"]} if body.get("morph") else {})}


def check_base_fits(header: dict[str, Any], bundle: dict[str, Any],
                    options: argparse.Namespace) -> dict[str, Any]:
    """``--init-from-base``: the third path of :func:`check_policy_fits`.

    The model and task digests are not compared: another robot is expected.
    Both sides must map a body of one family and version, the network must
    have the hidden layers ``--hidden`` asks for, every leg the target maps
    must share at least one joint slot with the source, and the critic must
    warm up (ADR-740), because it starts on another robot's returns."""

    def refuse(message: str) -> None:
        raise SystemExit(f"--init-from-base: {message}\nA warm start across robots "
                         "matches them on the family's canonical body (ADR-755).")

    source = header.get("body")
    target = body_layout(bundle["task"])
    if not source:
        refuse("the policy records no body; it was trained on a task without one.")
    if target is None:
        refuse("this bundle maps no body (api.task(body=...)).")
    if (source.get("family"), source.get("version")) != (target["family"], target["version"]):
        refuse(f"the policy's body is {source.get('family')} v{source.get('version')} "
               f"and this bundle's is {target['family']} v{target['version']}.")
    if str(getattr(options, "init_from_task_change", "") or "").strip():
        refuse("it is not a curriculum step; drop --init-from-task-change.")
    if int(getattr(options, "critic_warmup", 0) or 0) <= 0:
        refuse("the critic starts on another robot's returns; give --critic-warmup N.")
    layers = [list(shape) for shape in (header.get("network") or {}).get("layers") or ()]
    hidden = [int(width) for width in options.hidden]
    if [shape[1] for shape in layers[:-1]] != hidden:
        refuse(f"the policy's hidden layers are {[shape[1] for shape in layers[:-1]]} "
               f"and --hidden asks for {hidden}.")
    source_slots = {str(name) for name, _sign in source["outputs"]}
    for leg in target["legs"]:
        if not any(str(name) in source_slots and str(name).startswith(f"{leg}.")
                   for name, _sign in target["outputs"]):
            refuse(f"leg {leg!r} shares no joint slot with the policy.")
    return target


def remap_from_base(np: Any, header: dict[str, Any], weights: Sequence[float],
                    target: dict[str, Any]) -> dict[str, Any]:
    """A policy's actor and statistics in another robot's layout (ADR-755).

    Inputs match by canonical name. A matched input copies its first-layer
    row, negated where the two gains' signs differ, and its statistics are
    mapped through the affine map between the two channels, so the source
    network sees the value it would have seen. A source input the target
    lacks is folded into the first layer's bias at its rest value (a joint
    slot at its reset angle, a goal, clock or command at 0, anything else at
    its mean) and dropped. A target input the source lacks gets a zero row,
    mean 0 and std 1. Outputs match by slot: a matched action copies its
    last-layer column and bias, negated where the signs differ; a target
    action the source lacks is a zero column and bias, its box centre; its
    exploration width is the default's. Hidden layers are copied.
    ``carried`` marks, per target input, whether its statistics are the
    source's (a matched input) or fresh (mean 0, std 1), so a warm start
    keeps the source's sample count on the former only (ADR-760)."""

    source = header["body"]
    network = header["network"]
    shapes = [tuple(int(v) for v in shape) for shape in network["layers"]]
    layers = [(np.asarray(w, dtype=np.float64), np.asarray(b, dtype=np.float64))
              for w, b in unflatten_parameters(np, weights, shapes)]
    stats = header.get("normaliser") or {}
    mean_s = np.asarray(stats.get("mean") or [0.0] * shapes[0][0], dtype=np.float64)
    std_s = np.asarray(stats.get("std") or [1.0] * shapes[0][0], dtype=np.float64)
    log_std_s = list((header.get("exploration") or {}).get("log_std") or ())

    first_w, first_b = layers[0]
    width = first_w.shape[1]
    s_index = {str(row[0]): i for i, row in enumerate(source["inputs"])}
    t_index = {str(row[0]): i for i, row in enumerate(target["inputs"])}
    new_w = np.zeros((len(target["inputs"]), width))
    new_b = first_b.copy()
    mean_t = np.zeros(len(target["inputs"]))
    std_t = np.ones(len(target["inputs"]))
    counts = {"inputs_copied": 0, "inputs_folded": 0, "inputs_zero": 0,
              "outputs_copied": 0, "outputs_dropped": 0, "outputs_zero": 0}
    for j, (name, gain_t, centre_t) in enumerate(target["inputs"]):
        i = s_index.get(str(name))
        if i is None:
            counts["inputs_zero"] += 1
            continue
        _name, gain_s, centre_s = source["inputs"][i]
        # x_s = a * x_t + b carries the same canonical value.
        a = float(gain_t) / float(gain_s)
        b = float(centre_s) - a * float(centre_t)
        new_w[j] = math.copysign(1.0, a) * first_w[i]
        mean_t[j] = (mean_s[i] - b) / a
        std_t[j] = std_s[i] / abs(a)
        counts["inputs_copied"] += 1
    # ADR-759: a family base reads each variant's morph constants; on the
    # target they are constants too, so they fold at the target's own values.
    target_morph = dict(morph_inputs(target.get("morph")))
    for i, (name, _gain, centre) in enumerate(source["inputs"]):
        if str(name) in t_index:
            continue
        rest = (float(centre) if str(name).split(".")[0] in BODY_FAMILIES[source["family"]]
                else 0.0 if str(name).split(".")[0] in ("goal", "clock", "command")
                else target_morph[str(name)] if str(name) in target_morph
                else float(mean_s[i]))
        new_b = new_b + ((rest - mean_s[i]) / std_s[i]) * first_w[i]
        counts["inputs_folded"] += 1

    last_w, last_b = layers[-1]
    s_out = {str(name): (i, int(sign)) for i, (name, sign) in enumerate(source["outputs"])}
    out_w = np.zeros((last_w.shape[0], len(target["outputs"])))
    out_b = np.zeros(len(target["outputs"]))
    log_std = [math.log(DEFAULT_INITIAL_STD)] * len(target["outputs"])
    for j, (name, sign_t) in enumerate(target["outputs"]):
        if str(name) not in s_out:
            counts["outputs_zero"] += 1
            continue
        i, sign_s = s_out[str(name)]
        flip = float(sign_s * int(sign_t))
        out_w[:, j] = flip * last_w[:, i]
        out_b[j] = flip * last_b[i]
        if i < len(log_std_s):
            log_std[j] = float(log_std_s[i])
        counts["outputs_copied"] += 1
    counts["outputs_dropped"] = len(source["outputs"]) - counts["outputs_copied"]
    if len(layers) == 1:
        raise SystemExit("--init-from-base: a network with no hidden layer cannot be remapped.")
    mapped = [(new_w, new_b)] + layers[1:-1] + [(out_w, out_b)]
    return {"layers": [(np.asarray(w, dtype=np.float32), np.asarray(b, dtype=np.float32))
                       for w, b in mapped],
            "mean": [float(v) for v in mean_t], "std": [float(v) for v in std_t],
            "log_std": log_std, "counts": counts,
            "carried": [str(name) in s_index for name, _gain, _centre in target["inputs"]]}


# ---------------------------------------------------------------------------
# A family (ADR-759): one run over built variants of one robot (ADR-758).
# ---------------------------------------------------------------------------

#: The model sizes every variant of a family must share, so their batched
#: MJX data concatenate environment by environment.
FAMILY_SIZES = ("nq", "nv", "nu", "nbody", "njnt", "ngeom", "nsite", "nsensordata",
                "nkey", "nmocap", "neq")


def morph_inputs(morph: dict[str, Any] | None) -> list[tuple[str, float]]:
    """A body's ``morph`` block as named constants, in sorted order:
    ``morph.<leg>.<key>`` for a leg's entry, ``morph.<key>`` for the body's."""

    rows: list[tuple[str, float]] = []
    for key, value in sorted((morph or {}).items()):
        if isinstance(value, dict):
            rows += [(f"morph.{key}.{inner}", float(number))
                     for inner, number in sorted(value.items())]
        else:
            rows.append((f"morph.{key}", float(value)))
    return rows


def family_morph_names(bundle: dict[str, Any]) -> list[str]:
    """The morph inputs a ``--family`` run's actor reads after its channels;
    empty for an ordinary run."""

    if not bundle.get("family"):
        return []
    return [name for name, _value in morph_inputs(bundle["task"]["body"]["morph"])]


def family_body(bundle: dict[str, Any]) -> dict[str, Any]:
    """:func:`body_layout`, with a family run's morph inputs after the
    channels' at gain 1 and centre 0."""

    layout = body_layout(bundle["task"])
    if bundle.get("family"):
        layout["inputs"] = layout["inputs"] + [[name, 1.0, 0.0]
                                               for name in family_morph_names(bundle)]
    return layout


def check_family(bundles: Sequence[dict[str, Any]]) -> None:
    """``--family``: refuse variants that are not one robot's.

    Each must map a body of one family with the same morph names, read and
    drive the same channels and joints, and score the same number of reward
    terms over the same episode. The model sizes are compared where the
    models are compiled (:func:`family_environment`)."""

    def refuse(message: str) -> None:
        raise SystemExit(f"--family: {message}\nA family is built variants of one "
                         "robot (ADR-758, ADR-759).")

    if len(bundles) < 2:
        refuse("name at least one variant beside the bundle.")

    def facts(task: dict[str, Any]) -> dict[str, Any]:
        body = task.get("body") or {}
        return {
            "the observation channels": channels(task),
            "the actor channels": actor_channels(task),
            "the actions' joints": [str(a["joint"]) for a in task["actions"]],
            "the reward term count": len(task["reward"]),
            "the episode": [int(task["episode"]["max_steps"]),
                            int(task["episode"]["solver_steps_per_action"])],
            "the body": [body.get("family"), body.get("version")],
            "the morph names": [name for name, _ in morph_inputs(body.get("morph"))],
        }

    first = facts(bundles[0]["task"])
    if not first["the morph names"]:
        refuse("the bundle maps no body with a morph block (api.task(body=...)).")
    seen = {bundles[0]["task_sha256"]}
    for index, bundle in enumerate(bundles[1:], start=1):
        if bundle["task_sha256"] in seen:
            refuse(f"variant {index} is a bundle already in the family.")
        seen.add(bundle["task_sha256"])
        for what, value in facts(bundle["task"]).items():
            if value != first[what]:
                refuse(f"variant {index}'s {what} differ from the bundle's: "
                       f"{value} vs {first[what]}.")


def family_environment(
    bundles: Sequence[dict[str, Any]],
    options: argparse.Namespace,
    *,
    count: int,
    seed: int,
    jax: Any,
    jnp: Any,
    np: Any,
    mujoco: Any,
    mjx: Any,
) -> Any:
    """``count`` environments over the family, as one batched environment.

    The environments are split in contiguous blocks, as evenly as they go,
    and block ``k`` is variant ``k``'s own :func:`build_environment`: its
    model, randomisation, reward, terminations, tracking clip, reset, pushes
    and action box, untouched. The block's draws are seeded from ``seed``
    plus the environments before it, so environment ``e`` draws
    ``random.Random(seed + e)`` whichever variant it is. Every observation
    gains the variant's morph constants at its end, the actor's and the
    critic's alike. A step splits the state by block, steps each variant and
    joins them; the one leaf with no environment axis, the PRNG key, is
    stacked per block.
    """

    variants = len(bundles)
    if int(count) < variants:
        raise SystemExit(f"--family: {count} environments cannot hold "
                         f"{variants} variants.")
    reference = None
    for index, bundle in enumerate(bundles):
        host = mujoco.MjModel.from_xml_string(bundle["model_xml"].decode("utf-8"))
        sizes = {name: int(getattr(host, name)) for name in FAMILY_SIZES}
        if reference is None:
            reference = sizes
        elif sizes != reference:
            raise SystemExit(
                f"--family: variant {index}'s model is another topology: "
                + ", ".join(f"{name} {sizes[name]} vs {reference[name]}"
                            for name in FAMILY_SIZES if sizes[name] != reference[name]))
    counts = [int(count) // variants + (1 if k < int(count) % variants else 0)
              for k in range(variants)]
    bounds = [0]
    for size in counts:
        bounds.append(bounds[-1] + size)
    subs = [build_environment(bundle, options, count=size, seed=int(seed) + start,
                              jax=jax, jnp=jnp, np=np, mujoco=mujoco, mjx=mjx)
            for bundle, size, start in zip(bundles, counts, bounds)]
    morphs = [jnp.asarray([value for _, value in
                           morph_inputs(bundle["task"]["body"]["morph"])],
                          dtype=jnp.float32)
              for bundle in bundles]
    morph_names = [name for name, _ in morph_inputs(bundles[0]["task"]["body"]["morph"])]
    first = subs[0]

    def dressed(state, k):
        extra = jnp.broadcast_to(morphs[k], (counts[k], morphs[k].shape[0]))
        return state.replace(obs={name: jnp.concatenate([value, extra], axis=-1)
                                  for name, value in state.obs.items()})

    def joined(states):
        keys = jnp.stack([state.info["key"] for state in states])
        bare = [state.replace(info={k: v for k, v in state.info.items() if k != "key"})
                for state in states]
        whole = jax.tree.map(lambda *parts: jnp.concatenate(parts, axis=0), *bare)
        return whole.replace(info={**whole.info, "key": keys})

    def part(state, k):
        start, stop = bounds[k], bounds[k + 1]
        bare = state.replace(info={key: value for key, value in state.info.items()
                                   if key != "key"})
        piece = jax.tree.map(lambda leaf: leaf[start:stop], bare)
        return piece.replace(info={**piece.info, "key": state.info["key"][k]})

    def reset(key):
        keys = jax.random.split(key, variants)
        return joined([dressed(sub.reset(keys[k]), k) for k, sub in enumerate(subs)])

    def step(state, action):
        return joined([
            dressed(sub.step(part(state, k), action[bounds[k]:bounds[k + 1]]), k)
            for k, sub in enumerate(subs)])

    class Environment:
        def __init__(self):
            self.reset = reset
            self.step = step
            self.count = int(count)
            self.counts = counts
            self.names = list(first.names) + morph_names
            self.actor_names = list(first.actor_names) + morph_names
            self.actor_idx = np.concatenate([
                np.asarray(first.actor_idx, dtype=np.int32),
                np.arange(len(first.names), len(first.names) + len(morph_names),
                          dtype=np.int32)])
            self.actions = first.actions
            # The header's box is the bundle's; each block plays its own.
            self.output_scale = first.output_scale
            self.output_bias = first.output_bias
            self.horizon = first.horizon
            self.action_size = first.action_size
            self.observation_size = {"state": (len(self.actor_names),),
                                     "privileged_state": (len(self.names),)}

    return Environment()


def check_policy_fits(
    header: dict[str, Any],
    bundle: dict[str, Any],
    options: argparse.Namespace,
) -> list[str] | None:
    """``--init-from``'s half of ``CadexDynamics.verify_policy``.

    A warm start is only meaningful when the network being warmed is the same
    network, against the same task, reading the same channels in the same
    order. These are the engine's own six checks, minus the witness -- the
    trainer is about to *train* these weights, so replaying them bit-for-bit
    proves nothing it needs.

    Every one of these is a silent-wrong if it is skipped. A policy from a
    task with two reward terms swapped has the right shape and the wrong
    gradient; one whose observation order differs by two channels trains
    perfectly well towards nonsense.
    """

    def refuse(what: str, expected: Any, found: Any) -> None:
        raise SystemExit(
            f"--init-from: {what} does not match this bundle.\n"
            f"  bundle: {expected}\n"
            f"  policy: {found}\n"
            "A warm start has to be the same network on the same task; "
            "otherwise the weights mean something else."
        )

    if str(getattr(options, "init_from_base", "") or "").strip():
        # ADR-755: another robot of the family; check_base_fits holds it.
        if bundle.get("family"):
            raise SystemExit("--init-from-base onto a --family run: the base's morph "
                             "inputs would fold into one variant's. Warm a family "
                             "from a family policy with --init-from alone.")
        check_base_fits(header, bundle, options)
        return None
    task = header.get("task") or {}
    reason = str(getattr(options, "init_from_task_change", "") or "").strip()
    curriculum: list[str] | None = None
    if task.get("sha256") != bundle["task_sha256"]:
        if not reason:
            refuse("the task digest", bundle["task_sha256"], task.get("sha256"))
        # ADR-161. Every check below still runs, unchanged: this branch skips
        # the whole-file digest and buys nothing else.
        curriculum = check_curriculum_change(task, bundle, options, reason)
    elif reason:
        # The flag asserts a change. There isn't one, so either the wrong
        # bundle is being trained or the wrong policy is being warmed, and
        # both of those are silent-wrongs worth an exit code.
        raise SystemExit(
            "--init-from-task-change was given and the bundle is byte-"
            "identical to the one this policy trained on. The flag asserts a "
            "curriculum step; there is no step here."
        )
    model = header.get("model") or {}
    # ADR-736: a curriculum step that moved the model has shown, above, that
    # only its ground moved.
    if model.get("sha256") != bundle["model_sha256"] and "model" not in (curriculum or ()):
        refuse("the model digest", bundle["model_sha256"], model.get("sha256"))
    # ADR-759: a family run's actor reads its morph constants after them.
    wanted_channels = actor_channels(bundle["task"]) + family_morph_names(bundle)
    if list(header.get("observations") or []) != wanted_channels:
        refuse(
            "the observation channels, in order",
            wanted_channels,
            header.get("observations"),
        )
    wanted_actions = list(bundle["task"]["actions"])
    found_actions = list(header.get("actions") or [])
    if len(found_actions) != len(wanted_actions):
        refuse("the action count", len(wanted_actions), len(found_actions))
    for index, (want, got) in enumerate(zip(wanted_actions, found_actions)):
        for field in _POLICY_ACTION_FIELDS:
            if want.get(field) != got.get(field):
                refuse(
                    f"action {index}'s {field}", want.get(field), got.get(field)
                )
    network = header.get("network") or {}
    wanted_layers = [
        list(shape)
        for shape in layer_shapes(
            len(wanted_channels), len(wanted_actions), options.hidden
        )
    ]
    found_layers = [list(shape) for shape in (network.get("layers") or [])]
    if found_layers != wanted_layers:
        refuse(
            "the network shape (check --hidden)", wanted_layers, found_layers
        )
    return curriculum


# ---------------------------------------------------------------------------
# Teachers: a student distilled by command band (ADR-825).
# ---------------------------------------------------------------------------


def parse_teacher(text: str) -> tuple[float, float, str]:
    """``--teacher LOW:HIGH:POLICY``: the band of the goal, then the file."""

    parts = str(text).split(":", 2)
    try:
        low, high = float(parts[0]), float(parts[1])
        path = parts[2]
    except (IndexError, ValueError) as error:
        raise SystemExit(f"--teacher {text!r} is not LOW:HIGH:POLICY") from error
    if not path or not low < high:
        raise SystemExit(f"--teacher {text!r}: needs LOW < HIGH and a policy path")
    return low, high, path


def check_teachers(
    teachers: Sequence[dict[str, Any]],
    bundle: dict[str, Any],
    goal: str,
) -> int:
    """Every refusal before a teacher is read in training; the goal's index
    among the actor's channels.

    A teacher is a policy for the same robot reading the same channels and
    emitting the same action table -- ``check_policy_fits`` without the task
    digest, because a teacher was trained on another bundle (that is what
    makes it a teacher). Its bands may not overlap, so one step has at most
    one teacher, and they sit inside the goal's range.
    """

    if not teachers:
        return -1
    if bundle.get("family"):
        raise SystemExit("--teacher on a --family run: a teacher reads one "
                         "variant's channels, not the family's morph inputs.")
    task = bundle["task"]
    record = next((item for item in task.get("goal") or ()
                   if goal in [str(channel) for channel in item["channels"]]), None)
    if record is None or len(record["channels"]) != 1:
        raise SystemExit(f"--teacher-goal {goal!r} is not a one-channel goal of "
                         f"this bundle (goals: {goal_channels(task)})")
    wanted_channels = actor_channels(task)
    wanted_actions = list(task["actions"])
    bands = sorted((float(t["low"]), float(t["high"])) for t in teachers)
    for (_low, high), (low, _high) in zip(bands, bands[1:]):
        if low < high:
            raise SystemExit(f"--teacher bands overlap at {low:g}-{high:g}: one "
                             "step is taught by at most one teacher")
    goal_low, goal_high = float(record["low"]), float(record["high"])
    for teacher in teachers:
        name = teacher["name"]
        if teacher["low"] < goal_low or teacher["high"] > goal_high:
            raise SystemExit(f"--teacher {name}: band {teacher['low']:g}-"
                             f"{teacher['high']:g} leaves {goal}'s range "
                             f"{goal_low:g}-{goal_high:g}")
        header = teacher["header"]
        model = (header.get("model") or {}).get("sha256")
        if model != bundle["model_sha256"]:
            raise SystemExit(f"--teacher {name}: model {model} is not this "
                             f"bundle's {bundle['model_sha256']}")
        if list(header.get("observations") or []) != wanted_channels:
            raise SystemExit(f"--teacher {name}: its observation channels are "
                             "not this bundle's, in order")
        found_actions = list(header.get("actions") or [])
        if len(found_actions) != len(wanted_actions) or any(
                want.get(field) != got.get(field)
                for want, got in zip(wanted_actions, found_actions)
                for field in _POLICY_ACTION_FIELDS):
            raise SystemExit(f"--teacher {name}: its action table is not this bundle's")
    return wanted_channels.index(goal)


def load_teacher(np: Any, low: float, high: float, path: str) -> dict[str, Any]:
    """One teacher: its band, digest, header, layers and normaliser."""

    source = Path(path).expanduser()
    try:
        blob = source.read_bytes()
    except OSError as error:
        raise SystemExit(f"--teacher: cannot read {source}: {error}") from error
    decoded = decode_policy(blob, context=str(source))
    header = decoded["header"]
    network = header.get("network") or {}
    shapes = [(int(a), int(b)) for a, b in network.get("layers") or ()]
    layers = [(np.asarray(w, dtype=np.float32), np.asarray(b, dtype=np.float32))
              for w, b in unflatten_parameters(np, decoded["weights"], shapes)]
    stats = header.get("normaliser") or {}
    std = np.asarray(stats.get("std") or [1.0] * shapes[0][0], dtype=np.float32)
    return {
        "name": source.name,
        "low": float(low),
        "high": float(high),
        "sha256": hashlib.sha256(blob).hexdigest(),
        "header": header,
        "layers": layers,
        "activation": str(network.get("activation") or "tanh"),
        "mean": np.asarray(stats.get("mean") or [0.0] * shapes[0][0], dtype=np.float32),
        "std": np.where(std == 0.0, np.float32(1.0), std),
    }


def teacher_provenance(teachers: Sequence[dict[str, Any]], goal: str,
                       weight: float) -> dict[str, Any] | None:
    """What the header records of the teachers: digests, not paths."""

    if not teachers:
        return None
    return {
        "goal": goal,
        "weight": float(weight),
        "teachers": [{
            "low": teacher["low"],
            "high": teacher["high"],
            "sha256": teacher["sha256"],
            "label": str(teacher["header"].get("label") or ""),
            "task_sha256": str((teacher["header"].get("task") or {}).get("sha256") or ""),
            "iterations": (teacher["header"].get("training") or {}).get("iterations"),
        } for teacher in sorted(teachers, key=lambda t: t["low"])],
    }


def teacher_actions(xp: Any, teachers: Sequence[dict[str, Any]], observation: Any,
                    goal_index: int) -> tuple[Any, Any]:
    """Each step's teacher action and whether it has a teacher (ADR-825).

    ``observation`` is the actor's raw channels, ``[..., channels]``. A step
    is taught by the teacher whose band ``[low, high)`` holds its goal (the
    last band also takes its ``high``); the target is ``tanh`` of the
    teacher's location, the action before the action box's scale and bias,
    which is what the engine plays. A step no band holds reads a target of 0
    and a mask of 0.
    """

    goal = observation[..., goal_index]
    actions = teachers[0]["layers"][-1][1].shape[0]
    target = xp.zeros(observation.shape[:-1] + (actions,), dtype=observation.dtype)
    mask = xp.zeros(observation.shape[:-1], dtype=observation.dtype)
    top = max((teacher["high"] for teacher in teachers), default=0.0)
    for teacher in teachers:
        inside = (goal >= teacher["low"]) & (
            (goal < teacher["high"]) | ((goal == teacher["high"]) & (teacher["high"] == top)))
        normalised = (observation - xp.asarray(teacher["mean"])) / xp.asarray(teacher["std"])
        layers = [(xp.asarray(w), xp.asarray(b)) for w, b in teacher["layers"]]
        action = xp.tanh(forward(xp, layers, normalised, activation=teacher["activation"]))
        target = xp.where(inside[..., None], action, target)
        mask = xp.where(inside, 1.0, mask).astype(observation.dtype)
    return target, mask


def distillation_loss(xp: Any, student_location: Any, target: Any, mask: Any) -> Any:
    """Mean over every step of ``mask`` times the squared distance between
    the student's played action and its teacher's, averaged over actions.

    Over every step, not only the taught ones: a band holding a fifth of the
    draws pulls a fifth as hard, as PPO's own terms do.
    """

    error = xp.mean(xp.square(xp.tanh(student_location) - target), axis=-1)
    return xp.mean(mask * error)


# ---------------------------------------------------------------------------
# The bundle, and the model beside it.
# ---------------------------------------------------------------------------


def load_bundle(bundle_path: str, table: dict[str, Any]) -> dict[str, Any]:
    """The task, its model's bytes, and the refusals that come before training.

    The model is referenced by a path relative to the *project root* and
    the bundle lives at ``outputs/<name>-task.json`` under it, so the root is
    two levels up. That pair is what makes the bundle movable -- which is
    exactly why it can be copied to a rented box.
    """

    path = Path(bundle_path).resolve()
    task = json.loads(path.read_text(encoding="utf-8"))
    if str(task.get("schema")) != TASK_SCHEMA:
        raise SystemExit(f"unknown task schema {task.get('schema')!r}")

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

    # Before an expression is compiled, and before a GPU is touched. A run
    # that would fail on the last reward term is a run that wasted the box.
    if function_names(table) != [str(name) for name in task["functions"]]:
        raise SystemExit(
            "this trainer's function whitelist differs from the bundle's: "
            f"{function_names(table)} vs {list(task['functions'])}"
        )

    return {
        "task": task,
        "task_bytes": path.read_bytes(),
        "task_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "model_xml": xml,
        "model_sha256": digest,
        "model_path": str(relative.as_posix()),
    }


def goal_channels(task: dict[str, Any]) -> list[str]:
    """Every goal channel the task declares, in bundle order (ADR-462)."""

    return [
        str(channel)
        for record in task.get("goal") or ()
        for channel in record["channels"]
    ]


def command_channels(task: dict[str, Any], *, policy_only: bool = False) -> list[str]:
    """Every command channel the task declares, in bundle order (ADR-696).

    ``CadexDynamics.command_channels``; with ``policy_only`` the ones not
    marked ``role: privileged``.
    """

    return [
        str(channel)
        for record in task.get("commands") or ()
        if not policy_only or str(record.get("role") or "policy") == "policy"
        for channel in record["channels"]
    ]


def command_vector(xp: Any, task: dict[str, Any], issued: Any, before: Any) -> Any:
    """The command channels from the last two issued commands (ADR-696).

    ``CadexDynamics.command_values`` in ``xp``: per command row, the command
    in force and its change over the control interval, interleaved as the
    rows' ``channels`` are. ``issued`` and ``before`` are indexed like the
    bundle's actions along their last axis.
    """

    index = [int(record["action"]) for record in task.get("commands") or ()]
    now = issued[..., index]
    rate = (now - before[..., index]) / float(task["episode"]["control_interval_s"])
    return xp.reshape(xp.stack([now, rate], axis=-1), now.shape[:-1] + (2 * len(index),))


def acceleration_channels(task: dict[str, Any]) -> list[str]:
    """Every acceleration channel the task declares (ADR-699).

    ``CadexDynamics.acceleration_channels``. Every one is privileged, so
    none reaches the actor.
    """

    return [str(channel) for record in task.get("accelerations") or ()
            for channel in record["channels"]]


def acceleration_vector(xp: Any, task: dict[str, Any], qacc: Any) -> Any:
    """The acceleration channels from the simulator's ``qacc`` (ADR-699).

    ``CadexDynamics.acceleration_values`` in ``xp``: each row's degree of
    freedom, times its scale, along ``qacc``'s last axis.
    """

    rows = list(task.get("accelerations") or ())
    dofs = [int(record["dof"]) for record in rows]
    scale = xp.asarray([float(record["scale"]) for record in rows], dtype=qacc.dtype)
    return qacc[..., dofs] * scale


def scan_channels(task: dict[str, Any], *, policy_only: bool = False) -> list[str]:
    """Every height-scan channel the task declares (ADR-715).

    ``CadexDynamics.scan_channels``: last in every vector. With
    ``policy_only`` the ones marked ``role: policy``, which the actor reads
    (ADR-748).
    """

    return [str(channel) for record in task.get("scans") or ()
            if not policy_only or str(record.get("role") or "privileged") == "policy"
            for channel in record["channels"]]


def waypoint_vector(xp: Any, task: dict[str, Any], told: Any, xipos: Any,
                    xmat: Any) -> Any:
    """The goal channels with each waypoint read from the base (ADR-751).

    ``CadexDynamics.waypoint_values`` in ``xp``: ``told`` is the goal vector,
    ``(..., G)`` in ``goal_channels`` order, holding a waypoint's world point
    in mm; a waypoint's two channels become that point ahead of and to the
    left of the base's centre of mass, along its x axis on the ground (the
    world's x when that is vertical). ``xipos`` is ``(..., nbody, 3)`` and
    ``xmat`` ``(..., nbody, 9)`` or ``(..., nbody, 3, 3)``, the leading axes
    ``told``'s. Every other goal channel is returned as it came.
    """

    parts, cursor = [], 0
    for entry in task.get("goal") or ():
        width = len(entry["channels"])
        held = told[..., cursor:cursor + width]
        if entry["kind"] == "waypoint":
            body = int(entry["body_id"])
            scale = float(entry["scale"])
            where = xipos[..., body, :] * scale
            flat = xp.reshape(xmat, xmat.shape[:-2] + (9,)) if xmat.shape[-1] == 3 else xmat
            frame = flat[..., body, :]
            ahead_x, ahead_y = frame[..., 0], frame[..., 3]
            norm = xp.sqrt(ahead_x * ahead_x + ahead_y * ahead_y)
            turned = norm > 1e-9
            safe = xp.where(turned, norm, 1.0)
            cos = xp.where(turned, ahead_x / safe, 1.0)
            sin = xp.where(turned, ahead_y / safe, 0.0)
            dx = held[..., 0] - where[..., 0]
            dy = held[..., 1] - where[..., 1]
            held = xp.stack([cos * dx + sin * dy, -sin * dx + cos * dy], axis=-1)
        parts.append(held)
        cursor += width
    return xp.concatenate(parts, axis=-1)


def height_scan_vector(xp: Any, task: dict[str, Any], xpos: Any, xmat: Any,
                       elevation: Any = None, course: Any = None) -> Any:
    """The height-scan channels (ADR-715), along a new last axis.

    ``CadexDynamics.height_scan_values`` in ``xp``: each scanning body's
    height in mm above the ground at each of its ``offsets_mm``, turned by
    its heading (its x axis on the ground; the world's when that is
    vertical). ``xpos`` is ``(..., nbody, 3)``, times the row's ``scale``, and ``xmat``
    ``(..., nbody, 9)`` or ``(..., nbody, 3, 3)``. ``elevation`` is the
    course's ``hfield_data``, read bilinearly and held at the edge, or
    ``None`` for the plane at z = 0; a box course (ADR-716) reads its boxes.
    ``course`` is a re-drawn course's ``(scan, lowest, domes)`` from
    :func:`terrain_pool`, ``(..., S, 6)``, ``(...)`` and ``(..., D, 4)`` with
    the leading axes ``xpos``'s, read in place of the bundle's boxes and
    domes (ADR-717, ADR-744).
    """

    terrain = task.get("terrain")
    parts = []
    for record in task.get("scans") or ():
        body = int(record["body_id"])
        where = xpos[..., body, :] * float(record["scale"])
        flat = xp.reshape(xmat, xmat.shape[:-2] + (9,)) if xmat.shape[-1] == 3 else xmat
        frame = flat[..., body, :]
        ahead_x, ahead_y = frame[..., 0], frame[..., 3]
        norm = xp.sqrt(ahead_x * ahead_x + ahead_y * ahead_y)
        turned = norm > 1e-9
        safe = xp.where(turned, norm, 1.0)
        cos = xp.where(turned, ahead_x / safe, 1.0)[..., None]
        sin = xp.where(turned, ahead_y / safe, 0.0)[..., None]
        offsets = xp.asarray(record["offsets_mm"], dtype=where.dtype)
        px = where[..., 0:1] + cos * offsets[:, 0] - sin * offsets[:, 1]
        py = where[..., 1:2] + sin * offsets[:, 0] + cos * offsets[:, 1]
        if terrain is not None and terrain.get("kind") == "boxes":
            # ADR-716: the highest box top over the point, or the plane.
            if course is not None:
                # ADR-717: this environment's course, one row per slot.
                rows, lowest, domes = course
                lowest = xp.asarray(lowest, dtype=where.dtype)
                floor, under = lowest[..., None], lowest[..., None, None]
                dx, dy, dz, dr = (domes[..., None, :, column] for column in range(4))
            else:
                boxes = terrain["boxes"]
                rows = xp.asarray(box_scan_rows(course_geoms(
                    boxes, float(terrain["lowest_mm"]), len(boxes), 1.0)),
                    dtype=where.dtype).reshape(len(boxes), 15)
                floor = under = float(terrain["lowest_mm"])
                dx, dy, dz, dr = (
                    xp.asarray([float(dome[key]) - (float(dome["radius_mm"]) if key == "top_mm" else 0.0)
                                for dome in terrain.get("domes") or ()], dtype=where.dtype)
                    for key in ("x_mm", "y_mm", "top_mm", "radius_mm"))
            bx, by = px[..., None], py[..., None]
            # ADR-745: each box read through its own rotation, so a ramp's
            # top, a platform's and a rock's turned stone are all exact.
            ground = xp.maximum(xp.max(box_tops(xp, rows, bx, by, under), axis=-1), floor) \
                if rows.shape[-2] else xp.maximum(px * 0.0, floor)
            if dr.shape[-1]:
                # ADR-744: a dome's sphere over the point, about its centre.
                reach = dr * dr - (bx - dx) ** 2 - (by - dy) ** 2
                cap = dz + xp.sqrt(xp.maximum(reach, 0.0))
                ground = xp.maximum(ground, xp.max(xp.where(reach >= 0.0, cap, under), axis=-1))
        elif terrain is None or elevation is None:
            ground = xp.zeros_like(px)
        else:
            x0, x1 = (float(value) for value in terrain["x_range_mm"])
            y0, y1 = (float(value) for value in terrain["y_range_mm"])
            nrow, ncol = int(terrain["nrow"]), int(terrain["ncol"])
            across = (xp.clip(px, x0, x1) - x0) / (x1 - x0) * (ncol - 1)
            along = (xp.clip(py, y0, y1) - y0) / (y1 - y0) * (nrow - 1)
            column = xp.minimum(xp.floor(across), ncol - 2)
            row = xp.minimum(xp.floor(along), nrow - 2)
            u, v = across - column, along - row
            column, row = column.astype(xp.int32), row.astype(xp.int32)
            grid = xp.asarray(elevation, dtype=where.dtype)

            def at(r, c):
                return grid[r * ncol + c]

            level = ((1.0 - v) * ((1.0 - u) * at(row, column) + u * at(row, column + 1))
                     + v * ((1.0 - u) * at(row + 1, column) + u * at(row + 1, column + 1)))
            lowest = float(terrain["lowest_mm"])
            ground = lowest + (float(terrain["highest_mm"]) - lowest) * level
        parts.append(where[..., 2:3] - ground)
    return xp.concatenate(parts, axis=-1)


# ---------------------------------------------------------------------------
# A course re-drawn per episode (ADR-717). The bundle's terrain carries a
# pool of courses as features; each environment is given one at every reset
# and the model's terrain geoms are placed there. The box builder below is
# ``CadexDynamics.terrain_boxes`` and ``terrain_box_geoms`` written out again,
# because this file cannot import the engine. No test holds the two equal
# since ADR-725: change them together.
# ---------------------------------------------------------------------------

#: How this trainer gives an environment its course: drawn on device, on the
#: same terms as the goal pool's pick.
TERRAIN_MODE = "per_episode"
TERRAIN_POOL_ALGORITHM = (
    "jax.random.randint over the bundle's terrain pool, folded from the reset "
    "key with 717, on every reset; the pool's courses are the bundle's own, "
    "drawn by the engine (terrain.random.algorithm)"
)

#: ``CadexDynamics`` constants the builder needs, copied and pinned equal.
TERRAIN_BASE_MM = 50.0
TERRAIN_FLAT_MM = 0.1
TERRAIN_RAMP_HALF_THICKNESS_MM = 10.0
TERRAIN_PARKED_DEPTH_MM = 1000.0
TERRAIN_PARKED_HALF_MM = 1.0
TERRAIN_RUNOUT_MM = 50000.0
TERRAIN_ROCK_CELLS = 3
TERRAIN_ROCK_TILT_DEG = (10.0, 25.0)
TERRAIN_ROCK_EMPTY = 0.3


def course_domes(features: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """A validated course's dome records (``CadexDynamics.terrain_boxes``'
    ``domes``, ADR-744): each bump a sphere whose cap is the bump."""

    domes = []
    for feature in features:
        if feature["kind"] != "bump":
            continue
        foot, rise = feature["radius_mm"], feature["height_mm"]
        domes.append({"x_mm": float(feature["x_mm"]), "y_mm": float(feature["y_mm"]),
                      "top_mm": _course_profile_mm(features, feature["x_mm"]) + rise,
                      "radius_mm": (foot * foot + rise * rise) / (2.0 * rise)})
    return domes


def _course_profile_mm(features: Sequence[dict[str, Any]], x_mm: float) -> float:
    height = 0.0
    for feature in features:
        if feature["kind"] == "step":
            if x_mm >= feature["x_mm"]:
                height += feature["height_mm"]
        elif feature["kind"] == "slope":
            run = min(max(x_mm, feature["from_x_mm"]), feature["to_x_mm"]) - feature["from_x_mm"]
            height += run * math.tan(math.radians(feature["grade_deg"]))
    return height


def course_boxes(features: Sequence[dict[str, Any]], x_range_mm: Sequence[float],
                 y_range_mm: Sequence[float]) -> list[dict[str, Any]]:
    """A validated course's box records (``CadexDynamics.terrain_boxes``,
    without its refusals: the engine made them when it drew the pool); its
    bumps are :func:`course_domes`."""

    x0, x1 = (float(value) for value in x_range_mm)
    y0, y1 = (float(value) for value in y_range_mm)
    cuts = {x0, x1}
    for feature in features:
        if feature["kind"] not in ("step", "slope"):
            continue
        for key in ("x_mm",) if feature["kind"] == "step" else ("from_x_mm", "to_x_mm"):
            if x0 < feature[key] < x1:
                cuts.add(float(feature[key]))
    edges = sorted(cuts)
    segments = []
    for a, b in zip(edges, edges[1:]):
        rise = sum(
            math.tan(math.radians(feature["grade_deg"]))
            for feature in features
            if feature["kind"] == "slope"
            and feature["from_x_mm"] <= a and feature["to_x_mm"] >= b
        )
        za = _course_profile_mm(features, a)
        segments.append((a, b, za, za + rise * (b - a)))
    lowest = min(0.0, *(min(za, zb) for _, _, za, zb in segments))
    boxes: list[dict[str, Any]] = []

    def box(shape, xs, ys, tops):
        boxes.append({"shape": shape, "x_range_mm": [float(v) for v in xs],
                      "y_range_mm": [float(v) for v in ys],
                      "top_mm": [float(v) for v in tops]})

    # ADR-745: the first and last level run on past the extent, and every
    # segment across it, so the ground has no edge an episode reaches.
    a, b, za, zb = segments[0]
    if abs(zb - za) <= TERRAIN_FLAT_MM:
        segments[0] = (x0 - TERRAIN_RUNOUT_MM, b, za, zb)
    else:
        segments.insert(0, (x0 - TERRAIN_RUNOUT_MM, x0, za, za))
    a, b, za, zb = segments[-1]
    if abs(zb - za) <= TERRAIN_FLAT_MM:
        segments[-1] = (a, x1 + TERRAIN_RUNOUT_MM, za, zb)
    else:
        segments.append((x1, x1 + TERRAIN_RUNOUT_MM, zb, zb))
    across = (y0 - TERRAIN_RUNOUT_MM, y1 + TERRAIN_RUNOUT_MM)
    for a, b, za, zb in segments:
        low = min(za, zb)
        if low > lowest + TERRAIN_FLAT_MM:
            box("block", (a, b), across, (low, low))
        if abs(zb - za) > TERRAIN_FLAT_MM:
            box("ramp", (a, b), across, (za, zb))
    for feature in features:
        if feature["kind"] == "platform":
            top = _course_profile_mm(features, feature["x_mm"]) + feature["height_mm"]
            box("block", (feature["x_mm"] - feature["length_mm"] / 2.0,
                          feature["x_mm"] + feature["length_mm"] / 2.0),
                (feature["y_mm"] - feature["width_mm"] / 2.0,
                 feature["y_mm"] + feature["width_mm"] / 2.0), (top, top))
        elif feature["kind"] == "rock":
            boxes.extend(course_rock_stones(feature, _course_profile_mm(features, feature["x_mm"])))
    return boxes


def course_rock_stones(rock: dict[str, Any], ground_mm: float) -> list[dict[str, Any]]:
    """A rock patch's stones (``CadexDynamics.terrain_rock_stones``, ADR-745)."""

    import random

    x, y, radius, height = (float(rock[key]) for key in ("x_mm", "y_mm", "radius_mm", "height_mm"))
    rng = random.Random(f"cadex-rock:{x!r}:{y!r}:{radius!r}:{height!r}")
    cell = 2.0 * radius / TERRAIN_ROCK_CELLS
    room = cell / 2.0
    stones = []
    for i in range(TERRAIN_ROCK_CELLS):
        for j in range(TERRAIN_ROCK_CELLS):
            centre_cell = (i, j) == (TERRAIN_ROCK_CELLS // 2, TERRAIN_ROCK_CELLS // 2)
            if not centre_cell and rng.random() < TERRAIN_ROCK_EMPTY:
                continue
            about = rng.choice(("x", "y"))
            tilt = math.radians(rng.uniform(*TERRAIN_ROCK_TILT_DEG)) * rng.choice((-1.0, 1.0))
            sine, cosine = abs(math.sin(tilt)), math.cos(tilt)
            turned = (rng.uniform(0.55, 0.95) * room - height * sine) / cosine
            across = rng.uniform(0.55, 0.95) * room
            reach = turned * cosine + height * sine
            rise = turned * sine + height * cosine
            if about == "y":
                half, plan = [turned, across, height], (reach, across)
                quat = [math.cos(tilt / 2.0), 0.0, math.sin(tilt / 2.0), 0.0]
            else:
                half, plan = [across, turned, height], (across, reach)
                quat = [math.cos(tilt / 2.0), math.sin(tilt / 2.0), 0.0, 0.0]
            cx = x - radius + (i + 0.5) * cell + rng.uniform(-1.0, 1.0) * (room - plan[0])
            cy = y - radius + (j + 0.5) * cell + rng.uniform(-1.0, 1.0) * (room - plan[1])
            peak = float(ground_mm) + rng.uniform(0.4, 1.0) * height
            stones.append({"shape": "stone", "centre_mm": [cx, cy, peak - rise],
                           "quat": quat, "half_mm": half, "top_mm": peak})
    return stones


def course_geoms(boxes: Sequence[dict[str, Any]], lowest_mm: float, slots: int,
                 scale: float) -> dict[str, Any]:
    """Where each of ``slots`` box geoms stands for one course, in metres
    (``CadexDynamics.terrain_box_geoms``): the course's boxes, then parked
    cubes under the plane. ``scale`` is the bundle's metres per millimetre
    (``terrain.scale``)."""

    lowest = float(lowest_mm)
    pos, quat, size = [], [], []
    for record in boxes:
        if record["shape"] == "stone":
            pos.append([value * scale for value in record["centre_mm"]])
            quat.append([float(value) for value in record["quat"]])
            size.append([value * scale for value in record["half_mm"]])
            continue
        (xa, xb), (ya, yb) = record["x_range_mm"], record["y_range_mm"]
        za, zb = record["top_mm"]
        if record["shape"] == "block":
            bottom = lowest - TERRAIN_BASE_MM
            centre = [(xa + xb) / 2.0, (ya + yb) / 2.0, (za + bottom) / 2.0]
            half = [(xb - xa) / 2.0, (yb - ya) / 2.0, (za - bottom) / 2.0]
            turn = [1.0, 0.0, 0.0, 0.0]
        else:
            grade = math.atan2(zb - za, xb - xa)
            thick = TERRAIN_RAMP_HALF_THICKNESS_MM
            centre = [(xa + xb) / 2.0 + thick * math.sin(grade), (ya + yb) / 2.0,
                      (za + zb) / 2.0 - thick * math.cos(grade)]
            half = [math.hypot(xb - xa, zb - za) / 2.0, (yb - ya) / 2.0, thick]
            turn = [math.cos(grade / 2.0), 0.0, -math.sin(grade / 2.0), 0.0]
        pos.append([value * scale for value in centre])
        quat.append(turn)
        size.append([value * scale for value in half])
    parked = lowest - TERRAIN_BASE_MM - TERRAIN_PARKED_DEPTH_MM
    for _ in range(int(slots) - len(boxes)):
        pos.append([0.0, 0.0, parked * scale])
        quat.append([1.0, 0.0, 0.0, 0.0])
        size.append([TERRAIN_PARKED_HALF_MM * scale] * 3)
    return {"plane_z_m": lowest * scale, "pos_m": pos, "quat": quat, "size_m": size}


def box_scan_rows(placed: dict[str, Any]) -> list[list[float]]:
    """Each box of :func:`course_geoms` (at ``scale`` 1, so in mm) as the row
    a height scan reads (ADR-745): its centre, its three axes in the world
    (its rotation's columns) and its half-extents, 15 numbers."""

    rows = []
    for centre, (w, x, y, z), half in zip(placed["pos_m"], placed["quat"], placed["size_m"]):
        axes = [1 - 2 * (y * y + z * z), 2 * (x * y + w * z), 2 * (x * z - w * y),
                2 * (x * y - w * z), 1 - 2 * (x * x + z * z), 2 * (y * z + w * x),
                2 * (x * z + w * y), 2 * (y * z - w * x), 1 - 2 * (x * x + y * y)]
        rows.append([*centre, *axes, *half])
    return rows


def box_tops(xp: Any, rows: Any, px: Any, py: Any, under: Any) -> Any:
    """The highest point of each box on the vertical line at each point
    (``CadexDynamics.terrain_turned_box_top_mm``), or ``under`` off it:
    ``rows`` ``(..., S, 15)`` from :func:`box_scan_rows`, ``px`` and ``py``
    ``(..., N, 1)``; returns ``(..., N, S)``."""

    rows = rows[..., None, :, :]
    dx, dy, cz = px - rows[..., 0], py - rows[..., 1], rows[..., 2]
    low = high = None
    inside = None
    for axis in range(3):
        ax, ay, az = (rows[..., 3 + 3 * axis + k] for k in range(3))
        half = rows[..., 12 + axis]
        offset = ax * dx + ay * dy - az * cz
        level = xp.abs(az) < 1e-9
        safe = xp.where(level, 1.0, az)
        a, b = (-half - offset) / safe, (half - offset) / safe
        lo = xp.where(level, -1e12, xp.minimum(a, b))
        hi = xp.where(level, 1e12, xp.maximum(a, b))
        within = ~level | (xp.abs(offset) <= half)
        low = lo if low is None else xp.maximum(low, lo)
        high = hi if high is None else xp.minimum(high, hi)
        inside = within if inside is None else inside & within
    return xp.where(inside & (low <= high), high, under)


def terrain_pool(np: Any, terrain: dict[str, Any]) -> dict[str, Any]:
    """The bundle's terrain pool as arrays, course first (ADR-717).

    ``plane_z`` ``(P,)``; ``pos``, ``size`` ``(P, S, 3)``; ``quat``
    ``(P, S, 4)``; ``rbound`` ``(P, S)`` and ``aabb`` ``(P, S, 6)``, which
    MuJoCo derives from a box's size at compile time; ``scan`` ``(P, S, 15)``,
    each slot's :func:`box_scan_rows` row in mm (ADR-745), a parked slot its
    cube under the plane; and ``lowest`` ``(P,)`` in mm. Domes (ADR-744): ``dome_pos``
    ``(P, D, 3)`` and ``dome_size`` ``(P, D, 3)`` (the radius, then zeros),
    ``dome_rbound`` ``(P, D)``, ``dome_aabb`` ``(P, D, 6)`` and
    ``dome_scan`` ``(P, D, 4)``, each dome's centre and radius in mm, a
    parked slot's radius 0.
    """

    slots = int(terrain["slots"])
    dome_slots = int(terrain.get("dome_slots") or 0)
    scale = float(terrain["scale"])
    columns: dict[str, list[Any]] = {key: [] for key in (
        "plane_z", "pos", "quat", "size", "scan", "lowest", "dome_pos", "dome_size",
        "dome_scan")}
    for course in terrain["pool"]:
        boxes = course_boxes(course["features"], terrain["x_range_mm"], terrain["y_range_mm"])
        if len(boxes) != int(course["boxes"]):
            raise SystemExit(
                f"a pooled course builds {len(boxes)} boxes here and "
                f"{course['boxes']} in the engine, so this trainer's box "
                "builder is not the engine's")
        placed = course_geoms(boxes, course["lowest_mm"], slots, float(terrain["scale"]))
        lowest = float(course["lowest_mm"])
        columns["plane_z"].append(placed["plane_z_m"])
        columns["pos"].append(placed["pos_m"])
        columns["quat"].append(placed["quat"])
        columns["size"].append(placed["size_m"])
        columns["lowest"].append(lowest)
        columns["scan"].append(box_scan_rows(course_geoms(boxes, lowest, slots, 1.0)))
        domes = course_domes(course["features"])
        if len(domes) != int(course.get("domes", 0)):
            raise SystemExit(
                f"a pooled course builds {len(domes)} domes here and "
                f"{course.get('domes', 0)} in the engine, so this trainer's dome "
                "builder is not the engine's")
        parked = lowest - TERRAIN_BASE_MM - TERRAIN_PARKED_DEPTH_MM
        rows = ([[d["x_mm"], d["y_mm"], d["top_mm"] - d["radius_mm"], d["radius_mm"]] for d in domes]
                + [[0.0, 0.0, parked, 0.0]] * (dome_slots - len(domes)))
        columns["dome_scan"].append(rows)
        columns["dome_pos"].append([[row[0] * scale, row[1] * scale, row[2] * scale] for row in rows])
        columns["dome_size"].append(
            [[(row[3] or TERRAIN_PARKED_HALF_MM) * scale, 0.0, 0.0] for row in rows])
    arrays = {key: np.asarray(value, dtype=np.float64) for key, value in columns.items()}
    # A course of domes alone has no box slots: keep the slot axis (ADR-747).
    for key, count, width in (("pos", slots, 3), ("quat", slots, 4), ("size", slots, 3),
                              ("scan", slots, 15), ("dome_pos", dome_slots, 3),
                              ("dome_size", dome_slots, 3), ("dome_scan", dome_slots, 4)):
        arrays[key] = arrays[key].reshape(len(terrain["pool"]), count, width)
    arrays["rbound"] = np.linalg.norm(arrays["size"], axis=-1)
    arrays["aabb"] = np.concatenate([np.zeros_like(arrays["size"]), arrays["size"]], axis=-1)
    arrays["dome_rbound"] = arrays["dome_size"][..., 0]
    arrays["dome_aabb"] = np.concatenate(
        [np.zeros_like(arrays["dome_size"]), np.repeat(arrays["dome_size"][..., :1], 3, axis=-1)],
        axis=-1)
    return arrays


def place_course(model: Any, pool: dict[str, Any], slots: Any, plane: int, course: Any,
                 dome_slots: Any) -> Any:
    """An MJX model with one pooled course in its terrain geoms (ADR-717):
    the plane at the course's lowest point, and each slot's box, or a parked
    cube, where :func:`terrain_pool` stands it, and each dome slot's sphere
    (ADR-744). ``pool`` holds its arrays on the device; ``slots`` are the
    ``environment/terrain/<i>`` geom ids, ``dome_slots`` the
    ``environment/terrain/dome/<j>`` ones."""

    return model.replace(
        geom_pos=model.geom_pos.at[slots].set(pool["pos"][course])
        .at[dome_slots].set(pool["dome_pos"][course])
        .at[plane, 2].set(pool["plane_z"][course]),
        geom_quat=model.geom_quat.at[slots].set(pool["quat"][course]),
        geom_size=model.geom_size.at[slots].set(pool["size"][course])
        .at[dome_slots].set(pool["dome_size"][course]),
        geom_rbound=model.geom_rbound.at[slots].set(pool["rbound"][course])
        .at[dome_slots].set(pool["dome_rbound"][course]),
        geom_aabb=model.geom_aabb.at[slots].set(pool["aabb"][course])
        .at[dome_slots].set(pool["dome_aabb"][course]))


def tracking_channels(task: dict[str, Any], *, policy_only: bool = False) -> list[str]:
    """Every channel a gait reference adds (ADR-706); with ``policy_only``
    its clock alone. ``CadexDynamics.tracking_channels``."""

    tracking = task.get("tracking")
    if not tracking:
        return []
    return [str(channel) for channel in
            tracking["policy_channels" if policy_only else "channels"]]


def schedule_blend(xp: Any, task: dict[str, Any], told: Any) -> tuple[Any, Any]:
    """The lower bracketing stride of a speed schedule and the upper one's
    weight, at the command in ``told`` (ADR-773).
    ``CadexDynamics.schedule_blend`` in ``xp``."""

    scheduled = task["tracking"]["schedule"]
    speeds = xp.asarray([float(v) for v in scheduled["speeds_mm_s"]], dtype=told.dtype)
    count = len(scheduled["speeds_mm_s"])
    v = xp.clip(xp.abs(told[..., goal_channels(task).index(str(scheduled["channel"]))]),
                speeds[0], speeds[-1])
    index = xp.clip(xp.searchsorted(speeds, v, side="right") - 1, 0, count - 2)
    weight = (v - speeds[index]) / (speeds[index + 1] - speeds[index])
    if scheduled.get("switches_mm_s"):
        # ADR-822: where two gait families meet, one or the other, never a blend.
        switched = [value is not None for value in scheduled["switches_mm_s"]]
        at = xp.asarray([float(value) if value is not None else 0.0
                         for value in scheduled["switches_mm_s"]], dtype=told.dtype)
        weight = xp.where(xp.asarray(switched)[index],
                          (v >= at[index]).astype(told.dtype), weight)
    return index, weight


def schedule_nearest(xp: Any, task: dict[str, Any], told: Any) -> Any:
    """The stride nearest the command in ``told``, the slower on a tie
    (ADR-773); with family switches (ADR-822), the bracketing stride nearer
    in the blend's weight. ``CadexDynamics.schedule_nearest`` in ``xp``."""

    scheduled = task["tracking"]["schedule"]
    if scheduled.get("switches_mm_s"):
        index, weight = schedule_blend(xp, task, told)
        return index + (weight > 0.5).astype(index.dtype)
    speeds = xp.asarray([float(v) for v in scheduled["speeds_mm_s"]], dtype=told.dtype)
    v = xp.abs(told[..., goal_channels(task).index(str(scheduled["channel"]))])
    return xp.argmin(xp.abs(speeds - v[..., None]), axis=-1)


def tracking_turn(xp: Any, task: dict[str, Any], told: Any) -> Any:
    """Cycles the gait clock turns over one control step taken under the
    goal channels ``told`` (``(..., G)`` in ``goal_channels`` order), on a
    speed cadence (ADR-752) or a speed schedule (ADR-773).
    ``CadexDynamics.tracking_turn`` in ``xp``."""

    tracking = task["tracking"]
    if tracking.get("schedule"):
        index, weight = schedule_blend(xp, task, told)
        turns = xp.asarray([float(v) for v in tracking["schedule"]["turns_per_step"]],
                           dtype=told.dtype)
        return (1.0 - weight) * turns[index] + weight * turns[index + 1]
    cadence = tracking["cadence"]
    speed = xp.abs(told[..., goal_channels(task).index(str(cadence["channel"]))])
    return float(tracking["turn_per_step"]) * (
        speed / float(cadence["reference_speed_mm_s"])) ** float(cadence["exponent"])


def tracking_vector(xp: Any, task: dict[str, Any], steps: Any, origin: Any = None,
                    turned: Any = None, told: Any = None) -> Any:
    """The tracking channels after ``steps`` control steps (ADR-706) of an
    episode that started at clip sample ``origin`` (ADR-709), or, on a
    speed cadence, after the clock has turned ``turned`` cycles (ADR-752).

    ``CadexDynamics.tracking_values`` in ``xp``, along a new last axis:
    the clock's phase is ``steps * turn_per_step`` (or ``turned``) plus
    ``origin / samples``, less its whole turns; a
    phase between two rows of the clip's table is read linearly between
    them, round the end, and a ``held`` column reads 1 from one half up.
    On a speed schedule (ADR-773) ``told`` is the goal channels in force,
    and the two bracketing strides' readings are blended before a held
    column is thresholded; ``origin`` is then a row of every stride's
    samples, whose phase is ``origin mod samples``.
    """

    tracking = task["tracking"]
    rows = int(tracking["samples"])
    turned = (xp.asarray(steps) * float(tracking["turn_per_step"]) if turned is None
              else xp.asarray(turned))
    if origin is not None:
        turned = turned + (xp.asarray(origin) % rows) / float(rows)
    phase = turned - xp.floor(turned)
    at = phase * rows
    floor = xp.floor(at)
    weight = (at - floor)[..., None]
    low = floor.astype(xp.int32) % rows
    high = (low + 1) % rows
    if tracking.get("schedule"):
        stride, share = schedule_blend(xp, task, told)
        share = share[..., None].astype(weight.dtype)
        tables = xp.asarray(tracking["schedule"]["tables"], dtype=weight.dtype)
        below = (1.0 - share) * tables[stride, low] + share * tables[stride + 1, low]
        above = (1.0 - share) * tables[stride, high] + share * tables[stride + 1, high]
        value = below + weight * (above - below)
    else:
        table = xp.asarray(tracking["table"], dtype=weight.dtype)
        value = table[low] + weight * (table[high] - table[low])
    held = xp.asarray([bool(flag) for flag in tracking["held"]])
    value = xp.where(held, (value >= 0.5).astype(value.dtype), value)
    angle = (2.0 * math.pi) * phase
    return xp.concatenate([xp.sin(angle)[..., None], xp.cos(angle)[..., None], value], axis=-1)


def channels(task: dict[str, Any]) -> list[str]:
    """Every name an expression may use: sensor, goal, command, acceleration,
    tracking, then height-scan channels (ADR-699, ADR-706, ADR-715).

    The engine's ``CadexDynamics._task_channels`` is the same rule. The
    sensor channels come out of ``sensordata``; the goal channels are what
    the episode is asking for, appended after them, so a task that gains a
    goal keeps the position of every channel it already had. The command
    channels (ADR-696) follow on the same terms.
    """

    return [
        str(channel)
        for record in task["observations"]
        for channel in record["channels"]
    ] + (goal_channels(task) + command_channels(task) + acceleration_channels(task)
         + tracking_channels(task) + scan_channels(task))


def actor_channels(task: dict[str, Any]) -> list[str]:
    """The channels the policy network reads (ADR-408).

    A row marked ``role: privileged`` is a simulation-only quantity: the
    reward, the terminations and the critic read it, and the actor -- the
    only network that ships -- never does. A task written before ADR-408
    marks none, so this is every channel, which is what it always was.
    The engine's ``CadexDynamics.policy_channels`` is the same rule; this
    copy is here because the trainer imports nothing from the engine.

    Every goal channel follows (ADR-462): a goal is what the robot is told
    to do, so the policy always reads it. Then the policy's command channels
    (ADR-696), then a gait reference's clock (ADR-706), then a height scan
    marked ``role: policy`` (ADR-748).
    """

    return [
        str(channel)
        for record in task["observations"]
        if str(record.get("role") or "policy") == "policy"
        for channel in record["channels"]
    ] + (goal_channels(task) + command_channels(task, policy_only=True)
         + tracking_channels(task, policy_only=True)
         + scan_channels(task, policy_only=True))


def tracker_reading(xp: Any, true_mm: Any, tracker: dict[str, Any],
                    noise_mm: Any = None) -> Any:
    """What a position tracker reports for a body at ``true_mm`` (ADR-588).

    ``CadexDynamics.tracker_reading`` written out in ``xp`` (``jnp`` here,
    ``numpy`` in the test that pins the two equal), because this file cannot
    import the engine. The true position plus the drawn noise, rounded to the
    declared resolution, then the in-range flag; outside the range on any
    axis -- judged on the true position, as a panel judges a touch -- every
    value is 0, never a clamped or a held one.
    """

    low = xp.asarray([float(pair[0]) for pair in tracker["range_mm"]])
    high = xp.asarray([float(pair[1]) for pair in tracker["range_mm"]])
    inside = xp.all(xp.logical_and(true_mm >= low, true_mm <= high))
    step = float(tracker["resolution_mm"])
    seen = true_mm if noise_mm is None else true_mm + noise_mm
    quantised = xp.round(seen / step) * step
    reading = xp.concatenate([quantised, xp.ones((1,), dtype=quantised.dtype)])
    return xp.where(inside, reading, xp.zeros_like(reading))


def tracker_velocity_noise(tracker: dict[str, Any]) -> tuple[float, float]:
    """``(noise, resolution)`` of a differenced velocity, mm/s (ADR-590).

    ``CadexDynamics.tracker_velocity_noise``: two readings ``1 / rate_hz``
    apart, so ``sqrt(2) * noise_mm * rate_hz`` and ``resolution_mm * rate_hz``.
    """

    rate = float(tracker["rate_hz"])
    return (math.sqrt(2.0) * float(tracker["noise_mm"]) * rate,
            float(tracker["resolution_mm"]) * rate)


def tracker_velocity_reading(xp: Any, true_mm_s: Any, tracker: dict[str, Any],
                             in_range: Any, noise_mm_s: Any = None) -> Any:
    """A tracker's differenced velocity (ADR-590), as the engine computes it.

    ``CadexDynamics.tracker_velocity_reading`` in ``xp``: velocity plus the
    drawn noise, rounded to the velocity resolution, and zeros whenever
    ``in_range`` -- the paired position's flag -- is not 1.
    """

    _sigma, step = tracker_velocity_noise(tracker)
    seen = true_mm_s if noise_mm_s is None else true_mm_s + noise_mm_s
    quantised = xp.round(seen / step) * step
    return xp.where(in_range == 1.0, quantised, xp.zeros_like(quantised))


def load_reading(xp: Any, true_effort: Any, load: dict[str, Any],
                 noise: Any = None) -> Any:
    """What a load sensor reports for an actuator's effort (ADR-591).

    ``CadexDynamics.load_reading`` in ``xp``: the effort plus the drawn
    noise, held within the stall line ``+/- full_scale``, then rounded to
    the declared resolution.
    """

    scale = float(load["full_scale"])
    step = float(load["resolution"])
    seen = true_effort if noise is None else true_effort + noise
    return xp.round(xp.clip(seen, -scale, scale) / step) * step


def contact_reading(xp: Any, force_n: Any, contact: dict[str, Any]) -> Any:
    """A contact channel and its ``_down`` flag (ADR-698).

    ``CadexDynamics.contact_reading`` in ``xp``: the touch sensor's normal
    force, then 1.0 while it is above the bundle's ``down_above_n``.
    """

    down = (force_n > float(contact["down_above_n"])).astype(force_n.dtype)
    return xp.concatenate([force_n, down])


def sensor_variance_floor(task: dict[str, Any]) -> list[float]:
    """The least variance the normaliser may hold for each channel (ADR-589).

    Zero for every channel no declared sensor reports. A load sensor's
    channel (ADR-591) is floored like a tracked axis, at the larger of its
    resolution and its noise, squared. A tracked
    axis is known no finer than the larger of its resolution and its noise,
    so its spread is floored at that, squared; the in-range flag is a 0/1
    flag, floored at a quarter, the variance of a fair one. Without the
    floor, an axis the body barely moves along -- a ball's height above the
    panel it rolls on -- holds a variance near zero, and one rounding step
    or one lost touch reaches the policy as thousands of standard
    deviations. In channel order, which is ``channels(task)``'s order.
    """

    floor: list[float] = []
    for record in task["observations"]:
        tracker = record.get("tracker")
        load = record.get("load")
        for index, _channel in enumerate(record["channels"]):
            if record.get("contact"):
                # ADR-698: the force is exact; the down flag is a 0/1 flag,
                # floored like the tracker's.
                floor.append(0.0 if index < int(record["dim"]) else 0.25)
            elif load:
                known = max(float(load["resolution"]), float(load["noise"]))
                floor.append(known * known)
            elif not tracker:
                floor.append(0.0)
            elif record.get("in_range_of"):
                known = max(tracker_velocity_noise(tracker))
                floor.append(known * known)
            elif index < int(record["dim"]):
                known = max(float(tracker["resolution_mm"]), float(tracker["noise_mm"]))
                floor.append(known * known)
            else:
                floor.append(0.25)
    return floor + [0.0] * (len(goal_channels(task)) + len(command_channels(task))
                            + len(acceleration_channels(task)) + len(tracking_channels(task))
                            + len(scan_channels(task)))


def sensor_noise_std(task: dict[str, Any]) -> list[float]:
    """One standard deviation per noisy coordinate, in observation order.

    A tracked velocity's is the differenced one (ADR-590); a load sensor's
    is its declared noise (ADR-591).
    """

    def spread(record: dict[str, Any]) -> float:
        if record.get("load"):
            return float(record["load"]["noise"])
        if record.get("in_range_of"):
            return tracker_velocity_noise(record["tracker"])[0]
        return float(record["tracker"]["noise_mm"])

    return [
        spread(record)
        for record in task["observations"]
        if record.get("tracker") or record.get("load")
        for _axis in range(int(record["dim"]))
    ]


# ---------------------------------------------------------------------------
# Domain randomisation, and the extension this trainer states rather than
# improvises.
# ---------------------------------------------------------------------------

#: How this trainer extends the bundle's one stated algorithm to the
#: thousands of independent draws a training run needs.
#:
#: The bundle states exactly one thing: ``random.Random(seed)`` drawing
#: ``uniform(low, high)`` in bundle order. That is one parameter set. A
#: training run needs many, and "whatever the trainer did" is not
#: reproducible -- so the extension is written into the container rather
#: than left to be inferred from the code that happened to run.
#:
#: **Environment *e* of the batch uses ``seed = base_seed + e``**, the
#: bundle's own algorithm unchanged, and holds that draw for the whole run.
#: Measured: 1000 seeds give 1000 distinct draw tuples, and seed 0
#: reproduces the bundle's own numbers exactly, so a single-environment run
#: at ``base_seed`` is the episode the engine and the reference runner
#: already agree on.
#:
#: What this does *not* do is resample per episode. That would need the
#: batched model rebuilt inside the training loop; holding one draw per
#: environment gives ``--envs`` distinct mechanisms, which is what domain
#: randomisation is for, and the limitation is stated here rather than
#: discovered.
RANDOMISATION_MODE = "per_environment"
RANDOMISATION_ALGORITHM = (
    "random.Random(base_seed + environment_index) drawing uniform(low, high) "
    "in bundle order, held fixed for the run"
)

#: How the M9 per-episode draws are made *here*, which is deliberately not
#: how the bundle's ``variation_algorithm`` says the engine makes them.
#:
#: The bundle's is ``random.Random(seed)`` continuing in bundle order. That
#: is a host-side stream and it cannot run here: a reset happens **on device,
#: inside a jitted scan**, thousands of times per iteration and whenever an
#: environment's episode ends. So this splits a ``jax.random`` key instead,
#: and the two do not produce the same numbers.
#:
#: They do not need to, and saying why is the point of writing this down.
#: Nobody replays a training episode -- there are millions of them and none
#: is referenced again. What VISION principle 3 requires is that *the
#: rollout* be reproducible from the script, and the rollout runs in the
#: engine on the stdlib path. What has to be identical between the two is the
#: **arithmetic** -- the same quaternion product, the same window test, the
#: same centre-of-mass application point -- not the stream that feeds it.
RESET_VARIATION_MODE = "per_episode"
RESET_VARIATION_ALGORITHM = (
    "jax.random.split of the rollout key, drawing uniform(low, high) in "
    "bundle order per environment on every reset. Deliberately NOT the "
    "bundle's variation_algorithm: that one is a host-side random.Random "
    "stream and a reset here happens on device inside a jitted scan. Same "
    "arithmetic, different numbers, and nobody replays a training episode"
)


#: How this trainer draws an episode's goals (ADR-462), and the one
#: per-episode draw it does **not** improvise on device.
#:
#: The reset variation above is redrawn with ``jax.random`` and need not
#: match the engine, because nobody replays a training episode. A goal is
#: different in kind: a ``point`` is where a tip is at a drawn joint
#: configuration that touches nothing and clears a floor, which takes
#: forward kinematics and a contact check, and a second algorithm that only
#: resembled the bundle's would train a policy on targets the evaluation
#: never asks for. So the goals are drawn **on the host, by the bundle's own
#: ``goal_algorithm``**, into a pool of whole episodes before training
#: starts, and the device only ever chooses which pooled episode an
#: environment is given. :func:`draw_goals` is that algorithm, and a test
#: holds it to the engine's numbers from the same seed.
#:
#: The pool is one stream, ``random.Random(base_seed)``, with no
#: randomisation or reset draws in front of it. An evaluation seed's goals
#: come after that seed's other draws, so the two coincide only for a task
#: with none of those -- which is why a ``--seed`` that is one of the
#: bundle's evaluation seeds is refused outright.
GOAL_MODE = "host_pool"
GOAL_POOL_ALGORITHM = (
    "random.Random(base_seed) drawing `pool` consecutive episodes by the "
    "bundle's goal_algorithm on the host; on device each environment is "
    "given one pooled episode, chosen by jax.random.randint on every reset, "
    "and reads segment min(step // resample_steps, segments - 1) of it"
)


def check_training_seed(task: dict[str, Any], seed: int) -> None:
    """Refuse a ``--seed`` that is one of the task's evaluation seeds.

    Evaluation seeds are never training seeds. The engine refuses to judge a
    policy on the seed it was trained with, and with a goal the rule has
    teeth: the pool's first episode is the first draws of
    ``random.Random(seed)``, which for a task with no randomisation, reset
    variation or disturbance are exactly the goals that evaluation seed
    draws. Refused before anything is imported, so it costs no GPU time.
    """

    judged = [int(value) for value in (task.get("success") or {}).get("seeds") or ()]
    if int(seed) in judged:
        raise SystemExit(
            f"--seed {int(seed)} is one of this task's evaluation seeds "
            f"({judged}). Evaluation seeds are never training seeds: pick "
            "another, and leave the spec's seeds as they are."
        )


def goal_tip_m(data: Any, body: int, local_m: Sequence[float]) -> list[float]:
    """One point fixed on one body, in the world, in metres.

    ``CadexDynamics._goal_tip_m``, written out again: ``xpos`` plus the
    body's rotation, nine row-major numbers in ``xmat``, applied to the
    offset.
    """

    origin = data.xpos[body]
    rotation = data.xmat[body]
    return [
        float(origin[axis])
        + sum(float(rotation[3 * axis + other]) * float(local_m[other])
              for other in range(3))
        for axis in range(3)
    ]


def goal_in_frame_m(data: Any, frame: int, point_m: Sequence[float]) -> list[float]:
    """A world point in one body's frame, in metres (ADR-592).

    ``CadexDynamics._goal_in_frame_m``, written out again: the transpose of
    ``xmat[frame]`` applied to the point less ``xpos[frame]``.
    """

    origin = data.xpos[frame]
    rotation = data.xmat[frame]
    relative = [float(point_m[axis]) - float(origin[axis]) for axis in range(3)]
    return [
        sum(float(rotation[3 * other + axis]) * relative[other] for other in range(3))
        for axis in range(3)
    ]


def place_goal_followers(data: Any, followers: Any) -> None:
    """Write each coupled follower where its law puts it, in list order.

    ``CadexDynamics._place_goal_followers``, written down for ADR-084's
    reason and held to it by ``test_dynamics_goal_coupled`` (ADR-474).
    """

    for follower in followers:
        driver = follower["driver_qpos_adr"]
        offset = (
            0.0 if driver is None
            else float(data.qpos[int(driver)]) - float(follower["driver_reference"])
        )
        c = [float(value) for value in follower["polycoef"]]
        data.qpos[int(follower["qpos_adr"])] = float(follower["reference"]) + (
            c[0] + c[1] * offset + c[2] * offset**2 + c[3] * offset**3
            + c[4] * offset**4
        )


def draw_goals(mujoco: Any, model: Any, task: dict[str, Any], rng: Any) -> list[dict[str, Any]]:
    """One episode's goals, by the bundle's ``goal_algorithm``.

    A second implementation of ``CadexDynamics.draw_episode_goals``, here
    for the reason every other second implementation in this file is: the
    trainer cannot import the engine (ADR-084), so the copy is written down
    and ``test_dynamics_goal_trainer`` pins the two number for number. It
    runs on the host with stock ``mujoco`` and never on device.

    One row per goal, each ``{"label", "segments": [[...], ...]}``.
    """

    drawn: list[dict[str, Any]] = []
    data = None
    for entry in task.get("goal") or ():
        segments: list[list[float]] = []
        if str(entry["kind"]) == "waypoint":
            # ADR-751: a chain of legs from where the base starts.
            x, y = (float(value) for value in entry["start_mm"])
            direction = float(entry["heading_rad"])
            bearing = float(entry["bearing_deg"])
            for _ in range(int(entry["segments"])):
                leg = rng.uniform(float(entry["low"]), float(entry["high"]))
                direction += math.radians(rng.uniform(-bearing, bearing))
                x += leg * math.cos(direction)
                y += leg * math.sin(direction)
                segments.append([x, y])
            drawn.append({"label": str(entry["label"]), "segments": segments})
            continue
        if str(entry["kind"]) != "point":
            scripted = list(entry.get("sequence") or ())
            for index in range(int(entry["segments"])):
                bands = entry.get("bands")
                if not bands:
                    value = rng.uniform(float(entry["low"]), float(entry["high"]))
                else:
                    # ADR-824: pick a band by weight, then draw inside it.
                    pick = rng.random() * sum(float(band[2]) for band in bands)
                    for start, end, weight in bands:
                        if pick < float(weight):
                            break
                        pick -= float(weight)
                    value = rng.uniform(float(start), float(end))
                # ADR-721: a scripted segment takes its draw, holds its script.
                segments.append(
                    [float(scripted[index]) if index < len(scripted) else value]
                )
            drawn.append({"label": str(entry["label"]), "segments": segments})
            continue
        if data is None:
            data = mujoco.MjData(model)
        key = int(mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_KEY, str(task["episode"]["reset_keyframe"])
        ))
        resting = {(int(first), int(second))
                   for first, second in entry["resting_contacts"]}
        body = int(entry["body_id"])
        local = [float(value) for value in entry["local_m"]]
        floor = entry.get("min_z_m")
        apart = float(entry["min_separation_m"])
        previous = [float(value) for value in entry["start_m"]]
        for segment in range(int(entry["segments"])):
            point = kept = None
            for _ in range(int(entry["attempts"])):
                mujoco.mj_resetDataKeyframe(model, data, key)
                for joint in entry["joints"]:
                    data.qpos[int(joint["qpos_adr"])] = rng.uniform(
                        float(joint["low"]), float(joint["high"])
                    )
                place_goal_followers(data, entry.get("followers") or ())
                mujoco.mj_forward(model, data)
                candidate = goal_tip_m(data, body, local)
                if floor is not None and candidate[2] < float(floor):
                    continue
                if any(
                    (
                        min(int(data.contact[index].geom1),
                            int(data.contact[index].geom2)),
                        max(int(data.contact[index].geom1),
                            int(data.contact[index].geom2)),
                    ) not in resting
                    for index in range(int(data.ncon))
                ):
                    continue
                if math.dist(candidate, previous) < apart:
                    continue
                point = candidate
                if entry.get("frame_id") is not None:
                    kept = goal_in_frame_m(data, int(entry["frame_id"]), candidate)
                break
            if point is None:
                raise SystemExit(
                    f"goal {str(entry['label'])!r} found no reachable point in "
                    f"{int(entry['attempts'])} tries for segment {segment}; "
                    "the engine refuses the same draw, so this bundle's goal "
                    "cannot be trained as declared"
                )
            segments.append([
                value * float(entry["scale"])
                for value in (kept if entry.get("frame_id") is not None else point)
            ])
            previous = point
        drawn.append({"label": str(entry["label"]), "segments": segments})
    return drawn


def goal_segment(xp: Any, steps: Any, period: int, count: int) -> Any:
    """Which segment of a goal is in force after ``steps`` control steps.

    The bundle's rule and ``CadexDynamics.goal_values``: segment
    ``steps // resample_steps``, clamped to the last one, and segment 0 for
    a goal that is held (``resample_steps`` 0). Integer arithmetic on the
    episode's own step counter, never a comparison on elapsed seconds.

    ``xp`` is the array module, taken as an argument for the reason
    :func:`forward` takes ``jnp``, so it can be checked against the engine with
    ``numpy``, with no jax in the process.
    """

    if not period:
        return xp.zeros_like(steps)
    return xp.minimum(steps // period, count - 1)


def phase_channels(xp: Any, start: Any, since: Any, radians_per_step: float) -> Any:
    """A phase goal's two channels, ``sin`` then ``cos`` (ADR-598).

    The bundle's ``goal_algorithm`` and ``CadexDynamics.goal_values``: the
    segment's drawn start phase advanced ``radians_per_step`` for each of
    the ``since`` control steps taken in that segment. ``start`` carries the
    pooled value's trailing axis of one; the result has two there.
    """

    angle = start + float(radians_per_step) * xp.expand_dims(since, -1)
    return xp.concatenate([xp.sin(angle), xp.cos(angle)], axis=-1)


def goal_pool(mujoco: Any, xml: bytes, task: dict[str, Any], *,
              base_seed: int, count: int) -> list[list[list[list[float]]]]:
    """``count`` episodes of goals, one table per goal entry.

    Entry ``i`` of the result is ``[episode][segment][channel]``. One
    stream, in episode order, so the pool is a function of the bundle and
    the seed and nothing else. The model is compiled here from the bundle's
    own bytes and is not the batch's: a draw reads kinematics and contacts,
    which no randomisation entry moves.
    """

    entries = list(task.get("goal") or ())
    if not entries:
        return []
    if int(count) < 1:
        raise SystemExit(f"--goal-pool {count} holds no episode to train on")
    model = mujoco.MjModel.from_xml_string(xml.decode("utf-8"))
    rng = random.Random(int(base_seed))
    tables: list[list[list[list[float]]]] = [[] for _ in entries]
    for _ in range(int(count)):
        for table, row in zip(tables, draw_goals(mujoco, model, task, rng)):
            table.append(row["segments"])
    return tables


def randomised_models(mujoco: Any, np: Any, xml: bytes, task: dict[str, Any], *,
                      base_seed: int, count: int) -> tuple[Any, dict[str, Any]]:
    """Environment 0's host ``MjModel``, and each drawn field for every environment.

    The second value maps each field a randomisation entry moves to an array
    of shape ``(count, *field.shape)``: row ``i`` is that field after
    environment ``i``'s draw, ``random.Random(base_seed + i)``. A task with no
    randomisation returns an empty map.

    The XML is compiled once and each draw is made on a copy that is dropped
    as soon as its fields are read, so host memory is one model plus the
    drawn fields, whatever ``count`` is (ADR-695). It used to keep one host
    model per environment: a 12 MB Go1 model at 8,192 environments is about
    98 GB, and the B1 run reached 41 GB before its first iteration and was
    killed.

    ``mj_setConst`` after a draw is not optional: M6 phase 0 measured that
    ``body_subtreemass`` is derived from ``body_mass`` there, so a mass draw
    that skipped it would change the mass and not what the solver does with
    it.
    """

    base = mujoco.MjModel.from_xml_string(xml.decode("utf-8"))
    entries = list(task.get("randomisation") or ())
    if not entries:
        return base, {}
    fields = sorted({str(field["field"]) for entry in entries for field in entry["fields"]})
    drawn = {
        name: np.empty((count, *getattr(base, name).shape), dtype=getattr(base, name).dtype)
        for name in fields
    }
    host = base
    for index in range(count):
        model = copy.copy(base)
        rng = random.Random(int(base_seed) + index)
        data = mujoco.MjData(model)
        for entry in entries:
            factor = rng.uniform(float(entry["low"]), float(entry["high"]))
            for field in entry["fields"]:
                getattr(model, str(field["field"])).flat[
                    int(field["index"])
                ] *= factor
        mujoco.mj_setConst(model, data)
        for name in fields:
            drawn[name][index] = getattr(model, name)
        if index == 0:
            host = model
    return host, drawn


# ---------------------------------------------------------------------------
# The network. A tanh MLP actor with a separate critic, which is what the
# container's `network` object describes -- minus the critic, which is
# training scaffolding and is not part of a policy.
# ---------------------------------------------------------------------------


def layer_shapes(observations: int, actions: int, hidden: Sequence[int]) -> list[tuple[int, int]]:
    widths = [observations, *[int(width) for width in hidden], actions]
    return [(a, b) for a, b in zip(widths[:-1], widths[1:])]


def initial_parameters(jax: Any, jnp: Any, key: Any, shapes, *, gain: float = 1.0):
    """Layer weights and biases, LeCun-normal, last layer deliberately small.

    A small final layer is what makes the first rollouts near-zero action
    rather than saturated tanh: a policy that starts at its action limits
    learns nothing from its first thousand steps because every gradient is
    through a flat region.
    """

    parameters = []
    keys = jax.random.split(key, len(shapes))
    for index, ((inputs, outputs), subkey) in enumerate(zip(shapes, keys)):
        scale = gain / math.sqrt(inputs)
        if index == len(shapes) - 1:
            scale *= 0.01
        weight = jax.random.normal(subkey, (inputs, outputs), dtype=jnp.float32) * scale
        parameters.append((weight, jnp.zeros((outputs,), dtype=jnp.float32)))
    return parameters


def forward(jnp: Any, parameters, inputs, *, activation: str = "tanh"):
    """The actor's forward pass, in the layout the container's blob records.

    ``swish`` is ``x * sigmoid(x)``, flax's ``linen.swish`` (ADR-712).
    """

    value = inputs
    last = len(parameters) - 1
    for index, (weight, bias) in enumerate(parameters):
        value = value @ weight + bias
        if index < last:
            if activation == "tanh":
                value = jnp.tanh(value)
            elif activation == "swish":
                value = value / (1.0 + jnp.exp(-value))
            else:
                value = jnp.maximum(value, 0.0)
    return value


def flat_parameters(np: Any, parameters) -> list[float]:
    """The blob: each layer's weight matrix row-major, then its bias.

    Float32 on the way out, because that is what the container stores and
    what the engine will read back -- so the witness recorded beside these
    numbers is a witness about the values that actually land.
    """

    flat: list[float] = []
    for weight, bias in parameters:
        flat.extend(np.asarray(weight, dtype=np.float32).reshape(-1).tolist())
        flat.extend(np.asarray(bias, dtype=np.float32).reshape(-1).tolist())
    return flat


# ---------------------------------------------------------------------------
# The physics. MJX is the engine's machine only where the two agree.
# ---------------------------------------------------------------------------


def match_engine_actuator_derivative(mujoco: Any, jax: Any, jnp: Any) -> None:
    """Make MJX's ``implicitfast`` drop a clamped actuator's damping, as MuJoCo does.

    ADR-465. Every Cadex servo is a force-limited affine PD actuator, and
    under ``implicitfast`` both engines fold its ``-kv`` into the implicit
    step. Stock MuJoCo 3.10 -- the engine, which is what evaluates a policy
    -- leaves the term out for an actuator whose force sits at its
    ``forcerange``; MJX 3.10's ``deriv_smooth_vel`` keeps it always. A
    saturated servo was therefore extra-damped here and torque-limited
    there: ot11's r2 walk policy went forwards at +2.80 reward per step in
    this file's physics and backwards at -1.95 in the engine's, from the
    same reset. This subtracts the term back out for exactly the clamped
    actuators, which ``test_dynamics_mjx_forcelimit`` holds to stock MuJoCo
    at float64 round-off.

    It replaces a function in a private MJX module, which the pinned
    ``mujoco-mjx`` in ``requirements.txt`` is what makes tolerable; the same
    test fails loudly the day raw MJX agrees, and then this goes. Installing
    it twice is harmless.
    """

    from mujoco.mjx._src import derivative

    original = derivative.deriv_smooth_vel
    if getattr(original, "cadex_engine_rule", False):
        return
    affine = int(mujoco.mjtBias.mjBIAS_AFFINE)
    affine_gain = int(mujoco.mjtGain.mjGAIN_AFFINE)
    no_dynamics = int(mujoco.mjtDyn.mjDYN_NONE)
    no_actuation = int(mujoco.mjtDisableBit.mjDSBL_ACTUATION)

    def deriv_smooth_vel(m, d):
        qderiv = original(m, d)
        if qderiv is None or m.opt.disableflags & no_actuation:
            return qderiv
        # The same per-actuator velocity gain MJX just added...
        ctrl = d.ctrl.at[m.actuator_dyntype != no_dynamics].set(d.act)
        vel = (m.actuator_biasprm[:, 2] * (m.actuator_biastype == affine)
               + m.actuator_gainprm[:, 2] * (m.actuator_gaintype == affine_gain) * ctrl)
        # ...taken back out wherever the force is pinned at its limit.
        force = d.actuator_force
        clamped = jnp.logical_and(
            m.actuator_forcelimited,
            jnp.logical_or(force <= m.actuator_forcerange[:, 0],
                           force >= m.actuator_forcerange[:, 1]),
        )
        moment = d._impl.actuator_moment
        return qderiv - moment.T @ jax.vmap(jnp.multiply)(
            moment, jnp.where(clamped, vel, 0.0))

    deriv_smooth_vel.cadex_engine_rule = True
    derivative.deriv_smooth_vel = deriv_smooth_vel


# ---------------------------------------------------------------------------
# PPO.
# ---------------------------------------------------------------------------


def resolved_command_slew_deg(options) -> float:
    """ADR-162's limit in degrees, resolved once.

    Module level and not a local of ``train`` because ``policy_header`` needs
    the same number and the two are different scopes: the first draft read it
    as a local there and every run died in the header writer. Two spellings of
    a resolution rule are two rules.

    ``None``, absent, zero and negative all mean **no limit** and return 0.0 —
    the flag's OFF value, unlike the action filter's alpha where 0 would freeze
    the command and is refused.
    """

    value = getattr(options, "command_slew_deg", 0.0)
    if value is None:
        return 0.0
    value = float(value)
    if not math.isfinite(value):
        raise SystemExit(
            "--command-slew-deg must be a finite number of degrees. 0 (the "
            "default) is NO LIMIT.")
    return value if value > 0.0 else 0.0


def resolved_reward_floor(options) -> float | None:
    """ADR-700's per-step reward floor, resolved once, or ``None`` for none.

    Module level for ADR-162's reason: ``train`` and ``policy_header`` need
    the same number. ``None`` (the default) is NO FLOOR and emits the same
    graph a trainer without this flag emits; a number clamps each step's
    summed reward from below, the way MuJoCo Playground's locomotion tasks
    clip theirs at 0.
    """

    value = getattr(options, "reward_floor", None)
    if value is None:
        return None
    value = float(value)
    if not math.isfinite(value):
        raise SystemExit(
            "--reward-floor must be a finite reward per step. Leave it out "
            "for no floor.")
    return value


#: When a run has learned to end its own episodes (ADR-410). hex3
#: (2026-09-26) paid a net-negative reward for every step it survived, and
#: its mean episode fell from 28 steps to 2 of a 200-step horizon by
#: iteration ~80, then trained on for seven hours while reward/step "rose".
#: Iteration 0 is not in the baseline: no episode has ended by then, and the
#: trainer reports the whole unroll.
COLLAPSE_BASELINE = (1, 11)
COLLAPSE_WINDOW = 50
COLLAPSE_FRACTION = 0.05


def episode_collapse(curve: Sequence[dict[str, Any]], horizon: int) -> str:
    """Why the run's episodes have collapsed, or ``""`` when they have not.

    Collapsed means every one of the last :data:`COLLAPSE_WINDOW` iterations
    averaged under both :data:`COLLAPSE_FRACTION` of the horizon and half of
    the run's own early episode length: the policy is not failing to learn,
    it is learning that ending the episode pays.
    """

    first, last = COLLAPSE_BASELINE
    lengths = [min(float(entry["episode_steps"]), float(horizon)) for entry in curve]
    if len(lengths) < last + COLLAPSE_WINDOW:
        return ""
    baseline = sum(lengths[first:last]) / (last - first)
    window = lengths[-COLLAPSE_WINDOW:]
    if max(window) >= min(COLLAPSE_FRACTION * horizon, 0.5 * baseline):
        return ""
    return (
        f"episodes collapsed: the last {COLLAPSE_WINDOW} iterations averaged "
        f"at most {max(window):.1f} of {horizon} steps, against {baseline:.1f} "
        f"early in the run. The policy is ending its own episodes, which "
        "means a surviving step is worth less than a termination: add a "
        "positive per-step reward (an alive bonus) and size the costs so "
        "standing still nets positive."
    )


def build_environment(
    bundle: dict[str, Any],
    options: argparse.Namespace,
    *,
    count: int,
    seed: int,
    jax: Any,
    jnp: Any,
    np: Any,
    mujoco: Any,
    mjx: Any,
) -> Any:
    """The bundle's task as ``count`` batched MJX environments (ADR-712).

    Everything that makes a run *this task* is here and nowhere else: the
    observation slices, the action box, the command filter and slew, the
    sensor noise, the goals, the gait reference and its random start, the
    reset variation, the pushes, the randomised models, the reward, the
    terminations and the episode. What it returns is driven by Brax's PPO in
    :func:`train`, which owns none of those.

    ``seed`` seeds the host draws (randomised models, the goal pool), so two
    batches built from one bundle with different seeds do not share them.
    """

    from brax.envs.base import State

    table = globals_for(jnp)
    task = bundle["task"]
    episode = task["episode"]
    names = channels(task)
    # The actor reads the policy channels only; the critic and the running
    # normaliser see every channel, privileged ones included (ADR-408).
    actor_names = actor_channels(task)
    if not actor_names:
        raise SystemExit(
            "every observation in this task is privileged, so the policy "
            "would read nothing. Mark at least one sensor-grounded channel "
            "role='policy'."
        )
    actor_idx = np.asarray([names.index(name) for name in actor_names], dtype=np.int32)
    actions = list(task["actions"])

    low = jnp.asarray([float(a["low"]) for a in actions], dtype=jnp.float32)
    high = jnp.asarray([float(a["high"]) for a in actions], dtype=jnp.float32)
    ctrl_scale = jnp.asarray([float(a["scale"]) for a in actions], dtype=jnp.float32)
    ctrl_index = np.asarray([int(a["index"]) for a in actions], dtype=np.int32)
    output_scale = [(float(a["high"]) - float(a["low"])) / 2.0 for a in actions]
    output_bias = [(float(a["high"]) + float(a["low"])) / 2.0 for a in actions]

    # ADR-160: the command may be low-passed before it reaches `data.ctrl`.
    #
    # `alpha` is a PYTHON float and every branch on it below is taken at
    # TRACE time, not at run time. That is the whole design: at the default
    # 1.0 this file emits **exactly** the graph it emitted before the flag
    # existed -- no extra carry member, no `where`, no multiply -- so a run
    # at 1.0 is bitwise identical to one under the unmodified trainer, and
    # `test_action_filter.py` proves it rather than assuming it. A runtime
    # `jnp.where(alpha < 1.0, ...)` would have been shorter and would have
    # changed the graph for everybody.
    action_filter_alpha = float(options.action_filter_alpha)
    if not (0.0 < action_filter_alpha <= 1.0):
        raise SystemExit(
            f"--action-filter-alpha {action_filter_alpha:g} is outside "
            f"(0, 1]. At 0 the command is frozen at the first step of every "
            f"episode and the policy cannot act at all; above 1 the filter "
            f"extrapolates past the raw command and AMPLIFIES the "
            f"step-to-step change, which is the opposite of what it is for. "
            f"1.0 is no filter."
        )
    filtering = action_filter_alpha < 1.0

    # ADR-162. A SLEW LIMIT IS A DIFFERENT OPERATOR FROM THE EMA, and this
    # repository spent two experiments (021, 023) discovering that the hard
    # way. An EMA's per-step change is `alpha * |raw - previous|`, which on a
    # +/-25 deg box at alpha 0.65 is up to 32.5 deg in ONE control step: it
    # bounds the command's SMOOTHNESS and does not bound its RATE at all.
    # This clamps the rate directly, so the setpoint cannot run away from a
    # joint that physically reaches 12.53 deg per 40 ms control step.
    #
    # Degrees, because the command surface is degrees -- `actions[].unit` is
    # "deg" and `scale` is the pi/180 that follows the clamp. There is no new
    # conversion site; `test_dynamics_units` greps for exactly that.
    #
    # `None`/0 is NO LIMIT and takes the pre-ADR-162 branch, emitting the same
    # graph a trainer without this flag emits.
    command_slew_deg = resolved_command_slew_deg(options)
    slewing = command_slew_deg > 0.0
    if slewing:
        # A limit wider than the box can never bind: the whole command range
        # is `high - low`, so any step is at most that. Refusing is better
        # than silently training an unlimited run under a flag that says
        # otherwise -- 016 lost two clips to a literal that could not bind.
        widest = float(jnp.max(high - low))
        if command_slew_deg >= widest:
            raise SystemExit(
                f"--command-slew-deg {command_slew_deg:g} is at or above the "
                f"widest command range in this bundle ({widest:g} deg), so it "
                f"can never bind and the run would be unlimited under a flag "
                f"that claims a limit. Pick a value below {widest:g}.")
    # ADR-696: a task that observes a command reads the last two ISSUED
    # commands, so it carries them whether or not it filters. A PYTHON bool,
    # like the two above: a task with no command emits the graph it did.
    commanding = bool(task.get("commands"))
    # One carry serves every operator: the previous ISSUED command, per
    # environment, episode-local -- and, when commanding, the one before it.
    # Everything below that used to test `filtering` tests this instead.
    carrying = filtering or slewing or commanding
    # ADR-699: a PYTHON bool on the same terms; qacc is read, never carried.
    accelerating = bool(task.get("accelerations"))
    # ADR-706: a PYTHON bool on the same terms; the reference is a function
    # of the episode's step counter, so nothing new is carried.
    tracking = bool(task.get("tracking"))
    # ADR-709: a PYTHON bool on the same terms; each episode starts at its
    # own clip sample, carried beside the step counter it offsets.
    starting = tracking and task["tracking"].get("start") == "random"
    # ADR-752: a PYTHON bool on the same terms; a speed cadence's clock is
    # the cycles turned so far, carried beside the step counter.
    cadenced = tracking and bool(task["tracking"].get("cadence"))
    # ADR-773: a speed schedule's clock is carried the same way, and its
    # random start row is the stride nearest the opening command.
    scheduled = tracking and bool(task["tracking"].get("schedule"))
    cadenced = cadenced or scheduled
    # ADR-715: a PYTHON bool on the same terms; a scan is read from the
    # state's xpos and xmat, never carried.
    scanning = bool(task.get("scans"))

    # ADR-700: a PYTHON value branched on at trace time, so no floor is the
    # graph this trainer always emitted.
    reward_floor = resolved_reward_floor(options)
    reward_terms = [
        (float(term["weight"]),
         compile_expression(str(term["expression"]), names, table))
        for term in task["reward"]
    ]
    termination_terms = [
        (rule.get("above"), rule.get("below"),
         compile_expression(str(rule["expression"]), names, table))
        for rule in task["termination"]
    ]

    # The observation slices, as one gather. `adr`, `dim` and `scale` are all
    # in the file; nothing here knows what a degree is.
    gather = np.concatenate([
        np.arange(int(r["adr"]), int(r["adr"]) + int(r["dim"]))
        for r in task["observations"]
    ]) if task["observations"] else np.zeros((0,), dtype=np.int32)
    gather = jnp.asarray(gather, dtype=jnp.int32)
    obs_scale = jnp.asarray(
        [float(r["scale"]) for r in task["observations"] for _ in range(int(r["dim"]))],
        dtype=jnp.float32,
    )

    envs = int(count)
    host, drawn = randomised_models(mujoco, np, bundle["model_xml"], task,
                                    base_seed=int(seed), count=envs)
    key_id = mujoco.mj_name2id(host, mujoco.mjtObj.mjOBJ_KEY,
                               str(episode["reset_keyframe"]))
    if key_id < 0:
        raise SystemExit(
            f"the model carries no {episode['reset_keyframe']!r} keyframe"
        )
    reset_qpos = jnp.asarray(host.key_qpos[key_id], dtype=jnp.float32)
    # ADR-696: the command the reset holds, in each action's surface unit and
    # box -- ``CadexDynamics.reset_command``. Both carried commands start
    # here, so an episode's first reported rate is zero.
    reset_command = jnp.clip(
        jnp.asarray(host.key_ctrl[key_id][ctrl_index], dtype=jnp.float32)
        / ctrl_scale, low, high)
    reset_qvel = jnp.zeros((host.nv,), dtype=jnp.float32)
    if starting:
        # ADR-709: the clip's state at each sample, which replaces the
        # keyframe's -- ``CadexDynamics.apply_reference_start``.
        start_qpos = jnp.asarray(task["tracking"]["reset_qpos"], dtype=jnp.float32)
        start_qvel = jnp.asarray(task["tracking"]["reset_qvel"], dtype=jnp.float32)
        start_samples = int(task["tracking"]["samples"])

    def scheduled_origin(sample, picks):
        """ADR-773: the start row of the stride nearest each opening command."""

        if not scheduled:
            return sample
        return schedule_nearest(jnp, task, goals_at(picks, jnp.zeros_like(sample))) \
            * start_samples + sample

    nbody = int(host.nbody)

    # ADR-715: the ground the scans read is the elevation the model collides with.
    scan_elevation = (jnp.asarray(host.hfield_data, dtype=jnp.float32)
                      if scanning and (task.get("terrain") or {}).get("kind") == "heightfield"
                      else None)
    # ADR-717: a PYTHON bool on the same terms; a course re-drawn per
    # episode is an index carried beside the step counter, and the terrain
    # geoms are placed from it wherever the model is used.
    redrawing = bool((task.get("terrain") or {}).get("pool"))
    if redrawing:
        pool = terrain_pool(np, task["terrain"])
        pool_size = int(pool["lowest"].shape[0])
        plane_geom = mujoco.mj_name2id(host, mujoco.mjtObj.mjOBJ_GEOM, "environment/terrain")
        slot_geoms = np.asarray([
            mujoco.mj_name2id(host, mujoco.mjtObj.mjOBJ_GEOM, f"environment/terrain/{index}")
            for index in range(int(task["terrain"]["slots"]))], dtype=np.int32)
        dome_geoms = np.asarray([
            mujoco.mj_name2id(host, mujoco.mjtObj.mjOBJ_GEOM, f"environment/terrain/dome/{index}")
            for index in range(int(task["terrain"].get("dome_slots") or 0))], dtype=np.int32)
        if plane_geom < 0 or (slot_geoms < 0).any() or (dome_geoms < 0).any():
            raise SystemExit(
                "the bundle's terrain pool names geoms the model does not carry: "
                f"environment/terrain, {len(slot_geoms)} environment/terrain/<i> and "
                f"{len(dome_geoms)} environment/terrain/dome/<j>")
        pool_device = {key: jnp.asarray(value, dtype=jnp.float32)
                       for key, value in pool.items()}

    def placed(m, course):
        return place_course(m, pool_device, slot_geoms, plane_geom, course, dome_geoms)

    def scanned_course(course):
        """``height_scan_vector``'s ``course`` for these course indices."""

        return ((pool_device["scan"][course], pool_device["lowest"][course],
                 pool_device["dome_scan"][course]) if redrawing else None)

    single = mjx.put_model(host)
    model = single
    if drawn and envs > 1:
        # Only the fields a draw actually moved are batched; everything else
        # is shared, which is what keeps the batched model the size of one.
        for field, values in drawn.items():
            if tuple(values.shape[1:]) != tuple(getattr(single, field).shape):
                raise SystemExit(
                    f"randomised field {field!r} is {tuple(values.shape[1:])} on "
                    f"the host model but {tuple(getattr(single, field).shape)} "
                    "in MJX, so its draws cannot be batched")
        model = model.tree_replace({
            field: jnp.asarray(values, dtype=getattr(single, field).dtype)
            for field, values in drawn.items()
        })
        model_axes = jax.tree.map(lambda _: None, single).tree_replace(
            {field: 0 for field in drawn}
        )
    else:
        model_axes = None

    per_action = int(episode["solver_steps_per_action"])
    # The episode the *bundle* declares, and the only horizon this file may
    # use. It is read here and enforced in `rollout`'s scan; for two runs it
    # was read here and never used again, and an environment whose policy did
    # not fall over therefore never reset -- see ADR-101. A constant would be
    # a second declaration of the episode, and the engine's
    # ``evaluate_episode`` would be honouring the other one.
    horizon = int(episode["max_steps"])

    # -- ADR-462: what each episode is asking for ---------------------------
    #
    # `goaled` is a PYTHON bool and every branch on it is taken at trace
    # time, exactly as `carrying` is below: a task with no goal emits the
    # graph, the carry and the key splits it always did.
    goal_entries = list(task.get("goal") or ())
    goaled = bool(goal_entries)
    goal_tables = [
        jnp.asarray(table, dtype=jnp.float32)
        for table in goal_pool(
            mujoco, bundle["model_xml"], task,
            base_seed=int(seed),
            count=int(getattr(options, "goal_pool", 4096)),
        )
    ]
    goal_periods = [int(entry["resample_steps"]) for entry in goal_entries]
    # ADR-773: a goal's ramp between segments, in steps; 0 steps at once.
    goal_ramps = [int(entry.get("ramp_steps") or 0) for entry in goal_entries]
    # ADR-598: a phase goal's turn per step; None for a goal that is held.
    goal_turns = [
        float(entry["radians_per_step"]) if entry["kind"] == "phase" else None
        for entry in goal_entries
    ]
    goal_pool_size = int(goal_tables[0].shape[0]) if goaled else 0
    # ADR-751: a PYTHON bool, so a task with no waypoint traces as before.
    waypointed = any(entry["kind"] == "waypoint" for entry in goal_entries)

    def goals_at(picks, steps):
        """Each environment's goal channels at its own episode step.

        ``picks`` is which pooled episode an environment holds and ``steps``
        how many control steps of it have been taken. A phase goal's pooled
        value is its segment's start, turned to the step here.
        """

        told = []
        for pooled, period, turn, ramp in zip(goal_tables, goal_periods, goal_turns,
                                              goal_ramps):
            segment = goal_segment(jnp, steps, period, pooled.shape[1])
            held = pooled[picks, segment]
            if ramp:
                # ADR-773: from the segment before, in a straight line.
                before = pooled[picks, jnp.maximum(segment - 1, 0)]
                share = jnp.minimum(1.0, (steps - segment * period + 1) / float(ramp))
                held = before + (held - before) * share[..., None].astype(held.dtype)
            if turn is not None:
                held = phase_channels(jnp, held, steps - segment * period, turn)
            told.append(held)
        return jnp.concatenate(told, axis=-1)

    # ADR-588: a tracked position reads as its tracker reports it, and
    # (ADR-591) a load as its load sensor does. `sensing` is a PYTHON bool,
    # so a task with neither emits the graph -- and draws the key stream --
    # it always did.
    noise_std = jnp.asarray(sensor_noise_std(task), dtype=jnp.float32)
    # ADR-698: a contact channel derives its down flag here too, noise or not.
    sensing = int(noise_std.shape[0]) > 0 or any(
        record.get("contact") for record in task["observations"])

    def observe(data, noise=None):
        raw = jnp.take(data.sensordata, gather) * obs_scale
        if not sensing:
            return raw
        parts, cursor, drawn, flags = [], 0, 0, {}
        for record in task["observations"]:
            dim = int(record["dim"])
            segment = raw[cursor:cursor + dim]
            cursor += dim
            if record.get("in_range_of"):
                # ADR-590: gated by the paired position's flag, read above.
                parts.append(tracker_velocity_reading(
                    jnp, segment, record["tracker"], flags[record["in_range_of"]],
                    None if noise is None else noise[drawn:drawn + dim]))
                drawn += dim
            elif record.get("tracker"):
                parts.append(tracker_reading(
                    jnp, segment, record["tracker"],
                    None if noise is None else noise[drawn:drawn + dim]))
                flags[record["name"]] = parts[-1][dim]
                drawn += dim
            elif record.get("load"):
                parts.append(load_reading(
                    jnp, segment, record["load"],
                    None if noise is None else noise[drawn:drawn + dim]))
                drawn += dim
            elif record.get("contact"):
                parts.append(contact_reading(jnp, segment, record["contact"]))
            else:
                parts.append(segment)
        return jnp.concatenate(parts)

    def named(vector):
        return {name: vector[index] for index, name in enumerate(names)}

    def reward_of(vector):
        values = named(vector)
        total = jnp.float32(0.0)
        for weight, code in reward_terms:
            total = total + weight * eval(code, table, dict(values))
        if reward_floor is not None:
            total = jnp.maximum(total, jnp.float32(reward_floor))
        return total

    def done_of(vector):
        values = named(vector)
        flag = jnp.bool_(False)
        for above, below, code in termination_terms:
            value = eval(code, table, dict(values))
            if above is not None:
                flag = jnp.logical_or(flag, value > float(above))
            if below is not None:
                flag = jnp.logical_or(flag, value < float(below))
        return flag

    # -- M9: the episode stops starting in the same place ------------------
    #
    # Three functions, and every line of arithmetic in them is a second
    # implementation of ``CadexDynamics._write_reset_variation``,
    # ``draw_episode_variation`` and ``apply_disturbance``. Written out in
    # ``jnp`` rather than shared, for the reason this file's reward whitelist
    # and ``encode_policy`` are written out: it cannot import the engine
    # (ADR-084), so the second copy is written down; change both together.
    variation_entries = list(task.get("reset_variation") or ())
    push_entries = list(task.get("disturbance") or ())

    def varied_reset(key, origin=None):
        """One reset pose per environment, each with its own draw.

        ``origin`` is each environment's clip sample when the task starts at
        a random phase of its reference (ADR-709): that sample's state is the
        pose the draws compose onto, their velocities added to its own.

        The tilt quaternion is left-multiplied onto the base's own, which is
        a world-frame rotation about the base's frame origin -- so the whole
        mechanism swings rigidly and every joint angle stays where the solve
        left it. Joint angles are never touched here and there is no code
        path that could: the reset pose is the solved one with the soles on
        the floor, and a few degrees at a knee is a foot through it.
        """

        if origin is None:
            qpos = jnp.tile(reset_qpos, (envs, 1))
            qvel = jnp.tile(reset_qvel, (envs, 1))
        else:
            qpos = start_qpos[origin]
            qvel = start_qvel[origin]
        for entry in variation_entries:
            key, k_tilt, k_azimuth, k_height, k_spin, k_speed, k_way = (
                jax.random.split(key, 7)
            )
            tilt = jax.random.uniform(
                k_tilt, (envs,), dtype=jnp.float32,
                minval=float(entry["tilt_low_rad"]),
                maxval=float(entry["tilt_high_rad"]),
            )
            azimuth = jax.random.uniform(
                k_azimuth, (envs,), dtype=jnp.float32,
                minval=0.0, maxval=2.0 * math.pi,
            )
            height = jax.random.uniform(
                k_height, (envs,), dtype=jnp.float32,
                minval=float(entry["height_low_m"]),
                maxval=float(entry["height_high_m"]),
            )
            spin = jax.random.uniform(
                k_spin, (envs, 3), dtype=jnp.float32,
                minval=float(entry["angular_velocity_low_rad_s"]),
                maxval=float(entry["angular_velocity_high_rad_s"]),
            )
            # The stumble: a speed and a direction, drawn whether or not the
            # bundle declares any, because a branch here is a branch in the
            # stream's position.
            speed = jax.random.uniform(
                k_speed, (envs,), dtype=jnp.float32,
                minval=float(entry.get("linear_velocity_low_m_s") or 0.0),
                maxval=float(entry.get("linear_velocity_high_m_s") or 0.0),
            )
            speed_azimuth = jax.random.uniform(
                k_way, (envs,), dtype=jnp.float32,
                minval=0.0, maxval=2.0 * math.pi,
            )
            adr = int(entry["qpos_adr"])
            half = 0.5 * tilt
            sine = jnp.sin(half)
            tw = jnp.cos(half)
            tx = sine * jnp.cos(azimuth)
            ty = sine * jnp.sin(azimuth)
            qw, qx = qpos[:, adr + 3], qpos[:, adr + 4]
            qy, qz = qpos[:, adr + 5], qpos[:, adr + 6]
            # Hamilton product, wxyz, with the tilt axis horizontal so its z
            # term is identically zero.
            qpos = qpos.at[:, adr + 3].set(tw * qw - tx * qx - ty * qy)
            qpos = qpos.at[:, adr + 4].set(tw * qx + tx * qw - ty * qz)
            qpos = qpos.at[:, adr + 5].set(tw * qy + tx * qz + ty * qw)
            qpos = qpos.at[:, adr + 6].set(tw * qz - tx * qy + ty * qx)
            qpos = qpos.at[:, adr + 2].add(height)
            dof = int(entry["qvel_adr"])
            # The base's own frame, which is where MuJoCo keeps a free
            # joint's angular velocity (M9 phase 0)...
            # Added to what the reset holds (ADR-709), which is zero unless
            # the episode starts inside a reference.
            qvel = qvel.at[:, dof + 3 : dof + 6].add(spin)
            # ...and the WORLD frame, three numbers earlier in the same
            # array, which is where it keeps the linear one.
            qvel = qvel.at[:, dof + 0].add(speed * jnp.cos(speed_azimuth))
            qvel = qvel.at[:, dof + 1].add(speed * jnp.sin(speed_azimuth))
        return key, qpos, qvel

    def drawn_pushes(key):
        """This episode's forces and start times, per environment.

        Always three draws per entry, sustained or not, so that the stream's
        position never depends on a branch -- the same deliberate waste the
        engine's stream carries, and for the same reason.
        """

        forces, starts = [], []
        for entry in push_entries:
            key, k_size, k_way, k_when = jax.random.split(key, 4)
            magnitude = jax.random.uniform(
                k_size, (envs,), dtype=jnp.float32,
                minval=float(entry["newtons_low"]),
                maxval=float(entry["newtons_high"]),
            )
            drawn = jax.random.uniform(
                k_way, (envs,), dtype=jnp.float32,
                minval=0.0, maxval=2.0 * math.pi,
            )
            # Folded into the arc the task declares, with no draw of its own
            # -- the engine does exactly this, and on the full circle it is
            # the identity, so a task that narrows nothing is unchanged.
            arc_low = float(entry.get("azimuth_low_rad") or 0.0)
            arc_high = float(entry.get("azimuth_high_rad", 2.0 * math.pi))
            azimuth = arc_low + drawn * ((arc_high - arc_low) / (2.0 * math.pi))
            starts.append(
                jax.random.uniform(
                    k_when, (envs,), dtype=jnp.float32,
                    minval=float(entry["at_low_s"]),
                    maxval=float(entry["at_high_s"]),
                )
            )
            zero = jnp.zeros_like(magnitude)
            if str(entry["direction"]) == "vertical":
                sign = jnp.where(azimuth < math.pi, 1.0, -1.0)
                forces.append(jnp.stack([zero, zero, magnitude * sign], axis=-1))
            else:
                forces.append(
                    jnp.stack(
                        [magnitude * jnp.cos(azimuth),
                         magnitude * jnp.sin(azimuth),
                         zero],
                        axis=-1,
                    )
                )
        if not push_entries:
            return key, jnp.zeros((envs, 0, 3)), jnp.zeros((envs, 0))
        return key, jnp.stack(forces, axis=1), jnp.stack(starts, axis=1)

    def applied_forces(forces, starts, elapsed):
        """``xfrc_applied`` for this control step, written from zero.

        At the body's centre of mass in the world frame, which is what phase
        0 measured ``xfrc_applied`` to mean. From zero rather than
        accumulated, so a window that closed stops pushing.

        ``elapsed`` is an **episode-local** clock carried in the scan rather
        than ``data.time``, because this trainer's reset does not rewind
        ``data.time`` -- an environment on its fortieth episode would test a
        1.0 s shove window against a clock reading 240.
        """

        xfrc = jnp.zeros((envs, nbody, 6), dtype=jnp.float32)
        for index, entry in enumerate(push_entries):
            if bool(entry["sustained"]):
                live = jnp.ones_like(elapsed)
            else:
                start = starts[:, index]
                live = jnp.logical_and(
                    elapsed >= start,
                    elapsed < start + float(entry["duration_s"]),
                ).astype(jnp.float32)
            xfrc = xfrc.at[:, int(entry["body_id"]), :3].add(
                forces[:, index, :] * live[:, None]
            )
        return xfrc

    def step_env(m, data, surface, *extra):
        """One control step: clamp, scale into ctrl, integrate, observe, score.

        ``extra`` is the goal this step was taken under, when the task has
        one, then ADR-160's filter state, when it filters. The landed
        observation carries that same goal: a reward is judged against what
        the policy was asked when it acted, which is the engine's rule.

        **The only unit arithmetic on this boundary is the bundle's own
        ``clamp then x scale``**, which is the same two operations
        ``CadexDynamics.evaluate_episode`` performs. M7 adds no conversion
        site, here or anywhere, and ``test_dynamics_units`` greps this file
        to keep that true.
        """

        if redrawing:
            # ADR-717: this environment's course, in front of the goal.
            course, *extra = extra
            m = placed(m, course)
        told = extra[0] if goaled else None
        filter_state = extra[1:] if goaled else extra
        # ADR-706: the reference where this step lands, after the goal.
        if tracking:
            tracked, *filter_state = filter_state
        clamped = jnp.clip(surface, low, high)
        if commanding:
            # ADR-696's second carried command rides after `(previous, first)`.
            *filter_state, before = filter_state
        if carrying:
            # AFTER the clamp, so the filter's memory only ever holds a
            # command the actuator could actually have been given, and the
            # convex combination of two in-box commands is itself in box --
            # no second clamp is needed and none is applied.
            #
            # `first` is the episode's own step counter being zero, so the
            # first command of every episode passes through UNFILTERED.
            # Seeding from zero instead would spend the first tau of every
            # episode ramping out of a posture the policy never asked for,
            # inside the reset drop.
            previous, first = filter_state
            if filtering:
                clamped = jnp.where(
                    first, clamped,
                    action_filter_alpha * clamped
                    + (1.0 - action_filter_alpha) * previous)
            if slewing:
                # AFTER the EMA, so the two compose in the same order the
                # harness composes them (`harness/_policy.py`): the rate limit
                # is the last thing between the policy and the actuator, and
                # what it bounds is what the actuator actually receives. The
                # other order would rate-limit a signal the EMA then smooths
                # back across the limit, which is not a rate limit.
                #
                # Still in box: `previous` is in box and this moves at most
                # `command_slew_deg` toward another in-box value, so the
                # result lies between them. No second clamp is applied.
                clamped = jnp.where(
                    first, clamped,
                    jnp.clip(clamped, previous - command_slew_deg,
                             previous + command_slew_deg))
        ctrl = data.ctrl.at[ctrl_index].set(clamped * ctrl_scale)
        data = data.replace(ctrl=ctrl)

        def one(d, _):
            return mjx.step(m, d), None

        data, _ = jax.lax.scan(one, data, None, length=per_action)
        vector = observe(data)
        if goaled:
            if waypointed:
                # ADR-751: read from where the step landed.
                told = waypoint_vector(jnp, task, told, data.xipos, data.xmat)
            vector = jnp.concatenate([vector, told])
        if commanding:
            # The command just issued replaces `previous`; on an episode's
            # first step it replaces the reset's and reports no rate, as
            # `CadexDynamics.evaluate_episode` does.
            replaced = jnp.where(first, clamped, previous)
            vector = jnp.concatenate(
                [vector, command_vector(jnp, task, clamped, replaced)])
        if accelerating:
            # ADR-699: the acceleration of the step's last solver step.
            vector = jnp.concatenate(
                [vector, acceleration_vector(jnp, task, data.qacc)])
        if tracking:
            vector = jnp.concatenate([vector, tracked])
        if scanning:
            # ADR-715: the ground round where the step landed.
            vector = jnp.concatenate([vector, height_scan_vector(
                jnp, task, data.xpos, data.xmat, scan_elevation,
                scanned_course(course) if redrawing else None)])
        if commanding:
            return (data, vector, reward_of(vector), done_of(vector), clamped,
                    replaced)
        if carrying:
            # The ISSUED command joins the outputs, because it is the next
            # step's filter state and there is nowhere else to get it: it is
            # not recoverable from `data.ctrl`, which holds it multiplied by
            # the actuator scale.
            return data, vector, reward_of(vector), done_of(vector), clamped
        return data, vector, reward_of(vector), done_of(vector)

    # `(previous, first)` are per environment, so they vmap on axis 0 like
    # `surface`. Empty at alpha 1.0, which is what keeps the traced signature
    # identical to the pre-ADR-160 one.
    _filter_axes = (0, 0) if carrying else ()
    # ADR-696's second carried command, after `(previous, first)`.
    if commanding:
        _filter_axes = _filter_axes + (0,)
    # ADR-462's goal is per environment too, and sits in front of the filter
    # state; empty for a task with no goal, on the same terms.
    _goal_axes = (0,) if goaled else ()
    # ADR-706's landed reference is per environment, after the goal.
    if tracking:
        _goal_axes = _goal_axes + (0,)
    # ADR-717's course is per environment, in front of the goal.
    _course_axes = (0,) if redrawing else ()
    batched_step = (
        jax.vmap(step_env, in_axes=(None, 0, 0) + _course_axes + _goal_axes + _filter_axes)
        if model_axes is None
        else jax.vmap(step_env,
                      in_axes=(model_axes, 0, 0) + _course_axes + _goal_axes + _filter_axes)
    )
    if redrawing:
        batched_forward = jax.vmap(
            lambda m, d, course: mjx.forward(placed(m, course), d),
            in_axes=(model_axes, 0, 0))
    else:
        batched_forward = (
            jax.vmap(mjx.forward, in_axes=(None, 0)) if model_axes is None
            else jax.vmap(mjx.forward, in_axes=(model_axes, 0))
        )

    actor_take = jnp.asarray(actor_idx)
    control_interval = float(episode["control_interval_s"])
    scale_out = jnp.asarray(output_scale, dtype=jnp.float32)
    bias_out = jnp.asarray(output_bias, dtype=jnp.float32)

    def sensed(key, data, picks, steps, origin, carry, course=None, turned=None):
        """The observation the policy acts on, in the state ``data`` holds.

        What the policy acts on carries its sensors' noise; the reward and
        the terminations, scored in ``step_env`` on the landed reading, do
        not. ``steps`` is the count of steps ALREADY taken, so a goal and a
        reference here are the ones in force for the step about to be taken.
        """

        if sensing:
            key, sense_key = jax.random.split(key)
            noise = jax.random.normal(
                sense_key, (envs, int(noise_std.shape[0])),
                dtype=jnp.float32) * noise_std
            vector = jax.vmap(observe)(data, noise)
        else:
            vector = jax.vmap(observe)(data)
        told = None
        if goaled:
            told = goals_at(picks, steps)
            if waypointed:
                # ADR-751: the point read from where the base is.
                told = waypoint_vector(jnp, task, told, data.xipos, data.xmat)
            vector = jnp.concatenate([vector, told], axis=-1)
        if commanding:
            # ADR-696: the command in force and the one it replaced.
            vector = jnp.concatenate(
                [vector, command_vector(jnp, task, *carry)], axis=-1)
        if accelerating:
            # ADR-699: the critic's; the actor never reads it.
            vector = jnp.concatenate(
                [vector, acceleration_vector(jnp, task, data.qacc)], axis=-1)
        if tracking:
            # ADR-706: the clock the policy acts on.
            vector = jnp.concatenate(
                [vector, tracking_vector(jnp, task, steps, origin, turned, told)], axis=-1)
        if scanning:
            # ADR-715: the critic's, and the actor's when role: policy (ADR-748).
            vector = jnp.concatenate([vector, height_scan_vector(
                jnp, task, data.xpos, data.xmat, scan_elevation,
                scanned_course(course) if redrawing else None)], axis=-1)
        return key, vector

    def observation(vector):
        """Brax's two observation keys (ADR-712): the actor reads the policy
        channels and the critic every channel, privileged ones included
        (ADR-408)."""

        return {"state": jnp.take(vector, actor_take, axis=-1),
                "privileged_state": vector}

    def reset(key):
        """A fresh batch: every environment drawn like every later episode.

        It would be easy to start the batch at the nominal pose and only vary
        on reset; that would make the first unroll of training the one
        episode M9 exists to stop happening.
        """

        key, start_key = jax.random.split(key)
        make = jax.vmap(lambda _: mjx.make_data(single))(jnp.arange(envs))
        # ADR-709: folded from the start key, so a task that starts at phase
        # 0 draws the stream it always did.
        origin = (jax.random.randint(jax.random.fold_in(start_key, 709), (envs,),
                                     0, start_samples) if starting else None)
        early = None
        if starting and scheduled:
            # ADR-773: the goals first, so the start row can follow the command.
            early = jax.random.randint(jax.random.fold_in(start_key, 773), (envs,),
                                       0, goal_pool_size)
            origin = scheduled_origin(origin, early)
        start_key, qpos, qvel = varied_reset(start_key, origin)
        pick_key, forces, starts = drawn_pushes(start_key)
        # ADR-717: folded from the start key, like ADR-709's origin, so a
        # task on one course draws the stream it always did.
        course = (jax.random.randint(jax.random.fold_in(start_key, 717), (envs,),
                                     0, pool_size) if redrawing else None)
        course_args = (course,) if redrawing else ()
        data = batched_forward(model, make.replace(qpos=qpos, qvel=qvel), *course_args)
        steps = jnp.zeros((envs,), dtype=jnp.int32)
        info = {"forces": forces, "starts": starts,
                "elapsed": jnp.zeros((envs,), dtype=jnp.float32),
                "steps": steps,
                "truncation": jnp.zeros((envs,), dtype=jnp.float32),
                "terminated": jnp.zeros((envs,), dtype=jnp.float32),
                "nonfinite": jnp.zeros((envs,), dtype=jnp.float32)}
        picks = None
        if goaled:
            picks = (early if early is not None
                     else jax.random.randint(pick_key, (envs,), 0, goal_pool_size))
            info["picks"] = picks
        if starting:
            info["origin"] = origin
        if redrawing:
            info["course"] = course
        turned = jnp.zeros((envs,), dtype=jnp.float32) if cadenced else None
        if cadenced:
            info["turned"] = turned
        carry = ()
        if carrying:
            # The previous ISSUED command, per environment and episode-local
            # (ADR-160, ADR-162). Never read on an episode's first step.
            carry = (jnp.zeros((envs, len(actions)), dtype=jnp.float32),)
        if commanding:
            # ADR-696: both carried commands start at the reset's.
            carry = (jnp.tile(reset_command, (envs, 1)),) * 2
        info["carry"] = carry
        key, vector = sensed(key, data, picks, steps, origin, carry, course, turned)
        info["key"] = key
        return State(pipeline_state=data, obs=observation(vector),
                     reward=jnp.zeros((envs,), dtype=jnp.float32),
                     done=jnp.zeros((envs,), dtype=jnp.float32),
                     metrics={}, info=info)

    def step(state, action):
        """One control step of every environment, reset where it ended.

        ``action`` is the policy's squashed output in [-1, 1]; the bundle's
        box is ``action * output_scale + output_bias``, the same map the
        engine applies to ``tanh`` of the network's output.

        ``done`` ends the episode either way. ``truncation`` marks the ones
        that ended only because the horizon came (ADR-101): Brax's GAE masks
        those steps and bootstraps the step before from the critic, rather
        than teaching it that surviving to the horizon is worth as much as
        falling over.
        """

        info = state.info
        data = state.pipeline_state
        key = info["key"]
        forces, starts = info["forces"], info["starts"]
        elapsed, steps = info["elapsed"], info["steps"]
        picks = info.get("picks")
        origin = info.get("origin")
        course = info.get("course")
        carry = info["carry"]
        surface = action * scale_out + bias_out
        told = goals_at(picks, steps) if goaled else None
        goal_args = ((course,) if redrawing else ()) + ((told,) if goaled else ())
        turned = None
        if cadenced:
            # ADR-752: the clock turns at the cadence of the command in force.
            turned = info["turned"] + tracking_turn(jnp, task, told)
            turned = turned - jnp.floor(turned)
        if tracking:
            # ADR-706: the reference one step on, where the step will land.
            goal_args = goal_args + (
                tracking_vector(jnp, task, steps + 1, origin, turned, told),)
        if push_entries:
            data = data.replace(xfrc_applied=applied_forces(forces, starts, elapsed))
        if commanding:
            data, landed, reward, terminated, issued, replaced = batched_step(
                model, data, surface, *goal_args, carry[0], steps == 0, carry[1])
        elif carrying:
            # `steps == 0` is exactly the first step of an episode, so the
            # first command of every episode passes through unfiltered.
            data, landed, reward, terminated, issued = batched_step(
                model, data, surface, *goal_args, carry[0], steps == 0)
        else:
            data, landed, reward, terminated = batched_step(
                model, data, surface, *goal_args)
        # ADR-735: an environment whose physics, readings or reward went
        # non-finite ends here as a fall, scores nothing, and is reset with a
        # clean solver warm start. Without this one environment's NaN reaches
        # the batch's advantages and the whole run diverges (orun7 r1-t5, at
        # iteration 2). The count travels in `info` for the log.
        blown = jnp.logical_not(
            jnp.isfinite(data.qpos).all(axis=-1) & jnp.isfinite(data.qvel).all(axis=-1)
            & jnp.isfinite(landed).all(axis=-1) & jnp.isfinite(reward))
        terminated = jnp.logical_or(terminated, blown)
        reward = jnp.where(blown, 0.0, reward)
        elapsed = elapsed + control_interval
        steps = steps + 1
        # An integer compare, not a float one on `elapsed`: 600 additions of
        # a 0.02 s interval do not land on 12.0.
        timeout = steps >= horizon
        done = jnp.logical_or(terminated, timeout)
        truncation = jnp.logical_and(timeout, jnp.logical_not(terminated))

        # Every environment redraws every step and the draw is *selected*
        # where done: under `vmap` a branch per environment is not a shape a
        # jitted batch can take.
        key, reset_key, push_key = jax.random.split(key, 3)
        fresh_origin = (jax.random.randint(jax.random.fold_in(reset_key, 709), (envs,),
                                           0, start_samples) if starting else None)
        fresh_picks = None
        if starting and scheduled:
            # ADR-773: the next episode's goals first, as at the reset.
            fresh_picks = jax.random.randint(jax.random.fold_in(reset_key, 773), (envs,),
                                             0, goal_pool_size)
            fresh_origin = scheduled_origin(fresh_origin, fresh_picks)
        _unused, fresh_qpos, fresh_qvel = varied_reset(reset_key, fresh_origin)
        _unused, fresh_forces, fresh_starts = drawn_pushes(push_key)
        if redrawing:
            # ADR-717: an episode that ended starts its next on a fresh course.
            course = jnp.where(done, jax.random.randint(
                jax.random.fold_in(reset_key, 717), (envs,), 0, pool_size), course)
        course_args = (course,) if redrawing else ()

        def where_done(new, old):
            return jnp.where(done.reshape((-1,) + (1,) * (new.ndim - 1)), new, old)

        reset_data = data.replace(qpos=where_done(fresh_qpos, data.qpos),
                                  qvel=where_done(fresh_qvel, data.qvel),
                                  # A blown environment's warm start is NaN
                                  # too, and the solver would start from it.
                                  qacc_warmstart=where_done(
                                      jnp.zeros_like(data.qacc_warmstart),
                                      data.qacc_warmstart))
        # A reset environment's readings must be of its NEW pose (ADR-712):
        # forward runs only when something ended, and its result is taken
        # only where it did, so an environment that carries on keeps exactly
        # the post-step readings `mjx.step` left -- the ones the engine's
        # evaluator reads.
        data = jax.lax.cond(
            jnp.any(done),
            lambda d: jax.tree.map(where_done, batched_forward(model, d, *course_args), d),
            lambda d: d,
            reset_data)
        forces = jnp.where(done[:, None, None], fresh_forces, forces)
        starts = jnp.where(done[:, None], fresh_starts, starts)
        elapsed = jnp.where(done, 0.0, elapsed)
        steps = jnp.where(done, 0, steps)
        info = dict(info)
        if goaled:
            key, pick_key = jax.random.split(key)
            picks = jnp.where(
                done, fresh_picks if fresh_picks is not None
                else jax.random.randint(pick_key, (envs,), 0, goal_pool_size), picks)
            info["picks"] = picks
        if starting:
            origin = jnp.where(done, fresh_origin, origin)
            info["origin"] = origin
        if redrawing:
            info["course"] = course
        if cadenced:
            turned = jnp.where(done, 0.0, turned)
            info["turned"] = turned
        if carrying:
            carry = (jnp.where(done[:, None], 0.0, issued),)
        if commanding:
            # ADR-696: a fresh episode starts both at the reset's command,
            # because unlike the filter's memory these are observed.
            carry = (jnp.where(done[:, None], reset_command[None, :], issued),
                     jnp.where(done[:, None], reset_command[None, :], replaced))
        key, vector = sensed(key, data, picks, steps, origin, carry, course, turned)
        info.update(key=key, forces=forces, starts=starts, elapsed=elapsed,
                    steps=steps, carry=carry,
                    truncation=truncation.astype(jnp.float32),
                    terminated=terminated.astype(jnp.float32),
                    nonfinite=blown.astype(jnp.float32))
        return State(pipeline_state=data, obs=observation(vector),
                     reward=reward, done=done.astype(jnp.float32),
                     metrics={}, info=info)

    class Environment:
        """The bundle's task as a batched Brax environment (ADR-712).

        Batched already: ``reset`` takes one key and returns ``count``
        environments, and ``step`` steps them all, so Brax's own wrappers --
        which would re-implement the episode, the reset and the
        randomisation the bundle already declares -- are not used.
        """

        def __init__(self):
            self.reset = reset
            self.step = step
            self.count = envs
            self.names = names
            self.actor_names = actor_names
            self.actor_idx = actor_idx
            self.actions = actions
            self.output_scale = output_scale
            self.output_bias = output_bias
            self.horizon = horizon
            self.action_size = len(actions)
            self.observation_size = {"state": (len(actor_names),),
                                     "privileged_state": (len(names),)}

    return Environment()


#: Activations a run may train with, by the names the container records
#: (ADR-712). ``swish`` is Brax's and MuJoCo Playground's default; ``tanh``
#: is what every policy before ADR-712 was trained with, so a warm start from
#: one of them asks for it.
TRAINING_ACTIVATIONS = ("swish", "tanh")

#: Brax's ``NormalTanhDistribution`` floor on the exploration scale: the
#: scale is ``softplus(raw) + 0.001``.
BRAX_MIN_STD = 1.0e-3

#: How many environments the witness rollout steps: a separate small batch,
#: so taking a witness never touches the training batch's state.
WITNESS_ENVS = 32


#: Brax's locomotion recipe splits each batch into this many minibatches.
DEFAULT_MINIBATCHES = 32


def resolved_minibatches(options) -> int:
    """``--minibatches``, or the recipe's 32 where ``--envs`` divides by it
    and otherwise the largest count under 32 that it does: an 8-environment
    smoke run trains in 8 minibatches of one unroll each."""

    value = getattr(options, "minibatches", None)
    if value is not None:
        return int(value)
    return math.gcd(int(options.envs), DEFAULT_MINIBATCHES)


def softplus_inverse(value: float) -> float:
    """The raw output whose ``softplus`` is ``value`` (``value > 0``)."""

    if value > 30.0:
        return value
    return math.log(math.expm1(value))


def train(
    bundle: dict[str, Any],
    options: argparse.Namespace,
    *,
    emit: Any = None,
    progress: Any = None,
) -> dict[str, Any]:
    """Brax's PPO over an MJX batch built from the bundle (ADR-712).

    The environment is the bundle's (:func:`build_environment`); the
    learner is Brax's: its policy and value networks, its tanh-squashed
    Gaussian, its running observation normaliser, its PPO loss and GAE, and
    its minibatched SGD under optax's Adam with gradient clipping. Only the
    iteration loop is this file's: one rollout of ``--unroll`` steps from
    every environment, then ``--epochs`` passes of ``--minibatches``
    minibatches -- Brax's ``training_step`` with one unroll per step, written
    out so that every iteration can be reported, checkpointed and judged the
    way every earlier run was. The hand-written PPO it replaces took four
    full-batch gradient steps an iteration and could not learn a quadruped
    trot Brax learns in minutes on the same physics (orun6 B1).

    ``emit(tag, iteration, reward, trained)`` is called for each checkpoint
    and for the best-so-far policy; ``progress(**fields)`` after every
    iteration.
    """

    check_training_seed(bundle["task"], int(options.seed))

    import functools

    import jax
    import jax.numpy as jnp
    import numpy as np
    import mujoco
    import mujoco.mjx as mjx
    import optax
    from flax import linen
    from brax.training import acting, gradients
    from brax.training.acme import specs
    from brax.training import types as brax_types
    from brax.training.acme import running_statistics
    from brax.training.agents.ppo import losses as ppo_losses
    from brax.training.agents.ppo import networks as ppo_networks

    match_engine_actuator_derivative(mujoco, jax, jnp)
    emit = emit or (lambda tag, iteration, reward, trained: None)
    progress = progress or (lambda **fields: None)

    activation_name = str(getattr(options, "activation", "swish"))
    if activation_name not in TRAINING_ACTIVATIONS:
        raise SystemExit(
            f"--activation {activation_name!r}: the trainer trains "
            f"{' or '.join(TRAINING_ACTIVATIONS)}")
    activation = linen.swish if activation_name == "swish" else linen.tanh

    envs = int(options.envs)
    minibatches = resolved_minibatches(options)
    if minibatches < 1 or envs % minibatches:
        raise SystemExit(
            f"--envs {envs} does not split into --minibatches {minibatches}: "
            "each minibatch is a whole number of environments' unrolls")
    unroll = int(options.unroll)
    epochs = int(options.epochs)
    hidden = [int(width) for width in options.hidden]
    value_hidden = [int(width) for width in (options.value_hidden or hidden)]

    modules = dict(jax=jax, jnp=jnp, np=np, mujoco=mujoco, mjx=mjx)
    # ADR-759: a family is one batch over its variants' own environments.
    environment = (functools.partial(family_environment, bundle["family"])
                   if bundle.get("family") else functools.partial(build_environment, bundle))
    env = environment(options, count=envs, seed=int(options.seed), **modules)
    # The witness batch is drawn from the run's own seed, so the goals it
    # shows the policy are rows of the pool the run trained on.
    witness_env = environment(options, count=WITNESS_ENVS,
                              seed=int(options.seed), **modules)
    actions = env.actions
    action_count = len(actions)
    shapes = layer_shapes(len(env.actor_names), action_count, hidden)

    network = ppo_networks.make_ppo_networks(
        env.observation_size, action_count,
        preprocess_observations_fn=running_statistics.normalize,
        policy_hidden_layer_sizes=hidden,
        value_hidden_layer_sizes=value_hidden,
        activation=activation,
        policy_obs_key="state",
        value_obs_key="privileged_state",
    )
    make_policy = ppo_networks.make_inference_fn(network)
    learning_rate = float(options.learning_rate)
    max_grad_norm = getattr(options, "max_grad_norm", None)
    optimizer = (
        optax.chain(optax.clip_by_global_norm(float(max_grad_norm)),
                    optax.adam(learning_rate))
        if max_grad_norm else optax.adam(learning_rate)
    )
    loss_fn = functools.partial(
        ppo_losses.compute_ppo_loss,
        ppo_network=network,
        entropy_cost=float(options.entropy),
        discounting=float(options.discount),
        reward_scaling=float(options.reward_scaling),
        gae_lambda=float(options.gae_lambda),
        clipping_epsilon=float(options.clip),
        normalize_advantage=True,
        vf_coefficient=float(options.value_weight),
    )
    # ADR-825: a student distilled by command band. Each teacher's played
    # action is a target on the steps whose goal its band holds, beside PPO's
    # own loss, which still trains every step (a band with no teacher learns
    # from the reward alone).
    teachers = [load_teacher(np, *parse_teacher(text))
                for text in getattr(options, "teacher", None) or ()]
    teacher_goal = str(getattr(options, "teacher_goal", "cmd") or "cmd")
    goal_index = check_teachers(teachers, bundle, teacher_goal)
    distill_weight = float(getattr(options, "distill_weight", 1.0))
    distill = teacher_provenance(teachers, teacher_goal, distill_weight)
    if teachers:
        if not distill_weight > 0.0:
            raise SystemExit(f"--distill-weight {distill_weight:g}: a teacher "
                             "needs a weight above 0")
        ppo_loss = loss_fn

        def loss_fn(params, normaliser, data, key):
            total, metrics = ppo_loss(params, normaliser, data, key)
            logits = network.policy_network.apply(normaliser, params.policy,
                                                  data.observation)
            target, mask = teacher_actions(jnp, teachers, data.observation["state"],
                                           goal_index)
            term = distillation_loss(jnp, logits[..., :action_count],
                                     jax.lax.stop_gradient(target), mask)
            total = total + distill_weight * term
            return total, {**metrics, "total_loss": total, "distill_loss": term,
                           "taught": jnp.mean(mask)}

        if not options.quiet:
            for teacher in distill["teachers"]:
                print(f"teacher  {teacher_goal} {teacher['low']:g}-{teacher['high']:g}  "
                      f"{teacher['label']}  sha256={teacher['sha256'][:16]}…", flush=True)
    loss_and_grad = gradients.loss_and_pgrad(loss_fn, pmap_axis_name=None,
                                              has_aux=True)

    key = jax.random.PRNGKey(int(options.seed))
    key, policy_key, value_key, env_key, witness_key = jax.random.split(key, 5)
    params = ppo_losses.PPONetworkParams(
        policy=network.policy_network.init(policy_key),
        value=network.value_network.init(value_key),
    )
    normaliser = running_statistics.init_state({
        name: specs.Array(shape, jnp.dtype("float32"))
        for name, shape in env.observation_size.items()
    })
    last_layer = f"hidden_{len(hidden)}"

    def set_scale(policy, std):
        """The exploration width a run starts at: the scale half of the last
        layer reads ``std`` whatever the observation (ADR-712)."""

        layer = policy["params"][last_layer]
        kernel = np.array(layer["kernel"], dtype=np.float32)
        bias = np.array(layer["bias"], dtype=np.float32)
        kernel[:, action_count:] = 0.0
        bias[action_count:] = [
            softplus_inverse(max(float(value) - BRAX_MIN_STD, 1.0e-6))
            for value in np.broadcast_to(np.asarray(std, dtype=np.float64),
                                         (action_count,))
        ]
        layers = dict(policy["params"])
        layers[last_layer] = {"kernel": jnp.asarray(kernel), "bias": jnp.asarray(bias)}
        return {**policy, "params": layers}

    init_from_provenance: dict[str, Any] | None = None
    source_header: dict[str, Any] | None = None
    # ADR-753: how many more samples the actor's statistics rest on than the
    # critic's. Zero on a cold run; on a warm start, the source's count.
    actor_count_offset = 0
    # ADR-760: per actor input, whether it keeps the source's sample count;
    # None when every input does.
    actor_carried: list[bool] | None = None
    if not getattr(options, "init_from", "") and (
            str(getattr(options, "init_from_task_change", "") or "").strip()
            or str(getattr(options, "init_from_parent_task", "") or "").strip()
            or str(getattr(options, "init_from_base", "") or "").strip()
    ):
        raise SystemExit(
            "--init-from-task-change / --init-from-parent-task / --init-from-base only mean "
            "anything beside --init-from. Without it this is a cold run and "
            "there is no parent task to change from."
        )
    if getattr(options, "init_from", ""):
        source = Path(options.init_from).expanduser()
        try:
            blob = source.read_bytes()
        except OSError as exc:
            raise SystemExit(f"--init-from: cannot read {source}: {exc}") from exc
        decoded = decode_policy(blob, context=str(source))
        curriculum_keys = check_policy_fits(decoded["header"], bundle, options)
        source_header = decoded["header"]
        base_reason = str(getattr(options, "init_from_base", "") or "").strip()
        base_counts: dict[str, int] | None = None
        if base_reason:
            # ADR-755: the source in this robot's layout, then warmed as usual.
            mapped = remap_from_base(np, source_header, decoded["weights"],
                                     body_layout(bundle["task"]))
            base_counts = mapped["counts"]
            decoded = {"weights": flat_parameters(np, mapped["layers"])}
            if not all(mapped["carried"]):
                actor_carried = list(mapped["carried"]) + [True] * len(family_morph_names(bundle))
            source_header = {
                **source_header,
                # ADR-760: the matched inputs keep the base's samples; the
                # target's new inputs start fresh (see actor_carried).
                "normaliser": {"mean": mapped["mean"], "std": mapped["std"],
                               "count": source_normaliser_count(source_header)},
                "exploration": {**(source_header.get("exploration") or {}),
                                "log_std": mapped["log_std"]},
            }
            if not options.quiet:
                print(f"init-from-base  {base_counts}", flush=True)
        trained_with = str((source_header.get("network") or {}).get("activation") or "")
        if trained_with != activation_name:
            raise SystemExit(
                f"--init-from: {source.name} was trained with a "
                f"{trained_with!r} activation and this run trains "
                f"{activation_name!r}. Weights do not carry across an "
                f"activation; pass --activation {trained_with} to continue it.")
        restored = unflatten_parameters(np, decoded["weights"], shapes)
        layers = dict(params.policy["params"])
        for index, (weight, bias) in enumerate(restored):
            name = f"hidden_{index}"
            if index < len(restored) - 1:
                layers[name] = {"kernel": jnp.asarray(weight),
                                "bias": jnp.asarray(bias)}
            else:
                # The container holds the deterministic half -- the location
                # the engine plays. The scale half is set below.
                kernel = np.asarray(layers[name]["kernel"], dtype=np.float32).copy()
                full_bias = np.asarray(layers[name]["bias"], dtype=np.float32).copy()
                kernel[:, :action_count] = weight
                full_bias[:action_count] = bias
                layers[name] = {"kernel": jnp.asarray(kernel),
                                "bias": jnp.asarray(full_bias)}
        params = params.replace(policy={**params.policy, "params": layers})

        # Without this the transfer is mostly wasted: the actor was trained
        # to read normalised observations. The actor's statistics keep the
        # weight of every sample the source saw (ADR-753): with a count of
        # one the first batch replaced them, and the frozen actor read its
        # inputs on a different scale for the iterations it took the
        # running mean to drift back. The critic's privileged statistics
        # are not in the header, so they start at a count of one as before.
        stats = source_header.get("normaliser") or {}
        if stats.get("mean") is not None and stats.get("std") is not None:
            mean = jnp.asarray(stats["mean"], dtype=jnp.float32)
            std = jnp.asarray(stats["std"], dtype=jnp.float32)
            actor_count = source_normaliser_count(source_header)
            actor_count_offset = actor_count - 1
            weight = (float(actor_count) if actor_carried is None else
                      jnp.where(jnp.asarray(actor_carried), float(actor_count), 1.0))
            normaliser = normaliser.replace(
                count=brax_types.UInt64(hi=0, lo=1),
                mean={**normaliser.mean, "state": mean},
                summed_variance={**normaliser.summed_variance,
                                 "state": jnp.square(std) * weight},
                std={**normaliser.std, "state": std},
            )
            if not options.quiet:
                fresh = ("" if actor_carried is None else
                         f" ({actor_carried.count(False)} new inputs start fresh)")
                print(f"normaliser  the actor's statistics carry the source's "
                      f"{actor_count} samples{fresh}", flush=True)

        source_training = source_header.get("training") or {}
        init_from_provenance = {
            "sha256": hashlib.sha256(blob).hexdigest(),
            "label": str(source_header.get("label") or ""),
            "iterations": source_training.get("iterations"),
            "trainer_sha256": source_training.get("trainer_sha256"),
        }
        if base_counts is not None:
            init_from_provenance["base"] = {
                "reason": base_reason,
                "family": str(source_header["body"]["family"]),
                "model_sha256": str((source_header.get("model") or {}).get("sha256") or ""),
                "task_sha256": str((source_header.get("task") or {}).get("sha256") or ""),
                **base_counts,
            }
        if curriculum_keys is not None:
            init_from_provenance["task_change"] = {
                "reason": str(options.init_from_task_change).strip(),
                "keys": list(curriculum_keys),
                "parent_task_sha256": str(
                    (source_header.get("task") or {}).get("sha256") or ""),
                "parent_task_label": str(
                    (source_header.get("task") or {}).get("label") or ""),
                "task_sha256": bundle["task_sha256"],
            }
        if not options.quiet:
            print(
                f"init-from  {source.name}  "
                f"iterations={source_training.get('iterations')}  "
                f"sha256={init_from_provenance['sha256'][:16]}…",
                flush=True,
            )
            if curriculum_keys is not None:
                print(
                    f"curriculum  the task changed in {list(curriculum_keys)} "
                    f"— {str(options.init_from_task_change).strip()}",
                    flush=True,
                )

    # ADR-471: a warm start continues at the width it trained to unless
    # --initial-std says otherwise. A cold run without the flag starts where
    # Brax's network does, softplus(~0) + 0.001, about 0.69 (ADR-712).
    if source_header is not None or getattr(options, "initial_std", None) is not None:
        start_log_std, std_source = starting_log_std(options, source_header, action_count)
        params = params.replace(policy=set_scale(params.policy, np.exp(start_log_std)))
        if init_from_provenance is not None:
            init_from_provenance["log_std_source"] = std_source
        if not options.quiet and std_source != "default":
            print(f"action_std  {float(np.mean(np.exp(start_log_std))):.4f}  "
                  f"(from {std_source})", flush=True)
    optimizer_state = optimizer.init(params)

    def minibatch_step(carry, data, normaliser, train_actor):
        optimizer_state, params, key = carry
        key, loss_key = jax.random.split(key)
        (_, metrics), grads = loss_and_grad(params, normaliser, data, loss_key)
        # ADR-740: while the critic warms up, the actor's gradient is zero, so
        # Adam leaves it where the warm start put it.
        grads = grads.replace(policy=jax.tree.map(lambda g: g * train_actor, grads.policy))
        updates, optimizer_state = optimizer.update(grads, optimizer_state)
        params = optax.apply_updates(params, updates)
        return (optimizer_state, params, key), metrics

    def sgd_step(carry, _unused, data, normaliser, train_actor):
        optimizer_state, params, key = carry
        key, permute_key, grad_key = jax.random.split(key, 3)

        def split(x):
            x = jax.random.permutation(permute_key, x)
            return jnp.reshape(x, (minibatches, -1) + x.shape[1:])

        (optimizer_state, params, _), metrics = jax.lax.scan(
            functools.partial(minibatch_step, normaliser=normaliser, train_actor=train_actor),
            (optimizer_state, params, grad_key),
            jax.tree.map(split, data),
            length=minibatches,
        )
        return (optimizer_state, params, key), metrics

    def action_std_of(logits):
        return jnp.mean(jax.nn.softplus(logits[..., action_count:]) + BRAX_MIN_STD)

    # ADR-589: a sensed channel's spread never falls below what its sensor
    # can resolve, so one rounding step or one lost touch cannot reach the
    # policy as thousands of standard deviations. Zero (no floor) for every
    # channel no declared sensor reports.
    floor = np.sqrt(np.asarray(sensor_variance_floor(bundle["task"])
                               + [0.0] * len(family_morph_names(bundle)), dtype=np.float32))
    std_floor = {"state": jnp.asarray(floor[env.actor_idx]),
                 "privileged_state": jnp.asarray(floor)}

    carried_mask = None if actor_carried is None else jnp.asarray(actor_carried)

    def floored(normaliser):
        return normaliser.replace(std={
            name: jnp.maximum(value, std_floor[name])
            for name, value in normaliser.std.items()})

    def update_normaliser(normaliser, observation):
        """Brax's one shared count, except that the actor's statistics
        count ``actor_count_offset`` samples more (ADR-753) -- on the
        inputs a base remap carried, when it marked some fresh (ADR-760)."""

        updated = running_statistics.update(normaliser, observation)
        if not actor_count_offset:
            return updated
        actor = running_statistics.update(
            normaliser.replace(count=normaliser.count + actor_count_offset),
            observation)
        pick = ((lambda carried, fresh: carried) if actor_carried is None else
                (lambda carried, fresh: jnp.where(carried_mask, carried, fresh)))
        return updated.replace(
            mean={**updated.mean, "state": pick(actor.mean["state"], updated.mean["state"])},
            summed_variance={**updated.summed_variance,
                             "state": pick(actor.summed_variance["state"],
                                           updated.summed_variance["state"])},
            std={**updated.std, "state": pick(actor.std["state"], updated.std["state"])})

    @jax.jit
    def iterate(optimizer_state, params, normaliser, env_state, key, train_actor):
        sgd_key, unroll_key, key = jax.random.split(key, 3)
        policy = make_policy((normaliser, params.policy, params.value))
        env_state, data = acting.generate_unroll(
            env, env_state, policy, unroll_key, unroll,
            extra_fields=("truncation", "terminated"))
        # [unroll, envs] -> [envs, unroll]: a minibatch is whole unrolls.
        data = jax.tree.map(lambda x: jnp.swapaxes(x, 0, 1), data)
        normaliser = floored(update_normaliser(normaliser, data.observation))
        (optimizer_state, params, _), metrics = jax.lax.scan(
            functools.partial(sgd_step, data=data, normaliser=normaliser, train_actor=train_actor),
            (optimizer_state, params, sgd_key), (), length=epochs)
        endings = jnp.sum(1.0 - data.discount)
        # Steps taken in this batch over episodes that ended in it; with
        # nothing ending it reads the whole batch, which cannot be an episode
        # length and is meant to be read as "nothing is resetting" (ADR-101).
        episode_steps = jnp.float32(unroll * envs) / jnp.maximum(endings, 1.0)
        report = {
            "reward_per_step": jnp.mean(data.reward),
            "loss": jnp.mean(metrics["total_loss"][-1]),
            "episode_steps": episode_steps,
            "action_std": action_std_of(
                data.extras["policy_extras"]["distribution_params"]),
        }
        if teachers:
            report["distill_loss"] = jnp.mean(metrics["distill_loss"][-1])
            report["taught"] = jnp.mean(metrics["taught"][-1])
        return optimizer_state, params, normaliser, env_state, key, report

    @jax.jit
    def witness_rollout(normaliser, policy_params, key):
        """The deterministic policy on the witness batch: what it reads."""

        policy = make_policy((normaliser, policy_params, None), deterministic=True)

        def one(state, step_key):
            action, _ = policy(state.obs, step_key)
            return witness_env.step(state, action), state.obs["state"]

        state = witness_env.reset(key)
        _state, seen = jax.lax.scan(one, state, jax.random.split(key, unroll))
        return seen

    view_steps = 0
    if getattr(options, "view_seconds", 0) and not bundle.get("family"):
        interval = float(bundle["task"]["episode"]["control_interval_s"])
        view_steps = max(1, round(float(options.view_seconds) / interval))

    @jax.jit
    def view_rollout(normaliser, policy_params, key):
        """The deterministic policy on the witness batch, every pose (ADR-835)."""

        policy = make_policy((normaliser, policy_params, None), deterministic=True)

        def one(state, step_key):
            action, _ = policy(state.obs, step_key)
            state = witness_env.step(state, action)
            return state, state.pipeline_state.qpos

        state = witness_env.reset(key)
        _state, poses = jax.lax.scan(one, state, jax.random.split(key, view_steps))
        return jnp.concatenate([state.pipeline_state.qpos[None], poses])

    def view_poses(params, normaliser):
        """[step, qpos] of the witness episode that travelled farthest, or None.

        The view is for watching; it never fails a run."""

        if not view_steps:
            return None
        try:
            poses = np.asarray(view_rollout(normaliser, params.policy, witness_key),
                               dtype=np.float64)
            host = mujoco.MjModel.from_xml_string(bundle["model_xml"].decode("utf-8"))
        except Exception as error:  # noqa: BLE001
            print(f"view: not written ({type(error).__name__}: {error})", file=sys.stderr)
            return None
        pick = 0
        if host.njnt and int(host.jnt_type[0]) == int(mujoco.mjtJoint.mjJNT_FREE):
            travel = np.linalg.norm(poses[-1, :, :2] - poses[0, :, :2], axis=-1)
            pick = int(np.argmax(travel))
        return poses[:, pick, :]

    def snapshot(params, normaliser, curve, wall):
        seen = np.asarray(witness_rollout(normaliser, params.policy, witness_key)
                          ).reshape((-1, len(env.actor_names)))
        if seen.shape[0] >= WITNESS_SAMPLES:
            picks = np.linspace(0, seen.shape[0] - 1, WITNESS_SAMPLES).astype(int)
        else:
            picks = np.arange(seen.shape[0])
        witness_obs = seen[picks].astype(np.float32)

        # The deterministic half of Brax's last layer is the network the
        # engine plays: tanh(location) * scale + bias. The scale half is the
        # exploration width, recorded below and never played.
        layers = params.policy["params"]
        stored = []
        for index in range(len(hidden) + 1):
            layer = layers[f"hidden_{index}"]
            weight = np.asarray(layer["kernel"], dtype=np.float32)
            bias = np.asarray(layer["bias"], dtype=np.float32)
            if index == len(hidden):
                weight, bias = weight[:, :action_count], bias[:action_count]
            stored.append((weight, bias))
        stored_jax = [(jnp.asarray(w), jnp.asarray(b)) for w, b in stored]
        stored_mean = np.asarray(normaliser.mean["state"], dtype=np.float32)
        stored_std = np.asarray(normaliser.std["state"], dtype=np.float32)
        stored_std = np.where(stored_std == 0.0, np.float32(1.0), stored_std)

        def witness_action(vector):
            normalised = (jnp.asarray(vector) - jnp.asarray(stored_mean)
                          ) / jnp.asarray(stored_std)
            raw = forward(jnp, stored_jax, normalised, activation=activation_name)
            return (jnp.tanh(raw) * jnp.asarray(env.output_scale)
                    + jnp.asarray(env.output_bias))

        # ``highest`` is load-bearing (ADR-094): a batched float32 matmul on
        # a tensor core is TF32, and the engine evaluates in float64.
        with jax.default_matmul_precision("highest"):
            witness_actions = np.asarray(
                jax.vmap(witness_action)(jnp.asarray(witness_obs)))
            logits = network.policy_network.apply(
                normaliser, params.policy, {"state": jnp.asarray(witness_obs),
                                            "privileged_state": None})
        scale = np.asarray(jax.nn.softplus(logits[:, action_count:]) + BRAX_MIN_STD)
        log_std = np.mean(np.log(scale), axis=0)

        return {
            "parameters": flat_parameters(np, stored),
            "layers": [[int(a), int(b)] for a, b in shapes],
            "activation": activation_name,
            # Brax's scale depends on the observation; this is its mean log
            # over the witness observations, per action, in the
            # pre-activation space the noise is added in (ADR-103, ADR-712).
            "log_std": [float(v) for v in log_std],
            "normaliser": {
                "mean": [float(v) for v in stored_mean],
                "std": [float(v) for v in stored_std],
                # ADR-753: the samples behind the actor's statistics, so a
                # warm start from this policy keeps their weight.
                "count": int(normaliser.count) + actor_count_offset,
            },
            "output_scale": env.output_scale,
            "output_bias": env.output_bias,
            "observations": list(env.actor_names),
            "witness_observations": [[float(v) for v in row] for row in witness_obs],
            "witness_actions": [[float(v) for v in row] for row in witness_actions],
            "reward_curve": list(curve),
            "iterations": len(curve),
            "wall_time_s": float(wall),
            "init_from": init_from_provenance,
            "distill": distill,
            "backend": jax.default_backend(),
            "devices": [str(device) for device in jax.devices()],
            "versions": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "mujoco": str(getattr(mujoco, "__version__", "unknown")),
                "mjx": str(getattr(mjx, "__version__",
                                    getattr(mujoco, "__version__", "unknown"))),
                "jax": jax.__version__,
                "brax": _package_version("brax"),
                "flax": _package_version("flax"),
                "optax": _package_version("optax"),
            },
        }

    env_state = jax.jit(env.reset)(env_key)
    curve = []
    started = time.perf_counter()
    total_iterations = int(options.iterations)
    every = max(0, int(getattr(options, "checkpoint_every", 0) or 0))
    best = {"reward_per_step": -math.inf, "iteration": -1,
            "params": None, "normaliser": None, "written": -1}
    collapsed = ""
    critic_warmup = int(getattr(options, "critic_warmup", 0) or 0) if source_header is not None else 0
    for iteration in range(total_iterations):
        train_actor = jnp.float32(0.0 if iteration < critic_warmup else 1.0)
        (optimizer_state, params, normaliser, env_state, key,
         report) = iterate(optimizer_state, params, normaliser, env_state, key, train_actor)
        entry = {"iteration": iteration,
                 **{name: float(value) for name, value in report.items()}}
        curve.append(entry)
        if not collapsed:
            collapsed = episode_collapse(curve, env.horizon)
            if collapsed:
                print(f"iteration {iteration}: {collapsed}", file=sys.stderr)
                if getattr(options, "stop_on_collapse", False):
                    progress(state="training", iteration=iteration,
                             total=total_iterations, curve=curve, best=best,
                             wall=time.perf_counter() - started,
                             device=jax.default_backend(), warning=collapsed)
                    raise SystemExit(f"Stopped at iteration {iteration}: {collapsed}")
        if not options.quiet:
            print(
                f"iteration {iteration:4d}  reward/step {entry['reward_per_step']:+.6g}"
                f"  loss {entry['loss']:+.6g}"
                f"  episode {entry['episode_steps']:.1f}"
                f"  sigma {entry['action_std']:.4f}"
                + (f"  distill {entry['distill_loss']:.4g} on {entry['taught']:.2f}"
                   if teachers else ""),
                file=sys.stderr,
            )
        # Stop at the first non-finite number: diverged parameters do not
        # recover, so every iteration after it is spent producing a policy
        # that cannot be written.
        diverged = [
            name for name in ("reward_per_step", "loss")
            if not math.isfinite(entry[name])
        ]
        if diverged:
            raise SystemExit(
                f"Training diverged at iteration {iteration}: "
                f"{' and '.join(diverged)} went non-finite "
                f"(reward/step {entry['reward_per_step']}, "
                f"loss {entry['loss']}). Nothing after this iteration can "
                "produce a writable policy. The usual causes are a learning "
                "rate too high for the reward's scale and a reward built on "
                "raw millimetre or degree channels -- see docs/MUJOCO.md on "
                "reward conditioning."
            )

        elapsed_wall = time.perf_counter() - started
        if entry["reward_per_step"] > best["reward_per_step"]:
            best.update(reward_per_step=entry["reward_per_step"],
                        iteration=iteration, params=params,
                        normaliser=normaliser)
        due = every and (iteration + 1) % every == 0
        if due and iteration + 1 < total_iterations:
            emit(f"{iteration + 1:06d}", iteration, entry["reward_per_step"],
                 snapshot(params, normaliser, curve, elapsed_wall))
            if best["written"] != best["iteration"]:
                emit("best", best["iteration"], best["reward_per_step"],
                     snapshot(best["params"], best["normaliser"],
                              curve, elapsed_wall))
                best["written"] = best["iteration"]
        progress(
            state="training",
            iteration=iteration,
            total=total_iterations,
            curve=curve,
            best=best,
            wall=elapsed_wall,
            device=jax.default_backend(),
            warning=collapsed,
        )

    wall = time.perf_counter() - started
    if best["params"] is not None and best["written"] != best["iteration"]:
        emit("best", best["iteration"], best["reward_per_step"],
             snapshot(best["params"], best["normaliser"], curve, wall))
    final = snapshot(params, normaliser, curve, wall)
    final["view_qpos"] = view_poses(params, normaliser)
    return final


def _package_version(name: str) -> str:
    try:
        from importlib import metadata
        return metadata.version(name)
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# The program.
# ---------------------------------------------------------------------------


def witness_swish(value: float) -> float:
    """``CadexDynamics.policy_swish``, copied for ADR-084's reason."""

    if value >= 0.0:
        return value / (1.0 + math.exp(-value))
    rising = math.exp(value)
    return value * rising / (1.0 + rising)


def witness_disagreement(header: dict[str, Any],
                         weights: Sequence[float]) -> tuple[float, int, int]:
    """The engine's own witness check, in the engine's own arithmetic.

    A fourth evaluator, and written down here for the reason the reward
    whitelist and :func:`encode_policy` are: this file cannot import
    ``CadexDynamics`` (ADR-084), so the check that decides whether hours of
    GPU time produced a usable file is copied rather than imported, and a
    test pins the two together.

    Pure ``float`` and pure Python -- no ``numpy``, no ``jax`` -- because
    the point is to reproduce ``CadexDynamics.policy_forward`` exactly,
    including that it is float64 throughout and that its inner sum
    accumulates in written order. Anything that reaches for a fast matmul
    here would reintroduce the very TF32 rounding this exists to catch.

    Returns ``(worst, sample, action)`` with the worst error relative to
    each action's own advertised ``high - low``.
    """

    network = header["network"]
    activation = str(network.get("activation") or "tanh")
    shapes = [(int(a), int(b)) for a, b in network["layers"]]
    scale = [float(v) for v in network["output_scale"]]
    bias_out = [float(v) for v in network["output_bias"]]
    mean = [float(v) for v in header["normaliser"]["mean"]]
    std = [float(v) for v in header["normaliser"]["std"]]
    ranges = [max(float(a["high"]) - float(a["low"]), 1.0e-12)
              for a in header["actions"]]
    weights = [float(v) for v in weights]

    worst, worst_sample, worst_action = 0.0, -1, -1
    evaluation = header["evaluation"]
    for sample, (observed, recorded) in enumerate(
        zip(evaluation["observations"], evaluation["actions"])
    ):
        activations = [(float(v) - mean[i]) / std[i]
                       for i, v in enumerate(observed)]
        cursor, last = 0, len(shapes) - 1
        for index, (inputs, outputs) in enumerate(shapes):
            matrix = weights[cursor:cursor + inputs * outputs]
            cursor += inputs * outputs
            bias = weights[cursor:cursor + outputs]
            cursor += outputs
            result = [0.0] * outputs
            for column in range(outputs):
                total, offset = bias[column], column
                for row in range(inputs):
                    total += activations[row] * matrix[offset]
                    offset += outputs
                result[column] = total
            if index < last:
                if activation == "tanh":
                    result = [math.tanh(value) for value in result]
                elif activation == "swish":
                    result = [witness_swish(value) for value in result]
                else:
                    result = [value if value > 0.0 else 0.0 for value in result]
            activations = result
        for index, value in enumerate(activations):
            produced = math.tanh(value) * scale[index] + bias_out[index]
            error = abs(produced - float(recorded[index])) / ranges[index]
            if error > worst:
                worst, worst_sample, worst_action = error, sample, index
    return worst, worst_sample, worst_action


def policy_header(
    bundle: dict[str, Any],
    options: argparse.Namespace,
    trained: dict[str, Any],
    *,
    cadex_importable: bool,
) -> dict[str, Any]:
    """One ``trained`` dict, as the header the engine reads.

    Lifted out of :func:`main` in M9 so that a checkpoint written at
    iteration 300 is **the same kind of file** as the one written at the
    end -- a complete, witness-checked ``.cxpolicy`` that can be pasted
    straight into ``assembly.policy``. A weight dump would need a second
    reader nobody has written, and would be a thing you cannot play.
    """

    task = bundle["task"]
    header = {
        "schema": POLICY_SCHEMA,
        "label": str(options.label or task.get("label") or ""),
        "task": {"sha256": bundle["task_sha256"],
                 "label": str(task.get("label") or "")},
        "model": {"sha256": bundle["model_sha256"], "path": bundle["model_path"]},
        "observations": list(trained.get("observations") or actor_channels(task)),
        "actions": list(task["actions"]),
        # ADR-755: what each input and action is on the family's canonical
        # body, so this policy can be a base. Absent without a body block.
        # ADR-759: a family run's morph inputs are named as themselves.
        **({"body": family_body(bundle)} if task.get("body") else {}),
        "network": {
            "kind": "mlp",
            "layers": trained["layers"],
            "activation": str(trained.get("activation") or "tanh"),
            "output": "tanh",
            "output_scale": trained["output_scale"],
            "output_bias": trained["output_bias"],
        },
        "normaliser": trained["normaliser"],
        # Top level, and deliberately NOT inside `network` (ADR-103). What
        # `network` describes is the deterministic forward pass the engine
        # evaluates and witnesses; this describes the distribution the
        # trainer sampled from around it, which the engine neither plays nor
        # checks. Filing it under `network` would invite a reader to think
        # the witness covers it.
        #
        # `space` is load-bearing and any reader has to honour it: the noise
        # is added to the network's raw output BEFORE the output tanh --
        # `surface = tanh(raw + noise * exp(log_std)) * scale + bias`, see
        # `rollout` above. Adding noise to a policy's surface action instead
        # would be noise in the wrong space, unbounded by the tanh, and
        # would answer a question nobody asked.
        #
        # Brax's scale depends on the observation (ADR-712), so `log_std` is
        # its mean log over the witness observations, and `state_dependent`
        # says so.
        "exploration": {
            "distribution": "gaussian",
            "log_std": [float(v) for v in trained["log_std"]],
            "space": "pre_activation",
            "state_dependent": True,
        },
        "training": {
            "trainer_sha256": TRAINER_SHA256,
            "seed": int(options.seed),
            # ADR-160. Written as its own key as well as appearing in
            # ``hyperparameters`` below, because this is the one an
            # *evaluator* reads: a policy trained with a filter has to be
            # PLAYED with it, and a driver that had to be told separately is
            # a driver somebody will forget to tell.
            "action_filter_alpha": float(options.action_filter_alpha),
            # ADR-162, and its own key for exactly ADR-160's reason: a policy
            # trained under a rate limit has to be PLAYED under one, and a
            # driver that had to be told separately is a driver somebody will
            # forget to tell. 0.0 is no limit.
            "command_slew_deg": resolved_command_slew_deg(options),
            # ADR-700. Not needed to PLAY the policy, but a reward curve is
            # read against it: a floored run's reward/step cannot go below it.
            "reward_floor": resolved_reward_floor(options),
            # ``init_from`` is excluded for the same reason ``bundle`` and
            # ``out`` are: it is a path on one machine, not a hyperparameter.
            # What it started from is recorded as a digest under
            # ``init_from`` below, which identifies the bytes and survives
            # being copied somewhere else.
            #
            # ADR-161's two flags go with it and for the same reason: one
            # names a second file and the other is a sentence explaining a
            # warm start. Both describe THIS RUN's provenance, not the
            # algorithm, and both are recorded under ``init_from.task_change``
            # where a reader will look for them.
            "hyperparameters": {
                key: value
                for key, value in sorted(vars(options).items())
                if key not in ("bundle", "out", "quiet", "label", "init_from",
                               "init_from_task_change",
                               "init_from_parent_task", "init_from_base",
                               "family", "teacher", "teacher_goal",
                               "distill_weight")
                # The goal pool's size means nothing to a task that states
                # no goal, and leaving it out there keeps such a policy's
                # header the one it always was (ADR-462).
                and (key != "goal_pool" or task.get("goal"))
            },
            "init_from": trained.get("init_from"),
            # The iterations this policy actually saw, which for a
            # checkpoint is not `options.iterations`. A checkpoint claiming
            # the run's total would be a file that lies about its own age.
            "iterations": int(trained["iterations"]),
            "wall_time_s": float(trained["wall_time_s"]),
            "device": trained["backend"],
            "devices": trained["devices"],
            "versions": trained["versions"],
            "reward_curve": trained["reward_curve"],
            "randomisation": {
                "mode": RANDOMISATION_MODE,
                "algorithm": RANDOMISATION_ALGORITHM,
                "base_seed": int(options.seed),
                "environments": int(options.envs),
                "entries": [str(entry["label"])
                            for entry in task.get("randomisation") or ()],
            },
            # The second stream, recorded beside the first because it is a
            # *different* algorithm and a reader has to be able to tell which
            # numbers came from where (M9, ADR-097).
            "episode_variation": {
                "mode": RESET_VARIATION_MODE,
                "algorithm": RESET_VARIATION_ALGORITHM,
                "bundle_algorithm": str(task.get("variation_algorithm") or ""),
                "reset_variation": [
                    str(entry["label"])
                    for entry in task.get("reset_variation") or ()
                ],
                "disturbance": [
                    str(entry["label"])
                    for entry in task.get("disturbance") or ()
                ],
            },
            # The third stream (ADR-462), and the one drawn by the bundle's
            # own algorithm. Absent for a task that states no goal, so such
            # a policy's header is the one it always was.
            **(
                {
                    "goal": {
                        "mode": GOAL_MODE,
                        "algorithm": GOAL_POOL_ALGORITHM,
                        "bundle_algorithm": str(task.get("goal_algorithm") or ""),
                        "base_seed": int(options.seed),
                        "pool": int(getattr(options, "goal_pool", 4096)),
                        "entries": [str(entry["label"])
                                    for entry in task.get("goal") or ()],
                    }
                }
                if task.get("goal") else {}
            ),
            # ADR-717: the course each episode ran on, when the bundle pools
            # them. Absent otherwise, so such a policy's header is unchanged.
            **(
                {
                    "terrain": {
                        "mode": TERRAIN_MODE,
                        "algorithm": TERRAIN_POOL_ALGORITHM,
                        "bundle_algorithm": str(
                            (task["terrain"].get("random") or {}).get("algorithm") or ""),
                        "courses": len(task["terrain"]["pool"]),
                    }
                }
                if (task.get("terrain") or {}).get("pool") else {}
            ),
            # ADR-759: the variants a --family run trained on, in block order.
            # Absent otherwise, so such a policy's header is unchanged.
            **(
                {
                    "family": [
                        {"task_sha256": variant["task_sha256"],
                         "model_sha256": variant["model_sha256"],
                         "label": str(variant["task"].get("label") or ""),
                         "morph": variant["task"]["body"]["morph"]}
                        for variant in bundle["family"]
                    ]
                }
                if bundle.get("family") else {}
            ),
            "cadex_importable": cadex_importable,
        },
        "evaluation": {
            "observations": trained["witness_observations"],
            "actions": trained["witness_actions"],
        },
    }
    # ADR-825: the teachers by digest. A run without them writes the header
    # it always wrote.
    if trained.get("distill"):
        header["training"]["distill"] = trained["distill"]
    return header


def checked_policy(
    header: dict[str, Any], trained: dict[str, Any], *, what: str
) -> bytes:
    """The container's bytes, or a refusal that names what failed.

    The engine's witness check, run here, before a single byte is written.
    Everything it needs has existed since the moment training stopped, and
    the engine will apply exactly this test on another machine at the end of
    a trip that costs a scp and a rebuild. A run that fails it is already
    lost; the only question is whether it is lost now or after somebody has
    spent an afternoon believing they have a policy.

    Run on **checkpoints too**, and that is the point of it being a function.
    The witness error is a relative one that grows with the activations a
    policy learns, so a checkpoint that fails it is a run that is going to
    fail it -- and the whole reason ADR-094 cost four hours is that nothing
    checked until the end.
    """

    worst, sample, action = witness_disagreement(header, trained["parameters"])
    if worst > POLICY_WITNESS_TOLERANCE:
        raise SystemExit(
            f"{what} does not reproduce its own recorded actions: "
            f"witness {sample}, action {action}, relative error {worst:g} "
            f"against a tolerance of {POLICY_WITNESS_TOLERANCE:g}. The "
            f"engine applies this same test and would refuse the file, so "
            f"it is not written.\n"
            f"  The witness is recorded under "
            f"jax.default_matmul_precision('highest') precisely so that a "
            f"tensor-core matmul cannot round it (see the comment beside "
            f"it, and ADR-094). An error near 1e-4 that survives that is "
            f"something else: a layer order, a bias layout, an activation, "
            f"or a normaliser that disagrees with the weights it shipped "
            f"with."
        )
    blob = encode_policy(header, trained["parameters"])
    if len(blob) > MAXIMUM_POLICY_BYTES:
        raise SystemExit(
            f"{what} is {len(blob)} bytes; the engine accepts at most "
            f"{MAXIMUM_POLICY_BYTES}. Train a smaller network."
        )
    return blob


def write_atomically(path: Path, payload: bytes) -> None:
    """Temp file then ``replace``, so no reader ever sees half a file.

    ``progress.json`` is rewritten every iteration and read by a `watch`
    loop on another machine and by a panel in the shell. A plain write is a
    window, small but real, in which both of those read a truncated file and
    report a run that has gone wrong.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_bytes(payload)
    temporary.replace(path)


def checkpoint_path(out: Path, tag: str) -> Path:
    """``walk.cxpolicy`` and ``000300`` -> ``walk.000300.cxpolicy``.

    The suffix is kept so that every file this writes is a ``.cxpolicy`` a
    person can hand to ``assembly.policy`` without renaming it, and the tag
    is zero-padded so a directory listing sorts into training order.
    """

    return out.with_name(f"{out.stem}.{tag}{out.suffix}")


def arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="cadex_train.py",
        description="Train a control policy from a cadex-training-task-v1 bundle.",
    )
    parser.add_argument("bundle", help="path to <root>/outputs/<name>-task.json")
    parser.add_argument("--out", default="", help="path to write the .cxpolicy (required unless --view)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--envs", type=int, default=256)
    # The defaults are MuJoCo Playground's locomotion PPO recipe (ADR-712),
    # which trains a quadruped trot in minutes on the same physics.
    parser.add_argument("--unroll", type=int, default=20)
    parser.add_argument(
        "--epochs", type=int, default=4,
        help="passes over each iteration's batch (Brax's num_updates_per_batch)")
    parser.add_argument(
        "--minibatches", type=int, default=None,
        help="minibatches per pass; --envs must divide by it. Each is "
             "--envs/--minibatches environments' whole unrolls. Default 32, "
             "or the largest count --envs divides by under it (ADR-712)")
    parser.add_argument(
        "--hidden", type=int, nargs="+", default=[512, 256, 128],
        help="the policy network's hidden widths")
    parser.add_argument(
        "--value-hidden", type=int, nargs="+", default=None,
        help="the critic's hidden widths; default the policy's")
    parser.add_argument(
        "--activation", choices=TRAINING_ACTIVATIONS, default="swish",
        help="hidden activation, recorded in the policy. A warm start must "
             "name the activation its source was trained with; every policy "
             "before ADR-712 is tanh")
    parser.add_argument("--learning-rate", type=float, default=3.0e-4)
    parser.add_argument("--discount", type=float, default=0.97)
    parser.add_argument("--gae-lambda", type=float, default=0.95)
    parser.add_argument("--clip", type=float, default=0.3)
    parser.add_argument("--entropy", type=float, default=1.0e-2)
    parser.add_argument("--value-weight", type=float, default=0.5)
    parser.add_argument(
        "--max-grad-norm", type=float, default=1.0,
        help="clip each gradient to this global norm; 0 does not clip")
    parser.add_argument(
        "--reward-scaling", type=float, default=1.0,
        help="multiply every reward by this before the PPO loss")
    parser.add_argument(
        "--initial-std", type=float, default=None,
        help="the exploration width (σ, pre-activation) the run starts at. "
             "A cold run without it starts where Brax's network does "
             "(about 0.69); on --init-from the source policy's own "
             "per-action width is carried instead, unless this is given "
             "explicitly (ADR-471)")
    parser.add_argument(
        "--goal-pool", type=int, default=4096,
        help="how many episodes of goals to draw on the host before training "
             "(ADR-462). Each is drawn by the bundle's own goal_algorithm "
             "from --seed, and every environment is given one of them on "
             "each reset. Ignored by a task that states no goal.",
    )
    parser.add_argument(
        "--action-filter-alpha", type=float, default=1.0,
        help="low-pass the command before it reaches the actuators: "
             "a[t] = A*clamped[t] + (1-A)*a[t-1], per environment, reset with "
             "the episode and with the first command of each episode passed "
             "through unfiltered. 1.0 (the default) is NO FILTER and emits "
             "the same computation graph as a trainer without this flag. "
             "The resolved value is written into the .cxpolicy header, so an "
             "evaluator plays the policy with the filter it was trained "
             "with instead of being told separately")
    parser.add_argument(
        "--command-slew-deg", type=float, default=0.0,
        help="cap the per-step change of the ISSUED command at this many "
             "degrees on every joint, applied AFTER the action filter and "
             "reset with the episode. This bounds the command's RATE, which "
             "the EMA does not: an EMA's per-step change is alpha*|raw - "
             "previous|, up to the full box width. 0.0 (the default) is NO "
             "LIMIT and emits the same computation graph as a trainer "
             "without this flag. The resolved value is written into the "
             ".cxpolicy header so an evaluator plays the policy under the "
             "limit it was trained under")
    parser.add_argument(
        "--reward-floor", type=float, default=None,
        help="clamp each step's summed reward from below at this value, as "
             "MuJoCo Playground's locomotion recipes clip theirs at 0. A "
             "floor at or above the cost of dying removes the incentive to "
             "end an episode early while costs outweigh pay (ADR-700). "
             "Absent (the default) is NO FLOOR and emits the same "
             "computation graph as a trainer without this flag. Recorded in "
             "the .cxpolicy header")
    parser.add_argument(
        "--init-from",
        default="",
        metavar="POLICY",
        help=(
            "warm-start the actor from an existing .cxpolicy instead of a "
            "fresh network. The policy must match this bundle's task and "
            "model digests, its observation channels in order, its action "
            "table and the network shape --hidden asks for. Only the actor, "
            "its exploration width (unless --initial-std is given) and the "
            "observation normaliser are carried: the critic and the "
            "optimiser start fresh, because the container holds neither."
        ),
    )
    parser.add_argument(
        "--critic-warmup",
        type=int,
        default=0,
        metavar="N",
        help=(
            "ADR-740: with --init-from, train only the critic for the first N "
            "iterations. The critic starts fresh, and until it values the "
            "carried actor its advantages are noise that PPO follows: "
            "rough-c2's episodes fell from 504 to 62 steps in two iterations."
        ),
    )
    parser.add_argument(
        "--init-from-task-change",
        default="",
        metavar="REASON",
        help=(
            "ADR-161: permit --init-from across a task change -- a "
            "CURRICULUM step -- and say why in one line, which is written "
            "into the run record. Without this, the bundle's whole-file "
            "digest must match the policy's, so a harder disturbance band "
            "can only ever be learned from a fresh network. Requires "
            "--init-from-parent-task. Only keys that change what the network "
            "is trained AGAINST may move; keys that change what it reads or "
            "emits are refused, and every other --init-from check still runs"
        ),
    )
    parser.add_argument(
        "--init-from-base",
        default="",
        metavar="REASON",
        help=(
            "ADR-755: warm-start --init-from's policy onto ANOTHER robot of its "
            "family, matched slot by slot on the canonical body both bundles "
            "map (api.task(body=...)), and say why in one line. The digests are "
            "not compared; the family, the hidden layers and one shared joint "
            "slot per leg are, and --critic-warmup is required"
        ),
    )
    parser.add_argument(
        "--family",
        nargs="+",
        default=[],
        metavar="BUNDLE",
        help=(
            "ADR-759: train one policy on a family of built variants of one "
            "robot -- the bundle plus each of these, every one mapping a body "
            "with a morph block. Environment blocks are split evenly across "
            "the variants, each with its own model, reward, clip and action "
            "box, and the policy reads the variant's morph constants as "
            "inputs, which --init-from-base folds into the bias on a target"
        ),
    )
    parser.add_argument(
        "--init-from-parent-task",
        default="",
        metavar="BUNDLE",
        help=(
            "the task bundle --init-from's policy was trained on, so the "
            "curriculum step can be named key by key. Its digest must equal "
            "the one in that policy's header. Only meaningful beside "
            "--init-from-task-change"
        ),
    )
    parser.add_argument(
        "--teacher",
        action="append",
        default=[],
        metavar="LOW:HIGH:POLICY",
        help=(
            "ADR-825: distil a teacher into this run on the steps whose goal "
            "(--teacher-goal) lies in [LOW, HIGH): its played action is a "
            "target beside PPO's loss. Repeat for one teacher per band; bands "
            "may not overlap. A teacher reads this bundle's channels and "
            "action table on the same model; its task may differ. Recorded "
            "by digest under training.distill"
        ),
    )
    parser.add_argument(
        "--teacher-goal", default="cmd", metavar="CHANNEL",
        help="the one-channel goal --teacher's bands are read on")
    parser.add_argument(
        "--distill-weight", type=float, default=1.0,
        help="the distillation term's weight beside PPO's loss (ADR-825)")
    parser.add_argument(
        "--stop-on-collapse", action="store_true",
        help="stop, with the reason, once the mean episode has collapsed "
             "(episode_collapse). Without it the collapse is only reported, "
             "on stderr and as progress.json's warning")
    parser.add_argument("--label", default="")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument(
        "--checkpoint-every", type=int, default=0, metavar="N",
        help=(
            "write a complete .cxpolicy every N iterations, plus the "
            "best-so-far. 0 disables. Costs about one iteration each: a "
            "rollout for the witness observations and 32 forward passes"
        ),
    )
    parser.add_argument(
        "--progress", default="", metavar="PATH",
        help=(
            "where to rewrite the progress file; defaults to progress.json "
            "beside --out. This is the artifact `remote_train.sh watch` and "
            "the dashboard read"
        ),
    )
    parser.add_argument(
        "--view-seconds", type=float, default=10.0, metavar="S",
        help=("at the end, play the policy for S seconds on the witness batch and write "
              "the farthest-travelled episode beside progress.json as view/: a mesh per "
              "body and a trace the dashboard plays (ADR-835). 0 disables"))
    parser.add_argument(
        "--view", default="", metavar="POLICY",
        help=("train nothing: replay POLICY (trained on this bundle) and write its view/ "
              "beside it, for a run made before ADR-835"))
    options = parser.parse_args(list(argv))
    if not options.out and not options.view:
        parser.error("--out is required (or --view POLICY)")
    return options


#: What a view's trace says it is: the schema the engine's own rollouts
#: carry, so the dashboard plays it unchanged (ADR-835).
VIEW_TRACE_SCHEMA = "cadex-assembly-simulation-trace-v1"


def _lathe(np, profile: Sequence[tuple[float, float]], segments: int = 16):
    """A solid of revolution about z from (radius, z) rows, bottom to top."""

    angles = np.linspace(0.0, 2.0 * math.pi, segments, endpoint=False)
    rings = [np.stack([r * np.cos(angles), r * np.sin(angles), np.full(segments, z)], axis=1)
             for r, z in profile]
    triangles = []
    for lower, upper in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            triangles += [(lower[i], lower[j], upper[j]), (lower[i], upper[j], upper[i])]
    return np.asarray(triangles)


def geom_triangles(mujoco, np, model, geom: int):
    """One geom as triangles in its body's frame, metres; None for what has no solid."""

    kind, size = int(model.geom_type[geom]), model.geom_size[geom]
    types = mujoco.mjtGeom
    arc = [-math.pi / 2 + math.pi * k / 16 for k in range(17)]
    if kind == types.mjGEOM_BOX:
        corner = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]) * size
        faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        local = np.asarray([tri for a, b, c, d in faces
                            for tri in ((corner[a], corner[b], corner[c]),
                                        (corner[a], corner[c], corner[d]))])
    elif kind in (types.mjGEOM_SPHERE, types.mjGEOM_ELLIPSOID):
        local = _lathe(np, [(math.cos(t), math.sin(t)) for t in arc])
        local = local * (size if kind == types.mjGEOM_ELLIPSOID else size[0])
    elif kind == types.mjGEOM_CAPSULE:
        r, h = float(size[0]), float(size[1])
        local = _lathe(np, [(r * math.cos(t), r * math.sin(t) - h) for t in arc[:9]]
                       + [(r * math.cos(t), r * math.sin(t) + h) for t in arc[8:]])
    elif kind == types.mjGEOM_CYLINDER:
        r, h = float(size[0]), float(size[1])
        local = _lathe(np, [(0.0, -h), (r, -h), (r, h), (0.0, h)])
    elif kind == types.mjGEOM_MESH:
        mesh = int(model.geom_dataid[geom])
        start, count = int(model.mesh_vertadr[mesh]), int(model.mesh_vertnum[mesh])
        first, faces = int(model.mesh_faceadr[mesh]), int(model.mesh_facenum[mesh])
        vertices = model.mesh_vert[start:start + count]
        local = vertices[model.mesh_face[first:first + faces]]
    else:
        return None
    rotation = np.zeros(9)
    mujoco.mju_quat2Mat(rotation, model.geom_quat[geom])
    return local @ rotation.reshape(3, 3).T + model.geom_pos[geom]


def binary_stl(np, triangles) -> bytes:
    """Triangles (metres) as a binary STL in millimetres, degenerate ones dropped."""

    import struct

    mm = np.asarray(triangles, dtype=np.float64) * 1000.0
    normal = np.cross(mm[:, 1] - mm[:, 0], mm[:, 2] - mm[:, 0])
    length = np.linalg.norm(normal, axis=1)
    keep = length > 1.0e-9
    mm, normal = mm[keep], normal[keep] / length[keep, None]
    rows = np.zeros(len(mm), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rows["n"], rows["v"] = normal, mm
    return b"cadex view".ljust(80, b" ") + struct.pack("<I", len(mm)) + rows.tobytes()


def write_view(directory: Path, model_xml: bytes, poses: Any, interval_s: float,
               *, source: str) -> Path:
    """``view/``: a mesh per body from its geoms and a trace of ``poses`` (ADR-835).

    Each body's mesh is in the body's own frame, named as the body is, and each
    trace frame places every body as the model's kinematics put it, so the
    dashboard plays the run on the very model it trained on, primitives and all.
    Geoms in group 3 and above (point masses, helpers) and invisible ones are left out.
    """

    import mujoco
    import numpy as np

    model = mujoco.MjModel.from_xml_string(model_xml.decode("utf-8"))
    data = mujoco.MjData(model)
    directory.mkdir(parents=True, exist_ok=True)
    bodies = []
    for body in range(1, model.nbody):
        parts = [geom_triangles(mujoco, np, model, g) for g in range(model.ngeom)
                 if int(model.geom_bodyid[g]) == body and int(model.geom_group[g]) < 3
                 and float(model.geom_rgba[g][3]) > 0.0]
        parts = [p for p in parts if p is not None and len(p)]
        if not parts:
            continue
        name = model.body(body).name or f"body{body}"
        write_atomically(directory / f"{name}.stl", binary_stl(np, np.concatenate(parts)))
        bodies.append((body, name))
    frames = []
    for step, qpos in enumerate(np.asarray(poses, dtype=np.float64)):
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        frames.append({"nominal_time_s": round(step * interval_s, 4), "component_placements": {
            name: {"position_mm": [round(float(v) * 1000.0, 2) for v in data.xpos[i]],
                   "rotation_xyzw": [round(float(v), 6)
                                     for v in (*data.xquat[i][1:], data.xquat[i][0])]}
            for i, name in bodies}})
    actuators = [{"actuator": model.actuator(a).name, "unit": "rad",
                  "low": float(model.actuator_ctrlrange[a][0]),
                  "high": float(model.actuator_ctrlrange[a][1])} for a in range(model.nu)]
    trace = {"schema": VIEW_TRACE_SCHEMA, "source": source,
             "parameters": {"frames_per_second": round(1.0 / interval_s, 2)},
             "actuator_channels": actuators, "frames": frames}
    path = directory / "trace.json"
    write_atomically(path, json.dumps(trace, separators=(",", ":")).encode("utf-8"))
    return path


def view_only(options: argparse.Namespace, bundle: dict[str, Any]) -> int:
    """``--view POLICY``: replay a finished policy and write its ``view/``."""

    policy = Path(options.view).expanduser()
    header = decode_policy(policy.read_bytes(), context=str(policy))["header"]
    network = header.get("network") or {}
    options.hidden = [int(b) for _a, b in (network.get("layers") or [])[:-1]]
    options.activation = str(network.get("activation") or options.activation)
    options.init_from, options.iterations = str(policy), 0
    trained = train(bundle, options)
    if trained.get("view_qpos") is None:
        raise SystemExit("--view: the replay produced no poses (see above)")
    path = write_view(policy.parent / "view", bundle["model_xml"], trained["view_qpos"],
                      float(bundle["task"]["episode"]["control_interval_s"]),
                      source=f"cadex_train --view {policy.name}")
    print(json.dumps({"view": str(path), "frames": len(trained["view_qpos"])}))
    return 0


def main(argv: Sequence[str]) -> int:
    options = arguments(argv[1:])

    try:
        import CadexDynamics  # noqa: F401
    except Exception:
        cadex_importable = False
    else:
        cadex_importable = True

    import jax.numpy as jnp

    bundle = load_bundle(options.bundle, globals_for(jnp))
    if options.family:
        # ADR-759: the bundle is variant 0; its digests name the run.
        bundle["family"] = [bundle] + [load_bundle(path, globals_for(jnp))
                                       for path in options.family]
        check_family(bundle["family"])
    if options.view:
        return view_only(options, bundle)
    target = Path(options.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    progress_path = (
        Path(options.progress) if options.progress
        else target.parent / "progress.json"
    )
    started_at = time.time()
    written: list[dict[str, Any]] = []

    def emit(tag: str, iteration: int, reward: float,
             trained: dict[str, Any]) -> None:
        """One mid-run checkpoint, as a policy the engine would accept.

        Not a weight dump. The whole value of a checkpoint here is that you
        can pull it off the box while the run is still going, paste its
        digest into ``assembly.policy``, rebuild and *watch it* -- which is
        only true if it is the same container the final policy is.
        """

        path = checkpoint_path(target, tag)
        header = policy_header(bundle, options, trained,
                               cadex_importable=cadex_importable)
        blob = checked_policy(header, trained, what=f"The {tag} checkpoint")
        write_atomically(path, blob)
        written.append({
            "tag": tag,
            "iteration": int(iteration),
            "path": path.name,
            "bytes": len(blob),
            "sha256": hashlib.sha256(blob).hexdigest(),
            # The reward of the iteration this policy's *weights* come
            # from, which for the best-so-far is not the last row of the
            # curve. A checkpoint labelled with somebody else's number is
            # the one thing a comparison table cannot survive.
            "reward_per_step": float(reward),
        })
        if not options.quiet:
            print(f"checkpoint {path.name}  ({written[-1]['sha256'][:12]})",
                  file=sys.stderr)

    last_report: dict[str, Any] = {}

    def report(**fields: Any) -> None:
        """``progress.json``, rewritten atomically.

        The one artifact everything downstream reads: `remote_train.sh
        watch` polls it over rsync, and the dashboard reads the
        copy that lands next to the project. Neither of them parses this
        program's stderr, and that is deliberate -- ADR-093's finding was
        that a receipt taken from a stream is a receipt something else can
        write into.
        """

        last_report.update(fields)
        if "curve" in fields:
            last_report["curve"] = list(fields["curve"])
        if "best" in fields:
            last_report["best"] = dict(fields["best"])
        fields = dict(last_report)
        curve = list(fields.pop("curve", ()) or ())
        best = dict(fields.pop("best", ()) or {})
        iteration = int(fields.get("iteration", -1))
        total = int(fields.get("total", 0))
        wall = float(fields.get("wall", 0.0))
        done = iteration + 1
        payload = {
            "schema": PROGRESS_SCHEMA,
            "state": str(fields.get("state", "training")),
            "iteration": iteration,
            "total": total,
            "wall_time_s": wall,
            # Straight-line from what has run so far. It is wrong early --
            # the first iteration carries the JIT compile -- and it is what
            # anybody would compute by hand from the numbers beside it.
            "eta_s": (
                (wall / done) * (total - done) if done > 0 and total > done
                else 0.0
            ),
            "started_at": started_at,
            "updated_at": time.time(),
            "task_sha256": bundle["task_sha256"],
            "model_sha256": bundle["model_sha256"],
            "device": str(fields.get("device", "")),
            "reward_per_step": (
                float(curve[-1]["reward_per_step"]) if curve else None
            ),
            "loss": float(curve[-1]["loss"]) if curve else None,
            # Additive under the same schema: its readers use
            # `.get`, so a `progress.json` written before ADR-101 still
            # renders -- it renders this row as "-".
            "episode_steps": (
                None if not curve or curve[-1].get("episode_steps") is None
                else float(curve[-1]["episode_steps"])
            ),
            # Additive on exactly the same terms as `episode_steps` above,
            # under the same unchanged schema (ADR-103): mean exploration
            # sigma, so a runaway entropy bonus is visible in the panel and
            # in `watch` while the run is still going rather than after it.
            "action_std": (
                None if not curve or curve[-1].get("action_std") is None
                else float(curve[-1]["action_std"])
            ),
            # Additive on the same terms again, under the same unchanged
            # schema: the curve itself, as compact [iteration, reward] pairs
            # capped at CURVE_POINTS_CAP, so a panel can draw the run's
            # shape rather than its last number. A reader written before
            # this field renders exactly what it always did.
            "curve": decimated_curve(curve),
            "loss_curve": decimated_curve(curve, key="loss"),
            "episode_steps_curve": decimated_curve(curve, key="episode_steps"),
            # Additive on the same terms (ADR-606): the exploration sigma's
            # history, so the dashboard's Status charts it beside reward,
            # loss and episode length rather than only its last value.
            "action_std_curve": decimated_curve(curve, key="action_std"),
            "best_reward_per_step": (
                None if not best or best.get("iteration", -1) < 0
                else float(best["reward_per_step"])
            ),
            "best_iteration": int(best.get("iteration", -1)) if best else -1,
            "out": target.name,
            "label": str(options.label or ""),
            "checkpoints": list(written),
            "error": str(fields.get("error", "")),
            # Additive under the same schema (ADR-410): the collapse the run
            # has detected, readable while it is still going.
            "warning": str(fields.get("warning", "")),
        }
        write_atomically(
            progress_path,
            json.dumps(payload, sort_keys=True, indent=2).encode("utf-8"),
        )

    report(state="starting", iteration=-1, total=int(options.iterations),
           curve=[], best={}, wall=0.0, device="")
    try:
        trained = train(bundle, options, emit=emit, progress=report)

        header = policy_header(bundle, options, trained,
                               cadex_importable=cadex_importable)
        blob = checked_policy(header, trained, what="This policy")
        worst, _sample, _action = witness_disagreement(header, trained["parameters"])
        margin = POLICY_WITNESS_TOLERANCE / max(worst, 1.0e-30)
        if not options.quiet:
            print(f"witness agrees to {worst:.3e} ({margin:,.0f}x inside the "
                  f"engine's tolerance)", file=sys.stderr)
        # A short run cannot prove a long one will pass, and saying so is the
        # whole point of printing the margin rather than a verdict. The witness
        # error is a *relative* one, so it grows with the activations a policy
        # learns: the run this check was written for measured a 14x margin after
        # 2 iterations and failed outright after 2000. A margin this thin means
        # the same run at length will not survive, and the time to know that is
        # now.
        if margin < 100.0:
            print(
                f"WARNING: {margin:,.0f}x is a thin margin. This error scales "
                f"with the size of the activations a policy learns, so a longer "
                f"run on this task will very likely be refused even though this "
                f"one passed. Do not start one on the strength of this result.",
                file=sys.stderr,
            )

        write_atomically(target, blob)
        curve = trained["reward_curve"]
        best_row = max(curve, key=lambda row: row["reward_per_step"]) if curve else None
        report(
            state="done",
            iteration=len(curve) - 1,
            total=int(options.iterations),
            curve=curve,
            best=({"iteration": best_row["iteration"],
                   "reward_per_step": best_row["reward_per_step"]}
                  if best_row else {}),
            wall=float(trained["wall_time_s"]),
            device=trained["backend"],
        )
        if trained.get("view_qpos") is not None:
            try:
                write_view(progress_path.parent / "view", bundle["model_xml"],
                           trained["view_qpos"],
                           float(bundle["task"]["episode"]["control_interval_s"]),
                           source=f"cadex_train's witness batch, {target.name}")
            except Exception as error:  # noqa: BLE001 -- the view never fails a run
                print(f"view: not written ({type(error).__name__}: {error})", file=sys.stderr)

    except BaseException as error:
        # Training or final policy publication failed. Publish the failure
        # so observers do not remain on "training". The exception is re-raised
        # unchanged: this adds a line to an artifact, it does not handle
        # anything.
        report(state="failed", wall=time.time() - started_at,
               error=f"{type(error).__name__}: {error}")
        raise

    print(json.dumps({
        "out": str(target),
        "bytes": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
        "parameters": len(trained["parameters"]),
        "task_sha256": bundle["task_sha256"],
        "model_sha256": bundle["model_sha256"],
        "witness_samples": len(trained["witness_observations"]),
        "witness_error": worst,
        "witness_tolerance": POLICY_WITNESS_TOLERANCE,
        "reward_per_step": (curve[-1]["reward_per_step"] if curve else None),
        "episode_steps": (curve[-1].get("episode_steps") if curve else None),
        "action_std": (curve[-1].get("action_std") if curve else None),
        "best_reward_per_step": (
            best_row["reward_per_step"] if best_row else None
        ),
        "best_iteration": best_row["iteration"] if best_row else None,
        "wall_time_s": trained["wall_time_s"],
        "device": trained["backend"],
        "progress": str(progress_path),
        "checkpoints": [item["path"] for item in written],
        "cadex_importable": cadex_importable,
    }, sort_keys=True))
    return 0



if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
