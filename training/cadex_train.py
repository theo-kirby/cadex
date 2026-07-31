#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later

"""One task bundle in, one ``.cxpolicy`` out, on a machine that has a GPU.

**This program is not part of the engine and is never installed into the
payload.** It lives at the repository root because it is a thing you *copy*
to another machine: ``pixi`` never sees it, CMake never installs it, and its
dependencies are pinned in ``training/requirements.txt`` and installed into
a venv on whatever box does the training. ``CARRIED_PYPI_PACKAGES`` stays
one entry long, which is what ADR-061 named that constant for.

The sibling of ``src/Mod/cadex/cadex_tests/dynamics_task_episode.py``, and
held to the same discipline: it imports only ``jax``, ``mujoco``,
``mujoco.mjx``, ``numpy`` and the standard library, and it reports whether
``CadexDynamics`` was importable so a test can assert the negative. Run
under ``python -P`` with a scrubbed ``PYTHONPATH`` that is ``false``; if it
ever comes back ``true`` the process was not stock and the run proves
nothing about what a trainer can do with the bundle alone.

**Why training is offboard.** MJX needs JAX-on-GPU, ``jax-metal`` is 0.1.0,
and the published reference for a humanoid gait is 4096 parallel
environments on an RTX 4090. ADR-060 recorded that as a design constraint
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

#: Mirrors ``CadexDynamics.MAXIMUM_POLICY_BYTES``. Checked here so a run that
#: would produce a file the engine refuses fails at the end of training
#: rather than at the end of the trip home.
MAXIMUM_POLICY_BYTES = 4 * 1024 * 1024

#: Mirrors ``CadexDynamics.MINIMUM_POLICY_WITNESS_SAMPLES`` /
#: ``MAXIMUM_POLICY_WITNESS_SAMPLES``.
WITNESS_SAMPLES = 32


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


def train(bundle: dict[str, Any], options: argparse.Namespace) -> dict[str, Any]:
    """Proximal policy optimisation over an MJX batch built from the bundle.

    Deliberately small and readable rather than a harness: everything it
    needs -- the observation slices, the action indices, the units, the
    reward, the termination rules, the episode schedule -- is in the bundle,
    and the point of M7 is that nothing else has to be.
    """

    import jax
    import jax.numpy as jnp
    import numpy as np
    import mujoco
    import mujoco.mjx as mjx

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

    def reset(data):
        data = data.replace(qpos=reset_qpos, qvel=reset_qvel,
                            ctrl=jnp.zeros_like(data.ctrl),
                            time=jnp.float32(0.0))
        return mjx.forward(model, data) if model_axes is None else data

    def step_env(m, data, surface):
        """One control step: clamp, scale into ctrl, integrate, observe, score.

        **The only unit arithmetic on this boundary is the bundle's own
        ``clamp then x scale``**, which is the same two operations
        ``CadexDynamics.evaluate_episode`` performs. M7 adds no conversion
        site, here or anywhere, and ``test_dynamics_units`` greps this file
        to keep that true.
        """

        clamped = jnp.clip(surface, low, high)
        ctrl = data.ctrl.at[ctrl_index].set(clamped * ctrl_scale)
        data = data.replace(ctrl=ctrl)

        def one(d, _):
            return mjx.step(m, d), None

        data, _ = jax.lax.scan(one, data, None, length=per_action)
        vector = observe(data)
        return data, vector, reward_of(vector), done_of(vector)

    batched_step = (
        jax.vmap(step_env, in_axes=(None, 0, 0)) if model_axes is None
        else jax.vmap(step_env, in_axes=(model_axes, 0, 0))
    )
    batched_forward = (
        jax.vmap(mjx.forward, in_axes=(None, 0)) if model_axes is None
        else jax.vmap(mjx.forward, in_axes=(model_axes, 0))
    )

    make = jax.vmap(lambda _: mjx.make_data(put[0]))(jnp.arange(envs))
    data = batched_forward(model, make.replace(
        qpos=jnp.tile(reset_qpos, (envs, 1)),
        qvel=jnp.tile(reset_qvel, (envs, 1)),
    ))

    shapes = layer_shapes(len(names), len(actions), options.hidden)
    critic_shapes = layer_shapes(len(names), 1, options.hidden)
    key = jax.random.PRNGKey(int(options.seed))
    key, actor_key, critic_key = jax.random.split(key, 3)
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

    def rollout(params, data, mean, variance, key):
        """``unroll`` control steps of every environment, with resets."""

        def one(carry, _):
            data, key = carry
            key, subkey = jax.random.split(key)
            vector = jax.vmap(observe)(data)
            normalised = normalise(vector, mean, variance)
            raw = net(params["actor"], normalised)
            noise = jax.random.normal(subkey, raw.shape, dtype=jnp.float32)
            sampled = raw + noise * jnp.exp(params["log_std"])
            logp = gaussian_logp(sampled, raw, params["log_std"])
            surface = surface_of(sampled)
            value = net(params["critic"], normalised)[:, 0]
            data, landed, reward, done = batched_step(model, data, surface)
            data = jax.tree.map(
                lambda new, start: jnp.where(
                    done.reshape((-1,) + (1,) * (new.ndim - 1)), start, new),
                data,
                data.replace(qpos=jnp.tile(reset_qpos, (envs, 1)),
                             qvel=jnp.tile(reset_qvel, (envs, 1))),
            )
            return (data, key), (vector, sampled, logp, value, reward, done, landed)

        (data, key), traces = jax.lax.scan(one, (data, key), None, length=unroll)
        vector = jax.vmap(observe)(data)
        bootstrap = net(params["critic"], normalise(vector, mean, variance))[:, 0]
        return data, key, traces, bootstrap

    discount = float(options.discount)
    lam = float(options.gae_lambda)

    def advantages(rewards, values, dones, bootstrap):
        def one(carry, row):
            reward, value, done, following = row
            delta = reward + discount * following * (1.0 - done) - value
            carry = delta + discount * lam * (1.0 - done) * carry
            return carry, carry

        following = jnp.concatenate([values[1:], bootstrap[None]], axis=0)
        _, out = jax.lax.scan(
            one, jnp.zeros((envs,), dtype=jnp.float32),
            (rewards, values, dones.astype(jnp.float32), following),
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
    def iterate(params, moment1, moment2, data, mean, variance, seen, key, step):
        data, key, traces, bootstrap = rollout(params, data, mean, variance, key)
        vectors, sampled, logp, values, rewards, dones, landed = traces

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

        advantage = advantages(rewards, values, dones, bootstrap)
        target = advantage + values

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
        return (params, moment1, moment2, data, new_mean, new_variance, total,
                key, step, rewards.mean(), losses[-1])

    curve = []
    step = jnp.int32(0)
    started = time.perf_counter()
    for iteration in range(int(options.iterations)):
        (params, moment1, moment2, data, mean, variance, seen, key, step,
         average, last_loss) = iterate(
            params, moment1, moment2, data, mean, variance, seen, key, step)
        entry = {"iteration": iteration,
                 "reward_per_step": float(average),
                 "loss": float(last_loss)}
        curve.append(entry)
        if not options.quiet:
            print(
                f"iteration {iteration:4d}  reward/step {entry['reward_per_step']:+.6g}"
                f"  loss {entry['loss']:+.6g}",
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
    wall = time.perf_counter() - started

    # ---------------------------------------------------------------------
    # The witness: observations the policy actually saw, and the actions this
    # trainer's own JAX network produced for them.
    # ---------------------------------------------------------------------

    data, key, traces, _ = rollout(params, data, mean, variance, key)
    seen_vectors = np.asarray(traces[6]).reshape((-1, len(names)))
    if seen_vectors.shape[0] >= WITNESS_SAMPLES:
        picks = np.linspace(0, seen_vectors.shape[0] - 1, WITNESS_SAMPLES).astype(int)
    else:
        picks = np.arange(seen_vectors.shape[0])
    witness_obs = seen_vectors[picks].astype(np.float32)

    # The weights are rounded to float32 *before* the witness is computed,
    # because float32 is what the container stores and what the engine reads
    # back. A witness taken against unrounded weights would be a witness
    # about numbers that never land.
    stored = [
        (np.asarray(w, dtype=np.float32), np.asarray(b, dtype=np.float32))
        for w, b in params["actor"]
    ]
    stored_jax = [(jnp.asarray(w), jnp.asarray(b)) for w, b in stored]
    stored_mean = np.asarray(mean, dtype=np.float32)
    stored_std = np.sqrt(np.maximum(np.asarray(variance, dtype=np.float32), 1.0e-8)
                          ).astype(np.float32)
    stored_std = np.where(stored_std == 0.0, np.float32(1.0), stored_std)

    def witness_action(vector):
        normalised = (jnp.asarray(vector) - jnp.asarray(stored_mean)) / jnp.asarray(stored_std)
        raw = forward(jnp, stored_jax, normalised)
        return jnp.tanh(raw) * jnp.asarray(output_scale) + jnp.asarray(output_bias)

    witness_actions = np.asarray(
        jax.vmap(witness_action)(jnp.asarray(witness_obs))
    )

    return {
        "parameters": flat_parameters(np, stored),
        "layers": [[int(a), int(b)] for a, b in shapes],
        "normaliser": {
            "mean": [float(v) for v in stored_mean],
            "std": [float(v) for v in stored_std],
        },
        "output_scale": output_scale,
        "output_bias": output_bias,
        "witness_observations": [[float(v) for v in row] for row in witness_obs],
        "witness_actions": [[float(v) for v in row] for row in witness_actions],
        "reward_curve": curve,
        "wall_time_s": wall,
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


# ---------------------------------------------------------------------------
# The program.
# ---------------------------------------------------------------------------


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
    parser.add_argument("--label", default="")
    parser.add_argument("--quiet", action="store_true")
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
    trained = train(bundle, options)

    task = bundle["task"]
    header = {
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
        "training": {
            "trainer_sha256": hashlib.sha256(
                Path(__file__).resolve().read_bytes()
            ).hexdigest(),
            "seed": int(options.seed),
            "hyperparameters": {
                key: value
                for key, value in sorted(vars(options).items())
                if key not in ("bundle", "out", "quiet", "label")
            },
            "iterations": int(options.iterations),
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
            "cadex_importable": cadex_importable,
        },
        "evaluation": {
            "observations": trained["witness_observations"],
            "actions": trained["witness_actions"],
        },
    }

    blob = encode_policy(header, trained["parameters"])
    if len(blob) > MAXIMUM_POLICY_BYTES:
        raise SystemExit(
            f"the policy is {len(blob)} bytes; the engine accepts at most "
            f"{MAXIMUM_POLICY_BYTES}. Train a smaller network."
        )
    target = Path(options.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(blob)

    print(json.dumps({
        "out": str(target),
        "bytes": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
        "parameters": len(trained["parameters"]),
        "task_sha256": bundle["task_sha256"],
        "model_sha256": bundle["model_sha256"],
        "witness_samples": len(trained["witness_observations"]),
        "reward_per_step": (trained["reward_curve"][-1]["reward_per_step"]
                            if trained["reward_curve"] else None),
        "wall_time_s": trained["wall_time_s"],
        "device": trained["backend"],
        "cadex_importable": cadex_importable,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
