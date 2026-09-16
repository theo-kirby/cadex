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
from .inventory import read_inventory_summary
from .tools import (
    STANDARD_DISPLAY, VIEW_ARGS, injects_display, injects_revision, tool_definitions,
)

#: Long enough that a slow rebuild is not a broken pipe; the engine's own
#: budget is what actually bounds a run.
SOCKET_TIMEOUT_SECONDS = 3600.0

#: The ops that run the script and publish a revision. Each one's reply is
#: what the model reasons about a build from, so each one carries the
#: measured fit (ADR-346) and the published catalog identity (ADR-362).
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
    #: The inventory block the same reply carried
    #: (:func:`read_inventory_summary`, ADR-362), or None on the same terms.
    inventory: dict[str, Any] | None = None


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
    #: The catalog identity of the most recent successful modelling reply,
    #: as the model saw it -- what the turn report carries as `inventory`.
    last_inventory: dict[str, Any] | None = None
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
        # ...and the view arguments (ADR-360): offered to the model, consumed
        # here, never sent to the engine, whose op does not take them.
        view_args = {
            name: args.pop(name)
            for op, name in VIEW_ARGS
            if op == tool and name in args
        }
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
            section = view_args.get("section")
            if tool == "describe_api" and ok and section is not None:
                if section not in api_sections(reply):
                    reply, ok = no_such_section(reply, section), False
            # A build's reply carries the measured fit (ADR-346): the
            # engine's own pair measurements at the solved pose, read back
            # from the store the accepted revision just published to, with
            # the published joint sweeps beside them in the same value
            # (ADR-366) -- motion fit at no second call. The script's stdout
            # is still in the reply; this is what says whether to believe
            # it. Read under the lock so the revision the measurements
            # describe is the one this reply accepted.
            fit = self._read_fit() if ok and tool in MODELLING_OPS else None
            # ...and the published catalog identity beside it (ADR-362):
            # which placed components are catalog parts and which outputs
            # no lib.* generator built as-is. Advisory -- a printed part is
            # expected there -- but it is the only place the model can
            # learn that a servo it drilled is no longer the catalog servo.
            inventory = (
                self._read_inventory() if ok and tool in MODELLING_OPS else None
            )

        summary = _summarize(tool, reply)
        if fit is not None:
            summary += "  " + _fit_line(fit)
            self.state.last_fit = fit
        if inventory is not None:
            summary += "  " + _inventory_line(inventory)
            self.state.last_inventory = inventory
        call = ToolCall(
            tool, args, ok, summary, str(reply.get("failure_code") or ""), fit,
            inventory,
        )
        self._record(call)
        view = _model_view(tool, reply, args, view_args)
        if fit is not None:
            view["fit"] = fit
        if inventory is not None:
            view["inventory"] = inventory
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

    def _read_inventory(self) -> dict[str, Any]:
        """The inventory block for a build that just succeeded; never raised.

        Same terms as :meth:`_read_fit`: the build was accepted whatever
        happens here, so an inventory the bridge cannot read is reported
        in the block, as `available: false` with the reason, and the block
        is present on every build reply without exception.
        """

        try:
            return read_inventory_summary(self.client)
        except Exception as exc:  # any failure is an identity the model cannot see
            return {
                "available": False,
                "source": "",
                "component_count": 0,
                "catalogued_count": 0,
                "uncatalogued_count": 0,
                "catalog_counts": {},
                "uncatalogued_sources": [],
                "error": f"inventory could not be read: {exc}",
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
#: (ADR-359, ADR-360). The agent harness refuses an MCP tool result over its
#: own token cap and writes it to a file the product agent has no tool to
#: read. The cap is not published in characters, so this budget is the
#: measurement: on ``ot7-heron-c`` (2026-09-15/16) the harness refused
#: 82,523 characters and accepted every result up to 21,742. Every page of
#: the contract — the index and each section — is held under this by a
#: live-engine test, so the contract cannot grow past a size the harness
#: has been seen to accept without a test saying so.
API_VIEW_CHAR_BUDGET = 21_500

#: The name of the one section that is not a domain.
API_LIBRARY_SECTION = "library"

#: The index's line saying where the signatures are.
API_VIEW_SECTIONS_NOTE = (
    "This index carries only names. Every signature is in a section: call "
    "describe_api section=<name> for one of the domains listed under "
    "`domains`, or section=library for the catalog and the lib exports. A "
    "section carries every export's name, full signature and the first "
    "paragraph of its documentation, and fits one tool result."
)


def _descriptions_note(prefix: str) -> str:
    """A section's line saying where the trimmed documentation went."""

    return (
        "Every export's `description` here is the first paragraph of its "
        "documentation, beside its full `signature`. The whole text of "
        "export N (N counting from 0 in this order) is one read away: "
        f"inspect scope=api path={prefix}/exports/N/description."
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


def _export_names(exports: Any) -> Any:
    if not isinstance(exports, list):
        return exports
    return [
        item.get("name") if isinstance(item, dict) else item for item in exports
    ]


def api_sections(reply: dict[str, Any]) -> list[str]:
    """The section names a ``describe_api`` reply can be paged by."""

    domains = reply.get("domains")
    names = list(domains) if isinstance(domains, dict) else []
    if isinstance(reply.get(API_LIBRARY_SECTION), dict):
        names.append(API_LIBRARY_SECTION)
    return names


def api_index(reply: dict[str, Any]) -> dict[str, Any]:
    """A ``describe_api`` reply cut to its index (ADR-360).

    Everything above the domains is kept whole; each domain and the
    library keep their globals and output types and list their exports by
    name only. Notes, signatures, descriptions and the catalog's rows are
    on the sections, which ``sections`` says how to reach.
    """

    view = dict(reply)
    domains = reply.get("domains")
    if isinstance(domains, dict):
        view["domains"] = {
            name: {
                **{key: value for key, value in domain.items() if key != "notes"},
                "exports": _export_names(domain.get("exports")),
            }
            if isinstance(domain, dict)
            else domain
            for name, domain in domains.items()
        }
    library = reply.get(API_LIBRARY_SECTION)
    if isinstance(library, dict):
        catalog = library.get("catalog")
        view[API_LIBRARY_SECTION] = {
            **{key: value for key, value in library.items() if key != "notes"},
            "exports": _export_names(library.get("exports")),
            "catalog": sorted(catalog) if isinstance(catalog, dict) else catalog,
        }
    view["sections"] = API_VIEW_SECTIONS_NOTE
    return view


def api_section(reply: dict[str, Any], section: str) -> dict[str, Any]:
    """One section of a ``describe_api`` reply, whole but for the docstrings.

    A domain section is the domain's own block — notes, globals, output
    types — with every export's name, full signature and first-paragraph
    description; the library section is the same plus the whole catalog.
    ``section`` must be one of :func:`api_sections`.
    """

    if section == API_LIBRARY_SECTION:
        block, prefix = reply.get(API_LIBRARY_SECTION), f"/{API_LIBRARY_SECTION}"
    else:
        domains = reply.get("domains")
        block = domains.get(section) if isinstance(domains, dict) else None
        prefix = f"/domains/{section}"
    if not isinstance(block, dict):
        raise KeyError(section)
    return {
        "ok": True,
        "section": section,
        **block,
        "exports": _summarised_exports(block.get("exports")),
        "descriptions": _descriptions_note(prefix),
    }


def api_view(reply: dict[str, Any], section: str | None = None) -> dict[str, Any]:
    """A ``describe_api`` reply as the model sees it (ADR-359, ADR-360).

    Without ``section`` it is the index; with one it is that section. The
    engine's reply is untouched and its full text stays readable through
    ``inspect scope=api``, which each page says how to reach.
    """

    if section is None:
        return api_index(reply)
    return api_section(reply, section)


def no_such_section(reply: dict[str, Any], section: Any) -> dict[str, Any]:
    """The failure envelope for a section the contract does not have."""

    sections = api_sections(reply)
    return {
        "ok": False,
        "failure_code": "NO_SUCH_SECTION",
        "error": "describe_api has no section {!r}; the sections are {}.".format(
            section, ", ".join(sections)
        ),
        "sections": sections,
    }


def _model_view(
    tool: str,
    reply: dict[str, Any],
    args: dict[str, Any],
    view_args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The reply as the model should see it.

    ``display`` is dropped: it is a page of artifact paths and triangle
    counts for a viewport that does not exist here, and it is the largest
    thing in the frame. Everything the model reasons with — the digest, the
    per-output facts, the script's own stdout, the failure envelope — stays.
    ``expected_revision`` is added back so the guard the bridge supplied is
    visible rather than merely absent. A ``describe_api`` reply is cut to
    the size of one tool result by :func:`api_view` — the index, or the
    one section ``view_args`` asks for.
    """

    view = {key: value for key, value in reply.items() if key not in {"display", "id"}}
    if tool == "describe_api" and reply.get("ok") is True:
        view = api_view(view, (view_args or {}).get("section"))
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
    """The fit block as one progress-log phrase, both halves (ADR-366)."""

    verdict = str(fit.get("verdict") or "")
    if verdict == "unavailable":
        line = "fit unavailable"
    else:
        line = "fit {:s}: {:d} failing of {:d} pair(s)".format(
            verdict, int(fit.get("failing_count") or 0),
            int(fit.get("pairs_checked") or 0),
        )
    sweep = fit.get("sweep")
    return line + ("  " + _sweep_line(sweep) if isinstance(sweep, dict) else "")


def _sweep_line(sweep: dict[str, Any]) -> str:
    """The swept half as one phrase: never a count without its coverage."""

    verdict = str(sweep.get("verdict") or "")
    checked = int(sweep.get("joints_checked") or 0)
    complete = int(sweep.get("joints_complete") or 0)
    if verdict == "unavailable":
        return "sweep unavailable"
    if verdict == "fail":
        return "sweep fail: {:d} overlapping pair(s) over {:d} of {:d} joint(s) swept".format(
            int(sweep.get("failing_count") or 0), complete, checked
        )
    if verdict == "incomplete":
        return "sweep incomplete: {:d} of {:d} joint(s) unswept".format(
            checked - complete, checked
        )
    return "sweep pass: {:d} joint(s) swept".format(complete)


def _inventory_line(inventory: dict[str, Any]) -> str:
    """The inventory block as one progress-log phrase."""

    if not inventory.get("available"):
        return "inventory unavailable"
    return "inventory: {:d} component(s), {:d} catalogued, {:d} uncatalogued".format(
        int(inventory.get("component_count") or 0),
        int(inventory.get("catalogued_count") or 0),
        int(inventory.get("uncatalogued_count") or 0),
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
