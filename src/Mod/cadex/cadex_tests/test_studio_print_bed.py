# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The print-bed hero (orun4 H2, ADR-569): parts laid flat, packed and drawn.

``CadexStudio.lay_flat`` seats a part on its largest flat face it can rest
on; ``pack_beds`` packs footprints onto as few beds as it takes, never
overlapping and never closer than the gap to each other or to an edge;
``print_bed`` draws the printed parts only, numbered, with the purchased
hardware listed beside them.
"""
from __future__ import annotations

import math
import random
import struct

import pytest

import CadexStudio

PNG = b'\x89PNG\r\n\x1a\n'
QUADS = ((0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5))


def _box(lo, hi):
    """A box as outward triangles."""
    c = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    return [tri for a, b, e, f in QUADS for tri in ((c[a], c[b], c[e]), (c[a], c[e], c[f]))]


def _turn(tris, axis, degrees):
    """``tris`` turned about the X or Y axis through the origin."""
    cs, sn = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))

    def one(p):
        x, y, z = p
        return (x, cs*y - sn*z, sn*y + cs*z) if axis == 'x' else (cs*x + sn*z, y, -sn*x + cs*z)
    return [tuple(one(p) for p in tri) for tri in tris]


def _extent(tris):
    points = [p for tri in tris for p in tri]
    return ([min(p[j] for p in points) for j in range(3)], [max(p[j] for p in points) for j in range(3)])


def test_a_tilted_plate_is_seated_on_its_broad_face():
    plate = _turn(_turn(_box((0, 0, 0), (40, 20, 4)), 'x', 63.0), 'y', 31.0)
    flat, facts = CadexStudio.lay_flat(plate)
    lo, hi = _extent(flat)
    assert lo == pytest.approx([0, 0, 0], abs=1e-6)
    assert hi == pytest.approx([40, 20, 4], abs=1e-6)
    assert facts['footprint_mm'] == pytest.approx([40, 20], abs=1e-6)
    assert facts['height_mm'] == pytest.approx(4, abs=1e-6)
    assert facts['seat'] == 'largest flat face'
    assert facts['seat_area_mm2'] == pytest.approx(800, abs=0.1)


def test_a_face_with_material_beyond_it_is_not_a_seat():
    # A 50 mm table top on a 10 mm leg: the top's underside is as large as
    # its upper face, but the leg stands below it, so only the upper face
    # (turned to the bed) can carry the part.
    table = _box((0, 0, 10), (50, 50, 12)) + _box((20, 20, 0), (30, 30, 10))
    flat, facts = CadexStudio.lay_flat(table)
    lo, hi = _extent(flat)
    assert facts['height_mm'] == pytest.approx(12, abs=1e-6)
    assert facts['footprint_mm'] == pytest.approx([50, 50], abs=1e-6)
    # The leg now points up, away from the bed.
    leg = [p for tri in flat[12:] for p in tri]
    assert min(p[2] for p in leg) == pytest.approx(2, abs=1e-6)


def test_a_part_with_no_flat_face_keeps_its_attitude():
    # Four fins round a centre, each in a vertical plane through it: every
    # fin's plane has the others on both sides, so none can carry the part.
    fins = [((20, 0, 0), (30, 0, 0), (25, 0, 20)), ((-20, 0, 0), (-25, 0, 20), (-30, 0, 0)),
            ((0, 20, 0), (0, 25, 20), (0, 30, 0)), ((0, -20, 0), (0, -30, 0), (0, -25, 20))]
    flat, facts = CadexStudio.lay_flat(fins)
    assert facts['seat'] == 'as assembled (no flat face)'
    lo, hi = _extent(flat)
    assert lo == pytest.approx([0, 0, 0], abs=1e-6)
    # Turned a quarter-diagonal to its smallest footprint: the diamond's square.
    assert hi == pytest.approx([30 * math.sqrt(2), 30 * math.sqrt(2), 20], abs=1e-6)


def _assert_packed(footprints, placements, bed, gap):
    by_bed = {}
    for (w, d), (index, x, y, turned) in zip(footprints, placements):
        if turned:
            w, d = d, w
        if w <= bed[0] - 2 * gap and d <= bed[1] - 2 * gap:
            assert x >= gap - 1e-9 and y >= gap - 1e-9
            assert x + w <= bed[0] - gap + 1e-9 and y + d <= bed[1] - gap + 1e-9
        by_bed.setdefault(index, []).append((x, y, w, d))
    for rects in by_bed.values():
        for i, (ax, ay, aw, ad) in enumerate(rects):
            for bx, by, bw, bd in rects[i + 1:]:
                apart = (ax + aw + gap <= bx + 1e-9 or bx + bw + gap <= ax + 1e-9 or
                         ay + ad + gap <= by + 1e-9 or by + bd + gap <= ay + 1e-9)
                assert apart, ((ax, ay, aw, ad), (bx, by, bw, bd))
    return by_bed


def test_packed_parts_never_overlap_and_stay_inside_the_bed():
    rng = random.Random(569)
    bed, gap = (256.0, 256.0, 256.0), 6.0
    for _ in range(40):
        footprints = [(rng.uniform(5, 150), rng.uniform(5, 90)) for _ in range(rng.randint(1, 25))]
        placements = CadexStudio.pack_beds(footprints, bed, gap)
        by_bed = _assert_packed(footprints, placements, bed, gap)
        assert sorted(by_bed) == list(range(len(by_bed)))


def test_parts_that_cannot_share_a_bed_go_on_more_beds():
    bed, gap = (256.0, 256.0, 256.0), 6.0
    placements = CadexStudio.pack_beds([(200, 200)] * 3 + [(40, 30)], bed, gap)
    assert sorted({p[0] for p in placements}) == [0, 1, 2]
    assert placements[3][0] in (0, 1, 2)
    _assert_packed([(200, 200)] * 3 + [(40, 30)], placements, bed, gap)


def test_a_long_part_is_turned_and_an_oversize_part_gets_its_own_bed():
    bed, gap = (200.0, 300.0, 200.0), 5.0
    placements = CadexStudio.pack_beds([(250, 20), (400, 50), (30, 30)], bed, gap)
    assert placements[0][3] is True
    assert placements[1][0] not in (placements[0][0], placements[2][0])
    _assert_packed([(250, 20), (400, 50), (30, 30)], placements, bed, gap)


def _snapshot():
    """A printed plate standing on edge, a printed block, a purchased pin, a cut
    catalog part and a floor, as :func:`CadexStudio.snapshot` returns them."""
    shapes = (('c_plate', 'plate', _turn(_box((0, 0, 0), (60, 30, 3)), 'x', 90.0)),
              ('c_block', 'block', _box((70, 0, 0), (90, 25, 15))),
              ('c_pin', 'pin', _box((100, 0, 0), (105, 5, 30))),
              ('c_horn', 'horn', _box((110, 0, 0), (120, 10, 4))),
              ('c_floor', 'floor', _box((-500, -500, -2), (500, 500, 0))))
    triangles, objects = [], {}
    for name, source, tris in shapes:
        objects[name] = {'first': len(triangles), 'triangles': len(tris), 'source': source,
                         'color': (91, 157, 205), 'placement': None,
                         'bounds_mm': list(_extent(tris))}
        triangles += [((91, 157, 205), tri) for tri in tris]
    return triangles, {'revision': 'b' * 64, 'objects': objects}


FIT = {'failing': [{'first': 'c_floor', 'status': 'world geometry'}]}
INVENTORY = {'available': True, 'uncatalogued_sources': ['block', 'floor', 'horn', 'plate'],
             'derived_catalog_sources': [{'source_output': 'horn', 'family': 'horn', 'part_number': '25t'}],
             'catalog_counts': {'bolt/m2x6-socket': 4, 'servo/sts3215': 2},
             'appearance': {}, 'palette': {}}


def test_the_print_bed_draws_the_printed_parts_and_lists_the_hardware():
    triangles, summary = _snapshot()
    image, facts = CadexStudio.print_bed(triangles, summary, FIT, INVENTORY, name='scratch')
    assert image.startswith(PNG)
    assert struct.unpack('>2I', image[16:24]) == CadexStudio.BED_IMAGE
    assert [row['component'] for row in facts['parts']] == ['c_plate', 'c_block']
    assert [row['number'] for row in facts['parts']] == [1, 2]
    assert facts['beds'] == 1 and facts['not_fitting'] == []
    plate = facts['parts'][0]
    assert plate['height_mm'] == pytest.approx(3, abs=1e-6)
    assert sorted(plate['footprint_mm']) == pytest.approx([30, 60], abs=0.01)
    assert facts['hardware'] == [{'count': 4, 'part': 'bolt m2x6-socket'},
                                 {'count': 2, 'part': 'servo sts3215'},
                                 {'count': 1, 'part': 'horn 25t, cut'}]
    assert facts['revision'] == 'b' * 64


def test_a_small_bed_spreads_the_parts_and_names_what_does_not_fit():
    triangles, summary = _snapshot()
    image, facts = CadexStudio.print_bed(triangles, summary, FIT, INVENTORY, bed=(40.0, 40.0, 10.0))
    assert image.startswith(PNG)
    assert facts['beds'] == 2
    # The plate is longer than the bed; the block is taller than it.
    assert facts['not_fitting'] == ['c_plate', 'c_block']


def test_the_print_bed_refuses_without_an_inventory():
    triangles, summary = _snapshot()
    with pytest.raises(CadexStudio.StudioError, match='no inventory'):
        CadexStudio.print_bed(triangles, summary, FIT, None)
    with pytest.raises(CadexStudio.StudioError, match='no printed part'):
        CadexStudio.print_bed(triangles, summary, FIT, {**INVENTORY, 'uncatalogued_sources': ['floor']})
