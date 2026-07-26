# SPDX-License-Identifier: LGPL-2.1-or-later

"""Inspection bounding: what a model may read, and how much of it.

Phase 7 (ADR-021) took the turn-context half of this file with the provider
and session that built it. What remains is engine-side and still live,
because cadexd serves ``inspect``: document reads are explicit and paged,
pages are deterministic and exactly size-accounted, and an oversized string
page is shrunk below the hard limit rather than streamed whole.
"""

from __future__ import annotations

import json
import sys
from types import ModuleType, SimpleNamespace

import pytest

from CadexInspection import (
    MAX_INSPECT_RESULT_BYTES,
    _bounded_page,
    _encoded_bytes,
    capture_inspection,
    complete_inspection,
)






def test_core_inspect_pages_are_deterministic_and_exactly_size_accounted() -> None:
    raw = {
        "objects": [
            {"name": f"Object{index:04d}", "label": "x" * 200}
            for index in range(1000)
        ]
    }
    captured = {
        "scope": "document",
        "target": "",
        "path": "/objects",
        "offset": 100,
        "limit": 50,
        "surface": {"workbench": "PartWorkbench", "engine": "native"},
        "document": {"name": "Large", "uid": "doc", "object_count": 1000},
    }

    first = _bounded_page(raw, captured)
    second = _bounded_page(raw, captured)

    assert first == second
    assert first["page"]["offset"] == 100
    assert first["page"]["returned"] == 50
    assert first["page"]["next_offset"] == 150
    assert first["result_json_bytes"] == _encoded_bytes(first)
    assert first["result_json_bytes"] <= MAX_INSPECT_RESULT_BYTES


def test_core_inspect_shrinks_large_string_pages_below_the_hard_limit() -> None:
    captured = {
        "scope": "script",
        "target": "",
        "path": "/source",
        "offset": 0,
        "limit": 50,
        "surface": {"workbench": "PartWorkbench", "engine": "xscript"},
        "document": {"name": "Large", "uid": "doc", "object_count": 1},
    }

    result = _bounded_page({"source": "x" * 100000}, captured)

    assert result["page"]["requested_limit"] == 50
    assert result["page"]["effective_limit"] < 50
    assert result["page"]["next_offset"] == len(result["value"])
    assert result["result_json_bytes"] == _encoded_bytes(result)
    assert result["result_json_bytes"] <= MAX_INSPECT_RESULT_BYTES


def test_document_inspection_is_explicit_and_paged() -> None:
    objects = [
        SimpleNamespace(Name=f"Object{index:04d}", Label=f"Object {index}", TypeId="Part::Feature")
        for index in range(1000)
    ]

    class _Service:
        def active_workbench_name(self) -> str:
            return "PartWorkbench"

        def modeling_engine(self) -> str:
            return "xscript"

        def _active_document(self):
            return SimpleNamespace(Name="Large", Uid="doc", Objects=objects)

    captured = capture_inspection(
        _Service(),
        {"scope": "document", "path": "/objects", "offset": 500, "limit": 20},
    )
    result = complete_inspection(captured)

    assert result["ok"] is True
    assert result["page"]["total"] == 1000
    assert result["page"]["returned"] == 20
    assert result["value"][0]["name"] == "Object0500"
    assert result["result_json_bytes"] <= MAX_INSPECT_RESULT_BYTES


def test_assets_inspection_lists_what_import_file_can_name(tmp_path) -> None:
    """scope=assets is how the agent discovers importable geometry (ADR-043)."""

    import CadexScriptedRuntime as runtime

    source = tmp_path / "scan.stl"
    source.write_bytes(b"solid scan")
    project_root = tmp_path / "project"
    runtime.store_project_asset(project_root, str(source), "scan.stl")

    class _Service:
        def active_workbench_name(self) -> str:
            return "PartWorkbench"

        def modeling_engine(self) -> str:
            return "xscript"

        def _active_document(self):
            return SimpleNamespace(Name="Ephemeral", Uid="doc", Objects=[])

        def project_scope_snapshot(self):
            return {"root": str(project_root)}

    captured = capture_inspection(_Service(), {"scope": "assets"})
    assert captured["kind"] == "assets"
    result = complete_inspection(captured)

    assert result["ok"] is True
    assert result["value"]["asset_count"] == 1
    assert result["value"]["assets"][0]["name"] == "scan.stl"
    assert result["result_json_bytes"] <= MAX_INSPECT_RESULT_BYTES

    # A path selects into the listing like any other scope.
    paged = complete_inspection(
        capture_inspection(_Service(), {"scope": "assets", "path": "/assets/0/name"})
    )
    assert paged["value"] == "scan.stl"


def _store_service(project_root):
    class _Service:
        def active_workbench_name(self) -> str:
            return "PartWorkbench"

        def modeling_engine(self) -> str:
            return "xscript"

        def _active_document(self):
            return SimpleNamespace(Name="Ephemeral", Uid="doc", Objects=[])

        def project_scope_snapshot(self):
            return {"root": str(project_root)}

    return _Service()


def test_output_inspection_serves_the_accepted_revisions_facts(tmp_path) -> None:
    """Facts for any accepted output, not just the run that made it (ADR-043)."""

    from CadexProject import CadexProjectScriptStore

    staging = tmp_path / "script_artifacts" / "ab12cd34" / "attempt-001"
    staging.mkdir(parents=True)
    staging.joinpath("result.json").write_text(
        json.dumps(
            {
                "ok": True,
                "outputs": [
                    {
                        "name": "plate",
                        "type": "solid",
                        "domain": "part",
                        "artifact_kind": "brep",
                        "facts": {"volume_mm3": 2160.0, "shape_type": "Solid"},
                        "definition": {"operation": "box"},
                    },
                    {
                        "name": "scan",
                        "type": "mesh",
                        "domain": "mesh",
                        "artifact_kind": "mesh",
                        "facts": {"facets": 4},
                        "mesh_data": {"operation": "import_file"},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    CadexProjectScriptStore(tmp_path).write(
        source="result = {}",
        state_updates={
            "accepted_revision": "ab" * 32,
            "accepted_attempt": {
                "attempt_id": "001",
                "staging": staging.relative_to(tmp_path).as_posix(),
                "revision": "ab" * 32,
            },
        },
    )
    service = _store_service(tmp_path)

    listing = complete_inspection(capture_inspection(service, {"scope": "output"}))
    assert listing["ok"] is True, listing
    assert listing["value"]["output_count"] == 2
    assert [item["name"] for item in listing["value"]["outputs"]] == ["plate", "scan"]
    assert listing["value"]["outputs"][0]["domain"] == "part"

    detail = complete_inspection(
        capture_inspection(service, {"scope": "output", "target": "scan"})
    )
    assert detail["ok"] is True, detail
    assert detail["value"]["facts"]["facets"] == 4
    assert detail["value"]["mesh_data"]["operation"] == "import_file"
    # The definition is the script's business; inspect reports measurements.
    assert "definition" not in detail["value"]
    assert detail["result_json_bytes"] <= MAX_INSPECT_RESULT_BYTES

    # Paging addresses into the facts like any other scope.
    paged = complete_inspection(
        capture_inspection(
            service,
            {"scope": "output", "target": "plate", "path": "/facts/volume_mm3"},
        )
    )
    assert paged["value"] == 2160.0

    missing = complete_inspection(
        capture_inspection(service, {"scope": "output", "target": "ghost"})
    )
    assert missing["ok"] is False
    assert "plate" in missing["error"] and "scan" in missing["error"]


def test_output_inspection_needs_an_accepted_revision(tmp_path) -> None:
    from CadexProject import CadexProjectScriptStore

    CadexProjectScriptStore(tmp_path).write(source="result = {}", state_updates={})
    result = complete_inspection(
        capture_inspection(_store_service(tmp_path), {"scope": "output"})
    )
    assert result["ok"] is True
    assert result["value"]["ok"] is False
    assert "accepted revision" in result["value"]["error"]


def test_document_inspection_captures_only_the_requested_object_page() -> None:
    accessed: list[int] = []

    class _Objects:
        def __len__(self) -> int:
            return 1000

        def __getitem__(self, index: int):
            accessed.append(index)
            return SimpleNamespace(
                Name=f"Object{index:04d}",
                Label=f"Object {index}",
                TypeId="Part::Feature",
            )

        def __iter__(self):
            raise AssertionError("inspection capture must not enumerate every object")

    class _Service:
        def active_workbench_name(self) -> str:
            return "PartWorkbench"

        def modeling_engine(self) -> str:
            return "xscript"

        def _active_document(self):
            return SimpleNamespace(Name="Large", Uid="doc", Objects=_Objects())

    captured = capture_inspection(
        _Service(),
        {"scope": "document", "path": "/objects", "offset": 500, "limit": 20},
    )
    result = complete_inspection(captured)

    assert accessed == list(range(500, 520))
    assert result["page"]["total"] == 1000
    assert result["page"]["next_offset"] == 520




