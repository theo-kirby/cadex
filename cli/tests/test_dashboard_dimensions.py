# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The viewer draws the script's declared dimensions over the solids (ADR-524).

The shell's ``cadex_dimension.py`` drew each declared ``part.measurement``
in its viewport: two exact anchors from the engine, everything else laid out
in screen space, collapsing to a leader when seen end-on. The dashboard
draws the same records, from the accepted ``result.json``, on the component
that shows the measured output. Proved against a real engine: the numbers
are the engine's, the anchors land where the placed solid is, the overlay
re-lays itself out as the camera moves, and an end-on extent becomes a
leader. Re-derived from the description of the shell module; nothing copied.
"""

from __future__ import annotations

import json
import math

import pytest

from cadex_cli.__main__ import main
from cadex_cli.report import EXIT_OK
from cadex_cli.review_server import declared_measurements, serve_projects
from test_review_server import _json, _model_state, _open, browser, needs_browser  # noqa: F401

#: A bored plate placed turned 90° about Z and lifted, with an extent and a
#: diameter on the placed part, and an extent on an undeclared intermediate that a
#: placed design cannot draw.
PLACED = """
plate  = part.box(60, 40, 10)
bored  = part.cut(plate, part.cylinder(3, 20))
height = part.measurement(bored, kind="extent", axis="z", label="overall height")
bore   = part.measurement(bored, kind="diameter", at={"geometry_type": "Cylinder", "radius": 3.0})
width  = part.measurement(plate, kind="extent", axis="x")
base = assembly.component(bored, grounded=True,
                          placement={"position": [12, 30, 6], "axis": [0, 0, 1], "angle_degrees": 90})
asm = assembly.assembly([base])
diag = assembly.solve(asm)
result = {"bored": bored, "height": height, "bore": bore, "width": width,
          "base": base, "asm": asm, "diag": diag}
"""


def test_each_record_is_drawn_on_the_component_that_shows_its_output() -> None:
    record = {"kind": "extent", "text": "10.00 mm", "anchors_mm": [[0, 0, 0], [0, 0, 10]]}
    result = {"outputs": [
        {"name": "left", "type": "solid"},
        {"name": "h", "type": "measurement", "measurement": {**record, "subject": "left"}},
        {"name": "free", "type": "measurement", "measurement": {**record, "subject": ""}},
        {"name": "gone", "type": "measurement", "measurement": {**record, "subject": "hidden"}},
    ]}
    entries = [{"name": "a", "output": "left", "mesh": "mesh/accepted/left.stl"},
               {"name": "b", "output": "left", "mesh": "mesh/accepted/left.stl"}]
    block = declared_measurements(result, entries)
    assert block["available"] is True and "exact BREP" in block["source"]
    rows = {row["name"]: row for row in block["records"]}
    assert (rows["h"]["component"], rows["h"]["drawn"]) == ("a", True)
    assert rows["h"]["reason"] == "drawn on a only; b show the same output"
    assert rows["h"]["text"] == "10.00 mm" and rows["h"]["anchors_mm"] == [[0, 0, 0], [0, 0, 10]]
    assert (rows["free"]["component"], rows["free"]["drawn"]) == (None, True)
    assert rows["free"]["frame"].startswith("model coordinates")
    placed = declared_measurements(result, [{**entries[0], "placement": {"position_mm": [0, 0, 5],
                                                                         "rotation_xyzw": [0, 0, 0, 1]}}])
    free = {row["name"]: row for row in placed["records"]}["free"]
    assert free["drawn"] is False and "part frame the viewer cannot place" in free["reason"]
    assert (rows["gone"]["drawn"], rows["gone"]["reason"]) == (False, "measures hidden, which the viewer does not show")
    empty = declared_measurements({"outputs": [{"name": "left", "type": "solid"}]}, entries)
    assert empty == {"available": False, "records": [], "reason": "the script declares no part.measurement"}


@pytest.fixture
def placed_app(engine, tmp_path, capsys):
    projects = tmp_path / "projects"
    source = tmp_path / "placed.py"
    source.write_text(PLACED, encoding="utf-8")
    assert main(["script", "--set", str(source), "--project", str(projects / "orun2-dims"), "--json"]) == EXIT_OK
    capsys.readouterr()
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        yield projects / "orun2-dims", server
    finally:
        server.shutdown()
        server.server_close()


def _rotate(quaternion, point):
    x, y, z, w = quaternion
    px, py, pz = point
    # v' = v + 2w(q × v) + 2 q × (q × v)
    cx, cy, cz = y * pz - z * py, z * px - x * pz, x * py - y * px
    ccx, ccy, ccz = y * cz - z * cy, z * cx - x * cz, x * cy - y * cx
    return [px + 2 * (w * cx + ccx), py + 2 * (w * cy + ccy), pz + 2 * (w * cz + ccz)]


def test_the_manifest_carries_the_engine_s_numbers_in_the_part_s_frame(engine, placed_app) -> None:
    _root, server = placed_app
    model = _json(server.url + "p/orun2-dims/api/model/accepted")
    block = model["measurements"]
    assert block["available"] is True
    rows = {row["name"]: row for row in block["records"]}
    assert {name: (row["kind"], row["text"], row["component"], row["drawn"]) for name, row in rows.items()} == {
        "height": ("extent", "10.00 mm", "base", True),
        "bore": ("diameter", "Ø6.00 mm", "base", True),
        "width": ("extent", "60.00 mm", None, False),
    }
    assert rows["height"]["value_mm"] == pytest.approx(10.0) and rows["bore"]["radius_mm"] == pytest.approx(3.0)
    assert rows["height"]["label"] == "overall height"
    # The anchors are in the part's own frame; the placement carries them to the world.
    base = {c["name"]: c for c in model["components"]}["base"]
    world = [a + b for a, b in zip(_rotate(base["placement"]["rotation_xyzw"], rows["height"]["anchors_mm"][0]),
                                   base["placement"]["position_mm"])]
    assert world == pytest.approx([-8.0, 60.0, 6.0], abs=1e-6)


def _overlay(page):
    return page.evaluate(
        "Array.from(document.querySelectorAll('#dimension-overlay g[data-measurement]')).map(g => ({"
        "name: g.dataset.measurement, form: g.dataset.form, text: g.querySelector('text').textContent,"
        "lines: Array.from(g.querySelectorAll('line')).map(l => ['x1','y1','x2','y2'].map(k => +l.getAttribute(k)))}))")
