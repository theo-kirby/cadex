# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Panels cut from the envelope of what they cover: the worker half (ADR-635).

``part.envelope(over=[...], clearance=, radius=, motion=)`` states what a
cover is drawn round; ``part.panel(env, side=, ...)`` takes one region of it
as a thin, open, screwed-down piece. Both are declared in the script and
built here, on the exact solids the worker already has, so nothing in the
script has to guess where a part's material is.

**The envelope.** Let ``C`` be the covered solids, with the space each
declared motion sweeps added. The envelope is the surface at ``clearance``
from the *closing* of ``C`` by a ball of ``radius``: dilate by ``r``, erode
by ``r``. ``r = 0`` shrink-wraps; a large ``r`` bridges every gap and is the
convex hull, the egg; ``r`` of 15-40 mm bridges the gaps between parts and
still dips between masses further apart than ``2r``. It is computed as a
signed distance field on a voxel grid in the panel's own frame (local
``+z`` is the panel's ``side``): the covered solids are tessellated and
filled by ray parity, closed with two Euclidean distance transforms, and
distanced once more.

**The panel.** Seen from ``side``, the envelope's first crossing of each
column is a height field: the panel's inner face. Columns are kept where
that face turns less than ``max_angle`` from ``side``, inside ``within``,
and outside every opening (a part the panel must clear, swept through its
motion, or a sensor's view cone). The kept region's outline is contoured
smoothly and closed with periodic B-splines; the inner face is fitted with
a B-spline surface, thickened outward by ``thickness`` along its normal,
and trimmed by the outline's prism. Seams are planes, cut with a gap. Each
piece gets ``screws`` bosses dropped along ``-side`` onto the exact frame
BREP (a ray cast, not a sample), with a clearance hole, a counterbore that
seats every screw at the one stocked length the script chose, and a
tap-drill pilot for the frame. The fasteners' frames are published, so the
script places each screw with ``part.mate`` onto them.

numpy and scipy are imported when a panel is built, never at module scope;
the kernel half (``Part``) likewise. :func:`occupancy`,
:func:`closed_distance`, :func:`height_field`, :func:`contour_loops` and
:func:`choose_sites` are pure arrays and are unit-tested headless.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Mapping, Sequence

__all__ = [
    "EnvelopeError",
    "MAX_VOXELS",
    "occupancy",
    "closed_distance",
    "height_field",
    "contour_loops",
    "choose_sites",
    "build_panel_plan",
    "build_skin_plan",
]


class EnvelopeError(ValueError):
    """A panel request the worker cannot meet, with the reason."""


#: The largest grid one field may use. A creature torso at 1 mm is ~4 M.
#: With the float fields kept beside it (closing, distance, room) one plan
#: peaks at a few hundred MB; the voxel count is checked before anything
#: is allocated, and the resolution coarsened to fit.
MAX_VOXELS = 9_000_000
#: Triangle-column pairs expanded at once while filling the voxels.
PAIR_BUDGET = 2_000_000
#: Covered triangles one plan reads, motion poses included.
MAX_TRIANGLES = 1_500_000
#: Hull planes x grid cells evaluated at once.
HULL_BUDGET = 4_000_000
#: The finest and coarsest automatic voxel, mm.
MIN_RESOLUTION_MM = 0.6
MAX_RESOLUTION_MM = 4.0
#: The angle step a hinge's sweep is sampled at, at most.
SWEEP_STEP_DEGREES = 5.0
#: How far a form panel's slope and outline are smoothed, mm (ADR-679).
FORM_SMOOTH_MM = 4.0

#: A piece's solid under this fraction of its largest is a sliver, and dropped.
SPECK_FRACTION = 0.1

#: How far into the frame a boss starts before the frame is cut from it, mm.
BOSS_SEAT_MM = 1.5

#: How far down a boss may reach for the frame, mm.
BOSS_REACH_MM = 60.0
#: Material kept under a screw head, and around a hole, mm.
SEAT_FLOOR_MM = 1.6
#: How far a skirt stands outside the outline, plus 0.6 of a voxel: the outline
#: is where the face turns max_angle, a vertical side below it is nearer, and the
#: outline's rounded corners are drawn a little inside the field's own.
SKIRT_STEP_MM = 0.6
BOSS_WALL_MM = 1.4


# ---------------------------------------------------------------------------
# frames


def _unit(v, what="direction"):
    length = math.sqrt(sum(float(x) * float(x) for x in v))
    if length <= 1e-12:
        raise EnvelopeError(f"{what} must not be zero")
    return [float(x) / length for x in v]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def panel_frame(side: Sequence[float]):
    """``(e1, e2, s)``: a right-handed frame whose third axis is ``side``.

    ``e1`` is the world axis least aligned with ``side`` projected off it, so
    a top panel's local axes are the world's own.
    """

    s = _unit(side, "side")
    helper = min(((abs(s[i]), i) for i in range(3)))[1]
    axis = [0.0, 0.0, 0.0]
    axis[helper] = 1.0
    if abs(s[2]) > 0.9:
        axis = [1.0, 0.0, 0.0]
    dot = sum(axis[i] * s[i] for i in range(3))
    e1 = _unit([axis[i] - dot * s[i] for i in range(3)])
    e2 = _cross(s, e1)
    return e1, e2, s


# ---------------------------------------------------------------------------
# voxels


def occupancy(triangles, origin, h, dims):
    """Fill a closed triangle soup onto the grid ``origin + (i+.5, j+.5, k+.5) h``.

    Parity along ``+z``: a voxel is solid when an odd number of the
    surface's crossings of its column lie below its centre. The column
    centres are nudged off the grid lines by irrational fractions of a cell
    (``CadexStress.voxelise``'s defence against a ray through a shared
    edge), and crossings within a nanometre collapse to one.
    """

    import numpy as np

    nx, ny, nz = dims
    occ = np.zeros((nx, ny, nz), dtype=bool)
    T = np.asarray(triangles, dtype=float).reshape(-1, 3, 3)
    if not len(T):
        return occ
    jx, jy = h * (math.sqrt(2.0) - 1.0) * 0.037, h * (math.sqrt(3.0) - 1.0) * 0.041
    a = T[:, 0]
    ab = T[:, 1] - a
    ac = T[:, 2] - a
    det = ab[:, 0] * ac[:, 1] - ab[:, 1] * ac[:, 0]
    live = np.abs(det) > 1e-14
    T, a, ab, ac, det = T[live], a[live], ab[live], ac[live], det[live]
    lo = T.min(axis=1)
    hi = T.max(axis=1)
    ox, oy, oz = origin
    i0 = np.clip(np.ceil((lo[:, 0] - ox - jx) / h - 0.5), 0, nx).astype(int)
    i1 = np.clip(np.floor((hi[:, 0] - ox - jx) / h - 0.5) + 1, 0, nx).astype(int)
    j0 = np.clip(np.ceil((lo[:, 1] - oy - jy) / h - 0.5), 0, ny).astype(int)
    j1 = np.clip(np.floor((hi[:, 1] - oy - jy) / h - 0.5) + 1, 0, ny).astype(int)
    ni, nj = np.maximum(i1 - i0, 0), np.maximum(j1 - j0, 0)
    count = ni * nj
    if not int(count.sum()):
        return occ
    # Triangle-column pairs are expanded a batch at a time, never more than
    # PAIR_BUDGET at once: one large triangle on a fine grid is a million
    # columns, and expanding every triangle's columns at once is how a
    # probe once took 58 GB (ADR-635).
    columns, heights = [], []
    ends = np.cumsum(count)
    first_tri = 0
    while first_tri < len(T):
        limit = (ends[first_tri - 1] if first_tri else 0) + PAIR_BUDGET
        last = max(int(np.searchsorted(ends, limit, side="right")), first_tri + 1)
        if int(count[first_tri]) > PAIR_BUDGET:
            raise EnvelopeError(
                "one covered triangle spans more grid columns than a field may expand "
                f"({int(count[first_tri])}); give resolution= a coarser voxel")
        sub = np.arange(first_tri, last)
        c = count[sub]
        tri = np.repeat(sub, c)
        start = np.repeat(np.cumsum(c) - c, c)
        local = np.arange(int(c.sum())) - start
        rows = np.maximum(nj[tri], 1)
        ci = i0[tri] + local // rows
        cj = j0[tri] + local % rows
        qx = ox + (ci + 0.5) * h + jx - a[tri, 0]
        qy = oy + (cj + 0.5) * h + jy - a[tri, 1]
        d = det[tri]
        u = (qx * ac[tri, 1] - qy * ac[tri, 0]) / d
        v = (qy * ab[tri, 0] - qx * ab[tri, 1]) / d
        inside = (u >= 0.0) & (v >= 0.0) & (u + v <= 1.0)
        if inside.any():
            z = a[tri, 2] + u * ab[tri, 2] + v * ac[tri, 2]
            columns.append(ci[inside] * ny + cj[inside])
            heights.append(z[inside])
        first_tri = last
    if not columns:
        return occ
    column, z = np.concatenate(columns), np.concatenate(heights)
    order = np.lexsort((z, column))
    column, z = column[order], z[order]
    # Collapse coincident crossings (a ray through a shared edge).
    keep = np.ones(len(z), dtype=bool)
    keep[1:] = ~((column[1:] == column[:-1]) & (np.abs(z[1:] - z[:-1]) < 1e-6))
    column, z = column[keep], z[keep]
    # Rank of each crossing within its column; pair (0,1), (2,3), ...
    first = np.ones(len(column), dtype=bool)
    first[1:] = column[1:] != column[:-1]
    group_start = np.maximum.accumulate(np.where(first, np.arange(len(column)), 0))
    rank = np.arange(len(column)) - group_start
    enter = (rank % 2) == 0
    has_exit = np.zeros(len(column), dtype=bool)
    has_exit[:-1] = enter[:-1] & (column[1:] == column[:-1])
    zin = z[has_exit]
    zout = z[np.nonzero(has_exit)[0] + 1]
    col = column[has_exit]
    k0 = np.clip(np.ceil((zin - oz) / h - 0.5), 0, nz).astype(int)
    k1 = np.clip(np.floor((zout - oz) / h - 0.5) + 1, 0, nz).astype(int)
    good = k1 > k0
    diff = np.zeros((nx * ny, nz + 1), dtype=np.int32)
    np.add.at(diff, (col[good], k0[good]), 1)
    np.add.at(diff, (col[good], k1[good]), -1)
    occ |= (np.cumsum(diff[:, :nz], axis=1) > 0).reshape(nx, ny, nz)
    return occ


def hull_field(points, origin, h, dims):
    """Distance (mm) outside the convex hull of ``points``, by its face planes.

    The largest signed plane distance: exact over each face, so an
    enclosure's panels are flat and meet square at the hull's edges rather
    than being drawn through a voxel staircase. Zero inside.
    """

    import numpy as np
    from scipy.spatial import ConvexHull

    points = np.unique(np.round(np.asarray(points, dtype=float).reshape(-1, 3), 3), axis=0)
    try:
        equations = ConvexHull(points).equations     # n . x + d <= 0 inside
    except Exception as exc:
        raise EnvelopeError(f"the covered parts have no convex hull: {exc}") from None
    nx, ny, nz = dims
    xs = origin[0] + (np.arange(nx) + 0.5) * h
    ys = origin[1] + (np.arange(ny) + 0.5) * h
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    flat = np.stack([X.ravel(), Y.ravel()], axis=1)
    field = np.zeros((nx * ny, nz))
    zs = origin[2] + (np.arange(nz) + 0.5) * h
    # Cells a chunk at a time, so cells x planes never passes HULL_BUDGET.
    chunk = max(1, HULL_BUDGET // max(len(equations), 1))
    for start in range(0, len(flat), chunk):
        base = flat[start:start + chunk] @ equations[:, :2].T + equations[:, 3]
        for k, z in enumerate(zs):
            field[start:start + chunk, k] = np.maximum(
                np.max(base + z * equations[:, 2], axis=1), 0.0)
    return field.reshape(nx, ny, nz)


def closed_distance(occ, h, radius):
    """Distance (mm) from each voxel centre to the closing of ``occ`` by ``radius``.

    Zero inside the closed set. The half-voxel bias of a centre-to-centre
    distance is taken off, so the zero set sits on the solids' surfaces
    rather than half a cell outside them.
    """

    import numpy as np
    from scipy.ndimage import distance_transform_edt as edt

    if not occ.any():
        raise EnvelopeError("the covered parts fill no voxel; are they solids?")
    closed = occ
    if radius > 0.0:
        dilated = edt(~occ) * h <= radius + 0.5 * h
        closed = (edt(dilated) * h > radius - 0.5 * h) | occ
    field = edt(~closed) * h
    return np.where(closed, 0.0, np.maximum(field - 0.5 * h, 0.0))


def height_field(field, z0, h, level):
    """Each column's top crossing of ``field == level``, as a local ``z``.

    Columns run along the grid's third axis; ``nan`` where a column never
    comes within ``level``. The crossing is interpolated between the two
    voxel centres either side of it.
    """

    import numpy as np

    below = field <= level
    any_hit = below.any(axis=2)
    nz = field.shape[2]
    top = nz - 1 - np.argmax(below[:, :, ::-1], axis=2)
    top_c = np.clip(top, 0, nz - 1)
    above = np.clip(top_c + 1, 0, nz - 1)
    f_in = np.take_along_axis(field, top_c[..., None], axis=2)[..., 0]
    f_out = np.take_along_axis(field, above[..., None], axis=2)[..., 0]
    with np.errstate(divide="ignore", invalid="ignore"):
        frac = np.where(f_out > f_in, (level - f_in) / (f_out - f_in), 0.5)
    frac = np.clip(frac, 0.0, 1.0)
    z = z0 + (top_c + 0.5 + frac) * h
    z[top_c >= nz - 1] = np.nan
    z[~any_hit] = np.nan
    return z


# ---------------------------------------------------------------------------
# outlines


_CASES = {
    1: [("L", "B")], 2: [("B", "R")], 3: [("L", "R")], 4: [("R", "T")],
    6: [("B", "T")], 7: [("L", "T")], 8: [("T", "L")], 9: [("B", "T")],
    11: [("R", "T")], 12: [("L", "R")], 13: [("B", "R")], 14: [("L", "B")],
}


def contour_loops(phi, x0, y0, h):
    """Closed loops where the 2D field ``phi`` crosses zero (inside: ``phi > 0``).

    Marching squares over the cells between samples ``(x0 + i h, y0 + j h)``,
    the field padded outside so every loop closes; a saddle is decided by
    the cell's mean. Each loop is a list of ``(x, y)``: outer boundaries
    counter-clockwise, holes clockwise, holes listed after the loop that
    contains them is not promised -- :func:`nest_loops` pairs them.
    """

    import numpy as np

    P = np.pad(np.asarray(phi, dtype=float), 1, constant_values=-1.0)
    X0, Y0 = x0 - h, y0 - h
    nx, ny = P.shape
    inside = P > 0.0

    def point(edge, i, j):
        if edge == "B":
            a, b = (i, j), (i + 1, j)
        elif edge == "T":
            a, b = (i, j + 1), (i + 1, j + 1)
        elif edge == "L":
            a, b = (i, j), (i, j + 1)
        else:
            a, b = (i + 1, j), (i + 1, j + 1)
        fa, fb = P[a], P[b]
        t = 0.5 if fa == fb else min(max(fa / (fa - fb), 0.0), 1.0)
        return (X0 + (a[0] + t * (b[0] - a[0])) * h, Y0 + (a[1] + t * (b[1] - a[1])) * h)

    def key(edge, i, j):
        if edge == "B":
            return ("h", i, j)
        if edge == "T":
            return ("h", i, j + 1)
        if edge == "L":
            return ("v", i, j)
        return ("v", i + 1, j)

    code = (inside[:-1, :-1].astype(int) | (inside[1:, :-1].astype(int) << 1)
            | (inside[1:, 1:].astype(int) << 2) | (inside[:-1, 1:].astype(int) << 3))
    segments = []
    for i, j in zip(*np.nonzero((code > 0) & (code < 15))):
        c = int(code[i, j])
        if c in (5, 10):
            centre = (P[i, j] + P[i + 1, j] + P[i + 1, j + 1] + P[i, j + 1]) / 4.0
            if (c == 5) == (centre > 0.0):
                pairs = [("B", "R"), ("T", "L")]
            else:
                pairs = [("L", "B"), ("R", "T")]
        else:
            pairs = _CASES[c]
        for e1, e2 in pairs:
            segments.append(((key(e1, i, j), point(e1, i, j)), (key(e2, i, j), point(e2, i, j))))
    ends: dict = {}
    for index, (first, second) in enumerate(segments):
        ends.setdefault(first[0], []).append(index)
        ends.setdefault(second[0], []).append(index)
    used = [False] * len(segments)
    loops = []
    for start in range(len(segments)):
        if used[start]:
            continue
        used[start] = True
        first, second = segments[start]
        loop = [first[1], second[1]]
        start_key, current = first[0], second[0]
        while current != start_key:
            nxt = [s for s in ends.get(current, ()) if not used[s]]
            if not nxt:
                break
            used[nxt[0]] = True
            a, b = segments[nxt[0]]
            current_pt, current = (b[1], b[0]) if a[0] == current else (a[1], a[0])
            loop.append(current_pt)
        if len(loop) >= 4 and current == start_key:
            loop.pop()
            loops.append(loop)
    oriented = []
    for loop in loops:
        area = _signed_area(loop)
        depth = sum(1 for other in loops if other is not loop and _inside(loop[0], other))
        hole = depth % 2 == 1
        if (area < 0) != hole:
            loop = loop[::-1]
        oriented.append(loop)
    return oriented


def _signed_area(loop):
    return 0.5 * sum(loop[k][0] * loop[(k + 1) % len(loop)][1]
                     - loop[(k + 1) % len(loop)][0] * loop[k][1] for k in range(len(loop)))


def _inside(point, loop):
    x, y = point
    hit = False
    for k in range(len(loop)):
        (x1, y1), (x2, y2) = loop[k], loop[(k + 1) % len(loop)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def nest_loops(loops):
    """``[(outer, [holes...]), ...]``: each hole with the outer loop round it."""

    outers = [loop for loop in loops if _signed_area(loop) > 0]
    holes = [loop for loop in loops if _signed_area(loop) < 0]
    result = [(outer, []) for outer in outers]
    for hole in holes:
        best = None
        for index, (outer, _list) in enumerate(result):
            if _inside(hole[0], outer):
                if best is None or abs(_signed_area(outer)) < abs(_signed_area(result[best][0])):
                    best = index
        if best is not None:
            result[best][1].append(hole)
    return result


def _decimate(loop, spacing):
    kept = [loop[0]]
    for p in loop[1:]:
        if math.dist(p, kept[-1]) >= spacing:
            kept.append(p)
    if len(kept) > 3 and math.dist(kept[0], kept[-1]) < spacing * 0.5:
        kept.pop()
    return kept


# ---------------------------------------------------------------------------
# where the screws go


def choose_sites(candidates, count, *, start=(), spacing_weight=1.0, length_weight=0.4):
    """``count`` well-spread sites from ``[(x, y, length), ...]`` (or ``(x, y, z, length)``).

    Farthest-point sampling, started at the candidate farthest from the
    candidates' centre (or from the indices in ``start``, kept first), each
    next site the one farthest from those chosen; a long boss is penalised
    by ``length_weight`` per mm, so a short reach to the frame wins a near
    tie. Returns the chosen indices.
    """

    if not candidates or count <= 0:
        return []
    dims = len(candidates[0]) - 1
    chosen = list(start)
    if not chosen:
        centre = [sum(c[d] for c in candidates) / len(candidates) for d in range(dims)]
        chosen = [max(range(len(candidates)),
                      key=lambda k: math.dist(candidates[k][:dims], centre)
                      - length_weight * candidates[k][dims])]
    while len(chosen) < min(count, len(candidates)):
        best, best_score = None, -math.inf
        for k, candidate in enumerate(candidates):
            if k in chosen:
                continue
            spread = min(math.dist(candidate[:dims], candidates[c][:dims]) for c in chosen)
            score = spacing_weight * spread - length_weight * candidate[dims]
            if score > best_score:
                best, best_score = k, score
        chosen.append(best)
    return chosen


# ---------------------------------------------------------------------------
# the plan


def _vec(value, n=3):
    return [float(v) for v in list(value)[:n]]


def _pose_budget(steps, sets):
    """Refuse a motion whose sampled poses would pass MAX_TRIANGLES, before copying."""

    count = steps * sum(len(t) for t in sets)
    if count > MAX_TRIANGLES:
        raise EnvelopeError(
            f"a declared motion samples {steps} poses of {count // steps} triangles, "
            f"{count} in all, more than one envelope reads ({MAX_TRIANGLES}); sweep a "
            "shorter range or a simpler part")


class _Grid:
    __slots__ = ("origin", "h", "dims")

    def __init__(self, origin, h, dims):
        self.origin, self.h, self.dims = origin, h, dims


def _grid_for(low, high, h_wanted, pad):
    span = [high[i] - low[i] + 2 * pad for i in range(3)]
    h = h_wanted
    if h is None:
        volume = span[0] * span[1] * span[2]
        h = max(MIN_RESOLUTION_MM, (volume / 4.0e6) ** (1.0 / 3.0))
    while True:
        dims = [max(int(math.ceil(span[i] / h)), 4) for i in range(3)]
        if dims[0] * dims[1] * dims[2] <= MAX_VOXELS:
            break
        h *= 1.15
    if h > MAX_RESOLUTION_MM and h_wanted is None:
        h = MAX_RESOLUTION_MM
        dims = [max(int(math.ceil(span[i] / h)), 4) for i in range(3)]
        if dims[0] * dims[1] * dims[2] > MAX_VOXELS:
            raise EnvelopeError(
                "the covered parts span {:.0f} x {:.0f} x {:.0f} mm, more than one field "
                "holds at {:g} mm; cover less with one panel".format(*span, h))
    origin = [low[i] - pad for i in range(3)]
    return _Grid(origin, h, dims)


def build_panel_plan(spec: Mapping[str, Any], build: Callable[[Mapping[str, Any]], Any],
                     plan_of: Callable[[Mapping[str, Any]], Any] | None = None):
    """Every piece, fastener and pilot of one ``part.panel``, built once.

    ``spec`` is the panel's payload argument; ``build`` turns a nested part
    payload into a kernel shape (the worker's memoised builder). Returns a
    dict: ``pieces`` (name -> world solid), ``fasteners`` (name -> list of
    rows with the head seat, axis, roll and the boss facts), ``pilots``
    (one compound of the frame's tap-drill holes, or None) and ``facts``
    (what the field and the outline measured).
    """

    import numpy as np
    import FreeCAD as App
    import Part
    from scipy import ndimage

    envelope = spec["envelope"]
    clearance = float(envelope["clearance"])
    # "hull": the rolling ball at infinity, the convex hull. What an enclosure
    # round an open frame is: a finite ball always dips into an open face.
    hull = envelope["radius"] == "hull"
    radius = 0.0 if hull else float(envelope["radius"])
    thickness = float(spec["thickness"])
    e1, e2, s = panel_frame(spec["side"])
    R = np.array([e1, e2, s])            # world -> local rows
    to_world = App.Matrix(e1[0], e2[0], s[0], 0.0, e1[1], e2[1], s[1], 0.0,
                          e1[2], e2[2], s[2], 0.0, 0.0, 0.0, 0.0, 1.0)

    def local(points):
        return np.asarray(points, dtype=float) @ R.T

    def triangles_of(shape, deflection):
        solids = list(shape.Solids)
        if not solids:
            raise EnvelopeError("a covered value has no solid; cover solids, not faces or wires")
        sets = []
        for solid in solids:
            points, facets = solid.tessellate(deflection)
            if not facets:
                continue
            vertices = np.array([[p.x, p.y, p.z] for p in points], dtype=float)
            sets.append(vertices[np.array(facets, dtype=int)])
        return sets

    def placed(sets, rotation=None, translation=None):
        out = []
        for tris in sets:
            flat = tris.reshape(-1, 3)
            if rotation is not None:
                flat = (flat - rotation[0]) @ rotation[1].T + rotation[0]
            if translation is not None:
                flat = flat + translation
            out.append(flat.reshape(-1, 3, 3))
        return out

    def poses(entry, sets):
        """The covered sets, at every sampled pose of a declared motion."""

        kind = str(entry.get("kind") or "hinge")
        lo, hi = (float(v) for v in entry["range"])
        if kind == "hinge":
            origin = np.array(_vec(entry["origin"]))
            axis = np.array(_unit(entry["axis"], "motion axis"))
            steps = max(2, int(math.ceil(abs(hi - lo) / SWEEP_STEP_DEGREES)) + 1)
            _pose_budget(steps, sets)
            result = []
            for angle in np.linspace(lo, hi, steps):
                t = math.radians(angle)
                K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]],
                              [-axis[1], axis[0], 0]])
                rot = np.eye(3) + math.sin(t) * K + (1 - math.cos(t)) * K @ K
                result += placed(sets, rotation=(origin, rot))
            return result
        direction = np.array(_unit(entry["direction"], "motion direction"))
        steps = max(2, int(math.ceil(abs(hi - lo) / 2.0)) + 1)
        _pose_budget(steps, sets)
        result = []
        for offset in np.linspace(lo, hi, steps):
            result += placed(sets, translation=direction * offset)
        return result

    def shape_sets(value, deflection):
        return triangles_of(build(value), deflection)

    # -- what is covered, in the panel's frame -----------------------------
    import json

    def same(a, b):
        return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)

    covered_world, covered_is_frame = [], []
    rough = 0.3
    frame_solid = build(spec["frame"]) if spec.get("frame") is not None else None

    def part_of_frame(value):
        """A covered value that is the frame, or most of it lies inside it (a keel the
        frame was fused from): bosses may land on it."""

        if frame_solid is None:
            return False
        if same(value, spec["frame"]):
            return True
        own = build(value)
        volume = abs(float(own.Volume))
        try:
            return volume > 0 and abs(float(own.common(frame_solid).Volume)) >= 0.8 * volume
        except Exception:
            return False

    for value in envelope["over"]:
        sets = shape_sets(value, rough)
        covered_world += sets
        covered_is_frame += [part_of_frame(value)] * len(sets)
    for entry in envelope.get("motion") or []:
        sets = poses(entry, shape_sets(entry["shape"], rough))
        covered_world += sets
        covered_is_frame += [False] * len(sets)
    # The designed form (ADR-679): wrapped, never a blocker or a frame.
    form_world = []
    for value in envelope.get("form") or []:
        form_world += shape_sets(value, rough)
    triangles = sum(len(t) for t in covered_world) + sum(len(t) for t in form_world)
    if triangles > MAX_TRIANGLES:
        raise EnvelopeError(
            f"the covered parts and their motion are {triangles} triangles, more than one "
            f"envelope reads ({MAX_TRIANGLES}); cover fewer parts, or sweep a shorter range")
    covered = [local(t.reshape(-1, 3)).reshape(-1, 3, 3) for t in covered_world]
    formed = [local(t.reshape(-1, 3)).reshape(-1, 3, 3) for t in form_world]
    allpts = np.concatenate([t.reshape(-1, 3) for t in covered + formed])
    low, high = allpts.min(axis=0), allpts.max(axis=0)
    within = spec.get("within")
    pad = radius + clearance + thickness + 8.0
    grid = _grid_for(list(low), list(high), envelope.get("resolution"), pad)
    h = grid.h
    _SANE_DIAGONAL[0] = 1.5 * math.sqrt(sum((d * h) ** 2 for d in grid.dims)) + 100.0
    occ = np.zeros(grid.dims, dtype=bool)
    if hull:
        field = hull_field(allpts, grid.origin, h, grid.dims)
    else:
        for tris in covered + formed:
            occ |= occupancy(tris, grid.origin, h, grid.dims)
        field = closed_distance(occ, h, radius)
    inner = height_field(field, grid.origin[2], h, clearance)
    nx, ny, _nz = grid.dims
    xs = grid.origin[0] + (np.arange(nx) + 0.5) * h
    ys = grid.origin[1] + (np.arange(ny) + 0.5) * h
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    valid = np.isfinite(inner)
    if not valid.any():
        raise EnvelopeError("no part of the envelope faces the panel's side")
    # Slope of the inner face from side.
    filled = _fill(inner, valid)
    gx, gy = np.gradient(filled, h)
    if formed:
        # A designed form is smooth; its voxel stairs are not. Its slope is
        # read off the smoothed face, so a max_angle= edge runs clean rather
        # than ragged along every stair (ADR-679).
        sx, sy = np.gradient(ndimage.gaussian_filter(filled, FORM_SMOOTH_MM / h), h)
        slope = np.degrees(np.arctan(np.hypot(sx, sy)))
    else:
        slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    region = valid & (slope <= float(spec["max_angle"]))
    # A sudden drop (the face jumps to a lower part) is an edge, not a slope.
    region &= _no_cliff(filled, valid, h, thickness * 2.0)
    if within is not None:
        world = _to_world_points(X, Y, filled, R)
        lo_w, hi_w = np.array(_vec(within[0])), np.array(_vec(within[1]))
        lo_w, hi_w = np.minimum(lo_w, hi_w), np.maximum(lo_w, hi_w)
        region &= np.all((world >= lo_w) & (world <= hi_w), axis=-1)
    # -- openings ------------------------------------------------------------
    outer_face = filled + thickness * np.sqrt(1.0 + gx * gx + gy * gy)
    open_mask = np.zeros_like(region)
    openings_facts, keepouts = [], []
    for entry in spec.get("openings") or []:
        hole = _opening_mask(entry, X, Y, filled, outer_face, R, grid, h, shape_sets, poses,
                             local, occupancy, closed_distance, keepouts)
        openings_facts.append(int(hole.sum()))
        open_mask |= hole
    region &= ~open_mask
    # Clean: drop specks, smooth the edge.
    region = ndimage.binary_opening(region, iterations=2)
    region = ndimage.binary_closing(region, iterations=2) & ~open_mask & valid
    labels, count = ndimage.label(region)
    if count == 0:
        raise EnvelopeError(
            "the panel's region is empty: nothing of the envelope faces side= within "
            "max_angle (and within=), or the openings remove all of it")
    sizes = ndimage.sum(region, labels, range(1, count + 1))
    keep = [k + 1 for k, size in enumerate(sizes) if size >= max(20, 0.05 * max(sizes))]
    region = np.isin(labels, keep)
    inset = float(spec.get("edge_inset") or 0.0)
    phi = (ndimage.distance_transform_edt(region) - ndimage.distance_transform_edt(~region)) * h
    phi = ndimage.gaussian_filter(phi, max(1.0, FORM_SMOOTH_MM / h) if formed else 1.0) \
        - 0.5 * h - inset
    # -- the inner face as a B-spline, over the region's box -----------------
    rows = np.nonzero(region.any(axis=1))[0]
    cols = np.nonzero(region.any(axis=0))[0]
    margin = int(math.ceil((thickness + 3.0) / h)) + 2
    i0, i1 = max(rows[0] - margin, 0), min(rows[-1] + margin, nx - 1)
    j0, j1 = max(cols[0] - margin, 0), min(cols[-1] + margin, ny - 1)
    surface_z = _smooth_cover(filled, region, h, radius)
    stride = max(1, int(math.ceil(max(i1 - i0, j1 - j0) / 40.0)))
    sub_i = list(range(i0, i1 + 1, stride))
    sub_j = list(range(j0, j1 + 1, stride))
    if sub_i[-1] != i1:
        sub_i.append(i1)
    if sub_j[-1] != j1:
        sub_j.append(j1)
    if len(sub_i) < 4 or len(sub_j) < 4:
        raise EnvelopeError("the panel's region is too small to draw; widen it")
    zgrid = surface_z[np.ix_(sub_i, sub_j)]
    surface = Part.BSplineSurface()
    xs_s, ys_s = xs[sub_i], ys[sub_j]
    surface.approximate(Points=[[float(v) for v in row] for row in zgrid], DegMin=3, DegMax=3,
                        Continuity=2, Tolerance=max(0.05, 0.1 * h),
                        X0=float(xs_s[0]), dX=float(xs_s[1] - xs_s[0]),
                        Y0=float(ys_s[0]), dY=float(ys_s[1] - ys_s[0]))
    # approximate() needs a uniform grid; snap the tail to it.
    # -- the outline, trimmed on the surface, thickened ----------------------
    # The surface is a height field over the local plane, so its parameters
    # are the plane's own x and y: an outline contoured there is its pcurve.
    top = float(np.nanmax(outer_face[region])) + 5.0
    bottom = float(np.nanmin(filled[region])) - 5.0
    loops = contour_loops(phi, float(xs[0]), float(ys[0]), h)
    spacing = max(4.0 * h, 4.0)
    # With a skirt the panel overhangs its own outline by the skirt's wall, so
    # the skirt's top runs inside the panel's wall: a lid over its walls, one
    # solid without any face of one lying on a face of the other.
    flange = spec.get("flange")
    grow = (SKIRT_STEP_MM + 0.6 * h + 1.5 * thickness) if flange else 0.0
    grown_outers = [outer for outer, _h in nest_loops(
        contour_loops(phi + grow, float(xs[0]), float(ys[0]), h))] if grow else []
    faces, planar, drawn_already = [], [], []
    for outer, holes in nest_loops(loops):
        if abs(_signed_area(outer)) < 25.0:
            continue
        holes = [hole for hole in holes if abs(_signed_area(hole)) >= 4.0]
        drawn = outer
        if grow:
            around = [g for g in grown_outers if _inside(outer[0], g)]
            drawn = min(around, key=lambda g: abs(_signed_area(g))) if around else outer
            if any(drawn is used for used in drawn_already):
                planar.append((outer, holes))     # two outlines grown into one face
                continue
            drawn_already.append(drawn)
        face = Part.Face(surface, _param_wire(drawn, surface, spacing, App, Part))
        if holes:
            face.cutHoles([_param_wire(hole, surface, spacing, App, Part) for hole in holes])
        face.validate()
        faces.append(face)
        planar.append((outer, holes))
    if not faces:
        raise EnvelopeError("the panel's outline is too small to draw; widen its region")
    probe = faces[0]
    u_mid = sum(probe.ParameterRange[:2]) / 2.0
    v_mid = sum(probe.ParameterRange[2:]) / 2.0
    sign = 1.0 if probe.normalAt(u_mid, v_mid).z > 0 else -1.0
    solids = []
    for face in faces:
        thick = face.makeOffsetShape(sign * thickness, 1e-3, fill=True)
        if not thick.isValid() or not thick.Solids:
            raise EnvelopeError(
                f"the inner face could not be thickened by {thickness:g} mm; its form curves "
                "tighter than the wall: raise radius= or lower thickness=")
        solids += [_sound(solid, "the thickened panel") for solid in thick.Solids]
    body_local = solids[0] if len(solids) == 1 else Part.makeCompound(solids)
    gx_s, gy_s = np.gradient(surface_z, h)
    outer_s = surface_z + thickness * np.sqrt(1.0 + gx_s * gx_s + gy_s * gy_s)
    # -- the frame under the panel, per column (for the skirt and the bosses)
    frame_value = spec.get("frame")
    frame_shape = frame_z = column_room = None
    if frame_value is not None:
        frame_shape = build(frame_value)
        frame_occ = np.zeros(grid.dims, dtype=bool)
        for tris in triangles_of(frame_shape, rough):
            frame_occ |= occupancy(local(tris.reshape(-1, 3)).reshape(-1, 3, 3), grid.origin,
                                   h, grid.dims)
        nz = grid.dims[2]
        zc = grid.origin[2] + (np.arange(nz) + 0.5) * h
        under = frame_occ & (zc[None, None, :] < surface_z[..., None])
        top_k = np.where(under, np.arange(nz)[None, None, :], -1).max(axis=2)
        frame_z = np.where(top_k >= 0, grid.origin[2] + (top_k + 1.0) * h, np.nan)
        # A skirt runs beside the frame, never into it: the frame keeps it out too.
        if frame_occ.any():
            keepouts.append((ndimage.distance_transform_edt(~frame_occ) * h - 0.5 * h, 0.3))
        # How close each column, from the frame up to the panel, passes the
        # covered parts that are not the frame: a boss there must clear them.
        occ_free = np.zeros(grid.dims, dtype=bool)
        for tris, is_frame in zip(covered, covered_is_frame):
            if not is_frame:
                occ_free |= occupancy(tris, grid.origin, h, grid.dims)
        room = (ndimage.distance_transform_edt(~occ_free) * h - 0.5 * h) if occ_free.any() \
            else np.full(grid.dims, np.inf)
        between = (np.arange(nz)[None, None, :] > top_k[..., None]) & \
            (zc[None, None, :] < surface_z[..., None])
        column_room = np.where(between, room, np.inf).min(axis=2)
    # -- edge: a skirt down the outline ---------------------------------------
    flange = spec.get("flange")
    flange_facts = None
    skirted = False
    bare_local = body_local
    if flange:
        depth = BOSS_REACH_MM if flange == "frame" else float(flange)
        if flange == "frame" and frame_z is None:
            raise EnvelopeError('flange="frame" needs frame=: the part the skirt comes down to')
        # The wall's top is tucked under the panel's overhang by the least that
        # joins the two: the more it tucks, the more it eats into the clearance at
        # the rim; each failed attempt costs one more B-spline fuse (seconds).
        for tuck in (0.0, 0.5, 1.0):
            walls, facts_now = _skirt(planar, surface_z, outer_s,
                                      frame_z if flange == "frame" else None, field, xs, ys,
                                      grid, clearance, thickness, depth, App, Part, np,
                                      keepouts=keepouts,
                                      tuck=tuck)
            walls = [wall for wall in walls if _wall_sane(wall)]
            flange_facts = facts_now
            if not walls:
                break
            # The wall overlaps the panel's overhang by volume: a plain fuse.
            fused = body_local.fuse(walls)
            if len(fused.Solids) == 1 and fused.isValid() and \
                    fused.BoundBox.DiagonalLength <= _SANE_DIAGONAL[0]:
                body_local = _refined(fused)
                skirted = True
                flange_facts = [dict(row, tuck_mm=tuck) for row in flange_facts]
                break
        else:
            flange_facts = (flange_facts or []) + [
                {"depth_mm": 0.0, "reason": "the skirt did not join the panel; it is left off"}]
    screw = spec.get("screw")
    per_piece = int(spec.get("screws") or 0)
    blockers = [tris for tris, is_frame in zip(covered_world, covered_is_frame) if not is_frame]

    def cut_and_mount(local_body, with_skirt):
        body = local_body.copy()
        body.transformShape(to_world, False, False)
        # -- seams ------------------------------------------------------------
        pieces = _split(body, spec.get("seams") or [], float(spec.get("seam_gap") or 0.6),
                        App, Part)
        # -- mounts -----------------------------------------------------------
        if frame_shape is None or screw is None or per_piece <= 0:
            return {name: [] for name in pieces}, [], pieces
        return _mount(pieces, frame_shape, screw, per_piece, phi, surface_z, outer_s, frame_z,
                      column_room, with_skirt, xs, ys, R, s, h, spec,
                      np.concatenate(blockers) if blockers else None, App, Part, np, ndimage,
                      taken=_taken_screws(spec, plan_of))

    try:
        fasteners, pilots, pieces = cut_and_mount(body_local, skirted)
    except EnvelopeError as exc:
        # A skirt the fuse accepted can still be refused by the next boolean;
        # the panel is drawn without it rather than not at all, and says so.
        if not skirted or "kernel refused" not in str(exc):
            raise
        fasteners, pilots, pieces = cut_and_mount(bare_local, False)
        flange_facts = (flange_facts or []) + [
            {"depth_mm": 0.0, "reason": "the skirt was refused by the seam or boss booleans; "
                                        "it is left off"}]
    max_piece = spec.get("max_piece")
    if max_piece is not None:
        bed = sorted(float(v) for v in max_piece)
        for name, solid in pieces.items():
            box = solid.optimalBoundingBox()
            size = sorted([box.XLength, box.YLength, box.ZLength])
            if any(a > b + 1e-6 for a, b in zip(size, bed)):
                raise EnvelopeError(
                    f"piece {name} is {box.XLength:.0f} x {box.YLength:.0f} x "
                    f"{box.ZLength:.0f} mm, larger than max_piece={list(max_piece)}; add a seam")
    facts = {
        "resolution_mm": round(h, 3),
        "grid": list(grid.dims),
        "region_area_mm2": round(float(region.sum()) * h * h, 1),
        "openings_cells": openings_facts,
        "gap_designed_mm": clearance,
    }
    if formed:
        facts["form"] = len(formed)
    if flange_facts:
        facts["flange"] = flange_facts
    return {"pieces": pieces, "fasteners": fasteners,
            "pilots": Part.makeCompound(pilots) if pilots else None, "facts": facts}


def _fill(values, valid):
    """``values`` with every invalid cell given its nearest valid cell's value."""

    import numpy as np
    from scipy import ndimage

    if valid.all():
        return values.copy()
    _d, (ii, jj) = ndimage.distance_transform_edt(~valid, return_indices=True)
    return np.where(valid, values, values[ii, jj])


def _grow(mask, cells):
    from scipy import ndimage

    return ndimage.binary_dilation(mask, iterations=max(1, cells))


def _no_cliff(z, valid, h, drop):
    """Cells not beside a neighbour more than ``drop`` lower or higher."""

    import numpy as np

    ok = np.ones_like(valid)
    for axis in (0, 1):
        for shift in (1, -1):
            other = np.roll(z, shift, axis=axis)
            ok &= np.abs(other - z) <= drop + h
    return ok


def _smooth_cover(z, region, h, radius):
    """The inner face smoothed without coming closer to what it covers.

    Outside the region the face is carried on from its nearest cell inside,
    so the edge of the region is not a cliff the surface has to ring over.
    A Gaussian of a third of the rolling radius (at least a cell and a
    half) takes the voxels' staircase and the small parts' bumps off;
    whatever it lowered a crest by is put back, spread and blurred, twice,
    so the smoothed face never sits inside the clearance it was drawn at.
    """

    import numpy as np
    from scipy import ndimage

    raw = _fill(z, region)
    sigma = max(1.5, min(radius / 3.0, 15.0) / h)
    width = 2 * int(math.ceil(sigma)) + 1
    smooth = ndimage.gaussian_filter(raw, sigma)
    for _ in range(3):
        deficit = np.maximum(raw - smooth, 0.0)
        deficit[~region] = 0.0
        if deficit.max() <= 0.02:
            break
        smooth = smooth + ndimage.gaussian_filter(ndimage.maximum_filter(deficit, size=width),
                                                  sigma / 2.0)
    return smooth


def _to_world_points(X, Y, Z, R):
    import numpy as np

    stack = np.stack([X, Y, Z], axis=-1)
    return stack @ R


def _loop_points(loop, spacing):
    """The loop thinned to ``spacing`` and corner-cut twice (Chaikin).

    Corner cutting keeps a simple polygon simple and rounds its corners, so
    the periodic spline drawn through the points never overshoots a sharp
    corner into a loop of its own -- the self-intersecting wire a box
    panel's outline otherwise makes.
    """

    points = _decimate(loop, spacing)
    if len(points) < 6:
        points = list(loop)
    for _ in range(2):
        cut = []
        for k in range(len(points)):
            (x0, y0), (x1, y1) = points[k], points[(k + 1) % len(points)]
            cut.append((0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1))
            cut.append((0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1))
        points = cut
    return points


def _param_wire(loop, surface, spacing, App, Part):
    """A closed periodic B-spline through ``loop``, drawn on ``surface``."""

    curve = Part.Geom2d.BSplineCurve2d()
    curve.interpolate([App.Base.Vector2d(x, y) for x, y in _loop_points(loop, spacing)],
                      PeriodicFlag=True)
    return Part.Wire([curve.toShape(surface)])


def _opening_mask(entry, X, Y, inner, outer, R, grid, h, shape_sets, poses, local,
                  occupancy_fn, distance_fn, keepouts=None):
    """The columns an opening takes out: where its keep-out meets the panel."""

    import numpy as np

    stack_in = np.stack([X, Y, inner], axis=-1)
    stack_out = np.stack([X, Y, outer], axis=-1)
    if "cone" in entry:
        apex, axis, half = entry["cone"]
        apex = np.array(_vec(apex)) @ R.T
        axis = np.array(_unit(axis, "opening cone axis")) @ R.T
        cos_half = math.cos(math.radians(float(half)))
        mask = np.zeros(X.shape, dtype=bool)
        for t in np.linspace(0.0, 1.0, 5):
            p = stack_in + t * (stack_out - stack_in) - apex
            along = p @ axis
            length = np.linalg.norm(p, axis=-1)
            mask |= (along > 0) & (along >= cos_half * np.maximum(length, 1e-9))
        return mask
    if "at" in entry:
        centre = np.array(_vec(entry["at"])) @ R.T
        r = float(entry.get("radius") or 5.0)
        return np.hypot(X - centre[0], Y - centre[1]) <= r
    sets = shape_sets(entry["around"], 0.3)
    if entry.get("motion"):
        sets = poses(entry["motion"], sets)
    sets = [local(t.reshape(-1, 3)).reshape(-1, 3, 3) for t in sets]
    occ = np.zeros(grid.dims, dtype=bool)
    for tris in sets:
        occ |= occupancy_fn(tris, grid.origin, h, grid.dims)
    if not occ.any():
        return np.zeros(X.shape, dtype=bool)
    reach = distance_fn(occ, h, 0.0)
    keep_out = float(entry.get("clearance") or 2.0)
    nz = grid.dims[2]
    mask = np.zeros(X.shape, dtype=bool)
    for t in np.linspace(0.0, 1.0, 6):
        z = inner + t * (outer - inner)
        k = np.clip(np.floor((z - grid.origin[2]) / h - 0.5).astype(int), 0, nz - 1)
        near = np.take_along_axis(reach, k[..., None], axis=2)[..., 0]
        mask |= near <= keep_out
    if keepouts is not None:
        keepouts.append((reach, keep_out))
    return mask


def _sample2d(values, xs, ys, x, y):
    """Bilinear samples of a grid field at points ``(x, y)``."""

    import numpy as np
    from scipy import ndimage

    h = float(xs[1] - xs[0])
    coords = np.vstack([(np.asarray(x) - xs[0]) / h, (np.asarray(y) - ys[0]) / h])
    return ndimage.map_coordinates(values, coords, order=1, mode="nearest")


def _skirt(planar, surface_z, outer_s, frame_z, field, xs, ys, grid, clearance, thickness,
           depth, App, Part, np, tuck=0.6, keepouts=()):
    """A wall round each outline, hanging from the panel down to the frame.

    The skirt is the panel's return edge: ``thickness`` thick just outside
    the outline, from inside the panel's wall down to the frame under it
    (``frame_z``, the frame's surface per column, a ``seam`` above it) or
    ``depth`` mm, whichever is less -- and never into the clearance band:
    at each point of the outline it stops where the envelope's field drops
    below the clearance, so over a box it reaches the frame, and over a
    form that curves under its rim it is short or absent. Built from four
    ruled faces through the same points, sewn: no boolean.
    """

    from scipy import ndimage

    h = grid.h
    spacing = max(4.0 * h, 4.0)
    walls, facts = [], []
    for outer, _holes in planar:
        pts = _loop_points(outer, spacing)
        n = len(pts)
        if n < 6:
            continue
        P = np.array(pts, dtype=float)
        tangent = np.roll(P, -1, axis=0) - np.roll(P, 1, axis=0)
        length = np.linalg.norm(tangent, axis=1, keepdims=True)
        normal = np.stack([tangent[:, 1], -tangent[:, 0]], axis=1) / np.maximum(length, 1e-9)
        # The outline is on the envelope where it turns max_angle from side;
        # straight down from there a vertical side is a little nearer than
        # the clearance, so the wall stands just outside it.
        P = P + normal * (SKIRT_STEP_MM + 0.6 * h)
        Q = P + normal * thickness
        rim = _sample2d(surface_z, xs, ys, P[:, 0], P[:, 1])
        # The wall's top edge is tucked just inside the outline, at the
        # middle of the panel's own wall: the two overlap by volume, and no
        # face of one lies nearly on a face of the other (which is what makes
        # the fuse, and the seam cut after it, fail).
        P_top = P - normal * tuck
        Q_top = P_top + normal * thickness

        def midwall(points):
            return 0.5 * (_sample2d(surface_z, xs, ys, points[:, 0], points[:, 1])
                          + _sample2d(outer_s, xs, ys, points[:, 0], points[:, 1]))

        top_in, top_out = midwall(P_top), midwall(Q_top)
        # How far down the wall may hang, column by column.
        mid = P + normal * 0.1
        steps = np.arange(0.0, depth + h, 0.5 * h)
        zs = rim[:, None] - steps[None, :]
        coords = np.vstack([
            np.repeat((mid[:, 0] - grid.origin[0]) / h - 0.5, len(steps)),
            np.repeat((mid[:, 1] - grid.origin[1]) / h - 0.5, len(steps)),
            ((zs - grid.origin[2]) / h - 0.5).ravel()])
        f = ndimage.map_coordinates(field, coords, order=1, mode="nearest").reshape(zs.shape)
        bad = f < clearance - 0.25 * h
        # ...and never into what an opening or the frame keeps out, across the
        # wall's whole thickness (its inner face, its middle and its outer face).
        for across in (0.1, 0.5 * thickness, thickness - 0.1):
            line = P + normal * across
            here = np.vstack([
                np.repeat((line[:, 0] - grid.origin[0]) / h - 0.5, len(steps)),
                np.repeat((line[:, 1] - grid.origin[1]) / h - 0.5, len(steps)),
                coords[2]])
            for reach, keep_out in keepouts:
                near = ndimage.map_coordinates(reach, here, order=1, mode="nearest")
                bad |= near.reshape(zs.shape) <= keep_out + 0.25 * h
        first_bad = np.where(bad.any(axis=1), np.argmax(bad, axis=1), len(steps) - 1)
        allowed = steps[np.maximum(first_bad - 1, 0)]
        bottom = rim - np.minimum(allowed, depth)
        if frame_z is not None:
            under = _sample2d(np.nan_to_num(frame_z, nan=-1e9), xs, ys, mid[:, 0], mid[:, 1])
            seated = under > -1e8
            if not seated.any():
                facts.append({"depth_mm": 0.0, "reason": "no frame under the outline"})
                continue
            # A voxel's top is the frame's face to within half a cell: stand clear of it.
            bottom = np.maximum(bottom, np.where(seated, under + 0.5 * h + 0.2, bottom))
            # Where the outline runs past the frame, carry the hem on from
            # the nearest points that sit on it, round the loop.
            if not seated.all():
                index = np.arange(n)
                known = index[seated]
                bottom = np.where(seated, bottom, np.interp(index, known, bottom[seated],
                                                            period=n))
        # Smooth the hem along the loop so it reads as one line.
        bottom = ndimage.uniform_filter1d(bottom, size=5, mode="wrap")
        hang = top_in - bottom
        if np.median(hang) < max(2.0 * thickness, 3.0):
            facts.append({"depth_mm": 0.0, "reason": "the form curves under the rim"})
            continue
        bottom = np.minimum(bottom, top_in - 1.0)

        def curve(xy, z):
            c = Part.BSplineCurve()
            c.interpolate([App.Vector(float(a), float(b), float(c_)) for (a, b), c_ in zip(xy, z)],
                          PeriodicFlag=True)
            return c.toShape()

        ti, bi = curve(P_top, top_in), curve(P, bottom)
        to, bo = curve(Q_top, top_out), curve(Q, bottom)
        faces = [Part.makeRuledSurface(ti, bi), Part.makeRuledSurface(to, bo),
                 Part.makeRuledSurface(ti, to), Part.makeRuledSurface(bi, bo)]
        try:
            solid = Part.Solid(Part.Shell(faces))
            if solid.Volume < 0:
                solid.reverse()
        except Exception:
            facts.append({"depth_mm": 0.0, "reason": "the wall could not be closed"})
            continue
        if not solid.isValid():
            solid.fix(1e-4, 1e-4, 1e-3)
        walls.append(solid)
        facts.append({"depth_mm": round(float(np.median(hang)), 2),
                      "min_depth_mm": round(float(hang.min()), 2)})
    return walls, facts
def _split(body, seams, gap, App, Part):
    """The panel cut at its seams: ``{"p0": solid, ...}`` in seam-cell order."""

    cells = [[]]
    for group in seams:
        normal = _unit(group["normal"], "seam normal")
        positions = sorted(float(v) for v in group["at"])
        bands = [(None, positions[0])] + [(positions[k], positions[k + 1])
                                         for k in range(len(positions) - 1)] + [(positions[-1], None)]
        cells = [cell + [(normal, low, high)] for cell in cells for low, high in bands]
    box = body.BoundBox
    reach = box.DiagonalLength + 10.0
    centre = box.Center
    pieces = {}
    for index, cell in enumerate(cells):
        piece = body
        for normal, low, high in cell:
            n = App.Vector(*normal)
            here = centre.dot(n)
            lo = (low + gap / 2.0) if low is not None else here - reach
            hi = (high - gap / 2.0) if high is not None else here + reach
            if hi <= lo:
                raise EnvelopeError("two seams lie closer than their gap")
            # A slab lo <= n.p <= hi, wide enough to hold the whole body.
            slab = Part.makeBox(2 * reach, 2 * reach, hi - lo, App.Vector(-reach, -reach, lo))
            slab.Placement = App.Placement(centre - n * here,
                                           App.Rotation(App.Vector(0, 0, 1), n))
            try:
                piece = piece.common(slab)
            except Exception as exc:
                raise EnvelopeError(
                    f"piece {name}: the kernel refused the seam cut "
                    f"({str(exc).splitlines()[0]}); move the seam a few mm or drop flange=") from None
        name = f"p{index}"
        if not piece.Solids:
            raise EnvelopeError(
                f"piece {name} of the seams {[(list(g['normal']), list(g['at'])) for g in seams]} "
                "is empty: a seam lies outside the panel")
        import os
        if len(piece.Solids) > 1 and os.environ.get("CADEX_ENVELOPE_KEEP_ISLANDS"):
            pieces[name] = piece
            continue
        solids = sorted(piece.Solids, key=lambda s: -abs(s.Volume))
        if len(solids) > 1:
            # A sliver a seam or the region's rim left beside the piece is
            # dropped, as the region's own specks are (ADR-679).
            largest = abs(solids[0].Volume)
            solids = [s for s in solids if abs(s.Volume) >= SPECK_FRACTION * largest]
        if len(solids) > 1:
            where = "; ".join(
                f"{round(abs(s.Volume))} mm3 at x {s.BoundBox.XMin:.0f}..{s.BoundBox.XMax:.0f}, "
                f"y {s.BoundBox.YMin:.0f}..{s.BoundBox.YMax:.0f}, "
                f"z {s.BoundBox.ZMin:.0f}..{s.BoundBox.ZMax:.0f}" for s in solids)
            raise EnvelopeError(
                f"piece {name} falls apart into {len(solids)} solids ({where}): its region "
                "is not one patch -- an opening, max_angle= or within= parts it; narrow "
                "within= to one patch, or add a seam between them")
        pieces[name] = _sound(solids[0], f"piece {name}")
    return pieces


def piece_index(points, seams):
    """Which seam cell each world point falls in, numbered as :func:`_split` names them.

    ``points`` is an ``(..., 3)`` array. Cells are the product of each
    seam group's bands, the first group varying slowest; a point inside a
    seam's gap belongs to the band it would join.
    """

    import numpy as np

    index = np.zeros(points.shape[:-1], dtype=int)
    for group in seams:
        normal = np.array(_unit(group["normal"], "seam normal"))
        positions = sorted(float(v) for v in group["at"])
        band = np.searchsorted(np.array(positions), points @ normal)
        index = index * (len(positions) + 1) + band
    return index


def _seam_distance(points, seams):
    """Each point's distance to the nearest seam plane (inf with none)."""

    import numpy as np

    best = np.full(points.shape[:-1], np.inf)
    for group in seams:
        normal = np.array(_unit(group["normal"], "seam normal"))
        along = points @ normal
        for position in group["at"]:
            best = np.minimum(best, np.abs(along - float(position)))
    return best


def _mount(pieces, frame, screw, per_piece, phi, inner, outer, frame_z, column_room, skirted,
           xs, ys, R, s, h, spec, blockers, App, Part, np, ndimage, taken=()):
    """Bosses down to the frame, holes, counterbores, pilots; the fastener table.

    A boss is a column along ``-side`` from the panel to the frame: inside
    the panel where the space under it is free, in the skirt's wall, or as
    a lug just outside the outline -- wherever it overlaps the panel by a
    millimetre and a half. Candidates stand on a 4 mm lattice and are
    sifted on the voxels (the frame under the whole boss, flat to within
    2.5 mm, the column a boss radius clear of everything the panel covers
    but the frame), spread by :func:`choose_sites`, then checked exactly:
    cast onto the frame's BREP at the centre and four rim points, and by
    rays at its rim against the covered parts' triangles. A site the exact
    check refuses is dropped and the spread chosen again.
    """

    from CadexPanels import first_hits

    d = float(screw["nominal_dia_mm"])
    length = float(screw["length_mm"])
    head_r = float(screw["head_dia_mm"]) / 2.0 + 0.3
    clear_r = float(screw["clearance_normal_mm"]) / 2.0
    tap_r = float(screw["tap_drill_mm"]) / 2.0
    boss_r = head_r + BOSS_WALL_MM
    thickness = float(spec["thickness"])
    clearance = float(spec["envelope"]["clearance"])
    seams = spec.get("seams") or []
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    middle = np.stack([X, Y, 0.5 * (inner + outer)], axis=-1) @ R
    cell = piece_index(middle, seams)
    seam_room = _seam_distance(middle, seams) >= boss_r + 1.0 + float(spec.get("seam_gap") or 0.6)
    overlap = boss_r + (thickness if skirted else 0.0) - 1.5
    radius_cells = int(math.ceil(boss_r / h))
    yy, xx = np.mgrid[-radius_cells:radius_cells + 1, -radius_cells:radius_cells + 1]
    disc = (xx * xx + yy * yy) * h * h <= boss_r * boss_r
    present = np.isfinite(frame_z)
    high = ndimage.maximum_filter(np.where(present, frame_z, np.inf), footprint=disc)
    low = ndimage.minimum_filter(np.where(present, frame_z, -np.inf), footprint=disc)
    flat = present & np.isfinite(high) & np.isfinite(low) & (high - low <= 2.5)
    reach = inner - np.where(present, frame_z, np.nan)
    sound = flat & (reach <= BOSS_REACH_MM) & (reach >= 0.0) & \
        (column_room >= boss_r + clearance) & seam_room & (phi >= -overlap)
    # The boss top: under the outer face all round it, but always into the wall.
    top_z = np.maximum(ndimage.minimum_filter(outer, footprint=disc), inner + 0.6 * (outer - inner))
    step = max(1, int(round(4.0 / h)))
    lattice = np.zeros_like(sound)
    lattice[::step, ::step] = True
    world_dir = App.Vector(*[-v for v in s])
    sv = App.Vector(*s)
    ex, ey = App.Vector(*R[0]), App.Vector(*R[1])
    rim_dirs = [(math.cos(a), math.sin(a)) for a in np.linspace(0.0, 2 * math.pi, 9)[:-1]]
    fasteners: dict[str, list] = {}
    pilots = []
    out = {}
    for name, solid in pieces.items():
        number = int(name[1:])
        sites = np.argwhere(sound & lattice & (cell == number))
        candidates = [(float(xs[i]), float(ys[j]), float(reach[i, j]), int(i), int(j))
                      for i, j in sites]
        accepted = []          # (site, exact) pairs
        tried = 0
        while candidates and len(accepted) < per_piece and tried < 6 * per_piece + 12:
            pool = [a[0] for a in accepted] + candidates
            picks = choose_sites([(c[0], c[1], c[2]) for c in pool], per_piece,
                                 start=range(len(accepted)))
            fresh = [pool[k] for k in picks[len(accepted):]]
            if not fresh:
                break
            for site in fresh:
                tried += 1
                candidates.remove(site)
                exact = _exact_boss(site, frame, inner, top_z, outer, xs, ys, R, sv, world_dir,
                                    ex, ey, boss_r, clearance, rim_dirs, blockers, first_hits, App,
                                    Part, np)
                if exact is not None and taken:
                    # Clear of the screws of the panels named in avoid=: two
                    # covers' screws must not meet in one corner of the frame.
                    q, top_point = exact[0], exact[1]
                    tip = q + world_dir * (length + 1.0)
                    path = ([top_point.x, top_point.y, top_point.z], [tip.x, tip.y, tip.z])
                    if min(_segment_distance(path, other) for other in taken) < d + 1.5:
                        exact = None
                if exact is None:
                    break          # choose the spread again without it
                accepted.append((site, exact))
        if len(accepted) < per_piece:
            raise EnvelopeError(
                f"piece {name}: only {len(accepted)} of {per_piece} boss sites reach the frame "
                f"within {BOSS_REACH_MM:g} mm, flat under the boss and clear of what the panel "
                "covers; put frame under the panel there (a part.former under a form panel), "
                "lower screws=, add flange=\"frame\" for lugs on its skirt, or seam the piece")
        bosses, holes, rows_out = [], [], []
        for index, (site, exact) in enumerate(accepted):
            boss, cut, pilot, row = _boss(name, exact, sv, R[0], frame, screw, Part)
            if boss is not None:
                bosses.append(boss)
            holes += cut
            pilots.append(pilot)
            rows_out.append({"name": f"b{index}", **row,
                             "kind": "lug" if phi[site[3], site[4]] < boss_r else "boss"})
        try:
            grown = solid.fuse(bosses).cut(holes)
        except Exception as exc:
            raise EnvelopeError(
                f"piece {name}: the kernel refused the bosses ({str(exc).splitlines()[0]}); "
                "a skirt that only just meets the panel is the usual cause: drop flange= or "
                "move the screws") from None
        solids = list(grown.Solids)
        if len(solids) != 1:
            raise EnvelopeError(f"piece {name}: the bosses did not fuse into one solid")
        out[name] = _sound(_refined(solids[0]), f"piece {name} with its bosses")
        fasteners[name] = rows_out
    return fasteners, pilots, out


def _boss(name, exact, sv, roll, frame, screw, Part, *, inner_gap=None, support="the frame"):
    """One boss of piece ``name``: ``(boss, [holes], pilot, row)``.

    ``exact`` is :func:`_exact_boss`'s ``(frame point, boss top, well top,
    frame thickness)``; ``sv`` the boss's axis out of the panel, ``roll``
    across it. The boss is started inside the frame and cut by it, so its
    foot is the frame's own surface: a flat foot on a curved former bit into
    it or stood off it by microns, either way a failing check (ADR-681).

    A support closer under the boss's top than :data:`SEAT_FLOOR_MM` leaves
    no boss to stand. When it is no nearer than the panel's inner face
    (``inner_gap`` >= 0, the frame meeting the panel there), the screw goes
    straight through the plate: no boss (``boss`` is None), a clearance hole
    through the wall, the head on the wall with at least SEAT_FLOOR_MM under
    it, recessed as deep as that allows, and a pilot in the support. A
    support inside the wall pierces the panel, and that is refused by its
    cause (ADR-687).
    """

    d = float(screw["nominal_dia_mm"])
    length = float(screw["length_mm"])
    head_r = float(screw["head_dia_mm"]) / 2.0 + 0.3
    head_h = float(screw.get("head_height_mm") or d)
    clear_r = float(screw["clearance_normal_mm"]) / 2.0
    tap_r = float(screw["tap_drill_mm"]) / 2.0
    boss_r = head_r + BOSS_WALL_MM
    q, top_point, well_top, frame_thick = exact
    total = (top_point - q).Length
    size = f"{str(screw['size']).upper()}x{length:g}"
    where = f"({q.x:.0f}, {q.y:.0f}, {q.z:.0f})"
    if total < SEAT_FLOOR_MM - 1e-6:
        if inner_gap is None or inner_gap < -0.05:
            inside = "" if inner_gap is None else f", {-inner_gap:.1f} mm inside the panel's wall"
            raise EnvelopeError(
                f"piece {name}: {support} at {where} stands {total:.1f} mm under the boss's "
                f"top{inside}, under the {SEAT_FLOOR_MM:g} mm a boss needs, so no screw length "
                "fits: the part there pierces the panel. Inset that support deeper (a "
                "part.former's inset= at least thickness + clearance), move that part, open the "
                "panel round it (openings=), or weld the piece to it and give it fewer screws=")
        # Straight through the plate into the support (ADR-687).
        room = (well_top - q).dot(sv)
        if room < SEAT_FLOOR_MM - 1e-6:
            raise EnvelopeError(
                f"piece {name}: {support} at {where} meets the panel, and its wall leaves "
                f"{room:.1f} mm under a screw head, under {SEAT_FLOOR_MM:g} mm; thicken the "
                "panel (thickness=) or weld the piece there and give it fewer screws=")
        under = max(SEAT_FLOOR_MM, room - head_h)
        engagement = length - under
        if engagement < 1.5 * d - 1e-6:
            raise EnvelopeError(
                f"piece {name}: an {size} through the plate at {where} bites {engagement:.1f} "
                f"mm into {support}, under {1.5 * d:g} mm; choose a longer screw")
        head_seat = q + sv * under
        holes = [Part.makeCylinder(clear_r, room + 4.0, q - sv * 1.0, sv)]
        if room - under > 0.05:
            holes.append(Part.makeCylinder(head_r, room - under + 2.0, head_seat, sv))
        pilot = Part.makeCylinder(tap_r, engagement + 1.5, q - sv * (engagement + 1.5), sv)
        row = {
            "head_seat": [round(v, 4) for v in (head_seat.x, head_seat.y, head_seat.z)],
            "axis": [round(float(v), 6) for v in (sv.x, sv.y, sv.z)],
            "roll": [round(float(v), 6) for v in roll],
            "frame_point": [round(v, 3) for v in (q.x, q.y, q.z)],
            "boss_length_mm": 0.0,
            "seat_depth_mm": round(max(room - under, 0.0), 2),
            "engagement_mm": round(engagement, 2),
            "through": True,
            "head_proud_mm": round(max(0.0, head_h - (room - under)), 2),
        }
        return None, holes, pilot, row
    engage = min(max(2.5 * d, 4.0), length - SEAT_FLOOR_MM - 0.2)
    if frame_thick is not None:
        engage = min(engage, max(frame_thick - 0.6, 1.5 * d))
    seat = max(0.0, total + engage - length)
    engagement = seat + length - total
    head_seat = top_point - sv * seat
    boss = _seated(Part.makeCylinder(boss_r, total + BOSS_SEAT_MM, q - sv * BOSS_SEAT_MM, sv),
                   Part.makeCylinder(boss_r, total, q, sv), frame)
    holes = [Part.makeCylinder(clear_r, total + 4.0, q - sv * 1.0, sv)]
    well = (well_top - head_seat).dot(sv)
    if well > 0.05:
        holes.append(Part.makeCylinder(head_r, well + 2.0, head_seat, sv))
    pilot = Part.makeCylinder(tap_r, engagement + 1.5, q - sv * (engagement + 1.5), sv)
    row = {
        "head_seat": [round(v, 4) for v in (head_seat.x, head_seat.y, head_seat.z)],
        "axis": [round(float(v), 6) for v in (sv.x, sv.y, sv.z)],
        "roll": [round(float(v), 6) for v in roll],
        "frame_point": [round(v, 3) for v in (q.x, q.y, q.z)],
        "boss_length_mm": round(total, 2),
        "seat_depth_mm": round(well, 2),
        "engagement_mm": round(engagement, 2),
    }
    return boss, holes, pilot, row


def _exact_boss(site, frame, inner, top_z, outer, xs, ys, R, sv, down, ex, ey, boss_r,
                clearance, rim_dirs, blockers, first_hits, App, Part, np):
    """``(frame point, boss top, well top, frame thickness)`` of one site, or None.

    Cast exactly: the frame's BREP under the centre and four rim points (all
    within 3 mm, the boss seated on the nearest), and eight rays down the
    boss's rim, a little outside it, against what the panel covers.
    """

    _x, _y, _reach, i, j = site[:5]
    local_top = np.array([xs[i], ys[j], top_z[i, j]])
    top_point = App.Vector(*(local_top @ R))
    well_top = App.Vector(*(np.array([xs[i], ys[j], outer[i, j]]) @ R))
    hit = _first_frame_hit(frame, top_point, down, Part)
    if hit is None or hit > BOSS_REACH_MM + 10.0:
        return None
    rims = []
    for a in (0.0, 0.5 * math.pi, math.pi, 1.5 * math.pi):
        offset = (ex * math.cos(a) + ey * math.sin(a)) * boss_r
        rim = _first_frame_hit(frame, top_point + offset, down, Part)
        if rim is None or abs(rim - hit) > 3.0:
            return None
        rims.append(rim)
    if blockers is not None and len(blockers):
        starts = np.array([[*(top_point + (ex * c + ey * s_) * (boss_r + clearance))]
                           for c, s_ in rim_dirs] + [[*top_point]])
        dirs = np.tile(np.array([down.x, down.y, down.z]), (len(starts), 1))
        blocked = first_hits(starts, dirs, blockers, reach=min(rims + [hit]) + 0.5)
        if np.isfinite(blocked).any():
            return None
    seat_on = min(rims + [hit])
    q = top_point + down * seat_on
    through = _frame_hits(frame, q, down, Part)
    thick = next((t for t in through if t > 0.05), None)
    return (q, top_point, well_top, thick)


def _taken_screws(spec, plan_of):
    """The screw paths of the panels this one is declared to avoid."""

    paths = []
    for other in spec.get("avoid") or []:
        if plan_of is None:
            break
        plan = plan_of(other)
        length = float((other.get("screw") or {}).get("length_mm") or 0.0)
        for rows in plan["fasteners"].values():
            for row in rows:
                head = row["head_seat"]
                axis = row["axis"]
                paths.append((list(head), [head[k] - axis[k] * (length + 1.0) for k in range(3)]))
    return paths


def _segment_distance(first, second):
    """The closest approach of two segments, each ``(p0, p1)``."""

    import numpy as np

    p, q = np.asarray(first[0], float), np.asarray(second[0], float)
    d1, d2 = np.asarray(first[1], float) - p, np.asarray(second[1], float) - q
    r = p - q
    a, e, f = d1 @ d1, d2 @ d2, d2 @ r
    c, b = d1 @ r, d1 @ d2
    denom = a * e - b * b
    s = np.clip((b * f - c * e) / denom, 0.0, 1.0) if denom > 1e-12 else 0.0
    t = np.clip((b * s + f) / e, 0.0, 1.0) if e > 1e-12 else 0.0
    s = np.clip((b * t - c) / a, 0.0, 1.0) if a > 1e-12 else 0.0
    return float(np.linalg.norm(p + d1 * s - q - d2 * t))


#: The largest a panel's box may be, as a diagonal in mm, set per plan from
#: its field: a boolean or a ruled face gone wrong can return a "valid"
#: solid 1e29 mm across, and tessellating that is what once ate 58 GB.
_SANE_DIAGONAL = [math.inf]


def _sane(shape, what):
    box = shape.BoundBox
    if not (math.isfinite(box.DiagonalLength) and box.DiagonalLength <= _SANE_DIAGONAL[0]):
        raise EnvelopeError(
            f"{what} came out {box.DiagonalLength:.3g} mm across, far past the field it was "
            "drawn in: the kernel failed on it; move a seam, an opening or the screws a "
            "few mm, or change resolution=")
    return shape


def _wall_sane(wall):
    box = wall.BoundBox
    return wall.isValid() and math.isfinite(box.DiagonalLength) and \
        box.DiagonalLength <= _SANE_DIAGONAL[0] and wall.Volume > 0


def _sound(shape, what):
    """``shape`` if the kernel calls it valid and sane, after one healing pass if not."""

    _sane(shape, what)
    if shape.isValid():
        return shape
    healed = shape.copy()
    try:
        healed.fix(1e-4, 1e-4, 1e-2)
    except Exception:
        pass
    if healed.isValid():
        return healed
    raise EnvelopeError(
        f"{what} is not a valid solid; move a seam, an opening or the screws a few mm, "
        "or change resolution=")


def _seated(boss, plain, frame):
    """``boss`` less the frame it starts inside: the piece of it that reaches the top.

    ``plain`` -- the boss as it was cast, kept when the cut does not give
    one sound solid (the frame's faces there are more than the kernel can
    cut cleanly; the boss then stands on its cast point as before).
    """

    try:
        cut = boss.cut(frame)
        solids = sorted(cut.Solids, key=lambda s: -abs(s.Volume))
        if not solids or not solids[0].isValid():
            return plain
        top = solids[0]
        if abs(top.Volume) < 0.5 * abs(plain.Volume):
            return plain
        return top
    except Exception:
        return plain


def _refined(shape):
    """``shape`` with its splitter faces merged, or as it is when that fails.

    Refined on a copy: OCCT's unifier can write a tolerance of up to 1e21 mm
    into the edges it shares with its input when it fails, and the piece
    "kept as it is" was then that corrupted shape -- valid after healing, its
    box the size of the world, so every fit pair with it was measured
    exactly at minutes each (ADR-678, ADR-680).
    """

    try:
        refined = shape.copy().removeSplitter()
        volume, before = abs(refined.Volume), abs(shape.Volume)
    except Exception:
        return shape
    sound = refined.isValid() and refined.Solids and abs(volume - before) <= 1e-3 * before + 1e-3
    return refined if sound else shape


def _frame_hits(frame, point, direction, Part):
    """Distances from ``point`` along ``direction`` to where the line crosses the frame."""

    far = point + direction * (BOSS_REACH_MM + 40.0)
    start = point - direction * 0.01
    try:
        section = frame.section(Part.makeLine(start, far))
    except Exception:
        return []
    found = sorted((vertex.Point - point).dot(direction) for vertex in section.Vertexes)
    return [d for d in found if d > -1e-6]


def _first_frame_hit(frame, point, direction, Part):
    """Distance from ``point`` along ``direction`` to the frame's surface, or None."""

    hits = _frame_hits(frame, point, direction, Part)
    return hits[0] if hits else None


def _inset_face(wire, normal, depth, count, App, Part):
    """The face of ``wire`` pulled ``depth`` mm in, through its sampled outline.

    OCCT's planar offset refuses the single periodic B-spline edge a slice
    of a loft gives, so the outline is sampled, each point moved inward
    along the section's normal, and a periodic B-spline fitted through them
    (ADR-679). Good for the gently curved sections of a designed form.
    """

    pts = wire.discretize(Number=count + 1)[:-1]
    n = len(pts)
    centre = App.Vector(0, 0, 0)
    for point in pts:
        centre = centre + point
    centre = centre * (1.0 / n)
    area = sum(((pts[i] - centre).cross(pts[(i + 1) % n] - centre)).dot(normal)
               for i in range(n))
    sign = 1.0 if area > 0 else -1.0
    moved = []
    for i in range(n):
        tangent = pts[(i + 1) % n] - pts[i - 1]
        if tangent.Length < 1e-9:
            continue
        tangent.normalize()
        moved.append(pts[i] + normal.cross(tangent) * (sign * depth))
    curve = Part.BSplineCurve()
    curve.interpolate(moved, PeriodicFlag=True)
    face = Part.Face(Part.Wire([curve.toShape()]))
    if not face.isValid() or face.Area <= 0:
        raise EnvelopeError(f"the form's section is too small or too tight to inset by {depth:g} mm")
    return face


def build_former(form, keep_out, origin, normal, width, depth, web, *, inset=0.0, samples=96):
    """A former: the band of a designed form that carries its panels (ADR-679).

    Built in the plane, never by a 3D boolean of the form's B-spline skin:
    the form is sliced at the band's two faces and its middle, the three
    outlines intersected (so the band stays inside a form that tapers
    across it), the hoop is that outline less its inset by ``depth``,
    extruded ``width`` along ``normal``, and the web, when asked, the inset
    face ``web`` thick less ``keep_out``. A few seconds where the 3D
    booleans took minutes. ``inset`` pulls the hoop's outer face that far
    inside the form: under a ``part.skin``, its wall and clearance (ADR-684).
    """

    import FreeCAD as App
    import Part

    n = App.Vector(*normal)
    n.normalize()
    o = App.Vector(*origin)
    d = o.dot(n)
    faces = []
    for shift in (-width / 2.0, 0.0, width / 2.0):
        wires = [w for w in form.slice(n, d + shift) if w.isClosed()]
        if not wires:
            raise EnvelopeError(
                f"the plane {shift:+g} mm from origin misses the form: put origin inside it, "
                "with the band's width inside it too")
        sections = [Part.Face(w) for w in wires]
        here = o + n * shift
        # The section round origin, else the largest (a form sliced through two limbs).
        chosen = next((f for f in sections if f.isInside(here, 0.01, True)),
                      max(sections, key=lambda f: f.Area))
        chosen.translate(n * (-shift))
        faces.append(chosen)
    outline = faces[0].common(faces[1]).common(faces[2])
    if not outline.Faces:
        raise EnvelopeError("the form's sections across the band do not overlap; narrow width=")
    outer = max(outline.Faces, key=lambda f: f.Area)
    if inset > 0:
        outer = _inset_face(outer.OuterWire, n, inset, samples, App, Part)
    inner = _inset_face(outer.OuterWire, n, depth, samples, App, Part)
    ring = outer.cut(inner)
    if not ring.Faces:
        raise EnvelopeError(f"depth={depth:g} leaves no hoop: the form is thinner than that")
    start = n * (-width / 2.0)
    hoop = ring.extrude(n * width)
    hoop.translate(start)
    tools = Part.makeCompound(list(keep_out)) if keep_out else None
    if tools is not None:
        # The hoop clears keep_out as the web does (ADR-687): a link or drum
        # passing through the band would otherwise stand in the hoop.
        hoop = hoop.cut(tools)
        if not hoop.Solids:
            raise EnvelopeError("keep_out takes the whole hoop: move the former or keep_out")
    body = hoop
    if web > 0:
        plate = inner.extrude(n * web)
        plate.translate(n * (-web / 2.0))
        if tools is not None:
            plate = plate.cut(tools)
        if plate.Solids:
            body = hoop.fuse(plate)
    body = body.removeSplitter()
    solids = list(body.Solids)
    if not solids:
        raise EnvelopeError("the former came out empty")
    if len(solids) > 1:
        # A web cut through by keep_out leaves islands, and they go. The
        # hoop's arcs are kept or refused, never dropped unseen: an arc that
        # no web ties to the rest is a second former.
        hoop_volume = abs(hoop.Volume)

        def arc(solid):
            try:
                return abs(solid.common(hoop).Volume)
            except Exception:
                return 0.0

        arcs = sorted(((arc(s), s) for s in solids), key=lambda pair: -pair[0])
        rest = [v for v, _s in arcs[1:] if v >= SPECK_FRACTION * arcs[0][0]
                and v >= 0.02 * hoop_volume]
        if rest:
            raise EnvelopeError(
                f"keep_out cuts the hoop into {len(rest) + 1} arcs that nothing ties together "
                f"({arcs[0][0]:.0f} and {rest[0]:.0f} mm3 of hoop): give it a web= that ties "
                "them, or declare one former per arc (part.common of the former and a box)")
        body = arcs[0][1]
    else:
        body = solids[0]
    return _sound(body, "the former")


# ---------------------------------------------------------------------------
# the skin: panels cut from the designed form itself (ADR-684)

#: The lattice a skin's boss candidates stand on, mm along its inner face.
SKIN_SITE_SPACING_MM = 4.0
#: At most this many candidates per piece are screened; a boss needs a few.
SKIN_MAX_CANDIDATES = 2500
#: How far inside the wall, as a fraction of it, a skin boss's top stands.
SKIN_BOSS_TOP = 0.6


def _skin_inner(form, thickness):
    """The form offset inward by the wall: the skin's inner face, as a solid."""

    attempts = []
    for join in (0, 2):
        try:
            inner = form.makeOffsetShape(-thickness, 1e-2, join=join, fill=False)
        except Exception as exc:
            attempts.append(str(exc).splitlines()[0] if str(exc) else type(exc).__name__)
            continue
        solids = list(getattr(inner, "Solids", []) or [])
        if len(solids) == 1 and solids[0].isValid() and \
                0.0 < abs(solids[0].Volume) < abs(form.Volume):
            return solids[0]
        attempts.append(f"{len(solids)} solids")
    raise EnvelopeError(
        f"the form could not be offset inward by thickness={thickness:g} mm ({'; '.join(attempts)}): "
        "it curves tighter than the wall somewhere, or two fused forms meet in a crease; "
        "round the form there (more stations, a larger section) or lower thickness=")


def _grown_region(region, gap):
    """``region`` grown by ``gap`` all round: what the next piece keeps clear of."""

    if gap <= 0.0:
        return region
    for join in (0, 2):
        try:
            grown = region.makeOffsetShape(gap, 1e-2, join=join, fill=False)
        except Exception:
            continue
        solids = list(getattr(grown, "Solids", []) or [])
        if len(solids) == 1 and solids[0].isValid() and abs(solids[0].Volume) > abs(region.Volume):
            return solids[0]
    # A solid the kernel cannot offset is scaled about its centre instead: the
    # gap is then exact only across the region's middle.
    box = region.BoundBox
    import FreeCAD as App

    scaled = region.copy()
    matrix = App.Matrix()
    matrix.move(box.Center * -1)
    matrix.scale(*[1.0 + 2.0 * gap / max(size, 1.0)
                   for size in (box.XLength, box.YLength, box.ZLength)])
    matrix.move(box.Center)
    return scaled.transformGeometry(matrix)


def _one_patch(piece, index):
    """The piece as one solid: specks dropped, two real patches refused."""

    solids = sorted(getattr(piece, "Solids", []) or [], key=lambda s: -abs(s.Volume))
    if not solids:
        raise EnvelopeError(
            f"regions[{index}] does not meet the form's surface, or the regions before it and "
            "the openings take all of it: move or grow the region")
    largest = abs(solids[0].Volume)
    solids = [s for s in solids if abs(s.Volume) >= SPECK_FRACTION * largest]
    if len(solids) > 1:
        where = "; ".join(
            f"{round(abs(s.Volume))} mm3 at x {s.BoundBox.XMin:.0f}..{s.BoundBox.XMax:.0f}, "
            f"y {s.BoundBox.YMin:.0f}..{s.BoundBox.YMax:.0f}, "
            f"z {s.BoundBox.ZMin:.0f}..{s.BoundBox.ZMax:.0f}" for s in solids)
        raise EnvelopeError(
            f"regions[{index}] meets the form in {len(solids)} separate patches ({where}): "
            "a region that passes through the body cuts both sides; keep it to one side, or "
            "give each patch its own region")
    return _sound(solids[0], f"piece p{index}")


def _faces_on(piece, surface, tolerance=0.05):
    """The faces of ``piece`` that lie on ``surface`` (a shell or compound of faces)."""

    import Part

    found = []
    for face in piece.Faces:
        try:
            points, _facets = face.tessellate(2.0)
        except Exception:
            continue
        if not points:
            continue
        probe = points[len(points) // 2]
        if surface.distToShape(Part.Vertex(probe))[0] <= tolerance:
            found.append(face)
    return found


def _triangles(shapes, deflection=0.3):
    import numpy as np

    sets = []
    for shape in shapes:
        for solid in getattr(shape, "Solids", []) or []:
            points, facets = solid.tessellate(deflection)
            if facets:
                vertices = np.array([[p.x, p.y, p.z] for p in points], dtype=float)
                sets.append(vertices[np.array(facets, dtype=int)])
    return np.concatenate(sets) if sets else None


def _face_samples(face, piece, thickness, margin, App, np):
    """Points on a skin piece's inner face a ``margin`` inside its outline, ``SKIN_SITE_SPACING_MM``
    apart, and the face's normal at each, pointing away from the wall: ``(points, directions)``.

    Read off the face's tessellation, all at once: the outline is the
    tessellation's open edges, the normals its facets', oriented by one
    exact probe of which side the wall is on.
    """

    points, facets = face.tessellate(0.2)
    if not facets:
        return np.zeros((0, 3)), np.zeros((0, 3))
    P = np.array([[p.x, p.y, p.z] for p in points], dtype=float)
    F = np.array(facets, dtype=int)
    tri = P[F]
    centres = tri.mean(axis=1)
    normals = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    length = np.linalg.norm(normals, axis=1)
    keep = length > 1e-12
    centres, normals = centres[keep], normals[keep] / length[keep][:, None]
    F = F[keep]
    # The outline: edges one facet uses.
    edges = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    rim = unique[counts == 1]
    if len(rim):
        a, b = P[rim[:, 0]], P[rim[:, 1]]
        ab = b - a
        denom = np.maximum((ab * ab).sum(axis=1), 1e-12)
        far = np.full(len(centres), np.inf)
        for start in range(0, len(centres), 512):
            c = centres[start:start + 512, None, :]
            t = np.clip(((c - a[None]) * ab[None]).sum(axis=2) / denom[None], 0.0, 1.0)
            nearest = a[None] + t[..., None] * ab[None]
            far[start:start + 512] = np.sqrt(((c - nearest) ** 2).sum(axis=2)).min(axis=1)
        inside = far >= margin
        centres, normals = centres[inside], normals[inside]
    if not len(centres):
        return np.zeros((0, 3)), np.zeros((0, 3))
    # One per cell of a SKIN_SITE_SPACING_MM lattice.
    cells = np.floor(centres / SKIN_SITE_SPACING_MM).astype(np.int64)
    _cells, first = np.unique(cells, axis=0, return_index=True)
    centres, normals = centres[first], normals[first]
    # The facets keep the face's orientation, so one probe orients them all.
    probe = App.Vector(*(centres[0] + normals[0] * (0.5 * thickness)))
    if piece.isInside(probe, 1e-3, False):
        normals = -normals
    return centres, normals


def _local_hits(first_hits, starts, dirs, tris, reach, np, chunk=128):
    """``first_hits`` of rays that each go at most ``reach``, a chunk of neighbouring rays at a
    time against only the triangles inside that chunk's reach."""

    out = np.full(len(starts), np.inf)
    if tris is None or not len(starts):
        return out
    order = np.lexsort(np.floor(starts / 40.0).T[::-1])
    box_lo, box_hi = tris.min(axis=1), tris.max(axis=1)
    for begin in range(0, len(order), chunk):
        idx = order[begin:begin + chunk]
        ends = starts[idx] + dirs[idx] * reach
        lo = np.minimum(starts[idx].min(axis=0), ends.min(axis=0)) - 1.0
        hi = np.maximum(starts[idx].max(axis=0), ends.max(axis=0)) + 1.0
        keep = np.all((box_hi >= lo) & (box_lo <= hi), axis=1)
        if keep.any():
            out[idx] = first_hits(starts[idx], dirs[idx], tris[keep], reach=reach)
    return out


def _skin_sites(name, piece, inner_faces, thickness, frame, frame_tris, blockers, screw,
                per_piece, clearance, taken, App, Part, np):
    """The boss sites of one skin piece and why the others were turned down.

    ``([(exact, sv, roll, inner_gap), ...], rejected)``: ``rejected`` counts
    the lattice candidates each screen dropped -- ``no support within reach``,
    ``support pierces the wall``, ``not flat under the boss``, ``keep_clear in
    the way`` -- and the chosen sites the exact cast turned down. Fewer sites
    than ``per_piece`` is the caller's to judge (ADR-687).
    """

    from CadexPanels import first_hits

    d = float(screw["nominal_dia_mm"])
    length = float(screw["length_mm"])
    boss_r = float(screw["head_dia_mm"]) / 2.0 + 0.3 + BOSS_WALL_MM
    rejected: dict[str, int] = {}

    def drop(reason, count=1):
        if count:
            rejected[reason] = rejected.get(reason, 0) + int(count)

    starts, downs = [], []
    for face in inner_faces:
        S_f, D_f = _face_samples(face, piece, thickness, boss_r + 1.0, App, np)
        starts.append(S_f)
        downs.append(D_f)
    starts = [a for a in starts if len(a)]
    if not starts:
        raise EnvelopeError(
            f"piece {name}: no point of its inner face lies a boss's radius ({boss_r:.1f} mm) "
            "inside its outline; make the region larger or lower screws=")
    starts, downs = np.concatenate(starts), np.concatenate([d for d in downs if len(d)])
    if len(starts) > SKIN_MAX_CANDIDATES:
        keep = np.linspace(0, len(starts) - 1, SKIN_MAX_CANDIDATES).astype(int)
        starts, downs = starts[keep], downs[keep]
    S, D = starts, downs
    top_depth = SKIN_BOSS_TOP * thickness
    tops = S - D * top_depth
    # Only the triangles a boss from this piece could reach: the screen is
    # rays against triangles, all pairs at once.
    low = tops.min(axis=0) - (BOSS_REACH_MM + 20.0)
    high = tops.max(axis=0) + (BOSS_REACH_MM + 20.0)

    def near(tris):
        if tris is None:
            return None
        box_lo, box_hi = tris.min(axis=1), tris.max(axis=1)
        keep = np.all((box_hi >= low) & (box_lo <= high), axis=1)
        return tris[keep] if keep.any() else None

    frame_tris, blockers = near(frame_tris), near(blockers)
    reach = _local_hits(first_hits, tops, D, frame_tris, BOSS_REACH_MM + 10.0, np)
    ok = np.isfinite(reach) & (reach <= BOSS_REACH_MM)
    drop("no support within reach", int(np.sum(~ok)))
    # A support nearer than the inner face is inside the wall: it pierces
    # the panel, and no boss or screw there is sound.
    pierced = ok & (reach < top_depth - 0.05)
    drop("support pierces the wall", int(np.sum(pierced)))
    ok &= ~pierced
    helper = np.where(np.abs(D[:, 2:3]) < 0.9, np.array([[0.0, 0.0, 1.0]]), np.array([[1.0, 0.0, 0.0]]))
    ex = np.cross(D, helper)
    ex /= np.linalg.norm(ex, axis=1, keepdims=True)
    ey = np.cross(D, ex)

    def screen(test, reason):
        # Each screen runs on the candidates the ones before it kept.
        live = np.nonzero(ok)[0]
        if len(live):
            passed = test(live)
            drop(reason, int(np.sum(~passed)))
            ok[live] = passed

    # Flat enough under the disc: four rim rays land within 3 mm of the centre's.
    for a in (0.0, 0.5 * math.pi, math.pi, 1.5 * math.pi):
        def flat(live, a=a):
            offset = (ex[live] * math.cos(a) + ey[live] * math.sin(a)) * boss_r
            rim_reach = _local_hits(first_hits, tops[live] + offset, D[live], frame_tris,
                                    BOSS_REACH_MM + 15.0, np)
            return np.isfinite(rim_reach) & (np.abs(rim_reach - reach[live]) <= 3.0)
        screen(flat, "not flat under the boss")
    if blockers is not None:
        for a in [None] + list(np.linspace(0.0, 2 * math.pi, 9)[:-1]):
            def clear_of(live, a=a):
                offset = 0.0 if a is None else \
                    (ex[live] * math.cos(a) + ey[live] * math.sin(a)) * (boss_r + clearance)
                blocked = _local_hits(first_hits, tops[live] + offset, D[live], blockers,
                                      float(reach[live].max()) + 0.5, np)
                return ~(np.isfinite(blocked) & (blocked < reach[live] + 0.5))
            screen(clear_of, "keep_clear in the way")
    candidates = [(float(tops[k, 0]), float(tops[k, 1]), float(tops[k, 2]), float(reach[k]), int(k))
                  for k in np.nonzero(ok)[0]]
    accepted, tried = [], 0
    while candidates and len(accepted) < per_piece and tried < 6 * per_piece + 12:
        pool = [a[0] for a in accepted] + candidates
        picks = choose_sites([c[:4] for c in pool], per_piece, start=range(len(accepted)))
        fresh = [pool[k] for k in picks[len(accepted):]]
        if not fresh:
            break
        for site in fresh:
            if site not in candidates:
                continue            # pruned beside a site accepted in this round
            if any(math.dist(site[:3], other[:3]) < 2.0 * boss_r + 1.0 for other, _e in accepted):
                # Two bosses of one piece may not overlap: their holes would
                # cut each other's walls apart.
                candidates.remove(site)
                drop("crowded by its other bosses")
                continue
            tried += 1
            candidates.remove(site)
            k = site[4]
            down = App.Vector(*D[k])
            sv = down * -1.0
            top_point = App.Vector(*tops[k])
            well_top = App.Vector(*S[k]) + sv * thickness
            hit = _first_frame_hit(frame, top_point, down, Part)
            exact, why = None, "the exact cast found no flat support"
            if hit is not None and hit <= BOSS_REACH_MM + 10.0:
                rims = []
                for a in (0.0, 0.5 * math.pi, math.pi, 1.5 * math.pi):
                    offset = App.Vector(*((ex[k] * math.cos(a) + ey[k] * math.sin(a)) * boss_r))
                    rim_hit = _first_frame_hit(frame, top_point + offset, down, Part)
                    if rim_hit is None or abs(rim_hit - hit) > 3.0:
                        rims = None
                        break
                    rims.append(rim_hit)
                if rims is not None:
                    seat_on = min(rims + [hit])
                    if seat_on < top_depth - 0.05:
                        why = "support pierces the wall"
                    else:
                        q = top_point + down * seat_on
                        through = _frame_hits(frame, q, down, Part)
                        exact = (q, top_point, well_top, next((t for t in through if t > 0.05), None))
            if exact is not None and taken:
                tip = exact[0] + down * (length + 1.0)
                path = ([top_point.x, top_point.y, top_point.z], [tip.x, tip.y, tip.z])
                if min(_segment_distance(path, other) for other in taken) < d + 1.5:
                    exact, why = None, "another panel's screw in the way"
            if exact is None:
                drop(why)
                break
            gap = (exact[0] - top_point).dot(down) - top_depth
            accepted.append((site, (exact, sv, App.Vector(*ex[k]), gap)))
            near_it = [c for c in candidates if math.dist(c[:3], site[:3]) < 2.0 * boss_r + 1.0]
            if near_it:
                drop("crowded by its other bosses", len(near_it))
                candidates = [c for c in candidates if c not in near_it]
    return [entry for _site, entry in accepted], rejected


def _reasons(rejected):
    return "; ".join(f"{reason}: {count}" for reason, count in
                     sorted(rejected.items(), key=lambda kv: -kv[1])) or "none screened"


# ---------------------------------------------------------------------------
# what a skin opens round: a part, at rest or swept through its motion (ADR-687)

#: The part is cut into slabs this long along its longest axis (at most
#: SKIN_SWEEP_MAX_SLABS of them); each slab is hulled, at rest or over each
#: pair of neighbouring poses, so the opening follows a long part's shape
#: rather than the hull of all of it.
SKIN_SWEEP_SLAB_MM = 40.0
SKIN_SWEEP_MAX_SLABS = 8
#: The part's surface is sampled this far apart, at most this many points.
SKIN_SWEEP_SPACING_MM = 4.0
SKIN_SWEEP_MAX_SAMPLES = 20_000
#: Facets of a slab's hull within this of one another are merged; every hull
#: grows by it on top of its clearance, so the merge never uncovers a point.
SKIN_SWEEP_MERGE_MM = 1.0
#: The most an arc between two sampled poses bulges past their chord, mm: the
#: hinge's step is chosen from the part's farthest reach from the axis, and
#: every hull grows by that bulge too.
SKIN_SWEEP_SAG_MM = 4.0
#: The coarsest and the most steps one hinge sweep takes.
SKIN_SWEEP_MAX_STEP_DEGREES = 20.0
SKIN_SWEEP_MAX_STEPS = 48
#: At most this many hulls one opening makes.
SKIN_SWEEP_MAX_HULLS = 400


def _motion_poses(motion, points, np):
    """``([(R, t), ...], bulge)``: the sampled poses ``p' = R p + t`` of a declared motion, and
    how far an arc between two of them stands past their chord."""

    if not motion:
        return [(np.eye(3), np.zeros(3))], 0.0
    lo, hi = (float(v) for v in motion["range"])
    if str(motion.get("kind") or "hinge") != "hinge":
        direction = np.array(_unit(motion["direction"], "motion direction"))
        # A hull over the two ends is the exact sweep of a convex cell.
        return [(np.eye(3), direction * lo), (np.eye(3), direction * hi)], 0.0
    origin = np.array(_vec(motion["origin"]))
    axis = np.array(_unit(motion["axis"], "motion axis"))
    rel = points - origin
    radius = float(np.max(np.linalg.norm(rel - np.outer(rel @ axis, axis), axis=1))) \
        if len(points) else 0.0
    step = SKIN_SWEEP_MAX_STEP_DEGREES
    if radius > SKIN_SWEEP_SAG_MM:
        step = min(step, math.degrees(2.0 * math.acos(1.0 - SKIN_SWEEP_SAG_MM / radius)))
    count = min(SKIN_SWEEP_MAX_STEPS, max(1, int(math.ceil(abs(hi - lo) / step - 1e-9))))
    angles = np.linspace(lo, hi, count + 1)
    half = math.radians(abs(hi - lo) / count) / 2.0
    bulge = radius * (1.0 - math.cos(half))
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    poses = []
    for angle in angles:
        t = math.radians(angle)
        rot = np.eye(3) + math.sin(t) * K + (1 - math.cos(t)) * K @ K
        poses.append((rot, origin - rot @ origin))
    return poses, bulge




def _cell_points(shape, np, deflection=0.5):
    """The shape's surface points, in slabs of SKIN_SWEEP_SLAB_MM along its longest axis."""

    from CadexPanels import sample_triangles

    points, facets = shape.tessellate(deflection)
    V = np.array([[p.x, p.y, p.z] for p in points], dtype=float)
    if not len(V) or not facets:
        return []
    # A flat face tessellates to its corners: the surface is sampled too, so
    # every slab it crosses holds its points.
    tris = V[np.array(facets, dtype=int)]
    area = float(np.sum(np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0],
                                                tris[:, 2] - tris[:, 0]), axis=1)) / 2.0)
    count = int(min(SKIN_SWEEP_MAX_SAMPLES, max(64, area / SKIN_SWEEP_SPACING_MM ** 2)))
    samples, _normals = sample_triangles(tris, count)
    V = np.vstack([V, samples])
    centred = V - V.mean(axis=0)
    _u, _s, vt = np.linalg.svd(centred[:: max(1, len(V) // 4000)], full_matrices=False)
    along = centred @ vt[0]
    low, high = float(along.min()), float(along.max())
    slabs = max(1, min(SKIN_SWEEP_MAX_SLABS, int(math.ceil((high - low) / SKIN_SWEEP_SLAB_MM))))
    edges = np.linspace(low, high, slabs + 1)
    # Neighbouring slabs share a millimetre so their hulls overlap.
    return [V[(along >= edges[k] - 1.0) & (along <= edges[k + 1] + 1.0)] for k in range(slabs)]


def _grown_hull(P, grow, np):
    """The vertices of ``P``'s convex hull with every facet pushed out ``grow`` mm.

    Facets within SKIN_SWEEP_MERGE_MM are merged first, and the push is that
    much more, so the polytope stays a few dozen exact planes; a box ``grow``
    round the points bounds the push at a sharp corner.
    """

    from scipy.spatial import ConvexHull, HalfspaceIntersection

    try:
        hull = ConvexHull(P, qhull_options=f"Qt C{SKIN_SWEEP_MERGE_MM:g}")
    except Exception:
        hull = None
    low, high = P.min(axis=0) - grow, P.max(axis=0) + grow
    box = np.array([[-1, 0, 0, low[0]], [1, 0, 0, -high[0]], [0, -1, 0, low[1]],
                    [0, 1, 0, -high[1]], [0, 0, -1, low[2]], [0, 0, 1, -high[2]]], dtype=float)
    if hull is None:
        # A flat or tiny cell: its box, grown.
        planes = box
    else:
        planes = np.unique(np.round(hull.equations, 9), axis=0)
        planes[:, 3] -= grow + SKIN_SWEEP_MERGE_MM
        planes = np.vstack([planes, box])
    inside = (low + high) / 2.0
    try:
        return HalfspaceIntersection(planes, inside).intersections
    except Exception:
        corners = np.array([[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1])
                            for z in (low[2], high[2])])
        return corners


def _hulls(shape, motion, grow, np):
    """Convex cells covering what ``shape`` sweeps through ``motion``, grown by ``grow`` mm:
    ``[(low, high, vertices), ...]`` (each cell is the convex hull of its vertices)."""

    cells = _cell_points(shape, np)
    every = np.concatenate(cells) if cells else np.zeros((0, 3))
    poses, bulge = _motion_poses(motion, every, np)
    pairs = [(poses[0], poses[0])] if len(poses) == 1 else list(zip(poses[:-1], poses[1:]))
    if len(cells) * len(pairs) > SKIN_SWEEP_MAX_HULLS:
        raise EnvelopeError(
            f"an opening's sweep makes {len(cells) * len(pairs)} cells, more than "
            f"{SKIN_SWEEP_MAX_HULLS}; name a smaller part (the drum, the foot) or a shorter range")
    hulls = []
    for points in cells:
        for (R0, t0), (R1, t1) in pairs:
            P = np.vstack([points @ R0.T + t0, points @ R1.T + t1])
            G = _grown_hull(P, max(grow + bulge, 0.05), np)
            hulls.append((G.min(axis=0), G.max(axis=0), G))
    return hulls


def _hull_solid(points, App, Part):
    """The convex hull of ``points`` as an exact solid: one planar face per hull facet."""

    import numpy as np
    from scipy.spatial import ConvexHull

    hull = ConvexHull(points)
    groups: dict[tuple, list[int]] = {}
    for index, equation in enumerate(hull.equations):
        groups.setdefault(tuple(np.round(equation, 7)), []).append(index)
    faces = []
    for key, members in groups.items():
        normal = np.array(key[:3])
        corners = sorted({int(v) for m in members for v in hull.simplices[m]})
        P = points[corners]
        centre = P.mean(axis=0)
        u = P[int(np.argmax(np.linalg.norm(P - centre, axis=1)))] - centre
        u = u - normal * (u @ normal)
        u /= np.linalg.norm(u)
        v = np.cross(normal, u)
        order = np.argsort(np.arctan2((P - centre) @ v, (P - centre) @ u))
        loop = [App.Vector(*map(float, P[k])) for k in order]
        try:
            face = Part.Face(Part.makePolygon(loop + [loop[0]]))
            if not face.isValid():
                raise ValueError("invalid facet")
            faces.append(face)
        except Exception:
            # A facet the kernel will not take flat: its triangles instead.
            for m in members:
                tri = [App.Vector(*map(float, points[int(k)])) for k in hull.simplices[m]]
                faces.append(Part.Face(Part.makePolygon(tri + [tri[0]])))
    solid = Part.Solid(Part.Shell(faces))
    if solid.Volume < 0:
        solid.reverse()
    return solid


#: A piece's surface is sampled this far apart to find the cells that meet it;
#: a cell is tested grown by twice this, so a sparse spot never hides one.
SKIN_SWEEP_PROBE_MM = 3.0


def _piece_samples(piece, np):
    """Points over ``piece``'s surface, about SKIN_SWEEP_PROBE_MM apart."""

    from CadexPanels import sample_triangles

    tris = _triangles([piece], 0.3)
    if tris is None:
        return np.zeros((0, 3))
    area = float(np.sum(np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0],
                                                tris[:, 2] - tris[:, 0]), axis=1)) / 2.0)
    count = int(min(400_000, max(256, 2.0 * area / SKIN_SWEEP_PROBE_MM ** 2)))
    points, _normals = sample_triangles(tris, count)
    return np.vstack([tris.reshape(-1, 3), points])


#: When a cut by an opening's cells is refused, the cells are rebuilt grown
#: this much more and cut again (ADR-691).
SKIN_SWEEP_RETRY_GROW_MM = 0.7


def _cut_or_none(piece, tools):
    """``piece.cut(tools)`` when the kernel returns a sound result, else None.

    A sound result is a valid shape no larger than ``piece``: a refused
    boolean raises ("Null shape"), and a degenerate one comes back invalid.
    """

    try:
        result = piece.cut(tools)
    except Exception:
        return None
    try:
        if result.isNull() or not result.isValid():
            return None
        if result.Solids and result.Volume > piece.Volume * (1.0 + 1e-6) + 1e-6:
            return None
    except Exception:
        return None
    return result


def _cells_meeting(hulls, planes, samples, np):
    """The indices of the cells holding a point of ``samples`` (within twice the sampling)."""

    margin = 2.0 * SKIN_SWEEP_PROBE_MM
    found = []
    for index, (low, high, _points) in enumerate(hulls):
        near = np.all((samples >= low - margin) & (samples <= high + margin), axis=1)
        if not near.any():
            continue
        P = planes[index]
        if np.all(samples[near] @ P[:, :3].T + P[:, 3] <= margin, axis=1).any():
            found.append(index)
    return found


class _SweptOpening:
    """An opening round a part, at rest or swept: convex cells, fused into one tool.

    Neighbouring cells share a pose, so their faces nearly coincide; cut one
    at a time they left slivers the next cut refused ("Null shape"). Only the
    cells that reach the skin's wall are kept -- most of a moving link's are
    inside the body -- and they are fused once into one solid per opening
    (planar faces, a fraction of a second), which every piece is cut by
    (ADR-691).
    """

    def __init__(self, shape, entry, np, index=0, wall_samples=None):
        self.shape, self.entry, self.index = shape, entry, index
        self.clearance = float(entry.get("clearance") or 0.0)
        self.wall_samples = wall_samples
        self.all_hulls = _hulls(shape, entry.get("motion"), self.clearance, np)
        self.hulls, self.planes = self._cells(np, 0.0, self.all_hulls)
        self._tools: dict[float, Any] = {}

    def _cells(self, np, extra, hulls=None):
        from scipy.spatial import ConvexHull

        if hulls is None:
            hulls = _hulls(self.shape, self.entry.get("motion"), self.clearance + extra, np)
        planes = [ConvexHull(points).equations for _low, _high, points in hulls]
        if self.wall_samples is not None:
            keep = _cells_meeting(hulls, planes, self.wall_samples, np)
            hulls, planes = [hulls[k] for k in keep], [planes[k] for k in keep]
        return hulls, planes

    def meets(self, samples, np):
        """Whether a cell holds a point of the piece's surface: an opening none of whose
        cells reaches the piece costs no boolean."""

        return any(_cells_meeting([cell], [planes], samples, np)
                   for cell, planes in zip(self.hulls, self.planes))

    def tool(self, App, Part, np, extra=0.0):
        """The opening's cells fused into one solid (``extra`` mm more grown), built once."""

        if extra not in self._tools:
            hulls = self.hulls if not extra else self._cells(np, extra)[0]
            cells = [_hull_solid(points, App, Part) for _low, _high, points in hulls]
            fused = None
            if len(cells) > 1:
                try:
                    fused = cells[0].multiFuse(cells[1:])
                    if fused.isNull() or not fused.isValid() or not fused.Solids:
                        fused = None
                    else:
                        fused = fused.removeSplitter()
                except Exception:
                    fused = None
            # A fuse the kernel refuses leaves the cells as one multi-tool cut.
            self._tools[extra] = [fused] if fused is not None else cells
        return self._tools[extra]


def _sweep_key(entry):
    """One key per part and motion, whatever else the entry says."""

    import json

    return json.dumps([entry.get("around"), entry.get("motion")], sort_keys=True, default=str)


def _hull_triangles(hulls, np):
    """The convex cells' surfaces as an ``(n, 3, 3)`` triangle array."""

    from scipy.spatial import ConvexHull

    tris = [points[ConvexHull(points).simplices] for _low, _high, points in hulls]
    return np.concatenate(tris) if tris else None


def _cut_openings(piece, swept, App, Part, np):
    """``piece`` less every swept opening that reaches it, or an EnvelopeError naming the one
    the kernel would not cut.

    All the openings go in one boolean; if the kernel refuses it, each is cut
    alone, then regrown by SKIN_SWEEP_RETRY_GROW_MM, then as its separate
    cells, before the opening is named (ADR-691).
    """

    # The samples of the piece before any cell is cut: a cut only removes
    # surface, so they still find every cell.
    samples = _piece_samples(piece, np)
    live = [opening for opening in swept if opening.meets(samples, np)]
    if not live:
        return piece
    together = _cut_or_none(piece, [t for o in live for t in o.tool(App, Part, np)])
    if together is not None:
        return together
    for opening in live:
        if not piece.Solids:
            break
        result = _cut_or_none(piece, opening.tool(App, Part, np))
        if result is None:
            result = _cut_or_none(piece, opening.tool(App, Part, np, SKIN_SWEEP_RETRY_GROW_MM))
        if result is None:
            cells = [_hull_solid(points, App, Part) for _l, _h, points in opening.hulls]
            for cell in cells:
                result = _cut_or_none(piece if result is None else result, [cell])
                if result is None:
                    break
        if result is None:
            raise EnvelopeError(
                f"the kernel would not cut openings[{opening.index}] from it, fused, regrown "
                f"{SKIN_SWEEP_RETRY_GROW_MM:g} mm or cell by cell; change that opening's "
                "clearance by a millimetre or its motion's range by a few degrees")
        piece = result
    return piece


def _form_identity(values):
    """``(key, label)`` of a skin's forms: one key per set of form definitions, the labels the
    script gave them (ADR-687)."""

    import hashlib
    import json

    canonical = sorted(json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                                  default=str) for v in values)
    key = hashlib.sha256("\n".join(canonical).encode("utf-8")).hexdigest()[:16]
    labels = [str(((v.get("properties") or {}) if isinstance(v, Mapping) else {}).get("label")
                  or "") for v in values]
    named = [label for label in labels if label]
    return key, "+".join(named) if named else f"form {key[:6]}"


def build_skin_plan(spec: Mapping[str, Any], build: Callable[[Mapping[str, Any]], Any],
                    plan_of: Callable[[Mapping[str, Any]], Any] | None = None):
    """Every piece, fastener and pilot of one ``part.skin``, built once (ADR-684).

    The skin is the designed form's own surface, ``thickness`` thick inward;
    each region cuts one piece of it, less the regions before it (grown by
    the gap) and the openings -- a part, or what a part sweeps through its
    joint's motion, grown by its clearance. Bosses are cast from each
    piece's inner face along its inward normal onto the frame. Every piece
    is tried; one refusal names each piece that failed (ADR-687). A piece
    that seats fewer bosses than asked keeps the ones it has, and the plan's
    ``shortfall`` says why the rest were turned down. Returns what
    :func:`build_panel_plan` returns, with ``shortfall``.
    """

    import numpy as np
    import FreeCAD as App
    import Part

    skin = spec["skin"]
    thickness = float(spec["thickness"])
    gap = float(skin.get("gap") or 0.0)
    forms = [build(value) for value in spec["envelope"]["form"]]
    form = forms[0] if len(forms) == 1 else forms[0].fuse(forms[1:])
    solids = list(getattr(form, "Solids", []) or [])
    if len(solids) != 1:
        raise EnvelopeError(
            f"the forms make {len(solids)} solids, not one: overlap each form with the next "
            "(a shoulder mass sunk into the torso), so the skin runs over them as one")
    form = _refined(solids[0]) if len(forms) > 1 else solids[0]
    inner = _skin_inner(form, thickness)
    try:
        shell = form.cut(inner)
    except Exception as exc:
        raise EnvelopeError(f"the kernel refused the skin's wall ({str(exc).splitlines()[0]})") \
            from None
    shell = _sound(shell, "the skin's wall")
    solid_openings, swept = [], []
    wall_samples = None
    for index, entry in enumerate(skin.get("openings") or []):
        if isinstance(entry, Mapping) and "around" in entry:
            if wall_samples is None:
                wall_samples = _piece_samples(shell, np)
            try:
                swept.append(_SweptOpening(build(entry["around"]), entry, np, index,
                                           wall_samples))
            except EnvelopeError as exc:
                raise EnvelopeError(f"openings[{index}]: {exc}") from None
        else:
            solid_openings.append(build(entry))
    regions = list(skin["regions"])
    names = [f"p{index}" for index in range(len(regions))]
    failures: dict[str, str] = {}

    def failed(name, message):
        failures[name] = message if message.startswith(f"piece {name}") else \
            f"piece {name}: {message}"

    grown, pieces = [], {}
    for index, value in enumerate(regions):
        name = names[index]
        region = build(value)
        try:
            piece = shell.common(region)
            cutters = grown + solid_openings
            if cutters and piece.Solids:
                piece = piece.cut(cutters)
            if swept and piece.Solids:
                piece = _cut_openings(piece, swept, App, Part, np)
            pieces[name] = _one_patch(piece, index)
        except EnvelopeError as exc:
            failed(name, str(exc))
        except Exception as exc:
            failed(name, f"regions[{index}]: the kernel refused the cut "
                         f"({str(exc).splitlines()[0] if str(exc) else type(exc).__name__}); "
                         "move the region a few mm")
        # Every region keeps its gap, built or not, so the pieces after it
        # keep the outline they will have once it is fixed.
        grown.append(_grown_region(region, gap))
    max_piece = spec.get("max_piece")
    if max_piece is not None:
        bed = sorted(float(v) for v in max_piece)
        for name, solid in list(pieces.items()):
            box = solid.optimalBoundingBox()
            size = sorted([box.XLength, box.YLength, box.ZLength])
            if any(a > b + 1e-6 for a, b in zip(size, bed)):
                failed(name, f"piece {name} is {box.XLength:.0f} x {box.YLength:.0f} x "
                             f"{box.ZLength:.0f} mm, larger than max_piece={list(max_piece)}; "
                             "split its region")
                del pieces[name]
    outer_surface = Part.Compound(form.Faces)
    inner_surface = Part.Compound(inner.Faces)
    areas = {name: sum(f.Area for f in _faces_on(solid, outer_surface))
             for name, solid in pieces.items()}
    fasteners = {name: [] for name in names}
    shortfall: dict[str, dict[str, Any]] = {}
    pilots = []
    screw = spec.get("screw")
    counts = list(skin.get("screws") or [int(spec.get("screws") or 0)] * len(names))
    if spec.get("frame") is not None and screw is not None and max(counts + [0]) > 0:
        frame = build(spec["frame"])
        frame_label = str((spec["frame"].get("properties") or {}).get("label") or "") \
            if isinstance(spec["frame"], Mapping) else ""
        support = f"the frame ('{frame_label}')" if frame_label else "the frame (frame=)"
        # Screens only: every site chosen is cast on the exact BREP.
        frame_tris = _triangles([frame], 1.0)
        blocking = []
        for entry in skin.get("keep_clear") or []:
            if isinstance(entry, Mapping) and "around" in entry and entry.get("motion"):
                # What it sweeps, as the triangles of its convex cells: an
                # opening round the same part and motion lends its own
                # (grown by its clearance), so nothing is hulled twice (ADR-691).
                key = _sweep_key(entry)
                hulls = next((o.all_hulls for o in swept if _sweep_key(o.entry) == key), None)
                if hulls is None:
                    hulls = _hulls(build(entry["around"]), entry["motion"], 0.0, np)
                tris = _hull_triangles(hulls, np)
            elif isinstance(entry, Mapping) and "around" in entry:
                tris = _triangles([build(entry["around"])], 1.0)
            else:
                tris = _triangles([build(entry)], 1.0)
            if tris is not None:
                blocking.append(tris)
        blockers = np.concatenate(blocking) if blocking else None
        clearance = float(spec["envelope"]["clearance"])
        taken = _taken_screws(spec, plan_of)
        for name, per_piece in zip(names, counts):
            if name not in pieces or per_piece <= 0:
                continue
            solid = pieces[name]
            faces = _faces_on(solid, inner_surface)
            if not faces:
                failed(name, f"piece {name} has no inner face to cast its bosses from")
                continue
            try:
                sites, rejected = _skin_sites(name, solid, faces, thickness, frame, frame_tris,
                                              blockers, screw, per_piece, clearance, taken,
                                              App, Part, np)
                if not sites:
                    raise EnvelopeError(
                        f"piece {name}: none of its {per_piece} boss sites reach the frame "
                        f"within {BOSS_REACH_MM:g} mm along the skin's inward normal, flat under "
                        f"the boss and clear of keep_clear= (turned down: {_reasons(rejected)}); "
                        "put a part.former of the form under the piece, move the region, or "
                        "weld the piece to what it meets and give it screws=0 in a per-region "
                        "screws=[...]")
                bosses, holes, rows, piece_pilots = [], [], [], []
                for index, (exact, sv, roll, inner_gap) in enumerate(sites):
                    boss, cut, pilot, row = _boss(name, exact, sv, roll, frame, screw, Part,
                                                  inner_gap=inner_gap, support=support)
                    if boss is not None:
                        bosses.append(boss)
                    holes += cut
                    piece_pilots.append(pilot)
                    rows.append({"name": f"b{index}", **row,
                                 "kind": "through" if boss is None else "boss"})
                with_bosses = solid.fuse(bosses) if bosses else solid
                with_bosses = with_bosses.cut(holes)
            except EnvelopeError as exc:
                failed(name, str(exc))
                continue
            except Exception as exc:
                failed(name, f"piece {name}: the kernel refused the bosses "
                             f"({str(exc).splitlines()[0] if str(exc) else type(exc).__name__}); "
                             "move the region a few mm")
                continue
            if len(with_bosses.Solids) != 1:
                failed(name, f"piece {name}: the bosses did not fuse into one solid")
                continue
            try:
                pieces[name] = _sound(_refined(with_bosses.Solids[0]),
                                      f"piece {name} with its bosses")
            except EnvelopeError as exc:
                failed(name, str(exc))
                continue
            pilots += piece_pilots
            fasteners[name] = rows
            if len(sites) < per_piece:
                # Held by the sites that qualify and by its weld: an advisory
                # on its row, never a refusal (ADR-687).
                shortfall[name] = {"wanted": per_piece, "placed": len(sites),
                                   "rejected": dict(rejected)}
    if failures:
        lines = [failures[name] for name in names if name in failures]
        raise EnvelopeError(
            f"{len(lines)} of {len(names)} pieces cannot be built; every piece was tried, "
            "one line each:\n" + "\n".join(f"  - {line}" for line in lines))
    form_area = float(form.Area)
    covered = sum(areas.values())
    form_key, form_label = _form_identity(list(spec["envelope"]["form"]))
    facts = {
        "skin": True,
        "form": len(forms),
        "form_key": form_key,
        "form_label": form_label,
        "form_area_mm2": round(form_area, 1),
        "region_area_mm2": round(covered, 1),
        "covered_fraction": round(covered / form_area, 4) if form_area > 0 else 0.0,
        "piece_area_mm2": {name: round(area, 1) for name, area in areas.items()},
        "gap_designed_mm": float(spec["envelope"]["clearance"]),
    }
    return {"pieces": pieces, "fasteners": fasteners, "shortfall": shortfall,
            "pilots": Part.makeCompound(pilots) if pilots else None, "facts": facts}
