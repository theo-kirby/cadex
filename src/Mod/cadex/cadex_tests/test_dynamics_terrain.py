# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Ground that is not flat: a declared course under a free base (ADR-714).

A script declares bumps, steps and slopes; the engine samples them onto a
heightfield on the world body, in place of the free base's plane, and the
course travels in the exported file and in every task bundle built on it.
The grid is pure and tested without MuJoCo; the rest is stock MuJoCo, no
engine.
"""

from __future__ import annotations

import math

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx

BLOCK = (100.0, 40.0, 20.0)

COURSE = {
    "x_range_mm": [-400.0, 1600.0],
    "y_range_mm": [-400.0, 400.0],
    "cell_mm": 20.0,
    "features": [
        {"kind": "step", "x_mm": 400.0, "height_mm": 80.0},
        {"kind": "slope", "from_x_mm": 800.0, "to_x_mm": 1200.0, "grade_deg": -10.0},
        # Off the centre line, so a swapped row order shows.
        {"kind": "bump", "x_mm": 200.0, "y_mm": 200.0, "radius_mm": 100.0, "height_mm": 40.0},
    ],
}


def _free_block(collision=None):
    """A block resting on z = 0 with an arm hinged over it, nothing grounded.

    The same rig ``test_dynamics_free_base`` stands on its plane: what is
    measured is the ground, not a cantilever falling over.
    """

    return fx.build(
        [
            {
                "name": "block",
                "world": fx.frame((0.0, 0.0, 10.0)),
                "size": BLOCK,
                "collision": {
                    "shapes": [collision or fx.collision_shape("box", size_mm=list(BLOCK))],
                    "mesh": None,
                },
            },
            {"name": "arm", "size": (300.0, 40.0, 20.0)},
        ],
        [
            {
                "name": "hinge",
                "kind": "revolute",
                "parent": "block",
                "child": "arm",
                "parent_frame": fx.frame((0.0, 0.0, 30.0), (1.0, 0.0, 0.0), 90.0),
                "child_frame": fx.frame((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), 90.0),
                "values": [0.0],
            }
        ],
    )


def _refusal(terrain) -> dyn.DynamicsError:
    with pytest.raises(dyn.DynamicsError) as caught:
        dyn.terrain_grid(terrain)
    return caught.value


# ---------------------------------------------------------------------------
# The grid: pure, no MuJoCo.
# ---------------------------------------------------------------------------


def test_features_add_and_the_grid_samples_them_row_by_row_from_minus_y() -> None:
    grid = dyn.terrain_grid(COURSE)
    descriptor = grid["descriptor"]
    assert (descriptor["ncol"], descriptor["nrow"]) == (101, 41)
    assert len(grid["heights_mm"]) == 101 * 41
    features = descriptor["features"]

    def at(x, y):
        column = round((x - COURSE["x_range_mm"][0]) / 20.0)
        row = round((y - COURSE["y_range_mm"][0]) / 20.0)
        return grid["heights_mm"][row * descriptor["ncol"] + column]

    assert at(0.0, 0.0) == 0.0
    assert at(380.0, 0.0) == 0.0
    assert at(400.0, 0.0) == pytest.approx(80.0)
    drop = 400.0 * math.tan(math.radians(10.0))
    assert at(1000.0, 0.0) == pytest.approx(80.0 - 200.0 * math.tan(math.radians(10.0)))
    assert at(1600.0, -400.0) == pytest.approx(80.0 - drop)
    assert at(200.0, 200.0) == pytest.approx(40.0)
    assert at(200.0, -200.0) == 0.0
    assert dyn.terrain_height_mm(features, 200.0, 250.0) == pytest.approx(20.0)
    assert descriptor["lowest_mm"] == 0.0
    assert descriptor["highest_mm"] == pytest.approx(80.0)
    assert descriptor["kind"] == "heightfield"
    assert descriptor["geom"] == dyn.ENVIRONMENT_TERRAIN_GEOM


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"features": [{"kind": "step", "x_mm": -10.0, "height_mm": 30.0}]}, "terrain_moves_start"),
        ({"features": [{"kind": "step", "x_mm": 5000.0, "height_mm": 30.0}]}, "terrain_is_flat"),
        ({"features": [{"kind": "stairs", "x_mm": 100.0}]}, "unknown_terrain_feature"),
        ({"features": [{"kind": "step", "x_mm": 100.0, "height_mm": 30.0, "width_mm": 5}]}, "malformed_terrain"),
        ({"features": [{"kind": "slope", "from_x_mm": 100.0, "to_x_mm": 200.0, "grade_deg": 90.0}]}, "malformed_terrain"),
        ({"features": []}, "malformed_terrain"),
        ({"x_range_mm": [100.0, 1600.0]}, "terrain_excludes_start"),
        ({"x_range_mm": [-400.0, 1610.0]}, "malformed_terrain"),
        ({"cell_mm": 5.0, "x_range_mm": [-4000.0, 4000.0], "y_range_mm": [-1000.0, 1000.0]}, "terrain_too_large"),
    ],
)
def test_a_course_that_cannot_stand_the_design_is_refused_with_its_reason(change, reason) -> None:
    error = _refusal({**COURSE, **change})
    assert error.reason == reason
    assert error.correction


# ---------------------------------------------------------------------------
# The model, the file and the bundle.
# ---------------------------------------------------------------------------

mujoco = pytest.importorskip("mujoco")


def _ground_z_mm(model, x_mm: float, y_mm: float) -> float:
    """Where a ray straight down from 1 m meets the world's own geometry."""

    import numpy as np

    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    hit = np.zeros(1, np.int32)
    distance = mujoco.mj_ray(
        model, data,
        np.array([x_mm / 1000.0, y_mm / 1000.0, 1.0]),
        np.array([0.0, 0.0, -1.0]),
        None, 1, -1, hit,
    )
    assert int(model.geom_bodyid[int(hit[0])]) == 0
    return (1.0 - distance) * 1000.0


def test_the_course_replaces_the_plane_and_stands_where_it_was_declared() -> None:
    components, joints, _ = _free_block()
    built = dyn.build_model(components, joints, terrain=COURSE)
    model = built["model"]
    assert set(built["environment"]) == {"terrain"}
    assert mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, dyn.ENVIRONMENT_FLOOR_GEOM) == -1
    index = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, dyn.ENVIRONMENT_TERRAIN_GEOM)
    assert int(model.geom_type[index]) == int(mujoco.mjtGeom.mjGEOM_HFIELD)
    assert int(model.geom_bodyid[index]) == 0

    features = built["environment"]["terrain"]["features"]
    # Off the block (it sits on the origin), on vertices and between them.
    for x, y in [(300.0, 0.0), (500.0, 100.0), (1000.0, -300.0), (1500.0, 0.0),
                 (200.0, 200.0), (200.0, -200.0), (-300.0, 300.0)]:
        assert _ground_z_mm(model, x, y) == pytest.approx(
            dyn.terrain_height_mm(features, x, y), abs=0.5
        ), (x, y)


def test_a_block_at_the_origin_stays_on_the_course() -> None:
    """Contact, not only geometry: the block neither sinks nor falls through."""

    components, joints, _ = _free_block()
    built = dyn.build_model(components, joints, terrain=COURSE)
    model = built["model"]
    data = mujoco.MjData(model)
    data.qpos[:] = built["qpos_solved"]
    for _ in range(int(1.0 / model.opt.timestep)):
        mujoco.mj_step(model, data)
    block = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "block")
    assert data.xpos[block][2] * 1000.0 == pytest.approx(10.0, abs=1.5)


def test_terrain_on_a_grounded_model_is_refused() -> None:
    components, joints, _ = fx.two_link_arm(limits=True)
    with pytest.raises(dyn.DynamicsError) as caught:
        dyn.build_model(components, joints, terrain=COURSE)
    assert caught.value.reason == "terrain_needs_free_base"


def test_the_exported_file_carries_the_course_and_the_bundle_names_it() -> None:
    components, joints, _ = _free_block()
    motor = {
        "joint": "hinge", "motion_type": "angular", "kind": "motor",
        "control_nmm": "0", "torque_limit_nmm": 800.0,
    }
    built = dyn.build_model(components, joints, actuators=[motor], terrain=COURSE)
    observations = dyn.observation_records(
        [{"kind": "position", "joint": "hinge", "motion_type": "angular", "name": "q"}],
        built["tree"], built["joint_records"], built["actuators"],
    )
    exported = dyn.export_mjcf(built, observations=observations)
    assert b"<hfield" in exported["xml"]
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    features = built["environment"]["terrain"]["features"]
    assert _ground_z_mm(reloaded, 1000.0, -300.0) == pytest.approx(
        dyn.terrain_height_mm(features, 1000.0, -300.0), abs=0.5
    )

    task = {
        "actions": [{"joint": "hinge", "motion_type": "angular", "actuator_kind": "motor"}],
        "reward": [{"label": "hold", "expression": "-q**2", "weight": 1.0}],
        "termination": [],
        "episode_seconds": 1.0,
        "control_hz": 50,
        "randomisation": [],
        "label": "hold",
    }
    bundle = dyn.task_records(built, reloaded, task, observations=observations)
    assert bundle["terrain"] == built["environment"]["terrain"]
    assert "terrain" in dyn.task_semantic_view(bundle)


def test_a_cylinder_foot_on_the_course_is_refused_before_a_trainer_sees_it() -> None:
    """MJX has no heightfield contact for a cylinder; the plane had one."""

    components, joints, _ = _free_block(
        fx.collision_shape("cylinder", radius_mm=20.0, length_mm=20.0)
    )
    built = dyn.build_model(components, joints, terrain=COURSE)
    exported = dyn.export_mjcf(built)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    rows = dyn.mjx_unsupported_collision_pairs(mujoco, reloaded)
    assert [sorted(row["kinds"]) for row in rows] == [["cylinder", "hfield"]]
