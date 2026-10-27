# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Stable publication boundary for generated CAD models.

Scripted engines are free to replace their private implementation history, but
objects consumed by Assembly, TechDraw, FEM, CAM, materials, or user-authored
links must retain their FreeCAD identity.  This module owns that boundary.
"""

from __future__ import annotations

from typing import Any


PROP_ROLE = "CadexScriptedRole"
PROP_ENGINE = "CadexScriptedEngine"
PROP_MODEL_ID = "CadexScriptedModelId"
PROP_OUTPUT_KEY = "CadexScriptedOutputKey"
PROP_REVISION = "CadexPublishedRevision"
PROP_IMPLEMENTATION = "CadexImplementationObject"
PROP_INTERFACES = "CadexPublishedInterfaces"
PROP_PARAMETER_NAMES = "CadexParameterNames"

ROLE_MODEL = "model"
ROLE_PUBLICATION = "publication"
ROLE_PUBLICATION_TARGET = "publication_target"
ROLE_IMPLEMENTATION = "implementation"

_LINK_PROPERTY_TYPES = {
    "App::PropertyLink",
    "App::PropertyXLink",
    "App::PropertyLinkHidden",
    "App::PropertyLinkChild",
    "App::PropertyLinkGlobal",
}
_LINK_LIST_PROPERTY_TYPES = {
    "App::PropertyLinkList",
    "App::PropertyXLinkList",
    "App::PropertyLinkListChild",
    "App::PropertyLinkListGlobal",
    "App::PropertyLinkListHidden",
}
_LINK_SUB_PROPERTY_TYPES = {
    "App::PropertyLinkSub",
    "App::PropertyXLinkSub",
    "App::PropertyLinkSubChild",
    "App::PropertyLinkSubGlobal",
    "App::PropertyLinkSubHidden",
    "App::PropertyXLinkSubHidden",
}
_LINK_SUB_LIST_PROPERTY_TYPES = {
    "App::PropertyLinkSubList",
    "App::PropertyXLinkSubList",
    "App::PropertyLinkSubListChild",
    "App::PropertyLinkSubListGlobal",
    "App::PropertyLinkSubListHidden",
}


class PublicationError(RuntimeError):
    """A publication mutation could not be completed without reference loss."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        self.details = dict(details or {})
        super().__init__(message)


def ensure_string_property(obj: Any, name: str) -> None:
    if name not in list(getattr(obj, "PropertiesList", []) or []):
        obj.addProperty("App::PropertyString", name, "Cadex Publication")


def tag_object(
    obj: Any,
    *,
    role: str,
    engine: str,
    model_id: str,
    output_key: str = "",
    revision: str = "",
) -> None:
    values = {
        PROP_ROLE: role,
        PROP_ENGINE: engine,
        PROP_MODEL_ID: model_id,
        PROP_OUTPUT_KEY: output_key,
        PROP_REVISION: revision,
    }
    for name, value in values.items():
        ensure_string_property(obj, name)
        setattr(obj, name, str(value or ""))


def role_of(obj: Any) -> str:
    return str(getattr(obj, PROP_ROLE, "") or "")


def is_publication(obj: Any) -> bool:
    return role_of(obj) == ROLE_PUBLICATION


def model_root_for(obj: Any) -> Any:
    """Resolve the one owning scripted-model root through native dependencies."""

    if role_of(obj) == ROLE_MODEL:
        return obj
    model_id = str(getattr(obj, PROP_MODEL_ID, "") or "")
    linked = getattr(obj, "LinkedObject", None)
    linked_root = linked[0] if isinstance(linked, (tuple, list)) and linked else None
    if (
        linked_root is not None
        and role_of(linked_root) == ROLE_MODEL
        and str(getattr(linked_root, PROP_MODEL_ID, "") or "") == model_id
    ):
        return linked_root
    matches = [
        owner
        for owner in list(getattr(obj, "InList", []) or [])
        if role_of(owner) == ROLE_MODEL
        and str(getattr(owner, PROP_MODEL_ID, "") or "") == model_id
    ]
    if len(matches) != 1:
        raise PublicationError(
            "A scripted publication must belong to exactly one model root.",
            details={
                "object": str(getattr(obj, "Name", "") or ""),
                "model_id": model_id,
                "roots": [str(getattr(item, "Name", "") or "") for item in matches],
            },
        )
    return matches[0]


def model_implementations(root: Any) -> list[Any]:
    return [
        child
        for child in list(getattr(root, "Group", []) or [])
        if role_of(child) == ROLE_IMPLEMENTATION
    ]


def global_placement(obj: Any) -> Any | None:
    getter = getattr(obj, "getGlobalPlacement", None)
    if callable(getter):
        try:
            return getter()
        except Exception as exc:
            raise PublicationError(
                f"Could not read the global placement of "
                f"{getattr(obj, 'Name', '<object>')}.",
                details={"native_error": str(exc)},
            ) from exc
    return getattr(obj, "Placement", None)


def placement_relative_to(root: Any, obj: Any) -> Any | None:
    object_global = global_placement(obj)
    root_global = global_placement(root)
    if object_global is None:
        return None
    if root_global is None:
        return object_global
    try:
        return root_global.inverse().multiply(object_global)
    except Exception as exc:
        raise PublicationError(
            f"Could not transform {getattr(obj, 'Name', '<object>')} into the "
            "published model coordinate system.",
            details={"native_error": str(exc)},
        ) from exc


def create_publication(
    doc: Any,
    root: Any,
    source: Any,
    *,
    internal_name: str,
    label: str,
    engine: str,
    model_id: str,
    output_key: str,
    revision: str,
) -> Any:
    target = doc.addObject("Part::Feature", f"{internal_name}_Source")
    tag_object(
        target,
        role=ROLE_PUBLICATION_TARGET,
        engine=engine,
        model_id=model_id,
        output_key=output_key,
        revision=revision,
    )
    root.addObject(target)
    target_view = getattr(target, "ViewObject", None)
    if target_view is not None and hasattr(target_view, "Visibility"):
        target_view.Visibility = False

    published = doc.addObject("App::Link", internal_name)
    published.Label = str(label or output_key)
    tag_object(
        published,
        role=ROLE_PUBLICATION,
        engine=engine,
        model_id=model_id,
        output_key=output_key,
        revision=revision,
    )
    published.LinkedObject = (root, f"{target.Name}.")
    published.LinkTransform = True
    ensure_string_property(published, PROP_IMPLEMENTATION)
    setattr(published, PROP_IMPLEMENTATION, target.Name)
    update_publication(published, root, source, revision=revision)
    _copy_presentation(source, published)
    return published


def update_publication(
    published: Any,
    root: Any,
    source: Any,
    *,
    revision: str,
) -> None:
    shape = getattr(source, "Shape", None)
    if shape is None:
        raise PublicationError(
            f"Output {getattr(source, 'Name', '<object>')} has no Shape to publish."
        )
    target = publication_target(published, root)
    relative = placement_relative_to(root, source)
    # Candidate BREP is already imported and validated off-thread.  Assign the
    # detached TopoShape directly so publication does not make a second deep
    # geometry copy on FreeCAD's document/UI thread.
    target.Shape = shape
    if relative is not None and hasattr(target, "Placement"):
        target.Placement = relative
    tag_object(
        target,
        role=ROLE_PUBLICATION_TARGET,
        engine=str(getattr(published, PROP_ENGINE, "") or ""),
        model_id=str(getattr(published, PROP_MODEL_ID, "") or ""),
        output_key=str(getattr(published, PROP_OUTPUT_KEY, "") or ""),
        revision=revision,
    )
    published.LinkedObject = (root, f"{target.Name}.")
    published.LinkTransform = True
    ensure_string_property(published, PROP_REVISION)
    setattr(published, PROP_REVISION, str(revision or ""))
    ensure_string_property(published, PROP_IMPLEMENTATION)
    setattr(
        published,
        PROP_IMPLEMENTATION,
        target.Name,
    )
    _copy_presentation(source, published)


def publication_target(published: Any, root: Any | None = None) -> Any:
    owner = root if root is not None else model_root_for(published)
    target_name = str(getattr(published, PROP_IMPLEMENTATION, "") or "")
    doc = getattr(owner, "Document", None)
    target = doc.getObject(target_name) if doc is not None and target_name else None
    if target is None or role_of(target) != ROLE_PUBLICATION_TARGET:
        raise PublicationError(
            "A scripted publication has no valid private shape target.",
            details={
                "model_root": str(getattr(owner, "Name", "") or ""),
                "published_object": str(getattr(published, "Name", "") or ""),
                "target": target_name,
            },
        )
    owned = {id(item) for item in list(getattr(owner, "OutListRecursive", []) or [])}
    if id(target) not in owned:
        raise PublicationError(
            "A scripted publication target is outside its model root.",
            details={
                "model_root": owner.Name,
                "published_object": published.Name,
                "target": target.Name,
            },
        )
    return target


def delete_publication(doc: Any, root: Any, published: Any) -> list[str]:
    target = publication_target(published, root)
    deleted: list[str] = []
    for obj in (published, target):
        name = str(getattr(obj, "Name", "") or "")
        if name and doc.getObject(name) is not None:
            doc.removeObject(name)
            deleted.append(name)
    return deleted


def implementation_closure(root: Any) -> list[Any]:
    roots = model_implementations(root)
    result: dict[str, Any] = {}
    for implementation in roots:
        name = str(getattr(implementation, "Name", "") or "")
        if name:
            result[name] = implementation
        for child in list(getattr(implementation, "OutListRecursive", []) or []):
            child_name = str(getattr(child, "Name", "") or "")
            if child_name:
                result[child_name] = child
    return list(result.values())


def external_reference_uses(
    doc: Any,
    targets: list[Any],
    *,
    internal_objects: list[Any] | None = None,
) -> list[dict[str, Any]]:
    target_by_id = {id(item): item for item in targets}
    target_ids = set(target_by_id)
    internal_ids = {id(item) for item in list(internal_objects or [])}
    uses: list[dict[str, Any]] = []
    owners: dict[int, Any] = {}
    for target in targets:
        for owner in list(getattr(target, "InList", []) or []):
            owners[id(owner)] = owner
    for owner in owners.values():
        if id(owner) in target_ids or id(owner) in internal_ids:
            continue
        for property_name in list(getattr(owner, "PropertiesList", []) or []):
            property_type = _property_type(owner, property_name)
            if property_type not in (
                _LINK_PROPERTY_TYPES
                | _LINK_LIST_PROPERTY_TYPES
                | _LINK_SUB_PROPERTY_TYPES
                | _LINK_SUB_LIST_PROPERTY_TYPES
            ):
                continue
            try:
                value = getattr(owner, property_name)
            except Exception as exc:
                raise PublicationError(
                    f"Could not inspect reference property {owner.Name}.{property_name}.",
                    details={
                        "owner": str(getattr(owner, "Name", "") or ""),
                        "property": property_name,
                        "property_type": property_type,
                        "native_error": str(exc),
                    },
                ) from exc
            matches = _references_in_value(value, property_type, target_ids)
            for target_id, subelements in matches:
                uses.append(
                    {
                        "owner": owner,
                        "owner_name": str(getattr(owner, "Name", "") or ""),
                        "owner_type": str(getattr(owner, "TypeId", "") or ""),
                        "property": property_name,
                        "property_type": property_type,
                        "subelements": subelements,
                        "target_name": str(
                            getattr(target_by_id[target_id], "Name", "") or ""
                        ),
                        "_target_id": target_id,
                    }
                )
    known_pairs = {
        (id(item["owner"]), int(item["_target_id"]))
        for item in uses
        if item.get("_target_id") is not None
    }
    for target in targets:
        for owner in list(getattr(target, "InList", []) or []):
            if (
                id(owner) in target_ids
                or id(owner) in internal_ids
                or (id(owner), id(target)) in known_pairs
            ):
                continue
            uses.append(
                {
                    "owner": owner,
                    "owner_name": str(getattr(owner, "Name", "") or ""),
                    "owner_type": str(getattr(owner, "TypeId", "") or ""),
                    "property": "<native_inbound_reference>",
                    "property_type": "unknown",
                    "subelements": ["<unclassified>"],
                }
            )
    return uses


def json_reference_uses(uses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_json_use(item) for item in uses]


def _property_type(owner: Any, property_name: str) -> str:
    getter = getattr(owner, "getTypeIdOfProperty", None)
    if not callable(getter):
        return ""
    try:
        return str(getter(property_name) or "")
    except Exception as exc:
        raise PublicationError(
            f"Could not inspect the type of reference property "
            f"{getattr(owner, 'Name', '<object>')}.{property_name}.",
            details={
                "owner": str(getattr(owner, "Name", "") or ""),
                "property": property_name,
                "native_error": str(exc),
            },
        ) from exc


def _references_in_value(
    value: Any, property_type: str, target_ids: set[int]
) -> list[tuple[int, list[str]]]:
    matches: list[tuple[int, list[str]]] = []
    if property_type in _LINK_PROPERTY_TYPES:
        if id(value) in target_ids:
            matches.append((id(value), []))
    elif property_type in _LINK_LIST_PROPERTY_TYPES:
        for item in list(value or []):
            if id(item) in target_ids:
                matches.append((id(item), []))
    elif property_type in _LINK_SUB_PROPERTY_TYPES:
        if isinstance(value, (tuple, list)) and value and id(value[0]) in target_ids:
            matches.append(
                (
                    id(value[0]),
                    _subelement_names(value[1] if len(value) > 1 else []),
                )
            )
    elif property_type in _LINK_SUB_LIST_PROPERTY_TYPES:
        for item in list(value or []):
            if isinstance(item, (tuple, list)) and item and id(item[0]) in target_ids:
                matches.append(
                    (
                        id(item[0]),
                        _subelement_names(item[1] if len(item) > 1 else []),
                    )
                )
    return matches


def _subelement_names(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    return [str(item) for item in list(value or []) if str(item)]


def _json_use(use: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in use.items()
        if key not in {"owner", "_target_id"}
    }


def _copy_presentation(source: Any, target: Any) -> None:
    if hasattr(source, "ShapeMaterial") and hasattr(target, "ShapeMaterial"):
        try:
            target.ShapeMaterial = source.ShapeMaterial
        except Exception as exc:
            raise PublicationError(
                f"Could not copy ShapeMaterial from "
                f"{getattr(source, 'Name', '<object>')} to "
                f"{getattr(target, 'Name', '<object>')}.",
                details={"native_error": str(exc)},
            ) from exc
    source_view = getattr(source, "ViewObject", None)
    target_view = getattr(target, "ViewObject", None)
    if source_view is None or target_view is None:
        return
    for name in (
        "ShapeColor",
        "LineColor",
        "PointColor",
        "Transparency",
        "DisplayMode",
        "LineWidth",
        "PointSize",
    ):
        if not hasattr(source_view, name) or not hasattr(target_view, name):
            continue
        try:
            setattr(target_view, name, getattr(source_view, name))
        except Exception as exc:
            raise PublicationError(
                f"Could not copy view property {name!r} from "
                f"{getattr(source, 'Name', '<object>')} to "
                f"{getattr(target, 'Name', '<object>')}.",
                details={"property": name, "native_error": str(exc)},
            ) from exc
    if hasattr(target_view, "Visibility"):
        target_view.Visibility = True
