# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Defining a terminal by clicking the model (ADR-067).

``part.terminals`` can name holes with a selector on a BREP board, and that
works. The case it cannot reach is the one the AI gets wrong most often: an
**imported STL**, which has no faces to select, so its terminals must be
*declared* — a row of hand-written origin/axis/pitch/depth numbers that the
model guesses from a bounding box and a screenshot.

This replaces the guess with a measurement. Alt-click a hole rim in Edit
Mode (one click selects the loop), press **Define Terminal**, and the
selection is fitted: the bore axis from the scatter matrix's odd-one-out
eigenvector (see :func:`_principal_axis` — *not* its smallest, which is the
plane-fit answer and is wrong for a hole), the points clustered along that
axis into at most two loops, and each loop fitted to a circle by closed-form
least squares. The numbers go back into the asset's own frame with
``obj.matrix_world.inverted_safe()``, exactly as :func:`cadex_pick.point_pin`
already does — that is the frame ``mesh.terminals`` declares in.

**The result is handed to the AI, not written to the script.** A terminal's
home is a ``mesh.terminals(...)`` call that usually does not exist yet, and
creating it means choosing the component argument, naming the set and wiring
it into a ``part.cable``. That is authoring, and authoring is the
assistant's job. What changes is that it stops guessing and starts
transcribing.

**A terminal is not a pin.** ``docs/XSCRIPT.md`` is explicit that a pin is
chat-scoped and ephemeral while a terminal is script-scoped and durable, so
this queues into its own list with its own wording rather than riding
``cadex_pick._pending_pins``. Several picks batch into one turn, so a 19-pin
header costs one turn and not nineteen.

Three things it must not guess:

- **Fewer than four vertices.** Three points always fit a circle exactly, so
  the residual carries no information. Refused, naming the count.
- **Hole or pad.** A square pad's four corners fit a circle with *zero*
  residual (radius = half the diagonal), so the residual is a quality
  signal and never a classifier. The operator carries an enum, defaulted
  from the geometry, and says which way it guessed.
- **The axis sign.** An eigenvector's sign is arbitrary and
  ``mesh.terminals`` needs the direction drilled *into* the body. Resolved
  from the viewport's view direction and reported so it can be flipped — the
  same instinct ``part.terminals`` encodes by making ``exit=`` required for
  ``holes=``.
"""

import json

import bpy
import bmesh
from mathutils import Matrix, Vector

from . import cadex_hydrate


#: Measured terminals waiting to be handed to the next chat turn. Separate
#: from ``cadex_pick._pending_pins`` on purpose: see the module docstring.
_pending_terminals = []

#: Below four points a circle fit is not a fit, it is an interpolation.
MIN_VERTICES = 4

#: A fit worse than this fraction of the radius is not a circle.
MAX_RESIDUAL_RATIO = 0.15

#: Two loops count as one bore when their radii agree this closely.
COAXIAL_RADIUS_RATIO = 0.1


def _principal_axis(points):
    """The bore/pad axis of a selection, with its centroid.

    **Not** the smallest eigenvector of the scatter matrix, which is what a
    plane fit wants and what a hole quietly breaks. Two rims of radius 0.5
    on a 1.6 mm board are a point cloud that is *taller than it is wide*, so
    least-variance picks a plane containing the axis and the whole fit comes
    back as a nonsense pad — found the hard way, and this is the test that
    keeps it found.

    The right rule uses the property that makes these points circular rather
    than the one that makes them flat: on a circle or a cylinder **two of the
    three eigenvalues are equal** (the in-plane pair) and the third is the
    axis, whichever end of the ordering it lands on. So the axis is the
    eigenvector whose eigenvalue is furthest from the median of the three —
    correct for one flat ring (odd one out ~0), for a deep narrow bore (odd
    one out largest) and for a shallow wide one (smallest) alike.
    """

    import numpy

    centroid = sum(points, Vector((0.0, 0.0, 0.0))) / len(points)
    deltas = numpy.array([[p.x - centroid.x, p.y - centroid.y, p.z - centroid.z]
                          for p in points], dtype=float)
    scatter = deltas.T @ deltas
    values, vectors = numpy.linalg.eigh(scatter)
    median = float(sorted(values)[1])
    index = max(range(3), key=lambda i: abs(float(values[i]) - median))
    axis = Vector(tuple(float(value) for value in vectors[:, index]))
    if axis.length <= 1.0e-12:
        return None, centroid
    return axis.normalized(), centroid


def _basis(normal):
    seed = Vector((1.0, 0.0, 0.0))
    if abs(normal.dot(seed)) > 0.9:
        seed = Vector((0.0, 1.0, 0.0))
    u = (seed - normal * seed.dot(normal)).normalized()
    return u, normal.cross(u).normalized()


def fit_circle(points, normal, origin):
    """Kåsa's closed-form least-squares circle. Returns (centre, radius, rms).

    Linear least squares, so it is deterministic: no iteration, no seed, no
    convergence to argue about.
    """

    u, v = _basis(normal)
    sx = sy = sxx = syy = sxy = sz = sxz = syz = 0.0
    count = float(len(points))
    planar = []
    for point in points:
        d = point - origin
        x, y = d.dot(u), d.dot(v)
        planar.append((x, y))
        z = x * x + y * y
        sx += x
        sy += y
        sxx += x * x
        syy += y * y
        sxy += x * y
        sz += z
        sxz += x * z
        syz += y * z
    matrix = Matrix(((sxx, sxy, sx), (sxy, syy, sy), (sx, sy, count)))
    if abs(matrix.determinant()) <= 1.0e-18:
        return None, 0.0, float("inf")
    a, b, c = matrix.inverted() @ Vector((sxz, syz, sz))
    cx, cy = a / 2.0, b / 2.0
    inner = c + cx * cx + cy * cy
    if inner <= 0.0:
        return None, 0.0, float("inf")
    radius = inner ** 0.5
    total = 0.0
    for x, y in planar:
        delta = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 - radius
        total += delta * delta
    rms = (total / count) ** 0.5
    return origin + u * cx + v * cy, radius, rms


def _split_loops(points, normal, origin):
    """One loop or two, by the largest gap in the along-axis projection."""

    keyed = sorted(((point - origin).dot(normal), point) for point in points)
    if len(keyed) < 2 * MIN_VERTICES:
        return [list(points)]
    gaps = [(keyed[i + 1][0] - keyed[i][0], i) for i in range(len(keyed) - 1)]
    gap, index = max(gaps)
    spread = keyed[-1][0] - keyed[0][0]
    below = index + 1
    if (gap < 0.5 * spread or below < MIN_VERTICES
            or len(keyed) - below < MIN_VERTICES):
        return [list(points)]
    return [[item[1] for item in keyed[:below]],
            [item[1] for item in keyed[below:]]]


def measure_selection(points, view_direction=None, kind='AUTO'):
    """Fit one terminal to a set of object-local points.

    Returns ``(row | None, report)``. ``row`` is exactly the mapping a
    ``mesh.terminals`` layout row takes, in the object's own coordinates.
    """

    points = [Vector(point) for point in points]
    if len(points) < MIN_VERTICES:
        return None, (
            "Select at least {:d} vertices around the rim — {:d} is not "
            "enough to tell a circle from an interpolation. Alt-click one "
            "edge of the hole to take the whole loop.".format(
                MIN_VERTICES, len(points)))
    normal, centroid = _principal_axis(points)
    if normal is None:
        return None, "The selected vertices are collinear; there is no circle to fit."

    loops = _split_loops(points, normal, centroid)
    fits = []
    for loop in loops:
        # Each loop is fitted in the *shared* axis frame, about its own
        # centroid: two rims of one bore must not disagree about which way
        # the axis points, or the depth below is measured across a fold.
        loop_centroid = sum(loop, Vector((0.0, 0.0, 0.0))) / len(loop)
        centre, radius, rms = fit_circle(loop, normal, loop_centroid)
        if centre is None:
            return None, "The selection could not be fitted to a circle."
        fits.append((centre, radius, rms))

    worst = max(fit[2] for fit in fits)
    mean_radius = sum(fit[1] for fit in fits) / len(fits)
    if mean_radius <= 1.0e-9:
        return None, "The fitted circle has no radius."
    if worst > MAX_RESIDUAL_RATIO * mean_radius:
        return None, (
            "That selection is not a circle: the best-fit radius is "
            "{:.4f} mm and the points sit {:.4f} mm off it. Select a hole "
            "rim, or state the pad by hand.".format(mean_radius, worst))

    # Two coaxial loops of matching radius are the two ends of one bore.
    two_loops = len(fits) == 2
    matched = two_loops and abs(fits[0][1] - fits[1][1]) <= (
        COAXIAL_RADIUS_RATIO * mean_radius)
    resolved = kind
    if resolved == 'AUTO':
        resolved = 'HOLE' if (two_loops and matched) else 'PAD'

    # The axis sign is not decidable from the fit: SVD's normal is arbitrary.
    # The viewport is what resolves it — the wire enters from the side the
    # user is looking from, so the drilling direction points away.
    axis = Vector(normal)
    if view_direction is not None and axis.dot(Vector(view_direction)) < 0.0:
        axis = -axis
    axis_from = "the view direction" if view_direction is not None else "the fit"

    if resolved == 'HOLE' and two_loops:
        near = max(fits, key=lambda fit: (fit[0] - centroid).dot(-axis))
        far = min(fits, key=lambda fit: (fit[0] - centroid).dot(-axis))
        origin = near[0]
        depth = abs((far[0] - near[0]).dot(axis))
        radius = min(near[1], far[1])
    else:
        origin = fits[0][0]
        depth = 0.0
        radius = fits[0][1]

    row = {
        "origin": [round(float(value), 5) for value in origin],
        "axis": [round(float(value), 6) for value in axis],
        "depth": round(float(depth), 5),
    }
    if resolved == 'HOLE':
        row["hole_dia"] = round(float(radius * 2.0), 5)
    report = {
        "kind": "hole" if resolved == 'HOLE' else "pad",
        "kind_guessed": kind == 'AUTO',
        "vertices": len(points),
        "loops": len(fits),
        "residual_mm": round(float(worst), 6),
        "residual_ratio": round(float(worst / mean_radius), 6),
        "radius_mm": round(float(radius), 5),
        "axis_resolved_from": axis_from,
        "coaxial_radii_match": bool(matched) if two_loops else None,
    }
    return row, report


# ---------------------------------------------------------------------------
# the queue


def queue_terminal(entry):
    _pending_terminals.append(entry)


def pending_terminal_count():
    return len(_pending_terminals)


def clear_terminals():
    _pending_terminals.clear()


def consume_terminal_notes():
    """Prompt suffix describing terminals measured since the last turn (drains).

    Deliberately worded as a *measurement to transcribe* rather than as a
    fact to reason from: the whole point of the gesture is that the model
    stops deriving these numbers and starts copying them.
    """

    if not _pending_terminals:
        return ""
    lines = []
    for entry in _pending_terminals:
        row = entry.get("row") or {}
        report = entry.get("report") or {}
        lines.append(
            "[The user MEASURED a terminal on output {output!r} (a circle fit "
            "over {vertices} selected vertices, residual {residual:.4f} mm = "
            "{ratio:.2%} of the radius; axis sign resolved from {axis_from}). "
            "These are the object's own coordinates, which is the frame "
            "mesh.terminals rows are written in. Transcribe them into a "
            "terminals row — do NOT re-derive them from the bounding box:\n"
            "  {row}\n"
            "  detail: {detail}]".format(
                output=entry.get("output", ""),
                vertices=report.get("vertices", 0),
                residual=float(report.get("residual_mm") or 0.0),
                ratio=float(report.get("residual_ratio") or 0.0),
                axis_from=report.get("axis_resolved_from", "the fit"),
                row=json.dumps(row, default=str),
                detail=json.dumps(report, default=str),
            )
        )
    _pending_terminals.clear()
    return "\n\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# the operator


def _view_direction(context):
    for area in getattr(context.screen, "areas", []) or []:
        if area.type != 'VIEW_3D':
            continue
        for space in area.spaces:
            region = getattr(space, "region_3d", None)
            if region is not None:
                return (region.view_rotation @ Vector((0.0, 0.0, -1.0)))
    return None


class MESH_AGENT_OT_define_terminal(bpy.types.Operator):
    """Fit a terminal to the selected hole rim and hand it to the assistant."""

    bl_idname = "mesh_agent.define_terminal"
    bl_label = "Define Terminal"
    bl_description = ("Fit a circle to the selected vertices and queue the "
                      "measured terminal for the next message")
    bl_options = {'REGISTER'}

    name: bpy.props.StringProperty(
        name="Signal",
        description="What this terminal is called, e.g. sda",
        default="",
    )
    kind: bpy.props.EnumProperty(
        name="Kind",
        description="A circle fit cannot tell a hole rim from a square pad — "
                    "four corners fit a circle exactly — so this is a guess "
                    "you can correct",
        items=(
            ('AUTO', "Auto", "Two coaxial loops of matching radius mean a hole"),
            ('HOLE', "Hole", "A drilled bore the wire threads"),
            ('PAD', "Pad", "A flat surface contact"),
        ),
        default='AUTO',
    )
    flip_axis: bpy.props.BoolProperty(
        name="Flip Axis",
        description="The drilling direction points away from the viewer; "
                    "turn this on when it should not",
        default=False,
    )

    @classmethod
    def poll(cls, context):
        obj = context.edit_object
        return obj is not None and cadex_hydrate.OUTPUT_PROP in obj

    def execute(self, context):
        obj = context.edit_object
        if obj is None:
            self.report({'ERROR'}, "Define Terminal works in Edit Mode.")
            return {'CANCELLED'}
        mesh = bmesh.from_edit_mesh(obj.data)
        points = [vertex.co.copy() for vertex in mesh.verts if vertex.select]
        if not points:
            self.report({'ERROR'}, "Select a hole rim first (Alt-click one edge).")
            return {'CANCELLED'}

        direction = _view_direction(context)
        if direction is not None:
            # The hit is in world space and the fit is in the object's, so the
            # view direction goes back through the placement too.
            direction = obj.matrix_world.inverted_safe().to_3x3() @ direction
            if self.flip_axis:
                direction = -direction

        row, report = measure_selection(points, view_direction=direction,
                                        kind=self.kind)
        if row is None:
            self.report({'ERROR'}, str(report))
            return {'CANCELLED'}
        if self.name:
            row["name"] = self.name
        queue_terminal({
            "output": str(obj.get(cadex_hydrate.OUTPUT_PROP, "") or ""),
            "object": obj.name,
            "row": row,
            "report": report,
        })
        self.report(
            {'INFO'},
            "Measured a {:s}: radius {:.3f} mm, depth {:.3f} mm, residual "
            "{:.4f} mm. Queued for the next message.".format(
                report["kind"], report["radius_mm"], row["depth"],
                report["residual_mm"]))
        return {'FINISHED'}


classes = (MESH_AGENT_OT_define_terminal,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    _pending_terminals.clear()
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
