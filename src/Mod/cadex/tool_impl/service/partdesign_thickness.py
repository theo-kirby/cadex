# SPDX-License-Identifier: LGPL-2.1-or-later

"""Focused native PartDesign Thickness tool."""

from __future__ import annotations

from typing import Any

from . import partdesign_dressup_feature


TOOL_SPEC = {
    "name": "partdesign.thickness",
    "description": (
        "Create one native PartDesign Thickness shell from exact or count-guarded opening faces "
        "on the current Body Tip with named direction, mode, join, and intersection behavior."
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
                "description": "Exact internal name of the Body Tip feature to shell.",
            },
            "label": {"type": "string", "description": "Visible label for the new feature."},
            "selection": partdesign_dressup_feature.selection_schema(
                allow_all_edges=False,
                face_only=True,
            ),
            "wall_thickness": {
                "type": "number",
                "exclusiveMinimum": 0,
                "description": "Wall thickness in mm.",
            },
            "direction": {
                "type": "string",
                "enum": ["inward", "outward"],
                "description": "Grow the wall into the solid or out from it.",
            },
            "mode": {
                "type": "string",
                "enum": ["skin", "pipe", "recto_verso"],
                "description": "Shell construction mode; skin is the standard hollow shell.",
            },
            "join": {
                "type": "string",
                "enum": ["arc", "intersection"],
                "description": "How offset walls join at edges.",
            },
            "intersection_handling": {
                "type": "boolean",
                "description": "Resolve self-intersections in the offset result; usually false.",
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
            "base_feature_name", "label", "selection", "wall_thickness", "direction",
            "mode", "join", "intersection_handling", "refine", "support_transform",
        ],
        "additionalProperties": False,
    },
}


def run(service: Any, **arguments: Any) -> dict[str, Any]:
    return partdesign_dressup_feature.run(
        service,
        operation="thickness",
        type_id="PartDesign::Thickness",
        **arguments,
    )
