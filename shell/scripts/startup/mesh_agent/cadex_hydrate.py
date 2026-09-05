# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Hydrate accepted cadexd results into the Model collection (cadex Phase 6).

Every accepted lifecycle response carries a per-output ``display`` block:
the BREP/mesh artifact path plus an opt-in ``cadex-tessellation-v1`` buffer
(f32 vertices, u32 triangles, f32 edge polylines) whose sidecar maps
triangle and polyline spans to the exact 1-based Face/Edge enumeration of
the engine's ``face_details``/``edge_details``. This module turns those
buffers into Blender mesh objects:

- one object per output in the "Model" collection (find-or-create by the
  ``cadex_output`` custom property; contract-driven GC removes objects
  whose output left the accepted contract);
- component instances land in an "Assembly" collection **inside** Model
  (ADR-177), so the outliner separates the placed copies from the solids
  they instance and one click on the collection's eye hides the lot — the
  exploded-view pattern publishes every part twice (the solid and its
  component), and before this the two sets interleaved at the root. A
  *child* of Model, deliberately: every walker here uses
  ``collection.all_objects``, which recurses, so find, GC, posing and
  bounds all see the components exactly as before — the opposite trade
  from ``cadex_collision``'s sibling collection, which exists to be
  *outside* that recursion;
- the BREP face ID map lands in a ``cadex_face`` INT face attribute
  (1-based face index per triangle), so a viewport pick resolves
  polygon → face index → ``resolve_pin`` without further lookups;
- edge polylines land in a wire-display child object with a ``cadex_edge``
  INT edge attribute (1-based edge index per segment).

The scene stays a rebuildable cache: objects here are display mirrors of
engine truth, exactly like the local-exec path treats script output.
"""

import json
import os

import numpy as np

TESSELLATION_SCHEMA = "cadex-tessellation-v1"
FACE_ATTRIBUTE = "cadex_face"
EDGE_ATTRIBUTE = "cadex_edge"
OUTPUT_PROP = "cadex_output"
REVISION_PROP = "cadex_revision"
KIND_PROP = "cadex_kind"
SIDECAR_PROP = "cadex_sidecar"
EDGE_SUFFIX = " Edges"

#: On a component instance: the declared output whose geometry it places
#: (the response's ``source_output``, ADR-049).
SOURCE_PROP = "cadex_source"
#: On a source object we hid because something instances it. A marker, so a
#: later pass can unhide exactly what it hid and never touch an object the
#: user hid themselves.
HIDDEN_SOURCE_PROP = "cadex_hidden_source"
#: ``KIND_PROP`` value for a component instance.
COMPONENT_KIND = "component"

#: The collection component instances are linked into — a **child** of
#: "Model", so ``all_objects`` walkers still see them (see the module
#: docstring). Created when the first component hydrates, removed by the GC
#: when the last one leaves the contract.
COMPONENT_COLLECTION = "Assembly"

#: What the object's current mesh was built from. Not the source artifact's
#: SHA alone: the *same* BREP is tessellated at draft quality during a drag
#: and at standard quality by the settled refine, with the same
#: ``source_sha256`` both times. Keyed on the SHA alone, the refine would
#: look like a no-op and the viewport would keep the coarse mesh for good.
SOURCE_SHA_PROP = "cadex_source_sha"


def _display_key(sidecar):
    """Identity of the *buffers* a sidecar describes, not just its source.

    Source artifact + quality + deflection + whether edges were streamed.
    Two hydrations agreeing on all four describe byte-identical buffers, so
    rebuilding the mesh from them cannot change anything on screen.
    """

    counts = sidecar.get("counts") or {}
    return "{:s}|{:s}|{:.9g}|{:d}".format(
        str(sidecar.get("source_sha256") or ""),
        str(sidecar.get("quality") or ""),
        float(sidecar.get("deflection") or 0.0),
        1 if int(counts.get("edge_vertices") or 0) > 0 else 0,
    )


def read_sidecar(sidecar_path):
    """Just the sidecar JSON -- no binary buffer read."""

    with open(sidecar_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def read_tessellation(sidecar_path):
    """Read one tessellation sidecar + binary buffer into numpy arrays."""
    with open(sidecar_path, "r", encoding="utf-8") as handle:
        sidecar = json.load(handle)
    if sidecar.get("schema") != TESSELLATION_SCHEMA:
        raise ValueError("{:s} is not a {:s} sidecar".format(
            str(sidecar_path), TESSELLATION_SCHEMA))
    binary_path = os.path.join(os.path.dirname(os.path.abspath(sidecar_path)),
                               os.path.basename(str(sidecar["artifact_path"])))
    with open(binary_path, "rb") as handle:
        blob = handle.read()
    layout = sidecar["layout"]

    def _slice(name, dtype):
        section = layout[name]
        start = int(section["offset"])
        stop = start + int(section["bytes"])
        return np.frombuffer(blob[start:stop], dtype=dtype)

    vertices = _slice("vertices", "<f4").reshape(-1, 3)
    triangles = _slice("triangles", "<u4").reshape(-1, 3)
    edge_vertices = _slice("edge_vertices", "<f4").reshape(-1, 3)
    return {
        "vertices": vertices,
        "triangles": triangles,
        "edge_vertices": edge_vertices,
        "face_ranges": [list(map(int, item)) for item in sidecar["face_ranges"]],
        "edge_polylines": [list(map(int, item))
                           for item in sidecar["edge_polylines"]],
        "deflection": float(sidecar.get("deflection") or 0.0),
        "counts": dict(sidecar.get("counts") or {}),
    }


def face_ids_per_triangle(face_ranges, triangle_count):
    """1-based BREP face index for every triangle, from the range map."""
    ids = np.zeros(triangle_count, dtype=np.int32)
    for index, (start, count) in enumerate(face_ranges, start=1):
        ids[start:start + count] = index
    return ids


def _build_mesh(name, vertices, triangles):
    import bpy
    mesh = bpy.data.meshes.new(name)
    mesh.vertices.add(len(vertices))
    mesh.vertices.foreach_set("co", vertices.astype(np.float32).ravel())
    triangle_count = len(triangles)
    mesh.loops.add(triangle_count * 3)
    mesh.loops.foreach_set("vertex_index", triangles.astype(np.int32).ravel())
    mesh.polygons.add(triangle_count)
    mesh.polygons.foreach_set(
        "loop_start", np.arange(0, triangle_count * 3, 3, dtype=np.int32))
    mesh.polygons.foreach_set(
        "loop_total", np.full(triangle_count, 3, dtype=np.int32))
    mesh.update(calc_edges=True)
    return mesh


def _build_edge_mesh(name, tessellation):
    import bpy
    edge_vertices = tessellation["edge_vertices"]
    polylines = tessellation["edge_polylines"]
    segments = []
    segment_ids = []
    for index, (start, count) in enumerate(polylines, start=1):
        for offset in range(count - 1):
            segments.append((start + offset, start + offset + 1))
            segment_ids.append(index)
    if not segments:
        return None
    mesh = bpy.data.meshes.new(name)
    mesh.vertices.add(len(edge_vertices))
    mesh.vertices.foreach_set("co",
                              edge_vertices.astype(np.float32).ravel())
    mesh.edges.add(len(segments))
    mesh.edges.foreach_set(
        "vertices", np.asarray(segments, dtype=np.int32).ravel())
    mesh.update()
    attribute = mesh.attributes.new(EDGE_ATTRIBUTE, 'INT', 'EDGE')
    attribute.data.foreach_set(
        "value", np.asarray(segment_ids, dtype=np.int32))
    return mesh


def _model_collection():
    from . import model
    import bpy
    return model._model_collection(bpy.context.scene)


def _cadex_objects(collection):
    return [obj for obj in collection.all_objects if OUTPUT_PROP in obj]


def _matrix_from_placement(values):
    from mathutils import Matrix
    values = [float(value) for value in values]
    if len(values) != 16:
        return None
    return Matrix((values[0:4], values[4:8], values[8:12], values[12:16]))


def _replace_data(obj, mesh):
    import bpy
    previous = obj.data
    obj.data = mesh
    if previous is not None and previous.users == 0:
        bpy.data.meshes.remove(previous)


def _component_collection(collection, create=True):
    """The "Assembly" child of Model, find-or-create (ADR-177)."""

    import bpy
    child = bpy.data.collections.get(COMPONENT_COLLECTION)
    if child is None:
        if not create:
            return None
        child = bpy.data.collections.new(COMPONENT_COLLECTION)
    if child.name not in collection.children:
        try:
            collection.children.link(child)
        except RuntimeError:
            pass  # already linked through another parent; good enough
    return child


def _link_into(target, obj):
    """Make ``target`` the object's one collection (migrates objects that
    older sessions linked at the Model root)."""

    if any(existing is target for existing in obj.users_collection):
        return
    for existing in obj.users_collection:
        existing.objects.unlink(obj)
    target.objects.link(obj)


def _find(collection, output, *, edges):
    """The one cadex object for ``output``, wire child or not.

    Found by ``OUTPUT_PROP`` rather than by name, because Blender's ``.001``
    dedup means an object's name is not a stable identity.
    """

    return next(
        (candidate for candidate in _cadex_objects(collection)
         if candidate[OUTPUT_PROP] == output
         and candidate.name.endswith(EDGE_SUFFIX) == edges),
        None,
    )


def _hydrate_components(collection, display_map, revision, keep,
                        created, updated):
    """Place component instances of already-hydrated source geometry.

    A component carries a solved ``placement`` and no geometry of its own;
    the shape it places is a *different* declared output, named by
    ``source_output`` (ADR-049). Before that key existed these entries had
    no tessellation, so the first pass skipped them and the GC deleted
    them -- a solved assembly simply never appeared.

    Instances **share the source's mesh datablock**, so forty screws cost
    one mesh. Runs after the geometry pass, which is what guarantees the
    source object exists and already carries this revision's mesh.

    Every instance (and its wire child) is linked into the "Assembly"
    child collection rather than the Model root (ADR-177): the exploded-view
    pattern publishes each part twice, and the copies grouped under one
    toggleable collection is what keeps the outliner readable.

    Returns the set of source output names that got at least one instance.
    """

    import bpy
    instanced = set()
    home = None
    for name in sorted(display_map or {}):
        entry = display_map[name] or {}
        if entry.get("tessellation"):
            continue  # geometry of its own; the first pass owns it
        source_name = str(entry.get("source_output") or "")
        matrix = _matrix_from_placement(entry.get("placement") or [])
        if not source_name or matrix is None:
            continue
        source = _find(collection, source_name, edges=False)
        if source is None or source.data is None:
            continue  # source not displayable this pass (draft, or absent)

        if home is None:
            home = _component_collection(collection)
        obj = _find(collection, name, edges=False)
        if obj is None:
            obj = bpy.data.objects.new(name, source.data)
            home.objects.link(obj)
            created.append(obj.name)
        else:
            _replace_data(obj, source.data)
            _link_into(home, obj)
            updated.append(obj.name)
        obj[OUTPUT_PROP] = name
        obj[REVISION_PROP] = str(revision)
        obj[KIND_PROP] = COMPONENT_KIND
        obj[SOURCE_PROP] = source_name
        obj.matrix_world = matrix
        keep.add(obj.name)
        instanced.add(source_name)

        # The wire child shares the source's edge mesh and is parented, so
        # it follows the component's matrix for free -- exactly as the
        # geometry pass parents its own.
        source_edges = _find(collection, source_name, edges=True)
        if source_edges is None or source_edges.data is None:
            continue
        edge_obj = _find(collection, name, edges=True)
        if edge_obj is None:
            edge_obj = bpy.data.objects.new(name + EDGE_SUFFIX,
                                            source_edges.data)
            home.objects.link(edge_obj)
        else:
            _replace_data(edge_obj, source_edges.data)
            _link_into(home, edge_obj)
        edge_obj[OUTPUT_PROP] = name
        edge_obj[REVISION_PROP] = str(revision)
        edge_obj[KIND_PROP] = "edges"
        edge_obj.display_type = 'WIRE'
        edge_obj.hide_select = True
        edge_obj.parent = obj
        edge_obj.matrix_parent_inverse.identity()
        keep.add(edge_obj.name)
    return instanced


def _hide_instanced_sources(collection, instanced):
    """Hide a source that is drawn through its instances; unhide when not.

    A source is a declared output, so it is hidden and never deleted. The
    marker property is what keeps this from stomping visibility the user
    set: only objects this function hid are ever unhidden by it.
    """

    for obj in _cadex_objects(collection):
        output = str(obj.get(OUTPUT_PROP) or "")
        if str(obj.get(KIND_PROP) or "") == COMPONENT_KIND:
            continue  # a component is never its own source
        if output in instanced:
            obj.hide_viewport = True
            obj[HIDDEN_SOURCE_PROP] = True
        elif obj.get(HIDDEN_SOURCE_PROP):
            obj.hide_viewport = False
            del obj[HIDDEN_SOURCE_PROP]


def apply_placements(placements):
    """Pose already-hydrated component instances. Returns how many moved.

    The preview path's whole viewport update (ADR-055). Deliberately **not**
    a hydration: ``preview_params`` answers with placements rather than a
    ``display`` block, because a pose-only change has no new geometry to
    carry — every mesh datablock in the collection is already the right one
    by definition, which is what "pose-only" means. So this sets
    ``matrix_world`` and stops. No sidecar read, no buffer decode, no mesh
    rebuild, no face attribute rewrite, no GC pass.

    Wire children are parented to their component and follow for free,
    exactly as they do on the accepting path.

    Silently ignores a name with no object: a component whose source was not
    displayable at draft quality has no instance to move, and a preview is
    not the place to complain about it.
    """

    collection = _model_collection()
    moved = 0
    for name in sorted(placements or {}):
        matrix = _matrix_from_placement(placements[name] or [])
        if matrix is None:
            continue
        obj = _find(collection, name, edges=False)
        if obj is None:
            continue
        obj.matrix_world = matrix
        moved += 1
    return moved


def hydrate_display(display_map, revision):
    """Mirror one accepted response's display block into the Model collection.

    ``display_map`` is the response's ``display`` object: output name →
    ``{artifact_kind, artifact_path, placement, tessellation}``, plus
    ``source_output`` on components. Two passes: outputs with a
    tessellation become geometry objects, then components become instances
    of that geometry at their solved placements. Returns a report dict with
    created/updated/removed object names.
    """
    import bpy
    collection = _model_collection()
    created, updated = [], []
    keep = set()
    for name in sorted(display_map or {}):
        entry = display_map[name] or {}
        tessellation_record = entry.get("tessellation")
        if not tessellation_record:
            continue
        sidecar_path = str(tessellation_record.get("sidecar_path") or "")
        key = _display_key(read_sidecar(sidecar_path))
        obj = _find(collection, name, edges=False)

        # The buffers this response describes are the ones already on the
        # object: rebuilding them cannot change a pixel, so don't read the
        # binary, don't build a mesh, don't rewrite the face attribute.
        # Compare the hash, never the path -- every attempt gets its own
        # staging directory, so paths differ on every single request.
        if (obj is not None and obj.data is not None
                and str(obj.get(SOURCE_SHA_PROP) or "") == key):
            obj[REVISION_PROP] = str(revision)
            obj[SIDECAR_PROP] = sidecar_path
            matrix = _matrix_from_placement(entry.get("placement") or [])
            if matrix is not None:
                obj.matrix_world = matrix
            updated.append(obj.name)
            keep.add(obj.name)
            edge_obj = _find(collection, name, edges=True)
            if edge_obj is not None:
                edge_obj[REVISION_PROP] = str(revision)
                keep.add(edge_obj.name)
            continue

        tessellation = read_tessellation(sidecar_path)
        mesh = _build_mesh(name, tessellation["vertices"],
                           tessellation["triangles"])
        attribute = mesh.attributes.new(FACE_ATTRIBUTE, 'INT', 'FACE')
        attribute.data.foreach_set(
            "value", face_ids_per_triangle(tessellation["face_ranges"],
                                           len(tessellation["triangles"])))
        if obj is None:
            obj = bpy.data.objects.new(name, mesh)
            collection.objects.link(obj)
            created.append(obj.name)
        else:
            _replace_data(obj, mesh)
            updated.append(obj.name)
        obj[OUTPUT_PROP] = name
        obj[REVISION_PROP] = str(revision)
        obj[KIND_PROP] = str(entry.get("artifact_kind") or "")
        obj[SIDECAR_PROP] = sidecar_path
        obj[SOURCE_SHA_PROP] = key
        matrix = _matrix_from_placement(entry.get("placement") or [])
        if matrix is not None:
            obj.matrix_world = matrix
        keep.add(obj.name)

        edge_mesh = _build_edge_mesh(name + EDGE_SUFFIX, tessellation)
        edge_obj = _find(collection, name, edges=True)
        if edge_mesh is None:
            pass  # no edge data requested/present; stale child GCed below
        elif edge_obj is None:
            edge_obj = bpy.data.objects.new(name + EDGE_SUFFIX, edge_mesh)
            collection.objects.link(edge_obj)
        else:
            _replace_data(edge_obj, edge_mesh)
        if edge_mesh is not None:
            edge_obj[OUTPUT_PROP] = name
            edge_obj[REVISION_PROP] = str(revision)
            edge_obj[KIND_PROP] = "edges"
            edge_obj.display_type = 'WIRE'
            edge_obj.hide_select = True
            edge_obj.parent = obj
            edge_obj.matrix_parent_inverse.identity()
            keep.add(edge_obj.name)

    instanced = _hydrate_components(collection, display_map, revision, keep,
                                    created, updated)
    _hide_instanced_sources(collection, instanced)

    # Contract-driven GC: any cadex-tagged object whose output name is no
    # longer displayable this pass goes, meshes included. Components join
    # `keep` above, so this stays the entire cleanup story -- no second GC
    # to fight. A shared datablock is never orphaned by it: the source
    # still uses it.
    removed = []
    for obj in list(_cadex_objects(collection)):
        if obj.name in keep:
            continue
        removed.append(obj.name)
        mesh = obj.data
        bpy.data.objects.remove(obj)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)

    # The component home follows its contents: a revision that drops the
    # assembly leaves no "Assembly" row behind in the outliner.
    home = _component_collection(collection, create=False)
    if home is not None and not home.all_objects:
        bpy.data.collections.remove(home)
    return {"created": created, "updated": updated, "removed": removed,
            "revision": str(revision)}
