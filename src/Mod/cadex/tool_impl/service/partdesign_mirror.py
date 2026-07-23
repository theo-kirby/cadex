# SPDX-License-Identifier: LGPL-2.1-or-later

"""Focused native PartDesign Mirrored tool."""

from __future__ import annotations

from typing import Any

from . import partdesign_transform_feature


TOOL_SPEC = {
    "name": "partdesign.mirror",
    "description": (
        "Create one native Mirrored feature from one or more exact features in the same Body "
        "about an exact origin plane, datum plane, sketch plane/axis plane, or planar face."
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
                "description": "Exact internal names of the features to mirror.",
            },
            "label": {"type": "string", "description": "Visible label for the new feature."},
            "plane": partdesign_transform_feature.PLANE_REFERENCE_SCHEMA,
            "transform_mode": partdesign_transform_feature.TRANSFORM_MODE_SCHEMA,
            "refine": {
                "type": "boolean",
                "description": "Remove redundant edges from the result; usually true.",
            },
        },
        "required": ["feature_names", "label", "plane", "transform_mode", "refine"],
        "additionalProperties": False,
    },
}


def run(service: Any, **arguments: Any) -> dict[str, Any]:
    plane = arguments.pop("plane")
    return partdesign_transform_feature.run_single_transform(
        service,
        operation="mirror",
        type_id="PartDesign::Mirrored",
        reference=plane,
        **arguments,
    )
