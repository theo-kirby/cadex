# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A refused project publish must leave the live document as accepted.

The ot10 biped (``ot10-biped-2``) returned its servo actuators in
``result``. Validation accepted them, and the assembly pass raised
``No native publisher exists for output type 'actuator'`` after it had
created the assembly, its components and its joints. The live document runs
with ``UndoMode 0``, where ``abortTransaction`` restores nothing, so those
objects stayed, the refusal claimed ``accepted_live_state_preserved: true``,
and every later publish was refused as ``PUBLICATION_UNTAGGED_OBJECT``
(ADR-434, amending ADR-429).

Two halves: a publish that raises mid assembly pass rolls back completely,
created objects and in-place edits alike, and the next publish succeeds; and
an argument value such as an actuator is refused at validation with the fix
named, before the document is touched. These run the real kernel, because
the stubbed FreeCAD in ``conftest.py`` has no transactions.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile

import pytest

_LIFECYCLE = __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"])

_PROBE = r'''
import json, sys, tempfile, traceback
from pathlib import Path
sys.path.insert(0, %(tests)r)
sys.path.insert(0, %(root)r)
import FreeCAD as App
import project_xscript_api_integration as lifecycle
from CadexProject import CadexProjectScriptStore
from CadexScriptedDomainPublication import publish_project_candidate
from CadexScriptedRuntime import accept_project_candidate

PARTS = """
plate = part.box(60, 60, 6)
result = {"plate": plate}
"""

def robot(arm="80, 8, 8", extra=""):
    return f"""
plate = part.box(60, 60, 6)
arm = part.box({arm})
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
    assembly.connector(base, "origin", offset={{"position": [12, 0, 6], "axis": [1, 0, 0], "angle_degrees": 90}}),
    assembly.connector(swing, "origin", offset={{"position": [0, 0, 0], "axis": [1, 0, 0], "angle_degrees": 90}}))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
motor = assembly.actuator(j, kind="motor", control_nmm="0", torque_limit_nmm=2000)
result = {{"plate": plate, "arm": arm, "base": base, "swing": swing, "j": j, "asm": asm, "diag": diag{extra}}}
"""

def snapshot(doc):
    return {
        "objects": sorted(o.Name for o in doc.Objects),
        "volumes": {
            o.Name: round(float(o.Shape.Volume), 3)
            for o in doc.Objects
            if o.TypeId == "Part::Feature" and not o.Shape.isNull()
        },
        "undo_mode": int(doc.UndoMode),
        "undo_count": int(doc.UndoCount),
    }

report = {}
root = Path(tempfile.mkdtemp(prefix="cadex-rollback-"))
doc = App.newDocument("RefusedRollback")
service = lifecycle._Service(root)
store = CadexProjectScriptStore(root)

def write(source):
    working = (store.read_state() or {}).get("working_revision", "")
    return lifecycle._run_lifecycle(
        service, "xscript.project.write_script",
        {"source": source, "expected_revision": working},
    )

def publish(source, poison=False):
    prepared, validated = write(source)
    if poison:
        # Stands in for any failure after the assembly pass has created
        # objects: an output with no publisher, last in the pass, exactly
        # where the biped's actuators sat before validation refused them.
        (diag,) = [o for o in validated["outputs"] if o.get("type") == "solver_diagnostics"]
        ghost = dict(diag)
        ghost.update(name="ghost", type="actuator")
        validated["outputs"].append(ghost)
    try:
        publication = publish_project_candidate(service, prepared, validated)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    accept_project_candidate(prepared, publication, validated)
    return {"ok": True, "outputs": sorted(publication["outputs"])}

try:
    report["parts"] = publish(PARTS)
    report["parts_state"] = snapshot(doc)

    # The biped's case: the first assembly publish raises mid pass.
    report["first_refused"] = publish(robot(), poison=True)
    report["first_refused_state"] = snapshot(doc)
    report["first"] = publish(robot())
    report["first_state"] = snapshot(doc)

    # An edit in place that is refused must restore the edited shape too.
    report["edit_refused"] = publish(robot("70, 8, 8"), poison=True)
    report["edit_refused_state"] = snapshot(doc)
    report["edit"] = publish(robot("70, 8, 8"))
    report["edit_state"] = snapshot(doc)

    # The real script shape: the actuator returned in `result`.
    before = snapshot(doc)
    try:
        write(robot("70, 8, 8", ', "motor": motor'))
        report["actuator"] = {"raised": False}
    except Exception as exc:
        payload = dict(getattr(exc, "payload", None) or {})
        report["actuator"] = {
            "raised": True,
            "code": str(payload.get("failure_code") or ""),
            "error": str(exc)[:2000],
        }
    report["actuator_unchanged"] = snapshot(doc) == before
    report["after"] = publish(robot("75, 8, 8"))
except Exception:
    report["crash"] = traceback.format_exc()
finally:
    App.closeDocument(doc.Name)
open(%(out)r, "w").write(json.dumps(report))
'''


def _kernel_report() -> dict:
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="cadex-rollback-probe-"))
    out = scratch / "report.json"
    probe = scratch / "probe.py"
    probe.write_text(
        _PROBE
        % {
            "root": str(_LIFECYCLE.CADEX_ROOT),
            "tests": str(pathlib.Path(__file__).resolve().parent),
            "out": str(out),
        }
    )
    finished = subprocess.run(
        [str(_LIFECYCLE.FREECADCMD), "-c", f"exec(open({str(probe)!r}).read())"],
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert out.is_file(), finished.stdout[-4000:] + finished.stderr[-4000:]
    report = json.loads(out.read_text())
    assert "crash" not in report, report["crash"]
    return report


_REPORT: dict = {}


def _report() -> dict:
    if not _REPORT:
        _REPORT.update(_kernel_report())
    return _REPORT


needs_kernel = pytest.mark.skipif(
    _LIFECYCLE.FREECADCMD is None,
    reason="No FreeCADCmd binary available to publish into a live document.",
)


@needs_kernel
def test_a_publish_refused_mid_assembly_pass_leaves_the_document_as_accepted() -> None:
    report = _report()
    assert report["parts"]["ok"], report["parts"]
    refused = report["first_refused"]
    assert not refused["ok"]
    assert "No native publisher exists for output type 'actuator'" in refused["error"]
    assert report["first_refused_state"] == report["parts_state"]


@needs_kernel
def test_the_publish_after_a_refusal_succeeds() -> None:
    report = _report()
    assert report["first"]["ok"], report["first"]
    assert "asm" in report["first"]["outputs"]
    # Undo is on only inside the publish, and keeps no history after it.
    assert report["first_state"]["undo_mode"] == 0
    assert report["first_state"]["undo_count"] == 0


@needs_kernel
def test_a_refused_edit_restores_the_edited_shape() -> None:
    report = _report()
    assert not report["edit_refused"]["ok"]
    assert report["edit_refused_state"] == report["first_state"]
    assert report["edit"]["ok"], report["edit"]
    assert report["edit_state"]["objects"] == report["first_state"]["objects"]
    assert report["edit_state"]["volumes"] != report["first_state"]["volumes"]


@needs_kernel
def test_an_actuator_in_result_is_refused_at_validation_with_the_fix() -> None:
    report = _report()
    refusal = report["actuator"]
    assert refusal["raised"], refusal
    assert refusal["code"] == "PROJECT_OUTPUT_UNPUBLISHABLE", refusal
    assert "Remove 'motor' from `result`" in refusal["error"]
    assert "actuators=[...]" in refusal["error"]
    assert report["actuator_unchanged"]
    assert report["after"]["ok"], report["after"]


def test_validation_refuses_an_argument_value_without_a_kernel() -> None:
    """The same refusal at the unit that makes it, so a bare checkout runs it."""
    from CadexScriptedRuntime import DomainRuntimeFailure, validate_project_result

    execution = {
        "schema": __import__("CadexScriptedRuntime").PROJECT_WORKER_SCHEMA,
        "outputs": [{"name": "grip", "domain": "assembly", "type": "observation"}],
        "digest": "0" * 64,
    }
    with pytest.raises(DomainRuntimeFailure) as caught:
        validate_project_result({"tool_name": "xscript.project.write_script"}, execution)
    payload = dict(caught.value.payload)
    assert payload.get("failure_code") == "PROJECT_OUTPUT_UNPUBLISHABLE", payload
    assert "Remove 'grip' from `result`" in str(caught.value)
