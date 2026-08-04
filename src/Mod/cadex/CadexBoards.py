# SPDX-License-Identifier: LGPL-2.1-or-later

"""Boards and terminals as a declared table: ``boards``/``board``/``term``
(ADR-120).

``nets(...)`` made the *wires* a table (ADR-065): the script declares the
rows, ``script.json`` holds the editor's overrides, and drift is pruned.
The two things a wire is drawn *between* stayed outside that: a board was
knowable only as a key of ``nets(ports=...)``, and a terminal was free-form
Python — a ``header=``, a ``terminals=[...]`` list, a selector, a
hand-inverted placement chain, whichever the author reached for that day.

That asymmetry is what left a script declaring six terminal sets with an
empty wiring canvas. A ``TerminalSet`` is an inert handle; it reaches the
canvas only when something *consumes* it, so six assigned-and-never-read
handles published nothing at all. And a terminal measured by clicking the
viewport had nowhere to land but a note for the assistant to transcribe.

``boards()`` closes both. It is the same shape ``nets()`` has::

    b = boards({
        "fc": board(fc_board, terminals=[
            term("batt_pos", origin=(12.7279, 0.9, 1.05), axis=(-1, 0, 0)),
            term("esp_vcc", origin=(-12.5724, 8.4287, 1.6),
                 axis=(0.495, 0, -0.87)),
        ]),
        "esp": board(esp32, units="m", terminals=[
            term("vcc", origin=(0.00936066, 0.00099, 0.0015086),
                 axis=(0, -1, 0), hole_dia=0.00075),
        ]),
    })

    harness = nets(ports=b, wires={})
    for name, w in harness.enabled():
        result["wire_" + name] = part.cable(w.a, w.b, gauge_mm=w.gauge)

Four properties carry the module.

**The canonical row is millimetres, in the board's own frame.**
``TERMINAL_FIELDS`` is one shape shared by the declaration, the store and
the ``set_params(boards=...)`` request. ``units="m"`` is a declaration-time
convenience and nothing more: a metre-frame row is multiplied into the
canonical form on the way in and divided back out on the way to the
geometry, so one project can no longer carry two unit systems and a reader
can no longer have to guess which one a row is in.

**``hole_dia`` present means a hole, absent means a pad.**  ADR-117's rule,
unchanged, and the reason ``term()`` takes ``hole_dia`` rather than a kind.

**Stored overrides are a full row list, not a patch** — the ``nets``
property, for the same reason: it is what lets the editor add and delete
terminals rather than only retune the ones the script happened to write.

**A ``boards(...)`` mapping is a mapping of ``TerminalSet``.**  That is the
join that makes everything downstream work unchanged: ``nets(ports=b)``
accepts it as-is, ``b["fc"]["batt_pos"]`` is an ordinary ``Terminal``, and
``part.cable`` never learns that a board is now declared.

Like ``CadexNets``, ``CadexTerminals`` and ``CadexRouting``, this module
imports nothing from FreeCAD and touches no kernel object.  The component is
carried through opaquely; nothing here looks inside it.  The one thing it
cannot do alone is convert a ``frame="world"`` row — that needs the
component's composed placement, which only the worker has, so the collector
takes a callback for it and the pure arithmetic stays here in
:func:`row_from_world`.
"""

from __future__ import annotations

from collections.abc import Mapping as _MappingABC
import math
import re
from typing import Any, Iterator, Mapping, Sequence

from CadexTerminals import (
    MAX_TERMINALS,
    TerminalError,
    TerminalSet,
    declared_layout,
    invert_placement,
    selector_layout,
)

__all__ = [
    "MAX_BOARDS",
    "MAX_TERMINALS",
    "TERMINAL_FIELDS",
    "UNITS",
    "BoardError",
    "BoardValues",
    "BoardsCollector",
    "board",
    "boards",
    "canonical_terminal_rows",
    "declared_boards",
    "declared_rows",
    "effective_terminals",
    "prune_terminal_rows",
    "row_from_world",
    "term",
]

#: One project's board count.  A board is a node on the canvas and every one
#: of them resolves its terminals on every run, so this is bounded for the
#: same reason ``MAX_NETS`` is: a project that declares more boards than a
#: person can see at once meant something else.
MAX_BOARDS = 64

#: Board and terminal names, the same rule ``params()`` and ``nets()`` apply.
#: A terminal name is the right half of every ``<board>.<terminal>`` address.
_NAME = re.compile(r"^[a-z_][a-z0-9_]{0,63}$")

#: What ``term()`` and ``board()`` return, so ``boards()`` can tell a
#: declaration from a dict that merely looks like one.  Same idiom as
#: ``wire()``'s marker, and ``num()``'s before it.
_TERM_MARKER = "cadex-project-term-spec"
_BOARD_MARKER = "cadex-project-board-spec"

#: The row fields the editor may write, and their order in canonical JSON.
#: ``board`` is the left half of the address and ``name`` the right; the four
#: after them are the measurement.
TERMINAL_FIELDS = ("board", "name", "origin", "axis", "hole_dia", "depth")

#: Declaration units, and the factor that carries one into the canonical
#: millimetre row.  Nothing else is accepted: inches would need a rounding
#: rule of their own and no asset in this codebase is stated in them.
UNITS = {"mm": 1.0, "m": 1000.0}

#: Below this a direction has no direction.
_TINY = 1.0e-12


class BoardError(ValueError):
    """A board table that could not be stated, or could not be applied."""

    def __init__(
        self, message: str, *, details: Mapping[str, Any] | None = None
    ) -> None:
        self.details = dict(details or {})
        super().__init__(str(message))


# ---------------------------------------------------------------------------
# small helpers, on plain numbers


def _finite(value: Any, *, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BoardError(f"{what} must be a number; received {value!r}")
    result = float(value)
    if not math.isfinite(result):
        raise BoardError(f"{what} must be finite; received {value!r}")
    return result


def _triple(value: Any, *, what: str) -> list[float]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise BoardError(f"{what} must be [x, y, z]; received {value!r}")
    if len(value) != 3:
        raise BoardError(f"{what} must be [x, y, z]; received {value!r}")
    return [_finite(item, what=f"{what}[{index}]") for index, item in enumerate(value)]


def _unit(value: Any, *, what: str) -> list[float]:
    vector = _triple(value, what=what)
    length = math.sqrt(sum(item * item for item in vector))
    if length <= _TINY:
        raise BoardError(f"{what} has no direction; received {value!r}")
    return [item / length for item in vector]


def _name(value: Any, *, what: str) -> str:
    clean = str(value or "")
    if not _NAME.fullmatch(clean):
        raise BoardError(
            f"{what} {clean!r} must be lower_snake_case (max 64 chars); it is "
            "half of every '<board>.<terminal>' address"
        )
    return clean


def _units(value: Any, *, what: str) -> str:
    clean = str(value or "")
    if clean not in UNITS:
        raise BoardError(
            f"{what} must be one of {sorted(UNITS)}; received {value!r}. Rows "
            "are stored in millimetres whichever is declared, so this states "
            "what the numbers in the script are in and nothing more"
        )
    return clean


def _optional_length(value: Any, *, what: str, positive: bool) -> float | None:
    if value is None:
        return None
    result = _finite(value, what=what)
    if positive and result <= 0.0:
        raise BoardError(f"{what} must be greater than zero; received {value!r}")
    if not positive and result < 0.0:
        raise BoardError(f"{what} must not be negative; received {value!r}")
    return result


# ---------------------------------------------------------------------------
# declaration


def term(
    name: str,
    *,
    origin: Sequence[float],
    axis: Sequence[float],
    hole_dia: float | None = None,
    depth: float | None = None,
) -> dict[str, Any]:
    """Declare one terminal on one board.

    ``origin`` is where the wire lands — the mouth of the hole or the centre
    of the pad, in the board's own frame — and ``axis`` is the direction it
    is drilled *into* the body, so the wire leaves back along ``-axis``.
    That is the same relation ``part.terminals``' declared row states, and it
    is deliberately the same words: this replaces that form, it does not
    reinterpret it.

    **``hole_dia`` is what makes this a hole** (ADR-117); without one it is a
    pad.  ``depth`` is optional and descriptive — the bore is that deep and
    the canvas reports it, and nothing geometric reads it.
    """

    return {
        "kind": _TERM_MARKER,
        "name": _name(name, what="term() name"),
        "origin": _triple(origin, what=f"term({name!r}) origin"),
        "axis": _unit(axis, what=f"term({name!r}) axis"),
        "hole_dia": _optional_length(
            hole_dia, what=f"term({name!r}) hole_dia", positive=True
        ),
        "depth": _optional_length(
            depth, what=f"term({name!r}) depth", positive=False
        ),
    }


def board(
    component: Any,
    *,
    terminals: Sequence[Mapping[str, Any]] | None = None,
    header: Mapping[str, Any] | None = None,
    holes: Mapping[str, Any] | None = None,
    pads: Mapping[str, Any] | None = None,
    exit: Sequence[float] | None = None,
    order_by: Sequence[float] | None = None,
    names: Sequence[str] | None = None,
    units: str = "mm",
) -> dict[str, Any]:
    """Declare one board: a component, and the terminals measured on it.

    Four forms, and only the first is a table the editor can author.

    - ``terminals=[term(...), ...]`` — the canonical form.  Each row is one
      measurement, named, and it round-trips through ``script.json``.
    - ``header=dict(origin=..., along=..., pitch=..., count=...)`` with
      ``names=`` — the generative form ``part.terminals`` already takes.  It
      is **expanded to explicit rows here**, so what the store holds is
      always flat and the editor never has to understand a pitch.
    - ``holes=``/``pads=`` with ``names=`` — an ADR-029 selector.  Its rows
      are derived from the shape on every run, so they are *read-only* in the
      editor: there is nothing an override could address that the geometry
      would not overwrite.
    - nothing at all — a board with no terminals yet, which is a legitimate
      thing to declare and is exactly what the pick gesture fills in.

    ``units="m"`` states what the numbers in *this* declaration are in.  The
    stored row is millimetres either way.
    """

    forms = {"terminals": terminals, "header": header, "holes": holes, "pads": pads}
    given = sorted(key for key, value in forms.items() if value is not None)
    if len(given) > 1:
        raise BoardError(
            "a board states at most one of terminals= (explicit rows), header= "
            "(one generative row), holes= or pads= (a selector); received "
            f"{given}"
        )
    spec: dict[str, Any] = {
        "kind": _BOARD_MARKER,
        "component": component,
        "units": _units(units, what="board() units"),
        "selector": False,
        "rows": [],
        "layout": None,
    }
    form = given[0] if given else ""
    if form in {"holes", "pads"}:
        if not isinstance(names, (list, tuple)) or isinstance(names, str) or not names:
            raise BoardError(
                f"board({form}=...) needs names=: a selector names faces, and "
                "the names are what a wire addresses them by"
            )
        try:
            spec["layout"] = selector_layout(
                form,
                dict(forms[form] or {}),
                exit=exit,
                order_by=order_by,
                names=names,
            )
        except TerminalError as exc:
            raise BoardError(str(exc), details=getattr(exc, "details", None)) from exc
        spec["selector"] = True
        return spec
    if exit is not None or order_by is not None:
        raise BoardError(
            "exit= and order_by= belong to a selector; a declared row already "
            "states its own axis and its own order"
        )
    if form == "header":
        spec["rows"] = _rows_from_header(header, names)
    elif form == "terminals":
        spec["rows"] = _rows_from_terms(terminals, names)
    elif names is not None:
        raise BoardError(
            "names= names the faces a selector matched or the terminals a "
            "header generates; an explicit terminals=[term(...)] list already "
            "carries its names"
        )
    return spec


def _rows_from_terms(entries: Any, names: Any) -> list[dict[str, Any]]:
    if names is not None:
        raise BoardError(
            "board(terminals=[term(...)]) rows already carry their names; "
            "names= is for the header and selector forms"
        )
    if isinstance(entries, Mapping) or not isinstance(entries, (list, tuple)):
        raise BoardError(
            "board(terminals=...) expects a list of term(...) rows; received "
            f"{entries!r}"
        )
    rows: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping) or entry.get("kind") != _TERM_MARKER:
            raise BoardError(
                f"board(terminals=...)[{index}] must be declared with term(...); "
                f"received {entry!r}"
            )
        rows.append({key: entry[key] for key in TERMINAL_FIELDS if key != "board"})
    return rows


def _rows_from_header(header: Any, names: Any) -> list[dict[str, Any]]:
    """One generative row, expanded to explicit rows at declaration.

    ``declared_layout`` is what validates and steps it — the same code
    ``part.terminals(header=...)`` goes through, so the two forms cannot
    drift.  What is different here is that the expansion is *kept*: the
    store never holds a pitch and a count, because a table whose row count
    depends on another column is not a table the editor can edit.
    """

    try:
        layout = declared_layout(None, header=dict(header or {}), names=names)
    except TerminalError as exc:
        raise BoardError(str(exc), details=getattr(exc, "details", None)) from exc
    row = dict(layout["terminals"][0])
    origin = list(row["origin"])
    along = list(row["along"])
    pitch = float(row["pitch"])
    rows: list[dict[str, Any]] = []
    for index, name in enumerate(layout["names"]):
        rows.append(
            {
                "name": _name(name, what="board(names=...) entry"),
                "origin": [
                    origin[axis] + along[axis] * pitch * index for axis in range(3)
                ],
                "axis": list(row["axis"]),
                "hole_dia": row.get("hole_dia"),
                "depth": row.get("depth") or None,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# rows: the canonical JSON a declaration, a store and a request share


def canonical_terminal_rows(
    rows: Any, *, what: str, allow_world: bool = False
) -> list[dict[str, Any]]:
    """Validate a full terminal-row list into canonical JSON, or refuse it.

    Shared by the declared table, the stored overrides and the host-side
    ``set_params(boards=...)`` check, so all three agree on what a row is.

    ``allow_world`` admits the one extra key a *request* may carry: a row
    measured in the viewport arrives as ``frame="world"`` because the shell
    has no way to know a board's own frame.  ``cadexd`` cannot convert it —
    it has no geometry and never runs user code — so the key survives into
    the staged values and the worker converts it there (ADR-120).
    """

    if isinstance(rows, Mapping) or not isinstance(rows, (list, tuple)):
        raise BoardError(f"{what} must be a list of terminal rows; received {rows!r}")
    if len(rows) > MAX_BOARDS * MAX_TERMINALS:
        raise BoardError(
            f"{what} holds {len(rows)} rows, past every bound this table has"
        )
    allowed = set(TERMINAL_FIELDS) | ({"frame"} if allow_world else set())
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    counts: dict[str, int] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise BoardError(f"{what}[{index}] must be an object; received {row!r}")
        unknown = sorted(set(map(str, row)) - allowed)
        if unknown:
            raise BoardError(
                f"{what}[{index}] has unrecognised keys {unknown}; a row carries "
                f"{list(TERMINAL_FIELDS)}"
            )
        board_name = _name(row.get("board"), what=f"{what}[{index}].board")
        name = _name(row.get("name"), what=f"{what}[{index}].name")
        if (board_name, name) in seen:
            raise BoardError(
                f"{what}[{index}] repeats terminal {name!r} on board "
                f"{board_name!r}; a terminal is looked up by name, so the names "
                "on one board must be distinct"
            )
        seen.add((board_name, name))
        counts[board_name] = counts.get(board_name, 0) + 1
        if counts[board_name] > MAX_TERMINALS:
            raise BoardError(
                f"board {board_name!r} holds more than {MAX_TERMINALS} terminals"
            )
        entry: dict[str, Any] = {
            "board": board_name,
            "name": name,
            "origin": _triple(row.get("origin"), what=f"{what}[{index}].origin"),
            "axis": _unit(row.get("axis"), what=f"{what}[{index}].axis"),
            "hole_dia": _optional_length(
                row.get("hole_dia"), what=f"{what}[{index}].hole_dia", positive=True
            ),
            "depth": _optional_length(
                row.get("depth"), what=f"{what}[{index}].depth", positive=False
            ),
        }
        frame = row.get("frame")
        if frame is not None:
            if str(frame) not in {"world", "board"}:
                raise BoardError(
                    f"{what}[{index}].frame is 'world' (measured in the "
                    f"viewport) or absent (the board's own frame); received "
                    f"{frame!r}"
                )
            if str(frame) == "world":
                entry["frame"] = "world"
        result.append(entry)
    return result


def declared_boards(specs: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    """``{board name: entry}`` from a stored ``board_specs`` block."""

    result: dict[str, dict[str, Any]] = {}
    for entry in list((specs or {}).get("boards") or []):
        if not isinstance(entry, Mapping):
            continue
        name = str(entry.get("name") or "")
        if name:
            result[name] = dict(entry)
    return result


def declared_rows(specs: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Every declared terminal row, flattened and stamped with its board."""

    rows: list[dict[str, Any]] = []
    for name, entry in declared_boards(specs).items():
        for row in list(entry.get("terminals") or []):
            if isinstance(row, Mapping):
                rows.append({**dict(row), "board": name})
    return rows


def prune_terminal_rows(
    rows: Sequence[Mapping[str, Any]], specs: Mapping[str, Any] | None
) -> list[dict[str, Any]]:
    """Drop rows whose board the script no longer declares (ADR-039).

    A stored row is not a caller error the way a bad request is: it is what a
    rewritten script leaves behind.  Raising on it would wedge the editor
    forever the moment the AI renamed a board — the same failure ADR-039
    recorded for parameters, and ``CadexNets.prune_rows`` for wires.

    A **selector** board is pruned wholesale, whatever its rows say: its
    terminals are derived from the shape on every run, so an override there
    is not an edit, it is a stale copy of something the geometry owns.
    """

    boards_by_name = declared_boards(specs)
    kept: list[dict[str, Any]] = []
    for row in rows:
        entry = boards_by_name.get(str(row.get("board") or ""))
        if entry is None or entry.get("selector"):
            continue
        kept.append(dict(row))
    return kept


def effective_terminals(
    specs: Mapping[str, Any] | None, values: Any
) -> list[dict[str, Any]]:
    """The table as built: stored overrides when there are any, else declared.

    A **full row list**, never a patch — the ``nets`` property, and what lets
    the editor add and delete terminals.  Selector boards are never in the
    override half: their rows come back from the declaration every time, so
    they are appended after the pruning rather than replaced by it.
    """

    if not values:
        return declared_rows(specs)
    boards_by_name = declared_boards(specs)
    overrides = prune_terminal_rows(
        canonical_terminal_rows(values, what="board values"), specs
    )
    derived = [
        row
        for row in declared_rows(specs)
        if (boards_by_name.get(str(row.get("board") or "")) or {}).get("selector")
    ]
    return overrides + derived


# ---------------------------------------------------------------------------
# the world-frame round trip


def row_from_world(
    row: Mapping[str, Any], matrix: Sequence[float], *, units: str = "mm"
) -> dict[str, Any]:
    """One ``frame="world"`` row, carried back into its board's own frame.

    The shell measures in world coordinates because that is the only frame a
    viewport click has.  A board's rows are in the asset's own frame, and
    before this the bridge between them was a person inverting a placement
    chain by hand and pasting the result into the script — which is where
    every magic literal in the V06 chassis came from.

    ``matrix`` is the composed placement the run resolved for this
    component, so the inverse of it is exact rather than reconstructed.  A
    non-uniform scale on that chain refuses **this row** with a named error
    rather than skewing its axis: the refusal already existed in
    ``CadexTerminals`` and was previously worked around by declaring a
    stand-in component; now it reaches the editor as a sentence.
    """

    inverse = invert_placement(matrix)
    factor = UNITS[_units(units, what="board units")]
    origin = _triple(row.get("origin"), what="row origin")
    axis = _unit(row.get("axis"), what="row axis")
    placed_origin = [
        inverse[0 + 4 * axis_index] * origin[0]
        + inverse[1 + 4 * axis_index] * origin[1]
        + inverse[2 + 4 * axis_index] * origin[2]
        + inverse[3 + 4 * axis_index]
        for axis_index in range(3)
    ]
    placed_axis = [
        inverse[0 + 4 * axis_index] * axis[0]
        + inverse[1 + 4 * axis_index] * axis[1]
        + inverse[2 + 4 * axis_index] * axis[2]
        for axis_index in range(3)
    ]
    # The inverse carries 1/scale, so a length measured in world millimetres
    # comes back in the asset's own units; the canonical row is millimetres in
    # the declaration frame, so it goes back out through the same factor the
    # declared rows came in through.
    scale = math.sqrt(sum(item * item for item in placed_axis))
    if scale <= _TINY:
        raise BoardError("the component's placement collapses an axis")
    lengths = {}
    for key in ("hole_dia", "depth"):
        value = row.get(key)
        lengths[key] = None if value is None else float(value) * scale * factor
    result = {
        "board": str(row.get("board") or ""),
        "name": str(row.get("name") or ""),
        "origin": [value * factor for value in placed_origin],
        "axis": [value / scale for value in placed_axis],
        "hole_dia": lengths["hole_dia"],
        "depth": lengths["depth"],
    }
    return canonical_terminal_rows([result], what="converted row")[0]


# ---------------------------------------------------------------------------
# what a script holds


class BoardValues(_MappingABC):
    """Ordered, immutable mapping of board name to its ``TerminalSet``.

    Exactly what ``nets(ports=...)`` already takes, so the join between the
    two tables is that this *is* a mapping of terminal sets and needs no
    adapter: ``NetsCollector._clean_ports`` reads ``.names`` and
    ``.component`` off each entry and never asks where it came from.  It is a
    real :class:`~collections.abc.Mapping` for exactly that reason — the
    collector type-checks its ports, and ``boards()`` has to pass that check
    without ``nets()`` learning what a board is.
    """

    __slots__ = ("_sets", "_specs")

    def __init__(
        self, sets: Mapping[str, TerminalSet], specs: Mapping[str, Any]
    ) -> None:
        object.__setattr__(self, "_sets", dict(sets))
        object.__setattr__(self, "_specs", dict(specs))

    @property
    def specs(self) -> dict[str, Any]:
        return dict(self._specs)

    def names(self) -> tuple[str, ...]:
        return tuple(self._sets)

    def items(self) -> tuple[tuple[str, TerminalSet], ...]:
        return tuple(self._sets.items())

    def values(self) -> tuple[TerminalSet, ...]:
        return tuple(self._sets.values())

    def keys(self) -> tuple[str, ...]:
        return tuple(self._sets)

    def get(self, name: Any, default: Any = None) -> Any:
        return self._sets.get(str(name), default)

    def __len__(self) -> int:
        return len(self._sets)

    def __iter__(self) -> Iterator[str]:
        return iter(self._sets)

    def __contains__(self, name: Any) -> bool:
        return str(name) in self._sets

    def __getitem__(self, name: Any) -> TerminalSet:
        clean = str(name)
        if clean not in self._sets:
            raise BoardError(
                f"this script declares no board named {clean!r}; it declares "
                f"{list(self._sets)}"
            )
        return self._sets[clean]

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("The board table is immutable inside the script.")

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"BoardValues({list(self._sets)!r})"


class BoardsCollector:
    """The ``boards(...)`` callable: collects specs, applies stored rows.

    The exact shape of :class:`~CadexNets.NetsCollector`, because a board and
    a wire are the same kind of thing: a table the script declares and
    something outside it currently sets.

    ``placement`` is the one thing this collector needs that the nets one
    does not: a callable from a component to its composed 4x4, used only to
    convert a ``frame="world"`` row.  It is supplied by the worker (which is
    the only process that can answer it) and absent everywhere else, where a
    world row is simply refused rather than silently mis-placed.
    """

    def __init__(self, overrides: Any = None, placement: Any = None) -> None:
        self.overrides = overrides
        self.placement = placement
        self.specs: dict[str, Any] = {}
        #: ``[(board name, TerminalSet)]`` in declaration order — the exact
        #: shape ``NetsCollector.ports`` has, because the worker joins the
        #: published registry to both tables the same way and one shape means
        #: one join.
        self.sets: list[tuple[str, TerminalSet]] = []
        #: Rows converted out of world coordinates on this run, canonical and
        #: board-frame.  ``validate_project_result`` writes them back into
        #: ``board_values`` so the conversion happens exactly once (ADR-120).
        self.converted: list[dict[str, Any]] = []
        self._called = False

    def __call__(self, mapping: Any) -> BoardValues:
        if self._called:
            raise BoardError("boards(...) may be called at most once per script.")
        self._called = True
        declared = self._clean(mapping)
        self.specs = {
            "boards": [
                {
                    "name": name,
                    "units": entry["units"],
                    "selector": bool(entry["selector"]),
                    "terminals": [
                        {key: row[key] for key in TERMINAL_FIELDS if key != "board"}
                        for row in entry["rows"]
                    ],
                }
                for name, entry in declared.items()
            ]
        }
        rows = effective_terminals(self.specs, self._resolved_overrides(declared))
        by_board: dict[str, list[dict[str, Any]]] = {name: [] for name in declared}
        for row in rows:
            by_board.setdefault(str(row.get("board") or ""), []).append(row)
        sets: dict[str, TerminalSet] = {}
        for name, entry in declared.items():
            sets[name] = self._terminal_set(name, entry, by_board.get(name) or [])
        self.sets = list(sets.items())
        return BoardValues(sets, self.specs)

    # -- helpers ----------------------------------------------------------

    def _clean(self, mapping: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(mapping, Mapping) or not mapping:
            raise BoardError(
                "boards(...) expects a non-empty mapping of board name to "
                f"board(...); received {mapping!r}"
            )
        if len(mapping) > MAX_BOARDS:
            raise BoardError(
                f"boards(...) declares {len(mapping)} boards; a project "
                f"declares at most {MAX_BOARDS}"
            )
        declared: dict[str, dict[str, Any]] = {}
        for name, spec in mapping.items():
            clean_name = _name(name, what="board name")
            if not isinstance(spec, Mapping) or spec.get("kind") != _BOARD_MARKER:
                raise BoardError(
                    f"board {clean_name!r} must be declared with board(...); "
                    f"received {spec!r}"
                )
            entry = dict(spec)
            entry["rows"] = canonical_terminal_rows(
                [{**dict(row), "board": clean_name} for row in entry["rows"]],
                what=f"board({clean_name!r})",
            )
            entry["rows"] = [
                self._to_canonical_units(row, entry["units"]) for row in entry["rows"]
            ]
            if not entry["rows"] and not entry["selector"]:
                # Refused at *declaration*, not after the merge: an override
                # list that happens to mention no terminal on this board means
                # the editor deleted them all, which is a legitimate state and
                # draws as an empty node.
                raise BoardError(
                    f"board {clean_name!r} declares no terminals; give it "
                    "terminals=[term(...)], a header=, or a selector"
                )
            declared[clean_name] = entry
        return declared

    @staticmethod
    def _to_canonical_units(row: Mapping[str, Any], units: str) -> dict[str, Any]:
        """A declared row into the canonical millimetre form.

        The declaration is written in whatever the asset is modelled in; the
        table is millimetres.  Doing this here rather than at the edges is
        what makes ``units=`` a spelling convenience and not a second unit
        system leaking into the store (ADR-120).
        """

        factor = UNITS[units]
        if factor == 1.0:
            return dict(row)
        scaled = dict(row)
        scaled["origin"] = [value * factor for value in row["origin"]]
        for key in ("hole_dia", "depth"):
            value = row.get(key)
            scaled[key] = None if value is None else float(value) * factor
        return scaled

    def _resolved_overrides(self, declared: Mapping[str, dict[str, Any]]) -> Any:
        """Stored rows, with every world-frame row converted exactly once."""

        rows = self.overrides
        if not rows:
            return rows
        resolved: list[dict[str, Any]] = []
        for row in canonical_terminal_rows(
            rows, what="board values", allow_world=True
        ):
            if row.get("frame") != "world":
                resolved.append(row)
                continue
            entry = declared.get(str(row.get("board") or ""))
            if entry is None:
                # A world row naming a board the script no longer declares is
                # dropped by the same rule every stale stored row is: the
                # pruning below would drop it anyway, and converting it first
                # would need a component that is not there.
                continue
            if self.placement is None:
                raise BoardError(
                    f"terminal {row.get('name')!r} on board "
                    f"{row.get('board')!r} was measured in world coordinates, "
                    "and this process cannot resolve the board's placement to "
                    "convert it"
                )
            try:
                converted = row_from_world(
                    row, self.placement(entry["component"]), units=entry["units"]
                )
            except TerminalError as exc:
                raise BoardError(
                    f"terminal {row.get('name')!r} on board "
                    f"{row.get('board')!r} was measured in the viewport and "
                    f"cannot be carried into that board's own frame: {exc}",
                    details=getattr(exc, "details", None),
                ) from exc
            # Stored in the declaration's units on the way to the geometry,
            # canonical millimetres on the way back to the store.
            resolved.append(converted)
            self.converted.append(converted)
        return resolved

    def _terminal_set(
        self, name: str, entry: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]
    ) -> TerminalSet:
        """One board's ``TerminalSet``, in the units its component is in.

        The canonical row is millimetres; the geometry is in whatever the
        asset is modelled in, so the factor is divided back out here.  A
        board is one ``TerminalSet`` — one memo key, one node on the canvas —
        so the rows become one ``terminals=[...]`` layout rather than one per
        row.
        """

        if entry.get("selector"):
            return TerminalSet(entry["component"], entry["layout"])
        if not rows:
            # Every terminal deleted from the canvas: an empty node, which is
            # a state the editor can be in and must be able to get out of.
            # ``declared_layout`` will not state it (a layout needs a row), so
            # the empty layout is constructed here rather than refused.
            return TerminalSet(
                entry["component"],
                {"kind": "declared", "terminals": [], "names": []},
            )
        factor = UNITS[str(entry.get("units") or "mm")]
        layout_rows = []
        for row in rows:
            layout_row: dict[str, Any] = {
                "origin": [value / factor for value in row["origin"]],
                "axis": list(row["axis"]),
                "count": 1,
            }
            if row.get("hole_dia") is not None:
                layout_row["hole_dia"] = float(row["hole_dia"]) / factor
            if row.get("depth") is not None:
                layout_row["depth"] = float(row["depth"]) / factor
            layout_rows.append(layout_row)
        try:
            layout = declared_layout(
                layout_rows, names=[str(row["name"]) for row in rows]
            )
        except TerminalError as exc:
            raise BoardError(
                f"board {name!r}: {exc}", details=getattr(exc, "details", None)
            ) from exc
        return TerminalSet(entry["component"], layout)


def boards(mapping: Any) -> BoardValues:  # pragma: no cover - staged form
    """The bare declaration, for a script run outside a collector.

    The worker stages a :class:`BoardsCollector` under this name, which is
    what applies the stored overrides.  This exists so the vocabulary can be
    imported and exercised on its own.
    """

    return BoardsCollector()(mapping)
