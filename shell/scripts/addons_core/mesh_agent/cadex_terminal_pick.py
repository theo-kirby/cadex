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
plane-fit answer and is wrong for a hole), then **two models fitted to the
same points** — a circle by Kåsa's closed-form least squares, and a
minimum-area enclosing rectangle by rotating calipers. The numbers go back
into the asset's own frame with ``obj.matrix_world.inverted_safe()``, exactly
as :func:`cadex_pick.point_pin` already does — that is the frame
``mesh.terminals`` declares in.

**The terminal lands in the plane you selected** (ADR-117). One ring is a
bore's mouth and the wire ends flush in it; one rectangle is a pad and the
wire ends at its centre. Neither carries a ``depth``: since ADR-117 the
landing *is* the mouth and the bore behind it is left empty, so ``hole_dia``
is what says a row is holes and a depth would size nothing. Selecting both
rims of a through-hole still works — the far one is dropped, and the report
says so.

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
- **Hole or pad.** ADR-067's rule stands: a residual is a quality signal and
  never a classifier, so "the circle fits well, therefore a bore" is not
  available. Both models are fitted, each residual is normalised by its own
  scale (the radius, the half-diagonal) and the better one wins — and **when
  the two are inside noise of each other the pick is refused with both fits
  named**, because that case is genuinely ambiguous rather than merely
  close. A rectangle's four corners are concyclic, so four corners fit a
  circle *exactly*: nothing can tell them apart, and saying so is the honest
  answer. The operator's enum is the override.
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

#: A fit worse than this fraction of its own scale is not a fit at all. It is
#: applied to the model that *won*, so it stays a quality gate and never a
#: classifier — the distinction ADR-067 drew and ADR-117 keeps.
MAX_RESIDUAL_RATIO = 0.15

#: How far apart the two models' normalised residuals must be for ``AUTO`` to
#: prefer one. Below it the selection is refused rather than guessed at.
#:
#: Calibrated on the two cases that matter. A ring of points fitted to its own
#: minimum-area rectangle sits, on average, ``0.1 r`` inside the nearest edge —
#: about 0.078 once normalised by the half-diagonal — against ~0 for the
#: circle, so a real rim clears this by three-and-a-half times even on a
#: coarse STL. A rectangle's four corners score *exactly* zero on both, which
#: is the case this margin exists to refuse.
AMBIGUOUS_MARGIN = 0.02


#: Below this ratio of smallest to median scatter eigenvalue, a selection is
#: flat and its normal is simply the least-variance direction. Above it the
#: cloud has real depth — two rims of a bore — and the odd-one-out rule below
#: is what finds the axis. See :func:`_principal_axis`.
PLANAR_EIGENVALUE_RATIO = 0.1


def _principal_axis(points):
    """The bore/pad axis of a selection, with its centroid.

    Two rules, and which one applies is decided by whether the selection is
    flat. Neither is safe on its own, and both failures were found the hard
    way.

    **Not always the smallest eigenvector of the scatter matrix**, which is
    what a plane fit wants and what a hole quietly breaks. Two rims of radius
    0.5 on a 1.6 mm board are a point cloud that is *taller than it is wide*,
    so least-variance picks a plane containing the axis and the whole fit
    comes back as a nonsense pad.

    The rule that fixes that uses the property that makes those points
    circular rather than the one that makes them flat: on a circle or a
    cylinder **two of the three eigenvalues are equal** (the in-plane pair)
    and the third is the axis, whichever end of the ordering it lands on. So
    the axis is the eigenvector whose eigenvalue is furthest from the median.

    **But that rule assumes the section is circular, and ADR-117 added a
    model where it is not.** A flat 2:1 rectangle has in-plane variances in a
    4:1 ratio, so its eigenvalues are `(0, λ, 4λ)`, the median is `λ`, and the
    odd one out is `4λ` — the pad's own long axis, taken as its normal. Every
    rectangle longer than about √2 : 1 came back fitted edge-on.

    So: **if the cloud is flat, the normal is unambiguous and is the smallest
    eigenvector**; only when it has real depth does the odd-one-out rule get
    used. Flatness is `λ_min / λ_median`, which is ~0 for one ring and for a
    rectangle alike, and 1 for a bore whose depth matches its radius. The two
    rules agree everywhere they overlap: a shallow bore reads as flat, and
    its smallest eigenvector *is* its axis.
    """

    import numpy

    centroid = sum(points, Vector((0.0, 0.0, 0.0))) / len(points)
    deltas = numpy.array([[p.x - centroid.x, p.y - centroid.y, p.z - centroid.z]
                          for p in points], dtype=float)
    scatter = deltas.T @ deltas
    values, vectors = numpy.linalg.eigh(scatter)
    ordered = sorted(float(value) for value in values)
    median = ordered[1]
    if median <= 1.0e-18 or ordered[0] <= PLANAR_EIGENVALUE_RATIO * median:
        index = min(range(3), key=lambda i: float(values[i]))
    else:
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


def _convex_hull(planar):
    """The 2D convex hull of ``[(x, y), ...]``, counter-clockwise.

    Monotone chain: a sort and two linear passes, so it is deterministic for
    the same reason :func:`fit_circle`'s Kåsa solve is — no iteration and no
    seed to argue about.
    """

    ordered = sorted(set(planar))
    if len(ordered) < 3:
        return ordered

    def half(sequence):
        chain = []
        for point in sequence:
            while len(chain) >= 2:
                (x1, y1), (x2, y2) = chain[-2], chain[-1]
                cross = ((x2 - x1) * (point[1] - y1)) - ((y2 - y1) * (point[0] - x1))
                if cross > 0.0:
                    break
                chain.pop()
            chain.append(point)
        return chain

    lower = half(ordered)
    upper = half(list(reversed(ordered)))
    return lower[:-1] + upper[:-1]


def fit_rectangle(points, normal, origin):
    """The minimum-area enclosing rectangle. Returns (centre, w, h, u, rms).

    The pad half of the pick (ADR-117). A pad is usually square, and fitting a
    circle to one is meaningless — four corners fit a circle *exactly*, with
    the radius coming out as half the diagonal.

    Rotating calipers over the convex hull: the minimum-area enclosing
    rectangle always has a side flush with a hull edge, so trying each hull
    edge in turn is exhaustive rather than approximate. There is no iteration
    and no seed, which is the same property :func:`fit_circle` was chosen for.

    ``rms`` is the root-mean-square distance from each point to the *nearest
    rectangle edge*, so a selection that really is a rectangle's outline
    scores zero and a ring scores about a tenth of its radius.
    """

    u, v = _basis(normal)
    planar = [((point - origin).dot(u), (point - origin).dot(v)) for point in points]
    hull = _convex_hull(planar)
    if len(hull) < 3:
        return None, 0.0, 0.0, None, float("inf")

    best = None
    for index in range(len(hull)):
        (x1, y1), (x2, y2) = hull[index], hull[(index + 1) % len(hull)]
        length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        if length <= 1.0e-12:
            continue
        ex, ey = (x2 - x1) / length, (y2 - y1) / length
        along = [x * ex + y * ey for x, y in planar]
        across = [-x * ey + y * ex for x, y in planar]
        width = max(along) - min(along)
        height = max(across) - min(across)
        area = width * height
        if best is None or area < best[0]:
            centre_along = 0.5 * (max(along) + min(along))
            centre_across = 0.5 * (max(across) + min(across))
            best = (area, width, height, (ex, ey),
                    (centre_along, centre_across), (along, across))
    if best is None:
        return None, 0.0, 0.0, None, float("inf")

    _area, width, height, (ex, ey), (ca, cb), (along, across) = best
    half_w, half_h = width / 2.0, height / 2.0
    total = 0.0
    for a, b in zip(along, across):
        # Every point is inside the enclosing rectangle by construction, so
        # the nearest edge is whichever of the four walls it sits closest to.
        total += min(half_w - abs(a - ca), half_h - abs(b - cb)) ** 2
    rms = (total / len(planar)) ** 0.5
    centre = origin + u * (ca * ex - cb * ey) + v * (ca * ey + cb * ex)
    axis_u = (u * ex + v * ey).normalized()
    return centre, width, height, axis_u, rms


def _split_loops(points, normal, origin):
    """One loop or two, by the largest gap in the along-axis projection.

    Kept only for the case where someone selects **both** rims of a
    through-hole (ADR-117). One ring is enough for a bore now, so the far loop
    is dropped rather than paired with the near one to measure a depth; what
    this still has to do is notice the second rim so it does not get fitted
    together with the first as one wildly out-of-plane blob.
    """

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


def _loop_station(loop, origin, axis):
    """How far down ``axis`` a loop's centroid sits — the near rim is least."""

    centroid = sum(loop, Vector((0.0, 0.0, 0.0))) / len(loop)
    return (centroid - origin).dot(axis)


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
        return None, "The selected vertices are collinear; there is nothing to fit."

    # The axis sign is not decidable from the fit: an eigenvector's is
    # arbitrary. The viewport is what resolves it — the wire arrives from the
    # side the user is looking from, so the drilling direction points away.
    axis = Vector(normal)
    if view_direction is not None and axis.dot(Vector(view_direction)) < 0.0:
        axis = -axis
    axis_from = "the view direction" if view_direction is not None else "the fit"

    # Both rims of a through-hole is a perfectly ordinary selection, and one
    # ring is enough for a bore since ADR-117 — so the far one is dropped
    # rather than paired, and the report says it was.
    loops = _split_loops(points, normal, centroid)
    dropped_far_loop = len(loops) > 1
    if dropped_far_loop:
        loops = [min(loops, key=lambda loop: _loop_station(loop, centroid, axis))]
    loop = loops[0]
    loop_centroid = sum(loop, Vector((0.0, 0.0, 0.0))) / len(loop)

    circle_centre, radius, circle_rms = fit_circle(loop, normal, loop_centroid)
    rect_centre, width, height, _u_axis, rect_rms = fit_rectangle(
        loop, normal, loop_centroid)
    if circle_centre is None and rect_centre is None:
        return None, "The selection could not be fitted to a circle or a rectangle."

    # Each residual normalised by its own model's scale, so the two numbers
    # are comparable at all: a circle's is its radius, a rectangle's is its
    # half-diagonal.
    half_diagonal = 0.5 * (width * width + height * height) ** 0.5
    circle_ratio = (
        float("inf") if circle_centre is None or radius <= 1.0e-9
        else circle_rms / radius)
    rect_ratio = (
        float("inf") if rect_centre is None or half_diagonal <= 1.0e-9
        else rect_rms / half_diagonal)
    margin = abs(circle_ratio - rect_ratio)

    resolved = kind
    if resolved == 'AUTO':
        if not (margin > AMBIGUOUS_MARGIN):
            return None, (
                "That selection fits a circle and a rectangle equally well "
                "({:.4f} vs {:.4f} of their own scale), so nothing here can "
                "tell a bore from a pad — four corners of a rectangle are "
                "concyclic, so they fit a circle exactly. The circle is "
                "{:.3f} mm across; the rectangle is {:.3f} x {:.3f} mm. "
                "Choose Hole or Pad on the operator panel.".format(
                    circle_ratio, rect_ratio,
                    radius * 2.0 if circle_centre is not None else 0.0,
                    width, height))
        resolved = 'HOLE' if circle_ratio < rect_ratio else 'PAD'

    if resolved == 'HOLE':
        if circle_centre is None or radius <= 1.0e-9:
            return None, "The fitted circle has no radius."
        origin, residual, scale = circle_centre, circle_rms, radius
    else:
        if rect_centre is None or half_diagonal <= 1.0e-9:
            return None, "The fitted rectangle has no extent."
        origin, residual, scale = rect_centre, rect_rms, half_diagonal
    if residual > MAX_RESIDUAL_RATIO * scale:
        return None, (
            "That selection is not a {:s}: the best fit is {:.4f} mm across "
            "and the points sit {:.4f} mm off it. Select a hole rim or a pad "
            "outline, or state the terminal by hand.".format(
                "circle" if resolved == 'HOLE' else "rectangle",
                scale * 2.0, residual))

    # No depth on either kind: the landing *is* the mouth since ADR-117, and
    # `hole_dia` is what says a row is holes.
    row = {
        "origin": [round(float(value), 5) for value in origin],
        "axis": [round(float(value), 6) for value in axis],
    }
    if resolved == 'HOLE':
        row["hole_dia"] = round(float(radius * 2.0), 5)
    report = {
        "kind": "hole" if resolved == 'HOLE' else "pad",
        "kind_guessed": kind == 'AUTO',
        "vertices": len(points),
        "fit_model": "circle" if resolved == 'HOLE' else "rectangle",
        "residual_mm": round(float(residual), 6),
        "residual_ratio": round(float(residual / scale), 6),
        "circle_ratio": None if circle_ratio == float("inf") else round(
            float(circle_ratio), 6),
        "rectangle_ratio": None if rect_ratio == float("inf") else round(
            float(rect_ratio), 6),
        "model_margin": None if margin == float("inf") else round(
            float(margin), 6),
        "axis_resolved_from": axis_from,
        "far_loop_ignored": bool(dropped_far_loop),
    }
    if resolved == 'HOLE':
        report["radius_mm"] = round(float(radius), 5)
    else:
        # In the *report* and never in the row: a declared layout row has no
        # rectangle field, and inventing one would put pad geometry into the
        # layout, which ADR-065 put out of scope. This is what lets the
        # assistant choose part.solder's pad_dia_mm.
        report["width_mm"] = round(float(width), 5)
        report["height_mm"] = round(float(height), 5)
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
        margin = report.get("model_margin")
        lines.append(
            "[The user MEASURED a {kind} terminal on output {output!r} (a "
            "{model} fit over {vertices} selected vertices, residual "
            "{residual:.4f} mm = {ratio:.2%} of its own scale; it beat the "
            "other model by {margin} of normalised residual; axis sign "
            "resolved from {axis_from}). The terminal lands IN this plane and "
            "carries no depth (ADR-117). These are the object's own "
            "coordinates, which is the frame mesh.terminals rows are written "
            "in. Transcribe them into a terminals row — do NOT re-derive them "
            "from the bounding box:\n"
            "  {row}\n"
            "  detail: {detail}]".format(
                kind=report.get("kind", "pad"),
                model=report.get("fit_model", "circle"),
                output=entry.get("output", ""),
                vertices=report.get("vertices", 0),
                residual=float(report.get("residual_mm") or 0.0),
                ratio=float(report.get("residual_ratio") or 0.0),
                margin="{:.4f}".format(margin) if margin is not None else "n/a",
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
        description="Auto fits a circle and a rectangle and takes the better "
                    "one; four corners fit both exactly, so it refuses rather "
                    "than guesses and this is where you say which",
        items=(
            ('AUTO', "Auto", "Whichever of a circle and a rectangle fits better"),
            ('HOLE', "Hole", "A drilled bore; the wire ends flush in this rim"),
            ('PAD', "Pad", "A flat contact; the wire ends at this centre"),
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
        if report["kind"] == "hole":
            size = "diameter {:.3f} mm".format(report["radius_mm"] * 2.0)
        else:
            size = "{:.3f} x {:.3f} mm".format(
                report["width_mm"], report["height_mm"])
        self.report(
            {'INFO'},
            "Measured a {:s} ({:s} fit): {:s}, residual {:.4f} mm. Queued for "
            "the next message.".format(
                report["kind"], report["fit_model"], size,
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
