# SPDX-License-Identifier: LGPL-2.1-or-later

"""Client-side protocol coverage against a fake cadexd (Phase 5.4).

The fake is a plain Python subprocess speaking cadex-cadexd-v1 over stdio,
so the client's spawn/request/progress/cancel/crash/respawn machinery is
exercised without FreeCAD.
"""

from __future__ import annotations

from pathlib import Path
import sys

from CadexdClient import CadexdClient

FAKE_SERVER = r'''
import json
import os
import sys


def send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


print("FreeCADCmd 1.x console noise before the fd hijack")
send({"id": None, "event": {"event": "ready", "schema": "cadex-cadexd-v1"}})
opens = 0
for line in sys.stdin:
    frame = json.loads(line)
    op = frame.get("op")
    rid = frame.get("id")
    args = frame.get("args") or {}
    if op == "open_project":
        opens += 1
        send({"id": rid, "ok": True, "opens": opens})
    elif op == "write_script":
        source = str(args.get("source") or "")
        if source == "crash":
            os._exit(9)
        send({"id": rid, "event": {"event": "cadex_domain_worker_started"}})
        if source == "slow-cancel":
            cancel = json.loads(next(sys.stdin))
            send({"id": cancel.get("id"), "ok": True, "cancelled": rid})
            send({"id": rid, "ok": False, "failure_code": "RUN_CANCELLED",
                  "cancelled": True})
            continue
        send({"id": rid, "ok": True, "digest": "d" * 64, "opens": opens})
    elif op == "shutdown":
        send({"id": rid, "ok": True, "shutting_down": True})
        break
'''


def _client(tmp_path: Path) -> CadexdClient:
    server = tmp_path / "fake_cadexd.py"
    server.write_text(FAKE_SERVER, encoding="utf-8")
    return CadexdClient(
        tmp_path,
        budgets={"timeout_seconds": 30.0, "memory_limit_mb": 512},
        command=[sys.executable, "-u", str(server)],
    )


def test_request_response_with_progress_events(tmp_path: Path) -> None:
    client = _client(tmp_path)
    events: list[dict] = []
    try:
        payload = client.request(
            "write_script",
            {"source": "result = {}", "expected_revision": ""},
            progress_callback=events.append,
        )
        assert payload["ok"] is True
        assert payload["digest"] == "d" * 64
        # The lazy spawn replayed open_project exactly once.
        assert payload["opens"] == 1
        assert [event["event"] for event in events] == [
            "cadex_domain_worker_started"
        ]
    finally:
        client.close()


def test_cancellation_polls_and_forwards_cancel(tmp_path: Path) -> None:
    client = _client(tmp_path)
    cancelled = {"value": False}
    try:
        events: list[dict] = []

        def progress(event: dict) -> None:
            events.append(event)
            cancelled["value"] = True  # cancel as soon as the worker starts

        payload = client.request(
            "write_script",
            {"source": "slow-cancel", "expected_revision": ""},
            cancellation_check=lambda: cancelled["value"],
            progress_callback=progress,
        )
        assert payload["ok"] is False
        assert payload["failure_code"] == "RUN_CANCELLED"
    finally:
        client.close()


def test_crash_yields_envelope_then_respawns_and_reopens(tmp_path: Path) -> None:
    client = _client(tmp_path)
    try:
        crashed = client.request(
            "write_script", {"source": "crash", "expected_revision": ""}
        )
        assert crashed["ok"] is False
        assert crashed["failure_code"] == "CADEXD_CRASHED"
        assert client.alive() is False

        recovered = client.request(
            "write_script", {"source": "result = {}", "expected_revision": ""}
        )
        assert recovered["ok"] is True
        # A fresh child replayed open_project exactly once.
        assert recovered["opens"] == 1
        assert client.alive() is True
    finally:
        client.close()


def test_timeout_kills_the_child_and_reports_crash(tmp_path: Path) -> None:
    client = _client(tmp_path)
    try:
        payload = client.request("describe_api", {}, timeout=0.3)
        assert payload["ok"] is False
        assert payload["failure_code"] == "CADEXD_CRASHED"
        assert "0.3" in payload["error"]
        assert client.alive() is False
    finally:
        client.close()


def test_close_is_idempotent(tmp_path: Path) -> None:
    client = _client(tmp_path)
    assert client.request(
        "write_script", {"source": "result = {}", "expected_revision": ""}
    )["ok"]
    client.close()
    client.close()
    assert client.alive() is False
