# SPDX-License-Identifier: LGPL-2.1-or-later

"""Translate existing Sketcher geometry through the native solver."""

from __future__ import annotations

from typing import Any

from CadexTools import tool_failure

from .common import (
    active_response,
    geometry_fingerprint,
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
        "A transient geometry index or preferred stable tag:<uuid> handle from "
        "the live sketch state."
    ),
}


TOOL_SPEC = {
    "name": "sketcher.translate_geometry",
    "safety": "SAFE_WRITE",
    "edit_modes": ["sketch"],
    "description": (
        "Translate exact existing Sketcher geometry by one XY displacement through "
        "FreeCAD's native moveGeometry solver operation. This edits the selected "
        "geometry in place; it never copies, mirrors, offsets, or arrays geometry."
    ),
    "contextual": True,
    "parameters": {
        "type": "object",
        "properties": {
            "geometry": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": _GEOMETRY_REFERENCE,
                "description": "Exact geometry references from live sketch state.",
            },
            "delta_mm": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 2,
                "maxItems": 2,
                "description": "Requested [x, y] translation in sketch millimetres.",
            },
        },
        "required": ["geometry", "delta_mm"],
        "additionalProperties": False,
    },
}


def run(
    service: Any,
    geometry: list[int | str],
    delta_mm: list[float],
) -> dict[str, Any]:
    sketch = get_sketch(service)
    if sketch is None:
        return tool_failure(
            TOOL_SPEC["name"],
            "NO_ACTIVE_SKETCH",
            "edit_state",
            "No Sketcher sketch is currently open for editing.",
            requested={"geometry": geometry, "delta_mm": delta_mm},
            observed={"active_edit_object": None},
            required_changes=[{"action": "open_target_sketch"}],
        )
    try:
        indices, handles = _resolve_references(service, sketch, geometry)
    except (KeyError, ValueError, RuntimeError, TypeError) as exc:
        return tool_failure(
            TOOL_SPEC["name"],
            "GEOMETRY_REFERENCE_INVALID",
            "precondition",
            str(exc),
            requested={"geometry": geometry, "delta_mm": delta_mm},
            observed={"sketch": sketch.Name},
            candidates=_live_geometry_candidates(service, sketch),
        )
    for index in indices:
        invalid = validate_geometry_index(sketch, index)
        if invalid:
            return tool_failure(
                TOOL_SPEC["name"],
                "GEOMETRY_REFERENCE_INVALID",
                "precondition",
                str(invalid.get("error") or "Geometry reference is invalid."),
                requested={"geometry": geometry, "delta_mm": delta_mm},
                observed={"sketch": sketch.Name, "resolved_index": index},
                candidates=_live_geometry_candidates(service, sketch),
            )
    dx, dy = float(delta_mm[0]), float(delta_mm[1])
    if abs(dx) <= 1e-12 and abs(dy) <= 1e-12:
        return tool_failure(
            TOOL_SPEC["name"],
            "ZERO_TRANSLATION",
            "precondition",
            "delta_mm must request a non-zero translation.",
            requested={"geometry": geometry, "delta_mm": delta_mm},
            normalized={"geometry_indices": indices, "delta_mm": [dx, dy]},
            required_changes=[{"delta_mm": "non-zero [x, y]"}],
        )

    def transform() -> dict[str, Any]:
        import FreeCAD as App

        target = get_sketch(service, sketch.Name)
        if target is None:
            raise RuntimeError(f"Sketch not found: {sketch.Name}")
        before = _geometry_states(service, target, indices)
        for index in indices:
            target.moveGeometry(index, 0, App.Vector(dx, dy, 0.0), 1)
        after = _geometry_states(service, target, indices)
        effects = []
        for before_item, after_item in zip(before, after):
            effects.append(
                {
                    "geometry_index": before_item["index"],
                    "geometry_handle": before_item["handle"],
                    "before": before_item,
                    "after": after_item,
                    "effect_applied": before_item["fingerprint"]
                    != after_item["fingerprint"],
                }
            )
        return {
            "sketch": target.Name,
            "operation": "translate",
            "requested_delta_mm": [dx, dy],
            "modified_geometry_indices": indices,
            "geometry_indices": indices,
            "geometry_handles": handles,
            "effects": effects,
            "effect_applied": all(item["effect_applied"] for item in effects),
        }

    def verify(result: dict[str, Any]) -> dict[str, Any]:
        effects = list(result.get("effects") or [])
        failed = [item for item in effects if not item.get("effect_applied")]
        return {
            "ok": bool(effects) and not failed,
            "checks": [
                {
                    "name": "requested_geometry_moved",
                    "ok": not failed,
                    "failed_geometry": [item["geometry_handle"] for item in failed],
                }
            ],
            "error": (
                "FreeCAD's solver retained one or more selected geometries at their "
                "original position. Their constraints prevented the requested move."
                if failed
                else None
            ),
        }

    response = active_response(
        service,
        sketch,
        run_freecad_transaction("Translate Sketcher geometry", transform, verify),
    )
    response["requested"] = {"geometry": geometry, "delta_mm": delta_mm}
    response["normalized"] = {
        "geometry_indices": indices,
        "geometry_handles": handles,
        "delta_mm": [dx, dy],
    }
    return response


def _resolve_references(
    service: Any,
    sketch: Any,
    references: list[int | str],
) -> tuple[list[int], list[str]]:
    resolved: list[int] = []
    handles: list[str] = []
    for reference in references:
        if isinstance(reference, bool):
            raise ValueError("Geometry references must be indices or stable handles.")
        if isinstance(reference, int):
            index = int(reference)
        elif isinstance(reference, str) and reference.strip():
            index = resolve_geometry_index(service, sketch, None, reference.strip())
        else:
            raise ValueError("Geometry references must be indices or stable handles.")
        if index not in resolved:
            resolved.append(index)
            handles.append(geometry_handle(sketch, index))
    return resolved, handles


def _geometry_states(
    service: Any,
    sketch: Any,
    indices: list[int],
) -> list[dict[str, Any]]:
    geometry = list(getattr(sketch, "Geometry", []) or [])
    states = []
    for index in indices:
        summary = service._geometry_summary(geometry[index], index, sketch)
        states.append(
            {
                "index": index,
                "handle": geometry_handle(sketch, index),
                "type": summary.get("type"),
                "fingerprint": geometry_fingerprint(summary),
            }
        )
    return states


def _live_geometry_candidates(service: Any, sketch: Any) -> list[dict[str, Any]]:
    geometry = list(getattr(sketch, "Geometry", []) or [])
    return [
        {
            "index": index,
            "handle": geometry_handle(sketch, index),
            "type": service._geometry_summary(item, index, sketch).get("type"),
        }
        for index, item in enumerate(geometry)
    ]
