# SPDX-License-Identifier: LGPL-2.1-or-later

"""Place one semantic Sketcher point at an exact sketch coordinate."""

from __future__ import annotations

from typing import Any

from CadexTools import tool_failure, unchanged_state

from .common import (
    active_response,
    geometry_handle,
    get_sketch,
    resolve_geometry_index,
    run_freecad_transaction,
    solver_status,
    validate_geometry_index,
)
from .constrain_common import point_position


_GEOMETRY_REFERENCE = {
    "oneOf": [
        {"type": "integer", "minimum": 0},
        {"type": "string", "minLength": 1},
    ],
    "description": (
        "One geometry index or, preferably, a stable tag:<uuid> handle from "
        "the live sketch state."
    ),
}


TOOL_SPEC = {
    "name": "sketcher.move_point",
    "safety": "SAFE_WRITE",
    "edit_modes": ["sketch"],
    "description": (
        "Place one exact endpoint or center of existing Sketcher geometry at an "
        "absolute [x, y] sketch coordinate through FreeCAD's solver. This tool "
        "never translates an entire curve; use sketcher.translate_geometry for "
        "whole-geometry or multi-geometry displacement."
    ),
    "contextual": True,
    "parameters": {
        "type": "object",
        "properties": {
            "geometry": _GEOMETRY_REFERENCE,
            "point": {
                "type": "string",
                "enum": ["start", "end", "center"],
                "description": (
                    "Semantic point to place: start/end for bounded curves, or "
                    "center for circles, arcs, and ellipses."
                ),
            },
            "position_mm": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 2,
                "maxItems": 2,
                "description": "Exact absolute [x, y] target in sketch millimetres.",
            },
        },
        "required": ["geometry", "point", "position_mm"],
        "additionalProperties": False,
    },
}


def run(
    service: Any,
    geometry: int | str,
    point: str,
    position_mm: list[float],
) -> dict[str, Any]:
    requested = {
        "geometry": geometry,
        "point": point,
        "position_mm": position_mm,
    }
    sketch = get_sketch(service)
    if sketch is None:
        return tool_failure(
            TOOL_SPEC["name"],
            "NO_ACTIVE_SKETCH",
            "edit_state",
            "No Sketcher sketch is currently open for editing.",
            requested=requested,
            observed={"active_edit_object": None},
            required_changes=[{"action": "open_target_sketch"}],
        )

    try:
        index = _resolve_reference(service, sketch, geometry)
    except (KeyError, RuntimeError, TypeError, ValueError) as exc:
        return tool_failure(
            TOOL_SPEC["name"],
            "GEOMETRY_REFERENCE_INVALID",
            "precondition",
            str(exc),
            requested=requested,
            observed={"sketch": sketch.Name},
            candidates=_live_geometry_candidates(service, sketch),
        )
    invalid = validate_geometry_index(sketch, index)
    if invalid:
        return tool_failure(
            TOOL_SPEC["name"],
            "GEOMETRY_REFERENCE_INVALID",
            "precondition",
            str(invalid.get("error") or "Geometry reference is invalid."),
            requested=requested,
            observed={"sketch": sketch.Name, "resolved_index": index},
            candidates=_live_geometry_candidates(service, sketch),
        )

    target_geometry = list(getattr(sketch, "Geometry", []) or [])[index]
    clean_point = str(point or "").strip().lower()
    allowed_roles = _available_move_roles(target_geometry)
    normalized_reference = {
        "geometry_index": index,
        "geometry_handle": geometry_handle(sketch, index),
    }
    if clean_point not in allowed_roles:
        return tool_failure(
            TOOL_SPEC["name"],
            "POINT_ROLE_UNAVAILABLE",
            "precondition",
            (
                f"{type(target_geometry).__name__} does not expose a movable "
                f"{clean_point!r} point."
            ),
            requested=requested,
            normalized=normalized_reference,
            observed={"geometry_type": type(target_geometry).__name__},
            allowed_values=allowed_roles,
            required_changes=[{"point": allowed_roles}],
        )
    try:
        target_x, target_y = _target_position(position_mm)
    except (TypeError, ValueError) as exc:
        return tool_failure(
            TOOL_SPEC["name"],
            "TARGET_POSITION_INVALID",
            "precondition",
            str(exc),
            requested=requested,
            normalized=normalized_reference,
            required_changes=[{"position_mm": "two finite numbers [x, y]"}],
        )

    try:
        before_point = _point_for_move(sketch, index, clean_point)
    except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
        return tool_failure(
            TOOL_SPEC["name"],
            "POINT_READ_FAILED",
            "precondition",
            str(exc),
            requested=requested,
            normalized={**normalized_reference, "point": clean_point},
            allowed_values=allowed_roles,
        )

    requested_point = [target_x, target_y]
    normalized = {
        **normalized_reference,
        "point": clean_point,
        "position_mm": requested_point,
    }
    before_solver = solver_status(service, sketch)
    initial_error = _distance(before_point, requested_point)
    if initial_error <= 1.0e-7:
        response = active_response(
            service,
            sketch,
            {
                "ok": True,
                "result": {
                    "sketch": sketch.Name,
                    **normalized,
                    "before_point": before_point,
                    "after_point": before_point,
                    "displacement_error_mm": initial_error,
                    "effect_applied": False,
                    "already_satisfied": True,
                },
                "document_delta": {},
                "state_change": unchanged_state(),
            },
        )
        response["requested"] = requested
        response["normalized"] = normalized
        return response

    def move() -> dict[str, Any]:
        import FreeCAD as App

        target = get_sketch(service, sketch.Name)
        if target is None:
            raise RuntimeError(f"Sketch not found: {sketch.Name}")
        before_geometry = service._geometry_summary(
            list(getattr(target, "Geometry", []))[index], index, target
        )
        native_point_position = point_position(clean_point)
        target.moveGeometry(
            index,
            native_point_position,
            App.Vector(target_x, target_y, 0.0),
            0,
        )
        geometry_after = service._geometry_summary(
            list(getattr(target, "Geometry", []))[index], index, target
        )
        after_point = _point_for_move(target, index, clean_point)
        displacement_error = _distance(after_point, requested_point)
        actual_movement = _distance(after_point, before_point)
        after_solver = solver_status(service, target)
        return {
            "sketch": target.Name,
            "geometry_index": index,
            "geometry_handle": geometry_handle(target, index),
            "point": clean_point,
            "position_mm": requested_point,
            "before_point": before_point,
            "after_point": after_point,
            "actual_movement_mm": actual_movement,
            "displacement_error_mm": displacement_error,
            "effect_applied": actual_movement > 1.0e-9,
            "degrees_of_freedom_before": before_solver.get("degrees_of_freedom"),
            "degrees_of_freedom_after": after_solver.get("degrees_of_freedom"),
            "geometry_before": before_geometry,
            "geometry": geometry_after,
        }

    def verify(result: dict[str, Any]) -> dict[str, Any]:
        effect = bool(result.get("effect_applied"))
        error = float(result.get("displacement_error_mm") or 0.0)
        ok = effect and error <= 1.0e-7
        return {
            "ok": ok,
            "checks": [
                {
                    "name": "requested_point_achieved",
                    "ok": ok,
                    "effect_applied": effect,
                    "displacement_error_mm": error,
                    "tolerance_mm": 1.0e-7,
                }
            ],
            "error": (
                None
                if ok
                else (
                    "Sketcher constraints prevented the point from reaching the "
                    "requested coordinate."
                )
            ),
        }

    response = active_response(
        service,
        sketch,
        run_freecad_transaction(
            "Move Sketcher geometry point",
            move,
            verifier=verify,
        ),
    )
    response["requested"] = requested
    response["normalized"] = normalized
    if not response.get("ok"):
        response["candidates"] = _live_geometry_candidates(service, sketch)
        response["retry"] = {
            "same_call": False,
            "required_changes": [
                {
                    "action": "inspect_or_edit_constraints",
                    "geometry_handle": normalized_reference["geometry_handle"],
                    "point": clean_point,
                    "reason": (
                        "The current constraint system prevented the requested "
                        "placement."
                    ),
                }
            ],
        }
    return response


def _available_move_roles(geometry: Any) -> list[str]:
    roles = []
    if getattr(geometry, "StartPoint", None) is not None:
        roles.append("start")
    if getattr(geometry, "EndPoint", None) is not None:
        roles.append("end")
    if getattr(geometry, "Center", None) is not None:
        roles.append("center")
    return roles


def _xy(value: Any) -> list[float]:
    return [float(value.x), float(value.y)]


def _point_for_move(sketch: Any, index: int, role: str) -> list[float]:
    geometry = list(getattr(sketch, "Geometry", []) or [])[index]
    if role == "start":
        return _xy(geometry.StartPoint)
    if role == "end":
        return _xy(geometry.EndPoint)
    if role == "center":
        center = getattr(geometry, "Center", None)
        if center is None:
            raise ValueError(f"{type(geometry).__name__} has no movable center.")
        return _xy(center)
    raise ValueError(f"Unsupported point role: {role!r}.")


def _resolve_reference(service: Any, sketch: Any, reference: int | str) -> int:
    if isinstance(reference, bool):
        raise ValueError("geometry must be an index or stable handle, not a boolean.")
    if isinstance(reference, int):
        return int(reference)
    if isinstance(reference, str) and reference.strip():
        return resolve_geometry_index(service, sketch, None, reference.strip())
    raise ValueError(
        "geometry must be an index or stable handle from live sketch state."
    )


def _target_position(value: list[float]) -> tuple[float, float]:
    import math

    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("position_mm must contain exactly two numbers [x, y].")
    if any(isinstance(item, bool) for item in value):
        raise ValueError("position_mm values must be numbers, not booleans.")
    x, y = float(value[0]), float(value[1])
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError("position_mm values must be finite numbers.")
    return x, y


def _distance(first: list[float], second: list[float]) -> float:
    dx = float(first[0]) - float(second[0])
    dy = float(first[1]) - float(second[1])
    return (dx * dx + dy * dy) ** 0.5


def _live_geometry_candidates(service: Any, sketch: Any) -> list[dict[str, Any]]:
    geometry = list(getattr(sketch, "Geometry", []) or [])
    return [
        {
            "index": index,
            "handle": geometry_handle(sketch, index),
            "type": service._geometry_summary(item, index, sketch).get("type"),
            "movable_points": _available_move_roles(item),
        }
        for index, item in enumerate(geometry)
    ]
