# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Global project-surface and XScript architecture contracts (Phase 2.4).

The tool surface is GLOBAL: any workbench with the xscript engine resolves to
the four ``xscript.project.*`` tools plus the core/conversation/file tools.
The per-domain multi-program surface was dissolved (ADR-013); the worker-side
capability APIs (part/partdesign/sketcher/assembly) and the publication
boundary contracts remain and stay pinned here.
"""

from __future__ import annotations

import inspect
import json
import math
from pathlib import Path

import pytest

from CadexModelingSurface import (
    CORE_CONVERSATION_VIEW_TOOLS,
    resolve_modeling_surface,
    validate_surface_names,
)
from CadexTools import SafetyLevel, ToolSpec
import CadexScriptedDomains as domains

PROJECT_TOOL_NAMES = (
    "xscript.project.describe_api",
    "xscript.project.write_script",
    "xscript.project.edit_script",
    "xscript.project.set_params",
)


def test_global_surface_is_project_for_every_workbench() -> None:
    surfaces = [
        resolve_modeling_surface(workbench, "xscript")
        for workbench in (
            *domains.XSCRIPT_WORKBENCH_PACKS,
            None,
            "TestWorkbench",
            "NoneWorkbench",
            "UnknownWorkbench",
        )
    ]
    surface_ids = {surface.surface_id for surface in surfaces}
    assert len(surface_ids) == 1, "The project surface must be global."
    for surface in surfaces:
        assert surface.available is True
        assert surface.unavailable_reason == ""
        assert surface.engine == "xscript"
        assert surface.domain == "project"
        assert surface.cad_tool_names == PROJECT_TOOL_NAMES
        assert set(surface.core_tool_names) == set(CORE_CONVERSATION_VIEW_TOOLS)
        assert "core.inspect" in surface.tool_names
    assert "project-v1-single-script" in surfaces[0].surface_id


def test_project_pack_tool_names_are_the_authority() -> None:
    assert domains.PROJECT_PACK.tool_names == PROJECT_TOOL_NAMES
    # Capability packs are execution contracts only: no tool surface.
    for pack in domains.XSCRIPT_WORKBENCH_PACKS.values():
        assert pack.tool_names == ()


def test_unknown_engine_is_unavailable_and_core_only() -> None:
    for engine in ("", "native", "build123d", "openscad"):
        surface = resolve_modeling_surface("PartWorkbench", engine)
        assert surface.available is False
        assert surface.cad_tool_names == ()
        assert surface.unavailable_reason
        assert set(surface.tool_names) == set(CORE_CONVERSATION_VIEW_TOOLS)


def test_mixed_and_foreign_namespace_surfaces_are_rejected() -> None:
    project = resolve_modeling_surface("PartWorkbench", "xscript")
    native_part_tool = "part.box"
    with pytest.raises(ValueError, match="cannot contain native"):
        validate_surface_names(
            workbench="PartWorkbench",
            engine="xscript",
            names=[*project.tool_names, native_part_tool],
            allowed_names=[*project.tool_names, native_part_tool],
        )
    with pytest.raises(ValueError, match="exactly the project namespace"):
        validate_surface_names(
            workbench="PartWorkbench",
            engine="xscript",
            names=["xscript.part.write_script"],
        )
    validate_surface_names(
        workbench=None,
        engine="xscript",
        names=list(project.tool_names),
        allowed_names=list(project.tool_names),
    )


def test_project_tool_specs_are_exact_and_guarded() -> None:
    specs = {
        spec.name: spec
        for spec in (
            ToolSpec.from_mapping(raw) for raw in domains.project_tool_specs()
        )
    }
    assert tuple(specs) == PROJECT_TOOL_NAMES
    describe = specs["xscript.project.describe_api"]
    assert describe.safety is SafetyLevel.READ
    assert describe.requires_document is False
    for name in PROJECT_TOOL_NAMES[1:]:
        spec = specs[name]
        assert spec.safety is SafetyLevel.SAFE_WRITE
        assert spec.requires_document is True
        revision = spec.parameters["properties"]["expected_revision"]
        assert revision["pattern"] == "^([0-9a-f]{64})?$"
        assert "expected_revision" in spec.parameters["required"]
    source = specs["xscript.project.write_script"].parameters["properties"]["source"]
    assert source["maxLength"] == domains.MAX_SOURCE_BYTES
    replacements = specs["xscript.project.edit_script"].parameters["properties"][
        "replacements"
    ]
    assert replacements["items"]["required"] == ["old", "new"]
    set_params = specs["xscript.project.set_params"].parameters["properties"]
    assert set_params["values"]["additionalProperties"] == {
        "type": ["number", "null"]
    }
    # `values` lost its minProperties with ADR-065: a nets-only edit patches
    # no parameter at all, and one op serves both declared tables.
    assert "minProperties" not in set_params["values"]
    nets = set_params["nets"]
    assert nets["type"] == "array" and nets["maxItems"] == 256
    assert nets["items"]["required"] == ["name", "a", "b", "gauge_mm"]
    assert nets["items"]["additionalProperties"] is False
    boards = set_params["boards"]
    assert boards["type"] == "array"
    assert boards["items"]["required"] == ["board", "name", "origin", "axis"]
    assert boards["items"]["additionalProperties"] is False
    # The one key a *request* may carry that a stored row may not: a
    # measurement taken in the viewport, converted by the worker (ADR-120).
    assert boards["items"]["properties"]["frame"]["enum"] == ["world", "board"]


def test_describe_project_api_is_json_safe_and_complete() -> None:
    from CadexScriptedRuntime import describe_project_api

    payload = describe_project_api()
    assert json.loads(json.dumps(payload)) == payload
    assert payload["ok"] is True
    assert payload["domain"] == "project"
    assert payload["program_schema"] == domains.PROJECT_SCRIPT_SCHEMA
    listings = payload["domains"]
    assert set(listings) == {"part", "partdesign", "sketcher", "mesh", "assembly"}
    for pack in domains.XSCRIPT_WORKBENCH_PACKS.values():
        listing = listings[pack.domain]
        export_names = [item["name"] for item in listing["exports"]]
        assert export_names == list(pack.api_exports)
        assert len(export_names) == len(set(export_names))
        assert all(item["description"] for item in listing["exports"])
        assert all(
            "*args" not in item["signature"] and "**" not in item["signature"]
            for item in listing["exports"]
        )
        assert listing["accepted_output_types"] == list(pack.output_types)
    assert set(payload["source_globals"]) == {
        "sketcher",
        "part",
        "partdesign",
        "mesh",
        "assembly",
        "params",
        "num",
        "nets",
        "wire",
        "boards",
        "board",
        "term",
        "mounts",
        "mount_set",
        "mount",
        "cage",
        "section_cage",
        "ring",
    }
    assert "params" in payload["parameters"]
    assert "num" in payload["parameters"]
    # The connection vocabulary is described beside the parameter one, so an
    # agent that reads describe_api learns the harness table exists (ADR-065).
    assert set(payload["connections"]) == {"nets", "wire", "values"}
    # ...and the board vocabulary beside it, for the same reason one table
    # over: where a wire attaches, rather than what it attaches to (ADR-120).
    assert set(payload["boards"]) == {"boards", "board", "term", "values"}
    # ...and the mount vocabulary, the fourth such table (ADR-126): where one
    # component bolts to another, and the op that puts it there.
    assert set(payload["mounts"]) == {
        "mounts", "mount_set", "mount", "mate", "values"
    }
    # ...and the section cage, the fifth (ADR-127): a shape as a table of
    # rings, which is what the model was already writing by hand.
    assert set(payload["cages"]) == {"cage", "section_cage", "ring", "values"}
    assert "result" in payload["result_contract"]
    assert set(payload["mutation_selection"]) == {
        "write_script",
        "edit_script",
        "set_params",
    }
    assert "expected_revision" in payload["revision_rule"]


def test_source_policy_blocks_escape_hatches() -> None:
    for source in (
        "import os\nresult = {}",
        "result = open('/tmp/value')",
        "result = {'x': doc.saveAs('x.FCStd')}",
        "result = {'x': part._domain}",
    ):
        with pytest.raises(ValueError, match="policy violation"):
            domains.validate_program_source(source)


def test_worker_staging_contains_only_the_project_bundle(tmp_path: Path) -> None:
    import CadexScriptedRuntime as runtime

    bundle, entry = runtime.shared_worker_bundle(
        Path(runtime.__file__).resolve().parent,
        "project",
    )
    copied = sorted(path.name for path in bundle.iterdir()
                    if path.suffix == ".py")
    expected = {
        # The project entry module, under its real name: it is imported
        # rather than runpy'd now, so it keeps a module name (ADR-052).
        "cadex_project_worker.py",
        "cadex_domain_api.py",
        "cadex_domain_worker.py",
        # The subshape vocabulary the five selector-taking part ops resolve
        # against; the sandbox imports it, so it has to be staged (Phase 10b).
        "CadexSubshapeQuery.py",
        "cadex_project_api.py",
        "cadex_sketcher_api.py",
        "cadex_sketcher_worker.py",
        "cadex_part_api.py",
        "cadex_part_worker.py",
        # The wire router part.cable searches with: pure Python, imported by
        # the part worker inside the sandbox, so it is staged too (ADR-056).
        "CadexRouting.py",
        # The multi-conductor lay part.bundle places around that route: pure
        # Python, staged for the same reason (ADR-057).
        "CadexBundle.py",
        # The named ports part.cable and part.bundle now take: pure Python,
        # staged for the same reason again (ADR-062).
        "CadexTerminals.py",
        "CadexSolder.py",
        # The linear-elastic solve part.stress runs: pure numpy/scipy, no
        # FreeCAD import at all, staged so the part worker can reach it
        # inside the sandbox and cadexd never does (ADR-145).
        "CadexStress.py",
        # The connection table nets()/wire() declare: pure Python, staged so
        # the project worker can stage it into the exec namespace (ADR-065).
        "CadexNets.py",
        # The board table boards()/board()/term() declare: pure Python,
        # staged for exactly that reason one table over (ADR-120).
        "CadexBoards.py",
        "CadexMounts.py",
        "CadexCage.py",
        # The linked-part container part.import_part reads: pure Python,
        # staged for the same reason, and the one module here that cadexd
        # also imports -- it builds a container out of another project's
        # accepted attempt (ADR-138).
        "CadexLinkedPart.py",
        "cadex_partdesign_api.py",
        "cadex_partdesign_worker.py",
        "cadex_mesh_api.py",
        "cadex_mesh_worker.py",
        "cadex_assembly_api.py",
        "cadex_assembly_worker.py",
        # The MuJoCo translator assembly.dynamics runs: pure Python, staged
        # for the same reason again -- and, uniquely, the only module in the
        # tree allowed to import mujoco (ADR-077).
        "CadexDynamics.py",
        "cadex_tessellation.py",
        # The resident preview worker's entry: a second entry point into the
        # same bundle, sandboxed the same way, never importable by the
        # service (ADR-055).
        "cadex_preview_worker.py",
        # ...and the resident live worker's (ADR-109). A third entry point,
        # and the one that makes the pattern load-bearing rather than tidy:
        # it imports CadexDynamics and through it mujoco, so being staged
        # here rather than imported is what keeps physics out of cadexd.
        "cadex_live_worker.py",
    }
    assert set(copied) == expected
    assert entry == "cadex_project_worker.py"
    # Nothing else rides along -- __pycache__ aside, which is the point.
    assert {path.name for path in bundle.iterdir()} - {"__pycache__"} == expected
    # The project bundle is the only bundle: per-domain staging was retired.
    assert set(runtime._DOMAIN_WORKER_BUNDLES) == {"project"}


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

def test_exploded_display_record_is_a_pure_projection_of_the_native_data() -> None:
    """The display record (ADR-149) is dict-to-dict: no FreeCAD needed."""

    from cadex_assembly_worker import _compact_pose, _exploded_display_record

    def fact(position, axis, angle_degrees):
        return {
            "position_mm": list(position),
            "rotation_axis": list(axis),
            "rotation_angle_degrees": angle_degrees,
            "matrix": [0.0] * 16,
        }

    identity = _compact_pose(fact([1.0, 2.0, 3.0], [0.0, 0.0, 1.0], 0.0))
    assert identity == {
        "position_mm": [1.0, 2.0, 3.0],
        "quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
    }
    quarter = _compact_pose(fact([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 90.0))
    half_root_two = math.sqrt(0.5)
    assert quarter["quaternion_xyzw"] == pytest.approx(
        [0.0, 0.0, half_root_two, half_root_two]
    )
    # A zero axis (the degenerate identity FreeCAD can emit) is the identity
    # quaternion rather than a division by zero.
    degenerate = _compact_pose(fact([0.0, 0.0, 0.0], [0.0, 0.0, 0.0], 0.0))
    assert degenerate["quaternion_xyzw"] == [0.0, 0.0, 0.0, 1.0]

    record = _exploded_display_record(
        {
            "schema": "cadex-assembly-exploded-view-v1",
            "assembly_output": "asm",
            "moves": [
                {
                    "move_index": 0,
                    "kind": "normal",
                    "component_outputs": ["top"],
                    "transform": {},
                    "movement_transform": fact([0, 0, 20], [0, 0, 1], 0.0),
                    "changed_component_outputs": ["top"],
                    "final_placements": {"top": fact([0, 0, 20], [0, 0, 1], 0.0)},
                    "line_segments": [
                        {
                            "component_output": "top",
                            "start_mm": [0.0, 0.0, 5.0],
                            "end_mm": [0.0, 0.0, 25.0],
                            "length_mm": 20.0,
                        }
                    ],
                },
                {
                    "move_index": 1,
                    "kind": "radial",
                    "component_outputs": ["left", "right"],
                    "radial_distance_mm": 10.0,
                    "movement_transform": fact([10, 0, 0], [0, 0, 1], 0.0),
                    "changed_component_outputs": ["left", "right"],
                    "final_placements": {
                        "left": fact([-15, 0, 0], [0, 0, 1], 90.0),
                        "right": fact([15, 0, 0], [0, 0, 1], 0.0),
                    },
                    "line_segments": [
                        {
                            "component_output": "left",
                            "start_mm": [-5.0, 0.0, 0.0],
                            "end_mm": [-15.0, 0.0, 0.0],
                            "length_mm": 10.0,
                        },
                        {
                            "component_output": "right",
                            "start_mm": [5.0, 0.0, 0.0],
                            "end_mm": [15.0, 0.0, 0.0],
                            "length_mm": 10.0,
                        },
                    ],
                },
            ],
            "assembly_bounds": {"center_mm": [0.0, 0.0, 2.5], "diagonal_mm": 40.0},
            "final_component_placements": {
                "base": fact([0, 0, 0], [0, 0, 1], 0.0),
                "top": fact([0, 0, 20], [0, 0, 1], 0.0),
                "left": fact([-15, 0, 0], [0, 0, 1], 90.0),
                "right": fact([15, 0, 0], [0, 0, 1], 0.0),
            },
            "line_count": 3,
            "native_readback": {"view_proxy_class": "ExplodedView"},
        }
    )
    assert set(record) == {
        "assembly_output", "bounds", "stages", "final_poses", "lines",
    }
    assert record["assembly_output"] == "asm"
    assert record["bounds"] == {"center_mm": [0.0, 0.0, 2.5], "diagonal_mm": 40.0}
    assert [stage["move_index"] for stage in record["stages"]] == [0, 1]
    assert [stage["kind"] for stage in record["stages"]] == ["normal", "radial"]
    assert record["stages"][1]["component_outputs"] == ["left", "right"]
    # Stage poses are the per-move cumulative placements, compacted.
    assert record["stages"][0]["poses"]["top"]["position_mm"] == [0.0, 0.0, 20.0]
    assert record["stages"][1]["poses"]["left"]["quaternion_xyzw"] == pytest.approx(
        [0.0, 0.0, half_root_two, half_root_two]
    )
    # Every component has a factor-1 endpoint, moved or not.
    assert set(record["final_poses"]) == {"base", "top", "left", "right"}
    # Lines are flattened in move order, without the redundant length.
    assert [line["component_output"] for line in record["lines"]] == [
        "top", "left", "right",
    ]
    assert all(
        set(line) == {"component_output", "start_mm", "end_mm"}
        for line in record["lines"]
    )

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

def test_worker_staging_rejects_an_undeclared_domain(tmp_path: Path) -> None:
    import CadexScriptedRuntime as runtime

    with pytest.raises(ValueError, match="no isolated worker bundle"):
        runtime.shared_worker_bundle(
            Path(runtime.__file__).resolve().parent,
            "not-a-domain",
        )

