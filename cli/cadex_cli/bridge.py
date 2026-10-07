# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The tools, run against one engine: what ``cadex mcp`` answers with.

The bridge sits between a tool call and :class:`CadexdClient`. It owns
what the agent is never asked for -- the revision guard and the display
request (:mod:`cadex_cli.tools`) -- runs the tools no engine op backs
(``look``, the training loop, ``draw_blueprint``), and records every call,
which is how ``cadex mcp`` knows what a session accepted when it lands the
session's ``PROGRESS.md`` row (ADR-538). It is a plain object called in
process: the relay socket a CLI-run ``claude`` child once reached it
through went with that child (ADR-538).
"""

from __future__ import annotations

from collections.abc import Callable
import base64
from dataclasses import dataclass, field
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
from typing import Any

from . import evaluate as evaluation
from . import loop
from .clearance import read_fit
from .client import CadexdClient
from .inventory import InventoryError, inventory_summary, read_inventory, read_inventory_summary
from .revision_meshes import retain as retain_revision_meshes
from .studio import FIT_REPORT, STUDIO
from .tools import (
    BRIDGE_TOOLS, STANDARD_DISPLAY, VIEW_ARGS, injects_display, injects_revision,
    tool_definitions,
)

#: The ops that run the script and publish a revision. Each one's reply is
#: what the model reasons about a build from, so each one carries the
#: measured fit (ADR-346) and the published catalog identity (ADR-362).
MODELLING_OPS = frozenset({"write_script", "edit_script", "set_params", "rebuild"})

#: The longest one ``train_status`` call waits for a run to end. An agent
#: that wants longer asks again; a tool call that blocks for an hour cannot
#: be told from a hung one.
TRAIN_WAIT_MAX_S = 900.0
#: How many filmed seeds an ``evaluate`` reply carries as pictures, two
#: sheets each.
EVALUATE_PICTURED_SEEDS = 2
#: How many ledger rows ``train_status`` without a run carries.
LEDGER_VIEW_ROWS = 40


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
    """What the calls so far have left: the revision, the last build and every call."""

    #: The revision to guard the next write with, tracked from replies.
    revision: str = ""
    #: The most recent successful modelling reply, display block and all.
    last_accepted: dict[str, Any] | None = None
    #: The measured fit of the most recent successful modelling reply, as
    #: the model saw it.
    last_fit: dict[str, Any] | None = None
    #: The catalog identity of the most recent successful modelling reply,
    #: as the model saw it.
    last_inventory: dict[str, Any] | None = None
    calls: list[ToolCall] = field(default_factory=list)


class Bridge:
    """Run tool calls against one :class:`CadexdClient`."""

    def __init__(
        self,
        client: CadexdClient,
        *,
        on_call: Callable[[ToolCall], None] | None = None,
        initial_revision: str = "",
        project_root: Path | str | None = None,
    ) -> None:
        self.client = client
        #: The project directory, which the loop tools (ADR-464) read the
        #: accepted attempt from and write runs and evaluations into. Without
        #: one those tools refuse; every other tool is unaffected.
        self.project_root = Path(project_root).resolve() if project_root else None
        self.on_call = on_call
        self.state = BridgeState(revision=str(initial_revision or ""))
        self._lock = threading.Lock()

    # A scope for the calls, so a caller can say where they end; the bridge
    # holds nothing that needs releasing.
    def __enter__(self) -> Bridge:
        return self

    def __exit__(self, *_exc: object) -> None:
        pass

    # -- the tool path ---------------------------------------------------

    def tools(self) -> list[dict[str, Any]]:
        """Every tool, as ``{"name", "description", "input_schema"}``."""

        return tool_definitions(self.client.engine.protocol)

    def call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Run one tool against the engine and answer in MCP content blocks."""

        protocol = self.client.engine.protocol
        if tool in BRIDGE_TOOLS:
            if tool == "look":
                return self._look(arguments)
            if tool == "draw_blueprint":
                return self._draw_blueprint(arguments)
            return self._loop_tool(tool, arguments)
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
            # ...and the accepted model is kept under its revision's
            # ordinal, for the timeline (ADR-546). Never fails the call.
            if ok and tool in MODELLING_OPS and self.project_root is not None:
                retain_revision_meshes(self.project_root)

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
        # The model sees both blocks bounded (ADR-435); the session's row and
        # `state` keep them whole.
        if fit is not None:
            view["fit"] = fit_view(fit)
        if inventory is not None:
            view["inventory"] = inventory_view(inventory)
        return _content(
            json.dumps(view, indent=2, sort_keys=True, default=str),
            is_error=not ok,
        )

    def _look(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Render the accepted design and hand the model the pictures (ADR-406).

        Drawn from the last accepted modelling reply's display block when the
        bridge holds one -- the tessellation the build already published, so
        looking costs no rebuild -- and from a ``rebuild`` only when a session
        opens on a revision this bridge has not built yet. World geometry the
        fit block names is left out. Each part is drawn in the appearance
        role the script declared, in the assembly's palette (ADR-413); an
        undeclared part is drawn by supplier, from the inventory block.
        """

        views = [str(v) for v in (arguments.get("views") or ["iso", "iso_back"])]
        focus = [str(v) for v in (arguments.get("focus") or [])]
        unknown = set(arguments) - {"views", "focus"}
        if unknown or not views or len(views) > 5:
            return _content(
                "look takes `views` (1 to 5 of hero, iso, iso_back, front, right, top) and "
                "`focus` (names), nothing else.", is_error=True,
            )
        with self._lock:
            try:
                reply = self._accepted_reply()
            except Exception as exc:
                return _content(f"look could not rebuild to get geometry: {exc}", is_error=True)
            fit, inventory = self.state.last_fit, self.state.last_inventory
            try:
                facts, shots = STUDIO.look_report(reply, fit, inventory, views, focus)
            except STUDIO.StudioError as exc:
                call = ToolCall("look", dict(arguments), False, str(exc))
                self._record(call)
                return _content(str(exc), is_error=True)
        text = json.dumps(facts, indent=2)
        content = [{"type": "text", "text": text}]
        for view, data, _details in shots:
            content.append({
                "type": "image",
                "data": base64.b64encode(data).decode("ascii"),
                "mimeType": "image/png",
            })
        self._record(ToolCall(
            "look", dict(arguments), True,
            f"{', '.join(views)}{' focus ' + ', '.join(focus) if focus else ''} "
            f"({facts['revision'][:12]})",
        ))
        return {"content": content, "is_error": False}

    def _accepted_reply(self) -> dict[str, Any]:
        """The last accepted modelling reply, rebuilding once when this
        bridge holds none; called under the lock. Raises when the engine
        cannot be reached."""

        reply = self.state.last_accepted
        if reply is None:
            args: dict[str, Any] = {"display": dict(STANDARD_DISPLAY)}
            if injects_revision(self.client.engine.protocol, "rebuild"):
                args["expected_revision"] = self.state.revision
            reply = self.client.request("rebuild", args)
            self._track("rebuild", reply)
            if reply.get("ok") is True:
                # What a modelling reply would have carried: without them
                # the floor frames the view and every part is one palette.
                self.state.last_fit = self._read_fit()
                self.state.last_inventory = self._read_inventory()
        return reply

    # -- drawing sheets (ADR-516) -----------------------------------------

    def _draw_blueprint(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Compose a dimensioned drawing sheet of the accepted design, store
        it with the project through ``put_blueprint`` and hand the model the
        picture (ADR-516).

        Drawn by the engine's own ``CadexStudio.blueprint_report`` from the
        same accepted reply ``look`` draws. A sheet's ``name`` is its
        identity: drawing again under a stored name stores the next version,
        and any key left out is taken from that sheet's stored recipe, so
        "add a note to the gearbox sheet" is one key, not the whole recipe.
        """

        allowed = set(BRIDGE_TOOLS["draw_blueprint"]["input_schema"]["properties"])
        unknown = sorted(set(arguments) - allowed)

        def refuse(message: str) -> dict[str, Any]:
            self._record(ToolCall("draw_blueprint", dict(arguments), False, message))
            return _content(json.dumps({"ok": False, "error": message}, indent=2), is_error=True)

        if unknown:
            return refuse(f"draw_blueprint takes {', '.join(sorted(allowed))}; not {', '.join(unknown)}.")
        name = " ".join(str(arguments.get("name") or "").split())
        with self._lock:
            stored = self._stored_blueprint(name) if name else None
            recipe = dict(arguments)
            meta = (stored or {}).get("meta") or {}
            if meta.get("schema") == STUDIO.BLUEPRINT_RECIPE_SCHEMA:
                recipe = {**{k: meta[k] for k in STUDIO.BLUEPRINT_RECIPE_KEYS if k in meta}, **recipe}
            try:
                recipe = STUDIO.blueprint_recipe(recipe)
                reply = self._accepted_reply()
                version = int((stored or {}).get("version") or 0) + 1
                data, facts = STUDIO.blueprint_report(
                    reply, self.state.last_fit, self.state.last_inventory, recipe,
                    project=self.project_root.name if self.project_root else "",
                    version=version, date=time.strftime("%Y-%m-%d"))
            except STUDIO.StudioError as exc:
                return refuse(str(exc))
            except Exception as exc:  # a dead engine must reach the model
                return refuse(f"draw_blueprint could not rebuild to get geometry: {exc}")
            with tempfile.TemporaryDirectory(prefix="cadex-blueprint-") as scratch:
                sheet = Path(scratch) / "sheet.png"
                sheet.write_bytes(data)
                try:
                    put = self.client.request("put_blueprint", {
                        "source_path": str(sheet), "name": recipe["name"],
                        "label": recipe["name"], "meta": recipe})
                except Exception as exc:
                    return refuse(f"the sheet could not be stored: {exc}")
        if put.get("ok") is not True:
            return refuse(f"the sheet was refused by the store: {put.get('error') or put.get('failure_code')}")
        entry = next((item for item in put.get("blueprints") or []
                      if item.get("file") == put.get("name")), {})
        facts.update({"stored": f"blueprints/{put.get('name')}", "version": int(entry.get("version") or version),
                      "sha256": put.get("sha256"),
                      "recipe": {k: recipe[k] for k in STUDIO.BLUEPRINT_RECIPE_KEYS}})
        self._record(ToolCall(
            "draw_blueprint", dict(arguments), True,
            f"{recipe['name']} v{facts['version']} ({facts['revision'][:12]})"))
        return {"content": [
            {"type": "text", "text": json.dumps(facts, indent=2)},
            {"type": "image", "data": base64.b64encode(data).decode("ascii"), "mimeType": "image/png"},
        ], "is_error": False}

    def _stored_blueprint(self, name: str) -> dict[str, Any] | None:
        """The newest stored sheet under ``name``, or ``None``; called under the lock."""

        try:
            reply = self.client.request("inspect", {"scope": "blueprint", "target": name, "path": "/blueprint"})
        except Exception:
            return None
        value = reply.get("value") if reply.get("ok") is True else None
        if not isinstance(value, dict) or " ".join(str(value.get("name") or "").split()).casefold() != name.casefold():
            return None
        return value

    # -- the training loop (ADR-464) ------------------------------------

    def _loop_tool(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Answer one of the loop's four tools; a refusal is a tool error
        whose text says what to do, never a raised exception."""

        allowed = set(BRIDGE_TOOLS[tool]["input_schema"]["properties"])
        unknown = sorted(set(arguments) - allowed)
        try:
            if unknown:
                raise loop.LoopError(
                    f"{tool} takes {', '.join(sorted(allowed))}; not {', '.join(unknown)}.")
            if self.project_root is None:
                raise loop.LoopError(f"{tool} needs a project directory; this session has none.")
            reply = getattr(self, "_" + tool)(arguments)
        except (loop.LoopError, evaluation.EvaluateError) as exc:
            self._record(ToolCall(tool, dict(arguments), False, str(exc)))
            return _content(json.dumps({"ok": False, "error": str(exc)}, indent=2), is_error=True)
        return reply

    def _run_dir(self, arguments: dict[str, Any]) -> Path:
        name = str(arguments.get("run") or "")
        run_dir = self.project_root / loop.RUNS_DIRNAME / name
        if not name or Path(name).name != name or not (run_dir / loop.REGISTRATION_NAME).is_file():
            known = ", ".join(run["run"] for run in loop.list_runs(self.project_root))
            raise loop.LoopError(
                f"no training run {name!r} in this project" + (f"; it has: {known}." if known else "."))
        return run_dir

    def _run_reply(self, tool: str, arguments: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
        view = {"ok": True, **loop.run_view(run)}
        progress = view.get("progress") or {}
        self._record(ToolCall(
            tool, dict(arguments), True,
            "{:s}  {:s}{:s}".format(
                str(view["run"]), str(view["state"]),
                "" if progress.get("iteration") is None else
                "  iteration {:d} of {}".format(int(progress["iteration"]) + 1, progress.get("total")))))
        return _content(json.dumps(view, indent=2, sort_keys=True, default=str))

    def _train_start(self, arguments: dict[str, Any]) -> dict[str, Any]:
        settings = arguments.get("settings") or {}
        if not isinstance(settings, dict):
            raise loop.LoopError("settings must be an object of trainer settings.")
        run_dir = loop.register(
            self.project_root, run=str(arguments.get("run") or ""),
            budget_s=arguments.get("budget_s"), reason=str(arguments.get("reason") or ""),
            settings=settings, task_name=str(arguments.get("task") or ""))
        # Freeze the model the run trains, as `cadex walk` does, so the
        # dashboard can pose its checkpoint rollouts on it. A view that
        # cannot be kept never stops the run; the page says why.
        from .review_server import retain_training_view
        try:
            retain_training_view(self.project_root, run_dir)
        except (OSError, ValueError, KeyError) as exc:
            print(f"train_start: training view not retained: {exc}", file=sys.stderr)
        return self._run_reply("train_start", arguments, loop.launch(run_dir))

    def _train_status(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not arguments.get("run"):
            runs = loop.list_runs(self.project_root)
            view = {
                "ok": True,
                "runs": [{"run": run["run"], "state": run["state"],
                          "reason": run["registration"].get("reason"),
                          "accepted_revision": run["registration"].get("accepted_revision"),
                          "elapsed_s": run["elapsed_s"],
                          "task_bundle": loop.task_bundle(run)["path"],
                          "policy_sha256": (run["status"].get("policy") or {}).get("sha256")}
                         for run in runs],
                "ledger": loop.read_ledger(self.project_root)[-LEDGER_VIEW_ROWS:],
            }
            self._record(ToolCall("train_status", dict(arguments), True, f"{len(runs)} run(s)"))
            return _content(json.dumps(view, indent=2, sort_keys=True, default=str))
        run_dir = self._run_dir(arguments)
        try:
            wait = float(arguments.get("wait_s") or 0.0)
        except (TypeError, ValueError) as exc:
            raise loop.LoopError("wait_s must be a number of seconds.") from exc
        if not 0.0 <= wait <= TRAIN_WAIT_MAX_S:
            raise loop.LoopError(f"wait_s must be within [0, {TRAIN_WAIT_MAX_S:g}] seconds.")
        deadline = time.monotonic() + wait
        run = loop.read_run(run_dir)
        while run["state"] in loop.LIVE_STATES and time.monotonic() < deadline:
            time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
            run = loop.read_run(run_dir)
        return self._run_reply("train_status", arguments, run)

    def _train_stop(self, arguments: dict[str, Any]) -> dict[str, Any]:
        reason = " ".join(str(arguments.get("reason") or "").split())
        if not reason:
            raise loop.LoopError("train_stop needs the reason the run is being stopped.")
        run = loop.request_stop(self._run_dir(arguments), reason)
        return self._run_reply("train_stop", arguments, run)

    def _evaluate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Measure the accepted policy on its task's frozen seeds, film it,
        and hand the agent the numbers and the filmstrips (ADR-457, ADR-459)."""

        root = self.project_root
        inputs = evaluation.retained_inputs(
            root, task_name=str(arguments.get("task") or ""),
            policy_name=str(arguments.get("policy") or ""))
        out = evaluation.check_out(root, evaluation.default_out(root, inputs))
        measured = evaluation.run_evaluation(self.client.engine, inputs, out)
        with self._lock:
            try:
                inventory = read_inventory(self.client)
            except (InventoryError, RuntimeError, ValueError, OSError):
                inventory = None
            try:
                fit = read_fit(self.client)
            except Exception:  # noqa: BLE001 - as cadex evaluate: an unreadable fit leaves every part drawn
                fit = None
        measured = evaluation.add_film(
            root, out, measured, choice=str(arguments.get("film") or "auto"),
            inventory=inventory)
        # A pass presents itself as `cadex evaluate`'s does, unasked: the two
        # heroes (ADR-570) and the shove video (ADR-571).
        measured = evaluation.add_heroes(
            root, out, measured, fit=fit,
            inventory=inventory_summary(inventory) if inventory else None)
        measured = evaluation.add_shove(self.client.engine, root, out, measured, inputs,
                                        inventory=inventory)
        trained_by = loop.runs_that_trained(root, inputs["policy_sha256"])
        view = {"ok": True, **evaluation.agent_view(measured, out), "trained_by_run": trained_by}
        failing = evaluation.failing_predicates(measured)
        loop.append_ledger(
            root, "evaluated", verdict=measured["verdict"], failing=failing,
            accepted_revision=inputs["accepted_revision"], policy_sha256=inputs["policy_sha256"],
            task=inputs["task_output"], passed=len(measured["summary"]["passed"]),
            seeds=measured["summary"]["seeds"], trained_by_run=trained_by,
            report=str((out / evaluation.REPORT_NAME).relative_to(root)))
        content: list[dict[str, Any]] = [
            {"type": "text", "text": json.dumps(view, indent=2, sort_keys=True, default=str)}]
        film = measured.get("film") or {}
        for row in (film.get("seeds") or [])[:EVALUATE_PICTURED_SEEDS]:
            for sheet in ("overview", "detail"):
                path = out / str((row.get(sheet) or {}).get("file") or "")
                if path.is_file():
                    content.append({
                        "type": "image", "mimeType": "image/png",
                        "data": base64.b64encode(path.read_bytes()).decode("ascii")})
        self._record(ToolCall(
            "evaluate", dict(arguments), True,
            "{:s}  {:d} of {:d} seeds pass{:s}".format(
                str(measured["verdict"]), len(measured["summary"]["passed"]),
                int(measured["summary"]["seeds"]),
                ("; failing " + ", ".join(failing[:4])) if failing else "")))
        return {"content": content, "is_error": False}

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
                "derived_catalog_sources": [],
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
    one section ``view_args`` asks for. A successful build's ``outputs``
    and ``live_outputs`` become one :func:`outputs_view` (ADR-435): two
    echoes of every declared name were most of a 200-output reply.
    """

    view = {key: value for key, value in reply.items() if key not in {"display", "id"}}
    if tool == "describe_api" and reply.get("ok") is True:
        view = api_view(view, (view_args or {}).get("section"))
    if tool in MODELLING_OPS and reply.get("ok") is True:
        view.pop("live_outputs", None)
        view["outputs"] = outputs_view(reply)
    if "expected_revision" in args:
        view["expected_revision_used"] = args["expected_revision"]
    return view


# The bounded model view of the fit and inventory blocks is engine code
# shared with the shell (ADR-447).
BUILD_VIEW_LIST_LIMIT = FIT_REPORT.BUILD_VIEW_LIST_LIMIT
_cut = FIT_REPORT._cut
_worst_first = FIT_REPORT._worst_first
fit_view = FIT_REPORT.fit_view
inventory_view = FIT_REPORT.inventory_view

#: Output names are listed while there are at most this many; past it the
#: view counts them by kind (ADR-435). The model wrote every one of them.
BUILD_VIEW_NAME_LIMIT = 40

#: The row keys an output carries that are about the output rather than
#: about FreeCAD's object for it. Only a row with one of these is detailed.
_OUTPUT_DETAIL_KEYS = (
    "facts", "diagnostics", "sketch_validation", "mesh_data",
    "operation_diagnostics", "assembly_data", "stale_reason",
)


def outputs_view(reply: dict[str, Any]) -> dict[str, Any]:
    """A build's declared outputs as the model needs them (ADR-435).

    The engine reply lists every output twice -- ``outputs`` and
    ``live_outputs`` -- and on ``ot10-biped-3`` (215 outputs) the two were
    60,669 of the reply's 85,954 characters. What the model reasons with is
    the count, the kinds, any output that has no live object, and any
    output that carries facts or diagnostics; each output's full row is one
    ``inspect scope=output target=<name>`` away.
    """

    rows = [row for row in (reply.get("outputs") or []) if isinstance(row, dict)]
    live = reply.get("live_outputs") if isinstance(reply.get("live_outputs"), dict) else {}
    kinds: dict[str, int] = {}
    detailed: list[dict[str, Any]] = []
    for row in rows:
        name = str(row.get("name") or "")
        live_row = live.get(name) if isinstance(live.get(name), dict) else {}
        merged = {**live_row, **row}
        kind = " ".join(str(part) for part in (
            merged.get("domain"), merged.get("type") or merged.get("output_type"),
        ) if part)
        kinds[kind or "unknown"] = kinds.get(kind or "unknown", 0) + 1
        detail = {key: merged[key] for key in _OUTPUT_DETAIL_KEYS if merged.get(key)}
        if detail:
            detailed.append({"name": name, **detail})
    names = _output_names(rows)
    view: dict[str, Any] = {"count": len(rows), "by_kind": dict(sorted(kinds.items()))}
    if len(names) <= BUILD_VIEW_NAME_LIMIT:
        view["names"] = names
    view["not_live"] = [name for name in names if name not in live]
    _cut(view, "detail", detailed, "inspect scope=output target=<name>")
    view["note"] = (
        "Summarised: one output's full row is inspect scope=output target=<name>."
    )
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
        # Never in the count (ADR-427), but a pass that hid them would read
        # as a robot that never touches its floor.
        resting = int(fit.get("world_geometry_contact_count") or 0)
        if resting:
            line += "; {:d} resting on world geometry (advisory)".format(resting)
    sweep = fit.get("sweep")
    line += ("  " + _sweep_line(sweep)) if isinstance(sweep, dict) else ""
    attachments = fit.get("attachments")
    # Silent when the design welds nothing and when the revision published no
    # report; a count of zero out of zero is noise, and a gap under a weld is
    # the one thing here worth a phrase of its own (ADR-370).
    if isinstance(attachments, dict) and int(attachments.get("pairs_checked") or 0):
        line += "  welded: {:d} of {:d} pair(s) not touching".format(
            int(attachments.get("reported_count") or 0),
            int(attachments["pairs_checked"]),
        )
    return line


def _sweep_line(sweep: dict[str, Any]) -> str:
    """The swept half as one phrase: never a count without its coverage."""

    verdict = str(sweep.get("verdict") or "")
    checked = int(sweep.get("joints_checked") or 0)
    complete = int(sweep.get("joints_complete") or 0)
    # Suppressed joints are rows this block does not judge (ADR-371), so they
    # are never counted as unswept coverage and never inflate a pass.
    skipped = int(sweep.get("joints_skipped") or 0)
    suffix = "; {:d} suppressed".format(skipped) if skipped else ""
    # Findings against world geometry never move the verdict (ADR-420), but
    # a pass that hides them would read as a leg that never meets the floor.
    world = int(sweep.get("world_geometry_count") or 0)
    if world:
        suffix += "; {:d} against world geometry (advisory)".format(world)
    if verdict == "unavailable":
        # Two different facts wear this verdict (ADR-368), and a bare
        # "unavailable" hides which: a revision accepted before ADR-367
        # published no sweep, while a current one with complete coverage of
        # no joints has nothing that moves within a range. `coverage` is
        # what tells them apart in the block, so say it here too.
        if str(sweep.get("coverage") or "") == "unavailable":
            return "sweep unavailable: no published sweep"
        # A third fact wears this verdict since ADR-371: the assembly declares
        # limited joints and suppresses every one of them, which is not the
        # same statement as declaring none.
        if skipped and skipped == checked:
            return "sweep unavailable: every limited joint suppressed ({:d})".format(skipped)
        return "sweep unavailable: no limited joint"
    if verdict == "fail":
        # "failing", not "overlapping": since ADR-378 a pair can fail this
        # block by closing below its minimum without ever interpenetrating.
        return "sweep fail: {:d} failing pair(s) over {:d} of {:d} joint(s) swept{:s}".format(
            int(sweep.get("failing_count") or 0), complete, checked - skipped, suffix
        )
    if verdict == "incomplete":
        return "sweep incomplete: {:d} of {:d} joint(s) unswept{:s}".format(
            checked - complete - skipped, checked - skipped, suffix
        )
    return "sweep pass: {:d} joint(s) swept{:s}".format(complete, suffix)


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
