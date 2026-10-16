# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The ground never ends (ADR-742).

A synthetic trace carries the design 50 m -- a 12 s episode at a little
over 4 m/s -- once with the follow camera on, as the playback drives it
(``followTo`` then ``setPoses``, as ``seek`` does), and once with it off, the camera left
where it was. At every frame the design stands over drawn ground, and the
camera stands far enough inside the mat that its edge lies past the fade.
"""

from __future__ import annotations

import pytest

from cadex_cli.browser import HeadlessBrowser
from cadex_cli.review_server import serve_projects
from review_helpers import BROWSER, REVISION_B, _model_state, _open, _projects, _stage_accepted, needs_browser

PLAY = """
(function (follow, heading) {
  var v = window.cadexReview.viewer(), s0 = v.stats(), names = Object.keys(s0.poses)
    .filter(function (n) { return s0.world.indexOf(n) < 0; });
  var base = {}; names.forEach(function (n) { base[n] = s0.poses[n]; });
  var dir = [Math.cos(heading), Math.sin(heading)], frames = 20, metres = 50, worst = null;
  window.cadexReview.setFollow(follow);
  v.followTo(null);
  for (var i = 0; i <= frames; i++) {
    var run = 1000 * metres * i / frames, poses = {};
    names.forEach(function (n) {
      var p = base[n].position_mm;
      poses[n] = {position_mm: [p[0] + run * dir[0], p[1] + run * dir[1], p[2]], rotation_xyzw: base[n].rotation_xyzw};
    });
    if (follow) v.followTo(v.centreAt(poses), i === 0);
    v.setPoses(poses);
    var s = v.stats(), f = s.floor, half = f.size_mm / 2, at = v.centreAt(poses), c = v.camera();
    var cp = Math.cos(c.pitch), eye = [c.target[0] + c.distance * cp * Math.cos(c.yaw),
                                       c.target[1] + c.distance * cp * Math.sin(c.yaw)];
    var inside = function (p) { return half - Math.max(Math.abs(p[0] - f.centre_mm[0]), Math.abs(p[1] - f.centre_mm[1])); };
    var row = {frame: i, design: inside(at), eye: inside(eye), fog: s.stage.fog.far * 1000, far: s.clip.far * 1000,
               corner: Math.hypot(Math.abs(eye[0] - f.centre_mm[0]) + half, Math.abs(eye[1] - f.centre_mm[1]) + half)};
    if (!worst || row.design < worst.design || row.eye - row.fog < worst.eye - worst.fog) worst = row;
  }
  v.followTo(null);
  window.cadexReview.setFollow(false);
  return worst;
})(%s, %s)
"""


@pytest.fixture
def app(tmp_path):
    projects = _projects(tmp_path)
    _stage_accepted(projects / "biped", REVISION_B)
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def small_browser():
    # Software GL paints every frame; a small window keeps 42 of them to seconds.
    with HeadlessBrowser(BROWSER, width=480, height=360) as instance:
        yield instance


@needs_browser
def test_a_50_m_trace_is_over_drawn_ground_every_frame(app, small_browser) -> None:
    page = _open(small_browser, app.url + "p/biped/")
    assert _model_state(page) == "loaded"
    # The ground's placement is the claim, not its shading: software GL spends seconds a frame
    # on occlusion and detail, which have nothing to say about where the mat lies.
    page.evaluate("window.cadexReview.setLook({occlusion: false, detail: false})")
    for follow, heading in ((True, 2.4), (False, -1.9)):
        worst = page.evaluate(PLAY % ("true" if follow else "false", heading))
        worst.update(follow=follow, heading=heading)
        # The design is over the mat, with metres to spare, at its worst frame.
        assert worst["design"] >= 1000, worst
        # The camera never sees the mat end: its edge is past the fade, and inside the far plane.
        assert worst["eye"] >= worst["fog"], worst
        assert worst["corner"] <= worst["far"], worst
