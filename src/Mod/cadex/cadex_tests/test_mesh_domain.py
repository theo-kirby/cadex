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


def test_api_is_immutable_and_payloads_are_json_safe() -> None:
    import json

    api = _api()
    with pytest.raises(AttributeError):
        api.extra = True  # type: ignore[attr-defined]
    payload = api.union(api.import_file("a.stl"), api.import_file("b.stl")).to_payload()
    assert json.loads(json.dumps(payload)) == payload


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
