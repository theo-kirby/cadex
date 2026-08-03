# SPDX-License-Identifier: LGPL-2.1-or-later

"""The wire router and the ``part.cable`` contract (ADR-056).

``CadexRouting`` imports nothing from FreeCAD, so the search itself is
exercised here against synthetic occupancy grids rather than against OCC.
What is asserted is the set of properties the rest of the system depends on:
a route is reproducible, it clears obstacles by the stated clearance, it
refuses instead of hanging, and it terminates exactly on the two ports.
"""

from __future__ import annotations

import math

import pytest

import CadexRouting
from CadexRouting import RoutingError, polyline_length, route_path
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import create_domain_api


PART_PACK = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]
MESH_PACK = XSCRIPT_WORKBENCH_PACKS["MeshWorkbench"]


def _part():
    return create_domain_api(PART_PACK.domain, PART_PACK.api_exports, PART_PACK.output_types)


def _mesh():
    return create_domain_api(MESH_PACK.domain, MESH_PACK.api_exports, MESH_PACK.output_types)


#: The corridor every test routes inside, and the cell size it uses.  The
#: predicate the router calls is in *lattice cells*, whose origin is the
#: corridor's low corner — so a test that wants to describe an obstacle in
#: millimetres converts, exactly as the part worker does.
CORRIDOR = ((-10.0, -20.0, -20.0), (50.0, 20.0, 20.0))
CELL_MM = 1.0

BLOCK = ((15.0, -6.0, -6.0), (25.0, 6.0, 6.0))


def _cell_center(i: int, j: int, k: int) -> tuple[float, float, float]:
    low = CORRIDOR[0]
    return tuple(low[axis] + ((i, j, k)[axis] + 0.5) * CELL_MM for axis in range(3))


def _empty(_i: int, _j: int, _k: int) -> bool:
    return False


def _solid_box(low, high, *, calls=None):
    """An axis-aligned block of solid material, in millimetres."""

    def occupied(i: int, j: int, k: int) -> bool:
        if calls is not None:
            calls.append((i, j, k))
        point = _cell_center(i, j, k)
        return all(low[axis] <= point[axis] <= high[axis] for axis in range(3))

    return occupied


def _route(**overrides):
    # ``standoff_mm`` is this helper's shorthand for "the same at both ends",
    # which is what every test here wants; the router itself takes one per end
    # (ADR-062), and test_terminals exercises them differing.
    standoff = overrides.pop("standoff_mm", 1.0)
    kwargs = dict(
        start_point=(0.0, 0.0, 0.0),
        start_dir=(1.0, 0.0, 0.0),
        end_point=(40.0, 0.0, 0.0),
        end_dir=(-1.0, 0.0, 0.0),
        occupied=_empty,
        cell_mm=CELL_MM,
        clearance_mm=0.0,
        start_standoff_mm=standoff,
        end_standoff_mm=standoff,
        slack=1.0,
        bounds=CORRIDOR,
        max_cells=200000,
    )
    kwargs.update(overrides)
    return route_path(**kwargs)


def _min_distance_to_box(points, low, high):
    """Closest approach of a polyline to an axis-aligned block, in mm.

    Sampled densely: what matters is the whole centreline clearing the
    obstacle, not just its waypoints.
    """

    best = math.inf
    for index in range(len(points) - 1):
        first, second = points[index], points[index + 1]
        span = math.dist(first, second)
        steps = max(1, int(math.ceil(span / 0.05)))
        for step in range(steps + 1):
            ratio = step / steps
            sample = [first[a] + (second[a] - first[a]) * ratio for a in range(3)]
            gap = 0.0
            for axis in range(3):
                outside = max(low[axis] - sample[axis], sample[axis] - high[axis], 0.0)
                gap += outside * outside
            best = min(best, math.sqrt(gap))
    return best


# --------------------------------------------------------------------------
# the search


def test_unobstructed_route_is_a_straight_run_between_the_ports() -> None:
    points = _route()

    assert points[0] == (0.0, 0.0, 0.0)
    assert points[-1] == (40.0, 0.0, 0.0)
    assert len(points) >= 3
    # Nothing in the way: the shortcut pass must collapse the lattice
    # staircase back to (very nearly) the straight run.
    assert polyline_length(points) == pytest.approx(40.0, rel=1.0e-3)


def test_route_detours_around_a_blocking_box() -> None:
    points = _route(occupied=_solid_box(*BLOCK))

    assert polyline_length(points) > 40.0
    assert _min_distance_to_box(points, *BLOCK) > 0.0


def test_identical_input_routes_identically() -> None:
    first = _route(occupied=_solid_box(*BLOCK), slack=1.08)
    second = _route(occupied=_solid_box(*BLOCK), slack=1.08)

    # Exact equality, not approximate: the project digest is recomputed from
    # the rebuilt geometry and open_project asserts it is unchanged.
    assert first == second


def test_a_sealed_corridor_refuses_with_a_named_reason() -> None:
    wall = _solid_box((18.0, -100.0, -100.0), (22.0, 100.0, 100.0))
    with pytest.raises(RoutingError) as excinfo:
        _route(occupied=wall)

    assert excinfo.value.reason == "blocked"
    assert "clearance" in str(excinfo.value)


def test_the_search_is_bounded_rather_than_unbounded() -> None:
    wall = _solid_box((18.0, -100.0, -100.0), (22.0, 100.0, 100.0))
    with pytest.raises(RoutingError) as excinfo:
        _route(occupied=wall, max_cells=400)

    assert excinfo.value.reason == "budget"
    assert excinfo.value.observed["max_cells"] == 400


def test_occupancy_is_lazy_and_probed_at_most_once_per_cell() -> None:
    calls: list[tuple[int, int, int]] = []
    _route(occupied=_solid_box(*BLOCK, calls=calls))

    assert len(calls) == len(set(calls))
    # The corridor is 60x40x40 cells; a search that materialised it would
    # probe 96000 cells.  This one walks a corridor, not a volume.
    assert len(calls) < 96000 / 4


def test_clearance_pushes_the_route_away_from_the_obstacle() -> None:
    tight = _route(occupied=_solid_box(*BLOCK), clearance_mm=0.0)
    wide = _route(occupied=_solid_box(*BLOCK), clearance_mm=3.0, standoff_mm=3.5)

    assert _min_distance_to_box(wide, *BLOCK) > _min_distance_to_box(tight, *BLOCK)
    assert _min_distance_to_box(wide, *BLOCK) >= 2.0


def test_the_standoff_stub_is_exempt_from_the_ports_own_material() -> None:
    # Both ports sit on the face of a solid pad, which is what a real
    # connector does; without the standoff exemption their own cells are
    # occupied and nothing routes at all.
    def occupied(i: int, j: int, k: int) -> bool:
        near_start = -6 <= i <= 0 and -6 <= j <= 6 and -6 <= k <= 6
        near_end = 40 <= i <= 46 and -6 <= j <= 6 and -6 <= k <= 6
        return near_start or near_end

    points = _route(occupied=occupied, clearance_mm=1.0, standoff_mm=2.0)

    assert points[0] == (0.0, 0.0, 0.0)
    assert points[-1] == (40.0, 0.0, 0.0)
    # The stand-off anchor, along +X -- reached through the stub's own knots,
    # which is why it is not waypoint 1 (ADR-114).
    assert points[CadexRouting._STUB_SEGMENTS][0] == pytest.approx(2.0)


def test_each_standoff_stub_arrives_as_collinear_knots() -> None:
    """What keeps a wire straight where its joint holds it (ADR-114).

    These waypoints are interpolated, not connected: a spline through a
    one-segment stub is tangent to it at the port and free to bow immediately
    after, which put the wire through the side of its own solder. Knots along
    the stub are what bound it.
    """

    points = _route(standoff_mm=2.0, slack=1.0)
    knots = points[: CadexRouting._STUB_SEGMENTS + 1]

    assert len(knots) == 4
    # Evenly spaced along the port's own direction, anchor included.
    for index, point in enumerate(knots):
        assert point == pytest.approx(
            (2.0 * index / CadexRouting._STUB_SEGMENTS, 0.0, 0.0), abs=1.0e-9
        )
    # And the same at the far end, arriving rather than leaving.
    tail = points[-(CadexRouting._STUB_SEGMENTS + 1):]
    for index, point in enumerate(reversed(tail)):
        assert point == pytest.approx(
            (40.0 - 2.0 * index / CadexRouting._STUB_SEGMENTS, 0.0, 0.0), abs=1.0e-9
        )


def test_a_port_with_no_standoff_still_yields_distinct_waypoints() -> None:
    """The stub collapses rather than repeating a point three times."""

    points = _route(standoff_mm=0.0, slack=1.0)

    assert points[0] == (0.0, 0.0, 0.0)
    for index in range(len(points) - 1):
        assert math.dist(points[index], points[index + 1]) > 1.0e-6


def test_path_length_grows_monotonically_with_slack() -> None:
    lengths = [polyline_length(_route(slack=value)) for value in (1.0, 1.05, 1.15, 1.3)]

    assert lengths == sorted(lengths)
    assert lengths[0] < lengths[-1]
    # Sag is downward: a slack wire hangs below the taut run.
    assert min(point[2] for point in _route(slack=1.3)) < -0.5


def test_sag_leaves_the_ports_where_they_were() -> None:
    points = _route(slack=1.4)

    assert points[0] == (0.0, 0.0, 0.0)
    assert points[-1] == (40.0, 0.0, 0.0)


def test_routing_refuses_degenerate_corridors_and_directions() -> None:
    with pytest.raises(RoutingError) as flat:
        _route(bounds=((0.0, 0.0, 0.0), (0.0, 10.0, 10.0)))
    assert flat.value.reason == "bounds"

    with pytest.raises(RoutingError) as spin:
        _route(start_dir=(0.0, 0.0, 0.0))
    assert spin.value.reason == "bounds"

    with pytest.raises(RoutingError) as outside:
        _route(bounds=((-10.0, -20.0, -20.0), (20.0, 20.0, 20.0)))
    assert outside.value.reason == "bounds"


def test_waypoints_are_distinct_so_a_spline_can_interpolate_them() -> None:
    points = _route(standoff_mm=0.0, slack=1.0)

    assert len(points) >= 3
    for index in range(len(points) - 1):
        assert math.dist(points[index], points[index + 1]) > 1.0e-6


def test_the_neighbourhood_is_fully_ordered_and_corner_cutting_is_refused() -> None:
    assert CadexRouting._NEIGHBOURS == tuple(sorted(CadexRouting._NEIGHBOURS))
    assert len(CadexRouting._NEIGHBOURS) == 26
    # A face move has no sub-moves; a body diagonal has its three faces and
    # three edges, which is what stops a wire slipping through a corner.
    assert CadexRouting._SUB_OFFSETS[(1, 0, 0)] == ()
    assert len(CadexRouting._SUB_OFFSETS[(1, 1, 1)]) == 6


def test_a_diagonal_gap_is_not_a_route() -> None:
    # A two-cell-thick wall whose only opening is a staircase: the cells
    # (30, 20, 20) and (31, 21, 21) are free, and every cell that would let a
    # wire turn between them is solid.  Stepping straight across is a corner
    # cut through material, so this must refuse rather than thread it.
    holes = {(30, 20, 20), (31, 21, 21)}

    def occupied(i: int, j: int, k: int) -> bool:
        return i in (30, 31) and (i, j, k) not in holes

    with pytest.raises(RoutingError) as excinfo:
        _route(occupied=occupied)

    assert excinfo.value.reason == "blocked"


# --------------------------------------------------------------------------
# the part.cable contract


def test_cable_is_declared_by_the_part_pack_and_the_runtime() -> None:
    assert "cable" in PART_PACK.api_exports
    assert "cable" in _part().exported_names


def test_cable_returns_a_solid_carrying_its_route_parameters() -> None:
    value = _part().cable(
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        ((40.0, 0.0, 0.0), (-1.0, 0.0, 0.0)),
        gauge_mm=0.8,
        label="battery lead",
    )

    payload = value.to_payload()
    assert value.domain == "part"
    assert value.output_type == "solid"
    assert payload["operation"] == "cable"
    assert payload["arguments"][0] == [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
    assert payload["arguments"][1] == [[40.0, 0.0, 0.0], [-1.0, 0.0, 0.0]]
    assert payload["properties"]["gauge_mm"] == 0.8
    assert payload["properties"]["clearance_mm"] == 1.0
    assert payload["properties"]["slack"] == 1.05
    assert payload["properties"]["label"] == "battery lead"
    assert payload["properties"]["avoid"] == []


def test_cable_accepts_part_and_mesh_obstacles_together() -> None:
    part_api, mesh_api = _part(), _mesh()
    obstacles = [
        part_api.box(10.0, 10.0, 10.0),
        mesh_api.import_file("scan.stl"),
    ]
    value = part_api.cable(
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        ((40.0, 0.0, 0.0), (-1.0, 0.0, 0.0)),
        gauge_mm=0.8,
        avoid=obstacles,
    )

    avoid = value.to_payload()["properties"]["avoid"]
    assert [entry["domain"] for entry in avoid] == ["part", "mesh"]


def test_cable_refuses_an_approximating_mesh_obstacle() -> None:
    mesh_api = _mesh()
    decimated = mesh_api.decimate(
        mesh_api.import_file("scan.stl"), tolerance=0.1, reduction=0.5
    )

    with pytest.raises(ValueError, match="decimate"):
        _part().cable(
            ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
            ((40.0, 0.0, 0.0), (-1.0, 0.0, 0.0)),
            gauge_mm=0.8,
            avoid=[decimated],
        )


def test_cable_validates_its_ports_and_options() -> None:
    part_api = _part()
    start = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    end = ((40.0, 0.0, 0.0), (-1.0, 0.0, 0.0))

    with pytest.raises(ValueError, match="start"):
        part_api.cable((0.0, 0.0, 0.0), end, gauge_mm=0.8)
    with pytest.raises(ValueError, match="start"):
        part_api.cable(((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)), end, gauge_mm=0.8)
    with pytest.raises(ValueError, match="end"):
        part_api.cable(start, ((40.0, 0.0, 0.0),), gauge_mm=0.8)
    with pytest.raises(ValueError, match="gauge_mm"):
        part_api.cable(start, end, gauge_mm=0.0)
    with pytest.raises(ValueError, match="clearance_mm"):
        part_api.cable(start, end, gauge_mm=0.8, clearance_mm=-1.0)
    with pytest.raises(ValueError, match="slack"):
        part_api.cable(start, end, gauge_mm=0.8, slack=0.9)
    with pytest.raises(ValueError, match="cell_mm"):
        part_api.cable(start, end, gauge_mm=0.8, cell_mm=0.0)
    with pytest.raises(ValueError, match="min_bend_radius_mm"):
        part_api.cable(start, end, gauge_mm=0.8, min_bend_radius_mm=0.0)
    with pytest.raises(ValueError, match="avoid"):
        part_api.cable(start, end, gauge_mm=0.8, avoid=[{"domain": "part"}])
    with pytest.raises(ValueError, match="start"):
        part_api.cable((start[0], start[1], start[0]), end, gauge_mm=0.8)


def test_cable_refuses_two_ports_at_the_same_place() -> None:
    with pytest.raises(ValueError, match="start/end"):
        _part().cable(
            ((1.0, 2.0, 3.0), (1.0, 0.0, 0.0)),
            ((1.0, 2.0, 3.0), (-1.0, 0.0, 0.0)),
            gauge_mm=0.8,
        )


# --------------------------------------------------------------------------
# an authored path: waypoints= (ADR-118)


def test_the_searched_route_splits_into_anchors_and_an_interior() -> None:
    """The split ADR-118 needs, asserted against the spine it composes back to.

    ``route_interior`` and ``assemble_spine`` are ``route_path`` cut in half,
    and the half that matters is the interior: it is the only part of a route
    a user may author, because the stubs and the anchors are regenerated from
    the terminals on every rebuild.
    """

    common = dict(
        occupied=_solid_box(*BLOCK),
        cell_mm=CELL_MM,
        clearance_mm=0.0,
        start_standoff_mm=3.0,
        end_standoff_mm=3.0,
        slack=1.0,
        bounds=CORRIDOR,
        max_cells=200000,
    )
    start, end = (0.0, 0.0, 0.0), (40.0, 0.0, 0.0)
    interior, anchor_start, anchor_end = CadexRouting.route_interior(
        start, (1.0, 0.0, 0.0), end, (-1.0, 0.0, 0.0), **common
    )
    spine = route_path(start, (1.0, 0.0, 0.0), end, (-1.0, 0.0, 0.0), **common)

    # The anchors are the stated stand-off in from each port...
    assert anchor_start[0] == pytest.approx(3.0)
    assert anchor_end[0] == pytest.approx(37.0)
    # ...the interior is what the search found between them, and it detoured.
    assert interior
    assert all(abs(point[1]) > 1.0e-9 or abs(point[2]) > 1.0e-9 for point in interior)
    # ...and the two compose back into exactly the spine route_path returns.
    assert CadexRouting.assemble_spine(
        start, anchor_start, interior, anchor_end, end
    ) == spine


def test_assemble_spine_gives_an_authored_path_the_same_stubs_a_searched_one_has() -> None:
    """Why an authored path goes through the same three helpers (ADR-118).

    The stub knots, the coincident-point dedup and the at-least-three floor
    are properties of what a spline can be fitted through, not of how the
    middle was arrived at. Handing authored points to the sweep raw would
    lose all three.
    """

    authored = CadexRouting.assemble_spine(
        (0.0, 0.0, 0.0), (3.0, 0.0, 0.0),
        [(20.0, 9.0, 0.0)],
        (37.0, 0.0, 0.0), (40.0, 0.0, 0.0),
    )

    stub = CadexRouting._STUB_SEGMENTS
    assert authored[0] == (0.0, 0.0, 0.0)
    assert authored[-1] == (40.0, 0.0, 0.0)
    # Each stub arrives as its own collinear knots, and the anchor closes it.
    assert authored[:stub + 1] == [
        (3.0 * index / stub, 0.0, 0.0) for index in range(stub + 1)
    ]
    assert authored[stub + 1] == (20.0, 9.0, 0.0)
    assert authored[-(stub + 1)] == (37.0, 0.0, 0.0)
    # The ends still ride their ports: only the interior is authored.
    assert authored.count((20.0, 9.0, 0.0)) == 1


def test_an_authored_path_of_coincident_points_still_feeds_the_interpolator() -> None:
    """A user can drag two handles onto each other; a spline cannot take that."""

    spine = CadexRouting.assemble_spine(
        (0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
        [(5.0, 0.0, 0.0), (5.0, 0.0, 0.0), (5.0, 0.0, 0.0)],
        (10.0, 0.0, 0.0), (10.0, 0.0, 0.0),
    )

    assert len(spine) >= 3
    assert all(
        polyline_length([spine[index], spine[index + 1]]) > 0.0
        for index in range(len(spine) - 1)
    )


def test_cable_carries_authored_waypoints_into_its_payload() -> None:
    value = _part().cable(
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        ((40.0, 0.0, 0.0), (-1.0, 0.0, 0.0)),
        gauge_mm=0.8,
        waypoints=[(10.0, 5.0, 0.0), (30.0, 5.0, 0.0)],
    )

    properties = value.to_payload()["properties"]
    assert properties["waypoints"] == [[10.0, 5.0, 0.0], [30.0, 5.0, 0.0]]
    # Absent when unset, like every other optional route argument: what it
    # falls back to is a search, and the search runs in the worker.
    assert "waypoints" not in _part().cable(
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        ((40.0, 0.0, 0.0), (-1.0, 0.0, 0.0)),
        gauge_mm=0.8,
    ).to_payload()["properties"]


def test_cable_validates_an_authored_path_point_by_point() -> None:
    part_api = _part()
    start = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    end = ((40.0, 0.0, 0.0), (-1.0, 0.0, 0.0))

    with pytest.raises(ValueError, match="waypoints"):
        part_api.cable(start, end, gauge_mm=0.8, waypoints=[])
    with pytest.raises(ValueError, match=r"waypoints\[1\]"):
        part_api.cable(
            start, end, gauge_mm=0.8, waypoints=[(1.0, 2.0, 3.0), (4.0, 5.0)]
        )
    with pytest.raises(ValueError, match=r"waypoints\[0\]\[2\]"):
        part_api.cable(
            start, end, gauge_mm=0.8, waypoints=[(1.0, 2.0, float("nan"))]
        )
    with pytest.raises(ValueError, match="waypoints"):
        part_api.cable(start, end, gauge_mm=0.8, waypoints=(0.0, 0.0, 0.0))
    from cadex_part_api import MAX_WAYPOINTS

    with pytest.raises(ValueError, match=str(MAX_WAYPOINTS)):
        part_api.cable(
            start, end, gauge_mm=0.8,
            waypoints=[(float(index), 0.0, 0.0) for index in range(MAX_WAYPOINTS + 1)],
        )


def test_the_cable_docstring_says_what_an_authored_path_does_not_do() -> None:
    """The staleness ADR-056 objected to is real here and is said out loud.

    ADR-118 reverses "waypoints must never be in the script" for *authored*
    points and not for cached ones, and the difference is only defensible if
    the docstring the model reads carries it.
    """

    text = _part().cable.__doc__ or ""

    assert "waypoints" in text
    assert "the search does not run at all" in text
    assert "Only the interior is authored" in text
    assert "ignored" in text and "slack" in text


# --------------------------------------------------------------------------
# ...and the whole authored path, against a real kernel
# --------------------------------------------------------------------------


#: Run inside ``FreeCADCmd``: sweep an authored path, and prove the three
#: things that cannot be checked headless — that the search really is skipped,
#: that the path is still collision-checked against ``avoid``, and that the
#: route the run followed is published for the canvas to draw.
_AUTHORED_PROBE = r"""
import json, sys
sys.path.insert(0, %(root)r)
import CadexRouting
import cadex_part_worker as worker

# A block the straight line between the ports runs into, and which a search
# can get round -- so "it went over the top" is a statement about the authored
# path and not about the only way through.
WALL = {
    "domain": "part", "operation": "box", "output_type": "solid",
    "arguments": [4.0, 12.0, 12.0],
    "properties": {"origin": [18.0, -6.0, -6.0]},
}

START = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
END = [[40.0, 0.0, 0.0], [-1.0, 0.0, 0.0]]


def cable(**properties):
    base = {"gauge_mm": 0.8, "clearance_mm": 0.5, "slack": 1.02, "avoid": []}
    base.update(properties)
    return {
        "domain": "part", "operation": "cable", "output_type": "solid",
        "arguments": [START, END], "properties": base,
    }


def refusal(payload):
    try:
        worker.build_part_shape(payload)
    except Exception as exc:
        return {"message": "%%s" %% (exc,), "details": getattr(exc, "details", {})}
    return None


report = {}
try:
    # Over the wall rather than round it, stated by hand.
    OVER = [[10.0, 0.0, 14.0], [20.0, 0.0, 14.0], [30.0, 0.0, 14.0]]

    worker.reset_part_shape_memo()
    searched = worker.build_part_shape(cable(avoid=[WALL], cell_mm=1.0))
    report["searched"] = {
        "valid": bool(searched.isValid()), "solids": len(searched.Solids),
    }
    routes = worker.published_routes()
    report["searched_routes"] = len(routes)
    entry = list(routes.values())[0]
    report["searched_path_len"] = len(entry["path"])
    report["searched_waypoints"] = entry["waypoints"]
    report["searched_path_ends"] = [entry["path"][0], entry["path"][-1]]

    # The search is SKIPPED, not merely bypassed: route_interior raises if it
    # is reached at all, which is the only way to assert a negative here.
    worker.reset_part_shape_memo()
    real = CadexRouting.route_interior

    def forbidden(*args, **kwargs):
        raise AssertionError("the search ran for an authored path")

    CadexRouting.route_interior = forbidden
    try:
        authored = worker.build_part_shape(
            cable(avoid=[WALL], waypoints=OVER, cell_mm=1.0)
        )
    finally:
        CadexRouting.route_interior = real
    report["authored"] = {
        "valid": bool(authored.isValid()), "solids": len(authored.Solids),
    }
    box = authored.BoundBox
    report["authored_bounds"] = [
        float(box.XMin), float(box.YMin), float(box.ZMin),
        float(box.XMax), float(box.YMax), float(box.ZMax),
    ]
    published = list(worker.published_routes().values())[0]
    report["authored_waypoints"] = published["waypoints"]
    report["authored_path"] = published["path"]

    # Straight through the wall, on the second segment of three.
    worker.reset_part_shape_memo()
    report["blocked"] = refusal(
        cable(avoid=[WALL],
              waypoints=[[10.0, 0.0, 0.0], [30.0, 0.0, 0.0]],
              cell_mm=1.0)
    )
    # ...and the same path with nothing to avoid is a wire, so the refusal is
    # about the obstacle and not about the shape of the path.
    worker.reset_part_shape_memo()
    clear = worker.build_part_shape(
        cable(waypoints=[[10.0, 0.0, 0.0], [30.0, 0.0, 0.0]], cell_mm=1.0)
    )
    report["unblocked"] = {"valid": bool(clear.isValid()), "solids": len(clear.Solids)}

    # A dragged hairpin: min_bend_radius_mm still applies, and matters more.
    worker.reset_part_shape_memo()
    report["hairpin"] = refusal(
        cable(waypoints=[[20.0, 0.0, 0.0], [20.0, 0.0, 1.0], [20.0, 0.0, -1.0]],
              min_bend_radius_mm=5.0, cell_mm=1.0)
    )

    # A bundle publishes its shared spine and no editable interior at all.
    worker.reset_part_shape_memo()
    pair = [[START, END], [[[0.0, 3.0, 0.0], [1.0, 0.0, 0.0]],
                           [[40.0, 3.0, 0.0], [-1.0, 0.0, 0.0]]]]
    worker.build_part_shape({
        "domain": "part", "operation": "bundle", "output_type": "solid",
        "arguments": [pair],
        "properties": {"gauge_mm": 0.8, "conductor": 0, "style": "flat",
                       "clearance_mm": 0.5, "slack": 1.02, "avoid": [],
                       "cell_mm": 1.0},
    })
    bundled = list(worker.published_routes().values())[0]
    report["bundle_waypoints"] = bundled["waypoints"]
    report["bundle_path_len"] = len(bundled["path"])

    # One request's routes never reach another's.
    worker.reset_part_shape_memo()
    report["routes_after_reset"] = len(worker.published_routes())
except Exception as exc:
    import traceback
    report["crashed"] = traceback.format_exc()
open(%(out)r, "w").write(json.dumps(report))
"""


def _authored_report():
    import json
    import pathlib
    import subprocess
    import tempfile

    from test_cadexd_lifecycle import CADEX_ROOT, FREECADCMD

    scratch = pathlib.Path(tempfile.mkdtemp(prefix="cadex-authored-probe-"))
    out = scratch / "report.json"
    probe = scratch / "probe.py"
    probe.write_text(_AUTHORED_PROBE % {"root": str(CADEX_ROOT), "out": str(out)})
    finished = subprocess.run(
        [str(FREECADCMD), "-c", f"exec(open({str(probe)!r}).read())"],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert out.is_file(), finished.stdout[-4000:] + finished.stderr[-4000:]
    return json.loads(out.read_text())


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available to sweep an authored path.",
)
def test_an_authored_path_is_swept_without_a_search() -> None:
    report = _authored_report()

    assert "crashed" not in report, report.get("crashed")
    # It built, and `route_interior` raising proves the search never ran: the
    # only assertion that can say "skipped" rather than "bypassed".
    assert report["authored"] == {"valid": True, "solids": 1}
    # It went over the wall because it was told to, not because a search
    # preferred that side: 14 mm up, where the wall is 40 mm tall.
    assert report["authored_bounds"][5] > 13.0
    assert report["authored_waypoints"] == [
        [10.0, 0.0, 14.0], [20.0, 0.0, 14.0], [30.0, 0.0, 14.0]
    ]
    # The spine still terminates on the two ports, so both ends ride their
    # terminals and only the interior was authored.
    assert report["authored_path"][0] == [0.0, 0.0, 0.0]
    assert report["authored_path"][-1] == [40.0, 0.0, 0.0]


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available to sweep an authored path.",
)
def test_an_authored_path_through_an_obstacle_is_refused_by_name() -> None:
    """A wire through a board is never what was meant, and loud beats clever."""

    report = _authored_report()

    assert "crashed" not in report, report.get("crashed")
    blocked = report["blocked"]
    assert blocked is not None, "an authored path through a wall was accepted"
    observed = blocked["details"]["observed"]
    assert observed["reason"] == "waypoints_blocked"
    assert blocked["details"]["stage"] == "part_routing"
    # The wall spans x = 18..22, which the run from the first waypoint at
    # x = 10 to the second at x = 30 crosses: segment 1, counting the run out
    # of the start port's anchor as segment 0.
    assert observed["segment"] == 1
    assert observed["waypoints"] == [[10.0, 0.0, 0.0], [30.0, 0.0, 0.0]]
    assert "waypoint" in blocked["details"]["correction"]

    # The same path with an empty avoid is a wire: the refusal is about the
    # obstacle, not about the shape of the path.
    assert report["unblocked"] == {"valid": True, "solids": 1}


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available to sweep an authored path.",
)
def test_a_dragged_hairpin_is_refused_rather_than_folded() -> None:
    """``min_bend_radius_mm`` matters *more* under ADR-118, not less.

    A search will not produce a hairpin; a hand is one drag away from it, and
    a sweep through one folds silently (ADR-074).
    """

    report = _authored_report()

    assert "crashed" not in report, report.get("crashed")
    hairpin = report["hairpin"]
    assert hairpin is not None, "a folded-back authored path was swept"
    assert hairpin["details"]["stage"] in ("part_routing", "part_kernel")
    assert "bend" in hairpin["message"].lower() or "radius" in hairpin["message"].lower()


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available to publish a route.",
)
def test_the_route_a_run_followed_is_published_for_the_canvas() -> None:
    report = _authored_report()

    assert "crashed" not in report, report.get("crashed")
    # A searched cable publishes its whole centreline and the interior of it
    # that a user may author.
    assert report["searched"] == {"valid": True, "solids": 1}
    assert report["searched_routes"] == 1
    assert report["searched_path_len"] >= 3
    assert report["searched_path_ends"] == [[0.0, 0.0, 0.0], [40.0, 0.0, 0.0]]
    # It had to go round the wall, so the interior is not empty and is off the
    # straight line between the ports.
    assert report["searched_waypoints"]
    assert any(
        abs(point[1]) > 1.0 or abs(point[2]) > 1.0
        for point in report["searched_waypoints"]
    )

    # A bundle publishes its shared spine and *no* editable interior: its
    # route belongs to the bundle, so authoring one conductor's path would
    # silently be authoring all of them.
    assert report["bundle_waypoints"] == []
    assert report["bundle_path_len"] >= 3

    # And one request's routes never reach another's.
    assert report["routes_after_reset"] == 0
