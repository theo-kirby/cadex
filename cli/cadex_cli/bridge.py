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

from .clearance import read_fit
from .client import CadexdClient
from .tools import STANDARD_DISPLAY, injects_display, injects_revision, tool_definitions

#: Long enough that a slow rebuild is not a broken pipe; the engine's own
#: budget is what actually bounds a run.
SOCKET_TIMEOUT_SECONDS = 3600.0

#: The ops that run the script and publish a revision. Each one's reply is
#: what the model reasons about a build from, so each one carries the
#: measured fit (ADR-346).
MODELLING_OPS = frozenset({"write_script", "edit_script", "set_params", "rebuild"})


@dataclass
class ToolCall:
    """One tool call as the parent saw it."""

    op: str
    args: dict[str, Any]
    ok: bool
    summary: str
    failure_code: str = ""
    #: The fit block a modelling reply carried (:func:`read_fit`), or None
    #: for a read, a refusal, or a build whose measurements could not be read.
    fit: dict[str, Any] | None = None


@dataclass
class BridgeState:
    """What the parent knows after the model has had its turn."""

    #: The revision to guard the next write with, tracked from replies.
    revision: str = ""
    #: The most recent successful modelling reply, display block and all.
    last_accepted: dict[str, Any] | None = None
    #: The measured fit of the most recent successful modelling reply, as
    #: the model saw it -- what the turn report carries as `fit`.
    last_fit: dict[str, Any] | None = None
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
        # The bridge owns both of these: the guard, and the tessellation the
        # accepted attempt must retain for review (ADR-312).
        args.pop("expected_revision", None)
        args.pop("display", None)
        if injects_revision(protocol, tool):
            args["expected_revision"] = self.state.revision
        if injects_display(protocol, tool):
            args["display"] = dict(STANDARD_DISPLAY)

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
            # A build's reply carries the measured fit (ADR-346): the
            # engine's own pair measurements at the solved pose, read back
            # from the store the accepted revision just published to. The
            # script's stdout is still in the reply; this is what says
            # whether to believe it. Read under the lock so the revision the
            # measurements describe is the one this reply accepted.
            fit = self._read_fit() if ok and tool in MODELLING_OPS else None

        summary = _summarize(tool, reply)
        if fit is not None:
            summary += "  " + _fit_line(fit)
            self.state.last_fit = fit
        call = ToolCall(
            tool, args, ok, summary, str(reply.get("failure_code") or ""), fit
        )
        self._record(call)
        view = _model_view(tool, reply, args)
        if fit is not None:
            view["fit"] = fit
        return _content(
            json.dumps(view, indent=2, sort_keys=True, default=str),
            is_error=not ok,
        )

    def _read_fit(self) -> dict[str, Any]:
        """The fit block for a build that just succeeded; never a raised error.

        The build was accepted whatever happens here, and a reply that fails
        because its *measurement* could not be read would refuse a design
        for a reason the design did not cause. So a read failure is reported
        in the block, as `verdict: unavailable` with the reason, and the
        block is present on every build reply without exception.
        """

        try:
            return read_fit(self.client)
        except Exception as exc:  # any failure is a fit the model cannot see
            return {
                "verdict": "unavailable",
                "source": "",
                "pairs_checked": 0,
                "failing_count": 0,
                "failing": [],
                "error": f"fit measurements could not be read: {exc}",
            }

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
        if reply.get("ok") is True and tool in MODELLING_OPS:
            self.state.last_accepted = reply


def _content(text: str, *, is_error: bool = False) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "is_error": bool(is_error)}


#: The most characters a ``describe_api`` reply may be, as the model sees it
#: (ADR-359). The agent harness refuses an MCP tool result over its own
#: token cap (25,000 tokens by default, which it estimates from the
#: character count) and writes it to a file the product agent has no tool
#: to read; on 2026-09-15 the live contract was 163,200 characters and the
#: agent spent four minutes paging it through ``inspect scope=api`` instead.
#: Held with a margin under that cap by a live-engine test, so the contract
#: can grow without silently crossing it again.
API_VIEW_CHAR_BUDGET = 90_000

#: The one line that says where the trimmed text went.
API_VIEW_DESCRIPTIONS_NOTE = (
    "Every export's `description` here is the first paragraph of its "
    "documentation, beside its full `signature`. The whole text of export N "
    "of domain D (N counting from 0 in this order) is one read away: "
    "inspect scope=api path=/domains/D/exports/N/description, or "
    "/library/exports/N/description for a lib export."
)


def _first_paragraph(text: Any) -> str:
    """The summary paragraph of a docstring, whitespace-normalised."""

    head = str(text or "").strip().split("\n\n", 1)[0]
    return " ".join(head.split())


def _summarised_exports(exports: Any) -> Any:
    if not isinstance(exports, list):
        return exports
    return [
        {**item, "description": _first_paragraph(item.get("description"))}
        if isinstance(item, dict) and "description" in item
        else item
        for item in exports
    ]


def api_view(reply: dict[str, Any]) -> dict[str, Any]:
    """A ``describe_api`` reply cut to fit one tool result (ADR-359).

    Every domain and library export keeps its name and full signature and
    loses all but the first paragraph of its description; nothing else in
    the contract changes. The engine's reply is untouched and its full
    text stays readable through ``inspect scope=api``, which the note in
    ``descriptions`` says how to reach.
    """

    view = dict(reply)
    domains = reply.get("domains")
    if isinstance(domains, dict):
        view["domains"] = {
            name: {**domain, "exports": _summarised_exports(domain.get("exports"))}
            if isinstance(domain, dict)
            else domain
            for name, domain in domains.items()
        }
    library = reply.get("library")
    if isinstance(library, dict):
        view["library"] = {
            **library,
            "exports": _summarised_exports(library.get("exports")),
        }
    view["descriptions"] = API_VIEW_DESCRIPTIONS_NOTE
    return view


def _model_view(
    tool: str, reply: dict[str, Any], args: dict[str, Any]
) -> dict[str, Any]:
    """The reply as the model should see it.

    ``display`` is dropped: it is a page of artifact paths and triangle
    counts for a viewport that does not exist here, and it is the largest
    thing in the frame. Everything the model reasons with — the digest, the
    per-output facts, the script's own stdout, the failure envelope — stays.
    ``expected_revision`` is added back so the guard the bridge supplied is
    visible rather than merely absent. A ``describe_api`` reply is cut to
    the size of one tool result by :func:`api_view`.
    """

    view = {key: value for key, value in reply.items() if key not in {"display", "id"}}
    if tool == "describe_api" and reply.get("ok") is True:
        view = api_view(view)
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
    if tool == "put_asset":
        return (
            f"{reply.get('name')}  {reply.get('bytes')} B  "
            f"sha256 {str(reply.get('sha256') or '')[:12]}"
        )
    names = ", ".join(_output_names(reply.get("outputs")))
    digest = str(reply.get("digest") or "")[:12]
    return f"{names} ({digest})" if names else digest


def _fit_line(fit: dict[str, Any]) -> str:
    """The fit block as one progress-log phrase."""

    verdict = str(fit.get("verdict") or "")
    if verdict == "unavailable":
        return "fit unavailable"
    return "fit {:s}: {:d} failing of {:d} pair(s)".format(
        verdict, int(fit.get("failing_count") or 0), int(fit.get("pairs_checked") or 0)
    )


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
