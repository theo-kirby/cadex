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

**The result is written into the table, not handed to the AI** (ADR-121).
That reverses ADR-067 for this one gesture, and the boundary it draws is the
point: a *measurement* is data, and a canonical row is where data goes —
``set_params(boards=[...])`` takes it, the model never sees it, and the
socket appears with no chat turn. A *name* and a hand-dragged route are
authored intent and still queue a note, which is why Define Board (ADR-119)
and Confirm Wire Path (ADR-118) are unchanged.

The fallback is honest rather than vestigial: a project whose script has no
``boards(...)`` call has no table to write into, and *creating* one means
choosing the component argument and naming the board — authoring, and the
assistant's job. There the pick still queues the note it always did, and
what changed is that the note has somewhere to land afterwards.

**The row goes out in world coordinates.** The fit is in the object's own
frame, the table is in the board's, and the shell cannot know the difference
— a hydrated object's transform is a display placement, not the asset's
declaration chain. So the row is marked ``frame: "world"`` and the engine
inverts the chain it actually resolved. That inversion is exactly what a
person used to do on paper.

**And a board says which object it is** (ADR-119). Naming one used to cost a
chat turn of description — there was no gesture that said "this object is the
range finder", so the assistant inferred it from output names and
screenshots. **Define Board** is that gesture, and it does two things: it
queues a note asking for the output to be declared as a port in
``nets(ports=...)``, and it *stamps the object with the name*, so every later
terminal pick on it says which board it is on. Click board, click terminals,
one turn declares the whole port.

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

#: Boards designated since the last turn (ADR-119). Its own queue for the same
#: reason a terminal has one: it is a different thing to say.
_pending_boards = []

#: The board name stamped on a designated object, so every later terminal pick
#: on it says which port it belongs to.
BOARD_PROP = "cadex_board"

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
# writing the row (ADR-121)


def world_row(matrix_world, row, board, name):
    """One fitted row, carried into world coordinates and named (ADR-121).

    The fit is in the object's own frame; the engine wants the *board's*, and
    the shell has no way to know what that is — a hydrated object's transform
    is the display placement, not the asset's declaration chain. So the row
    goes out in the one frame a viewport click actually has, marked
    ``frame: "world"``, and the engine converts it through the inverse of the
    placement chain it resolved. That inversion is what a person used to do
    on paper before pasting the literals into the script.
    """

    linear = matrix_world.to_3x3()
    origin = matrix_world @ Vector(row["origin"])
    axis = linear @ Vector(row["axis"])
    if axis.length > 1.0e-12:
        axis = axis / axis.length
    # A length measured in the object's frame is that frame's scale away from
    # a world millimetre; the engine divides the same scale back out.
    scale = sum(linear.col[index].length for index in range(3)) / 3.0
    written = {
        "board": str(board),
        "name": str(name),
        "origin": [round(float(value), 5) for value in origin],
        "axis": [round(float(value), 6) for value in axis],
        "frame": "world",
    }
    if row.get("hole_dia") is not None:
        written["hole_dia"] = round(float(row["hole_dia"]) * scale, 5)
    return written


def board_of(state, output):
    """The declared board one engine output is, or ``""``.

    Engine truth, and deliberately keyed on the *output* rather than on the
    Blender object's name — the identity rule ADR-119 set for Define Board,
    which this gesture now depends on rather than merely echoes. Returns ""
    for a component that is no board, or whose board is a selector: those
    rows are the geometry's and there is nothing to write.
    """

    for component in list((state or {}).get("components") or []):
        if not isinstance(component, dict):
            continue
        if str(component.get("output") or "") != str(output or ""):
            continue
        if not component.get("editable"):
            continue
        return str(component.get("board") or "")
    return ""


def terminal_rows(state):
    """The complete terminal table, read back off ``scope="wiring"``.

    ``set_params(boards=...)`` replaces the table wholesale, so a pick sends
    every row that exists plus its own — the same shape ``wiring.push``
    sends, from the same source, so the two gestures cannot disagree about
    what the table currently is.
    """

    rows = []
    for component in list((state or {}).get("components") or []):
        if not isinstance(component, dict) or not component.get("editable"):
            continue
        board = str(component.get("board") or "")
        if not board:
            continue
        for terminal in list(component.get("terminals") or []):
            if not isinstance(terminal, dict) or "origin" not in terminal:
                continue
            rows.append({
                "board": board,
                "name": str(terminal.get("name") or ""),
                "origin": [float(value) for value in terminal.get("origin") or []],
                "axis": [float(value) for value in terminal.get("axis") or []],
                "hole_dia": terminal.get("hole_dia"),
                "depth": terminal.get("depth"),
            })
    return rows


def rows_with(state, written):
    """The table plus one measured row, replacing any row of the same name."""

    key = (str(written.get("board") or ""), str(written.get("name") or ""))
    rows = [row for row in terminal_rows(state)
            if (str(row.get("board") or ""), str(row.get("name") or "")) != key]
    rows.append(dict(written))
    return rows


def free_name(state, board, prefix="t"):
    """A terminal name not already on that board, for a pick given no name."""

    taken = {str(row.get("name") or "") for row in terminal_rows(state)
             if str(row.get("board") or "") == str(board)}
    index = 1
    while "{:s}{:d}".format(prefix, index) in taken:
        index += 1
    return "{:s}{:d}".format(prefix, index)


# ---------------------------------------------------------------------------
# the queue


def queue_board(entry):
    _pending_boards.append(entry)


def pending_board_count():
    return len(_pending_boards)


def clear_boards():
    _pending_boards.clear()


def consume_board_notes():
    """Prompt suffix naming the boards designated since the last turn (drains).

    **The identity is the engine's output key, never the Blender object's
    name** (ADR-119). Everything else in the add-on routes object identity
    through the engine deliberately — ``tools.py``'s ``scene_summary`` reports
    engine truth precisely so the model reasons about the model and not about
    the mirror — and this gesture is the one that starts from a click on the
    mirror, so it is the one that has to convert.

    It states two engine limits rather than promising around them, both from
    ADR-113 §5, because "this is the range finder" invites exactly the two
    follow-ups they refuse.
    """

    if not _pending_boards:
        return ""
    lines = []
    for entry in _pending_boards:
        lines.append(
            "[The user DESIGNATED output {output!r} as a board named "
            "{name!r}. Declare it as a port in nets(ports=...) under that "
            "name, keyed on that OUTPUT — not on any Blender object name. "
            "Its bounding box is {bbox} mm and its placement is {placement}. "
            "Two things this does NOT do, so do not offer them: designating a "
            "board does not make it avoidable by its own wires — a component "
            "cannot avoid itself as a mesh, because its own pad is inside its "
            "own bounding box and every wire off it refuses with 'blocked'; "
            "part.shape_from_mesh is the workaround that exists, and it "
            "cannot express a multi-shell import. And a port with no terminals "
            "yet draws no node in the wiring editor: a node is one terminal "
            "set, and a terminal set needs a non-empty names list. This "
            "designates a board; it does not conjure a node.]".format(
                output=entry.get("output", ""),
                name=entry.get("name", ""),
                bbox=json.dumps(entry.get("bbox_mm") or []),
                placement=json.dumps(entry.get("placement") or []),
            )
        )
    _pending_boards.clear()
    return "\n\n" + "\n".join(lines)


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
            "[The user MEASURED a {kind} terminal on output {output!r}{board} "
            "(a {model} fit over {vertices} selected vertices, residual "
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
                board=(", which is the board {!r}".format(entry["board"])
                       if entry.get("board") else ""),
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
    bl_description = ("Fit a circle to the selected vertices and write the "
                      "measured terminal into the board's table")
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
        output = str(obj.get(cadex_hydrate.OUTPUT_PROP, "") or "")
        if report["kind"] == "hole":
            size = "diameter {:.3f} mm".format(report["radius_mm"] * 2.0)
        else:
            size = "{:.3f} x {:.3f} mm".format(
                report["width_mm"], report["height_mm"])

        # The row goes straight into the table when there is a table to put it
        # in (ADR-121). A measurement is data, and transcribing data through a
        # language model is the step this gesture exists to remove; the note
        # below is what remains for a project that has not declared boards(...)
        # yet, where there is genuinely authoring to be done.
        written = self._write_row(context, obj, row, output)
        if written is not None:
            self.report(
                {'INFO'},
                "Measured a {:s} ({:s} fit): {:s}, residual {:.4f} mm. Wrote "
                "{:s}.{:s}.".format(
                    report["kind"], report["fit_model"], size,
                    report["residual_mm"], written[0], written[1]))
            return {'FINISHED'}

        entry = {
            "output": output,
            "object": obj.name,
            "row": row,
            "report": report,
        }
        # Stamped by Define Board (ADR-119), if it was pressed on this object:
        # click board -> click terminals -> one turn declares the whole port.
        board = str(obj.get(BOARD_PROP) or "")
        if board:
            entry["board"] = board
        queue_terminal(entry)
        self.report(
            {'INFO'},
            "Measured a {:s} ({:s} fit): {:s}, residual {:.4f} mm. Queued for "
            "the next message.".format(
                report["kind"], report["fit_model"], size,
                report["residual_mm"]))
        return {'FINISHED'}

    def _write_row(self, context, obj, row, output):
        """Push the measured row into ``board_values``; ``None`` to fall back.

        Returns ``(board, name)`` when the row was sent. Falls back — rather
        than failing — whenever there is no declared board to write onto: no
        engine, no ``boards(...)`` in the script, or a component whose
        terminals come from a selector and are the geometry's to state.
        """

        try:
            from . import cadex_backend

            state = cadex_backend.wiring_state(context.scene)
        except Exception:
            return None
        if not isinstance(state, dict) or state.get("ok") is False:
            return None
        value = state.get("value") if isinstance(state.get("value"), dict) else state
        board = board_of(value, output)
        if not board:
            return None
        name = str(row.get("name") or "") or free_name(value, board)
        written = world_row(obj.matrix_world, row, board, name)
        # Through ``begin_set_boards``, which since ADR-122 fills the wiring
        # slot and returns a report rather than a ``Lifecycle`` nobody polls.
        # A pick had the identical defect the canvas did: the request was
        # started and then dropped, so the *second* terminal measured on a
        # board was refused with STALE_PROGRAM_REVISION in silence.
        ok, report = cadex_backend.begin_set_boards(
            context.scene, rows_with(value, written))
        if not ok:
            self.report({'ERROR'}, str(report))
            return None
        return board, name


class MESH_AGENT_OT_define_board(bpy.types.Operator):
    """Name the clicked object as a board, and say so on the next turn."""

    bl_idname = "mesh_agent.define_board"
    bl_label = "Define Board"
    bl_description = ("Name the active object as a board and queue it as a "
                      "wiring port for the next message")
    bl_options = {'REGISTER', 'UNDO'}

    name: bpy.props.StringProperty(
        name="Board",
        description="What this board is called, e.g. range_finder",
        default="",
    )

    @classmethod
    def poll(cls, context):
        if getattr(context, "mode", 'OBJECT') != 'OBJECT':
            return False
        obj = getattr(context, "active_object", None)
        return obj is not None and cadex_hydrate.OUTPUT_PROP in obj

    def invoke(self, context, _event):
        obj = getattr(context, "active_object", None)
        if not self.name and obj is not None:
            self.name = _board_name(str(obj.get(cadex_hydrate.OUTPUT_PROP) or ""))
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = getattr(context, "active_object", None)
        if obj is None or cadex_hydrate.OUTPUT_PROP not in obj:
            self.report({'ERROR'},
                        "Click a part of the model first — Define Board names "
                        "an object the engine built.")
            return {'CANCELLED'}
        output = str(obj.get(cadex_hydrate.OUTPUT_PROP) or "")
        name = _board_name(self.name or output)
        if not name:
            self.report({'ERROR'}, "A board needs a name, e.g. range_finder.")
            return {'CANCELLED'}

        low, high = _bounds(obj)
        queue_board({
            "output": output,
            "name": name,
            "object": obj.name,
            "bbox_mm": [
                [round(value, 4) for value in low],
                [round(value, 4) for value in high],
            ],
            "placement": [round(float(value), 6)
                          for row in obj.matrix_world for value in row],
        })
        # The second effect, and the one that makes the gesture compose: every
        # later terminal pick on this object carries the board it belongs to,
        # so click board -> click terminals -> one turn declares the whole port.
        obj[BOARD_PROP] = name
        self.report(
            {'INFO'},
            "Board {:s} ({:s}). Pick its terminals in Edit Mode; they will say "
            "which board they are on.".format(name, output))
        return {'FINISHED'}


def _board_name(text):
    """A port name ``nets(...)`` will accept: lower_snake_case, no dot."""

    cleaned = []
    for character in str(text or "").strip().lower():
        cleaned.append(character if (character.isalnum() or character == "_") else "_")
    name = "".join(cleaned).strip("_")
    while "__" in name:
        name = name.replace("__", "_")
    if name and name[0].isdigit():
        name = "b_" + name
    return name[:64]


def _bounds(obj):
    """The object's world-space bounding box, as (low, high)."""

    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    if not corners:
        origin = obj.matrix_world.translation
        return list(origin), list(origin)
    low = [min(corner[axis] for corner in corners) for axis in range(3)]
    high = [max(corner[axis] for corner in corners) for axis in range(3)]
    return low, high


classes = (MESH_AGENT_OT_define_terminal, MESH_AGENT_OT_define_board)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    _pending_terminals.clear()
    _pending_boards.clear()
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
