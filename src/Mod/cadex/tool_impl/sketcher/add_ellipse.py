# SPDX-License-Identifier: LGPL-2.1-or-later

"""Create an elliptical Sketcher profile."""

from __future__ import annotations

from typing import Any

from . import add_geometry


TOOL_SPEC = {
    "name": "sketcher.add_ellipse",
    "safety": "SAFE_WRITE",
    "edit_modes": ["sketch"],
    "description": (
        "Add one exact Sketcher ellipse from center, major/minor radii, and "
        "orientation. Use for elliptical sections and intentional conic form."
    ),
    "contextual": True,
    "parameters": {
        "type": "object",
        "properties": {
            "center": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 2,
                "maxItems": 2,
                "description": "Ellipse center as sketch-local [x, y] coordinates in mm.",
            },
            "major_radius": {
                "type": "number",
                "exclusiveMinimum": 0,
                "description": "Major radius in mm.",
            },
            "minor_radius": {
                "type": "number",
                "exclusiveMinimum": 0,
                "description": "Minor radius in mm.",
            },
            "angle_degrees": {
                "type": "number",
                "description": "Major-axis orientation in sketch-plane degrees.",
            },
            "construction": {
                "type": "boolean",
                "description": "Create the ellipse as construction geometry.",
            },
        },
        "required": [
            "center",
            "major_radius",
            "minor_radius",
            "angle_degrees",
            "construction",
        ],
        "additionalProperties": False,
    },
}


def run(service: Any, **kwargs: Any) -> dict[str, Any]:
    return add_geometry.run(service, kind="ellipse", **kwargs)
