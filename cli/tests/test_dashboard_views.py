# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""More than one of an editor at once (ADR-723, DASHBOARD.md §12).

The 3D viewport, Activations and Network may each be shown in several areas:
a split of one opens a copy of it, and picking one already shown opens
another copy rather than swapping; every other editor still shows once.
Copies carry no id of their own. Every 3D viewport shows the one model on
the one timeline, while its style, camera, gizmo and Follow are its own; and
the gizmo snaps the view with a real press and release while a rollout plays
and the view follows it.
"""

from __future__ import annotations

import json

from cadex_cli.review_server import serve
from test_review_follow import _running_trace
from test_review_server import _open, _review_project, browser, needs_browser  # noqa: F401  (fixture)

LAYOUT = "window.cadexReview.layout()"
DUPLICATE_IDS = """(function(){var seen={}, twice=[];
  document.querySelectorAll('[id]').forEach(function(e){ if (seen[e.id]) twice.push(e.id); seen[e.id]=true; });
  return twice;})()"""


def _areas(page) -> list[dict]:
    return page.evaluate(f"{LAYOUT}.areas()")


def _press(page, selector: str) -> None:
    """A real press and release on an element's centre, as a person's click."""

    x, y = page.evaluate(f"""(function(){{var r=document.querySelector({json.dumps(selector)}).getBoundingClientRect();
        return [r.x + r.width / 2, r.y + r.height / 2];}})()""")
    page.mouse("mouseMoved", x, y)
    page.mouse("mousePressed", x, y, clickCount=1)
    page.mouse("mouseReleased", x, y, clickCount=1)


@needs_browser
def test_multi_editors_open_copies_and_the_rest_still_swap(tmp_path, browser) -> None:
    root = _review_project(tmp_path)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        first = {a["editor"]: a["id"] for a in _areas(page)}
        # A split of the 3D viewport opens a second one beside it.
        assert page.evaluate(f"{LAYOUT}.split({json.dumps(first['view3d'])}, 'row')") is True
        assert [(a["editor"], a["copy"]) for a in _areas(page)][:2] == [("view3d", 0), ("view3d", 1)]
        # Picking it where Status is opens a third; Status, shown once, is simply replaced.
        page.evaluate(f"{LAYOUT}.setEditor({json.dumps(first['status'])}, 'view3d')")
        assert sorted(a["copy"] for a in _areas(page) if a["editor"] == "view3d") == [0, 1, 2]
        assert "status" not in [a["editor"] for a in _areas(page)]
        # A single editor still swaps: the Outliner picked in a viewport's area trades places.
        third = [a for a in _areas(page) if a["editor"] == "view3d" and a["copy"] == 2][0]
        page.evaluate(f"{LAYOUT}.setEditor({json.dumps(third['id'])}, 'outliner')")
        editors = [a["editor"] for a in _areas(page)]
        assert editors.count("outliner") == 1 and editors.count("view3d") == 3
        # Activations and Network copy too, and no copy carries an id of its own.
        out = [a for a in _areas(page) if a["editor"] == "outliner"][0]
        page.evaluate(f"{LAYOUT}.setEditor({json.dumps(out['id'])}, 'activations')")
        page.evaluate(f"{LAYOUT}.split({json.dumps(out['id'])}, 'col')")
        assert [a["copy"] for a in _areas(page) if a["editor"] == "activations"] == [0, 1]
        assert page.evaluate(DUPLICATE_IDS) == []
        assert page.evaluate("document.querySelectorAll('#screen canvas[data-ref=viewer]').length") == 2
        # The copies are kept: a reload lays them out again.
        tree = page.evaluate(f"{LAYOUT}.tree()")
        page = _open(browser, server.url)
        assert page.evaluate(f"{LAYOUT}.tree()") == tree
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
def test_two_viewports_share_the_timeline_and_keep_their_own_view(tmp_path, browser) -> None:
    root = _review_project(tmp_path)
    (root / "runs" / "second" / "rollout" / "assembly-simulation-trace.json").write_text(_running_trace())
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        page.evaluate("window.cadexReview.setFollow(false)")
        view3d = [a for a in _areas(page) if a["editor"] == "view3d"][0]
        page.evaluate(f"{LAYOUT}.split({json.dumps(view3d['id'])}, 'col')")
        page.evaluate("window.cadexReview.setSource('run:second')", await_promise=True)
        page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
        page.wait_for("(function(){var p=window.cadexReview.playback();return p&&p.times_s.length>2})()")
        copy = ".area[data-editor=view3d][data-copy='1']"
        # The copy's own style: a wireframe beside the shaded first.
        page.click(f"{copy} [data-ref=view3d-style] [data-style=wireframe]")
        assert [v["style"] for v in page.evaluate("window.cadexReview.views()")] == ["shaded", "wireframe"]
        assert page.evaluate("window.cadexReview.renderStyle()") == "shaded"
        # One timeline: a seek poses both, and the copy's scrubber shows the same time.
        body = "[0, 1].map(function (i) { return window.cadexReview.view(i).stats().poses.body.position_mm[0]; })"
        page.evaluate("window.cadexReview.seek(0)")
        assert page.evaluate(body) == [0, 0]
        page.evaluate("window.cadexReview.seek(1)")
        assert page.evaluate(body) == [1000, 1000]
        page.wait_for(f"document.querySelector({json.dumps(copy + ' [data-ref=play-clock]')}).textContent === '1.00 s'")
        # The copy's own camera: the gizmo turns it to the top; the first stays where it was.
        first_camera = page.evaluate("window.cadexReview.views()[0].camera")
        _press(page, f"{copy} .gizmo-end[data-end='+z']")
        page.wait_for("window.cadexReview.views()[1].camera.pitch > 1.5")
        assert page.evaluate("window.cadexReview.views()[0].camera") == first_camera
        # Follow is each view's: on in the copy, its target travels and the first's stays.
        page.click(f"{copy} [data-ref=play-follow]")
        assert [v["follow"] for v in page.evaluate("window.cadexReview.views()")] == [False, True]
        page.evaluate("window.cadexReview.seek(0)")
        a = page.evaluate("[window.cadexReview.views()[0].camera.target[0], window.cadexReview.views()[1].camera.target[0]]")
        page.evaluate("window.cadexReview.seek(2)")
        b = page.evaluate("[window.cadexReview.views()[0].camera.target[0], window.cadexReview.views()[1].camera.target[0]]")
        assert b[0] == a[0] and b[1] - a[1] > 1000, (a, b)
        # The copy's Play works the one timeline.
        page.click(f"{copy} [data-ref=play-toggle]")
        page.wait_for("window.cadexReview.playback().playing")
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
def test_the_gizmo_snaps_while_a_rollout_plays_and_the_view_follows(tmp_path, browser) -> None:
    root = _review_project(tmp_path)
    (root / "runs" / "second" / "rollout" / "assembly-simulation-trace.json").write_text(_running_trace(seconds=20.0))
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        page.evaluate("window.cadexReview.setSource('run:second')", await_promise=True)
        page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
        page.wait_for("(function(){var p=window.cadexReview.playback();return p&&p.times_s.length>2})()")
        assert page.evaluate("window.cadexReview.setFollow(true)") is True
        if not page.evaluate("window.cadexReview.playback().playing"):
            page.click("#play-toggle")
        page.wait_for("window.cadexReview.playback().playing")
        # Redrawn every frame, the ends stay put under a press, and the snap lands.
        _press(page, "#view3d-gizmo .gizmo-end[data-end='+z']")
        page.wait_for("window.cadexReview.viewer().camera().pitch > 1.5", timeout=5)
        page.wait_for("document.getElementById('view3d-gizmo').dataset.view === '+z'", timeout=5)
        assert page.evaluate("window.cadexReview.playback().playing")
        # And the follow carries on from the new direction.
        x0 = page.evaluate("window.cadexReview.viewer().camera().target[0]")
        page.wait_for(f"window.cadexReview.viewer().camera().target[0] - {x0} > 100", timeout=10)
        assert page.evaluate("window.cadexReview.viewer().camera().pitch") > 1.5
    finally:
        server.shutdown()
        server.server_close()
