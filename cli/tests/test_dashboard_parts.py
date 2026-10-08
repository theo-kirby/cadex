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
#: A catalog bolt is drawn black-oxide steel whatever its role (ADR-603).
BLACK_OXIDE = "#%02X%02X%02X" % STUDIO.METALS["black_oxide"][0]


def test_no_assembly_keeps_index_colours_and_a_bad_role_says_why() -> None:
    entries = [{"name": "plate", "output": "plate"}]
    block = part_looks({"outputs": [{"name": "plate", "type": "solid", "artifact_kind": "brep"},
                                    {"name": "note", "type": "measurement"}]}, entries)
    assert block["available"] is False and "no assembly" in block["reason"]
    assert block["printable"] == ["plate"]
    assert entries == [{"name": "plate", "output": "plate", "role": None, "color": None,
                        "role_source": None, "supplier": None, "finish": None, "catalog": None,
                        "board": None, "printable": True}]
    link = {"name": "c", "type": "component_link",
            "definition": {"properties": {"appearance": "chrome"}}}
    entries = [{"name": "c", "output": "plate"}]
    block = part_looks({"outputs": [{"name": "plate", "type": "solid", "artifact_kind": "brep"}, link]}, entries)
    assert block["available"] is False and "unknown appearance role chrome" in block["reason"]
    assert entries[0]["role"] is None and entries[0]["printable"] is True


def _board_points(spec, shift=(0.0, 0.0, 0.0)):
    """The corners of a catalog board's PCB and chip box, as lib.board builds them."""
    w, l, t = spec["width_mm"], spec["length_mm"], spec["thickness_mm"]
    (ox, oy, oz), (sx, sy, sz) = spec["cosmetic_origin"], spec["cosmetic_size"]
    corners = [(x, y, z) for x in (0.0, w) for y in (0.0, l) for z in (0.0, t)]
    corners += [(x, y, z) for x in (ox, ox + sx) for y in (oy, oy + sy) for z in (oz, oz + sz)]
    return [(x + shift[0], y + shift[1], z + shift[2]) for x, y, z in corners]


def test_each_part_carries_its_finish_catalog_row_and_board_layout() -> None:
    """ADR-603's contract for the viewport: ``finish``, ``catalog`` and, on a
    board whose mesh is the catalog's, ``board`` in the part's mesh frame.
    Hardware and boards take the finish's colour over the role they declare."""

    def link(name, source, **properties):
        return {"name": name, "type": "component_link", "source_output": source,
                "definition": {"arguments": [{"object_name": source}], "properties": properties}}
    outputs = [
        {"name": "plate", "type": "solid", "artifact_kind": "brep"},
        {"name": "bolt", "type": "solid", "artifact_kind": "brep",
         "catalog": {"family": "bolt", "part_number": "m3x12-socket"}},
        {"name": "washer", "type": "solid", "artifact_kind": "brep",
         "catalog": {"family": "washer", "part_number": "m3"}},
        {"name": "insert", "type": "solid", "artifact_kind": "brep",
         "catalog": {"family": "heat_insert", "part_number": "m3"}},
        {"name": "esp", "type": "solid", "artifact_kind": "brep",
         "catalog": {"family": "board", "part_number": "esp32-devkitc-v4"}},
        {"name": "imu", "type": "solid", "artifact_kind": "brep",
         "catalog": {"family": "board", "part_number": "bno085-adafruit-4754"}},
        {"name": "servo", "type": "solid", "artifact_kind": "brep",
         "catalog": {"family": "servo", "part_number": "mg90s"}},
        link("c_plate", "plate"), link("c_bolt", "bolt", appearance="accent"),
        link("c_washer", "washer"), link("c_insert", "insert"),
        link("c_esp", "esp", appearance="shell"), link("c_imu", "imu"),
        link("c_servo", "servo", appearance="accent"),
        {"name": "asm", "type": "assembly", "definition": {"properties": {}}},
    ]
    entries = [{"name": item["name"], "output": item["source_output"]}
               for item in outputs if item["type"] == "component_link"]
    esp = STUDIO._board_spec("esp32-devkitc-v4")
    imu = STUDIO._board_spec("bno085-adafruit-4754")
    # The ESP32 mesh was moved before it was published; the IMU's is not the
    # catalog board at all (a script cut it 2 mm narrower).
    meshes = {"esp": _board_points(esp, (32.0, -18.0, 12.0)),
              "imu": [(x * 0.9, y, z) for x, y, z in _board_points(imu)]}
    block = part_looks({"outputs": outputs}, entries, meshes.get)
    assert block["available"] is True and block["finishes"]["classes"] == list(STUDIO.FINISH_CLASSES)
    parts = {entry["name"]: entry for entry in entries}
    hexes = {name: "#%02X%02X%02X" % rgb for name, (rgb, _finish) in STUDIO.METALS.items()}
    mask = "#%02X%02X%02X" % STUDIO.BOARD_LOOK["mask"][0]
    assert {name: (e["role"], e["color"], e["finish"]) for name, e in parts.items()} == {
        "c_plate": ("shell", "#%02X%02X%02X" % STUDIO.ROLE_COLORS["shell"], "printed"),
        "c_bolt": ("accent", hexes["black_oxide"], "hardware"),     # declared accent, still metal
        "c_washer": ("mechanism", hexes["steel"], "hardware"),
        "c_insert": ("mechanism", hexes["brass"], "hardware"),
        "c_esp": ("shell", mask, "board"),                          # declared shell, still a PCB
        "c_imu": ("mechanism", mask, "board"),
        "c_servo": ("accent", ACCENT, "purchased"),                 # keeps its role colour
    }
    assert parts["c_plate"]["catalog"] is None
    assert parts["c_servo"]["catalog"] == {"family": "servo", "part_number": "mg90s"}
    board = parts["c_esp"]["board"]
    assert (board["width_mm"], board["length_mm"], board["thickness_mm"]) == (27.94, 48.26, 1.6)
    assert board["chip"] == {"origin": [4.97 + 32.0, 23.0 - 18.0, 1.6 + 12.0], "size": [18.0, 31.3, 3.0]}
    assert len(board["pads"]) == len(esp["terminals"])
    first = esp["terminals"][0]
    assert board["pads"][0] == {"origin": [round(first["origin"][0] + 32.0, 4), round(first["origin"][1] - 18.0, 4),
                                           round(first["origin"][2] + 12.0, 4)],
                                "dia_mm": round(first["hole_dia"] + 2 * STUDIO.PAD_RING_MM, 4)}
    assert parts["c_imu"]["board"] is None                         # mismatched mesh: plain mask
    assert all(parts[name]["board"] is None for name in parts if name not in {"c_esp"})


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
        "screw": ("mechanism", BLACK_OXIDE, "supplier", "purchased", True),
        "cap": ("accent", ACCENT, "declared", "printed", True),
    }
    assert {name: (c["finish"], c["catalog"], c["board"]) for name, c in parts.items()} == {
        "base": ("printed", None, None),
        "screw": ("hardware", {"family": "bolt", "part_number": parts["screw"]["catalog"]["part_number"]}, None),
        "cap": ("printed", None, None),
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
