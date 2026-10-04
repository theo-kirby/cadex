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

Writing is the dashboard's light steering (orun2 D2, ADR-503 to ADR-506, ADR-509),
and it has no write path of its own: each POST runs the very ``cadex``
command a person would type (``params --set``, ``-p PROMPT`` for a
design turn whose stderr is the live transcript, ``comment`` for a
note on the design or a picked part (ADR-505), ``revision`` for a verdict
(ADR-506), or ``export`` into the ignored ``review/export/``, ADR-509), as a child process the
way ``cadex walk`` runs its legs, so the project lock, the ``PROGRESS.md``
row and the project commit are the CLI's. Every POST needs the per-launch token the
server writes into the page it serves, and a browser's ``Origin``, when
sent, must be this server's own; anything else is refused before it is
routed.

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
import base64
import binascii
import datetime as _datetime
import hashlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import hmac
import math
import mimetypes
import os
import re
import secrets
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
from typing import Any, Callable, Mapping
from urllib.parse import parse_qs, quote, unquote, urlsplit
from xml.etree import ElementTree

from .agent import IMAGE_LIMIT, IMAGES_PER_TURN, ImageAttachment, ImageRefused, image_attachment
from .comments import read_comments, read_notes
from .project_docs import progress_rows
from .revisions import read_history as read_revision_history
from .walk import run_leg
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
       ("three.module.js", "floor.js", "environment.js", "review_scene.js", "stl.js", "capture.js")},
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
#: The CLI agent turns across a projects directory, ``/api/turns`` (ADR-519).
TURNS_SCHEMA = "cadex-agent-turns-v1"
#: How many turns ``/api/turns`` carries, newest kept.
TURNS_SHOWN = 100
#: An Ouroboros run's page, under ``/r/<run>/`` (ADR-513).
RUN_STATIC_FILES = {
    "run.html": ("text/html; charset=utf-8", STATIC_DIR / "run.html"),
    "run.js": ("text/javascript; charset=utf-8", STATIC_DIR / "run.js"),
    "markdown.js": ("text/javascript; charset=utf-8", STATIC_DIR / "markdown.js"),
    "review.css": STATIC_FILES["review.css"],
}
RUNS_SCHEMA = "cadex-ouroboros-runs-v1"
RUN_SCHEMA = "cadex-ouroboros-run-v1"
#: A run directory's name: what ``ouroboros run`` mints, and nothing a path could hide in.
OUROBOROS_RUN_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
#: A run's branch, as ``git`` is given it: a plain ref name, never an option.
OUROBOROS_BRANCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
#: One charter criterion: a checkbox at the start of a line under ``## Done criteria``.
CHARTER_ITEM = re.compile(r"^- \[([ xX])\] ?(.*)$")
#: A run's probe material is ``docs/probes/<run>/`` in the checkout, served
#: read-only under ``/r/<run>/probes/`` (ADR-515): only these suffixes, so no
#: page the dashboard's origin would run is ever served from the repo.
PROBE_KINDS = {".png": "image", ".jpg": "image", ".jpeg": "image", ".svg": "image",
               ".md": "text", ".txt": "text", ".py": "text",
               ".json": "data", ".jsonl": "data", ".csv": "data",
               ".mp4": "video", ".webm": "video"}
#: One path segment of a probe file: no dot-file, no separator, no ``..``.
PROBE_SEGMENT = re.compile(r"^[A-Za-z0-9_+-][A-Za-z0-9._+-]{0,127}$")
#: The most files one run's probe listing names; the rest are counted.
PROBE_LISTING_LIMIT = 2000
#: Served probe files run nothing and are never sniffed into something that does.
PROBE_HEADERS = {"Content-Security-Policy": "sandbox", "X-Content-Type-Options": "nosniff"}
#: A run's records are the checkout's hypergraph record nodes whose ``## Repo``
#: names the run's branch (ADR-518); the repo paths under ``docs/`` they name
#: are the artifacts its page links, served under ``/r/<run>/linked/``.
RECORD_DIR = Path(".hypergraph") / "graph" / "record"
RECORD_PATH_MENTION = re.compile(r"(?<![\w/.~-])docs(?:/[A-Za-z0-9_+-][A-Za-z0-9._+-]*)+/?")
#: The most artifacts one record lists; the rest are counted.
RECORD_ARTIFACT_LIMIT = 24
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


def accepted_model(project_root: Path | str) -> dict[str, Any]:
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


def _telemetry_summary(result: dict[str, Any], reported: int) -> dict[str, Any]:
    """The run-list form of a telemetry result (ADR-321): the same state,
    reason and latest metrics, with each history replaced by its sample
    count and the checkpoint list by how many entries it reports. Nothing
    here is hashed and nothing grows with training length, so a poll of the
    whole run list costs a bounded amount per run however long the history."""

    result["samples"] = {key: len(result.pop(key, []) or []) for key in HISTORY_KEYS}
    result.pop("checkpoints", None)
    result["checkpoints_reported"] = reported
    result["summary"] = True
    return result


def training_telemetry(root: Path, record: Mapping[str, Any], *, detail: bool = True) -> dict[str, Any]:
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
        return value if detail else _telemetry_summary(value, reported)

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
        for key in ("iteration", "total", "reward_per_step", "loss", "episode_steps"):
            value = data.get(key)
            if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise ValueError("invalid metric")
            result[key] = value
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
        return _telemetry_summary(result, reported)
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
                                   if isinstance(row, dict)]},
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


def agent_turns(root: Path) -> list[dict[str, Any]]:
    """A project's CLI agent turns, oldest first, from what the CLI already
    keeps (ADR-519): read-only, and no store of their own (A3).

    A turn is a ``prompt`` row of ``PROGRESS.md`` -- one per turn the CLI
    accepted, whether typed at a terminal or started from the dashboard,
    with its time, the revision and digest it left and its words. The row's
    revision prefix finds the rest: the revision's ordinal in the trail
    (``script_history/``), the owner's verdicts on it and the notes the agent
    left on it (``comments.jsonl``). No transcript is kept, so none is shown.
    """

    rows = [row for row in progress_rows(root) if row["run"] == "prompt"]
    if not rows:
        return []
    trail = read_revision_history(root)
    comments = read_comments(root)
    notes = read_notes(root)
    turns = []
    for row in rows:
        short = row["revision"].lower()

        def on(revision: Any) -> bool:
            return bool(short) and str(revision or "").lower().startswith(short)

        entry = next((item for item in trail if on(item.get("revision"))), None)
        verdicts = [{"verdict": comment["verdict"], "at": comment["at"], "text": comment["text"]}
                    for comment in comments if comment.get("verdict") and on(comment["revision"])]
        what = row["what"].removeprefix("prompt: ")
        prompt, _arrow, said = what.partition(" → ")
        turns.append({
            "when": row["when"], "prompt": prompt, "said": said,
            "revision": str(entry["revision"]) if entry else short,
            "ordinal": entry.get("ordinal") if entry else None,
            "digest": row["digest"],
            "verdict": verdicts[-1]["verdict"] if verdicts else None,
            "verdicts": verdicts,
            "notes": [{"type": note["type"], "text": note["text"], "answered": bool(note["answers"])}
                      for note in notes if on(note["revision"])],
        })
    return turns


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
        review["comments"] = read_comments(self.root)[-COMMENTS_SHOWN:]
        review["notes"] = [dict(note, url=f"note/{note['id']}" if self.note_artifact(note["id"]) else "")
                           for note in read_notes(self.root)[-NOTES_SHOWN:]]
        review["revisions"] = revision_trail(self.root)
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

    def note_artifact(self, note_id: str) -> Path | None:
        """The file an agent note flags (ADR-512), when it is one the page
        can show: inside the project, still present, and of a served type."""

        note = next((note for note in read_notes(self.root) if note["id"] == note_id), None)
        if note is None or not note["artifact"]:
            return None
        path = (self.root / note["artifact"]).resolve()
        if not path.is_relative_to(self.root) or not path.is_file() \
                or path.suffix.lower() not in NOTE_ARTIFACT_SUFFIXES:
            return None
        return path

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
        model = accepted_model(self.root)
        artifact = (model.get("meshes") or {}).get(output)
        if not model["available"] or not artifact:
            return None
        staging, _manifest, _reason = _accepted_staging(self.root)
        if staging is None:
            return None
        sidecar_path = staging / "display" / (Path(artifact).name.replace(".tess.bin", ".tess.json"))
        sidecar = _load_json(sidecar_path)
        artifact_path = staging / artifact
        if not sidecar or not artifact_path.is_file():
            return None
        try:
            return tessellation_to_stl(sidecar, artifact_path.read_bytes())
        except (ValueError, OSError):
            return None


#: The page's write token, as the served ``index.html`` carries it: the
#: placeholder is replaced, per response, with the launch's own token.
WRITE_TOKEN_META = b'<meta name="cadex-write-token" content="">'
WRITE_TOKEN_HEADER = "X-Cadex-Token"
#: Bound on a POST body; a parameter change is a few dozen bytes.
WRITE_BODY_LIMIT = 64 * 1024
#: Bound on a design turn's body, which may carry its images as base64
#: (ADR-507): every one at the CLI's limit, plus the prompt.
TURN_BODY_LIMIT = IMAGES_PER_TURN * (IMAGE_LIMIT * 4 // 3 + 4) + WRITE_BODY_LIMIT
#: How long one dashboard write may run before it is stopped, in seconds.
WRITE_TIMEOUT_S = 300.0
PARAM_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def write_params(root: Path, values: Any) -> tuple[HTTPStatus, dict[str, Any]]:
    """``cadex params --project ROOT --set NAME=VALUE ...``, as a child.

    The dashboard's slider and the command line are one write path (A3):
    this spawns the CLI exactly as ``cadex walk`` spawns a leg, without
    ``--wait``, so a project another run holds is refused rather than
    queued, and the reply is the child's own envelope.
    """

    from .report import EXIT_OK, EXIT_REJECTED, EXIT_USAGE  # report imports this module

    if not isinstance(values, Mapping) or not values:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "values must be a non-empty object."}
    argv = ["params", "--project", str(root)]
    for name, value in sorted(values.items()):
        if not isinstance(name, str) or not PARAM_NAME.match(name):
            return HTTPStatus.BAD_REQUEST, {"ok": False, "error": f"not a parameter name: {name!r}"}
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            return HTTPStatus.BAD_REQUEST, {"ok": False, "error": f"{name} must be a finite number."}
        argv += ["--set", f"{name}={value!r}"]
    leg = run_leg("params", argv + ["--json"], timeout=WRITE_TIMEOUT_S)
    envelope = leg.envelope
    reply = {"ok": leg.code == EXIT_OK and envelope.get("ok") is True, "exit": leg.code,
             "seconds": round(leg.seconds, 3), "command": ["cadex", *argv]}
    for key in ("accepted_revision", "digest", "params", "error"):
        if key in envelope:
            reply[key] = envelope[key]
    if reply["ok"]:
        return HTTPStatus.OK, reply
    if leg.code == EXIT_USAGE:
        return HTTPStatus.BAD_REQUEST, reply
    return (HTTPStatus.UNPROCESSABLE_ENTITY if leg.code == EXIT_REJECTED else HTTPStatus.CONFLICT), reply


def write_comment(root: Path, body: Mapping[str, Any]) -> tuple[HTTPStatus, dict[str, Any]]:
    """``cadex comment --project ROOT [--part NAME] -- TEXT``, as a child (ADR-505).

    The comment box and the command line are one write path (A3). The text
    travels after ``--`` and the part as one ``--part=`` token, so neither
    is read as a flag; the bounds are the CLI's own, checked here only so a
    bad body spawns nothing.
    """

    from .comments import COMMENT_LIMIT, PART_LIMIT
    from .report import EXIT_OK, EXIT_USAGE  # report imports this module

    text, part, reply_to = body.get("text"), body.get("part", ""), body.get("reply_to", "")
    if not isinstance(text, str) or not text.strip():
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "text must be non-empty text."}
    if len(text) > COMMENT_LIMIT or "\x00" in text:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": f"a comment is at most {COMMENT_LIMIT} characters of text."}
    if not isinstance(part, str) or len(part) > PART_LIMIT or "\x00" in part or "\n" in part:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": f"part must be one line of at most {PART_LIMIT} characters."}
    if not isinstance(reply_to, str) or (reply_to and not NOTE_ID.match(reply_to)):
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "reply_to must be an agent note's id."}
    argv = ["comment", "--project", str(root), "--json"] + (["--part=" + part.strip()] if part.strip() else []) \
        + (["--reply=" + reply_to] if reply_to else [])
    leg = run_leg("comment", argv + ["--", text.strip()], timeout=WRITE_TIMEOUT_S)
    envelope = leg.envelope
    reply: dict[str, Any] = {"ok": leg.code == EXIT_OK and envelope.get("ok") is True, "exit": leg.code,
                             "seconds": round(leg.seconds, 3), "command": ["cadex", *argv]}
    if envelope.get("comments"):
        reply["comment"] = envelope["comments"][0]
    if "error" in envelope:
        reply["error"] = envelope["error"]
    if reply["ok"]:
        return HTTPStatus.OK, reply
    return (HTTPStatus.BAD_REQUEST if leg.code == EXIT_USAGE else HTTPStatus.CONFLICT), reply


REVISION_ACTIONS = ("accept", "reject", "restore")
NOTE_ID = re.compile(r"^n-[0-9a-f]{12}$")
REVISION_SELECTOR = re.compile(r"^[0-9a-fA-F]{1,64}$|^[0-9]{1,6}$")


def write_revision(root: Path, body: Mapping[str, Any]) -> tuple[HTTPStatus, dict[str, Any]]:
    """``cadex revision ACTION --project ROOT [--note=TEXT] [SELECTOR]``, as a child (ADR-506).

    Accept, Reject and Restore on the page and the command line are one
    write path (A3). A reject or restore rebuilds, under the project lock
    and without ``--wait``, so a project a turn holds is refused (409).
    """

    from .comments import COMMENT_LIMIT
    from .report import EXIT_OK, EXIT_REJECTED, EXIT_USAGE  # report imports this module

    action, selector, note = body.get("action"), body.get("revision", ""), body.get("note", "")
    if action not in REVISION_ACTIONS:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": f"action must be one of {', '.join(REVISION_ACTIONS)}."}
    if not isinstance(selector, str) or (selector and not REVISION_SELECTOR.match(selector)):
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "revision must be an ordinal or a revision prefix."}
    if action == "restore" and not selector:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "restore needs the revision to put back."}
    if not isinstance(note, str) or len(note) > COMMENT_LIMIT or "\x00" in note:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": f"note must be at most {COMMENT_LIMIT} characters of text."}
    argv = ["revision", "--project", str(root), "--json"] + (["--note=" + note.strip()] if note.strip() else [])
    argv += [action] + ([selector] if selector else [])
    leg = run_leg("revision", argv, timeout=WRITE_TIMEOUT_S)
    envelope = leg.envelope
    reply: dict[str, Any] = {"ok": leg.code == EXIT_OK and envelope.get("ok") is True, "exit": leg.code,
                             "seconds": round(leg.seconds, 3), "command": ["cadex", *argv]}
    for key in ("accepted_revision", "digest", "revisions", "error"):
        if key in envelope:
            reply[key] = envelope[key]
    if reply["ok"]:
        return HTTPStatus.OK, reply
    if leg.code == EXIT_USAGE:
        return HTTPStatus.BAD_REQUEST, reply
    return (HTTPStatus.UNPROCESSABLE_ENTITY if leg.code == EXIT_REJECTED else HTTPStatus.CONFLICT), reply


#: Where the dashboard's Export button has ``cadex export`` write, one
#: directory per accepted revision (ADR-509). Under ``/review/``, which the
#: project's own ignore rules keep out of its commits: a rebuild re-makes it.
EXPORT_DIR = "review/export"
EXPORT_FORMATS = ("step", "stl", "brep")
#: What the export directory may serve: the converted geometry and the
#: staged non-geometry outputs ``cadex export`` copies beside it.
EXPORT_SUFFIXES = (".step", ".stl", ".brep", ".xml", ".json", ".ply")
REVISION_HASH = re.compile(r"^[0-9a-f]{64}$")


def write_export(root: Path, body: Mapping[str, Any]) -> tuple[HTTPStatus, dict[str, Any]]:
    """``cadex export --project ROOT --out ROOT/review/export/<revision> --format F``, as a child (ADR-509).

    The Export button and the command line are one write path (A3): the
    CLI rebuilds the accepted script under the project lock, without
    ``--wait``, and converts each staged BREP. The directory is named by
    the revision accepted when the button was pressed; if a write moved
    the accepted revision before the child took the lock, what it wrote is
    removed and the reply says to export again, so a directory never holds
    another revision's files.
    """

    from .report import EXIT_OK, EXIT_REJECTED, EXIT_USAGE  # report imports this module

    formats = body.get("formats", ["step", "stl"])
    if not isinstance(formats, list) or not formats or any(f not in EXPORT_FORMATS for f in formats) \
            or len(set(formats)) != len(formats):
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": f"formats must be a list drawn from {', '.join(EXPORT_FORMATS)}."}
    accepted = read_accepted_identity(root)
    revision = accepted.get("revision") if accepted.get("available") else None
    if not isinstance(revision, str) or not REVISION_HASH.match(revision):
        return HTTPStatus.CONFLICT, {"ok": False, "error": "nothing to export: the project has no accepted revision."}
    out = root / EXPORT_DIR / revision
    argv = ["export", "--project", str(root), "--out", str(out), "--format", ",".join(formats), "--json"]
    leg = run_leg("export", argv, timeout=WRITE_TIMEOUT_S)
    envelope = leg.envelope
    reply: dict[str, Any] = {"ok": leg.code == EXIT_OK and envelope.get("ok") is True, "exit": leg.code,
                             "seconds": round(leg.seconds, 3), "command": ["cadex", *argv], "revision": revision}
    for key in ("accepted_revision", "digest", "error"):
        if key in envelope:
            reply[key] = envelope[key]
    if reply["ok"] and envelope.get("accepted_revision") != revision:
        shutil.rmtree(out, ignore_errors=True)
        reply.update(ok=False, error="the accepted revision changed while exporting; export again.")
        return HTTPStatus.CONFLICT, reply
    if reply["ok"]:
        reply["exports"] = export_listing(root)
        return HTTPStatus.OK, reply
    if leg.code == EXIT_USAGE:
        return HTTPStatus.BAD_REQUEST, reply
    return (HTTPStatus.UNPROCESSABLE_ENTITY if leg.code == EXIT_REJECTED else HTTPStatus.CONFLICT), reply


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
                "reason": "no section cut yet: Cut runs cadex section for this revision"}
    return {"available": True, "revision": revision, "cuts": cuts}


def write_section_cut(root: Path, body: Mapping[str, Any]) -> tuple[HTTPStatus, dict[str, Any]]:
    """``cadex section --project ROOT --plane P [--offset-mm=N] --json``, as a child (orun2 D2.5).

    The Cut button and the command line are one path (A3): the CLI acquires
    the accepted tessellation from the engine and writes the SVG and summary
    under ``review/section/<revision>/``. With no ``offset_mm`` the offset is
    derived the way the walk derives it (ADR-273). The reply names the cut
    the child wrote, read back from the listing.
    """

    from .report import EXIT_OK, EXIT_REJECTED, EXIT_USAGE  # report imports this module

    plane, offset = body.get("plane"), body.get("offset_mm")
    if plane not in SECTION_PLANES:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": f"plane must be one of {', '.join(SECTION_PLANES)}."}
    if offset is not None and (isinstance(offset, bool) or not isinstance(offset, (int, float))
                               or not math.isfinite(offset) or abs(offset) > 1e6):
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "offset_mm must be a finite number of mm, or absent."}
    accepted = read_accepted_identity(root)
    revision = accepted.get("revision") if accepted.get("available") else None
    if not isinstance(revision, str) or not REVISION_HASH.match(revision):
        return HTTPStatus.CONFLICT, {"ok": False, "error": "nothing to cut: the project has no accepted revision."}
    argv = ["section", "--project", str(root), "--plane", plane, "--json"]
    if offset is not None:
        argv[5:5] = [f"--offset-mm={float(offset)!r}"]
    leg = run_leg("section", argv, timeout=WRITE_TIMEOUT_S)
    envelope = leg.envelope
    reply: dict[str, Any] = {"ok": leg.code == EXIT_OK and envelope.get("ok") is True, "exit": leg.code,
                             "seconds": round(leg.seconds, 3), "command": ["cadex", *argv], "revision": revision}
    for key in ("accepted_revision", "digest", "error", "notes"):
        if key in envelope:
            reply[key] = envelope[key]
    if reply["ok"]:
        listing = section_listing(root)
        reply["sections"] = listing
        cuts = [cut for cut in listing["cuts"] if cut["plane"] == plane
                and (offset is None or cut["offset_mm"] == float(offset))]
        if envelope.get("accepted_revision") != revision or not cuts:
            reply.update(ok=False, error="the accepted revision changed while cutting; cut again.")
            return HTTPStatus.CONFLICT, reply
        reply["cut"] = cuts[0]
        return HTTPStatus.OK, reply
    if leg.code == EXIT_USAGE:
        return HTTPStatus.BAD_REQUEST, reply
    return (HTTPStatus.UNPROCESSABLE_ENTITY if leg.code == EXIT_REJECTED else HTTPStatus.CONFLICT), reply


def revision_trail(root: Path) -> list[dict[str, Any]]:
    """The stored trail for the page, newest first, without sources or values."""

    keep = ("ordinal", "revision", "saved_at", "outputs")
    return [{key: entry.get(key) for key in keep} for entry in reversed(read_revision_history(root))]


#: How many comments ``/api/project`` carries, newest kept.
COMMENTS_SHOWN = 100
#: How many agent notes ``/api/project`` carries, newest kept (ADR-512).
NOTES_SHOWN = 50
#: What a note's flagged artifact may be for the page to link it.
NOTE_ARTIFACT_SUFFIXES = frozenset({".png", ".svg", ".mp4", ".webm", ".json", ".md", ".txt"})


#: How long one dashboard prompt turn may run before it is stopped, in seconds.
TURN_TIMEOUT_S = 3600.0
#: Bound on a prompt, in characters; a design brief, not a document.
PROMPT_LIMIT = 16_000
#: Bound on the transcript kept for one turn, in characters; past it the
#: tail is dropped and the transcript says so.
TRANSCRIPT_LIMIT = 4 * 1024 * 1024


class PromptTurn:
    """One ``cadex -p PROMPT --project ROOT`` child and its live transcript.

    The transcript is the child's stderr — the tool-call progress lines and
    the model's prose, exactly what a terminal shows — held in memory for
    the page to read from any offset while the turn runs. It is never
    written into the project: what the turn leaves there (the revision, the
    ``PROGRESS.md`` row, the project commit, the agent's decisions and
    notes) is the CLI's, as for a turn typed at a terminal (A3).
    """

    def __init__(self, root: Path, prompt: str, resume: bool,
                 images: tuple[ImageAttachment, ...] = ()) -> None:
        self.id = secrets.token_hex(6)
        self.root = root
        self.prompt = prompt
        self.resume = resume
        self.images = [image.summary() for image in images]
        self.started = _now()
        self.state = "running"
        self.reply: dict[str, Any] | None = None
        self._text: list[str] = []
        self._length = 0
        self._truncated = False
        self._lock = threading.Lock()
        self.argv = ["--project", str(root), "--prompt=" + prompt] + (["--resume"] if resume else [])
        # An attached image reaches the child as a file only it reads, in a
        # scratch directory outside the project that goes when the turn
        # ends; what the turn keeps of it is the CLI's (ADR-507).
        self._scratch: Path | None = None
        if images:
            self._scratch = Path(tempfile.mkdtemp(prefix="cadex-turn-images-"))
            for index, image in enumerate(images):
                path = self._scratch / str(index) / image.name
                path.parent.mkdir()
                path.write_bytes(image.data)
                self.argv.append("--image=" + str(path))

    def _append(self, text: str) -> None:
        with self._lock:
            if self._truncated:
                return
            if self._length + len(text) > TRANSCRIPT_LIMIT:
                text = "\n[transcript truncated at %d characters]\n" % TRANSCRIPT_LIMIT
                self._truncated = True
            self._text.append(text)
            self._length += len(text)

    def start(self) -> None:
        threading.Thread(target=self._run, name="cadex-turn-" + self.id, daemon=True).start()

    def _run(self) -> None:
        from .report import EXIT_OK  # report imports this module

        try:
            leg = run_leg("prompt", self.argv + ["--json"], timeout=TURN_TIMEOUT_S, on_stderr=self._append)
            envelope = leg.envelope
            reply = {"ok": leg.code == EXIT_OK and envelope.get("ok") is True, "exit": leg.code,
                     "seconds": round(leg.seconds, 3)}
            for key in ("accepted_revision", "digest", "params", "error", "notes", "session_id", "attachments",
                        "usage"):
                if key in envelope:
                    reply[key] = envelope[key]
        except Exception as exc:  # noqa: BLE001 - the page must hear how it ended
            reply = {"ok": False, "exit": None, "error": f"the turn could not run: {exc}"}
        finally:
            if self._scratch is not None:
                shutil.rmtree(self._scratch, ignore_errors=True)
        with self._lock:
            self.reply = reply
            self.state = "done" if reply["ok"] else "failed"

    def snapshot(self, since: int = 0) -> dict[str, Any]:
        with self._lock:
            text = "".join(self._text)
            return {"id": self.id, "state": self.state, "prompt": self.prompt, "resume": self.resume,
                    "images": list(self.images), "started": self.started, "command": ["cadex", *self.argv],
                    "text": text[max(0, min(since, len(text))):], "next": len(text), "reply": self.reply}


def _turn_images(value: Any) -> tuple[ImageAttachment, ...]:
    """A turn body's ``images``, ``[{"name", "data" (base64)}]``, checked as the CLI checks a file."""

    if not isinstance(value, list) or len(value) > IMAGES_PER_TURN:
        raise ImageRefused(f"images must be a list of at most {IMAGES_PER_TURN}.")
    images = []
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) \
                or not isinstance(item.get("data"), str):
            raise ImageRefused('each image is {"name": text, "data": base64 text}.')
        try:
            data = base64.b64decode(item["data"], validate=True)
        except (binascii.Error, ValueError):
            raise ImageRefused(f"{item['name']!r} is not base64.") from None
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(item["name"]).name).strip("._") or "image"
        images.append(image_attachment(data, name[:80]))
    return tuple(images)


class Turns:
    """At most one dashboard turn per project, and the last one each ran."""

    def __init__(self) -> None:
        self._turns: dict[Path, PromptTurn] = {}
        self._lock = threading.Lock()

    def current(self, root: Path) -> PromptTurn | None:
        with self._lock:
            return self._turns.get(root.resolve())

    def start(self, root: Path, body: Mapping[str, Any]) -> tuple[HTTPStatus, dict[str, Any]]:
        """Start ``cadex -p`` on ``root``, unless the body is wrong or one runs."""

        prompt, resume = body.get("prompt"), body.get("resume", False)
        if not isinstance(prompt, str) or not prompt.strip():
            return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "prompt must be non-empty text."}
        if len(prompt) > PROMPT_LIMIT or "\x00" in prompt:
            return HTTPStatus.BAD_REQUEST, {"ok": False, "error": f"a prompt is at most {PROMPT_LIMIT} characters of text."}
        if not isinstance(resume, bool):
            return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "resume must be true or false."}
        try:
            images = _turn_images(body.get("images", []))
        except ImageRefused as exc:
            return HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)}
        key = root.resolve()
        with self._lock:
            running = self._turns.get(key)
            if running is not None and running.state == "running":
                return HTTPStatus.CONFLICT, {"ok": False, "error": "a turn is already running on this project.",
                                             "turn": {"id": running.id, "state": running.state}}
            turn = self._turns[key] = PromptTurn(key, prompt.strip(), resume, images)
        turn.start()
        return HTTPStatus.ACCEPTED, {"ok": True, "turn": turn.snapshot()}


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
                    extra: Mapping[str, str] | None = None) -> None:
        self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

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
        self.query = parts.query
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

    def _write_refusal(self) -> str | None:
        """Why this POST may not write, or ``None`` when it may.

        The token is the launch's own and reaches only a page this server
        served, which a page of another origin cannot read; the ``Origin``
        check refuses a cross-site form or fetch even before that.
        """

        token = self.headers.get(WRITE_TOKEN_HEADER, "")
        if not token or not hmac.compare_digest(token, self.server.write_token):  # type: ignore[attr-defined]
            return f"a write needs this launch's {WRITE_TOKEN_HEADER} header (from the page the server served)."
        origin = self.headers.get("Origin")
        if origin is not None and urlsplit(origin).netloc != self.headers.get("Host", ""):
            return f"cross-origin write refused: Origin {origin!r} is not this server."
        return None

    def do_POST(self) -> None:  # noqa: N802
        parts = urlsplit(self.path)
        segments = [unquote(segment) for segment in parts.path.split("/") if segment]
        try:
            refusal = self._write_refusal()
            if refusal is not None:
                self._send_json({"ok": False, "error": refusal}, HTTPStatus.FORBIDDEN)
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = -1
            limit = TURN_BODY_LIMIT if segments[-2:] == ["api", "turn"] else WRITE_BODY_LIMIT
            if not 0 < length <= limit:
                self._send_json({"ok": False, "error": "a write needs a JSON body of at most "
                                 f"{limit} bytes."}, HTTPStatus.BAD_REQUEST)
                return
            try:
                body = json.loads(self.rfile.read(length))
            except ValueError:
                self._send_json({"ok": False, "error": "the body is not JSON."}, HTTPStatus.BAD_REQUEST)
                return
            projects = getattr(self.server, "projects", None)
            project: ReviewProject | None = self.project if projects is None else None
            if projects is not None and segments[:1] == ["p"] and len(segments) > 1:
                project, segments = projects.project(segments[1]), segments[2:]
            if project is None or segments not in (["api", "params"], ["api", "turn"], ["api", "comment"],
                                                    ["api", "revision"], ["api", "export"], ["api", "section"]) \
                    or not isinstance(body, dict):
                self._not_found(parts.path)
                return
            if segments == ["api", "turn"]:
                status, reply = self.server.turns.start(project.root, body)  # type: ignore[attr-defined]
            elif segments == ["api", "comment"]:
                status, reply = write_comment(project.root, body)
            elif segments == ["api", "revision"]:
                status, reply = write_revision(project.root, body)
            elif segments == ["api", "export"]:
                status, reply = write_export(project.root, body)
            elif segments == ["api", "section"]:
                status, reply = write_section_cut(project.root, body)
            else:
                status, reply = write_params(project.root, body.get("values"))
            self._send_json(reply, status)
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
        if segments == ["api", "turns"]:
            self._send_json(projects.turns())
            return
        runs: OuroborosRuns = self.server.runs  # type: ignore[attr-defined]
        if segments == ["api", "runs"]:
            self._send_json(runs.listing())
            return
        if head == "r" and rest:
            if len(rest) == 1 and not path.endswith("/"):
                self._send_bytes(b"", "text/plain; charset=utf-8", HTTPStatus.MOVED_PERMANENTLY,
                                 {"Location": "/r/" + quote(rest[0], safe="") + "/"})
                return
            page = rest[1:] or ["run.html"]
            if len(page) == 1 and page[0] in RUN_STATIC_FILES and runs.has(rest[0]):
                content_type, file = RUN_STATIC_FILES[page[0]]
                self._send_bytes(file.read_bytes(), content_type)
                return
            if page[0] == "probes" and len(page) > 1:
                probe = runs.probe_file(rest[0], page[1:])
                if probe is not None:
                    self._send_file(probe, download=False, headers=PROBE_HEADERS)
                    return
            if page[0] == "linked" and len(page) > 1:
                linked = runs.linked_file(rest[0], page[1:])
                if linked is not None:
                    self._send_file(linked, download=False, headers=PROBE_HEADERS)
                    return
            run = runs.run(rest[0]) if page == ["api", "run"] else None
            if run is not None:
                self._send_json(run)
                return
            self._not_found("/".join(segments))
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
            body = path.read_bytes()
            if head == "index.html":
                body = body.replace(WRITE_TOKEN_META, WRITE_TOKEN_META.replace(
                    b'content=""', b'content="' + self.server.write_token.encode("ascii") + b'"'))  # type: ignore[attr-defined]
            self._send_bytes(body, content_type)
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
            if rest == ["turn"]:
                turn = self.server.turns.current(project.root)  # type: ignore[attr-defined]
                since = parse_qs(self.query).get("since", ["0"])[0]
                self._send_json(turn.snapshot(int(since) if since.isdigit() else 0) if turn is not None else {"state": "idle"})
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
            self._not_found("/".join(segments))
            return
        path: Path | None = None
        if head == "mesh" and rest[:1] == ["accepted"] and len(rest) == 2 and rest[1].endswith(".stl"):
            body = project.accepted_mesh(rest[1][:-4])
            if body is None:
                self._not_found("/".join(segments))
                return
            self._send_bytes(body, CONTENT_TYPES[".stl"])
            return
        if head == "mesh" and rest[:1] == ["run"] and len(rest) == 3 and rest[2].endswith(".stl"):
            path = project.run_mesh(rest[1], rest[2][:-4])
        elif head == "artifact" and rest[:1] == ["run"] and len(rest) == 3:
            path = project.run_artifact(rest[1], rest[2])
        elif head == "artifact" and rest[:1] == ["project"] and len(rest) == 3:
            path = project.project_artifact(rest[1], rest[2])
        elif head == "note" and len(rest) == 1 and NOTE_ID.match(rest[0]):
            path = project.note_artifact(rest[0])
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
        self.turns = Turns()
        self.log = log
        self.write_token = secrets.token_urlsafe(32)
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

    def turns(self) -> dict[str, Any]:
        """Every project's CLI agent turns, newest first (ADR-519)."""

        # A row's time has one-second resolution: within a project, a tie
        # falls to the row written later.
        found = [(turn["when"], index, {**turn, "project": name, "url": "/p/" + quote(name, safe="") + "/"})
                 for name in self._names() for index, turn in enumerate(agent_turns(self.root / name))]
        found.sort(key=lambda item: item[:2], reverse=True)
        return {"schema": TURNS_SCHEMA, "root": self.root.name, "count": len(found),
                "turns": [turn for _when, _index, turn in found[:TURNS_SHOWN]], "served_at": _now()}


class OuroborosRuns:
    """The Ouroboros runs under one directory, read-only (ADR-513).

    A run is a subdirectory holding ``iterations.jsonl`` or ``status.json``.
    Only four files of it are read -- ``run.yml``'s top-level scalars,
    ``status.json``, ``iterations.jsonl`` and ``critic.jsonl`` -- so the
    transcripts, logs and patches beside them never reach a page. Every read
    is fresh, so a live run's next iteration appears on the next poll; a
    line that is not a JSON object is counted, not fatal.

    A run's charter is the one more read: when the directory is a checkout's
    ``.ouroboros/runs``, ``run.yml``'s ``goal`` file is read from the run's
    branch (``git show``, the checkout's working tree when that branch is the
    one checked out), so a finished run shows the charter it ran to and not
    the one that replaced it, and its ``## Done criteria`` checkboxes are
    listed.

    A run's probe material is ``docs/probes/<run>/`` in the checkout's working
    tree (ADR-515): listed with the run, and each file served read-only under
    ``/r/<run>/probes/``. Only :data:`PROBE_KINDS` suffixes, only
    :data:`PROBE_SEGMENT` names, and no symlink anywhere on the path, so
    nothing outside that directory is reachable through it.

    A run's records are the checkout's record nodes whose ``## Repo`` names
    the run's branch (ADR-518), each placed in the iteration it landed in,
    with the ``docs/`` files its text names served under ``/r/<run>/linked/``
    by the same rules.
    """

    def __init__(self, root: Path | str | None) -> None:
        self.root = Path(root).expanduser().resolve() if root is not None else None
        self.checkout = (self.root.parent.parent if self.root is not None
                         and self.root.parent.name == ".ouroboros" else None)

    def _names(self) -> list[str]:
        if self.root is None or not self.root.is_dir():
            return []
        return sorted(child.name for child in self.root.iterdir()
                      if child.is_dir() and OUROBOROS_RUN_NAME.match(child.name)
                      and ((child / "iterations.jsonl").is_file() or (child / "status.json").is_file()))

    def has(self, name: str) -> bool:
        return name in self._names()

    @staticmethod
    def _rows(path: Path) -> tuple[list[dict[str, Any]], int]:
        rows: list[dict[str, Any]] = []
        skipped = 0
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return rows, 0
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                skipped += 1
                continue
            if isinstance(row, dict) and isinstance(row.get("iteration"), int):
                rows.append(row)
            else:
                skipped += 1
        return rows, skipped

    @staticmethod
    def _config(path: Path) -> dict[str, str]:
        """``run.yml``'s unindented ``key: value`` lines; no YAML parser (A2)."""

        values: dict[str, str] = {}
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return values
        for line in lines:
            key, sep, value = line.partition(":")
            if sep and key and not key[0].isspace() and key.strip() == key and value.strip():
                values[key] = value.strip().strip("'\"")
        return values

    def _git(self, *args: str) -> str | None:
        assert self.checkout is not None
        try:
            done = subprocess.run(["git", "-C", str(self.checkout), *args], capture_output=True,
                                  timeout=10, check=False)
        except (OSError, subprocess.SubprocessError):
            return None
        return done.stdout.decode("utf-8", errors="replace") if done.returncode == 0 else None

    def _goal(self, goal: str, branch: str) -> tuple[str | None, str | None, str | None]:
        """The goal file's text as the run's branch holds it: ``(text, source, reason)``."""

        if self.checkout is None:
            return None, None, "the runs directory is not a checkout's .ouroboros/runs"
        relative = Path(goal)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            return None, None, f"goal {goal!r} is not a path inside the checkout"
        if not OUROBOROS_BRANCH.match(branch) or ".." in branch:
            return None, None, f"branch {branch!r} is not a plain ref name"
        head = self._git("symbolic-ref", "--quiet", "--short", "HEAD")
        if head is not None and head.strip() == branch:
            try:
                return (self.checkout / relative).read_text(encoding="utf-8", errors="replace"), \
                    "working tree", None
            except OSError:
                return None, None, f"{goal} is missing from the working tree"
        for ref, source in ((f"refs/heads/{branch}", branch), (f"refs/remotes/origin/{branch}", f"origin/{branch}")):
            text = self._git("show", f"{ref}:{relative.as_posix()}")
            if text is not None:
                return text, source, None
        return None, None, f"neither {branch} nor origin/{branch} holds {goal}"

    @staticmethod
    def criteria(text: str) -> list[dict[str, Any]]:
        """The checkboxes under ``## Done criteria``: each one's id, title,
        whether it is ticked, and its markdown as written."""

        lines = text.splitlines()
        start = next((i for i, line in enumerate(lines)
                      if re.match(r"^##\s+done criteria\s*$", line, re.IGNORECASE)), None)
        if start is None:
            return []
        items: list[dict[str, Any]] = []
        body: list[str] = []
        for line in lines[start + 1:]:
            if line.startswith("## "):
                break
            match = CHARTER_ITEM.match(line)
            if match:
                body = [match.group(2)]
                items.append({"checked": match.group(1) != " ", "lines": body})
            elif items and (not line.strip() or line[:1].isspace()):
                body.append(line[2:] if line.startswith("  ") else line.strip())
            elif items:
                body = []  # prose between the checkboxes belongs to none of them
        out: list[dict[str, Any]] = []
        for item in items:
            markdown = "\n".join(item["lines"]).strip()
            flat = " ".join(markdown.split())
            bold = re.match(r"^\*\*(.+?)\*\*", flat)
            title = bold.group(1).strip() if bold else flat.split(". ")[0]
            ident = re.match(r"^([A-Z]+[0-9]+[a-z]?)\.\s+", title)
            out.append({"id": ident.group(1) if ident else None,
                        "title": title[ident.end():] if ident else title,
                        "checked": item["checked"], "markdown": markdown})
        return out

    def _charter(self, config: Mapping[str, str], branch: str) -> dict[str, Any]:
        goal = config.get("goal") or ".ouroboros/goal.md"
        text, source, reason = self._goal(goal, branch)
        criteria = self.criteria(text) if text is not None else []
        if text is not None and not criteria:
            reason = f"{goal} has no checkboxes under '## Done criteria'"
        return {"available": text is not None, "goal": goal, "source": source, "reason": reason,
                "checked": sum(1 for item in criteria if item["checked"]), "total": len(criteria),
                "criteria": criteria}

    def _probe_base(self, name: str) -> Path | None:
        """``docs/probes/<run>/``, when it is a real directory of the checkout."""

        if self.checkout is None or not self.has(name):
            return None
        base = self.checkout / "docs" / "probes" / name
        try:
            resolved = base.resolve(strict=True)
        except OSError:
            return None
        return base if resolved == base and resolved.is_dir() else None

    def probe_file(self, name: str, segments: list[str]) -> Path | None:
        """One file under the run's probe directory, or ``None`` for anything
        that is not plainly one: a bad name, a suffix off the list, a symlink."""

        base = self._probe_base(name)
        if base is None or not segments or not all(PROBE_SEGMENT.match(part) and ".." not in part
                                                   for part in segments):
            return None
        path = base.joinpath(*segments)
        if path.suffix.lower() not in PROBE_KINDS:
            return None
        try:
            resolved = path.resolve(strict=True)
        except OSError:
            return None
        return path if resolved == path and path.is_file() else None

    def probes(self, name: str) -> dict[str, Any]:
        """What :meth:`probe_file` would serve for this run, by path."""

        base = self._probe_base(name)
        root = f"docs/probes/{name}"
        if base is None:
            reason = ("the runs directory is not a checkout's .ouroboros/runs" if self.checkout is None
                      else f"{root} is not a directory of the checkout")
            return {"available": False, "root": root, "reason": reason, "readme": None,
                    "files": [], "truncated": 0}
        files: list[dict[str, Any]] = []
        truncated = 0
        for directory, dirs, names in os.walk(base):
            here = Path(directory)
            dirs[:] = sorted(d for d in dirs if PROBE_SEGMENT.match(d) and d != "__pycache__"
                             and not (here / d).is_symlink())
            for file in sorted(names):
                path = here / file
                kind = PROBE_KINDS.get(path.suffix.lower())
                if kind is None or not PROBE_SEGMENT.match(file) or path.is_symlink() or not path.is_file():
                    continue
                if len(files) >= PROBE_LISTING_LIMIT:
                    truncated += 1
                    continue
                files.append({"path": path.relative_to(base).as_posix(), "kind": kind,
                              "bytes": path.stat().st_size})
        files.sort(key=lambda entry: (entry["path"].count("/"), entry["path"]))
        readme = next((entry["path"] for entry in files if entry["path"].lower() == "readme.md"), None)
        return {"available": True, "root": root, "reason": None, "readme": readme, "files": files,
                "truncated": truncated}

    def _record_nodes(self) -> list[dict[str, Any]]:
        """Every record node of the checkout: slug, title, created, branch and
        the ``docs/`` paths its text names, cached until the directory changes."""

        assert self.checkout is not None
        directory = self.checkout / RECORD_DIR
        try:
            stamp = directory.stat().st_mtime_ns
        except OSError:
            return []
        cached = getattr(self, "_record_cache", None)
        if cached is not None and cached[0] == stamp:
            return cached[1]
        nodes: list[dict[str, Any]] = []
        for path in sorted(directory.glob("*.md")):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            head, sep, body = text[4:].partition("\n---\n") if text.startswith("---\n") else ("", "", text)
            if not sep:
                continue
            fields: dict[str, str] = {}
            for line in head.splitlines():
                key, colon, value = line.partition(":")
                if colon and key in ("slug", "title", "created_at"):
                    value = value.strip()
                    if len(value) > 1 and value[0] == value[-1] == "'":
                        value = value[1:-1].replace("''", "'")
                    elif len(value) > 1 and value[0] == value[-1] == '"':
                        value = value[1:-1]
                    fields[key] = value
            branch = re.search(r"^- branch: *(\S+) *$", body, re.MULTILINE)
            if not fields.get("slug") or branch is None:
                continue
            mentions = list(dict.fromkeys(match.group(0).rstrip(".") for match in RECORD_PATH_MENTION.finditer(body)))
            nodes.append({"slug": fields["slug"], "title": fields.get("title", ""),
                          "created_at": fields.get("created_at"), "branch": branch.group(1),
                          "mentions": [m for m in mentions if m.rstrip("/") != "docs"]})
        self._record_cache = (stamp, nodes)
        return nodes

    def _docs_path(self, relative: str) -> Path | None:
        """A plain ``docs/...`` path of the checkout, file or directory, with
        no symlink on it and no dot-segment, or ``None``."""

        assert self.checkout is not None
        parts = relative.rstrip("/").split("/")
        if parts[0] != "docs" or len(parts) < 2 or not all(PROBE_SEGMENT.match(part) and ".." not in part
                                                           for part in parts[1:]):
            return None
        path = self.checkout.joinpath(*parts)
        try:
            resolved = path.resolve(strict=True)
        except OSError:
            return None
        return path if resolved == path else None

    @staticmethod
    def _artifact(path: Path, relative: str) -> dict[str, Any] | None:
        kind = PROBE_KINDS.get(path.suffix.lower())
        if kind is None or not path.is_file():
            return None
        return {"path": relative, "kind": kind, "bytes": path.stat().st_size}

    def _linked(self, mention: str) -> list[dict[str, Any]]:
        """The servable files one mention names: the file, or a directory's own files."""

        path = self._docs_path(mention)
        if path is None:
            return []
        relative = mention.rstrip("/")
        if not path.is_dir():
            artifact = self._artifact(path, relative)
            return [artifact] if artifact is not None else []
        out = []
        for child in sorted(path.iterdir()):
            if PROBE_SEGMENT.match(child.name) and not child.is_symlink():
                artifact = self._artifact(child, f"{relative}/{child.name}")
                if artifact is not None:
                    out.append(artifact)
        return out

    @staticmethod
    def _when(stamp: Any) -> _datetime.datetime | None:
        try:
            when = _datetime.datetime.fromisoformat(str(stamp))
        except ValueError:
            return None
        return when if when.tzinfo is not None else when.replace(tzinfo=_datetime.timezone.utc)

    def records(self, name: str, branch: str, iterations: list[dict[str, Any]]) -> dict[str, Any]:
        """The run's records, newest first, each with the iteration it landed
        in -- the first whose last step is not older than it -- and the
        artifacts under ``docs/`` it names (ADR-518)."""

        root = RECORD_DIR.as_posix()
        if self.checkout is None or not self.has(name):
            return {"available": False, "root": root, "reason": "the runs directory is not a checkout's .ouroboros/runs",
                    "records": []}
        if not (self.checkout / RECORD_DIR).is_dir():
            return {"available": False, "root": root, "reason": f"{root} is not a directory of the checkout",
                    "records": []}
        ends = [(when, item["iteration"]) for item in iterations
                if (when := self._when(item.get("ts"))) is not None]
        out = []
        for node in self._record_nodes():
            if node["branch"] != branch:
                continue
            created = self._when(node["created_at"])
            landed = next((number for when, number in ends if created is not None and when >= created), None)
            artifacts: list[dict[str, Any]] = []
            for mention in node["mentions"]:
                for artifact in self._linked(mention):
                    if artifact["path"] not in {a["path"] for a in artifacts}:
                        artifacts.append(artifact)
            out.append({"slug": node["slug"], "title": node["title"], "created_at": node["created_at"],
                        "iteration": landed, "artifacts": artifacts[:RECORD_ARTIFACT_LIMIT],
                        "more": max(0, len(artifacts) - RECORD_ARTIFACT_LIMIT)})
        out.sort(key=lambda record: str(record["created_at"] or ""), reverse=True)
        return {"available": True, "root": root, "reason": None, "records": out}

    def linked_file(self, name: str, segments: list[str]) -> Path | None:
        """One file a record of this run names, or one inside a probe
        directory (``docs/probes/<dir>/``) a record of it names a path in, so
        a linked README's own images resolve. Anything else is ``None``."""

        if self.checkout is None or not self.has(name) or not segments:
            return None
        relative = "/".join(segments)
        path = self._docs_path(relative)
        if path is None or self._artifact(path, relative) is None:
            return None
        run = self._read(name)
        if run is None:
            return None
        for node in self._record_nodes():
            if node["branch"] != run["branch"]:
                continue
            for mention in node["mentions"]:
                mention = mention.rstrip("/")
                parts = mention.split("/")
                if relative == mention or relative.rpartition("/")[0] == mention:
                    return path
                if parts[:2] == ["docs", "probes"] and len(parts) > 2 and relative.startswith("/".join(parts[:3]) + "/"):
                    return path
        return None

    def _read(self, name: str) -> dict[str, Any] | None:
        if name not in self._names():
            return None
        assert self.root is not None
        directory = self.root / name
        config = self._config(directory / "run.yml")
        try:
            status = json.loads((directory / "status.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            status = {}
        if not isinstance(status, dict):
            status = {}
        steps, skipped_steps = self._rows(directory / "iterations.jsonl")
        verdicts, skipped_verdicts = self._rows(directory / "critic.jsonl")
        by_number: dict[int, dict[str, Any]] = {}

        def entry(number: int) -> dict[str, Any]:
            return by_number.setdefault(number, {"iteration": number, "ts": None, "housekeeping": False,
                                                 "attempts": 0, "actor": None, "commit": None,
                                                 "verdict": None, "critic": None})

        for row in steps:
            item = entry(row["iteration"])
            item["ts"] = row.get("ts") or item["ts"]
            item["housekeeping"] = item["housekeeping"] or bool(row.get("housekeeping"))
            step = row.get("step")
            if step == "actor":
                item["attempts"] += 1
                item["actor"] = {key: row.get(key) for key in ("exit", "timed_out", "error", "turns")}
            elif step == "commit":
                item["commit"] = {key: row.get(key) for key in ("sha", "changed", "recorded", "cost")}
            elif step == "critique":
                item["verdict"] = row.get("verdict")
                item["critique"] = {"reason": row.get("reason") or "; ".join(map(str, row.get("reasons") or [])),
                                    "must_fix": row.get("must_fix") or []}
        for row in verdicts:
            item = entry(row["iteration"])
            item["ts"] = item["ts"] or row.get("ts")
            item["verdict"] = row.get("verdict") or item["verdict"]
            item["critic"] = {key: row.get(key) or "" for key in ("reason", "did", "doing", "fix_first", "reply")}
        iterations = [by_number[number] for number in sorted(by_number)]
        tally: dict[str, int] = {}
        for item in iterations:
            if item["verdict"]:
                tally[item["verdict"]] = tally.get(item["verdict"], 0) + 1
        last = iterations[-1] if iterations else None
        return {
            "name": name,
            "state": status.get("state") or "unknown",
            "branch": status.get("branch") or config.get("branch") or f"ouroboros/{name}",
            "started": config.get("started"),
            "updated": status.get("ts") or (last or {}).get("ts"),
            "cost_usd": status.get("cost_usd"),
            "elapsed_s": status.get("elapsed_s"),
            "iteration_count": len(iterations),
            "verdicts": tally,
            "latest": None if last is None else {
                "iteration": last["iteration"], "verdict": last["verdict"],
                "did": (last["critic"] or {}).get("did", "")},
            "skipped_lines": skipped_steps + skipped_verdicts,
            "iterations": iterations,
        }

    def listing(self) -> dict[str, Any]:
        runs = []
        for name in self._names():
            run = self._read(name)
            if run is not None:
                run.pop("iterations")
                runs.append({**run, "url": "/r/" + quote(name, safe="") + "/"})
        runs.sort(key=lambda run: str(run["updated"] or ""), reverse=True)
        return {"schema": RUNS_SCHEMA, "available": self.root is not None and self.root.is_dir(),
                "root": self.root.name if self.root is not None else None, "runs": runs,
                "served_at": _now()}

    def run(self, name: str) -> dict[str, Any] | None:
        run = self._read(name)
        if run is None:
            return None
        assert self.root is not None
        charter = self._charter(self._config(self.root / name / "run.yml"), run["branch"])
        records = self.records(name, run["branch"], run["iterations"])
        for item in run["iterations"]:
            item["records"] = [record["slug"] for record in records["records"]
                               if record["iteration"] == item["iteration"]]
        return {"schema": RUN_SCHEMA, **run, "charter": charter, "probes": self.probes(name),
                "records": records, "served_at": _now()}


class ProjectsServer(ThreadingHTTPServer):
    """A directory of projects, one address: the index lists them, and each
    project's review page is served under ``/p/<name>/``."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, projects_root: Path | str, host: str, port: int,
                 log: Callable[[str], None] | None = None, runs_root: Path | str | None = None) -> None:
        self.projects = ProjectsDirectory(projects_root)
        self.runs = OuroborosRuns(runs_root)
        self.turns = Turns()
        self.log = log
        self.write_token = secrets.token_urlsafe(32)
        super().__init__((host, port), ReviewHandler)

    url = ReviewServer.url


def serve_projects(projects_root: Path | str, host: str = "127.0.0.1", port: int = 0,
                   log: Callable[[str], None] | None = None,
                   runs_root: Path | str | None = None) -> tuple[ProjectsServer, threading.Thread]:
    """As :func:`serve`, over a directory of projects (``cadex app``), with
    the Ouroboros runs under ``runs_root`` listed beside them (ADR-513)."""

    server = ProjectsServer(projects_root, host, port, log=log, runs_root=runs_root)
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
