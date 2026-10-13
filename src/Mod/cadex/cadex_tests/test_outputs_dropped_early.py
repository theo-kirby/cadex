# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A script that drops accepted outputs is refused before it builds (ADR-682).

``PROJECT_OUTPUTS_DROPPED`` (ADR-045) needs only the names the script
returns, but it was decided after the whole build: on panel-cat-2 a
``write_script`` paid 1111 s of geometry, fit and panels to hear it. These
tests run the real lifecycle -- prepare, the project worker's ``main``,
execute, validate -- in this process, with the output builder replaced by
one that raises: a refusal that arrives with the builder's error instead of
its own was decided too late.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

import pytest

import CadexScriptedProcess
import CadexScriptedRuntime as runtime
from CadexScriptedDomains import PROJECT_PACK
from CadexScriptStore import CadexProjectScriptStore
import cadex_project_worker

ACCEPTED = [
    {"name": "frame", "domain": "part", "type": "solid"},
    {"name": "servo", "domain": "part", "type": "solid"},
]
BATTERY_ONLY = 'result = {"battery": part.box(1.0, 1.0, 1.0)}\n'
KEEPS_ALL = (
    'result = {"frame": part.box(1.0, 1.0, 1.0), "servo": part.box(2.0, 1.0, 1.0),'
    ' "battery": part.box(3.0, 1.0, 1.0)}\n'
)
BUILDER_REACHED = "the output builder was reached"


@pytest.fixture()
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    home = tmp_path / "freecad"
    (home / "bin").mkdir(parents=True)
    (home / "bin" / "FreeCADCmd").write_text("#!/bin/sh\n", encoding="utf-8")
    root = tmp_path / "project.cadex"
    store = CadexProjectScriptStore(root)
    store.write(
        source='result = {"frame": part.box(1.0, 1.0, 1.0)}\n',
        state_updates={
            "accepted_contract": ACCEPTED,
            "accepted_revision": "a" * 64,
            "accepted_digest": "digest-accepted",
            "working_revision": "a" * 64,
        },
    )

    def captured(_service: Any, tool_name: str, arguments: Any) -> dict[str, Any]:
        return {
            "tool_name": tool_name,
            "operation": runtime.parse_project_tool(tool_name),
            "arguments": dict(arguments),
            "pack": PROJECT_PACK,
            "project_root": str(root),
            "project_id": "test",
            "document_name": "CadexdEphemeral",
            "document_uid": "uid",
            "document_revision": "0",
            "document_objects": [],
            "freecad_home": str(home),
            "timeout_seconds": 30.0,
            "memory_limit_bytes": 512 * 1024 * 1024,
        }

    def worker_in_process(_argv: Any, *, cwd: str, **_kwargs: Any) -> dict[str, Any]:
        """FreeCADCmd's part: the project worker's own ``main``, here."""

        monkeypatch.setenv(cadex_project_worker.REQUEST_ENV, os.path.join(cwd, "request.json"))
        monkeypatch.setenv(cadex_project_worker.RESULT_ENV, os.path.join(cwd, "result.json"))
        cadex_project_worker.main()
        return {"started": True, "returncode": 0, "elapsed_seconds": 0.0,
                "stdout": "", "stderr": ""}

    def builder(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(BUILDER_REACHED)

    app = sys.modules["FreeCAD"]
    monkeypatch.setattr(app, "newDocument", lambda *a: type("Doc", (), {"Name": "D"})(), raising=False)
    monkeypatch.setattr(app, "closeDocument", lambda name: None, raising=False)
    monkeypatch.setattr(runtime, "capture_project_state", captured)
    monkeypatch.setattr(CadexScriptedProcess, "run_process", worker_in_process)
    monkeypatch.setattr(cadex_project_worker, "_resource_limits", lambda request: None)
    monkeypatch.setattr(cadex_project_worker, "_serialize_output", builder)
    return {"root": root, "store": store}


def _write(source: str, **extra: Any) -> dict[str, Any]:
    return runtime.run_project_lifecycle(
        object(),
        "xscript.project.write_script",
        {"source": source, "expected_revision": "a" * 64, **extra},
    )


def _request(root: Path) -> dict[str, Any]:
    (attempt,) = sorted(root.glob("script_artifacts/*/attempt-*"))
    return json.loads((attempt / "request.json").read_text(encoding="utf-8"))


def test_the_refusal_comes_from_the_names_before_any_output_is_built(project) -> None:
    payload = _write(BATTERY_ONLY)

    assert payload["ok"] is False
    assert payload["failure_code"] == "PROJECT_OUTPUTS_DROPPED"
    assert payload["failure_stage"] == "postcondition"
    # The message the census (cli/tests/test_ot10_contract.py) classifies.
    assert payload["error"] == (
        "This script drops outputs that the accepted revision declares: frame, "
        "servo. write_script replaces THE whole project script -- to add a part, "
        "edit the script you have. Pass replace=true if removing them is what "
        "you meant."
    )
    assert BUILDER_REACHED not in json.dumps(payload)
    assert payload["observed"] == {"dropped_outputs": ["frame", "servo"]}
    assert payload["requested"] == {"replace": False}
    assert payload["model_state"]["status"] == "working_candidate_not_accepted"
    assert _request(project["root"])["protected_outputs"] == ["frame", "servo"]
    # Rolled back like any refused candidate (ADR-044).
    state = project["store"].read_state()
    assert state["latest_candidate"]["failure_code"] == "PROJECT_OUTPUTS_DROPPED"
    assert state["working_revision"] == "a" * 64


def test_replace_true_still_goes_through_to_the_build(project) -> None:
    payload = _write(BATTERY_ONLY, replace=True)

    assert payload["failure_code"] == "DOMAIN_CANDIDATE_FAILED"
    assert BUILDER_REACHED in payload["error"]
    assert "protected_outputs" not in _request(project["root"])


def test_a_script_that_keeps_every_output_is_not_refused(project) -> None:
    payload = _write(KEEPS_ALL)

    assert payload["failure_code"] == "DOMAIN_CANDIDATE_FAILED"
    assert BUILDER_REACHED in payload["error"]


def test_only_a_write_script_over_an_accepted_contract_is_protected() -> None:
    assert runtime.protected_outputs("write_script", {}, ACCEPTED) == ["frame", "servo"]
    assert runtime.protected_outputs("write_script", {"replace": True}, ACCEPTED) == []
    assert runtime.protected_outputs("write_script", {}, None) == []
    for operation in ("edit_script", "set_params"):
        assert runtime.protected_outputs(operation, {}, ACCEPTED) == []
