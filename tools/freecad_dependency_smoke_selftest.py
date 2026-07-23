#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Self-test optional dependency smoke configuration behavior."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import freecad_dependency_smoke


SCHEMA = "freecad-optional-dependency-smoke-selftest-v1"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/freecad-test-results/freecad-dependency-smoke-selftest.json"))
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="freecad-dependency-smoke-selftest-") as temp:
        config = Path(temp) / "deps.json"
        executable = shutil.which("python3") or shutil.which("python")
        payload = {
            "dependencies": [
                {
                    "name": "PresentPythonModule",
                    "kind": "python_module",
                    "module": "json",
                    "affects": ["self-test present module"],
                },
                {
                    "name": "MissingPythonModule",
                    "kind": "python_module",
                    "module": "freecad_missing_dependency_probe_module",
                    "affects": ["self-test missing module"],
                },
                {
                    "name": "PresentExecutable",
                    "kind": "executable",
                    "executable": executable,
                    "version_args": ["--version"],
                    "affects": ["self-test present executable"],
                },
                {
                    "name": "MissingExecutable",
                    "kind": "executable",
                    "executable": "freecad-missing-dependency-probe-executable",
                    "version_args": ["--version"],
                    "affects": ["self-test missing executable"],
                },
            ]
        }
        write_json(config, payload)
        report = freecad_dependency_smoke.build_report(timeout=15, config_path=config)
        duplicate_config = Path(temp) / "duplicate.json"
        duplicate_payload = {
            "dependencies": [
                {
                    "name": "DuplicateDependency",
                    "kind": "python_module",
                    "module": "json",
                    "affects": ["self-test duplicate"],
                },
                {
                    "name": "DuplicateDependency",
                    "kind": "python_module",
                    "module": "json",
                    "affects": ["self-test duplicate"],
                },
            ]
        }
        write_json(duplicate_config, duplicate_payload)
        duplicate_report = freecad_dependency_smoke.build_report(timeout=15, config_path=duplicate_config)

        missing_affects_config = Path(temp) / "missing-affects.json"
        write_json(
            missing_affects_config,
            {
                "dependencies": [
                    {
                        "name": "NoAffects",
                        "kind": "python_module",
                        "module": "json",
                        "affects": [],
                    }
                ]
            },
        )
        missing_affects_report = freecad_dependency_smoke.build_report(
            timeout=15,
            config_path=missing_affects_config,
        )

        unsupported_config = Path(temp) / "unsupported.json"
        write_json(
            unsupported_config,
            {
                "dependencies": [
                    {
                        "name": "UnsupportedKind",
                        "kind": "service",
                        "affects": ["self-test unsupported kind"],
                    }
                ]
            },
        )
        unsupported_report = freecad_dependency_smoke.build_report(timeout=15, config_path=unsupported_config)

        placeholder_affects_config = Path(temp) / "placeholder-affects.json"
        write_json(
            placeholder_affects_config,
            {
                "dependencies": [
                    {
                        "name": "PlaceholderAffects",
                        "kind": "python_module",
                        "module": "json",
                        "affects": ["TODO"],
                    }
                ]
            },
        )
        placeholder_affects_report = freecad_dependency_smoke.build_report(
            timeout=15,
            config_path=placeholder_affects_config,
        )

        duplicate_affects_config = Path(temp) / "duplicate-affects.json"
        write_json(
            duplicate_affects_config,
            {
                "dependencies": [
                    {
                        "name": "DuplicateAffects",
                        "kind": "python_module",
                        "module": "json",
                        "affects": ["same coverage", "same coverage"],
                    }
                ]
            },
        )
        duplicate_affects_report = freecad_dependency_smoke.build_report(
            timeout=15,
            config_path=duplicate_affects_config,
        )

    deps = report.get("dependencies", {})
    scenarios = {
        "present_python_module_available": deps.get("PresentPythonModule", {}).get("available") is True,
        "missing_python_module_recorded": deps.get("MissingPythonModule", {}).get("available") is False,
        "present_executable_available": deps.get("PresentExecutable", {}).get("available") is True,
        "missing_executable_recorded": deps.get("MissingExecutable", {}).get("available") is False,
        "partial_when_any_dependency_missing": report.get("result") == "partial" and report.get("missing_count") == 2,
        "duplicate_dependency_name_fails_config": duplicate_report.get("result") == "failed"
        and any(error.get("kind") == "duplicate_name" for error in duplicate_report.get("config_errors", [])),
        "missing_affects_fails_config": missing_affects_report.get("result") == "failed"
        and any(error.get("kind") == "missing_affects" for error in missing_affects_report.get("config_errors", [])),
        "unsupported_kind_fails_config": unsupported_report.get("result") == "failed"
        and any(error.get("kind") == "unsupported_kind" for error in unsupported_report.get("config_errors", [])),
        "placeholder_affects_fails_config": placeholder_affects_report.get("result") == "failed"
        and any(error.get("kind") == "placeholder_affects" for error in placeholder_affects_report.get("config_errors", [])),
        "duplicate_affects_fails_config": duplicate_affects_report.get("result") == "failed"
        and any(error.get("kind") == "duplicate_affects" for error in duplicate_affects_report.get("config_errors", [])),
    }
    failed = [name for name, ok in scenarios.items() if not ok]
    result = {
        "schema": SCHEMA,
        "result": "ok" if not failed else "failed",
        "scenario_count": len(scenarios),
        "scenario_names": sorted(scenarios),
        "failed_scenarios": failed,
        "scenarios": scenarios,
        "dependency_report": report,
        "invalid_config_reports": {
            "duplicate": duplicate_report,
            "missing_affects": missing_affects_report,
            "unsupported": unsupported_report,
            "placeholder_affects": placeholder_affects_report,
            "duplicate_affects": duplicate_affects_report,
        },
    }
    write_json(args.output, result)
    return 0 if result["result"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
