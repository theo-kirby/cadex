# SPDX-License-Identifier: LGPL-2.1-or-later

"""Named, geometry-anchored ports for the harness operations (ADR-062).

``part.cable`` and ``part.bundle`` took ports as literal ``(point,
direction)`` pairs (ADR-056, ADR-057), and that was wrong in three ways at
once.  A through-hole has no surface point to name — its attachment is an
*axis* and a depth.  A hand-measured constant does not move when a slider
does, which defeats the one property a routed wire exists for.  And
``((11.3, -4.0, 3.8), (1, 0, 0))`` does not say which signal it is.

A **terminal** fixes all three: it is named, and it is derived from geometry
on every rebuild.  ``part.terminals`` names holes or pads with a selector,
the same ADR-029 vocabulary the five selector-taking part ops use; both
``part.terminals`` and ``mesh.terminals`` also take a *declared* layout, for
an imported STL where there is no BREP face to select.

Two properties carry the module.

**A terminal is never geometry.**  It is not a ``DomainValue``, it has no
output type, it is never built, published or digested.  It converts to plain
JSON inside a ``cable``/``bundle`` argument with the component's payload
nested in it, and the worker resolves it there.  Everything downstream —
``_OPERATION_OUTPUT_TYPES``, the pack ``output_types``, ``build_part_shape``,
the tree — is untouched, which is why a script that uses no terminals
rebuilds byte-identically.

**Ordering is geometric, never ordinal.**  ``order_by`` is a direction;
matched faces are projected onto it and sorted along it.  Taking
``TopExp::MapShapes`` order would reintroduce exactly the index reference
ADR-029 deleted — a saved ``names`` list would silently start naming
different holes the moment a parameter changed topology.

Like ``CadexRouting`` and ``CadexBundle``, this module imports nothing from
FreeCAD and touches no kernel object.  The host extracts the handful of
numbers a matched face carries — axis, centre, radius, parameter range — and
hands them in; the layout, the ordering and the placement arithmetic are
here, and are unit-testable headless for the same reason the router is.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

__all__ = [
    "MAX_TERMINALS",
    "Terminal",
    "TerminalError",
    "TerminalSet",
    "apply_placement",
    "declared_layout",
    "identity_matrix",
    "resolve_terminals",
    "selector_layout",
]

#: One component's terminal count.  A 40-pin header is a real thing; four
#: hundred is a script that meant something else, and the resolved set is
#: held in a per-request memo, so it is bounded like everything else here.
MAX_TERMINALS = 256

#: Below this a direction has no direction.
_TINY = 1.0e-12

#: How far a hole's axis may lie from ``exit`` before the pairing is refused.
#: A ``Cylinder`` face gives an axis but not which end is outward, so ``exit``
#: is what resolves it — and an ``exit`` across the barrel resolves nothing.
_EXIT_ALIGNMENT = 0.5  # cos 60 degrees

#: Ordering keys are rounded to this many decimals before comparison, so two
#: holes drilled at the same station order by the secondary axis rather than
#: by whichever one float noise put first.  Rounding is a function of one
#: value, so the comparison stays a total order.
_ORDER_DECIMALS = 6

#: Columns of a placement's linear part may differ in length by at most this
#: ratio, and may be out of square by at most this much, before it is refused
#: as non-uniform.  A skewed frame does not rotate an axis, it *bends* it.
_RIGID_TOLERANCE = 1.0e-9

#: The declared-layout keys, closed like ``SELECTOR_KEYS`` and for the same
#: reason: a typo that widened the layout silently would place a terminal in
#: mid-air and the script would still build.
LAYOUT_KEYS = frozenset(
    {"origin", "along", "axis", "pitch", "count", "hole_dia", "depth"}
)

#: What a selector names.  ``holes`` resolves to an axis and a depth,
#: ``pads`` to a face centre and its normal.
SELECTOR_KINDS = ("holes", "pads")


class TerminalError(ValueError):
    """A terminal set that could not be stated, or could not be resolved.

    ``details`` carries the same shape of envelope
    ``SubshapeSelectionError`` does, so the agent reads one format whether
    the selector missed or the layout did.
    """

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        self.details = dict(details or {})
        super().__init__(str(message))


# ---------------------------------------------------------------------------
# small vector arithmetic, on plain tuples


def _finite(value: Any) -> float:
    if isinstance(value, bool):
        raise TerminalError(f"expected a finite number, not {value!r}")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TerminalError(f"expected a finite number, not {value!r}") from exc
    if not math.isfinite(result):
        raise TerminalError(f"expected a finite number, not {value!r}")
    return result


def _triple(value: Any, *, what: str) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise TerminalError(f"{what} must be [x, y, z]; received {value!r}")
    return tuple(_finite(item) for item in value)  # type: ignore[return-value]


def _length(vector: Sequence[float]) -> float:
    return math.sqrt(sum(float(item) * float(item) for item in vector))


def _unit(vector: Sequence[float], *, what: str) -> tuple[float, float, float]:
    length = _length(vector)
    if length <= _TINY:
        raise TerminalError(f"{what} has no direction; received {list(vector)!r}")
    return (
        float(vector[0]) / length,
        float(vector[1]) / length,
        float(vector[2]) / length,
    )


def _scaled(vector: Sequence[float], factor: float) -> tuple[float, float, float]:
    return (float(vector[0]) * factor, float(vector[1]) * factor, float(vector[2]) * factor)


def _added(first: Sequence[float], second: Sequence[float]) -> tuple[float, float, float]:
    return (
        float(first[0]) + float(second[0]),
        float(first[1]) + float(second[1]),
        float(first[2]) + float(second[2]),
    )


def _dot(first: Sequence[float], second: Sequence[float]) -> float:
    return sum(float(a) * float(b) for a, b in zip(first, second))


def _cross(first: Sequence[float], second: Sequence[float]) -> tuple[float, float, float]:
    return (
        float(first[1]) * float(second[2]) - float(first[2]) * float(second[1]),
        float(first[2]) * float(second[0]) - float(first[0]) * float(second[2]),
        float(first[0]) * float(second[1]) - float(first[1]) * float(second[0]),
    )


def _point_list(vector: Sequence[float]) -> list[float]:
    return [float(vector[0]), float(vector[1]), float(vector[2])]


# ---------------------------------------------------------------------------
# the declarative spec


def _names(value: Any) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, (list, tuple)) or not value:
        raise TerminalError(
            "names must be a non-empty list of signal names, e.g. "
            "['vcc', 'gnd', 'sda', 'scl']; received " + repr(value)
        )
    if len(value) > MAX_TERMINALS:
        raise TerminalError(
            f"a terminal set holds at most {MAX_TERMINALS} terminals; "
            f"received {len(value)}"
        )
    result: list[str] = []
    for index, item in enumerate(value):
        name = str(item or "").strip()
        if not name or len(name) > 64:
            raise TerminalError(
                f"names[{index}] must be 1-64 characters naming the signal; "
                f"received {item!r}"
            )
        if name in result:
            raise TerminalError(
                f"names[{index}] repeats {name!r}; a terminal is looked up by "
                "name, so the names in one set must be distinct"
            )
        result.append(name)
    return tuple(result)


def _layout_entry(value: Any, *, index: int) -> dict[str, Any]:
    """One declared row of terminals, validated into canonical JSON.

    **``hole_dia`` is what says a row is holes; without it the row is pads**
    (ADR-117).  ``depth`` used to be the classifier, and a ``hole_dia`` with
    no ``depth`` was refused — which was sound while the landing was a depth
    down the barrel.  It no longer is: the terminal lands in the mouth, so
    ``depth`` does nothing geometric and cannot classify anything.  It stays
    as an optional descriptive field, because the bore is still that deep and
    the canvas still reports it.
    """

    if not isinstance(value, Mapping) or not value:
        raise TerminalError(
            f"terminals[{index}] must be a layout mapping with origin, axis and "
            "count; received " + repr(value)
        )
    unknown = sorted(set(map(str, value)) - LAYOUT_KEYS)
    if unknown:
        raise TerminalError(
            f"terminals[{index}] has unrecognised layout keys {unknown}; "
            f"allowed: {sorted(LAYOUT_KEYS)}"
        )
    if "origin" not in value or "axis" not in value:
        raise TerminalError(
            f"terminals[{index}] must declare origin and axis — the point the "
            "row starts at and the direction the holes are drilled along"
        )
    origin = _triple(value["origin"], what=f"terminals[{index}].origin")
    axis = _unit(
        _triple(value["axis"], what=f"terminals[{index}].axis"),
        what=f"terminals[{index}].axis",
    )
    count = value.get("count", 1)
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise TerminalError(
            f"terminals[{index}].count must be a positive integer; received {count!r}"
        )
    if count > MAX_TERMINALS:
        raise TerminalError(
            f"terminals[{index}].count must not exceed {MAX_TERMINALS}; "
            f"received {count}"
        )
    depth = _finite(value.get("depth", 0.0))
    if depth < 0.0:
        raise TerminalError(
            f"terminals[{index}].depth must not be negative; received {depth!r}"
        )
    hole_dia = value.get("hole_dia")
    if hole_dia is not None:
        hole_dia = _finite(hole_dia)
        if hole_dia <= 0.0:
            raise TerminalError(
                f"terminals[{index}].hole_dia must be greater than zero; "
                f"received {hole_dia!r}"
            )
    if count > 1:
        if "along" not in value or "pitch" not in value:
            raise TerminalError(
                f"terminals[{index}] declares count={count} but no along/pitch; "
                "a row of terminals needs the direction it runs and its spacing"
            )
        along = _unit(
            _triple(value["along"], what=f"terminals[{index}].along"),
            what=f"terminals[{index}].along",
        )
        pitch = _finite(value["pitch"])
        if pitch <= 0.0:
            raise TerminalError(
                f"terminals[{index}].pitch must be greater than zero; "
                f"received {pitch!r}"
            )
    else:
        along = (
            _unit(
                _triple(value["along"], what=f"terminals[{index}].along"),
                what=f"terminals[{index}].along",
            )
            if "along" in value
            else (0.0, 1.0, 0.0)
        )
        pitch = _finite(value.get("pitch", 0.0))
        if pitch < 0.0:
            raise TerminalError(
                f"terminals[{index}].pitch must not be negative; received {pitch!r}"
            )
    return {
        "origin": list(origin),
        "along": list(along),
        "axis": list(axis),
        "pitch": pitch,
        "count": int(count),
        "depth": depth,
        "hole_dia": hole_dia,
    }


def declared_layout(entries: Any, *, header: Any = None, names: Any) -> dict[str, Any]:
    """The declared form: rows of terminals stated in the component's frame.

    ``header=`` is sugar for a single row — it is the overwhelmingly common
    case and reads better than a one-element list — and expands here so both
    forms go through one piece of layout code rather than two that drift.
    """

    if header is not None and entries is not None:
        raise TerminalError(
            "declare either header= (one row) or terminals= (several), not both"
        )
    rows = [header] if header is not None else entries
    if isinstance(rows, Mapping):
        rows = [rows]
    if not isinstance(rows, (list, tuple)) or not rows:
        raise TerminalError(
            "terminals= expects a non-empty list of layout mappings; received "
            + repr(entries)
        )
    layout_entries = [_layout_entry(row, index=index) for index, row in enumerate(rows)]
    clean_names = _names(names)
    declared = sum(entry["count"] for entry in layout_entries)
    if declared != len(clean_names):
        raise TerminalError(
            f"the declared layout holds {declared} terminals but {len(clean_names)} "
            "names were given; names run over the rows in declaration order",
            details={
                "stage": "terminal_layout",
                "expected_count": len(clean_names),
                "actual_count": declared,
                "names": list(clean_names),
                "layout": layout_entries,
            },
        )
    return {
        "kind": "declared",
        "terminals": layout_entries,
        "names": list(clean_names),
    }


def selector_layout(
    kind: str,
    selector: Mapping[str, Any],
    *,
    exit: Any = None,
    order_by: Any = None,
    names: Any,
) -> dict[str, Any]:
    """The selector form: name the faces, and the geometry supplies the rest.

    ``exit`` is **required for holes**.  A ``Cylinder`` surface gives an axis
    but not which end of it is outward, and inferring that from the solid's
    centre of mass is a heuristic that fails on any board that is not roughly
    symmetric.  Loud beats clever.
    """

    clean_kind = str(kind or "")
    if clean_kind not in SELECTOR_KINDS:
        raise TerminalError(
            f"a selector names {' or '.join(SELECTOR_KINDS)}; received {kind!r}"
        )
    clean_names = _names(names)
    result: dict[str, Any] = {
        "kind": clean_kind,
        "selector": {str(key): value for key, value in dict(selector).items()},
        "names": list(clean_names),
    }
    if exit is None:
        if clean_kind == "holes":
            raise TerminalError(
                "holes= needs exit=: a cylindrical face states an axis but not "
                "which end of it the wire leaves from, and guessing that from "
                "the solid's shape is wrong on any board that is not symmetric"
            )
    else:
        result["exit"] = list(_unit(_triple(exit, what="exit"), what="exit"))
    if order_by is None:
        if len(clean_names) > 1:
            raise TerminalError(
                "order_by= is required when a selector names more than one "
                "terminal: the names are matched to the faces by projecting "
                "them onto that direction, never by kernel enumeration order"
            )
    else:
        result["order_by"] = list(
            _unit(_triple(order_by, what="order_by"), what="order_by")
        )
    return result


# ---------------------------------------------------------------------------
# resolution


def _order_frame(direction: Sequence[float]) -> tuple[tuple[float, float, float], ...]:
    """A right-handed frame whose first axis is ``direction``.

    The secondary axis is derived from the world axis least aligned with the
    primary one, so it is a pure function of ``order_by`` — two terminals at
    the same station along the primary break their tie the same way on every
    run, and on every model that states the same ordering direction.
    """

    primary = _unit(direction, what="order_by")
    seed_axis = min(range(3), key=lambda index: (abs(primary[index]), index))
    seed = [0.0, 0.0, 0.0]
    seed[seed_axis] = 1.0
    projected = _added(seed, _scaled(primary, -_dot(seed, primary)))
    secondary = _unit(projected, what="order_by")
    return primary, secondary, _cross(primary, secondary)


def _order_key(point: Sequence[float], frame, ordinal: int):
    primary, secondary, tertiary = frame
    return (
        round(_dot(point, primary), _ORDER_DECIMALS),
        round(_dot(point, secondary), _ORDER_DECIMALS),
        round(_dot(point, tertiary), _ORDER_DECIMALS),
        # Only reached by two faces indistinguishable to a nanometre in all
        # three axes, where no geometric rule can prefer either.
        int(ordinal),
    )


def _hole_terminal(candidate: Mapping[str, Any], *, name: str, exit_dir) -> dict[str, Any]:
    """One through-hole: the wire lands flush in the mouth the user pointed at.

    ``exit`` is the direction the wire *leaves* along, so the wire arrives from
    that side and stops in the **near** rim's plane — the end with the larger
    projection onto ``exit``.  ADR-117 reversed this.  ADR-062 landed on the
    far face so that two holes wired to each other met in the middle rather
    than each stopping a board thickness short of it; with the landing at the
    mouth there is no middle left to meet in, because the joint is what closes
    the gap and it is at the mouth on both ends.  The gesture the user has is
    "the rim on top of the hole", and the answer they want is "the wire ends
    there".  The bore interior is left empty by design.

    ``depth`` is still measured and still reported — the bore is that deep and
    the canvas says so — but nothing geometric reads it any more: the
    stand-off floor is zero, and the joint's outline is the same one a pad
    gets.  This is the same relation a declared row states directly, where the
    landing point is ``origin`` and the wire leaves along ``-axis``.
    """

    axis = _triple(candidate["axis"], what="hole axis")
    center = _triple(candidate["center"], what="hole center")
    extent = candidate["extent"]
    low_parameter = _finite(extent[0])
    high_parameter = _finite(extent[1])
    unit_axis = _unit(axis, what="hole axis")
    if abs(_dot(unit_axis, exit_dir)) < _EXIT_ALIGNMENT:
        raise TerminalError(
            f"terminal {name!r} sits on a hole whose axis is across exit=, so "
            "there is no end of it the wire leaves from",
            details={
                "stage": "terminal_layout",
                "terminal": name,
                "hole_axis": _point_list(unit_axis),
                "exit": _point_list(exit_dir),
            },
        )
    first = _added(center, _scaled(axis, low_parameter))
    second = _added(center, _scaled(axis, high_parameter))
    if _dot(first, exit_dir) > _dot(second, exit_dir):
        landing = first
    else:
        landing = second
    depth = abs(high_parameter - low_parameter) * _length(axis)
    outward = unit_axis if _dot(unit_axis, exit_dir) > 0.0 else _scaled(unit_axis, -1.0)
    return {
        "name": name,
        "point": _point_list(landing),
        "direction": _point_list(exit_dir),
        # The landing is on the surface the wire arrives at, so its own
        # neighbourhood is the only thing between it and open air — the same
        # position a pad is in, and the same floor.
        "standoff_floor": 0.0,
        "metrics": {
            "kind": "hole",
            "axis": _point_list(outward),
            "radius": float(candidate["radius"]),
            # Measured and reported, read by nothing geometric (ADR-117).
            "depth": depth,
            "entry_point": _point_list(landing),
            "exit_point": _point_list(landing),
        },
    }


def _pad_terminal(
    candidate: Mapping[str, Any], *, name: str, exit_dir
) -> dict[str, Any]:
    """One surface pad: the face's centre of mass, leaving along its normal."""

    center = _triple(candidate["center"], what="pad center")
    normal = _unit(_triple(candidate["normal"], what="pad normal"), what="pad normal")
    if exit_dir is not None and _dot(normal, exit_dir) < 0.0:
        # A face normal's sense follows the face's orientation in the shell,
        # which is not something a script should have to know about.
        normal = _scaled(normal, -1.0)
    return {
        "name": name,
        "point": _point_list(center),
        "direction": _point_list(normal),
        "standoff_floor": 0.0,
        "metrics": {
            "kind": "pad",
            "axis": _point_list(normal),
            "radius": None,
            "depth": 0.0,
            "area": float(candidate.get("area") or 0.0),
            "entry_point": _point_list(center),
            "exit_point": _point_list(center),
        },
    }


def _declared_terminals(layout: Mapping[str, Any]) -> list[dict[str, Any]]:
    names = list(layout["names"])
    rows = list(layout["terminals"])
    declared = sum(int(entry["count"]) for entry in rows)
    if declared != len(names):
        raise TerminalError(
            f"the declared layout holds {declared} terminals but carries "
            f"{len(names)} names",
            details={
                "stage": "terminal_layout",
                "expected_count": len(names),
                "actual_count": declared,
            },
        )
    result: list[dict[str, Any]] = []
    for entry in rows:
        origin = _triple(entry["origin"], what="origin")
        along = _triple(entry["along"], what="along")
        axis = _triple(entry["axis"], what="axis")
        pitch = _finite(entry["pitch"])
        depth = _finite(entry["depth"])
        hole_dia = entry.get("hole_dia")
        for index in range(int(entry["count"])):
            station = _added(origin, _scaled(along, pitch * index))
            result.append(
                {
                    "name": names[len(result)],
                    # The row's ``origin`` *is* the landing (ADR-117): it is
                    # the mouth, on the surface the wire arrives at, and the
                    # bore behind it is left empty.
                    "point": _point_list(station),
                    # The row is drilled *into* the body along ``axis``, so the
                    # wire leaves back along it — the same relation the
                    # selector form's near-face landing has to ``exit``.
                    "direction": _point_list(_scaled(axis, -1.0)),
                    "standoff_floor": 0.0,
                    "metrics": {
                        # ``hole_dia`` is what says this is a hole. ``depth``
                        # used to classify, and cannot any more: it no longer
                        # does anything geometric (ADR-117).
                        "kind": "pad" if hole_dia is None else "hole",
                        "axis": _point_list(_scaled(axis, -1.0)),
                        "radius": None if hole_dia is None else float(hole_dia) / 2.0,
                        "depth": depth,
                        "entry_point": _point_list(station),
                        "exit_point": _point_list(station),
                    },
                }
            )
    return result


def resolve_terminals(
    layout: Mapping[str, Any],
    *,
    candidates: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """One layout to its terminals, in the component's own frame.

    ``candidates`` is what the host extracted from the matched faces — for
    ``holes`` an axis, a centre, a radius and the face's axial parameter
    range; for ``pads`` a centre, a normal and an area.  Declared layouts
    need none of it: they are arithmetic, and they order by declaration.
    """

    kind = str(layout.get("kind") or "")
    if kind == "declared":
        return _declared_terminals(layout)
    if kind not in SELECTOR_KINDS:
        raise TerminalError(f"unknown terminal layout kind {kind!r}")

    names = list(layout["names"])
    entries = list(candidates or [])
    if len(entries) != len(names):
        raise TerminalError(
            f"the selector matched {len(entries)} faces but {len(names)} names "
            "were given",
            details={
                "stage": "terminal_layout",
                "selection": dict(layout.get("selector") or {}),
                "expected_count": len(names),
                "actual_count": len(entries),
                "names": list(names),
                "available": [dict(entry) for entry in entries[:MAX_TERMINALS]],
            },
        )
    exit_dir = (
        _unit(_triple(layout["exit"], what="exit"), what="exit")
        if layout.get("exit") is not None
        else None
    )
    if len(entries) > 1:
        if layout.get("order_by") is None:
            raise TerminalError(
                "more than one matched face and no direction to order them "
                "along; a selector layout carries order_by for exactly this"
            )
        frame = _order_frame(_triple(layout["order_by"], what="order_by"))
        entries = sorted(
            entries,
            key=lambda entry: _order_key(
                _triple(entry["sort_point"], what="sort point"),
                frame,
                entry.get("ordinal", 0),
            ),
        )
    if kind == "holes":
        if exit_dir is None:
            raise TerminalError("a holes= layout resolves only with an exit direction")
        return [
            _hole_terminal(entry, name=name, exit_dir=exit_dir)
            for name, entry in zip(names, entries)
        ]
    return [
        _pad_terminal(entry, name=name, exit_dir=exit_dir)
        for name, entry in zip(names, entries)
    ]


# ---------------------------------------------------------------------------
# placement


def identity_matrix() -> tuple[float, ...]:
    """The 4x4 identity, row-major — what an unplaced component composes to."""

    return (
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    )


def _linear_columns(matrix: Sequence[float]):
    return (
        (float(matrix[0]), float(matrix[4]), float(matrix[8])),
        (float(matrix[1]), float(matrix[5]), float(matrix[9])),
        (float(matrix[2]), float(matrix[6]), float(matrix[10])),
    )


def _uniform_scale(matrix: Sequence[float]) -> float:
    """The one scale factor a placement applies, or a refusal.

    Non-uniform scale is refused rather than applied because it does not act
    on a direction the way it acts on a point: a normal transforms by the
    inverse transpose, so scaling a board 2x in X and 1x in Y would tilt
    every terminal's axis off the hole it belongs to while the points still
    landed correctly.  A terminal that reports an axis it does not have is
    worse than no terminal at all — ``part.solder`` builds a joint from it.
    """

    columns = _linear_columns(matrix)
    lengths = [_length(column) for column in columns]
    if min(lengths) <= _TINY:
        raise TerminalError(
            "the component's placement collapses an axis, so its terminals "
            "have no frame to ride",
            details={"stage": "terminal_placement", "column_lengths": lengths},
        )
    if max(lengths) - min(lengths) > _RIGID_TOLERANCE * max(lengths):
        raise TerminalError(
            "terminals cannot ride a non-uniform scale: a hole scaled by "
            f"{min(lengths):.6g} on one axis and {max(lengths):.6g} on another "
            "is no longer round, and its axis would no longer point along it. "
            "Scale the asset uniformly, or state the layout in the placed frame",
            details={"stage": "terminal_placement", "column_lengths": lengths},
        )
    for first in range(3):
        for second in range(first + 1, 3):
            skew = abs(_dot(columns[first], columns[second]))
            if skew > _RIGID_TOLERANCE * lengths[first] * lengths[second]:
                raise TerminalError(
                    "terminals cannot ride a sheared placement: the component's "
                    "frame is not square, so a hole's axis and its face no "
                    "longer meet at a right angle",
                    details={"stage": "terminal_placement", "shear": skew},
                )
    return sum(lengths) / 3.0


def _transform_point(matrix: Sequence[float], point: Sequence[float]) -> list[float]:
    return [
        float(matrix[0]) * point[0]
        + float(matrix[1]) * point[1]
        + float(matrix[2]) * point[2]
        + float(matrix[3]),
        float(matrix[4]) * point[0]
        + float(matrix[5]) * point[1]
        + float(matrix[6]) * point[2]
        + float(matrix[7]),
        float(matrix[8]) * point[0]
        + float(matrix[9]) * point[1]
        + float(matrix[10]) * point[2]
        + float(matrix[11]),
    ]


def _transform_direction(matrix: Sequence[float], vector: Sequence[float]) -> list[float]:
    rotated = (
        float(matrix[0]) * vector[0] + float(matrix[1]) * vector[1] + float(matrix[2]) * vector[2],
        float(matrix[4]) * vector[0] + float(matrix[5]) * vector[1] + float(matrix[6]) * vector[2],
        float(matrix[8]) * vector[0] + float(matrix[9]) * vector[1] + float(matrix[10]) * vector[2],
    )
    return _point_list(_unit(rotated, what="terminal direction"))


def apply_placement(
    terminals: Iterable[Mapping[str, Any]], matrix: Sequence[float]
) -> list[dict[str, Any]]:
    """Carry terminals from the asset's own frame into the placed one.

    This is what makes define-once/place-many work: one spec, four motors,
    four correct sets of terminals.  **Points transform by the whole matrix
    and directions by its rotation part only** — the distinction ADR-056's
    point-pin work was bitten by, and the reason the suite's transform
    fixture rotates rather than only translating.  Lengths (the depth, the
    radius, the standoff floor) carry the uniform scale.
    """

    values = list(matrix)
    if len(values) != 16:
        raise TerminalError("a placement is a 4x4 matrix of 16 numbers, row-major")
    scale = _uniform_scale(values)
    placed: list[dict[str, Any]] = []
    for terminal in terminals:
        metrics = dict(terminal.get("metrics") or {})
        radius = metrics.get("radius")
        placed.append(
            {
                "name": str(terminal["name"]),
                "point": _transform_point(values, _triple(terminal["point"], what="point")),
                "direction": _transform_direction(
                    values, _triple(terminal["direction"], what="direction")
                ),
                "standoff_floor": float(terminal["standoff_floor"]) * scale,
                "metrics": {
                    **metrics,
                    "axis": _transform_direction(
                        values, _triple(metrics["axis"], what="axis")
                    ),
                    "radius": None if radius is None else float(radius) * scale,
                    "depth": float(metrics.get("depth") or 0.0) * scale,
                    "entry_point": _transform_point(
                        values, _triple(metrics["entry_point"], what="entry_point")
                    ),
                    "exit_point": _transform_point(
                        values, _triple(metrics["exit_point"], what="exit_point")
                    ),
                },
            }
        )
    return placed


# ---------------------------------------------------------------------------
# what a script holds


@dataclass(frozen=True)
class Terminal:
    """One named attachment on one component.

    Never a ``DomainValue``: it carries no output type, it is never built or
    published, and it exists only to be handed to ``part.cable`` or
    ``part.bundle``, which serialise it into their own arguments.
    """

    name: str
    component: Any
    layout: Mapping[str, Any]

    def to_port(self) -> dict[str, Any]:
        """The JSON one end of a cable carries — the component nested inside.

        The component stays the domain value it was; the api's ``_json_value``
        recurses into mappings and turns it into its payload, so a terminal
        needs no special case anywhere in ``cadex_domain_api``.
        """

        return {
            "terminal": str(self.name),
            "component": self.component,
            "layout": dict(self.layout),
        }

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"Terminal({self.name!r})"


class TerminalSet:
    """The named terminals of one component: ``fc['sda']``, not ``fc[4]``."""

    __slots__ = ("_component", "_layout", "_names")

    def __init__(self, component: Any, layout: Mapping[str, Any]) -> None:
        self._component = component
        self._layout = MappingProxyType(dict(layout))
        self._names = tuple(str(name) for name in layout["names"])

    @property
    def names(self) -> tuple[str, ...]:
        return self._names

    @property
    def component(self) -> Any:
        return self._component

    @property
    def layout(self) -> Mapping[str, Any]:
        return self._layout

    def __len__(self) -> int:
        return len(self._names)

    def __iter__(self):
        return (self[name] for name in self._names)

    def __contains__(self, name: Any) -> bool:
        return str(name) in self._names

    def __getitem__(self, name: Any) -> Terminal:
        if isinstance(name, int) and not isinstance(name, bool):
            raise TerminalError(
                "a terminal is named, not numbered: an ordinal would start "
                f"meaning a different pin the moment the layout changed. Use one "
                f"of {list(self._names)}"
            )
        clean = str(name)
        if clean not in self._names:
            raise TerminalError(
                f"this component has no terminal named {clean!r}; it has "
                f"{list(self._names)}",
                details={
                    "stage": "terminal_lookup",
                    "requested": clean,
                    "available": list(self._names),
                },
            )
        return Terminal(name=clean, component=self._component, layout=self._layout)

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"TerminalSet({list(self._names)!r})"
