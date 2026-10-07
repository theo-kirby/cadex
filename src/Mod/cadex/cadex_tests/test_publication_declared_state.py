# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A rerun project script publishes the state it declares (ADR-585).

The excavator-mini project renamed its component outputs twice, ending at
``cp_*`` names, because two publishes of an otherwise ordinary edit were
refused:

* ``grounded=True`` turned to ``grounded=False`` on the same output raised
  ``Cannot unground component output 'c_drive_left'; external objects
  reference its managed grounding joint``, naming the assembly's own
  ``Joints`` group -- untagged, so the check counted it as foreign;
* a part output dropped from ``result`` raised ``Cannot retire XScript
  output 'bolt_drive_0'; human-created or foreign document objects still
  reference it``, naming the project's own component link -- owned by the
  assembly pass, which had not yet run when the part pass retired the shape.

The refusals still stand for a real foreign reference, so the last case
adds one and expects the refusal. These run the real kernel, because the
stubbed FreeCAD in ``conftest.py`` has no group or link semantics.
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

def script(bolt="bolt", bolt_grounded=True, with_bolt=True):
    if with_bolt:
        bolt_lines = f"""
{bolt} = part.cylinder(3, 12)
cbolt = assembly.component({bolt}, placement=[20, 20, 6], grounded={bolt_grounded})
"""
        weld = "" if bolt_grounded else """
w = assembly.joint("fixed", assembly.connector(cbolt), assembly.connector(base))
"""
        comps = "[base, swing, cbolt]"
        joints = "[j]" if bolt_grounded else "[j, w]"
        extra = f', "{bolt}": {bolt}, "cbolt": cbolt' + ("" if bolt_grounded else ', "w": w')
    else:
        bolt_lines, weld, comps, joints, extra = "", "", "[base, swing]", "[j]", ""
    return f"""
plate = part.box(60, 60, 6)
arm = part.box(80, 8, 8)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
{bolt_lines}
j = assembly.joint("revolute",
    assembly.connector(base, "origin", offset={{"position": [12, 0, 6], "axis": [1, 0, 0], "angle_degrees": 90}}),
    assembly.connector(swing, "origin", offset={{"position": [0, 0, 0], "axis": [1, 0, 0], "angle_degrees": 90}}))
{weld}
asm = assembly.assembly({comps}, {joints})
diag = assembly.solve(asm)
result = {{"plate": plate, "arm": arm, "base": base, "swing": swing, "j": j, "asm": asm, "diag": diag{extra}}}
"""

def pd_script(name):
    square = """partdesign.sketch([
    partdesign.line([0, 0], [16, 0]),
    partdesign.line([16, 0], [16, 10]),
    partdesign.line([16, 10], [0, 10]),
    partdesign.line([0, 10], [0, 0]),
], [])"""
    return f"""
keep = partdesign.body(partdesign.pad({square}, 4))
{name} = partdesign.body(partdesign.pad({square}, 6))
plate = part.box(60, 60, 6)
base = assembly.component(plate, grounded=True)
cblock = assembly.component({name}, placement=[0, 0, 6])
w = assembly.joint("fixed", assembly.connector(cblock), assembly.connector(base))
asm = assembly.assembly([base, cblock], [w])
diag = assembly.solve(asm)
result = {{"keep": keep, "{name}": {name}, "plate": plate, "base": base, "cblock": cblock, "w": w, "asm": asm, "diag": diag}}
"""

def output_object(doc, output):
    for obj in doc.Objects:
        if str(getattr(obj, "CadexXScriptOutputName", "") or "") == output:
            return obj
    return None

def snapshot(doc):
    cbolt = output_object(doc, "cbolt")
    return {
        "objects": sorted(o.Name for o in doc.Objects),
        "outputs": sorted(
            str(getattr(o, "CadexXScriptOutputName", "") or "")
            for o in doc.Objects
            if str(getattr(o, "CadexXScriptOutputName", "") or "")
        ),
        "cbolt_target": (
            str(cbolt.LinkedObject.CadexXScriptOutputName)
            if cbolt is not None and cbolt.LinkedObject is not None
            else None
        ),
    }

report = {}
root = Path(tempfile.mkdtemp(prefix="cadex-declared-"))
doc = App.newDocument("DeclaredState")
service = lifecycle._Service(root)
store = CadexProjectScriptStore(root)

def publish(source):
    working = (store.read_state() or {}).get("working_revision", "")
    prepared, validated = lifecycle._run_lifecycle(
        service, "xscript.project.write_script",
        {"source": source, "expected_revision": working},
    )
    try:
        publication = publish_project_candidate(service, prepared, validated)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    accept_project_candidate(prepared, publication, validated)
    return {"ok": True, "state": snapshot(doc)}

try:
    report["grounded"] = publish(script())
    report["ungrounded"] = publish(script(bolt_grounded=False))
    report["regrounded"] = publish(script(bolt_grounded=True))
    # The component keeps its output name; its source part is renamed, so
    # the part pass retires ``bolt`` while ``cbolt`` still links it.
    report["source_renamed"] = publish(script(bolt="screw"))
    # The part and its component leave the script together.
    report["retired"] = publish(script(bolt="screw", with_bolt=False))
    # A real foreign reference is still refused, and names its owner.
    report["restored"] = publish(script(bolt="screw"))
    foreign = doc.addObject("App::Link", "ForeignLink")
    foreign.LinkedObject = output_object(doc, "screw")
    report["foreign"] = publish(script(bolt="nut"))
    doc.removeObject("ForeignLink")
    # The same through the Part Design pass, which retires on its own path.
    report["pd_first"] = publish(pd_script("block"))
    report["pd_renamed"] = publish(pd_script("brick"))
    target = output_object(doc, "cblock").LinkedObject
    report["pd_renamed"]["cblock_target"] = str(
        getattr(target, "CadexXScriptOutputName", "") or ""
    )
except Exception:
    report["crash"] = traceback.format_exc()
finally:
    App.closeDocument(doc.Name)
open(%(out)r, "w").write(json.dumps(report))
'''


def _kernel_report() -> dict:
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="cadex-declared-probe-"))
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
def test_a_grounded_component_ungrounds_in_place() -> None:
    report = _report()
    assert report["grounded"]["ok"], report["grounded"]
    assert "cbolt.ground" in report["grounded"]["state"]["outputs"]
    assert report["ungrounded"]["ok"], report["ungrounded"]
    state = report["ungrounded"]["state"]
    assert "cbolt.ground" not in state["outputs"], state
    assert "base.ground" in state["outputs"], state
    assert "w" in state["outputs"], state
    # ...and grounds again from the same script.
    assert report["regrounded"]["ok"], report["regrounded"]
    assert "cbolt.ground" in report["regrounded"]["state"]["outputs"]


@needs_kernel
def test_a_component_source_renamed_retires_the_old_shape() -> None:
    report = _report()
    assert report["source_renamed"]["ok"], report["source_renamed"]
    state = report["source_renamed"]["state"]
    assert "bolt" not in state["outputs"], state
    assert "screw" in state["outputs"], state
    assert state["cbolt_target"] == "screw", state


@needs_kernel
def test_a_part_and_its_component_retire_together() -> None:
    report = _report()
    assert report["retired"]["ok"], report["retired"]
    state = report["retired"]["state"]
    for gone in ("screw", "cbolt", "cbolt.ground"):
        assert gone not in state["outputs"], state
    assert report["restored"]["ok"], report["restored"]


@needs_kernel
def test_a_foreign_reference_still_blocks_retirement() -> None:
    report = _report()
    assert not report["foreign"]["ok"], report["foreign"]
    error = report["foreign"]["error"]
    assert "Cannot retire XScript output 'screw'" in error, error
    assert "ForeignLink" in error, error


@needs_kernel
def test_a_part_design_source_renamed_retires_the_old_body() -> None:
    report = _report()
    assert report["pd_first"]["ok"], report["pd_first"]
    renamed = report["pd_renamed"]
    assert renamed["ok"], renamed
    assert "block" not in renamed["state"]["outputs"], renamed
    assert "brick" in renamed["state"]["outputs"], renamed
    assert renamed["cblock_target"] == "brick", renamed


# The same two rules without a kernel: the stubbed objects carry only the
# ownership tags and the InList the reference check reads.


class _Obj:
    def __init__(self, name, type_id="Part::Feature", domain=None, output=""):
        self.Name = name
        self.TypeId = type_id
        self.InList: list = []
        self.Group: list = []
        self.OutList: list = []
        self.PropertiesList: list = []
        if domain is not None:
            self.CadexXScriptProgramId = "project"
            self.CadexXScriptDomain = domain
            self.CadexXScriptOutputName = output
            self.PropertiesList = [
                "CadexXScriptProgramId",
                "CadexXScriptDomain",
                "CadexXScriptOutputName",
            ]


class _Doc:
    def __init__(self, *objects):
        self.Objects = list(objects)


class _Pack:
    domain = "assembly"


def test_the_assemblys_own_joint_group_is_not_a_foreign_reference() -> None:
    import CadexScriptedDomainPublication as publication

    assembly = _Obj("Assembly", "Assembly::AssemblyObject", "assembly", "asm")
    joints = _Obj("Joints", "Assembly::JointGroup")
    ground = _Obj("Ground_cbolt", "App::FeaturePython", "assembly", "cbolt.ground")
    assembly.Group = [joints]
    joints.Group = [ground]
    joints.InList = [assembly]
    ground.InList = [joints]
    doc = _Doc(assembly, joints, ground)
    prepared = {"program_id": "project", "pack": _Pack()}
    internal = publication._domain_internal_objects(doc, prepared)
    assert publication._external_uses(doc, [ground], internal) == []
    ground.InList.append(_Obj("Rogue"))
    uses = publication._external_uses(doc, [ground], internal)
    assert [use["owner_name"] for use in uses] == ["Rogue"]


def test_a_retired_shape_linked_by_the_scripts_own_component_retires() -> None:
    import CadexScriptedDomainPublication as publication

    bolt = _Obj("VibePart_project_bolt", domain="part", output="bolt")
    cbolt = _Obj("VibeAssembly_project_cbolt", "App::Link", "assembly", "cbolt")
    bolt.InList = [cbolt]
    doc = _Doc(bolt, cbolt)
    internal = publication._program_internal_objects(doc, "project")
    publication._refuse_foreign_retirement_uses(doc, [bolt], internal)
    bolt.InList.append(_Obj("ForeignLink", "App::Link"))
    with pytest.raises(
        RuntimeError, match="Cannot retire XScript output 'bolt'.*ForeignLink"
    ):
        publication._refuse_foreign_retirement_uses(doc, [bolt], internal)
