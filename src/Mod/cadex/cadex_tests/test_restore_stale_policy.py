# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A stale policy is refused without locking the project (ADR-520).

ADR-469 moved every contact's solref, which moved the task bundle digest of
every robot, so every policy trained before it is refused with
``policy_task_mismatch``. The restore pass re-runs the stored script at
every open, so that refusal used to fail the open itself, and no command —
not even the design turn that sets the policy aside — could reach the
project. These tests drive ``open_project`` through the server dispatch with
the lifecycle faked, on a store whose accepted run declared a policy whose
task digest the engine no longer reproduces.
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

SOURCE = "result = {}\nif p.policy_on >= 0.5:\n    result['policy'] = assembly.policy(task)\n"
ACCEPTED = {"status": "accepted", "revision": "rev-accepted", "staging": None}


def _refusal(reason: str, *, stage: str = "policy_model") -> dict[str, Any]:
    """What a restore run returns when the worker refuses the policy."""

    return {
        "ok": False,
        "failure_code": "DOMAIN_CANDIDATE_FAILED",
        "error": f"Policy output 'policy' could not be built: {reason}",
        "observed": {
            "details": {
                "stage": stage,
                "simulation_output": "policy",
                "reason": reason,
                "correction": "Retrain against the current bundle.",
                "policy_task_sha256": "ca60b4ce",
                "task_sha256": "d50e953b",
            }
        },
    }


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    root = tmp_path / "robin"
    CadexProjectScriptStore(root).write(
        source=SOURCE,
        state_updates={
            "accepted_digest": "digest-accepted",
            "accepted_revision": "rev-accepted",
            "working_revision": "rev-accepted",
            "latest_candidate": dict(ACCEPTED),
            "param_values": {"policy_on": 1.0},
        },
    )
    return root


@pytest.fixture()
def harness(monkeypatch: pytest.MonkeyPatch):
    """A server whose restore run returns whatever the test puts in ``reply``."""

    app = sys.modules["FreeCAD"]
    monkeypatch.setattr(app, "newDocument", lambda name: type("Doc", (), {"Name": name})(), raising=False)
    monkeypatch.setattr(app, "closeDocument", lambda name: None, raising=False)
    monkeypatch.setattr(
        cadexd, "_resolve_budgets",
        lambda raw: {"timeout_seconds": 30.0, "memory_limit_mb": 512},
    )
    frames: list[dict] = []
    reply: dict[str, Any] = {}
    calls: list[str] = []

    def lifecycle(_service, tool, args, **_kwargs):
        calls.append(tool)
        # The real lifecycle records the refused run as the latest candidate
        # before it returns; the open must put the accepted one back.
        root = Path(_service._root)
        CadexProjectScriptStore(root).write(
            state_updates={"latest_candidate": {"status": "failed", "revision": "rev-accepted"}}
        )
        return json.loads(json.dumps(reply["payload"]))

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

    return open_, reply, calls


@pytest.mark.parametrize("reason", sorted(cadexd.STALE_POLICY_REASONS))
def test_a_stale_policy_opens_the_project_and_names_the_output(project, harness, reason):
    open_, reply, calls = harness
    reply["payload"] = _refusal(reason)

    response = open_(project)

    assert response["ok"] is True, response
    assert calls == ["xscript.project.write_script"]
    restore = response["restore"]
    assert restore["performed"] is False
    stale = restore["stale_policy"]
    assert stale["output"] == "policy"
    assert stale["reason"] == reason
    assert stale["policy_task_sha256"] == "ca60b4ce"
    assert stale["task_sha256"] == "d50e953b"
    assert "Retrain" in stale["correction"]
    assert not protocol.validate_response("open_project", response)

    # The accepted model is untouched, and the candidate record the refused
    # run wrote is put back (ADR-421).
    state = CadexProjectScriptStore(project).read_state()
    assert state["accepted_digest"] == "digest-accepted"
    assert state["accepted_revision"] == "rev-accepted"
    assert state["latest_candidate"]["status"] == "accepted"
    assert CadexProjectScriptStore(project).read_source() == SOURCE


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(_refusal("policy_header_malformed"), id="a corrupt container"),
        pytest.param(_refusal("policy_witness_disagrees"), id="a misread network"),
        pytest.param(_refusal("policy_task_mismatch", stage="dynamics_model"), id="another stage"),
        pytest.param(
            {"ok": False, "failure_code": "DOMAIN_CANDIDATE_FAILED", "error": "KeyError",
             "observed": {"details": {}}},
            id="a script that will not run",
        ),
    ],
)
def test_anything_but_staleness_still_refuses_the_open(project, harness, payload):
    open_, reply, _calls = harness
    reply["payload"] = payload

    response = open_(project)

    assert response["ok"] is False
    assert response["failure_code"] == protocol.CADEXD_RESTORE_FAILED
    assert "restore_failure" in response


def test_stale_policy_is_read_only_from_a_failed_payload():
    assert cadexd._stale_policy(None) is None
    assert cadexd._stale_policy({"ok": True, "observed": _refusal("policy_task_mismatch")["observed"]}) is None
    assert cadexd._stale_policy({"ok": False, "observed": "text"}) is None
    assert cadexd._stale_policy(_refusal("policy_model_mismatch"))["reason"] == "policy_model_mismatch"
