# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The restore pass proves the digest without measuring the fit (ADR-630).

Every ``open_project`` re-runs the accepted script and asserts digest
equality. The fit (static pairs, joint sweeps, shell gaps) is not digest
material, and when the accepted attempt's report is on disk an identical
acceptance keeps that attempt pinned, so the replay's fit was measured and
thrown away: on ``castra-deinonychus`` with a cold fit cache, most of a 299 s
open. The replay may skip it only when it cannot become the attempt reads are
served from. These tests drive ``open_project`` through the server dispatch
with the lifecycle faked and record what the restore asked for.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import pytest

import CadexdProtocol as protocol
from CadexScriptStore import CadexProjectScriptStore
import cadexd
from cadexd import CadexdServer

STAGING = "script_artifacts/rev/attempt-1"


def _project(tmp_path: Path, *, report: bool, working: str = "rev-accepted") -> Path:
    root = tmp_path / "creature"
    CadexProjectScriptStore(root).write(
        source="result = {}\n",
        state_updates={
            "accepted_digest": "digest-accepted",
            "accepted_revision": "rev-accepted",
            "working_revision": working,
            "accepted_attempt": {"attempt_id": "1", "staging": STAGING, "revision": "rev-accepted"},
            "latest_candidate": {"status": "accepted", "revision": "rev-accepted"},
        },
    )
    if report:
        staging = root / STAGING
        staging.mkdir(parents=True)
        (staging / "result.json").write_text(json.dumps({"ok": True, "outputs": []}), encoding="utf-8")
    return root


@pytest.fixture()
def opened(monkeypatch: pytest.MonkeyPatch):
    app = sys.modules["FreeCAD"]
    monkeypatch.setattr(app, "newDocument", lambda name: type("Doc", (), {"Name": name})(), raising=False)
    monkeypatch.setattr(app, "closeDocument", lambda name: None, raising=False)
    monkeypatch.setattr(
        cadexd, "_resolve_budgets",
        lambda raw: {"timeout_seconds": 30.0, "memory_limit_mb": 512},
    )
    calls: list[dict[str, Any]] = []

    def lifecycle(_service, tool, args, **kwargs):
        calls.append({"tool": tool, **kwargs})
        return {"ok": True, "digest": "digest-accepted"}

    frames: list[dict] = []
    server = CadexdServer(frames.append, run_lifecycle=lifecycle)

    def open_(root: Path) -> dict:
        line = protocol.encode_frame(
            {"schema": protocol.PROTOCOL_SCHEMA, "id": "o1", "op": "open_project",
             "args": {"project_root": str(root)}}
        )[:-1]
        admitted = server.admit(line)
        assert admitted is not None
        server.dispatch(*admitted)
        return frames[-1]

    return open_, calls


def test_a_restore_over_a_kept_report_measures_no_fit(tmp_path, opened) -> None:
    open_, calls = opened
    response = open_(_project(tmp_path, report=True))
    assert response["ok"] is True and response["restore"]["matches_accepted"] is True
    assert [call["measure_fit"] for call in calls] == [False]
    assert calls[0]["prune_artifacts"] is False


def test_a_restore_with_no_kept_report_measures_the_fit(tmp_path, opened) -> None:
    # The replay would be pinned, and reads would find no fit in it.
    open_, calls = opened
    assert open_(_project(tmp_path, report=False))["ok"] is True
    assert [call["measure_fit"] for call in calls] == [True]


def test_a_working_script_that_is_not_the_accepted_one_measures_the_fit(tmp_path, opened) -> None:
    # A different revision is a new acceptance, never the pinned attempt.
    open_, calls = opened
    open_(_project(tmp_path, report=True, working="rev-edited"))
    assert [call["measure_fit"] for call in calls] == [True]


def test_the_runtime_writes_the_flag_only_when_asked() -> None:
    # Not a recipe key: the drift comparison (ADR-476) reads both attempts
    # as it always did.
    from CadexGeometryDigest import RECIPE_REQUEST_KEYS

    assert "measure_fit" not in RECIPE_REQUEST_KEYS
    source = Path(cadexd.__file__).with_name("CadexScriptedRuntime.py").read_text(encoding="utf-8")
    assert 'request["measure_fit"] = False' in source
    worker = Path(cadexd.__file__).with_name("cadex_project_worker.py").read_text(encoding="utf-8")
    assert 'skip_fit=request.get("measure_fit") is False' in worker
