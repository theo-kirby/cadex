# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The agent's `look` tool (ADR-406): pictures of the accepted design."""
import base64
import json
import struct
import zlib

import pytest

from cadex_cli import render
from cadex_cli.bridge import Bridge
from cadex_cli.inventory import InventoryError

from fake_cadexd import FakeCadexd

IDENTITY = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]


def draw(triangles, basis, *, bounds=None, size=render.SIZE):
    """The studio renderer over bare ``(colour, points)`` triangles, framed on them."""
    prepared = render._prepare([((colour, render.FINISH['shell']), [points]) for colour, points in triangles])
    return render.studio(prepared, basis, bounds=bounds or render._frame(prepared, basis, 0.04), size=size)


def _mesh(tmp_path, name, vertices, triangles):
    data = b''.join(struct.pack('<3f', *v) for v in vertices)
    data += b''.join(struct.pack('<3I', *t) for t in triangles)
    binary, side = tmp_path / f'{name}.bin', tmp_path / f'{name}.json'
    binary.write_bytes(data)
    side.write_text(json.dumps({
        'schema': 'cadex-tessellation-v1', 'byte_order': 'little',
        'layout': {'vertices': {'offset': 0, 'bytes': 12 * len(vertices), 'dtype': 'f32'},
                   'triangles': {'offset': 12 * len(vertices), 'bytes': 12 * len(triangles), 'dtype': 'u32'}}}))
    return {'artifact_kind': 'tessellation', 'artifact_path': str(binary), 'sidecar_path': str(side),
            'counts': {'vertices': len(vertices), 'triangles': len(triangles), 'faces': 6,
                       'edges': 0, 'edge_vertices': 0},
            'deflection': 0.1, 'quality': 'standard'}


def _box(size, z0=0.0):
    x, y, z = size
    v = [(i * x, j * y, z0 + k * z) for i in (0, 1) for j in (0, 1) for k in (0, 1)]
    t = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1),
         (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    return v, t


def _reply(tmp_path):
    """A floor 1 m across, a 20 mm printed body on it and a 5 mm purchased pin."""
    revision = 'a' * 64
    floor = _mesh(tmp_path, 'floor', *_box((1000, 1000, 2), -2))
    body = _mesh(tmp_path, 'body', *_box((20, 20, 20)))
    pin = _mesh(tmp_path, 'pin', *_box((5, 5, 30)))
    display = {
        'floor': {'artifact_kind': 'brep', 'artifact_path': '/staging/floor.brep', 'placement': None,
                  'tessellation': floor},
        'body': {'artifact_kind': 'brep', 'artifact_path': '/staging/body.brep', 'placement': None,
                 'tessellation': body},
        'pin': {'artifact_kind': 'brep', 'artifact_path': '/staging/pin.brep', 'placement': None,
                'tessellation': pin},
        'c_floor': {'artifact_kind': None, 'artifact_path': None, 'placement': IDENTITY,
                    'tessellation': None, 'source_output': 'floor'},
        'c_body': {'artifact_kind': None, 'artifact_path': None, 'placement': IDENTITY,
                   'tessellation': None, 'source_output': 'body'},
        'c_pin': {'artifact_kind': None, 'artifact_path': None,
                  'placement': [1, 0, 0, 30, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
                  'tessellation': None, 'source_output': 'pin'},
    }
    return {'ok': True, 'revision': revision, 'accepted_revision': revision, 'digest': 'd' * 64,
            'display': display}


def _pixels(data):
    """Decode one of render.png's own images (8-bit RGB, filter 0 rows)."""
    size = struct.unpack('>I', data[16:20])[0]
    raw = zlib.decompress(data[data.index(b'IDAT') + 4:data.index(b'IEND') - 8])
    stride = 3 * size + 1
    return size, [raw[r * stride + 1:(r + 1) * stride] for r in range(size)]


def _colours(data):
    _, rows = _pixels(data)
    return {bytes(row[i:i + 3]) for row in rows for i in range(0, len(row), 3)}


def _is_shade_of(pixel, colour):
    ratios = [p / c for p, c in zip(pixel, colour)]
    return max(ratios) - min(ratios) < 0.03 and 0.5 <= ratios[0] <= 1.01


def test_look_leaves_the_floor_out_and_frames_the_design(tmp_path):
    triangles, summary = render.snapshot(_reply(tmp_path))
    with_floor = render.look(triangles, summary, ['top'])[0]
    without = render.look(triangles, summary, ['top'], exclude={'c_floor'})[0]
    # With the floor, a 1 m plate sets the framing and the design is a speck;
    # without it, the frame is the 35 mm design plus padding.
    span = lambda shot: shot[2]['projection_bounds_mm'][1][0] - shot[2]['projection_bounds_mm'][0][0]
    assert span(with_floor) > 900
    assert span(without) < 40
    assert without[1][:8] == b'\x89PNG\r\n\x1a\n'


def _kinds(data):
    """How many pixels read as bone shell, graphite mechanism and orange accent."""
    _, rows = _pixels(data)
    pixels = [tuple(row[i:i + 3]) for row in rows for i in range(0, len(row), 3)]
    return {
        'shell': sum(min(p) > 150 and p[0] >= p[2] and p[0] - p[2] < 30 for p in pixels),
        'mechanism': sum(max(p) < 90 and max(p) - min(p) < 20 for p in pixels),
        'accent': sum(p[0] > 170 and p[1] < 150 and p[2] < 100 for p in pixels),
    }


def test_look_colours_parts_by_role_with_printed_and_purchased_defaults(tmp_path):
    """Undeclared parts: printed is shell bone, purchased is graphite mechanism."""
    triangles, summary = render.snapshot(_reply(tmp_path))
    (_, data, details), = render.look(triangles, summary, ['iso'], exclude={'c_floor'}, purchased={'c_pin'})
    kinds = _kinds(data)
    assert kinds['shell'] > 500 and kinds['mechanism'] > 100 and kinds['accent'] == 0
    assert details['materials'] == ['#2F3237', '#E9E6DF']


def test_look_material_comes_from_the_declared_role_and_palette(tmp_path):
    """A3's hook: a declared role wins over printed/purchased, and a palette recolours a role."""
    triangles, summary = render.snapshot(_reply(tmp_path))
    (_, data, details), = render.look(triangles, summary, ['iso'], exclude={'c_floor'},
                                      purchased={'c_pin'}, appearance={'c_pin': 'accent'})
    assert _kinds(data)['accent'] > 100 and _kinds(data)['mechanism'] < 20
    assert details['materials'] == ['#E9E6DF', '#F26A1B']
    looks = render.materials(summary, purchased={'c_pin'}, palette={'shell': (201, 174, 134)})
    assert looks['c_body'] == ('shell', (201, 174, 134)) and looks['c_pin'][0] == 'mechanism'
    with pytest.raises(InventoryError, match='unknown appearance role chrome'):
        render.look(triangles, summary, ['iso'], appearance={'c_pin': 'chrome'})


def test_look_focus_frames_a_close_up(tmp_path):
    triangles, summary = render.snapshot(_reply(tmp_path))
    whole = render.look(triangles, summary, ['front'], exclude={'c_floor'})[0][2]
    close = render.look(triangles, summary, ['front'], exclude={'c_floor'}, focus={'c_pin'})[0][2]
    assert close['projection_bounds_mm'] != whole['projection_bounds_mm']
    width = close['projection_bounds_mm'][1][0] - close['projection_bounds_mm'][0][0]
    assert width < 10  # the 5 mm pin plus padding, not the 35 mm design


def test_look_refuses_unknown_names_and_views(tmp_path):
    triangles, summary = render.snapshot(_reply(tmp_path))
    with pytest.raises(InventoryError, match='unknown focus'):
        render.look(triangles, summary, ['iso'], focus={'c_nothing'})
    with pytest.raises(InventoryError, match='unknown view'):
        render.look(triangles, summary, ['perspective'])
    with pytest.raises(InventoryError, match='nothing to draw'):
        render.look(triangles, summary, ['iso'], exclude=set(summary['objects']))


def test_offcanvas_triangles_cost_no_pixel_budget():
    # Framed on a 10 mm window, a triangle wholly above-left of it has a
    # negative span on both axes; the pre-ADR-406 count multiplied the two
    # into a positive number and billed pixels that were never visited.
    far = ((1, 1, 1), ((-500, 500, 0), (-400, 500, 0), (-450, 600, 0)))
    near = ((1, 1, 1), ((0, 0, 0), (10, 0, 0), (0, 10, 0)))
    _, alone = draw([near], render.BASES['top'], bounds=([0, 0], [10, 10]), size=64)
    _, both = draw([near, far], render.BASES['top'], bounds=([0, 0], [10, 10]), size=64)
    assert both['pixel_visits'] == alone['pixel_visits']


def test_bridge_look_returns_images_from_the_accepted_build(tmp_path):
    with Bridge(FakeCadexd()) as bridge:
        bridge.state.last_accepted = _reply(tmp_path)
        bridge.state.last_fit = {'failing': [{'first': 'c_floor', 'second': '', 'status': 'world geometry'}]}
        bridge.state.last_inventory = {'available': True, 'uncatalogued_sources': ['floor', 'body']}
        result = bridge.call('look', {'views': ['iso', 'top'], 'focus': ['pin']})
        assert result['is_error'] is False
        text, *images = result['content']
        facts = json.loads(text['text'])
        assert facts['left_out_as_environment'] == ['c_floor']
        assert facts['views'] == ['iso', 'top']
        assert facts['colours'].startswith('by appearance role: shell #E9E6DF')
        assert '0 component(s) declare a role' in facts['colours']
        assert [image['type'] for image in images] == ['image', 'image']
        assert base64.b64decode(images[0]['data'])[:4] == b'\x89PNG'
        assert bridge.state.calls[-1].op == 'look' and bridge.state.calls[-1].ok


def test_bridge_look_refuses_bad_arguments(tmp_path):
    with Bridge(FakeCadexd()) as bridge:
        bridge.state.last_accepted = _reply(tmp_path)
        assert bridge.call('look', {'views': ['iso'] * 6})['is_error'] is True
        assert bridge.call('look', {'angle': 30})['is_error'] is True
        refused = bridge.call('look', {'focus': ['c_nothing']})
        assert refused['is_error'] is True and 'unknown focus' in refused['content'][0]['text']


def test_bridge_look_first_in_a_turn_rebuilds_and_reads_fit_and_inventory(tmp_path):
    """A turn that opens with `look` has no build reply yet. It rebuilds for
    the geometry and reads the same fit and inventory a modelling reply would
    carry, so the floor is still left out and parts are still coloured."""
    from fake_cadexd import accepted_reply

    def rebuild(_args):
        reply = accepted_reply('rebuild', 'a' * 64)
        reply['display'] = _reply(tmp_path)['display']
        return reply

    client = FakeCadexd(replies={'rebuild': rebuild})
    with Bridge(client) as bridge:
        result = bridge.call('look', {})
        assert result['is_error'] is False, result['content'][0]['text']
        assert [op for op, _ in client.calls][:1] == ['rebuild']
        scopes = {args.get('scope') for op, args in client.calls if op == 'inspect'}
        assert {'clearance', 'inventory'} <= scopes
        assert bridge.state.last_fit is not None and bridge.state.last_inventory is not None
        # ...and a second look draws from the held build, with no second rebuild.
        bridge.call('look', {'views': ['top']})
        assert [op for op, _ in client.calls].count('rebuild') == 1


def test_hero_is_a_low_three_quarter_studio_shot(tmp_path):
    """DESIGN-LANGUAGE.md section 7: 15-25 degrees above the floor, 30-45 off the front."""
    import math
    right, up, toward = render.HERO
    assert 15 <= math.degrees(math.asin(toward[2])) <= 25
    assert 30 <= math.degrees(math.atan2(toward[0], -toward[1])) <= 45
    assert abs(sum(a * b for a, b in zip(right, up))) < 1e-12 and up[2] > 0
    triangles, summary = render.snapshot(_reply(tmp_path))
    (view, data, details), = render.look(triangles, summary, ['hero'], exclude={'c_floor'}, purchased={'c_pin'})
    size, rows = _pixels(data)
    assert view == 'hero' and size == render.LOOK_SIZE
    assert details['samples_per_pixel'] == render.SUPERSAMPLE ** 2 == 4
    assert details['contact_shadow'] is True
    # A seamless backdrop: down the left edge, darker at the top, lighter at
    # the bottom, and no step between neighbouring rows (no horizon line).
    edge = [row[0] for row in rows]
    assert edge[0] < edge[-1]
    assert max(abs(a - b) for a, b in zip(edge, edge[1:])) <= 2


def test_contact_shadow_darkens_the_floor_under_the_design_only(tmp_path):
    triangles, summary = render.snapshot(_reply(tmp_path))
    looks = render.materials(summary, purchased={'c_pin'})
    names = ['c_body', 'c_pin']
    prepared = render._prepare(render._studio_parts(triangles, summary, names, looks))
    bounds = render._frame(prepared, render.HERO, 0.10)
    lit, details = render.studio(prepared, render.HERO, bounds=bounds, size=96, shadow=render._contact_shadow(prepared))
    bare, _ = render.studio(prepared, render.HERO, bounds=bounds, size=96)
    darker = [a - b for a, b in zip(bare, lit)]
    assert details['contact_shadow'] and max(darker) > 30 and min(darker) >= 0
    assert lit[:3 * 96] == bare[:3 * 96]  # the top row, far from the floor, is untouched
    # ...and a camera level with the floor cannot see a shadow on it.
    front = render.studio(prepared, render.BASES['front'], bounds=render._frame(prepared, render.BASES['front'], .1),
                          size=32, shadow=render._contact_shadow(prepared))[1]
    assert front['contact_shadow'] is False


def test_supersampling_antialiases_edges():
    """One subsample per pixel gives each row two colours; four give the edge its blend."""
    tri = render._prepare([(((233, 230, 223), render.FINISH['shell']), [((0, 0, 0), (10, 3, 0), (4, 10, 0))])])
    bounds = ([-1, -1], [11, 11])
    def most_colours_in_a_row(samples):
        pixels, _ = render.studio(tri, render.BASES['top'], bounds=bounds, size=48, samples=samples)
        return max(len({bytes(pixels[3 * (48 * y + x):3 * (48 * y + x) + 3]) for x in range(48)})
                   for y in range(48))
    assert most_colours_in_a_row(1) == 2
    assert most_colours_in_a_row(2) > 2


def test_normals_are_smoothed_over_curves_and_kept_across_creases():
    import math
    # A cube whose corners are shared unevenly between faces: every corner
    # keeps its own face's normal.
    vertices, faces = _box((10, 10, 10))
    cube = render._prepare([((None, None), [tuple(vertices[i] for i in f) for f in faces])])
    for _, points, normals in cube:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = points
        face = ((by-ay)*(cz-az) - (bz-az)*(cy-ay), (bz-az)*(cx-ax) - (bx-ax)*(cz-az),
                (bx-ax)*(cy-ay) - (by-ay)*(cx-ax))
        length = math.sqrt(sum(c * c for c in face))
        assert all(n == pytest.approx(tuple(c / length for c in face)) for n in normals)
    # A 24-sided cylinder wall: each corner normal lies nearer the radius
    # through it than the facet's own normal does (7.5 degrees off it).
    ring = [(math.cos(2 * math.pi * k / 24), math.sin(2 * math.pi * k / 24)) for k in range(24)]
    wall = []
    for k in range(24):
        (x0, y0), (x1, y1) = ring[k], ring[(k + 1) % 24]
        wall += [((x0, y0, 0), (x1, y1, 0), (x1, y1, 1)), ((x0, y0, 0), (x1, y1, 1), (x0, y0, 1))]
    for _, points, normals in render._prepare([((None, None), wall)]):
        for (x, y, _), n in zip(points, normals):
            assert n[2] == pytest.approx(0) and x * n[0] + y * n[1] > math.cos(math.radians(4))


def test_render_writes_a_1024_px_studio_hero(tmp_path):
    (tmp_path / 'mesh').mkdir()
    reply = _reply(tmp_path / 'mesh')

    class Client:
        def request(self, op, args=None):
            if op == 'rebuild':
                return reply
            raise RuntimeError('no published blocks here')  # fit/inventory unreadable

    path, summary = render.write_render(Client(), tmp_path / 'project')
    hero = (path.parent / 'hero.png').read_bytes()
    size, _ = _pixels(hero)
    assert size == render.HERO_SIZE == 1024 and len(hero) < 300 * 1024
    assert summary['hero']['path'] == 'review/render/hero.png'
    assert summary['hero']['size'] == 1024 and summary['hero']['samples_per_pixel'] == 4
    assert set(summary['views']) == {'front', 'top', 'right', 'iso'}
    # No inventory: every object in its index colour, the floor still drawn.
    assert summary['environment'] == [] and set(summary['appearance']) == set(summary['objects'])
    assert json.loads((path.parent / 'summary.json').read_text())['hero']['size'] == 1024


def _teal(pixel):
    """A lit shade of the teal accent #179C98: green and blue well above red."""
    return pixel[1] - pixel[0] > 50 and pixel[2] - pixel[0] > 50


def _declared_inventory():
    """An inventory block as the engine carries a script's declared look (ADR-413)."""
    return {'available': True, 'uncatalogued_sources': ['floor', 'body'],
            'appearance': {'c_pin': 'accent', 'c_body': 'shell'},
            'palette': {'shell': '#C9AE86', 'accent': '#179C98'}}


def test_declared_reads_roles_and_palette_from_the_inventory_block():
    appearance, palette = render.declared(_declared_inventory())
    assert appearance == {'c_pin': 'accent', 'c_body': 'shell'}
    assert palette == {'shell': (201, 174, 134), 'accent': (23, 156, 152)}
    # Nothing declared, or nothing readable: supplier decides, as before.
    assert render.declared(None) == ({}, {})
    assert render.declared({'available': False, 'appearance': {'c_pin': 'accent'}}) == ({}, {})
    with pytest.raises(InventoryError, match='invalid palette colour'):
        render.declared({'palette': {'shell': 'bone'}})


def test_render_draws_the_declared_role_in_the_declared_palette(tmp_path, monkeypatch):
    """The purchased pin is declared accent: it is drawn teal, not graphite,
    and the summary says the role was declared rather than inferred."""
    (tmp_path / 'mesh').mkdir()
    reply = _reply(tmp_path / 'mesh')

    class Client:
        def request(self, op, args=None):
            return reply

    fit = {'failing': [{'first': 'c_floor', 'second': '', 'status': 'world geometry'}]}
    monkeypatch.setattr(render, '_published_blocks', lambda client: [fit, _declared_inventory()])
    path, summary = render.write_render(Client(), tmp_path / 'project')
    assert summary['appearance'] == {
        'c_body': {'role': 'shell', 'color': '#C9AE86', 'source': 'declared'},
        'c_pin': {'role': 'accent', 'color': '#179C98', 'source': 'declared'},
    }
    assert summary['palette'] == {'shell': '#C9AE86', 'mechanism': '#2F3237', 'accent': '#179C98'}
    _, rows = _pixels((path.parent / 'hero.png').read_bytes())
    pixels = [tuple(row[i:i + 3]) for row in rows for i in range(0, len(row), 3)]
    assert sum(_teal(p) for p in pixels) > 1000
    assert sum(max(p) < 90 and max(p) - min(p) < 20 for p in pixels) < 50  # no graphite pin


def test_bridge_look_draws_and_reports_the_declared_roles(tmp_path):
    with Bridge(FakeCadexd()) as bridge:
        bridge.state.last_accepted = _reply(tmp_path)
        bridge.state.last_fit = {'failing': [{'first': 'c_floor', 'second': '', 'status': 'world geometry'}]}
        bridge.state.last_inventory = _declared_inventory()
        result = bridge.call('look', {'views': ['iso']})
        text, image = result['content']
        facts = json.loads(text['text'])
        assert 'shell #C9AE86' in facts['colours'] and 'accent #179C98' in facts['colours']
        assert '2 component(s) declare a role' in facts['colours']
        pixels = _colours(base64.b64decode(image['data']))
        assert any(_teal(p) for p in pixels)


def _design(tmp_path, boxes):
    """A snapshot of named boxes: ``name -> (size, offset)``, each its own output."""
    display = {}
    for name, (size, offset) in boxes.items():
        display['o_' + name] = {'artifact_kind': 'brep', 'artifact_path': f'/staging/{name}.brep',
                                'placement': None, 'tessellation': _mesh(tmp_path, name, *_box(size))}
        display[name] = {'artifact_kind': None, 'artifact_path': None, 'tessellation': None,
                         'source_output': 'o_' + name,
                         'placement': [1, 0, 0, offset[0], 0, 1, 0, offset[1], 0, 0, 1, offset[2], 0, 0, 0, 1]}
    revision = 'a' * 64
    return render.snapshot({'ok': True, 'revision': revision, 'accepted_revision': revision,
                            'digest': 'd' * 64, 'display': display})


def test_hardware_silhouette_share_fails_exposed_hardware_and_passes_a_shell(tmp_path):
    """P1: a servo on a plate is mostly hardware in the hero; the same servo
    inside a printed shell is none of it."""
    crude = _design(tmp_path, {'plate': ((60, 30, 3), (0, 0, 0)), 'servo': ((40, 20, 40), (10, 5, 3))})
    p1 = render.design_proxies(*crude, purchased={'servo'})['hardware_silhouette_share']
    assert p1['value'] > 0.5 and p1['meets'] is False and p1['bar'] == {'max': 0.2}
    designed = _design(tmp_path, {'shell': ((60, 30, 50), (0, 0, 0)), 'servo': ((40, 20, 40), (10, 5, 3))})
    p1 = render.design_proxies(*designed, purchased={'servo'})['hardware_silhouette_share']
    assert p1['value'] == 0.0 and p1['meets'] is True
    assert p1['design_subsamples'] > 0.2 * (2 * render.PROXY_SIZE) ** 2
    # With no inventory nothing says what was purchased: unmeasured, not zero.
    p1 = render.design_proxies(*designed)['hardware_silhouette_share']
    assert p1['value'] is None and p1['meets'] is None and 'no inventory' in p1['reason']


def test_hardware_share_counts_only_what_is_in_front(tmp_path):
    """A servo half hidden behind a printed wall counts only its visible half."""
    snap = _design(tmp_path, {'wall': ((40, 2, 20), (0, -10, 0)), 'servo': ((40, 20, 40), (0, 0, 0))})
    hidden = render.design_proxies(*snap, purchased={'servo'})['hardware_silhouette_share']
    alone = render.design_proxies(*_design(tmp_path, {'servo': ((40, 20, 40), (0, 0, 0))}),
                                  purchased={'servo'})['hardware_silhouette_share']
    assert alone['value'] == 1.0 and 0.2 < hidden['value'] < 0.9


def test_material_count_fails_one_colour_and_a_rainbow_and_passes_roles(tmp_path):
    """P3: one colour and four colours are both outside 2-3; shell,
    mechanism and accent declared by role are three."""
    boxes = {name: ((10, 10, 10), (20 * i, 0, 0)) for i, name in enumerate(['a', 'b', 'c', 'd'])}
    snap = _design(tmp_path, boxes)
    one = render.design_proxies(*snap, purchased=set())['material_count']
    assert one['value'] == 1 and one['meets'] is False and one['materials'] == ['#E9E6DF']
    rainbow = render.design_proxies(*snap)['material_count']  # index colours
    assert rainbow['value'] == 4 and rainbow['meets'] is False
    roles = render.design_proxies(*snap, purchased={'b'}, appearance={'c': 'accent', 'd': 'shell'})
    assert roles['material_count']['value'] == 3 and roles['material_count']['meets'] is True
    # Only what the hero shows counts: a part left out as environment is not a material.
    left_out = render.design_proxies(*snap, exclude={'c'}, purchased={'b'}, appearance={'c': 'accent'})
    assert left_out['material_count']['value'] == 2


def test_proxies_do_not_depend_on_the_size_look_draws_at(tmp_path):
    snap = _design(tmp_path, {'plate': ((60, 30, 3), (0, 0, 0)), 'servo': ((40, 20, 40), (10, 5, 3))})
    first = render.design_proxies(*snap, purchased={'servo'})
    render.look(*snap, ['hero'], purchased={'servo'}, size=64)
    assert render.design_proxies(*snap, purchased={'servo'}) == first
    assert first['view'] == 'hero' and first['size'] == render.PROXY_SIZE


def test_render_and_bridge_look_report_the_proxies(tmp_path, monkeypatch):
    (tmp_path / 'mesh').mkdir()
    reply = _reply(tmp_path / 'mesh')

    class Client:
        def request(self, op, args=None):
            return reply

    fit = {'failing': [{'first': 'c_floor', 'second': '', 'status': 'world geometry'}]}
    monkeypatch.setattr(render, '_published_blocks', lambda client: [fit, _declared_inventory()])
    path, summary = render.write_render(Client(), tmp_path / 'project')
    proxies = summary['proxies']
    assert json.loads(path.read_text())['proxies'] == proxies
    assert proxies['material_count']['materials'] == ['#179C98', '#C9AE86']
    assert 0 < proxies['hardware_silhouette_share']['value'] < 1
    line = render.describe_proxies(proxies)
    assert 'hardware share of hero silhouette' in line and '2 material(s)' in line
    with Bridge(FakeCadexd()) as bridge:
        bridge.state.last_accepted = reply
        bridge.state.last_fit = fit
        bridge.state.last_inventory = _declared_inventory()
        facts = json.loads(bridge.call('look', {'views': ['top']})['content'][0]['text'])
    assert facts['measures'] == {key: {k: proxies[key][k] for k in ('value', 'bar', 'meets')}
                                 for key in ('hardware_silhouette_share', 'sharp_outside_edge_share',
                                             'material_count')}
    # This inventory carries no edge facts, so P2 says why rather than passing.
    assert proxies['sharp_outside_edge_share']['value'] is None


def _edge_inventory(printed):
    """An inventory as the engine reads it: ``printed`` maps a component to
    its output's (edge length, sharp convex length), or ``None`` for none
    measured; a purchased servo's sharp edges are always there to ignore."""
    from cadex_cli.inventory import inventory_summary
    rows = [{'component': 'c_servo', 'source_output': 'servo',
             'catalog': {'family': 'servos', 'part_number': 'MG90S'},
             'source_facts': {'sharp_edges': {'edge_length_mm': 500.0, 'sharp_convex_length_mm': 500.0}}}]
    for name, edges in printed.items():
        facts = {} if edges is None else {
            'sharp_edges': {'edge_length_mm': edges[0], 'sharp_convex_length_mm': edges[1]}}
        rows.append({'component': name, 'source_output': 'o_' + name, 'source_facts': facts})
    return inventory_summary({'revision': 'r' * 64, 'assembly': 'asm', 'components': rows,
                              'catalog_counts': {'servos/MG90S': 1},
                              'uncatalogued_sources': ['o_' + name for name in printed]})


def test_sharp_outside_edge_share_fails_bare_boxes_and_passes_a_blended_shell():
    """P2 (ADR-415): bare printed boxes are all sharp edge; the same parts
    filleted are none of it. Purchased edges never count, and a printed
    part placed twice counts twice."""
    crude = render.edge_proxy(_edge_inventory({'deck': (280.0, 280.0), 'leg': (140.0, 140.0)}))
    assert crude['value'] == 1.0 and crude['meets'] is False and crude['bar'] == {'max': 0.25}
    designed = render.edge_proxy(_edge_inventory({'deck': (529.1, 0.0), 'leg': (300.0, 40.0)}))
    assert designed['value'] == pytest.approx(40.0 / 829.1, abs=1e-4) and designed['meets'] is True
    assert designed['printed_components'] == 2 and designed['edge_length_mm'] == 829.1
    twice = _edge_inventory({'leg_a': (100.0, 50.0), 'leg_b': (100.0, 50.0), 'deck': (200.0, 0.0)})
    assert render.edge_proxy(twice)['value'] == 0.25
    # Nothing printed: zero, as frozen.
    assert render.edge_proxy(_edge_inventory({}))['value'] == 0.0


def test_sharp_outside_edge_share_is_unmeasured_rather_than_zero():
    unmeasured = render.edge_proxy(_edge_inventory({'deck': (280.0, 0.0), 'skin': None}))
    assert unmeasured['value'] is None and unmeasured['meets'] is None
    assert unmeasured['unmeasured'] == ['skin'] and 'skin' in unmeasured['reason']
    for missing in (None, {'available': False}):
        none = render.edge_proxy(missing)
        assert none['value'] is None and 'no inventory' in none['reason']
    line = render.describe_proxies({
        'hardware_silhouette_share': {'value': 0.1, 'meets': True, 'bar': {'max': 0.2}},
        'sharp_outside_edge_share': render.edge_proxy(_edge_inventory({'deck': (100.0, 60.0)})),
        'material_count': {'value': 2, 'materials': ['#000000', '#FFFFFF'], 'meets': True,
                           'bar': {'min': 2, 'max': 3}}})
    assert 'sharp printed outside edges 60.0% (over 25%)' in line
