# SPDX-License-Identifier: LGPL-2.1-or-later

"""Create one native Sketcher sketch owned by an explicit PartDesign Body."""

from __future__ import annotations

from typing import Any

from CadexTransactions import run_freecad_transaction

from . import domain_runtime, partdesign_find_subelements


_ORIGIN_PLANES = ("XY_Plane", "XZ_Plane", "YZ_Plane")

_VECTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "x": {"type": "number", "description": "X component"},
        "y": {"type": "number", "description": "Y component"},
        "z": {"type": "number", "description": "Z component"},
    },
    "required": ["x", "y", "z"],
    "additionalProperties": False,
}

TOOL_SPEC = {
    "name": "partdesign.create_sketch",
    "description": (
        "Create one native Sketcher sketch inside an explicitly named PartDesign "
        "Body. Attach it to a Body origin plane, a datum plane in that Body, or one exact "
        "planar face. A face query is accepted only when it resolves uniquely; ambiguous "
        "queries return candidates and create nothing. This creates the sketch object but "
        "does not enter sketch edit mode. When ready to author its geometry, pass the exact "
        "internal sketch name returned by this tool to partdesign.edit_sketch. Do not infer "
        "that geometry-authoring tools are unavailable merely because they are absent before "
        "edit mode; opening the sketch refreshes the live tool surface with Sketcher geometry "
        "and constraint tools."
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
                "description": "Exact internal PartDesign Body name from current CAD state.",
            },
            "label": {"type": "string", "description": "Visible label for the new sketch."},
            "support": {
                "description": "Exactly one native sketch support variant.",
                "oneOf": [
                    {
                        "type": "object",
                        "properties": {
                            "type": {"const": "origin_plane"},
                            "plane": {"type": "string", "enum": list(_ORIGIN_PLANES)},
                        },
                        "required": ["type", "plane"],
                        "additionalProperties": False,
                    },
                    {
                        "type": "object",
                        "properties": {
                            "type": {"const": "datum_plane"},
                            "object_name": {"type": "string", "minLength": 1},
                        },
                        "required": ["type", "object_name"],
                        "additionalProperties": False,
                    },
                    {
                        "type": "object",
                        "properties": {
                            "type": {"const": "planar_face"},
                            "object_name": {"type": "string", "minLength": 1},
                            "selection": {
                                "oneOf": [
                                    {
                                        "type": "object",
                                        "properties": {
                                            "type": {"const": "exact"},
                                            "subelement": {
                                                "type": "string",
                                                "pattern": "^Face[1-9][0-9]*$",
                                            },
                                        },
                                        "required": ["type", "subelement"],
                                        "additionalProperties": False,
                                    },
                                    {
                                        "type": "object",
                                        "properties": {
                                            "type": {"const": "query"},
                                            "normal": _VECTOR_SCHEMA,
                                            "near_point": _VECTOR_SCHEMA,
                                            "normal_tolerance_degrees": {
                                                "type": "number",
                                                "minimum": 0,
                                                "maximum": 180,
                                            },
                                            "max_distance": {
                                                "type": "number",
                                                "minimum": 0,
                                            },
                                        },
                                        "required": ["type"],
                                        "anyOf": [
                                            {"required": ["normal"]},
                                            {"required": ["near_point"]},
                                        ],
                                        "additionalProperties": False,
                                    },
                                ]
                            },
                        },
                        "required": ["type", "object_name", "selection"],
                        "additionalProperties": False,
                    },
                ],
            },
        },
        "required": ["body_name", "label", "support"],
        "additionalProperties": False,
    },
}


def run(
    service: Any,
    body_name: str,
    label: str,
    support: dict[str, Any],
) -> dict[str, Any]:
    clean_label = str(label or "").strip()
    if not clean_label:
        return _invalid("label is required.")
    clean_support_type = str(support.get("type") or "").strip()
    if clean_support_type not in {"origin_plane", "datum_plane", "planar_face"}:
        return _invalid(
            "support_type must be origin_plane, datum_plane, or planar_face."
        )
    body = service._get_partdesign_body(body_name)
    if body is None:
        return _invalid(
            f"PartDesign Body not found by exact internal name: {body_name}",
            requested_body=body_name,
        )
    body_block = domain_runtime.invalid_partdesign_tip(body)
    if body_block is not None:
        return {
            "ok": False,
            "error": "The target Body has an invalid Tip; repair or delete that feature before adding a sketch.",
            "body": body.Name,
            "tip_state": body_block,
            "retry_same_call": False,
        }

    support_resolution = _resolve_support(
        service,
        body,
        clean_support_type,
        support=support,
    )
    if not support_resolution.get("ok"):
        return support_resolution
    support = support_resolution["object"]
    support_subelement = str(support_resolution.get("subelement") or "")

    def create() -> dict[str, Any]:
        import FreeCAD as App

        doc = App.ActiveDocument
        if doc is None:
            raise RuntimeError("No active document. Create or open a document in FreeCAD first.")
        target_body = service._get_partdesign_body(body.Name)
        if target_body is None:
            raise RuntimeError(f"PartDesign Body no longer exists: {body.Name}")
        target_support = doc.getObject(support.Name)
        if target_support is None:
            raise RuntimeError(f"Sketch support no longer exists: {support.Name}")

        sketch = target_body.newObject("Sketcher::SketchObject", "Sketch")
        sketch.Label = clean_label
        sketch.AttachmentSupport = (target_support, [support_subelement])
        sketch.MapMode = "FlatFace"
        doc.recompute()
        actual_support = _actual_support(sketch)
        owner = sketch.getParentGeoFeatureGroup()
        placement = sketch.getGlobalPlacement()
        normal = placement.Rotation.multVec(App.Vector(0.0, 0.0, 1.0))
        global_plane = {
            "origin": [
                float(placement.Base.x),
                float(placement.Base.y),
                float(placement.Base.z),
            ],
            "normal": [float(normal.x), float(normal.y), float(normal.z)],
        }
        return {
            "document": doc.Name,
            "body": target_body.Name,
            "sketch": sketch.Name,
            "sketch_label": sketch.Label,
            "support_type": clean_support_type,
            "support_object": target_support.Name,
            "subelement": support_subelement,
            "map_mode": str(sketch.MapMode),
            "requested_support": support_resolution["requested"],
            "resolved_support": support_resolution["resolved"],
            "actual_attachment": actual_support,
            "global_sketch_plane": global_plane,
            "owner_body": getattr(owner, "Name", None),
            "native_state": domain_runtime.feature_state_summary(sketch),
            "body_group": [item.Name for item in list(target_body.Group)],
            "body_tip": getattr(getattr(target_body, "Tip", None), "Name", None),
        }

    def verify(result: dict[str, Any]) -> dict[str, Any]:
        expected = support_resolution["resolved"]
        actual = result.get("actual_attachment") or {}
        checks = [
            {
                "name": "body_membership",
                "ok": result.get("owner_body") == body.Name
                and result.get("sketch") in result.get("body_group", []),
            },
            {
                "name": "attachment_support",
                "ok": actual.get("object_name") == expected.get("object_name")
                and actual.get("subelements") == expected.get("subelements"),
                "expected": expected,
                "actual": actual,
            },
            {
                "name": "map_mode",
                "ok": result.get("map_mode") == "FlatFace",
                "actual": result.get("map_mode"),
            },
            {
                "name": "native_state",
                "ok": not bool((result.get("native_state") or {}).get("marked_invalid")),
            },
        ]
        return {"ok": all(item["ok"] for item in checks), "checks": checks}

    transaction = run_freecad_transaction(
        f"Create PartDesign sketch: {clean_label}",
        create,
        verifier=verify,
    )
    result = transaction.get("result") if isinstance(transaction.get("result"), dict) else {}
    response = {
        "ok": bool(transaction.get("ok")),
        "mutation": result,
        "document_delta": transaction.get("document_delta") or {},
        "native_diagnostics": domain_runtime.recompute_diagnostics(transaction),
    }
    if not response["ok"]:
        response["error"] = transaction.get("error") or "PartDesign sketch creation failed."
    return response


def _resolve_support(
    service: Any,
    body: Any,
    support_type: str,
    *,
    support: dict[str, Any],
) -> dict[str, Any]:
    if support_type == "origin_plane":
        requested_plane = str(support.get("plane") or "").strip()
        if requested_plane not in _ORIGIN_PLANES:
            return _invalid(
                "plane is required for origin_plane support and must be XY_Plane, XZ_Plane, or YZ_Plane."
            )
        origin_plane = service._partdesign_origin_feature(body, requested_plane)
        if origin_plane is None:
            return _invalid(f"Body origin plane not found: {requested_plane}")
        return {
            "ok": True,
            "object": origin_plane,
            "subelement": "",
            "resolution": "exact_origin_plane",
            "requested": dict(support),
            "resolved": {
                "object_name": origin_plane.Name,
                "subelements": [],
                "type": "origin_plane",
            },
        }

    object_name = str(support.get("object_name") or "").strip()
    if not object_name:
        return _invalid(f"support_object is required for {support_type} support.")
    doc = service._active_document()
    target = doc.getObject(object_name) if doc is not None else None
    if target is None:
        return _invalid(f"Support object not found by exact internal name: {object_name}")
    owner = service._partdesign_body_for_feature(target)
    if owner is not body:
        return _invalid(
            f"Support object {target.Name} is not owned by Body {body.Name}.",
            support_owner=getattr(owner, "Name", None),
            target_body=body.Name,
        )

    if support_type == "datum_plane":
        if getattr(target, "TypeId", "") != "PartDesign::Plane":
            return _invalid(
                f"Support object {target.Name} is {target.TypeId}, not PartDesign::Plane."
            )
        return {
            "ok": True,
            "object": target,
            "subelement": "",
            "resolution": "exact_datum_plane",
            "requested": dict(support),
            "resolved": {
                "object_name": target.Name,
                "subelements": [],
                "type": "datum_plane",
            },
        }

    selection = support.get("selection")
    if not isinstance(selection, dict):
        return _invalid("planar_face support requires one structured selection.")
    selection_type = str(selection.get("type") or "")
    requested_face = (
        str(selection.get("subelement") or "").strip()
        if selection_type == "exact"
        else ""
    )
    normal = selection.get("normal") if selection_type == "query" else None
    near_point = selection.get("near_point") if selection_type == "query" else None
    query = partdesign_find_subelements.run(
        service,
        object_name=target.Name,
        element_type="face",
        geometry_type="plane",
        normal=normal,
        normal_tolerance_degrees=float(
            selection.get("normal_tolerance_degrees", 5.0)
        ),
        near_point=near_point,
        max_distance=float(selection.get("max_distance", 1.0)),
    )
    if not query.get("ok"):
        return {
            "ok": False,
            "error": query.get("error") or "Planar-face query failed.",
            "face_query": query,
            "retry_same_call": False,
        }
    matches = [item for item in query.get("matches", []) if isinstance(item, dict)]
    if requested_face:
        selected = next((item for item in matches if item.get("name") == requested_face), None)
        if selected is None:
            return {
                "ok": False,
                "error": f"{requested_face} is not a matching planar face on {target.Name}.",
                "candidates": matches,
                "retry_same_call": False,
            }
    elif len(matches) == 1:
        selected = matches[0]
    elif not matches:
        return {
            "ok": False,
            "error": f"No planar face on {target.Name} matches the supplied query.",
            "candidates": [],
            "retry_same_call": False,
        }
    else:
        return {
            "ok": False,
            "error": (
                f"Planar-face query is ambiguous on {target.Name}; provide one candidate's "
                "exact subelement name."
            ),
            "candidates": matches,
            "retry_same_call": False,
        }
    return {
        "ok": True,
        "object": target,
        "subelement": str(selected["name"]),
        "resolution": "exact_face" if requested_face else "unique_face_query",
        "selected": selected,
        "requested": dict(support),
        "resolved": {
            "object_name": target.Name,
            "subelements": [str(selected["name"])],
            "type": "planar_face",
            "geometry": selected,
        },
    }


def _actual_support(sketch: Any) -> dict[str, Any]:
    raw = getattr(sketch, "AttachmentSupport", None)
    if not raw:
        return {"object_name": None, "subelements": []}
    if isinstance(raw, (list, tuple)) and raw and hasattr(raw[0], "Name"):
        source = raw[0]
        subelements = raw[1] if len(raw) > 1 else []
    elif (
        isinstance(raw, (list, tuple))
        and raw
        and isinstance(raw[0], (list, tuple))
        and raw[0]
    ):
        source = raw[0][0]
        subelements = raw[0][1] if len(raw[0]) > 1 else []
    else:
        return {"object_name": None, "subelements": []}
    return {
        "object_name": getattr(source, "Name", None),
        "subelements": [str(item) for item in list(subelements or []) if str(item)],
    }


def _invalid(message: str, **details: Any) -> dict[str, Any]:
    return {
        "ok": False,
        "error": message,
        "retry_same_call": False,
        **details,
    }
