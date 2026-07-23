#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Record optional dependency coverage that affects UI/style readiness."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


PLACEHOLDER_TEXT = {"todo", "tbd", "n/a", "none", "placeholder"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_config(config: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    dependencies = config.get("dependencies")
    if not isinstance(dependencies, list):
        return [{"kind": "config_shape", "message": "dependencies must be a list"}]

    seen_names: set[str] = set()
    for index, item in enumerate(dependencies):
        if not isinstance(item, dict):
            errors.append({"kind": "dependency_shape", "index": index, "message": "dependency must be an object"})
            continue
        name = str(item.get("name", "")).strip()
        dep_kind = item.get("kind")
        if not name:
            errors.append({"kind": "missing_name", "index": index})
        elif name in seen_names:
            errors.append({"kind": "duplicate_name", "name": name})
        seen_names.add(name)
        if dep_kind not in {"python_module", "executable"}:
            errors.append({"kind": "unsupported_kind", "name": name, "dependency_kind": dep_kind})
        if dep_kind == "python_module" and not str(item.get("module", "")).strip():
            errors.append({"kind": "missing_module", "name": name})
        if dep_kind == "executable" and not str(item.get("executable", "")).strip():
            errors.append({"kind": "missing_executable", "name": name})
        affects = item.get("affects")
        if not isinstance(affects, list) or not affects or not all(str(value).strip() for value in affects):
            errors.append({"kind": "missing_affects", "name": name})
        elif any(str(value).strip().lower() in PLACEHOLDER_TEXT for value in affects):
            errors.append({"kind": "placeholder_affects", "name": name})
        elif len({str(value).strip() for value in affects}) != len(affects):
            errors.append({"kind": "duplicate_affects", "name": name})
    return errors


def python_module_status(spec_item: dict[str, Any]) -> dict[str, Any]:
    module_name = spec_item["module"]
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        return {
            "available": False,
            "reason": f"Python module '{module_name}' is not importable",
            "affects": spec_item.get("affects", []),
        }
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        return {
            "available": False,
            "reason": f"Python module '{module_name}' failed to import: {exc!r}",
            "affects": spec_item.get("affects", []),
        }
    return {
        "available": True,
        "version": getattr(module, "__version__", None),
        "module_file": getattr(module, "__file__", None),
        "affects": spec_item.get("affects", []),
    }


def executable_status(spec_item: dict[str, Any], timeout: int) -> dict[str, Any]:
    executable_name = spec_item["executable"]
    executable = shutil.which(executable_name)
    if not executable:
        return {
            "available": False,
            "reason": f"{spec_item.get('name', executable_name)} executable was not found on PATH",
            "affects": spec_item.get("affects", []),
        }
    try:
        completed = subprocess.run(
            [executable, *(spec_item.get("version_args") or ["--version"])],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "available": False,
            "executable": executable,
            "reason": f"{spec_item.get('name', executable_name)} version check timed out after {timeout}s",
            "affects": spec_item.get("affects", []),
        }
    available = completed.returncode == 0
    return {
        "available": available,
        "executable": executable,
        "returncode": completed.returncode,
        "version_output": completed.stdout.strip(),
        "reason": None if available else f"{spec_item.get('name', executable_name)} executable did not return a successful version check",
        "affects": spec_item.get("affects", []),
    }


def dependency_status(spec_item: dict[str, Any], timeout: int) -> dict[str, Any]:
    kind = spec_item.get("kind")
    if kind == "python_module":
        return python_module_status(spec_item)
    if kind == "executable":
        return executable_status(spec_item, timeout)
    return {
        "available": False,
        "reason": f"Unsupported dependency kind: {kind!r}",
        "affects": spec_item.get("affects", []),
    }


def build_report(timeout: int, config_path: Path) -> dict[str, Any]:
    config = read_json(config_path)
    config_errors = validate_config(config)
    if config_errors:
        return {
            "schema": "freecad-optional-dependency-smoke-v1",
            "config": str(config_path),
            "result": "failed",
            "missing_count": 0,
            "dependencies": {},
            "missing": {},
            "config_errors": config_errors,
        }
    dependencies = {
        item["name"]: dependency_status(item, timeout)
        for item in config.get("dependencies", [])
    }
    missing = {
        name: item
        for name, item in dependencies.items()
        if not item.get("available")
    }
    return {
        "schema": "freecad-optional-dependency-smoke-v1",
        "config": str(config_path),
        "result": "partial" if missing else "ok",
        "missing_count": len(missing),
        "dependencies": dependencies,
        "missing": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().with_name("optional_dependencies.default.json"),
    )
    args = parser.parse_args()

    report = build_report(args.timeout, args.config)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
