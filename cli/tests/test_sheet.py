# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The concept sheet (ot10 A6, ADR-430): its shape, its identity, its numbers,
and how `cadex review` leads with it."""
import json
import struct
import zlib

import pytest

from cadex_cli import render as cli_render
from cadex_cli.studio import STUDIO as render
sheet = render
from cadex_cli.review_server import presentation, serve

from test_look import _box, _mesh, _reply, IDENTITY
from test_review_server import _get, _json


def _decode(data):
    """``(width, height, rows)`` of one of render.png's own images."""
    width, height = struct.unpack('>2I', data[16:24])
    raw = zlib.decompress(data[data.index(b'IDAT') + 4:data.index(b'IEND') - 8])
    stride = 3 * width + 1
    return width, height, [raw[r * stride + 1:(r + 1) * stride] for r in range(height)]


def _pixel(rows, x, y):
    return tuple(rows[y][3 * x:3 * x + 3])


def _accepted(root, revision, *, inertials=True, attempt_revision=None, digest='d' * 64):
    """A project manifest pinning an attempt whose MJCF output carries inertials."""
    staging = root / 'script_artifacts' / revision / 'attempt-1'
    staging.mkdir(parents=True)
    outputs = [{'name': 'body', 'type': 'solid'}]
    if inertials:
        outputs.append({'name': 'model', 'type': 'mjcf', 'assembly_data': {'dynamics': {'inertials': [
            {'component_output': 'c_floor', 'mass_kg': 1.9},
            {'component_output': 'c_body', 'mass_kg': 0.25},
            {'component_output': 'c_pin', 'mass_kg': 0.055}]}}})
    (staging / 'result.json').write_text(json.dumps({'ok': True, 'digest': digest, 'outputs': outputs}))
    (root / 'script.json').write_text(json.dumps({
        'schema': 'cadex-project-script-v1', 'accepted_revision': revision, 'accepted_digest': 'd' * 64,
        'accepted_attempt': {'revision': attempt_revision or revision,
                             'staging': f'script_artifacts/{revision}/attempt-1'}}))


def _inventory():
    return {'available': True, 'uncatalogued_sources': ['floor', 'body'],
            'catalog_counts': {'servo/MG90S': 1, 'servo_horn/MG90S-HORN': 4},
            'appearance': {'c_pin': 'accent', 'c_body': 'shell'},
            'palette': {'shell': '#C9AE86', 'accent': '#179C98'}}


def _render(tmp_path, monkeypatch, *, inventory=None, **accepted):
    (tmp_path / 'mesh').mkdir()
    reply = _reply(tmp_path / 'mesh')
    root = tmp_path / 'ot10-fixture'
    root.mkdir()
    _accepted(root, reply['revision'], **accepted)

    class Client:
        def request(self, op, args=None):
            return reply
    fit = {'failing': [{'first': 'c_floor', 'second': '', 'status': 'world geometry'}]}
    monkeypatch.setattr(cli_render, '_published_blocks', lambda client: [fit, inventory])
    path, summary = cli_render.write_render(Client(), root)
    return root, path.parent, summary


def test_render_writes_the_concept_sheet_with_the_hero_numbers_palette_and_line_views(tmp_path, monkeypatch, small_renders):
    root, directory, summary = _render(tmp_path, monkeypatch, inventory=_inventory())
    data = (directory / 'sheet.png').read_bytes()
    width, height, rows = _decode(data)
    # Shape: one PNG, 1536 x 1024, under the charter's 300 KB.
    assert (width, height) == (sheet.WIDTH, sheet.HEIGHT) == (1536, 1024)
    assert len(data) <= 300 * 1024
    assert summary['sheet']['path'] == 'review/render/sheet.png'
    assert summary['sheet']['size'] == [1536, 1024]
    # Identity: the sheet names the revision and digest it was drawn from, and
    # its left 1024 px are the hero written beside it, pixel for pixel.
    assert summary['sheet']['revision'] == summary['revision'] and summary['sheet']['digest'] == 'd' * 64
    _, _, hero = _decode((directory / 'hero.png').read_bytes())
    assert all(rows[y][:3 * 1024] == hero[y] for y in range(0, 1024, 97))
    # The numbers: mass from the dynamics model without the floor, the
    # servo family only (not its horns), and the size without the floor.
    numbers = summary['sheet']['numbers']
    assert numbers['name'] == 'ot10-fixture'
    assert numbers['mass_kg'] == pytest.approx(0.305)
    assert numbers['servo_count'] == 1
    assert numbers['size_mm'] == [35.0, 20.0, 30.0]
    assert 'mass_reason' not in numbers and 'servo_reason' not in numbers
    # The palette: a swatch per role the design uses (here shell and accent;
    # the floor's mechanism is environment), each in the declared colour.
    swatch = (sheet.WIDTH - 1024 - 80 - 24) // 2
    y = 170 + 3 * 64 + 20 + 50
    assert _pixel(rows, 1024 + 40 + 10, y) == (0xC9, 0xAE, 0x86)
    assert _pixel(rows, 1024 + 40 + swatch + 24 + 10, y) == (0x17, 0x9C, 0x98)
    # The line views are ink on paper, and the panel is paper elsewhere.
    ink = sum(1 for yy in range(540, 1000) for xx in range(1064, 1496)
              if min(_pixel(rows, xx, yy)) > 120)
    assert ink > 200
    assert _pixel(rows, sheet.WIDTH - 5, sheet.HEIGHT - 5) == sheet.PAPER


def test_sheet_says_why_a_number_is_missing_rather_than_inventing_it(tmp_path, monkeypatch, small_renders):
    _, _, summary = _render(tmp_path, monkeypatch, inventory=None, inertials=False)
    numbers = summary['sheet']['numbers']
    assert numbers['mass_kg'] is None and 'no dynamics model' in numbers['mass_reason']
    assert numbers['servo_count'] is None and numbers['servo_reason'] == 'no readable inventory'


@pytest.mark.parametrize('pin, reason', [
    ({'attempt_revision': 'b' * 64}, 'not the revision drawn'),
    ({'digest': 'e' * 64}, 'does not carry the accepted digest'),
])
def test_mass_is_refused_from_an_attempt_that_is_not_the_one_drawn(tmp_path, monkeypatch, small_renders, pin, reason):
    _, _, summary = _render(tmp_path, monkeypatch, inventory=_inventory(), **pin)
    assert summary['sheet']['numbers']['mass_kg'] is None
    assert reason in summary['sheet']['numbers']['mass_reason']


def test_line_view_draws_silhouettes_and_creases_but_not_coplanar_splits(tmp_path):
    reply = {'ok': True, 'revision': 'a' * 64, 'accepted_revision': 'a' * 64, 'display': {
        'box': {'artifact_kind': 'brep', 'artifact_path': '/b.brep', 'placement': None,
                'tessellation': _mesh(tmp_path, 'box', *_box((20, 20, 20)))},
        'c_box': {'artifact_kind': None, 'artifact_path': None, 'placement': IDENTITY,
                  'tessellation': None, 'source_output': 'box'}}}
    triangles, summary = render.snapshot(reply)
    front, details = sheet.line_view(triangles, summary, ['c_box'], render.BASES['front'], size=100)
    iso, _ = sheet.line_view(triangles, summary, ['c_box'], render.BASES['iso'], size=100)
    # Front on, a cube is one face split into two triangles: its outline and
    # nothing across its diagonal.
    # Light ink on the dark scene paper (ADR-444).
    grey = [max(front[3 * i:3 * i + 3]) for i in range(100 * 100)]
    assert details['ink_pixels'] > 0
    assert grey[50 * 100 + 50] == max(sheet.PAPER)
    diagonal = [grey[k * 100 + k] for k in range(20, 80)]
    assert max(diagonal) == max(sheet.PAPER)
    # In three-quarter view the three visible faces meet at creases: ink
    # inside the silhouette, not only around it.
    inside = [max(iso[3 * (y * 100 + 50):3 * (y * 100 + 50) + 3]) for y in range(30, 70)]
    assert max(inside) > 120


def test_the_face_draws_every_glyph_and_marks_what_it_lacks():
    canvas = sheet.Canvas(200, 12, sheet.PAPER)
    end = canvas.text(0, 0, 'Ab9.%', 1, sheet.INK)
    assert end == 30 and sheet.text_width('Ab9.%', 1) == 29
    assert all(len(rows) == 7 and all(len(r) == 5 for r in rows) for rows in sheet.FONT.values())
    unknown = sheet.Canvas(10, 10, sheet.PAPER)
    unknown.text(0, 0, '§', 1, sheet.INK)
    question = sheet.Canvas(10, 10, sheet.PAPER)
    question.text(0, 0, '?', 1, sheet.INK)
    assert unknown.pixels == question.pixels
    assert sheet.fitted_scale('OT10-HEXAPOD-10', 432, 5) == 4


def _presented(root, revision, *, with_sheet=True):
    directory = root / 'review' / 'render'
    directory.mkdir(parents=True)
    summary = {'revision': revision, 'digest': 'd' * 64, 'palette': {'shell': '#E9E4D8'},
               'hero': {'path': 'review/render/hero.png'}}
    (directory / 'hero.png').write_bytes(render.png(bytearray(3 * 4), 2))
    if with_sheet:
        summary['sheet'] = {'path': 'review/render/sheet.png', 'numbers': {'name': root.name, 'mass_kg': 0.3}}
        (directory / 'sheet.png').write_bytes(render.png(bytearray(3 * 6), 3, 2))
    (directory / 'summary.json').write_text(json.dumps(summary))


def test_presentation_names_its_revision_and_relation(tmp_path):
    root = tmp_path / 'p'
    root.mkdir()
    accepted = {'available': True, 'revision': 'a' * 64}
    assert presentation(root, accepted) == {
        'available': False, 'reason': 'no render yet: cadex render draws the hero and the sheet'}
    _presented(root, 'a' * 64)
    shown = presentation(root, accepted)
    assert shown['available'] and shown['relation'] == 'current'
    assert set(shown['files']) == {'hero', 'sheet'} and shown['files']['sheet']['url'] == 'presentation/sheet.png'
    assert shown['numbers'] == {'name': 'p', 'mass_kg': 0.3} and shown['source'] == 'review/render'
    assert presentation(root, {'available': True, 'revision': 'b' * 64})['relation'] == 'historical'
    assert presentation(root, {'available': False})['relation'] == 'unknown'


def test_a_walk_render_of_the_accepted_revision_is_presented_first(tmp_path):
    root = tmp_path / 'p'
    (root / 'review' / 'render').mkdir(parents=True)
    _presented(root / 'review' / 'render', 'b' * 64)  # a walk's per-revision render
    (root / 'review' / 'render' / 'review' / 'render').rename(root / 'review' / 'render' / ('a' * 64))
    summary = root / 'review' / 'render' / ('a' * 64) / 'summary.json'
    value = json.loads(summary.read_text())
    value['revision'] = 'a' * 64
    value['hero']['path'] = f'review/render/{"a" * 64}/hero.png'
    value['sheet']['path'] = f'review/render/{"a" * 64}/sheet.png'
    summary.write_text(json.dumps(value))
    shown = presentation(root, {'available': True, 'revision': 'a' * 64})
    assert shown['available'] and shown['relation'] == 'current'
    assert shown['source'] == f'review/render/{"a" * 64}'


def test_a_render_from_before_the_sheet_says_so(tmp_path):
    root = tmp_path / 'p'
    root.mkdir()
    _presented(root, 'a' * 64, with_sheet=False)
    shown = presentation(root, {'available': True, 'revision': 'a' * 64})
    assert not shown['available'] and 'predates the concept sheet' in shown['reason']
    assert set(shown['files']) == {'hero'}


def test_review_serves_the_sheet_and_hero_and_nothing_else_from_the_render(tmp_path):
    root = tmp_path / 'p'
    root.mkdir()
    _accepted(root, 'a' * 64)
    _presented(root, 'a' * 64)
    server, _thread = serve(root, '127.0.0.1', 0)
    try:
        review = _json(server.url + 'api/project')
        assert review['presentation']['available'] and review['presentation']['relation'] == 'current'
        status, headers, body = _get(server.url + 'presentation/sheet.png')
        assert status == 200 and headers['content-type'] == 'image/png'
        assert body == (root / 'review/render/sheet.png').read_bytes()
        assert _get(server.url + 'presentation/hero.png')[0] == 200
        for name in ('summary.json', 'front.svg', '..%2Fscript.json', 'sheet.jpg'):
            assert _get(server.url + 'presentation/' + name)[0] == 404, name
    finally:
        server.shutdown()
        server.server_close()
