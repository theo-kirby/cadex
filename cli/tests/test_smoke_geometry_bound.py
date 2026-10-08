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
    # ADR-582: frame 1 moves both rigidly, so the boolean is reused; frame 2
    # moves the ball 1 mm inside the box, so it is run again.
    carried = {"position_mm": [7, -3, 2], "rotation_xyzw": [0, 0, 0.6, 0.8]}
    nudged = {"position_mm": [1, 0, 0], "rotation_xyzw": [0, 0, 0, 1]}
    (tmp_path / "trace.json").write_text(json.dumps(
        [{"time_s": 0.0, "placements": {"ball": identity, "box": identity}},
         {"time_s": 0.1, "placements": {"ball": carried, "box": carried}},
         {"time_s": 0.2, "placements": {"ball": nudged, "box": identity}}]))
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
    assert result["booleans"] == {"run": 2, "reused": 1}
    assert abs(result["failing"][0]["common_volume_mm3"] - 4.0 / 3.0 * 3.141592653589793) < 1e-2


@pytest.mark.skipif(FREECADCMD is None, reason="Needs real OCCT")
def test_a_threaded_bolt_holds_its_allowance_while_a_real_collision_fails(tmp_path):
    # ADR-583: a bolt half-sunk in a block shares 2π mm³ with it, inside the
    # thread allowance the CLI passed (ADR-492); a ball driven into the block
    # is a collision, and the bolt driven past its thread is one too.
    subprocess.run([str(FREECADCMD), "-c", (
        "import Part, FreeCAD as App;"
        f"Part.makeBox(10, 10, 10).exportBrep({str(tmp_path / 'block.brep')!r});"
        f"Part.makeCylinder(1, 4, App.Vector(5, 5, 8)).exportBrep({str(tmp_path / 'bolt.brep')!r});"
        f"Part.makeSphere(1, App.Vector(2, 2, 20)).exportBrep({str(tmp_path / 'ball.brep')!r})")],
        check=True, capture_output=True, timeout=300)
    identity = {"position_mm": [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]}
    names = ("ball", "block", "bolt")

    def run(*moves):
        trace = [{"time_s": 0.0, "placements": {n: identity for n in names}}]
        for i, move in enumerate(moves):
            trace.append({"time_s": 0.1 * (i + 1), "placements": {
                n: {"position_mm": move.get(n, [0, 0, 0]), "rotation_xyzw": [0, 0, 0, 1]} for n in names}})
        (tmp_path / "trace.json").write_text(json.dumps(trace))
        plan = {"trace": str(tmp_path / "trace.json"), "out": str(tmp_path / "out.json"),
                "maximum_volume_mm3": 1e-6,
                "static": [{"first": "ball", "second": "block", "distance_mm": 9.0, "common_volume_mm3": 0.0},
                           {"first": "ball", "second": "bolt", "distance_mm": 5.0, "common_volume_mm3": 0.0,
                            "culled": True},
                           {"first": "block", "second": "bolt", "distance_mm": 0.0,
                            "common_volume_mm3": 2.0 * 3.141592653589793}],
                "thread_allowances": [{"first": "bolt", "second": "block", "allowance_mm3": 7.0}],
                "geometry": [{"name": n, "path": str(tmp_path / f"{n}.brep")} for n in names]}
        (tmp_path / "plan.json").write_text(json.dumps(plan))
        subprocess.run([str(FREECADCMD), str(SMOKE)], check=True, capture_output=True, timeout=300,
                       env={**os.environ, "CADEX_SMOKE_GEOMETRY_PLAN": str(tmp_path / "plan.json")})
        result = json.loads((tmp_path / "out.json").read_text())
        assert "error" not in result, result
        return result

    collided = run({"ball": [0, 0, -12]})
    assert [(r["first"], r["second"]) for r in collided["failing"]] == [("ball", "block")]
    assert collided["threaded"] == 1
    bolt = next(r for r in collided["pairs"] if r["second"] == "bolt" and r["first"] == "block")
    assert bolt["thread_allowance_mm3"] == 7.0 and bolt["common_volume_mm3"] > 6.0
    # 2 mm deeper is 4π mm³, past the 7 mm³ the thread accounts for.
    driven = run({"bolt": [0, 0, -2]})
    assert [(r["first"], r["second"]) for r in driven["failing"]] == [("block", "bolt")]


@pytest.mark.skipif(FREECADCMD is None, reason="Needs real OCCT")
def test_the_first_frame_agrees_to_the_mjcf_pose_precision_not_float_noise(tmp_path):
    # ADR-584: frame 0 is MuJoCo's pose of an MJCF written to six significant
    # figures, so it sits up to micrometres from the solved pose. The
    # excavator's bucket was 7e-5 mm off, its box gap 3.5e-5 mm short of the
    # published 90.06905449114826 mm, and smoke refused it at a 1e-5 bound.
    subprocess.run([str(FREECADCMD), "-c", (
        "import Part, FreeCAD as App;"
        f"Part.makeBox(10, 10, 10).exportBrep({str(tmp_path / 'block.brep')!r});"
        f"Part.makeCylinder(1, 4, App.Vector(5, 5, 8)).exportBrep({str(tmp_path / 'bolt.brep')!r});"
        f"Part.makeSphere(1, App.Vector(100, 0, 5)).exportBrep({str(tmp_path / 'far.brep')!r});"
        f"Part.makeSphere(1, App.Vector(5, 5, 14)).exportBrep({str(tmp_path / 'near.brep')!r})")],
        check=True, capture_output=True, timeout=300)
    names = ("block", "bolt", "far", "near")
    identity = {"position_mm": [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]}
    static = [
        # The far ball's box is 89 mm from the block's, a culled bound; the
        # near ball is 3 mm from the block shell to shell, 1 mm from the
        # bolt; the bolt shares 2π mm³ with the block.
        {"first": "block", "second": "bolt", "distance_mm": 0.0, "common_volume_mm3": 2.0 * 3.141592653589793},
        {"first": "block", "second": "far", "distance_mm": 89.0, "common_volume_mm3": 0.0, "culled": True},
        {"first": "block", "second": "near", "distance_mm": 3.0, "common_volume_mm3": 0.0},
        {"first": "bolt", "second": "far", "distance_mm": 80.0, "common_volume_mm3": 0.0, "culled": True},
        {"first": "bolt", "second": "near", "distance_mm": 1.0, "common_volume_mm3": 0.0},
        {"first": "far", "second": "near", "distance_mm": 80.0, "common_volume_mm3": 0.0, "culled": True},
    ]

    def run(offset_mm):
        # Every part but the block sits offset_mm off its solved pose in -x
        # and in +z, the way a rounded MJCF position puts it.
        moved = {"position_mm": [-offset_mm, 0, offset_mm], "rotation_xyzw": [0, 0, 0, 1]}
        (tmp_path / "trace.json").write_text(json.dumps([{"time_s": 0.0, "placements": {
            n: identity if n == "block" else moved for n in names}}]))
        plan = {"trace": str(tmp_path / "trace.json"), "out": str(tmp_path / "out.json"),
                "maximum_volume_mm3": 1e-6, "static": static,
                "thread_allowances": [{"first": "block", "second": "bolt", "allowance_mm3": 7.0}],
                "geometry": [{"name": n, "path": str(tmp_path / f"{n}.brep")} for n in names]}
        (tmp_path / "plan.json").write_text(json.dumps(plan))
        subprocess.run([str(FREECADCMD), str(SMOKE)], check=True, capture_output=True, timeout=300,
                       env={**os.environ, "CADEX_SMOKE_GEOMETRY_PLAN": str(tmp_path / "plan.json")})
        return json.loads((tmp_path / "out.json").read_text())

    exact = run(0.0)
    assert "error" not in exact, exact
    assert exact["pass"] is True
    # The far ball's box gap falls 7e-5 mm short of its bound, the near
    # ball's distance moves by 7e-5 mm, and the bolt's 2π mm³ by about
    # 2e-4 mm³ -- each past the old 1e-5, each only the file's rounding.
    rounded = run(7e-5)
    assert "error" not in rounded, rounded
    assert rounded["pass"] is True and rounded["initial_pose_agrees"] is True
    assert abs(rounded["initial_pose_tolerance_mm"] - 0.034641016151377546) < 1e-12
    # A pose 0.1 mm off is not rounding; it is a trace that put a part
    # somewhere else, and still a measurement error.
    wrong = run(0.1)
    assert "initial pose disagrees with published clearance" in wrong["error"], wrong


def test_the_initial_pose_bound_is_the_engines_mjcf_pose_contract():
    # ADR-584: the child cannot import the engine, so it restates the
    # export's pose tolerance; a change on either side must move both.
    import importlib.util
    import re

    spec = importlib.util.spec_from_file_location("smoke_geometry_under_test", SMOKE)
    child = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(child)
    source = (ROOT / "src/Mod/cadex/CadexDynamics.py").read_text()
    engine = float(re.search(r"^MJCF_POSE_TOLERANCE_MM = (\S+)$", source, re.M).group(1))
    assert child.MJCF_POSE_TOLERANCE_MM == engine
    assert child.INITIAL_POSE_TOLERANCE_MM == 2.0 * 3.0 ** 0.5 * engine


@pytest.mark.skipif(FREECADCMD is None, reason="Needs real OCCT")
def test_a_pair_in_simulated_contact_shares_its_contact_depth_and_no_more(tmp_path):
    # ADR-599: a 25 mm ball resting 7.5 um into a plate, as the simulator's
    # soft contact holds it, shares a sliver with it. That is contact, not a
    # collision, while the simulator held the pair within the penetration
    # tolerance; a ball 1 mm in is a collision whatever the contact says.
    subprocess.run([str(FREECADCMD), "-c", (
        "import Part, FreeCAD as App;"
        f"Part.makeBox(160, 160, 10, App.Vector(-80, -80, -10)).exportBrep({str(tmp_path / 'plate.brep')!r});"
        f"Part.makeSphere(12.5, App.Vector(0, 0, 12.5)).exportBrep({str(tmp_path / 'ball.brep')!r})")],
        check=True, capture_output=True, timeout=300)
    identity = {"position_mm": [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]}

    def run(sink_mm, contacts):
        trace = [{"time_s": 0.0, "placements": {"ball": identity, "plate": identity}},
                 {"time_s": 0.1, "placements": {"plate": identity, "ball": {
                     "position_mm": [0, 0, -sink_mm], "rotation_xyzw": [0, 0, 0, 1]}}}]
        (tmp_path / "trace.json").write_text(json.dumps(trace))
        plan = {"trace": str(tmp_path / "trace.json"), "out": str(tmp_path / "out.json"),
                "maximum_volume_mm3": 1e-6, "contact_depth_mm": 0.05, "contacts": contacts,
                "static": [{"first": "ball", "second": "plate", "distance_mm": 0.0,
                            "common_volume_mm3": 0.0}],
                "geometry": [{"name": n, "path": str(tmp_path / f"{n}.brep")} for n in ("ball", "plate")]}
        (tmp_path / "plan.json").write_text(json.dumps(plan))
        subprocess.run([str(FREECADCMD), str(SMOKE)], check=True, capture_output=True, timeout=300,
                       env={**os.environ, "CADEX_SMOKE_GEOMETRY_PLAN": str(tmp_path / "plan.json")})
        result = json.loads((tmp_path / "out.json").read_text())
        assert "error" not in result, result
        return result

    touching = [{"first": "ball", "second": "plate", "depth_mm": 0.0075}]
    resting = run(0.0075, touching)
    assert resting["pass"] is True and resting["in_contact"] == 1
    # Without the simulator's contact the same sliver is a collision...
    assert run(0.0075, [])["pass"] is False
    # ...and so is a ball 1 mm in, or one whose contact passed the tolerance.
    assert run(1.0, touching)["pass"] is False
    assert run(0.0075, [dict(touching[0], depth_mm=0.2)])["pass"] is False
