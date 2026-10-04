# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``cadex mcp``'s transport: MCP over stdio, answered by a tool host (ADR-538).

Cadex has no agent of its own. Any agent that speaks MCP -- Claude Code,
Codex, Pi -- registers ``cadex mcp --project DIR`` as a stdio server and
gets the project's tools and the guidance that goes with them. This module is
only the wire: newline-delimited JSON-RPC 2.0 on stdin/stdout, the subset
every client exercises -- ``initialize``, ``notifications/initialized``,
``ping``, ``tools/list``, ``tools/call`` -- and a proper ``-32601`` for
anything else. What the tools do is the host's: :class:`ToolHost`, which
``cadex mcp`` implements with the project's engine and the bridge.

The guidance travels as the ``instructions`` of the ``initialize`` result,
which is where an MCP client puts a server's own system-prompt text, so a
client that reads it needs no other setup. ``cadex guidance`` prints the
same text for one that does not.

The host is told when the client has gone quiet: :func:`serve` waits for
the next message at most ``idle_seconds`` and calls ``host.idle()`` when
none came, so the host can let go of what it holds -- the project lock,
above all, so the agent's own ``cadex`` commands on the same project get
through between bursts of tool calls.
"""

from __future__ import annotations

import json
import os
import select
from typing import Any, BinaryIO, Protocol

SERVER_NAME = "cadex"
SERVER_VERSION = "0.2.0"
DEFAULT_PROTOCOL_VERSION = "2024-11-05"


class ToolHost(Protocol):
    """What answers the tools: the engine, behind :class:`cadex_cli.bridge.Bridge`."""

    def instructions(self) -> str: ...

    def tools(self) -> list[dict[str, Any]]:
        """Each tool as ``{"name", "description", "input_schema"}``."""

    def call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """``{"content": [MCP content blocks], "is_error": bool}``."""

    def idle(self) -> None:
        """The client sent nothing for a while; let go of what can be reopened."""


def _write(message: dict[str, Any], stream: Any) -> None:
    stream.write(json.dumps(message) + "\n")
    stream.flush()


def _result(message_id: Any, result: dict[str, Any], stream: Any) -> None:
    _write({"jsonrpc": "2.0", "id": message_id, "result": result}, stream)


def _error(message_id: Any, code: int, message: str, stream: Any) -> None:
    _write({"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}, stream)


def handle(message: dict[str, Any], host: ToolHost, stream: Any) -> None:
    """Answer one JSON-RPC message. Split out so the tests can drive it."""

    method = str(message.get("method") or "")
    message_id = message.get("id")

    if method == "initialize":
        params = message.get("params") or {}
        _result(
            message_id,
            {
                # Echo the client's version: this server speaks the subset
                # every revision of MCP shares.
                "protocolVersion": params.get("protocolVersion", DEFAULT_PROTOCOL_VERSION),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": host.instructions(),
            },
            stream,
        )
    elif method == "notifications/initialized":
        pass
    elif method == "ping":
        _result(message_id, {}, stream)
    elif method == "tools/list":
        tools = [{"name": tool["name"], "description": tool["description"],
                  "inputSchema": tool["input_schema"]} for tool in host.tools()]
        _result(message_id, {"tools": tools}, stream)
    elif method == "tools/call":
        params = message.get("params") or {}
        try:
            reply = host.call(str(params.get("name") or ""), dict(params.get("arguments") or {}))
        except Exception as exc:  # the engine failing to open must reach the model
            # A tool result, not a JSON-RPC error: the model can read this one
            # and say so, where a transport error just ends its turn.
            reply = {"content": [{"type": "text", "text": f"Cadex could not run the tool: {exc}"}],
                     "is_error": True}
        _result(message_id, {"content": reply.get("content", []),
                             "isError": bool(reply.get("is_error", False))}, stream)
    elif message_id is not None:
        _error(message_id, -32601, f"Method not found: {method}", stream)


def serve(host: ToolHost, stdin: BinaryIO, stdout: Any, *, idle_seconds: float = 0.0) -> None:
    """Answer messages until stdin closes; ``host.idle()`` after each quiet spell.

    Reads the raw descriptor, not a buffered reader, so waiting with
    ``select`` never misses a line already buffered.
    """

    fd = stdin.fileno()
    pending = b""
    quiet_since_idle = True
    while True:
        while b"\n" not in pending:
            wait = idle_seconds if idle_seconds > 0 and not quiet_since_idle else None
            ready, _, _ = select.select([fd], [], [], wait)
            if not ready:
                host.idle()
                quiet_since_idle = True
                continue
            chunk = os.read(fd, 65536)
            if not chunk:
                return
            pending += chunk
        line, pending = pending.split(b"\n", 1)
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            continue
        if isinstance(message, dict):
            handle(message, host, stdout)
            quiet_since_idle = False
