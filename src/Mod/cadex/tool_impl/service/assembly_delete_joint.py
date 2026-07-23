# SPDX-License-Identifier: LGPL-2.1-or-later

"""Delete one joint from an assembly's JointGroup without touching geometry."""

from __future__ import annotations

from typing import Any

from CadexTransactions import run_freecad_transaction

from . import domain_runtime


TOOL_SPEC = {
    "name": "assembly.delete_joint",
    "description": (
        "Delete exactly one joint from an assembly by internal name. The joint "
        "must live in the assembly's JointGroup (a mate created by "
        "assembly.create_joint, or a grounding created by "
        "assembly.ground_component). Removing a joint deletes only that "
        "constraint: component links and their geometry are untouched, and "
        "already-positioned components keep their current placement. Use this "
        "to drop a redundant, conflicting, or wrong mate, or to un-ground a "
        "component. After deleting, run assembly.solve if the remaining joints "
        "should reposition anything. Deleting the last grounded joint leaves "
        "the assembly with no fixed component until you ground one again."
    ),
    "contextual": True,
    "safety": "SAFE_WRITE",
    "workbench": "AssemblyWorkbench",
    "edit_modes": ["none"],
    "parameters": {
        "type": "object",
        "properties": {
            "assembly_name": {
                "type": "string",
                "description": (
                    "Exact internal name of the assembly from "
                    "assembly.list_structure."
                ),
            },
            "joint_name": {
                "type": "string",
                "description": (
                    "Exact internal name of the joint to delete, e.g. "
                    "'Joint007'. Read joint names from assembly.list_structure."
                ),
            },
        },
        "required": ["assembly_name", "joint_name"],
        "additionalProperties": False,
    },
}


def run(service: Any, assembly_name: str, joint_name: str) -> dict[str, Any]:
    doc = service._active_document()
    if doc is None:
        return _invalid("No active document.")
    assembly = _find_assembly(service, assembly_name)
    if assembly is None:
        return _invalid(
            f"Assembly not found by exact internal name: {assembly_name}. "
            "Call assembly.list_structure for exact names."
        )
    clean_joint = str(joint_name or "").strip()
    joint = doc.getObject(clean_joint) if clean_joint else None
    assembly_joints = service._assembly_joint_objects(assembly)
    joint_names = {getattr(item, "Name", None) for item in assembly_joints}
    if joint is None or clean_joint not in joint_names:
        return _invalid(
            f"Joint not found in assembly {assembly.Name} by exact internal "
            f"name: {joint_name}",
            joints=[service._joint_summary(item) for item in assembly_joints[:40]],
        )

    joint_group = domain_runtime.assembly_joint_group(assembly)
    joint_before = service._joint_summary(joint)
    invalid_before = _invalid_names(doc)

    def remove() -> dict[str, Any]:
        import FreeCAD as App

        active = App.ActiveDocument
        if active is None:
            raise RuntimeError("No active document.")
        target_assembly = active.getObject(assembly.Name)
        live_joint = active.getObject(clean_joint)
        if target_assembly is None or live_joint is None:
            raise RuntimeError("The assembly or joint no longer exists.")
        native_group = domain_runtime.assembly_joint_group(target_assembly)
        if native_group is not None and live_joint in list(
            getattr(native_group, "Group", []) or []
        ):
            remover = getattr(native_group, "removeObject", None)
            if callable(remover):
                remover(live_joint)
        active.removeObject(clean_joint)
        active.recompute()
        remaining = service._assembly_joint_objects(target_assembly)
        return {
            "document": active.Name,
            "assembly": target_assembly.Name,
            "deleted_joint": clean_joint,
            "joint_group": getattr(native_group, "Name", None),
            "joint_group_members": [
                getattr(child, "Name", None)
                for child in list(getattr(native_group, "Group", []) or [])
            ]
            if native_group is not None
            else [],
            "remaining_joints": [service._joint_summary(item) for item in remaining],
            "grounded_remaining": sum(
                1 for item in remaining if service._is_grounded_joint(item)
            ),
            "still_present": active.getObject(clean_joint) is not None,
            "solver_diagnostics": domain_runtime.assembly_solver_diagnostics(
                target_assembly
            ),
        }

    def verify(result: dict[str, Any]) -> dict[str, Any]:
        new_invalid = [name for name in _invalid_names(doc) if name not in invalid_before]
        checks = [
            {
                "name": "joint_absent",
                "ok": result.get("still_present") is False,
                "joint": clean_joint,
            },
            {
                "name": "joint_group_membership_cleared",
                "ok": clean_joint not in list(result.get("joint_group_members") or []),
                "actual": result.get("joint_group_members"),
            },
            {
                "name": "no_new_invalid_objects",
                "ok": not new_invalid,
                "new_invalid_objects": new_invalid,
            },
        ]
        return {"ok": all(check["ok"] for check in checks), "checks": checks}

    transaction = run_freecad_transaction(
        f"Delete assembly joint: {clean_joint}",
        remove,
        verifier=verify,
    )
    mutation = transaction.get("result") if isinstance(transaction.get("result"), dict) else {}
    grounded_remaining = int(mutation.get("grounded_remaining") or 0)
    next_action = (
        "Run assembly.solve if the remaining joints should reposition "
        "components."
        if grounded_remaining
        else "No grounded component remains; ground one with "
        "assembly.ground_component before assembly.solve can succeed."
    )
    return domain_runtime.build_mutation_result(
        transaction,
        extra={
            "operation": "delete_joint",
            "deleted_joint": joint_before,
            "mutation": mutation,
        },
        next_action=next_action,
    )


def _find_assembly(service: Any, assembly_name: str) -> Any:
    clean = str(assembly_name or "").strip()
    if not clean:
        return None
    for assembly in service._assembly_objects():
        if assembly.Name == clean:
            return assembly
    return None


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


def _invalid(message: str, **details: Any) -> dict[str, Any]:
    return {"ok": False, "error": message, "retry_same_call": False, **details}
