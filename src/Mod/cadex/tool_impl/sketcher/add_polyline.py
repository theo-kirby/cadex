# SPDX-License-Identifier: LGPL-2.1-or-later

"""Create connected straight Sketcher segments."""

from __future__ import annotations

from typing import Any

from . import add_geometry


TOOL_SPEC = {
    "name": "sketcher.add_polyline",
    "safety": "SAFE_WRITE",
    "edit_modes": ["sketch"],
    "description": (
        "Add one connected sequence of straight Sketcher segments. Use this "
        "only where the intended profile is genuinely straight; choose arc, "
        "ellipse, or spline operations for curved product form. Adjacent "
        "segments receive native Coincident constraints automatically."
    ),
    "contextual": True,
    "parameters": {
        "type": "object",
        "properties": {
            "points": {
                "type": "array",
                "minItems": 2,
                "items": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 2,
                },
                "description": "Ordered sketch-local [x,y] points in mm.",
            },
            "closed": {
                "type": "boolean",
                "description": "Connect the final point back to the first point.",
            },
            "lock_points": {
                "type": "boolean",
                "description": "Add exact DistanceX/DistanceY dimensions for every supplied point.",
            },
            "construction": {
                "type": "boolean",
                "description": "Create every segment as construction geometry.",
            },
        },
        "required": ["points", "closed", "lock_points", "construction"],
        "additionalProperties": False,
    },
}


def run(
    service: Any,
    points: list[list[float]],
    closed: bool,
    lock_points: bool,
    construction: bool,
) -> dict[str, Any]:
    return add_geometry.run(
        service,
        kind="polyline",
        points=points,
        closed=closed,
        constrain_points=lock_points,
        construction=construction,
    )
