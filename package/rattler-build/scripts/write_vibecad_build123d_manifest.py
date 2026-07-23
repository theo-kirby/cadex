#!/usr/bin/env python3

"""Write a relocatable manifest for the packaged build123d sidecar."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runtime_root", type=Path)
    parser.add_argument("python_prefix", type=Path)
    parser.add_argument("python_executable", type=Path)
    arguments = parser.parse_args()

    runtime_root = arguments.runtime_root.resolve()
    python_prefix = arguments.python_prefix.absolute()
    python_executable = arguments.python_executable.absolute()
    if not python_prefix.is_dir():
        raise SystemExit(f"Python prefix is missing: {python_prefix}")
    if not python_executable.is_file():
        raise SystemExit(f"Python executable is missing: {python_executable}")
    try:
        executable_relative = python_executable.relative_to(python_prefix)
    except ValueError as exc:
        raise SystemExit(
            f"Python executable {python_executable} is outside prefix {python_prefix}."
        ) from exc
    site_packages = runtime_root / "site-packages"
    distribution = site_packages / "build123d-0.11.1.dist-info"
    if not distribution.is_dir():
        raise SystemExit(f"build123d 0.11.1 metadata is missing: {distribution}")
    payload = {
        "schema": "vibecad-build123d-runtime-v1",
        "version": "0.11.1",
        "site_packages": "site-packages",
        "python_prefix": os.path.relpath(python_prefix, runtime_root),
        "python_executable": executable_relative.as_posix(),
    }
    destination = runtime_root / "runtime.json"
    temporary = destination.with_name("runtime.json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
