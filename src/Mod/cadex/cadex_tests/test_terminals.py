# SPDX-License-Identifier: LGPL-2.1-or-later

"""Terminals: ports that name geometry (ADR-062).

``part.cable`` and ``part.bundle`` shipped taking literal ``(point,
direction)`` pairs, and ADR-056 named that as the gap it was leaving.  A
literal is wrong by construction for a through-hole, which has no surface
point to attach to; it is stale the moment a slider moves the component it
was measured off; and it does not say which signal it is.

``CadexTerminals`` imports nothing from FreeCAD, so the layout, the ordering,
the landing points and the placement arithmetic are exercised here against
plain numbers, exactly as ``CadexRouting`` and ``CadexBundle`` are.  The
worker's own extraction — the handful of values it reads off a matched
face — is exercised against fake shapes, the fixture idiom
``test_subshape_selectors`` established.  The end-to-end path through a real
kernel is at the bottom, behind the same ``FreeCADCmd`` skip the bundle
suite uses.
"""

from __future__ import annotations

import json
import math
import pathlib
import subprocess
import tempfile

import pytest

import CadexTerminals
from CadexTerminals import (
    Terminal,
    TerminalError,
    TerminalSet,
    apply_placement,
    declared_layout,
    identity_matrix,
    resolve_terminals,
    selector_layout,
)
from CadexRouting import route_path
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import DomainValue, create_domain_api


PART_PACK = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]
MESH_PACK = XSCRIPT_WORKBENCH_PACKS["MeshWorkbench"]


def _part():
    return create_domain_api(PART_PACK.domain, PART_PACK.api_exports, PART_PACK.output_types)


def _mesh():
    return create_domain_api(MESH_PACK.domain, MESH_PACK.api_exports, MESH_PACK.output_types)


def _board():
    return _part().box(40.0, 20.0, 1.6, label="board")


def _module():
    return _mesh().import_file("esp32.stl")


#: A four-pin 2.54 mm header drilled 1.6 mm into a board, stated in the
#: component's own frame: the numbers you read off a datasheet once.
HEADER = dict(
    origin=(0.0, 0.0, 0.0),
    along=(0.0, 1.0, 0.0),
    axis=(0.0, 0.0, -1.0),
    pitch=2.54,
    count=4,
    hole_dia=1.0,
    depth=1.6,
)
SIGNALS = ["vcc", "gnd", "sda", "scl"]


def _hole(center, axis=(0.0, 0.0, 1.0), extent=(0.0, 1.6), radius=0.5, ordinal=1):
    """One matched barrel, as the worker hands it over."""

    sort_point = [
        center[k] + axis[k] * (extent[0] + extent[1]) / 2.0 for k in range(3)
    ]
    return {
        "ordinal": ordinal,
        "axis": list(axis),
        "center": list(center),
        "radius": radius,
        "extent": list(extent),
        "sort_point": sort_point,
    }


def _pad(center, normal=(0.0, 0.0, 1.0), area=4.0, ordinal=1):
    return {
        "ordinal": ordinal,
        "center": list(center),
        "normal": list(normal),
        "area": area,
        "sort_point": list(center),
    }


def _by_name(terminals):
    return {entry["name"]: entry for entry in terminals}


# --------------------------------------------------------------------------
# the declared layout


def test_a_declared_header_expands_to_a_row_at_the_stated_pitch() -> None:
    layout = declared_layout(None, header=HEADER, names=SIGNALS)
    terminals = resolve_terminals(layout)

    assert [entry["name"] for entry in terminals] == SIGNALS
    # Four stations 2.54 mm apart along +Y, each landing 1.6 mm down the bore.
    assert [entry["point"] for entry in terminals] == [
        [0.0, 2.54 * index, -1.6] for index in range(4)
    ]
    # Drilled along -Z, so the wire leaves along +Z.
    assert all(entry["direction"] == [0.0, 0.0, 1.0] for entry in terminals)


def test_header_is_sugar_for_one_row_of_terminals() -> None:
    assert declared_layout(None, header=HEADER, names=SIGNALS) == declared_layout(
        [HEADER], names=SIGNALS
    )


def test_several_declared_rows_take_their_names_in_declaration_order() -> None:
    first = {**HEADER, "count": 2}
    second = {**HEADER, "origin": (10.0, 0.0, 0.0), "count": 1}
    terminals = resolve_terminals(
        declared_layout([first, second], names=["a", "b", "c"])
    )

    assert [entry["name"] for entry in terminals] == ["a", "b", "c"]
    assert terminals[2]["point"] == [10.0, 0.0, -1.6]


def test_a_declared_hole_floors_its_standoff_at_its_depth_and_a_pad_at_zero() -> None:
    hole = resolve_terminals(declared_layout(None, header=HEADER, names=SIGNALS))
    pad = resolve_terminals(
        declared_layout(
            None,
            header={"origin": (1.0, 2.0, 3.0), "axis": (0.0, 0.0, -1.0)},
            names=["signal"],
        )
    )

    assert all(entry["standoff_floor"] == pytest.approx(1.6) for entry in hole)
    assert hole[0]["metrics"]["kind"] == "hole"
    assert hole[0]["metrics"]["radius"] == pytest.approx(0.5)
    # A wire landing on the far face is inside the board for the whole depth
    # of it, so the search anchor has to start beyond that; a pad is on the
    # surface and needs nothing.
    assert pad[0]["standoff_floor"] == 0.0
    assert pad[0]["metrics"]["kind"] == "pad"
    assert pad[0]["point"] == [1.0, 2.0, 3.0]


def test_a_declared_layout_needs_exactly_one_name_per_terminal() -> None:
    with pytest.raises(TerminalError) as excinfo:
        declared_layout(None, header=HEADER, names=["vcc", "gnd"])

    assert excinfo.value.details["actual_count"] == 4
    assert excinfo.value.details["expected_count"] == 2
    assert "4 terminals" in str(excinfo.value)


def test_a_declared_layout_refuses_what_it_cannot_place() -> None:
    with pytest.raises(TerminalError, match="unrecognised"):
        declared_layout(None, header={**HEADER, "pich": 2.54}, names=SIGNALS)
    with pytest.raises(TerminalError, match="origin and axis"):
        declared_layout(None, header={"count": 2, "along": (0, 1, 0), "pitch": 1.0}, names=["a", "b"])
    with pytest.raises(TerminalError, match="along/pitch"):
        declared_layout(
            None, header={"origin": (0, 0, 0), "axis": (0, 0, 1), "count": 2}, names=["a", "b"]
        )
    with pytest.raises(TerminalError, match="depth"):
        declared_layout(None, header={**HEADER, "count": 1, "depth": -1.0}, names=["a"])
    with pytest.raises(TerminalError, match="hole_dia with no depth"):
        declared_layout(
            None,
            header={"origin": (0, 0, 0), "axis": (0, 0, 1), "hole_dia": 1.0},
            names=["a"],
        )
    with pytest.raises(TerminalError, match="no direction"):
        declared_layout(
            None, header={"origin": (0, 0, 0), "axis": (0, 0, 0)}, names=["a"]
        )
    with pytest.raises(TerminalError, match="distinct"):
        declared_layout(
            None, header={**HEADER, "count": 2}, names=["gnd", "gnd"]
        )
    with pytest.raises(TerminalError, match="not both"):
        declared_layout([HEADER], header=HEADER, names=SIGNALS)


# --------------------------------------------------------------------------
# the selector form: ordering and landing


def _plate_holes(exit=(0.0, 0.0, 1.0), order_by=(1.0, 0.0, 0.0), names=("a", "b", "c")):
    layout = selector_layout(
        "holes",
        {"geometry_type": "Cylinder", "radius": 0.5, "expected_count": len(names)},
        exit=exit,
        order_by=order_by,
        names=list(names),
    )
    # Deliberately handed over out of order: the ordering must come from the
    # geometry, never from the order the kernel happened to enumerate them.
    candidates = [
        _hole((20.0, 5.0, 0.0), ordinal=1),
        _hole((0.0, 5.0, 0.0), ordinal=2),
        _hole((10.0, 5.0, 0.0), ordinal=3),
    ]
    return resolve_terminals(layout, candidates=candidates[: len(names)])


def test_a_holes_selector_orders_its_terminals_along_order_by() -> None:
    terminals = _plate_holes()

    assert [entry["name"] for entry in terminals] == ["a", "b", "c"]
    assert [entry["point"][0] for entry in terminals] == [0.0, 10.0, 20.0]


def test_reversing_order_by_reverses_the_names() -> None:
    forward = _plate_holes(order_by=(1.0, 0.0, 0.0))
    backward = _plate_holes(order_by=(-1.0, 0.0, 0.0))

    assert [entry["point"] for entry in forward] == [
        entry["point"] for entry in reversed(backward)
    ]


def test_ordering_never_falls_back_to_kernel_enumeration_order() -> None:
    # The candidates arrive in the order 20, 0, 10 mm along +X; taking that
    # order would name the 20 mm hole 'a', which is exactly the index
    # reference ADR-029 deleted.
    assert _plate_holes()[0]["point"][0] == 0.0


def test_a_tie_along_the_primary_axis_breaks_on_a_fixed_secondary() -> None:
    layout = selector_layout(
        "pads",
        {"expected_count": 2},
        exit=(0.0, 0.0, 1.0),
        order_by=(0.0, 0.0, 1.0),
        names=["low", "high"],
    )
    # Two pads at the same height: nothing to choose between them along
    # order_by, so the secondary axis has to be a pure function of order_by
    # and give the same answer whichever way they are handed over.
    first = resolve_terminals(
        layout,
        candidates=[_pad((0.0, 0.0, 4.0), ordinal=1), _pad((9.0, 0.0, 4.0), ordinal=2)],
    )
    second = resolve_terminals(
        layout,
        candidates=[_pad((9.0, 0.0, 4.0), ordinal=1), _pad((0.0, 0.0, 4.0), ordinal=2)],
    )

    assert [entry["point"] for entry in first] == [entry["point"] for entry in second]


def test_a_hole_terminal_lands_on_the_far_face_and_floors_at_its_depth() -> None:
    upward = resolve_terminals(
        selector_layout(
            "holes", {"expected_count": 1}, exit=(0.0, 0.0, 1.0), names=["signal"]
        ),
        candidates=[_hole((3.0, 4.0, 0.0), axis=(0.0, 0.0, 1.0), extent=(0.0, 1.6))],
    )
    downward = resolve_terminals(
        selector_layout(
            "holes", {"expected_count": 1}, exit=(0.0, 0.0, -1.0), names=["signal"]
        ),
        candidates=[_hole((3.0, 4.0, 0.0), axis=(0.0, 0.0, 1.0), extent=(0.0, 1.6))],
    )

    # exit=+Z means the wire leaves upward, so it comes down from above,
    # threads the barrel and ends flush on the *bottom* — the opposite side.
    # Two holes wired to each other therefore meet in true centres rather
    # than each stopping a board thickness short.
    assert upward[0]["point"] == [3.0, 4.0, 0.0]
    assert downward[0]["point"] == [3.0, 4.0, 1.6]
    assert upward[0]["direction"] == [0.0, 0.0, 1.0]
    assert downward[0]["direction"] == [0.0, 0.0, -1.0]
    assert upward[0]["standoff_floor"] == pytest.approx(1.6)
    assert upward[0]["metrics"]["entry_point"] == [3.0, 4.0, 1.6]
    assert upward[0]["metrics"]["radius"] == pytest.approx(0.5)


def test_a_declared_row_and_a_selector_agree_on_which_end_is_which() -> None:
    """The two forms must land on the same face, or they mean different things.

    A declared row states the drilling direction and leaves along ``-axis``;
    a selector states the leaving direction and infers the rest.  Given the
    same physical hole they have to produce the same terminal, and this is
    the assertion that keeps them from drifting apart.
    """

    declared = resolve_terminals(
        declared_layout(
            None,
            header={"origin": (3.0, 4.0, 1.6), "axis": (0.0, 0.0, -1.0), "depth": 1.6},
            names=["signal"],
        )
    )
    selected = resolve_terminals(
        selector_layout(
            "holes", {"expected_count": 1}, exit=(0.0, 0.0, 1.0), names=["signal"]
        ),
        candidates=[_hole((3.0, 4.0, 0.0), axis=(0.0, 0.0, 1.0), extent=(0.0, 1.6))],
    )

    assert declared[0]["point"] == pytest.approx(selected[0]["point"])
    assert declared[0]["direction"] == pytest.approx(selected[0]["direction"])
    assert declared[0]["standoff_floor"] == pytest.approx(selected[0]["standoff_floor"])
    assert declared[0]["metrics"]["entry_point"] == pytest.approx(
        selected[0]["metrics"]["entry_point"]
    )


def test_a_pad_terminal_takes_the_face_centre_and_its_outward_normal() -> None:
    layout = selector_layout(
        "pads", {"expected_count": 1}, exit=(1.0, 0.0, 0.0), names=["signal"]
    )
    # An inward-facing normal is a fact about the face's orientation in the
    # shell, which is not something a script should have to know about.
    terminals = resolve_terminals(
        layout, candidates=[_pad((2.0, 0.0, 0.0), normal=(-1.0, 0.0, 0.0))]
    )

    assert terminals[0]["point"] == [2.0, 0.0, 0.0]
    assert terminals[0]["direction"] == [1.0, 0.0, 0.0]
    assert terminals[0]["standoff_floor"] == 0.0


def test_holes_without_exit_is_refused() -> None:
    with pytest.raises(TerminalError, match="exit"):
        selector_layout("holes", {"expected_count": 4}, order_by=(1, 0, 0), names=SIGNALS)


def test_more_than_one_name_needs_a_direction_to_order_along() -> None:
    with pytest.raises(TerminalError, match="order_by"):
        selector_layout(
            "holes", {"expected_count": 2}, exit=(0, 0, 1), names=["a", "b"]
        )
    # One name needs no ordering: there is nothing to order.
    selector_layout("holes", {"expected_count": 1}, exit=(0, 0, 1), names=["a"])


def test_an_exit_across_the_barrel_is_refused() -> None:
    with pytest.raises(TerminalError, match="across exit"):
        resolve_terminals(
            selector_layout(
                "holes", {"expected_count": 1}, exit=(1.0, 0.0, 0.0), names=["signal"]
            ),
            candidates=[_hole((0.0, 0.0, 0.0), axis=(0.0, 0.0, 1.0))],
        )


def test_a_names_count_mismatch_reports_both_counts_and_the_candidates() -> None:
    layout = selector_layout(
        "holes",
        {"geometry_type": "Cylinder", "expected_count": 3},
        exit=(0, 0, 1),
        order_by=(1, 0, 0),
        names=["a", "b", "c"],
    )
    with pytest.raises(TerminalError) as excinfo:
        resolve_terminals(layout, candidates=[_hole((0.0, 0.0, 0.0))])

    details = excinfo.value.details
    assert details["expected_count"] == 3
    assert details["actual_count"] == 1
    assert len(details["available"]) == 1
    assert details["selection"]["geometry_type"] == "Cylinder"


# --------------------------------------------------------------------------
# what the worker reads off a matched face


class _Vector:
    def __init__(self, x, y, z) -> None:
        self.x, self.y, self.z = float(x), float(y), float(z)


class _Cylinder:
    def __init__(self, center, axis, radius) -> None:
        self.Center = _Vector(*center)
        self.Axis = _Vector(*axis)
        self.Radius = float(radius)


class _Face:
    def __init__(self, *, surface=None, center=(0, 0, 0), area=1.0, parameters=(0, 1, 0, 1)):
        self.Surface = surface
        self.CenterOfMass = _Vector(*center)
        self.Area = float(area)
        self.ParameterRange = tuple(float(value) for value in parameters)


def test_the_worker_reads_a_barrels_axis_radius_and_extent() -> None:
    from cadex_part_worker import _terminal_candidates

    face = _Face(
        surface=_Cylinder((5.0, 6.0, 0.0), (0.0, 0.0, 1.0), 0.5),
        center=(5.0, 6.0, 0.8),
        parameters=(0.0, 2.0 * math.pi, 0.0, 1.6),
    )
    candidates = _terminal_candidates("terminals", "holes", "holes", [face], [{}])

    assert candidates[0]["radius"] == 0.5
    assert candidates[0]["extent"] == [0.0, 1.6]
    assert candidates[0]["axis"] == [0.0, 0.0, 1.0]
    # The barrel's midpoint on the axis, which is where a partial cylinder's
    # own centre of mass would not be.
    assert candidates[0]["sort_point"] == [5.0, 6.0, 0.8]


def test_a_non_cylindrical_face_matched_by_holes_is_refused() -> None:
    from cadex_part_worker import PartOperationError, _terminal_candidates

    with pytest.raises(PartOperationError, match="no barrel"):
        _terminal_candidates(
            "terminals", "holes", "holes", [_Face()], [{"geometry_type": "Plane"}]
        )


def test_the_worker_prefers_the_fingerprinted_normal_for_a_pad() -> None:
    from cadex_part_worker import _terminal_candidates

    face = _Face(center=(1.0, 2.0, 3.0), area=9.0)
    candidates = _terminal_candidates(
        "terminals", "pads", "pads", [face], [{"normal": [0.0, 0.0, 1.0]}]
    )

    assert candidates[0]["center"] == [1.0, 2.0, 3.0]
    assert candidates[0]["normal"] == [0.0, 0.0, 1.0]
    assert candidates[0]["area"] == 9.0


# --------------------------------------------------------------------------
# terminals ride their component's placement


def _translation(x, y, z):
    return (1.0, 0.0, 0.0, x, 0.0, 1.0, 0.0, y, 0.0, 0.0, 1.0, z, 0.0, 0.0, 0.0, 1.0)


def _rotation_z(degrees):
    angle = math.radians(degrees)
    cos, sin = math.cos(angle), math.sin(angle)
    return (
        cos, -sin, 0.0, 0.0,
        sin, cos, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    )


def _scale(x, y, z):
    return (x, 0.0, 0.0, 0.0, 0.0, y, 0.0, 0.0, 0.0, 0.0, z, 0.0, 0.0, 0.0, 0.0, 1.0)


def test_one_spec_placed_twice_lands_in_two_places() -> None:
    terminals = resolve_terminals(declared_layout(None, header=HEADER, names=SIGNALS))
    first = apply_placement(terminals, _translation(10.0, 0.0, 0.0))
    second = apply_placement(terminals, _translation(-10.0, 5.0, 2.0))

    assert [entry["point"][0] for entry in first] == [10.0] * 4
    assert second[0]["point"] == pytest.approx([-10.0, 5.0, 0.4])
    # A translation does not turn anything.
    assert all(entry["direction"] == [0.0, 0.0, 1.0] for entry in first + second)


def test_a_rotated_component_turns_its_terminals_points_and_directions() -> None:
    """The test a translation-only fixture would pass with the two swapped.

    Points transform by the whole matrix and directions by its rotation part
    only.  Under a pure translation both spellings give the same answer, which
    is the exact bug ADR-056's point-pin work hit; a rotation is what tells
    them apart.
    """

    header = {**HEADER, "count": 2, "axis": (1.0, 0.0, 0.0), "depth": 2.0}
    terminals = resolve_terminals(declared_layout(None, header=header, names=["a", "b"]))
    placed = apply_placement(terminals, _rotation_z(90.0))

    # (2, 0, 0) about +Z by 90 degrees is (0, 2, 0); the second station is
    # 2.54 mm further along +Y, which rotates onto -X.
    assert placed[0]["point"] == pytest.approx([0.0, 2.0, 0.0], abs=1.0e-9)
    assert placed[1]["point"] == pytest.approx([-2.54, 2.0, 0.0], abs=1.0e-9)
    # The row is drilled along +X, so the wire left along -X; rotated, -Y.
    assert placed[0]["direction"] == pytest.approx([0.0, -1.0, 0.0], abs=1.0e-9)


def test_a_placed_terminal_is_the_placed_geometry_it_names() -> None:
    header = {"origin": (1.0, 0.0, 0.0), "axis": (0.0, 0.0, -1.0), "depth": 1.0}
    terminals = resolve_terminals(declared_layout(None, header=header, names=["a"]))
    # Rotate first, then translate: the same composition mesh.transform does.
    rotate = _rotation_z(90.0)
    translate = _translation(5.0, 0.0, 0.0)
    composed = tuple(
        sum(translate[row * 4 + k] * rotate[k * 4 + column] for k in range(4))
        for row in range(4)
        for column in range(4)
    )
    placed = apply_placement(terminals, composed)

    assert placed[0]["point"] == pytest.approx([5.0, 1.0, -1.0], abs=1.0e-9)
    assert placed[0]["direction"] == pytest.approx([0.0, 0.0, 1.0], abs=1.0e-9)


def test_a_uniform_scale_carries_the_depth_the_radius_and_the_floor() -> None:
    terminals = resolve_terminals(declared_layout(None, header=HEADER, names=SIGNALS))
    placed = apply_placement(terminals, _scale(2.0, 2.0, 2.0))

    assert placed[0]["standoff_floor"] == pytest.approx(3.2)
    assert placed[0]["metrics"]["depth"] == pytest.approx(3.2)
    assert placed[0]["metrics"]["radius"] == pytest.approx(1.0)
    assert placed[1]["point"] == pytest.approx([0.0, 5.08, -3.2])


def test_a_non_uniform_scale_on_a_terminal_bearing_tree_is_refused() -> None:
    terminals = resolve_terminals(declared_layout(None, header=HEADER, names=SIGNALS))

    with pytest.raises(TerminalError, match="non-uniform"):
        apply_placement(terminals, _scale(2.0, 1.0, 1.0))
    with pytest.raises(TerminalError, match="collapses"):
        apply_placement(terminals, _scale(1.0, 1.0, 0.0))


def test_an_unplaced_component_composes_to_the_identity() -> None:
    terminals = resolve_terminals(declared_layout(None, header=HEADER, names=SIGNALS))

    assert apply_placement(terminals, identity_matrix()) == terminals


# --------------------------------------------------------------------------
# the router takes one stand-off per end


def test_route_path_honours_two_different_per_end_standoffs() -> None:
    points = route_path(
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (40.0, 0.0, 0.0),
        (-1.0, 0.0, 0.0),
        occupied=lambda _i, _j, _k: False,
        cell_mm=1.0,
        clearance_mm=0.0,
        start_standoff_mm=6.0,
        end_standoff_mm=1.0,
        slack=1.0,
        bounds=((-10.0, -20.0, -20.0), (50.0, 20.0, 20.0)),
        max_cells=200000,
    )

    # The run still terminates exactly on its two ports...
    assert points[0] == (0.0, 0.0, 0.0)
    assert points[-1] == (40.0, 0.0, 0.0)
    # ...and the two anchors are the two stated distances in, not one. Each
    # stub arrives as its own collinear knots (ADR-114), so the anchors are
    # that many waypoints in from either end rather than one.
    import CadexRouting

    stub = CadexRouting._STUB_SEGMENTS
    assert points[stub][0] == pytest.approx(6.0)
    assert points[-(stub + 1)][0] == pytest.approx(39.0)
    # The stand-offs differ, so the knots are spaced differently at each end.
    assert points[1][0] == pytest.approx(6.0 / stub)
    assert points[-2][0] == pytest.approx(40.0 - 1.0 / stub)


def test_the_standoff_floor_lifts_the_anchor_clear_of_a_board() -> None:
    from cadex_part_worker import _end_standoff

    # A pad keeps exactly what ADR-056 computed, so nothing that routed
    # before routes differently.
    assert _end_standoff(1.4, 0.0, 1.0) == 1.4
    # A hole through a 1.6 mm board needs the anchor past the far face, or
    # the search starts inside the board it just threaded.
    assert _end_standoff(1.4, 1.6, 1.0) == pytest.approx(2.6)


# --------------------------------------------------------------------------
# the api surface


def test_terminals_is_declared_by_both_packs_and_both_runtimes() -> None:
    assert "terminals" in PART_PACK.api_exports
    assert "terminals" in MESH_PACK.api_exports
    assert "terminals" in _part().exported_names
    assert "terminals" in _mesh().exported_names


def test_a_terminal_is_never_a_declarable_output() -> None:
    """The central simplification: a terminal is not geometry.

    ``PROJECT_PACK.output_types`` is the union of every pack's, so a terminal
    type declared in either pack would make it a declarable project output —
    something to be built, published, digested and hydrated as a tree row,
    none of which a terminal is.
    """

    from CadexScriptedDomains import PROJECT_PACK

    assert "terminal" not in PROJECT_PACK.output_types
    assert "terminals" not in PROJECT_PACK.output_types
    assert PART_PACK.output_types == ("solid", "shell", "face", "wire", "compound")
    assert MESH_PACK.output_types == ("mesh",)

    terminals = _part().terminals(_board(), header=HEADER, names=SIGNALS)
    assert not isinstance(terminals, DomainValue)
    assert not isinstance(terminals["vcc"], DomainValue)


def test_a_terminal_set_is_looked_up_by_name_not_by_number() -> None:
    terminals = _part().terminals(_board(), header=HEADER, names=SIGNALS)

    assert terminals.names == tuple(SIGNALS)
    assert len(terminals) == 4
    assert [entry.name for entry in terminals] == SIGNALS
    assert "sda" in terminals
    assert isinstance(terminals["sda"], Terminal)

    with pytest.raises(TerminalError) as unknown:
        terminals["sdo"]
    assert "'sdo'" in str(unknown.value)
    assert unknown.value.details["available"] == SIGNALS

    with pytest.raises(TerminalError, match="named, not numbered"):
        terminals[0]


def test_a_terminal_carries_its_component_and_layout_into_a_port() -> None:
    board = _board()
    terminals = _part().terminals(board, header=HEADER, names=SIGNALS)
    port = terminals["sda"].to_port()

    assert port["terminal"] == "sda"
    assert port["component"] is board
    assert port["layout"]["kind"] == "declared"
    assert port["layout"]["names"] == SIGNALS
    assert port["layout"]["terminals"][0]["pitch"] == 2.54


def test_a_selector_terminal_takes_its_cardinality_from_its_names() -> None:
    terminals = _part().terminals(
        _board(),
        holes={"geometry_type": "Cylinder", "radius": 0.5},
        exit=(0, 0, 1),
        order_by=(1, 0, 0),
        names=SIGNALS,
    )
    layout = terminals["vcc"].to_port()["layout"]

    assert layout["kind"] == "holes"
    # len(names) *is* expected_count, so a selector that starts matching a
    # different number of faces fails loudly instead of naming the wrong ones.
    assert layout["selector"]["expected_count"] == 4
    assert layout["exit"] == [0.0, 0.0, 1.0]
    assert layout["order_by"] == [1.0, 0.0, 0.0]

    with pytest.raises(ValueError, match="expected_count"):
        _part().terminals(
            _board(),
            holes={"geometry_type": "Cylinder", "expected_count": 8},
            exit=(0, 0, 1),
            order_by=(1, 0, 0),
            names=SIGNALS,
        )


def test_part_terminals_validates_its_form() -> None:
    part_api = _part()
    board = _board()

    with pytest.raises(ValueError, match="exactly one of"):
        part_api.terminals(board, names=SIGNALS)
    with pytest.raises(ValueError, match="exactly one of"):
        part_api.terminals(
            board, header=HEADER, pads={"expected_count": 4}, names=SIGNALS
        )
    with pytest.raises(ValueError, match="component"):
        part_api.terminals(_module(), header=HEADER, names=SIGNALS)
    with pytest.raises(ValueError, match="exit"):
        part_api.terminals(
            board, holes={"geometry_type": "Cylinder"}, order_by=(1, 0, 0), names=SIGNALS
        )
    with pytest.raises(ValueError, match="exit= and order_by="):
        part_api.terminals(board, header=HEADER, exit=(0, 0, 1), names=SIGNALS)
    with pytest.raises(ValueError, match="names"):
        part_api.terminals(board, holes={"geometry_type": "Cylinder"}, exit=(0, 0, 1), names=[])
    with pytest.raises(ValueError, match="selector"):
        part_api.terminals(
            board, holes=[1, 2, 3, 4], exit=(0, 0, 1), order_by=(1, 0, 0), names=SIGNALS
        )


def test_mesh_terminals_is_declared_only_and_rides_a_placed_asset() -> None:
    mesh_api = _mesh()
    placed = mesh_api.transform(_module(), translation=(10.0, 0.0, 0.0))
    terminals = mesh_api.terminals(placed, header=HEADER, names=SIGNALS)

    assert terminals["gnd"].to_port()["component"] is placed
    # A boolean of two placed meshes has two frames and no leaf, so a layout
    # stated against it means nothing.
    with pytest.raises(ValueError, match="single asset frame"):
        mesh_api.terminals(
            mesh_api.union(_module(), placed), header=HEADER, names=SIGNALS
        )
    with pytest.raises(ValueError, match="component"):
        mesh_api.terminals(_board(), header=HEADER, names=SIGNALS)
    with pytest.raises(TypeError):
        mesh_api.terminals(placed, holes={"expected_count": 4}, names=SIGNALS)


# --------------------------------------------------------------------------
# terminals and literals are interchangeable at either end


def test_cable_takes_a_terminal_and_a_literal_interchangeably() -> None:
    part_api = _part()
    board = _board()
    fc = part_api.terminals(board, header=HEADER, names=SIGNALS)
    literal = ((30.0, 12.0, 9.0), (0.0, 0.0, 1.0))

    value = part_api.cable(fc["sda"], literal, gauge_mm=0.4)
    payload = value.to_payload()

    assert value.output_type == "solid"
    start, end = payload["arguments"]
    assert start["terminal"] == "sda"
    # The component's payload is nested in the port, as plain JSON: nothing in
    # cadex_domain_api needed a special case for it.
    assert start["component"]["operation"] == "box"
    assert start["layout"]["kind"] == "declared"
    assert end == [[30.0, 12.0, 9.0], [0.0, 0.0, 1.0]]

    # ...and the other way round.
    flipped = part_api.cable(literal, fc["scl"], gauge_mm=0.4).to_payload()
    assert flipped["arguments"][0] == [[30.0, 12.0, 9.0], [0.0, 0.0, 1.0]]
    assert flipped["arguments"][1]["terminal"] == "scl"


def test_bundle_takes_terminals_and_literals_in_one_lay() -> None:
    part_api = _part()
    fc = part_api.terminals(_board(), header=HEADER, names=SIGNALS)
    connections = [
        (fc["sda"], ((30.0, 0.0, 9.0), (0.0, 0.0, 1.0))),
        (((0.0, 2.54, -1.6), (0.0, 0.0, 1.0)), fc["scl"]),
    ]
    payload = part_api.bundle(
        connections, gauge_mm=0.4, conductor=0, style="flat"
    ).to_payload()

    first, second = payload["arguments"][0]
    assert first[0]["terminal"] == "sda"
    assert first[1] == [[30.0, 0.0, 9.0], [0.0, 0.0, 1.0]]
    assert second[0] == [[0.0, 2.54, -1.6], [0.0, 0.0, 1.0]]
    assert second[1]["terminal"] == "scl"


def test_a_whole_terminal_set_is_not_a_port() -> None:
    part_api = _part()
    fc = part_api.terminals(_board(), header=HEADER, names=SIGNALS)

    with pytest.raises(ValueError, match="subscript it by name"):
        part_api.cable(fc, ((30.0, 0.0, 9.0), (0, 0, 1)), gauge_mm=0.4)


def test_two_literal_ports_at_one_point_are_still_refused() -> None:
    with pytest.raises(ValueError, match="different points"):
        _part().cable(
            ((1.0, 2.0, 3.0), (1.0, 0.0, 0.0)),
            ((1.0, 2.0, 3.0), (-1.0, 0.0, 0.0)),
            gauge_mm=0.8,
        )


def test_a_terminal_set_in_result_is_not_an_output() -> None:
    """Putting one in ``result`` fails as an unsupported value, not a null shape.

    Nothing had to be added for this: a terminal is not a ``DomainValue``, so
    the existing result-grouping path refuses it by the same rule that refuses
    a plain dict.
    """

    from cadex_domain_worker import _payload

    terminals = _part().terminals(_board(), header=HEADER, names=SIGNALS)
    with pytest.raises(TypeError, match="active domain api"):
        _payload(terminals)
    with pytest.raises(TypeError, match="active domain api"):
        _payload(terminals["vcc"])


def test_the_terminals_docstring_says_where_the_coordinates_are() -> None:
    part_text = _part().terminals.__doc__ or ""
    mesh_text = _mesh().terminals.__doc__ or ""

    assert "far" in part_text and "exit" in part_text
    assert "recommended" in part_text
    assert "asset's own" in mesh_text


# --------------------------------------------------------------------------
# the whole path, against a real kernel
# --------------------------------------------------------------------------


#: Run inside ``FreeCADCmd``: resolve terminals off a real drilled plate and
#: route between them.  What cannot be checked headless is exactly the half
#: that matters most — that the selector reaches real ``Cylinder`` faces,
#: that their parameter range is the bore's depth, and that a wire built
#: between two hole terminals lands in true centres.
_PROBE = r"""
import json, sys
sys.path.insert(0, %(root)r)
import cadex_part_worker as worker

PLATE = {
    "domain": "part", "operation": "cut", "output_type": "solid",
    "arguments": [
        {"domain": "part", "operation": "box", "output_type": "solid",
         "arguments": [40.0, 20.0, 1.6], "properties": {}},
        [
            {"domain": "part", "operation": "cylinder", "output_type": "solid",
             "arguments": [0.5, 6.0],
             "properties": {"origin": [x, 10.0, -2.0]}}
            for x in (5.0, 15.0, 25.0, 35.0)
        ],
    ],
    "properties": {"refine": False},
}

LAYOUT = {
    "kind": "holes",
    "selector": {"geometry_type": "Cylinder", "radius": 0.5, "expected_count": 4},
    "exit": [0.0, 0.0, 1.0],
    "order_by": [1.0, 0.0, 0.0],
    "names": ["vbat", "gnd", "sda", "scl"],
}


def terminal(name, layout=LAYOUT, component=PLATE):
    return {"terminal": name, "component": component, "layout": layout}


def cable(start, end, **properties):
    base = {"gauge_mm": 0.6, "clearance_mm": 0.5, "slack": 1.02, "avoid": []}
    base.update(properties)
    return {
        "domain": "part", "operation": "cable", "output_type": "solid",
        "arguments": [start, end], "properties": base,
    }


report = {}
try:
    worker.reset_part_shape_memo()
    resolved = worker._resolve_terminal_set("terminals", "start", terminal("sda"))
    report["names"] = sorted(resolved)
    report["points"] = [resolved[n]["point"] for n in LAYOUT["names"]]
    report["floors"] = [resolved[n]["standoff_floor"] for n in LAYOUT["names"]]
    report["radii"] = [resolved[n]["metrics"]["radius"] for n in LAYOUT["names"]]
    report["directions"] = [resolved[n]["direction"] for n in LAYOUT["names"]]
    # The same board named four times resolves -- and builds -- once.
    before = len(worker._SHAPE_MEMO)
    for name in LAYOUT["names"]:
        worker._resolve_terminal_set("terminals", "start", terminal(name))
    report["memo_entries"] = len(worker._TERMINAL_SETS)
    report["shape_entries_added"] = len(worker._SHAPE_MEMO) - before

    wire = worker.build_part_shape(
        cable(terminal("vbat"), terminal("scl"), cell_mm=1.0)
    )
    report["wire_valid"] = bool(wire.isValid())
    report["wire_solids"] = len(wire.Solids)
    box = wire.BoundBox
    report["wire_bounds"] = [
        float(box.XMin), float(box.YMin), float(box.ZMin),
        float(box.XMax), float(box.YMax), float(box.ZMax),
    ]

    mixed = worker.build_part_shape(
        cable(terminal("gnd"), [[25.0, 10.0, 12.0], [0.0, 0.0, 1.0]], cell_mm=1.0)
    )
    report["mixed_valid"] = bool(mixed.isValid())

    try:
        worker._resolve_port("cable", "start", terminal("miso"))
    except Exception as exc:
        report["unknown_name"] = "%%s" %% (exc,)
    # A mesh component: one datasheet header, stated in the asset's own
    # frame, riding a rotation and a translation it knows nothing about.
    import CadexTerminals
    import cadex_mesh_worker as meshes

    MOTOR = {
        "domain": "mesh", "operation": "transform", "output_type": "mesh",
        "arguments": [{
            "domain": "mesh", "operation": "import_file", "output_type": "mesh",
            "arguments": ["motor.stl"], "properties": {},
        }],
        "properties": {
            "translation": [10.0, 0.0, 0.0], "rotation_axis": [0.0, 0.0, 1.0],
            "rotation_degrees": 90.0, "scale": [1.0, 1.0, 1.0],
            "pivot": [0.0, 0.0, 0.0],
        },
    }
    MOTOR_LAYOUT = {
        "kind": "declared",
        "terminals": [{
            "origin": [0.0, 0.0, 4.2], "along": [0.0, 1.0, 0.0],
            "axis": [0.0, 0.0, 1.0], "pitch": 1.2, "count": 3,
            "depth": 0.8, "hole_dia": 0.6,
        }],
        "names": ["a", "b", "c"],
    }
    worker.configure_part_assets(None, None, meshes.composed_placement)
    worker.reset_part_shape_memo()
    placed = worker._resolve_terminal_set(
        "terminals", "start", terminal("a", MOTOR_LAYOUT, MOTOR)
    )
    report["motor_points"] = [placed[n]["point"] for n in ("a", "b", "c")]
    report["motor_directions"] = [placed[n]["direction"] for n in ("a", "b", "c")]
    report["motor_floor"] = placed["a"]["standoff_floor"]

    across = worker.build_part_shape(
        cable(terminal("a", MOTOR_LAYOUT, MOTOR), terminal("sda"), cell_mm=1.0)
    )
    report["across_valid"] = bool(across.isValid())
    report["across_solids"] = len(across.Solids)

    bad = dict(LAYOUT, names=["a", "b", "c"], selector=dict(LAYOUT["selector"], expected_count=3))
    try:
        worker.reset_part_shape_memo()
        worker._resolve_terminal_set("terminals", "start", terminal("a", bad))
    except Exception as exc:
        report["count_mismatch"] = "%%s" %% (exc,)
        report["count_observed"] = getattr(exc, "details", {}).get("observed", {})
except Exception as exc:
    import traceback
    report["crashed"] = traceback.format_exc()
open(%(out)r, "w").write(json.dumps(report))
"""


def _kernel_report():
    from test_cadexd_lifecycle import CADEX_ROOT, FREECADCMD

    scratch = pathlib.Path(tempfile.mkdtemp(prefix="cadex-terminal-probe-"))
    out = scratch / "report.json"
    probe = scratch / "probe.py"
    probe.write_text(_PROBE % {"root": str(CADEX_ROOT), "out": str(out)})
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
    reason="No FreeCADCmd binary available to resolve a terminal against OCC.",
)
def test_terminals_resolve_against_a_real_drilled_plate() -> None:
    report = _kernel_report()

    assert "crashed" not in report, report.get("crashed")
    assert report["names"] == ["gnd", "scl", "sda", "vbat"]
    # Four 1 mm bores through a 1.6 mm plate at x = 5, 15, 25, 35.  The wire
    # leaves along +Z, so it threads down the barrel and lands flush on the
    # bottom face, floored at the plate's own thickness.
    assert [round(point[0], 6) for point in report["points"]] == [5.0, 15.0, 25.0, 35.0]
    assert all(point[2] == pytest.approx(0.0, abs=1.0e-9) for point in report["points"])
    assert all(point[1] == pytest.approx(10.0) for point in report["points"])
    assert all(floor == pytest.approx(1.6) for floor in report["floors"])
    assert all(radius == pytest.approx(0.5) for radius in report["radii"])
    assert all(
        direction == pytest.approx([0.0, 0.0, 1.0]) for direction in report["directions"]
    )

    # One board, named four times: one resolved set, and no second build.
    assert report["memo_entries"] == 1
    assert report["shape_entries_added"] == 0

    # A wire between two hole terminals is one solid that spans the two bores
    # and reaches the bottom face they both land on, a whole plate below the
    # face a literal port would have been measured on.
    assert report["wire_valid"] is True
    assert report["wire_solids"] == 1
    assert report["wire_bounds"][0] == pytest.approx(5.0, abs=1.5)
    assert report["wire_bounds"][3] == pytest.approx(35.0, abs=1.5)
    assert report["wire_bounds"][2] < 0.35
    assert report["wire_bounds"][5] > 1.6
    assert report["mixed_valid"] is True

    assert "miso" in report["unknown_name"]
    assert "vbat" in report["unknown_name"]
    assert "expected_count" in json.dumps(report["count_observed"])


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available to compose a mesh placement.",
)
def test_a_mesh_components_terminals_ride_its_placement() -> None:
    """One header off a datasheet, under a rotation the spec knows nothing of.

    The third ``configure_part_assets`` binding end to end: the part worker
    reaches ``cadex_mesh_worker.composed_placement`` through a callable rather
    than an import, and the asset itself is never materialized — placing a
    terminal needs where the component *is*, not its triangles.
    """

    report = _kernel_report()

    assert "crashed" not in report, report.get("crashed")
    # (0, 0, 4.2) drilled 0.8 mm along +Z lands at (0, 0, 5.0) in the asset's
    # own frame; rotated 90 degrees about +Z and moved to x = 10, the row
    # runs back along -X from there.
    assert report["motor_points"][0] == pytest.approx([10.0, 0.0, 5.0], abs=1.0e-9)
    assert report["motor_points"][1] == pytest.approx([8.8, 0.0, 5.0], abs=1.0e-9)
    assert report["motor_points"][2] == pytest.approx([7.6, 0.0, 5.0], abs=1.0e-9)
    # Drilled along +Z, so the wire leaves along -Z; a rotation about Z does
    # not touch that.
    assert all(
        direction == pytest.approx([0.0, 0.0, -1.0], abs=1.0e-9)
        for direction in report["motor_directions"]
    )
    assert report["motor_floor"] == pytest.approx(0.8)

    # ...and a wire runs from that mesh terminal to a hole in the board.
    assert report["across_valid"] is True
    assert report["across_solids"] == 1
