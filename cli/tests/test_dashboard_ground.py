# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The ground never ends (ADR-742), and a course is one ground (ADR-743).

A synthetic trace carries the design 50 m -- a 12 s episode at a little
over 4 m/s -- once with the follow camera on, as the playback drives it
(``followTo`` then ``setPoses``, as ``seek`` does), and once with it off, the camera left
where it was. At every frame the design stands over drawn ground, and the
camera stands far enough inside the mat that its edge lies past the fade.

A served box course -- a step, a ramp turned to its grade as the engine
builds one, a turned rock, and a mogul built as the engine builds one, a
buried sphere (ADR-744) -- is drawn as one mesh whose height, read off its
own triangles, is the highest box or dome top over each point, and which ends
at the plane the mat lies on.

And what is drawn is what the paws touch (ADR-745): on 10 held-out courses
the engine draws -- steps, slopes, moguls, platforms and rock patches, with
their run-outs -- the drawn height and MuJoCo's own ray onto the placed
course agree within 5 mm at 1,000 points, on the course, on its features and
past its extent.
"""

from __future__ import annotations

import importlib.util
import json
import math
import random

import pytest

from conftest import SOURCE_MODULE_DIR

from cadex_cli.browser import HeadlessBrowser
from cadex_cli.review_server import serve_projects, terrain_block
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


def _ramp(xa: float, xb: float, za: float, zb: float, y: float) -> dict:
    # CadexDynamics.terrain_box_geoms's ramp: a 10 mm half-thick box turned about y to its grade.
    grade, thick = math.atan2(zb - za, xb - xa), 10.0
    return {"shape": "ramp", "centre_mm": [(xa + xb) / 2 + thick * math.sin(grade), 0.0, (za + zb) / 2 - thick * math.cos(grade)],
            "rotation_xyzw": [0.0, -math.sin(grade / 2), 0.0, math.cos(grade / 2)], "half_mm": [math.hypot(xb - xa, zb - za) / 2, y, thick]}


def _block(xa: float, xb: float, ya: float, yb: float, top: float) -> dict:
    return {"shape": "block", "centre_mm": [(xa + xb) / 2, (ya + yb) / 2, (top - 50) / 2],
            "rotation_xyzw": [0.0, 0.0, 0.0, 1.0], "half_mm": [(xb - xa) / 2, (yb - ya) / 2, (top + 50) / 2]}


def _rock() -> dict:
    turn = [0.12, 0.2, 0.3]  # an axis-angle, small enough that one face is on top
    angle = math.hypot(*turn)
    xyz = [v / angle * math.sin(angle / 2) for v in turn]
    return {"shape": "block", "centre_mm": [2600.0, -300.0, -20.0], "rotation_xyzw": [*xyz, math.cos(angle / 2)],
            "half_mm": [180.0, 140.0, 80.0]}


def _dome(x: float, y: float, foot: float, rise: float) -> dict:
    # CadexDynamics.terrain_dome_geoms's mogul: a sphere whose cap stands `rise` over the plane at
    # `foot` from its centre.
    radius = (foot * foot + rise * rise) / (2 * rise)
    return {"centre_mm": [x, y, rise - radius], "radius_mm": radius}


# A step up 100 mm, a ramp down from it at -15 degrees onto the plane, a rock past it, and a
# 60 mm mogul on a 250 mm foot beside the ramp.
STEP_TOP, RAMP = 100.0, (1200.0, 1200.0 + 100.0 / math.tan(math.radians(15)))
MOGUL = (2000.0, 450.0, 250.0, 60.0)
COURSE = terrain_block({
    "kind": "boxes", "x_range_mm": [-500.0, 3000.0], "y_range_mm": [-800.0, 800.0],
    "lowest_mm": 0.0, "highest_mm": STEP_TOP, "plane_z_mm": 0.0,
    "boxes": [_block(400.0, RAMP[0], -800.0, 800.0, STEP_TOP), _ramp(RAMP[0], RAMP[1], STEP_TOP, 0.0, 800.0), _rock()],
    "domes": [_dome(*MOGUL)]})


def _top(box: dict, x: float, y: float) -> float:
    """The highest point of a box on the vertical at (x, y), or -inf: slab clipping, in Python."""
    qx, qy, qz, qw = box["rotation_xyzw"]
    axes = [[1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy + qz * qw), 2 * (qx * qz - qy * qw)],
            [2 * (qx * qy - qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz + qx * qw)],
            [2 * (qx * qz + qy * qw), 2 * (qy * qz - qx * qw), 1 - 2 * (qx * qx + qy * qy)]]
    d = [x - box["centre_mm"][0], y - box["centre_mm"][1], -box["centre_mm"][2]]
    lo, hi = -math.inf, math.inf
    for axis, half in zip(axes, box["half_mm"]):
        offset, slope = sum(a * b for a, b in zip(axis, d)), axis[2]
        if abs(slope) < 1e-12:
            if abs(offset) > half:
                return -math.inf
            continue
        a, b = (-half - offset) / slope, (half - offset) / slope
        lo, hi = max(lo, min(a, b)), min(hi, max(a, b))
    return hi if lo <= hi else -math.inf


def _cap(dome: dict, x: float, y: float) -> float:
    reach = dome["radius_mm"] ** 2 - (x - dome["centre_mm"][0]) ** 2 - (y - dome["centre_mm"][1]) ** 2
    return dome["centre_mm"][2] + math.sqrt(reach) if reach >= 0 else -math.inf


def _ground(x: float, y: float) -> float:
    return max([COURSE["plane_z_mm"], *(_top(box, x, y) for box in COURSE["boxes"]),
                *(_cap(dome, x, y) for dome in COURSE["domes"])])


@needs_browser
def test_a_box_course_is_one_ground_at_its_boxes_height(app, small_browser) -> None:
    page = _open(small_browser, app.url + "p/biped/")
    assert _model_state(page) == "loaded"
    page.evaluate("window.cadexReview.setLook({occlusion: false, detail: false})")
    assert page.evaluate("window.cadexReview.viewer().setTerrain(%s)" % json.dumps(COURSE)) == 4
    stats = page.evaluate("window.cadexReview.viewer().stats()")
    surface = stats["terrain"]["surface"]
    # One mesh: no box objects, no slab, no edge lines; the mat lies at the plane.
    assert surface["meshes"] == 1 and stats["floor"]["z_mm"] == 0.0, stats["terrain"]
    rng = random.Random(743)
    (x0, x1), (y0, y1) = surface["x_range_mm"], surface["y_range_mm"]
    points = [(rng.uniform(x0, x1), rng.uniform(y0, y1)) for _ in range(1000)]
    drawn = page.evaluate("(function (p) { var v = window.cadexReview.viewer(); "
                          "return p.map(function (q) { return v.groundAt(q[0], q[1]); }); })(%s)" % json.dumps(points))
    # The step's and the ramp's edges run along y; a point within a wall's half-width of one is on
    # the wall, and the rock's turned edges cut cells at a slant, so their neighbourhoods are left out.
    edges = [400.0, RAMP[0], RAMP[1]]
    near_rock = lambda x, y: math.hypot(x - 2600.0, y + 300.0) < 300.0
    worst = max(abs(h - _ground(x, y)) for (x, y), h in zip(points, drawn)
                if min(abs(x - e) for e in edges) > 1.0 and not near_rock(x, y))
    assert worst <= 5.0, worst
    # The rock's top, away from its edges, is drawn where it stands.
    assert abs(page.evaluate("window.cadexReview.viewer().groundAt(2600, -300)") - _ground(2600.0, -300.0)) <= 5.0
    # The mogul is round: its peak, and half way down its side, are drawn where the sphere is.
    for dx in (0.0, 125.0):
        x, y = MOGUL[0] + dx, MOGUL[1]
        assert abs(page.evaluate("window.cadexReview.viewer().groundAt(%r, %r)" % (x, y)) - _ground(x, y)) <= 1.0
    # The step's face is a wall: 2 mm either side of it the ground is the plane and the step's top.
    assert page.evaluate("window.cadexReview.viewer().groundAt(398, 0)") == pytest.approx(0.0, abs=1e-6)
    assert page.evaluate("window.cadexReview.viewer().groundAt(402, 0)") == pytest.approx(STEP_TOP, abs=1e-3)
    # The surface ends at the plane on every side, where the mat takes over without a seam.
    rim = [(x, y) for x in (x0, x1) for y in (y0, (y0 + y1) / 2, y1)] + [((x0 + x1) / 2, y) for y in (y0, y1)]
    assert page.evaluate("(function (p) { var v = window.cadexReview.viewer(); "
                         "return p.map(function (q) { return v.groundAt(q[0], q[1]); }); })(%s)" % json.dumps(rim)) == [0.0] * len(rim)


# A held-out pool with every kind the engine draws (ADR-745): long flat runs, so rock patches find
# flat ground, moguls up to 80 mm (C3), and platforms 10 to 50 cm high (O4's ladder).
EVERY_KIND = {
    "form": "boxes", "x_range_mm": [-1000.0, 14000.0], "y_range_mm": [-2000.0, 2000.0],
    "random": {"seed": 7, "courses": 8, "run_mm": [1200.0, 2000.0], "step_mm": [50.0, 100.0],
               "grade_deg": [5.0, 15.0], "slope_mm": [400.0, 1000.0], "bump_mm": [30.0, 80.0],
               "bump_radius_mm": [250.0, 400.0], "bumps": 3, "platform_mm": [100.0, 500.0], "platforms": 2,
               "rock_mm": [30.0, 60.0], "rock_radius_mm": [250.0, 400.0], "rocks": 2}}


def _engine():
    # The engine's own course builder, read from source: the claim is that the two halves agree.
    spec = importlib.util.spec_from_file_location("cadex_dynamics_under_test", SOURCE_MODULE_DIR / "CadexDynamics.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _walls(block: dict) -> tuple[list[float], list[float]]:
    """Where a served course's vertical faces stand, along x and along y."""
    xs, ys = [], []
    for box in block["boxes"]:
        qx, qy, qz, qw = box["rotation_xyzw"]
        axes = [[1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy + qz * qw), 2 * (qx * qz - qy * qw)],
                [2 * (qx * qy - qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz + qx * qw)],
                [2 * (qx * qz + qy * qw), 2 * (qy * qz - qx * qw), 1 - 2 * (qx * qx + qy * qy)]]
        for axis, half in zip(axes, box["half_mm"]):
            for k, out in ((0, xs), (1, ys)):
                if abs(abs(axis[k]) - 1.0) < 1e-9:
                    out += [box["centre_mm"][k] - half, box["centre_mm"][k] + half]
    return xs, ys


@needs_browser
def test_the_drawn_ground_is_the_ground_physics_stands_on(app, small_browser) -> None:
    mujoco = pytest.importorskip("mujoco")
    import numpy as np

    engine = _engine()
    descriptor = engine.terrain_grid(EVERY_KIND)["descriptor"]
    spec = mujoco.MjSpec()
    engine._environment_box_course(mujoco, spec, descriptor)
    model = spec.compile()
    data = mujoco.MjData(model)
    page = _open(small_browser, app.url + "p/biped/")
    assert _model_state(page) == "loaded"
    page.evaluate("window.cadexReview.setLook({occlusion: false, detail: false})")
    rng, kinds, worst, compared, walls = random.Random(745), set(), (0.0, None), 0, 0
    (x0, x1), (y0, y1) = EVERY_KIND["x_range_mm"], EVERY_KIND["y_range_mm"]
    for seed in range(10):
        course = engine.terrain_evaluation_course(descriptor, seed)
        kinds |= {feature["kind"] for feature in course["features"]}
        engine.place_terrain_course(model, course)
        mujoco.mj_forward(model, data)
        block = terrain_block(json.loads(json.dumps(engine.terrain_drawing(course))))
        assert page.evaluate("window.cadexReview.viewer().setTerrain(%s)" % json.dumps(block)) > 0
        # Half the points anywhere, 3 m past the extent included (the run-out); half on a feature.
        placed = [f for f in course["features"] if f["kind"] in ("bump", "platform", "rock")]
        points = [(rng.uniform(x0 - 3000, x1 + 3000), rng.uniform(y0 - 3000, y1 + 3000)) for _ in range(50)]
        for _ in range(50):
            f = rng.choice(placed)
            reach = (f["length_mm"] / 2 + 50, f["width_mm"] / 2 + 50) if f["kind"] == "platform" else (f["radius_mm"],) * 2
            points.append((f["x_mm"] + rng.uniform(-1, 1) * reach[0], f["y_mm"] + rng.uniform(-1, 1) * reach[1]))
        drawn = page.evaluate("(function (p) { var v = window.cadexReview.viewer(); "
                              "return p.map(function (q) { return v.groundAt(q[0], q[1]); }); })(%s)" % json.dumps(points))
        # Off the surface the mat is the drawn ground: where a course ends at its plane, the plane.
        mat = page.evaluate("window.cadexReview.viewer().stats().floor.z_mm")
        drawn = [mat if height is None else height for height in drawn]
        wall_x, wall_y = _walls(block)
        def physics(x: float, y: float) -> float:
            geom = np.zeros(1, np.int32)
            distance = mujoco.mj_ray(model, data, np.array([x / 1000, y / 1000, 5.0]),
                                     np.array([0.0, 0.0, -1.0]), None, 1, -1, geom)
            assert distance > 0, (seed, x, y)
            return (5.0 - distance) * 1000.0

        for (x, y), height in zip(points, drawn):
            error = abs(height - physics(x, y))
            # A point within a millimetre of a vertical face is on the wall, which the drawing
            # gives a 1 mm run: anywhere from the foot of the wall to its top is the ground there.
            if min(abs(x - w) for w in wall_x) < 1.0 or min(abs(y - w) for w in wall_y) < 1.0:
                walls += 1
                side = [physics(x + dx, y + dy) for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))]
                error = max(0.0, min(side) - height, height - max(side))
            compared += 1
            if error > worst[0]:
                worst = (error, (seed, x, y, height))
        # No physics edge (G2): 3 to 40 m off either side, and past either end, the ground is the
        # level the course has there, never a fall to its plane.
        profile = lambda x: engine._terrain_profile_mm(course["features"], min(max(x, x0), x1))
        for _ in range(10):
            x, off = rng.uniform(x0 - 40000, x1 + 40000), rng.uniform(3000, 40000)
            for y in (y0 - off, y1 + off):
                assert physics(x, y) == pytest.approx(profile(x), abs=1e-6), (seed, x, y)
    assert kinds == {"step", "slope", "bump", "platform", "rock"}, kinds
    assert compared == 1000 and walls <= 50, (compared, walls)
    assert worst[0] <= 5.0, worst
