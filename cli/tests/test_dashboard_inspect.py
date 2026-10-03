# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The dashboard's inspection views, orun2 D2 item 5.

The collision view's t=0 contact readout (ADR-508): which parts' collision
shapes already touch at the pose every simulation starts from. The engine
measured it when it exported the MJCF; the page lists it under the
collision toggle, and the agent reads the same block through ``inspect
scope=contacts``, so a person and the agent see one fact. Proved against a
real engine in headless Chromium: a post sunk 2 mm into the floor is named,
the page's own slider lifts it clear, and the readout empties.
"""

from __future__ import annotations

import json

import pytest

from cadex_cli.__main__ import main
from cadex_cli.client import CadexdClient, open_project
from cadex_cli.report import EXIT_OK
from cadex_cli.review_server import initial_contacts, serve_projects
from test_review_server import _json, _model_state, _open, browser, needs_browser  # noqa: F401

#: A floor, a block that slides on it and a post that slides on the block.
#: The joints exclude block/floor and block/post from contact, so the one
#: pair that can touch is floor/post, and ``sink`` pushes the post into the
#: floor. Measured on a real build: at 2 mm MuJoCo reports four points,
#: each at -2.0 mm; at 0 mm, face on face, it reports none.
REST = """
p = params(sink=num(2.0, unit="mm", min=0.0, max=5.0, step=0.5))
slab = part.box(200, 100, 10, origin=[-100, -50, -10])
brick = part.box(40, 40, 30, origin=[-20, -20, 0])
peg = part.box(20, 20, 50, origin=[-10, -10, 0])
floor = assembly.component(slab, grounded=True)
block = assembly.component(brick, placement=[0, 0, 0])
post = assembly.component(peg, placement=[60, 0, -p.sink])
rail = assembly.joint("slider",
                      assembly.connector(floor, "origin", offset={"position": [0, 0, 0]}),
                      assembly.connector(block, "origin", offset={"position": [0, 0, 0]}))
lift = assembly.joint("slider",
                      assembly.connector(block, "origin", offset={"position": [60, 0, -p.sink]}),
                      assembly.connector(post, "origin", offset={"position": [0, 0, 0]}))
asm = assembly.assembly([floor, block, post], [rail, lift])
diag = assembly.solve(asm)
model = assembly.mjcf(asm, [
    assembly.body(floor, density_kg_m3=1000,
                  collision=[assembly.collision("box", size_mm=[200, 100, 10], offset={"position": [0, 0, -5]})]),
    assembly.body(block, density_kg_m3=1200,
                  collision=[assembly.collision("box", size_mm=[40, 40, 30], offset={"position": [0, 0, 15]})]),
    assembly.body(post, density_kg_m3=1200,
                  collision=[assembly.collision("box", size_mm=[20, 20, 50], offset={"position": [0, 0, 25]})]),
])
result = {"slab": slab, "brick": brick, "peg": peg, "floor": floor, "block": block, "post": post,
          "rail": rail, "lift": lift, "asm": asm, "diag": diag, "model": model}
"""


def _mjcf(dynamics: dict | None) -> dict:
    data = {"assembly_output": "asm"}
    if dynamics is not None:
        data["dynamics"] = dynamics
    return {"name": "model", "type": "mjcf", "assembly_data": data}


def test_initial_contacts_groups_by_pair_and_says_why_when_absent() -> None:
    def contact(a, b, distance, penetrating):
        return {"component_outputs": [a, b], "distance_mm": distance, "penetrating": penetrating}

    block = initial_contacts({"outputs": [_mjcf({
        "initial_contact_count": 3, "initial_contacts_omitted": 0,
        "initial_contacts": [contact("foot", "floor", 0.0, False),
                             contact("post", "floor", -2.0, True), contact("floor", "post", -1.5, True)]})]})
    assert block["available"] is True and block["count"] == 3 and block["omitted"] == 0
    assert "t=0" in block["source"] and "not the exact solids" in block["source"]
    assert block["pairs"] == [
        {"components": ["floor", "post"], "points": 2, "penetrating": True, "deepest_mm": -2.0},
        {"components": ["floor", "foot"], "points": 1, "penetrating": False, "deepest_mm": 0.0},
    ]
    none = initial_contacts({"outputs": [{"name": "plate", "type": "solid"}]})
    assert none["available"] is False and "no assembly.mjcf output" in none["reason"]
    old = initial_contacts({"outputs": [_mjcf(None)]})
    assert old["available"] is False and "rebuild" in old["reason"]


@pytest.fixture
def rest_app(engine, tmp_path, capsys):
    projects = tmp_path / "projects"
    source = tmp_path / "rest.py"
    source.write_text(REST, encoding="utf-8")
    assert main(["script", "--set", str(source), "--project", str(projects / "rest"), "--json"]) == EXIT_OK
    capsys.readouterr()
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        yield projects / "rest", server
    finally:
        server.shutdown()
        server.server_close()


def _agent_pairs(engine, root) -> list[dict]:
    """What the agent reads: ``inspect scope=contacts`` through cadexd."""

    with CadexdClient(engine) as client:
        open_project(client, root)
        reply = client.request("inspect", {"scope": "contacts", "path": "/models/0/pairs", "limit": 50})
    assert reply["ok"], reply
    return reply["value"]


def _page_pairs(page) -> list[list]:
    return page.evaluate(
        "Array.from(document.querySelectorAll('#collision-contacts li[data-pair]'))"
        ".map(li => [li.dataset.pair, li.dataset.penetrating, li.textContent])")


@needs_browser
def test_browser_names_the_parts_touching_at_rest_and_the_agent_reads_the_same(
        engine, rest_app, browser) -> None:
    root, server = rest_app
    page = _open(browser, server.url + "p/rest/")
    assert _model_state(page) == "loaded"
    # The collision view has the proxies to draw, and beside it the t=0 readout.
    assert page.evaluate("document.getElementById('show-collision').disabled") is False
    assert page.attribute("#collision-contacts", "data-state") == "penetrating"
    [(pair, penetrating, text)] = _page_pairs(page)
    assert pair == "floor|post" and penetrating == "true"
    assert "interpenetrating 2.0 mm" in text and "4 point(s)" in text
    assert "1 pair(s), 4 contact point(s)" in page.text("#collision-contacts")

    # The agent reads the same pair, with no page in the loop.
    served = _json(server.url + "p/rest/api/model/accepted")["contacts"]
    agent = _agent_pairs(engine, root)
    assert agent == served["pairs"]
    assert agent[0]["components"] == ["floor", "post"] and agent[0]["points"] == 4
    assert agent[0]["deepest_mm"] == pytest.approx(-2.0, abs=1e-6)

    # Lift the post with the page's own slider (the `cadex params` write,
    # ADR-503): the rebuilt export reports nothing touching, and so does the page.
    slider = "#params input[type=range][data-param=sink]"
    page.evaluate(
        "(() => { const s = document.querySelector(%s); s.value = '0';"
        " s.dispatchEvent(new Event('input')); s.dispatchEvent(new Event('change')); })()"
        % json.dumps(slider))
    page.wait_for("(window.cadexReview.lastWrite() || {}).value === 0", timeout=120)
    assert page.evaluate("window.cadexReview.lastWrite()")["ok"] is True
    page.wait_for("document.getElementById('collision-contacts').dataset.state === 'clear'", timeout=60)
    assert _page_pairs(page) == []
    assert "nothing" in page.text("#collision-contacts")
    assert _agent_pairs(engine, root) == []
