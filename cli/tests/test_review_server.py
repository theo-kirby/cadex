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
from pathlib import Path
import shutil
import signal
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest

from cadex_cli.__main__ import main
from cadex_cli.report import EXIT_OK, EXIT_USAGE
from cadex_cli.review_record import RUN_RECORD_FILENAME, read_run_record, write_run_record
from cadex_cli.review_server import (
    REVIEW_MODEL_SCHEMA,
    accepted_model,
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
                  status: str = "running", error: str | None = None) -> Path:
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
    # A staging directory under another revision is never shown as the accepted model.
    _stage_accepted(root, REVISION_B, staging_revision=REVISION_A)
    model = _json(server.url + "api/model/accepted")
    assert model["available"] is False
    assert "does not belong to the accepted revision" in model["reason"]
    assert _get(server.url + "mesh/accepted/torso.stl")[0] == 404


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


def _telemetry(root, iteration=0, **changes):
    data = {"schema": "cadex-training-progress-v1", "state": "training",
            "updated_at": time.time(), "task_sha256": "t" * 64,
            "iteration": iteration, "total": 10, "reward_per_step": iteration + 0.5,
            "loss": 3.0 - iteration, "episode_steps": 12 + iteration,
            "curve": [[i, i + 0.5] for i in range(iteration + 1)],
            "loss_curve": [[i, 3.0-i] for i in range(iteration + 1)],
            "episode_steps_curve": [[i, 12+i] for i in range(iteration + 1)],
            "checkpoints": []}
    data.update(changes)
    path = root / "runs/first/train/progress.json"
    temporary = path.with_suffix('.partial')
    temporary.write_text(json.dumps(data))
    temporary.replace(path)
    return path


def test_telemetry_refuses_escape_mismatch_and_invalid_histories(served):
    root, server = served
    def read():
        return next(r for r in _json(server.url + 'api/project')['runs'] if r['run'] == 'first')['telemetry']
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
