# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Panels cut from the envelope of what they cover, and housings round drives.

``part.envelope`` and ``part.panel`` (ADR-635) are declarations: the script
half validates them and makes one value per piece, the screws mated onto
fastener frames the worker fills in, and the frame's pilots. The worker
half (``CadexEnvelope``) builds the field, the surface, the skirt and the
bosses on the exact solids; its array steps are tested here headless, and
one real-kernel test builds a cover over a battery and a board on a deck.
``lib.housing`` (ADR-611) wraps a drive's own envelope and screws it through
its own holes.
"""

from __future__ import annotations

import json
import math

import pytest

import CadexEnvelope as envelope_worker
from CadexMounts import Mount
from CadexPanels import Envelope, Panel, PanelMount
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import DomainValue, create_domain_api
from cadex_library_api import (LibraryError, create_library_api, library_catalog_identity,
                               library_listing)

PART_PACK = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]


def _part():
    return create_domain_api(PART_PACK.domain, PART_PACK.api_exports, PART_PACK.output_types)


def _lib():
    return create_library_api(_part())


def _trunk(lib):
    part = lib._part
    deck = part.box(160, 110, 4, origin=(-80, -40, -2))
    pack = lib.battery("gensace-gea2s100045d", origin=(-30, 0, 2))
    board = lib.board("esp32-devkitc-v4", origin=(18, -14, 2))
    return deck, pack, board


# --------------------------------------------------------------------------
# the declarations
# --------------------------------------------------------------------------


def test_an_envelope_is_a_declaration_of_what_is_covered():
    lib = _lib()
    part = lib._part
    _deck, pack, board = _trunk(lib)
    link = part.box(10, 10, 60, origin=(40, -5, 0))
    env = part.envelope([pack, board], clearance=2.0, radius=25.0,
                        motion=[{"shape": link, "origin": (45, 0, 0), "axis": (0, 1, 0),
                                 "range": (30, -30)}])
    assert isinstance(env, Envelope) and not isinstance(env, DomainValue)
    assert env.spec["over"] == [pack.body, board.body]
    assert env.spec["motion"][0]["kind"] == "hinge"
    assert env.spec["motion"][0]["range"] == [-30.0, 30.0]
    with pytest.raises(ValueError, match="at least one part"):
        part.envelope([])
    with pytest.raises(ValueError, match="clearance must be between"):
        part.envelope([pack], clearance=0.0)
    with pytest.raises(ValueError, match="'axis'"):
        part.envelope([pack], motion=[{"shape": link, "range": (0, 1)}])
    with pytest.raises(ValueError, match="lib.\\* part"):
        part.envelope(["box"])


def test_a_panel_makes_one_value_per_piece_and_mates_its_screws_onto_its_bosses():
    lib = _lib()
    part = lib._part
    deck, pack, board = _trunk(lib)
    env = part.envelope([pack, board])
    panel = part.panel(env, side=(0, 0, 1), frame=deck, screw=lib.bolt("m2", 8), screws=3,
                       seams=[((1, 0, 0), [0.0])], flange="frame", label="lid")
    assert isinstance(panel, Panel)
    assert panel.names == ["p0", "p1"] and len(panel.parts) == 2
    assert all(p.operation == "panel" and p.output_type == "solid" for p in panel.parts)
    assert [p.properties["piece"] for p in panel.parts] == ["p0", "p1"]
    # One spec for every piece: the worker plans it once.
    assert panel.parts[0].arguments[0] == panel.parts[1].arguments[0]
    assert panel.pilots.output_type == "compound" and panel.pilots.properties["piece"] == "pilots"
    assert len(panel.screws) == 6 and sorted(panel.mounts) == ["p0", "p1"]
    assert sorted(panel.mounts["p0"]) == ["b0", "b1", "b2"]
    target = panel.mounts["p1"]["b2"]
    assert isinstance(target, PanelMount) and isinstance(target, Mount)
    screw = panel.screws[5]
    assert screw.family == "bolt" and screw.part_number == "m2x8-socket"
    assert screw.body.operation == "mate"
    assert screw.body.arguments[2]["panel_fastener"] == "b2"
    assert screw.body.arguments[2]["shape"]["properties"]["piece"] == "p1"
    # Each placed screw is catalogued as the bolt it is, for the mounting check.
    identity = library_catalog_identity()
    key = json.dumps(screw.body.to_payload(), ensure_ascii=True, sort_keys=True,
                     separators=(",", ":"), allow_nan=False)
    assert identity[key] == {"family": "bolt", "part_number": "m2x8-socket"}
    spec = panel.parts[0].arguments[0]
    assert spec["screw"]["size"] == "m2" and spec["screws"] == 3 and spec["flange"] == "frame"


def test_a_panel_declaration_refuses_what_it_cannot_build():
    lib = _lib()
    part = lib._part
    deck, pack, _board = _trunk(lib)
    env = part.envelope([pack])
    with pytest.raises(ValueError, match="part.envelope"):
        part.panel(pack)
    with pytest.raises(ValueError, match="needs frame="):
        part.panel(env, screw=lib.bolt("m2", 8))
    with pytest.raises(ValueError, match="lib.bolt"):
        part.panel(env, frame=deck, screw="m2")
    with pytest.raises(ValueError, match="countersink"):
        part.panel(env, frame=deck, screw=lib.bolt("m3", 10, head="countersunk"))
    with pytest.raises(ValueError, match="pieces"):
        part.panel(env, seams=[((1, 0, 0), [-60, -40, -20, 0, 20]),
                               ((0, 1, 0), [-10, 10])])
    with pytest.raises(ValueError, match='flange="frame" needs frame='):
        part.panel(env, flange="frame")
    with pytest.raises(ValueError, match="'around', 'cone' or 'at'"):
        part.panel(env, openings=[{"radius": 3}])
    openings = part.panel(env, openings=[
        {"around": pack, "clearance": 3.0, "motion": {"origin": (0, 0, 0), "axis": (0, 1, 0),
                                                       "range": (-10, 10)}},
        {"cone": ((0, 0, 0), (1, 0, 0), 30.0)}, {"at": (0, 0, 20), "radius": 4.0}],
        within=((-100, -100, 0), (100, 100, 50)), max_angle=45.0)
    spec = openings.parts[0].arguments[0]
    assert [sorted(o) for o in spec["openings"]] == [["around", "clearance", "motion"],
                                                     ["cone"], ["at", "radius"]]
    assert openings.screws == [] and openings.pilots is None and openings.mounts == {}


def test_describe_api_lists_the_panel_ops_and_lib_panel_is_gone():
    exports = {row["name"]: row for row in library_listing()["exports"]}
    assert "panel" not in exports
    assert "wall" in exports["housing"]["signature"]
    part = _part()
    assert {"envelope", "panel"} <= set(part.exported_names)
    assert "radius" in part.envelope.__doc__ and "flange" in part.panel.__doc__
    with pytest.raises(AttributeError):
        _lib().panel  # noqa: B018 - the attribute is what is asserted


# --------------------------------------------------------------------------
# the worker's arrays
# --------------------------------------------------------------------------


def _box_triangles(low, high):
    (x0, y0, z0), (x1, y1, z1) = low, high
    v = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    tris = []
    for a, b, c, d in faces:
        tris += [(v[a], v[b], v[c]), (v[a], v[c], v[d])]
    return tris


def test_a_box_fills_its_own_voxels_and_no_others():
    import numpy as np

    occ = envelope_worker.occupancy(_box_triangles((2, 2, 2), (8, 6, 4)), (0, 0, 0), 1.0,
                                    (10, 10, 10))
    assert occ.sum() == 6 * 4 * 2
    assert occ[2:8, 2:6, 2:4].all() and not occ[:2].any() and not occ[:, :, 4:].any()
    assert np.array_equal(occ, envelope_worker.occupancy(
        np.array(_box_triangles((2, 2, 2), (8, 6, 4))), (0, 0, 0), 1.0, (10, 10, 10)))


def test_the_rolling_radius_bridges_a_gap_narrower_than_twice_itself():
    import numpy as np

    occ = np.zeros((40, 12, 30), dtype=bool)
    occ[2:16, 2:10, 2:10] = True
    occ[22:38, 2:10, 2:10] = True            # a 6-voxel gap between two blocks
    hug = envelope_worker.closed_distance(occ, 1.0, 0.0)
    bridged = envelope_worker.closed_distance(occ, 1.0, 5.0)
    assert hug[19, 6, 6] > 2.0               # shrink-wrapped: the gap stays open
    assert bridged[19, 6, 6] == 0.0          # r = 5 closes a 6 mm gap
    assert bridged[19, 6, 16] > 0.0          # ...but not above the blocks
    assert hug[0, 6, 6] == pytest.approx(1.5, abs=0.01)   # the half-cell bias is off


def test_the_height_field_is_the_first_crossing_from_the_side():
    import numpy as np

    field = np.zeros((4, 4, 20))
    field[:] = np.clip(np.arange(20) - 9.5, 0, None)[None, None, :]   # top face at z = 10
    z = envelope_worker.height_field(field, 0.0, 1.0, 2.0)
    assert np.allclose(z, 12.0)
    field[0, 0, :] = 50.0
    assert np.isnan(envelope_worker.height_field(field, 0.0, 1.0, 2.0)[0, 0])


def test_outlines_are_contoured_outer_counter_clockwise_holes_clockwise():
    import numpy as np

    X, Y = np.meshgrid(np.arange(41.0), np.arange(41.0), indexing="ij")
    r = np.hypot(X - 20, Y - 20)
    phi = np.minimum(15.0 - r, r - 5.0)       # an annulus
    loops = envelope_worker.contour_loops(phi, 0.0, 0.0, 1.0)
    nested = envelope_worker.nest_loops(loops)
    assert len(nested) == 1 and len(nested[0][1]) == 1
    outer, (hole,) = nested[0]
    assert envelope_worker._signed_area(outer) == pytest.approx(math.pi * 225, rel=0.02)
    assert envelope_worker._signed_area(hole) == pytest.approx(-math.pi * 25, rel=0.05)


def test_screw_sites_spread_and_prefer_a_short_reach():
    sites = [(0, 0, 5), (100, 0, 5), (50, 0, 5), (0, 1, 30), (100, 60, 5), (99, 60, 40)]
    chosen = envelope_worker.choose_sites(sites, 3)
    assert len(chosen) == 3 and 3 not in chosen and 5 not in chosen
    assert envelope_worker.choose_sites(sites, 2, start=[2])[0] == 2


def test_pieces_are_numbered_by_seam_cell():
    import numpy as np

    seams = [{"normal": [1, 0, 0], "at": [0.0]}, {"normal": [0, 1, 0], "at": [-5.0, 5.0]}]
    points = np.array([[-1, -9, 0], [-1, 0, 0], [-1, 9, 0], [1, -9, 0], [1, 9, 0]], float)
    assert envelope_worker.piece_index(points, seams).tolist() == [0, 1, 2, 3, 5]
    assert envelope_worker._seam_distance(points, seams).tolist() == [1, 1, 1, 1, 1]


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
# the real kernel
# --------------------------------------------------------------------------


def test_a_cover_and_a_housing_build_valid_solids_on_the_kernel(tmp_path):
    import subprocess
    from test_cadexd_lifecycle import CADEX_ROOT, FREECADCMD
    if FREECADCMD is None:
        pytest.skip("needs a built engine (pixi run build-engine)")

    driver = tmp_path / "panels.py"
    report = tmp_path / "report.txt"
    driver.write_text(f'''
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import create_domain_api
from cadex_library_api import create_library_api
from cadex_part_worker import build_part_shape
out = open({str(report)!r}, "w")
pack = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]
part = create_domain_api(pack.domain, pack.api_exports, pack.output_types)
lib = create_library_api(part)
deck = part.box(160, 110, 4, origin=(-80, -40, -2))
battery = lib.battery("gensace-gea2s100045d", origin=(-30, 0, 2))
board = lib.board("esp32-devkitc-v4", origin=(18, -14, 2))
env = part.envelope([battery, board], clearance=1.5, radius=20.0)
cover = part.panel(env, side=(0, 0, 1), max_angle=70, frame=deck, screw=lib.bolt("m2", 8),
                   screws=3, seams=[((1, 0, 0), [0.0])], flange="frame")
deck_shape = build_part_shape(part.cut(deck, cover.pilots).to_payload())
contents = [build_part_shape(v.body.to_payload()) for v in (battery, board)]
for name, body in zip(cover.names, cover.parts):
    facts = {{}}
    shape = build_part_shape(body.to_payload(), diagnostics=facts)
    assert shape.isValid() and len(shape.Solids) == 1, name
    assert 1.4 < 2 * shape.Volume / shape.Area < 3.0, (name, 2 * shape.Volume / shape.Area)
    assert min(shape.distToShape(c)[0] for c in contents) > 1.2, name
    assert shape.common(deck_shape).Volume < 1e-3, name
    assert shape.distToShape(deck_shape)[0] < 0.25, name
    grown = facts["panel"]
    assert grown["piece"] == name and grown["clearance_mm"] == 1.5
    assert len(grown["fasteners"]) == 3 and grown["flange"][0]["depth_mm"] > 3.0
    out.write(name + " ok\\n")
for bolt in cover.screws:
    shank = build_part_shape(bolt.body.to_payload())
    assert 0.1 < shank.common(deck_shape).Volume < 8.0
    assert all(shank.common(c).Volume < 1e-6 for c in contents)
qdd = lib.qdd("cubemars-ak80-9-v3", origin=(-121.5, 0, 0), direction=(-1, 0, 0))
drum = build_part_shape(lib.housing(qdd).body.to_payload())
motor = build_part_shape(qdd.body.to_payload())
assert drum.isValid() and len(drum.Solids) == 1
assert drum.common(motor).Volume < 1e-6 and drum.distToShape(motor)[0] < 1e-6
out.write("PANELS-OK\\n")
out.close()
''')
    completed = subprocess.run(
        [str(FREECADCMD), "-c",
         f"import sys; sys.path.insert(0, {str(CADEX_ROOT)!r}); exec(open({str(driver)!r}).read())"],
        capture_output=True, text=True, timeout=900,
    )
    written = report.read_text() if report.exists() else ""
    assert "PANELS-OK" in written, written + completed.stdout[-3000:] + completed.stderr[-3000:]
