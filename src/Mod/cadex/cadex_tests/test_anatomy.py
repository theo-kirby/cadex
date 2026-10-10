# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A creature's moving anatomy, declared and measured (ADR-613, ADR-614).

In the cbase sweep no agent-designed deinonychus, heron or leopard gave the
head, jaw, tail, forelimbs or wings a joint, and nothing the agents read
said so. ``assembly.anatomy(region, components, reason=)`` names the
regions; the ``anatomy`` block every build reply carries says, per region,
which joints move it and whether one is driven, and finds every large
welded piece sticking out of a rigid body whether or not it was declared.

Three halves: the **declaration** (the API refuses what a reader of the
script could see), the **stamp** (the worker publishes graph facts beside
the definition), and the **summary** (pure graph arithmetic over the stamp
and the inventory's boxes), served as ``inspect scope=anatomy``. None of it
touches ``CadexdProtocol.OP_ARG_SPECS``: ``inspect`` already takes a scope.
"""

from __future__ import annotations

import pytest

import CadexAnatomy as anatomy
from cadex_assembly_api import AssemblyDomainAPI
from cadex_assembly_worker import _anatomy_stamp
from cadex_domain_api import _DOMAIN_OPERATION_OUTPUT_TYPES
from CadexInspection import capture_inspection, complete_inspection
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from CadexScriptedRuntime import describe_project_api
from test_inventory_scope import _service, _store


def _api() -> AssemblyDomainAPI:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return AssemblyDomainAPI(pack.api_exports, pack.output_types)


def _source(name: str) -> dict[str, str]:
    return {"document_uid": "doc", "object_name": name}


# -- the declaration (ADR-613) ---------------------------------------------

def test_anatomy_is_an_intermediate_and_never_an_output() -> None:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    assert "anatomy" in pack.api_exports
    assert "anatomy" not in pack.output_types
    assert _DOMAIN_OPERATION_OUTPUT_TYPES["assembly"]["anatomy"] == "anatomy"
    assert "anatomy" in _api().exported_names


def test_describe_api_lists_the_declaration_and_the_assembly_argument() -> None:
    api = describe_project_api()
    exports = api["domains"]["assembly"]["exports"]
    (listed,) = [entry for entry in exports if entry["name"] == "anatomy"]
    for parameter in ("region", "components", "reason"):
        assert parameter in listed["signature"], parameter
    assert listed["description"].startswith("Name one moving region of the machine")
    (assembly,) = [entry for entry in exports if entry["name"] == "assembly"]
    assert "anatomy" in assembly["signature"]


def test_a_region_carries_its_components_and_reason_into_the_assembly() -> None:
    api = _api()
    torso, tail = api.component(_source("torso")), api.component(_source("tail"))
    weld = api.joint("fixed", api.connector(torso), api.connector(tail))
    region = api.anatomy("  tail ", [tail], reason="ossified:  raptor tails were stiff")
    assert region.output_type == "anatomy" and region.arguments == (tail,)
    assert region.properties["region"] == "tail"
    assert region.properties["reason"] == "ossified: raptor tails were stiff"
    built = api.assembly([torso, tail], [weld], anatomy=[region])
    assert list(built.properties["anatomy"]) == [region]
    # No anatomy keeps the definition byte-identical to one written before it.
    assert "anatomy" not in api.assembly([torso, tail], [weld]).properties


@pytest.mark.parametrize("region, components, reason, message", [
    ("", None, None, "region name"),
    ("x" * 49, None, None, "region name"),
    ("neck", [], None, "at least 1"),
    ("neck", None, "  ", "the reason this region is rigid"),
    ("neck", None, 3, "the reason this region is rigid"),
])
def test_the_declaration_refuses_what_a_reader_could_see(region, components, reason, message) -> None:
    api = _api()
    part = api.component(_source("part"))
    with pytest.raises(ValueError, match=message):
        api.anatomy(region, [part] if components is None else components, reason=reason)


def test_the_assembly_refuses_a_region_it_cannot_place() -> None:
    api = _api()
    a, b, stray = (api.component(_source(n)) for n in ("a", "b", "stray"))
    joint = api.joint("revolute", api.connector(a), api.connector(b))
    with pytest.raises(ValueError, match="not listed in components"):
        api.assembly([a, b], [joint], anatomy=[api.anatomy("tail", [stray])])
    with pytest.raises(ValueError, match="already declared"):
        api.assembly([a, b], [joint], anatomy=[api.anatomy("neck", [a]), api.anatomy("neck", [b])])
    with pytest.raises(ValueError, match="belongs to one region"):
        api.assembly([a, b], [joint], anatomy=[api.anatomy("neck", [a, b]), api.anatomy("head", [b])])
    with pytest.raises(ValueError, match="anatomy"):
        api.assembly([a, b], [joint], anatomy=[a])


# -- the stamp (ADR-614) -----------------------------------------------------

def _joint_data(rows):
    return {
        name: {"assembly_output": "asm", "kind": kind, "suppressed": suppressed,
               "connectors": [{"component_output": first}, {"component_output": second}]}
        for name, kind, first, second, suppressed in rows
    }


def test_the_stamp_names_regions_joints_and_the_motors_that_drive_them() -> None:
    api = _api()
    torso, neck, head, floor = (api.component(_source(n), world=(n == "floor"))
                                for n in ("torso", "neck", "head", "floor"))
    hinge = api.joint("revolute", api.connector(torso), api.connector(neck))
    weld = api.joint("fixed", api.connector(neck), api.connector(head))
    resting = api.joint("fixed", api.connector(floor), api.connector(torso), suppressed=True)
    built = api.assembly([torso, neck, head, floor], [hinge, weld, resting],
                         anatomy=[api.anatomy("neck", [neck]),
                                  api.anatomy("head", [head], reason="fixed gaze")])
    motor = api.actuator(hinge, kind="motor", control_nmm="1", torque_limit_nmm=10)
    bodies = [api.body(c, density_kg_m3=1000) for c in (torso, neck, head, floor)]
    raw = {"torso": torso, "neck": neck, "head": head, "floor": floor,
           "hinge": hinge, "weld": weld, "resting": resting, "asm": built,
           # Two exports of one robot declare one motor, not two.
           "earth": api.mjcf(built, bodies, actuators=[motor]),
           "moon": api.mjcf(built, bodies, actuators=[motor])}
    components = {id(v): k for k, v in raw.items() if v.output_type == "component_link"}
    joints = {id(v): k for k, v in raw.items() if v.output_type == "joint"}
    stamp = _anatomy_stamp(raw, built.properties, components, joints, _joint_data([
        ("hinge", "revolute", "torso", "neck", False),
        ("weld", "fixed", "neck", "head", False),
        ("resting", "fixed", "floor", "torso", True),
    ]), "asm", root="torso", world_geometry=None)
    assert stamp == {
        "regions": [{"region": "neck", "components": ["neck"]},
                    {"region": "head", "components": ["head"], "reason": "fixed gaze"}],
        "components": ["torso", "neck", "head", "floor"],
        "world_components": ["floor"],
        "root_component": "torso",
        "joints": [
            {"joint": "hinge", "kind": "revolute", "components": ["torso", "neck"], "actuators": 1},
            {"joint": "weld", "kind": "fixed", "components": ["neck", "head"], "actuators": 0},
        ],
    }


# -- the summary (ADR-614) ---------------------------------------------------

def _box(name, low, high):
    return {"component": name, "placement": {"matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]},
            "source_facts": {"bounds_mm": {"min": list(low), "max": list(high)},
                             "volume_mm3": 1000.0}}


#: A raptor along +X: a 300 mm torso, a two-segment neck driven at its base
#: and closed by a passive rod, a head welded to the top segment, a tail
#: welded to the torso and sticking 400 mm out behind it, one driven leg
#: and one leg whose only hinge is passive.
_BOXES = [
    _box("torso", (0, -60, 200), (300, 60, 320)),
    _box("battery", (50, -40, 220), (250, 40, 280)),
    _box("neck_1", (300, -15, 300), (360, 15, 400)),
    _box("neck_2", (330, -15, 380), (380, 15, 470)),
    _box("rod", (300, 20, 300), (380, 25, 470)),
    _box("head", (360, -25, 450), (520, 25, 500)),
    _box("tail", (-400, -20, 240), (0, 20, 290)),
    _box("thigh", (100, 60, 0), (160, 90, 220)),
    _box("arm", (280, 60, 150), (320, 70, 250)),
    _box("floor", (-2000, -2000, -10), (2000, 2000, 0)),
]


def _joint(name, kind, first, second, actuators=0):
    return {"joint": name, "kind": kind, "components": [first, second], "actuators": actuators}


def _raptor(regions):
    return {
        "regions": regions,
        "components": [row["component"] for row in _BOXES],
        "world_components": ["floor"],
        "root_component": "torso",
        "joints": [
            _joint("w_battery", "fixed", "torso", "battery"),
            _joint("neck_base", "revolute", "torso", "neck_1", actuators=1),
            _joint("neck_mid", "revolute", "neck_1", "neck_2"),
            _joint("rod_base", "ball", "torso", "rod"),
            _joint("rod_top", "ball", "rod", "neck_2"),
            _joint("w_head", "fixed", "neck_2", "head"),
            _joint("w_tail", "fixed", "torso", "tail"),
            _joint("hip", "revolute", "torso", "thigh", actuators=1),
            _joint("shoulder", "revolute", "torso", "arm"),
            _joint("rest", "fixed", "floor", "torso"),
        ],
    }


def _region(block, name):
    (row,) = [row for row in block["regions"] if row["region"] == name]
    return row


def test_an_undeclared_design_is_advisory_and_still_finds_its_welded_tail() -> None:
    block = anatomy.anatomy_summary(_raptor([]), _BOXES)
    assert block["verdict"] == "undeclared"
    assert "assembly.anatomy" in block["note"]
    assert block["actuated_dof"] == 2 and block["joint_dof"] == 1 + 1 + 3 + 3 + 1 + 1
    assert block["mobile_joints"] == 6 and block["actuated_joints"] == 2
    found = {row["joint"]: row for row in block["rigid_appendages"]}
    assert set(found) == {"w_tail", "w_head"}
    tail = found["w_tail"]
    assert tail["components"] == ["tail"] and tail["welded_to"] == "torso"
    assert tail["toward"] == "-x" and tail["protrudes_mm"] == pytest.approx(400.0)
    assert tail["extent_mm"] == [400.0, 40.0, 50.0] and tail["acknowledged"] is False
    # The battery is inside the torso's box: welded, but it sticks out of nothing.
    assert "w_battery" not in found


def test_regions_read_articulated_rigid_and_passive_from_the_graph() -> None:
    block = anatomy.anatomy_summary(_raptor([
        {"region": "spine", "components": ["torso", "battery"]},
        {"region": "neck", "components": ["neck_1", "neck_2", "rod"]},
        {"region": "head", "components": ["head"]},
        {"region": "tail", "components": ["tail"]},
        {"region": "leg_l", "components": ["thigh"]},
        {"region": "arm_l", "components": ["arm"]},
    ]), _BOXES)
    assert block["verdict"] == "incomplete"
    assert _region(block, "spine")["status"] == "root"
    neck = _region(block, "neck")
    assert neck["status"] == "articulated" and neck["parent_region"] == "spine"
    assert {j["joint"]: j["drive"] for j in neck["joints"]} == {
        "neck_base": "actuated", "neck_mid": "loop", "rod_base": "loop", "rod_top": "loop"}
    assert neck["joint_dof"] == 8 and neck["actuated_dof"] == 1
    head = _region(block, "head")
    assert head["status"] == "rigid, no reason" and head["welded_to"] == ["neck"]
    assert _region(block, "tail")["status"] == "rigid, no reason"
    assert _region(block, "leg_l")["status"] == "articulated"
    arm = _region(block, "arm_l")
    assert arm["status"] == "passive only" and arm["joints"][0]["drive"] == "passive"
    assert block["unacknowledged_appendages"] == 2
    measure = anatomy.anatomy_measure(block)
    assert measure["meets"] is False
    assert measure["open_regions"] == ["head", "tail", "arm_l"]


def test_a_reason_completes_a_rigid_region_and_acknowledges_its_appendage() -> None:
    block = anatomy.anatomy_summary(_raptor([
        {"region": "spine", "components": ["torso", "battery"]},
        {"region": "neck", "components": ["neck_1", "neck_2", "rod"]},
        {"region": "head", "components": ["head"], "reason": "fixed gaze; camera on a stiff mount"},
        {"region": "tail", "components": ["tail"],
         "reason": "ossified tail: raptor tails were stiff; a tail joint costs 0.4 kg"},
        {"region": "leg_l", "components": ["thigh"]},
        {"region": "arm_l", "components": ["arm"], "reason": "passive forelimb, folds on contact"},
    ]), _BOXES)
    assert block["verdict"] == "complete"
    tail = _region(block, "tail")
    assert tail["status"] == "rigid" and tail["reason"].startswith("ossified tail")
    assert _region(block, "arm_l")["status"] == "passive only"
    assert all(row["acknowledged"] for row in block["rigid_appendages"])
    assert block["unacknowledged_appendages"] == 0
    assert anatomy.anatomy_measure(block)["meets"] is True


def test_a_jointed_tail_is_articulated_and_no_longer_an_appendage() -> None:
    stamp = _raptor([{"region": "tail", "components": ["tail"]}])
    stamp["joints"] = [j if j["joint"] != "w_tail" else _joint("tail_yaw", "revolute", "torso", "tail", 1)
                       for j in stamp["joints"]]
    block = anatomy.anatomy_summary(stamp, _BOXES)
    assert _region(block, "tail")["status"] == "articulated"
    assert _region(block, "tail")["parent_region"] is None
    assert [row["joint"] for row in block["rigid_appendages"]] == ["w_head"]
    assert block["verdict"] == "complete"


def test_two_regions_on_one_rigid_body_give_the_joint_to_the_first_declared() -> None:
    """A jaw welded to its head moves with the head and not relative to it."""

    stamp = _raptor([{"region": "head", "components": ["neck_2", "head"]},
                     {"region": "jaw", "components": ["rod"]}])
    stamp["joints"] = [_joint("w_battery", "fixed", "torso", "battery"),
                       _joint("nod", "revolute", "torso", "neck_2", 1),
                       _joint("w_head", "fixed", "neck_2", "head"),
                       _joint("w_jaw", "fixed", "head", "rod")]
    block = anatomy.anatomy_summary(stamp, _BOXES)
    assert _region(block, "head")["status"] == "articulated"
    jaw = _region(block, "jaw")
    assert jaw["status"] == "rigid, no reason" and jaw["welded_to"] == ["head"]


def test_an_unpublished_graph_is_unavailable_not_complete() -> None:
    block = anatomy.anatomy_summary(None)
    assert block["verdict"] == "unavailable" and "rebuild" in block["reason"]
    assert anatomy.anatomy_measure(None)["meets"] is None


def test_the_view_cuts_long_lists_and_says_where_the_rest_is() -> None:
    many = [f"seg_{i}" for i in range(20)]
    block = {"verdict": "complete", "source": "x", "actuated_dof": 1,
             "regions": [{"region": "tail", "status": "articulated", "components": many,
                          "joints": [{"joint": "j", "kind": "revolute", "drive": "actuated"}]}],
             "rigid_appendages": [{"components": many, "joint": f"w{i}", "acknowledged": False,
                                   "protrudes_mm": 1.0} for i in range(20)]}
    view = anatomy.anatomy_view(block)
    assert "source" not in view and view["full"] == "inspect scope=anatomy"
    assert view["regions"][0]["components"] == {"first": many[:6], "count": 20}
    assert view["regions"][0]["joints"] == ["j (revolute, actuated)"]
    assert len(view["rigid_appendages"]) == anatomy.VIEW_LIST_LIMIT
    assert view["rigid_appendages_omitted"] == 20 - anatomy.VIEW_LIST_LIMIT


# -- the scope -----------------------------------------------------------------

def _report(stamp):
    outputs = [{"name": "asm", "type": "assembly", "anatomy": stamp}]
    for row in _BOXES:
        outputs.append({"name": row["component"] + "_body", "type": "solid",
                        "facts": dict(row["source_facts"])})
        outputs.append({"name": row["component"], "type": "component_link",
                        "source_output": row["component"] + "_body",
                        "definition": {"properties": {"label": row["component"]}},
                        "solved_placement_matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]})
    return {"ok": True, "outputs": outputs}


def test_inspect_scope_anatomy_serves_the_block(tmp_path) -> None:
    root = _store(tmp_path, _report(_raptor([{"region": "tail", "components": ["tail"]}])))
    captured = capture_inspection(_service(root), {"scope": "anatomy"})
    assert captured["kind"] == "anatomy"
    value = complete_inspection(captured)["value"]
    assert value["assembly"] == "asm" and value["verdict"] == "incomplete"
    assert value["regions"][0]["status"] == "rigid, no reason"
    tail = complete_inspection(capture_inspection(_service(root), {
        "scope": "anatomy", "path": "/rigid_appendages/0/joint"}))["value"]
    assert tail == "w_tail"


def test_a_revision_accepted_before_the_stamp_reads_unavailable(tmp_path) -> None:
    root = _store(tmp_path, {"ok": True, "outputs": [{"name": "asm", "type": "assembly"}]})
    value = complete_inspection(capture_inspection(_service(root), {"scope": "anatomy"}))["value"]
    assert value["verdict"] == "unavailable"


# -- catalog drives: a design-only project's motors (ADR-614) ----------------

def test_every_drive_family_records_its_output_axis_and_motion() -> None:
    from cadex_library_api import _definition_key, library_mount_facts
    from test_library import _lib

    lib = _lib()
    qdd = lib.qdd("cubemars-ak80-9-v3", origin=(10.0, 20.0, 30.0), direction=(0.0, 1.0, 0.0))
    servo = lib.servo("sts3215", origin=(1.0, 2.0, 3.0), direction=(1.0, 0.0, 0.0))
    motor = lib.gearmotor("pololu-2367")
    bldc = lib.bldc("hobbywing-30415200", origin=(0.0, 0.0, 5.0))
    linear = lib.linear_actuator("l12-50-210-12-s", direction=(0.0, 0.0, -1.0))
    bolt = lib.bolt("M3", 10.0)
    drives = library_mount_facts()["drives"]
    row = drives[_definition_key(qdd.body)]
    assert row["origin"] == pytest.approx([10.0, 20.0, 30.0])
    assert row["axis"] == pytest.approx([0.0, 1.0, 0.0]) and row["motion"] == "rotary"
    assert drives[_definition_key(servo.body)]["axis"] == pytest.approx([1.0, 0.0, 0.0])
    assert drives[_definition_key(motor.body)]["motion"] == "rotary"
    assert drives[_definition_key(bldc.body)]["origin"] == pytest.approx([0.0, 0.0, 5.0])
    assert drives[_definition_key(linear.body)]["axis"] == pytest.approx([0.0, 0.0, -1.0])
    assert drives[_definition_key(linear.body)]["motion"] == "linear"
    # A bolt drives nothing.
    assert _definition_key(bolt.body) not in drives


def test_the_stamp_carries_each_joint_axis_to_the_solved_pose() -> None:
    from cadex_assembly_worker import _solved_joint_axis

    def fact(matrix):
        return {"matrix": matrix}

    identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    # The hinge frame sits at (10, 0, 0) with its +Z along world +Y, on
    # component a at the origin...
    frame = [1, 0, 0, 10, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1]
    joint = {"connectors": [{"component_output": "a", "global_frame": fact(frame)}]}
    assert _solved_joint_axis(joint, {"a": fact(identity)}, {"a": fact(identity)}) == {
        "origin": [10.0, 0.0, 0.0], "axis": [0.0, 1.0, 0.0]}
    # ...and the solve turned a 90 degrees about Z and lifted it 5 mm.
    turned = [0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 5, 0, 0, 0, 1]
    line = _solved_joint_axis(joint, {"a": fact(identity)}, {"a": fact(turned)})
    assert line["origin"] == pytest.approx([0.0, 10.0, 5.0])
    assert line["axis"] == pytest.approx([-1.0, 0.0, 0.0])


def _drive_row(name, origin, axis, motion="rotary"):
    row = _box(name, origin, [v + 10 for v in origin])
    row["drive_axis"] = {"origin": list(origin), "axis": list(axis), "motion": motion}
    return row


def _arm(drive_rows, joints):
    rows = [_box("torso", (0, 0, 0), (200, 100, 100)), _box("upper", (200, 0, 40), (400, 20, 60)),
            _box("lower", (400, 0, 40), (600, 20, 60)), _box("rod", (200, 30, 40), (400, 40, 60)),
            *drive_rows]
    stamp = {"regions": [{"region": "spine", "components": ["torso"]},
                         {"region": "arm_r", "components": ["upper", "lower", "rod"]}],
             "components": [r["component"] for r in rows], "world_components": [],
             "root_component": "torso", "joints": joints}
    return anatomy.anatomy_summary(stamp, rows)


_SHOULDER = {"origin": [200.0, 10.0, 50.0], "axis": [0.0, 1.0, 0.0]}


def test_a_motor_welded_on_the_joint_axis_drives_it_with_no_actuator_declared() -> None:
    block = _arm([_drive_row("qdd", (200.0, -5.0, 50.0), (0.0, -1.0, 0.0))], [
        _joint("w_qdd", "fixed", "torso", "qdd"),
        {**_joint("shoulder", "revolute", "torso", "upper"), "axis": _SHOULDER},
        {**_joint("elbow", "revolute", "upper", "lower"),
         "axis": {"origin": [400.0, 10.0, 50.0], "axis": [0.0, 1.0, 0.0]}},
    ])
    arm = _region(block, "arm_r")
    drives = {j["joint"]: (j["drive"], j.get("driver")) for j in arm["joints"]}
    # Antiparallel is still coaxial; the elbow has no motor on its axis.
    assert drives == {"shoulder": ("catalog drive", "qdd"), "elbow": ("passive", None)}
    assert arm["status"] == "articulated" and arm["actuated_dof"] == 1
    assert block["catalog_driven_joints"] == 1 and block["actuated_dof"] == 1
    view = anatomy.anatomy_view(block)
    assert "shoulder (revolute, catalog drive: qdd)" in view["regions"][1]["joints"]


def test_a_declared_actuator_wins_and_an_off_axis_or_wrong_motion_drive_does_not_count() -> None:
    declared = _arm([_drive_row("qdd", (200.0, -5.0, 50.0), (0.0, 1.0, 0.0))], [
        _joint("w_qdd", "fixed", "torso", "qdd"),
        {**_joint("shoulder", "revolute", "torso", "upper", actuators=1), "axis": _SHOULDER}])
    assert _region(declared, "arm_r")["joints"][0]["drive"] == "actuated"
    assert declared["catalog_driven_joints"] == 0
    for drive in (_drive_row("qdd", (200.0, -5.0, 53.0), (0.0, 1.0, 0.0)),        # 3 mm off
                  _drive_row("qdd", (200.0, -5.0, 50.0), (0.0, 0.2, 1.0)),        # aimed away
                  _drive_row("qdd", (200.0, -5.0, 50.0), (0.0, 1.0, 0.0), "linear")):
        block = _arm([drive], [_joint("w_qdd", "fixed", "torso", "qdd"),
                               {**_joint("shoulder", "revolute", "torso", "upper"), "axis": _SHOULDER}])
        assert _region(block, "arm_r")["status"] == "passive only"
    # A motor that is not welded to either side drives nothing.
    loose = _arm([_drive_row("qdd", (200.0, -5.0, 50.0), (0.0, 1.0, 0.0))],
                 [{**_joint("shoulder", "revolute", "torso", "upper"), "axis": _SHOULDER}])
    assert _region(loose, "arm_r")["status"] == "passive only"


def test_a_loop_a_catalog_drive_closes_is_driven_through_it() -> None:
    block = _arm([_drive_row("qdd", (200.0, -5.0, 50.0), (0.0, 1.0, 0.0))], [
        _joint("w_qdd", "fixed", "torso", "qdd"),
        {**_joint("shoulder", "revolute", "torso", "upper"), "axis": _SHOULDER},
        _joint("rod_base", "ball", "torso", "rod"),
        _joint("rod_top", "ball", "rod", "upper"),
    ])
    drives = {j["joint"]: j["drive"] for j in _region(block, "arm_r")["joints"]}
    assert drives == {"shoulder": "catalog drive", "rod_base": "loop", "rod_top": "loop"}
