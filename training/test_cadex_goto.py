# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-839: one go-to-point source for training and the judge.

Run: ``CUDA_VISIBLE_DEVICES= python -m pytest training/test_cadex_goto.py`` from the repo.
"""

from __future__ import annotations

import math

import numpy as np

from cadex_goto import layer_start, layer_step, sequence, stack

BANDS = [{"name": "walk", "low": 0.4, "high": 0.7}, {"name": "run", "low": 1.0, "high": 1.5}]
LIMITS = {"vx": [-1.5, 1.5], "vy": [-0.8, 0.8], "wz": [-1.2, 1.2]}


def test_a_sequence_is_its_seed_and_split_and_honours_its_shape() -> None:
    a = sequence(3, split="heldout", bands=BANDS)
    assert a == sequence(3, split="heldout", bands=BANDS)
    assert a["points"] != sequence(3, split="train", bands=BANDS)["points"]
    kinds = [p["bearing"] for p in a["points"]]
    assert len(kinds) == 8 and kinds.count("behind") >= 2 and kinds.count("side") >= 2
    assert sum(p["hold_s"] > 0 for p in a["points"]) >= 2
    for p in a["points"]:
        band = next(b for b in BANDS if b["name"] == p["band"])
        assert band["low"] <= p["speed_mps"] <= band["high"]


def test_the_next_point_lights_on_arrival_and_after_the_hold_not_on_a_clock() -> None:
    plan = stack(np, [{"points": [{"xy_m": [1.0, 0.0], "speed_mps": 1.0, "hold_s": 0.5},
                                  {"xy_m": [1.0, 3.0], "speed_mps": 1.0, "hold_s": 0.0}]}])
    state = layer_start(np, [1])
    one = lambda x, y, yaw=0.0: layer_step(np, plan, state, np.array([x]), np.array([y]),  # noqa: E731
                                           np.array([yaw]), 0.02, LIMITS)
    # Far from the first point, any number of steps: it stays lit, and the command heads there.
    for _ in range(500):
        state, command = one(-2.0, 0.0)
    assert int(state["index"][0]) == 0 and command["vx"][0] > 0.9 and abs(command["wz"][0]) < 1e-6
    # Behind the robot: it turns in place, toward the point.
    state, command = one(2.0, 0.0)
    assert command["vx"][0] == 0.0 and abs(command["wz"][0]) == 1.2
    # On the point: held for 0.5 s (25 steps of 0.02 s), then the next point lights.
    for _ in range(24):
        state, command = one(1.0, 0.0)
        assert int(state["index"][0]) == 0 and bool(state["arrived"][0])
    for _ in range(2):
        state, command = one(1.0, 0.0)
    assert int(state["index"][0]) == 1 and command["wz"][0] == 1.2
    # A point with no hold is passed on arrival; past the last one the command is zero.
    state, command = one(1.0, 2.9, math.pi / 2)
    assert int(state["index"][0]) == 2 and all(float(v[0]) == 0.0 for v in command.values())
