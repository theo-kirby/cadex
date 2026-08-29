# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``assembly.mjcf`` on the script surface (docs/MUJOCO.md M5, phase 2).

One new publishable output type and one new export, and the interesting
decisions are the two that differ from ``api.dynamics``:

* **``mjcf`` is its own output type**, where ``dynamics`` deliberately
  shares ``simulation``. The reason ``dynamics`` shares is that
  ``cadex_animate`` bakes exactly one ``assembly_simulation_json`` and
  silently bakes *neither* when it finds two. Nothing bakes an MJCF file,
  so the "exactly one" rule has nothing to protect here -- and a script
  that wants two exported models is a reasonable script.
* **Every validation it shares with ``api.dynamics`` is the same code**,
  not a copy. Two copies of the "steel is 7850" refusal is two places for
  it to drift, so both surfaces run ``_mujoco_model`` and this file asserts
  they refuse identically rather than asserting each refusal twice.

What ``api.mjcf`` does *not* take is everything that counts a trace --
``start_time_s``, ``end_time_s``, ``frames_per_second`` and the frame and
pose caps -- because nothing is integrated and those numbers would be
meaningless.
"""

from __future__ import annotations

import inspect

import pytest

from cadex_assembly_api import AssemblyDomainAPI, _PUBLISHABLE_TYPES
from cadex_domain_api import _DOMAIN_OPERATION_OUTPUT_TYPES
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from CadexScriptedDomainPublication import _NATIVE_TYPE_BY_OUTPUT


def _api() -> AssemblyDomainAPI:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return AssemblyDomainAPI(pack.api_exports, pack.output_types)


def _source(name: str) -> dict[str, str]:
    return {"document_uid": "doc", "object_name": name}


def _assembly(api, count: int = 2):
    components = [
        api.component(_source(f"solid{index}"), grounded=index == 0)
        for index in range(count)
    ]
    joints = [
        api.joint(
            "revolute",
            api.connector(components[index], "origin"),
            api.connector(components[index + 1], "origin"),
        )
        for index in range(count - 1)
    ]
    return api.assembly(components, joints), components, joints


def _bodies(api, components):
    return [api.body(component, density_kg_m3=7850) for component in components]


# ---------------------------------------------------------------------------
# Registration: the four places the constructors cross-check each other.
# ---------------------------------------------------------------------------


def test_the_pack_and_the_api_agree_about_mjcf() -> None:
    """``AssemblyDomainAPI.__init__`` refuses to start if these disagree."""

    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    assert pack.api_exports == AssemblyDomainAPI.exported_names
    assert "mjcf" in pack.api_exports
    assert "mjcf" in pack.output_types
    assert "mjcf" in _PUBLISHABLE_TYPES
    assert frozenset(pack.output_types) == _PUBLISHABLE_TYPES
    # Constructing it at all is the cross-check.
    assert _api().domain == "assembly"


def test_the_operation_maps_to_its_own_output_type() -> None:
    """Unlike ``dynamics``, which maps to ``simulation``."""

    table = _DOMAIN_OPERATION_OUTPUT_TYPES["assembly"]
    assert table["mjcf"] == "mjcf"
    assert table["dynamics"] == "simulation"
    assert table["simulation"] == "simulation"


def test_an_mjcf_output_has_a_native_type_to_publish_onto() -> None:
    assert _NATIVE_TYPE_BY_OUTPUT["mjcf"] == "App::FeaturePython"


# ---------------------------------------------------------------------------
# The value it makes.
# ---------------------------------------------------------------------------


def test_mjcf_produces_an_mjcf_value_over_the_assembly() -> None:
    api = _api()
    assembly, components, _joints = _assembly(api)
    value = api.mjcf(assembly, _bodies(api, components))
    assert value.domain == "assembly"
    assert value.operation == "mjcf"
    assert value.output_type == "mjcf"
    assert value.arguments == (assembly,)
    assert [body.output_type for body in value.properties["bodies"]] == [
        "body",
        "body",
    ]
    assert value.properties["actuators"] == ()
    assert value.properties["joint_dynamics"] == ()
    assert value.properties["gravity_m_s2"] is None
    assert value.properties["solver_step_s"] is None


def test_mjcf_carries_actuators_joint_dynamics_gravity_and_step() -> None:
    api = _api()
    assembly, components, joints = _assembly(api)
    actuator = api.actuator(
        joints[0],
        kind="position",
        control_deg="30",
        stiffness_nmm_per_deg=4000,
        damping_nmms_per_deg=120,
    )
    damping = api.joint_dynamics(joints[0], damping_nmms_per_deg=40)
    value = api.mjcf(
        assembly,
        _bodies(api, components),
        actuators=[actuator],
        joint_dynamics=[damping],
        gravity_m_s2=[0.0, 0.0, -1.62],
        solver_step_s=0.0005,
        label="Lunar arm",
    )
    assert value.properties["actuators"] == (actuator,)
    assert value.properties["joint_dynamics"] == (damping,)
    assert value.properties["gravity_m_s2"] == (0.0, 0.0, -1.62)
    assert value.properties["solver_step_s"] == 0.0005
    assert value.properties["label"] == "Lunar arm"


def test_mjcf_takes_no_trace_parameters() -> None:
    """The frame budget counts what a trace costs, and there is no trace."""

    parameters = set(inspect.signature(AssemblyDomainAPI.mjcf).parameters)
    assert not parameters & {
        "start_time_s",
        "end_time_s",
        "frames_per_second",
    }
    assert parameters == {
        "self",
        "assembly",
        "bodies",
        "actuators",
        "joint_dynamics",
        # M6's one addition to an M5 surface: channels are written into the
        # exported file, and there is nothing for them to be in a trace --
        # a dynamics run reports poses, not sensors.
        "observations",
        "gravity_m_s2",
        "solver_step_s",
        "label",
    }
    # And everything else it takes, api.dynamics shares.
    shared = set(inspect.signature(AssemblyDomainAPI.dynamics).parameters)
    assert parameters - {"observations"} <= shared


def test_the_shared_parameters_have_the_same_defaults_on_both() -> None:
    """A default that drifted would be a difference nobody would look for."""

    dynamics = inspect.signature(AssemblyDomainAPI.dynamics).parameters
    mjcf = inspect.signature(AssemblyDomainAPI.mjcf).parameters
    for name, parameter in mjcf.items():
        if name in {"self", "assembly", "bodies", "observations"}:
            continue
        assert parameter.default == dynamics[name].default, name
        assert parameter.kind == dynamics[name].kind, name
    # The addition is defaulted and keyword-only, which is what makes it
    # additive: every M5 call site means exactly what it meant.
    observations = mjcf["observations"]
    assert observations.default == ()
    assert observations.kind is inspect.Parameter.KEYWORD_ONLY


# ---------------------------------------------------------------------------
# The refusals, which are the same refusals -- asserted as being the same.
# ---------------------------------------------------------------------------


def _both(api, assembly, **overrides):
    """Call both surfaces the same way and return the two refusal texts.

    The ``api.<operation>:`` prefix is stripped, and only that: the rest of
    the sentence is the part that must be identical, and a comparison that
    also scrubbed the word "dynamics" from the body would quietly excuse a
    ``joint_dynamics`` parameter name changing on one side only.
    """

    texts = {}
    for operation in ("dynamics", "mjcf"):
        try:
            getattr(api, operation)(assembly, **overrides)
        except Exception as error:  # noqa: BLE001 - the message is the subject
            text = str(error)
            assert text.startswith(f"api.{operation}: "), text
            texts[operation] = text.split(": ", 1)[1]
        else:
            texts[operation] = ""
    return texts


def _identical(texts) -> None:
    assert texts["dynamics"] == texts["mjcf"], texts


def test_a_component_without_a_body_is_refused_identically() -> None:
    api = _api()
    assembly, components, _joints = _assembly(api, count=3)
    texts = _both(api, assembly, bodies=_bodies(api, components[:2]))
    assert "one api.body per component" in texts["mjcf"]
    assert "steel is 7850" not in texts["mjcf"].lower()
    _identical(texts)


def test_a_component_from_another_assembly_is_refused_identically() -> None:
    api = _api()
    assembly, components, _joints = _assembly(api)
    other, other_components, _other_joints = _assembly(api)
    texts = _both(
        api,
        assembly,
        bodies=[*_bodies(api, components), api.body(other_components[0],
                                                    density_kg_m3=2700)],
    )
    assert "not listed in this assembly" in texts["mjcf"]
    _identical(texts)


def test_two_densities_for_one_component_are_refused_identically() -> None:
    api = _api()
    assembly, components, _joints = _assembly(api)
    doubled = [*_bodies(api, components), api.body(components[0], density_kg_m3=2700)]
    texts = _both(api, assembly, bodies=doubled)
    assert "two densities" in texts["mjcf"]
    _identical(texts)


def test_two_motors_on_one_coordinate_are_refused_identically() -> None:
    api = _api()
    assembly, components, joints = _assembly(api)
    motor = lambda: api.actuator(  # noqa: E731 - two identical values are the point
        joints[0], kind="motor", control_nmm="100"
    )
    texts = _both(
        api,
        assembly,
        bodies=_bodies(api, components),
        actuators=[motor(), motor()],
    )
    assert "two motors" in texts["mjcf"]
    _identical(texts)


def test_two_dampings_on_one_coordinate_are_refused_identically() -> None:
    api = _api()
    assembly, components, joints = _assembly(api)
    texts = _both(
        api,
        assembly,
        bodies=_bodies(api, components),
        joint_dynamics=[
            api.joint_dynamics(joints[0], damping_nmms_per_deg=10),
            api.joint_dynamics(joints[0], damping_nmms_per_deg=20),
        ],
    )
    assert "damping, armature and friction loss" in texts["mjcf"]
    _identical(texts)


def test_gravity_in_millimetres_is_refused_identically() -> None:
    """The refusal that says "Earth is 9.81", in both places at once."""

    api = _api()
    assembly, components, _joints = _assembly(api)
    texts = _both(
        api,
        assembly,
        bodies=_bodies(api, components),
        gravity_m_s2=[0.0, 0.0, -9810.0],
    )
    assert "Earth is 9.81" in texts["mjcf"]
    _identical(texts)


def test_a_solver_step_outside_its_bounds_is_refused_identically() -> None:
    api = _api()
    assembly, components, _joints = _assembly(api)
    for step in (0.0, -0.001, 2.0):
        texts = _both(
            api,
            assembly,
            bodies=_bodies(api, components),
            solver_step_s=step,
        )
        assert "solver_step_s" in texts["mjcf"], step
        _identical(texts)


def test_the_frame_interval_check_stays_on_dynamics_alone() -> None:
    """The one solver-step rule an export cannot have: there are no frames."""

    api = _api()
    assembly, components, _joints = _assembly(api)
    with pytest.raises(Exception, match="one frame interval"):
        api.dynamics(
            assembly,
            _bodies(api, components),
            frames_per_second=240,
            solver_step_s=0.5,
        )
    # The same step, exported: legal, because nothing is sampled.
    value = api.mjcf(assembly, _bodies(api, components), solver_step_s=0.5)
    assert value.properties["solver_step_s"] == 0.5


def test_an_actuator_on_a_foreign_joint_is_refused() -> None:
    api = _api()
    assembly, components, _joints = _assembly(api)
    _other, _other_components, other_joints = _assembly(api)
    with pytest.raises(Exception, match="not listed in this assembly"):
        api.mjcf(
            assembly,
            _bodies(api, components),
            actuators=[
                api.actuator(other_joints[0], kind="motor", control_nmm="100")
            ],
        )


def test_an_assembly_that_is_not_an_assembly_is_refused() -> None:
    api = _api()
    assembly, components, _joints = _assembly(api)
    with pytest.raises(Exception):
        api.mjcf(components[0], _bodies(api, components))


def test_no_bodies_at_all_is_refused() -> None:
    api = _api()
    assembly, _components, _joints = _assembly(api)
    with pytest.raises(Exception):
        api.mjcf(assembly, [])


# ---------------------------------------------------------------------------
# The mixing rules, stated rather than inherited.
# ---------------------------------------------------------------------------


def test_a_script_may_declare_more_than_one_mjcf() -> None:
    """The "exactly one simulation" rule exists for the bake, and this is not one."""

    api = _api()
    assembly, components, _joints = _assembly(api)
    first = api.mjcf(assembly, _bodies(api, components), label="earth")
    second = api.mjcf(
        assembly, _bodies(api, components), gravity_m_s2=[0, 0, -1.62], label="moon"
    )
    assert first is not second
    assert first.output_type == second.output_type == "mjcf"
    assert first.properties["gravity_m_s2"] is None
    assert second.properties["gravity_m_s2"] == (0.0, 0.0, -1.62)


def test_an_mjcf_output_is_neither_a_simulation_nor_a_motion() -> None:
    """What keeps it out of the "exactly one simulation" contract entirely."""

    api = _api()
    assembly, components, _joints = _assembly(api)
    value = api.mjcf(assembly, _bodies(api, components))
    assert value.output_type not in {"simulation", "motion"}
