# SPDX-License-Identifier: LGPL-2.1-or-later

"""Native Sketcher construction-geometry toggle tool."""

from __future__ import annotations

from typing import Any

from .common import (
    active_response,
    geometry_handle,
    get_sketch,
    resolve_geometry_index,
    run_freecad_transaction,
    validate_geometry_index,
)


_GEOMETRY_REFERENCE = {
    "oneOf": [
        {"type": "integer", "minimum": 0},
        {"type": "string", "minLength": 1},
    ],
    "description": (
        "A transient geometry index or the preferred stable tag:<uuid> handle "
        "from live sketch state."
    ),
}


TOOL_SPEC = {
    "name": "sketcher.set_construction",
    "safety": "SAFE_WRITE",
    "edit_modes": ["sketch"],
    "description": (
        "Set selected or all Sketcher geometry as construction or normal geometry. "
        "Construction geometry guides constraints (axes, pitch circles) but is excluded "
        "from solid-feature profiles. The complete selection is resolved before mutation."
    ),
    "contextual": True,
    "parameters": {
        "type": "object",
        "properties": {
            "selection": {
                "oneOf": [
                    {
                        "type": "object",
                        "properties": {
                            "mode": {"type": "string", "const": "geometry"},
                            "items": {
                                "type": "array",
                                "items": _GEOMETRY_REFERENCE,
                                "minItems": 1,
                            },
                        },
                        "required": ["mode", "items"],
                        "additionalProperties": False,
                    },
                    {
                        "type": "object",
                        "properties": {
                            "mode": {"type": "string", "const": "all"},
                        },
                        "required": ["mode"],
                        "additionalProperties": False,
                    },
                ],
                "description": "Explicit geometry selection; use mode='all' for the whole sketch.",
            },
            "construction": {
                "type": "boolean",
                "description": "True for construction geometry, false for normal profile geometry.",
            },
        },
        "required": ["selection", "construction"],
        "additionalProperties": False,
    },
}


def _invalid_call(error: str, **extra: Any) -> dict[str, Any]:
    result = {
        "ok": False,
        "error": error,
        "retry_same_call": False,
        "recoverable": True,
    }
    result.update(extra)
    return result


def run(
    service: Any,
    selection: dict[str, Any] | None = None,
    construction: bool | None = None,
) -> dict[str, Any]:
    if construction is None or not isinstance(construction, bool):
        return _invalid_call(
            "sketcher.set_construction requires construction as an explicit boolean."
        )
    if not isinstance(selection, dict):
        return _invalid_call("selection must be one structured selection object.")
    mode = str(selection.get("mode") or "").strip().lower()
    if mode not in {"geometry", "all"}:
        return _invalid_call("selection.mode must be geometry or all.")
    unexpected = set(selection) - (
        {"mode", "items"} if mode == "geometry" else {"mode"}
    )
    if unexpected:
        return _invalid_call(
            "Unsupported selection field(s): " + ", ".join(sorted(unexpected)) + "."
        )
    sketch = get_sketch(service)
    if sketch is None:
        return _invalid_call("No Sketcher sketch is currently open for editing.")

    geometry_count = len(getattr(sketch, "Geometry", []) or [])
    if mode == "all":
        if geometry_count == 0:
            return _invalid_call("The active sketch has no geometry to update.")
        indices = list(range(geometry_count))
    else:
        items = selection.get("items")
        if not isinstance(items, list) or not items:
            return _invalid_call(
                "selection.items must contain at least one geometry reference."
            )
        indices = []
        for item in items:
            try:
                if isinstance(item, bool):
                    raise ValueError("Boolean values are not geometry references.")
                index = resolve_geometry_index(
                    service,
                    sketch,
                    int(item) if isinstance(item, int) else None,
                    str(item).strip() if isinstance(item, str) else None,
                )
            except Exception as exc:
                return _invalid_call(f"Could not resolve geometry item {item!r}: {exc}")
            invalid = validate_geometry_index(sketch, index)
            if invalid:
                invalid.setdefault("retry_same_call", False)
                invalid.setdefault("recoverable", True)
                return invalid
            indices.append(index)
        if len(indices) != len(set(indices)):
            return _invalid_call(
                "selection.items resolves to duplicate geometry elements."
            )

    stable_handles = {index: geometry_handle(sketch, index) for index in indices}

    def _set() -> dict[str, Any]:
        import FreeCAD as App

        target = get_sketch(service, sketch.Name)
        if target is None:
            raise RuntimeError(f"Sketch not found: {sketch.Name}")
        changes = []
        modified_indices = []
        for index in indices:
            before = bool(target.getConstruction(index))
            target.setConstruction(index, bool(construction))
            after = bool(target.getConstruction(index))
            changed = before != after
            if changed:
                modified_indices.append(index)
            changes.append(
                {
                    "geometry_index": index,
                    "geometry_handle": stable_handles[index],
                    "before": before,
                    "after": after,
                    "changed": changed,
                }
            )
        return {
            "sketch": target.Name,
            "selection_mode": mode,
            "target_count": len(indices),
            "changed_count": len(modified_indices),
            "changes": changes,
            "profile_effect": (
                "ignored_by_profile_validation"
                if construction
                else "included_in_profile_validation"
            ),
            "modified_geometry_indices": modified_indices,
        }

    return active_response(
        service,
        sketch,
        run_freecad_transaction("Set Sketcher construction geometry", _set),
    )
