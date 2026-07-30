# SPDX-License-Identifier: LGPL-2.1-or-later

"""Gear, belt and screw couplings (docs/MUJOCO.md M2, phase 9).

Four of FreeCAD's thirteen joints constrain motion rather than provide it:
``AssemblyObject::isJointTypeConnecting`` returns false for screw,
rack-and-pinion, gears and belt, so its own solver never uses them to place
a part. They become MuJoCo ``equality/joint`` rows relating two coordinates
other joints already own.

**Every law here was measured against OndselSolver, through the real
kinematics path, rather than derived from documentation.** Hazard 7 is that
a wrong ratio or a wrong sign produces a gear train running backwards --
which looks exactly like a working mechanism. Driving one revolution gave:

* gears, r1=20 r2=10: the second wheel turns **−2x** the first (measured
  −0.6283 rad for +0.3142), so external gears counter-rotate;
* belt, same radii: **+2x** -- which is also what the FreeCAD source
  predicts, since it builds a belt as a gear with ``radiusJ`` negated;
* screw, pitch 4 mm: one full turn moved the nut **−4.000 mm**, settling
  the 2π ambiguity -- ``pitch`` is millimetres per revolution.

``rack_pinion`` is refused, with the reason. Its native constraint acts
along a marker frame OndselSolver derives specially, the measurement run did
not produce a clean ``x = R·θ``, and shipping a guess is exactly what the
hazard warns against.
"""

from __future__ import annotations

import math

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx

mujoco = pytest.importorskip("mujoco")


def _gear_train(kind: str, radius1: float = 20.0, radius2: float = 10.0):
    """A housing and two wheels on parallel revolute joints, meshed."""

    components, joints, placements = fx.build(
        [
            {"name": "housing", "grounded": True, "size": (200.0, 80.0, 10.0)},
            {"name": "pinion", "size": (40.0, 40.0, 10.0)},
            {"name": "wheel", "size": (20.0, 20.0, 10.0)},
        ],
        [
            {
                "name": "axle1",
                "kind": "revolute",
                "parent": "housing",
                "child": "pinion",
                "parent_frame": fx.frame((0.0, 0.0, 20.0)),
                "child_frame": fx.frame(),
                "values": [0.0],
            },
            {
                "name": "axle2",
                "kind": "revolute",
                "parent": "housing",
                "child": "wheel",
                "parent_frame": fx.frame((30.0, 0.0, 20.0)),
                "child_frame": fx.frame(),
                "values": [0.0],
            },
        ],
    )
    joints.append(
        {
            "name": "mesh",
            "kind": kind,
            "suppressed": False,
            "parameters": {"radius1_mm": radius1, "radius2_mm": radius2},
            "length_limits_mm": None,
            "angle_limits_degrees": None,
            "connectors": [
                {"component": "pinion", "local_matrix": fx.frame()},
                {"component": "wheel", "local_matrix": fx.frame()},
            ],
        }
    )
    return components, joints, placements


def _screw_stack(pitch_mm: float = 4.0):
    """A frame, a nut on a slider and a shaft on a revolute, threaded.

    The same shape as the assembly the law was measured on: the coupling's
    two components are placed by *other* joints to a common parent.
    """

    components, joints, placements = fx.build(
        [
            {"name": "frame", "grounded": True, "size": (60.0, 60.0, 10.0)},
            {"name": "nut", "size": (20.0, 20.0, 20.0)},
            {"name": "shaft", "size": (10.0, 10.0, 80.0)},
        ],
        [
            {
                "name": "guide",
                "kind": "slider",
                "parent": "frame",
                "child": "nut",
                "parent_frame": fx.frame((0.0, 0.0, 30.0)),
                "child_frame": fx.frame(),
                "values": [0.0],
            },
            {
                "name": "spin",
                "kind": "revolute",
                "parent": "frame",
                "child": "shaft",
                "parent_frame": fx.frame((0.0, 0.0, 10.0)),
                "child_frame": fx.frame(),
                "values": [0.0],
            },
        ],
    )
    joints.append(
        {
            "name": "thread",
            "kind": "screw",
            "suppressed": False,
            "parameters": {"thread_pitch_mm": pitch_mm},
            "length_limits_mm": None,
            "angle_limits_degrees": None,
            "connectors": [
                {"component": "nut", "local_matrix": fx.frame()},
                {"component": "shaft", "local_matrix": fx.frame()},
            ],
        }
    )
    return components, joints, placements


def _settle(built, turns_of: str, radians: float, steps: int = 400):
    """Drive one joint and let the coupling carry the other."""

    model = built["model"]
    data = mujoco.MjData(model)
    data.qpos[:] = built["qpos_solved"]
    driver = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, turns_of)
    address = int(model.jnt_qposadr[driver])
    data.qpos[address] += radians
    mujoco.mj_forward(model, data)
    return data


def _coordinate(built, name: str, data) -> float:
    model = built["model"]
    joint = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
    return float(data.qpos[int(model.jnt_qposadr[joint])])


def test_a_gear_pair_counter_rotates_at_the_measured_ratio() -> None:
    built = dyn.build_model(*_gear_train("gears")[:2])
    assert built["model"].neq == 1
    assert int(built["model"].eq_type[0]) == int(mujoco.mjtEq.mjEQ_JOINT)
    coupling = built["couplings"][0]
    assert coupling["dependent_joint"] == "axle2"
    assert coupling["independent_joint"] == "axle1"
    assert coupling["slope"] == pytest.approx(-2.0)

    # The constraint is satisfied exactly where Ondsel put the pair, and at
    # the ratio it measured.
    data = _settle(built, "axle1", 0.0)
    assert _coordinate(built, "axle2", data) == pytest.approx(0.0, abs=1e-12)
    for angle in (0.3141592653589793, -1.0, 2.5):
        data = _settle(built, "axle1", angle)
        data.qpos[
            int(built["model"].jnt_qposadr[
                mujoco.mj_name2id(built["model"], mujoco.mjtObj.mjOBJ_JOINT, "axle2")
            ])
        ] = -2.0 * angle
        mujoco.mj_forward(built["model"], data)
        assert max(abs(float(value)) for value in data.efc_pos) < 1e-12


def test_a_belt_drives_the_same_way_round() -> None:
    built = dyn.build_model(*_gear_train("belt")[:2])
    assert built["couplings"][0]["slope"] == pytest.approx(2.0)


def test_the_gear_ratio_is_the_radius_ratio() -> None:
    for radius1, radius2, expected in ((20.0, 10.0, -2.0), (10.0, 40.0, -0.25)):
        built = dyn.build_model(*_gear_train("gears", radius1, radius2)[:2])
        assert built["couplings"][0]["slope"] == pytest.approx(expected)


def test_a_gear_train_actually_turns_the_second_wheel() -> None:
    """Driven, integrated, and checked against the measured ratio."""

    built = dyn.build_model(*_gear_train("gears")[:2])
    model = built["model"]
    data = mujoco.MjData(model)
    data.qpos[:] = built["qpos_solved"]
    data.qvel[0] = 1.0
    for _step in range(300):
        mujoco.mj_step(model, data)
    first = _coordinate(built, "axle1", data)
    second = _coordinate(built, "axle2", data)
    assert abs(first) > 0.1
    assert second == pytest.approx(-2.0 * first, rel=1.0e-3)


def test_a_screw_advances_its_measured_pitch_per_revolution() -> None:
    """One turn, four millimetres, and the sign Ondsel produced."""

    built = dyn.build_model(*_screw_stack(4.0)[:2])
    coupling = built["couplings"][0]
    assert coupling["dependent_joint"] == "guide"
    assert coupling["independent_joint"] == "spin"
    # −pitch per 2π, in metres per radian.
    assert coupling["slope"] == pytest.approx(-0.004 / (2.0 * math.pi))

    model = built["model"]
    # Exactly, as a constraint: one turn of the shaft is four millimetres of
    # nut, and the residual at that configuration is zero.
    data = mujoco.MjData(model)
    data.qpos[:] = built["qpos_solved"]
    data.qpos[
        int(model.jnt_qposadr[
            mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "spin")
        ])
    ] = 2.0 * math.pi
    data.qpos[
        int(model.jnt_qposadr[
            mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "guide")
        ])
    ] = -0.004
    mujoco.mj_forward(model, data)
    assert max(abs(float(value)) for value in data.efc_pos) < 1.0e-12

    # ...and under load. The nut's weight drives the thread here, which is
    # the hardest case for a soft equality: a heavy nut on a fine pitch has
    # to be held by a shaft with almost no inertia. It tracks its pitch to
    # under a percent, and the residual left over is a real screw's
    # elasticity rather than a coupling that let go.
    data = mujoco.MjData(model)
    data.qpos[:] = built["qpos_solved"]
    worst = 0.0
    for _step in range(500):
        mujoco.mj_step(model, data)
        worst = max(worst, max(abs(float(value)) for value in data.efc_pos))
    turn = _coordinate(built, "spin", data)
    travel = _coordinate(built, "guide", data)
    assert abs(turn) > 1.0
    assert dyn.length_mm(travel) == pytest.approx(
        -4.0 * turn / (2.0 * math.pi), rel=0.01
    )
    assert dyn.length_mm(worst) < 2.0


def test_the_screw_pitch_scales_the_coupling() -> None:
    for pitch, expected in ((1.5, -0.0015), (-4.0, 0.004)):
        built = dyn.build_model(*_screw_stack(pitch)[:2])
        assert built["couplings"][0]["slope"] == pytest.approx(
            expected / (2.0 * math.pi)
        )


def test_an_opposed_axis_flips_the_coupling_sign() -> None:
    """The sign comes from the frames, not from the joint declaration order.

    A wheel whose revolute axis points the other way turns the other way for
    the same gear pair, and nothing but the frames says so.
    """

    components, joints, _placements = _gear_train("gears")
    upright = dyn.build_model(components, joints)
    components, joints, _placements = _gear_train("gears")
    for joint in joints:
        if joint["name"] == "axle2":
            for connector in joint["connectors"]:
                connector["local_matrix"] = dyn.matrix_multiply(
                    connector["local_matrix"],
                    dyn.matrix_from_quaternion_wxyz(
                        dyn.quaternion_from_axis_angle_wxyz((1.0, 0.0, 0.0), math.pi)
                    ),
                )
    flipped = dyn.build_model(components, joints)
    assert upright["couplings"][0]["slope"] == pytest.approx(-2.0)
    assert flipped["couplings"][0]["slope"] == pytest.approx(2.0)


def test_a_rack_and_pinion_is_refused_rather_than_guessed() -> None:
    components, joints, _placements = _screw_stack()
    joints[-1]["kind"] = "rack_pinion"
    joints[-1]["parameters"] = {"pitch_radius_mm": 15.0}
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(components, joints)
    assert excinfo.value.reason == "unmapped_coupled_joint"
    assert "backwards" in excinfo.value.correction


def test_a_gear_on_a_component_nothing_places_is_refused() -> None:
    components, joints, _placements = _gear_train("gears")
    joints = [joint for joint in joints if joint["name"] != "axle2"]
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(components, joints)
    assert excinfo.value.reason == "uncouplable_component"


def test_a_gear_coupled_to_a_slider_is_refused() -> None:
    components, joints, _placements = _gear_train("gears")
    for joint in joints:
        if joint["name"] == "axle2":
            joint["kind"] = "slider"
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(components, joints)
    assert excinfo.value.reason == "coupled_joint_kind"


def test_a_screw_without_its_slider_is_refused() -> None:
    components, joints, _placements = _screw_stack()
    for joint in joints:
        if joint["name"] == "guide":
            joint["kind"] = "revolute"
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(components, joints)
    assert excinfo.value.reason == "coupled_joint_kind"
    assert "slider" in excinfo.value.correction


def test_coupled_axes_that_are_not_parallel_are_refused() -> None:
    components, joints, _placements = _gear_train("gears")
    for joint in joints:
        if joint["name"] == "mesh":
            joint["connectors"][1]["local_matrix"] = fx.frame(
                axis=(1.0, 0.0, 0.0), angle_degrees=30.0
            )
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(components, joints)
    assert excinfo.value.reason == "coupled_axes_not_parallel"


def test_components_on_different_parents_are_refused() -> None:
    """Two coordinates are only comparable against a common frame."""

    components, joints, placements = _gear_train("gears")
    for joint in joints:
        if joint["name"] == "axle2":
            joint["connectors"][0]["component"] = "pinion"
            joint["connectors"][0]["local_matrix"] = fx.closing_frame(
                placements, "housing", fx.frame((30.0, 0.0, 20.0)), "pinion"
            )
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(components, joints)
    assert excinfo.value.reason == "coupled_parents_differ"


def test_a_suppressed_coupling_is_ignored() -> None:
    components, joints, _placements = _gear_train("gears")
    joints[-1]["suppressed"] = True
    built = dyn.build_model(components, joints)
    assert built["model"].neq == 0
    assert built["couplings"] == []


def test_the_coupling_is_published_as_evidence() -> None:
    components, joints, _placements = _screw_stack()
    run = dyn.simulate(
        components,
        joints,
        start_time_s=0.0,
        end_time_s=0.2,
        frames_per_second=30,
    )
    coupling = run["evidence"]["couplings"][0]
    assert coupling["joint_kind"] == "screw"
    assert coupling["dependent_joint"] == "guide"
    assert coupling["slope"] == pytest.approx(-0.004 / (2.0 * math.pi))
