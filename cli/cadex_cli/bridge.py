# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The parent's end of the tool path: a socket server in front of cadexd.

``claude`` spawns MCP servers as its own children, so a CLI that wants the
model to reach the engine has some IPC to pay for whatever it does. This is
the cheapest arrangement that keeps the parent in the loop: the parent owns
the single ``cadexd`` child and a unix-domain socket in a private directory;
:mod:`cadex_cli.mcp`, spawned by ``claude``, relays every ``tools/call``
down that socket.

The shape is the Blender shell's, without the reason the shell needed it.
There, the bridge exists because ``bpy`` may only be touched from Blender's
main thread. Here nothing is thread-affine and the bridge earns its keep a
different way: **the parent observes every tool call**, which is what lets
it print progress, know the final revision without asking, and hold the
model's display block for :mod:`cadex_cli.export` — none of which a run
whose engine lived inside the MCP child could do.

A unix socket rather than the shell's localhost TCP: it lives in a
0700 directory, so the filesystem enforces what the token only asserts.
The token is kept anyway — belt and braces cost one comparison.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import json
from pathlib import Path
import secrets
import shutil
import socket
import socketserver
import tempfile
import threading
from typing import Any

from .client import CadexdClient
from .tools import injects_revision, tool_definitions

#: Long enough that a slow rebuild is not a broken pipe; the engine's own
#: budget is what actually bounds a run.
SOCKET_TIMEOUT_SECONDS = 3600.0


@dataclass
class ToolCall:
    """One tool call as the parent saw it."""

    op: str
    args: dict[str, Any]
    ok: bool
    summary: str
    failure_code: str = ""


@dataclass
class BridgeState:
    """What the parent knows after the model has had its turn."""

    #: The revision to guard the next write with, tracked from replies.
    revision: str = ""
    #: The most recent successful modelling reply, display block and all.
    last_accepted: dict[str, Any] | None = None
    calls: list[ToolCall] = field(default_factory=list)


class Bridge:
    """Serve tool calls from the MCP child against one :class:`CadexdClient`."""

    def __init__(
        self,
        client: CadexdClient,
        *,
        on_call: Callable[[ToolCall], None] | None = None,
        initial_revision: str = "",
    ) -> None:
        self.client = client
        self.on_call = on_call
        self.state = BridgeState(revision=str(initial_revision or ""))
        self._lock = threading.Lock()
        self._dir: Path | None = None
        self._server: socketserver.UnixStreamServer | None = None
        self._thread: threading.Thread | None = None
        self.token = secrets.token_urlsafe(24)
        self.socket_path: Path | None = None

    # -- lifecycle -------------------------------------------------------

    def start(self) -> Bridge:
        directory = Path(tempfile.mkdtemp(prefix="cadex-cli-bridge-"))
        directory.chmod(0o700)
        # Unix socket paths are capped near 108 bytes on Linux and 104 on
        # macOS, so the name stays short and the entropy lives in mkdtemp's.
        path = directory / "s"
        bridge = self

        class _Handler(socketserver.StreamRequestHandler):
            timeout = SOCKET_TIMEOUT_SECONDS

            def handle(self) -> None:
                line = self.rfile.readline()
                if not line:
                    return
                try:
                    payload = json.loads(line.decode("utf-8"))
                except (UnicodeDecodeError, ValueError):
                    reply: dict[str, Any] = {"error": "malformed bridge request"}
                else:
                    reply = bridge.handle(payload)
                self.wfile.write(json.dumps(reply).encode("utf-8") + b"\n")
                self.wfile.flush()

        server = socketserver.UnixStreamServer(str(path), _Handler)
        path.chmod(0o600)
        thread = threading.Thread(
            # A short poll interval only shortens teardown: `shutdown()`
            # waits for the accept loop to come round, and the default 0.5 s
            # is half a second on the end of every run.
            target=lambda: server.serve_forever(poll_interval=0.02),
            daemon=True,
            name="cadex-cli-bridge",
        )
        thread.start()

        self._dir = directory
        self._server = server
        self._thread = thread
        self.socket_path = path
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        if self._dir is not None:
            shutil.rmtree(self._dir, ignore_errors=True)
            self._dir = None
        self.socket_path = None

    def __enter__(self) -> Bridge:
        return self.start()

    def __exit__(self, *_exc: object) -> None:
        self.stop()

    # -- the tool path ---------------------------------------------------

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Answer one bridge request. Also the seam the tests drive."""

        if not secrets.compare_digest(
            str(payload.get("token") or ""), self.token
        ):
            return {"error": "bad bridge token"}
        op = str(payload.get("op") or "")
        if op == "list_tools":
            return {"tools": tool_definitions(self.client.engine.protocol)}
        if op == "call":
            return self.call(
                str(payload.get("tool") or ""),
                dict(payload.get("input") or {}),
            )
        return {"error": f"unknown bridge op {op!r}"}

    def call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Run one tool against the engine and answer in MCP content blocks."""

        protocol = self.client.engine.protocol
        if tool not in protocol.OP_ARG_SPECS:
            return _content(f"No such tool: {tool!r}.", is_error=True)

        args = dict(arguments)
        args.pop("expected_revision", None)  # the bridge owns this one
        if injects_revision(protocol, tool):
            args["expected_revision"] = self.state.revision

        with self._lock:
            try:
                reply = self.client.request(tool, args or None)
            except Exception as exc:  # a dead engine must reach the model
                call = ToolCall(tool, args, False, str(exc), "CADEXD_UNREACHABLE")
                self._record(call)
                return _content(
                    json.dumps(
                        {
                            "ok": False,
                            "failure_code": "CADEXD_UNREACHABLE",
                            "error": str(exc),
                        },
                        indent=2,
                    ),
                    is_error=True,
                )
            self._track(tool, reply)

        ok = reply.get("ok") is True
        call = ToolCall(
            tool, args, ok, _summarize(tool, reply), str(reply.get("failure_code") or "")
        )
        self._record(call)
        return _content(
            json.dumps(_model_view(reply, args), indent=2, sort_keys=True, default=str),
            is_error=not ok,
        )

    def _record(self, call: ToolCall) -> None:
        self.state.calls.append(call)
        if self.on_call is not None:
            self.on_call(call)

    def _track(self, tool: str, reply: dict[str, Any]) -> None:
        """Follow the revision through both outcomes, not just the happy one.

        A *refused* candidate still moves the working revision — that is the
        engine's rule, and the reason a failure envelope carries
        ``model_state`` at all. Reading it off both replies is what stops the
        second attempt after a rejection failing for a reason that has
        nothing to do with why the first one did.
        """

        model_state = reply.get("model_state")
        if isinstance(model_state, dict):
            revision = str(model_state.get("next_write_expected_revision") or "")
            if revision:
                self.state.revision = revision
        if reply.get("ok") is True and tool in {
            "write_script",
            "edit_script",
            "set_params",
            "rebuild",
        }:
            self.state.last_accepted = reply


def _content(text: str, *, is_error: bool = False) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "is_error": bool(is_error)}


def _model_view(reply: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    """The reply as the model should see it.

    ``display`` is dropped: it is a page of artifact paths and triangle
    counts for a viewport that does not exist here, and it is the largest
    thing in the frame. Everything the model reasons with — the digest, the
    per-output facts, the script's own stdout, the failure envelope — stays.
    ``expected_revision`` is added back so the guard the bridge supplied is
    visible rather than merely absent.
    """

    view = {key: value for key, value in reply.items() if key not in {"display", "id"}}
    if "expected_revision" in args:
        view["expected_revision_used"] = args["expected_revision"]
    return view


def _summarize(tool: str, reply: dict[str, Any]) -> str:
    """One line for the progress log."""

    if reply.get("ok") is not True:
        return str(reply.get("error") or reply.get("failure_code") or "failed")
    if tool == "describe_api":
        return "authoring contract"
    if tool == "inspect":
        return str(reply.get("scope") or "")
    names = ", ".join(_output_names(reply.get("outputs")))
    digest = str(reply.get("digest") or "")[:12]
    return f"{names} ({digest})" if names else digest


def _output_names(outputs: Any) -> list[str]:
    """The declared output names, however the op chose to shape them.

    A modelling reply's ``outputs`` is a list of records; other shapes turn
    up in failure envelopes and in older replies. Reading the name out of
    whichever it is keeps the progress line readable without pinning a shape
    the protocol does not pin.
    """

    if isinstance(outputs, dict):
        return sorted(str(name) for name in outputs)
    if not isinstance(outputs, list):
        return []
    names: list[str] = []
    for item in outputs:
        if isinstance(item, dict):
            name = str(item.get("name") or "")
            if name:
                names.append(name)
        elif isinstance(item, str):
            names.append(item)
    return names
