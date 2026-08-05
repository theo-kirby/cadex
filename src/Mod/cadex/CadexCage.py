# SPDX-License-Identifier: LGPL-2.1-or-later

"""The section cage: a shape as a table of rings (ADR-127).

The robot wolf's script *is already a section table* — six rings for the
torso, eight for the neck and head, six per leg — spelled as Python literals
inside three helper functions (`docs/ORGANIC.md` §1). Everything about that
works except the spelling: nudging one silhouette costs a chat turn and a
rebuild, and the ring that actually spoiled that model — a leg root flaring
to half the body length — survived eleven revisions because nobody could
grab it.

So the rings become a declared table, the fourth of its kind after
`nets`, `boards` and `mounts`, and for the same reasons in the same shape:
the script declares it, the store overrides it wholesale, the shell edits it,
and drift is pruned rather than refused.

    c = cage({
        "torso": section_cage([
            ring(0,   30, 38, exponent=2.4),
            ring(120, 46, 52, exponent=3.0),
            ring(300, 34, 40, exponent=2.2),
        ], axis=(1, 0, 0)),
    })

    result["torso"] = part.loft_cage(c["torso"], solid=True)

**The exponent is the reason this is worth a table and not just a list of
ellipses.** A ring is a *superellipse* — ``|x/a|^n + |y/b|^n = 1`` — where
``n = 2`` is an ellipse and larger ``n`` fills the corners out towards a
rounded rectangle. That single number is the difference between a limb that
reads as tubular and one that reads as muscled, and it costs a parameter
rather than an operation.

No new kernel mathematics: ``part.loft`` already lofts NURBS through section
wires, which is what the wolf was doing by hand. What is new is that the
sections are a table rather than literals.

Like `CadexBoards`, `CadexMounts`, `CadexNets` and `CadexTerminals`, this
module **imports nothing from FreeCAD and touches no kernel object**. The
section geometry is computed here, as plain points, so the profile is
testable without a kernel and Phase 12 re-binds it rather than re-deriving
it.
"""

from __future__ import annotations

from collections.abc import Mapping as _MappingABC
import math
from typing import Any, Iterator, Mapping, Sequence

# The same row vocabulary every other declared table validates against.
from CadexBoards import (
    UNITS,
    BoardError as _RowError,
    _finite,
    _name as _row_name,
    _triple,
    _unit,
    _units,
)

__all__ = [
    "MAX_CAGES",
    "MAX_RINGS",
    "RING_FIELDS",
    "CageError",
    "CageSet",
    "CageValues",
    "CagesCollector",
    "cage",
    "canonical_ring_rows",
    "declared_cages",
    "declared_ring_rows",
    "effective_rings",
    "prune_ring_rows",
    "ring",
    "ring_points",
    "section_cage",
]

#: Rings in one cage, and cages in one project. A cage longer than this was
#: meant to be a swept law (ADR-125) rather than a table someone reads.
MAX_RINGS = 128
MAX_CAGES = 64

#: The row fields the editor may write, in canonical JSON order.
RING_FIELDS = ("cage", "position", "half_width", "half_height", "roll", "exponent")

#: The superellipse exponent's range. 2.0 is an ellipse; below it the section
#: pinches towards an astroid and above it fills out towards a rounded
#: rectangle. Past 12 the difference stops being visible and the corner
#: curvature starts costing the tessellator.
MIN_EXPONENT = 1.0
MAX_EXPONENT = 12.0

#: How many points one section wire is sampled at. Enough that a high
#: exponent's corner reads as a corner; few enough that a 128-ring cage
#: stays inside the operation budget.
RING_SAMPLES = 64

_RING_MARKER = "cadex-project-ring-spec"
_CAGE_MARKER = "cadex-project-cage-spec"

_TINY = 1.0e-12


class CageError(ValueError):
    """A cage that could not be stated, or could not be applied."""

    def __init__(
        self, message: str, *, details: Mapping[str, Any] | None = None
    ) -> None:
        self.details = dict(details or {})
        super().__init__(str(message))


def _wrap(exc: Exception) -> CageError:
    return CageError(str(exc), details=getattr(exc, "details", None))


def _positive(value: Any, *, what: str) -> float:
    try:
        result = _finite(value, what=what)
    except _RowError as exc:
        raise _wrap(exc) from exc
    if result <= 0.0:
        raise CageError(f"{what} must be greater than zero; received {value!r}")
    return result


def _exponent(value: Any, *, what: str) -> float:
    try:
        result = _finite(value, what=what)
    except _RowError as exc:
        raise _wrap(exc) from exc
    if not MIN_EXPONENT <= result <= MAX_EXPONENT:
        raise CageError(
            f"{what} must be between {MIN_EXPONENT} and {MAX_EXPONENT}; 2.0 is "
            f"an ellipse and larger fills the corners out. Received {value!r}"
        )
    return result


def _default_up(axis: Sequence[float]) -> list[float]:
    """World up, or +Y for a cage that runs along Z."""

    if abs(float(axis[2])) > 0.9:
        return [0.0, 1.0, 0.0]
    return [0.0, 0.0, 1.0]


# ---------------------------------------------------------------------------
# declaration


def ring(
    position: float,
    half_width: float,
    half_height: float,
    *,
    roll: float = 0.0,
    exponent: float = 2.0,
) -> dict[str, Any]:
    """One section of a cage.

    ``position`` is the distance along the cage's axis, ``half_width`` and
    ``half_height`` are the section's radii across it, ``roll`` turns the
    section about the axis in degrees, and ``exponent`` is the superellipse
    power: 2.0 is an ellipse, 4.0 already reads as a muscle, 8.0 as a rounded
    box.
    """

    try:
        clean_position = _finite(position, what="ring() position")
        clean_roll = _finite(roll, what="ring() roll")
    except _RowError as exc:
        raise _wrap(exc) from exc
    return {
        "kind": _RING_MARKER,
        "position": clean_position,
        "half_width": _positive(half_width, what="ring() half_width"),
        "half_height": _positive(half_height, what="ring() half_height"),
        "roll": clean_roll,
        "exponent": _exponent(exponent, what="ring() exponent"),
    }


def section_cage(
    rings: Sequence[Mapping[str, Any]],
    *,
    axis: Sequence[float] = (1.0, 0.0, 0.0),
    origin: Sequence[float] = (0.0, 0.0, 0.0),
    up: Sequence[float] | None = None,
    units: str = "mm",
) -> dict[str, Any]:
    """Declare one cage: an axis, an origin, and the rings along it.

    The rings are perpendicular to ``axis`` and stationed at their
    ``position`` along it from ``origin``. ``up`` fixes which way a ring's
    *height* points, so a cage is a frame rather than an aim — the same thing
    a mount's roll does, and for the same reason.

    Left out, ``up`` is world +Z, or +Y for a cage that runs *along* Z — a
    leg is the commonest cage there is and refusing it over a default nobody
    stated would be a footgun. An ``up`` that is stated **and** parallel to
    the axis is still refused: that one is a mistake, not an omission.

    A curved spine is `part.sweep(scale_law=...)`'s job (ADR-125); this is
    the straight one, where every ring is separately shaped.
    """

    try:
        clean_units = _units(units, what="section_cage() units")
        clean_axis = _unit(axis, what="section_cage() axis")
        clean_origin = _triple(origin, what="section_cage() origin")
        stated = up is not None
        clean_up = _unit(
            up if stated else _default_up(clean_axis), what="section_cage() up"
        )
    except _RowError as exc:
        raise _wrap(exc) from exc
    if abs(sum(a * b for a, b in zip(clean_axis, clean_up))) > 1.0 - 1.0e-9:
        raise CageError(
            "section_cage() up is parallel to axis, so it fixes no rotation "
            "about it; give a direction across the axis"
        )

    entries = list(rings or [])
    if len(entries) < 2:
        raise CageError(
            f"a cage needs at least two rings to loft between; received "
            f"{len(entries)}"
        )
    if len(entries) > MAX_RINGS:
        raise CageError(
            f"a cage states at most {MAX_RINGS} rings; received {len(entries)}"
        )
    rows: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping) or entry.get("kind") != _RING_MARKER:
            raise CageError(
                f"section_cage() row {index} is not a ring(...); received {entry!r}"
            )
        row = {key: entry[key] for key in RING_FIELDS[1:]}
        if rows and row["position"] <= rows[-1]["position"]:
            raise CageError(
                f"section_cage() row {index} is at position "
                f"{row['position']}, which does not come after "
                f"{rows[-1]['position']}; rings run along the axis in order, "
                "and a loft through a table that doubles back is not a shape "
                "anyone asked for"
            )
        rows.append(row)
    return {
        "kind": _CAGE_MARKER,
        "axis": clean_axis,
        "origin": clean_origin,
        "up": clean_up,
        "units": clean_units,
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# the canonical row


def canonical_ring_rows(rows: Any, *, what: str) -> list[dict[str, Any]]:
    """Validate a full ring-row list into canonical JSON, or refuse it.

    Shared by the declared table, the stored overrides and the host-side
    ``set_params(cages=...)`` check, so all three agree on what a row is.

    Unlike a terminal or a mount, a ring has **no name**: its identity is its
    place in its cage's order. That is not an oversight — a ring is a station
    on a spine, and naming one would invite an override that addresses a ring
    the script has since moved past. The stored list is complete, so there is
    nothing an identity would be needed for.
    """

    if isinstance(rows, Mapping) or not isinstance(rows, (list, tuple)):
        raise CageError(f"{what} must be a list of ring rows; received {rows!r}")
    if len(rows) > MAX_CAGES * MAX_RINGS:
        raise CageError(
            f"{what} holds {len(rows)} rows, past every bound this table has"
        )
    allowed = set(RING_FIELDS)
    result: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    last: dict[str, float] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise CageError(f"{what}[{index}] must be an object; received {row!r}")
        unknown = sorted(set(map(str, row)) - allowed)
        if unknown:
            raise CageError(
                f"{what}[{index}] has unrecognised keys {unknown}; a row carries "
                f"{list(RING_FIELDS)}"
            )
        try:
            name = _row_name(row.get("cage"), what=f"{what}[{index}].cage")
            position = _finite(row.get("position"), what=f"{what}[{index}].position")
            roll = _finite(row.get("roll", 0.0), what=f"{what}[{index}].roll")
        except _RowError as exc:
            raise _wrap(exc) from exc
        counts[name] = counts.get(name, 0) + 1
        if counts[name] > MAX_RINGS:
            raise CageError(f"cage {name!r} holds more than {MAX_RINGS} rings")
        if name in last and position <= last[name]:
            raise CageError(
                f"{what}[{index}] is at position {position} on cage {name!r}, "
                f"which does not come after {last[name]}; the rows of one cage "
                "run along its axis in order"
            )
        last[name] = position
        result.append({
            "cage": name,
            "position": position,
            "half_width": _positive(
                row.get("half_width"), what=f"{what}[{index}].half_width"
            ),
            "half_height": _positive(
                row.get("half_height"), what=f"{what}[{index}].half_height"
            ),
            "roll": roll,
            "exponent": _exponent(
                row.get("exponent", 2.0), what=f"{what}[{index}].exponent"
            ),
        })
    return result


def declared_cages(specs: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    """``{cage name: entry}`` from a stored ``cage_specs`` block."""

    result: dict[str, dict[str, Any]] = {}
    for entry in list((specs or {}).get("cages") or []):
        if not isinstance(entry, Mapping):
            continue
        name = str(entry.get("name") or "")
        if name:
            result[name] = dict(entry)
    return result


def declared_ring_rows(specs: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Every declared ring row, flattened and stamped with its cage."""

    rows: list[dict[str, Any]] = []
    for name, entry in declared_cages(specs).items():
        for row in list(entry.get("rings") or []):
            if isinstance(row, Mapping):
                rows.append({**dict(row), "cage": name})
    return rows


def prune_ring_rows(
    rows: Sequence[Mapping[str, Any]], specs: Mapping[str, Any] | None
) -> list[dict[str, Any]]:
    """Drop rows whose cage the script no longer declares (ADR-039)."""

    cages = declared_cages(specs)
    return [dict(row) for row in rows if str(row.get("cage") or "") in cages]


def effective_rings(
    specs: Mapping[str, Any] | None, values: Any
) -> list[dict[str, Any]]:
    """The table as built: stored overrides when there are any, else declared.

    Wholesale, per cage rather than per project: a cage the editor has not
    touched keeps its declared rings even when another cage has overrides,
    because a stored list that mentions one cage is not a statement about the
    others.
    """

    declared = declared_ring_rows(specs)
    if not values:
        return declared
    overrides = prune_ring_rows(canonical_ring_rows(values, what="cage values"), specs)
    touched = {str(row["cage"]) for row in overrides}
    kept = [row for row in declared if str(row.get("cage") or "") not in touched]
    return overrides + kept


# ---------------------------------------------------------------------------
# the section itself


def ring_points(
    row: Mapping[str, Any],
    *,
    axis: Sequence[float] = (1.0, 0.0, 0.0),
    origin: Sequence[float] = (0.0, 0.0, 0.0),
    up: Sequence[float] = (0.0, 0.0, 1.0),
    samples: int = RING_SAMPLES,
) -> list[list[float]]:
    """One ring, as points on a closed superellipse in 3D.

    ``|x/a|^n + |y/b|^n = 1``, sampled by the parametrisation that stays
    even around the corners::

        x = a * sign(cos t) * |cos t| ** (2/n)
        y = b * sign(sin t) * |sin t| ** (2/n)

    At ``n = 2`` that is exactly ``(a cos t, b sin t)`` — an ellipse — which
    is what makes the exponent a continuous knob rather than a mode.
    """

    half_width = float(row["half_width"])
    half_height = float(row["half_height"])
    exponent = float(row.get("exponent", 2.0))
    roll = math.radians(float(row.get("roll", 0.0)))
    power = 2.0 / exponent

    axis_vector = _normalized(axis)
    across = _normalized(_reject(up, axis_vector))
    third = _cross(axis_vector, across)
    station = [
        float(origin[index]) + axis_vector[index] * float(row["position"])
        for index in range(3)
    ]

    points: list[list[float]] = []
    for index in range(int(samples)):
        angle = 2.0 * math.pi * index / float(samples)
        cosine, sine = math.cos(angle), math.sin(angle)
        u = half_width * _signed_power(cosine, power)
        v = half_height * _signed_power(sine, power)
        # The roll turns the section in its own plane, which is what lets a
        # ring follow a limb that twists without moving the spine.
        turned_u = u * math.cos(roll) - v * math.sin(roll)
        turned_v = u * math.sin(roll) + v * math.cos(roll)
        points.append([
            station[axis_index]
            + third[axis_index] * turned_u
            + across[axis_index] * turned_v
            for axis_index in range(3)
        ])
    return points


def _signed_power(value: float, power: float) -> float:
    magnitude = abs(value) ** power
    return magnitude if value >= 0.0 else -magnitude


def _cross(a: Sequence[float], b: Sequence[float]) -> list[float]:
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def _normalized(vector: Sequence[float]) -> list[float]:
    length = math.sqrt(sum(float(item) * float(item) for item in vector))
    if length <= _TINY:
        raise CageError("a cage direction has no direction")
    return [float(item) / length for item in vector]


def _reject(vector: Sequence[float], axis: Sequence[float]) -> list[float]:
    along = sum(float(v) * float(a) for v, a in zip(vector, axis))
    rejected = [float(v) - along * float(a) for v, a in zip(vector, axis)]
    if math.sqrt(sum(item * item for item in rejected)) <= 1.0e-9:
        raise CageError("a cage's up direction is parallel to its axis")
    return rejected


# ---------------------------------------------------------------------------
# the handles a script holds


class CageSet:
    """One named cage: its frame, and its rings in order."""

    __slots__ = ("_name", "_frame", "_rows")

    def __init__(self, name: str, frame: Mapping[str, Any],
                 rows: Sequence[Mapping[str, Any]]) -> None:
        self._name = str(name)
        self._frame = dict(frame)
        self._rows = [dict(row) for row in rows]

    @property
    def name(self) -> str:
        return self._name

    @property
    def axis(self) -> list[float]:
        return list(self._frame["axis"])

    @property
    def origin(self) -> list[float]:
        return list(self._frame["origin"])

    @property
    def up(self) -> list[float]:
        return list(self._frame["up"])

    @property
    def rows(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self._rows]

    @property
    def length(self) -> float:
        """Spine length: the last ring's position less the first's."""

        if not self._rows:
            return 0.0
        return float(self._rows[-1]["position"]) - float(self._rows[0]["position"])

    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(self.rows)

    def to_payload(self) -> dict[str, Any]:
        """Plain JSON for the worker: the frame plus the rows, nothing else."""

        return {
            "cage": self._name,
            "axis": list(self._frame["axis"]),
            "origin": list(self._frame["origin"]),
            "up": list(self._frame["up"]),
            "rings": self.rows,
        }

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"CageSet({self._name!r}, {len(self._rows)} rings)"


class CageValues(_MappingABC):
    """What ``cage(...)`` returns: ``{name: CageSet}``."""

    __slots__ = ("_sets", "_specs")

    def __init__(self, sets: Mapping[str, CageSet], specs: Mapping[str, Any]) -> None:
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

    def __getitem__(self, name: Any) -> CageSet:
        clean = str(name)
        if clean not in self._sets:
            raise CageError(
                f"no cage named {clean!r}; this project declares "
                f"{list(self._sets)}",
                details={
                    "stage": "cage_lookup",
                    "requested": clean,
                    "available": list(self._sets),
                },
            )
        return self._sets[clean]

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise CageError("a cage(...) table is immutable once declared")

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"CageValues({list(self._sets)!r})"


class CagesCollector:
    """``cage(...)`` as the worker stages it: declaration plus overrides."""

    def __init__(self, overrides: Any = None) -> None:
        self.specs: dict[str, Any] = {"cages": []}
        self.rows: list[dict[str, Any]] = []
        self._overrides = overrides
        self._called = False

    def __call__(self, mapping: Any) -> CageValues:
        if self._called:
            raise CageError(
                "cage(...) may be called once: the table is the project's, not "
                "one statement's"
            )
        self._called = True
        declared = self._clean(mapping)
        self.specs = {
            "cages": [
                {
                    "name": name,
                    "axis": entry["axis"],
                    "origin": entry["origin"],
                    "up": entry["up"],
                    "rings": [dict(row) for row in entry["rows"]],
                }
                for name, entry in declared.items()
            ]
        }
        rows = effective_rings(self.specs, self._overrides)
        self.rows = rows
        by_cage: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_cage.setdefault(str(row["cage"]), []).append(row)
        sets = {
            name: CageSet(
                name,
                entry,
                sorted(by_cage.get(name, []), key=lambda row: float(row["position"])),
            )
            for name, entry in declared.items()
        }
        return CageValues(sets, self.specs)

    def _clean(self, mapping: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(mapping, Mapping):
            raise CageError(
                "cage(...) takes {name: section_cage([ring(...), ...])}; "
                f"received {mapping!r}"
            )
        if len(mapping) > MAX_CAGES:
            raise CageError(
                f"a project states at most {MAX_CAGES} cages; received "
                f"{len(mapping)}"
            )
        cleaned: dict[str, dict[str, Any]] = {}
        for key, value in mapping.items():
            try:
                name = _row_name(key, what="cage() key")
            except _RowError as exc:
                raise _wrap(exc) from exc
            if not isinstance(value, Mapping) or value.get("kind") != _CAGE_MARKER:
                raise CageError(
                    f"cage()[{name!r}] must be a section_cage(...); received "
                    f"{value!r}"
                )
            factor = UNITS[str(value.get("units") or "mm")]
            rows = [
                {
                    **dict(row),
                    "position": float(row["position"]) * factor,
                    "half_width": float(row["half_width"]) * factor,
                    "half_height": float(row["half_height"]) * factor,
                }
                for row in value["rows"]
            ]
            cleaned[name] = {
                "axis": list(value["axis"]),
                "origin": [item * factor for item in value["origin"]],
                "up": list(value["up"]),
                "rows": rows,
            }
        return cleaned


def cage(mapping: Any) -> CageValues:  # pragma: no cover - staged form
    """Declare the project's cage table. Replaced by a collector in the worker."""

    return CagesCollector()(mapping)
