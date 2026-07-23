# SPDX-License-Identifier: LGPL-2.1-or-later

"""Native Sketcher remove-external-geometry tool."""

from __future__ import annotations

from typing import Any

from .common import (
    active_response,
    external_geometry_summary,
    get_sketch,
    run_freecad_transaction,
)


TOOL_SPEC = {
    "name": "sketcher.remove_external_geometry",
    "safety": "SAFE_WRITE",
    "edit_modes": ["sketch"],
    "description": (
        "Remove one native Sketcher external geometry reference by its index from the "
        "current live sketch state."
    ),
    "contextual": True,
    "parameters": {
        "type": "object",
        "properties": {
            "external_geometry_index": {
                "type": "integer",
                "description": "External geometry index to remove (0-based).",
            },
        },
        "required": ["external_geometry_index"],
        "additionalProperties": False,
    },
}


def run(
    service: Any,
    sketch_name: str | None = None,
    external_geometry_index: int = 0,
) -> dict[str, Any]:
    sketch = get_sketch(service)
    if sketch is None:
        return {
            "ok": False,
            "failure_code": "NO_ACTIVE_SKETCH",
            "failure_stage": "edit_state",
            "error": "No Sketcher sketch is currently open for editing.",
        }
    external = external_geometry_summary(sketch)
    index = int(external_geometry_index)
    if index < 0 or index >= len(external):
        return {
            "ok": False,
            "failure_code": "EXTERNAL_GEOMETRY_INDEX_OUT_OF_RANGE",
            "failure_stage": "precondition",
            "error": f"External geometry index out of range: {index}",
            "requested": {"external_geometry_index": index},
            "external_geometry_count": len(external),
            "candidates": external,
            "live_external_references": external,
            "required_changes": [
                "Choose one external_geometry_index from the live candidates."
            ],
        }

    def _remove() -> dict[str, Any]:
        import FreeCAD as App

        target = get_sketch(service, sketch.Name)
        if target is None:
            raise RuntimeError(f"Sketch not found: {sketch.Name}")
        before = external_geometry_summary(target)
        target.delExternal(index)
        after = external_geometry_summary(target)
        return {
            "sketch": target.Name,
            "removed_external_reference": before[index],
            "deleted_external_geometry_index": index,
            "deleted_external_geometry_id": -index - 1,
            "external_geometry_count_before": len(before),
            "external_geometry_count": len(after),
            "external_geometry": after,
            "old_to_new_external_geometry_index": {
                str(old): (old if old < index else old - 1)
                for old in range(len(before))
                if old != index
            },
        }

    return active_response(
        service,
        sketch,
        run_freecad_transaction("Remove Sketcher external geometry", _remove),
    )
