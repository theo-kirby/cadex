# SPDX-License-Identifier: LGPL-2.1-or-later

"""The MCP shim, the bridge socket, and the tool surface they publish.

Everything here runs against :mod:`fake_cadexd`, so what is under test is
the plumbing: the JSON-RPC subset Claude Code needs, the relay down the unix
socket, the schemas generated from ``OP_ARG_SPECS``, and the revision the
model never has to supply.
"""

from __future__ import annotations

import io
import json
from typing import Any

import pytest

from cadex_cli import mcp
from cadex_cli.bridge import Bridge
from cadex_cli.tools import CLI_TOOL_OPS, tool_definitions

from fake_cadexd import FakeCadexd, accepted_reply, rejected_reply


@pytest.fixture
def bridge():
    client = FakeCadexd()
    with Bridge(client) as running:
        yield running


def _rpc(bridge: Bridge, method: str, params: dict[str, Any] | None = None, id_: Any = 1):
    stream = io.StringIO()
    message: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
    if id_ is not None:
        message["id"] = id_
    if params is not None:
        message["params"] = params
    mcp.handle(message, str(bridge.socket_path), bridge.token, stream)
    raw = stream.getvalue()
    return json.loads(raw) if raw.strip() else None


# -- the JSON-RPC subset -------------------------------------------------


def test_initialize_echoes_the_client_protocol_version(bridge) -> None:
    reply = _rpc(bridge, "initialize", {"protocolVersion": "2025-06-18"})
    assert reply["result"]["protocolVersion"] == "2025-06-18"
    assert reply["result"]["capabilities"] == {"tools": {}}
    assert reply["result"]["serverInfo"]["name"] == "cadex"


def test_initialized_and_ping_behave(bridge) -> None:
    # A notification carries no id and must produce no reply at all.
    assert _rpc(bridge, "notifications/initialized", id_=None) is None
    assert _rpc(bridge, "ping")["result"] == {}


def test_an_unknown_method_is_a_proper_jsonrpc_error(bridge) -> None:
    reply = _rpc(bridge, "resources/list")
    assert reply["error"]["code"] == -32601


def test_an_unknown_notification_is_silently_ignored(bridge) -> None:
    assert _rpc(bridge, "notifications/cancelled", id_=None) is None


# -- the tool surface ----------------------------------------------------


def test_tools_list_relays_the_generated_surface(bridge) -> None:
    tools = _rpc(bridge, "tools/list")["result"]["tools"]
    assert [tool["name"] for tool in tools] == list(CLI_TOOL_OPS)
    for tool in tools:
        assert tool["description"]
        assert tool["inputSchema"]["type"] == "object"


def test_the_schemas_cannot_drift_from_op_arg_specs(protocol) -> None:
    """Every schema property is an argument the protocol declares.

    This is the point of generating them. A tool that offers an argument the
    engine does not take is a tool call that fails at the protocol layer for
    a reason the model cannot act on.
    """

    for tool in tool_definitions(protocol):
        required, optional = protocol.OP_ARG_SPECS[tool["name"]]
        declared = set(required) | set(optional)
        offered = set(tool["input_schema"]["properties"])
        assert offered <= declared, (tool["name"], offered - declared)
        # Required-minus-injected is exactly what the model must supply.
        assert set(tool["input_schema"]["required"]) == set(required) - {
            "expected_revision"
        }


def test_expected_revision_and_display_are_never_asked_of_the_model(protocol) -> None:
    for tool in tool_definitions(protocol):
        assert "expected_revision" not in tool["input_schema"]["properties"]
        assert "display" not in tool["input_schema"]["properties"]


def test_inspect_offers_only_scopes_a_headless_client_can_serve(protocol) -> None:
    scopes = {
        tool["input_schema"]["properties"]["scope"]["enum"]
        and tuple(tool["input_schema"]["properties"]["scope"]["enum"])
        for tool in tool_definitions(protocol)
        if tool["name"] == "inspect"
    }
    (offered,) = scopes
    assert "image" not in offered
    assert "output" in offered and "script" in offered


# -- calls ---------------------------------------------------------------


def test_a_tool_call_reaches_the_engine_with_the_injected_revision() -> None:
    client = FakeCadexd(
        replies={"write_script": lambda _args: accepted_reply("write", "rev-2")}
    )
    with Bridge(client, initial_revision="rev-1") as bridge:
        reply = _rpc(
            bridge, "tools/call", {"name": "write_script", "arguments": {"source": "x"}}
        )

    assert reply["result"]["isError"] is False
    (sent,) = client.args_for("write_script")
    assert sent == {"source": "x", "expected_revision": "rev-1"}
    # …and the guard that was used is visible to the model, not merely absent.
    payload = json.loads(reply["result"]["content"][0]["text"])
    assert payload["expected_revision_used"] == "rev-1"
    assert payload["revision"] == "rev-2"


def test_a_revision_the_model_supplies_is_overruled_not_honoured() -> None:
    client = FakeCadexd()
    with Bridge(client, initial_revision="rev-1") as bridge:
        _rpc(
            bridge,
            "tools/call",
            {
                "name": "write_script",
                "arguments": {"source": "x", "expected_revision": "guessed"},
            },
        )
    (sent,) = client.args_for("write_script")
    assert sent["expected_revision"] == "rev-1"


def test_the_revision_advances_across_calls() -> None:
    revisions = iter(["rev-2", "rev-3"])
    client = FakeCadexd(
        replies={"write_script": lambda _a: accepted_reply("w", next(revisions))}
    )
    with Bridge(client, initial_revision="rev-1") as bridge:
        for _ in range(2):
            _rpc(
                bridge,
                "tools/call",
                {"name": "write_script", "arguments": {"source": "x"}},
            )
    assert [args["expected_revision"] for args in client.args_for("write_script")] == [
        "rev-1",
        "rev-2",
    ]
    assert bridge.state.revision == "rev-3"


def test_a_refusal_still_advances_the_revision() -> None:
    """A rejected candidate becomes the working revision — the engine's rule.

    Tracking it only on success would make the *retry* after a rejection
    fail with STALE_PROGRAM_REVISION, for a reason that has nothing to do
    with what the model got wrong.
    """

    client = FakeCadexd(replies={"write_script": lambda _a: rejected_reply("rev-9")})
    with Bridge(client, initial_revision="rev-1") as bridge:
        reply = _rpc(
            bridge, "tools/call", {"name": "write_script", "arguments": {"source": "x"}}
        )
        assert bridge.state.revision == "rev-9"

    assert reply["result"]["isError"] is True
    payload = json.loads(reply["result"]["content"][0]["text"])
    assert payload["failure_code"] == "SCRIPT_REJECTED"
    assert payload["retry"] is False


def test_the_display_block_is_kept_from_the_model_and_kept_for_the_parent() -> None:
    """The model gets facts; the parent gets the artifact paths it exports."""

    client = FakeCadexd()
    with Bridge(client) as bridge:
        reply = _rpc(
            bridge, "tools/call", {"name": "write_script", "arguments": {"source": "x"}}
        )
        accepted = bridge.state.last_accepted

    payload = json.loads(reply["result"]["content"][0]["text"])
    assert "display" not in payload
    assert payload["live_outputs"]["widget"]["facts"]["volume"] == 1000.0
    assert accepted is not None
    assert accepted["display"]["widget"]["artifact_path"] == "/staging/widget.brep"


def test_a_read_only_op_is_not_given_a_revision() -> None:
    client = FakeCadexd(
        replies={
            "inspect": {
                "ok": True,
                "scope": "output",
                "target": "",
                "path": "",
                "value": {"outputs": []},
                "page": None,
                "document": {},
                "surface": {},
                "result_json_bytes": 2,
            }
        }
    )
    with Bridge(client, initial_revision="rev-1") as bridge:
        _rpc(
            bridge, "tools/call", {"name": "inspect", "arguments": {"scope": "output"}}
        )
    assert client.args_for("inspect") == [{"scope": "output"}]


def test_an_unknown_tool_is_refused_without_reaching_the_engine() -> None:
    client = FakeCadexd()
    with Bridge(client) as bridge:
        reply = _rpc(bridge, "tools/call", {"name": "rm_rf", "arguments": {}})
    assert reply["result"]["isError"] is True
    assert client.calls == []


def test_a_dead_engine_becomes_a_tool_error_the_model_can_read() -> None:
    """Not a transport error: the model must be able to say what happened."""

    class Dead(FakeCadexd):
        def request(self, op, args=None, **kwargs):
            raise RuntimeError("the engine closed its protocol stream.")

    with Bridge(Dead()) as bridge:
        reply = _rpc(
            bridge, "tools/call", {"name": "rebuild", "arguments": {}}
        )
    assert reply["result"]["isError"] is True
    payload = json.loads(reply["result"]["content"][0]["text"])
    assert payload["failure_code"] == "CADEXD_UNREACHABLE"


# -- the socket itself ---------------------------------------------------


def test_the_bridge_refuses_a_wrong_token(bridge) -> None:
    reply = mcp.bridge_request(
        str(bridge.socket_path), "not-the-token", {"op": "list_tools"}
    )
    assert reply == {"error": "bad bridge token"}


def test_the_socket_lives_in_a_private_directory(bridge) -> None:
    directory = bridge.socket_path.parent
    assert directory.stat().st_mode & 0o077 == 0


def test_the_socket_is_gone_after_the_bridge_stops() -> None:
    client = FakeCadexd()
    bridge = Bridge(client).start()
    path = bridge.socket_path
    bridge.stop()
    assert not path.exists()


def test_serve_reads_newline_delimited_messages(bridge) -> None:
    """The stdio transport, driven the way ``claude`` drives it."""

    stdin = io.StringIO(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        + "\n"
        + "\n"  # a blank line is not a message
        + "{not json}\n"  # nor is garbage
        + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        + "\n"
    )
    stdout = io.StringIO()
    mcp.serve(str(bridge.socket_path), bridge.token, stdin, stdout)

    replies = [json.loads(line) for line in stdout.getvalue().splitlines() if line]
    assert [reply["id"] for reply in replies] == [1, 2]
    assert len(replies[1]["result"]["tools"]) == len(CLI_TOOL_OPS)


def test_tools_list_reports_an_unreachable_bridge_rather_than_hanging() -> None:
    stream = io.StringIO()
    mcp.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        "/nonexistent/socket",
        "token",
        stream,
    )
    assert json.loads(stream.getvalue())["error"]["code"] == -32000
