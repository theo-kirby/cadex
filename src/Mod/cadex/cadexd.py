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
                                busy_request_id=self._busy_request_id,
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
            payload = self._run_lifecycle(
                service,
                "xscript.project.write_script",
                {
                    "source": source,
                    "expected_revision": str(state.get("working_revision") or ""),
                },
                cancellation_check=self._cancellation_check(request_id),
                progress_callback=lambda event: self._send(
                    {"id": request_id, "event": event}
                ),
            )
            if payload.get("ok") is not True:
                return failure(
                    CADEXD_RESTORE_FAILED,
                    "The restore pass could not re-run the accepted script.",
                    restore_failure=payload,
                )
            if str(payload.get("digest") or "") != accepted_digest:
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

    def _lifecycle_response(
        self, request_id: str, tool_name: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        not_open = self._require_open()
        if not_open is not None:
            return not_open
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

    def _op_shutdown(self, _request_id: str, _args: dict[str, Any]) -> dict[str, Any]:
        self.shutdown_requested = True
        return {"ok": True, "shutting_down": True}

    def close(self) -> None:
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
