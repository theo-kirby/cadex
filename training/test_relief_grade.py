# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-980: --relief-grade sets the hills' grade range the relief fields draw from.

Run: ``CUDA_VISIBLE_DEVICES= python -m pytest training/test_relief_grade.py`` from the repo.
"""

from __future__ import annotations

import numpy as np
import pytest

import cadex_goto as G
import cadex_train as T


def sprint(*extra: str):
    return T.arguments(["bundle.json", "--out", "x.cxpolicy", "--race-terrain", "u1",
                        "--relief-strip", "20", *extra])


def test_off_by_default_leaves_the_rule_and_fields_as_they_were() -> None:
    rule = T.relief_rule(sprint("--relief-levels", "3", "--relief-fields", "graded"))
    assert "grade_deg" not in rule
    low, high = G.RACE_TERRAIN["grade_deg"]
    fields = T.relief_fields(np, rule, 2)
    assert fields[-1]["drawn"]["grade_deg"] == pytest.approx(high)


def test_graded_rough_grades_the_hills_inside_the_given_range() -> None:
    rule = T.relief_rule(sprint("--relief-levels", "4", "--relief-fields", "graded-rough",
                                "--relief-grade", "4,10"))
    assert rule["grade_deg"] == [4.0, 10.0]
    fields = T.relief_fields(np, rule, 7)
    assert fields[0]["kind"] == "rough"
    assert [f["drawn"]["grade_deg"] for f in fields[1:]] == pytest.approx([6.0, 8.0, 10.0])
    for f in fields[1:]:
        raw = G.strip_terrain(np, "u1", 7 * 4 + f["level"] - 1, length_m=20.0,
                              grade_deg=(f["drawn"]["grade_deg"],) * 2)
        assert np.array_equal(f["heights_mm"], raw["heights_mm"])
        assert f["hill_grade_deg"] <= 10.0 + 0.05


def test_graded_and_scaled_take_the_range_too() -> None:
    graded = T.relief_fields(np, T.relief_rule(sprint("--relief-levels", "2", "--relief-fields",
                                                      "graded", "--relief-grade", "6,8")), 1)
    assert [f["drawn"]["grade_deg"] for f in graded] == pytest.approx([7.0, 8.0])
    scaled = T.relief_fields(np, T.relief_rule(sprint("--relief-levels", "2",
                                                      "--relief-grade", "5,6")), 1)
    top = scaled[-1]
    assert 5.0 - 1e-6 <= top["drawn"]["grade_deg"] <= 6.0 + 1e-6
    assert top["hill_grade_deg"] <= 6.0 + 0.05


@pytest.mark.parametrize("bad", ["10,4", "0,5", "5", "5,50", "a,b"])
def test_refused_out_of_bounds(bad: str) -> None:
    with pytest.raises(SystemExit):
        T.relief_rule(sprint("--relief-grade", bad))


def test_refused_on_relief_without_hills() -> None:
    with pytest.raises(SystemExit):
        T.relief_rule(T.arguments(["b.json", "--out", "x.cxpolicy", "--race-terrain", "rough",
                                   "--relief-grade", "4,10"]))
