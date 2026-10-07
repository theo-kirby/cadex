# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Closed linkages, driven (ADR-593, orun5 L1).

M2 closed a loop with ``equality/connect`` and M4 put an actuator on a
tree joint; this is the claim the two make together: an actuator on the
crank of a closed chain moves the *whole* chain where its geometry says,
across the crank's range, with the closure holding inside the MJCF's pose
contract (``MJCF_POSE_TOLERANCE_MM``, ADR-584). The comparison is made
against the crank angle the run actually reached, so a PD lag is not
mistaken for a kinematic error, and against the analytic output of the
linkage: the four-bar's rocker by circle intersection, the slider-crank's
slider by ``r cos θ + sqrt(l² - r² sin² θ)``.

And the two ways a loop can mean something different in MuJoCo than on
the bench are refused: a closing hinge whose axis would have to tilt (a
connect pins the pin, not the axis), and a drive on a loop with no motion
left in it.
"""

from __future__ import annotations

import math

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx

mujoco = pytest.importorskip("mujoco")

GROUND, CRANK, COUPLER, ROCKER = 200.0, 80.0, 220.0, 120.0
ROD = 200.0

#: A connect is a soft constraint with a two-step time constant, so how far
#: a driven loop sits open grows with the step squared and the drive speed
#: squared. Measured on the four-bar's crank at 225 deg/s: 0.045 mm of
#: closure error at the 2 ms default, 0.0062 mm at 1 ms, 0.0012 mm at
#: 0.5 ms -- so a linkage that must hold the MJCF's 0.01 mm pose contract
#: while it moves this fast steps at 0.5 ms (ADR-593).
STEP_S = 0.0005


def _servo(joint: str, control_deg: str) -> dict:
    return {
        "joint": joint,
        "motion_type": "angular",
        "kind": "position",
        "control_deg": control_deg,
        "stiffness_nmm_per_deg": 500.0,
        "damping_nmms_per_deg": 5.0,
    }


def _rocker_angle(theta: float, previous: float) -> float:
    """The rocker's angle at crank ``theta``, on the branch nearest ``previous``."""

    b = (CRANK * math.cos(theta), CRANK * math.sin(theta))
    d = (GROUND, 0.0)
    span = math.dist(b, d)
    base = math.atan2(b[1] - d[1], b[0] - d[0])
    interior = math.acos((ROCKER**2 + span**2 - COUPLER**2) / (2.0 * ROCKER * span))
    candidates = [base + interior, base - interior]
    return min(
        candidates,
        key=lambda angle: abs(math.remainder(angle - previous, math.tau)),
    )


def _four_bar(*, crank_degrees: float = 50.0, closing_tilt_degrees: float = 0.0):
    """Ground, crank, coupler and rocker; pin ``c`` closes the loop."""

    theta = math.radians(crank_degrees)
    b = (CRANK * math.cos(theta), CRANK * math.sin(theta))
    # The fixture's branch: the coupler's far pin above the line B-D.
    span = math.dist(b, (GROUND, 0.0))
    base = math.atan2(-b[1], GROUND - b[0])
    interior = math.acos((COUPLER**2 + span**2 - ROCKER**2) / (2.0 * COUPLER * span))
    coupler = base + interior
    c = (b[0] + COUPLER * math.cos(coupler), b[1] + COUPLER * math.sin(coupler))
    rocker = math.atan2(c[1], c[0] - GROUND)

    def link(name, length, grounded=False):
        return {"name": name, "grounded": grounded, "size": (length, 20.0, 10.0)}

    components, joints, placements = fx.build(
        [link("ground", GROUND, True), link("crank", CRANK),
         link("coupler", COUPLER), link("rocker", ROCKER)],
        [
            {"name": "a", "kind": "revolute", "parent": "ground", "child": "crank",
             "parent_frame": fx.frame(), "child_frame": fx.frame(), "values": [theta]},
            {"name": "d", "kind": "revolute", "parent": "ground", "child": "rocker",
             "parent_frame": fx.frame((GROUND, 0.0, 0.0)), "child_frame": fx.frame(),
             "values": [rocker]},
            {"name": "b", "kind": "revolute", "parent": "crank", "child": "coupler",
             "parent_frame": fx.frame((CRANK, 0.0, 0.0)), "child_frame": fx.frame(),
             "values": [coupler - theta]},
        ],
    )
    joints.append(
        fx.closing_joint(
            "c", "revolute", "coupler", "rocker",
            fx.frame((COUPLER, 0.0, 0.0), axis=(1.0, 0.0, 0.0),
                     angle_degrees=closing_tilt_degrees),
            placements,
        )
    )
    return components, joints


def _slider_crank(*, crank_degrees: float = 30.0):
    """A crank on the ground, a rod, and a slider on the crank's line."""

    theta = math.radians(crank_degrees)
    x = CRANK * math.cos(theta) + math.sqrt(ROD**2 - (CRANK * math.sin(theta)) ** 2)
    rod = math.atan2(-CRANK * math.sin(theta), x - CRANK * math.cos(theta))
    along_x = fx.frame(axis=(0.0, 1.0, 0.0), angle_degrees=90.0)
    components, joints, placements = fx.build(
        [
            {"name": "ground", "grounded": True, "size": (300.0, 40.0, 10.0)},
            {"name": "crank", "size": (CRANK, 20.0, 10.0)},
            {"name": "rod", "size": (ROD, 15.0, 10.0)},
            {"name": "slider", "size": (40.0, 30.0, 30.0)},
        ],
        [
            {"name": "crank_pin", "kind": "revolute", "parent": "ground", "child": "crank",
             "parent_frame": fx.frame(), "child_frame": fx.frame(), "values": [theta]},
            {"name": "guide", "kind": "slider", "parent": "ground", "child": "slider",
             "parent_frame": along_x, "child_frame": fx.frame(),
             "values": [dyn.length_m(x)]},
            {"name": "big_end", "kind": "revolute", "parent": "crank", "child": "rod",
             "parent_frame": fx.frame((CRANK, 0.0, 0.0)), "child_frame": fx.frame(),
             "values": [rod - theta]},
        ],
    )
    joints.append(
        fx.closing_joint(
            "gudgeon", "revolute", "rod", "slider", fx.frame((ROD, 0.0, 0.0)), placements
        )
    )
    return components, joints


def _angle(placement) -> float:
    """A planar body's heading: the angle of its own +X in the world XY plane."""

    quaternion = dyn.quaternion_wxyz_from_xyzw(placement["rotation_xyzw"])
    matrix = dyn.matrix_from_quaternion_wxyz(quaternion, (0.0, 0.0, 0.0))
    return math.atan2(matrix[4], matrix[0])


def test_a_four_bar_driven_by_its_crank_follows_the_analytic_rocker() -> None:
    components, joints = _four_bar()
    tree = dyn.extract_tree(components, joints)
    assert [closure["joint"] for closure in tree["closures"]] == ["c"]
    run = dyn.simulate(
        components, joints, start_time_s=0.0, end_time_s=2.0, frames_per_second=60,
        time_step_s=STEP_S,
        # A whole turn and a quarter: this is a Grashof crank-rocker
        # (80 + 220 <= 200 + 120), so the crank goes all the way round.
        actuators=[_servo("a", "50 + 225*time")],
    )
    mobility = run["built"]["loop_mobility"]
    assert (mobility["export_mobility"], mobility["mechanism_mobility"]) == (1, 1)
    worst = 0.0
    reached = []
    rocker = None
    for frame in run["frames"]:
        poses = frame["component_placements"]
        theta = _angle(poses["crank"])
        expected = _rocker_angle(theta, _angle(poses["rocker"]) if rocker is None else rocker)
        rocker = expected
        worst = max(worst, abs(math.remainder(_angle(poses["rocker"]) - expected, math.tau)))
        reached.append(theta)
    swept = sum(
        abs(math.remainder(b - a, math.tau)) for a, b in zip(reached, reached[1:])
    )
    assert swept > math.radians(400.0), math.degrees(swept)
    # The rocker's far pin within the export's pose contract of where the
    # geometry puts it, at every frame of a full turn.
    assert ROCKER * worst < dyn.MJCF_POSE_TOLERANCE_MM, ROCKER * worst
    assert run["worst_closure_residual_mm"] < dyn.MJCF_POSE_TOLERANCE_MM


def test_a_slider_crank_driven_by_its_crank_follows_the_analytic_stroke() -> None:
    components, joints = _slider_crank()
    run = dyn.simulate(
        components, joints, start_time_s=0.0, end_time_s=2.0, frames_per_second=60,
        time_step_s=STEP_S,
        actuators=[_servo("crank_pin", "30 + 225*time")],
    )
    assert [c["joint"] for c in run["built"]["tree"]["closures"]] == ["gudgeon"]
    worst = 0.0
    strokes = []
    for frame in run["frames"]:
        poses = frame["component_placements"]
        theta = _angle(poses["crank"])
        expected = CRANK * math.cos(theta) + math.sqrt(
            ROD**2 - (CRANK * math.sin(theta)) ** 2
        )
        strokes.append(poses["slider"]["position_mm"][0])
        worst = max(worst, abs(poses["slider"]["position_mm"][0] - expected))
    # Top and bottom dead centre were both passed: the whole stroke, 2r.
    assert max(strokes) - min(strokes) == pytest.approx(2.0 * CRANK, abs=0.5)
    assert worst < dyn.MJCF_POSE_TOLERANCE_MM, worst
    assert run["worst_closure_residual_mm"] < dyn.MJCF_POSE_TOLERANCE_MM


def test_a_loop_whose_closing_axis_must_tilt_is_refused_as_over_constrained() -> None:
    components, joints = _four_bar(closing_tilt_degrees=30.0)
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(components, joints)
    assert excinfo.value.reason == "overconstrained_loop"
    assert "'c'" in str(excinfo.value)
    assert excinfo.value.observed == {
        "closures": ["c"], "export_mobility": 1, "mechanism_mobility": 0,
    }
    assert "ball joint" in excinfo.value.correction


def test_a_ball_ended_closure_is_exact_and_is_not_refused() -> None:
    components, joints = _four_bar(closing_tilt_degrees=30.0)
    joints[-1]["kind"] = "ball"
    built = dyn.build_model(components, joints)
    assert built["loop_mobility"]["export_mobility"] == built["loop_mobility"]["mechanism_mobility"]


def test_a_drive_on_a_rigid_triangle_is_refused() -> None:
    components, joints, placements = fx.build(
        [
            {"name": "ground", "grounded": True, "size": (200.0, 20.0, 10.0)},
            {"name": "left", "size": (100.0, 20.0, 10.0)},
            {"name": "right", "size": (100.0, 20.0, 10.0)},
        ],
        [
            {"name": "left_pin", "kind": "revolute", "parent": "ground", "child": "left",
             "parent_frame": fx.frame(), "child_frame": fx.frame(),
             "values": [math.radians(60.0)]},
            {"name": "right_pin", "kind": "revolute", "parent": "ground", "child": "right",
             "parent_frame": fx.frame((100.0, 0.0, 0.0)), "child_frame": fx.frame(),
             "values": [math.radians(120.0)]},
        ],
    )
    joints.append(
        fx.closing_joint("apex", "revolute", "left", "right", fx.frame((100.0, 0.0, 0.0)), placements)
    )
    # Undriven, a truss is a legitimate model.
    assert dyn.build_model(components, joints)["loop_mobility"]["mechanism_mobility"] == 0
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(components, joints, actuators=[_servo("left_pin", "60")])
    assert excinfo.value.reason == "actuator_locked_by_loop"
    assert excinfo.value.observed["joints"] == ["left_pin"]


def test_the_fit_sweep_refuses_each_joint_of_a_closed_loop_naming_the_loop() -> None:
    """A one-joint sweep would tear the chain open; it says so, by name."""

    import cadex_assembly_worker as worker

    components, joints = _four_bar()
    component_data = {c["name"]: {"grounded": c["grounded"]} for c in components}
    joint_data = {
        joint["name"]: {
            **{key: joint[key] for key in ("kind", "suppressed", "parameters", "length_limits_mm")},
            "angle_limits_degrees": [-180.0, 180.0],
            "connectors": [
                {"component_output": c["component"], "local_frame": {"matrix": c["local_matrix"]}}
                for c in joint["connectors"]
            ],
        }
        for joint in joints
    }
    report = worker._measure_joint_sweeps(
        {}, component_data, joint_data, [], {"sweep_step_degrees": 1.0}, True
    )
    assert report["status"] == "incomplete"
    assert [row["joint"] for row in report["joints"]] == ["a", "d", "b", "c"]
    for row in report["joints"]:
        assert row["status"] == "incomplete"
        assert "closed loop ['b', 'a', 'd', 'c']" in row["reason"]
        assert "closed by 'c'" in row["reason"]
