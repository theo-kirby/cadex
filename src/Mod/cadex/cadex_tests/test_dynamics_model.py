# SPDX-License-Identifier: LGPL-2.1-or-later

"""The compiled model (docs/MUJOCO.md M2, phase 4).

Structure, flags and units of the ``mjSpec`` build, for the five joint
types that map directly. What the model *does* is phase 5's exit criterion;
this is what it *is*.

Hazard 3 gets the most space here, because it is the one that would quietly
undo the whole slice: MuJoCo's compiler can rewrite an inertia tensor into
invented numbers. With ``balanceinertia`` on, ``[0.001, 0.001, 1.0]``
compiles to ``[0.334, 0.334, 0.334]`` -- a body that still simulates, still
looks plausible, and no longer has anything to do with the part. Asserting
the flag is off is not enough on its own, because a MuJoCo upgrade can
change a default; the model's compiled inertia is compared against the
OCCT numbers it was built from, per body, every time.
"""

from __future__ import annotations

import math

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx

mujoco = pytest.importorskip("mujoco")


def test_a_geomless_model_compiles_and_has_no_collision_geometry() -> None:
    """M2 defers collision to M3, and explicit inertia makes that possible.

    docs/MUJOCO.md M2 said "primitives only", assuming geoms were needed to
    infer mass. They are not -- we have the BREP -- so a body carries no
    geometry at all and contact cannot silently participate in a result
    this slice has not validated.
    """

    built = dyn.build_model(*fx.pendulum()[:2])
    model = built["model"]
    assert model.ngeom == 0
    assert model.nbody == 3  # world, base, arm
    assert model.njnt == 1

    data = mujoco.MjData(model)
    data.qpos[:] = built["qpos_solved"]
    for _step in range(50):
        mujoco.mj_step(model, data)
    assert all(math.isfinite(value) for value in data.qpos)


def test_the_compiler_flags_that_would_invent_inertia_are_off() -> None:
    built = dyn.build_model(*fx.pendulum()[:2])
    compiler = built["spec"].compiler
    assert not compiler.balanceinertia
    assert compiler.boundinertia == 0.0
    assert compiler.boundmass == 0.0
    assert compiler.inertiafromgeom == mujoco.mjtInertiaFromGeom.mjINERTIAFROMGEOM_FALSE
    # Radians. The default is degrees, and it turned a [-1, 1] joint range
    # into [-0.017, 0.017] the first time this was measured.
    assert not compiler.degree


def test_balanceinertia_is_measured_rather_than_merely_forbidden() -> None:
    """What the flag does, so the assertion above reads as a decision."""

    spec = mujoco.MjSpec()
    spec.compiler.inertiafromgeom = mujoco.mjtInertiaFromGeom.mjINERTIAFROMGEOM_FALSE
    spec.compiler.balanceinertia = True
    body = spec.worldbody.add_body(name="thin")
    body.explicitinertial = True
    body.mass = 1.0
    body.fullinertia = [0.001, 0.001, 1.0, 0.0, 0.0, 0.0]
    body.add_freejoint()
    compiled = spec.compile()
    invented = sorted(float(value) for value in compiled.body_inertia[1])
    assert invented == pytest.approx([0.334, 0.334, 0.334], abs=0.001)


def test_exact_inertia_survives_compilation() -> None:
    components, joints, _placements = fx.pendulum()
    built = dyn.build_model(components, joints)
    model = built["model"]
    for component in components:
        body_id = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_BODY, component["name"]
        )
        inertial = component["inertial"]
        assert float(model.body_mass[body_id]) == pytest.approx(
            inertial["mass_kg"], rel=1.0e-15
        )
        assert sorted(float(value) for value in model.body_inertia[body_id]) == (
            pytest.approx(inertial["principal_inertia_kg_m2"], rel=1.0e-12)
        )


def test_a_rewritten_inertia_is_caught_even_if_a_default_changes() -> None:
    """The guard is on the effect, not only on the flag."""

    components, joints, _placements = fx.pendulum()
    components[1]["inertial"] = dict(components[1]["inertial"])
    # Claim a tensor the compiler will reject or rewrite; the point is that
    # the verification path is exercised rather than assumed.
    components[1]["inertial"]["principal_inertia_kg_m2"] = [1.0, 2.0, 3.0]
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(components, joints)
    assert excinfo.value.reason == "compiler_rewrote_inertia"


def test_the_body_frame_is_the_component_frame_with_the_mass_offset_in_ipos() -> None:
    """Hazard 4: a body frame at the centre of mass offsets every part.

    On screen that reads as "the mesh is wrong", long after the physics has
    already been built around the wrong frame.
    """

    offset_inertial = fx.box_inertial(
        200.0, 40.0, 20.0, centre=(100.0, 0.0, 0.0)
    )
    components, joints, placements = fx.pendulum()
    components[1]["inertial"] = offset_inertial
    built = dyn.build_model(components, joints)
    model = built["model"]
    arm = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "arm")
    assert list(model.body_ipos[arm]) == pytest.approx([0.1, 0.0, 0.0], abs=1.0e-15)

    data = mujoco.MjData(model)
    data.qpos[:] = built["qpos_solved"]
    mujoco.mj_forward(model, data)
    # The *body* still sits where FreeCAD solved it; only the mass is offset.
    assert (data.xpos[arm] * 1000.0).tolist() == pytest.approx(
        dyn.matrix_translation_mm(placements["arm"]), abs=1.0e-9
    )


def test_a_grounded_component_is_static_and_a_stray_one_falls() -> None:
    components, joints, _placements = fx.pendulum()
    components.append(
        {
            "name": "dropped",
            "grounded": False,
            "flexible": False,
            "inertial": fx.box_inertial(50.0, 50.0, 50.0),
            "solved_matrix": list(
                dyn.matrix_from_rotation_translation(
                    [1, 0, 0, 0, 1, 0, 0, 0, 1], (500.0, 0.0, 300.0)
                )
            ),
        }
    )
    built = dyn.build_model(components, joints)
    model = built["model"]
    assert model.nq == 1 + 7  # the hinge, plus one free body
    base = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "base")
    assert model.body_dofnum[base] == 0
    dropped = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "dropped")
    assert model.body_dofnum[dropped] == 6

    data = mujoco.MjData(model)
    data.qpos[:] = built["qpos_solved"]
    mujoco.mj_forward(model, data)
    assert (data.xpos[dropped] * 1000.0).tolist() == pytest.approx(
        [500.0, 0.0, 300.0], abs=1.0e-9
    )
    for _step in range(100):
        mujoco.mj_step(model, data)
    # It falls, because nothing holds it and gravity is in m/s².
    assert data.xpos[dropped][2] < 0.3
    assert data.xpos[base][2] == 0.0


@pytest.mark.parametrize(
    ("kind", "values", "expected"),
    [
        ("revolute", [0.4], ["hinge"]),
        ("slider", [0.05], ["slide"]),
        ("cylindrical", [0.03, 0.6], ["slide", "hinge"]),
        ("ball", [0.9238795, 0.0, 0.3826834, 0.0], ["ball"]),
        ("fixed", [], []),
    ],
)
def test_each_direct_joint_reaches_its_mujoco_type(kind, values, expected) -> None:
    components, joints, placements = fx.build(
        [
            {"name": "base", "grounded": True, "size": (200.0, 200.0, 20.0)},
            {"name": "arm", "size": (300.0, 40.0, 20.0)},
        ],
        [
            {
                "name": "j",
                "kind": kind,
                "parent": "base",
                "child": "arm",
                "parent_frame": fx.frame((40.0, -15.0, 60.0), (1.0, 0.0, 0.0), 90.0),
                "child_frame": fx.frame((-120.0, 5.0, 0.0), (0.0, 1.0, 0.0), -35.0),
                "values": values,
            }
        ],
    )
    built = dyn.build_model(components, joints)
    model = built["model"]
    assert [
        record["mujoco_type"] for record in built["joint_records"]
    ] == expected

    data = mujoco.MjData(model)
    data.qpos[:] = built["qpos_solved"]
    mujoco.mj_forward(model, data)
    arm = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "arm")
    assert (data.xpos[arm] * 1000.0).tolist() == pytest.approx(
        dyn.matrix_translation_mm(placements["arm"]), abs=1.0e-6
    )


def test_joint_limits_arrive_in_radians_and_metres() -> None:
    components, joints, _placements = fx.build(
        [
            {"name": "base", "grounded": True},
            {"name": "arm"},
            {"name": "rod"},
        ],
        [
            {
                "name": "hinge",
                "kind": "revolute",
                "parent": "base",
                "child": "arm",
                "parent_frame": fx.frame((0.0, 0.0, 30.0)),
                "child_frame": fx.frame(),
                "values": [0.3],
                "angle_limits_degrees": [-45.0, 90.0],
            },
            {
                "name": "travel",
                "kind": "slider",
                "parent": "base",
                "child": "rod",
                "parent_frame": fx.frame((0.0, 60.0, 0.0)),
                "child_frame": fx.frame(),
                "values": [0.02],
                "length_limits_mm": [-10.0, 250.0],
            },
        ],
    )
    built = dyn.build_model(components, joints)
    model = built["model"]
    hinge = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "hinge")
    travel = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "travel")
    assert bool(model.jnt_limited[hinge])
    assert list(model.jnt_range[hinge]) == pytest.approx(
        [math.radians(-45.0), math.radians(90.0)], rel=1.0e-12
    )
    assert list(model.jnt_range[travel]) == pytest.approx(
        [-0.01, 0.25], rel=1.0e-12
    )
    # And the solved coordinate is inside its own declared limits, which is
    # what proves the sign convention rather than assuming it.
    for record, address in zip(
        built["joint_records"], (hinge, travel), strict=True
    ):
        low, high = model.jnt_range[address]
        value = built["qpos_solved"][model.jnt_qposadr[address]]
        assert low <= value <= high


def test_a_one_sided_limit_is_widened_and_the_substitution_is_recorded() -> None:
    components, joints, _placements = fx.build(
        [{"name": "base", "grounded": True}, {"name": "arm"}],
        [
            {
                "name": "hinge",
                "kind": "revolute",
                "parent": "base",
                "child": "arm",
                "parent_frame": fx.frame(),
                "child_frame": fx.frame(),
                "values": [0.2],
                "angle_limits_degrees": [-30.0, None],
            }
        ],
    )
    built = dyn.build_model(components, joints)
    record = built["joint_records"][0]
    assert record["limits"]["one_sided"] is True
    assert record["limits"]["declared"] == [-30.0, None]
    low, high = record["limits"]["range"]
    assert low == pytest.approx(math.radians(-30.0))
    assert high > 100.0  # a hundred turns away, where nothing reaches it


def test_an_unlimited_joint_stays_unlimited() -> None:
    built = dyn.build_model(*fx.pendulum()[:2])
    model = built["model"]
    assert not any(bool(value) for value in model.jnt_limited)
    assert built["joint_records"][0]["limits"] is None


def test_gravity_and_the_solver_step_are_si() -> None:
    built = dyn.build_model(*fx.pendulum()[:2])
    assert list(built["model"].opt.gravity) == [0.0, 0.0, pytest.approx(-9.81)]
    assert built["model"].opt.timestep == pytest.approx(dyn.DEFAULT_TIME_STEP_S)


def test_bodies_are_added_parents_first() -> None:
    """MuJoCo needs it, and the BFS order is what supplies it."""

    components, joints, _placements = fx.four_bar()
    built = dyn.build_model(components, joints)
    model = built["model"]
    for body_id in range(1, model.nbody):
        assert model.body_parentid[body_id] < body_id


def test_the_same_assembly_builds_the_same_model_twice() -> None:
    components, joints, _placements = fx.four_bar()
    first = dyn.build_model(components, joints)
    second = dyn.build_model(components, joints)
    assert first["qpos_solved"] == second["qpos_solved"]
    assert first["spec"].to_xml() == second["spec"].to_xml()
