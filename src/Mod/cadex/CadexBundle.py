# SPDX-License-Identifier: LGPL-2.1-or-later

"""Multi-conductor lay geometry for procedural wire bundles (ADR-057).

The geometry behind ``part.bundle``.  Like :mod:`CadexRouting` — and for the
same reason — this module imports nothing from FreeCAD and knows nothing
about topology: it takes a sampled centreline and returns one polyline per
conductor, so the whole lay is unit-testable headless without a kernel.

``part.cable`` routes one wire.  A bundle routes *once* and then places N
conductors around that shared centreline: twisted helically about it, or laid
flat side by side.  The search, the corridor and the sweep are unchanged and
shared; what lives here is the frame along the centreline and the offsets
from it, which is pure arithmetic.

Three properties are load-bearing, in this order.

**Determinism.**  ``open_project`` re-runs the accepted script and asserts
digest equality, so a lay that varies run to run breaks the project.  Every
loop here runs over an explicit range in a fixed order, every sum accumulates
left to right, no step iterates a set or a dict, and the one numerical solve
runs a *fixed* iteration count rather than to a tolerance.  Nothing reads the
clock, the address space or the hash seed.

**A rotation-minimising frame, not Frenet.**  Frenet's normal is defined by
the curvature vector, so it is undefined where the path is straight and flips
through a half-turn at an inflection point.  A routed centreline is made of
near-straight runs with S-bends around obstacles — inflections are the normal
case, not the exception, and each one would snap the whole bundle 180° mid-run.
The frame is carried instead by the double-reflection method of Wang et al.,
which is O(1) per sample, needs no trigonometry, and reproduces exactly in
floating point given the same inputs.

**Conductors that do not interpenetrate.**  The obvious lay radius — put N
circles of diameter ``d`` touching on a circle, ``R = (d/2)/sin(pi/N)`` — is
*wrong for every finite pitch* when ``N >= 3``.  That formula is the condition
for two neighbours to touch within one shared cross-section, but neighbouring
helices do not reach their closest approach in a shared cross-section: for
phase offset ``dphi`` and axial offset ``u`` the squared centre distance is

    f(u) = 2R^2 (1 - cos(2*pi*u/P - dphi)) + u^2

and ``f'(0) = -2 R^2 (2*pi/P) sin(dphi) < 0``, so ``u = 0`` is never the
minimum.  Six 1.2 mm conductors laid at a 15 mm pitch on the chord radius
overlap by 0.104 mm — 8.7% of the gauge — which is exactly the kind of error
that still passes ``isValid()`` and still renders.  ``N = 2`` is the one case
where the chord formula is exact, because antipodal helices *do* achieve their
minimum at ``u = 0``.

So the lay radius is **solved**, not asserted: the smallest radius at or above
the chord radius at which no two conductors come closer than the gauge.  As
``R`` grows the minimum migrates to ``u = P/N``, so a non-interfering lay
exists if and only if ``pitch > N * gauge``; below that the solve runs away
and the operation refuses with that floor named.
"""

from __future__ import annotations

import math
from typing import Sequence

__all__ = [
    "BundleError",
    "STYLES",
    "bundle_radius",
    "conductor_paths",
    "default_twist_pitch",
    "min_conductor_separation",
    "outer_diameter",
    "sample_count",
]

#: The lay styles ``part.bundle`` understands.
STYLES = frozenset({"twisted", "flat"})

#: Below this, two points are the same point — a spline interpolator rejects
#: coincident interpolation points, so samples are deduped against it.  Same
#: value as ``CadexRouting._COINCIDENT_MM``, for the same reason.
_COINCIDENT_MM = 1.0e-6

#: Below this a cross product has no direction left to normalise.
_DEGENERATE = 1.0e-9

#: How much clearance the solved lay radius leaves between conductors, as a
#: multiple of the gauge.  Not zero: the conductors follow the *centreline's*
#: curvature as well as the helix, which perturbs the separation by O(u^2 k)
#: in either direction, and exact tangency is a line contact that OCC handles
#: poorly downstream.  2% of a 1 mm wire is 20 um — invisible, and enough.
_LAY_MARGIN = 1.02

#: Scan resolution and refinement for the helix separation minimum.  Both
#: fixed rather than tolerance-driven, so the verdict is identical every run.
_SEPARATION_SCAN = 256
_SEPARATION_REFINE = 48

#: Bracket growth and bisection count for the lay radius solve.  1.02^400 is
#: a factor of ~2900 on the chord radius, far past any usable bundle.
_RADIUS_GROWTH = 1.02
_RADIUS_GROWTH_STEPS = 400
_RADIUS_BISECTIONS = 60

#: Samples per turn of the lay, and the range the sample count is clamped to.
#: 24 per turn holds the discrete bend-radius check within ~0.6% of the true
#: helix curvature, which the lay margin above already absorbs.
_SAMPLES_PER_TURN = 24
_MIN_SAMPLES = 33
_MAX_TWISTED_SAMPLES = 1200
_MAX_FLAT_SAMPLES = 400

#: The world axes, in the fixed order the frame seed falls back through.
_WORLD_AXES = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


class BundleError(ValueError):
    """A lay that could not be produced, with the reason named.

    ``reason`` is one of ``"count"``, ``"pitch"``, ``"radius"`` or
    ``"path"``; the host maps it to a model-facing correction that says what
    to change, the same contract :class:`CadexRouting.RoutingError` has.
    """

    def __init__(self, message: str, *, reason: str, observed: dict | None = None) -> None:
        self.reason = str(reason)
        self.observed = dict(observed or {})
        super().__init__(str(message))


def _dot(first: Sequence[float], second: Sequence[float]) -> float:
    return first[0] * second[0] + first[1] * second[1] + first[2] * second[2]


def _cross(first: Sequence[float], second: Sequence[float]) -> tuple[float, float, float]:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def _norm(vector: Sequence[float]) -> float:
    return math.sqrt(_dot(vector, vector))


def _scaled(vector: Sequence[float], factor: float) -> tuple[float, float, float]:
    return (vector[0] * factor, vector[1] * factor, vector[2] * factor)


def _difference(
    first: Sequence[float], second: Sequence[float]
) -> tuple[float, float, float]:
    return (first[0] - second[0], first[1] - second[1], first[2] - second[2])


def _normalized(vector: Sequence[float]) -> tuple[float, float, float] | None:
    length = _norm(vector)
    if not math.isfinite(length) or length <= _DEGENERATE:
        return None
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def _perpendicular_to(tangent: Sequence[float]) -> tuple[float, float, float]:
    """A unit vector perpendicular to ``tangent``, chosen by a fixed rule.

    The world axis least parallel to the tangent, taken in x, y, z order with
    ties going to the earlier axis.  Deterministic, and never degenerate: the
    least-parallel axis of a unit vector makes an angle of at least 45 degrees
    with it.
    """

    index, smallest = 0, abs(_dot(tangent, _WORLD_AXES[0]))
    for candidate in (1, 2):
        magnitude = abs(_dot(tangent, _WORLD_AXES[candidate]))
        if magnitude < smallest:
            index, smallest = candidate, magnitude
    result = _normalized(_cross(tangent, _WORLD_AXES[index]))
    if result is None:  # unreachable for a unit tangent; not worth trusting
        return _WORLD_AXES[(index + 1) % 3]
    return result


def _deduped(points: Sequence[Sequence[float]]) -> list[tuple[float, float, float]]:
    result: list[tuple[float, float, float]] = []
    for value in points:
        candidate = (float(value[0]), float(value[1]), float(value[2]))
        if result:
            gap = _norm(_difference(candidate, result[-1]))
            if gap <= _COINCIDENT_MM:
                continue
        result.append(candidate)
    return result


def _tangents(points: Sequence[Sequence[float]]) -> list[tuple[float, float, float]]:
    """Unit tangents by central differences, one-sided at the two ends.

    A previous tangent is reused where a difference degenerates, so a doubled
    sample cannot put a zero vector into the frame.
    """

    count = len(points)
    result: list[tuple[float, float, float]] = []
    for index in range(count):
        if index == 0:
            raw = _difference(points[1], points[0])
        elif index == count - 1:
            raw = _difference(points[count - 1], points[count - 2])
        else:
            raw = _difference(points[index + 1], points[index - 1])
        unit = _normalized(raw)
        if unit is None:
            unit = result[-1] if result else _WORLD_AXES[0]
        result.append(unit)
    return result


def _frame(
    points: Sequence[Sequence[float]],
    tangents: Sequence[Sequence[float]],
    seed: Sequence[float],
) -> list[tuple[float, float, float]]:
    """Carry ``seed`` along the curve by double reflection (Wang et al. 2008).

    Each step reflects the frame vector in the plane bisecting the two points,
    then in the plane bisecting the two tangents.  The composition is the
    rotation that takes tangent *i* to tangent *i+1* about their common
    perpendicular — the minimum rotation, hence no spurious twist — and it is
    two dot products and two scaled subtractions per sample.
    """

    normals: list[tuple[float, float, float]] = [tuple(seed)]  # type: ignore[list-item]
    for index in range(len(points) - 1):
        current = normals[index]
        step = _difference(points[index + 1], points[index])
        step_square = _dot(step, step)
        if step_square <= _DEGENERATE:
            normals.append(current)
            continue
        factor = 2.0 / step_square
        reflected_normal = _difference(current, _scaled(step, factor * _dot(step, current)))
        reflected_tangent = _difference(
            tangents[index], _scaled(step, factor * _dot(step, tangents[index]))
        )
        bisector = _difference(tangents[index + 1], reflected_tangent)
        bisector_square = _dot(bisector, bisector)
        if bisector_square > _DEGENERATE:
            reflected_normal = _difference(
                reflected_normal,
                _scaled(bisector, (2.0 / bisector_square) * _dot(bisector, reflected_normal)),
            )
        # Re-orthogonalise against the tangent before normalising: the two
        # reflections are exact in theory and drift in float over hundreds of
        # samples, and a frame that leans into the tangent shears the lay.
        aligned = _dot(reflected_normal, tangents[index + 1])
        reflected_normal = _difference(
            reflected_normal, _scaled(tangents[index + 1], aligned)
        )
        unit = _normalized(reflected_normal)
        normals.append(unit if unit is not None else _perpendicular_to(tangents[index + 1]))
    return normals


def _seed_normal(
    tangent: Sequence[float], up: Sequence[float] | None
) -> tuple[float, float, float]:
    """Where the lay starts, as a stated rule rather than a constant.

    With an ``up``, the seed is ``tangent x up`` — the direction across the
    run and square to ``up``, which is what makes a flat bundle lie flat
    rather than stand on edge.  Where the run is parallel to ``up`` that cross
    product has no direction, and the seed falls back to the world axis least
    parallel to the tangent.  Both branches are exact and reproducible; which
    one is taken depends only on the inputs.
    """

    if up is not None:
        seeded = _normalized(_cross(tangent, up))
        if seeded is not None:
            return seeded
    return _perpendicular_to(tangent)


def min_conductor_separation(radius: float, pitch: float, count: int) -> float:
    """Smallest centre-to-centre distance between any two conductors of a lay.

    Minimised over the axial offset, not evaluated in a shared cross-section —
    see the module docstring for why that distinction is the whole point.
    Every distinct phase separation is checked, not only neighbouring ones,
    and the scan runs over one pitch either side because ``f(u) >= u^2`` puts
    every interesting minimum inside that window.
    """

    if count < 2:
        return math.inf
    if radius <= 0.0:
        return 0.0
    rate = 2.0 * math.pi / pitch
    smallest = math.inf
    for step in range(1, count // 2 + 1):
        phase = 2.0 * math.pi * step / count
        twice_square = 2.0 * radius * radius

        def squared(offset: float, _phase: float = phase, _t: float = twice_square) -> float:
            return _t * (1.0 - math.cos(rate * offset - _phase)) + offset * offset

        best_offset, best_value = -pitch, squared(-pitch)
        for index in range(1, _SEPARATION_SCAN + 1):
            offset = -pitch + 2.0 * pitch * index / _SEPARATION_SCAN
            value = squared(offset)
            if value < best_value:
                best_offset, best_value = offset, value
        window = 2.0 * pitch / _SEPARATION_SCAN
        low, high = best_offset - window, best_offset + window
        for _ in range(_SEPARATION_REFINE):
            first = low + (high - low) / 3.0
            second = high - (high - low) / 3.0
            if squared(first) < squared(second):
                high = second
            else:
                low = first
        smallest = min(smallest, squared((low + high) / 2.0))
    return math.sqrt(smallest)


def bundle_radius(gauge_mm: float, *, count: int, pitch_mm: float) -> float:
    """The smallest lay radius at which no two conductors interpenetrate.

    Bisected between the chord radius ``(d/2)/sin(pi/N)`` — a hard lower bound,
    since neighbours already touch there in cross-section — and a bracket grown
    until the separation clears.  Fixed iteration counts throughout, so the
    answer is a pure function of the three arguments.
    """

    if count < 2:
        raise BundleError(
            "a bundle needs at least two conductors",
            reason="count",
            observed={"count": int(count)},
        )
    target = gauge_mm * _LAY_MARGIN
    low = (gauge_mm / 2.0) / math.sin(math.pi / count)
    if min_conductor_separation(low, pitch_mm, count) >= target:
        return low
    high = low
    for _ in range(_RADIUS_GROWTH_STEPS):
        high *= _RADIUS_GROWTH
        if min_conductor_separation(high, pitch_mm, count) >= target:
            break
    else:
        raise BundleError(
            f"{count} conductors of {gauge_mm:.3f} mm cannot be laid at a "
            f"{pitch_mm:.3f} mm pitch; no lay radius keeps them apart below a "
            f"{count * gauge_mm:.3f} mm pitch",
            reason="pitch",
            observed={
                "count": int(count),
                "gauge_mm": float(gauge_mm),
                "twist_pitch_mm": float(pitch_mm),
                "minimum_twist_pitch_mm": float(count * gauge_mm),
            },
        )
    for _ in range(_RADIUS_BISECTIONS):
        middle = (low + high) / 2.0
        if min_conductor_separation(middle, pitch_mm, count) >= target:
            high = middle
        else:
            low = middle
    return high


def default_twist_pitch(gauge_mm: float, *, count: int) -> float:
    """A lay length a real harness would recognise, and comfortably feasible.

    Twice the ``N * gauge`` floor, and at least ten times the touching bundle
    diameter — real rope and cable lay lengths sit at eight to fifteen times
    the bundle diameter, and both terms keep the solved radius within about
    15% of the touching radius rather than out on the hyperbola near the floor.
    """

    touching = gauge_mm / math.sin(math.pi / count) + gauge_mm
    return max(10.0 * touching, 2.0 * count * gauge_mm)


def outer_diameter(
    gauge_mm: float,
    *,
    count: int,
    style: str,
    twist_pitch_mm: float | None = None,
    spacing_mm: float | None = None,
) -> float:
    """How much room the whole lay needs, across its widest direction.

    This is what the route is searched at — the corridor has to clear the
    bundle, not one conductor — and for a flat lay it is the ribbon's width.
    """

    if style == "flat":
        spacing = gauge_mm if spacing_mm is None else spacing_mm
        return (count - 1) * spacing + gauge_mm
    pitch = default_twist_pitch(gauge_mm, count=count) if twist_pitch_mm is None else twist_pitch_mm
    return 2.0 * bundle_radius(gauge_mm, count=count, pitch_mm=pitch) + gauge_mm


def sample_count(
    length_mm: float,
    *,
    style: str,
    twist_pitch_mm: float | None = None,
    cell_mm: float | None = None,
) -> int:
    """How densely the shared centreline is sampled before the lay is placed.

    A twisted lay has to resolve the *twist*, not just the path, so the count
    follows the number of turns; a flat lay only has to resolve the path.  Both
    are pure functions of their inputs and both are clamped, so a long run at a
    tight pitch cannot ask for an unbuildable spline.
    """

    if style == "flat":
        step = cell_mm if cell_mm else max(length_mm / 200.0, _COINCIDENT_MM)
        raw = int(math.ceil(length_mm / step)) + 1
        return max(_MIN_SAMPLES, min(raw, _MAX_FLAT_SAMPLES))
    pitch = twist_pitch_mm if twist_pitch_mm else length_mm
    turns = max(1, int(math.ceil(length_mm / pitch)))
    raw = _SAMPLES_PER_TURN * turns + 1
    return max(_MIN_SAMPLES, min(raw, _MAX_TWISTED_SAMPLES))


def _breakout_weight(distance: float, breakout: float) -> float:
    """0 at the port, 1 once the conductor has joined the lay, smooth between.

    A raised cosine rather than a straight ramp, because its derivative
    vanishes at both ends: the conductor leaves its port along the run and
    joins the lay tangentially, so neither join is a corner the sweep has to
    turn.  That matters more than it sounds — an interpolating spline through
    a corner overshoots, and a swept circle around the overshoot
    self-intersects into a solid that is still closed, still valid, and the
    wrong volume.
    """

    if breakout <= 0.0:
        return 1.0
    ratio = distance / breakout
    if ratio <= 0.0:
        return 0.0
    if ratio >= 1.0:
        return 1.0
    return 0.5 - 0.5 * math.cos(math.pi * ratio)


def conductor_paths(
    centre_points: Sequence[Sequence[float]],
    *,
    count: int,
    style: str,
    gauge_mm: float,
    spacing_mm: float | None = None,
    twist_pitch_mm: float | None = None,
    left_handed: bool = False,
    up: Sequence[float] | None = None,
    start_points: Sequence[Sequence[float]] | None = None,
    end_points: Sequence[Sequence[float]] | None = None,
    breakout_mm: float | None = None,
) -> list[list[tuple[float, float, float]]]:
    """Place ``count`` conductors around one sampled centreline.

    ``centre_points`` is the shared route, already sampled densely enough to
    resolve the lay (:func:`sample_count` says how densely).  The result is one
    polyline per conductor, in the order the conductors were declared:
    conductor ``k`` takes phase ``2*pi*k/N`` of a twisted lay, or lane
    ``k - (N-1)/2`` of a flat one.  **That order is the caller's control over
    which wire sits where** — two conductors whose ports are ordered opposite
    to their lanes cross once near the breakout, which is what a real harness
    does.

    ``up`` orients the lay where the run starts: a flat bundle spreads square
    to it, so the default ``(0, 0, 1)`` makes a ribbon lie flat.  The frame is
    then *carried along* the route rather than re-levelled at each sample,
    which is both what a real ribbon does and the only formulation that does
    not degenerate where the run turns parallel to ``up``.

    With ``start_points`` and ``end_points`` — one port per conductor — each
    conductor also **fans out** at the ends: over ``breakout_mm`` of arc it
    blends between sitting on its own port and sitting in its place in the
    lay, so the run leaves the connector as N separate wires and becomes a
    bundle only once clear of it.  The blend is exact at both ends, so a
    conductor lands precisely on its port.  Without them the conductors are
    laid along the whole centreline and the ends are left to the caller.
    """

    if style not in STYLES:
        raise BundleError(
            f"unknown lay style {style!r}", reason="path", observed={"style": str(style)}
        )
    if count < 2:
        raise BundleError(
            "a bundle needs at least two conductors",
            reason="count",
            observed={"count": int(count)},
        )
    if not math.isfinite(gauge_mm) or gauge_mm <= 0.0:
        raise BundleError(
            "gauge_mm must be a positive diameter",
            reason="path",
            observed={"gauge_mm": float(gauge_mm)},
        )

    points = _deduped(centre_points)
    if len(points) < 2:
        raise BundleError(
            "the shared centreline has no length to lay conductors along",
            reason="path",
            observed={"samples": len(points)},
        )

    tangents = _tangents(points)
    seed_up = None if up is None else _normalized(up)
    normals = _frame(points, tangents, _seed_normal(tangents[0], seed_up))
    samples = len(points)

    # Arc length as cumulative chord, summed left to right in one fixed order:
    # float addition is not associative, and this sum feeds every phase angle.
    arc = [0.0]
    for index in range(samples - 1):
        arc.append(arc[index] + _norm(_difference(points[index + 1], points[index])))
    total = arc[-1]

    if style == "flat":
        spacing = gauge_mm if spacing_mm is None else float(spacing_mm)
        lanes = [(index - (count - 1) / 2.0) * spacing for index in range(count)]

        def lay_offset(conductor: int, sample: int) -> tuple[float, float, float]:
            return _scaled(normals[sample], lanes[conductor])

    else:
        pitch = (
            default_twist_pitch(gauge_mm, count=count)
            if twist_pitch_mm is None
            else float(twist_pitch_mm)
        )
        if not math.isfinite(pitch) or pitch <= 0.0:
            raise BundleError(
                "twist_pitch_mm must be a positive length",
                reason="pitch",
                observed={"twist_pitch_mm": float(pitch)},
            )
        radius = bundle_radius(gauge_mm, count=count, pitch_mm=pitch)
        rate = (-1.0 if left_handed else 1.0) * 2.0 * math.pi / pitch
        phases = [2.0 * math.pi * index / count for index in range(count)]

        def lay_offset(conductor: int, sample: int) -> tuple[float, float, float]:
            angle = rate * arc[sample] + phases[conductor]
            across = radius * math.cos(angle)
            along = radius * math.sin(angle)
            normal = normals[sample]
            binormal = _cross(tangents[sample], normal)
            return (
                normal[0] * across + binormal[0] * along,
                normal[1] * across + binormal[1] * along,
                normal[2] * across + binormal[2] * along,
            )

    # The fan-out. Without ports the conductors are laid along the whole run;
    # with them each end blends from the port's own offset into the lay.
    fanning = start_points is not None and end_points is not None
    if fanning:
        if len(start_points) != count or len(end_points) != count:  # type: ignore[arg-type]
            raise BundleError(
                "one start port and one end port are needed per conductor",
                reason="count",
                observed={
                    "count": int(count),
                    "start_points": len(start_points),  # type: ignore[arg-type]
                    "end_points": len(end_points),  # type: ignore[arg-type]
                },
            )
        # Half the run each at most: two breakouts that met in the middle
        # would leave no length actually laid up as a bundle.
        breakout = total / 4.0 if breakout_mm is None else float(breakout_mm)
        breakout = min(max(breakout, 0.0), total / 2.0)
        start_gap = [
            _difference(start_points[index], points[0]) for index in range(count)  # type: ignore[index]
        ]
        end_gap = [
            _difference(end_points[index], points[samples - 1]) for index in range(count)  # type: ignore[index]
        ]

    result: list[list[tuple[float, float, float]]] = []
    for conductor in range(count):
        path: list[tuple[float, float, float]] = []
        for sample in range(samples):
            offset = lay_offset(conductor, sample)
            base = points[sample]
            if fanning:
                entering = _breakout_weight(arc[sample], breakout)
                leaving = _breakout_weight(total - arc[sample], breakout)
                weight = entering * leaving
                start_share = 1.0 - entering
                end_share = 1.0 - leaving
                path.append(
                    tuple(  # type: ignore[arg-type]
                        base[axis]
                        + offset[axis] * weight
                        + start_gap[conductor][axis] * start_share
                        + end_gap[conductor][axis] * end_share
                        for axis in range(3)
                    )
                )
            else:
                path.append(
                    (
                        base[0] + offset[0],
                        base[1] + offset[1],
                        base[2] + offset[2],
                    )
                )
        result.append(path)
    return result
