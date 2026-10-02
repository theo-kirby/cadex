# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The D1 metrics, pinned before any held-out judge call.

    pixi run python -m pytest docs/probes/orun1/runner/test_metrics.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import metrics  # noqa: E402


def test_the_counted_split_is_26_heldout_designs_with_37_pairs_two_levels_apart():
    owner = metrics.heldout()
    assert len(owner) == 26
    assert sorted(owner.values()).count(3) == 2 and sorted(owner.values()).count(0) == 1
    result = metrics.evaluate(owner, {d: 0 for d in owner})
    assert result['pairwise_2plus']['pairs'] == 37
    assert result['kendall']['pairs'] == 325
    assert result['love_over_no']['pairs'] == 2


def test_a_tie_is_a_disagreement_and_is_counted():
    owner = {'love': 3, 'meh': 1, 'no': 0}
    result = metrics.pairwise(owner, {'love': 10, 'meh': 10, 'no': 5})
    # love>meh tie, love>no agree, meh-no differ by 1 so not counted
    assert (result['pairs'], result['agree'], result['ties'], result['disagree']) == (2, 1, 1, 0)
    assert result['agreement'] == 0.5
    assert result['tied_pairs'] == [['love', 'meh']]
    assert not result['meets_bar']


def test_the_bar_is_eighty_percent_and_inclusive():
    owner = {f'l{i}': 3 for i in range(5)} | {'n': 0}
    score = {f'l{i}': 9 for i in range(5)} | {'n': 5}
    score['l0'] = 1
    result = metrics.pairwise(owner, score)
    assert result['agreement'] == 0.8 and result['meets_bar']


def test_love_over_no_is_strict():
    owner = {'a': 3, 'b': 3, 'z': 0}
    assert metrics.love_over_no(owner, {'a': 12, 'b': 11, 'z': 10})['holds']
    tied = metrics.love_over_no(owner, {'a': 12, 'b': 10, 'z': 10})
    assert not tied['holds'] and tied['failed_pairs'] == [['b', 'z']]


def test_tau_b_matches_scipy_with_ties_on_both_sides():
    scipy_stats = pytest.importorskip('scipy.stats')
    owner = {'a': 3, 'b': 2, 'c': 2, 'd': 1, 'e': 1, 'f': 1, 'g': 0}
    score = {'a': 14, 'b': 9, 'c': 12, 'd': 9, 'e': 7, 'f': 12, 'g': 7}
    ours = metrics.kendall_tau_b(owner, score)
    ids = sorted(owner)
    theirs = scipy_stats.kendalltau([owner[i] for i in ids], [score[i] for i in ids], variant='b')
    assert ours['tau_b'] == pytest.approx(theirs.statistic)
    assert ours['counted'] == 21
    assert sum(ours[k] for k in ('concordant', 'discordant', 'tied_owner_only',
                                 'tied_judge_only', 'tied_both')) == 21


def test_a_missing_design_drops_its_pairs_and_fails_the_bar():
    owner = {'a': 3, 'b': 1, 'c': 0}
    result = metrics.evaluate(owner, {'a': 9, 'c': 1})
    assert result['missing'] == ['b']
    assert result['pairwise_2plus']['dropped_pairs'] == [['a', 'b']]
    assert result['pairwise_2plus']['agreement'] == 1.0
    assert not result['pairwise_2plus']['meets_bar']
    assert result['kendall']['dropped_pairs'] == [['a', 'b'], ['b', 'c']]
