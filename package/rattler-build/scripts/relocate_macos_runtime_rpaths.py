#!/usr/bin/env python3
"""Relocate non-system RPATHs in embedded macOS runtimes."""

from __future__ import annotations

import argparse
import os
from pathlib import Path, PurePosixPath
import subprocess

from macos_macho import dylib_dependencies, load_command_paths, otool


SYSTEM_PREFIXES = (
    Path("/System/Library"),
    Path("/usr/lib"),
    Path("/Library/Apple/System/Library"),
)
MACHO_SUFFIXES = {".dylib", ".so", ".bundle"}


def _normalized(path: Path) -> Path:
    return Path(os.path.abspath(os.path.expanduser(str(path))))


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _is_non_system_absolute(path: str) -> bool:
    if not os.path.isabs(path):
        return False
    normalized = _normalized(Path(path))
    return not any(_is_relative_to(normalized, prefix) for prefix in SYSTEM_PREFIXES)


def _candidate(file_path: Path) -> bool:
    return file_path.suffix in MACHO_SUFFIXES or os.access(file_path, os.X_OK)


def _run(arguments: list[str], file_path: Path) -> None:
    subprocess.run([*arguments, str(file_path)], check=True, text=True)


def _dependency_suffix(dependency: str, *, file_path: Path) -> PurePosixPath:
    relative = dependency.removeprefix("@rpath/")
    suffix = PurePosixPath(relative)
    if not relative or suffix.is_absolute() or ".." in suffix.parts:
        raise RuntimeError(
            f"{file_path}: invalid @rpath dependency cannot be relocated: {dependency}"
        )
    return suffix


def _dependency_base(
    dependency: str,
    *,
    file_path: Path,
    runtime_root: Path,
) -> Path:
    suffix = _dependency_suffix(dependency, file_path=file_path)
    matches: set[Path] = set()
    for candidate in runtime_root.rglob(suffix.name):
        if not candidate.is_file():
            continue
        if tuple(candidate.parts[-len(suffix.parts) :]) != suffix.parts:
            continue
        resolved = candidate.resolve()
        if not _is_relative_to(resolved, runtime_root.resolve()):
            raise RuntimeError(
                f"{file_path}: @rpath dependency escapes its runtime through a "
                f"symbolic link: {dependency} -> {resolved}"
            )
        base = candidate
        for _ in suffix.parts:
            base = base.parent
        matches.add(_normalized(base))

    if len(matches) != 1:
        rendered = sorted(str(path) for path in matches)
        raise RuntimeError(
            f"{file_path}: expected one bundled target base for {dependency}; "
            f"found {len(matches)}: {rendered}"
        )
    return matches.pop()


def _loader_rpath(
    dependencies: list[str],
    *,
    file_path: Path,
    runtime_root: Path,
) -> str:
    bases = {
        _dependency_base(
            dependency,
            file_path=file_path,
            runtime_root=runtime_root,
        )
        for dependency in dependencies
    }
    if len(bases) != 1:
        raise RuntimeError(
            f"{file_path}: @rpath dependencies require different bundled bases: "
            f"{sorted(str(path) for path in bases)}"
        )
    base = bases.pop()
    relative = os.path.relpath(base, start=file_path.parent)
    if relative == ".":
        return "@loader_path"
    return f"@loader_path/{Path(relative).as_posix()}"


def _rpaths(load_output: str) -> list[str]:
    return [
        value
        for command, value in load_command_paths(load_output)
        if command == "LC_RPATH"
    ]


def _sanitize_file(
    file_path: Path,
    *,
    runtime_root: Path,
    scan_only: bool,
) -> int:
    load_output = otool(file_path, "-l")
    if load_output is None:
        return 0
    external_rpaths = sorted(
        {path for path in _rpaths(load_output) if _is_non_system_absolute(path)}
    )
    if not external_rpaths:
        return 0

    rpath_dependencies = sorted(
        {
            dependency
            for dependency in dylib_dependencies(load_output)
            if dependency.startswith("@rpath/")
        }
    )
    replacement = (
        _loader_rpath(
            rpath_dependencies,
            file_path=file_path,
            runtime_root=runtime_root,
        )
        if rpath_dependencies
        else None
    )

    current_rpaths = set(_rpaths(load_output))
    operations: list[list[str]] = []
    pending = list(external_rpaths)
    if replacement is not None and replacement not in current_rpaths:
        original = pending.pop(0)
        operations.append(["install_name_tool", "-rpath", original, replacement])
        print(f"{file_path}: replace RPATH {original} -> {replacement}", flush=True)
    for rpath in pending:
        operations.append(["install_name_tool", "-delete_rpath", rpath])
        print(f"{file_path}: delete unused RPATH {rpath}", flush=True)

    if scan_only:
        return len(operations)

    for operation in operations:
        _run(operation, file_path)
    _run(["codesign", "--force", "--sign", "-"], file_path)

    updated_output = otool(file_path, "-l")
    if updated_output is None:
        raise RuntimeError(f"Modified file is no longer recognized as Mach-O: {file_path}")
    remaining_external = sorted(
        {path for path in _rpaths(updated_output) if _is_non_system_absolute(path)}
    )
    if remaining_external:
        raise RuntimeError(
            f"Non-system RPATH relocation did not persist for {file_path}: "
            f"{remaining_external}"
        )
    if replacement is not None and replacement not in _rpaths(updated_output):
        raise RuntimeError(
            f"Required loader-relative RPATH is missing after relocating {file_path}: "
            f"{replacement}"
        )
    updated_dependencies = sorted(
        {
            dependency
            for dependency in dylib_dependencies(updated_output)
            if dependency.startswith("@rpath/")
        }
    )
    if updated_dependencies != rpath_dependencies:
        raise RuntimeError(
            f"Relocating RPATHs changed dylib dependencies for {file_path}: "
            f"before={rpath_dependencies}, after={updated_dependencies}"
        )
    return len(operations)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runtime_root", type=Path)
    parser.add_argument("--bundle-prefix", required=True, type=Path)
    parser.add_argument("--scan-only", action="store_true")
    arguments = parser.parse_args()

    runtime_root = _normalized(arguments.runtime_root)
    bundle_prefix = _normalized(arguments.bundle_prefix)
    if not runtime_root.is_dir():
        parser.error(f"runtime root does not exist: {runtime_root}")
    if not bundle_prefix.is_dir():
        parser.error(f"bundle prefix does not exist: {bundle_prefix}")
    if not _is_relative_to(runtime_root, bundle_prefix):
        parser.error(f"runtime root is outside bundle prefix: {runtime_root}")

    scanned = 0
    changes = 0
    for file_path in sorted(runtime_root.rglob("*")):
        if not file_path.is_file() or file_path.is_symlink() or not _candidate(file_path):
            continue
        scanned += 1
        changes += _sanitize_file(
            file_path,
            runtime_root=runtime_root,
            scan_only=arguments.scan_only,
        )

    action = "required" if arguments.scan_only else "applied"
    print(
        f"macOS runtime RPATH relocation complete: scanned {scanned} files; "
        f"{changes} load-command changes {action}.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
