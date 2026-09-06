"""Headless OCCT experiment; not a catalog recipe or installation envelope.

Run from repo root:
  build/release/bin/FreeCADCmd -c 'exec(open("docs/experiments/l12_nominal_probe.py").read())'

Dimension provenance and intentional approximations: PROVENANCE.md section 8d.
No manufacturer CAD is imported by this construction.
"""
import json
import FreeCAD as App
import Part


def box(x, y, z, corner):
    return Part.makeBox(x, y, z, App.Vector(*corner))


def construct(extension):
    # Datum: rear mounting centre; travel +Z; both mounting axes +X.
    # Primitive housing, rear lug and sleeve replace undimensioned transitions.
    housing = box(14.9, 18, 37, (-7.45, -7.5, 4.5))
    rear = box(8, 9, 12.5, (-4, -4.5, -4.5))
    sleeve = box(12, 12, 60, (-6, -6, 35.5))
    # Filled shaft is an exterior approximation, not a physical mass model.
    shaft = Part.makeCylinder(4.5, 8 + extension, App.Vector(0, 0, 90))
    centre = 102 + extension
    # Supplied clevis eye: diameter 9, CAD-derived 6 mm flats at the bore.
    # Flat-ended cylinder/box intersection approximates its rounded tip/neck.
    eye = Part.makeCylinder(4.5, 9, App.Vector(0, 0, centre - 4.5))
    eye = eye.common(box(6, 10, 9, (-3, -5, centre - 4.5)))
    shape = housing.fuse(rear).fuse(sleeve).fuse(shaft).fuse(eye)
    for z in (0, centre):
        shape = shape.cut(Part.makeCylinder(
            2.125, 20, App.Vector(-10, 0, z), App.Vector(1, 0, 0)))
    return shape.removeSplitter()


for extension in (0, 23.5, 50):
    shape = construct(extension)
    assert shape.isValid() and len(shape.Solids) == 1
    # Read actual cylindrical surfaces, not returned metadata or recipe inputs.
    centres = sorted({round(f.Surface.Center.z, 7) for f in shape.Faces
                      if isinstance(f.Surface, Part.Cylinder)
                      and abs(f.Surface.Radius - 2.125) < 1e-7
                      and abs(abs(f.Surface.Axis.x) - 1) < 1e-7})
    assert centres == [0, 102 + extension], centres
    probes = []
    for z, half_width in ((0, 4), (102 + extension, 3)):
        # Axis and near bore wall: void through the full mounting width.
        for x in (-half_width + .1, 0, half_width - .1):
            probes.extend([((x, 0, z), False), ((x, 2.1, z), False),
                           ((x, 2.2, z), True), ((x, 3, z), True)])
        probes.append(((half_width + .1, 3, z), False))
    probes.extend([((0, 0, 20), True), ((5.9, 5.9, 70), True),
                   ((0, 0, 96 + extension), True),
                   ((4.6, 0, 96 + extension), False)])
    # Cyclic rotation + translation, mapping (x,y,z) to (100+z,30+x,20+y).
    placement = App.Placement(App.Vector(100, 30, 20),
                              App.Rotation(App.Vector(1, 1, 1), 120))
    placed = shape.copy()
    placed.Placement = placement
    assert placed.isValid() and len(placed.Solids) == 1
    assert abs(placed.Volume - shape.Volume) < 1e-6
    for point, occupied in probes:
        assert shape.isInside(App.Vector(*point), 1e-7, True) == occupied, point
        x, y, z = point
        assert placed.isInside(App.Vector(100+z, 30+x, 20+y), 1e-7, True) == occupied, point
    print('L12-NOMINAL ' + json.dumps({
        'extension_mm': extension, 'bore_centres_z_mm': centres,
        'volume_mm3': round(shape.Volume, 6), 'solids': len(shape.Solids),
        'canonical_and_placed_probes': 2 * len(probes),
        'bounds_mm': [round(v, 6) for v in (
            shape.BoundBox.XMin, shape.BoundBox.XMax,
            shape.BoundBox.YMin, shape.BoundBox.YMax,
            shape.BoundBox.ZMin, shape.BoundBox.ZMax)]}))
print('L12-NOMINAL-OK')
