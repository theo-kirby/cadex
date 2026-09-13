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


@needs_browser
def test_browser_shows_disk_use_for_the_selected_run_and_keeps_history_through_polls(tmp_path, browser) -> None:
    from cadex_cli.video import render as render_video
    from test_video import _video_run

    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg not available")
    root = _review_project(tmp_path)
    _decorate(root, tmp_path)
    _video_run(root, "movie")
    render_video(root, "movie")
    _mesh_run(root, "newest", revision=REVISION_B)
    _rewrite_record(root / "runs" / "newest", recorded_at="2031-01-01T00:00:00Z")
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        assert page.text("#view-kind") == "RUN newest"
        page.wait_for("document.getElementById('disk').dataset.state === 'counted'")
        api = _json(server.url + "api/run/newest")["disk"]
        assert page.attribute("#disk-summary", "data-bytes") == str(api["bytes"])
        assert page.attribute("#disk-summary", "data-files") == str(api["files"])
        assert page.text("#disk-summary").startswith("Disk use: ")
        assert "under runs/newest/" in page.text("#disk-summary")

        # The accepted view has no run to count.
        page.evaluate("window.cadexReview.select('accepted')", await_promise=True)
        assert page.attribute("#disk", "data-state") == "unselected"
        assert page.text("#artifacts tbody tr td:nth-child(4)") == ""

        # A deliberately selected historical run with a video: its own
        # count, its links skipped, its shared references named.
        page.click("#views li[data-run='movie']")
        page.wait_for("document.getElementById('view-kind').textContent === 'RUN movie'")
        page.wait_for("document.getElementById('disk').dataset.state === 'counted'")
        movie = _json(server.url + "api/run/movie")["disk"]
        assert page.text("#view-relation").startswith("HISTORICAL")
        assert page.attribute("#disk-summary", "data-bytes") == str(movie["bytes"])
        assert page.attribute("#disk-summary", "data-shared-bytes") == str(movie["shared_bytes"])
        dirs = page.evaluate("Array.from(document.querySelectorAll('#disk-dirs li[data-dir]')).map(n => [n.dataset.dir, +n.dataset.bytes])")
        assert dict(dirs) == {dir: entry["bytes"] for dir, entry in movie["by_dir"].items()}
        shared = page.evaluate("Array.from(document.querySelectorAll('#disk-shared li[data-key]')).map(n => [n.dataset.key, n.dataset.shared, +n.dataset.bytes, n.textContent])")
        by_key = {item[0]: item for item in shared}
        assert by_key["policy"][1] == "true" and by_key["policy"][2] == movie["references"]["project_artifacts"]["policy"]["bytes"]
        assert "shared with broken, first, newest, second" in by_key["policy"][3] and "not in its total" in by_key["policy"][3]
        assert page.attribute("#disk-shared li[data-shared-total]", "data-shared-total") == str(movie["shared_bytes"])
        trace_size = page.attribute("#artifacts tr[data-group=artifacts][data-key=trace] td:nth-child(4)", "data-size")
        assert trace_size == str(movie["references"]["artifacts"]["trace"]["bytes"])
        assert page.attribute("#artifacts tr[data-group=artifacts][data-key=receipt] td:nth-child(4)", "data-size") == "none"
        assert "KB" in page.text("#videos li[data-video='0']") or " B" in page.text("#videos li[data-video='0']")
        page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
        page.evaluate("window.playing = document.querySelector('#videos video'); playing.muted = true; playing.loop = true; playing.play()",
                      await_promise=True)
        page.wait_for("playing.currentTime > 0.1")

        # A poll under a growing project leaves the historical selection,
        # its playback and its count in place.
        _mesh_run(root, "later", revision=REVISION_B)
        _rewrite_record(root / "runs" / "later", recorded_at="2032-01-01T00:00:00Z")
        page.evaluate("window.cadexReview.refresh()", await_promise=True)
        assert page.text("#view-kind") == "RUN movie"
        assert page.evaluate("playing === document.querySelector('#videos video') && !playing.paused")
        assert page.attribute("#disk-summary", "data-bytes") == str(movie["bytes"])
        assert page.text("#current-run") == "Current run: later"

        # Missing and refused references say so in the size column too.
        page.click("#views li[data-run='broken']")
        page.wait_for("document.getElementById('view-kind').textContent === 'RUN broken'")
        page.wait_for("document.getElementById('disk').dataset.state === 'counted'")
        assert page.attribute("#artifacts tr[data-group=artifacts][data-key=trace] td:nth-child(4)", "data-size") == "missing"
        assert page.text("#artifacts tr[data-group=artifacts][data-key=trace] td:nth-child(4)") == "missing — nothing on disk"
        first = root / "runs" / "first"
        record = json.loads((first / "run.json").read_text())
        record["artifacts"]["task_bundle"] = "../../../etc/passwd"
        _rewrite_record(first, artifacts=record["artifacts"])
        page.click("#views li[data-run='first']")
        page.wait_for("document.getElementById('view-kind').textContent === 'RUN first'")
        page.wait_for("document.getElementById('disk').dataset.state === 'counted'")
        assert page.attribute("#artifacts tr[data-group=artifacts][data-key=task_bundle] td:nth-child(4)", "data-size") == "refused"
        skipped = page.evaluate("Array.from(document.querySelectorAll('#disk-dirs li[data-skipped]')).map(n => n.dataset.skipped)")
        assert sorted(skipped) == ["linked-tree", "train/leak.bin"]
        assert "1 hard-linked entry counted once" in page.text("#disk-summary")
        assert "2 entries skipped" in page.text("#disk-summary")

        # An escaped run directory is not counted, and the page says why.
        _escaped_run(root, tmp_path)
        page.evaluate("window.cadexReview.refresh()", await_promise=True)
        page.click("#views li[data-run='escaped']")
        page.wait_for("document.getElementById('disk').dataset.state === 'unreadable'")
        assert page.text("#disk-summary") == "Disk use: not counted — run directory escapes the project directory"

        # The route back to the current run.
        page.click("#current-run")
        page.wait_for("document.getElementById('view-kind').textContent === 'RUN later'")
        page.wait_for("document.getElementById('disk').dataset.state === 'counted'")
        assert page.evaluate("window.cadexReview.state().disk.state") == "counted"
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


@needs_browser
def test_browser_labels_truncated_reference_sizes_as_lower_bounds(tmp_path, monkeypatch, browser):
    root = _review_project(tmp_path)
    monkeypatch.setattr(review_record, "DISK_USE_ENTRY_LIMIT", 1)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        page.evaluate("window.cadexReview.select('first')", await_promise=True)
        page.wait_for("document.getElementById('disk').dataset.state === 'truncated'")
        disk = _json(server.url + "api/run/first")["disk"]
        render = disk["references"]["project_artifacts"]["render"]
        assert render["status"] == "truncated" and render["lower_bound"]
        cell = '#artifacts tr[data-group=project_artifacts][data-key=render] td:nth-child(4)'
        assert page.attribute(cell, "data-lower-bound") == "true"
        assert page.text(cell) == "at least 0 B · truncated"
        assert "at least 0 B · truncated" in page.text('#disk-shared li[data-key=render]')
        assert "at least" in page.text('#disk-shared li[data-shared-total]')
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
def test_arriving_disk_detail_adds_video_size_without_replacing_playback(tmp_path, monkeypatch, browser):
    import threading
    from cadex_cli.video import render as render_video
    from test_video import _video_run

    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg not available")
    root = _review_project(tmp_path)
    _video_run(root, "movie")
    render_video(root, "movie")
    _rewrite_record(root / "runs" / "movie", recorded_at="2032-01-01T00:00:00Z")
    release = threading.Event()
    original = ReviewProject.detail

    def delayed(self, name):
        assert release.wait(15), "test must release the detail response"
        return original(self, name)

    monkeypatch.setattr(ReviewProject, "detail", delayed)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = browser.page(server.url)
        page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
        page.evaluate("window.kept=document.querySelector('#videos video'); kept.muted=true; kept.loop=true; kept.play()", await_promise=True)
        page.wait_for("kept.currentTime > 0.1")
        assert page.text('[data-video-size="0"]') == ''
        release.set()
        page.wait_for("document.querySelector('[data-video-size]')?.textContent.length > 0")
        assert page.evaluate("kept === document.querySelector('#videos video') && !kept.paused")
    finally:
        release.set()
        server.shutdown()
        server.server_close()
