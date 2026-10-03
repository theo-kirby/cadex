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
