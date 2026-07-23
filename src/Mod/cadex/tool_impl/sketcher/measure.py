# SPDX-License-Identifier: LGPL-2.1-or-later

"""Exact point-to-point measurement inside the active Sketcher sketch."""

from __future__ import annotations

import math
from typing import Any

from .common import (
    geometry_handle,
    geometry_inventory,
    get_sketch,
    resolve_geometry_index,
    validate_geometry_index,
)


class PointReferenceError(ValueError):
    def __init__(self, message: str, **details: Any):
        super().__init__(message)
        self.details = details


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

_POINT_REFERENCE = {
    "oneOf": [
        {
            "type": "object",
            "properties": {"kind": {"type": "string", "const": "origin"}},
            "required": ["kind"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "const": "geometry"},
                "geometry": _GEOMETRY_REFERENCE,
                "point": {
                    "type": "string",
                    "enum": ["start", "end", "center", "midpoint"],
                },
            },
            "required": ["kind", "geometry", "point"],
            "additionalProperties": False,
        },
    ]
}


TOOL_SPEC = {
    "name": "sketcher.measure",
    "safety": "READ",
    "edit_modes": ["sketch"],
    "description": (
        "Measure the exact 2D distance between two existing semantic sketch points. "
        "Returns resolved coordinates, signed X/Y deltas, and Euclidean distance in mm. "
        "This reads geometry only and does not create a dimensional constraint."
    ),
    "contextual": True,
    "parameters": {
        "type": "object",
        "properties": {
            "first": {**_POINT_REFERENCE, "description": "First measured point."},
            "second": {**_POINT_REFERENCE, "description": "Second measured point."},
        },
        "required": ["first", "second"],
        "additionalProperties": False,
    },
}


def _invalid(error: str, **extra: Any) -> dict[str, Any]:
    result = {
        "ok": False,
        "error": error,
        "retry_same_call": False,
        "recoverable": True,
    }
    result.update(extra)
    return result


def _point_xy(value: Any) -> list[float]:
    try:
        return [float(value.x), float(value.y)]
    except Exception as exc:
        raise ValueError("FreeCAD did not return a valid sketch-local point.") from exc


def _available_roles(geometry: Any) -> list[str]:
    roles = []
    if getattr(geometry, "StartPoint", None) is not None:
        roles.append("start")
    if getattr(geometry, "EndPoint", None) is not None:
        roles.append("end")
    if getattr(geometry, "Center", None) is not None:
        roles.append("center")
    if all(
        hasattr(geometry, attribute)
        for attribute in (
            "FirstParameter",
            "LastParameter",
            "length",
            "parameterAtDistance",
            "value",
        )
    ):
        roles.append("midpoint")
    return roles


def _curve_midpoint(geometry: Any) -> list[float]:
    required = (
        "FirstParameter",
        "LastParameter",
        "length",
        "parameterAtDistance",
        "value",
    )
    missing = [name for name in required if not hasattr(geometry, name)]
    if missing:
        raise ValueError(f"{type(geometry).__name__} has no measurable curve midpoint.")
    first_parameter = float(geometry.FirstParameter)
    last_parameter = float(geometry.LastParameter)
    curve_length = float(geometry.length(first_parameter, last_parameter))
    if not math.isfinite(curve_length) or curve_length <= 0.0:
        raise ValueError(f"{type(geometry).__name__} has zero or invalid curve length.")
    midpoint_parameter = float(
        geometry.parameterAtDistance(curve_length / 2.0, first_parameter)
    )
    return _point_xy(geometry.value(midpoint_parameter))


def _resolve_point(service: Any, sketch: Any, reference: Any) -> dict[str, Any]:
    if not isinstance(reference, dict):
        raise PointReferenceError(
            "Point reference must be a structured object.", requested=reference
        )
    kind = str(reference.get("kind") or "").strip().lower()
    if kind == "origin":
        if set(reference) != {"kind"}:
            raise PointReferenceError(
                "An origin reference accepts only kind='origin'.", requested=reference
            )
        return {"kind": "origin", "point": [0.0, 0.0]}
    if kind != "geometry":
        raise PointReferenceError(
            "Point reference kind must be origin or geometry.",
            requested=reference,
            allowed_values=["origin", "geometry"],
        )
    if set(reference) != {"kind", "geometry", "point"}:
        raise PointReferenceError(
            "A geometry point reference requires exactly kind, geometry, and point."
            , requested=reference
        )
    raw_geometry = reference.get("geometry")
    if isinstance(raw_geometry, bool):
        raise PointReferenceError(
            "Boolean values are not geometry references.", requested=reference
        )
    try:
        if isinstance(raw_geometry, int):
            index = resolve_geometry_index(service, sketch, int(raw_geometry), None)
        elif isinstance(raw_geometry, str) and raw_geometry.strip():
            index = resolve_geometry_index(service, sketch, None, raw_geometry.strip())
        else:
            raise ValueError("geometry must be an index or stable handle.")
    except (KeyError, RuntimeError, TypeError, ValueError) as exc:
        raise PointReferenceError(
            str(exc),
            requested=reference,
            requested_handle=raw_geometry,
            live_alternatives=_point_alternatives(service, sketch),
        ) from exc
    invalid = validate_geometry_index(sketch, index)
    if invalid:
        raise PointReferenceError(
            str(invalid.get("error") or "Invalid geometry reference."),
            requested=reference,
            requested_handle=raw_geometry,
            live_alternatives=_point_alternatives(service, sketch),
        )
    geometry = list(getattr(sketch, "Geometry", []) or [])[index]
    role = str(reference.get("point") or "").strip().lower()
    available_roles = _available_roles(geometry)
    if role not in {"start", "end", "center", "midpoint"}:
        raise PointReferenceError(
            "point must be start, end, center, or midpoint.",
            requested=reference,
            resolved_handle=geometry_handle(sketch, index),
            geometry_summary=service._geometry_summary(geometry, index, sketch),
            allowed_point_roles=available_roles,
        )
    if role not in available_roles:
        raise PointReferenceError(
            f"{type(geometry).__name__} does not expose point role '{role}'. "
            f"Available roles: {', '.join(available_roles) or 'none'}.",
            requested=reference,
            requested_handle=raw_geometry,
            resolved_handle=geometry_handle(sketch, index),
            geometry_summary=service._geometry_summary(geometry, index, sketch),
            allowed_point_roles=available_roles,
            live_alternatives=_point_alternatives(service, sketch),
        )
    if role == "midpoint":
        point = _curve_midpoint(geometry)
    else:
        point = _point_xy(
            getattr(
                geometry,
                {"start": "StartPoint", "end": "EndPoint", "center": "Center"}[role],
            )
        )
    return {
        "kind": "geometry",
        "geometry_index": index,
        "geometry_handle": geometry_handle(sketch, index),
        "geometry_type": type(geometry).__name__,
        "point_role": role,
        "point": point,
    }


def _point_alternatives(service: Any, sketch: Any) -> list[dict[str, Any]]:
    alternatives = []
    for item in geometry_inventory(service, sketch):
        index = int(item["index"])
        geometry = list(getattr(sketch, "Geometry", []) or [])[index]
        alternatives.append(
            {
                "geometry_index": index,
                "geometry_handle": item.get("stable_handle"),
                "geometry_type": item.get("type"),
                "allowed_point_roles": _available_roles(geometry),
            }
        )
    return alternatives


def run(service: Any, first: Any, second: Any) -> dict[str, Any]:
    sketch = get_sketch(service)
    if sketch is None:
        return _invalid("No Sketcher sketch is currently open for editing.")
    try:
        first_point = _resolve_point(service, sketch, first)
    except PointReferenceError as exc:
        return _invalid(
            str(exc),
            failure_code="POINT_REFERENCE_INVALID",
            failure_stage="precondition",
            reference_side="first",
            **exc.details,
        )
    try:
        second_point = _resolve_point(service, sketch, second)
    except PointReferenceError as exc:
        return _invalid(
            str(exc),
            failure_code="POINT_REFERENCE_INVALID",
            failure_stage="precondition",
            reference_side="second",
            **exc.details,
        )
    dx = float(second_point["point"][0]) - float(first_point["point"][0])
    dy = float(second_point["point"][1]) - float(first_point["point"][1])
    return {
        "ok": True,
        "measurement_type": "point_distance",
        "sketch": sketch.Name,
        "first": first_point,
        "second": second_point,
        "delta_x_mm": dx,
        "delta_y_mm": dy,
        "distance_mm": math.hypot(dx, dy),
    }
