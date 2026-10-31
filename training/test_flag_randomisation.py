# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-970: ``--randomise-drive-torque`` and ``--randomise-friction``, the run's own draws.

Run: ``CUDA_VISIBLE_DEVICES= python -m pytest training/test_flag_randomisation.py`` from the repo.
"""

from __future__ import annotations

import random

import numpy as np
import pytest

import cadex_train as T
from test_race_terrain_training import WALKER, walker_task

#: The walker with a second, force-unlimited actuator, which no flag may move.
TWO_DRIVES = WALKER.replace(
    '</actuator>',
    '<motor name="j/free" joint="j" gear="1"/></actuator>')

MASS = {"label": "mass", "low": 0.9, "high": 1.1, "mode": "scale",
        "fields": [{"field": "body_mass", "index": 1}]}


def options(*extra: str):
    return T.arguments(["bundle.json", "--out", "x.cxpolicy", *extra])


def drawn(task, *extra, xml=WALKER, count=4, seed=7):
    import mujoco

    return T.randomised_models(mujoco, np, xml.encode(), task, base_seed=seed, count=count,
                               options=options(*extra))


def test_off_by_default_draws_nothing_and_writes_nothing() -> None:
    import mujoco

    opts = options()
    assert opts.randomise_drive_torque is None and opts.randomise_friction is None
    model = mujoco.MjModel.from_xml_string(WALKER)
    assert T.flag_randomisation(model, opts) == []
    assert T.flag_randomisation_header(opts) == {}
    host, fields = drawn(walker_task())
    assert fields == {}
    assert np.array_equal(host.actuator_forcerange, model.actuator_forcerange)


def test_the_bundles_draws_are_unchanged_by_the_flags() -> None:
    _host, plain = drawn(walker_task([MASS]))
    _host, flagged = drawn(walker_task([MASS]), "--randomise-drive-torque", "0.8", "1.0",
                           "--randomise-friction", "0.6", "1.0")
    assert np.array_equal(plain["body_mass"], flagged["body_mass"])
    assert set(flagged) == {"body_mass", "actuator_forcerange", "geom_friction"}


def test_each_environment_scales_every_limited_drive_by_its_own_draw_after_the_bundles() -> None:
    import mujoco

    base = mujoco.MjModel.from_xml_string(TWO_DRIVES)
    host, fields = drawn(walker_task([MASS]), "--randomise-drive-torque", "0.8", "1.0",
                         xml=TWO_DRIVES, count=5)
    ranges = fields["actuator_forcerange"]
    assert ranges.shape == (5, 2, 2)
    for e in range(5):
        rng = random.Random(7 + e)
        rng.uniform(0.9, 1.1)                 # the bundle's mass entry draws first
        factor = rng.uniform(0.8, 1.0)
        assert 0.8 <= factor <= 1.0
        assert ranges[e, 0] == pytest.approx(base.actuator_forcerange[0] * factor)
        assert np.array_equal(ranges[e, 1], base.actuator_forcerange[1])  # not force-limited
    assert len({float(r) for r in ranges[:, 0, 1]}) == 5   # five mechanisms
    assert np.array_equal(host.actuator_forcerange, ranges[0])


def test_friction_scales_every_geoms_sliding_column_only() -> None:
    import mujoco

    base = mujoco.MjModel.from_xml_string(WALKER)
    _host, fields = drawn(walker_task(), "--randomise-drive-torque", "0.8", "1.0",
                          "--randomise-friction", "0.6", "1.0", count=3)
    friction = fields["geom_friction"]
    for e in range(3):
        rng = random.Random(7 + e)
        torque = rng.uniform(0.8, 1.0)
        factor = rng.uniform(0.6, 1.0)
        assert fields["actuator_forcerange"][e, 0, 1] == pytest.approx(2.0 * torque)
        assert friction[e, :, 0] == pytest.approx(base.geom_friction[:, 0] * factor)
        assert np.array_equal(friction[e, :, 1:], base.geom_friction[:, 1:])


@pytest.mark.parametrize("bounds", [("0", "1"), ("1.0", "0.8"), ("-0.5", "1"), ("nan", "1")])
def test_a_bad_range_is_refused(bounds) -> None:
    import mujoco

    model = mujoco.MjModel.from_xml_string(WALKER)
    with pytest.raises(SystemExit, match="randomise-friction"):
        T.flag_randomisation(model, options("--randomise-friction", *bounds))


def test_a_model_without_a_limited_drive_is_refused() -> None:
    import mujoco

    model = mujoco.MjModel.from_xml_string(WALKER.replace(' forcelimited="true" forcerange="-2 2"', ''))
    with pytest.raises(SystemExit, match="no force-limited actuator"):
        T.flag_randomisation(model, options("--randomise-drive-torque", "0.8", "1"))


def test_the_header_names_the_flags_draws() -> None:
    header = T.flag_randomisation_header(options("--randomise-friction", "0.6", "1.0"))
    assert header == {"flag_entries": [
        {"label": "friction", "field": "geom_friction", "low": 0.6, "high": 1.0}]}


def test_the_trainers_step_clamps_each_environment_to_its_drawn_torque() -> None:
    """End to end: a drive asked far past its range gives its drawn limit, under the curve too."""

    import jax
    import jax.numpy as jnp
    import mujoco
    import mujoco.mjx as mjx

    def peak(*extra):
        opts = options("--no-load-speed", "1e6", *extra)  # the curve on, its slope nil
        stiff = WALKER.replace('kp="5"', 'kp="500"')  # any error past 4 mm-rad saturates
        bundle = {"task": walker_task(), "model_xml": stiff.encode("utf-8")}
        env = T.build_environment(bundle, opts, count=2, seed=0, jax=jax, jnp=jnp, np=np,
                                  mujoco=mujoco, mjx=mjx)
        state = env.reset(jax.random.PRNGKey(0))
        state = env.step(state, jnp.ones((2, 1)))  # +30 deg: far past the range at kp 500
        return np.abs(np.asarray(state.pipeline_state.actuator_force[:, 0]))

    nominal = peak()
    assert nominal == pytest.approx([2.0, 2.0], abs=0.05)
    halved = peak("--randomise-drive-torque", "0.5", "0.5")
    assert halved == pytest.approx([1.0, 1.0], abs=0.05)


def test_a_plain_runs_header_is_unchanged_and_a_flagged_one_names_its_flags() -> None:
    from test_distill import header_of

    plain = header_of(options(), None)["training"]
    flagged = header_of(options("--randomise-drive-torque", "0.8", "1.0"), None)["training"]
    assert not any(key.startswith("randomise_") for key in plain["hyperparameters"])
    assert "flag_entries" not in plain["randomisation"]
    assert flagged["hyperparameters"]["randomise_drive_torque"] == [0.8, 1.0]
    assert "randomise_friction" not in flagged["hyperparameters"]
    assert flagged["randomisation"]["flag_entries"] == [
        {"label": "drive_torque", "field": "actuator_forcerange", "low": 0.8, "high": 1.0}]
    del flagged["hyperparameters"]["randomise_drive_torque"]
    del flagged["randomisation"]["flag_entries"]
    assert plain == flagged
