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


def test_look_colours_printed_and_purchased_parts(tmp_path):
    triangles, summary = render.snapshot(_reply(tmp_path))
    (_, data, _), = render.look(triangles, summary, ['iso'], exclude={'c_floor'}, purchased={'c_pin'})
    colours = _colours(data) - {bytes((246, 247, 250))}
    assert any(_is_shade_of(c, render.PRINTED_COLOR) for c in colours)
    assert any(_is_shade_of(c, render.PURCHASED_COLOR) for c in colours)


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
    _, alone = render.rasterize([near], render.BASES['top'], bounds=([0, 0], [10, 10]), size=64)
    _, both = render.rasterize([near, far], render.BASES['top'], bounds=([0, 0], [10, 10]), size=64)
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
        assert facts['colours'].startswith('orange = printed')
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
