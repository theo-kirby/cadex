# SPDX-License-Identifier: LGPL-2.1-or-later

"""Solder: the joint a terminal implies (ADR-063, ADR-064).

ADR-062 landed terminals and carried a ``metrics`` payload — a hole's axis,
bore radius, depth and its two face points; a pad's centre, normal and area —
through ``_resolve_port`` deliberately unused.  ``part.solder`` is its
consumer, and the first operation a terminal *unlocks* rather than merely
improves: a literal port carries no radius, no depth and no face, so there is
nothing to build a joint from.

ADR-064 replaced the fused primitives with one closed outline revolved about
the terminal's axis, so the meniscus is a concave arc rather than a straight
cone.  That moves the risk out of OCC and into pure Python: **that the loop
is closed, simple and correctly wound is decided here**, headless, over a
parameter sweep, rather than probed in a subprocess.  ``CadexSolder`` imports
nothing from FreeCAD, so every derivation and every refusal is exercised
against plain numbers, exactly as ``CadexRouting``, ``CadexBundle`` and
``CadexTerminals`` are.  The kernel half — that the outline revolves into
*one* closed solid, that its volume is the contour integral, that a slab
through it is the ring the arc implies, and how much material the joint shares
with the wire that lands in it — is at the bottom, behind the same
``FreeCADCmd`` skip ``test_terminals.py`` uses.
"""

from __future__ import annotations

import inspect
import json
import math
import pathlib
import subprocess
import tempfile

import pytest

import CadexRouting
import CadexSolder
from CadexSolder import SolderError, joint_volume, solder_specs
from CadexTerminals import apply_placement, declared_layout, resolve_terminals
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import create_domain_api


PART_PACK = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]


def _part():
    return create_domain_api(PART_PACK.domain, PART_PACK.api_exports, PART_PACK.output_types)


def _board():
    return _part().box(40.0, 20.0, 1.6, label="board")


#: A 1 mm bore through a 1.6 mm board at (5, 10), with the wire leaving
#: upward: it threads down the barrel and ends flush on the bottom face, so
#: the entry face is the top and the exit face is the bottom.  Exactly what
#: ``CadexTerminals._hole_terminal`` resolves for ``exit=(0, 0, 1)``.
HOLE = {
    "kind": "hole",
    "axis": [0.0, 0.0, 1.0],
    "radius": 0.5,
    "depth": 1.6,
    "entry_point": [5.0, 10.0, 1.6],
    "exit_point": [5.0, 10.0, 0.0],
}

#: A pad of area pi, so its equivalent-area radius is exactly 1.
PAD = {
    "kind": "pad",
    "axis": [0.0, 0.0, 1.0],
    "radius": None,
    "depth": 0.0,
    "area": math.pi,
    "entry_point": [5.0, 10.0, 1.6],
    "exit_point": [5.0, 10.0, 1.6],
}

#: What the fixtures derive, written down once: a 0.4 mm lead in a 1.0 mm bore
#: rings a 2.0 mm pad, so the collar stands a quarter of the lead's radius
#: clear of it and the quarter-round meniscus spans the rest.
LEAD, BORE, PAD_R = 0.2, 0.5, 1.0
COLLAR = 0.25
SPAN = PAD_R - COLLAR  # 0.75: the default fillet, and its floor
#: The crown's radius is the collar's stand-off, so it needs no constant of
#: its own -- but it is what the joint's top now rounds over on (ADR-114).
CROWN = COLLAR - LEAD


def _roles(specs):
    return [segment["role"] for segment in specs["profile"]]


def _segment(specs, role):
    for segment in specs["profile"]:
        if segment["role"] == role:
            return segment
    raise AssertionError(f"no {role!r} among {_roles(specs)}")


def _points(segment, samples=1):
    """A segment as a polyline, arcs chorded through the circle they name."""

    if segment["kind"] != "arc":
        return [tuple(segment["start"]), tuple(segment["end"])]
    centre_r, centre_z = segment["centre"]
    radius = segment["radius"]
    start, end = segment["start_angle"], segment["end_angle"]
    chords = [
        (
            centre_r + radius * math.cos(start + (end - start) * index / samples),
            centre_z + radius * math.sin(start + (end - start) * index / samples),
        )
        for index in range(1, samples)
    ]
    return [tuple(segment["start"]), *chords, tuple(segment["end"])]


def _polyline(specs, samples=64):
    """The whole outline as one closed polyline, without repeating vertices."""

    result = []
    for segment in specs["profile"]:
        result.extend(_points(segment, samples)[:-1])
    return result


def _signed_area(points):
    return 0.5 * sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    )


def _circumcentre(first, second, third):
    """The circle through three points, fitted from the points alone.

    Deliberately independent of the centre the module emits: this is what the
    kernel reconstructs from the three-point ``Part.Arc``, so it is what the
    tangency assertions should be made against.
    """

    (x1, y1), (x2, y2), (x3, y3) = first, second, third
    d = 2.0 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    assert abs(d) > 1.0e-9, "the three arc points are collinear"
    s1, s2, s3 = x1 * x1 + y1 * y1, x2 * x2 + y2 * y2, x3 * x3 + y3 * y3
    return (
        (s1 * (y2 - y3) + s2 * (y3 - y1) + s3 * (y1 - y2)) / d,
        (s1 * (x3 - x2) + s2 * (x1 - x3) + s3 * (x2 - x1)) / d,
    )


# --------------------------------------------------------------------------
# the through-hole outline


def test_a_hole_joint_is_one_closed_loop_from_the_cap_to_the_collar() -> None:
    specs = solder_specs(HOLE, gauge_mm=0.4)

    assert specs["kind"] == "hole"
    assert _roles(specs) == [
        "cap",
        "cap_rim",
        "bore",
        "entry_annulus",
        "meniscus",
        "collar",
        "crown",
        "lead",
        "lead_end",
        "spine",
    ]
    # Two arcs and eight lines: there is no fuse and no cut left to get wrong.
    # The second arc is the crown, which replaced the flat annulus the collar
    # used to cross to the lead along (ADR-114).
    assert [segment["kind"] for segment in specs["profile"]].count("arc") == 2
    # Consecutive segments share bit-identical endpoints, so Part.Wire orders
    # the edges rather than sewing them, and isClosed() is exact.
    for index, segment in enumerate(specs["profile"]):
        following = specs["profile"][(index + 1) % len(specs["profile"])]
        assert segment["end"] == following["start"], segment["role"]


def test_the_outline_stands_on_the_far_face_and_reaches_the_entry_face() -> None:
    """The assertion that catches an axis-sign flip.

    ``axis`` points *out of* the board on the side the lead leaves, and the
    outline's ``z`` is measured from the far face towards it.  Swap the two
    faces, or negate the axis, and the barrel is built through open air below
    the board while everything else still looks plausible.
    """

    specs = solder_specs(HOLE, gauge_mm=0.4)

    assert specs["origin"] == HOLE["exit_point"]
    assert specs["direction"] == HOLE["axis"]
    # The bore wall runs the plating's whole depth, from the far face up.
    assert _segment(specs, "bore")["start"] == [BORE, 0.0]
    assert _segment(specs, "bore")["end"] == [BORE, 1.6]
    # ...and z = depth arrives exactly at the entry face, not short of it.
    assert [
        specs["origin"][k] + specs["direction"][k] * specs["depth"] for k in range(3)
    ] == pytest.approx(HOLE["entry_point"])
    # The cap hangs below the far face and nothing else does.
    assert min(point[1] for point in _polyline(specs)) == pytest.approx(
        -specs["cap_height"]
    )


def test_the_radial_basis_is_a_stated_function_of_the_axis() -> None:
    """A revolve is rotationally symmetric, so this does not change the shape.

    It changes where the BREP's seam edge lands, and the exported BREP is what
    ``compute_project_digest`` hashes — so it has to be derived from the axis
    by a stated rule rather than left to the kernel.  The rule is the one
    ``CadexTerminals._order_frame`` already uses: the world axis with the
    smallest component, ties to the lowest index.
    """

    specs = solder_specs(HOLE, gauge_mm=0.4)
    radial, axis = specs["radial"], specs["direction"]

    assert sum(radial[k] * axis[k] for k in range(3)) == pytest.approx(0.0, abs=1e-15)
    assert math.sqrt(sum(item * item for item in radial)) == pytest.approx(1.0)
    # z is the least-aligned world axis with the smallest index, so +z picks x.
    assert radial == [1.0, 0.0, 0.0]
    sideways = solder_specs({**HOLE, "axis": [1.0, 0.0, 0.0]}, gauge_mm=0.4)
    assert sideways["radial"] == [0.0, 1.0, 0.0]
    # A tie between two equally-aligned world axes breaks by index, so it does
    # not depend on which one the kernel enumerated first.
    diagonal = solder_specs(
        {**HOLE, "axis": [0.0, math.sqrt(0.5), math.sqrt(0.5)]}, gauge_mm=0.4
    )
    assert diagonal["radial"] == [1.0, 0.0, 0.0]


# --------------------------------------------------------------------------
# the meniscus: concave, and tangent at both ends


def test_the_meniscus_is_an_arc_tangent_to_the_board_and_to_the_lead() -> None:
    """The one assertion that says "not a cone".

    Fitted from the three points the kernel is handed, and differentiated
    numerically at each end, so nothing here reads back the centre the module
    computed.  At the rim the tangent is flat — the solder leaves the board
    without a lip — and at the collar it is vertical, so the surface arrives
    parallel to the wire it is about to run alongside.
    """

    specs = solder_specs(HOLE, gauge_mm=0.4)
    arc = _segment(specs, "meniscus")
    centre = _circumcentre(arc["start"], arc["through"], arc["end"])

    def tangent(point):
        radius = math.hypot(point[0] - centre[0], point[1] - centre[1])
        angle = math.atan2(point[1] - centre[1], point[0] - centre[0])
        step = 1.0e-7
        ahead = (
            centre[0] + radius * math.cos(angle + step),
            centre[1] + radius * math.sin(angle + step),
        )
        behind = (
            centre[0] + radius * math.cos(angle - step),
            centre[1] + radius * math.sin(angle - step),
        )
        length = math.hypot(ahead[0] - behind[0], ahead[1] - behind[1])
        return (
            (ahead[0] - behind[0]) / length,
            (ahead[1] - behind[1]) / length,
        )

    assert arc["start"] == pytest.approx([PAD_R, 1.6])
    assert abs(tangent(arc["start"])[1]) == pytest.approx(0.0, abs=1.0e-6)
    assert arc["end"] == pytest.approx([COLLAR, 1.6 + SPAN])
    assert abs(tangent(arc["end"])[0]) == pytest.approx(0.0, abs=1.0e-6)
    # Tangency to the lead survives a taller fillet; tangency to the board is
    # the quarter-round default's own property and does not.
    taller = _segment(solder_specs(HOLE, gauge_mm=0.4, fillet_mm=2.0), "meniscus")
    tall_centre = _circumcentre(taller["start"], taller["through"], taller["end"])
    assert tall_centre[1] == pytest.approx(taller["end"][1])


def test_the_default_fillet_is_an_exact_quarter_circle() -> None:
    """Tangent to the board *and* to the lead: the softest fillet that exists.

    ``H == d`` makes ``R = (d**2 + H**2) / 2d`` collapse to ``d`` and the swept
    angle to a right angle, which is why the default sits exactly on the
    undercut floor rather than a hair above it.
    """

    specs = solder_specs(HOLE, gauge_mm=0.4)
    arc = _segment(specs, "meniscus")

    assert specs["fillet_height"] == pytest.approx(SPAN)
    assert specs["arc_radius"] == pytest.approx(SPAN)
    assert arc["start_angle"] - arc["end_angle"] == pytest.approx(math.pi / 2.0)
    fitted = _circumcentre(arc["start"], arc["through"], arc["end"])
    assert fitted == pytest.approx((COLLAR + SPAN, 1.6 + SPAN))


@pytest.mark.parametrize("gauge", (0.1, 0.25, 0.4, 0.6, 0.9))
@pytest.mark.parametrize("pad_dia", (1.0, 1.4, 2.0, 5.0))
@pytest.mark.parametrize("bore_dia", (1.0, 1.6))
def test_the_default_fillet_never_trips_the_undercut_floor(
    gauge: float, pad_dia: float, bore_dia: float
) -> None:
    """The floor is reachable only by an explicit override.

    The default is computed by the same expression as the floor, so it passes
    by equality — but "the same expression" is exactly the kind of claim that
    stops being true after an edit, so it is swept rather than reasoned about.
    """

    try:
        specs = solder_specs(
            HOLE, gauge_mm=gauge, pad_dia_mm=pad_dia, bore_dia_mm=bore_dia
        )
    except SolderError as exc:
        # Whatever refused, it was not the fillet: the default cannot undercut.
        assert exc.reason != "fillet", exc
        return
    assert specs["fillet_height"] == pytest.approx(
        specs["pad_radius"] - specs["collar_radius"]
    )
    assert specs["arc_radius"] == pytest.approx(specs["fillet_height"])


def test_the_arc_climbs_without_dipping_below_the_face_or_passing_the_pad() -> None:
    """Concave, monotonic and inside the footprint it was given, everywhere."""

    for specs in (
        solder_specs(HOLE, gauge_mm=0.4),
        solder_specs(HOLE, gauge_mm=0.4, fillet_mm=3.0),
        solder_specs(PAD, gauge_mm=0.4, pad_dia_mm=5.0),
    ):
        arc = _segment(specs, "meniscus")
        face_z = specs["depth"]
        samples = _points(arc, 200)
        for radius, height in samples:
            assert height >= face_z - 1.0e-12
            assert height <= face_z + specs["fillet_height"] + 1.0e-12
            assert specs["collar_radius"] - 1.0e-12 <= radius <= specs["pad_radius"] + 1.0e-12
        # It sweeps inward and upward the whole way, so no sample retraces.
        assert all(
            later[0] < earlier[0] and later[1] > earlier[1]
            for earlier, later in zip(samples, samples[1:])
        )
        # Concave, stated as the one thing a cone is not: the arc runs
        # *inside* the straight chord between its own two endpoints, so a joint
        # is hollowed out relative to the ruled meniscus it replaced.
        first, last = samples[0], samples[-1]
        for radius, height in samples[1:-1]:
            chord_z = first[1] + (last[1] - first[1]) * (radius - first[0]) / (
                last[0] - first[0]
            )
            assert height < chord_z


def test_the_collar_hugs_the_lead_and_is_half_the_fillet_tall() -> None:
    specs = solder_specs(HOLE, gauge_mm=0.4)

    # A quarter of the lead's radius clear of it: subtle, never a knife edge
    # the way a cone tapering to exactly the lead radius is, and wide enough
    # that the crown rounding over it is solder rather than a bright ring.
    assert specs["collar_radius"] == pytest.approx(1.25 * specs["lead_radius"])
    assert specs["collar_radius"] == pytest.approx(COLLAR)
    assert specs["collar_height"] == pytest.approx(0.5 * specs["fillet_height"])
    collar = _segment(specs, "collar")
    assert collar["start"] == pytest.approx([COLLAR, 1.6 + SPAN])
    assert collar["end"] == pytest.approx([COLLAR, 1.6 + SPAN + 0.5 * SPAN])
    # On a pad too tight for a tenth of the lead, a quarter of the annulus is
    # taken instead, so the collar is always strictly between lead and pad.
    tight = solder_specs(PAD, gauge_mm=0.6, pad_dia_mm=0.7)
    assert tight["collar_radius"] == pytest.approx(0.3125)
    assert tight["lead_radius"] < tight["collar_radius"] < tight["pad_radius"]


def test_the_crown_rounds_the_collar_onto_the_lead_with_no_flat_ring() -> None:
    """The joint closes onto the wire instead of stopping across it (ADR-114).

    The collar used to cross to the lead along a flat annulus — a washer of
    solder presenting a hard bright ring to every render, and a square edge
    for a wire leaving at any angle to poke through. Nothing in the outline
    may run horizontally between the collar and the lead any more.
    """

    for metrics, gauge in ((HOLE, 0.4), (PAD, 0.6)):
        specs = solder_specs(metrics, gauge_mm=gauge)
        crown = _segment(specs, "crown")
        lead, collar = specs["lead_radius"], specs["collar_radius"]

        assert crown["kind"] == "arc"
        assert specs["crown_height"] == pytest.approx(collar - lead)
        # It leaves the collar's wall where the collar ends...
        collar_end = _segment(specs, "collar")["end"]
        assert crown["start"] == pytest.approx(collar_end)
        # ...and lands on the lead, a crown's height higher.
        assert crown["end"] == pytest.approx([lead, collar_end[1] + (collar - lead)])
        # Tangent to that wall where it leaves it: the centre is level with
        # the start, which is what makes the surface flow rather than crease.
        assert crown["centre"] == pytest.approx([lead, collar_end[1]])
        assert crown["radius"] == pytest.approx(collar - lead)

        # No horizontal run anywhere above the board: the ring is gone.
        face_z = specs["depth"]
        for segment in specs["profile"]:
            if segment["kind"] != "line":
                continue
            start, end = segment["start"], segment["end"]
            if min(start[1], end[1]) < face_z + 1.0e-12:
                continue
            assert start[1] != end[1], segment["role"]


def test_the_crown_bulges_outward_over_the_whole_quarter() -> None:
    """Convex, and outside the lead the whole way: it cannot pinch the wire."""

    specs = solder_specs(HOLE, gauge_mm=0.4)
    crown = _segment(specs, "crown")
    lead = specs["lead_radius"]

    for point in _points(crown, samples=32):
        assert point[0] >= lead - 1.0e-12
        assert point[1] >= crown["start"][1] - 1.0e-12
    # The bulge is on the outside of the chord, which is what convex means
    # here: the mid-arc point sits further from the axis than the chord does.
    chord_r = 0.5 * (crown["start"][0] + crown["end"][0])
    assert crown["through"][0] > chord_r


def test_the_lead_run_is_the_meniscus_and_the_collar_together() -> None:
    """What ``part.cable`` has to leave straight for a joint to fit (ADR-074).

    Read off the joint rather than restated beside it: the whole point of the
    function is that the router cannot drift from the shape.
    """

    for metrics, gauge in ((HOLE, 0.4), (PAD, 0.6), (HOLE, 0.8)):
        specs = solder_specs(metrics, gauge_mm=gauge)
        assert CadexSolder.lead_run_mm(metrics, gauge) == pytest.approx(
            specs["fillet_height"]
            + specs["collar_height"]
            + specs["crown_height"]
        )

    # And it is the height the joint actually reaches above the entry face,
    # which is the property the stand-off floor is really about. The crown is
    # part of that reach: it is the last thing holding the lead (ADR-114).
    specs = solder_specs(HOLE, gauge_mm=0.4)
    crest = _segment(specs, "crown")["end"][1]
    assert crest - specs["depth"] == pytest.approx(
        CadexSolder.lead_run_mm(HOLE, 0.4)
    )


@pytest.mark.parametrize(
    "metrics, gauge",
    [
        ({}, 0.4),                      # a literal (point, direction) port
        (HOLE, 0.0),                    # no lead at all
        (HOLE, 1.2),                    # a lead too fat for its own bore
        ({**PAD, "area": 1.0e-9}, 0.6),  # a pad with no annulus to sit on
    ],
)
def test_a_terminal_that_cannot_be_soldered_reserves_no_lead(metrics, gauge) -> None:
    """A run that could never carry a joint needs no room left for one.

    The alternative is for ``part.cable`` to refuse a route because a joint
    nobody asked for would not build — which would couple the two operations
    in exactly the direction ADR-074 is keeping them apart.
    """

    assert CadexSolder.lead_run_mm(metrics, gauge) == 0.0
    with pytest.raises(SolderError):
        solder_specs(metrics, gauge_mm=gauge)


def test_the_collar_and_the_cap_derive_and_are_not_knobs() -> None:
    """ADR-063's "a joint has enough numbers", pinned against drift.

    Nothing about the new shape reaches the payload, ``OP_ARG_SPECS`` or
    ``docs/INTEGRATION.md``: the four knobs are the four knobs.
    """

    signature = inspect.signature(solder_specs)
    assert [
        name
        for name, parameter in signature.parameters.items()
        if parameter.kind is inspect.Parameter.KEYWORD_ONLY
    ] == ["gauge_mm", "pad_dia_mm", "fillet_mm", "bore_dia_mm"]


# --------------------------------------------------------------------------
# the pad outline


def test_a_pad_joint_is_five_segments_with_no_cap_and_no_bore() -> None:
    specs = solder_specs(PAD, gauge_mm=0.4)

    assert specs["kind"] == "pad"
    assert _roles(specs) == ["pad_face", "meniscus", "collar", "crown", "lead"]
    assert specs["bore_radius"] is None
    assert specs["depth"] == 0.0
    # No lead end to cover: the wire lands on the pad, it does not pass it.
    assert specs["cap_height"] == 0.0
    assert specs["origin"] == PAD["entry_point"]
    # It never touches the axis, so it carries none of the hole's pole edge.
    assert min(point[0] for point in _polyline(specs)) == pytest.approx(LEAD)
    assert min(point[1] for point in _polyline(specs)) == pytest.approx(0.0)


def test_only_a_hole_reaches_the_axis_and_only_along_its_spine() -> None:
    specs = solder_specs(HOLE, gauge_mm=0.4)

    on_axis = [
        segment
        for segment in specs["profile"]
        if segment["start"][0] == 0.0 and segment["end"][0] == 0.0
    ]
    assert [segment["role"] for segment in on_axis] == ["spine"]
    assert abs(on_axis[0]["end"][1] - on_axis[0]["start"][1]) == pytest.approx(
        specs["cap_height"]
    )


# --------------------------------------------------------------------------
# the outline is simple, and wound the way the revolve needs


@pytest.mark.parametrize("metrics", (HOLE, PAD), ids=("hole", "pad"))
@pytest.mark.parametrize("gauge", (0.1, 0.4, 0.9))
@pytest.mark.parametrize("pad_dia", (1.2, 2.0, 6.0))
@pytest.mark.parametrize("fillet", (None, 1.0, 4.0))
def test_the_outline_is_simple_and_counter_clockwise(
    metrics, gauge: float, pad_dia: float, fillet
) -> None:
    """Where the risk went when the booleans left (ADR-064).

    A closed loop with positive signed area and no crossing between
    non-adjacent segments is a valid lathe profile, and all three of those are
    decidable headless — which is strictly better than a kernel hazard that
    can only be probed in a subprocess.
    """

    try:
        specs = solder_specs(
            metrics, gauge_mm=gauge, pad_dia_mm=pad_dia, fillet_mm=fillet
        )
    except SolderError:
        return  # refused for a stated reason, which the refusal tests cover

    points = _polyline(specs, samples=64)
    count = len(points)
    edges = [(points[index], points[(index + 1) % count]) for index in range(count)]
    for index, (first_start, first_end) in enumerate(edges):
        assert math.hypot(
            first_end[0] - first_start[0], first_end[1] - first_start[1]
        ) > 1.0e-9, "a segment shorter than the kernel's own confusion"
        assert first_start[0] >= 0.0
        for other in range(index + 2, count):
            if index == 0 and other == count - 1:
                continue  # adjacent across the wrap
            assert not _crosses(
                first_start, first_end, edges[other][0], edges[other][1]
            ), (index, other)
    assert _signed_area(points) > 0.0


def _crosses(a1, a2, b1, b2) -> bool:
    def side(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    d1, d2 = side(b1, b2, a1), side(b1, b2, a2)
    d3, d4 = side(a1, a2, b1), side(a1, a2, b2)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return True
    # Touching counts as crossing here: two non-adjacent segments of a simple
    # loop must not meet at all, not even at a point.
    for point, start, end in ((a1, b1, b2), (a2, b1, b2), (b1, a1, a2), (b2, a1, a2)):
        if abs(side(start, end, point)) < 1.0e-12 and (
            min(start[0], end[0]) - 1.0e-12 <= point[0] <= max(start[0], end[0]) + 1.0e-12
            and min(start[1], end[1]) - 1.0e-12 <= point[1] <= max(start[1], end[1]) + 1.0e-12
        ):
            return True
    return False


# --------------------------------------------------------------------------
# every derivation, and every override winning


def test_the_bore_comes_off_the_terminal_and_bore_dia_mm_overrides_it() -> None:
    assert solder_specs(HOLE, gauge_mm=0.4)["bore_radius"] == pytest.approx(0.5)
    assert solder_specs(HOLE, gauge_mm=0.4, bore_dia_mm=1.4)[
        "bore_radius"
    ] == pytest.approx(0.7)
    # A declared hole that never stated hole_dia has no measurement to take,
    # so the override is the only way it builds at all.
    declared = {**HOLE, "radius": None}
    assert solder_specs(declared, gauge_mm=0.4, bore_dia_mm=1.0)[
        "bore_radius"
    ] == pytest.approx(0.5)


def test_a_holes_pad_is_twice_the_bore_diameter_unless_it_is_stated() -> None:
    specs = solder_specs(HOLE, gauge_mm=0.4)

    # A 1.0 mm bore rings a 2.0 mm pad: the annulus a plated through-hole
    # footprint actually carries.
    assert specs["pad_radius"] == pytest.approx(1.0)
    assert solder_specs(HOLE, gauge_mm=0.4, pad_dia_mm=1.5)[
        "pad_radius"
    ] == pytest.approx(0.75)


def test_a_selected_pad_takes_its_width_from_the_faces_area() -> None:
    # area = pi is the disc of radius 1, so the derivation is exact rather
    # than merely close.
    assert solder_specs(PAD, gauge_mm=0.4)["pad_radius"] == pytest.approx(1.0)
    assert solder_specs({**PAD, "area": 4.0 * math.pi}, gauge_mm=0.4)[
        "pad_radius"
    ] == pytest.approx(2.0)
    assert solder_specs(PAD, gauge_mm=0.4, pad_dia_mm=3.0)[
        "pad_radius"
    ] == pytest.approx(1.5)


def test_the_fillet_is_a_quarter_round_unless_it_is_stated() -> None:
    specs = solder_specs(HOLE, gauge_mm=0.4)

    # It climbs to the collar exactly as far as it sweeps across to it.
    assert specs["fillet_height"] == pytest.approx(
        specs["pad_radius"] - specs["collar_radius"]
    )
    assert specs["fillet_height"] == pytest.approx(SPAN)
    # An override may only make the meniscus *taller*: below the default the
    # arc would undercut the board, which is its own refusal below.
    assert solder_specs(HOLE, gauge_mm=0.4, fillet_mm=1.25)[
        "fillet_height"
    ] == pytest.approx(1.25)
    # The cap and the collar follow the fillet and are not knobs of their own.
    stated = solder_specs(HOLE, gauge_mm=0.4, fillet_mm=1.25)
    assert stated["cap_height"] == pytest.approx(0.625)
    assert stated["collar_height"] == pytest.approx(0.625)


def test_the_lead_radius_is_half_the_gauge_it_was_given() -> None:
    assert solder_specs(HOLE, gauge_mm=0.6)["lead_radius"] == pytest.approx(0.3)


def test_the_same_metrics_give_byte_identical_specs() -> None:
    """A joint that varied run to run would change the project digest."""

    first = json.dumps(solder_specs(HOLE, gauge_mm=0.4), sort_keys=True)
    second = json.dumps(solder_specs(HOLE, gauge_mm=0.4), sort_keys=True)

    assert first == second


# --------------------------------------------------------------------------
# the contour integral


def _quadrature(specs, steps=200000):
    """``integral r**2 dz`` around the same loop, by brute force.

    Simpson over the arc's own parameter and exact on the lines, so it is a
    genuinely independent derivation of the same number rather than the same
    algebra written twice.
    """

    total = 0.0
    for segment in specs["profile"]:
        if segment["kind"] != "arc":
            (r1, z1), (r2, z2) = segment["start"], segment["end"]
            total += (z2 - z1) * (r1 * r1 + r1 * r2 + r2 * r2) / 3.0
            continue
        centre_r, _centre_z = segment["centre"]
        radius = segment["radius"]
        start, end = segment["start_angle"], segment["end_angle"]
        step = (end - start) / steps

        def integrand(theta):
            r = centre_r + radius * math.cos(theta)
            return r * r * radius * math.cos(theta)

        simpson = integrand(start) + integrand(end)
        for index in range(1, steps):
            simpson += (4.0 if index % 2 else 2.0) * integrand(start + step * index)
        total += simpson * step / 3.0
    return math.pi * total


def test_a_hole_joints_volume_is_the_contour_integral_of_its_own_outline() -> None:
    specs = solder_specs(HOLE, gauge_mm=0.4)

    assert joint_volume(specs) == pytest.approx(_quadrature(specs), rel=1.0e-9)
    # Moved by ADR-114 from 1.818264338933: a wider collar and the crown that
    # rounds it onto the lead. The quadrature above is what proves the new
    # arc's closed-form moment, and it is the assertion that matters.
    assert joint_volume(specs) == pytest.approx(1.847204008408, rel=1.0e-9)


def test_a_pad_joints_volume_is_the_contour_integral_too() -> None:
    specs = solder_specs(PAD, gauge_mm=0.4)

    assert joint_volume(specs) == pytest.approx(_quadrature(specs), rel=1.0e-9)
    # The two straight segments that carry volume, written out longhand: the
    # collar's cylinder up, the lead's cylinder down from the crown's crest,
    # and the pad face contributing nothing because dz is zero along it. What
    # is left over is the two arcs' own terms, and the quadrature above is
    # what pins them independently.
    straight = math.pi * (
        0.5 * SPAN * COLLAR**2 - (1.5 * SPAN + CROWN) * LEAD**2
    )
    arc_term = joint_volume(specs) - straight
    assert arc_term > 0.0
    assert joint_volume(specs) == pytest.approx(0.398929795103, rel=1.0e-9)


def test_the_concave_sweep_holds_less_solder_than_the_cone_it_replaced() -> None:
    """One number that documents the whole change (ADR-064).

    The old straight cone from the pad rim to the lead held 0.1676 mm^3 on the
    wcv8 ribbon joint; hollowing it into a concave sweep leaves 0.0940 — 56% of
    it — while making the joint 1.44x taller.  A sign error in either arc term
    would make it bigger, and this is what notices.

    It was 0.0744, 44%, until ADR-114 widened the collar and rounded it over
    onto the lead; the shape holds more solder near the wire on purpose, and
    "less than the cone" is the property being defended, not the fraction.
    """

    specs = solder_specs(PAD, gauge_mm=0.4, pad_dia_mm=1.2)
    lead, pad, fillet = 0.2, 0.6, 0.4
    cone = math.pi / 3.0 * fillet * (pad * pad + pad * lead + lead * lead) - (
        math.pi * lead * lead * fillet
    )

    assert cone == pytest.approx(0.1676, abs=5.0e-5)
    assert joint_volume(specs) == pytest.approx(0.0940, abs=5.0e-5)
    assert joint_volume(specs) < 0.6 * cone
    assert (
        specs["fillet_height"] + specs["collar_height"] + specs["crown_height"]
    ) == pytest.approx(1.4375 * fillet)


def test_a_thin_annulus_is_permitted_and_is_a_real_joint() -> None:
    """A press-fit lead with a film of solder around it is not an error.

    Only ``bore <= lead`` is refused, where there is no annulus at all.
    """

    specs = solder_specs(HOLE, gauge_mm=0.99, pad_dia_mm=2.0)

    assert specs["bore_radius"] > specs["lead_radius"]
    assert joint_volume(specs) > 0.0
    assert math.isfinite(specs["arc_radius"]) and specs["arc_radius"] > 0.0


# --------------------------------------------------------------------------
# every refusal, by message and by the values it names


def test_a_literal_port_carries_nothing_to_build_a_joint_from() -> None:
    with pytest.raises(SolderError) as excinfo:
        solder_specs({}, gauge_mm=0.4)

    assert excinfo.value.reason == "metrics"
    assert "part.terminals" in str(excinfo.value)
    assert "no radius" in str(excinfo.value)


def test_a_lead_that_does_not_fit_its_bore_is_refused_by_both_numbers() -> None:
    with pytest.raises(SolderError) as excinfo:
        solder_specs(HOLE, gauge_mm=1.2)

    assert excinfo.value.reason == "bore"
    assert excinfo.value.observed == {"bore_dia_mm": 1.0, "gauge_mm": 1.2}
    assert "1 mm across" in str(excinfo.value)
    assert "1.2 mm" in str(excinfo.value)
    # Exactly filling the bore leaves no annulus either.
    with pytest.raises(SolderError, match="already fills"):
        solder_specs(HOLE, gauge_mm=1.0)


def test_a_declared_hole_with_no_hole_dia_names_the_argument_that_fixes_it() -> None:
    with pytest.raises(SolderError) as excinfo:
        solder_specs({**HOLE, "radius": None}, gauge_mm=0.4)

    assert excinfo.value.reason == "bore"
    assert "bore_dia_mm" in str(excinfo.value)
    assert "hole_dia" in str(excinfo.value)


def test_a_declared_pad_with_no_area_names_the_argument_that_fixes_it() -> None:
    declared = {key: value for key, value in PAD.items() if key != "area"}

    with pytest.raises(SolderError) as excinfo:
        solder_specs(declared, gauge_mm=0.4)

    assert excinfo.value.reason == "pad"
    assert "pad_dia_mm" in str(excinfo.value)
    assert "pads=" in str(excinfo.value)


def test_a_pad_no_wider_than_the_lead_has_no_annulus_to_sit_on() -> None:
    with pytest.raises(SolderError) as excinfo:
        solder_specs(PAD, gauge_mm=2.0)

    assert excinfo.value.reason == "pad"
    assert excinfo.value.observed == {"pad_dia_mm": 2.0, "gauge_mm": 2.0}
    assert "no annulus for a fillet" in str(excinfo.value)


def test_a_pad_a_hair_wider_than_the_lead_collapses_the_arc_and_is_refused() -> None:
    """``pad > lead`` is strict-greater only, which was enough for a cone.

    A cone whose two radii differ by a picometre is a cylinder and builds
    fine.  An arc's three points collapse into one and OCC throws, so the
    floor is named here rather than arriving as a kernel traceback.
    """

    with pytest.raises(SolderError) as excinfo:
        solder_specs(PAD, gauge_mm=2.0, pad_dia_mm=2.0 + 1.0e-12)

    assert excinfo.value.reason == "pad"
    assert "floor an arc needs" in str(excinfo.value)
    assert excinfo.value.observed["minimum_span_mm"] == pytest.approx(1.0e-6)
    # A micron of annulus either side of the floor decides it.
    with pytest.raises(SolderError, match="floor an arc"):
        solder_specs(PAD, gauge_mm=2.0, pad_dia_mm=2.0 + 1.0e-6)
    assert solder_specs(PAD, gauge_mm=2.0, pad_dia_mm=2.0 + 1.0e-4)["arc_radius"] > 0.0


def test_a_pad_narrower_than_the_hole_it_rings_is_refused() -> None:
    with pytest.raises(SolderError) as excinfo:
        solder_specs(HOLE, gauge_mm=0.4, pad_dia_mm=0.9)

    assert excinfo.value.reason == "pad"
    assert excinfo.value.observed == {"pad_dia_mm": 0.9, "bore_dia_mm": 1.0}
    assert "narrower than the bore" in str(excinfo.value)


def test_a_meniscus_that_never_climbs_is_refused() -> None:
    with pytest.raises(SolderError) as excinfo:
        solder_specs(HOLE, gauge_mm=0.4, fillet_mm=-1.0)

    assert excinfo.value.reason == "fillet"
    assert "climbs the lead" in str(excinfo.value)


def test_a_fillet_shorter_than_the_pad_it_spans_would_undercut_the_board() -> None:
    """The one refusal the concave meniscus costs (ADR-064).

    An arc tangent to the lead at its top and passing through the pad rim
    sweeps more than a right angle when it climbs less than it spreads, and
    past a right angle it arrives at the board from *underneath*.  Both ways
    out are named: raise the fillet, or narrow the pad.
    """

    with pytest.raises(SolderError) as excinfo:
        solder_specs(HOLE, gauge_mm=0.4, fillet_mm=0.25)

    assert excinfo.value.reason == "fillet"
    assert "undercut" in str(excinfo.value)
    assert "0.75" in str(excinfo.value)
    assert excinfo.value.observed["minimum_fillet_mm"] == pytest.approx(SPAN)
    assert excinfo.value.observed["pad_dia_mm"] == pytest.approx(2.0)
    # The floor itself builds, by equality — which is exactly where the default
    # sits, so nothing that leaves fillet_mm alone can reach this refusal.
    assert solder_specs(HOLE, gauge_mm=0.4, fillet_mm=SPAN)[
        "fillet_height"
    ] == pytest.approx(SPAN)
    # ...and narrowing the pad is the other way out the message names: the
    # floor is a property of the two together, not of fillet_mm alone.
    assert solder_specs(PAD, gauge_mm=0.4, fillet_mm=0.25, pad_dia_mm=0.9)[
        "fillet_height"
    ] == pytest.approx(0.25)


def test_a_joint_needs_a_gauge_and_a_kind_it_understands() -> None:
    with pytest.raises(SolderError) as gauge:
        solder_specs(HOLE, gauge_mm=0.0)
    assert gauge.value.reason == "gauge"

    with pytest.raises(SolderError, match="hole or a pad") as kind:
        solder_specs({**HOLE, "kind": "via"}, gauge_mm=0.4)
    assert kind.value.observed == {"kind": "via"}

    with pytest.raises(SolderError, match="no depth"):
        solder_specs({**HOLE, "depth": 0.0}, gauge_mm=0.4)

    with pytest.raises(SolderError, match="no direction"):
        solder_specs({**HOLE, "axis": [0.0, 0.0, 0.0]}, gauge_mm=0.4)


# --------------------------------------------------------------------------
# the joint rides the terminal, and the terminal rides its component


def test_a_placed_terminals_metrics_size_the_joint() -> None:
    """ADR-062's ``_uniform_scale`` docstring, finally acquiring its consumer.

    A terminal's lengths carry the component's scale; the lead's gauge is a
    script number about the wire, which is not part of the component, so it
    does not.  A joint on a doubled board therefore has a doubled bore and the
    same lead — surprising, and correct.
    """

    terminals = resolve_terminals(
        declared_layout(
            None,
            header={
                "origin": (5.0, 10.0, 1.6),
                "axis": (0.0, 0.0, -1.0),
                "depth": 1.6,
                "hole_dia": 1.0,
            },
            names=["sda"],
        )
    )
    doubled = apply_placement(
        terminals,
        (2.0, 0.0, 0.0, 0.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.0, 1.0),
    )
    specs = solder_specs(doubled[0]["metrics"], gauge_mm=0.4)

    assert specs["bore_radius"] == pytest.approx(1.0)
    assert specs["depth"] == pytest.approx(3.2)
    assert specs["lead_radius"] == pytest.approx(0.2)
    assert specs["origin"] == pytest.approx([10.0, 20.0, 0.0])


def test_a_declared_terminal_and_a_selected_one_solder_the_same_way() -> None:
    """The two terminal forms must imply the same joint, or they mean different
    things — the same drift guard ``test_terminals.py`` puts on the landing
    point, carried one operation further."""

    declared = resolve_terminals(
        declared_layout(
            None,
            header={
                "origin": (5.0, 10.0, 1.6),
                "axis": (0.0, 0.0, -1.0),
                "depth": 1.6,
                "hole_dia": 1.0,
            },
            names=["sda"],
        )
    )[0]["metrics"]

    assert json.dumps(solder_specs(declared, gauge_mm=0.4), sort_keys=True) == json.dumps(
        solder_specs(HOLE, gauge_mm=0.4), sort_keys=True
    )


# --------------------------------------------------------------------------
# the api surface


def test_solder_is_declared_by_the_part_pack_and_the_runtime() -> None:
    assert "solder" in PART_PACK.api_exports
    assert "solder" in _part().exported_names
    # It publishes a solid, which the pack already declares; a joint is not a
    # new kind of thing.
    assert "solid" in PART_PACK.output_types


def test_one_call_is_one_joint_and_one_solid() -> None:
    part_api = _part()
    board = _board()
    fc = part_api.terminals(
        board,
        header={
            "origin": (5.0, 10.0, 1.6),
            "axis": (0.0, 0.0, -1.0),
            "depth": 1.6,
            "hole_dia": 1.0,
        },
        names=["sda"],
    )
    value = part_api.solder(fc["sda"], gauge_mm=0.4, label="sda joint")
    payload = value.to_payload()

    assert value.output_type == "solid"
    assert payload["operation"] == "solder"
    terminal = payload["arguments"][0]
    assert terminal["terminal"] == "sda"
    # The component's payload is nested in the port, exactly as a cable's is.
    assert terminal["component"]["operation"] == "box"
    assert terminal["layout"]["kind"] == "declared"
    assert payload["properties"]["gauge_mm"] == 0.4
    assert payload["properties"]["label"] == "sda joint"


def test_solder_refuses_a_literal_port_and_a_whole_terminal_set() -> None:
    part_api = _part()
    fc = part_api.terminals(
        _board(),
        header={
            "origin": (5.0, 10.0, 1.6),
            "axis": (0.0, 0.0, -1.0),
            "depth": 1.6,
            "hole_dia": 1.0,
            "along": (0.0, 1.0, 0.0),
            "pitch": 2.54,
            "count": 2,
        },
        names=["sda", "scl"],
    )

    with pytest.raises(ValueError) as literal:
        part_api.solder(((5.0, 10.0, 1.6), (0.0, 0.0, 1.0)), gauge_mm=0.4)
    assert "no bore radius" in str(literal.value)
    assert "part.terminals" in str(literal.value)

    with pytest.raises(ValueError, match="subscript it by name"):
        part_api.solder(fc, gauge_mm=0.4)


def test_solder_validates_its_numbers_before_any_geometry() -> None:
    part_api = _part()
    fc = part_api.terminals(
        _board(),
        header={
            "origin": (5.0, 10.0, 1.6),
            "axis": (0.0, 0.0, -1.0),
            "depth": 1.6,
            "hole_dia": 1.0,
        },
        names=["sda"],
    )

    with pytest.raises(ValueError, match="gauge_mm"):
        part_api.solder(fc["sda"], gauge_mm=0.0)
    with pytest.raises(ValueError, match="pad_dia_mm"):
        part_api.solder(fc["sda"], gauge_mm=0.4, pad_dia_mm=0.0)
    with pytest.raises(ValueError, match="fillet_mm"):
        part_api.solder(fc["sda"], gauge_mm=0.4, fillet_mm=-1.0)
    with pytest.raises(ValueError, match="bore_dia_mm"):
        part_api.solder(fc["sda"], gauge_mm=0.4, bore_dia_mm=-2.0)


def test_an_unset_override_is_absent_from_the_payload() -> None:
    """What it falls back to is geometry, and geometry resolves in the worker.

    Defaulting a derived number here would freeze it into the payload, which
    is exactly what a terminal exists to stop: the joint has to re-derive when
    the hole it names moves or changes size.
    """

    part_api = _part()
    fc = part_api.terminals(
        _board(),
        header={
            "origin": (5.0, 10.0, 1.6),
            "axis": (0.0, 0.0, -1.0),
            "depth": 1.6,
            "hole_dia": 1.0,
        },
        names=["sda"],
    )
    properties = part_api.solder(fc["sda"], gauge_mm=0.4).to_payload()["properties"]

    assert "pad_dia_mm" not in properties
    assert "fillet_mm" not in properties
    assert "bore_dia_mm" not in properties
    assert properties["refine"] is True


def test_the_solder_docstring_says_it_takes_a_terminal_and_never_a_literal() -> None:
    text = _part().solder.__doc__ or ""

    assert "never a literal" in text
    assert "meniscus" in text
    # ...and that the meniscus is the concave one ADR-064 shipped.
    assert "concave" in text


def test_the_worker_maps_every_refusal_reason_to_a_correction() -> None:
    """A reason with no correction would tell the model what is wrong and not
    what to do about it, which is the one thing this error envelope is for."""

    from cadex_part_worker import _SOLDER_CORRECTIONS

    reasons = {"metrics", "gauge", "bore", "pad", "fillet"}
    assert set(_SOLDER_CORRECTIONS) == reasons
    # Every reason CadexSolder can actually raise is one of them.
    raised = set()
    for call in (
        lambda: solder_specs({}, gauge_mm=0.4),
        lambda: solder_specs(HOLE, gauge_mm=0.0),
        lambda: solder_specs(HOLE, gauge_mm=1.2),
        lambda: solder_specs(PAD, gauge_mm=2.0),
        lambda: solder_specs(HOLE, gauge_mm=0.4, fillet_mm=-1.0),
        lambda: solder_specs(HOLE, gauge_mm=0.4, fillet_mm=0.25),
    ):
        with pytest.raises(SolderError) as excinfo:
            call()
        raised.add(excinfo.value.reason)
    assert raised == reasons


# --------------------------------------------------------------------------
# the whole path, against a real kernel
# --------------------------------------------------------------------------


#: Run inside ``FreeCADCmd``: build real joints on the real drilled plate
#: ``test_terminals.py`` uses.  What cannot be checked headless is exactly the
#: half that matters most — that the outline revolves into *one* closed solid,
#: that its volume is the contour integral, that a slab through it is the ring
#: the arc implies rather than the ring a cone would, and how much material
#: the joint shares with the wire that lands in it.
#:
#: ``sda`` is the *third* hole along +X, so its joint is centred on x = 25.
_PROBE = r"""
import json, math, sys, time
sys.path.insert(0, %(root)r)
import Part, FreeCAD as App
import CadexSolder
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

PAD_LAYOUT = {
    "kind": "declared",
    "terminals": [{
        "origin": [20.0, 4.0, 1.6], "along": [0.0, 1.0, 0.0],
        "axis": [0.0, 0.0, -1.0], "pitch": 0.0, "count": 1,
        "depth": 0.0, "hole_dia": None,
    }],
    "names": ["led"],
}


def terminal(name, layout=LAYOUT, component=PLATE):
    return {"terminal": name, "component": component, "layout": layout}


def solder(port, **properties):
    base = {"gauge_mm": 0.6, "refine": True}
    base.update(properties)
    return {
        "domain": "part", "operation": "solder", "output_type": "solid",
        "arguments": [port], "properties": base,
    }


def cable(start, end, **properties):
    base = {"gauge_mm": 0.6, "clearance_mm": 0.5, "slack": 1.02, "avoid": []}
    base.update(properties)
    return {
        "domain": "part", "operation": "cable", "output_type": "solid",
        "arguments": [start, end], "properties": base,
    }


def measure(shape):
    # OCC's BoundBox over-estimates a revolved arc: the toroidal face's own
    # box, not the trimmed patch's. The joint's z-extent comes out 0.14 mm too
    # tall on the hole joint, which is why the exact one is asked for first.
    box = shape.BoundBox
    try:
        exact = shape.optimalBoundingBox()
        optimal = [
            float(exact.XMin), float(exact.YMin), float(exact.ZMin),
            float(exact.XMax), float(exact.YMax), float(exact.ZMax),
        ]
    except Exception:
        points = [v.Point for v in shape.Vertexes]
        optimal = [
            min(p.x for p in points), min(p.y for p in points),
            min(p.z for p in points), max(p.x for p in points),
            max(p.y for p in points), max(p.z for p in points),
        ]
    return {
        "shape_type": str(shape.ShapeType),
        "solids": len(shape.Solids),
        "faces": len(shape.Faces),
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
        "volume": float(shape.Volume),
        "bounds": [
            float(box.XMin), float(box.YMin), float(box.ZMin),
            float(box.XMax), float(box.YMax), float(box.ZMax),
        ],
        "optimal": optimal,
    }


def arc_of(specs):
    for segment in specs["profile"]:
        if segment["kind"] == "arc":
            return segment
    raise AssertionError("no arc")


# pi (r(z)^2 - w^2): what a slab at height z should cut, from the module. The
# meniscus inverts exactly -- r(z) = rc - sqrt(R^2 - (z - zc)^2) -- so this is
# the arc's own radius at that height and not a resampling of it.
def ring_area(specs, z):
    arc = arc_of(specs)
    centre_r, centre_z = arc["centre"]
    radius = arc["radius"]
    lead = specs["lead_radius"]
    outer = centre_r - math.sqrt(max(radius * radius - (z - centre_z) ** 2, 0.0))
    return math.pi * (outer * outer - lead * lead)


report = {}
try:
    worker.reset_part_shape_memo()
    metrics = worker._resolve_terminal_set("solder", "terminal", terminal("sda"))
    specs = CadexSolder.solder_specs(metrics["sda"]["metrics"], gauge_mm=0.6)
    report["ideal_volume"] = CadexSolder.joint_volume(specs)
    report["lead_run"] = CadexSolder.lead_run_mm(metrics["sda"]["metrics"], 0.6)
    report["pad_radius"] = specs["pad_radius"]
    report["collar_radius"] = specs["collar_radius"]
    report["fillet_height"] = specs["fillet_height"]
    report["collar_height"] = specs["collar_height"]
    report["crown_height"] = specs["crown_height"]
    report["cap_height"] = specs["cap_height"]
    report["arc_radius"] = specs["arc_radius"]

    joint = worker.build_part_shape(solder(terminal("sda")))
    report["joint"] = measure(joint)
    # ...and unrefined: a revolve leaves no seam, so removeSplitter has nothing
    # to remove, which retires ADR-063's coincident-face worry outright.
    report["unrefined"] = measure(
        worker.build_part_shape(solder(terminal("sda"), refine=False))
    )

    # The assertion that tells a concave arc from a convex one: total volume
    # cannot, because the same endpoints and the same integral admit both.
    # Slab the meniscus and compare each ring to what the module's r(z) says.
    slabs = []
    thickness = 2.0e-3
    for fraction in (0.15, 0.35, 0.55, 0.75, 0.95):
        base = 1.6 + fraction * report["fillet_height"]
        slab = Part.makeBox(
            60.0, 40.0, thickness, App.Vector(-10.0, -10.0, base)
        )
        cut = joint.common((slab,))
        steps = 400
        analytic = 0.0
        for index in range(steps + 1):
            z = base + thickness * index / steps
            weight = 1.0 if index in (0, steps) else (4.0 if index %% 2 else 2.0)
            analytic += weight * ring_area(specs, z)
        analytic *= (thickness / steps) / 3.0
        # The straight chord between the arc's own two endpoints -- and, since
        # both this chord and ADR-063's cone from the pad rim to the lead have
        # slope exactly -1, the same line as the shape ADR-064 replaced. A
        # concave arc cuts less than it at every height; a convex one through
        # the same endpoints would cut more.
        chord_r = report["pad_radius"] + fraction * (
            report["collar_radius"] - report["pad_radius"]
        )
        slabs.append({
            "z": base,
            "measured": float(cut.Volume),
            "analytic": analytic,
            "chord": math.pi * thickness * (chord_r * chord_r - 0.3 * 0.3),
        })
    report["slabs"] = slabs

    # A pad joint: no cap, no barrel, and it never reaches the axis.
    pad_joint = worker.build_part_shape(
        solder(terminal("led", PAD_LAYOUT), pad_dia_mm=2.0)
    )
    report["pad_joint"] = measure(pad_joint)
    pad_specs = CadexSolder.solder_specs(
        worker._resolve_terminal_set(
            "solder", "terminal", terminal("led", PAD_LAYOUT)
        )["led"]["metrics"],
        gauge_mm=0.6,
        pad_dia_mm=2.0,
    )
    report["pad_ideal_volume"] = CadexSolder.joint_volume(pad_specs)
    report["pad_fillet_height"] = pad_specs["fillet_height"]
    report["pad_collar_height"] = pad_specs["collar_height"]
    report["pad_crown_height"] = pad_specs["crown_height"]

    # The two places OCC could plausibly misbehave: the tangency case, where
    # the torus is tangent to the entry-face plane, and a near-spindle torus.
    for label, fillet in (("tangent", specs["fillet_height"]), ("spindle", 4.0)):
        report[label] = measure(
            worker.build_part_shape(solder(terminal("sda"), fillet_mm=fillet))
        )

    # How much material the joint shares with the wire that lands in it, and
    # how straight the wire is where the joint grips it (ADR-074). The spine
    # is caught on its way through so the swept solid can be measured against
    # `pi r^2 L` -- a folded sweep is closed, valid and short, so volume
    # against its own path length is the only assertion that sees it.
    caught = {}
    uncaught_sweep = worker._sweep_conductor

    def catching(waypoints, **kwargs):
        caught["waypoints"] = [list(point) for point in waypoints]
        caught["gauge"] = float(kwargs["gauge"])
        caught["frenet"] = bool(kwargs.get("frenet", True))
        caught["start_tangent"] = list(kwargs["start_tangent"])
        return uncaught_sweep(waypoints, **kwargs)

    worker._sweep_conductor = catching
    try:
        wire = worker.build_part_shape(
            cable(terminal("vbat"), terminal("scl"), cell_mm=1.0)
        )
    finally:
        worker._sweep_conductor = uncaught_sweep
    report["wire_waypoints"] = caught["waypoints"]
    report["wire_frenet"] = caught["frenet"]
    report["wire_start_tangent"] = caught["start_tangent"]
    spine = Part.BSplineCurve()
    spine.interpolate(
        Points=[App.Vector(*point) for point in caught["waypoints"]],
        PeriodicFlag=False, Tolerance=1.0e-7,
        **worker._tangent_constraints(
            App.Vector(*caught["start_tangent"]), App.Vector(0.0, 0.0, -1.0)
        ),
    )
    report["wire_volume"] = float(wire.Volume)
    report["wire_ideal_volume"] = (
        math.pi * (caught["gauge"] / 2.0) ** 2 * float(spine.toShape().Length)
    )
    # The start cap of the pipe shell: a flat disc whose normal *is* the
    # tangent the wire leaves on. A tilted one is the misaligned ring you see
    # where the collar meets the wire.
    planar = [
        face for face in wire.Faces
        if isinstance(face.Surface, Part.Plane)
        and (face.CenterOfMass - App.Vector(5.0, 10.0, 0.0)).Length < 1.0
    ]
    report["wire_start_faces"] = len(planar)
    if planar:
        surface = planar[0].Surface
        report["wire_start_normal"] = list(surface.Axis)
    # ...and how far the wire's centreline has wandered off the terminal's
    # axis by the time it leaves the barrel and the collar behind.
    drift = {}
    for height in (0.4, 1.2, 1.6, 2.0, 2.6):
        sections = wire.slice(App.Vector(0.0, 0.0, 1.0), height)
        faces = [Part.Face(section) for section in sections]
        nearest = min(faces, key=lambda f: abs(f.CenterOfMass.x - 5.0))
        drift["%%.1f" %% height] = [
            abs(float(nearest.CenterOfMass.x) - 5.0), float(nearest.Area)
        ]
    report["wire_drift"] = drift
    barrel_zone = Part.makeBox(60.0, 40.0, 1.6, App.Vector(-10.0, -10.0, 0.0))
    for name in ("vbat", "scl"):
        joint_shape = worker.build_part_shape(solder(terminal(name)))
        shared = joint_shape.common((wire,))
        report["overlap_" + name] = float(shared.Volume)
        # Clip the JOINT and intersect that, rather than clipping the sliver:
        # since the lead runs straight through a bore of its own radius the
        # two meet tangentially, and a boolean against that near-empty result
        # comes back as the whole clipping box (3840 mm^3 of "overlap" between
        # shapes sharing 3e-6). Both operands here are well-formed solids.
        in_barrel = joint_shape.common((barrel_zone,)).common((wire,))
        report["overlap_in_barrel_" + name] = float(in_barrel.Volume)
    # What the wire would share with the joint if its outline did not leave the
    # lead's own radius empty: the whole length through barrel, arc and collar.
    report["unbored_overlap"] = (
        math.pi * 0.3 * 0.3
        * (1.6 + report["fillet_height"] + report["collar_height"])
    )

    # Eight joints and a cable on one board: one terminal resolution, one
    # board build, whatever names it and however many times.
    worker.reset_part_shape_memo()
    uncached = worker._build_part_shape_uncached
    builds = {"plate": 0}

    def counting(payload, *, diagnostics=None):
        if payload == PLATE:
            builds["plate"] += 1
        return uncached(payload, diagnostics=diagnostics)

    worker._build_part_shape_uncached = counting
    try:
        started = time.time()
        for name in LAYOUT["names"]:
            for gauge in (0.6, 0.5):
                worker.build_part_shape(solder(terminal(name), gauge_mm=gauge))
        report["eight_joint_seconds"] = time.time() - started
        worker.build_part_shape(cable(terminal("gnd"), terminal("sda"), cell_mm=1.0))
    finally:
        worker._build_part_shape_uncached = uncached
    report["terminal_sets"] = len(worker._TERMINAL_SETS)
    report["board_builds"] = builds["plate"]

    for label, payload in (
        ("fat_lead", solder(terminal("sda"), gauge_mm=1.2)),
        ("literal", solder([[5.0, 10.0, 1.6], [0.0, 0.0, 1.0]])),
        ("narrow_pad", solder(terminal("sda"), pad_dia_mm=0.8)),
        ("short_fillet", solder(terminal("sda"), fillet_mm=0.1)),
    ):
        try:
            worker.build_part_shape(payload)
        except Exception as exc:
            report[label] = "%%s" %% (exc,)
            report[label + "_details"] = getattr(exc, "details", {})
except Exception as exc:
    import traceback
    report["crashed"] = traceback.format_exc()
open(%(out)r, "w").write(json.dumps(report))
"""


def _kernel_report():
    from test_cadexd_lifecycle import CADEX_ROOT, FREECADCMD

    scratch = pathlib.Path(tempfile.mkdtemp(prefix="cadex-solder-probe-"))
    out = scratch / "report.json"
    probe = scratch / "probe.py"
    probe.write_text(_PROBE % {"root": str(CADEX_ROOT), "out": str(out)})
    finished = subprocess.run(
        [str(FREECADCMD), "-c", f"exec(open({str(probe)!r}).read())"],
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert out.is_file(), finished.stdout[-4000:] + finished.stderr[-4000:]
    return json.loads(out.read_text())


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available to revolve a joint against OCC.",
)
def test_a_joint_on_a_real_drilled_plate_is_one_closed_solid() -> None:
    report = _kernel_report()

    assert "crashed" not in report, report.get("crashed")
    joint = report["joint"]
    assert joint["solids"] == 1
    assert joint["valid"] is True
    assert joint["closed"] is True
    # Ten segments, one of which lies on the axis and sweeps into nothing.
    assert joint["faces"] == 9

    # The assertion that catches an outline which lost a segment or wound the
    # wrong way. It is exact now rather than merely close: there is no boolean
    # left to lose precision in.
    assert joint["volume"] == pytest.approx(report["ideal_volume"], rel=1.0e-9)

    # A 1.0 mm bore rings a 2.0 mm pad, so the joint is 2 mm across, centred
    # on the third hole along +X at (25, 10).
    pad = report["pad_radius"]
    assert pad == pytest.approx(1.0)
    assert joint["optimal"][0] == pytest.approx(25.0 - pad, abs=1.0e-6)
    assert joint["optimal"][3] == pytest.approx(25.0 + pad, abs=1.0e-6)
    # It sits on the two right faces: the cap hangs below the far face at
    # z = 0 and the meniscus climbs above the entry face at z = 1.6, with the
    # collar carrying it half as far again. An axis flip would put both on the
    # same side.
    assert joint["optimal"][2] == pytest.approx(-report["cap_height"], abs=1.0e-6)
    assert joint["optimal"][5] == pytest.approx(
        1.6
        + report["fillet_height"]
        + report["collar_height"]
        + report["crown_height"],
        abs=1.0e-6,
    )
    # The exact box is asked for rather than BoundBox, and that is not
    # fussiness: OCC boxes a revolved arc by its whole toroidal surface rather
    # than the trimmed patch, and on some joints that over-states the z-extent
    # by more than a tenth of a millimetre. It is a bound, so it never
    # under-states -- but an assertion on it to 1e-6 would fail for that
    # reason and look like a geometry bug.
    assert joint["bounds"][5] >= joint["optimal"][5] - 1.0e-9
    assert joint["bounds"][2] <= joint["optimal"][2] + 1.0e-9


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available to revolve a joint against OCC.",
)
def test_a_slab_through_the_meniscus_cuts_the_ring_the_arc_implies() -> None:
    """The assertion that pins *concave*, which no volume can (ADR-064).

    A convex sweep with the same two endpoints and the same total volume
    exists; what separates it from this one is where the material sits at each
    height. So the joint is sliced, and each ring is compared to
    ``pi (r(z)^2 - w^2)`` integrated over the slab from the module's own arc —
    and, at the same heights, against the straight chord between the arc's
    endpoints, which is the cone ADR-063 shipped.
    """

    report = _kernel_report()

    assert "crashed" not in report, report.get("crashed")
    for slab in report["slabs"]:
        assert slab["measured"] == pytest.approx(slab["analytic"], rel=1.0e-6)
        # Inside the chord at every height, by a wide margin in the middle:
        # that gap *is* the swoop, and a convex arc through the same two
        # endpoints would sit outside it instead.
        assert slab["measured"] < slab["chord"]
    assert report["slabs"][2]["measured"] < 0.6 * report["slabs"][2]["chord"]


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available to revolve a joint against OCC.",
)
def test_a_pad_joint_is_one_revolve_with_nothing_below_the_face() -> None:
    report = _kernel_report()

    assert "crashed" not in report, report.get("crashed")
    pad_joint = report["pad_joint"]
    assert pad_joint["solids"] == 1
    assert pad_joint["valid"] is True
    assert pad_joint["closed"] is True
    # Five segments, none of them on the axis, so five faces.
    assert pad_joint["faces"] == 5
    assert pad_joint["volume"] == pytest.approx(report["pad_ideal_volume"], rel=1.0e-9)
    # No barrel and no cap: nothing below the face it sits on.
    assert pad_joint["optimal"][2] == pytest.approx(1.6, abs=1.0e-6)
    assert pad_joint["optimal"][5] == pytest.approx(
        1.6
        + report["pad_fillet_height"]
        + report["pad_collar_height"]
        + report["pad_crown_height"],
        abs=1.0e-6,
    )


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available to revolve a joint against OCC.",
)
def test_the_revolve_leaves_no_seam_and_survives_both_torus_extremes() -> None:
    """What ADR-064 deleted, measured.

    ``refine`` is kept because the payload is unchanged, but a revolve has no
    coincident faces to drop — so refined and unrefined must be the same shape,
    which is the retirement of ADR-063's fuse-seam worry. The two extremes are
    the tangency case, where the toroidal face is tangent to the entry-face
    plane, and a near-spindle torus whose major radius dwarfs the collar.
    """

    report = _kernel_report()

    assert "crashed" not in report, report.get("crashed")
    assert report["unrefined"]["faces"] == report["joint"]["faces"]
    assert report["unrefined"]["volume"] == pytest.approx(
        report["joint"]["volume"], rel=1.0e-12
    )
    for label in ("tangent", "spindle"):
        assert report[label]["solids"] == 1, label
        assert report[label]["valid"] is True, label
        assert report[label]["closed"] is True, label


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available to revolve a joint against OCC.",
)
def test_the_wire_leaves_its_terminal_along_the_axis_it_was_given() -> None:
    """The assertion that would have caught ADR-074, at both ends of it.

    A cable's spline used to be fitted with **free** ends, so it left the
    terminal on whatever tangent a global C2 fit produced — measured here at
    9.7 degrees off a bore's own axis — and the profile circle, which is
    oriented off that same first tangent, was tilted with it.  That is the
    misaligned ring where the collar meets the wire, and the wire clipping
    through the joint that is meant to grip it.

    The sweep frame is the other half.  True Frenet takes its normal from the
    curve's curvature, and a routed cable is mostly straight: the same run
    swept in true Frenet came out at 78% of ``pi r^2 L``, folded through
    itself, and — the part worth remembering — *boolean operations against it
    silently returned nothing*, which is how a wire drifting 0.09 mm off-axis
    inside a 0.3 mm bore reported exactly zero shared volume with the joint
    around it.  The zero this test used to assert was a broken sweep, not a
    straight wire.
    """

    report = _kernel_report()

    assert "crashed" not in report, report.get("crashed")
    # Corrected frame, and volume against the spine's own length: closed and
    # valid say nothing here, a folded sweep is both.
    assert report["wire_frenet"] is False
    assert report["wire_volume"] == pytest.approx(
        report["wire_ideal_volume"], rel=0.01
    )

    # The terminal leaves along +Z, and so does the wire: exactly, not nearly.
    assert report["wire_start_tangent"] == pytest.approx([0.0, 0.0, 1.0])
    assert report["wire_start_faces"] == 1
    assert abs(report["wire_start_normal"][2]) == pytest.approx(1.0, abs=1.0e-9)

    # ...and it stays on that axis for the whole run the joint grips: a lead
    # that wandered its own radius would leave the bore entirely.
    for height, (drift, area) in sorted(report["wire_drift"].items()):
        assert drift < 0.05, (height, drift)
        # Still a full round conductor at every height — the section a
        # collapsed sweep loses.
        assert area == pytest.approx(math.pi * 0.3 * 0.3, rel=0.05), height


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available to revolve a joint against OCC.",
)
def test_the_router_leaves_the_lead_the_joint_needs_before_it_turns() -> None:
    """Where the route is allowed to start bending (ADR-074).

    ``part.cable`` never learns whether a joint exists — it floors its
    stand-off with :func:`CadexSolder.lead_run_mm` so that one *could* be
    there.  On this plate that is the 1.6 mm barrel plus the meniscus and the
    collar, and the anchor is exactly that far along the axis: the first
    waypoint the search is free to move.
    """

    report = _kernel_report()

    assert "crashed" not in report, report.get("crashed")
    waypoints = report["wire_waypoints"]
    anchor = CadexRouting._STUB_SEGMENTS
    # From the far face, up the bore, and clear of the joint before the first
    # searched cell -- through the stub's own knots, which is what keeps the
    # interpolated wire on the axis rather than merely tangent to it at the
    # port (ADR-114).
    assert waypoints[0] == pytest.approx([5.0, 10.0, 0.0])
    for index in range(anchor + 1):
        assert waypoints[index][0] == pytest.approx(5.0)
        assert waypoints[index][1] == pytest.approx(10.0)
        assert waypoints[index][2] == pytest.approx(
            (1.6 + report["lead_run"]) * index / anchor
        )
    # Which is more than the clearance alone would have given: without the
    # floor the anchor sat 0.5 mm above the face, inside the collar.
    assert report["lead_run"] > 0.5


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available to revolve a joint against OCC.",
)
def test_the_lead_bore_leaves_the_wire_a_radius_of_its_own() -> None:
    """What the joint and its wire share, and where.

    Measured, not assumed.  A joint is built from the terminal's *straight*
    bore while the wire is a spline fitted through a searched route, so the
    two agree exactly only where the route is straight — and since ADR-114
    that is the whole run the joint holds, knot by knot, rather than merely
    tangentially at the port.  It is measured against the counterfactual
    rather than against zero: without the empty radius in the joint's own
    outline, the wire's whole length through the barrel, the meniscus and the
    collar would be shared.

    ADR-074 left a sliver of 0.038 mm^3 here — the wire bowing out of one side
    of its own solder — and the stub knots took it to 3.5e-6, four orders of
    magnitude down and nothing a render can show.  It stays a bound rather
    than an equality because ``part.solder`` takes a terminal, not a wire, and
    must build whether or not a cable was ever routed to it.
    """

    report = _kernel_report()

    assert "crashed" not in report, report.get("crashed")
    for name in ("vbat", "scl"):
        # Nothing inside the board at all, and a rounding of the joint above it.
        assert report["overlap_in_barrel_" + name] == pytest.approx(0.0, abs=1.0e-9)
        assert report["overlap_" + name] < 1.0e-4 * report["unbored_overlap"]
        assert report["overlap_" + name] < 1.0e-4 * report["joint"]["volume"]


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available to revolve a joint against OCC.",
)
def test_eight_joints_resolve_one_terminal_set_and_refuse_loudly() -> None:
    report = _kernel_report()

    assert "crashed" not in report, report.get("crashed")
    # Eight joints and a cable on one board: one resolved terminal set.
    assert report["terminal_sets"] == 1
    assert report["board_builds"] == 1

    assert "no annulus" in report["fat_lead"]
    assert report["fat_lead_details"]["stage"] == "part_solder"
    assert report["fat_lead_details"]["observed"]["reason"] == "bore"
    assert "part.terminals" in report["literal"]
    assert "narrower than the bore" in report["narrow_pad"]
    # The one refusal ADR-064 added, reaching the model through the same
    # envelope as the four ADR-063 shipped.
    assert "undercut" in report["short_fillet"]
    assert report["short_fillet_details"]["observed"]["reason"] == "fillet"
