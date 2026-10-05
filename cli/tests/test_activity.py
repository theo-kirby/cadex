# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The project activity log ``cadex mcp`` writes, and ``/api/project`` reads (ADR-549)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.request

from cadex_cli import activity
from cadex_cli.activity import (
    activity_path,
    append_activity,
    begin_activity,
    read_activity,
    reply_error,
    summarize_arguments,
)
from cadex_cli.review_server import serve

from test_commands import PLATE


def test_arguments_are_summarised_never_logged_in_full() -> None:
    source = "plate = part.box(30, 20, 6)\nresult = {'plate': plate}\n" * 50
    line = summarize_arguments({"source": source, "name": "foot", "values": {"a": 1, "b": 2},
                                "views": ["iso", "top"], "width": 30.5, "wait": True})
    assert line == (f'name="foot", source=<{len(source)} chars>, values={{a,b}}, views=[2], '
                    'wait=true, width=30.5')
    assert "part.box" not in line
    many = summarize_arguments({f"k{i}": "x" * 39 for i in range(20)})
    assert len(many) == activity.FIELD_CHARS and many.endswith("…")
    wide = summarize_arguments({"values": {f"parameter_{i}": i for i in range(9)}})
    assert wide == "values={9 keys}"


def test_an_error_reply_is_reduced_to_its_code_and_reason() -> None:
    engine = {"content": [{"type": "text", "text": json.dumps(
        {"ok": False, "failure_code": "CADEXD_UNREACHABLE", "error": "broken pipe"})}]}
    assert reply_error(engine) == "CADEXD_UNREACHABLE: broken pipe"
    assert reply_error({"content": [{"type": "text", "text": "No such tool: 'x'."}]}) == "No such tool: 'x'."
    assert reply_error({"content": []}) == ""


def test_the_log_is_capped_and_keeps_the_newest_calls(tmp_path) -> None:
    for i in range(2000):
        append_activity(tmp_path, "write_script", {"source": "s" * 500, "i": i},
                        ok=i % 3 != 0, detail="d" * 400, ms=12.4, now=1_800_000_000 + i)
    path = activity_path(tmp_path)
    assert path.stat().st_size <= activity.MAX_BYTES
    lines = path.read_bytes().splitlines()
    assert all(len(line) < 600 for line in lines)
    assert [json.loads(line)["args"] for line in lines][-1] == 'i=1999, source=<500 chars>'
    read = read_activity(tmp_path)
    assert read["available"] is True and len(read["entries"]) == activity.READ_LIMIT
    newest = read["entries"][0]
    assert newest == {"t": "2027-01-15T08:33:19Z", "tool": "write_script",
                      "args": "i=1999, source=<500 chars>", "outcome": "ok",
                      "detail": "d" * (activity.FIELD_CHARS - 1) + "…", "ms": 12}
    assert read["entries"][1]["outcome"] == "error"  # 1998 % 3 == 0
    assert not list(path.parent.glob("*.tmp"))


def test_no_log_and_a_torn_line_are_said_not_filled(tmp_path) -> None:
    missing = read_activity(tmp_path)
    assert missing["available"] is False and missing["entries"] == []
    assert "cadex mcp" in missing["reason"]
    append_activity(tmp_path, "inspect", {"scope": "fit"}, ok=True, detail="fit", ms=3)
    with open(activity_path(tmp_path), "ab") as handle:
        handle.write(b'{"t": "2026-')  # an append in flight
    read = read_activity(tmp_path)
    assert [entry["tool"] for entry in read["entries"]] == ["inspect"]


def _gone_pid() -> int:
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    child.wait()
    return child.pid


def test_a_call_is_in_flight_until_it_returns_and_then_one_entry(tmp_path) -> None:
    first = begin_activity(tmp_path, "evaluate", {"seeds": [1, 2]}, now=1_800_000_000)
    running = read_activity(tmp_path)["entries"]
    assert running == [{"t": "2027-01-15T08:00:00Z", "tool": "evaluate", "args": "seeds=[2]",
                        "outcome": "running", "detail": "", "ms": 0, "call": first, "pid": os.getpid()}]
    append_activity(tmp_path, "evaluate", {"seeds": [1, 2]}, ok=True, detail="evaluate: fail",
                    ms=68000.0, now=1_800_000_068, call=first)
    second = begin_activity(tmp_path, "render", {}, now=1_800_000_070)
    assert second != first
    entries = read_activity(tmp_path)["entries"]
    assert [(e["tool"], e["outcome"]) for e in entries] == [("render", "running"), ("evaluate", "ok")]
    assert entries[1]["t"] == "2027-01-15T08:01:08Z" and entries[1]["call"] == first
    assert len(activity_path(tmp_path).read_text().splitlines()) == 3


def test_an_in_flight_line_whose_server_is_gone_reads_lost(tmp_path) -> None:
    begin_activity(tmp_path, "evaluate", {})
    log = activity_path(tmp_path)
    entry = json.loads(log.read_text()) | {"pid": _gone_pid(), "call": "gone-1"}
    log.write_text(json.dumps(entry) + "\n")
    lost = read_activity(tmp_path)["entries"][0]
    assert lost["outcome"] == "lost" and "ended before this call returned" in lost["detail"]


def test_two_lines_a_call_stay_inside_the_bound(tmp_path) -> None:
    for i in range(2000):
        call = begin_activity(tmp_path, "write_script", {"source": "s" * 500, "i": i},
                              now=1_800_000_000 + i)
        append_activity(tmp_path, "write_script", {"source": "s" * 500, "i": i},
                        ok=True, detail="d" * 400, ms=12.4, now=1_800_000_000 + i, call=call)
    path = activity_path(tmp_path)
    assert path.stat().st_size <= activity.MAX_BYTES
    assert all(len(line) < 600 for line in path.read_bytes().splitlines())
    entries = read_activity(tmp_path)["entries"]
    assert len(entries) == activity.READ_LIMIT and {e["outcome"] for e in entries} == {"ok"}
    assert entries[0]["args"] == "i=1999, source=<500 chars>"


def test_a_slow_evaluate_through_cadex_mcp_is_in_flight_on_api_project(engine, tmp_path) -> None:
    """ADR-553 end to end: while a real ``cadex mcp`` process is still answering
    an ``evaluate`` -- most of it the session opening the engine and building
    the design -- ``/api/project`` carries the call as running and the stage as
    ``evaluating``; once it returns, the same entry is finished."""

    root = tmp_path / "orun3-biped-inflight"
    cli_dir = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(cli_dir) + os.pathsep + os.environ.get("PYTHONPATH", "")}

    def session(calls):
        mcp = subprocess.Popen(
            [sys.executable, "-m", "cadex_cli", "mcp", "--project", str(root)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=env)
        replies = []
        try:
            for ident, (name, arguments) in enumerate(calls, start=1):
                mcp.stdin.write(json.dumps({"jsonrpc": "2.0", "id": ident, "method": "tools/call",
                                            "params": {"name": name, "arguments": arguments}}) + "\n")
                mcp.stdin.flush()
                replies.append(json.loads(mcp.stdout.readline()))
        finally:
            mcp.stdin.close()
            assert mcp.wait(timeout=180) == 0
            mcp.stdout.close()
        return replies

    assert session([("write_script", {"source": PLATE})])[0]["result"]["isError"] is False
    server, _thread = serve(root, "127.0.0.1", 0)
    seen: list[dict] = []
    replies: list = []
    try:
        caller = threading.Thread(target=lambda: replies.extend(session([("evaluate", {})])))
        caller.start()
        while caller.is_alive():
            with urllib.request.urlopen(server.url.rstrip("/") + "/api/project", timeout=10) as response:
                project = json.loads(response.read())
            newest = (project["activity"].get("entries") or [None])[0]
            if newest and newest["tool"] == "evaluate" and newest["outcome"] == "running":
                seen.append({"stage": project["stage"], "entry": newest})
            time.sleep(0.05)
        caller.join()
        with urllib.request.urlopen(server.url.rstrip("/") + "/api/project", timeout=10) as response:
            after = json.loads(response.read())
    finally:
        server.shutdown()
        server.server_close()
    assert replies and "result" in replies[0], replies
    assert seen, "the evaluate call was never seen in flight"
    first = seen[0]
    assert first["stage"]["state"] == "evaluating"
    assert first["stage"]["reason"] == "the agent's evaluate call is running"
    assert first["stage"]["since"] == first["entry"]["t"] and first["entry"]["args"] == ""
    assert isinstance(first["entry"]["pid"], int) and first["entry"]["call"]
    entries = after["activity"]["entries"]
    finished = entries[0]
    assert finished["tool"] == "evaluate" and finished["outcome"] in ("ok", "error")
    assert finished["call"] == first["entry"]["call"] and finished["ms"] > 0
    assert [e["tool"] for e in entries] == ["evaluate", "write_script"]
    assert after["stage"]["state"] != "evaluating"


def test_a_tool_call_through_cadex_mcp_reaches_api_project(engine, tmp_path) -> None:
    """The product path end to end: a real ``cadex mcp`` process builds a
    plate and refuses an unknown tool, and the dashboard's ``/api/project``
    carries both calls, newest first, with the source summarised by length."""

    root = tmp_path / "orun3-biped-activity"
    cli_dir = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(cli_dir) + os.pathsep + os.environ.get("PYTHONPATH", "")}
    mcp = subprocess.Popen(
        [sys.executable, "-m", "cadex_cli", "mcp", "--project", str(root)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=env)
    try:
        for ident, (name, arguments) in enumerate(
                [("write_script", {"source": PLATE}), ("no_such_tool", {"x": 1})], start=1):
            mcp.stdin.write(json.dumps({"jsonrpc": "2.0", "id": ident, "method": "tools/call",
                                        "params": {"name": name, "arguments": arguments}}) + "\n")
            mcp.stdin.flush()
            reply = json.loads(mcp.stdout.readline())
            assert reply["result"]["isError"] is (name == "no_such_tool"), reply
    finally:
        mcp.stdin.close()
        assert mcp.wait(timeout=120) == 0
        mcp.stdout.close()

    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        with urllib.request.urlopen(server.url.rstrip("/") + "/api/project", timeout=10) as response:
            project = json.loads(response.read())
    finally:
        server.shutdown()
        server.server_close()
    log = project["activity"]
    assert log["available"] is True
    refused, built = log["entries"]
    assert refused["tool"] == "no_such_tool" and refused["outcome"] == "error"
    assert refused["args"] == "x=1" and refused["detail"] == "No such tool: 'no_such_tool'."
    assert built["tool"] == "write_script" and built["outcome"] == "ok"
    assert built["args"] == f"source=<{len(PLATE)} chars>"
    assert built["detail"].startswith("plate (") and built["ms"] > 0
    assert built["t"].endswith("Z") and built["t"] <= refused["t"]
    assert "part.box" not in activity_path(root).read_text()
    # The project's own repository never carries the log (ADR-194's `/review/`).
    tracked = subprocess.run(["git", "-C", str(root), "ls-files"], capture_output=True,
                             text=True, check=True).stdout
    assert "activity" not in tracked
