# SPDX-License-Identifier: LGPL-2.1-or-later

"""Shared helpers for typed Sketcher constraint tools."""

from __future__ import annotations


POINT_POSITIONS = {
    "whole": 0,
    "edge": 0,
    "curve": 0,
    "start": 1,
    "end": 2,
    "center": 3,
    "midpoint": 3,
    "origin": 1,
}


def normalized_point_role(
    value: str | None,
    default: str = "whole",
    geometry_kind: str | None = None,
) -> str:
    clean = str(value or default or "whole").strip().lower()
    if clean not in POINT_POSITIONS:
        raise ValueError(
            "point role must be one of: " + ", ".join(sorted(POINT_POSITIONS))
        )
    return clean


def point_position(value: str, geometry_kind: str | None = None) -> int:
    return POINT_POSITIONS[normalized_point_role(value, geometry_kind=geometry_kind)]


def optional_point_position(
    value: str | None,
    geometry_handle: str | None = None,
    default: str = "whole",
    geometry_kind: str | None = None,
) -> int:
    if value is None:
        clean_handle = str(geometry_handle or "").strip().lower()
        if clean_handle == "origin":
            return POINT_POSITIONS["start"]
    return POINT_POSITIONS[
        normalized_point_role(value, default=default, geometry_kind=geometry_kind)
    ]


def point_role_enum() -> list[str]:
    return sorted(POINT_POSITIONS)
