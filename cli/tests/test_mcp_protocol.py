# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``cadex mcp``'s transport, the bridge, and the tool surface they publish.

Everything here runs against :mod:`fake_cadexd`, so what is under test is
the plumbing: the JSON-RPC subset an MCP client needs, the stdio loop and
its idle callback, the schemas generated from ``OP_ARG_SPECS``, and the
revision the model never has to supply (ADR-538).
"""

from __future__ import annotations

import io
import json
import os
import threading
from typing import Any

import pytest

from cadex_cli import mcp
from cadex_cli.bridge import BUILD_VIEW_LIST_LIMIT, Bridge
from cadex_cli.tools import BRIDGE_TOOLS, CLI_TOOL_OPS, tool_definitions

from fake_cadexd import (
    anatomy_value,
    inventory_value,
    FakeCadexd, accepted_reply, clearance_value, inspect_reply, rejected_reply,
)


@pytest.fixture
def bridge():
    client = FakeCadexd()
    with Bridge(client) as running:
        yield running


class _Host:
    """The bridge as ``cadex mcp`` hosts it, without an engine to open."""

    def __init__(self, bridge: Bridge) -> None:
        self.bridge = bridge
        self.idled = 0

    def instructions(self) -> str:
        return "the guidance"

    def tools(self) -> list[dict[str, Any]]:
        return self.bridge.tools()

    def call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.bridge.call(tool, arguments)

    def idle(self) -> None:
        self.idled += 1


def _rpc(bridge: Bridge, method: str, params: dict[str, Any] | None = None, id_: Any = 1):
    stream = io.StringIO()
    message: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
    if id_ is not None:
        message["id"] = id_
    if params is not None:
        message["params"] = params
    mcp.handle(message, _Host(bridge), stream)
    raw = stream.getvalue()
    return json.loads(raw) if raw.strip() else None


# -- the JSON-RPC subset -------------------------------------------------


def test_initialize_echoes_the_client_protocol_version(bridge) -> None:
    reply = _rpc(bridge, "initialize", {"protocolVersion": "2025-06-18"})
    assert reply["result"]["protocolVersion"] == "2025-06-18"
    assert reply["result"]["capabilities"] == {"tools": {}}
    assert reply["result"]["serverInfo"]["name"] == "cadex"
    assert reply["result"]["instructions"] == "the guidance"


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
    assert [tool["name"] for tool in tools] == list(CLI_TOOL_OPS) + list(BRIDGE_TOOLS)
    for tool in tools:
        assert tool["description"]
        assert tool["inputSchema"]["type"] == "object"


def test_the_schemas_cannot_drift_from_op_arg_specs(protocol) -> None:
    """Every schema property is an argument the protocol declares.

    This is the point of generating them. A tool that offers an argument the
    engine does not take is a tool call that fails at the protocol layer for
    a reason the model cannot act on.
    """

    from cadex_cli.tools import VIEW_ARGS

    for tool in tool_definitions(protocol):
        if tool["name"] in BRIDGE_TOOLS:
            # Answered by the bridge itself (ADR-406): no engine op to drift
            # from, and never a name the engine serves.
            assert tool["name"] not in protocol.OP_ARG_SPECS
            continue
        required, optional = protocol.OP_ARG_SPECS[tool["name"]]
        declared = set(required) | set(optional)
        # The one allowed drift is the bridge's own view arguments
        # (ADR-360), which it consumes before the engine sees the call.
        declared |= {name for op, name in VIEW_ARGS if op == tool["name"]}
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


#: Heron's shape, as F5 measured it over four turns (ADR-362): a printed
#: base, two servos placed from one drilled catalog body -- so two
#: uncatalogued components but one uncatalogued source -- a catalog horn
#: and two catalog bearings. Six components, three catalogued, three not.
_INVENTORY = [
    {"component": "base", "label": "base", "source_output": "base_plate"},
    {"component": "shoulder_servo", "label": "shoulder", "source_output": "servo_drilled",
     "catalog_derived_from": {"family": "servo", "part_number": "MG90S"}},
    {"component": "elbow_servo", "label": "elbow", "source_output": "servo_drilled",
     "catalog_derived_from": {"family": "servo", "part_number": "MG90S"}},
    {"component": "horn", "label": "horn", "source_output": "horn",
     "catalog": {"family": "horn", "part_number": "SG-25T-1"}},
    {"component": "bearing_a", "label": "bearing a", "source_output": "mr128",
     "catalog": {"family": "bearing", "part_number": "MR128"}},
    {"component": "bearing_b", "label": "bearing b", "source_output": "mr128",
     "catalog": {"family": "bearing", "part_number": "MR128"}},
]


def _fit_client(pairs, inventory=None, sweep=None, **replies):
    def inspect(args):
        if args["scope"] == "inventory":
            return inspect_reply(args, inventory_value(inventory))
        if args["scope"] == "anatomy":
            return inspect_reply(args, anatomy_value())
        assert args["scope"] == "clearance", args
        return inspect_reply(args, clearance_value(pairs, sweep=sweep))
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
    assert [op for op, _ in client.calls] == ["write_script", "inspect", "inspect", "inspect"]
    assert [a["scope"] for a in client.args_for("inspect")] == ["clearance", "inventory", "anatomy"]
    # ...and the parent saw the same thing the model did: one failing pair
    # is under the view's limit, so the bounded view is the whole block.
    assert call.fit == last_fit
    assert last_fit["failing"] == fit["failing"] and last_fit["counts"] == fit["counts"]
    assert ("fit fail: 1 failing of 2 pair(s)  sweep unavailable: no published sweep  "
            "inventory unavailable") in call.summary


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
    assert ("fit unavailable  sweep unavailable: no published sweep  "
            "inventory unavailable") in call.summary


@pytest.mark.parametrize("sweep,phrase", [
    ({"status": "complete", "joints": [
        {"joint": "knee", "kind": "revolute", "unit": "degrees",
         "status": "complete", "pairs": [
             {"first": "a", "second": "b", "minimum_distance_mm": 2.0,
              "maximum_common_volume_mm3": 0.0, "first_contact_degrees": None}]}]},
     "sweep pass: 1 joint(s) swept"),
    ({"status": "complete", "joints": [
        {"joint": "knee", "kind": "revolute", "unit": "degrees",
         "status": "complete", "pairs": [
             {"first": "a", "second": "b", "minimum_distance_mm": 0.0,
              "maximum_common_volume_mm3": 8.0, "first_contact_degrees": -20.0}]}]},
     "sweep fail: 1 failing pair(s) over 1 of 1 joint(s) swept"),
    # A gap the motion closes, with nothing overlapping anywhere (ADR-378):
    # `b`/`c` is `_CLEAR`'s pair, 10 mm apart at the solved pose, and the
    # hinge takes it to 0.04 mm. Before this the phrase was `sweep pass`.
    ({"status": "complete", "joints": [
        {"joint": "knee", "kind": "revolute", "unit": "degrees",
         "status": "complete", "pairs": [
             {"first": "b", "second": "c", "relative_motion": True,
              "minimum_distance_mm": 0.04,
              "maximum_common_volume_mm3": 0.0, "first_contact_degrees": None}]}]},
     "sweep fail: 1 failing pair(s) over 1 of 1 joint(s) swept"),
    ({"status": "incomplete", "joints": [
        {"joint": "knee", "kind": "revolute", "unit": "degrees",
         "status": "incomplete", "reason": "sweep_step_degrees is not declared"}]},
     "sweep incomplete: 1 of 1 joint(s) unswept"),
])
def test_the_progress_line_carries_the_swept_half(sweep, phrase) -> None:
    """The parent's one-line summary says both halves (ADR-366).

    A swept overlap must never reach the log as a bare `fit pass`: the
    static verdict is the solved pose, and the phrase beside it is the
    motion. Coverage travels with the count, so no number appears without
    the joints it was measured over.
    """

    client = _fit_client([_CLEAR], sweep=sweep)
    with Bridge(client, initial_revision="rev-1") as bridge:
        payload = json.loads(
            bridge.call("write_script", {"source": "x"})["content"][0]["text"]
        )
        (call,) = bridge.state.calls
    assert payload["fit"]["verdict"] == "pass"
    assert f"fit pass: 0 failing of 1 pair(s)  {phrase}" in call.summary
    assert payload["fit"]["sweep"]["verdict"] == phrase.split()[1].rstrip(":")


def test_sixty_failing_pairs_reach_the_model_worst_first_and_counted() -> None:
    """Sixty failing pairs of sixty-three: counted whole, listed worst first.

    ADR-346 put every failing pair in the reply. At robot scale that reply
    passed the harness's result cap, and the agent got none of them
    (ADR-435). The model's view now carries the full counts, the worst
    ``BUILD_VIEW_LIST_LIMIT`` rows with their distance and volume, and
    the number cut and where they are read. The parent keeps all sixty.
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
    rows = [
        (r["first"], r["second"], r["distance_mm"], r["common_volume_mm3"])
        for i, r in enumerate(pairs) if i % 21 != 20
    ]
    assert len(rows) == 60
    worst = sorted(rows, key=lambda row: (-row[3], row[2]))[:BUILD_VIEW_LIST_LIMIT]
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
    ] == worst
    assert fit["failing_omitted"] == 60 - BUILD_VIEW_LIST_LIMIT
    assert fit["failing_rest"].startswith("inspect scope=clearance path=/pairs")
    assert [
        (f["first"], f["second"], f["distance_mm"], f["common_volume_mm3"])
        for f in call.fit["failing"]
    ] == rows
    assert ("fit fail: 60 failing of 63 pair(s)  sweep unavailable: no published sweep  "
            "inventory unavailable") in call.summary


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
            assert "inventory" not in payload, tool
    calls = [op for op, _ in client.calls]
    # Four fit reads, four inventory reads, four anatomy reads (ADR-614)
    # and the model's own.
    assert calls.count("inspect") == 13


def test_a_refused_build_carries_no_fit_block() -> None:
    client = FakeCadexd(replies={"write_script": lambda _a: rejected_reply("rev-9")})
    with Bridge(client, initial_revision="rev-1") as bridge:
        reply = bridge.call("write_script", {"source": "x"})
        (call,) = bridge.state.calls
        assert bridge.state.last_fit is None
    assert reply["is_error"] is True
    payload = json.loads(reply["content"][0]["text"])
    assert "fit" not in payload and "inventory" not in payload
    assert call.fit is None and call.inventory is None
    assert bridge.state.last_inventory is None
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
    # The inventory read fails the same way and is reported the same way.
    assert payload["inventory"]["available"] is False
    assert "store unreadable" in payload["inventory"]["error"]
    assert payload["inventory"]["uncatalogued_sources"] == []


# -- the inventory block (ADR-362) -------------------------------------------


def test_a_build_reply_carries_catalog_identity_beside_the_fit() -> None:
    """The script says every purchased part is catalog; the inventory says
    the two servos are placed from a drilled body and are not (ADR-362).

    Known answer from the fixture: six components, three catalogued (one
    horn, two MR128 bearings), three uncatalogued components over two
    uncatalogued sources -- the printed base and the one drilled servo
    body placed twice. The count is per component and the names are per
    source, and both reach the model on the build reply itself.
    """

    client = _fit_client([_CLEAR], inventory=_INVENTORY)
    write = accepted_reply("write", "rev-2")
    write["stdout"] = "all purchased parts are catalog parts\n"
    client.replies["write_script"] = write
    with Bridge(client, initial_revision="rev-1") as bridge:
        payload = json.loads(
            bridge.call("write_script", {"source": "x"})["content"][0]["text"]
        )
        (call,) = bridge.state.calls
        last = bridge.state.last_inventory

    assert payload["stdout"] == "all purchased parts are catalog parts\n"
    assert payload["fit"]["verdict"] == "pass"  # fit is untouched by this
    inventory = payload["inventory"]
    assert inventory["available"] is True
    assert inventory["component_count"] == 6
    assert inventory["catalogued_count"] == 3
    assert inventory["uncatalogued_count"] == 3
    assert inventory["catalog_counts"] == {"bearing/MR128": 2, "horn/SG-25T-1": 1}
    assert inventory["uncatalogued_sources"] == ["base_plate", "servo_drilled"]
    # ...and which of those two is the defect rather than the printed part
    # (ADR-381): the base plate is expected here, the servo body is not.
    assert inventory["derived_catalog_sources"] == [
        {"source_output": "servo_drilled", "family": "servo",
         "part_number": "MG90S"},
    ]
    assert "servo_drilled (cut from servo/MG90S)" in inventory["note"]
    assert "inspect scope=inventory" in inventory["source"]
    assert "stdout" in inventory["source"] and "Advisory" in inventory["source"]
    assert "lost its catalog identity" in inventory["note"]
    # The parent kept the whole block, and the progress line says it.
    assert call.inventory == last and last["appearance"] == {}
    assert inventory["appearance"] == {}
    assert call.summary.endswith(
        "fit pass: 0 failing of 1 pair(s)  sweep unavailable: no published sweep  "
        "inventory: 6 component(s), 3 catalogued, 3 uncatalogued"
    )


def test_a_partless_build_says_inventory_unavailable_not_all_catalog() -> None:
    client = _fit_client([], inventory=[])
    with Bridge(client, initial_revision="rev-1") as bridge:
        payload = json.loads(
            bridge.call("write_script", {"source": "x"})["content"][0]["text"]
        )
        (call,) = bridge.state.calls
    inventory = payload["inventory"]
    assert inventory["available"] is False
    assert inventory["component_count"] == 0 and inventory["catalogued_count"] == 0
    assert "places none" in inventory["note"]
    assert call.summary.endswith(
        "fit unavailable  sweep unavailable: no published sweep  inventory unavailable")


def test_the_inventory_block_is_advisory_and_refuses_nothing() -> None:
    """Three uncatalogued components, fit passing: the build is accepted
    and the reply is not an error. Uncatalogued is a fact, not a failure."""

    client = _fit_client([_CLEAR], inventory=_INVENTORY)
    with Bridge(client, initial_revision="rev-1") as bridge:
        reply = bridge.call("write_script", {"source": "x"})
    assert reply["is_error"] is False
    payload = json.loads(reply["content"][0]["text"])
    assert payload["ok"] is True
    assert payload["inventory"]["uncatalogued_count"] == 3
    assert "verdict" not in payload["inventory"]
    assert "failing" not in payload["inventory"]


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
    assert payload["outputs"]["detail"] == [{"name": "widget", "facts": {"volume": 1000.0}}]
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


# -- the stdio loop ------------------------------------------------------


def _pipe(text: str):
    read, write = os.pipe()
    os.write(write, text.encode("utf-8"))
    os.close(write)
    return os.fdopen(read, "rb", buffering=0)


def test_serve_reads_newline_delimited_messages(bridge) -> None:
    """The stdio transport, driven the way an MCP client drives it."""

    stdin = _pipe(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        + "\n"
        + "\n"  # a blank line is not a message
        + "{not json}\n"  # nor is garbage
        + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        + "\n"
    )
    stdout = io.StringIO()
    mcp.serve(_Host(bridge), stdin, stdout)

    replies = [json.loads(line) for line in stdout.getvalue().splitlines() if line]
    assert [reply["id"] for reply in replies] == [1, 2]
    assert len(replies[1]["result"]["tools"]) == len(CLI_TOOL_OPS) + len(BRIDGE_TOOLS)


def test_a_quiet_client_lets_the_host_go_once_per_quiet_spell(bridge) -> None:
    """``idle()`` once after a message and a quiet spell, not again until the
    next message: the host is not woken to close what it already closed."""

    read, write = os.pipe()
    host, stdout = _Host(bridge), io.StringIO()
    thread = threading.Thread(target=mcp.serve, args=(host, os.fdopen(read, "rb", buffering=0), stdout),
                              kwargs={"idle_seconds": 0.05})
    thread.start()
    try:
        os.write(write, (json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}) + "\n").encode())
        threading.Event().wait(0.4)
        assert host.idled == 1
        os.write(write, (json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping"}) + "\n").encode())
        threading.Event().wait(0.4)
        assert host.idled == 2
    finally:
        os.close(write)
        thread.join(timeout=5)
    assert not thread.is_alive()
    assert [json.loads(line)["id"] for line in stdout.getvalue().splitlines()] == [1, 2]


def test_a_host_that_cannot_open_the_engine_is_a_tool_error() -> None:
    """The engine failing to open -- the project busy, no engine -- reaches
    the model as a result it can read, not a transport error."""

    class Closed(_Host):
        def call(self, tool, arguments):
            raise RuntimeError("project busy")

    stream = io.StringIO()
    mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "rebuild", "arguments": {}}}, Closed(Bridge(FakeCadexd())), stream)
    result = json.loads(stream.getvalue())["result"]
    assert result["isError"] is True and "project busy" in result["content"][0]["text"]



def _contract(description: str) -> dict[str, Any]:
    """A ``describe_api`` reply whose exports carry whole docstrings."""

    export = {"name": "collision", "signature": "(self, kind: 'str')", "description": description}
    return {
        "ok": True,
        "domain": "project",
        "domains": {"assembly": {"exports": [export, {"name": "bare"}], "notes": "keep"}},
        "engine": "fake",
        "instructions": "i",
        "program_schema": "s",
        "result_contract": "r",
        "revision_rule": "v",
        "source_globals": ["part"],
        "parameters": {},
        "connections": {},
        "boards": {},
        "mounts": {},
        "cages": {},
        "library": {"exports": [dict(export, name="bearing")], "catalog": {"bearings": {}}},
        "mutation_selection": {},
    }


def test_describe_api_offers_section_and_nothing_else_does(protocol) -> None:
    """``section`` is the bridge's argument, on ``describe_api`` alone (ADR-360)."""

    offered = {
        tool["name"]: tool["input_schema"]["properties"] for tool in tool_definitions(protocol)
    }
    assert "section" in offered["describe_api"]
    assert offered["describe_api"]["section"]["type"] == "string"
    assert "library" in offered["describe_api"]["section"]["description"]
    assert "section" not in tool_definitions(protocol)[0]["input_schema"]["required"]
    assert not any("section" in props for name, props in offered.items() if name != "describe_api")
    # ...and the engine's op still takes nothing: the page is cut here.
    assert protocol.OP_ARG_SPECS["describe_api"] == ({}, {})


def test_describe_api_reaches_the_model_as_an_index_of_names() -> None:
    """Without ``section`` the contract is its index (ADR-360).

    On 2026-09-15 the whole reply was 163,200 characters and the harness
    refused it; cut to one paragraph per export (ADR-359) it was 82,523 and
    was refused again, while every result the harness accepted was under
    21,742. So the default page carries no signature at all: the domains
    list their exports by name, the library lists its catalog families, and
    a ``sections`` line says where the signatures are.
    """

    from cadex_cli.bridge import API_VIEW_SECTIONS_NOTE

    long = "Declare what one body\nmay touch.\n\nSeven kinds, in two groups.\n\n" + "x" * 5000
    client = FakeCadexd(replies={"describe_api": _contract(long)})
    with Bridge(client, initial_revision="rev-1") as bridge:
        result = _rpc(bridge, "tools/call", {"name": "describe_api", "arguments": {}})
    text = result["result"]["content"][0]["text"]
    view = json.loads(text)

    assert result["result"]["isError"] is False
    assert view["domains"]["assembly"] == {"exports": ["collision", "bare"]}
    assert view["library"] == {"exports": ["bearing"], "catalog": ["bearings"]}
    assert view["sections"] == API_VIEW_SECTIONS_NOTE
    assert "describe_api section=<name>" in view["sections"]
    assert view["instructions"] == "i" and view["program_schema"] == "s"
    assert '"signature"' not in text and "keep" not in text and "xxxx" not in text
    assert client.args_for("describe_api") == [{}]


def test_a_describe_api_section_carries_signatures_and_first_paragraphs() -> None:
    """One section is one page: notes, signatures, summaries, and the way to the rest."""

    long = "Declare what one body\nmay touch.\n\nSeven kinds, in two groups.\n\n" + "x" * 5000
    client = FakeCadexd(replies={"describe_api": _contract(long)})
    with Bridge(client, initial_revision="rev-1") as bridge:
        result = _rpc(
            bridge, "tools/call", {"name": "describe_api", "arguments": {"section": "assembly"}}
        )
        library = _rpc(
            bridge, "tools/call", {"name": "describe_api", "arguments": {"section": "library"}}
        )
    text = result["result"]["content"][0]["text"]
    view = json.loads(text)

    assert result["result"]["isError"] is False
    assert view["section"] == "assembly" and view["ok"] is True
    assert view["exports"] == [
        {
            "name": "collision",
            "signature": "(self, kind: 'str')",
            "description": "Declare what one body may touch.",
        },
        {"name": "bare"},
    ]
    assert view["notes"] == "keep"
    assert "inspect scope=api path=/domains/assembly/exports/N/description" in view["descriptions"]
    assert "xxxx" not in text and "instructions" not in view

    lib = json.loads(library["result"]["content"][0]["text"])
    assert lib["section"] == "library" and lib["catalog"] == {"bearings": {}}
    assert lib["exports"][0]["description"] == "Declare what one body may touch."
    assert "path=/library/exports/N/description" in lib["descriptions"]
    # `section` never reached the engine, and its reply is what it was.
    assert client.args_for("describe_api") == [{}, {}]
    assert client.replies["describe_api"]["domains"]["assembly"]["exports"][0]["description"] == long


def test_a_section_the_contract_lacks_is_refused_by_name() -> None:
    """A wrong section is an error the model can act on: it names the right ones."""

    client = FakeCadexd(replies={"describe_api": _contract("d")})
    with Bridge(client, initial_revision="rev-1") as bridge:
        result = _rpc(
            bridge, "tools/call", {"name": "describe_api", "arguments": {"section": "sketch"}}
        )
    view = json.loads(result["result"]["content"][0]["text"])

    assert result["result"]["isError"] is True
    assert view["failure_code"] == "NO_SUCH_SECTION"
    assert view["sections"] == ["assembly", "library"]
    assert "'sketch'" in view["error"] and "assembly, library" in view["error"]
    assert client.args_for("describe_api") == [{}]


# -- the anatomy block (ADR-614) ---------------------------------------------


def test_a_build_reply_carries_the_anatomy_block_bounded() -> None:
    """A heron's head welded to its neck reads rigid with no reason beside
    the articulated neck, and the parent keeps the whole block."""

    neck = {"region": "neck", "status": "articulated", "components": ["lower_neck", "upper_neck"],
            "joints": [{"joint": "neck", "kind": "revolute", "dof": 1, "drive": "actuated",
                        "actuators": 1}],
            "joint_dof": 1, "actuated_dof": 1, "parent_region": "spine"}
    head = {"region": "head", "status": "rigid, no reason",
            "components": [f"part_{i}" for i in range(9)], "joints": [],
            "joint_dof": 0, "actuated_dof": 0, "welded_to": ["neck"]}
    welded = {"components": ["head", "tof"], "welded_to": "upper_neck", "joint": "w_head",
              "extent_mm": [225.0, 30.0, 53.4], "protrudes_mm": 152.1, "toward": "+x",
              "regions": ["head"], "acknowledged": False, "component_count": 2}
    value = anatomy_value([neck, head], verdict="incomplete", appendages=[welded])

    def inspect(args):
        if args["scope"] == "anatomy":
            return inspect_reply(args, value)
        return inspect_reply(args, inventory_value() if args["scope"] == "inventory"
                             else clearance_value())

    client = FakeCadexd(replies={"inspect": inspect})
    with Bridge(client, initial_revision="rev-1") as bridge:
        payload = json.loads(bridge.call("write_script", {"source": "x"})["content"][0]["text"])
        assert bridge.state.last_anatomy == value
    block = payload["anatomy"]
    assert block["verdict"] == "incomplete" and block["full"] == "inspect scope=anatomy"
    assert block["actuated_dof"] == 1 and block["unacknowledged_appendages"] == 1
    assert [r["status"] for r in block["regions"]] == ["articulated", "rigid, no reason"]
    assert block["regions"][0]["joints"] == ["neck (revolute, actuated)"]
    assert block["regions"][1]["components"] == {
        "first": [f"part_{i}" for i in range(6)], "count": 9}
    assert block["rigid_appendages"][0]["joint"] == "w_head"
    assert "source" not in block


def test_an_engine_without_the_scope_reports_anatomy_unavailable() -> None:
    """An older engine refuses the scope; the build is still accepted."""

    def inspect(args):
        if args["scope"] == "anatomy":
            return {
                "ok": False, "tool": "core.inspect", "error": "Unknown core.inspect scope",
                "failure_code": "INSPECTION_FAILED", "failure_stage": "precondition",
                "observed": {}, "normalized": {}, "requested": {}, "retry": False,
                "candidates": [], "allowed_values": [], "native_diagnostics": [],
                "state_change": "none",
            }
        return inspect_reply(args, clearance_value())

    with Bridge(FakeCadexd(replies={"inspect": inspect}), initial_revision="rev-1") as bridge:
        reply = bridge.call("write_script", {"source": "x"})
    assert reply["is_error"] is False
    block = json.loads(reply["content"][0]["text"])["anatomy"]
    assert block["verdict"] == "unavailable" and "Unknown core.inspect scope" in block["error"]
