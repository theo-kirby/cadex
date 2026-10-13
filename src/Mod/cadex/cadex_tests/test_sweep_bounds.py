# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""ADR-686: the swept fit skips a sample only where a bound proves it cannot matter.

``panel-cat-2`` (115 components, 15 driven joints) reached 3 of its joints in
the 180 s sweep budget: a hip spent 120 s in ``distToShape`` on 33 pairs,
16 samples each, most of them 26 to 130 mm apart, because a long leg's box
turned with it covers everything near the hip. Each sample now carries a
lower bound on its distance -- the moving body's hull carried there, its
extent along 13 directions, and, face by face, the distance measured at
another sample less how far that face travels between the two -- and a
sample is measured only while its bound could still change the minimum, a
contact or a common volume. A pair is culled, as a far one always was, only
once every sample is bound past its margin.
"""
import math

import numpy as np
import pytest

import test_clearance_scope as kernel


def _worker():
    import cadex_assembly_worker as worker
    return worker


def _turn(degrees, about=(0.0, 0.0, 0.0)):
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    m = np.eye(4)
    m[:2, :2] = [[c, -s], [s, c]]
    m[:3, 3] = np.array(about) - m[:3, :3] @ np.array(about)
    return m


def _box_faces(low, high):
    """A box's six faces as boxes, eight corners each (the sweep's face pieces)."""
    low, high = np.array(low, float), np.array(high, float)
    faces = []
    for axis in range(3):
        for side in (low[axis], high[axis]):
            lo, hi = low.copy(), high.copy()
            lo[axis] = hi[axis] = side
            faces.append([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    return np.array(faces, float)


def _corners(low, high):
    return np.array([[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1])
                     for z in (low[2], high[2])], float)


def test_relative_motion_and_carried_points_agree_with_the_matrix_product():
    worker = _worker()
    rng = np.random.default_rng(7)
    points = rng.normal(size=(20, 3)) * 50
    anchor, mover = _turn(30, (5, 7, 0)), _turn(-50, (40, -3, 0))
    mover[:3, 3] += (1.5, -2.0, 3.0)
    relative = worker._relative_motion(anchor, mover)
    assert np.allclose(relative, np.linalg.inv(anchor) @ mover)
    assert np.allclose(worker._relative_motion(None, mover), mover)
    assert np.allclose(worker._relative_motion(anchor, None), np.linalg.inv(anchor))
    assert np.allclose(worker._carried(points, mover), points @ mover[:3, :3].T + mover[:3, 3])


def test_a_face_bound_never_exceeds_the_distance_and_needs_both_solids_outside_each_other():
    """The face-by-face bound is below the true distance, and absent where one box could hold the other."""
    worker = _worker()
    # A 200 mm arm turning about z, and a block beside the path of its root.
    arm = ((0.0, -5.0, -5.0), (200.0, 5.0, 5.0))
    block = ((20.0, 40.0, -5.0), (30.0, 50.0, 5.0))
    motions = [_turn(a) for a in range(0, 46, 5)]
    pieces = worker._SweepPieces(_box_faces(*arm), _box_faces(*block), [_corners(*arm)],
                                 [_corners(*block)], [*block[0], *block[1]], motions)

    def exact(m):
        # The block's nearest approach to the turned arm, on a fine grid of
        # the arm's surface: an upper bound on the true distance.
        u = np.linspace(0, 1, 201)
        best = math.inf
        for x, y in [(200 * t, side) for t in u for side in (-5.0, 5.0)] + [(200.0, -5 + 10 * t) for t in u]:
            p = m[:3, :3] @ np.array([x, y, 0.0]) + m[:3, 3]
            gap = np.maximum(0.0, np.maximum(np.array(block[0][:2]) - p[:2], p[:2] - np.array(block[1][:2])))
            best = min(best, float(np.hypot(*gap)))
        return best

    truth = [exact(m) for m in motions]
    for index in range(len(motions)):
        assert pieces.at(index) <= truth[index] + 1e-9
    # A distance measured at one sample bounds its neighbours through the
    # travel of each face, never past the truth.
    pieces.learn(0, truth[0])
    for index in range(len(motions)):
        assert pieces.at(index) <= truth[index] + 1e-9
    assert pieces.at(1) > 0.0
    # A block inside the arm's box: no face bound at all, the whole solids'
    # bound decides.
    inside = ((50.0, -2.0, -2.0), (52.0, 2.0, 2.0))
    held = worker._SweepPieces(_box_faces(*arm), _box_faces(*inside), [_corners(*arm)],
                               [_corners(*inside)], [*inside[0], *inside[1]], motions[:1])
    assert held.at(0) == 0.0 and held.best == [None]


_DRIVER = r'''
import json, math, sys
import FreeCAD as App
import Part
sys.path.insert(0, sys.argv[-1])
import cadex_assembly_worker as worker
from cadex_assembly_worker import _measure_clearance, _sweep_joint
D = App.newDocument('SweepBounds')
def feature(name, shape):
    obj = D.addObject('Part::Feature', name)
    obj.Shape = shape
    return obj
base = feature('base', Part.makeBox(10, 10, 10, App.Vector(-5, -5, -30)))
# A 200 mm arm turning about z from 0 to 90 degrees at 5 degree steps.
arm = feature('arm', Part.makeBox(200, 10, 10, App.Vector(0, -5, -5)))
# 3 mm above the arm's top at 45 degrees and 150 mm out.
over = feature('over', Part.makeBox(8, 8, 4, App.Vector(150 / 2 ** 0.5 - 4, 150 / 2 ** 0.5 - 4, 8)))
# Beyond the arm's tip on the diagonal: its box overlaps the turned arm's
# box, but the arm comes no nearer than 12.1 mm.
corner = feature('corner', Part.makeBox(4, 4, 4, App.Vector(150, 150, -2)))
# In the arm's path at 80 degrees: a real collision.
stop = feature('stop', Part.makeBox(6, 6, 6, App.Vector(100 * math.cos(math.radians(80)) - 3,
                                                        100 * math.sin(math.radians(80)) - 3, -3)))
# Across the arm's path from about 50 to 80 degrees: a long overlap, its
# volume asked for first once the overlap is found, and only its volume
# once the minimum is 0.0 and first contact is known.
wall = feature('wall', Part.makeBox(20, 80, 6, App.Vector(15, 40, -3)))
D.recompute()
components = {o.Name: o for o in (base, arm, over, corner, stop, wall)}
data = {n: {'grounded': n != 'arm'} for n in components}
joints = {'hinge': {'kind': 'revolute', 'suppressed': False, 'parameters': {},
  'angle_limits_degrees': [0, 90], 'length_limits_mm': None,
  'connectors': [{'component_output': 'base', 'local_frame': {'matrix': list(App.Matrix().A)}},
                 {'component_output': 'arm', 'local_frame': {'matrix': list(App.Matrix().A)}}]}}
baseline = _measure_clearance(components)
calls = []
measured = worker._boundary_distance
def counting(first, second, *args, **kwargs):
    calls.append(1)
    return measured(first, second, *args, **kwargs)
worker._boundary_distance = counting
result = _sweep_joint(components, data, joints, baseline, 'hinge', 5)
# A declared 50 mm floor between the arm and the corner block keeps the
# pair exact: no bound past 10 mm decides it.
floored = [dict(row, intent={'minimum_mm': 50.0}) if {row['first'], row['second']} == {'arm', 'corner'}
           else row for row in baseline]
floor_result = _sweep_joint(components, data, joints, floored, 'hinge', 5)
worker._boundary_distance = measured
# Every sample of every pair, on the solids, as the truth.
truth = {}
solved = arm.Placement
for name in ('base', 'over', 'corner', 'stop', 'wall'):
    rows = []
    for degrees in range(0, 91, 5):
        moved = arm.Shape.copy()
        moved.Placement = App.Placement(App.Vector(), App.Rotation(App.Vector(0, 0, 1), degrees)).multiply(solved)
        other = components[name].Shape
        rows.append([degrees, float(moved.distToShape(other)[0]), float(moved.common(other).Volume)])
    truth[name] = rows
print('\nCLEARANCE-FRAME ' + json.dumps(dict(result=result, floor=floor_result, truth=truth, calls=len(calls))))
'''


@pytest.mark.skipif(kernel.FREECADCMD is None, reason='Needs real OCCT')
def test_a_sweep_measures_only_the_samples_a_bound_cannot_settle(tmp_path, monkeypatch):
    """Exact where it was exact, bounded where it was bounded, and far fewer queries.

    Every exact row equals the minimum over every sample on the solids; the
    collisions keep their first contact and their largest common volume; the
    block beyond the tip, whose box the turned arm's box overlaps, is now a
    bound above the margin and below the truth instead of 19 queries; a
    declared floor above that bound keeps it exact.
    """

    monkeypatch.setattr(kernel, '_FRAME_DRIVER', _DRIVER)
    out = kernel._drive_frame(tmp_path)
    result, truth = out['result'], out['truth']
    assert result['status'] == 'complete', result
    rows = {frozenset((r['first'], r['second'])): r for r in result['pairs']}
    for name, samples in truth.items():
        row = rows[frozenset(('arm', name))]
        assert row['relative_motion'] is True
        least = min(d for _, d, _ in samples)
        if row.get('culled'):
            assert 10.0 < row['minimum_distance_mm'] <= least + 1e-9, (name, row, least)
            assert row['maximum_common_volume_mm3'] == 0.0 and row['first_contact_degrees'] is None
            assert all(v == 0.0 for _, _, v in samples)
            continue
        assert row['minimum_distance_mm'] == pytest.approx(least, abs=1e-6), (name, row)
        assert row['maximum_common_volume_mm3'] == pytest.approx(max(v for _, _, v in samples), abs=1e-6)
        contact = [degrees for degrees, d, _ in samples if d <= 1e-3]
        assert row['first_contact_degrees'] == (contact[0] if contact else None), (name, row)
    over, corner, stop = (rows[frozenset(('arm', n))] for n in ('over', 'corner', 'stop'))
    assert 'culled' not in over and over['minimum_distance_mm'] == pytest.approx(3.0, abs=1e-6)
    assert 'culled' not in stop and stop['first_contact_degrees'] == 80
    assert stop['maximum_common_volume_mm3'] > 100
    assert corner.get('culled') is True, corner
    wall = rows[frozenset(('arm', 'wall'))]
    assert wall['first_contact_degrees'] == 45 and wall['maximum_common_volume_mm3'] > 3900
    # Five moving pairs at 19 samples: the code before ADR-686 made 78
    # distance queries here; the bounds, and asking an overlap for its
    # volume alone, leave 28.
    assert out['calls'] < 40, out['calls']
    floored = {frozenset((r['first'], r['second'])): r for r in out['floor']['pairs']}
    exact = floored[frozenset(('arm', 'corner'))]
    assert 'culled' not in exact
    assert exact['minimum_distance_mm'] == pytest.approx(min(d for _, d, _ in truth['corner']), abs=1e-6)
    assert 12.0 < exact['minimum_distance_mm'] < 12.5
