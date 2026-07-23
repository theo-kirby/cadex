"""Strict parsers for the macOS toolchain output used by bundle scripts."""

from __future__ import annotations

from pathlib import Path
import subprocess


DYLIB_DEPENDENCY_COMMANDS = frozenset(
    {
        "LC_LAZY_LOAD_DYLIB",
        "LC_LOAD_DYLIB",
        "LC_LOAD_UPWARD_DYLIB",
        "LC_LOAD_WEAK_DYLIB",
        "LC_REEXPORT_DYLIB",
    }
)


def otool(file_path: Path, option: str) -> str | None:
    result = subprocess.run(
        ["otool", option, str(file_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout
    diagnostic = f"{result.stdout}\n{result.stderr}"
    if "is not an object file" in diagnostic or "The file was not recognized" in diagnostic:
        return None
    raise RuntimeError(
        f"otool {option} failed for {file_path} with status {result.returncode}:\n"
        f"{diagnostic.strip()}"
    )


def load_command_paths(output: str) -> list[tuple[str, str]]:
    paths: list[tuple[str, str]] = []
    command = ""
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if line.startswith("cmd "):
            command = line.removeprefix("cmd ")
            continue
        if command == "LC_RPATH" and line.startswith("path "):
            paths.append(
                (command, line.removeprefix("path ").split(" (offset", 1)[0])
            )
            command = ""
        elif command == "LC_ID_DYLIB" and line.startswith("name "):
            paths.append(
                (command, line.removeprefix("name ").split(" (offset", 1)[0])
            )
            command = ""
    return paths


def dylib_dependency_paths(output: str) -> list[tuple[str, str]]:
    dependencies: list[tuple[str, str]] = []
    command = ""
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if line.startswith("cmd "):
            command = line.removeprefix("cmd ")
            continue
        if command in DYLIB_DEPENDENCY_COMMANDS and line.startswith("name "):
            dependencies.append(
                (
                    command,
                    line.removeprefix("name ").split(" (offset", 1)[0],
                )
            )
            command = ""
    return dependencies


def dylib_dependencies(output: str) -> list[str]:
    return [path for _, path in dylib_dependency_paths(output)]
