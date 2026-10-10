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
