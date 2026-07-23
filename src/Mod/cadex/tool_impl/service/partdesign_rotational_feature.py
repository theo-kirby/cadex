# SPDX-License-Identifier: LGPL-2.1-or-later

"""Native Revolution/Groove implementation shared by focused tool contracts."""

from __future__ import annotations

from typing import Any

from CadexTransactions import run_freecad_transaction

from . import domain_runtime


AXIS_SCHEMA = {
    "description": "Rotation axis reference.",
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "source": {"const": "body_origin"},
                "axis": {"type": "string", "enum": ["X_Axis", "Y_Axis", "Z_Axis"]},
            },
            "required": ["source", "axis"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "source": {"const": "profile_axis"},
                "axis": {"type": "string", "enum": ["H_Axis", "V_Axis"]},
            },
            "required": ["source", "axis"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "source": {"const": "object_edge"},
                "object_name": {"type": "string", "minLength": 1},
                "subelement": {"type": "string", "pattern": "^Edge[1-9][0-9]*$"},
            },
            "required": ["source", "object_name", "subelement"],
            "additionalProperties": False,
        },
    ],
}


def extent_schema(valid_types: list[str]) -> dict[str, Any]:
    variants: list[dict[str, Any]] = []
    if "angle" in valid_types:
        variants.append({
            "type": "object",
            "properties": {
                "type": {"const": "angle"},
                "angle_degrees": {"type": "number", "exclusiveMinimum": 0, "maximum": 360},
            },
            "required": ["type", "angle_degrees"],
            "additionalProperties": False,
        })
    if "two_angles" in valid_types:
        variants.append({
            "type": "object",
            "properties": {
                "type": {"const": "two_angles"},
                "angle_degrees": {"type": "number", "exclusiveMinimum": 0, "maximum": 360},
                "second_angle_degrees": {"type": "number", "exclusiveMinimum": 0, "maximum": 360},
            },
            "required": ["type", "angle_degrees", "second_angle_degrees"],
            "additionalProperties": False,
        })
    for extent_type in ("through_all", "up_to_last", "up_to_first"):
        if extent_type in valid_types:
            variants.append({
                "type": "object",
                "properties": {"type": {"const": extent_type}},
                "required": ["type"],
                "additionalProperties": False,
            })
    if "up_to_face" in valid_types:
        variants.append({
            "type": "object",
            "properties": {
                "type": {"const": "up_to_face"},
                "target_object": {"type": "string", "minLength": 1},
                "target_subelement": {"type": "string", "pattern": "^Face[1-9][0-9]*$"},
            },
            "required": ["type", "target_object", "target_subelement"],
            "additionalProperties": False,
        })
    return {
        "description": "How far the rotation extends and what terminates it.",
        "oneOf": variants,
    }


def run(
    service: Any,
    *,
    operation: str,
    type_id: str,
    profile_name: str,
    label: str,
    axis: dict[str, Any],
    extent: dict[str, Any],
    midplane: bool,
    reversed: bool,
) -> dict[str, Any]:
    clean_label = str(label or "").strip()
    if not clean_label:
        return _invalid("label is required.")
    profile = service._get_sketch(str(profile_name or ""))
    if profile is None:
        return _invalid(
            f"Profile sketch not found by exact internal name: {profile_name}"
        )
    body = service._partdesign_body_for_feature(profile)
    if body is None:
        return _invalid(
            f"Sketch {profile.Name} is not owned by exactly one PartDesign Body."
        )
    tip_block = domain_runtime.invalid_partdesign_tip(body)
    if tip_block is not None:
        return {
            "ok": False,
            "error": "The profile Body has an invalid or zero-effect Tip.",
            "body": body.Name,
            "tip_state": tip_block,
            "retry_same_call": False,
        }
    profile_status = service._sketch_profile_status(profile)
    if not profile_status.get("ready_for_closed_profile_feature"):
        return {
            "ok": False,
            "error": f"Sketch {profile.Name} is not a closed face-buildable profile.",
            "profile_status": profile_status,
            "retry_same_call": False,
        }
    axis_state = _resolve_axis(service, body, profile, axis)
    if not axis_state.get("ok"):
        return axis_state
    extent_state = _validate_extent(service, operation, extent)
    if not extent_state.get("ok"):
        return extent_state
    body_shape_before = domain_runtime.shape_summary(body)
    if operation == "groove" and int(body_shape_before.get("solids", 0) or 0) == 0:
        return _invalid(
            f"Body {body.Name} has no solid for a Groove to remove material from.",
            body_shape=body_shape_before,
        )

    def create_feature() -> dict[str, Any]:
        import FreeCAD as App

        doc = App.ActiveDocument
        if doc is None:
            raise RuntimeError("No active document.")
        target_profile = service._get_sketch(profile.Name)
        if target_profile is None:
            raise RuntimeError(f"Profile sketch no longer exists: {profile.Name}")
        target_body = service._partdesign_body_for_feature(target_profile)
        if target_body is None or target_body.Name != body.Name:
            raise RuntimeError(f"Profile ownership changed for {profile.Name}.")
        axis_object = doc.getObject(axis_state["object_name"])
        if axis_object is None:
            raise RuntimeError(f"Axis object no longer exists: {axis_state['object_name']}")

        native_name = "Revolution" if operation == "revolution" else "Groove"
        feature = target_body.newObject(type_id, native_name)
        feature.Label = clean_label
        feature.Profile = target_profile
        feature.ReferenceAxis = (axis_object, [axis_state["subelement"]])
        feature.Type = extent_state["type"]
        if "angle_degrees" in extent_state:
            feature.Angle = float(extent_state["angle_degrees"])
        if "second_angle_degrees" in extent_state:
            feature.Angle2 = float(extent_state["second_angle_degrees"])
        if extent_state.get("target") is not None:
            feature.UpToFace = (
                extent_state["target"],
                [extent_state["target_subelement"]],
            )
        feature.Midplane = bool(midplane)
        feature.Reversed = bool(reversed)
        target_body.Tip = feature
        doc.recompute()
        effect = domain_runtime.finalize_partdesign_feature_effect(
            doc,
            target_body,
            feature,
            operation,
            body_shape_before,
        )
        return {
            "document": doc.Name,
            "body": target_body.Name,
            "profile": target_profile.Name,
            "feature": feature.Name,
            "feature_label": feature.Label,
            "feature_type": feature.TypeId,
            "axis_object": axis_object.Name,
            "axis_subelement": axis_state["subelement"],
            "termination": str(feature.Type),
            "angle_degrees": float(feature.Angle),
            "second_angle_degrees": float(feature.Angle2),
            "midplane": bool(feature.Midplane),
            "reversed": bool(feature.Reversed),
            "body_group": [item.Name for item in list(target_body.Group)],
            "body_tip": getattr(getattr(target_body, "Tip", None), "Name", None),
            "base_feature": getattr(getattr(feature, "BaseFeature", None), "Name", None),
            **effect,
        }

    transaction = run_freecad_transaction(
        f"Create PartDesign {operation}: {clean_label}",
        create_feature,
    )
    return domain_runtime.partdesign_feature_response(
        service,
        transaction,
        operation=operation,
        profile_status=profile_status,
    )


def _resolve_axis(
    service: Any,
    body: Any,
    profile: Any,
    axis: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(axis, dict):
        return _invalid("axis must be an object.")
    source = str(axis.get("source") or "").strip()
    axis_name = str(axis.get("axis") or "").strip()
    if source == "body_origin":
        if axis_name not in {"X_Axis", "Y_Axis", "Z_Axis"}:
            return _invalid(
                "body_origin axis requires axis X_Axis, Y_Axis, or Z_Axis."
            )
        origin_axis = service._partdesign_origin_feature(body, axis_name)
        if origin_axis is None:
            return _invalid(f"Body origin axis not found: {axis_name}")
        return {
            "ok": True,
            "object_name": origin_axis.Name,
            "subelement": "",
        }
    if source == "profile_axis":
        if axis_name not in {"H_Axis", "V_Axis"}:
            return _invalid("profile_axis requires axis H_Axis or V_Axis.")
        return {
            "ok": True,
            "object_name": profile.Name,
            "subelement": axis_name,
        }
    if source == "object_edge":
        object_name = str(axis.get("object_name") or "").strip()
        subelement = str(axis.get("subelement") or "").strip()
        if not object_name or not subelement.startswith("Edge"):
            return _invalid(
                "object_edge requires exact object_name and edge subelement such as Edge4."
            )
        doc = service._active_document()
        target = doc.getObject(object_name) if doc is not None else None
        if target is None:
            return _invalid(f"Axis object not found: {object_name}")
        try:
            edge = target.Shape.getElement(subelement)
        except Exception as exc:
            return _invalid(
                f"Axis edge {subelement} does not exist on {object_name}.",
                native_error=str(exc),
            )
        curve = getattr(edge, "Curve", None)
        curve_type = type(curve).__name__ if curve is not None else None
        if curve_type not in {"Line", "LineSegment"}:
            return _invalid(
                "object_edge rotation axes must resolve to one straight line edge.",
                axis_object=target.Name,
                axis_subelement=subelement,
                axis_geometry_type=curve_type,
            )
        return {
            "ok": True,
            "object_name": target.Name,
            "subelement": subelement,
            "geometry_type": curve_type,
            "length": float(getattr(edge, "Length", 0.0) or 0.0),
        }
    return _invalid("axis.source must be body_origin, profile_axis, or object_edge.")


def _validate_extent(
    service: Any,
    operation: str,
    extent: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(extent, dict):
        return _invalid("extent must be an object.")
    requested = str(extent.get("type") or "").strip()
    values = (
        {
            "angle": "Angle",
            "up_to_last": "UpToLast",
            "up_to_first": "UpToFirst",
            "up_to_face": "UpToFace",
            "two_angles": "TwoAngles",
        }
        if operation == "revolution"
        else {
            "angle": "Angle",
            "through_all": "ThroughAll",
            "up_to_first": "UpToFirst",
            "up_to_face": "UpToFace",
            "two_angles": "TwoAngles",
        }
    )
    if requested not in values:
        return _invalid(
            f"extent.type '{requested}' is not valid for {operation}.",
            valid_extent_types=sorted(values),
        )
    result: dict[str, Any] = {"ok": True, "type": values[requested]}
    if requested in {"angle", "two_angles"}:
        angle = extent.get("angle_degrees")
        if angle is None or not (0 < float(angle) <= 360):
            return _invalid("extent.angle_degrees must be greater than 0 and at most 360.")
        result["angle_degrees"] = float(angle)
    if requested == "two_angles":
        second = extent.get("second_angle_degrees")
        if second is None or not (0 < float(second) <= 360):
            return _invalid(
                "extent.second_angle_degrees must be greater than 0 and at most 360."
            )
        result["second_angle_degrees"] = float(second)
    if requested == "up_to_face":
        object_name = str(extent.get("target_object") or "").strip()
        subelement = str(extent.get("target_subelement") or "").strip()
        doc = service._active_document()
        target = doc.getObject(object_name) if doc is not None else None
        if target is None:
            return _invalid(f"Extent target not found: {object_name}")
        if not subelement.startswith("Face"):
            return _invalid("up_to_face requires target_subelement such as Face3.")
        try:
            target.Shape.getElement(subelement)
        except Exception:
            return _invalid(f"Target face {subelement} does not exist on {object_name}.")
        result["target"] = target
        result["target_subelement"] = subelement
    return result


def _invalid(message: str, **details: Any) -> dict[str, Any]:
    return {
        "ok": False,
        "error": message,
        "retry_same_call": False,
        **details,
    }
