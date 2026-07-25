# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
``mesh_cad``: solid-modelling helpers for Part Design mode, importable inside
model scripts (an alias is installed in sys.modules when the add-on
registers, next to ``mesh_model``).

Conventions:
- All lengths are millimeters (Part Design mode: 1 Blender unit = 1 mm).
- Constructors build the mesh in local coordinates, link the new object into
  the active collection (the Model collection during a rebuild) and return it.
  Solids sit on z=0 and extend +Z; gears and cylinders are centered on Z.
- Everything is manifold by construction or cleaned up immediately: booleans
  and bevels use applied modifiers (via the depsgraph, so behavior is
  identical in the GUI and ``--background``), never live ones, and consumed
  boolean operands are explicitly deleted — object *and* mesh — because the
  rebuild's ``orphans_purge`` must not be relied on for cutters created
  mid-script.
- The involute gear is built directly in bmesh with no booleans, so rebuilds
  driven by a slider stay fast.
"""

import math

MERGE_DISTANCE = 0.001
# How far boolean cutters protrude past the faces they cut, so no cut is ever
# coplanar with a face (exact-solver failure mode).
CUTTER_OVERSHOOT = 0.5


# -- internals ---------------------------------------------------------------

def _new_object(name, bm):
    """Bake a bmesh into a new object linked to the active collection."""
    import bpy
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    collection = getattr(bpy.context, "collection", None)
    if collection is None:
        collection = bpy.context.scene.collection
    collection.objects.link(obj)
    return obj


def _delete(obj):
    import bpy
    mesh = obj.data if obj.type == 'MESH' else None
    bpy.data.objects.remove(obj)
    if mesh is not None and mesh.users == 0:
        bpy.data.meshes.remove(mesh)


def _cleanup_bm(bm):
    import bmesh
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=MERGE_DISTANCE)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=MERGE_DISTANCE)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


def _apply_modifiers(obj):
    """Apply the object's modifier stack destructively via the depsgraph
    (works identically in GUI and --background, unlike the operator)."""
    import bpy
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
    old = obj.data
    obj.data = mesh
    obj.modifiers.clear()
    if old.users == 0:
        bpy.data.meshes.remove(old)


def _dedupe_outline(points):
    """Drop consecutive (and wraparound) duplicate outline points."""
    def same(a, b):
        return abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6

    out = []
    for point in points:
        if out and same(point, out[-1]):
            continue
        out.append(point)
    while len(out) > 1 and same(out[0], out[-1]):
        out.pop()
    return out


def _prism(name, outline, z0, z1):
    """Solid extrusion of a ccw 2D outline from z0 to z1 (capped n-gons)."""
    import bmesh
    bm = bmesh.new()
    bottom = [bm.verts.new((px, py, z0)) for px, py in outline]
    top = [bm.verts.new((px, py, z1)) for px, py in outline]
    count = len(outline)
    for i in range(count):
        j = (i + 1) % count
        bm.faces.new((bottom[i], bottom[j], top[j], top[i]))
    bm.faces.new(tuple(reversed(bottom)))
    bm.faces.new(tuple(top))
    _cleanup_bm(bm)
    return _new_object(name, bm)


def _circle_outline(radius, segments, center=(0.0, 0.0)):
    return [(center[0] + radius * math.cos(2 * math.pi * i / segments),
             center[1] + radius * math.sin(2 * math.pi * i / segments))
            for i in range(segments)]


def _rounded_rect_outline(x, y, radius, center, arc_segments=8):
    """Counterclockwise rounded-rectangle outline centered at ``center``."""
    hx, hy = x / 2.0, y / 2.0
    cx, cy = center
    radius = max(0.0, min(radius, hx - 1e-4, hy - 1e-4))
    if radius <= 0.0:
        return [(cx - hx, cy - hy), (cx + hx, cy - hy),
                (cx + hx, cy + hy), (cx - hx, cy + hy)]
    corners = (
        ((cx + hx - radius, cy - hy + radius), -90.0),
        ((cx + hx - radius, cy + hy - radius), 0.0),
        ((cx - hx + radius, cy + hy - radius), 90.0),
        ((cx - hx + radius, cy - hy + radius), 180.0),
    )
    points = []
    for (ccx, ccy), start in corners:
        for i in range(arc_segments + 1):
            angle = math.radians(start + 90.0 * i / arc_segments)
            points.append((ccx + radius * math.cos(angle),
                           ccy + radius * math.sin(angle)))
    return _dedupe_outline(points)


def _bevel(obj, width, segments, angle_limit):
    if width <= 0.0:
        return obj
    mod = obj.modifiers.new(name="mesh_cad_bevel", type='BEVEL')
    mod.width = width
    mod.segments = segments
    mod.limit_method = 'ANGLE'
    mod.angle_limit = math.radians(angle_limit)
    _apply_modifiers(obj)
    return finalize(obj)


def _boolean(obj, operation, others):
    if not others:
        raise ValueError("boolean needs at least one operand object")
    for other in others:
        mod = obj.modifiers.new(name="mesh_cad_boolean", type='BOOLEAN')
        mod.operation = operation
        mod.solver = 'EXACT'
        mod.object = other
        _apply_modifiers(obj)
        _delete(other)
    return finalize(obj)


# -- public API --------------------------------------------------------------

def finalize(obj):
    """Weld near-duplicate vertices, dissolve degenerate faces and point the
    normals outward. Call after any manual vertex-level work; the mesh_cad
    booleans and bevels already do it."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    _cleanup_bm(bm)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


def plate(name, x, y, thickness, corner_radius=0, center=(0, 0)):
    """Rectangular plate on z=0, extruded up by ``thickness``, optionally
    with rounded corners, centered at ``center`` in XY."""
    outline = _rounded_rect_outline(float(x), float(y), float(corner_radius),
                                    (float(center[0]), float(center[1])))
    return _prism(name, outline, 0.0, float(thickness))


def rounded_box(name, x, y, z, radius=2):
    """Box on z=0 with all edges filleted by ``radius``."""
    obj = plate(name, x, y, z)
    radius = min(float(radius), x / 2.0 - 1e-3, y / 2.0 - 1e-3,
                 z / 2.0 - 1e-3)
    if radius > 0.0:
        _bevel(obj, radius, 4, 30.0)
    return obj


def cylinder(name, d, h, at=(0, 0, 0), segments=64):
    """Solid cylinder of diameter ``d``; ``at`` is the center of its base,
    the body extends +Z by ``h``."""
    outline = _circle_outline(float(d) / 2.0, int(segments),
                              (float(at[0]), float(at[1])))
    return _prism(name, outline, float(at[2]), float(at[2]) + float(h))


def gear_center_distance(module, teeth1, teeth2):
    """Exact center distance for two meshing spur gears of the same module."""
    return float(module) * (int(teeth1) + int(teeth2)) / 2.0


def spur_gear(name, module, teeth, thickness, bore=0, pressure_angle=20,
              backlash=0.1, hub_d=0, hub_h=0):
    """Involute spur gear, boolean-free and manifold by construction.

    Centered on the Z axis, body from z=0 to ``thickness``; outside diameter
    is ``module * (teeth + 2)``. ``bore`` (diameter) cuts a through hole in
    the caps; ``hub_d``/``hub_h`` add a cylindrical hub boss on top. Backlash
    thins each tooth by ``backlash`` mm along the pitch circle.
    """
    import bmesh

    module = float(module)
    teeth = int(teeth)
    thickness = float(thickness)
    if teeth < 4:
        raise ValueError("spur_gear: needs at least 4 teeth")
    if module <= 0 or thickness <= 0:
        raise ValueError("spur_gear: module and thickness must be positive")

    pa = math.radians(float(pressure_angle))
    r_pitch = module * teeth / 2.0
    r_base = r_pitch * math.cos(pa)
    r_tip = r_pitch + module
    r_root = max(r_pitch - 1.25 * module, 0.2 * r_pitch)
    r_bore = float(bore) / 2.0
    if r_bore >= r_root - 0.5:
        raise ValueError("spur_gear: bore too large for the root circle")

    # Involute geometry: half tooth thickness (angle) at the pitch circle,
    # thinned by backlash, plus the involute rollback between radii.
    inv_pa = math.tan(pa) - pa
    half_tooth = math.pi / (2 * teeth) - float(backlash) / (2.0 * r_pitch)

    def flank_angle(radius):
        """Polar offset of the involute flank from the tooth center line."""
        t = math.sqrt(max((radius / r_base) ** 2 - 1.0, 0.0))
        return half_tooth + inv_pa - (t - math.atan(t))

    r_start = max(r_root, r_base)
    base_angle = flank_angle(r_start)
    tip_angle = flank_angle(r_tip)
    gap_angle = math.pi / teeth
    if tip_angle <= 0.0 or base_angle >= gap_angle:
        raise ValueError("spur_gear: degenerate tooth shape "
                         "(adjust teeth/module/pressure_angle/backlash)")

    flank_samples, tip_samples, root_samples = 6, 3, 3

    # One tooth outline as (radius, angle) pairs on [-gap_angle, gap_angle],
    # counterclockwise; duplicates are removed after rotation.
    profile = []
    for i in range(root_samples + 1):  # leading root arc
        angle = -gap_angle + (gap_angle - base_angle) * i / root_samples
        profile.append((r_root, angle))
    for i in range(flank_samples + 1):  # rising involute flank
        radius = r_start + (r_tip - r_start) * i / flank_samples
        profile.append((radius, -flank_angle(radius)))
    for i in range(1, tip_samples):  # tip arc (interior points)
        angle = -tip_angle + 2.0 * tip_angle * i / tip_samples
        profile.append((r_tip, angle))
    for i in range(flank_samples + 1):  # falling involute flank
        radius = r_tip - (r_tip - r_start) * i / flank_samples
        profile.append((radius, flank_angle(radius)))
    for i in range(root_samples + 1):  # trailing root arc
        angle = base_angle + (gap_angle - base_angle) * i / root_samples
        profile.append((r_root, angle))

    pitch = 2.0 * math.pi / teeth
    outline = []  # (x, y, polar angle), ccw, monotonic angle
    for tooth in range(teeth):
        rotation = tooth * pitch
        for radius, angle in profile:
            total = angle + rotation
            outline.append((radius * math.cos(total),
                            radius * math.sin(total), total))
    outline = _dedupe_outline(outline)
    count = len(outline)

    has_hub = float(hub_d) > 0.0 and float(hub_h) > 0.0
    hub_r = min(float(hub_d) / 2.0, r_root - 0.1) if has_hub else 0.0
    if has_hub and hub_r <= r_bore + 0.05:
        raise ValueError("spur_gear: hub_d must exceed the bore")
    top_z = thickness + (float(hub_h) if has_hub else 0.0)

    bm = bmesh.new()

    def ring(radius, z):
        # Circle ring with one vert per outline point, at matching polar
        # angles: radial cap quads between rings can then never cross.
        # Same-angle outline points yield coincident verts here; the final
        # weld collapses the resulting degenerate quads.
        return [bm.verts.new((radius * math.cos(angle),
                              radius * math.sin(angle), z))
                for _x, _y, angle in outline]

    def quad_ring(inner, outer):
        for i in range(count):
            j = (i + 1) % count
            bm.faces.new((inner[i], inner[j], outer[j], outer[i]))

    def fan_cap(ringverts, z):
        center = bm.verts.new((0.0, 0.0, z))
        for i in range(count):
            j = (i + 1) % count
            bm.faces.new((ringverts[i], ringverts[j], center))

    outline_bottom = [bm.verts.new((x, y, 0.0)) for x, y, _a in outline]
    outline_top = [bm.verts.new((x, y, thickness)) for x, y, _a in outline]
    quad_ring(outline_bottom, outline_top)  # gear side wall

    bore_bottom = ring(r_bore, 0.0) if r_bore > 0.0 else None
    bore_top = ring(r_bore, top_z) if r_bore > 0.0 else None
    if r_bore > 0.0:
        quad_ring(bore_bottom, bore_top)  # bore wall, full height
        quad_ring(bore_bottom, outline_bottom)  # bottom annular cap
    else:
        fan_cap(outline_bottom, 0.0)

    if has_hub:
        hub_lower = ring(hub_r, thickness)
        hub_upper = ring(hub_r, top_z)
        quad_ring(outline_top, hub_lower)  # shoulder around the hub
        quad_ring(hub_lower, hub_upper)  # hub wall
        top_ring = hub_upper
    else:
        top_ring = outline_top

    if r_bore > 0.0:
        quad_ring(top_ring, bore_top)  # top annular cap
    else:
        fan_cap(top_ring, top_z)

    _cleanup_bm(bm)
    return _new_object(name, bm)


def hole(obj, d, at=(0, 0), depth=None, cbore_d=0, cbore_depth=0,
         csink_d=0, csink_angle=90, segments=32):
    """Drill a hole into ``obj`` from its top (+Z) face, straight down.

    ``at`` and ``depth`` are in the object's local frame: ``at`` is the XY
    position of the hole axis, ``depth`` is measured from the top face
    (None = through hole). ``cbore_d``/``cbore_depth`` add a counterbore,
    ``csink_d``/``csink_angle`` a countersink. Cutters are oversized past the
    faces they cut, so cuts are never coplanar with a face.
    """
    from mathutils import Matrix

    mesh = obj.data
    if obj.type != 'MESH' or not mesh.vertices:
        raise ValueError("hole(): object has no mesh geometry")
    d = float(d)
    if d <= 0.0:
        raise ValueError("hole(): diameter must be positive")

    zs = [vert.co.z for vert in mesh.vertices]
    z_top, z_bottom = max(zs), min(zs)
    over = CUTTER_OVERSHOOT
    z_end = (z_bottom - over) if depth is None else (z_top - float(depth))

    import bmesh

    def frustum(r_low, z_low, r_high, z_high):
        bm = bmesh.new()
        low = [bm.verts.new((r_low * math.cos(2 * math.pi * i / segments),
                             r_low * math.sin(2 * math.pi * i / segments),
                             z_low))
               for i in range(segments)]
        high = [bm.verts.new((r_high * math.cos(2 * math.pi * i / segments),
                              r_high * math.sin(2 * math.pi * i / segments),
                              z_high))
                for i in range(segments)]
        for i in range(segments):
            j = (i + 1) % segments
            bm.faces.new((low[i], low[j], high[j], high[i]))
        bm.faces.new(tuple(reversed(low)))
        bm.faces.new(tuple(high))
        _cleanup_bm(bm)
        return _new_object("_mesh_cad_cutter", bm)

    cutters = [frustum(d / 2.0, z_end, d / 2.0, z_top + over)]
    if float(cbore_d) > 0.0 and float(cbore_depth) > 0.0:
        cutters.append(frustum(float(cbore_d) / 2.0,
                               z_top - float(cbore_depth),
                               float(cbore_d) / 2.0, z_top + over))
    if float(csink_d) > d:
        half = math.radians(float(csink_angle)) / 2.0
        cs_depth = (float(csink_d) - d) / 2.0 / math.tan(half)
        cutters.append(frustum(d / 2.0, z_top - cs_depth,
                               float(csink_d) / 2.0 + over * math.tan(half),
                               z_top + over))

    axis = obj.matrix_world @ Matrix.Translation(
        (float(at[0]), float(at[1]), 0.0))
    for cutter in cutters:
        cutter.matrix_world = axis
    return difference(obj, *cutters)


def union(obj, *others):
    """Boolean-union ``others`` into ``obj`` (exact solver, applied
    immediately, then welded); the consumed operands are deleted."""
    return _boolean(obj, 'UNION', others)


def difference(obj, *cutters):
    """Boolean-subtract ``cutters`` from ``obj``; the cutters are deleted."""
    return _boolean(obj, 'DIFFERENCE', cutters)


def intersect(obj, *others):
    """Boolean-intersect ``obj`` with ``others``; the operands are deleted."""
    return _boolean(obj, 'INTERSECT', others)


def chamfer(obj, width=0.5, angle_limit=30):
    """Flat 45° bevel on every edge sharper than ``angle_limit`` degrees."""
    return _bevel(obj, float(width), 1, float(angle_limit))


def fillet(obj, radius=1, segments=4):
    """Rounded bevel on every edge sharper than 30 degrees."""
    return _bevel(obj, float(radius), int(segments), 30.0)
