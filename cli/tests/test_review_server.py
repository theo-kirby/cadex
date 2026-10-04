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


# Collision proxies that DIFFER from the solids they stand for: the torso cube
# spans 0..20 mm, its box proxy -20..40 mm; the leg cube is 8 mm, its capsule
# 40 mm long and laid along Y; the sphere takes part in no contact and is not a
# proxy at all. Bodies are named as the trace's components are.
PROXY_MJCF = """<mujoco model="fixture">
  <worldbody>
    <body name="body" pos="0 0 0">
      <geom name="body/collision0" type="box" size="0.03 0.03 0.03" pos="0.01 0.01 0.01"/>
      <body name="shin" pos="0 0 -0.04">
        <geom name="shin/collision0" type="capsule" size="0.006 0.02" quat="0.7071068 0.7071068 0 0"/>
        <geom name="shin/visual" type="sphere" size="0.05" contype="0" conaffinity="0"/>
      </body>
    </body>
  </worldbody>
</mujoco>
"""


def _mesh_run(root: Path, name: str, *, revision: str) -> Path:
    """A walked run that retained its rollout meshes: body←torso, shin←leg."""

    # Two runs at one revision share a render directory; the helper makes it.
    shutil.rmtree(root / "review" / "render" / revision, ignore_errors=True)
    run = _walked_run(root, name, revision=revision)
    (run / "train" / "rig-model.xml").write_text(PROXY_MJCF)
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
    (staging / "outputs" / "rig-model.xml").write_text(PROXY_MJCF)
    (staging / "result.json").write_text(json.dumps({
        "ok": True, "schema": "cadex-xscript-project-worker-v1",
        "component_sources": {"src-1": "torso"},
        "outputs": [
            {"name": "torso", "type": "solid", "artifact_kind": "brep", "artifact_path": "outputs/output-000.brep"},
            {"name": "rig", "type": "mjcf", "artifact_kind": "assembly_mjcf_xml", "artifact_path": "outputs/rig-model.xml"},
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


def test_collision_proxies_come_from_the_retained_mjcf_at_the_same_identity(served) -> None:
    """D4 (ADR-333): the proxies a view offers are parsed from the MJCF the run
    (or the accepted attempt) retained, in the component's frame, in mm and
    xyzw, and refused when the rollout's own receipt names another model."""

    root, server = served
    model = _json(server.url + "api/model/run/first")
    collision = model["collision"]
    assert collision["available"] is True and collision["skipped"] == 1
    assert collision["source"].startswith("runs/first/train/rig-model.xml")
    assert collision["sha256"] == hashlib.sha256(PROXY_MJCF.encode()).hexdigest()
    assert collision["components"] == ["body", "shin"]
    box, capsule = collision["geoms"]
    assert box["component"] == "body" and box["type"] == "box" and box["drawn"] is True
    assert box["size_mm"] == [30.0, 30.0, 30.0] and box["pos_mm"] == [10.0, 10.0, 10.0]
    assert box["rotation_xyzw"] == [0.0, 0.0, 0.0, 1.0]
    assert capsule["component"] == "shin" and capsule["type"] == "capsule"
    assert capsule["size_mm"] == [6.0, 20.0] and capsule["pos_mm"] == [0.0, 0.0, 0.0]
    assert capsule["rotation_xyzw"] == pytest.approx([0.7071068, 0.0, 0.0, 0.7071068])
    # A fromto capsule, an inline mesh, a plane and a bad size are each said plainly.
    (root / "runs" / "first" / "train" / "rig-model.xml").write_text("""<mujoco>
      <asset><mesh name="hull" vertex="0 0 0 0.01 0 0 0 0.01 0 0 0 0.01" face="0 1 2 0 2 3 0 3 1 1 3 2"/></asset>
      <worldbody><body name="body">
        <geom type="capsule" size="0.005" fromto="0 0 0 0 0 0.05"/>
        <geom type="mesh" mesh="hull"/>
        <geom type="plane" size="0 0 0.1"/>
        <geom type="box" size="0 0.01 0.01"/>
      </body></worldbody></mujoco>""")
    geoms = _json(server.url + "api/model/run/first")["collision"]["geoms"]
    assert [g["type"] for g in geoms] == ["capsule", "mesh", "plane", "box"]
    assert geoms[0]["pos_mm"] == [0.0, 0.0, 25.0] and geoms[0]["size_mm"] == [5.0, 25.0]
    assert geoms[0]["rotation_xyzw"] == [0.0, 0.0, 0.0, 1.0] and geoms[0]["drawn"]
    assert geoms[1]["drawn"] and len(geoms[1]["vertices_mm"]) == 12 and geoms[1]["faces"] == [0, 1, 2, 0, 2, 3, 0, 3, 1, 1, 3, 2]
    assert geoms[2]["drawn"] is False and "plane" in geoms[2]["note"]
    assert geoms[3]["drawn"] is False and geoms[3]["note"] == "invalid size"
    # The trace's policy receipt names the model it ran: another file is refused.
    trace_path = root / "runs" / "first" / "rollout" / "assembly-simulation-trace.json"
    trace = json.loads(trace_path.read_text())
    trace["policy"] = {"model_sha256": "0" * 64}
    trace_path.write_text(json.dumps(trace))
    collision = _json(server.url + "api/model/run/first")["collision"]
    assert collision["available"] is False and "digest mismatch" in collision["reason"]
    assert collision["geoms"] == []
    # No model, no proxies; a missing export says so.
    assert _json(server.url + "api/model/run/broken")["collision"]["available"] is False
    (root / "runs" / "second" / "train" / "rig-model.xml").unlink()
    collision = _json(server.url + "api/model/run/second")["collision"]
    assert collision["available"] is False and collision["reason"].startswith("MJCF export missing")
    # The accepted view reads the accepted attempt's own assembly.mjcf output.
    assert _json(server.url + "api/model/accepted")["collision"]["reason"] == "no model to show"
    _stage_accepted(root, REVISION_B)
    collision = _json(server.url + "api/model/accepted")["collision"]
    assert collision["available"] is True and collision["source"].startswith("the accepted attempt's rig")
    assert [g["component"] for g in collision["geoms"]] == ["body", "shin"]


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


def test_an_accepted_mesh_is_tagged_by_content_compressed_and_revalidated(served, monkeypatch) -> None:
    """A mesh carries its tessellation's content hash as its ETag and is
    revalidated, not refetched: a matching If-None-Match is 304 with no body.
    A client that accepts gzip gets the same bytes compressed; one that does
    not gets them plain. The manifest it is read from is remembered and is
    rebuilt when the manifest changes."""

    import gzip
    from cadex_cli import review_server
    root, server = served
    monkeypatch.setattr(review_server, "GZIP_MIN_BYTES", 0)  # the fixture's mesh is 684 bytes
    _stage_accepted(root, REVISION_B)
    status, headers, plain = _get(server.url + "mesh/accepted/torso.stl")
    assert status == 200 and "content-encoding" not in headers
    assert headers["cache-control"] == "no-cache" and headers["etag"].startswith('"')
    status, packed_headers, packed = _get(server.url + "mesh/accepted/torso.stl", {"Accept-Encoding": "gzip"})
    assert status == 200 and packed_headers["content-encoding"] == "gzip" and gzip.decompress(packed) == plain
    assert packed_headers["etag"] == headers["etag"]
    status, _h, body = _get(server.url + "mesh/accepted/torso.stl", {"If-None-Match": headers["etag"]})
    assert status == 304 and body == b""
    status, _h, body = _get(server.url + "mesh/accepted/torso.stl", {"If-None-Match": '"stale"'})
    assert status == 200 and body == plain
    first = _json(server.url + "api/model/accepted")
    assert _json(server.url + "api/model/accepted") == first
    manifest = json.loads((root / "script.json").read_text())
    manifest.pop("accepted_attempt")
    (root / "script.json").write_text(json.dumps(manifest))
    assert _json(server.url + "api/model/accepted")["available"] is False


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
def test_browser_orbit_and_zoom_move_the_camera_over_a_drawn_model(tmp_path, browser) -> None:
    root = _review_project(tmp_path)
    _stage_accepted(root, REVISION_B)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        _orbit_and_zoom(browser, server)
    finally:
        server.shutdown()
        server.server_close()


def _orbit_and_zoom(browser, server) -> None:
    page = _open(browser, server.url)
    assert _model_state(page) == "loaded"
    stats = page.evaluate("window.cadexReview.viewer().stats()")
    assert stats["components"] == 1 and stats["triangles"] == 12
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
    # Fit frames the model for the canvas's shape (a narrow stage frames by
    # its horizontal field of view), so take the reference framing at this size.
    page.click("#model-fit")
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


@needs_browser
def test_browser_draws_the_accepted_attempt_and_labels_a_lost_server_stale(tmp_path, browser) -> None:
    root = _review_project(tmp_path)
    _stage_accepted(root, REVISION_B)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        assert _model_state(page) == "loaded"
        assert page.text("#model-status") == ""  # a drawn model needs no caption
        assert page.evaluate("window.cadexReview.viewer().stats()")["triangles"] == 12
        assert page.evaluate("window.cadexReview.viewer().nonBackgroundPixels()") > 1000
        assert page.attribute("#freshness", "data-state") == "live"
        line = page.text("#accepted-line")
    finally:
        server.shutdown()
        server.server_close()
    page.evaluate("window.cadexReview.refresh()", await_promise=True)
    assert page.attribute("#freshness", "data-state") == "stale"
    assert page.text("#freshness") == "offline"
    assert page.evaluate("window.cadexReview.state().stale") is True
    # What was on screen stays: the last good identity and model, not a blank page.
    assert page.text("#accepted-line") == line and line.startswith("revision ")
    assert page.evaluate("window.cadexReview.viewer().nonBackgroundPixels()") > 1000


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
        assert page.text("#project-name") == "fresh-biped"
        assert page.text("#accepted-line") == "nothing accepted yet"
        assert _model_state(page) == "missing"
        assert page.text("#model-status").startswith("no model: ")
        assert page.evaluate("document.querySelectorAll('#revision-list li').length") == 0
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
        assert page.evaluate('window.cadexReview.state().revision') == REVISION_A
        page.wait_for("window.cadexReview.state().model && window.cadexReview.state().model.revision === %s"
                      % json.dumps(REVISION_A))
        assert _model_state(page) == 'loaded'
        assert page.evaluate('window.cadexReview.viewer().stats().bounds.max[0]') == 45.0
        # Identical polls must preserve deliberate orbit/zoom.
        page.evaluate('const viewer = window.cadexReview.viewer(); const camera = viewer.camera(); camera.yaw += .3; camera.distance *= 1.2; viewer.setCamera(camera); window.cameraBefore = viewer.camera()')
        page.evaluate('window.cadexReview.refresh()', await_promise=True)
        assert page.evaluate('JSON.stringify(cameraBefore) === JSON.stringify(window.cadexReview.viewer().camera())')
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
        assert page.evaluate('window.cadexReview.viewer().stats()')['components'] == 2
        assert page.evaluate('window.cadexReview.state().revision') == accepted
        assert page.evaluate('window.cadexReview.viewer().nonBackgroundPixels()') > 1000
    finally:
        server.shutdown()
        server.server_close()


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
