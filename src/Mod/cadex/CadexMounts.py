# SPDX-License-Identifier: LGPL-2.1-or-later

"""Mounts: where a mechanism bolts to a skin, declared once (ADR-126).

A **mount** is a named, geometry-anchored, rebuild-derived frame on a
component — a terminal row with the two things a terminal deliberately does
not have:

- a **roll**, so the frame is fully determined rather than only aimed. An
  axis fixes two of three rotations; a bracket that can spin about its own
  bolt is not located, and "it looked right in the viewport" is how the
  remaining degree of freedom gets decided today.
- **fastener** and **clearance**, which are what the mating half needs to
  know and what nothing in a script currently says out loud.

Everything else is `CadexBoards`'s shape, deliberately: canonical rows in
millimetres in the component's own frame, ``units=`` as a declaration-time
convenience and nothing more, stored overrides as a **full row list** rather
than a patch, and drift **pruned** rather than refused (ADR-120's rule — a
stored row naming a mount the script no longer declares is what a rewritten
script leaves behind, not a caller error).

    m = mounts({
        "skin": mount_set(shell, [
            mount("hip_l", origin=(-40, 30, 120), axis=(0, 1, 0),
                  roll=(0, 0, 1), fastener="m3", clearance=2.0),
        ]),
        "leg": mount_set(leg, [
            mount("root", origin=(0, 0, 0), axis=(0, -1, 0), roll=(0, 0, 1)),
        ]),
    })

    result["leg"] = part.mate(leg, m["leg"]["root"], m["skin"]["hip_l"])

``part.mate`` takes the two handles rather than two name strings, which is
`part.cable(esp["sda"], fc["sda"])`'s idiom (ADR-062) and means there is one
name-resolution path in the codebase instead of two.

Like `CadexBoards`, `CadexNets`, `CadexTerminals` and `CadexRouting`, this
module **imports nothing from FreeCAD and touches no kernel object**. The
component is carried through opaquely. :func:`mate_matrix` is the whole
placement calculation and it is arithmetic on sixteen numbers, so the thing
most likely to be wrong is the thing most easily tested headless.
"""

from __future__ import annotations

from collections.abc import Mapping as _MappingABC
import math
import re
from types import MappingProxyType
from typing import Any, Iterator, Mapping, Sequence

# One project's rules for what a number, a name, a direction and a unit are.
# Imported rather than restated: two copies of "what is a valid row" is how
# two tables drift into disagreeing about the same measurement.
from CadexBoards import (
    UNITS,
    BoardError as _RowError,
    _name as _row_name,
    _optional_length,
    _triple,
    _unit,
    _units,
)
from CadexTerminals import TerminalError, invert_placement

__all__ = [
    "MAX_MOUNTS",
    "MAX_MOUNT_GROUPS",
    "MOUNT_FIELDS",
    "Mount",
    "MountError",
    "MountSet",
    "MountValues",
    "MountsCollector",
    "canonical_mount_rows",
    "declared_groups",
    "declared_mount_rows",
    "effective_mounts",
    "mate_matrix",
    "mount",
    "mount_set",
    "mounts",
    "prune_mount_rows",
    "row_frame",
    "row_from_world",
]

#: Mounts on one component, and components carrying mounts. Bounded for the
#: reason ``MAX_BOARDS`` is: a table longer than a person can read at once
#: was meant to be geometry.
MAX_MOUNTS = 64
MAX_MOUNT_GROUPS = 64

#: The row fields the editor may write, in canonical JSON order.
MOUNT_FIELDS = (
    "component",
    "name",
    "origin",
    "axis",
    "roll",
    "fastener",
    "clearance",
)

#: A fastener designation: free-form enough to name anything real, closed
#: enough that it cannot become a sentence.
_FASTENER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._x/+-]{0,31}$")

_MOUNT_MARKER = "cadex-project-mount-spec"
_GROUP_MARKER = "cadex-project-mount-group-spec"

_TINY = 1.0e-12


class MountError(ValueError):
    """A mount table that could not be stated, or could not be applied."""

    def __init__(
        self, message: str, *, details: Mapping[str, Any] | None = None
    ) -> None:
        self.details = dict(details or {})
        super().__init__(str(message))


def _wrap(exc: Exception) -> MountError:
    return MountError(str(exc), details=getattr(exc, "details", None))


# ---------------------------------------------------------------------------
# vector arithmetic, on plain numbers


def _cross(a: Sequence[float], b: Sequence[float]) -> list[float]:
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(float(x) * float(y) for x, y in zip(a, b))


def _normalized(vector: Sequence[float], *, what: str) -> list[float]:
    length = math.sqrt(_dot(vector, vector))
    if length <= _TINY:
        raise MountError(f"{what} has no direction")
    return [float(item) / length for item in vector]


def _orthogonal_roll(axis: Sequence[float], roll: Sequence[float], *, what: str):
    """The component of ``roll`` across ``axis``, normalised.

    A roll parallel to the axis states nothing — it is the one direction that
    cannot resolve the spin — so it is refused rather than silently replaced
    by an arbitrary perpendicular. Any other roll is projected, so a caller
    may hand over "up" without first making it exactly perpendicular.
    """

    along = _dot(roll, axis)
    across = [float(r) - along * float(a) for r, a in zip(roll, axis)]
    if math.sqrt(_dot(across, across)) <= 1.0e-9:
        raise MountError(
            f"{what} is parallel to the axis, so it fixes no rotation about "
            "it; give a direction across the axis (the mount's own 'up')"
        )
    return _normalized(across, what=what)


def _fastener(value: Any, *, what: str) -> str | None:
    if value is None:
        return None
    clean = str(value).strip()
    if not clean:
        return None
    if not _FASTENER.fullmatch(clean):
        raise MountError(
            f"{what} {clean!r} is a designation such as 'm3' or 'm4x0.7', not "
            "a description; it is metadata the mating half reads"
        )
    return clean


# ---------------------------------------------------------------------------
# declaration


def mount(
    name: str,
    *,
    origin: Sequence[float],
    axis: Sequence[float],
    roll: Sequence[float],
    fastener: Any = None,
    clearance: Any = None,
) -> dict[str, Any]:
    """Declare one mount on one component.

    ``origin`` is where the two parts meet, ``axis`` is the direction the
    other part approaches **along** — so two mating mounts face each other —
    and ``roll`` is the mount's own 'up', which is what makes the frame a
    frame rather than an aim. ``clearance`` is the free space the mount needs
    in front of it, in millimetres, and ``fastener`` names the screw.
    """

    try:
        clean_name = _row_name(name, what="mount() name")
        clean_axis = _unit(axis, what=f"mount({name!r}) axis")
        clean_origin = _triple(origin, what=f"mount({name!r}) origin")
        clean_roll = _orthogonal_roll(
            clean_axis,
            _unit(roll, what=f"mount({name!r}) roll"),
            what=f"mount({name!r}) roll",
        )
        clean_clearance = _optional_length(
            clearance, what=f"mount({name!r}) clearance", positive=False
        )
    except _RowError as exc:
        raise _wrap(exc) from exc
    return {
        "kind": _MOUNT_MARKER,
        "name": clean_name,
        "origin": clean_origin,
        "axis": clean_axis,
        "roll": clean_roll,
        "fastener": _fastener(fastener, what=f"mount({name!r}) fastener"),
        "clearance": clean_clearance,
    }


def mount_set(
    component: Any,
    rows: Sequence[Mapping[str, Any]] | None = None,
    *,
    units: str = "mm",
) -> dict[str, Any]:
    """Declare the mounts of one component.

    ``units="m"`` states what the numbers in *this* declaration are in; the
    stored row is millimetres either way.
    """

    try:
        clean_units = _units(units, what="mount_set() units")
    except _RowError as exc:
        raise _wrap(exc) from exc
    entries = list(rows or [])
    if len(entries) > MAX_MOUNTS:
        raise MountError(
            f"a component states at most {MAX_MOUNTS} mounts; received {len(entries)}"
        )
    clean: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping) or entry.get("kind") != _MOUNT_MARKER:
            raise MountError(
                f"mount_set() row {index} is not a mount(...); received {entry!r}"
            )
        row = {key: entry[key] for key in ("name", *MOUNT_FIELDS[2:])}
        if row["name"] in seen:
            raise MountError(
                f"mount_set() repeats {row['name']!r}; a mount is looked up by "
                "name, so the names on one component must be distinct"
            )
        seen.add(row["name"])
        clean.append(row)
    return {
        "kind": _GROUP_MARKER,
        "component": component,
        "units": clean_units,
        "rows": clean,
    }


# ---------------------------------------------------------------------------
# the canonical row


def canonical_mount_rows(rows: Any, *, what: str, allow_world: bool = False):
    """Validate a full mount-row list into canonical JSON, or refuse it.

    Shared by the declared table, the stored overrides and the host-side
    ``set_params(mounts=...)`` check, so all three agree on what a row is.
    ``allow_world`` admits ``frame="world"`` on a *request*: a mount measured
    in the viewport, which cadexd cannot convert because it has no geometry
    and never runs user code — the worker converts it (ADR-120's mechanism,
    reused).
    """

    if isinstance(rows, Mapping) or not isinstance(rows, (list, tuple)):
        raise MountError(f"{what} must be a list of mount rows; received {rows!r}")
    if len(rows) > MAX_MOUNT_GROUPS * MAX_MOUNTS:
        raise MountError(
            f"{what} holds {len(rows)} rows, past every bound this table has"
        )
    allowed = set(MOUNT_FIELDS) | ({"frame"} if allow_world else set())
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    counts: dict[str, int] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise MountError(f"{what}[{index}] must be an object; received {row!r}")
        unknown = sorted(set(map(str, row)) - allowed)
        if unknown:
            raise MountError(
                f"{what}[{index}] has unrecognised keys {unknown}; a row carries "
                f"{list(MOUNT_FIELDS)}"
            )
        try:
            component = _row_name(row.get("component"), what=f"{what}[{index}].component")
            name = _row_name(row.get("name"), what=f"{what}[{index}].name")
            origin = _triple(row.get("origin"), what=f"{what}[{index}].origin")
            axis = _unit(row.get("axis"), what=f"{what}[{index}].axis")
            roll = _unit(row.get("roll"), what=f"{what}[{index}].roll")
            clearance = _optional_length(
                row.get("clearance"), what=f"{what}[{index}].clearance", positive=False
            )
        except _RowError as exc:
            raise _wrap(exc) from exc
        if (component, name) in seen:
            raise MountError(
                f"{what}[{index}] repeats mount {name!r} on {component!r}; a "
                "mount is looked up by name, so the names on one component "
                "must be distinct"
            )
        seen.add((component, name))
        counts[component] = counts.get(component, 0) + 1
        if counts[component] > MAX_MOUNTS:
            raise MountError(
                f"component {component!r} holds more than {MAX_MOUNTS} mounts"
            )
        entry: dict[str, Any] = {
            "component": component,
            "name": name,
            "origin": origin,
            "axis": axis,
            "roll": _orthogonal_roll(axis, roll, what=f"{what}[{index}].roll"),
            "fastener": _fastener(
                row.get("fastener"), what=f"{what}[{index}].fastener"
            ),
            "clearance": clearance,
        }
        frame = row.get("frame")
        if frame is not None:
            if str(frame) not in {"world", "component"}:
                raise MountError(
                    f"{what}[{index}].frame is 'world' (measured in the "
                    "viewport) or absent (the component's own frame); received "
                    f"{frame!r}"
                )
            if str(frame) == "world":
                entry["frame"] = "world"
        result.append(entry)
    return result


def declared_groups(specs: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    """``{component name: entry}`` from a stored ``mount_specs`` block."""

    result: dict[str, dict[str, Any]] = {}
    for entry in list((specs or {}).get("mounts") or []):
        if not isinstance(entry, Mapping):
            continue
        name = str(entry.get("name") or "")
        if name:
            result[name] = dict(entry)
    return result


def declared_mount_rows(specs: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Every declared mount row, flattened and stamped with its component."""

    rows: list[dict[str, Any]] = []
    for name, entry in declared_groups(specs).items():
        for row in list(entry.get("mounts") or []):
            if isinstance(row, Mapping):
                rows.append({**dict(row), "component": name})
    return rows


def prune_mount_rows(
    rows: Sequence[Mapping[str, Any]], specs: Mapping[str, Any] | None
) -> list[dict[str, Any]]:
    """Drop rows whose component the script no longer declares (ADR-039).

    Dropped, never refused: a stale row is what a rewritten script leaves
    behind, and raising on it would wedge the editor the moment the AI
    renamed a component.
    """

    groups = declared_groups(specs)
    return [dict(row) for row in rows if str(row.get("component") or "") in groups]


def effective_mounts(
    specs: Mapping[str, Any] | None, values: Any
) -> list[dict[str, Any]]:
    """The table as built: stored overrides when there are any, else declared."""

    if not values:
        return declared_mount_rows(specs)
    return prune_mount_rows(
        canonical_mount_rows(values, what="mount values"), specs
    )


# ---------------------------------------------------------------------------
# the frame, and the mate


def row_frame(row: Mapping[str, Any]) -> tuple[list[float], list[float], list[float], list[float]]:
    """(origin, x, y, z) of one mount row, as an orthonormal right-handed frame.

    ``z`` is the mount's axis, ``x`` its roll, ``y`` the third by
    construction. Derived rather than stored, so a roll that is merely
    *nearly* perpendicular cannot become a sheared frame.
    """

    origin = [float(value) for value in row["origin"]]
    z_axis = _normalized(row["axis"], what="mount axis")
    x_axis = _orthogonal_roll(z_axis, _normalized(row["roll"], what="mount roll"),
                              what="mount roll")
    y_axis = _cross(z_axis, x_axis)
    return origin, x_axis, y_axis, z_axis


def _matrix(origin, x_axis, y_axis, z_axis) -> list[float]:
    """Row-major 4x4 taking frame coordinates into the component's own."""

    return [
        x_axis[0], y_axis[0], z_axis[0], origin[0],
        x_axis[1], y_axis[1], z_axis[1], origin[1],
        x_axis[2], y_axis[2], z_axis[2], origin[2],
        0.0, 0.0, 0.0, 1.0,
    ]


def _multiply(left: Sequence[float], right: Sequence[float]) -> list[float]:
    return [
        sum(left[row * 4 + k] * right[k * 4 + column] for k in range(4))
        for row in range(4)
        for column in range(4)
    ]


def _inverse_rigid(matrix: Sequence[float]) -> list[float]:
    """Inverse of a rotation+translation, by transpose. No scale is admitted
    because a mount frame is built orthonormal a few lines above."""

    rotation = [[matrix[row * 4 + column] for column in range(3)] for row in range(3)]
    translation = [matrix[3], matrix[7], matrix[11]]
    inverse = [[rotation[column][row] for column in range(3)] for row in range(3)]
    offset = [
        -sum(inverse[row][k] * translation[k] for k in range(3)) for row in range(3)
    ]
    return [
        inverse[0][0], inverse[0][1], inverse[0][2], offset[0],
        inverse[1][0], inverse[1][1], inverse[1][2], offset[1],
        inverse[2][0], inverse[2][1], inverse[2][2], offset[2],
        0.0, 0.0, 0.0, 1.0,
    ]


def mate_matrix(
    source: Mapping[str, Any],
    target: Mapping[str, Any],
    *,
    flip: bool = False,
    offset: float = 0.0,
) -> list[float]:
    """The placement that brings ``source``'s mount onto ``target``'s.

    The convention is **face to face**: each mount's axis points the way the
    other part approaches from, so mating opposes them — source ``+z`` onto
    target ``−z`` — and the two origins coincide. Rolls are aligned, so the
    remaining rotation is decided by the declaration rather than by whatever
    the kernel happens to produce.

    ``flip`` turns the part half a turn about the mating axis, for a bracket
    that bolts on the other way round. ``offset`` moves it along the target's
    axis afterwards — positive is *away* from the target's face, which is a
    gap; negative is into it, which is an interference the caller has asked
    for and will be told about.
    """

    source_origin, sx, sy, sz = row_frame(source)
    target_origin, tx, ty, tz = row_frame(target)

    # Target frame, with its z reversed so the two faces oppose. Reversing z
    # alone would mirror the frame, so y is reversed with it and the result
    # stays right-handed -- a mirrored placement is not a rigid motion and
    # would silently turn a left bracket into a right one.
    opposed_z = [-value for value in tz]
    opposed_y = [-value for value in ty]
    if flip:
        opposed_y = [-value for value in opposed_y]
        target_x = [-value for value in tx]
    else:
        target_x = list(tx)

    placed_origin = [
        origin + tz[index] * float(offset)
        for index, origin in enumerate(target_origin)
    ]
    into_target = _matrix(placed_origin, target_x, opposed_y, opposed_z)
    into_source = _matrix(source_origin, sx, sy, sz)
    return _multiply(into_target, _inverse_rigid(into_source))


def row_from_world(
    row: Mapping[str, Any], matrix: Sequence[float], *, units: str = "mm"
) -> dict[str, Any]:
    """One ``frame="world"`` row, carried back into its component's own frame.

    ``CadexBoards.row_from_world`` with one more direction to carry: the
    roll. A mount measured in the viewport arrives as a frame, and a frame
    that lost its roll on the way in would be an aim — which is precisely the
    thing this table exists to stop being implicit.
    """

    try:
        inverse = invert_placement(matrix)
    except TerminalError as exc:
        raise MountError(
            f"mount {row.get('name')!r} was measured in the viewport and "
            f"cannot be carried into its component's own frame: {exc}",
            details=getattr(exc, "details", None),
        ) from exc
    factor = UNITS[_units(units, what="mount units")]
    origin = _triple(row.get("origin"), what="row origin")

    def carry_point(point: Sequence[float]) -> list[float]:
        return [
            inverse[0 + 4 * index] * point[0]
            + inverse[1 + 4 * index] * point[1]
            + inverse[2 + 4 * index] * point[2]
            + inverse[3 + 4 * index]
            for index in range(3)
        ]

    def carry_direction(vector: Sequence[float]) -> list[float]:
        return [
            inverse[0 + 4 * index] * vector[0]
            + inverse[1 + 4 * index] * vector[1]
            + inverse[2 + 4 * index] * vector[2]
            for index in range(3)
        ]

    placed_origin = carry_point(origin)
    axis = carry_direction(_unit(row.get("axis"), what="row axis"))
    roll = carry_direction(_unit(row.get("roll"), what="row roll"))
    scale = math.sqrt(_dot(axis, axis))
    if scale <= _TINY:
        raise MountError("the component's placement collapses an axis")
    clearance = row.get("clearance")
    result = {
        "component": str(row.get("component") or ""),
        "name": str(row.get("name") or ""),
        "origin": [value * factor for value in placed_origin],
        "axis": [value / scale for value in axis],
        "roll": [value / scale for value in roll],
        "fastener": row.get("fastener"),
        "clearance": (
            None if clearance is None else float(clearance) * scale * factor
        ),
    }
    return canonical_mount_rows([result], what="converted row")[0]


# ---------------------------------------------------------------------------
# the handles a script holds


class Mount:
    """One named mount of one component: ``m['skin']['hip_l']``."""

    __slots__ = ("_name", "_component", "_row")

    def __init__(self, name: str, component: Any, row: Mapping[str, Any]) -> None:
        self._name = str(name)
        self._component = component
        self._row = MappingProxyType(dict(row))

    @property
    def name(self) -> str:
        return self._name

    @property
    def component(self) -> Any:
        return self._component

    @property
    def row(self) -> Mapping[str, Any]:
        return self._row

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"Mount({self._name!r})"


class MountSet(_MappingABC):
    """The named mounts of one component."""

    __slots__ = ("_component", "_rows", "_names")

    def __init__(self, component: Any, rows: Sequence[Mapping[str, Any]]) -> None:
        self._component = component
        self._rows = {str(row["name"]): dict(row) for row in rows}
        self._names = tuple(self._rows)

    @property
    def names(self) -> tuple[str, ...]:
        return self._names

    @property
    def component(self) -> Any:
        return self._component

    def __len__(self) -> int:
        return len(self._names)

    def __iter__(self) -> Iterator[str]:
        return iter(self._names)

    def __getitem__(self, name: Any) -> Mount:
        if isinstance(name, int) and not isinstance(name, bool):
            raise MountError(
                "a mount is named, not numbered: an ordinal would start "
                f"meaning a different mount the moment the table changed. Use "
                f"one of {list(self._names)}"
            )
        clean = str(name)
        if clean not in self._rows:
            raise MountError(
                f"this component has no mount named {clean!r}; it has "
                f"{list(self._names)}",
                details={
                    "stage": "mount_lookup",
                    "requested": clean,
                    "available": list(self._names),
                },
            )
        return Mount(clean, self._component, self._rows[clean])

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"MountSet({list(self._names)!r})"


class MountValues(_MappingABC):
    """What ``mounts(...)`` returns: ``{component name: MountSet}``."""

    __slots__ = ("_sets", "_specs")

    def __init__(self, sets: Mapping[str, MountSet], specs: Mapping[str, Any]) -> None:
        object.__setattr__(self, "_sets", dict(sets))
        object.__setattr__(self, "_specs", dict(specs))

    @property
    def specs(self) -> dict[str, Any]:
        return dict(self._specs)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._sets)

    def __len__(self) -> int:
        return len(self._sets)

    def __iter__(self) -> Iterator[str]:
        return iter(self._sets)

    def __getitem__(self, name: Any) -> MountSet:
        clean = str(name)
        if clean not in self._sets:
            raise MountError(
                f"no component named {clean!r} declares mounts; this project "
                f"declares {list(self._sets)}",
                details={
                    "stage": "mount_group_lookup",
                    "requested": clean,
                    "available": list(self._sets),
                },
            )
        return self._sets[clean]

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise MountError("a mounts(...) table is immutable once declared")

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"MountValues({list(self._sets)!r})"


class MountsCollector:
    """``mounts(...)`` as the worker stages it: declaration plus overrides.

    The same two-layer read `BoardsCollector` performs — what the script
    declared, and what the editor stored over it — with the same conversion
    of a ``frame="world"`` row through the component's inverted placement,
    supplied by the worker because only the worker has one.
    """

    def __init__(self, overrides: Any = None, placement: Any = None) -> None:
        self.specs: dict[str, Any] = {"mounts": []}
        self.rows: list[dict[str, Any]] = []
        #: Rows carried out of world coordinates on this run, canonical, so
        #: the store can write them back and convert a pick exactly once.
        self.converted: list[dict[str, Any]] = []
        self._overrides = overrides
        self._placement = placement
        self._called = False

    def __call__(self, mapping: Any) -> MountValues:
        if self._called:
            raise MountError(
                "mounts(...) may be called once: the table is the project's, "
                "not one statement's"
            )
        self._called = True
        declared = self._clean(mapping)
        self.specs = {
            "mounts": [
                {"name": name, "mounts": [dict(row) for row in entry["rows"]]}
                for name, entry in declared.items()
            ]
        }
        rows = effective_mounts(self.specs, self._resolved_overrides(declared))
        self.rows = rows
        by_component: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_component.setdefault(str(row["component"]), []).append(row)
        sets = {
            name: MountSet(entry["component"], by_component.get(name, []))
            for name, entry in declared.items()
        }
        return MountValues(sets, self.specs)

    def _clean(self, mapping: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(mapping, Mapping):
            raise MountError(
                "mounts(...) takes {name: mount_set(component, [mount(...)])}; "
                f"received {mapping!r}"
            )
        if len(mapping) > MAX_MOUNT_GROUPS:
            raise MountError(
                f"a project states at most {MAX_MOUNT_GROUPS} components with "
                f"mounts; received {len(mapping)}"
            )
        cleaned: dict[str, dict[str, Any]] = {}
        for key, value in mapping.items():
            try:
                name = _row_name(key, what="mounts() key")
            except _RowError as exc:
                raise _wrap(exc) from exc
            if not isinstance(value, Mapping) or value.get("kind") != _GROUP_MARKER:
                raise MountError(
                    f"mounts()[{name!r}] must be a mount_set(...); received "
                    f"{value!r}"
                )
            factor = UNITS[str(value.get("units") or "mm")]
            rows = [
                {
                    **dict(row),
                    "origin": [item * factor for item in row["origin"]],
                    "clearance": (
                        None if row.get("clearance") is None
                        else float(row["clearance"]) * factor
                    ),
                }
                for row in value["rows"]
            ]
            cleaned[name] = {
                "component": value["component"],
                "units": str(value.get("units") or "mm"),
                "rows": rows,
            }
        return cleaned

    def _resolved_overrides(self, declared: Mapping[str, dict[str, Any]]) -> Any:
        """Stored rows, with every world-frame row converted exactly once."""

        rows = self._overrides
        if not rows:
            return rows
        resolved: list[dict[str, Any]] = []
        for row in canonical_mount_rows(rows, what="mount values", allow_world=True):
            if row.get("frame") != "world":
                resolved.append(row)
                continue
            entry = declared.get(str(row.get("component") or ""))
            if entry is None:
                # A world row naming a component the script no longer
                # declares is dropped by the rule every stale row is; the
                # pruning below would drop it anyway, and converting it first
                # would need a component that is not there.
                continue
            if self._placement is None:
                raise MountError(
                    f"mount {row.get('name')!r} on {row.get('component')!r} was "
                    "measured in world coordinates, and this process cannot "
                    "resolve the component's placement to convert it"
                )
            converted = row_from_world(
                row, self._placement(entry["component"]), units=entry["units"]
            )
            resolved.append(converted)
            self.converted.append(converted)
        return resolved


def mounts(mapping: Any) -> MountValues:  # pragma: no cover - staged form
    """Declare the project's mount table. Replaced by a collector in the worker."""

    return MountsCollector()(mapping)
