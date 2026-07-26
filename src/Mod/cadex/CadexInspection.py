# SPDX-License-Identifier: LGPL-2.1-or-later

"""Deterministic, bounded inspection for the active modeling surface."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any

from CadexModelingSurface import resolve_service_surface


MAX_INSPECT_RESULT_BYTES = 32 * 1024
_PREVIEW_BYTES = 1024
_PROPERTY_SEQUENCE_LIMIT = 256
_HEAVY_PROPERTIES = frozenset({"Mesh", "Points", "Proxy", "Shape", "ViewObject"})


def _surface_summary(resolution: Any) -> dict[str, Any]:
    result = {
        "workbench": str(resolution.workbench or ""),
        "engine": str(resolution.engine or ""),
        "domain": resolution.domain,
        "surface_id": str(resolution.surface_id or ""),
        "available": bool(resolution.available),
    }
    if not resolution.available:
        result["unavailable_reason"] = str(resolution.unavailable_reason or "")
    return result


def _identity(obj: Any) -> dict[str, Any]:
    return {
        "name": str(getattr(obj, "Name", "") or ""),
        "label": str(getattr(obj, "Label", "") or ""),
        "type": str(getattr(obj, "TypeId", "") or type(obj).__name__),
    }


def _document_identity(doc: Any) -> dict[str, Any]:
    if doc is None:
        return {"name": None, "uid": None, "object_count": 0}
    return {
        "name": str(getattr(doc, "Name", "") or ""),
        "uid": str(getattr(doc, "Uid", "") or ""),
        "object_count": len(getattr(doc, "Objects", []) or []),
    }


def _stable_value(value: Any, *, depth: int = 0) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if depth >= 5:
        return {"omitted": True, "reason": "value_depth", "type": type(value).__name__}
    if hasattr(value, "Name") and hasattr(value, "TypeId"):
        return _identity(value)
    if isinstance(value, Mapping):
        items = list(value.items())
        result = {
            str(key): _stable_value(item, depth=depth + 1)
            for key, item in items[:_PROPERTY_SEQUENCE_LIMIT]
        }
        if len(items) > _PROPERTY_SEQUENCE_LIMIT:
            result["_items_omitted"] = len(items) - _PROPERTY_SEQUENCE_LIMIT
        return result
    if isinstance(value, (list, tuple)):
        values = list(value)
        result = [
            _stable_value(item, depth=depth + 1)
            for item in values[:_PROPERTY_SEQUENCE_LIMIT]
        ]
        if len(values) > _PROPERTY_SEQUENCE_LIMIT:
            result.append({"items_omitted": len(values) - _PROPERTY_SEQUENCE_LIMIT})
        return result
    if all(hasattr(value, axis) for axis in ("x", "y", "z")):
        try:
            return {
                "x": float(value.x),
                "y": float(value.y),
                "z": float(value.z),
            }
        except Exception:
            pass
    quantity_value = getattr(value, "Value", None)
    quantity_unit = getattr(value, "Unit", None)
    if isinstance(quantity_value, (int, float)) and quantity_unit is not None:
        return {"value": float(quantity_value), "unit": str(quantity_unit)}
    text = str(value)
    if len(text) <= 2048:
        return text
    return {
        "omitted": True,
        "reason": "value_text_size",
        "characters": len(text),
        "utf8_bytes": len(text.encode("utf-8", errors="replace")),
        "type": type(value).__name__,
    }


def _object_detail(obj: Any) -> dict[str, Any]:
    result = _identity(obj)
    properties = list(getattr(obj, "PropertiesList", []) or [])
    captured: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for raw_name in properties:
        name = str(raw_name)
        if name in _HEAVY_PROPERTIES:
            captured[name] = {
                "omitted": True,
                "reason": "heavy_native_property",
                "property_type": str(
                    getattr(obj, "getTypeIdOfProperty", lambda _name: "")(name) or ""
                ),
            }
            continue
        try:
            value = getattr(obj, name)
            captured[name] = {
                "property_type": str(
                    getattr(obj, "getTypeIdOfProperty", lambda _name: "")(name) or ""
                ),
                "group": str(
                    getattr(obj, "getGroupOfProperty", lambda _name: "")(name) or ""
                ),
                "value": _stable_value(value),
            }
        except Exception as exc:
            errors[name] = f"{type(exc).__name__}: {exc}"
    result["property_count"] = len(properties)
    result["properties"] = captured
    if errors:
        result["property_errors"] = errors
    return result


def _edit_object() -> None:
    """Always None: interactive edit state was a Qt shell concept.

    The engine's document is cadexd's ephemeral one — nothing is ever "in
    edit" in it, because no user interacts with it. Kept as a field of the
    document inspection so the payload shape does not change for clients
    (ADR-021).
    """

    return None


def capture_inspection(service: Any, arguments: Mapping[str, Any]) -> dict[str, Any]:
    """Capture only document-affine state; artifact reads happen in complete()."""

    scope = str(arguments.get("scope") or "")
    target = str(arguments.get("target") or "")
    path = str(arguments.get("path") or "")
    offset = int(arguments.get("offset") or 0)
    limit = int(arguments.get("limit") or 20)
    attach = bool(arguments.get("attach", False))
    if offset < 0 or offset > 100000000:
        raise ValueError("offset must be between 0 and 100000000.")
    if limit < 1 or limit > 50:
        raise ValueError("limit must be between 1 and 50.")
    if len(target) > 512 or len(path) > 512:
        raise ValueError("target and path are each limited to 512 characters.")
    if attach and scope != "image":
        raise ValueError("attach=true is valid only for image scope.")
    if scope == "object" and not target:
        raise ValueError(f"{scope} scope requires an exact target.")
    if scope == "image" and attach and not target:
        raise ValueError("image scope requires an exact target when attach=true.")
    workbench = service.active_workbench_name()
    resolution = resolve_service_surface(service, workbench)
    doc = service._active_document()
    common = {
        "scope": scope,
        "target": target,
        "path": path,
        "offset": offset,
        "limit": limit,
        "attach": attach,
        "surface": _surface_summary(resolution),
        "document": _document_identity(doc),
    }
    if scope == "document":
        objects = (getattr(doc, "Objects", []) or []) if doc is not None else []
        if path == "/objects":
            total = len(objects)
            end = min(offset + limit, total)
            values = [_identity(objects[index]) for index in range(offset, end)]
            return {
                **common,
                "kind": "document_objects_page",
                "values": values,
                "total": total,
            }
        if path.startswith("/objects/"):
            raise ValueError(
                "Inspect /objects as a page, then use object scope with the exact "
                "returned internal name."
            )
        raw = {
            **common["document"],
            "edit_object": _edit_object(),
            "objects": {
                "type": "array",
                "item_count": len(objects),
                "inspect_path": "/objects",
            },
        }
        return {**common, "kind": "captured", "raw": raw}
    if scope == "object":
        if doc is None:
            raise ValueError("No active document.")
        obj = doc.getObject(target) if target else None
        if obj is None:
            raise ValueError(f"Object not found by exact internal name: {target!r}.")
        return {**common, "kind": "captured", "raw": _object_detail(obj)}
    if scope == "script":
        # THE project script: source text, parameter specs/values, revisions,
        # accepted contract/digest, latest candidate. Artifact reads happen in
        # complete_inspection, off the document thread.
        return {
            **common,
            "kind": "script",
            "project_root": str(service.project_scope_snapshot().get("root") or ""),
        }
    if scope == "api":
        schemas = [
            service.registry.get(name).to_schema(active_workbench=workbench)
            for name in resolution.tool_names
            if name in service.registry.names()
        ]
        return {**common, "kind": "api", "schemas": schemas}
    if scope == "image":
        return {
            **common,
            "kind": "image",
            "project_root": str(service.project_scope_snapshot().get("root") or ""),
        }
    if scope == "assets":
        # What ``mesh.import_file`` can name. Store-backed like image scope,
        # so the walk happens in complete_inspection, off the document thread.
        return {
            **common,
            "kind": "assets",
            "project_root": str(service.project_scope_snapshot().get("root") or ""),
        }
    if scope == "output":
        # The accepted revision's per-output facts, read from the pinned
        # attempt directory rather than from the run that produced them.
        return {
            **common,
            "kind": "output",
            "project_root": str(service.project_scope_snapshot().get("root") or ""),
        }
    if scope == "history":
        # The undo trail (ADR-045): every accepted revision's source, newest
        # last. Store-backed, so the read happens off the document thread.
        # With no target it lists; with one it serves that version's source.
        return {
            **common,
            "kind": "history",
            "project_root": str(service.project_scope_snapshot().get("root") or ""),
        }
    raise ValueError(f"Unknown core.inspect scope: {scope!r}.")


def _complete_api(captured: Mapping[str, Any]) -> Any:
    surface = captured["surface"]
    if str(surface.get("engine") or "") != "xscript":
        return {"surface": surface, "tools": list(captured.get("schemas") or [])}
    from CadexScriptedRuntime import describe_project_api

    return describe_project_api()


def _complete_script(captured: Mapping[str, Any]) -> Any:
    """Read THE project script's persisted state; paged by _bounded_page."""

    root = str(captured.get("project_root") or "")
    if not root:
        return {
            "ok": False,
            "error": "The active document has no durable Cadex project root.",
        }
    from CadexScriptStore import CadexProjectScriptStore

    store = CadexProjectScriptStore(root)
    state = store.read_state()
    source = store.read_source()
    return {
        "script_present": bool(source),
        "source": source,
        "source_characters": len(source),
        "params": {
            "specs": list(state.get("param_specs") or []),
            "values": dict(state.get("param_values") or {}),
        },
        "revisions": {
            "working_revision": str(state.get("working_revision") or ""),
            "accepted_revision": str(state.get("accepted_revision") or ""),
        },
        "accepted": {
            "contract": state.get("accepted_contract"),
            "digest": str(state.get("accepted_digest") or ""),
        },
        "latest_candidate": state.get("latest_candidate"),
        "updated_at": str(state.get("updated_at") or ""),
    }


def _complete_image(captured: Mapping[str, Any]) -> tuple[Any, dict[str, Any] | None]:
    root = Path(str(captured.get("project_root") or ""))
    state_path = root / "references.json"
    entries: list[dict[str, Any]] = []
    if state_path.is_file():
        data = json.loads(state_path.read_text(encoding="utf-8"))
        raw = data.get("reference_images") if isinstance(data, dict) else None
        if isinstance(raw, list):
            entries = [dict(item) for item in raw if isinstance(item, dict)]
    target = str(captured.get("target") or "")
    if not target:
        return {
            "image_count": len(entries),
            "images": [
                {key: item.get(key) for key in ("id", "name", "label", "format", "image_size")}
                for item in entries
            ],
        }, None
    selected = next(
        (
            item
            for item in entries
            if str(item.get("id") or "") == target
            or str(item.get("name") or "") == target
        ),
        None,
    )
    if selected is None:
        return {"ok": False, "error": f"No reference image matches {target!r}."}, None
    public = {
        key: selected.get(key)
        for key in ("id", "name", "label", "format", "size_bytes", "image_size", "attached_at")
        if selected.get(key) not in (None, "", [], {})
    }
    if not captured.get("attach"):
        return {"ok": True, "image": public, "attached": False}, None
    path = Path(str(selected.get("path") or ""))
    allowed_root = (root / "references").resolve()
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(allowed_root)
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": f"Reference image artifact is unavailable: {exc}"}, None
    if not resolved.is_file():
        return {"ok": False, "error": "Reference image artifact is not a file."}, None
    return (
        {"ok": True, "image": public, "attached": True},
        {"path": str(resolved), "name": str(selected.get("name") or target)},
    )


def _complete_assets(captured: Mapping[str, Any]) -> Any:
    """The project's importable mesh assets — how the agent discovers them."""

    root = str(captured.get("project_root") or "")
    if not root:
        return {
            "ok": False,
            "error": "The active document has no durable Cadex project root.",
        }
    from CadexScriptedRuntime import list_project_assets

    entries = list_project_assets(root)
    return {
        "asset_count": len(entries),
        "assets": entries,
        "note": (
            "Names here are what mesh.import_file() takes. Add one with the "
            "shell's File > Import Geometry, or the import_geometry tool."
        ),
    }


def _complete_history(captured: Mapping[str, Any]) -> Any:
    """The project's accepted-revision history — the undo trail (ADR-045).

    No target lists it, newest last. A target selects one version by ordinal
    or revision prefix and serves that version's source, which is what a
    revert reads before writing it back.
    """

    root = str(captured.get("project_root") or "")
    if not root:
        return {
            "ok": False,
            "error": "The active document has no durable Cadex project root.",
        }
    from CadexScriptStore import CadexProjectScriptStore

    store = CadexProjectScriptStore(root)
    target = str(captured.get("target") or "").strip()
    if target:
        source = store.read_history_source(target)
        if not source:
            return {
                "ok": False,
                "error": (
                    "No stored version matches {!r}. Inspect scope=history "
                    "with no target for the list.".format(target)
                ),
            }
        return {"selector": target, "source": source, "characters": len(source)}

    entries = store.read_history()
    return {
        "version_count": len(entries),
        "versions": entries,
        "note": (
            "Every accepted revision, oldest first. Inspect one with "
            "target=<ordinal|revision>; write it back with write_script to "
            "revert (replace=true if it drops outputs you have now)."
        ),
    }


#: Per-output detail the worker already computed, in the order an agent
#: reading a page wants it. Absent keys are simply not reported.
_OUTPUT_DETAIL_KEYS = (
    "name",
    "type",
    "domain",
    "artifact_kind",
    "facts",
    "mesh_data",
    "operation_diagnostics",
)


def _complete_output(captured: Mapping[str, Any]) -> Any:
    """Facts for any output of the *accepted* revision, on demand.

    The facts already exist: every attempt's ``result.json`` carries them,
    and ``script.json``'s ``accepted_attempt`` pins that directory against
    GC. Before this they were readable only on the rebuild response that
    produced them, so "how big is the bracket I imported an hour ago" had no
    answer (ADR-043). Nothing is computed here.
    """

    root = str(captured.get("project_root") or "")
    if not root:
        return {
            "ok": False,
            "error": "The active document has no durable Cadex project root.",
        }
    from CadexPinResolution import (
        accepted_attempt_dir,
        accepted_output_item,
        load_worker_report,
    )
    from CadexScriptStore import CadexProjectScriptStore

    state = CadexProjectScriptStore(root).read_state()
    revision = str(state.get("accepted_revision") or "")
    if not revision:
        return {
            "ok": False,
            "error": "The project has no accepted revision to inspect outputs of.",
        }
    report = load_worker_report(accepted_attempt_dir(Path(root), state))
    items = [item for item in list(report.get("outputs") or []) if isinstance(item, Mapping)]
    target = str(captured.get("target") or "")
    if not target:
        return {
            "revision": revision,
            "output_count": len(items),
            "outputs": [
                {
                    "name": str(item.get("name") or ""),
                    "type": str(item.get("type") or ""),
                    "domain": str(item.get("domain") or ""),
                    "artifact_kind": item.get("artifact_kind"),
                }
                for item in items
            ],
        }
    try:
        item = accepted_output_item(report, target)
    except KeyError:
        raise ValueError(
            f"The accepted revision has no output named {target!r}; it publishes "
            f"{sorted(str(entry.get('name') or '') for entry in items)}."
        ) from None
    detail = {
        key: item[key] for key in _OUTPUT_DETAIL_KEYS if item.get(key) is not None
    }
    detail["revision"] = revision
    return detail


def _json_pointer_parts(pointer: str) -> list[str]:
    if not pointer:
        return []
    if not pointer.startswith("/"):
        raise ValueError("path must be an empty string or a JSON Pointer beginning with '/'.")
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def _resolve_pointer(value: Any, pointer: str) -> Any:
    current = value
    for part in _json_pointer_parts(pointer):
        if isinstance(current, Mapping):
            if part not in current:
                raise ValueError(f"JSON Pointer path does not exist: {pointer!r}.")
            current = current[part]
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError) as exc:
                raise ValueError(f"JSON Pointer path does not exist: {pointer!r}.") from exc
        else:
            raise ValueError(f"JSON Pointer traverses a scalar: {pointer!r}.")
    return current


def _pointer_child(pointer: str, value: str | int) -> str:
    escaped = str(value).replace("~", "~0").replace("/", "~1")
    return f"{pointer}/{escaped}" if pointer else f"/{escaped}"


def _encoded_bytes(value: Any) -> int:
    return len(
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    )


def _preview(value: Any, pointer: str) -> Any:
    if _encoded_bytes(value) <= _PREVIEW_BYTES:
        return value
    if isinstance(value, Mapping):
        return {"type": "object", "entry_count": len(value), "inspect_path": pointer}
    if isinstance(value, list):
        return {"type": "array", "item_count": len(value), "inspect_path": pointer}
    if isinstance(value, str):
        return {
            "type": "string",
            "characters": len(value),
            "utf8_bytes": len(value.encode("utf-8", errors="replace")),
            "inspect_path": pointer,
        }
    return {"type": type(value).__name__, "json_bytes": _encoded_bytes(value)}


def _page_value(value: Any, pointer: str, offset: int, limit: int) -> tuple[Any, dict[str, Any]]:
    if isinstance(value, Mapping):
        keyed = sorted(((str(key), key) for key in value), key=lambda item: item[0])
        string_keys = [item[0] for item in keyed]
        if len(set(string_keys)) != len(string_keys):
            raise ValueError("The inspected mapping contains ambiguous non-string keys.")
        selected = keyed[offset : offset + limit]
        page = {
            public_key: _preview(value[actual_key], _pointer_child(pointer, public_key))
            for public_key, actual_key in selected
        }
        return page, {
            "kind": "mapping",
            "total": len(keyed),
            "offset": offset,
            "returned": len(selected),
            "next_offset": (
                offset + len(selected)
                if offset + len(selected) < len(keyed)
                else None
            ),
        }
    if isinstance(value, list):
        selected = value[offset : offset + limit]
        return [
            _preview(item, _pointer_child(pointer, offset + index))
            for index, item in enumerate(selected)
        ], {
            "kind": "array",
            "total": len(value),
            "offset": offset,
            "returned": len(selected),
            "next_offset": offset + len(selected) if offset + len(selected) < len(value) else None,
        }
    if isinstance(value, str):
        character_limit = limit * 1024
        selected = value[offset : offset + character_limit]
        return selected, {
            "kind": "string",
            "total_characters": len(value),
            "offset": offset,
            "returned_characters": len(selected),
            "next_offset": offset + len(selected) if offset + len(selected) < len(value) else None,
        }
    if offset:
        raise ValueError("offset must be zero when the selected path is a scalar.")
    return value, {"kind": "scalar", "returned": 1, "next_offset": None}


def _bounded_page(raw: Any, captured: Mapping[str, Any]) -> dict[str, Any]:
    pointer = str(captured.get("path") or "")
    selected = _resolve_pointer(raw, pointer)
    offset = int(captured.get("offset") or 0)
    requested_limit = int(captured.get("limit") or 1)
    effective_limit = requested_limit
    while True:
        value, page = _page_value(selected, pointer, offset, effective_limit)
        result = {
            "ok": True,
            "scope": str(captured.get("scope") or ""),
            "target": str(captured.get("target") or ""),
            "path": pointer,
            "surface": dict(captured.get("surface") or {}),
            "document": dict(captured.get("document") or {}),
            "page": {
                **page,
                "requested_limit": requested_limit,
                "effective_limit": effective_limit,
            },
            "value": value,
        }
        result["result_json_bytes"] = 0
        size = _encoded_bytes(result)
        while result["result_json_bytes"] != size:
            result["result_json_bytes"] = size
            size = _encoded_bytes(result)
        if size <= MAX_INSPECT_RESULT_BYTES:
            return result
        if effective_limit > 1:
            effective_limit = max(1, effective_limit // 2)
            continue
        raise RuntimeError("The selected scalar exceeds the 32 KiB inspection result limit.")


def _bounded_document_objects_page(captured: Mapping[str, Any]) -> dict[str, Any]:
    values = list(captured.get("values") or [])
    requested_limit = int(captured.get("limit") or 1)
    effective_limit = len(values)
    offset = int(captured.get("offset") or 0)
    total = int(captured.get("total") or 0)
    while True:
        page_values = values[:effective_limit]
        returned = len(page_values)
        result = {
            "ok": True,
            "scope": "document",
            "target": str(captured.get("target") or ""),
            "path": "/objects",
            "surface": dict(captured.get("surface") or {}),
            "document": dict(captured.get("document") or {}),
            "page": {
                "kind": "array",
                "total": total,
                "offset": offset,
                "returned": returned,
                "next_offset": offset + returned if offset + returned < total else None,
                "requested_limit": requested_limit,
                "effective_limit": effective_limit,
            },
            "value": page_values,
        }
        result["result_json_bytes"] = 0
        size = _encoded_bytes(result)
        while result["result_json_bytes"] != size:
            result["result_json_bytes"] = size
            size = _encoded_bytes(result)
        if size <= MAX_INSPECT_RESULT_BYTES:
            return result
        if effective_limit > 1:
            effective_limit = max(1, effective_limit // 2)
            continue
        raise RuntimeError("One document object identity exceeds the inspection result limit.")


def complete_inspection(captured: Mapping[str, Any]) -> dict[str, Any]:
    """Complete artifact-backed reads and apply the exact result-size boundary."""

    try:
        kind = str(captured.get("kind") or "")
        attachment = None
        if kind == "captured":
            raw = captured.get("raw")
        elif kind == "document_objects_page":
            return _bounded_document_objects_page(captured)
        elif kind == "script":
            raw = _complete_script(captured)
        elif kind == "api":
            raw = _complete_api(captured)
        elif kind == "image":
            raw, attachment = _complete_image(captured)
        elif kind == "assets":
            raw = _complete_assets(captured)
        elif kind == "output":
            raw = _complete_output(captured)
        elif kind == "history":
            raw = _complete_history(captured)
        else:
            raise ValueError("Invalid captured core.inspect operation.")
        result = _bounded_page(raw, captured)
        if attachment is not None:
            result["_cadex_image_attachment"] = attachment
        return result
    except Exception as exc:
        error = str(exc)
        if len(error) > 4096:
            error = error[:4093] + "..."
        result = {
            "ok": False,
            "tool": "core.inspect",
            "failure_code": "INSPECTION_FAILED",
            "failure_stage": "precondition",
            "error": error,
            "scope": str(captured.get("scope") or ""),
            "target": str(captured.get("target") or ""),
        }
        result["result_json_bytes"] = 0
        size = _encoded_bytes(result)
        while result["result_json_bytes"] != size:
            result["result_json_bytes"] = size
            size = _encoded_bytes(result)
        return result
