# SPDX-License-Identifier: LGPL-2.1-or-later

"""Shared helpers for native Sketcher tool implementations."""

from __future__ import annotations

import json
from typing import Any

from CadexTransactions import run_freecad_transaction

GEOMETRY_METADATA_PROPERTY = "CadexGeometryMetadata"


def get_sketch(service: Any, sketch_name: str | None = None) -> Any:
    return service._get_sketch(sketch_name)


def no_sketch(sketch_name: str | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "error": "No active Sketcher sketch found.",
        "requested": sketch_name,
    }


def recompute_diagnostics(transaction: dict[str, Any]) -> list[dict[str, Any]]:
    """Return structured diagnostics from the transaction's recompute generation."""
    if not isinstance(transaction, dict):
        return []
    summary = transaction.get("native_diagnostics")
    if not isinstance(summary, dict):
        return []
    return [
        dict(item)
        for item in list(summary.get("diagnostics") or [])
        if isinstance(item, dict)
    ]


def active_response(
    service: Any, sketch: Any, transaction: dict[str, Any]
) -> dict[str, Any]:
    """Return one concise mutation result plus authoritative post-operation state."""
    if not isinstance(transaction, dict):
        transaction = {"ok": False, "error": "Invalid transaction result."}
    updated = service._get_sketch(getattr(sketch, "Name", None))
    solver = solver_status(service, updated)
    profile = service._sketch_profile_status(updated)
    result = transaction.get("result") if isinstance(transaction, dict) else {}
    mutation = result if isinstance(result, dict) else {}
    geometry = (
        list(getattr(updated, "Geometry", []) or []) if updated is not None else []
    )
    affected_indices: set[int] = set()
    for key in (
        "created_geometry_indices",
        "modified_geometry_indices",
        "geometry_indices",
    ):
        raw_indices = mutation.get(key)
        if not isinstance(raw_indices, (list, tuple, set)):
            continue
        for raw_index in raw_indices:
            if isinstance(raw_index, int) and not isinstance(raw_index, bool):
                affected_indices.add(int(raw_index))
    base_index = mutation.get("geometry_index")
    geometry_added = int(mutation.get("geometry_added") or 0)
    if isinstance(base_index, int) and not isinstance(base_index, bool):
        span = max(1, geometry_added)
        affected_indices.update(range(int(base_index), int(base_index) + span))
    handle_table = []
    for index in sorted(affected_indices):
        if index < 0 or index >= len(geometry):
            continue
        summary = service._geometry_summary(geometry[index], index, updated)
        handle_table.append(
            {
                key: summary[key]
                for key in (
                    "index",
                    "index_handle",
                    "handle",
                    "geometry_id",
                    "type",
                    "construction",
                )
                if key in summary
            }
        )
    diagnostics = recompute_diagnostics(transaction)
    incomplete_edit = bool(
        not profile.get("closed_profile")
        and int(profile.get("open_wire_count") or 0) > 0
    )
    envelope = {
        "ok": bool(transaction.get("ok")),
        "sketch": getattr(sketch, "Name", None),
        "mutation": mutation,
        "document_delta": transaction.get("document_delta") or {},
        "state_change": transaction.get("state_change") or {},
        "native_diagnostics": diagnostics,
        "profile_status": profile,
        "solver_status": solver,
        "affected_geometry_handles": handle_table,
        "incomplete_edit": incomplete_edit,
    }
    for key in ("failure_code", "failure_stage"):
        if transaction.get(key) not in (None, "", [], {}):
            envelope[key] = transaction[key]
    if transaction.get("error"):
        envelope["error"] = str(transaction["error"])
    return envelope


def geometry_metadata(sketch: Any) -> dict[str, Any]:
    raw = getattr(sketch, GEOMETRY_METADATA_PROPERTY, "") or ""
    if not raw:
        return {"names": {}}
    try:
        parsed = json.loads(str(raw))
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"Sketch {getattr(sketch, 'Name', '<unnamed>')} has invalid "
            f"{GEOMETRY_METADATA_PROPERTY} JSON: {exc}"
        ) from exc
    if not isinstance(parsed, dict):
        raise ValueError(
            f"Sketch {getattr(sketch, 'Name', '<unnamed>')} has non-object "
            f"{GEOMETRY_METADATA_PROPERTY} data."
        )
    names = parsed.get("names")
    if not isinstance(names, dict):
        raise ValueError(
            f"Sketch {getattr(sketch, 'Name', '<unnamed>')} has invalid "
            f"{GEOMETRY_METADATA_PROPERTY}.names data."
        )
    return parsed


def set_geometry_metadata(sketch: Any, metadata: dict[str, Any]) -> None:
    if not hasattr(sketch, GEOMETRY_METADATA_PROPERTY):
        sketch.addProperty(
            "App::PropertyString",
            GEOMETRY_METADATA_PROPERTY,
            "Cadex",
            "Cadex semantic geometry handle metadata.",
        )
    setattr(sketch, GEOMETRY_METADATA_PROPERTY, json.dumps(metadata, sort_keys=True))


def _rounded_point(value: Any) -> list[float] | None:
    if value is None:
        return None
    return [
        round(float(value[0]), 6),
        round(float(value[1]), 6),
        round(float(value[2]), 6),
    ]


def geometry_fingerprint(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "type",
        "construction",
        "start",
        "end",
        "center",
        "radius",
        "major_radius",
        "minor_radius",
        "poles",
    )
    fingerprint: dict[str, Any] = {}
    for key in keys:
        if key not in summary:
            continue
        value = summary[key]
        if key in {"start", "end", "center"}:
            fingerprint[key] = _rounded_point(value)
        elif key == "poles" and isinstance(value, list):
            fingerprint[key] = [_rounded_point(point) for point in value]
        elif isinstance(value, float):
            fingerprint[key] = round(value, 6)
        else:
            fingerprint[key] = value
    return fingerprint


def geometry_inventory(service: Any, sketch: Any) -> list[dict[str, Any]]:
    summary = service.sketcher_summary(getattr(sketch, "Name", None))
    geometry = [dict(item) for item in summary.get("geometry", [])]
    metadata = geometry_metadata(sketch)
    names = metadata.get("names", {})
    current_by_name = resolve_geometry_names(service, sketch, include_missing=False)
    for item in geometry:
        index = item.get("index")
        item["index_handle"] = f"geometry:{index}"
        item["stable_handle"] = geometry_handle(sketch, int(index))
        item["fingerprint"] = geometry_fingerprint(item)
        item_names = [
            str(name)
            for name, resolved in current_by_name.items()
            if resolved.get("ok") and resolved.get("geometry_index") == index
        ]
        if item_names:
            item["names"] = sorted(item_names)
            item["semantic_handles"] = [f"name:{name}" for name in sorted(item_names)]
    if names:
        missing = resolve_geometry_names(service, sketch, include_missing=True)
        unresolved = {
            name: data for name, data in missing.items() if not data.get("ok")
        }
        if unresolved:
            for item in geometry:
                item.setdefault("unresolved_named_geometry", unresolved)
                break
    return geometry


def constraint_inventory(service: Any, sketch: Any) -> list[dict[str, Any]]:
    """Return constraints with references resolved through native geometry tags."""
    summary = service.sketcher_summary(getattr(sketch, "Name", None))
    constraints = [dict(item) for item in summary.get("constraints", [])]
    geometry = list(getattr(sketch, "Geometry", []) or [])
    handles: dict[int, str] = {}
    for index in range(len(geometry)):
        try:
            handles[index] = geometry_handle(sketch, index)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            handles[index] = f"geometry:{index}"

    def referenced_geometry(value: Any) -> Any:
        if isinstance(value, bool) or not isinstance(value, int):
            return value
        return handles.get(value, value)

    for item in constraints:
        index = int(item.get("index", -1))
        item["index"] = index
        item["index_handle"] = f"constraint:{index}"
        name = str(item.get("name") or "").strip()
        item["stable_handle"] = f"name:{name}" if name else None
        semantic = {
            "type": item.get("type"),
            "name": name,
            "driving": item.get("driving"),
        }
        for ordinal in ("first", "second", "third"):
            if ordinal in item:
                semantic[ordinal] = referenced_geometry(item.get(ordinal))
            position = f"{ordinal}pos"
            if position in item:
                semantic[position] = item.get(position)
        if "value" in item:
            try:
                semantic["value"] = round(float(item["value"]), 12)
            except (TypeError, ValueError):
                semantic["value"] = item["value"]
        item["semantic_fingerprint"] = semantic
        item["identity_key"] = json.dumps(semantic, sort_keys=True, separators=(",", ":"))
    return constraints


def collection_change_map(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    *,
    identity_field: str,
) -> dict[str, Any]:
    """Map a collection using native/stable identities, including duplicates."""
    remaining: dict[str, list[int]] = {}
    for item in after:
        key = str(item.get(identity_field) or "")
        remaining.setdefault(key, []).append(int(item["index"]))
    old_to_new: dict[str, int] = {}
    deleted: list[dict[str, Any]] = []
    for item in before:
        old_index = int(item["index"])
        key = str(item.get(identity_field) or "")
        matches = remaining.get(key) or []
        if matches:
            old_to_new[str(old_index)] = matches.pop(0)
        else:
            deleted.append(item)
    mapped_new = set(old_to_new.values())
    created = [item for item in after if int(item["index"]) not in mapped_new]
    return {
        "identity_field": identity_field,
        "old_to_new": old_to_new,
        "deleted": deleted,
        "created": created,
        "before_count": len(before),
        "after_count": len(after),
    }


def sketch_collection_maps(
    service: Any,
    sketch: Any,
    before_geometry: list[dict[str, Any]],
    before_constraints: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return read-back maps after one native Sketcher mutation."""
    after_geometry = geometry_inventory(service, sketch)
    after_constraints = constraint_inventory(service, sketch)
    return {
        "geometry": collection_change_map(
            before_geometry,
            after_geometry,
            identity_field="stable_handle",
        ),
        "constraints": collection_change_map(
            before_constraints,
            after_constraints,
            identity_field="identity_key",
        ),
        "geometry_after": after_geometry,
        "constraints_after": after_constraints,
    }


def resolve_geometry_names(
    service: Any,
    sketch: Any,
    include_missing: bool = True,
) -> dict[str, dict[str, Any]]:
    metadata = geometry_metadata(sketch)
    names = metadata.get("names", {})
    if not isinstance(names, dict):
        return {}
    summary = service.sketcher_summary(getattr(sketch, "Name", None))
    geometry = list(summary.get("geometry", []))
    result: dict[str, dict[str, Any]] = {}
    for raw_name, record in names.items():
        name = str(raw_name)
        if not isinstance(record, dict):
            continue
        stored_fingerprint = record.get("fingerprint")
        preferred_index = record.get("index")
        if isinstance(preferred_index, int) and 0 <= preferred_index < len(geometry):
            current = geometry_fingerprint(geometry[preferred_index])
            if current == stored_fingerprint:
                result[name] = {
                    "ok": True,
                    "name": name,
                    "geometry_index": preferred_index,
                    "geometry": geometry[preferred_index],
                    "match": "preferred_index",
                }
                continue
        matches = [
            item
            for item in geometry
            if geometry_fingerprint(item) == stored_fingerprint
        ]
        if len(matches) == 1:
            result[name] = {
                "ok": True,
                "name": name,
                "geometry_index": int(matches[0]["index"]),
                "geometry": matches[0],
                "match": "fingerprint",
            }
            continue
        if include_missing:
            result[name] = {
                "ok": False,
                "name": name,
                "error": "Named geometry is missing or ambiguous after sketch topology changed.",
                "match_count": len(matches),
                "stored_index": preferred_index,
                "stored_fingerprint": stored_fingerprint,
            }
    return result


def resolve_geometry_index(
    service: Any,
    sketch: Any,
    geometry_index: int | None = None,
    geometry_handle: str | None = None,
) -> int:
    if geometry_handle is None or str(geometry_handle).strip() == "":
        if geometry_index is None:
            raise ValueError("geometry_index or geometry_handle is required.")
        return int(geometry_index)
    handle = str(geometry_handle).strip()
    clean = handle.lower()
    if clean == "origin":
        return -1
    if clean == "axis:h":
        return -1
    if clean == "axis:v":
        return -2
    if clean.startswith("external:"):
        return -3 - int(clean.split(":", 1)[1])
    if clean.startswith("tag:"):
        requested_tag = handle.split(":", 1)[1]
        matches = [
            index
            for index, facade in enumerate(
                list(getattr(sketch, "GeometryFacadeList", []) or [])
            )
            if str(getattr(facade, "Tag", "") or "") == requested_tag
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Native geometry tag did not resolve uniquely: {handle}. "
                f"match_count={len(matches)}"
            )
        return int(matches[0])
    if clean.startswith("id:"):
        requested_id = int(clean.split(":", 1)[1])
        matches = [
            index
            for index, facade in enumerate(
                list(getattr(sketch, "GeometryFacadeList", []) or [])
            )
            if int(getattr(facade, "Id")) == requested_id
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Native geometry id did not resolve uniquely: {handle}. "
                f"match_count={len(matches)}"
            )
        return int(matches[0])
    if handle.startswith("geometry:"):
        return int(handle.split(":", 1)[1])
    if handle.startswith("name:"):
        name = handle.split(":", 1)[1]
    else:
        name = handle
    resolved = resolve_geometry_names(service, sketch, include_missing=True).get(name)
    if not resolved or not resolved.get("ok"):
        raise ValueError(
            f"Geometry handle could not be resolved: {handle}. {resolved or {}}"
        )
    return int(resolved["geometry_index"])


def geometry_handle(sketch: Any, geometry_index: int) -> str:
    index = int(geometry_index)
    facades = list(getattr(sketch, "GeometryFacadeList", []) or [])
    if index < 0 or index >= len(facades):
        raise ValueError(f"Geometry index {index} is outside the active sketch.")
    tag = str(getattr(facades[index], "Tag", "") or "").strip()
    if not tag:
        raise ValueError(f"Sketch geometry {index} has no native GeometryFacade tag.")
    return f"tag:{tag}"


def find_document_object(service: Any, object_name: str | None) -> Any:
    if not object_name:
        return None
    doc = service._active_document()
    if doc is None:
        return None
    target = doc.getObject(str(object_name))
    return target


def external_geometry_summary(sketch: Any) -> list[dict[str, Any]]:
    external = list(getattr(sketch, "ExternalGeometry", []) or [])
    result: list[dict[str, Any]] = []
    for index, item in enumerate(external):
        source = None
        subelements: tuple[str, ...] = ()
        if isinstance(item, tuple) and len(item) >= 2:
            source = item[0]
            raw_subs = item[1]
            if isinstance(raw_subs, str):
                subelements = (raw_subs,)
            else:
                try:
                    subelements = tuple(str(value) for value in raw_subs)
                except Exception:
                    subelements = (str(raw_subs),)
        result.append(
            {
                "external_index": index,
                "external_geometry_id": -index - 1,
                "source_object": getattr(source, "Name", None),
                "source_label": getattr(source, "Label", getattr(source, "Name", None)),
                "source_type": getattr(source, "TypeId", None),
                "subelements": list(subelements),
            }
        )
    return result


def subelement_references(obj: Any) -> list[dict[str, Any]]:
    shape = getattr(obj, "Shape", None)
    if shape is None:
        return []
    refs: list[dict[str, Any]] = []
    for prefix, attr in (("Vertex", "Vertexes"), ("Edge", "Edges"), ("Face", "Faces")):
        items = list(getattr(shape, attr, []) or [])
        for offset, item in enumerate(items, start=1):
            entry: dict[str, Any] = {
                "subelement": f"{prefix}{offset}",
                "kind": prefix.lower(),
                "geometry_type": type(
                    getattr(item, "Curve", getattr(item, "Surface", item))
                ).__name__,
            }
            field_errors: list[dict[str, str]] = []
            try:
                center = getattr(item, "CenterOfMass", None)
                if center is not None:
                    entry["center"] = [
                        float(center.x),
                        float(center.y),
                        float(center.z),
                    ]
            except Exception as exc:
                field_errors.append({"field": "center", "error": str(exc)})
            if prefix == "Edge":
                try:
                    entry["length"] = float(item.Length)
                except Exception as exc:
                    field_errors.append({"field": "length", "error": str(exc)})
            if prefix == "Face":
                try:
                    entry["area"] = float(item.Area)
                except Exception as exc:
                    field_errors.append({"field": "area", "error": str(exc)})
            try:
                bounds = item.BoundBox
                entry["bounds"] = {
                    "min": [float(bounds.XMin), float(bounds.YMin), float(bounds.ZMin)],
                    "max": [float(bounds.XMax), float(bounds.YMax), float(bounds.ZMax)],
                    "size": [
                        float(bounds.XLength),
                        float(bounds.YLength),
                        float(bounds.ZLength),
                    ],
                }
            except Exception as exc:
                field_errors.append({"field": "bounds", "error": str(exc)})
            if field_errors:
                entry["field_errors"] = field_errors
            refs.append(entry)
    return refs


def solver_status(service: Any, sketch: Any | None) -> dict[str, Any]:
    if sketch is None:
        return {"found": False, "error": "Sketch not found."}
    field_diagnostics: list[dict[str, str]] = []
    try:
        degrees_of_freedom = int(getattr(sketch, "DoF"))
    except Exception as exc:
        degrees_of_freedom = None
        field_diagnostics.append({"field": "DoF", "error": str(exc)})
    constraints = list(getattr(sketch, "Constraints", []) or [])
    geometry = list(getattr(sketch, "Geometry", []) or [])
    has_geometry = bool(geometry)
    fully_constrained = bool(
        has_geometry and degrees_of_freedom is not None and degrees_of_freedom == 0
    )
    under_constrained = bool(
        has_geometry and degrees_of_freedom is not None and degrees_of_freedom > 0
    )
    status = {
        "found": True,
        "sketch": getattr(sketch, "Name", None),
        "sketch_label": getattr(sketch, "Label", getattr(sketch, "Name", None)),
        "geometry_count": len(geometry),
        "constraint_count": len(constraints),
        "degrees_of_freedom": degrees_of_freedom,
        "constraint_state": (
            "empty"
            if not has_geometry
            else "fully_constrained"
            if fully_constrained
            else "under_constrained"
            if under_constrained
            else "unknown"
        ),
        "fully_constrained": fully_constrained,
        "under_constrained": under_constrained,
        "solver_message": None,
        "conflicting_constraint_indices": [],
        "redundant_constraint_indices": [],
        "field_diagnostics": field_diagnostics,
    }
    for attr, key in (
        ("ConflictingConstraints", "conflicting_constraint_indices"),
        ("RedundantConstraints", "redundant_constraint_indices"),
    ):
        try:
            values = getattr(sketch, attr)
        except Exception as exc:
            field_diagnostics.append({"field": attr, "error": str(exc)})
            continue
        if values:
            try:
                status[key] = [int(item) for item in values]
            except Exception as exc:
                field_diagnostics.append({"field": attr, "error": str(exc)})
    return status


def profile_validation(service: Any, sketch: Any | None) -> dict[str, Any]:
    if sketch is None:
        return {"found": False, "error": "Sketch not found."}
    profile_status = service._sketch_profile_status(sketch)
    return {
        **profile_status,
        "diagnostic_source": "SketchObject.getProfileDiagnostics",
    }


def vector2(raw: list[float], index: int, label: str):
    if len(raw) < 2:
        raise ValueError(f"{label} point {index} must contain x and y.")
    import FreeCAD as App

    return App.Vector(float(raw[0]), float(raw[1]), 0.0)


def validate_geometry_index(sketch: Any, geometry_index: int) -> dict[str, Any] | None:
    geometry = list(getattr(sketch, "Geometry", []))
    index = int(geometry_index)
    if index < 0 or index >= len(geometry):
        return {
            "ok": False,
            "error": f"Geometry index out of range: {index}",
            "geometry_count": len(geometry),
        }
    return None


def validate_constraint_index(
    sketch: Any, constraint_index: int
) -> dict[str, Any] | None:
    constraints = list(getattr(sketch, "Constraints", []))
    index = int(constraint_index)
    if index < 0 or index >= len(constraints):
        return {
            "ok": False,
            "error": f"Constraint index out of range: {index}",
            "constraint_count": len(constraints),
        }
    return None


def resolve_constraint_index(
    sketch: Any,
    constraint_index: int | None = None,
    constraint_name: str | None = None,
    constraint_handle: str | None = None,
) -> int:
    if constraint_handle:
        handle = str(constraint_handle).strip()
        if handle.startswith("constraint:"):
            return int(handle.split(":", 1)[1])
        constraint_name = handle[5:] if handle.startswith("name:") else handle
    if constraint_name:
        return int(sketch.getIndexByName(str(constraint_name)))
    if constraint_index is None:
        raise ValueError(
            "constraint_index, constraint_name, or constraint_handle is required."
        )
    return int(constraint_index)


__all__ = [
    "active_response",
    "external_geometry_summary",
    "find_document_object",
    "geometry_fingerprint",
    "geometry_inventory",
    "geometry_metadata",
    "geometry_handle",
    "get_sketch",
    "no_sketch",
    "profile_validation",
    "resolve_geometry_index",
    "resolve_geometry_names",
    "run_freecad_transaction",
    "set_geometry_metadata",
    "solver_status",
    "resolve_constraint_index",
    "subelement_references",
    "validate_constraint_index",
    "validate_geometry_index",
    "vector2",
]
