# SPDX-License-Identifier: LGPL-2.1-or-later

"""Export named document objects to one file on the local filesystem."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from CadexTools import tool_failure

from . import file_io_runtime


TOOL_SPEC = {
    "name": "file.export_model",
    "description": (
        "Export named document objects to one file at an absolute local "
        "filesystem path. The extension selects the format: STEP "
        "(.step/.stp), IGES (.iges/.igs), or BREP (.brep/.brp) write exact "
        "BREP geometry; STL, OBJ, or PLY write one combined tessellated "
        "mesh. An existing file is only replaced when overwrite is true. "
        "The document itself is never modified."
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
                    "Absolute destination path whose extension selects the "
                    "format, e.g. /Users/me/out/bracket.step."
                ),
            },
            "object_names": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "minItems": 1,
                "description": (
                    "Exact internal names of the document objects to export."
                ),
            },
            "overwrite": {
                "type": "boolean",
                "default": False,
                "description": "Replace the destination file if it already exists.",
            },
            "linear_deflection": {
                "type": "number",
                "exclusiveMinimum": 0,
                "default": 0.1,
                "description": (
                    "Maximum tessellation deviation in mm when meshing BREP "
                    "shapes for STL/OBJ/PLY export; ignored for BREP formats."
                ),
            },
        },
        "required": ["file_path", "object_names"],
        "additionalProperties": False,
    },
}


def run(
    service: Any,
    file_path: str,
    object_names: list[str],
    overwrite: bool = False,
    linear_deflection: float = 0.1,
) -> dict[str, Any]:
    doc = service._active_document()
    if doc is None:
        return tool_failure(
            TOOL_SPEC["name"],
            "NO_ACTIVE_DOCUMENT",
            "precondition",
            "No active document.",
            requested={"file_path": file_path, "object_names": object_names},
        )
    requested_names = [str(name or "").strip() for name in list(object_names or [])]
    targets = []
    missing = []
    for name in requested_names:
        obj = doc.getObject(name) if name else None
        if obj is None:
            missing.append(name)
        else:
            targets.append(obj)
    if missing or not targets:
        return tool_failure(
            TOOL_SPEC["name"],
            "OBJECT_NOT_FOUND",
            "precondition",
            f"Objects not found by exact internal name: {missing or requested_names}",
            requested={"object_names": object_names},
            candidates=[
                service._document_object_summary(item)
                for item in list(getattr(doc, "Objects", []) or [])[:80]
            ],
        )
    resolved = file_io_runtime.resolve_export_path(file_path, overwrite=bool(overwrite))
    if not resolved.get("ok"):
        return tool_failure(
            TOOL_SPEC["name"],
            str(resolved.get("reason") or "INVALID_PATH"),
            "precondition",
            str(resolved.get("message") or "Invalid destination path."),
            requested={"file_path": file_path},
            allowed_extensions=resolved.get("allowed_extensions")
            or list(file_io_runtime.EXPORT_EXTENSIONS),
        )
    path: Path = resolved["path"]
    kind = file_io_runtime.classify_extension(path)
    unshaped = [
        obj
        for obj in targets
        if not _exportable(obj, kind)
    ]
    if unshaped:
        return tool_failure(
            TOOL_SPEC["name"],
            "OBJECT_NOT_EXPORTABLE",
            "precondition",
            "Every exported object needs shape or mesh geometry for this format.",
            requested={"object_names": object_names, "format": path.suffix.lower()},
            rejected_objects=[
                service._document_object_summary(obj) for obj in unshaped
            ],
        )
    try:
        if kind == file_io_runtime.KIND_MESH:
            _export_mesh(targets, path, float(linear_deflection))
        elif path.suffix.lower() in file_io_runtime.BREP_EXTENSIONS:
            import Part

            Part.export(targets, str(path))
        else:
            import Import

            Import.export(targets, str(path))
    except Exception as exc:
        return tool_failure(
            TOOL_SPEC["name"],
            "EXPORT_FAILED",
            "mutation",
            f"FreeCAD export raised: {exc}",
            requested={"file_path": str(path), "object_names": requested_names},
        )
    size = path.stat().st_size if path.is_file() else 0
    if size <= 0:
        return tool_failure(
            TOOL_SPEC["name"],
            "EXPORT_EMPTY",
            "postcondition",
            f"Export produced no file content at {path}.",
            requested={"file_path": str(path), "object_names": requested_names},
        )
    return {
        "ok": True,
        "operation": "export_model",
        "file": {"path": str(path), "size_bytes": size},
        "format": path.suffix.lower(),
        "export_kind": kind,
        "exported_objects": [
            service._document_object_summary(obj) for obj in targets
        ],
        "document_modified": False,
        "next_action": (
            "Report the written file path to the user; the active document "
            "was not changed."
        ),
    }


def _exportable(obj: Any, kind: str | None) -> bool:
    if obj.isDerivedFrom("Mesh::Feature"):
        return kind == file_io_runtime.KIND_MESH
    shape = _resolved_shape(obj)
    return shape is not None and not bool(shape.isNull())


def _resolved_shape(obj: Any) -> Any:
    """Overall shape of an object, resolving containers and links.

    ``Part.getShape`` flattens App::Part, App::Link, and group hierarchies
    into one compound, which plain ``obj.Shape`` does not."""
    import Part

    try:
        return Part.getShape(obj)
    except Exception:
        return getattr(obj, "Shape", None)


def _export_mesh(targets: list[Any], path: Path, linear_deflection: float) -> None:
    import Mesh
    import MeshPart

    combined = Mesh.Mesh()
    for obj in targets:
        if obj.isDerivedFrom("Mesh::Feature"):
            combined.addMesh(obj.Mesh)
            continue
        combined.addMesh(
            MeshPart.meshFromShape(
                Shape=_resolved_shape(obj),
                LinearDeflection=linear_deflection,
                AngularDeflection=0.5235987755982988,
                Relative=False,
            )
        )
    combined.write(str(path))
