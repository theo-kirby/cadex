# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""P2's engine half: how much of a solid's edge length is a sharp convex corner (ADR-415).

A1 froze ``sharp_outside_edge_share`` (docs/probes/ot10/README.md): sharp
convex edge length over total edge length, where sharp means the two
faces' outward normals turn by more than 60 degrees at the edge's midpoint.
The measure is geometry, so it is proved against the kernel: a bare box
fails the 0.25 bar and the same box filleted or chamfered passes. The
exclusions the definition names are pinned too -- a seam is not an edge
between two faces, and a concave corner is not an outside edge.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from test_cadexd_lifecycle import FREECADCMD

import cadex_part_worker as worker


_MODULE_DIR = Path(worker.__file__).resolve().parent

_SCRIPT = """
import json, sys
sys.path.insert(0, {module_dir!r})
import FreeCAD, Part
from FreeCAD import Vector
from cadex_part_worker import part_shape_facts, sharp_edge_facts
box = Part.makeBox(40, 20, 10)
shapes = {{
    "box": box,
    "filleted": box.makeFillet(3, box.Edges),
    "chamfered": box.makeChamfer(2, box.Edges),
    "l_block": Part.makeBox(20, 20, 10).cut(Part.makeBox(10, 10, 10, Vector(10, 10, 0))),
    "cylinder": Part.makeCylinder(5, 10),
    "boss": Part.makeBox(40, 40, 10).fuse(
        Part.makeCylinder(5, 20, Vector(20, 20, 0))).removeSplitter(),
    "wire": Part.makePolygon([Vector(0, 0, 0), Vector(10, 0, 0), Vector(10, 10, 0)]),
}}
out = {{name: sharp_edge_facts(shape) for name, shape in shapes.items()}}
out["facts"] = part_shape_facts(box, max_subelements=0)["sharp_edges"]
out["counts_only"] = "sharp_edges" in part_shape_facts(box, max_subelements=0, edge_convexity=False)
json.dump(out, open({target!r}, "w"))
"""


def _share(row):
    return row["sharp_convex_length_mm"] / row["edge_length_mm"]


@pytest.fixture(scope="module")
def measured():
    if FREECADCMD is None:
        pytest.skip("No FreeCADCmd binary available for the edge measure.")
    with tempfile.TemporaryDirectory(prefix="cadex-p2-") as directory:
        target = str(Path(directory) / "out.json")
        source = _SCRIPT.format(module_dir=str(_MODULE_DIR), target=target)
        result = subprocess.run(
            [str(FREECADCMD), "-c", source], capture_output=True, text=True, timeout=120,
        )
        assert Path(target).is_file(), result.stdout + result.stderr
        return json.loads(Path(target).read_text())


def test_a_bare_box_fails_the_bar_and_a_blended_one_passes(measured) -> None:
    box = measured["box"]
    assert box["edge_length_mm"] == pytest.approx(4 * (40 + 20 + 10))
    assert _share(box) == pytest.approx(1.0) and _share(box) > 0.25
    for blended in ("filleted", "chamfered"):
        row = measured[blended]
        assert row["edge_length_mm"] > box["edge_length_mm"], row
        assert row["sharp_convex_length_mm"] == pytest.approx(0.0), (blended, row)
        assert row["unresolved_edges"] == 0
    assert measured["box"]["threshold_deg"] == worker.SHARP_EDGE_DEGREES == 60.0


def test_a_concave_corner_and_a_seam_are_not_outside_edges(measured) -> None:
    # The L's one inner vertical edge (10 mm) is concave; the other 210 mm is sharp.
    l_block = measured["l_block"]
    assert l_block["edge_length_mm"] == pytest.approx(220.0)
    assert l_block["sharp_convex_length_mm"] == pytest.approx(210.0)
    # A cylinder's seam has its lateral face on both sides: two rims only.
    cylinder = measured["cylinder"]
    assert cylinder["edge_length_mm"] == pytest.approx(2 * 2 * 3.141592653589793 * 5)
    assert _share(cylinder) == pytest.approx(1.0)
    # A boss's root circle is concave and drops out of the sharp length only.
    boss = measured["boss"]
    assert boss["edge_length_mm"] - boss["sharp_convex_length_mm"] == pytest.approx(
        2 * 3.141592653589793 * 5)


def test_the_fact_rides_on_shape_facts_and_is_empty_without_a_solid(measured) -> None:
    assert measured["facts"] == measured["box"]
    assert measured["counts_only"] is False
    assert measured["wire"]["edge_length_mm"] == 0.0
    assert measured["wire"]["sharp_convex_length_mm"] == 0.0
