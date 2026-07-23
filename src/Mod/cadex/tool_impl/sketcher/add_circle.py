# SPDX-License-Identifier: LGPL-2.1-or-later

"""Create a circular Sketcher profile or construction reference."""

from __future__ import annotations

from typing import Any

from . import add_geometry


TOOL_SPEC = {
    "name": "sketcher.add_circle",
    "safety": "SAFE_WRITE",
    "edit_modes": ["sketch"],
    "description": (
        "Add one exact Sketcher circle from a sketch-local center and radius. "
        "Use for holes, bosses, pitch references, and circular sections."
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
                "description": "Circle center as sketch-local [x, y] coordinates in mm.",
            },
            "radius": {
                "type": "number",
                "exclusiveMinimum": 0,
                "description": "Circle radius in mm.",
            },
            "construction": {
                "type": "boolean",
                "description": "Create the circle as construction geometry.",
            },
        },
        "required": ["center", "radius", "construction"],
        "additionalProperties": False,
    },
}


def run(service: Any, **kwargs: Any) -> dict[str, Any]:
    return add_geometry.run(service, kind="circle", **kwargs)
