# SPDX-License-Identifier: LGPL-2.1-or-later

"""cadexd — the headless xscript engine service (Phase 5.3, ADR-017).

One cadexd child per open project, spawned and owned by the shell:

    FreeCADCmd -c "import sys; sys.path.insert(0, '<cadex>'); \\
        import cadexd; raise SystemExit(cadexd.main())"

or ``pixi run cadexd``. Speaks ``cadex-cadexd-v1`` NDJSON over stdio
(:mod:`CadexdProtocol`). cadexd runs *without* ``--safe-mode`` — it is
trusted engine code; only user scripts stay sandboxed in the per-run
``--safe-mode`` worker beneath it.

Process discipline:

- **stdout hijack** — fd 1 is dup()ed to a private protocol fd before any
  FreeCAD chatter can pollute it, then fd 1 is redirected to stderr. Only
  protocol frames ever reach the parent's pipe.
- **stdin EOF is the lifetime signal** — shell death ⇒ self-exit.
- **serial dispatch** — one modeling request in flight; a second modeling
  request is refused with ``CADEXD_BUSY`` by the reader thread while
  read-only requests queue behind the running one. ``cancel`` is honored
  mid-run through the pipeline's existing cancellation path.
- **ephemeral document** — cadexd hosts one persistent headless
  ``App::Document`` per open project for publication semantics (lint, GC,
  output identity, inspect). The document of record (.FCStd) stays in the
  shell; both are rebuildable and digest-verified. Every ``open_project``
  with an accepted digest runs a restore pass that re-proves restart
  determinism.

The module scope stays FreeCAD-free so the dispatch/cancel machinery is
testable under the stubbed pytest suite.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import sys
import threading
from typing import Any, Callable, Mapping

from CadexdProtocol import (
    CADEXD_BUSY,
    CADEXD_NOT_OPEN,
    CADEXD_PROTOCOL_ERROR,
    CADEXD_RESTORE_FAILED,
    MODELING_OPS,
    OP_ARG_SPECS,
    PROTOCOL_SCHEMA,
    ProtocolError,
    decode_frame,
    encode_frame,
    failure,
    validate_request,
)


class _EmptyRegistry:
    """core.inspect scope='api' resolves through describe_project_api on the
    xscript engine; cadexd serves no per-tool schema registry."""

    @staticmethod
    def names() -> frozenset[str]:
        return frozenset()

    @staticmethod
    def get(name: str) -> Any:
        raise KeyError(name)


class _CadexdService:
    """Document-affine service shim: the 7-member surface the pipeline uses,
    plus resolved worker budgets and a monotonic document revision."""

    def __init__(
        self, project_root: Path, document: Any, budgets: Mapping[str, Any]
    ) -> None:
        self._root = Path(project_root)
        self._document = document
        self._budgets = dict(budgets)
        self._revision = 0
        self.registry = _EmptyRegistry()

    def _active_document(self):
        return self._document

    def project_scope_snapshot(self) -> dict[str, Any]:
        return {"root": str(self._root), "project_id": "cadexd"}

    def provider_document_revision(self) -> str:
        # Stable within one lifecycle (capture and publication must agree);
        # bumped by note_document_changed() after each accepted publication.
        return f"cadexd-{self._revision}"

    def note_document_changed(self) -> None:
        self._revision += 1

    def scripted_budgets(self) -> dict[str, Any]:
        return dict(self._budgets)

    @staticmethod
    def active_workbench_name() -> str:
        return "CadexProject"

    @staticmethod
    def modeling_engine() -> str:
        return "xscript"

    @staticmethod
    def _partdesign_body_for_feature(_obj):
        return None


def _resolve_budgets(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    from CadexEngineSettings import resolve_budgets

    return resolve_budgets(raw)


def _display_block(
    staging: Path, validated: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    """Per-output display record with absolute artifact paths (ADR-017)."""

    result: dict[str, dict[str, Any]] = {}
    for item in list(validated.get("outputs") or []):
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or "")
        artifact = str(item.get("artifact_path") or "")
        entry: dict[str, Any] = {
            "artifact_kind": str(item.get("artifact_kind") or "") or None,
            "artifact_path": str(staging / artifact) if artifact else None,
            "placement": item.get("solved_placement_matrix"),
            "tessellation": None,
        }
        # Only components have one, and only then (ADR-049): the key is a
        # positive signal that this entry places another output's geometry,
        # so every other entry keeps the shape it has always had.
        source_output = str(item.get("source_output") or "")
        if source_output:
            entry["source_output"] = source_output
        # And only measurements have one (ADR-139), for the same reason and on
        # the same terms: a positive signal that this entry is two points and
        # a number rather than a thing with a shape. Every other entry keeps
        # exactly the four keys it has always had.
        measurement = item.get("measurement")
        if isinstance(measurement, Mapping):
            entry["measurement"] = dict(measurement)
        # ...and only mesh checks have one (ADR-144), on the same terms
        # again: a positive signal that this entry is four integers about
        # another output rather than a thing with a shape.
        mesh_check = item.get("mesh_check")
        if isinstance(mesh_check, Mapping):
            entry["mesh_check"] = dict(mesh_check)
        # ...and only stress checks have one (ADR-145). Three optional keys
        # now, all on the same terms: a positive signal that this entry
        # states a fact about geometry rather than being geometry.
        stress = item.get("stress")
        if isinstance(stress, Mapping):
            entry["stress"] = dict(stress)
        # ...and only exploded views have one (ADR-149), on the same terms
        # once more: a positive signal that this entry is staged poses and
        # leader lines for the shell to interpolate, not geometry of its own.
        exploded_view = item.get("exploded_view")
        if isinstance(exploded_view, Mapping):
            entry["exploded_view"] = dict(exploded_view)
        tessellation = item.get("display")
        if isinstance(tessellation, Mapping):
            entry["tessellation"] = {
                **dict(tessellation),
                "artifact_path": str(
                    staging / str(tessellation.get("artifact_path") or "")
                ),
                "sidecar_path": str(
                    staging / str(tessellation.get("sidecar_path") or "")
                ),
            }
        result[name] = entry
    return result


def _declined_preview(revision: str, reason: str) -> dict[str, Any]:
    """A successful ``preview_params`` that declines to answer with poses."""

    return {
        "ok": True,
        "previewable": False,
        "revision": revision,
        "placements": {},
        "reason": reason,
    }


def _declined_live_open(reason: str) -> dict[str, Any]:
    """A successful ``live_open`` that declines to start a session.

    Every required key is present and empty, exactly as
    :func:`_declined_preview` fills ``placements``: the response contract is
    pinned by op and not by outcome, so a refusal the shell can read is a
    refusal that carries the whole shape.
    """

    return {
        "ok": True,
        "live": False,
        "components": [],
        "control_hz": 0,
        "frames_per_second": 0,
        "actuator_channels": [],
        "episode_seconds": 0.0,
        "policy": {"label": "", "weights": "", "sha256": "",
                   "trained_label": ""},
        "reason": reason,
    }


def _declined_live_step(reason: str) -> dict[str, Any]:
    """A successful ``live_step`` with no session behind it."""

    return {
        "ok": True,
        "live": False,
        "frames": [],
        "step": 0,
        "time_s": 0.0,
        "terminated": False,
        "termination": "",
        "reset_count": 0,
        "reason": reason,
    }


class CadexdServer:
    """Serial dispatcher over one project's engine state.

    ``send`` writes one frame (thread-safe); the pipeline entry points are
    injectable so the dispatch/cancel/busy machinery is unit-testable
    without FreeCAD.
    """

    def __init__(
        self,
        send: Callable[[dict[str, Any]], None],
        *,
        run_lifecycle: Callable[..., dict[str, Any]] | None = None,
        resolve_pin: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        self._send = send
        self._injected_run_lifecycle = run_lifecycle
        self._injected_resolve_pin = resolve_pin
        self._state_lock = threading.Lock()
        self._modeling_in_flight = 0
        self._busy_request_id: str | None = None
        self._cancel_requested = False
        self._service: _CadexdService | None = None
        self._project_root: Path | None = None
        self._document: Any = None
        # Spawned lazily on the first preview, so a session that never drags
        # a slider never pays for it (ADR-055).
        self._preview_worker: Any = None
        # ...and the same for live mode (ADR-109), which is the more
        # expensive of the two to hold: it is a *running* episode, not an
        # idle oracle.
        self._live_session: Any = None
        self.shutdown_requested = False

    # -- reader-thread side ---------------------------------------------

    def admit(self, line: bytes) -> tuple[str, str, dict[str, Any]] | None:
        """Validate one incoming frame on the reader thread.

        Control frames (``cancel``) and refusals (``CADEXD_BUSY``,
        protocol errors) are answered here so they work while a modeling
        request is executing; everything else is returned for the serial
        dispatch queue.
        """

        try:
            request_id, op, args = validate_request(decode_frame(line))
        except ProtocolError as exc:
            self._send(
                {
                    "id": getattr(exc, "request_id", None),
                    **failure(CADEXD_PROTOCOL_ERROR, str(exc)),
                }
            )
            return None
        if op == "cancel":
            self._handle_cancel(request_id, args)
            return None
        if op in MODELING_OPS:
            with self._state_lock:
                if self._modeling_in_flight >= 1:
                    self._send(
                        {
                            "id": request_id,
                            **failure(
                                CADEXD_BUSY,
                                "A modeling request is already in flight; "
                                "cancel it or wait for its response.",
                                busy_with=self._busy_request_id,
                            ),
                        }
                    )
                    return None
                self._modeling_in_flight += 1
        return request_id, op, args

    def _handle_cancel(self, request_id: str, args: Mapping[str, Any]) -> None:
        target = str(args.get("request_id") or "")
        with self._state_lock:
            busy = self._busy_request_id
            if busy is not None and (not target or target == busy):
                self._cancel_requested = True
                cancelled = busy
            else:
                cancelled = None
        self._send({"id": request_id, "ok": True, "cancelled": cancelled})

    def _cancellation_check(self, request_id: str) -> Callable[[], bool]:
        def check() -> bool:
            with self._state_lock:
                return (
                    self._cancel_requested
                    and self._busy_request_id == request_id
                )

        return check

    # -- dispatch-thread side -------------------------------------------

    def dispatch(self, request_id: str, op: str, args: dict[str, Any]) -> None:
        """Handle one admitted request serially; always answers exactly once."""

        is_modeling = op in MODELING_OPS
        if is_modeling:
            with self._state_lock:
                self._busy_request_id = request_id
                self._cancel_requested = False
        try:
            handler = getattr(self, f"_op_{op}")
            response = handler(request_id, args)
        except Exception as exc:  # a handler bug must not kill the server
            response = failure(
                CADEXD_PROTOCOL_ERROR,
                f"cadexd handler for {op} failed: {exc}",
                exception_type=exc.__class__.__name__,
            )
        finally:
            if is_modeling:
                with self._state_lock:
                    self._busy_request_id = None
                    self._cancel_requested = False
                    self._modeling_in_flight -= 1
        self._send({"id": request_id, **response})

    # -- handlers --------------------------------------------------------

    def _run_lifecycle(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        if self._injected_run_lifecycle is not None:
            return self._injected_run_lifecycle(*args, **kwargs)
        from CadexScriptedRuntime import run_project_lifecycle

        return run_project_lifecycle(*args, **kwargs)

    def _require_open(self) -> dict[str, Any] | None:
        if self._service is None:
            return failure(
                CADEXD_NOT_OPEN, "No project is open; call open_project first."
            )
        return None

    def _script_state(self) -> dict[str, Any]:
        from CadexInspection import _complete_script

        return _complete_script({"project_root": str(self._project_root)})

    def _op_open_project(
        self, request_id: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        import FreeCAD as App

        from CadexScriptStore import CadexProjectScriptStore

        root = Path(str(args["project_root"])).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        root = root.resolve()
        budgets = _resolve_budgets(args.get("budgets"))
        # A different project is a different everything.
        self._invalidate_resident_workers()
        if self._document is not None:
            try:
                App.closeDocument(self._document.Name)
            except Exception:
                pass
            self._document = None
            self._service = None
        document = App.newDocument("CadexdEphemeral")
        service = _CadexdService(root, document, budgets)
        self._document = document
        self._service = service
        self._project_root = root

        store = CadexProjectScriptStore(root)
        state = store.read_state()
        source = store.read_source()
        manifest = None
        manifest_path = root / "project.cadex.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                manifest = None

        restore: dict[str, Any] = {"performed": False}
        accepted_digest = str(state.get("accepted_digest") or "")
        if bool(args.get("restore", True)) and accepted_digest and source.strip():
            # Restore pass: re-run THE script into the fresh ephemeral
            # document and assert digest equality — every open re-proves
            # restart determinism and makes document/object inspect live.
            def rerun(text: str) -> dict[str, Any]:
                return self._run_lifecycle(
                    service,
                    "xscript.project.write_script",
                    {
                        "source": text,
                        "expected_revision": str(
                            store.read_state().get("working_revision") or ""
                        ),
                    },
                    cancellation_check=self._cancellation_check(request_id),
                    progress_callback=lambda event: self._send(
                        {"id": request_id, "event": event}
                    ),
                )

            payload = rerun(source)
            repaired = False
            if payload.get("ok") is not True:
                # The working script does not even run. That is not a model
                # the user changed — a script they changed still executes and
                # fails on the *digest* below, which stays a hard error. It is
                # a store left broken by something that had no business
                # writing it: before ADR-044 a refused candidate stayed on
                # disk, and re-running it locked the project shut for good.
                # The accepted revision's own source is pinned beside it and
                # provably reproduces the accepted digest, so use it, and say
                # so in the reply.
                accepted_source = store.read_accepted_source()
                retry = (
                    rerun(accepted_source)
                    if accepted_source.strip() and accepted_source != source
                    else None
                )
                if retry is None or retry.get("ok") is not True:
                    return failure(
                        CADEXD_RESTORE_FAILED,
                        "The restore pass could not re-run the stored script.",
                        restore_failure=payload,
                    )
                payload = retry
                repaired = True
            if str(payload.get("digest") or "") != accepted_digest:
                # The restore pass runs through `write_script`, which is an
                # *accepting* operation: by now it has already recorded what
                # it just built as the accepted revision. For a match that is
                # a no-op. For a mismatch it is the whole model being
                # redefined by whatever the file happened to contain — so the
                # second open of a hand-edited project used to adopt the edit
                # silently, having called it a corruption once (ADR-044).
                store.write(
                    state_updates={
                        "accepted_revision": str(state.get("accepted_revision") or ""),
                        "accepted_contract": state.get("accepted_contract"),
                        "accepted_digest": accepted_digest,
                        "accepted_attempt": state.get("accepted_attempt"),
                    }
                )
                return failure(
                    CADEXD_RESTORE_FAILED,
                    "The restore pass digest does not match the accepted digest.",
                    observed={
                        "restored_digest": payload.get("digest"),
                        "accepted_digest": accepted_digest,
                    },
                )
            restore = {
                "performed": True,
                "digest": str(payload.get("digest") or ""),
                "matches_accepted": True,
            }
            if repaired:
                # The rerun re-wrote script.py and working_revision on its way
                # through, so the store is consistent again by the time this
                # reply is sent.
                restore["repaired_from_accepted"] = True
        return {
            "ok": True,
            "schema": PROTOCOL_SCHEMA,
            "project_root": str(root),
            "budgets": budgets,
            "manifest": manifest,
            "script": self._script_state(),
            "restore": restore,
        }

    def _op_describe_api(
        self, _request_id: str, _args: dict[str, Any]
    ) -> dict[str, Any]:
        return self._run_lifecycle(
            self._service, "xscript.project.describe_api", {}
        )

    def _invalidate_resident_workers(self) -> None:
        """Kill both resident workers: the preview one and the live one.

        Free, because both are stateless by contract: the cost of being
        wrong is one respawn. Called by everything that can change the source,
        the parameters, the assets or the project — deliberately *not* from
        ``open_project``'s restore path, which re-runs the stored script
        through the same lifecycle without changing anything (ADR-055).

        The live session (ADR-109) is invalidated on the same list and for a
        sharper reason than the preview worker is. A preview answering from a
        stale generation shows the wrong poses for a moment; a live session
        answering from one keeps playing a *mechanism that no longer exists*,
        indefinitely, while the viewport says otherwise.
        """

        worker, self._preview_worker = self._preview_worker, None
        if worker is not None:
            worker.invalidate()
        session, self._live_session = self._live_session, None
        if session is not None:
            session.invalidate()

    def _lifecycle_response(
        self, request_id: str, tool_name: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        not_open = self._require_open()
        if not_open is not None:
            return not_open
        # Before the run, not after: this request is about to change the
        # source or the parameters, and a preview answered from the old
        # generation while it does would be answering about a model that no
        # longer exists.
        self._invalidate_resident_workers()
        sink: dict[str, Any] = {}
        payload = self._run_lifecycle(
            self._service,
            tool_name,
            args,
            cancellation_check=self._cancellation_check(request_id),
            progress_callback=lambda event: self._send(
                {"id": request_id, "event": event}
            ),
            result_sink=sink,
        )
        if payload.get("ok"):
            note = getattr(self._service, "note_document_changed", None)
            if callable(note):
                note()
            if "prepared" in sink:
                payload = dict(payload)
                payload["display"] = _display_block(
                    Path(str(sink["prepared"]["staging"])), sink["validated"]
                )
        return payload

    def _op_write_script(
        self, request_id: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        return self._lifecycle_response(
            request_id, "xscript.project.write_script", args
        )

    def _op_edit_script(
        self, request_id: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        return self._lifecycle_response(
            request_id, "xscript.project.edit_script", args
        )

    def _op_set_params(
        self, request_id: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        return self._lifecycle_response(
            request_id, "xscript.project.set_params", args
        )

    def _op_rebuild(self, request_id: str, args: dict[str, Any]) -> dict[str, Any]:
        not_open = self._require_open()
        if not_open is not None:
            return not_open
        from CadexScriptStore import CadexProjectScriptStore

        store = CadexProjectScriptStore(self._project_root)
        source = store.read_source()
        if not source.strip():
            return failure(
                CADEXD_NOT_OPEN, "The open project has no script to rebuild."
            )
        state = store.read_state()
        rebuild_args: dict[str, Any] = {
            "source": source,
            "expected_revision": str(state.get("working_revision") or ""),
        }
        if isinstance(args.get("display"), dict):
            rebuild_args["display"] = args["display"]
        return self._lifecycle_response(
            request_id, "xscript.project.write_script", rebuild_args
        )

    def _op_resolve_pin(
        self, _request_id: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        not_open = self._require_open()
        if not_open is not None:
            return not_open
        if self._injected_resolve_pin is not None:
            resolver = self._injected_resolve_pin
        else:
            from CadexPinResolution import resolve_pin as resolver

        return resolver(self._project_root, args["output"], args["selection"])

    def _op_inspect(self, _request_id: str, args: dict[str, Any]) -> dict[str, Any]:
        not_open = self._require_open()
        if not_open is not None:
            return not_open
        if str(args.get("scope") or "") == "selection":
            return failure(
                CADEXD_PROTOCOL_ERROR,
                "inspect scope 'selection' is shell-side only; cadexd has no "
                "viewport selection.",
            )
        from CadexInspection import capture_inspection, complete_inspection

        try:
            captured = capture_inspection(self._service, args)
        except Exception as exc:
            return failure(
                CADEXD_PROTOCOL_ERROR,
                f"inspect capture failed: {exc}",
                exception_type=exc.__class__.__name__,
            )
        # _cadex_image_attachment (a project-store file path) stays in the
        # response: the shell shares the filesystem and consumes it there.
        return complete_inspection(captured)

    def _op_put_asset(
        self, _request_id: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Copy one mesh file into the open project's ``assets`` directory.

        The shell may not write the store itself (docs/ARCHITECTURE.md: cadexd
        is its sole writer and sole reader), so importing external geometry
        goes through the protocol like everything else. A modeling op, so it
        cannot race a rebuild's asset staging.
        """

        not_open = self._require_open()
        if not_open is not None:
            return not_open
        # An asset is part of the preview generation: mesh.import_file
        # resolves against the staged copy, so a new one is a new model.
        self._invalidate_resident_workers()
        from CadexScriptedRuntime import list_project_assets, store_project_asset
        from CadexTools import tool_failure

        source_path = str(args["source_path"])
        name = str(args.get("name") or "")
        try:
            stored = store_project_asset(self._project_root, source_path, name)
        except (OSError, ValueError) as exc:
            return tool_failure(
                "cadexd.put_asset",
                "ASSET_REJECTED",
                "precondition",
                str(exc),
                requested={"source_path": source_path, "name": name},
                observed={"assets": list_project_assets(self._project_root)},
            )
        return {
            "ok": True,
            **stored,
            "assets": list_project_assets(self._project_root),
        }

    def _op_link_part(
        self, _request_id: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Pull one accepted solid out of another project into this one.

        One op rather than an export from A and an import into B (ADR-138).
        The consuming project pulls, so project A never opens: everything
        this reads is a file under A's root, and the pinned accepted attempt
        is where the exact BREP and the exact source that produced it already
        sit. Refresh is this same call with the same arguments — it ends in
        ``store_project_asset``, where overwriting a name is re-import.

        A modeling op for ``put_asset``'s reason exactly: it writes the store,
        and exclusion against an in-flight rebuild is what stops a container
        landing half-copied while ``_stage_project_assets`` reads.
        """

        not_open = self._require_open()
        if not_open is not None:
            return not_open
        import shutil
        import tempfile

        from CadexLinkedPart import (
            LinkedPartError,
            build_linked_part,
            decode_linked_part,
            source_outputs,
        )
        from CadexScriptedRuntime import list_project_assets, store_project_asset
        from CadexTools import tool_failure

        source_project = str(args["source_project"])
        output = str(args.get("output") or "").strip()
        name = str(args.get("name") or "").strip()
        requested = {
            "source_project": source_project,
            "output": output,
            "name": name,
        }

        def refuse(message: str, candidates: Any = ()) -> dict[str, Any]:
            return tool_failure(
                "cadexd.link_part",
                "LINKED_PART_REJECTED",
                "precondition",
                message,
                requested=requested,
                observed={"assets": list_project_assets(self._project_root)},
                candidates=[str(item) for item in candidates],
            )

        source_root = Path(source_project).expanduser()
        try:
            same = source_root.resolve() == Path(self._project_root).resolve()
        except OSError:
            same = False
        if same:
            return refuse("A project cannot link a part from itself.")
        if not source_root.is_dir():
            return refuse(f"'{source_root}' is not a project directory.")
        if not output:
            # Omitting the output is how a caller asks what is on offer; the
            # names are the answer, not a diagnostic.
            try:
                declared = source_outputs(source_root)
            except LinkedPartError as exc:
                return refuse(str(exc))
            names = [str(item["name"]) for item in declared]
            return refuse(
                f"link_part needs the output to pull from '{source_root}'; it "
                f"declares: {', '.join(names) or '(nothing)'}.",
                candidates=names,
            )

        # An imported part is part of the preview generation for the same
        # reason an imported mesh is: part.import_part resolves against the
        # staged copy, so a new one is a new model.
        self._invalidate_resident_workers()
        try:
            blob = build_linked_part(source_root, output)
        except LinkedPartError as exc:
            return refuse(str(exc), exc.candidates)
        header, _brep = decode_linked_part(blob)
        source = dict(header.get("source") or {})

        target_name = name or f"{output}.cxpart"
        # What is already stored under this name, so the reply can say whether
        # the source project moved. Unreadable or absent means "nothing to
        # compare against", which is a first pull rather than a failure.
        previous_revision = ""
        changed = True
        stored_path = Path(self._project_root) / "assets" / target_name
        if stored_path.is_file():
            try:
                previous, _ = decode_linked_part(stored_path.read_bytes())
            except (LinkedPartError, OSError):
                previous = {}
            if previous:
                previous_revision = str(
                    dict(previous.get("source") or {}).get("revision") or ""
                )
                changed = str(previous.get("shape_sha256") or "") != str(
                    header.get("shape_sha256") or ""
                )

        scratch = Path(tempfile.mkdtemp(prefix="cadex-link-part-"))
        try:
            # A fixed scratch name, never the caller's: `target_name` is
            # validated by `store_project_asset` (traversal, length, suffix),
            # and joining it onto a path before that check would be the one
            # place it could escape.
            staged = scratch / "part.cxpart"
            staged.write_bytes(blob)
            stored = store_project_asset(
                self._project_root, str(staged), target_name
            )
        except (OSError, ValueError) as exc:
            return refuse(str(exc))
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
        return {
            "ok": True,
            **stored,
            "source_revision": str(source.get("revision") or ""),
            "source_digest": str(source.get("digest") or ""),
            "previous_revision": previous_revision,
            "changed": bool(changed),
            "assets": list_project_assets(self._project_root),
        }

    def _op_preview_params(
        self, _request_id: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Answer a parameter change with solved placements, or decline.

        A read-only oracle in front of ``set_params``, not a replacement for
        it (ADR-055): it writes nothing, publishes nothing, and moves no
        revision or digest. The accepting path behind it is still what makes
        a change real, so **every** way this can go wrong ends in
        ``previewable: false`` with a reason rather than a failure envelope —
        an optimisation that fails loudly is worse than one that fails
        silently, because the shell has a correct answer already in flight.
        """

        not_open = self._require_open()
        if not_open is not None:
            return not_open
        from CadexScriptedRuntime import DomainRuntimeFailure, prepare_preview

        try:
            prepared = prepare_preview(self._service, dict(args["values"]))
        except (DomainRuntimeFailure, ValueError, KeyError, OSError) as exc:
            return _declined_preview("", f"this preview could not be prepared: {exc}")

        revision = str(prepared["revision"])
        expected = str(args["expected_revision"])
        if expected and expected != revision:
            # Same guard as set_params. A preview of a revision the caller is
            # not looking at would pose the viewport from a model the user
            # never asked about.
            return _declined_preview(
                revision,
                f"expected revision {expected!r}, the store is at {revision!r}",
            )

        if self._preview_worker is None:
            from CadexWarmWorker import CadexWarmWorker

            self._preview_worker = CadexWarmWorker(self._project_root)
        answer = self._preview_worker.preview(prepared, prepared["param_values"])
        if answer.get("previewable") is not True:
            return _declined_preview(
                revision, str(answer.get("reason") or "not previewable")
            )
        return {
            "ok": True,
            "previewable": True,
            "revision": revision,
            "placements": dict(answer.get("placements") or {}),
        }

    def _op_live_open(
        self, _request_id: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Start a live session on the accepted revision's rollout (ADR-109).

        A **read** op: it writes nothing, publishes nothing, and moves no
        revision or digest, so it queues behind an in-flight rebuild rather
        than refusing one. That matters more here than for a preview — a
        running simulation that blocked the AI from editing the script would
        make watching the machine and changing it mutually exclusive, and
        watching it *while* it changes is the point.

        Every way this can fail answers ``live: false`` with a reason, the
        same shape ``preview_params`` refuses in. A project with no accepted
        rollout is a **state**, not an error: the panel says "build a rollout
        first" rather than showing the user a failure envelope.

        ``variation`` defaults **true** — play the task as the bundle
        declares it. False is the calm session (ADR-110): one fixed machine
        at the solved pose, with the only force acting the one the user is
        applying. It is not a new engine state, only the unseeded episode
        ``evaluate_episode`` has always had, finally reachable from here.
        """

        not_open = self._require_open()
        if not_open is not None:
            return not_open
        from CadexScriptedRuntime import LiveBundleUnavailable, prepare_live

        try:
            prepared = prepare_live(self._project_root, str(args["output"]))
        except (LiveBundleUnavailable, OSError, ValueError, KeyError) as exc:
            return _declined_live_open(str(exc))

        from CadexLiveSession import CadexLiveSession, LiveSessionFailure

        session = self._live_session
        if session is None:
            session = self._live_session = CadexLiveSession(self._project_root)
        seed = args.get("seed")
        try:
            opened = session.open(
                prepared,
                None if seed is None else int(seed),
                bool(args.get("variation", True)),
            )
        except LiveSessionFailure as exc:
            return _declined_live_open(str(exc))
        # From the host rather than from the worker: the worker plays three
        # staged files and has no idea what the project calls them, and this
        # is the side that resolved and digest-checked them.
        identity = dict(prepared.get("policy_identity") or {})
        return {
            "ok": True,
            "live": True,
            **opened,
            "policy": {
                "label": str(identity.get("label") or ""),
                "weights": str(identity.get("weights") or ""),
                "sha256": str(identity.get("sha256") or ""),
                "trained_label": str(identity.get("trained_label") or ""),
            },
        }

    def _op_live_step(
        self, _request_id: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Advance the running episode and hand back the frames it made."""

        not_open = self._require_open()
        if not_open is not None:
            return not_open
        session = self._live_session
        if session is None or not session.is_open:
            return _declined_live_step("no live session is open")
        from CadexLiveSession import LiveSessionFailure

        try:
            answer = session.step(int(args["steps"]), args.get("push"))
        except LiveSessionFailure as exc:
            self._live_session = None
            return _declined_live_step(str(exc))
        return {"ok": True, "live": True, **answer}

    def _op_live_close(
        self, _request_id: str, _args: dict[str, Any]
    ) -> dict[str, Any]:
        """End the session. Idempotent: closing a closed session is fine."""

        session, self._live_session = self._live_session, None
        if session is not None:
            session.close()
        return {"ok": True, "live": False, "closed": True}

    def _op_shutdown(self, _request_id: str, _args: dict[str, Any]) -> dict[str, Any]:
        self.shutdown_requested = True
        return {"ok": True, "shutting_down": True}

    def close(self) -> None:
        self._invalidate_resident_workers()
        if self._document is not None:
            try:
                import FreeCAD as App

                App.closeDocument(self._document.Name)
            except Exception:
                pass
            self._document = None
            self._service = None


def main() -> int:
    """cadexd entry: fd hijack, ready banner, reader thread, serial loop."""

    module_root = Path(__file__).resolve().parent
    if str(module_root) not in sys.path:
        sys.path.insert(0, str(module_root))

    # stdout-pollution defense: keep the protocol on a private fd; anything
    # that prints to fd 1 (FreeCAD console included) lands on stderr.
    protocol_fd = os.dup(1)
    os.dup2(2, 1)
    protocol_out = os.fdopen(protocol_fd, "wb", buffering=0)
    write_lock = threading.Lock()

    def send(frame: dict[str, Any]) -> None:
        data = encode_frame(frame)
        with write_lock:
            protocol_out.write(data)

    server = CadexdServer(send)
    send(
        {
            "event": {
                "event": "ready",
                "schema": PROTOCOL_SCHEMA,
                "pid": os.getpid(),
                "ops": sorted(OP_ARG_SPECS),
            },
            "id": None,
        }
    )

    requests: queue.SimpleQueue = queue.SimpleQueue()

    def reader() -> None:
        try:
            for line in sys.stdin.buffer:
                line = line.strip()
                if not line:
                    continue
                admitted = server.admit(line)
                if admitted is not None:
                    requests.put(admitted)
        finally:
            requests.put(None)  # stdin EOF: the shell died — self-exit.

    threading.Thread(target=reader, name="cadexd-reader", daemon=True).start()

    try:
        while True:
            item = requests.get()
            if item is None:
                break
            request_id, op, args = item
            server.dispatch(request_id, op, args)
            if server.shutdown_requested:
                break
    finally:
        server.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
