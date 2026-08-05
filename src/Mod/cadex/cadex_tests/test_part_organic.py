# SPDX-License-Identifier: LGPL-2.1-or-later

"""Three ops with organic leverage (ADR-125, slice O1).

Each one is here because the robot wolf paid for its absence
(``docs/ORGANIC.md`` §1):

- ``ellipse(x_direction=...)`` — the script spent an if/else and up to two
  ``part.transform`` calls **per section**, thirty-odd times, to point a
  major axis somewhere. ``plane`` has taken an ``x_direction`` all along.
- ``sweep(scale_law=...)`` — the tail is five hand-placed tilted circles and
  a loft, because nothing tapered a section along a curve.
- ``fillet(radius_end=...)`` — the two-radius overload was already in the
  binding, unreachable from the script.
"""

from __future__ import annotations

import math
import tempfile

import pytest

import cadex_part_worker as worker
from cadex_part_api import _in_plane_direction, _scale_law


# -- the law, without a kernel ----------------------------------------------


def test_a_law_interpolates_between_its_control_points() -> None:
    law = [[0.0, 1.0], [0.5, 0.5], [1.0, 0.1]]
    assert worker._law_factor(law, 0.0) == 1.0
    assert worker._law_factor(law, 0.25) == pytest.approx(0.75)
    assert worker._law_factor(law, 0.5) == pytest.approx(0.5)
    assert worker._law_factor(law, 0.75) == pytest.approx(0.3)
    assert worker._law_factor(law, 1.0) == pytest.approx(0.1)


def test_a_law_outside_its_range_holds_its_ends() -> None:
    law = [[0.0, 2.0], [1.0, 0.5]]
    assert worker._law_factor(law, -1.0) == 2.0
    assert worker._law_factor(law, 5.0) == 0.5


def test_a_law_must_span_the_path_and_increase() -> None:
    """A half-declared law is a silhouette nobody wrote."""

    assert _scale_law("sweep", [[0, 1], [1, 0.2]]) == [[0.0, 1.0], [1.0, 0.2]]
    for bad, why in (
        ([[0.3, 1], [1, 0.2]], "does not start at 0"),
        ([[0, 1], [0.8, 0.2]], "does not reach 1"),
        ([[0, 1], [0.5, 0.5], [0.4, 0.2], [1, 0.1]], "goes backwards"),
        ([[0, 1]], "is one point"),
        ([[0, 1], [1, 0]], "scales to nothing"),
        ([[0, 1], [1, "x"]], "is not a number"),
    ):
        with pytest.raises(ValueError) as caught:
            _scale_law("sweep", bad)
        assert "scale_law" in str(caught.value), why


def test_an_x_direction_may_not_be_parallel_to_the_normal() -> None:
    assert _in_plane_direction("ellipse", "x_direction", [0, 0, 1], [1, 0, 0]) == [
        0.0, 0.0, 1.0
    ]
    with pytest.raises(ValueError) as caught:
        _in_plane_direction("ellipse", "x_direction", [2, 0, 0], [1, 0, 0])
    assert "parallel" in str(caught.value)


def test_the_api_refuses_a_law_on_ordered_sections() -> None:
    """Two ways to say the same thing, and only one of them is honoured."""

    import CadexScriptedDomains as domains
    from cadex_domain_api import create_domain_api

    pack = domains.get_xscript_pack("PartWorkbench")
    api = create_domain_api(pack.domain, pack.api_exports, pack.output_types)
    spine = api.wire([api.bspline([[0, 0, 0], [0, 50, 0], [0, 90, 40]])])
    profile = api.wire([api.circle(5.0)], closed=True)
    with pytest.raises(ValueError) as caught:
        api.sweep([profile, profile], spine, solid=True,
                  scale_law=[[0, 1.0], [1, 0.2]])
    assert "scale_law" in str(caught.value)


# -- against a live kernel --------------------------------------------------

SEAM_SOURCE = """
bar = part.box(60, 30, 12, origin=[0, 0, 0])
post = part.cylinder(5, 40, origin=[30, 15, 0])
plain = part.fuse([bar, post], label="plain")
welded = part.fuse([bar, post], blend=2.0, label="welded")
result = {"plain": plain, "welded": welded}
"""

NO_SEAM_SOURCE = """
left = part.box(10, 10, 10, origin=[0, 0, 0])
right = part.box(10, 10, 10, origin=[50, 0, 0])
apart = part.fuse([left, right], blend=1.0, output_type="compound", label="apart")
result = {"apart": apart}
"""

TAPER_SOURCE = """
spine = part.wire([part.bspline([[0, 0, 0], [0, 60, 20], [0, 110, 60], [0, 130, 120]])])
profile = part.wire([part.circle(12, center=[0, 0, 0], normal=[0, 0, 1])], closed=True)
tail = part.sweep(profile, spine, solid=True,
                  scale_law=[[0, 1.0], [0.6, 0.55], [1.0, 0.08]], label="tail")
stub = part.sweep(profile, spine, solid=True,
                  scale_law=[[0, 1.0], [1.0, 1.0]], label="stub")
result = {"tail": tail, "stub": stub}
"""

AIM_SOURCE = """
# Two ellipses in the same plane, one aimed and one not. Aimed puts the
# 20 mm major axis along Z; the default puts it wherever +X lands.
aimed = part.face(part.wire([part.ellipse(
    20, 8, center=[0, 0, 0], normal=[1, 0, 0], x_direction=[0, 0, 1])],
    closed=True), label="aimed")
plain = part.face(part.wire([part.ellipse(
    20, 8, center=[0, 0, 0], normal=[1, 0, 0])], closed=True), label="plain")
result = {"aimed": aimed, "plain": plain}
"""

TAPERED_BLEND_SOURCE = """
block = part.box(40, 40, 20)
even = part.fillet(block, 3.0, label="even")
tapered = part.fillet(block, 1.0, radius_end=6.0, label="tapered")
result = {"even": even, "tapered": tapered}
"""


def _live():
    from test_cadexd_lifecycle import FREECADCMD

    return FREECADCMD is not None


def _client_write(client, source: str, prefix: str):
    client.request("open_project", {"project_root": tempfile.mkdtemp(prefix=prefix)})
    return client.request("write_script", {"source": source, "expected_revision": ""})


def _available(client, output: str, kind: str):
    probe = client.request(
        "resolve_pin",
        {"output": output, "selection": {"element_type": kind, "expected_count": 0}},
    )
    return ((probe.get("observed") or {}).get("available")) or []


@pytest.mark.skipif(not _live(), reason="No FreeCADCmd binary available.")
def test_a_fuse_blends_the_seam_it_just_made() -> None:
    """The operation §1's second failure needed and could not write.

    The seam set is not a selector a script can declare: how many
    intersection curves a boolean produced is knowable only to the boolean.
    Here it is one — the circle where the post enters the bar — and blending
    it adds exactly one toroidal face to the eight the union has.
    """

    from test_cadexd_lifecycle import _spawn_cadexd, _stop

    client = None
    try:
        client = _spawn_cadexd()
        written = _client_write(client, SEAM_SOURCE, "cadexd-seam-")
        assert written["ok"] is True, written

        plain = _available(client, "plain", "face")
        welded = _available(client, "welded", "face")
        assert len(plain) == 8, plain
        assert len(welded) == 9, welded
        kinds = sorted(face["geometry_type"] for face in welded)
        assert kinds.count("Toroid") == 1, kinds
        # ...and only the seam was touched: the bar's six planes and the
        # post's end disc are all still there, unrounded, which is what
        # edges="all" could never express.
        assert kinds.count("Plane") == 7, kinds

        refused = _client_write(client, NO_SEAM_SOURCE, "cadexd-noseam-")
        assert refused["ok"] is False, refused
        assert "no seam" in str(refused.get("error")), refused
    finally:
        _stop(client)


@pytest.mark.skipif(not _live(), reason="No FreeCADCmd binary available.")
def test_a_swept_law_tapers_and_a_flat_law_does_not() -> None:
    """The tail, in one call instead of five hand-placed circles."""

    from test_cadexd_lifecycle import _spawn_cadexd, _stop

    client = None
    try:
        client = _spawn_cadexd()
        written = _client_write(client, TAPER_SOURCE, "cadexd-taper-")
        assert written["ok"] is True, written

        tail = _available(client, "tail", "solid")
        stub = _available(client, "stub", "solid")
        assert len(tail) == 1 and len(stub) == 1, (tail, stub)
        tapered_volume = float(tail[0]["volume_mm3"])
        even_volume = float(stub[0]["volume_mm3"])
        # A law that ends at 0.08 must remove most of the material, and the
        # flat law must remove none: a taper that did nothing would still
        # produce a solid, and only the comparison catches that.
        assert 0.2 < tapered_volume / even_volume < 0.6, (
            tapered_volume, even_volume)
    finally:
        _stop(client)


@pytest.mark.skipif(not _live(), reason="No FreeCADCmd binary available.")
def test_an_ellipse_aims_its_major_axis() -> None:
    """Measured on the face's own bounding box, not on the arguments."""

    from test_cadexd_lifecycle import _spawn_cadexd, _stop

    client = None
    try:
        client = _spawn_cadexd()
        written = _client_write(client, AIM_SOURCE, "cadexd-aim-")
        assert written["ok"] is True, written
        aimed = _available(client, "aimed", "face")
        plain = _available(client, "plain", "face")
        assert len(aimed) == 1 and len(plain) == 1
        # Same area either way — this is an orientation, not a resize.
        assert float(aimed[0]["area_mm2"]) == pytest.approx(
            float(plain[0]["area_mm2"]), rel=1e-6)
        assert float(aimed[0]["area_mm2"]) == pytest.approx(
            math.pi * 20.0 * 8.0, rel=1e-3)
    finally:
        _stop(client)


@pytest.mark.skipif(not _live(), reason="No FreeCADCmd binary available.")
def test_a_variable_radius_blend_is_not_the_even_one() -> None:
    """One argument, and the transition stops being machined."""

    from test_cadexd_lifecycle import _spawn_cadexd, _stop

    client = None
    try:
        client = _spawn_cadexd()
        written = _client_write(client, TAPERED_BLEND_SOURCE, "cadexd-vary-")
        assert written["ok"] is True, written
        even = _available(client, "even", "solid")
        tapered = _available(client, "tapered", "solid")
        assert len(even) == 1 and len(tapered) == 1
        # 1 -> 6 mm along each edge removes a different amount of material
        # from a 40x40x20 block than an even 3 mm does.
        assert float(tapered[0]["volume_mm3"]) != pytest.approx(
            float(even[0]["volume_mm3"]), rel=1e-4)
        assert float(tapered[0]["volume_mm3"]) < 40.0 * 40.0 * 20.0
    finally:
        _stop(client)
