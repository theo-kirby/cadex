# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``assembly.success`` on the script surface (ADR-456).

A success spec is what a policy is judged by, declared beside the task and
kept apart from its reward. It is one more intermediate on ``api.task``,
shaped like ``api.reset_variation`` and split the same way.

**The API refuses what a reader of the script could see**: a predicate that
is an expression rather than a name, one with no bound, a repeated seed, a
foot that is not in the assembly. **The engine refuses what needs the
vocabulary or the model**: whether the name is a behaviour metric at all,
whether it is the reward, whether a foot has a shape to be measured by.
That half is ``test_success_spec_model``; the vocabulary is
``CadexEvaluation``'s, and this module may not import it, because
``cadex_assembly_api`` is in the service's closure and ``CadexEvaluation``
is not (ADR-455).

None of this touches ``CadexdProtocol.OP_ARG_SPECS``: ``assembly.*`` is the
xscript authoring surface, not the cadexd op table.
"""

from __future__ import annotations

import pytest

from cadex_assembly_api import AssemblyDomainAPI
from cadex_domain_api import _DOMAIN_OPERATION_OUTPUT_TYPES
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from CadexScriptedRuntime import _DOMAIN_WORKER_BUNDLES

BALANCE = [
    {"id": "upright", "metric": "max_tilt_deg", "max": 30.0},
    {"id": "in_place", "metric": "max_drift_com_heights", "max": 2.0},
]
SEEDS = [1101, 1102, 1103]


def _api() -> AssemblyDomainAPI:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return AssemblyDomainAPI(pack.api_exports, pack.output_types)


def _source(name: str) -> dict[str, str]:
    return {"document_uid": "doc", "object_name": name}


def _scene(api):
    components = [
        api.component(_source("solid0")),
        api.component(_source("solid1")),
    ]
    joint = api.joint(
        "revolute",
        api.connector(components[0], "origin"),
        api.connector(components[1], "origin"),
    )
    assembly = api.assembly(components, [joint])
    motor = api.actuator(joint, kind="motor", control_nmm="100",
                         torque_limit_nmm=500)
    model = api.mjcf(
        assembly,
        [api.body(component, density_kg_m3=7850) for component in components],
        actuators=[motor],
        observations=[api.observation(joint, "position", name="angle")],
    )
    return {"components": components, "motor": motor, "model": model}


def _task(api, scene, **overrides):
    arguments = {
        "actions": [scene["motor"]],
        "reward": [api.reward("angle", weight=1.0e-3, label="up")],
        "episode_seconds": 4.0,
        "control_hz": 50,
    }
    arguments.update(overrides)
    return api.task(scene["model"], **arguments)


# -- registration -----------------------------------------------------------

def test_success_is_an_intermediate_and_never_an_output() -> None:
    """An argument to a task, on the terms a reward term is one."""

    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    assert "success" in pack.api_exports
    assert "success" not in pack.output_types
    assert _DOMAIN_OPERATION_OUTPUT_TYPES["assembly"]["success"] == "success"
    assert "success" in _api().exported_names


def test_the_worker_is_staged_the_module_the_vocabulary_lives_in() -> None:
    """The engine resolves a spec inside the sandbox, so the file is there."""

    staged = {name for names in _DOMAIN_WORKER_BUNDLES.values() for name in names}
    assert "CadexEvaluation.py" in staged


def test_the_api_does_not_import_the_vocabulary() -> None:
    """It is in the service's closure and ``CadexEvaluation`` stays out."""

    from test_engine_purity_guardrails import MODULE_DIR, _import_roots

    assert "CadexEvaluation" not in _import_roots(MODULE_DIR / "cadex_assembly_api.py")


# -- what a spec carries ----------------------------------------------------

def test_a_spec_carries_its_predicates_seeds_feet_tip_and_conditions() -> None:
    api = _api()
    scene = _scene(api)
    base, limb = scene["components"]
    start = api.reset_variation(base, tilt_degrees=[0.0, 3.0], height_mm=[3.0, 6.0])
    shove = api.disturbance(base, newtons=[1.0, 2.0], at_seconds=[2.0, 3.0],
                            duration_s=0.1)
    spec = api.success(
        BALANCE + [{"metric": "recovery_s_max", "max": 2.0}],
        seeds=SEEDS, feet=[limb], tip=limb, tip_offset_mm=[0, 0, 40],
        episode_seconds=10.0, reset_variation=[start], disturbance=[shove],
        label="balance",
    )
    assert spec.output_type == "success"
    assert [dict(row) for row in spec.properties["predicates"]] == [
        {"id": "upright", "metric": "max_tilt_deg", "min": None, "max": 30.0},
        {"id": "in_place", "metric": "max_drift_com_heights", "min": None, "max": 2.0},
        # An id defaults to the metric it bounds.
        {"id": "recovery_s_max", "metric": "recovery_s_max", "min": None, "max": 2.0},
    ]
    assert list(spec.properties["seeds"]) == SEEDS
    assert list(spec.properties["feet"]) == [limb]
    assert spec.properties["tip"] is limb
    assert list(spec.properties["tip_offset_mm"]) == [0.0, 0.0, 40.0]
    assert spec.properties["episode_seconds"] == 10.0
    assert list(spec.properties["reset_variation"]) == [start]
    assert list(spec.properties["disturbance"]) == [shove]
    assert spec.properties["label"] == "balance"

    task = _task(api, scene, success=spec)
    assert task.properties["success"] is spec


def test_omitted_conditions_are_absent_and_an_empty_list_is_a_statement() -> None:
    """Absent is "the task's own"; ``[]`` is "none". They are not the same."""

    api = _api()
    inherits = api.success(BALANCE, seeds=SEEDS)
    for name in ("randomisation", "reset_variation", "disturbance",
                 "episode_seconds", "tip"):
        assert name not in inherits.properties
    bare = api.success(BALANCE, seeds=SEEDS, randomisation=[], reset_variation=[],
                       disturbance=[])
    assert list(bare.properties["randomisation"]) == []
    assert list(bare.properties["reset_variation"]) == []
    assert list(bare.properties["disturbance"]) == []


def test_a_spec_states_its_own_randomisation_as_the_values_a_task_takes() -> None:
    """The third condition (ADR-458), held to the assembly as a task's is."""

    api = _api()
    scene = _scene(api)
    base = scene["components"][0]
    mass = api.randomise(base, "mass", scale=[0.85, 1.15])
    spec = api.success(BALANCE, seeds=SEEDS, randomisation=[mass])
    assert list(spec.properties["randomisation"]) == [mass]
    assert _task(api, scene, success=spec).properties["success"] is spec

    for wrong in ([base], [api.reward("angle")], "mass"):
        with pytest.raises(ValueError):
            api.success(BALANCE, seeds=SEEDS, randomisation=wrong)

    stranger = api.randomise(api.component(_source("solid9")), "mass", scale=[0.9, 1.1])
    twice = api.randomise(base, "mass", scale=[0.5, 1.5])
    for entries, why in (
        ([stranger], "varies a component that is not listed in this assembly"),
        ([mass, twice], "on one target twice"),
    ):
        with pytest.raises(ValueError) as refusal:
            _task(api, scene, success=api.success(BALANCE, seeds=SEEDS, randomisation=entries))
        assert "success.randomisation[" in str(refusal.value)
        assert why in str(refusal.value)


def test_a_task_without_a_spec_is_the_value_it_always_was() -> None:
    """No ``success`` key at all, so its payload and digest do not move."""

    api = _api()
    task = _task(api, _scene(api))
    assert "success" not in task.properties
    assert "success" not in task.to_payload()["properties"]


# -- refusals a reader could see --------------------------------------------

@pytest.mark.parametrize(
    "metric",
    ["up", "reward > 3", "-(angle)^2", "total reward", "Reward", "", 7, None],
)
def test_a_predicate_is_a_name_and_never_an_expression(metric) -> None:
    """The reward is arithmetic on channels; a predicate is not arithmetic.

    ``up`` -- the task's own reward label -- is a well-formed name and gets
    through here. Refusing it takes the vocabulary, which is the engine's.
    """

    api = _api()
    predicates = [{"id": "p", "metric": metric, "min": 0.0}]
    if metric == "up":
        assert api.success(predicates, seeds=SEEDS).properties["predicates"]
        return
    with pytest.raises(ValueError) as refusal:
        api.success(predicates, seeds=SEEDS)
    assert "never an expression" in str(refusal.value)
    assert "predicates[0].metric" in str(refusal.value)


@pytest.mark.parametrize(
    "predicates, says",
    [
        ([], "passes everything"),
        ("max_tilt_deg", "passes everything"),
        (["max_tilt_deg"], "expected an object"),
        ([{"metric": "max_tilt_deg"}], "states no bound"),
        ([{"metric": "max_tilt_deg", "min": 30.0, "max": 10.0}], "max below min"),
        ([{"metric": "max_tilt_deg", "max": float("nan")}], "finite number"),
        ([{"metric": "max_tilt_deg", "max": True}], "finite number"),
        ([{"metric": "max_tilt_deg", "max": 30.0, "weight": 2.0}], "unknown keys"),
        ([{"metric": "max_tilt_deg", "max": 30.0},
          {"metric": "max_tilt_deg", "min": 1.0}], "used by an earlier predicate"),
        ([{"id": "x" * 65, "metric": "max_tilt_deg", "max": 30.0}], "1-64 characters"),
        ([{"metric": "completed", "min": 1.0}] * 33, "1 through 32"),
    ],
)
def test_a_malformed_predicate_list_is_refused_with_the_reason(predicates, says) -> None:
    with pytest.raises(ValueError) as refusal:
        _api().success(predicates, seeds=SEEDS)
    assert says in str(refusal.value)


@pytest.mark.parametrize(
    "seeds, says",
    [
        ([], "1 through 64"),
        (1101, "1 through 64"),
        (list(range(65)), "1 through 64"),
        ([1101, 1101], "repeats a seed"),
        ([1101, -1], "integer from 0"),
        ([1101, 1.5], "integer from 0"),
        ([True], "integer from 0"),
        ([2**31], "integer from 0"),
    ],
)
def test_seeds_are_distinct_non_negative_integers(seeds, says) -> None:
    with pytest.raises(ValueError) as refusal:
        _api().success(BALANCE, seeds=seeds)
    assert says in str(refusal.value)


def test_a_spec_may_state_the_scale_it_was_written_for() -> None:
    """Checked by the engine against the model; here only its shape."""

    spec = _api().success(
        BALANCE, seeds=SEEDS, scale={"weight_n": 4.7, "hip_height_mm": 96.7006}
    )
    assert dict(spec.properties["scale"]) == {"weight_n": 4.7, "hip_height_mm": 96.7006}
    assert "scale" not in _api().success(BALANCE, seeds=SEEDS).properties


@pytest.mark.parametrize(
    "scale, says",
    [
        ({}, "at least one of"),
        ([96.7], "at least one of"),
        ({"hip_mm": 96.7}, "unknown keys ['hip_mm']"),
        ({"hip_height_mm": 0.0}, "scale.hip_height_mm"),
        ({"weight_n": "heavy"}, "scale.weight_n"),
    ],
)
def test_a_malformed_scale_is_refused(scale, says) -> None:
    with pytest.raises(ValueError) as refusal:
        _api().success(BALANCE, seeds=SEEDS, scale=scale)
    assert says in str(refusal.value)


def test_a_tip_offset_without_a_tip_is_refused() -> None:
    with pytest.raises(ValueError) as refusal:
        _api().success(BALANCE, seeds=SEEDS, tip_offset_mm=[0, 0, 40])
    assert "no tip is named" in str(refusal.value)


def test_feet_a_tip_and_conditions_are_api_values_of_the_right_type() -> None:
    api = _api()
    scene = _scene(api)
    base = scene["components"][0]
    shove = api.disturbance(base, newtons=[1.0, 2.0], at_seconds=[2.0, 3.0],
                            duration_s=0.1)
    for arguments in (
        {"feet": ["c_foot"]},
        {"feet": [scene["motor"]]},
        {"feet": [base, base]},
        {"tip": "c_hand"},
        {"tip": scene["motor"]},
        {"reset_variation": [shove]},
        {"disturbance": [base]},
        {"episode_seconds": 0.0},
    ):
        with pytest.raises(ValueError):
            api.success(BALANCE, seeds=SEEDS, **arguments)


def test_a_task_refuses_a_spec_that_names_another_assemblys_components() -> None:
    """Checked where both are visible: the task knows the assembly."""

    api = _api()
    scene = _scene(api)
    stranger = api.component(_source("solid9"))
    shove = api.disturbance(stranger, newtons=[1.0, 2.0], at_seconds=[2.0, 3.0],
                            duration_s=0.1)
    start = api.reset_variation(stranger, tilt_degrees=[0.0, 3.0])
    for arguments, where in (
        ({"feet": [stranger]}, "success.feet[0]"),
        ({"tip": stranger}, "success.tip"),
        ({"disturbance": [shove]}, "success.disturbance[0]"),
        ({"reset_variation": [start]}, "success.reset_variation[0]"),
    ):
        spec = api.success(BALANCE, seeds=SEEDS, **arguments)
        with pytest.raises(ValueError) as refusal:
            _task(api, scene, success=spec)
        assert where in str(refusal.value)
        assert "not listed in this assembly" in str(refusal.value)


def test_a_task_takes_one_success_value_and_nothing_else() -> None:
    api = _api()
    scene = _scene(api)
    for wrong in (BALANCE, api.reward("angle"), [api.success(BALANCE, seeds=SEEDS)]):
        with pytest.raises(ValueError) as refusal:
            _task(api, scene, success=wrong)
        assert "invalid success" in str(refusal.value)
