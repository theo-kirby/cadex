# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``assembly.rollout`` on the script surface (docs/MUJOCO.md M8, phase 2).

**A new operation and no new output type**, which is the whole design. A
rollout produces a ``simulation`` -- the same type ``api.simulation`` and
``api.dynamics`` produce -- so it lands under ADR-077's "exactly one
simulation" rule for free, reaches the shell through a trace format that has
not changed since ADR-050, and needs no protocol change and no ``shell/``
diff.

What that buys, and what this file tests:

* a rollout beside an ``api.dynamics`` is a **refusal**, not a scene
  ``cadex_animate`` silently clears on finding two
  ``assembly_simulation_json`` artifacts;
* a rollout beside an ``api.motion`` is a refusal for the same reason
  ``api.dynamics`` beside one is: they are three ways of deciding where a
  part goes, and a script picks one;
* a rollout naming a policy the script does not **return** is a refusal,
  because an unpublished policy is one the engine never verified.

The worker-contract half lives here for the reason it does in
``test_dynamics_policy_api``: a ``DomainValue`` is a plain object, so testing
the re-validation against the API that makes the values is what makes it a
re-validation rather than a restatement.
"""

from __future__ import annotations

import inspect

import pytest

from cadex_assembly_api import AssemblyDomainAPI
from cadex_domain_api import DomainValue, _DOMAIN_OPERATION_OUTPUT_TYPES
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS

DIGEST = "a" * 64


def _api() -> AssemblyDomainAPI:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return AssemblyDomainAPI(pack.api_exports, pack.output_types)


def _source(name: str) -> dict[str, str]:
    return {"document_uid": "doc", "object_name": name}


def _scene(api, *, episode_seconds: float = 2.0, control_hz: int = 50):
    components = [api.component(_source(f"solid{index}"), grounded=index == 0)
                  for index in range(2)]
    joints = [api.joint("revolute", api.connector(components[0], "origin"),
                        api.connector(components[1], "origin"))]
    assembly = api.assembly(components, joints)
    motor = api.actuator(joints[0], kind="motor", control_nmm="0",
                         torque_limit_nmm=500)
    model = api.mjcf(
        assembly,
        [api.body(component, density_kg_m3=7850) for component in components],
        actuators=[motor],
        observations=[api.observation(joints[0], "position", name="angle")],
    )
    task = api.task(
        model, actions=[motor],
        reward=[api.reward("angle", weight=1.0e-3, label="lift")],
        episode_seconds=episode_seconds, control_hz=control_hz,
    )
    policy = api.policy(task, weights="walk.cxpolicy", sha256=DIGEST)
    return {"assembly": assembly, "components": components, "joints": joints,
            "motor": motor, "model": model, "task": task, "policy": policy}


# ---------------------------------------------------------------------------
# Registration. Four places rather than five: there is no new output type,
# which is what puts a rollout under the "exactly one simulation" rule.
# ---------------------------------------------------------------------------


def test_rollout_is_an_operation_that_produces_the_existing_simulation_type() -> None:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    assert "rollout" in pack.api_exports
    assert "rollout" in AssemblyDomainAPI.exported_names
    assert _DOMAIN_OPERATION_OUTPUT_TYPES["assembly"]["rollout"] == "simulation"
    # The negative, which is the design: no `rollout` output type anywhere.
    assert "rollout" not in pack.output_types
    assert _DOMAIN_OPERATION_OUTPUT_TYPES["assembly"]["dynamics"] == "simulation"


def test_the_surface_takes_a_policy_and_three_optional_keywords() -> None:
    signature = inspect.signature(AssemblyDomainAPI.rollout)
    assert list(signature.parameters) == [
        "self", "policy", "frames_per_second", "seed", "label"
    ]
    for name in ("frames_per_second", "seed", "label"):
        assert signature.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["frames_per_second"].default is None
    assert signature.parameters["seed"].default is None


# ---------------------------------------------------------------------------
# The value it makes.
# ---------------------------------------------------------------------------


def test_a_rollout_records_the_policy_the_rate_and_the_seed() -> None:
    api = _api()
    scene = _scene(api)
    run = api.rollout(scene["policy"], frames_per_second=25, seed=7, label="gait")

    assert run.output_type == "simulation"
    assert run.operation == "rollout"
    assert run.arguments == (scene["policy"],)
    assert run.properties["frames_per_second"] == 25
    assert run.properties["seed"] == 7
    assert run.properties["label"] == "gait"


def test_the_frame_rate_defaults_to_the_tasks_own_control_rate() -> None:
    """One frame per control step: the only rate that always divides.

    A default of 60 -- ``api.dynamics``'s -- would refuse every 50 Hz task,
    which is the rate the task surface's own documentation encourages.
    """

    api = _api()
    assert api.rollout(_scene(api, control_hz=50)["policy"]).properties[
        "frames_per_second"] == 50
    assert api.rollout(_scene(api, control_hz=120)["policy"]).properties[
        "frames_per_second"] == 120


def test_the_frame_limit_is_declared_from_the_schedule_the_task_fixed() -> None:
    """No time range to read, so the estimate comes off the episode.

    An episode's real step count is not known until the bundle is built, so
    this is an upper bound and the worker re-checks it against the frames
    that actually came out -- the same division ``api.dynamics`` makes.
    """

    api = _api()
    scene = _scene(api, episode_seconds=4.0)
    assert api.rollout(scene["policy"]).properties["estimated_frame_limit"] == 202
    assert api.rollout(
        scene["policy"], frames_per_second=25
    ).properties["estimated_frame_limit"] == 102


# ---------------------------------------------------------------------------
# What the API refuses, which is what a reader of the script could see.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("wrong", ["task", "model", "assembly", "motor"])
def test_a_rollout_that_does_not_consume_a_policy_is_refused(wrong) -> None:
    api = _api()
    scene = _scene(api)
    with pytest.raises(ValueError, match="policy"):
        api.rollout(scene[wrong])


def test_a_rollout_consuming_something_that_is_not_a_domain_value_is_refused() -> None:
    api = _api()
    with pytest.raises(ValueError, match="policy"):
        api.rollout("outputs/gait-policy.json")


@pytest.mark.parametrize("rate", [0, -1, 241, 1.5, True, "50"])
def test_a_frame_rate_outside_one_through_240_is_refused(rate) -> None:
    api = _api()
    scene = _scene(api)
    with pytest.raises(ValueError, match="frames_per_second"):
        api.rollout(scene["policy"], frames_per_second=rate)


@pytest.mark.parametrize("seed", [-1, 1.5, True, "7", 2**31])
def test_a_seed_that_is_not_a_non_negative_integer_is_refused(seed) -> None:
    api = _api()
    scene = _scene(api)
    with pytest.raises(ValueError, match="seed"):
        api.rollout(scene["policy"], seed=seed)


def test_a_rollout_that_would_bake_too_many_frames_is_refused() -> None:
    """An hour of episode at 240 fps is 864 000 frames."""

    api = _api()
    scene = _scene(api, episode_seconds=3600.0)
    with pytest.raises(ValueError, match="10000 frames"):
        api.rollout(scene["policy"], frames_per_second=240)


# ---------------------------------------------------------------------------
# The worker's tier-3 re-validation, which is a different check.
# ---------------------------------------------------------------------------


def _contract(raw, *, assembly_value, joint_outputs=None):
    from cadex_assembly_worker import _simulation_contract

    policies = [(name, value) for name, value in raw.items()
                if isinstance(value, DomainValue) and value.output_type == "policy"]
    return _simulation_contract(
        raw,
        assembly_value=assembly_value,
        joint_outputs=joint_outputs or {},
        policy_exports=policies,
    )


def test_the_worker_contract_accepts_a_rollout_of_a_published_policy() -> None:
    api = _api()
    scene = _scene(api)
    run = api.rollout(scene["policy"])
    output, value, motions = _contract(
        {"asm": scene["assembly"], "gait": scene["policy"], "play": run},
        assembly_value=scene["assembly"],
    )
    assert output == "play"
    assert value is run
    # A rollout drives no api.motion, exactly as a dynamics run drives none.
    assert motions == {}


def test_a_rollout_of_a_policy_the_script_never_returned_is_refused() -> None:
    """The check no earlier contract could make.

    An unpublished policy has no retained receipt, and the receipt is where
    the engine records that it checked the weights against the task they
    claim. Playing one would be playing a network nothing verified -- which
    is exactly the gait ``verify_policy`` exists so nobody has to watch and
    distrust.
    """

    from cadex_assembly_worker import AssemblyCandidateError

    api = _api()
    scene = _scene(api)
    run = api.rollout(scene["policy"])
    with pytest.raises(AssemblyCandidateError) as excinfo:
        _contract({"asm": scene["assembly"], "play": run},
                  assembly_value=scene["assembly"])
    details = excinfo.value.details
    assert details["stage"] == "rollout_graph"
    assert "Return the api.policy value in result" in details["correction"]


def test_a_rollout_cannot_sit_beside_a_dynamics_run() -> None:
    """ADR-077, inherited rather than restated.

    Both are ``simulation`` outputs, so this is the *existing* "exactly one"
    refusal firing on a new pair. That is the reason a rollout has no output
    type of its own: ``cadex_animate._simulation_entries`` finds two
    ``assembly_simulation_json`` artifacts, bakes NEITHER, clears the scene
    and reports into a message the UI never shows.
    """

    from cadex_assembly_worker import AssemblyCandidateError

    api = _api()
    scene = _scene(api)
    bodies = [api.body(component, density_kg_m3=7850)
              for component in scene["components"]]
    raw = {
        "asm": scene["assembly"],
        "gait": scene["policy"],
        "play": api.rollout(scene["policy"]),
        "drop": api.dynamics(scene["assembly"], bodies),
    }
    with pytest.raises(AssemblyCandidateError, match="exactly one"):
        _contract(raw, assembly_value=scene["assembly"])


def test_a_rollout_cannot_sit_beside_an_api_motion() -> None:
    """The refusal ``api.dynamics`` already carries, extended by one word.

    Three ways of deciding where a part goes -- prescribed, computed from
    mass, computed from a policy -- and a script picks one.
    """

    from cadex_assembly_worker import AssemblyCandidateError

    api = _api()
    scene = _scene(api)
    joint = scene["joints"][0]
    raw = {
        "asm": scene["assembly"],
        "gait": scene["policy"],
        "spin": api.motion(joint, "2 * pi * time"),
        "play": api.rollout(scene["policy"]),
    }
    with pytest.raises(AssemblyCandidateError) as excinfo:
        _contract(raw, assembly_value=scene["assembly"],
                  joint_outputs={id(joint): "j"})
    assert "cannot be combined" in str(excinfo.value)
    assert "trained policy" in excinfo.value.details["correction"]


def test_a_hand_built_value_that_only_looks_like_a_rollout_is_refused() -> None:
    from cadex_assembly_worker import AssemblyCandidateError

    api = _api()
    scene = _scene(api)
    forged = DomainValue(
        domain="assembly", operation="rollout", output_type="simulation",
        arguments=(scene["task"],),
        properties={"frames_per_second": 50, "estimated_frame_limit": 102},
    )
    with pytest.raises(AssemblyCandidateError, match="api.policy value"):
        _contract({"asm": scene["assembly"], "gait": scene["policy"],
                   "play": forged},
                  assembly_value=scene["assembly"])


def test_a_rollout_does_not_have_to_consume_the_assembly_value() -> None:
    """The one contract line M8 relaxed, and the reason it is safe.

    Every other simulation must consume the exact returned ``api.assembly``.
    A rollout consumes a policy instead, and everything it needs to know
    about the mechanism it reads out of the exported model that policy was
    verified against -- a file ``_mjcf_contract`` already tied to this
    assembly, two links back up the chain.
    """

    api = _api()
    scene = _scene(api)
    run = api.rollout(scene["policy"])
    assert run.arguments[0] is not scene["assembly"]
    assert run.arguments[0].arguments[0].arguments[0].arguments[0] is scene[
        "assembly"
    ]


# ---------------------------------------------------------------------------
# The describe_api note, which is how the model learns any of this exists.
# ---------------------------------------------------------------------------


def test_the_api_note_says_a_rollout_closes_the_loop_and_what_it_refuses() -> None:
    from CadexScriptedRuntime import _capability_api_listing

    note = _capability_api_listing()["assembly"]["notes"]
    assert "assembly.rollout(" in note
    assert "must divide the task's control_hz" in note
    assert "returned as an output" in note
    assert "exactly one of the three" in note


def test_the_docstring_names_the_refusals_a_reader_will_actually_meet() -> None:
    text = " ".join((inspect.getdoc(AssemblyDomainAPI.rollout) or "").split())
    assert "exactly one simulation" in text
    assert "divide the task's ``control_hz`` exactly" in text
    assert "returned as an output too" in text
    assert "api.motion" in text
