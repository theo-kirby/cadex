# SPDX-License-Identifier: LGPL-2.1-or-later

"""Service tool definition for ``partdesign.create_body``."""

from __future__ import annotations

from typing import Any

from CadexTransactions import run_freecad_transaction

from . import domain_runtime


TOOL_SPEC = {
    "contextual": True,
    "description": (
        "Create a new PartDesign Body. Each physically separate component "
        "(e.g. housing vs rotor) needs its own Body; create it before adding "
        "that component's sketches and features."
    ),
    "name": "partdesign.create_body",
    "edit_modes": ["none"],
    "parameters": {
        "type": "object",
        "properties": {
            "label": {
                "type": "string",
                "description": "Component name for the Body, e.g. 'Housing'.",
            },
        },
        "required": ["label"],
        "additionalProperties": False,
    },
    "safety": "SAFE_WRITE",
    "workbench": "PartDesignWorkbench",
}


def run(service, label: str) -> dict[str, Any]:
    clean_label = str(label or "").strip()
    if not clean_label:
        return {"ok": False, "error": "label is required.", "retry_same_call": False}

    def _create_body() -> dict[str, Any]:
        import FreeCAD as App

        doc = App.ActiveDocument
        if doc is None:
            raise RuntimeError("No active document. Create or open a document in FreeCAD first.")
        body = doc.addObject("PartDesign::Body", "Body")
        body.Label = clean_label
        doc.recompute()
        return {
            "document": doc.Name,
            "body": body.Name,
            "body_label": getattr(body, "Label", body.Name),
            "body_state": service._partdesign_body_summary(body),
        }

    transaction = run_freecad_transaction(
        f"Create PartDesign body: {clean_label}",
        _create_body,
    )
    result = transaction.get("result") if isinstance(transaction.get("result"), dict) else {}
    response = {
        "ok": bool(transaction.get("ok")),
        "mutation": result,
        "document_delta": transaction.get("document_delta") or {},
        "native_diagnostics": domain_runtime.recompute_diagnostics(transaction),
    }
    if not response["ok"]:
        response["error"] = transaction.get("error") or "PartDesign Body creation failed."
    return response
