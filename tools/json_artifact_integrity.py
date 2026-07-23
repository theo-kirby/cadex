#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Validate that generated JSON artifacts are strict machine-readable JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCHEMA = "freecad-json-artifact-integrity-v1"


def selected_artifact_paths(results_dir: Path, includes: list[str]) -> tuple[list[Path], list[dict[str, str]]]:
    results_root = results_dir.resolve()
    if not includes:
        return sorted(path for path in results_dir.rglob("*.json") if path.is_file()), []

    paths = []
    selection_failures = []
    seen = set()
    seen_patterns = set()
    for pattern in includes:
        if pattern in seen_patterns:
            selection_failures.append(
                {
                    "path": pattern,
                    "error": "duplicate include pattern",
                    "prefix": "",
                }
            )
            continue
        seen_patterns.add(pattern)
        pattern_path = Path(pattern)
        if pattern_path.is_absolute() or ".." in pattern_path.parts:
            selection_failures.append(
                {
                    "path": pattern,
                    "error": "include pattern must stay within results-dir",
                    "prefix": "",
                }
            )
            continue
        matches = sorted(results_dir.glob(pattern))
        if not matches:
            selection_failures.append(
                {
                    "path": pattern,
                    "error": "expected JSON artifact is missing",
                    "prefix": "",
                }
            )
            continue
        for match in matches:
            resolved = match.resolve()
            try:
                resolved.relative_to(results_root)
            except ValueError:
                selection_failures.append(
                    {
                        "path": pattern,
                        "error": "include match escapes results-dir",
                        "prefix": str(match),
                    }
                )
                continue
            if match.is_file() and resolved not in seen:
                paths.append(match)
                seen.add(resolved)
    return paths, selection_failures


def validate_json_artifacts(
    results_dir: Path,
    output: Path | None = None,
    includes: list[str] | None = None,
) -> dict[str, Any]:
    output_resolved = output.resolve() if output else None
    paths, selection_failures = selected_artifact_paths(results_dir, includes or [])
    checked = []
    failures = list(selection_failures)
    for path in paths:
        if not path.is_file():
            continue
        if output_resolved and path.resolve() == output_resolved:
            continue
        relpath = str(path.relative_to(results_dir))
        checked.append(relpath)
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            failures.append(
                {
                    "path": relpath,
                    "error": str(exc),
                    "prefix": path.read_text(encoding="utf-8", errors="replace")[:120],
                }
            )
    return {
        "schema": SCHEMA,
        "results_dir": str(results_dir),
        "result": "ok" if not failures else "failed",
        "checked_count": len(checked),
        "checked": checked,
        "missing_count": len(
            [failure for failure in selection_failures if failure.get("error") == "expected JSON artifact is missing"]
        ),
        "failure_count": len(failures),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=Path("/tmp/freecad-test-results"))
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Relative glob of JSON artifacts to validate; defaults to every JSON file under results-dir.",
    )
    args = parser.parse_args()

    report = validate_json_artifacts(args.results_dir, args.output, args.include)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if report["result"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
