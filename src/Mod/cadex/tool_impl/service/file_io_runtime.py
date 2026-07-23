# SPDX-License-Identifier: LGPL-2.1-or-later

"""Shared path and format resolution for the ``file.*`` import/export tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

PROJECT_EXTENSIONS = (".fcstd",)
SOLID_EXTENSIONS = (".step", ".stp", ".iges", ".igs", ".brep", ".brp")
BREP_EXTENSIONS = (".brep", ".brp")
MESH_EXTENSIONS = (".stl", ".obj", ".ply")

IMPORT_EXTENSIONS = PROJECT_EXTENSIONS + SOLID_EXTENSIONS + MESH_EXTENSIONS
EXPORT_EXTENSIONS = SOLID_EXTENSIONS + MESH_EXTENSIONS

KIND_PROJECT = "project"
KIND_SOLID = "solid"
KIND_MESH = "mesh"

CANDIDATE_LIMIT = 20


def classify_extension(path: Path) -> str | None:
    """Map a file extension to its import/export pipeline kind."""
    suffix = path.suffix.lower()
    if suffix in PROJECT_EXTENSIONS:
        return KIND_PROJECT
    if suffix in SOLID_EXTENSIONS:
        return KIND_SOLID
    if suffix in MESH_EXTENSIONS:
        return KIND_MESH
    return None


def resolve_source_path(
    raw: Any,
    allowed_extensions: tuple[str, ...] = IMPORT_EXTENSIONS,
) -> dict[str, Any]:
    """Resolve one user-supplied path to an existing readable source file.

    A bare path without an extension resolves when exactly one file in the
    same directory shares the stem and carries an allowed extension
    (``/parts/chassis-v10`` resolves to ``/parts/chassis-v10.FCStd``).
    Extension matching is case-insensitive.
    """
    clean = str(raw or "").strip()
    if not clean:
        return _fail("EMPTY_PATH", "file_path is required.")
    path = Path(clean).expanduser()
    if not path.is_absolute():
        return _fail(
            "RELATIVE_PATH",
            f"file_path must be an absolute path, got: {clean}",
        )
    allowed = tuple(ext.lower() for ext in allowed_extensions)
    if path.is_file():
        if path.suffix.lower() in allowed:
            return {"ok": True, "path": path}
        return _fail(
            "UNSUPPORTED_EXTENSION",
            f"Unsupported file extension {path.suffix!r} for {path.name}.",
            allowed_extensions=list(allowed),
        )
    parent = path.parent
    if not parent.is_dir():
        return _fail(
            "NO_SUCH_DIRECTORY",
            f"Directory does not exist: {parent}",
        )
    siblings = sorted(
        item
        for item in parent.iterdir()
        if item.is_file() and item.suffix.lower() in allowed
    )
    matches = [
        item
        for item in siblings
        if item.stem == path.name or item.name.lower() == path.name.lower()
    ]
    if len(matches) == 1:
        return {"ok": True, "path": matches[0], "resolved_from": clean}
    if len(matches) > 1:
        return _fail(
            "AMBIGUOUS_PATH",
            f"Multiple supported files match {path.name!r}; pass the full file name.",
            candidates=[str(item) for item in matches[:CANDIDATE_LIMIT]],
        )
    return _fail(
        "FILE_NOT_FOUND",
        f"File not found: {clean}",
        candidates=[str(item) for item in siblings[:CANDIDATE_LIMIT]],
    )


def resolve_export_path(
    raw: Any,
    *,
    overwrite: bool,
    allowed_extensions: tuple[str, ...] = EXPORT_EXTENSIONS,
) -> dict[str, Any]:
    """Validate one user-supplied destination path for an export write."""
    clean = str(raw or "").strip()
    if not clean:
        return _fail("EMPTY_PATH", "file_path is required.")
    path = Path(clean).expanduser()
    if not path.is_absolute():
        return _fail(
            "RELATIVE_PATH",
            f"file_path must be an absolute path, got: {clean}",
        )
    allowed = tuple(ext.lower() for ext in allowed_extensions)
    if path.suffix.lower() not in allowed:
        return _fail(
            "UNSUPPORTED_EXTENSION",
            f"Unsupported export extension {path.suffix!r}; the extension selects the format.",
            allowed_extensions=list(allowed),
        )
    if not path.parent.is_dir():
        return _fail(
            "NO_SUCH_DIRECTORY",
            f"Destination directory does not exist: {path.parent}",
        )
    if path.exists():
        if path.is_dir():
            return _fail("IS_DIRECTORY", f"Destination is a directory: {path}")
        if not overwrite:
            return _fail(
                "FILE_EXISTS",
                f"File already exists: {path}. Pass overwrite=true to replace it.",
            )
    return {"ok": True, "path": path}


def _fail(reason: str, message: str, **details: Any) -> dict[str, Any]:
    return {"ok": False, "reason": reason, "message": message, **details}
