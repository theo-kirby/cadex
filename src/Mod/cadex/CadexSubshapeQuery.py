# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The one vocabulary for naming a subshape without an index (Phase 10b).

A subshape is identified by *what it is* — its geometry type, orientation,
size, and where it sits — never by its ordinal in ``TopExp::MapShapes``.
ADR-028 established that the ordering is reproducible; it did not make it
*stable across edits*, and it never can be: any parameter change that alters
topology renumbers everything after it, so a saved ordinal silently comes to
mean a different face.

The vocabulary was already here — ``resolve_pin`` has spoken it since Phase
5.2 — but it lived inside ``cadex_partdesign_worker``, which imports
``cadex_part_worker``. The part domain therefore could not reach it without a
cycle, which is why the five index-taking part ops still took integers. This
module is that extraction (scheduled for Phase 11a, forced forward by 10b),
and it is deliberately kernel-neutral: it touches only the shape objects
handed to it, so replacing FreeCAD underneath does not move pin resolution.

Selector keys, all optional unless noted:

``element_type``    ``edge``/``wire``/``face``/``shell``/``solid``; callers
                    that know the kind inject it.
``expected_count``  **required by op selectors** — the declared cardinality.
                    A mismatch raises rather than silently doing less work.
``geometry_type``   ``Plane``, ``Cylinder``, ``Circle``, ``Line``, ...
``normal`` / ``direction``  unit-ish vector, matched by angle within
                    ``normal_tolerance_degrees`` / ``direction_tolerance_degrees``
                    (default 1.0).
``radius``          with ``radius_tolerance`` (default 1e-6).
``min_area`` / ``max_area`` / ``min_length`` / ``max_length``
``near_point``      with ``max_distance`` (default 1e-6).
``type: all_edges`` the whole-edge-set shorthand partdesign uses.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping

#: The collection attribute backing each selectable kind. ``face`` and
#: ``edge`` are what carry a full geometric fingerprint; the container kinds
#: are selectable too (``part.subshape`` accepts them) but only by the
#: measures that mean anything for them — centre, area, volume.
SUBSHAPE_COLLECTIONS: Mapping[str, str] = {
    "edge": "Edges",
    "wire": "Wires",
    "face": "Faces",
    "shell": "Shells",
    "solid": "Solids",
}

ELEMENT_TYPES = frozenset(SUBSHAPE_COLLECTIONS)

#: Every key a selector may carry, with the tolerance each measure honours.
#: Closed deliberately: an unrecognised key is a typo that would otherwise
#: widen the match silently — ``radius_tolerence`` would select every radius
#: rather than one, and the script would build wrong geometry that validates.
SELECTOR_KEYS = frozenset(
    {
        "expected_count",
        "geometry_type",
        "normal",
        "normal_tolerance_degrees",
        "direction",
        "direction_tolerance_degrees",
        "radius",
        "radius_tolerance",
        "min_area",
        "max_area",
        "min_length",
        "max_length",
        "near_point",
        "max_distance",
    }
)


class SubshapeSelectionError(RuntimeError):
    """A selector did not resolve to its declared cardinality.

    ``details`` carries the failure envelope the agent reads and acts on:
    the selection as written, the expected and actual counts, what did
    match, and the available subshapes to re-query against.
    """

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None):
        self.details = dict(details or {})
        super().__init__(message)


def _unit(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    try:
        components = [float(item) for item in value]
    except (TypeError, ValueError):
        return None
    length = math.sqrt(sum(item**2 for item in components))
    if length <= 1.0e-12:
        return None
    return [item / length for item in components]


def _angle_matches(actual: Any, requested: Any, tolerance: float) -> bool:
    left = _unit(actual)
    right = _unit(requested)
    if left is None or right is None:
        return False
    dot = max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right))))
    return math.degrees(math.acos(dot)) <= tolerance


def subshape_geometry(shape: Any, kind: str, index: int, subshape: Any) -> dict[str, Any]:
    """The identity of one subshape: name, type, and geometric fingerprint.

    ``index`` is 1-based and *reported*, never used for selection. It stays in
    the payload because the picking path and the failure envelopes both need
    to point at a concrete subshape.
    """

    center = getattr(subshape, "CenterOfMass", None)
    geometry = None
    if kind in {"face", "edge"}:
        try:
            geometry = getattr(subshape, "Surface" if kind == "face" else "Curve")
        except Exception:
            pass
    result: dict[str, Any] = {
        "name": f"{kind.title()}{index}",
        "element_type": kind,
        "geometry_type": (
            type(geometry).__name__.removeprefix("Part.")
            if geometry is not None
            else "Undefined"
        ),
        "center_mm": (
            [float(center.x), float(center.y), float(center.z)]
            if center is not None
            else None
        ),
    }
    if kind == "face":
        result["area_mm2"] = float(subshape.Area)
        try:
            u_min, u_max, v_min, v_max = (float(value) for value in subshape.ParameterRange)
            normal = subshape.normalAt((u_min + u_max) / 2.0, (v_min + v_max) / 2.0)
            result["normal"] = [float(normal.x), float(normal.y), float(normal.z)]
        except Exception:
            result["normal"] = None
        # Cylindrical and spherical faces carry a radius, and "the four 3 mm
        # holes" is the single most natural way to name drilled features.
        # Without this the radius filter silently matched nothing on faces,
        # because only edges were ever fingerprinted with one (Phase 10b).
        radius = getattr(geometry, "Radius", None)
        if radius is not None:
            result["radius_mm"] = float(radius)
    elif kind == "edge":
        result["length_mm"] = float(subshape.Length)
        try:
            first, last = (float(value) for value in subshape.ParameterRange)
            tangent = subshape.tangentAt((first + last) / 2.0)
            result["direction"] = [float(tangent.x), float(tangent.y), float(tangent.z)]
        except Exception:
            result["direction"] = None
        radius = getattr(geometry, "Radius", None)
        if radius is not None:
            result["radius_mm"] = float(radius)
    else:
        # Wires measure as length, shells and solids as area; a solid also
        # carries volume. Enough to tell two of them apart without inventing
        # a fingerprint the kernel does not actually define.
        if kind == "wire":
            result["length_mm"] = float(getattr(subshape, "Length", 0.0))
        else:
            result["area_mm2"] = float(getattr(subshape, "Area", 0.0))
        if kind == "solid":
            result["volume_mm3"] = float(getattr(subshape, "Volume", 0.0))
    return result


def subshape_collection(shape: Any, kind: str) -> list[Any]:
    """Every subshape of one kind, in kernel enumeration order."""

    attribute = SUBSHAPE_COLLECTIONS.get(kind)
    if attribute is None:
        raise ValueError(
            f"element_type must be one of {sorted(SUBSHAPE_COLLECTIONS)}, got {kind!r}."
        )
    return list(getattr(shape, attribute, []) or [])


def describe_subshapes(shape: Any, kind: str) -> list[dict[str, Any]]:
    """Fingerprint every subshape of one kind, 1-based."""

    return [
        subshape_geometry(shape, kind, index, value)
        for index, value in enumerate(subshape_collection(shape, kind), start=1)
    ]


def fingerprint_key(detail: Mapping[str, Any]) -> str:
    """A short, stable, human-legible handle for one subshape.

    Not a selector and not a hash of the ordinal: it is derived purely from
    the geometry, so the same face keeps its key across a rebuild that
    renumbers it. Collisions are possible in symmetric models and are
    tolerated — the key is a *hint* for the picking path, which sends the
    accompanying fingerprint fields along with it.
    """

    parts = [str(detail.get("element_type") or "?"), str(detail.get("geometry_type") or "?")]
    center = detail.get("center_mm")
    if isinstance(center, (list, tuple)) and len(center) == 3:
        parts.append(",".join(f"{float(value):.3f}" for value in center))
    for key in ("area_mm2", "length_mm", "radius_mm"):
        value = detail.get(key)
        if value is not None:
            parts.append(f"{key}={float(value):.3f}")
    return "|".join(parts)


def _matches(item: Mapping[str, Any], selection: Mapping[str, Any]) -> bool:
    geometry_type = str(selection.get("geometry_type") or "")
    if geometry_type and str(item.get("geometry_type") or "").lower() != geometry_type.lower():
        return False
    if "normal" in selection and not _angle_matches(
        item.get("normal"),
        selection["normal"],
        float(selection.get("normal_tolerance_degrees", 1.0)),
    ):
        return False
    if "direction" in selection and not _angle_matches(
        item.get("direction"),
        selection["direction"],
        float(selection.get("direction_tolerance_degrees", 1.0)),
    ):
        return False
    if "radius" in selection:
        radius = item.get("radius_mm")
        if radius is None or abs(float(radius) - float(selection["radius"])) > float(
            selection.get("radius_tolerance", 1.0e-6)
        ):
            return False
    area = item.get("area_mm2")
    if "min_area" in selection and (area is None or float(area) < float(selection["min_area"])):
        return False
    if "max_area" in selection and (area is None or float(area) > float(selection["max_area"])):
        return False
    length = item.get("length_mm")
    if "min_length" in selection and (
        length is None or float(length) < float(selection["min_length"])
    ):
        return False
    if "max_length" in selection and (
        length is None or float(length) > float(selection["max_length"])
    ):
        return False
    if "near_point" in selection:
        center = item.get("center_mm")
        if center is None or math.dist(center, selection["near_point"]) > float(
            selection.get("max_distance", 1.0e-6)
        ):
            return False
    return True


def _select(
    shape: Any, selection: Mapping[str, Any]
) -> tuple[list[int], list[dict[str, Any]]]:
    """Resolve a selector to (1-based ordinals, their details).

    Ordinals are produced here rather than recovered from the ``Face3``-style
    names later, so nothing downstream has to parse a display string to find
    the subshape it just selected.
    """

    if str(selection.get("type") or "") == "all_edges":
        details = describe_subshapes(shape, "edge")
        if not details:
            raise SubshapeSelectionError("The selected feature has no edges.")
        return list(range(1, len(details) + 1)), details

    kind = str(selection.get("element_type") or "")
    if kind not in ELEMENT_TYPES:
        # The partdesign original treated anything that was not "face" as
        # "edge"; kept, so existing partdesign selections behave identically.
        kind = "edge"
    details = describe_subshapes(shape, kind)

    chosen = [
        (ordinal, item)
        for ordinal, item in enumerate(details, start=1)
        if _matches(item, selection)
    ]
    expected = int(selection.get("expected_count") or 0)
    if len(chosen) != expected:
        raise SubshapeSelectionError(
            "A geometric selection did not match its declared cardinality.",
            details={
                "stage": "topology_selection",
                "selection": dict(selection),
                "expected_count": expected,
                "actual_count": len(chosen),
                "matches": [item for _ordinal, item in chosen],
                "available": details[:256],
            },
        )
    return [ordinal for ordinal, _item in chosen], [item for _ordinal, item in chosen]


def query_subelements(
    shape: Any, selection: Mapping[str, Any]
) -> tuple[list[str], list[dict[str, Any]]]:
    """Resolve one selector against a shape. Returns (names, details).

    Raises :class:`SubshapeSelectionError` when the match count does not equal
    the declared ``expected_count`` — the loud failure that makes a selector
    safer than an index, which would have quietly addressed the wrong face.
    """

    _ordinals, details = _select(shape, selection)
    return [str(item["name"]) for item in details], details


def resolve_selected_subshapes(
    shape: Any, kind: str, selection: Any
) -> tuple[list[Any], list[dict[str, Any]]]:
    """Selector (or the literal ``"all"``) to concrete subshape objects.

    The bridge the part ops use: it returns the kernel objects an operation
    needs alongside the details, so a failure can report what *was* there.
    """

    collection = subshape_collection(shape, kind)
    if selection == "all":
        if not collection:
            raise SubshapeSelectionError(
                f"The shape contains no {kind}s to select.",
                details={
                    "stage": "topology_selection",
                    "selection": "all",
                    "actual_count": 0,
                },
            )
        return collection, describe_subshapes(shape, kind)

    if not isinstance(selection, Mapping):
        raise ValueError(
            "expected 'all' or a selector mapping such as "
            "{'geometry_type': 'Cylinder', 'expected_count': 4}"
        )

    query = dict(selection)
    query["element_type"] = kind
    ordinals, details = _select(shape, query)
    return [collection[ordinal - 1] for ordinal in ordinals], details


__all__ = [
    "ELEMENT_TYPES",
    "SELECTOR_KEYS",
    "SUBSHAPE_COLLECTIONS",
    "SubshapeSelectionError",
    "describe_subshapes",
    "fingerprint_key",
    "query_subelements",
    "resolve_selected_subshapes",
    "subshape_collection",
    "subshape_geometry",
]
