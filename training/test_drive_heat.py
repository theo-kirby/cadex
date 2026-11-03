"""ADR-974: a drive is held to its rating by its heat; ADR-975: a foot that stays up costs."""
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cadex_train  # noqa: E402

LIMIT = np.array([[-14.0, 14.0]])
ON = np.array([True])
HEAT = (5.0 / 14.0, 2.0)          # an RS00: 5 N*m of 14 rated, 2 s at peak from cold


def test_the_budget_is_two_seconds_at_peak():
    peak, rated, budget = cadex_train.heat_budget(np, LIMIT, *HEAT)
    assert peak.tolist() == [14.0] and np.allclose(rated, [5.0])
    assert np.allclose(budget, [(196.0 - 25.0) * 2.0])


def test_the_ceiling_falls_from_peak_to_rating():
    _, _, budget = cadex_train.heat_budget(np, LIMIT, *HEAT)
    cold = cadex_train.heat_range(np, LIMIT, LIMIT, np.zeros(1), ON, *HEAT)
    half = cadex_train.heat_range(np, LIMIT, LIMIT, budget / 2, ON, *HEAT)
    full = cadex_train.heat_range(np, LIMIT, LIMIT, budget * 2, ON, *HEAT)
    assert cold.tolist() == [[-14.0, 14.0]]
    assert np.allclose(half, [[-9.5, 9.5]])
    assert np.allclose(full, [[-5.0, 5.0]])
    # the speed curve's lower end holds where it is lower; an actuator off the map keeps its range
    curve = np.array([[-14.0, 3.0]])
    assert np.allclose(cadex_train.heat_range(np, curve, LIMIT, budget, ON, *HEAT), [[-5.0, 3.0]])
    assert cadex_train.heat_range(np, LIMIT, LIMIT, budget, np.array([False]), *HEAT).tolist() == LIMIT.tolist()


def test_heat_rises_over_the_rating_and_falls_under_it():
    _, _, budget = cadex_train.heat_budget(np, LIMIT, *HEAT)
    h = np.zeros(1)
    for _ in range(1000):                             # 2 s at peak, 2 ms steps
        h = cadex_train.heated(np, h, np.array([14.0]), LIMIT, ON, *HEAT, 0.002)
    assert np.allclose(h, budget)
    h = cadex_train.heated(np, h, np.array([30.0]), LIMIT, ON, *HEAT, 0.002)
    assert np.allclose(h, budget)                     # kept at the budget
    h = cadex_train.heated(np, h, np.array([0.0]), LIMIT, ON, *HEAT, 0.002)
    assert np.allclose(h, budget - 25.0 * 0.002)      # cools at rated^2 when idle
    assert cadex_train.heated(np, np.zeros(1), np.array([3.0]), LIMIT, ON, *HEAT, 0.002).tolist() == [0.0]


def test_jax_and_numpy_agree():
    import jax.numpy as jnp

    heat = np.array([0.0, 50.0, 171.0, 400.0])[:, None]
    a = cadex_train.heat_range(np, LIMIT, LIMIT, heat, ON, *HEAT)
    b = np.asarray(cadex_train.heat_range(jnp, jnp.asarray(LIMIT), jnp.asarray(LIMIT),
                                          jnp.asarray(heat), jnp.asarray(ON), *HEAT))
    assert np.allclose(a, b)


def test_a_drive_held_at_peak_folds_back_to_its_rating_in_mujoco():
    import mujoco

    model = mujoco.MjModel.from_xml_string("""
<mujoco><option timestep="0.002" gravity="0 0 0"/>
  <worldbody><body><joint name="j" type="hinge" axis="0 0 1" damping="1e6"/>
    <geom type="cylinder" size="0.05 0.01" mass="1"/></body></worldbody>
  <actuator><general joint="j" forcelimited="true" forcerange="-14 14" gainprm="1"/></actuator>
</mujoco>""")
    data = mujoco.MjData(model)
    data.ctrl[0] = 100.0
    speed_map = cadex_train.actuator_speed_map(model)
    limit = model.actuator_forcerange.copy()
    heat, forces = np.zeros(1), []
    for _ in range(15000):                            # 30 s
        model.actuator_forcerange[:] = cadex_train.heat_range(np, limit, limit, heat, speed_map[2], *HEAT)
        mujoco.mj_step(model, data)
        heat = cadex_train.heated(np, heat, data.actuator_force.copy(), limit, speed_map[2], *HEAT, 0.002)
        forces.append(float(data.actuator_force[0]))
    assert forces[0] == pytest.approx(14.0, rel=1e-3)
    assert forces[1000] < 10.0                        # folding back by 2 s
    assert forces[-1] == pytest.approx(5.0, rel=1e-2)  # held to its rating
    rms = float(np.sqrt(np.mean(np.square(forces[-5000:]))))
    assert rms < 5.1                                  # its last 10 s at its rating


def test_the_flags_are_checked():
    assert cadex_train.resolved_drive_heat(SimpleNamespace(drive_heat=None)) is None
    assert cadex_train.resolved_drive_heat(SimpleNamespace(drive_heat=[0.357, 2.0])) == (0.357, 2.0)
    for bad in ([1.0, 2.0], [0.3, 0.0]):
        with pytest.raises(SystemExit):
            cadex_train.resolved_drive_heat(SimpleNamespace(drive_heat=bad))
    assert cadex_train.resolved_heat_start(SimpleNamespace()) == (0.0, 0.0)
    with pytest.raises(SystemExit):
        cadex_train.resolved_heat_start(SimpleNamespace(heat_start=[0.6, 0.2]))


TASK = {"observations": [
    {"kind": "contact", "channels": ["fl_paw", "fl_paw_down"]},
    {"kind": "joint", "channels": ["q"]},
    {"kind": "contact", "channels": ["hr_paw", "hr_paw_down"]}]}


def test_the_air_limit_joins_a_feet_block_read_from_the_contacts():
    task = cadex_train.with_feet_air_limit(TASK, SimpleNamespace(feet_air_limit=[0.4, -1.0]))
    assert task["feet"] == {"contacts": ["fl_paw_down", "hr_paw_down"],
                            "air_limit": {"limit_s": 0.4, "weight": -1.0}}
    assert "feet" not in TASK
    assert cadex_train.with_feet_air_limit(TASK, SimpleNamespace(feet_air_limit=None)) is TASK
    for bad in ([0.4, 1.0], [0.0, -1.0]):
        with pytest.raises(SystemExit):
            cadex_train.with_feet_air_limit(TASK, SimpleNamespace(feet_air_limit=bad))


def test_a_foot_up_past_the_limit_costs_every_step_and_a_landing_foot_nothing():
    names = ["fl_paw", "fl_paw_down", "q", "hr_paw", "hr_paw_down"]
    task = cadex_train.with_feet_air_limit(TASK, SimpleNamespace(feet_air_limit=[0.1, -2.0]))
    terms = cadex_train.feet_terms(task, names)
    memory = (np.zeros(2), np.zeros(2, bool), np.zeros(2))
    pays = []
    for k in range(10):                               # fl never lands; hr lands every 4th step
        contact = np.array([False, k % 4 == 3])
        pay, memory = cadex_train.feet_step(np, terms, memory, contact, np.zeros(2), np.bool_(True), 0.02)
        pays.append(float(pay))
    # fl is up 0.02 * (k + 1) s; past 0.1 s from k = 5 on; hr is never up past 0.08 s
    expected = [-2.0 * max(0.0, 0.02 * (k + 1) - 0.1) for k in range(10)]
    assert np.allclose(pays, expected)
