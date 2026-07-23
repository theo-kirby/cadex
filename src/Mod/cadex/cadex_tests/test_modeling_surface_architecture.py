# SPDX-License-Identifier: LGPL-2.1-or-later

"""Exact modeling-surface and XScript v2 architecture contracts."""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path

import pytest

from CadexModelingSurface import (
    CORE_CONVERSATION_VIEW_TOOLS,
    HIDDEN_PROVIDER_INSPECTION_TOOLS,
    resolve_modeling_surface,
    validate_surface_names,
)
from CadexTools import ToolSpec
import CadexScriptedDomains as domains

USER_WORKBENCHES = tuple(
    workbench
    for workbench in domains.XSCRIPT_WORKBENCH_PACKS
    if workbench not in {"NoneWorkbench", "TestWorkbench"}
)
PRODUCTION_READY_XSCRIPT_WORKBENCHES = frozenset(
    {
        "PartDesignWorkbench",
        "SketcherWorkbench",
        "PartWorkbench",
        "AssemblyWorkbench",
    }
)


def test_complete_xscript_surface_matrix() -> None:
    assert len(USER_WORKBENCHES) == 4
    observed_ready = set()
    for workbench in USER_WORKBENCHES:
        scripted = resolve_modeling_surface(workbench, "xscript")
        domain_pack = domains.get_xscript_pack(workbench)
        assert domain_pack is not None
        assert scripted.domain == domain_pack.domain
        assert set(scripted.core_tool_names) == set(CORE_CONVERSATION_VIEW_TOOLS)
        if domain_pack.production_ready:
            observed_ready.add(workbench)
            assert scripted.available is True
            assert scripted.unavailable_reason == ""
            assert scripted.cad_tool_names == tuple(
                name
                for name in domain_pack.tool_names
                if name not in HIDDEN_PROVIDER_INSPECTION_TOOLS
                and not name.endswith(".describe_api")
                and not name.endswith(".inspect_program")
            )
            assert len(scripted.cad_tool_names) == 6
            assert len(scripted.tool_names) <= 15
            assert "core.inspect" in scripted.tool_names
            assert not set(scripted.tool_names) & set(HIDDEN_PROVIDER_INSPECTION_TOOLS)
            namespaces = {
                name.split(".")[1]
                for name in scripted.cad_tool_names
                if name.count(".") == 2
            }
            assert namespaces == {domain_pack.domain}
        else:
            assert scripted.available is False
            assert scripted.cad_tool_names == ()
            assert scripted.tool_names == scripted.core_tool_names
            assert "production-readiness gate" in scripted.unavailable_reason
            assert not any(
                name.startswith("xscript.") for name in scripted.tool_names
            )
    assert observed_ready == PRODUCTION_READY_XSCRIPT_WORKBENCHES


@pytest.mark.parametrize(
    "workbench",
    (None, "NoneWorkbench", "TestWorkbench", "UnregisteredWorkbench"),
)
@pytest.mark.parametrize("engine", ("xscript", "xscript"))
def test_unsupported_surfaces_are_precise_and_core_only(
    workbench: str | None, engine: str
) -> None:
    surface = resolve_modeling_surface(workbench, engine)
    assert surface.available is False
    assert surface.cad_tool_names == ()
    assert surface.unavailable_reason
    assert set(surface.tool_names) == set(CORE_CONVERSATION_VIEW_TOOLS)


def test_mixed_and_cross_domain_surfaces_are_rejected() -> None:
    part = resolve_modeling_surface("PartWorkbench", "xscript")
    native_part_tool = "part.box"
    with pytest.raises(ValueError, match="cannot contain native"):
        validate_surface_names(
            workbench="PartWorkbench",
            engine="xscript",
            names=[*part.tool_names, native_part_tool],
            allowed_names=[*part.tool_names, native_part_tool],
        )
    with pytest.raises(ValueError, match="exactly one domain"):
        validate_surface_names(
            workbench="PartWorkbench",
            engine="xscript",
            names=[
                "xscript.part.inspect_program",
                "xscript.assembly.inspect_program",
            ],
        )


def test_domain_lifecycle_schemas_are_stable_and_domain_specific() -> None:
    for workbench in USER_WORKBENCHES:
        pack = domains.get_xscript_pack(workbench)
        assert pack is not None
        specs = domains.domain_tool_specs(pack)
        assert tuple(spec["name"] for spec in specs) == pack.tool_names
        assert len(specs) == 8
        for raw in specs:
            spec = ToolSpec.from_mapping(raw)
            assert spec.workbench == workbench
            assert spec.parameters["additionalProperties"] is False
        create = next(spec for spec in specs if spec["name"].endswith("create_program"))
        output_enum = create["parameters"]["properties"]["expected_outputs"]["items"][
            "properties"
        ]["type"]["enum"]
        assert output_enum == list(pack.output_types)


def test_shared_xscript_lifecycle_is_unambiguous_for_the_operating_model() -> None:
    for workbench in USER_WORKBENCHES:
        pack = domains.get_xscript_pack(workbench)
        assert pack is not None
        specs = {
            spec["name"].rsplit(".", 1)[-1]: spec
            for spec in domains.domain_tool_specs(pack)
        }
        program_id_description = specs["inspect_program"]["parameters"]["properties"][
            "program_id"
        ]["description"]
        assert "create_program" in program_id_description
        assert "core.inspect" in program_id_description
        assert "source-only" in specs["edit_source"]["description"]
        assert "value-only" in specs["set_inputs"]["description"]
        assert (
            "prefer edit_source or set_inputs"
            in specs["reconfigure_program"]["description"]
        )

        adapter = domains.get_domain_adapter(pack.domain)
        assert adapter is not None
        description = adapter.describe_api()
        operating = description["model_operating_contract"]
        assert [item["action"] for item in operating["authoring_sequence"]] == [
            "discover",
            "learn_api",
            "author",
            "repair",
            "verify",
        ]
        assert set(operating["mutation_selection"]) == {
            "edit_source",
            "set_inputs",
            "reconfigure_program",
        }
        assert "failed candidate revision" in operating["revision_rule"]
        reference_schema = operating["input_schema_templates"][
            "stable_reference_property"
        ]
        assert reference_schema["x-cadex-reference"] is True
        assert reference_schema["required"] == ["document_uid", "object_name"]


def test_every_domain_description_is_copy_ready_for_the_operating_model() -> None:
    for workbench in USER_WORKBENCHES:
        pack = domains.get_xscript_pack(workbench)
        assert pack is not None
        adapter = domains.get_domain_adapter(pack.domain)
        assert adapter is not None
        description = adapter.describe_api()

        exports = description["runtime_exports"]
        export_names = [item["name"] for item in exports]
        assert export_names == list(pack.api_exports)
        assert len(export_names) == len(set(export_names))
        assert all(item["description"] for item in exports)
        assert all(
            "*args" not in item["signature"] and "**" not in item["signature"]
            for item in exports
        )
        assert description["accepted_output_types"] == list(pack.output_types)
        assert "exactly match expected_outputs" in description["result_contract"]
        assert "redundan" in json.dumps(description).lower()
        assert len(json.dumps(description, separators=(",", ":")).encode()) < 48_000

        handoffs = json.dumps(description["workbench_handoffs"]).lower()
        assert "human" in handoffs and "switch" in handoffs
        error_contract = json.dumps(description["error_contract"]).lower()
        assert "correct" in error_contract

        patterns = description["recommended_patterns"]
        assert patterns
        for pattern in patterns:
            source = pattern["source"]
            expected_outputs = pattern["expected_outputs"]
            assert pattern["goal"]
            assert expected_outputs
            domains.validate_program_source(source)
            tree = ast.parse(source)
            result_assignments = [
                node
                for node in tree.body
                if isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == "result"
                    for target in node.targets
                )
            ]
            assert len(result_assignments) == 1
            result_value = result_assignments[0].value
            assert isinstance(result_value, ast.Dict)
            result_names = [ast.literal_eval(key) for key in result_value.keys]
            expected_names = [item["name"] for item in expected_outputs]
            assert result_names == expected_names
            assert all(item["type"] in pack.output_types for item in expected_outputs)

            api_calls = {
                node.func.attr
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "api"
            }
            assert api_calls <= set(pack.api_exports)


def test_inspect_program_returns_machine_readable_model_state() -> None:
    pack = domains.get_xscript_pack("AssemblyWorkbench")
    assert pack is not None
    adapter = domains.get_domain_adapter(pack.domain)
    assert adapter is not None
    program_id = "a" * 32
    accepted_revision = "b" * 64
    accepted = adapter.inspect(
        {},
        {
            "program_id": program_id,
            "domain": pack.domain,
            "workbench": pack.workbench,
            "working_revision": accepted_revision,
            "accepted_revision": accepted_revision,
            "latest_candidate": {"status": "accepted"},
        },
    )
    assert accepted["model_state"] == {
        "status": "accepted_current",
        "candidate_status": "accepted",
        "accepted_is_current": True,
        "accepted_live_state_preserved": True,
        "next_write_expected_revision": accepted_revision,
        "mutation_selection": {
            "source_only": "xscript.assembly.edit_source",
            "input_values_only": "xscript.assembly.set_inputs",
            "contract_or_outputs": "xscript.assembly.reconfigure_program",
        },
        "instruction": (
            "The accepted contract is current; verify domain-specific live evidence."
        ),
    }

    failed_revision = "c" * 64
    failed = adapter.inspect(
        {},
        {
            "program_id": program_id,
            "domain": pack.domain,
            "workbench": pack.workbench,
            "working_revision": failed_revision,
            "accepted_revision": accepted_revision,
            "latest_candidate": {"status": "failed", "failure": {"error": "bad"}},
        },
    )
    assert failed["model_state"]["status"] == "working_candidate_not_accepted"
    assert failed["model_state"]["accepted_live_state_preserved"] is True
    assert failed["model_state"]["next_write_expected_revision"] == failed_revision
    assert failed["program"]["latest_candidate"]["failure"]["error"] == "bad"


def test_partdesign_xscript_schema_golden_fixture() -> None:
    fixture_path = Path(__file__).with_name("partdesign_xscript_schema_sha256.json")
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    pack = domains.get_xscript_pack("PartDesignWorkbench")
    assert pack is not None
    assert pack.program_schema == "cadex-xscript-program-v2"
    assert pack.api_global == "x"
    observed: dict[str, str] = {}
    for raw in domains.domain_tool_specs(pack):
        schema = ToolSpec.from_mapping(raw).to_schema(
            active_workbench="PartDesignWorkbench"
        )
        digest = hashlib.sha256(
            json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        observed[str(schema["name"])] = digest
    assert observed == expected
    assert all(name.startswith("xscript.partdesign.") for name in observed)


def test_schema_v1_migrates_to_partdesign_without_relocation(tmp_path: Path) -> None:
    v1_directory = tmp_path / "xscript" / ("a" * 32)
    migrated = domains.migrate_program_manifest(
        {
            "schema": domains.PARTDESIGN_V1_SCHEMA,
            "model_id": "a" * 32,
            "model_name": "Saved v1 model",
            "source": "result = {}",
            "parameters": {"Length": 10.0},
            "expected_outputs": ["Body"],
            "revision": "b" * 64,
        },
        artifact_directory=v1_directory,
    )
    assert migrated["schema"] == domains.PROGRAM_SCHEMA
    assert migrated["version"] == 2
    assert migrated["domain"] == "partdesign"
    assert migrated["workbench"] == "PartDesignWorkbench"
    assert migrated["artifact_directory"] == str(v1_directory)
    assert migrated["expected_outputs"] == [{"name": "Body", "type": "solid"}]
    assert migrated["migration_required"] is True
    assert migrated["migration_action"] == "xscript.partdesign.reconfigure_program"

    v1_directory.mkdir(parents=True)
    (v1_directory / "model.py").write_text("result = {}\n", encoding="utf-8")
    (v1_directory / "parameters.json").write_text('{"Length":12}', encoding="utf-8")
    artifact_backed = domains.migrate_program_manifest(
        {
            "schema": domains.PARTDESIGN_V1_SCHEMA,
            "model_id": "a" * 32,
            "model_name": "Saved v1 model",
            "expected_outputs": ["Body"],
            "revision": "b" * 64,
        },
        artifact_directory=v1_directory,
    )
    assert artifact_backed["source"] == "result = {}\n"
    assert artifact_backed["inputs"] == {"Length": 12}
    assert artifact_backed["artifact_directory"] == str(v1_directory)


def test_source_and_input_policy_blocks_escape_hatches() -> None:
    for source in (
        "import os\nresult = {}",
        "result = open('/tmp/value')",
        "result = {'x': doc.saveAs('x.FCStd')}",
        "result = {'x': api._domain}",
    ):
        with pytest.raises(ValueError, match="policy violation"):
            domains.validate_program_source(source)
    with pytest.raises(ValueError, match="raw filesystem path"):
        domains.validate_inputs({"source": "/tmp/cloud.xyz"})
    with pytest.raises(ValueError, match="arbitrary object"):
        domains.validate_inputs({"source": {"path": "artifact.xyz"}})
    assert domains.validate_inputs(
        {"source": {"document_uid": "uid", "object_name": "Cloud"}}
    )
    with pytest.raises(ValueError, match="must require"):
        domains.validate_input_schema(
            {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "object",
                        "x-cadex-reference": True,
                        "properties": {
                            "document_uid": {"type": "string"},
                            "object_name": {"type": "string"},
                        },
                        "additionalProperties": False,
                    }
                },
                "additionalProperties": False,
            }
        )


def test_worker_result_values_must_come_from_the_active_domain_api() -> None:
    from cadex_domain_worker import _payload

    forged = {
        "domain": "part",
        "operation": "box",
        "output_type": "solid",
        "arguments": [1, 1, 1],
        "properties": {},
    }
    with pytest.raises(TypeError, match="active domain api"):
        _payload(forged)


def test_part_api_is_explicit_documented_and_generated_from_the_runtime() -> None:
    from cadex_domain_api import create_domain_api

    pack = domains.get_xscript_pack("PartWorkbench")
    assert pack is not None and pack.production_ready
    api = create_domain_api(pack.domain, pack.api_exports, pack.output_types)
    adapter = domains.get_domain_adapter(pack.domain)
    assert adapter is not None and adapter.production_ready
    description = adapter.describe_api()
    exports = description["runtime_exports"]

    assert description["api_contract"] == "cadex-xscript-part-api-v2"
    assert description["units"] == {
        "length": "millimetres",
        "angle": "degrees",
        "tolerance": "millimetres",
    }
    assert description["topology_selection"]["index_base"] == 1
    assert [item["name"] for item in exports] == list(pack.api_exports)
    assert tuple(api.exported_names) == pack.api_exports
    assert len(exports) == 49
    sweep_export = next(item for item in exports if item["name"] == "sweep")
    assert "DomainValue | Sequence[DomainValue]" in sweep_export["signature"]
    assert "one or more ordered wire profiles" in sweep_export["description"]
    assert "long_helix" not in pack.api_exports
    assert "project_parallel" not in pack.api_exports
    assert "project_perspective" not in pack.api_exports
    assert {"helix", "project"} <= set(pack.api_exports)
    assert all(item["description"] for item in exports)
    assert all("*args" not in item["signature"] for item in exports)
    assert all("**properties" not in item["signature"] for item in exports)
    grouped = {
        name for names in description["operation_groups"].values() for name in names
    }
    assert grouped == set(pack.api_exports)
    selection = description["operation_selection"]
    assert selection["one_or_more_profiles_along_path"].startswith("api.sweep")
    assert selection["intersection_edges_only"] == "api.section"
    assert selection["parallel_planar_cross_sections"] == "api.slice"
    assert selection["all_touching_boolean_fragments_with_provenance"] == (
        "api.general_fuse"
    )
    assert selection["join_touching_faces_or_shells"] == "api.sew"
    assert selection["remove_redundant_boolean_splitters"] == "api.refine"
    assert "one helix operation" in selection["redundancy_contract"]
    assert "one projection operation" in selection["redundancy_contract"]
    assert "There are no model-facing" in selection["redundancy_contract"]
    assert description["composition_contract"]["construction_order"][-1].startswith(
        "Return only semantic publication outputs"
    )
    assert (
        "never cycle through guessed indexes"
        in description["model_verification_contract"]["selection_repair"]
    )
    assert (
        "cannot switch workbench or engine" in description["workbench_handoffs"]["rule"]
    )
    assert (
        len(
            json.dumps(description, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        )
        < 32_000
    )
    assert len(description["recommended_patterns"]) >= 2

    assert not hasattr(api, "long_helix")
    assert not hasattr(api, "project_parallel")
    assert not hasattr(api, "project_perspective")


def test_part_api_reports_operation_and_parameter_before_kernel_execution() -> None:
    from cadex_domain_api import create_domain_api

    pack = domains.get_xscript_pack("PartWorkbench")
    assert pack is not None
    api = create_domain_api(pack.domain, pack.api_exports, pack.output_types)

    cases = (
        (
            lambda: api.from_object({"object_name": "Body"}, output_type="solid"),
            r"api\.from_object.*reference",
        ),
        (lambda: api.box(-1, 2, 3), r"api\.box.*length"),
        (lambda: api.wedge(2, 3, 4, ridge_x=3), r"api\.wedge.*ridge_x"),
        (lambda: api.cylinder(2, 3, direction=[0, 0, 0]), r"api\.cylinder.*direction"),
        (lambda: api.wire([[0, 0, 0]]), r"api\.wire.*items"),
        (
            lambda: api.sweep([], api.wire([[0, 0, 0], [0, 0, 1]])),
            r"api\.sweep.*profile",
        ),
        (lambda: api.fillet(object(), 1), r"api\.fillet.*shape"),
        (
            lambda: api.repair(
                api.box(1, 1, 1),
                working_tolerance=1.0e-2,
                maximum_tolerance=1.0e-3,
            ),
            r"api\.repair.*tolerance",
        ),
        (
            lambda: api.bezier([[0, 0, 0], [1, 1, 0]], weights=[1.0]),
            r"api\.bezier.*weights",
        ),
        (
            lambda: api.nurbs_curve(
                [[0, 0, 0], [1, 1, 0], [2, 0, 0]],
                2,
                [0.0, 1.0],
                [2, 2],
            ),
            r"api\.nurbs_curve.*multiplicities",
        ),
        (
            lambda: api.transform(api.box(1, 1, 1), scale=[1, 0, 1]),
            r"api\.transform.*scale",
        ),
        (
            lambda: api.helix(1, 10, 2, representation="adaptive"),
            r"api\.helix.*representation",
        ),
        (
            lambda: api.project(
                api.plane(10, 10),
                api.circle(2),
                [0, 0, 1],
                mode="orthographic",
            ),
            r"api\.project.*mode",
        ),
    )
    for invoke, pattern in cases:
        with pytest.raises(ValueError, match=pattern):
            invoke()


def test_assembly_api_is_explicit_graph_based_and_generated_from_runtime() -> None:
    from cadex_domain_api import create_domain_api

    pack = domains.get_xscript_pack("AssemblyWorkbench")
    assert pack is not None
    api = create_domain_api(pack.domain, pack.api_exports, pack.output_types)
    adapter = domains.get_domain_adapter(pack.domain)
    assert adapter is not None
    description = adapter.describe_api()

    assert description["api_contract"] == "cadex-xscript-assembly-api-v1"
    assert tuple(api.exported_names) == pack.api_exports
    assert [item["name"] for item in description["runtime_exports"]] == list(
        pack.api_exports
    )
    assert all(item["description"] for item in description["runtime_exports"])
    assert all(
        "*args" not in item["signature"] and "**properties" not in item["signature"]
        for item in description["runtime_exports"]
    )
    assert set(description["joint_types"]["coupled_motion"]) == {
        "rack_pinion",
        "screw",
        "gears",
        "belt",
    }
    assert description["solver_codes"]["-6"] == "no_grounded_component"
    assert description["capability_inventory"]["joint_graph"]["status"] == "supported"
    assert any(
        "vertex anchors" in feature
        for feature in description["capability_inventory"]["joint_graph"]["features"]
    )
    assert (
        "Slider joint"
        in description["joint_types"]["coupled_joint_dependencies"]["screw"]
    )
    assert [step["action"] for step in description["model_workflow"]] == [
        "discover",
        "plan_frames",
        "author_graph",
        "solve",
        "simulate",
        "present",
        "document",
        "repair",
        "verify",
    ]
    assert description["operation_selection"]["named_parts_table"] == (
        "api.bill_of_materials"
    )
    assert "no aliases" in description["operation_selection"]["redundancy_contract"]
    assert "failed_segment_index" in description["nested_subassemblies"]["repair"]
    assert any(
        "nested flexible links" in feature
        for feature in description["capability_inventory"]["component_occurrences"][
            "features"
        ]
    )
    assert (
        "collinear slider"
        in description["joint_selection_guide"]["couple_linear_rack_to_rotation"]
    )
    assert "axis" in description["coordinate_system"]["placement"]["rotation"]
    assert "angle_degrees" in description["coordinate_system"]["placement"]["rotation"]
    assert (
        description["capability_inventory"]["kinematic_simulation"]["status"]
        == "supported"
    )
    assert description["capability_inventory"]["exploded_views"]["status"] == (
        "supported"
    )
    assert (
        description["capability_inventory"]["bills_of_materials"]["status"]
        == "supported"
    )
    assert (
        "exploded views"
        not in description["capability_inventory"]["not_yet_provider_exposed"]
    )
    assert description["capability_inventory"]["not_yet_provider_exposed"] == []
    assert (
        "no separate add-column"
        in description["bills_of_materials"]["single_operation_rule"]
    )
    assert (
        "available_occurrence_paths" in description["bills_of_materials"]["inspection"]
    )
    assert description["publication_contract"]["native_types"]["bom"].startswith(
        "stable frozen Assembly::BomObject"
    )
    assert description["units"]["angular_motion_formula"] == "radians"
    assert description["units"]["linear_motion_formula"] == "millimetres"
    assert any(
        pattern["goal"] == "joint to a nested occurrence in a flexible subassembly"
        for pattern in description["recommended_patterns"]
    )
    for pattern in description["recommended_patterns"]:
        domains.validate_program_source(pattern["source"])

    def reference(name: str) -> dict[str, str]:
        return {"document_uid": "document", "object_name": name}

    base = api.component(reference("BaseSource"), grounded=True, label="Base")
    arm = api.component(
        reference("ArmSource"),
        placement={"position": [0, 0, 20], "rotation": [0, 0, 0, 2]},
        label="Arm",
    )
    hinge = api.joint(
        "revolute",
        api.connector(base, "Face1"),
        api.connector(arm, {"type": "exact_subelement", "subelement": "Face2"}),
        angle_limits_degrees=[-90, 90],
        label="Hinge",
    )
    model = api.assembly([base, arm], [hinge], label="Robot Arm")
    diagnostics = api.solve(model)
    drive = api.motion(hinge, "initialValue + pi/2*time")
    simulation = api.simulation(
        model,
        [drive],
        end_time_s=2,
        time_step_s=0.1,
    )
    exploded = api.exploded_view(
        model,
        [
            {"components": [arm], "transform": [0, 0, 40]},
            {"components": [base, arm], "radial_distance_mm": 15},
        ],
        label="Service View",
    )
    bill = api.bill_of_materials(
        model,
        columns=[
            "index",
            "name",
            "quantity",
            {"property": "PartNumber", "heading": "Part Number"},
            {"heading": "Description"},
        ],
        row_overrides=[
            {
                "occurrence_path": "Arm",
                "values": {"Description": "Moving link"},
            }
        ],
        label="Service BOM",
    )

    assert base.properties["grounded"] is True
    assert arm.properties["placement"]["rotation"] == (0.0, 0.0, 0.0, 1.0)
    assert model.properties["components"] == (base, arm)
    assert model.properties["joints"] == (hinge,)
    assert diagnostics.arguments == (model,)
    assert drive.arguments == (hinge,)
    assert drive.properties["motion_type"] == "angular"
    assert simulation.arguments == (model,)
    assert simulation.properties["motions"] == (drive,)
    assert simulation.properties["estimated_frame_limit"] == 22
    assert exploded.arguments == (model,)
    assert exploded.properties["moves"][0]["kind"] == "normal"
    assert exploded.properties["moves"][0]["components"] == (arm,)
    assert exploded.properties["moves"][0]["transform"]["position"] == (
        0.0,
        0.0,
        40.0,
    )
    assert exploded.properties["moves"][1]["kind"] == "radial"
    assert exploded.properties["moves"][1]["radial_distance_mm"] == 15.0
    assert bill.arguments == (model,)
    assert bill.output_type == "bom"
    assert [dict(column) for column in bill.properties["columns"]] == [
        {
            "kind": "builtin",
            "key": "index",
            "heading": "Index",
            "native_name": "Index",
        },
        {
            "kind": "builtin",
            "key": "name",
            "heading": "Name",
            "native_name": "Name",
        },
        {
            "kind": "builtin",
            "key": "quantity",
            "heading": "Quantity",
            "native_name": "Quantity",
        },
        {
            "kind": "property",
            "property": "PartNumber",
            "heading": "Part Number",
            "native_name": ".PartNumber",
        },
        {
            "kind": "custom",
            "heading": "Description",
            "native_name": "Description",
        },
    ]
    assert [
        {
            "occurrence_path": str(item["occurrence_path"]),
            "values": dict(item["values"]),
        }
        for item in bill.properties["row_overrides"]
    ] == [
        {
            "occurrence_path": "Arm",
            "values": {"Description": "Moving link"},
        }
    ]
    with pytest.raises(TypeError):
        model.properties["components"][0] = arm


def test_assembly_api_exposes_native_signed_parameters_anchors_and_open_limits() -> (
    None
):
    from cadex_domain_api import create_domain_api

    pack = domains.get_xscript_pack("AssemblyWorkbench")
    assert pack is not None
    api = create_domain_api(pack.domain, pack.api_exports, pack.output_types)

    def reference(name: str) -> dict[str, str]:
        return {"document_uid": "document", "object_name": name}

    first = api.component(
        reference("First"),
        placement={
            "position": [1, 2, 3],
            "axis": [0, 0, 2],
            "angle_degrees": 90,
        },
    )
    second = api.component(reference("Second"))
    rotation = first.properties["placement"]["rotation"]
    assert tuple(rotation) == pytest.approx((0.0, 0.0, 2**-0.5, 2**-0.5))

    anchored = api.connector(first, "Edge1", anchor="Vertex1")
    assert anchored.properties["anchor"] == "Vertex1"
    assert anchored.properties["selection"] == {
        "type": "exact_subelement",
        "subelement": "Edge1",
    }

    slider = api.joint(
        "slider",
        api.connector(first),
        api.connector(second),
        length_limits_mm={"minimum": None, "maximum": 25},
    )
    revolute = api.joint(
        "revolute",
        api.connector(first),
        api.connector(second),
        angle_limits_degrees=[-45, None],
    )
    distance = api.joint(
        "distance",
        api.connector(first),
        api.connector(second),
        distance_mm=-8,
    )
    rack = api.joint(
        "rack_pinion",
        api.connector(first),
        api.connector(second),
        pitch_radius_mm=-4,
    )
    screw = api.joint(
        "screw",
        api.connector(first),
        api.connector(second),
        thread_pitch_mm=-2,
    )

    assert slider.properties["length_limits_mm"] == (None, 25.0)
    assert revolute.properties["angle_limits_degrees"] == (-45.0, None)
    assert distance.properties["parameters"]["distance_mm"] == -8.0
    assert rack.properties["parameters"]["pitch_radius_mm"] == -4.0
    assert screw.properties["parameters"]["thread_pitch_mm"] == -2.0


def test_assembly_api_rejects_ambiguous_graphs_and_wrong_joint_parameters() -> None:
    from cadex_domain_api import create_domain_api

    pack = domains.get_xscript_pack("AssemblyWorkbench")
    assert pack is not None
    api = create_domain_api(pack.domain, pack.api_exports, pack.output_types)

    def reference(name: str) -> dict[str, str]:
        return {"document_uid": "document", "object_name": name}

    first = api.component(reference("First"))
    second = api.component(reference("Second"))

    with pytest.raises(ValueError, match=r"api\.component.*source"):
        api.component({"object_name": "First"})
    with pytest.raises(ValueError, match=r"api\.connector.*selection"):
        api.connector(first, "Face0")
    with pytest.raises(ValueError, match=r"api\.connector.*anchor.*exact"):
        api.connector(first, "Face1", anchor="center")
    with pytest.raises(ValueError, match=r"api\.connector.*anchor.*only"):
        api.connector(first, "origin", anchor="Vertex1")
    with pytest.raises(ValueError, match=r"api\.component.*axis.*supplied together"):
        api.component(reference("AxisOnly"), placement={"axis": [0, 0, 1]})
    with pytest.raises(
        ValueError, match=r"api\.component.*rotation cannot be combined"
    ):
        api.component(
            reference("MixedRotation"),
            placement={
                "rotation": [0, 0, 0, 1],
                "axis": [0, 0, 1],
                "angle_degrees": 30,
            },
        )
    with pytest.raises(ValueError, match=r"api\.joint.*different component"):
        api.joint("fixed", api.connector(first), api.connector(first))
    with pytest.raises(ValueError, match=r"api\.joint.*distance_mm.*required"):
        api.joint("distance", api.connector(first), api.connector(second))
    with pytest.raises(ValueError, match=r"api\.joint.*distance_mm.*does not apply"):
        api.joint(
            "revolute",
            api.connector(first),
            api.connector(second),
            distance_mm=2,
        )
    with pytest.raises(ValueError, match=r"api\.joint.*length_limits_mm"):
        api.joint(
            "revolute",
            api.connector(first),
            api.connector(second),
            length_limits_mm=[0, 5],
        )
    with pytest.raises(ValueError, match=r"api\.joint.*length_limits_mm.*at least one"):
        api.joint(
            "slider",
            api.connector(first),
            api.connector(second),
            length_limits_mm=[None, None],
        )
    with pytest.raises(ValueError, match=r"api\.joint.*pitch_radius_mm.*non-zero"):
        api.joint(
            "rack_pinion",
            api.connector(first),
            api.connector(second),
            pitch_radius_mm=0,
        )
    with pytest.raises(ValueError, match=r"api\.joint.*radius1_mm.*greater than"):
        api.joint(
            "gears",
            api.connector(first),
            api.connector(second),
            radius1_mm=-1,
            radius2_mm=2,
        )
    joint = api.joint("fixed", api.connector(first), api.connector(second))
    third = api.component(reference("Third"))
    with pytest.raises(ValueError, match=r"api\.assembly.*not listed"):
        api.assembly([first, third], [joint])
    with pytest.raises(ValueError, match=r"api\.assembly.*same graph value"):
        api.assembly([first, first])

    revolute = api.joint("revolute", api.connector(first), api.connector(second))
    slider = api.joint("slider", api.connector(first), api.connector(second))
    fixed = api.joint("fixed", api.connector(first), api.connector(second))
    cylindrical = api.joint("cylindrical", api.connector(first), api.connector(second))
    mechanism = api.assembly([first, second], [revolute])
    drive = api.motion(revolute, "initialValue + pi/2*time")
    assert drive.properties["formula"] == "initialValue + pi/2*time"
    assert (
        api.motion(slider, "initialValue + 10*time").properties["motion_type"]
        == "linear"
    )
    with pytest.raises(ValueError, match=r"api\.motion.*joint.*supported only"):
        api.motion(fixed, "time")
    with pytest.raises(ValueError, match=r"api\.motion.*cylindrical.*explicit"):
        api.motion(cylindrical, "time")
    with pytest.raises(ValueError, match=r"api\.motion.*motion_type"):
        api.motion(revolute, "time", motion_type="linear")
    for formula in (
        "__import__('os')",
        "time.real",
        "sqrt(time)",
        "[time]",
    ):
        with pytest.raises(ValueError, match=r"api\.motion.*formula"):
            api.motion(revolute, formula)
    with pytest.raises(ValueError, match=r"api\.simulation.*same graph value"):
        api.simulation(mechanism, [drive, drive])
    with pytest.raises(ValueError, match=r"api\.simulation.*greater than"):
        api.simulation(mechanism, [drive], start_time_s=1, end_time_s=1)
    with pytest.raises(ValueError, match=r"api\.simulation.*10000 native frames"):
        api.simulation(mechanism, [drive], end_time_s=100, time_step_s=0.001)
    with pytest.raises(ValueError, match=r"api\.exploded_view.*1 through 64"):
        api.exploded_view(mechanism, [])
    with pytest.raises(ValueError, match=r"api\.exploded_view.*exactly one"):
        api.exploded_view(mechanism, [{"components": [first]}])
    with pytest.raises(ValueError, match=r"api\.exploded_view.*exactly one"):
        api.exploded_view(
            mechanism,
            [
                {
                    "components": [first],
                    "transform": [0, 0, 1],
                    "radial_distance_mm": 2,
                }
            ],
        )
    with pytest.raises(ValueError, match=r"api\.exploded_view.*unknown keys"):
        api.exploded_view(
            mechanism,
            [{"components": [first], "transform": [0, 0, 1], "distance": 2}],
        )
    with pytest.raises(ValueError, match=r"api\.exploded_view.*same graph value"):
        api.exploded_view(
            mechanism,
            [{"components": [first, first], "transform": [0, 0, 1]}],
        )
    foreign = api.component(reference("Foreign"))
    with pytest.raises(ValueError, match=r"api\.exploded_view.*not listed"):
        api.exploded_view(
            mechanism,
            [{"components": [foreign], "transform": [0, 0, 1]}],
        )
    with pytest.raises(ValueError, match=r"api\.exploded_view.*translate or rotate"):
        api.exploded_view(
            mechanism,
            [{"components": [first], "transform": [0, 0, 0]}],
        )
    with pytest.raises(ValueError, match=r"api\.exploded_view.*greater than"):
        api.exploded_view(
            mechanism,
            [{"components": [first], "radial_distance_mm": 0}],
        )
    with pytest.raises(ValueError, match=r"api\.bill_of_materials.*include the 'name'"):
        api.bill_of_materials(mechanism, columns=["quantity"])
    with pytest.raises(
        ValueError,
        match=r"api\.bill_of_materials.*duplicates column identity.*keep one best version",
    ):
        api.bill_of_materials(
            mechanism,
            columns=[
                "name",
                {"property": "PartNumber", "heading": "Part Number"},
                {"property": "PartNumber", "heading": "PN"},
            ],
        )
    with pytest.raises(
        ValueError, match=r"api\.bill_of_materials.*undeclared custom headings"
    ):
        api.bill_of_materials(
            mechanism,
            columns=["name", {"heading": "Description"}],
            row_overrides=[{"occurrence_path": "First", "values": {"Notes": "Base"}}],
        )
    with pytest.raises(ValueError, match=r"api\.bill_of_materials.*is duplicated"):
        api.bill_of_materials(
            mechanism,
            columns=["name", {"heading": "Description"}],
            row_overrides=[
                {"occurrence_path": "First", "values": {"Description": "Base"}},
                {"occurrence_path": "First", "values": {"Description": "Fixed"}},
            ],
        )
    with pytest.raises(ValueError, match=r"api\.bill_of_materials.*assembly"):
        api.bill_of_materials(first)


def test_assembly_bom_planner_keeps_model_paths_exact_and_actionable() -> None:
    from CadexAssemblyBOM import AssemblyBOMError, plan_assembly_bom

    root_identity = {"document_uid": "source-document", "object_name": "Module"}
    gear_identity = {"document_uid": "source-document", "object_name": "Gear"}
    hierarchy = {
        "schema": "cadex-assembly-source-hierarchy-v1",
        "root_node_id": "node-module",
        "nodes": [
            {
                "node_id": "node-module",
                "identity": root_identity,
                "kind": "assembly",
                "label": "Drive Module",
                "document_file_name": "drive-module.FCStd",
                "bom_properties": [
                    {
                        "name": "PartNumber",
                        "property_type": "App::PropertyString",
                        "kind": "string",
                        "value": "MOD-001",
                    }
                ],
                "occurrences": [
                    {
                        "name": "GearLeft",
                        "source_node_id": "node-gear",
                        "scale": 1.0,
                    },
                    {
                        "name": "GearRight",
                        "source_node_id": "node-gear",
                        "scale": 1.0,
                    },
                ],
            },
            {
                "node_id": "node-gear",
                "identity": gear_identity,
                "kind": "shape",
                "label": "Gear",
                "document_file_name": "gear.FCStd",
                "bom_properties": [
                    {
                        "name": "PartNumber",
                        "property_type": "App::PropertyString",
                        "kind": "string",
                        "value": "GEAR-020",
                    }
                ],
                "occurrences": [],
            },
        ],
    }
    component_sources = [
        {
            "output_name": "Module",
            "reference": {
                **root_identity,
                "assembly_hierarchy": hierarchy,
            },
        }
    ]
    columns = [
        {
            "kind": "builtin",
            "key": "index",
            "heading": "Index",
            "native_name": "Index",
        },
        {
            "kind": "builtin",
            "key": "name",
            "heading": "Name",
            "native_name": "Name",
        },
        {
            "kind": "builtin",
            "key": "quantity",
            "heading": "Quantity",
            "native_name": "Quantity",
        },
        {
            "kind": "property",
            "property": "PartNumber",
            "heading": "Part Number",
            "native_name": ".PartNumber",
        },
        {
            "kind": "custom",
            "heading": "Description",
            "native_name": "Description",
        },
    ]
    contract = plan_assembly_bom(
        component_sources,
        columns=columns,
        detail_subassemblies=True,
        detail_parts=True,
        only_parts=False,
        row_overrides=[
            {
                "occurrence_path": "Module/GearLeft",
                "values": {"Description": "Matched gear"},
            }
        ],
    )
    assert contract["row_count"] == 2
    assert contract["used_range"] == ["A1", "E3"]
    assert contract["rows"][0]["occurrence_paths"] == ["Module"]
    assert contract["rows"][1]["occurrence_paths"] == [
        "Module/GearLeft",
        "Module/GearRight",
    ]
    assert contract["rows"][1]["cells"] == {
        "Index": "1.1",
        "Name": "Gear",
        "Quantity": "2",
        "Part Number": "GEAR-020",
        "Description": "Matched gear",
    }
    assert len(contract["table_sha256"]) == 64
    assert contract == plan_assembly_bom(
        component_sources,
        columns=columns,
        detail_subassemblies=True,
        detail_parts=True,
        only_parts=False,
        row_overrides=[
            {
                "occurrence_path": "Module/GearLeft",
                "values": {"Description": "Matched gear"},
            }
        ],
    )

    with pytest.raises(AssemblyBOMError) as conflict:
        plan_assembly_bom(
            component_sources,
            columns=columns,
            detail_subassemblies=True,
            detail_parts=True,
            only_parts=False,
            row_overrides=[
                {
                    "occurrence_path": "Module/GearLeft",
                    "values": {"Description": "Left gear"},
                },
                {
                    "occurrence_path": "Module/GearRight",
                    "values": {"Description": "Right gear"},
                },
            ],
        )
    assert conflict.value.details["stage"] == "bom_row_overrides"
    assert conflict.value.details["heading"] == "Description"
    assert conflict.value.details["conflicting_occurrence_paths"] == [
        "Module/GearLeft",
        "Module/GearRight",
    ]
    assert "omit 'quantity'" in conflict.value.details["correction"]

    with pytest.raises(AssemblyBOMError) as unknown:
        plan_assembly_bom(
            component_sources,
            columns=columns,
            detail_subassemblies=True,
            detail_parts=True,
            only_parts=False,
            row_overrides=[
                {
                    "occurrence_path": "Module/GearCenter",
                    "values": {"Description": "Center gear"},
                }
            ],
        )
    assert unknown.value.details["requested_path"] == "Module/GearCenter"
    assert unknown.value.details["available_occurrence_paths"] == [
        "Module",
        "Module/GearLeft",
        "Module/GearRight",
    ]
    assert unknown.value.details["settings"] == {
        "detail_subassemblies": True,
        "detail_parts": True,
        "only_parts": False,
    }

    separate_columns = [column for column in columns if column.get("key") != "quantity"]
    separate = plan_assembly_bom(
        component_sources,
        columns=separate_columns,
        detail_subassemblies=True,
        detail_parts=True,
        only_parts=False,
        row_overrides=[
            {
                "occurrence_path": "Module/GearLeft",
                "values": {"Description": "Left gear"},
            },
            {
                "occurrence_path": "Module/GearRight",
                "values": {"Description": "Right gear"},
            },
        ],
    )
    assert [row["occurrence_paths"] for row in separate["rows"]] == [
        ["Module"],
        ["Module/GearLeft"],
        ["Module/GearRight"],
    ]
    assert [row["cells"]["Description"] for row in separate["rows"][1:]] == [
        "Left gear",
        "Right gear",
    ]

    only_containers = plan_assembly_bom(
        component_sources,
        columns=columns,
        detail_subassemblies=True,
        detail_parts=True,
        only_parts=True,
        row_overrides=[],
    )
    assert [row["occurrence_paths"] for row in only_containers["rows"]] == [["Module"]]

    with pytest.raises(AssemblyBOMError) as unavailable_hierarchy:
        plan_assembly_bom(
            [
                {
                    "output_name": "Module",
                    "reference": {
                        **root_identity,
                        "source_kind": "assembly",
                        "label": "Drive Module",
                        "document_file_name": "drive-module.FCStd",
                        "bom_properties": [],
                    },
                }
            ],
            columns=columns,
            detail_subassemblies=True,
            detail_parts=True,
            only_parts=False,
            row_overrides=[],
        )
    assert unavailable_hierarchy.value.details["stage"] == "bom_source_hierarchy"
    assert unavailable_hierarchy.value.details["occurrence_path"] == "Module"
    assert (
        "detail_subassemblies=False"
        in unavailable_hierarchy.value.details["correction"]
    )

    with pytest.raises(AssemblyBOMError) as oversized:
        plan_assembly_bom(
            [
                {
                    "output_name": f"Component{index:03d}",
                    "reference": {
                        "document_uid": "source-document",
                        "object_name": f"Source{index:03d}",
                        "source_kind": "shape",
                        "label": "X" * 4096,
                        "document_file_name": "large-module.FCStd",
                        "bom_properties": [],
                    },
                }
                for index in range(100)
            ],
            columns=[columns[1]],
            detail_subassemblies=False,
            detail_parts=False,
            only_parts=False,
            row_overrides=[],
        )
    assert oversized.value.details["stage"] == "bom_budget"
    assert (
        oversized.value.details["observed_contract_bytes"]
        > (oversized.value.details["maximum_contract_bytes"])
    )
    assert "split the design" in oversized.value.details["correction"]


def test_assembly_occurrence_global_placement_failure_is_never_silently_local() -> None:
    from cadex_assembly_worker import (
        AssemblyCandidateError,
        _global_placement_fact,
    )

    class BrokenOccurrence:
        Name = "NestedGear"

        @staticmethod
        def getGlobalPlacement():
            raise RuntimeError("native placement unavailable")

    with pytest.raises(AssemblyCandidateError) as failure:
        _global_placement_fact(
            BrokenOccurrence(),
            context="component output 'Drive' occurrence 'Core/Gear'",
        )
    assert failure.value.details["stage"] == "assembly_occurrence_placement"
    assert failure.value.details["native_object"] == "NestedGear"
    assert "same stable occurrence_path" in failure.value.details["correction"]


def test_sketcher_api_is_explicit_complete_and_generated_from_runtime() -> None:
    from cadex_domain_api import create_domain_api

    pack = domains.get_xscript_pack("SketcherWorkbench")
    assert pack is not None
    api = create_domain_api(pack.domain, pack.api_exports, pack.output_types)
    adapter = domains.get_domain_adapter(pack.domain)
    assert adapter is not None
    description = adapter.describe_api()

    assert description["api_contract"] == "cadex-xscript-sketcher-api-v1"
    assert tuple(api.exported_names) == pack.api_exports
    exports = description["runtime_exports"]
    assert [item["name"] for item in exports] == list(pack.api_exports)
    assert len(exports) == 12
    assert all(item["description"] for item in exports)
    assert all(
        "*args" not in item["signature"] and "**properties" not in item["signature"]
        for item in exports
    )
    assert len(json.dumps(description, separators=(",", ":"))) < 32 * 1024
    selection = description["operation_selection"]
    assert selection["any_geometric_dimensional_or_annotation_relation"].startswith(
        "api.constraint"
    )
    assert "one api.constraint operation" in selection["redundancy_contract"]
    assert "no model-facing rectangle" in selection["redundancy_contract"]
    assert description["constraint_forms"]["coincident"] == "[point, point]"
    assert "value required" in description["constraint_forms"]["angle_via_point"]
    assert description["model_verification_contract"]["underconstrained"].endswith(
        "Never apply every suggestion in one edit."
    )
    assert "cannot switch workbench" in description["workbench_handoffs"]["rule"]
    assert set(description["geometry"]) >= {
        "point",
        "line",
        "arc",
        "circle",
        "ellipse",
        "elliptic_arc",
        "hyperbolic_arc",
        "parabolic_arc",
        "bspline",
        "external_geometry",
        "construction",
    }
    external_contract = description["external_geometry_contract"]
    assert "x-cadex-reference" in external_contract["input"]
    assert external_contract["regenerating_selection"]["schema"] == {
        "type": "published_interface",
        "interface_name": "DatumEdge",
    }
    assert "-3, -4" in external_contract["identity"]
    internal = description["constraints"]["internal_alignment"]
    assert set(internal["hyperbola"]) == {
        "hyperbola_major_diameter",
        "hyperbola_minor_diameter",
        "hyperbola_focus",
    }
    assert set(internal["parabola"]) == {
        "parabola_focus",
        "parabola_focal_axis",
    }
    rectangle_source = description["recommended_patterns"][0]["source"]
    domains.validate_program_source(rectangle_source)
    assert "constraints = [" in rectangle_source
    assert "# Add coincidence" not in rectangle_source
    external_source = description["recommended_patterns"][2]["source"]
    domains.validate_program_source(external_source)
    assert "api.external_geometry" in external_source


def test_sketcher_api_reports_exact_source_errors_before_native_execution() -> None:
    from cadex_domain_api import create_domain_api

    pack = domains.get_xscript_pack("SketcherWorkbench")
    assert pack is not None
    api = create_domain_api(pack.domain, pack.api_exports, pack.output_types)
    line = api.line([0, 0], [5, 0])
    circle = api.circle([0, 0], 2)

    cases = (
        (lambda: api.line([0, 0], [0, 0]), r"api\.line.*end"),
        (
            lambda: api.elliptic_arc([0, 0], 2, 3, 0, 1),
            r"api\.elliptic_arc.*major_radius",
        ),
        (
            lambda: api.hyperbolic_arc([0, 0], 2, 1, 0, 21),
            r"api\.hyperbolic_arc.*start_parameter/end_parameter",
        ),
        (
            lambda: api.constraint("horizontal", [circle]),
            r"api\.constraint.*line geometry",
        ),
        (
            lambda: api.constraint("coincident", [line, circle]),
            r"api\.constraint.*explicit points",
        ),
        (
            lambda: api.constraint(
                "angle_via_point",
                [line, circle, circle],
                value=30,
            ),
            r"api\.constraint.*angle_via_point.*explicit point",
        ),
        (
            lambda: api.constraint("group", [circle]),
            r"api\.constraint.*entities\[0\]",
        ),
        (
            lambda: api.constraint(
                "radius",
                [circle],
                value=2,
                driving=False,
                expression="2 mm",
            ),
            r"api\.constraint.*expression.*reference",
        ),
        (
            lambda: api.external_geometry(
                {"document_uid": "doc", "object_name": "Source"},
                "Face1",
            ),
            r"api\.external_geometry.*selection\.subelements.*EdgeN or VertexN",
        ),
    )
    for invoke, pattern in cases:
        with pytest.raises(ValueError, match=pattern):
            invoke()

    control = api.circle([0, 0], 0.5, construction=True)
    spline = api.bspline(
        [[0, 0], [2, 3], [4, 2], [6, 0]],
        degree=3,
        knots=[0, 1],
        multiplicities=[4, 4],
    )
    with pytest.raises(ValueError, match=r"api\.constraint.*internal_index.*0-3"):
        api.constraint(
            "internal_alignment",
            [{"geometry": control, "point": "center"}, spline],
            alignment="bspline_control_point",
            internal_index=4,
        )
    other = api.line([0, 0], [1, 0])
    foreign_constraint = api.constraint("horizontal", [other])
    with pytest.raises(ValueError, match=r"api\.sketch.*not listed"):
        api.sketch([line], [foreign_constraint])


def test_sketcher_live_publication_boundary_never_solves_or_recomputes() -> None:
    import CadexScriptedDomainPublication as publication
    from cadex_sketcher_worker import populate_sketch_without_solving

    configure_source = inspect.getsource(publication._configure_sketch)
    populate_source = inspect.getsource(populate_sketch_without_solving)
    for source in (configure_source, populate_source):
        assert ".solve(" not in source
        assert ".recompute(" not in source
        assert "subprocess" not in source
    assert "addConstraint(native_constraints)" in populate_source
    assert populate_source.count("addConstraint(") == 1


def test_rollback_property_digest_ignores_zip_timestamp_not_content() -> None:
    from io import BytesIO
    import zipfile

    import CadexScriptedDomainPublication as publication

    def persisted(timestamp: tuple[int, int, int, int, int, int], text: str) -> bytes:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            info = zipfile.ZipInfo("Persistence.xml", timestamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, text.encode("utf-8"))
        return buffer.getvalue()

    first = persisted((2024, 1, 1, 0, 0, 0), "<Property value='3 mm'/>")
    later = persisted((2026, 7, 19, 12, 30, 0), "<Property value='3 mm'/>")
    changed = persisted((2026, 7, 19, 12, 30, 0), "<Property value='4 mm'/>")
    assert publication._property_content_sha256(first) == (
        publication._property_content_sha256(later)
    )
    assert publication._property_content_sha256(first) != (
        publication._property_content_sha256(changed)
    )


def test_reference_revision_binds_assembly_semantic_connector_contract() -> None:
    base = {
        "document_uid": "document",
        "object_name": "Arm",
        "brep_sha256": "a" * 64,
    }
    geometry_only = domains.program_revision_with_references(
        contract_revision="b" * 64,
        references=[base],
    )
    first_contract = domains.program_revision_with_references(
        contract_revision="b" * 64,
        references=[{**base, "reference_contract_sha256": "c" * 64}],
    )
    second_contract = domains.program_revision_with_references(
        contract_revision="b" * 64,
        references=[{**base, "reference_contract_sha256": "d" * 64}],
    )

    assert len({geometry_only, first_contract, second_contract}) == 3
    with pytest.raises(ValueError, match="reference contracts require a SHA-256"):
        domains.program_revision_with_references(
            contract_revision="b" * 64,
            references=[{**base, "reference_contract_sha256": "not-a-digest"}],
        )


def test_domain_api_graph_and_worker_inputs_are_deeply_immutable() -> None:
    from cadex_domain_api import create_domain_api
    from cadex_domain_worker import _execute_source, _immutable_input

    pack = domains.get_xscript_pack("PartWorkbench")
    assert pack is not None
    api = create_domain_api(pack.domain, pack.api_exports, pack.output_types)
    value = api.box(2, 3, 4, origin=[1, 2, 3])

    with pytest.raises(TypeError):
        value.properties["origin"] = (9, 9, 9)
    with pytest.raises(TypeError):
        value.properties["origin"][0] = 9
    with pytest.raises((AttributeError, TypeError)):
        api.box = None

    inputs = _immutable_input(
        {
            "dimensions": [2, 3, 4],
            "source": {"document_uid": "doc", "object_name": "Body"},
        }
    )
    with pytest.raises(TypeError):
        inputs["dimensions"] = (1, 1, 1)
    with pytest.raises(TypeError):
        inputs["source"]["object_name"] = "Other"

    with pytest.raises(TypeError, match="does not support item assignment"):
        _execute_source(
            source="inputs['dimensions'][0] = 99\nresult = {}",
            document_name="ImmutableFixture",
            document_objects=[],
            inputs={"dimensions": [2, 3, 4]},
            api=api,
            max_operations=1_000,
            max_seconds=1.0,
        )
    with pytest.raises(TypeError, match="does not support item assignment"):
        _execute_source(
            source=(
                "value = x.box(1, 2, 3, origin=[0, 0, 0])\n"
                "value.properties['origin'][0] = 99\n"
                "result = {'Body': value}"
            ),
            document_name="ImmutableFixture",
            document_objects=[],
            inputs={},
            api=api,
            max_operations=1_000,
            max_seconds=1.0,
        )


def test_source_operation_budget_excludes_trusted_domain_api_frames() -> None:
    from cadex_domain_worker import _execute_source

    class TrustedAPI:
        @staticmethod
        def build() -> int:
            total = 0
            for value in range(100_000):
                total += value % 7
            return total

    result, _stdout, budget = _execute_source(
        source="value = x.build()\nresult = {'Value': value}\n",
        document_name="BudgetFixture",
        document_objects=[],
        inputs={},
        api=TrustedAPI(),
        max_operations=10,
        max_seconds=1.0,
    )
    assert result["Value"] > 0
    assert 1 <= budget["operations"] <= 10

    with pytest.raises(RuntimeError, match=r"exceeded its 10 operation budget"):
        _execute_source(
            source=(
                "value = 0\n"
                "for item in range(100):\n"
                "    value += item\n"
                "result = {'Value': value}\n"
            ),
            document_name="BudgetFixture",
            document_objects=[],
            inputs={},
            api=TrustedAPI(),
            max_operations=10,
            max_seconds=1.0,
        )


def test_domain_context_merges_live_identity_without_losing_persisted_facts(
    tmp_path: Path,
) -> None:
    program_id = "a" * 32
    directory = tmp_path / "xscript" / "part" / program_id
    directory.mkdir(parents=True)
    (directory / "program.json").write_text(
        json.dumps(
            {
                "schema": domains.PROGRAM_SCHEMA,
                "version": domains.PROGRAM_VERSION,
                "program_id": program_id,
                "domain": "part",
                "workbench": "PartWorkbench",
                "label": "Context fixture",
                "source": "result = {}",
                "input_schema": {},
                "inputs": {},
                "expected_outputs": [{"name": "Body", "type": "solid"}],
                "working_revision": "b" * 64,
                "accepted_revision": "b" * 64,
                "live_outputs": {
                    "Body": {
                        "object_name": "OldBody",
                        "label": "Old label",
                        "type_id": "Part::Feature",
                        "output_type": "solid",
                        "facts": {"shape_type": "Solid", "volume_mm3": 24.0},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    context = domains.complete_domain_context(
        {
            "_cadex_deferred_xscript_domain_context": True,
            "domain": "part",
            "workbench": "PartWorkbench",
            "surface_id": "xscript:part:v2",
            "project_root": str(tmp_path),
            "contract": {},
            "native_programs": [
                {
                    "program_id": program_id,
                    "domain": "part",
                    "workbench": "PartWorkbench",
                    "working_revision": "b" * 64,
                    "live_outputs": [
                        {
                            "name": "Body",
                            "object_name": "LiveBody",
                            "label": "Live label",
                            "type_id": "Part::Feature",
                        }
                    ],
                }
            ],
        }
    )
    output = context["programs"][0]["live_outputs"]["Body"]
    assert output["object_name"] == "LiveBody"
    assert output["label"] == "Live label"
    assert output["output_type"] == "solid"
    assert output["facts"] == {"shape_type": "Solid", "volume_mm3": 24.0}


def test_domain_context_is_aggregate_bounded_and_points_to_exact_inspection(
    tmp_path: Path,
) -> None:
    target_program_id = f"{1:032x}"
    root = tmp_path / "xscript" / "part"
    for index in range(35):
        program_id = f"{index + 1:032x}"
        directory = root / program_id
        directory.mkdir(parents=True)
        manifest = {
            "schema": domains.PROGRAM_SCHEMA,
            "version": domains.PROGRAM_VERSION,
            "program_id": program_id,
            "domain": "part",
            "workbench": "PartWorkbench",
            "label": f"Program {index + 1}",
            "source": "result = {}",
            "input_schema": {},
            "inputs": {},
            "expected_outputs": [{"name": "Body", "type": "solid"}],
            "working_revision": "b" * 64,
            "accepted_revision": "b" * 64,
            "live_outputs": {},
        }
        if program_id == target_program_id:
            manifest["inputs"] = {"values": ["x" * 1_000 for _ in range(20)]}
            manifest["resolved_references"] = [
                {
                    "document_uid": "document",
                    "object_name": f"Source{reference_index}",
                    "facts": {
                        "shape_type": "Solid",
                        "face_details": [{"index": 1}],
                        "edge_details": [{"index": 1}],
                    },
                }
                for reference_index in range(20)
            ]
            manifest["live_outputs"] = {
                "Body": {
                    "object_name": "Body",
                    "output_type": "solid",
                    "facts": {
                        "shape_type": "Solid",
                        "faces": 6,
                        "edges": 12,
                        "face_details": [{"index": 1}],
                        "edge_details": [{"index": 1}],
                    },
                }
            }
        (directory / "program.json").write_text(json.dumps(manifest), encoding="utf-8")

    context = domains.complete_domain_context(
        {
            "_cadex_deferred_xscript_domain_context": True,
            "domain": "part",
            "workbench": "PartWorkbench",
            "surface_id": "xscript:part:v2",
            "project_root": str(tmp_path),
            "contract": {},
            "native_program_count": 1,
            "native_programs": [
                {
                    "program_id": target_program_id,
                    "domain": "part",
                    "workbench": "PartWorkbench",
                    "live_outputs": [],
                }
            ],
        }
    )
    assert context["program_limit"] == domains.MAX_DOMAIN_CONTEXT_PROGRAMS == 32
    assert context["program_count"] == 35
    assert len(context["programs"]) == 32
    assert context["programs_truncated"] is True
    assert context["programs_omitted"] == 3
    target = next(
        item for item in context["programs"] if item["program_id"] == target_program_id
    )
    assert target["inputs"]["_cadex_context_omitted"] is True
    assert len(target["resolved_references"]) == 16
    assert target["resolved_references_omitted"] == 4
    output_facts = target["live_outputs"]["Body"]["facts"]
    assert "face_details" not in output_facts
    assert "edge_details" not in output_facts
    assert output_facts["subelement_details_context_omitted"] is True
    assert "core.inspect" in output_facts["subelement_details_guidance"]


def test_generic_prototype_adapters_cannot_surface_unfinished_domains() -> None:
    for workbench, pack in domains.XSCRIPT_WORKBENCH_PACKS.items():
        if pack.production_ready:
            continue
        adapter = domains.get_domain_adapter(pack.domain)
        assert adapter is not None
        assert adapter.production_ready is False
        available, reason = domains.domain_availability(workbench)
        assert available is False
        assert "production-readiness gate" in reason
        surface = resolve_modeling_surface(workbench, "xscript")
        assert surface.cad_tool_names == ()
        assert surface.tool_names == surface.core_tool_names


def test_nested_stable_inputs_are_reauthorized_against_the_live_document() -> None:
    from CadexScriptedRuntime import _validate_stable_references

    captured = {
        "document_uid": "live-document",
        "document_objects": [{"name": "Body"}],
    }
    _validate_stable_references(
        {
            "source": {
                "document_uid": "live-document",
                "object_name": "Body",
            }
        },
        captured,
        "inputs",
    )
    with pytest.raises(ValueError, match="different document uid"):
        _validate_stable_references(
            {
                "source": {
                    "document_uid": "stale-document",
                    "object_name": "Body",
                }
            },
            captured,
            "inputs",
        )


def test_domain_publication_has_no_worker_or_artifact_io_fallback() -> None:
    import CadexScriptedDomainPublication as publication

    source = inspect.getsource(publication)
    for forbidden in (
        "subprocess.",
        "run_process(",
        ".wait(",
        "read_text(",
        "write_text(",
        "importBrep(",
        "exportBrep(",
        ".recompute(",
        ".solve(",
    ):
        assert forbidden not in source


def test_part_reference_capture_only_detaches_live_shapes() -> None:
    import CadexScriptedRuntime as runtime

    source = inspect.getsource(runtime.capture_reference_inputs)
    for forbidden in (
        "exportBrep(",
        "importBrep(",
        "part_shape_facts(",
        "read_text(",
        "write_text(",
        "subprocess.",
        ".wait(",
    ):
        assert forbidden not in source
    assert ".copy()" in source


@pytest.mark.parametrize(
    ("domain", "domain_files"),
    (
        ("part", {"cadex_part_api.py", "cadex_part_worker.py"}),
        (
            "assembly",
            {
                "CadexAssemblyBOM.py",
                "cadex_assembly_api.py",
                "cadex_assembly_worker.py",
                "cadex_part_worker.py",
            },
        ),
        (
            "sketcher",
            {
                "cadex_sketcher_api.py",
                "cadex_sketcher_worker.py",
                "cadex_part_worker.py",
            },
        ),
    ),
)
def test_worker_staging_contains_only_the_active_domain_bundle(
    tmp_path: Path,
    domain: str,
    domain_files: set[str],
) -> None:
    import CadexScriptedRuntime as runtime

    staging = tmp_path / domain
    staging.mkdir()
    copied = runtime._stage_worker_bundle(
        Path(runtime.__file__).resolve().parent,
        staging,
        domain,
    )
    expected = {"worker.py", "cadex_domain_api.py", *domain_files}
    assert set(copied) == expected
    assert {path.name for path in staging.iterdir()} == expected
    assert not any(
        path.name.startswith("xscript_")
        and path.name.endswith(("_api.py", "_worker.py"))
        and path.name not in expected
        for path in staging.iterdir()
    )


def test_worker_staging_rejects_an_undeclared_domain(tmp_path: Path) -> None:
    import CadexScriptedRuntime as runtime

    with pytest.raises(ValueError, match="no isolated worker bundle"):
        runtime._stage_worker_bundle(
            Path(runtime.__file__).resolve().parent,
            tmp_path,
            "not-a-domain",
        )


def test_point_artifact_input_schema_is_explicit_and_bounded() -> None:
    schema = {
        "type": "object",
        "properties": {
            "source": {
                "oneOf": [
                    {
                        "type": "object",
                        "x-cadex-reference": True,
                        "properties": {
                            "document_uid": {"type": "string"},
                            "object_name": {"type": "string"},
                        },
                        "required": ["document_uid", "object_name"],
                        "additionalProperties": False,
                    },
                    {
                        "type": "object",
                        "x-cadex-point-artifact": True,
                        "properties": {
                            "artifact_id": {
                                "type": "string",
                                "pattern": "^[0-9a-f]{32}$",
                            }
                        },
                        "required": ["artifact_id"],
                        "additionalProperties": False,
                    },
                ]
            }
        },
        "required": ["source"],
        "additionalProperties": False,
    }
    assert domains.validate_input_schema(schema) == schema
    assert domains.validate_inputs({"source": {"artifact_id": "a" * 32}})
    malformed = json.loads(json.dumps(schema))
    malformed["properties"]["source"]["oneOf"][1]["properties"]["artifact_id"][
        "pattern"
    ] = ".*"
    with pytest.raises(ValueError, match="exact bounded"):
        domains.validate_input_schema(malformed)
    with pytest.raises(ValueError, match="invalid stable artifact"):
        domains.validate_inputs({"source": {"artifact_id": "not-an-id"}})
    with pytest.raises(ValueError, match="only one bounded oneOf"):
        domains.validate_input_schema(
            {
                **schema,
                "anyOf": [{"type": "string"}],
            }
        )


def test_point_artifact_registry_authenticates_guards_and_rolls_back(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import CadexPointArtifacts as artifacts

    source = tmp_path / "source.xyz"
    source.write_text("0 0 0\n1 2 3\n", encoding="utf-8")
    approved = artifacts.approve_point_artifact(tmp_path, source, label="Scan")
    summary = artifacts.point_artifacts_summary(tmp_path)
    assert summary["artifact_count"] == 1
    assert "path" not in summary["artifacts"][0]
    resolved = artifacts.resolve_point_artifacts(tmp_path, [approved["artifact_id"]])[0]
    assert Path(resolved["path"]).is_file()

    program_id = "b" * 32
    program = tmp_path / "xscript" / "points" / program_id
    program.mkdir(parents=True)
    (program / "program.json").write_text(
        json.dumps(
            {
                "program_id": program_id,
                "label": "Uses scan",
                "inputs": {"source": {"artifact_id": approved["artifact_id"]}},
                "working_revision": "c" * 64,
                "accepted_revision": "c" * 64,
                "accepted_contract": {
                    "inputs": {"source": {"artifact_id": approved["artifact_id"]}}
                },
            }
        ),
        encoding="utf-8",
    )
    references = artifacts.point_artifact_program_references(
        tmp_path, approved["artifact_id"]
    )
    assert references[0]["accepted_reference"] is True
    with pytest.raises(ValueError, match="programs reference it"):
        artifacts.remove_point_artifact(tmp_path, approved["artifact_id"])

    (program / "program.json").write_text(
        json.dumps(
            {
                "program_id": program_id,
                "inputs": {},
                "accepted_contract": None,
            }
        ),
        encoding="utf-8",
    )
    original_write = artifacts._write_manifest
    calls = []

    def fail_first_write(project_root, values):
        calls.append(True)
        if len(calls) == 1:
            raise OSError("injected manifest failure")
        return original_write(project_root, values)

    monkeypatch.setattr(artifacts, "_write_manifest", fail_first_write)
    with pytest.raises(OSError, match="injected manifest failure"):
        artifacts.remove_point_artifact(tmp_path, approved["artifact_id"])
    assert artifacts.resolve_point_artifacts(tmp_path, [approved["artifact_id"]])
    monkeypatch.setattr(artifacts, "_write_manifest", original_write)
    removed = artifacts.remove_point_artifact(tmp_path, approved["artifact_id"])
    assert removed["artifact_copy_deleted"] is True
    assert artifacts.point_artifacts_summary(tmp_path)["artifact_count"] == 0


def test_gui_document_observer_marks_xscript_dependencies_stale(monkeypatch) -> None:
    import CadexGui as gui
    import CadexScriptedDomainPublication as publication

    observed = []
    refreshed = []
    source = object()

    def mark(obj, property_name):
        observed.append((obj, property_name))
        return ["DependentOutput"]

    monkeypatch.setattr(publication, "mark_programs_stale_from_source", mark)
    monkeypatch.setattr(
        gui,
        "_schedule_assistant_document_refresh",
        lambda: refreshed.append(True),
    )
    gui._CadexDocumentObserver().slotChangedObject(source, "Shape")
    assert observed == [(source, "Shape")]
    assert refreshed == [True]


def test_gui_document_observer_ignores_properties_restored_from_file(
    monkeypatch,
) -> None:
    import CadexGui as gui
    import CadexScriptedDomainPublication as publication

    observed = []
    monkeypatch.setattr(gui.App, "isRestoring", lambda: True, raising=False)
    monkeypatch.setattr(
        publication,
        "mark_programs_stale_from_source",
        lambda obj, property_name: observed.append((obj, property_name)),
    )

    gui._CadexDocumentObserver().slotChangedObject(object(), "Shape")

    assert observed == []
