# SPDX-License-Identifier: LGPL-2.1-or-later

"""Consolidated native Sketcher local-geometry modification tool.

Replaces the retired single-operation tools ``sketcher.trim_geometry``,
``sketcher.extend_geometry``, ``sketcher.split_geometry``, and
``sketcher.fillet_corner`` with one operation-discriminated tool.
"""

from __future__ import annotations

import math
from typing import Any

from .common import (
    active_response,
    constraint_inventory,
    geometry_inventory,
    geometry_handle as stable_geometry_handle,
    get_sketch,
    resolve_geometry_index,
    run_freecad_transaction,
    sketch_collection_maps,
    validate_geometry_index,
)
from .constrain_common import point_position


OPERATIONS = (
    "trim",
    "extend",
    "split",
    "fillet_at_endpoint",
    "fillet_between_curves",
    "chamfer_at_endpoint",
    "chamfer_between_curves",
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

_POINT = {
    "type": "array",
    "items": {"type": "number"},
    "minItems": 2,
    "maxItems": 2,
    "description": "Exact [x, y] point in sketch-local mm.",
}


def _action_schema(
    operation: str, properties: dict[str, Any], required: list[str]
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {"type": "string", "const": operation},
            **properties,
        },
        "required": ["operation", *required],
        "additionalProperties": False,
    }


TOOL_SPEC = {
    "name": "sketcher.modify_geometry",
    "safety": "SAFE_WRITE",
    "edit_modes": ["sketch"],
    "description": (
        "Trim, extend, split, or fillet/chamfer at an endpoint or between curves "
        "on existing Sketcher geometry. "
        "Choose one explicit action shape; only arguments valid for that native "
        "operation are accepted. Fillets do not replace required design curves."
    ),
    "contextual": True,
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "oneOf": [
                    _action_schema(
                        "trim",
                        {"target": _GEOMETRY_REFERENCE, "point": _POINT},
                        ["target", "point"],
                    ),
                    _action_schema(
                        "split",
                        {"target": _GEOMETRY_REFERENCE, "point": _POINT},
                        ["target", "point"],
                    ),
                    _action_schema(
                        "extend",
                        {
                            "target": _GEOMETRY_REFERENCE,
                            "endpoint": {"type": "string", "enum": ["start", "end"]},
                            "distance_mm": {"type": "number"},
                        },
                        ["target", "endpoint", "distance_mm"],
                    ),
                    *[
                        _action_schema(
                            operation,
                            {
                                "target": _GEOMETRY_REFERENCE,
                                "endpoint": {
                                    "type": "string",
                                    "enum": ["start", "end"],
                                },
                                "size_mm": {"type": "number", "exclusiveMinimum": 0},
                                "trim_originals": {"type": "boolean"},
                                "preserve_corner": {"type": "boolean"},
                            },
                            [
                                "target",
                                "endpoint",
                                "size_mm",
                                "trim_originals",
                                "preserve_corner",
                            ],
                        )
                        for operation in ("fillet_at_endpoint", "chamfer_at_endpoint")
                    ],
                    *[
                        _action_schema(
                            operation,
                            {
                                "first": _GEOMETRY_REFERENCE,
                                "first_pick": {
                                    **_POINT,
                                    "description": (
                                        "Optional point on the first curve near the intended corner. "
                                        "Provide both picks for ambiguous or non-coincident curves."
                                    ),
                                },
                                "second": _GEOMETRY_REFERENCE,
                                "second_pick": {
                                    **_POINT,
                                    "description": (
                                        "Optional point on the second curve near the intended corner. "
                                        "Provide both picks for ambiguous or non-coincident curves."
                                    ),
                                },
                                "size_mm": {"type": "number", "exclusiveMinimum": 0},
                                "trim_originals": {"type": "boolean"},
                                "preserve_corner": {"type": "boolean"},
                            },
                            [
                                "first",
                                "second",
                                "size_mm",
                                "trim_originals",
                                "preserve_corner",
                            ],
                        )
                        for operation in (
                            "fillet_between_curves",
                            "chamfer_between_curves",
                        )
                    ],
                ],
                "description": "One exact native geometry modification.",
            },
        },
        "required": ["action"],
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
    action: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(action, dict):
        return _invalid_call("action must be one structured modification object.")
    op = str(action.get("operation") or "").strip().lower()
    if op not in OPERATIONS:
        return _invalid_call(
            f"Unknown operation: {op!r}. Valid operations: {', '.join(OPERATIONS)}."
        )
    sketch = get_sketch(service)
    if sketch is None:
        return _invalid_call("No Sketcher sketch is currently open for editing.")
    if op.endswith("_at_endpoint") or op.endswith("_between_curves"):
        endpoint_mode = op.endswith("_at_endpoint")
        first = action.get("target") if endpoint_mode else action.get("first")
        try:
            first_geometry, first_handle = _reference_parts(first)
            second_geometry, second_handle = (
                (None, None)
                if endpoint_mode
                else _reference_parts(action.get("second"))
            )
        except ValueError as exc:
            return _invalid_call(str(exc))
        first_pick = action.get("first_pick")
        second_pick = action.get("second_pick")
        if not endpoint_mode and ((first_pick is None) != (second_pick is None)):
            return _invalid_call(
                f"operation='{op}' requires both first_pick and second_pick when either is provided."
            )
        if (
            not endpoint_mode
            and first_pick is not None
            and (not _point2(first_pick) or not _point2(second_pick))
        ):
            return _invalid_call(
                f"operation='{op}' requires each explicit pick as a numeric [x, y] pair."
            )
        if not isinstance(action.get("trim_originals"), bool):
            return _invalid_call(
                f"operation='{op}' requires trim_originals=true or false."
            )
        if not isinstance(action.get("preserve_corner"), bool):
            return _invalid_call(
                f"operation='{op}' requires preserve_corner=true or false."
            )
        return _run_fillet(
            service,
            sketch,
            first_geometry,
            first_handle,
            str(action.get("endpoint") or "") if endpoint_mode else None,
            None if endpoint_mode else second_geometry,
            None if endpoint_mode else second_handle,
            float(first_pick[0])
            if isinstance(first_pick, list) and len(first_pick) == 2
            else None,
            float(first_pick[1])
            if isinstance(first_pick, list) and len(first_pick) == 2
            else None,
            float(second_pick[0])
            if isinstance(second_pick, list) and len(second_pick) == 2
            else None,
            float(second_pick[1])
            if isinstance(second_pick, list) and len(second_pick) == 2
            else None,
            action.get("size_mm"),
            action["trim_originals"],
            action["preserve_corner"],
            op.startswith("chamfer_"),
        )
    try:
        geometry_index, geometry_handle = _reference_parts(action.get("target"))
    except ValueError as exc:
        return _invalid_call(str(exc))
    try:
        index = resolve_geometry_index(service, sketch, geometry_index, geometry_handle)
    except (KeyError, ValueError, RuntimeError, TypeError) as exc:
        return _invalid_call(
            str(exc),
            geometry_index=geometry_index,
            geometry_handle=geometry_handle,
        )
    invalid = validate_geometry_index(sketch, index)
    if invalid:
        invalid.setdefault("retry_same_call", False)
        invalid.setdefault("recoverable", True)
        return invalid
    if op in {"trim", "split"}:
        point = action.get("point")
        if not isinstance(point, list) or len(point) != 2:
            return _invalid_call(f"operation='{op}' requires point=[x, y].")
        return _run_trim_or_split(
            service,
            sketch,
            op,
            index,
            geometry_handle,
            float(point[0]),
            float(point[1]),
        )
    # op == "extend"
    endpoint = action.get("endpoint")
    if endpoint is None:
        return _invalid_call(
            "operation='extend' requires endpoint='start' or endpoint='end'."
        )
    clean_endpoint = str(endpoint or "").strip().lower()
    if clean_endpoint not in {"start", "end"}:
        return _invalid_call("endpoint must be start or end.")
    distance = action.get("distance_mm")
    if distance is None:
        return _invalid_call("operation='extend' requires distance_mm.")
    return _run_extend(
        service, sketch, index, geometry_handle, clean_endpoint, float(distance)
    )


def _reference_parts(reference: Any) -> tuple[int | None, str | None]:
    if isinstance(reference, bool):
        raise ValueError("Geometry reference must be an index or stable handle.")
    if isinstance(reference, int):
        return int(reference), None
    if isinstance(reference, str) and reference.strip():
        return None, reference.strip()
    raise ValueError("Geometry reference must be an index or stable handle.")


def _point2(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and not any(isinstance(item, bool) for item in value)
        and all(isinstance(item, (int, float)) for item in value)
    )


def _run_trim_or_split(
    service: Any,
    sketch: Any,
    op: str,
    index: int,
    geometry_handle: str | None,
    x: float,
    y: float,
) -> dict[str, Any]:
    def _mutate() -> dict[str, Any]:
        import FreeCAD as App

        target = get_sketch(service, sketch.Name)
        if target is None:
            raise RuntimeError(f"Sketch not found: {sketch.Name}")
        before_geometry = geometry_inventory(service, target)
        before_constraints = constraint_inventory(service, target)
        requested_handle = stable_geometry_handle(target, index)
        if op == "trim":
            native_result = target.trim(index, App.Vector(x, y, 0.0))
        else:
            native_result = target.split(index, App.Vector(x, y, 0.0))
        maps = sketch_collection_maps(
            service, target, before_geometry, before_constraints
        )
        return {
            "sketch": target.Name,
            "operation": op,
            "geometry_index": index,
            "requested_geometry_handle": requested_handle,
            "picked_point": [x, y],
            "native_mutation_result": native_result,
            "geometry_map": maps["geometry"],
            "constraint_map": maps["constraints"],
            "geometry_count_before": len(before_geometry),
            "geometry_count": len(maps["geometry_after"]),
            "constraint_count_before": len(before_constraints),
            "constraint_count": len(maps["constraints_after"]),
            "created_geometry": maps["geometry"]["created"],
            "deleted_geometry": maps["geometry"]["deleted"],
            "created_constraints": maps["constraints"]["created"],
            "deleted_constraints": maps["constraints"]["deleted"],
        }

    label = "Trim Sketcher geometry" if op == "trim" else "Split Sketcher geometry"
    return active_response(service, sketch, run_freecad_transaction(label, _mutate))


def _run_extend(
    service: Any,
    sketch: Any,
    index: int,
    geometry_handle: str | None,
    endpoint: str,
    increment: float,
) -> dict[str, Any]:
    def _extend() -> dict[str, Any]:
        import FreeCAD as App

        target = get_sketch(service, sketch.Name)
        if target is None:
            raise RuntimeError(f"Sketch not found: {sketch.Name}")
        before_geometry = geometry_inventory(service, target)
        before_constraints = constraint_inventory(service, target)
        requested_handle = stable_geometry_handle(target, index)
        native_result = target.extend(index, increment, point_position(endpoint))
        maps = sketch_collection_maps(
            service, target, before_geometry, before_constraints
        )
        return {
            "sketch": target.Name,
            "operation": "extend",
            "geometry_index": index,
            "requested_geometry_handle": requested_handle,
            "endpoint": endpoint,
            "increment": increment,
            "native_mutation_result": native_result,
            "geometry_map": maps["geometry"],
            "constraint_map": maps["constraints"],
            "geometry_count_before": len(before_geometry),
            "geometry_count": len(maps["geometry_after"]),
            "constraint_count_before": len(before_constraints),
            "constraint_count": len(maps["constraints_after"]),
            "created_geometry": maps["geometry"]["created"],
            "deleted_geometry": maps["geometry"]["deleted"],
            "created_constraints": maps["constraints"]["created"],
            "deleted_constraints": maps["constraints"]["deleted"],
        }

    return active_response(
        service, sketch, run_freecad_transaction("Extend Sketcher geometry", _extend)
    )


def _run_fillet(
    service: Any,
    sketch: Any,
    first_geometry: int | None,
    first_geometry_handle: str | None,
    first_point: str,
    second_geometry: int | None,
    second_geometry_handle: str | None,
    first_reference_x: float | None,
    first_reference_y: float | None,
    second_reference_x: float | None,
    second_reference_y: float | None,
    radius: float | None,
    trim: bool,
    preserve_corner: bool,
    chamfer: bool,
) -> dict[str, Any]:
    if radius is None or float(radius) <= 0:
        return _invalid_call("operation='fillet' requires a positive radius.")
    if second_geometry is None and not second_geometry_handle:
        if first_point is None:
            return _invalid_call(
                "operation='fillet' without second_geometry requires first_point='start' or first_point='end'."
            )
        if str(first_point or "").strip().lower() not in {"start", "end"}:
            return _invalid_call("first_point must be start or end.")
    try:
        first_index = resolve_geometry_index(
            service, sketch, first_geometry, first_geometry_handle
        )
        second_index = (
            resolve_geometry_index(
                service, sketch, second_geometry, second_geometry_handle
            )
            if second_geometry is not None or second_geometry_handle
            else None
        )
    except (KeyError, ValueError, RuntimeError, TypeError) as exc:
        return _invalid_call(str(exc))
    invalid = validate_geometry_index(sketch, first_index)
    if invalid:
        invalid.setdefault("retry_same_call", False)
        invalid.setdefault("recoverable", True)
        return invalid
    if second_index is not None:
        invalid = validate_geometry_index(sketch, second_index)
        if invalid:
            invalid.setdefault("retry_same_call", False)
            invalid.setdefault("recoverable", True)
            return invalid
    resolved_references = _resolve_fillet_references(
        sketch,
        first_index,
        second_index,
        first_reference_x,
        first_reference_y,
        second_reference_x,
        second_reference_y,
        float(radius),
    )
    if not resolved_references.get("ok"):
        resolved_references.setdefault("retry_same_call", False)
        resolved_references.setdefault("recoverable", True)
        return resolved_references

    def _fillet() -> dict[str, Any]:
        import FreeCAD as App

        target = get_sketch(service, sketch.Name)
        if target is None:
            raise RuntimeError(f"Sketch not found: {sketch.Name}")
        before_geometry = geometry_inventory(service, target)
        before_constraints = constraint_inventory(service, target)
        first_requested_handle = stable_geometry_handle(target, first_index)
        second_requested_handle = (
            stable_geometry_handle(target, second_index)
            if second_index is not None
            else None
        )
        if second_index is None:
            native_result = target.fillet(
                first_index,
                point_position(str(first_point).strip().lower()),
                float(radius),
                int(bool(trim)),
                bool(preserve_corner),
                bool(chamfer),
            )
            reference_mode = "coincident_point"
        else:
            first_ref = resolved_references["first_reference"]
            second_ref = resolved_references["second_reference"]
            native_result = target.fillet(
                first_index,
                second_index,
                App.Vector(float(first_ref[0]), float(first_ref[1]), 0.0),
                App.Vector(float(second_ref[0]), float(second_ref[1]), 0.0),
                float(radius),
                int(bool(trim)),
                bool(preserve_corner),
                bool(chamfer),
            )
            reference_mode = str(resolved_references["reference_mode"])
        maps = sketch_collection_maps(
            service, target, before_geometry, before_constraints
        )
        created_geometry = maps["geometry"]["created"]
        created_constraints = maps["constraints"]["created"]
        return {
            "sketch": target.Name,
            "operation": "fillet",
            "created_geometry_indices": [item["index"] for item in created_geometry],
            "created_constraint_indices": [item["index"] for item in created_constraints],
            "first_geometry": first_index,
            "first_geometry_handle": first_requested_handle,
            "second_geometry": second_index,
            "second_geometry_handle": second_requested_handle,
            "reference_mode": reference_mode,
            "first_reference": resolved_references.get("first_reference"),
            "second_reference": resolved_references.get("second_reference"),
            "shared_endpoint": resolved_references.get("shared_endpoint"),
            "radius": float(radius),
            "trim": bool(trim),
            "preserve_corner": bool(preserve_corner),
            "chamfer": bool(chamfer),
            "native_mutation_result": native_result,
            "geometry_map": maps["geometry"],
            "constraint_map": maps["constraints"],
            "geometry_count_before": len(before_geometry),
            "geometry_count": len(maps["geometry_after"]),
            "constraint_count_before": len(before_constraints),
            "constraint_count": len(maps["constraints_after"]),
            "created_geometry": created_geometry,
            "deleted_geometry": maps["geometry"]["deleted"],
            "created_constraints": created_constraints,
            "deleted_constraints": maps["constraints"]["deleted"],
        }

    return active_response(
        service,
        sketch,
        run_freecad_transaction("Create Sketcher fillet/chamfer", _fillet),
    )


def _point_xy(point: Any) -> tuple[float, float] | None:
    if point is None:
        return None
    return (float(point.x), float(point.y))


def _geometry_endpoints(geometry: Any) -> list[dict[str, Any]]:
    endpoints: list[dict[str, Any]] = []
    for role, attr in (("start", "StartPoint"), ("end", "EndPoint")):
        point = _point_xy(getattr(geometry, attr, None))
        if point is not None:
            endpoints.append({"role": role, "point": [point[0], point[1]]})
    return endpoints


def _endpoint_candidates(
    sketch: Any, first_index: int, second_index: int | None
) -> dict[str, Any]:
    geometry = list(getattr(sketch, "Geometry", []) or [])
    result: dict[str, Any] = {
        "first_geometry": first_index,
        "first_endpoints": _geometry_endpoints(geometry[first_index])
        if 0 <= first_index < len(geometry)
        else [],
    }
    if second_index is not None:
        result["second_geometry"] = second_index
        result["second_endpoints"] = (
            _geometry_endpoints(geometry[second_index])
            if 0 <= second_index < len(geometry)
            else []
        )
    return result


def _unique_shared_endpoint_references(
    sketch: Any,
    first_index: int,
    second_index: int,
    tolerance_mm: float = 1.0e-5,
) -> dict[str, Any]:
    candidates = _endpoint_candidates(sketch, first_index, second_index)
    first_endpoints = list(candidates.get("first_endpoints") or [])
    second_endpoints = list(candidates.get("second_endpoints") or [])
    pair_gaps = []
    shared_pairs = []
    for first in first_endpoints:
        for second in second_endpoints:
            first_point = first["point"]
            second_point = second["point"]
            gap = math.hypot(
                float(first_point[0]) - float(second_point[0]),
                float(first_point[1]) - float(second_point[1]),
            )
            pair = {
                "first_role": first["role"],
                "second_role": second["role"],
                "gap_mm": gap,
            }
            pair_gaps.append(pair)
            if gap <= tolerance_mm:
                shared_pairs.append((first, second, gap))
    if len(shared_pairs) != 1:
        return {
            "ok": False,
            "error": (
                "The selected curves do not have exactly one unambiguous shared "
                "endpoint. Provide first_pick and second_pick explicitly."
            ),
            "reference_mode": "ambiguous_or_unconnected_endpoints",
            "endpoint_candidates": candidates,
            "endpoint_pair_gaps": pair_gaps,
            "shared_endpoint_tolerance_mm": tolerance_mm,
            "required_arguments": ["first_pick", "second_pick"],
        }
    first_shared, second_shared, gap = shared_pairs[0]
    first_other = [
        endpoint
        for endpoint in first_endpoints
        if endpoint["role"] != first_shared["role"]
    ]
    second_other = [
        endpoint
        for endpoint in second_endpoints
        if endpoint["role"] != second_shared["role"]
    ]
    if len(first_other) != 1 or len(second_other) != 1:
        return {
            "ok": False,
            "error": (
                "The shared corner is unique, but one selected curve has no unique "
                "opposite endpoint. Provide first_pick and second_pick explicitly."
            ),
            "reference_mode": "closed_or_unsupported_curve_endpoint",
            "endpoint_candidates": candidates,
            "required_arguments": ["first_pick", "second_pick"],
        }
    shared_point = [
        (float(first_shared["point"][0]) + float(second_shared["point"][0])) / 2.0,
        (float(first_shared["point"][1]) + float(second_shared["point"][1])) / 2.0,
    ]
    return {
        "ok": True,
        "reference_mode": "unique_shared_endpoint",
        "first_reference": list(first_other[0]["point"]),
        "second_reference": list(second_other[0]["point"]),
        "shared_endpoint": {
            "first_role": first_shared["role"],
            "second_role": second_shared["role"],
            "point": shared_point,
            "gap_mm": gap,
            "tolerance_mm": tolerance_mm,
        },
    }


def _resolve_fillet_references(
    sketch: Any,
    first_index: int,
    second_index: int | None,
    first_reference_x: float | None,
    first_reference_y: float | None,
    second_reference_x: float | None,
    second_reference_y: float | None,
    radius: float,
) -> dict[str, Any]:
    if second_index is None:
        return {"ok": True, "reference_mode": "coincident_point"}
    if None not in (
        first_reference_x,
        first_reference_y,
        second_reference_x,
        second_reference_y,
    ):
        return {
            "ok": True,
            "reference_mode": "explicit_two_curve_references",
            "first_reference": [float(first_reference_x), float(first_reference_y)],
            "second_reference": [float(second_reference_x), float(second_reference_y)],
        }
    return _unique_shared_endpoint_references(sketch, first_index, second_index)
