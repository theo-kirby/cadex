# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fit frames the design, not the task floor it stands on (ADR-525).

A robot project draws its task's floor as a component: in orun2's W1 walk
a 1.2 m slab under a 178 mm quadruped, which Fit framed whole and left the
robot a speck (docs/probes/orun2/REPORT.md, defect 1). The engine already
names that slab world geometry in the fit block; the manifest carries the
flag and the viewer leaves such parts out of the bounds Fit frames and out
of the model-pixel coverage check, and (ADR-600) does not draw them at all:
the mat lies at the floor's top instead. Proved against a real engine.
"""

from __future__ import annotations

import pytest

from cadex_cli.__main__ import main
from cadex_cli.report import EXIT_OK
from cadex_cli.review_server import serve_projects, world_components
from test_review_server import _json, _model_state, _open, browser, needs_browser  # noqa: F401

#: A 60 × 40 × 30 mm body standing on a 1200 mm floor marked world geometry.
ON_A_FLOOR = """
floor = part.box(1200, 1200, 2, origin=(-600, -600, -2))
body  = part.box(60, 40, 30, origin=(-30, -20, 0))
c_floor = assembly.component(floor, grounded=True, world=True, label="floor")
c_body  = assembly.component(body, grounded=True, label="body")
asm  = assembly.assembly([c_floor, c_body])
diag = assembly.solve(asm)
result = {"floor": floor, "body": body, "c_floor": c_floor, "c_body": c_body, "asm": asm, "diag": diag}
"""


def test_world_components_are_the_fit_block_s_world_geometry_rows() -> None:
    result = {"outputs": [
        {"name": "c_floor", "type": "component_link"},
        {"name": "asm", "world_geometry": [
            {"component": "c_floor", "status": "world geometry", "reason": "declared world=True"},
            {"component": "c_other", "status": "something else"}]},
        "not a mapping",
    ]}
    assert world_components(result) == {"c_floor"}
    assert world_components({"outputs": []}) == set()


@pytest.fixture
def floor_app(engine, tmp_path, capsys):
    projects = tmp_path / "projects"
    source = tmp_path / "on_a_floor.py"
    source.write_text(ON_A_FLOOR, encoding="utf-8")
    assert main(["script", "--set", str(source), "--project", str(projects / "orun2-fit"), "--json"]) == EXIT_OK
    capsys.readouterr()
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


def test_the_manifest_marks_the_floor_and_only_the_floor(engine, floor_app) -> None:
    model = _json(floor_app.url + "p/orun2-fit/api/model/accepted")
    assert {c["name"]: c["world"] for c in model["components"] if c.get("mesh")} == {
        "c_floor": True, "c_body": False}


@needs_browser
def test_browser_fit_frames_the_body_and_coverage_ignores_the_floor(engine, floor_app, browser) -> None:
    page = _open(browser, floor_app.url + "p/orun2-fit/")
    assert _model_state(page) == "loaded"
    page.click("#model-fit")
    stats = page.evaluate("window.cadexReview.viewer().stats()")
    assert stats["world"] == ["c_floor"] and stats["components"] == 2
    # Fit's bounds are the body's, not the floor's 1200 mm.
    assert stats["bounds"]["min"] == pytest.approx([-30, -20, 0], abs=1e-3)
    assert stats["bounds"]["max"] == pytest.approx([30, 20, 30], abs=1e-3)
    px = page.evaluate("window.cadexReview.viewer().modelPixels()")
    fraction = px["count"] / float(px["width"] * px["height"])
    x0, y0, x1, y1 = px["box"]
    # The body (and its shadow) fills a real share of the canvas, and its box is
    # well inside it: a floor slab counted as the model would run to the edges.
    assert 0.05 < fraction < 0.6, px
    assert x0 > 0 and y0 > 0 and x1 < px["width"] - 1 and y1 < px["height"] - 1, px
    assert (x1 - x0) > 0.25 * px["width"] or (y1 - y0) > 0.25 * px["height"], px
    # The floor is installed but not drawn (ADR-600): the mat lies at its top, z = 0, where the
    # body stands.
    page.evaluate("window.cadexReview.viewer().draw()")
    stats = page.evaluate("window.cadexReview.viewer().stats()")
    assert stats["components"] == 2 and stats["hidden_world"] == ["c_floor"]
    assert stats["floor"]["source"] == "world" and stats["floor"]["z_mm"] == pytest.approx(0, abs=1e-6)
