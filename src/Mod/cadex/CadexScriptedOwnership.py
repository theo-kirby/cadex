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
