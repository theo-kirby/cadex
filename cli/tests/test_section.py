# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
import json
import math
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import pytest

from cadex_cli.section import (contours, derived_section, offset_candidates,
                               section_snapshot, write_section)
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


def slab(x, y, z, color=(1, 2, 3)):
    """Triangles of one axis-aligned box, given (lo, hi) per axis."""
    vertices = [(a, b, c) for a in x for b in y for c in z]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
             (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return [(color, tuple(vertices[i] for i in tri))
            for a, b, c, d in faces for tri in ((a, b, c), (a, c, d))]


def accepted(objects):
    """A render snapshot pair over named triangle lists, as the walk sees it."""
    triangles, summary = [], {}
    for name, tris in objects:
        points = [p for _, tri in tris for p in tri]
        summary[name] = {'triangles': len(tris), 'color': (1, 2, 3),
                         'bounds_mm': [[fn(p[j] for p in points) for j in range(3)]
                                       for fn in (min, max)]}
        triangles.extend(tris)
    return triangles, {'revision': 'r'*64, 'digest': 'd', 'objects': summary, 'limits': {}}


def test_derived_offset_cuts_the_part_a_constant_misses():
    # The ot4-quill shape: a housing straddling Y=0 and a quill entirely at -Y.
    # The literal 3.125 mm the walk used to cut at reports `ok` overall while
    # the moving part it exists to look at is missing from the drawing.
    triangles, source = accepted([
        ('housing', slab((-46, 46), (-42, 42), (0, 164))),
        ('quill', slab((-7, 23), (-32, -10), (16, 152))),
    ])
    fixed = section_snapshot(triangles, source, 'XZ', 3.125)
    assert fixed['status'] == 'ok' and fixed['objects']['quill']['status'] == 'empty'

    derived = derived_section(triangles, source, 'XZ')
    assert derived['offset_source'] == 'derived'
    assert derived['offset_mm'] == -21.0  # the two parts' only common band
    assert derived['status'] == 'ok'
    assert all(obj['status'] == 'ok' for obj in derived['objects'].values())
    assert offset_candidates(source, 'XZ')[0] == derived['offset_mm']


def test_derived_offset_skips_a_candidate_the_cut_cannot_support():
    # A stack of two boxes meeting at Y=0 puts vertices on its own centre
    # plane, which `contours` refuses; the next candidate is taken instead.
    stack = slab((0, 10), (-10, 0), (0, 10)) + slab((0, 10), (0, 10), (0, 10))
    triangles, source = accepted([('stack', stack), ('solid', slab((0, 10), (-6, 10), (0, 10)))])
    assert offset_candidates(source, 'XZ') == [0.0, 2.0, -2.0, -5.0, 5.0, 6.0]
    assert section_snapshot(triangles, source, 'XZ', 0.0)['status'] == 'unsupported'
    derived = derived_section(triangles, source, 'XZ')
    assert derived['offset_mm'] == 2.0 and derived['status'] == 'ok'
    assert derived['offset_candidates_mm'] == [0.0, 2.0, -2.0, -5.0, 5.0, 6.0]


def prism(cx, cy, radius, sides, z):
    """A tessellated cylinder about a vertical axis.

    Unlike a box, its facet seams land on its own symmetry planes -- which is
    why the live quill refused the cut at its bounding-box centre and a slab
    standing in for it did not.
    """
    ring = [(cx + radius*math.cos(2*math.pi*i/sides), cy + radius*math.sin(2*math.pi*i/sides))
            for i in range(sides)]
    walls = [((1, 2, 3), tri)
             for i in range(sides)
             for tri in (((*ring[i], z[0]), (*ring[(i+1) % sides], z[0]), (*ring[(i+1) % sides], z[1])),
                         ((*ring[i], z[0]), (*ring[(i+1) % sides], z[1]), (*ring[i], z[1])))]
    caps = [((1, 2, 3), ((*ring[0], zk), (*ring[i], zk), (*ring[i+1], zk)))
            for zk in z for i in range(1, sides - 1)]
    return walls + caps


def test_a_seam_on_the_best_candidate_costs_millimetres_not_the_part():
    # The live ot4-quill failure (ADR-270): the quill's bounding-box centre is
    # the one plane that crosses both parts, and the tessellation puts vertices
    # on it. Before the quarter-span siblings the derivation fell all the way
    # back to Y=0, which cuts the housing and misses the quill entirely.
    triangles, source = accepted([
        ('housing', slab((-46, 46), (-42, 42), (0, 164))),
        ('quill', prism(8, -21, 11, 8, (16, 152))),
    ])
    candidates = offset_candidates(source, 'XZ')
    assert candidates[0] == -21.0  # still the best drawing, and still first
    assert section_snapshot(triangles, source, 'XZ', -21.0)['status'] == 'unsupported'

    derived = derived_section(triangles, source, 'XZ')
    assert derived['offset_source'] == 'derived' and derived['status'] == 'ok'
    assert derived['offset_mm'] == -15.5  # a quarter span off the same centre
    assert all(obj['status'] == 'ok' for obj in derived['objects'].values())
    assert 0.0 in candidates and candidates.index(0.0) > candidates.index(-15.5)


def test_derived_offset_reports_the_unsupported_cut_when_no_candidate_works():
    # A plate lying in the cut plane has no thickness to step off into: every
    # sibling collapses onto the centre, and the first cut is what is reported.
    triangles, source = accepted([('plate', slab((0, 10), (0, 0), (0, 10)))])
    assert offset_candidates(source, 'XZ') == [0.0]
    derived = derived_section(triangles, source, 'XZ')
    assert derived['offset_mm'] == 0.0 and derived['status'] == 'unsupported'
    assert derived['available'] is False and derived['offset_source'] == 'derived'


def test_derived_offset_prefers_the_plane_that_cuts_over_the_plane_that_crosses():
    # Bounds are not the solid (ADR-273). Three two-lobed rings and one post
    # all span y -10..10, so the shared centre plane has the best coverage any
    # candidate can have -- and it passes through all three gaps, cutting the
    # post alone. Taking the first candidate whose overall status was `ok`
    # accepted that one-object drawing; counting what came back does not.
    def ring():
        return slab((0, 10), (-10, -4), (0, 10)) + slab((0, 10), (4, 10), (0, 10))
    triangles, source = accepted([('post', slab((0, 10), (-10, 10), (0, 10))),
                                  ('ring_a', ring()), ('ring_b', ring()), ('ring_c', ring())])
    assert offset_candidates(source, 'XZ') == [0.0, -5.0, 5.0]
    crossing = section_snapshot(triangles, source, 'XZ', 0.0)
    assert crossing['status'] == 'ok' and crossing['objects_cut'] == 1

    derived = derived_section(triangles, source, 'XZ')
    assert derived['offset_mm'] == -5.0 and derived['objects_cut'] == 4
    assert all(obj['status'] == 'ok' for obj in derived['objects'].values())


def test_every_object_keeps_its_own_candidate_plane():
    # The live ot4-swing2 shape (ADR-273): a long base plate, a dense cluster
    # of mount hardware at one end, and the moving arm with its pinch fastener
    # at the other. The cluster's planes cover more bounds and sit nearer the
    # overall centre, so under a cap of eight they filled every place and the
    # arm's own centre plane was never cut at all -- the derivation could not
    # have chosen it however it ranked what it had.
    def part(lo, hi):
        return slab((0, 10), (lo, hi), (0, 10))
    triangles, source = accepted([
        ('plate', part(-45, 32)), ('bolt_l', part(-12.1, 8.9)), ('bolt_r', part(-12.1, 8.9)),
        ('nut_l', part(-10.4, -8)), ('nut_r', part(-10.4, -8)), ('retainer', part(0, 5.9)),
        ('servo', part(-18.5, 13.9)), ('pinch', part(13.15, 18.65)), ('arm', part(10.9, 20.9)),
    ])
    candidates = offset_candidates(source, 'XZ')
    assert candidates[:8] == [-9.2, -8.6, -9.8, 2.95, 1.475, 3.65, 4.425, 5.8]  # the old eight
    assert 13.4 in candidates and 18.4 in candidates  # the arm's own, now cut too
    assert section_snapshot(triangles, source, 'XZ', 13.4)['objects']['arm']['status'] == 'ok'

    # ...and the honest half of the same measurement: no plane reaches both
    # ends, so the best drawing is still the cluster's and still omits the arm.
    derived = derived_section(triangles, source, 'XZ')
    assert derived['offset_mm'] == -9.2 and derived['objects_cut'] == 6
    assert derived['objects']['arm']['status'] == 'empty'
