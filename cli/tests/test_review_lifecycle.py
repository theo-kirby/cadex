# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The review dashboard across restart and copy (D6/D7, fixture evidence).

The dashboard is a process a person stops and starts; the project and the
training that writes into it are not. This module restarts the real
``cadex review`` command on its own port while an **independent telemetry
producer** — a separate process the server never spawned and never
learns about — keeps committing training snapshots, and checks that the
page already open recovers, that a page opened afresh shows the same
project, and that the producer was neither stopped nor duplicated.

Fixture coverage only: the project is laid out by hand, the producer is
a loop writing the trainer's snapshot format, and no engine runs at any
point. That last fact is the engine half of D6 for this reader — there is
no engine to restart — and the real fresh-biped pass remains separate.
The copy test checks independent accepted fixtures and retained review artifacts
with the original path unavailable; it does not run real design or training.
Browser tests **skip** without a Chromium; the video half without FFmpeg.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

import pytest

from cadex_cli.report import EXIT_OK
from cadex_cli.video import render
from cdp_browser import HeadlessBrowser
from test_review_record import REVISION_A, REVISION_B
from test_review_server import (CLI_DIR, _get, _open, _review_project,
                                _stage_accepted, browser, needs_browser)
from test_video import _video_run

PRODUCER = r"""
import json, os, sys, time
path, marker = sys.argv[1], sys.argv[2]
path = __import__('pathlib').Path(path)
started = time.time()
iteration = 0
while time.time() - started < 300:
    data = {"schema": "cadex-training-progress-v1", "state": "training",
            "updated_at": time.time(), "task_sha256": "t" * 64,
            "iteration": iteration, "total": 10 ** 6,
            "reward_per_step": iteration + 0.5, "loss": 1.0 / (iteration + 1),
            "episode_steps": 12 + iteration,
            "curve": [[i, i + 0.5] for i in range(max(0, iteration - 511), iteration + 1)],
            "loss_curve": [[i, 1.0 / (i + 1)] for i in range(max(0, iteration - 511), iteration + 1)],
            "episode_steps_curve": [[i, 12 + i] for i in range(max(0, iteration - 511), iteration + 1)],
            "checkpoints": [], "producer_pid": os.getpid(), "producer_marker": marker}
    temporary = path.with_suffix('.partial')
    temporary.write_text(json.dumps(data))
    temporary.replace(path)
    iteration += 1
    time.sleep(0.3)
"""


class Producer:
    """An independent trainer stand-in: commits a snapshot every 0.3 s."""

    def __init__(self, progress: Path) -> None:
        self.progress = progress
        self.marker = f"cadex-lifecycle-producer-{os.getpid()}-{time.time_ns()}"
        self.process = subprocess.Popen([sys.executable, "-c", PRODUCER, str(progress), self.marker],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        self.samples: list[int] = []

    def snapshot(self) -> dict:
        deadline = time.monotonic() + 10
        while True:
            try:
                data = json.loads(self.progress.read_text())
                break
            except (OSError, ValueError):
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.05)
        assert data["producer_pid"] == self.process.pid and data["producer_marker"] == self.marker
        self.samples.append(int(data["iteration"]))
        return data

    def alive(self) -> bool:
        return self.process.poll() is None

    def count_processes(self) -> int | None:
        """How many processes carry this producer's marker; ``None`` off Linux."""

        proc = Path("/proc")
        if not proc.is_dir():
            return None
        count = 0
        for entry in proc.iterdir():
            if not entry.name.isdigit():
                continue
            try:
                if self.marker.encode() in (entry / "cmdline").read_bytes():
                    count += 1
            except OSError:
                continue
        return count

    def stop(self) -> None:
        if self.alive():
            self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=10)


class ReviewCommand:
    """One ``cadex review`` process on ``port``; ``url`` once bound."""

    def __init__(self, root: Path, port: int) -> None:
        env = {**os.environ, "PYTHONPATH": str(CLI_DIR)}
        self.process = subprocess.Popen(
            [sys.executable, "-m", "cadex_cli", "review", "--project", str(root),
             "--port", str(port), "--json"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        line = self.process.stderr.readline()
        assert f"review: serving {root.name} at http://127.0.0.1:" in line, line
        self.url = line.split(" at ")[1].split(" ")[0]
        self.port = int(self.url.rstrip("/").rsplit(":", 1)[1])

    def stop(self) -> tuple[int, str]:
        if self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)
        try:
            stdout, stderr = self.process.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            self.process.kill()
            stdout, stderr = self.process.communicate()
        return self.process.returncode, stdout + stderr


def _tree_digest(root: Path, *, ignore: Path) -> dict[str, str]:
    """sha256 of every file under ``root`` except the producer's own output."""

    digests = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not (path.parent == ignore.parent and path.stem == ignore.stem):
            digests[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def _lifecycle_project(tmp_path: Path) -> tuple[Path, dict]:
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg not available")
    root = _review_project(tmp_path)
    _stage_accepted(root, REVISION_B)
    _video_run(root, "sample")
    return root, render(root, "sample")


def _server_video(url: str) -> bytes:
    status, _headers, body = _get(url + "video/run/sample/0")
    assert status == 200
    return body


def _run_identities(url: str) -> dict[str, tuple]:
    """What identifies each run to a reader, from the server's own review."""

    status, _headers, body = _get(url + "api/project")
    assert status == 200
    review = json.loads(body)
    return {run["run"]: (run["model"]["accepted_revision"], run["model"]["digest"], run["relation"],
                         run["outcome"], [video["sha256"] for video in run["videos"]])
            for run in review["runs"]}


@needs_browser
def test_restarting_the_dashboard_keeps_the_review_and_leaves_training_alone(tmp_path, browser: HeadlessBrowser) -> None:
    root, video = _lifecycle_project(tmp_path)
    progress = root / "runs" / "sample" / "train" / "progress.json"
    before = _tree_digest(root, ignore=progress)
    producer = Producer(progress)
    first = ReviewCommand(root, 0)
    second = None
    try:
        producer.snapshot()
        page = _open(browser, first.url)
        # A fresh visit lands on the current run without a click; the same
        # visit after the restart must land on the same one.
        default_before = page.text("#view-kind")
        assert default_before == "RUN second", default_before
        identities_before = _run_identities(first.url)
        assert sorted(identities_before) == ["broken", "first", "sample", "second"]
        page.evaluate("window.cadexReview.select('accepted')", await_promise=True)
        assert page.text("#view-revision") == REVISION_B
        runs_before = page.evaluate("window.cadexReview.state().runs")
        assert sorted(runs_before) == ["broken", "first", "sample", "second"]
        page.click("#views li[data-run='sample']")
        page.wait_for("document.getElementById('telemetry').dataset.state === 'training'")
        page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
        page.evaluate("window.testVideo = document.querySelector('#videos video');"
                      "window.lifecycleMarker = 'opened before restart'; "
                      "testVideo.muted = true; testVideo.loop = true; testVideo.play()", await_promise=True)
        page.wait_for("!testVideo.paused && testVideo.currentTime > 0.1")
        page.wait_for("parseInt(document.querySelector('[data-metric=iteration]').textContent.split(': ')[1]) >= 2")
        shown_before = int(page.text("[data-metric=iteration]").split(": ")[1])
        assert page.attribute("[data-history=loss_curve]", "data-points") == str(shown_before + 1)
        assert page.text("#view-relation").startswith("HISTORICAL — recorded at " + REVISION_A[:12])
        assert _server_video(first.url) == (root / "runs/sample" / video["path"]).read_bytes()

        # Stop the dashboard. The page notices, keeps what it had, and the
        # producer — which the server never knew about — carries on.
        code, output = first.stop()
        assert code == EXIT_OK, output
        page.evaluate("window.cadexReview.refresh()", await_promise=True)
        assert page.attribute("#freshness", "data-state") == "stale"
        assert page.text("#view-revision") == REVISION_A
        assert page.evaluate("document.querySelector('#videos video') === window.testVideo")
        while_down = producer.snapshot()
        time.sleep(0.7)
        assert producer.snapshot()["iteration"] > while_down["iteration"]
        assert producer.alive()

        # Restart it on the same port; the open page recovers on its own poll.
        restart_started = time.monotonic()
        second = ReviewCommand(root, first.port)
        assert second.url == first.url
        page.wait_for("document.getElementById('freshness').dataset.state === 'live'", timeout=10)
        assert page.evaluate("window.lifecycleMarker") == "opened before restart"
        state = page.evaluate("window.cadexReview.state()")
        assert state["selected"] == "sample" and state["revision"] == REVISION_A
        assert sorted(state["runs"]) == sorted(runs_before)
        assert page.text("#view-revision") == REVISION_A
        page.wait_for("parseInt(document.querySelector('[data-metric=iteration]').textContent.split(': ')[1]) > " + str(shown_before))
        assert time.monotonic() - restart_started < 5
        shown_after = int(page.text("[data-metric=iteration]").split(": ")[1])
        assert page.attribute("#telemetry", "data-state") == "training"
        assert page.attribute("[data-history=loss_curve]", "data-points") == str(shown_after + 1)
        assert page.evaluate("document.querySelector('#videos video') === window.testVideo && testVideo.readyState >= 2 && !testVideo.paused")
        playback_time = page.evaluate("testVideo.currentTime")
        page.wait_for("testVideo.currentTime !== " + str(playback_time))
        assert hashlib.sha256(_server_video(second.url)).hexdigest() == video["sha256"]

        # Reopen: a fresh page against the restarted server reads the same project.
        reopened = _open(browser, second.url)
        assert reopened.text("#view-kind") == default_before
        assert _run_identities(second.url) == identities_before
        reopened.evaluate("window.cadexReview.select('accepted')", await_promise=True)
        assert reopened.text("#view-revision") == REVISION_B
        assert REVISION_B[:12] in reopened.text("#accepted-line")
        assert sorted(reopened.evaluate("window.cadexReview.state().runs")) == sorted(runs_before)
        reopened.click("#views li[data-run='sample']")
        reopened.wait_for("document.getElementById('view-revision').textContent === " + json.dumps(REVISION_A))
        assert reopened.text("#view-relation").startswith("HISTORICAL — recorded at " + REVISION_A[:12])
        assert reopened.text("#params tr[data-param='leg_len'] td:nth-child(2)") == "90"
        reopened.wait_for("document.getElementById('telemetry').dataset.state === 'training'")
        reopened.wait_for("parseInt(document.querySelector('[data-metric=iteration]').textContent.split(': ')[1]) > " + str(shown_after))
        points = int(reopened.attribute("[data-history=loss_curve]", "data-points"))
        assert points == int(reopened.text("[data-metric=iteration]").split(": ")[1]) + 1
        reopened.wait_for("document.querySelector('#videos video')?.readyState >= 2")
        assert video["policy_sha256"][:12] in reopened.text("#videos") and "seed 7" in reopened.text("#videos")
        download = reopened.download("#videos a")
        assert hashlib.sha256(download.path.read_bytes()).hexdigest() == video["sha256"]

        # The producer: same process throughout, never restarted, never doubled.
        assert producer.alive()
        final = producer.snapshot()
        assert final["producer_pid"] == producer.process.pid
        assert producer.samples == sorted(producer.samples) and len(set(producer.samples)) == len(producer.samples)
        assert producer.count_processes() in (None, 1)
    finally:
        producer.stop()
        if second is not None:
            code, output = second.stop()
            assert code == EXIT_OK, output
        first.stop()
    assert _tree_digest(root, ignore=progress) == before
    assert producer.process.returncode in (-signal.SIGTERM, 0)


@needs_browser
def test_copied_project_reopens_without_source_and_keeps_edits_isolated(tmp_path, browser):
    """D7 fixture: whole-directory copy, independent edits, offline source."""
    from test_review_record import _manifest

    root, video = _lifecycle_project(tmp_path)
    progress = root / 'runs/sample/train/progress.json'
    progress.write_text(json.dumps({
        'schema': 'cadex-training-progress-v1', 'state': 'done',
        'updated_at': time.time(), 'task_sha256': 't' * 64,
        'iteration': 2, 'total': 2, 'reward_per_step': 0.5,
        'loss': 0.25, 'episode_steps': 14,
        'curve': [[0, 0.1], [1, 0.3], [2, 0.5]],
        'loss_curve': [[0, 1], [1, 0.5], [2, 0.25]],
        'episode_steps_curve': [[0, 12], [1, 13], [2, 14]],
        'checkpoints': [],
    }))
    # No file is excluded: accepted artifacts, assets and retained runs travel.
    before = _tree_digest(root, ignore=root / 'nonexistent')
    copy = tmp_path / 'independent-copy'
    subprocess.run(['cp', '-R', str(root), str(copy)], check=True)
    assert _tree_digest(copy, ignore=copy / 'nonexistent') == before
    source = ReviewCommand(root, 0)
    copied = ReviewCommand(copy, 0)
    try:
        original_page = _open(browser, source.url)
        copied_page = _open(browser, copied.url)
        original_page.evaluate("window.cadexReview.select('accepted')", await_promise=True)
        copied_page.evaluate("window.cadexReview.select('accepted')", await_promise=True)
        assert original_page.text('#view-revision') == REVISION_B
        assert copied_page.text('#view-revision') == REVISION_B
        # Simulate an accepted design change in the copy, without an engine.
        # This proves reader isolation; it does not claim a real design/retrain.
        revision_c = 'c' * 64
        (copy / 'script.py').write_text('# independently revised fixture\n')
        _manifest(copy, revision_c)
        _stage_accepted(copy, revision_c)
        copied_page.evaluate('window.cadexReview.refresh()', await_promise=True)
        copied_page.wait_for("document.getElementById('view-revision').textContent === " + json.dumps(revision_c))
        original_page.evaluate('window.cadexReview.refresh()', await_promise=True)
        assert original_page.text('#view-revision') == REVISION_B
        assert _tree_digest(root, ignore=root / 'nonexistent') == before
        assert source.stop()[0] == EXIT_OK
        unavailable = tmp_path / 'source-unavailable'
        root.rename(unavailable)
        assert not root.exists()
        # A new browser page must resolve every historical artifact in the copy.
        reopened = _open(browser, copied.url)
        reopened.evaluate("window.cadexReview.select('accepted')", await_promise=True)
        assert reopened.text('#view-revision') == revision_c
        assert sorted(reopened.evaluate('window.cadexReview.state().runs')) == ['broken', 'first', 'sample', 'second']
        reopened.click("#views li[data-run='sample']")
        reopened.wait_for("document.getElementById('view-revision').textContent === " + json.dumps(REVISION_A))
        assert reopened.text('#view-relation').startswith('HISTORICAL')
        assert reopened.text("#params tr[data-param='leg_len'] td:nth-child(2)") == '90'
        reopened.wait_for('window.cadexReview.viewer().stats().triangles === 24')
        assert reopened.attribute('#telemetry', 'data-state') == 'done'
        for history in ('curve', 'loss_curve', 'episode_steps_curve'):
            assert reopened.attribute(f'[data-history={history}]', 'data-points') == '3'
        reopened.wait_for("document.querySelector('#videos video')?.readyState >= 2")
        reopened.evaluate("window.copyVideo=document.querySelector('#videos video'); copyVideo.muted=true; copyVideo.loop=true; copyVideo.play()", await_promise=True)
        reopened.wait_for('copyVideo.currentTime > 0.1')
        assert video['policy_sha256'][:12] in reopened.text('#videos')
        download = reopened.download('#videos a')
        assert hashlib.sha256(download.path.read_bytes()).hexdigest() == video['sha256']
        assert hashlib.sha256(_server_video(copied.url)).hexdigest() == video['sha256']
        assert _tree_digest(unavailable, ignore=unavailable / 'nonexistent') == before
        # Historical bytes in the edited copy remain exactly the copied bytes.
        after = _tree_digest(copy, ignore=copy / 'nonexistent')
        for name, digest in before.items():
            if name.startswith(('runs/', 'review/', 'assets/')):
                assert after[name] == digest, name
    finally:
        source.stop()
        code, output = copied.stop()
        assert code == EXIT_OK, output
