# SPDX-License-Identifier: LGPL-2.1-or-later

"""Create a native PartDesign datum point at an explicit 3D position."""

from __future__ import annotations

from typing import Any

from . import partdesign_create_datum_axis


TOOL_SPEC = {
    "name": "partdesign.create_datum_point",
    "description": (
        "Create one native PartDesign datum point at an explicit 3D position in an exact Body. "
        "Use as a stable construction reference for placements, sections, and measurements."
    ),
    "contextual": True,
    "safety": "SAFE_WRITE",
    "workbench": "PartDesignWorkbench",
    "edit_modes": ["none"],
    "parameters": {
        "type": "object",
        "properties": {
            "body_name": {
                "type": "string",
                "description": "Exact internal name of the owning Body.",
            },
            "label": {
                "type": "string",
                "description": "Visible label for the new datum point.",
            },
            "position": {
                **partdesign_create_datum_axis._VECTOR_SCHEMA,
                "description": "Point position in mm.",
            },
        },
        "required": ["body_name", "label", "position"],
        "additionalProperties": False,
    },
}


def run(
    service: Any,
    body_name: str,
    label: str,
    position: dict[str, float],
) -> dict[str, Any]:
    return partdesign_create_datum_axis._create_datum(
        service,
        body_name=body_name,
        label=label,
        origin=position,
        direction={"x": 0.0, "y": 0.0, "z": 1.0},
        type_id="PartDesign::Point",
        object_name="DatumPoint",
        operation="datum point",
    )
