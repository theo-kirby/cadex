# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The multi-conductor lay and the ``part.bundle`` contract (ADR-057).

``CadexBundle`` imports nothing from FreeCAD, so the lay itself is exercised
here against synthetic centrelines rather than against OCC.  What is asserted
is the set of properties the rest of the system depends on: a lay is
reproducible, its conductors do not interpenetrate, the frame does not flip
where Frenet's would, and the degenerate cases degrade to a stated answer
rather than to NaN.

The kernel-side geometry — that a conductor sweeps into one valid closed
solid of the right volume — is at the bottom of this file, behind the same
``FreeCADCmd`` skip the selector suite uses.
"""

from __future__ import annotations

import json
import math
import pathlib
import subprocess
import tempfile

import pytest

import CadexBundle
from CadexBundle import (
    BundleError,
    bundle_radius,
    conductor_paths,
    default_twist_pitch,
    min_conductor_separation,
    outer_diameter,
    sample_count,
)
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import create_domain_api


PART_PACK = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]
MESH_PACK = XSCRIPT_WORKBENCH_PACKS["MeshWorkbench"]


def _part():
    return create_domain_api(PART_PACK.domain, PART_PACK.api_exports, PART_PACK.output_types)


def _mesh():
    return create_domain_api(MESH_PACK.domain, MESH_PACK.api_exports, MESH_PACK.output_types)


def _straight(length: float = 100.0, samples: int = 241, axis: int = 2):
    """A centreline along one world axis."""

    def point(index: int) -> tuple[float, float, float]:
        value = length * index / (samples - 1)
        return tuple(value if axis == k else 0.0 for k in range(3))  # type: ignore[return-value]

    return [point(index) for index in range(samples)]


def _s_bend(samples: int = 401):
    """A planar S-curve: curvature changes sign, so Frenet's normal flips."""

    return [
        (index * 0.2, 8.0 * math.sin(index * 0.2 * math.pi / 20.0), 0.0)
        for index in range(samples)
    ]


def _distance(first, second) -> float:
    return math.sqrt(sum((first[k] - second[k]) ** 2 for k in range(3)))


def _closest_approach(first, second) -> float:
    """Smallest distance between two sampled polylines, sample to sample."""

    return min(_distance(a, b) for a in first for b in second)


# --------------------------------------------------------------------------
# The lay: separation, determinism, frame
# --------------------------------------------------------------------------


def test_a_lay_returns_one_path_per_conductor_of_the_same_length() -> None:
    centre = _straight()
    paths = conductor_paths(centre, count=3, style="twisted", gauge_mm=1.0, twist_pitch_mm=20.0)

    assert len(paths) == 3
    assert all(len(path) == len(centre) for path in paths)


def test_the_same_inputs_give_byte_identical_paths() -> None:
    """The digest depends on this: ``open_project`` re-runs the script."""

    centre = _straight()
    first = conductor_paths(centre, count=4, style="twisted", gauge_mm=0.9, twist_pitch_mm=17.0)
    second = conductor_paths(centre, count=4, style="twisted", gauge_mm=0.9, twist_pitch_mm=17.0)

    assert first == second
    flat_first = conductor_paths(centre, count=4, style="flat", gauge_mm=0.9)
    flat_second = conductor_paths(centre, count=4, style="flat", gauge_mm=0.9)
    assert flat_first == flat_second


def test_twisted_conductors_hold_a_constant_radius_and_even_phase() -> None:
    centre = _straight()
    paths = conductor_paths(centre, count=3, style="twisted", gauge_mm=1.0, twist_pitch_mm=20.0)

    radii = [math.hypot(point[0], point[1]) for path in paths for point in path]
    assert max(radii) - min(radii) < 1.0e-9

    # Phase separation between neighbours is 2*pi/N at every sample.
    for sample in range(0, len(centre), 17):
        angles = [math.atan2(path[sample][1], path[sample][0]) for path in paths]
        for index in range(3):
            gap = (angles[(index + 1) % 3] - angles[index]) % (2.0 * math.pi)
            assert gap == pytest.approx(2.0 * math.pi / 3.0, abs=1.0e-9)


def test_twist_count_over_a_straight_run_matches_length_over_pitch() -> None:
    length, pitch = 100.0, 10.0
    paths = conductor_paths(
        _straight(length), count=3, style="twisted", gauge_mm=1.0, twist_pitch_mm=pitch
    )

    turned = 0.0
    previous = math.atan2(paths[0][0][1], paths[0][0][0])
    for point in paths[0][1:]:
        angle = math.atan2(point[1], point[0])
        step = (angle - previous + math.pi) % (2.0 * math.pi) - math.pi
        turned += step
        previous = angle

    assert turned / (2.0 * math.pi) == pytest.approx(length / pitch, abs=1.0e-6)


def test_left_handed_mirrors_the_lay() -> None:
    """Handedness pinned concretely: the run is +Z, the seed normal is +Y, so
    a left-handed lay is the right-handed one reflected in X."""

    centre = _straight(60.0, 121)
    right = conductor_paths(centre, count=3, style="twisted", gauge_mm=1.0, twist_pitch_mm=8.0)
    left = conductor_paths(
        centre, count=3, style="twisted", gauge_mm=1.0, twist_pitch_mm=8.0, left_handed=True
    )

    for first, second in zip(right[0], left[0]):
        assert first[0] == pytest.approx(-second[0], abs=1.0e-12)
        assert first[1] == pytest.approx(second[1], abs=1.0e-12)
        assert first[2] == pytest.approx(second[2], abs=1.0e-12)


def test_flat_conductors_are_coplanar_evenly_spaced_and_touching() -> None:
    centre = _straight()
    paths = conductor_paths(centre, count=4, style="flat", gauge_mm=0.8)

    for sample in range(0, len(centre), 23):
        row = [path[sample] for path in paths]
        for index in range(3):
            assert _distance(row[index], row[index + 1]) == pytest.approx(0.8, abs=1.0e-9)
        # Coplanar: every conductor sits on the line through the outer two.
        span = [row[3][k] - row[0][k] for k in range(3)]
        for point in row[1:3]:
            offset = [point[k] - row[0][k] for k in range(3)]
            cross = (
                span[1] * offset[2] - span[2] * offset[1],
                span[2] * offset[0] - span[0] * offset[2],
                span[0] * offset[1] - span[1] * offset[0],
            )
            assert math.sqrt(sum(value * value for value in cross)) < 1.0e-9


def test_the_frame_does_not_flip_through_an_inflection() -> None:
    """The reason the frame is rotation-minimising and not Frenet.

    A routed centreline S-bends around obstacles, and Frenet's normal is
    defined by the curvature vector, so it reverses at every inflection.  The
    carried frame turns only as fast as the path does.
    """

    centre = _s_bend()
    paths = conductor_paths(
        centre, count=2, style="twisted", gauge_mm=1.0, twist_pitch_mm=1.0e12
    )
    offsets = [
        tuple(paths[0][index][k] - centre[index][k] for k in range(3))
        for index in range(len(centre))
    ]

    worst = 0.0
    for index in range(1, len(offsets)):
        before, after = offsets[index - 1], offsets[index]
        cosine = sum(before[k] * after[k] for k in range(3)) / (
            math.dist(before, (0.0, 0.0, 0.0)) * math.dist(after, (0.0, 0.0, 0.0))
        )
        worst = max(worst, math.degrees(math.acos(max(-1.0, min(1.0, cosine)))))

    # The path itself turns by a couple of degrees per sample; the frame turns
    # no faster.  A Frenet frame would post a 180 here.
    assert worst < 10.0


def test_a_run_parallel_to_up_degrades_deterministically() -> None:
    """``lateral = tangent x up`` has no direction on a vertical run, which is
    the single most common harness geometry.  It must fall back, not NaN."""

    centre = _straight(30.0, 61, axis=2)
    paths = conductor_paths(
        centre, count=4, style="flat", gauge_mm=1.0, up=(0.0, 0.0, 1.0)
    )

    assert all(math.isfinite(value) for path in paths for point in path for value in point)
    for sample in range(0, 61, 7):
        row = [path[sample] for path in paths]
        for index in range(3):
            assert _distance(row[index], row[index + 1]) == pytest.approx(1.0, abs=1.0e-9)
    # And it is a *choice*, not luck: the same input gives the same fallback.
    assert paths == conductor_paths(
        centre, count=4, style="flat", gauge_mm=1.0, up=(0.0, 0.0, 1.0)
    )


# --------------------------------------------------------------------------
# The lay radius: the correction the chord formula needs
# --------------------------------------------------------------------------


def test_neighbouring_helices_do_not_touch_in_a_shared_cross_section() -> None:
    """Why the lay radius is solved rather than asserted.

    ``R = (d/2)/sin(pi/N)`` puts N circles of diameter ``d`` touching on a
    circle, but two helices reach their closest approach at an *axial* offset,
    not in a shared cross-section.  For N >= 3 the chord radius therefore
    interpenetrates at every finite pitch — silently, since the result is
    still a closed valid solid.
    """

    overlaps = {
        # (count, gauge, pitch): the chord radius is not enough
        (3, 1.0, 8.0): True,
        (4, 1.0, 10.0): True,
        (6, 1.2, 15.0): True,
        # N = 2 is the one exact case: antipodal helices *do* pinch at u = 0.
        (2, 1.0, 10.0): False,
    }
    for (count, gauge, pitch), interferes in overlaps.items():
        chord = (gauge / 2.0) / math.sin(math.pi / count)
        separation = min_conductor_separation(chord, pitch, count)
        assert (separation < gauge - 1.0e-9) is interferes, (count, gauge, pitch, separation)


def test_the_solved_lay_radius_keeps_every_conductor_clear() -> None:
    for count, gauge, pitch in ((2, 1.0, 10.0), (3, 1.0, 8.0), (4, 1.0, 10.0), (6, 1.2, 15.0)):
        radius = bundle_radius(gauge, count=count, pitch_mm=pitch)
        assert radius >= (gauge / 2.0) / math.sin(math.pi / count) - 1.0e-12
        assert min_conductor_separation(radius, pitch, count) >= gauge


def test_a_lay_below_the_pitch_floor_is_refused_with_the_floor_named() -> None:
    """As the radius grows the closest approach tends to ``pitch / N``, so no
    lay exists at all below ``N * gauge``.  That is a refusal, not a solve."""

    with pytest.raises(BundleError) as refused:
        bundle_radius(1.0, count=6, pitch_mm=5.9)
    assert refused.value.reason == "pitch"
    assert refused.value.observed["minimum_twist_pitch_mm"] == pytest.approx(6.0)

    # Just above the floor a lay exists, however wide.
    assert bundle_radius(1.0, count=6, pitch_mm=6.3) > 0.0


def test_the_default_pitch_is_comfortably_above_the_floor() -> None:
    for count, gauge in ((2, 1.6), (3, 1.0), (4, 0.8), (6, 1.2)):
        pitch = default_twist_pitch(gauge, count=count)
        assert pitch > count * gauge
        # And it lands near the touching radius rather than out on the
        # hyperbola: a real harness lay, not a barely-legal one.
        radius = bundle_radius(gauge, count=count, pitch_mm=pitch)
        assert radius < 1.25 * (gauge / 2.0) / math.sin(math.pi / count)


def test_conductors_of_a_built_lay_stay_a_gauge_apart() -> None:
    """The property the solve exists to guarantee, measured on the polylines."""

    centre = _straight(80.0, 481)
    for count, gauge, pitch in ((2, 1.0, 12.0), (3, 1.0, 10.0), (6, 0.9, 12.0)):
        paths = conductor_paths(
            centre, count=count, style="twisted", gauge_mm=gauge, twist_pitch_mm=pitch
        )
        for first in range(count):
            for second in range(first + 1, count):
                assert _closest_approach(paths[first], paths[second]) >= gauge - 1.0e-6


def test_outer_diameter_covers_the_whole_lay() -> None:
    assert outer_diameter(0.8, count=4, style="flat") == pytest.approx(3.2)
    assert outer_diameter(0.8, count=4, style="flat", spacing_mm=1.5) == pytest.approx(5.3)
    twisted = outer_diameter(1.0, count=3, style="twisted", twist_pitch_mm=20.0)
    assert twisted == pytest.approx(2.0 * bundle_radius(1.0, count=3, pitch_mm=20.0) + 1.0)


def test_sampling_resolves_the_twist_and_stays_bounded() -> None:
    dense = sample_count(200.0, style="twisted", twist_pitch_mm=8.0)
    coarse = sample_count(200.0, style="twisted", twist_pitch_mm=80.0)

    assert dense > coarse
    assert 33 <= coarse and dense <= 1200
    # A 200 mm run at a 0.1 mm pitch is 2000 turns; the count still clamps.
    assert sample_count(200.0, style="twisted", twist_pitch_mm=0.1) == 1200
    assert 33 <= sample_count(4.0, style="flat", cell_mm=1.0) <= 400


# --------------------------------------------------------------------------
# The fan-out
# --------------------------------------------------------------------------


def test_the_fan_out_lands_each_conductor_exactly_on_its_own_port() -> None:
    centre = _straight(60.0, 121)
    starts = [(k * 1.4 - 1.4, 0.0, 0.0) for k in range(3)]
    ends = [(k * 1.4 - 1.4, 0.0, 60.0) for k in range(3)]
    paths = conductor_paths(
        centre,
        count=3,
        style="twisted",
        gauge_mm=1.0,
        twist_pitch_mm=20.0,
        start_points=starts,
        end_points=ends,
        breakout_mm=6.0,
    )

    for index in range(3):
        assert paths[index][0] == pytest.approx(starts[index], abs=1.0e-9)
        assert paths[index][-1] == pytest.approx(ends[index], abs=1.0e-9)


def test_the_middle_of_a_fanned_run_is_still_the_plain_lay() -> None:
    """The breakout is local: past it, the conductors are in the bundle."""

    centre = _straight(60.0, 121)
    plain = conductor_paths(
        centre, count=3, style="twisted", gauge_mm=1.0, twist_pitch_mm=20.0
    )
    fanned = conductor_paths(
        centre,
        count=3,
        style="twisted",
        gauge_mm=1.0,
        twist_pitch_mm=20.0,
        start_points=[(k * 1.4 - 1.4, 0.0, 0.0) for k in range(3)],
        end_points=[(k * 1.4 - 1.4, 0.0, 60.0) for k in range(3)],
        breakout_mm=6.0,
    )

    middle = len(centre) // 2
    for index in range(3):
        assert fanned[index][middle] == pytest.approx(plain[index][middle], abs=1.0e-9)


def test_a_fan_out_needs_one_port_per_conductor() -> None:
    with pytest.raises(BundleError) as refused:
        conductor_paths(
            _straight(),
            count=3,
            style="twisted",
            gauge_mm=1.0,
            start_points=[(0.0, 0.0, 0.0)],
            end_points=[(0.0, 0.0, 100.0)],
        )
    assert refused.value.reason == "count"


def test_the_lay_refuses_what_it_cannot_place() -> None:
    with pytest.raises(BundleError) as style:
        conductor_paths(_straight(), count=2, style="braided", gauge_mm=1.0)
    assert style.value.reason == "path"

    with pytest.raises(BundleError) as single:
        conductor_paths(_straight(), count=1, style="twisted", gauge_mm=1.0)
    assert single.value.reason == "count"

    with pytest.raises(BundleError) as gauge:
        conductor_paths(_straight(), count=2, style="twisted", gauge_mm=0.0)
    assert gauge.value.reason == "path"

    with pytest.raises(BundleError) as empty:
        conductor_paths([(1.0, 2.0, 3.0)], count=2, style="twisted", gauge_mm=1.0)
    assert empty.value.reason == "path"


# --------------------------------------------------------------------------
# The part.bundle contract
# --------------------------------------------------------------------------


PORTS = [
    (((0.0, -1.4, 0.0), (1.0, 0.0, 0.0)), ((40.0, -1.4, 0.0), (-1.0, 0.0, 0.0))),
    (((0.0, 1.4, 0.0), (1.0, 0.0, 0.0)), ((40.0, 1.4, 0.0), (-1.0, 0.0, 0.0))),
]


def test_bundle_is_exported_by_the_part_pack() -> None:
    assert "bundle" in PART_PACK.api_exports
    assert "bundle" in _part().exported_names


def test_bundle_publishes_one_solid_per_conductor() -> None:
    part_api = _part()
    first = part_api.bundle(PORTS, gauge_mm=1.0, conductor=0)
    second = part_api.bundle(PORTS, gauge_mm=1.0, conductor=1)

    assert first.output_type == "solid"
    assert second.output_type == "solid"
    # Same lay, different wire: the payloads differ only in the index, which
    # is what lets the worker share one route between them.
    assert first.to_payload()["properties"]["conductor"] == 0
    assert second.to_payload()["properties"]["conductor"] == 1
    assert first.to_payload()["arguments"] == second.to_payload()["arguments"]


def test_bundle_validates_its_connections_and_options() -> None:
    part_api = _part()

    with pytest.raises(ValueError, match="connections"):
        part_api.bundle([PORTS[0]], gauge_mm=1.0, conductor=0)
    with pytest.raises(ValueError, match="connections"):
        part_api.bundle("not a list", gauge_mm=1.0, conductor=0)
    with pytest.raises(ValueError, match=r"connections\[1\]"):
        part_api.bundle([PORTS[0], (PORTS[1][0],)], gauge_mm=1.0, conductor=0)
    with pytest.raises(ValueError, match="conductor"):
        part_api.bundle(PORTS, gauge_mm=1.0, conductor=2)
    with pytest.raises(ValueError, match="conductor"):
        part_api.bundle(PORTS, gauge_mm=1.0, conductor=-1)
    with pytest.raises(ValueError, match="style"):
        part_api.bundle(PORTS, gauge_mm=1.0, conductor=0, style="braided")
    with pytest.raises(ValueError, match="gauge_mm"):
        part_api.bundle(PORTS, gauge_mm=0.0, conductor=0)
    with pytest.raises(ValueError, match="twist_pitch_mm"):
        part_api.bundle(PORTS, gauge_mm=1.0, conductor=0, twist_pitch_mm=0.0)
    with pytest.raises(ValueError, match="spacing_mm"):
        part_api.bundle(PORTS, gauge_mm=1.0, conductor=0, spacing_mm=-1.0)
    with pytest.raises(ValueError, match="breakout_mm"):
        part_api.bundle(PORTS, gauge_mm=1.0, conductor=0, breakout_mm=0.0)
    with pytest.raises(ValueError, match="up"):
        part_api.bundle(PORTS, gauge_mm=1.0, conductor=0, up=(0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="clearance_mm"):
        part_api.bundle(PORTS, gauge_mm=1.0, conductor=0, clearance_mm=-1.0)
    with pytest.raises(ValueError, match="slack"):
        part_api.bundle(PORTS, gauge_mm=1.0, conductor=0, slack=0.9)
    with pytest.raises(ValueError, match="cell_mm"):
        part_api.bundle(PORTS, gauge_mm=1.0, conductor=0, cell_mm=0.0)
    with pytest.raises(ValueError, match="min_bend_radius_mm"):
        part_api.bundle(PORTS, gauge_mm=1.0, conductor=0, min_bend_radius_mm=0.0)
    with pytest.raises(ValueError, match="avoid"):
        part_api.bundle(PORTS, gauge_mm=1.0, conductor=0, avoid=[{"domain": "part"}])


def test_bundle_refuses_a_connection_whose_two_ports_coincide() -> None:
    same = (((1.0, 2.0, 3.0), (1.0, 0.0, 0.0)), ((1.0, 2.0, 3.0), (-1.0, 0.0, 0.0)))
    with pytest.raises(ValueError, match=r"connections\[1\]"):
        _part().bundle([PORTS[0], same], gauge_mm=1.0, conductor=0)


def test_bundle_refuses_an_obstacle_that_cannot_be_reproduced() -> None:
    """Same contract as ``part.cable``: a decimated obstacle moves every
    rebuild, and a route around a moving obstacle moves the project digest."""

    mesh_api = _mesh()
    decimated = mesh_api.decimate(
        mesh_api.import_file("scan.stl"), tolerance=0.1, reduction=0.5
    )

    with pytest.raises(ValueError, match="decimate"):
        _part().bundle(PORTS, gauge_mm=1.0, conductor=0, avoid=[decimated])


def test_the_bundle_docstring_documents_the_conductor_ordering() -> None:
    """``describe_project_api`` publishes this docstring verbatim as the AI's
    only instructions for the op, so the fan-out rule has to be in it."""

    text = _part().bundle.__doc__ or ""
    assert "conductor" in text
    assert "order of ``connections``" in text
    assert "part.cable" in text


# --------------------------------------------------------------------------
# The geometry, against a real kernel
# --------------------------------------------------------------------------


BUNDLE_SCRIPT = """
lead = [
    (((0.0, -1.4, 0.0), (1.0, 0.0, 0.0)), ((60.0, -1.4, 0.0), (-1.0, 0.0, 0.0))),
    (((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)), ((60.0, 0.0, 0.0), (-1.0, 0.0, 0.0))),
    (((0.0, 1.4, 0.0), (1.0, 0.0, 0.0)), ((60.0, 1.4, 0.0), (-1.0, 0.0, 0.0))),
]
ribbon = [
    (((0.0, k * 1.0 - 1.5, 20.0), (1.0, 0.0, 0.0)),
     ((25.0, k * 1.0 - 1.5, 26.0), (-1.0, 0.0, 0.0)))
    for k in range(4)
]
result = {}
for index in range(3):
    result["phase_%d" % index] = part.bundle(
        lead, gauge_mm=1.0, conductor=index, twist_pitch_mm=20.0
    )
for index in range(4):
    result["ribbon_%d" % index] = part.bundle(
        ribbon, gauge_mm=0.8, conductor=index, style="flat"
    )
"""


#: Run inside ``FreeCADCmd``: build each conductor against the real kernel and
#: report the facts a self-intersecting sweep gets wrong.  ``inspect`` cannot
#: answer this — ``Shape`` is a heavy property it deliberately omits — and a
#: sweep that folds still returns one closed valid solid, so *volume* against
#: the spine length is the only assertion that catches it.
_PROBE = r"""
import json, math, sys
sys.path.insert(0, %(root)r)
import cadex_part_worker as worker
import FreeCAD as App, Part

spines = {}
original = worker._sweep_conductor


def spy(waypoints, **kwargs):
    shape = original(waypoints, **kwargs)
    spines[len(spines)] = (list(waypoints), float(kwargs["gauge"]))
    return shape


worker._sweep_conductor = spy


def payload(connections, conductor, **properties):
    base = {
        "conductor": conductor, "gauge_mm": 1.0, "style": "twisted",
        "left_handed": False, "clearance_mm": 1.0, "slack": 1.05, "avoid": [],
    }
    base.update(properties)
    return {
        "domain": "part", "operation": "bundle", "output_type": "solid",
        "arguments": [connections], "properties": base,
    }


def facts(name, connections, count, **properties):
    worker.reset_part_shape_memo()
    spines.clear()
    entry = {"name": name}
    try:
        shapes = [
            worker.build_part_shape(payload(connections, index, **properties))
            for index in range(count)
        ]
    except Exception as exc:  # a refusal is a result, not a crash
        entry["refused"] = "%%s: %%s" %% (type(exc).__name__, exc)
        return entry
    entry["valid"] = [bool(s.isValid()) for s in shapes]
    entry["solids"] = [len(s.Solids) for s in shapes]
    entry["closed"] = [bool(s.Solids[0].isClosed()) for s in shapes]
    entry["volumes"] = [float(s.Volume) for s in shapes]
    ideal = []
    for index in range(count):
        points, gauge = spines[index]
        curve = Part.BSplineCurve()
        curve.interpolate(
            Points=[App.Vector(*p) for p in points], PeriodicFlag=False, Tolerance=1.0e-7
        )
        ideal.append(math.pi * (gauge / 2.0) ** 2 * curve.toShape().Length)
    entry["ideal"] = ideal
    return entry


# Lists, not tuples: a payload reaches the worker through JSON, and the
# worker validates the shape it will actually be handed.
lead = [
    [[[0.0, k * 1.4 - 1.4, 0.0], [1.0, 0.0, 0.0]],
     [[60.0, k * 1.4 - 1.4, 0.0], [-1.0, 0.0, 0.0]]]
    for k in range(3)
]
ribbon = [
    [[[0.0, k * 1.0 - 1.5, 0.0], [1.0, 0.0, 0.0]],
     [[25.0, k * 1.0 - 1.5, 6.0], [-1.0, 0.0, 0.0]]]
    for k in range(4)
]
pair = [
    [[[0.0, s, 0.0], [1.0, 0.0, 0.0]], [[40.0, s, 12.0], [-1.0, 0.0, 0.0]]]
    for s in (-1.0, 1.0)
]

report = [
    facts("three_phase", lead, 3, twist_pitch_mm=20.0),
    facts("twisted_pair", pair, 2, gauge_mm=1.6, twist_pitch_mm=14.0),
    facts("flat_ribbon", ribbon, 4, style="flat", gauge_mm=0.8),
    facts("impossible_twist", lead, 3, twist_pitch_mm=1.5),
]
open(%(out)r, "w").write(json.dumps(report))
"""


def _kernel_report():
    """Build every conductor under a real kernel and bring back the facts."""

    from test_cadexd_lifecycle import CADEX_ROOT, FREECADCMD

    scratch = pathlib.Path(tempfile.mkdtemp(prefix="cadex-bundle-probe-"))
    out = scratch / "report.json"
    probe = scratch / "probe.py"
    probe.write_text(_PROBE % {"root": str(CADEX_ROOT), "out": str(out)})
    # Read the probe off disk rather than passing it as one -c argument: the
    # script is long and multi-line, and FreeCADCmd does not survive it inline.
    finished = subprocess.run(
        [str(FREECADCMD), "-c", f"exec(open({str(probe)!r}).read())"],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert out.is_file(), finished.stdout[-4000:] + finished.stderr[-4000:]
    return {entry["name"]: entry for entry in json.loads(out.read_text())}


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available to sweep a conductor.",
)
def test_conductors_sweep_into_solids_of_the_right_volume() -> None:
    """Every conductor is one closed solid whose volume matches its spine.

    ``_build_cable`` shipped with no worker-level test at all, so nothing
    exercised the spline fit or the sweep against a real kernel.  A bundle
    puts far more geometry through them, and a sweep that self-intersects
    still returns a closed, valid solid — measured at 51% of the volume
    missing on a six-way lay before the sweep mode was pinned — so volume
    against ``pi * r^2 * spine`` is the assertion that actually catches it.
    """

    report = _kernel_report()

    for name in ("three_phase", "twisted_pair", "flat_ribbon"):
        entry = report[name]
        assert "refused" not in entry, entry
        assert all(entry["valid"]), entry
        assert entry["solids"] == [1] * len(entry["solids"]), entry
        assert all(entry["closed"]), entry
        for volume, ideal in zip(entry["volumes"], entry["ideal"]):
            assert abs(volume - ideal) / ideal < 0.02, entry

    # Conductors of one lay are the same wire in different places.
    phases = report["three_phase"]["volumes"]
    assert (max(phases) - min(phases)) / max(phases) < 0.05, phases


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available to sweep a conductor.",
)
def test_an_impossible_twist_is_refused_rather_than_self_intersected() -> None:
    """A pitch below ``N * gauge`` has no lay at all; the op must say so."""

    entry = _kernel_report()["impossible_twist"]

    assert "refused" in entry, entry
    assert "pitch" in entry["refused"]
    assert "3.000 mm" in entry["refused"], entry["refused"]
