# SPDX-License-Identifier: LGPL-2.1-or-later

"""Focused native PartDesign Revolution tool."""

from __future__ import annotations

from typing import Any

from . import partdesign_rotational_feature


TOOL_SPEC = {
    "name": "partdesign.revolution",
    "description": (
        "Create one additive native PartDesign Revolution from an exact closed sketch and an "
        "explicit Body-origin axis, profile axis, or object edge. Supports angle, two-angle, "
        "up-to-first, up-to-last, and up-to-face termination."
    ),
    "contextual": True,
    "safety": "SAFE_WRITE",
    "workbench": "PartDesignWorkbench",
    "edit_modes": ["none"],
    "parameters": {
        "type": "object",
        "properties": {
            "profile_name": {
                "type": "string",
                "description": "Exact internal name of the closed profile sketch.",
            },
            "label": {
                "type": "string",
                "description": "Visible label for the new feature.",
            },
            "axis": partdesign_rotational_feature.AXIS_SCHEMA,
            "extent": partdesign_rotational_feature.extent_schema(
                ["angle", "up_to_last", "up_to_first", "up_to_face", "two_angles"]
            ),
            "midplane": {
                "type": "boolean",
                "description": "Center the rotation on the profile plane; usually false.",
            },
            "reversed": {
                "type": "boolean",
                "description": "Rotate in the opposite direction; usually false.",
            },
        },
        "required": [
            "profile_name",
            "label",
            "axis",
            "extent",
            "midplane",
            "reversed",
        ],
        "additionalProperties": False,
    },
}


def run(service: Any, **arguments: Any) -> dict[str, Any]:
    return partdesign_rotational_feature.run(
        service,
        operation="revolution",
        type_id="PartDesign::Revolution",
        **arguments,
    )
