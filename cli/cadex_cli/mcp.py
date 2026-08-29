# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The MCP stdio server ``claude`` spawns, and the socket it relays down.

Run as ``python <path>/mcp.py --socket <path> --token <token>``, arranged by
:mod:`cadex_cli.agent` through ``--mcp-config``. It is a *child of
``claude``*, not of the CLI, so it shares nothing with the parent but the
socket: no engine, no project, no state of its own beyond the request it is
relaying — and no import outside the standard library, which is what lets it
be started as a bare script path with nothing on ``PYTHONPATH``.

The transport is newline-delimited JSON-RPC 2.0 on stdin/stdout. Only the
subset Claude Code actually exercises is implemented — ``initialize``,
``notifications/initialized``, ``ping``, ``tools/list``, ``tools/call`` —
because a shim that answers methods nobody sends is a shim with untested
code in it. Anything else gets a proper ``-32601``.

Standard library only, and deliberately: this process is spawned by a
program we do not control, in an environment we did not set up.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
from typing import Any

SERVER_NAME = "cadex"
SERVER_VERSION = "0.1.0"
DEFAULT_PROTOCOL_VERSION = "2024-11-05"

#: Matches the bridge's own socket timeout: a rebuild may take minutes.
RELAY_TIMEOUT_SECONDS = 3600.0


class BridgeUnreachable(OSError):
    """The parent's bridge socket did not answer."""


def bridge_request(
    socket_path: str, token: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """One request down the bridge socket; one reply back."""

    message = dict(payload)
    message["token"] = token
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    connection.settimeout(RELAY_TIMEOUT_SECONDS)
    try:
        connection.connect(socket_path)
        connection.sendall(json.dumps(message).encode("utf-8") + b"\n")
        buffer = b""
        while not buffer.endswith(b"\n"):
            chunk = connection.recv(65536)
            if not chunk:
                break
            buffer += chunk
    finally:
        connection.close()
    if not buffer.strip():
        raise BridgeUnreachable("The Cadex bridge closed without answering.")
    return json.loads(buffer.decode("utf-8"))


def _write(message: dict[str, Any], stream: Any) -> None:
    stream.write(json.dumps(message) + "\n")
    stream.flush()


def _result(message_id: Any, result: dict[str, Any], stream: Any) -> None:
    _write({"jsonrpc": "2.0", "id": message_id, "result": result}, stream)


def _error(message_id: Any, code: int, message: str, stream: Any) -> None:
    _write(
        {
            "jsonrpc": "2.0",
            "id": message_id,
            "error": {"code": code, "message": message},
        },
        stream,
    )


def _mcp_tools(socket_path: str, token: str) -> list[dict[str, Any]]:
    reply = bridge_request(socket_path, token, {"op": "list_tools"})
    return [
        {
            "name": tool["name"],
            "description": tool["description"],
            "inputSchema": tool["input_schema"],
        }
        for tool in reply.get("tools", [])
    ]


def handle(
    message: dict[str, Any], socket_path: str, token: str, stream: Any
) -> None:
    """Answer one JSON-RPC message. Split out so the tests can drive it."""

    method = str(message.get("method") or "")
    message_id = message.get("id")

    if method == "initialize":
        params = message.get("params") or {}
        _result(
            message_id,
            {
                # Echo the client's version: this shim speaks the subset every
                # revision of MCP shares, so refusing one would be posturing.
                "protocolVersion": params.get(
                    "protocolVersion", DEFAULT_PROTOCOL_VERSION
                ),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
            stream,
        )
    elif method == "notifications/initialized":
        pass
    elif method == "ping":
        _result(message_id, {}, stream)
    elif method == "tools/list":
        try:
            _result(message_id, {"tools": _mcp_tools(socket_path, token)}, stream)
        except (OSError, ValueError) as exc:
            _error(message_id, -32000, f"Cadex bridge unreachable: {exc}", stream)
    elif method == "tools/call":
        params = message.get("params") or {}
        try:
            reply = bridge_request(
                socket_path,
                token,
                {
                    "op": "call",
                    "tool": params.get("name", ""),
                    "input": params.get("arguments") or {},
                },
            )
        except (OSError, ValueError) as exc:
            # A tool result, not a JSON-RPC error: the model can read this
            # one and say so, where a transport error just ends the turn.
            _result(
                message_id,
                {
                    "content": [
                        {"type": "text", "text": f"Cadex bridge unreachable: {exc}"}
                    ],
                    "isError": True,
                },
                stream,
            )
        else:
            _result(
                message_id,
                {
                    "content": reply.get("content", []),
                    "isError": bool(reply.get("is_error", False)),
                },
                stream,
            )
    elif message_id is not None:
        _error(message_id, -32601, f"Method not found: {method}", stream)


def serve(socket_path: str, token: str, stdin: Any, stdout: Any) -> None:
    while True:
        line = stdin.readline()
        if not line:
            return
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            continue
        if isinstance(message, dict):
            handle(message, socket_path, token, stdout)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cadex_cli.mcp")
    parser.add_argument("--socket", required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args(argv)
    serve(args.socket, args.token, sys.stdin, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
