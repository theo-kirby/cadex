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




