# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The mounting check: what holds each purchased part (ADR-486).

orun1's D3 asks the product to say, for every purchased part, which printed
part holds it and by what -- screws through its mounting holes, its own
bay, a press fit, a drive's output -- and to report a part held by nothing
or held only by sitting inside a shell. The block rides in ``fit_summary``,
so it reaches every build reply the CLI and the shell show the model.

Three layers, each failing without the others: the library remembers each
body's mounting-hole axes and which body each ``.bay()`` cavity was cut
for; the project worker stamps them beside the definition (never inside
it, so no digest moves); and ``CadexFitReport.mounting_summary`` judges a
published ``inspect scope=clearance`` value. The two real-kernel fixtures
build an assembly that passes and one that fails through a live ``cadexd``.
"""

from __future__ import annotations

import math

import pytest

import CadexFitReport
from CadexFitReport import fit_summary, fit_view, mounting_summary


IDENTITY = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]


def _row(name, family=None, part_number="x", *, axes=(), houses=(), source=None,
         matrix=IDENTITY, bounds=None):
    row = {"component": name, "source_output": source or name,
           "placement": {"matrix": list(matrix)}}
    if family:
        row["catalog"] = {"family": family, "part_number": part_number}
        row["mount_axes"] = [{"origin": list(o), "axis": list(a)} for o, a in axes]
    if houses:
        row["houses"] = list(houses)
    if bounds:
        row["source_facts"] = {"bounds_mm": {"min": list(bounds[0]), "max": list(bounds[1])}}
    return row


def _pair(first, second, distance, volume=0.0, **extra):
    return {"first": first, "second": second, "distance_mm": distance,
            "common_volume_mm3": volume, **extra}


def _by_component(block):
    return {row["component"]: row for row in block["reported"] + block["held"]}


# --------------------------------------------------------------------------
# the judgement, on published values
# --------------------------------------------------------------------------


def test_a_bolt_on_a_hole_axis_into_a_printed_part_holds_by_screws():
    value = {"components": [
        _row("plate"),
        _row("board", "board", "b", axes=[((2.0, 2.0, 0.0), (0, 0, 1)),
                                          ((20.0, 2.0, 0.0), (0, 0, 1))]),
        _row("bolt0", "bolt", "m2.5x6-socket", axes=[((2.0, 2.0, 1.6), (0, 0, 1))]),
    ], "pairs": [
        _pair("plate", "board", 0.0), _pair("bolt0", "board", 0.0),
        _pair("bolt0", "plate", 0.0, 2.1),
    ]}
    block = mounting_summary(value)
    assert block["verdict"] == "pass"
    board = _by_component(block)["board"]
    assert (board["status"], board["by"], board["holders"]) == ("held", "screws", ["plate"])
    assert board["detail"].startswith("1 of 2 mounting holes carry a bolt (bolt0)")
    # A fastener is what holds, never what is checked.
    assert block["purchased_count"] == 1


def test_a_bolt_beside_the_hole_axis_is_not_a_screw_through_it():
    value = {"components": [
        _row("plate"),
        _row("board", "board", "b", axes=[((2.0, 2.0, 0.0), (0, 0, 1))]),
        _row("bolt0", "bolt", "m2.5x6-socket", axes=[((3.0, 2.0, 1.6), (0, 0, 1))]),
    ], "pairs": [
        _pair("plate", "board", 0.0), _pair("bolt0", "board", 0.0),
        _pair("bolt0", "plate", 0.0, 2.1),
    ]}
    board = _by_component(mounting_summary(value))["board"]
    assert board["status"] == "contact only"
    assert board["holders"] == ["plate"]


def test_the_hole_axis_is_carried_through_the_solved_placement():
    # The board's component is moved 50 mm in X; its hole goes with it.
    moved = list(IDENTITY)
    moved[3] = 50.0
    value = {"components": [
        _row("plate"),
        _row("board", "board", "b", axes=[((2.0, 2.0, 0.0), (0, 0, 1))], matrix=moved),
        _row("bolt0", "bolt", "m2.5x6-socket", axes=[((52.0, 2.0, 1.6), (0, 0, -1))]),
    ], "pairs": [
        _pair("plate", "board", 0.0), _pair("bolt0", "board", 0.0),
        _pair("bolt0", "plate", 0.0, 2.1),
    ]}
    assert _by_component(mounting_summary(value))["board"]["by"] == "screws"


def _n20(bolt_size, bolt_dia):
    """An N20 face (two M1.6 tapped holes) under a plate, both holes bolted."""

    hole = {"thread_dia_mm": 1.6}
    motor = _row("motor", "gearmotor", "pololu-2367")
    motor["mount_axes"] = [{"origin": [x, 0.0, 0.0], "axis": [0, 0, 1], **hole}
                           for x in (-4.5, 4.5)]
    rows = [_row("plate"), motor]
    pairs = [_pair("plate", "motor", 0.0)]
    for i, x in enumerate((-4.5, 4.5)):
        bolt = _row(f"bolt{i}", "bolt", f"{bolt_size}x3-socket")
        bolt["mount_axes"] = [{"origin": [x, 0.0, 2.0], "axis": [0, 0, 1],
                               "bolt_dia_mm": bolt_dia}]
        rows.append(bolt)
        pairs += [_pair(f"bolt{i}", "motor", 0.0, 0.2), _pair(f"bolt{i}", "plate", 0.0)]
    return {"components": rows, "pairs": pairs}


def _board_with_one_bolt(*bite, tapped=False):
    """A board with one bolt on its hole axis, head on the plate (ADR-492)."""
    value = {"components": [
        _row("plate"),
        _row("board", "board", "b", axes=[((2.0, 2.0, 0.0), (0, 0, 1))]),
        _row("bolt0", "bolt", "m2.5x6-socket", axes=[((2.0, 2.0, 1.6), (0, 0, 1))]),
        _row("nut0", "nut", "m2.5-hex"),
    ], "pairs": [
        _pair("plate", "board", 0.0), _pair("bolt0", "board", 0.0),
        _pair("bolt0", "plate", 0.0), _pair("bolt0", "nut0", 0.0),
        _pair("nut0", "plate", 0.0),
    ]}
    for pair in value["pairs"]:
        if pair["first"] == "bolt0" and pair["second"] in bite:
            pair["common_volume_mm3"] = 1.5
    if tapped:
        value["components"][1]["mount_axes"][0]["thread_dia_mm"] = 2.5
    return _by_component(mounting_summary(value))["board"]


def test_a_bolt_holds_only_if_its_shank_threads_into_something():
    # ADR-491's no-ledge servo: the head sat within 0.5 mm of the printed
    # pocket while the shank hung in the bay's lead room, and it counted.
    loose = _board_with_one_bolt()
    assert loose["status"] == "contact only"
    assert loose["unthreaded"] == ["bolt0"]
    assert "threads into nothing" in loose["detail"]
    # A printed thread, the part's own tapped hole, or a nut each hold it.
    for bite in ("plate", "board", "nut0"):
        held = _board_with_one_bolt(bite)
        assert (held["status"], held["by"], held["holders"]) == (
            "held", "screws", ["plate"]), bite
        assert "unthreaded" not in held
    # A tapped hole is modelled as an open bore: reaching it is its thread.
    tapped = _board_with_one_bolt(tapped=True)
    assert (tapped["status"], tapped["by"]) == ("held", "screws")


def _bolt_in_a_plate(volume, *, sweep_volume=None, moving=False):
    """An M2x6 bolt sharing ``volume`` with a printed plate (ADR-492)."""
    value = {"available": True, "components": [
        _row("plate"), _row("arm"),
        _row("bolt0", "bolt", "m2x6-socket", axes=[((0.0, 0.0, 0.0), (0, 0, 1))]),
    ], "pairs": [
        _pair("bolt0", "plate", 0.0, volume), _pair("arm", "plate", 5.0),
        _pair("arm", "bolt0", 3.0),
    ]}
    if sweep_volume is not None:
        first = "arm" if moving else "plate"
        value["clearance_sweep"] = {"status": "complete", "joints": [{
            "joint": "hinge", "status": "complete", "unit": "degrees", "pairs": [{
                "first": first, "second": "bolt0", "minimum_distance_mm": 0.0,
                "maximum_common_volume_mm3": sweep_volume, "relative_motion": moving}]}]}
    return fit_summary(value)


def test_a_bolts_thread_in_a_printed_part_is_engagement_not_an_intersection():
    # An M2x6 in a 1.6 mm tap drill shares pi/4 (4 - 2.56) 6 = 6.79 mm^3;
    # its thread may reach the 1.567 mm minor diameter, 7.28 mm^3.
    ring = math.pi / 4.0 * (2.0 ** 2 - 1.567 ** 2) * 6.0
    fit = _bolt_in_a_plate(math.pi / 4.0 * (4.0 - 1.6 ** 2) * 6.0)
    assert fit["verdict"] == "pass" and fit["threaded_count"] == 1, fit
    assert _bolt_in_a_plate(ring)["verdict"] == "pass"
    # Through solid, or a pilot finer than the minor diameter, is a collision.
    solid = _bolt_in_a_plate(math.pi / 4.0 * 4.0 * 6.0)
    assert solid["verdict"] == "fail" and solid["threaded_count"] == 0
    assert solid["failing"][0]["status"] == "intersection"
    assert _bolt_in_a_plate(ring * 1.01)["verdict"] == "fail"


def test_a_threaded_bolt_keeps_its_allowance_only_in_its_own_part_through_motion():
    held = _bolt_in_a_plate(6.0, sweep_volume=6.0)
    assert held["sweep"]["failing"] == [], held["sweep"]
    # A link swinging into the bolt is a collision whatever the volume.
    swung = _bolt_in_a_plate(6.0, sweep_volume=1.0, moving=True)
    assert [row["status"] for row in swung["sweep"]["failing"]] == ["intersection"]


def test_the_thread_depths_are_the_catalogs():
    import CadexCatalog

    assert CadexFitReport.THREAD_MINOR_DIAMETER_MM == {
        row["nominal_dia_mm"]: row["minor_dia_mm"]
        for row in CadexCatalog.METRIC_THREADS.values()}


def test_a_bolt_must_match_a_tapped_holes_thread_to_hold():
    # Trial 1 of orun1's balancer counted M2 bolts in the N20's M1.6 face
    # holes as screws (ADR-488): on the axis, but the wrong thread.
    block = mounting_summary(_n20("m2", 2.0))
    motor = _by_component(block)["motor"]
    assert block["verdict"] == "reported"
    assert motor["status"] == "contact only"
    assert motor["misfits"] == [
        "bolt0: an M2 bolt in an M1.6 tapped hole",
        "bolt1: an M2 bolt in an M1.6 tapped hole",
    ]
    assert "do not fit" in motor["detail"]
    motor = _by_component(mounting_summary(_n20("m1.6", 1.6)))["motor"]
    assert (motor["status"], motor["by"]) == ("held", "screws")
    assert "misfits" not in motor


def test_a_bolt_may_not_be_larger_than_a_clearance_hole():
    def board(bolt_dia):
        value = {"components": [
            _row("plate"),
            _row("board", "board", "b", axes=[((2.0, 2.0, 0.0), (0, 0, 1))]),
            _row("bolt0", "bolt", "x", axes=[((2.0, 2.0, 1.6), (0, 0, 1))]),
        ], "pairs": [
            _pair("plate", "board", 0.0), _pair("bolt0", "board", 0.0),
            _pair("bolt0", "plate", 0.0, 2.1),
        ]}
        value["components"][1]["mount_axes"][0]["hole_dia_mm"] = 2.5
        value["components"][2]["mount_axes"][0]["bolt_dia_mm"] = bolt_dia
        return _by_component(mounting_summary(value))["board"]

    assert board(2.5)["by"] == "screws"
    assert board(2.0)["by"] == "screws"
    loose = board(3.0)
    assert loose["status"] == "contact only"
    assert loose["misfits"] == ["bolt0: an M3 bolt through a 2.5 mm hole"]


def test_a_hole_or_bolt_with_no_size_facts_is_judged_by_axis_alone():
    # Revisions accepted before ADR-488 published no sizes: still judged.
    value = _n20("m2", 2.0)
    for row in value["components"]:
        for axis in row.get("mount_axes") or []:
            axis.pop("thread_dia_mm", None)
            axis.pop("bolt_dia_mm", None)
    assert _by_component(mounting_summary(value))["motor"]["by"] == "screws"


def test_a_bay_holds_only_at_the_parts_own_placement():
    value = {"components": [
        _row("cradle", houses=["battery"]),
        _row("battery", "battery", "pack"),
    ], "pairs": [_pair("cradle", "battery", 1.0)]}
    battery = _by_component(mounting_summary(value))["battery"]
    assert (battery["status"], battery["by"], battery["holders"]) == ("held", "bay", ["cradle"])
    moved = list(IDENTITY)
    moved[11] = 30.0
    value["components"][1]["placement"]["matrix"] = moved
    value["pairs"] = [_pair("cradle", "battery", 25.0)]
    assert _by_component(mounting_summary(value))["battery"]["status"] == "held by nothing"


def test_a_wheel_well_is_not_a_seat_and_a_wheel_rides_its_motors_output():
    value = {"components": [
        _row("body", houses=["wheel"]),
        _row("motor", "gearmotor", "pololu-2367", axes=[((4.5, 0.0, 0.0), (0, 0, 1))]),
        _row("wheel", "wheel", "pololu-1430"),
    ], "pairs": [
        _pair("body", "motor", 0.0), _pair("body", "wheel", 3.0),
        _pair("motor", "wheel", 0.0, 4.0),
    ]}
    rows = _by_component(mounting_summary(value))
    # The motor only touches the body: nothing screws it there.
    assert rows["motor"]["status"] == "contact only"
    # ...so the wheel on its shaft is held by nothing either.
    assert rows["wheel"]["status"] == "held by nothing"
    assert "motor" in rows["wheel"]["detail"]


def test_a_tyre_is_held_on_the_rim_of_a_held_wheel_and_freed_with_it():
    """ADR-489: a tyre is its own part, held by the wheel it sits on."""
    def value(motor_screwed):
        components = [
            _row("plate"),
            _row("motor", "gearmotor", "pololu-2367", axes=[((4.5, 0.0, 0.0), (0, 0, 1))]),
            _row("wheel", "wheel", "pololu-1430"),
            _row("tyre", "tyre", "pololu-1430"),
        ]
        pairs = [_pair("plate", "motor", 0.0), _pair("motor", "wheel", 0.0, 4.0),
                 _pair("wheel", "tyre", 0.0), _pair("plate", "tyre", 20.0)]
        if motor_screwed:
            components.append(_row("screw", "bolt", "m1.6x4-socket",
                                   axes=[((4.5, 0.0, 1.0), (0, 0, 1))]))
            pairs += [_pair("screw", "motor", 0.0, 1.0), _pair("screw", "plate", 0.0, 1.0)]
            components[1]["mount_axes"][0]["thread_dia_mm"] = 1.6
            components[-1]["mount_axes"][0]["bolt_dia_mm"] = 1.6
        return {"components": components, "pairs": pairs}

    rows = _by_component(mounting_summary(value(True)))
    assert rows["wheel"]["status"] == "held", rows["wheel"]
    assert (rows["tyre"]["status"], rows["tyre"]["by"], rows["tyre"]["holders"]) == (
        "held", "rim", ["wheel"])
    # A loose motor frees its wheel, and the wheel its tyre.
    rows = _by_component(mounting_summary(value(False)))
    assert rows["wheel"]["status"] == "held by nothing"
    assert rows["tyre"]["status"] == "held by nothing"
    assert "wheel" in rows["tyre"]["detail"]


def test_a_tyre_off_its_wheel_is_held_by_nothing():
    value = {"components": [_row("tyre", "tyre", "pololu-1430"), _row("plate")],
             "pairs": [_pair("plate", "tyre", 12.0)]}
    assert _by_component(mounting_summary(value))["tyre"]["status"] == "held by nothing"


def test_a_horn_on_a_held_servo_is_held_on_its_output():
    value = {"components": [
        _row("bracket"),
        _row("servo", "servo", "sts3215", axes=[((5.0, 0.0, 0.0), (0, 0, -1))]),
        _row("screw", "bolt", "m2x6-socket", axes=[((5.0, 0.0, 3.0), (0, 0, 1))]),
        _row("horn", "servo_horn", "sts3215-disc"),
        _row("bearing", "bearing", "608"),
    ], "pairs": [
        _pair("bracket", "servo", 0.0), _pair("screw", "servo", 0.0, 1.0),
        _pair("screw", "bracket", 0.0, 1.0), _pair("horn", "servo", 0.0),
        _pair("bearing", "bracket", 0.0, 0.5),
    ]}
    block = mounting_summary(value)
    rows = _by_component(block)
    assert (rows["horn"]["status"], rows["horn"]["by"], rows["horn"]["holders"]) == (
        "held", "output", ["servo"])
    assert (rows["bearing"]["by"], rows["bearing"]["holders"]) == ("press fit", ["bracket"])
    assert block["verdict"] == "pass"


def test_a_part_inside_a_printed_envelope_is_reported_as_inside_a_shell():
    value = {"components": [
        _row("shell", bounds=((0, 0, 0), (100, 60, 40))),
        _row("board", "board", "b", bounds=((40, 20, 10), (60, 40, 12))),
        _row("loose", "board", "b", bounds=((200, 0, 0), (220, 20, 2))),
    ], "pairs": [
        _pair("shell", "board", 6.0), _pair("shell", "loose", 100.0),
        _pair("board", "loose", 140.0),
    ]}
    block = mounting_summary(value)
    rows = _by_component(block)
    assert (rows["board"]["status"], rows["board"]["holders"]) == ("inside shell", ["shell"])
    assert rows["loose"]["status"] == "held by nothing"
    assert block["verdict"] == "reported"
    assert block["reported_count"] == 2 and block["note"] == CadexFitReport.MOUNTING_NOTE


def test_an_unmeasured_pair_is_unknown_never_a_pass():
    value = {"components": [_row("plate"), _row("board", "board", "b")],
             "pairs": [{"first": "plate", "second": "board", "distance_mm": None,
                        "common_volume_mm3": None, "error": "no measurement"}]}
    block = mounting_summary(value)
    assert block["verdict"] == "unknown"
    assert block["reported"][0]["status"] == "unknown"


def test_no_published_components_is_unavailable_and_no_purchase_is_none():
    assert mounting_summary({"pairs": []})["verdict"] == "unavailable"
    # A revision accepted before the stamps: no facts, so no judgement.
    older = _row("board", "board", "b")
    del older["mount_axes"]
    block = mounting_summary({"components": [_row("plate"), older],
                              "pairs": [_pair("plate", "board", 0.0)]})
    assert block["verdict"] == "unavailable" and "new revision" in block["reason"]
    assert mounting_summary({"components": [_row("plate")], "pairs": []})["verdict"] == "none"


def test_the_block_rides_in_the_fit_summary_and_its_view_is_bounded():
    components = [_row("plate")] + [_row(f"b{i:02d}", "board", "b") for i in range(15)]
    value = {"available": True, "components": components,
             "pairs": [_pair("plate", f"b{i:02d}", 50.0) for i in range(15)]}
    fit = fit_summary(value)
    assert fit["mounting"]["reported_count"] == 15
    # Its own verdict: the static fit above it still passes.
    assert fit["verdict"] == "pass" and fit["mounting"]["verdict"] == "reported"
    view = fit_view(fit)["mounting"]
    assert len(view["reported"]) == CadexFitReport.BUILD_VIEW_LIST_LIMIT
    assert view["reported_omitted"] == 3
    assert view["reported_rest"] == "inspect scope=clearance path=/components"


# --------------------------------------------------------------------------
# the library and the stamp
# --------------------------------------------------------------------------


def _staged():
    from test_library import _lib, _part

    return _lib(), _part()


def test_the_library_remembers_hole_axes_and_what_each_bay_houses():
    from cadex_library_api import _definition_key, library_mount_facts

    lib, _ = _staged()
    board = lib.board("bno085-adafruit-4754", origin=(10.0, 0.0, 5.0),
                      direction=(0.0, 0.0, -1.0))
    bolt = lib.bolt("M2.5", 6.0, origin=(1.0, 2.0, 3.0), direction=(1.0, 0.0, 0.0))
    pack = lib.battery("gensace-gea2s100045d")
    bay = pack.bay()
    facts = library_mount_facts()
    holes = facts["axes"][_definition_key(board.body)]
    assert len(holes) == 4
    # Board frame flipped about X onto -Z: local (x, y, 0) -> (10 + x, -y, 5).
    assert holes[0]["origin"] == pytest.approx([12.54, -2.54, 5.0])
    assert holes[0]["axis"] == pytest.approx([0.0, 0.0, -1.0])
    assert facts["axes"][_definition_key(bolt.body)] == [
        {"origin": pytest.approx([1.0, 2.0, 3.0]), "axis": pytest.approx([1.0, 0.0, 0.0]),
         "bolt_dia_mm": 2.5}]
    # What fits each hole travels with it (ADR-488): the board's are
    # clearance holes, the N20's and the bus servo's are tapped.
    assert holes[0]["hole_dia_mm"] == 2.5 and "thread_dia_mm" not in holes[0]
    motor = lib.gearmotor("pololu-2367")
    assert {row["thread_dia_mm"] for row in
            library_mount_facts()["axes"][_definition_key(motor.body)]} == {1.6}
    servo = lib.servo("sts3215")
    assert {row["thread_dia_mm"] for row in
            library_mount_facts()["axes"][_definition_key(servo.body)]} == {2.0}
    assert facts["bays"] == {_definition_key(bay): _definition_key(pack.body)}
    # A pack has no holes: it is housed, not screwed.
    assert _definition_key(pack.body) not in facts["axes"]


def test_the_stamp_names_housed_outputs_and_stays_out_of_the_digest():
    import cadex_project_worker
    from cadex_project_worker import _canonical_json

    lib, part = _staged()
    pack = lib.battery("gensace-gea2s100045d")
    cradle = part.cut(part.box(80.0, 40.0, 10.0, origin=(-40.0, -20.0, 0.0)), [pack.bay()])
    outputs = [
        {"name": "battery", "type": "part", "definition": pack.body.to_payload(),
         "catalog": {"family": "battery", "part_number": "gensace-gea2s100045d"}},
        {"name": "cradle", "type": "part", "definition": cradle.to_payload()},
    ]
    before = [_canonical_json(item["definition"]) for item in outputs]
    cadex_project_worker._stamp_mounting(outputs)
    assert outputs[1]["houses"] == ["battery"]
    # A pack has no holes, and says so: an empty list, not an absent key.
    assert outputs[0]["catalog_mount_axes"] == [] and "houses" not in outputs[0]
    assert "catalog_mount_axes" not in outputs[1]
    assert [_canonical_json(item["definition"]) for item in outputs] == before


# --------------------------------------------------------------------------
# the real kernel: one assembly that passes and one that fails
# --------------------------------------------------------------------------


_PASSING = """
imu = lib.board("bno085-adafruit-4754", origin=(0.0, 0.0, 0.0))
t = imu.spec["thickness_mm"]
bolts = [lib.bolt("M2.5", 6.0, origin=(x, y, t)) for x, y in imu.spec["mount_holes"]]
taps = [part.cylinder(radius=lib.tap_drill("M2.5") / 2.0, height=8.0,
                      origin=(x, y, -6.0)) for x, y in imu.spec["mount_holes"]]
plate = part.cut(part.box(140.0, 60.0, 4.0, origin=(-10.0, -20.0, -4.0)), taps)
pack = lib.battery("gensace-gea2s100045d", origin=(80.0, 10.0, 0.0))
cradle = part.cut(part.box(100.0, 50.0, 12.0, origin=(35.0, -15.0, 0.0)), [pack.bay()])
result = {"plate": plate, "cradle": cradle, "imu": imu.body, "pack": pack.body}
comps = [assembly.component(plate, grounded=True), assembly.component(cradle),
         assembly.component(imu.body), assembly.component(pack.body)]
for i, bolt in enumerate(bolts):
    result["bolt%d" % i] = bolt.body
    comps.append(assembly.component(bolt.body))
for i, comp in enumerate(comps):
    result["component_%d" % i] = comp
asm = assembly.assembly(comps)
result["asm"] = asm
result["diag"] = assembly.solve(asm)
"""

_FAILING = """
imu = lib.board("bno085-adafruit-4754", origin=(0.0, 0.0, 0.0))
plate = part.box(120.0, 60.0, 4.0, origin=(-10.0, -20.0, -4.0))
pack = lib.battery("gensace-gea2s100045d", origin=(70.0, 10.0, 6.0))
shell = part.cut(part.box(100.0, 50.0, 40.0, origin=(25.0, -15.0, 0.0)),
                 [part.box(94.0, 44.0, 37.0, origin=(28.0, -12.0, 3.0))])
imu_far = lib.board("bno085-adafruit-4754", origin=(0.0, 200.0, 0.0))
result = {"plate": plate, "shell": shell, "imu": imu.body, "pack": pack.body,
          "imu_far": imu_far.body}
comps = [assembly.component(plate, grounded=True), assembly.component(shell),
         assembly.component(imu.body), assembly.component(pack.body),
         assembly.component(imu_far.body)]
for i, comp in enumerate(comps):
    result["component_%d" % i] = comp
asm = assembly.assembly(comps)
result["asm"] = asm
result["diag"] = assembly.solve(asm)
"""


_N20_ON_A_PLATE = """
motor = lib.gearmotor("pololu-2367", origin=(0.0, 0.0, 0.0))
holes = [part.cylinder(radius=lib.clearance_hole(SIZE) / 2.0, height=4.0,
                       origin=(x, y, -1.0)) for x, y in motor.spec["mount_holes"]]
shaft = part.cylinder(radius=2.5, height=4.0, origin=(0.0, 0.0, -1.0))
plate = part.cut(part.box(30.0, 14.0, 2.0, origin=(-15.0, -7.0, 0.0)), holes + [shaft])
bolts = [lib.bolt(SIZE, 3.0, origin=(x, y, 2.0)) for x, y in motor.spec["mount_holes"]]
result = {"plate": plate, "motor": motor.body}
comps = [assembly.component(plate, grounded=True), assembly.component(motor.body)]
for i, bolt in enumerate(bolts):
    result["bolt%d" % i] = bolt.body
    comps.append(assembly.component(bolt.body))
for i, comp in enumerate(comps):
    result["component_%d" % i] = comp
asm = assembly.assembly(comps)
result["asm"] = asm
result["diag"] = assembly.solve(asm)
"""


# ADR-490: the motor driver has two holes, both on one edge; two screws
# through them are its whole hold.
_DRIVER_ON_A_PLATE = """
drv = lib.board("tb6612-adafruit-2448", origin=(0.0, 0.0, 0.0))
t = drv.spec["thickness_mm"]
taps = [part.cylinder(radius=lib.tap_drill("m2") / 2.0, height=6.0,
                      origin=(x, y, -5.0)) for x, y in drv.spec["mount_holes"][:COUNT]]
plate = part.box(30.0, 36.0, 4.0, origin=(-5.0, -5.0, -4.0))
plate = part.cut(plate, taps) if taps else plate
bolts = [lib.bolt("m2", 6.0, origin=(x, y, t)) for x, y in drv.spec["mount_holes"][:COUNT]]
result = {"plate": plate, "driver": drv.body}
comps = [assembly.component(plate, grounded=True), assembly.component(drv.body)]
for i, bolt in enumerate(bolts):
    result["bolt%d" % i] = bolt.body
    comps.append(assembly.component(bolt.body))
for i, comp in enumerate(comps):
    result["component_%d" % i] = comp
asm = assembly.assembly(comps)
result["asm"] = asm
result["diag"] = assembly.solve(asm)
"""


# ADR-491: a micro servo screwed down by both tabs into the block its own
# bay is cut from. Without a ledge the lead room is under the lead-side hole.
_SERVO_IN_A_BLOCK = """
sv = lib.servo("mg90s")
spec = sv.spec
z = spec["mount_hole_z_mm"]
top = z + spec["tab_thickness_mm"]
back = spec["shaft_offset_from_front_mm"] - spec["body_length_mm"]
block = part.box(40.0, 18.0, top + spec["case_height_mm"] + 3.0,
                 origin=(back - 10.0, -9.0, -spec["case_height_mm"] - 3.0))
taps = [part.cylinder(radius=lib.tap_drill("m2") / 2.0, height=6.0,
                      origin=(x, y, z - 6.0)) for x, y in spec["mount_holes"]]
block = part.cut(block, [sv.bay(ledge=LEDGE)] + taps)
bolts = [lib.bolt("m2", 6.0, origin=(x, y, top)) for x, y in spec["mount_holes"]]
result = {"block": block, "servo": sv.body}
comps = [assembly.component(block, grounded=True), assembly.component(sv.body)]
for i, bolt in enumerate(bolts):
    result["bolt%d" % i] = bolt.body
    comps.append(assembly.component(bolt.body))
for i, comp in enumerate(comps):
    result["component_%d" % i] = comp
asm = assembly.assembly(comps)
result["asm"] = asm
result["diag"] = assembly.solve(asm)
"""


def _built_mounting(tmp_path, source):
    from test_cadexd_lifecycle import _spawn_cadexd, _stop

    client = None
    try:
        client = _spawn_cadexd()
        assert client.request("open_project", {"project_root": str(tmp_path)})["ok"]
        written = client.request("write_script", {"source": source, "expected_revision": ""})
        assert written["ok"], written
        value = _read_all(client, {"scope": "clearance", "target": ""}, "")
        return fit_view(fit_summary(value))["mounting"]
    finally:
        _stop(client)


def _read_all(client, base, path):
    """Every page of an inspect value, previews resolved (the CLI's reader)."""

    def expand(value):
        if isinstance(value, dict):
            pointer = value.get("inspect_path")
            if isinstance(pointer, str) and value.get("type") in {"object", "array", "string"}:
                return _read_all(client, base, pointer)
            return {key: expand(item) for key, item in value.items()}
        if isinstance(value, list):
            return [expand(item) for item in value]
        return value

    result, offset = None, 0
    while True:
        reply = client.request("inspect", {**base, "path": path, "offset": offset, "limit": 50})
        assert reply["ok"], reply
        value = expand(reply.get("value"))
        if offset == 0:
            result = value
        elif isinstance(result, dict):
            result.update(value)
        elif isinstance(result, list):
            result.extend(value)
        else:
            result += value
        following = (reply.get("page") or {}).get("next_offset")
        if not isinstance(following, int) or following <= offset:
            return result
        offset = following


_NEEDS_KERNEL = pytest.mark.skipif(
    __import__("test_cadexd_lifecycle").FREECADCMD is None,
    reason="No FreeCADCmd binary available for the real-kernel mounting check.",
)


@_NEEDS_KERNEL
def test_a_screwed_board_and_a_bayed_pack_pass_on_the_real_kernel(tmp_path):
    block = _built_mounting(tmp_path, _PASSING)
    rows = {row["component"]: row for row in block["reported"] + block["held"]}
    assert block["verdict"] == "pass", block
    assert block["purchased_count"] == 2
    imu = next(row for row in rows.values() if row["part"] == "board/bno085-adafruit-4754")
    pack = next(row for row in rows.values() if row["part"].startswith("battery/"))
    assert imu["by"] == "screws" and imu["detail"].startswith("4 of 4 mounting holes")
    assert pack["by"] == "bay"
    assert len(imu["holders"]) == 1 and len(pack["holders"]) == 1
    assert imu["holders"] != pack["holders"]


@_NEEDS_KERNEL
def test_a_resting_board_a_shelled_pack_and_a_loose_board_fail_on_the_real_kernel(tmp_path):
    block = _built_mounting(tmp_path, _FAILING)
    assert block["verdict"] == "reported", block
    statuses = sorted(row["status"] for row in block["reported"])
    assert statuses == ["contact only", "held by nothing", "inside shell"]
    assert block["held"] == [] and block["note"] == CadexFitReport.MOUNTING_NOTE
    assert not math.isnan(block["thresholds"]["contact_mm"])


@_NEEDS_KERNEL
@pytest.mark.parametrize("size, status", [("m1.6", "held"), ("m2", "contact only")])
def test_an_n20_is_held_only_by_its_own_m1_6_screws_on_the_real_kernel(tmp_path, size, status):
    block = _built_mounting(tmp_path, _N20_ON_A_PLATE.replace("SIZE", repr(size)))
    motor = next(row for row in block["reported"] + block["held"]
                 if row["part"] == "gearmotor/pololu-2367")
    assert motor["status"] == status, motor
    if status == "held":
        assert motor["by"] == "screws" and motor["detail"].startswith("2 of 2 mounting holes")
    else:
        assert len(motor["misfits"]) == 2
        assert all(m.endswith("an M2 bolt in an M1.6 tapped hole") for m in motor["misfits"])


@_NEEDS_KERNEL
@pytest.mark.parametrize("count, status", [(2, "held"), (0, "contact only")])
def test_the_motor_driver_is_held_by_its_two_screws_on_the_real_kernel(tmp_path, count, status):
    block = _built_mounting(tmp_path, _DRIVER_ON_A_PLATE.replace("COUNT", str(count)))
    drv = next(row for row in block["reported"] + block["held"]
               if row["part"] == "board/tb6612-adafruit-2448")
    assert drv["status"] == status, drv
    if status == "held":
        assert drv["by"] == "screws" and drv["detail"].startswith("2 of 2 mounting holes")



def _servo_block_bites(tmp_path, ledge):
    """The thread each tab bolt cuts into the block, lead side first (mm^3)."""
    from test_cadexd_lifecycle import _spawn_cadexd, _stop

    client = None
    try:
        client = _spawn_cadexd()
        assert client.request("open_project", {"project_root": str(tmp_path)})["ok"]
        source = _SERVO_IN_A_BLOCK.replace("LEDGE", str(ledge))
        written = client.request("write_script", {"source": source, "expected_revision": ""})
        assert written["ok"], written
        value = _read_all(client, {"scope": "clearance", "target": ""}, "")
    finally:
        _stop(client)
    fit = fit_summary(value)
    servo = next(row for row in fit_view(fit)["mounting"]["held"]
                 if row["part"] == "servo/mg90s")
    # ADR-492: a bolt's thread in its tap drill is engagement, never an
    # intersection, so no bolt/block pair fails the static fit.
    assert not [row for row in fit["failing"] if row["status"] == "intersection"
                and "component_0" in (row["first"], row["second"])], fit["failing"]
    bites = {}
    for pair in value["pairs"]:
        names = {pair["first"], pair["second"]}
        for bolt in ("component_2", "component_3"):
            if names == {"component_0", bolt}:
                bites[bolt] = pair["common_volume_mm3"]
    return servo, [bites["component_2"], bites["component_3"]]


@_NEEDS_KERNEL
def test_a_ledged_servo_bay_gives_the_lead_side_screw_its_thread_on_the_real_kernel(tmp_path):
    """ADR-491, ADR-492. Without a ledge the lead-side shank hangs in the lead
    room: its head comes within 0.5 mm of the tab pocket's end wall, which
    once counted it, but it threads nothing and so holds nothing."""
    servo, (lead, free) = _servo_block_bites(tmp_path / "ledged", 4)
    assert servo["by"] == "screws" and servo["detail"].startswith("2 of 2"), servo
    assert "unthreaded" not in servo
    assert lead > 0.5 and free > 0.5 and lead == pytest.approx(free, rel=0.05)
    servo, (lead, free) = _servo_block_bites(tmp_path / "plain", 0)
    assert free > 0.5 and lead < 0.01
    # ADR-492: the lead-side head still comes within 0.5 mm of the pocket,
    # but a shank in the lead room threads nothing, so one hole holds.
    assert servo["by"] == "screws" and servo["detail"].startswith("1 of 2"), servo
    assert servo["unthreaded"] == ["component_2"]


# ADR-493: the regulator on a vertical web, rolled as orun1-t3-balancer
# carries it. BORED is that design's own hold: M2 screws in bores drilled at
# the thread's major diameter, which leaves the thread nothing to cut.
# MOUNTED is the same board on .mounting()'s standoffs, holes and screws.
_REGULATOR_ON_A_WEB = """
web = part.box(11.0, 40.0, 40.0, origin=(-4.0, -20.0, 40.0))
if MOUNTED:
    reg = lib.board("pololu-d36v50f6", origin=(10.0, -12.7, 52.0),
                    direction=(1, 0, 0), roll_degrees=90.0)
    hold = reg.mounting(standoff=3.0)
    web = part.cut(part.fuse([web, *hold.standoffs]), hold.holes)
    bolts = list(hold.screws)
else:
    reg = lib.board("pololu-d36v50f6", origin=(7.0, -12.7, 52.0),
                    direction=(1, 0, 0), roll_degrees=90.0)
    pts = [(-12.7 + u, 52.0 + v) for (u, v) in reg.spec["mount_holes"]]
    web = part.cut(web, [part.cylinder(1.0005, 7.5, origin=(0.5, y, z), direction=(1, 0, 0))
                         for (y, z) in pts])
    bolts = [lib.bolt("m2", 6.0, origin=(7.0 + 1.57, y, z), direction=(1, 0, 0))
             for (y, z) in pts]
result = {"web": web, "regulator": reg.body}
comps = [assembly.component(web, grounded=True), assembly.component(reg.body)]
for i, bolt in enumerate(bolts):
    result["bolt%d" % i] = bolt.body
    comps.append(assembly.component(bolt.body))
for i, comp in enumerate(comps):
    result["component_%d" % i] = comp
asm = assembly.assembly(comps)
result["asm"] = asm
result["diag"] = assembly.solve(asm)
"""


def _regulator_on_a_web(tmp_path, mounted):
    from test_cadexd_lifecycle import _spawn_cadexd, _stop

    client = None
    try:
        client = _spawn_cadexd()
        assert client.request("open_project", {"project_root": str(tmp_path)})["ok"]
        source = _REGULATOR_ON_A_WEB.replace("MOUNTED", str(mounted))
        written = client.request("write_script", {"source": source, "expected_revision": ""})
        assert written["ok"], written
        value = _read_all(client, {"scope": "clearance", "target": ""}, "")
    finally:
        _stop(client)
    fit = fit_summary(value)
    mounting = fit_view(fit)["mounting"]
    reg = next(row for row in mounting["reported"] + mounting["held"]
               if row["part"] == "board/pololu-d36v50f6")
    return fit, reg


@_NEEDS_KERNEL
def test_a_board_on_its_own_mounting_threads_every_screw_on_the_real_kernel(tmp_path):
    """ADR-493. Balancer trial 3's board hold threads 0 of 3; the same board
    on .mounting()'s standoffs and tapping holes threads 3 of 3, and the
    static fit reads that thread as engagement, never an intersection."""
    fit, reg = _regulator_on_a_web(tmp_path / "bored", False)
    assert reg["status"] == "contact only", reg
    assert len(reg["unthreaded"]) == 3
    fit, reg = _regulator_on_a_web(tmp_path / "mounted", True)
    assert reg["status"] == "held" and reg["by"] == "screws", reg
    assert reg["detail"].startswith("3 of 3 mounting holes"), reg
    assert "unthreaded" not in reg and "misfits" not in reg
    # The fixture declares no welds, so its touching pairs read "below
    # clearance"; what matters is that no screw's thread is an intersection.
    assert not [row for row in fit["failing"] if row["status"] == "intersection"], fit["failing"]
    assert fit["threaded_count"] == 3



# ADR-609: an AK45-10 held by .mounting()'s rear stator screws in a printed
# bracket, and a link screwed to its output flange that the joint swings.
# The catalog case is one solid fixed to the stator; the flange turns with
# the link, so the output screws turn with it rather than through the case.
_QDD_ON_A_BRACKET = """
qdd = lib.qdd("cubemars-ak45-10-v3")
hold = qdd.mounting(4.0, face="rear")
bracket = part.cut(part.box(70.0, 70.0, 4.0, origin=(-35.0, -35.0, -49.2)), list(hold.stator.holes))
link = part.cut(part.box(70.0, 34.0, 4.0, origin=(-20.0, -17.0, 0.0)), list(hold.output.holes))
result = {"bracket": bracket, "qdd": qdd.body, "link": link}
c_bracket = assembly.component(bracket, grounded=True)
c_qdd = assembly.component(qdd.body)
c_link = assembly.component(link)
comps = [c_bracket, c_qdd, c_link]
def at(c):
    return assembly.connector(c, "origin", offset={"position": [0.0, 0.0, 0.0], "axis": [0.0, 0.0, 1.0], "angle_degrees": 0.0})
joints = [assembly.joint("fixed", at(c_bracket), at(c_qdd)),
          assembly.joint("revolute", at(c_qdd), at(c_link), angle_limits_degrees=(-90.0, 90.0))]
contacts = [(c_qdd, c_link)]
stators = len(hold.stator.screws)
for i, screw in enumerate(list(hold.stator.screws) + list(hold.output.screws)):
    result["screw%d" % i] = screw.body
    c = assembly.component(screw.body)
    comps.append(c)
    joints.append(assembly.joint("fixed", at(c_link if i >= stators else c_bracket), at(c)))
    contacts.append((c_qdd, c))
for i, comp in enumerate(comps):
    result["component_%d" % i] = comp
for i, joint in enumerate(joints):
    result["joint_%d" % i] = joint
asm = assembly.assembly(comps, joints, contacts=contacts, sweep_step_degrees=15.0)
result["asm"] = asm
result["diag"] = assembly.solve(asm)
"""


def test_a_bolt_in_a_qdd_output_flange_turns_with_it_in_the_sweep():
    """ADR-609, on a published value: an output-axis bolt is not swept
    against its drive, and the output axes never count as holding it."""
    qdd = _row("qdd", "qdd", "cubemars-ak45-10-v3",
               axes=[((10.0, 0.0, -45.2), (0.0, 0.0, -1.0))])
    qdd["mount_axes"].append({"origin": [13.5, 0.0, 0.0], "axis": [0.0, 0.0, 1.0],
                              "thread_dia_mm": 2.5, "output": True})
    bolt = _row("out_bolt", "bolt", "m2.5x10-socket",
                axes=[((13.5, 0.0, 4.0), (0.0, 0.0, 1.0))])
    stray = _row("stray_bolt", "bolt", "m2.5x10-socket",
                 axes=[((0.0, 13.5, 4.0), (0.0, 0.0, 1.0))])
    link = _row("link")
    value = {
        "components": [qdd, bolt, stray, link],
        "pairs": [_pair("out_bolt", "qdd", 0.0), _pair("stray_bolt", "qdd", 0.0),
                  _pair("out_bolt", "link", 0.0), _pair("qdd", "link", 0.0)],
        "clearance_sweep": {"status": "complete", "joints": [{
            "joint": "j", "kind": "revolute", "unit": "degrees", "status": "complete",
            "pairs": [
                {"first": "out_bolt", "second": "qdd", "minimum_distance_mm": 0.0,
                 "maximum_common_volume_mm3": 12.0, "relative_motion": True},
                {"first": "stray_bolt", "second": "qdd", "minimum_distance_mm": 0.0,
                 "maximum_common_volume_mm3": 12.0, "relative_motion": True},
            ]}]},
    }
    assert CadexFitReport.output_bolt_pairs(value) == {frozenset(("out_bolt", "qdd"))}
    sweep = CadexFitReport.sweep_summary(value)
    assert [(r["first"], r["status"]) for r in sweep["failing"]] == [
        ("stray_bolt", "intersection")]
    # The output bolt touches the drive and the link on an output axis: that
    # holds the link to the flange, never the drive in place.
    assert _by_component(mounting_summary(value))["qdd"]["status"] != "held"
    # Overlapping the drive at the solved pose already, it turns with nothing.
    value["pairs"][0]["common_volume_mm3"] = 1.0
    assert CadexFitReport.output_bolt_pairs(value) == set()


@_NEEDS_KERNEL
def test_a_qdd_on_its_own_mounting_is_held_and_its_output_screws_turn_on_the_real_kernel(tmp_path):
    """ADR-608, ADR-609: the AK45-10 on .mounting()'s rear screws is held by
    them; neither side's screws intersect it at the solved pose or through
    the swing, though the raw sweep shows the output screws in the case."""
    from test_cadexd_lifecycle import _spawn_cadexd, _stop

    client = None
    try:
        client = _spawn_cadexd()
        assert client.request("open_project", {"project_root": str(tmp_path)})["ok"]
        written = client.request("write_script", {"source": _QDD_ON_A_BRACKET,
                                                  "expected_revision": ""})
        assert written["ok"], written
        value = _read_all(client, {"scope": "clearance", "target": ""}, "")
    finally:
        _stop(client)
    fit = fit_summary(value)
    view = fit_view(fit)
    qdd = next(row for row in view["mounting"]["reported"] + view["mounting"]["held"]
               if row["part"] == "qdd/cubemars-ak45-10-v3")
    assert (qdd["status"], qdd["by"]) == ("held", "screws"), qdd
    # 6 front and 4 rear stator holes; the 3 output holes never count. The
    # rear screws at 90 and 270 degrees also lie on two front holes' axes
    # (23.5 against 23.75 mm out), so 4 screws carry 6 of the 10.
    assert qdd["detail"].startswith("6 of 10 mounting holes"), qdd
    assert qdd["detail"].count("component_") == 4, qdd
    assert "unthreaded" not in qdd and "misfits" not in qdd
    assert view["mounting"]["verdict"] == "pass", view["mounting"]
    assert fit["verdict"] == "pass", fit["failing"]
    turning = CadexFitReport.output_bolt_pairs(value)
    assert len(turning) == 3
    sweep = fit["sweep"]
    assert sweep["joints_complete"] == 1 and sweep["failing_count"] == 0, sweep["failing"]
    raw = [row for joint in value["clearance_sweep"]["joints"] for row in joint["pairs"]
           if frozenset((row["first"], row["second"])) in turning]
    assert len(raw) == 3 and all(row["maximum_common_volume_mm3"] > 1.0 for row in raw), raw
