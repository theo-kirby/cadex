# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A success spec, resolved against the vocabulary and the model (ADR-456).

``test_success_spec_api`` pins what a reader of the script could check. This
is the other half: what takes ``CadexEvaluation``'s list of behaviour
metrics, or the compiled model, to decide.

* **The reward never judges itself.** A predicate that names the task's
  reward, or one of its reward terms, is refused with that reason; a name
  that is no metric at all is refused with the list of the ones that are.
* A metric the spec or the mechanism cannot measure is refused when the task
  is declared, not discovered as a failed seed: gait without feet, recovery
  without a shove, tilt on an arm bolted to the bench.
* The spec's conditions are resolved against the spec's **own** horizon, by
  the functions that resolve the task's.
* A spec is **not part of what the task is**: a task with no spec is the
  bundle it always was, and two bundles that differ only in their spec are
  the same task.
"""

from __future__ import annotations

import copy
import json

import pytest

import CadexDynamics as dyn
import CadexEvaluation as evaluation
import dynamics_fixtures as fx
from test_dynamics_variation_model import (
    MOTOR as HOPPER_MOTOR,
    OBSERVATIONS as HOPPER_OBSERVATIONS,
    TASK as HOPPER_TASK,
    hopper,
)

mujoco = pytest.importorskip("mujoco")

FOOT_RADIUS_MM = 10.0
HIP_MM = 30.0
SEEDS = [1101, 1102, 1103]


def walker():
    """A free body on two round feet, standing on the environment's floor.

    Nothing is grounded, so the body is the floating base and the world
    supplies the plane (ADR-335) -- the shape every walker and balancer
    has. Each foot is a sphere on a hinge, resting exactly on the floor.
    """

    def foot(name: str, x: float) -> dict:
        return {
            "name": name,
            "size": (20.0, 20.0, 20.0),
            "collision": {
                "shapes": [fx.collision_shape("sphere", radius_mm=FOOT_RADIUS_MM)],
                "mesh": None,
            },
        }

    def hip(name: str, child: str, x: float) -> dict:
        return {
            "name": name,
            "kind": "revolute",
            "parent": "body",
            "child": child,
            "parent_frame": fx.frame((x, 0.0, -20.0), (1.0, 0.0, 0.0), -90.0),
            # The hinge sits a hip's height up and the foot hangs below it,
            # its sphere resting exactly on the floor.
            "child_frame": fx.frame(
                (0.0, 0.0, HIP_MM - FOOT_RADIUS_MM), (1.0, 0.0, 0.0), -90.0
            ),
            "values": [0.0],
            "angle_limits_degrees": [-30.0, 30.0],
        }

    return fx.build(
        [
            {
                "name": "body",
                "size": (120.0, 60.0, 40.0),
                "world": dyn.matrix_from_rotation_translation(
                    (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
                    [0.0, 0.0, HIP_MM + 20.0],
                ),
            },
            foot("front", 40.0),
            foot("rear", -40.0),
        ],
        [hip("hip_front", "front", 40.0), hip("hip_rear", "rear", -40.0)],
    )


MOTORS = [
    {"joint": joint, "motion_type": "angular", "kind": "motor",
     "control_nmm": "0", "torque_limit_nmm": 50.0}
    for joint in ("hip_front", "hip_rear")
]
OBSERVATIONS = [{"kind": "component_position", "component": "body", "name": "body"}]
START = {
    "label": "start", "component": "body",
    "tilt_degrees_low": 0.0, "tilt_degrees_high": 3.0,
    "height_mm_low": 3.0, "height_mm_high": 6.0,
    "angular_velocity_dps_low": 0.0, "angular_velocity_dps_high": 0.0,
}
SHOVE = {
    "label": "shove", "component": "body", "direction": "horizontal",
    "newtons_low": 0.5, "newtons_high": 1.0, "sustained": False,
    "at_seconds_low": 1.0, "at_seconds_high": 1.5, "duration_s": 0.1,
}
LATE_SHOVE = {**SHOVE, "label": "late", "at_seconds_low": 5.5, "at_seconds_high": 6.5}
WIND = {
    "label": "wind", "component": "body", "direction": "horizontal",
    "newtons_low": 0.0, "newtons_high": 0.1, "sustained": True,
    "at_seconds_low": 0.0, "at_seconds_high": 0.0, "duration_s": 0.0,
}
TASK = {
    "label": "stand",
    "actions": [
        {"joint": joint, "motion_type": "angular", "actuator_kind": "motor"}
        for joint in ("hip_front", "hip_rear")
    ],
    "reward": [
        {"label": "height", "expression": "body_z", "weight": 1.0e-3},
        {"label": "still", "expression": "body_x * body_x", "weight": -1.0e-4},
    ],
    "termination": [],
    "episode_seconds": 2.0,
    "control_hz": 50,
    "randomisation": [],
    "reset_variation": [START],
    "disturbance": [SHOVE],
}
BALANCE = [
    {"id": "completes", "metric": "completed", "min": 1.0},
    {"id": "upright", "metric": "max_tilt_deg", "max": 30.0},
    {"id": "in_place", "metric": "max_drift_com_heights", "max": 2.0},
    {"id": "recovers", "metric": "recovery_s_max", "max": 2.0},
]
GAIT = [
    {"id": "steps", "metric": "steps_min", "min": 4},
    {"id": "slip", "metric": "slip_share_max", "max": 0.15},
]


def spec(predicates=BALANCE, **overrides):
    declared = {
        "label": "", "predicates": [dict(row) for row in predicates],
        "seeds": list(SEEDS), "feet": [], "tip": None, "episode_seconds": None,
        "randomisation": None, "reset_variation": None, "disturbance": None,
    }
    declared.update(overrides)
    return declared


def bundle(success=None, *, mechanism=walker, motors=MOTORS,
           observations=OBSERVATIONS, task=TASK, **overrides):
    components, joints, _placements = mechanism()
    built = dyn.build_model(components, joints, actuators=[dict(m) for m in motors])
    channels = dyn.observation_records(
        list(observations), built["tree"], built["joint_records"], built["actuators"]
    )
    exported = dyn.export_mjcf(built, observations=channels)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    declaration = {**task, **overrides}
    if success is not None:
        declaration["success"] = success
    return reloaded, dyn.task_records(built, reloaded, declaration, observations=channels)


def refusal(success, **arguments) -> dyn.DynamicsError:
    with pytest.raises(dyn.DynamicsError) as raised:
        bundle(success, **arguments)
    return raised.value


# -- what lands in the bundle -----------------------------------------------

def test_a_spec_lands_in_the_bundle_resolved_and_self_contained() -> None:
    _model, task = bundle(spec(BALANCE + GAIT, feet=["front", "rear"], label="balance"))
    success = task["success"]

    assert success["schema"] == dyn.SUCCESS_SCHEMA == "cadex-success-spec-v1"
    assert success["label"] == "balance"
    assert success["seeds"] == SEEDS
    assert success["feet"] == ["front", "rear"]
    assert success["tip"] is None
    # Predicates are check()'s shape exactly, so an evaluator hands the list
    # straight to it.
    assert success["predicates"][1] == {
        "id": "upright", "metric": "max_tilt_deg", "min": None, "max": 30.0
    }
    rows = evaluation.check(success["predicates"], {"completed": 1.0, "max_tilt_deg": 4.0})
    assert [row["pass"] for row in rows] == [True, True, False, False, False, False]
    # The scale a threshold in hip heights or COM heights has on this body.
    assert success["scale"]["hip_height_mm"] == pytest.approx(HIP_MM, abs=1.0e-3)
    assert success["scale"]["com_height_mm"] > FOOT_RADIUS_MM
    assert success["scale"]["weight_n"] == pytest.approx(
        success["scale"]["mass_kg"] * 9.81
    )
    assert success["scale"]["arm_length_mm"] is None
    json.dumps(task)


def test_omitted_conditions_are_the_tasks_own() -> None:
    _model, task = bundle(spec())
    assert task["success"]["episode"] == task["episode"]
    assert task["success"]["reset_variation"] == task["reset_variation"]
    assert task["success"]["disturbance"] == task["disturbance"]


def test_declared_conditions_replace_the_tasks_and_an_empty_list_is_none() -> None:
    harder = {**SHOVE, "label": "harder", "newtons_low": 2.0, "newtons_high": 3.0}
    _model, task = bundle(spec(reset_variation=[], disturbance=[harder]))
    assert task["success"]["reset_variation"] == []
    (shove,) = task["success"]["disturbance"]
    assert (shove["label"], shove["newtons_low"], shove["newtons_high"]) == ("harder", 2.0, 3.0)
    # ...and the task it trains under is untouched by what it is judged under.
    assert [entry["label"] for entry in task["disturbance"]] == ["shove"]
    assert [entry["label"] for entry in task["reset_variation"]] == ["start"]


def test_randomisation_is_a_condition_the_spec_may_state_or_switch_off() -> None:
    """Omitted it is the task's; ``[]`` is the mechanism as built (ADR-458)."""

    mass = {"target": "mass", "label": "body_mass", "component": "body",
            "low": 0.85, "high": 1.15}
    _model, inherits = bundle(spec(), randomisation=[mass])
    assert inherits["success"]["randomisation"] == inherits["randomisation"] != []

    _model, as_built = bundle(spec(randomisation=[]), randomisation=[mass])
    assert as_built["success"]["randomisation"] == []
    # ...and the task it trains under still varies the mass.
    assert as_built["randomisation"] == inherits["randomisation"]
    assert dyn.evaluation_task(as_built)["randomisation"] == []
    assert dyn.evaluation_task(inherits)["randomisation"] == inherits["randomisation"]

    wider = {**mass, "label": "wider", "low": 0.5, "high": 1.5}
    _model, harder = bundle(spec(randomisation=[wider]), randomisation=[mass])
    (entry,) = harder["success"]["randomisation"]
    assert (entry["label"], entry["low"], entry["high"]) == ("wider", 0.5, 1.5)
    assert entry["fields"] == inherits["randomisation"][0]["fields"]

    # What a spec is judged under does not decide what the task is.
    assert (dyn.task_semantic_digest(as_built) == dyn.task_semantic_digest(inherits)
            == dyn.task_semantic_digest(harder))

    error = refusal(spec(randomisation=[{**mass, "component": "nobody"}]))
    assert error.reason == "randomisation_component_missing"
    assert "the success spec of" in str(error)


def test_the_conditions_are_checked_against_the_specs_own_horizon() -> None:
    """A shove at six seconds fits a ten second evaluation of a two second task."""

    _model, task = bundle(spec(episode_seconds=10.0, disturbance=[SHOVE, LATE_SHOVE]))
    assert task["episode"]["episode_seconds"] == pytest.approx(2.0)
    assert task["success"]["episode"]["episode_seconds"] == pytest.approx(10.0)
    assert task["success"]["episode"]["control_hz"] == task["episode"]["control_hz"]
    assert task["success"]["episode"]["max_steps"] == 500
    assert [entry["label"] for entry in task["success"]["disturbance"]] == ["shove", "late"]

    # ...and the same shove does not fit the task's own two seconds.
    error = refusal(spec(disturbance=[LATE_SHOVE]))
    assert error.reason == "disturbance_past_the_horizon"
    assert "the success spec of" in str(error)
    # Nor does an inherited one fit a spec that shortens the episode.
    assert refusal(spec(episode_seconds=1.0)).reason == "disturbance_past_the_horizon"


def test_a_spec_reset_variation_is_measured_for_clearance_like_the_tasks() -> None:
    steep = {**START, "tilt_degrees_high": 20.0}
    error = refusal(spec(reset_variation=[steep]))
    assert error.reason == "reset_variation_penetrates"
    assert "the success spec of" in str(error)


# -- the reward never judges itself -----------------------------------------

@pytest.mark.parametrize("metric", ["height", "still", "reward", "total_reward", "return"])
def test_a_predicate_on_the_tasks_own_reward_is_refused(metric) -> None:
    """``height`` and ``still`` are this task's reward terms."""

    error = refusal(spec([{"id": "paid", "metric": metric, "min": 0.0}]))
    assert error.reason == "success_reads_the_reward"
    assert "never judges itself" in error.correction
    assert error.observed["metric"] == metric
    assert error.observed["reward_terms"] == ["height", "still"]


@pytest.mark.parametrize("metric", ["body_z", "walked", "max_tilt"])
def test_a_name_that_is_no_behaviour_metric_is_refused_with_the_list(metric) -> None:
    """``body_z`` is one of the task's observation channels."""

    error = refusal(spec([{"id": "p", "metric": metric, "min": 0.0}]))
    assert error.reason == "unknown_success_metric"
    assert error.observed["available"] == sorted(evaluation.METRICS)


def test_no_behaviour_metric_is_a_reward() -> None:
    for name in evaluation.METRICS:
        assert "reward" not in name and "return" not in name


# -- a metric that cannot be measured is refused at declaration -------------

def test_a_gait_metric_needs_feet() -> None:
    error = refusal(spec(GAIT))
    assert error.reason == "success_metric_needs_feet"
    assert error.observed == {"predicate": "steps", "metric": "steps_min", "needs": "feet"}
    bundle(spec(GAIT, feet=["front", "rear"]))


def test_recovery_needs_a_shove_that_ends() -> None:
    for disturbance in ([], [WIND]):
        error = refusal(spec(disturbance=disturbance))
        assert error.reason == "success_metric_needs_shove"
        assert error.observed["predicate"] == "recovers"
    bundle(spec(disturbance=[WIND, SHOVE]))
    # Inherited from a task that has none is the same refusal.
    assert refusal(spec(), disturbance=[]).reason == "success_metric_needs_shove"


@pytest.mark.parametrize(
    "metric, arguments, need",
    [
        ("speed_ratio", {"feet": ["front", "rear"]}, "command"),
        ("lateral_ratio", {"feet": ["front", "rear"]}, "command"),
        ("final_error_arm_lengths_max", {"tip": {"body": "front", "local_mm": [0, 0, 0]}}, "target"),
        ("time_to_target_s_max", {"tip": {"body": "front", "local_mm": [0, 0, 0]}}, "target"),
        ("overshoot_ratio_max", {"tip": {"body": "front", "local_mm": [0, 0, 0]}}, "target"),
    ],
)
def test_a_metric_measured_against_a_goal_is_refused_on_a_task_that_states_none(
    metric, arguments, need
) -> None:
    """The goal is read by kind (ADR-462): a speed goal is the command and
    a point goal the target, and each refusal says which the task lacks.
    ``test_dynamics_goal_model`` holds the other half, that a task which
    states one is accepted and measured."""

    error = refusal(spec([{"id": "tracks", "metric": metric, "max": 1.0}], **arguments))
    assert error.reason == f"success_metric_needs_{need}"
    assert "this task states none" in error.correction
    assert "assembly.goal(" in error.correction


def test_a_reach_metric_needs_a_tip() -> None:
    error = refusal(spec([{"id": "close", "metric": "final_error_mm_max", "max": 5.0}]))
    assert error.reason == "success_metric_needs_tip"


def test_posture_on_a_mechanism_bolted_to_the_world_is_refused() -> None:
    arm = {
        "mechanism": lambda: fx.two_link_arm(limits=True),
        "motors": [
            {"joint": joint, "motion_type": "angular", "kind": "motor",
             "control_nmm": "0", "torque_limit_nmm": 5000.0}
            for joint in ("shoulder", "elbow")
        ],
        "observations": [{"kind": "position", "joint": "elbow",
                          "motion_type": "angular", "name": "elbow"}],
        "task": {
            **TASK,
            "actions": [
                {"joint": joint, "motion_type": "angular", "actuator_kind": "motor"}
                for joint in ("shoulder", "elbow")
            ],
            "reward": [{"label": "bent", "expression": "elbow", "weight": 1.0e-3}],
            "reset_variation": [],
            "disturbance": [],
        },
    }
    error = refusal(spec([{"id": "upright", "metric": "max_tilt_deg", "max": 30.0}]), **arm)
    assert error.reason == "success_metric_needs_base"
    assert error.observed["predicate"] == "upright"

    # What an arm can be held to today, and the tip it will be measured at.
    _model, task = bundle(
        spec([{"id": "completes", "metric": "completed", "min": 1.0}],
             tip={"body": "fore", "local_mm": [220.0, 0.0, 0.0]}),
        **arm,
    )
    assert task["success"]["tip"] == {"body": "fore", "local_mm": [220.0, 0.0, 0.0]}
    assert task["success"]["scale"]["arm_length_mm"] == pytest.approx(520.0, abs=1.0e-2)
    assert task["success"]["scale"]["com_height_mm"] is None


def test_a_height_in_com_heights_needs_the_one_floor_plane() -> None:
    """The hopper floats over a floor that is a *part*, so there is no plane."""

    arguments = {
        "mechanism": lambda: hopper(clearance_mm=1.0),
        "motors": [HOPPER_MOTOR],
        "observations": HOPPER_OBSERVATIONS,
        "task": HOPPER_TASK,
    }
    error = refusal(
        spec([{"id": "in_place", "metric": "max_drift_com_heights", "max": 2.0}]),
        **arguments,
    )
    assert error.reason == "success_metric_needs_floor"
    # Millimetres need no floor.
    bundle(spec([{"id": "in_place", "metric": "max_drift_mm", "max": 100.0}]), **arguments)


def test_what_the_spec_names_is_checked_against_the_model() -> None:
    """The rig's own refusals, reached when the task is declared."""

    assert refusal(spec(GAIT, feet=["front", "toe"])).reason == "evaluation_body_missing"
    # The body carries no collision shape, so it has no lowest point.
    assert refusal(spec(GAIT, feet=["body"])).reason == "evaluation_foot_has_no_geom"
    assert refusal(
        spec(tip={"body": "body", "local_mm": [0.0, 0.0, 0.0]})
    ).reason == "evaluation_tip_is_not_driven"


# -- a spec is not part of what the task is ---------------------------------

def test_a_task_with_no_spec_is_byte_for_byte_the_bundle_it_was() -> None:
    _model, plain = bundle()
    assert "success" not in plain
    _model, judged = bundle(spec())
    without = {key: value for key, value in judged.items() if key != "success"}
    assert json.dumps(without, sort_keys=True) == json.dumps(plain, sort_keys=True)


def test_two_bundles_that_differ_only_in_their_spec_are_the_same_task() -> None:
    """So a spec can be revised and held against every earlier policy."""

    _model, plain = bundle()
    _model, lenient = bundle(spec())
    _model, strict = bundle(spec(
        [{"id": "upright", "metric": "max_tilt_deg", "max": 10.0}],
        seeds=[7, 8], episode_seconds=10.0, disturbance=[SHOVE, LATE_SHOVE],
    ))
    digests = {dyn.task_semantic_digest(task) for task in (plain, lenient, strict)}
    assert len(digests) == 1
    assert dyn.task_differences(lenient, strict) == []
    assert dyn.task_differences(plain, strict) == []
    assert "success" in dyn.TASK_JUDGEMENT_FIELDS
    assert "success" not in dyn.TASK_SEMANTIC_FIELDS
    covered = (set(dyn.TASK_SEMANTIC_FIELDS) | set(dyn.TASK_PROVENANCE_FIELDS)
               | set(dyn.TASK_JUDGEMENT_FIELDS))
    assert set(strict) <= covered, set(strict) - covered


# -- the conditions are playable --------------------------------------------

def test_an_evaluation_episode_runs_under_the_specs_conditions() -> None:
    """The spec's horizon and shoves, on the task's model, channels and reward."""

    harder = {**SHOVE, "label": "harder", "newtons_low": 2.0, "newtons_high": 3.0,
              "at_seconds_low": 2.5, "at_seconds_high": 3.0}
    model, task = bundle(spec(episode_seconds=4.0, reset_variation=[], disturbance=[harder]))
    played = dyn.evaluation_task(task)

    assert "success" not in played
    assert played["episode"] == task["success"]["episode"]
    for key in ("observations", "actions", "reward", "termination", "randomisation"):
        assert played[key] == task[key]
    # A copy: playing an evaluation cannot edit the spec it came from.
    before = copy.deepcopy(task)
    played["disturbance"][0]["newtons_high"] = 99.0
    played["episode"]["max_steps"] = 1
    assert task == before

    played = dyn.evaluation_task(task)
    trained = dyn.evaluate_episode(model, task, seed=SEEDS[0], record_steps=False)
    judged = dyn.evaluate_episode(model, played, seed=SEEDS[0], record_steps=False)
    assert trained["step_count"] == 100 and judged["step_count"] == 200
    assert [push["label"] for push in trained["disturbance"]] == ["shove"]
    (push,) = judged["disturbance"]
    assert push["label"] == "harder" and 2.0 <= push["newtons"] <= 3.0
    assert 2.5 <= push["start_s"] <= 3.0
    assert trained["reset_variation"] and judged["reset_variation"] == []
    # The same seed is the same episode, which is what a frozen seed is for.
    again = dyn.evaluate_episode(model, played, seed=SEEDS[0], record_steps=False)
    assert again["disturbance"] == judged["disturbance"]
    assert again["total_reward"] == judged["total_reward"]


def test_a_task_with_no_spec_has_nothing_to_evaluate_under() -> None:
    _model, task = bundle()
    with pytest.raises(dyn.DynamicsError) as raised:
        dyn.evaluation_task(task)
    assert raised.value.reason == "task_has_no_success_spec"
