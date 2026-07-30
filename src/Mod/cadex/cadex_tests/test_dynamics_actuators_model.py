# SPDX-License-Identifier: LGPL-2.1-or-later

"""Actuators in the compiled model, and in the loop (M4, phase 4).

Phase 2 built the records and phase 3 the formula; this is where they reach
MuJoCo. Three things are asserted that nothing above this file could:

* the actuator compiled into what the translator asked for -- gear, limits,
  and the gain and bias parameters that *are* the PD loop, checked on the
  compiled model because that is where a MuJoCo release changing a default
  would land;
* the control reaches ``data.ctrl`` in the model's units at the instant the
  index says, and the mechanism moves accordingly;
* an actuator that is doing nothing changes nothing at all -- byte for
  byte, on the four-bar, because these traces are compared as bytes across
  processes and a zero motor moving the answer would be a prior problem.
"""

from __future__ import annotations

import json
import math

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx

mujoco = pytest.importorskip("mujoco")


def _servo(**overrides):
    entry = {
        "joint": "hinge",
        "motion_type": "angular",
        "kind": "position",
        "control_deg": "30",
        "stiffness_nmm_per_deg": 4000.0,
        "damping_nmms_per_deg": 120.0,
    }
    entry.update(overrides)
    return entry


# ---------------------------------------------------------------------------
# What compiles.
# ---------------------------------------------------------------------------


def test_a_position_actuator_compiles_to_the_pd_loop_phase_zero_measured() -> None:
    components, joints, _placements = fx.pendulum()
    built = dyn.build_model(components, joints, actuators=[_servo()])
    model = built["model"]
    assert int(model.nu) == 1
    index = mujoco.mj_name2id(
        model, mujoco.mjtObj.mjOBJ_ACTUATOR, "hinge/position"
    )
    gain = dyn.stiffness_nm_per_rad(4000.0)
    damping = dyn.damping_nms_per_rad(120.0)
    assert float(model.actuator_gainprm[index][0]) == pytest.approx(gain)
    assert list(model.actuator_biasprm[index][:3]) == pytest.approx(
        [0.0, -gain, -damping]
    )
    assert list(model.actuator_gear[index]) == [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    assert bool(model.actuator_ctrllimited[index]) is False
    assert bool(model.actuator_forcelimited[index]) is False


def test_an_effort_limit_compiles_to_a_symmetric_force_range() -> None:
    components, joints, _placements = fx.pendulum()
    built = dyn.build_model(
        components, joints, actuators=[_servo(torque_limit_nmm=8000.0)]
    )
    model = built["model"]
    index = mujoco.mj_name2id(
        model, mujoco.mjtObj.mjOBJ_ACTUATOR, "hinge/position"
    )
    assert bool(model.actuator_forcelimited[index]) is True
    assert list(model.actuator_forcerange[index]) == pytest.approx([-8.0, 8.0])


def test_a_motor_and_a_velocity_actuator_compile_to_their_own_shapes() -> None:
    components, joints, _placements = fx.pendulum()
    motor = dyn.build_model(
        components,
        joints,
        actuators=[
            {
                "joint": "hinge",
                "motion_type": "angular",
                "kind": "motor",
                "control_nmm": "500",
            }
        ],
    )["model"]
    index = mujoco.mj_name2id(motor, mujoco.mjtObj.mjOBJ_ACTUATOR, "hinge/motor")
    assert float(motor.actuator_gainprm[index][0]) == 1.0
    assert list(motor.actuator_biasprm[index][:3]) == [0.0, 0.0, 0.0]

    speed = dyn.build_model(
        components,
        joints,
        actuators=[
            {
                "joint": "hinge",
                "motion_type": "angular",
                "kind": "velocity",
                "control_deg_per_s": "90",
                "damping_nmms_per_deg": 120.0,
            }
        ],
    )["model"]
    index = mujoco.mj_name2id(speed, mujoco.mjtObj.mjOBJ_ACTUATOR, "hinge/velocity")
    damping = dyn.damping_nms_per_rad(120.0)
    assert float(speed.actuator_gainprm[index][0]) == pytest.approx(damping)
    assert list(speed.actuator_biasprm[index][:3]) == pytest.approx(
        [0.0, 0.0, -damping]
    )


def test_a_model_with_no_actuator_still_has_none() -> None:
    """``model.ngeom == 0`` was M2's version of this claim; here it is nu."""

    components, joints, _placements = fx.pendulum()
    assert int(dyn.build_model(components, joints)["model"].nu) == 0


# ---------------------------------------------------------------------------
# What runs.
# ---------------------------------------------------------------------------


def _run(actuators, joint_dynamics=(), *, end_time_s=3.0, fps=60):
    components, joints, _placements = fx.pendulum()
    return dyn.simulate(
        components,
        joints,
        start_time_s=0.0,
        end_time_s=end_time_s,
        frames_per_second=fps,
        actuators=list(actuators),
        joint_dynamics=list(joint_dynamics),
    )


def _hinge_angle(run, frame_index: int) -> float:
    """The arm's own angle, read back off the trace rather than off qpos.

    Which is the number that matters: the trace is what the shell plays, so
    a servo that held ``qpos`` while the trace said otherwise would be a
    working model and a broken product.
    """

    arm = run["frames"][frame_index]["component_placements"]["arm"]
    base = run["frames"][1]["component_placements"]["arm"]
    return dyn.rotation_angle_between(
        dyn.quaternion_wxyz_from_xyzw(arm["rotation_xyzw"]),
        dyn.quaternion_wxyz_from_xyzw(base["rotation_xyzw"]),
    )


def test_a_servo_holds_the_joint_where_it_was_told_to() -> None:
    """The claim M4 exists for, on a fixture, before it is made end to end.

    The pendulum fixture starts at 0.7 rad. Commanded to 30° = 0.5236 rad
    and given a joint to damp against, it goes there and stays.
    """

    run = _run(
        [_servo()],
        [{"joint": "hinge", "motion_type": "angular", "damping_nmms_per_deg": 20.0}],
    )
    # The trace carries poses rather than joint values, so the angle is
    # recovered the way anything downstream would have to: how far the arm
    # turned from the pose the run started in.
    turned = math.degrees(_hinge_angle(run, -1))
    settled = math.degrees(0.7) - turned
    assert settled == pytest.approx(30.0, abs=0.5)
    # The residual is gravity, not noise: the servo is a spring, so holding
    # a load off-centre costs a proportional offset. 0.41° at this gain.
    assert 0.0 < 30.0 - settled < 1.0
    still = _hinge_angle(run, -1) - _hinge_angle(run, -2)
    assert abs(still) < 1.0e-5, "a held arm is not still moving at the end"


def test_the_setpoint_is_degrees_and_a_different_one_lands_elsewhere() -> None:
    """Two runs, one number changed: the arm ends up somewhere else.

    This is the units claim made behaviourally rather than by reading a
    field. If the setpoint were being taken as radians both runs would end
    past a full turn and neither would look wrong on its own.
    """

    damping = [
        {"joint": "hinge", "motion_type": "angular", "damping_nmms_per_deg": 20.0}
    ]
    poses = {}
    for setpoint in ("0", "45"):
        run = _run([_servo(control_deg=setpoint)], damping)
        poses[setpoint] = run["frames"][-1]["component_placements"]["arm"][
            "rotation_xyzw"
        ]
    apart = dyn.rotation_angle_between(
        dyn.quaternion_wxyz_from_xyzw(poses["0"]),
        dyn.quaternion_wxyz_from_xyzw(poses["45"]),
    )
    assert apart == pytest.approx(math.radians(45.0), abs=math.radians(1.0))


def test_a_swept_setpoint_moves_the_arm_through_the_run() -> None:
    """A formula of ``time``, doing what a constant cannot."""

    run = _run(
        [_servo(control_deg="45*sin(2*pi*time)")],
        [{"joint": "hinge", "motion_type": "angular", "damping_nmms_per_deg": 20.0}],
        end_time_s=2.0,
    )
    heights = [
        frame["component_placements"]["arm"]["position_mm"][2]
        for frame in run["frames"][2:]
    ]
    assert max(heights) - min(heights) > 50.0, "the arm has to have swept"


def test_an_effort_limit_that_binds_shows_up_in_the_evidence() -> None:
    """"The arm sagged" with the number that explains it.

    A tenth of a newton-metre cannot hold this arm, so it holds short --
    and the run says which actuator saturated rather than leaving a reader
    to infer it from a pose.
    """

    run = _run(
        [_servo(torque_limit_nmm=100.0)],
        [{"joint": "hinge", "motion_type": "angular", "damping_nmms_per_deg": 20.0}],
    )
    record = run["evidence"]["actuators"][0]
    assert record["effort_limit_si"] == pytest.approx(0.1)
    assert record["peak_effort_si"] == pytest.approx(0.1, rel=1.0e-6)
    assert record["saturated"] is True

    strong = _run(
        [_servo(torque_limit_nmm=100_000.0)],
        [{"joint": "hinge", "motion_type": "angular", "damping_nmms_per_deg": 20.0}],
    )
    assert strong["evidence"]["actuators"][0]["saturated"] is False
    assert 0.0 < strong["evidence"]["actuators"][0]["peak_effort_si"] < 100.0


def test_the_evidence_names_the_motor_and_keeps_the_declared_numbers() -> None:
    run = _run([_servo(torque_limit_nmm=8000.0)])
    record = run["evidence"]["actuators"][0]
    assert record["joint_output"] == "hinge"
    assert record["kind"] == "position"
    assert record["motion_type"] == "angular"
    assert record["mujoco_actuator"] == "hinge/position"
    assert record["stiffness_si"] == pytest.approx(dyn.stiffness_nm_per_rad(4000.0))
    assert record["declared"]["stiffness"] == 4000.0
    assert record["declared"]["effort_limit"] == 8000.0
    # And the whole block survives being written to the artifact, which is
    # what the worker does with it.
    json.dumps(run["evidence"])


def test_per_frame_actuator_state_stays_out_of_the_trace_frames() -> None:
    """The frame schema is why this whole arc needs no shell change.

    ``{frame_index, nominal_time_s, component_placements}`` is what
    ``cadex_animate`` bakes, and a fourth key on a frame is a shell change
    wearing an engine change's clothes. Run-level facts go in the evidence.
    """

    run = _run([_servo()])
    for frame in run["frames"]:
        assert set(frame) == {
            "frame_index",
            "frame_kind",
            "nominal_time_s",
            "component_placements",
        }


# ---------------------------------------------------------------------------
# The one that would have been a prior problem.
# ---------------------------------------------------------------------------


def test_a_zero_motor_does_not_move_a_four_bar_by_one_byte() -> None:
    """Phase 0 measured this on a bare hinge; this is the real mechanism.

    A ``motor`` at zero control adds ``qfrc_actuator`` of exactly nothing,
    so a run with one must be *identical* to a run without -- not close.
    These traces are compared as bytes across processes, and if adding an
    idle actuator moved the answer, the digest story would have a problem
    that had nothing to do with actuators.
    """

    components, joints, _placements = fx.four_bar()

    def _trace(actuators):
        run = dyn.simulate(
            components,
            joints,
            start_time_s=0.0,
            end_time_s=1.0,
            frames_per_second=60,
            actuators=actuators,
        )
        return json.dumps(run["frames"], sort_keys=True)

    idle = [
        {
            "joint": "a",
            "motion_type": "angular",
            "kind": "motor",
            "control_nmm": "0",
        }
    ]
    assert _trace([]) == _trace(idle)


def test_a_motor_with_a_control_does_move_it() -> None:
    """The converse, so the test above cannot pass by doing nothing."""

    components, joints, _placements = fx.four_bar()

    def _crank(control):
        run = dyn.simulate(
            components,
            joints,
            start_time_s=0.0,
            end_time_s=1.0,
            frames_per_second=60,
            actuators=[
                {
                    "joint": "a",
                    "motion_type": "angular",
                    "kind": "motor",
                    "control_nmm": control,
                }
            ],
        )
        return run["frames"][-1]["component_placements"]["crank"]["rotation_xyzw"]

    apart = dyn.rotation_angle_between(
        dyn.quaternion_wxyz_from_xyzw(_crank("0")),
        dyn.quaternion_wxyz_from_xyzw(_crank("2000000")),
    )
    assert apart > math.radians(5.0)


def test_the_control_is_sampled_on_step_boundaries_and_not_on_the_clock() -> None:
    """Two runs at different solver steps agree at the instants they share.

    A control evaluated against an accumulated clock would drift apart with
    the step count; one evaluated at ``start + index · step`` cannot, and
    the two runs land on the same setpoint at the same trace times even
    though one took four times as many steps to get there.
    """

    damping = [
        {"joint": "hinge", "motion_type": "angular", "damping_nmms_per_deg": 60.0}
    ]
    poses = {}
    for step in (0.002, 0.0005):
        components, joints, _placements = fx.pendulum()
        run = dyn.simulate(
            components,
            joints,
            start_time_s=0.0,
            end_time_s=2.0,
            frames_per_second=60,
            time_step_s=step,
            actuators=[_servo(control_deg="20*sin(2*pi*time)")],
            joint_dynamics=damping,
        )
        poses[step] = run["frames"][-1]["component_placements"]["arm"][
            "rotation_xyzw"
        ]
    apart = dyn.rotation_angle_between(
        dyn.quaternion_wxyz_from_xyzw(poses[0.002]),
        dyn.quaternion_wxyz_from_xyzw(poses[0.0005]),
    )
    assert apart < math.radians(1.0)
