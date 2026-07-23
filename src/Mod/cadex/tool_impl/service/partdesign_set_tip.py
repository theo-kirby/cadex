# SPDX-License-Identifier: LGPL-2.1-or-later

"""Set the native PartDesign Body Tip and therefore its insertion point."""

from __future__ import annotations

from typing import Any

from CadexTransactions import run_freecad_transaction

from . import domain_runtime


TOOL_SPEC = {
    "name": "partdesign.set_tip",
    "description": (
        "Set an exact Body's native Tip to an exact solid feature already in that Body. "
        "This changes the native insertion point without deleting, cloning, or reordering history."
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
                "description": "Exact internal name of the Body whose Tip changes.",
            },
            "feature_name": {
                "type": "string",
                "description": "Exact internal name of the solid feature that becomes the Tip.",
            },
        },
        "required": ["body_name", "feature_name"],
        "additionalProperties": False,
    },
}


def run(service: Any, body_name: str, feature_name: str) -> dict[str, Any]:
    body = service._get_partdesign_body(str(body_name or "").strip())
    if body is None:
        return _invalid(f"Body not found by exact internal name: {body_name}")
    doc = service._active_document()
    feature = doc.getObject(str(feature_name or "").strip()) if doc is not None else None
    if feature is None:
        return _invalid(f"Feature not found by exact internal name: {feature_name}")
    if feature not in list(body.Group):
        return _invalid(f"Feature {feature.Name} is not in Body {body.Name}.")
    if not str(getattr(feature, "TypeId", "")).startswith("PartDesign::") or not hasattr(
        feature, "Shape"
    ):
        return _invalid("Only a solid PartDesign feature can be a Body Tip.")
    feature_state = domain_runtime.feature_state_summary(feature)
    feature_shape = domain_runtime.shape_summary(feature)
    if (
        feature_state.get("marked_invalid")
        or feature_state.get("shape_null")
        or feature_state.get("shape_valid") is not True
        or int(feature_shape.get("solids", 0) or 0) != 1
    ):
        return _invalid(
            "The requested Tip must be one valid, non-null PartDesign solid.",
            selected_feature_state=feature_state,
            selected_feature_shape=feature_shape,
        )
    body_group_before = list(body.Group)
    feature_index = body_group_before.index(feature)
    downstream = [
        item.Name
        for item in body_group_before[feature_index + 1 :]
        if str(getattr(item, "TypeId", "")).startswith("PartDesign::")
    ]
    if body in list(getattr(feature, "OutListRecursive", []) or []):
        return _invalid(
            "The requested Tip would create a dependency cycle back to its owning Body.",
            dependency_cycle={"body": body.Name, "feature": feature.Name},
        )
    before_tip = getattr(getattr(body, "Tip", None), "Name", None)

    def set_tip() -> dict[str, Any]:
        import FreeCAD as App

        active_doc = App.ActiveDocument
        target_body = service._get_partdesign_body(body.Name)
        target_feature = active_doc.getObject(feature.Name) if active_doc is not None else None
        if target_body is None or target_feature is None:
            raise RuntimeError("Body or feature no longer exists.")
        if target_feature not in list(target_body.Group):
            raise RuntimeError("Feature ownership changed before Tip assignment.")
        target_body.Tip = target_feature
        active_doc.recompute()
        return {
            "document": active_doc.Name,
            "body": target_body.Name,
            "tip_before": before_tip,
            "tip_after": getattr(getattr(target_body, "Tip", None), "Name", None),
            "insertion_occurs_after": target_feature.Name,
            "body_group": [item.Name for item in list(target_body.Group)],
            "selected_feature_state": domain_runtime.feature_state_summary(target_feature),
            "selected_feature_shape": domain_runtime.shape_summary(target_feature),
            "selected_feature_history_index": feature_index,
            "downstream_features_made_inactive": downstream,
            "dag_safe": target_body not in list(
                getattr(target_feature, "OutListRecursive", []) or []
            ),
        }

    transaction = run_freecad_transaction(
        f"Set PartDesign Body Tip: {body.Name} -> {feature.Name}",
        set_tip,
    )
    result = transaction.get("result") if isinstance(transaction.get("result"), dict) else {}
    current_body = service._get_partdesign_body(body.Name)
    actual_tip = getattr(getattr(current_body, "Tip", None), "Name", None)
    ok = (
        bool(transaction.get("ok"))
        and result.get("tip_after") == feature.Name
        and actual_tip == feature.Name
        and bool(result.get("dag_safe"))
    )
    response = {
        "ok": ok,
        "mutation": result,
        "document_delta": transaction.get("document_delta") or {},
        "native_diagnostics": domain_runtime.recompute_diagnostics(transaction),
        "body_state": service._partdesign_body_summary(
            current_body
        ),
        "tip_before": before_tip,
        "tip_after": actual_tip,
        "tip_changed": actual_tip != before_tip,
    }
    if not ok:
        response["error"] = transaction.get("error") or "FreeCAD did not retain the requested Body Tip."
        response["retry_same_call"] = False
    return response


def _invalid(message: str, **details: Any) -> dict[str, Any]:
    return {"ok": False, "error": message, "retry_same_call": False, **details}
