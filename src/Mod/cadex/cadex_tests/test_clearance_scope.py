# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from CadexInspection import capture_inspection, complete_inspection
from cadex_assembly_worker import _measure_clearance
from cadex_project_worker import compute_project_digest
from test_inventory_scope import _store, _service, _component_output


def test_measurement_failure_keeps_every_pair_unknown():
    components = {name: SimpleNamespace() for name in ('a', 'b', 'c')}
    rows = _measure_clearance(components)
    assert [(r['first'], r['second']) for r in rows] == [('a', 'b'), ('a', 'c'), ('b', 'c')]
    assert all(r['distance_mm'] is None and r['common_volume_mm3'] is None and r['error'] for r in rows)


def test_measurements_do_not_move_the_content_digest(tmp_path):
    output = {'name': 'asm', 'domain': 'assembly', 'type': 'assembly', 'definition': {'operation': 'assembly'}}
    before = compute_project_digest(tmp_path, [output])
    output['clearance'] = [{'first': 'a', 'second': 'b', 'distance_mm': 1.0, 'common_volume_mm3': 0.0}]
    assert compute_project_digest(tmp_path, [output]) == before
    output['clearance'][0]['distance_mm'] = 2.0
    assert compute_project_digest(tmp_path, [output]) == before


def test_legacy_assembly_has_unknown_pairs_and_catalog_labels(tmp_path):
    root = _store(tmp_path, {'ok': True, 'outputs': [
        {'name': 'asm', 'type': 'assembly'},
        {'name': 'bolt', 'catalog': {'family': 'bolt', 'part_number': 'm3x12-socket'}},
        _component_output('a', 'bolt', position=[0, 0, 0]),
        _component_output('b', 'bolt', position=[0, 0, 1]),
    ]})
    captured = capture_inspection(_service(root), {'scope': 'clearance'})
    result = complete_inspection(captured)
    assert result['ok'], json.dumps(result)
    value = result['value']
    assert value['available'] is False
    row, = value['pairs']
    assert row['distance_mm'] is None and row['common_volume_mm3'] is None
    assert row['first_label'] == 'a label'
    assert row['first_catalog']['part_number'] == 'm3x12-socket'


def test_no_assembly_is_unavailable(tmp_path):
    root = _store(tmp_path, {'ok': True, 'outputs': []})
    result = complete_inspection(capture_inspection(_service(root), {'scope': 'clearance'}))
    assert result['ok'], json.dumps(result)
    assert result['value']['available'] is False
    assert result['value']['pairs'] == []


def test_unsolved_assembly_does_not_claim_a_solved_pose():
    rows = _measure_clearance({'a': object(), 'b': object()}, solved=False)
    assert rows[0]['distance_mm'] is None
    assert 'solved pose' in rows[0]['error']


# --------------------------------------------------------------------------
# the frame, against a real kernel (ADR-241)
# --------------------------------------------------------------------------


REPO_ROOT = Path(__file__).resolve().parents[4]
_FREECADCMD_CANDIDATES = (
    REPO_ROOT / ".pixi" / "envs" / "default" / "bin" / "FreeCADCmd",
    REPO_ROOT / "build" / "release" / "bin" / "FreeCADCmd",
)
FREECADCMD = next(
    (candidate for candidate in _FREECADCMD_CANDIDATES if candidate.is_file()), None
)


#: Four bodies, three of which carry their transform on the *shape* rather
#: than on the component -- which is every ``lib.*`` part, because
#: ``lib._place`` moves a canonical part with one ``part.transform`` and
#: ``Shape.translate`` writes a placement instead of moving geometry.
#: ``App::Link.Shape`` replaces that placement with the link's own, so before
#: ADR-241 A and B read as one fully intersecting body 40 mm apart.
_FRAME_DRIVER = r'''
import json
import sys
from pathlib import Path

import FreeCAD as App
import Part

cadex_root = Path(sys.argv[-1])
sys.path.insert(0, str(cadex_root))
from cadex_assembly_worker import _measure_clearance

doc = App.newDocument("ClearanceFrame")


def feature(name, shape):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj


def link(name, source, placement=None):
    obj = doc.addObject("App::Link", name)
    obj.LinkedObject = source
    if placement is not None:
        obj.Placement = placement
    return obj


# A: a canonical-frame body moved by part.transform, component identity.
moved = Part.makeBox(10, 10, 10)
moved.translate(App.Vector(0, 0, 50))
a = link("A", feature("MovedSource", moved))
# B: authored in world coordinates, identity everywhere.
b = link("B", feature("WorldSource", Part.makeBox(10, 10, 10)))
# C: both frames non-identity -- shape +50, component +100, so 150..160.
c = link("C", feature("BothSource", moved.copy()),
         App.Placement(App.Vector(0, 0, 100), App.Rotation()))
# D: a shape-placed body that really does overlap B, by 2 mm.
sunk = Part.makeBox(10, 10, 10)
sunk.translate(App.Vector(0, 0, 8))
d = link("D", feature("SunkSource", sunk))
doc.recompute()

rows = _measure_clearance({"A": a, "B": b, "C": c, "D": d})
print("CLEARANCE-FRAME " + json.dumps(
    {
        f"{row['first']}{row['second']}": [
            row["distance_mm"], row["common_volume_mm3"], row.get("error")
        ]
        for row in rows
    },
    sort_keys=True,
))
'''


def _drive_frame(tmp_path) -> dict:
    driver = tmp_path / "clearance_frame_driver.py"
    driver.write_text(_FRAME_DRIVER, encoding="utf-8")
    cadex_root = Path(__file__).resolve().parent.parent
    completed = subprocess.run(
        [
            str(FREECADCMD),
            "-c",
            (
                "import sys; sys.argv = ['driver', "
                f"{str(cadex_root)!r}]; "
                f"exec(open({str(driver)!r}).read())"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=900,
        env={**os.environ, "PYTHONHASHSEED": "0"},
        check=False,
    )
    marker = next(
        (
            line
            for line in completed.stdout.splitlines()
            if line.startswith("CLEARANCE-FRAME ")
        ),
        None,
    )
    assert marker, (
        f"clearance driver produced no report; exit={completed.returncode}\n"
        f"stdout:\n{completed.stdout[-6000:]}\nstderr:\n{completed.stderr[-6000:]}"
    )
    return json.loads(marker.removeprefix("CLEARANCE-FRAME "))


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available to place a component."
)
def test_a_shape_placed_component_is_measured_where_it_is(tmp_path) -> None:
    """The pair a walk got wrong: two placed bodies, 40 mm apart, not one.

    A pan-tilt head built from two catalog MG90S reported both servos fully
    intersecting and a base/servo overlap ten times its true volume, while
    the render, the section, the MJCF inertials and the exported STL all
    agreed the parts were where the script put them.
    """

    report = _drive_frame(tmp_path)
    assert all(row[2] is None for row in report.values()), report

    # The false intersection: A is 40 mm above B, sharing nothing.
    assert report["AB"][0] == pytest.approx(40.0, abs=1e-6), report
    assert report["AB"][1] == pytest.approx(0.0, abs=1e-6), report
    # The component placement composes with the shape's rather than
    # replacing it: C stands at 150..160, not at 100..110.
    assert report["BC"][0] == pytest.approx(140.0, abs=1e-6), report
    assert report["CD"][0] == pytest.approx(132.0, abs=1e-6), report
    # A real overlap is still reported, and at its true volume -- 10 x 10 x 2,
    # not the whole 10 x 10 x 10 the wrong frame gave.
    assert report["BD"][0] == pytest.approx(0.0, abs=1e-6), report
    assert report["BD"][1] == pytest.approx(200.0, rel=1e-9), report
