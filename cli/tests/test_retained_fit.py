# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay retained OCCT measurements, without a build or operator projects."""
import json
from collections import Counter
from pathlib import Path

import pytest

from cadex_cli.clearance import fit_summary, sweep_summary

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


#: The twelve pairs Heron's script welds, from its own ``weld()`` calls. Finch
#: and Robin's welds follow a rule rather than a list, so they are derived
#: below the way their scripts write them.
HERON_WELDS = [
    ('comp_base', 'comp_servo_shoulder'), ('comp_base', 'comp_bearing_shoulder'),
    ('comp_base', 'comp_tabscrew_shoulder_0'), ('comp_base', 'comp_tabscrew_shoulder_1'),
    ('comp_upper_arm', 'comp_horn_shoulder'), ('comp_upper_arm', 'comp_centrescrew_shoulder'),
    ('comp_upper_arm', 'comp_servo_elbow'), ('comp_upper_arm', 'comp_bearing_elbow'),
    ('comp_upper_arm', 'comp_tabscrew_elbow_0'), ('comp_upper_arm', 'comp_tabscrew_elbow_1'),
    ('comp_forearm', 'comp_horn_elbow'), ('comp_forearm', 'comp_centrescrew_elbow'),
]


def _welded_pairs(name, components):
    """Every pair an unsuppressed ``fixed`` joint welds, read off the script."""
    if name == 'finch':
        # `purchase()` welds each bought part to the link it rides: the servo,
        # its two tab screws and the bearing to the parent, the horn and the
        # centre screw to the child.
        pairs = set()
        for side in ('l', 'r'):
            for tag, parent, child in ((f'hip_{side}', 'pelvis', f'thigh_{side}'),
                                       (f'knee_{side}', f'thigh_{side}', f'shin_{side}')):
                for part in (f'servo_{tag}', f'tabscrew_{tag}_0',
                             f'tabscrew_{tag}_1', f'bearing_{tag}'):
                    pairs.add(frozenset((f'{parent}_link', f'{part}_link')))
                for part in (f'horn_{tag}', f'centrescrew_{tag}'):
                    pairs.add(frozenset((f'{child}_link', f'{part}_link')))
        return pairs
    if name == 'robin':
        # Everything but the two wheels is welded to the chassis.
        return {frozenset(('comp_chassis', c)) for c in components
                if c not in ('comp_chassis', 'comp_wheel_l', 'comp_wheel_r')}
    return {frozenset(pair) for pair in HERON_WELDS}


@pytest.mark.parametrize('name,failing,exempt', [
    ('finch', 44, 16), ('robin', 39, 11), ('heron', 20, 8),
])
def test_weld_exemption_would_clear_exactly_these(name, failing, exempt):
    """What ADR-372 changes about these three, and what it leaves alone.

    The retained rows themselves are untouched: they were published by the
    engine that accepted them and carry no intent, which is why the numbers
    above this test are stable. This pins the *other* half, the one
    `docs/probes/ot7/REGRESSION.md` states — what the same measurements say
    under ADR-372's weld exemption alone, by handing `fit_summary` the
    `attached` intent the engine now implies for a welded pair. Overlap under
    a weld still fails, and a pair that merely shares a host is not welded to
    anything. This models no other checker change and is not a fresh-build
    verdict: nothing here rebuilds a design, so ADR-370's attachment block and
    ADR-371's sweep coverage are outside it.
    """
    value = json.loads((RECEIPTS / f'{name}.measurements.json').read_text())
    components = value.pop('components')
    welds = _welded_pairs(name, components)
    value['pairs'] = [
        dict(first=components[a], second=components[b], distance_mm=d,
             common_volume_mm3=v,
             **({'intent': {'kind': 'attached', 'minimum_mm': 0.0}}
                if frozenset((components[a], components[b])) in welds else {}))
        for a, b, d, v in value.pop('measurements')
    ]
    assert sum('intent' in row for row in value['pairs']) == len(welds)
    before = {(a, b) for a, b, *_ in json.loads(
        (RECEIPTS / 'comparison.json').read_text())['designs'][name]['failing']}
    summary = fit_summary(value)
    after = {(r['first'], r['second']) for r in summary['failing']}
    assert summary['failing_count'] == failing - exempt
    cleared = before - after
    assert len(cleared) == exempt + (2 if name == 'heron' else 0)
    # Every pair the weld clears was a zero-volume gap under the default, and
    # no intersection was silenced by it.
    assert all(frozenset(p) in welds for p in cleared
               if p not in ROUNDING_PAIRS) and summary['counts']['intersection'] == {
        'finch': 12, 'robin': 8, 'heron': 6}[name]


@pytest.mark.parametrize('name,welded,not_touching,distances', [
    ('finch', 24, 0, {}),
    ('robin', 21, 10, {0.3: 2, 0.6: 8}),
    ('heron', 12, 0, {}),
])
def test_welded_pairs_that_do_not_meet(name, welded, not_touching, distances):
    """What ADR-370's block would say about these three, if they had one.

    `docs/probes/ot7/REGRESSION.md` states this as the reason its
    weld-exemption table is not a fresh-build verdict: the exemption reads a
    weld as *these two are one body*, and on Robin ten of those welds hold
    nothing — the chassis stands 0.3 mm off each motor and 0.6 mm off each
    board and clamp screw. The retained receipts publish no `attachments` key,
    so nothing in them reports it; a rebuild would. Same tolerance ADR-370
    uses for `touching`.
    """
    value = json.loads((RECEIPTS / f'{name}.measurements.json').read_text())
    components = value['components']
    welds = _welded_pairs(name, components)
    assert 'attachments' not in value
    measured = [(components[a], components[b], d) for a, b, d, _
                in value['measurements']
                if frozenset((components[a], components[b])) in welds]
    assert len(measured) == welded == len(welds)
    apart = [row for row in measured if row[2] > 0.001]
    assert len(apart) == not_touching
    assert Counter(round(d, 3) for _, _, d in apart) == Counter(distances)


@pytest.mark.parametrize('name', ['finch', 'robin', 'heron'])
def test_the_retained_receipts_publish_no_sweep_to_roll_up(name):
    """Why ADR-371 and ADR-374 are outside the weld-exemption table.

    `docs/probes/ot7/REGRESSION.md` says both swept-side changes are outside
    its two columns because there is no joint row here for either of them to
    read. ADR-374 reads a joint row's three numbers over the pairs that joint
    moves and counts them as `pairs_moving`; a receipt with no joint row has
    no such number to move, in either direction. Pin that through the product
    surface rather than the raw key, so the receipt's claim and
    `sweep_summary` cannot drift apart.
    """
    value = json.loads((RECEIPTS / f'{name}.measurements.json').read_text())
    summary = sweep_summary(value)
    assert summary['verdict'] == 'unavailable'
    assert summary['coverage'] == 'unavailable'
    assert summary['joints'] == [] and summary['joints_checked'] == 0
    assert summary['failing'] == [] and summary['failing_count'] == 0
    assert not any('pairs_moving' in row for row in summary['joints'])
    assert 'No published sweep' in summary['reason']


@pytest.mark.parametrize('name', ['finch', 'robin', 'heron'])
def test_adr_379_moves_no_retained_number(name):
    """A retained row carries no intent at all, so the weld contradiction cannot fire.

    ADR-379 fails a pair that is welded *and* declares a running clearance,
    and it reads that from the `joints` the engine publishes on such a
    declaration. A retained receipt is the measurement the accepting engine
    published: these three carry no `intent` key on any row, so every count
    in `docs/probes/ot7/REPORT.md` is untouched by construction rather than
    by luck. The twenty `clearance.json` receipts in the operator's `ot7-*`
    projects carry no such row either, measured while the rule landed, but
    they are outside this checkout and are not replayed here.
    """
    value = json.loads((RECEIPTS / f'{name}.measurements.json').read_text())
    components = value.pop('components')
    value['pairs'] = [
        dict(first=components[a], second=components[b], distance_mm=d,
             common_volume_mm3=v)
        for a, b, d, v in value.pop('measurements')
    ]
    assert all('intent' not in row for row in value['pairs'])
    counts = fit_summary(value)['counts']
    assert 'clearance under weld' not in counts
