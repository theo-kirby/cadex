# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""An evaluation's film: a filmstrip and a rollout video of its seeds (ADR-459).

``cadex evaluate`` measures a policy on every frozen seed and keeps each
seed's trace. This module draws what those traces did, on the dark prototype
floor (ADR-444) with the engine's studio renderer, for a person or a model
to look at:

- a **filmstrip** per filmed seed, two sheets of twelve frames. The
  *overview* is evenly spaced from the first solved pose to the last, in the
  fixed three-quarter hero view, framed on the whole path. The *detail* is
  consecutive moments a declared step apart, side-on to the direction the
  evaluation rig's base travelled, the window following that base. A
  mechanism with no floating base has a fixed one, and its window is fixed.
  Every frame carries its simulation time and, where the trace says where
  the episode was asked to go, a ring at that point (ADR-463). Nothing else;
- a **video** of the first filmed seed, drawn as a run's studio video is
  (:mod:`video`), ten frames a second.

The solids are the accepted attempt's own retained tessellation, moved
rigidly to each frame's recorded pose. Nothing is rebuilt and no engine is
opened. Nothing here knows what the behaviour is: the detail starts where
the seed's first drawn disturbance begins, or at the middle of an episode
that has none, unless the caller says otherwise, and the ring is drawn for
any trace whose frames carry a point goal (ADR-462), whatever the task.
"""

from __future__ import annotations

from array import array
import bisect
import hashlib
import json
import math
from pathlib import Path
import tempfile
import time
from typing import Any, Mapping, Sequence

from . import video as studio_video
from .smoke import retained_attempt
from .studio import STUDIO as studio_render

FILM_SCHEMA = "cadex-evaluation-film-v1"
TRACE_SCHEMA = "cadex-assembly-simulation-trace-v1"
#: One filmstrip frame's edge, in pixels, and how a sheet lays twelve out.
FRAME = 256
COLUMNS, ROWS = 4, 3
STRIP = COLUMNS * ROWS
GUTTER = 4
#: The detail view looks from this far above the floor: low enough to be a
#: side view, high enough that the mat's grid is seen under the feet.
DETAIL_ELEVATION_DEGREES = 12.0
#: The step between detail frames when the caller names none.
DETAIL_STEP_S = 0.2
#: The margin round the framed extent, as a fraction of it, on each side.
PAD = 0.10
#: A design that ends up nearer its start than this fraction of its own size
#: has no direction of travel, and its detail is the front view.
TRAVEL_FRACTION = 0.05
#: The target marker (ADR-463): a ring centred on the point a trace's point
#: goal names, its radius and its band as shares of the frame's edge. It is
#: drawn over the solids, so a tip that arrives does not hide it, and it is
#: hollow, so it does not hide the tip. The colour is the dashboard's
#: ``--info``, which no appearance role uses; the rim round the band is the
#: scene's background, so the ring reads against a light part as well.
MARKER_RADIUS = 9 / 256
MARKER_BAND = 2.5 / 256
MARKER_RIM_PX = 1.0
MARKER_COLOUR = (111, 240, 240)
#: Declared bound on drawing one seed's two sheets.
STRIP_SECONDS = 300
OVERVIEW_NAME = "seed-{seed}-overview.png"
DETAIL_NAME = "seed-{seed}-detail.png"
VIDEO_NAME = "seed-{seed}-rollout.webm"
#: What a re-run removes before it draws.
FILM_GLOBS = ("seed-*-overview.png", "seed-*-detail.png", "seed-*-rollout.webm")
#: Every video drawn beside the report, the evaluation's and any other a
#: pass presents (ADR-571): drawn again, so kept out of the history.
VIDEOS = "*.webm"
#: Written beside the film. A project is a git repository that commits what
#: a command changed (ADR-194); the report belongs in its history and the
#: film, which the traces can draw again, does not.
IGNORE_NAME = ".gitignore"
#: The two heroes a passed evaluation presents (ADR-570), drawn again by
#: ``--film-only`` like the film, so kept out of the history like it.
HERO_NAMES = ("hero.png", "print-bed.png")
IGNORE = ("# Written by cadex evaluate (ADR-459, ADR-570, ADR-571). The film, the heroes and the\n"
          "# videos are drawn again with --film-only; evaluation.json is the record.\n"
          + "".join(pattern + "\n" for pattern in FILM_GLOBS + HERO_NAMES + (VIDEOS,)))


class FilmError(RuntimeError):
    """The film could not be drawn; the measured evaluation stands without it."""


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise FilmError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def choose_seeds(report: Mapping[str, Any], choice: str) -> list[int]:
    """The seeds to film: ``auto``, ``all``, ``none`` or a comma-separated list.

    ``auto`` is the first seed that failed, the one a diagnosis starts from,
    or the first seed of an evaluation that passed.
    """

    rows = list(report.get("seeds") or [])
    every = [int(row["seed"]) for row in rows]
    choice = str(choice or "auto").strip().lower()
    if choice == "none" or not every:
        return []
    if choice == "all":
        return every
    if choice == "auto":
        failed = [int(row["seed"]) for row in rows if not row.get("pass")]
        return (failed or every)[:1]
    try:
        wanted = [int(part) for part in choice.split(",") if part.strip()]
    except ValueError as exc:
        raise FilmError(f"--film takes auto, all, none or seed numbers, not {choice!r}.") from exc
    unknown = [seed for seed in wanted if seed not in every]
    _require(wanted and not unknown,
             "--film names seed(s) this evaluation did not run: "
             + ", ".join(map(str, unknown)) + "; it ran " + ", ".join(map(str, every)) + ".")
    return list(dict.fromkeys(wanted))


# -- the solids, as the accepted attempt retained them -----------------------

def retained_solids(root: Path, model_output: str) -> tuple[dict[str, array], dict[str, str], set[str]]:
    """``(flats, sources, world)`` for the components of ``model_output``.

    ``flats`` is each component's triangles in its own frame, nine
    coordinates a triangle, read from the tessellation the accepted attempt
    retained for its source solid; ``sources`` is component -> source
    output; ``world`` names the components the assembly calls world
    geometry (a declared floor). Validated and bounded by the engine's own
    snapshot reader, the one ``cadex render`` draws from.
    """

    try:
        state, staging, result = retained_attempt(root)
    except Exception as exc:  # noqa: BLE001 - one reason, whatever was unreadable
        raise FilmError(f"cannot read the retained accepted attempt: {exc}") from exc
    items = {str(item["name"]): item for item in result["outputs"]}
    model = items.get(model_output) or {}
    data = model.get("assembly_data") or {}
    components = [str(name) for name in data.get("component_outputs") or []]
    _require(components, f"model {model_output} names no components to draw")
    revision = str(state["accepted_revision"])
    display: dict[str, Any] = {}
    sources: dict[str, str] = {}
    for name in components:
        source = str((items.get(name) or {}).get("source_output") or "")
        tess = (items.get(source) or {}).get("display") or {}
        _require(source and source != name and tess.get("artifact_kind") == "tessellation",
                 f"the accepted attempt retained no tessellation for {name}")
        paths = {}
        for key in ("artifact_path", "sidecar_path"):
            path = (staging / str(tess.get(key) or "")).resolve()
            _require(path.is_relative_to(staging) and path.is_file(),
                     f"missing or escaping retained tessellation for {name}")
            paths[key] = str(path)
        display[source] = {"tessellation": paths}
        display[name] = {"source_output": source, "placement": list(studio_render.IDENTITY)}
        sources[name] = source
    try:
        triangles, summary = studio_render.snapshot(
            {"ok": True, "revision": revision, "accepted_revision": revision, "display": display})
    except studio_render.StudioError as exc:
        raise FilmError(str(exc)) from exc
    flats = {}
    for name, item in summary["objects"].items():
        flat = array("d")
        for _colour, corners in triangles[item["first"]:item["first"] + item["triangles"]]:
            for corner in corners:
                flat.extend(corner)
        flats[name] = flat
    assembly = items.get(str(data.get("assembly_output") or "")) or {}
    world = {str(row.get("component") or "") for row in assembly.get("world_geometry") or []
             if isinstance(row, Mapping) and row.get("status") == "world geometry"}
    return flats, sources, world & set(flats)


def materials(sources: Mapping[str, str], drawn: Sequence[str], revision: str,
              inventory: Mapping[str, Any] | None) -> tuple[dict[str, tuple], dict[str, Any]]:
    """``(looks, source)``: each drawn component's appearance role and colour.

    By the rules a render draws with: the role the script declared, else
    mechanism for a catalogued part and shell for a printed one, and the
    finish its catalog family gives it (metal hardware, a board, a purchased
    satin: ADR-603). The inventory block carries all three, read from the
    accepted attempt. Without one at this revision every part is drawn as
    shell, and the film says so.
    """

    summary = {"objects": {name: {"source": sources[name], "color": studio_render.ROLE_COLORS["shell"]}
                           for name in drawn}}
    usable = (isinstance(inventory, Mapping) and inventory.get("available", True)
              and inventory.get("revision") == revision and "uncatalogued_sources" in inventory)
    if not usable:
        shell = studio_render.ROLE_COLORS["shell"]
        return ({name: ("shell", shell) for name in drawn},
                {"source": "no inventory at this revision: every part drawn as shell",
                 "declared": False})
    # ``inspect scope=inventory`` carries a declared role on its component's
    # row; the build reply's block carries the same as one map (ADR-413).
    block = dict(inventory)
    block.setdefault("appearance", {
        str(row.get("component") or ""): str(row["appearance"])
        for row in inventory.get("components") or []
        if isinstance(row, Mapping) and row.get("appearance")})
    try:
        _environment, purchased = studio_render.classify(summary, None, block)
        appearance, palette = studio_render.declared(block)
        looks = studio_render.materials(summary, purchased=purchased,
                                        appearance={k: v for k, v in appearance.items() if k in drawn},
                                        palette=palette, catalog=studio_render.catalogued(summary, block))
    except studio_render.StudioError as exc:
        raise FilmError(str(exc)) from exc
    return looks, {"source": "the accepted assembly's inventory", "declared": True}


# -- one seed's trace ---------------------------------------------------------

def read_trace(path: Path, expected_sha256: str, names: Sequence[str]
               ) -> tuple[list[dict], list[float], dict[str, Any] | None]:
    """The solved frames of one seed's trace, their times and its target, checked.

    The file filmed is the file measured: its digest is the one the
    evaluation recorded for the seed. The target is ``None`` for a trace
    that carries no point goal (:func:`target_track`).
    """

    _require(path.is_file() and not path.is_symlink(), f"{path.name} is not in the evaluation")
    data = path.read_bytes()
    _require(hashlib.sha256(data).hexdigest() == expected_sha256,
             f"{path.name} is not the trace this evaluation measured")
    trace = json.loads(data)
    _require(trace.get("schema") == TRACE_SCHEMA, f"{path.name}: unsupported trace")
    frames = [frame for frame in trace.get("frames") or [] if frame.get("frame_kind") == "solver_output"]
    times = [frame.get("nominal_time_s") for frame in frames]
    _require(len(frames) >= 2 and all(type(t) in (int, float) and math.isfinite(t) for t in times)
             and times[0] == 0 and 0 < times[-1] <= 60
             and all(b > a for a, b in zip(times, times[1:])),
             f"{path.name}: missing or invalid solved frames")
    for frame in frames:
        poses = frame.get("component_placements") or {}
        _require(all(name in poses for name in names), f"{path.name}: a frame places no {names[0]}")
        for name in names:
            try:
                studio_video.placed((), poses[name])
            except (ValueError, KeyError, TypeError) as exc:
                raise FilmError(f"{path.name}: {exc}") from exc
    times = [float(t) for t in times]
    return frames, times, target_track(trace, frames, times, path.name)


def target_track(trace: Mapping[str, Any], frames: Sequence[Mapping[str, Any]],
                 times: Sequence[float], name: str) -> dict[str, Any] | None:
    """Where each solved frame was asked to go, or ``None`` for a trace that says nothing.

    A trace whose task states a point goal names its three channels once
    (``goal_channels``) and carries the point in force in every frame's
    ``goal`` row, in millimetres in the world (ADR-462), or in the frame of
    the component its rows name as ``frame`` (ADR-592), which is placed into
    the world with that component's pose in the same frame. ``points`` is
    that point per solved frame, in the world; ``positions`` is each place
    it held, from when.
    """

    rows = trace.get("goal_channels")
    rows = rows if isinstance(rows, list) else []
    places = [at for at, row in enumerate(rows) if isinstance(row, Mapping) and row.get("kind") == "point"]
    if not places:
        return None
    goal = str(rows[places[0]].get("goal") or "")
    places = [at for at in places if rows[at].get("goal") == goal]
    _require(len(places) == 3 and all(rows[at].get("unit") == "mm" for at in places),
             f"{name}: the point goal {goal!r} is not three channels in millimetres")
    carrier = rows[places[0]].get("frame")
    points = []
    for frame in frames:
        row = frame.get("goal")
        _require(isinstance(row, list) and len(row) == len(rows)
                 and all(type(row[at]) in (int, float) and math.isfinite(row[at]) for at in places),
                 f"{name}: a frame carries no {goal}")
        point = tuple(float(row[at]) for at in places)
        if carrier:
            pose = (frame.get("component_placements") or {}).get(str(carrier))
            _require(isinstance(pose, Mapping), f"{name}: a frame places no {carrier}")
            point = _carried(pose, point)
        points.append(point)
    positions = [{"from_s": times[at], "point_mm": list(point)} for at, point in enumerate(points)
                 if at == 0 or point != points[at - 1]]
    return {"goal": goal, "channels": [str(rows[at].get("channel") or "") for at in places],
            "unit": "mm", "points": points, "positions": positions}


def _carried(pose: Mapping[str, Any], local: Sequence[float]) -> tuple[float, float, float]:
    """A point fixed in a component, in the world at that component's pose."""

    x, y, z, w = (float(v) for v in pose["rotation_xyzw"])
    n = math.sqrt(x * x + y * y + z * z + w * w)
    x, y, z, w = x / n, y / n, z / n, w / n
    rows = ((1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
            (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
            (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)))
    origin = [float(v) for v in pose["position_mm"]]
    return tuple(origin[i] + sum(rows[i][j] * float(local[j]) for j in range(3)) for i in range(3))


def read_terrain(path: Path) -> dict[str, Any] | None:
    """The course a trace says its episode stood on, checked as the dashboard
    checks it, or ``None`` on flat ground. The trace was already held to its
    digest by :func:`read_trace`."""

    from .review_server import terrain_block

    return terrain_block(json.loads(path.read_bytes()).get("terrain"))


#: The dashboard's ground sampler (``review_scene.js``'s ``TERRAIN``): its
#: finest spacing and most samples, a wall's half-width, the most breaks a
#: side, the margin past a box course, the blend to the mat, the reach a box
#: corner widens the fine span by, and the run-out's spacing (ADR-743, ADR-745).
SURFACE = {"pitch_mm": 25.0, "samples": 120000, "wall_mm": 0.5, "breaks": 512, "margin_mm": 500.0,
           "blend_mm": 1500.0, "reach_mm": 10000.0, "far_mm": 2500.0}


def _round(value: float) -> float:
    # JavaScript's Math.round: halves go up.
    return math.floor(value + 0.5)


def _box_axes(box: Mapping[str, Any]) -> list[list[float]]:
    """A box's axes in the world, the columns of its rotation."""

    qx, qy, qz, qw = box["rotation_xyzw"]
    return [[1 - 2*(qy*qy + qz*qz), 2*(qx*qy + qz*qw), 2*(qx*qz - qy*qw)],
            [2*(qx*qy - qz*qw), 1 - 2*(qx*qx + qz*qz), 2*(qy*qz + qx*qw)],
            [2*(qx*qz + qy*qw), 2*(qy*qz - qx*qw), 1 - 2*(qx*qx + qy*qy)]]


def _box_top(box: Mapping[str, Any], axes, x: float, y: float) -> float:
    """The highest point of a box on the vertical at (x, y), or -inf."""

    (cx, cy, cz), half = box["centre_mm"], box["half_mm"]
    dx, dy = x - cx, y - cy
    lo, hi = -math.inf, math.inf
    for i in range(3):
        a = axes[i]
        o, d, h = a[0]*dx + a[1]*dy - a[2]*cz, a[2], half[i]
        if abs(d) < 1e-12:
            if abs(o) > h:
                return -math.inf
            continue
        p, q = (-h - o) / d, (h - o) / d
        lo, hi = max(lo, min(p, q)), min(hi, max(p, q))
    return hi if lo <= hi else -math.inf


def _sample_axis(lo: float, hi: float, pitch: float, breaks: Sequence[float]) -> list[float]:
    """Every ``pitch`` across [lo, hi], and each break on both sides of it."""

    n = max(1, math.ceil((hi - lo) / pitch))
    at = [lo + (hi - lo) * k / n for k in range(n + 1)]
    for v in breaks:
        if lo < v < hi:
            at += [v - SURFACE["wall_mm"], v + SURFACE["wall_mm"]]
    at.sort()
    return [v for i, v in enumerate(at) if i == 0 or v - at[i - 1] > .01]


def terrain_surface(block: Mapping[str, Any]) -> tuple[list[float], list[float], Any]:
    """``(xs, ys, height)``: the course as the dashboard draws it, one ground
    (``review_scene.js``'s ``sampleSurface``, ADR-743): its sample axes and
    the height (mm) at any of their crossings. A port, held to the dashboard's
    own by ``test_dashboard_ground.py``."""

    (x0, x1), (y0, y1) = block["x_range_mm"], block["y_range_mm"]
    bx: list[float] = []
    by: list[float] = []
    far = None
    if block["kind"] == "boxes":
        boxes = [(box, _box_axes(box)) for box in block.get("boxes") or ()]
        domes = list(block.get("domes") or ())
        plane = block.get("plane_z_mm")
        plane = block["lowest_mm"] if plane is None else plane
        # Each box's plan footprint, so a point far from it never asks it.
        reach = []
        for box, axes in boxes:
            spread = [sum(abs(axes[i][k]) * box["half_mm"][i] for i in range(3)) for k in range(2)]
            reach.append((box["centre_mm"][0] - spread[0] - 1e-6, box["centre_mm"][0] + spread[0] + 1e-6,
                          box["centre_mm"][1] - spread[1] - 1e-6, box["centre_mm"][1] + spread[1] + 1e-6))

        def exact(x: float, y: float, skip: int = -1) -> float:
            z = plane
            for k, (box, axes) in enumerate(boxes):
                r = reach[k]
                if k != skip and r[0] <= x <= r[1] and r[2] <= y <= r[3]:
                    z = max(z, _box_top(box, axes, x, y))
            for dome in domes:
                (cx, cy, cz), radius = dome["centre_mm"], dome["radius_mm"]
                d2 = radius * radius - (x - cx) ** 2 - (y - cy) ** 2
                if d2 >= 0:
                    z = max(z, cz + math.sqrt(d2))
            return z

        ex0, ex1, ey0, ey1 = x0, x1, y0, y1
        near = lambda v, lo, hi: lo - SURFACE["reach_mm"] <= v <= hi + SURFACE["reach_mm"]
        ox0, ox1, oy0, oy1 = x0, x1, y0, y1
        for box, axes in boxes:
            for sx in (-1, 1):
                for sy in (-1, 1):
                    for sz in (-1, 1):
                        local = (sx * box["half_mm"][0], sy * box["half_mm"][1], sz * box["half_mm"][2])
                        x = box["centre_mm"][0] + sum(axes[i][0] * local[i] for i in range(3))
                        y = box["centre_mm"][1] + sum(axes[i][1] * local[i] for i in range(3))
                        bx.append(x); by.append(y)
                        ox0, ox1, oy0, oy1 = min(ox0, x), max(ox1, x), min(oy0, y), max(oy1, y)
                        if near(x, ex0, ex1):
                            x0, x1 = min(x0, x), max(x1, x)
                        if near(y, ey0, ey1):
                            y0, y1 = min(y0, y), max(y1, y)
        # A box turned about x or y meets the ground under it in a crease: a break too.
        for k, (box, axes) in enumerate(boxes):
            if all(abs(abs(a[0]) + abs(a[1]) + abs(a[2]) - 1) < 1e-9 for a in axes):
                continue
            c = box["centre_mm"]
            z0 = exact(c[0], c[1], k)
            for i, a in enumerate(axes):
                for sign in (-1, 1):
                    h, dz = sign * box["half_mm"][i], a[2] * (z0 - c[2])
                    if abs(a[2]) < 1e-9:
                        continue
                    if abs(a[1]) < 1e-9 and abs(a[0]) > 1e-9:
                        bx.append(c[0] + (h - dz) / a[0])
                    if abs(a[0]) < 1e-9 and abs(a[1]) > 1e-9:
                        by.append(c[1] + (h - dz) / a[1])
        for dome in domes:
            (cx, cy, cz), radius = dome["centre_mm"], dome["radius_mm"]
            r = math.sqrt(max(0.0, radius ** 2 - (plane - cz) ** 2))
            x0, x1, y0, y1 = min(x0, cx - r), max(x1, cx + r), min(y0, cy - r), max(y1, cy + r)
        ox0, ox1, oy0, oy1 = min(ox0, x0), max(ox1, x1), min(oy0, y0), max(oy1, y1)
        bx = list(dict.fromkeys(_round(v * 100) / 100 for v in bx))
        by = list(dict.fromkeys(_round(v * 100) / 100 for v in by))
        if len(bx) > SURFACE["breaks"]:
            bx = []
        if len(by) > SURFACE["breaks"]:
            by = []
        blend = SURFACE["blend_mm"]
        runout = ox0 < x0 - blend or ox1 > x1 + blend or oy0 < y0 - blend or oy1 > y1 + blend

        def height(x: float, y: float) -> float:
            cx, cy = min(ox1, max(ox0, x)), min(oy1, max(oy0, y))
            if not runout or (cx == x and cy == y):
                return exact(x, y)
            edge, t = exact(cx, cy), min(1.0, math.hypot(x - cx, y - cy) / blend)
            return edge + (plane - edge) * t * t * (3 - 2 * t)

        run = SURFACE["margin_mm"]
        if runout:
            far = (ox0, ox1, oy0, oy1)
    else:
        grid = block["grid"]
        rows, columns, heights = grid["rows"], grid["columns"], grid["heights_mm"]
        (gx0, gx1), (gy0, gy1), mat = block["x_range_mm"], block["y_range_mm"], block["lowest_mm"] - 50
        bx = [gx0 + (gx1 - gx0) * k / (columns - 1) for k in range(columns)]
        by = [gy0 + (gy1 - gy0) * r / (rows - 1) for r in range(rows)]

        def height(x: float, y: float) -> float:
            cx, cy = min(gx1, max(gx0, x)), min(gy1, max(gy0, y))
            k = int(_round((cx - gx0) / (gx1 - gx0) * (columns - 1)))
            r = int(_round((cy - gy0) / (gy1 - gy0) * (rows - 1)))
            edge, t = heights[r * columns + k], min(1.0, math.hypot(x - cx, y - cy) / SURFACE["blend_mm"])
            return edge + (mat - edge) * t * t * (3 - 2 * t)

        run = SURFACE["blend_mm"]
    x0, x1, y0, y1 = x0 - run, x1 + run, y0 - run, y1 + run
    pitch = max(SURFACE["pitch_mm"], math.sqrt((x1 - x0) * (y1 - y0) / SURFACE["samples"]))

    def outer(lo: float, hi: float, a, b, breaks) -> list[float]:
        if far is None:
            return _sample_axis(lo, hi, pitch, breaks)
        blend, spacing = SURFACE["blend_mm"], SURFACE["far_mm"]
        return sorted(set(_sample_axis(min(lo, a) - blend, lo, spacing, breaks)
                          + _sample_axis(lo, hi, pitch, breaks)
                          + _sample_axis(hi, max(hi, b) + blend, spacing, breaks)))

    def own(a: list[float], lo: float, hi: float, grid: list[float]) -> list[float]:
        return [v for v in a if v < lo] + grid + [v for v in a if v > hi]

    if block["kind"] == "boxes":
        xs = outer(x0, x1, far and far[0], far and far[1], bx)
        ys = outer(y0, y1, far and far[2], far and far[3], by)
    else:
        xs = own(_sample_axis(x0, x1, pitch, []), bx[0], bx[-1], bx)
        ys = own(_sample_axis(y0, y1, pitch, []), by[0], by[-1], by)
    return xs, ys, height


class Ground:
    """A course drawn as one ground (orun8 G1, ADR-746): the dashboard's
    surface (:func:`terrain_surface`), split on its own sample lines into
    tiles prepared on demand and painted with the mat (``GROUND``). A view
    draws the tiles under its window and inside the mat's fade, at a stride
    that keeps a cell about a pixel tall: what the dashboard draws, at the
    detail the frame can show."""

    #: Cells a tile spans along each axis, and the most tiles kept prepared.
    TILE = 48
    KEPT = 512

    def __init__(self, block: Mapping[str, Any]) -> None:
        self.xs, self.ys, self._height = terrain_surface(block)
        self.low, self.high = float(block["lowest_mm"]), float(block["highest_mm"])
        plane = block.get("plane_z_mm")
        self.low = min(self.low, float(plane) if plane is not None else self.low - 50.0)
        self._z: dict[tuple[int, int], float] = {}
        self._tiles: dict[tuple, list] = {}
        self._axes: dict[int, tuple[list[int], list[int]]] = {}

    def z(self, k: int, r: int) -> float:
        """The height at the crossing of sample columns ``k`` and row ``r``."""

        key = (k, r)
        if key not in self._z:
            self._z[key] = self._height(self.xs[k], self.ys[r])
        return self._z[key]

    def at(self, x: float, y: float) -> float | None:
        """The drawn height at (x, y), read off the surface's own triangles
        (each cell split on its (0,0)-(1,1) diagonal), or ``None`` off it:
        ``groundAt`` in ``review_scene.js``."""

        xs, ys = self.xs, self.ys
        if not (xs[0] <= x <= xs[-1] and ys[0] <= y <= ys[-1]):
            return None
        k = min(len(xs) - 2, bisect.bisect_right(xs, x) - 1)
        r = min(len(ys) - 2, bisect.bisect_right(ys, y) - 1)
        u, v = (x - xs[k]) / (xs[k + 1] - xs[k]), (y - ys[r]) / (ys[r + 1] - ys[r])
        z00, z10, z01, z11 = self.z(k, r), self.z(k + 1, r), self.z(k, r + 1), self.z(k + 1, r + 1)
        return z00 + u*(z10 - z00) + v*(z11 - z10) if u >= v else z00 + v*(z01 - z00) + u*(z11 - z01)

    def _strided(self, stride: int) -> tuple[list[int], list[int]]:
        if stride not in self._axes:
            pick = lambda n: sorted(set(range(0, n, stride)) | {n - 1})
            self._axes[stride] = (pick(len(self.xs)), pick(len(self.ys)))
        return self._axes[stride]

    def _tile(self, stride: int, i: int, j: int) -> list:
        key = (stride, i, j)
        if key in self._tiles:
            self._tiles[key] = self._tiles.pop(key)
            return self._tiles[key]
        kx, ky = self._strided(stride)
        # A ring of one cell round the tile is prepared with it and dropped,
        # so its normals are smoothed across the tile's edge as across any other.
        c0, c1 = i * self.TILE, min(len(kx) - 1, (i + 1) * self.TILE)
        r0, r1 = j * self.TILE, min(len(ky) - 1, (j + 1) * self.TILE)
        cells = [(c, r) for r in range(r0, r1) for c in range(c0, c1)]
        cells += [(c, r) for r in range(max(0, r0 - 1), min(len(ky) - 1, r1 + 1))
                  for c in range(max(0, c0 - 1), min(len(kx) - 1, c1 + 1))
                  if not (c0 <= c < c1 and r0 <= r < r1)]

        def corner(c: int, r: int) -> tuple[float, float, float]:
            return (self.xs[kx[c]], self.ys[ky[r]], self.z(kx[c], ky[r]))

        triangles = []
        for c, r in cells:
            p00, p10, p01, p11 = corner(c, r), corner(c + 1, r), corner(c, r + 1), corner(c + 1, r + 1)
            triangles += [(p00, p10, p11), (p00, p11, p01)]
        inner = 2 * (c1 - c0) * (r1 - r0)
        tile = studio_render._prepare([(studio_render.GROUND, triangles)])[:inner]
        self._tiles[key] = tile
        while len(self._tiles) > self.KEPT:
            self._tiles.pop(next(iter(self._tiles)))
        return tile

    def visible(self, basis, bounds, size: int) -> list:
        """The prepared tiles a view of ``bounds`` along ``basis`` can show."""

        (rx, ry, rz), (ux, uy, uz), (tx, ty, tz) = basis
        lo, hi = bounds
        extent = max(hi[0] - lo[0], hi[1] - lo[1])
        cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
        far = studio_render.FLOOR_FADE[1] * extent
        if tz > 0.05:
            def at(sx: float, sy: float, z: float) -> tuple[float, float]:
                along = (z - sx*rz - sy*uz) / tz
                return sx*rx + sy*ux + along*tx, sx*ry + sy*uy + along*ty
            plan = [at(sx, sy, z) for sx in (lo[0], hi[0]) for sy in (lo[1], hi[1]) for z in (self.low, self.high)]
            mx, my = at(cx, cy, self.low)
            x0 = max(min(p[0] for p in plan), mx - far); x1 = min(max(p[0] for p in plan), mx + far)
            y0 = max(min(p[1] for p in plan), my - far); y1 = min(max(p[1] for p in plan), my + far)
        else:
            mx, my = cx*rx + cy*ux, cx*ry + cy*uy
            x0, x1, y0, y1 = mx - far, mx + far, my - far, my + far
        if x1 < self.xs[0] or x0 > self.xs[-1] or y1 < self.ys[0] or y0 > self.ys[-1]:
            return []
        # A cell about a pixel tall where the view foreshortens the ground most.
        stride = 1
        while stride < 64 and 2 * stride * SURFACE["pitch_mm"] * max(tz, 0.1) <= extent / size:
            stride *= 2
        kx, ky = self._strided(stride)
        xs, ys = [self.xs[k] for k in kx], [self.ys[r] for r in ky]
        c0 = max(0, bisect.bisect_right(xs, x0) - 1) // self.TILE
        c1 = min(len(xs) - 2, bisect.bisect_left(xs, x1)) // self.TILE
        r0 = max(0, bisect.bisect_right(ys, y0) - 1) // self.TILE
        r1 = min(len(ys) - 2, bisect.bisect_left(ys, y1)) // self.TILE
        return [tri for j in range(r0, r1 + 1) for i in range(c0, c1 + 1) for tri in self._tile(stride, i, j)]


def terrain_floor(block: Mapping[str, Any] | None) -> float | None:
    """Where the mat lies under a course: a box course's plane, or under a
    heightfield's base, which has no ground beyond it."""

    if block is None:
        return None
    plane = block.get("plane_z_mm")
    return float(plane) if plane is not None else float(block["lowest_mm"]) - 50.0


class _Stage:
    """The drawn solids, prepared once, and the measures every shot needs."""

    def __init__(self, meshes: Mapping[str, list], looks: Mapping[str, tuple],
                 world_flats: Mapping[str, array]) -> None:
        #: The course under the solids (ADR-734), one ground (:class:`Ground`)
        #: drawn in every shot and framing none: set per seed, from its trace.
        self.ground: Ground | None = None
        self.names = [name for name in meshes if name in looks]
        _require(self.names, "nothing to draw once world geometry is left out")
        self.local = {name: studio_render._prepare(
            [(studio_render.material(looks[name], meshes[name]), meshes[name])])
            for name in self.names}
        self.corners = {}
        for name in self.names:
            points = [p for tri in meshes[name] for p in tri]
            lo = [min(p[j] for p in points) for j in range(3)]
            hi = [max(p[j] for p in points) for j in range(3)]
            self.corners[name] = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                                  for z in (lo[2], hi[2])]
        self.world = dict(world_flats)

    def centre(self, poses: Mapping[str, Any], base: str | None) -> tuple[float, float, float]:
        """Where ``base`` is at ``poses``: the middle of its own bounds. With
        no base, the middle of the whole design's."""

        if base is None:
            box = self.box(poses)
            return tuple((min(p[j] for p in box) + max(p[j] for p in box)) / 2 for j in range(3))
        ((a, b, c), (d, e, f), (g, h, i)), (px, py, pz) = studio_video._rows(poses[base])
        x, y, z = (sum(p[j] for p in self.corners[base]) / 8 for j in range(3))
        return a*x+b*y+c*z+px, d*x+e*y+f*z+py, g*x+h*y+i*z+pz

    def box(self, poses: Mapping[str, Any]) -> list[tuple[float, float, float]]:
        """Every component's bounding-box corner at ``poses``: a conservative hull."""

        out = []
        for name in self.names:
            ((a, b, c), (d, e, f), (g, h, i)), (px, py, pz) = studio_video._rows(poses[name])
            out.extend((a*x+b*y+c*z+px, d*x+e*y+f*z+py, g*x+h*y+i*z+pz)
                       for x, y, z in self.corners[name])
        return out

    def floor(self, frames: Sequence[Mapping[str, Any]], plane: Any = None) -> tuple[float, str]:
        """The floor's height: the model's collision plane, the one the
        evaluation measured against; else the world geometry's top face;
        else the lowest reach."""

        if isinstance(plane, (int, float)) and math.isfinite(plane):
            return float(plane), "the model's collision plane"
        if self.world:
            top = -math.inf
            for name, flat in self.world.items():
                (_r0, _r1, (g, h, i)), (_px, _py, pz) = studio_video._rows(
                    frames[0]["component_placements"][name])
                top = max(top, max(g*flat[k] + h*flat[k+1] + i*flat[k+2] + pz
                                   for k in range(0, len(flat), 3)))
            return top, "top of the world geometry: " + ", ".join(sorted(self.world))
        lowest = min(p[2] for frame in frames for p in self.box(frame["component_placements"]))
        return lowest, "lowest point of the drawn solids' bounds"

    def draw(self, poses: Mapping[str, Any], basis, bounds, floor: float, clock: str,
             target: Sequence[float] | None = None) -> bytes:
        posed = [tri for name in self.names
                 for tri in studio_video._posed(self.local[name], poses[name])]
        shadow = studio_render._contact_shadow(posed, floor=floor)
        ground = self.ground.visible(basis, bounds, FRAME) if self.ground else []
        pixels, _ = studio_render.studio(posed + ground, basis, bounds=bounds, size=FRAME,
                                         shadow=shadow)
        canvas = studio_render.Canvas(FRAME, FRAME, (0, 0, 0))
        canvas.pixels = bytearray(pixels)
        if target is not None:
            mark(canvas.pixels, FRAME, basis, bounds, target)
        canvas.text(10, FRAME - 24, clock, 2, studio_render.PALETTE["ink_2"])
        return bytes(canvas.pixels)


def _pixel(size: int, basis, bounds, point: Sequence[float]) -> tuple[float, float]:
    """Where ``point`` falls in a ``size`` px frame drawn on ``bounds``: the renderer's own mapping."""

    right, up = basis[0], basis[1]
    lo, hi = bounds
    scale = size / max(hi[0] - lo[0], hi[1] - lo[1])
    across = sum(p * r for p, r in zip(point, right)) - (lo[0] + hi[0]) / 2
    above = sum(p * u for p, u in zip(point, up)) - (lo[1] + hi[1]) / 2
    return size / 2 + across * scale, size / 2 - above * scale


def mark(pixels: bytearray, size: int, basis, bounds, point: Sequence[float]) -> bool:
    """Draw the target marker for ``point`` over a rendered frame; say whether its centre is in it.

    A ring of :data:`MARKER_COLOUR` inside a rim of the scene's background,
    antialiased by how much of each pixel the band covers. A ring partly
    outside the frame is drawn as far as the frame goes.
    """

    cx, cy = _pixel(size, basis, bounds, point)
    radius, band = MARKER_RADIUS * size, max(1.5, MARKER_BAND * size) / 2
    rim = studio_render.PALETTE["bg"]
    outer = radius + band + MARKER_RIM_PX + 1
    for oy in range(max(0, math.floor(cy - outer)), min(size, math.ceil(cy + outer))):
        for ox in range(max(0, math.floor(cx - outer)), min(size, math.ceil(cx + outer))):
            off = abs(math.hypot(ox + .5 - cx, oy + .5 - cy) - radius)
            ring = min(1.0, max(0.0, band + .5 - off))
            edge = min(1.0, max(0.0, band + MARKER_RIM_PX + .5 - off))
            if edge <= 0.0:
                continue
            at = 3 * (oy * size + ox)
            for j in range(3):
                under = pixels[at + j] + (rim[j] - pixels[at + j]) * edge
                pixels[at + j] = round(under + (MARKER_COLOUR[j] - under) * ring)
    return 0 <= cx < size and 0 <= cy < size


def _projected(points, basis) -> tuple[float, float, float, float]:
    right, up = basis[0], basis[1]
    xs = [p[0]*right[0] + p[1]*right[1] + p[2]*right[2] for p in points]
    ys = [p[0]*up[0] + p[1]*up[1] + p[2]*up[2] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _index(times: Sequence[float], moment: float) -> int:
    """The latest solved frame at or before ``moment``."""

    return max(0, min(len(times) - 1, bisect.bisect_right(times, moment + 1e-9) - 1))


def _sheet(frames: Sequence[bytes]) -> bytes:
    width = COLUMNS * FRAME + (COLUMNS - 1) * GUTTER
    height = ROWS * FRAME + (ROWS - 1) * GUTTER
    canvas = studio_render.Canvas(width, height, studio_render.PALETTE["bg"])
    for at, pixels in enumerate(frames):
        canvas.paste((at % COLUMNS) * (FRAME + GUTTER), (at // COLUMNS) * (FRAME + GUTTER),
                     pixels, FRAME, FRAME)
    return studio_render.png(bytes(canvas.pixels), width, height)


def travel_azimuth(stage: _Stage, frames: Sequence[Mapping[str, Any]],
                   base: str | None = None) -> tuple[float, float]:
    """``(azimuth_degrees, travel_mm)``: the plan direction ``base`` went.

    From where it was in the first solved frame to where it was farthest
    from there. A side-on camera puts its right along it, so the base
    travels left to right. One that stays within a twentieth of the
    design's size is seen from the front. With no base the design's own
    centre is what is tracked.
    """

    box = stage.box(frames[0]["component_placements"])
    size = max(max(p[j] for p in box) - min(p[j] for p in box) for j in range(3))
    centres = [stage.centre(frame["component_placements"], base)[:2] for frame in frames]
    x0, y0 = centres[0]
    far = max(centres, key=lambda c: math.hypot(c[0] - x0, c[1] - y0))
    travel = math.hypot(far[0] - x0, far[1] - y0)
    if travel < TRAVEL_FRACTION * size:
        return 0.0, travel
    return math.degrees(math.atan2(far[1] - y0, far[0] - x0)), travel


def overview(stage: _Stage, frames, times, floor: float, deadline: float,
             points: Sequence[Sequence[float]] | None = None) -> tuple[bytes, dict[str, Any]]:
    """Twelve frames evenly spaced over the episode, in one window on the whole path.

    ``points`` is the target of each solved frame, where the trace states
    one: the window holds every one of them beside the path, and each frame
    is marked with its own.
    """

    basis = studio_render.HERO
    boxes = [_projected(stage.box(frame["component_placements"]) + ([points[at]] if points else []), basis)
             for at, frame in enumerate(frames)]
    lo = [min(b[0] for b in boxes), min(b[1] for b in boxes)]
    hi = [max(b[2] for b in boxes), max(b[3] for b in boxes)]
    half = max(hi[0] - lo[0], hi[1] - lo[1]) / 2 * (1 + 2 * PAD)
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    bounds = ([cx - half, cy - half], [cx + half, cy + half])
    moments = [times[-1] * k / (STRIP - 1) for k in range(STRIP)]
    picked = [len(times) - 1 if k == STRIP - 1 else _index(times, moment)
              for k, moment in enumerate(moments)]
    drawn = []
    for at in picked:
        _require(time.monotonic() < deadline, f"the filmstrip ran past {STRIP_SECONDS} seconds")
        drawn.append(stage.draw(frames[at]["component_placements"], basis, bounds, floor,
                                f"{times[at]:.2f} s", target=points[at] if points else None))
    return _sheet(drawn), {
        "frames": len(drawn), "times_s": [times[at] for at in picked],
        "view": "hero: 35 degrees round from the front, 20 above the floor; one window on the whole path",
        "half_extent_mm": half,
        "marked_frames": _marked(basis, [bounds] * len(picked), picked, points),
    }


def _marked(basis, windows, picked: Sequence[int], points) -> int:
    """How many of a sheet's frames have their target's centre inside them."""

    if not points:
        return 0
    return sum(1 for at, bounds in zip(picked, windows)
               if all(0 <= value < FRAME for value in _pixel(FRAME, basis, bounds, points[at])))


def detail(stage: _Stage, frames, times, floor: float, deadline: float, *,
           start: float, step: float, base: str | None = None,
           points: Sequence[Sequence[float]] | None = None) -> tuple[bytes, dict[str, Any]]:
    """Up to twelve consecutive moments ``step`` apart from ``start``, side-on, following ``base``.

    ``base`` is the evaluation rig's floating base: the window is centred on
    it in every frame and wide enough that the whole design is inside it in
    each. A mechanism with none (``None``) has a base fixed to the world, and
    the window is fixed on everything the shown moments cover. The window
    never moves up or down, so the floor stays where it is.

    ``points`` is the target of each solved frame, where the trace states
    one, and each frame is marked with its own. A fixed window holds the
    shown moments' targets. A window that follows the base stays the
    design's size and marks a target only while it is inside.

    An episode that ended before the last of them is shown to its end: the
    window of moments slides back until its last one is the final frame.
    """

    span = (STRIP - 1) * step
    began = start if start + span <= times[-1] else max(0.0, times[-1] - span)
    picked = []
    for k in range(STRIP):
        moment = began + k * step
        if moment > times[-1] + 1e-9:
            break
        at = _index(times, moment)
        if not picked or at != picked[-1]:
            picked.append(at)
    azimuth, travel = travel_azimuth(stage, frames, base)
    basis = studio_render.camera(azimuth, DETAIL_ELEVATION_DEGREES)
    right = basis[0]
    held = bool(points) and base is None
    boxes = [_projected(stage.box(frames[at]["component_placements"]) + ([points[at]] if held else []),
                        basis) for at in picked]
    low, high = min(b[1] for b in boxes), max(b[3] for b in boxes)
    cy = (low + high) / 2
    if base is None:
        middle = (min(b[0] for b in boxes) + max(b[2] for b in boxes)) / 2
        centres = [middle] * len(picked)
    else:
        centres = [sum(c * r for c, r in zip(stage.centre(frames[at]["component_placements"], base), right))
                   for at in picked]
    across = max(max(cx - b[0], b[2] - cx) for cx, b in zip(centres, boxes))
    half = max(across, (high - low) / 2) * (1 + 2 * PAD)
    windows = [([cx - half, cy - half], [cx + half, cy + half]) for cx in centres]
    drawn = []
    for at, bounds in zip(picked, windows):
        _require(time.monotonic() < deadline, f"the filmstrip ran past {STRIP_SECONDS} seconds")
        drawn.append(stage.draw(frames[at]["component_placements"], basis, bounds, floor,
                                f"{times[at]:.2f} s", target=points[at] if points else None))
    view = ("side-on to the direction the base travelled, {:g} degrees above the floor; "
            "the window follows the base".format(DETAIL_ELEVATION_DEGREES) if base is not None else
            "side-on to the direction the design travelled, {:g} degrees above the floor; "
            "no floating base, so the window is fixed".format(DETAIL_ELEVATION_DEGREES))
    return _sheet(drawn), {
        "frames": len(drawn), "times_s": [times[at] for at in picked],
        "requested_start_s": start, "start_s": began, "step_s": step,
        "view": view, "follows": base,
        "azimuth_degrees": azimuth, "travel_mm": travel, "half_extent_mm": half,
        "marked_frames": _marked(basis, windows, picked, points),
    }


def detail_start(row: Mapping[str, Any], times: Sequence[float], given: float | None) -> tuple[float, str]:
    """Where a seed's detail begins, and why there."""

    if given is not None:
        return float(given), "given"
    onsets = [float(item["start_s"]) for item in (row.get("drawn") or {}).get("disturbance") or []
              if isinstance(item, Mapping) and isinstance(item.get("start_s"), (int, float))]
    if onsets:
        return min(onsets), "the seed's first disturbance"
    return times[-1] / 2, "the middle of the episode"


def _video(stage_names, looks, source, meshes, frames, times, out: Path, seed: int,
           floor: float, points: Sequence[Sequence[float]] | None = None, *,
           name: str | None = None, draw=None, ground: Ground | None = None) -> dict[str, Any]:
    """The seed's rollout as a studio video, encoded and decoded back before it is kept.

    With ``points``, each frame's target is kept inside the window and
    marked as the sheets mark it. ``draw(index, pixels, size, bounds)``
    marks a frame instead and says whether it marked anything; ``name`` is
    the file kept, the seed's rollout unless given.
    """

    started = time.monotonic()
    count = math.ceil(times[-1] * studio_video.FPS) + 1
    marked = []

    def overlay(at: int, pixels: bytearray, size: int, bounds) -> None:
        marked.append(draw(at, pixels, size, bounds) if draw is not None else
                      mark(pixels, size, studio_render.HERO, bounds, points[at]))

    def sample(i: int) -> int:
        return len(frames) - 1 if i == count - 1 else max(
            0, bisect.bisect_right(times, i / studio_video.FPS) - 1)

    with tempfile.TemporaryDirectory(prefix=".film-", dir=out) as temporary:
        work = Path(temporary)
        try:
            drawn = studio_video._studio_frames(looks, source, list(stage_names), meshes, frames,
                                                times, count, sample, work, started, floor=floor,
                                                held=points, ground=ground,
                                                overlay=overlay if points or draw else None)
            studio_video.encode(work, count)
        except ValueError as exc:
            raise FilmError(f"video: {exc}") from exc
        target = out / (name or VIDEO_NAME.format(seed=seed))
        (work / "rollout.webm").replace(target)
    return {"file": target.name, "sha256": _sha256(target), "bytes": target.stat().st_size,
            "frames": count, "fps": studio_video.FPS, "sim_seconds": times[-1],
            "width": drawn["width"], "height": drawn["height"],
            "projection": drawn["projection"], "floor_z_mm": drawn["floor_z_mm"],
            "marked_frames": sum(marked),
            "render_seconds": round(time.monotonic() - started, 3),
            "render_bound_seconds": studio_video.RENDER_SECONDS}


def film_digest() -> str:
    """Identity of the code that determines a film's pixels: the renderer,
    the video's drawing and this module's framing and layout."""

    digest = hashlib.sha256()
    for path in (Path(studio_render.__file__), Path(studio_render.FONT_FILE), Path(studio_video.__file__),
                 Path(__file__)):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def write_ignore(out: Path) -> None:
    """Keep what is drawn beside ``evaluation.json`` out of the project's history."""

    (out / IGNORE_NAME).write_text(IGNORE, encoding="utf-8")


def clear(out: Path) -> None:
    """Remove a previous film from ``out``."""

    for pattern in FILM_GLOBS:
        for stale in out.glob(pattern):
            stale.unlink()


def film_evaluation(root: Path, out: Path, report: Mapping[str, Any], *, seeds: Sequence[int],
                    inventory: Mapping[str, Any] | None = None,
                    start: float | None = None, step: float | None = None,
                    video: bool = True, progress=None) -> dict[str, Any]:
    """Draw ``seeds`` of the evaluation in ``out`` and return its ``film`` block.

    Each filmed seed gets its two sheets; the first also gets the video,
    unless ``video`` is false. ``report`` is the evaluation as measured: its
    rows name each seed's trace and digest, and the values it drew. A video
    that could not be encoded leaves the sheets, and the block says failed
    with the reason.
    """

    started = time.monotonic()
    step = DETAIL_STEP_S if step is None else float(step)
    _require(math.isfinite(step) and step > 0, "the detail step must be a positive number of seconds")
    _require(start is None or (math.isfinite(start) and start >= 0),
             "the detail start must be a time in the episode, in seconds")
    clear(out)
    write_ignore(out)
    rows = {int(row["seed"]): row for row in report.get("seeds") or []}
    revision = str(report.get("accepted_revision") or "")
    flats, sources, world = retained_solids(root, str(report.get("model_output") or ""))
    world_flats = {name: flats[name] for name in world}
    try:
        meshes, geometry = studio_video.drawn_meshes(
            {name: flat for name, flat in flats.items() if name not in world})
    except ValueError as exc:
        raise FilmError(str(exc)) from exc
    looks, source = materials(sources, list(meshes), revision, inventory)
    source["environment_omitted"] = sorted(world)
    stage = _Stage(meshes, looks, world_flats)
    # The body the evaluation measured tilt, heading and drift on, or None
    # for a mechanism fixed to the world.
    base = (report.get("rig") or {}).get("base")
    _require(base is None or base in stage.names,
             f"the evaluation's base, {base}, is not one of the solids drawn")
    # The video's renderer finds its floor the same way, from the world's own triangles.
    world_meshes = {name: [tuple(tuple(flat[k + 3*c:k + 3*c + 3]) for c in range(3))
                           for k in range(0, len(flat), 9)] for name, flat in world_flats.items()}
    filmed = []
    for position, seed in enumerate(seeds):
        row = rows.get(int(seed))
        _require(row is not None and isinstance(row.get("trace"), Mapping),
                 f"seed {seed} is not in this evaluation")
        frames, times, target = read_trace(out / str(row["trace"]["file"]), str(row["trace"]["sha256"]),
                                           list(flats))
        # A seed the report says was given a point and a trace that names
        # none would be filmed unmarked, and look like an episode with
        # nowhere to go.
        _require(target is not None or not any(
            isinstance(item, Mapping) and item.get("kind") == "point"
            for item in (row.get("drawn") or {}).get("goal") or []),
            f"seed {seed} drew a point goal and its trace carries none to mark")
        points = target["points"] if target else None
        course = read_terrain(out / str(row["trace"]["file"]))
        stage.ground = Ground(course) if course else None
        if course is not None:
            floor, floor_source = terrain_floor(course), "the course's plane (ADR-734)"
        else:
            floor, floor_source = stage.floor(frames, (report.get("rig") or {}).get("floor_mm"))
        deadline = time.monotonic() + STRIP_SECONDS
        entry: dict[str, Any] = {"seed": int(seed), "trace_sha256": str(row["trace"]["sha256"]),
                                 "floor_z_mm": floor, "floor_source": floor_source}
        image, facts = overview(stage, frames, times, floor, deadline, points)
        entry["overview"] = _keep(out / OVERVIEW_NAME.format(seed=seed), image, facts)
        begin, why = detail_start(row, times, start)
        image, facts = detail(stage, frames, times, floor, deadline, start=begin, step=step, base=base,
                              points=points)
        entry["detail"] = _keep(out / DETAIL_NAME.format(seed=seed), image, {**facts, "start_source": why})
        entry["video"] = None
        entry["target"] = target and {key: target[key] for key in ("goal", "channels", "unit", "positions")}
        if course is not None:
            entry["terrain"] = {"kind": course["kind"], "course": course.get("course"),
                                "boxes": len(course.get("boxes") or ()),
                                "domes": len(course.get("domes") or ())}
        filmed.append(entry)
        if position == 0:
            first = (frames, times, floor, points, stage.ground)
        if progress is not None:
            progress(" · film  seed {:d}  sheets  {:.1f} s".format(int(seed), time.monotonic() - started))
    # The video last: it is the long half, and the sheets stand without it.
    error = None
    if video and filmed:
        frames, times, floor, points, ground = first
        try:
            try:
                studio_video.ffmpeg()
            except ValueError as exc:
                raise FilmError(f"video: {exc}; the sheets were drawn") from exc
            filmed[0]["video"] = _video(stage.names + sorted(world), looks, source,
                                        {**meshes, **world_meshes}, frames, times, out,
                                        filmed[0]["seed"], floor, points, ground=ground)
        except FilmError as exc:
            error = str(exc)
        if progress is not None:
            progress(" · film  seed {:d}  video  {:.1f} s".format(
                filmed[0]["seed"], time.monotonic() - started))
    return {
        "schema": FILM_SCHEMA, "state": "failed" if error else "ready", "error": error,
        "style": "studio", "style_sha256": film_digest(),
        "renderer": "CadexStudio studio (engine), CPU, no browser or display",
        "floor": "the review viewport's dark prototype mat (ADR-444)",
        "frame_px": FRAME, "sheet": {"columns": COLUMNS, "rows": ROWS, "gutter_px": GUTTER},
        "overlay": "simulation seconds, bottom left of every frame",
        "marker": {"what": "a ring centred on the target point in force at the frame's time, drawn over "
                           "the solids, in a seed whose trace carries a point goal",
                   "color": "#%02X%02X%02X" % MARKER_COLOUR,
                   "radius_px": MARKER_RADIUS * FRAME, "radius_of_frame": MARKER_RADIUS},
        "showing": "tessellated solids of the accepted revision at each recorded pose, on the "
                   "course each seed's trace stood on when it names one (ADR-734); "
                   "collision proxies and world geometry not drawn",
        "materials": source,
        "appearance": {name: {"role": looks[name][0], "color": "#%02X%02X%02X" % tuple(looks[name][1]),
                              "finish": getattr(looks[name], "finish", "printed")}
                       for name in stage.names},
        "geometry": geometry,
        "seeds": filmed,
        "render_seconds": round(time.monotonic() - started, 3),
    }


def _keep(path: Path, image: bytes, facts: Mapping[str, Any]) -> dict[str, Any]:
    path.write_bytes(image)
    return {"file": path.name, "sha256": hashlib.sha256(image).hexdigest(), "bytes": len(image),
            "width": COLUMNS * FRAME + (COLUMNS - 1) * GUTTER,
            "height": ROWS * FRAME + (ROWS - 1) * GUTTER, **facts}


def failed(error: Exception | str) -> dict[str, Any]:
    """The ``film`` block of an evaluation whose film could not be drawn."""

    return {"schema": FILM_SCHEMA, "state": "failed", "error": str(error), "seeds": []}

