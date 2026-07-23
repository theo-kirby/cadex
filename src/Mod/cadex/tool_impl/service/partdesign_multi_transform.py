# SPDX-License-Identifier: LGPL-2.1-or-later

"""Focused native PartDesign MultiTransform tool."""

from __future__ import annotations

from typing import Any

from . import partdesign_transform_feature


_TRANSFORMATION_SCHEMA = {
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "type": {"const": "linear", "description": "Linear pattern step."},
                "reference": partdesign_transform_feature.AXIS_REFERENCE_SCHEMA,
                "distribution": partdesign_transform_feature.distribution_schema("length"),
                "reversed": {
                    "type": "boolean",
                    "description": "Pattern in the opposite direction; usually false.",
                },
            },
            "required": ["type", "reference", "distribution", "reversed"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {"const": "polar", "description": "Polar pattern step."},
                "reference": partdesign_transform_feature.AXIS_REFERENCE_SCHEMA,
                "distribution": partdesign_transform_feature.distribution_schema("angle_degrees", 360.0),
                "reversed": {
                    "type": "boolean",
                    "description": "Pattern in the opposite rotation; usually false.",
                },
            },
            "required": ["type", "reference", "distribution", "reversed"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {"const": "mirror", "description": "Mirror step."},
                "reference": partdesign_transform_feature.PLANE_REFERENCE_SCHEMA,
            },
            "required": ["type", "reference"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {"const": "scale", "description": "Scale step."},
                "factor": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "Scale factor of the final occurrence.",
                },
                "occurrences": {
                    "type": "integer",
                    "minimum": 2,
                    "description": "Total occurrence count, original included.",
                },
            },
            "required": ["type", "factor", "occurrences"],
            "additionalProperties": False,
        },
    ]
}

TOOL_SPEC = {
    "name": "partdesign.multi_transform",
    "description": (
        "Create one native MultiTransform from one or more exact source features and an ordered "
        "composition of at least two mirror, linear, polar, or scale transformations."
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
                "description": "Exact internal names of the features to transform.",
            },
            "label": {"type": "string", "description": "Visible label for the new feature."},
            "transformations": {
                "type": "array",
                "items": _TRANSFORMATION_SCHEMA,
                "minItems": 2,
                "description": "Ordered transformation steps applied in sequence.",
            },
            "transform_mode": partdesign_transform_feature.TRANSFORM_MODE_SCHEMA,
            "refine": {
                "type": "boolean",
                "description": "Remove redundant edges from the result; usually true.",
            },
        },
        "required": ["feature_names", "label", "transformations", "transform_mode", "refine"],
        "additionalProperties": False,
    },
}


def run(service: Any, **arguments: Any) -> dict[str, Any]:
    return partdesign_transform_feature.run_multi_transform(service, **arguments)
