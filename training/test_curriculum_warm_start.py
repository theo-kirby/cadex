"""ADR-161: `--init-from` across a task change, and every refusal around it.

No jax. `check_policy_fits` is a pure function of a header, a bundle dict and
an options namespace, so the whole surface is testable without a device --
which is the point: a warm start that is going to be refused should be refused
before anything reserves a card.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import pytest

from cadex_train import (
    CURRICULUM_EPISODE_KEYS,
    CURRICULUM_TASK_KEYS,
    check_policy_fits,
)

EPISODE = {
    "control_hz": 25,
    "control_interval_s": 0.04,
    "episode_seconds": 6.0,
    "max_steps": 150,
    "reset_keyframe": "solved",
    "reward_stage": "after_step",
    "solver_step_s": 0.002,
    "solver_steps_per_action": 20,
}

TASK = {
    "actions": [
        {"actuator": "j/position", "high": 25.0, "index": 0, "joint": "j",
         "kind": "position", "low": -25.0, "scale": 0.01745, "unit": "deg"},
    ],
    "disturbance": [{"label": "shove", "newtons_low": 0.3,
                     "newtons_high": 0.8, "duration_s": 0.12}],
    "episode": dict(EPISODE),
    "functions": ["abs", "exp"],
    "label": "parent",
    "observations": [{"channels": ["a", "b"], "dim": 2}],
    "reward": [{"expression": "1", "label": "alive", "weight": 0.2}],
    "schema": "cadex-training-task-v1",
}


def emit(task: dict) -> bytes:
    return json.dumps(task, indent=1, sort_keys=True).encode()


def bundle_of(task: dict) -> dict:
    return {
        "task": task,
        "task_sha256": hashlib.sha256(emit(task)).hexdigest(),
        "model_sha256": "m" * 64,
    }


def header_for(task: dict) -> dict:
    return {
        "task": {"label": task["label"],
                 "sha256": hashlib.sha256(emit(task)).hexdigest()},
        "model": {"sha256": "m" * 64},
        "observations": ["a", "b"],
        "actions": copy.deepcopy(task["actions"]),
        "network": {"layers": [[2, 8], [8, 8], [8, 1]]},
    }


def options(**kw) -> argparse.Namespace:
    base = {"hidden": [8, 8], "init_from": "p.cxpolicy",
            "init_from_task_change": "", "init_from_parent_task": ""}
    base.update(kw)
    return argparse.Namespace(**base)


@pytest.fixture()
def parent_file(tmp_path: Path) -> Path:
    path = tmp_path / "parent-task.json"
    path.write_bytes(emit(TASK))
    return path


def child_with(**changes) -> dict:
    task = copy.deepcopy(TASK)
    task.update(changes)
    return task


# --------------------------------------------------------------------------
# The default path, unchanged. These two are the regression guard: ADR-161
# buys a new branch and must not move the old one.
# --------------------------------------------------------------------------


def test_the_same_bundle_still_fits_with_no_new_flags():
    task = copy.deepcopy(TASK)
    assert check_policy_fits(header_for(task), bundle_of(task),
                             options()) is None


def test_a_changed_bundle_is_still_refused_with_no_new_flags():
    with pytest.raises(SystemExit, match="the task digest"):
        check_policy_fits(header_for(TASK),
                          bundle_of(child_with(label="child")), options())


# --------------------------------------------------------------------------
# The curriculum branch.
# --------------------------------------------------------------------------


def test_a_declared_curriculum_step_is_admitted_and_names_its_keys(parent_file):
    child = child_with(label="child", disturbance=[
        {"label": "shove", "newtons_low": 0.48, "newtons_high": 1.28,
         "duration_s": 0.12}])
    keys = check_policy_fits(
        header_for(TASK), bundle_of(child),
        options(init_from_task_change="a harder band",
                init_from_parent_task=str(parent_file)))
    assert keys == ["disturbance", "label"]


def test_the_horizon_may_move_because_the_policy_cannot_see_it(parent_file):
    episode = dict(EPISODE, max_steps=300, episode_seconds=12.0)
    keys = check_policy_fits(
        header_for(TASK), bundle_of(child_with(episode=episode)),
        options(init_from_task_change="a longer episode",
                init_from_parent_task=str(parent_file)))
    assert keys == ["episode"]


@pytest.mark.parametrize("field, value", [
    ("control_hz", 50),
    ("control_interval_s", 0.02),
    ("solver_step_s", 0.001),
    ("solver_steps_per_action", 10),
])
def test_the_control_cadence_may_not_move(parent_file, field, value):
    episode = dict(EPISODE)
    episode[field] = value
    with pytest.raises(SystemExit, match="episode keys moved and may not"):
        check_policy_fits(
            header_for(TASK), bundle_of(child_with(episode=episode)),
            options(init_from_task_change="sneaking a rate change",
                    init_from_parent_task=str(parent_file)))


@pytest.mark.parametrize("key", sorted(
    set(TASK) - CURRICULUM_TASK_KEYS - {"observations", "actions"}))
def test_a_key_outside_the_curriculum_set_is_refused(parent_file, key):
    child = copy.deepcopy(TASK)
    child[key] = ["something else"]
    with pytest.raises(SystemExit, match="moved and may not"):
        check_policy_fits(
            header_for(TASK), bundle_of(child),
            options(init_from_task_change="x",
                    init_from_parent_task=str(parent_file)))


def test_the_reason_alone_is_not_enough(parent_file):
    with pytest.raises(SystemExit, match="--init-from-parent-task is required"):
        check_policy_fits(header_for(TASK),
                          bundle_of(child_with(label="child")),
                          options(init_from_task_change="x"))


def test_the_parent_bundle_is_tied_to_the_policys_own_digest(tmp_path):
    other = tmp_path / "other.json"
    other.write_bytes(emit(child_with(label="not-the-parent")))
    with pytest.raises(SystemExit, match="is not the one this policy trained"):
        check_policy_fits(header_for(TASK),
                          bundle_of(child_with(label="child")),
                          options(init_from_task_change="x",
                                  init_from_parent_task=str(other)))


def test_asserting_a_change_that_is_not_there_is_refused(parent_file):
    task = copy.deepcopy(TASK)
    with pytest.raises(SystemExit, match="there is no step here"):
        check_policy_fits(header_for(task), bundle_of(task),
                          options(init_from_task_change="x",
                                  init_from_parent_task=str(parent_file)))


def test_a_formatting_only_difference_is_refused_rather_than_papered_over(
        tmp_path):
    """Same keys, different bytes: re-emit the child, do not warm across it."""

    parent = tmp_path / "p.json"
    parent.write_bytes(json.dumps(TASK, indent=4, sort_keys=True).encode())
    header = header_for(TASK)
    header["task"]["sha256"] = hashlib.sha256(parent.read_bytes()).hexdigest()
    with pytest.raises(SystemExit, match="the difference is formatting"):
        check_policy_fits(header, bundle_of(copy.deepcopy(TASK)),
                          options(init_from_task_change="x",
                                  init_from_parent_task=str(parent)))


def test_every_other_check_still_runs_inside_the_curriculum_branch(parent_file):
    """The flag skips the whole-file digest and buys nothing else."""

    child = child_with(label="child")
    header = header_for(TASK)
    header["network"] = {"layers": [[2, 999], [999, 999], [999, 1]]}
    with pytest.raises(SystemExit, match="the network shape"):
        check_policy_fits(header, bundle_of(child),
                          options(init_from_task_change="x",
                                  init_from_parent_task=str(parent_file)))


def test_the_curriculum_sets_say_what_they_mean():
    assert "observations" not in CURRICULUM_TASK_KEYS
    assert "actions" not in CURRICULUM_TASK_KEYS
    assert "model" not in CURRICULUM_TASK_KEYS
    assert "functions" not in CURRICULUM_TASK_KEYS
    assert "schema" not in CURRICULUM_TASK_KEYS
    assert CURRICULUM_EPISODE_KEYS == {"episode_seconds", "max_steps"}
