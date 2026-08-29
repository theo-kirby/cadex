# SPDX-FileCopyrightText: 2026 Cadex Authors
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
linked = part.import_part("sensor.cxpart")
bolted = part.cut(linked, part.cylinder(2.0, 40, origin=[5.0, 5.0, -5.0]))
tall = part.measurement(plate, kind="extent", axis="z", label="plate thickness")
across = part.measurement(
    plate,
    kind="distance",
    start={"geometry_type": "Plane", "normal": [0.0, -1.0, 0.0]},
    end={"geometry_type": "Plane", "normal": [0.0, 1.0, 0.0]},
)
wide = part.measurement(
    bolted, kind="diameter", at={"geometry_type": "Cylinder", "radius": 2.0}
)
result = {"plate": plate, "base": base, "top": top, "asm": asm, "diag": diag,
          "hull": hull, "lite": lite, "scan": scan, "placed": placed,
          "scan_solid": scan_solid, "carved": carved, "linked": linked,
          "bolted": bolted, "tall": tall, "across": across, "wide": wide}
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

# A linked part (ADR-138), in the store the same way the link_part op puts
# one there. Written here from a shape rather than pulled from a second
# project because what this CI is about is the *rebuild*: an imported BREP
# has to reproduce byte-for-byte across two runs of the same script, exactly
# as an imported mesh does, or a project holding one drifts on every open.
import hashlib

import Part

from CadexLinkedPart import LINKED_PART_SCHEMA, encode_linked_part

_seed = Part.makeBox(18.0, 12.0, 9.0)
_brep = root / "seed.brep"
_seed.exportBrep(str(_brep))
_bytes = _brep.read_bytes()
_brep.unlink()
(root / "assets" / "sensor.cxpart").write_bytes(
    encode_linked_part(
        {
            "schema": LINKED_PART_SCHEMA,
            "source": {
                "project_root": str(root),
                "project_title": "seed",
                "output": "sensor",
                "revision": "seedrev",
                "digest": "seeddigest",
                "output_type": "solid",
            },
            "params": {},
            "param_specs": [],
            "script": 'result = {"sensor": part.box(18, 12, 9)}\n',
            "shape_sha256": hashlib.sha256(_bytes).hexdigest(),
            "brep_bytes": len(_bytes),
        },
        _bytes,
    )
)
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
            "measurement": item.get("measurement"),
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
    # ...and the same two statements for a linked part (ADR-138). The digest
    # assertions above are what actually matter here: an imported container
    # must re-export byte-identically on every rebuild, or a project holding
    # one drifts every time it is opened.
    assert outputs["linked"]["artifact_kind"] == "brep", report
    assert outputs["linked"]["domain"] == "part", report
    assert outputs["linked"]["shape_type"] == "Solid", report
    assert outputs["linked"]["volume_mm3"] == pytest.approx(18.0 * 12.0 * 9.0), report
    assert 0.0 < outputs["bolted"]["volume_mm3"] < outputs["linked"]["volume_mm3"], report
    # Measurements (ADR-139). The digest assertions above already say the
    # important thing -- a measurement is declared, so it enters the digest
    # through its own definition, and a project carrying three of them still
    # rebuilds to the same digest twice. These say the numbers are the ones
    # a person would get with a ruler.
    tall = outputs["tall"]["measurement"]
    assert outputs["tall"]["artifact_kind"] is None, report
    assert tall["kind"] == "extent" and tall["subject"] == "plate", report
    assert tall["value_mm"] == pytest.approx(4.0), report
    assert tall["text"] == "4.00 mm", report
    assert tall["label"] == "plate thickness", report
    # The anchors run down the centre of the part, not off a corner.
    assert tall["anchors_mm"][0] == pytest.approx([15.0, 9.0, 0.0]), report
    assert tall["anchors_mm"][1] == pytest.approx([15.0, 9.0, 4.0]), report

    across = outputs["across"]["measurement"]
    assert across["kind"] == "distance" and across["subject"] == "plate", report
    assert across["value_mm"] == pytest.approx(18.0), report
    assert across["label"] == "", report

    # A diameter publishes the circle, never a pair of points: which diameter
    # reads widest is the viewport's question and it changes as you orbit.
    wide = outputs["wide"]["measurement"]
    assert wide["kind"] == "diameter" and wide["subject"] == "bolted", report
    assert wide["value_mm"] == pytest.approx(4.0), report
    assert wide["radius_mm"] == pytest.approx(2.0), report
    assert wide["anchors_mm"] is None, report
    assert wide["text"] == "Ø4.00 mm", report
    # The centre sits on the bore's axis, at the middle of the measured face.
    assert wide["center_mm"][0] == pytest.approx(5.0), report
    assert wide["center_mm"][1] == pytest.approx(5.0), report
    assert wide["normal"] == pytest.approx([0.0, 0.0, 1.0]), report
