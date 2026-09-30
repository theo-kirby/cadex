# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""An evaluation's film: the filmstrip and the video of its seeds (ADR-459).

Everything here runs on a hand-built retained attempt -- two boxes'
tessellations, a floor the assembly calls world geometry -- and hand-written
traces, so it needs no engine and no ``mujoco``. The frames are drawn small;
the real frame size is asserted as a constant. The video tests need FFmpeg
and skip without it.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import struct
import subprocess
import types
import zlib

import pytest

from cadex_cli import film
from cadex_cli import video as studio_video
from cadex_cli.evaluate import REPORT_NAME, add_film, human_lines, read_report, EvaluateRefused
from cadex_cli.studio import STUDIO

from test_evaluate import _code

REVISION = "a" * 64
DIGEST = "d" * 64
BG = STUDIO.PALETTE["bg"]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _box(lo, hi) -> tuple[list, list]:
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    vertices = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return vertices, [t for a, b, c, d in quads for t in ((a, b, c), (a, c, d))]


def _tessellation(staging: Path, index: int, lo, hi) -> dict:
    vertices, triangles = _box(lo, hi)
    points = b"".join(struct.pack("<3f", *v) for v in vertices)
    indices = b"".join(struct.pack("<3I", *t) for t in triangles)
    (staging / "display").mkdir(exist_ok=True)
    stem = f"display/display-{index:03d}.tess"
    (staging / f"{stem}.bin").write_bytes(points + indices)
    (staging / f"{stem}.json").write_text(json.dumps({
        "schema": "cadex-tessellation-v1", "byte_order": "little",
        "layout": {"vertices": {"offset": 0, "bytes": len(points), "dtype": "f32"},
                   "triangles": {"offset": len(points), "bytes": len(indices), "dtype": "u32"}}}))
    return {"artifact_kind": "tessellation", "artifact_path": f"{stem}.bin",
            "sidecar_path": f"{stem}.json"}


def _project(root: Path, *, world: bool = True) -> Path:
    """A project as the store leaves one: a body on two posts, and a floor slab."""

    staging = root / "script_artifacts" / REVISION / "attempt-1"
    staging.mkdir(parents=True)
    solids = {"body": ((-40, -20, 30), (40, 20, 50)), "post": ((-5, -5, 0), (5, 5, 30)),
              "floor": ((-500, -500, -10), (500, 500, 0))}
    outputs = []
    for index, (name, (lo, hi)) in enumerate(solids.items()):
        outputs.append({"name": name, "artifact_kind": "brep",
                        "display": _tessellation(staging, index, lo, hi)})
    components = {"c_body": "body", "c_post_a": "post", "c_post_b": "post", "c_floor": "floor"}
    outputs += [{"name": name, "type": "component_link", "source_output": source}
                for name, source in components.items()]
    outputs.append({"name": "assembly", "type": "assembly", "world_geometry": (
        [{"component": "c_floor", "status": "world geometry"}] if world else [])})
    outputs.append({"name": "model", "artifact_kind": "assembly_mjcf_xml",
                    "assembly_data": {"assembly_output": "assembly",
                                      "component_outputs": list(components)}})
    (staging / "result.json").write_text(json.dumps({"ok": True, "digest": DIGEST, "outputs": outputs}))
    (root / "script.json").write_text(json.dumps({
        "schema": "cadex-project-script-v1", "accepted_revision": REVISION,
        "accepted_digest": DIGEST,
        "accepted_attempt": {"revision": REVISION, "staging": str(staging.relative_to(root))}}))
    return staging


def _pose(x: float, y: float, z: float = 0.0) -> dict:
    return {"position_mm": [x, y, z], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}


#: What a trace whose task states a commanded speed and a target declares
#: once (ADR-462): each frame's ``goal`` row is read in this order.
GOAL_CHANNELS = [{"channel": "pace", "goal": "pace", "kind": "speed", "unit": "mm/s"}] + [
    {"channel": f"target_{axis}", "goal": "target", "kind": "point", "unit": "mm"} for axis in "xyz"]


def _trace(out: Path, seed: int, *, seconds: float = 4.0, velocity=(100.0, 0.0), hz: int = 50,
           trailing: float = 1.0, target=None, channels=GOAL_CHANNELS) -> dict:
    """One seed's trace: the design translating at ``velocity`` mm/s over its floor.

    ``trailing`` is the share of that velocity the rear post keeps: at 0 it
    stays where it started while the body and the front post leave it.
    ``target`` maps a time to the point the episode asks for at that time;
    with one, the trace carries its goal as the engine's does.
    """

    frames = [{"frame_kind": "input", "nominal_time_s": None, "component_placements": {}}]
    for step in range(int(round(seconds * hz)) + 1):
        t = step / hz
        x, y = velocity[0] * t, velocity[1] * t
        frames.append({"frame_kind": "solver_output", "nominal_time_s": t, "component_placements": {
            "c_body": _pose(x, y), "c_post_a": _pose(trailing * x - 30, trailing * y),
            "c_post_b": _pose(x + 30, y),
            "c_floor": _pose(0, 0)},
            **({"goal": [80.0, *target(t)]} if target else {})})
    data = json.dumps({"schema": film.TRACE_SCHEMA, "frames": frames,
                       **({"goal_channels": channels} if target else {})}).encode()
    out.mkdir(parents=True, exist_ok=True)
    (out / f"seed-{seed}-trace.json").write_bytes(data)
    return {"file": f"seed-{seed}-trace.json", "sha256": _sha(data), "bytes": len(data)}


def _report(out: Path, seeds=(1101, 1102), *, passing=(), floor=0.0, onset=1.0, base="c_body",
            **trace) -> dict:
    rows = [{"seed": seed, "pass": seed in passing, "trace": _trace(out, seed, **trace),
             "drawn": {"disturbance": [] if onset is None else [{"label": "shove", "start_s": onset}]}}
            for seed in seeds]
    return {"schema": "cadex-evaluation-v1", "accepted_revision": REVISION, "policy_sha256": "p" * 64,
            "model_output": "model", "rig": {"floor_mm": floor, "base": base}, "seeds": rows,
            "summary": {"seeds": len(rows), "passed": list(passing), "predicates": []},
            "verdict": "pass" if set(passing) == set(seeds) else "fail"}


def _pixels(path: Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">2I", data[16:24])
    at, body = 8, b""
    while at < len(data):
        length, kind = struct.unpack(">I4s", data[at:at + 8])
        if kind == b"IDAT":
            body += data[at + 8:at + 8 + length]
        at += 12 + length
    raw = zlib.decompress(body)
    stride = 1 + 3 * width
    assert all(raw[y * stride] == 0 for y in range(height))
    return width, height, b"".join(raw[y * stride + 1:(y + 1) * stride] for y in range(height))


def _frame(pixels: tuple[int, int, bytes], index: int, size: int) -> list[tuple[int, int, int]]:
    """Frame ``index`` of a sheet, as rows of RGB flattened."""

    width, _height, data = pixels
    x0 = (index % film.COLUMNS) * (size + film.GUTTER)
    y0 = (index // film.COLUMNS) * (size + film.GUTTER)
    return [tuple(data[3 * ((y0 + y) * width + x0 + x):3 * ((y0 + y) * width + x0 + x) + 3])
            for y in range(size) for x in range(size)]


def _bright_centre(frame, size: int) -> tuple[float, float]:
    """Where the design is in a frame: the centroid of pixels brighter than the mat's ink."""

    hits = [(i % size, i // size) for i, p in enumerate(frame[:size * (size - 30)]) if min(p) > 170]
    assert hits, "nothing bright was drawn"
    return sum(x for x, _ in hits) / len(hits), sum(y for _, y in hits) / len(hits)


@pytest.fixture
def small(monkeypatch):
    """Draw 96 px frames: the layout and the sampling are what is under test."""

    monkeypatch.setattr(film, "FRAME", 96)
    return 96


def test_a_sheet_is_twelve_frames_a_judge_can_read() -> None:
    assert (film.COLUMNS, film.ROWS, film.STRIP) == (4, 3, 12)
    assert film.FRAME >= 256
    # One sheet stays inside what a vision model reads without downscaling.
    assert film.COLUMNS * film.FRAME + (film.COLUMNS - 1) * film.GUTTER <= 1568


# -- which seeds ---------------------------------------------------------------

def test_auto_films_the_first_failing_seed_and_a_pass_films_its_first() -> None:
    rows = [{"seed": 1101, "pass": True}, {"seed": 1102, "pass": False}, {"seed": 1103, "pass": False}]
    assert film.choose_seeds({"seeds": rows}, "auto") == [1102]
    assert film.choose_seeds({"seeds": [{"seed": 7, "pass": True}, {"seed": 8, "pass": True}]}, "auto") == [7]
    assert film.choose_seeds({"seeds": rows}, "all") == [1101, 1102, 1103]
    assert film.choose_seeds({"seeds": rows}, "none") == []
    assert film.choose_seeds({"seeds": rows}, "1103, 1101,1103") == [1103, 1101]


def test_a_seed_the_evaluation_did_not_run_is_refused_by_name() -> None:
    report = {"seeds": [{"seed": 1101, "pass": True}]}
    with pytest.raises(film.FilmError, match="did not run: 1199; it ran 1101"):
        film.choose_seeds(report, "1101,1199")
    for choice in ("first", "1101,x"):
        with pytest.raises(film.FilmError, match="auto, all, none or seed numbers"):
            film.choose_seeds(report, choice)


# -- the solids ------------------------------------------------------------------

def test_the_solids_are_the_accepted_attempts_own_tessellation(tmp_path) -> None:
    _project(tmp_path)
    flats, sources, world = film.retained_solids(tmp_path, "model")

    assert sources == {"c_body": "body", "c_post_a": "post", "c_post_b": "post", "c_floor": "floor"}
    assert {name: len(flat) // 9 for name, flat in flats.items()} == dict.fromkeys(sources, 12)
    assert world == {"c_floor"}
    # Each component in its own frame: both posts are the one post, unplaced.
    assert flats["c_post_a"] == flats["c_post_b"]
    assert (min(flats["c_body"][2::3]), max(flats["c_body"][2::3])) == (30.0, 50.0)


def test_a_component_with_no_retained_tessellation_is_a_reason_not_a_blank(tmp_path) -> None:
    staging = _project(tmp_path)
    result = json.loads((staging / "result.json").read_text())
    next(item for item in result["outputs"] if item["name"] == "post").pop("display")
    (staging / "result.json").write_text(json.dumps(result))
    with pytest.raises(film.FilmError, match="no tessellation for c_post_a"):
        film.retained_solids(tmp_path, "model")


def test_a_tessellation_outside_the_attempt_is_never_read(tmp_path) -> None:
    staging = _project(tmp_path)
    (tmp_path / "elsewhere.bin").write_bytes(b"x")
    result = json.loads((staging / "result.json").read_text())
    next(item for item in result["outputs"] if item["name"] == "body")["display"][
        "artifact_path"] = "../../../elsewhere.bin"
    (staging / "result.json").write_text(json.dumps(result))
    with pytest.raises(film.FilmError, match="missing or escaping"):
        film.retained_solids(tmp_path, "model")


# -- what each part is made of -------------------------------------------------

def test_materials_are_the_declared_roles_then_supplier(tmp_path) -> None:
    sources = {"c_body": "body", "c_post_a": "post", "c_post_b": "post"}
    inventory = {"revision": REVISION, "uncatalogued_sources": ["body"],
                 "palette": {"accent": "#102030"},
                 "components": [{"component": "c_post_b", "appearance": "accent"},
                                {"component": "c_body"}]}
    looks, source = film.materials(sources, list(sources), REVISION, inventory)

    assert looks["c_body"] == ("shell", STUDIO.ROLE_COLORS["shell"])          # printed
    assert looks["c_post_a"] == ("mechanism", STUDIO.ROLE_COLORS["mechanism"])  # catalogued
    assert looks["c_post_b"] == ("accent", (0x10, 0x20, 0x30))                # declared, recoloured
    assert source["declared"] is True


@pytest.mark.parametrize("inventory", [None, {"revision": "b" * 64, "uncatalogued_sources": []},
                                       {"revision": REVISION}])
def test_without_this_revisions_inventory_every_part_is_shell_and_the_film_says_so(inventory) -> None:
    looks, source = film.materials({"c_body": "body"}, ["c_body"], REVISION, inventory)
    assert looks == {"c_body": ("shell", STUDIO.ROLE_COLORS["shell"])}
    assert source["declared"] is False and "every part drawn as shell" in source["source"]


# -- the sheets --------------------------------------------------------------------

def test_a_filmed_seed_has_an_overview_and_a_detail_on_the_dark_floor(tmp_path, small) -> None:
    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    report = _report(out)
    block = film.film_evaluation(tmp_path, out, report, seeds=[1101], video=False)

    assert block["schema"] == film.FILM_SCHEMA and block["state"] == "ready" and block["error"] is None
    assert block["style"] == "studio" and block["style_sha256"] == film.film_digest()
    assert block["frame_px"] == small and "dark prototype mat" in block["floor"]
    assert block["materials"]["environment_omitted"] == ["c_floor"]
    assert set(block["appearance"]) == {"c_body", "c_post_a", "c_post_b"}
    (seed,) = block["seeds"]
    assert seed["seed"] == 1101 and seed["video"] is None
    assert seed["trace_sha256"] == report["seeds"][0]["trace"]["sha256"]
    assert (seed["floor_z_mm"], seed["floor_source"]) == (0.0, "the model's collision plane")
    side = film.COLUMNS * small + (film.COLUMNS - 1) * film.GUTTER
    for key, name in (("overview", "seed-1101-overview.png"), ("detail", "seed-1101-detail.png")):
        sheet = seed[key]
        path = out / name
        assert sheet["file"] == name and sheet["sha256"] == _sha(path.read_bytes())
        assert sheet["bytes"] == path.stat().st_size and sheet["frames"] == 12
        width, height, _ = pixels = _pixels(path)
        assert (width, height) == (sheet["width"], sheet["height"]) == (
            side, film.ROWS * small + (film.ROWS - 1) * film.GUTTER)
        for index in range(12):
            frame = _frame(pixels, index, small)
            # The dark scene: no pixel of the backdrop is lighter than the
            # mat's line, and most of the frame is backdrop.
            dark = sum(1 for p in frame if max(p) <= max(STUDIO.PALETTE["line"]) + 2)
            assert dark > 0.5 * len(frame), (key, index)
            # Every frame carries its time: the label's ink, bottom left.
            label = [frame[y * small + x] for y in range(small - 24, small - 10) for x in range(10, 90)]
            assert STUDIO.PALETTE["ink_2"] in label, (key, index)
    # The gutters are the scene's background.
    width, _, data = _pixels(out / "seed-1101-overview.png")
    assert tuple(data[3 * (small + 1):3 * (small + 1) + 3]) == BG


def test_the_overview_spans_the_episode_in_one_window_on_the_whole_path(tmp_path, small) -> None:
    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    block = film.film_evaluation(tmp_path, out, _report(out, seconds=4.4), seeds=[1101], video=False)
    sheet = block["seeds"][0]["overview"]

    assert sheet["times_s"] == pytest.approx([0.4 * k for k in range(12)], abs=0.011)
    assert sheet["times_s"][0] == 0.0 and sheet["times_s"][-1] == 4.4
    # 440 mm of travel and an 80 mm body, in one fixed window.
    assert sheet["half_extent_mm"] > 220
    pixels = _pixels(out / sheet["file"])
    first, last = (_bright_centre(_frame(pixels, index, small), small) for index in (0, 11))
    assert last[0] - first[0] > 0.3 * small, "the design did not cross the fixed window"


def test_the_detail_starts_at_the_first_disturbance_and_follows_side_on(tmp_path, small) -> None:
    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    block = film.film_evaluation(tmp_path, out, _report(out, onset=1.0, velocity=(0.0, 100.0)),
                                 seeds=[1101], video=False)
    sheet = block["seeds"][0]["detail"]

    assert sheet["start_source"] == "the seed's first disturbance"
    assert (sheet["requested_start_s"], sheet["start_s"], sheet["step_s"]) == (1.0, 1.0, film.DETAIL_STEP_S)
    assert sheet["times_s"] == pytest.approx([1.0 + 0.2 * k for k in range(12)])
    # It travelled along +Y, so the camera's right is +Y.
    assert sheet["azimuth_degrees"] == pytest.approx(90.0) and sheet["travel_mm"] == pytest.approx(400.0)
    # Followed: the design stays where it was in the frame while it moves 220 mm.
    pixels = _pixels(out / sheet["file"])
    centres = [_bright_centre(_frame(pixels, index, small), small)[0] for index in range(12)]
    assert max(centres) - min(centres) < 0.06 * small
    assert sheet["half_extent_mm"] < 80


@pytest.fixture
def windows(monkeypatch):
    """Every frame's window as it was drawn: ``(poses, basis, (lo, hi))``."""

    seen = []
    draw = film._Stage.draw

    def recording(self, poses, basis, bounds, floor, clock, target=None):
        seen.append((poses, basis, bounds))
        return draw(self, poses, basis, bounds, floor, clock, target=target)

    monkeypatch.setattr(film._Stage, "draw", recording)
    return seen


def _along(basis, position) -> float:
    return sum(a * b for a, b in zip(basis[0], position))


def test_the_detail_follows_the_evaluations_base_not_the_middle_of_the_design(tmp_path, small, windows) -> None:
    """The body is the base and walks off along +Y; one post stays behind.

    The middle of the design goes half as far as the base does. The window
    is centred on the base in every frame, the side-on direction and the
    travel are the base's, and the post left behind is still in the window.
    """

    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    block = film.film_evaluation(tmp_path, out, _report(out, velocity=(0.0, 100.0), trailing=0.0),
                                 seeds=[1101], video=False)
    sheet = block["seeds"][0]["detail"]

    assert sheet["follows"] == "c_body" and "follows the base" in sheet["view"]
    assert sheet["azimuth_degrees"] == pytest.approx(90.0) and sheet["travel_mm"] == pytest.approx(400.0)
    shown = windows[film.STRIP:]            # the overview's twelve come first
    assert len(shown) == 12
    for poses, basis, (lo, hi) in shown:
        base = poses["c_body"]["position_mm"]
        # The body's bounds are symmetric about its own origin, so its middle is its position.
        assert (lo[0] + hi[0]) / 2 == pytest.approx(_along(basis, base), abs=1e-6)
        assert lo[0] < _along(basis, poses["c_post_a"]["position_mm"]) - 5
    assert shown[0][2][0][1] == shown[-1][2][0][1], "the window moved up or down"
    # 320 mm back to the post by the last moment, and the margin round it.
    assert sheet["half_extent_mm"] == pytest.approx((320 + 5) * (1 + 2 * film.PAD), rel=0.02)


def test_a_mechanism_with_no_floating_base_is_detailed_in_one_fixed_window(tmp_path, small, windows) -> None:
    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    block = film.film_evaluation(tmp_path, out, _report(out, base=None), seeds=[1101], video=False)
    sheet = block["seeds"][0]["detail"]

    assert sheet["follows"] is None and "the window is fixed" in sheet["view"]
    shown = windows[film.STRIP:]
    assert len({(tuple(lo), tuple(hi)) for _poses, _basis, (lo, hi) in shown}) == 1
    # 220 mm of travel over the twelve moments and the 80 mm body, all in it.
    assert sheet["half_extent_mm"] == pytest.approx((220 + 80) / 2 * (1 + 2 * film.PAD))


# -- the target marker (ADR-463) ---------------------------------------------------

A, B = (60.0, 40.0, 120.0), (-80.0, -30.0, 25.0)


def _two_targets(t: float) -> tuple[float, float, float]:
    """Target A, then target B from 2.0 s."""

    return A if t < 2.0 else B


def _ring(frame, size: int) -> list[tuple[int, int]]:
    """The pixels of a frame that are the marker's colour and nothing the scene draws."""

    return [(i % size, i // size) for i, (r, g, b) in enumerate(frame) if g > 150 and b > 150 and g - r > 60]


def _middle(hits) -> tuple[float, float]:
    return sum(x for x, _ in hits) / len(hits) + .5, sum(y for _, y in hits) / len(hits) + .5


def test_a_trace_that_says_where_to_go_is_marked_there_in_every_frame(tmp_path, small, windows) -> None:
    """The frozen filmstrip's "a frame shows the target as a marker": a ring
    centred where the target in force at the frame's own time projects, in
    both sheets, that jumps when the target does."""

    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    report = _report(out, base=None, velocity=(0.0, 0.0), onset=None, target=_two_targets)
    block = film.film_evaluation(tmp_path, out, report, seeds=[1101], video=False)
    (seed,) = block["seeds"]

    assert seed["target"] == {"goal": "target", "channels": ["target_x", "target_y", "target_z"],
                              "unit": "mm", "positions": [{"from_s": 0.0, "point_mm": list(A)},
                                                          {"from_s": 2.0, "point_mm": list(B)}]}
    assert block["marker"]["color"] == "#6FF0F0" and block["marker"]["radius_px"] == film.MARKER_RADIUS * small
    for key, shown in (("overview", windows[:film.STRIP]), ("detail", windows[film.STRIP:])):
        sheet = seed[key]
        assert sheet["marked_frames"] == 12
        pixels = _pixels(out / sheet["file"])
        middles = []
        for index, (when, (_poses, basis, bounds)) in enumerate(zip(sheet["times_s"], shown)):
            frame = _frame(pixels, index, small)
            hits = _ring(frame, small)
            assert len(hits) >= 8, (key, index)
            expected = film._pixel(small, basis, bounds, _two_targets(when))
            middles.append(_middle(hits))
            assert middles[-1] == pytest.approx(expected, abs=0.75), (key, index)
            # A ring, not a disc: what is at the target stays visible through it.
            cx, cy = (int(value) for value in expected)
            assert (cx, cy) not in hits, (key, index)
            assert all(abs(math.hypot(x + .5 - expected[0], y + .5 - expected[1])
                           - film.MARKER_RADIUS * small) < 2 for x, y in hits), (key, index)
        moved = [at for at in range(1, 12) if math.dist(middles[at], middles[at - 1]) > 1]
        # One jump, at the first frame from 2.0 s on.
        assert moved == [next(at for at, when in enumerate(sheet["times_s"]) if when >= 2.0)], key


def test_a_trace_that_says_nothing_about_where_to_go_is_not_marked(tmp_path, small) -> None:
    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    block = film.film_evaluation(tmp_path, out, _report(out), seeds=[1101], video=False)
    (seed,) = block["seeds"]
    assert seed["target"] is None
    for key in ("overview", "detail"):
        assert seed[key]["marked_frames"] == 0
        pixels = _pixels(out / seed[key]["file"])
        assert not any(_ring(_frame(pixels, index, small), small) for index in range(12)), key


def test_the_marker_is_drawn_over_the_solids(tmp_path, small) -> None:
    """A tip that arrives at its target does not hide it: the ring is whole
    when the target is in the middle of the body."""

    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    inside = film.film_evaluation(
        tmp_path, out, _report(out, base=None, velocity=(0.0, 0.0), target=lambda t: (0.0, 0.0, 40.0)),
        seeds=[1101], video=False)["seeds"][0]
    covered = [len(_ring(_frame(_pixels(out / inside[key]["file"]), 0, small), small))
               for key in ("overview", "detail")]
    clear = film.film_evaluation(
        tmp_path, out, _report(out, base=None, velocity=(0.0, 0.0), target=lambda t: (0.0, 60.0, 100.0)),
        seeds=[1101], video=False)["seeds"][0]
    free = [len(_ring(_frame(_pixels(out / clear[key]["file"]), 0, small), small))
            for key in ("overview", "detail")]
    assert min(covered) >= 8 and covered == pytest.approx(free, abs=4)


def test_a_fixed_window_holds_the_target_and_a_following_one_stays_the_designs_size(tmp_path, small) -> None:
    far = lambda t: (0.0, 400.0, 300.0)                                     # noqa: E731
    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    plain = film.film_evaluation(tmp_path, out, _report(out, base=None, velocity=(0.0, 0.0)),
                                 seeds=[1101], video=False)["seeds"][0]
    fixed = film.film_evaluation(tmp_path, out, _report(out, base=None, velocity=(0.0, 0.0), target=far),
                                 seeds=[1101], video=False)["seeds"][0]
    # No floating base: both windows grow to hold a target far outside the design.
    assert fixed["overview"]["half_extent_mm"] > 2 * plain["overview"]["half_extent_mm"]
    assert fixed["detail"]["half_extent_mm"] > 2 * plain["detail"]["half_extent_mm"]
    assert fixed["overview"]["marked_frames"] == fixed["detail"]["marked_frames"] == 12

    followed = film.film_evaluation(tmp_path, out, _report(out, velocity=(0.0, 0.0), target=far),
                                    seeds=[1101], video=False)["seeds"][0]
    # A base is followed at the design's size: the overview holds the target, the detail does not.
    assert followed["overview"]["marked_frames"] == 12
    assert followed["detail"]["half_extent_mm"] == plain["detail"]["half_extent_mm"]
    assert followed["detail"]["marked_frames"] == 0
    pixels = _pixels(out / followed["detail"]["file"])
    assert not any(_ring(_frame(pixels, index, small), small) for index in range(12))


def test_a_point_goal_the_film_cannot_place_is_a_reason(tmp_path, small) -> None:
    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    metres = [{**row, "unit": "m"} for row in GOAL_CHANNELS]
    with pytest.raises(film.FilmError, match="'target' is not three channels in millimetres"):
        film.film_evaluation(tmp_path, out, _report(out, target=_two_targets, channels=metres),
                             seeds=[1101], video=False)
    with pytest.raises(film.FilmError, match="'target' is not three channels in millimetres"):
        film.film_evaluation(tmp_path, out, _report(out, target=_two_targets, channels=GOAL_CHANNELS[:3]),
                             seeds=[1101], video=False)
    # A frame without its goal row: the declaration and the frames disagree.
    report = _report(out, target=_two_targets)
    path = out / report["seeds"][0]["trace"]["file"]
    trace = json.loads(path.read_text())
    del trace["frames"][7]["goal"]
    path.write_bytes(json.dumps(trace).encode())
    report["seeds"][0]["trace"]["sha256"] = _sha(path.read_bytes())
    with pytest.raises(film.FilmError, match="a frame carries no target"):
        film.film_evaluation(tmp_path, out, report, seeds=[1101], video=False)
    # A goal that is not a point is nobody's target.
    block = film.film_evaluation(
        tmp_path, out, _report(out, target=_two_targets, channels=GOAL_CHANNELS[:1]), seeds=[1101],
        video=False)
    assert block["seeds"][0]["target"] is None
    # ...unless the evaluation says this seed drew one: then an unmarked film would mislead.
    report = _report(out, target=_two_targets, channels=GOAL_CHANNELS[:1])
    report["seeds"][0]["drawn"]["goal"] = [{"name": "target", "kind": "point", "segments": []}]
    with pytest.raises(film.FilmError, match="seed 1101 drew a point goal and its trace carries none"):
        film.film_evaluation(tmp_path, out, report, seeds=[1101], video=False)


def test_a_base_that_is_not_drawn_is_a_reason(tmp_path, small) -> None:
    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    with pytest.raises(film.FilmError, match="c_torso, is not one of the solids drawn"):
        film.film_evaluation(tmp_path, out, _report(out, base="c_torso"), seeds=[1101], video=False)
    with pytest.raises(film.FilmError, match="c_floor, is not one of the solids drawn"):
        film.film_evaluation(tmp_path, out, _report(out, base="c_floor"), seeds=[1101], video=False)


def test_the_detail_takes_a_given_start_and_step(tmp_path, small) -> None:
    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    block = film.film_evaluation(tmp_path, out, _report(out), seeds=[1101], video=False,
                                 start=2.0, step=0.04)
    sheet = block["seeds"][0]["detail"]
    assert sheet["start_source"] == "given" and sheet["step_s"] == 0.04
    assert sheet["times_s"] == pytest.approx([2.0 + 0.04 * k for k in range(12)])


def test_an_episode_with_no_disturbance_is_detailed_from_its_middle(tmp_path, small) -> None:
    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    block = film.film_evaluation(tmp_path, out, _report(out, onset=None, seconds=8.0),
                                 seeds=[1101], video=False)
    sheet = block["seeds"][0]["detail"]
    assert sheet["start_source"] == "the middle of the episode" and sheet["start_s"] == 4.0


def test_an_episode_that_ended_early_is_detailed_to_its_end(tmp_path, small) -> None:
    """A fall at 1.5 s, a detail asked for from 5 s: the last twelve moments are shown."""

    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    block = film.film_evaluation(tmp_path, out, _report(out, seconds=1.5), seeds=[1101], video=False,
                                 start=5.0, step=0.04)
    sheet = block["seeds"][0]["detail"]
    assert sheet["requested_start_s"] == 5.0 and sheet["start_s"] == pytest.approx(1.5 - 11 * 0.04)
    assert sheet["frames"] == 12 and sheet["times_s"][-1] == 1.5

    # Shorter than the whole window: every solved frame once, and no more.
    block = film.film_evaluation(tmp_path, out, _report(out, seconds=0.1), seeds=[1101], video=False)
    sheet = block["seeds"][0]["detail"]
    assert sheet["start_s"] == 0.0 and sheet["times_s"] == [0.0]


def test_a_design_that_stays_put_is_seen_from_the_front(tmp_path, small) -> None:
    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    block = film.film_evaluation(tmp_path, out, _report(out, velocity=(0.5, 0.0)), seeds=[1101],
                                 video=False)
    sheet = block["seeds"][0]["detail"]
    assert sheet["azimuth_degrees"] == 0.0 and sheet["travel_mm"] == pytest.approx(2.0)


def test_the_floor_is_the_collision_plane_then_the_world_then_the_lowest_reach(tmp_path, small) -> None:
    _project(tmp_path / "world")
    out = tmp_path / "world" / "evaluations" / "one"
    block = film.film_evaluation(tmp_path / "world", out, _report(out, floor=None), seeds=[1101],
                                 video=False)
    assert block["seeds"][0]["floor_z_mm"] == 0.0
    assert block["seeds"][0]["floor_source"] == "top of the world geometry: c_floor"

    _project(tmp_path / "bare", world=False)
    out = tmp_path / "bare" / "evaluations" / "one"
    block = film.film_evaluation(tmp_path / "bare", out, _report(out, floor=None), seeds=[1101],
                                 video=False)
    # No world geometry declared: the slab is drawn, and its underside is the lowest reach.
    assert block["materials"]["environment_omitted"] == [] and "c_floor" in block["appearance"]
    assert block["seeds"][0]["floor_z_mm"] == -10.0
    assert "lowest point" in block["seeds"][0]["floor_source"]


def test_every_named_seed_is_filmed_and_a_rerun_leaves_no_stale_sheet(tmp_path, small) -> None:
    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    report = _report(out)
    block = film.film_evaluation(tmp_path, out, report, seeds=[1102, 1101], video=False)
    assert [row["seed"] for row in block["seeds"]] == [1102, 1101]
    assert sorted(p.name for p in out.glob("*.png")) == [
        "seed-1101-detail.png", "seed-1101-overview.png",
        "seed-1102-detail.png", "seed-1102-overview.png"]

    film.film_evaluation(tmp_path, out, report, seeds=[1102], video=False)
    assert sorted(p.name for p in out.glob("*.png")) == ["seed-1102-detail.png", "seed-1102-overview.png"]
    # The film stays out of the project's own history; the report does not.
    ignored = (out / ".gitignore").read_text().splitlines()
    assert {"seed-*-overview.png", "seed-*-detail.png", "seed-*-rollout.webm"} <= set(ignored)
    assert "evaluation.json" not in " ".join(line for line in ignored if not line.startswith("#"))


def test_the_trace_filmed_is_the_trace_measured(tmp_path, small) -> None:
    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    report = _report(out)
    _trace(out, 1101, velocity=(5.0, 0.0))      # the file changed after the evaluation
    with pytest.raises(film.FilmError, match="not the trace this evaluation measured"):
        film.film_evaluation(tmp_path, out, report, seeds=[1101], video=False)
    with pytest.raises(film.FilmError, match="seed 1199 is not in this evaluation"):
        film.film_evaluation(tmp_path, out, report, seeds=[1199], video=False)


@pytest.mark.parametrize("start, step", [(-1.0, None), (None, 0.0), (None, math.inf)])
def test_a_detail_window_that_is_no_time_is_refused(tmp_path, small, start, step) -> None:
    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    with pytest.raises(film.FilmError, match="detail"):
        film.film_evaluation(tmp_path, out, _report(out), seeds=[1101], video=False,
                             start=start, step=step)


def test_the_films_identity_covers_the_renderer_the_video_and_its_own_framing(tmp_path, monkeypatch) -> None:
    before = film.film_digest()
    assert re.fullmatch("[0-9a-f]{64}", before) and before != studio_video.studio_digest()
    for module in (film, studio_video, STUDIO):
        copy = tmp_path / Path(module.__file__).name
        copy.write_bytes(Path(module.__file__).read_bytes() + b"\n# changed\n")
        with monkeypatch.context() as patch:
            patch.setattr(module, "__file__", str(copy))
            assert film.film_digest() != before, copy.name
    assert film.film_digest() == before


def test_the_film_names_no_behaviour() -> None:
    """The detail's window is a disturbance or a time, never a gait or a shove by name."""

    assert not re.search(r"walk|gait|balanc|reach|feet|foot|quadruped|biped|shove",
                         _code(Path(film.__file__)), re.IGNORECASE)


# -- the video ---------------------------------------------------------------------

def _has_ffmpeg() -> bool:
    try:
        studio_video.ffmpeg()
    except ValueError:
        return False
    return True


needs_ffmpeg = pytest.mark.skipif(not _has_ffmpeg(), reason="FFmpeg is not available here")


@needs_ffmpeg
def test_the_first_filmed_seed_is_also_a_video_that_decodes_whole(tmp_path, small, monkeypatch) -> None:
    monkeypatch.setitem(studio_video.STUDIO, "size", 96)
    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    lines = []
    block = film.film_evaluation(tmp_path, out, _report(out, seconds=1.0), seeds=[1102, 1101],
                                 progress=lines.append)

    assert block["state"] == "ready"
    first, second = block["seeds"]
    assert second["video"] is None
    clip = first["video"]
    path = out / "seed-1102-rollout.webm"
    assert clip["file"] == path.name and clip["sha256"] == _sha(path.read_bytes())
    assert (clip["frames"], clip["fps"], clip["sim_seconds"]) == (11, 10, 1.0)
    assert clip["floor_z_mm"] == 0.0 and (clip["width"], clip["height"]) == (96, 96)
    decoded = subprocess.run([studio_video.ffmpeg(), "-v", "error", "-i", str(path), "-f", "framemd5", "-"],
                             capture_output=True, check=True).stdout
    assert len([row for row in decoded.splitlines() if row and not row.startswith(b"#")]) == 11
    assert not list(out.glob(".film-*")), "the scratch frames were left behind"
    assert [line.split()[2:5] for line in lines] == [
        ["seed", "1102", "sheets"], ["seed", "1101", "sheets"], ["seed", "1102", "video"]]


@needs_ffmpeg
def test_the_video_marks_the_target_and_keeps_it_in_its_window(tmp_path, small, monkeypatch) -> None:
    monkeypatch.setitem(studio_video.STUDIO, "size", 96)
    drawn = []
    encode = studio_video.encode

    def keeping(work, count):
        drawn.extend(_pixels(work / f"{index:04d}.png") for index in range(count))
        return encode(work, count)

    monkeypatch.setattr(studio_video, "encode", keeping)
    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    # The target stays 300 mm up the floor from a design that walks away along +X.
    report = _report(out, seconds=1.0, target=lambda t: (0.0, 300.0, 40.0))
    block = film.film_evaluation(tmp_path, out, report, seeds=[1101])

    clip = block["seeds"][0]["video"]
    assert block["state"] == "ready" and (clip["frames"], clip["marked_frames"]) == (11, 11)
    assert len(drawn) == 11
    for width, _height, data in drawn:
        frame = [tuple(data[3 * i:3 * i + 3]) for i in range(width * width)]
        assert len(_ring(frame, width)) >= 8

    # The same rollout with nowhere to go: no ring, and a window the design's own size.
    drawn.clear()
    block = film.film_evaluation(tmp_path, out, _report(out, seconds=1.0), seeds=[1101])
    assert block["seeds"][0]["video"]["marked_frames"] == 0
    for width, _height, data in drawn:
        assert not _ring([tuple(data[3 * i:3 * i + 3]) for i in range(width * width)], width)


def test_a_video_that_cannot_be_encoded_leaves_the_sheets_and_says_why(tmp_path, small, monkeypatch) -> None:
    def missing():
        raise ValueError("FFmpeg is required and is neither on PATH nor beside the interpreter")

    monkeypatch.setattr(studio_video, "ffmpeg", missing)
    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    block = film.film_evaluation(tmp_path, out, _report(out), seeds=[1101])

    assert block["state"] == "failed" and "FFmpeg is required" in block["error"]
    assert block["seeds"][0]["video"] is None
    assert (out / block["seeds"][0]["overview"]["file"]).is_file()
    assert (out / block["seeds"][0]["detail"]["file"]).is_file()
    assert not list(out.glob("*.webm"))


def test_the_encoder_beside_the_interpreter_is_found_without_a_path(tmp_path, monkeypatch) -> None:
    """``./cadex`` runs the environment's Python with no environment on PATH."""

    beside = tmp_path / "bin" / "ffmpeg"
    beside.parent.mkdir()
    beside.write_text("#!/bin/sh\n")
    beside.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.setattr(studio_video, "sys", types.SimpleNamespace(executable=str(tmp_path / "bin" / "python")))
    assert studio_video.ffmpeg() == str(beside)
    beside.unlink()
    with pytest.raises(ValueError, match="FFmpeg is required"):
        studio_video.ffmpeg()


# -- the report carries it ---------------------------------------------------------

def test_the_report_is_rewritten_with_its_film_and_the_measurement_untouched(tmp_path, small) -> None:
    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    report = _report(out)
    filmed = add_film(tmp_path, out, report, choice="auto", video=False)

    assert {key: filmed[key] for key in report} == report
    assert filmed["film"]["state"] == "ready" and [r["seed"] for r in filmed["film"]["seeds"]] == [1101]
    assert json.loads((out / REPORT_NAME).read_text()) == filmed
    assert any(line.startswith("  film: seed(s) 1101") for line in human_lines(filmed))


def test_no_seed_to_film_is_recorded_as_skipped(tmp_path, small) -> None:
    _project(tmp_path)
    out = tmp_path / "evaluations" / "one"
    report = _report(out)
    add_film(tmp_path, out, report, choice="all", video=False)
    filmed = add_film(tmp_path, out, report, choice="none")
    assert filmed["film"] == {"schema": film.FILM_SCHEMA, "state": "skipped", "error": None, "seeds": []}
    assert not list(out.glob("*.png"))


def test_a_film_that_cannot_be_drawn_leaves_a_complete_report_that_says_so(tmp_path, small) -> None:
    out = tmp_path / "evaluations" / "one"            # no retained attempt at all
    report = _report(out)
    filmed = add_film(tmp_path, out, report, choice="auto")
    assert filmed["film"]["state"] == "failed" and filmed["film"]["seeds"] == []
    assert "cannot read the retained accepted attempt" in filmed["film"]["error"]
    assert json.loads((out / REPORT_NAME).read_text())["seeds"] == report["seeds"]
    assert any(line.startswith("  film: not drawn") for line in human_lines(filmed))


def test_film_only_draws_from_the_evaluation_of_this_revision_and_policy(tmp_path) -> None:
    out = tmp_path / "evaluations" / "one"
    inputs = {"accepted_revision": REVISION, "policy_sha256": "p" * 64}
    with pytest.raises(EvaluateRefused, match="no evaluation in"):
        read_report(out, inputs)
    report = _report(out)
    (out / REPORT_NAME).write_text(json.dumps(report))
    assert read_report(out, inputs) == report
    with pytest.raises(EvaluateRefused, match="another revision or policy"):
        read_report(out, {**inputs, "policy_sha256": "q" * 64})
    with pytest.raises(EvaluateRefused, match="another revision or policy"):
        read_report(out, {**inputs, "accepted_revision": "b" * 64})
    (out / REPORT_NAME).write_text(json.dumps({"schema": "something-else"}))
    with pytest.raises(EvaluateRefused, match="not an evaluation report"):
        read_report(out, inputs)
