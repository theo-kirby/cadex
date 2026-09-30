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
  design travelled, the window following it. Every frame carries its
  simulation time and nothing else;
- a **video** of the first filmed seed, drawn as a run's studio video is
  (:mod:`video`), ten frames a second.

The solids are the accepted attempt's own retained tessellation, moved
rigidly to each frame's recorded pose. Nothing is rebuilt and no engine is
opened. Nothing here knows what the behaviour is: the detail starts where
the seed's first drawn disturbance begins, or at the middle of an episode
that has none, unless the caller says otherwise.
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
#: Declared bound on drawing one seed's two sheets.
STRIP_SECONDS = 300
OVERVIEW_NAME = "seed-{seed}-overview.png"
DETAIL_NAME = "seed-{seed}-detail.png"
VIDEO_NAME = "seed-{seed}-rollout.webm"
#: What a re-run removes before it draws.
FILM_GLOBS = ("seed-*-overview.png", "seed-*-detail.png", "seed-*-rollout.webm")
#: Written beside the film. A project is a git repository that commits what
#: a command changed (ADR-194); the report belongs in its history and the
#: film, which the traces can draw again, does not.
IGNORE_NAME = ".gitignore"
IGNORE = ("# Written by cadex evaluate (ADR-459). The film is drawn from this evaluation's\n"
          "# traces and can be drawn again with --film-only; evaluation.json is the record.\n"
          + "".join(pattern + "\n" for pattern in FILM_GLOBS))


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
    mechanism for a catalogued part and shell for a printed one. The
    inventory block carries both, read from the accepted attempt. Without
    one at this revision every part is drawn as shell, and the film says so.
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
                                        palette=palette)
    except studio_render.StudioError as exc:
        raise FilmError(str(exc)) from exc
    return looks, {"source": "the accepted assembly's inventory", "declared": True}


# -- one seed's trace ---------------------------------------------------------

def read_trace(path: Path, expected_sha256: str, names: Sequence[str]) -> tuple[list[dict], list[float]]:
    """The solved frames of one seed's trace and their times, checked.

    The file filmed is the file measured: its digest is the one the
    evaluation recorded for the seed.
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
    return frames, [float(t) for t in times]


class _Stage:
    """The drawn solids, prepared once, and the measures every shot needs."""

    def __init__(self, meshes: Mapping[str, list], looks: Mapping[str, tuple],
                 world_flats: Mapping[str, array]) -> None:
        self.names = [name for name in meshes if name in looks]
        _require(self.names, "nothing to draw once world geometry is left out")
        self.local = {name: studio_render._prepare(
            [((looks[name][1], studio_render.FINISH[looks[name][0]]), meshes[name])])
            for name in self.names}
        self.corners = {}
        for name in self.names:
            points = [p for tri in meshes[name] for p in tri]
            lo = [min(p[j] for p in points) for j in range(3)]
            hi = [max(p[j] for p in points) for j in range(3)]
            self.corners[name] = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                                  for z in (lo[2], hi[2])]
        self.world = dict(world_flats)

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

    def draw(self, poses: Mapping[str, Any], basis, bounds, floor: float, clock: str) -> bytes:
        posed = [tri for name in self.names
                 for tri in studio_video._posed(self.local[name], poses[name])]
        shadow = studio_render._contact_shadow(posed, floor=floor)
        pixels, _ = studio_render.studio(posed, basis, bounds=bounds, size=FRAME, shadow=shadow)
        canvas = studio_render.Canvas(FRAME, FRAME, (0, 0, 0))
        canvas.pixels = bytearray(pixels)
        canvas.text(10, FRAME - 24, clock, 2, studio_render.PALETTE["ink_2"])
        return bytes(canvas.pixels)


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


def travel_azimuth(stage: _Stage, frames: Sequence[Mapping[str, Any]]) -> tuple[float, float]:
    """``(azimuth_degrees, travel_mm)``: the plan direction the design went.

    From its centre in the first solved frame to its centre where that was
    farthest from the start. A side-on camera puts its right along it, so
    the design travels left to right. One that stays put is seen from the
    front.
    """

    centres, size = [], 0.0
    for at, frame in enumerate(frames):
        box = stage.box(frame["component_placements"])
        lo = [min(p[j] for p in box) for j in range(3)]
        hi = [max(p[j] for p in box) for j in range(3)]
        if at == 0:
            size = max(hi[j] - lo[j] for j in range(3))
        centres.append(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2))
    x0, y0 = centres[0]
    far = max(centres, key=lambda c: math.hypot(c[0] - x0, c[1] - y0))
    travel = math.hypot(far[0] - x0, far[1] - y0)
    if travel < TRAVEL_FRACTION * size:
        return 0.0, travel
    return math.degrees(math.atan2(far[1] - y0, far[0] - x0)), travel


def overview(stage: _Stage, frames, times, floor: float, deadline: float) -> tuple[bytes, dict[str, Any]]:
    """Twelve frames evenly spaced over the episode, in one window on the whole path."""

    basis = studio_render.HERO
    boxes = [_projected(stage.box(frame["component_placements"]), basis) for frame in frames]
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
                                f"T {times[at]:.2f} S"))
    return _sheet(drawn), {
        "frames": len(drawn), "times_s": [times[at] for at in picked],
        "view": "hero: 35 degrees round from the front, 20 above the floor; one window on the whole path",
        "half_extent_mm": half,
    }


def detail(stage: _Stage, frames, times, floor: float, deadline: float, *,
           start: float, step: float) -> tuple[bytes, dict[str, Any]]:
    """Up to twelve consecutive moments ``step`` apart from ``start``, side-on, followed.

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
    azimuth, travel = travel_azimuth(stage, frames)
    basis = studio_render.camera(azimuth, DETAIL_ELEVATION_DEGREES)
    boxes = [_projected(stage.box(frames[at]["component_placements"]), basis) for at in picked]
    low, high = min(b[1] for b in boxes), max(b[3] for b in boxes)
    cy = (low + high) / 2
    half = max(max(b[2] - b[0] for b in boxes), high - low) / 2 * (1 + 2 * PAD)
    drawn = []
    for at, box in zip(picked, boxes):
        _require(time.monotonic() < deadline, f"the filmstrip ran past {STRIP_SECONDS} seconds")
        cx = (box[0] + box[2]) / 2
        drawn.append(stage.draw(frames[at]["component_placements"], basis,
                                ([cx - half, cy - half], [cx + half, cy + half]), floor,
                                f"T {times[at]:.2f} S"))
    return _sheet(drawn), {
        "frames": len(drawn), "times_s": [times[at] for at in picked],
        "requested_start_s": start, "start_s": began, "step_s": step,
        "view": "side-on to the direction of travel, {:g} degrees above the floor; "
                "the window follows the design".format(DETAIL_ELEVATION_DEGREES),
        "azimuth_degrees": azimuth, "travel_mm": travel, "half_extent_mm": half,
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
           floor: float) -> dict[str, Any]:
    """The seed's rollout as a studio video, encoded and decoded back before it is kept."""

    started = time.monotonic()
    count = math.ceil(times[-1] * studio_video.FPS) + 1

    def sample(i: int) -> int:
        return len(frames) - 1 if i == count - 1 else max(
            0, bisect.bisect_right(times, i / studio_video.FPS) - 1)

    with tempfile.TemporaryDirectory(prefix=".film-", dir=out) as temporary:
        work = Path(temporary)
        try:
            drawn = studio_video._studio_frames(looks, source, list(stage_names), meshes, frames,
                                                times, count, sample, work, started, floor=floor)
            studio_video.encode(work, count)
        except ValueError as exc:
            raise FilmError(f"video: {exc}") from exc
        target = out / VIDEO_NAME.format(seed=seed)
        (work / "rollout.webm").replace(target)
    return {"file": target.name, "sha256": _sha256(target), "bytes": target.stat().st_size,
            "frames": count, "fps": studio_video.FPS, "sim_seconds": times[-1],
            "width": drawn["width"], "height": drawn["height"],
            "projection": drawn["projection"], "floor_z_mm": drawn["floor_z_mm"],
            "render_seconds": round(time.monotonic() - started, 3),
            "render_bound_seconds": studio_video.RENDER_SECONDS}


def film_digest() -> str:
    """Identity of the code that determines a film's pixels: the renderer,
    the video's drawing and this module's framing and layout."""

    digest = hashlib.sha256()
    for path in (Path(studio_render.__file__), Path(studio_video.__file__), Path(__file__)):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


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
    (out / IGNORE_NAME).write_text(IGNORE, encoding="utf-8")
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
    # The video's renderer finds its floor the same way, from the world's own triangles.
    world_meshes = {name: [tuple(tuple(flat[k + 3*c:k + 3*c + 3]) for c in range(3))
                           for k in range(0, len(flat), 9)] for name, flat in world_flats.items()}
    filmed = []
    for position, seed in enumerate(seeds):
        row = rows.get(int(seed))
        _require(row is not None and isinstance(row.get("trace"), Mapping),
                 f"seed {seed} is not in this evaluation")
        frames, times = read_trace(out / str(row["trace"]["file"]), str(row["trace"]["sha256"]),
                                   list(flats))
        floor, floor_source = stage.floor(frames, (report.get("rig") or {}).get("floor_mm"))
        deadline = time.monotonic() + STRIP_SECONDS
        entry: dict[str, Any] = {"seed": int(seed), "trace_sha256": str(row["trace"]["sha256"]),
                                 "floor_z_mm": floor, "floor_source": floor_source}
        image, facts = overview(stage, frames, times, floor, deadline)
        entry["overview"] = _keep(out / OVERVIEW_NAME.format(seed=seed), image, facts)
        begin, why = detail_start(row, times, start)
        image, facts = detail(stage, frames, times, floor, deadline, start=begin, step=step)
        entry["detail"] = _keep(out / DETAIL_NAME.format(seed=seed), image, {**facts, "start_source": why})
        entry["video"] = None
        filmed.append(entry)
        if position == 0:
            first = (frames, times, floor)
        if progress is not None:
            progress(" · film  seed {:d}  sheets  {:.1f} s".format(int(seed), time.monotonic() - started))
    # The video last: it is the long half, and the sheets stand without it.
    error = None
    if video and filmed:
        frames, times, floor = first
        try:
            try:
                studio_video.ffmpeg()
            except ValueError as exc:
                raise FilmError(f"video: {exc}; the sheets were drawn") from exc
            filmed[0]["video"] = _video(stage.names + sorted(world), looks, source,
                                        {**meshes, **world_meshes}, frames, times, out,
                                        filmed[0]["seed"], floor)
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
        "showing": "tessellated solids of the accepted revision at each recorded pose; "
                   "collision proxies and world geometry not drawn",
        "materials": source,
        "appearance": {name: {"role": looks[name][0], "color": "#%02X%02X%02X" % tuple(looks[name][1])}
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
