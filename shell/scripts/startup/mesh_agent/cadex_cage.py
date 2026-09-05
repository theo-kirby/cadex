# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Draw a declared section cage, and let the user drag its rings (ADR-127).

The engine holds a cage as a table of rings — position along an axis, a
half-width, a half-height, a roll and a superellipse exponent
(`CadexCage.py`). This module draws that table as an edge-only overlay, lets
the user move and scale a ring like any other object, and reads the result
back into rows when **Apply** is pressed.

Three inherited decisions, none of them re-litigated here:

- **A sibling collection, never a child of Model.** ``cadex_hydrate``'s
  contract GC walks ``collection.all_objects``, which recurses, and removes
  every tagged object that is not in the pass's keep set. A child collection
  would be swept on the next rebuild. `cadex_collision` says this at length
  and it is exactly as load-bearing here.
- **Never tagged ``cadex_output``.** Same reason: that property is what the
  GC hunts for.
- **Apply, not auto-push.** ADR-122: the wiring editor pushed on every edit,
  the pump held one request, and nineteen of twenty edits were dropped in
  silence. A cage drag is a stream of transform events and would be worse. So
  edits accumulate in the viewport and one button sends the whole table.

The pure half — everything above ``-- the bpy half --`` — imports no ``bpy``.
It is where a dragged transform becomes a row, which is the arithmetic most
likely to be wrong and the half Phase 12 keeps.
"""

import math

#: Collection name: a **sibling** of "Model" at the scene root.
COLLECTION_NAME = "Cage"

#: On a ring object: which cage it belongs to, and which row it is.
CAGE_PROP = "cadex_cage"
INDEX_PROP = "cadex_cage_index"
#: The row as it was drawn, so Apply can tell a dragged ring from a still one
#: and send the exponent back unchanged (nothing in the viewport edits it).
ROW_PROP = "cadex_cage_row"

#: Scene flag: the panel's "is it showing" and the report the tool reads.
SCENE_FLAG = "cadex_cage_overlay"

#: Points per drawn ring. Fewer than the engine's 64 — this is a guide, and
#: a 128-ring cage at 64 points each is 8192 vertices of overlay.
SEGMENTS = 48


# -- the pure half: no bpy --------------------------------------------------


def superellipse(half_width, half_height, exponent, segments=SEGMENTS):
    """One ring's profile in its own plane, as (u, v) pairs.

    The engine's ``CadexCage.ring_points`` parametrisation, deliberately: an
    overlay that drew a different curve from the one the loft uses would be
    worse than no overlay.
    """

    power = 2.0 / float(exponent or 2.0)
    points = []
    for index in range(int(segments)):
        angle = 2.0 * math.pi * index / float(segments)
        cosine, sine = math.cos(angle), math.sin(angle)
        u = float(half_width) * _signed_power(cosine, power)
        v = float(half_height) * _signed_power(sine, power)
        points.append((u, v))
    return points


def _signed_power(value, power):
    magnitude = abs(value) ** power
    return magnitude if value >= 0.0 else -magnitude


def ring_edges(count):
    """The closed loop's edge list."""

    return [(index, (index + 1) % count) for index in range(count)]


def frame_axes(axis, up):
    """(along, across, third) — the cage's orthonormal frame.

    ``along`` is the spine, ``across`` carries a ring's *height* and
    ``third`` its *width*, which is the same assignment ``ring_points``
    makes. Getting this wrong would swap width for height on every ring in a
    cage that does not run along +X.
    """

    along = _normalized(axis)
    across = _normalized(_reject(up, along))
    third = _cross(along, across)
    return along, across, third


def row_from_placement(row, offset_along, scale_u, scale_v):
    """One drawn ring plus what the user did to it, as a canonical row.

    ``offset_along`` is how far the ring moved down the spine, in
    millimetres; ``scale_u``/``scale_v`` are what its width and height were
    multiplied by. The exponent and the roll come back unchanged — neither is
    a transform, and inventing one from a rotation the user may have made by
    accident is exactly the sort of quiet reinterpretation this table exists
    to avoid.
    """

    return {
        "cage": str(row.get("cage") or ""),
        "position": round(float(row.get("position") or 0.0) + float(offset_along), 5),
        "half_width": round(max(float(row.get("half_width") or 0.0) * float(scale_u),
                                1.0e-4), 5),
        "half_height": round(max(float(row.get("half_height") or 0.0) * float(scale_v),
                                 1.0e-4), 5),
        "roll": round(float(row.get("roll") or 0.0), 5),
        "exponent": round(float(row.get("exponent") or 2.0), 5),
    }


def sorted_rows(rows):
    """Rows grouped by cage and ordered along each spine.

    A dragged ring can overtake its neighbour, and the engine refuses a table
    whose positions do not increase. Sorting here is not hiding that: the
    ring *is* where the user put it, and its place in the order is a
    consequence rather than a second fact.
    """

    ordered = []
    for cage in sorted({str(row.get("cage") or "") for row in rows}):
        ordered.extend(sorted(
            (dict(row) for row in rows if str(row.get("cage") or "") == cage),
            key=lambda row: float(row.get("position") or 0.0),
        ))
    return ordered


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return sum(float(x) * float(y) for x, y in zip(a, b))


def _normalized(vector):
    length = math.sqrt(_dot(vector, vector))
    if length <= 1.0e-12:
        return (0.0, 0.0, 1.0)
    return tuple(float(item) / length for item in vector)


def _reject(vector, axis):
    along = _dot(vector, axis)
    rejected = tuple(float(v) - along * float(a) for v, a in zip(vector, axis))
    if math.sqrt(_dot(rejected, rejected)) <= 1.0e-9:
        return (0.0, 1.0, 0.0) if abs(axis[2]) > 0.9 else (0.0, 0.0, 1.0)
    return rejected


# -- the bpy half -----------------------------------------------------------


def _collection(scene, create=True):
    import bpy
    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is None:
        if not create:
            return None
        collection = bpy.data.collections.new(COLLECTION_NAME)
    if collection.name not in scene.collection.children:
        if not create:
            return collection
        scene.collection.children.link(collection)
    return collection


def clear(scene=None):
    """Remove every ring object and forget the flag."""

    import bpy
    scene = scene or bpy.context.scene
    collection = _collection(scene, create=False)
    removed = 0
    if collection is not None:
        for obj in list(collection.objects):
            mesh = obj.data
            bpy.data.objects.remove(obj)
            if mesh is not None and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
            removed += 1
    if SCENE_FLAG in scene:
        del scene[SCENE_FLAG]
    return removed


def _mesh_for(name, row):
    import bpy
    points = superellipse(row.get("half_width"), row.get("half_height"),
                          row.get("exponent", 2.0))
    mesh = bpy.data.meshes.new(name)
    mesh.vertices.add(len(points))
    # In the ring's own plane: +X is width, +Y is height, and the object's
    # matrix puts that plane on the spine.
    mesh.vertices.foreach_set(
        "co", [value for u, v in points for value in (u, v, 0.0)])
    edges = ring_edges(len(points))
    mesh.edges.add(len(edges))
    mesh.edges.foreach_set("vertices", [i for edge in edges for i in edge])
    mesh.update()
    return mesh


def _matrix_for(cage, row):
    """Where one ring sits: on the spine, in the cage's frame."""

    from mathutils import Matrix, Vector

    along, across, third = frame_axes(
        cage.get("axis") or [1.0, 0.0, 0.0], cage.get("up") or [0.0, 0.0, 1.0])
    origin = Vector(cage.get("origin") or [0.0, 0.0, 0.0])
    station = origin + Vector(along) * float(row.get("position") or 0.0)
    roll = math.radians(float(row.get("roll") or 0.0))
    width = Vector(third) * math.cos(roll) + Vector(across) * math.sin(roll)
    height = Vector(across) * math.cos(roll) - Vector(third) * math.sin(roll)
    basis = Matrix((
        (width.x, height.x, along[0], station.x),
        (width.y, height.y, along[1], station.y),
        (width.z, height.z, along[2], station.z),
        (0.0, 0.0, 0.0, 1.0),
    ))
    return basis


def draw(cages, rows, scene=None):
    """Build the overlay from the engine's table. Returns a report dict."""

    import bpy

    scene = scene or bpy.context.scene
    clear(scene)
    frames = {str(entry.get("name") or ""): dict(entry) for entry in cages or []}
    if not rows:
        return {"shown": False, "rings": 0}

    collection = _collection(scene)
    drawn = 0
    for index, row in enumerate(rows):
        cage = frames.get(str(row.get("cage") or ""))
        if cage is None:
            continue
        name = "{:s}/ring{:02d}".format(str(row.get("cage") or "cage"), index)
        obj = bpy.data.objects.new(name, _mesh_for(name, row))
        collection.objects.link(obj)
        obj[CAGE_PROP] = str(row.get("cage") or "")
        obj[INDEX_PROP] = index
        obj[ROW_PROP] = {key: row.get(key) for key in
                         ("cage", "position", "half_width", "half_height",
                          "roll", "exponent")}
        obj.display_type = 'WIRE'
        obj.hide_render = True
        obj.show_in_front = True
        obj.matrix_world = _matrix_for(cage, row)
        drawn += 1

    scene[SCENE_FLAG] = {"rings": drawn, "cages": sorted(frames)}
    return {"shown": bool(drawn), "rings": drawn, "cages": sorted(frames)}


def ring_objects(scene=None):
    import bpy
    scene = scene or bpy.context.scene
    collection = _collection(scene, create=False)
    if collection is None:
        return []
    return sorted(
        (obj for obj in collection.objects if CAGE_PROP in obj),
        key=lambda obj: int(obj.get(INDEX_PROP, 0)),
    )


def enabled(scene=None):
    import bpy
    scene = scene or bpy.context.scene
    return SCENE_FLAG in scene


def show(scene=None):
    """Read the table off the engine and draw it. Returns a report dict."""

    import bpy
    from . import cadex_backend

    scene = scene or bpy.context.scene
    cages, rows = cadex_backend.script_cages(scene)
    if cages is None:
        return {"shown": False, "rings": 0,
                "message": "No engine to read a cage table from."}
    if not cages:
        return {"shown": False, "rings": 0,
                "message": ("This script declares no cage(...) table, so there "
                            "are no rings to drag.")}
    return draw(cages, rows, scene)


def toggle(on=None, scene=None):
    import bpy
    scene = scene or bpy.context.scene
    wanted = (not enabled(scene)) if on is None else bool(on)
    if not wanted:
        clear(scene)
        return {"shown": False, "rings": 0}
    return show(scene)


def rows_from_overlay(scene=None):
    """Read the drawn rings back into canonical rows.

    Each ring was drawn on its cage's spine; what the user did to it is the
    difference between where it is now and where it was put. Movement across
    the spine is **dropped** rather than honoured — a cage is a straight
    spine by construction (a curved one is `part.sweep(scale_law=...)`), and
    silently bending it because a ring was dragged sideways would produce a
    shape the script cannot express.
    """

    import bpy
    from mathutils import Vector
    from . import cadex_backend

    scene = scene or bpy.context.scene
    cages, _rows = cadex_backend.script_cages(scene)
    frames = {str(entry.get("name") or ""): dict(entry) for entry in cages or []}
    result = []
    for obj in ring_objects(scene):
        stored = obj.get(ROW_PROP)
        row = dict(stored) if stored else None
        if not row:
            continue
        cage = frames.get(str(row.get("cage") or ""))
        if cage is None:
            continue
        along, across, third = frame_axes(
            cage.get("axis") or [1.0, 0.0, 0.0], cage.get("up") or [0.0, 0.0, 1.0])
        origin = Vector(cage.get("origin") or [0.0, 0.0, 0.0])
        placed = obj.matrix_world
        moved = (placed.translation - origin).dot(Vector(along))
        scale = placed.to_scale()
        result.append(row_from_placement(
            row,
            moved - float(row.get("position") or 0.0),
            abs(scale.x),
            abs(scale.y),
        ))
    return sorted_rows(result)


def apply(scene=None):
    """Send the dragged table to the engine. Returns ``(ok, report)``.

    One button, one request, however many rings were moved — ADR-122's rule,
    and a cage is the case that most needs it: a drag is a stream of
    transform events and pushing on each would drop all but the last.
    """

    import bpy
    from . import cadex_backend

    scene = scene or bpy.context.scene
    rows = rows_from_overlay(scene)
    if not rows:
        return False, "No rings are drawn, so there is nothing to apply."
    ok, report = cadex_backend.begin_set_cages(scene, rows)
    if not ok:
        return False, report
    return True, "Applying {:d} ring(s)…".format(len(rows))
