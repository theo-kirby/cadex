# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Standalone MCP stdio server that exposes Mesh's Blender tools to Claude Code.

This script is spawned *by the `claude` CLI* (via ``--mcp-config``), so it runs
outside the Blender process and must not import ``bpy``. Every MCP ``tools/call``
is relayed over a localhost TCP connection to the bridge server running inside
Blender (see ``bridge.py``), which executes the tool on Blender's main thread
and returns the result.

Only the Python standard library is used. The MCP stdio transport is
newline-delimited JSON-RPC 2.0 messages on stdin/stdout.

Usage (as arranged by backend.py):
    python mcp_shim.py --port <bridge-port> --token <auth-token>
"""

import argparse
import json
import socket
import sys


def bridge_request(port, token, payload):
    """Send one request to the Blender bridge and return the decoded reply."""
    payload = dict(payload)
    payload["token"] = token
    with socket.create_connection(("127.0.0.1", port), timeout=600.0) as sock:
        sock.sendall(json.dumps(payload).encode("utf-8") + b"\n")
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = sock.recv(65536)
            if not chunk:
                break
            buf += chunk
    return json.loads(buf.decode("utf-8"))


def _read_message(stream):
    """Read one newline-delimited JSON-RPC message; None on EOF."""
    line = stream.readline()
    if not line:
        return None
    line = line.strip()
    if not line:
        return {}
    return json.loads(line)


def _write_message(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _result(msg_id, result):
    _write_message({"jsonrpc": "2.0", "id": msg_id, "result": result})


def _error(msg_id, code, message):
    _write_message({"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}})


def _mcp_tool_defs(port, token):
    """Fetch tool definitions from the bridge, converted to MCP schema."""
    reply = bridge_request(port, token, {"op": "list_tools"})
    tools = []
    for tool in reply["tools"]:
        tools.append({
            "name": tool["name"],
            "description": tool["description"],
            "inputSchema": tool["input_schema"],
        })
    return tools


def serve(port, token):
    while True:
        try:
            msg = _read_message(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            continue
        if msg is None:
            return
        if not msg:
            continue

        method = msg.get("method", "")
        msg_id = msg.get("id")

        if method == "initialize":
            client_version = msg.get("params", {}).get("protocolVersion", "2024-11-05")
            _result(msg_id, {
                "protocolVersion": client_version,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mesh", "version": "0.1.0"},
            })
        elif method == "notifications/initialized":
            pass
        elif method == "ping":
            _result(msg_id, {})
        elif method == "tools/list":
            try:
                _result(msg_id, {"tools": _mcp_tool_defs(port, token)})
            except OSError as ex:
                _error(msg_id, -32000, "Mesh bridge unreachable: {!s}".format(ex))
        elif method == "tools/call":
            params = msg.get("params", {})
            try:
                reply = bridge_request(port, token, {
                    "op": "call",
                    "tool": params.get("name", ""),
                    "input": params.get("arguments", {}) or {},
                })
                _result(msg_id, {
                    "content": reply.get("content", []),
                    "isError": bool(reply.get("is_error", False)),
                })
            except OSError as ex:
                _result(msg_id, {
                    "content": [{"type": "text", "text": "Mesh bridge unreachable: {!s}".format(ex)}],
                    "isError": True,
                })
        elif msg_id is not None:
            _error(msg_id, -32601, "Method not found: {:s}".format(method))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    serve(args.port, args.token)


if __name__ == "__main__":
    main()
