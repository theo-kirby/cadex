# SPDX-License-Identifier: LGPL-2.1-or-later

"""Create a native PartDesign datum axis from an origin and direction."""

from __future__ import annotations

from typing import Any

from CadexTransactions import run_freecad_transaction

from . import domain_runtime


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

TOOL_SPEC = {
    "name": "partdesign.create_datum_axis",
    "description": (
        "Create one native PartDesign datum axis in an exact Body from an explicit 3D origin "
        "and non-zero direction. The axis remains an editable datum object and can drive "
        "revolutions, grooves, polar patterns, and measurements."
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
            "label": {"type": "string", "description": "Visible label for the new datum axis."},
            "origin": {
                **_VECTOR_SCHEMA,
                "description": "Point in mm the axis passes through.",
            },
            "direction": {
                **_VECTOR_SCHEMA,
                "description": "Non-zero axis direction.",
            },
        },
        "required": ["body_name", "label", "origin", "direction"],
        "additionalProperties": False,
    },
}


def run(
    service: Any,
    body_name: str,
    label: str,
    origin: dict[str, float],
    direction: dict[str, float],
) -> dict[str, Any]:
    return _create_datum(
        service,
        body_name=body_name,
        label=label,
        origin=origin,
        direction=direction,
        type_id="PartDesign::Line",
        object_name="DatumLine",
        operation="datum axis",
    )


def _create_datum(
    service: Any,
    *,
    body_name: str,
    label: str,
    origin: dict[str, float],
    direction: dict[str, float],
    type_id: str,
    object_name: str,
    operation: str,
) -> dict[str, Any]:
    body = service._get_partdesign_body(body_name)
    if body is None:
        return _invalid(f"PartDesign Body not found: {body_name}")
    clean_label = str(label or "").strip()
    if not clean_label:
        return _invalid("label is required.")
    origin_vector = _vector(origin, "origin", allow_zero=True)
    if not origin_vector.get("ok"):
        return origin_vector
    direction_vector = _vector(direction, "direction", allow_zero=False)
    if not direction_vector.get("ok"):
        return direction_vector
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
        if target_body is None:
            raise RuntimeError(f"PartDesign Body no longer exists: {body.Name}")
        datum = target_body.newObject(type_id, object_name)
        datum.Label = clean_label
        datum.MapMode = "Deactivated"
        datum.Placement = App.Placement(
            App.Vector(*origin_vector["vector"]),
            App.Rotation(
                App.Vector(0.0, 0.0, 1.0),
                App.Vector(*direction_vector["vector"]),
            ),
        )
        doc.recompute()
        return {
            "document": doc.Name,
            "body": target_body.Name,
            "datum": datum.Name,
            "datum_label": datum.Label,
            "datum_type": datum.TypeId,
            "map_mode": str(datum.MapMode),
            "placement": service._placement_summary(datum.Placement),
            "state": [str(value) for value in list(datum.State)],
            "body_group": [item.Name for item in list(target_body.Group)],
            "body_tip": getattr(getattr(target_body, "Tip", None), "Name", None),
        }

    transaction = run_freecad_transaction(f"Create {operation}: {clean_label}", create)
    result = transaction.get("result") if isinstance(transaction.get("result"), dict) else {}
    response = {
        "ok": bool(transaction.get("ok")),
        "mutation": result,
        "document_delta": transaction.get("document_delta") or {},
        "native_diagnostics": domain_runtime.recompute_diagnostics(transaction),
        "body_state": service._partdesign_body_summary(body),
    }
    if not response["ok"]:
        response["error"] = transaction.get("error") or f"{operation} creation failed."
        response["retry_same_call"] = False
    return response


def _vector(value: Any, name: str, *, allow_zero: bool) -> dict[str, Any]:
    try:
        vector = (float(value["x"]), float(value["y"]), float(value["z"]))
    except (KeyError, TypeError, ValueError):
        return _invalid(f"{name} requires numeric x, y, and z.")
    if not allow_zero and sum(component * component for component in vector) <= 1e-18:
        return _invalid(f"{name} must be non-zero.")
    return {"ok": True, "vector": vector}


def _invalid(message: str, **details: Any) -> dict[str, Any]:
    return {"ok": False, "error": message, "retry_same_call": False, **details}
