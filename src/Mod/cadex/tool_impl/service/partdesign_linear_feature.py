# SPDX-License-Identifier: LGPL-2.1-or-later

"""Native Pad/Pocket implementation shared by their focused tool contracts."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from CadexTransactions import run_freecad_transaction

from . import domain_runtime


VECTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "x": {"type": "number", "description": "X component"},
        "y": {"type": "number", "description": "Y component"},
        "z": {"type": "number", "description": "Z component"},
    },
    "required": ["x", "y", "z"],
    "additionalProperties": False,
}

def extent_schema(valid_types: list[str]) -> dict[str, Any]:
    common_offsets = {
        "offset": {
            "type": "number",
            "description": "Signed offset in mm from the termination; 0 for none.",
        },
        "second_offset": {
            "type": "number",
            "description": "Signed second-side offset in mm; valid only for two-sided length.",
        },
    }
    variants: list[dict[str, Any]] = []
    if "length" in valid_types:
        variants.append(
            {
                "type": "object",
                "properties": {
                    "type": {"const": "length"},
                    "length": {"type": "number", "exclusiveMinimum": 0},
                    "second_length": {"type": "number", "exclusiveMinimum": 0},
                    **deepcopy(common_offsets),
                },
                "required": ["type", "length"],
                "additionalProperties": False,
            }
        )
    for extent_type in ("through_all", "up_to_last", "up_to_first"):
        if extent_type not in valid_types:
            continue
        variants.append(
            {
                "type": "object",
                "properties": {
                    "type": {"const": extent_type},
                    "offset": deepcopy(common_offsets["offset"]),
                },
                "required": ["type"],
                "additionalProperties": False,
            }
        )
    if "up_to_face" in valid_types:
        variants.append(
            {
                "type": "object",
                "properties": {
                    "type": {"const": "up_to_face"},
                    "target_object": {"type": "string", "minLength": 1},
                    "target_subelement": {
                        "type": "string",
                        "pattern": "^Face[1-9][0-9]*$",
                    },
                    "offset": deepcopy(common_offsets["offset"]),
                },
                "required": ["type", "target_object", "target_subelement"],
                "additionalProperties": False,
            }
        )
    if "up_to_shape" in valid_types:
        variants.append(
            {
                "type": "object",
                "properties": {
                    "type": {"const": "up_to_shape"},
                    "target_object": {"type": "string", "minLength": 1},
                    "offset": deepcopy(common_offsets["offset"]),
                },
                "required": ["type", "target_object"],
                "additionalProperties": False,
            }
        )
    return {
        "description": "How far the feature extends and what terminates it.",
        "oneOf": variants,
    }


def run(
    service: Any,
    *,
    operation: str,
    type_id: str,
    profile_name: str,
    label: str,
    extent: dict[str, Any],
    side: str,
    reversed: bool,
    taper_angle_degrees: float,
    second_taper_angle_degrees: float,
    direction: dict[str, float] | None = None,
    refine: bool,
) -> dict[str, Any]:
    clean_label = str(label or "").strip()
    if not clean_label:
        return _invalid("label is required.")
    profile = service._get_sketch(str(profile_name or ""))
    if profile is None:
        return _invalid(
            f"Profile sketch not found by exact internal name: {profile_name}",
            requested_profile=profile_name,
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
            "error": "The profile Body has an invalid Tip; repair or delete it before creating another feature.",
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
    extent_state = _validate_extent(
        service,
        operation,
        extent,
        side,
        body,
    )
    if not extent_state.get("ok"):
        return extent_state
    if not (-89.0 < float(taper_angle_degrees) < 89.0):
        return _invalid("taper_angle_degrees must be greater than -89 and less than 89.")
    if not (-89.0 < float(second_taper_angle_degrees) < 89.0):
        return _invalid(
            "second_taper_angle_degrees must be greater than -89 and less than 89."
        )
    direction_vector = _validate_direction(direction)
    if isinstance(direction_vector, dict) and not direction_vector.get("ok", True):
        return direction_vector

    body_shape_before = domain_runtime.shape_summary(body)
    if operation == "pocket" and int(body_shape_before.get("solids", 0) or 0) == 0:
        return _invalid(
            f"Body {body.Name} has no solid for a Pocket to remove material from.",
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

        feature = target_body.newObject(type_id, "Pad" if operation == "pad" else "Pocket")
        feature.Label = clean_label
        feature.Profile = target_profile
        _apply_extent(feature, extent_state)
        feature.SideType = _SIDE_VALUES[side]
        feature.Reversed = bool(reversed)
        feature.TaperAngle = float(taper_angle_degrees)
        feature.TaperAngle2 = float(second_taper_angle_degrees)
        feature.Refine = bool(refine)
        if direction is not None:
            feature.UseCustomVector = True
            feature.AlongSketchNormal = False
            feature.Direction = App.Vector(
                float(direction["x"]),
                float(direction["y"]),
                float(direction["z"]),
            )
        else:
            feature.UseCustomVector = False
            feature.AlongSketchNormal = True
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
            "termination": str(feature.Type),
            "side": str(feature.SideType),
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


_SIDE_VALUES = {
    "one_side": "One side",
    "two_sides": "Two sides",
    "symmetric": "Symmetric",
}

_PAD_EXTENTS = {
    "length": "Length",
    "up_to_last": "UpToLast",
    "up_to_first": "UpToFirst",
    "up_to_face": "UpToFace",
    "up_to_shape": "UpToShape",
}

_POCKET_EXTENTS = {
    "length": "Length",
    "through_all": "ThroughAll",
    "up_to_first": "UpToFirst",
    "up_to_face": "UpToFace",
    "up_to_shape": "UpToShape",
}


def _validate_extent(
    service: Any,
    operation: str,
    extent: dict[str, Any],
    side: str,
    body: Any,
) -> dict[str, Any]:
    if not isinstance(extent, dict):
        return _invalid("extent must be an object.")
    extent_type = str(extent.get("type") or "").strip()
    valid_extents = _PAD_EXTENTS if operation == "pad" else _POCKET_EXTENTS
    if extent_type not in valid_extents:
        return _invalid(
            f"extent.type '{extent_type}' is not valid for {operation}.",
            valid_extent_types=sorted(valid_extents),
        )
    if side not in _SIDE_VALUES:
        return _invalid("side must be one_side, two_sides, or symmetric.")
    result: dict[str, Any] = {
        "ok": True,
        "type": valid_extents[extent_type],
        "side": side,
        "offset": float(extent.get("offset", 0.0) or 0.0),
        "second_offset": float(extent.get("second_offset", 0.0) or 0.0),
    }
    if extent_type == "length":
        length = extent.get("length")
        if length is None or float(length) <= 0:
            return _invalid("extent.length must be positive for length termination.")
        result["length"] = float(length)
        if side == "two_sides":
            second_length = extent.get("second_length")
            if second_length is None or float(second_length) <= 0:
                return _invalid(
                    "extent.second_length must be positive when side is two_sides."
                )
            result["second_length"] = float(second_length)
        elif "second_length" in extent or "second_offset" in extent:
            return _invalid(
                "extent.second_length and extent.second_offset are valid only when side is two_sides."
            )
    elif side == "two_sides":
        return _invalid("two_sides is supported only with length termination.")

    if extent_type in {"up_to_face", "up_to_shape"}:
        object_name = str(extent.get("target_object") or "").strip()
        if not object_name:
            return _invalid(f"extent.target_object is required for {extent_type}.")
        doc = service._active_document()
        target = doc.getObject(object_name) if doc is not None else None
        if target is None:
            return _invalid(
                f"Extent target not found by exact internal name: {object_name}"
            )
        result["target"] = target
        if extent_type == "up_to_face":
            subelement = str(extent.get("target_subelement") or "").strip()
            if not subelement.startswith("Face"):
                return _invalid(
                    "extent.target_subelement must be an exact face name such as Face3."
                )
            try:
                target.Shape.getElement(subelement)
            except Exception:
                return _invalid(
                    f"Extent target face {subelement} does not exist on {target.Name}."
                )
            result["target_subelement"] = subelement
    return result


def _apply_extent(feature: Any, extent: dict[str, Any]) -> None:
    feature.Type = extent["type"]
    if "length" in extent:
        feature.Length = extent["length"]
    if "second_length" in extent:
        feature.Length2 = extent["second_length"]
    feature.Offset = extent["offset"]
    feature.Offset2 = extent["second_offset"]
    target = extent.get("target")
    if target is not None:
        if extent["type"] == "UpToFace":
            feature.UpToFace = (target, [extent["target_subelement"]])
        elif extent["type"] == "UpToShape":
            feature.UpToShape = target


def _validate_direction(direction: dict[str, float] | None) -> dict[str, Any] | None:
    if direction is None:
        return None
    try:
        x = float(direction["x"])
        y = float(direction["y"])
        z = float(direction["z"])
    except (KeyError, TypeError, ValueError):
        return _invalid("direction requires numeric x, y, and z.")
    if x * x + y * y + z * z <= 1e-18:
        return _invalid("direction must be non-zero.")
    return {"ok": True}


def _invalid(message: str, **details: Any) -> dict[str, Any]:
    return {
        "ok": False,
        "error": message,
        "retry_same_call": False,
        **details,
    }
