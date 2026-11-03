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


def test_a_corner_keeps_the_whole_range_to_it_then_falls_to_no_load():
    """ADR-985: an RS00 keeps 14 N*m to 16.8 rad/s and passes its datasheet's 5 N*m at 260 rpm."""
    omega = np.array([[0.0], [10.0], [16.8], [260 * 2 * math.pi / 60], [33.0], [-20.0]])
    r = cadex_train.drive_force_range(np, LIMIT, omega, 33.0, 16.8)
    assert r[0, 0].tolist() == [-14.0, 14.0] and r[1, 0].tolist() == [-14.0, 14.0]
    assert math.isclose(r[2, 0, 1], 14.0)
    assert abs(r[3, 0, 1] - 5.0) < 0.05                       # the datasheet's rated point
    assert r[4, 0].tolist() == [-14.0, 0.0]
    assert math.isclose(r[5, 0, 0], -14.0 * (33.0 - 20.0) / (33.0 - 16.8)) and r[5, 0, 1] == 14.0
    # corner 0 is ADR-969's line exactly
    assert np.array_equal(cadex_train.drive_force_range(np, LIMIT, omega, 33.0, 0.0),
                          cadex_train.drive_force_range(np, LIMIT, omega, 33.0))


def test_the_corner_flag_needs_a_no_load_speed_above_it():
    class Options:
        no_load_speed = 33.0
        drive_corner_speed = 0.0

    assert cadex_train.resolved_drive_corner_speed(Options()) == 0.0
    Options.drive_corner_speed = 16.8
    assert cadex_train.resolved_drive_corner_speed(Options()) == 16.8
    for bad_corner, bad_no_load in ((33.0, 33.0), (-1.0, 33.0), (10.0, 0.0)):
        Options.drive_corner_speed, Options.no_load_speed = bad_corner, bad_no_load
        try:
            cadex_train.resolved_drive_corner_speed(Options())
        except SystemExit:
            continue
        raise AssertionError(f"corner {bad_corner} with no-load {bad_no_load} accepted")


RS00_CHART = "10.47:1,15.71:0.857,23.56:0.571,28.27:0.357,32.99:0.036"


def test_a_chart_curve_reads_the_makers_points_and_keeps_braking():
    """ADR-986: RobStride's RS00 chart: 14 N*m to 100 rpm, 12 at 150, 8 at 225, 5 at 270, none at no-load."""
    class Options:
        no_load_speed = 33.0
        drive_corner_speed = 0.0
        drive_curve = RS00_CHART

    curve = cadex_train.resolved_drive_curve(Options())
    rpm = 2 * math.pi / 60
    omega = np.array([[0.0], [100 * rpm], [150 * rpm], [225 * rpm], [270 * rpm], [33.0], [40.0], [-150 * rpm]])
    r = cadex_train.drive_force_range(np, LIMIT, omega, 33.0, 0.0, curve)
    assert r[0, 0].tolist() == [-14.0, 14.0]
    for row, want in ((1, 14.0), (2, 12.0), (3, 8.0), (4, 5.0)):
        assert abs(r[row, 0, 1] - want) < 0.02, (row, r[row, 0, 1])
        assert r[row, 0, 0] == -14.0                       # braking keeps the whole range
    assert r[5, 0, 1] == 0.0 and r[6, 0, 1] == 0.0
    assert abs(r[7, 0, 0] + 12.0) < 0.02 and r[7, 0, 1] == 14.0
    import jax.numpy as jnp
    jr = np.asarray(cadex_train.drive_force_range(jnp, jnp.asarray(LIMIT), jnp.asarray(omega), 33.0, 0.0, curve))
    assert np.allclose(jr, r, atol=1e-5)
    # no curve is the old shapes exactly
    assert np.array_equal(cadex_train.drive_force_range(np, LIMIT, omega, 33.0, 16.8, None),
                          cadex_train.drive_force_range(np, LIMIT, omega, 33.0, 16.8))


def test_the_curve_flag_refuses_bad_charts():
    class Options:
        no_load_speed = 33.0
        drive_corner_speed = 0.0
        drive_curve = None

    assert cadex_train.resolved_drive_curve(Options()) is None
    for bad, no_load, corner in (("10:1,5:0.5", 33.0, 0.0), ("10:0.5,20:0.8", 33.0, 0.0), ("10:1,40:0.5", 33.0, 0.0),
                                 ("10:1.2", 33.0, 0.0), ("10-1", 33.0, 0.0), ("10:1", 0.0, 0.0), ("10:1", 33.0, 16.8)):
        Options.drive_curve, Options.no_load_speed, Options.drive_corner_speed = bad, no_load, corner
        try:
            cadex_train.resolved_drive_curve(Options())
        except SystemExit:
            continue
        raise AssertionError(f"curve {bad!r} accepted")
