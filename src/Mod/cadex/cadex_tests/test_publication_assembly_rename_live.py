# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Renaming a project's assembly output must not wedge the live document.

Hexapod attempt 8 (ot10) renamed its assembly output after a run of
CPU-limit kills, and from then on every write — even a one-box script — was
refused with ``PUBLICATION_UNTAGGED_OBJECT: ['Joints', 'Joints001']``. The
cause was measured under FreeCADCmd: a rename published as retire-plus-
create, the new assembly got a fresh ``Joints001``, and the old assembly was
removed alone, leaving its untagged ``Joints`` group behind with the joints
that had been updated in place still inside it (ADR-429).

These run the real kernel, because the stubbed FreeCAD in ``conftest.py``
has no group semantics and would have passed the defect.
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

def script(assembly_key, body="", extra=""):
    return f"""
plate = part.box(60, 60, 6)
arm = part.box(80, 8, 8)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
    assembly.connector(base, "origin", offset={{"position": [12, 0, 6], "axis": [1, 0, 0], "angle_degrees": 90}}),
    assembly.connector(swing, "origin", offset={{"position": [0, 0, 0], "axis": [1, 0, 0], "angle_degrees": 90}}))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
{body}
result = {{"plate": plate, "arm": arm, "base": base, "swing": swing, "j": j, "{assembly_key}": asm, "diag": diag{extra}}}
"""

#: A pass heavy enough to outrun a one-second CPU budget, standing in for
#: the 300 CPU-second kills that preceded the wedge. It is published as an
#: output because xscript builds only what ``result`` reaches.
HEAVY = """
spikes = part.fuse([
    part.sphere(3.0 + k * 0.001, center=(k * 0.37, (k %% 7) * 0.9, (k %% 5) * 0.8))
    for k in range(1500)
])
"""

class Budgeted(lifecycle._Service):
    budgets = None
    def scripted_budgets(self):
        return self.budgets

def snapshot(doc):
    groups = {}
    for obj in doc.Objects:
        if obj.TypeId == "Assembly::AssemblyObject":
            groups[obj.Name] = {
                "output": str(getattr(obj, "CadexXScriptOutputName", "") or ""),
                "joint_groups": [
                    child.Name for child in obj.Group
                    if child.TypeId == "Assembly::JointGroup"
                ],
                "joints": sorted(
                    member.Name
                    for child in obj.Group
                    if child.TypeId == "Assembly::JointGroup"
                    for member in child.Group
                ),
            }
    return {
        "joint_groups": sorted(o.Name for o in doc.Objects if o.TypeId == "Assembly::JointGroup"),
        "assemblies": groups,
        "objects": sorted(o.Name for o in doc.Objects),
    }

report = {}
root = Path(tempfile.mkdtemp(prefix="cadex-rename-"))
doc = App.newDocument("RenameWedge")
service = Budgeted(root)
store = CadexProjectScriptStore(root)

def write(source):
    working = (store.read_state() or {}).get("working_revision", "")
    return lifecycle._run_lifecycle(
        service, "xscript.project.write_script",
        {"source": source, "expected_revision": working},
    )

def publish(source):
    prepared, validated = write(source)
    try:
        publication = publish_project_candidate(service, prepared, validated)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    accept_project_candidate(prepared, publication, validated)
    return {"ok": True, "outputs": sorted(publication["outputs"])}

try:
    report["first"] = publish(script("probe"))
    report["first_state"] = snapshot(doc)

    # A CPU-limited pass: the worker is killed and nothing reaches the
    # document, so what the next publish sees is the accepted state.
    service.budgets = {"timeout_seconds": 1.0, "memory_limit_mb": 4096}
    try:
        write(script("probe", HEAVY, ', "spikes": spikes'))
        report["killed"] = {"raised": False}
    except AssertionError as exc:
        report["killed"] = {"raised": True, "error": str(exc)[:400]}
    service.budgets = None
    report["killed_state"] = snapshot(doc)

    report["renamed"] = publish(script("robot"))
    report["renamed_state"] = snapshot(doc)

    # A rename refused by the ownership lint is retried once the cause goes.
    rogue = doc.addObject("Part::Feature", "Rogue")
    report["refused"] = publish(script("hexapod"))
    doc.removeObject("Rogue")
    report["retried"] = publish(script("hexapod"))
    report["retried_state"] = snapshot(doc)

    # ...and an ordinary edit after all of it still publishes.
    report["after"] = publish(script("hexapod").replace("80, 8, 8", "70, 8, 8"))
except Exception:
    report["crash"] = traceback.format_exc()
finally:
    App.closeDocument(doc.Name)
open(%(out)r, "w").write(json.dumps(report))
'''


def _kernel_report() -> dict:
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="cadex-rename-probe-"))
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
def test_a_cpu_killed_pass_leaves_the_document_as_accepted() -> None:
    report = _report()
    assert report["first"]["ok"], report["first"]
    assert report["killed"]["raised"], report["killed"]
    assert "DOMAIN_CPU_LIMIT_EXCEEDED" in report["killed"]["error"]
    assert report["killed_state"] == report["first_state"]


@needs_kernel
def test_renaming_the_assembly_output_publishes_and_keeps_one_joint_group() -> None:
    report = _report()
    assert report["renamed"]["ok"], report["renamed"]
    assert "robot" in report["renamed"]["outputs"]
    assert "probe" not in report["renamed"]["outputs"]
    state = report["renamed_state"]
    # One assembly, one joint group, and it is the assembly's own.
    assert state["joint_groups"] == ["Joints"], state
    (assembly,) = state["assemblies"].values()
    assert assembly["output"] == "robot"
    assert assembly["joint_groups"] == ["Joints"]
    # The revolute joint and the grounding joint stayed under the assembly.
    assert assembly["joints"] == report["first_state"]["assemblies"][
        next(iter(report["first_state"]["assemblies"]))
    ]["joints"]
    assert len(assembly["joints"]) == 2, assembly


@needs_kernel
def test_a_refused_rename_does_not_wedge_the_next_publish() -> None:
    report = _report()
    assert not report["refused"]["ok"]
    assert "Rogue" in report["refused"]["error"]
    assert report["retried"]["ok"], report["retried"]
    assert report["retried_state"]["joint_groups"] == ["Joints"]
    assert report["after"]["ok"], report["after"]
