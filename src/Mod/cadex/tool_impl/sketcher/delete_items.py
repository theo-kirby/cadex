# SPDX-License-Identifier: LGPL-2.1-or-later

"""Consolidated Sketcher deletion tool.

Replaces sketcher.delete_geometry, sketcher.delete_constraint,
sketcher.delete_all_geometry, and sketcher.delete_all_constraints with one
tool that deletes single items, bulk selections, or everything.
"""

from __future__ import annotations

from typing import Any

from .common import (
    active_response,
    constraint_inventory,
    geometry_handle,
    geometry_inventory,
    get_sketch,
    resolve_constraint_index,
    resolve_geometry_index,
    run_freecad_transaction,
    sketch_collection_maps,
    validate_constraint_index,
    validate_geometry_index,
)


TOOL_SPEC = {
    "name": "sketcher.delete_items",
    "safety": "SAFE_WRITE",
    "edit_modes": ["sketch"],
    "description": (
        "Delete Sketcher geometry and/or constraints by index, name, or handle. "
        "Supports bulk lists and all_geometry/all_constraints. Prefer tag:<uuid> geometry "
        "handles: they remain valid when deletion shifts surviving geometry indices."
    ),
    "contextual": True,
    "workbench": "SketcherWorkbench",
    "parameters": {
        "type": "object",
        "properties": {
            "geometry_items": {
                "type": "array",
                "items": {"type": ["integer", "string"]},
                "description": (
                    "Geometry to delete: transient integer indices or stable tag:<uuid> "
                    "handles from live sketch state."
                ),
            },
            "constraint_items": {
                "type": "array",
                "items": {"type": ["integer", "string"]},
                "description": "Constraints to delete: integer indices, handles (constraint:N), or names.",
            },
            "all_geometry": {
                "type": "boolean",
                "description": "Delete all editable geometry in the sketch.",
            },
            "all_constraints": {
                "type": "boolean",
                "description": "Delete all constraints in the sketch.",
            },
            "delete_constraints_first": {
                "type": "boolean",
                "description": (
                    "Required when all_geometry is true. When true, delete all constraints "
                    "before all geometry so FreeCAD does not cascade-delete implicitly."
                ),
            },
        },
        "additionalProperties": False,
    },
}


def _invalid_call(error: str, **extra: Any) -> dict[str, Any]:
    result = {
        "ok": False,
        "error": error,
        "retry_same_call": False,
        "recoverable": True,
    }
    result.update(extra)
    return result


def run(
    service: Any,
    sketch_name: str | None = None,
    geometry_items: list[int | str] | None = None,
    constraint_items: list[int | str] | None = None,
    all_geometry: bool | None = None,
    all_constraints: bool | None = None,
    delete_constraints_first: bool | None = None,
) -> dict[str, Any]:
    if all_geometry is not None and not isinstance(all_geometry, bool):
        return _invalid_call("all_geometry must be a boolean when provided.")
    if all_constraints is not None and not isinstance(all_constraints, bool):
        return _invalid_call("all_constraints must be a boolean when provided.")
    if delete_constraints_first is not None and not isinstance(
        delete_constraints_first, bool
    ):
        return _invalid_call(
            "delete_constraints_first must be a boolean when provided."
        )
    wants_all_geometry = bool(all_geometry)
    wants_all_constraints = bool(all_constraints)
    if wants_all_geometry and delete_constraints_first is None:
        return _invalid_call(
            "all_geometry=true requires explicit delete_constraints_first."
        )
    if wants_all_geometry and wants_all_constraints:
        return _invalid_call(
            "Use all_geometry=true with delete_constraints_first=true instead of combining all_geometry and all_constraints."
        )
    if not wants_all_geometry and delete_constraints_first is not None:
        return _invalid_call(
            "delete_constraints_first is only valid when all_geometry=true."
        )
    sketch = get_sketch(service)
    if sketch is None:
        return _invalid_call("No Sketcher sketch is currently open for editing.")
    geometry_items = geometry_items or []
    constraint_items = constraint_items or []
    if (
        not geometry_items
        and not constraint_items
        and not wants_all_geometry
        and not wants_all_constraints
    ):
        return _invalid_call(
            "Nothing to delete. Provide geometry_items, constraint_items, "
            "all_geometry=true, or all_constraints=true."
        )
    if wants_all_geometry and geometry_items:
        return _invalid_call("Use either all_geometry or geometry_items, not both.")
    if wants_all_constraints and constraint_items:
        return _invalid_call(
            "Use either all_constraints or constraint_items, not both."
        )

    geometry_indices: list[int] = []
    for item in geometry_items:
        try:
            if isinstance(item, bool):
                raise ValueError(f"Invalid geometry item: {item!r}")
            if isinstance(item, int):
                index = int(item)
            elif isinstance(item, float) and float(item).is_integer():
                index = int(item)
            else:
                index = resolve_geometry_index(service, sketch, None, str(item))
        except (ValueError, TypeError, KeyError) as exc:
            return _invalid_call(f"Could not resolve geometry item {item!r}: {exc}")
        invalid = validate_geometry_index(sketch, index)
        if invalid:
            invalid.setdefault("retry_same_call", False)
            invalid.setdefault("recoverable", True)
            return invalid
        geometry_indices.append(index)

    constraint_indices: list[int] = []
    for item in constraint_items:
        try:
            if isinstance(item, bool):
                raise ValueError(f"Invalid constraint item: {item!r}")
            if isinstance(item, int):
                index = int(item)
            elif isinstance(item, float) and float(item).is_integer():
                index = int(item)
            else:
                handle = str(item)
                if handle.startswith("constraint:"):
                    index = resolve_constraint_index(sketch, None, None, handle)
                else:
                    index = resolve_constraint_index(sketch, None, handle, None)
        except (ValueError, TypeError, KeyError) as exc:
            return _invalid_call(f"Could not resolve constraint item {item!r}: {exc}")
        invalid = validate_constraint_index(sketch, index)
        if invalid:
            invalid.setdefault("retry_same_call", False)
            invalid.setdefault("recoverable", True)
            return invalid
        constraint_indices.append(index)

    geometry_targets = sorted(set(geometry_indices))
    constraint_targets = sorted(set(constraint_indices))

    def _delete() -> dict[str, Any]:
        import FreeCAD as App

        target = get_sketch(service, sketch.Name)
        if target is None:
            raise RuntimeError(f"Sketch not found: {sketch.Name}")
        before_geometry = geometry_inventory(service, target)
        before_constraints = constraint_inventory(service, target)
        before_geometry_count = len(before_geometry)
        before_constraint_count = len(before_constraints)
        requested_geometry = (
            list(range(before_geometry_count))
            if wants_all_geometry
            else geometry_targets
        )
        requested_geometry_handles = [
            geometry_handle(target, index) for index in requested_geometry
        ]
        requested_constraint_handles = [
            before_constraints[index].get("stable_handle")
            or before_constraints[index].get("index_handle")
            for index in (
                list(range(before_constraint_count))
                if wants_all_constraints
                or (wants_all_geometry and delete_constraints_first)
                else constraint_targets
            )
        ]
        native_mutation_results: list[dict[str, Any]] = []

        if wants_all_constraints or (wants_all_geometry and delete_constraints_first):
            if before_constraint_count:
                native_mutation_results.append(
                    target.delConstraints(
                        list(range(before_constraint_count)), True, False
                    )
                )
        else:
            if constraint_targets:
                native_mutation_results.append(
                    target.delConstraints(constraint_targets, True, False)
                )

        if wants_all_geometry:
            if before_geometry_count:
                native_mutation_results.append(
                    target.delGeometries(
                        list(range(before_geometry_count)), False
                    )
                )
        else:
            if geometry_targets:
                native_mutation_results.append(
                    target.delGeometries(geometry_targets, False)
                )

        maps = sketch_collection_maps(
            service, target, before_geometry, before_constraints
        )
        geometry_map = maps["geometry"]
        constraint_map = maps["constraints"]
        return {
            "sketch": target.Name,
            "requested_geometry_indices": requested_geometry,
            "requested_geometry_handles": requested_geometry_handles,
            "requested_constraint_indices": (
                list(range(before_constraint_count))
                if wants_all_constraints
                or (wants_all_geometry and delete_constraints_first)
                else constraint_targets
            ),
            "requested_constraint_handles": requested_constraint_handles,
            "native_mutation_results": native_mutation_results,
            "deleted_geometry": geometry_map["deleted"],
            "cascade_deleted_constraints": constraint_map["deleted"],
            "created_geometry": geometry_map["created"],
            "created_constraints": constraint_map["created"],
            "geometry_count_before": before_geometry_count,
            "constraint_count_before": before_constraint_count,
            "geometry_count": len(maps["geometry_after"]),
            "constraint_count": len(maps["constraints_after"]),
            "old_to_new_geometry_index": geometry_map["old_to_new"],
            "old_to_new_constraint_index": constraint_map["old_to_new"],
            "geometry_map_identity": geometry_map["identity_field"],
            "constraint_map_identity": constraint_map["identity_field"],
            "surviving_tag_handles_remain_valid": True,
        }

    return active_response(
        service, sketch, run_freecad_transaction("Delete Sketcher items", _delete)
    )
