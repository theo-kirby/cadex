# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``inspect scope="wiring"``: the harness, as something you can draw (ADR-065).

Terminals were resolved inside the isolated worker and discarded.  Their
name, point, axis and metrics never entered a response, so the shell saw a
seven-component, ten-cable harness as exactly two outputs — one compound of
wires and one of joints — and could not have drawn a wiring diagram if it
wanted to.

The scope answers from two places, and which one is the whole design: the
**terminals** come from the accepted run's own resolution, published into
its worker report, because a ``holes=`` selector needs the built shape and
the live process never runs user code; the **connections** come from the
declared table in ``script.json``.  A script written before ``nets(...)``
gets the same picture reconstructed from the ``cable``/``bundle``/``solder``
calls it made, marked read-only, because nothing outside such a script names
a row for an override to address.

``inspect`` already takes ``{"scope": str}``, so none of this is a protocol
change; the fixtures here are a fabricated store, the idiom
``test_model_context_contract`` uses for the output scope.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import cadex_part_worker
import cadex_project_worker
from CadexInspection import (
    MAX_INSPECT_RESULT_BYTES,
    capture_inspection,
    complete_inspection,
)
from CadexNets import NetsCollector, wire
from CadexScriptStore import CadexProjectScriptStore
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import create_domain_api
from cadex_domain_worker import _payload


REVISION = "a" * 64
DIGEST = "b" * 64

SIGNALS = ["sda", "scl", "gnd"]

SENSOR = {
    "domain": "part",
    "operation": "box",
    "output_type": "solid",
    "arguments": [40.0, 20.0, 1.6],
    "properties": {},
}
ESP = {
    "domain": "part",
    "operation": "box",
    "output_type": "solid",
    "arguments": [30.0, 18.0, 1.6],
    "properties": {},
}
LAYOUT = {
    "kind": "declared",
    "terminals": [
        {
            "origin": [0.0, 0.0, 0.0],
            "along": [0.0, 1.0, 0.0],
            "axis": [0.0, 0.0, -1.0],
            "pitch": 2.54,
            "count": 3,
            "depth": 1.6,
            "hole_dia": 1.0,
        }
    ],
    "names": SIGNALS,
}


def _terminal(name: str, index: int) -> dict:
    return {
        "name": name,
        "point": [0.0, 2.54 * index, -1.6],
        "direction": [0.0, 0.0, 1.0],
        "standoff_floor": 1.6,
        "metrics": {
            "kind": "hole",
            "axis": [0.0, 0.0, 1.0],
            "radius": 0.5,
            "depth": 1.6,
            "entry_point": [0.0, 2.54 * index, 0.0],
            "exit_point": [0.0, 2.54 * index, -1.6],
        },
    }


def _registry_entry(port: str, output: str, component: dict) -> dict:
    return {
        "port": port,
        "output": output,
        "domain": "part",
        "kind": "declared",
        "component": component,
        "layout": LAYOUT,
        "terminals": [_terminal(name, index) for index, name in enumerate(SIGNALS)],
    }


def _port_payload(component: dict, terminal: str) -> dict:
    return {"terminal": terminal, "component": component, "layout": LAYOUT}


def _output(name: str, operation: str, arguments: list, **properties) -> dict:
    return {
        "name": name,
        "type": "solid",
        "domain": "part",
        "definition": {
            "domain": "part",
            "operation": operation,
            "output_type": "solid",
            "arguments": arguments,
            "properties": properties,
        },
    }


def _service(root):
    class _Service:
        def active_workbench_name(self) -> str:
            return "PartWorkbench"

        def modeling_engine(self) -> str:
            return "xscript"

        def _active_document(self):
            return SimpleNamespace(Name="Ephemeral", Uid="doc", Objects=[])

        def project_scope_snapshot(self):
            return {"root": str(root)}

    return _Service()


def _store(tmp_path, *, report: dict, state: dict):
    """A project whose accepted attempt carries ``report``."""

    root = tmp_path / "project.cadex"
    staging = root / "script_artifacts" / REVISION[:16] / "attempt-1"
    staging.mkdir(parents=True)
    (staging / "result.json").write_text(json.dumps(report), encoding="utf-8")
    store = CadexProjectScriptStore(root)
    store.write(
        source="result = {}",
        state_updates={
            "accepted_revision": REVISION,
            "accepted_digest": DIGEST,
            "accepted_attempt": {
                "attempt_id": "1",
                "staging": staging.relative_to(root).as_posix(),
                "revision": REVISION,
            },
            **state,
        },
    )
    return root


def _wiring(root, **arguments):
    captured = capture_inspection(_service(root), {"scope": "wiring", **arguments})
    assert captured["kind"] == "wiring"
    return complete_inspection(captured)


# --------------------------------------------------------------------------
# a script that declares nets(...)
# --------------------------------------------------------------------------


def _declared_project(tmp_path):
    report = {
        "ok": True,
        "digest": DIGEST,
        "outputs": [],
        "wiring": [
            _registry_entry("sen", "sensor_board", SENSOR),
            _registry_entry("esp", "esp32_board", ESP),
        ],
    }
    state = {
        "net_specs": {
            "ports": [
                {"name": "sen", "terminals": SIGNALS},
                {"name": "esp", "terminals": SIGNALS},
            ],
            "wires": [
                {
                    "name": "sda",
                    "a": "sen.sda",
                    "b": "esp.sda",
                    "gauge_mm": 0.8,
                    "solder": True,
                    "enabled": True,
                }
            ],
        },
        "net_values": [],
    }
    return _store(tmp_path, report=report, state=state)


def test_a_declared_harness_is_editable_and_carries_its_terminals(tmp_path) -> None:
    result = _wiring(_declared_project(tmp_path))

    assert result["ok"] is True
    value = result["value"]
    assert value["source"] == "nets"
    assert value["editable"] is True
    assert value["revision"] == REVISION

    ports = [component["port"] for component in value["components"]]
    assert ports == ["sen", "esp"]
    # The join that comes free: the worker knows both the set's component
    # payload and the declared outputs' payloads.
    assert value["components"][1]["output"] == "esp32_board"
    terminal = value["components"][0]["terminals"][0]
    assert terminal["name"] == "sda"
    assert terminal["kind"] == "hole"
    assert terminal["radius"] == pytest.approx(0.5)
    assert terminal["depth"] == pytest.approx(1.6)
    assert terminal["point"] == [0.0, 0.0, -1.6]
    assert terminal["direction"] == [0.0, 0.0, 1.0]

    assert value["wires"] == [
        {
            "name": "sda",
            "a": "sen.sda",
            "b": "esp.sda",
            "gauge_mm": 0.8,
            "solder": True,
            "enabled": True,
        }
    ]
    assert result["result_json_bytes"] <= MAX_INSPECT_RESULT_BYTES


def test_stored_rows_are_what_the_scope_reports(tmp_path) -> None:
    """The editor reads back what it wrote, not what the script declared."""

    root = _declared_project(tmp_path)
    CadexProjectScriptStore(root).write(
        state_updates={
            "net_values": [
                {
                    "name": "sda",
                    "a": "sen.sda",
                    "b": "esp.scl",
                    "gauge_mm": 1.2,
                    "solder": False,
                    "enabled": True,
                },
                {
                    "name": "gnd",
                    "a": "sen.gnd",
                    "b": "esp.gnd",
                    "gauge_mm": 0.8,
                    "solder": True,
                    "enabled": False,
                },
            ]
        }
    )

    wires = _wiring(root)["value"]["wires"]
    assert [row["name"] for row in wires] == ["sda", "gnd"]
    assert wires[0]["b"] == "esp.scl" and wires[0]["gauge_mm"] == pytest.approx(1.2)
    assert wires[1]["enabled"] is False


def test_a_stale_stored_row_is_dropped_from_the_view(tmp_path) -> None:
    """The same pruning the runtime applies, so the two never disagree."""

    root = _declared_project(tmp_path)
    CadexProjectScriptStore(root).write(
        state_updates={
            "net_values": [
                {"name": "kept", "a": "sen.sda", "b": "esp.sda", "gauge_mm": 0.8},
                {"name": "stale", "a": "sen.sda", "b": "gone.sda", "gauge_mm": 0.8},
            ]
        }
    )

    assert [row["name"] for row in _wiring(root)["value"]["wires"]] == ["kept"]


# --------------------------------------------------------------------------
# a script written before nets(...) existed
# --------------------------------------------------------------------------


def _legacy_project(tmp_path):
    """One cable, one four-way bundle conductor, one joint on one end."""

    connections = [
        [_port_payload(SENSOR, "sda"), _port_payload(ESP, "sda")],
        [_port_payload(SENSOR, "scl"), _port_payload(ESP, "scl")],
    ]
    report = {
        "ok": True,
        "digest": DIGEST,
        "outputs": [
            _output(
                "wire_gnd",
                "cable",
                [_port_payload(SENSOR, "gnd"), _port_payload(ESP, "gnd")],
                gauge_mm=0.8,
            ),
            _output("ribbon_0", "bundle", [connections], gauge_mm=0.5, conductor=0),
            _output("ribbon_1", "bundle", [connections], gauge_mm=0.5, conductor=1),
            _output("joint_gnd", "solder", [_port_payload(SENSOR, "gnd")], gauge_mm=0.8),
            # A literal (point, direction) port has no component behind it.
            _output(
                "loose",
                "cable",
                [[[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]], [[5.0, 0.0, 0.0], [0.0, 0.0, 1.0]]],
                gauge_mm=0.8,
            ),
            _output("sensor_board", "box", [40.0, 20.0, 1.6]),
        ],
        "wiring": [
            _registry_entry("", "sensor_board", SENSOR),
            _registry_entry("", "", ESP),
        ],
    }
    return _store(tmp_path, report=report, state={})


def test_a_legacy_harness_is_reconstructed_read_only(tmp_path) -> None:
    result = _wiring(_legacy_project(tmp_path))

    assert result["ok"] is True
    value = result["value"]
    assert value["source"] == "derived"
    assert value["editable"] is False
    assert "nets(ports=..., wires=...)" in value["note"]

    # No ports were declared, so a component is named by its output — and a
    # component that is not a declared output still yields a node.
    assert [component["port"] for component in value["components"]] == [
        "sensor_board",
        "component_1",
    ]
    assert len(value["components"][0]["terminals"]) == 3

    rows = {row["name"]: row for row in value["wires"]}
    assert set(rows) == {"wire_gnd", "ribbon_0", "ribbon_1"}
    assert rows["wire_gnd"]["a"] == "sensor_board.gnd"
    assert rows["wire_gnd"]["b"] == "component_1.gnd"
    # The joint scan is what says which ends are soldered, and it runs after
    # the rows are built: a solder output may be declared before its cable.
    assert rows["wire_gnd"]["solder"] is True
    assert rows["ribbon_0"]["solder"] is False


def test_a_bundle_conductor_is_one_row_and_is_marked_as_one(tmp_path) -> None:
    """Bundles draw; they are never editable, which the row says out loud."""

    rows = {row["name"]: row for row in _wiring(_legacy_project(tmp_path))["value"]["wires"]}
    assert rows["ribbon_0"]["kind"] == "bundle"
    assert rows["wire_gnd"]["kind"] == "cable"
    assert rows["ribbon_0"]["a"] == "sensor_board.sda"
    assert rows["ribbon_1"]["a"] == "sensor_board.scl"


def test_a_literal_port_yields_no_half_wire(tmp_path) -> None:
    """It has no component, so it has no node; half a wire is worse than none."""

    names = {row["name"] for row in _wiring(_legacy_project(tmp_path))["value"]["wires"]}
    assert "loose" not in names


# --------------------------------------------------------------------------
# the producer, not a fixture
# --------------------------------------------------------------------------
#
# Everything above hand-builds its registry, and that is exactly how this
# scope shipped drawing every node and not one wire (ADR-113): the real
# producer, ``cadex_project_worker._wiring_registry``, dropped the
# ``component`` and ``layout`` fields the fixtures supplied, so every
# endpoint hashed to the same empty identity and ``_derived_wires`` refused
# all of them.  A fixture that can disagree with its producer proves the
# fixture.  These two drive the producer.


PRODUCER_HEADER = {
    "origin": (0.0, 0.0, 1.6),
    "along": (0.0, 1.0, 0.0),
    "axis": (0.0, 0.0, 1.0),
    "pitch": 2.54,
    "count": 3,
    "depth": 1.6,
    "hole_dia": 1.0,
}


def _built_harness():
    """One real run's worth of harness, built through the shipping APIs.

    The part API declares the boards, their terminal sets and the wire
    between them; the part worker resolves those sets exactly as
    ``_resolve_port`` does on the way into a route, which is what fills the
    registry the project worker then publishes.  A declared layout on a
    ``part`` component needs no kernel, so this runs headless with the rest
    of the suite.
    """

    pack = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]
    part = create_domain_api(pack.domain, pack.api_exports, pack.output_types)
    sensor = part.box(40.0, 20.0, 1.6, label="sensor")
    esp = part.box(30.0, 18.0, 1.6, label="esp")
    return (
        part,
        sensor,
        esp,
        part.terminals(sensor, header=PRODUCER_HEADER, names=SIGNALS),
        part.terminals(esp, header=PRODUCER_HEADER, names=SIGNALS),
    )


def _resolve_endpoints(result):
    """Resolve every terminal endpoint the result's harness operations name."""

    cadex_part_worker.reset_part_shape_memo()
    for value in result.values():
        definition = _payload(value)
        if str(definition.get("operation") or "") not in _HARNESS_OPS:
            continue
        for argument in list(definition.get("arguments") or []):
            if isinstance(argument, dict) and "terminal" in argument:
                cadex_part_worker._resolve_terminal_set(
                    str(definition["operation"]), "start", argument
                )


_HARNESS_OPS = ("cable", "solder")


def _produced_project(tmp_path, nets, result):
    """A store whose accepted attempt carries the report the worker would write."""

    _resolve_endpoints(result)
    report = {
        "ok": True,
        "digest": DIGEST,
        "outputs": [
            {
                "name": name,
                "type": "solid",
                "domain": "part",
                "definition": _payload(value),
            }
            for name, value in result.items()
        ],
        "wiring": cadex_project_worker._wiring_registry(nets, result),
    }
    # Through JSON, because the registry and the outputs meet only after a
    # round trip through ``result.json`` — and they are matched on canonical
    # JSON, so the round trip is part of what is being asserted.
    return _store(tmp_path, report=json.loads(json.dumps(report)), state={})


def test_the_published_registry_addresses_a_real_cable(tmp_path) -> None:
    """The join the derived view lives on, end to end from the producer."""

    part, sensor, esp, sen_t, esp_t = _built_harness()
    result = {
        "sensor_board": sensor,
        "esp32_board": esp,
        "wire_gnd": part.cable(sen_t["gnd"], esp_t["gnd"], gauge_mm=0.8),
        "joint_gnd": part.solder(sen_t["gnd"], gauge_mm=0.8, pad_dia_mm=1.2),
    }
    # No ports declared: this is the pre-nets() script the derived path is for.
    root = _produced_project(tmp_path, NetsCollector(), result)

    value = _wiring(root)["value"]
    assert value["source"] == "derived"
    assert [component["output"] for component in value["components"]] == [
        "sensor_board",
        "esp32_board",
    ]
    assert value["wires"] == [
        {
            "name": "wire_gnd",
            "a": "sensor_board.gnd",
            "b": "esp32_board.gnd",
            "gauge_mm": 0.8,
            "enabled": True,
            "kind": "cable",
            "solder": True,
        }
    ]


def test_the_published_registry_carries_a_declared_port_to_the_canvas(
    tmp_path,
) -> None:
    """The same join, from the other table: a node is named by its port."""

    part, sensor, esp, sen_t, esp_t = _built_harness()
    nets = NetsCollector()
    table = nets(
        ports={"sen": sen_t, "esp": esp_t},
        wires={"gnd": wire("sen.gnd", "esp.gnd", gauge=0.8, solder=True)},
    )
    row = table["gnd"]
    result = {
        "sensor_board": sensor,
        "esp32_board": esp,
        "wire_gnd": part.cable(row.a, row.b, gauge_mm=row.gauge),
    }
    root = _produced_project(tmp_path, nets, result)
    CadexProjectScriptStore(root).write(state_updates={"net_specs": nets.specs})

    value = _wiring(root)["value"]
    assert value["source"] == "nets" and value["editable"] is True
    assert [component["port"] for component in value["components"]] == ["sen", "esp"]
    assert [component["output"] for component in value["components"]] == [
        "sensor_board",
        "esp32_board",
    ]
    assert [row["a"] for row in value["wires"]] == ["sen.gnd"]


# --------------------------------------------------------------------------
# two terminal sets on one board, and wires the table does not declare
# --------------------------------------------------------------------------
#
# A board with a front header and a back header is one component and two
# ``terminals(...)`` calls, and both sets answered to the component's output
# name. The canvas keys a node by that name, so the second set's sockets
# replaced the first set's and every declared wire lost an end: three wires,
# no links, and a header still reading "3 wires" (ADR-115).


BACK_HEADER = {**PRODUCER_HEADER, "origin": (0.0, 12.0, 1.6)}
BACK_SIGNALS = ["h1", "h2", "h3"]


def _two_header_project(tmp_path):
    """One board wired from its front row and cabled from its back row.

    The declared port is named after the output on purpose: that is the
    collision, and it is what a script written by the assistant looks like.
    """

    part, sensor, esp, sen_t, esp_t = _built_harness()
    back = part.terminals(sensor, header=BACK_HEADER, names=BACK_SIGNALS)
    nets = NetsCollector()
    table = nets(
        ports={"sensor_board": sen_t, "esp": esp_t},
        wires={"gnd": wire("sensor_board.gnd", "esp.gnd", gauge=0.8, solder=True)},
    )
    row = table["gnd"]
    result = {
        "sensor_board": sensor,
        "esp32_board": esp,
        "wire_gnd": part.cable(row.a, row.b, gauge_mm=row.gauge),
        # Built by hand, outside the table — which is the only way to build a
        # bundle, and a perfectly ordinary way to build a cable.
        "wire_back": part.cable(back["h1"], esp_t["scl"], gauge_mm=0.5),
    }
    root = _produced_project(tmp_path, nets, result)
    CadexProjectScriptStore(root).write(state_updates={"net_specs": nets.specs})
    return root


def _components(root):
    """The node list, walked the way the shell's ``_inspect_full`` walks it.

    Three components of resolved terminals are past the per-value preview
    stub, so the list arrives as a path to follow — which is the shipping
    path for any harness worth drawing.
    """

    return _wiring(root, path="/components", limit=50)["value"]


def test_a_second_terminal_set_gets_its_own_node(tmp_path) -> None:
    components = _components(_two_header_project(tmp_path))

    assert [component["port"] for component in components] == [
        "sensor_board",
        "esp",
        "sensor_board#2",
    ]
    # Both sets are on the same board, and both keep their own terminals:
    # the declared port's are what its addresses are written against.
    assert [term["name"] for term in components[0]["terminals"]] == SIGNALS
    assert [term["name"] for term in components[2]["terminals"]] == BACK_SIGNALS
    assert components[2]["output"] == "sensor_board"


def test_the_declared_wire_still_addresses_the_declared_set(tmp_path) -> None:
    """The point of reserving port names before naming anything else."""

    wires = _wiring(_two_header_project(tmp_path))["value"]["wires"]

    assert wires[0]["a"] == "sensor_board.gnd" and wires[0]["b"] == "esp.gnd"
    assert "editable" not in wires[0]


def test_a_wire_built_outside_the_table_is_drawn_read_only(tmp_path) -> None:
    """The boards it lands on drew as nodes with nothing attached before."""

    wires = _wiring(_two_header_project(tmp_path))["value"]["wires"]
    extra = [row for row in wires if row.get("editable") is False]

    assert [row["name"] for row in extra] == ["wire_back"]
    assert extra[0]["a"] == "sensor_board#2.h1" and extra[0]["b"] == "esp.scl"
    assert extra[0]["kind"] == "cable"


def test_the_declared_wires_own_cable_is_not_drawn_twice(tmp_path) -> None:
    """It is the same connection seen from the other table."""

    wires = _wiring(_two_header_project(tmp_path))["value"]["wires"]

    pairs = [frozenset((row["a"], row["b"])) for row in wires]
    assert len(pairs) == len(set(pairs))
    assert [row["name"] for row in wires] == ["gnd", "wire_back"]


def test_an_inline_component_is_named_by_its_label(tmp_path) -> None:
    """A pad that is never published under a result key still needs a node."""

    registry = [
        {**_registry_entry("", "", {**SENSOR, "properties": {"label": "fpga pad"}})},
        {**_registry_entry("", "", {**ESP, "properties": {}})},
    ]
    root = _store(
        tmp_path,
        report={"ok": True, "digest": DIGEST, "outputs": [], "wiring": registry},
        state={},
    )

    assert [c["port"] for c in _wiring(root)["value"]["components"]] == [
        "fpga pad",
        "component_1",
    ]


# --------------------------------------------------------------------------
# a script that declares boards(...) (ADR-120)
# --------------------------------------------------------------------------


BOARD_SPECS = {
    "boards": [
        {
            "name": "fc",
            "units": "mm",
            "selector": False,
            "terminals": [
                {
                    "name": name,
                    "origin": [0.0, 2.54 * index, 1.6],
                    "axis": [0.0, 0.0, -1.0],
                    "hole_dia": 1.0,
                    "depth": 1.6,
                }
                for index, name in enumerate(SIGNALS)
            ],
        },
        {
            "name": "esp",
            "units": "m",
            "selector": True,
            "terminals": [],
        },
    ]
}


def _board_project(tmp_path, *, board_values=()):
    """Two boards, neither of them wired to anything at all.

    Which is the case that motivated ADR-120: before it, a declared terminal
    set that nothing consumed reached the canvas as nothing at all.
    """

    report = {
        "ok": True,
        "digest": DIGEST,
        "outputs": [],
        "wiring": [
            {**_registry_entry("fc", "fc_board", SENSOR), "board": "fc"},
            {**_registry_entry("esp", "esp32_board", ESP), "board": "esp"},
        ],
    }
    state = {
        "board_specs": BOARD_SPECS,
        "board_values": [dict(row) for row in board_values],
    }
    return _store(tmp_path, report=report, state=state)


def test_a_declared_board_is_a_node_even_with_nothing_wired_to_it(tmp_path) -> None:
    value = _wiring(_board_project(tmp_path))["value"]

    components = {item["board"]: item for item in value["components"]}
    assert sorted(components) == ["esp", "fc"]
    assert value["wires"] == []
    assert [item["name"] for item in components["fc"]["terminals"]] == SIGNALS


def test_a_declared_boards_sockets_carry_their_row(tmp_path) -> None:
    """The row is what ``set_params(boards=...)`` writes back, so the canvas
    is shown the same numbers it will send."""

    value = _wiring(_board_project(tmp_path))["value"]
    components = {item["board"]: item for item in value["components"]}

    socket = components["fc"]["terminals"][1]
    assert socket["origin"] == pytest.approx([0.0, 2.54, 1.6])
    assert socket["axis"] == [0.0, 0.0, -1.0]
    assert socket["hole_dia"] == pytest.approx(1.0)
    # The resolved world point stays beside it: the row is the board's own
    # frame and the canvas needs both.
    assert socket["point"] == [0.0, 2.54, -1.6]


def test_a_selector_board_draws_and_is_not_editable(tmp_path) -> None:
    value = _wiring(_board_project(tmp_path))["value"]
    components = {item["board"]: item for item in value["components"]}

    assert components["fc"]["editable"] is True
    assert components["esp"]["editable"] is False
    # Its sockets carry the resolved geometry and no row: there is nothing an
    # override could address that the shape would not overwrite.
    assert "origin" not in components["esp"]["terminals"][0]


def test_stored_terminal_rows_are_what_the_scope_reports(tmp_path) -> None:
    """The editor reads back what it wrote, not what the script declared."""

    root = _board_project(
        tmp_path,
        board_values=[
            {
                "board": "fc",
                "name": "sda",
                "origin": [4.0, 5.0, 6.0],
                "axis": [1.0, 0.0, 0.0],
                "hole_dia": None,
                "depth": None,
            }
        ],
    )
    components = {
        item["board"]: item for item in _wiring(root)["value"]["components"]
    }

    socket = components["fc"]["terminals"][0]
    assert socket["origin"] == pytest.approx([4.0, 5.0, 6.0])
    assert socket["hole_dia"] is None
    # A row the stored table dropped keeps its resolved socket and loses its
    # row fields: the run built it, the table no longer names it.
    assert "origin" not in components["fc"]["terminals"][1]


def test_a_row_naming_a_dropped_board_is_pruned_from_the_view(tmp_path) -> None:
    """The same pruning the runtime applies, so the two never disagree."""

    root = _board_project(
        tmp_path,
        board_values=[
            {"board": "gone", "name": "sda", "origin": [1.0, 1.0, 1.0],
             "axis": [0.0, 0.0, 1.0]},
        ],
    )
    components = {
        item["board"]: item for item in _wiring(root)["value"]["components"]
    }
    assert all("origin" not in socket for socket in components["fc"]["terminals"])


def test_a_board_name_is_reserved_the_way_a_port_name_is(tmp_path) -> None:
    """One namespace: a board is the left half of an address too (ADR-115)."""

    report = {
        "ok": True,
        "digest": DIGEST,
        "outputs": [],
        "wiring": [
            {**_registry_entry("", "fc", SENSOR), "board": "fc"},
            # A second set on a component whose output name would collide with
            # the board's name; it must not take it.
            {**_registry_entry("", "fc", ESP), "board": ""},
        ],
    }
    value = _wiring(_store(tmp_path, report=report, state={}))["value"]
    assert [item["port"] for item in value["components"]] == ["fc", "fc#2"]


# --------------------------------------------------------------------------
# boundaries
# --------------------------------------------------------------------------


def test_the_scope_pages_like_every_other(tmp_path) -> None:
    root = _declared_project(tmp_path)
    paged = _wiring(root, path="/components/0/terminals")

    assert paged["ok"] is True
    assert paged["page"]["kind"] == "array"
    assert paged["page"]["total"] == 3
    assert [item["name"] for item in paged["value"]] == SIGNALS


def test_a_project_with_no_accepted_revision_says_so(tmp_path) -> None:
    root = tmp_path / "empty.cadex"
    CadexProjectScriptStore(root).write(source="result = {}")

    value = _wiring(root)["value"]
    assert value["ok"] is False
    assert "no accepted revision" in value["error"]


def test_a_script_with_no_terminals_draws_an_empty_graph(tmp_path) -> None:
    root = _store(
        tmp_path,
        report={"ok": True, "digest": DIGEST, "outputs": [], "wiring": []},
        state={},
    )

    value = _wiring(root)["value"]
    assert value["components"] == [] and value["wires"] == []
    assert value["editable"] is False


def test_a_large_harness_stays_inside_the_inspection_budget(tmp_path) -> None:
    """Seven components and twenty terminals each — wiring-test's size, twice."""

    report = {
        "ok": True,
        "digest": DIGEST,
        "outputs": [],
        "wiring": [
            {
                **_registry_entry(f"c{index}", f"board_{index}", dict(SENSOR)),
                "terminals": [_terminal(f"t{pin}", pin) for pin in range(20)],
            }
            for index in range(7)
        ],
    }
    result = _wiring(_store(tmp_path, report=report, state={}))

    assert result["ok"] is True
    assert result["result_json_bytes"] <= MAX_INSPECT_RESULT_BYTES
    # Over budget in full, so the components come back as a stub carrying the
    # path to walk — never silently truncated. The shell follows that path;
    # ``_inspect_full`` already does exactly this for the parameter specs.
    assert result["value"]["components"] == {
        "type": "array",
        "item_count": 7,
        "inspect_path": "/components",
    }
    walked = _wiring(_store(tmp_path / "again", report=report, state={}),
                     path="/components/3/terminals")
    assert walked["page"]["total"] == 20


# --------------------------------------------------------------------------
# the route each wire followed (ADR-118)


ROUTE = {
    "path": [
        [0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, 2.0],
        [12.0, 4.0, 9.0], [30.0, 4.0, 9.0],
        [40.0, 0.0, 2.0], [40.0, 0.0, 1.0], [40.0, 0.0, 0.0],
    ],
    "waypoints": [[12.0, 4.0, 9.0], [30.0, 4.0, 9.0]],
}


def _routed_project(tmp_path, *, declared: bool):
    """The same two wires, once declared by ``nets(...)`` and once not.

    The join differs between the two branches — a declared row knows its
    endpoints and a reconstructed one knows its output — so the round trip is
    asserted through both rather than through whichever one is easier.
    """

    outputs = [
        dict(
            _output(
                "wire_sda",
                "cable",
                [_port_payload(SENSOR, "sda"), _port_payload(ESP, "sda")],
                gauge_mm=0.8,
            ),
            route=ROUTE,
        ),
        # A bundle conductor publishes its shared spine and no interior.
        dict(
            _output(
                "ribbon_0",
                "bundle",
                [[[_port_payload(SENSOR, "scl"), _port_payload(ESP, "scl")],
                  [_port_payload(SENSOR, "gnd"), _port_payload(ESP, "gnd")]]],
                gauge_mm=0.5,
                conductor=0,
            ),
            route={"path": ROUTE["path"], "waypoints": []},
        ),
    ]
    report = {
        "ok": True,
        "digest": DIGEST,
        "outputs": outputs,
        "wiring": [
            _registry_entry("sen" if declared else "", "sensor_board", SENSOR),
            _registry_entry("esp" if declared else "", "esp32_board", ESP),
        ],
    }
    state = {}
    if declared:
        state = {
            "net_specs": {
                "ports": [
                    {"name": "sen", "terminals": SIGNALS},
                    {"name": "esp", "terminals": SIGNALS},
                ],
                "wires": [
                    {
                        "name": "sda",
                        "a": "sen.sda",
                        "b": "esp.sda",
                        "gauge_mm": 0.8,
                        "solder": False,
                        "enabled": True,
                    }
                ],
            },
            "net_values": [],
        }
    return _store(tmp_path, report=report, state=state)


def test_a_declared_row_carries_the_route_its_cable_followed(tmp_path) -> None:
    value = _wiring(_routed_project(tmp_path, declared=True))["value"]

    assert value["source"] == "nets"
    row = next(row for row in value["wires"] if row["name"] == "sda")
    # The whole centreline the sweep was built from...
    assert row["path"] == ROUTE["path"]
    # ...and the interior of it a user may drag, which is exactly what would
    # go back into waypoints= to reproduce the run.
    assert row["waypoints"] == ROUTE["waypoints"]
    # It is read-only here: a path is script state and set_params(nets=)
    # carries editor state, which is the boundary ADR-065 drew.
    assert "path" in value["note"] and "read-only" in value["note"]


def test_a_reconstructed_row_carries_it_too(tmp_path) -> None:
    value = _wiring(_routed_project(tmp_path, declared=False))["value"]

    assert value["source"] == "derived"
    row = next(row for row in value["wires"] if row["kind"] == "cable")
    assert row["path"] == ROUTE["path"]
    assert row["waypoints"] == ROUTE["waypoints"]


def test_a_bundle_conductor_publishes_a_path_and_no_editable_interior(
    tmp_path,
) -> None:
    """ADR-115 §4's read-only treatment, made structural rather than advisory.

    A bundle's route belongs to the bundle, so authoring one conductor's path
    would silently be authoring all of them. An empty ``waypoints`` is what
    tells the editor that without it having to know what a bundle is.
    """

    value = _wiring(_routed_project(tmp_path, declared=False))["value"]

    row = next(row for row in value["wires"] if row["kind"] == "bundle")
    assert row["path"] == ROUTE["path"]
    assert row["waypoints"] == []


def test_a_wire_whose_run_published_no_route_simply_has_none(tmp_path) -> None:
    """The key is absent, not empty: a project accepted before ADR-118 has no
    published route at all, and the canvas must draw it rather than refuse."""

    value = _wiring(_legacy_project(tmp_path))["value"]

    assert value["wires"]
    assert all("path" not in row for row in value["wires"])
