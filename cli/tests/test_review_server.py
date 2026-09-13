# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The one-project review dashboard (ADR-286).

Two halves. The HTTP half drives the server in-process against projects
laid out by hand — records, meshes, traces, a staged accepted attempt —
and pins what it serves and, more to the point, what it refuses. The
browser half opens the page in a headless Chromium over its DevTools
pipe (``cdp_browser.py``): identities on screen against the records they
came from, a historical run labelled and drawn from its own mesh, real
mouse orbit and zoom on the WebGL canvas, missing data labelled, stale
data labelled. Browser tests **skip** without a Chromium, the way engine
tests skip without an engine; ``CADEX_BROWSER`` names one explicitly.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

from cadex_cli.__main__ import main
from cadex_cli.report import EXIT_OK, EXIT_USAGE
from cadex_cli.review_record import RUN_RECORD_FILENAME, read_run_record, write_run_record
from cadex_cli.review_server import (
    REVIEW_MODEL_SCHEMA,
    ReviewProject,
    accepted_model,
    default_run,
    run_model,
    serve,
    tessellation_to_stl,
)
from cdp_browser import HeadlessBrowser, find_browser
from test_review_record import REVISION_A, REVISION_B, _manifest, _project, _walked_run

TRACE_SCHEMA = "cadex-assembly-simulation-trace-v1"
CLI_DIR = Path(__file__).resolve().parents[1]


# -- fixtures ------------------------------------------------------------------

def _cube_stl(size: float) -> str:
    """An ASCII STL cube of ``size`` mm at the origin: 12 facets."""

    s = size
    quads = [
        ((0, 0, 0), (0, s, 0), (s, s, 0), (s, 0, 0)), ((0, 0, s), (s, 0, s), (s, s, s), (0, s, s)),
        ((0, 0, 0), (s, 0, 0), (s, 0, s), (0, 0, s)), ((0, s, 0), (0, s, s), (s, s, s), (s, s, 0)),
        ((0, 0, 0), (0, 0, s), (0, s, s), (0, s, 0)), ((s, 0, 0), (s, s, 0), (s, s, s), (s, 0, s)),
    ]
    lines = ["solid cube"]
    for a, b, c, d in quads:
        for tri in ((a, b, c), (a, c, d)):
            lines.append("  facet normal 0 0 0\n    outer loop")
            lines.extend(f"      vertex {x} {y} {z}" for x, y, z in tri)
            lines.append("    endloop\n  endfacet")
    lines.append("endsolid cube")
    return "\n".join(lines) + "\n"


def _cube_tessellation(size: float) -> tuple[dict, bytes]:
    """The same cube as a ``cadex-tessellation-v1`` sidecar and buffer."""

    s = size
    vertices = [(0, 0, 0), (s, 0, 0), (s, s, 0), (0, s, 0), (0, 0, s), (s, 0, s), (s, s, s), (0, s, s)]
    triangles = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
                 (2, 3, 7), (2, 7, 6), (0, 4, 7), (0, 7, 3), (1, 2, 6), (1, 6, 5)]
    vbytes = b"".join(struct.pack("<3f", *v) for v in vertices)
    tbytes = b"".join(struct.pack("<3I", *t) for t in triangles)
    sidecar = {
        "schema": "cadex-tessellation-v1", "byte_order": "little", "quality": "standard",
        "counts": {"vertices": 8, "triangles": 12, "faces": 6, "edges": 0, "edge_vertices": 0},
        "layout": {"vertices": {"dtype": "f32", "offset": 0, "bytes": len(vbytes)},
                   "triangles": {"dtype": "u32", "offset": len(vbytes), "bytes": len(tbytes)},
                   "edge_vertices": {"dtype": "f32", "offset": len(vbytes) + len(tbytes), "bytes": 0}},
    }
    return sidecar, vbytes + tbytes


def _trace(placements: dict[str, list[float]]) -> str:
    return json.dumps({
        "schema": TRACE_SCHEMA, "component_outputs": list(placements),
        "frames": [{"frame_index": 0, "frame_kind": "input", "component_placements": {
            name: {"position_mm": position, "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}
            for name, position in placements.items()}}],
    })


def _mesh_run(root: Path, name: str, *, revision: str) -> Path:
    """A walked run that retained its rollout meshes: body←torso, shin←leg."""

    # Two runs at one revision share a render directory; the helper makes it.
    shutil.rmtree(root / "review" / "render" / revision, ignore_errors=True)
    run = _walked_run(root, name, revision=revision)
    rollout = run / "rollout"
    (rollout / "torso.stl").write_text(_cube_stl(20.0))
    (rollout / "leg.stl").write_text(_cube_stl(8.0))
    (rollout / "assembly-simulation-trace.json").write_text(
        _trace({"body": [0.0, 0.0, 0.0], "shin": [0.0, 0.0, -40.0]}))
    (root / "review" / "render" / revision / "summary.json").write_text(json.dumps({
        "revision": revision, "objects": {"body": {"source": "torso"}, "shin": {"source": "leg"}},
    }))
    return run


def _rewrite_record(run: Path, **changes) -> None:
    path = run / RUN_RECORD_FILENAME
    record = json.loads(path.read_text())
    for key, value in changes.items():
        record[key] = value
    path.write_text(json.dumps(record, indent=2))


def _review_project(tmp_path: Path) -> Path:
    """Accepted at B; ``first`` historical (A), ``second`` current (B),
    ``broken`` historical with its rollout deleted."""

    root = _project(tmp_path)
    _manifest(root, REVISION_B)
    first = _mesh_run(root, "first", revision=REVISION_A)
    _rewrite_record(first, params={"values": {"leg_len": 77.0},
                                   "specs": [{"name": "leg_len", "default": 70.0, "unit": "mm"}],
                                   "specs_source": "inspect scope=script at revision a"})
    _mesh_run(root, "second", revision=REVISION_B)
    broken = _mesh_run(root, "broken", revision=REVISION_A)
    for path in (broken / "rollout").iterdir():
        path.unlink()
    (broken / "rollout").rmdir()
    return root


def _stage_accepted(root: Path, revision: str, *, staging_revision: str | None = None) -> Path:
    """An accepted attempt's staging directory: one solid, one link, a trace."""

    staging = root / "script_artifacts" / (staging_revision or revision) / "attempt-1"
    (staging / "outputs").mkdir(parents=True)
    (staging / "display").mkdir()
    brep = staging / "outputs" / "output-000.brep"
    brep.write_bytes(b"DBRep_DrawableShape torso\n")
    sidecar, data = _cube_tessellation(20.0)
    sidecar["artifact_path"] = "display/display-000.tess.bin"
    sidecar["source_sha256"] = hashlib.sha256(brep.read_bytes()).hexdigest()
    (staging / "display" / "display-000.tess.json").write_text(json.dumps(sidecar))
    (staging / "display" / "display-000.tess.bin").write_bytes(data)
    (staging / "outputs" / "assembly-simulation-trace.json").write_text(_trace({"body": [5.0, 0.0, 10.0]}))
    (staging / "result.json").write_text(json.dumps({
        "ok": True, "schema": "cadex-xscript-project-worker-v1",
        "component_sources": {"src-1": "torso"},
        "outputs": [
            {"name": "torso", "type": "solid", "artifact_kind": "brep", "artifact_path": "outputs/output-000.brep"},
            {"name": "body", "type": "component_link", "definition": {
                "arguments": [{"object_name": "src-1"}],
                "properties": {"placement": {"position": [0.0, 0.0, 0.0], "rotation": [0.0, 0.0, 0.0, 1.0]}}}},
        ],
    }))
    manifest = json.loads((root / "script.json").read_text())
    manifest["accepted_attempt"] = {"attempt_id": "1", "revision": revision,
                                    "staging": staging.relative_to(root).as_posix()}
    (root / "script.json").write_text(json.dumps(manifest))
    return staging


@pytest.fixture
def served(tmp_path):
    root = _review_project(tmp_path)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        yield root, server
    finally:
        server.shutdown()
        server.server_close()


def _get(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read()
    except urllib.error.HTTPError as error:
        return error.code, {k.lower(): v for k, v in error.headers.items()}, error.read()


def _json(url: str):
    status, _headers, body = _get(url)
    assert status == 200, (status, body[:200])
    return json.loads(body)


# -- the API -------------------------------------------------------------------

def test_the_project_api_reads_the_project_live(served) -> None:
    root, server = served
    review = _json(server.url + "api/project")
    assert review["schema"] == "cadex-project-review-v1"
    assert review["accepted"]["revision"] == REVISION_B
    assert {run["run"]: run["relation"] for run in review["runs"]} == {
        "first": "historical", "second": "current", "broken": "historical"}
    assert review["served_at"].endswith("Z")
    # A run landing after the server started is on the next request: nothing is cached.
    _mesh_run(root, "third", revision=REVISION_B)
    assert "third" in {run["run"] for run in _json(server.url + "api/project")["runs"]}
    record = _json(server.url + "api/run/third")
    assert record["relation"] == "current" and record["outcome"] == "completed"


def test_a_run_model_is_its_own_meshes_placed_by_its_own_trace(served) -> None:
    root, server = served
    model = _json(server.url + "api/model/run/first")
    assert model["schema"] == REVIEW_MODEL_SCHEMA and model["available"] is True
    assert model["revision"] == REVISION_A and model["relation"] == "historical"
    by_name = {entry["name"]: entry for entry in model["components"]}
    assert by_name["body"]["output"] == "torso" and by_name["shin"]["output"] == "leg"
    assert by_name["shin"]["placement"]["position_mm"] == [0.0, 0.0, -40.0]
    assert by_name["shin"]["placement_source"] == "rollout trace, first frame"
    assert by_name["body"]["mesh"] == "/mesh/run/first/torso.stl"
    status, headers, body = _get(server.url + "mesh/run/first/torso.stl")
    assert status == 200 and headers["content-type"] == "model/stl"
    assert body == (root / "runs" / "first" / "rollout" / "torso.stl").read_bytes()
    # A mesh with no component, and a component with no mesh, are both said plainly.
    (root / "runs" / "first" / "rollout" / "spare.stl").write_text(_cube_stl(1.0))
    (root / "runs" / "first" / "rollout" / "leg.stl").unlink()
    model = _json(server.url + "api/model/run/first")
    by_name = {entry["name"]: entry for entry in model["components"]}
    assert by_name["spare"]["placement"] is None and "identity" in by_name["spare"]["placement_source"]
    assert by_name["shin"]["mesh"] is None and by_name["shin"]["mesh_status"] == "missing"
    assert _get(server.url + "mesh/run/first/leg.stl")[0] == 404


def test_a_run_without_its_trace_has_no_model_and_says_why(served) -> None:
    _root, server = served
    model = _json(server.url + "api/model/run/broken")
    assert model["available"] is False
    assert model["reason"] == "rollout trace missing: rollout/assembly-simulation-trace.json"
    assert model["components"] == []
    assert _get(server.url + "mesh/run/broken/torso.stl")[0] == 404
    record = _json(server.url + "api/run/broken")
    assert "artifacts.trace: missing" in record["problems"]


def _training_run(root: Path, name: str, *, revision: str, digest: str = "d" * 64,
                  status: str = "running", error: str | None = None, **extra) -> Path:
    """A walk that has trained (or is training) and never rolled out: no
    meshes of its own, identity from the manifest at walk start."""

    run = root / "runs" / name
    (run / "train").mkdir(parents=True, exist_ok=True)
    write_run_record(
        run, project_root=root, status=status, mode="blocking", error=error,
        accepted_revision=revision, digest=digest,
        identity_source="project manifest (script.json) at walk start",
        param_specs=[{"name": "leg_len", "default": 80.0}],
        specs_source="project manifest (script.json) at walk start",
        requested={"iterations": 40, "envs": 1024, "seed": 0},
        legs=[{"leg": "train", "exit": 3, "seconds": 1.0, "argv": ["never"]}] if error else [],
        **extra,
    )
    return run


def test_a_run_before_its_rollout_borrows_the_accepted_model_only_when_it_is_that_model(served) -> None:
    root, server = served
    _stage_accepted(root, REVISION_B)
    _training_run(root, "training", revision=REVISION_B)
    _training_run(root, "old", revision=REVISION_A)
    _training_run(root, "moved", revision=REVISION_B, digest="e" * 64)
    _training_run(root, "blank", revision="")
    model = _json(server.url + "api/model/run/training")
    assert model["available"] and model["relation"] == "current"
    assert model["revision"] == REVISION_B and model["digest"] == "d" * 64
    assert "borrowed" in model["source"] and "retained no rollout" in model["source"]
    assert [c["mesh"] for c in model["components"]] == ["/mesh/accepted/torso.stl"]
    status, _headers, body = _get(server.url + "mesh/accepted/torso.stl")
    assert status == 200 and body.startswith(b"cadex tessellation as binary STL")
    # Nothing is served under the run's own mesh route: it retained none.
    assert _get(server.url + "mesh/run/training/torso.stl")[0] == 404
    for name, wording in (("old", "not the accepted one now"), ("moved", "not the accepted one now"),
                          ("blank", "no revision recorded")):
        model = _json(server.url + f"api/model/run/{name}")
        assert not model["available"] and wording in model["reason"], (name, model["reason"])
        assert model["components"] == []
    # After the design moves on, the same training run is historical and
    # shows nothing rather than today's geometry.
    _manifest(root, REVISION_A)
    model = _json(server.url + "api/model/run/training")
    assert not model["available"] and model["relation"] == "historical"


def test_the_accepted_model_comes_from_the_accepted_attempt_only(served) -> None:
    root, server = served
    model = _json(server.url + "api/model/accepted")
    assert model["available"] is False
    assert model["reason"] == "the manifest names no accepted attempt"
    _stage_accepted(root, REVISION_B)
    model = _json(server.url + "api/model/accepted")
    assert model["available"] is True and model["revision"] == REVISION_B
    (entry,) = model["components"]
    assert entry["name"] == "body" and entry["output"] == "torso"
    assert entry["placement"]["position_mm"] == [5.0, 0.0, 10.0]
    assert entry["placement_source"] == "accepted attempt's simulation trace, first frame"
    status, headers, body = _get(server.url + "mesh/accepted/torso.stl")
    assert status == 200 and headers["content-type"] == "model/stl"
    assert struct.unpack("<I", body[80:84])[0] == 12 and len(body) == 84 + 12 * 50
    assert _get(server.url + "mesh/accepted/leg.stl")[0] == 404
    # A staging directory under another revision is shown as the accepted model
    # only when the manifest's pin names the accepted revision AND the attempt's
    # own result carries the accepted digest (ADR-311): a first accepted script
    # is staged under the engine's pre-run revision, which lacks the specs the
    # worker later collected. Without that proof it is still refused.
    staging = _stage_accepted(root, REVISION_B, staging_revision=REVISION_A)
    model = _json(server.url + "api/model/accepted")
    assert model["available"] is False
    assert "does not belong to the accepted revision" in model["reason"]
    assert _get(server.url + "mesh/accepted/torso.stl")[0] == 404
    result = json.loads((staging / "result.json").read_text())
    result["digest"] = "e" * 64
    (staging / "result.json").write_text(json.dumps(result))
    assert _json(server.url + "api/model/accepted")["available"] is False
    result["digest"] = "d" * 64  # the manifest's accepted_digest
    (staging / "result.json").write_text(json.dumps(result))
    model = _json(server.url + "api/model/accepted")
    assert model["available"] is True and model["revision"] == REVISION_B
    assert [c["name"] for c in model["components"]] == ["body"]
    assert _get(server.url + "mesh/accepted/torso.stl")[0] == 200
    manifest = json.loads((root / "script.json").read_text())
    manifest["accepted_attempt"]["revision"] = REVISION_A  # a pin naming another revision
    (root / "script.json").write_text(json.dumps(manifest))
    model = _json(server.url + "api/model/accepted")
    assert model["available"] is False and "does not belong" in model["reason"]


def test_tessellation_to_stl_writes_every_triangle_with_a_unit_normal() -> None:
    sidecar, data = _cube_tessellation(3.0)
    body = tessellation_to_stl(sidecar, data)
    count = struct.unpack("<I", body[80:84])[0]
    assert count == 12 and len(body) == 84 + count * 50
    for index in range(count):
        values = struct.unpack("<12fH", body[84 + index * 50: 84 + (index + 1) * 50])
        assert abs(sum(v * v for v in values[:3]) - 1.0) < 1e-5
    bad = dict(sidecar)
    bad["layout"] = {**sidecar["layout"], "triangles": {"dtype": "u32", "offset": 0, "bytes": 10 ** 6}}
    with pytest.raises(ValueError):
        tessellation_to_stl(bad, data)


# -- what is served, and what is refused ----------------------------------------

def test_only_recorded_artifacts_and_documents_are_served(served) -> None:
    root, server = served
    ok = server.url + "artifact/run/first/review"
    status, headers, body = _get(ok)
    assert status == 200 and headers["content-type"].startswith("application/json")
    assert body == (root / "runs" / "first" / "review.json").read_bytes()
    status, headers, _body = _get(ok + "?download=1")
    assert status == 200 and headers["content-disposition"] == 'attachment; filename="review.json"'
    status, headers, body = _get(server.url + "artifact/project/first/policy")
    assert status == 200 and body == b"policy"
    assert _get(server.url + "doc/run/first/DECISIONS.md")[2].startswith(b"# biped")
    assert _get(server.url + "doc/current/docs/actuators.md")[0] == 200
    assert _get(server.url + "doc/current/ARCHITECTURE.md")[0] == 200
    refused = [
        "artifact/run/first/../../script.json", "artifact/run/first/script.json",
        "artifact/run/nope/review", "artifact/project/first/nope",
        "doc/run/first/../../../script.py", "doc/run/first/script.py",
        "doc/current/script.py", "doc/current/../script.py", "doc/current/runs/first/run.json",
        "review_server.py", "cadex_cli/review_server.py", "static/../review_server.py",
        "runs/first/run.json", "script.json", "api/nope", "mesh/run/first/../../script.json",
        "mesh/accepted/../../script.json", "video/run/first/0",
    ]
    for path in refused:
        status, _headers, body = _get(server.url + path)
        assert status == 404, (path, status)
        assert json.loads(body)["error"] == "not found", path


def test_a_record_that_points_outside_its_run_is_reported_and_never_served(served) -> None:
    root, server = served
    run = root / "runs" / "first"
    _rewrite_record(run, artifacts={**json.loads((run / RUN_RECORD_FILENAME).read_text())["artifacts"],
                                    "trace": "../../script.json", "review": "/etc/hostname"})
    record = _json(server.url + "api/run/first")
    assert "artifacts.trace: escapes the base directory" in record["problems"]
    assert "artifacts.review: escapes the base directory" in record["problems"]
    assert _get(server.url + "artifact/run/first/trace")[0] == 404
    assert _get(server.url + "artifact/run/first/review")[0] == 404
    model = _json(server.url + "api/model/run/first")
    assert model["available"] is False and "not honoured" in model["reason"]


def _escaped_run(root: Path, tmp_path: Path, name: str = "escaped") -> Path:
    """``runs/<name>`` symlinked to a directory outside the project that
    carries a record, a retained training view and an STL for it."""

    outside = tmp_path / "elsewhere" / name
    (outside / "training-view").mkdir(parents=True)
    stl = outside / "training-view" / "leaked.stl"
    stl.write_text(_cube_stl(9.0))
    (outside / "training-view.json").write_text(json.dumps({
        "schema": "cadex-training-view-v1",
        "model": {"available": True, "placement_source": "fixture", "reason": None,
                  "components": [{"name": "leaked", "output": "leaked",
                                  "mesh": f"/mesh/run/{name}/leaked.stl",
                                  "sha256": hashlib.sha256(stl.read_bytes()).hexdigest(),
                                  "placement": None}]}}))
    (outside / "run.json").write_text(json.dumps({"schema": "cadex-run-record-v1", "run": name}))
    (root / "runs" / name).symlink_to(outside, target_is_directory=True)
    return outside


def test_a_run_directory_outside_the_project_has_no_model_and_serves_no_mesh(served, tmp_path) -> None:
    root, server = served
    _escaped_run(root, tmp_path)
    record = _json(server.url + "api/run/escaped")
    assert record["status"] == "unreadable"
    assert "run: directory escapes the project directory" in record["problems"]
    model = _json(server.url + "api/model/run/escaped")
    assert model["available"] is False
    assert model["reason"] == "run directory escapes the project directory"
    assert model["components"] == []
    assert _get(server.url + "mesh/run/escaped/leaked.stl")[0] == 404
    assert _get(server.url + "artifact/run/escaped/trace")[0] == 404
    assert _get(server.url + "video/run/escaped/0")[0] == 404
    # The project's own runs are untouched by the listing.
    listed = {run["run"]: run["status"] for run in _json(server.url + "api/project")["runs"]}
    assert listed["escaped"] == "unreadable" and listed["second"] == "ok"


def test_recorded_videos_are_served_whole_or_by_range(served) -> None:
    root, server = served
    run = root / "runs" / "first"
    (run / "videos").mkdir()
    (run / "videos" / "final.mp4").write_bytes(bytes(range(64)))
    _rewrite_record(run, videos=[
        {"path": "videos/final.mp4", "policy_sha256": "p" * 64, "seed": 7, "sim_seconds": 4.0},
        {"path": "videos/missing.mp4", "policy_sha256": "p" * 64, "seed": 7, "sim_seconds": 4.0},
    ])
    status, headers, body = _get(server.url + "video/run/first/0")
    assert status == 200 and headers["content-type"] == "video/mp4"
    assert headers["accept-ranges"] == "bytes" and body == bytes(range(64))
    status, headers, body = _get(server.url + "video/run/first/0", {"Range": "bytes=2-5"})
    assert status == 206 and body == bytes([2, 3, 4, 5])
    assert headers["content-range"] == "bytes 2-5/64"
    status, _headers, body = _get(server.url + "video/run/first/0", {"Range": "bytes=-4"})
    assert status == 206 and body == bytes([60, 61, 62, 63])
    assert _get(server.url + "video/run/first/0", {"Range": "bytes=99-"})[0] == 416
    assert _get(server.url + "video/run/first/1")[0] == 404
    assert _get(server.url + "video/run/first/2")[0] == 404
    assert "videos[1]: missing" in _json(server.url + "api/run/first")["problems"]


# -- the command ---------------------------------------------------------------

def test_the_review_command_serves_until_interrupted_and_writes_nothing(tmp_path) -> None:
    root = _review_project(tmp_path)
    progress_before = (root / "PROGRESS.md").read_text()
    env = {**os.environ, "PYTHONPATH": str(CLI_DIR)}
    process = subprocess.Popen(
        [sys.executable, "-m", "cadex_cli", "review", "--project", str(root), "--port", "0", "--json"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    try:
        line = process.stderr.readline()
        assert "review: serving biped at http://127.0.0.1:" in line, line
        url = line.split(" at ")[1].split(" ")[0]
        assert _json(url + "api/project")["accepted"]["revision"] == REVISION_B
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate(timeout=20)
    finally:
        if process.poll() is None:
            process.kill()
    assert process.returncode == EXIT_OK, stderr
    envelope = json.loads(stdout)
    assert envelope["ok"] is True and envelope["notes"] == [f"review: served {url}; stopped"]
    assert (root / "PROGRESS.md").read_text() == progress_before
    assert not (root / ".git").exists()


def test_the_review_command_refuses_a_missing_project_and_a_bad_port(tmp_path, capsys) -> None:
    assert main(["review", "--project", str(tmp_path / "nope")]) == EXIT_USAGE
    assert "project directory not found" in capsys.readouterr().out
    root = _review_project(tmp_path)
    assert main(["review", "--project", str(root), "--port", "70000"]) == EXIT_USAGE
    assert "--port must be" in capsys.readouterr().out


# -- the browser ---------------------------------------------------------------

BROWSER = find_browser()
needs_browser = pytest.mark.skipif(BROWSER is None, reason="no Chromium found (set CADEX_BROWSER)")


@pytest.fixture(scope="module")
def browser():
    if BROWSER is None:
        pytest.skip("no Chromium found (set CADEX_BROWSER)")
    with HeadlessBrowser(BROWSER) as instance:
        yield instance


def _open(browser: HeadlessBrowser, url: str):
    page = browser.page(url)
    page.evaluate("window.cadexReview.ready", await_promise=True)
    return page


MODEL_SETTLED = ("['loaded','missing','error'].includes("
                 "document.getElementById('model-status').dataset.state)")


def _model_state(page) -> str:
    page.wait_for(MODEL_SETTLED)
    return page.attribute("#model-status", "data-state")


@needs_browser
def test_browser_shows_the_accepted_identity_and_every_run_with_its_relation(served, browser) -> None:
    _root, server = served
    page = _open(browser, server.url)
    assert page.text("#project-name") == "biped — review"
    assert REVISION_B[:12] in page.text("#accepted-line")
    page.evaluate("window.cadexReview.select('accepted')", await_promise=True)
    assert page.text("#view-kind") == "ACCEPTED NOW"
    assert page.text("#view-revision") == REVISION_B
    assert page.text("#view-digest") == "d" * 64
    relations = page.evaluate(
        "Array.from(document.querySelectorAll('#views li[data-run]')).map("
        "n => [n.dataset.run, n.dataset.relation, n.dataset.status])")
    assert sorted(relations) == [["broken", "historical", "ok"], ["first", "historical", "ok"],
                                 ["second", "current", "ok"]]
    assert page.text("#params tr[data-param='leg_len'] td:nth-child(2)") == "90"
    assert page.text("#params tr[data-param='leg_len'] td:nth-child(3)") == "80"
    assert page.attribute("#freshness", "data-state") == "live"
    assert "updated" in page.text("#freshness")
    assert page.evaluate("Array.from(document.querySelectorAll('#docs li[data-doc]')).map(n => n.dataset.doc)") == [
        "ARCHITECTURE.md", "DECISIONS.md", "PROGRESS.md", "docs/actuators.md", "docs/inventory.md"]
    assert page.text("#decisions li[data-decision]") == "ADR-001 — Project scaffolded (2026-09-12)"
    assert _model_state(page) == "missing"
    assert "no model to show" in page.text("#model-status")


@needs_browser
def test_browser_selecting_a_historical_run_shows_that_run_not_today(served, browser) -> None:
    _root, server = served
    page = _open(browser, server.url)
    page.click("#views li[data-run='first']")
    assert page.wait_for("document.getElementById('view-revision').textContent === " + json.dumps(REVISION_A))
    assert page.text("#view-kind") == "RUN first"
    assert page.text("#view-relation").startswith("HISTORICAL — recorded at " + REVISION_A[:12])
    assert "accepted now is " + REVISION_B[:12] in page.text("#view-relation")
    assert page.attribute("#view-relation", "data-tone") == "historical"
    assert page.text("#view-status") == "completed"
    assert page.text("#view-identity-source") == "rollout leg envelope"
    # Parameters and specs are the run's own record, not the accepted manifest's.
    assert page.text("#params tr[data-param='leg_len'] td:nth-child(2)") == "77"
    assert page.text("#params tr[data-param='leg_len'] td:nth-child(3)") == "70"
    assert "inspect scope=script at revision a" in page.text("#params-note")
    assert page.text("#training tr[data-key='requested iterations'] td") == "10"
    assert page.text("#training tr[data-key='rollout seed'] td") == "7"
    assert page.attribute("#artifacts tr[data-key='trace'] td:nth-child(3)", "data-status") == "retained"
    assert page.attribute("#artifacts tr[data-key='model_xml'] td:nth-child(3)", "data-status") == "retained"
    assert "none recorded" in page.text("#videos li")
    assert "snapshot taken when this run was recorded" in page.text("#docs-note")
    page.click("#docs li[data-doc='DECISIONS.md'] a")
    assert "ADR-002 — Longer shins" in page.wait_for(
        "document.getElementById('doc-view').textContent.includes('ADR-002') && "
        "document.getElementById('doc-view').textContent")
    assert _model_state(page) == "loaded"
    status = page.text("#model-status")
    assert status.startswith("HISTORICAL model of run first at revision " + REVISION_A[:12])
    assert "2 component(s), 24 triangles" in status
    components = page.evaluate(
        "Array.from(document.querySelectorAll('#model-components li')).map(n => n.textContent)")
    assert any(line.startswith("body ← torso · mesh retained (12 triangles)") for line in components)
    assert any("shin ← leg" in line and "rollout trace, first frame" in line for line in components)
    state = page.evaluate("window.cadexReview.state()")
    assert state["selected"] == "first" and state["revision"] == REVISION_A
    assert state["model"]["revision"] == REVISION_A


@needs_browser
def test_browser_lists_an_escaped_run_as_unreadable_and_draws_nothing_for_it(served, browser, tmp_path) -> None:
    root, server = served
    _escaped_run(root, tmp_path)
    page = _open(browser, server.url)
    assert page.attribute("#views li[data-run='escaped']", "data-status") == "unreadable"
    page.click("#views li[data-run='escaped']")
    assert page.wait_for("document.getElementById('view-kind').textContent === 'RUN escaped'")
    assert _model_state(page) == "missing"
    status = page.text("#model-status")
    assert status.startswith("no model to show: run directory escapes the project directory")
    assert page.evaluate("document.querySelectorAll('#model-components li').length") == 0
    state = page.evaluate("window.cadexReview.state()")
    assert state["selected"] == "escaped" and state["model"]["available"] is False
    # The project's own historical run still draws afterwards.
    page.click("#views li[data-run='first']")
    assert page.wait_for("document.getElementById('view-kind').textContent === 'RUN first'")
    assert _model_state(page) == "loaded"


@needs_browser
def test_browser_orbit_and_zoom_move_the_camera_over_a_drawn_model(served, browser) -> None:
    _root, server = served
    page = _open(browser, server.url)
    page.click("#views li[data-run='second']")
    assert _model_state(page) == "loaded"
    assert page.text("#view-relation").startswith("CURRENT")
    stats = page.evaluate("window.cadexReview.viewer().stats()")
    assert stats["components"] == 2 and stats["triangles"] == 24
    assert stats["bounds"]["min"][2] == -40.0 and stats["bounds"]["max"][2] == 20.0
    drawn_before = page.evaluate("window.cadexReview.viewer().nonBackgroundPixels()")
    assert drawn_before > 1000, "the model is not drawn"
    page.send("Emulation.setDeviceMetricsOverride", {
        "width": 1000, "height": 900, "deviceScaleFactor": 1, "mobile": False,
    })
    # Redrawing resizes the canvas backing store. Its intrinsic size must not
    # widen the grid column on each subsequent layout (and move mouse targets).
    widths = page.evaluate("""Array.from({length: 8}, () => {
        window.cadexReview.viewer().nonBackgroundPixels();
        return document.getElementById('viewer').getBoundingClientRect().width;
    })""")
    assert max(widths) - min(widths) <= 1, widths
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.scroll_into_view("#viewer")
    rect = page.rect("#viewer")
    cx, cy = rect["x"] + rect["width"] / 2, rect["y"] + rect["height"] / 2
    before = page.evaluate("window.cadexReview.viewer().camera()")
    page.drag(cx, cy, cx + 150, cy + 60)
    after_orbit = page.wait_for(
        "(function(){var c=window.cadexReview.viewer().camera();"
        f"return (c.yaw !== {before['yaw']} && c.pitch !== {before['pitch']}) && c}})()")
    assert after_orbit["distance"] == before["distance"]
    page.wheel(cx, cy, -240)
    after_zoom = page.wait_for(
        "(function(){var c=window.cadexReview.viewer().camera();"
        f"return c.distance < {after_orbit['distance']} && c}})()")
    assert after_zoom["yaw"] == after_orbit["yaw"]
    assert page.evaluate("window.cadexReview.viewer().nonBackgroundPixels()") > 1000
    page.click("#model-fit")
    reset = page.wait_for("(function(){var c=window.cadexReview.viewer().camera(); return c.yaw === 0.8 && c})()")
    assert reset["distance"] == before["distance"]
    # A run that lost its rollout draws nothing and says so, with the artifact marked missing.
    page.click("#views li[data-run='broken']")
    page.wait_for("document.getElementById('view-kind').textContent === 'RUN broken'")
    assert _model_state(page) == "missing"
    assert "rollout trace missing" in page.text("#model-status")
    assert page.evaluate("window.cadexReview.viewer().stats().components") == 0
    assert page.attribute("#artifacts tr[data-key='trace'] td:nth-child(3)", "data-status") == "missing"
    assert page.text("#artifacts tr[data-key='receipt'] td:nth-child(3)") == "not recorded"
    assert "artifacts.trace: missing" in page.evaluate(
        "Array.from(document.querySelectorAll('#problems li')).map(n => n.textContent)")


@needs_browser
def test_browser_draws_the_accepted_attempt_and_labels_a_lost_server_stale(tmp_path, browser) -> None:
    root = _review_project(tmp_path)
    _stage_accepted(root, REVISION_B)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        assert _model_state(page) == "loaded"
        page.evaluate("window.cadexReview.select('accepted')", await_promise=True)
        assert page.text("#model-status").startswith("accepted model at revision " + REVISION_B[:12])
        assert "1 component(s), 12 triangles" in page.text("#model-status")
        assert page.evaluate("window.cadexReview.viewer().nonBackgroundPixels()") > 1000
        assert page.attribute("#freshness", "data-state") == "live"
    finally:
        server.shutdown()
        server.server_close()
    page.evaluate("window.cadexReview.refresh()", await_promise=True)
    assert page.attribute("#freshness", "data-state") == "stale"
    assert page.text("#freshness").startswith("stale: server unreachable, last update ")
    assert page.evaluate("window.cadexReview.state().stale") is True
    # What was on screen stays: the last good identity, not a blank page.
    assert page.text("#view-revision") == REVISION_B


@needs_browser
def test_browser_reaches_the_dashboard_over_the_private_network_address(tmp_path, browser) -> None:
    """D1's smoke test: ``CADEX_REVIEW_HOST=<tailscale address>`` binds the
    server there and opens it in the browser by that address, not loopback."""

    host = os.environ.get("CADEX_REVIEW_HOST", "")
    if not host:
        pytest.skip("set CADEX_REVIEW_HOST to the machine's private-network address")
    root = _review_project(tmp_path)
    server, _thread = serve(root, host, 0)
    try:
        assert host in server.url and "127.0.0.1" not in server.url
        started = time.monotonic()
        page = _open(browser, server.url)
        elapsed = time.monotonic() - started
        assert page.text("#project-name") == "biped — review"
        assert page.text("#view-revision") == REVISION_B
        assert page.evaluate("location.host") == server.url[len("http://"):-1]
        print(f"\nreached {server.url} in {elapsed:.2f}s")
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
def test_browser_unaccepted_project_reports_missing_model_and_next_cli_action(tmp_path, browser) -> None:
    """A first design refusal can leave documents but no accepted manifest."""
    root = tmp_path / "fresh-biped"
    root.mkdir()
    progress = "# Progress\n\nNo accepted design turns.\n"
    (root / "PROGRESS.md").write_text(progress)
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        assert page.text("#project-name") == "fresh-biped — review"
        assert "nothing accepted: no script.json" in page.text("#accepted-line")
        assert "0 run(s)" in page.text("#accepted-line")
        assert page.text("#view-revision") == "none"
        assert page.text("#view-digest") == "none"
        assert page.text("#view-status") == ""
        assert "cadex -p" in page.text("#view-note")
        assert _model_state(page) == "missing"
        assert "no model to show" in page.text("#model-status")
        assert "specs unavailable" in page.text("#params-note")
        assert page.evaluate("document.querySelectorAll('#views li[data-run]').length") == 0
        page.click("#docs li[data-doc='PROGRESS.md'] a")
        page.wait_for("document.getElementById('doc-view').textContent.includes('No accepted design turns.')")
    finally:
        server.shutdown()
        server.server_close()
    assert {p.name: p.read_bytes() for p in root.iterdir()} == before


def _telemetry(root, iteration=0, run="first", **changes):
    data = {"schema": "cadex-training-progress-v1", "state": "training",
            "updated_at": time.time(), "task_sha256": "t" * 64,
            "iteration": iteration, "total": 10, "reward_per_step": iteration + 0.5,
            "loss": 3.0 - iteration, "episode_steps": 12 + iteration,
            "curve": [[i, i + 0.5] for i in range(iteration + 1)],
            "loss_curve": [[i, 3.0-i] for i in range(iteration + 1)],
            "episode_steps_curve": [[i, 12+i] for i in range(iteration + 1)],
            "checkpoints": []}
    data.update(changes)
    path = root / "runs" / run / "train/progress.json"
    temporary = path.with_suffix('.partial')
    temporary.write_text(json.dumps(data))
    temporary.replace(path)
    return path


def test_telemetry_refuses_escape_mismatch_and_invalid_histories(served):
    root, server = served
    def read():
        # Histories and verified checkpoints travel with the run's detail (ADR-321).
        return _json(server.url + 'api/run/first')['telemetry']
    path = _telemetry(root, task_sha256='wrong')
    assert read()['state'] == 'invalid'
    _telemetry(root, loss_curve=[[0, float('nan')]])
    assert read()['state'] == 'invalid'
    _telemetry(root, loss_curve=[[0, 1]] * 513)
    assert read()['state'] == 'invalid'
    _telemetry(root, checkpoints=[{'path': '../../../script.json'}, {'path': 'lost.cxpolicy'}])
    assert [c['status'] for c in read()['checkpoints']] == ['refused', 'missing']
    path.unlink()
    path.symlink_to(root / 'script.json')
    assert read()['state'] == 'missing'
    assert 'refused' in read()['reason']


def test_default_run_prefers_active_training_then_the_newest_record_whatever_the_names(tmp_path):
    """The reader's rule for a fresh visit, the one the page applies, with
    run names that say nothing: record time and telemetry decide."""

    root = _project(tmp_path)
    _manifest(root, REVISION_B)
    for name, stamp in (("zebra", "2026-01-01T00:00:00Z"), ("aardvark", "2026-01-03T00:00:00Z"),
                        ("mango", "2026-01-02T00:00:00Z")):
        _rewrite_record(_mesh_run(root, name, revision=REVISION_B), recorded_at=stamp)
    project = ReviewProject(root)
    assert default_run(project.review()) == "aardvark"          # newest by record time, not by name
    _rewrite_record(root / "runs/aardvark", status="failed")
    assert default_run(project.review()) == "aardvark"          # a newer failure is never hidden
    _rewrite_record(root / "runs/zebra", status="running")
    _telemetry(root, run="zebra")
    assert default_run(project.review()) == "zebra"             # active training first
    _telemetry(root, run="zebra", updated_at=time.time() - 60)
    assert default_run(project.review()) == "aardvark"          # stale is not active
    _telemetry(root, run="zebra", state="done")
    assert default_run(project.review()) == "aardvark"
    assert default_run({"runs": []}) == "accepted"


def _checkpoint(root, run, name="iter-2.cxpolicy", payload=b"fixture checkpoint, not a verified policy"):
    """A checkpoint file in ``runs/<run>/train`` and its telemetry entry."""

    path = root / "runs" / run / "train" / name
    path.write_bytes(payload)
    return {"path": name, "iteration": 2, "sha256": hashlib.sha256(payload).hexdigest()}


def _playback_run(root, name, *, source, revision):
    """A playback run of ``source``'s policy: it copies the training snapshot
    beside its own rollout and records the training run it came from, the
    way the fresh biped's checkpoint/final playbacks do. The checkpoint bytes
    stay with the training run."""

    run = _mesh_run(root, name, revision=revision)
    shutil.copyfile(root / "runs" / source / "train/progress.json", run / "train/progress.json")
    _rewrite_record(run, training={"requested": {"source_run": source, "checkpoint": "iter-2.cxpolicy"},
                                   "receipt": {}})
    return run


def test_playback_checkpoints_resolve_through_the_recorded_training_run(served, tmp_path):
    """A playback run shows its training run's checkpoints, through the
    provenance its own record names and only inside this project; every way
    that fails is a distinct, explicit state rather than a bare ``missing``."""

    root, server = served
    item = _checkpoint(root, "first")
    _telemetry(root, 2, state="done", checkpoints=[item])
    _playback_run(root, "first-final", source="first", revision=REVISION_A)

    def telemetry(url=server.url, run="first-final"):
        return _json(url + "api/run/" + run)["telemetry"]

    # The training run itself: its own train/, no provenance needed.
    own = telemetry(run="first")
    assert own["checkpoint_source"]["state"] == "none"
    assert [(c["status"], c["source"]) for c in own["checkpoints"]] == [("retained", "run")]
    # The playback: resolved through runs/first/train, named as such.
    data = telemetry()
    assert data["state"] == "done"
    assert data["checkpoint_source"] == {"state": "resolved", "run": "first", "path": "runs/first/train",
                                         "reason": "checkpoints resolved through recorded training run first"}
    assert [(c["status"], c["source"]) for c in data["checkpoints"]] == [("retained", "first")]
    # A copy of the bytes beside the playback wins, and says it is the run's own.
    shutil.copyfile(root / "runs/first/train/iter-2.cxpolicy", root / "runs/first-final/train/iter-2.cxpolicy")
    assert [(c["status"], c["source"]) for c in telemetry()["checkpoints"]] == [("retained", "run")]
    (root / "runs/first-final/train/iter-2.cxpolicy").unlink()
    # Integrity is checked wherever the bytes were found.
    (root / "runs/first/train/iter-2.cxpolicy").write_bytes(b"changed")
    assert [(c["status"], c["source"]) for c in telemetry()["checkpoints"]] == [("digest mismatch", "first")]
    (root / "runs/first/train/iter-2.cxpolicy").unlink()
    assert [(c["status"], c["source"]) for c in telemetry()["checkpoints"]] == [("missing", None)]
    assert telemetry()["checkpoint_source"]["state"] == "resolved"
    # A provenance that is not a bare run name is refused, never followed.
    playback = root / "runs/first-final"
    for bad in ("../../first", "first/train", "/", "."):
        _rewrite_record(playback, training={"requested": {"source_run": bad}, "receipt": {}})
        data = telemetry()
        assert data["checkpoint_source"]["state"] == "refused", bad
        assert [(c["status"], c["source"]) for c in data["checkpoints"]] == [("missing", None)]
    # A training run that is not in this project is a named, explained absence.
    _rewrite_record(playback, training={"requested": {"source_run": "gone"}, "receipt": {}})
    data = telemetry()
    assert data["checkpoint_source"]["state"] == "missing" and data["checkpoint_source"]["run"] == "gone"
    assert "not in this project" in data["checkpoint_source"]["reason"]
    assert "cadex walk" in data["checkpoint_source"]["reason"]
    assert [(c["status"], c["source"]) for c in data["checkpoints"]] == [("missing", None)]
    # Copy isolation: a copy that left runs/first behind cannot reach the
    # original's checkpoints, by name or by symlink, and the original is unmoved.
    _rewrite_record(playback, training={"requested": {"source_run": "first"}, "receipt": {}})
    _checkpoint(root, "first")
    copy = tmp_path / "copy"
    shutil.copytree(root, copy, ignore=lambda d, names: ["first"] if Path(d) == root / "runs" else [])
    other, _thread = serve(copy, "127.0.0.1", 0)
    try:
        data = telemetry(other.url)
        assert data["checkpoint_source"]["state"] == "missing"
        assert [(c["status"], c["source"]) for c in data["checkpoints"]] == [("missing", None)]
        (copy / "runs/first").symlink_to(root / "runs/first", target_is_directory=True)
        data = telemetry(other.url)
        assert data["checkpoint_source"]["state"] == "refused"
        assert [(c["status"], c["source"]) for c in data["checkpoints"]] == [("missing", None)]
    finally:
        other.shutdown()
        other.server_close()
    assert [(c["status"], c["source"]) for c in telemetry()["checkpoints"]] == [("retained", "first")]


@needs_browser
def test_browser_shows_checkpoint_provenance_for_current_and_historical_playback(served, browser):
    """The page names where a playback's checkpoints come from — its own
    train/, the recorded training run, or nowhere in this project — for the
    current playback and for a historical one, and a historical view keeps
    its own revision while its training run's files go missing."""

    root, server = served
    for source in ("first", "second"):
        _telemetry(root, 2, run=source, state="done", checkpoints=[_checkpoint(root, source)])
    _playback_run(root, "first-final", source="first", revision=REVISION_A)
    _playback_run(root, "second-final", source="second", revision=REVISION_B)
    page = _open(browser, server.url)
    page.click("#views li[data-run='second-final']")
    page.wait_for("document.getElementById('view-kind').textContent === 'RUN second-final'")
    page.wait_for("document.getElementById('checkpoint-source').dataset.state === 'resolved'")
    assert page.text("#view-relation").startswith("CURRENT")
    assert page.attribute("#checkpoint-source", "data-run") == "second"
    assert "recorded training run second" in page.text("#checkpoint-source")
    assert page.attribute("#checkpoints li", "data-status") == "retained"
    assert page.attribute("#checkpoints li", "data-source") == "second"
    assert "from training run second" in page.text("#checkpoints li")
    page.click("#views li[data-run='first-final']")
    page.wait_for("document.getElementById('view-kind').textContent === 'RUN first-final'")
    page.wait_for("document.getElementById('checkpoint-source').dataset.run === 'first'")
    assert page.text("#view-relation").startswith("HISTORICAL")
    assert page.text("#view-revision") == REVISION_A
    assert page.attribute("#checkpoints li", "data-status") == "retained"
    assert page.attribute("#checkpoints li", "data-source") == "first"
    # The training run's own view says its checkpoints are its own.
    page.click("#views li[data-run='first']")
    page.wait_for("document.getElementById('checkpoint-source').dataset.state === 'none'")
    assert page.attribute("#checkpoints li", "data-source") == "run"
    assert "from training run" not in page.text("#checkpoints li")
    # Back on the historical playback: the checkpoint file goes, then the whole training run.
    page.click("#views li[data-run='first-final']")
    page.wait_for("document.getElementById('checkpoint-source').dataset.run === 'first'")
    (root / "runs/first/train/iter-2.cxpolicy").unlink()
    page.wait_for("document.querySelector('#checkpoints li').dataset.status === 'missing'")
    assert "not found in this project" in page.text("#checkpoints li")
    assert page.attribute("#checkpoint-source", "data-state") == "resolved"
    shutil.rmtree(root / "runs/first/train")
    page.wait_for("document.getElementById('checkpoint-source').dataset.state === 'missing'")
    assert "training run first missing" in page.text("#checkpoint-source")
    assert "not in this project" in page.text("#checkpoint-source")
    assert page.text("#view-kind") == "RUN first-final"
    assert page.text("#view-revision") == REVISION_A
    assert page.attribute("#telemetry", "data-state") == "done"


@needs_browser
def test_browser_polls_training_histories_checkpoints_and_stale_states(served, browser):
    root, server = served
    path = root / 'runs/first/train/progress.json'
    path.unlink()
    record = json.loads((path.parent.parent / RUN_RECORD_FILENAME).read_text())
    _rewrite_record(path.parent.parent, artifacts={**record['artifacts'], 'progress': None})
    page = _open(browser, server.url)
    page.click("#views li[data-run='first']")
    page.wait_for("document.getElementById('telemetry').dataset.state === 'missing'")
    path.write_text('{partial')
    page.wait_for("document.getElementById('telemetry').dataset.state === 'invalid'")
    page.evaluate("window.telemetryTestIdentity = {}")
    for iteration in range(3):
        started = time.monotonic()
        _telemetry(root, iteration)
        page.wait_for("document.querySelector('[data-metric=iteration]').textContent === " + json.dumps(f'iteration: {iteration}'))
        assert time.monotonic() - started < 5
        assert page.attribute('#telemetry', 'data-state') == 'training'
        assert page.attribute('[data-history=loss_curve]', 'data-points') == str(iteration + 1)
        assert page.text('[data-metric=loss]') == f'loss: {3-iteration}'
        assert page.text('[data-metric=episode_steps]') == f'episode_steps: {12+iteration}'
        assert page.text('#view-revision') == REVISION_A
        assert page.evaluate('!!window.telemetryTestIdentity')
    checkpoint = path.parent / 'iter-2.cxpolicy'
    checkpoint.write_bytes(b'fixture checkpoint, not a verified policy')
    item = {'path': checkpoint.name, 'iteration': 2, 'sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest()}
    _telemetry(root, 2, checkpoints=[item])
    page.wait_for("document.querySelector('#checkpoints li').dataset.status === 'retained'")
    checkpoint.write_bytes(b'changed')
    page.wait_for("document.querySelector('#checkpoints li').dataset.status === 'digest mismatch'")
    _telemetry(root, 2, updated_at=time.time()-31)
    page.wait_for("document.getElementById('telemetry').dataset.state === 'stale'")
    assert 'process state unknown' in page.text('#telemetry')
    assert page.attribute('#freshness', 'data-state') == 'live'
    _telemetry(root, 2, state='failed', error='controlled fixture failure')
    page.wait_for("document.getElementById('telemetry').dataset.state === 'failed'")
    assert 'controlled fixture failure' in page.text('#telemetry')
    assert 'cadex walk' in page.text('#telemetry')
    assert page.attribute('[data-history=loss_curve]', 'data-points') == '3'
    _telemetry(root, 2, state='done', updated_at=time.time()-3600)
    page.wait_for("document.getElementById('telemetry').dataset.state === 'done'")
    page.click("#views li[data-run='second']")
    page.wait_for("document.getElementById('view-kind').textContent === 'RUN second'")
    assert page.attribute('#telemetry', 'data-state') == 'invalid'
    page.click("#views li[data-run='first']")
    page.wait_for("document.getElementById('telemetry').dataset.state === 'done'")
    assert page.attribute('[data-history=loss_curve]', 'data-points') == '3'


@needs_browser
def test_browser_identifies_a_training_run_s_model_and_keeps_it_through_failure(tmp_path, browser):
    """The fresh biped's first walk on screen: a run that is training shows
    the revision, digest, specs and model it trains on — borrowed from the
    accepted attempt, labelled — and keeps every one of them when the
    trainer and then the walk report failure."""

    root = _project(tmp_path)
    _manifest(root, REVISION_B)
    _stage_accepted(root, REVISION_B)
    run = _training_run(root, "probe", revision=REVISION_B)
    progress = run / "train" / "progress.json"

    def telemetry(iteration, **changes):
        data = {"schema": "cadex-training-progress-v1", "state": "training",
                "updated_at": time.time(), "task_sha256": "t" * 64,
                "iteration": iteration, "total": 40, "reward_per_step": 0.1 * iteration,
                "loss": 2.0, "episode_steps": 30,
                "curve": [[i, 0.1 * i] for i in range(iteration + 1)],
                "loss_curve": [[i, 2.0] for i in range(iteration + 1)],
                "episode_steps_curve": [[i, 30] for i in range(iteration + 1)], "checkpoints": []}
        data.update(changes)
        temporary = progress.with_suffix(".partial")
        temporary.write_text(json.dumps(data))
        temporary.replace(progress)

    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        page.click("#views li[data-run='probe']")
        page.wait_for("document.getElementById('view-kind').textContent === 'RUN probe'")
        assert page.text("#view-relation").startswith("CURRENT")
        assert page.attribute("#views li[data-run='probe']", "data-relation") == "current"
        assert page.text("#view-revision") == REVISION_B
        assert page.text("#view-digest") == "d" * 64
        assert page.text("#view-identity-source") == "project manifest (script.json) at walk start"
        assert "never finished" in page.text("#view-status")
        assert "project manifest (script.json) at walk start" in page.text("#params-note")
        assert page.text("#params tr[data-param='leg_len'] td:nth-child(3)") == "80"
        assert _model_state(page) == "loaded"
        assert "borrowed" in page.text("#model-status") and "run probe" in page.text("#model-status")
        assert page.attribute("#model-components li[data-component='body']", "data-mesh") == "retained"
        # Telemetry arrives beside an identity that is already on screen.
        telemetry(3)
        page.wait_for("document.querySelector('[data-metric=iteration]').textContent === 'iteration: 3'")
        assert page.attribute("#telemetry", "data-state") == "training"
        assert page.text("#view-revision") == REVISION_B
        # The trainer fails, then the walk lands its failed record: the run's
        # identity, specs and model stay; only the state changes.
        telemetry(3, state="failed", error="controlled fixture failure")
        _training_run(root, "probe", revision=REVISION_B, status="failed",
                      error="training did not produce a policy (leg train, exit 3): controlled fixture failure")
        page.wait_for("document.getElementById('view-status').textContent === 'failed'")
        page.wait_for("document.getElementById('telemetry').dataset.state === 'failed'")
        assert page.text("#view-relation").startswith("CURRENT")
        assert page.text("#view-revision") == REVISION_B
        assert page.text("#view-identity-source") == "project manifest (script.json) at walk start"
        assert "controlled fixture failure" in page.text("#view-note")
        assert page.text("#params tr[data-param='leg_len'] td:nth-child(3)") == "80"
        assert page.attribute("#telemetry", "data-state") == "failed"
        assert page.attribute("[data-history=loss_curve]", "data-points") == "4"
        assert _model_state(page) == "loaded" and "borrowed" in page.text("#model-status")
        # The accepted view is untouched by any of it.
        page.click("#views li[data-view='accepted']")
        page.wait_for("document.getElementById('view-kind').textContent === 'ACCEPTED NOW'")
        assert page.text("#view-revision") == REVISION_B
        assert _model_state(page) == "loaded" and "borrowed" not in page.text("#model-status")
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
def test_browser_explains_a_failed_observation_whose_training_finished(tmp_path, browser):
    """The Lark run ``lark109-engine`` on screen (ADR-326): the trainer
    reached ``done`` and saved its policy, then the run's observation
    failed and nothing put the policy in the store. A fresh visit selects
    that failed attempt over the older completed one; the page says the
    training finished and the failure came after it, names the store state
    and the CLI command that stores the retained policy, and serves the
    trainer's copy. When the operator runs that command the page notices
    on its next poll — no reload, no record rewrite — and the run stays
    ``failed``: storing a policy does not rewrite history."""

    root = _project(tmp_path)
    _manifest(root, REVISION_B)
    _stage_accepted(root, REVISION_B)
    _training_run(root, "earlier", revision=REVISION_B, status="ok")
    run = _training_run(root, "probe", revision=REVISION_B)
    payload = b"fixture policy bytes, trained to the last update"
    (run / "train" / "probe.cxpolicy").write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    _telemetry(root, 99, run="probe", state="done", total=100, out="probe.cxpolicy")
    error = ("Observation aborted: the probe's exclusion guard tripped during the "
             "completion wait; the engine kill/restart phases had passed.")
    _training_run(root, "probe", revision=REVISION_B, status="failed", error=error,
                  policy_name="probe.cxpolicy", policy_sha256=digest)
    assert json.loads((run / RUN_RECORD_FILENAME).read_text())["policy"]["asset"] is None

    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        page.wait_for("document.getElementById('view-kind').textContent === 'RUN probe'")
        assert page.text("#view-status") == "failed"
        page.wait_for("document.getElementById('telemetry').dataset.state === 'done'")
        page.wait_for("document.getElementById('view-note').textContent.includes('training itself finished')")
        note = page.text("#view-note")
        assert "error: Observation aborted" in note
        assert "training itself finished (iteration 99 of 100, policy probe.cxpolicy saved by the trainer)" in note
        assert "failed after that, in its observation or recording, not in the trainer" in note
        assert page.attribute("#view-policy-store", "data-state") == "unstored"
        store = page.text("#view-policy-store")
        assert "never stored as a project asset" in store
        assert "trainer copy retained at train/probe.cxpolicy" in store
        assert ("next: store it: cadex asset --project <project-dir> --put "
                "<project-dir>/runs/probe/train/probe.cxpolicy") in store
        assert "or start a new attempt: cadex walk --out runs/<new-name>" in store
        assert page.text("#problems").strip() == ""      # nothing recorded is missing
        row = "#artifacts tr[data-group='artifacts'][data-key='policy']"
        assert page.text(row + " td:nth-child(2)") == "train/probe.cxpolicy"
        assert page.attribute(row + " td:nth-child(3)", "data-status") == "retained"
        assert page.text("#artifacts tr[data-group='project_artifacts'][data-key='policy'] td:nth-child(3)") == "not recorded"
        download = page.download(row + " a[href$='download=1']")
        assert download.path.read_bytes() == payload
        # The operator runs the command the page named (its effect: the store
        # copy appears). The page notices on its own; the record is untouched.
        before = (run / RUN_RECORD_FILENAME).read_bytes()
        (root / "assets" / "probe.cxpolicy").write_bytes(payload)
        page.wait_for("document.getElementById('view-policy-store').dataset.state === 'stored'")
        store = page.text("#view-policy-store")
        assert "holds this policy with the recorded digest" in store and "next:" not in store
        assert page.text("#view-status") == "failed"
        assert "training itself finished" in page.text("#view-note")
        assert (run / RUN_RECORD_FILENAME).read_bytes() == before
        # The earlier completed run is untouched: no policy, no store state.
        page.click("#views li[data-run='earlier']")
        page.wait_for("document.getElementById('view-kind').textContent === 'RUN earlier'")
        assert page.text("#view-status") == "completed"
        assert page.attribute("#view-policy-store", "data-state") == "none"
        assert "training itself finished" not in page.text("#view-note")
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
def test_browser_lists_a_completed_run_whose_policy_was_never_stored_as_a_problem(tmp_path, browser):
    """The Lark runs ``lark96-restart`` and ``lark109-engine2`` on screen
    (ADR-327): bounded drivers that trained to ``done`` and recorded ``ok``
    with the policy under ``train/`` and nothing in the project store. A
    completed run whose only policy copy is the trainer's is a retention
    gap: the page lists it under problems with the one command that closes
    it, beside the policy-store row's advice. When the operator runs that
    command the problem disappears on the next poll — no reload, no record
    rewrite — and the run stays ``completed``. A fresh visit still selects
    the newest run."""

    root = _project(tmp_path)
    _manifest(root, REVISION_B)
    _stage_accepted(root, REVISION_B)
    payloads = {}
    for name in ("bounded-a", "bounded-b"):
        run = _training_run(root, name, revision=REVISION_B)
        payloads[name] = f"fixture policy bytes of {name}".encode()
        (run / "train" / f"{name}.cxpolicy").write_bytes(payloads[name])
        _training_run(root, name, revision=REVISION_B, status="ok",
                      policy_name=f"{name}.cxpolicy",
                      policy_sha256=hashlib.sha256(payloads[name]).hexdigest())
        assert json.loads((run / RUN_RECORD_FILENAME).read_text())["policy"]["asset"] is None
    _telemetry(root, 99, run="bounded-b", state="done", total=100, out="bounded-b.cxpolicy")
    command = "cadex asset --project <project-dir> --put <project-dir>/runs/bounded-b/train/bounded-b.cxpolicy"

    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        page.wait_for("document.getElementById('view-kind').textContent === 'RUN bounded-b'")
        assert page.text("#view-status") == "completed"
        page.wait_for("document.getElementById('view-policy-store').dataset.state === 'unstored'")
        assert ("next: store it: " + command) in page.text("#view-policy-store")
        page.wait_for("document.querySelectorAll('#problems li').length === 1")
        assert page.text("#problems li") == (
            "policy_store: unstored — this completed run's policy bounded-b.cxpolicy is retained at "
            "train/bounded-b.cxpolicy but the project store does not hold it; store it: " + command)
        row = "#artifacts tr[data-group='artifacts'][data-key='policy']"
        assert page.attribute(row + " td:nth-child(3)", "data-status") == "retained"
        # The operator runs the command the page named: the gap closes on the
        # next poll, the record is untouched, and the run is still completed.
        record = root / "runs" / "bounded-b" / RUN_RECORD_FILENAME
        before = record.read_bytes()
        (root / "assets" / "bounded-b.cxpolicy").write_bytes(payloads["bounded-b"])
        page.wait_for("document.getElementById('view-policy-store').dataset.state === 'stored'")
        page.wait_for("document.querySelectorAll('#problems li').length === 0")
        assert page.text("#view-status") == "completed"
        assert "next:" not in page.text("#view-policy-store")
        assert record.read_bytes() == before
        assert page.evaluate("performance.getEntriesByType('navigation').length") == 1
        # The other bounded run still carries its own gap, and only its own.
        page.click("#views li[data-run='bounded-a']")
        page.wait_for("document.getElementById('view-kind').textContent === 'RUN bounded-a'")
        page.wait_for("document.querySelectorAll('#problems li').length === 1")
        assert "bounded-a.cxpolicy" in page.text("#problems li") and "bounded-b" not in page.text("#problems li")
        assert page.attribute("#view-policy-store", "data-state") == "unstored"
        fresh = _open(browser, server.url)
        fresh.wait_for("document.getElementById('view-kind').textContent === 'RUN bounded-b'")
        assert fresh.attribute("#view-policy-store", "data-state") == "stored"
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
@pytest.mark.parametrize('failure_stage', ['header', 'validation', 'witness', 'save'])
def test_browser_observes_final_policy_publication_failure(served, browser, monkeypatch, failure_stage):
    """Fault the real trainer's publication path after a retained checkpoint.

    Training and policy math are fixtures; the atomic writer, failure handler,
    HTTP reader and browser are real. No GPU or verified-policy claim is made.
    """
    import importlib.util
    import types

    root, server = served
    trainer_path = CLI_DIR.parent / 'training/cadex_train.py'
    spec = importlib.util.spec_from_file_location('review_test_trainer', trainer_path)
    trainer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trainer)
    monkeypatch.setitem(sys.modules, 'jax', types.ModuleType('jax'))
    monkeypatch.setitem(sys.modules, 'jax.numpy', types.ModuleType('jax.numpy'))
    monkeypatch.setattr(trainer, 'globals_for', lambda _: {})
    monkeypatch.setattr(trainer, 'load_bundle', lambda *_: {
        'task_sha256': 't' * 64, 'model_sha256': 'm' * 64})
    monkeypatch.setattr(trainer, 'policy_header', lambda *_, **__: {})
    monkeypatch.setattr(trainer, 'checked_policy', lambda *_, **__: b'fixture policy')
    monkeypatch.setattr(trainer, 'witness_disagreement', lambda *_: (0.0, 0, 0))
    target = root / 'runs/first/train/final.cxpolicy'
    progress_path = target.parent / 'progress.json'
    prior_run = root / 'runs/second' / RUN_RECORD_FILENAME
    prior_bytes = prior_run.read_bytes()
    error = RuntimeError('controlled final policy ' + failure_stage + ' failure')
    original_write = trainer.write_atomically

    def fail(*_, **__):
        raise error

    page = _open(browser, server.url)
    page.click("#views li[data-run='first']")
    page.evaluate('window.publicationTestIdentity = {}')

    def trained_fixture(bundle, options, *, emit, progress):
        rows = [{'iteration': 0, 'reward_per_step': 0.5, 'loss': 2.0,
                 'episode_steps': 12}]
        trained = {'parameters': [], 'reward_curve': rows,
                   'wall_time_s': 1.0, 'backend': 'fixture'}
        emit('iter-0', 0, 0.5, trained)
        progress(state='training', iteration=0, total=1, curve=rows,
                 wall=1.0, device='fixture')
        page.wait_for("document.getElementById('telemetry').dataset.state === 'training'")
        if failure_stage == 'save':
            def write(path, blob):
                if path == target:
                    raise error
                return original_write(path, blob)
            monkeypatch.setattr(trainer, 'write_atomically', write)
        else:
            function = {'header': 'policy_header', 'validation': 'checked_policy',
                        'witness': 'witness_disagreement'}[failure_stage]
            monkeypatch.setattr(trainer, function, fail)
        return trained

    monkeypatch.setattr(trainer, 'train', trained_fixture)
    with pytest.raises(RuntimeError) as raised:
        trainer.main(['trainer', 'fixture-task.json', '--out', str(target), '--quiet', '--iterations', '1'])
    assert raised.value is error
    data = json.loads(progress_path.read_text())
    assert data['state'] == 'failed'
    assert data['iteration'] == 0 and data['total'] == 1
    assert data['curve'] == [[0, 0.5]]
    assert data['loss_curve'] == [[0, 2.0]]
    assert data['episode_steps_curve'] == [[0, 12.0]]
    assert data['task_sha256'] == 't' * 64 and data['model_sha256'] == 'm' * 64
    assert data['updated_at'] >= data['started_at']
    assert not target.exists()
    checkpoint = data['checkpoints'][0]
    assert hashlib.sha256((target.parent / checkpoint['path']).read_bytes()).hexdigest() == checkpoint['sha256']
    page.wait_for("document.getElementById('telemetry').dataset.state === 'failed'")
    assert str(error) in page.text('#telemetry')
    assert 'cadex walk' in page.text('#telemetry')
    assert page.text('[data-metric=iteration]') == 'iteration: 0'
    assert page.attribute('[data-history=loss_curve]', 'data-points') == '1'
    assert page.attribute('#checkpoints li', 'data-status') == 'retained'
    assert page.text('#view-revision') == REVISION_A
    assert page.evaluate('!!window.publicationTestIdentity')
    assert prior_run.read_bytes() == prior_bytes


@needs_browser
def test_browser_retained_training_parts_survive_revision_change(served, browser):
    root, server = served
    run = _training_run(root, 'exported', revision=REVISION_A)
    model_xml = run / 'train/model.xml'
    model_xml.write_text('<mujoco/>')
    mesh = run / 'train/torso.stl'
    mesh.write_text(_cube_stl(20))
    record = json.loads((run / RUN_RECORD_FILENAME).read_text())
    _rewrite_record(run, artifacts={**record['artifacts'], 'model_xml': 'train/model.xml'})
    before = {p: p.read_bytes() for p in run.rglob('*') if p.is_file()}
    page = _open(browser, server.url)
    page.click("#views li[data-run='exported']")
    page.wait_for("document.getElementById('view-kind').textContent === 'RUN exported'")
    assert _model_state(page) == 'loaded'
    assert page.text('#view-revision') == REVISION_A
    assert page.text('#view-relation').startswith('HISTORICAL')
    assert 'assembly placements not recorded' in page.text('#model-status')
    assert 'not a solved pose' in page.text('#model-status')
    page.scroll_into_view('#viewer')
    rect = page.rect('#viewer')
    x, y = rect['x'] + rect['width']/2, rect['y'] + rect['height']/2
    camera = page.evaluate('window.cadexReview.viewer().camera()')
    page.drag(x, y, x+100, y+40)
    page.wait_for(f'window.cadexReview.viewer().camera().yaw !== {camera["yaw"]}')
    page.wheel(x, y, -240)
    page.wait_for(f'window.cadexReview.viewer().camera().distance < {camera["distance"]}')
    assert page.evaluate('window.cadexReview.viewer().nonBackgroundPixels()') > 1000
    assert _get(server.url + 'mesh/run/exported/torso.stl')[2] == mesh.read_bytes()
    assert before == {p: p.read_bytes() for p in run.rglob('*') if p.is_file()}
    # A deleted export, escaping anchor or symlinked mesh cannot borrow today's model.
    mesh.unlink()
    mesh.symlink_to(root / 'runs/second/rollout/torso.stl')
    assert not _json(server.url + 'api/model/run/exported')['available']
    assert _get(server.url + 'mesh/run/exported/torso.stl')[0] == 404
    mesh.unlink()
    mesh.write_text(_cube_stl(20))
    model_xml.unlink()
    assert not _json(server.url + 'api/model/run/exported')['available']
    model_xml.symlink_to(root / 'script.json')
    assert not _json(server.url + 'api/model/run/exported')['available']
    assert _get(server.url + 'mesh/run/exported/torso.stl')[0] == 404
    _rewrite_record(run, artifacts={**record['artifacts'], 'model_xml': '../outside.xml'})
    assert not _json(server.url + 'api/model/run/exported')['available']


@needs_browser
def test_browser_training_snapshot_keeps_assembly_and_documents(tmp_path, browser):
    from cadex_cli.review_server import retain_training_view

    root = _project(tmp_path)
    _manifest(root, REVISION_A)
    staging = _stage_accepted(root, REVISION_A)
    run = _training_run(root, 'frozen', revision=REVISION_A)
    (root / 'DECISIONS.md').write_text('## ADR-1: Original narrow stance\n')
    retain_training_view(root, run)
    frozen = (run / 'training-view.json').read_bytes()
    identity = json.loads(frozen)['identity']
    mesh = (run / 'training-view/torso.stl').read_bytes()
    _manifest(root, REVISION_B)
    revised = _stage_accepted(root, REVISION_B)
    (revised / 'outputs/assembly-simulation-trace.json').write_text(
        _trace({'body': [1000.0, 0.0, 0.0]}))
    shutil.rmtree(staging)
    manifest = json.loads((root / 'script.json').read_text())
    manifest['param_values'] = {'leg_len': 120}
    manifest['param_specs'] = [{'name': 'leg_len', 'default': 110}]
    (root / 'script.json').write_text(json.dumps(manifest))
    (root / 'DECISIONS.md').write_text('## ADR-2: Wider revised stance\n')
    retain_training_view(root, run)
    write_run_record(run, project_root=root, status='failed', mode='blocking',
                     accepted_revision=REVISION_A, digest='d' * 64,
                     snapshot_docs=True, params={'leg_len': 999})
    assert (run / 'training-view.json').read_bytes() == frozen
    assert (run / 'training-view/torso.stl').read_bytes() == mesh
    server, _thread = serve(root, '127.0.0.1', 0)
    try:
        page = _open(browser, server.url)
        page.evaluate("window.cadexReview.select('accepted')", await_promise=True)
        accepted_target = page.evaluate('window.cadexReview.viewer().camera().target')
        page.click("#views li[data-run='frozen']")
        page.wait_for("document.getElementById('view-kind').textContent === 'RUN frozen'")
        assert _model_state(page) == 'loaded'
        assert page.text('#view-revision') == REVISION_A
        assert page.text('#view-relation').startswith('HISTORICAL')
        record = read_run_record(run, root)
        assert record['params']['values'] == identity['param_values']
        assert record['params']['specs'] == identity['param_specs']
        assert page.text("#params tr[data-param='leg_len'] td:nth-child(2)") == '90'
        assert page.text("#params tr[data-param='leg_len'] td:nth-child(3)") == '80'
        assert 'retained before training' in page.text('#model-status')
        assert page.evaluate('window.cadexReview.viewer().camera().target') != accepted_target
        assert page.evaluate('window.cadexReview.viewer().nonBackgroundPixels()') > 1000
        model = _json(server.url + 'api/model/run/frozen')
        assert model['components'][0]['name'] == 'body'
        assert model['components'][0]['placement']['position_mm'] == [5, 0, 10]
        page.click("#docs li[data-doc='DECISIONS.md'] a")
        page.wait_for("document.body.textContent.includes('Original narrow stance')")
        assert 'Wider revised stance' not in page.text('body')
        assert _get(server.url + 'mesh/run/frozen/torso.stl')[2] == mesh
        (run / 'training-view/torso.stl').write_bytes(b'changed mesh')
        assert _get(server.url + 'mesh/run/frozen/torso.stl')[0] == 404
        assert _json(server.url + 'api/model/run/frozen')['components'][0]['mesh_status'] == 'digest mismatch'
        (run / 'training-view/torso.stl').unlink()
        (run / 'training-view/torso.stl').symlink_to(root / 'script.json')
        assert _get(server.url + 'mesh/run/frozen/torso.stl')[0] == 404
        (run / 'training-view.json').write_text('{')
        assert not _json(server.url + 'api/model/run/frozen')['available']
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
def test_browser_walk_parameter_sweep_retains_model_before_training(
    engine, tmp_path, capsys, monkeypatch, browser,
):
    """Real engine/params/walk; stop at trainer dispatch, then revise again."""
    from cadex_cli import __main__ as command
    from cadex_cli.report import EXIT_FAILURE
    from cadex_cli.walk import Leg
    from test_train import _run
    from test_walk import TOY

    root = tmp_path / 'swept-project'
    source = tmp_path / 'mechanism.py'
    source.write_text(TOY.replace(
        'p = params(', 'p = params(arm_len=num(80, min=40, max=160), '
    ).replace('part.box(80, 8, 8)', 'part.box(p.arm_len, 8, 8)'))
    code, result = _run(capsys, 'script', '--project', str(root), '--set', str(source))
    assert code == EXIT_OK, result
    initial_revision = result['accepted_revision']
    run = root / 'runs/swept'
    server, _thread = serve(root, '127.0.0.1', 0)
    real_run_leg = command.run_leg
    evidence = {}

    def dispatch(name, argv, **kwargs):
        if name != 'train':
            return real_run_leg(name, argv, **kwargs)
        # This callback is the exact boundary before any trainer starts.
        record = read_run_record(run, root)
        revision = record['model']['accepted_revision']
        assert revision != initial_revision
        assert record['status'] == 'running'
        assert record['params']['values']['arm_len'] == 100
        model = _json(server.url + 'api/model/run/swept')
        assert model['available'], model
        assert model['revision'] == revision
        assert model['digest'] == record['model']['digest']
        assert {c['name'] for c in model['components']} == {'base', 'swing'}
        assert all(c['placement'] for c in model['components'])
        mesh_bytes = {c['name']: _get(server.url.rstrip('/') + c['mesh'])[2]
                      for c in model['components']}
        page = _open(browser, server.url)
        page.click("#views li[data-run='swept']")
        page.wait_for("document.getElementById('view-kind').textContent === 'RUN swept'")
        assert _model_state(page) == 'loaded'
        assert page.text('#view-revision') == revision
        assert page.text("#params tr[data-param='arm_len'] td:nth-child(2)") == '100'
        assert page.text("#params tr[data-param='arm_len'] td:nth-child(3)") == '80'
        assert page.text('#view-relation').startswith('CURRENT')
        assert 'assembled model retained before training' in page.text('#model-status')
        page.scroll_into_view('#viewer')
        rect = page.rect('#viewer')
        x, y = rect['x'] + rect['width']/2, rect['y'] + rect['height']/2
        camera = page.evaluate('window.cadexReview.viewer().camera()')
        page.drag(x, y, x+90, y+40)
        page.wait_for(f'window.cadexReview.viewer().camera().yaw !== {camera["yaw"]}')
        page.wheel(x, y, -240)
        page.wait_for(f'window.cadexReview.viewer().camera().distance < {camera["distance"]}')
        assert page.evaluate('window.cadexReview.viewer().nonBackgroundPixels()') > 1000
        evidence.update(page=page, model=model, meshes=mesh_bytes,
                        marker=(run / 'training-view.json').read_bytes())
        return Leg(name, argv, code=EXIT_FAILURE,
                   envelope={'error': 'intentional stop at training dispatch'})

    monkeypatch.setattr(command, 'run_leg', dispatch)
    try:
        code, result = _run(capsys, 'walk', '--project', str(root), '--out', str(run),
                            '--set', 'arm_len=100', '--iterations', '1', '--envs', '4')
        assert code == EXIT_FAILURE, result
        assert 'intentional stop' in result['error']
        code, later = _run(capsys, 'params', '--project', str(root), '--set', 'arm_len=140')
        assert code == EXIT_OK, later
        assert later['accepted_revision'] != evidence['model']['revision']
        # Retained bytes, rather than any staging cache, are what the URL serves.
        page = evidence['page']
        page.wait_for("document.getElementById('view-relation').textContent.startsWith('HISTORICAL')",
                      timeout=10)
        assert _model_state(page) == 'loaded'
        assert page.text('#view-revision') == evidence['model']['revision']
        assert page.text("#params tr[data-param='arm_len'] td:nth-child(2)") == '100'
        assert page.text("#params tr[data-param='arm_len'] td:nth-child(3)") == '80'
        assert (run / 'training-view.json').read_bytes() == evidence['marker']
        historical = _json(server.url + 'api/model/run/swept')
        assert historical['components'] == evidence['model']['components']
        for component in historical['components']:
            assert _get(server.url.rstrip('/') + component['mesh'])[2] == evidence['meshes'][component['name']]
        record = read_run_record(run, root)
        assert record['params']['values']['arm_len'] == 100
        assert record['status'] == 'failed'
        accepted = _json(server.url + 'api/model/accepted')
        swing = next(c for c in accepted['components'] if c['name'] == 'swing')
        assert _get(server.url.rstrip('/') + swing['mesh'])[2] != evidence['meshes']['swing']
    finally:
        server.shutdown()
        server.server_close()


def test_browser_refuses_damaged_video_and_recovers(served, browser, monkeypatch):
    root, server = served
    run = root / 'runs/first'
    video = run / 'final.webm'
    original = bytes(range(128))
    video.write_bytes(original)
    _rewrite_record(run, videos=[{'path': video.name,
                                 'sha256': hashlib.sha256(original).hexdigest()}])
    page = _open(browser, server.url)
    page.click("#views li[data-run='first']")
    page.wait_for("!!document.querySelector('#videos video')")
    from cadex_cli import review_record
    original_hash = review_record._sha256
    reads = []
    def counted(path):
        if path == video:
            reads.append(path)
        return original_hash(path)
    monkeypatch.setattr(review_record, '_sha256', counted)
    for _ in range(3):
        page.evaluate('window.cadexReview.refresh()', await_promise=True)
    assert not reads, 'polling an unchanged retained video must not reread its bytes'
    for damaged in (original[:32], b'x' * len(original)):
        video.write_bytes(damaged)
        page.wait_for("document.getElementById('videos').textContent.includes('digest mismatch')")
        assert not page.evaluate("!!document.querySelector('#videos video')")
        assert 'Retry the CLI video command' in page.text('#videos')
        assert _get(server.url + 'video/run/first/0')[0] == 404
        assert _get(server.url + 'video/run/first/0', {'Range': 'bytes=0-5'})[0] == 404
        video.write_bytes(original)
        page.wait_for("!!document.querySelector('#videos video')")
        assert _get(server.url + 'video/run/first/0')[2] == original
    video.unlink()
    page.wait_for("document.querySelector('#videos [data-video]').textContent.includes('missing')")
    assert 'Retry the CLI video command' in page.text('#videos')


def test_browser_coalesces_polls_during_initial_video_verification(served, browser, monkeypatch):
    """Cold verification exceeding three poll intervals must read bytes once."""
    from cadex_cli import review_record
    root, server = served
    run = root / 'runs/first'
    video = run / 'cold.webm'
    video.write_bytes(b'corrupt retained video')
    _rewrite_record(run, videos=[{'path': video.name, 'sha256': '0' * 64}])
    entered, release = threading.Event(), threading.Event()
    original_hash = review_record._sha256
    reads = []

    def slow_hash(path):
        if path == video:
            reads.append(path)
            entered.set()
            if not release.wait(20):
                raise OSError('test verification timed out')
        return original_hash(path)

    monkeypatch.setattr(review_record, '_sha256', slow_hash)
    page = browser.page(server.url)
    try:
        assert entered.wait(5)
        page.evaluate('new Promise(resolve => setTimeout(resolve, 7200))', await_promise=True)
        assert page.attribute('#freshness', 'data-state') == 'loading'
        assert not page.evaluate("!!document.querySelector('#videos video')")
        assert len(reads) == 1, 'slow initial verification must not launch overlapping polls'
    finally:
        release.set()
    page.evaluate('window.cadexReview.ready', await_promise=True)
    page.click("#views li[data-run='first']")
    page.wait_for("document.getElementById('videos').textContent.includes('digest mismatch')")
    assert not page.evaluate("!!document.querySelector('#videos video')")
    # Completion releases the pending request, so subsequent changes still arrive.
    _rewrite_record(run, status='failed')
    page.wait_for("document.getElementById('view-status').textContent === 'failed'")
    assert page.attribute('#freshness', 'data-state') == 'live'
    assert len(reads) == 1


def test_two_browser_clients_share_cold_video_verification(served, browser, monkeypatch):
    """Concurrent clients must share byte reads and both refuse corrupt output."""
    from cadex_cli import review_record
    root, server = served
    run = root / 'runs/first'
    video = run / 'shared-cold.webm'
    video.write_bytes(b'corrupt retained video')
    _rewrite_record(run, videos=[{'path': video.name, 'sha256': '0' * 64}])
    entered, second, release = threading.Event(), threading.Event(), threading.Event()
    original_hash = review_record._sha256
    original_verify = review_record._video_sha256
    reads, requests = [], []

    def verify(path):
        if path == video:
            requests.append(path)
            if len(requests) == 2:
                second.set()
        return original_verify(path)

    def slow_hash(path):
        if path == video:
            reads.append(path)
            entered.set()
            if not release.wait(20):
                raise OSError('test verification timed out')
        return original_hash(path)

    monkeypatch.setattr(review_record, '_sha256', slow_hash)
    monkeypatch.setattr(review_record, '_video_sha256', verify)
    first = browser.page(server.url)
    try:
        assert entered.wait(5)
        other = browser.page(server.url)
        assert second.wait(5), 'second browser must reach server verification'
        for page in (first, other):
            assert page.attribute('#freshness', 'data-state') == 'loading'
            assert not page.evaluate("!!document.querySelector('#videos video')")
    finally:
        release.set()
    for page in (first, other):
        page.evaluate('window.cadexReview.ready', await_promise=True)
        page.click("#views li[data-run='first']")
        page.wait_for("document.getElementById('videos').textContent.includes('digest mismatch')")
        assert not page.evaluate("!!document.querySelector('#videos video')")
    assert len(reads) == 1, 'two cold clients must hash the shared file once'
    # Publish one file version: truncating in place exposes an intermediate
    # empty file to timer polls, which correctly needs another verification.
    replacement = video.with_suffix('.partial')
    replacement.write_bytes(b'changed corrupt bytes')
    replacement.replace(video)
    for page in (first, other):
        page.evaluate('window.cadexReview.refresh()', await_promise=True)
        assert 'digest mismatch' in page.text('#videos')
    assert len(reads) == 2, 'changed bytes need one fresh verification'
    assert review_record._cached_video_sha256.cache_info().maxsize == 256


@needs_browser
def test_browser_current_attempt_selection_preserves_deliberate_history(served, browser):
    root, server = served
    first = root / 'runs/first'
    second = root / 'runs/second'
    _rewrite_record(first, recorded_at='2026-01-01T00:00:00Z', status='running')
    _rewrite_record(second, recorded_at='2026-01-03T00:00:00Z', status='failed')
    _rewrite_record(root / 'runs/broken', recorded_at='2026-01-02T00:00:00Z')
    _telemetry(root)
    page = _open(browser, server.url)
    assert page.text('#view-kind') == 'RUN first'  # active beats newer failure
    assert page.attribute('#telemetry', 'data-state') == 'training'
    _telemetry(root, state='failed')
    _rewrite_record(first, status='failed')
    page.wait_for("document.getElementById('view-kind').textContent === 'RUN second'")
    assert page.text('#view-status') == 'failed'
    assert _model_state(page) == 'loaded'
    assert page.text('#view-revision') == REVISION_B
    fresh = _open(browser, server.url)
    assert fresh.text('#view-kind') == 'RUN second'
    page.click("#views li[data-run='first']")
    page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
    _rewrite_record(second, recorded_at='2026-01-04T00:00:00Z')
    page.evaluate('window.cadexReview.refresh()', await_promise=True)
    assert page.text('#view-kind') == 'RUN first'
    assert page.text('#view-revision') == REVISION_A
    assert 'second' in page.text('#current-run')
    page.click('#current-run')
    assert page.text('#view-kind') == 'RUN second'
    _rewrite_record(first, status='running')
    _telemetry(root, updated_at=time.time() - 60)
    page.evaluate('window.cadexReview.refresh()', await_promise=True)
    assert page.text('#view-kind') == 'RUN second'  # stale is not active
    _telemetry(root)
    page.wait_for("document.getElementById('view-kind').textContent === 'RUN first'")


@needs_browser
def test_browser_playing_video_survives_new_current_attempt(served, browser):
    from test_video import _video_run
    from cadex_cli.video import render as render_video

    if not shutil.which('ffmpeg'):
        pytest.skip('FFmpeg not available')
    root, server = served
    run = _video_run(root)
    render_video(root, 'sample')
    _rewrite_record(run, recorded_at='2099-01-01T00:00:00Z')
    page = _open(browser, server.url)
    assert page.text('#view-kind') == 'RUN sample'
    page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
    page.evaluate("window.playing = document.querySelector('#videos video'); playing.muted = true; playing.loop = true; playing.play()", await_promise=True)
    page.wait_for('playing.currentTime > 0.1')
    _rewrite_record(root / 'runs/second', recorded_at='2099-01-02T00:00:00Z', status='failed')
    page.evaluate('window.cadexReview.refresh()', await_promise=True)
    assert page.text('#view-kind') == 'RUN sample'
    assert page.evaluate("playing === document.querySelector('#videos video') && !playing.paused")
    assert 'second' in page.text('#current-run')
    fresh = _open(browser, server.url)
    assert fresh.text('#view-kind') == 'RUN second'
    assert fresh.text('#view-status') == 'failed'
    page.click('#current-run')
    assert page.text('#view-kind') == 'RUN second'


@needs_browser
def test_browser_historical_playback_survives_published_failed_attempt(served, browser):
    from test_video import _video_run
    from cadex_cli.video import render as render_video

    if not shutil.which('ffmpeg'):
        pytest.skip('FFmpeg not available')
    root, server = served
    old = _video_run(root, 'historical-video')
    video = render_video(root, 'historical-video')
    _rewrite_record(old, recorded_at='2099-01-01T00:00:00Z')
    _rewrite_record(root / 'runs/second', recorded_at='2099-01-02T00:00:00Z')
    page = _open(browser, server.url)
    assert page.text('#view-kind') == 'RUN second'
    page.click("#views li[data-run='historical-video']")
    assert page.text('#view-relation').startswith('HISTORICAL')
    revision = page.text('#view-revision')
    page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
    page.evaluate("window.playing=document.querySelector('#videos video');"
                  "window.playedSeconds=0; window.lastVideoTime=0;"
                  "playing.addEventListener('timeupdate', () => {"
                  "playedSeconds += Math.max(0, playing.currentTime-lastVideoTime);"
                  "lastVideoTime=playing.currentTime; });"
                  "playing.muted=true; playing.loop=true; playing.play()", await_promise=True)
    page.wait_for('playedSeconds > 0.1')

    # Publish a new attempt, rather than relabelling a run already in the list.
    failed = _mesh_run(root, 'new-failure', revision=REVISION_B)
    _rewrite_record(failed, recorded_at='2099-01-03T00:00:00Z', status='failed')
    page.wait_for("document.getElementById('current-run').textContent === 'Current run: new-failure'")
    elapsed = page.evaluate('playedSeconds')
    # Count two subsequent automatic polls; never call refresh from the test.
    page.evaluate("window.polls=0; window.originalFetch=window.fetch;"
                  "window.fetch=async (...args) => { const response=await originalFetch(...args);"
                  "if(String(args[0]).includes('api/project')) polls++; return response; }")
    page.wait_for('polls >= 2 && playedSeconds > ' + str(elapsed + 0.25))
    assert page.text('#view-kind') == 'RUN historical-video'
    assert page.text('#view-revision') == revision
    assert page.text('#view-relation').startswith('HISTORICAL')
    assert page.evaluate("playing===document.querySelector('#videos video') && !playing.paused")
    assert hashlib.sha256(page.download('#videos a').path.read_bytes()).hexdigest() == video['sha256']

    fresh = _open(browser, server.url)
    assert fresh.text('#view-kind') == 'RUN new-failure'
    assert fresh.text('#view-status') == 'failed'
    assert fresh.text('#view-revision') == REVISION_B
    assert not fresh.evaluate("!!document.querySelector('#videos video')")
    page.send('Page.bringToFront')
    assert page.text('#view-kind') == 'RUN historical-video'
    assert page.evaluate("playing===document.querySelector('#videos video') && !playing.paused")
    page.click('#current-run')
    assert page.text('#view-kind') == 'RUN new-failure'
    assert page.text('#view-status') == 'failed'
    assert page.text('#view-revision') == REVISION_B
    assert page.evaluate("performance.getEntriesByType('navigation').length") == 1


@needs_browser
def test_browser_current_run_gains_video_preserving_historical_playback(served, browser):
    from test_video import _video_run
    from cadex_cli.video import render as render_video

    if not shutil.which('ffmpeg'):
        pytest.skip('FFmpeg not available')
    root, server = served
    old = _video_run(root, 'old-video')
    old_video = render_video(root, 'old-video')
    current = _video_run(root, 'current-video')
    trace_path = current / 'rollout/assembly-simulation-trace.json'
    trace = json.loads(trace_path.read_text())
    trace['frames'][-1]['component_placements']['body']['position_mm'][2] += 20
    trace_path.write_text(json.dumps(trace))
    _rewrite_record(old, recorded_at='2099-01-01T00:00:00Z')
    _rewrite_record(current, recorded_at='2099-01-02T00:00:00Z')
    page = _open(browser, server.url)
    assert page.text('#view-kind') == 'RUN current-video'
    assert not page.evaluate("!!document.querySelector('#videos video')")
    page.click("#views li[data-run='old-video']")
    page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
    old_revision = page.text('#view-revision')
    page.evaluate("window.playing=document.querySelector('#videos video'); playing.muted=true; playing.loop=true; playing.play()", await_promise=True)
    page.wait_for('playing.currentTime > 0.1')
    # Publish through the actual renderer/status writer while history is playing.
    published = render_video(root, 'current-video')
    assert published['sha256'] != old_video['sha256']
    page.evaluate('window.cadexReview.refresh()', await_promise=True)
    assert page.text('#view-kind') == 'RUN old-video'
    assert page.text('#view-revision') == old_revision
    assert page.evaluate("playing===document.querySelector('#videos video') && !playing.paused")
    assert 'current-video' in page.text('#current-run')
    page.click('#current-run')
    page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
    assert page.text('#view-kind') == 'RUN current-video'
    page.evaluate("window.newVideo=document.querySelector('#videos video'); newVideo.muted=true; newVideo.play()", await_promise=True)
    page.wait_for('newVideo.currentTime > 0.1')
    download = page.download('#videos a')
    assert hashlib.sha256(download.path.read_bytes()).hexdigest() == published['sha256']
    fresh = _open(browser, server.url)
    assert fresh.text('#view-kind') == 'RUN current-video'
    fresh.wait_for("document.querySelector('#videos video')?.readyState >= 2")

    # Recover current output while a historical video remains playing. Real
    # encoded bytes exercise playback as well as the retained-file hash gate.
    video_path = current / published['path']
    retained = video_path.read_bytes()
    for fault in ('missing', 'partial'):
        if fault == 'missing':
            video_path.unlink()
        else:
            video_path.write_bytes(retained[:64])
        message = 'missing' if fault == 'missing' else 'digest mismatch'
        fresh.wait_for("document.querySelector('#videos [data-video]').textContent.includes(" +
                       json.dumps(message) + ")")
        assert fresh.text('#videos > li') == 'Video files: unavailable (0/1 retained)'
        assert 'Retry the CLI video command' in fresh.text('#videos')
        assert not fresh.evaluate("!!document.querySelector('#videos video, #videos a')")
        assert _get(server.url + 'video/run/current-video/0')[0] == 404
        assert _get(server.url + 'video/run/current-video/0', {'Range': 'bytes=0-63'})[0] == 404
        page.send('Page.bringToFront')
        page.click("#views li[data-run='old-video']")
        page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
        page.evaluate("window.playing=document.querySelector('#videos video'); playing.muted=true; playing.loop=true; playing.play()", await_promise=True)
        page.wait_for('playing.currentTime > 0.1')
        assert hashlib.sha256(page.download('#videos a').path.read_bytes()).hexdigest() == old_video['sha256']
        video_path.write_bytes(retained)
        fresh.wait_for("!!document.querySelector('#videos video')")
        page.evaluate('window.cadexReview.refresh()', await_promise=True)
        assert page.text('#view-kind') == 'RUN old-video'
        assert page.text('#view-revision') == old_revision
        assert page.evaluate("playing===document.querySelector('#videos video') && !playing.paused")
        page.click('#current-run')
        page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
        assert hashlib.sha256(page.download('#videos a').path.read_bytes()).hexdigest() == published['sha256']
        assert page.evaluate("performance.getEntriesByType('navigation').length") == 1


def test_byte_identical_outputs_each_keep_their_accepted_mesh(served, tmp_path) -> None:
    """A mirrored pair of legs is two outputs with one BREP digest; the
    accepted model and the retained training view show both, not one."""

    root, server = served
    staging = _stage_accepted(root, REVISION_B)
    for index, side in ((1, "thigh_l"), (2, "thigh_r")):
        brep = staging / "outputs" / f"output-00{index}.brep"
        brep.write_bytes(b"DBRep_DrawableShape same thigh both sides\n")
        sidecar, data = _cube_tessellation(8.0)
        sidecar["artifact_path"] = f"display/display-00{index}.tess.bin"
        sidecar["source_sha256"] = hashlib.sha256(brep.read_bytes()).hexdigest()
        (staging / "display" / f"display-00{index}.tess.json").write_text(json.dumps(sidecar))
        (staging / "display" / f"display-00{index}.tess.bin").write_bytes(data)
    result = json.loads((staging / "result.json").read_text())
    result["component_sources"].update({"src-2": "thigh_l", "src-3": "thigh_r"})
    for index, side, y in ((1, "thigh_l", 25.0), (2, "thigh_r", -25.0)):
        result["outputs"].append({"name": side, "type": "solid", "artifact_kind": "brep",
                                  "artifact_path": f"outputs/output-00{index}.brep"})
        result["outputs"].append({"name": side + "_link", "type": "component_link", "definition": {
            "arguments": [{"object_name": f"src-{index + 1}"}],
            "properties": {"placement": {"position": [0.0, y, 0.0], "rotation": [0.0, 0.0, 0.0, 1.0]}}}})
    (staging / "result.json").write_text(json.dumps(result))
    model = _json(server.url + "api/model/accepted")
    meshes = {c["name"]: c["mesh_status"] for c in model["components"]}
    assert meshes == {"body": "retained", "thigh_l_link": "retained", "thigh_r_link": "retained"}
    for side in ("thigh_l", "thigh_r"):
        status, _headers, body = _get(server.url + f"mesh/accepted/{side}.stl")
        assert status == 200 and body.startswith(b"cadex tessellation as binary STL")
    from cadex_cli.review_server import retain_training_view
    run = root / "runs" / "frozen"
    run.mkdir(parents=True)
    retain_training_view(root, run)
    assert sorted(p.name for p in (run / "training-view").iterdir()) == ["thigh_l.stl", "thigh_r.stl", "torso.stl"]
    retained = json.loads((run / "training-view.json").read_text())["model"]["components"]
    assert all(entry["mesh"] for entry in retained), retained


@needs_browser
@pytest.mark.parametrize('view', ['accepted', 'first'])
def test_browser_keeps_open_document_across_polls_until_view_changes(served, browser, view):
    _root, server = served
    page = _open(browser, server.url)
    page.evaluate('window.cadexReview.select(' + json.dumps(view) + ')', await_promise=True)
    page.click("#docs li[data-doc='DECISIONS.md'] a")
    page.wait_for("document.getElementById('doc-view').textContent.includes('ADR-')")
    body = page.text('#doc-view')
    for _ in range(3):
        page.evaluate('window.cadexReview.refresh()', await_promise=True)
        assert not page.evaluate("document.getElementById('doc-view').classList.contains('hidden')")
        assert page.text('#doc-view') == body
    other = 'second' if view == 'first' else 'first'
    page.evaluate('window.cadexReview.select(' + json.dumps(other) + ')', await_promise=True)
    assert page.evaluate("document.getElementById('doc-view').classList.contains('hidden')")


@needs_browser
def test_browser_document_reading_pins_current_and_ignores_late_response(served, browser):
    root, server = served
    page = _open(browser, server.url)
    selected = page.evaluate('window.cadexReview.state().selected')
    page.click("#docs li[data-doc='DECISIONS.md'] a")
    page.wait_for("document.getElementById('doc-view').textContent.includes('Loaded on open;')")
    _mesh_run(root, 'new-attempt', revision=REVISION_B)
    _rewrite_record(root / 'runs' / 'new-attempt', recorded_at='2099-01-01T00:00:00Z')
    page.evaluate('window.cadexReview.refresh()', await_promise=True)
    assert page.text('#current-run') == 'Current run: new-attempt'
    assert page.evaluate('window.cadexReview.state().selected') == selected
    assert not page.evaluate("document.getElementById('doc-view').classList.contains('hidden')")
    # Delay a document response across a view change and a newer document load.
    page.evaluate("""(() => {
      const original = window.fetch;
      window.fetch = function(url, options) {
        if (url.startsWith('/doc/') && !window.delayedDoc) {
          return new Promise(resolve => { window.delayedDoc = () => resolve(new Response('obsolete response')); });
        }
        return original(url, options);
      };
    })()""")
    page.click("#docs li[data-doc='DECISIONS.md'] a")
    page.wait_for('!!window.delayedDoc')
    page.click('#current-run')
    page.wait_for("document.getElementById('view-kind').textContent === 'RUN new-attempt'")
    assert page.evaluate("document.getElementById('doc-view').classList.contains('hidden')")
    page.click("#docs li[data-doc='DECISIONS.md'] a")
    page.wait_for("document.getElementById('doc-view').textContent.includes('Loaded on open;')")
    body = page.text('#doc-view')
    page.evaluate('window.delayedDoc()')
    page.evaluate('new Promise(resolve => setTimeout(resolve, 50))', await_promise=True)
    assert page.text('#doc-view') == body


@needs_browser
@pytest.mark.parametrize('initially_accepted', [True, False])
def test_browser_accepted_geometry_tracks_live_identity(tmp_path, browser, initially_accepted):
    root = _review_project(tmp_path)
    if initially_accepted:
        _stage_accepted(root, REVISION_B)
    else:
        (root / 'script.json').unlink()
    server, _thread = serve(root, '127.0.0.1', 0)
    try:
        page = _open(browser, server.url)
        page.evaluate("window.cadexReview.select('accepted')", await_promise=True)
        assert _model_state(page) == ('loaded' if initially_accepted else 'missing')
        # Publish a new accepted attempt while this browser keeps inspecting.
        _manifest(root, REVISION_A)
        staging = _stage_accepted(root, REVISION_A)
        sidecar, data = _cube_tessellation(40.0)
        old = json.loads((staging / 'display/display-000.tess.json').read_text())
        sidecar.update({key: old[key] for key in ['artifact_path', 'source_sha256']})
        (staging / 'display/display-000.tess.json').write_text(json.dumps(sidecar))
        (staging / 'display/display-000.tess.bin').write_bytes(data)
        page.evaluate('window.cadexReview.refresh()', await_promise=True)
        assert page.text('#view-revision') == REVISION_A
        assert page.evaluate('window.cadexReview.state().model.revision') == REVISION_A
        assert _model_state(page) == 'loaded'
        assert page.evaluate('window.cadexReview.viewer().stats().bounds.max[0]') == 45.0
        # Identical polls must preserve deliberate orbit/zoom.
        page.evaluate('const viewer = window.cadexReview.viewer(); const camera = viewer.camera(); camera.yaw += .3; camera.distance *= 1.2; viewer.setCamera(camera); window.cameraBefore = viewer.camera()')
        page.evaluate('window.cadexReview.refresh()', await_promise=True)
        assert page.evaluate('JSON.stringify(cameraBefore) === JSON.stringify(window.cadexReview.viewer().camera())')
        # A later acceptance must not replace a selected retained historical mesh.
        page.evaluate("window.cadexReview.select('second')", await_promise=True)
        page.evaluate('window.cadexReview.refresh()', await_promise=True)
        assert page.evaluate('window.cadexReview.state().model.revision') == REVISION_B
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
def test_browser_draws_a_first_accepted_script_written_through_the_bridge_without_a_render(
    engine, tmp_path, browser,
):
    """A project straight out of the agent's turn has a model to show (ADR-312).

    The agent's writes reach the engine through the bridge, which used to omit
    ``display``: the first accepted attempt had BREP outputs and no
    tessellation, and this page said ``accepted attempt retained no
    tessellation`` until ``cadex render`` republished it. The bridge now asks
    for the standard tessellation on every modelling op. This is the same
    path ``cadex -p`` takes minus the model, on a fresh project, with no
    render, params or rebuild afterwards — and the store keeps the ADR-311
    shape the reader must tolerate: the attempt staged under the pre-run
    revision while the accepted revision carries the collected specs.
    """
    from cadex_cli.bridge import Bridge
    from cadex_cli.client import CadexdClient, open_project
    from cadex_cli.session import read_working_revision
    from test_walk import TOY

    root = tmp_path / 'fresh-project'
    source = TOY.replace(
        'p = params(', 'p = params(arm_len=num(80, min=40, max=160), '
    ).replace('part.box(80, 8, 8)', 'part.box(p.arm_len, 8, 8)')
    client = CadexdClient(engine)
    client.start()
    try:
        open_project(client, root)
        with Bridge(client, initial_revision=read_working_revision(client)) as bridge:
            reply = bridge.call('write_script', {'source': source})
        payload = json.loads(reply['content'][0]['text'])
        assert payload['ok'] is True, payload
        assert 'display' not in payload  # the model still never sees the block
    finally:
        client.shutdown()
    manifest = json.loads((root / 'script.json').read_text())
    accepted = manifest['accepted_revision']
    assert payload['revision'] == accepted
    staging = Path(manifest['accepted_attempt']['staging'])
    assert staging.parts[0] == 'script_artifacts' and staging.parts[1] != accepted
    assert not (root / 'review').exists()  # nothing rendered, rebuilt or exported

    server, _thread = serve(root, '127.0.0.1', 0)
    try:
        model = _json(server.url + 'api/model/accepted')
        assert model['available'] is True, model
        assert model['revision'] == accepted and model['digest'] == manifest['accepted_digest']
        assert model['source'].startswith("the accepted attempt's tessellation (display/*.tess)")
        assert {c['name'] for c in model['components']} == {'base', 'swing'}
        page = _open(browser, server.url)
        assert _model_state(page) == 'loaded'
        status = page.text('#model-status')
        assert status.startswith('accepted model at revision ' + accepted[:12])
        assert '2 component(s)' in status and 'retained no tessellation' not in status
        assert page.text('#view-revision') == accepted
        assert page.text("#params tr[data-param='arm_len'] td:nth-child(3)") == '80'
        assert page.evaluate('window.cadexReview.viewer().nonBackgroundPixels()') > 1000
    finally:
        server.shutdown()
        server.server_close()


def test_browser_policy_origin_uses_bytes_and_exposes_conflicting_source(served, browser):
    root, server = served
    item = _checkpoint(root, 'first')
    _telemetry(root, 2, state='done', checkpoints=[item])
    playback = _playback_run(root, 'quince', source='first', revision=REVISION_A)
    _rewrite_record(playback, policy={'sha256': item['sha256']})
    page = browser.page(server.url)
    page.evaluate('window.cadexReview.ready', await_promise=True)
    page.click("#views li[data-run='quince']")
    page.wait_for("document.getElementById('policy-origin').dataset.state === 'resolved'")
    assert page.attribute('#policy-origin', 'data-run') == 'first'
    assert page.attribute('#policy-origin', 'data-source-agrees') == 'true'
    assert 'first · checkpoint · iteration 2' in page.text('#policy-origin')
    # A changed declaration must not replace the byte-resolved origin.
    _rewrite_record(playback, training={'requested': {'source_run': 'second'}, 'receipt': {}})
    page.evaluate('window.cadexReview.refresh()', await_promise=True)
    page.wait_for("document.getElementById('policy-origin').dataset.sourceAgrees === 'false'")
    assert page.attribute('#policy-origin', 'data-run') == 'first'
    assert page.attribute('#policy-origin', 'data-tone') == 'bad'
    assert 'SOURCE-NAME DISAGREEMENT' in page.text('#policy-origin')
    assert 'declared source: second' in page.text('#policy-origin')
    assert page.text('#view-relation').startswith('HISTORICAL')
    # Ordinary polls do not hash the files again; the labelled snapshot has
    # an explicit refresh for a changed/missing retained file.
    (root / 'runs/first/train' / item['path']).unlink()
    page.evaluate('window.cadexReview.refresh()', await_promise=True)
    assert page.attribute('#policy-origin', 'data-state') == 'resolved'
    page.click('#check-policy-origin')
    page.wait_for("document.getElementById('policy-origin').dataset.state === 'unresolved'")
    assert 'no run in this project retains' in page.text('#policy-origin')
    assert 'SOURCE-NAME DISAGREEMENT' not in page.text('#policy-origin')
    # Final-policy identification needs no declared source or naming convention.
    policy = _checkpoint(root, 'second', name='weights.bin', payload=b'other final bytes')
    _rewrite_record(root / 'runs/second', policy={'sha256': policy['sha256']})
    page.evaluate('window.cadexReview.refresh()', await_promise=True)
    page.click("#views li[data-run='second']")
    page.wait_for("document.getElementById('policy-origin').dataset.run === 'second'")
    assert 'second · final' in page.text('#policy-origin')
    assert page.attribute('#policy-origin', 'data-source-agrees') == 'null'
    page.evaluate("window.cadexReview.select('accepted')", await_promise=True)
    assert page.attribute('#policy-origin', 'data-state') == 'unselected'
    # An origin request finishing after selection changes cannot overwrite
    # the accepted view; a visible request failure can be retried.
    page.evaluate("""window.originFetch = window.fetch;
      window.fetch = function(url, options) {
        if (url.startsWith('/api/policy-origin/')) return new Promise(function(resolve, reject) {
          window.rejectOrigin = reject;
        });
        return originFetch(url, options);
      };""")
    page.evaluate("window.cadexReview.select('second')", await_promise=True)
    assert page.attribute('#policy-origin', 'data-state') == 'pending'
    page.evaluate("window.cadexReview.select('accepted')", await_promise=True)
    page.evaluate("rejectOrigin(new Error('late failure'))")
    assert page.attribute('#policy-origin', 'data-state') == 'unselected'
    page.evaluate("window.cadexReview.select('second')", await_promise=True)
    page.evaluate("rejectOrigin(new Error('injected unavailable'))")
    page.wait_for("document.getElementById('policy-origin').dataset.state === 'failed'")
    assert 'injected unavailable' in page.text('#policy-origin')
    page.evaluate('window.fetch = originFetch')
    page.click('#check-policy-origin')
    page.wait_for("document.getElementById('policy-origin').dataset.state === 'resolved'")
    assert page.attribute('#policy-origin', 'data-run') == 'second'


@needs_browser
def test_browser_downloads_unicode_video_filename(served, browser):
    root, server = served
    run = root / 'runs' / 'second'
    name = '歩行 résumé.webm'
    payload = b'retained video bytes'
    (run / name).write_bytes(payload)
    _rewrite_record(run, videos=[{
        'path': name, 'sha256': hashlib.sha256(payload).hexdigest(),
        'policy_sha256': 'p' * 64, 'seed': 7, 'sim_seconds': 4.0,
    }])
    page = _open(browser, server.url)
    assert page.text('#view-kind') == 'RUN second'
    download = page.download('#videos a')
    assert download.path.read_bytes() == payload
    assert download.path.name == name


@pytest.mark.parametrize('name', ['résumé.webm', 'clip"quoted.webm', 'clip\r\nX-Injected: yes.webm'])
def test_download_filename_cannot_break_response_headers(served, name):
    from urllib.parse import quote

    root, server = served
    run = root / 'runs' / 'second'
    (run / name).write_bytes(b'retained')
    _rewrite_record(run, videos=[{'path': name}])
    status, headers, body = _get(server.url + 'video/run/second/0?download=1')
    assert status == 200 and body == b'retained'
    assert 'x-injected' not in headers
    disposition = headers['content-disposition']
    assert disposition.isascii()
    assert '\r' not in disposition and '\n' not in disposition
    assert disposition.endswith("filename*=UTF-8''" + quote(name, safe=''))


# -- interrupted downloads (ADR-324) -------------------------------------------

def _large_video_project(tmp_path: Path) -> tuple[Path, bytes]:
    """The review project with a 48 MiB retained video on ``second``: large
    enough that a client closing after the headers leaves the server with
    bytes still to write, which is what an interrupted download is."""

    root = _review_project(tmp_path)
    payload = os.urandom(1 << 20) * 48
    (root / 'runs' / 'second' / 'big.webm').write_bytes(payload)
    _rewrite_record(root / 'runs' / 'second', videos=[{
        'path': 'big.webm', 'sha256': hashlib.sha256(payload).hexdigest(),
        'policy_sha256': 'p' * 64, 'seed': 3, 'sim_seconds': 8.0,
    }])
    return root, payload


def _abort_download(server, path: str) -> int:
    """Start a download, read the response head, then reset the connection —
    what a browser does when its user cancels. Returns the bytes received."""

    host, port = server.server_address[:2]
    with socket.create_connection((host, port), timeout=10) as sock:
        sock.sendall(f'GET {path} HTTP/1.1\r\nHost: review\r\n\r\n'.encode('ascii'))
        received = len(sock.recv(65536))
        time.sleep(0.05)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
    return received


def _wait_for_line(lines: list[str], fragment: str, timeout: float = 10.0) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for line in lines:
            if fragment in line:
                return line
        time.sleep(0.05)
    raise AssertionError(f'no log line containing {fragment!r} within {timeout}s: {lines}')


def test_an_interrupted_download_is_one_log_line_not_a_traceback(tmp_path, capsys) -> None:
    """A client that cancels a download mid-transfer is logged in one line
    naming the bytes it took; the server prints no traceback, the request
    is not mistaken for a completed one, and the next request — whole or
    resumed with a byte range — gets the file (ADR-324)."""

    root, payload = _large_video_project(tmp_path)
    lines: list[str] = []
    server, _thread = serve(root, '127.0.0.1', 0, log=lines.append)
    try:
        received = _abort_download(server, '/video/run/second/0?download=1')
        assert 0 < received < len(payload)
        line = _wait_for_line(lines, 'client closed the connection')
        sent, total = map(int, re.search(r'after (\d+) of (\d+) bytes of big\.webm$', line).groups())
        assert total == len(payload) and 0 <= sent < total
        err = capsys.readouterr().err
        assert 'Traceback' not in err and 'Exception occurred' not in err, err
        assert [entry for entry in lines if 'client closed' in entry] == [line]

        status, headers, body = _get(server.url + 'video/run/second/0?download=1')
        assert status == 200 and body == payload
        assert headers['content-disposition'] == 'attachment; filename="big.webm"'
        resume_from = len(payload) // 2 + 12345
        status, headers, body = _get(server.url + 'video/run/second/0',
                                     {'Range': f'bytes={resume_from}-'})
        assert status == 206 and body == payload[resume_from:]
        assert headers['content-range'] == f'bytes {resume_from}-{len(payload) - 1}/{len(payload)}'
        assert 'Traceback' not in capsys.readouterr().err
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
def test_browser_interrupted_download_leaves_polling_and_a_fresh_download_working(
        tmp_path, browser, capsys) -> None:
    """With the page open and polling, one client cancels the video download
    mid-transfer: the page keeps polling and stays live, the server logs
    one line and no traceback, and a fresh browser download of the same
    video completes byte-identical (ADR-324)."""

    root, payload = _large_video_project(tmp_path)
    lines: list[str] = []
    server, _thread = serve(root, '127.0.0.1', 0, log=lines.append)
    try:
        page = _open(browser, server.url)
        assert page.text('#view-kind') == 'RUN second'
        assert page.attribute('#freshness', 'data-state') == 'live'
        page.evaluate("window.polls=0; window.originalFetch=window.fetch;"
                      "window.fetch=async (...args) => { const response=await originalFetch(...args);"
                      "if(String(args[0]).includes('api/project')) polls++; return response; }")
        received = _abort_download(server, '/video/run/second/0?download=1')
        assert 0 < received < len(payload)
        polls_at_abort = page.evaluate('polls')
        line = _wait_for_line(lines, 'client closed the connection')
        assert line.endswith(f'of {len(payload)} bytes of big.webm')
        # Two automatic polls after the interruption, never refresh() from here.
        page.wait_for(f'polls >= {polls_at_abort + 2}', timeout=15)
        assert page.attribute('#freshness', 'data-state') == 'live'
        assert page.text('#view-kind') == 'RUN second'

        download = page.download('#videos a', timeout=60)
        assert download.received_bytes == download.total_bytes == len(payload)
        assert download.path.name == 'big.webm'
        assert hashlib.sha256(download.path.read_bytes()).hexdigest() == hashlib.sha256(payload).hexdigest()
        err = capsys.readouterr().err
        assert 'Traceback' not in err and 'Exception occurred' not in err, err
        # The page's own <video> element abandons its request once it has
        # seen enough of a file it cannot decode, so the cancelled download
        # is one of possibly several closed connections — each one line.
        closed = [entry for entry in lines if 'client closed' in entry]
        assert line in closed
        assert all(re.search(r'after \d+ of 50331648 bytes of big\.webm$', entry) for entry in closed)
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
def test_browser_cancelled_download_is_logged_once_and_the_next_download_completes(
        tmp_path, browser, capsys) -> None:
    """The cancellation comes from the browser's own download manager this
    time, not a raw socket: with the page's network throttled so the 48 MiB
    video is still arriving, ``Browser.cancelDownload`` stops it part-way.
    The server logs the bytes it had sent in one line and no traceback, the
    page keeps polling, and a fresh unthrottled download of the same video
    completes byte-identical (ADR-324)."""

    root, payload = _large_video_project(tmp_path)
    lines: list[str] = []
    server, _thread = serve(root, '127.0.0.1', 0, log=lines.append)
    try:
        page = _open(browser, server.url)
        assert page.text('#view-kind') == 'RUN second'
        page.evaluate("window.polls=0; window.originalFetch=window.fetch;"
                      "window.fetch=async (...args) => { const response=await originalFetch(...args);"
                      "if(String(args[0]).includes('api/project')) polls++; return response; }")
        directory = browser.download_dir()
        page.send('Browser.setDownloadBehavior', {
            'behavior': 'allow', 'downloadPath': str(directory), 'eventsEnabled': True})
        page.send('Network.enable')
        page.send('Network.emulateNetworkConditions', {
            'offline': False, 'latency': 0, 'downloadThroughput': 4 << 20, 'uploadThroughput': -1})
        page.click('#videos a')
        guid = browser.wait_event('Browser.downloadWillBegin', page.session, timeout=30)['guid']
        partial = browser.wait_event(
            'Browser.downloadProgress', page.session, timeout=60,
            predicate=lambda params: params.get('guid') == guid
            and (params.get('state') != 'inProgress' or params.get('receivedBytes', 0) > 0))
        assert partial['state'] == 'inProgress', partial
        assert 0 < partial['receivedBytes'] < len(payload) == partial['totalBytes']
        page.send('Browser.cancelDownload', {'guid': guid})
        final = browser.wait_event(
            'Browser.downloadProgress', page.session, timeout=30,
            predicate=lambda params: params.get('guid') == guid
            and params.get('state') in ('completed', 'canceled'))
        assert final['state'] == 'canceled', final
        assert final['receivedBytes'] < len(payload)
        page.send('Network.emulateNetworkConditions', {
            'offline': False, 'latency': 0, 'downloadThroughput': -1, 'uploadThroughput': -1})
        polls_at_cancel = page.evaluate('polls')
        line = _wait_for_line(lines, 'client closed the connection')
        sent, total = map(int, re.search(r'after (\d+) of (\d+) bytes of big\.webm$', line).groups())
        assert total == len(payload) and sent < total
        page.wait_for(f'polls >= {polls_at_cancel + 2}', timeout=15)
        assert page.attribute('#freshness', 'data-state') == 'live'

        download = page.download('#videos a', timeout=60)
        assert download.received_bytes == download.total_bytes == len(payload)
        assert hashlib.sha256(download.path.read_bytes()).hexdigest() == hashlib.sha256(payload).hexdigest()
        err = capsys.readouterr().err
        assert 'Traceback' not in err and 'Exception occurred' not in err, err
        closed = [entry for entry in lines if 'client closed' in entry]
        assert line in closed
        assert all(re.search(r'after \d+ of 50331648 bytes of big\.webm$', entry) for entry in closed)
    finally:
        server.shutdown()
        server.server_close()
