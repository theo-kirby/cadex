# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay retained OCCT measurements, without a build or operator projects."""
import json
from collections import Counter
from pathlib import Path

import pytest

from cadex_cli.clearance import fit_summary

RECEIPTS = Path(__file__).resolve().parents[2] / 'docs/probes/ot7/retained'
ROUNDING_PAIRS = {
    ('comp_upper_arm', 'comp_bearing_shoulder'),
    ('comp_forearm', 'comp_bearing_elbow'),
}


@pytest.mark.parametrize('name,pairs,overlaps,seatings,gaps', [
    ('finch', 406, 12, 28, 4),
    ('robin', 276, 8, 29, 2),
    ('heron', 105, 6, 14, 0),
])
def test_retained_comparison_and_explained_differences(name, pairs, overlaps, seatings, gaps):
    """Every old finding persists except Heron's two nominal 0.1 mm gaps.

    ot6 allowed thread engagement and checked seats explicitly. The product
    reports overlap even with intent, and these old scripts have no intent.
    Replay *all* pairs so a new failure on a formerly clear pair is caught too.
    """
    value = json.loads((RECEIPTS / f'{name}.measurements.json').read_text())
    components = value.pop('components')
    value['pairs'] = [
        dict(first=components[a], second=components[b], distance_mm=d,
             common_volume_mm3=v)
        for a, b, d, v in value.pop('measurements')
    ]
    original = json.loads((RECEIPTS / 'comparison.json').read_text())['designs'][name]
    assert value['revision'] == original['revision']
    assert len(value['pairs']) == pairs
    assert len({(r['first'], r['second']) for r in value['pairs']}) == pairs
    summary = fit_summary(value)
    expected = {(a, b): (status, d, v) for a, b, status, d, v in original['failing']}
    if name == 'heron':
        for pair in ROUNDING_PAIRS:
            status, distance, volume = expected.pop(pair)
            assert status == 'below clearance'
            assert distance == pytest.approx(0.1, abs=1e-12)
            assert volume == 0
    assert {(r['first'], r['second']):
            (r['status'], r['distance_mm'], r['common_volume_mm3'])
            for r in summary['failing']} == expected
    assert summary['verdict'] == 'fail'
    assert summary['pairs_checked'] == pairs
    assert summary['failing_count'] == overlaps + seatings + gaps
    assert summary['counts'] == {
        'clear': pairs - overlaps - seatings - gaps,
        'intersection': overlaps, 'below clearance': seatings + gaps, 'unknown': 0,
    }

    # Pin the numerical explanation, independently of the old status column.
    near = [r for r in summary['failing'] if r['status'] == 'below clearance']
    assert sum(abs(r['distance_mm']) < 1e-9 for r in near) == seatings
    assert sum(abs(r['distance_mm'] - 0.05) < 1e-9 for r in near) == gaps
    volumes = Counter(round(r['common_volume_mm3'], 5)
                      for r in summary['failing'] if r['status'] == 'intersection')
    assert volumes == {
        'finch': Counter({4.07150: 8, 7.85398: 4}),
        'robin': Counter({4.85222: 8}),
        'heron': Counter({4.07150: 4, 9.42478: 2}),
    }[name]
    assert value['world_geometry'] == []
    assert value['clearance_sweep']['status'] == 'unavailable'
