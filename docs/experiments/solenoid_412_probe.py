"""Partial nominal exterior only; missing mounting interfaces block catalog delivery.

Reproduce from repository root with the existing headless engine:
  build/release/bin/FreeCADCmd -c 'exec(open("docs/experiments/solenoid_412_probe.py").read())'

Sources, datum decisions and omitted geometry: PROVENANCE.md section 8e.
"""
import json
import math
import FreeCAD as App
import Part


def construct(gap):
    if not math.isfinite(gap) or not 0 <= gap <= 4.9:
        raise ValueError("drawing gap must be finite and within 0..4.9 mm")
    # Z=0 is the main body's push face; +Z is energized push direction.
    # Centering and filled body are approximations, not measured interfaces.
    body = Part.makeBox(17, 14, 29.7, App.Vector(-8.5, -7, -29.7))
    tip = 15.4 - gap
    rear = -36.5 - gap
    # Neck diameter 3 and rear head length 2 are cosmetic choices only.
    neck = Part.makeCylinder(1.5, tip - rear, App.Vector(0, 0, rear))
    cap = Part.makeCylinder(2.5, 10, App.Vector(0, 0, tip - 10))
    head = Part.makeCylinder(3.45, 2, App.Vector(0, 0, rear))
    return body.fuse(neck).fuse(cap).fuse(head).removeSplitter()


for invalid in (-0.1, 5.5, float('nan'), float('inf')):
    try:
        construct(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError(invalid)

for gap in (0, 2.3, 4.9):
    shape = construct(gap)
    assert shape.isValid() and len(shape.Solids) == 1
    bounds = shape.BoundBox
    expected = (-8.5, 8.5, -7, 7, -36.5-gap, 15.4-gap)
    actual = (bounds.XMin, bounds.XMax, bounds.YMin, bounds.YMax,
              bounds.ZMin, bounds.ZMax)
    assert all(abs(a-b) < 1e-7 for a, b in zip(actual, expected)), actual
    assert abs(bounds.ZLength - 51.9) < 1e-7
    # Inspect actual cap surface limits, independently of metadata.
    caps = [face for face in shape.Faces
            if isinstance(face.Surface, Part.Cylinder)
            and abs(face.Surface.Radius - 2.5) < 1e-7]
    assert len(caps) == 1
    assert abs(caps[0].BoundBox.ZMin - (5.4-gap)) < 1e-7
    assert abs(caps[0].BoundBox.ZMax - (15.4-gap)) < 1e-7
    points = [((0, 0, -15), True), ((8.4, 6.9, -15), True),
              ((8.6, 0, -15), False), ((0, 7.1, -15), False)]
    for z in (5.5-gap, 15.3-gap):
        points.extend([((2.4, 0, z), True), ((2.6, 0, z), False)])
    points.extend([((0, 0, 15.5-gap), False),
                   ((0, 0, -36.6-gap), False),
                   ((3.4, 0, -35.5-gap), True),
                   ((3.5, 0, -35.5-gap), False)])
    placed = shape.copy()
    placed.Placement = App.Placement(App.Vector(100, 30, 20),
                                     App.Rotation(App.Vector(1, 1, 1), 120))
    assert placed.isValid() and len(placed.Solids) == 1
    assert abs(shape.Volume - placed.Volume) < 1e-6
    for (x, y, z), occupied in points:
        assert shape.isInside(App.Vector(x, y, z), 1e-7, True) == occupied
        assert placed.isInside(App.Vector(100+z, 30+x, 20+y), 1e-7, True) == occupied
    print('SOLENOID-412 ' + json.dumps({
        'gap_mm': gap, 'bounds_mm': [round(v, 6) for v in actual],
        'volume_mm3': round(shape.Volume, 6),
        'canonical_and_placed_probes': 2 * len(points),
        'mounting_interfaces': 'unsupported; omitted'}))
print('SOLENOID-412-PARTIAL-OK')
