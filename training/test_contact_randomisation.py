# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-971: ``--randomise-contact-timeconst`` and ``--solver-step-divisor``.

Run: ``CUDA_VISIBLE_DEVICES= python -m pytest training/test_contact_randomisation.py`` from the repo.
"""

from __future__ import annotations

import random

import numpy as np
import pytest

import cadex_train as T
from test_race_terrain_training import WALKER, walker_task

MASS = {"label": "mass", "low": 0.9, "high": 1.1, "mode": "scale",
        "fields": [{"field": "body_mass", "index": 1}]}

#: The walker with one more geom whose solref is a (negative) stiffness, which no flag may move.
DIRECT = WALKER.replace(
    '<body name="arm">',
    '<geom name="bumper" type="sphere" size="0.01" pos="0.1 0 0" mass="0.01" '
    'solref="-1000 -10" contype="0" conaffinity="0"/><body name="arm">')


def options(*extra: str):
    return T.arguments(["bundle.json", "--out", "x.cxpolicy", *extra])


def drawn(task, *extra, xml=WALKER, count=4, seed=7):
    import mujoco

    return T.randomised_models(mujoco, np, xml.encode(), task, base_seed=seed, count=count,
                               options=options(*extra))


def test_off_by_default() -> None:
    import mujoco

    opts = options()
    assert opts.randomise_contact_timeconst is None and opts.solver_step_divisor == 1
    assert T.solver_step_divisor(opts) == 1
    assert T.flag_randomisation(mujoco.MjModel.from_xml_string(WALKER), opts) == []
    assert drawn(walker_task())[1] == {}


def test_each_environment_scales_every_time_constant_after_the_other_draws() -> None:
    import mujoco

    base = mujoco.MjModel.from_xml_string(DIRECT)
    bumper = mujoco.mj_name2id(base, mujoco.mjtObj.mjOBJ_GEOM, "bumper")
    _host, fields = drawn(walker_task([MASS]), "--randomise-drive-torque", "0.8", "1.0",
                          "--randomise-friction", "0.6", "1.0",
                          "--randomise-contact-timeconst", "0.5", "1.0",
                          "--solver-step-divisor", "2", xml=DIRECT, count=5)
    solref = fields["geom_solref"]
    assert solref.shape == (5, base.ngeom, 2)
    timed = base.geom_solref[:, 0] > 0
    for e in range(5):
        rng = random.Random(7 + e)
        rng.uniform(0.9, 1.1)        # the bundle's mass
        rng.uniform(0.8, 1.0)        # drive torque
        rng.uniform(0.6, 1.0)        # friction
        factor = rng.uniform(0.5, 1.0)
        assert solref[e, timed, 0] == pytest.approx(base.geom_solref[timed, 0] * factor)
        assert np.array_equal(solref[e, :, 1], base.geom_solref[:, 1])      # damping ratio kept
        assert np.array_equal(solref[e, bumper], base.geom_solref[bumper])  # a stiffness kept
    assert len({float(v) for v in solref[:, 0, 0]}) == 5


def test_the_bundles_and_the_other_flags_draws_are_unchanged() -> None:
    plain = drawn(walker_task([MASS]), "--randomise-friction", "0.6", "1.0")[1]
    flagged = drawn(walker_task([MASS]), "--randomise-friction", "0.6", "1.0",
                    "--randomise-contact-timeconst", "0.5", "1.0", "--solver-step-divisor", "2")[1]
    for field in plain:
        assert np.array_equal(plain[field], flagged[field])


def test_a_time_constant_under_two_solver_steps_is_refused_naming_the_divisor() -> None:
    import mujoco

    model = mujoco.MjModel.from_xml_string(WALKER)   # floor 4 ms, step 2 ms: already at 2 steps
    with pytest.raises(SystemExit, match="--solver-step-divisor 2 or more"):
        T.flag_randomisation(model, options("--randomise-contact-timeconst", "0.5", "1"))
    with pytest.raises(SystemExit, match="--solver-step-divisor 4 or more"):
        T.flag_randomisation(model, options("--randomise-contact-timeconst", "0.25", "1",
                                            "--solver-step-divisor", "2"))
    assert T.flag_randomisation(model, options("--randomise-contact-timeconst", "0.5", "1",
                                               "--solver-step-divisor", "2"))
    with pytest.raises(SystemExit, match="randomise-contact-timeconst"):
        T.flag_randomisation(model, options("--randomise-contact-timeconst", "1", "0.5"))
    with pytest.raises(SystemExit, match="whole number"):
        T.solver_step_divisor(options("--solver-step-divisor", "0"))


def test_mujoco_clamps_a_short_time_constant_without_the_finer_step() -> None:
    """Why the divisor exists: at a 2 ms step, a 2 ms floor sinks a resting box as a 4 ms one
    does (refsafe); at a 1 ms step it holds it four times higher (stiffness ~ 1/tc^2)."""

    import mujoco

    def sink(timeconst: float, step: float) -> float:
        xml = (f'<mujoco><option timestep="{step}"/><worldbody>'
               f'<geom type="plane" size="1 1 .1" solref="{timeconst} 1"/>'
               '<body pos="0 0 .05"><freejoint/><geom type="box" size=".05 .05 .05" mass="5" '
               f'solref="{timeconst} 1"/></body></worldbody></mujoco>')
        model = mujoco.MjModel.from_xml_string(xml)
        data = mujoco.MjData(model)
        while data.time < 1.0:
            mujoco.mj_step(model, data)
        return 0.05 - float(data.qpos[2])

    assert sink(0.002, 0.002) == pytest.approx(sink(0.004, 0.002), rel=1e-3)
    assert sink(0.002, 0.001) == pytest.approx(sink(0.004, 0.001) / 4.0, rel=0.1)


def test_the_divisor_keeps_the_control_interval_and_divides_the_step() -> None:
    """End to end: one action is 20 ms of simulated time at either step."""

    import jax
    import jax.numpy as jnp
    import mujoco
    import mujoco.mjx as mjx

    def elapsed(*extra):
        bundle = {"task": walker_task(), "model_xml": WALKER.encode("utf-8")}
        env = T.build_environment(bundle, options(*extra), count=2, seed=0, jax=jax, jnp=jnp,
                                  np=np, mujoco=mujoco, mjx=mjx)
        state = env.reset(jax.random.PRNGKey(0))
        start = np.asarray(state.pipeline_state.time)
        state = env.step(state, jnp.zeros((2, 1)))
        return np.asarray(state.pipeline_state.time) - start

    assert elapsed() == pytest.approx([0.02, 0.02], abs=1e-6)
    assert elapsed("--solver-step-divisor", "2", "--randomise-contact-timeconst", "0.5", "1.0") \
        == pytest.approx([0.02, 0.02], abs=1e-6)


def test_the_header_names_the_flag_and_divisor_only_when_given() -> None:
    from test_distill import header_of

    plain = header_of(options(), None)["training"]
    flagged = header_of(options("--randomise-contact-timeconst", "0.5", "1.0",
                                "--solver-step-divisor", "2"), None)["training"]
    assert "solver_step_divisor" not in plain["hyperparameters"]
    assert flagged["hyperparameters"]["solver_step_divisor"] == 2
    assert flagged["hyperparameters"]["randomise_contact_timeconst"] == [0.5, 1.0]
    assert flagged["randomisation"]["flag_entries"] == [
        {"label": "contact_timeconst", "field": "geom_solref", "low": 0.5, "high": 1.0}]
    for key in ("solver_step_divisor", "randomise_contact_timeconst"):
        del flagged["hyperparameters"][key]
    del flagged["randomisation"]["flag_entries"]
    assert plain == flagged
