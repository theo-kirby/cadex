# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""A course from placed boxes, the form MJX trains on (ADR-716).

ADR-714's heightfield is stable in stock MuJoCo, but MJX's float32
heightfield-convex collider threw a box rig to non-finite under driven
motion. ``form="boxes"`` builds the same steps and slopes from flat blocks
and turned ramps on a plane at the course's lowest point, and a bump as a
block. The boxes are pure and tested without MuJoCo; the geometry against
MuJoCo's own rays; the stability under MJX from the training venv.
"""

from __future__ import annotations

import math

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx
from test_dynamics_terrain import _free_block, _ground_z_mm

TAN10, TAN15 = math.tan(math.radians(10.0)), math.tan(math.radians(15.0))

#: Up a step, up a slope, down a step clear of the slope's end, down a slope
#: to below the start, and a block off the centre line.
BOX_COURSE = {
    "form": "boxes",
    "x_range_mm": [-400.0, 2400.0],
    "y_range_mm": [-400.0, 400.0],
    "features": [
        {"kind": "step", "x_mm": 400.0, "height_mm": 80.0},
        {"kind": "slope", "from_x_mm": 800.0, "to_x_mm": 1200.0, "grade_deg": 10.0},
        {"kind": "step", "x_mm": 1600.0, "height_mm": -80.0},
        {"kind": "slope", "from_x_mm": 1800.0, "to_x_mm": 2100.0, "grade_deg": -15.0},
        {"kind": "bump", "x_mm": 200.0, "y_mm": 200.0, "radius_mm": 100.0, "height_mm": 40.0},
    ],
}
PEAK = 80.0 + 400.0 * TAN10
END = PEAK - 80.0 - 300.0 * TAN15

MOTOR = {"joint": "hinge", "motion_type": "angular", "kind": "motor",
         "control_nmm": "0", "torque_limit_nmm": 800.0}

#: (x, y, the ground there in mm), off every edge.
EXPECTED = [
    (0.0, 0.0, 0.0), (-300.0, 300.0, 0.0), (300.0, 0.0, 0.0),
    (200.0, 200.0, 40.0), (200.0, -200.0, 0.0),
    (600.0, 100.0, 80.0), (1000.0, -300.0, 80.0 + 200.0 * TAN10),
    (1400.0, 0.0, PEAK), (1700.0, 0.0, PEAK - 80.0),
    (1950.0, 50.0, PEAK - 80.0 - 150.0 * TAN15), (2300.0, 0.0, END),
]


def _reading(terrain, x, y):
    return dyn.terrain_box_ground_mm(terrain, x, y)


def test_steps_slopes_and_bumps_become_blocks_and_ramps() -> None:
    grid = dyn.terrain_grid(BOX_COURSE)
    descriptor = grid["descriptor"]
    assert grid["heights_mm"] is None
    assert descriptor["kind"] == "boxes"
    assert "cell_mm" not in descriptor and "nrow" not in descriptor
    assert descriptor["lowest_mm"] == pytest.approx(END)
    assert descriptor["highest_mm"] == pytest.approx(PEAK)
    shapes = [record["shape"] for record in descriptor["boxes"]]
    assert shapes.count("ramp") == 2
    for x, y, ground in EXPECTED:
        assert _reading(descriptor, x, y) == pytest.approx(ground, abs=1e-9), (x, y)
    # Off the extent the plane at the lowest point is the ground.
    assert _reading(descriptor, 3000.0, 0.0) == pytest.approx(END)
    # The heightfield's cosine at its half height is the block's edge.
    assert _reading(descriptor, 249.0, 200.0) == pytest.approx(40.0)
    assert _reading(descriptor, 251.0, 200.0) == 0.0


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"form": "mesh"}, "malformed_terrain"),
        ({"cell_mm": 20.0}, "malformed_terrain"),
        ({"features": [{"kind": "bump", "x_mm": 500.0, "y_mm": 0.0,
                        "radius_mm": 100.0, "height_mm": -30.0}]}, "terrain_dip_needs_heightfield"),
        ({"features": [{"kind": "slope", "from_x_mm": 300.0, "to_x_mm": 600.0, "grade_deg": 10.0},
                       {"kind": "step", "x_mm": 600.0, "height_mm": -40.0}]}, "terrain_step_off_slope"),
        ({"features": [{"kind": "step", "x_mm": 300.0, "height_mm": 40.0},
                       {"kind": "slope", "from_x_mm": 300.0, "to_x_mm": 600.0, "grade_deg": -10.0}]},
         "terrain_step_off_slope"),
        ({"features": [{"kind": "step", "x_mm": -10.0, "height_mm": 30.0}]}, "terrain_moves_start"),
        ({"features": [{"kind": "step", "x_mm": 5000.0, "height_mm": 30.0}]}, "terrain_is_flat"),
    ],
)
def test_a_box_course_it_cannot_build_is_refused_with_its_reason(change, reason) -> None:
    with pytest.raises(dyn.DynamicsError) as caught:
        dyn.terrain_grid({**BOX_COURSE, **change})
    assert caught.value.reason == reason
    assert caught.value.correction


def test_a_step_up_onto_a_slopes_high_end_is_accepted() -> None:
    """Higher ground past a ramp's high end covers its leaning end face."""

    descriptor = dyn.terrain_grid({**BOX_COURSE, "features": [
        {"kind": "slope", "from_x_mm": 300.0, "to_x_mm": 600.0, "grade_deg": 10.0},
        {"kind": "step", "x_mm": 600.0, "height_mm": 40.0}]})["descriptor"]
    assert _reading(descriptor, 700.0, 0.0) == pytest.approx(300.0 * TAN10 + 40.0)


# ---------------------------------------------------------------------------
# The model: stock MuJoCo, no engine.
# ---------------------------------------------------------------------------

mujoco = pytest.importorskip("mujoco")


def test_the_boxes_stand_where_the_reading_says() -> None:
    components, joints, _ = _free_block()
    built = dyn.build_model(components, joints, terrain=BOX_COURSE)
    model = built["model"]
    descriptor = built["environment"]["terrain"]
    plane = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, dyn.ENVIRONMENT_TERRAIN_GEOM)
    assert int(model.geom_type[plane]) == int(mujoco.mjtGeom.mjGEOM_PLANE)
    assert mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, dyn.ENVIRONMENT_FLOOR_GEOM) == -1
    for index in range(len(descriptor["boxes"])):
        geom = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_GEOM, f"{dyn.ENVIRONMENT_TERRAIN_GEOM}/{index}")
        assert int(model.geom_type[geom]) == int(mujoco.mjtGeom.mjGEOM_BOX)
        assert int(model.geom_bodyid[geom]) == 0
    # Off the block at the origin, every 50 mm along three lines, a ray
    # down meets the ground the reading names.
    for y in (-300.0, 120.0, 200.0):
        for step in range(1, 56):
            x = -375.0 + 50.0 * step
            if abs(x) < 100.0 and abs(y) < 100.0:
                continue
            assert _ground_z_mm(model, x, y) == pytest.approx(
                _reading(descriptor, x, y), abs=1e-3), (x, y)
    assert _ground_z_mm(model, 3000.0, 0.0) == pytest.approx(END, abs=1e-3)


def test_a_block_at_the_origin_stays_on_the_box_course() -> None:
    components, joints, _ = _free_block()
    built = dyn.build_model(components, joints, terrain=BOX_COURSE)
    model = built["model"]
    data = mujoco.MjData(model)
    data.qpos[:] = built["qpos_solved"]
    for _ in range(int(1.0 / model.opt.timestep)):
        mujoco.mj_step(model, data)
    block = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "block")
    assert data.xpos[block][2] * 1000.0 == pytest.approx(10.0, abs=1.5)


def test_the_exported_file_and_the_bundle_carry_the_boxes() -> None:
    components, joints, _ = _free_block()
    built = dyn.build_model(components, joints, actuators=[dict(MOTOR)], terrain=BOX_COURSE)
    exported = dyn.export_mjcf(built)
    assert b"<hfield" not in exported["xml"]
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    descriptor = built["environment"]["terrain"]
    assert _ground_z_mm(reloaded, 1000.0, -300.0) == pytest.approx(
        _reading(descriptor, 1000.0, -300.0), abs=1e-3)
    task = {
        "actions": [{"joint": "hinge", "motion_type": "angular", "actuator_kind": "motor"}],
        "reward": [{"label": "still", "expression": "1", "weight": 1.0}],
        "termination": [], "episode_seconds": 0.2, "control_hz": 50,
        "randomisation": [], "label": "still",
    }
    bundle = dyn.task_records(built, reloaded, task, observations=[])
    assert bundle["terrain"]["boxes"] == descriptor["boxes"]


def test_a_cylinder_foot_on_a_box_course_is_refused_as_on_any_box() -> None:
    components, joints, _ = _free_block(
        fx.collision_shape("cylinder", radius_mm=20.0, length_mm=20.0))
    built = dyn.build_model(components, joints, terrain=BOX_COURSE)
    reloaded = mujoco.MjModel.from_xml_string(dyn.export_mjcf(built)["xml"].decode("utf-8"))
    kinds = {tuple(sorted(row["kinds"])) for row in dyn.mjx_unsupported_collision_pairs(mujoco, reloaded)}
    assert kinds == {("box", "cylinder")}


def test_mjx_keeps_a_driven_rig_finite_on_the_box_course() -> None:
    """The measurement ADR-716 rests on, kept: ADR-714's block and arm on
    this course, 32 envs of random +-0.8 N*m torque held 10 solver steps, for
    100 control steps. The same test on ``test_dynamics_terrain.COURSE``'s
    heightfield measured 3 of 32 envs non-finite from control step 10 and
    one thrown 9.9 m (2026-10-16, MJX 3.10.0, CPU); on the boxes all 32 stay
    finite, the highest at 0.18 m."""

    mjx = pytest.importorskip("mujoco.mjx")
    jax = pytest.importorskip("jax")
    jnp = pytest.importorskip("jax.numpy")
    import numpy

    components, joints, _ = _free_block()
    built = dyn.build_model(components, joints, actuators=[dict(MOTOR)], terrain=BOX_COURSE)
    model = mujoco.MjModel.from_xml_string(dyn.export_mjcf(built)["xml"].decode("utf-8"))
    device = mjx.put_model(model)
    envs, steps = 32, 100
    rng = numpy.random.default_rng(0)
    start = numpy.tile(numpy.asarray(built["qpos_solved"], numpy.float32), (envs, 1))
    # Spread the envs over the course's features, each on the ground there.
    xs = numpy.linspace(-300.0, 2300.0, envs)
    start[:, 0] = xs / 1000.0
    start[:, 2] += numpy.array([
        _reading(built["environment"]["terrain"], x, 0.0) + 20.0 for x in xs]) / 1000.0
    torques = rng.uniform(-1.0, 1.0, size=(envs, steps, model.nu)).astype(numpy.float32)
    torques *= float(model.actuator_forcerange[0, 1])

    def episode(qpos, controls):
        data = mjx.make_data(device).replace(qpos=qpos)

        def control(data, value):
            data = data.replace(ctrl=value)
            data = jax.lax.fori_loop(0, 10, lambda _, d: mjx.step(device, d), data)
            return data, data.qpos[2]

        return jax.lax.scan(control, data, controls)

    final, heights = jax.jit(jax.vmap(episode))(jnp.asarray(start), jnp.asarray(torques))
    heights = numpy.asarray(heights)
    assert numpy.isfinite(numpy.asarray(final.qpos)).all()
    assert numpy.isfinite(heights).all()
    assert heights.max() < 0.5
