# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The smoke check's first-frame agreement reads a bounded static row as a bound (ADR-423)."""
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FREECADCMD = next((p for p in (ROOT / ".pixi/envs/default/bin/FreeCADCmd",
                               ROOT / "build/release/bin/FreeCADCmd") if p.is_file()), None)
SMOKE = ROOT / "cli" / "cadex_cli" / "smoke_geometry.py"


@pytest.mark.skipif(FREECADCMD is None, reason="Needs real OCCT")
def test_a_culled_static_row_agrees_when_the_exact_distance_reaches_its_bound(tmp_path):
    # Two unit spheres 40 mm apart centre to centre: 38 mm exact, and the
    # engine may publish any bound at or below that as a culled row.
    subprocess.run([str(FREECADCMD), "-c", (
        "import Part, FreeCAD as App;"
        f"Part.makeSphere(1).exportBrep({str(tmp_path / 'a.brep')!r});"
        f"Part.makeSphere(1, App.Vector(40, 0, 0)).exportBrep({str(tmp_path / 'b.brep')!r})")],
        check=True, capture_output=True, timeout=300)
    identity = {"position_mm": [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]}
    (tmp_path / "trace.json").write_text(json.dumps(
        [{"time_s": 0.0, "placements": {"a": identity, "b": identity}}]))

    def run(static):
        plan = {"trace": str(tmp_path / "trace.json"), "out": str(tmp_path / "out.json"),
                "maximum_volume_mm3": 1e-6, "static": [static],
                "geometry": [{"name": n, "path": str(tmp_path / f"{n}.brep")} for n in "ab"]}
        (tmp_path / "plan.json").write_text(json.dumps(plan))
        subprocess.run([str(FREECADCMD), str(SMOKE)], check=True, capture_output=True, timeout=300,
                       env={**os.environ, "CADEX_SMOKE_GEOMETRY_PLAN": str(tmp_path / "plan.json")})
        return json.loads((tmp_path / "out.json").read_text())

    row = {"first": "a", "second": "b", "distance_mm": 36.0, "common_volume_mm3": 0.0}
    assert run(dict(row, culled=True))["pass"] is True
    # An exact row still has to equal the measurement, and a bound above the
    # exact distance is a disagreement, not a pass.
    assert "error" in run(row)
    assert "error" in run(dict(row, distance_mm=38.5, culled=True))


@pytest.mark.skipif(FREECADCMD is None, reason="Needs real OCCT")
def test_the_first_frame_measures_shells_the_way_the_engine_published_them(tmp_path):
    # ADR-581: the engine publishes a near pair's distance between shells
    # (ADR-425). A sphere nested in a box is 4 mm from it shell to shell,
    # while a solid's distToShape answers 0 through OCCT's inside test --
    # the test that, on a printed shin, called a vertex 89 mm away inside.
    subprocess.run([str(FREECADCMD), "-c", (
        "import Part, FreeCAD as App;"
        f"Part.makeBox(10, 10, 10).exportBrep({str(tmp_path / 'box.brep')!r});"
        f"Part.makeSphere(1, App.Vector(5, 5, 5)).exportBrep({str(tmp_path / 'ball.brep')!r})")],
        check=True, capture_output=True, timeout=300)
    identity = {"position_mm": [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]}
    (tmp_path / "trace.json").write_text(json.dumps(
        [{"time_s": 0.0, "placements": {"ball": identity, "box": identity}}]))
    plan = {"trace": str(tmp_path / "trace.json"), "out": str(tmp_path / "out.json"),
            "maximum_volume_mm3": 1e-6,
            "static": [{"first": "ball", "second": "box", "distance_mm": 4.0,
                        "common_volume_mm3": 4.0 / 3.0 * 3.141592653589793}],
            "geometry": [{"name": n, "path": str(tmp_path / f"{n}.brep")} for n in ("ball", "box")]}
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    subprocess.run([str(FREECADCMD), str(SMOKE)], check=True, capture_output=True, timeout=300,
                   env={**os.environ, "CADEX_SMOKE_GEOMETRY_PLAN": str(tmp_path / "plan.json")})
    result = json.loads((tmp_path / "out.json").read_text())
    # The pose agrees; the nested volume is then the finding, not an error.
    assert "error" not in result, result
    assert result["pass"] is False
    assert [(r["first"], r["second"]) for r in result["failing"]] == [("ball", "box")]
