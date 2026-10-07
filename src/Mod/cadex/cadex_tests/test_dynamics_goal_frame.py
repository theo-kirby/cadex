# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A point goal held in a body's frame (ADR-592).

A reach target fixed in the world is the wrong question for a machine whose
base moves: the base drifts, the target stays, and the error the policy is
failed for is partly the drift. ``goal(frame=component)`` keeps the drawn
point relative to that component instead. This pins:

* **the draw**: the tries and the acceptance tests are the world ones, and
  what is kept is the accepted point in the frame body's frame, in the
  engine, the trainer and the reference runner alike;
* **the channels**: the policy reads the point as that body sees it, and a
  reward reads the tip in the same frame with
  ``observation(..., "component_position", frame=...)``;
* **the measurement**: the reach metrics read the tip in that frame at every
  frame of the trace, so the error is to where the target really was;
* **the refusals**: a frame that is the tip, a frame on a value goal, a spec
  judging in the world a goal the task holds in a frame.

None of this touches ``CadexdProtocol.OP_ARG_SPECS``.
"""

from __future__ import annotations

import math
from pathlib import Path
import random

import pytest

import CadexDynamics as dyn
import CadexEvaluation as evaluation
from test_dynamics_goal_api import BALANCE, SEEDS, _api, _scene, _source, _task
from test_dynamics_goal_model import (
    ARM_OBSERVATIONS,
    ARM_TASK,
    FORE_LENGTH_MM,
    PACE,
    REACH,
    TARGET,
    TIP,
    _stock,
    evaluate,
    made,
    model,
)
from test_success_spec_model import spec

mujoco = pytest.importorskip("mujoco")

UPPER_LENGTH_MM = 300.0
#: The forearm's target, held in the upper arm's frame: the upper arm turns
#: about the shoulder during every episode, so the target moves with it.
HELD = {**TARGET, "frame": "upper"}
HELD_TASK = {**ARM_TASK, "goal": [HELD, PACE]}
#: The forearm's far end, as the upper arm sees it.
SEEN = {"kind": "component_position", "component": "fore", "frame": "upper",
        "name": "fore_seen", "role": "privileged"}


def test_a_held_goal_names_its_frame_and_the_algorithm_says_so() -> None:
    bundle = made(HELD_TASK)["bundle"]
    held = bundle["goal"][0]
    assert held["frame"] == "upper" and isinstance(held["frame_id"], int)
    assert bundle["goal_algorithm"] == dyn.GOAL_ALGORITHM + dyn.GOAL_FRAME_ALGORITHM
    # Unseeded, the target is where the tip already is -- in the frame.
    assert math.dist(held["nominal"], [UPPER_LENGTH_MM, 0.0, 0.0]) == pytest.approx(
        FORE_LENGTH_MM, abs=1.0e-6
    )
    # A world goal is the record, and the algorithm, it always was.
    world = made()["bundle"]
    assert "frame" not in world["goal"][0] and "frame_id" not in world["goal"][0]
    assert world["goal_algorithm"] == dyn.GOAL_ALGORITHM


def test_a_held_point_is_the_world_draw_kept_in_the_frame() -> None:
    """Same seed, same tries: the held target is the world target, seen
    from the upper arm. Distance to the shoulder is a rigid invariant, and
    in the upper arm's frame the forearm's end is a forearm from the elbow."""

    world_bundle = made()["bundle"]
    held_bundle = made(HELD_TASK)["bundle"]
    compiled = model(made())
    for seed in (3, 11, 29):
        world = dyn.draw_episode_goals(mujoco, compiled, world_bundle, random.Random(seed))
        held = dyn.draw_episode_goals(mujoco, compiled, held_bundle, random.Random(seed))
        for there, here in zip(world[0]["segments"], held[0]["segments"], strict=True):
            assert math.dist(there, [0.0, 0.0, 200.0]) == pytest.approx(
                math.hypot(*here), abs=1.0e-9
            )
            assert math.dist(here, [UPPER_LENGTH_MM, 0.0, 0.0]) == pytest.approx(
                FORE_LENGTH_MM, abs=1.0e-9
            )
        assert world[1] == held[1]


def test_the_trainer_and_a_stock_mujoco_draw_the_held_goal_the_engine_drew(
    tmp_path: Path,
) -> None:
    from test_dynamics_policy_trainer import _trainer_module

    module = _trainer_module()
    prepared = made(HELD_TASK, root=tmp_path)
    bundle = prepared["bundle"]
    here, there = random.Random(17), random.Random(17)
    for _ in range(10):
        assert module.draw_goals(mujoco, model(prepared), bundle, there) == (
            dyn.draw_episode_goals(mujoco, model(prepared), bundle, here)
        )
    stock = _stock(prepared["path"], 17)
    mine = dyn.evaluate_episode(model(prepared), bundle, seed=17)
    assert stock["goal"][0]["segments"] == [
        [repr(value) for value in segment["values"]]
        for segment in mine["goal"][0]["segments"]
    ]
    assert mine["goal"][0]["frame"] == "upper"


def test_the_tip_is_read_in_the_frame_the_goal_is_held_in() -> None:
    """The reward's half: ``fore_seen`` is the forearm's origin in the upper
    arm's frame, which is the elbow wherever the shoulder turns."""

    prepared = made(HELD_TASK, observations=[*ARM_OBSERVATIONS, SEEN])
    episode = dyn.evaluate_episode(model(prepared), prepared["bundle"], seed=5)
    for step in episode["steps"]:
        seen = step["observation"]
        assert [seen["fore_seen_x"], seen["fore_seen_y"], seen["fore_seen_z"]] == (
            pytest.approx([UPPER_LENGTH_MM, 0.0, 0.0], abs=1.0e-6)
        )
        # ...and the policy reads the target in that frame too.
        assert math.dist([seen["target_x"], seen["target_y"], seen["target_z"]],
                         [UPPER_LENGTH_MM, 0.0, 0.0]) == pytest.approx(FORE_LENGTH_MM, abs=1.0e-6)


@pytest.mark.parametrize(
    ("entry", "reason"),
    [
        ({**SEEN, "kind": "component_linear_velocity"}, "observation_frame_kind"),
        ({**SEEN, "frame": "fore"}, "observation_frame_missing"),
        ({**SEEN, "frame": "nothing"}, "observation_frame_missing"),
    ],
)
def test_a_frame_the_engine_cannot_read_in_is_refused(entry, reason) -> None:
    with pytest.raises(dyn.DynamicsError) as raised:
        made(HELD_TASK, observations=[*ARM_OBSERVATIONS, entry])
    assert raised.value.reason == reason


@pytest.mark.parametrize("frame", ["fore", "nothing"])
def test_a_goal_frame_that_is_its_tip_or_absent_is_refused(frame) -> None:
    with pytest.raises(dyn.DynamicsError) as raised:
        made({**ARM_TASK, "goal": [{**TARGET, "frame": frame}, PACE]})
    assert raised.value.reason == "goal_frame_missing"


def test_a_spec_may_not_judge_in_the_world_a_goal_held_in_a_frame() -> None:
    with pytest.raises(dyn.DynamicsError) as raised:
        made(HELD_TASK, success=spec(REACH, tip=TIP, episode_seconds=4.0, goal=[TARGET, PACE]))
    assert raised.value.reason == "success_goal_mismatch"


# -- the measurement --------------------------------------------------------

def _drifting(tip_in_base: bool) -> list:
    """A base sliding 400 mm along X and turning a quarter turn over 2 s,
    with a tip either fixed in the base at (100, 0, 0) or left in the world
    where it started."""

    samples = []
    for index in range(101):
        t = index * 0.02
        yaw = 0.5 * math.pi * t / 2.0
        base = (400.0 * t / 2.0, 0.0, 50.0)
        rotation = [0.0, 0.0, math.sin(0.5 * yaw), math.cos(0.5 * yaw)]
        if tip_in_base:
            tip = (base[0] + 100.0 * math.cos(yaw), 100.0 * math.sin(yaw), 50.0)
        else:
            tip = (100.0, 0.0, 50.0)
        samples.append((t, {
            "base": {"position_mm": list(base), "rotation_xyzw": rotation},
            "tip": {"position_mm": list(tip), "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]},
        }))
    return samples


def test_a_goal_on_a_drifting_base_is_measured_where_it_was() -> None:
    """The charter's test: a target held at (100, 0, 0) in a base that slides
    and turns. A tip that rides with the base is on it at every frame; a tip
    left where the target started is measured against the target's real
    place, 400 mm and a quarter turn later."""

    rig = {"tip": {"body": "tip", "local_mm": [0.0, 0.0, 0.0]}, "arm_length_mm": 200.0}
    held = [{"start_s": 0.0, "end_s": 2.0, "target_mm": [100.0, 0.0, 0.0], "frame": "base"}]
    riding = evaluation.reach_metrics(_drifting(True), rig, held)
    assert riding["final_error_mm_max"] == pytest.approx(0.0, abs=1.0e-9)
    assert riding["time_to_target_s_max"] == 0.0
    assert riding["segments"][0]["frame"] == "base"

    left = evaluation.reach_metrics(_drifting(False), rig, held)
    # At t = 2 s the target is at (400, 100) in the world; the tip at (100, 0).
    assert left["final_error_mm_max"] == pytest.approx(math.hypot(300.0, 100.0), abs=1.0e-6)
    assert left["time_to_target_s_max"] is None

    # The same target fixed in the world reads the opposite way round.
    world = [{"start_s": 0.0, "end_s": 2.0, "target_mm": [100.0, 0.0, 50.0]}]
    assert evaluation.reach_metrics(_drifting(False), rig, world)["final_error_mm_max"] == 0.0
    assert evaluation.reach_metrics(_drifting(True), rig, world)["final_error_mm_max"] > 300.0


def test_an_evaluation_measures_a_held_target_in_its_frame() -> None:
    """The positive control end to end: the target narrowed to where a still
    policy settles, held in the upper arm, which turns from its reset pose
    to the middle of its range during the episode. Measured in the upper
    arm's frame it is reached; the same numbers read as world points are not."""

    there = {**HELD, "joint_fraction": 1.0e-4, "min_separation_mm": 0.0,
             "resample_seconds": 2.0}
    prepared = made(HELD_TASK, success=spec(REACH, tip=TIP, episode_seconds=4.0,
                                            goal=[there, PACE]))
    report = evaluate(prepared)
    assert report["summary"]["pass"] is True, report["summary"]["predicates"]
    for row in report["seeds"]:
        segments = row["detail"]["segments"]
        assert {segment["frame"] for segment in segments} == {"upper"}
        assert row["metrics"]["final_error_arm_lengths_max"] < 0.05
        # The held point is in the upper arm's frame, nowhere near the world
        # place the tip settles: a reach measured to it as a world point fails.
        assert math.dist(segments[0]["target_mm"], [UPPER_LENGTH_MM, 0.0, 0.0]) == (
            pytest.approx(FORE_LENGTH_MM, abs=1.0e-6)
        )


# -- the script surface -----------------------------------------------------

def test_the_api_carries_a_goal_frame_and_refuses_what_it_cannot_mean() -> None:
    api = _api()
    scene = _scene(api)
    base, hand = scene["components"][0], scene["components"][1]
    held = api.goal("target", kind="point", tip=hand, frame=base)
    assert held.properties["frame"] is base
    assert "frame" not in api.goal("target", kind="point", tip=hand).properties
    with pytest.raises(ValueError, match="invalid frame"):
        api.goal("target", kind="point", tip=hand, frame=hand)
    with pytest.raises(ValueError, match="invalid frame"):
        api.goal("pace", kind="value", between=[0, 1], frame=base)
    assert _task(api, scene, goals=[held]) is not None

    stranger = api.component(_source("solid9"))
    with pytest.raises(ValueError, match=r"goals\[0\].*frame"):
        _task(api, scene, goals=[api.goal("target", kind="point", tip=hand, frame=stranger)])
    with pytest.raises(ValueError, match=r"success\.goals\[0\]"):
        _task(api, scene, goals=[held], success=api.success(
            BALANCE, seeds=SEEDS,
            goals=[api.goal("target", kind="point", tip=hand, frame=stranger)]))


def test_the_api_reads_a_component_position_in_another_frame_only() -> None:
    api = _api()
    scene = _scene(api)
    base, hand = scene["components"][0], scene["components"][1]
    seen = api.observation(hand, "component_position", name="seen", frame=base,
                           role="privileged")
    assert seen.arguments[1] is base and seen.properties["role"] == "privileged"
    with pytest.raises(ValueError, match="invalid frame"):
        api.observation(hand, "component_orientation", name="seen", frame=base)
    with pytest.raises(ValueError, match="invalid frame"):
        api.observation(hand, "component_position", name="seen", frame=hand)
