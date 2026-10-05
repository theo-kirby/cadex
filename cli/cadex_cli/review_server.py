# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The one-project review dashboard server (ADR-286).

``cadex review --project DIR`` serves **one** project, read-only, to a
browser on the machine's private network: the accepted identity now, every
run as recorded (ADR-285), the parameters and specs each run was made
under, the retained artifacts, and the model itself — the per-output
meshes a run's rollout leg exported, placed where the rollout trace's
first frame put them, or the accepted attempt's own tessellation for the
project as it stands now — and each evaluation of a policy against its
task's success spec, with the film drawn from it (ADR-459). Reading
opens no engine, rebuilds nothing and holds no state of its own, so a
browser that goes away changes nothing about the project.

It has no write route at all (ADR-537): a request other than GET or HEAD
is refused. The project changes only through the agent that is working
it -- the CLI, or ``cadex mcp`` -- and the page follows on its next poll.

What it will serve is an allowlist, never a path. Every route names a run
by its directory name, an artifact by its record key, a document by the
relative name its record lists, a mesh by the output it belongs to; each is
looked up in what the reader returned and resolved through the same
containment check the reader applies (:func:`resolve_reference`). A
request for anything else — a path the record does not name, a file that
escapes its base, a run that does not exist — is a 404 that says so, and
no filesystem path in the request is ever joined onto the project root.

The page is plain HTML and JavaScript under ``review_static/`` with no
framework. Its shared viewport/video scene uses a shipped, pinned Three.js
module and an attributed prototype environment (ADR-301), with no CDN.
"""

from __future__ import annotations

from array import array
from collections import OrderedDict
import copy
import datetime as _datetime
import hashlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import mimetypes
import re
from pathlib import Path
import struct
import sys
import threading
import zlib
from typing import Any, Callable, Mapping
from urllib.parse import quote, unquote, urlsplit
from xml.etree import ElementTree

from .checkpoints import FAILURE_SUFFIX as CHECKPOINT_FAILURE_SUFFIX
from .checkpoints import TRACE_SUFFIX as CHECKPOINT_TRACE_SUFFIX
from .revisions import read_history as read_revision_history
from .session import read_agent_state
from .studio import PRINTABLES, STUDIO
from .review_record import (
    policy_lineage,
    PROJECT_ARTIFACT_KEYS,
    PROJECT_SCRIPT_FILENAME,
    PROJECT_SCRIPT_SCHEMA,
    RUN_ARTIFACT_KEYS,
    RUNS_DIRNAME,
    read_accepted_identity,
    read_project_review,
    read_run_record,
    resolve_reference,
    run_disk_use,
)

REVIEW_MODEL_SCHEMA = "cadex-review-model-v1"
STATIC_DIR = Path(__file__).resolve().parent / "review_static"
#: The page's files, by the name the browser asks for. A name not in this
#: table is not served, whatever is in the directory.
STATIC_FILES = {
    "index.html": ("text/html; charset=utf-8", STATIC_DIR / "index.html"),
    "review.css": ("text/css; charset=utf-8", STATIC_DIR / "review.css"),
    "review.js": ("text/javascript; charset=utf-8", STATIC_DIR / "review.js"),
    **{name: ("text/javascript; charset=utf-8", STATIC_DIR / name) for name in
       ("three.module.js", "floor.js", "environment.js", "review_scene.js", "stl.js", "capture.js",
        "layout.js", "theme.js")},
    "capture.html": ("text/html; charset=utf-8", STATIC_DIR / "capture.html"),
    "viewer.js": ("text/javascript; charset=utf-8", STATIC_DIR / "viewer.js"),
}
#: The projects index's own files (``cadex app``); the review page's files
#: are served too, so the index shares its stylesheet.
PROJECTS_STATIC_FILES = {
    **STATIC_FILES,
    "projects.html": ("text/html; charset=utf-8", STATIC_DIR / "projects.html"),
    "projects.js": ("text/javascript; charset=utf-8", STATIC_DIR / "projects.js"),
}
PROJECTS_SCHEMA = "cadex-projects-v1"
#: Content types for the retained artifacts; anything else downloads as bytes.
CONTENT_TYPES = {
    ".json": "application/json; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".py": "text/x-python; charset=utf-8",
    ".xml": "application/xml; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".stl": "model/stl",
    ".step": "model/step",
    ".brep": "application/octet-stream",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".txt": "text/plain; charset=utf-8",
    ".jsonl": "text/plain; charset=utf-8",
    ".csv": "text/plain; charset=utf-8",
}
TESSELLATION_SCHEMA = "cadex-tessellation-v1"
TRACE_SCHEMA = "cadex-assembly-simulation-trace-v1"
#: Bound on any single file the server will read into memory to serve; a
#: video or trace past this is streamed, a JSON past this is refused.
JSON_READ_LIMIT = 64 * 1024 * 1024


def _now() -> str:
    return (
        _datetime.datetime.now(_datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _load_json(path: Path, limit: int = JSON_READ_LIMIT) -> dict[str, Any] | None:
    try:
        if path.stat().st_size > limit:
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


#: Where ``cadex render`` leaves the project's presentation (ADR-430): the
#: studio hero and the concept sheet, beside the summary that names them. A
#: walk renders per revision, under ``review/render/<revision>/``.
PRESENTATION_DIR = "review/render"
PRESENTATION_FILES = ("hero", "sheet")


def _presentation_source(root: Path, accepted: Mapping[str, Any]) -> tuple[str, dict[str, Any] | None]:
    """``(relative directory, summary)`` of the render to present.

    The accepted revision's own walk render when it drew a sheet, else the
    project's last ``cadex render``, whatever revision it drew; a render
    with a sheet is preferred over one without.
    """

    candidates = [PRESENTATION_DIR]
    revision = accepted.get("revision") if accepted.get("available") else None
    if isinstance(revision, str) and len(revision) == 64 and revision.isalnum():
        candidates.insert(0, f"{PRESENTATION_DIR}/{revision}")
    found = []
    for relative in candidates:
        summary = _load_json(root / relative / "summary.json")
        if summary and isinstance(summary.get("revision"), str):
            found.append((relative, summary))
    with_sheet = [item for item in found if isinstance(item[1].get("sheet"), dict)]
    return (with_sheet or found or [(PRESENTATION_DIR, None)])[0]


def presentation(project_root: Path | str, accepted: Mapping[str, Any]) -> dict[str, Any]:
    """The project's studio hero and concept sheet, as a render left them.

    Read from the render's ``summary.json`` (:func:`_presentation_source`);
    an image is offered only when the summary names it at its own path and
    the file is there. The block carries the render's revision and its
    relation to the accepted revision now -- ``current``, ``historical`` or
    ``unknown`` -- so a sheet drawn for an earlier design never reads as
    this one. Read-only: a project with no render, or a render from before
    the sheet, says so and what makes one.
    """

    root = Path(project_root).expanduser()
    relative, summary = _presentation_source(root, accepted)
    if summary is None:
        return {"available": False, "reason": "no render yet: cadex render draws the hero and the sheet"}
    files: dict[str, dict[str, Any]] = {}
    for key in PRESENTATION_FILES:
        block = summary.get(key)
        path = root / relative / f"{key}.png"
        if isinstance(block, dict) and block.get("path") == f"{relative}/{key}.png" and path.is_file():
            files[key] = {"url": f"presentation/{key}.png", "bytes": path.stat().st_size}
    revision = summary["revision"]
    if accepted.get("available"):
        relation = "current" if revision == accepted.get("revision") else "historical"
    else:
        relation = "unknown"
    result: dict[str, Any] = {
        "available": "sheet" in files,
        "revision": revision,
        "digest": summary.get("digest"),
        "relation": relation,
        "source": relative,
        "files": files,
    }
    sheet = summary.get("sheet")
    if isinstance(sheet, dict):
        result["numbers"] = sheet.get("numbers")
        result["palette"] = summary.get("palette")
    else:
        result["reason"] = "this render predates the concept sheet: run cadex render again"
    return result


def _placement(entry: Any) -> dict[str, list[float]] | None:
    """A ``{position_mm, rotation_xyzw}`` block, validated, or None."""

    if not isinstance(entry, Mapping):
        return None
    position = entry.get("position_mm", entry.get("position"))
    rotation = entry.get("rotation_xyzw", entry.get("rotation"))
    try:
        position = [float(x) for x in position]
        rotation = [float(x) for x in rotation]
    except (TypeError, ValueError):
        return None
    if len(position) != 3 or len(rotation) != 4:
        return None
    if not all(math.isfinite(x) for x in position + rotation):
        return None
    return {"position_mm": position, "rotation_xyzw": rotation}


def _matrix_placement(matrix: Any) -> dict[str, list[float]] | None:
    """A row-major 4x4 ``solved_placement_matrix`` as ``{position_mm, rotation_xyzw}``, or None."""

    try:
        m = [float(x) for x in matrix]
    except (TypeError, ValueError):
        return None
    if len(m) != 16 or not all(math.isfinite(x) for x in m):
        return None
    r = [[m[0], m[1], m[2]], [m[4], m[5], m[6]], [m[8], m[9], m[10]]]
    trace = r[0][0] + r[1][1] + r[2][2]
    if trace > 0:
        s = 2.0 * math.sqrt(trace + 1.0)
        q = [(r[2][1] - r[1][2]) / s, (r[0][2] - r[2][0]) / s, (r[1][0] - r[0][1]) / s, s / 4]
    elif r[0][0] > r[1][1] and r[0][0] > r[2][2]:
        s = 2.0 * math.sqrt(1.0 + r[0][0] - r[1][1] - r[2][2])
        q = [s / 4, (r[0][1] + r[1][0]) / s, (r[0][2] + r[2][0]) / s, (r[2][1] - r[1][2]) / s]
    elif r[1][1] > r[2][2]:
        s = 2.0 * math.sqrt(1.0 + r[1][1] - r[0][0] - r[2][2])
        q = [(r[0][1] + r[1][0]) / s, s / 4, (r[1][2] + r[2][1]) / s, (r[0][2] - r[2][0]) / s]
    else:
        s = 2.0 * math.sqrt(1.0 + r[2][2] - r[0][0] - r[1][1])
        q = [(r[0][2] + r[2][0]) / s, (r[1][2] + r[2][1]) / s, s / 4, (r[1][0] - r[0][1]) / s]
    norm = math.sqrt(sum(x * x for x in q)) or 1.0
    return {"position_mm": [m[3], m[7], m[11]], "rotation_xyzw": [x / norm for x in q]}


def exploded_views(result: Mapping[str, Any], assembled: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Each ``assembly.exploded_view`` output as pose frames for the viewer (orun2 D2.5).

    The engine computed the explosion: every staged move's cumulative poses
    and the leader lines, published on the output as ``exploded_view``
    (``_exploded_display_record``). Frame 0 is the model as the viewer
    places it (``assembled``, component name to placement); frame *k* is
    frame *k-1* with stage *k*'s poses applied, so a component a stage does
    not move keeps where it was. The last frame is the engine's
    ``final_poses``, which the page's test checks. Nothing is computed here
    but that bookkeeping; the page interpolates between frames.
    """

    views: list[dict[str, Any]] = []
    for item in result.get("outputs") or []:
        record = item.get("exploded_view") if isinstance(item, Mapping) else None
        if not isinstance(record, Mapping) or not isinstance(record.get("stages"), list):
            continue
        frame = {name: placement for name, placement in assembled.items() if placement is not None}
        frames = [dict(frame)]
        for stage in record["stages"]:
            for name, pose in ((stage or {}).get("poses") or {}).items():
                placement = _placement({"position_mm": (pose or {}).get("position_mm"),
                                        "rotation_xyzw": (pose or {}).get("quaternion_xyzw")})
                if placement is not None:
                    frame[str(name)] = placement
            frames.append(dict(frame))
        lines = [{"component": str(line.get("component_output")),
                  "start_mm": [float(x) for x in line.get("start_mm") or []],
                  "end_mm": [float(x) for x in line.get("end_mm") or []]}
                 for line in record.get("lines") or [] if isinstance(line, Mapping)]
        views.append({
            "output": str(item.get("name")), "assembly_output": record.get("assembly_output"),
            "stages": len(record["stages"]), "frames": frames,
            "lines": [line for line in lines if len(line["start_mm"]) == 3 and len(line["end_mm"]) == 3],
            "source": f"the accepted attempt's {item.get('name')} (assembly.exploded_view): the engine's "
                      "staged moves from the solved pose, with its leader lines",
        })
    return views


def _first_frame_placements(trace: Mapping[str, Any] | None) -> tuple[dict[str, dict[str, list[float]]], list[str]]:
    """Component placements at a trace's first frame, and its component list."""

    if not trace or trace.get("schema") != TRACE_SCHEMA:
        return {}, []
    frames = trace.get("frames") or []
    placements: dict[str, dict[str, list[float]]] = {}
    if frames and isinstance(frames[0], Mapping):
        for name, entry in (frames[0].get("component_placements") or {}).items():
            block = _placement(entry)
            if block is not None:
                placements[str(name)] = block
    components = [str(name) for name in trace.get("component_outputs") or []]
    return placements, components


def trace_playback(trace: Mapping[str, Any] | None) -> dict[str, Any]:
    """A rollout or simulation trace as the viewer's playback (orun2 D2.5).

    Frames are the trace's timed ones (``nominal_time_s``), in time order:
    the untimed input frame in front of t=0 is the reset pose again and is
    left out, so the page plays seconds and not frame numbers. Each
    component's quaternion keeps its sign from the frame before (``q`` and
    ``-q`` are one rotation, and a flip between them would make the page's
    interpolation take the long way round). A frame's ``actuator_commands``
    is the command that produced it and holds until the next frame's (zero
    order hold); the reset frame has none and says so with ``None``.
    Nothing here is simulated: every placement is the trace's own.
    """

    if not trace or trace.get("schema") != TRACE_SCHEMA:
        return {"available": False, "reason": "the trace is unreadable, past the read bound, or not a " + TRACE_SCHEMA}
    timed: list[tuple[float, Mapping[str, Any]]] = []
    for frame in trace.get("frames") or []:
        if not isinstance(frame, Mapping):
            continue
        try:
            time_s = float(frame.get("nominal_time_s"))
        except (TypeError, ValueError):
            continue
        if math.isfinite(time_s):
            timed.append((time_s, frame))
    timed.sort(key=lambda item: item[0])
    times: list[float] = []
    frames: list[dict[str, dict[str, list[float]]]] = []
    commands: list[list[float] | None] = []
    previous: dict[str, list[float]] = {}
    for time_s, frame in timed:
        poses: dict[str, dict[str, list[float]]] = {}
        for name, entry in (frame.get("component_placements") or {}).items():
            block = _placement(entry)
            if block is None:
                continue
            q, before = block["rotation_xyzw"], previous.get(str(name))
            if before is not None and sum(a * b for a, b in zip(q, before)) < 0:
                block["rotation_xyzw"] = [-x for x in q]
            previous[str(name)] = block["rotation_xyzw"]
            poses[str(name)] = block
        if not poses:
            continue
        times.append(time_s)
        frames.append(poses)
        raw = frame.get("actuator_commands")
        commands.append([float(x) for x in raw] if isinstance(raw, list) else None)
    if not frames:
        return {"available": False, "reason": "the trace has no timed frames with placements"}
    channels = [{"actuator": str(c.get("actuator")), "unit": str(c.get("unit")),
                 "low": c.get("low"), "high": c.get("high")}
                for c in trace.get("actuator_channels") or [] if isinstance(c, Mapping)]
    return {"available": True, "times_s": times, "frames": frames, "commands": commands,
            "channels": channels, "duration_s": times[-1] - times[0],
            "frames_per_second": (trace.get("parameters") or {}).get("frames_per_second")}


def _run_trace(root: Path, record: Mapping[str, Any]) -> tuple[Path | None, str | None]:
    """The run's own rollout trace on disk, or why there is none."""

    run_ref = resolve_reference(root, f"{RUNS_DIRNAME}/{record.get('run')}")
    if run_ref["error"] or not run_ref["exists"]:
        return None, "run directory escapes the project directory" if run_ref["error"] else "run directory missing"
    item = ((record.get("resolved") or {}).get("artifacts") or {}).get("trace") or {}
    if item.get("path") is None:
        return None, "this run retained no rollout trace"
    if item.get("error"):
        return None, f"trace reference not honoured: {item['error']}"
    if not item.get("exists"):
        return None, f"rollout trace missing: {item['path']}"
    return root / RUNS_DIRNAME / str(record.get("run")) / item["path"], None


def run_playback(project_root: Path | str, record: Mapping[str, Any]) -> dict[str, Any]:
    """``/api/playback/run/<name>``: the run's rollout trace as playback frames."""

    root = Path(project_root).expanduser()
    path, reason = _run_trace(root, record)
    playback = trace_playback(_load_json(path)) if path is not None else {"available": False, "reason": reason}
    playback.update(run=str(record.get("run")),
                    source=path.relative_to(root).as_posix() if path is not None else None)
    return playback


# -- checkpoint rollouts: training as motion (ADR-544 writes them, ADR-545 shows them) --

#: ``walk.000040.rollout-trace.json`` and its siblings: the output, the
#: numbered tag, and which of the three files it is.
_CHECKPOINT_FILE = re.compile(r"(?P<stem>(?P<output>.+)\.(?P<tag>\d+))"
                              r"(?P<kind>\.cxpolicy|" + re.escape(CHECKPOINT_TRACE_SUFFIX)
                              + "|" + re.escape(CHECKPOINT_FAILURE_SUFFIX) + ")")
#: The newest checkpoints the stage lists; older ones stay on disk.
CHECKPOINTS_LISTED = 64
#: What one checkpoint's trace says of itself, kept per file identity so
#: a poll reparses no trace that did not change.
_CHECKPOINT_MEMO: "OrderedDict[str, tuple[tuple[int, int] | None, dict[str, Any]]]" = OrderedDict()
_CHECKPOINT_MEMO_SIZE = 512


def _checkpoint_dir(root: Path, run: str) -> Path | None:
    """``runs/<run>/train`` when it resolves inside the project, else ``None``."""

    ref = resolve_reference(root, f"{RUNS_DIRNAME}/{run}/train")
    if ref["error"] or not ref["exists"] or not (root / ref["path"]).is_dir():
        return None
    return root / ref["path"]


def _checkpoint_head(path: Path) -> dict[str, Any]:
    """A trace's ``checkpoint`` block and its length, or a failure record's
    reason, read once per file identity."""

    key = _stat_key(path)
    with _MEMO_LOCK:
        held = _CHECKPOINT_MEMO.get(str(path))
        if held is not None and held[0] == key:
            _CHECKPOINT_MEMO.move_to_end(str(path))
            return held[1]
    data = _load_json(path) or {}
    if path.name.endswith(CHECKPOINT_FAILURE_SUFFIX):
        head = {"state": "failed", "iteration": data.get("iteration"), "reward_per_step": None,
                "sha256": None, "reason": str(data.get("reason") or "unreadable failure record")[:120],
                "error": str(data.get("error") or "")[:300]}
    else:
        block = data.get("checkpoint") if isinstance(data.get("checkpoint"), Mapping) else {}
        playback = trace_playback(data)
        head = {"state": "ready" if playback["available"] else "failed",
                "iteration": block.get("iteration"), "reward_per_step": block.get("reward_per_step"),
                "sha256": block.get("sha256"),
                "reason": "" if playback["available"] else "unplayable_trace",
                "error": "" if playback["available"] else playback["reason"],
                "duration_s": playback.get("duration_s")}
    for name in ("iteration", "reward_per_step", "duration_s"):
        value = head.get(name)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                  or not math.isfinite(value)):
            head[name] = None
    with _MEMO_LOCK:
        _CHECKPOINT_MEMO[str(path)] = (key, head)
        _CHECKPOINT_MEMO.move_to_end(str(path))
        while len(_CHECKPOINT_MEMO) > _CHECKPOINT_MEMO_SIZE:
            _CHECKPOINT_MEMO.popitem(last=False)
    return head


def checkpoint_rollouts(project_root: Path | str, run: str) -> dict[str, Any]:
    """A run's checkpoints as the 3D viewport scrubs them (ADR-545).

    One item per numbered checkpoint that has been rolled out, oldest
    first: ``ready`` with the URL of its playback, or ``failed`` with the
    reason its failure record (or an unplayable trace) gives. ``pending``
    counts the checkpoints on disk with neither yet -- the watcher has not
    reached them. Only regular files in the run's own ``train/`` are read;
    a checkpoint is never borrowed from another run.
    """

    root = Path(project_root).expanduser()
    train = _checkpoint_dir(root, run)
    if train is None:
        return {"run": run, "items": [], "pending": 0, "listed_of": 0,
                "reason": "the run has no train directory"}
    found: dict[str, dict[str, Any]] = {}
    for path in train.iterdir():
        match = _CHECKPOINT_FILE.fullmatch(path.name)
        if match is None or path.is_symlink() or not path.is_file():
            continue
        entry = found.setdefault(match["stem"], {"stem": match["stem"], "tag": match["tag"],
                                                 "kinds": set()})
        entry["kinds"].add(match["kind"])
    items, pending = [], 0
    for stem, entry in found.items():
        kinds = entry.pop("kinds")
        if CHECKPOINT_TRACE_SUFFIX in kinds:
            head = _checkpoint_head(train / (stem + CHECKPOINT_TRACE_SUFFIX))
        elif CHECKPOINT_FAILURE_SUFFIX in kinds:
            head = _checkpoint_head(train / (stem + CHECKPOINT_FAILURE_SUFFIX))
        else:
            pending += 1
            continue
        item = {**entry, **head}
        if item["iteration"] is None:
            item["iteration"] = int(entry["tag"]) - 1
        item["url"] = (f"/api/playback/checkpoint/{quote(run, safe='')}/{quote(stem, safe='')}"
                       if head["state"] == "ready" else None)
        items.append(item)
    items.sort(key=lambda item: (int(item["tag"]), item["stem"]))
    return {"run": run, "items": items[-CHECKPOINTS_LISTED:], "pending": pending,
            "listed_of": len(items), "reason": "" if items or pending else "no checkpoint rolled out yet"}


def checkpoint_playback(project_root: Path | str, run: str, stem: str) -> dict[str, Any] | None:
    """``/api/playback/checkpoint/<run>/<stem>``: one checkpoint's rollout
    as playback frames, with what the trainer said of it; ``None`` when
    the name is not a checkpoint this run's ``train/`` holds."""

    root = Path(project_root).expanduser()
    match = _CHECKPOINT_FILE.fullmatch(stem + CHECKPOINT_TRACE_SUFFIX)
    train = _checkpoint_dir(root, run)
    if match is None or match["stem"] != stem or train is None:
        return None
    path = train / (stem + CHECKPOINT_TRACE_SUFFIX)
    if path.is_symlink() or not path.is_file():
        failure = train / (stem + CHECKPOINT_FAILURE_SUFFIX)
        if failure.is_symlink() or not failure.is_file():
            return None
        head = _checkpoint_head(failure)
        return {"available": False, "reason": f"{head['reason']}: {head['error']}", "run": run,
                "stem": stem, "checkpoint": head, "source": failure.relative_to(root).as_posix()}
    trace = _load_json(path)
    playback = trace_playback(trace)
    playback.update(run=run, stem=stem, checkpoint=_checkpoint_head(path),
                    source=path.relative_to(root).as_posix())
    return playback


def _render_sources(root: Path, record: Mapping[str, Any]) -> dict[str, str]:
    """``component -> output`` from the run's render summary, when it resolves."""

    item = ((record.get("resolved") or {}).get("project_artifacts") or {}).get("render") or {}
    if not item.get("exists") or item.get("error"):
        return {}
    summary_path = root / item["path"]
    if summary_path.is_dir():
        summary_path = summary_path / "summary.json"
    summary = _load_json(summary_path)
    if not summary:
        return {}
    sources: dict[str, str] = {}
    for name, entry in (summary.get("objects") or {}).items():
        if isinstance(entry, Mapping) and isinstance(entry.get("source"), str):
            sources[str(name)] = entry["source"]
    return sources


MJCF_READ_LIMIT = 8 * 1024 * 1024
MJCF_ARTIFACT_KIND = "assembly_mjcf_xml"
# MuJoCo geom types the viewer can draw as a proxy outline. A plane is listed
# and never drawn (it is infinite); anything else is listed as unknown.
PROXY_TYPES = ("box", "sphere", "capsule", "cylinder", "mesh", "plane")


def _no_collision(reason: str, source: str | None = None) -> dict[str, Any]:
    return {"available": False, "source": source, "sha256": None, "reason": reason,
            "geoms": [], "components": [], "skipped": 0}


def _floats(value: str | None, count: int, default: list[float]) -> list[float] | None:
    if value is None:
        return list(default)
    try:
        parsed = [float(v) for v in value.split()]
    except ValueError:
        return None
    if len(parsed) < count or not all(math.isfinite(v) for v in parsed):
        return None
    return parsed[:count]


def _quat_from_z(direction: list[float]) -> list[float]:
    """The xyzw rotation taking +Z onto ``direction`` (unit), for ``fromto`` geoms."""

    dz = direction[2]
    if dz > 1 - 1e-9:
        return [0.0, 0.0, 0.0, 1.0]
    if dz < -1 + 1e-9:
        return [1.0, 0.0, 0.0, 0.0]
    axis = [-direction[1], direction[0], 0.0]
    norm = math.hypot(axis[0], axis[1])
    half = math.acos(dz) / 2
    return [axis[0] / norm * math.sin(half), axis[1] / norm * math.sin(half), 0.0, math.cos(half)]


def collision_proxies(path: Path, *, source: str, expected_sha256: str | None = None) -> dict[str, Any]:
    """The collision proxies a retained MJCF declares, per body, in mm and xyzw.

    Read from the file the run (or the accepted attempt) retained at its own
    identity — never regenerated — and refused when a digest the rollout trace
    recorded for its model does not match, so a historical run's proxies are
    the ones it rolled out against. Bodies are named as the trace's components
    are, and every geom is expressed in its body's frame, so the viewer places
    a proxy by the same pose it places the solid. Sizes keep MuJoCo's meaning
    (half-sizes for a box, radius and half-length for a capsule or cylinder,
    radius for a sphere) converted to millimetres; inline mesh assets are
    carried as vertices and faces. Geoms that take part in no contact are
    counted as skipped rather than listed: the toggle shows *collision*
    geometry and nothing else.
    """

    block = _no_collision("", source)
    try:
        if path.is_symlink() or not path.is_file():
            block["reason"] = "retained MJCF is not a regular file"
            return block
        if path.stat().st_size > MJCF_READ_LIMIT:
            block["reason"] = "retained MJCF exceeds the read limit"
            return block
        data = path.read_bytes()
        block["sha256"] = hashlib.sha256(data).hexdigest()
        if expected_sha256 and block["sha256"] != expected_sha256:
            block["reason"] = "retained MJCF is not the model this rollout ran (digest mismatch)"
            return block
        root = ElementTree.fromstring(data)
    except (OSError, ElementTree.ParseError) as exc:
        block["reason"] = f"retained MJCF unreadable: {type(exc).__name__}"
        return block
    if root.tag != "mujoco":
        block["reason"] = "retained MJCF is not a MuJoCo model"
        return block
    meshes: dict[str, tuple[list[float], list[int]] | None] = {}
    for asset in root.iter("mesh"):
        name = asset.get("name")
        vertex, face = asset.get("vertex"), asset.get("face")
        if not name:
            continue
        try:
            vertices = [float(v) * 1000.0 for v in (vertex or "").split()]
            faces = [int(v) for v in (face or "").split()]
        except ValueError:
            meshes[name] = None
            continue
        ok = (vertices and len(vertices) % 3 == 0 and faces and len(faces) % 3 == 0
              and all(math.isfinite(v) for v in vertices)
              and all(0 <= f < len(vertices) // 3 for f in faces))
        meshes[name] = (vertices, faces) if ok else None
    geoms: list[dict[str, Any]] = []
    skipped = 0
    for body in root.iter("body"):
        component = body.get("name")
        if not component:
            continue
        for index, geom in enumerate(child for child in body if child.tag == "geom"):
            contype = _floats(geom.get("contype"), 1, [1.0])
            conaffinity = _floats(geom.get("conaffinity"), 1, [1.0])
            if not contype or not conaffinity or (int(contype[0]) == 0 and int(conaffinity[0]) == 0):
                skipped += 1
                continue
            kind = geom.get("type") or "sphere"
            try:
                size = [float(v) * 1000.0 for v in (geom.get("size") or "").split()]
            except ValueError:
                size = []
            pos = _floats(geom.get("pos"), 3, [0.0, 0.0, 0.0])
            quat = _floats(geom.get("quat"), 4, [1.0, 0.0, 0.0, 0.0])
            entry: dict[str, Any] = {
                "name": geom.get("name") or f"{component}/geom{index}", "component": component,
                "type": kind, "size_mm": size, "pos_mm": None, "rotation_xyzw": None,
                "drawn": kind in PROXY_TYPES and kind != "plane", "note": None,
            }
            fromto = _floats(geom.get("fromto"), 6, []) if geom.get("fromto") else None
            if fromto is not None and len(fromto) == 6:
                a, b = fromto[:3], fromto[3:]
                length = math.dist(a, b)
                if length <= 0:
                    entry.update(drawn=False, note="degenerate fromto")
                else:
                    direction = [(q - p) / length for p, q in zip(a, b)]
                    pos = [(p + q) / 2 for p, q in zip(a, b)]
                    entry["rotation_xyzw"] = _quat_from_z(direction)
                    entry["size_mm"] = [size[0] if size else 0.0, length * 500.0]
            elif quat is not None:
                w, x, y, z = quat
                norm = math.sqrt(w * w + x * x + y * y + z * z) or 1.0
                entry["rotation_xyzw"] = [x / norm, y / norm, z / norm, w / norm]
            if pos is None or entry["rotation_xyzw"] is None:
                entry.update(drawn=False, note="invalid pose")
            else:
                entry["pos_mm"] = [v * 1000.0 for v in pos]
            if kind == "plane":
                entry["note"] = "infinite plane: listed, not drawn"
            elif kind not in PROXY_TYPES:
                entry["note"] = f"unsupported geom type {kind!r}: listed, not drawn"
            elif kind == "mesh":
                asset = meshes.get(geom.get("mesh") or "")
                if asset is None:
                    entry.update(drawn=False, note="mesh asset not inline or invalid")
                else:
                    entry["vertices_mm"], entry["faces"] = asset
            elif not size or any(v <= 0 for v in size[:{"box": 3, "sphere": 1}.get(kind, 2)]):
                entry.update(drawn=False, note="invalid size")
            geoms.append(entry)
    block.update(available=True, geoms=geoms, skipped=skipped,
                 components=sorted({g["component"] for g in geoms}))
    return block


def _run_collision(run_dir: Path, record: Mapping[str, Any], *, expected_sha256: str | None = None) -> dict[str, Any]:
    """The run's own MJCF export, resolved through its record, as proxies."""

    item = ((record.get("resolved") or {}).get("artifacts") or {}).get("model_xml") or {}
    if item.get("path") is None:
        return _no_collision("no MJCF export recorded for this run")
    if item.get("error"):
        return _no_collision(f"MJCF reference not honoured: {item['error']}")
    if not item.get("exists"):
        return _no_collision(f"MJCF export missing: {item['path']}")
    source = f"runs/{run_dir.name}/{item['path']} (this run's own MJCF export at its revision)"
    return collision_proxies(run_dir / item["path"], source=source, expected_sha256=expected_sha256)


def _no_contacts(reason: str) -> dict[str, Any]:
    return {"available": False, "reason": reason, "source": None, "count": 0,
            "omitted": 0, "pairs": []}


def initial_contacts(result: Mapping[str, Any]) -> dict[str, Any]:
    """Which parts' collision shapes touch at rest, from the accepted MJCF export.

    The assembly worker measured it when it exported the model: MuJoCo's
    collision pass at the solved pose every rollout starts from, kept on the
    export's ``assembly_data.dynamics`` (ADR-087). The agent reads the same
    block through ``inspect scope=contacts`` (ADR-508); here it is grouped by
    the two components each contact joins, penetrating pairs first, for the
    collision view. Nothing is measured here.
    """

    exports = [item for item in result.get("outputs") or []
               if isinstance(item, Mapping) and item.get("type") == "mjcf"]
    if not exports:
        return _no_contacts("the accepted attempt exported no MJCF (no assembly.mjcf output)")
    item = exports[0]
    data = item.get("assembly_data") if isinstance(item.get("assembly_data"), Mapping) else {}
    dynamics = data.get("dynamics") if isinstance(data.get("dynamics"), Mapping) else {}
    if "initial_contact_count" not in dynamics:
        return _no_contacts(f"the export {item.get('name')} recorded no t=0 contacts; rebuild to measure them")
    pairs: dict[tuple[str, ...], dict[str, Any]] = {}
    for contact in dynamics.get("initial_contacts") or []:
        names = sorted(str(n) for n in (contact.get("component_outputs") or [])) if isinstance(contact, Mapping) else []
        if len(names) != 2:
            continue
        row = pairs.setdefault(tuple(names), {"components": names, "points": 0, "penetrating": False, "deepest_mm": None})
        row["points"] += 1
        row["penetrating"] = row["penetrating"] or bool(contact.get("penetrating"))
        distance = contact.get("distance_mm")
        if isinstance(distance, (int, float)) and (row["deepest_mm"] is None or distance < row["deepest_mm"]):
            row["deepest_mm"] = float(distance)
    return {
        "available": True, "reason": None,
        "source": f"the accepted attempt's {item.get('name')} (assembly.mjcf export): MuJoCo contacts between "
                  "collision shapes at the solved starting pose (t=0), not the exact solids",
        "count": int(dynamics.get("initial_contact_count") or 0),
        "omitted": int(dynamics.get("initial_contacts_omitted") or 0),
        "pairs": sorted(pairs.values(), key=lambda row: (not row["penetrating"], row["components"])),
    }


def _identity_model(**fields: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema": REVIEW_MODEL_SCHEMA, "view": None, "run": None, "relation": None,
        "revision": None, "digest": None, "available": False, "reason": None,
        "source": None, "placement_source": None, "components": [],
        "collision": _no_collision("no model to show"),
        "contacts": _no_contacts("t=0 contacts are read from the accepted attempt's MJCF export only"),
        "exploded": [],
        "appearance": {"available": False, "reason": "no model to show", "palette": None, "printable": []},
        "measurements": {"available": False, "reason": "no model to show", "records": []},
    }
    base.update(fields)
    return base


def retain_training_view(project_root: Path | str, run_dir: Path | str) -> None:
    """Freeze accepted review inputs before a walk dispatches training."""
    from .review_record import read_accepted_identity, snapshot_project_docs

    root, destination = Path(project_root), Path(run_dir)
    marker = destination / "training-view.json"
    if marker.exists():
        return
    model = accepted_model(root)
    project = ReviewProject(root)
    mesh_dir = destination / "training-view"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    for entry in model["components"]:
        output = entry.get("output")
        if not entry.get("mesh"):
            continue
        data = project.accepted_mesh(output)
        if data is None:
            raise OSError(f"accepted mesh disappeared while retaining {output}")
        mesh_path = mesh_dir / f"{output}.stl"
        mesh_path.write_bytes(data)
        entry["sha256"] = _sha256(mesh_path)
        entry["mesh"] = f"/mesh/run/{destination.name}/{output}.stl"
    model.pop("meshes", None)
    payload = {"schema": "cadex-training-view-v1", "model": model,
               "identity": read_accepted_identity(root),
               "project_docs": snapshot_project_docs(root, destination)}
    temporary = marker.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n")
    temporary.replace(marker)


def run_model(project_root: Path | str, record: Mapping[str, Any]) -> dict[str, Any]:
    """The model a run retained: its rollout meshes, placed as its trace says.

    The rollout leg exports each output beside its trace, so the meshes in
    the trace's directory *are* the geometry that run rolled out, at the
    revision its record names — never today's script. Components come
    from the trace's first frame; the component-to-output link comes from
    the run's render summary when it resolves, else from a mesh named as
    the component is. A mesh with no component is shown unplaced and says
    so; a component with no mesh is listed as missing one.

    With no recorded trace, new walks use the frozen assembled training view.
    Older STL parts beside the recorded training model remain inspectable at
    identity, explicitly without assembly placements.
    A missing recorded trace or training export never borrows other geometry.
    """

    root = Path(project_root).expanduser()
    run_name = str(record.get("run"))
    run_dir = root / RUNS_DIRNAME / run_name
    model_block = record.get("model") or {}
    model = _identity_model(
        view="run", run=run_name, relation=record.get("relation"),
        revision=model_block.get("accepted_revision"), digest=model_block.get("digest"),
        appearance={"available": False, "palette": None, "printable": [],
                    "reason": "a run's retained meshes carry no appearance roles; the accepted model shows them"},
        measurements={"available": False, "records": [],
                      "reason": "a run's retained meshes carry no declared measurements; the accepted model shows them"},
    )
    run_ref = resolve_reference(root, f"{RUNS_DIRNAME}/{run_name}")
    if run_ref["error"] or not run_ref["exists"]:
        # A runs/<name> that is itself a symlink out of the project passes
        # every check anchored at that already-escaped directory (ADR-318):
        # the reader lists it unreadable, and the model says the same
        # before anything under it is read.
        model["reason"] = ("run directory escapes the project directory" if run_ref["error"]
                           else "run directory missing")
        return model
    trace_item = ((record.get("resolved") or {}).get("artifacts") or {}).get("trace") or {}
    if trace_item.get("path") is None:
        snapshot_path = run_dir / "training-view.json"
        if snapshot_path.exists():
            reference = resolve_reference(run_dir, "training-view.json")
            snapshot = _load_json(snapshot_path) if not reference["error"] else None
            retained = (snapshot or {}).get("model") or {}
            if ((snapshot or {}).get("schema") != "cadex-training-view-v1"
                    or not isinstance(retained.get("components"), list)):
                model["reason"] = "retained training view is unreadable or incomplete"
                return model
            if (retained.get("revision") != model["revision"]
                    or retained.get("digest") != model["digest"]):
                model["reason"] = "retained training view identity does not match run"
                return model
            model.update({key: retained.get(key) for key in
                          ("available", "components", "placement_source", "reason")})
            model["source"] = "assembled model retained before training"
            model["collision"] = _run_collision(run_dir, record)
            for entry in model["components"]:
                output = entry.get("output")
                item = resolve_reference(run_dir, f"training-view/{output}.stl")
                if entry.get("mesh"):
                    if item["error"] or not item["exists"]:
                        entry.update(mesh=None, mesh_status="missing")
                    elif _sha256(run_dir / item["path"]) != entry.get("sha256"):
                        entry.update(mesh=None, mesh_status="digest mismatch")
            return model
        exported = ((record.get("resolved") or {}).get("artifacts") or {}).get("model_xml") or {}
        if exported.get("path") is not None:
            if not model.get("revision") or not model.get("digest"):
                model["reason"] = "training export has no recorded revision and digest"
                return model
            if exported.get("error") or not exported.get("exists"):
                model["reason"] = "training model reference unavailable: " + (exported.get("error") or "missing")
                return model
            mesh_dir = (run_dir / exported["path"]).parent
            meshes = [p for p in sorted(mesh_dir.glob("*.stl"))
                      if p.is_file() and not p.is_symlink()]
            if not meshes:
                model["reason"] = "no STL parts retained beside the recorded training model"
                return model
            model.update({
                "available": True,
                "source": "retained training export parts at this run's revision; "
                          "assembly placements not recorded (parts shown at identity, not a solved pose)",
                "placement_source": "assembly placements not recorded: individual parts at identity",
                "components": [{
                    "name": p.stem, "output": p.stem,
                    "mesh": f"/mesh/run/{run_name}/{p.stem}.stl",
                    "mesh_status": "retained", "placement": None,
                    "placement_source": "individual exported part: identity",
                } for p in meshes],
                "collision": _run_collision(run_dir, record),
            })
            return model
        return _model_before_rollout(root, model)
    if trace_item.get("error"):
        model["reason"] = f"trace reference not honoured: {trace_item['error']}"
        return model
    if not trace_item.get("exists"):
        model["reason"] = f"rollout trace missing: {trace_item['path']}"
        return model
    trace_path = run_dir / trace_item["path"]
    mesh_dir = trace_path.parent
    meshes = {path.stem: path for path in sorted(mesh_dir.glob("*.stl"))
              if path.is_file() and not path.is_symlink()}
    if not meshes:
        model["reason"] = f"no .stl meshes retained beside the trace ({trace_item['path']})"
        return model
    trace = _load_json(trace_path)
    placements, components = _first_frame_placements(trace)
    sources = _render_sources(root, record)
    placement_source = ("rollout trace, first frame" if placements
                        else "none recorded: meshes shown at identity")
    entries: list[dict[str, Any]] = []
    used: set[str] = set()
    for name in components or list(placements):
        output = sources.get(name) or (name if name in meshes else None)
        if output in meshes:
            used.add(output)
        entries.append({
            "name": name, "output": output,
            "mesh": f"/mesh/run/{run_name}/{output}.stl" if output in meshes else None,
            "mesh_status": "retained" if output in meshes else "missing",
            "placement": placements.get(name),
            "placement_source": ("rollout trace, first frame" if name in placements
                                 else "none recorded: identity"),
        })
    for output, path in meshes.items():
        if output in used:
            continue
        entries.append({
            "name": output, "output": output,
            "mesh": f"/mesh/run/{run_name}/{output}.stl", "mesh_status": "retained",
            "placement": None, "placement_source": "no component placement recorded: identity",
        })
    model.update({
        "available": True,
        "source": f"runs/{run_name}/{mesh_dir.relative_to(run_dir).as_posix()}/*.stl "
                  "(the rollout leg's exports at this run's revision)",
        "placement_source": placement_source,
        "components": entries,
        # The proxies the rollout ran against: the run's own export, and only
        # if it is the model the trace's policy receipt names.
        "collision": _run_collision(run_dir, record, expected_sha256=(
            ((trace or {}).get("policy") or {}).get("model_sha256"))),
    })
    # The frames themselves travel in ``/api/playback/run/<name>``; the
    # manifest says only whether there is something to play.
    playback = trace_playback(trace)
    model["playback"] = ({"available": True, "frames": len(playback["frames"]),
                          "duration_s": playback["duration_s"],
                          "url": f"/api/playback/run/{run_name}"}
                         if playback["available"] else {"available": False, "reason": playback["reason"]})
    return model


def _model_before_rollout(root: Path, model: dict[str, Any]) -> dict[str, Any]:
    """A run that has not rolled out yet: the accepted model, if it *is* this one.

    Without a recorded training export or rollout, the reader cannot
    locate the run's own meshes. The
    record still names the revision and digest the trainer was given
    (``identity_source`` says from where), and when **both** equal the
    accepted revision and digest now, the accepted attempt's tessellation
    is exactly that geometry and is shown, labelled as borrowed. Any other
    case — a historical run, a record with no identity, an accepted digest
    that has moved — shows nothing, with the reason, rather than today's
    script standing in for what the run trained on.
    """

    if not model.get("revision"):
        model["reason"] = "no rollout trace retained for this run, and no revision recorded to match the accepted model against"
        return model
    accepted = accepted_model(root)
    same = (accepted["revision"] == model["revision"]
            and accepted["digest"] is not None and accepted["digest"] == model.get("digest"))
    if not same:
        model["reason"] = ("no rollout trace retained for this run; its recorded revision "
                           "is not the accepted one now, so no model is shown for it")
        return model
    if not accepted["available"]:
        model["reason"] = f"no rollout trace retained for this run, and the accepted model it matches is unavailable: {accepted['reason']}"
        return model
    model.update({
        "available": True,
        "source": "the accepted attempt's tessellation, borrowed: this run retained no "
                  "rollout, and its recorded revision and digest are the accepted ones now",
        "placement_source": accepted["placement_source"],
        "components": accepted["components"],
        "meshes": accepted.get("meshes") or {},
        "collision": accepted["collision"],
        "contacts": accepted["contacts"],
        "exploded": accepted["exploded"],
        "appearance": accepted["appearance"],
        "measurements": accepted["measurements"],
    })
    return model


def _accepted_staging(root: Path) -> tuple[Path | None, dict[str, Any] | None, str | None]:
    """The accepted attempt's staging directory, or why it cannot be used.

    Read-only, and only when the manifest's ``accepted_attempt.staging``
    lies inside the project under the accepted revision: a staging path
    that names another revision is refused rather than shown as the
    accepted model.
    """

    manifest = _load_json(root / PROJECT_SCRIPT_FILENAME)
    if not manifest or manifest.get("schema") != PROJECT_SCRIPT_SCHEMA:
        return None, None, "no readable project manifest"
    revision = manifest.get("accepted_revision")
    if not revision:
        return None, manifest, "nothing accepted yet"
    staging = (manifest.get("accepted_attempt") or {}).get("staging")
    if not staging:
        return None, manifest, "the manifest names no accepted attempt"
    item = resolve_reference(root, staging)
    if item["error"]:
        return None, manifest, f"accepted attempt reference not honoured: {item['error']}"
    if not item["exists"]:
        return None, manifest, "accepted attempt's staging directory is not on disk"
    parts = Path(item["path"]).parts
    if len(parts) < 2 or parts[0] != "script_artifacts":
        return None, manifest, "accepted attempt's staging is not under script_artifacts"
    if parts[1] != revision and not _attempt_is_the_accepted_one(root / item["path"], manifest):
        return None, manifest, "accepted attempt's staging does not belong to the accepted revision"
    return root / item["path"], manifest, None


def _attempt_is_the_accepted_one(staging: Path, manifest: Mapping[str, Any]) -> bool:
    """Whether a staging directory named for another revision still holds
    the accepted attempt (ADR-311).

    The engine stages every attempt under the revision it can compute
    *before* the worker runs — over the stored parameter-spec cache — and
    records the revision recomputed with the worker-collected specs as the
    accepted one. On a project's first accepted script those differ, so the
    directory name alone cannot say whether the attempt is the accepted one.
    The manifest's own pin and the attempt's content digest can: the pin
    must name the accepted revision, and the attempt's ``result.json`` must
    carry the accepted digest. Anything less is still refused.
    """

    attempt = manifest.get("accepted_attempt") or {}
    digest = manifest.get("accepted_digest")
    if not digest or attempt.get("revision") != manifest.get("accepted_revision"):
        return False
    result = _load_json(staging / "result.json")
    return bool(result) and result.get("digest") == digest


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def part_looks(result: Mapping[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Each shown part's appearance role, colour and print status (ADR-522).

    The rule is the renderer's (``CadexStudio.materials``), so the viewer
    paints a part as ``look`` and the concept sheet do: the role a
    component declared, else mechanism for a catalogued (purchased) part and
    shell for a printed one, in the assembly's palette. The facts are the
    ones ``inspect scope=inventory`` joins, read from the same accepted
    ``result.json``. ``printable`` is the engine's roster, every output with
    a surface ``export_printable`` would accept. Sets ``role``, ``color``,
    ``role_source``, ``supplier`` and ``printable`` on each entry and
    returns the model's ``appearance`` block. With no assembly there is no
    supplier to read and every entry keeps ``role`` ``None``: the viewer
    keeps its index colours, as ``look`` does.
    """

    outputs = {str(item.get("name") or ""): item for item in result.get("outputs") or []
               if isinstance(item, Mapping)}
    roster = PRINTABLES.printable_roster(result.get("outputs"))
    for entry in entries:
        entry.update(role=None, color=None, role_source=None, supplier=None,
                     printable=entry.get("output") in roster)
    links = {name: item for name, item in outputs.items() if item.get("type") == "component_link"}
    assemblies = [item for item in outputs.values() if item.get("type") == "assembly"]
    if not links:
        return {"available": False, "reason": "no assembly: no inventory to tell printed from purchased",
                "palette": None, "printable": sorted(roster)}
    appearance = {}
    for name, item in links.items():
        role = ((item.get("definition") or {}).get("properties") or {}).get("appearance")
        if role:
            appearance[name] = str(role)
    palette_block = ((((assemblies[0].get("definition") or {}).get("properties") or {}).get("palette"))
                     if assemblies else None) or {}
    summary = {"objects": {entry["name"]: {"source": entry.get("output"), "color": (0, 0, 0)}
                           for entry in entries}}
    purchased = {entry["name"] for entry in entries
                 if isinstance((outputs.get(str(entry.get("output"))) or {}).get("catalog"), Mapping)}
    try:
        _declared, palette = STUDIO.declared({"appearance": appearance, "palette": palette_block})
        looks = STUDIO.materials(summary, purchased=purchased,
                                 appearance={k: v for k, v in appearance.items() if k in summary["objects"]},
                                 palette=palette)
    except STUDIO.StudioError as exc:
        return {"available": False, "reason": str(exc), "palette": None, "printable": sorted(roster)}
    for entry in entries:
        role, rgb = looks[entry["name"]]
        entry.update(role=role, color="#%02X%02X%02X" % tuple(rgb),
                     role_source="declared" if entry["name"] in appearance else "supplier",
                     supplier="purchased" if entry["name"] in purchased else "printed")
    return {"available": True,
            "source": "the accepted assembly's declared roles, else purchased mechanism and printed shell "
                      "(CadexStudio.materials, as look and the concept sheet draw them)",
            "palette": {role: "#%02X%02X%02X" % tuple(rgb)
                        for role, rgb in {**STUDIO.ROLE_COLORS, **palette}.items()},
            "printable": sorted(roster)}


#: The record fields the viewer's dimension overlay draws from, as the engine
#: publishes them on a ``measurement`` output (``measurement_record``, ADR-139).
_MEASUREMENT_FIELDS = ("kind", "label", "text", "value_mm", "value_deg", "anchors_mm",
                       "center_mm", "radius_mm", "normal", "vertex_mm")


def declared_measurements(result: Mapping[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    """The script's declared ``part.measurement`` records, and where to draw each (ADR-524).

    The engine resolved each one against the exact BREP when it built the
    accepted attempt: the number, its text, and the anchor points or circle
    it is drawn from, in the measured output's own frame (``subject``). The
    viewer draws them in that frame on the component that shows the output,
    so a placed, exploded or played part carries its dimension with it. A
    record whose subject the viewer does not show is listed with the reason
    and not drawn. One with no subject (an undeclared intermediate) is in
    the model's own coordinates only when nothing is placed; in a design
    that places components it is in some part's frame the viewer cannot
    name, so it is listed and not drawn, as the blueprint sheet does.
    Nothing is measured here.
    """

    placed = any(entry.get("placement") is not None for entry in entries)
    shown: dict[str, list[str]] = {}
    for entry in entries:
        if entry.get("mesh") and entry.get("output"):
            shown.setdefault(str(entry["output"]), []).append(str(entry["name"]))
    records = []
    for item in result.get("outputs") or []:
        if not isinstance(item, Mapping) or not isinstance(item.get("measurement"), Mapping):
            continue
        record = item["measurement"]
        subject = str(record.get("subject") or "")
        row: dict[str, Any] = {"name": str(item.get("name") or ""), "subject": subject}
        row.update({key: record.get(key) for key in _MEASUREMENT_FIELDS})
        if not subject and placed:
            row.update(component=None, frame="an undeclared intermediate shape's own frame", drawn=False,
                       reason="measures an undeclared intermediate shape, and the design places components, "
                              "so its points are in a part frame the viewer cannot place")
        elif not subject:
            row.update(component=None, frame="model coordinates (an undeclared intermediate shape)",
                       drawn=True, reason=None)
        elif subject in shown:
            names = shown[subject]
            row.update(component=names[0], frame=f"{subject}'s own frame, on component {names[0]}",
                       drawn=True, reason=None)
            if len(names) > 1:
                row["reason"] = f"drawn on {names[0]} only; {', '.join(names[1:])} show the same output"
        else:
            row.update(component=None, frame=f"{subject}'s own frame", drawn=False,
                       reason=f"measures {subject}, which the viewer does not show")
        records.append(row)
    if not records:
        return {"available": False, "records": [],
                "reason": "the script declares no part.measurement"}
    return {"available": True, "records": records,
            "source": "the accepted attempt's declared part.measurement records, measured by the engine "
                      "on the exact BREP (the numbers the blueprint sheet draws)"}


def world_components(result: Mapping[str, Any]) -> set[str]:
    """The components the accepted attempt's fit calls world geometry.

    A task floor or bench is drawn like any part, but it is the stage, not
    the design: the viewer frames and measures coverage without it. The
    engine decides (``world=True``, a collision plane, a bare planar face —
    docs/XSCRIPT.md); nothing here infers purpose from a name.
    """

    return {str(row.get("component")) for output in result.get("outputs") or []
            if isinstance(output, Mapping)
            for row in output.get("world_geometry") or []
            if isinstance(row, Mapping) and row.get("status") == "world geometry" and row.get("component")}


#: What :func:`accepted_model` read last, per project: an attempt's staging
#: is written once, so the model is a function of the manifest that names it
#: and of the few staging files it reads, and is rebuilt only when one of
#: their stats moves. Rebuilding hashes every BREP of the attempt, which a
#: page loading forty meshes did forty times over.
_MODEL_MEMO: "OrderedDict[str, tuple[tuple[Any, ...], dict[str, Any]]]" = OrderedDict()
_MODEL_MEMO_SIZE = 64
_MEMO_LOCK = threading.Lock()


def _stat_key(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return stat.st_mtime_ns, stat.st_size


def _content_key(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _model_inputs(root: Path) -> tuple[Any, ...]:
    """What the accepted model is a function of: the manifest and the
    attempt's result by content (a rewrite inside one clock tick keeps its
    mtime), the tessellation directory and the trace by stat."""

    manifest = root / PROJECT_SCRIPT_FILENAME
    staging = ((_load_json(manifest) or {}).get("accepted_attempt") or {}).get("staging")
    inputs: tuple[Any, ...] = (_content_key(manifest), staging)
    if isinstance(staging, str):
        base = root / staging
        inputs += (_content_key(base / "result.json"), _stat_key(base / "display"),
                   _stat_key(base / "outputs" / "assembly-simulation-trace.json"))
    return inputs


def accepted_model(project_root: Path | str) -> dict[str, Any]:
    """:func:`accepted_model_uncached`, remembered until its inputs move."""

    root = Path(project_root).expanduser()
    key, inputs = str(root.resolve()), _model_inputs(root)
    with _MEMO_LOCK:
        held = _MODEL_MEMO.get(key)
        if held is not None and held[0] == inputs:
            _MODEL_MEMO.move_to_end(key)
            return copy.deepcopy(held[1])
    model = accepted_model_uncached(root)
    with _MEMO_LOCK:
        _MODEL_MEMO[key] = (inputs, copy.deepcopy(model))
        while len(_MODEL_MEMO) > _MODEL_MEMO_SIZE:
            _MODEL_MEMO.popitem(last=False)
    return model


def accepted_model_uncached(project_root: Path | str) -> dict[str, Any]:
    """The accepted model now, from the accepted attempt's own tessellation.

    The attempt's ``result.json`` lists the outputs in order with their
    BREP artifacts; each ``display/*.tess.json`` sidecar names the BREP it
    was tessellated from by sha256, which is the link used here — not
    file order. Component links are followed through the attempt's
    ``component_sources`` to their outputs, and placed where the attempt's
    own simulation trace put them at its first frame, falling back to the
    placement each link declared. Nothing is rebuilt.
    """

    root = Path(project_root).expanduser()
    staging, manifest, reason = _accepted_staging(root)
    model = _identity_model(
        view="accepted",
        revision=(manifest or {}).get("accepted_revision"),
        digest=(manifest or {}).get("accepted_digest"),
    )
    if staging is None:
        model["reason"] = reason
        return model
    result = _load_json(staging / "result.json")
    if not result or not isinstance(result.get("outputs"), list):
        model["reason"] = "accepted attempt has no readable result.json"
        return model
    # Several outputs may be byte-identical BREP (a mirrored pair of legs);
    # every one of them owns the tessellation made from those bytes.
    brep_digests: dict[str, list[str]] = {}
    outputs_by_name: dict[str, Mapping[str, Any]] = {}
    for output in result["outputs"]:
        if not isinstance(output, Mapping) or not isinstance(output.get("name"), str):
            continue
        outputs_by_name[output["name"]] = output
        artifact = output.get("artifact_path")
        if output.get("artifact_kind") == "brep" and isinstance(artifact, str):
            item = resolve_reference(staging, artifact)
            if item["exists"] and not item["error"]:
                brep_digests.setdefault(_sha256(staging / artifact), []).append(output["name"])
    tess_by_output: dict[str, dict[str, Any]] = {}
    for sidecar_path in sorted((staging / "display").glob("*.tess.json")):
        sidecar = _load_json(sidecar_path)
        if not sidecar or sidecar.get("schema") != TESSELLATION_SCHEMA:
            continue
        artifact = resolve_reference(staging, sidecar.get("artifact_path"))
        if not artifact["exists"] or artifact["error"]:
            continue
        for output in brep_digests.get(str(sidecar.get("source_sha256")), []):
            tess_by_output.setdefault(output, {"sidecar": sidecar_path.name, "artifact": artifact["path"],
                                               "triangles": (sidecar.get("counts") or {}).get("triangles")})
    if not tess_by_output:
        model["reason"] = "accepted attempt retained no tessellation"
        return model
    component_sources = result.get("component_sources") or {}
    placements, _components = _first_frame_placements(
        _load_json(staging / "outputs" / "assembly-simulation-trace.json"))
    world = world_components(result)
    entries: list[dict[str, Any]] = []
    used: set[str] = set()
    for name, output in outputs_by_name.items():
        if output.get("type") != "component_link":
            continue
        definition = output.get("definition") or {}
        arguments = definition.get("arguments") or [{}]
        object_name = (arguments[0] or {}).get("object_name") if isinstance(arguments[0], Mapping) else None
        source = component_sources.get(str(object_name))
        declared = _placement((definition.get("properties") or {}).get("placement"))
        solved = _matrix_placement(output.get("solved_placement_matrix"))
        if name in placements:
            placement, placement_source = placements[name], "accepted attempt's simulation trace, first frame"
        elif solved is not None:
            placement, placement_source = solved, "solved component placement (no simulation trace)"
        elif declared is not None:
            placement, placement_source = declared, "declared component placement (no solved trace)"
        else:
            placement, placement_source = None, "none recorded: identity"
        if source in tess_by_output:
            used.add(source)
        entries.append({
            "name": name, "output": source,
            "mesh": f"/mesh/accepted/{source}.stl" if source in tess_by_output else None,
            "mesh_status": "retained" if source in tess_by_output else "missing",
            "placement": placement, "placement_source": placement_source,
            "world": name in world,
        })
    for output in tess_by_output:
        if output in used:
            continue
        entries.append({
            "name": output, "output": output, "mesh": f"/mesh/accepted/{output}.stl",
            "mesh_status": "retained", "placement": None,
            "placement_source": "no component placement recorded: identity",
        })
    collision = _no_collision("the accepted attempt exported no MJCF (no assembly.mjcf output)")
    for output in result["outputs"]:
        if (isinstance(output, Mapping) and output.get("artifact_kind") == MJCF_ARTIFACT_KIND
                and isinstance(output.get("artifact_path"), str)):
            item = resolve_reference(staging, output["artifact_path"])
            if item["error"] or not item["exists"]:
                collision = _no_collision("the accepted attempt's MJCF export is missing or not honoured")
            else:
                collision = collision_proxies(
                    staging / item["path"],
                    source=f"the accepted attempt's {output.get('name')} (assembly.mjcf export at the accepted revision)")
            break
    model.update({
        "available": True,
        "collision": collision,
        "contacts": initial_contacts(result),
        "source": "the accepted attempt's tessellation (display/*.tess), linked to each output by sha256",
        "placement_source": ("accepted attempt's simulation trace, first frame" if placements
                             else "solved component placements" if any(
                                 entry["placement_source"].startswith("solved") for entry in entries)
                             else "declared component placements"),
        "components": entries,
        "exploded": exploded_views(result, {entry["name"]: entry["placement"] for entry in entries}),
        "appearance": part_looks(result, entries),
        "measurements": declared_measurements(result, entries),
        "meshes": {output: entry["artifact"] for output, entry in tess_by_output.items()},
    })
    return model


def tessellation_to_stl(sidecar: Mapping[str, Any], data: bytes) -> bytes:
    """A ``cadex-tessellation-v1`` buffer as a binary STL, for the viewer.

    One mesh format in the browser rather than two: the run meshes are
    already STL, so the accepted tessellation is written as one too.
    """

    if sidecar.get("schema") != TESSELLATION_SCHEMA or sidecar.get("byte_order") != "little":
        raise ValueError("unsupported tessellation format")
    layout = sidecar.get("layout") or {}
    vertex_layout, triangle_layout = layout.get("vertices") or {}, layout.get("triangles") or {}
    if vertex_layout.get("dtype") != "f32" or triangle_layout.get("dtype") != "u32":
        raise ValueError("unsupported tessellation layout")
    vertices = array("f")
    triangles = array("I")
    if vertices.itemsize != 4 or triangles.itemsize != 4:
        raise ValueError("platform array sizes unsupported")
    v0, vn = int(vertex_layout["offset"]), int(vertex_layout["bytes"])
    t0, tn = int(triangle_layout["offset"]), int(triangle_layout["bytes"])
    if v0 < 0 or t0 < 0 or v0 + vn > len(data) or t0 + tn > len(data):
        raise ValueError("tessellation layout exceeds its buffer")
    vertices.frombytes(data[v0:v0 + vn])
    triangles.frombytes(data[t0:t0 + tn])
    if sys.byteorder != "little":
        vertices.byteswap()
        triangles.byteswap()
    count = len(triangles) // 3
    vertex_count = len(vertices) // 3
    out = bytearray(b"cadex tessellation as binary STL".ljust(80, b"\0"))
    out += struct.pack("<I", count)
    pack = struct.Struct("<12fH").pack
    for index in range(count):
        a, b, c = triangles[3 * index], triangles[3 * index + 1], triangles[3 * index + 2]
        if max(a, b, c) >= vertex_count:
            raise ValueError("tessellation triangle index out of range")
        ax, ay, az = vertices[3 * a], vertices[3 * a + 1], vertices[3 * a + 2]
        bx, by, bz = vertices[3 * b], vertices[3 * b + 1], vertices[3 * b + 2]
        cx, cy, cz = vertices[3 * c], vertices[3 * c + 1], vertices[3 * c + 2]
        ux, uy, uz = bx - ax, by - ay, bz - az
        vx, vy, vz = cx - ax, cy - ay, cz - az
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        out += pack(nx / length, ny / length, nz / length,
                    ax, ay, az, bx, by, bz, cx, cy, cz, 0)
    return bytes(out)


HISTORY_KEYS = ("curve", "loss_curve", "episode_steps_curve")


#: The most points a sparkline in the stage overlay carries (ADR-542).
SPARK_POINTS = 64
#: The histories the stage overlay draws as sparklines.
SPARK_KEYS = ("curve", "loss_curve")


def _spark(points: list[list[float]], limit: int = SPARK_POINTS) -> list[list[float]]:
    """At most ``limit`` evenly spaced points of a history, its last one
    always kept, each value to five significant figures: the shape of a
    curve in a sparkline's width, at a cost that never grows."""

    if len(points) > limit:
        step = (len(points) - 1) / (limit - 1)
        points = [points[round(i * step)] for i in range(limit)]
    return [[int(i), float(f"{v:.5g}")] for i, v in points]


def _telemetry_summary(result: dict[str, Any], reported: int, *, spark: bool = False) -> dict[str, Any]:
    """The run-list form of a telemetry result (ADR-321): the same state,
    reason and latest metrics, with each history replaced by its sample
    count and the checkpoint list by how many entries it reports. Nothing
    here is hashed and nothing grows with training length, so a poll of the
    whole run list costs a bounded amount per run however long the history.
    ``spark`` keeps a :data:`SPARK_POINTS` sketch of the reward and loss
    histories, for the one run the stage overlay reads (ADR-542)."""

    if spark:
        result["spark"] = {key: _spark(result.get(key) or []) for key in SPARK_KEYS}
    result["samples"] = {key: len(result.pop(key, []) or []) for key in HISTORY_KEYS}
    result.pop("checkpoints", None)
    result["checkpoints_reported"] = reported
    result["summary"] = True
    return result


def training_telemetry(root: Path, record: Mapping[str, Any], *, detail: bool = True,
                       spark: bool = False) -> dict[str, Any]:
    """Observe the run-local trainer snapshot; never infer process success.

    ``detail=True`` is the ``/api/run/<name>`` form: full histories (at
    most 512 samples each) and every reported checkpoint verified against
    its recorded digest. ``detail=False`` is the ``/api/project`` form,
    :func:`_telemetry_summary`: the same validation and state, sample
    counts instead of histories, a count instead of the checkpoint list,
    and no checkpoint bytes read. The two agree on ``state``, so the
    current-run rule (:func:`default_run`) reads either.
    """

    result: dict[str, Any] = {"state": "missing", "reason": "training telemetry missing",
                              "checkpoints": [], "curve": [], "loss_curve": [],
                              "episode_steps_curve": []}

    def finish(value: dict[str, Any], reported: int = 0) -> dict[str, Any]:
        return value if detail else _telemetry_summary(value, reported, spark=spark)

    run_ref = resolve_reference(root, f"runs/{record['run']}")
    if run_ref["error"] or not run_ref["exists"]:
        result["reason"] = "training run directory refused or missing"
        return finish(result)
    run_dir = root / run_ref["path"]
    # Fixed location also works before the running record sees the first snapshot.
    ref = resolve_reference(run_dir, "train/progress.json")
    if ref["error"] or not ref["exists"]:
        result["reason"] = "training telemetry refused or missing"
        return finish(result)
    path = run_dir / ref["path"]
    data = _load_json(path, limit=2 * 1024 * 1024)
    if not data or data.get("schema") != "cadex-training-progress-v1":
        result.update(state="invalid", reason="training telemetry unreadable or unsupported")
        return finish(result)
    expected = (record.get("task") or {}).get("sha256")
    if expected and data.get("task_sha256") and expected != data["task_sha256"]:
        result.update(state="invalid", reason="training telemetry task identity mismatch")
        return finish(result)
    try:
        stamp = float(data.get("updated_at", path.stat().st_mtime))
        age = max(0.0, _datetime.datetime.now(_datetime.timezone.utc).timestamp() - stamp)
        if not math.isfinite(stamp):
            raise ValueError("nonfinite timestamp")
        for key in HISTORY_KEYS:
            points = data.get(key, [])
            if not isinstance(points, list) or len(points) > 512:
                raise ValueError("invalid history")
            result[key] = [[int(i), float(v)] for i, v in points]
            if any(not math.isfinite(v) for i, v in result[key]):
                raise ValueError("nonfinite history")
        for key in ("iteration", "total", "reward_per_step", "loss", "episode_steps",
                    "eta_s", "wall_time_s", "best_iteration", "best_reward_per_step"):
            value = data.get(key)
            if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise ValueError("invalid metric")
            result[key] = value
        # The collapse the trainer has detected (ADR-410), as it said it.
        result["warning"] = str(data.get("warning") or "")[:300]
    except (OSError, TypeError, ValueError, OverflowError):
        return finish({"state": "invalid", "reason": "training telemetry has invalid metrics",
                       "checkpoints": [], "curve": [], "loss_curve": [], "episode_steps_curve": []})
    reported = data.get("state")
    result.update(state=reported if reported in ("starting", "training", "done", "failed") else "unknown",
                  reported_state=reported, age_s=age, reason=str(data.get("error") or ""))
    if reported in ("starting", "training") and age > 30:
        result.update(state="stale", reason="no telemetry update for over 30 s; process state unknown")
    checkpoints = data.get("checkpoints", [])
    if not isinstance(checkpoints, list):
        result.update(state="invalid", reason="invalid checkpoint list")
        return finish(result)
    reported = sum(1 for item in checkpoints[:512] if isinstance(item, dict))
    # Where the checkpoint bytes may be: this run's own train/ first, then the
    # training run its record names (a playback run copies the snapshot but
    # not the checkpoints). Both stay inside this project's runs/.
    bases: list[tuple[str, Path]] = [("run", run_dir / "train")]
    source = _checkpoint_source(root, record)
    result["checkpoint_source"] = source
    if not detail:
        return _telemetry_summary(result, reported, spark=spark)
    if source["state"] == "resolved":
        bases.append((source["run"], root / source["path"]))
    for item in checkpoints[:512]:
        if not isinstance(item, dict):
            continue
        name = item.get("path")
        status, found = "missing", None
        if not (isinstance(name, str) and name and Path(name).name == name):
            status = "refused"
        else:
            for label, base in bases:
                ref = resolve_reference(base, name)
                if ref["error"]:
                    status = "refused"
                    continue
                if not ref["exists"]:
                    continue
                checkpoint = base / ref["path"]
                try:
                    status = ("retained" if checkpoint.is_file() and checkpoint.stat().st_size <= 4 * 1024 * 1024
                              and _sha256(checkpoint) == item.get("sha256") else "digest mismatch")
                except OSError:
                    status = "missing"
                found = label
                break
        result["checkpoints"].append({"path": name, "iteration": item.get("iteration"),
                                      "sha256": item.get("sha256"), "status": status,
                                      "source": found})
    return result


def _checkpoint_source(root: Path, record: Mapping[str, Any]) -> dict[str, Any]:
    """The training run a playback record names, resolved inside this project.

    ``state`` is ``none`` when the record names no source run (the run's own
    ``train/`` is the only place), ``resolved`` when ``runs/<source>/train``
    exists here, ``missing`` when the named run is not in this project, and
    ``refused`` when the name is not a bare run name or escapes ``runs/``.
    A copy that left its training run behind says so instead of borrowing
    from wherever the original lives.
    """

    requested = (record.get("training") or {}).get("requested") or {}
    name = requested.get("source_run") if isinstance(requested, Mapping) else None
    if not name:
        return {"state": "none", "run": None, "path": None,
                "reason": "no training run recorded; checkpoints resolve in this run only"}
    if not isinstance(name, str) or Path(name).name != name or name in (".", ".."):
        return {"state": "refused", "run": str(name)[:128], "path": None,
                "reason": "recorded training run name is not a bare run name"}
    ref = resolve_reference(root, f"{RUNS_DIRNAME}/{name}/train")
    if ref["error"]:
        return {"state": "refused", "run": name, "path": None, "reason": ref["error"]}
    if not ref["exists"] or not (root / ref["path"]).is_dir():
        return {"state": "missing", "run": name, "path": None,
                "reason": f"training run {name} is not in this project; its checkpoints "
                          "cannot be shown here. Copy the project with runs/" + name +
                          "/train, or start a new cadex walk --out runs/<new-name>"}
    return {"state": "resolved", "run": name, "path": ref["path"],
            "reason": f"checkpoints resolved through recorded training run {name}"}


# -- evaluations: a policy held to its task's success spec (ADR-457, ADR-459) --

#: How many evaluations the project list names, newest kept.
EVALUATIONS_LISTED = 64
_EVALUATION_NAME = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
_evaluation_cache: dict[str, tuple[tuple[int, ...], dict[str, Any]]] = {}


def _evaluation_constants() -> tuple[str, str, str, Callable[[Mapping[str, Any]], list[str]]]:
    # Imported where it is used: ``evaluate`` draws with ``video``, which
    # serves its capture page from this module.
    from .evaluate import EVALUATIONS_DIR, REPORT_NAME, REPORT_SCHEMA, failing_predicates
    return EVALUATIONS_DIR, REPORT_NAME, REPORT_SCHEMA, failing_predicates


def _evaluation_dir(root: Path, name: str) -> Path | None:
    """``evaluations/<name>`` when it is a directory of the project, by name only."""

    directory_name = _evaluation_constants()[0]
    if not name or name in (".", "..") or not set(name) <= _EVALUATION_NAME:
        return None
    item = resolve_reference(root, f"{directory_name}/{name}")
    path = root / directory_name / name
    if item["error"] or not item["exists"] or not path.is_dir():
        return None
    return path


def _evaluation_report(directory: Path) -> tuple[dict[str, Any], tuple[int, ...]] | None:
    _dirname, report_name, schema, _failing = _evaluation_constants()
    path = directory / report_name
    try:
        if path.is_symlink() or not path.is_file():
            return None
        stat = path.stat()
    except OSError:
        return None
    report = _load_json(path)
    if not report or report.get("schema") != schema or not isinstance(report.get("summary"), dict):
        return None
    return report, (stat.st_ino, stat.st_size, stat.st_mtime_ns)


def _film_files(directory: Path, report: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Every file the report's film block names, resolved inside the evaluation."""

    files: dict[str, dict[str, Any]] = {}
    film = report.get("film") if isinstance(report.get("film"), dict) else {}
    for row in film.get("seeds") or []:
        for key in ("overview", "detail", "video"):
            item = row.get(key) if isinstance(row, dict) else None
            name = item.get("file") if isinstance(item, dict) else None
            if not isinstance(name, str) or not name or not set(name) <= _EVALUATION_NAME:
                continue
            resolved = resolve_reference(directory, name)
            path = directory / name
            present = bool(resolved["exists"] and not resolved["error"]
                           and path.is_file() and not path.is_symlink())
            files[name] = {"exists": present, "error": resolved["error"],
                           "bytes": path.stat().st_size if present else None}
    return files


def _film_sheets(film: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Per filmed seed, the file each of its sheets and its video is in, or None.

    Names only, as the report wrote them; the 2D viewport lists them and
    ``evaluation/<name>/<file>`` serves only what the report names (ADR-541).
    """

    sheets = []
    for row in film.get("seeds") or []:
        if not isinstance(row, dict):
            continue
        entry: dict[str, Any] = {"seed": row.get("seed")}
        for key in ("overview", "detail", "video"):
            item = row.get(key)
            name = item.get("file") if isinstance(item, dict) else None
            entry[key] = name if isinstance(name, str) and name and set(name) <= _EVALUATION_NAME else None
        sheets.append(entry)
    return sheets


def _evaluation_relation(report: Mapping[str, Any], accepted: Mapping[str, Any]) -> str:
    if not accepted.get("available") or not report.get("accepted_revision"):
        return "unknown"
    return "current" if report["accepted_revision"] == accepted["revision"] else "historical"


def evaluations(project_root: Path | str, accepted: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The project's evaluations as a bounded summary each, oldest first.

    One row per ``evaluations/<name>/evaluation.json``: the verdict, the
    seed tally, what failed, whose policy and task it was, its relation to
    the accepted revision now, and which seeds were filmed. The per-seed
    rows travel only in ``/api/evaluation/<name>``. A report is parsed once
    per file identity, so an idle poll reads no report twice.
    """

    root = Path(project_root).expanduser().resolve()
    directory_name, report_name, _schema, failing = _evaluation_constants()
    base = root / directory_name
    if not base.is_dir() or base.is_symlink():
        return []
    rows = []
    for entry in sorted(base.iterdir()):
        directory = _evaluation_dir(root, entry.name)
        if directory is None:
            continue
        try:
            stat = (directory / report_name).stat()
        except OSError:
            continue
        stamp = (stat.st_ino, stat.st_size, stat.st_mtime_ns)
        cached = _evaluation_cache.get(str(directory))
        if cached is None or cached[0] != stamp:
            found = _evaluation_report(directory)
            if found is None:
                continue
            report, stamp = found
            summary = report["summary"]
            film = report.get("film") if isinstance(report.get("film"), dict) else {}
            if len(_evaluation_cache) >= 4 * EVALUATIONS_LISTED:
                _evaluation_cache.clear()
            cached = _evaluation_cache[str(directory)] = (stamp, {
                "name": entry.name,
                "verdict": report.get("verdict"),
                "seeds": int(summary.get("seeds") or 0),
                "passed": len(summary.get("passed") or []),
                "void": list(summary.get("void") or []),
                "failing": failing(report),
                "terminations": dict(summary.get("terminations") or {}),
                "accepted_revision": report.get("accepted_revision"),
                "policy_output": report.get("policy_output"),
                "policy_sha256": report.get("policy_sha256"),
                "task_output": report.get("task_output"),
                "task_label": report.get("task_label"),
                "film": {"state": film.get("state") or "none",
                         "seeds": [row.get("seed") for row in film.get("seeds") or []
                                   if isinstance(row, dict)],
                         "sheets": _film_sheets(film)},
                "stamp": "-".join(str(part) for part in stamp[1:]),
                "evaluated_at": _datetime.datetime.fromtimestamp(
                    stamp[2] / 1e9, _datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "_order": stamp[2],
            })
        rows.append({**cached[1], "relation": _evaluation_relation(cached[1], accepted)})
    rows.sort(key=lambda row: (row["_order"], row["name"]))
    for row in rows:
        del row["_order"]
    return rows[-EVALUATIONS_LISTED:]


def evaluation_detail(project_root: Path | str, name: str,
                      accepted: Mapping[str, Any]) -> dict[str, Any] | None:
    """``/api/evaluation/<name>``: the report as written, and what of its film is on disk."""

    root = Path(project_root).expanduser().resolve()
    directory = _evaluation_dir(root, name)
    found = _evaluation_report(directory) if directory is not None else None
    if found is None:
        return None
    report, stamp = found
    return {"name": name, "relation": _evaluation_relation(report, accepted),
            "stamp": "-".join(str(part) for part in stamp[1:]),
            "files": _film_files(directory, report), "report": report}


def evaluation_file(project_root: Path | str, name: str, filename: str) -> Path | None:
    """The report itself or a film file it names; nothing else in the directory."""

    root = Path(project_root).expanduser().resolve()
    directory = _evaluation_dir(root, name)
    found = _evaluation_report(directory) if directory is not None else None
    if found is None:
        return None
    report_name = _evaluation_constants()[1]
    if filename != report_name and not _film_files(directory, found[0]).get(filename, {}).get("exists"):
        return None
    path = directory / filename
    return path if path.is_file() and not path.is_symlink() else None


def default_run(review: Mapping[str, Any]) -> str:
    """The view a fresh visit opens, as ``review.js``'s ``currentView`` does.

    The newest ``running``/``pending`` record whose telemetry is ``starting``
    or ``training`` comes first; otherwise the newest record, failed or
    interrupted included; ``accepted`` when there are no runs. ``review`` is
    ``ReviewProject.review()`` (records oldest first, telemetry attached).
    Names play no part: a checker that wants to know what the page will
    select asks this, not the run's suffix.
    """

    runs = list(review.get("runs") or [])
    active = [run for run in runs if run.get("status") in ("running", "pending")
              and (run.get("telemetry") or {}).get("state") in ("starting", "training")]
    candidates = active or runs
    return str(candidates[-1]["run"]) if candidates else "accepted"


#: How long after a revision is accepted the project counts as being designed.
DESIGNING_WINDOW_S = 600
#: How long an evaluation directory with no report yet, written to that
#: recently, counts as an evaluation running; past it, it was abandoned.
EVALUATING_WINDOW_S = 120
#: Entries of one evaluation directory read to find its newest write.
EVALUATING_ENTRY_LIMIT = 256
#: The telemetry fields the stage overlay shows for the run it reads.
STAGE_TELEMETRY_KEYS = ("state", "reason", "age_s", "iteration", "total", "eta_s", "wall_time_s",
                        "reward_per_step", "loss", "best_iteration", "best_reward_per_step",
                        "warning", "spark")


def _stamp(value: Any) -> float | None:
    """An ISO 8601 time as epoch seconds, or ``None``."""

    try:
        parsed = _datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_datetime.timezone.utc)
    return parsed.timestamp()


def _iso(stamp: float) -> str:
    return _datetime.datetime.fromtimestamp(stamp, _datetime.timezone.utc).replace(microsecond=0).isoformat()


def _evaluation_running(root: Path, now: float) -> tuple[str, float] | None:
    """The newest evaluation directory that has no report yet and was
    written to inside :data:`EVALUATING_WINDOW_S`: an evaluation writes its
    report last (``evaluate.run_evaluation``), so until then the directory
    holds only its seeds' traces."""

    directory_name, report_name, _schema, _failing = _evaluation_constants()
    base = root / directory_name
    if not base.is_dir() or base.is_symlink():
        return None
    newest: tuple[str, float] | None = None
    for entry in base.iterdir():
        directory = _evaluation_dir(root, entry.name)
        if directory is None or (directory / report_name).exists():
            continue
        try:
            stamps = [directory.stat().st_mtime]
            for i, child in enumerate(directory.iterdir()):
                if i >= EVALUATING_ENTRY_LIMIT:
                    break
                stamps.append(child.stat().st_mtime)
        except OSError:
            continue
        written = max(stamps)
        if now - written <= EVALUATING_WINDOW_S and (newest is None or written > newest[1]):
            newest = (entry.name, written)
    return newest


def project_stage(root: Path, review: Mapping[str, Any]) -> dict[str, Any]:
    """What the project is doing now, for the 3D viewport's overlay (ADR-542).

    ``state`` is the first that holds of: ``evaluating`` (an evaluation is
    writing), ``training`` (the run the page reads is training, or its
    telemetry has gone quiet -- ``stale``), ``failed`` (the newest run failed
    and no revision was accepted after it), ``designing`` (a revision was
    accepted inside :data:`DESIGNING_WINDOW_S`), else ``idle``. ``since`` is
    when that state's evidence was written. ``run`` is the newest run
    training, a quiet one included, else the one :func:`default_run`
    picks, and ``training`` its telemetry with the
    reward and loss sparklines, or ``None`` when no run has telemetry.
    ``checkpoints`` is that run's :func:`checkpoint_rollouts` (ADR-545).
    Everything is read from the project directory; nothing is inferred
    about a process the files do not describe.
    """

    now = _datetime.datetime.now(_datetime.timezone.utc).timestamp()
    runs = list(review.get("runs") or [])
    trail = list(review.get("revisions") or [])
    accepted_at = _stamp(trail[0].get("saved_at")) if trail else None
    # The run training now, a quiet one included; else the one a fresh visit opens.
    active = [run for run in runs if run.get("status") in ("running", "pending")
              and (run.get("telemetry") or {}).get("state") in ("starting", "training", "stale")]
    name = str(active[-1]["run"]) if active else default_run(review)
    record = next((run for run in runs if run.get("run") == name), None)
    training = None
    if record is not None:
        telemetry = training_telemetry(root, record, detail=False, spark=True)
        if telemetry.get("state") not in ("missing", None):
            training = {key: telemetry.get(key) for key in STAGE_TELEMETRY_KEYS}
    stage: dict[str, Any] = {"state": "idle", "reason": "", "since": _iso(accepted_at) if accepted_at else None}
    evaluating = _evaluation_running(root, now)
    recorded_at = _stamp(record.get("recorded_at")) if record else None
    if evaluating:
        stage.update(state="evaluating", reason=f"evaluation {evaluating[0]} is running",
                     since=_iso(evaluating[1]))
    elif record is not None and record.get("status") in ("running", "pending") and training \
            and training["state"] in ("starting", "training", "stale"):
        stage.update(state="training", reason=training["reason"] if training["state"] == "stale" else "",
                     since=_iso(recorded_at) if recorded_at else None)
    elif record is not None and (record.get("status") == "failed" or (training or {}).get("state") == "failed") \
            and (accepted_at is None or (recorded_at or 0) >= accepted_at):
        stage.update(state="failed", reason=str(record.get("error") or (training or {}).get("reason") or "the run failed"),
                     since=_iso(recorded_at) if recorded_at else None)
    elif accepted_at is not None and now - accepted_at <= DESIGNING_WINDOW_S:
        stage.update(state="designing", reason=f"revision {trail[0].get('ordinal')} accepted")
    # The read run's checkpoint rollouts, for the 3D viewport's scrubber (ADR-545).
    checkpoints = checkpoint_rollouts(root, name) if record is not None else None
    return {**stage, "run": None if record is None else name, "runs": len(runs), "training": training,
            "checkpoints": checkpoints}


class ReviewProject:
    """What the server knows how to serve for one project, resolved per request.

    Records are read anew across requests: a walk that lands while the page is
    open shows up on its next poll, and a record that is rewritten from
    ``running`` to ``ok`` is read as it stands. The cost is one directory
    walk of ``runs/`` per request, which is what a review client should
    pay to never show a stale run — and it is bounded per run: the list
    carries each run's telemetry as a summary (state, latest metrics,
    sample and checkpoint counts) and reads no checkpoint bytes; histories
    and digest-verified checkpoints are served for one run at a time by
    ``/api/run/<name>`` (ADR-321). Only video digests are cached, bounded and
    keyed by file identity, size and nanosecond modification/change times.
    """

    def __init__(self, project_root: Path | str) -> None:
        self.root = Path(project_root).expanduser().resolve()

    def review(self) -> dict[str, Any]:
        review = read_project_review(self.root)
        for record in review["runs"]:
            record["telemetry"] = training_telemetry(self.root, record, detail=False)
        review["presentation"] = presentation(self.root, review["accepted"])
        review["evaluations"] = evaluations(self.root, review["accepted"])
        review["revisions"] = revision_trail(self.root)
        review["stage"] = project_stage(self.root, review)
        review["exports"] = export_listing(self.root)
        review["sections"] = section_listing(self.root)
        review["drawings"] = blueprint_listing(self.root)
        # Read-only; `cadex budgets --set` is how they change (ADR-517).
        review["budgets"] = {"stored": dict(read_agent_state(self.root).budgets)}
        review["served_at"] = _now()
        return review

    def run(self, name: str) -> dict[str, Any] | None:
        found = self._run(name)
        return found[0] if found else None

    def _run(self, name: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
        runs_dir = self.root / RUNS_DIRNAME
        if not name or name in (".", "..") or "/" in name or "\\" in name:
            return None
        run_dir = runs_dir / name
        if not runs_dir.is_dir() or not run_dir.is_dir() or run_dir.parent != runs_dir:
            return None
        record = read_run_record(run_dir, self.root)
        review = read_project_review(self.root)
        accepted = review["accepted"]
        recorded = (record.get("model") or {}).get("accepted_revision")
        if accepted.get("available") and recorded:
            record["relation"] = "current" if recorded == accepted["revision"] else "historical"
        else:
            record["relation"] = "unknown"
        return record, review

    def detail(self, name: str) -> dict[str, Any] | None:
        """The ``/api/run/<name>`` form: the record with its full telemetry
        (histories, digest-verified checkpoints — the one place they travel,
        ADR-321) and its disk use (ADR-322): what this run keeps under
        ``runs/<name>``, sized per reference, with project-level references
        other runs share sized once and named as shared rather than folded
        into this run's total. Neither is in the run list."""

        found = self._run(name)
        if found is None:
            return None
        record, review = found
        record["telemetry"] = training_telemetry(self.root, record)
        record["disk"] = run_disk_use(self.root, record, review["runs"])
        return record

    # -- files, each through an allowlist and the containment check --------

    def run_artifact(self, name: str, key: str) -> Path | None:
        record = self.run(name)
        if record is None or key not in RUN_ARTIFACT_KEYS:
            return None
        item = record["resolved"]["artifacts"].get(key) or {}
        if not item.get("exists") or item.get("error"):
            return None
        path = self.root / RUNS_DIRNAME / name / item["path"]
        return path if path.is_file() else None

    def project_artifact(self, name: str, key: str) -> Path | None:
        record = self.run(name)
        if record is None or key not in PROJECT_ARTIFACT_KEYS:
            return None
        item = record["resolved"]["project_artifacts"].get(key) or {}
        if not item.get("exists") or item.get("error"):
            return None
        path = self.root / item["path"]
        return path if path.is_file() else None

    def presentation_image(self, name: str) -> Path | None:
        """``hero.png`` or ``sheet.png``, only when the presentation offers it."""

        key = name[:-4] if name.endswith(".png") else ""
        offered = presentation(self.root, read_accepted_identity(self.root))
        if key not in offered.get("files", {}):
            return None
        return self.root / offered["source"] / name

    def exported_file(self, revision: str, name: str) -> Path | None:
        """A file ``export_listing`` offers for the accepted revision, and nothing else."""

        offered = export_listing(self.root)
        if offered.get("revision") != revision or name not in {f["name"] for f in offered.get("files", [])}:
            return None
        return self.root / EXPORT_DIR / revision / name

    def section_file(self, revision: str, name: str) -> Path | None:
        """A cut's SVG that ``section_listing`` offers for the accepted revision, and nothing else."""

        offered = section_listing(self.root)
        if offered.get("revision") != revision or name not in {cut["name"] for cut in offered["cuts"]}:
            return None
        return self.root / SECTION_DIR / revision / name / "section.svg"

    def blueprint_file(self, name: str) -> Path | None:
        """A stored sheet ``blueprint_listing`` offers, and nothing else."""

        if name not in {sheet["file"] for sheet in blueprint_listing(self.root)["sheets"]}:
            return None
        return self.root / BLUEPRINT_DIR / name

    def run_video(self, name: str, index: int) -> Path | None:
        record = self.run(name)
        if record is None or index < 0:
            return None
        videos = record["resolved"]["videos"]
        if index >= len(videos):
            return None
        item = videos[index]
        if not item.get("exists") or item.get("error"):
            return None
        path = self.root / RUNS_DIRNAME / name / item["path"]
        return path if path.is_file() else None

    def run_document(self, name: str, relative: str) -> Path | None:
        record = self.run(name)
        if record is None:
            return None
        docs = record.get("project_docs") or {}
        if not docs.get("dir") or relative not in (docs.get("files") or {}):
            return None
        item = resolve_reference(self.root / RUNS_DIRNAME / name, f"{docs['dir']}/{relative}")
        if not item["exists"] or item["error"]:
            return None
        path = self.root / RUNS_DIRNAME / name / item["path"]
        return path if path.is_file() else None

    def current_document(self, relative: str) -> Path | None:
        review = read_project_review(self.root)
        allowed = {name for name, present in review["docs"].items()
                   if name != "domain" and present}
        allowed.update(review["docs"]["domain"])
        if relative not in allowed:
            return None
        item = resolve_reference(self.root, relative)
        if not item["exists"] or item["error"]:
            return None
        path = self.root / item["path"]
        return path if path.is_file() else None

    def run_mesh(self, name: str, output: str) -> Path | None:
        record = self.run(name)
        if record is None:
            return None
        model = run_model(self.root, record)
        wanted = f"/mesh/run/{name}/{output}.stl"
        if not any(entry.get("mesh") == wanted for entry in model["components"]):
            return None
        if model.get("source") == "assembled model retained before training":
            path = self.root / RUNS_DIRNAME / name / "training-view" / f"{output}.stl"
        else:
            artifacts = record["resolved"]["artifacts"]
            anchor = artifacts["trace"]["path"] or artifacts["model_xml"]["path"]
            path = (self.root / RUNS_DIRNAME / name / anchor).parent / f"{output}.stl"
        if not path.is_file() or path.is_symlink():
            return None
        # Served bytes resolve inside the project root, whatever the run
        # directory's own links say (ADR-318).
        try:
            path.resolve().relative_to(self.root.resolve())
        except ValueError:
            return None
        return path

    def accepted_mesh(self, output: str) -> bytes | None:
        found = self.accepted_mesh_entry(output)
        return None if found is None else found[1]

    def accepted_mesh_entry(self, output: str) -> tuple[str, bytes] | None:
        """``(etag, stl)`` for one accepted output, converted once per tessellation.

        The tag is the tessellation's own content hash, so a part a rebuild
        left as it was keeps its tag across revisions and a browser that has
        it is answered 304.
        """

        model = accepted_model(self.root)
        artifact = (model.get("meshes") or {}).get(output)
        if not model["available"] or not artifact:
            return None
        staging, _manifest, _reason = _accepted_staging(self.root)
        if staging is None:
            return None
        sidecar_path = staging / "display" / (Path(artifact).name.replace(".tess.bin", ".tess.json"))
        artifact_path = staging / artifact
        try:
            sidecar_bytes, data = sidecar_path.read_bytes(), artifact_path.read_bytes()
        except OSError:
            return None
        etag = '"' + hashlib.sha256(sidecar_bytes + b"\0" + data).hexdigest()[:40] + '"'
        with _MEMO_LOCK:
            held = _STL_MEMO.get(etag)
            if held is not None:
                _STL_MEMO.move_to_end(etag)
                return etag, held
        try:
            sidecar = json.loads(sidecar_bytes)
            body = tessellation_to_stl(sidecar, data)
        except (ValueError, OSError):
            return None
        with _MEMO_LOCK:
            global _STL_MEMO_BYTES
            _STL_MEMO[etag] = body
            _STL_MEMO_BYTES += len(body)
            while _STL_MEMO_BYTES > STL_MEMO_LIMIT and len(_STL_MEMO) > 1:
                _STL_MEMO_BYTES -= len(_STL_MEMO.popitem(last=False)[1])
        return etag, body


#: Converted meshes by content tag, newest kept, at most this many bytes.
_STL_MEMO: "OrderedDict[str, bytes]" = OrderedDict()
_STL_MEMO_BYTES = 0
STL_MEMO_LIMIT = 512 * 1024 * 1024
#: A response at least this long, of a type that compresses, is gzipped for
#: a client that accepts it; a mesh's compressed form is kept beside it.
GZIP_MIN_BYTES = 1024
GZIP_TYPES = ("application/json", "text/", "model/stl", "image/svg+xml")
_GZIP_MEMO: "OrderedDict[str, bytes]" = OrderedDict()
_GZIP_MEMO_SIZE = 512



#: Where the dashboard's Export button has ``cadex export`` write, one
#: directory per accepted revision (ADR-509). Under ``/review/``, which the
#: project's own ignore rules keep out of its commits: a rebuild re-makes it.
EXPORT_DIR = "review/export"
EXPORT_FORMATS = ("step", "stl", "brep")
#: What the export directory may serve: the converted geometry and the
#: staged non-geometry outputs ``cadex export`` copies beside it.
EXPORT_SUFFIXES = (".step", ".stl", ".brep", ".xml", ".json", ".ply")
REVISION_HASH = re.compile(r"^[0-9a-f]{64}$")


def export_listing(root: Path) -> dict[str, Any]:
    """The accepted revision's exported files, as ``cadex export`` left them.

    Only the accepted revision's directory is offered, so a file exported
    from an earlier design never reads as this one; an older directory
    stays on disk until the project is cleaned, and is not served.
    """

    accepted = read_accepted_identity(root)
    revision = accepted.get("revision") if accepted.get("available") else None
    if not isinstance(revision, str) or not REVISION_HASH.match(revision):
        return {"available": False, "reason": "no accepted revision to export"}
    directory = root / EXPORT_DIR / revision
    files = []
    if directory.is_dir() and not directory.is_symlink():
        for path in sorted(directory.iterdir()):
            if path.suffix.lower() in EXPORT_SUFFIXES and path.is_file() and not path.is_symlink():
                files.append({"name": path.name, "bytes": path.stat().st_size,
                              "url": f"export/{revision}/{quote(path.name, safe='')}"})
    if not files:
        return {"available": False, "revision": revision,
                "reason": "not exported yet: Export runs cadex export for this revision"}
    return {"available": True, "revision": revision, "files": files}


BLUEPRINT_DIR = "blueprints"
BLUEPRINT_INDEX = "blueprints.json"
#: ``{ordinal:04d}-{slug}.png`` as ``CadexBlueprints.store_project_blueprint`` names a sheet.
BLUEPRINT_FILE = re.compile(r"^[0-9]{4,}-[A-Za-z0-9._-]{1,80}\.png$")


def blueprint_listing(root: Path) -> dict[str, Any]:
    """The project's stored drawing sheets (ADR-516), newest first, read-only.

    Read from ``blueprints/blueprints.json``, the index the engine's store
    writes on ``put_blueprint``; a sheet is served at ``blueprint/<file>``
    only when this lists it. Every version is listed, each with the
    revision it drew, so a sheet of an earlier design reads as one.
    """

    index = _load_json(root / BLUEPRINT_DIR / BLUEPRINT_INDEX)
    accepted = read_accepted_identity(root)
    current = accepted.get("revision") if accepted.get("available") else None
    sheets = []
    for entry in (index or {}).get("entries") or []:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("file") or "")
        path = root / BLUEPRINT_DIR / name
        if not BLUEPRINT_FILE.match(name) or path.is_symlink() or not path.is_file():
            continue
        revision = str(entry.get("revision") or "")
        sheets.append({
            "file": name, "name": str(entry.get("name") or entry.get("label") or name),
            "version": int(entry.get("version") or 1), "revision": revision,
            "relation": "current" if current and revision == current else "earlier",
            "created_at": str(entry.get("created_at") or ""), "bytes": path.stat().st_size,
            "url": f"blueprint/{quote(name, safe='')}",
        })
    sheets.reverse()
    if not sheets:
        return {"available": False, "sheets": [],
                "reason": "no drawing yet: the agent's draw_blueprint stores one with the project"}
    return {"available": True, "sheets": sheets}


SECTION_DIR = "review/section"
SECTION_PLANES = ("XY", "XZ", "YZ")
#: ``<plane>-<offset>`` as ``write_section`` names a cut's directory.
SECTION_NAME = re.compile(r"^(XY|XZ|YZ)-[0-9eE.+-]{1,32}$")


def section_listing(root: Path) -> dict[str, Any]:
    """The accepted revision's section cuts, as ``cadex section`` left them, newest first.

    Read from ``review/section/<revision>/<plane>-<offset>/summary.json``;
    only the accepted revision's cuts are offered, and a cut is served at
    ``section/<revision>/<name>/section.svg`` only when this lists it.
    """

    accepted = read_accepted_identity(root)
    revision = accepted.get("revision") if accepted.get("available") else None
    if not isinstance(revision, str) or not REVISION_HASH.match(revision):
        return {"available": False, "reason": "no accepted revision to cut", "cuts": []}
    directory = root / SECTION_DIR / revision
    cuts = []
    if directory.is_dir() and not directory.is_symlink():
        for path in directory.iterdir():
            summary_path, svg_path = path / "summary.json", path / "section.svg"
            if (not SECTION_NAME.match(path.name) or path.is_symlink() or not summary_path.is_file()
                    or summary_path.is_symlink() or not svg_path.is_file() or svg_path.is_symlink()):
                continue
            summary = _load_json(summary_path)
            if not summary or summary.get("revision") != revision or summary.get("plane") not in SECTION_PLANES:
                continue
            objects = summary.get("objects") or {}
            cuts.append({
                "name": path.name, "plane": summary["plane"], "offset_mm": summary.get("offset_mm"),
                "offset_source": summary.get("offset_source") or "explicit",
                "status": summary.get("status"), "objects_cut": summary.get("objects_cut"),
                "objects": len(objects), "missed": sorted(name for name, obj in objects.items()
                                                          if (obj or {}).get("status") != "ok"),
                "approximation": summary.get("approximation"),
                "svg": f"section/{revision}/{quote(path.name, safe='')}/section.svg",
                "mtime": summary_path.stat().st_mtime,
            })
    cuts.sort(key=lambda cut: -cut.pop("mtime"))
    if not cuts:
        return {"available": False, "revision": revision, "cuts": [],
                "reason": "no section cut yet: `cadex section` cuts this revision"}
    return {"available": True, "revision": revision, "cuts": cuts}


def revision_trail(root: Path) -> list[dict[str, Any]]:
    """The stored trail for the page, newest first, without sources or values."""

    keep = ("ordinal", "revision", "saved_at", "outputs")
    return [{key: entry.get(key) for key in keep} for entry in reversed(read_revision_history(root))]


# The two ways Linux reports a peer that went away mid-write: EPIPE, or
# ECONNRESET when the peer closed with bytes still unread (ADR-324).
CLIENT_GONE = (BrokenPipeError, ConnectionResetError)


class ReviewHandler(BaseHTTPRequestHandler):
    """One request per connection (``Connection: close`` on every reply):
    a review server that has been shut down keeps no handler thread alive
    on a browser's idle keep-alive socket, so "the server went away" means
    what it says to the page — and so a restart is a restart."""

    server_version = "cadex-review/1"
    protocol_version = "HTTP/1.1"

    @property
    def project(self) -> ReviewProject:
        return self.server.project  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        log = getattr(self.server, "log", None)
        if log is not None:
            log("%s - %s" % (self.address_string(), format % args))

    # -- responses ---------------------------------------------------------

    def _send_bytes(self, body: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK,
                    extra: Mapping[str, str] | None = None, memo: str | None = None) -> None:
        self.close_connection = True
        headers = {"Cache-Control": "no-store", **(extra or {})}
        compressible = len(body) >= GZIP_MIN_BYTES and content_type.startswith(GZIP_TYPES)
        if compressible:
            headers["Vary"] = "Accept-Encoding"
        if compressible and "gzip" in self.headers.get("Accept-Encoding", ""):
            body = self._gzip(body, memo)
            headers["Content-Encoding"] = "gzip"
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    @staticmethod
    def _gzip(body: bytes, memo: str | None) -> bytes:
        """``body`` gzipped; a body with a content tag is compressed once."""

        if memo is not None:
            with _MEMO_LOCK:
                held = _GZIP_MEMO.get(memo)
                if held is not None:
                    _GZIP_MEMO.move_to_end(memo)
                    return held
        packer = zlib.compressobj(6 if memo is not None else 5, zlib.DEFLATED, 31)
        packed = packer.compress(body) + packer.flush()
        if memo is not None:
            with _MEMO_LOCK:
                _GZIP_MEMO[memo] = packed
                while len(_GZIP_MEMO) > _GZIP_MEMO_SIZE:
                    _GZIP_MEMO.popitem(last=False)
        return packed

    def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        self._send_bytes(json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n",
                         "application/json; charset=utf-8", status)

    def _not_found(self, what: str) -> None:
        self._send_json({"error": "not found", "what": what}, HTTPStatus.NOT_FOUND)

    def _send_file(self, path: Path, *, download: bool, headers: Mapping[str, str] | None = None) -> None:
        """A permitted file, whole or as one byte range (video seeking)."""

        content_type = CONTENT_TYPES.get(path.suffix.lower()) or (
            mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        try:
            size = path.stat().st_size
            handle = path.open("rb")
        except OSError:
            self._not_found(path.name)
            return
        extra = {"Accept-Ranges": "bytes", **(headers or {})}
        if download:
            # HTTP headers must stay ASCII; retain Unicode in the encoded name.
            fallback = "".join(c if 32 <= ord(c) < 127 and c not in '\\"%'
                               else "_" for c in path.name)
            disposition = f'attachment; filename="{fallback}"'
            if fallback != path.name:
                disposition += "; filename*=UTF-8''" + quote(path.name, safe="")
            extra["Content-Disposition"] = disposition
        start, end = 0, size - 1
        status = HTTPStatus.OK
        range_header = self.headers.get("Range", "")
        if range_header.startswith("bytes=") and size:
            spec = range_header[len("bytes="):].split(",")[0].strip()
            first, _, last = spec.partition("-")
            try:
                if first:
                    start = int(first)
                    end = int(last) if last else size - 1
                else:
                    start = max(size - int(last), 0)
            except ValueError:
                start, end = 0, size - 1
            if start > end or start >= size:
                handle.close()
                self._send_bytes(b"", content_type, HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE,
                                 {"Content-Range": f"bytes */{size}"})
                return
            end = min(end, size - 1)
            status = HTTPStatus.PARTIAL_CONTENT
            extra["Content-Range"] = f"bytes {start}-{end}/{size}"
        length = end - start + 1 if size else 0
        with handle:
            self.close_connection = True
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-store")
            for key, value in extra.items():
                self.send_header(key, value)
            self.end_headers()
            if self.command == "HEAD":
                return
            handle.seek(start)
            remaining = length
            try:
                while remaining > 0:
                    chunk = handle.read(min(1 << 20, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
            except CLIENT_GONE:
                # A browser that cancelled a download or abandoned a video
                # range request (ADR-324): the client's choice, not a fault
                # of ours, so one line rather than socketserver's traceback.
                self.log_message("client closed the connection after %d of %d bytes of %s",
                                 length - remaining, length, path.name)

    # -- routing -----------------------------------------------------------

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_GET(self) -> None:  # noqa: N802
        parts = urlsplit(self.path)
        segments = [unquote(segment) for segment in parts.path.split("/") if segment]
        download = "download=1" in parts.query.split("&")
        if any(segment in (".", "..") or "\\" in segment for segment in segments):
            self._not_found(parts.path)
            return
        try:
            projects = getattr(self.server, "projects", None)
            if projects is None:
                self._route(self.project, segments, download)
            else:
                self._route_projects(projects, parts.path, segments, download)
        except CLIENT_GONE:
            pass

    def _route_projects(self, projects: "ProjectsDirectory", path: str, segments: list[str],
                        download: bool) -> None:
        """The projects index at ``/``; each project's page under ``/p/<name>/``."""

        if not segments:
            segments = ["projects.html"]
        head, rest = segments[0], segments[1:]
        if len(segments) == 1 and head in PROJECTS_STATIC_FILES:
            content_type, file = PROJECTS_STATIC_FILES[head]
            self._send_bytes(file.read_bytes(), content_type)
            return
        if segments == ["api", "projects"]:
            self._send_json(projects.listing())
            return
        if head == "p" and rest:
            project = projects.project(rest[0])
            if project is None:
                self._not_found(f"project {rest[0]!r}")
                return
            if len(rest) == 1 and not path.endswith("/"):
                # The page's URLs are relative to its own directory.
                self._send_bytes(b"", "text/plain; charset=utf-8", HTTPStatus.MOVED_PERMANENTLY,
                                 {"Location": "/p/" + quote(rest[0], safe="") + "/"})
                return
            self._route(project, rest[1:], download)
            return
        self._not_found("/".join(segments))

    def _route(self, project: ReviewProject, segments: list[str], download: bool) -> None:
        if not segments:
            segments = ["index.html"]
        head, rest = segments[0], segments[1:]
        if len(segments) == 1 and head in STATIC_FILES:
            content_type, path = STATIC_FILES[head]
            self._send_bytes(path.read_bytes(), content_type)
            return
        if head == "api":
            if rest == ["project"]:
                self._send_json(project.review())
                return
            if rest[:1] == ["run"] and len(rest) == 2:
                record = project.detail(rest[1])
                if record is None:
                    self._not_found(f"run {rest[1]!r}")
                    return
                self._send_json(record)
                return
            if rest[:1] == ["policy-origin"] and len(rest) == 2:
                if project.run(rest[1]) is None:
                    self._not_found(f"run {rest[1]!r}")
                    return
                self._send_json(policy_lineage(project.root, rest[1]))
                return
            if rest[:1] == ["evaluation"] and len(rest) == 2:
                detail = evaluation_detail(project.root, rest[1], read_accepted_identity(project.root))
                if detail is None:
                    self._not_found(f"evaluation {rest[1]!r}")
                    return
                self._send_json(detail)
                return
            if rest == ["model", "accepted"]:
                self._send_json(accepted_model(project.root))
                return
            if rest[:2] == ["model", "run"] and len(rest) == 3:
                record = project.run(rest[2])
                if record is None:
                    self._not_found(f"run {rest[2]!r}")
                    return
                self._send_json(run_model(project.root, record))
                return
            if rest[:2] == ["playback", "run"] and len(rest) == 3:
                record = project.run(rest[2])
                if record is None:
                    self._not_found(f"run {rest[2]!r}")
                    return
                self._send_json(run_playback(project.root, record))
                return
            if rest[:2] == ["playback", "checkpoint"] and len(rest) == 4:
                played = (checkpoint_playback(project.root, rest[2], rest[3])
                          if project.run(rest[2]) is not None else None)
                if played is None:
                    self._not_found("/".join(segments))
                    return
                self._send_json(played)
                return
            self._not_found("/".join(segments))
            return
        path: Path | None = None
        if head == "mesh" and rest[:1] == ["accepted"] and len(rest) == 2 and rest[1].endswith(".stl"):
            found = project.accepted_mesh_entry(rest[1][:-4])
            if found is None:
                self._not_found("/".join(segments))
                return
            etag, body = found
            # Revalidated on every use, so a rebuild's changed part is never stale.
            cache = {"Cache-Control": "no-cache", "ETag": etag}
            if etag in [tag.strip() for tag in self.headers.get("If-None-Match", "").split(",")]:
                self._send_bytes(b"", CONTENT_TYPES[".stl"], HTTPStatus.NOT_MODIFIED, cache)
                return
            self._send_bytes(body, CONTENT_TYPES[".stl"], extra=cache, memo=etag)
            return
        if head == "mesh" and rest[:1] == ["run"] and len(rest) == 3 and rest[2].endswith(".stl"):
            path = project.run_mesh(rest[1], rest[2][:-4])
        elif head == "artifact" and rest[:1] == ["run"] and len(rest) == 3:
            path = project.run_artifact(rest[1], rest[2])
        elif head == "artifact" and rest[:1] == ["project"] and len(rest) == 3:
            path = project.project_artifact(rest[1], rest[2])
        elif head == "presentation" and len(rest) == 1:
            path = project.presentation_image(rest[0])
        elif head == "export" and len(rest) == 2:
            path = project.exported_file(rest[0], rest[1])
        elif head == "blueprint" and len(rest) == 1:
            path = project.blueprint_file(rest[0])
        elif head == "section" and len(rest) == 3 and rest[2] == "section.svg":
            path = project.section_file(rest[0], rest[1])
        elif head == "video" and rest[:1] == ["run"] and len(rest) == 3 and rest[2].isdigit():
            path = project.run_video(rest[1], int(rest[2]))
        elif head == "evaluation" and len(rest) == 2:
            path = evaluation_file(project.root, rest[0], rest[1])
        elif head == "doc" and rest[:1] == ["run"] and len(rest) >= 3:
            path = project.run_document(rest[1], "/".join(rest[2:]))
        elif head == "doc" and rest[:1] == ["current"] and len(rest) >= 2:
            path = project.current_document("/".join(rest[1:]))
        if path is None:
            self._not_found("/".join(segments))
            return
        self._send_file(path, download=download)


class ReviewServer(ThreadingHTTPServer):
    """One project, one address. ``url`` is where a browser opens it."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, project_root: Path | str, host: str, port: int,
                 log: Callable[[str], None] | None = None) -> None:
        self.project = ReviewProject(project_root)
        self.log = log
        super().__init__((host, port), ReviewHandler)

    @property
    def url(self) -> str:
        host, port = self.server_address[:2]
        shown = f"[{host}]" if ":" in str(host) else str(host)
        return f"http://{shown}:{port}/"


class ProjectsDirectory:
    """Every project directly under one directory, found anew per request.

    A project is a subdirectory holding the project manifest
    (``script.json``); a project created while the page is open appears on
    its next poll. Listing reads each manifest and counts ``runs/`` entries,
    and nothing else, so a directory of many projects stays cheap to list.
    """

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).expanduser().resolve()

    def _names(self) -> list[str]:
        if not self.root.is_dir():
            return []
        return sorted(child.name for child in self.root.iterdir()
                      if child.is_dir() and not child.name.startswith(".")
                      and (child / PROJECT_SCRIPT_FILENAME).is_file())

    def project(self, name: str) -> ReviewProject | None:
        if name not in self._names():
            return None
        return ReviewProject(self.root / name)

    def listing(self) -> dict[str, Any]:
        projects = []
        for name in self._names():
            root = self.root / name
            runs = root / RUNS_DIRNAME
            projects.append({
                "name": name,
                "url": "/p/" + quote(name, safe="") + "/",
                "accepted": read_accepted_identity(root),
                "runs": sum(1 for child in runs.iterdir() if child.is_dir()) if runs.is_dir() else 0,
            })
        return {"schema": PROJECTS_SCHEMA, "root": self.root.name, "projects": projects,
                "served_at": _now()}

class ProjectsServer(ThreadingHTTPServer):
    """A directory of projects, one address: the index lists them, and each
    project's review page is served under ``/p/<name>/``."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, projects_root: Path | str, host: str, port: int,
                 log: Callable[[str], None] | None = None) -> None:
        self.projects = ProjectsDirectory(projects_root)
        self.log = log
        super().__init__((host, port), ReviewHandler)

    url = ReviewServer.url


def serve_projects(projects_root: Path | str, host: str = "127.0.0.1", port: int = 0,
                   log: Callable[[str], None] | None = None) -> tuple[ProjectsServer, threading.Thread]:
    """As :func:`serve`, over a directory of projects (``cadex app``)."""

    server = ProjectsServer(projects_root, host, port, log=log)
    thread = threading.Thread(target=server.serve_forever, name="cadex-app", daemon=True)
    thread.start()
    return server, thread


def serve(project_root: Path | str, host: str = "127.0.0.1", port: int = 0,
          log: Callable[[str], None] | None = None) -> tuple[ReviewServer, threading.Thread]:
    """Bind and start serving in a daemon thread; the caller stops it.

    ``port=0`` takes a free port; ``server.url`` says which. Stop with
    ``server.shutdown()`` then ``server.server_close()``.
    """

    server = ReviewServer(project_root, host, port, log=log)
    thread = threading.Thread(target=server.serve_forever, name="cadex-review", daemon=True)
    thread.start()
    return server, thread
