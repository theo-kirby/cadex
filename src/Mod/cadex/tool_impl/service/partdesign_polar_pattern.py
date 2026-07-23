# SPDX-License-Identifier: LGPL-2.1-or-later

"""Focused native PartDesign PolarPattern tool."""

from __future__ import annotations

from typing import Any

from . import partdesign_transform_feature


TOOL_SPEC = {
    "name": "partdesign.polar_pattern",
    "description": (
        "Create one native PolarPattern from one or more exact features in the same Body. "
        "Choose a typed axis and an unambiguous total angle, uniform angular gap, or exact gap list."
    ),
    "contextual": True,
    "safety": "SAFE_WRITE",
    "workbench": "PartDesignWorkbench",
    "edit_modes": ["none"],
    "parameters": {
        "type": "object",
        "properties": {
            "feature_names": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "description": "Exact internal names of the features to pattern.",
            },
            "label": {"type": "string", "description": "Visible label for the new feature."},
            "axis": partdesign_transform_feature.AXIS_REFERENCE_SCHEMA,
            "distribution": partdesign_transform_feature.distribution_schema("angle_degrees", 360.0),
            "reversed": {
                "type": "boolean",
                "description": "Pattern in the opposite rotation; usually false.",
            },
            "transform_mode": partdesign_transform_feature.TRANSFORM_MODE_SCHEMA,
            "refine": {
                "type": "boolean",
                "description": "Remove redundant edges from the result; usually true.",
            },
        },
        "required": [
            "feature_names", "label", "axis", "distribution", "reversed",
            "transform_mode", "refine",
        ],
        "additionalProperties": False,
    },
}


def run(service: Any, **arguments: Any) -> dict[str, Any]:
    axis = arguments.pop("axis")
    return partdesign_transform_feature.run_single_transform(
        service,
        operation="polar_pattern",
        type_id="PartDesign::PolarPattern",
        reference=axis,
        **arguments,
    )
