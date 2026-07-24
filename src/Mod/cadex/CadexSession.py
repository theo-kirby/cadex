# SPDX-License-Identifier: LGPL-2.1-or-later

"""Cadex provider session orchestration.

The session owns context, tool exposure, execution, steering, cancellation,
and persistence. Product intent stays in the conversation. FreeCAD state stays
in the live state packet. There is no workflow phase machine or prose parser.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from importlib import import_module
import json
import logging
import time
from typing import Any, Callable

from CadexCore import CadexService, get_service
from CadexProvider import (
    AnthropicProvider,
    BaseProvider,
    ChatGPTSubscriptionProvider,
    OfflineProvider,
    OpenAIProvider,
    ProviderUnavailable,
    provider_tool_schema_digest,
)
from CadexModelingSurface import (
    CORE_CONVERSATION_VIEW_TOOLS,
    ModelingSurface,
    infer_engine_from_names,
    resolve_service_surface,
    validate_surface_names,
)
from CadexTools import (
    SafetyLevel,
    ToolArgumentValidationError,
    normalize_tool_failure,
    tool_failure,
)
import CadexScriptedDomains as xscript_domains


ProgressCallback = Callable[[dict[str, Any]], None]
CancellationCheck = Callable[[], bool]
SteeringCheck = Callable[[], list[str]]
QuestionCallback = Callable[[list[dict[str, Any]]], list[dict[str, Any]]]
DocumentThreadDispatch = Callable[[Callable[[], Any]], Any]

PROVIDER_SAFE_LEVELS = {
    SafetyLevel.READ,
    SafetyLevel.VIEW,
    SafetyLevel.SAFE_WRITE,
}

CORE_PROVIDER_TOOLS = set(CORE_CONVERSATION_VIEW_TOOLS)

#: The complete xscript authoring surface: core/conversation/file tools plus
#: the four xscript.project.* tools. The per-domain lifecycle surface was
#: dissolved by the Phase 2.4 tool-surface swap (ADR-013).
XSCRIPT_PROVIDER_TOOLS = {
    *CORE_CONVERSATION_VIEW_TOOLS,
    *xscript_domains.PROJECT_PACK.tool_names,
}

ISOLATED_GEOMETRY_TOOLS = {"partdesign.measure"}

SCRIPTED_ENGINE_PROVIDER_TOOLS = {
    "xscript": XSCRIPT_PROVIDER_TOOLS,
}

logger = logging.getLogger("Cadex.session")

# MAX_PROVIDER_TOOL_SCHEMAS_JSON_BYTES is a real transport ceiling: the whole
# frozen surface is committed once to the provider wire (Codex app-server dynamic
# tool declarations), so exceeding it is a hard error. The other two budgets below
# are self-imposed discipline thresholds, not transport limits: exceeding them is
# a warning that lets the turn proceed. Experimental mode's unified "Parts"
# surface intentionally bundles multiple tool packs and routinely runs past the
# tactical XScript budget, so it must not be a hard failure.
MAX_TURN_CONTEXT_JSON_BYTES = 16 * 1024
MAX_PROVIDER_TOOL_SCHEMAS_JSON_BYTES = 128 * 1024
# The document-level file.* and core.relink_object tools ride on every surface,
# adding ~4.6 KiB to each XScript wire snapshot; a lean single domain lands
# near 22 KiB. The tactical budget stays at 20 KiB as a discipline signal (1/8 of
# the provider budget); crossing it warns rather than aborts the turn.
MAX_XSCRIPT_TOOL_SCHEMAS_JSON_BYTES = 20 * 1024

# Cross-message memory: prior user/assistant turns are re-sent so the model keeps
# context between messages. Bound the transcript so it never blows the window --
# keep the most recent turns within both a turn count and a byte budget.
MAX_HISTORY_TURNS = 24
MAX_HISTORY_CONTENT_BYTES = 24 * 1024

def _experimental_mode_session() -> bool:
    """True in a GUI experimental-mode session; headless imports degrade to manual."""
    try:
        from CadexExperimentalMode import is_experimental_mode_session
    except Exception:
        return False
    return bool(is_experimental_mode_session())


def _budget_notice_level() -> int:
    """Self-imposed budget notices are debug-only in experimental mode.

    These are "sending it anyway" discipline signals, not errors. FreeCAD's
    Report view auto-shows on warnings, so surfacing them in experimental mode
    reads as a spurious "too much context" popup. Genuine errors are unaffected.
    """
    return logging.DEBUG if _experimental_mode_session() else logging.WARNING


@dataclass(frozen=True)
class CadexResponse:
    provider: str
    final_output: str
    context: dict[str, Any]
    tool_trace: list[dict[str, Any]]
    error: str | None = None


def _on_document_thread(
    dispatch: DocumentThreadDispatch | None,
    operation: Callable[[], Any],
) -> Any:
    """Run one FreeCAD/service operation on the owning document thread."""
    if dispatch is None:
        return operation()
    return dispatch(operation)


def _schedule_parameters_panel_refresh(
    dispatch: DocumentThreadDispatch | None,
) -> None:
    """Refresh the slider panel on the GUI thread after a metadata-only write.

    A controls write changes no geometry and no document, so the document
    observer never fires; the panel is nudged here instead. QTimer scheduling
    is marshalled to the GUI thread because tools run off it.
    """
    try:
        import FreeCAD as App

        if not bool(getattr(App, "GuiUp", False)):
            return
    except Exception:
        return

    def fire() -> None:
        try:
            import CadexParametersPanel

            CadexParametersPanel.schedule_refresh()
        except Exception:
            pass

    try:
        _on_document_thread(dispatch, fire)
    except Exception:
        pass


def _document_recompute_state(service: CadexService) -> dict[str, Any]:
    """Read the active document's native recompute state on its owning thread."""
    document = service._active_document()
    return {
        "document": str(getattr(document, "Name", "") or "") or None,
        "recomputing": bool(getattr(document, "Recomputing", False))
        if document is not None
        else False,
        "recompute_pending": bool(getattr(document, "RecomputePending", False))
        if document is not None
        else False,
    }


def _wait_for_document_idle(
    service: CadexService,
    dispatch: DocumentThreadDispatch | None,
    cancellation_check: CancellationCheck | None,
    progress_callback: ProgressCallback | None,
) -> dict[str, Any]:
    """Wait off-thread until FreeCAD finishes the active native recompute."""
    started = time.monotonic()
    next_progress = started
    while True:
        state = _on_document_thread(
            dispatch,
            lambda: _document_recompute_state(service),
        )
        if not state["recomputing"] and not state["recompute_pending"]:
            state["ok"] = True
            state["waited_seconds"] = round(time.monotonic() - started, 3)
            return state
        if cancellation_check is not None and cancellation_check():
            return {
                "ok": False,
                "cancelled": True,
                "document": state["document"],
                "recomputing": state["recomputing"],
                "recompute_pending": state["recompute_pending"],
                "waited_seconds": round(time.monotonic() - started, 3),
            }
        now = time.monotonic()
        if now >= next_progress:
            _emit(
                progress_callback,
                {
                    "event": "document_recompute_waiting",
                    "document": state["document"],
                    "queued": state["recompute_pending"],
                    "elapsed_seconds": round(now - started, 1),
                },
            )
            next_progress = now + 2.0
        time.sleep(0.05)


def _document_idle_failure(
    tool_name: str,
    requested: dict[str, Any],
    wait_state: dict[str, Any],
) -> dict[str, Any]:
    return tool_failure(
        tool_name,
        "RUN_CANCELLED",
        "precondition",
        "The CAD run was stopped while waiting for FreeCAD to finish recomputing.",
        requested=requested,
        observed={
            "document": wait_state.get("document"),
            "waited_seconds": wait_state.get("waited_seconds", 0.0),
            "recomputing": bool(wait_state.get("recomputing", False)),
            "recompute_pending": bool(
                wait_state.get("recompute_pending", False)
            ),
        },
    )


@dataclass(frozen=True)
class _ScriptedEngineRunner:
    """How one scripted engine's runner tools execute through the session.

    Scripted geometry executes outside the GUI process, then waits for the live
    document to become idle before a bounded owner-thread publication. Detached
    native BREP may be imported on the provider worker; STEP and other
    document-coupled transfers remain on the document thread.
    """

    engine: str
    module_name: str
    failure_exception_name: str
    bridge_failure_code: str
    bridge_failure_stage: str
    import_on_document_thread: bool
    prepare_off_document_thread: bool
    persist_artifacts_off_document_thread: bool
    started_event_output_count: bool
    completed_event_fidelity: bool
    tool_names: frozenset[str]


# The runner-bridge machinery served the isolated build123d/openscad engines,
# which have been removed. xscript/xscript execute through the domain runtime,
# not this bridge, so no engine registers a runner today.
_SCRIPTED_ENGINE_RUNNERS: tuple[_ScriptedEngineRunner, ...] = ()

_SCRIPTED_RUNNER_BY_TOOL: dict[str, _ScriptedEngineRunner] = {
    name: runner for runner in _SCRIPTED_ENGINE_RUNNERS for name in runner.tool_names
}


def _record_failed_candidate(
    record_failed_attempt: Callable[[dict[str, Any], dict[str, Any]], Any],
    prepared: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    """Attach the persisted failed-attempt artifact record to the payload."""
    observed = payload.get("observed")
    if not isinstance(observed, dict):
        observed = {"raw_observed": observed}
    try:
        observed["model_candidate"] = record_failed_attempt(prepared, payload)
    except Exception as exc:
        observed["artifact_record_error"] = {
            "exception_type": exc.__class__.__name__,
            "error": str(exc),
        }
    payload["observed"] = observed


def _run_scripted_engine_tool(
    runner: _ScriptedEngineRunner,
    service: CadexService,
    tool_name: str,
    args: dict[str, Any],
    *,
    document_thread_dispatch: DocumentThreadDispatch | None,
    cancellation_check: CancellationCheck | None,
    progress_callback: ProgressCallback | None,
) -> dict[str, Any]:
    """Run one scripted-engine tool through the shared prepare/execute path."""
    module = import_module(runner.module_name)
    failure_type = getattr(module, runner.failure_exception_name)
    persist_artifacts = getattr(module, "persist_commit_artifacts", None)
    finish_artifacts = getattr(module, "finish_commit_artifacts", None)
    if runner.persist_artifacts_off_document_thread and (
        not callable(persist_artifacts) or not callable(finish_artifacts)
    ):
        return tool_failure(
            tool_name,
            "SCRIPTED_ARTIFACT_PROTOCOL_ERROR",
            "precondition",
            "The scripted engine does not implement its declared worker-side "
            "artifact persistence contract; execution was not started.",
            requested=args,
        )
    prepared: dict[str, Any] | None = None
    payload: dict[str, Any] | None = None
    try:
        if runner.prepare_off_document_thread:
            captured = _on_document_thread(
                document_thread_dispatch,
                lambda: module.capture_execution_state(service, tool_name, args),
            )
            prepared = module.prepare_execution_from_state(
                captured, tool_name, args
            )
        else:
            prepared = _on_document_thread(
                document_thread_dispatch,
                lambda: module.prepare_execution(service, tool_name, args),
            )
        _emit(
            progress_callback,
            {
                "event": "scripted_model_update_started",
                "engine": runner.engine,
                "document_name": prepared["document_name"],
                "model_id": prepared["model_id"],
                "revision": prepared["revision"],
            },
        )
        started_event = {
            "event": f"{runner.engine}_execution_started",
            "model_name": prepared["model_name"],
        }
        if runner.started_event_output_count:
            started_event["output_count"] = len(prepared["expected_outputs"])
        _emit(progress_callback, started_event)
        execution = module.execute_prepared(
            prepared,
            cancellation_check=cancellation_check,
        )
        if not execution.get("ok"):
            execution["requested"] = dict(args)
            payload = execution
        else:
            idle_state = _wait_for_document_idle(
                service,
                document_thread_dispatch,
                cancellation_check,
                progress_callback,
            )
            if not idle_state.get("ok"):
                payload = _document_idle_failure(tool_name, args, idle_state)
            else:
                if runner.import_on_document_thread:
                    imported = _on_document_thread(
                        document_thread_dispatch,
                        lambda: module.import_validated_outputs(prepared, execution),
                    )
                else:
                    imported = module.import_validated_outputs(prepared, execution)
                payload = _on_document_thread(
                    document_thread_dispatch,
                    lambda: module.commit_outputs(
                        service, prepared, execution, imported
                    ),
                )
                continue_commit = getattr(module, "continue_commit", None)
                cancel_commit = getattr(module, "cancel_commit", None)
                resolve_rebind = getattr(module, "resolve_commit_rebind", None)
                finish_rebind = getattr(module, "finish_commit_rebind", None)
                while isinstance(
                    payload.get("_cadex_async_commit"), dict
                ) or isinstance(payload.get("_cadex_async_rebind"), dict):
                    if isinstance(payload.get("_cadex_async_rebind"), dict):
                        if not callable(resolve_rebind) or not callable(finish_rebind):
                            payload = tool_failure(
                                tool_name,
                                "SCRIPTED_REBIND_PROTOCOL_ERROR",
                                "native_recompute",
                                "The scripted engine returned a pending Part "
                                "rebind without a complete worker continuation.",
                                requested=args,
                            )
                            break
                        if cancellation_check is not None and cancellation_check():
                            if callable(cancel_commit):
                                payload = _on_document_thread(
                                    document_thread_dispatch,
                                    lambda: cancel_commit(service, payload),
                                )
                            else:
                                payload = _document_idle_failure(
                                    tool_name,
                                    args,
                                    {
                                        "document": prepared["document_name"],
                                        "waited_seconds": 0.0,
                                    },
                                )
                            break
                        resolved_rebind = resolve_rebind(payload)
                        payload = _on_document_thread(
                            document_thread_dispatch,
                            lambda: finish_rebind(
                                service, payload, resolved_rebind
                            ),
                        )
                        continue
                    idle_state = _wait_for_document_idle(
                        service,
                        document_thread_dispatch,
                        cancellation_check,
                        progress_callback,
                    )
                    if not idle_state.get("ok"):
                        if callable(cancel_commit):
                            payload = _on_document_thread(
                                document_thread_dispatch,
                                lambda: cancel_commit(service, payload),
                            )
                        else:
                            payload = _document_idle_failure(
                                tool_name, args, idle_state
                            )
                        break
                    if not callable(continue_commit):
                        payload = tool_failure(
                            tool_name,
                            "SCRIPTED_COMMIT_PROTOCOL_ERROR",
                            "native_recompute",
                            "The scripted engine returned pending native work "
                            "without a continuation implementation.",
                            requested=args,
                        )
                        break
                    payload = _on_document_thread(
                        document_thread_dispatch,
                        lambda: continue_commit(service, payload),
                    )
                if isinstance(payload.get("_cadex_async_validation"), dict):
                    validate_commit = getattr(module, "validate_commit", None)
                    finish_validation = getattr(
                        module, "finish_commit_validation", None
                    )
                    if not callable(validate_commit) or not callable(
                        finish_validation
                    ):
                        payload = tool_failure(
                            tool_name,
                            "SCRIPTED_VALIDATION_PROTOCOL_ERROR",
                            "native_recompute",
                            "The scripted engine returned pending validation "
                            "without a complete validation implementation.",
                            requested=args,
                        )
                    elif cancellation_check is not None and cancellation_check():
                        if callable(cancel_commit):
                            payload = _on_document_thread(
                                document_thread_dispatch,
                                lambda: cancel_commit(service, payload),
                            )
                        else:
                            payload = _document_idle_failure(
                                tool_name,
                                args,
                                {
                                    "document": prepared["document_name"],
                                    "waited_seconds": 0.0,
                                },
                            )
                    else:
                        validation = validate_commit(payload)
                        if (
                            cancellation_check is not None
                            and cancellation_check()
                            and callable(cancel_commit)
                        ):
                            payload = _on_document_thread(
                                document_thread_dispatch,
                                lambda: cancel_commit(service, payload),
                            )
                        else:
                            payload = _on_document_thread(
                                document_thread_dispatch,
                                lambda: finish_validation(
                                    service, payload, validation
                                ),
                            )
                artifact_request = payload.get("_cadex_async_artifact")
                if runner.persist_artifacts_off_document_thread:
                    if payload.get("ok"):
                        artifact_result = (
                            persist_artifacts(payload)
                            if isinstance(artifact_request, dict)
                            else {
                                "ok": False,
                                "error": (
                                    "The validated scripted update did not provide "
                                    "its required artifact request."
                                ),
                                "exception_type": "ScriptedArtifactProtocolError",
                            }
                        )
                        payload = _on_document_thread(
                            document_thread_dispatch,
                            lambda: finish_artifacts(
                                service, payload, artifact_result
                            ),
                        )
                elif isinstance(artifact_request, dict):
                    raise RuntimeError(
                        f"{runner.engine} returned an undeclared worker artifact request."
                    )
        if payload is not None and payload.get("ok"):
            completed_event = {
                "event": f"{runner.engine}_execution_completed",
                "model_name": prepared["model_name"],
                "output_count": len(payload.get("outputs") or []),
            }
            if runner.completed_event_fidelity:
                completed_event["fidelity"] = payload.get("fidelity")
            _emit(progress_callback, completed_event)
    except failure_type as exc:
        payload = exc.payload
        if not payload.get("requested"):
            payload["requested"] = dict(args)
    except Exception as exc:
        payload = tool_failure(
            tool_name,
            runner.bridge_failure_code,
            runner.bridge_failure_stage,
            str(exc),
            requested=args,
            observed={"exception_type": exc.__class__.__name__},
        )
    finally:
        if prepared is not None:
            if payload is not None and not payload.get("ok"):
                _record_failed_candidate(
                    module.record_failed_attempt, prepared, payload
                )
            module.cleanup_prepared(prepared)
    assert payload is not None
    if prepared is not None:
        _emit(
            progress_callback,
            {
                "event": "scripted_model_update_finished",
                "engine": runner.engine,
                "document_name": prepared["document_name"],
                "model_id": prepared["model_id"],
                "revision": prepared["revision"],
                "ok": bool(payload.get("ok")),
            },
        )
    return payload


def run_scripted_engine_operation(
    service: CadexService,
    tool_name: str,
    args: dict[str, Any],
    *,
    document_thread_dispatch: DocumentThreadDispatch | None,
    cancellation_check: CancellationCheck | None = None,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Run one scripted operation through the production async lifecycle."""

    runner = _SCRIPTED_RUNNER_BY_TOOL.get(tool_name)
    if runner is None:
        raise ValueError(f"No scripted-engine runner owns {tool_name!r}.")
    return _run_scripted_engine_tool(
        runner,
        service,
        tool_name,
        dict(args),
        document_thread_dispatch=document_thread_dispatch,
        cancellation_check=cancellation_check,
        progress_callback=progress_callback,
    )


def choose_provider(
    service: CadexService,
    prefer_online: bool = True,
) -> BaseProvider:
    if not prefer_online:
        return OfflineProvider()
    provider_name = service.provider_name()
    auth = service.auth_state()
    if provider_name != "chatgpt" and not auth.can_call_provider:
        return OfflineProvider()
    if provider_name == "chatgpt":
        return ChatGPTSubscriptionProvider(
            model=service.provider_model(),
            reasoning_effort=service.provider_reasoning_effort(),
            web_search_enabled=service.web_search_enabled(),
            skills_enabled=service.codex_skills_enabled(),
        )
    if provider_name in {"anthropic", "claude-code"}:
        # Claude Code subscriptions ride the same Messages API adapter; the
        # OAuth access token read from Claude Code's credential file is
        # detected downstream and sent as a Bearer token.
        return AnthropicProvider(
            model=service.provider_model(),
            api_key=service.provider_api_key(),
            reasoning_effort=service.provider_reasoning_effort(),
            base_url=service.provider_base_url(),
            web_search_enabled=service.web_search_enabled(),
        )
    return OpenAIProvider(
        model=service.provider_model(),
        api_key=service.provider_api_key(),
        reasoning_effort=service.provider_reasoning_effort(),
        base_url=service.provider_base_url(),
        web_search_enabled=service.web_search_enabled(),
    )


def _active_document_exists(service: CadexService) -> bool:
    return service._active_document() is not None


def _surface_tool_names(
    service: CadexService,
    workbench: str | None,
) -> set[str]:
    resolution = resolve_service_surface(service, workbench)
    names = set(resolution.tool_names)
    if not _active_document_exists(service):
        names = {
            name
            for name in names
            if service.registry.get(name).safety in {SafetyLevel.READ, SafetyLevel.VIEW}
        }
    return names


def _current_edit_mode(service: CadexService) -> str:
    return _edit_mode_from_runtime_state(_minimal_runtime_state(service))


def _edit_mode_from_runtime_state(state: dict[str, Any]) -> str:
    if state.get("edit_mode") and _active_sketch_name(state):
        return "sketch"
    return "none"


def _provider_safe_tool_names(
    service: CadexService,
    workbench: str | None,
    edit_mode: str,
) -> list[str]:
    """Return live-callable names without serializing provider schemas."""

    result: list[str] = []
    for name in sorted(_surface_tool_names(service, workbench)):
        tool = service.registry.get(name)
        if tool.safety not in PROVIDER_SAFE_LEVELS:
            continue
        if not tool.spec.supports_edit_mode(edit_mode):
            continue
        result.append(name)
    return result


def is_provider_safe_tool(
    service: CadexService,
    tool_name: str,
    workbench: str | None = None,
) -> bool:
    try:
        tool = service.registry.get(tool_name)
    except KeyError:
        return False
    active = workbench or service.active_workbench_name()
    if tool.safety not in PROVIDER_SAFE_LEVELS:
        return False
    if tool_name not in _surface_tool_names(service, active):
        return False
    return tool.spec.supports_edit_mode(_current_edit_mode(service))


def provider_tool_schemas(
    service: CadexService,
    workbench: str | None,
    *,
    runtime_state: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    state = (
        runtime_state
        if runtime_state is not None
        else _minimal_runtime_state(service)
    )
    names = _provider_safe_tool_names(
        service,
        workbench,
        _edit_mode_from_runtime_state(state),
    )
    return [
        _provider_schema_copy(
            service.registry.get(name).to_schema(active_workbench=workbench)
        )
        for name in names
    ]


def _live_provider_surface_state(service: CadexService) -> dict[str, Any]:
    """Capture one coherent authorization snapshot on the document thread."""

    workbench = service.active_workbench_name()
    resolution = resolve_service_surface(service, workbench)
    runtime_state = _minimal_runtime_state(service)
    return {
        "workbench": workbench,
        "engine": resolution.engine,
        "domain": resolution.domain,
        "surface_id": resolution.surface_id,
        "available": resolution.available,
        "unavailable_reason": resolution.unavailable_reason,
        "runtime_state": runtime_state,
        "tool_names": _provider_safe_tool_names(
            service,
            workbench,
            _edit_mode_from_runtime_state(runtime_state),
        ),
    }


def _scripted_engines_in_tool_names(names: list[str]) -> list[str]:
    return [
        engine
        for engine in SCRIPTED_ENGINE_PROVIDER_TOOLS
        if any(name.startswith(f"{engine}.") for name in names)
    ]


def _turn_start_tool_surface(
    workbench: str | None,
    schemas: list[dict[str, Any]],
    *,
    resolution: ModelingSurface | None = None,
    engine: str | None = None,
) -> dict[str, Any]:
    """Validate and freeze the complete provider surface for one turn.

    ChatGPT dynamic tool declarations cannot change after the app-server thread
    starts. Every attempted call is reauthorized against the live engine and
    workbench tuple by the session tool runner.
    """
    try:
        schema_json_bytes = len(
            json.dumps(
                schemas,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"The turn-start provider schemas are not JSON serializable: {exc}"
        ) from exc
    if schema_json_bytes > MAX_PROVIDER_TOOL_SCHEMAS_JSON_BYTES:
        raise ValueError(
            "The exact turn-start provider schemas exceed the deterministic "
            f"{MAX_PROVIDER_TOOL_SCHEMAS_JSON_BYTES}-byte wire limit "
            f"({schema_json_bytes} bytes)."
        )
    if not schemas:
        raise ValueError("The turn-start provider surface has no tools.")
    if any(not isinstance(schema, dict) for schema in schemas):
        raise ValueError("Every turn-start provider tool schema must be an object.")
    names = [str(schema.get("name") or "").strip() for schema in schemas]
    if any(not name for name in names):
        raise ValueError("Every turn-start provider tool schema must have a name.")
    if len(names) != len(set(names)):
        raise ValueError("The turn-start provider surface contains duplicate tools.")
    resolved_engine = str(engine or "").strip().lower()
    if resolution is not None:
        if resolved_engine and resolved_engine != resolution.engine:
            raise ValueError("The requested engine does not match the resolved surface.")
        resolved_engine = resolution.engine
    if not resolved_engine:
        resolved_engine = infer_engine_from_names(names)
    if (
        resolved_engine in {"xscript", "xscript"}
        and schema_json_bytes > MAX_XSCRIPT_TOOL_SCHEMAS_JSON_BYTES
    ):
        logger.log(
            _budget_notice_level(),
            "The XScript provider schemas exceed the tactical %d-byte budget "
            "(%d bytes); serving the surface anyway.",
            MAX_XSCRIPT_TOOL_SCHEMAS_JSON_BYTES,
            schema_json_bytes,
        )
    if resolution is None:
        from CadexModelingSurface import resolve_modeling_surface

        resolution = resolve_modeling_surface(workbench, resolved_engine)
    # Experimental mode intentionally serves a mixed-namespace "Parts" surface (engine
    # tools + direct Part/Assembly + core.relink_object), which the single-
    # namespace surface validator rejects. The surface is fork-controlled and
    # session-constant, so validate only non-experimental-mode turns. The decision
    # is recorded on the frozen snapshot so the provider transport (which may
    # re-validate inside a spawned child process, where the GUI session flag is
    # not readable) applies the same exemption without re-detecting the mode.
    unified = (
        str(workbench or "") == "PartDesignWorkbench" and _experimental_mode_session()
    )
    if not unified:
        validate_surface_names(
            workbench=workbench,
            engine=resolved_engine,
            names=names,
            allowed_names=resolution.tool_names,
        )
    return {
        "kind": "turn_start_snapshot",
        "frozen": True,
        "workbench": str(workbench or ""),
        "engine": resolved_engine,
        "domain": resolution.domain,
        "surface_id": resolution.surface_id,
        "available": resolution.available,
        "unavailable_reason": resolution.unavailable_reason,
        "tool_names": names,
        "schema_count": len(schemas),
        "schema_sha256": provider_tool_schema_digest(schemas),
        "unified": unified,
    }


def _provider_schema_copy(schema: dict[str, Any]) -> dict[str, Any]:
    """Return only the callable contract that a provider model needs."""

    def compact(value: Any, path: tuple[str, ...] = ()) -> Any:
        if isinstance(value, list):
            return [compact(item, path + ("[]",)) for item in value]
        if not isinstance(value, dict):
            return value
        result: dict[str, Any] = {}
        for key, item in value.items():
            if key == "default":
                continue
            if key == "description":
                if len(path) == 2 and path[0] == "properties":
                    result[key] = item
                continue
            result[key] = compact(item, path + (str(key),))
        return result

    parameters = schema.get("parameters")
    if not isinstance(parameters, dict):
        raise ValueError(f"Provider tool {schema.get('name')!r} has no parameters.")
    return {
        "name": str(schema.get("name") or ""),
        "description": str(schema.get("description") or ""),
        "parameters": compact(parameters),
    }


def _minimal_runtime_state(service: CadexService) -> dict[str, Any]:
    """Read edit ownership only; never recompute or summarize geometry."""

    getter = getattr(service, "provider_edit_object_summary", None)
    edit_object = getter() if callable(getter) else None
    if not isinstance(edit_object, dict):
        return {"edit_mode": False, "active_sketch": None}
    is_sketch = str(edit_object.get("type") or "") == "Sketcher::SketchObject"
    return {
        "edit_mode": True,
        "edit_object": edit_object,
        "active_sketch": (
            {"name": str(edit_object.get("name") or "")} if is_sketch else None
        ),
    }


def _context_for_provider(
    service: CadexService,
    session_trigger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw_context = service.provider_context_summary()
    # Treat the session boundary as the final model-context allowlist. This
    # prevents any service implementation from accidentally reintroducing broad
    # CAD or domain snapshots.
    allowed_turn_facts = (
        "document",
        "selection",
        "view_screenshot",
        "reference_images",
    )
    context = {
        key: raw_context[key]
        for key in allowed_turn_facts
        if key in raw_context
    }
    workbench = service.active_workbench_name()
    resolution = resolve_service_surface(service, workbench)
    context["workbench"] = workbench
    context["modeling_surface"] = {
        "workbench": str(resolution.workbench or ""),
        "engine": resolution.engine,
        "domain": resolution.domain,
        "surface_id": resolution.surface_id,
        "available": resolution.available,
        **(
            {"unavailable_reason": resolution.unavailable_reason}
            if not resolution.available
            else {}
        ),
    }
    context["_cadex_debug"] = service.provider_debug_config()
    runtime_state = _minimal_runtime_state(service)
    schemas = provider_tool_schemas(
        service,
        workbench,
        runtime_state=runtime_state,
    )
    context["provider_tool_schemas"] = schemas
    try:
        turn_surface = _turn_start_tool_surface(workbench, schemas, resolution=resolution)
    except ValueError as exc:
        if service.provider_name() != "chatgpt":
            raise
        context["provider_tool_surface"] = {
            "kind": "unavailable",
            "frozen": True,
            "workbench": str(workbench or ""),
            "reason": str(exc),
        }
    else:
        context["provider_tool_surface"] = turn_surface
    if session_trigger:
        context["session_trigger"] = dict(session_trigger)
    return context


def _consume_context_view_attachment(
    service: CadexService,
    context: Mapping[str, Any],
    dispatch: DocumentThreadDispatch | None,
) -> None:
    """Consume the exact one-shot images already copied into provider context."""

    screenshot = context.get("view_screenshot")
    consume = getattr(service, "consume_view_screenshot_attachment", None)
    if (
        isinstance(screenshot, dict)
        and screenshot.get("captured") is True
        and screenshot.get("pending_attachment") is True
        and callable(consume)
    ):
        frozen = dict(screenshot)
        _on_document_thread(dispatch, lambda: consume(frozen))
    references = context.get("reference_images")
    consume_references = getattr(service, "consume_reference_image_attachments", None)
    if (
        isinstance(references, dict)
        and references.get("images")
        and callable(consume_references)
    ):
        frozen_references = {
            "images": [
                dict(item)
                for item in list(references.get("images") or [])
                if isinstance(item, dict)
            ]
        }
        _on_document_thread(
            dispatch, lambda: consume_references(frozen_references)
        )


def _persist_session_conversation_turn(
    service: CadexService,
    role: str,
    content: str,
    *,
    provider: str | None = None,
    metadata: dict[str, Any] | None = None,
    conversation_id: str | None = None,
    dispatch: DocumentThreadDispatch | None = None,
) -> dict[str, Any]:
    """Persist text off-thread after a document-thread identity capture."""

    prepare = getattr(service, "prepare_conversation_turn", None)
    persist = getattr(service, "persist_prepared_conversation_turn", None)
    accept = getattr(service, "accept_persisted_conversation_turn", None)
    if not all(callable(item) for item in (prepare, persist, accept)):
        raise RuntimeError(
            "The Cadex service does not implement the asynchronous "
            "conversation persistence contract."
        )
    prepared = _on_document_thread(
        dispatch,
        lambda: prepare(
            role,
            content,
            provider=provider,
            metadata=metadata,
            conversation_id=conversation_id,
        ),
    )
    history = persist(prepared)
    _on_document_thread(dispatch, lambda: accept(history, prepared))
    return history


def _load_conversation_history_for_turn(
    service: CadexService,
    conversation_id: str | None,
    current_prompt: str,
    dispatch: DocumentThreadDispatch | None,
) -> list[dict[str, Any]]:
    """Seed cross-message memory: read the persisted transcript off-thread."""

    prepare = getattr(service, "prepare_conversation_read", None)
    read = getattr(service, "read_prepared_conversation", None)
    if not callable(prepare) or not callable(read):
        return []
    try:
        prepared = _on_document_thread(
            dispatch, lambda: prepare(conversation_id)
        )
        conversation = read(prepared)
    except Exception as exc:
        logger.debug("Cadex could not load prior conversation turns: %s", exc)
        return []
    if not isinstance(conversation, list):
        return []
    return _conversation_history_for_provider(conversation, current_prompt)


def _prime_modeling_engine_for_session(
    service: CadexService,
    dispatch: DocumentThreadDispatch | None,
) -> str:
    """Load the project engine without doing manifest I/O in a GUI callback."""

    prepare = getattr(service, "prepare_modeling_engine_read", None)
    complete = getattr(service, "complete_modeling_engine_read", None)
    accept = getattr(service, "accept_modeling_engine_read", None)
    if not all(callable(item) for item in (prepare, complete, accept)):
        return str(_on_document_thread(dispatch, service.modeling_engine))
    prepared = _on_document_thread(dispatch, prepare)
    engine = str(complete(prepared))
    accepted = _on_document_thread(dispatch, lambda: accept(prepared, engine))
    if isinstance(accepted, dict) and accepted.get("accepted") is False:
        raise RuntimeError(
            "The active document changed while Cadex loaded its modeling engine. "
            "Start the request again in the current document."
        )
    return engine


def _provider_state_payload(context: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "workbench",
        "modeling_surface",
        "document",
        "selection",
        "message_geometry_references",
    )
    return {
        key: context[key]
        for key in keys
        if key in context and context[key] not in (None, "", [], {})
    }


def _conversation_history_for_provider(
    conversation: list[dict[str, Any]],
    current_prompt: str,
) -> list[dict[str, Any]]:
    """Bound and normalize prior turns for re-sending to the provider.

    Keeps only user/assistant turns, drops the just-persisted current user
    message (re-sent separately as CURRENT_USER_MESSAGE), enforces strict
    user/assistant alternation starting with a user turn (required by the
    Anthropic wire), and trims to the most recent turns within both a turn
    count and a byte budget so the transcript never blows the context window.
    """

    current = str(current_prompt or "").strip()
    turns: list[dict[str, Any]] = []
    for entry in conversation:
        if not isinstance(entry, dict):
            continue
        role = str(entry.get("role") or "").strip()
        content = str(entry.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        turns.append({"role": role, "content": content})
    # Drop the trailing current user message if it is the last recorded turn.
    if turns and turns[-1]["role"] == "user" and turns[-1]["content"] == current:
        turns.pop()
    # Trim by byte budget from the most recent end.
    budget = MAX_HISTORY_CONTENT_BYTES
    kept_reversed: list[dict[str, Any]] = []
    for turn in reversed(turns):
        cost = len(turn["content"].encode("utf-8"))
        if kept_reversed and budget - cost < 0:
            break
        budget -= cost
        kept_reversed.append(turn)
        if len(kept_reversed) >= MAX_HISTORY_TURNS:
            break
    kept = list(reversed(kept_reversed))
    # Enforce strict alternation starting with a user turn.
    normalized: list[dict[str, Any]] = []
    for turn in kept:
        if not normalized:
            if turn["role"] != "user":
                continue
        elif turn["role"] == normalized[-1]["role"]:
            continue
        normalized.append(turn)
    # The current user message is appended after this history; the transcript
    # must therefore end on an assistant turn (Anthropic rejects user/user).
    if normalized and normalized[-1]["role"] == "user":
        normalized.pop()
    return normalized


def _provider_prompt(
    prompt: str,
    context: dict[str, Any],
    *,
    prompt_section: str = "CURRENT_USER_MESSAGE",
) -> str:
    payload = {"active_state": _provider_state_payload(context)}
    encoded = json.dumps(
        payload, ensure_ascii=True, separators=(",", ":"), default=str
    )
    encoded_bytes = len(encoded.encode("utf-8"))
    if encoded_bytes > MAX_TURN_CONTEXT_JSON_BYTES:
        logger.log(
            _budget_notice_level(),
            "Cadex turn-start context exceeds the %d-byte budget (%d bytes); "
            "sending it anyway.",
            MAX_TURN_CONTEXT_JSON_BYTES,
            encoded_bytes,
        )
    return (
        "CADEX_CONTEXT_JSON\n"
        + encoded
        + "\nEND_CADEX_CONTEXT_JSON\n\n"
        + f"{prompt_section}\n"
        + prompt
    )


def _run_provider(
    provider: BaseProvider,
    prompt: str,
    context: dict[str, Any],
    tool_runner: Callable[[str, str], dict[str, Any]],
    cancellation_check: CancellationCheck | None,
    progress_callback: ProgressCallback | None,
):
    return provider.run(
        prompt,
        context,
        tool_runner=tool_runner,
        cancellation_check=cancellation_check,
        progress_callback=progress_callback,
    )


def _parse_arguments(arguments_json: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(arguments_json or "{}")
    except (TypeError, ValueError) as exc:
        return None, f"Tool arguments are not valid JSON: {exc}"
    if not isinstance(value, dict):
        return None, "Tool arguments must be a JSON object."
    return value, None


def _active_sketch_name(state: dict[str, Any]) -> str:
    sketch = state.get("active_sketch")
    if not isinstance(sketch, dict):
        return ""
    return str(sketch.get("name") or "").strip()


def _edit_mode_block(
    tool: Any,
    state: dict[str, Any],
) -> dict[str, Any] | None:
    edit_mode = (
        "sketch" if state.get("edit_mode") and _active_sketch_name(state) else "none"
    )
    if tool.spec.supports_edit_mode(edit_mode):
        return None
    if edit_mode == "sketch":
        explanation = (
            f"Sketch {_active_sketch_name(state)} is open for editing. Finish or "
            f"verify that sketch, then call sketcher.close_sketch before running "
            f"{tool.name}."
        )
    else:
        explanation = (
            f"{tool.name} requires an open Sketcher edit session. Open the exact "
            "target sketch first."
        )
    return tool_failure(
        tool.name,
        "EDIT_STATE_MISMATCH",
        "edit_state",
        explanation,
        observed={
            "active_edit_mode": edit_mode,
            "active_edit_object": _active_sketch_name(state) or None,
            "allowed_edit_modes": sorted(tool.spec.edit_modes),
            "recovery": (
                "Finish and verify the active sketch, then call sketcher.close_sketch."
                if edit_mode == "sketch"
                else "Open the exact target sketch for editing."
            ),
        },
        allowed_values=sorted(tool.spec.edit_modes),
        required_changes=[
            {
                "action": (
                    "call_sketcher.close_sketch"
                    if edit_mode == "sketch"
                    else "open_target_sketch"
                )
            }
        ],
    )


def _consume_steering(steering_check: SteeringCheck | None) -> list[str]:
    if steering_check is None:
        return []
    values = steering_check() or []
    return [str(value).strip() for value in values if str(value).strip()]


def _emit(progress_callback: ProgressCallback | None, event: dict[str, Any]) -> None:
    if progress_callback is None:
        return
    progress_callback(event)


_TRACE_ITEM_LIMIT = 32
_TRACE_STRING_LIMIT = 1400
_TRACE_DEPTH_LIMIT = 6


def _bounded_trace_value(
    value: Any,
    *,
    path: str,
    depth: int,
    truncated: list[dict[str, Any]],
) -> Any:
    if depth >= _TRACE_DEPTH_LIMIT:
        truncated.append({"path": path, "reason": "depth", "limit": _TRACE_DEPTH_LIMIT})
        return "<truncated>"
    if isinstance(value, str):
        if len(value) <= _TRACE_STRING_LIMIT:
            return value
        truncated.append(
            {
                "path": path,
                "reason": "string_length",
                "original": len(value),
                "limit": _TRACE_STRING_LIMIT,
            }
        )
        return value[: _TRACE_STRING_LIMIT - 3] + "..."
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, dict):
        items = list(value.items())
        if len(items) > _TRACE_ITEM_LIMIT:
            truncated.append(
                {
                    "path": path,
                    "reason": "mapping_items",
                    "original": len(items),
                    "limit": _TRACE_ITEM_LIMIT,
                }
            )
            items = items[:_TRACE_ITEM_LIMIT]
        return {
            str(key): _bounded_trace_value(
                item,
                path=f"{path}.{key}" if path else str(key),
                depth=depth + 1,
                truncated=truncated,
            )
            for key, item in items
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        items = list(value)
        if len(items) > _TRACE_ITEM_LIMIT:
            truncated.append(
                {
                    "path": path,
                    "reason": "sequence_items",
                    "original": len(items),
                    "limit": _TRACE_ITEM_LIMIT,
                }
            )
            items = items[:_TRACE_ITEM_LIMIT]
        return [
            _bounded_trace_value(
                item,
                path=f"{path}[{index}]",
                depth=depth + 1,
                truncated=truncated,
            )
            for index, item in enumerate(items)
        ]
    return _bounded_trace_value(
        repr(value), path=path, depth=depth, truncated=truncated
    )


def _trace_result(payload: dict[str, Any]) -> dict[str, Any]:
    selected = {
        key: value for key, value in payload.items() if value not in (None, "", [], {})
    }
    selected["ok"] = bool(payload.get("ok"))
    truncated: list[dict[str, Any]] = []
    result = _bounded_trace_value(
        selected,
        path="result",
        depth=0,
        truncated=truncated,
    )
    if truncated:
        result["truncation"] = {
            "truncated": True,
            "entries": truncated[:_TRACE_ITEM_LIMIT],
            "entry_count": len(truncated),
        }
    return result


def _run_project_xscript_tool(
    service: CadexService,
    tool_name: str,
    args: dict[str, Any],
    *,
    document_thread_dispatch: DocumentThreadDispatch | None,
    cancellation_check: CancellationCheck | None,
    progress_callback: ProgressCallback | None,
) -> dict[str, Any]:
    """Run one xscript.project.* lifecycle without blocking the document thread.

    Capture and publication run on the document thread; script persistence,
    the sandboxed worker, and result validation run off-thread. A failed
    candidate is recorded on the script store while the previous accepted
    revision stays live.
    """

    from CadexScriptedDomainPublication import publish_project_candidate
    from CadexScriptedRuntime import (
        DomainRuntimeFailure,
        accept_project_candidate,
        capture_project_state,
        describe_project_api,
        execute_candidate,
        parse_project_tool,
        prepare_project_candidate,
        record_project_candidate_failure,
        validate_project_result,
    )

    def candidate_model_state(prepared: Mapping[str, Any]) -> dict[str, Any]:
        # next_write_expected_revision is the durable working revision from
        # the script store (validate_project_result may have re-bound it with
        # the worker-collected parameter specs).
        try:
            from CadexProject import CadexProjectScriptStore

            working = str(
                CadexProjectScriptStore(str(prepared["project_root"]))
                .read_state()
                .get("working_revision")
                or ""
            )
        except Exception:
            working = str(prepared["revision"])
        accepted = str(prepared.get("accepted_revision_before") or "")
        return {
            "status": "working_candidate_not_accepted",
            "program_id": "project",
            "working_revision": working,
            "accepted_revision": accepted,
            "accepted_live_state_preserved": bool(accepted),
            "next_write_expected_revision": working,
            "inspection_call": {
                "tool": "core.inspect",
                "arguments": {
                    "scope": "script",
                    "target": "",
                    "path": "",
                    "offset": 0,
                    "limit": 50,
                    "attach": False,
                },
            },
            "repair_rule": (
                "Inspect the script when the source or latest revision is "
                "uncertain, then repair the smallest exact cause. Use "
                "edit_script for unique targeted replacements, write_script "
                "for a full rewrite, and set_params for value-only parameter "
                "changes."
            ),
        }

    operation = parse_project_tool(tool_name)
    if operation is None:
        return tool_failure(
            tool_name,
            "UNKNOWN_PROJECT_TOOL",
            "surface",
            f"Unknown project XScript tool: {tool_name}.",
            requested=args,
        )
    if operation == "describe_api":
        return describe_project_api()
    prepared = None
    try:
        captured = _on_document_thread(
            document_thread_dispatch,
            lambda: capture_project_state(service, tool_name, args),
        )
        prepared = prepare_project_candidate(captured)
        _emit(
            progress_callback,
            {
                "event": "cadex_domain_worker_started",
                "domain": "project",
                "program_id": "project",
                "revision": prepared["revision"],
            },
        )
        execution = execute_candidate(prepared, cancellation_check=cancellation_check)
        if execution.get("ok") is not True:
            record_project_candidate_failure(prepared, execution)
            execution["model_state"] = candidate_model_state(prepared)
            return execution
        try:
            validated = validate_project_result(prepared, execution)
        except DomainRuntimeFailure as exc:
            record_project_candidate_failure(prepared, exc.payload)
            exc.payload["model_state"] = candidate_model_state(prepared)
            return exc.payload
        except Exception as exc:
            failure = tool_failure(
                tool_name,
                "DOMAIN_RESULT_INVALID",
                "postcondition",
                str(exc),
                requested=args,
                observed={"exception_type": exc.__class__.__name__},
            )
            record_project_candidate_failure(prepared, failure)
            failure["model_state"] = candidate_model_state(prepared)
            return failure
        try:
            publication = _on_document_thread(
                document_thread_dispatch,
                lambda: publish_project_candidate(service, prepared, validated),
            )
        except Exception as exc:
            failure = tool_failure(
                tool_name,
                "DOMAIN_PUBLICATION_FAILED",
                "native_call",
                str(exc),
                requested=args,
                observed={"exception_type": exc.__class__.__name__},
            )
            record_project_candidate_failure(prepared, failure)
            failure["model_state"] = candidate_model_state(prepared)
            return failure
        payload = accept_project_candidate(prepared, publication, validated)
        _schedule_parameters_panel_refresh(document_thread_dispatch)
        _emit(
            progress_callback,
            {
                "event": "xscript_domain_publication_completed",
                "domain": "project",
                "program_id": "project",
                "revision": prepared["revision"],
                "output_count": len(payload.get("outputs") or []),
            },
        )
        return payload
    except DomainRuntimeFailure as exc:
        if prepared is not None:
            try:
                record_project_candidate_failure(prepared, exc.payload)
                exc.payload["model_state"] = candidate_model_state(prepared)
            except Exception:
                pass
        return exc.payload
    except Exception as exc:
        return tool_failure(
            tool_name,
            "DOMAIN_LIFECYCLE_FAILED",
            "external_process",
            str(exc),
            requested=args,
            observed={"exception_type": exc.__class__.__name__},
        )


def run_domain_xscript_operation(
    service: CadexService,
    tool_name: str,
    args: dict[str, Any],
    *,
    document_thread_dispatch: DocumentThreadDispatch | None = None,
    cancellation_check: CancellationCheck | None = None,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Compatibility bridge kept only for CadexParametersPanel (dies in 2.5).

    The per-domain multi-program lifecycle was dissolved by the Phase 2.4
    tool-surface swap (ADR-013), so a per-domain rebuild request now returns a
    structured failure. The panel lists zero per-domain programs on the
    project surface, so this is unreachable in practice; Phase 2.5 rewires
    the panel to the project script's parameters and removes this symbol.
    """

    del service, document_thread_dispatch, cancellation_check, progress_callback
    return tool_failure(
        tool_name,
        "DOMAIN_TOOLS_RETIRED",
        "surface",
        "Per-domain XScript programs were retired; the project script is the "
        "only mutation surface (xscript.project.*).",
        requested=dict(args),
    )


def make_provider_tool_runner(
    service: CadexService,
    *,
    tool_trace: list[dict[str, Any]],
    progress_callback: ProgressCallback | None,
    cancellation_check: CancellationCheck | None,
    steering_check: SteeringCheck | None,
    question_callback: QuestionCallback | None,
    session_trigger: dict[str, Any] | None = None,
    document_thread_dispatch: DocumentThreadDispatch | None = None,
    turn_surface: dict[str, Any] | None = None,
    turn_schemas: list[dict[str, Any]] | None = None,
    turn_modeling_surface: dict[str, Any] | None = None,
):
    frozen_schemas = json.loads(json.dumps(turn_schemas or []))
    frozen_modeling_surface = json.loads(json.dumps(turn_modeling_surface or {}))

    def run(tool_name: str, arguments_json: str = "{}") -> dict[str, Any]:
        started = time.monotonic()
        tool = None
        args: dict[str, Any] = {}

        def finalize(payload: dict[str, Any]) -> dict[str, Any]:
            nonlocal args, tool
            if not bool(payload.get("ok")):
                payload = normalize_tool_failure(tool_name, args, payload)
            elif tool_name != "core.inspect":
                _on_document_thread(
                    document_thread_dispatch,
                    lambda: service.note_provider_tool_targets(args, payload),
                )
            trace_payload = dict(payload)
            trace_payload.pop("_cadex_image_attachment", None)
            trace_result = _trace_result(trace_payload)
            trace = {
                "tool_name": tool_name,
                "arguments": args,
                "safety": tool.safety.value if tool is not None else None,
                "workbench": tool.workbench if tool is not None else None,
                "ok": bool(payload.get("ok")),
                "elapsed_seconds": round(time.monotonic() - started, 4),
                "result": trace_result,
            }
            tool_trace.append(trace)
            _emit(
                progress_callback,
                {
                    "event": "tool_call_completed",
                    "tool_name": tool_name,
                    "ok": bool(payload.get("ok")),
                    "result": trace_result,
                },
            )
            return payload

        if cancellation_check is not None and cancellation_check():
            return finalize(
                tool_failure(
                    tool_name,
                    "RUN_CANCELLED",
                    "precondition",
                    "Cadex run stopped before this tool executed.",
                    requested={"arguments_json": arguments_json},
                    observed={"cancel_requested": True},
                    cancelled=True,
                )
            )
        live_surface = _on_document_thread(
            document_thread_dispatch,
            lambda: _live_provider_surface_state(service),
        )
        active_workbench = live_surface["workbench"]
        runtime_state = live_surface["runtime_state"]
        visible_names = live_surface["tool_names"]
        if isinstance(turn_surface, dict):
            expected_tuple = {
                "workbench": str(turn_surface.get("workbench") or ""),
                "engine": str(turn_surface.get("engine") or ""),
                "surface_id": str(turn_surface.get("surface_id") or ""),
            }
            observed_tuple = {
                "workbench": str(active_workbench or ""),
                "engine": str(live_surface.get("engine") or ""),
                "surface_id": str(live_surface.get("surface_id") or ""),
            }
            if observed_tuple != expected_tuple:
                return finalize(
                    tool_failure(
                        tool_name,
                        "TURN_SURFACE_INVALIDATED",
                        "surface",
                        "The workbench or modeling engine changed after this turn "
                        "started. Start the next turn on the live surface.",
                        requested={"arguments_json": arguments_json},
                        observed={
                            "turn_start": expected_tuple,
                            "live": observed_tuple,
                            "unavailable_reason": live_surface.get("unavailable_reason"),
                        },
                        candidates=visible_names,
                        required_changes=[{"start_next_turn": True}],
                    )
                )
        try:
            tool = service.registry.get(tool_name)
        except KeyError:
            return finalize(
                tool_failure(
                    tool_name,
                    "UNKNOWN_TOOL",
                    "surface",
                    f"Unknown Cadex tool: {tool_name}",
                    requested={"arguments_json": arguments_json},
                    observed={
                        "active_workbench": active_workbench,
                        "active_edit_mode": runtime_state.get("edit_mode"),
                    },
                    candidates=visible_names,
                    required_changes=[{"choose_available_tool": visible_names}],
                )
            )
        if tool_name not in visible_names:
            return finalize(
                tool_failure(
                    tool_name,
                    "TOOL_NOT_ON_ACTIVE_SURFACE",
                    "surface",
                    f"Tool is not in the active provider surface: {tool_name}.",
                    requested={"arguments_json": arguments_json},
                    observed={
                        "active_workbench": active_workbench,
                        "active_edit_mode": runtime_state.get("edit_mode"),
                        "active_edit_object": _active_sketch_name(runtime_state)
                        or None,
                    },
                    candidates=visible_names,
                    required_changes=[{"choose_available_tool": visible_names}],
                )
            )
        args, argument_error = _parse_arguments(arguments_json)
        if argument_error:
            args = {}
            return finalize(
                tool_failure(
                    tool_name,
                    "INVALID_TOOL_ARGUMENTS_JSON",
                    "schema",
                    argument_error,
                    requested={"arguments_json": arguments_json},
                    observed={"expected": "JSON object"},
                    required_changes=[{"provide": "one valid JSON object"}],
                )
            )
        assert args is not None
        try:
            tool.spec.validate_arguments(args)
        except ToolArgumentValidationError as exc:
            return finalize(exc.payload)
        if tool_name == "conversation.ask_user":
            questions = args.get("questions")
            assert isinstance(questions, list) and questions
            if question_callback is None:
                return finalize(
                    tool_failure(
                        tool_name,
                        "QUESTION_UI_UNAVAILABLE",
                        "precondition",
                        "The interactive question UI is unavailable in this session.",
                        requested=args,
                        observed={"question_count": len(questions)},
                    )
                )
            try:
                answers = question_callback(questions)
            except Exception as exc:
                completed_answers = list(getattr(exc, "completed_answers", []) or [])
                return finalize(
                    tool_failure(
                        tool_name,
                        "QUESTION_ROUND_FAILED",
                        "precondition",
                        f"The question round failed: {exc}",
                        requested=args,
                        observed={
                            "question_count": len(questions),
                            "completed_answer_count": len(completed_answers),
                        },
                        completed_answers=completed_answers,
                    )
                )
            payload = {
                "ok": bool(answers),
                "answers": answers,
                "cancelled": not bool(answers),
            }
            if not answers:
                payload = tool_failure(
                    tool_name,
                    "QUESTION_ROUND_CANCELLED",
                    "precondition",
                    "The user cancelled the question round.",
                    requested=args,
                    observed={"question_count": len(questions)},
                    cancelled=True,
                    answers=[],
                )
            return finalize(payload)
        if tool_name == "core.inspect":
            from CadexInspection import capture_inspection, complete_inspection

            if str(args.get("scope") or "") not in {"api", "image"}:
                idle_state = _wait_for_document_idle(
                    service,
                    document_thread_dispatch,
                    cancellation_check,
                    progress_callback,
                )
                if not idle_state.get("ok"):
                    return finalize(
                        _document_idle_failure(tool_name, args, idle_state)
                    )
            try:
                captured = _on_document_thread(
                    document_thread_dispatch,
                    lambda: capture_inspection(service, args),
                )
                return finalize(complete_inspection(captured))
            except Exception as exc:
                return finalize(
                    tool_failure(
                        tool_name,
                        "INSPECTION_CAPTURE_FAILED",
                        "precondition",
                        str(exc),
                        requested=args,
                        observed={"exception_type": exc.__class__.__name__},
                    )
                )
        if tool.spec.requires_document:
            idle_state = _wait_for_document_idle(
                service,
                document_thread_dispatch,
                cancellation_check,
                progress_callback,
            )
            if not idle_state.get("ok"):
                return finalize(_document_idle_failure(tool_name, args, idle_state))
        state_before = _on_document_thread(
            document_thread_dispatch,
            lambda: _minimal_runtime_state(service),
        )
        edit_block = _edit_mode_block(tool, state_before)
        if edit_block is not None:
            edit_block["requested"] = args
            return finalize(edit_block)
        from CadexScriptedRuntime import parse_project_tool

        if parse_project_tool(tool_name) is not None:
            return finalize(
                _run_project_xscript_tool(
                    service,
                    tool_name,
                    args,
                    document_thread_dispatch=document_thread_dispatch,
                    cancellation_check=cancellation_check,
                    progress_callback=progress_callback,
                )
            )
        if tool_name in ISOLATED_GEOMETRY_TOOLS:
            from CadexGeometry import execute_job
            from tool_impl.service.partdesign_measure import (
                cleanup_isolated_measurement,
                finish_isolated_measurement,
                prepare_isolated_measurement,
            )

            prepared = _on_document_thread(
                document_thread_dispatch,
                lambda: prepare_isolated_measurement(service, args["measurement"]),
            )
            if prepared.get("mode") == "immediate":
                return finalize(dict(prepared["payload"]))
            _emit(
                progress_callback,
                {
                    "event": "geometry_worker_started",
                    "operation": "minimum_distance",
                    "input_complexity": prepared.get("input_complexity"),
                },
            )
            try:
                execution = execute_job(
                    prepared["request_path"],
                    prepared["result_path"],
                    cancellation_check=cancellation_check,
                )
                payload = finish_isolated_measurement(prepared, execution)
            finally:
                cleanup_isolated_measurement(prepared)
            return finalize(payload)
        engine_runner = _SCRIPTED_RUNNER_BY_TOOL.get(tool_name)
        if engine_runner is not None:
            return finalize(
                _run_scripted_engine_tool(
                    engine_runner,
                    service,
                    tool_name,
                    args,
                    document_thread_dispatch=document_thread_dispatch,
                    cancellation_check=cancellation_check,
                    progress_callback=progress_callback,
                )
            )
        try:
            raw = _on_document_thread(
                document_thread_dispatch,
                lambda: service.registry.call(tool_name, **args),
            )
            payload = dict(raw) if isinstance(raw, dict) else {"value": raw}
            payload.setdefault("ok", payload.get("error") in (None, ""))
        except ToolArgumentValidationError as exc:
            payload = exc.payload
        except Exception as exc:
            payload = tool_failure(
                tool_name,
                "TOOL_HANDLER_EXCEPTION",
                "native_call",
                str(exc),
                requested=args,
                observed={"exception_type": exc.__class__.__name__},
            )
        try:
            steering = _consume_steering(steering_check)
        except Exception as exc:
            steering = []
            payload["human_steering_error"] = str(exc)
        if steering:
            payload["human_steering"] = steering
            _emit(
                progress_callback,
                {"event": "human_steering_consumed", "message_count": len(steering)},
            )
        return finalize(payload)

    def provider_update() -> dict[str, Any]:
        refreshed = _on_document_thread(
            document_thread_dispatch,
            lambda: _context_for_provider(service, session_trigger),
        )
        completed = refreshed
        _consume_context_view_attachment(
            service, completed, document_thread_dispatch
        )
        if not isinstance(turn_surface, dict):
            return completed

        live_surface = dict(completed.get("provider_tool_surface") or {})
        expected_tuple = (
            str(turn_surface.get("workbench") or ""),
            str(turn_surface.get("engine") or ""),
            str(turn_surface.get("surface_id") or ""),
        )
        live_tuple = (
            str(live_surface.get("workbench") or ""),
            str(live_surface.get("engine") or ""),
            str(live_surface.get("surface_id") or ""),
        )
        completed["provider_tool_surface"] = dict(turn_surface)
        completed["provider_tool_schemas"] = json.loads(json.dumps(frozen_schemas))
        completed["workbench"] = str(turn_surface.get("workbench") or "") or None
        if frozen_modeling_surface:
            completed["modeling_surface"] = json.loads(
                json.dumps(frozen_modeling_surface)
            )
        if live_tuple != expected_tuple:
            # Never inject the next workbench/domain into an in-flight turn.
            # Calls remain authorized against the frozen tuple and will return
            # TURN_SURFACE_INVALIDATED until the human starts the next turn.
            for key in (
                "partdesign",
                "xscript",
                "xscript_domain",
                "xscript",
                "xscript_domain",
                "sketcher",
                "part",
                "assembly",
                "surface",
                "draft",
                "techdraw",
                "cam",
                "fem",
                "material",
                "mesh",
                "meshpart",
                "points",
                "spreadsheet",
                "bim",
                "inspection",
                "robot",
                "reverse_engineering",
            ):
                completed.pop(key, None)
            completed["modeling_surface"] = {
                **dict(completed.get("modeling_surface") or {}),
                "invalidated": True,
                "live_tuple": {
                    "workbench": live_tuple[0],
                    "engine": live_tuple[1],
                    "surface_id": live_tuple[2],
                },
                "next_turn_required": True,
            }
        return completed

    run.provider_update = provider_update
    return run


def _run_session_turn(
    prompt: str,
    *,
    service: CadexService | None,
    prefer_online: bool,
    provider: BaseProvider | None,
    progress_callback: ProgressCallback | None,
    cancellation_check: CancellationCheck | None,
    steering_check: SteeringCheck | None,
    question_callback: QuestionCallback | None,
    session_trigger: dict[str, Any] | None,
    persist_input_as_user: bool,
    prompt_section: str,
    document_thread_dispatch: DocumentThreadDispatch | None,
) -> CadexResponse:
    clean_prompt = str(prompt or "").strip()
    if not clean_prompt:
        raise ValueError("Prompt cannot be empty.")
    active_service = service or _on_document_thread(
        document_thread_dispatch,
        get_service,
    )
    persistence = _on_document_thread(
        document_thread_dispatch,
        active_service.document_persistence_state,
    )
    if not persistence.get("enabled"):
        raise RuntimeError(
            str(
                persistence.get("message")
                or "Save the active document to enable Cadex."
            )
        )
    # Prime the manifest engine for the session (side effect); the scripted
    # engines author on every workbench, so there is no per-engine preflight.
    _prime_modeling_engine_for_session(
        active_service,
        document_thread_dispatch,
    )
    turn_conversation_id: str | None = None
    if persist_input_as_user:
        recorded = _persist_session_conversation_turn(
            active_service,
            "user",
            clean_prompt,
            dispatch=document_thread_dispatch,
        )
        turn_conversation_id = str(recorded.get("conversation_id") or "") or None
    _emit(progress_callback, {"event": "context_build_started"})
    context = _on_document_thread(
        document_thread_dispatch,
        lambda: _context_for_provider(active_service, session_trigger),
    )
    _consume_context_view_attachment(
        active_service, context, document_thread_dispatch
    )
    context["conversation_history"] = _load_conversation_history_for_turn(
        active_service,
        turn_conversation_id,
        clean_prompt,
        document_thread_dispatch,
    )
    # Threaded to the provider subprocess so its budget notices can be demoted
    # there too (the subprocess cannot see GUI experimental-mode state).
    context["_experimental_mode"] = _experimental_mode_session()
    tool_trace: list[dict[str, Any]] = []
    _emit(
        progress_callback,
        {
            "event": "context_build_completed",
            "workbench": context.get("workbench"),
            "provider_tool_count": len(context.get("provider_tool_schemas") or []),
        },
    )
    active_provider = provider or _on_document_thread(
        document_thread_dispatch,
        lambda: choose_provider(
            active_service,
            prefer_online=prefer_online,
        ),
    )
    provider_name = active_provider.__class__.__name__
    tool_runner = make_provider_tool_runner(
        active_service,
        tool_trace=tool_trace,
        progress_callback=progress_callback,
        cancellation_check=cancellation_check,
        steering_check=steering_check,
        question_callback=question_callback,
        session_trigger=session_trigger,
        document_thread_dispatch=document_thread_dispatch,
        turn_surface=(
            dict(context["provider_tool_surface"])
            if isinstance(context.get("provider_tool_surface"), dict)
            and context["provider_tool_surface"].get("kind") == "turn_start_snapshot"
            else None
        ),
        turn_schemas=[
            dict(schema)
            for schema in list(context.get("provider_tool_schemas") or [])
            if isinstance(schema, dict)
        ],
        turn_modeling_surface=(
            dict(context["modeling_surface"])
            if isinstance(context.get("modeling_surface"), dict)
            else None
        ),
    )
    _emit(
        progress_callback,
        {"event": "provider_turn_started", "provider": provider_name, "turn": 1},
    )
    try:
        result = _run_provider(
            active_provider,
            _provider_prompt(
                clean_prompt,
                context,
                prompt_section=prompt_section,
            ),
            context,
            tool_runner,
            cancellation_check,
            progress_callback,
        )
        final_output = str(result.final_output or "").strip()
        if final_output:
            _persist_session_conversation_turn(
                active_service,
                "assistant",
                final_output,
                provider=provider_name,
                metadata={"session_trigger": session_trigger}
                if session_trigger
                else None,
                conversation_id=turn_conversation_id,
                dispatch=document_thread_dispatch,
            )
            _emit(
                progress_callback,
                {
                    "event": "provider_turn_output",
                    "provider": provider_name,
                    "turn": 1,
                    "text": final_output,
                },
            )
        final_context = _on_document_thread(
            document_thread_dispatch,
            lambda: _context_for_provider(active_service, session_trigger),
        )
        _emit(
            progress_callback,
            {
                "event": "provider_turn_completed",
                "provider": provider_name,
                "turn": 1,
                "tool_count": len(tool_trace),
            },
        )
        return CadexResponse(
            provider=provider_name,
            final_output=final_output,
            context=final_context,
            tool_trace=tool_trace,
        )
    except ProviderUnavailable as exc:
        provider_error = str(exc)
        final_output = f"{provider_name} failed before returning a usable AI result: {provider_error}"
        _emit(
            progress_callback,
            {
                "event": "provider_turn_failed",
                "provider": provider_name,
                "turn": 1,
                "error": str(exc),
                "tool_count": len(tool_trace),
            },
        )
        failed_context = _on_document_thread(
            document_thread_dispatch,
            lambda: _context_for_provider(active_service, session_trigger),
        )
        return CadexResponse(
            provider=provider_name,
            final_output=final_output,
            context=failed_context,
            tool_trace=tool_trace,
            error=str(exc),
        )


def run_prompt(
    prompt: str,
    service: CadexService | None = None,
    prefer_online: bool = True,
    provider: BaseProvider | None = None,
    progress_callback: ProgressCallback | None = None,
    cancellation_check: CancellationCheck | None = None,
    steering_check: SteeringCheck | None = None,
    question_callback: QuestionCallback | None = None,
    document_thread_dispatch: DocumentThreadDispatch | None = None,
) -> CadexResponse:
    return _run_session_turn(
        prompt,
        service=service,
        prefer_online=prefer_online,
        provider=provider,
        progress_callback=progress_callback,
        cancellation_check=cancellation_check,
        steering_check=steering_check,
        question_callback=question_callback,
        session_trigger=None,
        persist_input_as_user=True,
        prompt_section="CURRENT_USER_MESSAGE",
        document_thread_dispatch=document_thread_dispatch,
    )


def run_sketch_close_continuation(
    event: dict[str, Any],
    service: CadexService | None = None,
    prefer_online: bool = True,
    provider: BaseProvider | None = None,
    progress_callback: ProgressCallback | None = None,
    cancellation_check: CancellationCheck | None = None,
    steering_check: SteeringCheck | None = None,
    question_callback: QuestionCallback | None = None,
    document_thread_dispatch: DocumentThreadDispatch | None = None,
) -> CadexResponse:
    if not isinstance(event, dict):
        raise ValueError("Sketch-close continuation event must be an object.")
    expected_fields = {
        "type",
        "document_uid",
        "document_name",
        "sketch_name",
        "sketch_label",
        "owner_body",
    }
    if set(event) != expected_fields:
        raise ValueError(
            "Sketch-close continuation event requires exactly: "
            + ", ".join(sorted(expected_fields))
            + "."
        )
    if str(event.get("type") or "").strip() != "human_closed_sketch":
        raise ValueError(
            "Sketch-close continuation event type must be human_closed_sketch."
        )
    clean_event = {
        "type": "human_closed_sketch",
        "document_uid": str(event.get("document_uid") or "").strip(),
        "document_name": str(event.get("document_name") or "").strip(),
        "sketch_name": str(event.get("sketch_name") or "").strip(),
        "sketch_label": str(event.get("sketch_label") or "").strip(),
        "owner_body": str(event.get("owner_body") or "").strip(),
    }
    missing = [
        key
        for key in ("document_uid", "document_name", "sketch_name", "owner_body")
        if not clean_event[key]
    ]
    if missing:
        raise ValueError(
            "Sketch-close continuation event is missing: " + ", ".join(missing) + "."
        )
    prompt = (
        f"The human closed sketch {clean_event['sketch_name']} "
        f"({clean_event['sketch_label'] or clean_event['sketch_name']}) in Body "
        f"{clean_event['owner_body']}. Continue the existing CAD obligation from the "
        "current post-edit document state. Closing the sketch is a handoff to continue, "
        "not proof that the sketch is valid or permission to skip verification. Inspect "
        "its current readiness and native errors before choosing the next operation. Do "
        "not restart requirement refinement or restate the accepted design."
    )
    return _run_session_turn(
        prompt,
        service=service,
        prefer_online=prefer_online,
        provider=provider,
        progress_callback=progress_callback,
        cancellation_check=cancellation_check,
        steering_check=steering_check,
        question_callback=question_callback,
        session_trigger=clean_event,
        persist_input_as_user=False,
        prompt_section="CURRENT_SESSION_EVENT",
        document_thread_dispatch=document_thread_dispatch,
    )


def _format_document_delta(delta: Any) -> str:
    if not isinstance(delta, dict):
        return ""
    added = delta.get("added") or []
    removed = delta.get("removed") or []
    changed = delta.get("changed") or []
    parts: list[str] = []
    if added:
        parts.append(f"+{len(added)} objects")
    if removed:
        parts.append(f"-{len(removed)} objects")
    if changed:
        parts.append(f"{len(changed)} changed")
    return ", ".join(parts)
