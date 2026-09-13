# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Bounded operation over a long run history (ADR-321).

A project that has been trained many times has many runs, each with a
512-sample history and a checkpoint list. The dashboard polls the run list
every two seconds, so what that list costs is what the whole review costs.
These tests lay out sixty-odd runs, each with full histories and verified
checkpoints, and pin three things: the list carries a bounded summary per
run rather than every run's histories and hashed checkpoints; the page's
idle poll touches a constant number of DOM nodes however long the list is;
and a deliberately selected historical run — with its video playing — stays
selected, with its own histories, while the list grows and a newer run's
telemetry grows underneath it. The browser half skips without a Chromium and
FFmpeg, like the rest of the dashboard's browser suite.
"""

from __future__ import annotations

import json
import shutil
import statistics
import time

import pytest

from cadex_cli.review_server import serve
from test_review_record import REVISION_A, REVISION_B
from test_review_server import (
    _checkpoint,
    _get,
    _json,
    _mesh_run,
    _open,
    _review_project,
    _rewrite_record,
    _telemetry,
    browser,  # noqa: F401  (fixture)
    needs_browser,
)

HISTORY = 60
POINTS = 512
CHECKPOINTS = 3
#: Bytes one run may cost in the list, record and telemetry summary together.
LIST_BYTES_PER_RUN = 12_000
#: Bytes one run's telemetry summary may cost in the list.
SUMMARY_BYTES = 1_500


def _history_run(root, name, *, revision, stamp, state="done", iteration=POINTS - 1, status="ok"):
    """A walked run with a full history and verified checkpoints, recorded at ``stamp``."""

    run = _mesh_run(root, name, revision=revision)
    checkpoints = [_checkpoint(root, name, name=f"iter-{i}.cxpolicy", payload=f"{name} checkpoint {i}".encode())
                   for i in range(CHECKPOINTS)]
    _telemetry(root, iteration, run=name, state=state, checkpoints=checkpoints)
    changes = {"recorded_at": stamp}
    if status != "ok":
        changes["status"] = status
    _rewrite_record(run, **changes)
    return run


def _long_history(tmp_path, *, video_run=None):
    root = _review_project(tmp_path)
    for i in range(HISTORY):
        name = f"hist-{i:03d}"
        if name == video_run:
            from test_video import _video_run
            _video_run(root, name)
            checkpoints = [_checkpoint(root, name, name=f"iter-{k}.cxpolicy", payload=f"{name} checkpoint {k}".encode())
                           for k in range(CHECKPOINTS)]
            _telemetry(root, POINTS - 1, run=name, state="done", checkpoints=checkpoints)
            _rewrite_record(root / "runs" / name, recorded_at=f"2030-01-01T00:{i // 60:02d}:{i % 60:02d}Z")
        else:
            _history_run(root, name, revision=REVISION_A, stamp=f"2030-01-01T00:{i // 60:02d}:{i % 60:02d}Z")
    return root


@pytest.fixture
def long_history(tmp_path):
    root = _long_history(tmp_path)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        yield root, server
    finally:
        server.shutdown()
        server.server_close()


def test_the_run_list_carries_a_bounded_telemetry_summary_per_run(long_history):
    root, server = long_history
    timings = []
    for _ in range(5):
        started = time.perf_counter()
        status, _headers, body = _get(server.url + "api/project")
        timings.append(time.perf_counter() - started)
        assert status == 200
    review = json.loads(body)
    runs = review["runs"]
    assert len(runs) == HISTORY + 3
    assert len(body) < LIST_BYTES_PER_RUN * len(runs)
    history = [run for run in runs if run["run"].startswith("hist-")]
    for run in history:
        telemetry = run["telemetry"]
        assert telemetry["summary"] is True
        assert telemetry["state"] == "done"
        assert telemetry["iteration"] == POINTS - 1
        assert telemetry["samples"] == {"curve": POINTS, "loss_curve": POINTS, "episode_steps_curve": POINTS}
        assert telemetry["checkpoints_reported"] == CHECKPOINTS
        assert "curve" not in telemetry and "checkpoints" not in telemetry
        assert telemetry["checkpoint_source"]["state"] == "none"
        assert len(json.dumps(telemetry)) < SUMMARY_BYTES
        assert len(json.dumps(run)) < LIST_BYTES_PER_RUN
    # The summary agrees with the detail on state and metrics, and the detail
    # alone carries the histories and the digest-verified checkpoints.
    detail = _json(server.url + "api/run/hist-007")["telemetry"]
    assert "summary" not in detail
    assert detail["state"] == "done" and detail["iteration"] == POINTS - 1
    assert all(len(detail[key]) == POINTS for key in ("curve", "loss_curve", "episode_steps_curve"))
    assert [item["status"] for item in detail["checkpoints"]] == ["retained"] * CHECKPOINTS
    assert len(json.dumps(detail)) > 10 * SUMMARY_BYTES
    # Missing, invalid and mismatched telemetry keep their states in the summary.
    (root / "runs/hist-001/train/progress.json").write_text("{broken")
    (root / "runs/hist-002/train/progress.json").unlink()
    _telemetry(root, 3, run="hist-003", task_sha256="x" * 64)
    by_name = {run["run"]: run["telemetry"] for run in _json(server.url + "api/project")["runs"]}
    assert by_name["hist-001"]["state"] == "invalid" and by_name["hist-001"]["samples"]["curve"] == 0
    assert by_name["hist-002"]["state"] == "missing" and by_name["hist-002"]["checkpoints_reported"] == 0
    assert by_name["hist-003"]["state"] == "invalid" and "mismatch" in by_name["hist-003"]["reason"]
    print(f"\nlist bytes={len(body)} runs={len(runs)} median_s={statistics.median(timings):.3f}")
    assert statistics.median(timings) < 2.0


def test_default_run_reads_the_summary_state(long_history):
    root, server = long_history
    from cadex_cli.review_server import default_run

    assert default_run(_json(server.url + "api/project")) == f"hist-{HISTORY - 1:03d}"
    _history_run(root, "active", revision=REVISION_B, stamp="2029-01-01T00:00:00Z",
                 state="training", iteration=4, status="running")
    assert default_run(_json(server.url + "api/project")) == "active"


OBSERVE = ("window.__added = 0; window.__observer = new MutationObserver(function (records) {"
           " records.forEach(function (r) { window.__added += r.addedNodes.length; }); });"
           " window.__observer.observe(document.body, {childList: true, subtree: true}); true")


def _idle_poll_additions(page):
    page.evaluate("window.__added = 0")
    page.evaluate("window.cadexReview.refresh()", await_promise=True)
    return page.evaluate("window.__added")


@needs_browser
def test_browser_long_history_keeps_selection_and_playback_with_bounded_poll_work(tmp_path, browser):
    from cadex_cli.video import render as render_video

    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg not available")
    root = _long_history(tmp_path, video_run="hist-007")
    render_video(root, "hist-007")
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        newest = f"hist-{HISTORY - 1:03d}"
        assert page.evaluate("document.querySelectorAll('#views li').length") == HISTORY + 4
        assert page.text("#view-kind") == f"RUN {newest}"
        page.wait_for("document.getElementById('telemetry').dataset.detail === 'loaded'")
        assert page.attribute("[data-history=curve]", "data-points") == str(POINTS)
        assert page.evaluate("document.querySelectorAll('#checkpoints li[data-status=retained]').length") == CHECKPOINTS

        # A deliberate historical selection, with its video playing.
        page.click("#views li[data-run='hist-007']")
        page.wait_for("document.getElementById('view-kind').textContent === 'RUN hist-007'")
        assert page.text("#view-relation").startswith("HISTORICAL")
        page.wait_for("document.getElementById('telemetry').dataset.detail === 'loaded'")
        assert page.attribute("[data-history=loss_curve]", "data-points") == str(POINTS)
        assert page.evaluate("window.cadexReview.state().detail") == "hist-007"
        page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
        page.evaluate("window.playing = document.querySelector('#videos video'); playing.muted = true; playing.loop = true; playing.play()",
                      await_promise=True)
        page.wait_for("playing.currentTime > 0.1")

        page.evaluate(OBSERVE)
        added_before = _idle_poll_additions(page)
        cost_before = page.evaluate("window.cadexReview.lastPoll()")
        assert cost_before["project_bytes"] < LIST_BYTES_PER_RUN * (HISTORY + 3)
        assert cost_before["detail_bytes"] > 10 * SUMMARY_BYTES

        # The history grows by a third, and the newest run is training.
        growth = 20
        for i in range(growth):
            name = f"grow-{i:02d}"
            last = i == growth - 1
            _history_run(root, name, revision=REVISION_B, stamp=f"2031-01-01T00:00:{i:02d}Z",
                         state="training" if last else "done", iteration=9 if last else POINTS - 1,
                         status="running" if last else "ok")
        page.evaluate("window.cadexReview.refresh()", await_promise=True)
        assert page.evaluate("document.querySelectorAll('#views li').length") == HISTORY + growth + 4
        assert page.text("#current-run") == f"Current run: grow-{growth - 1:02d}"
        assert page.text("#view-kind") == "RUN hist-007"
        assert page.text("#view-relation").startswith("HISTORICAL")
        assert page.evaluate("playing === document.querySelector('#videos video') && !playing.paused")
        assert page.attribute("[data-history=curve]", "data-points") == str(POINTS)
        # The current run's telemetry grows under the historical selection.
        _telemetry(root, 99, run=f"grow-{growth - 1:02d}", state="training",
                   checkpoints=[_checkpoint(root, f"grow-{growth - 1:02d}", name="iter-0.cxpolicy",
                                            payload=f"grow-{growth - 1:02d} checkpoint 0".encode())])
        added_after = _idle_poll_additions(page)
        cost_after = page.evaluate("window.cadexReview.lastPoll()")
        assert page.text("#view-kind") == "RUN hist-007"
        assert page.evaluate("!playing.paused")
        assert added_after <= added_before + 10, (added_before, added_after)
        assert added_after < 400
        assert cost_after["project_bytes"] < LIST_BYTES_PER_RUN * (HISTORY + growth + 3)
        print(f"\nidle poll nodes added: {added_before} -> {added_after}; "
              f"list bytes {cost_before['project_bytes']} -> {cost_after['project_bytes']}; "
              f"detail bytes {cost_before['detail_bytes']}; poll ms {cost_before['ms']:.0f} -> {cost_after['ms']:.0f}")

        # A fresh visit selects the training run; the route back to current works.
        fresh = _open(browser, server.url)
        assert fresh.text("#view-kind") == f"RUN grow-{growth - 1:02d}"
        page.click("#current-run")
        page.wait_for("document.getElementById('view-kind').textContent === " + json.dumps(f"RUN grow-{growth - 1:02d}"))
        page.wait_for("document.getElementById('telemetry').dataset.detail === 'loaded' && "
                      "document.querySelector('[data-history=curve]').dataset.points === '100'")
        started = time.monotonic()
        _telemetry(root, POINTS - 1, run=f"grow-{growth - 1:02d}", state="training")
        page.wait_for("document.querySelector('[data-metric=iteration]').textContent === " + json.dumps(f"iteration: {POINTS - 1}"))
        assert time.monotonic() - started < 5
        assert page.attribute("[data-history=curve]", "data-points") == str(POINTS)
        assert page.attribute("#telemetry", "data-state") == "training"

        # Back to the historical run: its own histories and video, unchanged.
        page.click("#views li[data-run='hist-007']")
        page.wait_for("document.getElementById('view-kind').textContent === 'RUN hist-007'")
        page.wait_for("document.getElementById('telemetry').dataset.detail === 'loaded'")
        assert page.attribute("[data-history=curve]", "data-points") == str(POINTS)
        assert page.text("#view-relation").startswith("HISTORICAL")
        page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
    finally:
        server.shutdown()
        server.server_close()
