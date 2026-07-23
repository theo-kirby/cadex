# SPDX-License-Identifier: LGPL-2.1-or-later

"""Create an associatively attached native PartDesign datum plane."""

from __future__ import annotations

from typing import Any

from CadexTransactions import run_freecad_transaction

from . import domain_runtime, partdesign_dressup_feature


_VECTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "x": {"type": "number", "description": "X component in mm"},
        "y": {"type": "number", "description": "Y component in mm"},
        "z": {"type": "number", "description": "Z component in mm"},
    },
    "required": ["x", "y", "z"],
    "additionalProperties": False,
}

_ORIGIN_PLANES = ("XY_Plane", "XZ_Plane", "YZ_Plane")

_FACE_SELECTION_SCHEMA = {
    **partdesign_dressup_feature.selection_schema(
        allow_all_edges=False,
        face_only=True,
        required_count=1,
    ),
    "description": (
        "Select exactly one planar support face. Prefer a geometric query with "
        "expected_count=1; use an exact FaceN name only when predicates cannot "
        "uniquely distinguish the face."
    ),
}

_SUPPORT_SCHEMA = {
    "description": "Associative support for the datum plane.",
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "type": {"const": "origin_plane"},
                "plane": {
                    "type": "string",
                    "enum": list(_ORIGIN_PLANES),
                    "description": "Body origin plane.",
                },
            },
            "required": ["type", "plane"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {"const": "datum_plane"},
                "object_name": {
                    "type": "string",
                    "description": "Exact internal name of an existing datum plane in this Body.",
                },
            },
            "required": ["type", "object_name"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {"const": "planar_face"},
                "object_name": {
                    "type": "string",
                    "description": "Exact internal name of the Body feature owning the face.",
                },
                "selection": _FACE_SELECTION_SCHEMA,
            },
            "required": ["type", "object_name", "selection"],
            "additionalProperties": False,
        },
    ],
}

TOOL_SPEC = {
    "name": "partdesign.create_datum_plane",
    "description": (
        "Create one native PartDesign datum plane associatively attached to a Body origin "
        "plane, an existing datum plane, or one count-guarded planar model face. Local "
        "translation and axis-angle rotation are applied in the support frame, so a normal "
        "offset follows upstream support changes."
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
            "label": {
                "type": "string",
                "description": "Visible label for the new datum plane.",
            },
            "support": _SUPPORT_SCHEMA,
            "offset": {
                **_VECTOR_SCHEMA,
                "description": (
                    "Translation in the support's local frame in mm. For a planar face, "
                    "positive local Z offsets along the attached plane normal."
                ),
            },
            "rotation_axis": {
                **_VECTOR_SCHEMA,
                "description": "Non-zero axis the plane rotates about.",
            },
            "rotation_degrees": {
                "type": "number",
                "description": "Rotation about rotation_axis; 0 for none.",
            },
        },
        "required": [
            "body_name",
            "label",
            "support",
            "offset",
            "rotation_axis",
            "rotation_degrees",
        ],
        "additionalProperties": False,
    },
}


def run(
    service: Any,
    body_name: str,
    label: str,
    support: dict[str, Any],
    offset: dict[str, float],
    rotation_axis: dict[str, float],
    rotation_degrees: float,
) -> dict[str, Any]:
    body = service._get_partdesign_body(body_name)
    if body is None:
        return _invalid(f"PartDesign Body not found: {body_name}")
    clean_label = str(label or "").strip()
    if not clean_label:
        return _invalid("label is required.")
    support_state = _resolve_support(service, body, support)
    if not support_state.get("ok"):
        return support_state
    support_object = support_state["object"]
    support_subelement = str(support_state.get("subelement") or "")
    parsed_offset = _vector(offset, "offset", allow_zero=True)
    if not parsed_offset.get("ok"):
        return parsed_offset
    parsed_axis = _vector(rotation_axis, "rotation_axis", allow_zero=False)
    if not parsed_axis.get("ok"):
        return parsed_axis
    tip_block = domain_runtime.invalid_partdesign_tip(body)
    if tip_block is not None:
        return _invalid(
            "The target Body has an invalid or zero-effect Tip.",
            tip_state=tip_block,
        )

    def create() -> dict[str, Any]:
        import FreeCAD as App

        doc = App.ActiveDocument
        if doc is None:
            raise RuntimeError("No active document.")
        target_body = service._get_partdesign_body(body.Name)
        target_support = doc.getObject(support_object.Name)
        if target_body is None or target_support is None:
            raise RuntimeError("Datum plane Body or support no longer exists.")
        datum = target_body.newObject("PartDesign::Plane", "DatumPlane")
        datum.Label = clean_label
        datum.AttachmentSupport = [(target_support, support_subelement)]
        datum.MapMode = "FlatFace"
        datum.AttachmentOffset = App.Placement(
            App.Vector(*parsed_offset["vector"]),
            App.Rotation(App.Vector(*parsed_axis["vector"]), float(rotation_degrees)),
        )
        doc.recompute()
        return {
            "document": doc.Name,
            "body": target_body.Name,
            "datum": datum.Name,
            "datum_label": datum.Label,
            "datum_type": datum.TypeId,
            "support_type": support_state["support_type"],
            "support": target_support.Name,
            "support_subelement": support_subelement,
            "support_resolution": support_state.get("resolution"),
            "resolved_support_geometry": support_state.get("resolved_geometry"),
            "map_mode": str(datum.MapMode),
            "attachment_offset": service._placement_summary(datum.AttachmentOffset),
            "state": [str(value) for value in list(datum.State)],
            "body_group": [item.Name for item in list(target_body.Group)],
            "body_tip": getattr(getattr(target_body, "Tip", None), "Name", None),
        }

    return _response(
        service,
        body,
        run_freecad_transaction(f"Create datum plane: {clean_label}", create),
    )


def _resolve_support(
    service: Any,
    body: Any,
    support: Any,
) -> dict[str, Any]:
    if not isinstance(support, dict):
        return _invalid("support must be one structured support object.")
    support_type = str(support.get("type") or "").strip()
    if support_type == "origin_plane":
        if set(support) != {"type", "plane"}:
            return _invalid("origin_plane support requires exactly type and plane.")
        plane_name = str(support.get("plane") or "").strip()
        if plane_name not in _ORIGIN_PLANES:
            return _invalid("support.plane must be XY_Plane, XZ_Plane, or YZ_Plane.")
        origin_plane = service._partdesign_origin_feature(body, plane_name)
        if origin_plane is None:
            return _invalid(f"Body origin plane not found: {plane_name}")
        return {
            "ok": True,
            "support_type": support_type,
            "object": origin_plane,
            "subelement": "",
            "resolution": "exact_origin_plane",
            "resolved_geometry": None,
        }

    if support_type not in {"datum_plane", "planar_face"}:
        return _invalid(
            "support.type must be origin_plane, datum_plane, or planar_face."
        )
    required_fields = (
        {"type", "object_name"}
        if support_type == "datum_plane"
        else {"type", "object_name", "selection"}
    )
    if set(support) != required_fields:
        return _invalid(
            f"{support_type} support requires exactly: "
            + ", ".join(sorted(required_fields))
            + "."
        )
    object_name = str(support.get("object_name") or "").strip()
    doc = service._active_document()
    target = doc.getObject(object_name) if doc is not None and object_name else None
    if target is None:
        return _invalid(
            f"Support object not found by exact internal name: {object_name}"
        )
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
            "support_type": support_type,
            "object": target,
            "subelement": "",
            "resolution": "exact_datum_plane",
            "resolved_geometry": None,
        }

    selection_state = partdesign_dressup_feature.resolve_selection(
        service,
        target,
        support.get("selection"),
        allow_all_edges=False,
        face_only=True,
    )
    if not selection_state.get("ok"):
        return _invalid(
            selection_state.get("error") or "Planar support-face selection failed.",
            support_selection=selection_state,
        )
    names = list(selection_state.get("subelements") or [])
    resolved = list(selection_state.get("resolved_geometry") or [])
    if len(names) != 1 or len(resolved) != 1:
        return _invalid(
            "Datum-plane support must resolve to exactly one face.",
            support_selection=selection_state,
        )
    selected = resolved[0]
    if str(selected.get("geometry_type") or "") != "plane":
        return _invalid(
            f"Selected support {target.Name}.{names[0]} is not planar.",
            selected_geometry=selected,
        )
    return {
        "ok": True,
        "support_type": support_type,
        "object": target,
        "subelement": names[0],
        "resolution": selection_state.get("mode"),
        "resolved_geometry": selected,
    }


def _vector(value: Any, name: str, *, allow_zero: bool) -> dict[str, Any]:
    try:
        vector = (float(value["x"]), float(value["y"]), float(value["z"]))
    except (KeyError, TypeError, ValueError):
        return _invalid(f"{name} requires numeric x, y, and z.")
    if not allow_zero and sum(component * component for component in vector) <= 1e-18:
        return _invalid(f"{name} must be non-zero.")
    return {"ok": True, "vector": vector}


def _response(service: Any, body: Any, transaction: dict[str, Any]) -> dict[str, Any]:
    result = (
        transaction.get("result") if isinstance(transaction.get("result"), dict) else {}
    )
    response = {
        "ok": bool(transaction.get("ok")),
        "mutation": result,
        "document_delta": transaction.get("document_delta") or {},
        "native_diagnostics": domain_runtime.recompute_diagnostics(transaction),
        "body_state": service._partdesign_body_summary(body),
    }
    if not response["ok"]:
        response["error"] = transaction.get("error") or "Datum plane creation failed."
        response["retry_same_call"] = False
    return response


def _invalid(message: str, **details: Any) -> dict[str, Any]:
    return {"ok": False, "error": message, "retry_same_call": False, **details}
