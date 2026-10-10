# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Machine drives in the dynamics model (ADR-640..644).

The four refusals docs/ARCHITECTURE-REVIEW.md §3.3 names as what stops a
printer, a CNC router, a loader or a tractor hitch, each removed and
measured here on a fixture built forwards from known joint values:

* a **slider on a closed loop** -- a cylinder between two links -- is
  taken into the spanning tree and the loop closes on a pin (ADR-640);
* **rack-and-pinion** follows OndselSolver's own law, ``x + R·θ`` constant
  in the rack's marker frame, across whatever tree path joins the rack to
  the pinion (ADR-641);
* an **n-joint coupling** -- CoreXY's belts, a differential -- is a fixed
  tendon held by an ``equality/tendon`` row (ADR-642);
* a **cylinder** is a position servo whose force range is bore × pressure,
  asymmetric by the rod's area (ADR-643);
* and the fit **sweep** moves every coordinate a coupling ties to the swept
  one (ADR-644).
"""

from __future__ import annotations

import math

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx

mujoco = pytest.importorskip("mujoco")

ALONG_X = fx.frame(axis=(0.0, 1.0, 0.0), angle_degrees=90.0)
ALONG_Y = fx.frame(axis=(1.0, 0.0, 0.0), angle_degrees=-90.0)
RADIUS = 10.0


def _qpos(built, data, joint: str) -> float:
    model = built["model"]
    index = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint)
    return float(data.qpos[int(model.jnt_qposadr[index])])


def _set(built, data, joint: str, value: float) -> None:
    model = built["model"]
    index = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint)
    data.qpos[int(model.jnt_qposadr[index])] = value


# -- rack and pinion ------------------------------------------------------------


def _travelling_pinion(radius: float = RADIUS):
    """A rack that is the frame, and a pinion riding a carriage along it."""

    components, joints, placements = fx.build(
        [
            {"name": "frame", "grounded": True, "size": (400.0, 40.0, 10.0)},
            {"name": "carriage", "size": (60.0, 60.0, 20.0)},
            {"name": "pinion", "size": (20.0, 20.0, 10.0)},
        ],
        [
            {"name": "rail", "kind": "slider", "parent": "frame", "child": "carriage",
             "parent_frame": ALONG_X, "child_frame": ALONG_X, "values": [0.05]},
            {"name": "spin", "kind": "revolute", "parent": "carriage", "child": "pinion",
             "parent_frame": fx.frame((0.0, 0.0, 20.0)), "child_frame": fx.frame(),
             "values": [0.3]},
        ],
    )
    joints.append({
        "name": "mesh", "kind": "rack_pinion", "suppressed": False,
        "parameters": {"pitch_radius_mm": radius},
        "length_limits_mm": None, "angle_limits_degrees": None,
        # The rack connector on its pitch line below the pinion, +Z along
        # the rack; the pinion's at its centre, +Z along its axis.
        "connectors": [
            {"component": "frame", "local_matrix": fx.frame((0.0, -radius, 20.0),
                                                            axis=(0.0, 1.0, 0.0),
                                                            angle_degrees=90.0)},
            {"component": "pinion", "local_matrix": fx.frame()},
        ],
    })
    return components, joints


def _sliding_rack(radius: float = RADIUS):
    """``lib.rack_and_pinion``'s datum: a fixed pinion, a rack below it on a slider."""

    components, joints, placements = fx.build(
        [
            {"name": "frame", "grounded": True, "size": (200.0, 80.0, 10.0)},
            {"name": "pinion", "size": (20.0, 20.0, 10.0)},
            {"name": "rack", "size": (200.0, 10.0, 10.0)},
        ],
        [
            {"name": "spin", "kind": "revolute", "parent": "frame", "child": "pinion",
             "parent_frame": fx.frame(), "child_frame": fx.frame(), "values": [0.2]},
            {"name": "guide", "kind": "slider", "parent": "frame", "child": "rack",
             "parent_frame": fx.frame((0.0, -radius, 0.0), axis=(0.0, 1.0, 0.0),
                                      angle_degrees=90.0),
             "child_frame": ALONG_X, "values": [0.01]},
        ],
    )
    joints.append({
        "name": "mesh", "kind": "rack_pinion", "suppressed": False,
        "parameters": {"pitch_radius_mm": radius},
        "length_limits_mm": None, "angle_limits_degrees": None,
        "connectors": [
            {"component": "rack", "local_matrix": ALONG_X},
            {"component": "pinion", "local_matrix": fx.frame()},
        ],
    })
    return components, joints


def test_a_rack_moves_plus_x_for_an_anticlockwise_pinion_above_it() -> None:
    """lib.rack_and_pinion's datum, and Ondsel's law: x + R·θ held."""

    built = dyn.build_model(*_sliding_rack())
    coupling = built["couplings"][0]
    assert coupling["joint_kind"] == "rack_pinion"
    assert (coupling["dependent_joint"], coupling["independent_joint"]) == ("guide", "spin")
    assert coupling["slope"] == pytest.approx(dyn.length_m(RADIUS))
    data = mujoco.MjData(built["model"])
    data.qpos[:] = built["qpos_solved"]
    _set(built, data, "spin", 0.2 + 0.5)
    _set(built, data, "guide", 0.01 + dyn.length_m(RADIUS) * 0.5)
    mujoco.mj_forward(built["model"], data)
    assert max(abs(float(v)) for v in data.efc_pos) < 1.0e-12


def test_a_travelling_pinion_rolls_back_along_a_rack_below_it() -> None:
    """The gantry case: the rack is the frame and the pinion rides along."""

    built = dyn.build_model(*_travelling_pinion())
    coupling = built["couplings"][0]
    assert (coupling["dependent_joint"], coupling["independent_joint"]) == ("rail", "spin")
    # Anticlockwise on a rack below: the centre rolls -X.
    assert coupling["slope"] == pytest.approx(-dyn.length_m(RADIUS))

    run = dyn.simulate(
        *_travelling_pinion(), start_time_s=0.0, end_time_s=1.0, frames_per_second=30,
        gravity_m_s2=[0.0, 0.0, 0.0],
        actuators=[{"joint": "spin", "motion_type": "angular", "kind": "velocity",
                    "control_deg_per_s": "90", "damping_nmms_per_deg": 2000.0}],
    )
    first, last = run["frames"][1], run["frames"][-1]
    turned = math.radians(90.0) * 1.0
    travel = (last["component_placements"]["carriage"]["position_mm"][0]
              - first["component_placements"]["carriage"]["position_mm"][0])
    assert travel == pytest.approx(-RADIUS * turned, rel=0.05)


def test_a_negative_pitch_radius_meshes_a_rack_on_the_other_side() -> None:
    built = dyn.build_model(*_sliding_rack(-RADIUS))
    assert built["couplings"][0]["slope"] == pytest.approx(-dyn.length_m(RADIUS))


def test_a_rack_and_pinion_exports_and_reloads() -> None:
    built = dyn.build_model(*_travelling_pinion())
    exported = dyn.export_mjcf(built)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"])
    assert reloaded.neq == 1 and int(reloaded.eq_type[0]) == int(mujoco.mjtEq.mjEQ_JOINT)


# -- a cylinder in a linkage ----------------------------------------------------

ARM_PIN = 300.0
BASE = (250.0, -100.0)


def _lift_arm(*, arm_degrees: float = 20.0, rod_first: bool = True):
    """A loader's lift arm: a boom on a pin, raised by a cylinder on two pins.

    ``boom`` turns about the frame's pin at the origin; the cylinder's
    ``barrel`` is pinned to the frame at ``BASE`` and its ``rod`` slides out
    of it to the boom's pin ``ARM_PIN`` along the boom. With the rod's pin
    listed before the stroke, breadth-first would close the loop on the
    slider -- the case ADR-640 grows again.
    """

    theta = math.radians(arm_degrees)
    pin = (ARM_PIN * math.cos(theta), ARM_PIN * math.sin(theta))
    length = math.dist(pin, BASE)
    phi = math.atan2(pin[1] - BASE[1], pin[0] - BASE[0])
    components, joints, placements = fx.build(
        [
            {"name": "frame", "grounded": True, "size": (300.0, 100.0, 20.0)},
            {"name": "boom", "size": (400.0, 40.0, 20.0)},
            {"name": "barrel", "size": (200.0, 50.0, 50.0)},
            {"name": "rod", "size": (220.0, 25.0, 25.0)},
        ],
        [
            {"name": "boom_pin", "kind": "revolute", "parent": "frame", "child": "boom",
             "parent_frame": fx.frame(), "child_frame": fx.frame(), "values": [theta],
             "angle_limits_degrees": [0.0, 60.0]},
            {"name": "base_pin", "kind": "revolute", "parent": "frame", "child": "barrel",
             "parent_frame": fx.frame((BASE[0], BASE[1], 0.0)), "child_frame": fx.frame(),
             "values": [phi]},
            {"name": "stroke", "kind": "slider", "parent": "barrel", "child": "rod",
             "parent_frame": ALONG_X, "child_frame": ALONG_X,
             "values": [dyn.length_m(length)], "length_limits_mm": [200.0, 420.0]},
        ],
    )
    closing = fx.closing_joint("rod_pin", "revolute", "rod", "boom", fx.frame(), placements)
    if rod_first:
        joints.insert(2, closing)
    else:
        joints.append(closing)
    return components, joints, length


def _boom_angle(placement) -> float:
    quaternion = dyn.quaternion_wxyz_from_xyzw(placement["rotation_xyzw"])
    matrix = dyn.matrix_from_quaternion_wxyz(quaternion, (0.0, 0.0, 0.0))
    return math.atan2(matrix[4], matrix[0])


def _cylinder(control_mm: str, *, bore_mm=40.0, rod_mm=20.0, pressure_bar=160.0):
    return {"joint": "stroke", "motion_type": "linear", "kind": "position",
            "control_mm": control_mm, "stiffness_n_per_mm": 2000.0, "damping_ns_per_mm": 40.0,
            "cylinder": {"bore_mm": bore_mm, "rod_mm": rod_mm, "pressure_bar": pressure_bar}}


def test_a_cylinder_between_two_links_builds_and_closes_on_a_pin() -> None:
    for rod_first in (True, False):
        components, joints, _length = _lift_arm(rod_first=rod_first)
        tree = dyn.extract_tree(components, joints)
        rod = next(body for body in tree["bodies"] if body["name"] == "rod")
        assert rod["joint"] == "stroke" and rod["mujoco_joints"] == ["slide"]
        assert [c["joint"] for c in tree["closures"]] == ["rod_pin"]
    built = dyn.build_model(components, joints)
    assert built["loop_mobility"]["export_mobility"] == 1


def test_a_cylinder_drives_the_boom_where_the_triangle_puts_it() -> None:
    """Extend the rod 60 mm; the boom's pin stays the rod's length from the base."""

    components, joints, length = _lift_arm()
    run = dyn.simulate(
        components, joints, start_time_s=0.0, end_time_s=1.5, frames_per_second=60,
        time_step_s=0.00025, actuators=[_cylinder(f"{length:.6f} + 40*time")],
    )
    actuator = run["built"]["actuators"][0]
    assert actuator["effort_range_si"][0] == pytest.approx(-0.75 * actuator["effort_range_si"][1])
    model = run["built"]["model"]
    assert list(model.actuator_forcerange[0]) == pytest.approx(actuator["effort_range_si"])
    worst = 0.0
    angles = []
    for frame in run["frames"][1:]:
        poses = frame["component_placements"]
        theta = _boom_angle(poses["boom"])
        pin = (ARM_PIN * math.cos(theta), ARM_PIN * math.sin(theta))
        rod = poses["rod"]["position_mm"]
        worst = max(worst, math.dist(pin, rod[:2]))
        angles.append(math.degrees(theta))
    assert angles[-1] - angles[0] > 5.0, angles[-1] - angles[0]
    assert worst < dyn.MJCF_POSE_TOLERANCE_MM, worst
    assert run["worst_closure_residual_mm"] < dyn.MJCF_POSE_TOLERANCE_MM


def test_a_cylinder_too_weak_for_its_load_holds_short() -> None:
    """At 2 bar a 40 mm bore pushes 251 N: the boom's weight wins."""

    components, joints, length = _lift_arm()
    run = dyn.simulate(
        components, joints, start_time_s=0.0, end_time_s=1.0, frames_per_second=30,
        time_step_s=0.0005, actuators=[_cylinder(f"{length + 60.0:.6f}", pressure_bar=2.0)],
    )
    evidence = run["evidence"]["actuators"][0]
    assert evidence["saturated"] is True
    assert evidence["effort_range_si"][1] == pytest.approx(2.0e5 * math.pi * 0.04**2 / 4.0)


def test_two_sliders_on_one_pair_are_still_refused_with_the_fix() -> None:
    components, joints, _placements = fx.build(
        [{"name": "frame", "grounded": True}, {"name": "carriage"}],
        [{"name": "rail_a", "kind": "slider", "parent": "frame", "child": "carriage",
          "parent_frame": ALONG_X, "child_frame": ALONG_X, "values": [0.0]}],
    )
    joints.append({**joints[0], "name": "rail_b"})
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(components, joints)
    assert excinfo.value.reason == "unclosable_loop_joint"


# -- n-joint couplings: CoreXY ------------------------------------------------------

#: A 20-tooth GT2 pulley: 40 mm of belt per turn.
BELT_MM_PER_DEG = 40.0 / 360.0


def _corexy():
    """A gantry on Y, a carriage on X along it, and two motors on the frame."""

    components, joints, placements = fx.build(
        [
            {"name": "frame", "grounded": True, "size": (400.0, 400.0, 10.0)},
            {"name": "gantry", "size": (360.0, 30.0, 20.0)},
            {"name": "carriage", "size": (50.0, 50.0, 20.0)},
            {"name": "motor_a", "size": (12.0, 12.0, 16.0)},
            {"name": "motor_b", "size": (12.0, 12.0, 16.0)},
        ],
        [
            {"name": "y", "kind": "slider", "parent": "frame", "child": "gantry",
             "parent_frame": fx.frame((0.0, 0.0, 30.0), axis=(1.0, 0.0, 0.0),
                                      angle_degrees=-90.0),
             "child_frame": ALONG_Y, "values": [0.02],
             "length_limits_mm": [-150.0, 150.0]},
            {"name": "x", "kind": "slider", "parent": "gantry", "child": "carriage",
             "parent_frame": ALONG_X, "child_frame": ALONG_X, "values": [-0.03],
             "length_limits_mm": [-150.0, 150.0]},
            {"name": "a", "kind": "revolute", "parent": "frame", "child": "motor_a",
             "parent_frame": fx.frame((-190.0, 190.0, 30.0)), "child_frame": fx.frame(),
             "values": [0.4]},
            {"name": "b", "kind": "revolute", "parent": "frame", "child": "motor_b",
             "parent_frame": fx.frame((190.0, 190.0, 30.0)), "child_frame": fx.frame(),
             "values": [-1.1]},
        ],
    )
    k = BELT_MM_PER_DEG / 2.0

    def term(joint, ratio):
        return {"joint": joint, "motion_type": "linear" if joint in "xy" else "angular",
                "ratio": ratio}

    couplings = [
        {"name": "coupling/x", "terms": [term("x", 1.0), term("a", -k), term("b", -k)]},
        {"name": "coupling/y", "terms": [term("y", 1.0), term("a", -k), term("b", k)]},
    ]
    return components, joints, couplings


def test_corexy_is_two_fixed_tendons_held_where_the_assembly_solved() -> None:
    components, joints, couplings = _corexy()
    built = dyn.build_model(components, joints, couplings=couplings)
    model = built["model"]
    assert model.ntendon == 2 and model.neq == 2
    assert {int(t) for t in model.eq_type} == {int(mujoco.mjtEq.mjEQ_TENDON)}
    data = mujoco.MjData(model)
    data.qpos[:] = built["qpos_solved"]
    mujoco.mj_forward(model, data)
    assert max(abs(float(v)) for v in data.efc_pos) < 1.0e-12
    # Both motors 90 degrees the same way: pure X, 10 mm.
    _set(built, data, "a", 0.4 + math.pi / 2.0)
    _set(built, data, "b", -1.1 + math.pi / 2.0)
    _set(built, data, "x", -0.03 + 0.010)
    mujoco.mj_forward(model, data)
    assert max(abs(float(v)) for v in data.efc_pos) < 1.0e-12
    # Opposite ways: pure Y.
    data.qpos[:] = built["qpos_solved"]
    _set(built, data, "a", 0.4 + math.pi / 2.0)
    _set(built, data, "b", -1.1 - math.pi / 2.0)
    _set(built, data, "y", 0.02 + 0.010)
    mujoco.mj_forward(model, data)
    assert max(abs(float(v)) for v in data.efc_pos) < 1.0e-12


def test_corexy_driven_by_its_motors_moves_the_carriage_diagonally() -> None:
    """One motor alone moves the carriage at 45 degrees, as CoreXY does."""

    components, joints, couplings = _corexy()
    run = dyn.simulate(
        components, joints, couplings=couplings, start_time_s=0.0, end_time_s=1.0,
        frames_per_second=30, gravity_m_s2=[0.0, 0.0, 0.0],
        # A NEMA17's rotor, 54 g*cm^2 (ADR-642): a coupled motor with no
        # inertia of its own is driven by a gain the soft equality cannot
        # hold, and the belt stretches by millimetres (measured: 20 mm at
        # 50 N*mm*s/deg with no armature, 0.008 mm at 0.05 with it).
        joint_dynamics=[{"joint": j, "motion_type": "angular", "armature_kgmm2": 5.4}
                        for j in ("a", "b")],
        actuators=[
            {"joint": "a", "motion_type": "angular", "kind": "velocity",
             "control_deg_per_s": "180", "damping_nmms_per_deg": 0.05},
            {"joint": "b", "motion_type": "angular", "kind": "velocity",
             "control_deg_per_s": "0", "damping_nmms_per_deg": 0.05},
        ],
    )
    first = run["frames"][1]["component_placements"]["carriage"]["position_mm"]
    last = run["frames"][-1]["component_placements"]["carriage"]["position_mm"]
    dx, dy = last[0] - first[0], last[1] - first[1]
    assert dx == pytest.approx(dy, rel=0.02)
    assert dx > 5.0
    evidence = run["evidence"]
    assert [c["constraint"] for c in evidence["linear_couplings"]] == ["tendon", "tendon"]


def test_a_two_term_coupling_is_a_joint_equality() -> None:
    components, joints, _ = _corexy()
    built = dyn.build_model(components, joints, couplings=[
        {"name": "coupling/belt", "terms": [
            {"joint": "x", "motion_type": "linear", "ratio": 1.0},
            {"joint": "a", "motion_type": "angular", "ratio": -BELT_MM_PER_DEG}]}])
    assert built["model"].ntendon == 0
    assert int(built["model"].eq_type[0]) == int(mujoco.mjtEq.mjEQ_JOINT)
    assert built["linear_couplings"][0]["slope"] == pytest.approx(
        BELT_MM_PER_DEG * 180.0 / math.pi / 1000.0)


def test_a_coupling_on_a_loop_closure_is_refused_with_the_trees_reason() -> None:
    components, joints, length = _lift_arm()
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(components, joints, couplings=[{"name": "c", "terms": [
            {"joint": "rod_pin", "motion_type": "angular", "ratio": 1.0},
            {"joint": "boom_pin", "motion_type": "angular", "ratio": 1.0}]}])
    assert excinfo.value.reason == "joint_has_no_coordinate"
    assert "closes a loop" in str(excinfo.value)


def test_corexy_exports_its_tendons_and_reloads_the_same_model() -> None:
    components, joints, couplings = _corexy()
    built = dyn.build_model(components, joints, couplings=couplings)
    exported = dyn.export_mjcf(built)
    xml = exported["xml"].decode() if isinstance(exported["xml"], bytes) else exported["xml"]
    assert "<tendon>" in xml and "<fixed" in xml
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"])
    assert reloaded.ntendon == 2


# -- the sweep moves what a coupling ties --------------------------------------------


def _joints_by_name(joints):
    return {joint["name"]: joint for joint in joints}


def test_a_swept_corexy_axis_turns_both_motors_and_holds_the_other_axis() -> None:
    components, joints, couplings = _corexy()
    tree = dyn.extract_tree(components, joints)
    placements = {c["name"]: c["solved_matrix"] for c in components}
    solved = dyn.coupled_sweep(tree, _joints_by_name(joints), placements, couplings, "x",
                               [0.0, 20.0])
    assert sorted(row["joint"] for row in solved["followers"].values()) == ["a", "b"]
    assert solved["held"] == ["y"]
    # 20 mm of X is 20 / (40/360) = 180 degrees of each motor, the same way.
    for row in solved["followers"].values():
        assert row["per_unit_si"] * 0.020 == pytest.approx(math.pi, rel=1e-9)
    carriage = solved["poses"][1]["bodies"]["carriage"]
    assert carriage[3] == pytest.approx(20.0) and carriage[7] == pytest.approx(0.0, abs=1e-9)
    assert solved["poses"][1]["bodies"]["gantry"][3] == pytest.approx(0.0, abs=1e-9)


def test_a_swept_leadscrew_nut_turns_its_screw() -> None:
    components, joints, placements = fx.build(
        [{"name": "frame", "grounded": True}, {"name": "nut"}, {"name": "shaft"}],
        [{"name": "guide", "kind": "slider", "parent": "frame", "child": "nut",
          "parent_frame": fx.frame((0.0, 0.0, 30.0)), "child_frame": fx.frame(),
          "values": [0.0], "length_limits_mm": [0.0, 100.0]},
         {"name": "spin", "kind": "revolute", "parent": "frame", "child": "shaft",
          "parent_frame": fx.frame((0.0, 0.0, 10.0)), "child_frame": fx.frame(),
          "values": [0.0]}],
    )
    joints.append({"name": "thread", "kind": "screw", "suppressed": False,
                   "parameters": {"thread_pitch_mm": 8.0}, "length_limits_mm": None,
                   "angle_limits_degrees": None,
                   "connectors": [{"component": "nut", "local_matrix": fx.frame()},
                                  {"component": "shaft", "local_matrix": fx.frame()}]})
    tree = dyn.extract_tree(components, joints)
    solved = dyn.coupled_sweep(tree, _joints_by_name(joints), placements, [], "guide", [8.0])
    turn = solved["followers"]["spin"]["per_unit_si"] * 0.008
    assert turn == pytest.approx(-2.0 * math.pi)
    assert dyn.coupled_sweep(tree, _joints_by_name(joints), placements, [], "spin", [1.0]) is not None


# -- a tool point and the area it must reach (ADR-645) -------------------------------


def test_a_gantry_nozzle_reaches_its_bed_exactly_and_says_by_how_much_it_misses() -> None:
    components, joints, _couplings = _corexy()
    tree = dyn.extract_tree(components, joints)
    placements = {c["name"]: c["solved_matrix"] for c in components}
    tool = {"component": "carriage", "origin_mm": [0.0, 0.0, -10.0], "axis": [0, 0, -1],
            "work_area_mm": [[-140.0, -140.0, 20.0], [140.0, 140.0, 20.0]], "work_frame": None}
    reach = dyn.tool_workspace(tree, _joints_by_name(joints), placements, tool)
    assert reach["status"] == "measured" and reach["exact"] is True
    assert sorted(reach["sampled_joints"]) == ["x", "y"] and reach["unsampled"] == []
    assert reach["reach_box_mm"][0][:2] == pytest.approx([-150.0, -150.0])
    assert reach["reach_box_mm"][1][:2] == pytest.approx([150.0, 150.0])
    assert reach["covers"] is True
    wide = dict(tool, work_area_mm=[[-160.0, -140.0, 20.0], [140.0, 140.0, 20.0]])
    reach = dyn.tool_workspace(tree, _joints_by_name(joints), placements, wide)
    assert reach["covers"] is False and len(reach["corners_missed"]) == 2
    assert reach["short_by_mm"]["low"][0] == pytest.approx(10.0)


def test_a_tool_is_read_in_its_work_frame() -> None:
    """The nozzle against the gantry it rides: only X moves it there."""

    components, joints, _couplings = _corexy()
    tree = dyn.extract_tree(components, joints)
    placements = {c["name"]: c["solved_matrix"] for c in components}
    reach = dyn.tool_workspace(tree, _joints_by_name(joints), placements,
                               {"component": "carriage", "work_frame": "gantry"})
    assert reach["sampled_joints"] == ["x"]
    span = [b - a for a, b in zip(*reach["reach_box_mm"])]
    assert span == pytest.approx([300.0, 0.0, 0.0], abs=1e-9)


def test_a_tool_on_a_loop_is_not_sampled_as_if_open() -> None:
    components, joints, _length = _lift_arm()
    tree = dyn.extract_tree(components, joints)
    placements = {c["name"]: c["solved_matrix"] for c in components}
    reach = dyn.tool_workspace(tree, _joints_by_name(joints), placements,
                               {"component": "boom", "origin_mm": [400.0, 0.0, 0.0]})
    assert reach["status"] == "unmeasured" and "closed loop" in reach["reason"]
