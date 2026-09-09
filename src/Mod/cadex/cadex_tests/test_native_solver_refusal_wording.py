# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A solver refusal names which of its two verdicts rejected the graph.

The Ondsel solver reports a status code and a set of diagnostic flags, and
they disagree routinely: a graph that comes back ``solved`` (code 0) can be
flagged redundant or malformed in the same breath. The refusal used to
interpolate the status verdict unconditionally, so an author whose graph was
rejected by the *diagnostics* read

    The isolated native Assembly solver rejected the graph with solved
    (code 0). Inspect details for conflicting, redundant, malformed, or
    ungrounded constraints.

which reads as a contradiction and names nothing actionable. The crank-slider
walk hit exactly this on its second script attempt.

These pin the two halves: the diagnostics are named, and a code-0 refusal no
longer claims the graph was "rejected ... with solved".
"""

from __future__ import annotations

import pytest

import cadex_assembly_worker as worker


def test_conflict_labels_name_each_flag() -> None:
    assert worker._diagnostics_conflict_labels({}) == []
    assert worker._diagnostics_conflict_labels({"has_redundancies": True}) == [
        "redundant constraints"
    ]
    assert worker._diagnostics_conflict_labels(
        {"has_conflicts": True, "has_malformed_constraints": True}
    ) == ["conflicting constraints", "malformed constraints"]


def test_conflict_bool_still_agrees_with_the_labels() -> None:
    for diagnostics in (
        {},
        {"has_conflicts": True},
        {"has_partial_redundancies": True},
        {"has_conflicts": False, "has_redundancies": False},
    ):
        assert worker._diagnostics_conflict(diagnostics) is bool(
            worker._diagnostics_conflict_labels(diagnostics)
        )


@pytest.mark.parametrize(
    "flag, label",
    [
        ("has_conflicts", "conflicting constraints"),
        ("has_redundancies", "redundant constraints"),
        ("has_partial_redundancies", "partially redundant constraints"),
        ("has_malformed_constraints", "malformed constraints"),
    ],
)
def test_every_flag_is_labelled(flag: str, label: str) -> None:
    assert worker._diagnostics_conflict_labels({flag: True}) == [label]


def test_the_flag_table_covers_the_bool_it_replaced() -> None:
    """The four flags the predicate has always read, and no fifth."""

    assert [name for name, _ in worker._DIAGNOSTIC_CONFLICT_LABELS] == [
        "has_conflicts",
        "has_redundancies",
        "has_partial_redundancies",
        "has_malformed_constraints",
    ]
