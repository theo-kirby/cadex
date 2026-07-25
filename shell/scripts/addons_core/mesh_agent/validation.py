# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Geometry validation for Part Design mode.

After a tool-triggered rebuild, every mesh object in the Model collection is
analyzed on its *evaluated* geometry (live modifiers included) and a compact
per-part report is appended to the tool result, so the model sees defects
(open boundaries, non-manifold edges, self-intersections, ...) and can fix its
script within the same turn. Slider-drag rebuilds never run this — the hook
lives in tools.py, not model.rebuild().

The report uses a small fixed vocabulary and puts problem parts first, so it
stays legible after truncation.
"""

# Reports are truncated independently of the rebuild report so both fit under
# tools.MAX_RESULT_CHARS.
MAX_REPORT_CHARS = 1600

# Above this triangle count the BVH self-intersection test is skipped (noted
# in the report) to keep the feedback loop fast.
SELF_INTERSECT_TRI_LIMIT = 50000

_AREA_EPSILON = 1e-8


def analyze_object(obj, depsgraph):
    """Analyze one mesh object's evaluated geometry. Returns a stats dict."""
    import bmesh

    bm = bmesh.new()
    try:
        bm.from_object(obj, depsgraph)

        stats = {
            "name": obj.name,
            "type": obj.type,
            "verts": len(bm.verts),
            "tris": 0,
            "dimensions": (0.0, 0.0, 0.0),
            "boundary_edges": 0,
            "non_manifold_edges": 0,
            "non_manifold_verts": 0,
            "zero_area_faces": 0,
            "loose_verts": 0,
            "loose_edges": 0,
            "self_intersections": 0,
            "self_intersect_skipped": False,
        }
        if not bm.verts:
            return stats

        # Dimensions of the evaluated geometry in world space (mm).
        matrix = obj.matrix_world
        xs, ys, zs = [], [], []
        for vert in bm.verts:
            co = matrix @ vert.co
            xs.append(co.x)
            ys.append(co.y)
            zs.append(co.z)
        stats["dimensions"] = (max(xs) - min(xs),
                               max(ys) - min(ys),
                               max(zs) - min(zs))

        for edge in bm.edges:
            if edge.is_boundary:
                stats["boundary_edges"] += 1
            elif not edge.is_manifold:
                stats["non_manifold_edges"] += 1
            if not edge.link_faces:
                stats["loose_edges"] += 1
        for vert in bm.verts:
            if not vert.link_edges:
                stats["loose_verts"] += 1
            elif not vert.is_manifold:
                stats["non_manifold_verts"] += 1
        for face in bm.faces:
            if face.calc_area() < _AREA_EPSILON:
                stats["zero_area_faces"] += 1

        triangles = bm.calc_loop_triangles()
        stats["tris"] = len(triangles)
        if stats["tris"] > SELF_INTERSECT_TRI_LIMIT:
            stats["self_intersect_skipped"] = True
        else:
            stats["self_intersections"] = _count_self_intersections(
                bm, triangles)
        return stats
    finally:
        bm.free()


def _count_self_intersections(bm, triangles):
    """Count intersecting triangle pairs, excluding pairs that merely share a
    vertex (every neighboring triangle 'overlaps' its neighbors in the BVH)."""
    from mathutils.bvhtree import BVHTree

    tree = BVHTree.FromBMesh(bm)
    overlap = tree.overlap(tree)
    if not overlap:
        return 0
    tri_verts = [frozenset(loop.vert.index for loop in tri)
                 for tri in triangles]
    seen = set()
    count = 0
    for i, j in overlap:
        if i == j:
            continue
        key = (i, j) if i < j else (j, i)
        if key in seen:
            continue
        seen.add(key)
        if tri_verts[i] & tri_verts[j]:
            continue
        count += 1
    return count


def _issues(stats):
    """(key, count) pairs for everything wrong with a part."""
    pairs = (
        ("open-boundary", stats["boundary_edges"]),
        ("non-manifold-edges", stats["non_manifold_edges"]),
        ("non-manifold-verts", stats["non_manifold_verts"]),
        ("self-intersect", stats["self_intersections"]),
        ("zero-area-faces", stats["zero_area_faces"]),
        ("loose-verts", stats["loose_verts"]),
        ("loose-edges", stats["loose_edges"]),
    )
    return [(key, count) for key, count in pairs if count]


def _describe(stats):
    dims = "{:.1f}x{:.1f}x{:.1f}".format(*stats["dimensions"])
    issues = _issues(stats)
    if issues:
        detail = " ".join("{:s}={:d}".format(key, count)
                          for key, count in issues)
        line = "  {:s}: {:s} ISSUES {:s}".format(stats["name"], dims, detail)
    else:
        line = "  {:s}: {:s} OK manifold watertight".format(
            stats["name"], dims)
    if stats["self_intersect_skipped"]:
        line += " (self-intersection check skipped: {:d} tris)".format(
            stats["tris"])
    return line, bool(issues)


def report():
    """Compact geometry report for the Model collection. Main thread only."""
    import bpy
    from . import model

    collection = bpy.data.collections.get(model.COLLECTION_NAME)
    if collection is None:
        return "Geometry check: no Model collection."

    depsgraph = bpy.context.evaluated_depsgraph_get()
    ok_lines, issue_lines = [], []
    skipped = []
    for obj in collection.all_objects:
        if obj.type != 'MESH':
            skipped.append("{:s} ({:s})".format(obj.name, obj.type))
            continue
        line, has_issues = _describe(analyze_object(obj, depsgraph))
        (issue_lines if has_issues else ok_lines).append(line)

    total = len(ok_lines) + len(issue_lines)
    if total == 0 and not skipped:
        return "Geometry check: no mesh parts."

    header = "Geometry check (mm): {:d} part(s), {:d} OK, {:d} with issues".format(
        total, len(ok_lines), len(issue_lines))
    lines = [header] + issue_lines + ok_lines
    if skipped:
        lines.append("  non-mesh objects (not checked): " + ", ".join(skipped))
    text = "\n".join(lines)
    if len(text) > MAX_REPORT_CHARS:
        text = text[:MAX_REPORT_CHARS] + "\n[... geometry check truncated ...]"
    return text
