# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""``cadex hero``, the project's presentation folder (ADR-677; docs/DASHBOARD.md §26).

The turn's wipes follow each other in order and the turn ends in the design's
own materials; the rollout shown is the one any policy lasted longest in, the
newest among equals; each item stands alone, so one that cannot be made is
named in ``hero.json`` while the rest are made; the hero page frames, wipes
and plots on geometry whose answer is known; and the encoder crossfades its
parts into one video of the expected length. Browser tests skip without a
Chromium, and the encoder's without FFmpeg.
"""

from __future__ import annotations

import json
import subprocess

import pytest

from cadex_cli import hero
from test_dashboard_viewport_look import SOLIDS
from test_review_checkpoints import RUN, _trace, _training_run
from test_review_record import REVISION_B, _manifest, _project
from test_review_server import browser, needs_browser, served  # noqa: F401  (fixtures)


def test_the_turn_wipes_each_look_in_order_and_ends_in_the_designs_own_materials() -> None:
    spec = hero.TURNTABLE
    starts = [layer["at"] for layer in spec["layers"][1:]]
    assert starts == sorted(starts)
    # Each wipe finishes before the next begins, and the last before the turn ends.
    assert all(a + spec["wipe_s"] <= b for a, b in zip(starts, starts[1:]))
    assert starts[-1] + spec["wipe_s"] < spec["seconds"]
    assert [layer.get("look") or layer.get("style") for layer in spec["layers"]] == [
        "clay", "aluminium", "wireframe", "studio"]
    first = hero.turntable_layers(0.0)
    assert first[0] == {"look": "clay"} and [layer["wipe"] for layer in first[1:]] == [0, 0, 0]
    middle = hero.turntable_layers(starts[1] + spec["wipe_s"] / 2)
    assert [layer["wipe"] for layer in middle[1:]] == [1, pytest.approx(0.5), 0]
    assert [layer["wipe"] for layer in hero.turntable_layers(spec["seconds"])[1:]] == [1, 1, 1]


def test_the_rollout_shown_is_the_longest_episode_and_the_newest_among_equals(tmp_path) -> None:
    root = _project(tmp_path)
    _manifest(root, REVISION_B)
    train = _training_run(root) / "train"
    assert hero.choose_rollout(root) is None
    (train / "walk.000020.rollout-trace.json").write_text(json.dumps(_trace("000020", 19, 0.5, frames=3)))
    (train / "walk.000040.rollout-trace.json").write_text(json.dumps(_trace("000040", 39, 1.2, frames=9)))
    (train / "walk.000060.rollout-trace.json").write_text(json.dumps(_trace("000060", 59, 1.5, frames=5)))
    chosen = hero.choose_rollout(root)
    assert (chosen["run"], chosen["stem"], chosen["kind"]) == (RUN, "walk.000040", "checkpoint")
    assert chosen["duration_s"] == pytest.approx(0.32)
    assert chosen["url"] == f"api/playback/checkpoint/{RUN}/walk.000040"
    assert chosen["model"] == f"api/model/run/{RUN}"
    # An episode as long, later in training, is preferred.
    (train / "walk.000080.rollout-trace.json").write_text(json.dumps(_trace("000080", 79, 0.9, frames=9)))
    assert hero.choose_rollout(root)["stem"] == "walk.000080"
    with pytest.raises(hero.HeroError, match="no run named"):
        hero.choose_rollout(root, "elsewhere")


def test_each_item_stands_alone_and_the_folder_says_what_was_not_made(tmp_path) -> None:
    root = _project(tmp_path)
    _manifest(root, REVISION_B)
    called = []

    def sheet(project_root):
        called.append(project_root)
        raise RuntimeError("the engine is busy")

    manifest = hero.make(root, only=("sheet",), sheet=sheet)
    folder = root / "hero"
    assert called == [root.resolve()]
    assert manifest["items"] == {} and manifest["errors"]["sheet"] == "RuntimeError: the engine is busy"
    assert json.loads((folder / "hero.json").read_text())["errors"] == manifest["errors"]
    # Bulk, drawn again on request: kept out of the project's history.
    assert (folder / ".gitignore").read_text().splitlines()[-1] == "*"
    # Without an engine to draw it, the sheet says what makes one.
    assert "run cadex render" in hero.make(root, only=("sheet",))["errors"]["sheet"]


def _hero_page(browser, server):
    page = browser.page(server.url + "hero.html")
    page.wait_for("window.cadexHero && window.cadexHero.available")
    assert page.evaluate(SOLIDS)
    page.evaluate("cadexHero.size(320, 180, 1)")
    page.evaluate("cadexHero.viewer.install([T.entry('body', T.box(-60,-20,0,60,20,50), "
                  "{finish:'printed', color:'#d9d4cb'}), T.entry('mast', T.box(-8,-8,50,8,8,110), {finish:'printed'})])")
    return page


def _image_pixels(page):
    """The hero frame's RGB pixels, row by row."""
    return page.evaluate("""(function () {
      var img = new Image(); return new Promise(function (ok) {
        img.onload = function () { var c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
          var x = c.getContext('2d'); x.drawImage(img, 0, 0); var d = x.getImageData(0, 0, c.width, c.height).data, rows = [];
          for (var y = 0; y < c.height; y++) { var row = []; for (var i = 0; i < c.width; i++) { var k = 4 * (y * c.width + i); row.push([d[k], d[k+1], d[k+2]]); } rows.push(row); }
          ok(rows); };
        img.src = 'data:image/png;base64,' + cadexHero.image('png'); }); })()""", await_promise=True)


@needs_browser
def test_the_hero_page_frames_wipes_and_plots(served, browser) -> None:
    _root, server = served
    page = _hero_page(browser, server)
    # Framed by the design's own outline at that view: centred, filling the asked share of the height.
    page.evaluate("cadexHero.fitCamera({yaw: .8, pitch: .3, fill: .7})")
    x0, y0, x1, y1 = page.evaluate("cadexHero.viewer.screenBox()")
    assert abs((x0 + x1) / 2 - 160) < 4 and abs((y0 + y1) / 2 - 90) < 4
    assert max((x1 - x0) / 320, (y1 - y0) / 180) == pytest.approx(0.7, abs=0.03)
    # One distance for the whole turn: no view of it overfills the frame.
    camera = page.evaluate("cadexHero.fitCamera({yaw: .8, pitch: .3, fill: .7, yaws: [0, 1.5, 3, 4.5]})")
    for yaw in (0, 1.5, 3, 4.5):
        page.evaluate(f"cadexHero.viewer.setCamera(Object.assign({json.dumps(camera)}, {{yaw: {yaw}}}))")
        bx0, by0, bx1, by1 = page.evaluate("cadexHero.viewer.screenBox()")
        assert bx0 >= 160 - 0.71 * 160 and bx1 <= 160 + 0.71 * 160 and by0 >= 90 - 0.71 * 90 and by1 <= 90 + 0.71 * 90

    # A wipe half across: the wireframe's flat paper on the top left, the shaded mat bottom right.
    page.evaluate("cadexHero.shot({camera: " + json.dumps(camera) + ", layers: [{look: 'clay'}, {style: 'wireframe', wipe: .5}]})")
    rows = _image_pixels(page)
    paper = rows[4][4]
    assert all(abs(c - p) <= 3 for c, p in zip(paper, (0x1b, 0x1b, 0x1b)))
    assert rows[175][315] != paper
    assert page.evaluate("cadexHero.viewer.style()") == "wireframe"
    # Fully across, the new layer is the whole frame.
    page.evaluate("cadexHero.shot({layers: [{look: 'clay'}, {style: 'wireframe', wipe: 1}]})")
    rows = _image_pixels(page)
    assert all(abs(c - p) <= 3 for c, p in zip(rows[175][315], (0x1b, 0x1b, 0x1b)))

    # The curves draw themselves: at a quarter of the way, nothing past the first half of the axis.
    spec = {"title": "t", "subtitle": "s", "progress": 0.25, "layout": "row",
            "panels": [{"label": "reward per step", "points": [[i, i * 0.1] for i in range(1, 101)], "best": [100, 10]}]}
    page.evaluate("cadexHero.plot(" + json.dumps(spec) + ")")
    rows = _image_pixels(page)
    lit = [x for row in rows[40:170] for x, rgb in enumerate(row) if min(rgb) > 180]
    assert lit and max(lit) < 180
    spec["progress"] = 1
    page.evaluate("cadexHero.plot(" + json.dumps(spec) + ")")
    rows = _image_pixels(page)
    assert max(x for row in rows[40:170] for x, rgb in enumerate(row) if min(rgb) > 180) > 260


def test_the_parts_are_crossfaded_into_one_video(tmp_path) -> None:
    try:
        encoder = hero.ffmpeg()
    except ValueError:
        pytest.skip("no FFmpeg")
    parts = []
    for name, colour, seconds in (("a", "red", 1.0), ("b", "blue", 2.0)):
        directory = tmp_path / name
        directory.mkdir()
        subprocess.run([encoder, "-v", "error", "-f", "lavfi", "-i", f"color=c={colour}:s=64x64:d={seconds}:r={hero.FPS}",
                        str(directory / "%05d.png")], check=True)
        parts.append(directory)
    made = hero.encode(parts, tmp_path / "out.mp4")
    assert made["seconds"] == pytest.approx(1.0 + 2.0 - hero.FADE_S)
    check = subprocess.run([encoder, "-v", "error", "-i", str(tmp_path / "out.mp4"), "-f", "framemd5", "-"],
                           capture_output=True, check=True)
    frames = [line for line in check.stdout.splitlines() if line and not line.startswith(b"#")]
    assert len(frames) == round(made["seconds"] * hero.FPS)
    assert not (tmp_path / "out.partial.mp4").exists()


def test_the_command_writes_no_progress_row_and_makes_no_commit(tmp_path, monkeypatch) -> None:
    from cadex_cli import __main__ as cli
    root = _project(tmp_path)
    _manifest(root, REVISION_B)
    (root / "script.json").write_text("{}")
    calls = []
    monkeypatch.setattr(cli, "append_progress_row", lambda *a, **k: calls.append("row"))
    monkeypatch.setattr(cli, "commit_project", lambda *a, **k: calls.append("commit") or "abc")
    monkeypatch.setattr(cli, "make_hero", lambda root, **k: {"items": {"stills": {}}, "errors": {}, "seconds": 1.0,
                                                            "revision": REVISION_B})
    assert cli.main(["hero", "--project", str(root), "--no-engine"]) == cli.EXIT_OK
    assert calls == []
    assert cli.main(["hero", "--project", str(root), "--only", "bogus"]) == cli.EXIT_USAGE


def test_a_partial_run_keeps_what_the_folder_says_of_the_other_items(tmp_path) -> None:
    root = _project(tmp_path)
    _manifest(root, REVISION_B)
    folder = root / "hero"
    folder.mkdir()
    (folder / "hero.json").write_text(json.dumps({"schema": hero.SCHEMA, "items": {"video": {"landscape": {}}},
                                                  "errors": {"rollout": "no run"}}))
    manifest = hero.make(root, only=("sheet",))
    assert manifest["items"]["video"] == {"landscape": {}} and manifest["errors"]["rollout"] == "no run"
    assert "sheet" in manifest["errors"]


def test_the_grid_tiles_each_projects_still_in_reading_order(tmp_path) -> None:
    try:
        encoder = hero.ffmpeg()
    except ValueError:
        pytest.skip("no FFmpeg")
    colours = ("red", "green", "blue")
    projects = []
    for name, colour in zip("abc", colours):
        folder = tmp_path / name / "hero"
        folder.mkdir(parents=True)
        subprocess.run([encoder, "-v", "error", "-f", "lavfi", "-i", f"color=c={colour}:s=32x18:d=1",
                        "-frames:v", "1", str(folder / "still-wireframe.png")], check=True)
        projects.append(tmp_path / name)
    made = hero.grid(projects, tmp_path / "out" / "grid.png")
    assert (made["rows"], made["columns"], made["projects"]) == (2, 2, ["a", "b", "c"])
    raw = subprocess.run([encoder, "-v", "error", "-i", str(tmp_path / "out" / "grid.png"), "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    assert len(raw) == 64 * 36 * 3

    def pixel(x, y):
        k = 3 * (y * 64 + x)
        return tuple(raw[k:k + 3])

    # Left to right, then top to bottom; the missing fourth tile is the dark mat.
    assert pixel(8, 8)[0] > 200 and pixel(40, 8)[1] > 100 and pixel(8, 26)[2] > 200
    assert max(pixel(40, 26)) < 40
    with pytest.raises(hero.HeroError, match="still-studio.png is missing"):
        hero.grid(projects, tmp_path / "x.png", still="studio")


def test_the_stills_include_a_wireframe_three_quarter_view() -> None:
    wire = [s for s in hero.STILLS if s.get("style") == "wireframe"]
    assert len(wire) == 1 and wire[0]["name"] == "wireframe"
    assert hero.WIRE_TURN["seconds"] < hero.TURNTABLE["seconds"] and hero.WIRE_TURN["layers"] == ({"style": "wireframe"},)
