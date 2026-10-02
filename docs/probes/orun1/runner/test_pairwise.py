# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The pairwise judge's bookkeeping, pinned without a model call.

    pixi run python -m pytest docs/probes/orun1/runner/test_pairwise.py
"""

from __future__ import annotations

from itertools import combinations
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import metrics  # noqa: E402
import pairwise  # noqa: E402


def test_the_dev_split_is_29_designs_with_54_pairs_two_levels_apart():
    owner = metrics.split_verdicts('dev')
    assert len(owner) == 29
    assert not set(owner) & set(metrics.heldout())
    assert metrics.evaluate(owner, {d: 0 for d in owner})['pairwise_2plus']['pairs'] == 54


def test_order_is_stable_whichever_way_the_pair_is_given_and_roughly_balanced():
    designs = sorted(metrics.split_verdicts('dev'))
    assert pairwise.order('v1', designs[0], designs[1]) == pairwise.order('v1', designs[1], designs[0])
    flipped = sum(pairwise.order('v1', a, b) != (a, b) for a, b in combinations(designs, 2))
    assert 0.4 < flipped / 406 < 0.6


def test_parse_takes_a_or_b_and_refuses_anything_else():
    assert pairwise.parse('ok {"winner": "B", "reason": "r"}')['winner'] == 'B'
    for reply in ('no json', '{"winner": "tie"}', '{"winner": "a"}'):
        with pytest.raises(pairwise.JudgeError):
            pairwise.parse(reply)


def test_score_is_the_fraction_of_judged_comparisons_won():
    rows = [{'pair': ['x', 'y'], 'winner': 'x'}, {'pair': ['x', 'z'], 'winner': 'z'},
            {'pair': ['y', 'z'], 'winner': None}]
    assert pairwise.scores(['x', 'y', 'z'], rows) == {'x': 0.5, 'y': 0.0, 'z': 1.0}


def test_the_judge_is_told_nothing_about_designs_theses_or_verdicts():
    for version in pairwise.VERSIONS.values():
        text = version['instructions'].lower()
        for word in ('love', 'meh', 'thesis', 'sweep', 'verdict', 'heldout', 'held-out'):
            assert word not in text


def test_a_mirror_replicate_shows_every_pair_the_other_way_round():
    designs = sorted(metrics.split_verdicts('dev'))
    for a, b in combinations(designs, 2):
        assert pairwise.order('v2', a, b, mirror=True) == pairwise.order('v2', a, b)[::-1]


def test_the_frozen_version_is_byte_for_byte_what_the_readme_froze():
    assert set(pairwise.FROZEN) == {'v2'}
    for version, digest in pairwise.FROZEN.items():
        assert pairwise.instructions_sha256(version) == digest
        assert pairwise.VERSIONS[version]['views'] == ('hero.png',)
        assert pairwise.VERSIONS[version]['effort'] == 'high'
    assert pairwise.MODEL == 'claude-opus-5-5'


def test_only_a_frozen_version_may_judge_heldout_and_only_once(tmp_path, capsys):
    common = ['--split', 'heldout', '--inputs', str(tmp_path)]

    def refusal(*argv):
        assert pairwise.main([*argv, *common]) == 2
        return capsys.readouterr().err

    assert 'not a frozen version' in refusal('--version', 'v1', '--out', str(tmp_path / 'a'))
    assert 'not a frozen version' in refusal('--version', 'v2', '--mirror', '--out', str(tmp_path / 'b'))
    measured = tmp_path / 'c'
    measured.mkdir()
    (measured / 'summary.json').write_text('{}')
    assert 'measured once' in refusal('--version', 'v2', '--out', str(measured))
    # A fresh directory passes both guards and stops only at the missing renders.
    assert 'missing inputs' in refusal('--version', 'v2', '--out', str(tmp_path / 'd'))
