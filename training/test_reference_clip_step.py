# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""ADR-982: `--init-from` across a swap of the reference clip on the same clock.
No jax: `check_policy_fits` is pure, as in test_curriculum_warm_start.py."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from cadex_train import TRACKING_CLIP_KEYS, actor_channels, check_policy_fits
from test_curriculum_warm_start import TASK, bundle_of, emit, header_for, options

TRACKING = {
    "channels": ["ref_sin", "ref_cos", "q_j_ref"],
    "policy_channels": ["ref_sin", "ref_cos"],
    "period_s": 0.4,
    "samples": 4,
    "turn_per_step": 0.1,
    "held": [False],
    "start": "random",
    "table": [[0.0], [0.1], [0.2], [0.1]],
    "reset_qpos": [[0.0], [0.1], [0.2], [0.1]],
    "reset_qvel": [[0.0], [0.0], [0.0], [0.0]],
}
PARENT = dict(copy.deepcopy(TASK), tracking=TRACKING, reference={"label": "R4", "qpos": [[0.0]]},
              reference_schedule=[{"label": "R4"}])


def new_clip(**tracking):
    child = copy.deepcopy(PARENT)
    child["tracking"].update(table=[[0.0], [0.3], [0.4], [0.2]], reset_qpos=[[0.0], [0.3], [0.4], [0.2]])
    child["tracking"].update(tracking)
    child["reference"] = {"label": "R5", "qpos": [[0.1]]}
    child["reference_schedule"] = [{"label": "R5"}]
    return child


@pytest.fixture()
def parent_file(tmp_path: Path) -> Path:
    path = tmp_path / "parent-task.json"
    path.write_bytes(emit(PARENT))
    return path


def header():
    h = header_for(PARENT)
    h["observations"] = actor_channels(PARENT)      # the clock rides in what the actor reads
    h["network"] = {"layers": [[len(h["observations"]), 8], [8, 8], [8, 1]]}
    return h


def test_the_actor_reads_the_clock_and_not_the_clip():
    read = actor_channels(PARENT)
    assert "ref_sin" in read and "q_j_ref" not in read


def fits(child, parent_file, **kw):
    kw.setdefault("critic_warmup", 10)
    return check_policy_fits(header(), bundle_of(child),
                             options(init_from_task_change="R5's clip", init_from_parent_task=str(parent_file), **kw))


def test_a_new_clip_on_the_same_clock_is_admitted_and_named(parent_file):
    assert fits(new_clip(), parent_file) == ["tracking.clip"]


def test_the_clip_keys_are_the_table_and_its_reset_states():
    assert TRACKING_CLIP_KEYS == {"table", "reset_qpos", "reset_qvel"}


def test_the_critic_must_warm_up(parent_file):
    with pytest.raises(SystemExit, match="critic-warmup"):
        fits(new_clip(), parent_file, critic_warmup=0)


@pytest.mark.parametrize("field,value", [("period_s", 0.5), ("samples", 5), ("turn_per_step", 0.2),
                                         ("policy_channels", ["ref_sin"]), ("start", "zero")])
def test_the_clock_may_not_move(parent_file, field, value):
    with pytest.raises(SystemExit, match="may not"):
        fits(new_clip(**{field: value}), parent_file)


def test_the_record_may_not_move_without_the_clip(parent_file):
    child = copy.deepcopy(PARENT)
    child["reference"] = {"label": "R5", "qpos": [[0.1]]}
    with pytest.raises(SystemExit, match="reference"):
        fits(child, parent_file)


def test_other_steps_ride_beside_it(parent_file):
    child = new_clip()
    child["label"] = "child"
    assert fits(child, parent_file) == ["label", "tracking.clip"]
