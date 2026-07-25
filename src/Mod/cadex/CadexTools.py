# SPDX-License-Identifier: LGPL-2.1-or-later

"""Authoritative Cadex tool contracts: stages, envelopes, declarations.

What survives Phase 7 (ADR-021): the failure vocabulary (FAILURE_STAGES),
the ``tool_failure`` envelope every engine refusal is shaped as and every
shell parses, ``unchanged_state``, and ``ToolSpec`` as a declaration of the
engine's tool surface. The runtime registry and JSON-schema argument
validation died with the provider stack that used them -- and with them
this repository's last third-party Python dependency.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping



class SafetyLevel(str, Enum):
    READ = "read"
    VIEW = "view"
    SAFE_WRITE = "safe_write"
    WRITE = "write"
    DESTRUCTIVE = "destructive"
    EXTERNAL = "external"
    DEVELOPER = "developer"


EDIT_MODE_NONE = "none"
EDIT_MODE_SKETCH = "sketch"
VALID_EDIT_MODES = frozenset({EDIT_MODE_NONE, EDIT_MODE_SKETCH})
FAILURE_STAGES = frozenset(
    {
        "schema",
        "surface",
        "edit_state",
        "precondition",
        "native_call",
        "native_recompute",
        "postcondition",
        "external_process",
    }
)


def unchanged_state() -> dict[str, Any]:
    return {
        "transaction_opened": False,
        "mutation_started": False,
        "commit_attempted": False,
        "commit_succeeded": False,
        "document_changed": False,
        "changed": False,
        "retained": False,
        "created_objects": [],
        "changed_objects": [],
        "deleted_objects": [],
        "repair_targets": [],
    }


def tool_failure(
    tool: str,
    failure_code: str,
    failure_stage: str,
    error: str,
    *,
    requested: Any = None,
    normalized: Any = None,
    observed: Any = None,
    candidates: Any = None,
    allowed_values: Any = None,
    state_change: Mapping[str, Any] | None = None,
    native_diagnostics: Any = None,
    retry_same_call: bool = False,
    required_changes: list[Any] | None = None,
    **details: Any,
) -> dict[str, Any]:
    """Build the single provider-visible contract for a rejected tool call."""
    stage = str(failure_stage or "").strip()
    if stage not in FAILURE_STAGES:
        raise ValueError(f"Unknown Cadex tool failure stage: {stage!r}")
    change = unchanged_state()
    if state_change is not None:
        change.update(dict(state_change))
    response: dict[str, Any] = {
        "ok": False,
        "tool": str(tool or "").strip(),
        "failure_code": str(failure_code or "TOOL_EXECUTION_FAILED").strip(),
        "failure_stage": stage,
        "requested": {} if requested is None else requested,
        "normalized": {} if normalized is None else normalized,
        "observed": {} if observed is None else observed,
        "candidates": [] if candidates is None else candidates,
        "allowed_values": [] if allowed_values is None else allowed_values,
        "state_change": change,
        "native_diagnostics": [] if native_diagnostics is None else native_diagnostics,
        "retry": {
            "same_call": bool(retry_same_call),
            "required_changes": list(required_changes or []),
        },
        "error": str(error or "Tool call failed."),
    }
    response.update(details)
    return response


def normalize_tool_failure(
    tool: str,
    requested: Mapping[str, Any] | None,
    payload: Mapping[str, Any],
    *,
    default_stage: str = "native_call",
) -> dict[str, Any]:
    """Enforce the failure contract without interpreting human-readable text."""
    raw = dict(payload)
    stage = str(raw.get("failure_stage") or default_stage)
    if stage not in FAILURE_STAGES:
        stage = default_stage
    document_delta = raw.get("document_delta")
    change = raw.get("state_change")
    if not isinstance(change, Mapping):
        delta = document_delta if isinstance(document_delta, Mapping) else {}
        created = list(delta.get("created_objects") or [])
        changed = list(delta.get("changed_objects") or [])
        deleted = list(delta.get("deleted_objects") or [])
        document_changed = bool(created or changed or deleted)
        change = {
            "transaction_opened": bool(raw.get("transaction_opened")),
            "mutation_started": bool(raw.get("mutation_started") or document_changed),
            "commit_attempted": bool(raw.get("commit_attempted")),
            "commit_succeeded": bool(raw.get("commit_succeeded")),
            "document_changed": document_changed,
            "changed": document_changed,
            "retained": document_changed,
            "created_objects": created,
            "changed_objects": changed,
            "deleted_objects": deleted,
            "repair_targets": list(raw.get("repair_targets") or []),
        }
    retry = raw.get("retry")
    if not isinstance(retry, Mapping):
        retry = {
            "same_call": bool(raw.get("retry_same_call", False)),
            "required_changes": list(raw.get("required_changes") or []),
        }
    native_diagnostics = raw.get("native_diagnostics")
    if native_diagnostics is None:
        native_diagnostics = []
    observed = raw.get("observed", {})
    if not isinstance(observed, Mapping):
        observed = {"raw_observed": observed}
    else:
        observed = dict(observed)
    reserved_input = {
        "ok",
        "tool",
        "failure_code",
        "failure_stage",
        "error",
        "requested",
        "normalized",
        "observed",
        "candidates",
        "allowed_values",
        "state_change",
        "native_diagnostics",
        "retry",
        "retry_same_call",
        "required_changes",
        "document_delta",
        "transaction_opened",
        "mutation_started",
        "commit_attempted",
        "commit_succeeded",
        "repair_targets",
    }
    tool_details = {
        key: value for key, value in raw.items() if key not in reserved_input
    }
    if tool_details:
        observed["tool_details"] = tool_details
    return tool_failure(
        tool,
        str(raw.get("failure_code") or "TOOL_EXECUTION_FAILED"),
        stage,
        str(raw.get("error") or "Tool call failed."),
        requested=raw.get("requested", dict(requested or {})),
        normalized=raw.get("normalized", {}),
        observed=observed,
        candidates=raw.get("candidates", []),
        allowed_values=raw.get("allowed_values", []),
        state_change=change,
        native_diagnostics=native_diagnostics,
        retry_same_call=bool(retry.get("same_call", False)),
        required_changes=list(retry.get("required_changes") or []),
    )



@dataclass(frozen=True)
class ToolSpec:
    """One declared operation on the engine's tool surface.

    Phase 7 (ADR-021) removed the provider stack that dispatched these, so a
    ToolSpec is now a *declaration* — the shape the guardrail tests pin —
    rather than a call target. JSON-schema validation of arguments went with
    the provider: the engine validates in the pipeline, against the real
    xscript surface, and jsonschema was this repository's last third-party
    Python dependency.
    """

    name: str
    description: str
    parameters: dict[str, Any]
    safety: SafetyLevel
    workbench: str | None
    contextual: bool
    requires_document: bool
    edit_modes: frozenset[str]
    provider_visible: bool

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "ToolSpec":
        name = str(raw.get("name") or "").strip()
        if not name or "." not in name:
            raise ValueError(f"Invalid Cadex tool name: {name!r}")
        tool_description = str(raw.get("description") or "").strip()
        if len(tool_description) < 24:
            raise ValueError(
                f"Tool {name} needs a concrete provider description, not a label."
            )
        parameters = deepcopy(raw.get("parameters"))
        if not isinstance(parameters, dict) or parameters.get("type") != "object":
            raise ValueError(f"Tool {name} parameters must be a JSON object schema.")
        properties = parameters.get("properties")
        if not isinstance(properties, dict):
            raise ValueError(f"Tool {name} parameter schema needs properties.")
        for argument_name, argument_schema in properties.items():
            parameter_description = (
                str(argument_schema.get("description") or "").strip()
                if isinstance(argument_schema, Mapping)
                else ""
            )
            if not parameter_description:
                raise ValueError(
                    f"Tool {name} parameter {argument_name!r} needs a direct "
                    "provider description."
                )
        if not isinstance(parameters.get("properties"), dict):
            raise ValueError(f"Tool {name} parameter schema needs properties.")
        safety_name = str(raw.get("safety") or "READ").strip().upper()
        try:
            safety = SafetyLevel[safety_name]
        except KeyError as exc:
            raise ValueError(
                f"Tool {name} has unknown safety {safety_name!r}."
            ) from exc
        workbench = str(raw.get("workbench") or "").strip() or None
        contextual = bool(raw.get("contextual", False))
        requires_document = bool(
            raw.get(
                "requires_document",
                bool(workbench)
                or safety in {SafetyLevel.SAFE_WRITE, SafetyLevel.WRITE},
            )
        )
        raw_modes = raw.get("edit_modes")
        if raw_modes is None:
            if safety in {SafetyLevel.READ, SafetyLevel.VIEW}:
                modes = set(VALID_EDIT_MODES)
            elif workbench == "SketcherWorkbench":
                modes = {EDIT_MODE_SKETCH}
            else:
                modes = {EDIT_MODE_NONE}
        else:
            if not isinstance(raw_modes, (list, tuple, set, frozenset)):
                raise ValueError(f"Tool {name} edit_modes must be a list of modes.")
            modes = {str(item).strip() for item in raw_modes}
        unknown_modes = modes - VALID_EDIT_MODES
        if unknown_modes:
            raise ValueError(
                f"Tool {name} has unknown edit modes: {sorted(unknown_modes)}."
            )
        if not modes:
            raise ValueError(f"Tool {name} must allow at least one edit mode.")
        return cls(
            name=name,
            description=tool_description,
            parameters=parameters,
            safety=safety,
            workbench=workbench,
            contextual=contextual,
            requires_document=requires_document,
            edit_modes=frozenset(modes),
            provider_visible=bool(raw.get("provider_visible", True)),
        )

    def supports_edit_mode(self, edit_mode: str) -> bool:
        return str(edit_mode or EDIT_MODE_NONE) in self.edit_modes
