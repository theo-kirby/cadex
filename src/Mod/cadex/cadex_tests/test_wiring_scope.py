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

from CadexInspection import (
    MAX_INSPECT_RESULT_BYTES,
    capture_inspection,
    complete_inspection,
)
from CadexScriptStore import CadexProjectScriptStore


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
