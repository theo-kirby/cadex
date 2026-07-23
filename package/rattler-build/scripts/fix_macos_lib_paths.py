#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
from pathlib import Path, PurePosixPath
import subprocess
from typing import Iterable

from macos_macho import dylib_dependency_paths, load_command_paths, otool


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Repair source-prefixed Mach-O identities, dependencies, and RPATHs "
            "in the top-level macOS bundle library directory."
        )
    )
    parser.add_argument("scan_path", type=Path)
    parser.add_argument("--bundle-prefix", required=True, type=Path)
    parser.add_argument("--source-prefix", required=True, type=Path)
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Report required changes without modifying files.",
    )
    return parser.parse_args()


def _normalized(path: Path) -> Path:
    return Path(os.path.abspath(os.path.expanduser(str(path))))


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _run_install_name_tool(arguments: Iterable[str], file_path: Path) -> None:
    subprocess.run(
        ["install_name_tool", *arguments, str(file_path)],
        check=True,
        text=True,
    )


def _sign(file_path: Path) -> None:
    subprocess.run(
        ["codesign", "--force", "--sign", "-", str(file_path)],
        check=True,
        text=True,
    )


def _source_destination(
    path: Path,
    *,
    source_prefix: Path,
    bundle_prefix: Path,
) -> Path | None:
    if not _is_relative_to(path, source_prefix):
        return None
    return bundle_prefix / path.relative_to(source_prefix)


def _loader_reference(target: Path, *, loader_directory: Path) -> str:
    relative = os.path.relpath(target, start=loader_directory)
    if relative == ".":
        return "@loader_path"
    return f"@loader_path/{Path(relative).as_posix()}"


def _append_unique(changes: list[tuple[str, ...]], change: tuple[str, ...]) -> None:
    if change not in changes:
        changes.append(change)


def _verify_loader_rpath_targets(
    dependencies: set[str],
    *,
    file_path: Path,
    bundle_prefix: Path,
) -> None:
    for dependency in sorted(dependencies):
        relative = dependency.removeprefix("@rpath/")
        suffix = PurePosixPath(relative)
        if not relative or suffix.is_absolute() or ".." in suffix.parts:
            raise RuntimeError(
                f"Invalid @rpath dependency in {file_path}: {dependency}"
            )
        target = file_path.parent.joinpath(*suffix.parts)
        if not target.exists():
            raise RuntimeError(
                f"Cannot relocate the RPATH in {file_path}: {dependency} does "
                f"not resolve under @loader_path ({target})."
            )
        if not _is_relative_to(target.resolve(), bundle_prefix.resolve()):
            raise RuntimeError(
                f"RPATH dependency escapes the app bundle in {file_path}: "
                f"{dependency} -> {target.resolve()}"
            )


def _has_loader_directory_rpath(rpaths: list[str]) -> bool:
    return any(value.rstrip("/") == "@loader_path" for value in rpaths)


def _repair_file(
    file_path: Path,
    *,
    bundle_prefix: Path,
    source_prefix: Path,
    scan_only: bool,
) -> int:
    load_output = otool(file_path, "-l")
    if load_output is None:
        return 0
    command_paths = load_command_paths(load_output)
    dependencies = dylib_dependency_paths(load_output)
    rpaths = [value for command, value in command_paths if command == "LC_RPATH"]
    rpath_dependencies = {
        value for _, value in dependencies if value.startswith("@rpath/")
    }
    install_ids = [
        value for command, value in command_paths if command == "LC_ID_DYLIB"
    ]
    changes: list[tuple[str, ...]] = []

    for rpath in rpaths:
        if not os.path.isabs(rpath):
            if rpath.startswith("@"):
                continue
            if rpath_dependencies:
                raise RuntimeError(
                    f"Unsafe relative RPATH in {file_path}: {rpath}. It cannot "
                    f"be removed because the file loads {sorted(rpath_dependencies)}."
                )
            _append_unique(changes, ("-delete_rpath", rpath))
            continue
        resolved = _normalized(Path(rpath))
        relocated = _source_destination(
            resolved,
            source_prefix=source_prefix,
            bundle_prefix=bundle_prefix,
        )
        if relocated is not None:
            if relocated != file_path.parent:
                raise RuntimeError(
                    f"Unsupported source-prefix RPATH in {file_path}: {rpath} "
                    f"would relocate to {relocated}."
                )
            replacement = "@loader_path"
            if rpath_dependencies:
                _verify_loader_rpath_targets(
                    rpath_dependencies,
                    file_path=file_path,
                    bundle_prefix=bundle_prefix,
                )
            if rpath_dependencies and not _has_loader_directory_rpath(rpaths):
                _append_unique(changes, ("-rpath", rpath, replacement))
            else:
                _append_unique(changes, ("-delete_rpath", rpath))
            continue
        if resolved == file_path.parent:
            replacement = "@loader_path"
            if rpath_dependencies:
                _verify_loader_rpath_targets(
                    rpath_dependencies,
                    file_path=file_path,
                    bundle_prefix=bundle_prefix,
                )
            if rpath_dependencies and not _has_loader_directory_rpath(rpaths):
                _append_unique(changes, ("-rpath", rpath, replacement))
            else:
                _append_unique(changes, ("-delete_rpath", rpath))
            continue
        if _is_relative_to(resolved, bundle_prefix):
            raise RuntimeError(
                f"Unsupported absolute bundle RPATH in {file_path}: {rpath}. "
                "The package must use an @loader_path or @rpath-relative entry."
            )
    for install_id in install_ids:
        if not os.path.isabs(install_id):
            continue
        resolved = _normalized(Path(install_id))
        relocated = _source_destination(
            resolved,
            source_prefix=source_prefix,
            bundle_prefix=bundle_prefix,
        )
        bundled_identity = relocated if relocated is not None else resolved
        if not _is_relative_to(bundled_identity, bundle_prefix):
            continue
        if not bundled_identity.exists():
            raise RuntimeError(
                f"Mach-O install identity is missing from the app bundle: "
                f"{install_id} should resolve to {bundled_identity}."
            )
        if bundled_identity.resolve() != file_path.resolve():
            raise RuntimeError(
                f"Mach-O install identity points at a different bundled file: "
                f"{file_path} has {install_id}, which maps to {bundled_identity}."
            )
        _append_unique(changes, ("-id", f"@rpath/{Path(install_id).name}"))

    for _, dependency in dependencies:
        if not os.path.isabs(dependency):
            continue
        resolved = _normalized(Path(dependency))
        relocated = _source_destination(
            resolved,
            source_prefix=source_prefix,
            bundle_prefix=bundle_prefix,
        )
        bundled_library = relocated if relocated is not None else resolved
        if not _is_relative_to(bundled_library, bundle_prefix):
            continue
        if not bundled_library.exists():
            raise RuntimeError(
                f"Mach-O dependency is missing from the app bundle: {dependency} "
                f"should resolve to {bundled_library}."
            )
        replacement = _loader_reference(
            bundled_library,
            loader_directory=file_path.parent,
        )
        _append_unique(changes, ("-change", dependency, replacement))

    if not changes:
        return 0

    for change in changes:
        print(f"{file_path}: install_name_tool {' '.join(change)}", flush=True)
        if not scan_only:
            _run_install_name_tool(change, file_path)
    if not scan_only:
        _sign(file_path)
        updated_output = otool(file_path, "-l")
        if updated_output is None:
            raise RuntimeError(
                f"Modified file is no longer recognized as Mach-O: {file_path}"
            )
        updated_command_paths = load_command_paths(updated_output)
        updated_paths = [value for _, value in updated_command_paths] + [
            value for _, value in dylib_dependency_paths(updated_output)
        ]
        stale_paths = sorted(
            {value for value in updated_paths if str(source_prefix) in value}
        )
        if stale_paths:
            raise RuntimeError(
                f"Source-prefix relocation did not persist for {file_path}: "
                f"{stale_paths}"
            )
        unsafe_relative_rpaths = sorted(
            {
                value
                for command, value in updated_command_paths
                if command == "LC_RPATH"
                and not os.path.isabs(value)
                and not value.startswith("@")
            }
        )
        if unsafe_relative_rpaths:
            raise RuntimeError(
                f"Unsafe relative RPATH removal did not persist for {file_path}: "
                f"{unsafe_relative_rpaths}"
            )
    return len(changes)


def main() -> int:
    arguments = _parse_arguments()
    scan_path = _normalized(arguments.scan_path)
    bundle_prefix = _normalized(arguments.bundle_prefix)
    source_prefix = _normalized(arguments.source_prefix)

    if not scan_path.is_dir():
        raise SystemExit(f"macOS library directory does not exist: {scan_path}")
    if not bundle_prefix.is_dir():
        raise SystemExit(f"macOS bundle prefix does not exist: {bundle_prefix}")
    if not source_prefix.is_dir():
        raise SystemExit(f"Source conda prefix does not exist: {source_prefix}")

    changed = 0
    scanned = 0
    for file_path in sorted(scan_path.iterdir()):
        if not file_path.is_file() or file_path.is_symlink():
            continue
        scanned += 1
        changed += _repair_file(
            file_path,
            bundle_prefix=bundle_prefix,
            source_prefix=source_prefix,
            scan_only=arguments.scan_only,
        )

    action = "required" if arguments.scan_only else "applied"
    print(
        f"macOS top-level library repair complete: scanned {scanned} files; "
        f"{changed} load-command changes {action}.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
