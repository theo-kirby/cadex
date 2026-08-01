# SPDX-License-Identifier: LGPL-2.1-or-later

"""``assembly.policy`` on the script surface (docs/MUJOCO.md M7, phase 3).

One new publishable output type and no new intermediates, which is the
smallest a slice of this kind can be. The decisions worth testing rather
than reading:

* **``policy`` is the second output that consumes another output.**
  ``api.task`` was the first, consuming one ``api.mjcf``; this consumes one
  ``api.task``. Two policies may share one task -- two seeds, two reward
  weightings -- and it is not under the "exactly one simulation" rule for
  the reason ``api.mjcf`` and ``api.task`` are not: nothing bakes a policy.
* **``sha256`` is required and never inferred.** VISION principle 3 says
  state that cannot be rebuilt from the script is a bug; a trained policy
  genuinely cannot be, so the script carries the one thing that *can* be
  checked. A surface that inferred the digest from whatever file was there
  would be indistinguishable from one that checked nothing.
* **The API refuses what a reader of the script could see** -- a name with a
  slash in it, a digest that is not 64 hex characters -- and the *worker*
  refuses what only the store and the bundle know. This file asserts the
  division rather than duplicating the worker's half.

The worker-contract half lives here too, because ``_policy_outputs_contract``
is tier-3 re-validation of a graph a script could hand-build, and testing it
against the API that makes the values is what makes it a re-validation
rather than a restatement.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import CadexDynamics as dyn
from cadex_assembly_api import AssemblyDomainAPI, _PUBLISHABLE_TYPES
from cadex_domain_api import DomainValue, _DOMAIN_OPERATION_OUTPUT_TYPES
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from CadexScriptedDomainPublication import _NATIVE_TYPE_BY_OUTPUT

DIGEST = "a" * 64


def _api() -> AssemblyDomainAPI:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return AssemblyDomainAPI(pack.api_exports, pack.output_types)


def _source(name: str) -> dict[str, str]:
    return {"document_uid": "doc", "object_name": name}


def _scene(api):
    components = [api.component(_source(f"solid{i}"), grounded=i == 0)
                  for i in range(3)]
    joints = [
        api.joint("revolute", api.connector(components[i], "origin"),
                  api.connector(components[i + 1], "origin"))
        for i in range(2)
    ]
    assembly = api.assembly(components, joints)
    motor = api.actuator(joints[0], kind="motor", control_nmm="100",
                         torque_limit_nmm=500)
    observations = [
        api.observation(joints[0], "position", name="angle"),
        api.observation(components[-1], "component_position", name="hand"),
        api.observation(motor, "actuator_force", name="effort"),
    ]
    model = api.mjcf(
        assembly,
        [api.body(component, density_kg_m3=7850) for component in components],
        actuators=[motor],
        observations=observations,
    )
    task = api.task(
        model,
        actions=[motor],
        reward=[api.reward("-(hand_x - 300)^2", weight=1.0e-4, label="reach")],
        episode_seconds=4.0,
        control_hz=50,
    )
    return {"assembly": assembly, "components": components, "joints": joints,
            "motor": motor, "model": model, "task": task}


# ---------------------------------------------------------------------------
# Registration: the five places that refuse to start if they disagree.
# ---------------------------------------------------------------------------


def test_policy_is_registered_everywhere_a_publishable_output_must_be() -> None:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    assert "policy" in _PUBLISHABLE_TYPES
    assert "policy" in pack.output_types
    assert "policy" in pack.api_exports
    assert _DOMAIN_OPERATION_OUTPUT_TYPES["assembly"]["policy"] == "policy"
    assert _NATIVE_TYPE_BY_OUTPUT["policy"] == "App::FeaturePython"
    assert "policy" in AssemblyDomainAPI.exported_names


def test_the_surface_takes_a_task_and_two_required_keywords() -> None:
    signature = inspect.signature(AssemblyDomainAPI.policy)
    assert list(signature.parameters) == ["self", "task", "weights", "sha256",
                                           "label"]
    for name in ("weights", "sha256"):
        assert signature.parameters[name].default is inspect.Parameter.empty
        assert signature.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY


# ---------------------------------------------------------------------------
# The value it makes.
# ---------------------------------------------------------------------------


def test_a_policy_records_the_file_and_the_digest_the_script_declared() -> None:
    api = _api()
    scene = _scene(api)
    policy = api.policy(scene["task"], weights="Walk.CxPolicy", sha256=DIGEST.upper(),
                        label="gait")

    assert policy.output_type == "policy"
    assert policy.operation == "policy"
    assert policy.arguments == (scene["task"],)
    assert policy.properties["weights"] == "Walk.CxPolicy"
    # The digest is lowercased so a pasted upper-case one is not a refusal,
    # but the *name* is not: a store is case-sensitive and so is this.
    assert policy.properties["sha256"] == DIGEST
    assert policy.properties["label"] == "gait"


def test_two_policies_may_share_one_task() -> None:
    """Two seeds against one task is a reasonable script, so it is allowed.

    The same reasoning that let two tasks share one model: nothing bakes a
    policy, so there is no "exactly one" rule for it to break.
    """

    api = _api()
    scene = _scene(api)
    first = api.policy(scene["task"], weights="a.cxpolicy", sha256="0" * 64)
    second = api.policy(scene["task"], weights="b.cxpolicy", sha256="1" * 64)
    assert first is not second
    assert first.arguments == second.arguments == (scene["task"],)


# ---------------------------------------------------------------------------
# What the API refuses, which is what a reader of the script could see.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "weights",
    ["", "   ", "nested/walk.cxpolicy", "..\\walk.cxpolicy", "../walk.cxpolicy",
     "x" * 121 + ".cxpolicy"],
)
def test_a_weights_name_that_is_not_a_file_in_assets_is_refused(weights) -> None:
    api = _api()
    scene = _scene(api)
    with pytest.raises(ValueError, match="weights"):
        api.policy(scene["task"], weights=weights, sha256=DIGEST)


@pytest.mark.parametrize("weights", ["walk.stl", "walk", "walk.json",
                                      "walk.cxpolicy.stl"])
def test_a_weights_name_that_is_not_a_cxpolicy_is_refused(weights) -> None:
    """The suffix is what the store's own check keys on, so it is checked here.

    A .stl in this parameter would be stored happily -- ``put_asset`` holds
    both kinds since ADR-084 -- and refused only once the worker tried to
    read a mesh as a container. Refusing it in the script is the cheaper
    place.
    """

    api = _api()
    scene = _scene(api)
    with pytest.raises(ValueError, match="cxpolicy"):
        api.policy(scene["task"], weights=weights, sha256=DIGEST)


@pytest.mark.parametrize(
    "digest",
    ["", "abc", "g" * 64, "a" * 63, "a" * 65, "  " + "a" * 62],
)
def test_a_digest_that_is_not_64_hex_characters_is_refused(digest) -> None:
    api = _api()
    scene = _scene(api)
    with pytest.raises(ValueError, match="sha256"):
        api.policy(scene["task"], weights="walk.cxpolicy", sha256=digest)


def test_the_digest_refusal_says_where_to_get_the_right_one() -> None:
    """A refusal that does not say what to change is addressed to nobody."""

    api = _api()
    scene = _scene(api)
    with pytest.raises(ValueError) as excinfo:
        api.policy(scene["task"], weights="walk.cxpolicy", sha256="short")
    assert "put_asset reports it" in str(excinfo.value)


@pytest.mark.parametrize("wrong", ["model", "assembly", "motor"])
def test_a_policy_that_does_not_consume_a_task_is_refused(wrong) -> None:
    api = _api()
    scene = _scene(api)
    with pytest.raises(ValueError, match="task"):
        api.policy(scene[wrong], weights="walk.cxpolicy", sha256=DIGEST)


def test_a_policy_consuming_something_that_is_not_a_domain_value_is_refused() -> None:
    api = _api()
    with pytest.raises(ValueError, match="task"):
        api.policy("outputs/job-task.json", weights="walk.cxpolicy",
                   sha256=DIGEST)


# ---------------------------------------------------------------------------
# The worker's tier-3 re-validation, which is a different check.
#
# A DomainValue is a plain object and a script can construct one that looks
# close enough, so the worker re-walks the graph. What it adds over the API
# is the one thing the API cannot know: whether the task this policy names is
# an output the script actually *returned*.
# ---------------------------------------------------------------------------


def _contract(**outputs):
    from cadex_assembly_worker import _policy_outputs_contract

    tasks = [(name, value) for name, value in outputs.items()
             if isinstance(value, DomainValue) and value.output_type == "task"]
    return _policy_outputs_contract(outputs, task_exports=tasks)


def test_a_policy_whose_task_is_returned_passes_the_contract() -> None:
    api = _api()
    scene = _scene(api)
    policy = api.policy(scene["task"], weights="walk.cxpolicy", sha256=DIGEST)
    found = _contract(job_task=scene["task"], job_policy=policy)
    assert [name for name, _ in found] == ["job_policy"]


def test_a_policy_naming_a_task_the_script_never_returned_is_refused() -> None:
    """The check no earlier contract could make.

    An unpublished task has no retained bundle and no digest -- and the
    digest is the entire claim a policy makes -- so a policy pointing at one
    would be verified against a file nobody has. It is exactly the sort of
    thing that would be discovered later, by whoever tried to run it.
    """

    from cadex_assembly_worker import AssemblyCandidateError

    api = _api()
    scene = _scene(api)
    policy = api.policy(scene["task"], weights="walk.cxpolicy", sha256=DIGEST)
    with pytest.raises(AssemblyCandidateError) as excinfo:
        _contract(job_policy=policy)
    details = excinfo.value.details
    assert details["stage"] == "policy_graph"
    assert "Return the api.task value in result" in details["correction"]


def test_a_hand_built_value_that_only_looks_like_a_policy_is_refused() -> None:
    from cadex_assembly_worker import AssemblyCandidateError

    api = _api()
    scene = _scene(api)
    forged = DomainValue(
        domain="assembly", operation="task", output_type="policy",
        arguments=(scene["task"],),
        properties={"weights": "walk.cxpolicy", "sha256": DIGEST},
    )
    with pytest.raises(AssemblyCandidateError, match="api.policy"):
        _contract(job_task=scene["task"], job_policy=forged)


def test_a_policy_consuming_a_non_task_value_is_refused_by_the_worker_too() -> None:
    from cadex_assembly_worker import AssemblyCandidateError

    api = _api()
    scene = _scene(api)
    forged = DomainValue(
        domain="assembly", operation="policy", output_type="policy",
        arguments=(scene["model"],),
        properties={"weights": "walk.cxpolicy", "sha256": DIGEST},
    )
    with pytest.raises(AssemblyCandidateError, match="api.task value"):
        _contract(job_task=scene["task"], job_policy=forged)


@pytest.mark.parametrize("missing", ["weights", "sha256"])
def test_a_policy_value_missing_a_required_property_is_refused(missing) -> None:
    from cadex_assembly_worker import AssemblyCandidateError

    api = _api()
    scene = _scene(api)
    properties = {"weights": "walk.cxpolicy", "sha256": DIGEST}
    properties[missing] = ""
    forged = DomainValue(
        domain="assembly", operation="policy", output_type="policy",
        arguments=(scene["task"],), properties=properties,
    )
    with pytest.raises(AssemblyCandidateError, match=missing):
        _contract(job_task=scene["task"], job_policy=forged)


# ---------------------------------------------------------------------------
# The describe_api note, which is how the model learns any of this exists.
# ---------------------------------------------------------------------------


def test_the_api_note_says_where_training_happens_and_that_it_is_not_here() -> None:
    """The answer to docs/VISION.md's open training question, on the surface.

    There is no train button and nothing to press. The note has to say so,
    because the alternative is a model that keeps looking for one.
    """

    from CadexScriptedRuntime import _capability_api_listing

    note = _capability_api_listing()["assembly"]["notes"]
    assert "assembly.policy(" in note
    assert "training/cadex_train.py" in note
    assert "put_asset" in note
    assert "required and never inferred" in note
    assert "refused rather than run" in note


def test_the_docstring_names_the_refusals_a_reader_will_actually_meet() -> None:
    # Whitespace-normalised: the docstring is wrapped, so a phrase that reads
    # as one on the page is several lines in the source.
    text = " ".join((inspect.getdoc(AssemblyDomainAPI.policy) or "").split())
    assert "no train button and nothing to press" in text
    assert "sha256" in text
    assert "witness" in text
    for reason in ("task", "model", "channels", "action"):
        assert reason in text


def test_the_engine_side_reasons_are_all_reachable_names() -> None:
    """Every refusal this surface can produce downstream, listed once.

    A reason code is a contract with the worker's candidate-failure stage,
    so a rename that missed one would be a stage nobody handles.
    """

    # The whole module, because the refusals are spread across
    # decode_policy, _policy_layers, _policy_vector, policy_forward and
    # verify_policy -- and which function raises which is an implementation
    # detail, while the reason code is the contract.
    source = Path(dyn.__file__).read_text(encoding="utf-8")
    for reason in (
        "policy_too_large", "policy_not_a_container", "policy_truncated",
        "policy_header_malformed", "policy_schema_unknown",
        "policy_task_mismatch", "policy_model_mismatch",
        "policy_channels_mismatch", "policy_actions_mismatch",
        "policy_output_range_mismatch", "policy_witness_missing",
        "policy_witness_disagrees", "policy_network_malformed",
        "policy_weights_mismatch", "policy_observation_mismatch",
        "policy_normaliser_malformed",
    ):
        assert reason in source, f"{reason} is not raised anywhere"
