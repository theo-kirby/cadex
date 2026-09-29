# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A housing is measured face by face against its part's box (ADR-437).

``ot10-hexapod-10``'s refused builds spent their fit budget measuring a
hollow tub against the boards it houses. The tub's box overlaps every
board, so no box culled a pair, and ``distToShape`` met all 250 tub faces
against all 77 faces of a board: 117 CPU-seconds for a 12.4 mm answer, 111
of them on three faces 28-30 mm away. Each face's distance to the board's
box bounds its distance to the board from below, so those faces need not
be measured. Two shells that touch need no re-measurement on the solids.
"""

from __future__ import annotations

import json
import sys
import types

import pytest

import cadex_assembly_worker as worker
import test_clearance_scope as kernel


class _Box:
    def __init__(self, low, high):
        self.XMin, self.YMin, self.ZMin = low
        self.XMax, self.YMax, self.ZMax = high
        self.XLength, self.YLength, self.ZLength = (h - l for l, h in zip(low, high))


class _Face:
    """A housing face: its exact box, its distance to the part's box, and to the part."""

    def __init__(self, name, box, bound, exact, calls):
        self.name, self.box, self.bound, self.exact, self.calls = name, box, bound, exact, calls

    def optimalBoundingBox(self, use_triangulation, use_tolerance):
        assert use_triangulation is False and use_tolerance is True
        return self.box

    def distToShape(self, other):
        if other == "bound":
            self.calls.append("bound " + self.name)
            return (self.bound, None, None)
        self.calls.append(self.name)
        return (self.exact, None, None)


class _Whole:
    """Both shells as one compound: measuring it meets every face."""

    def __init__(self, calls, value):
        self.calls, self.value = calls, value

    def distToShape(self, other):
        if isinstance(other, _Face):
            return other.distToShape(self)
        self.calls.append("whole")
        return (self.value, None, None)


class _Solid:
    Vertexes = [types.SimpleNamespace(Point="outside")]


class _Shape:
    def __init__(self, box, faces, calls, solid_distance=0.0):
        self.box, self.Faces, self.calls = box, faces, calls
        self.Solids, self.Shells = [_Solid()], ["shell"]
        self.solid_distance = solid_distance

    def optimalBoundingBox(self, use_triangulation, use_tolerance):
        assert use_triangulation is False and use_tolerance is True
        return self.box

    def isInside(self, point, tolerance, on_face):
        return False

    def isNull(self):
        return False

    @property
    def BoundBox(self):
        return types.SimpleNamespace(intersect=lambda other: True)

    def distToShape(self, other):
        self.calls.append("solid")
        return (self.solid_distance, None, None)


def _kernel(monkeypatch, calls, whole_value):
    part = types.ModuleType("Part")
    part.Compound = lambda shells: _Whole(calls, whole_value)
    part.makeBox = lambda *args: "bound"
    app = types.ModuleType("FreeCAD")
    app.Vector = lambda *xyz: xyz
    monkeypatch.setitem(sys.modules, "Part", part)
    monkeypatch.setitem(sys.modules, "FreeCAD", app)


def _housing(calls):
    around = _Box((-80, -60, 0), (80, 60, 90))
    faces = [_Face("far_offset", around, 28.084, 28.084, calls),
             _Face("back", _Box((-80, -60, 0), (80, -59, 90)), 44.0, 44.0, calls),
             _Face("near", around, 12.0, 12.4, calls),
             _Face("far_bspline", around, 30.603, 30.603, calls),
             _Face("wall", _Box((31, -60, 0), (32, 60, 90)), 11.0, 13.0, calls)]
    tub = _Shape(around, faces, calls)
    board = _Shape(_Box((-20, -15, 40), (20, 15, 55)), [object()] * 77, calls)
    return tub, board


def test_the_static_fit_measures_only_housing_faces_that_could_be_nearer(monkeypatch):
    """The tub against a board it houses, in either order: two faces measured, not all."""

    calls = []
    _kernel(monkeypatch, calls, 12.4)
    tub, board = _housing(calls)
    monkeypatch.setattr(worker, "_cpu_stage", lambda stage: None)
    for order in ({"c_tub": tub, "c_board": board}, {"c_board": board, "c_tub": tub}):
        monkeypatch.setattr(worker, "_component_world_shape", lambda component: order[component])
        calls.clear()
        (row,) = worker._measure_clearance({name: name for name in order})
        assert row["distance_mm"] == 12.4 and row["common_volume_mm3"] == 0.0
        assert "culled" not in row and "error" not in row
        # Best first: the faces whose boxes overlap the board's, then the wall,
        # are bounded by the board's box; the wall and "near" beat every other
        # bound and are measured. The back face's box is 44 mm off: untouched.
        assert calls == ["bound far_offset", "bound near", "bound far_bspline", "bound wall",
                         "wall", "near"]


def test_the_sweep_and_a_part_no_more_complex_than_a_box_are_measured_whole(monkeypatch):
    """No boxes (the sweep, ADR-425) or a housed side of six faces or fewer: one whole call."""

    calls = []
    _kernel(monkeypatch, calls, 12.4)
    tub, board = _housing(calls)
    assert worker._boundary_distance(tub, board) == 12.4 and calls == ["whole"]
    calls.clear()
    screw = _Shape(_Box((-2, -2, 40), (2, 2, 55)), [object()] * 5, calls)
    assert worker._boundary_distance(tub, screw, (tub.box, screw.box)) == 12.4 and calls == ["whole"]


def test_shells_that_touch_are_not_re_measured_on_the_solids(monkeypatch):
    """The visor seated in the tub: 21 CPU-s re-measured a 0.0 the shells had proved."""

    calls = []
    _kernel(monkeypatch, calls, 0.0)
    visor = _Shape(_Box((-30, 50, 20), (30, 62, 60)), [object()] * 4, calls)
    tub = _Shape(_Box((-80, -60, 0), (80, 60, 90)), [object()] * 4, calls)
    assert worker._boundary_distance(tub, visor) == 0.0 and calls == ["whole"]
    # A reading inside the recheck but above zero still goes to the solids.
    calls.clear()
    _kernel(monkeypatch, calls, 2e-14)
    assert worker._boundary_distance(tub, visor) == 0.0 and calls == ["whole", "solid"]


_DRIVER = r'''
import json, sys
import FreeCAD as App
import Part
sys.path.insert(0, sys.argv[-1])
from cadex_assembly_worker import _boundary_distance
# A hollow tub, open at the top, and a board with holes and pins inside it.
tub = Part.makeBox(160, 120, 90, App.Vector(-80, -60, 0)).cut(
    Part.makeBox(150, 110, 90, App.Vector(-75, -55, 5)))
board = Part.makeBox(40, 30, 2, App.Vector(-20, -15, 30))
for x in (-15, -5, 5, 15):
    board = board.cut(Part.makeCylinder(1.5, 2, App.Vector(x, -10, 30)))
    board = board.fuse(Part.makeCylinder(0.6, 8, App.Vector(x, 10, 32)))
board = board.removeSplitter()
dome = Part.makeSphere(60).cut(Part.makeSphere(55)).cut(Part.makeBox(200, 200, 100, App.Vector(-100, -100, -100)))
dome.translate(App.Vector(0, 0, 10))
rows = []
for name, a, b in (("tub/board", tub, board), ("board/tub", board, tub),
                   ("dome/board", dome, board), ("board/dome", board, dome)):
    whole = Part.Compound(a.Shells).distToShape(Part.Compound(b.Shells))[0]
    boxes = tuple(shape.optimalBoundingBox(False, True) for shape in (a, b))
    rows.append([name, len(b.Faces), _boundary_distance(a, b, boxes), whole])
print('CLEARANCE-FRAME ' + json.dumps(rows))
'''


@pytest.mark.skipif(kernel.FREECADCMD is None, reason="Needs real OCCT")
def test_the_culled_distance_equals_the_whole_shell_distance_on_real_occt(tmp_path, monkeypatch):
    """ADR-437 on real OCCT: a board in a tub and under a dome, both orders, to the last digit."""

    monkeypatch.setattr(kernel, "_FRAME_DRIVER", _DRIVER)
    rows = kernel._drive_frame(tmp_path)
    assert [row[0] for row in rows] == ["tub/board", "board/tub", "dome/board", "board/dome"]
    for name, faces, culled, whole in rows:
        assert culled == whole, (name, culled, whole)
    assert rows[0][2] == pytest.approx(25.0)  # the board's underside to the tub floor
    assert 19.0 < rows[2][2] < 21.0  # a pin tip to the dome's inner wall
    assert all(faces > 6 for _name, faces, _culled, _whole in rows[::2])
