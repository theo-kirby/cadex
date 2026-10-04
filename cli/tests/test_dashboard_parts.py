# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The viewer paints each part by its appearance role and lists the parts (ADR-522).

The shell painted shell / mechanism / accent onto its viewport
(``cadex_roles.py``) and kept a printable-part roster (``cadex_print.py``,
the Parameters editor). The dashboard reads the same facts the engine
publishes in the accepted ``result.json`` — the role a component declared,
the catalog row its output came off, the assembly's palette, and the
printable roster ``export_printable`` checks against — and colours them
with ``CadexStudio.materials``, the rule ``look`` and the concept sheet
draw with. Proved against a real engine: the roles agree with what
``inspect scope=inventory`` tells the agent, and headless Chromium shows
each part's role, colour, supplier and print status.
"""

from __future__ import annotations

import pytest

from cadex_cli.__main__ import main
from cadex_cli.client import CadexdClient, open_project
from cadex_cli.inventory import read_inventory
from cadex_cli.report import EXIT_OK
from cadex_cli.review_server import part_looks, serve_projects
from cadex_cli.studio import STUDIO
from test_review_server import _json, _model_state, _open, browser, needs_browser  # noqa: F401

#: A printed plate in a recoloured shell, a catalog bolt (purchased, so
#: mechanism by supplier) and a printed cap that declares itself accent.
RIG = """
plate = part.box(40.0, 20.0, 4.0)
bolt = lib.bolt("M3", 12.0, origin=[10.0, 10.0, 4.0]).body
cap_body = part.box(8.0, 8.0, 3.0, origin=[26.0, 6.0, 4.0])
base = assembly.component(plate, grounded=True)
screw = assembly.component(bolt)
cap = assembly.component(cap_body, appearance="accent")
asm = assembly.assembly([base, screw, cap], palette={"shell": "#C9AE86"})
diag = assembly.solve(asm)
result = {"plate": plate, "bolt": bolt, "cap_body": cap_body,
          "base": base, "screw": screw, "cap": cap, "asm": asm, "diag": diag}
"""

MECHANISM = "#%02X%02X%02X" % STUDIO.ROLE_COLORS["mechanism"]
ACCENT = "#%02X%02X%02X" % STUDIO.ROLE_COLORS["accent"]


def test_no_assembly_keeps_index_colours_and_a_bad_role_says_why() -> None:
    entries = [{"name": "plate", "output": "plate"}]
    block = part_looks({"outputs": [{"name": "plate", "type": "solid", "artifact_kind": "brep"},
                                    {"name": "note", "type": "measurement"}]}, entries)
    assert block["available"] is False and "no assembly" in block["reason"]
    assert block["printable"] == ["plate"]
    assert entries == [{"name": "plate", "output": "plate", "role": None, "color": None,
                        "role_source": None, "supplier": None, "printable": True}]
    link = {"name": "c", "type": "component_link",
            "definition": {"properties": {"appearance": "chrome"}}}
    entries = [{"name": "c", "output": "plate"}]
    block = part_looks({"outputs": [{"name": "plate", "type": "solid", "artifact_kind": "brep"}, link]}, entries)
    assert block["available"] is False and "unknown appearance role chrome" in block["reason"]
    assert entries[0]["role"] is None and entries[0]["printable"] is True


@pytest.fixture
def rig_app(engine, tmp_path, capsys):
    projects = tmp_path / "projects"
    source = tmp_path / "rig.py"
    source.write_text(RIG, encoding="utf-8")
    assert main(["script", "--set", str(source), "--project", str(projects / "rig"), "--json"]) == EXIT_OK
    capsys.readouterr()
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        yield projects / "rig", server
    finally:
        server.shutdown()
        server.server_close()


def test_the_roles_are_the_ones_the_agent_reads_from_the_inventory(engine, rig_app) -> None:
    root, server = rig_app
    model = _json(server.url + "p/rig/api/model/accepted")
    assert model["available"] is True and model["appearance"]["available"] is True
    parts = {c["name"]: c for c in model["components"]}
    assert {name: (c["role"], c["color"], c["role_source"], c["supplier"], c["printable"])
            for name, c in parts.items()} == {
        "base": ("shell", "#C9AE86", "supplier", "printed", True),
        "screw": ("mechanism", MECHANISM, "supplier", "purchased", True),
        "cap": ("accent", ACCENT, "declared", "printed", True),
    }
    assert model["appearance"]["palette"] == {"shell": "#C9AE86", "mechanism": MECHANISM, "accent": ACCENT}
    assert {"plate", "bolt", "cap_body"} <= set(model["appearance"]["printable"])
    with CadexdClient(engine) as client:
        open_project(client, root)
        inventory = read_inventory(client)
        script = client.request("inspect", {"scope": "script", "path": "/printable/outputs", "limit": 50})
    assert script["ok"], script
    rows = {row["component"]: row for row in inventory["components"]}
    assert {name: row.get("appearance") for name, row in rows.items()} == {"base": None, "screw": None, "cap": "accent"}
    assert sorted(inventory["uncatalogued_sources"]) == ["cap_body", "plate"]
    assert "catalog" in rows["screw"] and inventory["palette"] == {"shell": "#C9AE86"}
    roster = {entry["name"] for entry in script["value"]}
    assert set(model["appearance"]["printable"]) == roster
