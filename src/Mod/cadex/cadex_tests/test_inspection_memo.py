# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The inventory-family scopes are joined once per accepted report (ADR-628).

A client pages ``inspect scope="clearance"`` fifty rows at a time, and every
page used to re-parse the accepted attempt's ``result.json`` and re-join every
pair. On ``castra-deinonychus`` (290 components, 41,905 pairs, a 65 MB report)
that was 0.41-0.48 s a page and 5,942 pages for one build reply's fit block:
about 48 minutes. The pages must be byte-identical with and without the memo, and a
new accepted report must never be answered from the old one.
"""

from __future__ import annotations

import json

import CadexInspection
from CadexInspection import _encoded_bytes, _encodes_within, capture_inspection, complete_inspection
from test_inventory_scope import _project, _service


def _page(root, scope, **arguments):
    captured = capture_inspection(_service(root), {"scope": scope, **arguments})
    return complete_inspection(captured)


def _clearance_report(root):
    path = next((root / "script_artifacts").rglob("result.json"))
    report = json.loads(path.read_text(encoding="utf-8"))
    for item in report["outputs"]:
        if item["type"] == "assembly":
            item["clearance"] = [
                {"first": "base", "second": "boltA", "distance_mm": 0.0, "common_volume_mm3": 2.0},
                {"first": "base", "second": "boltB", "distance_mm": 1.5, "common_volume_mm3": 0.0},
                {"first": "boltA", "second": "boltB", "distance_mm": 30.0, "common_volume_mm3": 0.0,
                 "culled": True},
            ]
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def _uncached(root, scope, **arguments):
    CadexInspection._INVENTORY_MEMO[:] = [None, {}]
    return _page(root, scope, **arguments)


def test_every_page_is_the_page_the_unmemoised_read_gives(tmp_path) -> None:
    root = _project(tmp_path)
    _clearance_report(root)
    for scope, path in (("inventory", ""), ("inventory", "/components"),
                        ("clearance", ""), ("clearance", "/pairs"), ("anatomy", "")):
        for offset in (0, 1, 2):
            fresh = _uncached(root, scope, path=path, offset=offset, limit=1)
            again = _page(root, scope, path=path, offset=offset, limit=1)
            assert again == fresh, (scope, path, offset)


def test_later_pages_do_not_reread_the_report(tmp_path, monkeypatch) -> None:
    root = _project(tmp_path)
    _clearance_report(root)
    CadexInspection._INVENTORY_MEMO[:] = [None, {}]
    calls = []
    real = CadexInspection._join_inventory

    def counted(captured):
        calls.append(captured["kind"])
        return real(captured)

    monkeypatch.setattr(CadexInspection, "_join_inventory", counted)
    for offset in range(3):
        assert _page(root, "clearance", path="/pairs", offset=offset, limit=1)["ok"] is True
    assert calls == ["clearance"]
    # A different scope over the same report is its own join.
    _page(root, "inventory")
    assert calls == ["clearance", "inventory"]


def test_a_new_accepted_report_is_never_answered_from_the_old(tmp_path) -> None:
    root = _project(tmp_path)
    path = _clearance_report(root)
    first = _page(root, "clearance", path="/pairs", limit=50)["value"]
    assert [row["distance_mm"] for row in first][:1] == [0.0]
    report = json.loads(path.read_text(encoding="utf-8"))
    for item in report["outputs"]:
        if item["type"] == "assembly":
            item["clearance"][0]["distance_mm"] = 0.25
    path.write_text(json.dumps(report) + " ", encoding="utf-8")
    second = _page(root, "clearance", path="/pairs", limit=50)["value"]
    assert second[0]["distance_mm"] == 0.25


def test_the_bounded_size_test_agrees_with_the_exact_size() -> None:
    values = [None, 0, 1.5, float("nan"), "x" * 1023, "é" * 200, [1] * 600, {"b": 1, "a": [2, 3]},
              {"k" * 1100: 1}, [{"first": "a", "second": "b", "distance_mm": 0.1}] * 40, (1, 2)]
    for value in values:
        size = _encoded_bytes(value)
        for limit in (0, size - 1, size, size + 1, 1024):
            assert _encodes_within(value, limit) == (size <= limit), (value, limit)
