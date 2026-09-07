"""SKF GE 6 C nominal joint qualification, not a public catalog implementation.

Run at repo root:
  build/release/bin/FreeCADCmd -c 'exec(open("docs/experiments/ge6c_joint_probe.py").read())'

Source and approximation contract: PROVENANCE.md section 8f.
"""
import json
import math
import FreeCAD as App
import Part


def cylinder(radius, length):
    return Part.makeCylinder(radius, length, App.Vector(0, 0, -length / 2))


def construct(tilt):
    if not math.isfinite(tilt) or abs(tilt) > 13:
        raise ValueError("nominal tilt must be finite and within -13..13 degrees")
    sphere = Part.makeSphere(5)
    outer = cylinder(7, 4).cut(sphere)
    inner = sphere.common(cylinder(6, 6)).cut(cylinder(3, 8))
    inner.rotate(App.Vector(), App.Vector(0, 1, 0), tilt)
    return outer, inner


for invalid in (-13.01, 13.01, float('nan'), float('inf')):
    try:
        construct(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError(invalid)

for tilt in (-13, 0, 6.5, 13):
    outer, inner = construct(tilt)
    rotation = App.Rotation(App.Vector(0, 1, 0), tilt)
    # Independently integrated spherical slabs minus the cylindrical bore.
    expected_volumes = (math.pi * (196 - (100 - 16/3)), 78 * math.pi)
    for shape, volume in zip((outer, inner), expected_volumes):
        assert shape.isValid() and len(shape.Solids) == 1
        assert abs(shape.Volume - volume) < 1e-6
    assert outer.common(inner).Volume < 1e-7
    assert abs(outer.BoundBox.XLength - 14) < 1e-7
    assert abs(outer.BoundBox.ZLength - 4) < 1e-7
    # Read actual mating surfaces, independently of construction metadata.
    for shape, radius, axis in ((outer, 7, App.Vector(0, 0, 1)),
                                (inner, 3, rotation.multVec(App.Vector(0, 0, 1)))):
        faces = [f for f in shape.Faces if isinstance(f.Surface, Part.Cylinder)]
        assert len(faces) == 1
        surface = faces[0].Surface
        assert abs(surface.Radius - radius) < 1e-7
        assert abs(abs(surface.Axis.dot(axis)) - 1) < 1e-7
        spheres = [f.Surface for f in shape.Faces if isinstance(f.Surface, Part.Sphere)]
        assert len(spheres) == 1 and abs(spheres[0].Radius - 5) < 1e-7
    # Full nominal bore remains open along the tilted shaft axis.
    shaft = cylinder(2.99, 20)
    shaft.rotate(App.Vector(), App.Vector(0, 1, 0), tilt)
    assert outer.common(shaft).Volume < 1e-7
    assert inner.common(shaft).Volume < 1e-7
    # Source limiting shoulders: shaft da max=8; housing Da min=9.5.
    # No fillets or fit tolerances; test both sides of the nominal faces.
    for side in (-1, 1):
        shoulder = Part.makeCylinder(4, 2, App.Vector(0, 0, side * 3),
                                     App.Vector(0, 0, side))
        shoulder.rotate(App.Vector(), App.Vector(0, 1, 0), tilt)
        assert outer.common(shoulder).Volume < 1e-7
        housing = Part.makeCylinder(7, 2, App.Vector(0, 0, side * 2),
                                    App.Vector(0, 0, side))
        opening = Part.makeCylinder(4.75, 2, App.Vector(0, 0, side * 2),
                                    App.Vector(0, 0, side))
        assert inner.common(housing.cut(opening)).Volume < 1e-7
    probes = [((6.9, 0, 0), True), ((7.1, 0, 0), False),
              ((5.1, 0, 0), True), ((4.9, 0, 0), False),
              ((6, 0, 1.9), True), ((6, 0, 2.1), False)]
    inner_probes = [((2.9, 0, 0), False), ((3.1, 0, 0), True),
                    ((4.9, 0, 0), True), ((5.1, 0, 0), False),
                    ((3.5, 0, 2.9), True), ((3.5, 0, 3.1), False)]
    placement = App.Placement(App.Vector(23, -17, 41),
                              App.Rotation(App.Vector(1, 2, 3), 37))
    for shape, points, local in ((outer, probes, App.Rotation()),
                                 (inner, inner_probes, rotation)):
        placed = shape.copy()
        placed.Placement = placement.multiply(shape.Placement)
        assert placed.isValid() and abs(placed.Volume - shape.Volume) < 1e-6
        for point, occupied in points:
            point = local.multVec(App.Vector(*point))
            assert shape.isInside(point, 1e-7, True) == occupied
            assert placed.isInside(placement.multVec(point), 1e-7, True) == occupied
    print('GE6C ' + json.dumps({'tilt_deg': tilt,
          'outer_volume_mm3': round(outer.Volume, 6),
          'inner_volume_mm3': round(inner.Volume, 6),
          'overlap_mm3': outer.common(inner).Volume,
          'canonical_and_placed_probes': 24}))
print('GE6C-NOMINAL-OK')
