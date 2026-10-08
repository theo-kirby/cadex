# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""What a part is made of, beside the role it plays (ADR-603).

A catalog fastener or bearing is drawn as metal and a catalog board as a
PCB, whatever appearance role it declares; any other catalog part keeps its
role's colour in a moulded satin; a printed part is drawn as before. The
board's chip and pads are painted by where a point lies in the catalog
board's frame, and only on a mesh that is the catalog board. One rule for
every image, film, video and the viewport (``review_server.part_looks``).
"""
from __future__ import annotations

import math

import pytest

import CadexStudio as studio
from CadexCatalog import BOARDS

ESP = 'esp32-devkitc-v4'


def _summary(*names):
    return {'objects': {name: {'source': name, 'color': (1, 2, 3)} for name in names}}


@pytest.mark.parametrize('family, metal', [('bolt', 'black_oxide'), ('nut', 'black_oxide'),
                                           ('washer', 'steel'), ('bearing', 'steel'),
                                           ('bushing', 'steel'), ('heat_insert', 'brass')])
def test_fasteners_and_bearings_are_metal(family, metal) -> None:
    assert studio.finish_class(family) == 'hardware'
    assert studio.HARDWARE_METALS[family] == metal
    assert studio.METALS[metal][1][2] == 1.0          # a mirror, not a plastic


def test_the_classes_follow_the_family_then_the_supplier() -> None:
    assert studio.finish_class('board') == 'board'
    for family in ('servo', 'gearmotor', 'battery', 'bldc', 'qdd', 'wheel', 'tyre', 'gear'):
        assert studio.finish_class(family) == 'purchased', family
    assert studio.finish_class(None, purchased=True) == 'purchased'
    assert studio.finish_class(None) == 'printed'
    # The hook for ground stock: no family is catalogued yet, one added is steel.
    assert {studio.HARDWARE_METALS[f] for f in ('shaft', 'dowel', 'pin')} == {'steel'}
    assert studio.FINISH_CLASSES == ('printed', 'purchased', 'hardware', 'board')


def test_hardware_and_boards_override_the_declared_role_and_printed_parts_keep_it() -> None:
    catalog = {'bolt': {'family': 'bolt', 'part_number': 'm3x12-socket'},
               'esp': {'family': 'board', 'part_number': ESP},
               'servo': {'family': 'servo', 'part_number': 'mg90s'}}
    looks = studio.materials(_summary('bolt', 'esp', 'servo', 'cap', 'body'),
                             purchased={'bolt', 'esp', 'servo'},
                             appearance={'bolt': 'accent', 'esp': 'shell', 'servo': 'accent', 'cap': 'accent'},
                             catalog=catalog)
    accent = studio.ROLE_COLORS['accent']
    # Declared accent, drawn black oxide: the role stays, the colour is the metal's.
    assert looks['bolt'] == ('accent', studio.METALS['black_oxide'][0])
    assert looks['bolt'].finish == 'hardware' and looks['bolt'].role_rgb == accent
    assert looks['bolt'].catalog == catalog['bolt']
    assert looks['esp'] == ('shell', studio.BOARD_LOOK['mask'][0]) and looks['esp'].finish == 'board'
    # A purchased servo and a printed cap keep the colour they declare.
    assert looks['servo'] == ('accent', accent) and looks['servo'].finish == 'purchased'
    assert looks['cap'] == ('accent', accent) and looks['cap'].finish == 'printed'
    assert looks['body'] == ('shell', studio.ROLE_COLORS['shell']) and looks['body'].finish == 'printed'
    # What each is drawn with: the metal's finish, the purchased satin, the role's own.
    assert studio.material(looks['bolt']) == (studio.METALS['black_oxide'][0], studio.METALS['black_oxide'][1])
    assert studio.material(looks['servo']) == (accent, studio.PURCHASED_FINISH)
    assert studio.material(looks['cap']) == (accent, studio.FINISH['accent'])
    # Without a catalog the rule is the old one, and a plain pair still draws.
    plain = studio.materials(_summary('bolt'), purchased={'bolt'})
    assert plain['bolt'] == ('mechanism', studio.ROLE_COLORS['mechanism'])
    assert plain['bolt'].finish == 'purchased'
    assert studio.material(('shell', (9, 9, 9))) == ((9, 9, 9), studio.FINISH['shell'])


def test_the_catalog_rows_come_from_any_inventory_shape() -> None:
    summary = {'objects': {'c_bolt': {'source': 'bolt'}, 'c_esp': {'source': 'esp'},
                           'c_horn': {'source': 'horn_cut'}, 'c_body': {'source': 'body'}}}
    block = {'catalog_by_component': {'c_bolt': {'family': 'bolt', 'part_number': 'm3x8-socket'}},
             'components': [{'component': 'c_esp', 'catalog': {'family': 'board', 'part_number': ESP}},
                            {'component': 'c_body'}],
             'derived_catalog_sources': [{'source_output': 'horn_cut', 'family': 'servo_horn',
                                          'part_number': 'mg90s-cross'}]}
    assert studio.catalogued(summary, block) == {
        'c_bolt': {'family': 'bolt', 'part_number': 'm3x8-socket'},
        'c_esp': {'family': 'board', 'part_number': ESP},
        'c_horn': {'family': 'servo_horn', 'part_number': 'mg90s-cross'},
    }
    assert studio.catalogued(summary, None) == {} == studio.catalogued(summary, {'available': False, **block})


def _board_mesh(spec, turn=0, shift=(0.0, 0.0, 0.0)):
    """The PCB and chip box ``lib.board`` builds, as triangles, turned a quarter
    ``turn`` times about +Z and shifted: a script moving it before it publishes."""
    w, l, t = spec['width_mm'], spec['length_mm'], spec['thickness_mm']
    (ox, oy, oz), (sx, sy, sz) = spec['cosmetic_origin'], spec['cosmetic_size']

    def box(x0, y0, z0, x1, y1, z1):
        v = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
        faces = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1),
                 (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
        return [tuple(v[i] for i in f) for f in faces]

    def move(p):
        x, y, z = p
        for _ in range(turn):
            x, y = -y, x
        return (x + shift[0], y + shift[1], z + shift[2])
    tris = box(0, 0, 0, w, l, t) + box(ox, oy, oz, ox + sx, oy + sy, oz + sz)
    return [tuple(move(p) for p in tri) for tri in tris]


def test_a_board_is_found_in_its_catalog_frame_moved_or_not() -> None:
    spec = BOARDS[ESP]
    identity = {'family': 'board', 'part_number': ESP}
    at_home = studio.board_layout(identity, [p for tri in _board_mesh(spec) for p in tri])
    assert at_home['frame'] == {'quarter_turns_about_z': 0, 'shift_mm': [0.0, 0.0, 0.0]}
    assert at_home['chip'] == {'origin': spec['cosmetic_origin'], 'size': spec['cosmetic_size']}
    assert [pad['origin'] for pad in at_home['pads']] == [row['origin'] for row in spec['terminals']]
    # Turned a quarter and moved: the chip and every pad move with it.
    moved = studio.board_layout(identity, [p for tri in _board_mesh(spec, 1, (5.0, 6.0, 7.0)) for p in tri])
    assert moved['frame']['quarter_turns_about_z'] == 1
    assert moved['frame']['shift_mm'] == pytest.approx([5.0, 6.0, 7.0])
    x, y, z = spec['cosmetic_origin']
    sx, sy, sz = spec['cosmetic_size']
    assert moved['chip']['size'] == pytest.approx([sy, sx, sz])
    assert moved['chip']['origin'] == pytest.approx([-(y + sy) + 5.0, x + 6.0, z + 7.0])
    px, py, pz = spec['terminals'][0]['origin']
    assert moved['pads'][0]['origin'] == pytest.approx([-py + 5.0, px + 6.0, pz + 7.0])


def test_a_board_that_is_not_the_catalog_board_is_plain_solder_mask() -> None:
    spec = BOARDS[ESP]
    identity = {'family': 'board', 'part_number': ESP}
    mesh = _board_mesh(spec)
    # Cut narrower, flipped upside down, or not a board at all: no layout.
    narrow = [tuple((x * 0.9, y, z) for x, y, z in tri) for tri in mesh]
    flipped = [tuple((x, y, -z) for x, y, z in tri) for tri in mesh]
    for tris in (narrow, flipped):
        assert studio.board_layout(identity, [p for tri in tris for p in tri]) is None
    assert studio.board_layout({'family': 'bolt', 'part_number': 'm3x8'}, [p for tri in mesh for p in tri]) is None
    assert studio.board_layout({'family': 'board', 'part_number': 'nope'}, [p for tri in mesh for p in tri]) is None
    look = studio.materials(_summary('esp'), catalog={'esp': identity})['esp']
    assert len(studio.material(look, narrow)) == 2       # one colour: the mask
    assert len(studio.material(look, mesh)) == 3         # painted per point


def test_the_paint_names_chip_pad_and_mask_by_where_a_point_is() -> None:
    spec = BOARDS[ESP]
    layout = studio.board_layout({'family': 'board', 'part_number': ESP},
                                 [p for tri in _board_mesh(spec) for p in tri])
    paint = studio._board_paint(layout)
    (ox, oy, oz), (sx, sy, sz) = spec['cosmetic_origin'], spec['cosmetic_size']
    t = spec['thickness_mm']
    assert paint((ox + sx / 2, oy + sy / 2, oz + sz)) == studio.BOARD_LOOK['chip']
    px, py, _ = spec['terminals'][0]['origin']
    assert paint((px + 0.5, py, t)) == studio.BOARD_LOOK['pad']         # on the ring
    assert paint((px + 1.2, py, t)) == studio.BOARD_LOOK['mask']        # past it
    assert paint((14.0, 5.0, t)) == studio.BOARD_LOOK['mask']
    # Placed in the world, the paint reads a point back through the placement.
    placement = [0, -1, 0, 100, 1, 0, 0, 50, 0, 0, 1, 10, 0, 0, 0, 1]
    world = studio._board_paint(layout, studio._rigid_inverse(placement))
    x, y, z = ox + sx / 2, oy + sy / 2, oz + sz
    assert world((-y + 100, x + 50, z + 10)) == studio.BOARD_LOOK['chip']


def _colours(pixels):
    return [tuple(pixels[i:i + 3]) for i in range(0, len(pixels), 3)]


def test_a_drawn_board_shows_mask_chip_and_pads_and_a_mismatched_one_only_mask() -> None:
    spec = BOARDS[ESP]
    look = studio.materials(_summary('esp'), catalog={'esp': {'family': 'board', 'part_number': ESP}})['esp']

    def draw(tris):
        prepared = studio._prepare([(studio.material(look, tris), tris)])
        basis = studio.BASES['top']
        pixels, _ = studio.studio(prepared, basis, bounds=studio._frame(prepared, basis, 0.04), size=160)
        return _colours(pixels)

    def kinds(colours):
        greens = sum(1 for r, g, b in colours if g > r + 30 and g > b + 20)
        darks = sum(1 for r, g, b in colours if max(r, g, b) < 60 and abs(r - b) < 12 and max(r, g, b) > 0)
        brights = sum(1 for r, g, b in colours if min(r, g, b) > 150)
        return greens, darks, brights
    greens, darks, brights = kinds(draw(_board_mesh(spec)))
    assert greens > 3000 and brights > 40
    # The chip covers 18 x 31 of the board's 28 x 48 mm.
    assert darks > 3000
    narrow = [tuple((x * 0.9, y, z) for x, y, z in tri) for tri in _board_mesh(spec)]
    greens, _darks, brights = kinds(draw(narrow))
    assert greens > 9000 and brights == 0


def _sphere(r=10.0, n=24):
    tris = []
    for i in range(n):
        t0, t1 = math.pi * i / n, math.pi * (i + 1) / n
        for j in range(2 * n):
            p0, p1 = math.pi * j / n, math.pi * (j + 1) / n

            def at(t, p):
                return (r * math.sin(t) * math.cos(p), r * math.sin(t) * math.sin(p), r + r * math.cos(t))
            a, b, c, d = at(t0, p0), at(t1, p0), at(t1, p1), at(t0, p1)
            tris += [(a, b, c), (a, c, d)]
    return tris


def test_black_oxide_is_dark_metal_not_graphite_plastic() -> None:
    """The same dark sphere, printed graphite and black-oxide steel: the metal
    mirrors the studio (a hard highlight and a dark floor reflection), so its
    range of brightness is far wider than the matte print's."""
    tris = _sphere()

    def spread(material):
        prepared = studio._prepare([(material, tris)])
        pixels, _ = studio.studio(prepared, studio.HERO, bounds=studio._frame(prepared, studio.HERO, 0.02),
                                  size=96)
        lit = sorted(sum(c) / 3 for c in _colours(pixels))
        return lit[len(lit) // 50], lit[-len(lit) // 200]
    graphite = spread((studio.ROLE_COLORS['mechanism'], studio.FINISH['mechanism']))
    metal = spread(studio.METALS['black_oxide'])
    assert metal[1] - metal[0] > graphite[1] - graphite[0] + 40
    # Deterministic: the same scene draws the same bytes.
    prepared = studio._prepare([(studio.METALS['steel'], tris)])
    first = studio.studio(prepared, studio.HERO, bounds=studio._frame(prepared, studio.HERO, 0.02), size=48)[0]
    assert studio.studio(prepared, studio.HERO, bounds=studio._frame(prepared, studio.HERO, 0.02), size=48)[0] == first
