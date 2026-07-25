# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Localhost TCP bridge between the MCP shim (running outside Blender) and the
Blender main thread.

``bpy`` is not thread-safe, so tool calls arriving on socket threads are queued
and executed by the agent's main-thread drain loop (a ``bpy.app.timers``
callback in the GUI, or a test-driven loop in background mode). The socket
thread blocks until the main thread has produced a result, which in turn keeps
the MCP shim — and therefore Claude Code — waiting for the tool result.

Wire protocol: one newline-delimited JSON request per connection.
  {"op": "list_tools", "token": ...}
      -> {"tools": [{name, description, input_schema}, ...]}
  {"op": "call", "tool": name, "input": {...}, "token": ...}
      -> {"content": [MCP content blocks], "is_error": bool}
"""

import json
import queue
import secrets
import socket
import threading


class ToolRequest:
    """A tool call waiting to be executed on the main thread."""

    __slots__ = ("tool", "input", "_event", "_reply")

    def __init__(self, tool, tool_input):
        self.tool = tool
        self.input = tool_input
        self._event = threading.Event()
        self._reply = None

    def reply(self, content, is_error):
        """Called from the main thread with the tool result."""
        self._reply = {"content": content, "is_error": is_error}
        self._event.set()

    def wait(self, timeout=None):
        """Called from the socket thread; blocks until the main thread replies."""
        if not self._event.wait(timeout):
            return {"content": [{"type": "text", "text": "Tool execution timed out"}],
                    "is_error": True}
        return self._reply


class BridgeServer:
    """Accepts shim connections and forwards tool calls to a queue."""

    def __init__(self, list_tools):
        # `list_tools` is safe to call from socket threads (static data only).
        self._list_tools = list_tools
        self.requests = queue.Queue()
        self.token = secrets.token_hex(16)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(8)
        self.port = self._sock.getsockname()[1]
        self._stopped = False
        self._thread = threading.Thread(target=self._accept_loop, daemon=True,
                                        name="mesh-agent-bridge")
        self._thread.start()

    def stop(self):
        self._stopped = True
        try:
            self._sock.close()
        except OSError:
            pass

    def _accept_loop(self):
        while not self._stopped:
            try:
                conn, _addr = self._sock.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn):
        try:
            with conn:
                conn.settimeout(600.0)
                buf = b""
                while not buf.endswith(b"\n"):
                    chunk = conn.recv(65536)
                    if not chunk:
                        return
                    buf += chunk
                try:
                    request = json.loads(buf.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return
                if request.get("token") != self.token:
                    return

                if request.get("op") == "list_tools":
                    reply = {"tools": self._list_tools()}
                elif request.get("op") == "call":
                    tool_request = ToolRequest(request.get("tool", ""),
                                               request.get("input", {}) or {})
                    self.requests.put(tool_request)
                    reply = tool_request.wait(timeout=600.0)
                else:
                    reply = {"content": [{"type": "text", "text": "Unknown bridge op"}],
                             "is_error": True}
                conn.sendall(json.dumps(reply).encode("utf-8") + b"\n")
        except OSError:
            pass
