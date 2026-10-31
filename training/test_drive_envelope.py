"""ADR-969: a drive's torque falls with its speed, in the trainer and the player alike."""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cadex_train  # noqa: E402

LIMIT = np.array([[-14.0, 14.0]])
HINGE = """
<mujoco><option timestep="0.002"/>
  <worldbody><body><joint name="j" type="hinge" axis="0 0 1"/>
    <geom type="cylinder" size="0.05 0.01" mass="1"/></body></worldbody>
  <actuator>
    <general name="drive" joint="j" forcelimited="true" forcerange="-14 14" biastype="affine"
             gainprm="90" biasprm="0 -90 -1"/>
    <general name="free" joint="j" gainprm="1"/>
  </actuator>
</mujoco>"""


def test_the_range_falls_in_the_turning_direction_and_braking_keeps_it():
    omega = np.array([[0.0], [16.5], [33.0], [50.0], [-16.5]])
    r = cadex_train.drive_force_range(np, LIMIT, omega, 33.0)
    assert r.shape == (5, 1, 2)
    assert r[0, 0].tolist() == [-14.0, 14.0]
    assert r[1, 0].tolist() == [-14.0, 7.0]
    assert r[2, 0].tolist() == [-14.0, 0.0]
    assert r[3, 0].tolist() == [-14.0, 0.0]
    assert r[4, 0].tolist() == [-7.0, 14.0]


def test_jax_and_numpy_agree():
    import jax.numpy as jnp

    omega = np.linspace(-40.0, 40.0, 17)[:, None]
    a = cadex_train.drive_force_range(np, LIMIT, omega, 33.0)
    b = np.asarray(cadex_train.drive_force_range(jnp, jnp.asarray(LIMIT), jnp.asarray(omega), 33.0))
    assert np.allclose(a, b)


def test_only_force_limited_joint_drives_are_enveloped():
    import mujoco

    model = mujoco.MjModel.from_xml_string(HINGE)
    dof, gear, enveloped = cadex_train.actuator_speed_map(model)
    assert dof.tolist() == [0, 0] and gear.tolist() == [1.0, 1.0]
    assert enveloped.tolist() == [True, False]
    limit = model.actuator_forcerange.copy()
    r = cadex_train.enveloped_range(np, limit, np.array([33.0]), (dof, gear, enveloped), 33.0)
    assert r[0].tolist() == [-14.0, 0.0] and r[1].tolist() == limit[1].tolist()


def test_a_drive_at_its_no_load_speed_gives_no_forward_torque():
    import mujoco

    model = mujoco.MjModel.from_xml_string(HINGE)
    data = mujoco.MjData(model)
    data.qvel[0] = 33.0
    data.ctrl[0] = 10.0          # far ahead: the PD asks for its whole range forward
    speed_map = cadex_train.actuator_speed_map(model)
    model.actuator_forcerange[:] = cadex_train.enveloped_range(
        np, model.actuator_forcerange.copy(), data.qvel, speed_map, 33.0)
    mujoco.mj_forward(model, data)
    assert data.actuator_force[0] == 0.0
    data.qvel[0] = 0.0
    model.actuator_forcerange[0] = [-14.0, 14.0]
    mujoco.mj_forward(model, data)
    assert math.isclose(data.actuator_force[0], 14.0)


def test_the_flag_is_off_by_default_and_refuses_a_negative_speed():
    class Options:
        no_load_speed = 0.0

    assert cadex_train.resolved_no_load_speed(Options()) == 0.0
    Options.no_load_speed = -1.0
    try:
        cadex_train.resolved_no_load_speed(Options())
    except SystemExit:
        pass
    else:
        raise AssertionError("a negative no-load speed was accepted")
