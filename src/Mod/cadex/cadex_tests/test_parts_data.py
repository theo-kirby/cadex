# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Machine parts as data (ADR-646): CadexParts.json and ``lib.part``.

Every row is a part number of a family, and every family names the one
interface that builds it. These pin the numbers that come from a standard
or a datasheet, the numbers derived from them (a pulley's pitch radius, a
spring's rate, a cylinder's two forces), and that every row in the file
builds -- so a new part number is a data change this file checks.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

import CadexCatalog as catalog
import CadexMachineParts
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import DomainValue, create_domain_api
from cadex_library_api import LibraryError, MachinePart, create_library_api, library_listing

PART_PACK = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]


def _lib():
    return create_library_api(create_domain_api(
        PART_PACK.domain, PART_PACK.api_exports, PART_PACK.output_types))


#: What each interface needs to be called with.
OPTIONS = {
    "rail": {"length": 300.0}, "profile": {"length": 400.0}, "screw": {"length": 250.0},
    "belt": {"span": 300.0, "pitch_radius": 6.366}, "cylinder": {"extension": 10.0},
}


def test_every_row_builds_and_states_its_source() -> None:
    lib = _lib()
    rows = catalog.PARTS_DATA["index"]
    assert len(rows) >= 40
    for sku, family in rows.items():
        interface = catalog.PARTS_DATA["families"][family]["interface"]
        part = lib.part(sku, **OPTIONS.get(interface, {}))
        assert isinstance(part, MachinePart) and isinstance(part.body, DomainValue)
        assert part.spec["sources"] and part.spec["approximate"]
        assert part.spec["datums"], sku
        if "density_kg_m3" in part.spec:
            # A pneumatic tyre is mostly air: its body is solid, so ~200.
            assert 100.0 < part.spec["density_kg_m3"] < 20000.0, (sku, part.spec["density_kg_m3"])


def test_every_family_is_built_by_a_known_interface() -> None:
    raw = json.loads((Path(catalog.__file__).with_name("CadexParts.json")).read_text())
    assert set(CadexMachineParts.BUILDERS) == set(catalog.PART_INTERFACES)
    for family, entry in raw["families"].items():
        assert entry["interface"] in CadexMachineParts.BUILDERS, family
        for sku, row in entry["rows"].items():
            assert set(entry["fields"]) <= set(row), sku


def test_gt2_pulley_numbers_are_the_profiles() -> None:
    spec = _lib().part("gt2-20t-5mm").spec
    assert spec["pitch_dia_mm"] == pytest.approx(40.0 / math.pi)
    assert spec["outside_dia_mm"] == pytest.approx(40.0 / math.pi - 0.508)
    assert spec["belt_mm_per_degree"] == pytest.approx(40.0 / 360.0)


def test_nema_faces_are_the_standards() -> None:
    lib = _lib()
    for sku, frame, holes, pilot in (("nema17-40", 42.3, 31.0, 22.0),
                                     ("nema23-56", 56.4, 47.14, 38.1)):
        spec = lib.part(sku).spec
        assert (spec["frame_mm"], spec["hole_spacing_mm"], spec["pilot_dia_mm"]) == (frame, holes, pilot)
    assert lib.part("nema17-40").spec["rotor_inertia_kgmm2"] == 5.4


def test_a_cylinder_pushes_bore_area_and_pulls_annulus_area() -> None:
    part = _lib().part("iso6020-40x250", extension=50.0)
    spec = part.spec
    assert spec["extend_force_n"] == pytest.approx(120e5 * math.pi * 0.040 ** 2 / 4.0)
    assert spec["retract_force_n"] == pytest.approx(120e5 * math.pi * (0.040 ** 2 - 0.018 ** 2) / 4.0)
    assert spec["mount_centres_mm"][1][2] == pytest.approx(250.0 + 230.0 + 50.0)
    assert set(part.members) == {"barrel", "rod"}
    with pytest.raises(LibraryError, match="extension"):
        _lib().part("iso6020-40x250", extension=300.0)


def test_a_spring_rate_is_computed_from_its_wire_and_coils() -> None:
    spec = _lib().part("spring-2x20x60").spec
    assert spec["rate_n_per_mm"] == pytest.approx(81500.0 * 2.0 ** 4 / (8.0 * 18.0 ** 3 * 8.0))
    assert spec["solid_length_mm"] == 20.0


def test_a_tyre_code_is_its_dimensions() -> None:
    spec = _lib().part("13x5.00-6").spec
    assert spec["outer_dia_mm"] == pytest.approx(13 * 25.4)
    assert spec["rim_dia_mm"] == pytest.approx(6 * 25.4)


def test_a_rail_needs_a_length_and_a_pulley_takes_none() -> None:
    lib = _lib()
    with pytest.raises(LibraryError, match="length"):
        lib.part("mgnr12")
    with pytest.raises(LibraryError, match="does not take length"):
        lib.part("gt2-20t-5mm", length=10.0)
    with pytest.raises(LibraryError, match="Unknown part"):
        lib.part("mgn15h")
    rail = lib.part("mgnr12", length=300.0).spec
    assert rail["mounting_holes"] == 12  # 10, 35, ... 285, 290 is past 300 - 10


def test_the_catalog_lists_the_machine_parts_by_family() -> None:
    """The part numbers ride on MachinePart's description (section=library_parts)."""

    listing = library_listing()
    assert "section=library_parts" in listing["catalog"]["machine_parts"]["notes"]
    assert "part" in [item["name"] for item in listing["exports"]]
    head = MachinePart.__doc__.split("\n\n", 1)[0]
    assert "linear_carriages: mgn12c, mgn12h, mgn9c, mgn9h" in head
    assert "extrusions: 2020, 2040" in head


def test_an_unknown_option_is_refused_by_name() -> None:
    with pytest.raises(LibraryError, match="no option 'lenght'"):
        _lib().part("mgnr12", lenght=100.0)


def test_m10_and_m12_fasteners_are_the_standards() -> None:
    assert catalog.thread_spec("m12")["pitch_mm"] == 1.75
    assert catalog.SOCKET_HEAD_SCREWS["m10"]["head_dia_mm"] == 16.0
    assert catalog.HEX_NUTS["m12"]["across_flats_mm"] == 18.0
    bolt = _lib().bolt("m10", length=40)
    assert bolt.spec["head_dia_mm"] == 16.0


# --------------------------------------------------------------------------
# mounting holes (ADR-660) and the slot (ADR-661)
# --------------------------------------------------------------------------


def _axes(part):
    from cadex_library_api import _definition_key, library_mount_facts

    return library_mount_facts()["axes"].get(_definition_key(part.body), [])


#: Every machine part with mounting holes: what fits them and how many.
HOLES = {
    "mgnr12": ("hole_dia_mm", 3.5, 4), "mgnr9": ("hole_dia_mm", 3.5, 5),
    "mgn12h": ("thread_dia_mm", 3.0, 4), "mgn9c": ("thread_dia_mm", 3.0, 4),
    "nema17-40": ("thread_dia_mm", 3.0, 4), "nema23-76": ("thread_dia_mm", 5.0, 4),
    "t8-flange-nut-lead8": ("hole_dia_mm", 3.5, 4), "sfu1204-nut": ("hole_dia_mm", 4.5, 6),
    "2020-tnut-m5": ("thread_dia_mm", 5.0, 1), "2020-tnut-m3": ("thread_dia_mm", 3.0, 1),
    "2020-corner-bracket": ("hole_dia_mm", 5.5, 2), "gt2-20t-5mm": ("hole_dia_mm", 5.0, 1),
    "gt2-20t-idler-3mm": ("hole_dia_mm", 3.0, 1), "caster-50": ("hole_dia_mm", 6.0, 4),
}


def test_every_machine_part_with_holes_publishes_them_with_what_fits() -> None:
    lib = _lib()
    for sku, (key, size, count) in HOLES.items():
        part = lib.part(sku, length=100.0) if sku.startswith("mgnr") else lib.part(sku)
        axes = _axes(part)
        assert len(axes) == count == len(part.spec["mount_points"]), sku
        assert {row[key] for row in axes} == {size}, sku
        other = {"hole_dia_mm": "thread_dia_mm", "thread_dia_mm": "hole_dia_mm"}[key]
        assert all(other not in row and "output" not in row for row in axes), sku
    # A part with no holes publishes none (the stamp writes an empty list).
    assert _axes(lib.part("er11-52-500w")) == []
    # A caster's holes are on its yoke too, which a mechanism places apart.
    caster = lib.part("caster-50")
    assert len(_axes(caster.members["yoke"])) == 4 and _axes(caster.members["wheel"]) == []


def test_the_holes_are_where_the_datasheets_put_them() -> None:
    lib = _lib()
    rail = lib.part("mgnr12", length=300.0).spec
    # Centred: 12 holes 25 apart leave 12.5 at each end (E 10 at least).
    zs = [row["origin"][2] for row in rail["mount_points"]]
    assert rail["end_offset_mm"] == pytest.approx(12.5) and zs[0] == pytest.approx(12.5)
    assert zs[-1] == pytest.approx(287.5) and len(zs) == rail["mounting_holes"] == 12
    assert all(row["origin"][1] == pytest.approx(8.0 - 4.5) for row in rail["mount_points"])
    carriage = lib.part("mgn12h").spec
    assert sorted((p["origin"][0], p["origin"][2]) for p in carriage["mount_points"]) == [
        (-10.0, -10.0), (-10.0, 10.0), (10.0, -10.0), (10.0, 10.0)]
    assert {p["origin"][1] for p in carriage["mount_points"]} == {13.0}
    motor = lib.part("nema17-48").spec
    assert sorted(tuple(p["origin"]) for p in motor["mount_points"]) == [
        (-15.5, -15.5, 0.0), (-15.5, 15.5, 0.0), (15.5, -15.5, 0.0), (15.5, 15.5, 0.0)]
    # The ball nut's six holes keep off its 30 mm flats.
    nut = lib.part("sfu1204-nut").spec
    assert all(abs(p["origin"][1]) + 2.25 < 15.0 for p in nut["mount_points"])
    assert all(math.hypot(*p["origin"][:2]) == pytest.approx(16.0) for p in nut["mount_points"])


def test_the_holes_ride_the_parts_placement() -> None:
    motor = _lib().part("nema17-40", origin=(100.0, 0.0, 50.0), direction=(0.0, 0.0, -1.0))
    axes = _axes(motor)
    # Flipped about X onto -Z: local (x, y, 0) -> (100 + x, -y, 50).
    assert sorted(tuple(round(v, 6) for v in row["origin"]) for row in axes)[0] == (
        84.5, -15.5, 50.0)
    assert all(row["axis"] == pytest.approx([0.0, 0.0, -1.0]) for row in axes)


def _inside(polygon, point, margin):
    """``point`` lies inside ``polygon`` with ``margin`` to every edge."""

    x, y = point
    crossings, nearest = 0, float("inf")
    for (ax, ay), (bx, by) in zip(polygon, polygon[1:] + polygon[:1]):
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            crossings += 1
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        nearest = min(nearest, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return crossings % 2 == 1 and nearest >= margin - 1e-9


def test_a_catalog_t_nut_fits_the_catalog_slot() -> None:
    """ADR-661: the wave-1 liquid handler found the 10 mm T-nut wider than
    the 8 mm modelled undercut. The slot is now the B-type's and the nut a
    slide-in nut's section: every corner of it below the clamp face is
    inside the slot by the 0.1 mm clearance floor."""
    lib = _lib()
    for profile in ("2020", "2040"):
        p = lib.part(profile, length=100.0).spec
        o, d, iw, lip, wall = (p[k] for k in ("slot_opening_mm", "slot_depth_mm",
                                              "slot_inner_width_mm", "lip_mm", "slot_wall_mm"))
        assert (o, iw, d) == (6.2, 11.0, 6.1)
        bottom = iw / 2.0 - (d - lip - wall)
        # The slot as (across, height above the lip's underside).
        slot = [(-o / 2, lip), (o / 2, lip), (o / 2, 0.0), (iw / 2, 0.0), (iw / 2, -wall),
                (bottom, lip - d), (-bottom, lip - d), (-iw / 2, -wall), (-iw / 2, 0.0),
                (-o / 2, 0.0)]
        for sku in ("2020-tnut-m3", "2020-tnut-m5"):
            n = lib.part(sku).spec
            w, h, nw, nh, c = (n[k] for k in ("width_mm", "height_mm", "neck_width_mm",
                                              "neck_height_mm", "chamfer_mm"))
            nut = [(-nw / 2, nh), (nw / 2, nh), (-(w / 2 - c), -h), (w / 2 - c, -h),
                   (w / 2, -(h - c)), (-w / 2, -(h - c))]
            for corner in nut:
                assert _inside(slot, corner, 0.1), (profile, sku, corner)
            # The clamp face's ends bear on the lip's underside, inside the undercut.
            assert w / 2 + 0.1 <= iw / 2 and nw / 2 + 0.1 <= o / 2 and nh < lip


def test_slot_places_a_t_nut_on_the_slot_of_a_placed_profile() -> None:
    import cadex_library_api as api

    lib = _lib()
    # A 2040 lying along +X.
    beam = lib.part("2040", length=300.0, origin=(0.0, 0.0, 10.0), direction=(1.0, 0.0, 0.0))
    datums = {(row["face"], row["index"]) for row in beam.spec["slot_datums"]}
    assert datums == {("+y", 0), ("+y", 1), ("-y", 0), ("-y", 1), ("+x", 0), ("-x", 0)}
    seat = beam.slot("+x", 40.0)
    nut = lib.part("2020-tnut-m5", **seat)
    # The nut's +X runs along the profile (world +X), its +Z out of the slot.
    frame = lib._frame("part", seat["origin"], seat["direction"], seat["roll_degrees"])
    assert api._rotate(frame[2], (1.0, 0.0, 0.0)) == pytest.approx((1.0, 0.0, 0.0), abs=1e-9)
    (face,) = api._frame_axes(beam._frame_placement, [((0.0, 0.0, 40.0), (1.0, 0.0, 0.0))])
    assert seat["direction"] == pytest.approx(face["axis"])
    assert seat["origin"] == pytest.approx([v + 18.2 * a for v, a in zip(face["origin"], face["axis"])])
    assert _axes(nut)[0]["axis"] == pytest.approx(seat["direction"])
    with pytest.raises(LibraryError, match="face must be one of"):
        beam.slot("+z", 10.0)
    with pytest.raises(LibraryError, match="index"):
        beam.slot("+x", 10.0, index=1)
    with pytest.raises(LibraryError, match="along"):
        beam.slot("+y", 400.0)
    with pytest.raises(LibraryError, match="no slots"):
        lib.part("mgn12h").slot()
