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
    # The first interior waypoint is the standoff anchor, along +X.
    assert points[1][0] == pytest.approx(2.0)


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
