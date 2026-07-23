# SPDX-License-Identifier: LGPL-2.1-or-later

"""Focused native PartDesign LinearPattern tool."""

from __future__ import annotations

from typing import Any

from . import partdesign_transform_feature


TOOL_SPEC = {
    "name": "partdesign.linear_pattern",
    "description": (
        "Create one native LinearPattern from one or more exact features in the same Body. "
        "Choose a typed axis and an unambiguous total extent, uniform gap, or exact gap list."
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
            "direction": partdesign_transform_feature.AXIS_REFERENCE_SCHEMA,
            "distribution": partdesign_transform_feature.distribution_schema("length"),
            "reversed": {
                "type": "boolean",
                "description": "Pattern in the opposite direction; usually false.",
            },
            "transform_mode": partdesign_transform_feature.TRANSFORM_MODE_SCHEMA,
            "refine": {
                "type": "boolean",
                "description": "Remove redundant edges from the result; usually true.",
            },
        },
        "required": [
            "feature_names", "label", "direction", "distribution", "reversed",
            "transform_mode", "refine",
        ],
        "additionalProperties": False,
    },
}


def run(service: Any, **arguments: Any) -> dict[str, Any]:
    direction = arguments.pop("direction")
    return partdesign_transform_feature.run_single_transform(
        service,
        operation="linear_pattern",
        type_id="PartDesign::LinearPattern",
        reference=direction,
        **arguments,
    )
