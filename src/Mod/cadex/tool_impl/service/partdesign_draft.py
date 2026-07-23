# SPDX-License-Identifier: LGPL-2.1-or-later

"""Focused native PartDesign Draft tool."""

from __future__ import annotations

from typing import Any

from . import partdesign_dressup_feature, partdesign_transform_feature


TOOL_SPEC = {
    "name": "partdesign.draft",
    "description": (
        "Create one native PartDesign Draft on exact or count-guarded faces of the current Body "
        "Tip using an explicit neutral plane and pull direction; no direction is guessed."
    ),
    "contextual": True,
    "safety": "SAFE_WRITE",
    "workbench": "PartDesignWorkbench",
    "edit_modes": ["none"],
    "parameters": {
        "type": "object",
        "properties": {
            "base_feature_name": {
                "type": "string",
                "description": "Exact internal name of the Body Tip feature to draft.",
            },
            "label": {"type": "string", "description": "Visible label for the new feature."},
            "selection": partdesign_dressup_feature.selection_schema(
                allow_all_edges=False,
                face_only=True,
            ),
            "neutral_plane": {
                **partdesign_transform_feature.PLANE_REFERENCE_SCHEMA,
                "description": "Plane that stays unchanged; drafted faces pivot about it.",
            },
            "pull_direction": partdesign_dressup_feature.DRAFT_PULL_DIRECTION_SCHEMA,
            "angle_degrees": {
                "type": "number",
                "exclusiveMinimum": 0,
                "exclusiveMaximum": 90,
                "description": "Draft angle from the pull direction.",
            },
            "reversed": {
                "type": "boolean",
                "description": "Draft in the opposite direction; usually false.",
            },
            "refine": {
                "type": "boolean",
                "description": "Remove redundant edges from the result; usually true.",
            },
            "support_transform": {
                "type": "boolean",
                "description": "Include the base feature's support shape in the dress-up; false dresses only the base feature's own geometry (usually false).",
            },
        },
        "required": [
            "base_feature_name", "label", "selection", "neutral_plane", "pull_direction",
            "angle_degrees", "reversed", "refine", "support_transform",
        ],
        "additionalProperties": False,
    },
}


def run(service: Any, **arguments: Any) -> dict[str, Any]:
    return partdesign_dressup_feature.run(
        service,
        operation="draft",
        type_id="PartDesign::Draft",
        **arguments,
    )
