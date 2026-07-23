# SPDX-License-Identifier: LGPL-2.1-or-later

"""Native additive/subtractive pipe implementation."""

from __future__ import annotations

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

PARAMETERS = {
    "type": "object",
    "properties": {
        "profile_name": {
            "type": "string",
            "description": "Exact internal name of the closed profile sketch to sweep.",
        },
        "spine_name": {
            "type": "string",
            "description": "Exact internal name of the sweep path (sketch or edged object) in the same Body.",
        },
        "section_names": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Exact internal names of additional closed section sketches; empty for a constant profile.",
        },
        "label": {"type": "string", "description": "Visible label for the new feature."},
        "orientation": {
            "type": "string",
            "enum": ["standard", "fixed", "frenet", "auxiliary", "binormal"],
            "description": "Profile orientation along the spine; auxiliary requires auxiliary_spine_name, binormal requires binormal.",
        },
        "transformation": {
            "type": "string",
            "enum": ["constant", "multisection", "linear", "s_shape", "interpolation"],
            "description": "How the profile changes along the spine; every value except constant requires section_names.",
        },
        "transition": {
            "type": "string",
            "enum": ["transformed", "right_corner", "round_corner"],
            "description": "How the sweep continues across spine corners.",
        },
        "auxiliary_spine_name": {
            "type": "string",
            "description": "Exact internal name of the auxiliary spine; required for auxiliary orientation.",
        },
        "binormal": {
            **VECTOR_SCHEMA,
            "description": "Fixed binormal vector; required for binormal orientation.",
        },
        "spine_tangent": {
            "type": "boolean",
            "description": "Extend the sweep along edges tangent to the spine; usually false.",
        },
        "auxiliary_spine_tangent": {
            "type": "boolean",
            "description": "Extend along edges tangent to the auxiliary spine; usually false.",
        },
        "auxiliary_curvilinear": {
            "type": "boolean",
            "description": "Use curvilinear equivalence between spine and auxiliary spine; usually false.",
        },
        "reversed": {
            "type": "boolean",
            "description": "Sweep in the opposite spine direction; usually false.",
        },
        "midplane": {
            "type": "boolean",
            "description": "Center the sweep on the profile plane; usually false.",
        },
        "refine": {
            "type": "boolean",
            "description": "Remove redundant edges from the result; usually true.",
        },
    },
    "required": [
        "profile_name",
        "spine_name",
        "section_names",
        "label",
        "orientation",
        "transformation",
        "transition",
        "spine_tangent",
        "auxiliary_spine_tangent",
        "auxiliary_curvilinear",
        "reversed",
        "midplane",
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
    spine_name: str,
    section_names: list[str],
    label: str,
    orientation: str,
    transformation: str,
    transition: str,
    spine_tangent: bool,
    auxiliary_spine_tangent: bool,
    auxiliary_curvilinear: bool,
    reversed: bool,
    midplane: bool,
    refine: bool,
    auxiliary_spine_name: str | None = None,
    binormal: dict[str, float] | None = None,
) -> dict[str, Any]:
    clean_label = str(label or "").strip()
    if not clean_label:
        return _invalid("label is required.")
    profile = service._get_sketch(str(profile_name or ""))
    if profile is None:
        return _invalid(f"Pipe profile not found: {profile_name}")
    doc = service._active_document()
    spine = doc.getObject(str(spine_name or "")) if doc is not None else None
    if spine is None:
        return _invalid(f"Pipe spine not found by exact internal name: {spine_name}")
    sections = []
    for name in section_names:
        section = service._get_sketch(str(name or ""))
        if section is None:
            return _invalid(f"Pipe section not found: {name}")
        sections.append(section)
    body = service._partdesign_body_for_feature(profile)
    if body is None:
        return _invalid(f"Profile {profile.Name} has no unambiguous owning Body.")
    ownership = {
        obj.Name: getattr(service._partdesign_body_for_feature(obj), "Name", None)
        for obj in [profile, spine, *sections]
    }
    if any(owner != body.Name for owner in ownership.values()):
        return _invalid(
            "Profile, spine, and all sections must already belong to the same Body.",
            object_ownership=ownership,
        )
    profile_status = service._sketch_profile_status(profile)
    if not profile_status.get("ready_for_closed_profile_feature"):
        return _invalid(
            "Pipe profile must be a closed face-buildable sketch.",
            profile_status=profile_status,
        )
    if getattr(spine, "TypeId", "") == "Sketcher::SketchObject":
        spine_status = service._sketch_profile_status(spine)
        if not spine_status.get("ready_for_path"):
            return _invalid("Pipe spine has no usable path geometry.", spine_status=spine_status)
    else:
        shape = getattr(spine, "Shape", None)
        if shape is None or len(getattr(shape, "Edges", []) or []) == 0:
            return _invalid("Pipe spine object has no edges.")
        spine_status = {"ready_for_path": True, "edge_count": len(shape.Edges)}
    section_states = {
        section.Name: service._sketch_profile_status(section) for section in sections
    }
    if any(not state.get("ready_for_loft_section") for state in section_states.values()):
        return _invalid(
            "Every additional pipe section must be closed and face-buildable.",
            section_states=section_states,
        )
    section_preflight = domain_runtime.ordered_section_preflight(
        service, [profile, *sections]
    )
    if sections and not section_preflight.get("ok"):
        return _invalid(
            "Ordered pipe sections do not have compatible native wire structure or distinct planes.",
            section_preflight=section_preflight,
        )
    path_preflight = domain_runtime.path_preflight(service, profile, spine)
    if not path_preflight.get("ok"):
        return _invalid(
            "Pipe profile and path failed native preflight.",
            path_preflight=path_preflight,
        )
    config = _validate_modes(
        service,
        body,
        orientation,
        transformation,
        transition,
        sections,
        auxiliary_spine_name,
        binormal,
    )
    if not config.get("ok"):
        return config
    tip_block = domain_runtime.invalid_partdesign_tip(body)
    if tip_block is not None:
        return _invalid(
            "The profile Body has an invalid or zero-effect Tip.",
            tip_state=tip_block,
        )
    body_shape_before = domain_runtime.shape_summary(body)
    if operation == "subtractive_pipe" and int(body_shape_before.get("solids", 0) or 0) == 0:
        return _invalid(f"Body {body.Name} has no solid for a subtractive pipe.")

    def create() -> dict[str, Any]:
        import FreeCAD as App

        active_doc = App.ActiveDocument
        if active_doc is None:
            raise RuntimeError("No active document.")
        target_profile = active_doc.getObject(profile.Name)
        target_spine = active_doc.getObject(spine.Name)
        target_sections = [active_doc.getObject(section.Name) for section in sections]
        if target_profile is None or target_spine is None or any(item is None for item in target_sections):
            raise RuntimeError("A pipe input no longer exists.")
        target_body = service._partdesign_body_for_feature(target_profile)
        if target_body is None or target_body.Name != body.Name:
            raise RuntimeError("Pipe input ownership changed before execution.")
        native_name = "AdditivePipe" if operation == "additive_pipe" else "SubtractivePipe"
        pipe = target_body.newObject(type_id, native_name)
        pipe.Label = clean_label
        pipe.Profile = target_profile
        pipe.Spine = target_spine
        pipe.Sections = target_sections
        pipe.Mode = config["orientation"]
        pipe.Transformation = config["transformation"]
        pipe.Transition = config["transition"]
        pipe.SpineTangent = bool(spine_tangent)
        pipe.AuxiliarySpineTangent = bool(auxiliary_spine_tangent)
        pipe.AuxiliaryCurvilinear = bool(auxiliary_curvilinear)
        if config.get("auxiliary_spine") is not None:
            pipe.AuxiliarySpine = config["auxiliary_spine"]
        if config.get("binormal") is not None:
            pipe.Binormal = App.Vector(*config["binormal"])
        pipe.Reversed = bool(reversed)
        pipe.Midplane = bool(midplane)
        pipe.Refine = bool(refine)
        target_body.Tip = pipe
        active_doc.recompute()
        effect = domain_runtime.finalize_partdesign_feature_effect(
            active_doc,
            target_body,
            pipe,
            operation,
            body_shape_before,
        )
        return {
            "document": active_doc.Name,
            "body": target_body.Name,
            "profile": target_profile.Name,
            "spine": target_spine.Name,
            "sections": [item.Name for item in target_sections],
            "path_preflight": path_preflight,
            "section_preflight": section_preflight,
            "feature": pipe.Name,
            "feature_label": pipe.Label,
            "feature_type": pipe.TypeId,
            "orientation": str(pipe.Mode),
            "transformation": str(pipe.Transformation),
            "transition": str(pipe.Transition),
            "body_group": [item.Name for item in list(target_body.Group)],
            "body_tip": getattr(getattr(target_body, "Tip", None), "Name", None),
            "base_feature": getattr(getattr(pipe, "BaseFeature", None), "Name", None),
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
        profile_status={
            "profile": profile_status,
            "spine": spine_status,
            "sections": section_states,
            "path_preflight": path_preflight,
            "section_preflight": section_preflight,
        },
    )


def _validate_modes(
    service: Any,
    body: Any,
    orientation: str,
    transformation: str,
    transition: str,
    sections: list[Any],
    auxiliary_spine_name: str | None,
    binormal: dict[str, float] | None,
) -> dict[str, Any]:
    orientation_values = {
        "standard": "Standard",
        "fixed": "Fixed",
        "frenet": "Frenet",
        "auxiliary": "Auxiliary",
        "binormal": "Binormal",
    }
    transformation_values = {
        "constant": "Constant",
        "multisection": "Multisection",
        "linear": "Linear",
        "s_shape": "S-shape",
        "interpolation": "Interpolation",
    }
    transition_values = {
        "transformed": "Transformed",
        "right_corner": "Right corner",
        "round_corner": "Round corner",
    }
    if orientation not in orientation_values:
        return _invalid("Unknown pipe orientation.")
    if transformation not in transformation_values:
        return _invalid("Unknown pipe transformation.")
    if transition not in transition_values:
        return _invalid("Unknown pipe transition.")
    if transformation != "constant" and not sections:
        return _invalid(
            f"Pipe transformation '{transformation}' requires at least one additional section."
        )
    result: dict[str, Any] = {
        "ok": True,
        "orientation": orientation_values[orientation],
        "transformation": transformation_values[transformation],
        "transition": transition_values[transition],
    }
    if orientation == "auxiliary":
        doc = service._active_document()
        auxiliary = doc.getObject(str(auxiliary_spine_name or "")) if doc is not None else None
        if auxiliary is None:
            return _invalid("auxiliary orientation requires auxiliary_spine_name.")
        if service._partdesign_body_for_feature(auxiliary) is not body:
            return _invalid("Auxiliary spine must belong to the same Body.")
        result["auxiliary_spine"] = auxiliary
    if orientation == "binormal":
        try:
            vector = (
                float(binormal["x"]),
                float(binormal["y"]),
                float(binormal["z"]),
            )
        except (KeyError, TypeError, ValueError):
            return _invalid("binormal orientation requires numeric binormal x, y, and z.")
        if sum(value * value for value in vector) <= 1e-18:
            return _invalid("binormal must be non-zero.")
        result["binormal"] = vector
    return result


def _invalid(message: str, **details: Any) -> dict[str, Any]:
    return {"ok": False, "error": message, "retry_same_call": False, **details}
