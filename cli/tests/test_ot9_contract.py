# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The ot9 evaluation contract (B1), frozen before any training run.

``docs/probes/ot9/contract.json`` pins ot8 Robin's identity, the ten reset
seeds every candidate policy is evaluated on and the bar it must clear on all
of them. A changed seed, bar value or pin is a new experiment rather than a
revision of this one, so the literals below are the freeze: moving either the
file or this test moves the other on purpose, in a diff someone reads. The
README is held to the same values so the page and the file cannot drift.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OT9 = REPO / "docs/probes/ot9"
CONTRACT = json.loads((OT9 / "contract.json").read_text(encoding="utf-8"))
README = (OT9 / "README.md").read_text(encoding="utf-8")
OT8_BASELINES = json.loads(
    (REPO / "docs/probes/ot8/baselines.json").read_text(encoding="utf-8")
)

SEEDS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
PINS = {
    "project": "ot8-robin",
    "script_sha256": "f805fdc2bd886b5da8b01f3051bd2668497a2e53c8d7f9fba392ed2c3c9d30e8",
    "accepted_revision": "0b4385616eb1610b5e8aeaec2dff56f2c073e6c1451b8975b4d9e08236975b3b",
    "accepted_digest": "b933d905ae51ef908af6bcb6fe677b1713b4b8e75e532410f138fd7f58d5638c",
    "geometry_digest": "34898ebcf359f1403070b9bf13a4c0b702bc0b7cf4bf82a5ba2e657664d918bb",
}
MJCF_SHA256 = "933b1ac6288d61904d8b7245076b96a5e02f13f7e0538ba0b5f49a322b869614"
TASK_SHA256 = "1f8c1040d6668a4f86a0cabb5d41d40a2c03bb5b1830d50d10c731d590269246"


def test_the_ten_evaluation_seeds_are_frozen() -> None:
    assert CONTRACT["evaluation_seeds"] == SEEDS
    assert len(set(SEEDS)) == CONTRACT["bar"]["seeds_required"] == 10
    # Every seed is one the design's own rollout_seed parameter admits, so an
    # evaluation is the declared rollout and never an actor edit to reach one.
    param = CONTRACT["baseline"]["rollout_seed_param"]
    assert param == {"name": "rollout_seed", "default": 0.0, "min": 0.0,
                     "max": 9.0, "step": 1.0}
    assert all(param["min"] <= seed <= param["max"] for seed in SEEDS)
    assert "**0, 1, 2, 3, 4, 5, 6, 7, 8, 9.**" in README
    assert "for S in 0 1 2 3 4 5 6 7 8 9; do" in README


def test_the_bar_is_eight_seconds_at_fifty_hertz_within_thirty_degrees() -> None:
    bar = CONTRACT["bar"]
    assert bar["episode_seconds"] == 8.0
    assert bar["control_hz"] == 50
    assert bar["steps"] == 400 == bar["episode_seconds"] * bar["control_hz"]
    assert bar["max_tilt_degrees"] == 30.0
    assert bar["forbidden_termination"] == "fallen"
    assert bar["aggregation"].startswith("every seed must pass")
    for phrase in ("**8.0 s**", "**400 steps at 50 Hz**", "**`fallen`**",
                   "**30°**", "One failed seed fails the candidate"):
        assert phrase in README


def test_the_bar_matches_the_accepted_task_it_is_measured_on() -> None:
    task = CONTRACT["task_contract"]
    bar = CONTRACT["bar"]
    assert (task["episode_seconds"], task["control_hz"], task["max_steps"]) == (
        bar["episode_seconds"], bar["control_hz"], bar["steps"])
    assert [rule["label"] for rule in task["termination"]] == [
        bar["forbidden_termination"]]
    assert task["termination"][0] == {
        "label": "fallen", "expression": "chassis_pos_z", "below": 75.25}


def test_the_baseline_pins_ot8_robin_and_agrees_with_ot8s_own_pin() -> None:
    baseline = CONTRACT["baseline"]
    for key, value in PINS.items():
        assert baseline[key] == value, key
        assert value in README, key
    assert baseline["working_revision"] == baseline["accepted_revision"]
    assert baseline["mjcf"]["sha256"] == MJCF_SHA256 in README
    assert baseline["task"]["sha256"] == TASK_SHA256 in README
    # ot8-robin is ot7-robin-c copied unchanged; the identity ot8 froze must
    # still be the identity ot9 starts from.
    robin = OT8_BASELINES["baselines"]["robin"]
    for key in ("script_sha256", "accepted_revision", "accepted_digest"):
        assert robin[key] == baseline[key], key


def test_every_run_class_is_accounted_for_in_the_readme() -> None:
    classes = CONTRACT["run_classes"]
    assert classes["training"] == ["completed", "failed", "interrupted", "void"]
    assert classes["evaluation"] == ["completed", "interrupted", "void"]
    for name in classes["training"]:
        assert f"| **{name}** |" in README, name
    assert "reruns **all ten** seeds" in README
