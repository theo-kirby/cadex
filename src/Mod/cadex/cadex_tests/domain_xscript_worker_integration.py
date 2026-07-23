# SPDX-License-Identifier: LGPL-2.1-or-later

"""Internal prototype smoke test for gated schema-v2 domain adapters.

Passing this test does not make a workbench production-ready. It exercises
shared lifecycle plumbing for in-progress adapters that remain unavailable to
providers until their real native APIs and dedicated integration suites pass
the production-readiness gate.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import sys
import tempfile

MODULE_ROOT = Path(__file__).resolve().parent.parent
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from CadexScriptedRuntime import (  # noqa: E402
    accept_candidate,
    capture_reference_inputs,
    complete_inspection,
    execute_candidate,
    finalize_candidate,
    finish_delete,
    prepare_candidate,
    prepare_delete,
    retain_candidate,
    validate_candidate,
)
from CadexScriptedDomainPublication import (  # noqa: E402
    delete_live_program,
    publish_candidate,
)
from CadexScriptedDomains import (  # noqa: E402
    PROP_PROGRAM_ID,
    get_xscript_pack,
)
from CadexModelingSurface import resolve_modeling_surface  # noqa: E402


class _WorkbenchService:
    def __init__(self, workbench: str) -> None:
        self.workbench = workbench

    def _active_document(self):
        import FreeCAD as App

        return App.ActiveDocument

    def active_workbench_name(self) -> str:
        return self.workbench

    @staticmethod
    def modeling_engine() -> str:
        return "xscript"

    @staticmethod
    def provider_document_revision() -> str:
        return "fixture-revision"

    @staticmethod
    def _partdesign_body_for_feature(_obj):
        return None


def _assert_program_inspection(captured: dict, prepared: dict) -> None:
    inspection = complete_inspection(
        {
            **captured,
            "program_id": prepared["program_id"],
            "live_programs": [],
        }
    )
    assert inspection.get("ok") is True, inspection
    assert inspection["program"]["program_id"] == prepared["program_id"]
    assert inspection["program"]["accepted_revision"] == prepared["revision"]


def _exercise_sketcher_lifecycle(root: Path, captured: dict) -> None:
    import FreeCAD as App

    document = App.newDocument("XScriptSketcherFixture")
    pack = get_xscript_pack("SketcherWorkbench")
    assert pack is not None
    source = (
        "bottom = x.line([0,0], [10,0], name='Bottom')\n"
        "right = x.line([10,0], [10,6], name='Right')\n"
        "top = x.line([10,6], [0,6], name='Top')\n"
        "left = x.line([0,6], [0,0], name='Left')\n"
        "geometry = [bottom, right, top, left]\n"
        "constraints = [\n"
        "  x.constraint('horizontal', [bottom]),\n"
        "  x.constraint('vertical', [right]),\n"
        "  x.constraint('horizontal', [top]),\n"
        "  x.constraint('vertical', [left]),\n"
        "]\n"
        "result = {'Profile': x.sketch(geometry, constraints, "
        "label='Worker Sketch')}\n"
    )
    sketch_captured = {
        **captured,
        "pack": pack,
        "operation": "create_program",
        "tool_name": "xscript.sketcher.create_program",
        "arguments": {
            "program_name": "Worker Sketch",
            "source": source,
            "input_schema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "inputs": {},
            "expected_outputs": [{"name": "Profile", "type": "sketch"}],
        },
        "document_name": str(document.Name),
        "document_uid": str(document.Uid),
        "document_objects": [],
        "surface": resolve_modeling_surface(
            "SketcherWorkbench", "xscript"
        ).summary(),
    }
    prepared = prepare_candidate(sketch_captured)
    execution = execute_candidate(prepared, cancellation_check=None)
    assert execution.get("ok") is True, execution
    assert execution["sketch_validation"]["geometry_count"] == 4
    assert execution["sketch_validation"]["conflicting_constraints"] == []
    validated = validate_candidate(prepared, execution)
    retain_candidate(prepared, status="validated")
    service = _WorkbenchService("SketcherWorkbench")
    accepted = accept_candidate(
        prepared,
        publish_candidate(service, prepared, validated),
    )
    _assert_program_inspection(sketch_captured, prepared)
    object_name = accepted["live_outputs"]["Profile"]["object_name"]
    sketch = document.getObject(object_name)
    assert sketch.TypeId == "Sketcher::SketchObject"
    assert sketch.GeometryCount == 4
    assert sketch.ConstraintCount == 4
    assert "CadexSketchValidation" in sketch.PropertiesList

    path = root / "sketcher-xscript.FCStd"
    document.saveAs(str(path))
    App.closeDocument(document.Name)
    reopened = App.openDocument(str(path))
    assert reopened is not None
    reopened_sketch = reopened.getObject(object_name)
    assert reopened_sketch is not None
    assert reopened_sketch.GeometryCount == 4
    delete_captured = {
        **sketch_captured,
        "operation": "delete_program",
        "tool_name": "xscript.sketcher.delete_program",
        "arguments": {
            "program_id": prepared["program_id"],
            "expected_revision": prepared["revision"],
            "reason": "Sketcher integration lifecycle complete",
        },
        "document_name": str(reopened.Name),
        "document_uid": str(reopened.Uid),
    }
    prepared_delete = prepare_delete(delete_captured)
    deletion = delete_live_program(service, prepared_delete)
    assert finish_delete(prepared_delete, deletion)["ok"] is True
    assert reopened.getObject(object_name) is None
    App.closeDocument(reopened.Name)


def main() -> int:
    import FreeCAD as App
    from pathlib import Path
    import shutil
    import tempfile

    root = Path(tempfile.mkdtemp(prefix="cadex-domain-worker-"))
    try:
        pack = get_xscript_pack("PartWorkbench")
        assert pack is not None
        captured = {
            "pack": pack,
            "operation": "create_program",
            "tool_name": "xscript.part.create_program",
            "arguments": {
                "program_name": "Worker Box",
                "source": 'result = {"Box": x.box(inputs["length"], 2, 3)}',
                "input_schema": {
                    "type": "object",
                    "properties": {"length": {"type": "number"}},
                    "required": ["length"],
                    "additionalProperties": False,
                },
                "inputs": {"length": 4.0},
                "expected_outputs": [{"name": "Box", "type": "solid"}],
            },
            "project_root": str(root),
            "document_name": "Fixture",
            "document_uid": "fixture-document",
            "document_revision": "fixture-revision",
            "document_objects": [],
            "surface": {
                "workbench": "PartWorkbench",
                "engine": "xscript",
                "surface_id": pack.surface_id,
            },
            "freecad_home": str(Path(App.getHomePath()).resolve()),
            "timeout_seconds": 30.0,
            "memory_limit_bytes": 1024 * 1024 * 1024,
        }
        prepared = prepare_candidate(captured)
        execution = execute_candidate(prepared, cancellation_check=None)
        assert execution.get("ok") is True, execution
        validated = validate_candidate(prepared, execution)
        assert validated.get("ok") is True
        output = validated["outputs"][0]
        assert output["name"] == "Box"
        assert output["type"] == "solid"
        assert output["facts"]["solids"] == 1
        retained = retain_candidate(prepared, status="validated")
        assert Path(retained["attempt_directory"]).is_dir()

        _exercise_sketcher_lifecycle(root, captured)

        import Part

        live_document = App.newDocument("XScriptAssemblyFixture")
        source_a = live_document.addObject("Part::Feature", "SourceA")
        source_a.Label = "Source A"
        source_a.Shape = Part.makeBox(10, 10, 10)
        source_b = live_document.addObject("Part::Feature", "SourceB")
        source_b.Label = "Source B"
        source_b.Shape = Part.makeBox(4, 4, 20)
        live_document.recompute()

        assembly_pack = get_xscript_pack("AssemblyWorkbench")
        assert assembly_pack is not None
        reference_a = {
            "document_uid": str(live_document.Uid),
            "object_name": "SourceA",
        }
        reference_b = {
            "document_uid": str(live_document.Uid),
            "object_name": "SourceB",
        }
        assembly_source = (
            "base = x.component(inputs['base'], grounded=True, label='Base')\n"
            "arm = x.component(inputs['arm'], placement=[0, 0, 0], label='Arm')\n"
            "hinge = x.joint('revolute', x.connector(base), x.connector(arm), "
            "angle_limits_degrees=[-90, 90], label='Hinge')\n"
            "model = x.assembly([base, arm], [hinge], label='Fixture Assembly')\n"
            "diagnostics = x.solve(model)\n"
            "result = {'Main': model, 'Base': base, 'Arm': arm, "
            "'Hinge': hinge, 'Diagnostics': diagnostics}"
        )
        assembly_captured = {
            **captured,
            "pack": assembly_pack,
            "operation": "create_program",
            "tool_name": "xscript.assembly.create_program",
            "arguments": {
                "program_name": "Worker Assembly",
                "source": assembly_source,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "base": {
                            "type": "object",
                            "x-cadex-reference": True,
                            "properties": {
                                "document_uid": {"type": "string"},
                                "object_name": {"type": "string"},
                            },
                            "required": ["document_uid", "object_name"],
                            "additionalProperties": False,
                        },
                        "arm": {
                            "type": "object",
                            "x-cadex-reference": True,
                            "properties": {
                                "document_uid": {"type": "string"},
                                "object_name": {"type": "string"},
                            },
                            "required": ["document_uid", "object_name"],
                            "additionalProperties": False,
                        },
                    },
                    "required": ["base", "arm"],
                    "additionalProperties": False,
                },
                "inputs": {"base": reference_a, "arm": reference_b},
                "expected_outputs": [
                    {"name": "Main", "type": "assembly"},
                    {"name": "Base", "type": "component_link"},
                    {"name": "Arm", "type": "component_link"},
                    {"name": "Hinge", "type": "joint"},
                    {"name": "Diagnostics", "type": "solver_diagnostics"},
                ],
            },
            "document_objects": [
                {"name": "SourceA", "label": "Source A", "type_id": "Part::Feature"},
                {"name": "SourceB", "label": "Source B", "type_id": "Part::Feature"},
            ],
            "document_name": str(live_document.Name),
            "document_uid": str(live_document.Uid),
            "surface": resolve_modeling_surface(
                "AssemblyWorkbench", "xscript"
            ).summary(),
        }
        assembly_prepared = prepare_candidate(assembly_captured)
        assembly_service = _WorkbenchService("AssemblyWorkbench")
        assembly_prepared = finalize_candidate(
            assembly_prepared,
            capture_reference_inputs(assembly_service, assembly_prepared),
        )
        assembly_execution = execute_candidate(
            assembly_prepared, cancellation_check=None
        )
        assert assembly_execution.get("ok") is True, assembly_execution
        assert assembly_execution["assembly_validation"]["solver_code"] == 0
        assert assembly_execution["assembly_validation"]["joint_count"] == 1
        assembly_validated = validate_candidate(assembly_prepared, assembly_execution)
        assert assembly_validated.get("ok") is True
        diagnostics = next(
            item
            for item in assembly_validated["outputs"]
            if item["name"] == "Diagnostics"
        )
        assert diagnostics["diagnostics"]["status"] == "solved"
        retain_candidate(assembly_prepared, status="validated")
        service = assembly_service
        publication = publish_candidate(service, assembly_prepared, assembly_validated)
        accepted = accept_candidate(assembly_prepared, publication)
        _assert_program_inspection(assembly_captured, assembly_prepared)
        assert accepted["accepted_revision"] == assembly_prepared["revision"]
        live_names = {
            name: details["object_name"]
            for name, details in accepted["live_outputs"].items()
        }
        assert live_document.getObject(live_names["Main"]).TypeId == (
            "Assembly::AssemblyObject"
        )
        assert live_document.getObject(live_names["Base"]).LinkedObject is source_a
        assert live_document.getObject(live_names["Arm"]).LinkedObject is source_b
        assert live_document.getObject(live_names["Hinge"]).Proxy is not None
        diagnostics_object = live_document.getObject(live_names["Diagnostics"])
        assert diagnostics_object.CadexSolverStatus == "solved"
        assert diagnostics_object.CadexSolverCode == 0
        grounded = [
            obj
            for obj in live_document.Objects
            if str(getattr(obj, "CadexXScriptOutputName", "")) == "Base.ground"
        ]
        assert len(grounded) == 1
        assert grounded[0].Proxy is not None
        accepted_diagnostics = next(
            item["diagnostics"]
            for item in accepted["outputs"]
            if item["name"] == "Diagnostics"
        )
        assert accepted_diagnostics["solver_code"] == 0
        assert accepted_diagnostics["grounded_components"] == ["Base"]

        update_captured = {
            **assembly_captured,
            "operation": "edit_source",
            "tool_name": "xscript.assembly.edit_source",
            "arguments": {
                "program_id": assembly_prepared["program_id"],
                "expected_revision": assembly_prepared["revision"],
                "replacements": [
                    {"old": "Fixture Assembly", "new": "Updated Assembly"}
                ],
            },
        }
        update_prepared = prepare_candidate(update_captured)
        update_prepared = finalize_candidate(
            update_prepared,
            capture_reference_inputs(service, update_prepared),
        )
        update_execution = execute_candidate(update_prepared, cancellation_check=None)
        assert update_execution.get("ok") is True, update_execution
        update_validated = validate_candidate(update_prepared, update_execution)
        retain_candidate(update_prepared, status="validated")
        update_publication = publish_candidate(
            service, update_prepared, update_validated
        )
        updated = accept_candidate(update_prepared, update_publication)
        assert {
            name: details["object_name"]
            for name, details in updated["live_outputs"].items()
        } == live_names
        assert live_document.getObject(live_names["Main"]).Label == "Updated Assembly"

        failed_captured = {
            **assembly_captured,
            "operation": "edit_source",
            "tool_name": "xscript.assembly.edit_source",
            "arguments": {
                "program_id": update_prepared["program_id"],
                "expected_revision": update_prepared["revision"],
                "replacements": [{"old": "x.solve", "new": "x.missing_export"}],
            },
        }
        failed_prepared = prepare_candidate(failed_captured)
        failed_prepared = finalize_candidate(
            failed_prepared,
            capture_reference_inputs(service, failed_prepared),
        )
        failed_execution = execute_candidate(failed_prepared, cancellation_check=None)
        assert failed_execution.get("ok") is False
        failed_retained = retain_candidate(
            failed_prepared,
            status="failed",
            failure=failed_execution,
        )
        assert (
            failed_retained["manifest"]["accepted_revision"]
            == update_prepared["revision"]
        )
        assert (
            failed_retained["manifest"]["working_revision"]
            == failed_prepared["revision"]
        )
        assert live_document.getObject(live_names["Main"]).Label == "Updated Assembly"

        document_path = root / "assembly-xscript.FCStd"
        live_document.recompute()
        live_document.saveAs(str(document_path))
        App.closeDocument(live_document.Name)
        reopened = App.openDocument(str(document_path))
        assert reopened is not None
        for output_name, object_name in live_names.items():
            obj = reopened.getObject(object_name)
            assert obj is not None, output_name
            assert (
                str(getattr(obj, PROP_PROGRAM_ID, "")) == update_prepared["program_id"]
            )

        delete_captured = {
            **update_captured,
            "operation": "delete_program",
            "tool_name": "xscript.assembly.delete_program",
            "arguments": {
                "program_id": update_prepared["program_id"],
                "expected_revision": failed_prepared["revision"],
                "reason": "Integration lifecycle complete",
            },
            "document_name": str(reopened.Name),
            "document_uid": str(reopened.Uid),
        }
        prepared_delete = prepare_delete(delete_captured)
        deletion = delete_live_program(service, prepared_delete)
        deleted = finish_delete(prepared_delete, deletion)
        assert deleted["ok"] is True
        assert reopened.getObject("SourceA") is not None
        assert reopened.getObject("SourceB") is not None
        assert not any(
            str(getattr(obj, PROP_PROGRAM_ID, "")) == update_prepared["program_id"]
            for obj in reopened.Objects
        )
        App.closeDocument(reopened.Name)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("XScript domain worker integration passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
