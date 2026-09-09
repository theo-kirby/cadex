# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
import base64
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zlib

import pytest

from cadex_cli import render
from cadex_cli.__main__ import main
from cadex_cli.inventory import InventoryError


def buffer_reply(tmp_path):
    vertices = [(0, 0, 0), (10, 0, 0), (0, 20, 0)]
    data = b''.join(struct.pack('<3f', *v) for v in vertices) + struct.pack('<3I', 0, 1, 2)
    binary, side = tmp_path / 'mesh.bin', tmp_path / 'mesh.json'
    binary.write_bytes(data)
    side.write_text(json.dumps({'schema': 'cadex-tessellation-v1', 'byte_order': 'little',
                               'layout': {'vertices': {'offset': 0, 'bytes': 36, 'dtype': 'f32'},
                                          'triangles': {'offset': 36, 'bytes': 12, 'dtype': 'u32'}}}))
    return {'ok': True, 'revision': 'a'*64, 'accepted_revision': 'a'*64,
            'display': {'source': {'tessellation': {'artifact_path': str(binary), 'sidecar_path': str(side)}}}}


def test_snapshot_poses_once_and_excludes_definition(tmp_path):
    reply = buffer_reply(tmp_path)
    matrix = [0, -1, 0, 12, 1, 0, 0, 30, 0, 0, 1, 6, 0, 0, 0, 1]
    reply['display']['posed'] = {'source_output': 'source', 'placement': matrix}
    triangles, summary = render.snapshot(reply)
    assert set(summary['objects']) == {'posed'}
    assert summary['objects']['posed']['bounds_mm'] == [[-8, 30, 6], [12, 40, 6]]
    # No files are needed after the snapshot, including after attempt invalidation.
    for path in tmp_path.iterdir():
        path.unlink()
    assert triangles[0][1] == ((12, 30, 6), (12, 40, 6), (-8, 30, 6))
    assert render.rasterize(triangles, render.BASES['top'])[1]['covered_pixels'] > 0


@pytest.mark.parametrize('failure', ['revision', 'empty', 'layout', 'index', 'nan', 'missing', 'pose', 'bytes', 'triangles', 'sidecar', 'absent_tessellation', 'placed_vertices'])
def test_refuses_bad_or_excessive_snapshot(tmp_path, monkeypatch, failure):
    reply = buffer_reply(tmp_path)
    if failure == 'sidecar':
        (tmp_path / 'mesh.json').write_text('[]')
    elif failure == 'absent_tessellation':
        reply['display']['source'] = {'artifact_kind': 'brep'}
    elif failure == 'revision':
        reply['accepted_revision'] = 'b'*64
    elif failure == 'empty':
        reply['display'] = {}
    elif failure == 'layout':
        side = json.loads((tmp_path / 'mesh.json').read_text())
        side['layout']['vertices']['offset'] = -4
        (tmp_path / 'mesh.json').write_text(json.dumps(side))
    elif failure in {'index', 'nan'}:
        data = bytearray((tmp_path / 'mesh.bin').read_bytes())
        struct.pack_into('<I' if failure == 'index' else '<f', data,
                         36 if failure == 'index' else 0, 999 if failure == 'index' else float('nan'))
        (tmp_path / 'mesh.bin').write_bytes(data)
    elif failure == 'missing':
        (tmp_path / 'mesh.bin').unlink()
    elif failure == 'pose':
        reply['display']['placed'] = {'source_output': 'source'}
    elif failure == 'placed_vertices':
        monkeypatch.setattr(render, 'MAX_PLACED_VERTICES', 5)
        for name in ('one', 'two'):
            reply['display'][name] = {'source_output': 'source', 'placement': render.IDENTITY}
    elif failure == 'bytes':
        monkeypatch.setattr(render, 'MAX_BYTES', 10)
    elif failure == 'triangles':
        monkeypatch.setattr(render, 'MAX_TRIANGLES', 0)
    with pytest.raises(InventoryError, match='render:'):
        render.snapshot(reply)


def test_depth_crossing_is_independent_of_triangle_order():
    # Same projected triangle, opposite slopes. A centroid painter has to
    # choose one entire face and is necessarily wrong on one side.
    red, blue = (250, 10, 10), (10, 10, 250)
    a = (red, ((0, 0, 0), (10, 0, 10), (0, 10, 0)))
    b = (blue, ((0, 0, 10), (10, 0, 0), (0, 10, 10)))
    image, _ = render.rasterize([a, b], render.BASES['top'])
    reverse, _ = render.rasterize([b, a], render.BASES['top'])
    # Interior samples away from the equal-depth tie and triangle edges.
    def pixel(img, x, y):
        offset = (y * render.SIZE + x) * 3
        return img[offset:offset+3]
    for x in (100, 360):
        assert pixel(image, x, 430) == pixel(reverse, x, 430)
    assert pixel(image, 100, 430)[2] > pixel(image, 100, 430)[0]
    assert pixel(image, 360, 430)[0] > pixel(image, 360, 430)[2]


def test_occluded_triangle_never_overpaints_near_surface():
    a = ((220, 10, 10), ((0, 0, 2), (10, 0, 2), (0, 10, 2)))
    b = ((10, 10, 220), ((0, 0, -2), (10, 0, -2), (0, 10, -2)))
    assert render.rasterize([a, b], render.BASES['top'])[0] == render.rasterize([b, a], render.BASES['top'])[0]


def test_render_work_refusal_writes_no_new_files(tmp_path, monkeypatch):
    reply = buffer_reply(tmp_path)
    monkeypatch.setattr(render, 'MAX_SAMPLES', 1)
    class Client:
        def request(self, *args):
            return reply
    with pytest.raises(InventoryError, match='budget'):
        render.write_render(Client(), tmp_path)
    assert not (tmp_path / 'review').exists()


def image_bytes(path, revision):
    svg = ET.parse(path).getroot()
    assert revision in svg.find('{*}title').text
    image = svg.find('{*}image')
    raw = base64.b64decode(image.attrib['href'].split(',')[1])
    assert raw.startswith(b'\x89PNG')
    offset, compressed = 8, b''
    while offset < len(raw):
        size = struct.unpack_from('>I', raw, offset)[0]
        kind = raw[offset+4:offset+8]
        if kind == b'IDAT':
            compressed += raw[offset+8:offset+8+size]
        offset += size + 12
    pixels = zlib.decompress(compressed)
    assert len(set(pixels)) > 8
    return pixels


@pytest.mark.parametrize('recipe', ['hinged-arm', 'curved'])
def test_real_render_revision_images_pose_and_project_commit(engine, tmp_path, capsys, recipe):
    def run(*args):
        code = main([*args, '--json'])
        report = json.loads(capsys.readouterr().out)
        assert code == 0, report
        return report
    root = tmp_path / 'project'
    if recipe == 'hinged-arm':
        source = Path(__file__).resolve().parents[2] / 'examples/lifecycle/hinged-arm/script.py'
    else:
        source = tmp_path / 'curved.py'
        source.write_text('''block = part.box(10, 20, 3)
rod = part.cylinder(4, 30)
a = assembly.component(block, grounded=True, placement={"position": [12, 30, 6], "axis": [0, 0, 1], "angle_degrees": 90})
b = assembly.component(rod, grounded=True, placement=[25, 30, 0])
asm = assembly.assembly([a, b])
diag = assembly.solve(asm)
result = {"block": block, "rod": rod, "a": a, "b": b, "asm": asm, "diag": diag}
''')
    initial = run('script', '--set', str(source), '--project', str(root))
    envelope = run('render', '--project', str(root))
    summary = json.loads((root / 'review/render/summary.json').read_text())
    assert summary['revision'] == initial['accepted_revision'] == envelope['accepted_revision']
    assert summary['digest'] == initial['digest']
    images = [image_bytes(root / entry['path'], summary['revision']) for entry in summary['views'].values()]
    assert len(set(images)) == 4
    assert all(e['covered_pixels'] > 100 for e in summary['views'].values())
    if recipe == 'hinged-arm':
        assert summary['objects']['swing']['bounds_mm'] == [[12, 0, 6], [92, 8, 14]]
        assert set(summary['objects']) == {'base', 'swing'}
        assert summary['triangles'] == 24
    else:
        assert summary['triangles'] > 24
        bounds = summary['objects']['a']['bounds_mm']
        assert bounds[0] == pytest.approx([-8, 30, 6])
        assert bounds[1] == pytest.approx([12, 40, 9])
    import subprocess
    tracked = subprocess.check_output(['git', '-C', str(root), 'ls-files', 'review/render'], text=True)
    assert tracked == ""  # Generated review files remain available locally.
    assert 'render → review/render/' in (root / 'PROGRESS.md').read_text()


def test_real_part_only_and_empty_refusal(engine, tmp_path, capsys):
    root = tmp_path / 'solo'
    assert main(['render', '--project', str(root), '--json']) != 0
    assert not json.loads(capsys.readouterr().out)['ok']
    source = tmp_path / 'solo.py'
    source.write_text("box = part.box(10, 20, 3)\nresult = {'box': box}\n")
    assert main(['script', '--set', str(source), '--project', str(root), '--json']) == 0
    initial = json.loads(capsys.readouterr().out)
    assert main(['render', '--project', str(root), '--json']) == 0
    capsys.readouterr()
    summary = json.loads((root / 'review/render/summary.json').read_text())
    assert set(summary['objects']) == {'box'}
    assert summary['revision'] == initial['accepted_revision']
    first = (root / 'review/render/iso.svg').read_bytes()
    assert main(['render', '--project', str(root), '--json']) == 0
    capsys.readouterr()
    assert (root / 'review/render/iso.svg').read_bytes() == first
