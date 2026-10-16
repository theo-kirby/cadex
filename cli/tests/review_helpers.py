# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Helpers the kept dashboard and HTTP API tests share (ADR-725).

Extracted from the test modules the suite pruning deleted; nothing here is
collected as a test.
"""
from __future__ import annotations

from cadex_cli.review_record import DOC_SNAPSHOT_LIMIT_BYTES, DOC_SNAPSHOT_LIMIT_FILES, PROJECT_REVIEW_SCHEMA, RUN_RECORD_FILENAME, RUN_RECORD_SCHEMA, _retained_policies, _retained_progress, list_runs, manifest_identity, policy_lineage, read_accepted_identity, read_project_review, read_run_record, resolve_reference, snapshot_project_docs, write_run_record
from cadex_cli.review_record import RUN_RECORD_FILENAME, read_run_record, write_run_record
from cadex_cli.review_record import write_run_record
from cadex_cli.review_server import CHECKPOINTS_LISTED, TRACE_SCHEMA, serve
from cadex_cli.revision_meshes import INDEX_NAME, NOT_RETAINED, PARTS_DIR, SCHEMA, revision_model, store_root
from cdp_browser import HeadlessBrowser, find_browser
from pathlib import Path
import hashlib
import json
import os
import pytest
import shutil
import struct
import time
import urllib.request

# from test_review_reference.py
DT, SAMPLES, STRIDE_MM = 0.1, 4, 200.0


# from test_review_server.py
TRACE_SCHEMA = "cadex-assembly-simulation-trace-v1"


# from test_review_server.py
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


# from test_review_server.py
BROWSER = find_browser()


# from test_review_server.py
needs_browser = pytest.mark.skipif(BROWSER is None, reason="no Chromium found (set CADEX_BROWSER)")


# from test_review_server.py
MODEL_SETTLED = ("['loaded','missing','error'].includes("
                 "document.getElementById('model-status').dataset.state)")


# from test_review_checkpoints.py
RUN = "orun3-biped-train"


# from test_review_checkpoints.py
DIGEST = "d" * 64


# from test_review_record.py
REVISION_A = "a" * 64


# from test_review_record.py
REVISION_B = "b" * 64


# from test_review_record.py
POLICY_SHA256 = hashlib.sha256(b"policy").hexdigest()


# from test_review_revisions.py
PLACED = {"position_mm": [0.0, 0.0, 0.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}


# from test_checkpoint_rollouts.py
BIPED = Path(__file__).parent / "fixtures" / "orun3-biped"


# from test_checkpoint_rollouts.py
MODEL = "reed_model-model.xml"


# from test_checkpoint_rollouts.py
TASK = "reed_walk-task.json"


# from test_checkpoint_rollouts.py
LINKS = ["ground_link", "torso_link", "thigh_l_link", "shin_l_link", "foot_l_link",
         "thigh_r_link", "shin_r_link", "foot_r_link"]


# from test_app.py
def _projects(tmp_path: Path) -> Path:
    """``biped`` (accepted at B, three runs), ``empty`` (a manifest, nothing
    accepted), and two directories that are not projects."""

    projects = tmp_path / "projects"
    projects.mkdir()
    _review_project(projects)
    empty = projects / "empty"
    empty.mkdir()
    (empty / "script.json").write_text("{}")
    (projects / "notes").mkdir()
    (projects / ".cache").mkdir()
    (projects / ".cache" / "script.json").write_text("{}")
    return projects


# from test_review_server.py
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


# from test_review_server.py
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


# from test_review_server.py
def _trace(placements: dict[str, list[float]]) -> str:
    return json.dumps({
        "schema": TRACE_SCHEMA, "component_outputs": list(placements),
        "frames": [{"frame_index": 0, "frame_kind": "input", "component_placements": {
            name: {"position_mm": position, "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}
            for name, position in placements.items()}}],
    })


# from test_review_server.py
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


# from test_review_server.py
def _rewrite_record(run: Path, **changes) -> None:
    path = run / RUN_RECORD_FILENAME
    record = json.loads(path.read_text())
    for key, value in changes.items():
        record[key] = value
    path.write_text(json.dumps(record, indent=2))


# from test_review_server.py
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


# from test_review_server.py
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


# from test_review_server.py
def _get(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read()
    except urllib.error.HTTPError as error:
        return error.code, {k.lower(): v for k, v in error.headers.items()}, error.read()


# from test_review_server.py
def _json(url: str):
    status, _headers, body = _get(url)
    assert status == 200, (status, body[:200])
    return json.loads(body)


# from test_review_server.py
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


# from test_review_server.py
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
                                  "mesh": f"mesh/run/{name}/leaked.stl",
                                  "sha256": hashlib.sha256(stl.read_bytes()).hexdigest(),
                                  "placement": None}]}}))
    (outside / "run.json").write_text(json.dumps({"schema": "cadex-run-record-v1", "run": name}))
    (root / "runs" / name).symlink_to(outside, target_is_directory=True)
    return outside


# from test_review_server.py
@pytest.fixture(scope="module")
def browser():
    if BROWSER is None:
        pytest.skip("no Chromium found (set CADEX_BROWSER)")
    with HeadlessBrowser(BROWSER) as instance:
        yield instance


# from test_review_server.py
def _open(browser: HeadlessBrowser, url: str):
    page = browser.page(url)
    page.evaluate("window.cadexReview.ready", await_promise=True)
    return page


# from test_review_server.py
def _model_state(page) -> str:
    page.wait_for(MODEL_SETTLED)
    return page.attribute("#model-status", "data-state")


# from test_review_checkpoints.py
def _checkpoint_training_run(root: Path) -> Path:
    """A biped walk at its train leg: running, its assembled model frozen
    before training as ``training-view.json``, its links named as the
    checkpoint traces name them."""

    run = root / "runs" / RUN
    train = run / "train"
    train.mkdir(parents=True)
    for name in (MODEL, TASK):
        shutil.copyfile(BIPED / name, train / name)
    write_run_record(run, project_root=root, status="running", mode="blocking",
                     accepted_revision=REVISION_B, digest=DIGEST,
                     requested={"iterations": 60, "seed": 7})
    (run / "training-view").mkdir()
    components = []
    for index, link in enumerate(LINKS):
        output = link[:-len("_link")]
        mesh = run / "training-view" / f"{output}.stl"
        mesh.write_text(_cube_stl(10.0 + index))
        components.append({
            "name": link, "output": output, "mesh": f"mesh/run/{RUN}/{output}.stl",
            "mesh_status": "retained", "sha256": hashlib.sha256(mesh.read_bytes()).hexdigest(),
            "placement": {"position_mm": [0.0, 0.0, 30.0 * index], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]},
            "placement_source": "accepted assembly placement"})
    (run / "training-view.json").write_text(json.dumps({
        "schema": "cadex-training-view-v1", "model": {
            "revision": REVISION_B, "digest": DIGEST, "available": True, "reason": "",
            "placement_source": "accepted assembly placement", "components": components}}))
    _progress(train, 0, [])
    return run


# from test_review_checkpoints.py
def _progress(train: Path, iteration: int, rows: list[dict], *, state: str = "training") -> None:
    payload = {"schema": "cadex-training-progress-v1", "state": state, "iteration": iteration,
               "total": 60, "updated_at": time.time(), "curve": [], "loss_curve": [],
               "episode_steps_curve": [], "checkpoints": rows, "error": "", "warning": ""}
    (train / "progress.json.partial").write_text(json.dumps(payload))
    (train / "progress.json.partial").replace(train / "progress.json")


# from test_review_checkpoints.py
def _checkpoint_trace(tag: str, iteration: int, reward: float, frames: int = 3) -> dict:
    return {
        "schema": TRACE_SCHEMA, "simulation_output": "checkpoint", "component_outputs": ["torso_link"],
        "parameters": {"frames_per_second": 25},
        "checkpoint": {"file": f"walk.{tag}.cxpolicy", "tag": tag, "iteration": iteration,
                       "reward_per_step": reward, "sha256": tag * 10},
        "frames": [{"frame_kind": "input", "component_placements": {
            "torso_link": {"position_mm": [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]}}}] + [
            {"nominal_time_s": i * 0.04, "component_placements": {
                "torso_link": {"position_mm": [i, 0, 0], "rotation_xyzw": [0, 0, 0, 1]}}}
            for i in range(frames)]}


# from test_review_evaluation.py
def _passing(root: Path, name: str = "steady", *, revision: str = REVISION_A) -> Path:
    directory = root / "evaluations" / name
    directory.mkdir(parents=True)
    seeds = []
    for seed, tilt in ((11, 3.5), (12, 4.25)):
        seeds.append({
            "seed": seed, "pass": True, "void": "", "failing": [],
            "predicates": [{"id": "upright", "metric": "max_tilt_deg", "value": tilt, "min": None,
                            "max": 30.0, "pass": True, "why": ""}],
            "metrics": {"completed": 1.0, "max_tilt_deg": tilt},
            "episode": {"steps": 200, "duration_s": 4.0, "termination": "", "truncated": True},
            "reward": {"total": 8.0, "terms": [{"label": "alive", "per_step": 0.04, "total": 8.0}]},
            "drawn": {"disturbance": []}, "trace": {"file": f"seed-{seed}-trace.json"}})
    (directory / "evaluation.json").write_text(json.dumps({
        "schema": "cadex-evaluation-v1", "verdict": "pass", "accepted_revision": revision,
        "policy_output": "hold", "policy_sha256": "9" * 64, "task_output": "stand", "task_label": "stand",
        "seeds": seeds,
        "summary": {"pass": True, "seeds": 2, "passed": [11, 12], "failed": [], "void": [],
                    "terminations": {"horizon": 2},
                    "predicates": [{"id": "upright", "metric": "max_tilt_deg", "min": None, "max": 30.0,
                                    "passed": 2, "failed_seeds": [],
                                    "value": {"min": 3.5, "median": 3.875, "max": 4.25}}]}}))
    # Older than the shuffle's, whatever order the fixtures were written in.
    os.utime(directory / "evaluation.json", (1_000_000_000, 1_000_000_000))
    return directory


# from test_review_record.py
def _manifest(root: Path, revision: str, digest: str = "d" * 64) -> None:
    (root / "script.json").write_text(json.dumps({
        "schema": "cadex-project-script-v1",
        "accepted_revision": revision, "accepted_digest": digest,
        "working_revision": revision, "updated_at": "2026-09-12T00:00:00Z",
        "param_specs": [{"name": "leg_len", "default": 80.0}],
        "param_values": {"leg_len": 90.0},
    }))


# from test_review_record.py
def _project(tmp_path: Path) -> Path:
    root = tmp_path / "biped"
    root.mkdir()
    (root / "script.py").write_text("# script\n")
    (root / "ARCHITECTURE.md").write_text("# biped — Architecture\n")
    (root / "DECISIONS.md").write_text(
        "# biped — Decisions\n\n## ADR-001 — Project scaffolded (2026-09-12)\n\n"
        "## ADR-002 — Longer shins (2026-09-12)\n"
    )
    (root / "PROGRESS.md").write_text("# biped — Progress\n")
    (root / "docs").mkdir()
    (root / "docs" / "actuators.md").write_text("# Actuators\n")
    (root / "assets").mkdir()
    (root / "assets" / "gait.cxpolicy").write_bytes(b"policy")
    return root


# from test_review_record.py
def _walked_run(root: Path, name: str, *, revision: str, status: str = "ok",
                policy: str = "gait.cxpolicy") -> Path:
    """A run directory with the files a walk leaves, then its record."""

    run = root / "runs" / name
    (run / "train").mkdir(parents=True)
    (run / "rollout").mkdir()
    (run / "script.py").write_text("# declared\n")
    (run / "review.json").write_text("{}\n")
    (run / "train" / "gait-task.json").write_text("{}")
    (run / "train" / "rig-model.xml").write_text("<mujoco/>")
    (run / "train" / "progress.json").write_text("{}")
    (run / "rollout" / "assembly-simulation-trace.json").write_text("{}")
    render = root / "review" / "render" / revision
    render.mkdir(parents=True)
    (render / "summary.json").write_text("{}")
    (root / "docs" / "inventory.md").write_text("# Inventory\n")
    write_run_record(
        run, project_root=root, status=status, mode="blocking",
        legs=[{"leg": "rollout", "exit": 0, "seconds": 1.0, "argv": ["never"],
               "accepted_revision": revision, "digest": "d" * 64}],
        accepted_revision=revision, digest="d" * 64,
        params={"leg_len": 90.0}, param_specs=[{"name": "leg_len", "default": 80.0}],
        specs_source="test", training={"reward_per_step": 0.3, "device": "gpu",
                                        "sha256": POLICY_SHA256, "ignored": "no"},
        requested={"iterations": 10, "seed": 3}, policy_name=policy,
        policy_sha256=POLICY_SHA256, task_bundle=run / "train" / "gait-task.json",
        task_sha256="t" * 64, model_xml=run / "train" / "rig-model.xml",
        trace=run / "rollout" / "assembly-simulation-trace.json",
        review={"render": {"path": f"review/render/{revision}"},
                "inventory": {"path": "docs/inventory.md"},
                "rollout_seed": 7, "total_reward": 12.5},
        walk_seconds=3.456, snapshot_docs=True,
    )
    return run


# from test_review_revisions.py
def _tess(scale: float) -> tuple[str, bytes, bytes]:
    """One triangle as a ``cadex-tessellation-v1`` buffer and its sidecar."""

    import struct
    vertices = struct.pack("<9f", 0, 0, 0, scale, 0, 0, 0, scale, 0)
    triangles = struct.pack("<3I", 0, 1, 2)
    data = vertices + triangles
    sha = hashlib.sha256(data).hexdigest()
    sidecar = {"schema": "cadex-tessellation-v1", "byte_order": "little", "artifact_path": f"{sha}.tess.bin",
               "counts": {"vertices": 3, "triangles": 1},
               "layout": {"vertices": {"dtype": "f32", "offset": 0, "bytes": len(vertices)},
                          "triangles": {"dtype": "u32", "offset": len(vertices), "bytes": len(triangles)}}}
    return sha, data, json.dumps(sidecar).encode()


# from test_review_revisions.py
def _biped_store(root: Path) -> dict[str, str]:
    """A four-revision biped trail: 1 not retained, 2 to 4 retained, the
    foot changing at 3 and the torso moving (not changing) at 4."""

    revisions = [c * 64 for c in "abcd"]
    trail = root / "script_history"
    trail.mkdir(parents=True)
    (trail / "history.json").write_text(json.dumps({"entries": [
        {"ordinal": n, "revision": rev, "file": f"{n:04d}.py", "saved_at": f"2026-10-05T10:0{n}:00Z"}
        for n, rev in enumerate(revisions, start=1)]}))
    parts = store_root(root) / PARTS_DIR
    parts.mkdir(parents=True)
    shas = {}
    for name, scale in (("torso", 60.0), ("foot_a", 40.0), ("foot_b", 70.0)):
        sha, data, sidecar = _tess(scale)
        (parts / f"{sha}.tess.bin").write_bytes(data)
        (parts / f"{sha}.tess.json").write_bytes(sidecar)
        shas[name] = sha

    def row(n: int, foot: str, torso_z: float) -> dict:
        moved = {"position_mm": [0.0, 0.0, torso_z], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}
        return {"ordinal": n, "revision": revisions[n - 1], "digest": f"d{n}",
                "parts": {"torso": {"sha256": shas["torso"]}, "foot_l": {"sha256": shas[foot]}},
                "components": [{"name": "torso", "output": "torso", "placement": moved},
                               {"name": "foot_l", "output": "foot_l", "placement": PLACED}]}

    (store_root(root) / INDEX_NAME).write_text(json.dumps({"schema": SCHEMA, "revisions": {
        "2": row(2, "foot_a", 0.0), "3": row(3, "foot_b", 0.0), "4": row(4, "foot_b", 5.0)}}))
    return shas


# from test_review_reference.py
def reference_bundle(staging: Path, task: str = "walk", *, reference: bool = True) -> Path:
    """A task bundle in the accepted attempt, with (or without) a gait reference."""

    bundle = {"schema": "cadex-training-task-v1", "label": task}
    if reference:
        bundle["reference"] = {
            "schema": "cadex-gait-clip-v1", "gait": "trot", "label": "cruise",
            "samples": SAMPLES, "sample_dt_s": DT,
            "parameters": {"speed_m_s": 0.5, "stride_length_m": STRIDE_MM / 1000.0,
                           "stride_frequency_hz": 2.5, "period_s": DT * SAMPLES, "duty_factor": 0.45,
                           "phase_offsets": {"LH": 0.0, "RF": 0.0, "RH": 0.5, "LF": 0.5},
                           "froude": 0.06, "hip_height_m": 0.4, "swing_height_m": 0.03},
            "contact": {"LF": [0, 0, 1, 1], "RF": [1, 1, 0, 0], "LH": [1, 1, 0, 0], "RH": [0, 0, 1, 1]},
            # the second sample's quaternion is the first's with its sign flipped
            "placements": [{"body": {"position_mm": [50.0 * k, 0.0, 10.0],
                                     "rotation_xyzw": [0.0, 0.0, 0.0, -1.0 if k == 1 else 1.0]}}
                           for k in range(SAMPLES)],
        }
    path = staging / "outputs" / f"{task}-task.json"
    path.write_text(json.dumps(bundle))
    return path
