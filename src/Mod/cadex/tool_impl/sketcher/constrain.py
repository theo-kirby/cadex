# SPDX-License-Identifier: LGPL-2.1-or-later

"""Apply a validated batch of native Sketcher constraints."""

from __future__ import annotations

from typing import Any

from CadexTools import tool_failure

from . import add_constraint
from .common import (
    active_response,
    geometry_inventory,
    get_sketch,
    run_freecad_transaction,
    solver_status,
)


_CONSTRAINT_TYPES = (
    "Horizontal",
    "Vertical",
    "Parallel",
    "Perpendicular",
    "Tangent",
    "Equal",
    "Symmetric",
    "Block",
    "Coincident",
    "PointOnObject",
    "Distance",
    "DistanceX",
    "DistanceY",
    "Radius",
    "Diameter",
    "Angle",
    "Lock",
)

_GEOMETRY = {
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
    "type": "object",
    "properties": {
        "geometry": _GEOMETRY,
        "point": {
            "type": "string",
            "enum": ["start", "end", "center", "midpoint", "whole"],
        },
    },
    "required": ["geometry", "point"],
    "additionalProperties": False,
}

_POSITION = {
    "type": "array",
    "items": {"type": "number"},
    "minItems": 2,
    "maxItems": 2,
}


def _constraint_schema(
    constraint_type: str,
    properties: dict[str, Any],
    required: list[str],
) -> dict[str, Any]:
    type_schema: dict[str, Any] = {"type": "string", "const": constraint_type}
    if constraint_type == "Block":
        type_schema["description"] = (
            "Freeze the complete geometry exactly as drawn. Reserve this for "
            "intentional fixed reference or imported geometry; do not use it on "
            "primary product form merely to force the sketch to zero DoF."
        )
    return {
        "type": "object",
        "properties": {
            "type": type_schema,
            **properties,
        },
        "required": ["type", *required],
        "additionalProperties": False,
    }


_CONSTRAINT_SCHEMAS = [
    *[
        _constraint_schema(kind, {"geometry": _GEOMETRY}, ["geometry"])
        for kind in ("Horizontal", "Vertical", "Block")
    ],
    *[
        _constraint_schema(
            kind,
            {"first": _GEOMETRY, "second": _GEOMETRY},
            ["first", "second"],
        )
        for kind in ("Parallel", "Perpendicular", "Tangent", "Equal")
    ],
    _constraint_schema(
        "Coincident",
        {"first": _POINT, "second": _POINT},
        ["first", "second"],
    ),
    _constraint_schema(
        "PointOnObject",
        {"point": _POINT, "object": _GEOMETRY},
        ["point", "object"],
    ),
    _constraint_schema(
        "Symmetric",
        {"first": _POINT, "second": _POINT, "about": _POINT},
        ["first", "second", "about"],
    ),
    *[
        _constraint_schema(
            kind,
            {
                "geometry": _GEOMETRY,
                "size_mm": {"type": "number", "exclusiveMinimum": 0},
            },
            ["geometry", "size_mm"],
        )
        for kind in ("Radius", "Diameter")
    ],
    _constraint_schema(
        "Distance",
        {
            "geometry": _GEOMETRY,
            "distance_mm": {"type": "number", "exclusiveMinimum": 0},
        },
        ["geometry", "distance_mm"],
    ),
    _constraint_schema(
        "Distance",
        {
            "first": _POINT,
            "second": _POINT,
            "distance_mm": {"type": "number", "exclusiveMinimum": 0},
        },
        ["first", "second", "distance_mm"],
    ),
    *[
        _constraint_schema(
            kind,
            {"point": _POINT, "coordinate_mm": {"type": "number"}},
            ["point", "coordinate_mm"],
        )
        for kind in ("DistanceX", "DistanceY")
    ],
    *[
        _constraint_schema(
            kind,
            {"first": _POINT, "second": _POINT, "distance_mm": {"type": "number"}},
            ["first", "second", "distance_mm"],
        )
        for kind in ("DistanceX", "DistanceY")
    ],
    _constraint_schema(
        "Angle",
        {"geometry": _GEOMETRY, "angle_degrees": {"type": "number"}},
        ["geometry", "angle_degrees"],
    ),
    _constraint_schema(
        "Angle",
        {"first": _POINT, "second": _POINT, "angle_degrees": {"type": "number"}},
        ["first", "second", "angle_degrees"],
    ),
    _constraint_schema(
        "Lock",
        {"point": _POINT, "position_mm": _POSITION},
        ["point", "position_mm"],
    ),
]


TOOL_SPEC = {
    "name": "sketcher.constrain",
    "safety": "SAFE_WRITE",
    "edit_modes": ["sketch"],
    "description": (
        "Apply one validated batch of native Sketcher constraints. Each item has a "
        "constraint-specific shape with semantic point roles; the complete batch is "
        "validated against the open sketch before any constraint is added. Prefer "
        "meaningful dimensions and geometric relationships that preserve parametric intent."
    ),
    "contextual": True,
    "parameters": {
        "type": "object",
        "properties": {
            "constraints": {
                "type": "array",
                "minItems": 1,
                "description": (
                    "One atomic batch of typed geometric or dimensional constraints "
                    "for the active sketch."
                ),
                "items": {"oneOf": _CONSTRAINT_SCHEMAS},
            },
        },
        "required": ["constraints"],
        "additionalProperties": False,
    },
}


def _reference_arguments(prefix: str, reference: Any) -> dict[str, Any]:
    if isinstance(reference, dict):
        geometry = reference.get("geometry")
        point = reference.get("point")
    else:
        geometry = reference
        point = None
    if isinstance(geometry, bool):
        raise ValueError(f"{prefix}.geometry must be an index or stable handle.")
    result: dict[str, Any] = {}
    if isinstance(geometry, int):
        result[f"{prefix}_geometry"] = geometry
    elif isinstance(geometry, str) and geometry.strip():
        result[f"{prefix}_geometry_handle"] = geometry.strip()
    else:
        raise ValueError(f"{prefix}.geometry must be an index or stable handle.")
    if point is not None:
        result[f"{prefix}_point"] = str(point)
    return result


def _arguments_for_item(item: Any, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError(f"Constraint item {index} must be an object.")
    canonical = {name.casefold(): name for name in _CONSTRAINT_TYPES}
    constraint_type = canonical.get(str(item.get("type") or "").casefold())
    if constraint_type is None:
        raise ValueError(f"Constraint item {index} has an unsupported type.")
    arguments: dict[str, Any] = {"constraint_type": constraint_type}
    if constraint_type in {"Horizontal", "Vertical", "Block", "Radius", "Diameter"}:
        arguments.update(_reference_arguments("first", item.get("geometry")))
    elif constraint_type in {"Parallel", "Perpendicular", "Tangent", "Equal"}:
        arguments.update(_reference_arguments("first", item.get("first")))
        arguments.update(_reference_arguments("second", item.get("second")))
    elif constraint_type == "Coincident":
        arguments.update(_reference_arguments("first", item.get("first")))
        arguments.update(_reference_arguments("second", item.get("second")))
    elif constraint_type == "PointOnObject":
        arguments.update(_reference_arguments("first", item.get("point")))
        arguments.update(_reference_arguments("second", item.get("object")))
    elif constraint_type == "Symmetric":
        arguments.update(_reference_arguments("first", item.get("first")))
        arguments.update(_reference_arguments("second", item.get("second")))
        arguments.update(_reference_arguments("third", item.get("about")))
    elif constraint_type == "Distance":
        if "geometry" in item:
            arguments.update(_reference_arguments("first", item.get("geometry")))
        else:
            arguments.update(_reference_arguments("first", item.get("first")))
            arguments.update(_reference_arguments("second", item.get("second")))
        arguments["value"] = item.get("distance_mm")
    elif constraint_type in {"DistanceX", "DistanceY"}:
        if "point" in item:
            arguments.update(_reference_arguments("first", item.get("point")))
            arguments["value"] = item.get("coordinate_mm")
        else:
            arguments.update(_reference_arguments("first", item.get("first")))
            arguments.update(_reference_arguments("second", item.get("second")))
            arguments["value"] = item.get("distance_mm")
    elif constraint_type == "Angle":
        if "geometry" in item:
            arguments.update(_reference_arguments("first", item.get("geometry")))
        else:
            arguments.update(_reference_arguments("first", item.get("first")))
            arguments.update(_reference_arguments("second", item.get("second")))
        arguments["value"] = item.get("angle_degrees")
    elif constraint_type == "Lock":
        arguments.update(_reference_arguments("first", item.get("point")))
        position = item.get("position_mm")
        if not isinstance(position, list) or len(position) != 2:
            raise ValueError(f"Constraint item {index} position_mm must be [x, y].")
        arguments["x"] = position[0]
        arguments["y"] = position[1]
    if constraint_type in {"Radius", "Diameter"}:
        arguments["value"] = item.get("size_mm")
    return arguments


def run(service: Any, constraints: list[dict[str, Any]]) -> dict[str, Any]:
    sketch = get_sketch(service)
    if sketch is None:
        return tool_failure(
            TOOL_SPEC["name"],
            "NO_ACTIVE_SKETCH",
            "edit_state",
            "No Sketcher sketch is currently open for editing.",
            requested={"constraints": constraints},
            required_changes=[{"action": "open_target_sketch"}],
        )
    prepared_items: list[dict[str, Any]] = []
    for index, item in enumerate(constraints):
        try:
            arguments = _arguments_for_item(item, index)
        except ValueError as exc:
            return tool_failure(
                TOOL_SPEC["name"],
                "CONSTRAINT_ITEM_INVALID",
                "precondition",
                str(exc),
                requested={"constraints": constraints},
                observed={
                    "failed_item_index": index,
                    "failed_item": item,
                    "validated_item_count": len(prepared_items),
                    "solver_status": solver_status(service, sketch),
                },
                candidates={
                    "geometry": geometry_inventory(service, sketch),
                    "constraints": _constraint_table(service, sketch),
                },
                required_changes=[{"constraint_item_index": index}],
            )
        prepared = add_constraint.prepare_constraint(service, sketch, **arguments)
        if not prepared.get("ok"):
            return tool_failure(
                TOOL_SPEC["name"],
                "CONSTRAINT_REFERENCE_INVALID",
                "precondition",
                str(
                    prepared.get("error")
                    or f"Constraint item {index} is invalid."
                ),
                requested={"constraints": constraints},
                normalized={"prepared_items": len(prepared_items)},
                observed={
                    "failed_item_index": index,
                    "failed_item": item,
                    "details": {
                    key: value
                    for key, value in prepared.items()
                    if key != "constraints"
                    },
                    "solver_status": solver_status(service, sketch),
                },
                candidates={
                    "geometry": geometry_inventory(service, sketch),
                    "constraints": _constraint_table(service, sketch),
                },
                required_changes=[{"constraint_item_index": index}],
            )
        prepared_items.append(prepared)

    proposed_constraints = [
        native
        for prepared in prepared_items
        for native in list(prepared.get("constraints") or [])
    ]
    try:
        feasibility = sketch.diagnoseAdditionalConstraints(proposed_constraints)
    except Exception as exc:
        return tool_failure(
            TOOL_SPEC["name"],
            "CONSTRAINT_FEASIBILITY_CHECK_FAILED",
            "native_call",
            str(exc),
            requested={"constraints": constraints},
            observed={
                "exception_type": exc.__class__.__name__,
                "solver_status": solver_status(service, sketch),
            },
        )
    if not isinstance(feasibility, dict):
        return tool_failure(
            TOOL_SPEC["name"],
            "CONSTRAINT_FEASIBILITY_RESULT_INVALID",
            "native_call",
            "FreeCAD did not return structured constraint feasibility data.",
            requested={"constraints": constraints},
            observed={"received_type": type(feasibility).__name__},
        )
    if not bool(feasibility.get("accepted")):
        proposed_index_map = _proposed_index_map(prepared_items, feasibility)
        return tool_failure(
            TOOL_SPEC["name"],
            "CONSTRAINT_BATCH_REJECTED_BY_SOLVER",
            "precondition",
            "FreeCAD's solver rejected the proposed constraint batch without adding it.",
            requested={"constraints": constraints},
            normalized={
                "native_constraints": [
                    _native_constraint_descriptor(item) for item in proposed_constraints
                ],
                "proposed_index_map": proposed_index_map,
            },
            observed={
                "feasibility": feasibility,
                "solver_status": solver_status(service, sketch),
            },
            candidates={
                "geometry": geometry_inventory(service, sketch),
                "constraints": _constraint_table(service, sketch),
            },
            required_changes=[
                {
                    "constraint_item_index": item["item_index"],
                    "hypothetical_constraint_indices": item["constraint_indices"],
                }
                for item in proposed_index_map
                if any(
                    index
                    in set(feasibility.get("conflicting_constraint_indices") or [])
                    | set(feasibility.get("redundant_constraint_indices") or [])
                    | set(
                        feasibility.get("partially_redundant_constraint_indices") or []
                    )
                    | set(feasibility.get("malformed_constraint_indices") or [])
                    for index in item["constraint_indices"]
                )
            ],
        )

    def _add() -> dict[str, Any]:
        target = get_sketch(service, sketch.Name)
        if target is None:
            raise RuntimeError(f"Sketch not found: {sketch.Name}")
        before_count = len(getattr(target, "Constraints", []) or [])
        solver_before = solver_status(service, target)
        conflict_before = set(solver_before.get("conflicting_constraint_indices") or [])
        redundant_before = set(solver_before.get("redundant_constraint_indices") or [])
        retained_indices: list[int] = []
        item_results: list[dict[str, Any]] = []
        stopped_at_item: int | None = None
        for item_index, prepared in enumerate(prepared_items):
            item_solver_before = solver_status(service, target)
            native_requested = [
                _native_constraint_descriptor(item)
                for item in list(prepared.get("constraints") or [])
            ]
            raw_indices = target.addConstraint(prepared["constraints"])
            normalized_indices = add_constraint._constraint_indices(raw_indices)
            indices = (
                list(normalized_indices)
                if isinstance(normalized_indices, list)
                else [int(normalized_indices)]
            )
            retained_indices.extend(index for index in indices if index >= 0)
            item_solver_after = solver_status(service, target)
            new_conflicts = sorted(
                set(item_solver_after.get("conflicting_constraint_indices") or [])
                - conflict_before
            )
            new_redundant = sorted(
                set(item_solver_after.get("redundant_constraint_indices") or [])
                - redundant_before
            )
            retained = [
                service._constraint_summary(target.Constraints[index], index)
                for index in indices
                if 0 <= index < len(target.Constraints)
            ]
            item_result = {
                "item_index": item_index,
                "requested": constraints[item_index],
                "normalized": prepared.get("resolved"),
                "native_constraints": native_requested,
                "retained_constraint_indices": indices,
                "retained_constraints": retained,
                "solver_before": item_solver_before,
                "solver_after": item_solver_after,
                "degrees_of_freedom_delta": _dof_delta(
                    item_solver_before,
                    item_solver_after,
                ),
                "new_conflicting_constraint_indices": new_conflicts,
                "new_redundant_constraint_indices": new_redundant,
                "accepted": bool(indices)
                and not new_conflicts
                and not new_redundant,
            }
            item_results.append(item_result)
            if not item_result["accepted"]:
                stopped_at_item = item_index
                break
        solver_after = solver_status(service, target)
        return {
            "sketch": target.Name,
            "constraint_index": retained_indices,
            "constraint_count_before": before_count,
            "constraint_count": len(getattr(target, "Constraints", []) or []),
            "constraints_requested": sum(
                len(item.get("constraints") or []) for item in prepared_items
            ),
            "constraints_added": len(retained_indices),
            "items_requested": len(prepared_items),
            "items_added": len(item_results),
            "resolved": [item["resolved"] for item in prepared_items],
            "constraint_types": [item["constraint_type"] for item in prepared_items],
            "solver_before": solver_before,
            "solver_after": solver_after,
            "degrees_of_freedom_delta": _dof_delta(solver_before, solver_after),
            "batch_items": item_results,
            "stopped_at_item": stopped_at_item,
            "retained_constraint_indices": retained_indices,
            "feasibility": feasibility,
        }

    def _verify(result: dict[str, Any]) -> dict[str, Any]:
        item_results = list(result.get("batch_items") or [])
        rejected = [item for item in item_results if not item.get("accepted")]
        all_items_executed = len(item_results) == len(prepared_items)
        return {
            "ok": all_items_executed and not rejected,
            "checks": [
                {
                    "name": "all_batch_items_executed",
                    "ok": all_items_executed,
                    "executed": len(item_results),
                    "requested": len(prepared_items),
                },
                {
                    "name": "solver_accepted_all_constraints",
                    "ok": not rejected,
                    "rejected_item_indices": [item["item_index"] for item in rejected],
                },
            ],
            "error": (
                "FreeCAD retained a conflicting or redundant constraint; the batch "
                "stopped at the reported item and later items were not attempted."
                if rejected
                else "Not every constraint item was executed."
                if not all_items_executed
                else None
            ),
        }

    transaction = run_freecad_transaction(
        "Apply Sketcher constraint batch",
        _add,
        _verify,
    )
    response = active_response(service, sketch, transaction)
    response["requested"] = {"constraints": constraints}
    return response


def _constraint_table(service: Any, sketch: Any) -> list[dict[str, Any]]:
    return [
        service._constraint_summary(item, index)
        for index, item in enumerate(list(getattr(sketch, "Constraints", []) or []))
    ]


def _native_constraint_descriptor(constraint: Any) -> dict[str, Any]:
    descriptor: dict[str, Any] = {}
    for name in (
        "Type",
        "First",
        "FirstPos",
        "Second",
        "SecondPos",
        "Third",
        "ThirdPos",
        "Value",
    ):
        try:
            value = getattr(constraint, name)
        except Exception:
            continue
        descriptor[name] = str(value) if name == "Type" else value
    return descriptor


def _dof_delta(before: dict[str, Any], after: dict[str, Any]) -> int | None:
    before_value = before.get("degrees_of_freedom")
    after_value = after.get("degrees_of_freedom")
    if before_value is None or after_value is None:
        return None
    return int(after_value) - int(before_value)


def _proposed_index_map(
    prepared_items: list[dict[str, Any]],
    feasibility: dict[str, Any],
) -> list[dict[str, Any]]:
    next_index = int(feasibility.get("first_proposed_constraint_index") or 0)
    result = []
    for item_index, item in enumerate(prepared_items):
        count = len(item.get("constraints") or [])
        indices = list(range(next_index, next_index + count))
        result.append(
            {
                "item_index": item_index,
                "constraint_type": item.get("constraint_type"),
                "constraint_indices": indices,
            }
        )
        next_index += count
    return result
