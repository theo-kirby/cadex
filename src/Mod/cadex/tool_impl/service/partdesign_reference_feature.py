# SPDX-License-Identifier: LGPL-2.1-or-later

"""Shared native ShapeBinder and SubShapeBinder support."""

from __future__ import annotations

from typing import Any

from CadexTransactions import run_freecad_transaction

from . import domain_runtime, partdesign_find_subelements


REFERENCE_SCHEMA = {
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "mode": {"const": "whole"},
                "object_name": {"type": "string", "minLength": 1},
            },
            "required": ["mode", "object_name"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "mode": {"const": "exact"},
                "object_name": {"type": "string", "minLength": 1},
                "subelements": {
                    "type": "array",
                    "items": {"type": "string", "pattern": "^(Face|Edge|Vertex)[1-9][0-9]*$"},
                    "minItems": 1,
                    "uniqueItems": True,
                },
            },
            "required": ["mode", "object_name", "subelements"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "mode": {"const": "query"},
                "object_name": {"type": "string", "minLength": 1},
                "element_type": {"type": "string", "enum": ["face", "edge"]},
                "expected_count": {"type": "integer", "minimum": 1},
                "geometry_type": {
                    "type": "string",
                    "enum": ["plane", "cylinder", "cone", "sphere", "torus", "bspline", "line", "circle", "ellipse"],
                },
                "radius": {"type": "number", "minimum": 0},
                "min_area": {"type": "number", "minimum": 0},
                "max_area": {"type": "number", "minimum": 0},
                "min_length": {"type": "number", "minimum": 0},
                "max_length": {"type": "number", "minimum": 0},
            },
            "required": ["mode", "object_name", "element_type", "expected_count"],
            "additionalProperties": False,
        },
    ]
}


def run(
    service: Any,
    *,
    operation: str,
    type_id: str,
    body_name: str,
    label: str,
    references: list[dict[str, Any]],
    trace_support: bool = False,
    fuse: bool = False,
    make_face: bool = True,
    offset: float = 0.0,
    offset_join: str = "arcs",
    offset_fill: bool = False,
    offset_open_result: bool = False,
    offset_intersection: bool = False,
    relative: bool = True,
    bind_mode: str = "synchronized",
    partial_load: bool = False,
    copy_on_change: str = "disabled",
    refine: bool = True,
) -> dict[str, Any]:
    body = service._get_partdesign_body(str(body_name or "").strip())
    if body is None:
        return _invalid(f"Body not found by exact internal name: {body_name}")
    clean_label = str(label or "").strip()
    if not clean_label:
        return _invalid("label is required.")
    resolved = _resolve_references(service, body, references)
    if not resolved.get("ok"):
        return resolved
    tip_block = domain_runtime.invalid_partdesign_tip(body)
    if tip_block is not None:
        return _invalid(
            "The target Body has an invalid or zero-effect Tip.",
            tip_state=tip_block,
        )
    config = _validate_config(
        operation,
        offset=offset,
        offset_join=offset_join,
        bind_mode=bind_mode,
        copy_on_change=copy_on_change,
    )
    if not config.get("ok"):
        return config

    def create() -> dict[str, Any]:
        import FreeCAD as App

        doc = App.ActiveDocument
        target_body = service._get_partdesign_body(body.Name)
        if doc is None or target_body is None:
            raise RuntimeError("Document or target Body no longer exists.")
        native_references = []
        for item in resolved["references"]:
            source = doc.getObject(item["object_name"])
            if source is None:
                raise RuntimeError(f"Binder source no longer exists: {item['object_name']}")
            native_references.append((source, list(item["subelements"])))
        native_name = "ShapeBinder" if operation == "shape_binder" else "SubShapeBinder"
        binder = target_body.newObject(type_id, native_name)
        binder.Label = clean_label
        binder.Support = native_references
        if operation == "shape_binder":
            binder.TraceSupport = bool(trace_support)
        else:
            binder.Fuse = bool(fuse)
            binder.MakeFace = bool(make_face)
            binder.Offset = config["offset"]
            binder.OffsetJoinType = config["offset_join"]
            binder.OffsetFill = bool(offset_fill)
            binder.OffsetOpenResult = bool(offset_open_result)
            binder.OffsetIntersection = bool(offset_intersection)
            binder.Relative = bool(relative)
            binder.BindMode = config["bind_mode"]
            binder.PartialLoad = bool(partial_load)
            binder.BindCopyOnChange = config["copy_on_change"]
            binder.Refine = bool(refine)
        doc.recompute()
        state = domain_runtime.feature_state_summary(binder)
        shape = domain_runtime.shape_summary(binder)
        valid = (
            not state.get("marked_invalid")
            and state.get("shape_valid") is True
            and bool(shape.get("available"))
            and (
                int(shape.get("faces", 0) or 0) > 0
                or int(shape.get("edges", 0) or 0) > 0
                or int(shape.get("vertices", 0) or 0) > 0
            )
        )
        return {
            "document": doc.Name,
            "body": target_body.Name,
            "feature": binder.Name,
            "feature_label": binder.Label,
            "feature_type": binder.TypeId,
            "references": [
                {
                    "object_name": getattr(source, "Name", None),
                    "subelements": [str(value) for value in list(subelements or [])],
                }
                for source, subelements in list(binder.Support)
            ],
            "resolved_reference_facts": resolved["references"],
            "parameters": _parameter_summary(binder, operation),
            "feature_state": state,
            "feature_shape": shape,
            "reference_valid": bool(valid),
            "body_group": [item.Name for item in list(target_body.Group)],
            "body_tip": getattr(getattr(target_body, "Tip", None), "Name", None),
        }

    expected_support = [
        {
            "object_name": item["object_name"],
            "subelements": item["subelements"],
        }
        for item in resolved["references"]
    ]

    def verify(result: dict[str, Any]) -> dict[str, Any]:
        actual = result.get("references") or []
        checks = [
            {
                "name": "binder_support",
                "ok": actual == expected_support,
                "expected": expected_support,
                "actual": actual,
            },
            {
                "name": "referenced_geometry",
                "ok": bool(result.get("reference_valid")),
            },
        ]
        return {"ok": all(item["ok"] for item in checks), "checks": checks}

    transaction = run_freecad_transaction(
        f"Create PartDesign {operation}: {clean_label}",
        create,
        verifier=verify,
    )
    result = transaction.get("result") if isinstance(transaction.get("result"), dict) else {}
    ok = bool(transaction.get("ok")) and bool(result.get("reference_valid"))
    response = {
        "ok": ok,
        "operation": operation,
        "mutation": result,
        "document_delta": transaction.get("document_delta") or {},
        "native_diagnostics": domain_runtime.recompute_diagnostics(transaction),
        "body_state": service._partdesign_body_summary(
            service._get_partdesign_body(body.Name)
        ),
        "failed_feature_retained": bool(result.get("feature")) and not ok,
    }
    if not ok:
        response["error"] = (
            transaction.get("error")
            or f"PartDesign {operation} did not produce referenced geometry."
        )
        response["retry_same_call"] = False
    return response


def _resolve_references(
    service: Any,
    body: Any,
    references: Any,
) -> dict[str, Any]:
    if not isinstance(references, list) or not references:
        return _invalid("references must contain at least one exact object reference.")
    doc = service._active_document()
    resolved = []
    seen = set()
    for index, reference in enumerate(references):
        if not isinstance(reference, dict):
            return _invalid(f"references[{index}] must be an object.")
        object_name = str(reference.get("object_name") or "").strip()
        source = doc.getObject(object_name) if doc is not None else None
        if source is None:
            return _invalid(f"Binder source not found by exact internal name: {object_name}")
        if source == body:
            return _invalid("A Binder cannot reference its own target Body.")
        mode = str(reference.get("mode") or "")
        if mode == "whole":
            clean_subelements = []
            selected_summaries = []
        elif mode == "exact":
            subelements = reference.get("subelements")
            if not isinstance(subelements, list) or not subelements:
                return _invalid(
                    f"references[{index}].subelements must contain exact names."
                )
            clean_subelements = [str(value or "").strip() for value in subelements]
            selected_summaries = []
        elif mode == "query":
            expected = int(reference.get("expected_count") or 0)
            filters = {
                key: value
                for key, value in reference.items()
                if key
                not in {"mode", "object_name", "element_type", "expected_count"}
            }
            query = partdesign_find_subelements.run(
                service,
                object_name=source.Name,
                element_type=str(reference.get("element_type") or ""),
                **filters,
            )
            if not query.get("ok"):
                return _invalid(
                    f"references[{index}] geometric query failed.",
                    query_result=query,
                )
            selected_summaries = list(query.get("matches") or [])
            if len(selected_summaries) != expected:
                return _invalid(
                    f"references[{index}] query did not resolve to expected_count.",
                    expected_count=expected,
                    actual_count=len(selected_summaries),
                    candidates=selected_summaries,
                )
            clean_subelements = [str(item["name"]) for item in selected_summaries]
        else:
            return _invalid(
                f"references[{index}].mode must be whole, exact, or query."
            )
        key = (source.Name, tuple(clean_subelements))
        if key in seen:
            return _invalid("references cannot contain duplicate object/subelement sets.")
        seen.add(key)
        shape = getattr(source, "Shape", None)
        if shape is None or shape.isNull():
            return _invalid(f"Binder source {source.Name} has no shape.")
        for subelement in clean_subelements:
            if not subelement:
                return _invalid("Binder subelement names cannot be empty strings.")
            try:
                element = shape.getElement(subelement)
            except Exception:
                return _invalid(
                    f"Binder source subelement does not exist: {source.Name}.{subelement}",
                    candidates=_source_subelements(service, source),
                )
            if mode == "exact":
                selected_summaries.append(
                    _subelement_fact(source, subelement, element)
                )
        owner = service._partdesign_body_for_feature(source)
        owner_group = list(getattr(owner, "Group", []) or []) if owner is not None else []
        history_index = owner_group.index(source) if source in owner_group else None
        source_depends_on_target = body in list(
            getattr(source, "OutListRecursive", []) or []
        )
        if source_depends_on_target:
            return _invalid(
                "Binder reference would create a dependency cycle.",
                source=source.Name,
                target_body=body.Name,
                dependency_direction=f"{source.Name} -> {body.Name}",
            )
        resolved.append(
            {
                "object_name": source.Name,
                "subelements": clean_subelements,
                "selection_mode": mode,
                "subshape_summaries": selected_summaries,
                "source_owner": getattr(owner, "Name", None),
                "source_history_index": history_index,
                "target_insertion_index": len(list(body.Group)),
                "dependency_direction": f"new_binder -> {source.Name}",
                "cycle_check": {"ok": True},
            }
        )
    return {"ok": True, "references": resolved}


def _source_subelements(service: Any, source: Any) -> list[dict[str, Any]]:
    candidates = []
    for kind in ("face", "edge"):
        result = partdesign_find_subelements.run(
            service,
            object_name=source.Name,
            element_type=kind,
        )
        if result.get("ok"):
            candidates.extend(result.get("matches") or [])
    return candidates


def _subelement_fact(source: Any, name: str, element: Any) -> dict[str, Any]:
    geometry = getattr(element, "Surface", getattr(element, "Curve", None))
    return {
        "name": name,
        "geometry_type": partdesign_find_subelements._canonical_geometry_type(
            type(geometry).__name__ if geometry is not None else ""
        ),
        "bounds": partdesign_find_subelements._bounding_box_dict(element.BoundBox),
        "source": source.Name,
    }


def _validate_config(
    operation: str,
    *,
    offset: Any,
    offset_join: Any,
    bind_mode: Any,
    copy_on_change: Any,
) -> dict[str, Any]:
    if operation == "shape_binder":
        return {"ok": True}
    try:
        parsed_offset = float(offset)
    except (TypeError, ValueError):
        return _invalid("offset must be numeric.")
    native_join = {
        "arcs": "Arcs",
        "tangent": "Tangent",
        "intersection": "Intersection",
    }.get(str(offset_join or ""))
    native_bind = {
        "synchronized": "Synchronized",
        "frozen": "Frozen",
        "detached": "Detached",
    }.get(str(bind_mode or ""))
    native_copy = {
        "disabled": "Disabled",
        "enabled": "Enabled",
        "mutated": "Mutated",
    }.get(str(copy_on_change or ""))
    if native_join is None:
        return _invalid("offset_join must be arcs, tangent, or intersection.")
    if native_bind is None:
        return _invalid("bind_mode must be synchronized, frozen, or detached.")
    if native_copy is None:
        return _invalid("copy_on_change must be disabled, enabled, or mutated.")
    return {
        "ok": True,
        "offset": parsed_offset,
        "offset_join": native_join,
        "bind_mode": native_bind,
        "copy_on_change": native_copy,
    }


def _parameter_summary(binder: Any, operation: str) -> dict[str, Any]:
    if operation == "shape_binder":
        return {"trace_support": bool(binder.TraceSupport)}
    return {
        "fuse": bool(binder.Fuse),
        "make_face": bool(binder.MakeFace),
        "offset": float(binder.Offset),
        "offset_join": str(binder.OffsetJoinType),
        "offset_fill": bool(binder.OffsetFill),
        "offset_open_result": bool(binder.OffsetOpenResult),
        "offset_intersection": bool(binder.OffsetIntersection),
        "relative": bool(binder.Relative),
        "bind_mode": str(binder.BindMode),
        "partial_load": bool(binder.PartialLoad),
        "copy_on_change": str(binder.BindCopyOnChange),
        "refine": bool(binder.Refine),
    }


def _invalid(message: str, **details: Any) -> dict[str, Any]:
    return {"ok": False, "error": message, "retry_same_call": False, **details}
