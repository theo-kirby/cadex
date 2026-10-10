# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Panels grown from what they cover, housings round drives, and the shell check.

``lib.panel`` (ADR-610) reads the covered recipes into points and a
membership test, fits a superellipse ring per station, and plans screw
bosses down to the frame; ``lib.housing`` (ADR-611) wraps a drive's own
envelope and screws it through its own holes; ``CadexFitReport.shell_summary``
(ADR-612) judges each declared shell as floating, solid or unmounted from
the published clearance value. Everything here runs headless on recipes;
one real-kernel test builds the solids.
"""

from __future__ import annotations

import math

import pytest

import CadexFitReport
from CadexFitReport import fit_summary, fit_view, shell_summary
from CadexPanels import (
    PanelError,
    fit_ring,
    gap_statistics,
    plan_panel,
    ring_points_2d,
    ring_radius,
    sample,
    Sample,
)
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import DomainValue, create_domain_api
from cadex_library_api import LibraryError, create_library_api, library_listing

PART_PACK = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]


def _part():
    return create_domain_api(PART_PACK.domain, PART_PACK.api_exports, PART_PACK.output_types)


def _lib():
    return create_library_api(_part())


def _walk(value):
    if isinstance(value, DomainValue):
        yield value
        for argument in value.arguments:
            yield from _walk(argument)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk(item)


def _trunk(lib):
    part = lib._part
    deck = part.box(158, 50, 4, origin=(-78, -25, -2))
    pack = lib.battery("gensace-gea2s100045d", origin=(-30, 0, 2))
    board = lib.board("esp32-devkitc-v4", origin=(18, -14, 2))
    return deck, pack, board


# --------------------------------------------------------------------------
# reading recipes
# --------------------------------------------------------------------------


def test_a_box_samples_its_surface_and_knows_its_inside():
    found = sample(_part().box(10, 20, 30, origin=(1, 2, 3)), 2.0)
    low, high = found.bounds()
    assert low == pytest.approx([1, 2, 3]) and high == pytest.approx([11, 22, 33])
    assert found.contains([5, 10, 10]) is True
    assert found.contains([0, 10, 10]) is False


def test_transforms_and_cuts_carry_points_and_membership():
    part = _part()
    tube = part.cut(part.cylinder(10, 40), [part.cylinder(6, 50, origin=(0, 0, -5))])
    moved = part.transform(tube, translation=(100, 0, 0), rotation_axis=(0, 1, 0),
                           rotation_degrees=90)
    found = sample(moved, 2.0)
    # Rotated +Z onto +X about the origin, then shifted 100 along X.
    assert found.contains([120, 8, 0]) is True        # in the wall
    assert found.contains([120, 0, 0]) is False       # in the bore
    assert found.contains([95, 8, 0]) is False        # before its start
    radii = [math.hypot(p[1], p[2]) for p in found.points]
    assert max(radii) == pytest.approx(10, abs=1e-6)
    # The bore's wall is surface too; nothing of the removed core is.
    assert min(radii) == pytest.approx(6, abs=1e-6)
    assert all(not (0.5 < r < 5.5) for r in radii)


def test_a_library_part_samples_through_its_body():
    lib = _lib()
    qdd = lib.qdd("cubemars-ak80-9-v3", origin=(0, 0, 50), direction=(1, 0, 0))
    found = sample(qdd, 3.0)
    low, high = found.bounds()
    assert low[0] == pytest.approx(-38.5, abs=1e-6) and high[0] == pytest.approx(0, abs=1e-6)
    assert high[2] == pytest.approx(50 + 49, abs=0.5)
    assert found.contains([-20, 0, 50]) is True


def test_a_recipe_it_cannot_follow_is_refused_by_name():
    part = _part()
    with pytest.raises(PanelError, match="import_part"):
        sample(part.import_part("x.cxpart"))


# --------------------------------------------------------------------------
# the ring
# --------------------------------------------------------------------------


def test_ring_radius_matches_the_ring_points():
    for exponent in (2.0, 3.0, 4.0, 8.0):
        points = ring_points_2d(0.0, 0.0, 30.0, 12.0, exponent, 64)
        for index in (0, 8, 16, 24):
            u, v = points[index]
            angle = math.degrees(math.atan2(v, u))
            assert ring_radius(30.0, 12.0, exponent, angle) == pytest.approx(math.hypot(u, v))


@pytest.mark.parametrize("exponent", [2.0, 4.0, 6.0])
def test_a_fitted_ring_clears_every_point_by_its_offset(exponent):
    points = [(x, y) for x in (-20, -10, 0, 10, 20) for y in (-4, 0, 4)] + [(0, 9), (5, -8)]
    a, b = fit_ring(points, centre=(0.0, 0.0), exponent=exponent, offset=1.5)
    curve = ring_points_2d(0.0, 0.0, a, b, exponent, 720)
    for u, v in points:
        nearest = min(math.hypot(u - x, v - y) for x, y in curve)
        inside = (abs(u) / a) ** exponent + (abs(v) / b) ** exponent < 1.0
        assert inside and nearest >= 1.5 - 0.05, (u, v, nearest)
    # And not grossly more: the ring hugs.
    assert a < 20 * 2 ** (1 / exponent) + 1.5 + 4.0


# --------------------------------------------------------------------------
# planning a panel
# --------------------------------------------------------------------------


def test_the_skin_follows_the_contents_station_by_station():
    lib = _lib()
    deck, pack, board = _trunk(lib)
    covered = [sample(v, 3.0) for v in (pack, board, deck)]
    cover = Sample([p for c in covered for p in c.points], None)
    plan = plan_panel(cover, None, axis=(1, 0, 0), span=(-74, 76), offset=1.5)
    rows = plan["stations"]
    # Over the pack (x < 0) the skin stands taller than over the board.
    over_pack = [r for r in rows if -60 < r["position"] < -10]
    over_board = [r for r in rows if 30 < r["position"] < 60]
    top = lambda r: r["centre"][1] + r["inner"][1]
    assert min(top(r) for r in over_pack) > max(top(r) for r in over_board) + 3.0
    # Every covered point inside its station's inner ring.
    for row in rows:
        a, b = row["inner"]
        n = plan["exponent"]
        for p in cover.points:
            if abs(p[0] - row["position"]) < 0.5:
                du, dv = p[1] - row["centre"][0], p[2] - row["centre"][1]
                assert (abs(du) / a) ** n + (abs(dv) / b) ** n < 1.0
        assert row["outer"] == pytest.approx([a + 2.0, b + 2.0])


def test_seams_and_a_parting_plane_name_the_pieces():
    lib = _lib()
    deck, pack, board = _trunk(lib)
    panel = lib.panel([pack, board], axis=(1, 0, 0), mount_to=deck, span=(-74, 76),
                      seams=[0.0], split="top_bottom")
    assert panel.names == ["0_top", "0_bottom", "1_top", "1_bottom"]
    assert len(panel.parts) == 4 and not panel.unmounted
    assert panel.spec["split_at_mm"] == pytest.approx(2.0, abs=0.3)  # the deck's top
    with pytest.raises(LibraryError, match="seam at 90"):
        lib.panel([pack], axis=(1, 0, 0), seams=[90.0])
    with pytest.raises(LibraryError, match="split must be"):
        lib.panel([pack], axis=(1, 0, 0), split="diagonal")


def test_every_panel_is_screwed_down_and_no_screw_leaves_the_frame():
    lib = _lib()
    deck, pack, board = _trunk(lib)
    panel = lib.panel([pack, board], axis=(1, 0, 0), mount_to=deck, span=(-74, 76),
                      seams=[0.0], split="top_bottom")
    assert len(panel.screws) == 8 and len(panel.holes) == 8
    assert all(len(screws) == 2 for screws in panel.screws_by_part)
    deck_found = sample(deck, 3.0)
    pack_found = sample(pack, 3.0)
    for bolt in panel.screws:
        assert bolt.family == "bolt" and bolt.part_number.startswith("m2x")
        found = sample(bolt.body, 0.5)
        # Its thread runs into the deck and never out into the pack.
        assert any(deck_found.contains(p) for p in found.points)
        assert not any(pack_found.contains(p) for p in found.points)
    for boss in panel.spec["bosses"]:
        assert 1.5 * 2.0 <= boss["engagement_mm"] <= 4.0 - 0.3 + 1e-6
        assert boss["angle_degrees"] % 90.0 == 0.0
    # The two halves never screw into the deck on one line from both faces.
    tips = [(b["position_mm"], b["angle_degrees"]) for b in panel.spec["bosses"]]
    assert len(set(tips)) == len(tips)


def test_without_a_frame_a_panel_carries_no_screws_and_says_so():
    lib = _lib()
    _deck, pack, _board = _trunk(lib)
    panel = lib.panel([pack], axis=(1, 0, 0))
    assert panel.screws == [] and panel.holes == []
    assert any("no mount_to" in note for note in panel.notes)
    assert panel.unmounted == ["0"]


def test_describe_api_lists_the_grown_parts_with_their_signatures():
    exports = {row["name"]: row for row in library_listing()["exports"]}
    assert "mount_to" in exports["panel"]["signature"]
    assert "seams" in exports["panel"]["signature"]
    assert "wall" in exports["housing"]["signature"]
    assert "lib.bolt" in exports["panel"]["description"]


# --------------------------------------------------------------------------
# housings
# --------------------------------------------------------------------------


@pytest.mark.parametrize("sku,seat,length", [
    ("cubemars-ak80-9-v3", "rear", 5.0), ("cubemars-ak70-10", "rear", 6.0),
    ("cubemars-ak70-10", "front", 12.0), ("cubemars-ak80-9-v3", "front", 5.0),
])
def test_a_qdd_housing_screws_through_its_own_stator_holes(sku, seat, length):
    lib = _lib()
    qdd = lib.qdd(sku, origin=(0, 0, 100), direction=(1, 0, 0))
    housing = lib.housing(qdd, seat=seat)
    holes = qdd.spec["mount_holes"]
    assert len(housing.screws) == len(holes) == housing.spec["screw_count"]
    assert housing.spec["screw_length_mm"] == length
    assert housing.spec["outer_dia_mm"] == pytest.approx(qdd.spec["case_dia_mm"] + 5.0)
    depth = qdd.spec[f"{seat}_mount_depth_mm"]
    assert housing.spec["engagement_mm"] <= depth
    # Every screw on one of the drive's own hole axes, in world coordinates.
    from cadex_library_api import library_mount_facts

    facts = library_mount_facts()["axes"]
    import json
    drive_axes = facts[json.dumps(qdd.body.to_payload(), sort_keys=True,
                                  separators=(",", ":"), ensure_ascii=True)]
    for bolt in housing.screws:
        origin = bolt.spec  # noqa: F841 - the bolt carries its own axis
        bolt_axes = facts[json.dumps(bolt.body.to_payload(), sort_keys=True,
                                     separators=(",", ":"), ensure_ascii=True)]
        o = bolt_axes[0]["origin"]
        assert any(math.hypot(o[1] - a["origin"][1], o[2] - a["origin"][2]) < 1e-6
                   for a in drive_axes)


def test_a_servo_housing_is_cut_with_its_own_bay():
    lib = _lib()
    for sku in ("mg996r", "sg90", "sts3215"):
        servo = lib.servo(sku, origin=(0, 40, 0))
        housing = lib.housing(servo)
        assert housing.spec["screw_count"] == len(housing.screws) > 0
        from cadex_library_api import library_mount_facts, _definition_key
        assert library_mount_facts()["bays"][_definition_key(housing.cavity)] == \
            _definition_key(servo.body)
    with pytest.raises(LibraryError, match="lib.qdd"):
        lib.housing(lib.bolt("m3", 10))


def test_a_link_grown_onto_a_housing_has_the_cavity_cut_again():
    lib = _lib()
    qdd = lib.qdd("cubemars-ak80-9-v3")
    housing = lib.housing(qdd)
    link = lib._part.box(10, 10, 80, origin=(-5, -5, -60))
    grown = housing.fuse(link)
    assert grown.operation == "cut"
    tools = list(grown.arguments[1])
    assert tools[0] is housing.cavity and len(tools) == 1 + len(housing.holes)


# --------------------------------------------------------------------------
# measuring a gap
# --------------------------------------------------------------------------


def _cube_triangles(size):
    s = size
    v = [(x, y, z) for x in (0, s) for y in (0, s) for z in (0, s)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    tris = []
    for a, b, c, d in faces:
        tris += [(v[a], v[b], v[c]), (v[a], v[c], v[d])]
    return tris


def test_the_inner_face_gap_is_measured_and_the_outer_face_ignored():
    triangles = _cube_triangles(10.0)
    samples, normals = [], []
    for gap in (2.0, 2.0, 2.0, 3.0):
        # Inner face of a lid over the top: normal points down at the cube.
        samples.append([5.0, 5.0, 10.0 + gap])
        normals.append([0.0, 0.0, -1.0])
    # The lid's outer face, 2 mm further, faces away: not a gap.
    samples.append([5.0, 5.0, 14.0])
    normals.append([0.0, 0.0, 1.0])
    stats = gap_statistics(samples, normals, triangles)
    assert stats["inner_samples"] == 4 and stats["samples"] == 5
    assert stats["gap_median_mm"] == pytest.approx(2.0)
    assert stats["gap_max_mm"] == pytest.approx(3.0)
    assert stats["hug_fraction"] == 1.0
    # A point off a corner measures to the corner, not the face planes.
    corner = gap_statistics([[13.0, 14.0, 10.0]], [[-1.0, -1.0, 0.0]], triangles)
    assert corner["gap_median_mm"] == pytest.approx(5.0)
    assert gap_statistics([[0, 0, 100]], [[0, 0, -1]], triangles, reach=50) is None


# --------------------------------------------------------------------------
# the shell block
# --------------------------------------------------------------------------


def _component(name, *, appearance=None, family=None, part_number="x", volume=None,
               area=None):
    row = {"component": name, "source_output": name}
    if appearance:
        row["appearance"] = appearance
    if family:
        row["catalog"] = {"family": family, "part_number": part_number}
        row["mount_axes"] = []
    if volume is not None:
        row["source_facts"] = {"volume_mm3": volume, "area_mm2": area}
    return row


def _pair(first, second, distance, volume=0.0):
    return {"first": first, "second": second, "distance_mm": distance,
            "common_volume_mm3": volume}


def _gaps(name, median, covers=("deck",), inner=180):
    return {"component": name, "covers": list(covers), "samples": 400, "inner_samples": inner,
            "gap_median_mm": median, "gap_p25_mm": median / 2, "gap_p90_mm": median * 2,
            "hug_fraction": 0.9 if median < 4 else 0.0}


def test_a_screwed_thin_hugging_panel_passes():
    value = {
        "components": [_component("deck"), _component("lid", appearance="shell",
                                                      volume=2000.0, area=2000.0),
                       _component("s0", family="bolt", part_number="m2x8-socket")],
        "pairs": [_pair("lid", "s0", 0.0), _pair("deck", "s0", 0.0, 4.5),
                  _pair("deck", "lid", 0.0)],
        "attachments": [],
        "shell_gaps": [_gaps("lid", 2.4)],
    }
    block = shell_summary(value)
    assert block["verdict"] == "pass" and block["shell_count"] == 1
    lid = block["fitted"][0]
    assert (lid["mounted"], lid["screws"], lid["held_by"]) == ("screws", ["s0"], ["deck"])
    assert lid["wall_mm"] == 2.0 and lid["findings"] == []


def test_an_egg_over_the_parts_is_floating_unmounted_and_named_worst_first():
    value = {
        "components": [_component("deck"),
                       _component("egg", appearance="shell", volume=20000.0, area=20000.0),
                       _component("lump", appearance="shell", volume=90000.0, area=9000.0),
                       _component("cap", appearance="shell", volume=500.0, area=500.0),
                       _component("lid", appearance="shell", volume=2000.0, area=2000.0)],
        "pairs": [],
        "attachments": [{"first": "deck", "second": "lid", "status": "touching"},
                        {"first": "deck", "second": "egg", "status": "not touching"},
                        {"first": "deck", "second": "cap", "status": "touching"},
                        {"first": "deck", "second": "lump", "status": "touching"}],
        "shell_gaps": [_gaps("egg", 31.3), _gaps("lump", 1.0), _gaps("cap", 0.0, covers=()),
                       _gaps("lid", 3.0)],
    }
    block = shell_summary(value)
    assert block["verdict"] == "reported" and block["reported_count"] == 3
    by = {row["component"]: row for row in block["reported"]}
    assert by["egg"]["findings"] == ["floating", "unmounted"]
    assert "31.3 mm" in by["egg"]["detail"]
    assert by["lump"]["findings"] == ["solid"] and by["lump"]["wall_mm"] == 20.0
    assert by["cap"]["findings"] == ["covers nothing"]
    assert block["reported"][0]["component"] == "egg"
    assert block["fitted"][0]["mounted"] == "welded"
    assert block["thresholds"]["floating_gap_mm"] == CadexFitReport.SHELL_FLOATING_GAP_MM
    assert "lib.panel" in block["note"]


def test_the_shell_block_rides_in_the_fit_block_and_its_view():
    value = {"components": [_component("deck")], "pairs": [], "available": True}
    fit = fit_summary(value)
    assert fit["shells"]["verdict"] == "none"
    many = {"components": [_component("deck")] + [
        _component(f"p{k}", appearance="shell", volume=1.0, area=1.0) for k in range(20)],
        "pairs": [], "shell_gaps": [_gaps(f"p{k}", 10.0) for k in range(20)]}
    view = fit_view(fit_summary(many))
    assert len(view["shells"]["reported"]) == 12
    assert view["shells"]["reported_omitted"] == 8
    old = shell_summary({"components": [_component("lid", appearance="shell")]})
    assert old["reported"][0]["gap"] == "unmeasured" and "gap_note" in old
    assert shell_summary({})["verdict"] == "unavailable"


# --------------------------------------------------------------------------
# the real kernel
# --------------------------------------------------------------------------


def test_panels_and_housings_build_valid_single_solids_on_the_kernel(tmp_path):
    import subprocess
    from test_cadexd_lifecycle import CADEX_ROOT, FREECADCMD
    if FREECADCMD is None:
        pytest.skip("needs a built engine (pixi run build-engine)")

    driver = tmp_path / "panels.py"
    driver.write_text('''
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import create_domain_api
from cadex_library_api import create_library_api
from cadex_part_worker import build_part_shape
pack = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]
part = create_domain_api(pack.domain, pack.api_exports, pack.output_types)
lib = create_library_api(part)
deck = part.box(158, 50, 4, origin=(-78, -25, -2))
battery = lib.battery("gensace-gea2s100045d", origin=(-30, 0, 2))
board = lib.board("esp32-devkitc-v4", origin=(18, -14, 2))
panel = lib.panel([battery, board], axis=(1, 0, 0), mount_to=deck, span=(-74, 76),
                  split="top_bottom")
deck_shape = build_part_shape(part.cut(deck, panel.holes).to_payload())
contents = [build_part_shape(v.body.to_payload()) for v in (battery, board)]
for name, body in zip(panel.names, panel.parts):
    shape = build_part_shape(body.to_payload())
    assert shape.isValid() and len(shape.Solids) == 1, name
    assert 1.6 < 2 * shape.Volume / shape.Area < 3.0, (name, 2 * shape.Volume / shape.Area)
    assert min(shape.distToShape(c)[0] for c in contents) > 1.0, name
    assert shape.common(deck_shape).Volume < 1e-6, name
    assert shape.distToShape(deck_shape)[0] < 1e-6, name
for bolt in panel.screws:
    shank = build_part_shape(bolt.body.to_payload())
    assert shank.common(deck_shape).Volume > 0.1
    assert all(shank.common(c).Volume < 1e-6 for c in contents)
qdd = lib.qdd("cubemars-ak80-9-v3", origin=(-121.5, 0, 0), direction=(-1, 0, 0))
drum = build_part_shape(lib.housing(qdd).body.to_payload())
motor = build_part_shape(qdd.body.to_payload())
assert drum.isValid() and len(drum.Solids) == 1
assert drum.common(motor).Volume < 1e-6 and drum.distToShape(motor)[0] < 1e-6
print("PANELS-OK")
''')
    completed = subprocess.run(
        [str(FREECADCMD), "-c",
         f"import sys; sys.path.insert(0, {str(CADEX_ROOT)!r}); exec(open({str(driver)!r}).read())"],
        capture_output=True, text=True, timeout=600,
    )
    assert "PANELS-OK" in completed.stdout, completed.stdout[-3000:] + completed.stderr[-3000:]
