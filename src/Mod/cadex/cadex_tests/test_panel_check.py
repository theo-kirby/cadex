# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The panel check: ``role="panel", covers=[...]`` judged by ``fit.panels``.

A panel is declared, not inferred from its colour (ADR-633): the assembly
API takes ``role=`` and ``covers=`` apart from ``appearance=``. The worker
measures each declared panel against what it says it covers (ADR-634), and
``CadexFitReport.panel_summary`` judges the numbers (ADR-636): a floating,
colliding or unmounted panel fails the fit; an egg, a lump, a thin wall, a
piece too big for the bed, a far fastener or a closed seam is named.
Everything here runs headless on published values.
"""

from __future__ import annotations

import pytest

import CadexFitReport
from CadexFitReport import fit_summary, fit_view, panel_summary
from CadexPanels import first_hits, gap_statistics
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import create_domain_api


def _assembly_api():
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return create_domain_api(pack.domain, pack.api_exports, pack.output_types)


SOURCE = {"document_uid": "doc", "object_name": "lid"}


# --------------------------------------------------------------------------
# the declaration
# --------------------------------------------------------------------------


def test_role_and_covers_are_declared_apart_from_the_colour():
    assembly = _assembly_api()
    board = assembly.component(dict(SOURCE, object_name="board"))
    deck = assembly.component(dict(SOURCE, object_name="deck"), role="frame")
    lid = assembly.component(SOURCE, role="panel", covers=[board], appearance="shell")
    assert lid.properties["role"] == "panel" and lid.properties["appearance"] == "shell"
    assert list(lid.properties["covers"]) == [board]
    assert deck.properties["role"] == "frame" and "covers" not in deck.properties
    # Painting a part light declares nothing.
    assert "role" not in assembly.component(SOURCE, appearance="shell").properties
    with pytest.raises(ValueError, match="names the components it covers"):
        assembly.component(SOURCE, role="panel")
    with pytest.raises(ValueError, match='declare role="panel"'):
        assembly.component(SOURCE, covers=[board])
    with pytest.raises(ValueError, match="must be one of"):
        assembly.component(SOURCE, role="shell")


# --------------------------------------------------------------------------
# the measuring arithmetic
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
    stats = gap_statistics(samples, normals, triangles, sample_area=10.0)
    assert stats["inner_samples"] == 4 and stats["samples"] == 5
    assert stats["gap_median_mm"] == pytest.approx(2.0)
    assert stats["gap_p10_mm"] == pytest.approx(2.0)
    assert stats["gap_max_mm"] == pytest.approx(3.0)
    assert stats["hug_fraction"] == 1.0
    assert stats["air_volume_mm3"] == pytest.approx(90.0)
    # A point off a corner measures to the corner, not the face planes.
    corner = gap_statistics([[13.0, 14.0, 10.0]], [[-1.0, -1.0, 0.0]], triangles)
    assert corner["gap_median_mm"] == pytest.approx(5.0)
    assert gap_statistics([[0, 0, 100]], [[0, 0, -1]], triangles, reach=50) is None


def test_rays_find_the_first_face_they_cross():
    triangles = _cube_triangles(10.0)
    hits = first_hits([[5, 5, 20], [5, 5, 5], [50, 50, 50], [5, 5, 20]],
                      [[0, 0, -1], [0, 0, 1], [0, 0, -1], [0, 0, 1]], triangles)
    assert hits[0] == pytest.approx(10.0) and hits[1] == pytest.approx(5.0)
    assert hits[2] == float("inf") and hits[3] == float("inf")
    assert first_hits([[5, 5, 20]], [[0, 0, -1]], triangles, reach=5.0)[0] == float("inf")


# --------------------------------------------------------------------------
# the panel block
# --------------------------------------------------------------------------


def _component(name, *, role=None, appearance=None, family=None, part_number="x",
               panel=None, box=None):
    row = {"component": name, "source_output": name}
    if role:
        row["role"] = role
    if appearance:
        row["appearance"] = appearance
    if family:
        row["catalog"] = {"family": family, "part_number": part_number}
        row["mount_axes"] = []
    if panel:
        row["panel"] = panel
    if box:
        row["source_facts"] = {"bounds_mm": {"min": box[0], "max": box[1]}}
        row["placement"] = {"position_mm": [0, 0, 0],
                            "matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]}
    return row


def _pair(first, second, distance, volume=0.0):
    row = {"first": first, "second": second, "distance_mm": distance,
           "common_volume_mm3": volume}
    if distance == 0.0 and volume == 0.0:
        # Seated face to face: what a weld or a declared contact publishes.
        row["intent"] = {"kind": "attached", "minimum_mm": 0.0}
    return row


def _measured(name, p90, covers=("board",), inner=180, **extra):
    row = {"component": name, "covers": list(covers), "samples": 400, "inner_samples": inner,
           "gap_p10_mm": p90 / 3, "gap_median_mm": p90 / 2, "gap_p90_mm": p90,
           "gap_max_mm": p90 * 1.2, "hug_fraction": 0.9 if p90 < 6 else 0.0,
           "egg_ratio": 1.3, "coverage": 0.8, "wall_p10_mm": 1.9, "wall_median_mm": 2.0,
           "wall_p90_mm": 2.4, "size_mm": [120.0, 80.0, 30.0],
           "points": [[0.0, 0.0, 10.0], [100.0, 0.0, 10.0]]}
    row.update(extra)
    return row


def _screwed(panel="lid"):
    return {
        "components": [_component("deck", role="frame"), _component("board"),
                       _component(panel, role="panel", appearance="shell"),
                       _component("s0", family="bolt", part_number="m2x8-socket",
                                  box=([-1, -1, 0], [1, 1, 12])),
                       _component("s1", family="bolt", part_number="m2x8-socket",
                                  box=([99, -1, 0], [101, 1, 12]))],
        "pairs": [_pair(panel, "s0", 0.0), _pair("deck", "s0", 0.0, 4.5),
                  _pair(panel, "s1", 0.0), _pair("deck", "s1", 0.0, 4.5),
                  _pair("deck", panel, 0.0), _pair("board", panel, 2.0)],
        "attachments": [],
        "panels": [_measured(panel, 3.0)],
        "available": True,
    }


def test_a_screwed_thin_hugging_panel_passes():
    block = panel_summary(_screwed())
    assert block["verdict"] == "pass" and block["panel_count"] == 1
    lid = block["fitted"][0]
    assert (lid["mounted"], lid["screws"], lid["held_by"]) == ("screws", ["s0", "s1"], ["deck"])
    assert lid["findings"] == [] and lid["covers"] == ["board"]
    assert lid["farthest_from_fastener_mm"] == pytest.approx(4.0, abs=0.2)
    assert fit_summary(_screwed())["verdict"] == "pass"


def test_a_part_painted_shell_is_not_judged_as_a_panel():
    value = _screwed()
    value["components"][2].pop("role")
    block = panel_summary(value)
    assert block["verdict"] == "none" and "colour" in block["note"]


def test_floating_colliding_and_unmounted_panels_fail_the_fit():
    value = {
        "components": [_component("deck", role="frame"), _component("board"),
                       _component("leg"),
                       _component("egg", role="panel"), _component("rub", role="panel"),
                       _component("loose", role="panel")],
        "pairs": [_pair("board", "rub", 0.0, 12.0), _pair("deck", "egg", 0.0)],
        "attachments": [{"first": "deck", "second": "egg", "status": "touching"},
                        {"first": "deck", "second": "rub", "status": "touching"}],
        "clearance_sweep": {"status": "complete", "joints": [
            {"joint": "hip", "status": "complete", "pairs": [
                {"first": "leg", "second": "rub", "minimum_distance_mm": 0.0,
                 "maximum_common_volume_mm3": 40.0, "relative_motion": True},
                {"first": "leg", "second": "egg", "minimum_distance_mm": 0.2,
                 "maximum_common_volume_mm3": 0.0, "relative_motion": True}]},
            {"joint": "knee", "status": "incomplete", "pairs": []}]},
        "panels": [_measured("egg", 31.3, egg_ratio=6.0), _measured("rub", 2.0),
                   _measured("loose", 2.0)],
        "available": True,
    }
    block = panel_summary(value)
    assert block["verdict"] == "fail" and block["failing_count"] == 3
    by = {row["component"]: row for row in block["failing"]}
    assert by["egg"]["findings"] == ["floating", "egg"]
    assert "31.3 mm" in by["egg"]["detail"]
    assert by["egg"]["closest_in_motion"]["minimum_distance_mm"] == 0.2
    assert by["rub"]["findings"] == ["colliding", "colliding in motion"]
    assert by["rub"]["colliding_with"][0]["with"] == "board"
    assert by["rub"]["colliding_in_motion"][0]["joint"] == "hip"
    assert by["loose"]["findings"] == ["unmounted"]
    assert "knee" in block["motion_note"]
    fit = fit_summary(value)
    assert fit["verdict"] == "fail" and fit["panel_failing_count"] == 3
    assert fit["failing_count"] == 1  # the board/rub overlap, as a pair


def test_a_grown_panel_is_held_to_its_own_clearance_and_radius():
    value = _screwed()
    value["components"][2]["panel"] = {"group": "g1", "piece": "p0", "clearance_mm": 1.5,
                                       "radius_mm": 30.0, "thickness_mm": 2.0}
    value["panels"] = [_measured("lid", 16.0)]
    block = panel_summary(value)
    assert block["verdict"] == "pass", block
    assert block["fitted"][0]["floating_at_mm"] == pytest.approx(18.5)
    value["panels"] = [_measured("lid", 19.0)]
    assert panel_summary(value)["failing"][0]["findings"] == ["floating"]
    # A hand-made panel is held to the fixed bar.
    plain = _screwed()
    plain["panels"] = [_measured("lid", 9.0)]
    assert panel_summary(plain)["failing"][0]["floating_at_mm"] == \
        CadexFitReport.PANEL_FLOATING_GAP_MM


def test_advisory_findings_are_named_and_do_not_fail():
    value = _screwed()
    value["panels"] = [_measured("lid", 3.0, egg_ratio=3.1, wall_median_mm=6.0,
                                 size_mm=[300.0, 40.0, 20.0],
                                 points=[[0.0, 0.0, 0.0], [400.0, 0.0, 0.0]])]
    block = panel_summary(value)
    assert block["verdict"] == "reported" and block["failing_count"] == 0
    assert block["reported"][0]["findings"] == ["egg", "solid", "larger than the bed",
                                                 "under-held"]
    assert fit_summary(value)["verdict"] == "pass"


def test_pieces_of_one_panel_keep_a_seam_gap():
    value = _screwed()
    value["components"].append(_component("lid_b", role="panel",
                                          panel={"group": "g1", "piece": "p1"}))
    value["components"][2]["panel"] = {"group": "g1", "piece": "p0"}
    value["pairs"] += [_pair("lid", "lid_b", 0.0), _pair("deck", "lid_b", 0.0)]
    value["attachments"] = [{"first": "deck", "second": "lid_b", "status": "touching"}]
    value["panels"].append(_measured("lid_b", 3.0))
    block = panel_summary(value)
    by = {row["component"]: row for row in block["reported"] + block["fitted"]}
    assert by["lid"]["seam_gap_mm"] == 0.0 and "seam closed" in by["lid"]["findings"]
    value["pairs"][-2] = _pair("lid", "lid_b", 0.6)
    by = {row["component"]: row for row in panel_summary(value)["fitted"]}
    assert by["lid"]["seam_gap_mm"] == 0.6


def test_the_panel_block_rides_in_the_fit_block_and_its_view():
    value = {"components": [_component("deck")], "pairs": [], "available": True}
    assert fit_summary(value)["panels"]["verdict"] == "none"
    many = {"components": [_component("deck")] + [
        _component(f"p{k}", role="panel") for k in range(20)],
        "pairs": [], "panels": [_measured(f"p{k}", 3.0) for k in range(20)], "available": True}
    view = fit_view(fit_summary(many))
    assert len(view["panels"]["failing"]) == 12
    assert view["panels"]["failing_omitted"] == 8
    old = panel_summary({"components": [_component("lid", role="panel")]})
    assert old["failing"][0]["gap"] == "unmeasured" and "gap_note" in old
    assert panel_summary({})["verdict"] == "unavailable"


def test_the_bed_is_the_studio_bed():
    import CadexStudio

    assert tuple(CadexFitReport.PANEL_BED_MM) == tuple(CadexStudio.BED_MM)
