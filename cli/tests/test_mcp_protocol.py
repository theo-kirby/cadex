# SPDX-FileCopyrightText: 2026 Cadex Authors
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

from fake_cadexd import (
    FakeCadexd, accepted_reply, clearance_value, inspect_reply, rejected_reply,
)


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
    # `blueprint` is served and the asymmetry with `image` is the point
    # (ADR-150): a reference image is a shell-only input, a blueprint sheet
    # is a stored deliverable this client exports. Writing one stays
    # shell-only — nothing headless can render.
    assert "blueprint" in offered
    assert "put_blueprint" not in CLI_TOOL_OPS
    # The measured fit is on the surface whole (ADR-346): the `fit` block a
    # build reply carries is a summary of this scope.
    assert "clearance" in offered


# -- the fit block (ADR-346) -----------------------------------------------


_OVERLAP = {
    "first": "a", "second": "b", "first_label": "a", "second_label": "b",
    "first_catalog": None, "second_catalog": None,
    "distance_mm": 0.0, "common_volume_mm3": 100.0,
}
_CLEAR = {**_OVERLAP, "first": "b", "second": "c", "distance_mm": 10.0,
          "common_volume_mm3": 0.0}


def _fit_client(pairs, **replies):
    def inspect(args):
        assert args["scope"] == "clearance", args
        return inspect_reply(args, clearance_value(pairs))
    write = accepted_reply("write", "rev-2")
    write["stdout"] = "no overlap\n"
    return FakeCadexd(replies={"write_script": write, "inspect": inspect, **replies})


def test_a_build_reply_carries_the_measured_fit_beside_the_stdout() -> None:
    """The script says "no overlap"; the engine's measurement says 100 mm³."""

    client = _fit_client([_OVERLAP, _CLEAR])
    with Bridge(client, initial_revision="rev-1") as bridge:
        reply = _rpc(
            bridge, "tools/call", {"name": "write_script", "arguments": {"source": "x"}}
        )
        (call,) = bridge.state.calls
        last_fit = bridge.state.last_fit

    assert reply["result"]["isError"] is False
    payload = json.loads(reply["result"]["content"][0]["text"])
    assert payload["stdout"] == "no overlap\n"
    fit = payload["fit"]
    assert fit["verdict"] == "fail"
    assert fit["pairs_checked"] == 2 and fit["failing_count"] == 1
    assert fit["counts"] == {
        "clear": 1, "intersection": 1, "below clearance": 0, "unknown": 0,
    }
    (failing,) = fit["failing"]
    assert (failing["first"], failing["second"]) == ("a", "b")
    assert failing["status"] == "intersection"
    assert failing["common_volume_mm3"] == 100.0 and failing["distance_mm"] == 0.0
    assert "stdout" in fit["source"] and "inspect scope=clearance" in fit["source"]
    # It was read from the store the build published to, after the build.
    assert [op for op, _ in client.calls] == ["write_script", "inspect"]
    (asked,) = client.args_for("inspect")
    assert asked["scope"] == "clearance"
    # ...and the parent saw the same thing the model did.
    assert call.fit == fit and last_fit == fit
    assert call.summary.endswith("fit fail: 1 failing of 2 pair(s)")


def test_a_clear_build_says_pass_and_a_partless_build_says_unavailable() -> None:
    client = _fit_client([_CLEAR])
    with Bridge(client, initial_revision="rev-1") as bridge:
        payload = json.loads(
            bridge.call("write_script", {"source": "x"})["content"][0]["text"]
        )
    assert payload["fit"]["verdict"] == "pass"
    assert payload["fit"]["failing"] == []

    client = _fit_client([])
    with Bridge(client, initial_revision="rev-1") as bridge:
        payload = json.loads(
            bridge.call("write_script", {"source": "x"})["content"][0]["text"]
        )
        (call,) = bridge.state.calls
    assert payload["fit"]["verdict"] == "unavailable"
    assert payload["fit"]["pairs_checked"] == 0
    assert "assembly.component" in payload["fit"]["note"]
    assert call.summary.endswith("fit unavailable")


def test_a_build_reply_names_every_failing_pair_past_forty() -> None:
    """Sixty failing pairs of sixty-three reach the model whole (ADR-346).

    An earlier cut of the block stopped at forty and pointed at the scope
    for the rest. The charter asks for every failing pair in the reply
    itself, so this pins the count, every name, every distance and every
    volume on the text the model actually receives.
    """

    pairs = []
    for i in range(63):
        failing = i % 21 != 20  # three clear pairs, sixty failing
        pairs.append({
            **_OVERLAP, "first": f"part{i}", "second": f"part{i + 1}",
            "first_label": f"part{i}", "second_label": f"part{i + 1}",
            "distance_mm": 12.0 + i if not failing else (0.0 if i % 2 else 0.001 * (i + 1)),
            "common_volume_mm3": (0.25 + i) if (failing and i % 2) else 0.0,
        })
    expected = [
        (r["first"], r["second"], r["distance_mm"], r["common_volume_mm3"])
        for i, r in enumerate(pairs) if i % 21 != 20
    ]
    assert len(expected) == 60
    client = _fit_client(pairs)
    with Bridge(client, initial_revision="rev-1") as bridge:
        payload = json.loads(
            bridge.call("write_script", {"source": "x"})["content"][0]["text"]
        )
        (call,) = bridge.state.calls
    fit = payload["fit"]
    assert fit["verdict"] == "fail"
    assert fit["pairs_checked"] == 63 and fit["failing_count"] == 60
    assert fit["counts"] == {
        "clear": 3, "intersection": 30, "below clearance": 30, "unknown": 0,
    }
    assert [
        (f["first"], f["second"], f["distance_mm"], f["common_volume_mm3"])
        for f in fit["failing"]
    ] == expected
    assert "failing_truncated" not in fit and "note" not in fit
    assert call.fit == fit
    assert call.summary.endswith("fit fail: 60 failing of 63 pair(s)")


def test_every_modelling_op_carries_a_fit_block_and_no_read_does() -> None:
    client = _fit_client(
        [_OVERLAP],
        edit_script=accepted_reply("edit", "rev-3"),
        set_params=accepted_reply("set", "rev-4"),
        rebuild=accepted_reply("rebuild", "rev-5"),
    )
    with Bridge(client, initial_revision="rev-1") as bridge:
        for tool, arguments in (
            ("write_script", {"source": "x"}),
            ("edit_script", {"replacements": [{"old": "a", "new": "b"}]}),
            ("set_params", {"values": {"w": 1}}),
            ("rebuild", {}),
        ):
            payload = json.loads(bridge.call(tool, arguments)["content"][0]["text"])
            assert payload["fit"]["verdict"] == "fail", tool
        for tool, arguments in (
            ("describe_api", {}),
            ("inspect", {"scope": "clearance"}),
        ):
            payload = json.loads(bridge.call(tool, arguments)["content"][0]["text"])
            assert "fit" not in payload, tool
    calls = [op for op, _ in client.calls]
    assert calls.count("inspect") == 5  # four fit reads and the model's own


def test_a_refused_build_carries_no_fit_block() -> None:
    client = FakeCadexd(replies={"write_script": lambda _a: rejected_reply("rev-9")})
    with Bridge(client, initial_revision="rev-1") as bridge:
        reply = bridge.call("write_script", {"source": "x"})
        (call,) = bridge.state.calls
        assert bridge.state.last_fit is None
    assert reply["is_error"] is True
    assert "fit" not in json.loads(reply["content"][0]["text"])
    assert call.fit is None
    assert [op for op, _ in client.calls] == ["write_script"]


def test_a_fit_that_cannot_be_read_is_reported_and_refuses_nothing() -> None:
    """The build was accepted; a measurement the bridge cannot read says so."""

    def failing_inspect(args):
        return {
            "ok": False, "tool": "core.inspect", "error": "store unreadable",
            "failure_code": "INSPECT_FAILED", "failure_stage": "read",
            "observed": {}, "normalized": {}, "requested": {}, "retry": True,
            "candidates": [], "allowed_values": [], "native_diagnostics": [],
            "state_change": "none",
        }

    client = FakeCadexd(replies={"inspect": failing_inspect})
    with Bridge(client, initial_revision="rev-1") as bridge:
        reply = bridge.call("write_script", {"source": "x"})
    assert reply["is_error"] is False
    payload = json.loads(reply["content"][0]["text"])
    assert payload["ok"] is True and payload["revision"] == "rev-1"
    assert payload["fit"]["verdict"] == "unavailable"
    assert "store unreadable" in payload["fit"]["error"]


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
    assert sent == {
        "source": "x",
        "expected_revision": "rev-1",
        "display": {"quality": "standard", "edges": False},
    }
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


def test_every_modelling_op_carries_the_standard_display_request(protocol) -> None:
    """The accepted attempt must retain tessellation for review (ADR-312).

    A first accepted script written without ``display`` left a fresh
    project's dashboard saying ``accepted attempt retained no
    tessellation`` until a later public rebuild republished it. The bridge
    now asks for the same standard tessellation ``cadex params`` asks for,
    on every op that takes it, and overrules anything the model supplies —
    so the request is a constant, not a model choice.
    """

    client = FakeCadexd()
    with Bridge(client, initial_revision="rev-1") as bridge:
        for tool, arguments in (
            ("write_script", {"source": "x", "display": {"quality": "coarse"}}),
            ("edit_script", {"old": "a", "new": "b"}),
            ("set_params", {"values": {"k": 1}}),
            ("rebuild", {}),
            ("describe_api", {}),
            ("inspect", {"scope": "outputs"}),
        ):
            _rpc(bridge, "tools/call", {"name": tool, "arguments": arguments})
    for tool in ("write_script", "edit_script", "set_params", "rebuild"):
        (sent,) = client.args_for(tool)
        assert sent["display"] == {"quality": "standard", "edges": False}, tool
    for tool in ("describe_api", "inspect"):
        assert all("display" not in sent for sent in client.args_for(tool)), tool
    # ...and this list is the protocol's, not a second copy of it.
    from cadex_cli.tools import injects_display
    takes_display = {op for op in CLI_TOOL_OPS if injects_display(protocol, op)}
    assert takes_display == {"write_script", "edit_script", "set_params", "rebuild"}


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
