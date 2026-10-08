# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The trainer and the engine agree on the goal, exactly (ADR-462).

The engine draws an episode's goals with ``CadexDynamics.draw_episode_goals``
and the trainer cannot import it (ADR-084), so ``training/cadex_train.py``
carries its own ``draw_goals``. Unlike the reset variation -- which the
trainer redraws on device with a different stream, on purpose -- this copy
has to produce **the same numbers**: a target is a place a tip can reach
without touching anything, and a trainer that drew targets by some other
rule would train a policy on goals the evaluation never asks for.

**This file is the test that fails if the two drift apart.** The first half
runs in the engine environment, because the trainer's goal code is host-side
and needs only stock ``mujoco``: the draw, the pool, the segment rule and
the channel order are each held to the engine's, number for number. The
second half runs the real trainer, and is gated on its dependencies as
``test_dynamics_policy_trainer`` is: it holds the rewards a run reports to
the goals the engine draws from the same seed, and plays the policy it wrote.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import inspect
import json
import os
from pathlib import Path
import random
import subprocess
import sys

import pytest

import CadexDynamics as dyn
import dynamics_policy_fixtures as pf
from test_dynamics_goal_model import (
    ARM_TASK,
    COMMAND,
    PACE,
    TARGET,
    WALK_TASK,
    made,
    model,
)
from test_dynamics_policy_trainer import TRAINER, _trainer_module, _venv_python
from test_success_spec_model import (
    MOTORS as WALKER_MOTORS,
    OBSERVATIONS as WALKER_OBSERVATIONS,
    spec,
    walker,
)

mujoco = pytest.importorskip("mujoco")

WALKER = {"mechanism": walker, "motors": WALKER_MOTORS, "observations": WALKER_OBSERVATIONS}
#: A speed drawn again every 0.4 s beside the point and the value, so one
#: bundle has all three kinds and two different periods.
MIXED = {**ARM_TASK, "goal": [TARGET, PACE, {**COMMAND, "resample_seconds": 0.4}],
         "reward": ARM_TASK["reward"] + [
             {"label": "asked", "expression": "command", "weight": 1.0e-3}]}


# -- the draw, number for number --------------------------------------------

@pytest.mark.parametrize("seed", [0, 1, 17, 1101, 2**31 - 1])
def test_the_trainer_draws_the_goals_the_engine_draws(seed) -> None:
    """Same bundle, same model, same seed: the same goals, compared with
    ``==`` on doubles. Twenty episodes a seed, so the streams are compared
    well past their first draw and through every rejected try."""

    module = _trainer_module()
    prepared = made(MIXED)
    bundle = prepared["bundle"]
    here, there = random.Random(seed), random.Random(seed)
    engine_model, trainer_model = model(prepared), model(prepared)
    for _ in range(20):
        assert module.draw_goals(mujoco, trainer_model, bundle, there) == (
            dyn.draw_episode_goals(mujoco, engine_model, bundle, here)
        )
    # ...and the two streams are left in the same place.
    assert here.random() == there.random()


def test_the_draws_really_exercise_the_rejections() -> None:
    """The comparison above means little if no try is ever refused. On this
    arm about a fifth of the poses put the tip under the stated floor."""

    bundle = made(MIXED)["bundle"]
    target = bundle["goal"][0]
    assert target["kind"] == "point" and target["min_z_m"] is not None
    probe = copy.deepcopy(bundle)
    probe["goal"][0]["min_z_m"] = None
    probe["goal"][0]["min_separation_m"] = 0.0
    compiled = mujoco.MjModel.from_xml_string(made(MIXED)["xml"].decode("utf-8"))
    rng = random.Random(3)
    unfiltered = [dyn.draw_episode_goals(mujoco, compiled, probe, rng)[0]["segments"][0]
                  for _ in range(200)]
    low = sum(1 for point in unfiltered if point[2] < 50.0)
    assert 10 < low < 100


def test_the_pool_is_the_engines_episodes_from_the_training_seed() -> None:
    """Entry ``i`` is ``[episode][segment][channel]``: one stream from
    ``random.Random(base_seed)``, episode after episode, nothing before it."""

    module = _trainer_module()
    prepared = made(MIXED)
    bundle = prepared["bundle"]
    pool = module.goal_pool(mujoco, prepared["xml"], bundle, base_seed=5, count=12)

    assert [len(table) for table in pool] == [12, 12, 12]
    assert [len(table[0]) for table in pool] == [2, 1, 5]
    assert [len(table[0][0]) for table in pool] == [3, 1, 1]
    rng = random.Random(5)
    for episode in range(12):
        drawn = dyn.draw_episode_goals(mujoco, model(prepared), bundle, rng)
        assert [table[episode] for table in pool] == [row["segments"] for row in drawn]
    # A task with no goal has no pool, whatever size was asked for.
    plain = made({**ARM_TASK, "goal": [], "reward": [
        {"label": "up", "expression": "hand_z", "weight": 1.0e-3}]})
    assert module.goal_pool(mujoco, plain["xml"], plain["bundle"], base_seed=5, count=12) == []
    with pytest.raises(SystemExit, match="holds no episode"):
        module.goal_pool(mujoco, prepared["xml"], bundle, base_seed=5, count=0)


def test_the_trainers_segment_rule_is_the_engines() -> None:
    """Which goal is up at which control step, on the trainer's integer
    arithmetic and the engine's schedule, for every step of an episode and
    a way past it."""

    numpy = pytest.importorskip("numpy")
    module = _trainer_module()
    prepared = made(MIXED)
    bundle = prepared["bundle"]
    episode = dyn.evaluate_episode(model(prepared), bundle, seed=9)
    steps = numpy.arange(0, int(bundle["episode"]["max_steps"]) + 40)
    for entry, scheduled in zip(bundle["goal"], episode["goal"], strict=True):
        segments = module.goal_segment(
            numpy, steps, int(entry["resample_steps"]), int(entry["segments"])
        )
        values = [segment["values"] for segment in scheduled["segments"]]
        for step, segment in zip(steps.tolist(), segments.tolist(), strict=True):
            held = dyn.goal_values([scheduled], step)
            assert [held[channel] for channel in entry["channels"]] == values[segment]
    # Held for the episode is segment zero throughout.
    assert module.goal_segment(numpy, steps, 0, 1).tolist() == [0] * len(steps)


def test_the_trainers_phase_is_the_engines() -> None:
    """A phase goal (ADR-598) is the one goal whose channels move inside a
    segment, so the trainer's turn of it is held to the engine's at every
    step of an episode and past it, through a resample."""

    numpy = pytest.importorskip("numpy")
    module = _trainer_module()
    prepared = made({**ARM_TASK, "goal": [TARGET, PACE, LEAD]})
    bundle = prepared["bundle"]
    lead = bundle["goal"][2]
    assert (lead["kind"], lead["resample_steps"], lead["segments"]) == ("phase", 35, 3)
    assert module.channels(bundle) == dyn._task_channels(bundle)
    episode = dyn.evaluate_episode(model(prepared), bundle, seed=9)
    scheduled = episode["goal"][2]
    starts = numpy.asarray([segment["values"] for segment in scheduled["segments"]])
    steps = numpy.arange(0, int(bundle["episode"]["max_steps"]) + 40)
    period = int(lead["resample_steps"])
    segment = module.goal_segment(numpy, steps, period, int(lead["segments"]))
    told = module.phase_channels(
        numpy, starts[segment], steps - segment * period, lead["radians_per_step"]
    )
    for step, row in zip(steps.tolist(), told.tolist(), strict=True):
        held = dyn.goal_values([scheduled], step)
        assert row == pytest.approx([held["lead_sin"], held["lead_cos"]], abs=1.0e-12)
    trained = inspect.getsource(module.train)
    assert "phase_channels(jnp, held, steps - segment * period, turn)" in trained


def test_the_trainer_reads_the_channels_in_the_engines_order() -> None:
    """The observation vector is positional. Sensor channels, then goals;
    and the policy's share of it is the policy channels, then goals."""

    module = _trainer_module()
    hidden = made(observations=[
        {"kind": "position", "joint": "elbow", "motion_type": "angular",
         "name": "elbow_angle"},
        {"kind": "centre_of_mass", "component": "fore", "name": "hand",
         "role": "privileged"},
    ])["bundle"]
    for bundle in (made(MIXED)["bundle"], hidden, made(WALK_TASK, **WALKER)["bundle"]):
        assert module.goal_channels(bundle) == dyn.goal_channels(bundle)
        assert module.channels(bundle) == dyn._task_channels(bundle)
        assert module.actor_channels(bundle) == dyn.policy_channels(bundle)
    assert module.actor_channels(hidden) == [
        "elbow_angle", "target_x", "target_y", "target_z", "pace"
    ]


def test_the_trainers_goal_code_is_host_side_and_states_its_algorithm() -> None:
    """The draw never runs on device, so it is not a second algorithm that
    resembles the bundle's: it is the bundle's. What the device does is
    choose which pooled episode an environment is given."""

    module = _trainer_module()
    for function in (module.draw_goals, module.goal_pool, module.goal_tip_m):
        source = inspect.getsource(function)
        assert "jnp" not in source and "jax" not in source.replace("no jax", "")
    assert module.GOAL_MODE == "host_pool"
    assert "bundle's goal_algorithm" in module.GOAL_POOL_ALGORITHM
    assert "random.Random(base_seed)" in module.GOAL_POOL_ALGORITHM
    trained = inspect.getsource(module.train)
    # The trace-time branch: a task with no goal takes no extra key split
    # and carries no extra member.
    assert "if goaled:" in trained
    assert "goal_segment(jnp, steps, period, pooled.shape[1])" in trained
    # The three lines of the tip point, as the engine writes them.
    for owner in (inspect.getsource(module.goal_tip_m), inspect.getsource(dyn._goal_tip_m)):
        assert "float(rotation[3 * axis + other]) * float(local_m[other])" in owner


def test_a_training_seed_may_not_be_an_evaluation_seed() -> None:
    """With a goal the rule has teeth: the pool's first episode is the first
    draws of the seed, which on a task with nothing drawn before its goals
    are the very targets that evaluation seed is judged on."""

    module = _trainer_module()
    judged = spec([{"id": "done", "metric": "completed", "min": 1.0}], seeds=[3, 5, 8])
    prepared = made(success=judged)
    bundle = prepared["bundle"]
    assert not bundle["reset_variation"] and not bundle["disturbance"]

    held_out = dyn.evaluate_episode(model(prepared), dyn.evaluation_task(bundle), seed=5)
    pool = module.goal_pool(mujoco, prepared["xml"], dyn.evaluation_task(bundle),
                            base_seed=5, count=1)
    assert pool[0][0] == [segment["values"] for segment in held_out["goal"][0]["segments"]]

    with pytest.raises(SystemExit, match="evaluation seeds"):
        module.check_training_seed(bundle, 5)
    module.check_training_seed(bundle, 4)
    module.check_training_seed(made()["bundle"], 5)
    # It is the first thing ``train`` does, before anything is imported.
    body = inspect.getsource(module.train)
    assert body.index("check_training_seed(") < body.index("import jax")


def _header(module, bundle, prepared, **options):
    trained = {
        "layers": [[1, 1]], "output_scale": [1.0], "output_bias": [0.0],
        "normaliser": {"mean": [0.0], "std": [1.0]}, "log_std": [0.0],
        "iterations": 1, "wall_time_s": 0.0, "backend": "cpu", "devices": ["cpu"],
        "versions": {}, "reward_curve": [], "witness_observations": [],
        "witness_actions": [],
    }
    arguments = module.arguments(["bundle.json", "--out", "p.cxpolicy",
                                  *[str(item) for pair in options.items() for item in pair]])
    return module.policy_header(
        {"task": bundle, "task_sha256": prepared["task_sha256"],
         "model_sha256": bundle["model"]["sha256"], "model_path": bundle["model"]["path"]},
        arguments, trained, cadex_importable=False,
    )


def test_a_policy_says_how_its_goals_were_drawn_and_a_goalless_one_says_nothing() -> None:
    module = _trainer_module()
    prepared = made(MIXED)
    header = _header(module, prepared["bundle"], prepared, **{"--seed": 4, "--goal-pool": 64})
    assert header["observations"] == dyn.policy_channels(prepared["bundle"])
    assert header["training"]["goal"] == {
        "mode": "host_pool", "algorithm": module.GOAL_POOL_ALGORITHM,
        "bundle_algorithm": dyn.GOAL_ALGORITHM, "base_seed": 4, "pool": 64,
        "entries": ["target", "pace", "command"],
    }
    assert header["training"]["hyperparameters"]["goal_pool"] == 64

    plain = made({**ARM_TASK, "goal": [], "reward": [
        {"label": "up", "expression": "hand_z", "weight": 1.0e-3}]})
    quiet = _header(module, plain["bundle"], plain)
    assert "goal" not in quiet["training"]
    assert "goal_pool" not in quiet["training"]["hyperparameters"]


def test_a_policy_names_the_trainer_that_ran_not_the_file_on_disk_when_it_saved(
        tmp_path) -> None:
    """``training.trainer_sha256`` is the digest of the code the process
    loaded. ot11's ``r3-nochatter`` started on the pre-ADR-465 trainer, the
    fix was written to disk mid-run, and every checkpoint saved after that
    claimed the fixed trainer's digest, because the file was hashed at save
    time (ADR-466)."""

    import importlib.util

    copied = tmp_path / "cadex_train.py"
    copied.write_bytes(TRAINER.read_bytes())
    loaded = hashlib.sha256(copied.read_bytes()).hexdigest()
    module_spec = importlib.util.spec_from_file_location("cadex_train_copy", copied)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)

    copied.write_bytes(copied.read_bytes() + b"\n# edited while a run was training\n")
    prepared = made()
    header = _header(module, prepared["bundle"], prepared)
    assert header["training"]["trainer_sha256"] == loaded


def test_a_warm_start_across_a_changed_goal_is_refused() -> None:
    """A goal is part of the observation vector's meaning, so it is not one
    of the keys a curriculum step may move (ADR-161)."""

    module = _trainer_module()
    assert not {"goal", "goal_algorithm"} & set(module.CURRICULUM_TASK_KEYS)


# -- the real trainer -------------------------------------------------------

#: One hinge, nothing that can end an episode, and a reward that is the goal
#: and nothing else. Whatever the policy does, the reward of a step is the
#: goal that was up when the step was taken -- so the curve a run reports is
#: a statement about the goals it drew and when it changed them.
ASKED = {"name": "ask", "kind": "value", "low": 1.0, "high": 2.0, "resample_seconds": 0.1}
#: A clock (ADR-598): a turn every 0.6 s, its start drawn again every 0.7 s.
LEAD = {"name": "lead", "kind": "phase", "period_seconds": 0.6, "resample_seconds": 0.7}
ASKED_TASK = {
    **pf.SWING_UP_TASK,
    "label": "asked",
    "termination": [],
    "episode_seconds": 0.4,
    "reward": [{"label": "asked", "expression": "ask", "weight": 1.0}],
    "goal": [ASKED],
}


def _swing(task, tmp_path: Path, name: str):
    prepared = pf.swing_up_bundle(task=task)
    root = tmp_path / name
    (root / "outputs").mkdir(parents=True)
    (root / "outputs" / "job-model.xml").write_bytes(prepared["model_xml"])
    (root / "outputs" / "job-task.json").write_bytes(prepared["task_bytes"])
    return prepared, root


def _run(python, root: Path, *extra):
    out = root / "p.cxpolicy"
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [python, "-P", str(TRAINER), str(root / "outputs" / "job-task.json"),
         "--out", str(out), "--quiet", *extra],
        capture_output=True, text=True, env=environment, check=False,
    )
    return out, result


def test_a_training_run_is_paid_for_the_goals_the_engine_draws(tmp_path) -> None:
    """The device half of the agreement, and it is exact.

    With a pool of one, every environment holds the same episode of goals:
    the first the engine draws from ``random.Random(seed)``. The reward is
    the goal, nothing terminates, and every environment resets together at
    the bundle's horizon -- so the mean reward of each iteration is fixed by
    the four drawn values and the step each one starts at. Fifteen steps an
    iteration against a twenty step episode, so the window slides across
    the resets and across every boundary. A trainer that drew differently,
    changed the goal a step early or late, or scored a step against the
    wrong segment reports a different curve.
    """

    python = _venv_python()
    if python is None:
        pytest.skip("the offboard trainer's dependencies are not installed here")

    prepared, root = _swing(ASKED_TASK, tmp_path, "asked")
    bundle = prepared["bundle"]
    assert int(bundle["episode"]["max_steps"]) == 20
    assert (bundle["goal"][0]["resample_steps"], bundle["goal"][0]["segments"]) == (5, 4)
    out, result = _run(python, root, "--seed", "6", "--iterations", "5", "--envs", "4",
                       "--unroll", "15", "--goal-pool", "1")
    assert result.returncode == 0, result.stderr[-4000:]

    rng = random.Random(6)
    (drawn,) = dyn.draw_episode_goals(mujoco, prepared["model"], bundle, rng)
    schedule = dyn.goal_schedule(bundle, [drawn])
    expected = [
        sum(dyn.goal_values(schedule, step % 20)["ask"]
            for step in range(15 * iteration, 15 * iteration + 15)) / 15.0
        for iteration in range(5)
    ]
    container = dyn.decode_policy(out.read_bytes())
    curve = [row["reward_per_step"] for row in container["header"]["training"]["reward_curve"]]
    assert curve == pytest.approx(expected, rel=2.0e-6)
    assert len({round(value, 5) for value in expected}) > 1

    # The policy reads the goal: it is the last input, and every observation
    # the run witnessed carries one of the four drawn values there.
    assert container["header"]["observations"][-1] == "ask"
    told = {row[-1] for row in container["header"]["evaluation"]["observations"]}
    assert told and all(
        any(value == pytest.approx(goal[0], rel=1.0e-6) for goal in drawn["segments"])
        for value in told
    )
    assert container["header"]["training"]["goal"]["pool"] == 1

    # And the engine accepts the file and plays it with a goal of its own.
    evidence = dyn.verify_policy(container, bundle, task_sha256=prepared["task_sha256"])
    assert evidence["witness_error"] < dyn.POLICY_WITNESS_TOLERANCE
    run = dyn.rollout_policy(
        dyn.load_model(prepared["model_xml"]), bundle, container,
        components=["link"], frames_per_second=50, seed=41,
    )
    asked = run["episode"]["goal"][0]["segments"]
    assert [segment["start_step"] for segment in asked] == [0, 5, 10, 15]
    assert run["episode"]["total_reward"] == pytest.approx(
        5.0 * sum(segment["values"][0] for segment in asked)
    )


def test_a_training_run_is_paid_for_the_phase_the_engine_turns(tmp_path) -> None:
    """The same exact agreement for a phase goal (ADR-598), whose channels
    change every step: the reward is its sine, so a trainer that turned it
    at another rate, from another start or across a resample wrongly
    reports a different curve."""

    python = _venv_python()
    if python is None:
        pytest.skip("the offboard trainer's dependencies are not installed here")

    clock = {"name": "lead", "kind": "phase", "period_seconds": 0.26,
             "resample_seconds": 0.1}
    prepared, root = _swing(
        {**ASKED_TASK, "label": "clocked", "goal": [clock],
         "reward": [{"label": "lead", "expression": "lead_sin", "weight": 1.0}]},
        tmp_path, "clocked",
    )
    bundle = prepared["bundle"]
    assert int(bundle["episode"]["max_steps"]) == 20
    out, result = _run(python, root, "--seed", "6", "--iterations", "5", "--envs", "4",
                       "--unroll", "15", "--goal-pool", "1")
    assert result.returncode == 0, result.stderr[-4000:]

    (drawn,) = dyn.draw_episode_goals(mujoco, prepared["model"], bundle, random.Random(6))
    schedule = dyn.goal_schedule(bundle, [drawn])
    expected = [
        sum(dyn.goal_values(schedule, step % 20)["lead_sin"]
            for step in range(15 * iteration, 15 * iteration + 15)) / 15.0
        for iteration in range(5)
    ]
    container = dyn.decode_policy(out.read_bytes())
    curve = [row["reward_per_step"] for row in container["header"]["training"]["reward_curve"]]
    assert curve == pytest.approx(expected, rel=1.0e-5, abs=1.0e-6)
    assert container["header"]["observations"][-2:] == ["lead_sin", "lead_cos"]


def test_the_trainer_trains_on_reachable_points_from_its_pool(tmp_path) -> None:
    """A point goal, through the real trainer: every target it showed the
    policy is a row of the host pool, which is the engine's own draw."""

    python = _venv_python()
    if python is None:
        pytest.skip("the offboard trainer's dependencies are not installed here")

    module = _trainer_module()
    prepared = made(root=tmp_path / "reach")
    bundle = prepared["bundle"]
    out, result = _run(python, tmp_path / "reach", "--seed", "2", "--iterations", "2",
                       "--envs", "16", "--unroll", "10", "--goal-pool", "8")
    assert result.returncode == 0, result.stderr[-4000:]

    container = dyn.decode_policy(out.read_bytes())
    assert container["header"]["observations"] == dyn.policy_channels(bundle)
    dyn.verify_policy(container, bundle, task_sha256=prepared["task_sha256"])
    pool = module.goal_pool(mujoco, prepared["xml"], bundle, base_seed=2, count=8)
    points = [segment for episode in pool[0] for segment in episode]
    paces = [episode[0][0] for episode in pool[1]]
    first = dyn.policy_channels(bundle).index("target_x")
    for row in container["header"]["evaluation"]["observations"]:
        assert any(row[first:first + 3] == pytest.approx(point, rel=1.0e-5, abs=1.0e-3)
                   for point in points)
        assert any(row[first + 3] == pytest.approx(pace, rel=1.0e-6) for pace in paces)


def test_the_trainer_refuses_an_evaluation_seed_before_it_trains(tmp_path) -> None:
    python = _venv_python()
    if python is None:
        pytest.skip("the offboard trainer's dependencies are not installed here")

    judged = {"label": "", "predicates": [{"id": "done", "metric": "completed", "min": 1.0}],
              "seeds": [3, 5, 8], "feet": [], "tip": None, "episode_seconds": None,
              "randomisation": None, "reset_variation": None, "disturbance": None}
    _prepared, root = _swing({**ASKED_TASK, "success": judged}, tmp_path, "judged")
    out, result = _run(python, root, "--seed", "5", "--iterations", "1", "--envs", "2")
    assert result.returncode != 0 and not out.exists()
    assert "evaluation seeds" in result.stderr


def test_a_task_with_no_goal_trains_as_it_did(tmp_path) -> None:
    """The goal branches are taken at trace time, so a task that states no
    goal draws no extra key and carries no extra member: two runs of it at
    one seed, one with a pool size given, write the same weights."""

    python = _venv_python()
    if python is None:
        pytest.skip("the offboard trainer's dependencies are not installed here")

    weights = []
    for name, extra in (("plain", ()), ("sized", ("--goal-pool", "3"))):
        _prepared, root = _swing(pf.SWING_UP_TASK, tmp_path, name)
        out, result = _run(python, root, "--seed", "0", "--iterations", "2",
                           "--envs", "8", "--unroll", "10", *extra)
        assert result.returncode == 0, result.stderr[-4000:]
        container = dyn.decode_policy(out.read_bytes())
        assert "goal" not in container["header"]["training"]
        weights.append(hashlib.sha256(
            json.dumps(container["weights"]).encode("utf-8")).hexdigest())
    assert weights[0] == weights[1]
