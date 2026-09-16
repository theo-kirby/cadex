# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``cadex inventory``: the parts of an assembly, with catalog ids (ADR-236).

The first of the headless review calls, and the one the walk's review step
needs before any of the others are worth having: an agent that cannot say
*what* it assembled cannot check it.

One real engine run, one real assembly of catalogued hardware, one process
interface — the same bar ``test_linked_part`` sets, because what a pipeline
branches on is the exit status and the file that lands. The rendering half
needs no engine and is checked directly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cadex_cli.__main__ import main
from cadex_cli.inventory import (
    INVENTORY_DOC_NAME, inventory_summary, render_inventory,
)
from cadex_cli.report import EXIT_OK

#: A plate with two catalogued M3 bolts standing on it. `plate` is modelled
#: by hand and the bolts come off `lib.bolt`, so one accepted revision
#: exercises both sides of the join: a component with a catalog row and one
#: without.
RIG = """
plate = part.box(40.0, 20.0, 4.0)
bolt_a = lib.bolt("M3", 12.0, origin=[10.0, 10.0, 4.0]).body
bolt_b = lib.bolt("M3", 16.0, origin=[30.0, 10.0, 4.0]).body
base = assembly.component(plate, grounded=True)
first = assembly.component(bolt_a)
second = assembly.component(bolt_b)
asm = assembly.assembly([base, first, second])
diag = assembly.solve(asm)
result = {"plate": plate, "bolt_a": bolt_a, "bolt_b": bolt_b,
          "base": base, "first": first, "second": second,
          "asm": asm, "diag": diag}
"""


def _run(capsys, *argv: str) -> tuple[int, dict]:
    code = main([*argv, "--json"])
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def rig_project(engine, tmp_path, capsys):
    script = tmp_path / "rig.py"
    script.write_text(RIG, encoding="utf-8")
    root = tmp_path / "rig"
    code, envelope = _run(capsys, "script", "--set", str(script), "--project", str(root))
    assert code == EXIT_OK, envelope
    return root


def test_inventory_lands_a_doc_naming_every_part_and_its_catalog_id(
    rig_project, capsys
) -> None:
    code, envelope = _run(capsys, "inventory", "--project", str(rig_project))
    assert code == EXIT_OK, envelope

    path = Path(rig_project) / "docs" / INVENTORY_DOC_NAME
    assert path.is_file(), envelope
    text = path.read_text(encoding="utf-8")

    # The three components, each naming the output it places.
    for component in ("base", "first", "second"):
        assert f"| `{component}` |" in text, text
    assert "`plate`" in text and "`bolt_a`" in text and "`bolt_b`" in text

    # The catalog ids — the whole point, and unavailable before ADR-236:
    # both bodies are ordinary part solids by the time the script returns
    # them, so nothing downstream could have said which row they came off.
    assert "bolt `m3x12-socket`" in text, text
    assert "bolt `m3x16-socket`" in text, text
    assert "bolt/m3x12-socket` × 1" in text, text
    # ...and the hand-modelled plate is named as having none rather than
    # silently dropped.
    assert "## Not from the catalog" in text and "- `plate`" in text, text

    assert any("inventory: 3 component(s), 2 catalogued" in note
               for note in envelope["notes"]), envelope


def test_inventory_is_repeatable_and_names_a_wrong_assembly(rig_project, capsys) -> None:
    path = Path(rig_project) / "docs" / INVENTORY_DOC_NAME

    code, _ = _run(capsys, "inventory", "--project", str(rig_project))
    assert code == EXIT_OK
    first = path.read_text(encoding="utf-8")
    code, _ = _run(capsys, "inventory", "--project", str(rig_project))
    assert code == EXIT_OK
    # Generated and overwritten, not appended: two runs of an unchanged
    # model leave the same file.
    assert path.read_text(encoding="utf-8") == first

    code, envelope = _run(
        capsys, "inventory", "--project", str(rig_project), "--assembly", "nope"
    )
    assert code != EXIT_OK
    assert "nope" in envelope["error"] and "asm" in envelope["error"], envelope


# -- the rendering half, which needs no engine ---------------------------


def test_a_component_with_no_catalog_row_still_gets_a_row() -> None:
    text = render_inventory(
        {
            "revision": "f" * 64,
            "assembly": "asm",
            "components": [
                {
                    "component": "base",
                    "source_output": "plate",
                    "grounded": True,
                    "placement": {"position_mm": [0.0, 0.0, 0.0]},
                    "source_facts": {"volume_mm3": 3200.0},
                },
                {
                    "component": "bolt",
                    "source_output": "m3",
                    "catalog": {"family": "bolt", "part_number": "m3x12-socket"},
                },
            ],
            "catalog_counts": {"bolt/m3x12-socket": 1},
            "uncatalogued_sources": ["plate"],
        },
        name="rig",
    )

    assert "# Inventory — rig" in text
    assert "2 component(s)" in text
    assert "| `base` | `plate` | — | 0.000, 0.000, 0.000 | 3200.000 |" in text
    # An unsolved or artifact-less component reports em dashes rather than
    # inventing a pose or a volume.
    assert "| `bolt` | `m3` | bolt `m3x12-socket` | — | — |" in text


@pytest.mark.parametrize("large_rows", [False, True])
def test_inventory_expands_real_inspection_previews(monkeypatch, tmp_path, large_rows):
    """Exercise the engine's 1 KiB previews and 50-entry pages, not a mock pager."""
    from conftest import SOURCE_MODULE_DIR

    monkeypatch.syspath_prepend(str(SOURCE_MODULE_DIR))
    import CadexInspection
    from cadex_cli.inventory import write_inventory

    suffix = "x" * 1400 if large_rows else ""
    rows = [
        {
            "component": f"component_{i:02d}{suffix}",
            "source_output": f"output_{i:02d}",
            "catalog": {"family": "bolt", "part_number": f"catalog-part-{i:02d}"},
            "placement": {"position_mm": [1.0, 2.0, 3.0]},
            "source_facts": {"volume_mm3": 10.0},
        }
        for i in range(60)
    ]
    raw = {
        "ok": True,
        "revision": "f" * 64,
        "assembly": "asm",
        "components": rows,
        "catalog_counts": {f"bolt/catalog-part-{i:02d}": i + 1 for i in range(60)},
        "uncatalogued_sources": [f"hand_modelled_output_{i:02d}{suffix}" for i in range(60)],
    }
    calls = []

    class Client:
        def request(self, op, arguments):
            assert op == "inspect"
            assert arguments["scope"] == "inventory"
            assert arguments["target"] == "asm"
            calls.append(arguments)
            return CadexInspection._bounded_page(raw, {"limit": 50, **arguments})

    preview = Client().request("inspect", {"scope": "inventory", "target": "asm"})
    for key in ("components", "catalog_counts", "uncatalogued_sources"):
        assert preview["value"][key]["inspect_path"] == f"/{key}"
    if large_rows:
        page = CadexInspection._bounded_page(raw, {"path": "/components", "limit": 50})
        assert page["value"][0]["inspect_path"] == "/components/0"

    path, value = write_inventory(Client(), tmp_path, target="asm")
    text = path.read_text(encoding="utf-8")
    assert "60 component(s)" in text
    for row in rows:
        assert f'| `{row["component"]}` | `{row["source_output"]}` |' in text
        assert f'bolt `{row["catalog"]["part_number"]}` | 1.000, 2.000, 3.000 | 10.000 |' in text
    for key, count in raw["catalog_counts"].items():
        assert f"- `{key}` × {count}\n" in text
    for name in raw["uncatalogued_sources"]:
        assert f"- `{name}`\n" in text
    for key in ("components", "catalog_counts", "uncatalogued_sources"):
        assert value[key] == raw[key]
        assert any(call.get("path") == f"/{key}" and call.get("offset", 0) > 0
                   for call in calls)


def test_part_only_inventory_is_explicitly_unavailable(engine, tmp_path, capsys):
    root = tmp_path / "part-only"
    source = tmp_path / "part.py"
    source.write_text("plate = part.box(10, 20, 3)\nresult = {'plate': plate}\n")
    code, envelope = _run(capsys, "script", "--set", str(source), "--project", str(root))
    assert code == EXIT_OK, envelope
    code, envelope = _run(capsys, "inventory", "--project", str(root))
    assert code == EXIT_OK, envelope
    text = (root / "docs/inventory.md").read_text()
    assert "0 component(s)" in text
    assert "Inventory unavailable: no published assembly." in text


def test_inventory_summary_counts_components_and_names_sources() -> None:
    """The build-reply block (ADR-362), from a published inventory value.

    Known answer: five components; two catalogued MG90S servos; a hand
    bracket and one drilled servo body placed twice, so three uncatalogued
    components over two uncatalogued sources. Counts are per component,
    names per source, and the order of the names is sorted, not placed.
    """

    value = {
        "revision": "r" * 64, "assembly": "asm",
        "components": [
            {"component": "c1", "source_output": "servo",
             "catalog": {"family": "servo", "part_number": "MG90S"}},
            {"component": "c2", "source_output": "servo",
             "catalog": {"family": "servo", "part_number": "MG90S"}},
            {"component": "c3", "source_output": "servo_cut"},
            {"component": "c4", "source_output": "servo_cut"},
            {"component": "c5", "source_output": "bracket"},
        ],
        "catalog_counts": {"servo/MG90S": 2},
        "uncatalogued_sources": ["servo_cut", "bracket"],
    }
    summary = inventory_summary(value)
    assert summary["available"] is True
    assert summary["revision"] == "r" * 64 and summary["assembly"] == "asm"
    assert summary["component_count"] == 5
    assert summary["catalogued_count"] == 2
    assert summary["uncatalogued_count"] == 3
    assert summary["catalog_counts"] == {"servo/MG90S": 2}
    assert summary["uncatalogued_sources"] == ["bracket", "servo_cut"]
    assert "Advisory" in summary["source"]
    assert "lost its catalog identity" in summary["note"]

    empty = inventory_summary({"revision": "r" * 64, "assembly": ""})
    assert empty["available"] is False
    assert empty["component_count"] == 0 and empty["uncatalogued_sources"] == []
    assert "places none" in empty["note"]

    clean = inventory_summary({
        "revision": "r", "assembly": "asm",
        "components": [{"component": "c1", "source_output": "servo",
                        "catalog": {"family": "servo", "part_number": "MG90S"}}],
        "catalog_counts": {"servo/MG90S": 1}, "uncatalogued_sources": [],
    })
    assert clean["uncatalogued_count"] == 0 and "note" not in clean
    assert inventory_summary(None)["available"] is False
