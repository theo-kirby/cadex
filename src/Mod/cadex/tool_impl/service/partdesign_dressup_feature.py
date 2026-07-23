# SPDX-License-Identifier: LGPL-2.1-or-later

"""Shared native PartDesign dress-up execution and geometric selection."""

from __future__ import annotations

from typing import Any

from CadexTransactions import run_freecad_transaction

from . import (
    domain_runtime,
    partdesign_find_subelements,
    partdesign_transform_feature,
)


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

_QUERY_PROPERTIES = {
    "geometry_type": {
        "type": "string",
        "enum": [
            "plane", "cylinder", "cone", "sphere", "torus", "bspline",
            "line", "circle", "ellipse",
        ],
        "description": "Match only subelements of this surface or curve type.",
    },
    "normal": {**VECTOR_SCHEMA, "description": "Match faces whose normal points this way."},
    "normal_tolerance_degrees": {
        "type": "number",
        "minimum": 0,
        "maximum": 180,
        "description": "Allowed deviation from normal.",
    },
    "direction": {**VECTOR_SCHEMA, "description": "Match edges aligned with this direction."},
    "direction_tolerance_degrees": {
        "type": "number",
        "minimum": 0,
        "maximum": 180,
        "description": "Allowed deviation from direction.",
    },
    "radius": {
        "type": "number",
        "exclusiveMinimum": 0,
        "description": "Match circular or cylindrical subelements of this radius in mm.",
    },
    "radius_tolerance": {
        "type": "number",
        "minimum": 0,
        "description": "Allowed radius deviation in mm.",
    },
    "min_area": {"type": "number", "minimum": 0, "description": "Minimum face area in mm^2."},
    "max_area": {"type": "number", "minimum": 0, "description": "Maximum face area in mm^2."},
    "min_length": {"type": "number", "minimum": 0, "description": "Minimum edge length in mm."},
    "max_length": {"type": "number", "minimum": 0, "description": "Maximum edge length in mm."},
    "near_point": {**VECTOR_SCHEMA, "description": "Match subelements near this point."},
    "max_distance": {
        "type": "number",
        "minimum": 0,
        "description": "Maximum distance in mm from near_point.",
    },
}


def selection_schema(
    *,
    allow_all_edges: bool,
    face_only: bool = False,
    edge_only: bool = False,
    required_count: int | None = None,
) -> dict[str, Any]:
    if face_only and edge_only:
        raise ValueError("A selection cannot be both face_only and edge_only.")
    name_pattern = (
        "^Face[1-9][0-9]*$"
        if face_only
        else "^Edge[1-9][0-9]*$"
        if edge_only
        else "^(Edge|Face)[1-9][0-9]*$"
    )
    kind_description = "Kind of subelement to match."
    element_type_schema = (
        {"const": "face", "description": kind_description}
        if face_only
        else {"const": "edge", "description": kind_description}
        if edge_only
        else {
            "type": "string",
            "enum": ["edge", "face"],
            "description": kind_description,
        }
    )
    exact_items = {
        "type": "array",
        "items": {"type": "string", "pattern": name_pattern},
        "minItems": required_count if required_count is not None else 1,
        "description": (
            "Exact subelement names on the base feature. This is a topology-fragile "
            "escape hatch; prefer a geometric query whenever predicates can identify "
            "the intended geometry."
        ),
    }
    if required_count is not None:
        exact_items["maxItems"] = required_count
    expected_count_schema = {
        "type": "integer",
        "description": (
            "Exact number of matches required; a different count fails before mutation."
        ),
    }
    if required_count is None:
        expected_count_schema["minimum"] = 1
    else:
        expected_count_schema["const"] = required_count
    choices: list[dict[str, Any]] = [
        {
            "type": "object",
            "properties": {
                "type": {
                    "const": "exact",
                    "description": (
                        "Select by exact FaceN/EdgeN names only when a geometric query "
                        "cannot uniquely discriminate the target."
                    ),
                },
                "subelements": exact_items,
            },
            "required": ["type", "subelements"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {
                    "const": "query",
                    "description": (
                        "Preferred: select by measurable geometric predicates and require "
                        "the exact expected match count."
                    ),
                },
                "element_type": element_type_schema,
                "expected_count": expected_count_schema,
                **_QUERY_PROPERTIES,
            },
            "required": ["type", "element_type", "expected_count"],
            "additionalProperties": False,
        },
    ]
    if allow_all_edges:
        choices.insert(
            0,
            {
                "type": "object",
                "properties": {
                    "type": {
                        "const": "all_edges",
                        "description": "Select every edge of the base feature.",
                    }
                },
                "required": ["type"],
                "additionalProperties": False,
            },
        )
    return {
        "oneOf": choices,
        "description": (
            "Which subelements to address. Prefer a geometric query with expected_count; "
            "use exact topology names only when predicates cannot distinguish the target."
        ),
    }


DRAFT_PULL_DIRECTION_SCHEMA = {
    "description": "Direction the mold pulls away from the part.",
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "source": {"const": "body_origin", "description": "Pull along a Body origin axis."},
                "axis": {
                    "type": "string",
                    "enum": ["X_Axis", "Y_Axis", "Z_Axis"],
                    "description": "Body origin axis.",
                },
            },
            "required": ["source", "axis"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "source": {"const": "datum_axis", "description": "Pull along a PartDesign datum axis."},
                "object_name": {
                    "type": "string",
                    "description": "Exact internal name of the datum axis.",
                },
            },
            "required": ["source", "object_name"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "source": {"const": "linear_edge", "description": "Pull along a straight model edge."},
                "object_name": {
                    "type": "string",
                    "description": "Exact internal name of the object that owns the edge.",
                },
                "subelement": {
                    "type": "string",
                    "pattern": "^Edge[1-9][0-9]*$",
                    "description": "Exact edge name such as Edge4; must be linear.",
                },
            },
            "required": ["source", "object_name", "subelement"],
            "additionalProperties": False,
        },
    ]
}


def run(
    service: Any,
    *,
    operation: str,
    type_id: str,
    base_feature_name: str,
    label: str,
    selection: dict[str, Any],
    refine: bool,
    support_transform: bool,
    definition: dict[str, Any] | None = None,
    neutral_plane: dict[str, Any] | None = None,
    pull_direction: dict[str, Any] | None = None,
    angle_degrees: float | None = None,
    reversed: bool = False,
    wall_thickness: float | None = None,
    direction: str | None = None,
    mode: str | None = None,
    join: str | None = None,
    intersection_handling: bool = False,
) -> dict[str, Any]:
    base_state = _resolve_base(service, base_feature_name)
    if not base_state.get("ok"):
        return base_state
    base = base_state["feature"]
    body = base_state["body"]
    clean_label = str(label or "").strip()
    if not clean_label:
        return _invalid("label is required.")
    selection_state = resolve_selection(
        service,
        base,
        selection,
        allow_all_edges=operation in {"fillet", "chamfer"},
        face_only=operation in {"draft", "thickness"},
    )
    if not selection_state.get("ok"):
        return selection_state
    config = _validate_operation(
        service,
        body,
        operation=operation,
        definition=definition,
        neutral_plane=neutral_plane,
        pull_direction=pull_direction,
        angle_degrees=angle_degrees,
        reversed=reversed,
        wall_thickness=wall_thickness,
        direction=direction,
        mode=mode,
        join=join,
        intersection_handling=intersection_handling,
    )
    if not config.get("ok"):
        return config
    body_shape_before = domain_runtime.shape_summary(body)

    def create() -> dict[str, Any]:
        import FreeCAD as App

        doc = App.ActiveDocument
        if doc is None:
            raise RuntimeError("No active document.")
        target = doc.getObject(base.Name)
        target_body = service._get_partdesign_body(body.Name)
        if target is None or target_body is None:
            raise RuntimeError("Dress-up base feature or Body no longer exists.")
        if service._partdesign_body_for_feature(target) != target_body:
            raise RuntimeError("Dress-up base ownership changed before execution.")
        if getattr(getattr(target_body, "Tip", None), "Name", None) != target.Name:
            raise RuntimeError("Dress-up base is no longer the Body Tip.")
        native_name = {
            "fillet": "Fillet",
            "chamfer": "Chamfer",
            "draft": "Draft",
            "thickness": "Thickness",
        }[operation]
        feature = target_body.newObject(type_id, native_name)
        feature.Label = clean_label
        feature.Base = (target, list(selection_state["subelements"]))
        feature.Refine = bool(refine)
        feature.SupportTransform = bool(support_transform)
        if operation in {"fillet", "chamfer"}:
            feature.UseAllEdges = bool(selection_state["use_all_edges"])
        if operation == "fillet":
            feature.Radius = config["radius"]
        elif operation == "chamfer":
            feature.ChamferType = config["chamfer_type"]
            feature.Size = config["size"]
            if config.get("size2") is not None:
                feature.Size2 = config["size2"]
            if config.get("angle_degrees") is not None:
                feature.Angle = config["angle_degrees"]
            feature.FlipDirection = config["flip_direction"]
        elif operation == "draft":
            neutral_object = doc.getObject(config["neutral_plane"]["object_name"])
            pull_object = doc.getObject(config["pull_direction"]["object_name"])
            if neutral_object is None or pull_object is None:
                raise RuntimeError("Draft neutral plane or pull direction no longer exists.")
            feature.NeutralPlane = (
                neutral_object,
                [config["neutral_plane"]["subelement"]],
            )
            feature.PullDirection = (
                pull_object,
                [config["pull_direction"]["subelement"]],
            )
            feature.Angle = config["angle_degrees"]
            feature.Reversed = config["reversed"]
        else:
            feature.Value = config["wall_thickness"]
            feature.Reversed = config["direction"] == "inward"
            feature.Mode = config["mode"]
            feature.Join = config["join"]
            feature.Intersection = config["intersection_handling"]
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
            "feature": feature.Name,
            "feature_label": feature.Label,
            "feature_type": feature.TypeId,
            "base_feature": target.Name,
            "source_shape": domain_runtime.shape_health(target),
            "selection": {
                "mode": selection_state["mode"],
                "subelements": list(selection_state["subelements"]),
                "resolved_geometry": selection_state["resolved_geometry"],
                "use_all_edges": selection_state["use_all_edges"],
            },
            "parameters": _feature_parameters(feature, operation),
            "body_group": [item.Name for item in list(target_body.Group)],
            "body_tip": getattr(getattr(target_body, "Tip", None), "Name", None),
            "native_base_feature": getattr(getattr(feature, "BaseFeature", None), "Name", None),
            **effect,
        }

    transaction = run_freecad_transaction(
        f"Create PartDesign {operation}: {clean_label}",
        create,
    )
    response = domain_runtime.partdesign_feature_response(
        service,
        transaction,
        operation=operation,
    )
    response["requested_selection"] = selection_state.get("request")
    response["resolved_selection"] = {
        "subelements": selection_state.get("subelements"),
        "geometry": selection_state.get("resolved_geometry"),
    }
    response["requested_parameters"] = config
    response["source_shape"] = domain_runtime.shape_health(base)
    return response


def _resolve_base(service: Any, name: str) -> dict[str, Any]:
    doc = service._active_document()
    feature = doc.getObject(str(name or "").strip()) if doc is not None else None
    if feature is None:
        return _invalid(f"PartDesign base feature not found by exact internal name: {name}")
    body = service._partdesign_body_for_feature(feature)
    if body is None:
        return _invalid(f"Base feature {feature.Name} is not owned by exactly one Body.")
    if not str(getattr(feature, "TypeId", "")).startswith("PartDesign::"):
        return _invalid(f"Base object {feature.Name} is not a PartDesign feature.")
    state = domain_runtime.feature_state_summary(feature)
    shape = domain_runtime.shape_summary(feature)
    if (
        state.get("inspection_complete") is not True
        or state.get("marked_invalid")
        or state.get("shape_null")
        or state.get("shape_valid") is not True
        or shape.get("inspection_complete") is not True
        or int(shape.get("solids", 0) or 0) != 1
    ):
        return _invalid(
            f"Base feature {feature.Name} is not one valid solid.",
            feature_state=state,
            shape=shape,
        )
    tip_name = getattr(getattr(body, "Tip", None), "Name", None)
    if tip_name != feature.Name:
        return _invalid(
            "Dress-up base must be the current Body Tip. Set the intended insertion Tip first.",
            base_feature=feature.Name,
            body=body.Name,
            current_tip=tip_name,
        )
    return {"ok": True, "feature": feature, "body": body}


def resolve_selection(
    service: Any,
    base: Any,
    selection: Any,
    *,
    allow_all_edges: bool,
    face_only: bool,
    edge_only: bool = False,
) -> dict[str, Any]:
    if not isinstance(selection, dict):
        return _invalid("selection must be an object.")
    mode = str(selection.get("type") or "")
    if mode == "all_edges":
        if not allow_all_edges:
            return _invalid("all_edges is not valid for this operation.")
        all_edges = partdesign_find_subelements.run(
            service,
            object_name=base.Name,
            element_type="edge",
        )
        if not all_edges.get("ok"):
            return _invalid(all_edges.get("error") or "Could not inspect base edges.")
        if int(all_edges.get("match_count", 0)) == 0:
            return _invalid(f"Base feature {base.Name} has no edges.")
        return {
            "ok": True,
            "mode": mode,
            "subelements": [],
            "resolved_geometry": all_edges["matches"],
            "use_all_edges": True,
            "request": dict(selection),
        }
    if mode == "exact":
        names = selection.get("subelements")
        if not isinstance(names, list) or not names:
            return _invalid("selection.subelements must contain at least one name.")
        names = [str(value or "").strip() for value in names]
        if len(set(names)) != len(names):
            return _invalid("selection.subelements cannot contain duplicates.")
        if face_only and any(not name.startswith("Face") for name in names):
            return _invalid("This operation requires face subelements.")
        if edge_only and any(not name.startswith("Edge") for name in names):
            return _invalid("This operation requires edge subelements.")
        summaries = _exact_summaries(service, base, names)
        if not summaries.get("ok"):
            return summaries
        return {
            "ok": True,
            "mode": mode,
            "subelements": names,
            "resolved_geometry": summaries["matches"],
            "use_all_edges": False,
            "request": dict(selection),
        }
    if mode == "query":
        kind = str(selection.get("element_type") or "")
        if (
            kind not in {"edge", "face"}
            or face_only and kind != "face"
            or edge_only and kind != "edge"
        ):
            return _invalid("selection.element_type is not valid for this operation.")
        expected = selection.get("expected_count")
        if not isinstance(expected, int) or isinstance(expected, bool) or expected < 1:
            return _invalid("selection.expected_count must be an integer of at least 1.")
        filters = {
            key: value
            for key, value in selection.items()
            if key not in {"type", "element_type", "expected_count"}
        }
        result = partdesign_find_subelements.run(
            service,
            object_name=base.Name,
            element_type=kind,
            **filters,
        )
        if not result.get("ok"):
            return _invalid(result.get("error") or "Geometric selection query failed.")
        actual = int(result.get("match_count", 0))
        if actual != expected:
            return _invalid(
                "Geometric selection did not return the required number of subelements; no feature was created.",
                expected_count=expected,
                actual_count=actual,
                matches=result.get("matches") or [],
                filters=result.get("filters") or {},
            )
        return {
            "ok": True,
            "mode": mode,
            "subelements": [item["name"] for item in result["matches"]],
            "resolved_geometry": result["matches"],
            "use_all_edges": False,
            "request": dict(selection),
        }
    return _invalid("selection.type must be exact, query, or all_edges where supported.")


def _exact_summaries(service: Any, base: Any, names: list[str]) -> dict[str, Any]:
    by_name = {}
    for kind in {"face" if name.startswith("Face") else "edge" for name in names}:
        result = partdesign_find_subelements.run(
            service,
            object_name=base.Name,
            element_type=kind,
        )
        if not result.get("ok"):
            return _invalid(result.get("error") or f"Could not inspect {kind} geometry.")
        by_name.update({item["name"]: item for item in result["matches"]})
    missing = [name for name in names if name not in by_name]
    if missing:
        return _invalid(
            f"Subelements do not exist on {base.Name}: {', '.join(missing)}",
            available_subelements=sorted(by_name),
        )
    return {"ok": True, "matches": [by_name[name] for name in names]}


def _validate_operation(
    service: Any,
    body: Any,
    *,
    operation: str,
    definition: Any,
    neutral_plane: Any,
    pull_direction: Any,
    angle_degrees: Any,
    reversed: bool,
    wall_thickness: Any,
    direction: Any,
    mode: Any,
    join: Any,
    intersection_handling: bool,
) -> dict[str, Any]:
    if operation == "fillet":
        radius = _positive((definition or {}).get("radius"), "definition.radius")
        return {"ok": True, "radius": radius["value"]} if radius.get("ok") else radius
    if operation == "chamfer":
        return _validate_chamfer(definition)
    if operation == "draft":
        neutral = partdesign_transform_feature._resolve_plane(service, body, neutral_plane)
        if not neutral.get("ok"):
            return neutral
        pull = partdesign_transform_feature._resolve_axis(service, body, pull_direction)
        if not pull.get("ok"):
            return pull
        if str((pull_direction or {}).get("source") or "") == "sketch_axis":
            return _invalid("Draft pull_direction cannot use a sketch axis.")
        try:
            angle = float(angle_degrees)
        except (TypeError, ValueError):
            return _invalid("angle_degrees must be numeric.")
        if not 0.0 < angle < 90.0:
            return _invalid("angle_degrees must be greater than 0 and less than 90.")
        return {
            "ok": True,
            "neutral_plane": neutral,
            "pull_direction": pull,
            "angle_degrees": angle,
            "reversed": bool(reversed),
        }
    if operation == "thickness":
        value = _positive(wall_thickness, "wall_thickness")
        if not value.get("ok"):
            return value
        if direction not in {"inward", "outward"}:
            return _invalid("direction must be inward or outward.")
        native_mode = {"skin": "Skin", "pipe": "Pipe", "recto_verso": "RectoVerso"}.get(mode)
        native_join = {"arc": "Arc", "intersection": "Intersection"}.get(join)
        if native_mode is None:
            return _invalid("mode must be skin, pipe, or recto_verso.")
        if native_join is None:
            return _invalid("join must be arc or intersection.")
        return {
            "ok": True,
            "wall_thickness": value["value"],
            "direction": direction,
            "mode": native_mode,
            "join": native_join,
            "intersection_handling": bool(intersection_handling),
        }
    return _invalid(f"Unsupported dress-up operation: {operation}")


def _validate_chamfer(definition: Any) -> dict[str, Any]:
    if not isinstance(definition, dict):
        return _invalid("definition must be an object.")
    kind = str(definition.get("type") or "")
    size = _positive(definition.get("size"), "definition.size")
    if not size.get("ok"):
        return size
    result = {
        "ok": True,
        "size": size["value"],
        "size2": None,
        "angle_degrees": None,
        "flip_direction": bool(definition.get("flip_direction", False)),
    }
    if kind == "equal_distance":
        result["chamfer_type"] = "Equal distance"
        return result
    if kind == "two_distances":
        size2 = _positive(definition.get("second_size"), "definition.second_size")
        if not size2.get("ok"):
            return size2
        result["chamfer_type"] = "Two distances"
        result["size2"] = size2["value"]
        return result
    if kind == "distance_angle":
        try:
            angle = float(definition.get("angle_degrees"))
        except (TypeError, ValueError):
            return _invalid("definition.angle_degrees must be numeric.")
        if not 0.0 < angle < 180.0:
            return _invalid("definition.angle_degrees must be between 0 and 180.")
        result["chamfer_type"] = "Distance and Angle"
        result["angle_degrees"] = angle
        return result
    return _invalid(
        "definition.type must be equal_distance, two_distances, or distance_angle."
    )


def _feature_parameters(feature: Any, operation: str) -> dict[str, Any]:
    common = {
        "refine": bool(feature.Refine),
        "support_transform": bool(feature.SupportTransform),
    }
    if operation == "fillet":
        return {**common, "radius": float(feature.Radius), "use_all_edges": bool(feature.UseAllEdges)}
    if operation == "chamfer":
        return {
            **common,
            "type": str(feature.ChamferType),
            "size": float(feature.Size),
            "second_size": float(feature.Size2),
            "angle_degrees": float(feature.Angle),
            "flip_direction": bool(feature.FlipDirection),
            "use_all_edges": bool(feature.UseAllEdges),
        }
    if operation == "draft":
        return {
            **common,
            "angle_degrees": float(feature.Angle),
            "reversed": bool(feature.Reversed),
            "neutral_plane": _link_sub_summary(feature.NeutralPlane),
            "pull_direction": _link_sub_summary(feature.PullDirection),
        }
    return {
        **common,
        "wall_thickness": float(feature.Value),
        "direction": "inward" if bool(feature.Reversed) else "outward",
        "mode": str(feature.Mode),
        "join": str(feature.Join),
        "intersection_handling": bool(feature.Intersection),
    }


def _link_sub_summary(value: Any) -> dict[str, Any]:
    try:
        obj, subelements = value
    except (TypeError, ValueError) as exc:
        raise TypeError(
            f"FreeCAD returned an invalid LinkSub value: {value!r}."
        ) from exc
    return {
        "object": getattr(obj, "Name", None),
        "subelements": [str(item) for item in list(subelements or [])],
    }


def _positive(value: Any, name: str) -> dict[str, Any]:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return _invalid(f"{name} must be a positive number.")
    if parsed <= 0:
        return _invalid(f"{name} must be a positive number.")
    return {"ok": True, "value": parsed}


def _invalid(message: str, **details: Any) -> dict[str, Any]:
    return {"ok": False, "error": message, "retry_same_call": False, **details}
