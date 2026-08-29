# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The connection table: ``nets(...)`` and ``wire(...)`` (ADR-065).

The harness pipeline built by ADR-056/057/062/063 could route, lay and
solder a real wire — and could not say, anywhere outside the script text,
*what was connected to what*.  ``nets()`` is the declaration that fixes
that, on exactly the terms ``params()`` already has: a table stated in the
script whose current values live outside it.

``CadexNets`` imports nothing from FreeCAD, so everything here runs against
plain numbers and fake terminal sets — the same footing ``CadexRouting``,
``CadexBundle`` and ``CadexTerminals`` are tested on.  What is checked is
the vocabulary, every refusal it makes, and the two properties the editor
depends on: a stored row list *replaces* the declared table, and a stored
row the script no longer supports is dropped rather than raised on.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pytest

from CadexNets import (
    MAX_NETS,
    NetError,
    NetsCollector,
    canonical_rows,
    declared_ports,
    effective_rows,
    prune_rows,
    wire,
)
from CadexTerminals import Terminal, TerminalSet, declared_layout


HEADER = dict(
    origin=(0.0, 0.0, 0.0),
    along=(0.0, 1.0, 0.0),
    axis=(0.0, 0.0, -1.0),
    pitch=2.54,
    count=3,
    hole_dia=1.0,
    depth=1.6,
)
SIGNALS = ["sda", "scl", "gnd"]


def _set(component: str) -> TerminalSet:
    return TerminalSet(component, declared_layout(None, header=HEADER, names=SIGNALS))


def _ports() -> dict[str, TerminalSet]:
    return {"sen": _set("SENSOR"), "esp": _set("ESP")}


def _row(name: str, a: str, b: str, **overrides):
    row = {"name": name, "a": a, "b": b, "gauge_mm": 0.8}
    row.update(overrides)
    return row


# --------------------------------------------------------------------------
# declaration
# --------------------------------------------------------------------------


def test_a_declared_table_resolves_to_real_terminals() -> None:
    """The whole point: ``w.a`` is a Terminal, so part.cable is unchanged."""

    collector = NetsCollector()
    table = collector(
        ports=_ports(),
        wires={
            "sda": wire("sen.sda", "esp.sda", gauge=0.8, solder=True, avoid=["board"]),
            "gnd": wire("sen.gnd", "esp.gnd", gauge=1.2),
        },
    )

    assert table.names() == ("sda", "gnd")
    row = table["sda"]
    assert isinstance(row.a, Terminal) and isinstance(row.b, Terminal)
    assert row.a.name == "sda" and row.a.component == "SENSOR"
    assert row.b.component == "ESP"
    assert row.gauge == pytest.approx(0.8)
    assert row.solder is True and row.enabled is True
    # Declaration-only, and carried straight through to part.cable.
    assert row.avoid == ("board",)
    assert table["gnd"].solder is False and table["gnd"].avoid == ()
    # The two ends as addresses as well as as Terminals (ADR-122). A Terminal
    # knows its own name and not which port addressed it, so a script sizing
    # one joint per soldered END -- ``part.solder`` needs ``pad_dia_mm`` on a
    # declared pad, and the right number is the board's -- has nothing else to
    # key a per-board table on.
    assert row.a_address == "sen.sda" and row.b_address == "esp.sda"
    assert row.a_address.split(".")[0] == "sen"
    assert table["gnd"].a_address == "sen.gnd"


def test_the_spec_cache_is_json_and_stable() -> None:
    """``net_specs`` rides in script.json and feeds the revision hash."""

    collector = NetsCollector()
    collector(
        ports=_ports(),
        wires={"sda": wire("sen.sda", "esp.sda", gauge=0.8, avoid=["board"])},
    )

    encoded = json.dumps(collector.specs, sort_keys=True)
    assert json.loads(encoded) == collector.specs
    assert collector.specs["ports"] == [
        {"name": "sen", "terminals": SIGNALS},
        {"name": "esp", "terminals": SIGNALS},
    ]
    # avoid and label are declaration-only: they must not reach the cache,
    # or the editor would be shown a column it cannot write.
    assert collector.specs["wires"] == [
        {
            "name": "sda",
            "a": "sen.sda",
            "b": "esp.sda",
            "gauge_mm": 0.8,
            "solder": False,
            "enabled": True,
        }
    ]


def test_the_table_iterates_in_declaration_order_and_reads_by_name() -> None:
    collector = NetsCollector()
    table = collector(
        ports=_ports(),
        wires={
            "gnd": wire("sen.gnd", "esp.gnd", gauge=1.0),
            "sda": wire("sen.sda", "esp.sda", gauge=0.8, enabled=False),
        },
    )

    assert [name for name, _row in table.items()] == ["gnd", "sda"]
    assert len(table) == 2
    assert "sda" in table and "miso" not in table
    # The common loop, spelled once so every script does not re-spell it.
    assert [row.name for row in table.enabled()] == ["gnd"]
    with pytest.raises(NetError, match="declares no connection named 'miso'"):
        table["miso"]


def test_the_table_is_immutable_inside_the_script() -> None:
    collector = NetsCollector()
    table = collector(ports=_ports(), wires={"sda": wire("sen.sda", "esp.sda", gauge=0.8)})
    with pytest.raises(TypeError):
        table.wires = []


# --------------------------------------------------------------------------
# refusals
# --------------------------------------------------------------------------


def test_nets_may_be_called_at_most_once() -> None:
    collector = NetsCollector()
    collector(ports=_ports(), wires={})
    with pytest.raises(NetError, match="at most once per script"):
        collector(ports=_ports(), wires={})


def test_an_endpoint_must_name_a_port_and_a_terminal() -> None:
    with pytest.raises(NetError, match="'<port>.<terminal>'"):
        wire("sensda", "esp.sda", gauge=0.8)
    with pytest.raises(NetError, match="lower_snake_case"):
        wire("Sen.sda", "esp.sda", gauge=0.8)


def test_both_ends_of_a_wire_must_differ() -> None:
    with pytest.raises(NetError, match="to itself"):
        wire("sen.sda", "sen.sda", gauge=0.8)


def test_an_unknown_port_or_terminal_is_a_refusal_not_a_silent_miswire() -> None:
    """Validated at declaration against the actual TerminalSets."""

    with pytest.raises(NetError, match=r"names port 'nope'.*\['esp', 'sen'\]"):
        NetsCollector()(
            ports=_ports(), wires={"x": wire("sen.sda", "nope.sda", gauge=0.8)}
        )
    with pytest.raises(NetError, match=r"names terminal 'miso'.*\['sda', 'scl', 'gnd'\]"):
        NetsCollector()(
            ports=_ports(), wires={"x": wire("sen.sda", "esp.miso", gauge=0.8)}
        )


def test_names_are_lower_snake_case_on_both_halves() -> None:
    with pytest.raises(NetError, match="port name 'Sen'"):
        NetsCollector()(ports={"Sen": _set("S")}, wires={})
    with pytest.raises(NetError, match="must be lower_snake_case"):
        NetsCollector()(
            ports=_ports(), wires={"I2C-SDA": wire("sen.sda", "esp.sda", gauge=0.8)}
        )


def test_a_row_must_be_declared_with_wire() -> None:
    with pytest.raises(NetError, match="must be declared with wire"):
        NetsCollector()(
            ports=_ports(), wires={"sda": {"a": "sen.sda", "b": "esp.sda"}}
        )


def test_a_port_must_be_a_terminal_set() -> None:
    with pytest.raises(NetError, match="must be the TerminalSet"):
        NetsCollector()(ports={"sen": "SENSOR"}, wires={})
    with pytest.raises(NetError, match="non-empty mapping"):
        NetsCollector()(ports={}, wires={})


def test_gauge_and_the_two_flags_are_checked() -> None:
    with pytest.raises(NetError, match="greater than zero"):
        wire("sen.sda", "esp.sda", gauge=0.0)
    with pytest.raises(NetError, match="must be finite"):
        wire("sen.sda", "esp.sda", gauge=float("inf"))
    with pytest.raises(NetError, match="solder must be True or False"):
        wire("sen.sda", "esp.sda", gauge=0.8, solder=1)
    with pytest.raises(NetError, match="avoid must be a list"):
        wire("sen.sda", "esp.sda", gauge=0.8, avoid="board")


def test_the_table_is_bounded() -> None:
    rows = [_row(f"n{index}", "sen.sda", "esp.sda") for index in range(MAX_NETS + 1)]
    with pytest.raises(NetError, match=f"at most {MAX_NETS}"):
        canonical_rows(rows, what="nets")


def test_a_stored_row_may_not_smuggle_a_declaration_only_field() -> None:
    """``avoid`` is the script's; an override that carried it would be a
    second place to look for one value, and then a rule about which wins."""

    with pytest.raises(NetError, match="unrecognised keys \\['avoid'\\]"):
        canonical_rows(
            [_row("sda", "sen.sda", "esp.sda", avoid=["board"])], what="nets"
        )


def test_two_rows_may_not_share_a_name() -> None:
    with pytest.raises(NetError, match="repeats the row name"):
        canonical_rows(
            [_row("sda", "sen.sda", "esp.sda"), _row("sda", "sen.gnd", "esp.gnd")],
            what="nets",
        )


# --------------------------------------------------------------------------
# the override channel
# --------------------------------------------------------------------------


def test_stored_rows_replace_the_declared_table_wholesale() -> None:
    """A full list, not a patch — that is what lets the editor add and drop."""

    collector = NetsCollector(
        [
            # rewired onto a different terminal, regauged, joint dropped
            _row("sda", "sen.sda", "esp.scl", gauge_mm=1.2, solder=False),
            # a row the script never declared: the editor drew it
            _row("new", "sen.gnd", "esp.gnd", enabled=False),
        ]
    )
    table = collector(
        ports=_ports(),
        wires={
            "sda": wire("sen.sda", "esp.sda", gauge=0.8, solder=True, avoid=["board"]),
            "gone": wire("sen.scl", "esp.scl", gauge=0.8),
        },
    )

    assert table.names() == ("sda", "new")
    assert table["sda"].b.name == "scl"
    assert table["sda"].gauge == pytest.approx(1.2)
    assert table["sda"].solder is False
    # The addresses follow the *stored* row, not the declaration: a rewire
    # moved this wire's far end, and the joint the script sizes has to move
    # with it.
    assert table["sda"].a_address == "sen.sda"
    assert table["sda"].b_address == "esp.scl"
    # The declaration-only column survives a rewire: it is matched by row
    # name, and the row is still the one the script declared.
    assert table["sda"].avoid == ("board",)
    # An editor-added row has no declaration behind it, so no obstacles.
    assert table["new"].avoid == () and table["new"].enabled is False
    # "gone" was declared and is not in the stored list, so it is not built.
    assert "gone" not in table


def test_no_stored_rows_means_the_declared_table_stands() -> None:
    """Empty means "no overrides", never "no wires"."""

    specs = {
        "ports": [{"name": "sen", "terminals": SIGNALS}],
        "wires": [_row("sda", "sen.sda", "sen.gnd")],
    }
    assert effective_rows(specs, []) == specs["wires"]
    assert effective_rows(specs, None) == specs["wires"]


def test_a_row_naming_a_dropped_port_is_pruned_not_raised_on() -> None:
    """ADR-039's rule, on the connection table.

    A rewritten script that renamed a port must not wedge the editor
    forever, which is exactly what raising here would do.
    """

    specs = {"ports": [{"name": "sen", "terminals": SIGNALS}], "wires": []}
    stored = [
        _row("kept", "sen.sda", "sen.gnd"),
        _row("dropped_port", "sen.sda", "gone.sda"),
        _row("dropped_terminal", "sen.sda", "sen.miso"),
    ]
    assert [row["name"] for row in effective_rows(specs, stored)] == ["kept"]
    assert declared_ports(specs) == {"sen": SIGNALS}
    assert prune_rows(stored, {}) == []


def test_pruning_is_what_the_collector_applies_too() -> None:
    """The worker sees the same table the host stored, minus what it lost."""

    collector = NetsCollector(
        [_row("kept", "sen.sda", "esp.sda"), _row("stale", "sen.sda", "gone.sda")]
    )
    table = collector(ports=_ports(), wires={})
    assert table.names() == ("kept",)


def test_an_override_is_still_validated() -> None:
    """Lenient about what the script dropped, strict about what a row *is*."""

    with pytest.raises(NetError, match="gauge_mm must be greater than zero"):
        effective_rows(
            {"ports": [{"name": "sen", "terminals": SIGNALS}], "wires": []},
            [_row("x", "sen.sda", "sen.gnd", gauge_mm=0.0)],
        )
    with pytest.raises(NetError, match="connects 'sen.sda' to itself"):
        effective_rows(
            {"ports": [{"name": "sen", "terminals": SIGNALS}], "wires": []},
            [_row("x", "sen.sda", "sen.sda")],
        )


# --------------------------------------------------------------------------
# the revision
# --------------------------------------------------------------------------


def test_a_script_with_no_nets_keeps_a_byte_identical_revision() -> None:
    """The migration-free property, asserted rather than asserted-to.

    ``net_specs``/``net_values`` enter the revision payload only when
    non-empty, so every project written before ADR-065 hashes exactly as it
    did. Unlike ADR-064, nothing needs re-accepting.
    """

    from CadexScriptedDomains import project_script_revision

    base = dict(source="result = {}", param_specs=[], param_values={"w": 1.0})
    before = project_script_revision(**base)
    assert project_script_revision(**base, net_specs={}, net_values=[]) == before
    assert project_script_revision(**base, net_specs=None, net_values=None) == before

    specs = {"ports": [{"name": "sen", "terminals": SIGNALS}], "wires": []}
    assert project_script_revision(**base, net_specs=specs, net_values=[]) != before
    assert project_script_revision(
        **base, net_specs=specs, net_values=[_row("x", "sen.sda", "sen.gnd")]
    ) != project_script_revision(**base, net_specs=specs, net_values=[])


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


#: Two plates, three signals, and a harness built by iterating the table.
#: This is the shape a converted script takes: the comprehension over literal
#: pairs becomes a declaration, and the loop under it barely changes.
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
p = params(gap=num(30, unit="mm", min=10, max=90, step=1))

PITCH, T = 2.54, 1.6
DOWN = (0.0, 0.0, -1.0)
SIGNALS = ["sda", "scl", "gnd"]

sensor = part.box(20.0, 20.0, T, label="sensor")
esp = part.box(20.0, 20.0, T, origin=(20.0, 0.0, 0.0), label="esp")

row = dict(along=(0.0, 1.0, 0.0), axis=DOWN, pitch=PITCH, count=3,
           hole_dia=1.0, depth=T)
sen_t = part.terminals(sensor, header=dict(origin=(10.0, 5.0, T), **row),
                       names=SIGNALS)
esp_t = part.terminals(esp, header=dict(origin=(30.0, 5.0, T), **row),
                       names=SIGNALS)

n = nets(
    ports={"sen": sen_t, "esp": esp_t},
    wires={
        "sda": wire("sen.sda", "esp.sda", gauge=0.8, solder=True,
                    avoid=[sensor, esp]),
        "gnd": wire("sen.gnd", "esp.gnd", gauge=0.8, avoid=[sensor, esp]),
    },
)

result = {"sensor": sensor, "esp": esp}
for name, w in n.items():
    if not w.enabled:
        continue
    result["wire_" + name] = part.cable(w.a, w.b, gauge_mm=w.gauge,
                                        avoid=w.avoid, cell_mm=1.0)
    if w.solder:
        result["joint_" + name] = part.solder(w.a, gauge_mm=w.gauge)
"""

root = Path(tempfile.mkdtemp(prefix="cadex-nets-"))
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
    document = App.newDocument("NetsSeed")
    service = cadex_rebuild._RebuildService(root, document)
    store = CadexProjectScriptStore(root)

    declared = run(service, "xscript.project.write_script",
                   {"source": SCRIPT, "expected_revision": ""})
    report["declared_outputs"] = sorted(
        str(item["name"]) for item in declared["contract"])
    report["declared_digest"] = str(declared["digest"])
    state = store.read_state()
    report["net_specs"] = state.get("net_specs")
    report["net_values"] = state.get("net_values")

    wiring = attempt_report(store).get("wiring") or []
    report["wiring"] = [
        {
            "port": entry.get("port"),
            "output": entry.get("output"),
            "names": [t["name"] for t in entry.get("terminals") or []],
            "points": [t["point"] for t in entry.get("terminals") or []],
            "radii": [t["metrics"]["radius"] for t in entry.get("terminals") or []],
        }
        for entry in wiring
    ]

    # Rewire without the AI: sda now lands on esp.scl, gnd is switched off,
    # and a row the script never declared is added.
    rewired = run(service, "xscript.project.set_params", {
        "values": {},
        "nets": [
            {"name": "sda", "a": "sen.sda", "b": "esp.scl", "gauge_mm": 0.6,
             "solder": True, "enabled": True},
            {"name": "gnd", "a": "sen.gnd", "b": "esp.gnd", "gauge_mm": 0.8,
             "solder": False, "enabled": False},
            {"name": "extra", "a": "sen.scl", "b": "esp.gnd", "gauge_mm": 0.6,
             "solder": False, "enabled": True},
        ],
        "expected_revision": revision(store),
    })
    report["rewired_outputs"] = sorted(
        str(item["name"]) for item in rewired["contract"])
    report["rewired_digest"] = str(rewired["digest"])
    report["stored_rows"] = [
        r["name"] for r in store.read_state().get("net_values") or []]

    # A slider still moves on its own, with the stored rows untouched.
    dragged = run(service, "xscript.project.set_params",
                  {"values": {"gap": 44.0}, "expected_revision": revision(store)})
    report["drag_ok"] = True
    report["rows_after_drag"] = [
        r["name"] for r in store.read_state().get("net_values") or []]

    # A row naming a terminal that does not exist is refused at declaration
    # time, inside the worker, so the run fails and the store rolls back.
    before = revision(store)
    try:
        run(service, "xscript.project.set_params", {
            "values": {},
            "nets": [{"name": "sda", "a": "sen.sda", "b": "esp.miso",
                      "gauge_mm": 0.8}],
            "expected_revision": before,
        })
    except DomainRuntimeFailure as failure:
        payload = dict(failure.payload)
        report["bad_terminal_refused"] = True
        report["bad_terminal_code"] = str(payload.get("failure_code") or "")
        report["bad_terminal_error"] = str(payload.get("error") or "")
    except AssertionError:
        report["bad_terminal_refused"] = True
        report["bad_terminal_code"] = "WORKER"
        report["bad_terminal_error"] = ""
    else:
        report["bad_terminal_refused"] = False
        report["bad_terminal_code"] = "NOT-RAISED"
        report["bad_terminal_error"] = ""
    report["revision_rolled_back"] = revision(store) == before
    report["rows_after_refusal"] = [
        r["name"] for r in store.read_state().get("net_values") or []]

    report["ok"] = True
finally:
    shutil.rmtree(root, ignore_errors=True)

print("NETS-E2E " + json.dumps(report, sort_keys=True))
'''


def _drive(tmp_path) -> dict:
    driver = tmp_path / "nets_driver.py"
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
            if line.startswith("NETS-E2E ")
        ),
        None,
    )
    assert marker, (
        f"nets driver produced no report; exit={completed.returncode}\n"
        f"stdout:\n{completed.stdout[-6000:]}\nstderr:\n{completed.stderr[-6000:]}"
    )
    return json.loads(marker.removeprefix("NETS-E2E "))


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available to build a harness."
)
def test_a_declared_harness_builds_and_rewires_without_the_ai(tmp_path) -> None:
    report = _drive(tmp_path)
    assert report.get("ok") is True, report

    # The declared table builds exactly what the loop under it asks for.
    assert report["declared_outputs"] == [
        "esp", "joint_sda", "sensor", "wire_gnd", "wire_sda"
    ], report

    # The spec cache is what the editor reads its columns from.
    specs = report["net_specs"]
    assert specs["ports"] == [
        {"name": "sen", "terminals": ["sda", "scl", "gnd"]},
        {"name": "esp", "terminals": ["sda", "scl", "gnd"]},
    ], specs
    assert [row["name"] for row in specs["wires"]] == ["sda", "gnd"]
    assert specs["wires"][0]["solder"] is True
    # Nothing is stored until something overrides: the declaration is the
    # default, in exactly the sense num()'s default is one.
    assert report["net_values"] == []

    # The registry the shell draws from: terminals resolved by the run that
    # built the geometry, joined to their port and their output.
    wiring = {entry["port"]: entry for entry in report["wiring"]}
    assert set(wiring) == {"sen", "esp"}, report["wiring"]
    assert wiring["esp"]["output"] == "esp"
    assert wiring["sen"]["names"] == ["sda", "scl", "gnd"]
    assert all(radius == pytest.approx(0.5) for radius in wiring["sen"]["radii"])
    # The header is drilled down from z=1.6 and the landing *is* its origin
    # since ADR-117, so every point is in the top face, in the plate's own
    # coordinates — not a board thickness below it.
    assert all(
        point[2] == pytest.approx(1.6, abs=1.0e-9)
        for point in wiring["sen"]["points"]
    )
    assert [round(point[1], 4) for point in wiring["sen"]["points"]] == [
        5.0, 7.54, 10.08
    ]

    # The rewire: sda moved, gnd switched off, a row the script never wrote
    # added — and the geometry followed, with no chat turn anywhere.
    assert report["rewired_outputs"] == [
        "esp", "joint_sda", "sensor", "wire_extra", "wire_sda"
    ], report
    assert report["rewired_digest"] != report["declared_digest"]
    assert report["stored_rows"] == ["sda", "gnd", "extra"]

    # A slider still moves on its own, and does not disturb the rows.
    assert report["drag_ok"] is True
    assert report["rows_after_drag"] == ["sda", "gnd", "extra"]

    # An endpoint the ports do not have is a refusal, not a silent miswire —
    # and a refused candidate leaves the working state exactly as it was.
    assert report["bad_terminal_refused"] is True, report
    assert report["bad_terminal_code"] == "UNKNOWN_PROJECT_NET_ENDPOINT", report
    assert "miso" in report["bad_terminal_error"], report
    assert report["revision_rolled_back"] is True, report
    assert report["rows_after_refusal"] == ["sda", "gnd", "extra"], report


# --------------------------------------------------------------------------
# the host-side override check
# --------------------------------------------------------------------------


def _state(ports: dict[str, list[str]], wires=()):
    return {
        "net_specs": {
            "ports": [
                {"name": name, "terminals": list(terminals)}
                for name, terminals in ports.items()
            ],
            "wires": list(wires),
        }
    }


def test_a_request_naming_an_undeclared_endpoint_stays_loud() -> None:
    """ADR-039's strict half. The lenient half is on the *stored* rows."""

    from CadexScriptedRuntime import DomainRuntimeFailure, _project_net_values

    state = _state({"sen": SIGNALS, "esp": SIGNALS})
    for bad, needle in (
        (_row("x", "sen.sda", "nope.sda"), "nope"),
        (_row("x", "sen.sda", "esp.miso"), "miso"),
    ):
        with pytest.raises(DomainRuntimeFailure) as caught:
            _project_net_values(state, [bad], "xscript.project.set_params")
        payload = dict(caught.value.payload)
        assert payload.get("failure_code") == "UNKNOWN_PROJECT_NET_ENDPOINT", payload
        assert needle in str(payload.get("error") or ""), payload


def test_a_malformed_request_row_is_refused_by_shape() -> None:
    from CadexScriptedRuntime import DomainRuntimeFailure, _project_net_values

    with pytest.raises(DomainRuntimeFailure) as caught:
        _project_net_values(
            _state({"sen": SIGNALS}),
            [{"name": "x", "a": "sen.sda"}],
            "xscript.project.set_params",
        )
    assert dict(caught.value.payload).get("failure_code") == "INVALID_PROJECT_NET"


def test_a_valid_request_passes_through_verbatim() -> None:
    from CadexScriptedRuntime import _project_net_values

    rows = [_row("sda", "sen.sda", "esp.sda", solder=True)]
    assert _project_net_values(_state({"sen": SIGNALS, "esp": SIGNALS}), rows, "t") == [
        {
            "name": "sda",
            "a": "sen.sda",
            "b": "esp.sda",
            "gauge_mm": 0.8,
            "solder": True,
            "enabled": True,
        }
    ]


def test_a_script_that_has_never_declared_nets_defers_to_the_worker() -> None:
    """No port list to check against yet; the run itself is the check."""

    from CadexScriptedRuntime import _project_net_values

    rows = [_row("x", "sen.sda", "esp.sda")]
    assert _project_net_values({}, rows, "t")[0]["name"] == "x"
