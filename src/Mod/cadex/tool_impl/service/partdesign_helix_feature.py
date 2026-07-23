# SPDX-License-Identifier: LGPL-2.1-or-later

"""Native additive/subtractive helix implementation."""

from __future__ import annotations

from typing import Any

from CadexTransactions import run_freecad_transaction

from . import domain_runtime, partdesign_rotational_feature


_DEFINITION_SCHEMA = {
    "description": "Helix shape; choose exactly one definition variant.",
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "type": {
                    "const": "pitch_height_angle",
                    "description": "Define the helix by pitch and total height.",
                },
                "pitch": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "Distance in mm between turns.",
                },
                "height": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "Total helix height in mm.",
                },
                "angle_degrees": {
                    "type": "number",
                    "description": "Cone half-angle between -89 and 89; 0 for a cylindrical helix.",
                },
            },
            "required": ["type", "pitch", "height", "angle_degrees"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {
                    "const": "pitch_turns_angle",
                    "description": "Define the helix by pitch and turn count.",
                },
                "pitch": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "Distance in mm between turns.",
                },
                "turns": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "Number of turns; fractions allowed.",
                },
                "angle_degrees": {
                    "type": "number",
                    "description": "Cone half-angle between -89 and 89; 0 for a cylindrical helix.",
                },
            },
            "required": ["type", "pitch", "turns", "angle_degrees"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {
                    "const": "height_turns_angle",
                    "description": "Define the helix by total height and turn count.",
                },
                "height": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "Total helix height in mm.",
                },
                "turns": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "Number of turns; fractions allowed.",
                },
                "angle_degrees": {
                    "type": "number",
                    "description": "Cone half-angle between -89 and 89; 0 for a cylindrical helix.",
                },
            },
            "required": ["type", "height", "turns", "angle_degrees"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {
                    "const": "height_turns_growth",
                    "description": "Define a spiral by total height, turn count, and radial growth.",
                },
                "height": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "Total height in mm; small values approach a flat spiral.",
                },
                "turns": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "Number of turns; fractions allowed.",
                },
                "growth": {
                    "type": "number",
                    "description": "Radial growth in mm per turn.",
                },
            },
            "required": ["type", "height", "turns", "growth"],
            "additionalProperties": False,
        },
    ]
}

PARAMETERS = {
    "type": "object",
    "properties": {
        "profile_name": {
            "type": "string",
            "description": "Exact internal name of the closed profile sketch to sweep along the helix.",
        },
        "label": {"type": "string", "description": "Visible label for the new feature."},
        "axis": partdesign_rotational_feature.AXIS_SCHEMA,
        "definition": _DEFINITION_SCHEMA,
        "left_handed": {
            "type": "boolean",
            "description": "Wind counterclockwise when viewed along the axis; false for a right-handed helix.",
        },
        "reversed": {
            "type": "boolean",
            "description": "Grow in the opposite axis direction; usually false.",
        },
        "midplane": {
            "type": "boolean",
            "description": "Center the helix on the profile plane; usually false.",
        },
        "outside": {
            "type": "boolean",
            "description": "Keep only material outside the profile; usually false.",
        },
        "tolerance": {
            "type": "number",
            "exclusiveMinimum": 0,
            "description": "Sweep approximation tolerance in mm; 0.001 is typical.",
        },
        "refine": {
            "type": "boolean",
            "description": "Remove redundant edges from the result; usually true.",
        },
    },
    "required": [
        "profile_name",
        "label",
        "axis",
        "definition",
        "left_handed",
        "reversed",
        "midplane",
        "outside",
        "tolerance",
        "refine",
    ],
    "additionalProperties": False,
}


def run(
    service: Any,
    *,
    operation: str,
    type_id: str,
    profile_name: str,
    label: str,
    axis: dict[str, Any],
    definition: dict[str, Any],
    left_handed: bool,
    reversed: bool,
    midplane: bool,
    outside: bool,
    tolerance: float,
    refine: bool,
) -> dict[str, Any]:
    clean_label = str(label or "").strip()
    if not clean_label:
        return _invalid("label is required.")
    profile = service._get_sketch(str(profile_name or ""))
    if profile is None:
        return _invalid(f"Helix profile not found: {profile_name}")
    body = service._partdesign_body_for_feature(profile)
    if body is None:
        return _invalid(f"Profile {profile.Name} has no unambiguous owning Body.")
    profile_status = service._sketch_profile_status(profile)
    if not profile_status.get("ready_for_closed_profile_feature"):
        return _invalid(
            "Helix profile must be a closed face-buildable sketch.",
            profile_status=profile_status,
        )
    axis_state = partdesign_rotational_feature._resolve_axis(
        service,
        body,
        profile,
        axis,
    )
    if not axis_state.get("ok"):
        return axis_state
    definition_state = _validate_definition(definition)
    if not definition_state.get("ok"):
        return definition_state
    if float(tolerance) <= 0:
        return _invalid("tolerance must be positive.")
    tip_block = domain_runtime.invalid_partdesign_tip(body)
    if tip_block is not None:
        return _invalid(
            "The profile Body has an invalid or zero-effect Tip.",
            tip_state=tip_block,
        )
    body_shape_before = domain_runtime.shape_summary(body)
    if operation == "subtractive_helix" and int(body_shape_before.get("solids", 0) or 0) == 0:
        return _invalid(f"Body {body.Name} has no solid for a subtractive helix.")

    def create() -> dict[str, Any]:
        import FreeCAD as App

        doc = App.ActiveDocument
        if doc is None:
            raise RuntimeError("No active document.")
        target_profile = service._get_sketch(profile.Name)
        target_body = service._partdesign_body_for_feature(target_profile)
        axis_object = doc.getObject(axis_state["object_name"])
        if target_profile is None or target_body is None or axis_object is None:
            raise RuntimeError("A helix input no longer exists.")
        if target_body.Name != body.Name:
            raise RuntimeError("Helix profile ownership changed before execution.")
        native_name = "AdditiveHelix" if operation == "additive_helix" else "SubtractiveHelix"
        helix = target_body.newObject(type_id, native_name)
        helix.Label = clean_label
        helix.Profile = target_profile
        helix.ReferenceAxis = (axis_object, [axis_state["subelement"]])
        helix.Mode = definition_state["mode"]
        for property_name in ("Pitch", "Height", "Turns", "Angle", "Growth"):
            key = property_name.lower()
            if key in definition_state:
                setattr(helix, property_name, definition_state[key])
        helix.LeftHanded = bool(left_handed)
        helix.Reversed = bool(reversed)
        helix.Midplane = bool(midplane)
        helix.Outside = bool(outside)
        helix.Tolerance = float(tolerance)
        helix.Refine = bool(refine)
        target_body.Tip = helix
        doc.recompute()
        effect = domain_runtime.finalize_partdesign_feature_effect(
            doc,
            target_body,
            helix,
            operation,
            body_shape_before,
        )
        return {
            "document": doc.Name,
            "body": target_body.Name,
            "profile": target_profile.Name,
            "feature": helix.Name,
            "feature_label": helix.Label,
            "feature_type": helix.TypeId,
            "axis_object": axis_object.Name,
            "axis_subelement": axis_state["subelement"],
            "mode": str(helix.Mode),
            "pitch": float(helix.Pitch),
            "height": float(helix.Height),
            "turns": float(helix.Turns),
            "angle_degrees": float(helix.Angle),
            "growth": float(helix.Growth),
            "body_group": [item.Name for item in list(target_body.Group)],
            "body_tip": getattr(getattr(target_body, "Tip", None), "Name", None),
            "base_feature": getattr(getattr(helix, "BaseFeature", None), "Name", None),
            **effect,
        }

    transaction = run_freecad_transaction(
        f"Create PartDesign {operation}: {clean_label}",
        create,
    )
    return domain_runtime.partdesign_feature_response(
        service,
        transaction,
        operation=operation,
        profile_status=profile_status,
    )


def _validate_definition(definition: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(definition, dict):
        return _invalid("definition must be an object.")
    requested = str(definition.get("type") or "")
    modes = {
        "pitch_height_angle": "pitch-height-angle",
        "pitch_turns_angle": "pitch-turns-angle",
        "height_turns_angle": "height-turns-angle",
        "height_turns_growth": "height-turns-growth",
    }
    if requested not in modes:
        return _invalid("Unknown helix definition type.")
    result: dict[str, Any] = {"ok": True, "mode": modes[requested]}
    required = {
        "pitch_height_angle": ("pitch", "height", "angle_degrees"),
        "pitch_turns_angle": ("pitch", "turns", "angle_degrees"),
        "height_turns_angle": ("height", "turns", "angle_degrees"),
        "height_turns_growth": ("height", "turns", "growth"),
    }[requested]
    for key in required:
        if key not in definition:
            return _invalid(f"definition.{key} is required for {requested}.")
        value = float(definition[key])
        native_key = "angle" if key == "angle_degrees" else key
        if key in {"pitch", "height", "turns"} and value <= 0:
            return _invalid(f"definition.{key} must be positive.")
        if key == "angle_degrees" and not (-89 < value < 89):
            return _invalid("definition.angle_degrees must be between -89 and 89.")
        result[native_key] = value
    return result


def _invalid(message: str, **details: Any) -> dict[str, Any]:
    return {"ok": False, "error": message, "retry_same_call": False, **details}
