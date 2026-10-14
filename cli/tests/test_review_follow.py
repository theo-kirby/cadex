# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The follow camera (DASHBOARD.md §5): while a rollout plays, the view
travels with the design, so a running machine can be watched close up.

A walked run whose rollout carries its two bodies 2 m along x in 2 s: with Follow off the camera stays where the person left it; with it on,
the target moves with the body (smoothed), yaw, pitch and distance stay the
person's, the body stays drawn, and the choice is remembered.
"""

from __future__ import annotations

import json

from cadex_cli.review_server import serve
from test_review_server import (TRACE_SCHEMA, _open, _review_project,
                                browser, needs_browser)  # noqa: F401  (fixture)


def _running_trace(seconds: float = 2.0, step: float = 0.04, speed_mm_s: float = 1000.0) -> str:
    frames = []
    for index in range(int(round(seconds / step)) + 1):
        t = round(index * step, 6)
        frames.append({"frame_index": index, "frame_kind": "solver_output", "nominal_time_s": t,
                       "component_placements": {
                           "body": {"position_mm": [speed_mm_s * t, 0.0, 0.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]},
                           "shin": {"position_mm": [speed_mm_s * t, 0.0, -40.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}}})
    return json.dumps({"schema": TRACE_SCHEMA, "component_outputs": ["body", "shin"], "frames": frames})


TARGET_X = "window.cadexReview.viewer().camera().target[0]"


@needs_browser
def test_follow_moves_the_view_with_the_design_and_keeps_the_persons_framing(tmp_path, browser) -> None:
    root = _review_project(tmp_path)
    (root / "runs" / "second" / "rollout" / "assembly-simulation-trace.json").write_text(_running_trace())
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        page.evaluate("window.cadexReview.setSource('run:second')", await_promise=True)
        page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
        page.wait_for("(function(){var p=window.cadexReview.playback();return p&&p.times_s.length>2})()")
        assert not page.evaluate("document.getElementById('playback').hidden")
        assert page.evaluate("document.getElementById('play-follow').getAttribute('aria-pressed')") == "false"

        # Off: the body runs out of a still view.
        assert page.evaluate("window.cadexReview.setFollow(false)") is False
        page.evaluate("window.cadexReview.seek(0)")
        still = page.evaluate(TARGET_X)
        page.evaluate("window.cadexReview.seek(2)")
        assert page.evaluate(TARGET_X) == still

        # On: the view snaps onto the body and travels with it.
        page.evaluate("window.cadexReview.seek(0)")
        assert page.evaluate("window.cadexReview.setFollow(true)") is True
        assert page.evaluate("document.getElementById('play-follow').getAttribute('aria-pressed')") == "true"
        start = page.evaluate("window.cadexReview.viewer().camera()")
        assert abs(start["target"][0] - 7.0) < 5.0, start   # the cubes' centres
        page.evaluate("window.cadexReview.seek(1)")
        middle = page.evaluate("window.cadexReview.viewer().camera()")
        page.evaluate("window.cadexReview.seek(2)")
        end = page.evaluate("window.cadexReview.viewer().camera()")
        assert middle["target"][0] - start["target"][0] > 700.0
        assert end["target"][0] - middle["target"][0] > 600.0
        # Mid-run the smoothed track is the bodies themselves: 1 m along, their centres 7 mm on.
        assert abs(middle["target"][0] - 1007.0) < 5.0, middle
        for key in ("yaw", "pitch", "distance"):
            assert end[key] == start[key]
        # At either end the window narrows, so the view is on the body, not trailing it.
        assert abs(end["target"][0] - 2007.0) < 5.0, end
        assert page.evaluate("window.cadexReview.viewer().nonBackgroundPixels()") > 300

        # A pan the person makes is kept: the view follows from where they put it.
        page.evaluate("window.cadexReview.seek(1)")
        panned = page.evaluate("""(function(){var v=window.cadexReview.viewer(), c=v.camera();
            c.target[1] += 50; v.setCamera(c); return v.camera().target[1];})()""")
        page.evaluate("window.cadexReview.seek(1.5)")
        assert page.evaluate("window.cadexReview.viewer().camera().target[1]") == panned

        # Off again: the view stays where it is; the choice outlives a reload.
        assert page.evaluate("window.cadexReview.setFollow(false)") is False
        page.evaluate("window.cadexReview.setFollow(true)")
        assert page.evaluate("localStorage.getItem('cadex.follow')") == "on"
    finally:
        server.shutdown()
        server.server_close()
