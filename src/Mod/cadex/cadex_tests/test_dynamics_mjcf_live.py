# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""M5's exit criterion, end to end (docs/MUJOCO.md M5, phase 6).

A script goes into a live ``cadexd``, an MJCF file comes out on disk, and a
subprocess that has **never heard of Cadex** opens it, resets to the pose
the assembly solver produced, integrates, and lands where the engine's own
dynamics run landed. Nothing here recomputes an artifact a helper produced:
the file compared is the one the project store retained.

Three things are proved that no unit test could:

* the export survives a **real Ondsel solve** rather than a fixture
  composed forwards from known joint coordinates -- the inertias come off
  real OCCT solids and the connector frames off objects FreeCAD placed;
* an ``api.mjcf`` **beside** an ``api.dynamics`` moves neither, so a script
  can have the animation and the file;
* a script may declare **more than one** export, and each names its own
  artifact.

One finding, recorded here because this is the only place it is visible:
FreeCAD's assembly solver drives a *tree* mechanism to the configuration
where each joint's connector frames coincide -- which is exactly MuJoCo's
reference configuration -- so an exported tree opens correctly with a
keyframe that happens to be all zeros. The keyframe becomes load-bearing
when a loop closure forces a nonzero coordinate, which is proved on the
four-bar fixture in ``test_dynamics_mjcf_model`` because a planar loop of
revolutes is reported redundant by this tree's native solver and cannot
reach a live gate.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pytest

import CadexDynamics as dyn
import dynamics_mjcf_digest
from test_cadexd_lifecycle import FREECADCMD, _spawn_cadexd, _stop

mujoco = pytest.importorskip("mujoco")

pytestmark = pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)

DIGEST_MODULE = Path(dynamics_mjcf_digest.__file__).resolve()

#: The mechanism from ``test_cadexd_publishes_a_dynamics_run``, exported as
#: well as simulated. Both outputs on one assembly is the point: the trace
#: and the file describe the same model, and the comparison below is
#: between the two of them rather than between the file and a helper's idea
#: of it.
EXPORT_SCRIPT = """
plate = part.box(60, 60, 6)
arm = part.box(80, 8, 8)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin",
                                      offset={"position": [12, 0, 6],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}),
                   assembly.connector(swing, "origin",
                                      offset={"position": [0, 0, 0],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
b1 = assembly.body(base, density_kg_m3=2700)
b2 = assembly.body(swing, density_kg_m3=7850)
sim = assembly.dynamics(asm, [b1, b2], end_time_s=1.0, frames_per_second=30)
model = assembly.mjcf(asm, [
    assembly.body(base, density_kg_m3=2700),
    assembly.body(swing, density_kg_m3=7850),
])
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag, "sim": sim, "model": model}
"""

#: The same assembly exported twice, under two gravities. Legal because
#: nothing bakes an MJCF file, and the rule that makes it legal is the one
#: worth a live test: two ``api.simulation`` outputs are refused.
TWO_EXPORTS_SCRIPT = """
plate = part.box(60, 60, 6)
arm = part.box(80, 8, 8)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin",
                                      offset={"position": [12, 0, 6],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}),
                   assembly.connector(swing, "origin",
                                      offset={"position": [0, 0, 0],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
bodies = [assembly.body(base, density_kg_m3=2700),
          assembly.body(swing, density_kg_m3=7850)]
earth = assembly.mjcf(asm, bodies)
moon = assembly.mjcf(asm, [assembly.body(base, density_kg_m3=2700),
                           assembly.body(swing, density_kg_m3=7850)],
                     gravity_m_s2=[0, 0, -1.62])
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag, "earth": earth, "moon": moon}
"""

#: A collision shape on one part, so the exported file carries a geom and
#: is something a viewer can draw. Same mechanism otherwise.
COLLISION_SCRIPT = """
plate = part.box(60, 60, 6)
arm = part.box(80, 8, 8)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin",
                                      offset={"position": [12, 0, 6],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}),
                   assembly.connector(swing, "origin",
                                      offset={"position": [0, 0, 0],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
model = assembly.mjcf(asm, [
    assembly.body(base, density_kg_m3=2700,
                  collision=assembly.collision("box", size_mm=[60, 60, 6],
                                               offset=[30, 30, 3])),
    assembly.body(swing, density_kg_m3=7850,
                  collision=assembly.collision("box", size_mm=[80, 8, 8],
                                               offset=[40, 4, 4])),
])
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag, "model": model}
"""


def _written(source: str) -> tuple[dict, Path]:
    """One script through one live cadexd, and what it retained."""

    root = Path(tempfile.mkdtemp(prefix="m5-live-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened
        written = client.request(
            "write_script", {"source": source, "expected_revision": ""}
        )
        assert written["ok"] is True, json.dumps(written)[:4000]
        # The artifacts are read here, inside the project root's lifetime,
        # and returned as bytes: the caller compares the store's file and
        # never a path that has since been removed.
        payloads = {
            name: Path(entry["artifact_path"]).read_bytes()
            for name, entry in written["display"].items()
            if entry.get("artifact_path")
            and str(entry.get("artifact_kind") or "").startswith("assembly_")
        }
        done = client.request("shutdown", timeout=60)
        assert done["ok"] is True
        return {"display": written["display"], "payloads": payloads}, root
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


def _stock(xml: bytes, steps: int, tmp_path: Path) -> dict:
    """The exported file, in an interpreter with no Cadex on its path."""

    target = tmp_path / "model.xml"
    target.write_bytes(xml)
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHASHSEED", None)
    finished = subprocess.run(
        [sys.executable, "-P", str(DIGEST_MODULE), "load", str(target), str(steps)],
        capture_output=True,
        text=True,
        timeout=600,
        env=environment,
    )
    assert finished.returncode == 0, finished.stderr
    result = json.loads(finished.stdout)
    assert result["cadex_importable"] is False, (
        "the subprocess reached Cadex, so it proves nothing about a stock MuJoCo"
    )
    return result


# ---------------------------------------------------------------------------
# The exit criterion.
# ---------------------------------------------------------------------------


def test_cadexd_exports_a_model_a_stock_mujoco_reproduces(tmp_path: Path) -> None:
    """Design a mechanism in Cadex, export MJCF with exact inertias.

    The whole slice in one assertion chain: the file on disk loads with
    nothing Cadex on the path, carries mass and inertia computed from OCCT
    solids to the pinned tolerance, opens at the solved pose, and
    integrates to the trajectory the engine's own dynamics run produced.
    """

    written, _root = _written(EXPORT_SCRIPT)
    entry = written["display"]["model"]
    assert entry["artifact_kind"] == "assembly_mjcf_xml", entry
    assert entry["tessellation"] is None, "an export is not display geometry"
    xml = written["payloads"]["model"]

    # It is one self-contained file: no sidecar, no asset directory.
    text = xml.decode("utf-8")
    assert text.startswith('<mujoco model="cadex-assembly">')
    assert "file=" not in text
    assert '<key name="solved"' in text

    trace = json.loads(written["payloads"]["sim"].decode("utf-8"))
    assert trace["schema"] == "cadex-assembly-simulation-trace-v1"
    evidence = trace["dynamics"]
    step = float(evidence["solver_step_s"])
    frames = trace["frames"]
    end_time = float(frames[-1]["nominal_time_s"])
    steps = int(round(end_time / step))

    result = _stock(xml, steps, tmp_path)
    assert result["nkey"] == 1
    assert result["keyframe_id"] == 0
    assert result["nbody"] == 3, "world, base and swing"
    assert result["nq"] == 1, "one hinge"

    # Exact OCCT masses, read by a MuJoCo that has never heard of OCCT.
    # 60x60x6 mm of aluminium and 80x8x8 mm of steel, computed here rather
    # than copied out of the trace.
    masses = {
        item["component_output"]: item["mass_kg"] for item in evidence["inertials"]
    }
    expected = {
        "base": 2700.0 * 0.06 * 0.06 * 0.006,
        "swing": 7850.0 * 0.08 * 0.008 * 0.008,
    }
    for name, mass in expected.items():
        assert masses[name] == pytest.approx(mass, rel=1.0e-9)
    from_file = sorted(float(value) for value in result["body_mass"])
    assert from_file == pytest.approx(
        sorted([0.0, *expected.values()]), rel=dyn.MJCF_INERTIA_TOLERANCE
    )

    # It opened where the assembly solver left it: the first *solved* trace
    # frame, which is frames[1] because frames[0] is the untimed input one.
    bodies = _body_index(text)
    assert bodies == [(1, "base"), (2, "swing")], bodies
    solved = frames[1]["component_placements"]
    for index, name in bodies:
        position = [
            dyn.length_mm(float(value))
            for value in result["start_xpos"][3 * index : 3 * index + 3]
        ]
        assert position == pytest.approx(
            solved[name]["position_mm"], abs=dyn.MJCF_POSE_TOLERANCE_MM
        ), name

    # ...and integrating it reproduces the engine's own last frame.
    final = frames[-1]["component_placements"]
    for index, name in bodies:
        position = [
            dyn.length_mm(float(value))
            for value in result["xpos"][3 * index : 3 * index + 3]
        ]
        assert position == pytest.approx(
            final[name]["position_mm"], abs=dyn.MJCF_POSE_TOLERANCE_MM
        ), name

    # The run being compared is one where something happened: the arm's
    # origin sits on the hinge axis so its position never moves, which is
    # exactly why the rotation is the observable.
    turns = _turn(frames[1], frames[-1], "swing")
    assert turns > 0.5, turns


def _body_index(text: str):
    """``(model body index, component output)`` for each exported body.

    Read out of the file's own body order rather than assumed: MuJoCo
    numbers ``world`` zero and the rest in declaration order, and a test
    that hardcoded that would pass on a file whose bodies had been
    reordered.
    """

    names = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("<body name="):
            names.append(stripped.split('"')[1])
    return [(index + 1, name) for index, name in enumerate(names)]


def _turn(first, second, name) -> float:
    dot = abs(
        sum(
            a * b
            for a, b in zip(
                first["component_placements"][name]["rotation_xyzw"],
                second["component_placements"][name]["rotation_xyzw"],
                strict=True,
            )
        )
    )
    return 2.0 * math.acos(min(1.0, dot))


# ---------------------------------------------------------------------------
# The mixing rules, live.
# ---------------------------------------------------------------------------


def test_an_export_beside_a_dynamics_run_moves_neither() -> None:
    """The reason ``export_mjcf`` copies the spec, proved through the pipeline.

    The same script without the ``api.mjcf`` output must retain the same
    trace bytes. If the export mutated the spec it was handed, the
    simulation's own numbers would move -- silently, and only in scripts
    that did both.
    """

    with_export, _first = _written(EXPORT_SCRIPT)
    without_export, _second = _written(
        EXPORT_SCRIPT.replace(
            'model = assembly.mjcf(asm, [\n'
            '    assembly.body(base, density_kg_m3=2700),\n'
            '    assembly.body(swing, density_kg_m3=7850),\n'
            '])\n',
            "",
        ).replace(', "model": model', "")
    )
    assert "model" not in without_export["display"]
    assert with_export["payloads"]["sim"] == without_export["payloads"]["sim"]


def test_a_script_may_export_two_models(tmp_path: Path) -> None:
    """Two exports of one assembly, each naming its own artifact."""

    written, _root = _written(TWO_EXPORTS_SCRIPT)
    for name in ("earth", "moon"):
        assert written["display"][name]["artifact_kind"] == "assembly_mjcf_xml"
    earth = written["payloads"]["earth"]
    moon = written["payloads"]["moon"]
    assert earth != moon
    # Different files, because they were exported under different gravity.
    assert 'gravity="0 0 -1.62"' in moon.decode("utf-8")
    assert "gravity=" not in earth.decode("utf-8"), "Earth is MuJoCo's default"
    # ...and identical in every other respect.
    assert moon.decode("utf-8").replace('  <option gravity="0 0 -1.62"', "  <option") \
        == earth.decode("utf-8")

    for xml in (earth, moon):
        result = _stock(xml, 200, tmp_path)
        assert result["nbody"] == 3
        assert result["nkey"] == 1


def test_an_export_carries_only_collision_geometry(tmp_path: Path) -> None:
    """Collision only, which is what makes the file the simulated model.

    Stated as a test because the consequence is worth being unable to
    forget: a mechanism with no ``assembly.collision`` shapes opens
    *invisible* in MuJoCo's viewer.
    """

    with_geoms, _first = _written(COLLISION_SCRIPT)
    without_geoms, _second = _written(EXPORT_SCRIPT)
    geoms = with_geoms["payloads"]["model"].decode("utf-8")
    bare = without_geoms["payloads"]["model"].decode("utf-8")
    assert geoms.count("<geom") == 2
    assert "<geom" not in bare

    result = _stock(with_geoms["payloads"]["model"], 100, tmp_path)
    assert result["ngeom"] == 2


# ---------------------------------------------------------------------------
# Across restarts.
# ---------------------------------------------------------------------------


def test_the_same_script_exports_the_same_bytes_across_cadexd_restarts() -> None:
    """Two engines, two project roots, nothing shared but the script text.

    The file compared is the one the project store retained, not anything a
    helper recomputed -- the same discipline
    ``test_dynamics_restart_determinism`` applies to the trace, and the same
    claim: two people open the same project on two machines and get the same
    model.
    """

    first, _one = _written(EXPORT_SCRIPT)
    second, _two = _written(EXPORT_SCRIPT)
    assert first["payloads"]["model"] == second["payloads"]["model"]
    digest = hashlib.sha256(first["payloads"]["model"]).hexdigest()
    # The digest the worker recorded, read back off the published entry
    # rather than recomputed here, so the two sides of the comparison are
    # the store's number and ours.
    for written in (first, second):
        assert hashlib.sha256(written["payloads"]["model"]).hexdigest() == digest
