# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The parts library (ADR-181): catalog pins, generator recipes, staging.

The catalog pins assert the standard's numbers — a failure here means the
data drifted from ISO 4762/4032/7089, DIN 7991/985 or the bearing tables,
not that a tolerance moved. The recipe tests walk the DomainValue tree the
generators compose, so they run under the stubbed suite with no kernel.
"""

from __future__ import annotations

import math
import tempfile

import pytest

import CadexCatalog as catalog
from CadexCatalog import CatalogError
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import DomainValue, create_domain_api
from cadex_library_api import (
    LibraryAPI,
    LibraryError,
    LibraryPart,
    create_library_api,
    library_listing,
)

PART_PACK = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]


def _part():
    return create_domain_api(
        PART_PACK.domain, PART_PACK.api_exports, PART_PACK.output_types
    )


def _lib():
    return create_library_api(_part())


def _walk(value):
    """Every DomainValue in a recipe tree, root first."""

    if isinstance(value, DomainValue):
        yield value
        for argument in value.arguments:
            yield from _walk(argument)
        for property_value in value.properties.values():
            yield from _walk(property_value)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk(item)


def _ops(value, operation):
    return [node for node in _walk(value) if node.operation == operation]


# -- catalog pins -----------------------------------------------------------


def test_metric_thread_pins() -> None:
    m3 = catalog.thread_spec("M3")
    assert m3["nominal_dia_mm"] == 3.0
    assert m3["pitch_mm"] == 0.5
    assert m3["minor_dia_mm"] == 2.459
    assert m3["tap_drill_mm"] == 2.5
    assert m3["clearance_close_mm"] == 3.2
    assert m3["clearance_normal_mm"] == 3.4
    assert catalog.thread_spec("m8")["pitch_mm"] == 1.25


def test_fastener_head_and_nut_pins() -> None:
    assert catalog.socket_head_spec("m3") == {
        "head_dia_mm": 5.5,
        "head_height_mm": 3.0,
        "socket_mm": 2.5,
    }
    assert catalog.countersunk_spec("m4") == {
        "head_dia_mm": 8.0,
        "head_height_mm": 2.3,
    }
    assert catalog.hex_nut_spec("m5") == {"across_flats_mm": 8.0, "height_mm": 4.7}
    assert catalog.nyloc_nut_spec("m3")["height_mm"] == 4.0
    assert catalog.washer_spec("m3") == {
        "bore_mm": 3.2,
        "od_mm": 7.0,
        "thickness_mm": 0.5,
    }
    assert catalog.heat_set_insert_spec("m3")["od_mm"] == 4.6
    assert catalog.heat_set_insert_spec("m3")["hole_dia_mm"] == 4.0


def test_bearing_pins() -> None:
    assert catalog.bearing_spec("608") == {
        "bore_mm": 8.0,
        "od_mm": 22.0,
        "width_mm": 7.0,
    }
    assert catalog.bearing_spec("625")["od_mm"] == 16.0
    assert catalog.bearing_spec("mr105") == {
        "bore_mm": 5.0,
        "od_mm": 10.0,
        "width_mm": 4.0,
    }


def test_normalisation_and_refusals() -> None:
    assert catalog.normalise_thread_size(" M3 ") == "m3"
    assert catalog.normalise_bearing_code("608ZZ") == "608"
    assert catalog.normalise_bearing_code("688-2RS") == "688"
    with pytest.raises(CatalogError) as caught:
        catalog.thread_spec("m7")
    assert "m3" in str(caught.value)
    with pytest.raises(CatalogError):
        catalog.bearing_spec("999")
    with pytest.raises(CatalogError):
        catalog.normalise_thread_size(3)
    with pytest.raises(CatalogError):
        catalog.nyloc_nut_spec("m2")  # catalogued from m3 up


# -- hole data --------------------------------------------------------------


def test_hole_helpers() -> None:
    lib = _lib()
    assert lib.clearance_hole("m3") == 3.4
    assert lib.clearance_hole("m3", fit="close") == 3.2
    assert lib.tap_drill("m4") == 3.3
    assert lib.insert_hole("m3") == 4.0
    with pytest.raises(LibraryError):
        lib.clearance_hole("m3", fit="loose")


# -- fastener recipes -------------------------------------------------------


def test_socket_bolt_recipe_and_spec() -> None:
    bolt = _lib().bolt("m3", 10)
    assert isinstance(bolt, LibraryPart)
    assert bolt.family == "bolt"
    assert bolt.part_number == "m3x10-socket"
    assert bolt.body.domain == "part"
    assert bolt.body.operation == "fuse"
    radii = sorted(node.arguments[0] for node in _ops(bolt.body, "cylinder"))
    assert radii == [1.5, 2.75]
    shank = min(_ops(bolt.body, "cylinder"), key=lambda node: node.arguments[0])
    assert shank.arguments[1] == 10.0
    assert tuple(shank.properties["origin"]) == (0.0, 0.0, -10.0)
    assert bolt.spec["head_height_mm"] == 3.0
    assert bolt.spec["length_mm"] == 10.0
    assert bolt.spec["density_kg_m3"] == catalog.STEEL_DENSITY_KG_M3


def test_countersunk_bolt_recipe_and_floor() -> None:
    lib = _lib()
    bolt = lib.bolt("m3", 8, head="countersunk")
    cones = _ops(bolt.body, "cone")
    assert len(cones) == 1
    assert cones[0].arguments == (1.5, 3.0, 1.7)
    assert tuple(cones[0].properties["origin"]) == (0.0, 0.0, -1.7)
    with pytest.raises(LibraryError):
        lib.bolt("m3", 1.5, head="countersunk")
    with pytest.raises(LibraryError):
        lib.bolt("m3", 10, head="pan")


def test_nut_recipes() -> None:
    lib = _lib()
    nut = lib.nut("m3")
    assert nut.body.operation == "cut"
    prism = _ops(nut.body, "prism")[0]
    assert prism.arguments[0] == 6
    assert prism.arguments[1] == pytest.approx(5.5 / math.sqrt(3.0))
    assert prism.arguments[2] == 2.4
    bore = _ops(nut.body, "cylinder")[0]
    assert bore.arguments[0] == pytest.approx(2.459 / 2.0)
    nyloc = lib.nut("m3", style="nyloc")
    assert _ops(nyloc.body, "prism")[0].arguments[2] == 4.0
    with pytest.raises(LibraryError):
        lib.nut("m3", style="wing")


def test_washer_insert_recipes() -> None:
    lib = _lib()
    washer = lib.washer("m3")
    radii = sorted(node.arguments[0] for node in _ops(washer.body, "cylinder"))
    assert radii == [1.6, 3.5]
    insert = lib.heat_insert("m3")
    sleeve = max(_ops(insert.body, "cylinder"), key=lambda node: node.arguments[0])
    assert sleeve.arguments == (2.3, 5.7)
    short = lib.heat_insert("m3", length="short")
    assert short.spec["length_selected_mm"] == 4.0
    with pytest.raises(LibraryError):
        lib.heat_insert("m3", length="stubby")


# -- bearings and bushings --------------------------------------------------


def test_bearing_recipes_and_refusals() -> None:
    lib = _lib()
    bearing = lib.bearing("608zz")
    assert bearing.part_number == "608"
    radii = sorted(node.arguments[0] for node in _ops(bearing.body, "cylinder"))
    assert radii == [4.0, 11.0]
    custom = lib.bearing(bore=6.0, od=12.0, width=4.0)
    assert custom.part_number == "custom-6x12x4"
    with pytest.raises(LibraryError):
        lib.bearing("608", bore=8.0)
    with pytest.raises(LibraryError):
        lib.bearing(bore=8.0, od=22.0)
    with pytest.raises(LibraryError):
        lib.bearing(bore=22.0, od=8.0, width=7.0)


def test_bushing_recipes_and_refusals() -> None:
    lib = _lib()
    plain = lib.bushing(bore=8.0, od=10.0, length=6.0)
    assert plain.body.operation == "cut"
    flanged = lib.bushing(
        bore=8.0, od=10.0, length=6.0, flange_od=14.0, flange_thickness=1.0
    )
    assert _ops(flanged.body, "fuse")
    assert flanged.spec["flange_od_mm"] == 14.0
    with pytest.raises(LibraryError):
        lib.bushing(bore=8.0, od=10.0, length=6.0, flange_od=14.0)
    with pytest.raises(LibraryError):
        lib.bushing(bore=8.0, od=10.0, length=6.0, flange_od=9.0, flange_thickness=1.0)
    with pytest.raises(LibraryError):
        lib.bushing(bore=8.0, od=10.0, length=6.0, flange_od=14.0, flange_thickness=7.0)
    with pytest.raises(LibraryError):
        lib.bushing(bore=10.0, od=8.0, length=6.0)


# -- placement --------------------------------------------------------------


def test_default_placement_adds_no_transform() -> None:
    assert _lib().nut("m3").body.operation == "cut"


def test_placement_composes_one_transform() -> None:
    lib = _lib()
    turned = lib.nut("m3", origin=(5.0, 0.0, 2.0), direction=(1.0, 0.0, 0.0))
    assert turned.body.operation == "transform"
    assert tuple(turned.body.properties["translation"]) == (5.0, 0.0, 2.0)
    assert tuple(turned.body.properties["rotation_axis"]) == (0.0, 1.0, 0.0)
    assert turned.body.properties["rotation_degrees"] == pytest.approx(90.0)
    flipped = lib.nut("m3", direction=(0.0, 0.0, -1.0))
    assert flipped.body.properties["rotation_degrees"] == pytest.approx(180.0)
    moved = lib.nut("m3", origin=(1.0, 2.0, 3.0))
    assert moved.body.properties["rotation_degrees"] == 0.0
    with pytest.raises(LibraryError):
        lib.nut("m3", direction=(0.0, 0.0, 0.0))
    with pytest.raises(LibraryError):
        lib.nut("m3", origin=(1.0, 2.0))


# -- the object contract ----------------------------------------------------


def test_library_part_is_immutable() -> None:
    nut = _lib().nut("m3")
    with pytest.raises(TypeError):
        nut.body = None
    with pytest.raises(TypeError):
        nut.spec["height_mm"] = 99.0


def test_create_library_api_wants_the_part_api() -> None:
    with pytest.raises(RuntimeError):
        create_library_api(object())


# -- servos -----------------------------------------------------------------


def _assembly_api():
    from cadex_assembly_api import AssemblyDomainAPI

    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return AssemblyDomainAPI(pack.api_exports, pack.output_types)


def _servo_lib():
    return create_library_api(_part(), _assembly_api())


def test_servo_spec_pins() -> None:
    sg90 = catalog.servo_spec("SG90")
    assert sg90["mass_g"] == 9.0
    assert sg90["hole_dia_mm"] == 2.2
    assert sg90["hole_spacing_mm"] == 29.0
    assert sg90["flange_height_mm"] == 15.9
    assert sg90["shaft_offset_from_front_mm"] == 8.75
    assert sg90["stall_torque"] == [{"volts": 4.8, "kg_cm": 1.8}]
    assert sg90["approximate"] == []
    mg996r = catalog.servo_spec("mg996r")
    assert mg996r["mass_g"] == 55.0
    assert mg996r["hole_spacing_mm"] == 49.5
    assert mg996r["hole_cross_spacing_mm"] == 10.0
    assert {"volts": 6.0, "kg_cm": 11.0} in mg996r["stall_torque"]
    ds = catalog.servo_spec("ds3218")
    assert ds["mass_g"] == 60.0
    assert {"volts": 5.0, "kg_cm": 19.0} in ds["stall_torque"]
    # A field no datasheet dimensions says so instead of passing as measured.
    assert "hole_spacing_mm" in catalog.servo_spec("mg90s")["approximate"]
    with pytest.raises(CatalogError) as caught:
        catalog.servo_spec("sg92r")
    assert "mg996r" in str(caught.value)


def test_servo_recipe_micro() -> None:
    servo = _servo_lib().servo("sg90")
    assert servo.family == "servo"
    assert servo.part_number == "sg90"
    assert servo.body.operation == "cut"
    boxes = _ops(servo.body, "box")
    assert len(boxes) == 2
    case = next(box for box in boxes if box.arguments[0] == 22.7)
    assert case.arguments == (22.7, 12.1, 27.1)
    assert tuple(case.properties["origin"]) == (8.75 - 22.7, -6.05, -27.1)
    plate = next(box for box in boxes if box.arguments[0] == 32.4)
    assert plate.arguments[2] == 2.4
    assert plate.properties["origin"][2] == pytest.approx(15.9 - 27.1)
    cylinders = _ops(servo.body, "cylinder")
    spline = next(c for c in cylinders if c.arguments[0] == 2.4)
    assert spline.arguments[1] == 3.6
    drills = [c for c in cylinders if c.arguments[0] == pytest.approx(1.1)]
    assert len(drills) == 2
    drill_x = sorted(d.properties["origin"][0] for d in drills)
    centre_x = 8.75 - 22.7 / 2.0
    assert drill_x == [
        pytest.approx(centre_x - 14.5),
        pytest.approx(centre_x + 14.5),
    ]
    assert servo.spec["mount_holes"] == [
        [pytest.approx(centre_x - 14.5), 0.0],
        [pytest.approx(centre_x + 14.5), 0.0],
    ]


def test_servo_recipe_standard_has_four_holes() -> None:
    servo = _servo_lib().servo("ds3218")
    drills = [
        c
        for c in _ops(servo.body, "cylinder")
        if c.arguments[0] == pytest.approx(2.25)
    ]
    assert len(drills) == 4
    assert sorted({d.properties["origin"][1] for d in drills}) == [-5.0, 5.0]


def test_servo_derived_numbers() -> None:
    servo = _servo_lib().servo("mg90s")
    torque = servo.spec["stall_torque_nmm"]
    assert torque[0] == {
        "volts": 4.8,
        "nmm": pytest.approx(1.8 * catalog.KG_CM_TO_NMM),
    }
    density = servo.spec["effective_density_kg_m3"]
    # 13.4 g in a body about 8.3 cm^3: much lighter than solid plastic would
    # be wrong, much heavier than aluminium would be wrong.
    assert 1000.0 < density < 3000.0
    volume = (
        22.8 * 12.2 * 28.4
        + (32.5 - 22.8) * 12.2 * 2.4
        + math.pi * 2.45**2 * 4.0
        - 2 * math.pi * 1.1**2 * 2.4
    )
    assert density == pytest.approx(13.4e6 / volume)


def test_servo_placement_carries_roll() -> None:
    from cadex_library_api import _quaternion, _rotate

    servo = _servo_lib().servo(
        "sg90", origin=(10.0, 0.0, 5.0), direction=(0.0, 1.0, 0.0),
        roll_degrees=90.0,
    )
    assert servo.body.operation == "transform"
    axis = servo.body.properties["rotation_axis"]
    angle = servo.body.properties["rotation_degrees"]
    rotated_z = _rotate(_quaternion(axis, angle), (0.0, 0.0, 1.0))
    assert rotated_z == (
        pytest.approx(0.0, abs=1e-9),
        pytest.approx(1.0),
        pytest.approx(0.0, abs=1e-9),
    )
    # The roll must survive the one composed rotation: +90 about the shaft
    # sends local +X to +Y, and aiming +Z at +Y then carries it to -Z.
    rotated_x = _rotate(_quaternion(axis, angle), (1.0, 0.0, 0.0))
    assert rotated_x == (
        pytest.approx(0.0, abs=1e-9),
        pytest.approx(0.0, abs=1e-9),
        pytest.approx(-1.0),
    )


def test_servo_horn_recipes() -> None:
    lib = _servo_lib()
    servo = lib.servo("sg90")
    horn = servo.horn()
    assert horn.family == "servo_horn"
    assert horn.part_number == "sg90-single_arm"
    # Default placement seats the hub on the spline top.
    assert horn.body.operation == "transform"
    assert tuple(horn.body.properties["translation"]) == (0.0, 0.0, 3.6)
    hub = next(
        c for c in _ops(horn.body, "cylinder") if c.arguments[0] == pytest.approx(3.45)
    )
    assert hub.arguments[1] == 2.5
    link_holes = [
        c for c in _ops(horn.body, "cylinder") if c.arguments[0] == pytest.approx(0.5)
    ]
    assert len(link_holes) == 6
    bore = [
        c for c in _ops(horn.body, "cylinder") if c.arguments[0] == pytest.approx(2.4)
    ]
    assert len(bore) == 1
    cross = servo.horn("cross")
    assert len(_ops(cross.body, "box")) == 2
    assert len(
        [c for c in _ops(cross.body, "cylinder") if c.arguments[0] == pytest.approx(0.5)]
    ) == 12
    with pytest.raises(LibraryError):
        servo.horn("wheel")
    with pytest.raises(LibraryError):
        lib.servo("mg996r").horn()


def test_servo_actuator_carries_the_datasheet_torque() -> None:
    lib = _servo_lib()
    api = _assembly_api()
    base = api.component({"document_uid": "doc", "object_name": "base"}, grounded=True)
    arm = api.component({"document_uid": "doc", "object_name": "arm"})
    joint = api.joint("revolute", api.connector(base), api.connector(arm))
    servo = lib.servo("mg90s")
    actuator = servo.actuator(joint, control_deg="30")
    payload = actuator.properties
    expected = 1.8 * catalog.KG_CM_TO_NMM
    assert payload["torque_limit_nmm"] == pytest.approx(expected)
    assert payload["stiffness_nmm_per_deg"] == pytest.approx(expected / 5.0)
    assert payload["damping_nmms_per_deg"] == pytest.approx(expected / 100.0)
    high = servo.actuator(joint, control_deg="30", voltage=6.6)
    assert high.properties["torque_limit_nmm"] == pytest.approx(
        2.2 * catalog.KG_CM_TO_NMM
    )
    with pytest.raises(LibraryError) as caught:
        servo.actuator(joint, control_deg="30", voltage=5.0)
    assert "4.8" in str(caught.value)
    unstaged = create_library_api(_part()).servo("mg90s")
    with pytest.raises(LibraryError):
        unstaged.actuator(joint, control_deg="30")


# -- browsing and describe_api ----------------------------------------------


def test_catalog_browse_shape() -> None:
    families = _lib().catalog()
    assert set(families) >= {"fasteners", "heat_set_inserts", "bearings"}
    assert "608" in families["bearings"]["codes"]
    assert "m3" in families["fasteners"]["sizes"]


def test_library_listing_serves_exports_and_catalog() -> None:
    listing = library_listing()
    assert listing["api_global"] == "lib"
    names = {entry["name"] for entry in listing["exports"]}
    assert {
        "bolt",
        "nut",
        "washer",
        "heat_insert",
        "bearing",
        "bushing",
        "clearance_hole",
        "tap_drill",
        "insert_hole",
        "catalog",
    } <= names
    for entry in listing["exports"]:
        assert entry["signature"].startswith("(")
        assert entry["description"]
    assert "608" in listing["catalog"]["bearings"]["codes"]


def test_describe_project_api_carries_the_library() -> None:
    from CadexScriptedRuntime import describe_project_api

    payload = describe_project_api()
    assert "lib" in payload["source_globals"]
    assert payload["library"]["api_global"] == "lib"
    assert payload["library"]["exports"]


_KERNEL_SCRIPT = """
servo = lib.servo("mg90s", origin=(0, 30, 0), direction=(0, 0, 1))
big = lib.servo("ds3218", origin=(60, 0, 0), direction=(1, 0, 0),
                roll_degrees=30)
result = {
    "servo": servo.body,
    "horn": servo.horn("double_arm").body,
    "big_servo": big.body,
    "bolt": lib.bolt("m3", 10).body,
    "flat_head": lib.bolt("m4", 12, head="countersunk").body,
    "nut": lib.nut("m3", origin=(0, 20, 0)).body,
    "nyloc": lib.nut("m5", style="nyloc", direction=(1, 0, 0)).body,
    "washer": lib.washer("m3").body,
    "insert": lib.heat_insert("m3").body,
    "bearing": lib.bearing("608zz").body,
    "bushing": lib.bushing(bore=8, od=10, length=6,
                           flange_od=14, flange_thickness=1).body,
}
"""


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available for a kernel build.",
)
def test_the_library_builds_on_the_real_kernel() -> None:
    """End to end: every L0 generator survives OCCT, not just the recipe.

    The recipe tests prove the tree the generators compose; only the kernel
    proves a hex prism cuts cleanly, a cone fuses onto a shank, and every
    result is a closed solid the worker can serialize.
    """

    from test_cadexd_lifecycle import _spawn_cadexd, _stop

    client = None
    try:
        client = _spawn_cadexd()
        client.request(
            "open_project",
            {"project_root": tempfile.mkdtemp(prefix="cadexd-library-")},
        )
        written = client.request(
            "write_script",
            {"source": _KERNEL_SCRIPT, "expected_revision": ""},
            timeout=600.0,
        )
        assert written["ok"] is True, written
        names = {output["name"] for output in written["outputs"]}
        assert names == {
            "servo",
            "horn",
            "big_servo",
            "bolt",
            "flat_head",
            "nut",
            "nyloc",
            "washer",
            "insert",
            "bearing",
            "bushing",
        }
        for output in written["outputs"]:
            assert output["type"] == "solid", output
    finally:
        if client is not None:
            _stop(client)


def test_worker_stages_lib() -> None:
    import cadex_project_worker as project_worker

    api_contracts = {}
    for pack in XSCRIPT_WORKBENCH_PACKS.values():
        api_contracts[pack.domain] = {
            "exports": list(pack.api_exports),
            "output_types": list(pack.output_types),
        }
    globals_by_name, *_ = project_worker._staged_globals(api_contracts, {}, {})
    assert isinstance(globals_by_name["lib"], LibraryAPI)
    bolt = globals_by_name["lib"].bolt("m3", 12)
    assert bolt.body.domain == "part"
