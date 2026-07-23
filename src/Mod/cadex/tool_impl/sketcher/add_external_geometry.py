# SPDX-License-Identifier: LGPL-2.1-or-later

"""Native Sketcher add-external-geometry tool."""

from __future__ import annotations

from typing import Any

from .common import (
    active_response,
    external_geometry_summary,
    find_document_object,
    get_sketch,
    run_freecad_transaction,
    subelement_references,
)


TOOL_SPEC = {
    "name": "sketcher.add_external_geometry",
    "safety": "SAFE_WRITE",
    "edit_modes": ["sketch"],
    "description": (
        "Add one Sketcher external-geometry reference from an existing object "
        "subelement. Use to constrain sketches to existing edges/vertices."
    ),
    "contextual": True,
    "parameters": {
        "type": "object",
        "properties": {
            "source_object": {
                "type": "string",
                "description": "Document object name providing the subelement.",
            },
            "subelement": {
                "type": "string",
                "description": "Subelement name on the source object, e.g. Edge1 or Vertex2.",
            },
            "defining": {
                "type": "boolean",
                "description": "Import as defining (driving) geometry. Default false (reference only).",
            },
            "intersection": {
                "type": "boolean",
                "description": "Project the subelement's intersection with the sketch plane. Default false.",
            },
        },
        "required": ["source_object", "subelement"],
        "additionalProperties": False,
    },
}


def run(
    service: Any,
    sketch_name: str | None = None,
    source_object: str | None = None,
    subelement: str | None = None,
    defining: bool = False,
    intersection: bool = False,
) -> dict[str, Any]:
    sketch = get_sketch(service)
    if sketch is None:
        return {
            "ok": False,
            "error": "No Sketcher sketch is currently open for editing.",
        }
    obj = find_document_object(service, source_object)
    if obj is None:
        doc = service._active_document()
        candidates = [
            {
                "name": getattr(candidate, "Name", None),
                "label": getattr(candidate, "Label", getattr(candidate, "Name", None)),
                "type": getattr(candidate, "TypeId", None),
            }
            for candidate in list(getattr(doc, "Objects", []) or [])
            if getattr(candidate, "Shape", None) is not None
        ]
        return {
            "ok": False,
            "failure_code": "SOURCE_OBJECT_NOT_FOUND",
            "failure_stage": "precondition",
            "error": f"Source object not found: {source_object}",
            "requested": {
                "source_object": source_object,
                "subelement": subelement,
            },
            "candidates": candidates,
            "live_external_references": external_geometry_summary(sketch),
            "required_changes": ["Choose one exact source object from candidates."],
        }
    clean_subelement = str(subelement or "").strip()
    if not clean_subelement:
        return {"ok": False, "error": "subelement is required."}
    available = subelement_references(obj)
    valid = {item["subelement"] for item in available}
    if valid and clean_subelement not in valid:
        return {
            "ok": False,
            "failure_code": "SUBELEMENT_NOT_FOUND",
            "failure_stage": "precondition",
            "error": f"Subelement {clean_subelement} was not found on {getattr(obj, 'Name', source_object)}.",
            "requested": {
                "source_object": source_object,
                "subelement": clean_subelement,
            },
            "observed": {
                "source_object": {
                    "name": getattr(obj, "Name", None),
                    "label": getattr(obj, "Label", getattr(obj, "Name", None)),
                    "type": getattr(obj, "TypeId", None),
                }
            },
            "candidates": available[:120],
            "available_subelements": available[:120],
            "live_external_references": external_geometry_summary(sketch),
            "required_changes": ["Choose one exact subelement from candidates."],
        }

    def _add() -> dict[str, Any]:
        import FreeCAD as App

        target = get_sketch(service, sketch.Name)
        if target is None:
            raise RuntimeError(f"Sketch not found: {sketch.Name}")
        before = external_geometry_summary(target)
        before_count = len(before)
        target.addExternal(
            getattr(obj, "Name", str(source_object)),
            clean_subelement,
            bool(defining),
            bool(intersection),
        )
        after = external_geometry_summary(target)
        return {
            "sketch": target.Name,
            "source_object": getattr(obj, "Name", str(source_object)),
            "source_label": getattr(
                obj, "Label", getattr(obj, "Name", str(source_object))
            ),
            "source_type": getattr(obj, "TypeId", None),
            "source_subelement": next(
                (
                    item
                    for item in available
                    if item.get("subelement") == clean_subelement
                ),
                None,
            ),
            "subelement": clean_subelement,
            "defining": bool(defining),
            "intersection": bool(intersection),
            "external_geometry_index": before_count,
            "external_geometry_id": -before_count - 1,
            "external_geometry_count_before": before_count,
            "external_geometry_count": len(after),
            "external_geometry": after,
        }

    return active_response(
        service, sketch, run_freecad_transaction("Add Sketcher external geometry", _add)
    )
