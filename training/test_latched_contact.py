# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-978: ``--latched-contact``, a contact flag latched over the control interval.

Run: ``CUDA_VISIBLE_DEVICES= python -m pytest training/test_latched_contact.py`` from the repo.
"""

from __future__ import annotations

import numpy as np
import pytest

import cadex_train as T

#: A bouncy ball on a free joint with a touch sensor, and an idle hinge to drive.
BALL = """
<mujoco><option timestep="0.002"/><worldbody>
  <geom name="environment/floor" type="plane" size="0 0 0.1" solref="-20000 -1"/>
  <body name="ball" pos="0 0 0.1"><freejoint/>
    <geom name="paw" type="sphere" size="0.02" mass="0.1" solref="-20000 -1"/>
    <site name="obs/paw/contact" size="0.021" type="sphere"/>
    <body name="arm"><joint name="j" type="hinge" axis="0 1 0" range="-60 60" limited="true"/>
      <geom name="link" type="capsule" fromto="0 0 0 0 0 0.03" size="0.003" mass="0.001"
            contype="0" conaffinity="0"/></body>
  </body></worldbody>
<actuator><position name="j/position" joint="j" kp="0.01" forcelimited="true" forcerange="-0.01 0.01"/></actuator>
<sensor><touch site="obs/paw/contact" name="obs/paw"/></sensor>
<keyframe><key name="home" qpos="0 0 0.1 1 0 0 0 0"/></keyframe></mujoco>"""


def ball_task() -> dict:
    return {
        "episode": {"control_interval_s": 0.02, "solver_steps_per_action": 10, "max_steps": 500,
                    "reset_keyframe": "home"},
        "observations": [{"adr": 0, "dim": 1, "channels": ["paw", "paw_down"], "scale": 1.0,
                          "kind": "contact", "name": "paw",
                          "contact": {"body": "ball", "down_above_n": 0.0}}],
        "actions": [{"actuator": "j/position", "joint": "j", "index": 0, "low": -30.0, "high": 30.0,
                     "scale": np.pi / 180.0, "kind": "position", "motion_type": "angular", "unit": "deg"}],
        "goal": [],
        "reward": [{"label": "touch", "weight": -1.0, "expression": "paw_down"},
                   {"label": "plain", "weight": -10.0, "expression": "paw_down"},
                   {"label": "force", "weight": 0.0, "expression": "paw"}],
        "termination": [],
        "randomisation": [],
    }


def options(*extra: str):
    return T.arguments(["bundle.json", "--out", "x.cxpolicy", *extra])


def test_off_by_default_and_named_terms_only() -> None:
    task = ball_task()
    names = T.channels(task)
    assert options().latched_contact is None
    assert T.latched_contact_plan(task, names, None) is None
    plan = T.latched_contact_plan(task, names, options("--latched-contact", "touch").latched_contact)
    assert plan["terms"] == [0]
    assert plan["contacts"] == [{"adr": 0, "scale": 1.0, "above": 0.0, "down": 1, "name": "paw_down"}]


def test_a_term_it_cannot_latch_is_refused() -> None:
    task, names = ball_task(), T.channels(ball_task())
    with pytest.raises(SystemExit, match="no reward term labelled"):
        T.latched_contact_plan(task, names, ["swing"])
    with pytest.raises(SystemExit, match="reads no contact _down flag"):
        T.latched_contact_plan(task, names, ["force"])
    bare = {**task, "observations": []}
    with pytest.raises(SystemExit, match="no contact observation"):
        T.latched_contact_plan(bare, [], ["touch"])


def test_the_latched_vector_sets_only_the_down_channels() -> None:
    import jax.numpy as jnp

    plan = {"contacts": [{"down": 1, "above": 0.0}, {"down": 3, "above": 2.0}]}
    vector = np.array([0.0, 0.0, 5.0, 0.0, 7.0], dtype=np.float32)
    peak = np.array([0.4, 1.5], dtype=np.float32)
    out = T.latched_vector(np, vector, peak, plan)
    assert out.tolist() == [0.0, 1.0, 5.0, 0.0, 7.0]
    assert vector.tolist() == [0.0, 0.0, 5.0, 0.0, 7.0]           # not written in place
    again = T.latched_vector(jnp, jnp.asarray(vector), jnp.asarray(peak), plan)
    assert np.asarray(again).tolist() == out.tolist()
    assert T.latched_vector(np, vector, np.array([-np.inf, 2.5], np.float32), plan).tolist() == \
        [0.0, 0.0, 5.0, 1.0, 7.0]


def _cpu_touches(steps: int) -> list[tuple[bool, bool]]:
    """Per control step: (touched on any solver step, touched on the last one), as mj_step reads."""

    import mujoco

    model = mujoco.MjModel.from_xml_string(BALL)
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    mujoco.mj_forward(model, data)
    out = []
    for _ in range(steps):
        seen = []
        for _ in range(10):
            mujoco.mj_step(model, data)
            seen.append(float(data.sensordata[0]) > 0.0)
        out.append((any(seen), seen[-1]))
    return out


def test_the_named_term_reads_every_solver_step_and_the_rest_the_last() -> None:
    import jax
    import jax.numpy as jnp
    import mujoco
    import mujoco.mjx as mjx

    expected = _cpu_touches(20)
    # The ball bounces: some interval holds a touch its last solver state misses.
    assert any(any_ and not last for any_, last in expected)

    def rewards(*extra):
        opts = options(*extra)
        bundle = {"task": ball_task(), "model_xml": BALL.encode("utf-8")}
        env = T.build_environment(bundle, opts, count=1, seed=0, jax=jax, jnp=jnp, np=np,
                                  mujoco=mujoco, mjx=mjx)
        state = env.reset(jax.random.PRNGKey(0))
        step = jax.jit(env.step)
        out = []
        for _ in range(20):
            state = step(state, jnp.zeros((1, 1)))
            out.append(float(state.reward[0]))
        return out

    plain = rewards()
    latched = rewards("--latched-contact", "touch")
    for k, (any_, last) in enumerate(expected):
        assert plain[k] == pytest.approx(-11.0 * last), k
        assert latched[k] == pytest.approx(-1.0 * any_ - 10.0 * last), k


def test_the_flag_is_recorded_in_the_header() -> None:
    import inspect

    assert '"latched_contact"' in inspect.getsource(T)
