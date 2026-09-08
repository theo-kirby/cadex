# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import pytest

from cadex_cli.section import contours, write_section
from cadex_cli.__main__ import main
from cadex_cli.inventory import InventoryError


def box(lo=0, hi=10):
    vertices = [(x, y, z) for x in (lo, hi) for y in (lo, hi) for z in (0, 10)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
             (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return [((1, 2, 3), tuple(vertices[i] for i in tri))
            for a, b, c, d in faces for tri in ((a, b, c), (a, c, d))]


def area(loop):
    return abs(sum(a[0]*b[1]-a[1]*b[0] for a, b in zip(loop, loop[1:]+loop[:1]))) / 2


@pytest.mark.parametrize('plane', ['XY', 'XZ', 'YZ'])
def test_cut_is_closed_not_projection(plane):
    cut = contours(box(), plane, 3)
    assert cut['status'] == 'ok'
    assert len(cut['contours_mm']) == 1
    assert area(cut['contours_mm'][0]) == pytest.approx(100)
    assert contours(box(), plane, 11)['status'] == 'empty'


def test_hole_offset_and_degenerate_contacts():
    cut = contours(box()+box(3, 7), 'XY', 4)
    assert cut['status'] == 'ok'
    assert sorted(area(loop) for loop in cut['contours_mm']) == [16, 100]
    for offset in (0, 10, 1e-7):
        assert contours(box(), 'XY', offset)['status'] == 'unsupported'
    assert contours(box()[:1], 'XY', 4)['status'] == 'unsupported'


def test_failed_acquisition_retains_old_artifact_without_success(tmp_path):
    old = tmp_path / 'review/section/old.svg'
    old.parent.mkdir(parents=True)
    old.write_text('old')
    class Client:
        def request(self, *args):
            return {'ok': False, 'error': 'refused'}
    with pytest.raises(InventoryError, match='refused'):
        write_section(Client(), tmp_path, plane='XY', offset=4)
    assert old.read_text() == 'old'
    assert list(old.parent.iterdir()) == [old]


def test_real_cavity_pose_offsets_and_local_artifacts(engine, tmp_path, capsys):
    root = tmp_path / 'project'
    source = tmp_path / 'script.py'
    source.write_text('''outer = part.box(20, 20, 10)
hole = part.transform(part.cylinder(4, 10), translation=[10, 10, 0])
shape = part.cut(outer, hole)
a = assembly.component(shape, grounded=True, placement={"position": [30, 40, 5], "axis": [0, 0, 1], "angle_degrees": 90})
asm = assembly.assembly([a])
diag = assembly.solve(asm)
result = {"shape": shape, "a": a, "asm": asm, "diag": diag}
''')
    def run(*args):
        code = main([*args, '--project', str(root), '--json'])
        report = json.loads(capsys.readouterr().out)
        assert code == 0, report
        return report
    initial = run('script', '--set', str(source))
    run('section', '--plane', 'XY', '--offset-mm', '8')
    path = next(root.glob('review/section/*/XY-8/summary.json'))
    summary = json.loads(path.read_text())
    assert summary['status'] == 'ok'
    assert summary['revision'] == initial['accepted_revision']
    assert summary['digest'] == initial['digest']
    assert set(summary['objects']) == {'a'}
    obj = summary['objects']['a']
    assert obj['bounds_mm'][0] == pytest.approx([10, 40, 5])
    loops = obj['contours_mm']
    assert len(loops) == 2
    assert sorted(area(loop) for loop in loops) == pytest.approx([50.265, 400], rel=.03)
    image = ET.parse(root / summary['path']).getroot()
    shape = image.find('{*}path')
    assert shape.attrib['fill-rule'] == 'evenodd'
    assert shape.attrib['d'].count('Z') == 2
    assert summary['revision'] in image.find('{*}title').text
    tracked = subprocess.check_output(['git', '-C', str(root), 'ls-files', 'review/section'], text=True)
    assert tracked == ""  # Generated review files remain available locally.
    assert 'section → review/section/' in (root / 'PROGRESS.md').read_text()
    for offset, status in [('18', 'empty'), ('5', 'unsupported')]:
        run('section', '--plane', 'XY', '--offset-mm', offset)
        report = json.loads(next(root.glob(f'review/section/*/XY-{offset}/summary.json')).read_text())
        assert report['status'] == status
    assert main(['section', '--project', str(root), '--plane', 'XY', '--offset-mm', 'nan', '--json']) != 0
    assert not json.loads(capsys.readouterr().out)['ok']


def test_sloping_faces_change_cut_area_with_offset():
    vertices = [(0, 0, 0), (10, 0, 0), (0, 10, 0), (0, 0, 10)]
    triangles = [((1, 2, 3), tuple(vertices[i] for i in face))
                 for face in [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]]
    for offset, expected in [(2.5, 28.125), (5, 12.5)]:
        cut = contours(triangles, 'XY', offset)
        assert cut['status'] == 'ok'
        assert area(cut['contours_mm'][0]) == pytest.approx(expected)
