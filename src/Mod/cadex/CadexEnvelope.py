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
#: How far down a boss may reach for the frame, mm.
BOSS_REACH_MM = 60.0
#: Material kept under a screw head, and around a hole, mm.
SEAT_FLOOR_MM = 1.6
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
    """``count`` well-spread sites from ``[(x, y, length), ...]``.

    Farthest-point sampling, started at the candidate farthest from the
    candidates' centre (or from the indices in ``start``, kept first), each
    next site the one farthest from those chosen; a long boss is penalised
    by ``length_weight`` per mm, so a short reach to the frame wins a near
    tie. Returns the chosen indices.
    """

    if not candidates or count <= 0:
        return []
    chosen = list(start)
    if not chosen:
        cx = sum(c[0] for c in candidates) / len(candidates)
        cy = sum(c[1] for c in candidates) / len(candidates)
        chosen = [max(range(len(candidates)),
                      key=lambda k: math.hypot(candidates[k][0] - cx, candidates[k][1] - cy)
                      - length_weight * candidates[k][2])]
    while len(chosen) < min(count, len(candidates)):
        best, best_score = None, -math.inf
        for k, (x, y, length) in enumerate(candidates):
            if k in chosen:
                continue
            spread = min(math.hypot(x - candidates[c][0], y - candidates[c][1]) for c in chosen)
            score = spacing_weight * spread - length_weight * length
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
    triangles = sum(len(t) for t in covered_world)
    if triangles > MAX_TRIANGLES:
        raise EnvelopeError(
            f"the covered parts and their motion are {triangles} triangles, more than one "
            f"envelope reads ({MAX_TRIANGLES}); cover fewer parts, or sweep a shorter range")
    covered = [local(t.reshape(-1, 3)).reshape(-1, 3, 3) for t in covered_world]
    allpts = np.concatenate([t.reshape(-1, 3) for t in covered])
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
        for tris in covered:
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
    openings_facts = []
    for entry in spec.get("openings") or []:
        hole = _opening_mask(entry, X, Y, filled, outer_face, R, grid, h, shape_sets, poses,
                             local, occupancy, closed_distance)
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
    phi = ndimage.gaussian_filter(phi, 1.0) - 0.5 * h - inset
    # -- the inner face as a B-spline, over the region's box -----------------
    rows = np.nonzero(region.any(axis=1))[0]
    cols = np.nonzero(region.any(axis=0))[0]
    margin = int(math.ceil((thickness + 3.0) / h)) + 2
    i0, i1 = max(rows[0] - margin, 0), min(rows[-1] + margin, nx - 1)
    j0, j1 = max(cols[0] - margin, 0), min(cols[-1] + margin, ny - 1)
    surface_z = _smooth_cover(filled, region, h, radius)
    stride = max(1, int(math.ceil(max(i1 - i0, j1 - j0) / 70.0)))
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
    spacing = max(3.0 * h, 3.0)
    # With a skirt the panel overhangs its own outline by the skirt's wall, so
    # the skirt's top runs inside the panel's wall: a lid over its walls, one
    # solid without any face of one lying on a face of the other.
    flange = spec.get("flange")
    grow = (0.6 + 0.25 * h + 1.5 * thickness) if flange else 0.0
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
    if flange:
        depth = BOSS_REACH_MM if flange == "frame" else float(flange)
        if flange == "frame" and frame_z is None:
            raise EnvelopeError('flange="frame" needs frame=: the part the skirt comes down to')
        # The wall's top is tucked under the panel's rim by the least that
        # makes the two one solid: the less it tucks, the less it eats into
        # the clearance at the rim.
        for tuck in (0.0, 0.5, 1.0):
            walls, facts_now = _skirt(planar, surface_z, outer_s,
                                      frame_z if flange == "frame" else None, field, xs, ys,
                                      grid, clearance, thickness, depth, App, Part, np,
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
                break
        else:
            flange_facts = (flange_facts or []) + [
                {"depth_mm": 0.0, "reason": "the skirt did not join the panel; it is left off"}]
    body = body_local.copy()
    body.transformShape(to_world, False, False)
    # -- seams ----------------------------------------------------------------
    pieces = _split(body, spec.get("seams") or [], float(spec.get("seam_gap") or 0.6),
                    App, Part)
    # -- mounts ------------------------------------------------------------------
    fasteners: dict[str, list] = {name: [] for name in pieces}
    pilots = []
    screw = spec.get("screw")
    per_piece = int(spec.get("screws") or 0)
    if frame_shape is not None and screw is not None and per_piece > 0:
        blockers = [tris for tris, is_frame in zip(covered_world, covered_is_frame)
                    if not is_frame]
        fasteners, pilots, pieces = _mount(
            pieces, frame_shape, screw, per_piece, phi, surface_z, outer_s, frame_z,
            column_room, skirted, xs, ys, R, s, h, spec,
            np.concatenate(blockers) if blockers else None, App, Part, np, ndimage,
            taken=_taken_screws(spec, plan_of))
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


def _plane_wire(loop, z, spacing, App, Part):
    """The same loop as a closed curve in the plane ``z``."""

    curve = Part.BSplineCurve()
    curve.interpolate([App.Vector(x, y, z) for x, y in _loop_points(loop, spacing)],
                      PeriodicFlag=True)
    return Part.Wire([curve.toShape()])


def _opening_mask(entry, X, Y, inner, outer, R, grid, h, shape_sets, poses, local,
                  occupancy_fn, distance_fn):
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
    return mask


def _sample2d(values, xs, ys, x, y):
    """Bilinear samples of a grid field at points ``(x, y)``."""

    import numpy as np
    from scipy import ndimage

    h = float(xs[1] - xs[0])
    coords = np.vstack([(np.asarray(x) - xs[0]) / h, (np.asarray(y) - ys[0]) / h])
    return ndimage.map_coordinates(values, coords, order=1, mode="nearest")


def _skirt(planar, surface_z, outer_s, frame_z, field, xs, ys, grid, clearance, thickness,
           depth, App, Part, np, tuck=0.6):
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
    spacing = max(3.0 * h, 3.0)
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
        P = P + normal * (0.6 + 0.25 * h)
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
        first_bad = np.where(bad.any(axis=1), np.argmax(bad, axis=1), len(steps) - 1)
        allowed = steps[np.maximum(first_bad - 1, 0)]
        bottom = rim - np.minimum(allowed, depth)
        if frame_z is not None:
            under = _sample2d(np.nan_to_num(frame_z, nan=-1e9), xs, ys, mid[:, 0], mid[:, 1])
            seated = under > -1e8
            if not seated.any():
                facts.append({"depth_mm": 0.0, "reason": "no frame under the outline"})
                continue
            bottom = np.maximum(bottom, np.where(seated, under + 0.2, bottom))
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
            piece = piece.common(slab)
        name = f"p{index}"
        if not piece.Solids:
            raise EnvelopeError(
                f"piece {name} of the seams {[(list(g['normal']), list(g['at'])) for g in seams]} "
                "is empty: a seam lies outside the panel")
        import os
        if len(piece.Solids) > 1 and os.environ.get("CADEX_ENVELOPE_KEEP_ISLANDS"):
            pieces[name] = piece
            continue
        if len(piece.Solids) > 1:
            sizes = sorted((round(abs(s.Volume)) for s in piece.Solids), reverse=True)
            raise EnvelopeError(
                f"piece {name} falls apart into {len(sizes)} solids ({sizes} mm3): its region "
                "is not one patch -- an opening, max_angle= or within= parts it; narrow "
                "within= to one patch, or add a seam between them")
        pieces[name] = _sound(piece.Solids[0], f"piece {name}")
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
                "covers; put frame under the panel there, lower screws=, add flange=\"frame\" "
                "for lugs on its skirt, or seam the piece")
        bosses, holes, rows_out = [], [], []
        for index, (site, exact) in enumerate(accepted):
            q, top_point, well_top, frame_thick = exact
            total = (top_point - q).Length
            engage = min(max(2.5 * d, 4.0), length - SEAT_FLOOR_MM - 0.2)
            if frame_thick is not None:
                engage = min(engage, max(frame_thick - 0.6, 1.5 * d))
            seat = max(0.0, total + engage - length)
            if total - seat < SEAT_FLOOR_MM - 1e-6:
                raise EnvelopeError(
                    f"piece {name}: an {str(screw['size']).upper()}x{length:g} reaches "
                    f"{total + engage:.1f} mm of boss here; choose a longer screw")
            engagement = seat + length - total
            head_seat = top_point - sv * seat
            bosses.append(Part.makeCylinder(boss_r, total, q, sv))
            holes.append(Part.makeCylinder(clear_r, total + 4.0, q - sv * 1.0, sv))
            well = (well_top - head_seat).dot(sv)
            if well > 0.05:
                holes.append(Part.makeCylinder(head_r, well + 2.0, head_seat, sv))
            pilots.append(Part.makeCylinder(tap_r, engagement + 1.5,
                                            q - sv * (engagement + 1.5), sv))
            rows_out.append({
                "name": f"b{index}",
                "head_seat": [round(v, 4) for v in (head_seat.x, head_seat.y, head_seat.z)],
                "axis": [round(float(v), 6) for v in s],
                "roll": [round(float(v), 6) for v in R[0]],
                "frame_point": [round(v, 3) for v in (q.x, q.y, q.z)],
                "boss_length_mm": round(total, 2),
                "seat_depth_mm": round(well, 2),
                "engagement_mm": round(engagement, 2),
                "kind": "lug" if phi[site[3], site[4]] < boss_r else "boss",
            })
        grown = solid.fuse(bosses).cut(holes)
        solids = list(grown.Solids)
        if len(solids) != 1:
            raise EnvelopeError(f"piece {name}: the bosses did not fuse into one solid")
        out[name] = _sound(_refined(solids[0]), f"piece {name} with its bosses")
        fasteners[name] = rows_out
    return fasteners, pilots, out


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


def _refined(shape):
    """``shape`` with its splitter faces merged, or as it is when that fails."""

    try:
        refined = shape.removeSplitter()
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
