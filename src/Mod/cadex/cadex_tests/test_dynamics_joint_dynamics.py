# SPDX-License-Identifier: LGPL-2.1-or-later

"""``api.joint_dynamics`` (docs/MUJOCO.md M4, phase 1).

MuJoCo's defaults for damping, armature and friction loss are all **zero**,
which describes a joint that exists nowhere: frictionless, undamped, and
with no rotor inertia on the far side of a gearbox. That is fine for a
mechanism falling under gravity -- M2 and M3 both ran on it -- and it stops
being fine the moment a motor holds something. Measured in phase 0: a
position gain stiff enough to hold this arm rings on an undamped joint at
sixty degrees peak to peak and does not decay.

So the second of M4's two corrections to its own plan: joint damping and
armature are *part of this slice*, and they are a declared intermediate
rather than a tuning secret, for the same reason density is required and
never defaulted. A gain that only behaves because of an undeclared default
is the failure class M2 and M3 were each organised against.

Every quantity here is one of a **suffixed pair**, and only the one matching
the joint's coordinate is accepted. That verbosity is hazard 1 answered in
the parameter names: a single ``damping=`` whose unit depended on the
joint's kind would read the same number as 4000 N·mm·s/deg and 4000 N·s/mm,
which differ by a factor of five and a half million.
"""

from __future__ import annotations

import math

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
    """A grounded base and one part, joined once, in the shape a script has."""

    base = api.component(_source("base"), grounded=True)
    part = api.component(_source("part"))
    joint = api.joint(
        kind,
        api.connector(base),
        api.connector(part),
        **arguments,
    )
    return base, part, joint, api.assembly([base, part], [joint])


# ---------------------------------------------------------------------------
# The value, and the pack that carries it.
# ---------------------------------------------------------------------------


def test_joint_dynamics_is_an_export_and_not_an_output_type() -> None:
    """The same mechanism ``collision`` uses: exported, unpublishable.

    A joint's damping is a fact about a joint, not a result a script
    declares. Being in ``api_exports`` and absent from ``output_types`` is
    what makes returning one a contract error rather than a silent
    publication of something with no native type behind it.
    """

    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    assert "joint_dynamics" in pack.api_exports
    assert "joint_dynamics" not in pack.output_types
    assert pack.api_exports == AssemblyDomainAPI.exported_names


def test_a_revolute_joint_takes_the_angular_names() -> None:
    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    value = api.joint_dynamics(
        hinge,
        damping_nmms_per_deg=0.02,
        armature_kgmm2=50.0,
        friction_loss_nmm=3.0,
    )
    assert value.output_type == "joint_dynamics"
    assert value.properties["motion_type"] == "angular"
    assert value.properties["damping_nmms_per_deg"] == 0.02
    assert value.properties["armature_kgmm2"] == 50.0
    assert value.properties["friction_loss_nmm"] == 3.0
    # The linear halves of each pair stay present and empty, so the seam
    # carries which unit was meant rather than only the number.
    assert value.properties["damping_ns_per_mm"] is None
    assert value.properties["armature_kg"] is None
    assert value.properties["friction_loss_n"] is None


def test_a_slider_takes_the_linear_names() -> None:
    api = _api()
    _base, _part, slide, _asm = _hinged(api, "slider")
    value = api.joint_dynamics(
        slide, damping_ns_per_mm=0.5, armature_kg=0.2, friction_loss_n=1.5
    )
    assert value.properties["motion_type"] == "linear"
    assert value.properties["damping_ns_per_mm"] == 0.5
    assert value.properties["armature_kg"] == 0.2
    assert value.properties["friction_loss_n"] == 1.5


# ---------------------------------------------------------------------------
# The refusals, which are the point.
# ---------------------------------------------------------------------------


def test_the_wrong_unit_of_a_pair_is_refused_and_names_the_right_one() -> None:
    """A factor of 5.5 million, turned into a sentence.

    ``damping_ns_per_mm`` on a hinge is not a number that needs scaling; it
    is a category error, and the only safe thing to do with one is refuse
    it. The refusal names the parameter that was meant, because an author
    who reached for the wrong suffix does not know there is a right one.
    """

    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    with pytest.raises(ValueError) as excinfo:
        api.joint_dynamics(hinge, damping_ns_per_mm=0.5)
    assert "damping_nmms_per_deg" in str(excinfo.value)
    _base2, _part2, slide, _asm2 = _hinged(api, "slider")
    with pytest.raises(ValueError) as excinfo:
        api.joint_dynamics(slide, armature_kgmm2=50.0)
    assert "armature_kg" in str(excinfo.value)


def test_a_cylindrical_joint_needs_to_say_which_coordinate() -> None:
    """Two coordinates, one of each kind: exactly ``api.motion``'s rule.

    Guessing would mean picking one of two units by default on the one
    joint where the surface cannot tell them apart, which is the shape of
    hazard 1 rather than a convenience.
    """

    api = _api()
    _base, _part, cylinder, _asm = _hinged(api, "cylindrical")
    with pytest.raises(ValueError) as excinfo:
        api.joint_dynamics(cylinder, damping_nmms_per_deg=0.02)
    assert "explicit" in str(excinfo.value)
    angular = api.joint_dynamics(
        cylinder, motion_type="angular", damping_nmms_per_deg=0.02
    )
    linear = api.joint_dynamics(
        cylinder, motion_type="linear", damping_ns_per_mm=0.5
    )
    assert angular.properties["motion_type"] == "angular"
    assert linear.properties["motion_type"] == "linear"


@pytest.mark.parametrize(
    "kind, expected",
    [
        ("screw", "attaches nothing"),
        ("gears", "attaches nothing"),
        ("belt", "attaches nothing"),
        ("rack_pinion", "attaches nothing"),
        ("fixed", "no coordinate"),
        ("ball", "three coordinates"),
        ("distance", "placement constraint"),
        ("parallel", "placement constraint"),
        ("perpendicular", "placement constraint"),
        ("angle", "placement constraint"),
    ],
)
def test_every_joint_without_a_scalar_coordinate_is_refused(
    kind: str, expected: str
) -> None:
    """Ten kinds, ten reasons, none of them "unsupported"."""

    api = _api()
    arguments = {
        "screw": {"thread_pitch_mm": 4.0},
        "gears": {"radius1_mm": 20.0, "radius2_mm": 10.0},
        "belt": {"radius1_mm": 20.0, "radius2_mm": 10.0},
        "rack_pinion": {"pitch_radius_mm": 12.0},
        "distance": {"distance_mm": 30.0},
        "angle": {"angle_degrees": 30.0},
    }.get(kind, {})
    _base, _part, joint, _asm = _hinged(api, kind, **arguments)
    with pytest.raises(ValueError) as excinfo:
        api.joint_dynamics(joint, damping_nmms_per_deg=0.02)
    assert expected in str(excinfo.value)


def test_a_coupled_joint_says_which_joint_to_configure_instead() -> None:
    """The `rack_pinion` precedent: a refusal that only says no is half done."""

    api = _api()
    _base, _part, screw, _asm = _hinged(api, "screw", thread_pitch_mm=4.0)
    with pytest.raises(ValueError) as excinfo:
        api.joint_dynamics(screw, damping_nmms_per_deg=0.02)
    assert "the slider and the revolute joint it relates" in str(excinfo.value)


def test_a_suppressed_joint_is_refused() -> None:
    api = _api()
    _base, _part, hinge, _asm = _hinged(api, suppressed=True)
    with pytest.raises(ValueError) as excinfo:
        api.joint_dynamics(hinge, damping_nmms_per_deg=0.02)
    assert "suppressed" in str(excinfo.value)


def test_an_empty_joint_dynamics_is_refused() -> None:
    """It reads like a joint that was configured and is a joint that was not."""

    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    with pytest.raises(ValueError) as excinfo:
        api.joint_dynamics(hinge)
    assert "declares nothing" in str(excinfo.value)


def test_negative_resistance_is_refused() -> None:
    """Negative damping is an energy source, and it looks like a number."""

    api = _api()
    _base, _part, hinge, _asm = _hinged(api)
    for name in ("damping_nmms_per_deg", "armature_kgmm2", "friction_loss_nmm"):
        with pytest.raises(ValueError):
            api.joint_dynamics(hinge, **{name: -1.0})


def test_two_declarations_on_one_coordinate_are_refused_by_dynamics() -> None:
    api = _api()
    base, part, hinge, asm = _hinged(api)
    first = api.joint_dynamics(hinge, damping_nmms_per_deg=0.02)
    second = api.joint_dynamics(hinge, armature_kgmm2=50.0)
    bodies = [
        api.body(base, density_kg_m3=7850.0),
        api.body(part, density_kg_m3=2700.0),
    ]
    with pytest.raises(ValueError) as excinfo:
        api.dynamics(asm, bodies, joint_dynamics=[first, second])
    assert "two sets of damping" in str(excinfo.value)


def test_a_cylindrical_joints_two_coordinates_are_separate_declarations() -> None:
    """The converse of the test above, and the reason it keys on coordinates."""

    api = _api()
    base, part, cylinder, asm = _hinged(api, "cylindrical")
    bodies = [
        api.body(base, density_kg_m3=7850.0),
        api.body(part, density_kg_m3=2700.0),
    ]
    run = api.dynamics(
        asm,
        bodies,
        joint_dynamics=[
            api.joint_dynamics(
                cylinder, motion_type="angular", damping_nmms_per_deg=0.02
            ),
            api.joint_dynamics(
                cylinder, motion_type="linear", damping_ns_per_mm=0.5
            ),
        ],
    )
    assert len(run.properties["joint_dynamics"]) == 2


def test_a_joint_from_another_assembly_is_refused() -> None:
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
            joint_dynamics=[api.joint_dynamics(stranger, damping_nmms_per_deg=0.02)],
        )
    assert "not listed in this assembly" in str(excinfo.value)


# ---------------------------------------------------------------------------
# The model, and the conversions reaching it.
# ---------------------------------------------------------------------------


def _pendulum_with(joint_dynamics):
    components, joints, _placements = fx.pendulum()
    return dyn.build_model(components, joints, joint_dynamics=joint_dynamics)


def test_the_declared_numbers_arrive_in_si_on_the_compiled_model() -> None:
    """The end of the units boundary: what the script said, in what MuJoCo has.

    0.02 N·mm·s/deg is 1.146e-3 N·m·s/rad and 50 kg·mm² is 5e-5 kg·m². Both
    are checked on the *compiled* model rather than on the spec, which is
    where a MuJoCo release changing what a field means would land.
    """

    built = _pendulum_with(
        [
            {
                "joint": "hinge",
                "motion_type": "angular",
                "damping_nmms_per_deg": 0.02,
                "armature_kgmm2": 50.0,
                "friction_loss_nmm": 3.0,
            }
        ]
    )
    model = built["model"]
    index = int(
        model.jnt_dofadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "hinge")]
    )
    assert float(model.dof_damping[index]) == pytest.approx(
        dyn.damping_nms_per_rad(0.02), rel=1.0e-12
    )
    assert float(model.dof_armature[index]) == pytest.approx(5.0e-5, rel=1.0e-12)
    assert float(model.dof_frictionloss[index]) == pytest.approx(
        dyn.torque_nm(3.0), rel=1.0e-12
    )


def test_a_joint_nobody_configured_keeps_mujocos_zeros() -> None:
    """Which is what makes this slice free for every mechanism before it."""

    built = _pendulum_with([])
    model = built["model"]
    index = int(
        model.jnt_dofadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "hinge")]
    )
    assert float(model.dof_damping[index]) == 0.0
    assert float(model.dof_armature[index]) == 0.0
    assert float(model.dof_frictionloss[index]) == 0.0
    assert built["joint_dynamics"] == []


def test_damping_actually_stops_the_arm_and_the_evidence_says_by_how_much() -> None:
    """The claim in physics rather than in field values.

    An undamped pendulum released horizontally still swings after four
    seconds; a damped one has stopped. Both runs are the same fixture and
    the same gravity, so the difference is the one number that changed.
    """

    components, joints, _placements = fx.pendulum()
    swings = {}
    for damping in (0.0, 20.0):
        entries = (
            []
            if damping == 0.0
            else [
                {
                    "joint": "hinge",
                    "motion_type": "angular",
                    "damping_nmms_per_deg": damping,
                }
            ]
        )
        run = dyn.simulate(
            components,
            joints,
            start_time_s=0.0,
            end_time_s=4.0,
            frames_per_second=30,
            joint_dynamics=entries,
        )
        heights = [
            frame["component_placements"]["arm"]["position_mm"][2]
            for frame in run["frames"][-30:]
        ]
        swings[damping] = max(heights) - min(heights)
    assert swings[0.0] > 20.0, "an undamped pendulum is still swinging"
    assert swings[20.0] < 0.5, "a damped one has stopped"


def test_the_evidence_carries_both_the_declared_and_the_si_numbers() -> None:
    components, joints, _placements = fx.pendulum()
    built = dyn.build_model(
        components,
        joints,
        joint_dynamics=[
            {
                "joint": "hinge",
                "motion_type": "angular",
                "damping_nmms_per_deg": 0.02,
                "armature_kgmm2": 50.0,
            }
        ],
    )
    entry = dyn.model_evidence(built, components)["joint_dynamics"][0]
    assert entry["joint_output"] == "hinge"
    assert entry["motion_type"] == "angular"
    assert entry["mujoco_joint"] == "hinge"
    assert entry["declared"]["damping"] == 0.02
    assert entry["declared"]["armature"] == 50.0
    assert entry["armature_si"] == pytest.approx(5.0e-5)


def test_a_joint_that_became_a_loop_closure_is_refused_by_name() -> None:
    """The refusal the API cannot make, because only the tree knows.

    ``api.joint_dynamics`` can see that a joint is a revolute one; it cannot
    see that the spanning forest reached both its components another way and
    turned it into an equality constraint. So the pure module refuses it,
    and says what would change it.
    """

    components, joints, _placements = fx.four_bar()
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(
            components,
            joints,
            joint_dynamics=[
                {
                    "joint": "c",
                    "motion_type": "angular",
                    "damping_nmms_per_deg": 0.02,
                }
            ],
        )
    assert excinfo.value.reason == "joint_has_no_coordinate"
    assert "closes a loop" in str(excinfo.value)


def test_a_joint_that_is_not_in_the_assembly_is_refused_by_the_pure_module() -> None:
    components, joints, _placements = fx.pendulum()
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(
            components,
            joints,
            joint_dynamics=[
                {
                    "joint": "elsewhere",
                    "motion_type": "angular",
                    "damping_nmms_per_deg": 0.02,
                }
            ],
        )
    assert excinfo.value.reason == "joint_not_in_assembly"


def test_asking_a_revolute_joint_for_its_linear_coordinate_is_refused() -> None:
    components, joints, _placements = fx.pendulum()
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(
            components,
            joints,
            joint_dynamics=[
                {
                    "joint": "hinge",
                    "motion_type": "linear",
                    "damping_ns_per_mm": 0.5,
                }
            ],
        )
    assert "owns only angular" in str(excinfo.value)


def test_damping_the_solver_cannot_resolve_is_refused_with_the_rate() -> None:
    """Phase 0's silent failure, in front of a sentence.

    Past ``c / M ≈ 1.2e10`` per second MuJoCo stops the joint instead of
    damping it and reports nothing. The refusal is stated as the rate
    because that is the invariant -- measured across four decades of
    inertia -- and it names the armature as the other way to get what an
    author asking for that much damping usually wants.
    """

    components, joints, _placements = fx.pendulum()
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(
            components,
            joints,
            joint_dynamics=[
                {
                    "joint": "hinge",
                    "motion_type": "angular",
                    "damping_nmms_per_deg": 1.0e9,
                }
            ],
        )
    assert excinfo.value.reason == "damping_rate_too_high"
    assert "armature" in excinfo.value.correction
    assert excinfo.value.observed["rate_per_s"] > dyn.MAXIMUM_DAMPING_RATE_PER_S


def test_armature_raises_the_inertia_the_joint_actually_carries() -> None:
    """Which is the other half of what armature is for, and it is measurable.

    A rotor's inertia is on the joint, not on the link, so it shows up in
    the mass matrix rather than in ``body_inertia`` -- and it is what lets a
    stiffer gain run at the same solver step.
    """

    components, joints, _placements = fx.pendulum()
    bare = dyn.build_model(components, joints)
    heavy = dyn.build_model(
        components,
        joints,
        joint_dynamics=[
            {"joint": "hinge", "motion_type": "angular", "armature_kgmm2": 1.0e6}
        ],
    )
    index = 0
    bare_inertia = dyn._dof_inertia(mujoco, bare["model"], bare["qpos_solved"])[index]
    heavy_inertia = dyn._dof_inertia(mujoco, heavy["model"], heavy["qpos_solved"])[
        index
    ]
    assert heavy_inertia - bare_inertia == pytest.approx(
        dyn.armature_kg_m2(1.0e6), rel=1.0e-9
    )
    assert float(heavy["model"].body_inertia[1][0]) == pytest.approx(
        float(bare["model"].body_inertia[1][0])
    ), "an armature is not part of the link, and must not touch its inertia"
