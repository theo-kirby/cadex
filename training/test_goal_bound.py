# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-900: a goal bounded by an earlier goal's value, drawn the same by trainer and engine.

Run: ``CUDA_VISIBLE_DEVICES= python -m pytest training/test_goal_bound.py`` from the repo.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

from cadex_train import draw_goals

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "Mod" / "cadex"))
import CadexDynamics  # noqa: E402

RAD = 57.29577951308232
#: The bound a 4.9 m/s^2 lateral acceleration puts on a turn: mm/s x deg/s.
PRODUCT = 4.9 * 1000.0 * RAD


def goal(label, high, bands, **extra):
    return {"channels": [label], "kind": "value", "label": label, "name": label,
            "low": -high, "high": high, "nominal": [0.0], "unit": "1",
            "bands": bands, "resample_steps": 250, "segments": 4, **extra}


def task(bound=None, script=None):
    speed = goal("vx", 4000.0, [[0.0, 0.0, 0.1], [-4000.0, 4000.0, 0.9]])
    turn = goal("wz", 1.5 * RAD, [[0.0, 0.0, 0.5], [-1.5 * RAD, 1.5 * RAD, 0.5]])
    if bound is not None:
        turn["bound"] = bound
    if script is not None:
        turn["sequence"] = script
    return {"goal": [speed, turn]}


def both(spec, seed):
    return (draw_goals(None, None, spec, random.Random(seed)),
            CadexDynamics.draw_episode_goals(None, None, spec, random.Random(seed)))


def test_trainer_and_engine_draw_the_same_bounded_turns():
    for seed in range(200):
        trainer, engine = both(task({"goal": "vx", "product": PRODUCT}), seed)
        assert trainer == engine


def test_the_turn_stays_within_the_lateral_acceleration_and_the_stream_is_unchanged():
    asked = 0
    for seed in range(500):
        bounded, _ = both(task({"goal": "vx", "product": PRODUCT}), seed)
        free, _ = both(task(), seed)
        assert bounded[0] == free[0]  # the speed: no draw was added or moved
        for (v,), (w,), (w_free,) in zip(bounded[0]["segments"], bounded[1]["segments"],
                                        free[1]["segments"]):
            assert abs(v * w) <= PRODUCT * (1 + 1e-12)
            assert abs(w) <= 1.5 * RAD
            scale = 1.0 if v == 0 else min(1.0, PRODUCT / (abs(v) * 1.5 * RAD))
            assert w == pytest.approx(w_free * scale, abs=1e-12)
            asked += abs(v) > 3266.0 and w != 0.0
    assert asked > 0  # above 3.27 m/s the bound binds and turns are still asked for


def test_a_scripted_segment_holds_its_script():
    bounded, engine = both(task({"goal": "vx", "product": 1.0}, script=[60.0]), 3)
    assert bounded == engine
    assert bounded[1]["segments"][0] == [60.0]


@pytest.mark.parametrize("bound", [
    {"goal": "nobody", "product": PRODUCT},
    {"goal": "vx", "product": 0.0},
    {"goal": "wz", "product": PRODUCT},  # itself: not an earlier goal
])
def test_a_malformed_bound_is_refused_by_both(bound):
    with pytest.raises(SystemExit):
        draw_goals(None, None, task(bound), random.Random(0))
    with pytest.raises(CadexDynamics.DynamicsError) as refused:
        CadexDynamics.draw_episode_goals(None, None, task(bound), random.Random(0))
    assert refused.value.reason == "goal_bound_malformed"


def test_a_bound_on_a_goal_with_other_segments_is_refused():
    spec = task({"goal": "vx", "product": PRODUCT})
    spec["goal"][0]["segments"] = 2
    with pytest.raises(SystemExit):
        draw_goals(None, None, spec, random.Random(0))
    with pytest.raises(CadexDynamics.DynamicsError):
        CadexDynamics.draw_episode_goals(None, None, spec, random.Random(0))


def test_the_bound_is_stated_in_the_goal_algorithm():
    assert "bound {goal, product}" in CadexDynamics.GOAL_BOUND_ALGORITHM
