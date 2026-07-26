# SPDX-License-Identifier: LGPL-2.1-or-later

"""Digest CI: delete the document, rebuild from THE script, digests match.

Phase 2 exit criterion (docs/ROADMAP.md): create -> accept -> delete document
-> headless rebuild -> digest matches the accepted digest, and a second
rebuild reproduces the first (rebuild-vs-accepted AND rebuild-vs-rebuild).
Skipped when no FreeCADCmd binary is available (pure-python CI).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
_FREECADCMD_CANDIDATES = (
    REPO_ROOT / ".pixi" / "envs" / "default" / "bin" / "FreeCADCmd",
    REPO_ROOT / "build" / "release" / "bin" / "FreeCADCmd",
)
FREECADCMD = next(
    (candidate for candidate in _FREECADCMD_CANDIDATES if candidate.is_file()), None
)

_DRIVER = r"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

import FreeCAD as App

cadex_root = Path(sys.argv[-1])
sys.path.insert(0, str(cadex_root))

from CadexProject import CadexProjectScriptStore
from CadexScriptedDomainPublication import publish_project_candidate
from CadexScriptedRuntime import (
    accept_project_candidate,
    capture_project_state,
    execute_candidate,
    prepare_project_candidate,
    validate_project_result,
)
import cadex_rebuild

SCRIPT = '''
p = params(width=num(30, unit="mm", min=10, max=90, step=1))
plate = part.box(p.width, 18, 4)
base = assembly.component(plate, grounded=True)
top = assembly.component(plate, placement=[0, 0, 4])
asm = assembly.assembly([base, top])
diag = assembly.solve(asm)
hull = mesh.union(
    mesh.from_shape(plate, linear_deflection=0.4),
    mesh.from_shape(part.sphere(6.0, center=[0.0, 9.0, 4.0]), linear_deflection=0.4),
)
lite = mesh.decimate(hull, tolerance=0.5, reduction=0.5)
scan = mesh.import_file("tetra.stl")
placed = mesh.transform(
    scan,
    translation=[12.0, 0.0, 0.0],
    rotation_axis=[0.0, 0.0, 1.0],
    rotation_degrees=45.0,
    scale=1.5,
    pivot=[2.0, 2.0, 0.0],
)
scan_solid = part.shape_from_mesh(scan)
carved = part.cut(plate, scan_solid)
result = {"plate": plate, "base": base, "top": top, "asm": asm, "diag": diag,
          "hull": hull, "lite": lite, "scan": scan, "placed": placed,
          "scan_solid": scan_solid, "carved": carved}
'''

TETRA_STL = '''solid tetra
facet normal 0 0 -1
 outer loop
  vertex 0 0 0
  vertex 4 0 0
  vertex 0 4 0
 endloop
endfacet
facet normal 0 -1 0
 outer loop
  vertex 0 0 0
  vertex 0 0 4
  vertex 4 0 0
 endloop
endfacet
facet normal -1 0 0
 outer loop
  vertex 0 0 0
  vertex 0 4 0
  vertex 0 0 4
 endloop
endfacet
facet normal 1 1 1
 outer loop
  vertex 4 0 0
  vertex 0 0 4
  vertex 0 4 0
 endloop
endfacet
endsolid tetra
'''

root = Path(tempfile.mkdtemp(prefix="cadex-rebuild-ci-"))
(root / "assets").mkdir(parents=True)
(root / "assets" / "tetra.stl").write_text(TETRA_STL, encoding="utf-8")
report = {}
try:
    # create + accept in a live document
    document = App.newDocument("RebuildSeed")
    service = cadex_rebuild._RebuildService(root, document)
    captured = capture_project_state(
        service,
        "xscript.project.write_script",
        {"source": SCRIPT, "expected_revision": ""},
    )
    prepared = prepare_project_candidate(captured)
    execution = execute_candidate(prepared, cancellation_check=None)
    assert execution.get("ok") is True, execution
    validated = validate_project_result(prepared, execution)
    publication = publish_project_candidate(service, prepared, validated)
    accept_project_candidate(prepared, publication, validated)
    accepted = str(CadexProjectScriptStore(root).read_state()["accepted_digest"])

    # delete the document entirely; the script store is the only truth left
    App.closeDocument(document.Name)

    # part.shape_from_mesh must land as real BREP the part kernel can consume,
    # not merely as an accepted output (ADR-043).
    accepted_outputs = {
        item["name"]: {
            "artifact_kind": item.get("artifact_kind"),
            "domain": item.get("domain"),
            "shape_type": (item.get("facts") or {}).get("shape_type"),
            "volume_mm3": (item.get("facts") or {}).get("volume_mm3"),
        }
        for item in json.loads(
            (Path(prepared["staging"]) / "result.json").read_text(encoding="utf-8")
        )["outputs"]
    }

    first = cadex_rebuild.rebuild_project(root)
    second = cadex_rebuild.rebuild_project(root)
    report = {
        "ok": True,
        "accepted": accepted,
        "first": first["digest"],
        "second": second["digest"],
        "first_matches_accepted": first["digest_matches_accepted"],
        "outputs": accepted_outputs,
    }
finally:
    shutil.rmtree(root, ignore_errors=True)

print("REBUILD-CI " + json.dumps(report, sort_keys=True))
"""


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for the digest CI."
)
def test_rebuild_digest_matches_accepted_and_is_reproducible(tmp_path) -> None:
    driver = tmp_path / "rebuild_ci_driver.py"
    driver.write_text(_DRIVER, encoding="utf-8")
    cadex_root = Path(__file__).resolve().parent.parent
    command = [
        str(FREECADCMD),
        "-c",
        (
            "import sys; sys.argv = ['driver', "
            f"{str(cadex_root)!r}]; "
            f"exec(open({str(driver)!r}).read())"
        ),
    ]
    completed = subprocess.run(
        command,
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
            if line.startswith("REBUILD-CI ")
        ),
        None,
    )
    assert marker, (
        f"digest CI driver produced no report; exit={completed.returncode}\n"
        f"stdout:\n{completed.stdout[-4000:]}\nstderr:\n{completed.stderr[-4000:]}"
    )
    report = json.loads(marker.removeprefix("REBUILD-CI "))
    assert report.get("ok") is True, report
    assert report["first"] == report["accepted"], report
    assert report["second"] == report["first"], report
    assert report["first_matches_accepted"] is True, report
    # The digest assertions above cover makeShapeFromMesh's reproducibility
    # for free; these say the ingested mesh is genuinely BREP, and that the
    # part kernel could cut a modelled solid with it (ADR-043).
    outputs = report["outputs"]
    assert outputs["scan_solid"]["artifact_kind"] == "brep", report
    assert outputs["scan_solid"]["domain"] == "part", report
    assert outputs["scan_solid"]["shape_type"] == "Solid", report
    assert outputs["carved"]["artifact_kind"] == "brep", report
    assert 0.0 < outputs["carved"]["volume_mm3"] < outputs["plate"]["volume_mm3"], report
