# SPDX-License-Identifier: LGPL-2.1-or-later

"""Repoint one existing App::Link at a new linked object without recreating it."""

from __future__ import annotations

from typing import Any

from CadexTools import tool_failure
from CadexTransactions import run_freecad_transaction

from . import domain_runtime
from .assembly_insert_component import (
    _component_candidates,
    _validate_component_source,
)


TOOL_SPEC = {
    "name": "core.relink_object",
    "description": (
        "Repoint one existing App::Link (or Assembly::AssemblyLink) at a new "
        "target object in the active document by rewriting its LinkedObject "
        "property in place. Use this to repair a link whose target was deleted "
        "or was pointed at the wrong object: the link keeps its exact internal "
        "Name, Label, and Placement, so every joint, assembly membership, or "
        "other reference that names the link stays intact. This is the correct "
        "way to recover a dead assembly component without deleting it and "
        "rebuilding the joints that reference it. The new target is validated "
        "as a legal link target (PartDesign Body, App::Part, Assembly, or a "
        "standalone solid) and must not create a dependency cycle."
    ),
    "contextual": True,
    "safety": "SAFE_WRITE",
    "edit_modes": ["none"],
    "parameters": {
        "type": "object",
        "properties": {
            "link_name": {
                "type": "string",
                "minLength": 1,
                "description": (
                    "Exact internal Name of the existing App::Link to repoint, "
                    "e.g. 'ChassisBody001'."
                ),
            },
            "new_target_name": {
                "type": "string",
                "minLength": 1,
                "description": (
                    "Exact internal Name of the object in the active document "
                    "to link to, e.g. the live 'ChassisBody'."
                ),
            },
        },
        "required": ["link_name", "new_target_name"],
        "additionalProperties": False,
    },
}


def run(service: Any, link_name: str, new_target_name: str) -> dict[str, Any]:
    doc = service._active_document()
    clean_link = str(link_name or "").strip()
    clean_target = str(new_target_name or "").strip()
    if doc is None:
        return _fail("NO_ACTIVE_DOCUMENT", "precondition", "No active document.", link_name, new_target_name)

    link = doc.getObject(clean_link) if clean_link else None
    if link is None:
        return _fail(
            "LINK_NOT_FOUND",
            "precondition",
            f"No object found by exact internal name: {clean_link}",
            link_name,
            new_target_name,
            candidates=_link_candidates(doc),
        )
    if not _is_link(link):
        return _fail(
            "NOT_A_LINK",
            "precondition",
            (
                f"Object {clean_link} is a {getattr(link, 'TypeId', '?')}, not an "
                "App::Link. core.relink_object only repoints link objects."
            ),
            link_name,
            new_target_name,
            candidates=_link_candidates(doc),
        )

    target = doc.getObject(clean_target) if clean_target else None
    if target is None:
        return _fail(
            "TARGET_NOT_FOUND",
            "precondition",
            f"No object found by exact internal name: {clean_target}",
            link_name,
            new_target_name,
            candidates=_component_candidates(service, doc),
        )
    if target is link:
        return _fail(
            "SELF_LINK",
            "precondition",
            "A link cannot point at itself.",
            link_name,
            new_target_name,
        )
    if link in list(getattr(target, "OutListRecursive", []) or []):
        return _fail(
            "DEPENDENCY_CYCLE",
            "precondition",
            (
                f"Linking {clean_link} to {clean_target} would create a "
                "dependency cycle because the target already depends on the link."
            ),
            link_name,
            new_target_name,
        )

    validation = _validate_component_source(service, target)
    if not validation.get("ok"):
        return _fail(
            "TARGET_NOT_LINKABLE",
            "precondition",
            str(validation.get("error", "The new target is not a valid link target.")),
            link_name,
            new_target_name,
            operation="relink_object",
            target_validation=validation,
        )

    before = _link_state(service, link)
    invalid_before = _invalid_names(doc)

    def repoint() -> dict[str, Any]:
        import FreeCAD as App

        active = App.ActiveDocument
        if active is None:
            raise RuntimeError("No active document.")
        live_link = active.getObject(clean_link)
        live_target = active.getObject(clean_target)
        if live_link is None or live_target is None:
            raise RuntimeError("The link or target object no longer exists.")
        live_link.LinkedObject = live_target
        live_link.touch()
        active.recompute()
        return _link_state(service, live_link)

    def verify(after: dict[str, Any]) -> dict[str, Any]:
        new_invalid = [name for name in _invalid_names(doc) if name not in invalid_before]
        checks = [
            {
                "name": "link_repointed",
                "ok": after.get("linked_object") == clean_target,
                "expected": clean_target,
                "actual": after.get("linked_object"),
            },
            {
                "name": "link_carries_shape",
                "ok": bool(after.get("has_shape")),
                "actual": after.get("has_shape"),
            },
            {
                "name": "no_new_invalid_objects",
                "ok": not new_invalid,
                "new_invalid_objects": new_invalid,
            },
        ]
        return {"ok": all(check["ok"] for check in checks), "checks": checks}

    transaction = run_freecad_transaction(
        f"Relink {clean_link} -> {clean_target}",
        repoint,
        verifier=verify,
    )
    after = transaction.get("result") if isinstance(transaction.get("result"), dict) else {}
    return domain_runtime.build_mutation_result(
        transaction,
        extra={
            "operation": "relink_object",
            "link": clean_link,
            "new_target": clean_target,
            "link_state_before": before,
            "link_state_after": after,
            "dependents_recovered": _dependents_recovered(
                before.get("dependents") or [],
                after.get("dependents") or [],
            ),
        },
        next_action=(
            "The link now carries the new target's geometry. If it is an "
            "assembly component, run assembly.solve to reposition it, then "
            "verify or rebuild the joints that reference it."
        ),
    )


def _is_link(obj: Any) -> bool:
    try:
        if obj.isDerivedFrom("App::Link"):
            return True
    except Exception:
        pass
    return "LinkedObject" in list(getattr(obj, "PropertiesList", []) or [])


def _link_state(service: Any, link: Any) -> dict[str, Any]:
    linked = getattr(link, "LinkedObject", None)
    shape = getattr(link, "Shape", None)
    try:
        has_shape = shape is not None and not bool(shape.isNull())
    except Exception:
        has_shape = False
    try:
        is_valid = bool(link.isValid())
    except Exception:
        is_valid = None
    return {
        "name": link.Name,
        "label": link.Label,
        "type": link.TypeId,
        "linked_object": getattr(linked, "Name", None),
        "linked_object_alive": _object_alive(linked),
        "has_shape": has_shape,
        "is_valid": is_valid,
        "state": [str(item) for item in list(getattr(link, "State", []) or [])],
        "dependents": [_dependent_summary(obj) for obj in list(getattr(link, "InList", []) or [])],
    }


def _dependent_summary(obj: Any) -> dict[str, Any]:
    try:
        is_valid = bool(obj.isValid())
    except Exception:
        is_valid = None
    properties = list(getattr(obj, "PropertiesList", []) or [])
    is_joint = "Reference1" in properties or "JointType" in properties
    return {
        "name": getattr(obj, "Name", None),
        "label": getattr(obj, "Label", None),
        "type": getattr(obj, "TypeId", None),
        "is_joint": is_joint,
        "is_valid": is_valid,
    }


def _dependents_recovered(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    before_by_name = {item.get("name"): item for item in before}
    recovered = []
    for item in after:
        prior = before_by_name.get(item.get("name")) or {}
        if prior.get("is_valid") is False and item.get("is_valid") is True:
            recovered.append(item)
    return recovered


def _object_alive(obj: Any) -> bool:
    if obj is None:
        return False
    doc = getattr(obj, "Document", None)
    name = getattr(obj, "Name", None)
    if doc is None or name is None:
        return False
    try:
        return doc.getObject(name) is not None
    except Exception:
        return False


def _invalid_names(doc: Any) -> set[str]:
    invalid: set[str] = set()
    for obj in list(getattr(doc, "Objects", []) or []):
        state = [str(item).lower() for item in list(getattr(obj, "State", []) or [])]
        checker = getattr(obj, "isValid", None)
        valid = True
        if callable(checker):
            try:
                valid = bool(checker())
            except Exception:
                valid = False
        if not valid or any(flag in {"invalid", "error"} for flag in state):
            invalid.add(str(getattr(obj, "Name", "")))
    return invalid


def _link_candidates(doc: Any) -> list[dict[str, Any]]:
    candidates = []
    for obj in list(getattr(doc, "Objects", []) or []):
        if _is_link(obj):
            candidates.append(
                {"name": obj.Name, "label": obj.Label, "type": obj.TypeId}
            )
    return candidates[:40]


def _fail(
    code: str,
    stage: str,
    message: str,
    link_name: Any,
    new_target_name: Any,
    **details: Any,
) -> dict[str, Any]:
    return tool_failure(
        TOOL_SPEC["name"],
        code,
        stage,
        message,
        requested={"link_name": link_name, "new_target_name": new_target_name},
        **details,
    )
