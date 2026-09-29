# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A touching pair's ``common`` is first run on the region the two can share (ADR-438).

``ot10-hexapod-10``'s refused build spent 77 CPU-seconds on ``common``
between its 250-face tub and the visor seated on it, to answer 0.0. Two
solids share volume only inside both their boxes, so the static fit cuts a
side to that overlap, grown by a margin, when most of its faces lie outside
it: 9 CPU-seconds for the same 0.0. The cut decides only a zero; any other
answer is the whole boolean's, as before.
"""

from __future__ import annotations

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
    def __init__(self, box):
        self.box = box

    def optimalBoundingBox(self, use_triangulation, use_tolerance):
        assert use_triangulation is False and use_tolerance is True
        return self.box


class _Whole:
    """Both shells as one compound: the two shapes touch."""

    def distToShape(self, other):
        return (0.0, None, None)


class _Result:
    def __init__(self, volume):
        self.Volume = volume


class _Shape:
    """A solid whose ``common`` calls are recorded, whole or cut to the region."""

    def __init__(self, name, box, faces, calls, volumes, cut=False):
        self.name, self.box, self.Faces, self.calls, self.volumes = name, box, faces, calls, volumes
        self.cut = cut
        self.Solids = [types.SimpleNamespace(Vertexes=[types.SimpleNamespace(Point="outside")])]
        self.Shells = ["shell"]

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

    def common(self, other):
        if other == "region":
            self.calls.append("cut " + self.name)
            return _Shape(self.name, self.box, self.Faces, self.calls, self.volumes, cut=True)
        kind = "cut" if self.cut or other.cut else "whole"
        self.calls.append(kind + " common")
        return _Result(self.volumes[kind])


def _kernel(monkeypatch):
    part = types.ModuleType("Part")
    part.Compound = lambda shells: _Whole()
    part.makeBox = lambda *args: "region"
    app = types.ModuleType("FreeCAD")
    app.Vector = lambda *xyz: xyz
    monkeypatch.setitem(sys.modules, "Part", part)
    monkeypatch.setitem(sys.modules, "FreeCAD", app)
    monkeypatch.setattr(worker, "_cpu_stage", lambda stage: None)


def _pair(calls, volumes, tub_faces_near=2):
    around = _Box((-80, -60, 0), (80, 60, 90))
    near = [_Face(_Box((75, -60, 0), (80, 60, 90)))] * tub_faces_near
    far = [_Face(_Box((-80, -60, 0), (-75, 60, 90)))] * (10 - tub_faces_near)
    tub = _Shape("tub", around, near + far, calls, volumes)
    visor_box = _Box((70, -36, 85), (84, 36, 110))
    visor = _Shape("visor", visor_box, [_Face(visor_box)] * 4, calls, volumes)
    return tub, visor


def _measure(monkeypatch, shapes):
    monkeypatch.setattr(worker, "_component_world_shape", lambda component: shapes[component])
    (row,) = worker._measure_clearance({name: name for name in shapes})
    assert row["distance_mm"] == 0.0 and "error" not in row
    return row


def test_a_touching_pair_is_answered_on_the_housing_cut_to_the_shared_region(monkeypatch):
    """The visor on the tub, in either order: the tub is cut, the whole boolean never runs."""

    calls = []
    _kernel(monkeypatch)
    tub, visor = _pair(calls, {"cut": 0.0, "whole": 0.0})
    for shapes in ({"c_tub": tub, "c_visor": visor}, {"c_visor": visor, "c_tub": tub}):
        calls.clear()
        assert _measure(monkeypatch, shapes)["common_volume_mm3"] == 0.0
        # Eight of the tub's ten faces lie outside the region: it is cut. All
        # four of the visor's meet it: it is not.
        assert calls == ["cut tub", "cut common"]


def test_a_cut_that_is_not_zero_leaves_the_volume_to_the_whole_boolean(monkeypatch):
    """A screw through the wall: the published volume is the uncut one, digit for digit."""

    calls = []
    _kernel(monkeypatch)
    tub, visor = _pair(calls, {"cut": 0.29839153663654, "whole": 0.29839153663654316})
    row = _measure(monkeypatch, {"c_tub": tub, "c_visor": visor})
    assert row["common_volume_mm3"] == 0.29839153663654316
    assert calls == ["cut tub", "cut common", "whole common"]


def test_no_side_mostly_outside_the_region_and_the_sweep_run_whole(monkeypatch):
    """A cut that removes little is a second boolean for nothing; the sweep passes no boxes."""

    calls = []
    _kernel(monkeypatch)
    tub, visor = _pair(calls, {"cut": 0.0, "whole": 0.0}, tub_faces_near=5)
    assert _measure(monkeypatch, {"c_tub": tub, "c_visor": visor})["common_volume_mm3"] == 0.0
    assert calls == ["whole common"]
    calls.clear()
    tub, visor = _pair(calls, {"cut": 0.0, "whole": 0.0})
    assert worker._common_volume(tub, visor, 0.0) == 0.0 and calls == ["whole common"]


_DRIVER = r'''
import json, sys
import FreeCAD as App
import Part
sys.path.insert(0, sys.argv[-1])
import cadex_assembly_worker as worker
# A hollow tub with a drilled floor, a visor seated on its rim at one end, and
# a screw through the end wall under the visor.
tub = Part.makeBox(160, 120, 90, App.Vector(-80, -60, 0)).cut(
    Part.makeBox(150, 110, 90, App.Vector(-75, -55, 5)))
for x in (-60, -40, -20, 0, 20, 40):
    for y in (-30, 30):
        tub = tub.cut(Part.makeCylinder(2, 5, App.Vector(x, y, 0)))
visor = Part.makeBox(25, 40, 20, App.Vector(60, -20, 90))
screw = Part.makeCylinder(1.5, 20, App.Vector(77.5, 0, 80))
rows = []
for name, a, b in (("tub/visor", tub, visor), ("visor/tub", visor, tub),
                   ("tub/screw", tub, screw), ("screw/tub", screw, tub)):
    boxes = tuple(shape.optimalBoundingBox(False, True) for shape in (a, b))
    distance = worker._boundary_distance(a, b, boxes, {})
    rows.append([name, distance, worker._clipped_common_is_zero(a, b, boxes, {}),
                 worker._common_volume(a, b, distance, boxes, {}), float(a.common(b).Volume)])
print('CLEARANCE-FRAME ' + json.dumps(rows))
'''


@pytest.mark.skipif(kernel.FREECADCMD is None, reason="Needs real OCCT")
def test_the_cut_common_agrees_with_the_whole_common_on_real_occt(tmp_path, monkeypatch):
    """ADR-438 on real OCCT: a zero proved on the cut, a real overlap left to the whole boolean."""

    monkeypatch.setattr(kernel, "_FRAME_DRIVER", _DRIVER)
    rows = kernel._drive_frame(tmp_path)
    assert [row[0] for row in rows] == ["tub/visor", "visor/tub", "tub/screw", "screw/tub"]
    for name, distance, cut_zero, volume, whole in rows:
        assert distance <= worker._DISJOINT_DISTANCE_MM, name
        assert volume == whole, (name, volume, whole)
    assert [row[2] for row in rows] == [True, True, False, False]
    assert rows[0][3] == 0.0
    assert rows[2][3] == pytest.approx(3.141592653589793 * 1.5 ** 2 * 10, rel=1e-6)
