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


def test_servo_joint_dynamics_is_the_datasheet_torque_speed_line() -> None:
    lib = _servo_lib()
    api = _assembly_api()
    base = api.component({"document_uid": "doc", "object_name": "base"}, grounded=True)
    arm = api.component({"document_uid": "doc", "object_name": "arm"})
    joint = api.joint("revolute", api.connector(base), api.connector(arm))
    servo = lib.servo("mg90s")
    stall = 1.8 * catalog.KG_CM_TO_NMM
    dynamics = servo.joint_dynamics(joint, friction_loss_nmm=2.0)
    # 4.8 V is the only voltage the MG90S rates for both: 0.10 s per 60 deg.
    damping = dynamics.properties["damping_nmms_per_deg"]
    assert damping == pytest.approx(stall / 600.0)
    assert dynamics.properties["friction_loss_nmm"] == 2.0
    with pytest.raises(LibraryError, match="4.8 V"):
        servo.joint_dynamics(joint, voltage=6.0)

    # The claim, in MuJoCo itself: a light link driven flat out by the servo's
    # own actuator settles at the datasheet no-load speed, not above it.
    mujoco = pytest.importorskip("mujoco")
    actuator = servo.actuator(joint, control_deg="0").properties
    per_deg = 180.0 / math.pi / 1000.0  # N*mm per deg -> N*m per rad
    model = mujoco.MjModel.from_xml_string(f"""
<mujoco><option timestep="0.0005"/><worldbody><body>
  <joint name="j" type="hinge" damping="{damping * per_deg}"/>
  <geom type="capsule" fromto="0 0 0 0.02 0 0" size="0.002" mass="0.002"/>
</body></worldbody><actuator>
  <position joint="j" kp="{actuator['stiffness_nmm_per_deg'] * per_deg}"
            kv="{actuator['damping_nmms_per_deg'] * per_deg}"
            forcerange="-{stall / 1000.0} {stall / 1000.0}" forcelimited="true"/>
</actuator></mujoco>""")
    data = mujoco.MjData(model)
    data.ctrl[0] = 100.0  # far enough that the actuator saturates throughout
    for _ in range(400):
        mujoco.mj_step(model, data)
    assert math.degrees(data.qvel[0]) == pytest.approx(600.0, rel=0.02)


@pytest.mark.parametrize("sku,count", [("esp32-devkitc-v4", 38),
                                       ("pi-zero-2-w", 40),
                                       ("pca9685-adafruit-rev-c", 62),
                                       ("bno085-adafruit-4754", 12),
                                       ("pololu-d36v50f6", 12),
                                       ("pi-5", 40),
                                       ("rpi-camera-module-3", 0),
                                       ("pololu-vl53l1x-3415", 7),
                                       ("tb6612-adafruit-2448", 18)])
def test_board_interfaces_and_terminal_rows(sku, count):
    board = _lib().board(sku)
    spec = board.spec
    assert board.family == "board"
    rows = board.terminals()
    assert len(rows) == count
    assert len({r["name"] for r in rows}) == count
    assert all(r["axis"] == [0.0, 0.0, -1.0] for r in rows)
    assert len(_ops(board.body, "cylinder")) == count + len(spec["mount_holes"])
    assert all(0 < r["origin"][0] < spec["width_mm"] and
               0 < r["origin"][1] < spec["length_mm"] for r in rows)
    assert "https://" in spec["source"]
    assert "density_kg_m3" in spec["approximate"]
    # A script can mutate its copy without poisoning a later generation.
    if spec["mount_holes"]:
        spec["mount_holes"][0][0] = -999
        assert catalog.board_spec(sku)["mount_holes"][0][0] > 0
    if count:
        spec["terminals"][0]["origin"][0] = -999
        assert catalog.board_spec(sku)["terminals"][0]["origin"][0] > 0


def test_board_manufacturer_dimension_pins():
    esp = catalog.board_spec(" ESP32-DEVKITC-V4 ")
    assert (esp["width_mm"], esp["length_mm"]) == (27.94, 48.26)
    assert esp["mount_holes"] == []
    assert esp["terminals"][0]["signal"] == "3V3"
    assert esp["terminals"][18]["origin"] == [1.24, 1.29, 1.6]
    pi = catalog.board_spec("pi-zero-2-w")
    assert pi["mount_holes"] == [[3.5, 3.5], [3.5, 26.5], [61.5, 3.5], [61.5, 26.5]]
    assert pi["terminals"][2]["signal"] == "GPIO2"
    assert "terminal_origins" in pi["approximate"]
    pca = catalog.board_spec("pca9685-adafruit-rev-c")
    assert (pca["width_mm"], pca["length_mm"], pca["mount_hole_dia_mm"]) == (62.23, 25.4, 2.5)
    assert pca["mount_holes"] == [[3.175, 3.175], [3.175, 22.225], [59.055, 3.175], [59.055, 22.225]]
    rows = {r["name"]: r for r in pca["terminals"]}
    assert rows["jp3_3"]["signal"] == "SDA"
    assert rows["pwm0_pwm"]["origin"] == [6.985, 6.477, 1.6]
    assert rows["pwm15_gnd"]["origin"] == [55.245, 1.397, 1.6]
    assert rows["j1_1"]["signal"] == "V+_IN"
    with pytest.raises(CatalogError, match="Unknown board"):
        _lib().board("generic-esp32")


def test_imu_and_regulator_manufacturer_pins():
    """ADR-407: the pins a robot's brain, sensor and power are wired by."""
    imu = catalog.board_spec("bno085-adafruit-4754")
    assert (imu["width_mm"], imu["length_mm"], imu["mount_hole_dia_mm"]) == (25.4, 22.86, 2.5)
    assert imu["mount_holes"] == [[2.54, 2.54], [2.54, 20.32], [22.86, 2.54], [22.86, 20.32]]
    rows = {r["name"]: r for r in imu["terminals"]}
    assert rows["jp1_4"]["signal"] == "SCL" and rows["jp1_5"]["signal"] == "SDA"
    assert rows["jp1_1"]["origin"] == [6.35, 2.54, 1.6]
    assert imu["mass_g"] == 2.5 and "be9dc998" in imu["source"]
    reg = catalog.board_spec("pololu-d36v50f6")
    assert (reg["width_mm"], reg["thickness_mm"], reg["output_voltage_v"]) == (25.4, 1.57, 6.0)
    assert len(reg["mount_holes"]) == 3 and reg["mount_hole_dia_mm"] == 2.18
    rows = {r["name"]: r for r in reg["terminals"]}
    assert rows["vin_1"]["signal"] == "VIN" and rows["vout_2"]["origin"] == [6.35, 3.81, 1.57]
    assert rows["en"]["signal"] == "EN" and rows["pg"]["origin"][1] == 3.81
    assert "terminal_signals" in reg["approximate"]


def test_orun1_board_manufacturer_pins():
    """ADR-485: a Linux brain, a camera and a range sensor, from their drawings."""
    pi = catalog.board_spec("pi-5")
    assert (pi["width_mm"], pi["length_mm"], pi["mount_hole_dia_mm"]) == (85.0, 56.0, 2.7)
    assert pi["mount_holes"] == [[3.5, 3.5], [3.5, 52.5], [61.5, 3.5], [61.5, 52.5]]
    rows = {r["name"]: r for r in pi["terminals"]}
    assert rows["j8_1"]["origin"] == [8.37, 51.23, 1.45] and rows["j8_1"]["signal"] == "3V3"
    assert rows["j8_2"]["origin"] == [8.37, 53.77, 1.45]
    assert rows["j8_40"]["signal"] == "GPIO21"
    # The port stacks overhang the +X edge by 3 mm and stand 16 mm proud.
    (mx, _my, _mz), (sx, _sy, sz) = pi["cosmetic_origin"], pi["cosmetic_size"]
    assert mx + sx == pytest.approx(88.0) and sz == 16.0
    assert "rpi5" in pi["source"] and "thickness_mm" in pi["approximate"]
    cam = catalog.board_spec("rpi-camera-module-3")
    assert (cam["width_mm"], cam["length_mm"], cam["thickness_mm"]) == (25.0, 23.862, 1.12)
    assert cam["mount_holes"] == [[2.0, 2.0], [2.0, 14.5], [23.0, 2.0], [23.0, 14.5]]
    assert cam["mount_hole_dia_mm"] == 2.2 and cam["lens_centre"] == [12.5, 14.4]
    assert cam["fov_degrees"]["horizontal"] == 66.0 and cam["terminals"] == []
    # The lens envelope tops out where the drawing's barrel tip is.
    assert cam["cosmetic_origin"][2] + cam["cosmetic_size"][2] == pytest.approx(8.55)
    tof = catalog.board_spec("pololu-vl53l1x-3415")
    assert (tof["width_mm"], tof["length_mm"], tof["mount_hole_dia_mm"]) == (12.7, 17.78, 2.18)
    assert [r["signal"] for r in tof["terminals"]] == "VDD VIN GND SDA SCL XSHUT GPIO1".split()
    assert tof["range_mm"] == [40.0, 4000.0] and tof["fov_degrees"]["full"] == 27.0
    assert "mount_holes" in tof["approximate"]
    for spec in (pi, cam, tof):
        assert spec["sources"] and all(u.startswith("https://") for u in spec["sources"])


def test_motor_driver_manufacturer_pins():
    """ADR-490: the H-bridge two N20s need, from Adafruit's published board."""
    drv = catalog.board_spec("tb6612-adafruit-2448")
    assert (drv["width_mm"], drv["length_mm"], drv["mount_hole_dia_mm"]) == (19.05, 26.67, 2.5)
    assert drv["mount_holes"] == [[16.51, 2.54], [16.51, 24.13]]
    rows = {r["name"]: r for r in drv["terminals"]}
    assert rows["jp1_1"]["origin"] == [2.54, 24.765, 1.6] and rows["jp1_1"]["signal"] == "VM"
    assert rows["jp1_10"]["origin"] == [2.54, 1.905, 1.6] and rows["jp1_10"]["signal"] == "PWMA"
    assert [rows[f"jp1_{i}"]["signal"] for i in (4, 5, 6, 7, 8, 9)] == \
        "PWMB BIN2 BIN1 STBY AIN1 AIN2".split()
    assert [rows[f"jp3_{i}"]["signal"] for i in range(1, 7)] == "MA1 MA2 GND GND MB2 MB1".split()
    assert rows["jp3_1"]["origin"] == [17.78, 6.985, 1.6] and rows["jp3_1"]["hole_dia"] == 1.016
    assert (rows["j1_1"]["signal"], rows["j1_2"]["origin"]) == ("VM", [11.098, 23.114, 1.6])
    # The TB6612's SSOP24 body, rotated 90 degrees, stands to the stated 3 mm.
    (mx, my, mz), (sx, sy, sz) = drv["cosmetic_origin"], drv["cosmetic_size"]
    assert (mx + sx / 2, my + sy / 2) == (pytest.approx(9.906), pytest.approx(14.986))
    assert mz + sz == pytest.approx(3.0)
    # Drives a 2S pack's motors directly, and two N20s at stall.
    assert drv["motor_voltage_range_v"][0] <= 7.4 <= drv["motor_voltage_range_v"][1]
    n20 = catalog.gearmotor_spec("pololu-2367")
    assert drv["channels"] == 2 and drv["continuous_current_a"] >= n20["stall_current_a"]
    assert "514d5ded" in drv["source"] and drv["mass_g"] == 1.8


def test_camera_bay_reaches_the_block_on_its_back_face():
    cam = _lib().board("rpi-camera-module-3")
    low, high = _box_extents(cam.bay())
    assert low[2] == pytest.approx(-2.75 - 1.0)
    assert high[2] == pytest.approx(8.55 + 1.0 + 8.0)
    # A deeper underside than the part needs is still the caller's.
    assert _box_extents(cam.bay(underside=5))[0][2] == pytest.approx(-6.0)


def test_sts3215_spec_pins():
    """ADR-485: the bus servo's datasheet numbers, and what is not dimensioned."""
    sts = catalog.servo_spec(" STS3215 ")
    assert (sts["body_length_mm"], sts["body_width_mm"], sts["case_height_mm"]) == (45.22, 24.72, 29.0)
    assert sts["envelope_height_mm"] == 35.0 and sts["shaft_offset_from_front_mm"] == 10.11
    assert (sts["spline_teeth"], sts["spline_dia_mm"], sts["spline_height_mm"]) == (25, 5.9, 3.4)
    assert sts["stall_torque"] == [{"volts": 6.0, "kg_cm": 16.5}, {"volts": 7.4, "kg_cm": 19.5}]
    assert sts["speed"][1] == {"volts": 7.4, "s_per_60_deg": 0.192}
    assert sts["mass_g"] == 55.0 and sts["travel_degrees"] == 360.0
    assert sts["mount_faces"][0] == {"face": "output", "x_from_axis_mm": [8.30, -29.00],
                                     "y_mm": [-10.25, 10.25]}
    assert "hole_depth_mm" in sts["approximate"]
    assert all(u.startswith("https://") for u in sts["sources"])
    sts["mount_faces"][0]["y_mm"][0] = 99.0
    assert catalog.servo_spec("sts3215")["mount_faces"][0]["y_mm"][0] == -10.25


def test_sts3215_recipe_is_held_by_its_case_holes():
    servo = _servo_lib().servo("sts3215")
    boxes = _ops(servo.body, "box")
    assert len(boxes) == 1  # no tab plate
    assert boxes[0].arguments == (45.22, 24.72, 29.0)
    assert tuple(boxes[0].properties["origin"]) == pytest.approx((10.11 - 45.22, -12.36, -29.0))
    drills = [c for c in _ops(servo.body, "cylinder") if c.arguments[0] == pytest.approx(1.0)]
    assert len(drills) == 8
    points = servo.spec["mount_points"]
    assert len(points) == 8
    output = [p for p in points if p["face"] == "output"]
    rear = [p for p in points if p["face"] == "rear"]
    assert {p["origin"][2] for p in output} == {0.0} and {p["origin"][2] for p in rear} == {-29.0}
    assert all(p["axis"] == [0.0, 0.0, -1.0] for p in output)
    assert all(p["axis"] == [0.0, 0.0, 1.0] for p in rear)
    assert sorted({p["origin"][0] for p in rear}) == [-32.75, 8.30]
    assert servo.spec["mount_holes"] == [p["origin"][:2] for p in output]
    # The idler boss stands below the rear face on the shaft axis.
    boss = next(c for c in _ops(servo.body, "cylinder") if c.arguments == (3.0, 4.1))
    assert tuple(boss.properties["origin"]) == (0.0, 0.0, -33.1)
    assert 1000.0 < servo.spec["effective_density_kg_m3"] < 2000.0
    with pytest.raises(LibraryError, match="bus"):
        servo.horn()


def test_sts3215_bay_keeps_its_faces_and_reserves_the_lead():
    servo = _servo_lib().servo("sts3215")
    boxes = _boxes(servo.bay())
    back = 10.11 - 45.22
    assert ((back - 0.5, -12.86, -29.5), (10.61, 12.86, 0.5)) in [
        (pytest.approx(lo), pytest.approx(hi)) for lo, hi in boxes]
    assert ((back - 6.5, -12.86, -29.5), (back - 0.5, 12.86, 0.5)) in [
        (pytest.approx(lo), pytest.approx(hi)) for lo, hi in boxes]
    columns = sorted(c.arguments for c in _ops(servo.bay(), "cylinder"))
    assert columns == [(pytest.approx(3.45), 3.4), (pytest.approx(3.5), 4.1)]
    assert len(_boxes(servo.bay(lead_room=0))) == 1
    placed = _servo_lib().servo("sts3215", origin=(5, 0, 0), direction=(1, 0, 0))
    assert placed.bay().properties == placed.body.properties
    assert catalog_identity_of(servo.bay()) is None


def test_sts3215_actuator_carries_its_bus_voltage_torque():
    calls = []

    class _Assembly:
        def actuator(self, joint, **kwargs):
            calls.append(kwargs)
            return kwargs

        def joint_dynamics(self, joint, **kwargs):
            calls.append(kwargs)
            return kwargs

    lib = create_library_api(_part(), _Assembly())
    servo = lib.servo("sts3215")
    servo.actuator("j", control_deg="a", voltage=7.4)
    assert calls[-1]["torque_limit_nmm"] == pytest.approx(19.5 * catalog.KG_CM_TO_NMM)
    servo.joint_dynamics("j", voltage=7.4)
    assert calls[-1]["damping_nmms_per_deg"] == pytest.approx(
        19.5 * catalog.KG_CM_TO_NMM / (60.0 / 0.192))


def test_wheel_spec_recipe_and_bay():
    """ADR-485: a tyred wheel that presses onto the catalogued N20's D shaft."""
    spec = catalog.wheel_spec("POLOLU-1430")
    assert (spec["tyre_dia_mm"], spec["width_mm"], spec["rim_dia_mm"]) == (80.0, 10.0, 76.5)
    assert (spec["bore_dia_mm"], spec["bore_flat_to_opposite_mm"]) == (3.0, 2.5)
    gearmotor = catalog.gearmotor_spec("pololu-2367")
    assert spec["bore_dia_mm"] == gearmotor["shaft_dia_mm"]
    assert spec["bore_flat_to_opposite_mm"] == gearmotor["shaft_flat_to_opposite_mm"]
    assert "pololu-2367" in spec["fits"]
    # ADR-489: the stated mass split between the wheel and its tyre.
    tyre_g = 4194.8e-9 * 1100.0 * 1e3
    assert spec["tyre_mass_g"] == pytest.approx(tyre_g, abs=0.01)
    assert spec["density_kg_m3"] == pytest.approx(
        (19.8 - tyre_g) * 1e-3 / (14715.5e-9), abs=0.05)
    wheel = _lib().wheel("pololu-1430")
    assert (wheel.family, wheel.part_number) == ("wheel", "pololu-1430")
    radii = {c.arguments[0] for c in _ops(wheel.body, "cylinder")}
    # Hub, flange, rim and its inside, the hub holes and the bore: no tyre.
    assert radii == {3.3, 8.5, 38.25, 33.5, 1.55, 1.5}
    # Six spokes, each a root block, two ribs and a rim block.
    assert len(_ops(wheel.body, "box")) == 24
    bore = next(c for c in _ops(wheel.body, "cylinder") if c.arguments[0] == 1.5)
    assert bore.arguments[1] == spec["bore_depth_mm"] + 1.0
    tyre = wheel.tyre()
    assert (tyre.family, tyre.part_number) == ("tyre", "pololu-1430")
    assert tyre.spec["density_kg_m3"] == 1100.0
    assert {c.arguments[0] for c in _ops(tyre.body, "cylinder")} == {39.0, 40.0, 38.25}
    assert len(_ops(tyre.body, "torus")) == 2
    assert catalog_identity_of(tyre.body) == {"family": "tyre", "part_number": "pololu-1430"}
    bay = wheel.bay()
    well = sorted(c.arguments for c in _ops(bay, "cylinder"))
    assert well == [(6.3, 4.75), (43.0, 16.0)]
    placed = _lib().wheel("pololu-1430", origin=(0, 50, 0), direction=(0, 1, 0))
    assert placed.bay().properties == placed.body.properties
    assert placed.tyre().body.properties == placed.body.properties
    assert catalog_identity_of(bay) is None
    with pytest.raises(CatalogError, match="Unknown wheel"):
        _lib().wheel("generic-80mm")
    with pytest.raises(LibraryError, match="wheel.bay: clearance must be"):
        wheel.bay(clearance=-1)


def test_foot_pad_spec_recipe_and_bay():
    """ADR-485: a rubber foot held by a screw, and the hole that screw needs."""
    spec = catalog.foot_pad_spec("essentra-462178")
    assert (spec["top_dia_mm"], spec["base_dia_mm"], spec["height_mm"]) == (19.0, 16.0, 8.0)
    assert (spec["screw"], spec["screw_hole_dia_mm"]) == ("m3", 3.0)
    assert (spec["counterbore_dia_mm"], spec["counterbore_depth_mm"]) == (7.0, 6.0)
    assert spec["screw_length_min_mm"] == 2.0
    pad = _lib().foot_pad("essentra-462178", direction=(0, 0, -1))
    (cone,) = _ops(pad.body, "cone")
    assert cone.arguments == (9.5, 8.0, 8.0)
    holes = sorted(c.arguments[0] for c in _ops(pad.body, "cylinder"))
    assert holes == [1.5, 3.5]
    bay = pad.bay()
    assert bay.properties == pad.body.properties
    keep_out, screw = sorted(_ops(bay, "cylinder"), key=lambda c: -c.arguments[0])
    assert keep_out.arguments == (10.0, 8.5)
    assert screw.arguments == (catalog.thread_spec("m3")["tap_drill_mm"] / 2.0, 8.0)
    assert tuple(screw.properties["origin"]) == (0.0, 0.0, -8.0)
    assert len(_ops(pad.bay(screw_depth=0), "cylinder")) == 1
    assert catalog_identity_of(bay) is None
    with pytest.raises(CatalogError, match="Unknown foot pad"):
        _lib().foot_pad("bumpon")
    with pytest.raises(LibraryError, match="foot_pad.bay: screw_depth must be"):
        pad.bay(screw_depth=float("inf"))


def test_orun1_families_are_browsable():
    families = catalog.catalog_families()
    assert families["wheels"]["skus"] == ["pololu-1430"]
    assert families["foot_pads"]["skus"] == ["essentra-462178"]
    assert {"pi-5", "rpi-camera-module-3", "pololu-vl53l1x-3415",
            "tb6612-adafruit-2448"} <= set(families["boards"]["skus"])
    assert "sts3215" in families["servos"]["skus"]
    assert "mount_points" in families["servos"]["notes"]
    names = {entry["name"] for entry in library_listing()["exports"]}
    assert {"wheel", "foot_pad"} <= names


def test_battery_envelope_mass_and_density():
    """ADR-407: the heaviest part on a small robot carries its stated mass."""
    pack = _lib().battery(" GENSACE-GEA2S100045D ")
    assert (pack.family, pack.part_number) == ("battery", "gensace-gea2s100045d")
    spec = pack.spec
    assert (spec["length_mm"], spec["width_mm"], spec["height_mm"], spec["mass_g"]) == (72.0, 36.0, 13.0, 64.0)
    assert spec["cells_series"] == 2 and spec["nominal_voltage_v"] == 7.4
    assert spec["density_kg_m3"] == pytest.approx(64e-3 / (72 * 36 * 13 * 1e-9), rel=1e-4)
    assert spec["sources"] and all(u.startswith("https://") for u in spec["sources"])
    assert "batteries" in catalog.catalog_families()
    with pytest.raises(CatalogError, match="Unknown battery"):
        _lib().battery("generic-2s")


def _box_extents(bay):
    (box,) = _ops(bay, "box")
    low = box.properties["origin"]
    return tuple(low), tuple(a + b for a, b in zip(low, box.arguments))


def test_battery_bay_houses_the_pack_with_room_for_its_leads():
    """ADR-442: a bay is cut from the pack's own extents, not guessed."""
    placed = _lib().battery("gensace-gea2s100045d", origin=(10, 20, 30),
                            direction=(1, 0, 0), roll_degrees=90)
    bay = placed.bay()
    assert bay.operation == "transform"
    # The bay follows the pack's placement exactly.
    assert bay.properties == placed.body.properties
    low, high = _box_extents(bay)
    assert low == pytest.approx((-37.0, -19.0, 0.0))  # seat, not clearance, below
    assert high == pytest.approx((36.0 + 1.0 + 15.0, 19.0, 14.0))
    low, high = _box_extents(placed.bay(clearance=2, lead_room=0))
    assert (low, high) == (pytest.approx((-38, -20, 0)), pytest.approx((38, 20, 15)))
    # A bay is a cutting tool, never catalogued hardware.
    assert catalog_identity_of(bay) is None


@pytest.mark.parametrize("sku", ["esp32-devkitc-v4", "pi-zero-2-w",
                                 "pca9685-adafruit-rev-c", "bno085-adafruit-4754",
                                 "pololu-d36v50f6", "pi-5", "pololu-vl53l1x-3415",
                                 "tb6612-adafruit-2448"])
def test_board_bay_contains_the_board_and_its_overhang(sku):
    board = _lib().board(sku)
    spec = board.spec
    low, high = _box_extents(board.bay())
    (mx, my, mz), (sx, sy, sz) = spec["cosmetic_origin"], spec["cosmetic_size"]
    assert low[:2] == pytest.approx((min(0, mx) - 1, min(0, my) - 1))
    assert high[:2] == pytest.approx((max(spec["width_mm"], mx + sx) + 1,
                                      max(spec["length_mm"], my + sy) + 1))
    assert low[2] == pytest.approx(-3.0)
    assert high[2] == pytest.approx(max(spec["thickness_mm"], mz + sz) + 1 + 8)
    assert catalog_identity_of(board.bay()) is None


def test_board_mounting_sizes_standoffs_taps_and_screws_from_the_board():
    """ADR-493: a board's screws thread printed material by construction."""
    reg = _lib().board("pololu-d36v50f6", origin=(7.0, -12.7, 52.0),
                       direction=(1, 0, 0), roll_degrees=90.0)
    hold = reg.mounting()
    t = reg.spec["thickness_mm"]
    assert (hold.screw, hold.length_mm) == ("m2", 7.0)  # ceil(1.57 + 5)
    assert len(hold.standoffs) == len(hold.holes) == len(hold.screws) == 3
    tap = catalog.thread_spec("m2")["tap_drill_mm"]
    for boss, hole, (x, y) in zip(hold.standoffs, hold.holes, reg.spec["mount_holes"]):
        assert boss.properties == hole.properties == reg.body.properties
        (cyl,) = _ops(boss, "cylinder")
        assert cyl.arguments == (2.5, 4.0)
        assert tuple(cyl.properties["origin"]) == (x, y, -4.0)
        (cyl,) = _ops(hole, "cylinder")
        assert cyl.arguments == pytest.approx((tap / 2.0, 7.0 - t + 1.5))
        assert tuple(cyl.properties["origin"]) == pytest.approx((x, y, -(7.0 - t + 1.0)))
    # Each screw seats on the PCB's top face, on its hole's axis.
    seat = hold.screws[0].body.properties["translation"]
    assert seat == pytest.approx((7.0 + t, -12.7 + 2.159, 52.0 + 2.159))
    assert {s.part_number for s in hold.screws} == {hold.screws[0].part_number}
    assert _lib().board("pi-5").mounting().screw == "m2.5"
    assert _lib().board("bno085-adafruit-4754").mounting(screw="m2").screw == "m2"
    assert _lib().board("bno085-adafruit-4754").mounting(standoff=5).length_mm == 8.0
    with pytest.raises(LibraryError, match="has no mounting holes"):
        _lib().board("esp32-devkitc-v4").mounting()
    with pytest.raises(LibraryError, match="does not pass the board's 2.18 mm holes"):
        reg.mounting(screw="m2.5")
    with pytest.raises(LibraryError, match="less than 0.8 mm of wall"):
        reg.mounting(diameter=3.0)
    with pytest.raises(LibraryError, match="does not pass the 1.57 mm PCB"):
        reg.mounting(length=1.0)
    with pytest.raises(LibraryError, match="standoff must be positive"):
        reg.mounting(standoff=0)


def test_esp32_bay_covers_the_module_overhanging_its_pcb():
    esp = _lib().board("esp32-devkitc-v4")
    _low, high = _box_extents(esp.bay(clearance=0, lead_room=0))
    assert high[1] == pytest.approx(23.0 + 31.30)  # past the 48.26 mm PCB


def _boxes(bay):
    return sorted(
        (tuple(b.properties["origin"]),
         tuple(o + a for o, a in zip(b.properties["origin"], b.arguments)))
        for b in _ops(bay, "box"))


def _servo_bay_bounds(servo, **kwargs):
    boxes = _boxes(servo.bay(**kwargs))
    return (tuple(min(low[i] for low, _ in boxes) for i in range(3)),
            tuple(max(high[i] for _, high in boxes) for i in range(3)))


@pytest.mark.parametrize("sku", ["sg90", "mg90s", "ds3218"])
def test_servo_bay_houses_the_case_tabs_and_lead(sku):
    """ADR-443: a limb grows around the servo's own keep-out, not a guess."""
    servo = _servo_lib().servo(sku)
    spec = servo.spec
    front = spec["shaft_offset_from_front_mm"]
    back = front - spec["body_length_mm"]
    half = spec["body_width_mm"] / 2
    plate_z = spec["mount_hole_z_mm"]
    centre = front - spec["body_length_mm"] / 2
    tab = spec["overall_tab_length_mm"] / 2
    boxes = _boxes(servo.bay())
    assert len(boxes) == 3
    assert ((back - 0.5, -half - 0.5, -spec["case_height_mm"] - 0.5),
            (front + 0.5, half + 0.5, 0.5)) in [
        (pytest.approx(lo), pytest.approx(hi)) for lo, hi in boxes]
    assert ((centre - tab - 0.5, -half - 0.5, plate_z - 0.5),
            (centre + tab + 0.5, half + 0.5, plate_z + spec["tab_thickness_mm"] + 0.5)) in [
        (pytest.approx(lo), pytest.approx(hi)) for lo, hi in boxes]
    assert ((back - 6.5, -half - 0.5, -spec["case_height_mm"] - 0.5),
            (back - 0.5, half + 0.5, plate_z - 0.5)) in [
        (pytest.approx(lo), pytest.approx(hi)) for lo, hi in boxes]
    (column,) = _ops(servo.bay(), "cylinder")
    assert column.arguments == (pytest.approx(spec["spline_dia_mm"] / 2 + 0.5),
                                spec["spline_height_mm"])
    # Without lead room the lead box is gone, not a zero-length solid.
    assert len(_boxes(servo.bay(lead_room=0))) == 2
    assert catalog_identity_of(servo.bay()) is None


@pytest.mark.parametrize("sku", ["sg90", "mg90s", "mg996r", "ds3218"])
def test_servo_bay_leaves_a_ledge_under_the_lead_side_screw(sku):
    """ADR-491: the lead room must not take the lead-side tab screw's bite.

    Every tabbed servo's lead-side hole sits 3.1-4.75 mm past the back end
    face, inside the 6 mm lead room. Run to the tab underside, the room cut
    away the material that screw goes into, so designs dropped it and held
    each servo by one tab (orun1-t1-hexapod). ``ledge`` is opt-in because
    the bay's boxes are part of every accepted recipe that cut one.
    """
    servo = _servo_lib().servo(sku)
    spec = servo.spec
    ledge_top = spec["mount_hole_z_mm"] - 0.5
    lead_side = [(x, y) for x, y in spec["mount_holes"]
                 if x < spec["shaft_offset_from_front_mm"] - spec["body_length_mm"]]
    assert lead_side

    def cut(boxes, point):
        return any(all(lo[i] < point[i] < hi[i] for i in range(3)) for lo, hi in boxes)

    ledged, plain = _boxes(servo.bay(ledge=4)), _boxes(servo.bay())
    for x, y in lead_side:
        for depth in (0.5, 2.0, 3.5):
            assert not cut(ledged, (x, y, ledge_top - depth)), (sku, depth)
        # ...the room itself is still there below the ledge, and the
        # default bay is ADR-443's, so accepted recipes do not move.
        assert cut(ledged, (x, y, ledge_top - 4.5))
        assert cut(plain, (x, y, ledge_top - 0.5))
    with pytest.raises(LibraryError, match="servo.bay: ledge 40 mm leaves no lead room"):
        servo.bay(ledge=40)
    with pytest.raises(LibraryError, match="servo.bay: ledge must be"):
        servo.bay(ledge=-1)
    bus = _servo_lib().servo("sts3215")
    assert _boxes(bus.bay(ledge=4)) == _boxes(bus.bay())


def test_servo_bay_contains_the_servo_body():
    servo = _servo_lib().servo("mg90s")
    low, high = _servo_bay_bounds(servo, clearance=0, lead_room=0)
    body_boxes = _boxes(servo.body)
    assert low == pytest.approx(tuple(min(b[0][i] for b in body_boxes) for i in range(3)))
    assert high[:2] == pytest.approx(tuple(max(b[1][i] for b in body_boxes)
                                           for i in range(2)))


def test_servo_bay_follows_the_servo_placement():
    servo = _servo_lib().servo("mg90s", origin=(10, 20, 30), direction=(0, 1, 0),
                               roll_degrees=90)
    bay = servo.bay(label="hip_bay")
    assert bay.operation == "transform"
    assert bay.properties == servo.body.properties


@pytest.mark.parametrize("name,value", [("clearance", -1), ("lead_room", float("nan")),
                                        ("clearance", True), ("underside", "2")])
def test_bay_allowances_refuse_by_name(name, value):
    board = _lib().board("pi-zero-2-w")
    with pytest.raises(LibraryError, match=f"board.bay: {name} must be"):
        board.bay(**{name: value})
    if name != "underside":
        with pytest.raises(LibraryError, match=f"battery.bay: {name} must be"):
            _lib().battery("gensace-gea2s100045d").bay(**{name: value})
        with pytest.raises(LibraryError, match=f"servo.bay: {name} must be"):
            _servo_lib().servo("mg90s").bay(**{name: value})


def catalog_identity_of(body):
    from cadex_library_api import _CATALOG_IDENTITY, _definition_key
    return _CATALOG_IDENTITY.get(_definition_key(body))


def test_board_terminals_follow_placement_and_enter_wiring_table():
    from CadexBoards import board as declare_board
    placed = _lib().board("pi-zero-2-w", origin=(10, 20, 30),
                          direction=(1, 0, 0), roll_degrees=90)
    first = placed.terminals()[0]
    # Roll maps (x,y,z) to (-y,x,z); +Z-to-+X maps this to (z,x,y).
    assert first["origin"] == pytest.approx((11.6, 28.37, 55.23))
    assert first["axis"] == pytest.approx((-1, 0, 0))
    assert placed.body.operation == "transform"
    declaration = declare_board(placed.body, terminals=placed.terminals())
    assert len(declaration["rows"]) == 40


# -- browsing and describe_api ----------------------------------------------


def test_bldc_pins_qualified_ratings_and_isolation():
    motor = _lib().bldc(" HOBBYWING-30415200 ")
    spec = motor.spec
    assert (motor.family, motor.part_number) == ("bldc", "hobbywing-30415200")
    assert (spec["case_dia_mm"], spec["case_length_mm"]) == (35.1, 40)
    assert (spec["rear_boss_dia_mm"], spec["rear_boss_height_mm"]) == (11, 2)
    assert (spec["shaft_dia_mm"], spec["shaft_projection_mm"]) == (5, 18)
    assert spec["shaft_collar_envelope_dia_mm"] == 10.5
    assert spec["mount_holes"] == [[-9.5, 0], [9.5, 0], [0, -12.5], [0, 12.5]]
    assert (spec["kv_rpm_per_v"], spec["supply_lipo_cells"]) == (550, 6)
    assert (spec["no_load_current_a"], spec["no_load_test_voltage_v"]) == (1.38, 22.2)
    assert spec["mass_g"] == 144.5
    assert "46 s" in spec["rating_notes"]
    assert "Not a shaft coupling fit model" in spec["approximate"][1]
    assert not any("torque" in key or "inertia" in key for key in spec)
    spec["mount_holes"][0][0] = 999
    assert catalog.bldc_spec("hobbywing-30415200")["mount_holes"][0][0] == -9.5
    assert _lib().catalog()["bldc_motors"]["skus"] == ["hobbywing-30415200"]
    assert "bldc" in {row["name"] for row in library_listing()["exports"]}
    with pytest.raises(LibraryError):
        _lib().bldc("hobbywing-30415200", direction=(0, 0, 0))


@pytest.mark.parametrize("sku", ["2820", "hobbywing-30415201", "", None, 30415200])
def test_bldc_rejects_unsourced_windings(sku):
    with pytest.raises(CatalogError, match="Unknown BLDC motor"):
        _lib().bldc(sku)


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available for BLDC interface checks.",
)
def test_bldc_real_kernel_interfaces_and_placement(tmp_path):
    import subprocess
    from test_cadexd_lifecycle import CADEX_ROOT, FREECADCMD

    # Build the actual lib recipe through the worker from the selected source
    # or payload. Probe solid material and empty mounting bores independently
    # of recipe-tree assertions, including after a nontrivial rigid placement.
    driver = tmp_path / "bldc_interfaces.py"
    driver.write_text('''
import FreeCAD as App
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import create_domain_api
from cadex_library_api import create_library_api
from cadex_part_worker import build_part_shape
pack = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]
lib = create_library_api(create_domain_api(pack.domain, pack.api_exports, pack.output_types))
canonical = build_part_shape(lib.bldc("hobbywing-30415200").body.to_payload())
assert canonical.isValid() and len(canonical.Solids) == 1
bb = canonical.BoundBox
for actual, expected in zip((bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax),
                            (-17.55, 17.55, -17.55, 17.55, -2, 58)):
    assert abs(actual-expected) < 1e-6, (actual, expected)
# In the bores, behind their assumed depth, and alongside their walls.
probes = [((x,y,0.5), False) for x,y in ((-9.5,0),(9.5,0),(0,-12.5),(0,12.5))]
probes += [((9.5,0,2), True), ((11.5,0,0.5), True),
           ((0,0,-1), True), ((6,0,-1), False),
           ((5,0,57), True), ((5.5,0,57), False)]
placed = build_part_shape(lib.bldc("hobbywing-30415200", origin=(100,30,20),
                                  direction=(1,0,0), roll_degrees=90).body.to_payload())
assert placed.isValid() and len(placed.Solids) == 1
assert abs(placed.Volume-canonical.Volume) < 1e-6
# The placement maps Z to X; 90-degree roll maps local X to world Y
# and local Y to world Z.
for point, occupied in probes:
    assert canonical.isInside(App.Vector(*point), 1e-7, True) == occupied, point
    x,y,z = point
    assert placed.isInside(App.Vector(100+z,30+x,20+y), 1e-7, True) == occupied, point
print("BLDC-INTERFACES-OK")
''')
    completed = subprocess.run(
        [str(FREECADCMD), "-c",
         f"import sys; sys.path.insert(0, {str(CADEX_ROOT)!r}); exec(open({str(driver)!r}).read())"],
        capture_output=True, text=True, timeout=120,
    )
    assert "BLDC-INTERFACES-OK" in completed.stdout, completed.stdout + completed.stderr



# -- quasi-direct-drive actuators (ADR-540) --------------------------------


def test_qdd_pins_manufacturer_ratings_and_isolation():
    ak70 = _lib().qdd(" CubeMars-AK70-10 ")
    spec = ak70.spec
    assert (ak70.family, ak70.part_number) == ("qdd", "cubemars-ak70-10")
    assert (spec["gear_ratio"], spec["rated_voltage_v"]) == (10, 48)
    assert (spec["rated_torque_nm"], spec["peak_torque_nm"]) == (8.3, 24.8)
    assert (spec["rated_speed_rpm"], spec["no_load_speed_rpm"]) == (310, 480)
    assert (spec["back_drive_torque_nm"], spec["mass_g"]) == (0.48, 621)
    assert spec["segments"] == [[77, -6, 0], [89, -39.05, -6], [71, -50.25, -39.05]]
    assert spec["peak_torque_nmm"] == pytest.approx(24800)
    assert spec["rated_torque_nmm"] == pytest.approx(8300)
    # 753.4788 g*cm^2 at the rotor is 75.34788 kg*mm^2; x 10^2 at the output.
    assert spec["reflected_inertia_kgmm2"] == pytest.approx(7534.788)
    assert len(spec["mount_holes"]) == 8 and len(spec["output_holes"]) == 6
    for x, y in spec["mount_holes"]:
        assert math.hypot(x, y) == pytest.approx(41.5)
    for x, y in spec["output_holes"]:
        assert math.hypot(x, y) == pytest.approx(12.5)
    assert spec["mount_holes"][0] == pytest.approx(
        [41.5 * math.cos(math.radians(22.5)), 41.5 * math.sin(math.radians(22.5))])
    assert "peak-to-no-load line" in spec["rating_notes"]
    # 24.8 N*m at rest to none at 480 rpm (2880 deg/s).
    assert spec["speed_line_damping_nmms_per_deg"] == pytest.approx(24800 / 2880)
    ak80 = _lib().qdd("cubemars-ak80-9-v3").spec
    assert (ak80["gear_ratio"], ak80["peak_torque_nm"], ak80["mass_g"]) == (9, 22, 490)
    assert ak80["reflected_inertia_kgmm2"] == pytest.approx(1118.3238 * 0.1 * 81)
    assert ak80["output_thread"] == "M4"
    # The effective density reproduces the manufacturer's mass over the
    # drilled envelope it was computed from.
    for row in (spec, ak80):
        envelope = sum(math.pi * (d / 2) ** 2 * (hi - lo) for d, lo, hi in row["segments"])
        assert row["effective_density_kg_m3"] * envelope / 1e6 > row["mass_g"]
        assert row["effective_density_kg_m3"] * envelope / 1e6 < row["mass_g"] * 1.01
    spec["segments"][0][0] = 999
    assert catalog.qdd_spec("cubemars-ak70-10")["segments"][0][0] == 77
    assert _lib().catalog()["qdd_actuators"]["skus"] == [
        "cubemars-ak45-10-v3", "cubemars-ak60-6-v3", "cubemars-ak70-10", "cubemars-ak80-9-v3"]
    assert "qdd" in {row["name"] for row in library_listing()["exports"]}
    with pytest.raises(LibraryError):
        _lib().qdd("cubemars-ak70-10", direction=(0, 0, 0))


@pytest.mark.parametrize("sku", ["ak70-10", "cubemars-ak80-9", "", None, 7010])
def test_qdd_rejects_uncatalogued_actuators(sku):
    with pytest.raises(CatalogError, match="Unknown QDD actuator"):
        _lib().qdd(sku)


def test_qdd_actuator_is_a_torque_motor_at_the_datasheet_limit() -> None:
    lib = _servo_lib()
    api = _assembly_api()
    base = api.component({"document_uid": "doc", "object_name": "base"}, grounded=True)
    leg = api.component({"document_uid": "doc", "object_name": "leg"})
    joint = api.joint("revolute", api.connector(base), api.connector(leg))
    qdd = lib.qdd("cubemars-ak80-9-v3")
    peak = qdd.actuator(joint).properties
    assert peak["kind"] == "motor"
    assert peak["control_nmm"] == "0"
    assert peak["torque_limit_nmm"] == pytest.approx(22000)
    rated = qdd.actuator(joint, control_nmm="100", rating="rated").properties
    assert rated["torque_limit_nmm"] == pytest.approx(9000)
    with pytest.raises(LibraryError, match="9 N\\*m continuous"):
        qdd.actuator(joint, rating="stall")
    dynamics = qdd.joint_dynamics(joint).properties
    assert dynamics["armature_kgmm2"] == pytest.approx(1118.3238 * 0.1 * 81)
    assert dynamics["friction_loss_nmm"] == pytest.approx(510)
    assert dynamics["damping_nmms_per_deg"] == pytest.approx(22000 / 3420)
    damped = qdd.joint_dynamics(joint, damping_nmms_per_deg=0.0).properties
    assert damped["damping_nmms_per_deg"] == 0.0
    # The claim, in MuJoCo itself: a leg driven flat out at the peak torque
    # settles at the datasheet no-load speed (570 rpm), not above it.
    mujoco = pytest.importorskip("mujoco")
    per_deg = 180.0 / math.pi / 1000.0  # N*mm per deg -> N*m per rad
    model = mujoco.MjModel.from_xml_string(f"""
<mujoco><option timestep="0.0005"/><worldbody><body>
  <joint name="j" type="hinge" axis="0 0 1" damping="{dynamics['damping_nmms_per_deg'] * per_deg}"
         armature="{dynamics['armature_kgmm2'] * 1e-6}"/>
  <geom type="capsule" fromto="0 0 0 0.2 0 0" size="0.01" mass="0.25"/>
</body></worldbody><actuator>
  <motor joint="j" forcerange="-22 22" forcelimited="true"/>
</actuator></mujoco>""")
    data = mujoco.MjData(model)
    data.ctrl[0] = 1e6
    for _ in range(int(2.0 / model.opt.timestep)):
        mujoco.mj_step(model, data)
    rpm = data.qvel[0] * 60.0 / (2.0 * math.pi)
    assert rpm == pytest.approx(570.0, rel=0.01)
    unstaged = create_library_api(_part()).qdd("cubemars-ak80-9-v3")
    with pytest.raises(LibraryError):
        unstaged.actuator(joint)
    with pytest.raises(LibraryError):
        unstaged.joint_dynamics(joint)


def test_light_qdds_pin_manufacturer_ratings_and_drawn_bolt_circles():
    """ADR-608: the AK60-6 V3 and AK45-10 V3 rows, from CubeMars' tables and drawings."""
    ak60 = _lib().qdd("cubemars-ak60-6-v3").spec
    assert (ak60["gear_ratio"], ak60["rated_voltage_v"], ak60["mass_g"]) == (6, 48, 380)
    assert (ak60["rated_torque_nm"], ak60["peak_torque_nm"]) == (3, 9)
    assert (ak60["rated_speed_rpm"], ak60["no_load_speed_rpm"]) == (490, 640)
    assert (ak60["kt_nm_per_a"], ak60["rotor_inertia_gcm2"]) == (0.135, 243.5)
    assert ak60["back_drive_torque_nm"] == 0.2 and ak60["backlash_arcmin"] is None
    assert "no backlash figure" in ak60["rating_notes"]
    assert ak60["reflected_inertia_kgmm2"] == pytest.approx(243.5 * 0.1 * 36)
    assert ak60["speed_line_damping_nmms_per_deg"] == pytest.approx(9000 / 3840)
    assert ak60["segments"][2] == [79, -31, -1.5]
    assert len(ak60["mount_holes"]) == len(ak60["rear_mount_holes"]) == 6
    assert ak60["mount_holes"] == ak60["rear_mount_holes"]
    assert all(math.hypot(x, y) == pytest.approx(34) for x, y in ak60["mount_holes"])
    assert all(math.hypot(x, y) == pytest.approx(10) for x, y in ak60["output_holes"])
    ak45 = _lib().qdd("cubemars-ak45-10-v3").spec
    assert (ak45["gear_ratio"], ak45["rated_voltage_v"], ak45["mass_g"]) == (10, 24, 262)
    assert (ak45["rated_torque_nm"], ak45["peak_torque_nm"]) == (2.5, 7)
    assert (ak45["rated_speed_rpm"], ak45["no_load_speed_rpm"]) == (120, 180)
    assert (ak45["back_drive_torque_nm"], ak45["backlash_arcmin"]) == (0.1, 18)
    assert ak45["reflected_inertia_kgmm2"] == pytest.approx(157.33 * 0.1 * 100)
    assert ak45["mount_thread"] == ak45["output_thread"] == "M2.5"
    # The rear face has its own circle: 4 x M2.5 on 47 mm against the front's 6 on 47.5.
    assert len(ak45["mount_holes"]) == 6 and len(ak45["rear_mount_holes"]) == 4
    assert all(math.hypot(x, y) == pytest.approx(23.75) for x, y in ak45["mount_holes"])
    assert all(math.hypot(x, y) == pytest.approx(23.5) for x, y in ak45["rear_mount_holes"])
    assert ak45["rear_mount_holes"][0] == pytest.approx([23.5, 0.0])
    assert len(ak45["output_holes"]) == 3
    for row in (ak60, ak45):
        # Light tier: under 400 g, and the drilled envelope reproduces the mass.
        assert row["mass_g"] < 400
        envelope = sum(math.pi * (d / 2) ** 2 * (hi - lo) for d, lo, hi in row["segments"])
        assert row["mass_g"] < row["effective_density_kg_m3"] * envelope / 1e6 < row["mass_g"] * 1.01
        assert row["sources"][0].startswith("https://www.cubemars.com/product/")
        # Every hole circle clears the envelope step it is drilled through.
        front = max(d for d, lo, hi in row["segments"] if hi > row["front_mount_z_mm"] + 1e-9)
        assert row["mount_pcd_mm"] / 2 > front / 2
        assert row["mount_pcd_mm"] / 2 < row["case_dia_mm"] / 2
    assert catalog.qdd_spec("cubemars-ak60-6-v3")["output_thread"] == "M3"


def _bolt_axis(bolt):
    from cadex_library_api import _MOUNT_AXES, _definition_key

    [row] = _MOUNT_AXES[_definition_key(bolt.body)]
    return row


@pytest.mark.parametrize("sku", sorted(catalog.QDD_ACTUATORS))
def test_qdd_mounting_puts_a_screw_on_every_hole_and_stops_in_the_thread(sku):
    """ADR-609: the stator and output screws, on the published hole axes."""
    from cadex_library_api import _MOUNT_AXES, _definition_key

    qdd = _lib().qdd(sku)
    spec = qdd.spec
    axes = _MOUNT_AXES[_definition_key(qdd.body)]
    hold = qdd.mounting()
    stator, output = hold.stator, hold.output
    assert (stator.face, output.face, stator.wall_mm, output.wall_mm) == (
        "front", "output", 4.0, 4.0)
    assert stator.screw == spec["mount_thread"].lower()
    assert output.screw == spec["output_thread"].lower()
    assert len(stator.screws) == len(stator.holes) == len(spec["mount_holes"])
    assert len(output.screws) == len(output.holes) == len(spec["output_holes"])
    for side, depth in ((stator, spec["front_mount_depth_mm"]),
                        (output, spec["output_depth_mm"])):
        # Rounded down to a millimetre, never past the drawn thread.
        assert side.length_mm == math.floor(4.0 + depth)
        assert 0 < side.length_mm - 4.0 <= depth
        for screw in side.screws:
            assert screw.family == "bolt"
            assert screw.part_number == f"{side.screw}x{side.length_mm:g}-socket"
    front = spec["front_mount_z_mm"]
    for (x, y), screw in zip(spec["mount_holes"], stator.screws):
        row = _bolt_axis(screw)
        assert row["origin"] == pytest.approx([x, y, front + 4.0])
        assert row["axis"] == pytest.approx([0, 0, 1])
        assert any(a["origin"] == pytest.approx([x, y, front]) and not a.get("output")
                   for a in axes)
    for (x, y), screw in zip(spec["output_holes"], output.screws):
        assert _bolt_axis(screw)["origin"] == pytest.approx([x, y, 4.0])
        assert any(a["origin"] == pytest.approx([x, y, 0.0]) and a.get("output")
                   and a["thread_dia_mm"] == float(spec["output_thread"][1:])
                   for a in axes)
    rear = qdd.mounting(3.0, face="rear").stator
    assert rear.face == "rear" and len(rear.screws) == len(spec["rear_mount_holes"])
    assert rear.length_mm == math.floor(3.0 + spec["rear_mount_depth_mm"])
    for (x, y), screw in zip(spec["rear_mount_holes"], rear.screws):
        row = _bolt_axis(screw)
        assert row["origin"] == pytest.approx([x, y, spec["rear_mount_z_mm"] - 3.0])
        assert row["axis"] == pytest.approx([0, 0, -1])
    with pytest.raises(TypeError):
        hold.stator = None


def test_qdd_mounting_follows_the_placement_and_refuses_a_bottoming_screw():
    qdd = _lib().qdd("cubemars-ak45-10-v3", origin=(10, 0, 0), direction=(1, 0, 0))
    hold = qdd.mounting(3.0, output_wall=5.0)
    # +Z maps to +X: front face at x = 9, head 3 mm out; output head 5 mm out.
    assert {round(_bolt_axis(s)["origin"][0], 6) for s in hold.stator.screws} == {12.0}
    assert {round(_bolt_axis(s)["origin"][0], 6) for s in hold.output.screws} == {15.0}
    assert all(_bolt_axis(s)["axis"] == pytest.approx([1, 0, 0]) for s in hold.output.screws)
    assert (hold.stator.length_mm, hold.output.length_mm) == (8.0, 11.0)
    assert len(_ops(hold.stator.holes[0], "cylinder")) == 1
    assert catalog_identity_of(hold.stator.holes[0]) is None
    with pytest.raises(LibraryError, match="bottoms out"):
        qdd.mounting(3.0, length=9.0)
    with pytest.raises(LibraryError, match="under half its diameter"):
        qdd.mounting(3.0, output_length=4.0)
    with pytest.raises(LibraryError, match="face must be"):
        qdd.mounting(face="side")
    with pytest.raises(LibraryError):
        qdd.mounting(0.0)


def test_qdd_bay_and_mount_axes_follow_the_placement():
    from cadex_library_api import _MOUNT_AXES, _definition_key

    qdd = _lib().qdd("cubemars-ak70-10", origin=(10, 0, 0), direction=(1, 0, 0))
    axes = _MOUNT_AXES[_definition_key(qdd.body)]
    # 8 front and 8 rear stator holes, then the 6 output-flange holes (ADR-609).
    assert len(axes) == 22
    assert all(row["thread_dia_mm"] == 3.0 for row in axes)
    assert [bool(row.get("output")) for row in axes] == [False] * 16 + [True] * 6
    # +Z maps to +X: the front stator face sits 6 mm behind the output face.
    assert {round(row["origin"][0], 6) for row in axes} == {10.0, 4.0, -29.05}
    assert all(abs(row["axis"][0]) == pytest.approx(1.0) for row in axes)
    bay = qdd.bay()
    assert len(_ops(bay, "cylinder")) == 4
    assert catalog_identity_of(bay) is None



@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available for QDD interface checks.",
)
def test_qdd_real_kernel_envelope_holes_and_placement(tmp_path):
    import subprocess
    from test_cadexd_lifecycle import CADEX_ROOT, FREECADCMD

    driver = tmp_path / "qdd_interfaces.py"
    driver.write_text('''
import math
import FreeCAD as App
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import create_domain_api
from cadex_library_api import create_library_api
from cadex_part_worker import build_part_shape
pack = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]
lib = create_library_api(create_domain_api(pack.domain, pack.api_exports, pack.output_types))
for sku, r, length in (("cubemars-ak70-10", 44.5, 50.25), ("cubemars-ak80-9-v3", 49.0, 38.5),
                       ("cubemars-ak60-6-v3", 39.5, 43.0), ("cubemars-ak45-10-v3", 26.5, 45.2)):
    part = lib.qdd(sku)
    spec = part.spec
    shape = build_part_shape(part.body.to_payload())
    assert shape.isValid() and len(shape.Solids) == 1, sku
    bb = shape.BoundBox
    for actual, expected in zip((bb.XMin, bb.XMax, bb.ZMin, bb.ZMax), (-r, r, -length, 0.0)):
        assert abs(actual - expected) < 1e-6, (sku, actual, expected)
    mass_g = shape.Volume * spec["effective_density_kg_m3"] / 1e6
    assert abs(mass_g - spec["mass_g"]) < 1e-6 * spec["mass_g"], (sku, mass_g)
    front, rear = spec["front_mount_z_mm"], spec["rear_mount_z_mm"]
    for x, y in spec["mount_holes"]:
        assert not shape.isInside(App.Vector(x, y, front - 0.5), 1e-7, True), (sku, x, y)
        assert shape.isInside(App.Vector(x * 0.9, y * 0.9, front - 1.0), 1e-7, True), sku
    for x, y in spec["rear_mount_holes"]:
        assert not shape.isInside(App.Vector(x, y, rear + 0.5), 1e-7, True), (sku, x, y)
    for x, y in spec["output_holes"]:
        assert not shape.isInside(App.Vector(x, y, -0.5), 1e-7, True), (sku, x, y)
    assert shape.isInside(App.Vector(0, 0, -1.0), 1e-7, True), sku
placed = build_part_shape(lib.qdd("cubemars-ak80-9-v3", origin=(100, 30, 20),
                                  direction=(1, 0, 0)).body.to_payload())
bb = placed.BoundBox
assert abs(bb.XMax - 100) < 1e-6 and abs(bb.XMin - 61.5) < 1e-6, (bb.XMin, bb.XMax)
print("QDD-INTERFACES-OK")
''')
    completed = subprocess.run(
        [str(FREECADCMD), "-c",
         f"import sys; sys.path.insert(0, {str(CADEX_ROOT)!r}); exec(open({str(driver)!r}).read())"],
        capture_output=True, text=True, timeout=120,
    )
    assert "QDD-INTERFACES-OK" in completed.stdout, completed.stdout + completed.stderr


def test_gearmotor_manufacturer_pins_and_isolation():
    motor = _lib().gearmotor(" POLOLU-2367 ")
    spec = motor.spec
    assert (motor.family, motor.part_number) == ("gearmotor", "pololu-2367")
    assert (spec["width_mm"], spec["height_mm"], spec["rear_envelope_mm"]) == (12, 10, 25.6)
    assert (spec["shaft_dia_mm"], spec["shaft_tip_z_mm"], spec["shaft_flat_to_opposite_mm"]) == (3, 10, 2.5)
    assert spec["mount_holes"] == [[-4.5, 0], [4.5, 0]]
    assert spec["mount_thread"] == "M1.6"
    assert spec["gear_ratio"] == pytest.approx(100.37004662004662)
    assert spec["rated_voltage_v"] == 6
    assert spec["no_load_speed_rpm"] == 220
    assert spec["no_load_current_a"] == 0.07
    assert spec["stall_current_a"] == 0.67
    assert spec["stall_torque_nmm"] == pytest.approx(92.18251)
    assert spec["mass_g"] == 9.5
    assert "extrapolations" in spec["rating_notes"]
    assert len(spec["approximate"]) == 3
    spec["mount_holes"][0][0] = 999
    assert catalog.gearmotor_spec("pololu-2367")["mount_holes"][0][0] == -4.5
    bores = [op for op in _ops(motor.body, "cylinder") if op.arguments[0] == 0.8]
    assert {tuple(op.properties["origin"]) for op in bores} == {(-4.5, 0, -1), (4.5, 0, -1)}
    flat = [op for op in _ops(motor.body, "box") if op.arguments[0] == 5][0]
    assert flat.properties["origin"] == (-2.5, 1.0, 1.0)


@pytest.mark.parametrize("sku", ["n20", "pololu-992", "", None, 2367])
def test_gearmotor_rejects_unsourced_variants(sku):
    with pytest.raises(CatalogError, match="Unknown gearmotor"):
        _lib().gearmotor(sku)


def test_gearmotor_placement_and_listing():
    motor = _lib().gearmotor("pololu-2367", origin=(10, 20, 30),
                             direction=(1, 0, 0), roll_degrees=30)
    assert motor.body.operation == "transform"
    assert motor.body.properties["translation"] == (10, 20, 30)
    assert motor.spec["mount_holes"] == [[-4.5, 0], [4.5, 0]]
    assert _lib().catalog()["gearmotors"]["skus"] == ["pololu-2367"]
    assert "gearmotor" in {row["name"] for row in library_listing()["exports"]}
    with pytest.raises(LibraryError):
        _lib().gearmotor("pololu-2367", direction=(0, 0, 0))


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle").FREECADCMD is None,
    reason="No FreeCADCmd binary available for N20 interface checks.",
)
def test_gearmotor_real_worker_interfaces_and_placement(tmp_path):
    import subprocess
    from test_cadexd_lifecycle import CADEX_ROOT, FREECADCMD

    driver = tmp_path / "n20_interfaces.py"
    driver.write_text(N20_INTERFACE_DRIVER)
    completed = subprocess.run(
        [str(FREECADCMD), "-c",
         f"import sys; sys.path.insert(0, {str(CADEX_ROOT)!r}); exec(open({str(driver)!r}).read())"],
        capture_output=True, text=True, timeout=120,
    )
    assert "N20-INTERFACES-OK" in completed.stdout, completed.stdout + completed.stderr
    print(completed.stdout)


N20_INTERFACE_DRIVER = r'''
import FreeCAD as App
import Part
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import create_domain_api
from cadex_library_api import create_library_api
from cadex_part_worker import build_part_shape
pack = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]
lib = create_library_api(create_domain_api(pack.domain, pack.api_exports, pack.output_types))
canonical = build_part_shape(lib.gearmotor("pololu-2367").body.to_payload())
placed = build_part_shape(lib.gearmotor("pololu-2367", origin=(100,30,20),
    direction=(1,0,0), roll_degrees=90).body.to_payload())
# Expected dimensions come from PROVENANCE 8b, never catalog/recipe metadata.
# Inverse of the independently specified cyclic placement, for surface measures.
for name, shape in (("canonical", canonical), ("placed", placed)):
    assert shape.isValid() and len(shape.Solids) == 1
    measured = shape.copy()
    if name == "placed":
        measured.translate(App.Vector(-100,-30,-20))
        measured.rotate(App.Vector(), App.Vector(1,1,1), -120)
    bores = sorted((round(f.Surface.Center.x, 6), round(f.Surface.Center.y, 6),
                    round(f.Surface.Radius, 6), round(f.BoundBox.ZMin, 6),
                    round(f.BoundBox.ZMax, 6)) for f in measured.Faces
                   if isinstance(f.Surface, Part.Cylinder)
                   and abs(f.Surface.Radius - .8) < 1e-7)
    assert bores == [(-4.5,0,.8,-1,0), (4.5,0,.8,-1,0)], bores
    shafts = [f for f in measured.Faces if isinstance(f.Surface, Part.Cylinder)
              and abs(f.Surface.Radius - 1.5) < 1e-7]
    assert shafts
    assert all(abs(f.Surface.Center.x) < 1e-7 and abs(f.Surface.Center.y) < 1e-7
               and abs(abs(f.Surface.Axis.z)-1) < 1e-7 for f in shafts)
    flat = [f for f in measured.Faces if isinstance(f.Surface, Part.Plane)
            and abs(f.BoundBox.YMin-1) < 1e-7 and abs(f.BoundBox.YMax-1) < 1e-7
            and f.BoundBox.ZLength > 8]
    assert len(flat) == 1
    assert abs(flat[0].BoundBox.ZMin-1) < 1e-7
    assert abs(flat[0].BoundBox.ZMax-10) < 1e-7
    assert abs(min(f.BoundBox.YMin for f in shafts) + 1.5) < 1e-7
    # Both sides of each bore wall, both sides of the assumed blind bottom.
    probes = []
    for x in (-4.5,4.5):
        for z in (-.95,-.5,-.05):
            probes.append(((x,0,z), False))
            for dx,dy in ((.79,0),(-.79,0),(0,.79),(0,-.79)):
                probes.append(((x+dx,dy,z), False))
            for dx,dy in ((.81,0),(-.81,0),(0,.81),(0,-.81)):
                probes.append(((x+dx,dy,z), True))
        probes.extend([((x,0,-1.05), True), ((x,0,.05), False)])
    for z in (1.05,5,9.95):
        probes.extend([((0,.99,z), True), ((0,1.01,z), False),
                       ((0,-1.49,z), True), ((0,-1.51,z), False),
                       ((1.49,0,z), True), ((1.51,0,z), False)])
    # Sharp flat transition at 1 mm is assumed, not measured hardware fidelity.
    probes.extend([((0,1.25,.95), True), ((0,1.25,1.05), False),
                   ((0,0,9.95), True), ((0,0,10.05), False)])
    for point, occupied in probes:
        x,y,z = point
        world = point if name == "canonical" else (100+z,30+x,20+y)
        assert shape.isInside(App.Vector(*world), 1e-7, True) == occupied, (name, point)
    print(name, "bores(x,y,r,zmin,zmax)=", bores,
          "shaft_dia=3 flat_to_opposite=2.5 flat_z=1..10 probes=", len(probes))
assert abs(placed.Volume-canonical.Volume) < 1e-6
print("N20-INTERFACES-OK")
'''


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
        "board",
        "battery",
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
esp = lib.board("esp32-devkitc-v4")
pi_board = lib.board("pi-zero-2-w", origin=(80, 0, 0))
pwm = lib.board("pca9685-adafruit-rev-c", direction=(1, 0, 0), roll_degrees=30)
b = boards({"esp": board(esp.body, terminals=esp.terminals()),
            "pi": board(pi_board.body, terminals=pi_board.terminals()),
            "pwm": board(pwm.body, terminals=pwm.terminals())})
n = nets(ports=b, wires={})
result = {
    "spur_gear": lib.spur_gear(2, 20, 10, bore=6).body,
    "spur_gear_placed": lib.spur_gear(1, 8, 5, origin=(100, 30, 20),
                                      direction=(1, 0, 0), roll_degrees=30).body,
    "rack": lib.rack(2, 10, 10, 8).body,
    "rack_placed": lib.rack(1.5, 4, 6, 5, origin=(100, 30, 20),
                            direction=(0, 1, 0), roll_degrees=90).body,
    "rack_and_pinion": lib.rack_and_pinion(2, 20, 10, 8, rotation_degrees=7).body,
    "rack_and_pinion_placed": lib.rack_and_pinion(1, 24, 12, 5, backlash=0.05, bore=4,
        origin=(100, 30, 20), direction=(1, 0, 0), roll_degrees=30).body,
    "joint": lib.joint("skf-ge-6-c").body,
    "joint_placed": lib.joint("skf-ge-6-c", tilt_degrees=13,
        origin=(100,30,20), direction=(1,0,0), roll_degrees=90).body,
    "linear_actuator": lib.linear_actuator("l12-50-210-12-s", extension=50).body,
    "linear_actuator_placed": lib.linear_actuator("l12-50-210-12-s", extension=23.5,
        origin=(100,30,20), direction=(1,0,0), roll_degrees=90).body,
    "bldc": lib.bldc("hobbywing-30415200").body,
    "bldc_placed": lib.bldc("hobbywing-30415200", origin=(100, 30, 20),
                             direction=(1, 0, 0), roll_degrees=90).body,
    "gearmotor": lib.gearmotor("pololu-2367").body,
    "gearmotor_placed": lib.gearmotor("pololu-2367", origin=(100, 30, 20),
                                     direction=(1, 0, 0), roll_degrees=30).body,
    "esp_board": esp.body,
    "pi_board": pi_board.body,
    "pi5_board": lib.board("pi-5", origin=(0, 80, 0)).body,
    "camera": lib.board("rpi-camera-module-3", direction=(1, 0, 0)).body,
    "tof": lib.board("pololu-vl53l1x-3415", origin=(0, -40, 0)).body,
    "motor_driver": lib.board("tb6612-adafruit-2448", origin=(40, -40, 0)).body,
    "bus_servo": lib.servo("sts3215", origin=(0, -80, 0), direction=(0, 1, 0)).body,
    "bus_servo_bay": lib.servo("sts3215", origin=(0, -80, 0), direction=(0, 1, 0)).bay(),
    "wheel": lib.wheel("pololu-1430", origin=(100, 30, 20), direction=(1, 0, 0)).body,
    "wheel_bay": lib.wheel("pololu-1430").bay(),
    "tyre": lib.wheel("pololu-1430", origin=(100, 30, 20), direction=(1, 0, 0)).tyre().body,
    "foot_pad": lib.foot_pad("essentra-462178", direction=(0, 0, -1)).body,
    "foot_pad_bay": lib.foot_pad("essentra-462178").bay(),
    "pwm_board": pwm.body,
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
    result has the solid or compound type the worker can serialize.
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
            "spur_gear", "spur_gear_placed", "rack", "rack_placed",
            "rack_and_pinion", "rack_and_pinion_placed",
            "joint", "joint_placed", "bldc", "bldc_placed", "linear_actuator", "linear_actuator_placed",
            "gearmotor", "gearmotor_placed",
            "esp_board", "pi_board", "pwm_board",
            "pi5_board", "camera", "tof", "motor_driver", "bus_servo", "bus_servo_bay",
            "wheel", "wheel_bay", "tyre", "foot_pad", "foot_pad_bay",
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
            expected_type = "compound" if output["name"] in {
                "joint", "joint_placed", "rack_and_pinion", "rack_and_pinion_placed"} else "solid"
            assert output["type"] == expected_type, output
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


def test_linear_actuator_spec_and_discovery():
    actuator = _lib().linear_actuator(" L12-50-210-12-S ", extension=23.5)
    assert (actuator.family, actuator.part_number) == ("linear_actuator", "l12-50-210-12-s")
    spec = actuator.spec
    assert spec["mount_centres_mm"] == [[0, 0, 0], [0, 0, 125.5]]
    assert (spec["rated_voltage_v"], spec["gear_ratio"], spec["maximum_duty_percent"]) == (12, 210, 20)
    assert (spec["maximum_lifted_force_n"], spec["unloaded_speed_mm_s"]) == (80, 6.5)
    assert (spec["peak_power_force_n"], spec["peak_power_speed_mm_s"]) == (62, 3.2)
    assert spec["temperature_range_c"] == [-10, 50]
    assert spec["older_step_spacing_excess_mm"] == .5
    assert "distinct operating points" in spec["rating_notes"]
    assert "not guaranteed powered-reachable" in spec["switch_notes"]
    assert len(spec["sources"]) == 2 and len(spec["approximate"]) == 3
    spec["temperature_range_c"][0] = 99
    assert catalog.linear_actuator_spec("l12-50-210-12-s")["temperature_range_c"][0] == -10
    assert _lib().catalog()["linear_actuators"]["skus"] == ["l12-50-210-12-s"]
    assert "linear_actuator" in {row["name"] for row in library_listing()["exports"]}
    with pytest.raises(LibraryError):
        _lib().linear_actuator("l12-50-210-12-s", direction=(0, 0, 0))


@pytest.mark.parametrize("extension", [-.01, 50.01, float("nan"), float("inf"), True, "20", None])
def test_linear_actuator_rejects_invalid_extension(extension):
    with pytest.raises(LibraryError, match="extension"):
        _lib().linear_actuator("l12-50-210-12-s", extension=extension)


@pytest.mark.parametrize("sku", ["l12-50-210-12-p", "l12-100-210-12-s", "l12-50-100-12-s", "l12-50-210-6-s", "", None])
def test_linear_actuator_rejects_unsupported_variants(sku):
    with pytest.raises(CatalogError, match="Unknown linear actuator"):
        _lib().linear_actuator(sku)


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle").FREECADCMD is None,
    reason="No FreeCADCmd binary available for L12 interface checks.",
)
def test_linear_actuator_real_kernel_interfaces_and_placement(tmp_path):
    import subprocess
    from test_cadexd_lifecycle import CADEX_ROOT, FREECADCMD
    driver = tmp_path / "l12_interfaces.py"
    driver.write_text(L12_INTERFACE_DRIVER)
    completed = subprocess.run(
        [str(FREECADCMD), "-c",
         f"import sys; sys.path.insert(0, {str(CADEX_ROOT)!r}); exec(open({str(driver)!r}).read())"],
        capture_output=True, text=True, timeout=120,
    )
    assert "L12-INTERFACES-OK" in completed.stdout, completed.stdout + completed.stderr


L12_INTERFACE_DRIVER = r'''
import FreeCAD as App
import Part
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import create_domain_api
from cadex_library_api import create_library_api
from cadex_part_worker import build_part_shape
pack = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]
lib = create_library_api(create_domain_api(pack.domain, pack.api_exports, pack.output_types))

for extension in (0, 23.5, 50):
    shape = build_part_shape(lib.linear_actuator("l12-50-210-12-s", extension=extension).body.to_payload())
    assert shape.isValid() and len(shape.Solids) == 1
    # Read actual cylindrical surfaces, not returned metadata or recipe inputs.
    centres = sorted({round(f.Surface.Center.z, 7) for f in shape.Faces
                      if isinstance(f.Surface, Part.Cylinder)
                      and abs(f.Surface.Radius - 2.125) < 1e-7
                      and abs(abs(f.Surface.Axis.x) - 1) < 1e-7})
    assert centres == [0, 102 + extension], centres
    bb = shape.BoundBox
    for actual, expected in zip((bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax),
                                (-7.45, 7.45, -7.5, 10.5, -4.5, 106.5+extension)):
        assert abs(actual-expected) < 1e-6, (actual, expected)
    probes = []
    for z, half_width in ((0, 4), (102 + extension, 3)):
        # Axis and near bore wall: void through the full mounting width.
        for x in (-half_width + .1, 0, half_width - .1):
            probes.extend([((x, 0, z), False), ((x, 2.1, z), False),
                           ((x, 2.2, z), True), ((x, 3, z), True)])
        probes.append(((half_width + .1, 3, z), False))
    probes.extend([((0, 0, 20), True), ((5.9, 5.9, 70), True),
                   ((0, 0, 96 + extension), True),
                   ((4.6, 0, 96 + extension), False)])
    # Cyclic rotation + translation, mapping (x,y,z) to (100+z,30+x,20+y).
    placed = build_part_shape(lib.linear_actuator("l12-50-210-12-s", extension=extension,
        origin=(100,30,20), direction=(1,0,0), roll_degrees=90).body.to_payload())
    assert placed.isValid() and len(placed.Solids) == 1
    assert abs(placed.Volume - shape.Volume) < 1e-6
    for point, occupied in probes:
        assert shape.isInside(App.Vector(*point), 1e-7, True) == occupied, point
        x, y, z = point
        assert placed.isInside(App.Vector(100+z, 30+x, 20+y), 1e-7, True) == occupied, point
print('L12-INTERFACES-OK')
'''


def test_joint_spec_and_discovery():
    joint = _lib().joint(" SKF-GE-6-C ", tilt_degrees=6.5)
    assert (joint.family, joint.part_number) == ("joint", "skf-ge-6-c")
    spec = joint.spec
    assert [spec[k] for k in ("bore_dia_mm", "outside_dia_mm", "inner_width_mm",
                              "outer_width_mm", "sphere_dia_mm")] == [6,14,6,4,10]
    assert (spec["basic_dynamic_load_n"], spec["basic_static_load_n"], spec["mass_g"]) == (3600,9000,4)
    assert spec["shaft_shoulder_dia_range_mm"] == [7.4,8]
    assert spec["housing_opening_dia_range_mm"] == [9.5,12.7]
    assert spec["tilt_degrees"] == 6.5 and spec["maximum_tilt_degrees"] == 13
    assert "conditional" in spec["tilt_notes"] and "not allowable" in spec["rating_notes"]
    assert spec["source_revision"] == "BU/P1 06116/1 EN, May 2013, printed pages 132–133"
    assert len(spec["source_sha256"]) == 64 and len(spec["approximate"]) == 3
    spec["shaft_shoulder_dia_range_mm"][0] = 99
    assert catalog.joint_spec("skf-ge-6-c")["shaft_shoulder_dia_range_mm"] == [7.4,8]
    assert _lib().catalog()["joints"]["skus"] == ["skf-ge-6-c"]
    entry = next(row for row in library_listing()["exports"] if row["name"] == "joint")
    assert "tilt_degrees" in entry["signature"] and "two-solid compound" in entry["description"]
    with pytest.raises(LibraryError):
        _lib().joint("skf-ge-6-c", direction=(0,0,0))


@pytest.mark.parametrize("tilt", [-13.01,13.01,float("nan"),float("inf"),True,"0",None])
def test_joint_rejects_invalid_tilt(tilt):
    with pytest.raises(LibraryError, match="tilt_degrees"):
        _lib().joint("skf-ge-6-c", tilt_degrees=tilt)


@pytest.mark.parametrize("sku", ["ge-6-c","skf-ge-6-e","skf-ge-8-c","",None])
def test_joint_rejects_unsupported_variants(sku):
    with pytest.raises(CatalogError, match="Unknown joint"):
        _lib().joint(sku)


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle").FREECADCMD is None,
    reason="No FreeCADCmd binary available for joint interface checks.",
)
def test_joint_real_worker_interfaces_and_placement(tmp_path):
    import subprocess
    from test_cadexd_lifecycle import CADEX_ROOT, FREECADCMD
    driver = tmp_path / "joint_interfaces.py"
    driver.write_text(JOINT_INTERFACE_DRIVER)
    completed = subprocess.run(
        [str(FREECADCMD), "-c",
         f"import sys; sys.path.insert(0, {str(CADEX_ROOT)!r}); exec(open({str(driver)!r}).read())"],
        capture_output=True, text=True, timeout=120,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "GE6C-NOMINAL-OK" in completed.stdout, completed.stdout + completed.stderr


JOINT_INTERFACE_DRIVER = r'''
import json
import math
import FreeCAD as App
import Part


def cylinder(radius, length):
    return Part.makeCylinder(radius, length, App.Vector(0, 0, -length / 2))


from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import create_domain_api
from cadex_library_api import create_library_api
from cadex_part_worker import build_part_shape
pack = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]
lib = create_library_api(create_domain_api(pack.domain, pack.api_exports, pack.output_types))


def construct(tilt, **placement):
    shape = build_part_shape(lib.joint("skf-ge-6-c", tilt_degrees=tilt,
                                      **placement).body.to_payload())
    assert shape.isValid() and len(shape.Solids) == 2
    return sorted(shape.Solids, key=lambda solid: -solid.Volume)


for invalid in (-13.01, 13.01, float('nan'), float('inf')):
    try:
        construct(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError(invalid)

for tilt in (-13, 0, 6.5, 13):
    outer, inner = construct(tilt)
    rotation = App.Rotation(App.Vector(0, 1, 0), tilt)
    # Independently integrated spherical slabs minus the cylindrical bore.
    expected_volumes = (math.pi * (196 - (100 - 16/3)), 78 * math.pi)
    for shape, volume in zip((outer, inner), expected_volumes):
        assert shape.isValid() and len(shape.Solids) == 1
        assert abs(shape.Volume - volume) < 1e-6
    assert outer.common(inner).Volume < 1e-7
    assert abs(outer.BoundBox.XLength - 14) < 1e-7
    assert abs(outer.BoundBox.ZLength - 4) < 1e-7
    # Read actual mating surfaces, independently of construction metadata.
    for shape, radius, axis in ((outer, 7, App.Vector(0, 0, 1)),
                                (inner, 3, rotation.multVec(App.Vector(0, 0, 1)))):
        faces = [f for f in shape.Faces if isinstance(f.Surface, Part.Cylinder)]
        assert len(faces) == 1
        surface = faces[0].Surface
        assert abs(surface.Radius - radius) < 1e-7
        assert abs(abs(surface.Axis.dot(axis)) - 1) < 1e-7
        spheres = [f.Surface for f in shape.Faces if isinstance(f.Surface, Part.Sphere)]
        assert len(spheres) == 1 and abs(spheres[0].Radius - 5) < 1e-7
    # Full nominal bore remains open along the tilted shaft axis.
    shaft = cylinder(2.99, 20)
    shaft.rotate(App.Vector(), App.Vector(0, 1, 0), tilt)
    assert outer.common(shaft).Volume < 1e-7
    assert inner.common(shaft).Volume < 1e-7
    # Source limiting shoulders: shaft da max=8; housing Da min=9.5.
    # No fillets or fit tolerances; test both sides of the nominal faces.
    for side in (-1, 1):
        shoulder = Part.makeCylinder(4, 2, App.Vector(0, 0, side * 3),
                                     App.Vector(0, 0, side))
        shoulder.rotate(App.Vector(), App.Vector(0, 1, 0), tilt)
        assert outer.common(shoulder).Volume < 1e-7
        housing = Part.makeCylinder(7, 2, App.Vector(0, 0, side * 2),
                                    App.Vector(0, 0, side))
        opening = Part.makeCylinder(4.75, 2, App.Vector(0, 0, side * 2),
                                    App.Vector(0, 0, side))
        assert inner.common(housing.cut(opening)).Volume < 1e-7
    probes = [((6.9, 0, 0), True), ((7.1, 0, 0), False),
              ((5.1, 0, 0), True), ((4.9, 0, 0), False),
              ((6, 0, 1.9), True), ((6, 0, 2.1), False)]
    inner_probes = [((2.9, 0, 0), False), ((3.1, 0, 0), True),
                    ((4.9, 0, 0), True), ((5.1, 0, 0), False),
                    ((3.5, 0, 2.9), True), ((3.5, 0, 3.1), False)]
    placed_rings = construct(tilt, origin=(100,30,20), direction=(1,0,0), roll_degrees=90)
    placement = App.Placement(App.Vector(100,30,20),
                              App.Rotation(App.Vector(1,1,1), 120))
    for shape, points, local in ((outer, probes, App.Rotation()),
                                 (inner, inner_probes, rotation)):
        placed = placed_rings[0 if shape is outer else 1]
        assert placed.isValid() and abs(placed.Volume - shape.Volume) < 1e-6
        surface = next(f.Surface for f in placed.Faces
                       if isinstance(f.Surface, Part.Cylinder))
        assert abs(surface.Radius - (7 if shape is outer else 3)) < 1e-7
        axis = placement.Rotation.multVec(local.multVec(App.Vector(0,0,1)))
        assert abs(abs(surface.Axis.dot(axis)) - 1) < 1e-7
        sphere = next(f.Surface for f in placed.Faces
                      if isinstance(f.Surface, Part.Sphere))
        assert abs(sphere.Radius - 5) < 1e-7
        assert (sphere.Center - placement.Base).Length < 1e-7
        for point, occupied in points:
            point = local.multVec(App.Vector(*point))
            assert shape.isInside(point, 1e-7, True) == occupied
            assert placed.isInside(placement.multVec(point), 1e-7, True) == occupied
    print('GE6C ' + json.dumps({'tilt_deg': tilt,
          'outer_volume_mm3': round(outer.Volume, 6),
          'inner_volume_mm3': round(inner.Volume, 6),
          'overlap_mm3': outer.common(inner).Volume,
          'canonical_and_placed_probes': 24}))
print('GE6C-NOMINAL-OK')
'''


# -- involute gearing (ADR-233) ---------------------------------------------


def test_gear_standard_pins():
    std = catalog.GEAR_STANDARD
    assert (std["pressure_angle_degrees"], std["addendum_coefficient"],
            std["dedendum_coefficient"], std["root_clearance_coefficient"],
            std["whole_depth_coefficient"]) == (20, 1, 1.25, 0.25, 2.25)
    assert std["preferred_modules_mm"][:9] == [1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6]
    assert std["preferred_modules_mm"][-1] == 50 and len(std["preferred_modules_mm"]) == 18
    assert (std["minimum_teeth"], std["undercut_teeth"], std["maximum_teeth"]) == (6, 17, 200)
    assert std["basic_rack"].startswith("ISO 53") and std["module_series"].startswith("ISO 54")
    assert len(std["sources"]) == 2


def test_gear_spec_numbers_and_undercut_note():
    spec = catalog.gear_spec(2, 20)
    assert [spec[k] for k in ("pitch_diameter_mm", "tip_diameter_mm", "root_diameter_mm")] == [40, 44, 35]
    assert abs(spec["base_diameter_mm"] - 40 * math.cos(math.radians(20))) < 1e-9
    assert abs(spec["tooth_thickness_mm"] - math.pi) < 1e-9
    assert abs(spec["circular_pitch_mm"] - 2 * math.pi) < 1e-9
    assert (spec["addendum_mm"], spec["dedendum_mm"], spec["whole_depth_mm"]) == (2, 2.5, 4.5)
    assert "ISO 53" in spec["standard"] and len(spec["approximate"]) == 2
    assert "undercut" in catalog.gear_spec(2, 12)["approximate"][-1]
    rack = catalog.gear_spec(1.5, 4, rack=True)
    assert abs(rack["length_mm"] - 6 * math.pi) < 1e-9 and "tip_diameter_mm" not in rack
    spec["sources"].clear()
    assert catalog.gear_spec(2, 20)["sources"]


@pytest.mark.parametrize("module,teeth", [(1.1, 20), (0.5, 20), (True, 20), ("2", 20),
                                          (float("nan"), 20), (2, 5), (2, 201), (2, 20.0),
                                          (2, True), (2, "20")])
def test_gear_spec_refusals(module, teeth):
    with pytest.raises(CatalogError):
        catalog.gear_spec(module, teeth)


def _outline_points(part):
    wire = _ops(part.body, "wire")[0]
    assert wire.properties["closed"] is True
    return wire.arguments[0]


def test_spur_gear_recipe_and_spec():
    gear = _lib().spur_gear(2, 20, 10, bore=6)
    assert (gear.family, gear.part_number) == ("gear", "m2z20")
    assert gear.spec["face_width_mm"] == 10 and gear.spec["bore_mm"] == 6
    points = _outline_points(gear)
    radii = [math.hypot(x, y) for x, y, z in points]
    assert all(z == 0 for _, _, z in points)
    assert abs(min(radii) - 17.5) < 1e-9 and abs(max(radii) - 22) < 1e-9
    assert sum(abs(r - 22) < 1e-9 for r in radii) == 3 * 20
    assert points[0] == pytest.approx((17.5 * math.cos(-math.pi / 20), 17.5 * math.sin(-math.pi / 20), 0))
    area = sum(x0 * y1 - x1 * y0 for (x0, y0, _), (x1, y1, _) in zip(points, points[1:] + points[:1])) / 2
    assert math.pi * 17.5 ** 2 < area < math.pi * 22 ** 2
    assert list(_ops(gear.body, "extrude")[0].arguments[1]) == [0, 0, 10]
    assert len(_ops(gear.body, "face")) == 1 and len(_ops(gear.body, "cut")) == 1
    assert _ops(gear.body, "cylinder")[0].arguments[0] == 3
    plain = _lib().spur_gear(1, 8, 5)
    assert plain.spec["bore_mm"] is None and not _ops(plain.body, "cut")
    assert plain.body.operation == "extrude"
    assert "undercut" in plain.spec["approximate"][-1]
    with pytest.raises(LibraryError, match="root diameter"):
        _lib().spur_gear(2, 20, 10, bore=35)
    with pytest.raises(LibraryError):
        _lib().spur_gear(2, 20, 0)
    with pytest.raises(CatalogError):
        _lib().spur_gear(2, 3, 10)


def test_rack_recipe_and_spec():
    rack = _lib().rack(2, 10, 10, 8)
    assert (rack.family, rack.part_number) == ("rack", "m2z10")
    assert rack.spec["height_mm"] == 8 and abs(rack.spec["length_mm"] - 20 * math.pi) < 1e-9
    points = _outline_points(rack)
    ys = sorted({round(y, 9) for _, y, _ in points})
    assert ys == [-6, -2.5, 2]
    assert sum(y == 2 for _, y, _ in points) == 20
    assert min(x for x, _, _ in points) == 0
    assert abs(max(x for x, _, _ in points) - 20 * math.pi) < 1e-9
    tips = [x for x, y, _ in points if y == 2]
    assert abs(tips[-1] - (math.pi - (math.pi / 2 - 2 * math.tan(math.radians(20))))) < 1e-9
    area = sum(x0 * y1 - x1 * y0 for (x0, y0, _), (x1, y1, _) in zip(points, points[1:] + points[:1])) / 2
    assert 20 * math.pi * 3.5 < area < 20 * math.pi * 8
    assert rack.body.operation == "extrude"
    with pytest.raises(LibraryError, match="whole depth"):
        _lib().rack(2, 10, 10, 4.5)
    with pytest.raises(CatalogError):
        _lib().rack(2, 0, 10, 8)


def test_gears_listing():
    families = _lib().catalog()["gears"]
    assert families["preferred_modules_mm"][0] == 1 and families["teeth_range"] == [6, 200]
    names = {entry["name"] for entry in library_listing()["exports"]}
    assert {"spur_gear", "rack"} <= names
    entry = next(row for row in library_listing()["exports"] if row["name"] == "spur_gear")
    assert "bore" in entry["signature"] and "ISO 53" in entry["description"]


# -- rack and pinion (ADR-234) ----------------------------------------------


def test_rack_and_pinion_spec_numbers():
    spec = catalog.rack_and_pinion_spec(2, 20, 10)
    assert (spec["pitch_radius_mm"], spec["centre_distance_mm"], spec["radial_shift_mm"]) == (20, 20, 0)
    assert (spec["backlash_mm"], spec["root_clearance_mm"]) == (0, 0.5)
    assert abs(spec["travel_per_revolution_mm"] - 40 * math.pi) < 1e-9
    assert abs(spec["travel_per_degree_mm"] * 360 - spec["travel_per_revolution_mm"]) < 1e-9
    assert abs(spec["rack_length_mm"] - 20 * math.pi) < 1e-9
    assert spec["pinion"]["tip_diameter_mm"] == 44 and spec["rack"]["teeth"] == 10
    assert "ISO 53" in spec["standard"] and len(spec["approximate"]) == 4
    played = catalog.rack_and_pinion_spec(2, 20, 10, backlash=0.2)
    shift = 0.2 / (2 * math.tan(math.radians(20)))
    assert abs(played["radial_shift_mm"] - shift) < 1e-12
    assert abs(played["centre_distance_mm"] - (20 + shift)) < 1e-12
    assert abs(played["root_clearance_mm"] - (0.5 + shift)) < 1e-12
    assert "undercut" in catalog.rack_and_pinion_spec(2, 12, 10)["approximate"][2]


@pytest.mark.parametrize("module,pinion,rack,backlash", [
    (2, 20, 10, 0.21), (2, 20, 10, -0.01), (2, 20, 10, True), (2, 20, 10, "0"),
    (2, 20, 10, float("inf")), (2, 5, 10, 0), (2, 20, 0, 0), (7, 20, 10, 0), (1.1, 20, 10, 0)])
def test_rack_and_pinion_spec_refusals(module, pinion, rack, backlash):
    with pytest.raises(CatalogError):
        catalog.rack_and_pinion_spec(module, pinion, rack, backlash=backlash)


def test_rack_and_pinion_recipe_and_spec():
    lib = _lib()
    pair = lib.rack_and_pinion(2, 20, 10, 8)
    assert (pair.family, pair.part_number) == ("rack_and_pinion", "m2z20r10")
    assert pair.body.operation == "compound" and len(pair.body.arguments[0]) == 2
    pinion_body, rack_body = pair.body.arguments[0]
    # The pinion is rolled so tooth 0 points at the rack; the rack sits one
    # pitch radius below the axis with a tooth space under the axis.
    pinion_transform = _ops(pinion_body, "transform")[0]
    assert pinion_transform.properties["rotation_degrees"] == pytest.approx(90)
    assert list(pinion_transform.properties["rotation_axis"]) == pytest.approx([0, 0, -1])
    rack_transform = _ops(rack_body, "transform")[0]
    assert list(rack_transform.properties["translation"]) == pytest.approx([-5 * 2 * math.pi, -20, 0])
    assert pair.spec["rack_height_mm"] == 7 and pair.spec["bore_mm"] is None
    assert pair.spec["face_width_mm"] == 8 and pair.spec["rotation_degrees"] == 0
    assert pair.spec["rack_x_range_mm"] == pytest.approx([-10 * math.pi, 10 * math.pi])
    assert pair.spec["datums"]["rack_pitch_line"] == "Y = -20, along X"
    assert pair.spec["centre_distance_mm"] == 20
    # A phase turns the pinion and slides the rack by the matching travel.
    turned = lib.rack_and_pinion(2, 20, 10, 8, rotation_degrees=9, bore=6, rack_height=10,
                                 backlash=0.2)
    shift = 0.2 / (2 * math.tan(math.radians(20)))
    travel = 40 * math.pi * 9 / 360
    assert turned.spec["rack_travel_mm"] == pytest.approx(travel)
    assert turned.spec["rack_x_range_mm"][0] == pytest.approx(-10 * math.pi + travel)
    assert turned.spec["bore_mm"] == 6 and turned.spec["rack_height_mm"] == 10
    pinion_body, rack_body = turned.body.arguments[0]
    pinion_transform = _ops(pinion_body, "transform")[0]
    assert pinion_transform.properties["rotation_degrees"] == pytest.approx(81)
    assert list(_ops(rack_body, "transform")[0].properties["translation"]) == pytest.approx(
        [-10 * math.pi + travel, -20 - shift, 0])
    assert len(_ops(turned.body, "cut")) == 1
    placed = lib.rack_and_pinion(2, 20, 10, 8, origin=(100, 30, 20), direction=(1, 0, 0))
    assert placed.body.operation == "transform"
    with pytest.raises(LibraryError, match="rotation_degrees"):
        lib.rack_and_pinion(2, 20, 10, 8, rotation_degrees=float("nan"))
    with pytest.raises(LibraryError, match="whole depth"):
        lib.rack_and_pinion(2, 20, 10, 8, rack_height=4)
    with pytest.raises(LibraryError, match="root diameter"):
        lib.rack_and_pinion(2, 20, 10, 8, bore=40)
    with pytest.raises(CatalogError, match="backlash"):
        lib.rack_and_pinion(2, 20, 10, 8, backlash=1)
    names = {entry["name"] for entry in library_listing()["exports"]}
    assert "rack_and_pinion" in names
    assert "rack_and_pinion" in _lib().catalog()["gears"]["notes"]


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle").FREECADCMD is None,
    reason="No FreeCADCmd binary available for mesh checks.",
)
def test_rack_and_pinion_real_kernel_mesh_and_clearance(tmp_path):
    import subprocess
    from test_cadexd_lifecycle import CADEX_ROOT, FREECADCMD
    driver = tmp_path / "mesh_checks.py"
    driver.write_text(RACK_AND_PINION_KERNEL_DRIVER)
    completed = subprocess.run(
        [str(FREECADCMD), "-c",
         f"import sys; sys.path.insert(0, {str(CADEX_ROOT)!r}); exec(open({str(driver)!r}).read())"],
        capture_output=True, text=True, timeout=600,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "RACK-AND-PINION-OK" in completed.stdout, completed.stdout + completed.stderr


RACK_AND_PINION_KERNEL_DRIVER = r"""
import json
import math
import FreeCAD as App
import Part
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import create_domain_api
from cadex_library_api import create_library_api
from cadex_part_worker import build_part_shape
pack = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]
lib = create_library_api(create_domain_api(pack.domain, pack.api_exports, pack.output_types))
MESH_TOLERANCE_MM3 = 1e-6


def members(pair):
    shape = build_part_shape(pair.body.to_payload())
    assert shape.isValid() and shape.ShapeType == "Compound" and len(shape.Solids) == 2
    spec = pair.spec
    probe_radius = ((0 if spec["bore_mm"] is None else spec["bore_mm"] / 2)
                    + spec["pinion"]["root_diameter_mm"] / 2) / 2
    probe = App.Vector(0, probe_radius, spec["face_width_mm"] / 2)
    pinion, rack = sorted(shape.Solids, key=lambda solid: not solid.isInside(probe, 1e-7, True))
    assert pinion.isInside(probe, 1e-7, True) and not rack.isInside(probe, 1e-7, True)
    return shape, pinion, rack


for module, pinion_teeth, rack_teeth, width, bore, backlash in (
        (2, 20, 10, 8, None, 0.0), (1, 24, 12, 5, 4, 0.05), (2, 20, 10, 8, 6, 0.2)):
    pitch_angle = 360.0 / pinion_teeth
    spec = lib.rack_and_pinion(module, pinion_teeth, rack_teeth, width, bore=bore, backlash=backlash).spec
    shift = spec["radial_shift_mm"]
    expected_flank_gap = backlash * math.cos(math.radians(20)) / 2
    commons, gaps = [], []
    phases = [pitch_angle * k / 7 for k in range(7)] + [2.5 * pitch_angle, -1.3 * pitch_angle]
    for rotation in phases:
        pair = lib.rack_and_pinion(module, pinion_teeth, rack_teeth, width, bore=bore,
                                   backlash=backlash, rotation_degrees=rotation)
        shape, pinion, rack = members(pair)
        # Clearance: the pinion tip clears the rack root, and the rack tip the
        # pinion root, by 0.25 m plus the backlash shift, measured on the solids.
        tip_radius = max(math.hypot(v.X, v.Y) for v in pinion.Vertexes)
        root_radius = min(r for r in (math.hypot(v.X, v.Y) for v in pinion.Vertexes)
                          if bore is None or r > bore / 2 + 1e-6)
        rack_ys = sorted({round(v.Y, 6) for v in rack.Vertexes})
        rack_root_y, rack_tip_y = rack_ys[1], rack_ys[2]
        assert abs((-rack_root_y - tip_radius) - (0.25 * module + shift)) < 1e-6
        assert abs((-rack_tip_y - root_radius) - (0.25 * module + shift)) < 1e-6
        assert abs(rack.BoundBox.XMin - pair.spec["rack_x_range_mm"][0]) < 1e-6
        # Mesh: no common volume at any phase, and the flanks apart by the
        # backlash's normal gap backlash*cos(20)/2, never less (the sampled
        # chords sit inside the involute) and over it by at most the chord sag.
        common = pinion.common(rack).Volume
        gap = pinion.distToShape(rack)[0]
        commons.append(common)
        gaps.append(gap)
        assert common < MESH_TOLERANCE_MM3, (module, pinion_teeth, rotation, common)
        assert expected_flank_gap - 1e-6 <= gap <= expected_flank_gap + 1e-3 * module, (
            module, pinion_teeth, rotation, gap)
    print("MESH " + json.dumps({"module": module, "pinion_teeth": pinion_teeth, "backlash_mm": backlash,
                                "phases": len(phases), "max_common_mm3": max(commons),
                                "flank_gap_mm": [round(min(gaps), 5), round(max(gaps), 5)],
                                "expected_flank_gap_mm": round(expected_flank_gap, 5)}))

# Negative controls: the mesh test must see a bad mesh. A rack shifted by half a
# pitch collides tooth on tooth, and an unshifted 12-tooth pinion (undercut is
# warned, not generated) interferes with the rack tip below its base circle.
base = lib.rack_and_pinion(2, 20, 10, 8)
_shape, pinion, rack = members(base)
rack.translate(App.Vector(math.pi, 0, 0))
collision = pinion.common(rack).Volume
assert collision > 10.0, collision
worst = 0.0
for rotation in [18.0 * k / 7 for k in range(7)]:
    _shape, pinion, rack = members(lib.rack_and_pinion(2, 12, 10, 8, rotation_degrees=rotation))
    worst = max(worst, pinion.common(rack).Volume)
assert worst > MESH_TOLERANCE_MM3, worst
print("CONTROLS " + json.dumps({"half_pitch_collision_mm3": round(collision, 3),
                                "z12_interference_mm3": round(worst, 6)}))

# Placement keeps the compound's volume and its member count.
canonical = build_part_shape(lib.rack_and_pinion(1, 24, 12, 5, bore=4, backlash=0.05).body.to_payload())
placed = build_part_shape(lib.rack_and_pinion(1, 24, 12, 5, bore=4, backlash=0.05, origin=(100, 30, 20),
                                              direction=(1, 0, 0), roll_degrees=30).body.to_payload())
assert len(placed.Solids) == 2 and abs(placed.Volume - canonical.Volume) < 1e-6
assert abs(placed.BoundBox.XMin - 100) < 1e-6 and abs(placed.BoundBox.XLength - 5) < 1e-6
print("RACK-AND-PINION-OK")
"""


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle").FREECADCMD is None,
    reason="No FreeCADCmd binary available for gear checks.",
)
def test_gear_real_kernel_diameters_and_volumes(tmp_path):
    import subprocess
    from test_cadexd_lifecycle import CADEX_ROOT, FREECADCMD
    driver = tmp_path / "gear_checks.py"
    driver.write_text(GEAR_KERNEL_DRIVER)
    completed = subprocess.run(
        [str(FREECADCMD), "-c",
         f"import sys; sys.path.insert(0, {str(CADEX_ROOT)!r}); exec(open({str(driver)!r}).read())"],
        capture_output=True, text=True, timeout=300,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "GEARS-OK" in completed.stdout, completed.stdout + completed.stderr


GEAR_KERNEL_DRIVER = r"""
import json
import math
import FreeCAD as App
import Part
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import create_domain_api
from cadex_library_api import create_library_api
from cadex_part_worker import build_part_shape
pack = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]
lib = create_library_api(create_domain_api(pack.domain, pack.api_exports, pack.output_types))


def build(part):
    shape = build_part_shape(part.body.to_payload())
    assert shape.isValid() and shape.ShapeType == "Solid" and len(shape.Solids) == 1
    return shape


for module, teeth, width, bore in ((2, 20, 10, 6), (2, 8, 4, None), (1, 60, 6, 4), (1, 6, 3, None)):
    gear = lib.spur_gear(module, teeth, width, bore=bore)
    shape = build(gear)
    tip = module * (teeth + 2) / 2
    root = module * (teeth - 2.5) / 2
    assert abs(shape.BoundBox.XMax - tip) < 1e-7 and abs(shape.BoundBox.XMin + tip) < 1e-7
    assert abs(shape.BoundBox.ZLength - width) < 1e-7 and abs(shape.BoundBox.ZMin) < 1e-7
    radii = sorted(math.hypot(v.X, v.Y) for v in shape.Vertexes)
    outer = [r for r in radii if bore is None or r > bore / 2 + 1e-6]
    assert abs(outer[0] - root) < 1e-7 and abs(outer[-1] - tip) < 1e-7
    bore_volume = 0.0 if bore is None else math.pi * (bore / 2) ** 2 * width
    assert math.pi * root ** 2 * width - bore_volume < shape.Volume < math.pi * tip ** 2 * width
    cylinders = [f.Surface for f in shape.Faces if isinstance(f.Surface, Part.Cylinder)]
    if bore is None:
        assert not cylinders
    else:
        assert len(cylinders) == 1 and abs(cylinders[0].Radius - bore / 2) < 1e-7
        assert not shape.isInside(App.Vector(0, 0, width / 2), 1e-7, True)
    # Pitch-circle tooth thickness: the chord across tooth 0 at the pitch
    # radius spans the standard's pi*m/2 arc, measured on the built solid.
    pitch = module * teeth / 2
    half = math.pi / (2 * teeth)
    assert shape.isInside(App.Vector(pitch * math.cos(half * 0.98), pitch * math.sin(half * 0.98), width / 2), 1e-7, True)
    assert not shape.isInside(App.Vector(pitch * math.cos(half * 1.02), pitch * math.sin(half * 1.02), width / 2), 1e-7, True)
    assert shape.isInside(App.Vector(tip - 1e-3, 0, width / 2), 1e-7, True)
    assert not shape.isInside(App.Vector(tip + 1e-3, 0, width / 2), 1e-7, True)
    placed = build(lib.spur_gear(module, teeth, width, bore=bore, origin=(100, 30, 20),
                                 direction=(1, 0, 0), roll_degrees=30))
    assert abs(placed.Volume - shape.Volume) < 1e-6
    assert abs(placed.BoundBox.XMin - 100) < 1e-7 and abs(placed.BoundBox.XLength - width) < 1e-7
    print("GEAR " + json.dumps({"module": module, "teeth": teeth, "volume_mm3": round(shape.Volume, 3),
                                "faces": len(shape.Faces)}))

for module, teeth, width, height in ((2, 10, 10, 8), (1.5, 4, 6, 5)):
    rack = lib.rack(module, teeth, width, height)
    shape = build(rack)
    length = teeth * math.pi * module
    assert abs(shape.BoundBox.XMin) < 1e-7 and abs(shape.BoundBox.XLength - length) < 1e-7
    assert abs(shape.BoundBox.YMax - module) < 1e-7 and abs(shape.BoundBox.YLength - height) < 1e-7
    assert abs(shape.BoundBox.ZLength - width) < 1e-7
    ys = sorted({round(v.Y, 6) for v in shape.Vertexes})
    assert ys == [round(module - height, 6), round(-1.25 * module, 6), round(module, 6)]
    assert abs((ys[-1] - ys[1]) - 2.25 * module) < 1e-7
    tips = sorted({round(v.X, 6) for v in shape.Vertexes if abs(v.Y - module) < 1e-6})
    assert len(tips) == 2 * teeth
    # Pitch: consecutive tooth centres are pi*m apart; thickness at the
    # pitch line is pi*m/2, probed just inside and outside a flank.
    centres = [(tips[i] + tips[i + 1]) / 2 for i in range(0, len(tips), 2)]
    assert all(abs((b - a) - math.pi * module) < 1e-5 for a, b in zip(centres, centres[1:]))
    quarter = math.pi * module / 4
    assert shape.isInside(App.Vector(centres[0] + quarter * 0.98, 0, width / 2), 1e-7, True)
    assert not shape.isInside(App.Vector(centres[0] + quarter * 1.02, 0, width / 2), 1e-7, True)
    # Exact area: back strip plus one trapezoid per tooth (flank sum from ISO 53).
    flank_sum = math.pi * module / 2 + 0.25 * module * math.tan(math.radians(20))
    area = length * (height - 2.25 * module) + teeth * 2.25 * module * flank_sum
    assert abs(shape.Volume - area * width) < 1e-6
    placed = build(lib.rack(module, teeth, width, height, origin=(100, 30, 20),
                            direction=(0, 1, 0), roll_degrees=90))
    assert abs(placed.Volume - shape.Volume) < 1e-6
    print("RACK " + json.dumps({"module": module, "teeth": teeth, "volume_mm3": round(shape.Volume, 3)}))
print("GEARS-OK")
"""


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle").FREECADCMD is None,
    reason="No FreeCADCmd binary available for a wheel sweep.",
)
def test_a_catalog_wheel_sweeps_clean_round_its_catalog_motor(tmp_path):
    """ADR-487: a full turn of the wheel joint leaves the shaft and bore apart.

    orun1's balancer trial measured 4.26 mm³ between the turning 1430's D
    bore and the N20's static D shaft, so no catalog wheel on its catalog
    motor could pass a sweep. The shaft really turns with the wheel; the
    round bore is what lets the sweep measure it so. This drives the
    engine's own sweep over the two library bodies as documented: the
    wheel on the shaft clear of the boss, the hinge on the shaft axis, -180..180.
    """
    import json
    import subprocess
    from test_cadexd_lifecycle import CADEX_ROOT, FREECADCMD
    from CadexFitReport import MAXIMUM_COMMON_VOLUME_MM3

    driver = tmp_path / "wheel_sweep.py"
    driver.write_text(WHEEL_SWEEP_DRIVER)
    completed = subprocess.run(
        [str(FREECADCMD), "-c",
         f"import sys; sys.path.insert(0, {str(CADEX_ROOT)!r}); exec(open({str(driver)!r}).read())"],
        capture_output=True, text=True, timeout=300,
    )
    line = next((l for l in completed.stdout.splitlines() if l.startswith("WHEEL-SWEEP ")), None)
    assert line, completed.stdout + completed.stderr
    result = json.loads(line[len("WHEEL-SWEEP "):])
    (solved,) = result["baseline"]
    assert solved["common_volume_mm3"] <= MAXIMUM_COMMON_VOLUME_MM3
    (joint,) = result["report"]["joints"]
    assert joint["status"] == "complete" and joint["sample_count"] == 25, json.dumps(joint)[:900]
    (pair,) = joint["pairs"]
    assert pair["relative_motion"] is True
    assert pair["maximum_common_volume_mm3"] <= MAXIMUM_COMMON_VOLUME_MM3, pair


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle").FREECADCMD is None,
    reason="No FreeCADCmd binary available for a wheel build.",
)
def test_the_catalog_wheel_is_a_spoked_rim_and_a_separate_tyre(tmp_path):
    """ADR-489: the 1430 is built as its STEP model reads, not as a slab.

    orun1's balancer lost twice to designs whose wheels read as wheels;
    both losses cited the catalog wheel being a plain disc. On the real
    kernel: the wheel's volume is the pinned spoked body's, well under the
    disc it replaced; a point between two spokes is open air; and the tyre
    is a second solid, seated on the rim, touching and not overlapping it,
    whose volume and the wheel's together are within 3% of Pololu's STEP.
    """
    import json
    import subprocess
    from test_cadexd_lifecycle import CADEX_ROOT, FREECADCMD

    driver = tmp_path / "wheel_build.py"
    driver.write_text(WHEEL_BUILD_DRIVER)
    completed = subprocess.run(
        [str(FREECADCMD), "-c",
         f"import sys; sys.path.insert(0, {str(CADEX_ROOT)!r}); exec(open({str(driver)!r}).read())"],
        capture_output=True, text=True, timeout=300,
    )
    line = next((l for l in completed.stdout.splitlines() if l.startswith("WHEEL-BUILD ")), None)
    assert line, completed.stdout + completed.stderr
    result = json.loads(line[len("WHEEL-BUILD "):])
    spec = catalog.wheel_spec("pololu-1430")
    disc = math.pi * 40.0 ** 2 * 10.0
    assert result["wheel"]["valid"] and result["wheel"]["solids"] == 1
    assert result["wheel"]["volume"] == pytest.approx(spec["wheel_volume_mm3"], abs=1.0)
    assert result["wheel"]["volume"] < 0.3 * disc
    assert result["between_spokes_inside"] is False
    assert result["on_spoke_inside"] is True
    assert result["tyre"]["valid"] and result["tyre"]["solids"] == 1
    assert result["tyre"]["volume"] == pytest.approx(spec["tyre_volume_mm3"], abs=1.0)
    assert result["common_volume"] < 1e-6 and result["distance"] < 1e-6
    step_volume = 19220.1  # Pololu's STEP model, measured in this kernel (ADR-489)
    total = result["wheel"]["volume"] + result["tyre"]["volume"]
    assert abs(total - step_volume) / step_volume < 0.03
    assert result["outer_dia"] == pytest.approx(80.0, abs=0.01)


WHEEL_BUILD_DRIVER = r'''
import json, math
import FreeCAD as App
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import create_domain_api
from cadex_library_api import create_library_api
from cadex_part_worker import build_part_shape
pack = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]
lib = create_library_api(create_domain_api(pack.domain, pack.api_exports, pack.output_types))
wheel = lib.wheel("pololu-1430")
w = build_part_shape(wheel.body.to_payload())
t = build_part_shape(wheel.tyre().body.to_payload())
def facts(shape):
    return {"volume": shape.Volume, "solids": len(shape.Solids), "valid": shape.isValid()}
mid = 6.75  # the wheel's centre plane, from the hub tip
probe = lambda r, deg: App.Vector(r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg)), mid)
print("WHEEL-BUILD " + json.dumps({
    "wheel": facts(w), "tyre": facts(t),
    "between_spokes_inside": w.isInside(probe(22.0, 30.0), 1e-6, True),
    "on_spoke_inside": w.isInside(probe(22.0, 0.0) + App.Vector(0, 1.8, 0), 1e-6, True),
    "common_volume": w.common(t).Volume, "distance": w.distToShape(t)[0],
    "outer_dia": t.optimalBoundingBox().XLength,
}))
'''


WHEEL_SWEEP_DRIVER = r'''
import json
import FreeCAD as App
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import create_domain_api
from cadex_library_api import create_library_api
from cadex_part_worker import build_part_shape
from cadex_assembly_worker import _measure_clearance, _measure_joint_sweeps
pack = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]
lib = create_library_api(create_domain_api(pack.domain, pack.api_exports, pack.output_types))
D = App.newDocument("WheelSweep")
motor = D.addObject("Part::Feature", "motor")
motor.Shape = build_part_shape(lib.gearmotor("pololu-2367").body.to_payload())
wheel = D.addObject("Part::Feature", "wheel")
# On the shaft axis, its hub 0.3 mm clear of the 0.7 mm boss.
wheel.Shape = build_part_shape(lib.wheel("pololu-1430", origin=(0, 0, 1.0)).body.to_payload())
D.recompute()
components = {"motor": motor, "wheel": wheel}
data = {"motor": {"grounded": True}, "wheel": {"grounded": False}}
# Both connectors at the world origin on the shaft axis, each in its own
# component's frame: the shape's placement becomes the object's.
def axis(obj):
    return {"matrix": list(obj.Placement.inverse().toMatrix().A)}
joints = {"wheel": {"kind": "revolute", "suppressed": False, "parameters": {},
    "angle_limits_degrees": [-180, 180], "length_limits_mm": None,
    "connectors": [{"component_output": "motor", "local_frame": axis(motor)},
                   {"component_output": "wheel", "local_frame": axis(wheel)}]}}
baseline = _measure_clearance(components)
report = _measure_joint_sweeps(components, data, joints, baseline,
                               {"sweep_step_degrees": 15}, True)
print("WHEEL-SWEEP " + json.dumps(dict(baseline=baseline, report=report)))
'''
