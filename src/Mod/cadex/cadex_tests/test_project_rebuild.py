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
result = {"plate": plate, "base": base, "top": top, "asm": asm, "diag": diag}
'''

root = Path(tempfile.mkdtemp(prefix="cadex-rebuild-ci-"))
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

    first = cadex_rebuild.rebuild_project(root)
    second = cadex_rebuild.rebuild_project(root)
    report = {
        "ok": True,
        "accepted": accepted,
        "first": first["digest"],
        "second": second["digest"],
        "first_matches_accepted": first["digest_matches_accepted"],
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
