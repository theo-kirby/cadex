# SPDX-License-Identifier: LGPL-2.1-or-later

"""Import a CAD file from the local filesystem into the active document."""

from __future__ import annotations

from typing import Any

from CadexTools import tool_failure
from CadexTransactions import run_freecad_transaction

from . import domain_runtime
from . import file_io_runtime


TOOL_SPEC = {
    "name": "file.import_model",
    "description": (
        "Import a CAD file from an absolute local filesystem path into the "
        "active document as an independent copy. Supported formats: FreeCAD "
        "projects (.FCStd, merged as copies of their objects), STEP "
        "(.step/.stp), IGES (.iges/.igs), BREP (.brep/.brp), and triangle "
        "meshes (.stl/.obj/.ply). A bare path without an extension resolves "
        "when exactly one supported file in that directory matches the name. "
        "Imported copies do not follow later changes to the source file; use "
        "file.link_external_part for a live reference to a part in another "
        "FreeCAD project."
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
                    "Absolute path to the source file, e.g. "
                    "/Users/me/parts/bracket.step."
                ),
            },
        },
        "required": ["file_path"],
        "additionalProperties": False,
    },
}


def run(service: Any, file_path: str) -> dict[str, Any]:
    doc = service._active_document()
    if doc is None:
        return tool_failure(
            TOOL_SPEC["name"],
            "NO_ACTIVE_DOCUMENT",
            "precondition",
            "No active document.",
            requested={"file_path": file_path},
        )
    resolved = file_io_runtime.resolve_source_path(file_path)
    if not resolved.get("ok"):
        return tool_failure(
            TOOL_SPEC["name"],
            str(resolved.get("reason") or "INVALID_PATH"),
            "precondition",
            str(resolved.get("message") or "Invalid file path."),
            requested={"file_path": file_path},
            candidates=resolved.get("candidates") or [],
            allowed_extensions=resolved.get("allowed_extensions")
            or list(file_io_runtime.IMPORT_EXTENSIONS),
        )
    path = resolved["path"]
    kind = file_io_runtime.classify_extension(path)
    before_names = {obj.Name for obj in list(getattr(doc, "Objects", []) or [])}

    def do_import() -> dict[str, Any]:
        import FreeCAD as App

        active = App.ActiveDocument
        if active is None:
            raise RuntimeError("No active document.")
        if kind == file_io_runtime.KIND_PROJECT:
            active.mergeProject(str(path))
        elif kind == file_io_runtime.KIND_MESH:
            import Mesh

            Mesh.insert(str(path), active.Name)
        elif path.suffix.lower() in file_io_runtime.BREP_EXTENSIONS:
            import Part

            Part.insert(str(path), active.Name)
        else:
            import Import

            Import.insert(str(path), active.Name)
        active.recompute()
        new_objects = [
            obj
            for obj in list(getattr(active, "Objects", []) or [])
            if obj.Name not in before_names
        ]
        return {
            "operation": "import_model",
            "document": active.Name,
            "source_file": str(path),
            "format": path.suffix.lower(),
            "import_kind": kind,
            "imported_object_count": len(new_objects),
            "imported_objects": [
                service._document_object_summary(obj) for obj in new_objects[:60]
            ],
        }

    def verify(result: dict[str, Any]) -> dict[str, Any]:
        count = int(result.get("imported_object_count") or 0)
        return {
            "ok": count > 0,
            "checks": [
                {"name": "objects_created", "ok": count > 0, "actual": count},
            ],
            "error": (
                None
                if count > 0
                else f"Importing {path.name} created no document objects."
            ),
        }

    transaction = run_freecad_transaction(
        f"Import file: {path.name}",
        do_import,
        verifier=verify,
    )
    mutation = transaction.get("result") if isinstance(transaction.get("result"), dict) else {}
    return domain_runtime.build_mutation_result(
        transaction,
        extra={
            "operation": "import_model",
            "source_file": str(path),
            "resolved_from": resolved.get("resolved_from"),
            "mutation": mutation,
        },
        next_action=(
            "Verify geometry with part.measure or a screenshot, then use the "
            "returned exact internal names for assembly.insert_component, "
            "booleans, or further modeling."
        ),
    )
