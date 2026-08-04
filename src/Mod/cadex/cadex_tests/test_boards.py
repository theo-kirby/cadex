# SPDX-License-Identifier: LGPL-2.1-or-later

"""The board table: ``boards(...)``, ``board(...)`` and ``term(...)`` (ADR-120).

``nets(...)`` made the wires a table.  The two things a wire is drawn
*between* stayed outside it — a board was knowable only as a key of
``nets(ports=...)``, and a terminal was free-form Python — and that is what
left a script declaring six terminal sets with an empty wiring canvas.

``CadexBoards`` imports nothing from FreeCAD, so everything here runs against
plain numbers and opaque component stand-ins, on the same footing
``test_nets.py`` runs on.  What is checked is the vocabulary, every refusal
it makes, and the four properties the editor depends on: the canonical row is
millimetres in the board's own frame whatever the declaration was written in,
a stored row list *replaces* the declared table, a stored row the script no
longer supports is dropped rather than raised on, and a row measured in the
viewport converts through the component's placement exactly once.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess

import pytest

from CadexBoards import (
    MAX_BOARDS,
    TERMINAL_FIELDS,
    BoardError,
    BoardsCollector,
    BoardValues,
    board,
    boards,
    canonical_terminal_rows,
    declared_boards,
    declared_rows,
    effective_terminals,
    prune_terminal_rows,
    row_from_world,
    term,
)
from CadexTerminals import Terminal, TerminalError, TerminalSet, invert_placement


FC = "FC-BOARD"
ESP = "ESP-BOARD"


def _fc(**overrides):
    spec = dict(
        terminals=[
            term("batt_pos", origin=(12.7279, 0.9, 1.05), axis=(-1, 0, 0)),
            term("esp_vcc", origin=(-12.5724, 8.4287, 1.6), axis=(0.495, 0, -0.87),
                 hole_dia=0.8, depth=1.6),
        ]
    )
    spec.update(overrides)
    return board(FC, **spec)


def _esp():
    return board(
        ESP,
        units="m",
        terminals=[
            term("vcc", origin=(0.00936066, 0.00099, 0.0015086), axis=(0, -1, 0),
                 hole_dia=0.00075),
            term("d4", origin=(0.00936066, -0.00155, 0.0015086), axis=(0, -1, 0)),
        ],
    )


def _table(overrides=None, placement=None):
    collector = BoardsCollector(overrides, placement)
    return collector, collector({"fc": _fc(), "esp": _esp()})


def _row(board_name: str, name: str, **overrides):
    row = {
        "board": board_name,
        "name": name,
        "origin": [1.0, 2.0, 3.0],
        "axis": [0.0, 0.0, 1.0],
    }
    row.update(overrides)
    return row


# --------------------------------------------------------------------------
# declaration
# --------------------------------------------------------------------------


def test_a_declared_board_is_a_terminal_set_nets_already_takes() -> None:
    """The join: ``nets(ports=b)`` needs no adapter and ``b['fc']['x']`` is a
    Terminal, so ``part.cable`` never learns that a board is now declared."""

    _collector, table = _table()

    assert isinstance(table, BoardValues)
    assert table.names() == ("fc", "esp")
    assert isinstance(table["fc"], TerminalSet)
    assert table["fc"].names == ("batt_pos", "esp_vcc")
    assert table["fc"].component == FC
    terminal = table["fc"]["batt_pos"]
    assert isinstance(terminal, Terminal)
    assert terminal.name == "batt_pos" and terminal.component == FC
    # What NetsCollector._clean_ports reads off each entry, and all it reads.
    for name, entry in table.items():
        assert hasattr(entry, "names") and hasattr(entry, "component"), name


def test_the_spec_cache_is_json_and_flat() -> None:
    """``board_specs`` rides in script.json and feeds the revision hash."""

    collector, _built = _table()
    encoded = json.dumps(collector.specs, sort_keys=True)
    assert json.loads(encoded) == collector.specs

    entries = {entry["name"]: entry for entry in collector.specs["boards"]}
    assert sorted(entries) == ["esp", "fc"]
    assert entries["fc"]["units"] == "mm" and entries["fc"]["selector"] is False
    assert entries["fc"]["terminals"][0] == {
        "name": "batt_pos",
        "origin": [12.7279, 0.9, 1.05],
        "axis": [-1.0, 0.0, 0.0],
        "hole_dia": None,
        "depth": None,
    }
    # The component itself is never in the cache: it is a DomainValue, and the
    # cache is JSON that feeds a digest.
    assert "component" not in entries["fc"]


def test_a_metre_declaration_is_stored_in_millimetres() -> None:
    """``units="m"`` is a spelling convenience, not a second unit system.

    This is the property V06 could not have: FC rows in mm and ESP rows in
    metres in one file, with nothing but a comment saying which.
    """

    collector, table = _table()
    entries = {entry["name"]: entry for entry in collector.specs["boards"]}
    stored = entries["esp"]["terminals"][0]
    assert stored["origin"] == pytest.approx([9.36066, 0.99, 1.5086])
    assert stored["hole_dia"] == pytest.approx(0.75)
    assert entries["esp"]["units"] == "m"

    # ...and the geometry still sees the asset's own numbers, so a converted
    # script builds byte-identically to the one it replaces.
    layout = table["esp"].layout["terminals"][0]
    assert layout["origin"] == pytest.approx([0.00936066, 0.00099, 0.0015086])
    assert layout["hole_dia"] == pytest.approx(0.00075)


def test_a_header_is_expanded_to_explicit_rows_at_declaration() -> None:
    """The store never holds a pitch: a row count that depends on another
    column is not a table the editor can edit."""

    collector = BoardsCollector()
    collector(
        {
            "hdr": board(
                "H",
                header=dict(
                    origin=(0.0, 0.0, 1.6),
                    along=(0.0, 1.0, 0.0),
                    axis=(0.0, 0.0, -1.0),
                    pitch=2.54,
                    count=3,
                    hole_dia=1.0,
                    depth=1.6,
                ),
                names=["sda", "scl", "gnd"],
            )
        }
    )

    rows = collector.specs["boards"][0]["terminals"]
    assert [row["name"] for row in rows] == ["sda", "scl", "gnd"]
    assert [round(row["origin"][1], 4) for row in rows] == [0.0, 2.54, 5.08]
    assert all(row["origin"][2] == pytest.approx(1.6) for row in rows)
    assert all(row["hole_dia"] == pytest.approx(1.0) for row in rows)
    assert all(set(row) == set(TERMINAL_FIELDS) - {"board"} for row in rows)


def test_a_selector_board_stays_declared_by_selector_and_is_read_only() -> None:
    """Its rows are derived from the shape on every run, so there is nothing
    an override could address that the geometry would not overwrite."""

    collector = BoardsCollector()
    table = collector(
        {
            "fc": board(
                "SHAPE",
                holes={"geometry_type": "Cylinder", "radius": 0.5},
                exit=(0, 0, 1),
                order_by=(1, 0, 0),
                names=["a", "b"],
            )
        }
    )

    entry = collector.specs["boards"][0]
    assert entry["selector"] is True and entry["terminals"] == []
    assert table["fc"].layout["kind"] == "holes"
    assert table["fc"].names == ("a", "b")


def test_hole_dia_is_what_says_a_row_is_a_hole() -> None:
    """ADR-117's rule, unchanged, and why term() takes no kind."""

    _collector, table = _table()
    layout = table["fc"].layout
    rows = dict(zip(layout["names"], layout["terminals"]))
    assert rows["batt_pos"]["hole_dia"] is None
    assert rows["esp_vcc"]["hole_dia"] == pytest.approx(0.8)


def test_the_table_is_immutable_and_callable_once() -> None:
    collector, table = _table()
    with pytest.raises(TypeError):
        table.boards = {}
    with pytest.raises(BoardError, match="at most once"):
        collector({"fc": _fc()})


def test_the_declared_axis_is_normalised() -> None:
    row = term("x", origin=(0, 0, 0), axis=(0, 0, -4))
    assert row["axis"] == [0.0, 0.0, -1.0]


# --------------------------------------------------------------------------
# refusals
# --------------------------------------------------------------------------


def test_names_are_lower_snake_case_on_both_halves() -> None:
    with pytest.raises(BoardError, match="lower_snake_case"):
        term("Batt Pos", origin=(0, 0, 0), axis=(0, 0, 1))
    with pytest.raises(BoardError, match="lower_snake_case"):
        boards({"FC": _fc()})


def test_a_board_must_be_declared_with_board() -> None:
    with pytest.raises(BoardError, match="declared with board"):
        boards({"fc": {"component": FC}})
    with pytest.raises(BoardError, match="non-empty mapping"):
        boards({})


def test_a_row_must_be_declared_with_term() -> None:
    with pytest.raises(BoardError, match="declared with term"):
        board(FC, terminals=[{"name": "x", "origin": (0, 0, 0), "axis": (0, 0, 1)}])


def test_two_terminals_on_one_board_may_not_share_a_name() -> None:
    with pytest.raises(BoardError, match="repeats terminal 'x'"):
        boards(
            {
                "fc": board(
                    FC,
                    terminals=[
                        term("x", origin=(0, 0, 0), axis=(0, 0, 1)),
                        term("x", origin=(1, 0, 0), axis=(0, 0, 1)),
                    ],
                )
            }
        )


def test_two_forms_at_once_are_refused() -> None:
    with pytest.raises(BoardError, match="at most one of terminals="):
        board(
            FC,
            terminals=[term("x", origin=(0, 0, 0), axis=(0, 0, 1))],
            header=dict(origin=(0, 0, 0), axis=(0, 0, 1)),
            names=["x"],
        )


def test_exit_and_order_by_belong_to_a_selector() -> None:
    with pytest.raises(BoardError, match="belong to a selector"):
        board(
            FC,
            terminals=[term("x", origin=(0, 0, 0), axis=(0, 0, 1))],
            exit=(0, 0, 1),
        )


def test_a_board_with_no_terminals_at_all_says_so() -> None:
    with pytest.raises(BoardError, match="declares no terminals"):
        boards({"fc": board(FC)})


def test_the_units_are_closed() -> None:
    with pytest.raises(BoardError, match="must be one of"):
        board(FC, units="in", terminals=[term("x", origin=(0, 0, 0), axis=(0, 0, 1))])


def test_a_zero_axis_and_a_negative_bore_are_refused() -> None:
    with pytest.raises(BoardError, match="no direction"):
        term("x", origin=(0, 0, 0), axis=(0, 0, 0))
    with pytest.raises(BoardError, match="greater than zero"):
        term("x", origin=(0, 0, 0), axis=(0, 0, 1), hole_dia=0.0)
    with pytest.raises(BoardError, match="must not be negative"):
        term("x", origin=(0, 0, 0), axis=(0, 0, 1), depth=-1.0)


def test_the_table_is_bounded() -> None:
    many = {
        f"b{index}": board(FC, terminals=[term("x", origin=(0, 0, 0), axis=(0, 0, 1))])
        for index in range(MAX_BOARDS + 1)
    }
    with pytest.raises(BoardError, match="at most"):
        boards(many)


def test_a_stored_row_may_not_smuggle_an_unknown_column() -> None:
    with pytest.raises(BoardError, match="unrecognised keys"):
        canonical_terminal_rows(
            [_row("fc", "x", kind="hole")], what="board values"
        )


def test_a_world_frame_row_is_only_admitted_where_it_is_expected() -> None:
    row = _row("fc", "x", frame="world")
    with pytest.raises(BoardError, match="unrecognised keys"):
        canonical_terminal_rows([row], what="board values")
    assert canonical_terminal_rows([row], what="v", allow_world=True)[0]["frame"] == (
        "world"
    )
    with pytest.raises(BoardError, match="frame is 'world'"):
        canonical_terminal_rows(
            [_row("fc", "x", frame="camera")], what="v", allow_world=True
        )


# --------------------------------------------------------------------------
# stored overrides
# --------------------------------------------------------------------------


def _specs(*, selector: bool = False):
    return {
        "boards": [
            {
                "name": "fc",
                "units": "mm",
                "selector": False,
                "terminals": [
                    {
                        "name": "batt_pos",
                        "origin": [1.0, 2.0, 3.0],
                        "axis": [0.0, 0.0, 1.0],
                        "hole_dia": None,
                        "depth": None,
                    }
                ],
            },
            {
                "name": "esp",
                "units": "m",
                "selector": selector,
                "terminals": [
                    {
                        "name": "vcc",
                        "origin": [9.0, 1.0, 1.5],
                        "axis": [0.0, -1.0, 0.0],
                        "hole_dia": 0.75,
                        "depth": None,
                    }
                ],
            },
        ]
    }


def test_no_stored_rows_means_the_declared_table_stands() -> None:
    rows = effective_terminals(_specs(), [])
    assert [(row["board"], row["name"]) for row in rows] == [
        ("fc", "batt_pos"),
        ("esp", "vcc"),
    ]
    assert rows == declared_rows(_specs())


def test_stored_rows_replace_the_declared_table_wholesale() -> None:
    """A full row list, not a patch — what lets the editor add and delete."""

    stored = [
        _row("fc", "batt_pos", origin=[9.0, 9.0, 9.0]),
        _row("fc", "new_pad", hole_dia=0.9),
    ]
    rows = effective_terminals(_specs(), stored)
    assert [(row["board"], row["name"]) for row in rows] == [
        ("fc", "batt_pos"),
        ("fc", "new_pad"),
    ]
    assert rows[0]["origin"] == [9.0, 9.0, 9.0]
    assert rows[1]["hole_dia"] == pytest.approx(0.9)


def test_a_row_naming_a_dropped_board_is_pruned_not_raised_on() -> None:
    """ADR-039's asymmetry: loud on the request, lenient on the store."""

    stored = [_row("fc", "batt_pos"), _row("gone", "x")]
    assert [row["board"] for row in effective_terminals(_specs(), stored)] == ["fc"]
    assert [row["board"] for row in prune_terminal_rows(stored, _specs())] == ["fc"]


def test_a_selector_boards_rows_come_back_from_the_geometry() -> None:
    """An override on a derived board is a stale copy, so it is dropped and
    the declared rows are appended instead."""

    stored = [_row("fc", "batt_pos"), _row("esp", "vcc", origin=[0.0, 0.0, 0.0])]
    rows = effective_terminals(_specs(selector=True), stored)
    assert [(row["board"], row["name"]) for row in rows] == [
        ("fc", "batt_pos"),
        ("esp", "vcc"),
    ]
    # The declared row, not the stored one.
    assert rows[1]["origin"] == [9.0, 1.0, 1.5]


def test_an_override_is_still_validated() -> None:
    with pytest.raises(BoardError, match="must be \\[x, y, z\\]"):
        effective_terminals(_specs(), [_row("fc", "x", origin=[1.0, 2.0])])


def test_the_collector_applies_the_overrides_to_the_geometry() -> None:
    """The whole point: an edited row moves the terminal the run resolves."""

    stored = [
        _row("fc", "batt_pos", origin=[4.0, 5.0, 6.0]),
        # Metres on the board, millimetres in the row: the editor writes one
        # unit whatever the asset is modelled in.
        _row("esp", "vcc", origin=[10.0, 0.0, 2.0], hole_dia=1.0),
    ]
    _collector, table = _table(stored)
    assert table["fc"].names == ("batt_pos",)
    assert table["fc"].layout["terminals"][0]["origin"] == [4.0, 5.0, 6.0]
    esp = table["esp"].layout["terminals"][0]
    assert esp["origin"] == pytest.approx([0.01, 0.0, 0.002])
    assert esp["hole_dia"] == pytest.approx(0.001)


def test_declared_boards_reads_the_cache_back() -> None:
    entries = declared_boards(_specs())
    assert sorted(entries) == ["esp", "fc"]
    assert entries["esp"]["units"] == "m"
    assert declared_boards(None) == {}


# --------------------------------------------------------------------------
# the world-frame round trip
# --------------------------------------------------------------------------


def _placement(scale: float = 1.0, *, quarter_turn: bool = False, offset=(0.0, 0.0, 0.0)):
    """A placement matrix: optional quarter turn about z, uniform scale, offset."""

    cos, sin = (0.0, 1.0) if quarter_turn else (1.0, 0.0)
    return (
        scale * cos, -scale * sin, 0.0, offset[0],
        scale * sin, scale * cos, 0.0, offset[1],
        0.0, 0.0, scale, offset[2],
        0.0, 0.0, 0.0, 1.0,
    )


def test_inverting_a_placement_is_exactly_its_inverse() -> None:
    matrix = _placement(2.0, quarter_turn=True, offset=(10.0, -3.0, 4.0))
    inverse = invert_placement(matrix)
    product = [
        sum(matrix[row * 4 + k] * inverse[k * 4 + column] for k in range(4))
        for row in range(4)
        for column in range(4)
    ]
    identity = [1.0 if row == column else 0.0 for row in range(4) for column in range(4)]
    assert product == pytest.approx(identity, abs=1.0e-12)


def test_a_world_row_lands_in_the_boards_own_frame() -> None:
    """What the pick gesture writes, and what the hand-inverted literals were."""

    matrix = _placement(quarter_turn=True, offset=(10.0, 0.0, 0.0))
    row = {
        "board": "fc",
        "name": "batt_pos",
        # World: 10 mm along +x of the origin, i.e. the board's own origin.
        "origin": [10.0, 0.0, 0.0],
        "axis": [0.0, 1.0, 0.0],
        "frame": "world",
    }
    converted = row_from_world(row, matrix)
    assert converted["origin"] == pytest.approx([0.0, 0.0, 0.0], abs=1.0e-12)
    # A quarter turn about z carries the board's +x onto the world's +y.
    assert converted["axis"] == pytest.approx([1.0, 0.0, 0.0], abs=1.0e-12)
    assert "frame" not in converted


def test_a_metre_asset_converts_into_the_millimetre_row() -> None:
    """The asset is modelled in metres and placed by a 1000x scale; the row
    that comes back is still millimetres in the declaration frame."""

    matrix = _placement(1000.0)
    row = {
        "board": "esp",
        "name": "vcc",
        "origin": [9.0, 1.0, 1.5],
        "axis": [0.0, -1.0, 0.0],
        "hole_dia": 0.75,
        "frame": "world",
    }
    converted = row_from_world(row, matrix, units="m")
    assert converted["origin"] == pytest.approx([9.0, 1.0, 1.5])
    assert converted["hole_dia"] == pytest.approx(0.75)


def test_a_non_uniform_scale_refuses_the_row_by_name() -> None:
    """The refusal that already existed, now reported instead of worked
    around by declaring a stand-in box."""

    skewed = (
        2.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    )
    with pytest.raises(TerminalError, match="non-uniform scale"):
        row_from_world(_row("fc", "x", frame="world"), skewed)

    collector = BoardsCollector(
        [_row("fc", "batt_pos", frame="world")], lambda _component: skewed
    )
    with pytest.raises(BoardError, match="measured in the viewport") as caught:
        collector({"fc": _fc(), "esp": _esp()})
    assert "batt_pos" in str(caught.value)


def test_a_world_row_is_converted_exactly_once_and_written_back() -> None:
    """``validate_project_result`` stores ``collector.converted``, so the
    second run reads a board-frame row and no conversion happens again."""

    matrix = _placement(quarter_turn=True, offset=(10.0, 0.0, 0.0))
    stored = [_row("fc", "batt_pos", origin=[10.0, 0.0, 0.0], frame="world")]
    collector, table = _table(stored, lambda _component: matrix)

    assert [row["name"] for row in collector.converted] == ["batt_pos"]
    written = collector.converted[0]
    assert "frame" not in written
    assert written["origin"] == pytest.approx([0.0, 0.0, 0.0], abs=1.0e-12)
    assert table["fc"].layout["terminals"][0]["origin"] == pytest.approx(
        [0.0, 0.0, 0.0], abs=1.0e-12
    )

    # Feeding the written-back row in again is a no-op: it is already canonical.
    second, _table_again = _table([written], lambda _component: matrix)
    assert second.converted == []


def test_a_process_with_no_geometry_refuses_a_world_row() -> None:
    """``cadexd`` has no placement to convert through and never runs user
    code, so it stages the row rather than guessing at it."""

    collector = BoardsCollector([_row("fc", "batt_pos", frame="world")])
    with pytest.raises(BoardError, match="cannot resolve the board's placement"):
        collector({"fc": _fc(), "esp": _esp()})


def test_a_world_row_on_a_dropped_board_is_pruned_like_any_other() -> None:
    collector = BoardsCollector(
        [_row("gone", "x", frame="world")], lambda _component: _placement()
    )
    table = collector({"fc": _fc(), "esp": _esp()})
    # No conversion attempted, and the declared table stands for both boards.
    assert collector.converted == []
    assert table["fc"].names == ("batt_pos", "esp_vcc")


# --------------------------------------------------------------------------
# the revision
# --------------------------------------------------------------------------


def test_a_script_with_no_boards_keeps_a_byte_identical_revision() -> None:
    """The migration-free property, asserted rather than asserted-to — the
    same guard ``net_specs`` carries, for the same reason."""

    from CadexScriptedDomains import project_script_revision

    base = dict(source="result = {}", param_specs=[], param_values={"w": 1.0})
    before = project_script_revision(**base)
    assert project_script_revision(**base, board_specs={}, board_values=[]) == before
    assert project_script_revision(**base, board_specs=None, board_values=None) == before

    specs = _specs()
    assert project_script_revision(**base, board_specs=specs, board_values=[]) != before
    assert project_script_revision(
        **base, board_specs=specs, board_values=[_row("fc", "batt_pos")]
    ) != project_script_revision(**base, board_specs=specs, board_values=[])


def test_the_store_loads_a_pre_boards_script_json_unchanged() -> None:
    from CadexScriptStore import CadexProjectScriptStore

    default = CadexProjectScriptStore.default_state()
    assert default["board_specs"] == {}
    assert default["board_values"] == []


# --------------------------------------------------------------------------
# the host-side override check
# --------------------------------------------------------------------------


def _state(**overrides):
    state = {"board_specs": _specs()}
    state.update(overrides)
    return state


def test_a_request_naming_an_undeclared_board_stays_loud() -> None:
    from CadexScriptedRuntime import DomainRuntimeFailure, _project_terminal_values

    with pytest.raises(DomainRuntimeFailure) as caught:
        _project_terminal_values(
            _state(), [_row("nope", "x")], "xscript.project.set_params"
        )
    payload = dict(caught.value.payload)
    assert payload.get("failure_code") == "UNKNOWN_PROJECT_BOARD", payload
    assert "nope" in str(payload.get("error") or ""), payload


def test_a_request_editing_a_selector_board_stays_loud() -> None:
    """Its rows are the geometry's; an override would be overwritten silently."""

    from CadexScriptedRuntime import DomainRuntimeFailure, _project_terminal_values

    with pytest.raises(DomainRuntimeFailure) as caught:
        _project_terminal_values(
            {"board_specs": _specs(selector=True)},
            [_row("esp", "vcc")],
            "xscript.project.set_params",
        )
    assert dict(caught.value.payload).get("failure_code") == "UNKNOWN_PROJECT_BOARD"


def test_a_malformed_request_row_is_refused_by_shape() -> None:
    from CadexScriptedRuntime import DomainRuntimeFailure, _project_terminal_values

    with pytest.raises(DomainRuntimeFailure) as caught:
        _project_terminal_values(
            _state(),
            [{"board": "fc", "name": "x", "origin": [1.0, 2.0, 3.0]}],
            "xscript.project.set_params",
        )
    assert dict(caught.value.payload).get("failure_code") == "INVALID_PROJECT_TERMINAL"


def test_a_valid_request_passes_through_verbatim() -> None:
    from CadexScriptedRuntime import _project_terminal_values

    rows = [_row("fc", "batt_pos", hole_dia=0.8, depth=1.6)]
    assert _project_terminal_values(_state(), rows, "t") == [
        {
            "board": "fc",
            "name": "batt_pos",
            "origin": [1.0, 2.0, 3.0],
            "axis": [0.0, 0.0, 1.0],
            "hole_dia": 0.8,
            "depth": 1.6,
        }
    ]


def test_a_world_frame_request_row_is_staged_not_converted() -> None:
    """``cadexd`` has no geometry; the worker converts, and the result is
    written back into ``board_values`` (ADR-120)."""

    from CadexScriptedRuntime import _project_terminal_values

    rows = [_row("fc", "new_pad", frame="world")]
    staged = _project_terminal_values(_state(), rows, "t")
    assert staged[0]["frame"] == "world"
    assert staged[0]["name"] == "new_pad"


def test_a_script_that_has_never_declared_boards_defers_to_the_worker() -> None:
    """No board list to check against yet; the run itself is the check."""

    from CadexScriptedRuntime import _project_terminal_values

    rows = [_row("fc", "x")]
    assert _project_terminal_values({}, rows, "t")[0]["board"] == "fc"


def test_the_two_tables_meet_at_the_address() -> None:
    """A board name is a port name: one namespace, one address grammar."""

    from CadexNets import NetsCollector, wire

    _collector, table = _table()
    harness = NetsCollector()(
        ports=table,
        wires={"vcc": wire("fc.batt_pos", "esp.vcc", gauge=0.8)},
    )
    row = harness["vcc"]
    assert isinstance(row.a, Terminal) and row.a.component == FC
    assert row.b.component == ESP
    assert math.isfinite(row.gauge)


# --------------------------------------------------------------------------
# the whole path, against a real kernel
# --------------------------------------------------------------------------


REPO_ROOT = Path(__file__).resolve().parents[4]
_FREECADCMD_CANDIDATES = (
    REPO_ROOT / ".pixi" / "envs" / "default" / "bin" / "FreeCADCmd",
    REPO_ROOT / "build" / "release" / "bin" / "FreeCADCmd",
)
FREECADCMD = next(
    (candidate for candidate in _FREECADCMD_CANDIDATES if candidate.is_file()), None
)


#: Two plates and two boards, one of them wired to nothing at all. That last
#: part is the whole point: before ADR-120 it drew as nothing.
_DRIVER = r'''
import json
import shutil
import sys
import tempfile
from pathlib import Path

import FreeCAD as App

cadex_root = Path(sys.argv[-1])
sys.path.insert(0, str(cadex_root))

from CadexProject import CadexProjectScriptStore
from CadexScriptedDomainPublication import publish_project_candidate
from CadexScriptedRuntime import (
    DomainRuntimeFailure,
    accept_project_candidate,
    capture_project_state,
    execute_candidate,
    prepare_project_candidate,
    validate_project_result,
)
import cadex_rebuild

SCRIPT = """
T = 1.6
plate = part.box(20.0, 20.0, T, label="plate")
spare = part.box(20.0, 20.0, T, origin=(40.0, 0.0, 0.0), label="spare")

b = boards({
    "plate": board(plate, terminals=[
        term("sda", origin=(10.0, 5.0, T), axis=(0, 0, -1), hole_dia=1.0,
             depth=T),
        term("gnd", origin=(10.0, 10.0, T), axis=(0, 0, -1), hole_dia=1.0,
             depth=T),
    ]),
    "spare": board(spare, terminals=[
        term("nc", origin=(50.0, 5.0, T), axis=(0, 0, -1)),
    ]),
})

n = nets(ports=b, wires={})

result = {"plate": plate, "spare": spare}
for name, w in n.items():
    if not w.enabled:
        continue
    result["wire_" + name] = part.cable(w.a, w.b, gauge_mm=w.gauge,
                                        avoid=[plate, spare], cell_mm=1.0)
"""

root = Path(tempfile.mkdtemp(prefix="cadex-boards-"))
report = {}


def run(service, tool, arguments):
    captured = capture_project_state(service, tool, arguments)
    prepared = prepare_project_candidate(captured)
    execution = execute_candidate(prepared, cancellation_check=None)
    assert execution.get("ok") is True, execution
    validated = validate_project_result(prepared, execution)
    publication = publish_project_candidate(service, prepared, validated)
    accept_project_candidate(prepared, publication, validated)
    return validated


def revision(store):
    return str(store.read_state().get("working_revision") or "")


def attempt_report(store):
    state = store.read_state()
    staging = root / str(state["accepted_attempt"]["staging"])
    return json.loads((staging / "result.json").read_text(encoding="utf-8"))


try:
    document = App.newDocument("BoardsSeed")
    service = cadex_rebuild._RebuildService(root, document)
    store = CadexProjectScriptStore(root)

    declared = run(service, "xscript.project.write_script",
                   {"source": SCRIPT, "expected_revision": ""})
    report["declared_outputs"] = sorted(
        str(item["name"]) for item in declared["contract"])
    state = store.read_state()
    report["board_specs"] = state.get("board_specs")
    report["board_values"] = state.get("board_values")

    wiring = attempt_report(store).get("wiring") or []
    report["wiring"] = [
        {
            "port": entry.get("port"),
            "board": entry.get("board"),
            "output": entry.get("output"),
            "names": [t["name"] for t in entry.get("terminals") or []],
            "points": [t["point"] for t in entry.get("terminals") or []],
        }
        for entry in wiring
    ]

    # Move a terminal and add one, with no model turn anywhere.
    moved = run(service, "xscript.project.set_params", {
        "values": {},
        "boards": [
            {"board": "plate", "name": "sda", "origin": [12.0, 5.0, 1.6],
             "axis": [0.0, 0.0, -1.0], "hole_dia": 1.0, "depth": 1.6},
            {"board": "plate", "name": "gnd", "origin": [10.0, 10.0, 1.6],
             "axis": [0.0, 0.0, -1.0], "hole_dia": 1.0, "depth": 1.6},
            {"board": "plate", "name": "extra", "origin": [10.0, 15.0, 1.6],
             "axis": [0.0, 0.0, -1.0]},
            {"board": "spare", "name": "nc", "origin": [50.0, 5.0, 1.6],
             "axis": [0.0, 0.0, -1.0]},
        ],
        "expected_revision": revision(store),
    })
    report["moved_ok"] = True
    report["stored_rows"] = [
        (r["board"], r["name"]) for r in store.read_state().get("board_values") or []]
    moved_wiring = {
        entry.get("board"): entry for entry in attempt_report(store).get("wiring") or []}
    report["moved_names"] = [
        t["name"] for t in moved_wiring["plate"].get("terminals") or []]
    report["moved_points"] = [
        t["point"] for t in moved_wiring["plate"].get("terminals") or []]

    # A board named by nothing in the script is refused before the run.
    before = revision(store)
    try:
        run(service, "xscript.project.set_params", {
            "values": {},
            "boards": [{"board": "nope", "name": "x", "origin": [0.0, 0.0, 0.0],
                        "axis": [0.0, 0.0, 1.0]}],
            "expected_revision": before,
        })
    except DomainRuntimeFailure as failure:
        payload = dict(failure.payload)
        report["bad_board_code"] = str(payload.get("failure_code") or "")
    else:
        report["bad_board_code"] = "NOT-RAISED"
    report["revision_rolled_back"] = revision(store) == before

    # A row measured in the viewport: world coordinates, converted by the
    # worker and written back canonical.
    run(service, "xscript.project.set_params", {
        "values": {},
        "boards": [
            {"board": "plate", "name": "sda", "origin": [12.0, 5.0, 1.6],
             "axis": [0.0, 0.0, -1.0], "hole_dia": 1.0, "depth": 1.6},
            {"board": "plate", "name": "picked", "origin": [4.0, 4.0, 1.6],
             "axis": [0.0, 0.0, -1.0], "frame": "world"},
            {"board": "spare", "name": "nc", "origin": [50.0, 5.0, 1.6],
             "axis": [0.0, 0.0, -1.0]},
        ],
        "expected_revision": revision(store),
    })
    report["picked_rows"] = [
        dict(r) for r in store.read_state().get("board_values") or []]

    report["ok"] = True
finally:
    shutil.rmtree(root, ignore_errors=True)

print("BOARDS-E2E " + json.dumps(report, sort_keys=True))
'''


def _drive(tmp_path) -> dict:
    driver = tmp_path / "boards_driver.py"
    driver.write_text(_DRIVER, encoding="utf-8")
    cadex_root = Path(__file__).resolve().parent.parent
    completed = subprocess.run(
        [
            str(FREECADCMD),
            "-c",
            (
                "import sys; sys.argv = ['driver', "
                f"{str(cadex_root)!r}]; "
                f"exec(open({str(driver)!r}).read())"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=900,
        env={**os.environ, "PYTHONHASHSEED": "0"},
        check=False,
    )
    marker = next(
        (
            line
            for line in completed.stdout.splitlines()
            if line.startswith("BOARDS-E2E ")
        ),
        None,
    )
    assert marker, (
        f"boards driver produced no report; exit={completed.returncode}\n"
        f"stdout:\n{completed.stdout[-6000:]}\nstderr:\n{completed.stderr[-6000:]}"
    )
    return json.loads(marker.removeprefix("BOARDS-E2E "))


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available to build a board."
)
def test_a_declared_board_draws_and_is_edited_without_the_ai(tmp_path) -> None:
    report = _drive(tmp_path)
    assert report.get("ok") is True, report

    # Nothing is wired, so nothing is built beyond the two plates...
    assert report["declared_outputs"] == ["plate", "spare"], report
    # ...and both boards are still nodes on the canvas. This is the whole of
    # what ADR-120 fixes: before it, a declared terminal set that nothing
    # consumed reached the registry as nothing at all.
    wiring = {entry["board"]: entry for entry in report["wiring"]}
    assert sorted(wiring) == ["plate", "spare"], report["wiring"]
    assert wiring["plate"]["port"] == "plate"
    assert wiring["plate"]["output"] == "plate"
    assert wiring["plate"]["names"] == ["sda", "gnd"]
    assert wiring["spare"]["names"] == ["nc"]

    # The spec cache is what the editor reads its columns from, flat and in
    # millimetres.
    specs = {entry["name"]: entry for entry in report["board_specs"]["boards"]}
    assert sorted(specs) == ["plate", "spare"]
    assert specs["plate"]["terminals"][0] == {
        "name": "sda",
        "origin": [10.0, 5.0, 1.6],
        "axis": [0.0, 0.0, -1.0],
        "hole_dia": 1.0,
        "depth": 1.6,
    }
    # Nothing is stored until something overrides.
    assert report["board_values"] == []

    # A terminal moved and one added, with no chat turn: the run resolved the
    # stored rows rather than the declared ones.
    assert report["moved_ok"] is True
    assert report["stored_rows"] == [
        ["plate", "sda"], ["plate", "gnd"], ["plate", "extra"], ["spare", "nc"]
    ], report
    assert report["moved_names"] == ["sda", "gnd", "extra"]
    assert report["moved_points"][0] == pytest.approx([12.0, 5.0, 1.6])

    # A board the script does not declare is refused before the run, and the
    # refusal leaves the working state exactly as it was.
    assert report["bad_board_code"] == "UNKNOWN_PROJECT_BOARD", report
    assert report["revision_rolled_back"] is True, report

    # The pick: a world-frame row is converted by the worker and written back
    # canonical, so it is converted exactly once.
    picked = {row["name"]: row for row in report["picked_rows"]}
    assert sorted(picked) == ["nc", "picked", "sda"], report["picked_rows"]
    assert "frame" not in picked["picked"]
    # A part value is built in final coordinates, so the board frame is the
    # world frame here and the numbers survive the round trip unchanged.
    assert picked["picked"]["origin"] == pytest.approx([4.0, 4.0, 1.6])
