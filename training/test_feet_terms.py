# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-870: a task's stateful foot terms, Playground's feet_air_time and feet_height.

No jax and no device. ``feet_step`` is a pure function of numpy arrays, so the
order of MuJoCo Playground's ``joystick.py`` step (first contact on the
filtered contact, the timer advanced, the pay, then the clear) is checked by
hand on one foot's swing; ``feet_terms`` refuses a block that cannot be paid.
"""

from __future__ import annotations

import numpy as np
import pytest

from cadex_train import feet_step, feet_terms

NAMES = ["kfl_down", "kfr_down", "pfl_z", "pfr_z", "cx"]
DT = 0.02


def block(**extra):
    feet = {"contacts": ["kfl_down", "kfr_down"], "heights": ["pfl_z", "pfr_z"],
            "height_scale": 0.001, "active": "abs(cx)", "active_above": 10.0,
            "air_time": {"weight": 0.1 * DT, "threshold_s": 0.1}}
    feet.update(extra)
    return {"feet": feet}


def run(terms, contacts, heights, active=True):
    """Pay per step for one foot's sequence of down flags and heights."""

    memory = (np.zeros(1), np.zeros(1, dtype=bool), np.zeros(1))
    paid = []
    for down, z in zip(contacts, heights):
        pay, memory = feet_step(np, terms, memory, np.asarray([down]), np.asarray([z]),
                                np.asarray(active), DT)
        paid.append(float(pay))
    return paid, memory


def test_air_time_pays_once_at_touchdown_after_the_timer_runs():
    terms = feet_terms(block(), NAMES)
    # Down, then 9 steps up, then down twice: 10 ticks of air at the touchdown.
    contacts = [True] + [False] * 9 + [True, True]
    paid, (air, last, _peak) = run(terms, contacts, [0.0] * len(contacts))
    # Step 2 lifts off: the filtered contact still holds last step's, and the
    # timer is 0 there, so nothing is paid until the touchdown.
    assert paid[:10] == [0.0] * 10
    assert paid[10] == pytest.approx(0.1 * DT * (10 * DT - 0.1))
    assert paid[11] == 0.0
    assert air[0] == 0.0 and bool(last[0])


def test_a_foot_that_starts_in_the_air_pays_at_its_first_touchdown():
    # The reset starts the timer at 0 with no last contact (joystick.py's reset).
    terms = feet_terms(block(), NAMES)
    paid, _ = run(terms, [False, False, True], [0.0] * 3)
    assert paid[0] == 0.0
    assert paid[1] == 0.0
    assert paid[2] == pytest.approx(0.1 * DT * (3 * DT - 0.1))


def test_swing_height_pays_the_squared_shortfall_of_the_peak():
    terms = feet_terms(block(air_time=None,
                             swing_height={"weight": -0.2 * DT, "target_m": 0.1}), NAMES)
    heights = [0.0, 0.03, 0.06, 0.04, 0.0]
    paid, (_air, _last, peak) = run(terms, [True, False, False, False, True], heights)
    assert paid[:4] == [0.0] * 4
    assert paid[4] == pytest.approx(-0.2 * DT * (0.06 / 0.1 - 1.0) ** 2)
    assert peak[0] == 0.0


def test_nothing_is_paid_at_a_zero_command():
    terms = feet_terms(block(), NAMES)
    paid, _ = run(terms, [True] + [False] * 9 + [True], [0.0] * 11, active=False)
    assert paid == [0.0] * 11


def test_a_block_that_cannot_be_paid_is_refused():
    assert feet_terms({}, NAMES) is None
    with pytest.raises(SystemExit, match="lacks"):
        feet_terms(block(contacts=["kfl_down", "khl_down"]), NAMES)
    with pytest.raises(SystemExit, match="neither"):
        feet_terms(block(air_time=None), NAMES)
    with pytest.raises(SystemExit, match="one height channel per foot"):
        feet_terms(block(heights=["pfl_z"], swing_height={"weight": -1, "target_m": 0.1}),
                   NAMES)
