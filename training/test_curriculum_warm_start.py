# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

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
    CURRICULUM_GOAL_KEYS,
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


def test_a_revised_success_spec_may_move(parent_file):
    """ADR-597: the bar is not something the network reads or emits."""

    parent_task = child_with(success={"seeds": [101, 102], "predicates": [
        {"metric": "final_distance_mm", "max": 20.0}]})
    parent_file.write_bytes(emit(parent_task))
    child = child_with(success={"seeds": [101, 102], "predicates": [
        {"metric": "final_distance_mm", "max": 20.0},
        {"metric": "laps", "min": 2.0}]})
    keys = check_policy_fits(
        header_for(parent_task), bundle_of(child),
        options(init_from_task_change="the spec now bounds laps",
                init_from_parent_task=str(parent_file)))
    assert keys == ["success"]


def test_a_revised_success_spec_still_needs_the_declared_step():
    """Without the flag a spec revision is a digest mismatch, as before."""

    parent_task = child_with(success={"seeds": [101]})
    with pytest.raises(SystemExit, match="the task digest"):
        check_policy_fits(header_for(parent_task),
                          bundle_of(child_with(success={"seeds": [102]})),
                          options())


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
    assert "goal" not in CURRICULUM_TASK_KEYS
    # ADR-871: ADR-824's weighted bands are a draw range too; ADR-900: so is a bound.
    assert CURRICULUM_GOAL_KEYS == {"low", "high", "nominal", "sequence", "bands", "bound"}
    assert "success" in CURRICULUM_TASK_KEYS
    assert CURRICULUM_EPISODE_KEYS == {"episode_seconds", "max_steps"}


# --------------------------------------------------------------------------
# ADR-791: a goal's draw range may move; nothing else about the goal may.
# --------------------------------------------------------------------------

GOAL = {"channels": ["cmd"], "high": 5000.0, "kind": "speed", "label": "cmd",
        "low": 700.0, "name": "cmd", "nominal": [2850.0], "ramp_steps": 50,
        "resample_steps": 600, "segments": 1, "unit": "mm/s"}


@pytest.fixture()
def goal_parent(tmp_path: Path) -> tuple[dict, Path]:
    task = child_with(goal=[dict(GOAL)])
    path = tmp_path / "goal-parent-task.json"
    path.write_bytes(emit(task))
    return task, path


def goal_header(task: dict) -> dict:
    header = header_for(task)
    header["observations"] = ["a", "b", "cmd"]
    header["network"] = {"layers": [[3, 8], [8, 8], [8, 1]]}
    return header


def test_a_wider_goal_range_may_move(goal_parent):
    parent, path = goal_parent
    child = copy.deepcopy(parent)
    child["goal"][0].update(high=7500.0, nominal=[4100.0], sequence=[7500.0])
    keys = check_policy_fits(
        goal_header(parent), bundle_of(child),
        options(init_from_task_change="a higher command ceiling",
                init_from_parent_task=str(path)))
    assert keys == ["goal.range"]


def test_a_wider_banded_range_may_move(goal_parent):
    """ADR-871: ADR-824's weighted bands are a draw range, as low and high are."""

    parent, path = goal_parent
    parent = copy.deepcopy(parent)
    parent["goal"][0].update(low=-1500.0, high=1500.0,
                             bands=[[0.0, 0.0, 0.1], [-1500.0, 1500.0, 0.9]])
    path.write_bytes(emit(parent))
    child = copy.deepcopy(parent)
    child["goal"][0].update(low=-2000.0, high=2000.0,
                            bands=[[0.0, 0.0, 0.1], [-2000.0, 2000.0, 0.9]])
    keys = check_policy_fits(
        goal_header(parent), bundle_of(child),
        options(init_from_task_change="a wider banded vx range",
                init_from_parent_task=str(path)))
    assert keys == ["goal.range"]


def test_a_bound_may_come_onto_a_goal(goal_parent):
    """ADR-900: a bound narrows where a goal is drawn from, so it is a draw range too."""

    parent, path = goal_parent
    parent = copy.deepcopy(parent)
    parent["goal"].append(dict(GOAL, label="yaw", name="yaw", channels=["yaw"],
                               low=-86.0, high=86.0, nominal=[0.0], unit="deg/s"))
    path.write_bytes(emit(parent))
    child = copy.deepcopy(parent)
    child["goal"][1]["bound"] = {"goal": "cmd", "product": 280000.0}
    child["goal_algorithm"] = str(parent.get("goal_algorithm") or "") + "; on a goal with bound"
    header = goal_header(parent)
    header["observations"] = ["a", "b", "cmd", "yaw"]
    header["network"] = {"layers": [[4, 8], [8, 8], [8, 1]]}
    keys = check_policy_fits(
        header, bundle_of(child),
        options(init_from_task_change="turns bounded by the speed drawn beside them",
                init_from_parent_task=str(path)))
    assert keys == ["goal.range"]


@pytest.mark.parametrize("field, value", [
    ("channels", ["cmd", "yaw"]),
    ("kind", "point"),
    ("unit", "m/s"),
    ("resample_steps", 300),
    ("ramp_steps", 0),
])
def test_anything_else_about_a_goal_may_not_move(goal_parent, field, value):
    parent, path = goal_parent
    child = copy.deepcopy(parent)
    child["goal"][0][field] = value
    with pytest.raises(SystemExit, match=r"moved and may not: \['goal'\]"):
        check_policy_fits(
            goal_header(parent), bundle_of(child),
            options(init_from_task_change="x", init_from_parent_task=str(path)))


def test_the_goal_algorithm_alone_may_not_move(goal_parent):
    """ADR-900: the algorithm moves only beside a goal whose draw range moved."""

    parent, path = goal_parent
    child = copy.deepcopy(parent)
    child["goal_algorithm"] = "another algorithm"
    with pytest.raises(SystemExit, match="goal_algorithm"):
        check_policy_fits(
            goal_header(parent), bundle_of(child),
            options(init_from_task_change="a new algorithm", init_from_parent_task=str(path)))


def test_a_scan_the_actor_gains_is_admitted_and_a_privileged_one_is_not_read(parent_file):
    """ADR-859: a policy scan appends its channels after the source's inputs;
    the step names ``scans.actor`` so the warm start widens the first layer.
    A privileged scan is a course step only (ADR-736), and the actor's inputs
    must still match the source's in order."""

    scan = {"name": "hs", "kind": "height_scan", "body_id": 1, "scale": 1000.0,
            "offsets_mm": [[0.0, 0.0], [100.0, 0.0]], "channels": ["hs_0", "hs_1"]}
    flags = options(init_from_task_change="scan", init_from_parent_task=str(parent_file))
    seen = child_with(scans=[dict(scan, role="policy")])
    assert check_policy_fits(header_for(TASK), bundle_of(seen), flags) == ["scans", "scans.actor"]
    hidden = child_with(scans=[dict(scan, role="privileged")])
    assert check_policy_fits(header_for(TASK), bundle_of(hidden), flags) == ["scans"]
    header = header_for(TASK)
    header["observations"] = ["b", "a"]
    with pytest.raises(SystemExit, match="the observation channels"):
        check_policy_fits(header, bundle_of(seen), flags)
