# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The 3D viewport's stage overlay (ADR-542, orun3 V1).

``/api/project`` carries ``stage``: what the project is doing (idle,
designing, training, evaluating, failed), the run the page reads, and that
run's telemetry with bounded reward and loss sparklines. The server half is
pinned here without a browser; with a Chromium the page is driven while the
biped fixture's ``progress.json`` is rewritten under it, on the page's own
poll, and the expanded overlay is measured at 390 px wide.

The fixture is the real biped's curves (``fixtures/biped-progress.json``,
from ``ot5-biped``'s ``probe3-final``), written a prefix at a time as a
training run would.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from cadex_cli.review_server import (DESIGNING_WINDOW_S, EVALUATING_WINDOW_S, SPARK_POINTS,
                                     serve)
from test_review_record import REVISION_B
from test_review_server import (_json, _mesh_run, _open, _review_project, _rewrite_record,
                                browser, needs_browser)  # noqa: F401  (fixture)

BIPED = json.loads((Path(__file__).parent / "fixtures" / "biped-progress.json").read_text())
RUN = "biped-train"


def _biped_progress(root: Path, iteration: int, *, state: str = "training", **changes) -> Path:
    """The biped's ``progress.json`` as the trainer writes it after ``iteration``."""

    done = iteration + 1
    curve = BIPED["curve"][:done]
    best = max(curve, key=lambda point: point[1]) if curve else None
    data = {"schema": BIPED["schema"], "state": state, "iteration": iteration, "total": BIPED["total"],
            "updated_at": time.time(), "task_sha256": "t" * 64, "device": "gpu",
            "wall_time_s": 4.0 * done, "eta_s": 4.0 * (BIPED["total"] - done),
            "reward_per_step": curve[-1][1] if curve else None,
            "loss": BIPED["loss_curve"][iteration][1] if curve else None,
            "curve": curve, "loss_curve": BIPED["loss_curve"][:done],
            "episode_steps_curve": BIPED["episode_steps_curve"][:done],
            "best_iteration": best[0] if best else -1,
            "best_reward_per_step": best[1] if best else None,
            "checkpoints": [], "error": "", "warning": ""}
    data.update(changes)
    path = root / "runs" / RUN / "train" / "progress.json"
    partial = path.with_suffix(".partial")
    partial.write_text(json.dumps(data))
    partial.replace(path)
    return path


def _training_project(tmp_path: Path) -> Path:
    """The review fixture with a biped training run going on at revision B."""

    root = _review_project(tmp_path)
    for older in ("first", "second", "broken"):
        _rewrite_record(root / "runs" / older, recorded_at="2026-09-01T00:00:00Z")
    run = _mesh_run(root, RUN, revision=REVISION_B)
    _rewrite_record(run, status="running")
    _biped_progress(root, 39)
    return root


def _history(root: Path, saved_at: str) -> None:
    (root / "script_history").mkdir(exist_ok=True)
    (root / "script_history" / "history.json").write_text(json.dumps({"entries": [
        {"ordinal": 1, "revision": "a" * 64, "saved_at": "2026-09-01T00:00:00Z", "outputs": {}},
        {"ordinal": 2, "revision": REVISION_B, "saved_at": saved_at, "outputs": {}}]}))


def _stage(root: Path) -> dict:
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        return _json(server.url + "api/project")["stage"]
    finally:
        server.shutdown()
        server.server_close()


def _iso(seconds_ago: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - seconds_ago))


def test_a_training_run_is_the_stage_with_its_numbers_and_bounded_sparklines(tmp_path):
    root = _training_project(tmp_path)
    _biped_progress(root, 199)
    stage = _stage(root)
    assert stage["state"] == "training" and stage["run"] == RUN and stage["runs"] == 4
    t = stage["training"]
    assert (t["iteration"], t["total"], t["eta_s"]) == (199, 240, 4.0 * 40)
    best = max(BIPED["curve"][:200], key=lambda p: p[1])
    assert (t["best_iteration"], t["best_reward_per_step"]) == (best[0], best[1])
    # 200 samples become at most SPARK_POINTS, the first and the newest kept.
    for key, history in (("curve", BIPED["curve"]), ("loss_curve", BIPED["loss_curve"])):
        points = t["spark"][key]
        assert len(points) == SPARK_POINTS
        assert points[0][0] == 0 and points[-1][0] == 199
        assert points[-1][1] == pytest.approx(history[199][1], rel=1e-4)
    assert t["warning"] == ""


def test_the_collapse_warning_and_a_quiet_trainer_reach_the_stage(tmp_path):
    root = _training_project(tmp_path)
    _biped_progress(root, 60, warning="episode_collapse: mean episode 3 steps")
    assert _stage(root)["training"]["warning"] == "episode_collapse: mean episode 3 steps"
    _biped_progress(root, 60, updated_at=time.time() - 120)
    stage = _stage(root)
    assert stage["state"] == "training" and stage["training"]["state"] == "stale"
    assert "no telemetry update" in stage["reason"]


def test_a_failed_run_is_the_stage_until_a_revision_is_accepted_after_it(tmp_path):
    root = _training_project(tmp_path)
    _rewrite_record(root / "runs" / RUN, status="failed", error="the trainer ran out of memory",
                    recorded_at=_iso(30))
    _biped_progress(root, 80, state="failed", error="the trainer ran out of memory")
    _history(root, _iso(3600))
    stage = _stage(root)
    assert stage["state"] == "failed" and stage["reason"] == "the trainer ran out of memory"
    _history(root, _iso(5))
    stage = _stage(root)
    assert stage["state"] == "designing" and stage["reason"] == "revision 2 accepted"
    # The run it read is still named, with its last numbers.
    assert stage["run"] == RUN and stage["training"]["state"] == "failed"


def test_designing_turns_idle_once_the_window_passes(tmp_path):
    root = _review_project(tmp_path)
    _history(root, _iso(DESIGNING_WINDOW_S - 60))
    assert _stage(root)["state"] == "designing"
    _history(root, _iso(DESIGNING_WINDOW_S + 60))
    stage = _stage(root)
    assert stage["state"] == "idle" and stage["since"].startswith(_iso(DESIGNING_WINDOW_S + 60)[:16])


def test_an_evaluation_without_its_report_is_the_stage_while_it_writes(tmp_path):
    root = _training_project(tmp_path)
    _biped_progress(root, 239, state="done")
    _rewrite_record(root / "runs" / RUN, status="ok")
    directory = root / "evaluations" / "bbbbbbbbbbbb-cccccccccccc"
    directory.mkdir(parents=True)
    trace = directory / "seed-1101-trace.json"
    trace.write_text("{}")
    stage = _stage(root)
    assert stage["state"] == "evaluating" and "bbbbbbbbbbbb-cccccccccccc" in stage["reason"]
    # Abandoned: nothing written inside the window.
    old = time.time() - EVALUATING_WINDOW_S - 30
    for path in (trace, directory):
        os.utime(path, (old, old))
    assert _stage(root)["state"] != "evaluating"


def test_a_project_with_no_runs_has_a_stage_and_no_training(tmp_path):
    from test_review_record import _manifest, _project
    root = _project(tmp_path)
    _manifest(root, REVISION_B)
    stage = _stage(root)
    assert stage == {"state": "idle", "reason": "", "since": None, "run": None, "runs": 0, "training": None,
                     "checkpoints": None}


# -- the page --------------------------------------------------------------------

OVERLAY = """(function () {
  function q(s) { return document.querySelector(s); }
  var box = q('#overlay').getBoundingClientRect(), model = q('#model').getBoundingClientRect();
  return {stage: q('#overlay').dataset.stage, collapsed: q('#overlay').dataset.collapsed,
          line: q('#overlay-line').textContent, chip: q('#overlay-stage').textContent,
          run: q('#overlay-run').hidden ? null : q('#overlay-run').textContent,
          best: q('#overlay-best').textContent, eta: q('#overlay-eta').textContent,
          reward: q('#overlay-reward polyline').getAttribute('points') || '',
          warning: q('#overlay-warning').hidden ? null : q('#overlay-warning').textContent,
          warning_color: getComputedStyle(q('#overlay-warning')).color,
          warn: getComputedStyle(document.documentElement).getPropertyValue('--warn').trim(),
          overlay: {width: box.width, height: box.height, x: box.x, y: box.y, right: box.right, bottom: box.bottom},
          model: {width: model.width, height: model.height, x: model.x, y: model.y, right: model.right, bottom: model.bottom}};
})()"""


def _hex_rgb(value: str) -> str:
    return "rgb(%d, %d, %d)" % tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


@needs_browser
def test_the_overlay_follows_progress_json_on_the_pages_own_poll(tmp_path, browser) -> None:
    root = _training_project(tmp_path)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        page.evaluate("window.cadexReview.setOverlayCollapsed(false)")
        page.wait_for("document.getElementById('overlay').dataset.stage === 'training'")
        first = page.evaluate(OVERLAY)
        assert first["chip"] == "training" and first["line"].startswith("iteration 40 / 240")
        assert first["run"] == "run " + RUN  # four runs: it says which it reads
        assert first["reward"] and first["warning"] is None
        # The trainer writes on; the page's 2 s poll, not a reload, carries it.
        _biped_progress(root, 159)
        page.wait_for("document.getElementById('overlay-line').textContent.indexOf('iteration 160 / 240') === 0",
                      timeout=10)
        second = page.evaluate(OVERLAY)
        assert second["reward"] != first["reward"] and second["best"] != first["best"]
        assert second["eta"] == "5 min"
        _biped_progress(root, 170, warning="episode_collapse: mean episode 3 steps")
        page.wait_for("!document.getElementById('overlay-warning').hidden", timeout=10)
        warned = page.evaluate(OVERLAY)
        assert warned["warning"] == "episode_collapse: mean episode 3 steps"
        assert warned["warning_color"] == _hex_rgb(warned["warn"])
        # Done: the run's numbers stay, the stage moves on.
        _biped_progress(root, 239, state="done")
        _rewrite_record(root / "runs" / RUN, status="ok")
        page.wait_for("document.getElementById('overlay').dataset.stage !== 'training'", timeout=10)
        assert page.evaluate(OVERLAY)["run"] == "run " + RUN + " · done"
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
def test_the_overlay_collapses_per_browser_and_covers_a_quarter_at_390px(tmp_path, browser) -> None:
    root = _training_project(tmp_path)
    _biped_progress(root, 120, warning="episode_collapse: mean episode 3 steps")
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = browser.page("about:blank")
        page.send("Emulation.setDeviceMetricsOverride",
                  {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
        page.send("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 5})
        page.send("Page.navigate", {"url": server.url})
        page.wait_for("document.readyState === 'complete' && !!window.cadexReview")
        page.evaluate("window.cadexReview.ready", await_promise=True)
        page.evaluate("window.cadexReview.setOverlayCollapsed(false)")
        page.wait_for("document.getElementById('overlay').dataset.stage === 'training'")
        m = page.evaluate(OVERLAY)
        o, v = m["overlay"], m["model"]
        assert v["width"] == 390
        # Inside the viewport, and at most a quarter of it, with every row showing.
        assert o["x"] >= v["x"] and o["right"] <= v["right"] and o["y"] >= v["y"] and o["bottom"] <= v["bottom"]
        share = o["width"] * o["height"] / (v["width"] * v["height"])
        assert share <= 0.25, share
        assert m["warning"] and m["reward"]
        assert page.evaluate("document.documentElement.scrollWidth") <= 390
        # One tap collapses it to one line, and this browser keeps that.
        page.evaluate("document.getElementById('overlay-toggle').click()")
        collapsed = page.evaluate(OVERLAY)
        assert collapsed["collapsed"] == "true" and collapsed["overlay"]["height"] <= 48
        page.send("Page.reload", {})
        page.wait_for("document.readyState === 'complete' && !!window.cadexReview")
        page.evaluate("window.cadexReview.ready", await_promise=True)
        assert page.evaluate(OVERLAY)["collapsed"] == "true"
        page.evaluate("window.cadexReview.setOverlayCollapsed(false)")
        print(json.dumps({"overlay_390": {"expanded_px": [round(o["width"]), round(o["height"])],
                                          "viewport_px": [round(v["width"]), round(v["height"])],
                                          "share": round(share, 4),
                                          "collapsed_height_px": round(collapsed["overlay"]["height"])}}))
    finally:
        server.shutdown()
        server.server_close()
