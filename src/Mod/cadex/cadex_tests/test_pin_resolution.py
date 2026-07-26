# SPDX-License-Identifier: LGPL-2.1-or-later

"""Stub coverage for headless pin resolution (Phase 5.2).

Everything up to the BREP import runs without FreeCAD; geometric matching
itself is covered by ``pin_resolution_integration.py`` under FreeCADCmd.
"""

from __future__ import annotations

import json
from pathlib import Path

from CadexPinResolution import resolve_pin
from CadexProject import CadexProjectScriptStore


def _seed_store(
    tmp_path: Path,
    *,
    accepted: bool = True,
    attempt: bool = True,
    report: dict | None = None,
) -> Path:
    store = CadexProjectScriptStore(tmp_path)
    staging = tmp_path / "script_artifacts" / "ab12cd34" / "attempt-001"
    staging.mkdir(parents=True)
    updates: dict = {}
    if accepted:
        updates.update(
            {
                "accepted_revision": "ab" * 32,
                "accepted_contract": [
                    {"name": "plate", "type": "solid", "domain": "part"}
                ],
                "accepted_digest": "cd" * 32,
            }
        )
    if attempt:
        updates["accepted_attempt"] = {
            "attempt_id": "001",
            "staging": staging.relative_to(tmp_path).as_posix(),
            "revision": "ab" * 32,
        }
    store.write(source="result = {}", state_updates=updates)
    if report is not None:
        (staging / "result.json").write_text(
            json.dumps(report), encoding="utf-8"
        )
    return staging


def test_import_is_side_effect_free() -> None:
    # The module (and the worker modules it reuses) must import under the
    # stubbed test runtime without touching FreeCAD.
    import CadexPinResolution
    import cadex_partdesign_worker

    assert callable(CadexPinResolution.resolve_pin)
    assert callable(cadex_partdesign_worker._query_subelements)


def test_rejects_empty_output_and_selection(tmp_path: Path) -> None:
    result = resolve_pin(tmp_path, "", {"element_type": "face", "index": 1})
    assert result["failure_code"] == "PIN_OUTPUT_INVALID"
    result = resolve_pin(tmp_path, "plate", {})
    assert result["failure_code"] == "PIN_SELECTION_INVALID"


def test_requires_an_accepted_revision(tmp_path: Path) -> None:
    _seed_store(tmp_path, accepted=False, attempt=False)
    result = resolve_pin(tmp_path, "plate", {"element_type": "face", "index": 1})
    assert result["ok"] is False
    assert result["failure_code"] == "NO_ACCEPTED_REVISION"


def test_rejects_outputs_outside_the_accepted_contract(tmp_path: Path) -> None:
    _seed_store(tmp_path)
    result = resolve_pin(tmp_path, "ghost", {"element_type": "face", "index": 1})
    assert result["failure_code"] == "UNKNOWN_PIN_OUTPUT"
    assert result["observed"]["accepted_outputs"] == ["plate"]


def test_missing_attempt_locator_yields_artifact_envelope(tmp_path: Path) -> None:
    _seed_store(tmp_path, attempt=False)
    result = resolve_pin(tmp_path, "plate", {"element_type": "face", "index": 1})
    assert result["failure_code"] == "PIN_ARTIFACT_MISSING"
    assert "accepted attempt" in result["error"]


def test_missing_worker_report_yields_artifact_envelope(tmp_path: Path) -> None:
    _seed_store(tmp_path, report=None)
    result = resolve_pin(tmp_path, "plate", {"element_type": "face", "index": 1})
    assert result["failure_code"] == "PIN_ARTIFACT_MISSING"
    assert "result.json" in result["error"]


def test_non_brep_outputs_are_unsupported(tmp_path: Path) -> None:
    _seed_store(
        tmp_path,
        report={
            "ok": True,
            "outputs": [
                {
                    "name": "plate",
                    "artifact_kind": "mesh",
                    "artifact_path": "outputs/output-000.ply",
                }
            ],
        },
    )
    result = resolve_pin(tmp_path, "plate", {"element_type": "face", "index": 1})
    assert result["failure_code"] == "UNSUPPORTED_PIN_TARGET"


def test_the_accepted_attempt_helpers_are_a_shared_public_surface(
    tmp_path: Path,
) -> None:
    """``inspect scope="output"`` reads the same pinned report (ADR-043)."""

    import pytest

    from CadexPinResolution import (
        accepted_attempt_dir,
        accepted_output_item,
        load_worker_report,
    )

    staging = _seed_store(
        tmp_path,
        report={
            "ok": True,
            "outputs": [{"name": "plate", "type": "solid", "domain": "part"}],
        },
    )
    state = CadexProjectScriptStore(tmp_path).read_state()

    assert accepted_attempt_dir(tmp_path, state) == staging.resolve()
    report = load_worker_report(staging)
    assert accepted_output_item(report, "plate")["domain"] == "part"
    with pytest.raises(KeyError):
        accepted_output_item(report, "ghost")

    # Containment is the guarantee both readers depend on.
    escaped = dict(state)
    escaped["accepted_attempt"] = {"staging": "../elsewhere"}
    with pytest.raises(ValueError):
        accepted_attempt_dir(tmp_path, escaped)


def test_accepted_attempt_is_recorded_on_acceptance(tmp_path: Path) -> None:
    # accept_project_candidate persists the locator; verified end-to-end in
    # the integration test, structurally here.
    from CadexScriptedRuntime import accept_project_candidate

    staging = tmp_path / "script_artifacts" / "ab12cd34" / "attempt-777"
    staging.mkdir(parents=True)
    prepared = {
        "revision": "ab" * 32,
        "project_root": str(tmp_path),
        "staging": str(staging),
        "attempt_id": "777",
        "tool_name": "xscript.project.write_script",
    }
    validated = {
        "digest": "cd" * 32,
        "contract": [{"name": "plate", "type": "solid", "domain": "part"}],
    }
    payload = accept_project_candidate(prepared, {"live_outputs": {}}, validated)
    assert payload["ok"] is True
    state = CadexProjectScriptStore(tmp_path).read_state()
    assert state["accepted_attempt"] == {
        "attempt_id": "777",
        "staging": "script_artifacts/ab12cd34/attempt-777",
        "revision": "ab" * 32,
    }
