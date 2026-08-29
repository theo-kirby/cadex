# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The section cage: ``cage(...)``, ``section_cage(...)``, ``ring(...)`` and
``part.loft_cage`` (ADR-127).

The robot wolf's script *is already* a section table, spelled as literals
inside three helper functions (`docs/ORGANIC.md` §1) — and the ring that
actually spoiled that model survived eleven revisions because nobody could
grab it. So the rings become a declared table, the fifth of its kind, with
the same properties every one of them has: canonical millimetres,
`units=` as declaration-time convenience, stored rows that replace
wholesale, and drift pruned rather than refused.

What is new here is the **superellipse exponent**, so most of what follows
is about the profile: at 2.0 it must be exactly an ellipse, because that is
what makes the exponent a continuous knob rather than a mode.
"""

from __future__ import annotations

import math
import tempfile

import pytest

from CadexCage import (
    MAX_RINGS,
    RING_FIELDS,
    CageError,
    CageSet,
    CagesCollector,
    canonical_ring_rows,
    declared_cages,
    declared_ring_rows,
    effective_rings,
    prune_ring_rows,
    ring,
    ring_points,
    section_cage,
)


def _torso(**overrides):
    rows = overrides.pop("rings", None) or [
        ring(0, 30, 38, exponent=2.4),
        ring(120, 46, 52, exponent=3.0),
        ring(300, 34, 40, exponent=2.2),
    ]
    return section_cage(rows, **overrides)


def _table(overrides=None):
    collector = CagesCollector(overrides)
    return collector, collector({"torso": _torso()})


def _row(cage_name: str, position: float, **overrides):
    row = {
        "cage": cage_name,
        "position": position,
        "half_width": 20.0,
        "half_height": 25.0,
        "roll": 0.0,
        "exponent": 2.0,
    }
    row.update(overrides)
    return row


# --------------------------------------------------------------------------
# declaration
# --------------------------------------------------------------------------


def test_a_declared_cage_is_its_rings_in_order() -> None:
    _collector, table = _table()
    assert table.names == ("torso",)
    torso = table["torso"]
    assert isinstance(torso, CageSet)
    assert len(torso) == 3
    assert [row["position"] for row in torso] == [0.0, 120.0, 300.0]
    assert torso.length == 300.0
    assert torso.axis == [1.0, 0.0, 0.0]


def test_the_spec_cache_is_json_and_flat() -> None:
    import json

    collector, _value = _table()
    encoded = json.loads(json.dumps(collector.specs))
    entry = encoded["cages"][0]
    assert entry["name"] == "torso"
    assert entry["axis"] == [1.0, 0.0, 0.0]
    assert set(entry["rings"][0]) == set(RING_FIELDS) - {"cage"}


def test_a_metre_declaration_is_stored_in_millimetres() -> None:
    collector = CagesCollector()
    table = collector({
        "leg": section_cage(
            [ring(0, 0.02, 0.03), ring(0.28, 0.012, 0.016)],
            axis=(0, 0, -1), origin=(0.0, 0.0, 0.28), units="m",
        )
    })
    rows = table["leg"].rows
    assert [row["position"] for row in rows] == [0.0, 280.0]
    assert rows[0]["half_width"] == pytest.approx(20.0)
    assert table["leg"].origin == pytest.approx([0.0, 0.0, 280.0])


def test_rings_must_run_along_the_axis_in_order() -> None:
    """A loft through a table that doubles back is not a shape anyone asked
    for, and the refusal is cheaper than the self-intersecting solid."""

    with pytest.raises(CageError) as caught:
        section_cage([ring(0, 10, 10), ring(50, 10, 10), ring(20, 10, 10)])
    assert "does not come after" in str(caught.value)


def test_a_cage_needs_two_rings_to_loft_between() -> None:
    with pytest.raises(CageError) as caught:
        section_cage([ring(0, 10, 10)])
    assert "at least two" in str(caught.value)


def test_the_exponent_is_bounded_and_positive_dimensions_required() -> None:
    with pytest.raises(CageError) as caught:
        ring(0, 10, 10, exponent=40.0)
    assert "2.0 is an ellipse" in str(caught.value)
    with pytest.raises(CageError):
        ring(0, 0.0, 10)
    with pytest.raises(CageError):
        ring(0, 10, -1)


def test_an_up_along_the_axis_is_refused() -> None:
    with pytest.raises(CageError) as caught:
        section_cage([ring(0, 10, 10), ring(20, 10, 10)],
                     axis=(0, 0, 1), up=(0, 0, 1))
    assert "parallel" in str(caught.value)


def test_the_table_is_immutable_and_callable_once() -> None:
    collector, table = _table()
    with pytest.raises(CageError):
        table.anything = 1
    with pytest.raises(CageError) as caught:
        collector({"torso": _torso()})
    assert "once" in str(caught.value)


def test_the_table_is_bounded() -> None:
    with pytest.raises(CageError) as caught:
        section_cage([ring(index, 10, 10) for index in range(MAX_RINGS + 1)])
    assert str(MAX_RINGS) in str(caught.value)


def test_a_row_must_be_declared_with_ring() -> None:
    with pytest.raises(CageError) as caught:
        section_cage([{"position": 0, "half_width": 1, "half_height": 1},
                      ring(10, 5, 5)])
    assert "not a ring(...)" in str(caught.value)


# --------------------------------------------------------------------------
# the superellipse
# --------------------------------------------------------------------------


def test_exponent_two_is_exactly_an_ellipse() -> None:
    """The property that makes the exponent a knob and not a mode."""

    points = ring_points(_row("c", 0.0, half_width=30.0, half_height=12.0),
                         samples=32)
    assert len(points) == 32
    for point in points:
        # axis is +X, up is +Z: the section lies in the YZ plane.
        assert point[0] == pytest.approx(0.0, abs=1e-9)
        y, z = point[1], point[2]
        assert (y / 30.0) ** 2 + (z / 12.0) ** 2 == pytest.approx(1.0, abs=1e-9)


def test_a_higher_exponent_fills_the_corners_out() -> None:
    """What the number is *for*: area, at the same half-width and height."""

    def area(exponent):
        points = ring_points(
            _row("c", 0.0, half_width=20.0, half_height=20.0,
                 exponent=exponent),
            samples=256,
        )
        # Shoelace in the section plane (y, z).
        total = 0.0
        for index, point in enumerate(points):
            other = points[(index + 1) % len(points)]
            total += point[1] * other[2] - other[1] * point[2]
        return abs(total) / 2.0

    ellipse = area(2.0)
    assert ellipse == pytest.approx(math.pi * 400.0, rel=1e-3)
    muscled = area(4.0)
    boxy = area(8.0)
    square = 40.0 * 40.0
    assert ellipse < muscled < boxy < square
    # ...and it is a real difference, not a rounding one: an exponent of 4
    # adds about a tenth of the bounding square.
    assert (muscled - ellipse) / square > 0.05


def test_a_ring_sits_on_its_station_and_rolls_in_its_own_plane() -> None:
    row = _row("c", 75.0, half_width=10.0, half_height=4.0, roll=90.0)
    points = ring_points(row, axis=(1, 0, 0), origin=(5, 0, 0), samples=64)
    assert all(point[0] == pytest.approx(80.0) for point in points)
    # Rolled a quarter turn, the 10 mm half-width now runs up rather than across.
    heights = [abs(point[2]) for point in points]
    widths = [abs(point[1]) for point in points]
    assert max(heights) == pytest.approx(10.0, abs=1e-6)
    assert max(widths) == pytest.approx(4.0, abs=1e-6)


def test_a_cage_can_point_anywhere() -> None:
    row = _row("c", 100.0, half_width=6.0, half_height=6.0)
    points = ring_points(row, axis=(0, 0, -1), origin=(0, 0, 300),
                         up=(0, 1, 0), samples=16)
    assert all(point[2] == pytest.approx(200.0) for point in points)
    assert max(abs(point[0]) for point in points) == pytest.approx(6.0, abs=1e-6)


# --------------------------------------------------------------------------
# the stored half
# --------------------------------------------------------------------------


def test_a_stored_row_may_not_smuggle_an_unknown_column() -> None:
    with pytest.raises(CageError) as caught:
        canonical_ring_rows([_row("torso", 0.0, twist=4)], what="v")
    assert "unrecognised keys" in str(caught.value)


def test_stored_rings_replace_that_cage_wholesale() -> None:
    collector, _value = _table()
    stored = [_row("torso", 0.0), _row("torso", 200.0)]
    effective = effective_rings(collector.specs, stored)
    assert [row["position"] for row in effective] == [0.0, 200.0]


def test_a_cage_nobody_edited_keeps_its_declared_rings() -> None:
    """Wholesale per cage, not per project: a stored list that mentions one
    cage is not a statement about the others."""

    collector = CagesCollector()
    collector({"torso": _torso(),
               "tail": section_cage([ring(0, 8, 8), ring(100, 2, 2)])})
    effective = effective_rings(collector.specs, [_row("torso", 0.0)])
    by_cage = {}
    for row in effective:
        by_cage.setdefault(row["cage"], []).append(row)
    assert len(by_cage["torso"]) == 1
    assert len(by_cage["tail"]) == 2


def test_a_row_naming_a_dropped_cage_is_pruned_not_raised_on() -> None:
    collector, _value = _table()
    stored = [_row("torso", 0.0), _row("gone", 0.0)]
    kept = prune_ring_rows(canonical_ring_rows(stored, what="v"), collector.specs)
    assert [row["cage"] for row in kept] == ["torso"]


def test_the_collector_applies_the_overrides_to_the_geometry() -> None:
    """What the loft sees is what the editor dragged, not what was declared."""

    dragged = [
        _row("torso", 0.0, half_width=30.0, half_height=38.0),
        _row("torso", 120.0, half_width=20.0, half_height=52.0),
        _row("torso", 300.0, half_width=34.0, half_height=40.0),
    ]
    collector = CagesCollector(dragged)
    table = collector({"torso": _torso()})
    assert [row["half_width"] for row in table["torso"]] == [30.0, 20.0, 34.0]


def test_stored_rows_are_sorted_onto_the_spine() -> None:
    """An editor that appends a dragged ring must not reorder the loft."""

    collector = CagesCollector([
        _row("torso", 300.0), _row("torso", 0.0), _row("torso", 120.0),
    ])
    with pytest.raises(CageError):
        # ...but out-of-order *rows* are still a refusal on the way in: the
        # sorting below is about the payload, not about hiding a bad table.
        collector({"torso": _torso()})


def test_declared_cages_reads_the_cache_back() -> None:
    collector, _value = _table()
    cages = declared_cages(collector.specs)
    assert list(cages) == ["torso"]
    assert len(declared_ring_rows(collector.specs)) == 3


def test_the_payload_is_the_frame_plus_the_rows() -> None:
    _collector, table = _table()
    payload = table["torso"].to_payload()
    assert set(payload) == {"cage", "axis", "origin", "up", "rings"}
    assert len(payload["rings"]) == 3


# --------------------------------------------------------------------------
# against a live kernel
# --------------------------------------------------------------------------

CAGE_SOURCE = """
p = params(waist=num(46, unit="mm", min=20, max=80, label="Waist"))

c = cage({
    "torso": section_cage([
        ring(0, 30, 38, exponent=2.4),
        ring(120, p.waist, 52, exponent=3.0),
        ring(300, 34, 40, exponent=2.2),
    ], axis=(1, 0, 0)),
    "round": section_cage([
        ring(0, 20, 20),
        ring(100, 20, 20),
    ], axis=(0, 0, 1), origin=(500, 0, 0)),
    "boxy": section_cage([
        ring(0, 20, 20, exponent=8.0),
        ring(100, 20, 20, exponent=8.0),
    ], axis=(0, 0, 1), origin=(600, 0, 0)),
})

result = {
    "torso": part.loft_cage(c["torso"], solid=True),
    "round": part.loft_cage(c["round"], solid=True),
    "boxy": part.loft_cage(c["boxy"], solid=True),
}
"""


def _live():
    from test_cadexd_lifecycle import FREECADCMD

    return FREECADCMD is not None


@pytest.mark.skipif(not _live(), reason="No FreeCADCmd binary available.")
def test_a_cage_lofts_and_its_exponent_changes_the_volume() -> None:
    """End to end: the table builds, and the exponent is doing real work.

    Two cages with identical rings and different exponents must differ by
    the amount the profile arithmetic predicts — a cylinder of half-width 20
    is pi*20^2*100, a superellipse of exponent 8 is most of the way to the
    40x40x100 box.
    """

    from test_cadexd_lifecycle import _spawn_cadexd, _stop

    client = None
    try:
        client = _spawn_cadexd()
        client.request(
            "open_project", {"project_root": tempfile.mkdtemp(prefix="cadexd-cage-")}
        )
        written = client.request(
            "write_script", {"source": CAGE_SOURCE, "expected_revision": ""}
        )
        assert written["ok"] is True, written

        def volume(name):
            probe = client.request(
                "resolve_pin",
                {"output": name,
                 "selection": {"element_type": "solid", "expected_count": 0}},
            )
            solids = ((probe.get("observed") or {}).get("available")) or []
            assert len(solids) == 1, (name, solids)
            return float(solids[0]["volume_mm3"])

        round_volume = volume("round")
        boxy_volume = volume("boxy")
        assert round_volume == pytest.approx(math.pi * 400.0 * 100.0, rel=0.02)
        assert boxy_volume > round_volume * 1.15
        assert boxy_volume < 40.0 * 40.0 * 100.0

        # ...and the table rides its parameters, which is what makes it a
        # cage rather than a mesh.
        before = volume("torso")
        moved = client.request(
            "set_params",
            {"values": {"waist": 60.0},
             "expected_revision": written["revision"]},
        )
        assert moved["ok"] is True, moved
        assert volume("torso") > before
    finally:
        _stop(client)
