"""ADR-984: ``--actor-ramp`` warms Adam's moments through the critic warmup and ramps the actor's update.

ADR-740's warmup zeroes the actor's gradient while Adam's shared step count runs on, so the actor's first real
step is m/sqrt(v) = 0.1/sqrt(0.001) ~ 2.7-3.2 times the learning rate (bias correction ~1) and rises to ~5.6
as m warms faster than v. With the ramp the moments see the actor's gradient through the warmup, the actor does
not move, and its first step is the learning rate's size times the ramp.
"""

from __future__ import annotations

import jax
import jax.numpy as jnp
import numpy as np
import optax
from flax import struct

from cadex_train import actor_gated_update, actor_schedule, arguments

LR = 3e-4
WARMUP_STEPS = 1280   # 10 iterations x 4 epochs x 32 minibatches


@struct.dataclass
class Pair:
    policy: dict
    value: dict


def _optimizer():
    return optax.chain(optax.clip_by_global_norm(1.0e6), optax.adam(LR))


def _steps(gate_scale, total, grad=0.01):
    """Run ``total`` steps of a constant gradient; return the policy's per-step moves."""
    optimizer = _optimizer()
    params = Pair(policy={"w": jnp.zeros(3)}, value={"w": jnp.zeros(3)})
    state = optimizer.init(params)
    grads = Pair(policy={"w": jnp.full(3, grad)}, value={"w": jnp.full(3, grad)})
    step = jax.jit(lambda s, p, g, a, b: actor_gated_update(optimizer, g, s, p, a, b))
    moves = []
    for k in range(total):
        gate, scale = gate_scale(k)
        before = float(params.policy["w"][0])
        params, state = step(state, params, grads, jnp.float32(gate), jnp.float32(scale))
        moves.append(abs(float(params.policy["w"][0]) - before))
    return np.asarray(moves)


def test_schedule():
    assert actor_schedule(0, 10, 0) == (0.0, 1.0)
    assert actor_schedule(9, 10, 0) == (0.0, 1.0)
    assert actor_schedule(10, 10, 0) == (1.0, 1.0)
    assert actor_schedule(0, 10, 20) == (1.0, 0.0)
    assert actor_schedule(9, 10, 20) == (1.0, 0.0)
    assert actor_schedule(10, 10, 20) == (1.0, 1.0 / 20.0)
    assert actor_schedule(29, 10, 20) == (1.0, 1.0)
    assert actor_schedule(40, 10, 20) == (1.0, 1.0)
    assert actor_schedule(10, 10, 1) == (1.0, 1.0)
    assert actor_schedule(0, 0, 4) == (1.0, 0.25)


def test_adr740_first_actor_steps_are_oversized():
    """The defect: after a zero-gradient warmup the actor's first steps are 2.7x, then ~5.6x, the rate."""
    moves = _steps(lambda k: (0.0 if k < WARMUP_STEPS else 1.0, 1.0), WARMUP_STEPS + 128)
    assert np.all(moves[:WARMUP_STEPS] == 0.0)
    after = moves[WARMUP_STEPS:] / LR
    assert 2.5 < after[0] < 3.0
    assert after.max() > 5.0
    assert after.sum() > 3.5 * 128


def test_ramp_warms_moments_and_holds_the_actor():
    """With the ramp: no actor move through the warmup; the first actor iteration's steps are the rate's size."""
    moves = _steps(lambda k: (1.0, 0.0 if k < WARMUP_STEPS else 1.0), WARMUP_STEPS + 128)
    assert np.all(moves[:WARMUP_STEPS] == 0.0)
    after = moves[WARMUP_STEPS:] / LR
    assert np.allclose(after, 1.0, atol=0.01)


def test_ramp_scales_the_update_not_the_critic():
    optimizer = _optimizer()
    params = Pair(policy={"w": jnp.zeros(2)}, value={"w": jnp.zeros(2)})
    state = optimizer.init(params)
    grads = Pair(policy={"w": jnp.ones(2)}, value={"w": jnp.ones(2)})
    params, _ = actor_gated_update(optimizer, grads, state, params, 1.0, 0.25)
    assert np.allclose(np.asarray(params.policy["w"]), -0.25 * LR, rtol=1e-4)
    assert np.allclose(np.asarray(params.value["w"]), -LR, rtol=1e-4)


def test_flag_parses():
    assert arguments(["bundle.json", "--out", "p.cxpolicy", "--actor-ramp", "20"]).actor_ramp == 20
    assert arguments(["bundle.json", "--out", "p.cxpolicy"]).actor_ramp == 0
