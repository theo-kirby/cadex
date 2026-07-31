# SPDX-License-Identifier: LGPL-2.1-or-later

"""``assembly.task`` on the script surface (docs/MUJOCO.md M6, phase 2).

One new publishable output type, four new intermediates, and one defaulted
parameter added to an M5 surface. The decisions worth testing rather than
reading:

* **``task`` consumes another output.** Every publishable output before it
  consumed the assembly; this consumes one ``api.mjcf`` value and writes a
  bundle that references that model's file. Two tasks may share one model,
  and a task is not under the "exactly one simulation" rule for the same
  reason ``api.mjcf`` is not: nothing bakes it.
* **The refusals are the point.** M6's fork on action bounds was decided as
  "underivable is a refusal, not a default", and a surface that quietly
  defaulted would be indistinguishable from one that derived. The API
  refuses what a reader of the script could see; the engine refuses what
  only the built model knows, and this file asserts the *division* rather
  than duplicating the engine's half.
* **The whitelist did not widen.** ``api.reward`` gets ``exp``, ``sqrt`` and
  ``tanh``; ``api.motion`` must not, because its formula is rendered back
  into an Ondsel expression. One checker, two whitelists, and this file is
  what keeps the second from becoming the first.
"""

from __future__ import annotations

import inspect

import pytest

import CadexDynamics as dyn
from cadex_assembly_api import (
    AssemblyDomainAPI,
    _OBSERVATION_KINDS,
    _PUBLISHABLE_TYPES,
    _RANDOMISATION_TARGETS,
    _REWARD_FUNCTIONS,
)
from cadex_domain_api import _DOMAIN_OPERATION_OUTPUT_TYPES
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from CadexScriptedDomainPublication import _NATIVE_TYPE_BY_OUTPUT


def _api() -> AssemblyDomainAPI:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return AssemblyDomainAPI(pack.api_exports, pack.output_types)


def _source(name: str) -> dict[str, str]:
    return {"document_uid": "doc", "object_name": name}


def _assembly(api, count: int = 3):
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


def _scene(api, *, observations=None, actuators=None):
    """One assembly, one motor and one exported model with channels on it."""

    assembly, components, joints = _assembly(api)
    motor = api.actuator(joints[0], kind="motor", control_nmm="100",
                         torque_limit_nmm=500)
    actuators = [motor] if actuators is None else actuators
    if observations is None:
        observations = [
            api.observation(joints[0], "position", name="angle"),
            api.observation(components[-1], "component_position", name="hand"),
            api.observation(motor, "actuator_force", name="effort"),
        ]
    model = api.mjcf(
        assembly,
        _bodies(api, components),
        actuators=actuators,
        observations=observations,
    )
    return {
        "assembly": assembly,
        "components": components,
        "joints": joints,
        "motor": motor,
        "model": model,
        "observations": observations,
    }


def _task(api, scene, **overrides):
    arguments = {
        "actions": [scene["motor"]],
        "reward": [api.reward("-(hand_x - 300)^2", weight=1.0e-4, label="reach")],
        "termination": [
            api.termination("abs(angle)", above=170.0, label="folded")
        ],
        "episode_seconds": 4.0,
        "control_hz": 50,
    }
    arguments.update(overrides)
    return api.task(scene["model"], **arguments)


# ---------------------------------------------------------------------------
# Registration: the five places that refuse to start if they disagree.
# ---------------------------------------------------------------------------


def test_task_is_registered_everywhere_a_publishable_output_must_be() -> None:
    """``AssemblyDomainAPI.__init__`` refuses to construct if these drift.

    Asserted individually anyway, because "the API constructed" tells a
    reader that *something* is consistent and not which five things.
    """

    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    assert "task" in _PUBLISHABLE_TYPES
    assert "task" in pack.output_types
    assert "task" in pack.api_exports
    assert _DOMAIN_OPERATION_OUTPUT_TYPES["assembly"]["task"] == "task"
    assert _NATIVE_TYPE_BY_OUTPUT["task"] == "App::FeaturePython"
    assert AssemblyDomainAPI.exported_names == tuple(pack.api_exports)


def test_the_four_companions_are_intermediates_and_not_outputs() -> None:
    """An observation is an argument to a model, not a result of a script.

    The same rule ``collision`` follows and for the same reason: nothing
    publishes one, it has no native type, and a script returning one would
    be declaring a fact about a joint rather than a result.
    """

    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    for name in ("observation", "reward", "termination", "randomise"):
        assert name in pack.api_exports, name
        assert name not in pack.output_types, name
        assert name not in _PUBLISHABLE_TYPES, name
        assert name not in _NATIVE_TYPE_BY_OUTPUT, name
        # Registered as its own intermediate output type, so a script that
        # returned one is refused by the result contract rather than
        # published as something else.
        assert _DOMAIN_OPERATION_OUTPUT_TYPES["assembly"][name] == name


def test_the_apis_kind_tables_agree_with_the_engines() -> None:
    """The second copy, written down and checked rather than remembered.

    This surface does not import ``CadexDynamics`` -- it is a validation
    layer with no physics in it -- so the observation table exists twice. A
    test is what makes that a cost of one assertion instead of a promise.
    """

    assert set(_OBSERVATION_KINDS) == set(dyn.OBSERVATION_KINDS)
    assert set(_RANDOMISATION_TARGETS) == set(dyn.RANDOMISATION_TARGETS)
    assert set(_REWARD_FUNCTIONS) == set(dyn.REWARD_FUNCTIONS)

    # And each kind's target agrees about *what* it reads.
    engine_target = {
        "joint": "joint", "component": "component_link", "actuator": "actuator"
    }
    for kind, row in dyn.OBSERVATION_KINDS.items():
        assert _OBSERVATION_KINDS[kind] == engine_target[row["target"]], kind
    for target, row in dyn.RANDOMISATION_TARGETS.items():
        assert _RANDOMISATION_TARGETS[target] == engine_target[row["on"]], target


def test_the_channel_expansion_agrees_with_the_engines() -> None:
    from cadex_assembly_api import _observation_channels

    for kind, row in dyn.OBSERVATION_KINDS.items():
        assert _observation_channels(kind, "x") == [
            f"x{suffix}" for suffix in row["suffixes"]
        ], kind


# ---------------------------------------------------------------------------
# The intermediates.
# ---------------------------------------------------------------------------


def test_an_observation_carries_its_kind_its_name_and_its_target() -> None:
    api = _api()
    scene = _scene(api)
    angle, hand, effort = scene["observations"]

    assert angle.output_type == "observation"
    assert angle.properties["kind"] == "position"
    assert angle.properties["name"] == "angle"
    assert angle.arguments == (scene["joints"][0],)
    assert hand.properties["kind"] == "component_position"
    # An actuator channel records the coordinate and the kind, because that
    # is what the compiled model names the actuator after.
    assert effort.properties["motion_type"] == "angular"
    assert effort.properties["actuator_kind"] == "motor"


def test_an_observation_must_read_the_right_kind_of_thing() -> None:
    api = _api()
    assembly, components, joints = _assembly(api)
    with pytest.raises(ValueError, match="target"):
        api.observation(components[0], "position", name="a")
    with pytest.raises(ValueError, match="target"):
        api.observation(joints[0], "component_position", name="a")
    with pytest.raises(ValueError, match="kind"):
        api.observation(joints[0], "vibes", name="a")


def test_a_channel_name_must_be_something_a_formula_can_write() -> None:
    api = _api()
    _assembly_value, components, joints = _assembly(api)
    for bad in ("", "2fast", "hand position", "hand-x", "x" * 49):
        with pytest.raises(ValueError, match="name"):
            api.observation(joints[0], "position", name=bad)
    assert api.observation(joints[0], "position", name="a").properties["name"] == "a"


def test_a_reward_names_its_channels_and_may_call_three_more_functions() -> None:
    api = _api()
    term = api.reward("exp(-sqrt(hand_x^2 + hand_y^2))", weight=-2.5, label="near")
    assert term.output_type == "reward"
    # ``^`` is Ondsel's power operator and this surface accepts it, but what
    # is stored is Python: it is this engine that evaluates a reward.
    assert "**" in term.properties["expression"]
    assert "^" not in term.properties["expression"]
    assert term.properties["weight"] == -2.5
    assert term.properties["label"] == "near"

    for allowed in ("tanh(x)", "exp(x)", "sqrt(x)", "abs(x)", "sin(x)"):
        api.reward(allowed)
    with pytest.raises(ValueError, match="log"):
        api.reward("log(x)")


def test_the_motion_whitelist_did_not_widen() -> None:
    """``api.motion`` renders back to Ondsel, which has no ``tanh``."""

    api = _api()
    with pytest.raises(ValueError, match="tanh"):
        api.motion(_api_joint(api), formula="tanh(time)")
    for name in ("exp", "sqrt", "tanh"):
        with pytest.raises(ValueError):
            api.motion(_api_joint(api), formula=f"{name}(time)")
    # And a control formula did not widen either.
    _assembly_value, _components, joints = _assembly(api)
    with pytest.raises(ValueError, match="tanh"):
        api.actuator(joints[0], kind="motor", control_nmm="tanh(time)",
                     torque_limit_nmm=100)


def _api_joint(api):
    _assembly_value, _components, joints = _assembly(api)
    return joints[0]


def test_a_termination_needs_exactly_one_threshold() -> None:
    api = _api()
    rule = api.termination("abs(rate)", above=2000.0, label="spun_out")
    assert rule.output_type == "termination"
    assert rule.properties["above"] == 2000.0
    assert rule.properties["below"] is None

    with pytest.raises(ValueError, match="exactly one"):
        api.termination("abs(rate)")
    with pytest.raises(ValueError, match="exactly one"):
        api.termination("abs(rate)", above=1.0, below=0.0)
    assert api.termination("z", below=10.0).properties["below"] == 10.0


def test_a_randomisation_is_a_positive_ordered_multiplicative_range() -> None:
    api = _api()
    _assembly_value, components, joints = _assembly(api)
    entry = api.randomise(components[1], "mass", scale=[0.9, 1.1])
    assert entry.output_type == "randomise"
    assert (entry.properties["low"], entry.properties["high"]) == (0.9, 1.1)
    assert entry.properties["target"] == "mass"

    damping = api.randomise(joints[0], "damping", scale=[0.5, 2.0])
    # A joint entry records which coordinate, because a cylindrical joint
    # owns two and damping one says nothing about the other.
    assert damping.properties["motion_type"] == "angular"

    with pytest.raises(ValueError, match="positive"):
        api.randomise(components[1], "mass", scale=[0.0, 1.1])
    with pytest.raises(ValueError, match="positive"):
        api.randomise(components[1], "mass", scale=[-1.0, 1.1])
    with pytest.raises(ValueError, match="ordered"):
        api.randomise(components[1], "mass", scale=[1.5, 0.5])
    with pytest.raises(ValueError, match="property_name"):
        api.randomise(components[1], "colour", scale=[0.9, 1.1])
    with pytest.raises(ValueError, match="target"):
        api.randomise(joints[0], "mass", scale=[0.9, 1.1])


# ---------------------------------------------------------------------------
# ``observations=`` on api.mjcf.
# ---------------------------------------------------------------------------


def test_observations_are_additive_and_default_to_none() -> None:
    api = _api()
    assembly, components, _joints = _assembly(api)
    plain = api.mjcf(assembly, _bodies(api, components))
    assert plain.properties["observations"] == ()
    assert plain.output_type == "mjcf"


def test_a_channel_must_observe_something_this_model_carries() -> None:
    api = _api()
    assembly, components, joints = _assembly(api)
    other, other_components, other_joints = _assembly(api)

    with pytest.raises(ValueError, match="not listed in this assembly"):
        api.mjcf(
            assembly,
            _bodies(api, components),
            observations=[
                api.observation(other_components[1], "component_position",
                                name="x")
            ],
        )
    with pytest.raises(ValueError, match="not listed in this assembly"):
        api.mjcf(
            assembly,
            _bodies(api, components),
            observations=[api.observation(other_joints[0], "position", name="x")],
        )
    # An actuator channel has to name a motor this export was given, not
    # merely one that exists somewhere in the script.
    motor = api.actuator(joints[0], kind="motor", control_nmm="1",
                         torque_limit_nmm=10)
    with pytest.raises(ValueError, match="does not carry"):
        api.mjcf(
            assembly,
            _bodies(api, components),
            observations=[api.observation(motor, "actuator_force", name="x")],
        )


def test_two_channels_with_one_name_are_refused_including_by_expansion() -> None:
    api = _api()
    assembly, components, joints = _assembly(api)
    with pytest.raises(ValueError, match="already declares"):
        api.mjcf(
            assembly,
            _bodies(api, components),
            observations=[
                api.observation(joints[0], "position", name="x"),
                api.observation(joints[1], "position", name="x"),
            ],
        )
    # The collision an author would not see coming.
    with pytest.raises(ValueError, match="hand_x"):
        api.mjcf(
            assembly,
            _bodies(api, components),
            observations=[
                api.observation(components[1], "component_position", name="hand"),
                api.observation(joints[0], "position", name="hand_x"),
            ],
        )


# ---------------------------------------------------------------------------
# api.task.
# ---------------------------------------------------------------------------


def test_a_task_consumes_a_model_and_carries_its_declaration() -> None:
    api = _api()
    scene = _scene(api)
    task = _task(api, scene, label="reach")

    assert task.output_type == "task"
    assert task.arguments == (scene["model"],)
    assert task.properties["actions"] == (scene["motor"],)
    assert task.properties["episode_seconds"] == 4.0
    assert task.properties["control_hz"] == 50
    assert task.properties["label"] == "reach"
    assert len(task.properties["reward"]) == 1
    assert task.properties["randomisation"] == ()


def test_two_tasks_may_share_one_model() -> None:
    """Not under the "exactly one" rule, and this is what says so.

    A model exported once and trained against two ways -- a reach and a
    balance, say -- is a reasonable script, and the rule that would forbid
    it exists to protect a shell that bakes one animation.
    """

    api = _api()
    scene = _scene(api)
    first = _task(api, scene, label="reach")
    second = _task(
        api,
        scene,
        reward=[api.reward("-abs(angle)", label="hold")],
        termination=[],
        label="hold",
    )
    assert first.arguments == second.arguments == (scene["model"],)
    assert first is not second


def test_an_action_must_be_an_actuator_this_model_carries() -> None:
    api = _api()
    scene = _scene(api)
    stray = api.actuator(scene["joints"][1], kind="motor", control_nmm="1",
                         torque_limit_nmm=10)
    with pytest.raises(ValueError, match="does not carry"):
        _task(api, scene, actions=[stray])
    # One actuator is one action. The generic duplicate refusal every list
    # parameter already carries is what says so, rather than a second one.
    with pytest.raises(ValueError, match="same graph value more than once"):
        _task(api, scene, actions=[scene["motor"], scene["motor"]])
    with pytest.raises(ValueError, match="actions"):
        _task(api, scene, actions=[])


def test_a_task_needs_at_least_one_reward_term() -> None:
    api = _api()
    scene = _scene(api)
    with pytest.raises(ValueError, match="reward"):
        _task(api, scene, reward=[])


def test_the_episode_bounds_are_checked_at_the_surface() -> None:
    api = _api()
    scene = _scene(api)
    for bad in (0.0, -1.0, 3601.0):
        with pytest.raises(ValueError, match="episode_seconds"):
            _task(api, scene, episode_seconds=bad)
    for bad in (0, 1001, 2.5, True, "50"):
        with pytest.raises(ValueError, match="control_hz"):
            _task(api, scene, control_hz=bad)


def test_a_randomisation_must_target_this_assembly_and_only_once() -> None:
    api = _api()
    scene = _scene(api)
    _other, other_components, _other_joints = _assembly(api)

    task = _task(
        api,
        scene,
        randomisation=[
            api.randomise(scene["components"][1], "mass", scale=[0.9, 1.1]),
            api.randomise(scene["joints"][0], "damping", scale=[0.5, 2.0]),
        ],
    )
    assert len(task.properties["randomisation"]) == 2

    with pytest.raises(ValueError, match="not listed in this assembly"):
        _task(api, scene, randomisation=[
            api.randomise(other_components[1], "mass", scale=[0.9, 1.1])
        ])
    with pytest.raises(ValueError, match="twice"):
        _task(api, scene, randomisation=[
            api.randomise(scene["components"][1], "mass", scale=[0.9, 1.1]),
            api.randomise(scene["components"][1], "mass", scale=[0.8, 1.2]),
        ])
    # Two different properties on one joint is fine: they are different
    # numbers, and varying both is a reasonable thing to want.
    _task(api, scene, randomisation=[
        api.randomise(scene["joints"][0], "damping", scale=[0.5, 2.0]),
        api.randomise(scene["joints"][0], "armature", scale=[0.5, 2.0]),
    ])


def test_a_task_must_be_given_an_exported_model_and_not_a_simulation() -> None:
    api = _api()
    assembly, components, joints = _assembly(api)
    run = api.dynamics(assembly, _bodies(api, components))
    with pytest.raises(ValueError, match="model"):
        api.task(
            run,
            actions=[api.actuator(joints[0], kind="motor", control_nmm="1",
                                  torque_limit_nmm=10)],
            reward=[api.reward("x")],
            episode_seconds=1.0,
            control_hz=10,
        )


def test_the_actuator_surface_did_not_change() -> None:
    """Zero diff on an existing surface, asserted rather than assumed.

    A policy-driven actuator's control formula becomes its deterministic
    fallback action, which is exactly what an episode needs to run without a
    policy -- so ``api.actuator`` keeps requiring one and M6 adds nothing to
    it.
    """

    parameters = inspect.signature(AssemblyDomainAPI.actuator).parameters
    assert set(parameters) == {
        "self", "joint", "kind", "motion_type",
        "control_deg", "control_mm", "control_deg_per_s", "control_mm_per_s",
        "control_nmm", "control_n",
        "stiffness_nmm_per_deg", "stiffness_n_per_mm",
        "damping_nmms_per_deg", "damping_ns_per_mm",
        "torque_limit_nmm", "force_limit_n", "label",
    }
    api = _api()
    _assembly_value, _components, joints = _assembly(api)
    with pytest.raises(ValueError, match="control_nmm"):
        api.actuator(joints[0], kind="motor", torque_limit_nmm=100)
