# SPDX-License-Identifier: LGPL-2.1-or-later

"""Consolidated native Sketcher constraint editing and lookup tool."""

from __future__ import annotations

from typing import Any

from .common import (
    active_response,
    get_sketch,
    profile_validation,
    resolve_constraint_index,
    run_freecad_transaction,
    solver_status,
    validate_constraint_index,
)


_TARGET = {
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "by": {"type": "string", "const": "index"},
                "index": {"type": "integer", "minimum": 0},
            },
            "required": ["by", "index"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "by": {"type": "string", "const": "name"},
                "name": {"type": "string", "minLength": 1},
            },
            "required": ["by", "name"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "by": {"type": "string", "const": "handle"},
                "handle": {"type": "string", "pattern": "^(constraint:|name:).+"},
            },
            "required": ["by", "handle"],
            "additionalProperties": False,
        },
    ],
    "description": "Exactly one live constraint selector.",
}


def _action_schema(
    operation: str,
    properties: dict[str, Any] | None = None,
    required: list[str] | None = None,
) -> dict[str, Any]:
    fields = {
        "operation": {"type": "string", "const": operation},
        "target": _TARGET,
        **(properties or {}),
    }
    return {
        "type": "object",
        "properties": fields,
        "required": ["operation", "target", *(required or [])],
        "additionalProperties": False,
    }


TOOL_SPEC = {
    "name": "sketcher.edit_constraint",
    "safety": "SAFE_WRITE",
    "edit_modes": ["sketch"],
    "description": (
        "Edit or inspect exactly one existing Sketcher constraint. Each operation "
        "has its own argument shape and one explicit index, name, or handle target. "
        "Creates nothing; use sketcher.constrain for new constraints."
    ),
    "contextual": True,
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "oneOf": [
                    _action_schema("get"),
                    _action_schema(
                        "set_value",
                        {"value": {"type": "number"}},
                        ["value"],
                    ),
                    _action_schema(
                        "set_name",
                        {"new_name": {"type": "string", "minLength": 1}},
                        ["new_name"],
                    ),
                    _action_schema(
                        "set_driving",
                        {"driving": {"type": "boolean"}},
                        ["driving"],
                    ),
                    _action_schema(
                        "set_expression",
                        {
                            "expression": {
                                "type": "string",
                                "description": "Expression text; an empty string clears it.",
                            }
                        },
                        ["expression"],
                    ),
                ],
                "description": "One exact constraint read or edit operation.",
            },
        },
        "required": ["action"],
        "additionalProperties": False,
    },
}


DIMENSION_CONSTRAINTS = {
    "Distance",
    "DistanceX",
    "DistanceY",
    "Radius",
    "Diameter",
    "Angle",
}


def _resolve_target(
    service: Any,
    target: Any,
) -> tuple[Any | None, int | None, dict[str, Any] | None]:
    sketch = get_sketch(service)
    available = _constraint_table(service, sketch)
    if sketch is None:
        return (
            None,
            None,
            {
                "ok": False,
                "error": "No Sketcher sketch is currently open for editing.",
                "requested": {"target": target},
                "available_constraints": available,
            },
        )
    if not isinstance(target, dict):
        return sketch, None, {
            "ok": False,
            "error": "target must be one structured constraint selector.",
            "requested": {"target": target},
            "available_constraints": available,
        }
    by = str(target.get("by") or "").strip().lower()
    constraint_index = int(target["index"]) if by == "index" else None
    constraint_name = str(target["name"]) if by == "name" else None
    constraint_handle = str(target["handle"]) if by == "handle" else None
    try:
        index = resolve_constraint_index(
            sketch, constraint_index, constraint_name, constraint_handle
        )
    except (ValueError, TypeError, RuntimeError, AttributeError) as exc:
        return (
            sketch,
            None,
            {
                "ok": False,
                "error": str(exc),
                "constraint_index": constraint_index,
                "constraint_name": constraint_name,
                "constraint_handle": constraint_handle,
                "available_constraints": available,
            },
        )
    invalid = validate_constraint_index(sketch, index)
    if invalid:
        return sketch, None, invalid
    return sketch, int(index), None


def _constraint_table(service: Any, sketch: Any | None) -> list[dict[str, Any]]:
    if sketch is None:
        return []
    try:
        return list(
            service.sketcher_summary(getattr(sketch, "Name", None)).get(
                "constraints", []
            )
        )
    except (RuntimeError, AttributeError, KeyError, TypeError) as exc:
        raise RuntimeError(
            f"Could not read the live constraint table for sketch "
            f"{getattr(sketch, 'Name', '<unnamed>')}: {exc}"
        ) from exc


def _native_property_status(constraint: Any) -> dict[str, Any]:
    constraint_type = str(getattr(constraint, "Type", ""))
    dimensional = constraint_type in DIMENSION_CONSTRAINTS
    return {
        "constraint_type": constraint_type,
        "supports_value": dimensional,
        "supports_expression": dimensional,
        "supports_driving_state": dimensional,
        "supports_name": True,
        "allowed_actions": [
            "get",
            "set_name",
            *(
                ["set_value", "set_driving", "set_expression"]
                if dimensional
                else []
            ),
        ],
    }


def _set_value(
    service: Any, sketch: Any, index: int, value: float | None
) -> dict[str, Any]:
    if value is None:
        return {"ok": False, "error": "value is required for action=set_value."}
    constraint = list(getattr(sketch, "Constraints", []))[index]
    constraint_type = str(getattr(constraint, "Type", ""))
    if constraint_type not in DIMENSION_CONSTRAINTS:
        return {
            "ok": False,
            "error": f"Constraint is not a dimension datum: {constraint_type}",
            "constraint_index": index,
            "constraint_type": constraint_type,
        }
    if float(value) <= 0 and constraint_type not in {"Angle", "DistanceX", "DistanceY"}:
        return {"ok": False, "error": f"{constraint_type} values must be positive."}

    def _apply() -> dict[str, Any]:
        import FreeCAD as App

        target = get_sketch(service, sketch.Name)
        if target is None:
            raise RuntimeError(f"Sketch not found: {sketch.Name}")
        before = float(
            getattr(list(getattr(target, "Constraints", []))[index], "Value", 0.0)
        )
        units = App.Units.Angle if constraint_type == "Angle" else App.Units.Length
        target.setDatum(index, App.Units.Quantity(float(value), units))
        after = float(
            getattr(list(getattr(target, "Constraints", []))[index], "Value", 0.0)
        )
        return {
            "sketch": target.Name,
            "action": "set_value",
            "constraint_index": index,
            "constraint_type": constraint_type,
            "before": before,
            "after": after,
        }

    return active_response(
        service,
        sketch,
        run_freecad_transaction(f"Edit Sketcher constraint {index} value", _apply),
    )


def _set_name(
    service: Any, sketch: Any, index: int, new_name: str | None
) -> dict[str, Any]:
    if not new_name or not str(new_name).strip():
        return {"ok": False, "error": "new_name is required for action=set_name."}

    def _apply() -> dict[str, Any]:
        import FreeCAD as App

        target = get_sketch(service, sketch.Name)
        if target is None:
            raise RuntimeError(f"Sketch not found: {sketch.Name}")
        before = getattr(list(getattr(target, "Constraints", []))[index], "Name", "")
        target.renameConstraint(index, str(new_name))
        after = getattr(list(getattr(target, "Constraints", []))[index], "Name", "")
        return {
            "sketch": target.Name,
            "action": "set_name",
            "constraint_index": index,
            "old_constraint_name": before,
            "constraint_name": after,
        }

    return active_response(
        service,
        sketch,
        run_freecad_transaction(f"Rename Sketcher constraint {index}", _apply),
    )


def _set_driving(
    service: Any, sketch: Any, index: int, driving: bool | None
) -> dict[str, Any]:
    if driving is None:
        return {"ok": False, "error": "driving is required for action=set_driving."}

    def _apply() -> dict[str, Any]:
        import FreeCAD as App

        target = get_sketch(service, sketch.Name)
        if target is None:
            raise RuntimeError(f"Sketch not found: {sketch.Name}")
        before_constraint = list(getattr(target, "Constraints", []))[index]
        before = bool(
            getattr(
                before_constraint,
                "Driving",
                getattr(before_constraint, "isDriving", True),
            )
        )
        target.setDriving(index, bool(driving))
        after_constraint = list(getattr(target, "Constraints", []))[index]
        after = bool(
            getattr(
                after_constraint,
                "Driving",
                getattr(after_constraint, "isDriving", True),
            )
        )
        return {
            "sketch": target.Name,
            "action": "set_driving",
            "constraint_index": index,
            "before_driving": before,
            "driving": after,
        }

    return active_response(
        service,
        sketch,
        run_freecad_transaction(
            f"Set Sketcher constraint {index} driving state", _apply
        ),
    )


def _set_expression(
    service: Any, sketch: Any, index: int, expression: str | None
) -> dict[str, Any]:
    if expression is None:
        return {
            "ok": False,
            "error": "expression is required for action=set_expression (empty string clears).",
        }

    def _apply() -> dict[str, Any]:
        import FreeCAD as App

        target = get_sketch(service, sketch.Name)
        if target is None:
            raise RuntimeError(f"Sketch not found: {sketch.Name}")
        path = f"Constraints[{index}]"
        clean = str(expression).strip()
        target.setExpression(path, clean or None)
        expressions: dict[str, str] = {}
        try:
            expressions = {
                str(expr_path): str(expr) for expr_path, expr in target.ExpressionEngine
            }
        except (AttributeError, TypeError, ValueError):
            expressions = {}
        return {
            "sketch": target.Name,
            "action": "set_expression",
            "constraint_index": index,
            "expression_path": path,
            "expression": expressions.get(path),
        }

    return active_response(
        service,
        sketch,
        run_freecad_transaction(f"Set Sketcher constraint {index} expression", _apply),
    )


def _get(service: Any, sketch: Any, index: int) -> dict[str, Any]:
    constraints = service.sketcher_summary(getattr(sketch, "Name", None)).get(
        "constraints", []
    )
    constraint = next(
        (item for item in constraints if item.get("index") == index), None
    )
    return {
        "ok": True,
        "action": "get",
        "sketch": getattr(sketch, "Name", None),
        "constraint_index": index,
        "constraint": constraint,
        "solver_status": solver_status(service, sketch),
        "profile_validation": profile_validation(service, sketch),
    }


def run(service: Any, action: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(action, dict):
        return {
            "ok": False,
            "error": "action must be one structured constraint operation.",
            "requested": {"action": action},
        }
    clean_action = str(action.get("operation") or "").strip().lower()
    actions = {"set_value", "set_name", "set_driving", "set_expression", "get"}
    if clean_action not in actions:
        return {
            "ok": False,
            "error": f"Unsupported edit_constraint action: {clean_action}",
            "supported": sorted(actions),
        }
    sketch, index, failure = _resolve_target(service, action.get("target"))
    if failure is not None:
        return failure
    assert sketch is not None and index is not None
    constraint = list(getattr(sketch, "Constraints", []))[index]
    property_status = _native_property_status(constraint)
    if clean_action not in property_status["allowed_actions"]:
        return {
            "ok": False,
            "error": (
                f"Constraint type {property_status['constraint_type']} does not "
                f"support action {clean_action}."
            ),
            "requested": action,
            "resolved_target": _constraint_table(service, sketch)[index],
            "native_property_status": property_status,
            "allowed_values": property_status["allowed_actions"],
            "available_constraints": _constraint_table(service, sketch),
        }
    result: dict[str, Any]
    if clean_action == "set_value":
        result = _set_value(service, sketch, index, action.get("value"))
    elif clean_action == "set_name":
        result = _set_name(service, sketch, index, action.get("new_name"))
    elif clean_action == "set_driving":
        result = _set_driving(service, sketch, index, action.get("driving"))
    elif clean_action == "set_expression":
        result = _set_expression(service, sketch, index, action.get("expression"))
    else:
        result = _get(service, sketch, index)
    if isinstance(result, dict):
        result.setdefault("resolved_target", _constraint_table(service, sketch)[index])
        result.setdefault("native_property_status", property_status)
        result.setdefault("allowed_values", property_status["allowed_actions"])
        result.setdefault("available_constraints", _constraint_table(service, sketch))
    return result
