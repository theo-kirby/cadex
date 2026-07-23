# SPDX-License-Identifier: LGPL-2.1-or-later

"""Focused native PartDesign SubShapeBinder tool."""

from __future__ import annotations

from typing import Any

from . import partdesign_reference_feature


TOOL_SPEC = {
    "name": "partdesign.create_subshape_binder",
    "description": (
        "Create one native SubShapeBinder inside an exact Body from exact multi-object geometry "
        "references with named bind, offset, face-building, fuse, and update behavior."
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
            "label": {"type": "string", "description": "Visible label for the new binder."},
            "references": {
                "type": "array",
                "items": partdesign_reference_feature.REFERENCE_SCHEMA,
                "minItems": 1,
                "description": "Geometry to bind into the Body.",
            },
            "fuse": {
                "type": "boolean",
                "description": "Fuse bound solids into one; usually false.",
            },
            "make_face": {
                "type": "boolean",
                "description": "Build faces from closed bound wires; usually true when binding profiles.",
            },
            "offset": {
                "type": "number",
                "description": "Offset of the bound geometry in mm; 0 for none.",
            },
            "offset_join": {
                "type": "string",
                "enum": ["arcs", "tangent", "intersection"],
                "description": "How offset edges join at corners; only used when offset is non-zero.",
            },
            "offset_fill": {
                "type": "boolean",
                "description": "Fill the gap between original and offset geometry; usually false.",
            },
            "offset_open_result": {
                "type": "boolean",
                "description": "Allow an open offset result; usually false.",
            },
            "offset_intersection": {
                "type": "boolean",
                "description": "Offset children independently; usually false.",
            },
            "relative": {
                "type": "boolean",
                "description": "Track the sources' relative placement; usually true.",
            },
            "bind_mode": {
                "type": "string",
                "enum": ["synchronized", "frozen", "detached"],
                "description": "synchronized follows source changes; frozen keeps the bound copy; detached drops the link.",
            },
            "partial_load": {
                "type": "boolean",
                "description": "Load only needed source data from external documents; usually false.",
            },
            "copy_on_change": {
                "type": "string",
                "enum": ["disabled", "enabled", "mutated"],
                "description": "Whether the binder copies sources when they change; usually disabled.",
            },
            "refine": {
                "type": "boolean",
                "description": "Remove redundant edges from the result; usually true.",
            },
        },
        "required": [
            "body_name", "label", "references", "fuse", "make_face", "offset",
            "offset_join", "offset_fill", "offset_open_result", "offset_intersection",
            "relative", "bind_mode", "partial_load", "copy_on_change", "refine",
        ],
        "additionalProperties": False,
    },
}


def run(service: Any, **arguments: Any) -> dict[str, Any]:
    return partdesign_reference_feature.run(
        service,
        operation="subshape_binder",
        type_id="PartDesign::SubShapeBinder",
        **arguments,
    )
