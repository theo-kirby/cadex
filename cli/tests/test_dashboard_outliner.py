# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Outliner (ADR-676; docs/DASHBOARD.md §25), after Blender's.

Every part the 3D viewport draws is listed in groups -- by type by default,
hardware folded -- with an eye that hides it and a row that selects it; the
selection is outlined in the viewport, and a click on a solid selects its
row. Hidden and selected parts are the viewer's, by name, and outlive a
reload of the model; the grouping is this browser's. Synthetic solids are
installed straight into the viewer, as the viewport-look tests do, so each
behaviour is checked on geometry whose answer is known.
"""

from __future__ import annotations

import json

from test_dashboard_viewport_look import _install, _page, _pixels
from test_review_server import browser, needs_browser, served  # noqa: F401  (fixtures)

#: A printed body, a purchased motor, three screws, a board and the task's floor.
PARTS = [
    ("body", "T.box(-40,-20,0,40,20,30)", {"finish": "printed", "role": "shell", "color": "#d9d4cb"}),
    ("motor", "T.box(50,-10,0,70,10,20)", {"finish": "purchased", "role": "mechanism", "color": "#2c2f35"}),
    ("screw_0", "T.box(-30,-5,30,-26,-1,36)", {"finish": "hardware", "role": "mechanism", "catalog": {"family": "bolt", "part_number": "m3x8"}}),
    ("screw_1", "T.box(-2,-5,30,2,-1,36)", {"finish": "hardware", "role": "mechanism", "catalog": {"family": "bolt", "part_number": "m3x8"}}),
    ("screw_2", "T.box(26,-5,30,30,-1,36)", {"finish": "hardware", "role": "mechanism", "catalog": {"family": "bolt", "part_number": "m3x8"}}),
    ("imu", "T.box(-60,-10,0,-45,10,2)", {"finish": "board", "role": "mechanism", "color": "#1f6b3c"}),
    ("floor", "T.box(-500,-500,-10,500,500,0)", {"world": True}),
]


def _load(page):
    entries = ", ".join(f"T.entry({json.dumps(name)}, {tris}, {json.dumps(extra)})" for name, tris, extra in PARTS)
    stats = _install(page, entries)
    manifest = {"available": True, "components": [dict(extra, name=name, mesh="mesh/" + name) for name, _t, extra in PARTS]}
    page.evaluate(f"window.cadexReview.outliner().setModel({json.dumps(manifest)})")
    return stats


def _state(page):
    return page.evaluate("""(function () {
      var o = window.cadexReview.outliner().state(), v = window.cadexReview.viewer(), s = v.stats();
      return {o: o, hidden: s.hidden, selected: s.selected, rows: Array.from(document.querySelectorAll('#outliner-tree .outliner-part'))
              .map(function (r) { return [r.dataset.part, r.getAttribute('aria-selected'), r.dataset.hidden]; }),
              summary: document.getElementById('outliner-summary').textContent}; })()""")


def _show_outliner(page):
    page.evaluate("window.cadexReview.layout().reset()")


@needs_browser
def test_the_outliner_lists_groups_and_hides_shows_and_isolates(served, browser) -> None:
    _root, server = served
    page = _page(browser, server)
    _show_outliner(page)
    _load(page)
    st = _state(page)
    # By type, in that order; the task's floor is world geometry and not listed; hardware starts folded.
    assert [(g["key"], g["count"], g["folded"]) for g in st["o"]["groups"]] == [
        ("type:printed", 1, False), ("type:purchased", 1, False), ("type:hardware", 3, True), ("type:board", 1, False)]
    assert [r[0] for r in st["rows"]] == ["body", "motor", "imu"]
    assert st["summary"] == "6 parts"
    # A part's eye hides it in the viewer; the row says so and the summary counts it.
    before = sum(1 for p in _pixels(page) if p[0] > 150)
    page.click(".outliner-part[data-part=body] .outliner-eye")
    st = _state(page)
    assert st["hidden"] == ["body"] and st["o"]["hidden"] == ["body"]
    assert dict((r[0], r[2]) for r in st["rows"])["body"] == "true" and "1 hidden" in st["summary"]
    assert sum(1 for p in _pixels(page) if p[0] > 150) < before
    page.click(".outliner-part[data-part=body] .outliner-eye")
    assert _state(page)["hidden"] == []
    # A group's eye hides the whole group, folded or not.
    page.click(".outliner-group[data-group='type:hardware'] .outliner-head .outliner-eye")
    assert sorted(_state(page)["hidden"]) == ["screw_0", "screw_1", "screw_2"]
    # Show all brings everything back; Ctrl on an eye isolates that part.
    page.click("#outliner-show-all")
    assert _state(page)["hidden"] == []
    page.evaluate("document.querySelector('.outliner-part[data-part=motor] .outliner-eye')"
                  ".dispatchEvent(new MouseEvent('click', {bubbles: true, ctrlKey: true}))")
    assert sorted(_state(page)["hidden"]) == ["body", "imu", "screw_0", "screw_1", "screw_2"]
    # Fit frames what is shown: the motor alone is a closer shot than the whole design.
    page.evaluate("window.cadexReview.viewer().fit()")
    alone = page.evaluate("window.cadexReview.viewer().camera().distance")
    page.click("#outliner-show-all")
    page.evaluate("window.cadexReview.viewer().fit()")
    assert alone < 0.6 * page.evaluate("window.cadexReview.viewer().camera().distance")
    # The filter narrows the rows; the grouping is kept by this browser.
    page.evaluate("var f=document.getElementById('outliner-filter'); f.value='scr'; f.dispatchEvent(new Event('input'))")
    assert [g["key"] for g in _state(page)["o"]["groups"]] == ["type:hardware"]
    page.evaluate("var f=document.getElementById('outliner-filter'); f.value=''; f.dispatchEvent(new Event('input'))")
    page.evaluate("var g=document.getElementById('outliner-group'); g.value='role'; g.dispatchEvent(new Event('change'))")
    assert [g["key"] for g in _state(page)["o"]["groups"]] == ["role:shell", "role:mechanism"]
    assert page.evaluate("localStorage.getItem('cadex.outliner.group')") == "role"
    page.evaluate("localStorage.clear()")


@needs_browser
def test_selection_is_shared_with_the_viewport_and_outlined(served, browser) -> None:
    _root, server = served
    page = _page(browser, server)
    _show_outliner(page)
    _load(page)
    page.evaluate("window.cadexReview.viewer().fit()")

    def blue():
        return sum(1 for r, g, b in _pixels(page) if b > 200 and r < 140 and 120 < g < 200)

    assert blue() == 0
    # A row click selects the part, and the viewport outlines it.
    page.click(".outliner-part[data-part=motor] .outliner-name")
    st = _state(page)
    assert st["selected"] == ["motor"] and dict((r[0], r[1]) for r in st["rows"])["motor"] == "true"
    assert st["summary"].startswith("motor · ")
    ringed = blue()
    assert ringed > 50
    # Ctrl adds; a plain click replaces.
    page.evaluate("document.querySelector('.outliner-part[data-part=body] .outliner-name')"
                  ".dispatchEvent(new MouseEvent('click', {bubbles: true, ctrlKey: true}))")
    assert _state(page)["selected"] == ["motor", "body"]
    page.click(".outliner-part[data-part=imu] .outliner-name")
    assert _state(page)["selected"] == ["imu"]
    # A click on a solid in the viewport selects its row; on empty floor, clears.
    x, y = page.evaluate("window.cadexReview.viewer().screenPoint('body')")
    page.mouse("mousePressed", x, y, button="left", clickCount=1)
    page.mouse("mouseReleased", x, y, button="left", clickCount=1)
    assert _state(page)["selected"] == ["body"]
    canvas = page.rect("#viewer")
    page.mouse("mousePressed", canvas["x"] + 8, canvas["y"] + 8, button="left", clickCount=1)
    page.mouse("mouseReleased", canvas["x"] + 8, canvas["y"] + 8, button="left", clickCount=1)
    assert _state(page)["selected"] == []
    assert blue() == 0
    # Selecting a folded group's part unfolds the group to show its row.
    page.evaluate("window.cadexReview.outliner().select(['screw_1'])")
    assert any(r[0] == "screw_1" and r[1] == "true" for r in _state(page)["rows"])
    # Keys over the Outliner, as in Blender: H hides the selection, Alt+H shows all,
    # Shift+H hides the rest, Esc clears.
    tree = page.rect("#outliner-tree")
    page.mouse("mouseMoved", tree["x"] + 20, tree["y"] + 20, buttons=0)

    def key(name, code, modifiers=0):
        for kind in ("rawKeyDown", "keyUp"):
            page.send("Input.dispatchKeyEvent", {"type": kind, "key": name, "code": code, "modifiers": modifiers,
                                                 "windowsVirtualKeyCode": ord(name.upper()) if len(name) == 1 else 27})

    key("h", "KeyH")
    assert _state(page)["hidden"] == ["screw_1"] and _state(page)["selected"] == []
    key("h", "KeyH", 1)  # Alt
    assert _state(page)["hidden"] == []
    page.evaluate("window.cadexReview.outliner().select(['motor'])")
    key("H", "KeyH", 8)  # Shift
    assert sorted(_state(page)["hidden"]) == ["body", "imu", "screw_0", "screw_1", "screw_2"]
    key("Escape", "Escape")
    assert _state(page)["selected"] == []
    # What is hidden outlives the agent's next write: a reload of the model keeps it.
    _load(page)
    assert sorted(_state(page)["hidden"]) == ["body", "imu", "screw_0", "screw_1", "screw_2"]
    page.evaluate("localStorage.clear()")
