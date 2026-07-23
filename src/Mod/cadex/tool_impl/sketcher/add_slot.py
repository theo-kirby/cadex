# SPDX-License-Identifier: LGPL-2.1-or-later

"""Native Sketcher slot profile tool."""

from __future__ import annotations

import math
from numbers import Real
from typing import Any

from .common import active_response, get_sketch, no_sketch, run_freecad_transaction


TOOL_SPEC = {
    "name": "sketcher.add_slot",
    "safety": "SAFE_WRITE",
    "edit_modes": ["sketch"],
    "description": (
        "Add one constrained slot profile: two straight sides and two "
        "semicircular ends. Overall length is the end-to-end size; center "
        "distance is derived internally as overall length minus width."
    ),
    "contextual": True,
    "parameters": {
        "type": "object",
        "properties": {
            "center_mm": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 2,
                "maxItems": 2,
                "description": "Exact [x, y] slot center in sketch-local mm.",
            },
            "overall_length": {
                "type": "number",
                "description": "Overall end-to-end slot length in mm including both semicircular ends.",
            },
            "width": {
                "type": "number",
                "description": "Slot width (arc diameter) in mm.",
            },
            "angle_degrees": {
                "type": "number",
                "description": "Explicit slot axis rotation in degrees.",
            },
            "construction": {
                "type": "boolean",
                "description": "Whether to create as construction geometry.",
            },
        },
        "required": [
            "center_mm",
            "overall_length",
            "width",
            "angle_degrees",
            "construction",
        ],
        "additionalProperties": False,
    },
}


def _number_arg(name: str, value: Any) -> tuple[bool, float | str]:
    if value is None:
        return False, f"{name} is required and must be an explicit number."
    if isinstance(value, bool) or not isinstance(value, Real):
        return False, f"{name} must be a number."
    return True, float(value)


def run(
    service: Any,
    center_mm: list[float] | None = None,
    overall_length: float | None = None,
    width: float | None = None,
    angle_degrees: float | None = None,
    construction: bool | None = None,
) -> dict[str, Any]:
    if not isinstance(center_mm, list) or len(center_mm) != 2:
        return {
            "ok": False,
            "error": "center_mm must be exactly [x, y] in sketch-local mm.",
            "retry_same_call": False,
        }
    parsed: dict[str, float] = {}
    for name, value in (
        ("center_x", center_mm[0]),
        ("center_y", center_mm[1]),
        ("overall_length", overall_length),
        ("width", width),
        ("angle_degrees", angle_degrees),
    ):
        ok, result = _number_arg(name, value)
        if not ok:
            return {"ok": False, "error": str(result), "retry_same_call": False}
        parsed[name] = float(result)
    if parsed["width"] <= 0:
        return {
            "ok": False,
            "error": "Slot width must be positive.",
            "retry_same_call": False,
        }
    if construction is None or not isinstance(construction, bool):
        return {
            "ok": False,
            "error": "construction is required and must be true or false.",
            "retry_same_call": False,
        }
    overall = parsed["overall_length"]
    center_to_center = overall - parsed["width"]
    if overall <= 0:
        return {
            "ok": False,
            "error": "Slot length and width must be positive.",
            "retry_same_call": False,
        }
    if center_to_center <= 0:
        return {
            "ok": False,
            "error": "Slot center distance must be positive; overall length must be greater than width.",
            "retry_same_call": False,
        }
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
        angle = math.radians(parsed["angle_degrees"])
        axis = App.Vector(math.cos(angle), math.sin(angle), 0.0)
        normal = App.Vector(-math.sin(angle), math.cos(angle), 0.0)
        center = App.Vector(parsed["center_x"], parsed["center_y"], 0.0)
        radius = parsed["width"] / 2.0
        straight_length = center_to_center
        left_center = center - axis * (straight_length / 2.0)
        right_center = center + axis * (straight_length / 2.0)
        left_top = left_center + normal * radius
        right_top = right_center + normal * radius
        right_bottom = right_center - normal * radius
        left_bottom = left_center - normal * radius
        left_outer = left_center - axis * radius
        right_outer = right_center + axis * radius
        target.addGeometry(
            [
                Part.LineSegment(left_top, right_top),
                Part.ArcOfCircle(right_top, right_center + axis * radius, right_bottom),
                Part.LineSegment(right_bottom, left_bottom),
                Part.ArcOfCircle(left_bottom, left_center - axis * radius, left_top),
            ],
            bool(construction),
        )
        base_index = before_geometry
        constraints = [
            Sketcher.Constraint("Block", base_index + 0),
            Sketcher.Constraint("Block", base_index + 1),
            Sketcher.Constraint("Block", base_index + 2),
            Sketcher.Constraint("Block", base_index + 3),
        ]
        target.addConstraint(constraints)
        degrees_of_freedom_error = None
        try:
            degrees_of_freedom = int(getattr(target, "DoF"))
        except Exception as exc:
            degrees_of_freedom = None
            degrees_of_freedom_error = str(exc)
        fully_constrained = (
            degrees_of_freedom == 0 if degrees_of_freedom is not None else False
        )
        return {
            "sketch": target.Name,
            "geometry_index": base_index,
            "geometry_added": 4,
            "created_geometry_indices": [
                base_index,
                base_index + 1,
                base_index + 2,
                base_index + 3,
            ],
            "constraint_count_before": before_constraints,
            "constraint_index": before_constraints,
            "constraints_added": len(constraints),
            "created_constraint_indices": list(
                range(before_constraints, before_constraints + len(constraints))
            ),
            "geometry_count_before": before_geometry,
            "geometry_count": len(getattr(target, "Geometry", [])),
            "constraint_count": len(getattr(target, "Constraints", [])),
            "center": [parsed["center_x"], parsed["center_y"]],
            "overall_length": overall,
            "center_distance": center_to_center,
            "straight_segment_length": center_to_center,
            "width": parsed["width"],
            "radius": radius,
            "angle_degrees": parsed["angle_degrees"],
            "arc_centers": {
                "left": [float(left_center.x), float(left_center.y)],
                "right": [float(right_center.x), float(right_center.y)],
            },
            "profile_points": {
                "left_top": [float(left_top.x), float(left_top.y)],
                "right_top": [float(right_top.x), float(right_top.y)],
                "right_bottom": [float(right_bottom.x), float(right_bottom.y)],
                "left_bottom": [float(left_bottom.x), float(left_bottom.y)],
                "left_outer": [float(left_outer.x), float(left_outer.y)],
                "right_outer": [float(right_outer.x), float(right_outer.y)],
            },
            "bounding_box": _bounding_box(
                [
                    left_top,
                    right_top,
                    right_bottom,
                    left_bottom,
                    left_outer,
                    right_outer,
                ]
            ),
            "degrees_of_freedom": degrees_of_freedom,
            "degrees_of_freedom_error": degrees_of_freedom_error,
            "fully_constrained": fully_constrained,
            "construction": bool(construction),
        }

    return active_response(
        service, sketch, run_freecad_transaction("Add Sketcher slot", _add)
    )


def _bounding_box(points):
    xs = [float(point.x) for point in points]
    ys = [float(point.y) for point in points]
    return {
        "min_x": min(xs),
        "min_y": min(ys),
        "max_x": max(xs),
        "max_y": max(ys),
        "width": max(xs) - min(xs),
        "height": max(ys) - min(ys),
    }
