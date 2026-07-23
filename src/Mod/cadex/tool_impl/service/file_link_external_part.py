# SPDX-License-Identifier: LGPL-2.1-or-later

"""Link an object from another FreeCAD project file into the active document."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from CadexTools import tool_failure
from CadexTransactions import run_freecad_transaction

from . import domain_runtime
from . import file_io_runtime


TOOL_SPEC = {
    "name": "file.link_external_part",
    "description": (
        "Create a live App::Link in the active document to one object inside "
        "another FreeCAD project (.FCStd) file on the local filesystem. The "
        "source file stays authoritative: reopening the document after the "
        "source changes updates the link. The active document must already "
        "be saved to a .FCStd file (FreeCAD records the reference relative "
        "to it). The source project is opened hidden and must remain "
        "available at its path; the user should save the active document "
        "again afterward to persist the external reference. Use "
        "file.import_model instead for an independent frozen copy. When the "
        "object name does not match, the failure lists linkable candidates "
        "from the source file."
    ),
    "contextual": True,
    "safety": "SAFE_WRITE",
    "edit_modes": ["none"],
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "minLength": 1,
                "description": (
                    "Absolute path to the source FreeCAD project, e.g. "
                    "/Users/me/parts/chassis.FCStd."
                ),
            },
            "object_name": {
                "type": "string",
                "minLength": 1,
                "description": (
                    "Exact internal Name, or unique Label, of the object "
                    "inside the source project to link."
                ),
            },
            "label": {
                "type": "string",
                "minLength": 1,
                "description": (
                    "Visible label for the new link occurrence, e.g. 'Chassis'."
                ),
            },
            "local_position": domain_runtime.vector_schema(
                "Initial position of the link in the active document in mm. "
                "Use {x:0,y:0,z:0} when unsure."
            ),
        },
        "required": ["file_path", "object_name", "label", "local_position"],
        "additionalProperties": False,
    },
}


LINKABLE_CONTAINER_TYPES = (
    "PartDesign::Body",
    "App::Part",
)

# Origin datums carry shapes but are internal scaffolding, never parts.
NON_LINKABLE_TYPES = (
    "App::Origin",
    "App::LocalCoordinateSystem",
    "App::Line",
    "App::Plane",
    "App::Point",
    "PartDesign::CoordinateSystem",
)


def run(
    service: Any,
    file_path: str,
    object_name: str,
    label: str,
    local_position: dict[str, Any],
) -> dict[str, Any]:
    clean_label = str(label or "").strip()
    if not clean_label:
        return _precondition_failure("EMPTY_LABEL", "label is required.", file_path)
    doc = service._active_document()
    if doc is None:
        return _precondition_failure("NO_ACTIVE_DOCUMENT", "No active document.", file_path)
    resolved = file_io_runtime.resolve_source_path(
        file_path, allowed_extensions=file_io_runtime.PROJECT_EXTENSIONS
    )
    if not resolved.get("ok"):
        return _precondition_failure(
            str(resolved.get("reason") or "INVALID_PATH"),
            str(resolved.get("message") or "Invalid file path."),
            file_path,
            candidates=resolved.get("candidates") or [],
        )
    path: Path = resolved["path"]
    own_file = str(getattr(doc, "FileName", "") or "")
    if not own_file:
        return _precondition_failure(
            "DOCUMENT_NOT_SAVED",
            "External links record a reference to the source file, so "
            "FreeCAD requires the active document to be saved to a .FCStd "
            "file first. Ask the user to save the document, then retry.",
            file_path,
        )
    if _same_file(Path(own_file), path):
        return _precondition_failure(
            "SELF_LINK",
            "The source file is the active document itself; the object is "
            "already available directly.",
            file_path,
        )
    try:
        source_doc = _find_or_open_source(doc, path)
    except Exception as exc:
        return _precondition_failure(
            "SOURCE_OPEN_FAILED",
            f"FreeCAD could not open the source project: {exc}",
            file_path,
        )
    clean_name = str(object_name or "").strip()
    target = source_doc.getObject(clean_name) if clean_name else None
    if target is None:
        by_label = [
            obj
            for obj in list(getattr(source_doc, "Objects", []) or [])
            if obj.Label == clean_name
        ]
        if len(by_label) == 1:
            target = by_label[0]
    if target is None or not _linkable(target):
        return _precondition_failure(
            "LINK_TARGET_NOT_FOUND" if target is None else "LINK_TARGET_NOT_LINKABLE",
            (
                f"No linkable object matches {object_name!r} in {path.name}."
                if target is None
                else f"Object {target.Name} in {path.name} has no linkable geometry."
            ),
            file_path,
            source_document=source_doc.Name,
            candidates=_linkable_candidates(source_doc),
        )
    target_name = target.Name
    source_doc_name = source_doc.Name

    def create() -> dict[str, Any]:
        import FreeCAD as App

        active = App.getDocument(doc.Name)
        base = App.getDocument(source_doc_name).getObject(target_name)
        if active is None or base is None:
            raise RuntimeError("The active document or source object no longer exists.")
        link = active.addObject("App::Link", base.Name)
        if link is None:
            raise RuntimeError("FreeCAD did not create the App::Link.")
        link.LinkedObject = base
        link.Label = clean_label
        link.Placement = App.Placement(
            domain_runtime.parse_vector(local_position), App.Rotation()
        )
        active.recompute()
        linked = getattr(link, "LinkedObject", None)
        shape = getattr(link, "Shape", None)
        return {
            "document": active.Name,
            "link": link.Name,
            "link_label": link.Label,
            "linked_object": getattr(linked, "Name", None),
            "linked_document": getattr(getattr(linked, "Document", None), "Name", None),
            "source_file": str(path),
            "link_has_shape": shape is not None and not bool(shape.isNull()),
            "placement": domain_runtime.placement_summary(link),
        }

    def verify(result: dict[str, Any]) -> dict[str, Any]:
        checks = [
            {
                "name": "link_target",
                "ok": result.get("linked_object") == target_name,
                "expected": target_name,
                "actual": result.get("linked_object"),
            },
            {
                "name": "link_target_document",
                "ok": result.get("linked_document") == source_doc_name,
                "expected": source_doc_name,
                "actual": result.get("linked_document"),
            },
        ]
        return {"ok": all(check["ok"] for check in checks), "checks": checks}

    transaction = run_freecad_transaction(
        f"Link external part: {clean_label}",
        create,
        verifier=verify,
    )
    mutation = transaction.get("result") if isinstance(transaction.get("result"), dict) else {}
    return domain_runtime.build_mutation_result(
        transaction,
        extra={
            "operation": "link_external_part",
            "source_file": str(path),
            "source_document": source_doc_name,
            "mutation": mutation,
        },
        next_action=(
            "Ask the user to save the document to persist the external "
            "reference. Use the returned link name with "
            "assembly.insert_component to place occurrences in an assembly, "
            "or position it directly."
        ),
    )


def _find_or_open_source(active_doc: Any, path: Path) -> Any:
    import FreeCAD as App

    for existing in list(App.listDocuments().values()):
        file_name = str(getattr(existing, "FileName", "") or "")
        if file_name and _same_file(Path(file_name), path):
            return existing
    opened = App.openDocument(str(path), hidden=True)
    current = getattr(App, "ActiveDocument", None)
    if current is not None and current.Name != active_doc.Name:
        App.setActiveDocument(active_doc.Name)
    return opened


def _same_file(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return str(left) == str(right)


def _linkable(obj: Any) -> bool:
    type_id = str(getattr(obj, "TypeId", ""))
    if type_id in NON_LINKABLE_TYPES:
        return False
    if _owned_by_partdesign_body(obj):
        return False
    if type_id in LINKABLE_CONTAINER_TYPES:
        return True
    if obj.isDerivedFrom("Assembly::AssemblyObject") or obj.isDerivedFrom("App::Part"):
        return True
    if obj.isDerivedFrom("Mesh::Feature"):
        return True
    shape = getattr(obj, "Shape", None)
    return shape is not None and not bool(shape.isNull())


def _owned_by_partdesign_body(obj: Any) -> bool:
    """True for sketches and features inside a Body; the Body is the part."""
    for parent in list(getattr(obj, "InList", []) or []):
        if str(getattr(parent, "TypeId", "")) != "PartDesign::Body":
            continue
        if obj in list(getattr(parent, "Group", []) or []):
            return True
    return False


def _linkable_candidates(source_doc: Any) -> list[dict[str, Any]]:
    candidates = []
    for obj in list(getattr(source_doc, "Objects", []) or []):
        if _linkable(obj):
            candidates.append(
                {"name": obj.Name, "label": obj.Label, "type": obj.TypeId}
            )
    return candidates[:40]


def _precondition_failure(
    code: str,
    message: str,
    file_path: Any,
    **details: Any,
) -> dict[str, Any]:
    return tool_failure(
        TOOL_SPEC["name"],
        code,
        "precondition",
        message,
        requested={"file_path": file_path},
        **details,
    )
