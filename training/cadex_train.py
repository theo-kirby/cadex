#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later

"""One task bundle in, one ``.cxpolicy`` out, on a machine that has a GPU.

**This program is not part of the engine and is never installed into the
payload.** It lives at the repository root because it is a thing you *copy*
to another machine: ``pixi`` never sees it, CMake never installs it, and its
dependencies are pinned in ``training/requirements.txt`` and installed into
a venv on whatever box does the training. ``CARRIED_PYPI_PACKAGES`` stays
one entry long, which is what ADR-076 named that constant for.

The sibling of ``src/Mod/cadex/cadex_tests/dynamics_task_episode.py``, and
held to the same discipline: it imports only ``jax``, ``mujoco``,
``mujoco.mjx``, ``numpy`` and the standard library, and it reports whether
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

**Two evaluators became three.** ``CadexDynamics`` compiles reward
expressions, ``dynamics_task_episode.py`` compiles them again, and this
compiles them a third time under ``jax.numpy`` so they vectorise. Three is
where a whitelist drifts, so the bundle ships its ``functions`` array, this
file builds its own from scratch, and it **refuses outright** when the two
differ rather than failing partway through a training run. A test asserts
all three are equal.

**The container this writes is byte-identical to what the engine writes.**
``encode_policy`` in ``CadexDynamics`` and :func:`encode_policy` here are
two implementations of one format, and a test compares their bytes. That is
the same move the reward whitelist gets, for the same reason: this file
cannot import the engine, so the second copy is written down and pinned.

Usage::

    python cadex_train.py <root>/outputs/<name>-task.json \\
        --seed 0 --iterations 200 --out walk.cxpolicy
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import sys
import time
from typing import Any, Sequence

TASK_SCHEMA = "cadex-training-task-v1"
POLICY_SCHEMA = "cadex-policy-v1"
POLICY_MAGIC = b"CXPOLICY1\n"

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
#: shell's Training panel read. Versioned like every other file this tree
#: writes, because two of its three readers are on other machines.
PROGRESS_SCHEMA = "cadex-training-progress-v1"

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
    thing a reader can compare against ``CadexDynamics._REWARD_GLOBALS`` and
    against ``dynamics_task_episode.GLOBALS`` by eye as well as by test.

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


def check_policy_fits(
    header: dict[str, Any],
    bundle: dict[str, Any],
    options: argparse.Namespace,
) -> None:
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

    task = header.get("task") or {}
    if task.get("sha256") != bundle["task_sha256"]:
        refuse("the task digest", bundle["task_sha256"], task.get("sha256"))
    model = header.get("model") or {}
    if model.get("sha256") != bundle["model_sha256"]:
        refuse("the model digest", bundle["model_sha256"], model.get("sha256"))
    wanted_channels = channels(bundle["task"])
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


# ---------------------------------------------------------------------------
# The bundle, and the model beside it.
# ---------------------------------------------------------------------------


def load_bundle(bundle_path: str, table: dict[str, Any]) -> dict[str, Any]:
    """The task, its model's bytes, and the refusals that come before training.

    The same resolution ``dynamics_task_episode`` performs, and deliberately
    so: the model is referenced by a path relative to the *project root* and
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


def channels(task: dict[str, Any]) -> list[str]:
    return [
        str(channel)
        for record in task["observations"]
        for channel in record["channels"]
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


def randomised_models(mujoco: Any, xml: bytes, task: dict[str, Any], *,
                      base_seed: int, count: int) -> list[Any]:
    """One host ``MjModel`` per environment, each with its own draw.

    ``mj_setConst`` after a draw is not optional: M6 phase 0 measured that
    ``body_subtreemass`` is derived from ``body_mass`` there, so a mass draw
    that skipped it would change the mass and not what the solver does with
    it.
    """

    entries = list(task.get("randomisation") or ())
    models = []
    for index in range(count):
        model = mujoco.MjModel.from_xml_string(xml.decode("utf-8"))
        if entries:
            rng = random.Random(int(base_seed) + index)
            data = mujoco.MjData(model)
            for entry in entries:
                factor = rng.uniform(float(entry["low"]), float(entry["high"]))
                for field in entry["fields"]:
                    getattr(model, str(field["field"])).flat[
                        int(field["index"])
                    ] *= factor
            mujoco.mj_setConst(model, data)
        models.append(model)
    return models


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
    """The actor's forward pass, in the layout the container's blob records."""

    value = inputs
    last = len(parameters) - 1
    for index, (weight, bias) in enumerate(parameters):
        value = value @ weight + bias
        if index < last:
            value = jnp.tanh(value) if activation == "tanh" else jnp.maximum(value, 0.0)
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
# PPO.
# ---------------------------------------------------------------------------


def train(
    bundle: dict[str, Any],
    options: argparse.Namespace,
    *,
    emit: Any = None,
    progress: Any = None,
) -> dict[str, Any]:
    """Proximal policy optimisation over an MJX batch built from the bundle.

    Deliberately small and readable rather than a harness: everything it
    needs -- the observation slices, the action indices, the units, the
    reward, the termination rules, the episode schedule -- is in the bundle,
    and the point of M7 is that nothing else has to be.

    ``emit(tag, iteration, reward, trained)`` is called for each checkpoint
    and for the best-so-far policy; ``progress(**fields)`` after every
    iteration.
    Both are injected rather than done here because this function has never
    seen a filesystem and there is no reason for it to start: it produces
    ``trained`` dicts, and :func:`main` is what turns one into a file. A run
    with neither passes no-ops and takes exactly the path it always took.
    """

    import jax
    import jax.numpy as jnp
    import numpy as np
    import mujoco
    import mujoco.mjx as mjx

    emit = emit or (lambda tag, iteration, reward, trained: None)
    progress = progress or (lambda **fields: None)

    table = globals_for(jnp)
    task = bundle["task"]
    episode = task["episode"]
    names = channels(task)
    actions = list(task["actions"])

    low = jnp.asarray([float(a["low"]) for a in actions], dtype=jnp.float32)
    high = jnp.asarray([float(a["high"]) for a in actions], dtype=jnp.float32)
    ctrl_scale = jnp.asarray([float(a["scale"]) for a in actions], dtype=jnp.float32)
    ctrl_index = np.asarray([int(a["index"]) for a in actions], dtype=np.int32)
    output_scale = [(float(a["high"]) - float(a["low"])) / 2.0 for a in actions]
    output_bias = [(float(a["high"]) + float(a["low"])) / 2.0 for a in actions]

    # ADR-138: the command may be low-passed before it reaches `data.ctrl`.
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

    envs = int(options.envs)
    hosts = randomised_models(mujoco, bundle["model_xml"], task,
                              base_seed=int(options.seed), count=envs)
    key_id = mujoco.mj_name2id(hosts[0], mujoco.mjtObj.mjOBJ_KEY,
                               str(episode["reset_keyframe"]))
    if key_id < 0:
        raise SystemExit(
            f"the model carries no {episode['reset_keyframe']!r} keyframe"
        )
    reset_qpos = jnp.asarray(hosts[0].key_qpos[key_id], dtype=jnp.float32)
    reset_qvel = jnp.zeros((hosts[0].nv,), dtype=jnp.float32)
    nbody = int(hosts[0].nbody)

    randomised_fields = sorted({
        str(field["field"])
        for entry in task.get("randomisation") or ()
        for field in entry["fields"]
    })
    put = [mjx.put_model(host) for host in hosts]
    model = put[0]
    if randomised_fields and envs > 1:
        # Only the fields a draw actually moved are batched; everything else
        # is shared, which is what keeps the batched model the size of one.
        model = model.tree_replace({
            field: jnp.stack([getattr(m, field) for m in put])
            for field in randomised_fields
        })
        model_axes = jax.tree.map(lambda _: None, put[0]).tree_replace(
            {field: 0 for field in randomised_fields}
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

    def observe(data):
        return jnp.take(data.sensordata, gather) * obs_scale

    def named(vector):
        return {name: vector[index] for index, name in enumerate(names)}

    def reward_of(vector):
        values = named(vector)
        total = jnp.float32(0.0)
        for weight, code in reward_terms:
            total = total + weight * eval(code, table, dict(values))
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
    # (ADR-084), so the second copy is written down and a test pins it.
    variation_entries = list(task.get("reset_variation") or ())
    push_entries = list(task.get("disturbance") or ())

    def varied_reset(key):
        """One reset pose per environment, each with its own draw.

        The tilt quaternion is left-multiplied onto the base's own, which is
        a world-frame rotation about the base's frame origin -- so the whole
        mechanism swings rigidly and every joint angle stays where the solve
        left it. Joint angles are never touched here and there is no code
        path that could: the reset pose is the solved one with the soles on
        the floor, and a few degrees at a knee is a foot through it.
        """

        qpos = jnp.tile(reset_qpos, (envs, 1))
        qvel = jnp.tile(reset_qvel, (envs, 1))
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
            qvel = qvel.at[:, dof + 3 : dof + 6].set(spin)
            # ...and the WORLD frame, three numbers earlier in the same
            # array, which is where it keeps the linear one.
            qvel = qvel.at[:, dof + 0].set(speed * jnp.cos(speed_azimuth))
            qvel = qvel.at[:, dof + 1].set(speed * jnp.sin(speed_azimuth))
            qvel = qvel.at[:, dof + 2].set(jnp.zeros_like(speed))
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

    def step_env(m, data, surface, *filter_state):
        """One control step: clamp, scale into ctrl, integrate, observe, score.

        **The only unit arithmetic on this boundary is the bundle's own
        ``clamp then x scale``**, which is the same two operations
        ``CadexDynamics.evaluate_episode`` performs. M7 adds no conversion
        site, here or anywhere, and ``test_dynamics_units`` greps this file
        to keep that true.
        """

        clamped = jnp.clip(surface, low, high)
        if filtering:
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
            clamped = jnp.where(
                first, clamped,
                action_filter_alpha * clamped
                + (1.0 - action_filter_alpha) * previous)
        ctrl = data.ctrl.at[ctrl_index].set(clamped * ctrl_scale)
        data = data.replace(ctrl=ctrl)

        def one(d, _):
            return mjx.step(m, d), None

        data, _ = jax.lax.scan(one, data, None, length=per_action)
        vector = observe(data)
        if filtering:
            # The ISSUED command joins the outputs, because it is the next
            # step's filter state and there is nowhere else to get it: it is
            # not recoverable from `data.ctrl`, which holds it multiplied by
            # the actuator scale.
            return data, vector, reward_of(vector), done_of(vector), clamped
        return data, vector, reward_of(vector), done_of(vector)

    # `(previous, first)` are per environment, so they vmap on axis 0 like
    # `surface`. Empty at alpha 1.0, which is what keeps the traced signature
    # identical to the pre-ADR-138 one.
    _filter_axes = (0, 0) if filtering else ()
    batched_step = (
        jax.vmap(step_env, in_axes=(None, 0, 0) + _filter_axes)
        if model_axes is None
        else jax.vmap(step_env, in_axes=(model_axes, 0, 0) + _filter_axes)
    )
    batched_forward = (
        jax.vmap(mjx.forward, in_axes=(None, 0)) if model_axes is None
        else jax.vmap(mjx.forward, in_axes=(model_axes, 0))
    )

    shapes = layer_shapes(len(names), len(actions), options.hidden)
    critic_shapes = layer_shapes(len(names), 1, options.hidden)
    key = jax.random.PRNGKey(int(options.seed))
    key, start_key, actor_key, critic_key = jax.random.split(key, 4)

    make = jax.vmap(lambda _: mjx.make_data(put[0]))(jnp.arange(envs))
    # The first episode is drawn like every other one. It would be easy to
    # start the batch at the nominal pose and only vary on reset; that would
    # make the first `unroll` steps of training the one episode M9 exists to
    # stop happening.
    start_key, first_qpos, first_qvel = varied_reset(start_key)
    _start_key, first_forces, first_starts = drawn_pushes(start_key)
    data = batched_forward(model, make.replace(
        qpos=first_qpos, qvel=first_qvel,
    ))
    control_interval = float(episode["control_interval_s"])
    # The environment state carried between iterations. It grew from one
    # `mjx.Data` to a four-tuple in M9: a disturbance is a property of the
    # episode, so its draw and the episode-local clock it is tested against
    # have to live exactly as long as the physics state does. ADR-101 added
    # the fifth member: the step counter the horizon is tested against, which
    # is episode-local for exactly the same reason `elapsed` is.
    state = (data, first_forces, first_starts,
             jnp.zeros((envs,), dtype=jnp.float32),
             jnp.zeros((envs,), dtype=jnp.int32))
    if filtering:
        # ADR-138's sixth member: the previous ISSUED command, per
        # environment. Episode-local for exactly the reason `elapsed` and
        # `steps` are -- a filter that carried across a reset would low-pass
        # the first command of an episode towards the last command of the
        # one before it, which is a different machine.
        #
        # The initial value is never read: `steps` is zero for every
        # environment here, so the first step of the first episode takes the
        # unfiltered branch.
        state = state + (jnp.zeros((envs, len(actions)), dtype=jnp.float32),)
    actor = initial_parameters(jax, jnp, actor_key, shapes)
    critic = initial_parameters(jax, jnp, critic_key, critic_shapes)
    log_std = jnp.full((len(actions),), math.log(float(options.initial_std)),
                       dtype=jnp.float32)

    # Adam, hand-rolled, so that requirements.txt stays four lines. The
    # trainer is a thing you copy to a box; every dependency is one more
    # thing that has to install there.
    def zeros_like(tree):
        return jax.tree.map(jnp.zeros_like, tree)

    params = {"actor": actor, "critic": critic, "log_std": log_std}
    moment1, moment2 = zeros_like(params), zeros_like(params)

    mean = jnp.zeros((len(names),), dtype=jnp.float32)
    variance = jnp.ones((len(names),), dtype=jnp.float32)
    seen = jnp.float32(1.0e-4)

    init_from_provenance: dict[str, Any] | None = None
    if getattr(options, "init_from", ""):
        # Applied here, after the fresh network and the zeroed Adam moments
        # exist, and that ordering is the whole trick. Every moment is
        # `zeros_like(params)`, so swapping the actor in *before* they are
        # taken would be identical -- and swapping it in after would leave
        # them the right shape anyway. "Leave the optimiser fresh" is
        # therefore free rather than a compromise, which is what makes this
        # a warm start and not a resume: a resume would need the moments,
        # and the container does not carry them.
        source = Path(options.init_from).expanduser()
        try:
            blob = source.read_bytes()
        except OSError as exc:
            raise SystemExit(f"--init-from: cannot read {source}: {exc}") from exc
        decoded = decode_policy(blob, context=str(source))
        check_policy_fits(decoded["header"], bundle, options)
        restored = unflatten_parameters(np, decoded["weights"], shapes)
        params["actor"] = [
            (jnp.asarray(weight), jnp.asarray(bias))
            for weight, bias in restored
        ]
        moment1, moment2 = zeros_like(params), zeros_like(params)

        # Without this the transfer is mostly wasted. The actor was trained
        # to read *normalised* observations, and a fresh normaliser feeds it
        # raw ones -- so a policy that stood up perfectly well starts by
        # seeing every channel shifted and scaled wrongly, and spends its
        # early iterations unlearning that before it can improve on
        # anything.
        #
        # `seen` is not in the container and restarts at its usual 1.0e-4, so
        # the restored statistics are re-estimated quickly rather than held.
        # That is the conservative direction: a stale mean that cannot move
        # would be worse than one that can.
        stats = decoded["header"].get("normaliser") or {}
        if stats.get("mean") is not None and stats.get("std") is not None:
            mean = jnp.asarray(stats["mean"], dtype=jnp.float32)
            variance = jnp.asarray(
                np.square(np.asarray(stats["std"], dtype=np.float32)),
                dtype=jnp.float32,
            )

        source_training = decoded["header"].get("training") or {}
        init_from_provenance = {
            "sha256": hashlib.sha256(blob).hexdigest(),
            "label": str(decoded["header"].get("label") or ""),
            "iterations": source_training.get("iterations"),
            # Which trainer produced the weights being warmed. A warm start
            # across an update-rule change is a thing somebody will want to
            # know about later, and this is the only place it can be said.
            "trainer_sha256": source_training.get("trainer_sha256"),
        }
        if not options.quiet:
            print(
                f"init-from  {source.name}  "
                f"iterations={source_training.get('iterations')}  "
                f"sha256={init_from_provenance['sha256'][:16]}…",
                flush=True,
            )

    scale_out = jnp.asarray(output_scale, dtype=jnp.float32)
    bias_out = jnp.asarray(output_bias, dtype=jnp.float32)

    def net(parameters, inputs):
        """The MLP, batch-capable: ``x @ W + b`` broadcasts over leading axes.

        Deliberately not wrapped in ``vmap``. ``forward`` takes ``jnp`` as an
        argument so it stays importable by a test without a live jax import,
        and a module is not a pytree -- so mapping over it is not merely slow,
        it is a type error waiting for the first person who tries.
        """

        return forward(jnp, parameters, inputs)

    def normalise(vector, mean, variance):
        return (vector - mean) / jnp.sqrt(jnp.maximum(variance, 1.0e-8))

    def surface_of(raw):
        return jnp.tanh(raw) * scale_out + bias_out

    def gaussian_logp(sampled, raw, log_std):
        return jnp.sum(
            -0.5 * ((sampled - raw) / jnp.exp(log_std)) ** 2
            - log_std - 0.5 * math.log(2.0 * math.pi),
            axis=-1,
        )

    unroll = int(options.unroll)

    def rollout(params, state, mean, variance, key):
        """``unroll`` control steps of every environment, with resets.

        The carry grew from ``(data, key)`` to ``(data, forces, starts,
        elapsed)`` because a disturbance is a property of the *episode* and
        not of the step: the draw has to survive every step between the reset
        that made it and the reset that replaces it, and the window has to be
        tested against a clock that rewinds when the episode does.

        It gained ``steps`` in ADR-101, and that member is what makes this an
        episode at all. Before it, ``done`` was the task's termination terms
        and nothing else, so an environment the policy kept upright ran for
        ever: past the last shove window, never pushed again, never re-drawn,
        standing still and collecting the ``alive`` bonus. The bundle
        declares 600 steps and ``CadexDynamics.evaluate_episode`` honours it;
        this now honours the same number.
        """

        def stepped(carry, _):
            # `filter_carry` is ADR-138's `[previous_action]` when filtering
            # and EMPTY otherwise, so at alpha 1.0 the carry pytree is the
            # six-tuple it has always been.
            data, key, forces, starts, elapsed, steps, *filter_carry = carry
            key, act_key = jax.random.split(key)
            vector = jax.vmap(observe)(data)
            normalised = normalise(vector, mean, variance)
            raw = net(params["actor"], normalised)
            noise = jax.random.normal(act_key, raw.shape, dtype=jnp.float32)
            sampled = raw + noise * jnp.exp(params["log_std"])
            logp = gaussian_logp(sampled, raw, params["log_std"])
            surface = surface_of(sampled)
            value = net(params["critic"], normalised)[:, 0]

            if push_entries:
                data = data.replace(
                    xfrc_applied=applied_forces(forces, starts, elapsed)
                )
            if filtering:
                # `steps` here is the count of steps ALREADY taken this
                # episode, because it is incremented below -- so `steps == 0`
                # is exactly the first step of an episode and needs no
                # separate flag in the carry.
                data, landed, reward, terminated, issued = batched_step(
                    model, data, surface, filter_carry[0], steps == 0)
            else:
                data, landed, reward, terminated = batched_step(
                    model, data, surface)
            elapsed = elapsed + control_interval
            steps = steps + 1
            # An integer compare, not a float one on `elapsed`: 600 additions
            # of a 0.02 s interval do not land on 12.0, and an episode whose
            # length depends on which side of the rounding the last step fell
            # is not the episode the bundle declares.
            timeout = steps >= horizon
            # Two flags from here down, and they are not interchangeable.
            # `done` ends the episode either way; `terminated` says the
            # *future* ended rather than merely our looking at it, and that
            # is the one the bootstrap in `advantages` is cut on.
            done = jnp.logical_or(terminated, timeout)

            # Every environment redraws every step and the draw is *selected*
            # where done, rather than drawn only where done. Under `vmap`
            # there is no other shape available: a branch per environment is
            # not something a jitted batch can take, and a uniform draw is
            # cheaper than the `lax.cond` that would avoid it.
            key, reset_key, push_key = jax.random.split(key, 3)
            _unused, fresh_qpos, fresh_qvel = varied_reset(reset_key)
            _unused, fresh_forces, fresh_starts = drawn_pushes(push_key)
            data = jax.tree.map(
                lambda new, start: jnp.where(
                    done.reshape((-1,) + (1,) * (new.ndim - 1)), start, new),
                data,
                data.replace(qpos=fresh_qpos, qvel=fresh_qvel),
            )
            if variation_entries:
                # The reset pose is no longer a constant, so the observation
                # a policy acts on after a reset has to be of *that* pose.
                # Without this the first step of every episode is taken on
                # the previous episode's last observation -- harmless while
                # every episode started identically, and the whole feature
                # otherwise. It costs one `mjx.forward` per control step and
                # is skipped entirely by a task that declares no variation.
                data = batched_forward(model, data)
            forces = jnp.where(done[:, None, None], fresh_forces, forces)
            starts = jnp.where(done[:, None], fresh_starts, starts)
            elapsed = jnp.where(done, 0.0, elapsed)
            steps = jnp.where(done, 0, steps)
            if filtering:
                # Zeroed on `done` for the same reason `elapsed` and `steps`
                # are. The value is not read after a reset -- `steps` is 0,
                # so the next step takes the unfiltered branch -- but leaving
                # the finished episode's last command in the carry would make
                # a debugger and a reader both wrong about what the state
                # means.
                filter_carry = [jnp.where(done[:, None], 0.0, issued)]
            return (data, key, forces, starts, elapsed, steps,
                    *filter_carry), (
                vector, sampled, logp, value, reward, done, landed, terminated
            )

        data, forces, starts, elapsed, steps, *filter_state = state
        carry, traces = jax.lax.scan(
            stepped, (data, key, forces, starts, elapsed, steps,
                      *filter_state), None,
            length=unroll,
        )
        data, key, forces, starts, elapsed, steps, *filter_state = carry
        # No trailing bootstrap: `landed` is the post-step, pre-reset
        # observation at *every* step, so the critic's value of it is the
        # next-state value the whole way through -- including at a boundary,
        # where `values[t + 1]` is the value of an environment that has
        # already been reset. `advantages` reads it directly.
        return (data, forces, starts, elapsed, steps, *filter_state), key, traces

    discount = float(options.discount)
    lam = float(options.gae_lambda)

    def advantages(rewards, values, dones, terminals, following):
        """GAE, with a timeout bootstrapped and a failure cut.

        **The one line in this file where a plausible-looking edit is
        silently wrong** (ADR-101), so it is written out rather than folded
        together: ``terminal`` cuts the bootstrap, ``done`` cuts the carry.

        A *failure* ends the future, so the state that follows it is worth
        nothing. A *timeout* ends only our looking at it, and the state we
        landed in is worth whatever the critic thinks -- feeding a timeout
        into the ``(1 - done)`` bootstrap term teaches the critic that
        surviving to step 600 is worth exactly as much as falling over, which
        at ``--discount 0.99`` over a 600-step episode is not a small lie.
        The *carry* is cut on ``done``, because the trajectory genuinely
        discontinues either way: the next row belongs to a fresh episode.

        ``following`` is ``V(landed)`` -- the value of the post-step,
        pre-reset observation -- so there is no shift and no separate
        trailing bootstrap to get wrong.
        """

        def one(carry, row):
            reward, value, done, terminal, following = row
            delta = reward + discount * following * (1.0 - terminal) - value
            carry = delta + discount * lam * (1.0 - done) * carry
            return carry, carry

        _, out = jax.lax.scan(
            one, jnp.zeros((envs,), dtype=jnp.float32),
            (rewards, values, dones.astype(jnp.float32),
             terminals.astype(jnp.float32), following),
            reverse=True,
        )
        return out

    clip = float(options.clip)
    entropy_weight = float(options.entropy)
    value_weight = float(options.value_weight)

    def loss(params, vectors, sampled, old_logp, target, advantage, mean, variance):
        normalised_obs = normalise(vectors, mean, variance)
        raw = net(params["actor"], normalised_obs)
        log_std = params["log_std"]
        logp = gaussian_logp(sampled, raw, log_std)
        ratio = jnp.exp(logp - old_logp)
        normalised = (advantage - advantage.mean()) / (advantage.std() + 1.0e-8)
        surrogate = jnp.minimum(
            ratio * normalised,
            jnp.clip(ratio, 1.0 - clip, 1.0 + clip) * normalised,
        ).mean()
        values = net(params["critic"], normalised_obs)[:, 0]
        value_loss = ((values - target) ** 2).mean()
        entropy = jnp.sum(log_std + 0.5 * math.log(2.0 * math.pi * math.e))
        return -surrogate + value_weight * value_loss - entropy_weight * entropy

    gradient = jax.value_and_grad(loss)
    learning_rate = float(options.learning_rate)
    epochs = int(options.epochs)

    @jax.jit
    def iterate(params, moment1, moment2, state, mean, variance, seen, key, step):
        state, key, traces = rollout(params, state, mean, variance, key)
        vectors, sampled, logp, values, rewards, dones, landed, terminals = traces

        # The normaliser's statistics follow what the policy actually saw.
        flat = landed.reshape((-1, len(names)))
        count = jnp.float32(flat.shape[0])
        batch_mean = flat.mean(axis=0)
        batch_var = flat.var(axis=0)
        total = seen + count
        delta = batch_mean - mean
        new_mean = mean + delta * count / total
        new_variance = (
            variance * seen + batch_var * count + delta**2 * seen * count / total
        ) / total

        # One extra critic pass, over the states the steps actually landed
        # in. It replaces the shifted `values` and the trailing bootstrap
        # both, and it is the only value of the next state that is correct at
        # an episode boundary.
        landed_values = net(params["critic"],
                            normalise(landed, mean, variance))[..., 0]
        advantage = advantages(rewards, values, dones, terminals, landed_values)
        target = advantage + values

        # Mean episode length: steps taken in this batch over episodes that
        # ended in it. There was no external observable for this at all until
        # ADR-101, which is why two runs reported a rising reward while the
        # policy they were reporting on got worse. With nothing ending, this
        # reads the size of the whole batch -- a number that cannot be an
        # episode length, and is meant to be read as "nothing is resetting".
        endings = jnp.sum(dones.astype(jnp.float32))
        episode_steps = jnp.float32(unroll * envs) / jnp.maximum(endings, 1.0)

        shape = (-1,)
        flat_vectors = vectors.reshape((-1, len(names)))
        flat_sampled = sampled.reshape((-1, len(actions)))
        flat_logp = logp.reshape(shape)
        flat_target = target.reshape(shape)
        flat_advantage = advantage.reshape(shape)

        def epoch(carry, _):
            params, moment1, moment2, step = carry
            value, grads = gradient(params, flat_vectors, flat_sampled,
                                     flat_logp, flat_target, flat_advantage,
                                     mean, variance)
            step = step + 1
            moment1 = jax.tree.map(lambda m, g: 0.9 * m + 0.1 * g, moment1, grads)
            moment2 = jax.tree.map(lambda v, g: 0.999 * v + 0.001 * g * g,
                                    moment2, grads)
            bias1 = 1.0 - 0.9**step
            bias2 = 1.0 - 0.999**step
            params = jax.tree.map(
                lambda p, m, v: p - learning_rate * (m / bias1)
                / (jnp.sqrt(v / bias2) + 1.0e-8),
                params, moment1, moment2,
            )
            return (params, moment1, moment2, step), value

        (params, moment1, moment2, step), losses = jax.lax.scan(
            epoch, (params, moment1, moment2, step), None, length=epochs)
        return (params, moment1, moment2, state, new_mean, new_variance, total,
                key, step, rewards.mean(), losses[-1], episode_steps)

    # -----------------------------------------------------------------
    # A snapshot: everything `main` needs to write a complete, witnessed
    # policy, as of whatever parameters it is handed.
    # -----------------------------------------------------------------
    #
    # Lifted out of the tail of this function in M9 so that it can run
    # *during* training as well as after it. Two properties make that safe
    # and they are both worth stating:
    #
    #   * it is **pure with respect to the training state**. The witness
    #     rollout it runs returns a new `state` and a new `key` and this
    #     discards both, so a run with checkpoints on takes exactly the same
    #     trajectory as one without. A checkpoint that perturbed the run it
    #     was reporting on would be a measurement instrument that moved the
    #     thing it measured.
    #   * it takes `params`, `mean` and `variance` as arguments rather than
    #     closing over them, so the same function writes the current policy
    #     and the best-so-far one.
    #
    # Cost is roughly one iteration: a `rollout()` for the observations plus
    # 32 forward passes at `highest` precision. Every hundredth iteration of
    # two thousand is one per cent.
    def snapshot(params, mean, variance, curve, wall):
        _state, _key, traces = rollout(params, state, mean, variance, key)
        seen_vectors = np.asarray(traces[6]).reshape((-1, len(names)))
        if seen_vectors.shape[0] >= WITNESS_SAMPLES:
            picks = np.linspace(
                0, seen_vectors.shape[0] - 1, WITNESS_SAMPLES
            ).astype(int)
        else:
            picks = np.arange(seen_vectors.shape[0])
        witness_obs = seen_vectors[picks].astype(np.float32)

        # The weights are rounded to float32 *before* the witness is
        # computed, because float32 is what the container stores and what
        # the engine reads back. A witness taken against unrounded weights
        # would be a witness about numbers that never land.
        stored = [
            (np.asarray(w, dtype=np.float32), np.asarray(b, dtype=np.float32))
            for w, b in params["actor"]
        ]
        stored_jax = [(jnp.asarray(w), jnp.asarray(b)) for w, b in stored]
        stored_mean = np.asarray(mean, dtype=np.float32)
        stored_std = np.sqrt(
            np.maximum(np.asarray(variance, dtype=np.float32), 1.0e-8)
        ).astype(np.float32)
        stored_std = np.where(stored_std == 0.0, np.float32(1.0), stored_std)

        def witness_action(vector):
            normalised = (
                jnp.asarray(vector) - jnp.asarray(stored_mean)
            ) / jnp.asarray(stored_std)
            raw = forward(jnp, stored_jax, normalised)
            return (jnp.tanh(raw) * jnp.asarray(output_scale)
                    + jnp.asarray(output_bias))

        # ``highest`` is load-bearing, and the default is not merely slower
        # to be right about -- it is wrong for this purpose.
        #
        # ``jax.vmap`` turns each layer's matrix-vector product into a
        # *batched* matmul, and XLA puts a batched float32 matmul on Ampere+
        # tensor cores at TF32: a 10-bit mantissa, eps ~4.9e-4. The engine
        # evaluates the same weights in float64. Measured on the legs
        # policy: the vmapped witness sits 1.43e-4 from float64 and the
        # identical arithmetic run one row at a time sits 5.14e-8 -- 2800x
        # closer, and the same weights either way. So the witness was not
        # recording what the network computes, it was recording what a
        # tensor core rounds it to, and the engine refused a sound policy
        # for it.
        #
        # The error is a fixed *relative* one, so it grows with the
        # activations a policy learns: the same run measured 7.3e-6 at
        # iteration 2 and 1.43e-4 at iteration 2000. That is why it survived
        # every short run and only appeared after four hours -- see ADR-094.
        #
        # This costs microseconds on 32 samples and nothing at all during
        # training, which is left at the default precision deliberately.
        with jax.default_matmul_precision("highest"):
            witness_actions = np.asarray(
                jax.vmap(witness_action)(jnp.asarray(witness_obs))
            )

        return {
            "parameters": flat_parameters(np, stored),
            "layers": [[int(a), int(b)] for a, b in shapes],
            # The exploration width these weights were rolled out at, which
            # is a *trained* parameter and until ADR-103 reached no file at
            # all. The engine plays the mean action and the trainer plays a
            # sample drawn about it, so without this number nobody could ask
            # whether those are the same policy -- see docs/MUJOCO.md 6
            # candidate (b). Recorded per action and in the pre-activation
            # space the noise is actually added in.
            "log_std": [float(v) for v in
                        np.asarray(params["log_std"], dtype=np.float32)],
            "normaliser": {
                "mean": [float(v) for v in stored_mean],
                "std": [float(v) for v in stored_std],
            },
            "output_scale": output_scale,
            "output_bias": output_bias,
            "witness_observations": [
                [float(v) for v in row] for row in witness_obs
            ],
            "witness_actions": [
                [float(v) for v in row] for row in witness_actions
            ],
            "reward_curve": list(curve),
            "iterations": len(curve),
            "wall_time_s": float(wall),
            # What this run started from, as a digest rather than a path.
            # `policy_header` folds every option into `hyperparameters`, so
            # left alone `--init-from` would stamp one machine's filesystem
            # layout into every policy the run writes -- which is not
            # provenance, because it does not identify the bytes and does not
            # survive being copied to another box. The digest does both.
            "init_from": init_from_provenance,
            "backend": jax.default_backend(),
            "devices": [str(device) for device in jax.devices()],
            "versions": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "mujoco": str(getattr(mujoco, "__version__", "unknown")),
                "mjx": str(getattr(mjx, "__version__",
                                    getattr(mujoco, "__version__", "unknown"))),
                "jax": jax.__version__,
            },
        }

    curve = []
    step = jnp.int32(0)
    started = time.perf_counter()
    total_iterations = int(options.iterations)
    every = max(0, int(getattr(options, "checkpoint_every", 0) or 0))
    # The best parameters are retained every iteration and *written* only at
    # a checkpoint. Retaining is a pytree copy of a 64x64 MLP and costs
    # nothing; writing runs a witness pass. mg-legs peaked at iteration 1200
    # of 2000 and came home with the iteration-2000 policy, so this alone
    # would have saved thirty of that run's seventy-six minutes.
    best = {"reward_per_step": -math.inf, "iteration": -1,
            "params": None, "mean": None, "variance": None, "written": -1}
    for iteration in range(total_iterations):
        (params, moment1, moment2, state, mean, variance, seen, key, step,
         average, last_loss, mean_steps) = iterate(
            params, moment1, moment2, state, mean, variance, seen, key, step)
        entry = {"iteration": iteration,
                 "reward_per_step": float(average),
                 "loss": float(last_loss),
                 # The row ADR-101 added, and the one to watch: a policy
                 # getting worse while the reward climbs shows up here first,
                 # as an episode length that falls. M9b's fell 170 -> 30 over
                 # 400 iterations with nothing recording it.
                 "episode_steps": float(mean_steps),
                 # The row ADR-103 added, for the same reason. The loss is
                 # `... - entropy_weight * entropy` with `entropy` linear in
                 # `log_std`, so minimising it pushes this number UP with
                 # nothing bounding it. A run whose sigma has walked away
                 # from --initial-std is a run sampling in a space its mean
                 # action never visits, and reading that live is cheaper
                 # than reading it off a finished checkpoint.
                 "action_std": float(jnp.mean(jnp.exp(params["log_std"])))}
        curve.append(entry)
        if not options.quiet:
            print(
                f"iteration {iteration:4d}  reward/step {entry['reward_per_step']:+.6g}"
                f"  loss {entry['loss']:+.6g}"
                f"  episode {entry['episode_steps']:.1f}"
                f"  sigma {entry['action_std']:.4f}",
                file=sys.stderr,
            )
        # Stop at the first non-finite number, naming the iteration and which
        # one went. Observed: a run whose reward/step was +nan from iteration
        # 0 trained on for 150 more iterations and then died in json.dumps --
        # an encoder traceback about a float, an hour after the information
        # that would have explained it. Diverged parameters do not recover,
        # so every iteration after the first nan is spent producing a policy
        # that cannot be written. ``encode_policy``'s ``allow_nan=False``
        # stays where it is: this is the diagnosis, that is the last line of
        # defence, and neither replaces the other.
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
                "raw millimetre or degree channels, which arrive in the "
                "hundreds against a normaliser that starts at mean 0 and "
                "variance 1 -- see docs/MUJOCO.md on reward conditioning."
            )

        elapsed_wall = time.perf_counter() - started
        if entry["reward_per_step"] > best["reward_per_step"]:
            best.update(
                reward_per_step=entry["reward_per_step"],
                iteration=iteration,
                params=params,
                mean=mean,
                variance=variance,
            )
        due = every and (iteration + 1) % every == 0
        if due and iteration + 1 < total_iterations:
            emit(f"{iteration + 1:06d}", iteration, entry["reward_per_step"],
                 snapshot(params, mean, variance, curve, elapsed_wall))
            if best["written"] != best["iteration"]:
                emit("best", best["iteration"], best["reward_per_step"],
                     snapshot(best["params"], best["mean"], best["variance"],
                              curve, elapsed_wall))
                best["written"] = best["iteration"]
        # Rewritten every iteration whether or not anything was checkpointed.
        # This file is the one artifact everything downstream reads -- the
        # `watch` subcommand, the shell's Training panel -- and a run you can
        # only see the state of once every hundred iterations is a run you
        # still cannot decide about.
        progress(
            state="training",
            iteration=iteration,
            total=total_iterations,
            curve=curve,
            best=best,
            wall=elapsed_wall,
            device=jax.default_backend(),
        )

    wall = time.perf_counter() - started
    # One last write of the best-so-far, if the run improved after the final
    # checkpoint boundary. Without it a 2000-iteration run with
    # --checkpoint-every 100 whose best landed at 1950 would come home with
    # a `.best` file from iteration 1900.
    if best["params"] is not None and best["written"] != best["iteration"]:
        emit("best", best["iteration"], best["reward_per_step"],
             snapshot(best["params"], best["mean"], best["variance"],
                      curve, wall))
    return snapshot(params, mean, variance, curve, wall)


# ---------------------------------------------------------------------------
# The program.
# ---------------------------------------------------------------------------


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
                result = [math.tanh(value) for value in result]
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
    return {
        "schema": POLICY_SCHEMA,
        "label": str(options.label or task.get("label") or ""),
        "task": {"sha256": bundle["task_sha256"],
                 "label": str(task.get("label") or "")},
        "model": {"sha256": bundle["model_sha256"], "path": bundle["model_path"]},
        "observations": channels(task),
        "actions": list(task["actions"]),
        "network": {
            "kind": "mlp",
            "layers": trained["layers"],
            "activation": "tanh",
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
        "exploration": {
            "distribution": "gaussian",
            "log_std": [float(v) for v in trained["log_std"]],
            "space": "pre_activation",
        },
        "training": {
            "trainer_sha256": hashlib.sha256(
                Path(__file__).resolve().read_bytes()
            ).hexdigest(),
            "seed": int(options.seed),
            # ADR-138. Written as its own key as well as appearing in
            # ``hyperparameters`` below, because this is the one an
            # *evaluator* reads: a policy trained with a filter has to be
            # PLAYED with it, and a driver that had to be told separately is
            # a driver somebody will forget to tell.
            "action_filter_alpha": float(options.action_filter_alpha),
            # ``init_from`` is excluded for the same reason ``bundle`` and
            # ``out`` are: it is a path on one machine, not a hyperparameter.
            # What it started from is recorded as a digest under
            # ``init_from`` below, which identifies the bytes and survives
            # being copied somewhere else.
            "hyperparameters": {
                key: value
                for key, value in sorted(vars(options).items())
                if key not in ("bundle", "out", "quiet", "label", "init_from")
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
            "cadex_importable": cadex_importable,
        },
        "evaluation": {
            "observations": trained["witness_observations"],
            "actions": trained["witness_actions"],
        },
    }


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
    parser.add_argument("--out", required=True, help="path to write the .cxpolicy")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--envs", type=int, default=256)
    parser.add_argument("--unroll", type=int, default=20)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--hidden", type=int, nargs="+", default=[64, 64])
    parser.add_argument("--learning-rate", type=float, default=3.0e-4)
    parser.add_argument("--discount", type=float, default=0.97)
    parser.add_argument("--gae-lambda", type=float, default=0.95)
    parser.add_argument("--clip", type=float, default=0.2)
    parser.add_argument("--entropy", type=float, default=1.0e-3)
    parser.add_argument("--value-weight", type=float, default=0.5)
    parser.add_argument("--initial-std", type=float, default=0.3)
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
        "--init-from",
        default="",
        metavar="POLICY",
        help=(
            "warm-start the actor from an existing .cxpolicy instead of a "
            "fresh network. The policy must match this bundle's task and "
            "model digests, its observation channels in order, its action "
            "table and the network shape --hidden asks for. Only the actor "
            "and the observation normaliser are carried: the critic and the "
            "optimiser start fresh, because the container holds neither."
        ),
    )
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
            "the shell's Training panel read"
        ),
    )
    return parser.parse_args(list(argv))


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

    def report(**fields: Any) -> None:
        """``progress.json``, rewritten atomically.

        The one artifact everything downstream reads: `remote_train.sh
        watch` polls it over rsync, and the shell's Training panel polls the
        copy that lands next to the project. Neither of them parses this
        program's stderr, and that is deliberate -- ADR-093's finding was
        that a receipt taken from a stream is a receipt something else can
        write into.
        """

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
            "device": str(fields.get("device", "")),
            "reward_per_step": (
                float(curve[-1]["reward_per_step"]) if curve else None
            ),
            "loss": float(curve[-1]["loss"]) if curve else None,
            # Additive under the same schema: `cadex_training.py` reads with
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
            "best_reward_per_step": (
                None if not best or best.get("iteration", -1) < 0
                else float(best["reward_per_step"])
            ),
            "best_iteration": int(best.get("iteration", -1)) if best else -1,
            "out": target.name,
            "label": str(options.label or ""),
            "checkpoints": list(written),
            "error": str(fields.get("error", "")),
        }
        write_atomically(
            progress_path,
            json.dumps(payload, sort_keys=True, indent=2).encode("utf-8"),
        )

    report(state="starting", iteration=-1, total=int(options.iterations),
           curve=[], best={}, wall=0.0, device="")
    try:
        trained = train(bundle, options, emit=emit, progress=report)
    except BaseException as error:
        # A run that died has to say so in the file, or a `watch` loop and a
        # panel both sit on "training" for ever. The exception is re-raised
        # unchanged: this adds a line to an artifact, it does not handle
        # anything.
        report(state="failed", iteration=-1, total=int(options.iterations),
               curve=[], best={}, wall=time.time() - started_at, device="",
               error=f"{type(error).__name__}: {error}")
        raise

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
