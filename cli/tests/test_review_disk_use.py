# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Per-run disk use in the review panel (ADR-322).

A project that has been trained many times keeps many runs, and the
charter's bounded-operation rung asks that what each keeps be visible.
``run_disk_use`` counts one run's permitted project-local files — each inode
once, no symlink followed — sizes every reference its record names with
the reader's own status words, and sizes a project-level reference that
other runs share once, named as shared, rather than folding it into the
run's total. It travels with ``/api/run/<name>`` (the detail), never with
the run list, so the two-second poll stays bounded (ADR-321). The browser
half opens the page, reads the panel against the API, keeps a historical
selection with its video playing through a poll, and shows missing and
refused references as such.
"""

from __future__ import annotations

import json
import os
import shutil

import pytest

from cadex_cli import review_record
from cadex_cli.review_record import run_disk_use
from cadex_cli.review_server import ReviewProject, serve
from test_review_record import REVISION_A, REVISION_B
from test_review_server import (
    _escaped_run,
    _json,
    _mesh_run,
    _open,
    _review_project,
    _rewrite_record,
    browser,  # noqa: F401  (fixture)
    needs_browser,
)


def _apparent(top) -> tuple[int, int]:
    """Bytes and files under ``top``, each inode once, symlinks not followed."""

    seen, total, files = set(), 0, 0
    for directory, _dirs, names in os.walk(top):
        for name in names:
            path = os.path.join(directory, name)
            if os.path.islink(path):
                continue
            stat = os.lstat(path)
            if (stat.st_dev, stat.st_ino) in seen:
                continue
            seen.add((stat.st_dev, stat.st_ino))
            total += stat.st_size
            files += 1
    return total, files


def _decorate(root, tmp_path):
    """``first`` gains a hard-linked rollout file, a symlinked file and a
    symlinked directory (both pointing outside the project) and a bigger
    checkpoint; the links must be skipped and the hard link counted once."""

    run = root / "runs" / "first"
    os.link(run / "rollout" / "torso.stl", run / "rollout" / "torso-again.stl")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "leak.bin").write_bytes(b"x" * 5000)
    (outside / "tree").mkdir()
    (outside / "tree" / "deep.bin").write_bytes(b"y" * 7000)
    os.symlink(outside / "leak.bin", run / "train" / "leak.bin")
    os.symlink(outside / "tree", run / "linked-tree")
    (run / "train" / "iter-9.cxpolicy").write_bytes(b"c" * 3000)
    return run


def test_disk_use_counts_permitted_files_once_and_sizes_each_reference(tmp_path) -> None:
    root = _review_project(tmp_path)
    run = _decorate(root, tmp_path)
    project = ReviewProject(root)
    disk = project.detail("first")["disk"]
    assert disk["schema"] == "cadex-run-disk-use-v1" and disk["state"] == "counted" and disk["reason"] is None
    expected_bytes, expected_files = _apparent(run)
    assert (disk["bytes"], disk["files"]) == (expected_bytes, expected_files)
    assert disk["hardlinked_entries"] == 1
    assert disk["skipped_count"] == 2
    assert sorted(item["path"] for item in disk["skipped"]) == ["linked-tree", "train/leak.bin"]
    assert {item["reason"] for item in disk["skipped"]} == {"symlink not followed"}
    # Nothing beyond the links was counted: the leaked bytes are not this run's.
    assert disk["bytes"] < expected_bytes + 5000 and 5000 not in {e["bytes"] for e in disk["by_dir"].values()}
    assert sum(entry["bytes"] for entry in disk["by_dir"].values()) == disk["bytes"]
    assert sum(entry["files"] for entry in disk["by_dir"].values()) == disk["files"]
    assert disk["by_dir"]["train"]["bytes"] == _apparent(run / "train")[0]
    assert disk["by_dir"]["rollout"]["files"] == 3  # trace, torso, leg: the hard link is not a fourth
    assert disk["by_dir"]["."]["files"] == 3  # script.py, review.json, run.json
    # Every reference the record names, with the reader's status words.
    refs = disk["references"]
    trace = refs["artifacts"]["trace"]
    assert trace["status"] == "retained" and trace["in_run"] is True
    assert trace["bytes"] == (run / "rollout" / "assembly-simulation-trace.json").stat().st_size
    assert refs["artifacts"]["receipt"] == {"path": None, "status": "not recorded", "bytes": None, "files": 0, "in_run": True}
    docs = refs["project_docs"]
    assert docs["status"] == "retained" and docs["files"] == 5 and docs["bytes"] == _apparent(run / "project-docs")[0]
    assert refs["videos"] == []
    # Project-level references outside the run are sized once and named as
    # shared: the policy asset every fixture run cites, and the render
    # directory ``broken`` shares at the same revision.
    policy = refs["project_artifacts"]["policy"]
    assert policy["status"] == "retained" and policy["in_run"] is False
    assert policy["bytes"] == (root / "assets" / "gait.cxpolicy").stat().st_size
    assert policy["shared_with"] == ["broken", "second"]
    render = refs["project_artifacts"]["render"]
    assert render["status"] == "retained" and render["in_run"] is False and render["files"] == 1
    assert render["shared_with"] == ["broken"]
    inventory = refs["project_artifacts"]["inventory"]
    assert inventory["status"] == "retained" and inventory["shared_with"] == ["broken", "second"]
    assert disk["shared_bytes"] == policy["bytes"] + render["bytes"] + inventory["bytes"]
    assert refs["project_artifacts"]["section"]["status"] == "not recorded"


def test_disk_use_marks_missing_and_refused_references_without_opening_them(tmp_path) -> None:
    root = _review_project(tmp_path)
    project = ReviewProject(root)
    # ``broken`` lost its rollout: its trace is missing, with no size.
    broken = project.detail("broken")["disk"]
    assert broken["state"] == "counted" and "rollout" not in broken["by_dir"]
    assert broken["references"]["artifacts"]["trace"] == {
        "path": "rollout/assembly-simulation-trace.json", "status": "missing", "bytes": None, "files": 0, "in_run": True}
    # A reference that escapes its base is refused and never stat'ed; a
    # project reference inside the run's own directory is in its total.
    second = root / "runs" / "second"
    record = json.loads((second / "run.json").read_text())
    record["artifacts"]["task_bundle"] = "../../../etc/passwd"
    record["project_artifacts"]["policy"] = "runs/second/rollout/torso.stl"
    _rewrite_record(second, artifacts=record["artifacts"], project_artifacts=record["project_artifacts"])
    disk = project.detail("second")["disk"]
    refused = disk["references"]["artifacts"]["task_bundle"]
    assert refused["status"] == "refused" and refused["bytes"] is None and "escapes" in refused["reason"]
    own = disk["references"]["project_artifacts"]["policy"]
    assert own["status"] == "retained" and own["in_run"] is True and own["shared_with"] == []
    assert disk["shared_bytes"] == sum(item["bytes"] for key, item in disk["references"]["project_artifacts"].items()
                                       if key != "policy" and item["status"] == "retained")
    # A run directory that escapes the project is not counted at all.
    _escaped_run(root, tmp_path)
    escaped = project.detail("escaped")["disk"]
    assert escaped["state"] == "unreadable" and escaped["reason"] == "run directory escapes the project directory"
    assert escaped["bytes"] == 0 and escaped["files"] == 0 and escaped["by_dir"] == {}


def test_disk_use_is_bounded_and_says_when_it_stopped(tmp_path, monkeypatch) -> None:
    root = _review_project(tmp_path)
    run = root / "runs" / "first"
    for i in range(30):
        (run / "train" / f"iter-{i}.cxpolicy").write_bytes(b"c" * 10)
    monkeypatch.setattr(review_record, "DISK_USE_ENTRY_LIMIT", 12)
    disk = run_disk_use(root, ReviewProject(root).run("first"))
    assert disk["state"] == "truncated" and disk["entry_limit"] == 12
    assert "12 directory entries" in disk["reason"] and "floor" in disk["reason"]
    assert 0 < disk["files"] <= 12 and disk["bytes"] < _apparent(run)[0]
    monkeypatch.setattr(review_record, "DISK_USE_ENTRY_LIMIT", 20_000)
    assert run_disk_use(root, ReviewProject(root).run("first"))["state"] == "counted"


def test_disk_use_travels_with_the_detail_and_never_with_the_run_list(tmp_path) -> None:
    root = _review_project(tmp_path)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        review = _json(server.url + "api/project")
        assert all("disk" not in run for run in review["runs"])
        detail = _json(server.url + "api/run/first")
        assert detail["disk"]["state"] == "counted" and detail["disk"]["bytes"] == _apparent(root / "runs" / "first")[0]
        assert detail["disk"]["references"]["project_artifacts"]["policy"]["shared_with"] == ["broken", "second"]
        assert "curve" in detail["telemetry"]
    finally:
        server.shutdown()
        server.server_close()


def test_directory_references_share_one_lazy_traversal_budget(tmp_path, monkeypatch):
    root = tmp_path / "project"
    (root / "runs" / "one").mkdir(parents=True)
    (root / "runs" / "one" / "file").write_bytes(b"run")
    refs = {}
    for name in ("a", "b", "c"):
        directory = root / name
        directory.mkdir()
        for i in range(8):
            (directory / str(i)).write_bytes(b"12345")
        refs[name] = review_record.resolve_reference(root, name)
    record = {"run": "one", "resolved": {"project_artifacts": refs}}
    scandir = os.scandir
    visited = []

    class CountedScan:
        def __init__(self, path):
            self.scan = scandir(path)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.scan.close()
        def __iter__(self):
            return self
        def __next__(self):
            entry = next(self.scan)
            visited.append(entry.path)
            return entry

    monkeypatch.setattr(review_record, "DISK_USE_ENTRY_LIMIT", 12)
    monkeypatch.setattr(review_record.os, "scandir", CountedScan)
    disk = run_disk_use(root, record)
    assert len(visited) == disk["entries_visited"] == 12
    assert disk["state"] == "counted"  # The run itself was fully counted.
    a, b, c = (disk["references"]["project_artifacts"][key] for key in refs)
    assert a["status"] == "retained" and a["bytes"] == 40
    assert b["status"] == "truncated" and b["lower_bound"] and b["bytes"] == 15
    assert c["status"] == "truncated" and c["lower_bound"] and c["bytes"] == 0
    assert disk["shared_bytes"] == 55 and disk["shared_lower_bound"]
