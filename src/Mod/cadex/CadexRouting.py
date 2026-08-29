# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Deterministic lattice routing for procedural wire paths (ADR-056).

The search behind ``part.cable``.  This module imports nothing from FreeCAD
and knows nothing about topology: the host hands it an ``occupied(i, j, k)``
predicate and gets back a polyline.  That is what makes the whole algorithm
unit-testable headless against synthetic occupancy grids, the same idiom the
shell's ``cadex_animate.curves_for_component`` uses to stay testable without
``bpy``.

Three properties are load-bearing, in this order.

**Determinism.**  ``open_project`` re-runs the accepted script and asserts
digest equality, so a route that varies run to run breaks the project, not
just the wire.  Every ordering in here is total and explicit: the frontier
pushes ``(f, g, cell)`` so heap ties break on cost and then lexicographically
on integer cell index, the neighbour offsets are a fixed sorted tuple, and no
step iterates a set or a dict.  Nothing reads the clock, the address space or
the hash seed.

**Laziness.**  Occupancy is the expensive half, so cells are probed only when
the search reaches them, and every probe is memoised.  The cost is the
corridor, not the model volume.

**Boundedness.**  ``max_cells`` caps the number of distinct cells whose
occupancy is evaluated.  A sealed corridor refuses with a stated reason
rather than grinding to the end of the lattice.
"""

from __future__ import annotations

import heapq
import math
from typing import Callable, Iterable, Sequence

__all__ = [
    "RoutingError",
    "assemble_spine",
    "route_path",
    "route_interior",
    "polyline_length",
]

#: Below this, two points are the same point — a spline interpolator rejects
#: coincident interpolation points, so the result is deduped against it.
_COINCIDENT_MM = 1.0e-6

#: Segment sampling step, in cells, for the line-of-sight and sag checks.
_SAMPLE_STEP_CELLS = 0.5

#: Bisection iterations used to hit a sag target length.  Fixed rather than
#: tolerance-driven so the answer is the same every run.
_SAG_ITERATIONS = 48

#: Heuristic weight.  Above 1.0 this is no longer an optimal A*: it may
#: return a path up to this factor longer than the shortest one, and in
#: exchange it settles far fewer cells.  That is the right trade here — a
#: wire that takes a slightly longer way round is still a wire, and the
#: shortcut pass recovers most of the difference anyway.
_HEURISTIC_WEIGHT = 1.35


class RoutingError(ValueError):
    """A route that could not be produced, with the reason named.

    ``reason`` is one of ``"bounds"``, ``"blocked"`` or ``"budget"``; the
    host maps it to a model-facing correction that says what to change.
    """

    def __init__(self, message: str, *, reason: str, observed: dict | None = None) -> None:
        self.reason = str(reason)
        self.observed = dict(observed or {})
        super().__init__(str(message))


def _neighbour_offsets() -> tuple[tuple[int, int, int], ...]:
    offsets = [
        (dx, dy, dz)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        for dz in (-1, 0, 1)
        if (dx, dy, dz) != (0, 0, 0)
    ]
    return tuple(sorted(offsets))


#: The 26-connected neighbourhood, in a fixed lexicographic order.
_NEIGHBOURS = _neighbour_offsets()


def _sub_offsets(offset: tuple[int, int, int]) -> tuple[tuple[int, int, int], ...]:
    """The proper non-zero sub-moves of one diagonal step.

    A 26-connected search will otherwise squeeze a wire through the diagonal
    gap between two blocked cells.  Requiring the sub-moves to be free is the
    standard no-corner-cutting rule; every check it adds is memoised, so it
    costs roughly one extra probe per reached cell rather than one per edge.
    """

    axes = [index for index in range(3) if offset[index]]
    if len(axes) < 2:
        return ()
    subs = []
    for mask in range(1, (1 << len(axes)) - 1):
        candidate = [0, 0, 0]
        for bit, axis in enumerate(axes):
            if mask & (1 << bit):
                candidate[axis] = offset[axis]
        subs.append((candidate[0], candidate[1], candidate[2]))
    return tuple(sorted(subs))


_SUB_OFFSETS = {offset: _sub_offsets(offset) for offset in _NEIGHBOURS}
_STEP_LENGTHS = {
    offset: math.sqrt(float(offset[0] ** 2 + offset[1] ** 2 + offset[2] ** 2))
    for offset in _NEIGHBOURS
}


def _ball_offsets(radius: int) -> tuple[tuple[int, int, int], ...]:
    """Cell offsets within a Euclidean ball of ``radius`` cells, sorted.

    A ball rather than a cube: for the common radius of 2 it is 33 cells
    instead of 125, and it is the shape the clearance actually describes.
    """

    if radius <= 0:
        return ((0, 0, 0),)
    limit = radius * radius
    offsets = [
        (dx, dy, dz)
        for dx in range(-radius, radius + 1)
        for dy in range(-radius, radius + 1)
        for dz in range(-radius, radius + 1)
        if dx * dx + dy * dy + dz * dz <= limit
    ]
    return tuple(sorted(offsets))


def _unit(vector: Sequence[float], *, name: str) -> tuple[float, float, float]:
    length = math.sqrt(sum(float(item) * float(item) for item in vector))
    if not math.isfinite(length) or length <= 1.0e-12:
        raise RoutingError(
            f"{name} has no direction to leave along",
            reason="bounds",
            observed={"vector": [float(item) for item in vector]},
        )
    return (float(vector[0]) / length, float(vector[1]) / length, float(vector[2]) / length)


def _point(value: Sequence[float]) -> tuple[float, float, float]:
    return (float(value[0]), float(value[1]), float(value[2]))


def _distance(first: Sequence[float], second: Sequence[float]) -> float:
    return math.sqrt(sum((float(first[k]) - float(second[k])) ** 2 for k in range(3)))


def polyline_length(points: Sequence[Sequence[float]]) -> float:
    """Total length of an ordered polyline."""

    return sum(_distance(points[index], points[index + 1]) for index in range(len(points) - 1))


class _Lattice:
    """Lazy, memoised free-space over an integer lattice.

    ``occupied`` answers for one cell; ``free`` answers for one cell *plus
    its clearance neighbourhood*, which is what the wire centreline actually
    needs.  Both memoise, and the probe count is the metered resource.
    """

    def __init__(
        self,
        occupied: Callable[[int, int, int], bool],
        *,
        origin: tuple[float, float, float],
        cell_mm: float,
        clearance_cells: int,
        counts: tuple[int, int, int],
        max_cells: int,
    ) -> None:
        self._occupied = occupied
        self._origin = origin
        self._cell_mm = cell_mm
        self._counts = counts
        self._ball = _ball_offsets(clearance_cells)
        self._max_cells = max_cells
        self._solid: dict[tuple[int, int, int], bool] = {}
        self._free: dict[tuple[int, int, int], bool] = {}
        self._exempt: set[tuple[int, int, int]] = set()
        self.probes = 0

    def extend_budget(self, extra: int) -> None:
        """Raise the probe cap once a path exists.

        The budget is there to bound the *search*.  Shortcutting and sag run
        over a path already found, and it would be perverse for them to turn
        a solved route into a budget refusal, so they get their own headroom.
        """

        self._max_cells += max(0, int(extra))

    def is_exempt(self, cell: tuple[int, int, int]) -> bool:
        return cell in self._exempt

    def exempt(self, cell: tuple[int, int, int]) -> None:
        """Declare a cell unconditionally free, and not blocking for others.

        The cells of the two port stubs.  A port sits *on* a component
        surface, so the run from it to its standoff anchor is inside that
        component's own material, and its anchor is usually still inside the
        clearance dilation of it; without this the search has nowhere to
        start and nothing routes at all.  The stub is the connector, not a
        routing choice, so it is exempt at both ends — as a place the wire
        may be, and as material that pushes the wire away.
        """

        self._exempt.add(cell)
        self._free[cell] = True

    def in_bounds(self, cell: tuple[int, int, int]) -> bool:
        return all(0 <= cell[k] < self._counts[k] for k in range(3))

    def center(self, cell: tuple[int, int, int]) -> tuple[float, float, float]:
        return (
            self._origin[0] + (cell[0] + 0.5) * self._cell_mm,
            self._origin[1] + (cell[1] + 0.5) * self._cell_mm,
            self._origin[2] + (cell[2] + 0.5) * self._cell_mm,
        )

    def cell_of(self, point: Sequence[float]) -> tuple[int, int, int]:
        return tuple(  # type: ignore[return-value]
            int(math.floor((float(point[k]) - self._origin[k]) / self._cell_mm)) for k in range(3)
        )

    def _solid_at(self, cell: tuple[int, int, int]) -> bool:
        cached = self._solid.get(cell)
        if cached is not None:
            return cached
        if self.probes >= self._max_cells:
            raise RoutingError(
                "the route search reached its cell budget before finding a path",
                reason="budget",
                observed={"probed_cells": self.probes, "max_cells": self._max_cells},
            )
        self.probes += 1
        result = bool(self._occupied(cell[0], cell[1], cell[2]))
        self._solid[cell] = result
        return result

    def free(self, cell: tuple[int, int, int]) -> bool:
        cached = self._free.get(cell)
        if cached is not None:
            return cached
        if not self.in_bounds(cell):
            self._free[cell] = False
            return False
        result = True
        for offset in self._ball:
            neighbour = (cell[0] + offset[0], cell[1] + offset[1], cell[2] + offset[2])
            if neighbour in self._exempt:
                continue
            if not self.in_bounds(neighbour):
                # Outside the corridor is unknown, not solid: the corridor is
                # a search bound, and treating its skin as material would
                # dilate a wall inwards along every face.
                continue
            if self._solid_at(neighbour):
                result = False
                break
        self._free[cell] = result
        return result

    def cells_along(
        self, first: Sequence[float], second: Sequence[float]
    ) -> list[tuple[int, int, int]]:
        """The cells one straight run passes through, in order, deduped."""

        span = _distance(first, second)
        steps = max(1, int(math.ceil(span / (self._cell_mm * _SAMPLE_STEP_CELLS))))
        result: list[tuple[int, int, int]] = []
        for index in range(steps + 1):
            ratio = index / steps
            sample = tuple(
                float(first[k]) + (float(second[k]) - float(first[k])) * ratio for k in range(3)
            )
            cell = self.cell_of(sample)
            if not result or result[-1] != cell:
                result.append(cell)
        return result

    def clear_segment(self, first: Sequence[float], second: Sequence[float]) -> bool:
        """True when every sampled cell along one straight run is free."""

        return all(self.free(cell) for cell in self.cells_along(first, second))


def _astar(
    lattice: _Lattice,
    start_cell: tuple[int, int, int],
    goal_cell: tuple[int, int, int],
    *,
    cell_mm: float,
) -> list[tuple[int, int, int]]:
    """Lazy A* on the 26-connected lattice; cost and heuristic in millimetres."""

    if start_cell == goal_cell:
        return [start_cell]
    goal_center = lattice.center(goal_cell)

    def heuristic(cell: tuple[int, int, int]) -> float:
        return _distance(lattice.center(cell), goal_center) * _HEURISTIC_WEIGHT

    frontier: list[tuple[float, float, tuple[int, int, int]]] = [
        (heuristic(start_cell), 0.0, start_cell)
    ]
    best: dict[tuple[int, int, int], float] = {start_cell: 0.0}
    came_from: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    settled: set[tuple[int, int, int]] = set()

    while frontier:
        _score, cost, cell = heapq.heappop(frontier)
        if cell in settled:
            continue
        settled.add(cell)
        if cell == goal_cell:
            path = [cell]
            while path[-1] != start_cell:
                path.append(came_from[path[-1]])
            path.reverse()
            return path
        for offset in _NEIGHBOURS:
            neighbour = (cell[0] + offset[0], cell[1] + offset[1], cell[2] + offset[2])
            if neighbour in settled or not lattice.free(neighbour):
                continue
            if neighbour != goal_cell and lattice.is_exempt(neighbour):
                # The stub is exempt so the *wire* may sit in it, not so the
                # *search* may travel down it.  An obstacle is blocked by its
                # surface, so a stub that starts on one punches a channel
                # through that surface; letting the search back down it would
                # let a route wander inside the component it leaves from.
                continue
            blocked_corner = False
            for sub in _SUB_OFFSETS[offset]:
                if not lattice.free((cell[0] + sub[0], cell[1] + sub[1], cell[2] + sub[2])):
                    blocked_corner = True
                    break
            if blocked_corner:
                continue
            candidate = cost + _STEP_LENGTHS[offset] * cell_mm
            if candidate < best.get(neighbour, math.inf):
                best[neighbour] = candidate
                came_from[neighbour] = cell
                heapq.heappush(frontier, (candidate + heuristic(neighbour), candidate, neighbour))

    raise RoutingError(
        "no clear corridor connects the two ports at the requested clearance",
        reason="blocked",
        observed={"probed_cells": lattice.probes},
    )


def _shortcut(
    lattice: _Lattice, points: list[tuple[float, float, float]]
) -> list[tuple[float, float, float]]:
    """Greedy line-of-sight reduction over the same free-space test.

    Without it the result is the lattice's staircase rather than a wire; the
    surviving waypoints are exactly the corners the obstacles force.
    """

    if len(points) <= 2:
        return list(points)
    kept = [points[0]]
    index = 0
    while index < len(points) - 1:
        furthest = index + 1
        for candidate in range(len(points) - 1, index, -1):
            if lattice.clear_segment(points[index], points[candidate]):
                furthest = candidate
                break
        kept.append(points[furthest])
        index = furthest
    return kept


def _sag(
    lattice: _Lattice,
    points: list[tuple[float, float, float]],
    *,
    slack: float,
) -> list[tuple[float, float, float]]:
    """Drop the interior waypoints along -Z until the run is ``slack`` times as long.

    A harness wire is not taut.  The displacement is a half-sine in
    normalised arc length, so the endpoints are fixed and the amount is one
    number; that number is found by bisection on total length, which makes it
    monotonic in ``slack``.  A displacement that would drive the wire into an
    obstacle is halved until it clears, so sag can shorten but never invent a
    collision.
    """

    taut = polyline_length(points)
    if slack <= 1.0 + 1.0e-12 or taut <= _COINCIDENT_MM:
        return list(points)
    if len(points) < 3:
        midpoint = tuple((points[0][k] + points[-1][k]) / 2.0 for k in range(3))
        points = [points[0], midpoint, points[-1]]  # type: ignore[list-item]

    cumulative = [0.0]
    for index in range(len(points) - 1):
        cumulative.append(cumulative[-1] + _distance(points[index], points[index + 1]))
    total = cumulative[-1]
    weights = [math.sin(math.pi * (value / total)) for value in cumulative]

    def displaced(depth: float) -> list[tuple[float, float, float]]:
        return [
            (point[0], point[1], point[2] - depth * weight)
            for point, weight in zip(points, weights)
        ]

    target = taut * slack
    high = total
    if polyline_length(displaced(high)) < target:
        depth = high
    else:
        low = 0.0
        for _ in range(_SAG_ITERATIONS):
            middle = (low + high) / 2.0
            if polyline_length(displaced(middle)) < target:
                low = middle
            else:
                high = middle
        depth = high

    for _ in range(_SAG_ITERATIONS):
        candidate = displaced(depth)
        if all(
            lattice.clear_segment(candidate[index], candidate[index + 1])
            for index in range(len(candidate) - 1)
        ):
            return candidate
        depth /= 2.0
        if depth <= _COINCIDENT_MM:
            break
    return list(points)


def _deduped(points: Iterable[Sequence[float]]) -> list[tuple[float, float, float]]:
    result: list[tuple[float, float, float]] = []
    for value in points:
        candidate = _point(value)
        if result and _distance(result[-1], candidate) <= _COINCIDENT_MM:
            continue
        result.append(candidate)
    return result


#: How many segments the straight stub in front of each port is written as.
#:
#: One — the stub the router actually plans — is what shipped, and it is not
#: enough. The spline fitted through these waypoints is *tangent* to the stub
#: at the port (ADR-074), but a C2 interpolation is free to bow the moment it
#: leaves, and it does: measured on `wiring-test-2`, the wire's centreline
#: strayed 0.20 mm off the terminal's axis inside the 1.24 mm run a joint
#: holds it straight for, against a collar clearing the lead by 0.025 mm. The
#: wire came out of one side of its own solder (ADR-114).
#:
#: Knots along the stub are the cheap fix: an interpolating spline through
#: collinear points stays between them. Three segments put two knots inside
#: every stub, and a stub of no length collapses back to one point in
#: `_deduped`, so a literal port with no stand-off is unchanged.
_STUB_SEGMENTS = 3


def _stub_knots(
    port: tuple[float, float, float], anchor: tuple[float, float, float]
) -> list[tuple[float, float, float]]:
    """The straight run from a port out to its stand-off anchor, as knots.

    The anchor is *not* included: it is the routed path's own first point,
    and repeating it would only be deduplicated away again.
    """

    return [
        tuple(
            port[k] + (anchor[k] - port[k]) * (index / _STUB_SEGMENTS)
            for k in range(3)
        )
        for index in range(_STUB_SEGMENTS)
    ]


def _at_least_three(
    points: list[tuple[float, float, float]]
) -> list[tuple[float, float, float]]:
    """Subdivide until the polyline has the three points a spline needs."""

    while len(points) < 3:
        if len(points) < 2:
            raise RoutingError(
                "the two ports resolve to the same point, so there is no run to route",
                reason="bounds",
                observed={"points": [list(point) for point in points]},
            )
        midpoint = tuple((points[0][k] + points[1][k]) / 2.0 for k in range(3))
        points.insert(1, midpoint)  # type: ignore[arg-type]
    return points


def assemble_spine(
    port_start: Sequence[float],
    anchor_start: Sequence[float],
    interior: Iterable[Sequence[float]],
    anchor_end: Sequence[float],
    port_end: Sequence[float],
) -> list[tuple[float, float, float]]:
    """The three helpers a spline interpolator's input contract is made of.

    A route is a straight stub out of each port and something in between, and
    the something is either searched (:func:`route_path`) or **authored**
    (ADR-118).  Both go through here rather than one of them handing points to
    the sweep raw, which is the whole reason this is a function: the stub
    knots (``_STUB_SEGMENTS``, ADR-114), the coincident-point dedup and the
    at-least-three floor are properties of *what a spline can be fitted
    through*, not of how the middle was arrived at.

    ``interior`` is what lies strictly between the two anchors; the anchors
    themselves are added here, because they are where each stub ends and the
    straight run the joint needs stops.
    """

    return _at_least_three(
        _deduped(
            _stub_knots(_point(port_start), _point(anchor_start))
            + [_point(anchor_start)]
            + [_point(item) for item in interior]
            + [_point(anchor_end)]
            + list(reversed(_stub_knots(_point(port_end), _point(anchor_end))))
        )
    )


def route_interior(
    start_point: Sequence[float],
    start_dir: Sequence[float],
    end_point: Sequence[float],
    end_dir: Sequence[float],
    *,
    occupied: Callable[[int, int, int], bool],
    cell_mm: float,
    clearance_mm: float,
    start_standoff_mm: float,
    end_standoff_mm: float,
    slack: float,
    bounds: Sequence[Sequence[float]],
    max_cells: int,
) -> list[tuple[float, float, float]]:
    """Route one wire centreline between two directed ports.

    ``start_point``/``end_point`` sit on their component surfaces and
    ``start_dir``/``end_dir`` point away from those surfaces.  The search runs
    between ``point + dir * standoff_mm`` at each end; the two short stubs
    back to the ports are collision-exempt straight runs, because a port cell
    is by construction inside the component it belongs to.

    **The two stand-offs are separate numbers** (ADR-062).  Each end reserves
    the straight run its own joint needs, and a 0.4 mm lead on one end and a
    1.6 mm one on the other do not need the same: forcing the fine end out as
    far as the coarse one would make a short run a hairpin.

    ``occupied(i, j, k)`` answers whether one lattice cell is inside solid
    material.  It is called only for cells the search reaches, and never
    twice for the same cell.  ``bounds`` is ``((xmin, ymin, zmin), (xmax,
    ymax, zmax))``: the corridor the search may use, not the extent of the
    model.  ``max_cells`` caps the number of distinct cells probed.

    **Cell indices are relative to the corridor**, not to the model origin:
    cell ``(i, j, k)`` is centred at ``bounds[0] + (i + 0.5) * cell_mm`` per
    axis, and indices run from zero.  A host that reads world coordinates
    straight out of ``(i, j, k)`` will describe its obstacles in the wrong
    place, and the search will happily route through them.

    Returns ``(interior, anchor_start, anchor_end)`` — the waypoints strictly
    **between** the two stand-off anchors, and the anchors themselves.  That
    split is what ADR-118 needs: the anchors and the collinear stub knots in
    front of them are regenerated from the terminals on every rebuild, so the
    interior is the only part of a route a user may author, and it is exactly
    what would go into ``waypoints=`` to reproduce this run.
    :func:`assemble_spine` turns the three back into the polyline a spline
    interpolator takes.  Raises :class:`RoutingError` with a named ``reason``
    rather than searching without limit.
    """

    if not math.isfinite(cell_mm) or cell_mm <= 0.0:
        raise RoutingError("cell_mm must be a positive length", reason="bounds")
    if not math.isfinite(clearance_mm) or clearance_mm < 0.0:
        raise RoutingError("clearance_mm must not be negative", reason="bounds")
    if max_cells < 1:
        raise RoutingError("max_cells must allow at least one probe", reason="budget")

    origin = _point(bounds[0])
    far = _point(bounds[1])
    if any(far[k] - origin[k] <= 0.0 for k in range(3)):
        raise RoutingError(
            "the routing corridor has no volume",
            reason="bounds",
            observed={"bounds": [list(origin), list(far)]},
        )
    counts = tuple(
        max(1, int(math.ceil((far[k] - origin[k]) / cell_mm))) for k in range(3)
    )

    port_start = _point(start_point)
    port_end = _point(end_point)
    exit_start = _unit(start_dir, name="start direction")
    exit_end = _unit(end_dir, name="end direction")
    start_standoff = max(0.0, float(start_standoff_mm))
    end_standoff = max(0.0, float(end_standoff_mm))
    anchor_start = tuple(port_start[k] + exit_start[k] * start_standoff for k in range(3))
    anchor_end = tuple(port_end[k] + exit_end[k] * end_standoff for k in range(3))

    lattice = _Lattice(
        occupied,
        origin=origin,
        cell_mm=cell_mm,
        clearance_cells=int(math.ceil(clearance_mm / cell_mm)),
        counts=counts,  # type: ignore[arg-type]
        max_cells=int(max_cells),
    )
    start_cell = lattice.cell_of(anchor_start)
    goal_cell = lattice.cell_of(anchor_end)
    for cell, name in ((start_cell, "start"), (goal_cell, "end")):
        if not lattice.in_bounds(cell):
            raise RoutingError(
                f"the {name} port stands off outside the routing corridor",
                reason="bounds",
                observed={"cell": list(cell), "counts": list(counts)},
            )
    for port, anchor in ((port_start, anchor_start), (port_end, anchor_end)):
        for cell in lattice.cells_along(port, anchor):
            if lattice.in_bounds(cell):
                lattice.exempt(cell)

    cells = _astar(lattice, start_cell, goal_cell, cell_mm=cell_mm)
    lattice.extend_budget(int(max_cells))
    lattice_points = _deduped(
        [anchor_start] + [lattice.center(cell) for cell in cells] + [anchor_end]
    )
    routed = _sag(lattice, _shortcut(lattice, lattice_points), slack=float(slack))
    if len(routed) < 2:
        return [], anchor_start, anchor_end
    # `routed[0]`/`routed[-1]` rather than the two anchors computed above, and
    # the difference is 6e-16. `_sag` weights each point by
    # ``sin(pi * s / total)``, and at the far end that is ``sin(pi)`` — which
    # is 1.22e-16 in binary floating point, not zero, so the sag nudges the
    # end anchor by about ``6e-16 mm``. Returning the *routed* endpoints keeps
    # every spine this function has ever produced bit-identical, and a spine
    # that moves in the sixteenth digit still moves the exported BREP, and so
    # the project digest, and so forces a re-accept for no reason at all.
    # What lies between the two is the searched middle, and it is the same
    # thing an authored ``waypoints=`` states directly (ADR-118).
    return list(routed[1:-1]), routed[0], routed[-1]


def route_path(
    start_point: Sequence[float],
    start_dir: Sequence[float],
    end_point: Sequence[float],
    end_dir: Sequence[float],
    *,
    occupied: Callable[[int, int, int], bool],
    cell_mm: float,
    clearance_mm: float,
    start_standoff_mm: float,
    end_standoff_mm: float,
    slack: float,
    bounds: Sequence[Sequence[float]],
    max_cells: int,
) -> list[tuple[float, float, float]]:
    """:func:`route_interior`, assembled into a spine. See both docstrings.

    The composition ``part.cable`` and ``part.bundle`` have always performed,
    and the one an authored path (ADR-118) replaces only the middle of. A
    caller that wants to *publish* the route wants the middle on its own and
    calls the two halves itself; one that only wants a wire calls this.
    """

    interior, anchor_start, anchor_end = route_interior(
        start_point,
        start_dir,
        end_point,
        end_dir,
        occupied=occupied,
        cell_mm=cell_mm,
        clearance_mm=clearance_mm,
        start_standoff_mm=start_standoff_mm,
        end_standoff_mm=end_standoff_mm,
        slack=slack,
        bounds=bounds,
        max_cells=max_cells,
    )
    return assemble_spine(
        start_point, anchor_start, interior, anchor_end, end_point
    )
