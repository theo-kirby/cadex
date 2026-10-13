# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A ``part.panel`` piece is measured against its frame face by face, on its geometry's boxes (ADR-678).

A robot cat's torso panels blew the static fit's CPU budget: ``c_frame /
c_waist_r_p0`` cost 386 CPU-seconds for a 0.0 its boss proves. The pieces'
boss seams carry edge tolerances of 1e15 mm and more, so the kernel's
toleranced box around a piece is unbounded and its classifier calls a point
10 m away inside it. The frame then read as lying inside the panel, and the
pair went to the solids' ``distToShape``; and no pair with a piece was ever
culled. The geometry's boxes bound all three, and the shells are searched
face pair by face pair, the small faces first.
"""

from __future__ import annotations

import math
import sys
import types

import pytest

import cadex_assembly_worker as worker
import test_clearance_scope as kernel
from test_housed_fit_distance import _Box


class _Face:
    Edges = ()

    def __init__(self, name, box, calls, refined=0.0):
        self.name, self.box, self.calls, self.refined = name, box, calls, refined

    def optimalBoundingBox(self, use_triangulation, use_tolerance):
        assert use_triangulation is False and use_tolerance is False
        return self.box.copy()

    def distToShape(self, other):
        if other == "bound":
            self.calls.append("bound " + self.name)
            return (self.refined, None, None)
        self.calls.append(self.name + "/" + other.name)
        # The boss's end is cast onto the frame's pad; every other pair is apart.
        touching = {self.name, other.name} == {"pad", "boss_end"}
        return (0.0 if touching else 5.0, None, None)


def _point(x, y, z):
    return types.SimpleNamespace(Point=types.SimpleNamespace(x=x, y=y, z=z))


class _Shape:
    def __init__(self, name, box, faces, vertex, calls, tolerance=1e-7, inside=False):
        self.name, self.box, self.Faces, self.calls = name, box, faces, calls
        self.tolerance, self.inside = tolerance, inside
        self.Solids = [types.SimpleNamespace(Vertexes=[vertex])]
        self.Shells = ["shell"]

    def optimalBoundingBox(self, use_triangulation, use_tolerance):
        assert use_triangulation is False and use_tolerance is True
        if self.tolerance > 1.0:
            return _Box((-self.tolerance,) * 3, (self.tolerance,) * 3)
        return self.box.copy()

    def getTolerance(self, mode):
        assert mode == 1
        return self.tolerance

    def isInside(self, point, tolerance, on_face):
        return self.inside

    def isNull(self):
        return False

    @property
    def BoundBox(self):
        return types.SimpleNamespace(intersect=lambda other: True)

    def distToShape(self, other):
        self.calls.append("solids")
        return (0.0, None, None)

    def common(self, other):
        self.calls.append("common")
        return types.SimpleNamespace(Volume=0.0)


class _Whole:
    def __init__(self, calls):
        self.calls = calls

    def distToShape(self, other):
        self.calls.append("whole")
        return (0.0, None, None)


def _kernel(monkeypatch, calls):
    part = types.ModuleType("Part")
    part.Compound = lambda shells: _Whole(calls)
    part.makeBox = lambda *args: "bound"
    app = types.ModuleType("FreeCAD")
    app.Vector = lambda *xyz: xyz
    app.BoundBox = _Box
    monkeypatch.setitem(sys.modules, "Part", part)
    monkeypatch.setitem(sys.modules, "FreeCAD", app)
    monkeypatch.setattr(worker, "_cpu_stage", lambda stage: None)


def _cat(calls):
    """A frame of 31 faces, a panel piece of vast tolerance on it, and a paw 90 mm off."""

    walls = [_Face(f"wall{index}", _Box((index * 6.5, 0, 0), ((index + 1) * 6.5, 60, 40)), calls)
             for index in range(30)]
    frame = _Shape("frame", _Box((0, 0, 0), (200, 60, 40)),
                   walls + [_Face("pad", _Box((95, 25, 40), (105, 35, 40)), calls)],
                   _point(0, 0, 0), calls)
    panel = _Shape("panel", _Box((-10, -10, 40), (210, 70, 77)),
                   [_Face("skin", _Box((-10, -10, 55), (210, 70, 77)), calls, refined=15.0),
                    _Face("boss_side", _Box((95, 25, 40), (105, 35, 57)), calls),
                    _Face("boss_end", _Box((95, 25, 40), (105, 35, 40)), calls)],
                   _point(-10, -10, 77), calls, tolerance=7.3e15, inside=True)
    paw = _Shape("paw", _Box((300, 0, 0), (320, 20, 20)),
                 [_Face(f"paw{index}", _Box((300, 0, 0), (320, 20, 20)), calls) for index in range(8)],
                 _point(300, 0, 0), calls)
    return {"c_frame": frame, "c_panel": panel, "c_paw": paw}


def test_a_panel_on_its_frame_is_proved_touching_by_its_boss_alone(monkeypatch):
    """No solids, no whole shells: the boss's end against the pad, after two box bounds."""

    calls = []
    _kernel(monkeypatch, calls)
    shapes = _cat(calls)
    monkeypatch.setattr(worker, "_component_world_shape", lambda component: shapes[component])
    rows = worker._measure_clearance({name: name for name in shapes})
    by_pair = {(row["first"], row["second"]): row for row in rows}
    touching = by_pair[("c_frame", "c_panel")]
    assert touching["distance_mm"] == 0.0 and touching["common_volume_mm3"] == 0.0
    assert "culled" not in touching and "error" not in touching
    # The panel's geometry box is the larger, so its faces are bounded by the
    # frame's box: the skin's box is 15 mm off it and never refined. The
    # boss's end is the smallest face, and the frame's pad the smallest of
    # those its box meets: their pair is measured first, and reads 0.0.
    assert calls[:3] == ["bound boss_end", "bound boss_side", "pad/boss_end"]
    assert "solids" not in calls and "whole" not in calls


def test_a_panel_of_vast_tolerance_is_culled_on_its_geometry(monkeypatch):
    """The paw 92 mm from the panel's geometry box: culled, as the toleranced box never let it be."""

    calls = []
    _kernel(monkeypatch, calls)
    shapes = _cat(calls)
    monkeypatch.setattr(worker, "_component_world_shape", lambda component: shapes[component])
    rows = worker._measure_clearance({name: name for name in shapes})
    by_pair = {(row["first"], row["second"]): row for row in rows}
    far = by_pair[("c_panel", "c_paw")]
    assert far["culled"] is True and far["distance_mm"] == pytest.approx(math.hypot(90.0, 20.0), abs=0.01)
    assert not any(call.startswith("paw") or "/paw" in call for call in calls)
    # A shape of ordinary tolerance keeps its toleranced box, and the gap it
    # was culled with: the frame's box to the paw's.
    assert by_pair[("c_frame", "c_paw")]["distance_mm"] == 100.0


def test_a_solid_a_classifier_calls_inside_is_still_measured_on_the_shells(monkeypatch):
    """The frame's vertex lies outside the panel's geometry: no solids call, without boxes too."""

    calls = []
    _kernel(monkeypatch, calls)
    shapes = _cat(calls)
    assert worker._boundary_distance(shapes["c_frame"], shapes["c_panel"]) == 0.0
    assert calls == ["whole"]
    # A vertex inside the geometry box as well leaves the pair to the solids.
    calls.clear()
    shapes["c_frame"].Solids[0].Vertexes = [_point(100, 30, 50)]
    assert worker._boundary_distance(shapes["c_frame"], shapes["c_panel"]) == 0.0
    assert calls == ["solids"]


_DRIVER = r'''
import json, sys
import FreeCAD as App
import Part
sys.path.insert(0, sys.argv[-1])
import cadex_assembly_worker as worker
# A drilled box beam, and a 2 mm B-spline panel arching over it with a boss
# column cast onto its top.
frame = Part.makeBox(200, 60, 40).cut(Part.makeBox(196, 56, 40, App.Vector(2, 2, -1)))
for x in range(10, 200, 12):
    frame = frame.cut(Part.makeCylinder(2.5, 70, App.Vector(x, -5, 20), App.Vector(0, 1, 0)))
frame = frame.removeSplitter()
poles = [[App.Vector(x, y, 55 + 10 * (1 - ((x - 100) / 100.0) ** 2) * (1 - ((y - 30) / 40.0) ** 2))
          for y in (-10, 10, 30, 50, 70)] for x in (-10, 40, 100, 160, 210)]
surface = Part.BSplineSurface()
surface.interpolate(poles)
skin = surface.toShape().makeOffsetShape(2.0, 1e-6, fill=True)
bare = skin.Solids[0]
panel = bare.fuse(Part.makeCylinder(5, 40, App.Vector(100, 30, 40))).removeSplitter().Solids[0]
# A post under the skin, capped by a ball: its nearest point is on the B-spline.
posted = frame.fuse(Part.makeCylinder(4, 15, App.Vector(50, 20, 38))).fuse(
    Part.makeSphere(4, App.Vector(50, 20, 53))).removeSplitter()
# The same panel with one B-spline seam's tolerance made vast, as part.panel's are.
vast = panel.copy()
seam = max((e for e in vast.Edges if "BSpline" in type(e.Curve).__name__), key=lambda e: e.Length)
seam.fixTolerance(1e15)
far = App.Vector(1e4, 1e4, 1e4)
facts = [vast.getTolerance(1), vast.optimalBoundingBox(False, True).DiagonalLength,
         vast.isInside(far, 1e-7, True), len(frame.Faces), len(panel.Faces)]
rows = []
for name, a, b in (("frame/panel", frame, panel), ("panel/frame", panel, frame),
                   ("posted/bare", posted, bare), ("bare/posted", bare, posted),
                   ("frame/vast", frame, vast), ("vast/frame", vast, frame),
                   ("posted/vast", posted, vast)):
    boxes = tuple(shape.optimalBoundingBox(False, True) for shape in (a, b))
    distance = worker._boundary_distance(a, b, boxes, {})
    whole = float(Part.Compound(a.Shells).distToShape(Part.Compound(b.Shells))[0])
    solids = float(a.distToShape(b)[0])
    rows.append([name, distance, whole, solids, worker._common_volume(a, b, distance, boxes, {}),
                 float(a.common(b).Volume)])
print('CLEARANCE-FRAME ' + json.dumps({"facts": facts, "rows": rows}))
'''


@pytest.mark.skipif(kernel.FREECADCMD is None, reason="Needs real OCCT")
def test_the_panel_search_reads_the_whole_shells_numbers_on_real_occt(tmp_path, monkeypatch):
    """ADR-678 on real OCCT: touching, apart across the B-spline, and of vast tolerance, both orders."""

    monkeypatch.setattr(kernel, "_FRAME_DRIVER", _DRIVER)
    report = kernel._drive_frame(tmp_path)
    tolerance, diagonal, _far_inside, frame_faces, panel_faces = report["facts"]
    assert tolerance >= 1e15 and diagonal > 1e15
    assert frame_faces > 40 and panel_faces > 6
    for name, distance, whole, solids, volume, common in report["rows"]:
        assert distance == whole == solids, (name, distance, whole, solids)
        assert volume == common, (name, volume, common)
    by_name = {row[0]: row for row in report["rows"]}
    assert by_name["frame/panel"][1] == 0.0 and by_name["frame/vast"][1] == 0.0
    assert 0.5 < by_name["posted/bare"][1] < 5.0
