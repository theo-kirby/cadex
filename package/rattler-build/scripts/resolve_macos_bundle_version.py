#!/usr/bin/env python3
"""Resolve VibeCAD's version metadata to valid Apple bundle versions."""

from __future__ import annotations

import argparse
import datetime
import json
import re
from pathlib import Path
from typing import Any


_APPLE_SUFFIXES = {"alpha": "a", "beta": "b", "rc": "fc"}


def _version_number(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{key} must be a non-negative integer, got {value!r}")
    return value


def resolve_bundle_versions(
    data: dict[str, Any], *, today: datetime.date | None = None
) -> tuple[str, str]:
    """Return (public version, Apple build version) for version.json data."""

    components = tuple(
        _version_number(data, key)
        for key in ("version_major", "version_minor", "version_patch")
    )
    if components[0] > 9999 or components[1] > 99 or components[2] > 99:
        raise ValueError(
            "Apple bundle version components exceed the supported 4.2.2 digit limits: "
            f"{components[0]}.{components[1]}.{components[2]}"
        )

    public_version = ".".join(str(component) for component in components)
    suffix = str(data.get("version_suffix", "")).strip()
    if not suffix:
        return public_version, public_version

    if suffix.lower() == "dev":
        date = today or datetime.date.today()
        return public_version, f"{public_version}d{date.isocalendar().week}"

    match = re.fullmatch(r"(?i)(RC|alpha|beta)([1-9][0-9]*)", suffix)
    if not match:
        raise ValueError(f"Unsupported macOS bundle version suffix: {suffix!r}")

    suffix_number = int(match.group(2))
    if suffix_number > 255:
        raise ValueError(f"macOS bundle version suffix exceeds Apple's limit: {suffix!r}")
    apple_suffix = _APPLE_SUFFIXES[match.group(1).lower()]
    return public_version, f"{public_version}{apple_suffix}{suffix_number}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("version_file", type=Path)
    args = parser.parse_args()

    try:
        with args.version_file.open(encoding="utf-8") as stream:
            data = json.load(stream)
        if not isinstance(data, dict):
            raise ValueError("version metadata must be a JSON object")
        public_version, bundle_version = resolve_bundle_versions(data)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    print(f"{public_version}|{bundle_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
