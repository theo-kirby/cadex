# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Document-object ownership operations shared by scripted CAD engines."""

from __future__ import annotations

from typing import Any


def owned_model_objects(doc: Any, property_name: str, model_id: str) -> list[Any]:
    return [
        obj
        for obj in list(getattr(doc, "Objects", []) or [])
        if property_name in list(getattr(obj, "PropertiesList", []) or [])
        and str(getattr(obj, property_name, "") or "") == model_id
    ]


def contained_object_closure(roots: list[Any]) -> list[Any]:
    contained: dict[str, Any] = {}
    for root in roots:
        name = str(getattr(root, "Name", "") or "")
        if name:
            contained[name] = root
        if str(getattr(root, "TypeId", "") or "") not in {
            "App::Part",
            "PartDesign::Body",
        }:
            continue
        for child in list(getattr(root, "OutListRecursive", []) or []):
            child_name = str(getattr(child, "Name", "") or "")
            if child_name:
                contained[child_name] = child
    return list(contained.values())


def delete_contained_objects(doc: Any, roots: list[Any]) -> list[str]:
    contained = contained_object_closure(roots)
    contained_names = {str(obj.Name) for obj in contained}

    def contained_descendants(obj: Any) -> int:
        return sum(
            1
            for child in list(getattr(obj, "OutListRecursive", []) or [])
            if str(getattr(child, "Name", "") or "") in contained_names
        )

    deletion_order = sorted(
        contained,
        key=lambda obj: (contained_descendants(obj), str(obj.Name)),
    )
    deleted: list[str] = []
    for obj in deletion_order:
        name = str(obj.Name)
        if doc.getObject(name) is None:
            continue
        doc.removeObject(name)
        deleted.append(name)
    return deleted


def delete_owned_model_objects(
    doc: Any,
    property_name: str,
    model_id: str,
) -> list[str]:
    return delete_contained_objects(
        doc,
        owned_model_objects(doc, property_name, model_id),
    )


# ---------------------------------------------------------------------------
# Program-ownership closure, lint, and orphan detection (project publication)
# ---------------------------------------------------------------------------

#: Mirrors CadexScriptedDomainPublication._ASSEMBLY_DEPENDENCY_SUFFIX; kept
#: local so publication can import this module without a cycle.
_DEPENDENCY_ANCHOR_SUFFIX = "__dependencies"


def _object_name(obj: Any) -> str:
    return str(getattr(obj, "Name", "") or "")


def _tagged_program_objects(doc: Any, program_id: str) -> list[Any]:
    import CadexScriptedDomains as contracts

    return [
        obj
        for obj in list(getattr(doc, "Objects", []) or [])
        if contracts.PROP_PROGRAM_ID in list(getattr(obj, "PropertiesList", []) or [])
        and str(getattr(obj, contracts.PROP_PROGRAM_ID, "") or "") == str(program_id)
    ]


def _closure_of(roots: list[Any]) -> dict[str, Any]:
    """Names→objects reachable from ``roots`` via Group membership and OutList."""

    closure: dict[str, Any] = {}
    stack = list(roots)
    while stack:
        obj = stack.pop()
        name = _object_name(obj)
        if not name or name in closure:
            continue
        closure[name] = obj
        stack.extend(list(getattr(obj, "Group", []) or []))
        stack.extend(list(getattr(obj, "OutList", []) or []))
    return closure


def owned_closure(doc: Any, program_id: str) -> set[Any]:
    """Objects tagged with ``program_id`` plus the children publication creates.

    Publication legitimately materializes untagged internals under tagged
    roots — PartDesign Body internals (origin, origin features, sketches,
    features), publication shape targets inside the program root, Assembly
    joint/simulation/view groups and their members. Those are reachable from
    the tagged objects through Group membership and OutList dependencies, so
    the closure is the tagged set expanded transitively over both.
    """

    return set(_closure_of(_tagged_program_objects(doc, str(program_id))).values())


def untagged_objects(doc: Any, program_id: str) -> list[Any]:
    """Document objects outside the program's owned closure."""

    closure = {
        _object_name(obj) for obj in owned_closure(doc, str(program_id))
    }
    return [
        obj
        for obj in list(getattr(doc, "Objects", []) or [])
        if _object_name(obj) not in closure
    ]


def _contract_base_name(output_name: str) -> str:
    """Base output name of one tagged object's output property.

    Managed satellite objects reuse their owner's base name either with a
    dotted suffix (``base.ground`` joints, ``asm.move.0``) or with the
    assembly dependency-anchor suffix (``asm__dependencies``).
    """

    base = str(output_name).partition(".")[0]
    if base.endswith(_DEPENDENCY_ANCHOR_SUFFIX):
        base = base[: -len(_DEPENDENCY_ANCHOR_SUFFIX)]
    return base


def orphaned_outputs(
    doc: Any,
    program_id: str,
    contract: list[dict[str, Any]],
) -> list[Any]:
    """Tagged objects whose (domain, base output name) left the contract.

    ``contract`` rows are ``{name, type, domain}``. Tagged objects without an
    output name (per-domain containers such as the Part Design program root)
    are orphaned exactly when their whole domain has no outputs left. Each
    orphan drags along its contained closure (Group/OutList reachable objects)
    minus anything still reachable from a surviving tagged object, so
    container internals (publication shape targets, joint groups) do not
    linger after their owner is retired.
    """

    import CadexScriptedDomains as contracts

    keep = {
        (str(item.get("domain") or ""), str(item.get("name") or ""))
        for item in list(contract or [])
    }
    live_domains = {domain for domain, _name in keep}
    orphans: list[Any] = []
    survivors: list[Any] = []
    for obj in _tagged_program_objects(doc, str(program_id)):
        domain = str(getattr(obj, contracts.PROP_PROGRAM_DOMAIN, "") or "")
        output_name = str(getattr(obj, contracts.PROP_PROGRAM_OUTPUT, "") or "")
        if output_name:
            retired = (domain, _contract_base_name(output_name)) not in keep
        else:
            retired = domain not in live_domains
        (orphans if retired else survivors).append(obj)
    surviving_closure = set(_closure_of(survivors))
    orphan_names = {_object_name(obj) for obj in orphans}
    result: dict[str, Any] = {}
    for name, obj in _closure_of(orphans).items():
        if name in orphan_names or name not in surviving_closure:
            result[name] = obj
    return list(result.values())
