# SPDX-License-Identifier: LGPL-2.1-or-later

"""Regression contracts for the lightweight, native model code editor."""

from __future__ import annotations

from pathlib import Path

import CadexScriptedDomains as domains


ROOT = Path(__file__).resolve().parents[4]


class _ShapeTrap:
    Name = "HeavyAssemblyShape"
    Label = "Heavy Assembly Shape"
    TypeId = "Part::Feature"
    PropertiesList: list[str] = []

    @property
    def Shape(self):
        raise AssertionError("The editor program index must never access Shape")


class _Document:
    Name = "EditorIndex"
    Uid = "editor-index-document"
    Objects = [_ShapeTrap()]


class _Service:
    @staticmethod
    def modeling_engine() -> str:
        return "xscript"

    @staticmethod
    def active_workbench_name() -> str:
        return "AssemblyWorkbench"

    @staticmethod
    def project_scope_snapshot() -> dict[str, str]:
        return {"root": ""}

    @staticmethod
    def _active_document() -> _Document:
        return _Document()


def test_editor_program_index_never_captures_domain_geometry() -> None:
    snapshot = domains.domain_program_index_snapshot(_Service(), "assembly")
    assert snapshot["native_programs"] == []
    assert "assembly_component_shapes" not in snapshot
    assert "part_document_shapes" not in snapshot
    completed = domains.complete_domain_program_index(snapshot)
    assert completed["ok"] is True
    assert completed["programs"] == []
    assert "component_candidates" not in completed


def test_editor_uses_explicit_builds_and_native_resizing() -> None:
    source = (ROOT / "src/Mod/cadex/CadexScriptedEditor.py").read_text(encoding="utf-8")
    assert "domain_program_index_snapshot(" in source
    assert "domain_context_snapshot(" not in source
    assert ".timer.start()" not in source
    assert "dock.setMinimumWidth" not in source
    assert "dock.setMinimumHeight" not in source
    assert "widget.setMinimumWidth" not in source
    assert "widget.setMinimumHeight" not in source
    assert '"XScriptedContentSplitter"' in source
    assert '"Build", "XScriptedRender"' in source
    assert '"Apply", "XScriptedAccept"' in source
