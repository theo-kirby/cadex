# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Layout presets and a discoverable drag (ADR-573, orun4 D3).

View → Layout offers eight presets; one click lays the screen out afresh
with the editors in their order (3D viewport, Status, 2D viewport) and any
area past the third empty, with only its editor picker. Each is applied
through the menu and its areas measured against the shape it names; then an
area is dragged by its grip onto another, the drop preview naming where it
will land, and Reset returns the default.
"""

from __future__ import annotations

import json

from cadex_cli.review_server import serve
from test_review_server import _open, _review_project, browser, needs_browser  # noqa: F401  (fixture)

#: Each preset's areas in reading order: editor, then x, y, width, height as
#: fractions of the screen.
H, T = 1 / 2, 1 / 3
EXPECTED = {
    "single": [("view3d", 0, 0, 1, 1)],
    "side": [("view3d", 0, 0, H, 1), ("status", H, 0, H, 1)],
    "stacked": [("view3d", 0, 0, 1, H), ("status", 0, H, 1, H)],
    "two_over_one": [("view3d", 0, 0, H, H), ("status", H, 0, H, H), ("view2d", 0, H, 1, H)],
    "one_over_two": [("view3d", 0, 0, 1, H), ("status", 0, H, H, H), ("view2d", H, H, H, H)],
    "columns": [("view3d", 0, 0, T, 1), ("status", T, 0, T, 1), ("view2d", 2 * T, 0, T, 1)],
    "rows": [("view3d", 0, 0, 1, T), ("status", 0, T, 1, T), ("view2d", 0, 2 * T, 1, T)],
    "quad": [("view3d", 0, 0, H, H), ("status", H, 0, H, H), ("view2d", 0, H, H, H), ("empty", H, H, H, H)],
}

AREAS = """(function () {
  var s = document.getElementById('screen').getBoundingClientRect();
  return Array.from(document.querySelectorAll('#screen .area')).map(function (a) {
    var r = a.getBoundingClientRect();
    return {editor: a.dataset.editor, id: a.dataset.area, x: (r.x - s.x) / s.width, y: (r.y - s.y) / s.height,
            w: r.width / s.width, h: r.height / s.height, px: [r.x, r.y, r.width, r.height],
            picker: !!a.querySelector('.area-header select.area-type')};
  });
})()"""


def _matches(areas: list[dict], expected: list[tuple]) -> bool:
    # Gutters and the screen's padding take a few pixels: 2.5 % of a side.
    tol = 0.025
    if [a["editor"] for a in areas] != [e[0] for e in expected]:
        return False
    return all(abs(a[k] - e[i + 1]) <= tol for a, e in zip(areas, expected) for i, k in enumerate("xywh"))


@needs_browser
def test_every_preset_lays_the_screen_out_in_one_click_and_areas_drag_with_a_preview(tmp_path, browser) -> None:
    server, _thread = serve(_review_project(tmp_path), "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        page.evaluate("window.cadexReview.layout().reset()")
        offered = page.evaluate("Array.from(document.querySelectorAll('#layout-presets button')).map(function (b) {"
                                " return [b.dataset.preset, b.title]; })")
        assert [name for name, _ in offered] == list(EXPECTED), offered
        assert page.evaluate("window.cadexReview.layout().presets") == list(EXPECTED)
        measured = {}
        for name, expected in EXPECTED.items():
            page.click("#view-panel > summary")
            page.click(f"#layout-presets button[data-preset={name}]")
            areas = page.evaluate(AREAS)
            assert _matches(areas, expected), (name, areas)
            assert all(a["picker"] for a in areas), name
            # The menu closes behind the click, and the layout is kept.
            assert page.evaluate("document.getElementById('view-panel').open") is False
            kept = json.loads(page.evaluate("localStorage.getItem('cadex.layout.v4')"))
            assert kept == page.evaluate("window.cadexReview.layout().tree()")
            measured[name] = len(areas)

        # Quad's fourth area is empty, with a picker; picking the 2D viewport
        # there moves it in and leaves its old area empty.
        page.click("#view-panel > summary")
        page.click("#layout-presets button[data-preset=quad]")
        empty = page.evaluate("(function () { var a = document.querySelector('.area[data-editor=empty]');"
                              " return {text: a.querySelector('.area-empty').textContent,"
                              " options: Array.from(a.querySelectorAll('select.area-type option')).map(function (o) { return o.value; })}; })()")
        assert "pick an editor" in empty["text"] and empty["options"] == ["view3d", "status", "view2d", "empty"]
        page.evaluate("(function () { var s = document.querySelector('.area[data-editor=empty] select.area-type');"
                      " s.value = 'view2d'; s.dispatchEvent(new Event('change')); })()")
        assert [a["editor"] for a in page.evaluate(AREAS)] == ["view3d", "status", "empty", "view2d"]
        # Kept across a reload, empty area and all.
        page.send("Page.reload")
        page.wait_for("document.readyState === 'complete' && !!window.cadexReview")
        page.evaluate("window.cadexReview.ready", await_promise=True)
        assert [a["editor"] for a in page.evaluate(AREAS)] == ["view3d", "status", "empty", "view2d"]

        # Side by side, then drag the 3D viewport by its grip onto Status's
        # right edge: the preview covers that half and says so, and it lands there.
        page.click("#view-panel > summary")
        page.click("#layout-presets button[data-preset=side]")
        grip = page.evaluate("(function () { var g = document.querySelector('.area[data-editor=view3d] .area-grip'),"
                             " b = g.getBoundingClientRect(); return [b.x + b.width / 2, b.y + b.height / 2, b.width, b.height,"
                             " getComputedStyle(g).opacity, getComputedStyle(g).cursor]; })()")
        assert grip[2] >= 8 and grip[3] >= 12 and float(grip[4]) >= 0.8 and grip[5] == "grab", grip
        status = [a for a in page.evaluate(AREAS) if a["editor"] == "status"][0]
        sx, sy, sw, sh = status["px"]
        to = (sx + sw * 0.92, sy + sh / 2)
        page.mouse("mousePressed", grip[0], grip[1], clickCount=1)
        for step in range(1, 9):
            page.mouse("mouseMoved", grip[0] + (to[0] - grip[0]) * step / 8, grip[1] + (to[1] - grip[1]) * step / 8)
        # The preview slides into place over 60 ms.
        page.wait_for("(function () { var h = document.querySelector('.drop-hint');"
                      " return !!h && !h.hidden && Math.abs(h.getBoundingClientRect().x - %f) <= 1; })()" % (sx + sw / 2),
                      timeout=3)
        hint = page.evaluate("(function () { var h = document.querySelector('.drop-hint'); if (!h || h.hidden) return null;"
                             " var r = h.getBoundingClientRect(); return {zone: h.dataset.zone, label: h.textContent,"
                             " x: r.x, w: r.width, h: r.height}; })()")
        assert hint and hint["zone"] == "right" and hint["label"] == "Dock right", hint
        assert abs(hint["x"] - (sx + sw / 2)) <= 1 and abs(hint["w"] - sw / 2) <= 1 and abs(hint["h"] - sh) <= 1
        page.mouse("mouseReleased", to[0], to[1], clickCount=1)
        page.wait_for("document.querySelector('#screen .area').dataset.editor === 'status'", timeout=5)
        assert page.evaluate("document.querySelector('.drop-hint')") is None
        assert [a["editor"] for a in page.evaluate(AREAS)] == ["status", "view3d"]

        # Reset puts the default back: the 3D viewport, Status beside it.
        page.click("#layout-reset")
        assert page.evaluate("window.cadexReview.layout().tree()") == {
            "dir": "row", "sizes": [0.75, 0.25], "children": [{"editor": "view3d"}, {"editor": "status"}]}
        print(json.dumps({"presets": measured}))
    finally:
        server.shutdown()
        server.server_close()
