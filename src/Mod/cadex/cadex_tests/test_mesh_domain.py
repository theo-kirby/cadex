# SPDX-License-Identifier: LGPL-2.1-or-later

"""Mesh domain (Phase 4): pack registration, API contract, and wiring.

Headless: everything here validates the FreeCAD-free half of the mesh domain
(the declarative API, the pack/worker registration, digest coverage, and the
asset-staging bounds). Kernel execution is exercised by the release-build
integration run (mesh program run/publish/rebuild)."""

from __future__ import annotations

from pathlib import Path
import re

import pytest

import CadexScriptedDomains as domains
from cadex_domain_api import DomainValue, create_domain_api
from cadex_mesh_api import MeshDomainAPI
import cadex_project_api as project_api
import cadex_project_worker as project_worker

MESH_PACK = domains.XSCRIPT_WORKBENCH_PACKS["MeshWorkbench"]


def _api() -> MeshDomainAPI:
    return MeshDomainAPI(MESH_PACK.api_exports, MESH_PACK.output_types)


def _part_solid() -> DomainValue:
    return DomainValue(
        domain="part",
        operation="box",
        output_type="solid",
        arguments=(10.0, 10.0, 10.0),
        properties={},
    )


# ---------------------------------------------------------------------------
# Pack registration and composition wiring
# ---------------------------------------------------------------------------


def test_mesh_pack_is_registered_production_ready_and_toolless() -> None:
    assert MESH_PACK.domain == "mesh"
    assert MESH_PACK.output_types == ("mesh",)
    assert MESH_PACK.production_ready is True
    # Capability packs carry no tool surface (ADR-013); the four project
    # tools stay the only mutation surface.
    assert MESH_PACK.tool_names == ()
    assert MESH_PACK.operations == ()


def test_mesh_joins_evaluation_order_between_partdesign_and_assembly() -> None:
    order = project_api.EVALUATION_ORDER
    assert "mesh" in order
    assert order.index("partdesign") < order.index("mesh") < order.index("assembly")


def test_create_domain_api_returns_the_production_mesh_api() -> None:
    api = create_domain_api("mesh", MESH_PACK.api_exports, MESH_PACK.output_types)
    assert isinstance(api, MeshDomainAPI)
    assert api.exported_names == MESH_PACK.api_exports


def test_project_worker_bundle_stages_the_mesh_modules() -> None:
    import CadexScriptedRuntime as runtime

    bundle = runtime._DOMAIN_WORKER_BUNDLES["project"]
    assert "cadex_mesh_api.py" in bundle
    assert "cadex_mesh_worker.py" in bundle


def test_project_pack_output_types_include_mesh() -> None:
    assert "mesh" in domains.PROJECT_PACK.output_types


def test_group_result_by_domain_accepts_mesh_values() -> None:
    grouped = project_worker._group_result_by_domain(
        {"hull": _api().from_shape(_part_solid())}
    )
    assert list(grouped) == list(project_api.EVALUATION_ORDER)
    assert set(grouped["mesh"]) == {"hull"}


# ---------------------------------------------------------------------------
# Declarative API contract
# ---------------------------------------------------------------------------


def test_api_contract_matches_the_pack_declaration() -> None:
    with pytest.raises(RuntimeError, match="does not declare"):
        MeshDomainAPI(("from_shape",), ("mesh",))
    with pytest.raises(RuntimeError, match="output types"):
        MeshDomainAPI(MESH_PACK.api_exports, ("mesh", "solid"))


def test_from_shape_validates_and_builds_a_mesh_value() -> None:
    value = _api().from_shape(
        _part_solid(), linear_deflection=0.5, angular_deflection=25.0, relative=True
    )
    assert value.domain == "mesh"
    assert value.output_type == "mesh"
    payload = value.to_payload()
    assert payload["operation"] == "from_shape"
    assert payload["properties"]["linear_deflection"] == 0.5
    assert payload["properties"]["relative"] is True
    assert payload["arguments"][0]["domain"] == "part"


def test_from_shape_rejects_non_part_and_non_tessellatable_values() -> None:
    api = _api()
    with pytest.raises(ValueError, match="Part api"):
        api.from_shape("not a value")
    with pytest.raises(ValueError, match="Part api"):
        api.from_shape(api.import_file("hull.stl"))
    wire = DomainValue(
        domain="part",
        operation="wire",
        output_type="wire",
        arguments=(),
        properties={},
    )
    with pytest.raises(ValueError, match="part topology"):
        api.from_shape(wire)
    with pytest.raises(ValueError, match="linear_deflection"):
        api.from_shape(_part_solid(), linear_deflection=0.0)


def test_import_file_accepts_only_flat_known_format_names() -> None:
    api = _api()
    assert api.import_file("scan.stl").to_payload()["arguments"] == ["scan.stl"]
    for filename in (
        "",
        "nested/scan.stl",
        "..\\scan.stl",
        "../scan.stl",
        "scan.step",
        "scan",
        "x" * 121 + ".stl",
    ):
        with pytest.raises(ValueError, match="filename"):
            api.import_file(filename)


def test_booleans_require_mesh_values_from_this_api() -> None:
    api = _api()
    left = api.import_file("a.stl")
    right = api.import_file("b.stl")
    for operation in ("union", "difference", "intersection"):
        value = getattr(api, operation)(left, right)
        assert value.to_payload()["operation"] == operation
        with pytest.raises(ValueError, match="Mesh api"):
            getattr(api, operation)(left, _part_solid())


def test_decimate_bounds_reduction_and_tolerance() -> None:
    api = _api()
    source = api.import_file("scan.ply")
    value = api.decimate(source, tolerance=0.5, reduction=0.9)
    assert value.to_payload()["properties"]["reduction"] == 0.9
    with pytest.raises(ValueError, match="reduction"):
        api.decimate(source, tolerance=0.5, reduction=1.5)
    with pytest.raises(ValueError, match="reduction"):
        api.decimate(source, tolerance=0.5, reduction=0.0)
    with pytest.raises(ValueError, match="tolerance"):
        api.decimate(source, tolerance=0.0, reduction=0.5)


def test_transform_mirrors_the_part_transform_contract() -> None:
    """An import you cannot place is not usable geometry (ADR-043)."""

    import cadex_part_api as part_api

    api = _api()
    scan = api.import_file("scan.stl")
    value = api.transform(
        scan,
        translation=[1.0, 2.0, 3.0],
        rotation_axis=[0.0, 0.0, 1.0],
        rotation_degrees=90.0,
        scale=2.0,
        pivot=[5.0, 0.0, 0.0],
    )
    assert value.domain == "mesh" and value.output_type == "mesh"
    properties = value.to_payload()["properties"]
    assert properties["translation"] == [1.0, 2.0, 3.0]
    assert properties["scale"] == [2.0, 2.0, 2.0]
    assert properties["pivot"] == [5.0, 0.0, 0.0]
    assert properties["rotation_degrees"] == 90.0

    # Same knobs as part.transform, so placing an import reads like placing
    # a modelled solid.
    part_transform = part_api.PartDomainAPI.transform
    mesh_transform = MeshDomainAPI.transform
    import inspect

    part_kwargs = set(inspect.signature(part_transform).parameters) - {"self", "shape"}
    mesh_kwargs = set(inspect.signature(mesh_transform).parameters) - {"self", "mesh"}
    assert part_kwargs == mesh_kwargs


def test_transform_validates_its_arguments() -> None:
    api = _api()
    scan = api.import_file("scan.stl")
    with pytest.raises(ValueError, match="Mesh api"):
        api.transform(_part_solid())
    with pytest.raises(ValueError, match="rotation_axis"):
        api.transform(scan, rotation_axis=[0.0, 0.0, 0.0])
    with pytest.raises(ValueError, match="scale"):
        api.transform(scan, scale=0.0)
    with pytest.raises(ValueError, match="scale"):
        api.transform(scan, scale=[1.0, -1.0, 1.0])
    with pytest.raises(ValueError, match="translation"):
        api.transform(scan, translation=[1.0, 2.0])


def test_transform_does_not_make_its_tree_approximating() -> None:
    """Rigid-plus-scale on floats is exact, so the fingerprint stays valid."""

    from cadex_mesh_worker import payload_tree_is_deterministic

    api = _api()
    placed = api.transform(api.import_file("scan.stl"), translation=[1.0, 0.0, 0.0])
    assert payload_tree_is_deterministic(placed.to_payload())
    decimated = api.decimate(placed, tolerance=0.5, reduction=0.5)
    assert not payload_tree_is_deterministic(
        api.transform(decimated, translation=[1.0, 0.0, 0.0]).to_payload()
    )


def test_api_is_immutable_and_payloads_are_json_safe() -> None:
    import json

    api = _api()
    with pytest.raises(AttributeError):
        api.extra = True  # type: ignore[attr-defined]
    payload = api.union(api.import_file("a.stl"), api.import_file("b.stl")).to_payload()
    assert json.loads(json.dumps(payload)) == payload


# ---------------------------------------------------------------------------
# Mesh into the BREP domains: part.shape_from_mesh (ADR-043)
# ---------------------------------------------------------------------------

PART_PACK = domains.XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]


def _part() -> object:
    return create_domain_api("part", PART_PACK.api_exports, PART_PACK.output_types)


def test_shape_from_mesh_crosses_the_domain_boundary_into_part() -> None:
    part = _part()
    value = part.shape_from_mesh(_api().import_file("scan.stl"))
    assert value.domain == "part"
    assert value.output_type == "solid"
    payload = value.to_payload()
    assert payload["operation"] == "shape_from_mesh"
    assert payload["arguments"][0]["domain"] == "mesh"
    assert payload["properties"]["tolerance"] == 0.1
    assert payload["properties"]["sew"] is True

    # solid=False publishes the sewn shell instead; both are publishable.
    shell = part.shape_from_mesh(_api().import_file("scan.stl"), solid=False)
    assert shell.output_type == "shell"


def test_shape_from_mesh_result_groups_under_part() -> None:
    grouped = project_worker._group_result_by_domain(
        {"scan_solid": _part().shape_from_mesh(_api().import_file("scan.stl"))}
    )
    assert set(grouped["part"]) == {"scan_solid"}
    assert grouped["mesh"] == {}


def test_shape_from_mesh_validates_its_argument_and_options() -> None:
    part = _part()
    mesh = _api().import_file("scan.stl")
    with pytest.raises(ValueError, match="Mesh api"):
        part.shape_from_mesh(_part_solid())
    with pytest.raises(ValueError, match="Mesh api"):
        part.shape_from_mesh({"domain": "mesh", "operation": "import_file"})
    with pytest.raises(ValueError, match="tolerance"):
        part.shape_from_mesh(mesh, tolerance=0.0)
    with pytest.raises(ValueError, match="sew"):
        part.shape_from_mesh(mesh, sew=False, solid=True)


def test_shape_from_mesh_rejects_approximating_trees_by_name() -> None:
    """A BREP output's identity is its bytes, so it has no by-definition
    fallback: an unreproducible mesh would flip the digest every rebuild."""

    api = _api()
    decimated = api.decimate(api.import_file("scan.stl"), tolerance=0.5, reduction=0.5)
    with pytest.raises(ValueError, match="decimate") as raised:
        _part().shape_from_mesh(decimated)
    assert "digest" in str(raised.value)
    # Nondeterminism propagates: transforming it does not launder it.
    with pytest.raises(ValueError, match="decimate"):
        _part().shape_from_mesh(api.transform(decimated, translation=[1.0, 0.0, 0.0]))
    # The reachable workaround stays reachable.
    assert _part().shape_from_mesh(api.import_file("scan.stl")).domain == "part"


def test_shape_from_mesh_is_declared_by_the_part_pack() -> None:
    assert "shape_from_mesh" in PART_PACK.api_exports
    assert "shape_from_mesh" in _part().exported_names


# ---------------------------------------------------------------------------
# Digest coverage and asset staging bounds
# ---------------------------------------------------------------------------


def test_project_digest_uses_the_mesh_geometry_fingerprint(tmp_path: Path) -> None:
    artifact = tmp_path / "outputs" / "output-000.ply"
    artifact.parent.mkdir()
    artifact.write_bytes(b"ply-bytes")
    outputs = [
        {
            "name": "hull",
            "domain": "mesh",
            "type": "mesh",
            "artifact_kind": "mesh",
            "artifact_path": "outputs/output-000.ply",
            "geometry_sha256": "aa" * 32,
            "definition": {"operation": "import_file"},
        }
    ]
    first = project_worker.compute_project_digest(tmp_path, outputs)
    assert re.fullmatch(r"[0-9a-f]{64}", first)
    # Artifact bytes do not join the digest (triangulation may differ run to
    # run for identical geometry); the vertex-set fingerprint does.
    artifact.write_bytes(b"different-ply-bytes")
    assert project_worker.compute_project_digest(tmp_path, outputs) == first
    outputs[0]["geometry_sha256"] = "bb" * 32
    assert project_worker.compute_project_digest(tmp_path, outputs) != first
    # Approximating outputs carry no fingerprint: identified by definition.
    del outputs[0]["geometry_sha256"]
    by_definition = project_worker.compute_project_digest(tmp_path, outputs)
    outputs[0]["definition"] = {"operation": "decimate"}
    assert project_worker.compute_project_digest(tmp_path, outputs) != by_definition


def test_decimate_trees_are_digested_by_definition() -> None:
    from cadex_mesh_worker import payload_tree_is_deterministic

    api = _api()
    tessellated = api.from_shape(_part_solid())
    assert payload_tree_is_deterministic(tessellated.to_payload())
    assert payload_tree_is_deterministic(
        api.union(tessellated, api.import_file("scan.stl")).to_payload()
    )
    decimated = api.decimate(tessellated, tolerance=0.5, reduction=0.5)
    assert not payload_tree_is_deterministic(decimated.to_payload())
    # Nondeterminism propagates to consumers of an approximating value.
    assert not payload_tree_is_deterministic(
        api.union(decimated, tessellated).to_payload()
    )


def test_asset_staging_copies_only_flat_mesh_files(tmp_path: Path) -> None:
    import CadexScriptedRuntime as runtime

    project_root = tmp_path / "project"
    staging = tmp_path / "staging"
    (project_root / "assets").mkdir(parents=True)
    staging.mkdir()
    (project_root / "assets" / "scan.stl").write_bytes(b"solid x")
    (project_root / "assets" / "notes.txt").write_text("skip me")
    (project_root / "assets" / "nested").mkdir()
    staged = runtime._stage_project_assets(project_root, staging)
    assert staged == ["scan.stl"]
    assert (staging / "assets" / "scan.stl").read_bytes() == b"solid x"
    assert not (staging / "assets" / "notes.txt").exists()


def test_asset_staging_without_assets_directory_is_a_noop(tmp_path: Path) -> None:
    import CadexScriptedRuntime as runtime

    project_root = tmp_path / "project"
    project_root.mkdir()
    staging = tmp_path / "staging"
    staging.mkdir()
    assert runtime._stage_project_assets(project_root, staging) == []
    assert not (staging / "assets").exists()


def test_asset_staging_enforces_the_budget(tmp_path: Path, monkeypatch) -> None:
    import CadexScriptedRuntime as runtime

    project_root = tmp_path / "project"
    staging = tmp_path / "staging"
    (project_root / "assets").mkdir(parents=True)
    staging.mkdir()
    (project_root / "assets" / "a.stl").write_bytes(b"1234")
    (project_root / "assets" / "b.stl").write_bytes(b"5678")
    monkeypatch.setattr(runtime, "_MAX_ASSET_BYTES", 5)
    with pytest.raises(ValueError, match="staging budget"):
        runtime._stage_project_assets(project_root, staging)


# ---------------------------------------------------------------------------
# Getting an asset into the project store (ADR-043)
# ---------------------------------------------------------------------------


def test_store_project_asset_copies_and_lists(tmp_path: Path) -> None:
    import CadexScriptedRuntime as runtime

    source = tmp_path / "incoming" / "Bracket.STL"
    source.parent.mkdir()
    source.write_bytes(b"solid bracket")
    project_root = tmp_path / "project"

    stored = runtime.store_project_asset(project_root, str(source))
    assert stored["name"] == "Bracket.STL"
    assert stored["bytes"] == len(b"solid bracket")
    assert re.fullmatch(r"[0-9a-f]{64}", stored["sha256"])
    assert (project_root / "assets" / "Bracket.STL").read_bytes() == b"solid bracket"
    assert runtime.list_project_assets(project_root) == [stored]
    # No half-copied temporaries survive an atomic store.
    assert sorted(p.name for p in (project_root / "assets").iterdir()) == [
        "Bracket.STL"
    ]

    # An explicit name renames; overwriting the same name is re-import.
    renamed = runtime.store_project_asset(project_root, str(source), "scan.stl")
    assert renamed["name"] == "scan.stl"
    source.write_bytes(b"solid bracket v2")
    again = runtime.store_project_asset(project_root, str(source), "scan.stl")
    assert again["sha256"] != renamed["sha256"]
    assert [item["name"] for item in runtime.list_project_assets(project_root)] == [
        "Bracket.STL",
        "scan.stl",
    ]


def test_store_project_asset_rejects_bad_sources_and_names(tmp_path: Path) -> None:
    import CadexScriptedRuntime as runtime

    project_root = tmp_path / "project"
    source = tmp_path / "scan.stl"
    source.write_bytes(b"solid x")
    notes = tmp_path / "notes.txt"
    notes.write_text("not geometry")

    with pytest.raises(ValueError, match="source_path"):
        runtime.store_project_asset(project_root, "")
    with pytest.raises(ValueError, match="Could not read"):
        runtime.store_project_asset(project_root, str(tmp_path / "missing.stl"))
    # The store holds two kinds of file since ADR-084 -- the three mesh
    # formats and a trained policy's .cxpolicy -- so the refusal names the
    # set rather than "mesh formats". A .txt is still not one of them.
    with pytest.raises(ValueError, match="formats this project store holds"):
        runtime.store_project_asset(project_root, str(notes))
    for name in ("nested/scan.stl", "../scan.stl", "scan", "x" * 121 + ".stl"):
        with pytest.raises(ValueError, match="filename"):
            runtime.store_project_asset(project_root, str(source), name)
    # A name that changes the format would break the suffix-driven importer.
    with pytest.raises(ValueError, match="format"):
        runtime.store_project_asset(project_root, str(source), "scan.ply")
    assert not (project_root / "assets").exists()


def test_store_project_asset_counts_the_incoming_file_against_the_budget(
    tmp_path: Path, monkeypatch
) -> None:
    import CadexScriptedRuntime as runtime

    project_root = tmp_path / "project"
    source = tmp_path / "scan.stl"
    source.write_bytes(b"12345678")
    runtime.store_project_asset(project_root, str(source), "a.stl")

    monkeypatch.setattr(runtime, "_MAX_ASSET_BYTES", 12)
    with pytest.raises(ValueError, match="staging budget"):
        runtime.store_project_asset(project_root, str(source), "b.stl")
    # Overwriting a.stl replaces its bytes rather than adding to them.
    assert runtime.store_project_asset(project_root, str(source), "a.stl")["bytes"] == 8

    monkeypatch.setattr(runtime, "_MAX_ASSET_FILES", 1)
    with pytest.raises(ValueError, match="staging budget is 1 files"):
        runtime.store_project_asset(project_root, str(source), "c.stl")


def test_stored_assets_are_exactly_what_a_run_would_stage(tmp_path: Path) -> None:
    """``list_project_assets`` and ``_stage_project_assets`` walk alike."""

    import CadexScriptedRuntime as runtime

    project_root = tmp_path / "project"
    staging = tmp_path / "staging"
    staging.mkdir()
    source = tmp_path / "scan.stl"
    source.write_bytes(b"solid x")
    runtime.store_project_asset(project_root, str(source), "scan.stl")
    (project_root / "assets" / "notes.txt").write_text("skip me")

    listed = [item["name"] for item in runtime.list_project_assets(project_root)]
    assert listed == runtime._stage_project_assets(project_root, staging) == ["scan.stl"]
    assert runtime.list_project_assets(tmp_path / "no-such-project") == []
