# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Draw the collision geometry a dynamics model actually simulates (cadex ADR-091).

A collision shape is not the solid it stands for. It is placed in the
*component* frame, it may legitimately sit outside the part -- a rounded foot
protrudes below a shin on purpose -- and until now **nothing drew it**. Two
bugs in one small model came out of that:

- the floor's collision box sat 20 mm proud of the floor's visible top, and a
  hopper stood on the invisible shelf for an entire training run (ADR-087);
- the foot was a 25 mm sphere at the end of a shin that had no foot on it, so
  the drawn leg ended 25 mm above the ground with nothing between (ADR-090).

Both were found by arithmetic, after the fact. This module makes them
visible: an edge-only wire cage per collision shape, named exactly what
MuJoCo calls the geom, sitting exactly where the solver puts it.

**No engine change and no protocol change.** Everything drawn here is already
published; see :func:`records_from_evidence` for the two readers.

The pure half -- everything above ``-- the bpy half --`` -- imports no
``bpy``. The ``size_m`` conversion table lives there exactly once and is
unit-testable without Blender, which matters because that table is the part
most likely to be got wrong (see :func:`extents_mm`).

A sibling of ``cadex_hydrate`` rather than part of it, exactly as
``cadex_animate`` is: a malformed collision record must never cost you the
geometry.

Two placement facts this depends on, both from ``CadexDynamics``:

- **The MuJoCo body frame IS the component frame** (``build_model``'s
  docstring, and the mass offset rides in ``body.ipos`` precisely so). So a
  geom's ``pos_m``/``quat_wxyz`` are component-local, and parenting the wire
  to the hydrated component instance with an identity
  ``matrix_parent_inverse`` puts it where the solver has it -- and keeps it
  there through the simulation bake, the preview path and the solved
  placement, for free.
- **Placements are rigid**, so the parent carries no scale for the child to
  inherit wrongly.
"""

import json
import math

#: Collection name. A **sibling** of "Model" at the scene root, not a child
#: of it, and this is load-bearing: ``cadex_hydrate._cadex_objects`` walks
#: ``collection.all_objects``, which recurses into child collections, and its
#: contract-driven GC removes every tagged object it finds that is not in
#: this pass's ``keep`` set. A child collection would be swept on the next
#: rebuild. A sibling is never looked at.
COLLECTION_NAME = "Collision"

#: On a wire object: the component output whose collision shape it draws.
#: Deliberately **not** ``cadex_hydrate.OUTPUT_PROP`` -- that property is what
#: the hydrate GC hunts for, so tagging with it would undo the isolation the
#: sibling collection buys. Two independent axes, both pointing the same way.
OF_PROP = "cadex_collision_of"
#: The MuJoCo geom name, so the outliner and ``initial_contacts`` agree.
GEOM_PROP = "cadex_collision_geom"
KIND_PROP = "cadex_collision_kind"

#: On the scene while the overlay is on: ``{shapes, components, contacts,
#: penetrating, revision}``. The panel polls on its presence, the same way
#: ``cadex_animate.SCENE_FLAG`` gates the Simulation panel.
SCENE_FLAG = "cadex_collision"

#: On the scene: the accepted revision the cached record was read at, so
#: path B costs one round trip per revision rather than one per redraw.
CACHE_PROP = "cadex_collision_cache"

TRACE_SCHEMA = "cadex-assembly-simulation-trace-v1"
SIMULATION_KIND = "assembly_simulation_json"

#: Segments per circle in a sphere/cylinder/capsule cage. 32 reads as round
#: at any zoom a 25 mm foot is looked at and costs 32 edges.
SEGMENTS = 32

#: Half-length of the axis cross drawn for a ``mesh``/``hull`` shape, in mm.
#: Fixed rather than derived: the evidence deliberately strips the vertices
#: (``CadexDynamics`` model_evidence: "the geometry itself is thousands of
#: numbers and it is already in the model"), so there is no extent to derive
#: from and inventing one would be a drawing of a guess.
FRAME_CROSS_MM = 30.0


# -- the pure half: no bpy, no scene ----------------------------------------

def extents_mm(kind, size_m):
    """The shape's semantic dimensions in mm, from MuJoCo's ``size`` triple.

    **The part most likely to be got wrong**, so it is written once, here,
    and the gate asserts it against the record's own independently-computed
    ``size_mm`` -- which is a different arithmetic on the engine side, so a
    doubled conversion cannot pass both.

    MuJoCo's conventions, which are not uniform:

    - **box**: ``size`` is HALF-extents. Full extent is ``2·s``.
    - **sphere**: ``[radius]``.
    - **cylinder**: ``[radius, half_length]``. Full length is ``2·s[1]``.
    - **capsule**: ``[radius, half_length OF THE CYLINDRICAL SECTION ONLY]``.
      The two hemispherical caps sit *outside* it, so the total extent along
      the axis is ``2·(half_length + radius)`` -- which is why a capsule is
      the one shape whose drawn length is not ``2·s[1]``.

    Returns the same shape of list the engine's ``size_mm`` carries: full
    extents for a box, ``[radius]`` for a sphere, ``[radius, full_length]``
    for a cylinder or capsule.
    """

    values = [float(value) * 1000.0 for value in (size_m or ())]
    if kind == "box":
        return [value * 2.0 for value in values[:3]]
    if kind == "sphere":
        return [values[0]] if values else [0.0]
    if kind in ("cylinder", "capsule"):
        return [values[0], values[1] * 2.0] if len(values) > 1 else [0.0, 0.0]
    return []


def _circle(radius, axis, offset=0.0, segments=SEGMENTS):
    """One closed ring of ``segments`` points about ``axis`` (0=x, 1=y, 2=z)."""

    points = []
    for step in range(segments):
        angle = 2.0 * math.pi * step / segments
        first, second = radius * math.cos(angle), radius * math.sin(angle)
        if axis == 2:
            points.append((first, second, offset))
        elif axis == 1:
            points.append((first, offset, second))
        else:
            points.append((offset, first, second))
    return points


def _ring_edges(start, count):
    return [(start + index, start + (index + 1) % count) for index in range(count)]


def _arc_zx(radius, start_angle, end_angle, offset_z, segments=SEGMENTS // 4):
    """A meridian arc in the x-z plane, for a capsule's caps."""

    points = []
    for step in range(segments + 1):
        angle = start_angle + (end_angle - start_angle) * step / segments
        points.append((radius * math.cos(angle), 0.0,
                       offset_z + radius * math.sin(angle)))
    return points


def wireframe(kind, size_m):
    """``(vertices_mm, edges)`` for one shape, in its own local frame.

    Edge-only by construction: no polygon is ever built, which is what keeps
    the overlay out of ``scene.ray_cast`` and unable to occlude the surface
    it exists to be compared against.
    """

    vertices, edges = [], []
    values = [float(value) * 1000.0 for value in (size_m or ())]

    if kind == "box" and len(values) >= 3:
        x, y, z = values[0], values[1], values[2]      # already half-extents
        vertices = [(sx * x, sy * y, sz * z)
                    for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)]
        # 0..3 bottom (z-), 4..7 top (z+), each quad ordered x-fastest.
        edges = [(0, 1), (1, 3), (3, 2), (2, 0),
                 (4, 5), (5, 7), (7, 6), (6, 4),
                 (0, 4), (1, 5), (2, 6), (3, 7)]

    elif kind == "sphere" and values:
        radius = values[0]
        for axis in (0, 1, 2):                          # three great circles
            start = len(vertices)
            vertices.extend(_circle(radius, axis))
            edges.extend(_ring_edges(start, SEGMENTS))

    elif kind in ("cylinder", "capsule") and len(values) >= 2:
        radius, half = values[0], values[1]
        low = len(vertices)
        vertices.extend(_circle(radius, 2, -half))
        edges.extend(_ring_edges(low, SEGMENTS))
        high = len(vertices)
        vertices.extend(_circle(radius, 2, half))
        edges.extend(_ring_edges(high, SEGMENTS))
        for quarter in range(4):                        # four verticals
            index = quarter * SEGMENTS // 4
            edges.append((low + index, high + index))
        if kind == "capsule":
            # The caps, drawn: a capsule's total extent is 2*(half+radius),
            # and a cage that stopped at the cylinder would understate the
            # shape by a full diameter.
            for sign, lo, hi in ((1, 0.0, math.pi / 2.0),
                                 (-1, 0.0, -math.pi / 2.0)):
                for turn in (0.0, math.pi / 2.0):
                    start = len(vertices)
                    arc = _arc_zx(radius, lo, hi, sign * half)
                    for px, _py, pz in arc:
                        vertices.append((px * math.cos(turn),
                                         px * math.sin(turn), pz))
                    edges.extend((start + i, start + i + 1)
                                 for i in range(len(arc) - 1))

    else:
        # mesh / hull, and anything a future engine adds. The evidence
        # deliberately strips `vertices_m` and `triangles`, so there is
        # nothing to draw and no extent to infer. A frame cross says "a
        # collision shape is here, and it is not a primitive" without
        # claiming a size.
        #
        # Never the component's own display mesh: for a `hull` that shows
        # the WRONG volume -- the hull is what collides and the part is not
        # -- which is the exact class of quiet error this feature exists to
        # end.
        arm = FRAME_CROSS_MM
        vertices = [(-arm, 0, 0), (arm, 0, 0), (0, -arm, 0),
                    (0, arm, 0), (0, 0, -arm), (0, 0, arm)]
        edges = [(0, 1), (2, 3), (4, 5)]

    return vertices, edges


def geom_name(component, index):
    """What MuJoCo calls this geom (``CadexDynamics`` ``_add_geoms``).

    The object is named this so the outliner and an ``initial_contacts``
    line say the same string.
    """

    return "{:s}/collision{:d}".format(str(component), int(index))


def records_from_evidence(evidence):
    """Flatten a ``model_evidence`` dict into one entry per collision shape.

    ``evidence`` is what both readers produce and is *already published*:

    - **path A**, free: a simulation trace artifact carries the whole of
      ``model_evidence`` at ``trace["dynamics"]``, and the shell already
      opens that file to bake the animation.
    - **path B**: ``inspect scope="object"`` on the mjcf publication
      object's ``CadexAssemblyMjcfValidation``, read through the existing
      ``cadex_backend._inspect_full``, which already concatenates
      ``kind == "string"`` pages -- exactly what a ~6 KiB JSON string
      property needs.

    Both are needed. A model that is mjcf-only has no trace; and a
    **rollout's** trace carries only the small evidence dict, not the
    collision block, so a hopper that plays back a policy still needs B.
    """

    records = []
    for entry in (evidence or {}).get("collisions") or ():
        component = str((entry or {}).get("component_output") or "")
        if not component:
            continue
        for shape in (entry or {}).get("shapes") or ():
            kind = str((shape or {}).get("kind") or "")
            index = int((shape or {}).get("index") or 0)
            records.append({
                "component": component,
                "index": index,
                "name": geom_name(component, index),
                "kind": kind,
                "position_mm": [float(value) * 1000.0
                                for value in (shape.get("pos_m") or (0, 0, 0))],
                "quaternion_wxyz": [float(value) for value in
                                    (shape.get("quat_wxyz") or (1, 0, 0, 0))],
                "size_m": [float(value) for value in (shape.get("size_m") or ())],
                "extents_mm": extents_mm(kind, shape.get("size_m") or ()),
                "declared_size_mm": [float(value) for value
                                     in (shape.get("size_mm") or ())],
            })
    return records


def contact_summary(evidence):
    """The one line that would have caught the shipped hopper.

    ADR-087's observable: *what is already touching before anything moves*.
    A model designed to start on its feet reads "touching at t = 0"; a model
    that should start clear and does not is a collision shape in the wrong
    frame, and this is the only thing that says so.
    """

    evidence = evidence or {}
    contacts = list(evidence.get("initial_contacts") or ())
    count = int(evidence.get("initial_contact_count") or 0)
    penetrating = sum(1 for item in contacts if (item or {}).get("penetrating"))
    lines = []
    for item in contacts[:4]:
        geoms = " + ".join(str(name) for name in (item.get("geoms") or ()))
        position = item.get("position_mm") or (0.0, 0.0, 0.0)
        lines.append("{:s} at z = {:.2f} mm{:s}".format(
            geoms, float(position[2]),
            ", INTERPENETRATING" if item.get("penetrating") else ""))
    return {"count": count, "penetrating": penetrating, "lines": lines,
            "omitted": int(evidence.get("initial_contacts_omitted") or 0)}


def dynamics_from_trace(path):
    """``trace["dynamics"]`` from a simulation trace artifact, or ``None``."""

    with open(path, "rb") as handle:
        trace = json.loads(handle.read().decode("utf-8"))
    if trace.get("schema") != TRACE_SCHEMA:
        raise ValueError("{:s} is not a {:s} trace".format(str(path),
                                                           TRACE_SCHEMA))
    dynamics = trace.get("dynamics")
    return dynamics if isinstance(dynamics, dict) else None


def trace_entries(display_map):
    """Simulation artifact paths in an accepted response's display block."""

    return sorted(
        str(entry["artifact_path"])
        for entry in (display_map or {}).values()
        if (entry or {}).get("artifact_kind") == SIMULATION_KIND
        and (entry or {}).get("artifact_path")
    )


def mjcf_outputs(display_map):
    """Output names whose artifact is an exported MJCF."""

    return sorted(
        name for name, entry in (display_map or {}).items()
        if str((entry or {}).get("artifact_kind") or "").startswith("assembly_mjcf")
    )


# -- the bpy half -----------------------------------------------------------

def _collection(scene, create=True):
    """The Collision collection, a sibling of Model at the scene root."""

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
    """Remove every overlay object and forget the panel flag.

    The entire cleanup story, which is the point of the sibling collection:
    nothing else in the add-on has to know this exists, and the hydrate GC
    never sees it.
    """

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


def _mesh_for(record):
    import bpy
    vertices, edges = wireframe(record["kind"], record["size_m"])
    mesh = bpy.data.meshes.new(record["name"])
    mesh.vertices.add(len(vertices))
    mesh.vertices.foreach_set(
        "co", [axis for vertex in vertices for axis in vertex])
    mesh.edges.add(len(edges))
    mesh.edges.foreach_set(
        "vertices", [index for edge in edges for index in edge])
    mesh.update()
    return mesh


def _component_objects():
    """Hydrated component instances by output name (not their wire children)."""

    from . import cadex_hydrate
    collection = cadex_hydrate._model_collection()
    found = {}
    for obj in cadex_hydrate._cadex_objects(collection):
        name = str(obj.get(cadex_hydrate.OUTPUT_PROP) or "")
        if name and not obj.name.endswith(cadex_hydrate.EDGE_SUFFIX):
            found[name] = obj
    return found


def draw(records, evidence=None, revision=""):
    """Build the overlay from flattened records. Returns a report dict."""

    import bpy
    from mathutils import Matrix, Quaternion

    scene = bpy.context.scene
    clear(scene)
    if not records:
        return {"shown": False, "shapes": 0}

    collection = _collection(scene)
    components = _component_objects()
    drawn, orphans = [], []
    for record in records:
        parent = components.get(record["component"])
        if parent is None:
            # The component is not hydrated this pass -- draft quality, or
            # it left the contract. Skipped rather than drawn at the origin,
            # which would be a wire cage in the wrong place, and a wire cage
            # in the wrong place is the bug this module exists to show.
            orphans.append(record["name"])
            continue
        obj = bpy.data.objects.new(record["name"], _mesh_for(record))
        collection.objects.link(obj)
        obj[OF_PROP] = record["component"]
        obj[GEOM_PROP] = record["name"]
        obj[KIND_PROP] = record["kind"]
        # Wire, unselectable and unrenderable: an overlay, not a part.
        obj.display_type = 'WIRE'
        obj.hide_select = True
        obj.hide_render = True
        obj.show_in_front = True
        obj.parent = parent
        obj.matrix_parent_inverse.identity()
        obj.matrix_basis = (
            Matrix.Translation(record["position_mm"])
            @ Quaternion(record["quaternion_wxyz"]).to_matrix().to_4x4()
        )
        drawn.append(obj.name)

    summary = contact_summary(evidence)
    scene[SCENE_FLAG] = {
        "shapes": len(drawn),
        "components": len({record["component"] for record in records}),
        "contacts": summary["count"],
        "penetrating": summary["penetrating"],
        "contact_lines": summary["lines"],
        "contacts_omitted": summary["omitted"],
        "skipped": orphans,
        "revision": str(revision),
    }
    return {"shown": True, "shapes": len(drawn), "skipped": orphans,
            "contacts": summary["count"]}


def enabled(scene=None):
    import bpy
    scene = scene or bpy.context.scene
    return SCENE_FLAG in scene


def read_evidence(payload, root=None):
    """The collision record for the accepted revision, by whichever path works.

    Path A first because it costs nothing -- the trace is a file already on
    disk that the bake is about to read anyway. Path B when there is no
    trace, or when the trace is a rollout's (which carries only the small
    evidence dict and no ``collisions`` block).
    """

    display_map = payload.get("display") or {}
    for path in trace_entries(display_map):
        try:
            dynamics = dynamics_from_trace(path)
        except Exception:
            continue
        if dynamics and dynamics.get("collisions"):
            return dynamics, "trace"

    if not mjcf_outputs(display_map):
        return None, "none"
    try:
        from . import cadex_backend
        evidence = cadex_backend.mjcf_validation_evidence(root)
    except Exception:
        return None, "none"
    return (evidence, "inspect") if evidence else (None, "none")


def apply(payload, root=None):
    """Refresh the overlay for one accepted response, if it is on.

    Never raises for the ordinary cases. A model with no dynamics is not an
    error -- it is most models.
    """

    import bpy
    scene = bpy.context.scene
    if not enabled(scene):
        return {"shown": False, "reason": "off"}
    evidence, source = read_evidence(payload, root)
    if not evidence:
        clear(scene)
        return {"shown": False, "reason": "no dynamics output"}
    report = draw(records_from_evidence(evidence), evidence,
                  payload.get("revision") or "")
    report["source"] = source
    return report


def toggle(on=None, root=None):
    """Turn the overlay on or off. Returns the resulting report."""

    import bpy
    from . import cadex_backend

    scene = bpy.context.scene
    want = (not enabled(scene)) if on is None else bool(on)
    if not want:
        cleared = clear(scene)
        return {"shown": False, "cleared": cleared}

    payload = cadex_backend.last_accepted(root)
    if not payload:
        return {"shown": False,
                "message": ("There is no accepted model to draw collision "
                            "shapes for yet. Rebuild first.")}
    evidence, source = read_evidence(payload, root)
    if not evidence:
        return {"shown": False,
                "message": ("This model declares no dynamics, so it has no "
                            "collision geometry. Add assembly.mjcf(...) with "
                            "collision= on the bodies that should touch.")}
    # `draw` writes SCENE_FLAG, which is what `enabled` reads.
    report = draw(records_from_evidence(evidence), evidence,
                  payload.get("revision") or "")
    report["source"] = source
    return report
