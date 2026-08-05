# SPDX-License-Identifier: LGPL-2.1-or-later

"""``api.actuator`` (docs/MUJOCO.md M4, phase 2).

The authoring surface for a motor: which joint, which of three kinds, what
it is told to do, and how hard it may pull. Nothing here runs a model --
these are the refusals, and they are most of the design.

**The unit pairs are the design.** Every quantity whose meaning depends on
whether the joint coordinate turns or slides gets two names, and only the
one matching the joint is accepted. That is more parameter names than a
single ``control=`` plus a ``motion_type`` would need, and that is the
point: ``api.motion``'s one formula whose unit depends on a sibling argument
is precisely hazard 1, and a ``control="30"`` that means 30 radians is a
57x error that runs, looks like physics and errors nowhere.

**The kind decides what the control *is*.** A ``position`` actuator is
commanded in position, a ``velocity`` one in speed and a ``motor`` in
effort, so ``control_deg`` on a motor is not a unit mistake -- it is a claim
about the wrong quantity, and it is refused as one.
"""

from __future__ import annotations

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx
from cadex_assembly_api import AssemblyDomainAPI
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS

mujoco = pytest.importorskip("mujoco")


def _api() -> AssemblyDomainAPI:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return AssemblyDomainAPI(pack.api_exports, pack.output_types)


def _source(name: str) -> dict[str, str]:
    return {"document_uid": "doc", "object_name": name}


def _hinged(api: AssemblyDomainAPI, kind: str = "revolute", **arguments):
    base = api.component(_source("base"), grounded=True)
    part = api.component(_source("part"))
    joint = api.joint(
        kind, api.connector(base), api.connector(part), **arguments
    )
    return base, part, joint, api.assembly([base, part], [joint])


# ---------------------------------------------------------------------------
# The value.
# ---------------------------------------------------------------------------


def test_actuator_is_an_export_and_not_an_output_type() -> None:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    assert "actuator" in pack.api_exports
    assert "actuator" not in pack.output_types
    assert pack.api_exports == AssemblyDomainAPI.exported_names


def test_a_position_servo_on_a_hinge_takes_the_angular_names() -> None:
    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    motor = api.actuator(
        hinge,
        kind="position",
        control_deg="30",
        stiffness_nmm_per_deg=4000.0,
        damping_nmms_per_deg=120.0,
        torque_limit_nmm=8000.0,
    )
    assert motor.output_type == "actuator"
    assert motor.properties["kind"] == "position"
    assert motor.properties["motion_type"] == "angular"
    assert motor.properties["control_deg"] == "30"
    assert motor.properties["stiffness_nmm_per_deg"] == 4000.0
    assert motor.properties["damping_nmms_per_deg"] == 120.0
    assert motor.properties["torque_limit_nmm"] == 8000.0
    assert motor.properties["control_mm"] is None
    assert motor.properties["force_limit_n"] is None


def test_a_position_servo_on_a_slider_takes_the_linear_names() -> None:
    api = _api()
    _base, _part, slide, _asm = _hinged(api, "slider")
    motor = api.actuator(
        slide,
        kind="position",
        control_mm="12.5",
        stiffness_n_per_mm=500.0,
        force_limit_n=200.0,
    )
    assert motor.properties["motion_type"] == "linear"
    assert motor.properties["control_mm"] == "12.5"
    assert motor.properties["stiffness_n_per_mm"] == 500.0
    assert motor.properties["force_limit_n"] == 200.0


def test_the_three_kinds_take_three_different_controls() -> None:
    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    torque = api.actuator(hinge, kind="motor", control_nmm="500")
    speed = api.actuator(
        hinge, kind="velocity", control_deg_per_s="90", damping_nmms_per_deg=120.0
    )
    place = api.actuator(
        hinge, kind="position", control_deg="30", stiffness_nmm_per_deg=4000.0
    )
    assert torque.properties["control_nmm"] == "500"
    assert speed.properties["control_deg_per_s"] == "90"
    assert place.properties["control_deg"] == "30"


def test_the_control_may_be_a_formula_of_time() -> None:
    """The whole reason there is no control callback."""

    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    motor = api.actuator(
        hinge,
        control_deg="30*sin(2*pi*time) + 15",
        stiffness_nmm_per_deg=4000.0,
    )
    assert motor.properties["control_deg"] == "30*sin(2*pi*time) + 15"


def test_a_power_may_be_written_either_way_and_arrives_as_python() -> None:
    """``api.motion`` renders back to Ondsel's ``^``; a control does not.

    Both surfaces share one whitelist and differ in what they emit, because
    the kinematics formula is evaluated by OndselSolver and this one is
    evaluated by us.
    """

    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    motor = api.actuator(
        hinge, control_deg="time^2", stiffness_nmm_per_deg=4000.0
    )
    assert motor.properties["control_deg"] == "time**2"
    assert api.motion(hinge, "time**2").properties["formula"] == "time^2"


# ---------------------------------------------------------------------------
# The refusals.
# ---------------------------------------------------------------------------


def test_the_wrong_unit_of_a_pair_is_refused_and_names_the_right_one() -> None:
    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    with pytest.raises(ValueError) as excinfo:
        api.actuator(hinge, control_deg="30", stiffness_n_per_mm=500.0)
    assert "stiffness_nmm_per_deg" in str(excinfo.value)
    with pytest.raises(ValueError) as excinfo:
        api.actuator(
            hinge,
            control_deg="30",
            stiffness_nmm_per_deg=4000.0,
            force_limit_n=200.0,
        )
    assert "torque_limit_nmm" in str(excinfo.value)


def test_a_command_range_is_accepted_in_both_spellings() -> None:
    """``[min, max]`` and ``{"minimum": …}``, like every other limit here."""

    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    for spelling in ([-25.0, 25.0], {"minimum": -25.0, "maximum": 25.0}):
        value = api.actuator(
            hinge,
            control_deg="30",
            stiffness_nmm_per_deg=4000.0,
            command_limits_degrees=spelling,
        )
        # A DomainValue freezes sequences on the way in, so this comes back
        # as a tuple whichever spelling produced it.
        assert value.properties["command_limits_degrees"] == (-25.0, 25.0)
        assert value.properties["command_limits_mm"] is None


def test_an_actuator_without_a_command_range_declares_none() -> None:
    """The default changes nothing for anyone who does not ask."""

    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    value = api.actuator(
        hinge, control_deg="30", stiffness_nmm_per_deg=4000.0
    )
    assert value.properties["command_limits_degrees"] is None
    assert value.properties["command_limits_mm"] is None


def test_a_command_range_in_the_wrong_unit_is_refused() -> None:
    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    with pytest.raises(ValueError) as excinfo:
        api.actuator(
            hinge,
            control_deg="30",
            stiffness_nmm_per_deg=4000.0,
            command_limits_mm=[-25.0, 25.0],
        )
    assert "command_limits_degrees" in str(excinfo.value)


def test_a_command_range_on_a_motor_is_refused() -> None:
    """Only a position servo derives its range from travel, so only it has
    travel to narrow. A motor is bounded by its effort limit."""

    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    with pytest.raises(ValueError) as excinfo:
        api.actuator(
            hinge,
            kind="motor",
            control_nmm="100",
            torque_limit_nmm=8000.0,
            command_limits_degrees=[-25.0, 25.0],
        )
    assert "position" in str(excinfo.value)


def test_a_half_stated_or_empty_command_range_is_refused() -> None:
    """One endpoint would have to mean "and the joint's own for the other",
    which is a second, quieter spelling of something already sayable."""

    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    for bad in ([None, 25.0], [-25.0, None]):
        with pytest.raises(ValueError) as excinfo:
            api.actuator(
                hinge,
                control_deg="30",
                stiffness_nmm_per_deg=4000.0,
                command_limits_degrees=bad,
            )
        assert "both endpoints" in str(excinfo.value)
    with pytest.raises(ValueError) as excinfo:
        api.actuator(
            hinge,
            control_deg="30",
            stiffness_nmm_per_deg=4000.0,
            command_limits_degrees=[25.0, 25.0],
        )
    assert "zero width" in str(excinfo.value)
    # Inverted is caught by the shared limit parser, before width.
    with pytest.raises(ValueError) as excinfo:
        api.actuator(
            hinge,
            control_deg="30",
            stiffness_nmm_per_deg=4000.0,
            command_limits_degrees=[25.0, -25.0],
        )
    assert "minimum must not exceed maximum" in str(excinfo.value)


def test_a_control_in_the_wrong_unit_is_refused_before_it_can_run() -> None:
    """The 57x error, refused at the parameter name rather than at 30 radians."""

    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    with pytest.raises(ValueError) as excinfo:
        api.actuator(hinge, control_mm="30", stiffness_nmm_per_deg=4000.0)
    assert "control_deg" in str(excinfo.value)


def test_a_control_meant_for_another_kind_is_refused() -> None:
    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    with pytest.raises(ValueError) as excinfo:
        api.actuator(hinge, kind="motor", control_deg="30")
    assert "control_nmm" in str(excinfo.value)
    with pytest.raises(ValueError) as excinfo:
        api.actuator(
            hinge,
            kind="velocity",
            control_deg="30",
            damping_nmms_per_deg=120.0,
        )
    assert "control_deg_per_s" in str(excinfo.value)


def test_a_position_servo_without_a_gain_is_refused() -> None:
    """There is no defensible default: too little sags, too much diverges."""

    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    with pytest.raises(ValueError) as excinfo:
        api.actuator(hinge, control_deg="30")
    assert "stiffness_nmm_per_deg" in str(excinfo.value)


def test_a_velocity_actuator_without_its_gain_is_refused() -> None:
    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    with pytest.raises(ValueError) as excinfo:
        api.actuator(hinge, kind="velocity", control_deg_per_s="90")
    assert "is the gain" in str(excinfo.value)


def test_a_motor_has_no_gains_at_all() -> None:
    """It is the one kind with no loop, so a gain on it means nothing."""

    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    with pytest.raises(ValueError) as excinfo:
        api.actuator(
            hinge, kind="motor", control_nmm="500", stiffness_nmm_per_deg=4000.0
        )
    assert "only a position servo" in str(excinfo.value)
    with pytest.raises(ValueError) as excinfo:
        api.actuator(
            hinge, kind="motor", control_nmm="500", damping_nmms_per_deg=120.0
        )
    assert "api.joint_dynamics" in str(excinfo.value)


def test_initialvalue_is_refused_with_the_reason() -> None:
    """``api.motion`` has it and a control formula must not.

    A kinematics run starts from a joint value the solver was handed; a
    dynamics run starts from a solved *pose*, which is not a scalar the
    script can name. Silently accepting the name and evaluating it as
    something would be inventing a number.
    """

    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    with pytest.raises(ValueError) as excinfo:
        api.actuator(
            hinge, control_deg="initialValue + 10", stiffness_nmm_per_deg=4000.0
        )
    assert "solved pose" in str(excinfo.value)
    # And the kinematics surface still accepts it, unchanged.
    assert api.motion(hinge, "initialValue + 10").properties["formula"]


@pytest.mark.parametrize(
    "formula",
    [
        "__import__('os').system('true')",
        "time if time else 0",
        "[time]",
        "open('x')",
        "time.real",
        "max(time, 1)",
        "lambda: 1",
    ],
)
def test_the_control_whitelist_refuses_everything_that_is_not_arithmetic(
    formula: str,
) -> None:
    """An AST whitelist, not a sandbox: what is allowed is enumerated.

    This is the same validator ``api.motion`` has always used, extracted so
    the two cannot drift. A Python release growing a new expression node
    adds nothing to what is accepted here.
    """

    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    with pytest.raises(ValueError):
        api.actuator(hinge, control_deg=formula, stiffness_nmm_per_deg=4000.0)


def test_a_bare_number_is_refused_with_the_quoted_form() -> None:
    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    with pytest.raises(ValueError) as excinfo:
        api.actuator(hinge, control_deg=30, stiffness_nmm_per_deg=4000.0)
    assert '"30"' in str(excinfo.value)


@pytest.mark.parametrize(
    "kind, expected",
    [
        ("screw", "attaches nothing"),
        ("gears", "attaches nothing"),
        ("fixed", "no coordinate"),
        ("ball", "three coordinates"),
        ("parallel", "placement constraint"),
    ],
)
def test_a_joint_with_no_scalar_coordinate_cannot_be_driven(
    kind: str, expected: str
) -> None:
    api = _api()
    arguments = {
        "screw": {"thread_pitch_mm": 4.0},
        "gears": {"radius1_mm": 20.0, "radius2_mm": 10.0},
    }.get(kind, {})
    _base, _part, joint, _asm = _hinged(api, kind, **arguments)
    with pytest.raises(ValueError) as excinfo:
        api.actuator(joint, control_deg="30", stiffness_nmm_per_deg=4000.0)
    assert expected in str(excinfo.value)


def test_a_suppressed_joint_cannot_be_driven() -> None:
    api = _api()
    _base, _part, hinge, _asm = _hinged(api, suppressed=True)
    with pytest.raises(ValueError) as excinfo:
        api.actuator(hinge, control_deg="30", stiffness_nmm_per_deg=4000.0)
    assert "suppressed" in str(excinfo.value)


def test_a_cylindrical_joint_must_say_which_coordinate_is_driven() -> None:
    api = _api()
    _base, _part, cylinder, _asm = _hinged(api, "cylindrical")
    with pytest.raises(ValueError) as excinfo:
        api.actuator(cylinder, control_deg="30", stiffness_nmm_per_deg=4000.0)
    assert "explicit" in str(excinfo.value)
    turning = api.actuator(
        cylinder,
        motion_type="angular",
        control_deg="30",
        stiffness_nmm_per_deg=4000.0,
    )
    sliding = api.actuator(
        cylinder,
        motion_type="linear",
        control_mm="12",
        stiffness_n_per_mm=500.0,
    )
    assert turning.properties["motion_type"] == "angular"
    assert sliding.properties["motion_type"] == "linear"


def test_two_motors_on_one_coordinate_are_refused() -> None:
    api = _api()
    base, part, hinge, asm = _hinged(api)
    bodies = [
        api.body(base, density_kg_m3=7850.0),
        api.body(part, density_kg_m3=2700.0),
    ]
    motors = [
        api.actuator(hinge, control_deg="30", stiffness_nmm_per_deg=4000.0),
        api.actuator(hinge, control_deg="40", stiffness_nmm_per_deg=4000.0),
    ]
    with pytest.raises(ValueError) as excinfo:
        api.dynamics(asm, bodies, actuators=motors)
    assert "two motors" in str(excinfo.value)


def test_a_motor_on_a_joint_from_another_assembly_is_refused() -> None:
    api = _api()
    base, part, _hinge, asm = _hinged(api)
    other_base = api.component(_source("other_base"), grounded=True)
    other_part = api.component(_source("other_part"))
    stranger = api.joint(
        "revolute", api.connector(other_base), api.connector(other_part)
    )
    bodies = [
        api.body(base, density_kg_m3=7850.0),
        api.body(part, density_kg_m3=2700.0),
    ]
    with pytest.raises(ValueError) as excinfo:
        api.dynamics(
            asm,
            bodies,
            actuators=[
                api.actuator(
                    stranger, control_deg="30", stiffness_nmm_per_deg=4000.0
                )
            ],
        )
    assert "not listed in this assembly" in str(excinfo.value)


def test_a_negative_or_zero_gain_is_refused() -> None:
    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    for gain in (0.0, -1.0):
        with pytest.raises(ValueError):
            api.actuator(hinge, control_deg="30", stiffness_nmm_per_deg=gain)
    with pytest.raises(ValueError):
        api.actuator(
            hinge,
            control_deg="30",
            stiffness_nmm_per_deg=4000.0,
            torque_limit_nmm=0.0,
        )


def test_an_unknown_kind_lists_the_three_that_exist() -> None:
    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    with pytest.raises(ValueError) as excinfo:
        api.actuator(hinge, kind="muscle", control_deg="30")
    assert "'motor', 'position', 'velocity'" in str(excinfo.value)


# ---------------------------------------------------------------------------
# The records the pure module builds from them.
# ---------------------------------------------------------------------------


def _pendulum_actuator(**overrides):
    entry = {
        "joint": "hinge",
        "motion_type": "angular",
        "kind": "position",
        "control_deg": "30",
        "stiffness_nmm_per_deg": 4000.0,
        "damping_nmms_per_deg": 120.0,
        "torque_limit_nmm": 8000.0,
    }
    entry.update(overrides)
    return entry


def test_the_gains_arrive_in_si_exactly_once() -> None:
    """The M2 split rule holding through a second slice.

    Everything numeric here happened in the pure module: the worker
    forwarded a property dict off the graph and touched no number in it,
    because there is nothing to read out of FreeCAD for an actuator.
    """

    components, joints, _placements = fx.pendulum()
    built = dyn.build_model(components, joints, actuators=[_pendulum_actuator()])
    record = built["actuators"][0]
    assert record["stiffness_si"] == pytest.approx(dyn.stiffness_nm_per_rad(4000.0))
    assert record["damping_si"] == pytest.approx(dyn.damping_nms_per_rad(120.0))
    assert record["effort_limit_si"] == pytest.approx(8.0)
    assert record["declared"] == {
        "control": "30",
        "stiffness": 4000.0,
        "damping": 120.0,
        "effort_limit": 8000.0,
        # Absent unless the script narrows the action range, and carried in
        # the surface unit like everything else here.
        "command_limits": None,
    }
    assert record["mujoco_joint"] == "hinge"
    assert record["mujoco_actuator"] == "hinge/position"


def test_a_linear_actuators_gains_go_the_other_way() -> None:
    components, joints, _placements = fx.build(
        [
            {"name": "base", "grounded": True, "size": (200.0, 200.0, 20.0)},
            {"name": "ram", "size": (60.0, 60.0, 200.0)},
        ],
        [
            {
                "name": "slide",
                "kind": "slider",
                "parent": "base",
                "child": "ram",
                "parent_frame": fx.frame((0.0, 0.0, 10.0)),
                "child_frame": fx.frame((0.0, 0.0, 0.0)),
                "values": [0.05],
            }
        ],
    )
    built = dyn.build_model(
        components,
        joints,
        actuators=[
            {
                "joint": "slide",
                "motion_type": "linear",
                "kind": "position",
                "control_mm": "50",
                "stiffness_n_per_mm": 500.0,
                "force_limit_n": 200.0,
            }
        ],
    )
    record = built["actuators"][0]
    assert record["stiffness_si"] == pytest.approx(500_000.0)
    assert record["effort_limit_si"] == pytest.approx(200.0)


def test_a_loop_closing_joint_cannot_be_driven_and_says_why() -> None:
    components, joints, _placements = fx.four_bar()
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(
            components,
            joints,
            actuators=[_pendulum_actuator(joint="c")],
        )
    assert excinfo.value.reason == "joint_has_no_coordinate"
    assert "closes a loop" in str(excinfo.value)
    assert "reorder the joints" in str(excinfo.value)


def test_a_gain_the_solver_step_cannot_carry_names_the_step_it_would_take() -> None:
    """M3's restitution refusal, in the actuator's own units.

    ``ω·h`` past 2 is where an undamped position gain diverges -- measured,
    not cited -- and the refusal has to carry the step, because "too stiff"
    on its own is advice nobody can act on.
    """

    components, joints, _placements = fx.pendulum()
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(
            components,
            joints,
            actuators=[_pendulum_actuator(stiffness_nmm_per_deg=1.0e8)],
            time_step_s=dyn.DEFAULT_TIME_STEP_S,
        )
    assert excinfo.value.reason == "actuator_gain_needs_a_finer_step"
    required = float(excinfo.value.observed["required_step_s"])
    assert 0.0 < required < dyn.DEFAULT_TIME_STEP_S
    assert "armature" in excinfo.value.correction
    # And the same gain at the step the refusal names is accepted.
    dyn.build_model(
        components,
        joints,
        actuators=[_pendulum_actuator(stiffness_nmm_per_deg=1.0e8)],
        time_step_s=required * 0.99,
    )


def test_an_armature_buys_the_stiffer_gain_the_refusal_offered() -> None:
    """Which is what makes that sentence advice rather than consolation."""

    components, joints, _placements = fx.pendulum()
    actuators = [_pendulum_actuator(stiffness_nmm_per_deg=1.0e8)]
    with pytest.raises(dyn.DynamicsError):
        dyn.build_model(components, joints, actuators=actuators)
    dyn.build_model(
        components,
        joints,
        actuators=actuators,
        joint_dynamics=[
            {"joint": "hinge", "motion_type": "angular", "armature_kgmm2": 1.0e7}
        ],
    )


def test_two_records_on_one_coordinate_are_refused_by_the_pure_module() -> None:
    components, joints, _placements = fx.pendulum()
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(
            components,
            joints,
            actuators=[_pendulum_actuator(), _pendulum_actuator()],
        )
    assert excinfo.value.reason == "duplicate_actuator"
