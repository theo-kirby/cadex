# SPDX-License-Identifier: LGPL-2.1-or-later

"""Native Sketcher rectangle tool."""

from __future__ import annotations

from numbers import Real
from typing import Any

from .common import active_response, get_sketch, no_sketch, run_freecad_transaction


TOOL_SPEC = {
    "name": "sketcher.draw_rectangle",
    "safety": "SAFE_WRITE",
    "edit_modes": ["sketch"],
    "description": (
        "Draw one fully constrained rectangle in the active Sketcher sketch: size and "
        "position are dimensioned; no further constraints are needed. Convenience "
        "shortcut for an exact four-line closed profile."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "width": {
                "type": "number",
                "description": "Rectangle width in mm along sketch X.",
            },
            "height": {
                "type": "number",
                "description": "Rectangle height in mm along sketch Y.",
            },
            "center_x": {"type": "number", "description": "Explicit center X in mm."},
            "center_y": {"type": "number", "description": "Explicit center Y in mm."},
            "construction": {
                "type": "boolean",
                "description": "Whether to create the rectangle as construction geometry.",
            },
        },
        "required": ["width", "height", "center_x", "center_y", "construction"],
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
    width: float | None = None,
    height: float | None = None,
    center_x: float | None = None,
    center_y: float | None = None,
    construction: bool | None = None,
) -> dict[str, Any]:
    parsed: dict[str, float] = {}
    for name, value in (
        ("width", width),
        ("height", height),
        ("center_x", center_x),
        ("center_y", center_y),
    ):
        ok, result = _number_arg(name, value)
        if not ok:
            return {"ok": False, "error": str(result), "retry_same_call": False}
        parsed[name] = float(result)
    if parsed["width"] <= 0 or parsed["height"] <= 0:
        return {
            "ok": False,
            "error": "Rectangle dimensions must be positive.",
            "retry_same_call": False,
        }
    if construction is None or not isinstance(construction, bool):
        return {
            "ok": False,
            "error": "construction is required and must be true or false.",
            "retry_same_call": False,
        }
    sketch = get_sketch(service)
    if sketch is None:
        return {
            **no_sketch(),
            "error": "No Sketcher sketch is currently open for editing.",
        }

    def _draw() -> dict[str, Any]:
        import FreeCAD as App
        import Part
        import Sketcher

        doc = App.ActiveDocument
        target = doc.getObject(sketch.Name) if doc else sketch
        if target is None:
            raise RuntimeError(f"Sketch not found: {sketch.Name}")
        width_value = parsed["width"]
        height_value = parsed["height"]
        x0 = parsed["center_x"] - width_value / 2.0
        x1 = parsed["center_x"] + width_value / 2.0
        y0 = parsed["center_y"] - height_value / 2.0
        y1 = parsed["center_y"] + height_value / 2.0
        index = int(
            getattr(target, "GeometryCount", len(getattr(target, "Geometry", [])))
        )
        target.addGeometry(
            [
                Part.LineSegment(App.Vector(x0, y1, 0), App.Vector(x1, y1, 0)),
                Part.LineSegment(App.Vector(x1, y1, 0), App.Vector(x1, y0, 0)),
                Part.LineSegment(App.Vector(x1, y0, 0), App.Vector(x0, y0, 0)),
                Part.LineSegment(App.Vector(x0, y0, 0), App.Vector(x0, y1, 0)),
            ],
            bool(construction),
        )
        target.addConstraint(
            [
                Sketcher.Constraint("Coincident", index + 0, 2, index + 1, 1),
                Sketcher.Constraint("Coincident", index + 1, 2, index + 2, 1),
                Sketcher.Constraint("Coincident", index + 2, 2, index + 3, 1),
                Sketcher.Constraint("Coincident", index + 3, 2, index + 0, 1),
                Sketcher.Constraint("Horizontal", index + 0),
                Sketcher.Constraint("Horizontal", index + 2),
                Sketcher.Constraint("Vertical", index + 1),
                Sketcher.Constraint("Vertical", index + 3),
                Sketcher.Constraint("DistanceX", index + 2, 2, x0),
                Sketcher.Constraint("DistanceY", index + 2, 2, y0),
            ]
        )
        if abs(width_value - height_value) < 1e-9:
            target.addConstraint(Sketcher.Constraint("Equal", index + 2, index + 3))
            target.addConstraint(
                Sketcher.Constraint("Distance", index + 0, width_value)
            )
        else:
            target.addConstraint(
                Sketcher.Constraint("Distance", index + 0, width_value)
            )
            target.addConstraint(
                Sketcher.Constraint("Distance", index + 1, height_value)
            )
        return {
            "sketch": target.Name,
            "geometry_index": index,
            "geometry_added": 4,
            "width": width_value,
            "height": height_value,
            "center": [parsed["center_x"], parsed["center_y"]],
            "construction": bool(construction),
            "geometry_count": len(getattr(target, "Geometry", [])),
            "constraint_count": len(getattr(target, "Constraints", [])),
        }

    return active_response(
        service,
        sketch,
        run_freecad_transaction(
            f"Draw Sketcher rectangle {parsed['width']:g} x {parsed['height']:g}",
            _draw,
        ),
    )
