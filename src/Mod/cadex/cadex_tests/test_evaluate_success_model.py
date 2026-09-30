# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``evaluate_success``: one policy, held to its task's spec, seed by seed (ADR-457).

``test_success_spec_model`` pins how a spec is declared and
``test_evaluation_metrics`` how a trace is read. This pins the step between:
the spec's seeds are played under the spec's conditions and each one comes
back as a row -- verdict, predicates, metrics, how the episode ended, the
reward term by term and every value the seed drew.

The claims worth testing rather than reading:

* **A seed is an independent episode.** A seeded episode multiplies its
  randomisation draws into the compiled model in place, so ten seeds on one
  model would each start from the last one's masses. The ten ot10 ``w2-2``
  seeds caught exactly that while this was being written: re-measured on one
  model, seeds three to ten disagreed with their retained receipts.
* **The conditions are the spec's**, not the task's: its horizon, its reset
  variation, its shoves.
* **The reward is reported and decides nothing.**
* **Nothing names a behaviour.** Which metrics are read follows from the
  rig.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import json
import re
import textwrap

import pytest

import CadexDynamics as dyn
import CadexEvaluation as evaluation
import dynamics_fixtures as fx
import dynamics_policy_fixtures as pf
from test_success_spec_model import (
    BALANCE,
    MOTORS,
    OBSERVATIONS,
    SEEDS,
    SHOVE,
    START,
    TASK,
    spec,
    walker,
)

mujoco = pytest.importorskip("mujoco")

FLAP_MOTOR = [{"joint": "wrist", "motion_type": "angular", "kind": "motor",
               "control_nmm": "0", "torque_limit_nmm": 50.0}]
#: A flat block's far corner swings further down under a tilt than a foot
#: does, so its reset pays for the tilt with more lift.
SLED_START = {**START, "height_mm_low": 5.0, "height_mm_high": 8.0}
SLED_TASK = {
    **TASK,
    "actions": [{"joint": "wrist", "motion_type": "angular", "actuator_kind": "motor"}],
    "reset_variation": [SLED_START],
}
MASS = [{"target": "mass", "label": "body_mass", "component": "body",
         "low": 0.5, "high": 1.5}]


def sled():
    """A free block lying flat on the environment's floor, with a flap to drive.

    It is the mechanism that passes: a 2 kg block a 1 N shove does not move.
    The flap has no collision shape, so whatever the policy does with it the
    block stays where it is.
    """

    return fx.build(
        [
            {
                "name": "body",
                "size": (120.0, 60.0, 40.0),
                "world": dyn.matrix_from_rotation_translation(
                    (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0), [0.0, 0.0, 20.0]
                ),
                "collision": {
                    "shapes": [fx.collision_shape("box", size_mm=[120.0, 60.0, 40.0])],
                    "mesh": None,
                },
            },
            {"name": "flap", "size": (50.0, 20.0, 6.0)},
        ],
        [
            {
                "name": "wrist", "kind": "revolute", "parent": "body", "child": "flap",
                "parent_frame": fx.frame((0.0, 0.0, 40.0), (1.0, 0.0, 0.0), -90.0),
                "child_frame": fx.frame((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), -90.0),
                "values": [0.0],
                "angle_limits_degrees": [-60.0, 60.0],
            },
        ],
    )


def prepared(success, *, mechanism=sled, motors=FLAP_MOTOR, task=SLED_TASK, still=True,
             training_seed=7, **overrides):
    """A bundle with its model's bytes and a policy container built against it.

    ``still`` zeroes the weights, so every action is the middle of its range
    -- no torque -- and what the episode shows is the mechanism and the
    conditions, not a random network.
    """

    components, joints, _placements = mechanism()
    built = dyn.build_model(components, joints, actuators=[dict(m) for m in motors])
    channels = dyn.observation_records(
        list(OBSERVATIONS), built["tree"], built["joint_records"], built["actuators"]
    )
    exported = dyn.export_mjcf(built, observations=channels)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    bundle = dyn.task_records(
        built, reloaded, {**task, **overrides, "success": success}, observations=channels
    )
    bundle["model"] = {
        "path": "outputs/model.xml", "output": "model", "bytes": len(exported["xml"]),
        "sha256": hashlib.sha256(exported["xml"]).hexdigest(),
        "mujoco_version": str(bundle["mujoco_version"]),
    }
    payload = json.dumps(bundle, indent=2, sort_keys=True).encode("utf-8")
    made = {"bundle": bundle, "xml": exported["xml"],
            "task_sha256": hashlib.sha256(payload).hexdigest()}
    container = pf.policy_container(made, seed=training_seed)
    if still:
        container = {"header": container["header"], "weights": [0.0] * len(container["weights"])}
    made["container"] = container
    return made


def evaluate(made, **arguments):
    arguments.setdefault("components", ["body"])
    return dyn.evaluate_success(made["xml"], made["bundle"], made["container"], **arguments)


# -- the rows ---------------------------------------------------------------

def test_a_block_at_rest_passes_a_balance_spec_on_every_seed() -> None:
    report = evaluate(prepared(spec(BALANCE, episode_seconds=4.0)))

    assert report["schema"] == dyn.EVALUATION_SCHEMA
    assert [row["seed"] for row in report["seeds"]] == SEEDS
    assert report["summary"]["pass"] is True
    assert report["summary"]["passed"] == SEEDS and report["summary"]["failed"] == []
    assert report["summary"]["terminations"] == {"horizon": len(SEEDS)}
    for row in report["seeds"]:
        assert row["pass"] is True and row["failing"] == []
        assert [entry["id"] for entry in row["predicates"]] == [p["id"] for p in BALANCE]
        assert all(entry["pass"] for entry in row["predicates"])
        assert row["metrics"]["completed"] == 1.0
        assert row["metrics"]["max_tilt_deg"] < 5.0
        assert row["metrics"]["recovery_s_max"] is not None
        assert row["detail"]["recovery_s"] == [row["metrics"]["recovery_s_max"]]
        assert row["episode"] == {
            "steps": 200, "duration_s": 4.0, "control_hz": 50, "termination": "",
            "terminated_step": None, "truncated": True, "solver_warnings": [],
        }
        # One frame per control step, plus the reset pose.
        assert row["frames"] == 201
    for held in report["summary"]["predicates"]:
        assert held["passed"] == len(SEEDS) and held["failed_seeds"] == []


def test_a_mechanism_that_falls_fails_and_the_report_says_which_predicate() -> None:
    """Two round feet on free hinges and no torque: it lies down."""

    report = evaluate(prepared(
        spec(BALANCE, episode_seconds=4.0), mechanism=walker, motors=MOTORS, task=TASK))

    assert report["summary"]["pass"] is False
    assert report["summary"]["failed"] == SEEDS
    by_id = {held["id"]: held for held in report["summary"]["predicates"]}
    assert by_id["upright"]["failed_seeds"] == SEEDS and by_id["upright"]["passed"] == 0
    assert by_id["upright"]["value"]["min"] > 30.0
    # It still ran to the horizon: completing is not the same as succeeding.
    assert by_id["completes"]["failed_seeds"] == []
    for row in report["seeds"]:
        assert row["pass"] is False and "upright" in row["failing"]
        failed = next(entry for entry in row["predicates"] if entry["id"] == "upright")
        assert failed["value"] > 30.0 and "over 30" in failed["why"]


def test_every_seed_must_pass() -> None:
    """A bound two seeds meet and one does not is a failed evaluation."""

    made = prepared(spec(BALANCE, episode_seconds=4.0))
    drifts = sorted(row["metrics"]["max_drift_mm"] for row in evaluate(made)["seeds"])
    assert drifts[1] < drifts[2]
    limit = (drifts[1] + drifts[2]) / 2.0
    report = evaluate(prepared(spec([{"id": "stays", "metric": "max_drift_mm", "max": limit}],
                                    episode_seconds=4.0)))
    assert len(report["summary"]["passed"]) == 2 and len(report["summary"]["failed"]) == 1
    assert report["summary"]["pass"] is False
    (held,) = report["summary"]["predicates"]
    assert held["passed"] == 2 and held["failed_seeds"] == report["summary"]["failed"]


# -- the conditions are the spec's ------------------------------------------

def test_each_seed_plays_the_specs_conditions_and_echoes_what_it_drew() -> None:
    harder = {**SHOVE, "label": "harder", "newtons_low": 2.0, "newtons_high": 3.0,
              "at_seconds_low": 2.5, "at_seconds_high": 3.0}
    made = prepared(spec(BALANCE, episode_seconds=4.0, reset_variation=[SLED_START],
                         disturbance=[harder]))
    report = evaluate(made)
    played = dyn.evaluation_task(made["bundle"])

    for row in report["seeds"]:
        alone = dyn.evaluate_episode(dyn.load_model(made["xml"]), played, seed=row["seed"],
                                     actions=lambda _step, _observation: [0.0])
        assert row["drawn"]["reset_variation"] == alone["reset_variation"]
        assert row["drawn"]["disturbance"] == alone["disturbance"]
        assert row["drawn"]["randomisation"] == alone["randomisation"] == []
        (push,) = row["drawn"]["disturbance"]
        assert push["label"] == "harder" and 2.0 <= push["newtons"] <= 3.0
        assert 2.5 <= push["start_s"] <= 3.0
        (start,) = row["drawn"]["reset_variation"]
        assert 0.0 <= start["tilt_rad"] <= 0.0524
        # The task trains for 2 s; the spec judges over 4 s.
        assert row["episode"]["duration_s"] == 4.0 and made["bundle"]["episode"]["max_steps"] == 100
        assert row["reward"]["total"] == pytest.approx(alone["total_reward"], rel=1e-12)
    # Three seeds, three different episodes.
    assert len({json.dumps(row["drawn"], sort_keys=True) for row in report["seeds"]}) == len(SEEDS)


def test_the_same_seeds_are_the_same_episodes() -> None:
    made = prepared(spec(BALANCE, episode_seconds=4.0))
    assert evaluate(made) == evaluate(made)


def test_a_seed_is_an_independent_episode_whatever_was_played_before_it() -> None:
    """The regression: randomisation is written into the model in place.

    Evaluated together, each seed must be the row it gets evaluated alone.
    On one shared compiled model the second seed's mass is its own factor
    times the first seed's, and the rewards below differ.
    """

    together = evaluate(prepared(spec(BALANCE, episode_seconds=4.0), randomisation=MASS))
    factors = [row["drawn"]["randomisation"][0]["factor"] for row in together["seeds"]]
    assert len(set(factors)) == len(SEEDS) and all(0.5 <= f <= 1.5 for f in factors)
    for row in together["seeds"]:
        alone = evaluate(prepared(spec(BALANCE, episode_seconds=4.0, seeds=[row["seed"]]),
                                  randomisation=MASS))
        assert alone["seeds"] == [row]
    backwards = evaluate(prepared(spec(BALANCE, episode_seconds=4.0, seeds=SEEDS[::-1]),
                                  randomisation=MASS))
    assert backwards["seeds"][::-1] == together["seeds"]


# -- how it ended, and what it was paid -------------------------------------

def test_a_termination_is_reported_as_the_cause_and_fails_completion() -> None:
    sunk = [{"label": "sunk", "expression": "body_z", "below": 100.0}]
    report = evaluate(prepared(spec(BALANCE, episode_seconds=4.0), termination=sunk))

    assert report["summary"]["terminations"] == {"sunk": len(SEEDS)}
    assert report["summary"]["pass"] is False
    for row in report["seeds"]:
        assert row["episode"]["termination"] == "sunk" and row["episode"]["truncated"] is False
        assert row["episode"]["steps"] == 1 and row["episode"]["terminated_step"] == 0
        assert row["metrics"]["completed"] == 0.0
        # Cut short before the shove: nothing to recover from, so not measured,
        # and a metric that was not measured fails.
        assert row["metrics"]["recovery_s_max"] is None
        assert {"completes", "recovers"} <= set(row["failing"])
    recovers = next(h for h in report["summary"]["predicates"] if h["id"] == "recovers")
    assert recovers["value"] is None and recovers["passed"] == 0


def test_a_simulation_that_went_unstable_voids_the_seed() -> None:
    """MuJoCo resets the state on a bad acceleration and counts a warning.

    The poses after the reset are the keyframe's -- level, in place, at rest
    -- so a predicate read from them can be met by a mechanism that was
    flung across the room a moment before. The seed is void whatever its
    predicates say, and a void seed has not passed.
    """

    wild = [{**FLAP_MOTOR[0], "torque_limit_nmm": 200000.0}]
    report = evaluate(prepared(spec(BALANCE[:3], episode_seconds=4.0), still=False, motors=wild))

    void = [row for row in report["seeds"] if row["void"]]
    assert [row["seed"] for row in void] == report["summary"]["void"] == [1101, 1102]
    for row in void:
        assert row["episode"]["solver_warnings"] == [{"warning": "mjWARN_BADQACC", "count": 1}]
        assert row["void"] == "the simulation went unstable: MuJoCo warned mjWARN_BADQACC x1"
        assert row["pass"] is False
        # Void is not a predicate: it is said once, beside them.
        assert row["void"] not in row["failing"]
        assert all(entry["id"] in {"completes", "upright", "in_place"} for entry in row["predicates"])
    assert report["summary"]["passed"] == [1103] and report["summary"]["pass"] is False
    sound = report["seeds"][2]
    assert sound["void"] == "" and sound["episode"]["solver_warnings"] == []
    # ...and a sound evaluation says so, seed by seed.
    calm = evaluate(prepared(spec(BALANCE, episode_seconds=4.0)))
    assert calm["summary"]["void"] == [] and all(row["void"] == "" for row in calm["seeds"])


def test_the_reward_is_decomposed_term_by_term_and_decides_nothing() -> None:
    made = prepared(spec(BALANCE, episode_seconds=4.0))
    report = evaluate(made)

    for row in report["seeds"]:
        terms = {term["label"]: term for term in row["reward"]["terms"]}
        assert list(terms) == ["height", "still"]
        assert sum(t["total"] for t in terms.values()) == pytest.approx(row["reward"]["total"])
        assert row["reward"]["per_step"] == pytest.approx(row["reward"]["total"] / 200)
        assert terms["height"]["per_step"] == pytest.approx(terms["height"]["total"] / 200)
    summary = report["summary"]["reward"]
    assert [term["label"] for term in summary["terms"]] == ["height", "still"]
    assert summary["total"]["min"] <= summary["total"]["median"] <= summary["total"]["max"]

    # The same episodes under a reward a hundred times larger: every verdict
    # and every metric is unchanged.
    richer = copy.deepcopy(made)
    for term in richer["bundle"]["reward"]:
        term["weight"] = float(term["weight"]) * 100.0
    again = evaluate(richer)
    assert again["seeds"][0]["reward"]["total"] == pytest.approx(
        report["seeds"][0]["reward"]["total"] * 100.0)
    assert [row["metrics"] for row in again["seeds"]] == [row["metrics"] for row in report["seeds"]]
    assert [row["predicates"] for row in again["seeds"]] == [
        row["predicates"] for row in report["seeds"]]


# -- the trace each seed leaves ---------------------------------------------

def test_each_seed_leaves_a_trace_the_reader_measures_to_the_same_numbers() -> None:
    made = prepared(spec(BALANCE, episode_seconds=4.0))
    documents: dict[int, dict] = {}
    report = evaluate(made, components=["body", "flap"],
                      identity={"policy_sha256": "p" * 64, "task_sha256": made["task_sha256"],
                                "model_sha256": made["bundle"]["model"]["sha256"]},
                      on_trace=lambda seed, document: documents.__setitem__(seed, document))

    assert sorted(documents) == SEEDS
    rig = dyn.evaluation_rig(dyn.load_model(made["xml"]))
    played = dyn.evaluation_task(made["bundle"])
    for row in report["seeds"]:
        document = json.loads(json.dumps(documents[row["seed"]], allow_nan=False))
        assert document["schema"] == "cadex-assembly-simulation-trace-v1"
        assert document["component_outputs"] == ["body", "flap"]
        assert document["frames"][0]["frame_kind"] == "input"
        assert document["dynamics"]["steps_per_frame"] == 1
        assert document["policy"]["seed"] == row["seed"]
        assert document["policy"]["disturbance"] == row["drawn"]["disturbance"]
        trace = evaluation.read_trace(document)
        assert trace["digests"] == {"policy_sha256": "p" * 64, "mjcf_sha256":
                                    made["bundle"]["model"]["sha256"],
                                    "task_sha256": made["task_sha256"]}
        assert trace["episode"]["seed"] == row["seed"]
        assert trace["episode"]["duration_s"] == 4.0 and trace["episode"]["truncated"] is True
        shoves = [(draw["start_s"], entry["duration_s"]) for entry, draw in
                  zip(played["disturbance"], document["policy"]["disturbance"])]
        again = evaluation.measure(trace["samples"], trace["episode"], rig, shoves=shoves)
        assert again["metrics"] == row["metrics"]


def test_a_body_the_rig_reads_is_in_the_trace_even_when_the_caller_left_it_out() -> None:
    made = prepared(spec(BALANCE + [{"id": "sinks", "metric": "foot_lowest_hip_heights_min",
                                     "min": -10.0}], feet=["front", "rear"],
                         episode_seconds=4.0),
                    mechanism=walker, motors=MOTORS, task=TASK)
    documents = []
    evaluate(made, components=[], on_trace=lambda _seed, document: documents.append(document))
    assert documents[0]["component_outputs"] == ["body", "front", "rear"]


# -- what is read follows from the rig --------------------------------------

def test_the_metric_families_follow_from_the_rig_not_from_a_behaviour() -> None:
    posture = {name for name, (family, _needs) in evaluation.METRICS.items()
               if family == "posture"}
    gait = {name for name, (family, _needs) in evaluation.METRICS.items()
            if family == "gait" and "goal" not in _needs}

    flat = evaluate(prepared(spec(BALANCE, episode_seconds=4.0)))["seeds"][0]
    assert posture <= set(flat["metrics"]) and not gait & set(flat["metrics"])
    assert "feet" not in flat["detail"]

    footed = evaluate(prepared(
        spec(BALANCE + [{"id": "steps", "metric": "steps_min", "min": 1}],
             feet=["front", "rear"], episode_seconds=4.0),
        mechanism=walker, motors=MOTORS, task=TASK))["seeds"][0]
    assert posture | gait <= set(footed["metrics"])
    assert sorted(footed["detail"]["feet"]) == ["front", "rear"]
    assert set(footed["metrics"]) <= set(evaluation.METRICS)


def test_the_evaluation_names_no_behaviour() -> None:
    """One path for every spec: the code says nothing about what is being done."""

    source = textwrap.dedent(inspect.getsource(dyn.evaluate_success))
    tree = ast.parse(source)
    function = tree.body[0]
    function.body = function.body[1:]  # the docstring may say what it likes
    code = ast.unparse(tree)
    assert not re.search(r"walk|gait|balanc|reach|quadruped|biped|arm\b", code, re.IGNORECASE)


# -- refusals ---------------------------------------------------------------

def test_a_task_with_no_spec_is_refused() -> None:
    made = prepared(spec(BALANCE, episode_seconds=4.0))
    del made["bundle"]["success"]
    with pytest.raises(dyn.DynamicsError) as raised:
        evaluate(made)
    assert raised.value.reason == "task_has_no_success_spec"


def test_an_evaluation_seed_the_policy_was_trained_with_is_refused() -> None:
    made = prepared(spec(BALANCE, episode_seconds=4.0), training_seed=SEEDS[1])
    assert made["container"]["header"]["training"]["seed"] == SEEDS[1]
    with pytest.raises(dyn.DynamicsError) as raised:
        evaluate(made)
    assert raised.value.reason == "evaluation_seed_is_the_training_seed"
    assert raised.value.observed == {"training_seed": SEEDS[1], "evaluation_seeds": SEEDS}
    assert "do not change the spec's seeds" in raised.value.correction


def test_a_rollout_echoes_its_reset_and_shove_draws() -> None:
    """``rollout_policy``'s episode summary carries what the seed drew."""

    made = prepared(spec(BALANCE, episode_seconds=4.0))
    played = dyn.evaluation_task(made["bundle"])
    run = dyn.rollout_policy(dyn.load_model(made["xml"]), played, made["container"],
                             components=["body"], frames_per_second=50, seed=SEEDS[0])
    alone = dyn.evaluate_episode(dyn.load_model(made["xml"]), played, seed=SEEDS[0],
                                 record_steps=False)
    assert run["episode"]["reset_variation"] == alone["reset_variation"] != []
    assert run["episode"]["disturbance"] == alone["disturbance"] != []
    unseeded = dyn.rollout_policy(dyn.load_model(made["xml"]), played, made["container"],
                                  components=["body"], frames_per_second=50)
    assert unseeded["episode"]["reset_variation"] == [] == unseeded["episode"]["disturbance"]
