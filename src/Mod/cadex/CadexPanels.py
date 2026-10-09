# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Panels grown from what they cover, housings grown around drives.

``lib.panel`` (ADR-610) and ``lib.housing`` (ADR-611), and the arithmetic
the shell check (ADR-612) measures with.

Blind-rated agent robots scored worst on "every part designed, shells
included": the shells were superellipse rings sized by eye, eggs and domes
floating over electronics they never touched, and no drive had a housing.
A designer does it the other way round: the panel is drawn **from** what it
covers, at a small clearance, thin, split where it can be assembled, and
screwed to the frame that carries it. That is what this module computes.

**How a panel finds its shape.** A script builds recipes, not kernel
shapes, so nothing here can ask OCCT where a solid is. It does not need to:
every part value is a tree of primitives (boxes, cylinders, cones,
spheres), transforms and booleans, and the tree says where its material
can be. :func:`sample` reads a recipe into surface points and, where the
tree allows it, a point-membership test -- a small CSG evaluator over the
same payloads the worker builds from. The panel then stands stations along
its axis; at each one the covered points in a window either side are
fitted with the tightest superellipse (``CadexCage``'s ring, with its own
centre and aspect), grown by the clearance; the skin is the loft through
those rings and the panel the outer loft less the inner. Every number the
screws need -- where the frame is under each boss, how long each bolt is
-- is known here, in Python, so ``.screws`` are ordinary ``lib.bolt`` parts.

**How a housing finds its shape.** A drive publishes its envelope: a QDD's
coaxial ``segments`` and stator bolt circles, a servo's case, tabs and
holes. The housing is that envelope at ``clearance``, wrapped in ``wall``,
seated on the drive's own mounting face and screwed to it through its own
holes, open where the output and the leads come out.

Like ``CadexCage`` this module imports nothing from FreeCAD at module
scope, so the planning half is unit-tested headless; only
:func:`gap_statistics` (the check's measuring half, run in the assembly
worker) imports numpy, and only when it is called.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Iterable, Mapping, Sequence

__all__ = [
    "PanelError",
    "Sample",
    "sample",
    "fit_ring",
    "ring_radius",
    "ring_points_2d",
    "plan_panel",
    "build_panel",
    "build_housing",
    "PanelSet",
    "Housing",
    "gap_statistics",
    "STANDARD_SCREW_LENGTHS_MM",
]


class PanelError(ValueError):
    """A panel or housing request that cannot be met, with the reason."""


#: Socket-head lengths a hardware store stocks, the ones a screw is rounded to.
STANDARD_SCREW_LENGTHS_MM = (3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0,
                             18.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0)

#: The superellipse ring's sample count: the cage's, so a panel reads like one.
RING_SAMPLES = 64

#: How fast a panel's half-axes may fall away along its axis (mm per mm):
#: about 9 degrees, a gentle curve over what it covers rather than a dimple.
MAX_SKIN_SLOPE = 0.15

_TINY = 1.0e-9


# ---------------------------------------------------------------------------
# small vector algebra


def _add(a, b):
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]


def _sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def _scale(a, s):
    return [a[0] * s, a[1] * s, a[2] * s]


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def _norm(a):
    return math.sqrt(_dot(a, a))


def _unit(a, what="direction"):
    length = _norm(a)
    if length <= 1.0e-12:
        raise PanelError(f"{what} must not be zero")
    return [a[0] / length, a[1] / length, a[2] / length]


def _matvec(m, v):
    return [m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
            m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
            m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2]]


def _matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)]
            for i in range(3)]


def _transpose(m):
    return [[m[j][i] for j in range(3)] for i in range(3)]


def _inverse(m):
    det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
           - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
           + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
    if abs(det) <= 1.0e-15:
        raise PanelError("a transform in the covered parts is singular")
    inv = [[0.0] * 3 for _ in range(3)]
    inv[0][0] = (m[1][1] * m[2][2] - m[1][2] * m[2][1]) / det
    inv[0][1] = (m[0][2] * m[2][1] - m[0][1] * m[2][2]) / det
    inv[0][2] = (m[0][1] * m[1][2] - m[0][2] * m[1][1]) / det
    inv[1][0] = (m[1][2] * m[2][0] - m[1][0] * m[2][2]) / det
    inv[1][1] = (m[0][0] * m[2][2] - m[0][2] * m[2][0]) / det
    inv[1][2] = (m[0][2] * m[1][0] - m[0][0] * m[1][2]) / det
    inv[2][0] = (m[1][0] * m[2][1] - m[1][1] * m[2][0]) / det
    inv[2][1] = (m[0][1] * m[2][0] - m[0][0] * m[2][1]) / det
    inv[2][2] = (m[0][0] * m[1][1] - m[0][1] * m[1][0]) / det
    return inv


def _rotation(axis, degrees):
    """Rodrigues: the matrix turning ``degrees`` about the unit ``axis``."""

    x, y, z = _unit(axis, "rotation_axis")
    angle = math.radians(degrees)
    c, s, t = math.cos(angle), math.sin(angle), 1.0 - math.cos(angle)
    return [[t * x * x + c, t * x * y - s * z, t * x * z + s * y],
            [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
            [t * x * z - s * y, t * y * z + s * x, t * z * z + c]]


def _rotation_between(source, target):
    """The shortest-arc rotation carrying ``source`` onto ``target``.

    ``App.Rotation(from, to)``'s choice, which is how the worker aims a
    prism; antiparallel turns half a turn about an axis across both.
    """

    a, b = _unit(source), _unit(target)
    cross = _cross(a, b)
    sine = _norm(cross)
    cosine = max(-1.0, min(1.0, _dot(a, b)))
    if sine <= 1.0e-12:
        if cosine > 0.0:
            return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        helper = [1.0, 0.0, 0.0] if abs(a[0]) < 0.9 else [0.0, 1.0, 0.0]
        return _rotation(_cross(a, helper), 180.0)
    return _rotation(cross, math.degrees(math.atan2(sine, cosine)))


def _occ_frame(direction):
    """``gp_Ax2(P, V)``'s X and Y directions, as OCCT picks them.

    ``Part.makeBox(..., pnt, dir)`` and ``makeCylinder(..., angle)`` build
    in that frame, so a box aimed off +Z lands where this says it does.
    """

    a, b, c = _unit(direction)
    aa, ba, ca = abs(a), abs(b), abs(c)
    if ba <= aa and ba <= ca:
        x = [-c, 0.0, a] if aa > ca else [c, 0.0, -a]
    elif aa <= ba and aa <= ca:
        x = [0.0, -c, b] if ba > ca else [0.0, c, -b]
    else:
        x = [-b, a, 0.0] if aa > ba else [b, -a, 0.0]
    x = _unit(x)
    z = [a, b, c]
    return x, _cross(z, x), z


def _frame_matrix(direction):
    """Columns X, Y, Z of the OCCT frame aimed along ``direction``."""

    x, y, z = _occ_frame(direction)
    return [[x[0], y[0], z[0]], [x[1], y[1], z[1]], [x[2], y[2], z[2]]]


def axis_angle(matrix):
    """``(axis, degrees)`` of a rotation matrix, for ``part.transform``."""

    trace = matrix[0][0] + matrix[1][1] + matrix[2][2]
    cosine = max(-1.0, min(1.0, (trace - 1.0) / 2.0))
    angle = math.acos(cosine)
    if angle <= 1.0e-9:
        return [0.0, 0.0, 1.0], 0.0
    if math.pi - angle <= 1.0e-6:
        # Half a turn: the axis is the column of (R + I) with the largest norm.
        best = None
        for column in range(3):
            v = [matrix[row][column] + (1.0 if row == column else 0.0) for row in range(3)]
            if best is None or _norm(v) > _norm(best):
                best = v
        return _unit(best), 180.0
    s = 2.0 * math.sin(angle)
    axis = [(matrix[2][1] - matrix[1][2]) / s, (matrix[0][2] - matrix[2][0]) / s,
            (matrix[1][0] - matrix[0][1]) / s]
    return _unit(axis), math.degrees(angle)


# ---------------------------------------------------------------------------
# reading a recipe: surface points and, where the tree allows, membership


class Sample:
    """What a recipe says about where its material is.

    ``points`` are world points on (or, after a boolean, near) its surface,
    at about the sampling spacing. ``contains(p)`` is True, False, or None
    when the recipe cannot say -- a loft, an offset or a partial revolve is
    sampled for its envelope but never trusted for membership.
    """

    __slots__ = ("points", "contains")

    def __init__(self, points: list, contains: Callable[[Sequence[float]], Any] | None):
        self.points = points
        self.contains = contains or (lambda _p: None)

    def bounds(self):
        if not self.points:
            return None
        return ([min(p[i] for p in self.points) for i in range(3)],
                [max(p[i] for p in self.points) for i in range(3)])


def _payload(value):
    """``(operation, arguments, properties)`` of a part value or its payload."""

    body = getattr(value, "body", None)
    if body is not None and hasattr(body, "operation"):
        value = body
    if hasattr(value, "operation") and hasattr(value, "arguments"):
        return (str(value.operation), list(value.arguments),
                dict(value.properties or {}), getattr(value, "domain", "part"))
    if isinstance(value, Mapping) and "operation" in value:
        return (str(value["operation"]), list(value.get("arguments") or []),
                dict(value.get("properties") or {}), str(value.get("domain") or "part"))
    raise PanelError(
        f"expected a part value (a part.* solid or a lib.* part); received {value!r}")


def _vec(value, default=(0.0, 0.0, 0.0)):
    if value is None:
        value = default
    return [float(v) for v in list(value)[:3]]


def _count(length, spacing, minimum=1):
    return max(minimum, int(math.ceil(abs(length) / spacing)))


def _grid(n):
    return [i / float(n) for i in range(n + 1)]


def _box_local(l, w, h, s):
    """Surface points of [0,l]x[0,w]x[0,h] at about spacing ``s``."""

    points = []
    nl, nw, nh = _count(l, s), _count(w, s), _count(h, s)
    for a in _grid(nl):
        for b in _grid(nw):
            points.append([a * l, b * w, 0.0])
            points.append([a * l, b * w, h])
    for a in _grid(nl):
        for c in _grid(nh)[1:-1]:
            points.append([a * l, 0.0, c * h])
            points.append([a * l, w, c * h])
    for b in _grid(nw)[1:-1]:
        for c in _grid(nh)[1:-1]:
            points.append([0.0, b * w, c * h])
            points.append([l, b * w, c * h])
    return points


def _revolved_local(profile, s, sweep=360.0):
    """Points on the surface of revolution of ``[(r, z)]`` profile samples."""

    points = []
    for r, z in profile:
        n = max(12, _count(2.0 * math.pi * r * sweep / 360.0, s))
        for k in range(n if sweep >= 360.0 else n + 1):
            t = math.radians(sweep * k / float(n))
            points.append([r * math.cos(t), r * math.sin(t), z])
    return points


def _frustum_profile(r1, r2, h, s):
    profile = []
    for t in _grid(_count(h, s)):
        profile.append((r1 + (r2 - r1) * t, h * t))
    for r, z in ((r1, 0.0), (r2, h)):
        for t in _grid(_count(r, s))[:-1]:
            profile.append((r * t, z))
    return profile


def _placed(points, matrix, origin):
    return [_add(_matvec(matrix, p), origin) for p in points]


def _placed_contains(inside, matrix, origin):
    inverse = _inverse(matrix)
    return lambda p: inside(_matvec(inverse, _sub(p, origin)))


def _unknown(_p):
    return None


def _any(values):
    seen_none = False
    for value in values:
        if value is True:
            return True
        if value is None:
            seen_none = True
    return None if seen_none else False


_PASS_THROUGH = {"fillet", "chamfer", "refine", "defeature", "repair", "to_nurbs",
                 "reverse", "solid", "shell", "sew", "mate"}

#: Points per sampled primitive, past which the spacing is coarsened.
_MAX_POINTS = 6000


def sample(value: Any, spacing: float = 3.0, _cache: dict | None = None) -> Sample:
    """Read a part recipe into surface points and a membership test.

    Supported: the primitives (``box``, ``cylinder``, ``cone``, ``sphere``,
    ``torus``, ``prism``, ``wedge``), ``transform``, ``mirror``, ``fuse``,
    ``compound``, ``cut``, ``common``, the edge finishes, and the profile
    operations (``extrude``, ``revolve``, ``loft``, ``loft_cage``) for their
    envelope. Anything else -- an imported or meshed part, a reference -- is
    refused by name, because a panel fitted to a guess is the egg again.
    """

    cache = {} if _cache is None else _cache
    key = id(value)
    if key in cache:
        return cache[key][1]
    result = _sample(value, float(spacing), cache)
    cache[key] = (value, result)  # keep value alive so ids stay unique
    return result


def _sample(value, s, cache):
    operation, args, props, domain = _payload(value)
    if domain not in ("part", ""):
        raise PanelError(
            f"cannot read the extent of a {domain}.{operation} value; give the "
            "part.* solids or lib.* parts the panel covers")
    origin = _vec(props.get("origin"))
    direction = _vec(props.get("direction"), (0.0, 0.0, 1.0))

    if operation in ("box", "wedge"):
        l, w, h = (float(v) for v in args[:3])
        while (2 * (l * w + w * h + l * h)) / (s * s) > _MAX_POINTS:
            s *= 1.5
        matrix = _frame_matrix(direction)
        local = _box_local(l, w, h, s)
        if operation == "box":
            def inside(p, l=l, w=w, h=h):
                return (-1e-9 <= p[0] <= l + 1e-9 and -1e-9 <= p[1] <= w + 1e-9
                        and -1e-9 <= p[2] <= h + 1e-9)
            return Sample(_placed(local, matrix, origin),
                          _placed_contains(inside, matrix, origin))
        return Sample(_placed(local, matrix, origin), _unknown)

    if operation in ("cylinder", "cone"):
        if operation == "cylinder":
            r1 = r2 = float(args[0])
            h = float(args[1])
        else:
            r1, r2, h = float(args[0]), float(args[1]), float(args[2])
        sweep = float(props.get("angle", 360.0))
        while (2 * math.pi * max(r1, r2) * (h + max(r1, r2))) / (s * s) > _MAX_POINTS:
            s *= 1.5
        matrix = _frame_matrix(direction)
        local = _revolved_local(_frustum_profile(r1, r2, h, s), s, sweep)
        if sweep < 360.0:
            return Sample(_placed(local, matrix, origin), _unknown)

        def inside(p, r1=r1, r2=r2, h=h):
            if p[2] < -1e-9 or p[2] > h + 1e-9:
                return False
            r = r1 + (r2 - r1) * min(max(p[2] / h, 0.0), 1.0)
            return p[0] * p[0] + p[1] * p[1] <= r * r + 1e-9
        return Sample(_placed(local, matrix, origin), _placed_contains(inside, matrix, origin))

    if operation == "sphere":
        r = float(args[0])
        centre = _vec(props.get("center"))
        lat1, lat2 = float(props.get("latitude1", -90.0)), float(props.get("latitude2", 90.0))
        lon = float(props.get("longitude", 360.0))
        matrix = _frame_matrix(direction)
        profile = []
        for t in _grid(_count(math.pi * r * (lat2 - lat1) / 180.0, s)):
            phi = math.radians(lat1 + (lat2 - lat1) * t)
            profile.append((r * math.cos(phi), r * math.sin(phi)))
        local = _revolved_local(profile, s, lon)
        full = lat1 <= -90.0 and lat2 >= 90.0 and lon >= 360.0
        if not full:
            return Sample(_placed(local, matrix, centre), _unknown)
        return Sample(_placed(local, matrix, centre),
                      lambda p, c=centre, r=r: _dot(_sub(p, c), _sub(p, c)) <= r * r + 1e-9)

    if operation == "torus":
        major, minor = float(args[0]), float(args[1])
        centre = _vec(props.get("center"))
        matrix = _frame_matrix(direction)
        profile = []
        for t in _grid(_count(2.0 * math.pi * minor, s, 12))[:-1]:
            a = 2.0 * math.pi * t
            profile.append((major + minor * math.cos(a), minor * math.sin(a)))
        sweep = float(props.get("sweep", 360.0))
        local = _revolved_local(profile, s, sweep)
        full = (float(props.get("angle1", -180.0)) <= -180.0
                and float(props.get("angle2", 180.0)) >= 180.0 and sweep >= 360.0)
        if not full:
            return Sample(_placed(local, matrix, centre), _unknown)

        def inside(p, R=major, r=minor):
            q = math.sqrt(p[0] * p[0] + p[1] * p[1]) - R
            return q * q + p[2] * p[2] <= r * r + 1e-9
        return Sample(_placed(local, matrix, centre), _placed_contains(inside, matrix, centre))

    if operation == "prism":
        sides, radius, h = int(args[0]), float(args[1]), float(args[2])
        centre = _vec(props.get("center"))
        turn = math.radians(float(props.get("rotation_degrees", 0.0)))
        matrix = _rotation_between([0.0, 0.0, 1.0], direction)
        corners = [(radius * math.cos(turn + 2 * math.pi * k / sides),
                    radius * math.sin(turn + 2 * math.pi * k / sides)) for k in range(sides)]
        local = []
        for k in range(sides):
            (x0, y0), (x1, y1) = corners[k], corners[(k + 1) % sides]
            edge = math.hypot(x1 - x0, y1 - y0)
            for a in _grid(_count(edge, s))[:-1]:
                x, y = x0 + (x1 - x0) * a, y0 + (y1 - y0) * a
                for c in _grid(_count(h, s)):
                    local.append([x, y, c * h])
                for f in _grid(_count(radius, s))[1:-1]:
                    local.append([x * f, y * f, 0.0])
                    local.append([x * f, y * f, h])
        apothem = radius * math.cos(math.pi / sides)

        def inside(p, h=h):
            if p[2] < -1e-9 or p[2] > h + 1e-9:
                return False
            for k in range(sides):
                mid = turn + 2 * math.pi * (k + 0.5) / sides
                if p[0] * math.cos(mid) + p[1] * math.sin(mid) > apothem + 1e-9:
                    return False
            return True
        return Sample(_placed(local, matrix, centre), _placed_contains(inside, matrix, centre))

    if operation == "transform":
        child = sample(args[0], s, cache)
        pivot = _vec(props.get("pivot"))
        factors = [float(v) for v in (props.get("scale") or [1.0, 1.0, 1.0])]
        matrix = [[factors[0], 0.0, 0.0], [0.0, factors[1], 0.0], [0.0, 0.0, factors[2]]]
        degrees = float(props.get("rotation_degrees", 0.0))
        if abs(degrees) > 1.0e-12:
            matrix = _matmul(_rotation(_vec(props.get("rotation_axis"), (0, 0, 1)), degrees), matrix)
        shift = _add(_sub(pivot, _matvec(matrix, pivot)), _vec(props.get("translation")))
        return Sample(_placed(child.points, matrix, shift),
                      _placed_contains(child.contains, matrix, shift))

    if operation == "mirror":
        child = sample(args[0], s, cache)
        point = _vec(args[1])
        normal = _unit(_vec(args[2]))
        n = normal
        matrix = [[1.0 - 2 * n[0] * n[0], -2 * n[0] * n[1], -2 * n[0] * n[2]],
                  [-2 * n[1] * n[0], 1.0 - 2 * n[1] * n[1], -2 * n[1] * n[2]],
                  [-2 * n[2] * n[0], -2 * n[2] * n[1], 1.0 - 2 * n[2] * n[2]]]
        shift = _sub(point, _matvec(matrix, point))
        return Sample(_placed(child.points, matrix, shift),
                      _placed_contains(child.contains, matrix, shift))

    if operation in ("fuse", "compound", "general_fuse"):
        children = [sample(item, s, cache) for item in list(args[0])]
        points = [p for child in children for p in child.points]
        tests = [child.contains for child in children]
        return Sample(points, lambda p: _any(test(p) for test in tests))

    if operation == "cut":
        base = sample(args[0], s, cache)
        tools = [sample(item, s, cache) for item in list(args[1])]
        kept = [p for p in base.points if not any(t.contains(p) is True for t in tools)]
        # The pocket walls a tool leaves inside the base are surface too.
        for index, tool in enumerate(tools):
            for p in tool.points:
                if base.contains(p) is True and not any(
                        other.contains(p) is True for j, other in enumerate(tools) if j != index):
                    kept.append(p)

        def inside(p):
            held = base.contains(p)
            if held is False:
                return False
            removed = _any(t.contains(p) for t in tools)
            if removed is True:
                return False
            if held is True and removed is False:
                return True
            return None
        return Sample(kept, inside)

    if operation == "common":
        children = [sample(item, s, cache) for item in list(args[0])]
        points = []
        for index, child in enumerate(children):
            others = [c for j, c in enumerate(children) if j != index]
            points.extend(p for p in child.points
                          if all(o.contains(p) is not False for o in others))

        def inside(p):
            values = [c.contains(p) for c in children]
            if any(v is False for v in values):
                return False
            return True if all(v is True for v in values) else None
        return Sample(points, inside)

    if operation in _PASS_THROUGH:
        child = sample(args[0], s, cache)
        return Sample(child.points, child.contains if operation in (
            "refine", "to_nurbs", "reverse", "solid", "shell", "sew") else _unknown)

    if operation in ("offset", "thicken"):
        child = sample(args[0], s, cache)
        distance = abs(float(args[1] if operation == "offset" else args[2]))
        bounds = child.bounds()
        if bounds is None:
            return Sample([], _unknown)
        centre = [(bounds[0][i] + bounds[1][i]) / 2.0 for i in range(3)]
        points = []
        for p in child.points:
            d = _sub(p, centre)
            length = _norm(d)
            points.append(p if length <= _TINY else _add(p, _scale(d, distance / length)))
        return Sample(points, _unknown)

    # -- profiles: envelope only ------------------------------------------
    if operation in ("line", "arc", "circle", "ellipse", "bezier", "bspline",
                     "nurbs_curve", "wire", "face", "plane", "helix"):
        return Sample(_curve_points(operation, args, props, s, cache), _unknown)

    if operation == "extrude":
        base = sample(args[0], s, cache)
        vector = _vec(args[1])
        steps = _count(_norm(vector), s)
        return Sample([_add(p, _scale(vector, t)) for t in _grid(steps) for p in base.points],
                      _unknown)

    if operation == "revolve":
        base = sample(args[0], s, cache)
        pivot, axis = _vec(args[1]), _unit(_vec(args[2]))
        sweep = float(props.get("angle", 360.0))
        reach = max((_norm(_sub(p, pivot)) for p in base.points), default=0.0)
        steps = max(12, _count(math.radians(sweep) * reach, s))
        points = []
        for k in range(steps + 1):
            matrix = _rotation(axis, sweep * k / float(steps))
            points.extend(_add(_matvec(matrix, _sub(p, pivot)), pivot) for p in base.points)
        return Sample(points, _unknown)

    if operation == "loft":
        sections = [sample(item, s, cache).points for item in list(args[0])]
        return Sample(_between_sections(sections, s), _unknown)

    if operation == "loft_cage":
        from CadexCage import ring_points

        definition = dict(args[0])
        rings = [ring_points(row, axis=definition.get("axis") or (1, 0, 0),
                             origin=definition.get("origin") or (0, 0, 0),
                             up=definition.get("up") or (0, 0, 1))
                 for row in definition.get("rings") or []]
        return Sample(_between_sections(rings, s), _unknown)

    raise PanelError(
        f"cannot read the extent of a part.{operation} value: it is not built "
        "from primitives and booleans this helper can follow. Pass the solids "
        "the panel covers, or a part.box keep-out standing in for this one")


def _between_sections(sections, s):
    points = [p for section in sections for p in section]
    for first, second in zip(sections, sections[1:]):
        if not first or not second:
            continue
        gap = max(_norm(_sub(first[0], second[0])), _TINY)
        steps = _count(gap, s)
        if len(first) == len(second):
            pairs = list(zip(first, second))
        else:
            # Different sample counts: pair by index fraction.
            pairs = [(first[i], second[int(i * len(second) / len(first))])
                     for i in range(len(first))]
        for t in _grid(steps)[1:-1]:
            points.extend(_add(a, _scale(_sub(b, a), t)) for a, b in pairs)
    return points


def _curve_points(operation, args, props, s, cache):
    if operation == "line":
        a, b = _vec(args[0]), _vec(args[1])
        return [_add(a, _scale(_sub(b, a), t)) for t in _grid(_count(_norm(_sub(b, a)), s))]
    if operation in ("circle", "arc", "ellipse"):
        if operation == "arc":
            return [_vec(p) for p in args[:3]]
        centre = _vec(props.get("center"))
        normal = _vec(props.get("normal"), (0.0, 0.0, 1.0))
        if operation == "circle":
            r1 = r2 = float(args[0])
        else:
            r1, r2 = float(args[0]), float(args[1])
        x, y, _z = _occ_frame(normal)
        if operation == "ellipse" and props.get("major_direction") is not None:
            x = _unit(_vec(props["major_direction"]))
            y = _cross(_unit(normal), x)
        n = max(16, _count(2 * math.pi * max(r1, r2), s))
        return [_add(centre, _add(_scale(x, r1 * math.cos(2 * math.pi * k / n)),
                                  _scale(y, r2 * math.sin(2 * math.pi * k / n))))
                for k in range(n)]
    if operation in ("bezier", "bspline", "nurbs_curve"):
        return [_vec(p) for p in list(args[0])]
    if operation == "helix":
        return []
    if operation == "plane":
        l, w = float(args[0]), float(args[1])
        origin = _vec(props.get("origin"))
        normal = _unit(_vec(props.get("normal"), (0, 0, 1)))
        x = _unit(_vec(props.get("x_direction"), (1, 0, 0)))
        y = _cross(normal, x)
        return [_add(origin, _add(_scale(x, a * l), _scale(y, b * w)))
                for a in _grid(_count(l, s)) for b in _grid(_count(w, s))]
    if operation == "wire":
        items = list(args[0])
        if items and all(isinstance(item, (list, tuple)) for item in items):
            vertices = [_vec(p) for p in items]
            if props.get("closed") and vertices:
                vertices.append(vertices[0])
            points = []
            for a, b in zip(vertices, vertices[1:]):
                points.extend(_add(a, _scale(_sub(b, a), t))
                              for t in _grid(_count(_norm(_sub(b, a)), s))[:-1])
            return points + vertices[-1:]
        return [p for item in items for p in sample(item, s, cache).points]
    if operation == "face":
        return [p for item in args[:1] for p in sample(item, s, cache).points]
    return []


# ---------------------------------------------------------------------------
# the superellipse ring


def _spow(value, power):
    magnitude = abs(value) ** power
    return magnitude if value >= 0.0 else -magnitude


def ring_radius(a: float, b: float, exponent: float, angle_degrees: float) -> float:
    """Distance from a ring's centre to its curve along one direction."""

    t = math.radians(angle_degrees)
    c, s = abs(math.cos(t)), abs(math.sin(t))
    value = (c / a) ** exponent + (s / b) ** exponent
    return 1.0 / value ** (1.0 / exponent)


def ring_points_2d(cu, cv, a, b, exponent, samples=RING_SAMPLES):
    """The ring as ``(u, v)`` points: ``CadexCage.ring_points``' curve, off-axis."""

    power = 2.0 / exponent
    return [(cu + a * _spow(math.cos(2 * math.pi * k / samples), power),
             cv + b * _spow(math.sin(2 * math.pi * k / samples), power))
            for k in range(samples)]


def _norm_value(du, dv, a, b, n):
    return ((abs(du) / a) ** n + (abs(dv) / b) ** n) ** (1.0 / n)


def fit_ring(points_uv: Sequence[Sequence[float]], *, centre: Sequence[float],
             exponent: float, offset: float, minimum_half: float = 2.0,
             search_aspect: bool = False) -> tuple[float, float]:
    """The tightest ring of this exponent and centre around the points, grown.

    The aspect is the points' own box's (``search_aspect`` searches it for
    the least area instead -- tighter on one section, but it jumps from
    station to station, so a panel does not); the scale is the least that
    contains every point; the
    clearance is then checked as a true distance to the curve and the ring
    grown until every point clears it by ``offset``.
    """

    cu, cv = float(centre[0]), float(centre[1])
    deltas = [(p[0] - cu, p[1] - cv) for p in points_uv]
    if not deltas:
        return minimum_half + offset, minimum_half + offset
    half_u = max(max(abs(d[0]) for d in deltas), minimum_half)
    half_v = max(max(abs(d[1]) for d in deltas), minimum_half)
    best = None
    for stretch in ([0.6 + 0.1 * k for k in range(13)] if search_aspect else [1.0]):
        a0, b0 = half_u * stretch, half_v
        k_scale = max(_norm_value(du, dv, a0, b0, exponent) for du, dv in deltas)
        a, b = a0 * k_scale, b0 * k_scale
        area = a * b
        if best is None or area < best[0]:
            best = (area, a, b)
    _area, a, b = best
    a, b = max(a, minimum_half) + offset, max(b, minimum_half) + offset
    # The superellipse grown by `offset` on both axes is not the curve's
    # offset; measure the clearance the points actually get and close it.
    ranked = sorted(deltas, key=lambda d: -_norm_value(d[0], d[1], a, b, exponent))
    extreme = ranked[:160]
    for _ in range(4):
        curve = ring_points_2d(0.0, 0.0, a, b, exponent, 96)
        worst = offset
        for du, dv in extreme:
            nearest = min(math.hypot(du - x, dv - y) for x, y in curve)
            inside = _norm_value(du, dv, a, b, exponent) <= 1.0
            clearance = nearest if inside else -nearest
            worst = min(worst, clearance)
        short = offset - worst
        if short <= 0.02:
            break
        a, b = a + short + 0.02, b + short + 0.02
    return a, b


# ---------------------------------------------------------------------------
# planning a panel (pure)


class _Frame:
    """The panel's frame: ``u`` across, ``v`` up, ``w`` along the axis."""

    def __init__(self, axis, up):
        self.w = _unit(axis, "lib.panel axis")
        if up is None:
            up = [0.0, 1.0, 0.0] if abs(self.w[2]) > 0.9 else [0.0, 0.0, 1.0]
        up = _vec(up)
        along = _dot(up, self.w)
        v = _sub(up, _scale(self.w, along))
        if _norm(v) <= 1.0e-9:
            raise PanelError("lib.panel up must not be parallel to axis")
        self.v = _unit(v)
        self.u = _cross(self.v, self.w)
        # World <- local: columns u, v, w.
        self.matrix = [[self.u[i], self.v[i], self.w[i]] for i in range(3)]

    def local(self, p):
        return [_dot(p, self.u), _dot(p, self.v), _dot(p, self.w)]

    def world(self, q):
        return _add(_add(_scale(self.u, q[0]), _scale(self.v, q[1])), _scale(self.w, q[2]))

    def world_dir(self, q):
        return self.world(q)


def _smooth(values, passes=2):
    out = list(values)
    for _ in range(passes):
        if len(out) < 3:
            break
        out = [out[0]] + [(out[i - 1] + 2 * out[i] + out[i + 1]) / 4.0
                          for i in range(1, len(out) - 1)] + [out[-1]]
    return out


_SPLITS = {
    None: (("all", None),),
    "top_bottom": (("top", 1), ("bottom", -1)),
    "left_right": (("right", 1), ("left", -1)),
}

#: Directions a boss may be aimed in, by piece side, in degrees about the
#: axis from +u (across) towards +v (up), most preferred first.
_BOSS_ANGLES = {
    "all": (90.0, 270.0, 0.0, 180.0, 45.0, 135.0, 225.0, 315.0),
    "top": (90.0, 45.0, 135.0),
    "bottom": (270.0, 225.0, 315.0),
    "right": (0.0, 45.0, 315.0),
    "left": (180.0, 135.0, 225.0),
}


def _choose_length(needed, longest=None):
    for length in STANDARD_SCREW_LENGTHS_MM:
        if length >= needed - 1e-6 and (longest is None or length <= longest + 1e-6):
            return length
    return None


#: The exponents ``exponent=None`` chooses among.
AUTO_EXPONENTS = (2.0, 2.5, 3.0, 4.0, 6.0)


def _superellipse_area_factor(n):
    """Area of ``|x|^n + |y|^n <= 1``: 4 Gamma(1+1/n)^2 / Gamma(1+2/n)."""

    return 4.0 * math.gamma(1.0 + 1.0 / n) ** 2 / math.gamma(1.0 + 2.0 / n)


def _section_area(rings, n):
    return sum(a * b for a, b in rings) * _superellipse_area_factor(n)


def _fit_rings(windows, stations, cu, cv, exponent, offset):
    """Each station's ring, then each half-axis as a slope-limited envelope."""

    rings = []
    for index in range(len(stations)):
        window = windows[index]
        if not window:
            # A gap in the contents: bridge it with the neighbours' ring.
            rings.append(None)
            continue
        rings.append(list(fit_ring(window, centre=(cu[index], cv[index]),
                                   exponent=exponent, offset=offset)))
    for index, ring in enumerate(rings):
        if ring is None:
            nearest = min((j for j, other in enumerate(rings) if other is not None),
                          key=lambda j: abs(j - index))
            rings[index] = list(rings[nearest])
    # A ring may only fall away from its neighbours at MAX_SKIN_SLOPE, so a
    # station whose window fitted a narrower ring fills in rather than
    # dimpling the skin, and no ring shrinks below what a station needed.
    for axis_index in (0, 1):
        values = [ring[axis_index] for ring in rings]
        for i, s in enumerate(stations):
            rings[i][axis_index] = max(values[j] - MAX_SKIN_SLOPE * abs(s - stations[j])
                                       for j in range(len(stations)))
    return rings


def plan_panel(cover: Sample, frame: Sample | None, *, axis, up=None, span=None,
               offset=1.5, thickness=2.0, exponent=None, step=12.0, seams=(),
               split=None, split_at=None, seam_gap=0.4, screw=None, screws_per_panel=2,
               engagement=None, spacing=3.0) -> dict[str, Any]:
    """Every number a panel needs, from the sampled contents (no kernel).

    ``cover`` is what the skin wraps (frame included), ``frame`` what it is
    screwed to. Returns the frame, the stations with their rings (centre,
    inner and outer half-axes), the pieces with their axial ranges and side,
    and per piece the bosses that reach the frame: station, angle, where the
    frame surface is, the seat, the screw length.
    """

    local_frame = _Frame(axis, up)
    if not cover.points:
        raise PanelError("lib.panel over= covers nothing: no surface to wrap")
    pts = [local_frame.local(p) for p in cover.points]
    ws = [p[2] for p in pts]
    if span is None:
        start, end = min(ws), max(ws)
    else:
        start, end = sorted(float(v) for v in span)
    if end - start < 2.0:
        raise PanelError("lib.panel span along the axis is under 2 mm")
    count = max(3, min(40, int(math.ceil((end - start) / float(step))) + 1))
    stations = [start + (end - start) * k / (count - 1) for k in range(count)]
    half = (end - start) / (count - 1)
    windows = []
    for s in stations:
        windows.append([(p[0], p[1]) for p in pts if abs(p[2] - s) <= half + 1e-9])
    # Centres: the window's box centre, smoothed along the spine so the skin
    # does not wobble with every part it passes.
    centres = []
    for index, window in enumerate(windows):
        if not window:
            centres.append(None)
            continue
        us, vs = [p[0] for p in window], [p[1] for p in window]
        centres.append(((min(us) + max(us)) / 2.0, (min(vs) + max(vs)) / 2.0))
    known = [c for c in centres if c is not None]
    if not known:
        raise PanelError("lib.panel span holds none of the covered parts")
    for index, c in enumerate(centres):
        if c is None:
            nearest = min((j for j, other in enumerate(centres) if other is not None),
                          key=lambda j: abs(j - index))
            centres[index] = centres[nearest]
    cu = _smooth([c[0] for c in centres])
    cv = _smooth([c[1] for c in centres])
    if exponent is None:
        # One exponent for the whole panel, the one whose skin encloses the
        # least section area: an ellipse over a narrow pack on a wide deck,
        # a rounded box over a box.
        candidates = [(_section_area(r, n), n, r) for n in AUTO_EXPONENTS
                      for r in [_fit_rings(windows, stations, cu, cv, n, offset)]]
        _area, exponent, rings = min(candidates, key=lambda row: row[0])
    else:
        rings = _fit_rings(windows, stations, cu, cv, exponent, offset)
    station_rows = [{
        "position": s, "centre": [cu[i], cv[i]],
        "inner": [rings[i][0], rings[i][1]],
        "outer": [rings[i][0] + thickness, rings[i][1] + thickness],
    } for i, s in enumerate(stations)]

    cuts = sorted(float(c) for c in (seams or ()))
    for c in cuts:
        if not start + 4.0 < c < end - 4.0:
            raise PanelError(
                f"lib.panel seam at {c:g} mm is not inside the panel's span "
                f"{start:.1f}..{end:.1f} mm along its axis (at least 4 mm from each end)")
    edges = [start] + cuts + [end]
    if split not in _SPLITS:
        raise PanelError(f"lib.panel split must be None, 'top_bottom' or 'left_right'; "
                         f"received {split!r}")
    part_at = None
    if split is not None:
        # The parting plane must cut every ring across its middle half, or a
        # piece pinches off into strips where the ring dips under it; within
        # that band it sits nearest the mean centre.
        index = 1 if split == "top_bottom" else 0
        centres_k = cv if index == 1 else cu
        lows = [centres_k[i] - 0.5 * rings[i][index] for i in range(len(stations))]
        highs = [centres_k[i] + 0.5 * rings[i][index] for i in range(len(stations))]
        band = (max(lows), min(highs))
        if band[0] > band[1]:
            raise PanelError(
                f"lib.panel split={split!r}: no one parting plane crosses every ring "
                "across its middle -- the panel steps too much along its axis. Split "
                "it at a seam first (seams=[...]) or narrow span=")
        mean = sum(centres_k) / len(centres_k)
        part_at = min(max(mean, band[0]), band[1])
    if split_at is not None:
        if split is None:
            raise PanelError("lib.panel split_at= needs split='top_bottom' or 'left_right'")
        part_at = float(split_at)
    pieces = []
    for k in range(len(edges) - 1):
        low = edges[k] + (seam_gap / 2.0 if k > 0 else 0.0)
        high = edges[k + 1] - (seam_gap / 2.0 if k + 1 < len(edges) - 1 else 0.0)
        for side, sign in _SPLITS[split]:
            pieces.append({"index": len(pieces), "station_range": [low, high],
                           "side": side, "sign": sign,
                           "name": f"{k}" + ("" if side == "all" else f"_{side}"),
                           "bosses": []})

    plan = {"frame": local_frame, "stations": station_rows, "pieces": pieces,
            "span": [start, end], "split_at": part_at, "split": split,
            "offset": offset, "thickness": thickness, "exponent": exponent,
            "seam_gap": seam_gap, "notes": []}
    if frame is not None and screw and screws_per_panel > 0:
        _plan_bosses(plan, cover, frame, screw, int(screws_per_panel), engagement, spacing)
    return plan


def _ring_at(plan, w):
    """Centre, inner and outer half-axes interpolated at axial ``w``."""

    rows = plan["stations"]
    if w <= rows[0]["position"]:
        row = rows[0]
        return row["centre"], row["inner"], row["outer"]
    for first, second in zip(rows, rows[1:]):
        if first["position"] <= w <= second["position"]:
            t = (w - first["position"]) / max(second["position"] - first["position"], _TINY)
            mix = lambda a, b: [a[i] + (b[i] - a[i]) * t for i in range(2)]
            return (mix(first["centre"], second["centre"]), mix(first["inner"], second["inner"]),
                    mix(first["outer"], second["outer"]))
    row = rows[-1]
    return row["centre"], row["inner"], row["outer"]


def _plan_bosses(plan, cover, frame, screw, wanted, engagement, spacing):
    import CadexCatalog as catalog

    head = catalog.socket_head_spec(screw)
    d = float(catalog.thread_spec(screw)["nominal_dia_mm"])
    boss_r = head["head_dia_mm"] / 2.0 + 1.6
    head_h = float(head["head_height_mm"])
    engage = float(engagement) if engagement else max(2.5 * d, 4.0)
    lf = plan["frame"]
    frame_ids = {id(p) for p in frame.points}
    frame_pts = [lf.local(p) for p in frame.points]
    # What must not be in a boss's way: the covered parts that are not the frame.
    other_pts = [lf.local(p) for p in cover.points if id(p) not in frame_ids]
    reach = max(boss_r, 1.2 * spacing) + 1.0
    buckets: dict = {}

    def near(w):
        if w not in buckets:
            buckets[w] = ([q for q in frame_pts if abs(q[2] - w) <= reach],
                          [q for q in other_pts if abs(q[2] - w) <= reach])
        return buckets[w]

    tests = {
        "frame": lambda q: frame.contains(lf.world(q)),
        "cover": lambda q: cover.contains(lf.world(q)),
    }
    positions = [row["position"] for row in plan["stations"]]
    taken: list = []
    for piece in plan["pieces"]:
        low, high = piece["station_range"]
        margin = boss_r + 1.5
        candidates_w = [w for w in positions if low + margin <= w <= high - margin]
        if not candidates_w and high - low >= 2 * margin:
            candidates_w = [(low + high) / 2.0]
        # Stations spread across the piece first: the ends of its range.
        middle = (low + high) / 2.0
        ordered_w = sorted(candidates_w, key=lambda w: -abs(w - middle))
        options = []
        for angle in _BOSS_ANGLES[piece["side"]]:
            for fraction in _BOSS_LATERALS:
                for w in ordered_w:
                    option = _boss_option(plan, w, angle, fraction, near(w), tests, boss_r,
                                          head_h, engage, spacing, piece, d)
                    if option is not None:
                        options.append(option)
        # A screw from another piece may already use this part of the frame:
        # a top and a bottom cover screwed into one deck from both faces on
        # the same line meet in the middle of it.
        options = [o for o in options
                   if all(_segment_gap(o["pilot"], t) > 2.0 * d for t in taken)]
        chosen = []
        while options and len(chosen) < wanted:
            if not chosen:
                pick = options[0]
            else:
                def spread(o):
                    return min(math.dist(o["seat_point"], c["seat_point"]) for c in chosen)

                # Spread out, square to the frame where it can be: a screw
                # aimed across a deck's edge rather than through a face is
                # the last resort.
                def score(o):
                    return spread(o) - (0.0 if o["angle"] % 90.0 == 0.0 else 40.0)
                pick = max(options, key=score)
                if spread(pick) < 2.5 * boss_r:
                    break
            chosen.append(pick)
            options.remove(pick)
            taken.append(pick["pilot"])
            options = [o for o in options if _segment_gap(o["pilot"], pick["pilot"]) > 2.0 * d]
        piece["bosses"] = chosen
        if len(chosen) < wanted:
            plan["notes"].append(
                f"panel piece {piece['name']}: {len(chosen)} of {wanted} screw bosses "
                "found a clear path to the frame")


#: Where across the ring a boss line may run, as fractions of the ring's
#: half-extent across the aim: on the centre line first, then out towards
#: the sides, where a cover stands over the frame beside what it covers.
_BOSS_LATERALS = (0.0, 0.3, -0.3, 0.55, -0.55, 0.75, -0.75)

#: The steepest skin a boss may come up through, from the boss's own axis.
_BOSS_MAX_SLOPE_DEGREES = 40.0


def _exit_radius(centre, a, b, exponent, origin, d):
    """How far along ``d`` from ``origin`` the line leaves the ring, or None."""

    def value(r):
        return _norm_value(origin[0] + d[0] * r - centre[0],
                           origin[1] + d[1] * r - centre[1], a, b, exponent)

    if value(0.0) >= 1.0:
        return None
    lo, hi = 0.0, 2.0 * (a + b) + 10.0
    for _ in range(48):
        mid = (lo + hi) / 2.0
        if value(mid) < 1.0:
            lo = mid
        else:
            hi = mid
    return lo


def _boss_option(plan, w, angle, fraction, nearby, tests, boss_r, head_h, engage, spacing,
                 piece, diameter=2.0):
    """One candidate boss at station ``w``, aimed ``angle``, offset sideways, or None.

    A boss is a line parallel to its aim (``angle`` degrees from the across
    direction towards up), ``fraction`` of the ring's half-extent to one
    side of the ring's centre. The frame's outermost material on that line
    is found from its sampled points, then refined on its membership test
    where the recipe can answer it; the boss is refused when anything else
    stands between the frame and the skin, when the skin is too steep there,
    when it would cross the parting plane, or when no stocked screw reaches.
    """

    frame_pts, other_pts = nearby
    centre, inner, outer = _ring_at(plan, w)
    exponent = plan["exponent"]
    t = math.radians(angle)
    du, dv = math.cos(t), math.sin(t)
    nu, nv = -dv, du
    if plan["split_at"] is not None:
        across = dv if plan["split"] == "top_bottom" else du
        if piece["sign"] * across <= 1.0e-6:
            return None
    # The ring's half-extent across the aim, and the line's foot.
    extent = ring_radius(inner[0], inner[1], exponent, angle + 90.0)
    e = fraction * extent
    origin = (centre[0] + nu * e, centre[1] + nv * e)
    r_in = _exit_radius(centre, inner[0], inner[1], exponent, origin, (du, dv))
    r_out = _exit_radius(centre, outer[0], outer[1], exponent, origin, (du, dv))
    if r_in is None or r_out is None:
        return None
    # The skin's slope where the boss comes up through it.
    eu, ev = origin[0] + du * r_out - centre[0], origin[1] + dv * r_out - centre[1]
    n = exponent
    gu = math.copysign(abs(eu) ** (n - 1.0) / outer[0] ** n, eu) if eu else 0.0
    gv = math.copysign(abs(ev) ** (n - 1.0) / outer[1] ** n, ev) if ev else 0.0
    glen = math.hypot(gu, gv)
    if glen <= 0.0 or (gu * du + gv * dv) / glen < math.cos(math.radians(_BOSS_MAX_SLOPE_DEGREES)):
        return None

    def axis_point(r, lateral=(0.0, 0.0)):
        # On the boss line at r, displaced (sideways, along w).
        return [origin[0] + du * r + nu * lateral[0], origin[1] + dv * r + nv * lateral[0],
                w + lateral[1]]

    def polar(q):
        rel = (q[0] - origin[0], q[1] - origin[1])
        return rel[0] * du + rel[1] * dv, rel[0] * nu + rel[1] * nv

    tube = max(boss_r, 1.2 * spacing)
    best = None
    for q in frame_pts:
        if abs(q[2] - w) > tube:
            continue
        along, sideways = polar(q)
        if abs(sideways) <= tube and along < r_in and (best is None or along > best):
            best = along
    if best is None:
        return None
    r_frame = best
    # Refine on the frame's membership test: the highest material on nine
    # lines across the boss's footprint, marched down from just above the
    # sampled estimate.
    frame_contains = tests["frame"]
    lines = [(0.0, 0.0)] + [(boss_r * 0.9 * math.cos(k * math.pi / 4),
                             boss_r * 0.9 * math.sin(k * math.pi / 4)) for k in range(8)]
    exact = frame_contains(axis_point(r_frame - 0.05)) is not None
    if exact:
        top = None
        start = min(r_in - 0.05, r_frame + 1.5 * spacing)
        for lateral in lines:
            r = start
            while r > r_frame - 3.0 * spacing:
                if frame_contains(axis_point(r, lateral)):
                    lo, hi = r, r + 0.5
                    for _ in range(16):
                        mid = (lo + hi) / 2.0
                        if frame_contains(axis_point(mid, lateral)):
                            lo = mid
                        else:
                            hi = mid
                    top = lo if top is None else max(top, lo)
                    break
                r -= 0.5
        if top is None or frame_contains(axis_point(top - 0.5)) is not True:
            return None
        r_frame = top
    gap = r_in - r_frame
    if gap < 0.0:
        return None
    if plan["split_at"] is not None:
        # The boss comes up through its own half's skin; where it reaches
        # past the parting plane to the frame, it must stay clear of the
        # other half's skin, inside the cavity.
        index = 1 if plan["split"] == "top_bottom" else 0
        side = plan["seam_gap"] / 2.0 + 0.8
        exit_point = [origin[0] + du * r_out, origin[1] + dv * r_out]
        if (exit_point[index] - plan["split_at"]) * piece["sign"] < side + boss_r * abs(
                nv if index == 1 else nu):
            return None
        margin = plan["seam_gap"] + 0.6
        for k in range(7):
            r = r_frame + (r_out - r_frame) * k / 6.0
            for j in range(8):
                rim = boss_r * math.cos(j * math.pi / 4)
                p = [origin[0] + du * r + nu * rim, origin[1] + dv * r + nv * rim]
                if (p[index] - plan["split_at"]) * piece["sign"] < side and _norm_value(
                        p[0] - centre[0], p[1] - centre[1], max(inner[0] - margin, 0.5),
                        max(inner[1] - margin, 0.5), exponent) >= 1.0:
                    return None
    # Nothing else may stand between the frame and the skin under the boss.
    clear = boss_r + plan["offset"]  # bosses clear the contents as the skin does
    for q in other_pts:
        if abs(q[2] - w) > clear:
            continue
        along, sideways = polar(q)
        if r_frame + 0.05 < along < r_out + 0.05 and math.hypot(sideways, q[2] - w) <= clear:
            return None
    cover_contains = tests["cover"]
    for k in range(7):
        r = r_frame + 0.2 + (r_out - r_frame - 0.2) * k / 6.0
        for lateral in lines:
            q = axis_point(r, lateral)
            if cover_contains(q) is True and frame_contains(q) is not True:
                return None
    seat = r_out - head_h - 0.3
    flush = seat - r_frame >= 1.5
    if not flush:
        seat = r_out
    # The thread may not run out of the far side of the frame: measure the
    # material under the boss where the recipe says, and stop 0.3 mm short.
    longest = None
    if exact:
        r = r_frame - 0.25
        while r > r_frame - 40.0 and frame_contains(axis_point(r)) is True:
            r -= 0.25
        lo, hi = r, r + 0.25  # lo outside the material, hi inside
        for _ in range(12):
            mid = (lo + hi) / 2.0
            if frame_contains(axis_point(mid)) is True:
                hi = mid
            else:
                lo = mid
        longest = (r_frame - hi) - 0.3
        if longest < 1.5 * diameter:
            return None
    clear = seat - r_frame
    length = _choose_length(clear + engage, None if longest is None else clear + longest)
    if length is None and longest is not None:
        fits = [L for L in STANDARD_SCREW_LENGTHS_MM
                if clear + 1.5 * diameter <= L <= clear + longest + 1e-6]
        length = fits[-1] if fits else None
    if length is None:
        return None
    return {"w": w, "angle": angle, "lateral": e, "origin": list(origin),
            "centre": list(centre), "r_frame": r_frame, "r_inner": r_in, "r_outer": r_out,
            "seat": seat, "flush": flush, "length": length,
            "engagement": length - (seat - r_frame), "boss_radius": boss_r, "exact": exact,
            "seat_point": [origin[0] + du * seat, origin[1] + dv * seat, w],
            # The screw's path from its seat to its tip, for spacing screws.
            "pilot": ([origin[0] + du * seat, origin[1] + dv * seat, w],
                      [origin[0] + du * (seat - length), origin[1] + dv * (seat - length), w])}


def _segment_gap(first, second, samples=12):
    """Least distance between two segments, sampled (good to a few percent)."""

    (a0, a1), (b0, b1) = first, second
    best = float("inf")
    for i in range(samples + 1):
        p = [a0[k] + (a1[k] - a0[k]) * i / samples for k in range(3)]
        for j in range(samples + 1):
            q = [b0[k] + (b1[k] - b0[k]) * j / samples for k in range(3)]
            best = min(best, math.dist(p, q))
    return best


# ---------------------------------------------------------------------------
# building a panel (part recipes)


class PanelSet:
    """What ``lib.panel`` returns: the panels, their screws and the frame's holes.

    ``parts`` -- one solid per panel piece, split at the seams; ``names`` the
    matching suffixes (``"0_top"``, ``"1"``...). ``screws`` -- every
    ``lib.bolt`` part, one component each; ``screws_by_part`` the same, per
    piece. ``holes`` -- the tap-drill pilots to cut from the frame:
    ``frame = part.cut(frame, panel.holes)``. ``rings`` -- the stations as
    fitted (``position`` along the axis, ``centre``, ``inner`` and ``outer``
    half-axes), so the numbers a skin was drawn from can be read back.
    ``unmounted`` names any piece no boss could reach the frame from, and
    ``notes`` says why.
    """

    __slots__ = ("parts", "names", "screws", "screws_by_part", "holes", "rings",
                 "unmounted", "notes", "spec")

    def __init__(self, **values):
        for key in self.__slots__:
            object.__setattr__(self, key, values.get(key))

    def __setattr__(self, _name, _value):
        raise TypeError("A panel set is immutable; build another instead.")

    def __repr__(self):  # pragma: no cover - debugging convenience
        return f"PanelSet({len(self.parts)} panels, {len(self.screws)} screws)"


def _number(name, value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise PanelError(f"{name} must be a finite number; received {value!r}")
    value = float(value)
    if not low <= value <= high:
        raise PanelError(f"{name} must be between {low:g} and {high:g}; received {value:g}")
    return value


def build_panel(lib, over, *, axis=(1.0, 0.0, 0.0), up=None, span=None, offset=1.5,
                thickness=2.0, exponent=None, step=12.0, seams=(), split=None,
                split_at=None, seam_gap=0.4, mount_to=None, screw="m2", screws_per_panel=2,
                spacing=3.0, label=""):
    part = lib._part
    offset = _number("lib.panel offset", offset, 0.3, 20.0)
    thickness = _number("lib.panel thickness", thickness, 0.8, 6.0)
    if exponent is not None:
        exponent = _number("lib.panel exponent", exponent, 2.0, 12.0)
    step = _number("lib.panel step", step, 3.0, 200.0)
    seam_gap = _number("lib.panel seam_gap", seam_gap, 0.1, 5.0)
    spacing = _number("lib.panel spacing", spacing, 0.5, 20.0)
    items = list(over) if isinstance(over, (list, tuple)) else [over]
    if not items:
        raise PanelError("lib.panel over= must name at least one part")
    cache: dict = {}
    bodies = [getattr(item, "body", item) for item in items]
    covered = [sample(body, spacing, cache) for body in bodies]
    frame_sample = frame_body = None
    if mount_to is not None:
        frame_body = getattr(mount_to, "body", mount_to)
        frame_sample = sample(frame_body, spacing, cache)
        # The frame is covered too, whether or not over= names it.
        if not any(body is frame_body for body in bodies):
            covered.append(frame_sample)
    tests = [c.contains for c in covered]
    cover = Sample([p for c in covered for p in c.points],
                   lambda p: _any(test(p) for test in tests))
    plan = plan_panel(cover, frame_sample, axis=axis, up=up, span=span, offset=offset,
                      thickness=thickness, exponent=exponent, step=step, seams=seams,
                      split=split, split_at=split_at, seam_gap=seam_gap,
                      screw=screw if mount_to is not None
                      else None, screws_per_panel=screws_per_panel, spacing=spacing)
    lf = plan["frame"]
    stations = plan["stations"]
    exponent = plan["exponent"]

    def loft(rows, key):
        wires = []
        for row in rows:
            a, b = row[key]
            pts = [[u, v, row["position"]] for u, v in
                   ring_points_2d(row["centre"][0], row["centre"][1], a, b, exponent)]
            wires.append(part.wire([part.bspline(pts, periodic=True)]))
        return part.loft(wires, solid=True, on_bulge="allow")

    # Outer and inner through the same stations, so their two skins are
    # parametrised alike and never cross; the end faces are coplanar, which
    # OCCT cuts cleanly, leaving the sleeve open at both ends.
    outer = loft(stations, "outer")
    inner = loft(stations, "inner")
    sleeve = part.cut(outer, [inner], refine=False)
    reach = max(max(row["outer"]) for row in stations) + max(
        max(abs(row["centre"][0]), abs(row["centre"][1])) for row in stations) + 20.0
    import CadexCatalog as catalog

    rotation_axis, rotation_degrees = axis_angle(lf.matrix)
    # The pieces are built in the panel's own frame; the frame they are cut
    # against has to be carried into it.
    frame_local = frame_body
    if frame_body is not None and abs(rotation_degrees) > 1.0e-9:
        frame_local = part.transform(frame_body, rotation_axis=rotation_axis,
                                     rotation_degrees=-rotation_degrees)
    parts, names, screws, screws_by_part, holes, unmounted = [], [], [], [], [], []
    for piece in plan["pieces"]:
        low, high = piece["station_range"]
        # Past the skin's open ends, so no slab face lies on an end face.
        span_low, span_high = plan["span"]
        box_low = [-reach, -reach, low - 5.0 if low <= span_low + 1e-9 else low]
        box_high = [reach, reach, high + 5.0 if high >= span_high - 1e-9 else high]
        if piece["sign"] is not None:
            index = 1 if plan["split"] == "top_bottom" else 0
            cut_at = plan["split_at"] + piece["sign"] * seam_gap / 2.0
            if piece["sign"] > 0:
                box_low[index] = cut_at
            else:
                box_high[index] = cut_at
        slab = part.box(*(hi - lo for lo, hi in zip(box_low, box_high)), origin=box_low)
        bosses, tools, own_screws = [], [], []
        for boss in piece["bosses"]:
            t = math.radians(boss["angle"])
            d = [math.cos(t), math.sin(t), 0.0]
            c = [boss["origin"][0], boss["origin"][1], boss["w"]]

            def at(r):
                return [c[0] + d[0] * r, c[1] + d[1] * r, c[2]]

            # From just inside the frame: the frame is cut from the piece
            # below, so the boss's foot takes the frame's own surface.
            bosses.append(part.cylinder(boss["boss_radius"],
                                        boss["r_outer"] + 6.0 - boss["r_frame"] + 0.5,
                                        origin=at(boss["r_frame"] - 0.5), direction=d))
            thread = catalog.thread_spec(screw)
            head = catalog.socket_head_spec(screw)
            tools.append(part.cylinder(thread["clearance_normal_mm"] / 2.0,
                                       boss["seat"] - boss["r_frame"] + 1.1,
                                       origin=at(boss["r_frame"] - 1.0), direction=d))
            if boss["flush"]:
                tools.append(part.cylinder(head["head_dia_mm"] / 2.0 + 0.4,
                                           boss["r_outer"] + 6.0 - boss["seat"],
                                           origin=at(boss["seat"]), direction=d))
            world_seat = lf.world(at(boss["seat"]))
            world_d = lf.world_dir(d)
            bolt = lib.bolt(screw, boss["length"], origin=world_seat, direction=world_d)
            own_screws.append(bolt)
            depth = boss["engagement"] + 1.5
            holes.append(part.cylinder(thread["tap_drill_mm"] / 2.0, depth + 0.5,
                                       origin=lf.world(at(boss["r_frame"] - depth)),
                                       direction=world_d))
        # The skin is split at the seam; a boss is this piece's whatever side
        # of the parting plane it stands on, trimmed to the outer skin.
        body = part.common([sleeve, slab], refine=False)
        if bosses:
            # Holes first, then the trim to the outer skin: a cut through a
            # trimmed boss top (a patch of the B-spline skin) can lose the
            # whole solid in OCCT, and the same cut before the trim cannot.
            body = part.common([part.cut(part.fuse([body] + bosses, refine=False),
                                         tools + [frame_local], refine=False), outer],
                               refine=False)
        if abs(rotation_degrees) > 1.0e-9:
            body = part.transform(body, rotation_axis=rotation_axis,
                                  rotation_degrees=rotation_degrees,
                                  label=f"{label}_{piece['name']}" if label else "")
        parts.append(body)
        names.append(piece["name"])
        screws.extend(own_screws)
        screws_by_part.append(own_screws)
        if not own_screws:
            unmounted.append(piece["name"])
    rings = [{"position": row["position"], "centre": list(row["centre"]),
              "inner": list(row["inner"]), "outer": list(row["outer"])} for row in stations]
    notes = list(plan["notes"])
    if mount_to is None:
        notes.append("no mount_to= frame: the panels carry no screws; screw or weld "
                     "them to the structure that carries them")
    return PanelSet(
        parts=parts, names=names, screws=screws, screws_by_part=screws_by_part,
        holes=holes, rings=rings, unmounted=unmounted, notes=notes,
        spec={"axis": list(lf.w), "up": list(lf.v), "across": list(lf.u),
              "span_mm": list(plan["span"]), "offset_mm": offset, "thickness_mm": thickness,
              "exponent": exponent, "seams_mm": sorted(float(c) for c in (seams or ())),
              "split": split, "split_at_mm": plan["split_at"], "screw": screw if mount_to
              is not None else None,
              "bosses": [{"piece": piece["name"], "position_mm": b["w"],
                          "angle_degrees": b["angle"], "screw_length_mm": b["length"],
                          "engagement_mm": round(b["engagement"], 3),
                          "standoff_mm": round(b["r_inner"] - b["r_frame"], 3),
                          "flush_head": b["flush"], "exact_frame": b["exact"]}
                         for piece in plan["pieces"] for b in piece["bosses"]]})


# ---------------------------------------------------------------------------
# housings grown around a drive


class Housing:
    """What ``lib.housing`` returns: a printed part grown around one drive.

    ``body`` -- the housing solid (give it ``appearance="shell"`` or
    ``"mechanism"``, and weld the drive to it with a fixed joint). ``screws``
    -- the ``lib.bolt`` parts through its seat into the drive's own holes,
    one component each. ``cavity`` and ``holes`` -- what was cut, so a link
    fused on later can be cut again: ``housing.fuse(link)`` does exactly
    that. ``spec`` -- the numbers it was grown with (``wall_mm``,
    ``clearance_mm``, ``outer_dia_mm`` or ``outer_size_mm``, ``seat``,
    ``screw``, ``screw_length_mm``, ``engagement_mm``).
    """

    __slots__ = ("body", "screws", "cavity", "holes", "drive", "spec", "_lib")

    def __init__(self, lib, **values):
        object.__setattr__(self, "_lib", lib)
        for key in self.__slots__[:-1]:
            object.__setattr__(self, key, values.get(key))

    def __setattr__(self, _name, _value):
        raise TypeError("A housing is immutable; build another instead.")

    def fuse(self, *links, label=""):
        """The housing with ``links`` grown on, cavity and screw holes cut again.

        A link fused onto a housing usually reaches into the drive's
        envelope; cutting the cavity and holes after the fuse keeps the
        drive's seat and its screws' paths clear.
        """

        part = self._lib._part
        shapes = [self.body] + [getattr(link, "body", link) for link in links]
        if len(shapes) < 2:
            return self.body
        return part.cut(part.fuse(shapes), [self.cavity] + list(self.holes), label=label)

    def __repr__(self):  # pragma: no cover - debugging convenience
        return f"Housing({self.spec.get('drive')})"


def _place_local(lib, body, frame):
    return lib._place_frame("housing", body, frame)


def _world_point(frame, local):
    from cadex_library_api import _rotate

    origin, _unit_dir, rotation = frame
    return [o + v for o, v in zip(origin, _rotate(rotation, local))]


def _world_vector(frame, local):
    from cadex_library_api import _rotate

    return list(_rotate(frame[2], local))


def _bolt_for_hole(hole_dia):
    """The largest catalogued metric bolt a clearance hole of this size takes."""

    import CadexCatalog as catalog

    best = None
    for key, row in catalog.METRIC_THREADS.items():
        if row["nominal_dia_mm"] <= hole_dia + 1e-6 and key in catalog.SOCKET_HEAD_SCREWS:
            if best is None or row["nominal_dia_mm"] > best[1]:
                best = (key, row["nominal_dia_mm"])
    if best is None:
        raise PanelError(f"no catalogued screw fits a {hole_dia:g} mm hole")
    return best[0]


def build_housing(lib, drive, *, wall=2.0, clearance=0.5, seat=None, plate=None,
                  lead_room=None, label=""):
    family = getattr(drive, "family", None)
    wall = _number("lib.housing wall", wall, 0.8, 10.0)
    clearance = _number("lib.housing clearance", clearance, 0.0, 5.0)
    if family == "qdd":
        return _qdd_housing(lib, drive, wall, clearance, seat or "rear", plate, label)
    if family == "servo":
        return _servo_housing(lib, drive, wall, clearance, lead_room, label)
    raise PanelError(
        "lib.housing grows around a lib.qdd(...) or lib.servo(...) part; received "
        f"{drive!r}")


def _qdd_housing(lib, qdd, wall, c, seat, plate, label):
    import CadexCatalog as catalog

    part = lib._part
    spec = qdd.spec
    frame = qdd._frame_placement
    if seat not in ("rear", "front"):
        raise PanelError(f"lib.housing seat must be 'rear' or 'front'; received {seat!r}")
    plate = _number("lib.housing plate", plate if plate is not None else max(3.0, 1.5 * wall),
                    1.0, 20.0)
    segments = [tuple(float(v) for v in row) for row in spec["segments"]]
    case_dia = float(spec["case_dia_mm"])
    stator = [row for row in segments if abs(row[0] - case_dia) <= 1e-6]
    body_low = min(row[1] for row in stator)
    body_high = max(row[2] for row in stator)
    r_in = case_dia / 2.0 + c
    r_out = r_in + wall
    thread = spec["mount_thread"].lower()
    screw = catalog.normalise_thread_size(thread)
    thread_row = catalog.thread_spec(screw)
    clear_r = thread_row["clearance_normal_mm"] / 2.0
    pcd_r = float(spec["mount_pcd_mm"]) / 2.0
    hole_edge = pcd_r - clear_r
    if seat == "rear":
        seat_z = float(spec["rear_mount_z_mm"])
        depth = float(spec["rear_mount_depth_mm"])
        behind = [row for row in segments if row[1] < seat_z - 1e-6]
        opening = max([row[0] / 2.0 + c for row in behind] + [0.0])
        if opening <= 0.0:
            opening = hole_edge - 2.0
        z0, z1 = seat_z - plate, body_high
        plate_low, plate_high = seat_z - plate, seat_z
        head_z, screw_dir = seat_z - plate, (0.0, 0.0, -1.0)
    else:
        seat_z = float(spec["front_mount_z_mm"])
        depth = float(spec["front_mount_depth_mm"])
        ahead = [row for row in segments if row[2] > seat_z + 1e-6]
        opening = max([row[0] / 2.0 + c for row in ahead] + [0.0])
        if opening <= 0.0:
            opening = hole_edge - 2.0
        z0, z1 = body_low, seat_z + plate
        plate_low, plate_high = seat_z, seat_z + plate
        head_z, screw_dir = seat_z + plate, (0.0, 0.0, 1.0)
    if opening > hole_edge - 0.6:
        raise PanelError(
            f"lib.housing: a {seat} seat on {qdd.part_number} leaves "
            f"{hole_edge - opening:.2f} mm between the {opening * 2:.1f} mm opening and "
            f"the {screw.upper()} holes; seat it on the other face")
    longest = plate + depth - 0.3
    length = None
    for candidate in reversed(STANDARD_SCREW_LENGTHS_MM):
        if plate + 1.5 <= candidate <= longest + 1e-6:
            length = candidate
            break
    if length is None:
        raise PanelError(
            f"lib.housing: no stocked {screw.upper()} length fits a {plate:g} mm plate "
            f"into {qdd.part_number}'s {depth:g} mm {seat} holes; thin the plate")
    drum = part.cylinder(r_out, z1 - z0, origin=(0.0, 0.0, z0))
    cavity_pieces = []
    for dia, low, high in segments:
        lo, hi = low - c, high + c
        if seat == "rear":
            lo = max(lo, seat_z)
            if hi <= seat_z:
                continue
            if abs(high - max(r[2] for r in segments)) <= 1e-6 or high >= body_high - 1e-6:
                hi = max(hi, z1 + 1.0)
        else:
            hi = min(hi, seat_z)
            if lo >= seat_z:
                continue
            if low <= body_low + 1e-6:
                lo = min(lo, z0 - 1.0)
        cavity_pieces.append(part.cylinder(dia / 2.0 + c, hi - lo, origin=(0.0, 0.0, lo)))
    # The opening the output (front seat) or the rear cover and leads
    # (rear seat) pass through.
    cavity_pieces.append(part.cylinder(opening, plate + 2.0, origin=(0.0, 0.0, plate_low - 1.0)))
    cavity_local = part.fuse(cavity_pieces) if len(cavity_pieces) > 1 else cavity_pieces[0]
    holes_local = [part.cylinder(clear_r, plate + 2.0, origin=(x, y, plate_low - 1.0))
                   for x, y in spec["mount_holes"]]
    cavity = _place_local(lib, cavity_local, frame)
    holes = [_place_local(lib, hole, frame) for hole in holes_local]
    body = part.cut(_place_local(lib, drum, frame), [cavity] + holes, label=label)
    screws = [lib.bolt(screw, length, origin=_world_point(frame, (x, y, head_z)),
                       direction=_world_vector(frame, screw_dir))
              for x, y in spec["mount_holes"]]
    return Housing(lib, body=body, screws=screws, cavity=cavity, holes=holes, drive=qdd,
                   spec={"drive": f"qdd/{qdd.part_number}", "seat": seat, "wall_mm": wall,
                         "clearance_mm": c, "plate_mm": plate, "outer_dia_mm": 2 * r_out,
                         "span_z_mm": [z0, z1], "opening_dia_mm": 2 * opening,
                         "screw": screw, "screw_count": len(screws),
                         "screw_length_mm": length, "engagement_mm": length - plate})


def _servo_housing(lib, servo, wall, c, lead_room, label):
    import CadexCatalog as catalog

    part = lib._part
    spec = servo.spec
    frame = servo._frame_placement
    front = float(spec["shaft_offset_from_front_mm"])
    length = float(spec["body_length_mm"])
    back = front - length
    half = float(spec["body_width_mm"]) / 2.0
    height = float(spec["case_height_mm"])

    def box(low, high):
        return part.box(*(b - a for a, b in zip(low, high)), origin=tuple(low))

    if spec.get("mount_style") == "case_holes":
        room = 15.0 if lead_room is None else float(lead_room)
        floor_low = -height - c - wall
        outer = box((back - c - wall, -half - c - wall, floor_low),
                    (front + c + wall, half + c + wall, 0.0))
        bay = servo.bay(clearance=c, lead_room=room)
        # The floor the rear face is screwed down onto: the bay leaves `c`
        # under the case, and a screwed face wants its seat.
        pad = box((back, -half, -height - c - 0.5), (front, half, -height))
        rear = [p for p in spec["mount_points"] if p["face"] == "rear"]
        screw = catalog.normalise_thread_size("m2")
        thread_row = catalog.thread_spec(screw)
        boss_hole = part.cylinder(spec["rear_boss_dia_mm"] / 2.0 + c, wall + c + 2.0,
                                  origin=(0.0, 0.0, floor_low - 1.0))
        holes_local = [part.cylinder(thread_row["clearance_normal_mm"] / 2.0, wall + c + 2.0,
                                     origin=(p["origin"][0], p["origin"][1], floor_low - 1.0))
                       for p in rear]
        floor = c + wall  # under the case, the pad included
        longest = floor + float(spec["hole_depth_mm"]) - 0.3
        screw_length = None
        for candidate in reversed(STANDARD_SCREW_LENGTHS_MM):
            if floor + 1.5 <= candidate <= longest + 1e-6:
                screw_length = candidate
                break
        if screw_length is None:
            raise PanelError("lib.housing: no stocked M2 length fits this floor; thin the wall")
        placed_holes = [_place_local(lib, hole, frame) for hole in holes_local + [boss_hole]]
        body = part.cut(
            part.fuse([part.cut(_place_local(lib, outer, frame), [bay]),
                       _place_local(lib, pad, frame)]),
            placed_holes, label=label)
        screws = [lib.bolt(screw, screw_length,
                           origin=_world_point(frame, (p["origin"][0], p["origin"][1], floor_low)),
                           direction=_world_vector(frame, (0.0, 0.0, -1.0)))
                  for p in rear]
        return Housing(lib, body=body, screws=screws, cavity=bay, holes=placed_holes,
                       drive=servo, spec={
                           "drive": f"servo/{servo.part_number}", "seat": "rear face",
                           "wall_mm": wall, "clearance_mm": c, "lead_room_mm": room,
                           "outer_size_mm": [length + 2 * (c + wall), 2 * (half + c + wall),
                                             height + c + wall],
                           "screw": screw, "screw_count": len(screws),
                           "screw_length_mm": screw_length,
                           "engagement_mm": screw_length - floor})

    room = 6.0 if lead_room is None else float(lead_room)
    plate_z = float(spec["mount_hole_z_mm"])
    tab_t = float(spec["tab_thickness_mm"])
    centre = front - length / 2.0
    tab_half = float(spec["overall_tab_length_mm"]) / 2.0
    x_low = min(back - c - wall, centre - tab_half)
    x_high = max(front + c + wall, centre + tab_half)
    bottom = -height - c - wall
    outer = box((x_low, -half - c - wall, bottom), (x_high, half + c + wall, plate_z))
    bay = servo.bay(clearance=c, lead_room=room, ledge=4.0)
    # Seats under the tabs: the bay grows the tab plate by `c` below, and a
    # screwed tab wants to land on the rim, not across a gap.
    pads = [box((front + c, -half, plate_z - c - 1.0), (centre + tab_half, half, plate_z)),
            box((centre - tab_half, -half, plate_z - c - 1.0), (back - c, half, plate_z))]
    screw = _bolt_for_hole(float(spec["hole_dia_mm"]))
    thread_row = catalog.thread_spec(screw)
    d = float(thread_row["nominal_dia_mm"])
    screw_length = _choose_length(tab_t + max(2.5 * d, 4.0))
    rim = plate_z - bottom
    engage = screw_length - tab_t
    if engage + 1.0 > rim:
        raise PanelError("lib.housing: the servo's housing is too shallow for its screws")
    pilots = [part.cylinder(thread_row["tap_drill_mm"] / 2.0, engage + 1.5,
                            origin=(x, y, plate_z - engage - 1.0))
              for x, y in spec["mount_holes"]]
    placed_pilots = [_place_local(lib, pilot, frame) for pilot in pilots]
    body = part.cut(
        part.fuse([part.cut(_place_local(lib, outer, frame), [bay])]
                  + [_place_local(lib, p, frame) for p in pads]),
        placed_pilots, label=label)
    screws = [lib.bolt(screw, screw_length,
                       origin=_world_point(frame, (x, y, plate_z + tab_t)),
                       direction=_world_vector(frame, (0.0, 0.0, 1.0)))
              for x, y in spec["mount_holes"]]
    return Housing(lib, body=body, screws=screws, cavity=bay, holes=placed_pilots,
                   drive=servo, spec={
                       "drive": f"servo/{servo.part_number}", "seat": "tabs",
                       "wall_mm": wall, "clearance_mm": c, "lead_room_mm": room,
                       "outer_size_mm": [x_high - x_low, 2 * (half + c + wall), plate_z - bottom],
                       "screw": screw, "screw_count": len(screws),
                       "screw_length_mm": screw_length, "engagement_mm": engage})


# ---------------------------------------------------------------------------
# the shell check's measuring half (run in the assembly worker)


def gap_statistics(samples, normals, triangles, *, reach=60.0):
    """How far a shell's inner face stands off what it covers.

    ``samples`` and ``normals`` are points on the shell and the shell's
    outward normals there; ``triangles`` the contents' surface, an
    ``(n, 3, 3)`` array-like. For every sample the nearest content point is
    found exactly (point-to-triangle). A sample faces the contents when its
    normal points towards that nearest point: on a hollow shell that is the
    inner face, whose distance is the gap a designer means. Returns the
    inner-face count and the gap's quartiles, or ``None`` when no sample
    faces any content within ``reach`` mm.
    """

    import numpy as np

    P = np.asarray(samples, dtype=float).reshape(-1, 3)
    N = np.asarray(normals, dtype=float).reshape(-1, 3)
    T = np.asarray(triangles, dtype=float).reshape(-1, 3, 3)
    if not len(P) or not len(T):
        return None
    best_d = np.full(len(P), np.inf)
    best_q = np.zeros_like(P)
    for start in range(0, len(T), 512):
        chunk = T[start:start + 512]
        q = _closest_on_triangles(P, chunk)  # (S, C, 3)
        d = np.linalg.norm(q - P[:, None, :], axis=2)
        index = np.argmin(d, axis=1)
        dmin = d[np.arange(len(P)), index]
        better = dmin < best_d
        best_d[better] = dmin[better]
        best_q[better] = q[np.arange(len(P)), index][better]
    toward = np.einsum("ij,ij->i", N, best_q - P)
    facing = (toward > 0.0) & (best_d <= reach)
    gaps = np.sort(best_d[facing])
    if not len(gaps):
        return None
    return {
        "samples": int(len(P)),
        "inner_samples": int(len(gaps)),
        "gap_p25_mm": round(float(np.percentile(gaps, 25)), 3),
        "gap_median_mm": round(float(np.percentile(gaps, 50)), 3),
        "gap_p90_mm": round(float(np.percentile(gaps, 90)), 3),
        "gap_max_mm": round(float(gaps[-1]), 3),
        "hug_fraction": round(float(np.mean(gaps <= HUG_GAP_MM)), 3),
    }


#: A sample of a shell's inner face within this of what it covers "hugs" it.
HUG_GAP_MM = 4.0


def _closest_on_triangles(P, T):
    """Closest points on each triangle to each point: (S, C, 3). Ericson 5.1.5."""

    import numpy as np

    a, b, c = T[:, 0][None], T[:, 1][None], T[:, 2][None]
    p = P[:, None, :]
    ab, ac, ap = b - a, c - a, p - a
    d1 = np.einsum("ijk,ijk->ij", ab, ap)
    d2 = np.einsum("ijk,ijk->ij", ac, ap)
    bp = p - b
    d3 = np.einsum("ijk,ijk->ij", ab, bp)
    d4 = np.einsum("ijk,ijk->ij", ac, bp)
    cp = p - c
    d5 = np.einsum("ijk,ijk->ij", ab, cp)
    d6 = np.einsum("ijk,ijk->ij", ac, cp)
    va = d3 * d6 - d5 * d4
    vb = d5 * d2 - d1 * d6
    vc = d1 * d4 - d3 * d2
    with np.errstate(divide="ignore", invalid="ignore"):
        denom = va + vb + vc
        v = np.where(np.abs(denom) > 1e-30, vb / denom, 0.0)
        w = np.where(np.abs(denom) > 1e-30, vc / denom, 0.0)
        result = a + ab * v[..., None] + ac * w[..., None]
        # Edge regions.
        t_ab = np.clip(np.where(np.abs(d1 - d3) > 1e-30, d1 / (d1 - d3), 0.0), 0, 1)
        t_ac = np.clip(np.where(np.abs(d2 - d6) > 1e-30, d2 / (d2 - d6), 0.0), 0, 1)
        t_bc = np.clip(np.where(np.abs((d4 - d3) + (d5 - d6)) > 1e-30,
                                (d4 - d3) / ((d4 - d3) + (d5 - d6)), 0.0), 0, 1)
    on_ab = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
    on_ac = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
    on_bc = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
    result = np.where(on_bc[..., None], b + (c - b) * t_bc[..., None], result)
    result = np.where(on_ac[..., None], a + ac * t_ac[..., None], result)
    result = np.where(on_ab[..., None], a + ab * t_ab[..., None], result)
    at_a = (d1 <= 0) & (d2 <= 0)
    at_b = (d3 >= 0) & (d4 <= d3)
    at_c = (d6 >= 0) & (d5 <= d6)
    result = np.where(at_c[..., None], np.broadcast_to(c, result.shape), result)
    result = np.where(at_b[..., None], np.broadcast_to(b, result.shape), result)
    result = np.where(at_a[..., None], np.broadcast_to(a, result.shape), result)
    return result
