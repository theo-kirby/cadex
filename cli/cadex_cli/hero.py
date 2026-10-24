# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""``cadex hero``: a project's presentation folder, made on request (ADR-677).

Nothing makes it on its own: a person or their agent runs ``cadex hero
--project DIR`` and ``DIR/hero/`` is written anew:

- ``still-<look>.png``: the accepted design on the clean mat under a lighting
  setup or a matcap (shading.js), each from its own side, no chrome;
- ``dashboard.png``: the dashboard with the 3D viewport on the left half and
  Status, showing training, on the right;
- ``sheet.png``: the concept sheet ``cadex render`` draws, of the accepted
  revision;
- ``rollout.mp4``: the chosen rollout (:func:`choose_rollout`) followed by the
  dashboard's rig, with its clock;
- ``hero-landscape.mp4`` and ``hero-square.mp4``: a full turn round the design
  that wipes from clay to aluminium to the wireframe to its own materials,
  then the rollout, then the training curves drawing themselves;
- ``hero.json``: what was made, from what, and why anything was not.

Each item stands alone: one that cannot be made is named in ``hero.json`` and
the rest are still made. Everything but the sheet is drawn by the dashboard's
own scene in headless Chromium (``hero.html``), from what the review server
serves, so this module never opens the engine; the sheet is a callable the
CLI hands in, because drawing one needs the design's fit and inventory.
FFmpeg encodes; it is an external program, never imported.

Independently authored LGPL client code.
"""
from __future__ import annotations

import base64
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any, Callable

from .browser import HeadlessBrowser, find_browser
from .review_server import (
    ReviewProject, accepted_model, checkpoint_playback, presentation, run_model, serve, STATIC_DIR,
)
from .video import ffmpeg

HERO_DIRNAME = "hero"
SCHEMA = "cadex-hero-v1"
ITEMS = ("stills", "dashboard", "sheet", "rollout", "video", "views")
#: What a bare ``cadex hero`` makes: the views are asked for by name (``--only views``).
DEFAULT_ITEMS = ITEMS[:-1]
PAGE_ITEMS = {"stills", "dashboard", "rollout", "video", "views"}
FPS = 30
#: The stills: each a look (shading.js) from its own three-quarter view, yaw and pitch in radians as
#: the viewport's camera has them (yaw 0.8, pitch 0.5 is its Fit). Three-quarter views show two
#: faces of any design whichever way it faces; a side-on view of a box is a rectangle.
STILLS = (
    {"name": "studio", "look": "studio", "yaw": 0.8, "pitch": 0.42},
    {"name": "softbox", "look": "softbox", "yaw": -0.8, "pitch": 0.5},
    {"name": "dramatic", "look": "dramatic", "yaw": 2.35, "pitch": 0.24},
    {"name": "aluminium", "look": "aluminium", "yaw": -2.35, "pitch": 0.55},
    {"name": "wireframe", "style": "wireframe", "yaw": 0.8, "pitch": 0.42},
)
STILL = {"size": (2560, 1440), "supersample": 2, "fill": 0.8}
#: The views (ADR-792): fixed cameras, so that two projects, or two revisions, compare shot for
#: shot. Yaw is measured from the design's front, the direction from its centre to its focus parts
#: (the head), so a design that faces any way is shot alike; ``parts`` frames the focus alone.
VIEWS = (
    {"name": "hero", "yaw": 0.75, "pitch": 0.42, "fill": 0.8},
    {"name": "side", "yaw": math.pi / 2, "pitch": 0.08, "fill": 0.85},
    {"name": "front", "yaw": 0.0, "pitch": 0.12, "fill": 0.8},
    {"name": "rear", "yaw": math.pi - 0.75, "pitch": 0.42, "fill": 0.8},
    {"name": "top", "yaw": math.pi / 2, "pitch": 1.45, "fill": 0.85},
    {"name": "head", "yaw": 0.6, "pitch": 0.2, "fill": 0.7, "parts": True},
)
VIEW = {"size": (1920, 1080), "supersample": 2, "look": "studio"}
#: The focus parts by default: a creature's head, named as the creature style names its parts.
FOCUS = r"(^|_)(head|skull|jaw|muzzle|snout|nose|face|cheek|brow|eye|ear)"
#: The two hero videos' frames.
FORMATS = {"landscape": (1920, 1080), "square": (1080, 1080)}
#: The turn: one full revolution at constant speed, starting from the viewport's yaw, while the
#: camera cranes down from ``pitch[0]`` to ``pitch[1]`` and pushes in by ``push`` of its distance,
#: both eased. Each layer after the first wipes over the one before at ``at`` seconds, taking ``wipe_s``.
TURNTABLE = {
    "seconds": 12.0, "yaw": 0.8, "pitch": (0.62, 0.36), "push": 0.12, "fill": 0.9, "wipe_s": 0.55,
    "layers": ({"look": "clay"}, {"look": "aluminium", "at": 2.7},
               {"style": "wireframe", "at": 5.9}, {"look": "studio", "at": 9.1}),
}
#: The wireframe turn: the same move in half the time, in the wireframe alone.
WIRE_TURN = {**TURNTABLE, "seconds": 6.0, "layers": ({"style": "wireframe"},)}
#: The rollout as the hero videos show it (at most ``clip_s`` of it), and as rollout.mp4 does.
#: ``fraction`` is the subject's standing height over the frame height (the follow rig's framing).
ROLLOUT = {"fraction": 0.42, "yaw": 0.8, "pitch": 0.3, "hold_s": 0.8, "clip_s": 6.0}
#: The training curves: drawn over ``draw_s``, then held.
PLOT = {"draw_s": 3.0, "hold_s": 1.6}
#: Crossfade between the hero video's parts.
FADE_S = 0.6
#: The frames are full-range JPEG; a video players read alike is limited-range BT.709 4:2:0.
TO_VIDEO = "scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p"
DASHBOARD = {"size": (1920, 1080), "scale": 2, "settle_s": 25.0}
#: Chromium's GPU path: ANGLE over Vulkan. ANGLE over EGL dropped whole parts from the odd frame of
#: a turn on an NVIDIA driver (ADR-677); Vulkan and SwiftShader drew every frame whole. Without a
#: GPU Chromium falls back to SwiftShader.
#: The 2D canvas stays in software: a GPU-accelerated canvas copied into WebGL came through black in
#: headless Chromium on most runs, which drew the mat's grid texture as a black floor.
GPU_FLAGS = ("--use-angle=vulkan", "--enable-features=Vulkan", "--ignore-gpu-blocklist",
             "--disable-accelerated-2d-canvas")
LAYOUT_KEY = "cadex.layout.v6"
#: Generous: a 775k-triangle model takes ~40 s to load into the page.
LOAD_TIMEOUT_S = 900.0


class HeroError(RuntimeError):
    pass


def hero_dir(root: Path, out: Path | None = None) -> Path:
    return Path(out).expanduser() if out else Path(root) / HERO_DIRNAME


def _smooth(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def _snap(x: float) -> float:
    """Ease in and out, cubic: slow off the mark, fast across the middle, settling at the end."""
    x = max(0.0, min(1.0, x))
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def turntable_camera(t: float, fitted: dict[str, Any], spec: dict[str, Any] = TURNTABLE) -> dict[str, Any]:
    """The turn's camera at ``t`` seconds: round once, craning down and pushing in, eased."""

    u = max(0.0, min(1.0, t / spec["seconds"]))
    eased = _smooth(u)
    pitch = spec["pitch"][0] + (spec["pitch"][1] - spec["pitch"][0]) * eased
    return {**fitted, "yaw": spec["yaw"] + 2 * math.pi * u, "pitch": pitch,
            "distance": fitted["distance"] * (1 - spec["push"] * eased)}


def turntable_layers(t: float, spec: dict[str, Any] = TURNTABLE) -> list[dict[str, Any]]:
    """The layers at ``t`` seconds into the turn, each later one with its wipe's progress."""

    layers = []
    for layer in spec["layers"]:
        entry = {k: v for k, v in layer.items() if k != "at"}
        if "at" in layer:
            entry["wipe"] = round(_snap((t - layer["at"]) / spec["wipe_s"]), 5)
        layers.append(entry)
    return layers


# -- choosing what to show ---------------------------------------------------------------------

def _run_names(root: Path) -> list[str]:
    """The runs, oldest first, as the dashboard lists them."""

    return [str(r.get("run")) for r in ReviewProject(root).review().get("runs") or [] if r.get("run")]


def choose_rollout(root: Path, run: str | None = None) -> dict[str, Any] | None:
    """The rollout to show: the longest episode any run's policy lasted, the newest among equals.

    Candidates are each run's own rollout (its final policy) and each checkpoint rollout the
    engine made while it trained (ADR-544); with ``run``, that run's alone. An episode that
    lasted longer is the policy doing more of its task, so length decides, and among rollouts
    that lasted the whole episode the newest -- the most trained -- wins, a run's own rollout
    after its checkpoints. ``None`` when nothing is playable.
    """

    root = Path(root)
    project = ReviewProject(root)
    names = [run] if run else _run_names(root)
    best, best_key = None, None
    for order, name in enumerate(names):
        record = project.run(name)
        if record is None:
            if run:
                raise HeroError(f"no run named {run}")
            continue
        candidates = []
        train = root / "runs" / name / "train"
        if train.is_dir():
            for trace in sorted(train.glob("*.rollout-trace.json")):
                stem = trace.name[: -len(".rollout-trace.json")]
                served = checkpoint_playback(root, name, stem)
                if served and served.get("available") and len(served.get("times_s") or []) >= 2:
                    iteration = (served.get("checkpoint") or {}).get("iteration")
                    candidates.append((served["times_s"][-1], int(iteration) if isinstance(iteration, int) else -1, {
                        "kind": "checkpoint", "run": name, "stem": stem, "iteration": iteration,
                        "url": f"api/playback/checkpoint/{name}/{stem}", "model": f"api/model/run/{name}"}))
        model = run_model(root, record)
        own = model.get("playback") if model.get("available") else None
        if isinstance(own, dict) and own.get("available") and own.get("url"):
            duration = own.get("duration_s") or 0.0
            candidates.append((float(duration), 10 ** 9, {
                "kind": "final", "run": name, "stem": None, "iteration": None,
                "url": own["url"], "model": f"api/model/run/{name}"}))
        for duration, rank, item in candidates:
            key = (round(float(duration), 2), order, rank)
            if best_key is None or key > best_key:
                best, best_key = {**item, "duration_s": float(duration)}, key
    return best


def training_curves(root: Path, run: str | None) -> dict[str, Any] | None:
    """The reward and loss curves of ``run`` (else the newest run that has any), as the plot draws them."""

    project = ReviewProject(root)
    names = ([run] if run else []) + list(reversed(_run_names(root)))
    for name in names:
        detail = project.detail(name)
        telemetry = (detail or {}).get("telemetry") or {}
        reward = [[int(p[0]) + 1, float(p[1])] for p in telemetry.get("curve") or []
                  if isinstance(p, list) and len(p) == 2 and all(isinstance(v, (int, float)) and math.isfinite(v) for v in p)]
        loss = [[int(p[0]) + 1, float(p[1])] for p in telemetry.get("loss_curve") or []
                if isinstance(p, list) and len(p) == 2 and all(isinstance(v, (int, float)) and math.isfinite(v) for v in p)]
        if len(reward) < 2:
            continue
        best = None
        if isinstance(telemetry.get("best_iteration"), int) and isinstance(telemetry.get("best_reward_per_step"), (int, float)):
            best = [telemetry["best_iteration"] + 1, float(telemetry["best_reward_per_step"])]
        panels = [{"label": "reward per step", "points": reward, "best": best}]
        if len(loss) >= 2:
            panels.append({"label": "loss", "points": loss, "best": None})
        label = str(telemetry.get("label") or (detail or {}).get("training", {}).get("label") or "")
        return {"run": name, "panels": panels, "iterations": reward[-1][0],
                "subtitle": " · ".join(x for x in (name, label, f"{reward[-1][0]} iterations") if x)}
    return None


# -- the page ----------------------------------------------------------------------------------

class Stage:
    """One headless Chromium on one review server over the project, and the hero page in it."""

    def __init__(self, root: Path, *, gpu: bool, progress: Callable[[str], None]) -> None:
        self.root = root
        self.progress = progress
        executable = find_browser()
        if executable is None:
            raise HeroError("headless Chromium is required (CADEX_BROWSER or PATH)")
        self.server, _ = serve(root, "127.0.0.1", 0)
        try:
            self.browser = HeadlessBrowser(executable, width=1920, height=1080, gpu=GPU_FLAGS if gpu else ())
        except Exception:
            self._stop_server()
            raise
        self.page = None
        self.loaded = None
        self.renderer = ""

    def _stop_server(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def close(self) -> None:
        try:
            self.browser.close()
        finally:
            self._stop_server()

    def hero(self):
        if self.page is None:
            self.page = self.browser.page(self.server.url + "hero.html")
            self.page.wait_for("window.cadexHero && window.cadexHero.available !== undefined", timeout=60)
            if not self.page.evaluate("cadexHero.available"):
                raise HeroError("WebGL is unavailable in headless Chromium")
            self.renderer = self.page.evaluate(
                "(()=>{const g=document.createElement('canvas').getContext('webgl2');"
                "const e=g&&g.getExtension('WEBGL_debug_renderer_info');"
                "return g?(e?g.getParameter(e.UNMASKED_RENDERER_WEBGL):g.getParameter(g.RENDERER)):''})()") or ""
        return self.page

    def call(self, expression: str, *, timeout: float = 120.0, await_promise: bool = False) -> Any:
        return self.hero().evaluate(expression, timeout=timeout, await_promise=await_promise)

    def load(self, url: str) -> dict[str, Any]:
        if self.loaded and self.loaded[0] == url:
            return self.loaded[1]
        self.progress(f" · loading {url}")
        facts = self.call(f"cadexHero.load({json.dumps(url)})", timeout=LOAD_TIMEOUT_S, await_promise=True)
        self.loaded = (url, facts)
        return facts

    def size(self, width: int, height: int, supersample: int = 1) -> None:
        self.call(f"cadexHero.size({width},{height},{supersample})")

    def grab(self, path: Path, kind: str = "png") -> None:
        data = self.call(f"cadexHero.image({json.dumps(kind)}, .95)", timeout=120)
        path.write_bytes(base64.b64decode(data))


def _frames(work: Path, name: str) -> Path:
    directory = work / name
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def make_stills(stage: Stage, out: Path) -> list[dict[str, Any]]:
    facts = stage.load("api/model/accepted")
    width, height = STILL["size"]
    stage.size(width, height, STILL["supersample"])
    made = []
    for spec in STILLS:
        camera = stage.call("cadexHero.fitCamera(" + json.dumps(
            {"yaw": spec["yaw"], "pitch": spec["pitch"], "fill": STILL["fill"]}) + ")")
        layer = {"style": "wireframe"} if spec.get("style") == "wireframe" else {"look": spec["look"]}
        stage.call("cadexHero.shot(" + json.dumps({"camera": camera, "layers": [layer]}) + ")")
        path = out / f"still-{spec['name']}.png"
        stage.grab(path, "png")
        made.append({"file": path.name, **layer, "size": [width, height],
                     "supersample": STILL["supersample"], "camera": camera, "revision": facts.get("revision")})
    return made


def make_views(stage: Stage, out: Path, focus: str = FOCUS) -> dict[str, Any]:
    """``view-<name>.png`` from each of :data:`VIEWS`, in the studio look on the dark mat."""

    facts = stage.load("api/model/accepted")
    width, height = VIEW["size"]
    stage.size(width, height, VIEW["supersample"])
    found = stage.call("cadexHero.focus(" + json.dumps(focus) + ")")
    if not found["names"]:
        raise HeroError(f"no part's name matches the focus {focus!r}: pass --focus")
    front = math.atan2(found["center"][1] - found["design"][1], found["center"][0] - found["design"][0])
    made = []
    for spec in VIEWS:
        options = {"yaw": front + spec["yaw"], "pitch": spec["pitch"], "fill": spec["fill"]}
        if spec.get("parts"):
            options["parts"] = found["names"]
        camera = stage.call("cadexHero.fitCamera(" + json.dumps(options) + ")")
        stage.call("cadexHero.shot(" + json.dumps({"camera": camera, "layers": [{"look": VIEW["look"]}]}) + ")")
        path = out / f"view-{spec['name']}.png"
        stage.grab(path, "png")
        made.append({"file": path.name, "view": spec["name"], "camera": camera})
    return {"files": made, "focus": focus, "focus_parts": found["names"], "front_yaw": front,
            "look": VIEW["look"], "size": [width, height], "supersample": VIEW["supersample"],
            "revision": facts.get("revision")}


def turntable_frames(stage: Stage, directory: Path, width: int, height: int,
                     spec: dict[str, Any] = TURNTABLE) -> dict[str, Any]:
    facts = stage.load("api/model/accepted")
    stage.size(width, height, 1)
    count = round(spec["seconds"] * FPS)
    # One base distance that frames every view of the move, each at its own pitch and push.
    probe = {"yaw": spec["yaw"], "pitch": spec["pitch"][0], "distance": 1.0, "target": [0, 0, 0]}
    views = []
    for j in range(49):
        view = turntable_camera(spec["seconds"] * j / 48, probe, spec)
        views.append({"yaw": view["yaw"], "pitch": view["pitch"], "scale": view["distance"]})
    camera = stage.call("cadexHero.fitCamera(" + json.dumps(
        {"yaw": spec["yaw"], "pitch": spec["pitch"][0], "fill": spec["fill"], "views": views}) + ")")
    for i in range(count):
        t = i / FPS
        stage.call("cadexHero.shot(" + json.dumps({"camera": turntable_camera(t, camera, spec),
                                                    "layers": turntable_layers(t, spec)}) + ")")
        stage.grab(directory / f"{i:05d}.png")
    return {"frames": count, "seconds": count / FPS, "camera": camera, "revision": facts.get("revision"),
            "layers": [dict(layer) for layer in spec["layers"]], "wipe_s": spec["wipe_s"]}


def rollout_frames(stage: Stage, choice: dict[str, Any], directory: Path, width: int, height: int,
                   *, clock: bool, limit_s: float | None) -> dict[str, Any]:
    try:
        facts = stage.load(choice["model"])
    except Exception:  # noqa: BLE001 - a run with no kept model poses the accepted one
        facts = stage.load("api/model/accepted")
    stage.size(width, height, 1)
    rig = stage.call("cadexHero.rollout(" + json.dumps(choice["url"]) + ", " + json.dumps(
        {"fps": FPS, "fraction": ROLLOUT["fraction"], "yaw": ROLLOUT["yaw"], "pitch": ROLLOUT["pitch"],
         "hold_s": ROLLOUT["hold_s"]}) + ")", timeout=600, await_promise=True)
    count = rig["frames"] if limit_s is None else min(rig["frames"], round(limit_s * FPS))
    for i in range(count):
        stage.call(f"cadexHero.rolloutFrame({i}, " + json.dumps({"clock": clock}) + ")")
        stage.grab(directory / f"{i:05d}.png")
    return {"frames": count, "seconds": count / FPS, "sim_seconds": rig["sim_seconds"], "model": facts,
            "rig": rig["rig"], "source": rig.get("source")}


def plot_frames(stage: Stage, curves: dict[str, Any], directory: Path, width: int, height: int, title: str) -> dict[str, Any]:
    stage.size(width, height, 1)
    draw, hold = round(PLOT["draw_s"] * FPS), round(PLOT["hold_s"] * FPS)
    layout = "row" if width > height * 1.2 else "col"
    for i in range(draw + hold):
        progress = _smooth(i / max(1, draw - 1)) if i < draw else 1.0
        stage.call("cadexHero.plot(" + json.dumps({"title": title, "subtitle": curves["subtitle"],
                                                    "panels": curves["panels"], "progress": progress,
                                                    "layout": layout}) + ")")
        stage.grab(directory / f"{i:05d}.png")
    return {"frames": draw + hold, "seconds": (draw + hold) / FPS, "run": curves["run"],
            "panels": [p["label"] for p in curves["panels"]]}


def encode(segments: list[Path], target: Path, *, fade_s: float = FADE_S) -> dict[str, Any]:
    """The PNG frame sequences in ``segments``, crossfaded in order, as H.264 at ``target``."""

    encoder = ffmpeg()
    lengths = [len(list(d.glob("*.png"))) / FPS for d in segments]
    argv = [encoder, "-v", "error", "-nostdin", "-y"]
    for directory in segments:
        argv += ["-framerate", str(FPS), "-i", str(directory / "%05d.png")]
    if len(segments) == 1:
        graph, label = "[0:v]" + TO_VIDEO + "[v]", "[v]"
    else:
        parts, previous, offset = [], "[0:v]", 0.0
        for k in range(1, len(segments)):
            offset += lengths[k - 1] - fade_s
            label = f"[x{k}]"
            parts.append(f"{previous}[{k}:v]xfade=transition=fade:duration={fade_s}:offset={offset:.4f}{label}")
            previous = label
        parts.append(f"{previous}{TO_VIDEO}[v]")
        graph, label = ";".join(parts), "[v]"
    partial = target.with_name(target.stem + ".partial.mp4")
    # The frames carry a fine dither (hero.js) so the dark sky and the fog fade do not band in
    # 8 bits; `tune grain` and adaptive quantisation keep x264 from smoothing it away.
    argv += ["-filter_complex", graph, "-map", label, "-an", "-c:v", "libx264", "-preset", "slow",
             "-tune", "grain", "-x264-params", "aq-mode=3", "-crf", "15", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
             "-color_range", "tv", "-r", str(FPS), "-movflags", "+faststart", str(partial)]
    result = subprocess.run(argv, capture_output=True, timeout=1800)
    if result.returncode != 0:
        partial.unlink(missing_ok=True)
        raise HeroError("FFmpeg failed: " + result.stderr.decode("utf-8", "replace")[-400:])
    partial.replace(target)
    seconds = sum(lengths) - fade_s * (len(segments) - 1)
    return {"file": target.name, "bytes": target.stat().st_size, "seconds": round(seconds, 3), "fps": FPS,
            "codec": "H.264 (libx264, crf 15, tune grain, aq-mode 3), yuv420p, BT.709 limited range"}


def make_dashboard(stage: Stage, out: Path) -> dict[str, Any]:
    """The dashboard as a person sees it, viewport left and Status (training) right."""

    width, height = DASHBOARD["size"]
    page = stage.browser.page("about:blank")
    page.send("Emulation.setDeviceMetricsOverride", {"width": width, "height": height,
                                                     "deviceScaleFactor": DASHBOARD["scale"], "mobile": False})
    layout = {"dir": "row", "sizes": [0.5, 0.5], "children": [{"editor": "view3d"}, {"editor": "training"}]}
    # The layout is this browser's own (the layout key, §12), set before the page's scripts read it.
    page.send("Page.enable")
    page.send("Page.addScriptToEvaluateOnNewDocument", {"source": "try { localStorage.setItem(%s, %s); } catch (e) {}" % (
        json.dumps(LAYOUT_KEY), json.dumps(json.dumps(layout)))})
    page.send("Page.navigate", {"url": stage.server.url})
    page.wait_for("document.readyState === 'complete' && !!window.cadexReview", timeout=120)
    page.evaluate("window.cadexReview.ready", await_promise=True, timeout=LOAD_TIMEOUT_S)
    # The accepted design, chosen by hand so a training run does not turn the viewport to itself.
    page.evaluate("window.cadexReview.setSource('accepted')")
    page.wait_for("['loaded','missing','error'].includes(document.getElementById('model-status').dataset.state)",
                  timeout=LOAD_TIMEOUT_S)
    deadline = time.monotonic() + DASHBOARD["settle_s"]
    while time.monotonic() < deadline and not page.evaluate(
            "document.querySelectorAll('#training-charts .chart-line').length > 0"):
        time.sleep(0.5)
    page.evaluate("window.cadexReview.viewer().fit()")
    time.sleep(1.0)
    path = out / "dashboard.png"
    shot = page.send("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False}, timeout=120)
    path.write_bytes(base64.b64decode(shot["data"]))
    charts = page.evaluate("document.querySelectorAll('#training-charts .chart-line').length")
    stage_state = page.evaluate("(document.getElementById('status-stage')||{}).textContent || ''")
    return {"file": path.name, "size": [width * DASHBOARD["scale"], height * DASHBOARD["scale"]],
            "layout": layout, "charts": charts, "stage": stage_state.strip(),
            "model": page.evaluate("document.getElementById('model-status').dataset.state")}


def current_sheet(root: Path) -> Path | None:
    """The concept sheet of the accepted revision, when a render already drew it."""

    accepted = accepted_model(root)
    shown = presentation(root, {"available": accepted.get("available"), "revision": accepted.get("revision")})
    if shown.get("available") and shown.get("relation") == "current":
        path = root / shown["source"] / "sheet.png"
        if path.is_file():
            return path
    return None


def make(root: Path | str, *, out: Path | None = None, run: str | None = None,
         only: tuple[str, ...] = DEFAULT_ITEMS, gpu: bool = True, focus: str = FOCUS,
         sheet: Callable[[Path], dict[str, Any]] | None = None,
         progress: Callable[[str], None] = lambda message: None) -> dict[str, Any]:
    """Write the hero folder; returns what ``hero.json`` says."""

    root = Path(root).expanduser().resolve()
    target = hero_dir(root, out)
    target.mkdir(parents=True, exist_ok=True)
    # Bulk drawn from the design, not the design: kept out of the project's history.
    (target / ".gitignore").write_text("# Written by cadex hero (ADR-677); it draws all of this again.\n*\n", encoding="utf-8")
    started = time.monotonic()
    accepted = accepted_model(root)
    manifest: dict[str, Any] = {
        "schema": SCHEMA, "project": root.name, "made_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "revision": accepted.get("revision"), "digest": accepted.get("digest"),
        "requested": list(only), "items": {}, "errors": {},
    }
    if not accepted.get("available"):
        manifest["errors"]["model"] = "no accepted model: " + str(accepted.get("reason"))
    # A partial run (--only) keeps what the folder already says of the items it does not remake.
    try:
        previous = json.loads((target / "hero.json").read_text())
    except (OSError, ValueError):
        previous = {}
    if previous.get("schema") == SCHEMA:
        for block in ("items", "errors"):
            for key, value in (previous.get(block) or {}).items():
                if key in ITEMS and key not in only:
                    manifest[block][key] = value

    def attempt(key: str, work: Callable[[], Any]) -> None:
        if key not in only:
            return
        progress(f" · {key}")
        began = time.monotonic()
        try:
            manifest["items"][key] = work()
        except Exception as exc:  # noqa: BLE001 - each item stands alone
            manifest["errors"][key] = f"{type(exc).__name__}: {exc}"
        else:
            if isinstance(manifest["items"][key], dict):
                manifest["items"][key]["seconds_to_make"] = round(time.monotonic() - began, 1)

    def make_sheet() -> dict[str, Any]:
        found = current_sheet(root)
        if found is None:
            if sheet is None:
                raise HeroError("no concept sheet of the accepted revision: run cadex render")
            facts = sheet(root)
            found = current_sheet(root)
            if found is None:
                raise HeroError("the render drew no concept sheet of the accepted revision")
        else:
            facts = {"drawn": False}
        shutil.copyfile(found, target / "sheet.png")
        return {"file": "sheet.png", "source": str(found.relative_to(root)), **facts}

    attempt("sheet", make_sheet)
    choice = curves = None
    if "rollout" in only or "video" in only:
        try:
            choice = choose_rollout(root, run)
        except Exception as exc:  # noqa: BLE001
            manifest["errors"]["rollout_choice"] = f"{type(exc).__name__}: {exc}"
        manifest["rollout_choice"] = choice
    if "video" in only:
        curves = training_curves(root, (choice or {}).get("run") or run)
    needs_page = bool(set(only) & PAGE_ITEMS) and accepted.get("available")
    if needs_page:
        try:
            stage = Stage(root, gpu=gpu, progress=progress)
        except Exception as exc:  # noqa: BLE001
            for key in set(only) & PAGE_ITEMS:
                manifest["errors"][key] = f"{type(exc).__name__}: {exc}"
            stage = None
        if stage is not None:
            try:
                with tempfile.TemporaryDirectory(prefix=".hero-", dir=target) as scratch:
                    work = Path(scratch)
                    attempt("stills", lambda: {"files": make_stills(stage, target)})
                    attempt("views", lambda: make_views(stage, target, focus))
                    manifest["renderer"] = stage.renderer
                    # The page holds one model at a time, so the order is the accepted design's
                    # work (stills, both turns), then the run's (the rollouts), then the curves.
                    videos: dict[str, dict[str, Any]] = {}
                    segments: dict[str, list[Path]] = {}
                    if "video" in only:
                        began = time.monotonic()
                        try:
                            for name, (width, height) in FORMATS.items():
                                progress(f" · video: the turn, {name} {width}x{height}")
                                segments[name] = [_frames(work, f"{name}-turn")]
                                videos[name] = {"size": [width, height], "parts": {
                                    "turntable": turntable_frames(stage, segments[name][0], width, height)}}
                                progress(f" · video: the wireframe turn, {name}")
                                wire = _frames(work, f"{name}-wire")
                                turn = turntable_frames(stage, wire, width, height, WIRE_TURN)
                                videos[f"wireframe-{name}"] = {"size": [width, height], "parts": {"turntable": turn},
                                                               **encode([wire], target / f"hero-wireframe-{name}.mp4")}
                        except Exception as exc:  # noqa: BLE001
                            manifest["errors"]["video"] = f"{type(exc).__name__}: {exc}"
                            videos = {}

                    def make_rollout() -> dict[str, Any]:
                        if choice is None:
                            raise HeroError("no playable rollout: no run kept one")
                        directory = _frames(work, "rollout")
                        width, height = FORMATS["landscape"]
                        facts = rollout_frames(stage, choice, directory, width, height, clock=True, limit_s=None)
                        return {**encode([directory], target / "rollout.mp4"), **facts, "choice": choice,
                                "size": [width, height]}

                    attempt("rollout", make_rollout)
                    if videos:
                        try:
                            for name, (width, height) in FORMATS.items():
                                if choice is not None:
                                    progress(f" · video: the rollout, {name}")
                                    segments[name].append(_frames(work, f"{name}-rollout"))
                                    videos[name]["parts"]["rollout"] = rollout_frames(
                                        stage, choice, segments[name][-1], width, height, clock=False,
                                        limit_s=ROLLOUT["clip_s"])
                                if curves is not None:
                                    progress(f" · video: the training curves, {name}")
                                    segments[name].append(_frames(work, f"{name}-plot"))
                                    videos[name]["parts"]["plot"] = plot_frames(
                                        stage, curves, segments[name][-1], width, height, f"{root.name} · training")
                                progress(f" · video: encoding hero-{name}.mp4")
                                videos[name].update(encode(segments[name], target / f"hero-{name}.mp4"))
                            videos["seconds_to_make"] = round(time.monotonic() - began, 1)
                            manifest["items"]["video"] = videos
                        except Exception as exc:  # noqa: BLE001
                            manifest["errors"]["video"] = f"{type(exc).__name__}: {exc}"
                    attempt("dashboard", lambda: make_dashboard(stage, target))
            finally:
                stage.close()
    elif needs_page is False and set(only) & PAGE_ITEMS and not accepted.get("available"):
        for key in set(only) & PAGE_ITEMS:
            manifest["errors"].setdefault(key, manifest["errors"]["model"])
    manifest["seconds"] = round(time.monotonic() - started, 1)
    manifest["style_sha256"] = _style_digest()
    partial = target / "hero.json.partial"
    partial.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    partial.replace(target / "hero.json")
    return manifest


def _style_digest() -> str:
    """Identity of the shipped page code that determines the pixels."""

    import hashlib
    h = hashlib.sha256()
    for name in ("hero.html", "hero.js", "review_scene.js", "shading.js", "environment.js", "floor.js",
                 "three.module.js", "stl.js"):
        h.update(name.encode())
        h.update((STATIC_DIR / name).read_bytes())
    return h.hexdigest()


#: A grid tile's label: the project's name, top left, in the dark page's ink on its mat.
LABEL = "font=Sans:fontcolor=0xededed:fontsize=h/24:x=h/40:y=h/40:box=1:boxcolor=0x141414@0.7:boxborderw=10"


def _label_text(text: str) -> str:
    """``text`` escaped for drawtext's value inside a filtergraph."""

    return "".join("\\" + ch if ch in "\\':,;[]=%" else ch for ch in text)


def grid(projects: list[Path], out: Path, *, still: str = "wireframe", columns: int = 2,
         tile_width: int | None = None) -> dict[str, Any]:
    """Tile each project's ``hero/still-<still>.png`` (or ``view-<still>.png``, ADR-792) into one
    image, ``columns`` to a row, in reading order (left to right, top to bottom), each labelled with
    its project's name. The images are all one size, so the tiles line up; ``tile_width`` scales
    each tile to that many pixels wide."""

    if not projects:
        raise HeroError("hero-grid needs at least one project")
    images = []
    for root in projects:
        folder = hero_dir(Path(root).expanduser())
        path = next((folder / f"{kind}-{still}.png" for kind in ("still", "view")
                     if (folder / f"{kind}-{still}.png").is_file()), None)
        if path is None:
            raise HeroError(f"{folder}/still-{still}.png and view-{still}.png are missing: run "
                            f"cadex hero --project {root} --only stills (or views)")
        images.append(path)
    out = Path(out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    encoder = ffmpeg()
    argv = [encoder, "-v", "error", "-nostdin", "-y"]
    for path in images:
        argv += ["-i", str(path)]
    columns = max(1, min(columns, len(images)))
    rows = math.ceil(len(images) / columns)
    pad = rows * columns - len(images)
    scale = f"scale={int(tile_width)}:-2" if tile_width else "null"
    parts = [f"[{k}:v]{scale}[s{k}]" for k in range(len(images))]
    if pad:
        # A missing last tile is the dark mat, the first tile's size, so the grid stays a rectangle.
        parts[0] = parts[0][:-len("[s0]")] + "[s0a]"
        parts.append(f"[s0a]split={pad + 1}[s0]" + "".join(f"[b{j}]" for j in range(pad)))
        parts += [f"[b{j}]drawbox=c=0x141414:t=fill[blank{j}]" for j in range(pad)]
    parts += [f"[s{k}]drawtext=text='{_label_text(Path(root).expanduser().name)}':{LABEL}[t{k}]"
              for k, root in enumerate(projects)]
    inputs = [f"[t{k}]" for k in range(len(images))] + [f"[blank{j}]" for j in range(pad)]
    layout = "|".join(("+".join(["w0"] * (k % columns)) or "0") + "_" + ("+".join(["h0"] * (k // columns)) or "0")
                      for k in range(rows * columns))
    graph = ";".join(parts + ["".join(inputs) + f"xstack=inputs={rows * columns}:layout={layout}[v]"])
    argv += ["-filter_complex", graph, "-map", "[v]", "-frames:v", "1", str(out)]
    result = subprocess.run(argv, capture_output=True, timeout=300)
    if result.returncode != 0:
        raise HeroError("FFmpeg failed: " + result.stderr.decode("utf-8", "replace")[-400:])
    return {"file": str(out), "still": still, "columns": columns, "rows": rows,
            "projects": [Path(p).expanduser().name for p in projects]}
