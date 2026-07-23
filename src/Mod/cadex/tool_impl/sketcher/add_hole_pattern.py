# SPDX-License-Identifier: LGPL-2.1-or-later

"""Native Sketcher hole-pattern helper."""

from __future__ import annotations

import math
from numbers import Integral, Real
from typing import Any

from .common import (
    active_response,
    geometry_fingerprint,
    geometry_metadata,
    get_sketch,
    no_sketch,
    run_freecad_transaction,
    set_geometry_metadata,
)


TOOL_SPEC = {
    "name": "sketcher.add_hole_pattern",
    "safety": "SAFE_WRITE",
    "edit_modes": ["sketch"],
    "description": (
        "Add one dimensioned Sketcher hole pattern for pockets, drilled holes, "
        "vents, or bolt circles. The selected layout exposes only its own fields."
    ),
    "contextual": True,
    "parameters": {
        "type": "object",
        "properties": {
            "layout": {
                "oneOf": [
                    {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "const": "rectangular"},
                            "center_mm": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 2,
                                "maxItems": 2,
                            },
                            "counts": {
                                "type": "array",
                                "items": {"type": "integer", "minimum": 1},
                                "minItems": 2,
                                "maxItems": 2,
                            },
                            "spacing_mm": {
                                "type": "array",
                                "items": {"type": "number", "minimum": 0},
                                "minItems": 2,
                                "maxItems": 2,
                            },
                        },
                        "required": ["type", "center_mm", "counts", "spacing_mm"],
                        "additionalProperties": False,
                    },
                    {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "const": "linear"},
                            "center_mm": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 2,
                                "maxItems": 2,
                            },
                            "count": {"type": "integer", "minimum": 1},
                            "spacing_mm": {"type": "number", "minimum": 0},
                            "angle_degrees": {"type": "number"},
                        },
                        "required": [
                            "type",
                            "center_mm",
                            "count",
                            "spacing_mm",
                            "angle_degrees",
                        ],
                        "additionalProperties": False,
                    },
                    {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "const": "circular"},
                            "center_mm": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 2,
                                "maxItems": 2,
                            },
                            "count": {"type": "integer", "minimum": 2},
                            "pitch_circle_diameter_mm": {
                                "type": "number",
                                "exclusiveMinimum": 0,
                            },
                            "start_angle_degrees": {"type": "number"},
                        },
                        "required": [
                            "type",
                            "center_mm",
                            "count",
                            "pitch_circle_diameter_mm",
                            "start_angle_degrees",
                        ],
                        "additionalProperties": False,
                    },
                ],
                "description": "Exact rectangular, linear, or circular center layout.",
            },
            "hole_diameter": {
                "type": "number",
                "description": "Hole diameter in mm.",
            },
            "name_prefix": {
                "type": "string",
                "description": "Semantic geometry name prefix.",
            },
            "construction": {
                "type": "boolean",
                "description": "Whether to create holes as construction geometry.",
            },
            "constrain_centers": {
                "type": "boolean",
                "description": "Dimension every generated center to the sketch origin.",
            },
            "equal_diameters": {
                "type": "boolean",
                "description": "Use Equal constraints after dimensioning the first hole.",
            },
        },
        "required": [
            "layout",
            "hole_diameter",
            "name_prefix",
            "construction",
            "constrain_centers",
            "equal_diameters",
        ],
        "additionalProperties": False,
    },
}


def _validation_error(message: str) -> dict[str, Any]:
    return {"ok": False, "error": message, "retry_same_call": False}


def _number_arg(name: str, value: Any) -> tuple[bool, float | str]:
    if value is None:
        return False, f"{name} is required and must be an explicit number."
    if isinstance(value, bool) or not isinstance(value, Real):
        return False, f"{name} must be a number."
    return True, float(value)


def _integer_arg(name: str, value: Any) -> tuple[bool, int | str]:
    if value is None:
        return False, f"{name} is required and must be an explicit integer."
    if isinstance(value, bool) or not isinstance(value, Integral):
        return False, f"{name} must be an integer."
    return True, int(value)


def _bool_arg(name: str, value: Any) -> tuple[bool, bool | str]:
    if value is None:
        return False, f"{name} is required and must be true or false."
    if not isinstance(value, bool):
        return False, f"{name} must be true or false."
    return True, value


def run(
    service: Any,
    layout: dict[str, Any],
    hole_diameter: float | None = None,
    name_prefix: str | None = None,
    construction: bool | None = None,
    constrain_centers: bool | None = None,
    equal_diameters: bool | None = None,
) -> dict[str, Any]:
    if not isinstance(layout, dict):
        return _validation_error("layout must be one structured pattern definition.")
    clean_pattern = str(layout.get("type") or "").strip().lower()
    if clean_pattern not in {"rectangular", "linear", "circular"}:
        return _validation_error("pattern must be rectangular, linear, or circular.")
    clean_prefix = str(name_prefix or "").strip()
    if not clean_prefix:
        return _validation_error(
            "name_prefix is required for sketcher.add_hole_pattern."
        )
    ok, result = _number_arg("hole_diameter", hole_diameter)
    if not ok:
        return _validation_error(str(result))
    diameter = float(result)
    if diameter <= 0:
        return _validation_error("hole_diameter must be positive.")
    ok, parsed_construction = _bool_arg("construction", construction)
    if not ok:
        return _validation_error(str(parsed_construction))
    ok, parsed_lock_centers = _bool_arg("constrain_centers", constrain_centers)
    if not ok:
        return _validation_error(str(parsed_lock_centers))
    ok, parsed_equal_radii = _bool_arg("equal_diameters", equal_diameters)
    if not ok:
        return _validation_error(str(parsed_equal_radii))
    center = layout.get("center_mm")
    if not _point2(center):
        return _validation_error("layout.center_mm must be exactly [x, y].")
    pattern_args: dict[str, float | int | None] = {
        "count_x": None,
        "count_y": None,
        "spacing_x": None,
        "spacing_y": None,
        "count": None,
        "linear_angle_degrees": None,
        "bolt_circle_diameter": None,
        "start_angle_degrees": None,
    }
    if clean_pattern == "rectangular":
        counts = layout.get("counts")
        spacing = layout.get("spacing_mm")
        if not isinstance(counts, list) or len(counts) != 2:
            return _validation_error(
                "rectangular layout.counts must be [columns, rows]."
            )
        if not _point2(spacing):
            return _validation_error("rectangular layout.spacing_mm must be [x, y].")
        for name, value in (("count_x", counts[0]), ("count_y", counts[1])):
            ok, result = _integer_arg(name, value)
            if not ok:
                return _validation_error(str(result))
            pattern_args[name] = int(result)
        for name, value in (("spacing_x", spacing[0]), ("spacing_y", spacing[1])):
            ok, result = _number_arg(name, value)
            if not ok:
                return _validation_error(str(result))
            pattern_args[name] = float(result)
    elif clean_pattern == "linear":
        ok, result = _integer_arg("count", layout.get("count"))
        if not ok:
            return _validation_error(str(result))
        pattern_args["count"] = int(result)
        for name, value in (
            ("spacing_x", layout.get("spacing_mm")),
            ("linear_angle_degrees", layout.get("angle_degrees")),
        ):
            ok, result = _number_arg(name, value)
            if not ok:
                return _validation_error(str(result))
            pattern_args[name] = float(result)
    else:
        ok, result = _integer_arg("count", layout.get("count"))
        if not ok:
            return _validation_error(str(result))
        pattern_args["count"] = int(result)
        for name, value in (
            ("bolt_circle_diameter", layout.get("pitch_circle_diameter_mm")),
            ("start_angle_degrees", layout.get("start_angle_degrees")),
        ):
            ok, result = _number_arg(name, value)
            if not ok:
                return _validation_error(str(result))
            pattern_args[name] = float(result)
    try:
        centers = _centers(
            clean_pattern,
            center_x=float(center[0]),
            center_y=float(center[1]),
            count_x=pattern_args["count_x"],
            count_y=pattern_args["count_y"],
            spacing_x=pattern_args["spacing_x"],
            spacing_y=pattern_args["spacing_y"],
            count=pattern_args["count"],
            linear_angle_degrees=pattern_args["linear_angle_degrees"],
            bolt_circle_diameter=pattern_args["bolt_circle_diameter"],
            start_angle_degrees=pattern_args["start_angle_degrees"],
        )
    except ValueError as exc:
        return _validation_error(str(exc))
    sketch = get_sketch(service)
    if sketch is None:
        return {
            **no_sketch(),
            "error": "No Sketcher sketch is currently open for editing.",
        }

    def _add() -> dict[str, Any]:
        import FreeCAD as App
        import Part
        import Sketcher

        target = get_sketch(service, sketch.Name)
        if target is None:
            raise RuntimeError(f"Sketch not found: {sketch.Name}")
        before_geometry = len(getattr(target, "Geometry", []))
        before_constraints = len(getattr(target, "Constraints", []))
        radius = diameter / 2.0
        created: list[int] = []
        constraints: list[Any] = []
        for x, y in centers:
            geometry_index = target.addGeometry(
                Part.Circle(
                    App.Vector(float(x), float(y), 0.0),
                    App.Vector(0.0, 0.0, 1.0),
                    radius,
                ),
                bool(parsed_construction),
            )
            created.append(int(geometry_index))
        if created:
            constraints.append(Sketcher.Constraint("Radius", created[0], radius))
        if parsed_equal_radii:
            constraints.extend(
                Sketcher.Constraint("Equal", created[0], index) for index in created[1:]
            )
        else:
            constraints.extend(
                Sketcher.Constraint("Radius", index, radius) for index in created[1:]
            )
        if parsed_lock_centers:
            for index, (x, y) in zip(created, centers):
                constraints.append(Sketcher.Constraint("DistanceX", index, 3, float(x)))
                constraints.append(Sketcher.Constraint("DistanceY", index, 3, float(y)))
        if constraints:
            target.addConstraint(constraints)
            constraint_index = before_constraints
        else:
            constraint_index = []
        _name_geometry(service, target, created, clean_prefix)
        return {
            "sketch": target.Name,
            "pattern": clean_pattern,
            "geometry_index": created[0] if created else None,
            "created_geometry_indices": created,
            "geometry_added": len(created),
            "constraint_index": _constraint_indices(constraint_index),
            "constraints_added": len(constraints),
            "created_constraint_indices": list(
                range(before_constraints, before_constraints + len(constraints))
            ),
            "geometry_count_before": before_geometry,
            "geometry_count": len(getattr(target, "Geometry", [])),
            "constraint_count_before": before_constraints,
            "constraint_count": len(getattr(target, "Constraints", [])),
            "hole_diameter": diameter,
            "hole_radius": radius,
            "centers": [[float(x), float(y)] for x, y in centers],
            "semantic_handles": [
                f"name:{clean_prefix}_{offset}" for offset in range(1, len(created) + 1)
            ],
            "construction": bool(parsed_construction),
            "constrain_centers": bool(parsed_lock_centers),
            "equal_diameters": bool(parsed_equal_radii),
        }

    return active_response(
        service,
        sketch,
        run_freecad_transaction(f"Add Sketcher {clean_pattern} hole pattern", _add),
    )


def _point2(value: Any) -> bool:
    if not isinstance(value, list) or len(value) != 2:
        return False
    if any(isinstance(item, bool) for item in value):
        return False
    try:
        float(value[0])
        float(value[1])
    except (TypeError, ValueError):
        return False
    return True


def _centers(
    pattern: str,
    *,
    center_x: float,
    center_y: float,
    count_x: int | None,
    count_y: int | None,
    spacing_x: float | None,
    spacing_y: float | None,
    count: int | None,
    linear_angle_degrees: float | None,
    bolt_circle_diameter: float | None,
    start_angle_degrees: float | None,
) -> list[tuple[float, float]]:
    if pattern == "rectangular":
        if count_x is None or count_y is None or spacing_x is None or spacing_y is None:
            raise ValueError(
                "count_x, count_y, spacing_x, and spacing_y are required for rectangular hole patterns."
            )
        if count_x <= 0 or count_y <= 0:
            raise ValueError(
                "count_x and count_y must be positive for rectangular hole patterns."
            )
        if count_x == 1 and count_y == 1:
            return [(center_x, center_y)]
        if count_x > 1 and spacing_x <= 0:
            raise ValueError(
                "spacing_x must be positive when count_x is greater than 1."
            )
        if count_y > 1 and spacing_y <= 0:
            raise ValueError(
                "spacing_y must be positive when count_y is greater than 1."
            )
        x0 = center_x - spacing_x * (count_x - 1) / 2.0
        y0 = center_y - spacing_y * (count_y - 1) / 2.0
        return [
            (x0 + column * spacing_x, y0 + row * spacing_y)
            for row in range(count_y)
            for column in range(count_x)
        ]
    if pattern == "linear":
        if count is None or spacing_x is None or linear_angle_degrees is None:
            raise ValueError(
                "count, spacing_x, and linear_angle_degrees are required for linear hole patterns."
            )
        if count <= 0:
            raise ValueError("count must be positive for linear hole patterns.")
        if count == 1:
            return [(center_x, center_y)]
        if spacing_x <= 0:
            raise ValueError("spacing_x must be positive for linear hole patterns.")
        angle = math.radians(linear_angle_degrees)
        dx = math.cos(angle) * spacing_x
        dy = math.sin(angle) * spacing_x
        start = -(count - 1) / 2.0
        return [
            (center_x + (start + offset) * dx, center_y + (start + offset) * dy)
            for offset in range(count)
        ]
    if pattern == "circular":
        if count is None or bolt_circle_diameter is None or start_angle_degrees is None:
            raise ValueError(
                "count, bolt_circle_diameter, and start_angle_degrees are required for circular hole patterns."
            )
        if count < 2:
            raise ValueError("count must be at least 2 for circular hole patterns.")
        if bolt_circle_diameter is None or float(bolt_circle_diameter) <= 0:
            raise ValueError(
                "bolt_circle_diameter must be positive for circular hole patterns."
            )
        radius = float(bolt_circle_diameter) / 2.0
        start = math.radians(start_angle_degrees)
        return [
            (
                center_x + math.cos(start + 2.0 * math.pi * offset / count) * radius,
                center_y + math.sin(start + 2.0 * math.pi * offset / count) * radius,
            )
            for offset in range(count)
        ]
    raise ValueError("pattern must be rectangular, linear, or circular.")


def _constraint_indices(raw_value: Any) -> int | list[int]:
    if isinstance(raw_value, int):
        return int(raw_value)
    if isinstance(raw_value, (list, tuple)):
        flattened: list[int] = []
        for item in raw_value:
            if isinstance(item, (list, tuple)):
                flattened.extend(int(value) for value in item)
            else:
                flattened.append(int(item))
        return flattened
    if raw_value is None:
        return []
    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            "FreeCAD addConstraint() returned an unsupported constraint-index value: "
            f"{raw_value!r}."
        ) from exc


def _name_geometry(service: Any, sketch: Any, indices: list[int], prefix: str) -> None:
    metadata = geometry_metadata(sketch)
    names = metadata.setdefault("names", {})
    geometry = service.sketcher_summary(getattr(sketch, "Name", None)).get(
        "geometry", []
    )
    for offset, index in enumerate(indices, start=1):
        if 0 <= index < len(geometry):
            names[f"{prefix}_{offset}"] = {
                "index": index,
                "fingerprint": geometry_fingerprint(geometry[index]),
            }
    set_geometry_metadata(sketch, metadata)
