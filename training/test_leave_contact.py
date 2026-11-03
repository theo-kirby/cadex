# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-979: ``--leave-contact``, a paw's leave of the floor over the control interval.

Run: ``CUDA_VISIBLE_DEVICES= python -m pytest training/test_leave_contact.py`` from the repo.
"""

from __future__ import annotations

import numpy as np
import pytest

import cadex_train as T
from test_latched_contact import BALL, ball_task, options


def leave_task() -> dict:
    task = ball_task()
    task["reward"] = [{"label": "touch", "weight": -1.0, "expression": "paw_down"},
                      {"label": "plain", "weight": -10.0, "expression": "paw_down"},
                      {"label": "leave", "weight": -100.0, "expression": "paw_down"},
                      {"label": "force", "weight": 0.0, "expression": "paw"}]
    return task


def test_off_by_default_and_refusals_name_the_option() -> None:
    task = leave_task()
    names = T.channels(task)
    assert options().leave_contact is None
    plan = T.latched_contact_plan(task, names, options("--leave-contact", "leave").leave_contact,
                                  flag="--leave-contact")
    assert plan["terms"] == [2]
    with pytest.raises(SystemExit, match="--leave-contact: term 'force' reads no contact"):
        T.latched_contact_plan(task, names, ["force"], flag="--leave-contact")


def test_the_leave_step_needs_a_down_state_before_an_off_one() -> None:
    def run(states, start=False):
        seen, left = np.array([start]), np.array([False])
        for f in states:
            seen, left = T.leave_step(np, seen, left, np.array([f]), np.array([0.0]))
        return bool(left[0])

    assert not run([0, 0, 0])            # never down
    assert not run([0, 0, 1, 1])         # lands: no leave
    assert not run([1, 1, 1])            # held
    assert run([1, 0, 0])                # leaves
    assert run([0, 1, 0, 1])             # lands, leaves, lands: the rebound
    assert run([0, 0], start=True)       # down at the interval's start, off in it
    out = T.leave_vector(np, np.zeros(3, np.float32), np.array([True]), {"contacts": [{"down": 1}]})
    assert out.tolist() == [0.0, 1.0, 0.0]


def _cpu_leaves(steps: int) -> list[tuple[bool, bool, bool]]:
    """Per control step: (touched on any solver step, touched on the last, left in it)."""

    import mujoco

    model = mujoco.MjModel.from_xml_string(BALL)
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    mujoco.mj_forward(model, data)
    out = []
    for _ in range(steps):
        seen = float(data.sensordata[0]) > 0.0
        left = False
        any_ = False
        for _ in range(10):
            mujoco.mj_step(model, data)
            down = float(data.sensordata[0]) > 0.0
            left = left or (seen and not down)
            seen = seen or down
            any_ = any_ or down
        out.append((any_, down, left))
    return out


def test_the_leave_term_reads_every_solver_step() -> None:
    import jax
    import jax.numpy as jnp
    import mujoco
    import mujoco.mjx as mjx

    expected = _cpu_leaves(30)
    # The ball bounces: some intervals hold a leave.
    assert any(left for _a, _l, left in expected)

    def rewards(*extra):
        opts = options(*extra)
        bundle = {"task": leave_task(), "model_xml": BALL.encode("utf-8")}
        env = T.build_environment(bundle, opts, count=1, seed=0, jax=jax, jnp=jnp, np=np,
                                  mujoco=mujoco, mjx=mjx)
        state = env.reset(jax.random.PRNGKey(0))
        step = jax.jit(env.step)
        out = []
        for _ in range(30):
            state = step(state, jnp.zeros((1, 1)))
            out.append(float(state.reward[0]))
        return out

    both = rewards("--latched-contact", "touch", "--leave-contact", "leave")
    alone = rewards("--leave-contact", "leave")
    for k, (any_, last, left) in enumerate(expected):
        assert both[k] == pytest.approx(-1.0 * any_ - 10.0 * last - 100.0 * left), k
        assert alone[k] == pytest.approx(-1.0 * last - 10.0 * last - 100.0 * left), k


def test_a_term_cannot_read_both() -> None:
    import jax
    import jax.numpy as jnp
    import mujoco
    import mujoco.mjx as mjx

    bundle = {"task": leave_task(), "model_xml": BALL.encode("utf-8")}
    with pytest.raises(SystemExit, match="both the latched and the leave"):
        T.build_environment(bundle, options("--latched-contact", "leave", "--leave-contact", "leave"),
                            count=1, seed=0, jax=jax, jnp=jnp, np=np, mujoco=mujoco, mjx=mjx)


def test_the_flag_is_recorded_in_the_header() -> None:
    import inspect

    assert '"leave_contact"' in inspect.getsource(T)
