# SPDX-License-Identifier: LGPL-2.1-or-later

"""Internal native constraint builder used by sketcher.constrain."""

from __future__ import annotations

from typing import Any

from .common import (
    active_response,
    get_sketch,
    no_sketch,
    resolve_geometry_index,
    run_freecad_transaction,
)
from .constrain_common import optional_point_position

SUPPORTED_CONSTRAINTS = {
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
}


def _error(message: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "error": message,
        "retry_same_call": False,
    }
    payload.update(extra)
    return payload


def _required_int(name: str, raw_value: int | None, constraint_type: str) -> int:
    if raw_value is None:
        raise ValueError(f"{name} is required for {constraint_type}.")
    return int(raw_value)


def _positive_value(name: str, raw_value: float | None, constraint_type: str) -> float:
    if raw_value is None:
        raise ValueError(f"{name} is required for {constraint_type}.")
    number = float(raw_value)
    if number <= 0:
        raise ValueError(f"{name} must be positive for {constraint_type}.")
    return number


def _number_value(name: str, raw_value: float | None, constraint_type: str) -> float:
    if raw_value is None:
        raise ValueError(f"{name} is required for {constraint_type}.")
    return float(raw_value)


def _constraint_indices(raw_value: Any) -> int | list[int]:
    if isinstance(raw_value, int):
        return int(raw_value)
    if isinstance(raw_value, (list, tuple)):
        flattened: list[int] = []
        for item in raw_value:
            if isinstance(item, int):
                flattened.append(int(item))
            elif isinstance(item, (list, tuple)):
                flattened.extend(int(value) for value in item)
            else:
                flattened.append(int(item))
        return flattened
    return int(raw_value)


def _resolve_point_roles(
    sketch: Any,
    constraint_type: str,
    first_point: str | None,
    first_geometry_handle: str | None,
    first_geometry: int | None,
    second_point: str | None,
    second_geometry_handle: str | None,
    second_geometry: int | None,
    third_point: str | None,
    third_geometry_handle: str | None,
    third_geometry: int | None,
) -> tuple[int | None, int | None, int | None]:
    """Resolve semantic point roles (start/end/center/...) into raw Sketcher pos ints.

    The public tool contract accepts semantic point roles only. Native Sketcher
    position integers are resolved internally here and never exposed as
    user/model arguments.
    """
    first_pos = None
    if first_point is not None:
        first_pos = optional_point_position(
            first_point,
            first_geometry_handle,
            "whole",
            _geometry_kind(sketch, first_geometry),
        )
    second_pos = None
    if second_point is not None:
        second_pos = optional_point_position(
            second_point,
            second_geometry_handle,
            "whole",
            _geometry_kind(sketch, second_geometry),
        )
    third_pos = None
    if third_point is not None:
        third_pos = optional_point_position(
            third_point,
            third_geometry_handle,
            "whole",
            _geometry_kind(sketch, third_geometry),
        )
    return first_pos, second_pos, third_pos


def _geometry_kind(sketch: Any, geometry_index: int | None) -> str | None:
    if geometry_index is None or int(geometry_index) < 0:
        return None
    geometry = list(getattr(sketch, "Geometry", []) or [])
    index = int(geometry_index)
    if index >= len(geometry):
        return None
    return geometry[index].__class__.__name__


def _validate_point_role_contract(
    constraint_type: str,
    first_point: str | None,
    has_second: bool,
    second_point: str | None,
    has_third: bool,
    third_point: str | None,
) -> dict[str, Any] | None:
    missing: list[str] = []
    unused: list[str] = []
    if constraint_type == "Coincident":
        if first_point is None:
            missing.append("first_point")
        if second_point is None:
            missing.append("second_point")
    elif constraint_type == "PointOnObject":
        if first_point is None:
            missing.append("first_point")
        if second_point is not None:
            unused.append("second_point")
    elif constraint_type == "Symmetric":
        if first_point is None:
            missing.append("first_point")
        if second_point is None:
            missing.append("second_point")
        if third_point is None:
            missing.append("third_point")
    elif constraint_type == "Lock":
        if first_point is None:
            missing.append("first_point")
        if second_point is not None:
            unused.append("second_point")
        if third_point is not None:
            unused.append("third_point")
    elif constraint_type in {"DistanceX", "DistanceY"}:
        if first_point is None:
            missing.append("first_point")
        if has_second and second_point is None:
            missing.append("second_point")
        if not has_second and second_point is not None:
            unused.append("second_point")
    elif constraint_type == "Distance":
        if has_second:
            if first_point is None:
                missing.append("first_point")
            if second_point is None:
                missing.append("second_point")
        else:
            if first_point is not None:
                unused.append("first_point")
            if second_point is not None:
                unused.append("second_point")
    elif constraint_type == "Angle":
        if not has_second and (first_point is not None or second_point is not None):
            if first_point is not None:
                unused.append("first_point")
            if second_point is not None:
                unused.append("second_point")
        if has_second:
            if first_point is None:
                missing.append("first_point")
            if second_point is None:
                missing.append("second_point")
    else:
        for field_name, field_value in (
            ("first_point", first_point),
            ("second_point", second_point),
            ("third_point", third_point),
        ):
            if field_value is not None:
                unused.append(field_name)
    if not has_third and third_point is not None:
        unused.append("third_point")
    if missing:
        return _error(
            f"{constraint_type} requires explicit point role(s): {', '.join(missing)}.",
            constraint_type=constraint_type,
            missing_point_roles=missing,
        )
    if unused:
        return _error(
            f"{constraint_type} does not use point role(s): {', '.join(sorted(set(unused)))}.",
            constraint_type=constraint_type,
            unused_point_roles=sorted(set(unused)),
        )
    return None


def prepare_constraint(
    service: Any,
    sketch: Any,
    *,
    constraint_type: str | None = None,
    first_geometry: int | None = None,
    first_geometry_handle: str | None = None,
    first_point: str | None = None,
    second_geometry: int | None = None,
    second_geometry_handle: str | None = None,
    second_point: str | None = None,
    third_geometry: int | None = None,
    third_geometry_handle: str | None = None,
    third_point: str | None = None,
    value: float | None = None,
    x: float | None = None,
    y: float | None = None,
) -> dict[str, Any]:
    """Validate and construct native constraints without mutating the sketch."""
    if constraint_type is None or not str(constraint_type).strip():
        return _error("constraint_type is required.")
    clean_type = str(constraint_type or "").strip()
    if clean_type not in SUPPORTED_CONSTRAINTS:
        return _error(
            f"Unsupported Sketcher constraint type: {clean_type}",
            supported=sorted(SUPPORTED_CONSTRAINTS),
        )
    try:
        first_geometry = resolve_geometry_index(
            service, sketch, first_geometry, first_geometry_handle
        )
        if second_geometry is not None or second_geometry_handle:
            second_geometry = resolve_geometry_index(
                service, sketch, second_geometry, second_geometry_handle
            )
        if third_geometry is not None or third_geometry_handle:
            third_geometry = resolve_geometry_index(
                service, sketch, third_geometry, third_geometry_handle
            )
    except Exception as exc:
        return _error(
            str(exc),
            first_geometry=first_geometry,
            first_geometry_handle=first_geometry_handle,
            second_geometry=second_geometry,
            second_geometry_handle=second_geometry_handle,
            third_geometry=third_geometry,
            third_geometry_handle=third_geometry_handle,
        )
    for role, geometry_index in (
        ("first", first_geometry),
        ("second", second_geometry),
        ("third", third_geometry),
    ):
        if geometry_index is None or int(geometry_index) < 0:
            continue
        if int(geometry_index) >= len(getattr(sketch, "Geometry", []) or []):
            return _error(
                f"{role} geometry index {geometry_index} is outside the active sketch.",
                geometry_count=len(getattr(sketch, "Geometry", []) or []),
            )
    point_role_error = _validate_point_role_contract(
        clean_type,
        first_point,
        second_geometry is not None,
        second_point,
        third_geometry is not None,
        third_point,
    )
    if point_role_error is not None:
        return point_role_error
    try:
        first_pos, second_pos, third_pos = _resolve_point_roles(
            sketch,
            clean_type,
            first_point,
            first_geometry_handle,
            first_geometry,
            second_point,
            second_geometry_handle,
            second_geometry,
            third_point,
            third_geometry_handle,
            third_geometry,
        )
    except ValueError as exc:
        return _error(
            str(exc),
            constraint_type=clean_type,
            first_geometry=first_geometry,
            second_geometry=second_geometry,
            third_geometry=third_geometry,
        )

    try:
        import FreeCAD as App
        import Sketcher

        first = _required_int("first_geometry", first_geometry, clean_type)
        if clean_type in {"Horizontal", "Vertical", "Block"}:
            constraints = [Sketcher.Constraint(clean_type, first)]
        elif clean_type in {"Parallel", "Perpendicular", "Tangent", "Equal"}:
            constraints = [
                Sketcher.Constraint(
                    clean_type,
                    first,
                    _required_int("second_geometry", second_geometry, clean_type),
                )
            ]
        elif clean_type == "Symmetric":
            constraints = [
                Sketcher.Constraint(
                    clean_type,
                    first,
                    _required_int("first_point", first_pos, clean_type),
                    _required_int("second_geometry", second_geometry, clean_type),
                    _required_int("second_point", second_pos, clean_type),
                    _required_int("third_geometry", third_geometry, clean_type),
                    _required_int("third_point", third_pos, clean_type),
                )
            ]
        elif clean_type == "Coincident":
            constraints = [
                Sketcher.Constraint(
                    clean_type,
                    first,
                    _required_int("first_point", first_pos, clean_type),
                    _required_int("second_geometry", second_geometry, clean_type),
                    _required_int("second_point", second_pos, clean_type),
                )
            ]
        elif clean_type == "PointOnObject":
            constraints = [
                Sketcher.Constraint(
                    clean_type,
                    first,
                    _required_int("first_point", first_pos, clean_type),
                    _required_int("second_geometry", second_geometry, clean_type),
                )
            ]
        elif clean_type in {"Radius", "Diameter"}:
            constraints = [
                Sketcher.Constraint(
                    clean_type, first, _positive_value("value", value, clean_type)
                )
            ]
        elif clean_type == "Distance":
            if (
                first_pos is not None
                and second_geometry is not None
                and second_pos is not None
            ):
                constraints = [
                    Sketcher.Constraint(
                        clean_type,
                        first,
                        int(first_pos),
                        int(second_geometry),
                        int(second_pos),
                        _positive_value("value", value, clean_type),
                    )
                ]
            else:
                constraints = [
                    Sketcher.Constraint(
                        clean_type, first, _positive_value("value", value, clean_type)
                    )
                ]
        elif clean_type in {"DistanceX", "DistanceY"}:
            if second_geometry is not None and second_pos is not None:
                constraints = [
                    Sketcher.Constraint(
                        clean_type,
                        first,
                        _required_int("first_point", first_pos, clean_type),
                        int(second_geometry),
                        int(second_pos),
                        _number_value("value", value, clean_type),
                    )
                ]
            else:
                constraints = [
                    Sketcher.Constraint(
                        clean_type,
                        first,
                        _required_int("first_point", first_pos, clean_type),
                        _number_value("value", value, clean_type),
                    )
                ]
        elif clean_type == "Angle":
            angle = App.Units.Quantity(
                float(_number_value("value", value, clean_type)), App.Units.Angle
            )
            if (
                first_pos is not None
                and second_geometry is not None
                and second_pos is not None
            ):
                constraints = [
                    Sketcher.Constraint(
                        clean_type,
                        first,
                        int(first_pos),
                        int(second_geometry),
                        int(second_pos),
                        angle,
                    )
                ]
            else:
                constraints = [Sketcher.Constraint(clean_type, first, angle)]
        elif clean_type == "Lock":
            constraints = [
                Sketcher.Constraint(
                    "DistanceX",
                    first,
                    _required_int("first_point", first_pos, clean_type),
                    _number_value("x", x, clean_type),
                ),
                Sketcher.Constraint(
                    "DistanceY",
                    first,
                    _required_int("first_point", first_pos, clean_type),
                    _number_value("y", y, clean_type),
                ),
            ]
        else:
            raise ValueError(f"Unsupported Sketcher constraint type: {clean_type}")
    except (TypeError, ValueError, RuntimeError) as exc:
        return _error(str(exc), constraint_type=clean_type)
    return {
        "ok": True,
        "constraint_type": clean_type,
        "constraints": constraints,
        "resolved": {
            "first_geometry": first_geometry,
            "first_point": first_point,
            "second_geometry": second_geometry,
            "second_point": second_point,
            "third_geometry": third_geometry,
            "third_point": third_point,
            "value": value,
            "x": x,
            "y": y,
        },
    }


def run(
    service: Any,
    sketch_name: str | None = None,
    constraint_type: str | None = None,
    first_geometry: int | None = None,
    first_geometry_handle: str | None = None,
    first_point: str | None = None,
    second_geometry: int | None = None,
    second_geometry_handle: str | None = None,
    second_point: str | None = None,
    third_geometry: int | None = None,
    third_geometry_handle: str | None = None,
    third_point: str | None = None,
    value: float | None = None,
    x: float | None = None,
    y: float | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    if kwargs:
        return _error(
            "Unsupported internal constraint parameter(s): "
            + ", ".join(sorted(str(key) for key in kwargs))
            + "."
        )
    sketch = get_sketch(service, sketch_name)
    if sketch is None:
        return {
            **no_sketch(sketch_name),
            "error": "No Sketcher sketch is currently open for editing.",
            "retry_same_call": False,
        }
    prepared = prepare_constraint(
        service,
        sketch,
        constraint_type=constraint_type,
        first_geometry=first_geometry,
        first_geometry_handle=first_geometry_handle,
        first_point=first_point,
        second_geometry=second_geometry,
        second_geometry_handle=second_geometry_handle,
        second_point=second_point,
        third_geometry=third_geometry,
        third_geometry_handle=third_geometry_handle,
        third_point=third_point,
        value=value,
        x=x,
        y=y,
    )
    if not prepared.get("ok"):
        return prepared
    clean_type = str(prepared["constraint_type"])
    constraints = list(prepared["constraints"])

    def _add() -> dict[str, Any]:
        import FreeCAD as App

        target = get_sketch(service, sketch.Name)
        if target is None:
            raise RuntimeError(f"Sketch not found: {sketch.Name}")
        before_count = len(getattr(target, "Constraints", []))
        constraint_index = target.addConstraint(constraints)
        return {
            "sketch": target.Name,
            "constraint_index": _constraint_indices(constraint_index),
            "constraint_type": clean_type,
            "constraint_count_before": before_count,
            "constraint_count": len(getattr(target, "Constraints", [])),
            "constraints_added": len(constraints),
            "resolved": prepared["resolved"],
        }

    return active_response(
        service,
        sketch,
        run_freecad_transaction(f"Add Sketcher {clean_type} constraint", _add),
    )
