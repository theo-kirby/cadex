# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A task that says where to go (ADR-462).

A goal is a number or a place drawn per episode -- a speed to walk at, a
point to reach -- and optionally drawn again while the episode runs. This
pins what the engine does with one:

* **the bundle** carries it resolved to addresses and SI, with the algorithm
  that draws it, and a task with no goal is the bundle, and the digest, it
  always was;
* **the draw** continues a seed's stream after the disturbance draws, so a
  goal moves no reset and no shove, and a point goal is a place the tip can
  really be;
* **the episode** shows the goal to the policy, lets the reward name it and
  changes it on a control step;
* **the reference runner** -- stock MuJoCo, no Cadex -- reproduces all of
  that from the file;
* **the trace** records it frame by frame;
* **the success spec** reads the commanded speed and the target from it, by
  kind, and nothing tells the evaluation a goal from outside.

``test_dynamics_goal_trainer`` holds the trainer to the same numbers.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys

import pytest

import CadexDynamics as dyn
import CadexEvaluation as evaluation
import dynamics_fixtures as fx
import dynamics_policy_fixtures as pf
import dynamics_task_episode as runner
from test_success_spec_model import (
    MOTORS as WALKER_MOTORS,
    OBSERVATIONS as WALKER_OBSERVATIONS,
    SEEDS,
    TASK as WALKER_TASK,
    spec,
    walker,
)

mujoco = pytest.importorskip("mujoco")

RUNNER = Path(runner.__file__).resolve()

FORE_LENGTH_MM = 220.0
ARM_SERVOS = [
    {"joint": joint, "motion_type": "angular", "kind": "position",
     "control_deg": "0", "stiffness_nmm_per_deg": 4000.0,
     "damping_nmms_per_deg": 120.0}
    for joint in ("shoulder", "elbow")
]
ARM_OBSERVATIONS = [
    {"kind": "position", "joint": "elbow", "motion_type": "angular", "name": "elbow_angle"},
    {"kind": "centre_of_mass", "component": "fore", "name": "hand"},
]
#: A point the forearm's far end can reach, drawn again halfway through.
TARGET = {
    "name": "target", "kind": "point", "tip": "fore",
    "tip_offset_mm": [FORE_LENGTH_MM, 0.0, 0.0], "joint_fraction": 0.8,
    "min_z_mm": 50.0, "min_separation_mm": 80.0, "resample_seconds": 1.0,
}
PACE = {"name": "pace", "kind": "value", "low": 1.0, "high": 2.0}
ARM_TASK = {
    "label": "reach",
    "actions": [
        {"joint": joint, "motion_type": "angular", "actuator_kind": "position"}
        for joint in ("shoulder", "elbow")
    ],
    "reward": [
        {"label": "near",
         "expression": "-sqrt((hand_x - target_x)**2 + (hand_z - target_z)**2)",
         "weight": 1.0e-3},
        {"label": "paced", "expression": "pace", "weight": 1.0},
    ],
    "termination": [],
    "episode_seconds": 2.0,
    "control_hz": 50,
    "randomisation": [],
    "goal": [TARGET, PACE],
}
COMMAND = {"name": "command", "kind": "speed", "low": 40.0, "high": 80.0}
WALK_TASK = {
    **WALKER_TASK,
    "label": "walk",
    "reward": [
        {"label": "height", "expression": "body_z", "weight": 1.0e-3},
        {"label": "asked", "expression": "command", "weight": 1.0e-3},
    ],
    "goal": [COMMAND],
}
REACH = [
    {"id": "arrives", "metric": "final_error_arm_lengths_max", "max": 0.05},
    {"id": "in_time", "metric": "time_to_target_s_max", "max": 2.0},
]
TIP = {"body": "fore", "local_mm": [FORE_LENGTH_MM, 0.0, 0.0]}


def arm():
    return fx.two_link_arm(limits=True)


def made(task=ARM_TASK, *, mechanism=arm, motors=ARM_SERVOS,
         observations=ARM_OBSERVATIONS, root: Path | None = None, **overrides):
    """One bundle, its model's bytes, and a still policy built against it.

    With ``root`` the two files are written in the worker's layout, so the
    reference runner can read them from disk.
    """

    components, joints, _placements = mechanism()
    built = dyn.build_model(components, joints, actuators=[dict(m) for m in motors])
    channels = dyn.observation_records(
        list(observations), built["tree"], built["joint_records"], built["actuators"]
    )
    exported = dyn.export_mjcf(built, observations=channels)
    bundle = dyn.task_records(
        built, dyn.load_model(exported["xml"]), {**task, **overrides}, observations=channels
    )
    bundle["model"] = {
        "path": "outputs/model-model.xml", "output": "model",
        "bytes": len(exported["xml"]),
        "sha256": hashlib.sha256(exported["xml"]).hexdigest(),
        "mujoco_version": str(bundle["mujoco_version"]),
    }
    payload = json.dumps(bundle, indent=2, sort_keys=True).encode("utf-8")
    result = {"bundle": bundle, "xml": exported["xml"],
              "task_sha256": hashlib.sha256(payload).hexdigest()}
    if root is not None:
        (root / "outputs").mkdir(parents=True, exist_ok=True)
        (root / "outputs" / "model-model.xml").write_bytes(exported["xml"])
        (root / "outputs" / "job-task.json").write_bytes(payload)
        result["path"] = root / "outputs" / "job-task.json"
    container = pf.policy_container(result, seed=7)
    # Zeroed weights: every action is the middle of its range, so what an
    # episode shows is the mechanism and the conditions.
    result["container"] = {"header": container["header"],
                           "weights": [0.0] * len(container["weights"])}
    return result


def model(prepared):
    return dyn.load_model(prepared["xml"])


def refusal(task=ARM_TASK, **arguments) -> dyn.DynamicsError:
    with pytest.raises(dyn.DynamicsError) as raised:
        made(task, **arguments)
    return raised.value


def goals(*entries, base=ARM_TASK):
    return {**base, "goal": [dict(entry) for entry in entries]}


# -- the bundle -------------------------------------------------------------

def test_a_task_with_no_goal_is_the_bundle_it_always_was() -> None:
    """No key, no algorithm, the same digest -- so every policy trained
    before a task could state a goal still names its task."""

    plain = {key: value for key, value in ARM_TASK.items() if key != "goal"}
    plain["reward"] = [{"label": "up", "expression": "hand_z", "weight": 1.0e-3}]
    absent = made(plain)["bundle"]
    empty = made({**plain, "goal": []})["bundle"]

    assert "goal" not in absent and "goal_algorithm" not in absent
    assert "goal" not in empty and "goal_algorithm" not in empty
    assert dyn.task_semantic_digest(absent) == dyn.task_semantic_digest(empty)
    assert dyn.policy_channels(absent) == dyn._task_channels(absent) == [
        "elbow_angle", "hand_x", "hand_y", "hand_z"
    ]
    # The stated reset-and-shove stream is a semantic field of every bundle
    # ever written. The goal draws have a text of their own for that reason,
    # and this one does not move.
    assert hashlib.sha256(dyn.EPISODE_VARIATION_ALGORITHM.encode()).hexdigest() == (
        "72216f869539226ee35a2471e64d0e31e8896eae7bc60761c4028ae036d119de"
    )
    assert absent["variation_algorithm"] == dyn.EPISODE_VARIATION_ALGORITHM
    assert dyn.evaluate_episode(model(made(plain)), absent, seed=3)["goal"] == []


def test_a_goal_lands_in_the_bundle_resolved_and_self_contained() -> None:
    bundle = made()["bundle"]
    target, pace = bundle["goal"]

    assert bundle["goal_algorithm"] == dyn.GOAL_ALGORITHM
    assert target["channels"] == ["target_x", "target_y", "target_z"]
    assert (target["kind"], target["unit"], target["scale"]) == ("point", "mm", 1000.0)
    # One second at 50 Hz over a two second episode.
    assert (target["resample_steps"], target["segments"]) == (50, 2)
    assert target["body"] == "fore" and target["local_m"] == pytest.approx([0.22, 0.0, 0.0])
    assert target["min_z_m"] == pytest.approx(0.05)
    assert target["min_separation_m"] == pytest.approx(0.08)
    assert target["attempts"] == dyn.GOAL_POINT_ATTEMPTS
    # Every driven joint, in action order, over the middle 80 % of its own
    # range -- addresses and radians, so a draw looks nothing up.
    assert [joint["joint"] for joint in target["joints"]] == ["shoulder", "elbow"]
    for joint, (low, high) in zip(target["joints"], ([-95.0, 95.0], [-140.0, 5.0])):
        middle, half = 0.5 * (low + high), 0.4 * (high - low)
        assert math.degrees(joint["low"]) == pytest.approx(middle - half, abs=1.0e-3)
        assert math.degrees(joint["high"]) == pytest.approx(middle + half, abs=1.0e-3)
    # The arm is solved straight out: upper 300 mm, forearm 220 mm, 200 mm up.
    assert target["start_m"] == pytest.approx([0.52, 0.0, 0.2], abs=1.0e-6)
    assert target["nominal"] == pytest.approx([520.0, 0.0, 200.0], abs=1.0e-3)
    assert target["resting_contacts"] == []

    assert pace == {
        "label": "pace", "name": "pace", "kind": "value", "channels": ["pace"],
        "resample_steps": 0, "segments": 1, "unit": "", "low": 1.0, "high": 2.0,
        "nominal": [1.5],
    }
    speed = made(WALK_TASK, mechanism=walker, motors=WALKER_MOTORS,
                 observations=WALKER_OBSERVATIONS)["bundle"]["goal"][0]
    assert (speed["kind"], speed["unit"], speed["channels"]) == ("speed", "mm/s", ["command"])
    assert dyn.GOAL_KINDS == ("value", "speed", "point")


def test_the_policy_reads_every_goal_after_its_sensor_channels() -> None:
    """A goal is what the robot is told, so it is never privileged -- and it
    sits last, so a task that gains one keeps every address it had."""

    hidden = [dict(ARM_OBSERVATIONS[0]), {**ARM_OBSERVATIONS[1], "role": "privileged"}]
    bundle = made(observations=hidden)["bundle"]

    told = ["target_x", "target_y", "target_z", "pace"]
    assert dyn.goal_channels(bundle) == told
    assert dyn.policy_channels(bundle) == ["elbow_angle"] + told
    assert dyn._task_channels(bundle) == ["elbow_angle", "hand_x", "hand_y", "hand_z"] + told
    # A goal is not a sensor, so it is not among the inputs a robot cannot read.
    assert not set(told) & set(dyn.ungrounded_policy_channels(bundle))


def test_a_goal_is_part_of_what_the_task_is() -> None:
    """Change what is asked and the policy was trained on something else."""

    one = made()["bundle"]
    wider = made(goals(TARGET, {**PACE, "high": 3.0}))["bundle"]
    held = made(goals({**TARGET, "resample_seconds": None}, PACE))["bundle"]

    assert {"goal", "goal_algorithm"} <= set(dyn.TASK_SEMANTIC_FIELDS)
    assert dyn.task_semantic_digest(one) != dyn.task_semantic_digest(wider)
    assert dyn.task_differences(one, wider) == ["goal[1].high: 2.0 here, 3.0 there",
                                               "goal[1].nominal[0]: 1.5 here, 2.0 there"]
    assert any(line.startswith("goal[0].resample_steps")
               for line in dyn.task_differences(one, held))


# -- what is refused --------------------------------------------------------

@pytest.mark.parametrize(
    "entries, reason",
    [
        ([{**PACE, "kind": "pose"}], "unknown_goal_kind"),
        ([{**PACE, "name": "hand_x"}], "duplicate_goal_channel"),
        ([TARGET, {**PACE, "name": "target_z"}], "duplicate_goal_channel"),
        ([{**PACE, "kind": "speed"}, {**PACE, "name": "other", "kind": "speed"}],
         "duplicate_goal_kind"),
        ([TARGET, {**TARGET, "name": "second"}], "duplicate_goal_kind"),
        ([{**PACE, "low": 2.0, "high": 1.0}], "malformed_goal"),
        ([{**PACE, "resample_seconds": 0.03}], "goal_resample_between_control_steps"),
        ([{**PACE, "resample_seconds": 0.001}], "goal_resample_between_control_steps"),
        ([{**TARGET, "tip": "nothing"}], "goal_tip_missing"),
        ([{**TARGET, "joint_fraction": 0.0}], "malformed_goal"),
        ([{**PACE, "name": f"v{index}"} for index in range(dyn.MAXIMUM_GOALS + 1)],
         "too_many_goals"),
    ],
)
def test_a_goal_the_engine_cannot_keep_is_refused_by_name(entries, reason) -> None:
    error = refusal(goals(*entries, base={**ARM_TASK, "reward": [
        {"label": "up", "expression": "hand_z", "weight": 1.0e-3}]}))
    assert error.reason == reason


def test_a_point_no_pose_can_reach_is_refused_when_the_task_is_built() -> None:
    """Not by an evaluation seed and not by a training run: the refusal is
    at the declaration, with what rejected the tries."""

    plain = {**ARM_TASK, "reward": [{"label": "up", "expression": "hand_z", "weight": 1.0e-3}]}
    too_high = refusal(goals({**TARGET, "min_z_mm": 5000.0}, base=plain))
    assert too_high.reason == "goal_draw_exhausted"
    assert too_high.observed["below_min_z"] == dyn.GOAL_POINT_ATTEMPTS
    assert "min_z_mm" in too_high.correction

    too_far = refusal(goals({**TARGET, "min_z_mm": None, "min_separation_mm": 5000.0},
                            base=plain))
    assert too_far.reason == "goal_draw_exhausted"
    assert too_far.observed["too_close"] == dyn.GOAL_POINT_ATTEMPTS


def test_a_point_goal_needs_limits_on_every_driven_joint() -> None:
    """A swing-up hinge turns without limit, so there is no range to draw a
    pose from."""

    components, joints, _ = fx.build(
        [{"name": "post", "grounded": True, "size": (60.0, 60.0, 300.0)},
         {"name": "link", "size": (200.0, 30.0, 15.0)}],
        [{"name": "hinge", "kind": "revolute", "parent": "post", "child": "link",
          "parent_frame": fx.frame((0.0, 0.0, 150.0), (1.0, 0.0, 0.0), -90.0),
          "child_frame": fx.frame((-100.0, 0.0, 0.0), (1.0, 0.0, 0.0), -90.0),
          "values": [0.0]}],
    )
    task = {**pf.SWING_UP_TASK,
            "goal": [{"name": "target", "kind": "point", "tip": "link"}]}
    error = refusal(
        task, mechanism=lambda: (components, joints, None),
        motors=[{"joint": "hinge", "motion_type": "angular", "kind": "motor",
                 "control_nmm": "0", "torque_limit_nmm": 2000.0}],
        observations=pf.SWING_UP_OBSERVATIONS,
    )
    assert error.reason == "goal_joint_unlimited"


# -- the draw ---------------------------------------------------------------

def test_a_drawn_point_is_a_place_the_tip_can_be() -> None:
    """Each target is the tip at a configuration inside the drawn ranges,
    over the floor it states and apart from where that segment starts."""

    prepared = made()
    bundle, compiled = prepared["bundle"], model(prepared)
    target = bundle["goal"][0]
    rng = random.Random(11)
    seen = set()
    for _ in range(40):
        drawn = dyn.draw_episode_goals(mujoco, compiled, bundle, rng)
        assert [row["label"] for row in drawn] == ["target", "pace"]
        first, second = drawn[0]["segments"]
        (pace,) = drawn[1]["segments"]
        assert 1.0 <= pace[0] <= 2.0
        previous = [value * 1000.0 for value in target["start_m"]]
        for point in (first, second):
            assert point[2] >= 50.0
            assert math.dist(point, previous) >= 80.0
            # The plane the arm moves in, and within its reach of the shoulder.
            assert point[1] == pytest.approx(0.0, abs=1.0e-9)
            assert math.dist(point, [0.0, 0.0, 200.0]) <= 300.0 + FORE_LENGTH_MM + 1.0e-6
            previous = point
            seen.add(tuple(round(value, 3) for value in point))
    assert len(seen) == 80


def test_a_goal_moves_no_other_draw_of_a_seed() -> None:
    """The goal draws come last in a seed's stream, so a seed's reset and
    shove are the ones it always drew whether or not the task has a goal."""

    arguments = {"mechanism": walker, "motors": WALKER_MOTORS,
                 "observations": WALKER_OBSERVATIONS}
    without = made({**WALK_TASK, "goal": [], "reward": WALKER_TASK["reward"]}, **arguments)
    with_goal = made(WALK_TASK, **arguments)
    for seed in SEEDS:
        plain = dyn.evaluate_episode(model(without), without["bundle"], seed=seed)
        asked = dyn.evaluate_episode(model(with_goal), with_goal["bundle"], seed=seed)
        assert asked["reset_variation"] == plain["reset_variation"]
        assert asked["disturbance"] == plain["disturbance"]
        assert asked["randomisation"] == plain["randomisation"]
        (command,) = asked["goal"]
        assert 40.0 <= command["segments"][0]["values"][0] <= 80.0


def test_an_episodes_goals_are_the_streams_next_draws() -> None:
    """``draw_episode_goals`` on the stream an episode leaves behind is what
    the episode reports -- the algorithm's text, held to."""

    prepared = made(WALK_TASK, mechanism=walker, motors=WALKER_MOTORS,
                    observations=WALKER_OBSERVATIONS)
    bundle = prepared["bundle"]
    rng = random.Random(1101)
    dyn.draw_episode_variation(bundle, rng)
    expected = dyn.draw_episode_goals(mujoco, model(prepared), bundle, rng)
    episode = dyn.evaluate_episode(model(prepared), bundle, seed=1101)
    assert [[segment["values"] for segment in row["segments"]] for row in episode["goal"]] == [
        row["segments"] for row in expected
    ]


# -- the episode ------------------------------------------------------------

def test_the_policy_sees_the_goal_and_the_reward_names_it() -> None:
    prepared = made()
    bundle = prepared["bundle"]
    shown = []

    def watching(step, observation):
        shown.append(dict(observation))
        return [0.0, -67.5]

    episode = dyn.evaluate_episode(model(prepared), bundle, actions=watching, seed=5)
    target, pace = episode["goal"]
    first, second = (segment["values"] for segment in target["segments"])
    value = pace["segments"][0]["values"][0]

    assert [segment["start_step"] for segment in target["segments"]] == [0, 50]
    assert [(segment["start_s"], segment["end_s"]) for segment in target["segments"]] == [
        (0.0, 1.0), (1.0, 2.0)
    ]
    assert first != second
    for step, (observed, landed) in enumerate(zip(shown, episode["steps"], strict=True)):
        held = first if step < 50 else second
        # What the policy acted on...
        assert [observed[name] for name in ("target_x", "target_y", "target_z")] == held
        assert observed["pace"] == value
        # ...and the goal that action is scored against: the same one, so
        # step 49 lands under the first target although the next step reads
        # the second.
        assert [landed["observation"][name]
                for name in ("target_x", "target_y", "target_z")] == held
        near, paced = landed["reward_terms"]
        assert near["value"] == -math.sqrt(
            (landed["observation"]["hand_x"] - held[0]) ** 2
            + (landed["observation"]["hand_z"] - held[2]) ** 2
        )
        assert paced["value"] == value


def test_an_unseeded_episode_holds_each_goals_nominal() -> None:
    """The middle of a range and the point the tip already occupies, for the
    whole episode: the episode the engine plays when a task is built."""

    prepared = made()
    episode = dyn.evaluate_episode(model(prepared), prepared["bundle"])
    target, pace = episode["goal"]
    assert [segment["values"] for segment in target["segments"]] == [
        prepared["bundle"]["goal"][0]["nominal"]
    ]
    assert target["segments"][0]["end_s"] == 2.0
    assert pace["segments"][0]["values"] == [1.5]
    assert {step["observation"]["pace"] for step in episode["steps"]} == {1.5}


def test_goal_values_are_the_last_segment_that_has_started() -> None:
    schedule = [{"channels": ["a"], "segments": [
        {"start_step": 0, "values": [1.0]}, {"start_step": 3, "values": [2.0]},
        {"start_step": 6, "values": [3.0]}]}]
    assert [dyn.goal_values(schedule, step)["a"] for step in range(9)] == [
        1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 3.0, 3.0, 3.0
    ]
    # Past the horizon it is still the last one: an endless episode, and the
    # frame after the final step.
    assert dyn.goal_values(schedule, 10_000)["a"] == 3.0


# -- the reference runner ---------------------------------------------------

def _stock(bundle_path: Path, seed=None) -> dict:
    environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    command = [sys.executable, "-P", str(RUNNER), str(bundle_path)]
    if seed is not None:
        command.append(str(seed))
    completed = subprocess.run(command, capture_output=True, text=True,
                               env=environment, check=False)
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


@pytest.mark.parametrize("seed", [None, 17])
def test_a_stock_mujoco_draws_the_goals_the_engine_drew(tmp_path: Path, seed) -> None:
    """The bundle says enough: a process with no Cadex on its path reads the
    same targets out of the same seed and scores the same rewards against
    them, every number compared as text."""

    prepared = made(root=tmp_path)
    there = _stock(prepared["path"], seed)
    here = dyn.evaluate_episode(model(prepared), prepared["bundle"], seed=seed)

    assert there["cadex_importable"] is False
    assert there["goal"] == [
        {"label": row["label"],
         "segments": [[repr(value) for value in segment["values"]]
                      for segment in row["segments"]]}
        for row in here["goal"]
    ]
    assert there["total_reward"] == repr(here["total_reward"])
    for mine, yours in zip(here["steps"], there["steps"], strict=True):
        assert yours["observation"] == {
            name: repr(value) for name, value in mine["observation"].items()
        }
        assert yours["reward"] == repr(mine["reward"])
    if seed is not None:
        assert len(there["goal"][0]["segments"]) == 2
        assert _stock(prepared["path"], 18)["goal"] != there["goal"]


# -- the trace --------------------------------------------------------------

def test_a_rollouts_frames_carry_the_goal_in_force() -> None:
    prepared = made()
    run = dyn.rollout_policy(
        model(prepared), prepared["bundle"], prepared["container"],
        components=["upper", "fore"], frames_per_second=50, seed=5,
    )
    assert run["goal_channels"] == [
        {"channel": "target_x", "goal": "target", "kind": "point", "unit": "mm"},
        {"channel": "target_y", "goal": "target", "kind": "point", "unit": "mm"},
        {"channel": "target_z", "goal": "target", "kind": "point", "unit": "mm"},
        {"channel": "pace", "goal": "pace", "kind": "value", "unit": ""},
    ]
    target, pace = run["episode"]["goal"]
    first, second = (segment["values"] for segment in target["segments"])
    value = pace["segments"][0]["values"]
    timed = [frame for frame in run["frames"] if frame["frame_kind"] == "solver_output"]
    assert len(timed) == 101
    assert "goal" not in run["frames"][0]
    for frame in timed:
        # A frame on the boundary shows the target that starts there; the
        # frame after the last step keeps the last step's.
        held = first if frame["nominal_time_s"] < 1.0 - 1.0e-9 else second
        assert frame["goal"] == held + value


def test_a_rollout_of_a_task_with_no_goal_is_the_trace_it_always_was() -> None:
    plain = {**ARM_TASK, "goal": [],
             "reward": [{"label": "up", "expression": "hand_z", "weight": 1.0e-3}]}
    prepared = made(plain)
    run = dyn.rollout_policy(
        model(prepared), prepared["bundle"], prepared["container"],
        components=["upper", "fore"], frames_per_second=50, seed=5,
    )
    assert "goal_channels" not in run and "goal" not in run["episode"]
    assert all("goal" not in frame for frame in run["frames"])


# -- the success spec reads the goal ----------------------------------------

def evaluate(prepared, **arguments):
    arguments.setdefault("components", [])
    return dyn.evaluate_success(
        prepared["xml"], prepared["bundle"], prepared["container"], **arguments
    )


def test_a_gait_is_tracked_against_the_speed_the_episode_commanded() -> None:
    """``speed_ratio`` is the measured speed over the drawn command, and the
    command comes out of the episode, not off a command line."""

    tracked = spec(
        [{"id": "tracks", "metric": "speed_ratio", "min": 0.75, "max": 1.25},
         {"id": "straight", "metric": "lateral_ratio", "max": 0.25}],
        feet=["front", "rear"], episode_seconds=4.0,
    )
    prepared = made(WALK_TASK, mechanism=walker, motors=WALKER_MOTORS,
                    observations=WALKER_OBSERVATIONS, success=tracked)
    documents = []
    report = evaluate(prepared, on_trace=lambda _seed, document: documents.append(document))

    assert report["spec"]["goal"] == prepared["bundle"]["success"]["goal"]
    commands = set()
    for row, document in zip(report["seeds"], documents, strict=True):
        (command,) = row["drawn"]["goal"]
        asked = command["segments"][0]["values"][0]
        assert 40.0 <= asked <= 80.0
        commands.add(asked)
        forward = row["metrics"]["mean_forward_speed_mm_s"]
        assert row["metrics"]["speed_ratio"] == forward / asked
        assert row["metrics"]["lateral_ratio"] == (
            abs(row["metrics"]["mean_lateral_speed_mm_s"]) / asked
        )
        # Two free hinges and no torque: it lies down, and the spec says so.
        assert "tracks" in row["failing"]
        # The trace is a record of what was asked, frame by frame.
        assert document["goal_channels"] == [
            {"channel": "command", "goal": "command", "kind": "speed", "unit": "mm/s"}
        ]
        assert document["policy"]["goal"] == row["drawn"]["goal"]
        assert {frame["goal"][0] for frame in document["frames"][1:]} == {asked}
    assert len(commands) == len(SEEDS)


def test_a_reach_is_measured_to_the_targets_the_episode_drew() -> None:
    judged = spec(REACH, tip=TIP, episode_seconds=4.0)
    prepared = made(success=judged)
    report = evaluate(prepared)

    assert prepared["bundle"]["success"]["goal"][0]["segments"] == 4
    for row in report["seeds"]:
        target = row["drawn"]["goal"][0]
        assert [segment["start_s"] for segment in target["segments"]] == [0.0, 1.0, 2.0, 3.0]
        measured = row["detail"]["segments"]
        assert [entry["target_mm"] for entry in measured] == [
            segment["values"] for segment in target["segments"]
        ]
        assert row["metrics"]["final_error_mm_max"] == max(
            entry["final_error_mm"] for entry in measured
        )
        # A still policy holds the middle of each joint's range and reaches
        # for nothing: the targets are 80 mm and more from where it starts.
        assert row["pass"] is False and "arrives" in row["failing"]
        assert row["metrics"]["final_error_arm_lengths_max"] > 0.05
    assert report["summary"]["pass"] is False


def test_a_reach_that_arrives_passes() -> None:
    """The positive control. The spec narrows the task's target to the one
    pose a still policy holds -- the middle of every joint's range -- so
    every drawn target is where the servos settle, and the predicates pass."""

    there = {**TARGET, "joint_fraction": 1.0e-4, "min_separation_mm": 0.0,
             "resample_seconds": 2.0}
    prepared = made(success=spec(REACH, tip=TIP, episode_seconds=4.0, goal=[there, PACE]))
    report = evaluate(prepared)

    assert report["summary"]["pass"] is True, report["summary"]["predicates"]
    for row in report["seeds"]:
        assert row["metrics"]["final_error_arm_lengths_max"] < 0.05
        assert row["metrics"]["time_to_target_s_max"] < 2.0
        assert len(row["detail"]["segments"]) == 2


def test_a_spec_draws_its_own_goals_and_they_are_the_tasks_goals_by_name() -> None:
    """A test is not a lesson: the spec may command faster than the task
    trained at. It may not judge on a goal the policy does not read."""

    arguments = {"mechanism": walker, "motors": WALKER_MOTORS,
                 "observations": WALKER_OBSERVATIONS}
    gait = [{"id": "tracks", "metric": "speed_ratio", "min": 0.75}]
    faster = {**COMMAND, "low": 100.0, "high": 120.0, "resample_seconds": 1.0}
    prepared = made(WALK_TASK, success=spec(gait, feet=["front", "rear"],
                                            episode_seconds=4.0, goal=[faster]), **arguments)
    bundle = prepared["bundle"]
    assert (bundle["goal"][0]["low"], bundle["goal"][0]["segments"]) == (40.0, 1)
    assert (bundle["success"]["goal"][0]["low"], bundle["success"]["goal"][0]["segments"]) == (
        100.0, 4)
    played = dyn.evaluation_task(bundle)
    assert played["goal"] == bundle["success"]["goal"]
    episode = dyn.evaluate_episode(model(prepared), played, seed=SEEDS[0])
    assert all(100.0 <= segment["values"][0] <= 120.0
               for segment in episode["goal"][0]["segments"])
    assert len(episode["goal"][0]["segments"]) == 4
    # The judgement is still not part of what the task is (ADR-456).
    same = made(WALK_TASK, **arguments)["bundle"]
    assert dyn.task_semantic_digest(bundle) == dyn.task_semantic_digest(same)

    for other in ([], [{**COMMAND, "name": "pace"}], [{**COMMAND, "kind": "value"}],
                  [COMMAND, PACE]):
        error = refusal(WALK_TASK, success=spec(
            [{"id": "done", "metric": "completed", "min": 1.0}], goal=other,
            disturbance=[]), **arguments)
        assert error.reason == "success_goal_mismatch"


def test_a_ratio_of_a_command_that_may_be_zero_is_refused() -> None:
    arguments = {"mechanism": walker, "motors": WALKER_MOTORS,
                 "observations": WALKER_OBSERVATIONS}
    gait = spec([{"id": "tracks", "metric": "speed_ratio", "min": 0.75}],
                feet=["front", "rear"])
    standing = {**WALK_TASK, "goal": [{**COMMAND, "low": 0.0}]}
    error = refusal(standing, success=gait, **arguments)
    assert error.reason == "success_command_spans_zero"
    assert "mean_forward_speed_mm_s" in error.correction
    # The spec may narrow the range it judges on, and then it is measurable.
    made(standing, success={**gait, "goal": [COMMAND]}, **arguments)
    # A spec that bounds no ratio is not asked the question.
    made(standing, success=spec([{"id": "done", "metric": "completed", "min": 1.0}],
                                disturbance=[]), **arguments)


def test_the_settled_command_is_the_command_held_or_its_mean() -> None:
    held = [(index * 0.02, 73.0) for index in range(200)]
    assert evaluation.settled_command(held) == 73.0
    changing = [(0.5, 10.0), (1.0, 40.0), (1.5, 40.0), (2.0, 80.0), (2.5, 80.0)]
    # Read over the settled frames only -- the same frames the speed is.
    assert evaluation.settled_command(changing) == pytest.approx(60.0)
    assert evaluation.settled_command([(0.2, 50.0)]) is None


def test_the_evaluation_is_told_no_goal_from_outside() -> None:
    """``evaluate_success`` takes no command and no target: what a rollout
    is measured against is what its own episode drew."""

    import inspect

    assert not {"command_mm_s", "segments", "goal", "target"} & set(
        inspect.signature(dyn.evaluate_success).parameters
    )
    assert copy.deepcopy(dyn.GOAL_ALGORITHM).startswith(
        "random.Random(seed) continuing after the disturbance draws"
    )
