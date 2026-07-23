# SPDX-License-Identifier: LGPL-2.1-or-later

"""Focused native PartDesign Chamfer tool."""

from __future__ import annotations

from typing import Any

from . import partdesign_dressup_feature


_DEFINITION_SCHEMA = {
    "description": "Chamfer geometry; choose exactly one definition variant.",
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "type": {"const": "equal_distance", "description": "Same setback on both faces."},
                "size": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "Setback in mm from the edge.",
                },
            },
            "required": ["type", "size"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {"const": "two_distances", "description": "Different setback on each face."},
                "size": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "First-face setback in mm.",
                },
                "second_size": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "Second-face setback in mm.",
                },
                "flip_direction": {
                    "type": "boolean",
                    "description": "Swap which face receives size and which second_size; usually false.",
                },
            },
            "required": ["type", "size", "second_size", "flip_direction"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {"const": "distance_angle", "description": "Setback on one face plus an angle."},
                "size": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "First-face setback in mm.",
                },
                "angle_degrees": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "exclusiveMaximum": 180,
                    "description": "Chamfer angle from the first face.",
                },
                "flip_direction": {
                    "type": "boolean",
                    "description": "Measure from the other face instead; usually false.",
                },
            },
            "required": ["type", "size", "angle_degrees", "flip_direction"],
            "additionalProperties": False,
        },
    ]
}

TOOL_SPEC = {
    "name": "partdesign.chamfer",
    "description": (
        "Create one native equal-distance, two-distance, or distance-angle PartDesign Chamfer "
        "on the current valid Body Tip with exact or count-guarded geometric selection. "
        "Finishing operation; apply after primary form is complete."
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
                "description": "Exact internal name of the Body Tip feature to chamfer.",
            },
            "label": {"type": "string", "description": "Visible label for the new feature."},
            "selection": partdesign_dressup_feature.selection_schema(allow_all_edges=True),
            "definition": _DEFINITION_SCHEMA,
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
            "base_feature_name", "label", "selection", "definition", "refine",
            "support_transform",
        ],
        "additionalProperties": False,
    },
}


def run(service: Any, **arguments: Any) -> dict[str, Any]:
    return partdesign_dressup_feature.run(
        service,
        operation="chamfer",
        type_id="PartDesign::Chamfer",
        **arguments,
    )
