# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A saturated servo is the same machine in the trainer and the engine (ADR-465).

Every Cadex servo is exported as a force-limited ``general`` actuator with an
affine bias ``[0, -kp, -kv]`` -- a PD loop whose torque is clamped at the
servo's stall -- under ``integrator="implicitfast"``. Under that integrator
both engines fold the actuator's velocity derivative, ``-kv``, into the
implicit step. **They disagree about when to stop.** Stock MuJoCo 3.10 drops
the term for an actuator whose force is clamped at its ``forcerange``; MJX
3.10's ``deriv_smooth_vel`` keeps it always. A servo that saturates is
therefore integrated as extra-damped in training and as torque-limited in
the engine, and the difference is not small: ot11's r2 walk policy, from one
reset with no contact at all, disagreed by 6.9 rad/s in one 2 ms substep,
and over a full episode MJX walked it **forwards** at +2.80 reward per step
while the engine walked the same weights **backwards** at -1.95.

``cadex_train.match_engine_actuator_derivative`` applies the engine's rule
inside MJX. These tests pin both halves: that raw MJX still disagrees (so
the day a release fixes it, the first test fails and the shim can go), and
that the trainer, with the rule installed, integrates what the engine does.

No contact anywhere in the fixture, so every disagreement is the smooth
dynamics and nothing else. float64 on both sides, so it is never rounding.

Gated on jax and mujoco.mjx, the trainer's dependencies, which the engine
environment deliberately lacks (ADR-084); the source-level test at the end
runs everywhere.
"""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

import pytest

TRAINER = Path(__file__).resolve().parents[4] / "training" / "cadex_train.py"

#: Two light links on hinges, each driven by the actuator Cadex exports for a
#: 9 g servo (kp, kv and stall torque copied from ot11-quad-1's model), with
#: contact disabled. The first is commanded far past what its stall torque
#: can hold, so it saturates; the second is commanded gently, so it never
#: does -- which is what shows the rule is per actuator.
FIXTURE = """
<mujoco model="forcelimit">
  <compiler angle="radian" autolimits="false"/>
  <option integrator="implicitfast" timestep="0.002">
    <flag contact="disable"/>
  </option>
  <worldbody>
    <body name="hard" pos="0 0 0.5">
      <joint name="j_hard" type="hinge" axis="0 1 0" damping="0.0168564"/>
      <geom type="capsule" fromto="0 0 0 0.05 0 0" size="0.006" mass="0.01"/>
    </body>
    <body name="soft" pos="0 0.2 0.5">
      <joint name="j_soft" type="hinge" axis="0 1 0" damping="0.0168564"/>
      <geom type="capsule" fromto="0 0 0 0.05 0 0" size="0.006" mass="0.01"/>
    </body>
  </worldbody>
  <actuator>
    <general name="hard" joint="j_hard" ctrllimited="false" forcelimited="{limited}"
             forcerange="-0.17652 0.17652" biastype="affine" gainprm="2.02277"
             biasprm="0 -2.02277 -0.101138"/>
    <general name="soft" joint="j_soft" ctrllimited="false" forcelimited="{limited}"
             forcerange="-0.17652 0.17652" biastype="affine" gainprm="2.02277"
             biasprm="0 -2.02277 -0.101138"/>
  </actuator>
</mujoco>
"""

CONTROL_STEPS = 60
SUBSTEPS = 10

#: Raw MJX on the saturating fixture: measured 10.2 rad/s worst ``qvel``
#: disagreement. Asserted at 1e-2 -- three orders below the measurement.
RAW_DISAGREEMENT_FLOOR = 1.0e-2
#: With the engine's rule installed: measured 6.2e-15, float64 round-off.
MATCHED_CEILING = 1.0e-9


def _mjx_or_skip():
    try:
        import jax
        import mujoco  # noqa: F401
        import mujoco.mjx  # noqa: F401
    except Exception:
        pytest.skip(
            "jax and mujoco.mjx are the offboard trainer's dependencies and "
            "are deliberately absent from the engine environment (ADR-084). "
            "Run this file from a venv built from training/requirements.txt."
        )
    jax.config.update("jax_enable_x64", True)
    return jax


def _trainer():
    spec = importlib.util.spec_from_file_location("cadex_train", TRAINER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _worst_disagreement(*, limited: bool, matched: bool) -> float:
    """Worst ``qvel`` difference, per substep, over a free-running episode.

    Free-running rather than re-synced, because without contact nothing here
    is chaotic: two engines computing the same physics stay together.
    """

    jax = _mjx_or_skip()
    import jax.numpy as jnp
    import mujoco
    import mujoco.mjx as mjx
    import numpy as np
    from mujoco.mjx._src import derivative

    original = derivative.deriv_smooth_vel
    # jit caches a trace by function, so an ``mjx.step`` traced by an earlier
    # test would keep whichever derivative it was traced with.
    jax.clear_caches()
    try:
        if matched:
            _trainer().match_engine_actuator_derivative(mujoco, jax, jnp)
        model = mujoco.MjModel.from_xml_string(
            FIXTURE.format(limited="true" if limited else "false"))
        data = mujoco.MjData(model)
        mujoco.mj_forward(model, data)
        put = mjx.put_model(model)
        state = mjx.forward(put, mjx.put_data(model, data))
        step = jax.jit(mjx.step)
        worst = 0.0
        for index in range(CONTROL_STEPS):
            # The hard link is told to swing a full radian either way, which
            # kp alone turns into 2 N m against a 0.18 N m stall: saturated
            # on every step. The soft one is asked for a hundredth of that.
            sign = 1.0 if (index // 10) % 2 == 0 else -1.0
            ctrl = np.array([sign * 1.0, sign * 0.01])
            data.ctrl[:] = ctrl
            state = state.replace(ctrl=jnp.asarray(ctrl))
            for _ in range(SUBSTEPS):
                mujoco.mj_step(model, data)
                state = step(put, state)
                worst = max(worst, float(np.max(np.abs(
                    np.asarray(state.qvel) - data.qvel))))
        return worst
    finally:
        derivative.deriv_smooth_vel = original
        jax.clear_caches()


def test_raw_mjx_integrates_a_saturated_servo_differently_from_the_engine() -> None:
    worst = _worst_disagreement(limited=True, matched=False)
    assert worst > RAW_DISAGREEMENT_FLOOR, (
        f"raw MJX now agrees with stock MuJoCo through a saturated, "
        f"force-limited PD servo (worst qvel difference {worst:.3e}). That is "
        f"good news: MJX has adopted the engine's rule for clamped actuator "
        f"derivatives, so cadex_train.match_engine_actuator_derivative and "
        f"this file can be deleted under ADR-465's removal note."
    )


def test_the_trainer_integrates_a_saturated_servo_as_the_engine_does() -> None:
    worst = _worst_disagreement(limited=True, matched=True)
    assert worst < MATCHED_CEILING, (
        f"with the engine's clamped-derivative rule installed, MJX still "
        f"differs from stock MuJoCo by {worst:.3e} rad/s through a saturated "
        f"servo; the trainer is training a different machine from the one "
        f"the engine evaluates (ADR-465)."
    )


def test_an_unlimited_servo_agrees_with_or_without_the_rule() -> None:
    """The control: with no force limit nothing clamps and nothing differs."""

    assert _worst_disagreement(limited=False, matched=False) < MATCHED_CEILING
    assert _worst_disagreement(limited=False, matched=True) < MATCHED_CEILING


def test_train_installs_the_rule_before_it_builds_a_model() -> None:
    """Runs everywhere: the trainer's own source, read without importing jax."""

    source = inspect.getsource(_trainer().train)
    call = source.find("match_engine_actuator_derivative(")
    assert call >= 0, "train() never installs the engine's actuator derivative rule"
    assert call < source.find("mjx.put_model("), (
        "train() must install the rule before it puts a model on the device"
    )
