# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The one-project review dashboard server (ADR-286).

``cadex review --project DIR`` serves **one** project, read-only, to a
browser on the machine's private network: the accepted identity now, every
run as recorded (ADR-285), the parameters and specs each run was made
under, the retained artifacts, and the model itself — the per-output
meshes a run's rollout leg exported, placed where the rollout trace's
first frame put them, or the accepted attempt's own tessellation for the
project as it stands now. It is a review client: it opens no engine,
rebuilds nothing, accepts nothing, and holds no state of its own, so a
browser that goes away changes nothing about the project.

What it will serve is an allowlist, never a path. Every route names a run
by its directory name, an artifact by its record key, a document by the
relative name its record lists, a mesh by the output it belongs to; each is
looked up in what the reader returned and resolved through the same
containment check the reader applies (:func:`resolve_reference`). A
request for anything else — a path the record does not name, a file that
escapes its base, a run that does not exist — is a 404 that says so, and
no filesystem path in the request is ever joined onto the project root.

The page is plain HTML and JavaScript under ``review_static/`` with no
framework: the viewer is a few hundred lines of WebGL because a review
client that depends on a CDN is not reachable on a private network with
no internet, and because there is nothing to add a dependency *for*.
"""

from __future__ import annotations

from array import array
import datetime as _datetime
import hashlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import mimetypes
from pathlib import Path
import struct
import sys
import threading
from typing import Any, Callable, Mapping
from urllib.parse import unquote, urlsplit

from .review_record import (
    PROJECT_ARTIFACT_KEYS,
    PROJECT_SCRIPT_FILENAME,
    PROJECT_SCRIPT_SCHEMA,
    RUN_ARTIFACT_KEYS,
    RUNS_DIRNAME,
    read_project_review,
    read_run_record,
    resolve_reference,
)

REVIEW_MODEL_SCHEMA = "cadex-review-model-v1"
STATIC_DIR = Path(__file__).resolve().parent / "review_static"
#: The page's files, by the name the browser asks for. A name not in this
#: table is not served, whatever is in the directory.
STATIC_FILES = {
    "index.html": ("text/html; charset=utf-8", STATIC_DIR / "index.html"),
    "review.css": ("text/css; charset=utf-8", STATIC_DIR / "review.css"),
    "review.js": ("text/javascript; charset=utf-8", STATIC_DIR / "review.js"),
    "viewer.js": ("text/javascript; charset=utf-8", STATIC_DIR / "viewer.js"),
}
#: Content types for the retained artifacts; anything else downloads as bytes.
CONTENT_TYPES = {
    ".json": "application/json; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".py": "text/x-python; charset=utf-8",
    ".xml": "application/xml; charset=utf-8",
    ".svg": "image/svg+xml",
    ".stl": "model/stl",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".txt": "text/plain; charset=utf-8",
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


def _identity_model(**fields: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema": REVIEW_MODEL_SCHEMA, "view": None, "run": None, "relation": None,
        "revision": None, "digest": None, "available": False, "reason": None,
        "source": None, "placement_source": None, "components": [],
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
    )
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
    placements, components = _first_frame_placements(_load_json(trace_path))
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
    })
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
    if len(parts) < 2 or parts[0] != "script_artifacts" or parts[1] != revision:
        return None, manifest, "accepted attempt's staging does not belong to the accepted revision"
    return root / item["path"], manifest, None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    brep_digests: dict[str, str] = {}
    outputs_by_name: dict[str, Mapping[str, Any]] = {}
    for output in result["outputs"]:
        if not isinstance(output, Mapping) or not isinstance(output.get("name"), str):
            continue
        outputs_by_name[output["name"]] = output
        artifact = output.get("artifact_path")
        if output.get("artifact_kind") == "brep" and isinstance(artifact, str):
            item = resolve_reference(staging, artifact)
            if item["exists"] and not item["error"]:
                brep_digests[_sha256(staging / artifact)] = output["name"]
    tess_by_output: dict[str, dict[str, Any]] = {}
    for sidecar_path in sorted((staging / "display").glob("*.tess.json")):
        sidecar = _load_json(sidecar_path)
        if not sidecar or sidecar.get("schema") != TESSELLATION_SCHEMA:
            continue
        output = brep_digests.get(str(sidecar.get("source_sha256")))
        artifact = resolve_reference(staging, sidecar.get("artifact_path"))
        if output and artifact["exists"] and not artifact["error"]:
            tess_by_output[output] = {"sidecar": sidecar_path.name, "artifact": artifact["path"],
                                      "triangles": (sidecar.get("counts") or {}).get("triangles")}
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
        if name in placements:
            placement, placement_source = placements[name], "accepted attempt's simulation trace, first frame"
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
    model.update({
        "available": True,
        "source": "the accepted attempt's tessellation (display/*.tess), linked to each output by sha256",
        "placement_source": ("accepted attempt's simulation trace, first frame" if placements
                             else "declared component placements"),
        "components": entries,
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


def training_telemetry(root: Path, record: Mapping[str, Any]) -> dict[str, Any]:
    """Observe the run-local trainer snapshot; never infer process success."""
    result: dict[str, Any] = {"state": "missing", "reason": "training telemetry missing",
                              "checkpoints": [], "curve": [], "loss_curve": [],
                              "episode_steps_curve": []}
    run_ref = resolve_reference(root, f"runs/{record['run']}")
    if run_ref["error"] or not run_ref["exists"]:
        result["reason"] = "training run directory refused or missing"
        return result
    run_dir = root / run_ref["path"]
    # Fixed location also works before the running record sees the first snapshot.
    ref = resolve_reference(run_dir, "train/progress.json")
    if ref["error"] or not ref["exists"]:
        result["reason"] = "training telemetry refused or missing"
        return result
    path = run_dir / ref["path"]
    data = _load_json(path, limit=2 * 1024 * 1024)
    if not data or data.get("schema") != "cadex-training-progress-v1":
        result.update(state="invalid", reason="training telemetry unreadable or unsupported")
        return result
    expected = (record.get("task") or {}).get("sha256")
    if expected and data.get("task_sha256") and expected != data["task_sha256"]:
        result.update(state="invalid", reason="training telemetry task identity mismatch")
        return result
    try:
        stamp = float(data.get("updated_at", path.stat().st_mtime))
        age = max(0.0, _datetime.datetime.now(_datetime.timezone.utc).timestamp() - stamp)
        if not math.isfinite(stamp):
            raise ValueError("nonfinite timestamp")
        for key in ("curve", "loss_curve", "episode_steps_curve"):
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
        return {"state": "invalid", "reason": "training telemetry has invalid metrics"}
    reported = data.get("state")
    result.update(state=reported if reported in ("starting", "training", "done", "failed") else "unknown",
                  reported_state=reported, age_s=age, reason=str(data.get("error") or ""))
    if reported in ("starting", "training") and age > 30:
        result.update(state="stale", reason="no telemetry update for over 30 s; process state unknown")
    checkpoints = data.get("checkpoints", [])
    if not isinstance(checkpoints, list):
        result.update(state="invalid", reason="invalid checkpoint list")
        return result
    for item in checkpoints[:512]:
        if not isinstance(item, dict):
            continue
        name = item.get("path")
        ref = resolve_reference(run_dir, "train/" + name) if isinstance(name, str) and Path(name).name == name else {"error": "invalid checkpoint path", "exists": False}
        status = "refused" if ref["error"] else "missing"
        if ref["exists"] and not ref["error"]:
            checkpoint = run_dir / ref["path"]
            try:
                status = ("retained" if checkpoint.is_file() and checkpoint.stat().st_size <= 4 * 1024 * 1024
                          and _sha256(checkpoint) == item.get("sha256") else "digest mismatch")
            except OSError:
                status = "missing"
        result["checkpoints"].append({"path": name, "iteration": item.get("iteration"),
                                      "sha256": item.get("sha256"), "status": status})
    return result


class ReviewProject:
    """What the server knows how to serve for one project, resolved per request.

    Records are read anew across requests: a walk that lands while the page is
    open shows up on its next poll, and a record that is rewritten from
    ``running`` to ``ok`` is read as it stands. The cost is one directory
    walk of ``runs/`` per request, which is what a review client should
    pay to never show a stale run. Only video digests are cached, bounded and
    keyed by file identity, size and nanosecond modification/change times.
    """

    def __init__(self, project_root: Path | str) -> None:
        self.root = Path(project_root).expanduser().resolve()

    def review(self) -> dict[str, Any]:
        review = read_project_review(self.root)
        for record in review["runs"]:
            record["telemetry"] = training_telemetry(self.root, record)
        review["served_at"] = _now()
        return review

    def run(self, name: str) -> dict[str, Any] | None:
        runs_dir = self.root / RUNS_DIRNAME
        if not name or name in (".", "..") or "/" in name or "\\" in name:
            return None
        run_dir = runs_dir / name
        if not runs_dir.is_dir() or not run_dir.is_dir() or run_dir.parent != runs_dir:
            return None
        record = read_run_record(run_dir, self.root)
        accepted = read_project_review(self.root)["accepted"]
        recorded = (record.get("model") or {}).get("accepted_revision")
        if accepted.get("available") and recorded:
            record["relation"] = "current" if recorded == accepted["revision"] else "historical"
        else:
            record["relation"] = "unknown"
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
            return self.root / RUNS_DIRNAME / name / "training-view" / f"{output}.stl"
        artifacts = record["resolved"]["artifacts"]
        anchor = artifacts["trace"]["path"] or artifacts["model_xml"]["path"]
        path = (self.root / RUNS_DIRNAME / name / anchor).parent / f"{output}.stl"
        return path if path.is_file() and not path.is_symlink() else None

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

    def _send_file(self, path: Path, *, download: bool) -> None:
        """A permitted file, whole or as one byte range (video seeking)."""

        content_type = CONTENT_TYPES.get(path.suffix.lower()) or (
            mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        try:
            size = path.stat().st_size
            handle = path.open("rb")
        except OSError:
            self._not_found(path.name)
            return
        extra = {"Accept-Ranges": "bytes"}
        if download:
            extra["Content-Disposition"] = f'attachment; filename="{path.name}"'
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
            while remaining > 0:
                chunk = handle.read(min(1 << 20, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

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
            self._route(segments, download)
        except BrokenPipeError:
            pass

    def _route(self, segments: list[str], download: bool) -> None:
        project = self.project
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
                record = project.run(rest[1])
                if record is None:
                    self._not_found(f"run {rest[1]!r}")
                    return
                self._send_json(record)
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
        elif head == "video" and rest[:1] == ["run"] and len(rest) == 3 and rest[2].isdigit():
            path = project.run_video(rest[1], int(rest[2]))
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
