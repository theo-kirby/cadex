# SPDX-License-Identifier: LGPL-2.1-or-later

"""Parametric PartDesign thin loft through open planar section curves."""

from __future__ import annotations

import math
from typing import Any

from CadexTransactions import run_freecad_transaction

from . import domain_runtime


_DIRECTIONS = {"forward", "reversed"}
_GEOMETRIC_TOLERANCE = 1e-7


TOOL_SPEC = {
    "name": "partdesign.thin_loft",
    "description": (
        "Create one parametric additive thin loft from two or more ordered open "
        "single-curve sketches in the same PartDesign Body. Each sketch is a camber or "
        "centerline section; the tool offsets it symmetrically by the stated thickness, "
        "rounds both ends, and lofts the resulting closed sections. Use this for twisted "
        "blades, vanes, fins, wings, and other thin curved solids. Section direction is "
        "explicit and never inferred. Author the source curve as construction geometry so "
        "Sketcher does not try to make a face from the intentionally open section. Existing "
        "Body material must overlap the loft so the additive result remains one solid."
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
                "description": "Exact internal name of the owning PartDesign Body.",
            },
            "sections": {
                "type": "array",
                "minItems": 2,
                "items": {
                    "type": "object",
                    "properties": {
                        "sketch_name": {
                            "type": "string",
                            "description": (
                                "Exact internal name of an open sketch containing one curve. "
                                "Construction geometry is preferred and fully supported."
                            ),
                        },
                        "direction": {
                            "type": "string",
                            "enum": ["forward", "reversed"],
                            "description": (
                                "Whether this section follows or reverses the curve's "
                                "authored start-to-end direction. Use one semantic direction "
                                "across every section, such as hub to shroud."
                            ),
                        },
                        "thickness_mm": {
                            "type": "number",
                            "exclusiveMinimum": 0,
                            "description": "Finished section thickness in millimeters.",
                        },
                    },
                    "required": ["sketch_name", "direction", "thickness_mm"],
                    "additionalProperties": False,
                },
                "description": "Ordered thin-loft sections from the first station to the last.",
            },
            "label": {
                "type": "string",
                "description": "Visible label for the new feature.",
            },
            "ruled": {
                "type": "boolean",
                "description": (
                    "Use straight transitions between stations. False creates a smooth loft."
                ),
            },
            "max_degree": {
                "type": "integer",
                "minimum": 1,
                "maximum": 9,
                "description": "Maximum B-spline degree along the loft; 5 is a robust default.",
            },
            "refine": {
                "type": "boolean",
                "description": "Remove redundant splitter edges from the final solid.",
            },
            "fuzzy_tolerance": {
                "type": "number",
                "minimum": 0,
                "description": (
                    "Explicit OpenCascade Boolean tolerance in millimeters. Use 0 for exact "
                    "fusion; use a positive value only for intentional near-coincident healing."
                ),
            },
        },
        "required": [
            "body_name",
            "sections",
            "label",
            "ruled",
            "max_degree",
            "refine",
            "fuzzy_tolerance",
        ],
        "additionalProperties": False,
    },
}


class ThinLoftBuildError(RuntimeError):
    """Structured geometry error shared by preflight and feature recompute."""

    def __init__(self, message: str, *, stage: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.stage = stage
        self.details = details or {}


class ThinLoftProxy:
    """Persistent recompute implementation for PartDesign::FeatureAdditivePython."""

    Type = "CadexThinLoft"

    def attach(self, feature: Any) -> None:
        _ensure_feature_properties(feature)

    def execute(self, feature: Any) -> None:
        import Part

        # A failed recompute must not leave a stale shape looking valid.
        feature.AddSubShape = Part.Shape()
        feature.CadexUnrefinedShape = Part.Shape()
        feature.Shape = Part.Shape()
        body = feature.getParentGeoFeatureGroup()
        if body is None or getattr(body, "TypeId", "") != "PartDesign::Body":
            raise RuntimeError("Thin loft is not owned by a PartDesign Body.")
        sections = list(feature.Sections or [])
        directions = [str(value).lower() for value in list(feature.SectionDirections or [])]
        thicknesses = [float(value) for value in list(feature.SectionThicknesses or [])]
        base_feature = getattr(feature, "BaseFeature", None)
        _base_shape_source = "unresolved"
        try:
            base_shape, _base_shape_source = _valid_base_shape(base_feature)
            if bool(getattr(feature, "Suppressed", False)):
                if base_shape is not None:
                    feature.CadexUnrefinedShape = base_shape
                    feature.Shape = base_shape
                return
            built = _build_geometry(
                sections,
                directions,
                thicknesses,
                ruled=bool(feature.Ruled),
                max_degree=int(feature.MaxDegree),
                refine=bool(feature.Refine),
                fuzzy_tolerance=float(feature.FuzzyTolerance),
                base_shape=base_shape,
            )
        except ThinLoftBuildError as exc:
            raise RuntimeError(
                f"Thin loft {exc.stage} failed: {exc}; "
                f"boolean_base_source={_base_shape_source}; "
                f"fuzzy_tolerance={float(feature.FuzzyTolerance)}; "
                f"diagnostics={exc.details}"
            ) from exc
        feature.AddSubShape = built["loft_shape"]
        feature.CadexUnrefinedShape = built["unrefined_result_shape"]
        feature.Shape = built["result_shape"]

    def onDocumentRestored(self, feature: Any) -> None:
        _ensure_feature_properties(feature)

    def dumps(self) -> dict[str, int]:
        return {"version": 1}

    def loads(self, _state: Any) -> None:
        return None


def run(
    service: Any,
    body_name: str,
    sections: list[dict[str, Any]],
    label: str,
    ruled: bool,
    max_degree: int,
    refine: bool,
    fuzzy_tolerance: float,
) -> dict[str, Any]:
    clean_label = str(label or "").strip()
    if not clean_label:
        return _invalid("label is required.", failure_stage="schema")
    body = service._get_partdesign_body(str(body_name or "").strip())
    if body is None:
        return _invalid(
            f"PartDesign Body not found by exact internal name: {body_name}",
            failure_stage="body_resolution",
            requested_body=body_name,
        )
    definitions = _validate_section_definitions(sections)
    if not definitions.get("ok"):
        return definitions
    try:
        degree = int(max_degree)
    except (TypeError, ValueError):
        return _invalid("max_degree must be an integer from 1 through 9.", failure_stage="schema")
    if degree < 1 or degree > 9:
        return _invalid("max_degree must be from 1 through 9.", failure_stage="schema")
    try:
        tolerance = float(fuzzy_tolerance)
    except (TypeError, ValueError):
        return _invalid(
            "fuzzy_tolerance must be numeric and non-negative.", failure_stage="schema"
        )
    if not math.isfinite(tolerance) or tolerance < 0:
        return _invalid(
            "fuzzy_tolerance must be finite and non-negative.", failure_stage="schema"
        )
    tip_block = domain_runtime.invalid_partdesign_tip(body)
    if tip_block is not None:
        return _invalid(
            "The target Body has an invalid or zero-effect Tip.",
            failure_stage="body_precondition",
            tip_state=tip_block,
        )
    invalid_history = _invalid_body_history(body)
    if invalid_history:
        return _invalid(
            "The target Body contains invalid PartDesign history that must be repaired first.",
            failure_stage="body_precondition",
            invalid_features=invalid_history,
        )
    resolved = _resolve_sections(service, body, definitions["sections"])
    if not resolved.get("ok"):
        return resolved
    base_feature = _last_valid_solid_feature(body)
    try:
        base_shape, base_shape_source = _valid_base_shape(base_feature)
    except ThinLoftBuildError as exc:
        return _invalid(str(exc), failure_stage=exc.stage, **exc.details)
    body_shape_before = domain_runtime.shape_summary(body)
    try:
        prebuilt = _build_geometry(
            resolved["sketches"],
            resolved["directions"],
            resolved["thicknesses"],
            ruled=bool(ruled),
            max_degree=degree,
            refine=bool(refine),
            fuzzy_tolerance=tolerance,
            base_shape=base_shape,
        )
    except ThinLoftBuildError as exc:
        failure_details = {
            "boolean_base_source": base_shape_source,
            "fuzzy_tolerance": tolerance,
            **exc.details,
        }
        return _invalid(
            str(exc),
            failure_stage=exc.stage,
            **failure_details,
        )
    preflight = prebuilt["diagnostics"]
    preflight["boolean_base_source"] = base_shape_source

    def create() -> dict[str, Any]:
        import FreeCAD as App

        doc = App.ActiveDocument
        if doc is None:
            raise RuntimeError("No active document.")
        target_body = service._get_partdesign_body(body.Name)
        target_sections = [doc.getObject(name) for name in resolved["names"]]
        if target_body is None or any(section is None for section in target_sections):
            raise RuntimeError("Thin-loft Body or section no longer exists.")
        if any(
            service._partdesign_body_for_feature(section) is not target_body
            for section in target_sections
        ):
            raise RuntimeError("Thin-loft section ownership changed before execution.")
        current_base = _last_valid_solid_feature(target_body)
        if getattr(current_base, "Name", None) != getattr(base_feature, "Name", None):
            raise RuntimeError("The Body's base solid changed after thin-loft preflight.")

        feature = target_body.newObject("PartDesign::FeatureAdditivePython", "ThinLoft")
        feature.Label = clean_label
        _ensure_feature_properties(feature)
        feature.Sections = target_sections
        feature.SectionDirections = list(resolved["directions"])
        feature.SectionThicknesses = list(resolved["thicknesses"])
        feature.Ruled = bool(ruled)
        feature.MaxDegree = degree
        feature.Refine = bool(refine)
        feature.FuzzyTolerance = tolerance
        feature.Proxy = ThinLoftProxy()
        target_body.Tip = feature
        doc.recompute()

        state = domain_runtime.feature_state_summary(feature)
        shape = domain_runtime.shape_summary(feature)
        if (
            state.get("inspection_complete") is not True
            or state.get("marked_invalid")
            or state.get("shape_valid") is not True
            or shape.get("inspection_complete") is not True
            or int(shape.get("solids", 0) or 0) != 1
        ):
            raise RuntimeError(
                "Thin loft did not recompute to exactly one valid solid: "
                f"state={state}, shape={shape}"
            )
        for section in target_sections:
            view = getattr(section, "ViewObject", None)
            if view is not None:
                view.Visibility = False
        effect = domain_runtime.finalize_partdesign_feature_effect(
            doc,
            target_body,
            feature,
            "thin_loft",
            body_shape_before,
        )
        return {
            "document": doc.Name,
            "body": target_body.Name,
            "feature": feature.Name,
            "feature_label": feature.Label,
            "feature_type": feature.TypeId,
            "feature_kind": str(feature.CadexFeatureType),
            "sections": [section.Name for section in target_sections],
            "section_directions": list(feature.SectionDirections),
            "section_thicknesses_mm": [
                float(value) for value in list(feature.SectionThicknesses)
            ],
            "ruled": bool(feature.Ruled),
            "max_degree": int(feature.MaxDegree),
            "refine": bool(feature.Refine),
            "fuzzy_tolerance": float(feature.FuzzyTolerance),
            "base_feature": getattr(getattr(feature, "BaseFeature", None), "Name", None),
            "body_group": [item.Name for item in list(target_body.Group)],
            "body_tip": getattr(getattr(target_body, "Tip", None), "Name", None),
            "preflight": preflight,
            **effect,
        }

    transaction = run_freecad_transaction(
        f"Create PartDesign thin loft: {clean_label}",
        create,
    )
    return domain_runtime.partdesign_feature_response(
        service,
        transaction,
        operation="thin_loft",
        profile_status={
            "section_count": len(preflight["sections"]),
            "all_sections_valid": True,
            "correspondence": preflight["correspondence"],
        },
    )


def _ensure_feature_properties(feature: Any) -> None:
    properties = set(getattr(feature, "PropertiesList", []) or [])
    if "CadexFeatureType" not in properties:
        feature.addProperty(
            "App::PropertyString",
            "CadexFeatureType",
            "Thin Loft",
            "Persistent Cadex parametric feature implementation.",
        )
    if "Sections" not in properties:
        feature.addProperty(
            "App::PropertyLinkList",
            "Sections",
            "Thin Loft",
            "Ordered open single-curve section sketches.",
        )
    if "SectionDirections" not in properties:
        feature.addProperty(
            "App::PropertyStringList",
            "SectionDirections",
            "Thin Loft",
            "Explicit forward/reversed direction for every section.",
        )
    if "SectionThicknesses" not in properties:
        feature.addProperty(
            "App::PropertyFloatList",
            "SectionThicknesses",
            "Thin Loft",
            "Ordered section thicknesses in millimeters.",
        )
    if "CadexUnrefinedShape" not in properties:
        feature.addProperty(
            "Part::PropertyPartShape",
            "CadexUnrefinedShape",
            "Thin Loft",
            "Fused feature result before optional same-domain refinement.",
        )
    if "Ruled" not in properties:
        feature.addProperty(
            "App::PropertyBool",
            "Ruled",
            "Thin Loft",
            "Use straight transitions between adjacent sections.",
        )
    if "MaxDegree" not in properties:
        feature.addProperty(
            "App::PropertyInteger",
            "MaxDegree",
            "Thin Loft",
            "Maximum B-spline degree along the loft.",
        )
    if "Refine" not in properties:
        feature.addProperty(
            "App::PropertyBool",
            "Refine",
            "Thin Loft",
            "Remove redundant splitter edges from the result.",
        )
    feature.CadexFeatureType = "thin_loft"
    feature.setEditorMode("CadexFeatureType", 1)
    feature.setEditorMode("CadexUnrefinedShape", 2)


def _validate_section_definitions(raw_sections: Any) -> dict[str, Any]:
    if not isinstance(raw_sections, list) or len(raw_sections) < 2:
        return _invalid(
            "sections must contain at least two ordered section definitions.",
            failure_stage="schema",
        )
    normalized = []
    names = []
    for index, raw in enumerate(raw_sections):
        if not isinstance(raw, dict):
            return _invalid(
                "Each sections item must be an object.",
                failure_stage="schema",
                section_index=index,
            )
        name = str(raw.get("sketch_name") or "").strip()
        direction = str(raw.get("direction") or "").strip().lower()
        try:
            thickness = float(raw.get("thickness_mm"))
        except (TypeError, ValueError):
            return _invalid(
                "section thickness_mm must be numeric.",
                failure_stage="schema",
                section_index=index,
                sketch_name=name,
            )
        if not name:
            return _invalid(
                "section sketch_name cannot be empty.",
                failure_stage="schema",
                section_index=index,
            )
        if direction not in _DIRECTIONS:
            return _invalid(
                "section direction must be forward or reversed.",
                failure_stage="schema",
                section_index=index,
                sketch_name=name,
            )
        if not math.isfinite(thickness) or thickness <= _GEOMETRIC_TOLERANCE:
            return _invalid(
                "section thickness_mm must be finite and greater than zero.",
                failure_stage="schema",
                section_index=index,
                sketch_name=name,
                thickness_mm=thickness,
            )
        normalized.append(
            {"sketch_name": name, "direction": direction, "thickness_mm": thickness}
        )
        names.append(name)
    if len(set(names)) != len(names):
        return _invalid(
            "sections cannot contain duplicate sketch names.",
            failure_stage="schema",
            sketch_names=names,
        )
    return {"ok": True, "sections": normalized}


def _resolve_sections(service: Any, body: Any, definitions: list[dict[str, Any]]) -> dict[str, Any]:
    sketches = []
    for index, definition in enumerate(definitions):
        sketch = service._get_sketch(definition["sketch_name"])
        if sketch is None:
            return _invalid(
                f"Thin-loft section sketch not found: {definition['sketch_name']}",
                failure_stage="section_resolution",
                section_index=index,
                requested_sketch=definition["sketch_name"],
            )
        owner = service._partdesign_body_for_feature(sketch)
        if owner is not body:
            return _invalid(
                f"Section {sketch.Name} is not owned by Body {body.Name}.",
                failure_stage="section_ownership",
                section_index=index,
                sketch=sketch.Name,
                section_owner=getattr(owner, "Name", None),
                target_body=body.Name,
            )
        sketches.append(sketch)
    return {
        "ok": True,
        "sketches": sketches,
        "names": [sketch.Name for sketch in sketches],
        "directions": [definition["direction"] for definition in definitions],
        "thicknesses": [definition["thickness_mm"] for definition in definitions],
    }


def _build_geometry(
    sketches: list[Any],
    directions: list[str],
    thicknesses: list[float],
    *,
    ruled: bool,
    max_degree: int,
    refine: bool,
    fuzzy_tolerance: float,
    base_shape: Any | None,
) -> dict[str, Any]:
    import Part

    if len(sketches) < 2:
        raise ThinLoftBuildError(
            "At least two section sketches are required.", stage="section_preflight"
        )
    if len(directions) != len(sketches) or len(thicknesses) != len(sketches):
        raise ThinLoftBuildError(
            "Section, direction, and thickness counts do not match.",
            stage="section_preflight",
            details={
                "section_count": len(sketches),
                "direction_count": len(directions),
                "thickness_count": len(thicknesses),
            },
        )
    if max_degree < 1 or max_degree > 9:
        raise ThinLoftBuildError(
            "MaxDegree must remain from 1 through 9.",
            stage="loft_parameters",
            details={"max_degree": max_degree},
        )
    if not math.isfinite(fuzzy_tolerance) or fuzzy_tolerance < 0:
        raise ThinLoftBuildError(
            "FuzzyTolerance must remain finite and non-negative.",
            stage="loft_parameters",
            details={"fuzzy_tolerance": fuzzy_tolerance},
        )
    for index, thickness in enumerate(thicknesses):
        if not math.isfinite(thickness) or thickness <= _GEOMETRIC_TOLERANCE:
            raise ThinLoftBuildError(
                "Every section thickness must remain finite and greater than zero.",
                stage="loft_parameters",
                details={"section_index": index, "thickness_mm": thickness},
            )
    section_wires = []
    section_diagnostics = []
    for index, (sketch, direction, thickness) in enumerate(
        zip(sketches, directions, thicknesses)
    ):
        wire, diagnostic = _build_section_wire(sketch, direction, thickness, index)
        section_wires.append(wire)
        section_diagnostics.append(diagnostic)
    correspondence = _section_correspondence(section_diagnostics)
    reversed_pairs = [item for item in correspondence if item["crossed_is_shorter"]]
    if reversed_pairs:
        raise ThinLoftBuildError(
            "Explicit section directions cross start/end correspondence. Reverse the "
            "reported section direction instead of creating an inverted loft.",
            stage="section_correspondence",
            details={
                "sections": section_diagnostics,
                "correspondence": correspondence,
                "inconsistent_pairs": reversed_pairs,
            },
        )
    try:
        loft_shape = Part.makeLoft(
            section_wires,
            True,
            bool(ruled),
            False,
            int(max_degree),
        )
    except Exception as exc:
        raise ThinLoftBuildError(
            f"OpenCascade could not loft the prepared thin sections: {exc}",
            stage="loft_builder",
            details={
                "sections": section_diagnostics,
                "correspondence": correspondence,
            },
        ) from exc
    _require_one_valid_solid(loft_shape, "loft_builder", "Thin loft tool shape")
    loft_summary = _shape_summary(loft_shape)

    overlap_volume = 0.0
    base_summary = _shape_summary(base_shape) if base_shape is not None else None
    if base_shape is not None:
        try:
            overlap = base_shape.common((loft_shape,), fuzzy_tolerance)
            overlap_volume = float(overlap.Volume)
        except Exception as exc:
            raise ThinLoftBuildError(
                f"Could not calculate overlap between the Body and thin loft: {exc}",
                stage="body_overlap",
                details={"base_shape": base_summary, "loft_shape": loft_summary},
            ) from exc
        if overlap_volume <= _GEOMETRIC_TOLERANCE:
            raise ThinLoftBuildError(
                "The thin loft does not overlap existing Body material. Extend the root "
                "sections into the Body; tangent contact is not a robust additive fusion.",
                stage="body_overlap",
                details={
                    "overlap_volume_mm3": overlap_volume,
                    "base_shape": base_summary,
                    "loft_shape": loft_summary,
                },
            )
        try:
            unrefined_result_shape = base_shape.fuse((loft_shape,), fuzzy_tolerance)
        except Exception as exc:
            raise ThinLoftBuildError(
                f"OpenCascade could not fuse the thin loft into the Body: {exc}",
                stage="body_fuse",
                details={
                    "overlap_volume_mm3": overlap_volume,
                    "base_shape": base_summary,
                    "loft_shape": loft_summary,
                },
            ) from exc
        _require_one_valid_solid(
            unrefined_result_shape,
            "body_fuse",
            "Unrefined fused Body result",
        )
        result_shape = (
            unrefined_result_shape.removeSplitter() if refine else unrefined_result_shape
        )
        _require_one_valid_solid(result_shape, "body_fuse", "Fused Body result")
        if result_shape.ShapeType != "Solid":
            result_shape = result_shape.Solids[0]
            _require_one_valid_solid(result_shape, "body_fuse", "Normalized Body result")
        volume_added = float(result_shape.Volume) - float(base_shape.Volume)
        if volume_added <= _GEOMETRIC_TOLERANCE:
            raise ThinLoftBuildError(
                "The fused result adds no measurable material to the Body.",
                stage="body_effect",
                details={
                    "volume_added_mm3": volume_added,
                    "overlap_volume_mm3": overlap_volume,
                    "base_shape": base_summary,
                    "loft_shape": loft_summary,
                    "result_shape": _shape_summary(result_shape),
                },
            )
    else:
        unrefined_result_shape = loft_shape
        result_shape = loft_shape.removeSplitter() if refine else loft_shape
        _require_one_valid_solid(result_shape, "loft_builder", "Thin loft result")
        if result_shape.ShapeType != "Solid":
            result_shape = result_shape.Solids[0]
            _require_one_valid_solid(result_shape, "loft_builder", "Normalized thin loft result")
        volume_added = float(result_shape.Volume)

    diagnostics = {
        "sections": section_diagnostics,
        "correspondence": correspondence,
        "ruled": bool(ruled),
        "max_degree": int(max_degree),
        "refine_requested": bool(refine),
        "fuzzy_tolerance": float(fuzzy_tolerance),
        "loft_shape": loft_summary,
        "base_shape": base_summary,
        "overlap_volume_mm3": overlap_volume,
        "volume_added_mm3": volume_added,
        "unrefined_result_shape": _shape_summary(unrefined_result_shape),
        "result_shape": _shape_summary(result_shape),
    }
    return {
        "loft_shape": loft_shape,
        "unrefined_result_shape": unrefined_result_shape,
        "result_shape": result_shape,
        "diagnostics": diagnostics,
    }


def _build_section_wire(
    sketch: Any,
    direction: str,
    thickness: float,
    index: int,
) -> tuple[Any, dict[str, Any]]:
    import FreeCAD as App
    from FreeCAD import Base
    import Part

    if direction not in _DIRECTIONS:
        raise ThinLoftBuildError(
            "Section direction must be forward or reversed.",
            stage="section_preflight",
            details={"section_index": index, "sketch": sketch.Name, "direction": direction},
        )
    state = domain_runtime.feature_state_summary(sketch)
    if state.get("inspection_complete") is not True or state.get("marked_invalid"):
        raise ThinLoftBuildError(
            f"Section sketch {sketch.Name} is marked Invalid.",
            stage="section_preflight",
            details={"section_index": index, "sketch": sketch.Name, "feature_state": state},
        )
    geometries = list(getattr(sketch, "Geometry", []) or [])
    if len(geometries) != 1:
        raise ThinLoftBuildError(
            "Each thin-loft section must contain exactly one curve. Use one construction "
            "B-spline or arc for the complete camber section and keep other references in "
            "a separate layout sketch.",
            stage="section_topology",
            details={
                "section_index": index,
                "sketch": sketch.Name,
                "geometry_count": len(geometries),
                "geometry_types": [type(geometry).__name__ for geometry in geometries],
            },
        )
    geometry = geometries[0]
    try:
        source_edge = geometry.toShape()
    except Exception as exc:
        raise ThinLoftBuildError(
            f"Section geometry {sketch.Name} cannot create a bounded curve edge: {exc}",
            stage="section_curve",
            details={
                "section_index": index,
                "sketch": sketch.Name,
                "curve_type": type(geometry).__name__,
            },
        ) from exc
    if getattr(geometry, "Closed", False) or source_edge.isClosed():
        raise ThinLoftBuildError(
            f"Section sketch {sketch.Name} is closed; thin loft requires an open centerline.",
            stage="section_topology",
            details={"section_index": index, "sketch": sketch.Name},
        )
    if float(source_edge.Length) <= _GEOMETRIC_TOLERANCE:
        raise ThinLoftBuildError(
            f"Section sketch {sketch.Name} contains a degenerate curve.",
            stage="section_topology",
            details={
                "section_index": index,
                "sketch": sketch.Name,
                "edge_length_mm": float(source_edge.Length),
            },
        )
    try:
        source_3d = source_edge.Curve.toBSpline(
            float(source_edge.FirstParameter), float(source_edge.LastParameter)
        )
    except Exception as exc:
        raise ThinLoftBuildError(
            f"Section curve {sketch.Name} cannot be represented as a bounded B-spline: {exc}",
            stage="section_curve",
            details={
                "section_index": index,
                "sketch": sketch.Name,
                "curve_type": type(geometry).__name__,
            },
        ) from exc
    if str(getattr(source_edge, "Orientation", "Forward")) == "Reversed":
        source_3d.reverse()
    if direction == "reversed":
        source_3d.reverse()
    placement = sketch.Placement
    local_poles = list(source_3d.getPoles())
    maximum_plane_error = max(abs(float(point.z)) for point in local_poles)
    if maximum_plane_error > 1e-6:
        raise ThinLoftBuildError(
            f"Section sketch {sketch.Name} is not planar in its sketch frame.",
            stage="section_plane",
            details={
                "section_index": index,
                "sketch": sketch.Name,
                "maximum_plane_error_mm": maximum_plane_error,
            },
        )
    source_2d = Part.Geom2d.BSplineCurve2d()
    source_2d.buildFromPolesMultsKnots(
        poles=[Base.Vector2d(point.x, point.y) for point in local_poles],
        mults=tuple(source_3d.getMultiplicities()),
        knots=tuple(source_3d.getKnots()),
        periodic=source_3d.isPeriodic(),
        degree=int(source_3d.Degree),
        weights=tuple(source_3d.getWeights()),
    )
    half = float(thickness) / 2.0
    try:
        positive_2d = Part.Geom2d.OffsetCurve2d(source_2d, half)
        negative_2d = Part.Geom2d.OffsetCurve2d(source_2d, -half)
        positive_3d = _curve_2d_to_3d(positive_2d)
        negative_3d = _curve_2d_to_3d(negative_2d)
        positive_edge = positive_3d.toShape()
        negative_edge = negative_3d.toShape()
    except Exception as exc:
        raise ThinLoftBuildError(
            f"Could not offset section {sketch.Name} by half-thickness {half:g} mm: {exc}",
            stage="section_offset",
            details={
                "section_index": index,
                "sketch": sketch.Name,
                "thickness_mm": float(thickness),
                "curve_type": type(geometry).__name__,
            },
        ) from exc

    start_2d = source_2d.value(source_2d.FirstParameter)
    end_2d = source_2d.value(source_2d.LastParameter)
    start_tangent = source_2d.tangent(source_2d.FirstParameter)
    end_tangent = source_2d.tangent(source_2d.LastParameter)
    if (
        start_tangent.length() <= _GEOMETRIC_TOLERANCE
        or end_tangent.length() <= _GEOMETRIC_TOLERANCE
    ):
        raise ThinLoftBuildError(
            f"Section {sketch.Name} has an undefined endpoint tangent.",
            stage="section_caps",
            details={"section_index": index, "sketch": sketch.Name},
        )
    start_tangent.normalize()
    end_tangent.normalize()
    start_center = App.Vector(start_2d.x, start_2d.y, 0.0)
    end_center = App.Vector(end_2d.x, end_2d.y, 0.0)
    start_mid = start_center - App.Vector(start_tangent.x, start_tangent.y, 0.0) * half
    end_mid = end_center + App.Vector(end_tangent.x, end_tangent.y, 0.0) * half
    positive_start = positive_edge.Vertexes[0].Point
    positive_end = positive_edge.Vertexes[-1].Point
    negative_start = negative_edge.Vertexes[0].Point
    negative_end = negative_edge.Vertexes[-1].Point
    try:
        end_cap = Part.Arc(positive_end, end_mid, negative_end).toShape()
        negative_edge.reverse()
        start_cap = Part.Arc(negative_start, start_mid, positive_start).toShape()
        section_wire = Part.Wire([positive_edge, end_cap, negative_edge, start_cap])
        section_wire.Placement = placement
        section_face = Part.Face(section_wire)
    except Exception as exc:
        raise ThinLoftBuildError(
            f"Could not close rounded ends on section {sketch.Name}: {exc}",
            stage="section_caps",
            details={
                "section_index": index,
                "sketch": sketch.Name,
                "thickness_mm": float(thickness),
            },
        ) from exc
    if not section_wire.isClosed() or not section_wire.isValid() or not section_face.isValid():
        raise ThinLoftBuildError(
            f"Offset section {sketch.Name} is not one valid closed profile.",
            stage="section_validation",
            details={
                "section_index": index,
                "sketch": sketch.Name,
                "wire_closed": bool(section_wire.isClosed()),
                "wire_valid": bool(section_wire.isValid()),
                "face_valid": bool(section_face.isValid()),
                "offset_edge_count": len(section_wire.Edges),
            },
        )
    start_body = placement.multVec(start_center)
    end_body = placement.multVec(end_center)
    normal = placement.Rotation.multVec(App.Vector(0.0, 0.0, 1.0))
    diagnostic = {
        "index": index,
        "sketch": sketch.Name,
        "sketch_label": getattr(sketch, "Label", sketch.Name),
        "direction": direction,
        "curve_type": type(geometry).__name__,
        "source_is_construction": bool(sketch.getConstruction(0)),
        "source_edge_length_mm": float(source_edge.Length),
        "thickness_mm": float(thickness),
        "start_body": _vector_summary(start_body),
        "end_body": _vector_summary(end_body),
        "plane_origin_body": _vector_summary(placement.Base),
        "plane_normal_body": _vector_summary(normal),
        "section_area_mm2": float(section_face.Area),
        "offset_edge_count": len(section_wire.Edges),
        "closed": True,
        "valid": True,
    }
    return section_wire, diagnostic


def _curve_2d_to_3d(curve_2d: Any) -> Any:
    import FreeCAD as App
    import Part

    spline_2d = curve_2d.toBSpline()
    spline_3d = Part.BSplineCurve()
    spline_3d.buildFromPolesMultsKnots(
        poles=[App.Vector(point.x, point.y, 0.0) for point in spline_2d.getPoles()],
        mults=tuple(spline_2d.getMultiplicities()),
        knots=tuple(spline_2d.getKnots()),
        periodic=spline_2d.isPeriodic(),
        degree=int(spline_2d.Degree),
        weights=tuple(spline_2d.getWeights()),
        CheckRational=True,
    )
    return spline_3d


def _section_correspondence(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for previous, current in zip(sections, sections[1:]):
        previous_start = _summary_vector(previous["start_body"])
        previous_end = _summary_vector(previous["end_body"])
        current_start = _summary_vector(current["start_body"])
        current_end = _summary_vector(current["end_body"])
        start_gap = _distance(previous_start, current_start)
        end_gap = _distance(previous_end, current_end)
        cross_start_gap = _distance(previous_start, current_end)
        cross_end_gap = _distance(previous_end, current_start)
        matched_total = start_gap + end_gap
        crossed_total = cross_start_gap + cross_end_gap
        result.append(
            {
                "from_section": previous["sketch"],
                "to_section": current["sketch"],
                "start_gap_mm": start_gap,
                "end_gap_mm": end_gap,
                "matched_total_mm": matched_total,
                "crossed_total_mm": crossed_total,
                "crossed_is_shorter": crossed_total + 1e-6 < matched_total,
            }
        )
    return result


def _require_one_valid_solid(shape: Any, stage: str, label: str) -> None:
    summary = _shape_summary(shape)
    if (
        shape is None
        or shape.isNull()
        or not shape.isValid()
        or len(shape.Solids) != 1
        or float(shape.Volume) <= _GEOMETRIC_TOLERANCE
    ):
        raise ThinLoftBuildError(
            f"{label} is not exactly one valid non-empty solid.",
            stage=stage,
            details={"shape": summary},
        )


def _last_valid_solid_feature(body: Any) -> Any | None:
    for item in reversed(list(getattr(body, "Group", []) or [])):
        if not str(getattr(item, "TypeId", "")).startswith("PartDesign::"):
            continue
        shape = getattr(item, "Shape", None)
        if shape is None or shape.isNull():
            continue
        if len(getattr(shape, "Solids", []) or []) == 1 and shape.isValid():
            return item
    return None


def _valid_base_shape(base_feature: Any | None) -> tuple[Any | None, str]:
    if base_feature is None:
        return None, "empty_body"
    stored_shape = getattr(base_feature, "CadexUnrefinedShape", None)
    if stored_shape is not None and not stored_shape.isNull():
        shape = stored_shape
        source = "cadex_unrefined_shape"
    elif bool(getattr(base_feature, "Refine", False)):
        get_unrefined = getattr(base_feature, "getUnrefinedShape", None)
        if not callable(get_unrefined):
            raise ThinLoftBuildError(
                "The refined BaseFeature does not expose its pre-refinement shape.",
                stage="body_precondition",
                details={
                    "base_feature": getattr(base_feature, "Name", None),
                    "base_feature_type": getattr(base_feature, "TypeId", None),
                },
            )
        shape = get_unrefined()
        source = "partdesign_unrefined_shape"
        if shape is None or shape.isNull():
            raise ThinLoftBuildError(
                "The refined BaseFeature has no computed pre-refinement shape. Recompute "
                "that feature before creating the thin loft.",
                stage="body_precondition",
                details={
                    "base_feature": getattr(base_feature, "Name", None),
                    "base_feature_type": getattr(base_feature, "TypeId", None),
                    "display_shape": _shape_summary(getattr(base_feature, "Shape", None)),
                },
            )
    else:
        shape = getattr(base_feature, "Shape", None)
        source = "feature_shape"
    if shape is None or shape.isNull() or not shape.isValid() or len(shape.Solids) != 1:
        raise ThinLoftBuildError(
            "The thin loft BaseFeature is not exactly one valid solid.",
            stage="body_precondition",
            details={
                "base_feature": getattr(base_feature, "Name", None),
                "base_shape_source": source,
                "base_shape": _shape_summary(shape),
            },
        )
    return shape.copy(), source


def _invalid_body_history(body: Any) -> list[dict[str, Any]]:
    invalid = []
    for item in list(getattr(body, "Group", []) or []):
        if not str(getattr(item, "TypeId", "")).startswith("PartDesign::"):
            continue
        state = domain_runtime.feature_state_summary(item)
        if state.get("inspection_complete") is not True or state.get("marked_invalid"):
            invalid.append(state)
    return invalid


def _shape_summary(shape: Any | None) -> dict[str, Any]:
    if shape is None:
        return {
            "available": False,
            "valid": False,
            "shape_type": None,
            "solids": 0,
            "faces": 0,
            "edges": 0,
            "vertices": 0,
            "volume": 0.0,
        }
    try:
        return {
            "available": not shape.isNull(),
            "valid": bool(shape.isValid()) if not shape.isNull() else False,
            "shape_type": str(shape.ShapeType),
            "solids": len(shape.Solids),
            "faces": len(shape.Faces),
            "edges": len(shape.Edges),
            "vertices": len(shape.Vertexes),
            "volume": float(shape.Volume),
            "bound_box": domain_runtime.bound_box_summary(shape.BoundBox),
        }
    except Exception as exc:
        return {"available": False, "valid": False, "error": str(exc)}


def _vector_summary(vector: Any) -> dict[str, float]:
    return {"x": float(vector.x), "y": float(vector.y), "z": float(vector.z)}


def _summary_vector(value: dict[str, Any]) -> tuple[float, float, float]:
    return (float(value["x"]), float(value["y"]), float(value["z"]))


def _distance(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    return math.sqrt(sum((left - right) ** 2 for left, right in zip(first, second)))


def _invalid(message: str, **details: Any) -> dict[str, Any]:
    return {"ok": False, "error": message, "retry_same_call": False, **details}
