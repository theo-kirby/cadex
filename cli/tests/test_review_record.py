# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The run record and the project review reader (ADR-285).

No engine and no walk: the writer is driven directly with what a walk
holds, and the reader against directories laid out by hand, including the
ones a walk never writes — a run whose files were deleted, a record that
points outside its project, a project from before records existed.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil

import pytest

from cadex_cli.review_record import (
    DOC_SNAPSHOT_LIMIT_BYTES,
    DOC_SNAPSHOT_LIMIT_FILES,
    PROJECT_REVIEW_SCHEMA,
    RUN_RECORD_FILENAME,
    RUN_RECORD_SCHEMA,
    list_runs,
    manifest_identity,
    policy_lineage,
    read_accepted_identity,
    read_project_review,
    read_run_record,
    resolve_reference,
    snapshot_project_docs,
    write_run_record,
)

REVISION_A = "a" * 64
REVISION_B = "b" * 64


def _manifest(root: Path, revision: str, digest: str = "d" * 64) -> None:
    (root / "script.json").write_text(json.dumps({
        "schema": "cadex-project-script-v1",
        "accepted_revision": revision, "accepted_digest": digest,
        "working_revision": revision, "updated_at": "2026-09-12T00:00:00Z",
        "param_specs": [{"name": "leg_len", "default": 80.0}],
        "param_values": {"leg_len": 90.0},
    }))


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
                                        "sha256": "p" * 64, "ignored": "no"},
        requested={"iterations": 10, "seed": 3}, policy_name=policy,
        policy_sha256="p" * 64, task_bundle=run / "train" / "gait-task.json",
        task_sha256="t" * 64, model_xml=run / "train" / "rig-model.xml",
        trace=run / "rollout" / "assembly-simulation-trace.json",
        review={"render": {"path": f"review/render/{revision}"},
                "inventory": {"path": "docs/inventory.md"},
                "rollout_seed": 7, "total_reward": 12.5},
        walk_seconds=3.456, snapshot_docs=True,
    )
    return run


# -- the writer ---------------------------------------------------------------


def test_the_record_carries_identities_and_only_relative_paths(tmp_path) -> None:
    root = _project(tmp_path)
    run = _walked_run(root, "run-1", revision=REVISION_A)
    text = (run / RUN_RECORD_FILENAME).read_text()
    assert str(tmp_path) not in text
    record = json.loads(text)
    assert record["schema"] == RUN_RECORD_SCHEMA and record["run"] == "run-1"
    assert record["status"] == "ok" and record["walk_seconds"] == 3.46
    assert record["model"]["accepted_revision"] == REVISION_A
    assert record["params"] == {"values": {"leg_len": 90.0},
                                "specs": [{"name": "leg_len", "default": 80.0}],
                                "specs_source": "test"}
    assert record["task"] == {"bundle": "train/gait-task.json", "sha256": "t" * 64,
                              "model_xml": "train/rig-model.xml"}
    assert record["training"]["requested"] == {"iterations": 10, "seed": 3}
    # The receipt is the trainer's named figures, not everything it said.
    assert record["training"]["receipt"] == {"reward_per_step": 0.3, "device": "gpu",
                                             "sha256": "p" * 64}
    assert record["policy"] == {"name": "gait.cxpolicy", "sha256": "p" * 64,
                                "asset": "assets/gait.cxpolicy"}
    assert record["rollout"] == {"trace": "rollout/assembly-simulation-trace.json",
                                 "seed": 7, "total_reward": 12.5}
    assert record["artifacts"]["progress"] == "train/progress.json"
    assert record["artifacts"]["receipt"] is None
    assert record["project_artifacts"]["render"] == f"review/render/{REVISION_A}"
    assert record["project_artifacts"]["section"] is None
    assert record["videos"] == []
    assert record["legs"] == [{"leg": "rollout", "exit": 0, "seconds": 1.0,
                               "accepted_revision": REVISION_A, "digest": "d" * 64}]


def test_a_reference_outside_both_bases_is_null_not_absolute(tmp_path) -> None:
    root = _project(tmp_path)
    elsewhere = tmp_path / "elsewhere" / "trace.json"
    elsewhere.parent.mkdir()
    elsewhere.write_text("{}")
    run = root / "runs" / "run-x"
    write_run_record(run, project_root=root, status="ok", mode="blocking",
                     trace=elsewhere, task_bundle=elsewhere, model_xml=elsewhere)
    record = json.loads((run / RUN_RECORD_FILENAME).read_text())
    assert record["artifacts"]["trace"] is None
    assert record["task"] == {"bundle": None, "sha256": None, "model_xml": None}
    assert str(elsewhere) not in (run / RUN_RECORD_FILENAME).read_text()


def test_a_running_record_claims_nothing_and_is_rewritten_whole(tmp_path) -> None:
    root = _project(tmp_path)
    run = root / "runs" / "run-2"
    write_run_record(run, project_root=root, status="running", mode="detach")
    record = json.loads((run / RUN_RECORD_FILENAME).read_text())
    assert record["status"] == "running" and record["error"] is None
    assert record["model"]["identity_source"] == "not reached"
    assert record["params"] == {"values": {}, "specs": None, "specs_source": "unavailable"}
    assert record["project_docs"]["dir"] is None
    assert record["project_docs"]["note"] == "not snapshotted"
    # A later write replaces the file rather than merging into it.
    write_run_record(run, project_root=root, status="failed", mode="detach",
                     error="the box went away")
    record = json.loads((run / RUN_RECORD_FILENAME).read_text())
    assert record["status"] == "failed" and record["error"] == "the box went away"
    with pytest.raises(ValueError):
        write_run_record(run, project_root=root, status="done", mode="detach")


# -- the document snapshot ----------------------------------------------------


def test_the_manifest_names_the_training_input_before_any_leg_runs(tmp_path) -> None:
    """What a walk can claim before its first leg: the manifest's revision,
    digest and specs, labelled with the moment they were read; nothing at
    all, with the reason, when there is no manifest."""

    root = _project(tmp_path)
    assert manifest_identity(root, "at walk start") == {
        "accepted_revision": "", "digest": "", "identity_source": "", "param_specs": None,
        "specs_source": "unavailable: project manifest at walk start: no script.json",
    }
    _manifest(root, REVISION_A)
    fields = manifest_identity(root, "at walk start")
    assert fields == {
        "accepted_revision": REVISION_A, "digest": "d" * 64,
        "identity_source": "project manifest (script.json) at walk start",
        "param_specs": [{"name": "leg_len", "default": 80.0}],
        "specs_source": "project manifest (script.json) at walk start",
    }
    run = root / "runs" / "training"
    write_run_record(run, project_root=root, status="running", mode="blocking", **fields)
    record = read_run_record(run, root)
    assert record["model"] == {"accepted_revision": REVISION_A, "digest": "d" * 64,
                               "identity_source": "project manifest (script.json) at walk start"}
    assert record["params"] == {"values": {}, "specs": [{"name": "leg_len", "default": 80.0}],
                                "specs_source": "project manifest (script.json) at walk start"}
    assert record["outcome"].startswith("started and never finished")
    reviewed = read_project_review(root)
    assert reviewed["runs"][0]["relation"] == "current"
    # An explicit source wins over the derived one; blank keeps the old rule.
    write_run_record(run, project_root=root, status="failed", mode="blocking",
                     accepted_revision=REVISION_A, digest="d" * 64,
                     identity_source="train leg envelope", error="refused")
    assert read_run_record(run, root)["model"]["identity_source"] == "train leg envelope"
    write_run_record(run, project_root=root, status="failed", mode="blocking",
                     accepted_revision=REVISION_A, digest="d" * 64, error="refused")
    assert read_run_record(run, root)["model"]["identity_source"] == "rollout leg envelope"


def test_the_snapshot_copies_the_project_documents_with_digests(tmp_path) -> None:
    root = _project(tmp_path)
    run = root / "runs" / "run-3"
    run.mkdir(parents=True)
    docs = snapshot_project_docs(root, run)
    assert docs["dir"] == "project-docs" and docs["skipped"] == []
    assert sorted(docs["files"]) == ["ARCHITECTURE.md", "DECISIONS.md", "PROGRESS.md",
                                     "docs/actuators.md"]
    for relative, digest in docs["files"].items():
        copied = run / "project-docs" / relative
        assert copied.read_bytes() == (root / relative).read_bytes()
        assert hashlib.sha256(copied.read_bytes()).hexdigest() == digest
    # The snapshot is what the documents said THEN: editing the project
    # afterwards changes nothing beside the run.
    (root / "DECISIONS.md").write_text("# rewritten\n")
    assert (run / "project-docs" / "DECISIONS.md").read_text().startswith("# biped")


def test_the_snapshot_is_bounded_and_says_what_it_skipped(tmp_path) -> None:
    root = _project(tmp_path)
    (root / "ARCHITECTURE.md").write_bytes(b"x" * (DOC_SNAPSHOT_LIMIT_BYTES + 1))
    for index in range(DOC_SNAPSHOT_LIMIT_FILES + 2):
        (root / "docs" / f"note-{index:02d}.md").write_text("n\n")
    run = root / "runs" / "run-4"
    run.mkdir(parents=True)
    docs = snapshot_project_docs(root, run)
    assert len(docs["files"]) == DOC_SNAPSHOT_LIMIT_FILES
    reasons = {row["reason"] for row in docs["skipped"]}
    assert reasons == {"size bound", "file count bound"}
    assert {"path": "ARCHITECTURE.md", "reason": "size bound"} in docs["skipped"]
    assert not (run / "project-docs" / "ARCHITECTURE.md").exists()


def test_a_project_without_documents_snapshots_nothing(tmp_path) -> None:
    root = tmp_path / "bare"
    root.mkdir()
    run = root / "runs" / "r"
    run.mkdir(parents=True)
    docs = snapshot_project_docs(root, run)
    assert docs == {"dir": None, "files": {}, "skipped": [], "note": docs["note"]}
    assert not (run / "project-docs").exists()


# -- path isolation -----------------------------------------------------------


@pytest.mark.parametrize("reference, error", [
    (None, "not recorded"),
    ("", "not a relative path"),
    (7, "not a relative path"),
    ("../secret", "escapes the base directory"),
    ("train/../../secret", "escapes the base directory"),
])
def test_references_that_cannot_be_honoured_are_errors_not_opens(tmp_path, reference, error):
    base = tmp_path / "base"
    base.mkdir()
    (tmp_path / "secret").write_text("no")
    resolved = resolve_reference(base, reference)
    assert resolved["exists"] is False and resolved["error"] == error


def test_an_absolute_reference_is_refused_even_when_it_is_inside(tmp_path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    (base / "inside.txt").write_text("yes")
    resolved = resolve_reference(base, str(base / "inside.txt"))
    assert resolved["exists"] is False and resolved["error"] == "escapes the base directory"


@pytest.mark.skipif(os.name != "posix", reason="symlinks")
def test_a_symlink_that_leaves_the_base_is_refused(tmp_path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    (tmp_path / "secret").write_text("no")
    os.symlink(tmp_path / "secret", base / "link")
    resolved = resolve_reference(base, "link")
    assert resolved["exists"] is False and resolved["error"] == "escapes the base directory"
    # ...while one that stays inside is an ordinary file.
    (base / "real.txt").write_text("yes")
    os.symlink(base / "real.txt", base / "inner")
    assert resolve_reference(base, "inner") == {"path": "inner", "exists": True, "error": None}


def test_a_missing_reference_is_reported_not_raised(tmp_path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    assert resolve_reference(base, "gone.json") == {"path": "gone.json", "exists": False,
                                                    "error": None}


def test_a_record_pointing_outside_its_project_is_a_problem(tmp_path) -> None:
    root = _project(tmp_path)
    run = _walked_run(root, "run-5", revision=REVISION_A)
    record = json.loads((run / RUN_RECORD_FILENAME).read_text())
    record["project_artifacts"]["policy"] = "../other-project/assets/gait.cxpolicy"
    record["artifacts"]["trace"] = "/etc/passwd"
    record["videos"] = [{"path": "../../video.mp4"}]
    (run / RUN_RECORD_FILENAME).write_text(json.dumps(record))
    read = read_run_record(run, root)
    assert read["resolved"]["project_artifacts"]["policy"]["error"] == "escapes the base directory"
    assert read["resolved"]["artifacts"]["trace"]["error"] == "escapes the base directory"
    assert read["problems"] == [
        "artifacts.trace: escapes the base directory",
        "project_artifacts.policy: escapes the base directory",
        "videos[0]: escapes the base directory",
    ]


# -- the reader ---------------------------------------------------------------


def test_the_reader_resolves_every_reference_and_names_the_missing(tmp_path) -> None:
    root = _project(tmp_path)
    run = _walked_run(root, "run-6", revision=REVISION_A)
    read = read_run_record(run, root)
    assert read["outcome"] == "completed" and read["problems"] == []
    assert read["resolved"]["artifacts"]["script"] == {"path": "script.py", "exists": True,
                                                       "error": None}
    assert read["resolved"]["project_artifacts"]["policy"]["exists"] is True
    assert read["resolved"]["artifacts"]["receipt"] == {"path": None, "exists": False,
                                                        "error": "not recorded"}
    # Delete the trace, the policy and one snapshot page; edit another.
    (run / "rollout" / "assembly-simulation-trace.json").unlink()
    (root / "assets" / "gait.cxpolicy").unlink()
    (run / "project-docs" / "docs" / "actuators.md").unlink()
    (run / "project-docs" / "PROGRESS.md").write_text("tampered\n")
    read = read_run_record(run, root)
    assert read["problems"] == [
        "artifacts.trace: missing",
        "project_artifacts.policy: missing",
        "project_docs.PROGRESS.md: digest differs from record",
        "project_docs.docs/actuators.md: missing",
    ]
    assert read["status"] == "ok"  # the record is what it was; the disk is not


def test_a_legacy_run_is_read_from_its_review_and_labelled(tmp_path) -> None:
    root = _project(tmp_path)
    run = root / "runs" / "old"
    (run / "rollout").mkdir(parents=True)
    (run / "review.json").write_text(json.dumps({
        "schema": "cadex-walk-review-v1", "weights": "w.cxpolicy", "sha256": "s" * 64,
        "total_reward": -1.0, "trace": "rollout/assembly-simulation-trace.json",
        "params": {"k": 1.0}, "render": {"path": "review/render/" + REVISION_B},
        "legs": [{"leg": "train", "exit": 0},
                 {"leg": "rollout", "exit": 0, "accepted_revision": REVISION_B,
                  "digest": "e" * 64}],
    }))
    read = read_run_record(run, root)
    assert read["status"] == "unrecorded"
    assert read["outcome"] == "legacy run: review.json only"
    assert read["model"] == {"accepted_revision": REVISION_B, "digest": "e" * 64,
                             "identity_source": "review.json legs (legacy run, no run.json)"}
    assert read["params"]["specs"] is None
    assert read["policy"] == {"name": "w.cxpolicy", "sha256": "s" * 64, "asset": None}
    assert read["problems"] == ["artifacts.trace: missing",
                                "project_artifacts.render: missing"]


def test_empty_and_unreadable_runs_are_listed_not_skipped(tmp_path) -> None:
    root = _project(tmp_path)
    (root / "runs" / "empty").mkdir(parents=True)
    broken = root / "runs" / "broken"
    broken.mkdir()
    (broken / RUN_RECORD_FILENAME).write_text("{not json")
    foreign = root / "runs" / "foreign"
    foreign.mkdir()
    (foreign / RUN_RECORD_FILENAME).write_text(json.dumps({"schema": "something-else"}))
    (root / "runs" / "a-file").write_text("not a run")
    runs = {run["run"]: run for run in list_runs(root)}
    assert set(runs) == {"empty", "broken", "foreign"}
    assert runs["empty"]["status"] == "empty"
    assert runs["broken"]["status"] == "unreadable" and "JSONDecodeError" in runs["broken"]["error"]
    assert runs["foreign"]["status"] == "unreadable"
    assert runs["foreign"]["error"] == "unknown record schema 'something-else'"
    assert list_runs(tmp_path / "nowhere") == []


def test_the_project_review_tells_current_runs_from_historical_ones(tmp_path) -> None:
    root = _project(tmp_path)
    _walked_run(root, "first", revision=REVISION_A)
    _walked_run(root, "second", revision=REVISION_B)
    _manifest(root, REVISION_B)
    review = read_project_review(root)
    assert review["schema"] == PROJECT_REVIEW_SCHEMA and review["project"] == "biped"
    assert review["accepted"]["available"] is True
    assert review["accepted"]["revision"] == REVISION_B
    assert review["accepted"]["param_values"] == {"leg_len": 90.0}
    assert review["decisions"] == ["ADR-001 — Project scaffolded (2026-09-12)",
                                   "ADR-002 — Longer shins (2026-09-12)"]
    assert review["docs"] == {"ARCHITECTURE.md": True, "DECISIONS.md": True,
                              "PROGRESS.md": True,
                              "domain": ["docs/actuators.md", "docs/inventory.md"]}
    relations = {run["run"]: run["relation"] for run in review["runs"]}
    assert relations == {"first": "historical", "second": "current"}
    # The historical run still shows ITS parameters and ITS documents, never
    # today's: the reader reads the record and the snapshot, nothing else.
    first = next(run for run in review["runs"] if run["run"] == "first")
    assert first["model"]["accepted_revision"] == REVISION_A
    assert first["resolved"]["project_artifacts"]["render"]["path"] == f"review/render/{REVISION_A}"
    assert first["resolved"]["artifacts"]["project_docs"]["exists"] is True


def test_the_project_review_without_a_manifest_says_so(tmp_path) -> None:
    root = _project(tmp_path)
    _walked_run(root, "only", revision=REVISION_A)
    review = read_project_review(root)
    assert review["accepted"] == {"available": False, "reason": "no script.json"}
    assert review["runs"][0]["relation"] == "unknown"
    (root / "script.json").write_text(json.dumps({"schema": "cadex-project-script-v9"}))
    assert read_accepted_identity(root)["reason"] == "unknown manifest schema 'cadex-project-script-v9'"
    (root / "script.json").write_text(json.dumps({"schema": "cadex-project-script-v1"}))
    assert read_accepted_identity(root)["reason"] == "nothing accepted yet"
    (root / "script.json").write_text("{")
    assert "JSONDecodeError" in read_accepted_identity(root)["reason"]


def test_runs_are_listed_oldest_first_by_their_recorded_time(tmp_path) -> None:
    root = _project(tmp_path)
    for name, stamp in (("zeta", "2026-09-12T10:00:00Z"), ("alpha", "2026-09-12T11:00:00Z")):
        run = root / "runs" / name
        run.mkdir(parents=True)
        (run / RUN_RECORD_FILENAME).write_text(json.dumps({
            "schema": RUN_RECORD_SCHEMA, "run": name, "recorded_at": stamp,
            "status": "running", "artifacts": {}, "project_artifacts": {},
            "videos": [], "legs": [],
        }))
    listed = list_runs(root)
    assert [run["run"] for run in listed] == ["zeta", "alpha"]
    assert listed[0]["outcome"] == "started and never finished: still running, or interrupted"


def test_the_reader_reads_a_copied_project_the_same(tmp_path) -> None:
    """Every reference is relative, so a copy reviews as the original did."""

    import shutil

    root = _project(tmp_path)
    _walked_run(root, "run-7", revision=REVISION_A)
    _manifest(root, REVISION_A)
    copy = tmp_path / "biped-copy"
    shutil.copytree(root, copy)
    shutil.rmtree(root)
    review = read_project_review(copy)
    assert review["project"] == "biped-copy"
    assert review["runs"][0]["problems"] == []
    assert review["runs"][0]["relation"] == "current"


def test_video_verification_reuses_unchanged_bytes_but_detects_replaced_content(tmp_path, monkeypatch):
    from cadex_cli import review_record

    root = _project(tmp_path)
    run = root / 'runs/video'
    run.mkdir(parents=True)
    video = run / 'final.mp4'
    original = b'original policy video'
    video.write_bytes(original)
    payload = {'schema': RUN_RECORD_SCHEMA, 'run': 'video', 'status': 'ok',
               'videos': [{'path': video.name, 'sha256': hashlib.sha256(original).hexdigest()}]}
    (run / RUN_RECORD_FILENAME).write_text(json.dumps(payload))
    reads = []
    real_hash = review_record._sha256
    def counted(path):
        reads.append(path)
        return real_hash(path)
    monkeypatch.setattr(review_record, '_sha256', counted)
    for _ in range(3):
        assert not read_run_record(run, root)['problems']
    assert reads == [video]
    # Restoring size and mtime must not conceal an in-place corruption.
    before = video.stat()
    video.write_bytes(b'x' * len(original))
    os.utime(video, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert 'digest mismatch' in read_run_record(run, root)['problems'][0]
    replacement = video.with_suffix('.partial')
    replacement.write_bytes(original)
    os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
    replacement.replace(video)
    assert not read_run_record(run, root)['problems']
    # A changed recorded digest is checked even when the file stays the same.
    payload['videos'][0]['sha256'] = '0' * 64
    (run / RUN_RECORD_FILENAME).write_text(json.dumps(payload))
    assert 'digest mismatch' in read_run_record(run, root)['problems'][0]
    # Cached bytes never permit a newly escaping reference.
    video.unlink()
    outside = tmp_path / 'outside.mp4'
    outside.write_bytes(original)
    video.symlink_to(outside)
    assert 'escapes' in read_run_record(run, root)['problems'][0]


def test_video_modified_during_verification_is_not_cached(tmp_path, monkeypatch):
    from cadex_cli import review_record

    video = tmp_path / 'changing.mp4'
    video.write_bytes(b'before')
    original_hash = review_record._sha256
    def changing(path):
        digest = original_hash(path)
        path.write_bytes(b'after')
        return digest
    monkeypatch.setattr(review_record, '_sha256', changing)
    with pytest.raises(OSError, match='changed during verification'):
        review_record._video_sha256(video)
    monkeypatch.setattr(review_record, '_sha256', original_hash)
    assert review_record._video_sha256(video) == hashlib.sha256(b'after').hexdigest()


def test_video_digest_cache_evicts_oldest_file(tmp_path, monkeypatch):
    from cadex_cli import review_record
    review_record._cached_video_sha256.cache_clear()
    original_hash = review_record._sha256
    reads = []

    def counted(path):
        reads.append(path)
        return original_hash(path)

    monkeypatch.setattr(review_record, '_sha256', counted)
    for index in range(257):
        video = tmp_path / f'{index}.webm'
        video.write_bytes(str(index).encode())
        review_record._video_sha256(video)
    assert review_record._cached_video_sha256.cache_info().currsize == 256
    review_record._video_sha256(video)
    assert len(reads) == 257
    assert review_record._video_sha256(tmp_path / '0.webm') == hashlib.sha256(b'0').hexdigest()
    assert len(reads) == 258
    assert review_record._cached_video_sha256.cache_info().currsize == 256


# -- policy lineage -----------------------------------------------------------


def _set(run: Path, **changes) -> None:
    path = run / RUN_RECORD_FILENAME
    record = json.loads(path.read_text())
    record.update(changes)
    path.write_text(json.dumps(record, indent=2))


def _retain(run: Path, name: str, payload: bytes) -> str:
    (run / "train" / name).write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def _video(run: Path) -> None:
    (run / "clip.webm").write_bytes(b"not a real video")
    (run / "video.json").write_text(json.dumps({
        "schema": "cadex-run-video-v1", "state": "ready", "error": None,
        "videos": [{"path": "clip.webm", "sha256": hashlib.sha256(b"not a real video").hexdigest()}]}))


def test_policy_lineage_comes_from_retained_bytes_not_from_run_names(tmp_path) -> None:
    """No run here is called ``-final`` or ``-checkpoint20``. The training run
    is the one whose own ``train/`` holds the policy bytes; a playback names
    the run its record kept and the bytes either agree or visibly do not;
    siblings are the other runs carrying policies from the same origin, in
    record order; a symlink out of the project is never followed."""

    root = _project(tmp_path)
    _manifest(root, REVISION_A)
    stamps = {"apple": "2026-09-01T00:00:00Z", "kestrel": "2026-09-02T00:00:00Z",
              "pear": "2026-09-03T00:00:00Z", "quince": "2026-09-04T00:00:00Z",
              "fig": "2026-09-05T00:00:00Z", "plum": "2026-09-06T00:00:00Z",
              "zebra": "2026-09-07T00:00:00Z", "mango": "2026-09-08T00:00:00Z"}
    runs = {}
    for name, stamp in stamps.items():
        shutil.rmtree(root / "review" / "render" / REVISION_A, ignore_errors=True)   # one revision, many runs
        runs[name] = _walked_run(root, name, revision=REVISION_A)
        _set(runs[name], recorded_at=stamp)
    final = _retain(runs["kestrel"], "weights.bin", b"kestrel final policy")
    checkpoint = _retain(runs["kestrel"], "snap-2.bin", b"kestrel checkpoint two")
    (runs["kestrel"] / "train/progress.json").write_text(json.dumps({
        "schema": "cadex-training-progress-v1", "state": "done",
        "checkpoints": [{"path": "snap-2.bin", "iteration": 2, "sha256": checkpoint}]}))
    _set(runs["kestrel"], policy={"name": "weights.bin", "sha256": final, "asset": None})
    other = _retain(runs["apple"], "own.bin", b"apple policy")
    _set(runs["apple"], policy={"name": "own.bin", "sha256": other, "asset": None})
    _retain(runs["fig"], "copied.bin", b"kestrel final policy")   # the same bytes, retained later
    _set(runs["fig"], policy={"name": "copied.bin", "sha256": final, "asset": None})
    _set(runs["pear"], policy={"name": "snap-2.bin", "sha256": checkpoint, "asset": None},
         training={"requested": {"source_run": "kestrel"}, "receipt": {}})
    _set(runs["quince"], policy={"name": "weights.bin", "sha256": final, "asset": None},
         training={"requested": {"source_run": "kestrel"}, "receipt": {}})
    _set(runs["plum"], policy={"name": "weights.bin", "sha256": final, "asset": None},
         training={"requested": {"source_run": "apple"}, "receipt": {}})
    _set(runs["zebra"], policy={"name": "", "sha256": "", "asset": None})
    outside = hashlib.sha256((root / "script.py").read_bytes()).hexdigest()
    os.symlink(root / "script.py", runs["apple"] / "train" / "link.bin")
    _set(runs["mango"], policy={"name": "link.bin", "sha256": outside, "asset": None},
         training={"requested": {"source_run": "apple"}, "receipt": {}})
    _video(runs["pear"])
    _video(runs["quince"])

    quince = policy_lineage(root, "quince")
    assert quince["schema"] == "cadex-policy-lineage-v1"
    assert quince["origin"] == {"run": "kestrel", "path": "weights.bin", "kind": "final", "iteration": None,
                                "recorded_at": stamps["kestrel"], "also_retained_by": ["fig"]}
    assert quince["recorded_source_run"] == "kestrel" and quince["source_agrees"] is True
    assert [(s["run"], s["kind"], s["iteration"], s["videos"], s["relation"]) for s in quince["playbacks"]] == [
        ("pear", "checkpoint", 2, 1, "current"), ("fig", "final", None, 0, "current"),
        ("plum", "final", None, 0, "current")]
    pear = policy_lineage(root, "pear")
    assert pear["origin"]["run"] == "kestrel" and pear["origin"]["kind"] == "checkpoint"
    assert pear["origin"]["iteration"] == 2 and pear["origin"]["path"] == "snap-2.bin"
    assert [s["run"] for s in pear["playbacks"]] == ["quince", "fig", "plum"]
    kestrel = policy_lineage(root, "kestrel")
    assert kestrel["origin"]["run"] == "kestrel" and kestrel["origin"]["kind"] == "final"
    assert kestrel["recorded_source_run"] is None and kestrel["source_agrees"] is None
    assert [s["run"] for s in kestrel["playbacks"]] == ["pear", "quince", "fig", "plum"]
    plum = policy_lineage(root, "plum")
    assert plum["origin"]["run"] == "kestrel" and plum["recorded_source_run"] == "apple"
    assert plum["source_agrees"] is False
    apple = policy_lineage(root, "apple")
    assert apple["origin"]["run"] == "apple" and apple["playbacks"] == []
    zebra = policy_lineage(root, "zebra")
    assert zebra["policy_sha256"] is None and zebra["origin"] is None
    assert zebra["reason"] == "no policy recorded for this run" and zebra["playbacks"] == []
    mango = policy_lineage(root, "mango")
    assert mango["origin"] is None and mango["source_agrees"] is None
    assert mango["reason"].startswith("no run in this project retains")
    missing = policy_lineage(root, "nonesuch")
    assert missing["origin"] is None and "not in this project" in missing["reason"]
