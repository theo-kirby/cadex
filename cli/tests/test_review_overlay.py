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

from cadex_cli.activity import activity_path, append_activity, begin_activity
from cadex_cli.review_server import (DESIGNING_WINDOW_S, EVALUATING_WINDOW_S, SPARK_POINTS,
                                     serve)
from test_review_record import REVISION_B
from test_review_server import (_json, _mesh_run, _open, _review_project, _rewrite_record,
                                browser, needs_browser)  # noqa: F401  (fixture)

BIPED = json.loads((Path(__file__).parent / "fixtures" / "biped-progress.json").read_text())
RUN = "biped-train"
ACTIVITY_IDLE_S = 300  # review.js's ACTIVITY_IDLE_S (ADR-550)


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
    assert stage["state"] == "evaluating" and stage["reason"] == "an evaluation is running"
    # Abandoned: nothing written inside the window.
    old = time.time() - EVALUATING_WINDOW_S - 30
    for path in (trace, directory):
        os.utime(path, (old, old))
    assert _stage(root)["state"] != "evaluating"


def test_an_in_flight_evaluate_call_is_the_stage_until_it_returns(tmp_path):
    """Most of an ``evaluate`` through ``cadex mcp`` is the session building the
    design, before any evaluation directory exists; its in-flight activity line
    is what says it is evaluating (ADR-553)."""

    root = _training_project(tmp_path)
    _biped_progress(root, 239, state="done")
    _rewrite_record(root / "runs" / RUN, status="ok")
    started = time.time() - 40
    call = begin_activity(root, "evaluate", {}, now=started)
    stage = _stage(root)
    assert stage["state"] == "evaluating" and stage["reason"] == "the agent's evaluate call is running"
    assert stage["since"] == time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(started)))
    append_activity(root, "evaluate", {}, ok=True, detail="evaluate: fail", ms=41000.0, call=call)
    assert _stage(root)["state"] != "evaluating"
    # Another call in flight is not an evaluation.
    begin_activity(root, "render", {"views": ["iso"]})
    assert _stage(root)["state"] != "evaluating"
    # An evaluate whose server is gone will never return: not evaluating.
    log = activity_path(root)
    gone = json.loads(log.read_text().splitlines()[-1]) | {"tool": "evaluate", "pid": 2 ** 22 + 7, "call": "x-1"}
    with open(log, "a") as handle:
        handle.write(json.dumps(gone) + "\n")
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
    for tool in ("build", "inspect", "measure"):
        append_activity(root, tool, {"scope": "clearance"}, ok=True, detail="", ms=900.0)
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
        assert page.evaluate("document.getElementById('overlay-activity').dataset.state") == "active"
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


ACTIVITY = """(function () {
  function q(s) { return document.querySelector(s); }
  return {state: q('#overlay-activity').dataset.state, line: q('#overlay-activity-line').textContent,
          log_hidden: q('#overlay-activity-log').hidden,
          items: Array.from(document.querySelectorAll('#overlay-activity-list li')).map(function (li) {
            return [li.dataset.outcome, li.textContent]; }),
          line_color: getComputedStyle(q('#overlay-activity-line')).color,
          bad: getComputedStyle(document.documentElement).getPropertyValue('--bad').trim(),
          info: getComputedStyle(document.documentElement).getPropertyValue('--info').trim()};
})()"""


@needs_browser
def test_the_overlay_says_what_the_agent_is_doing_and_when_it_went_quiet(tmp_path, browser) -> None:
    """V4's line (ADR-550): the newest call and how long ago, a short list of the
    ones before it, ``idle`` past :data:`ACTIVITY_IDLE_S`, and a page that
    renders with no log at all, all on the page's own poll."""

    root = _review_project(tmp_path)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        page.evaluate("window.cadexReview.setOverlayCollapsed(false)")
        none = page.evaluate(ACTIVITY)
        assert none["state"] == "none" and none["log_hidden"] and none["items"] == []
        assert none["line"] == "no tool call through cadex mcp has been logged in this project"
        # The agent works: each call lands in the log and the poll carries it.
        append_activity(root, "build", {"source": "x" * 3000}, ok=True, detail="built 4 parts", ms=2100.0)
        page.wait_for("document.getElementById('overlay-activity').dataset.state === 'active'", timeout=10)
        first = page.evaluate(ACTIVITY)
        assert first["line"] == "build source=<3000 chars> · just now" and first["log_hidden"]
        append_activity(root, "inspect", {"scope": "clearance"}, ok=True, detail="", ms=400.0)
        append_activity(root, "set_params", {"values": {"bore": 8}}, ok=False,
                        detail="unknown parameter: bore", ms=12.0)
        page.wait_for("document.getElementById('overlay-activity').dataset.state === 'error'", timeout=10)
        failed = page.evaluate(ACTIVITY)
        assert failed["line"] == "set_params values={bore} · failed: unknown parameter: bore · just now"
        assert failed["line_color"] == _hex_rgb(failed["bad"])
        assert not failed["log_hidden"]
        assert [outcome for outcome, _ in failed["items"]] == ["error", "ok", "ok"]
        assert failed["items"][1][1].endswith("inspect scope=\"clearance\"")
        # Only the newest few are listed.
        for n in range(6):
            append_activity(root, "measure", {"n": n}, ok=True, detail="", ms=5.0)
        page.wait_for("document.querySelectorAll('#overlay-activity-list li').length === 5 && "
                      "document.getElementById('overlay-activity-line').textContent.indexOf('measure n=5') === 0",
                      timeout=10)
        # Quiet past the threshold: the line says idle, not a stale action as current.
        log = activity_path(root)
        log.unlink()
        append_activity(root, "build", {}, ok=True, detail="", ms=10.0, now=time.time() - 3600)
        append_activity(root, "evaluate", {"seeds": [1, 2]}, ok=True, detail="", ms=10.0,
                        now=time.time() - ACTIVITY_IDLE_S - 120)
        page.wait_for("document.getElementById('overlay-activity').dataset.state === 'idle'", timeout=10)
        idle = page.evaluate(ACTIVITY)
        assert idle["line"] == "agent idle · last call evaluate 7 min ago"
        assert [text.split(" ", 1)[1] for _, text in idle["items"]] == ["evaluate seeds=[2]", "build"]
        # The log goes away (a fresh copy): the page shows the absence, not the old line.
        log.unlink()
        page.wait_for("document.getElementById('overlay-activity').dataset.state === 'none'", timeout=10)
        assert page.evaluate(ACTIVITY)["items"] == []
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
def test_an_in_flight_evaluate_reads_evaluating_and_running_never_idle(tmp_path, browser) -> None:
    """ADR-553 on the page: an ``evaluate`` call in flight turns the stage
    ``evaluating`` and the activity line ``running``, however long it has run;
    its return turns both back, on the page's own poll."""

    root = _review_project(tmp_path)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        page.evaluate("window.cadexReview.setOverlayCollapsed(false)")
        append_activity(root, "set_params", {"values": {"foot_w": 38}}, ok=True, detail="", ms=900.0)
        page.wait_for("document.getElementById('overlay-activity').dataset.state === 'active'", timeout=10)
        # Started longer ago than the idle threshold, and still running.
        call = begin_activity(root, "evaluate", {}, now=time.time() - ACTIVITY_IDLE_S - 100)
        page.wait_for("document.getElementById('overlay').dataset.stage === 'evaluating'", timeout=10)
        running = page.evaluate(ACTIVITY) | {"overlay": page.evaluate(OVERLAY)}
        assert running["overlay"]["chip"] == "evaluating"
        assert running["overlay"]["line"] == "the agent's evaluate call is running · 7 min"
        assert running["state"] == "running" and running["line"] == "evaluate · running 7 min"
        assert running["line_color"] == _hex_rgb(running["info"])
        assert running["items"][0][0] == "running" and running["items"][0][1].endswith("evaluate · running")
        assert [outcome for outcome, _ in running["items"]] == ["running", "ok"]
        append_activity(root, "evaluate", {}, ok=True, detail="evaluate: fail", ms=480000.0, call=call)
        page.wait_for("document.getElementById('overlay-activity').dataset.state === 'active'", timeout=10)
        done = page.evaluate(ACTIVITY) | {"overlay": page.evaluate(OVERLAY)}
        assert done["overlay"]["stage"] != "evaluating"
        assert done["line"] == "evaluate · just now"
        assert [outcome for outcome, _ in done["items"]] == ["ok", "ok"]
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
def test_the_evaluate_call_names_the_stage_once_its_directory_exists(tmp_path, browser) -> None:
    """W1's ``evaluate`` wrote its evaluation directory part-way through the
    call, and the line then named that directory's id. The agent's call wins,
    and a directory alone reads without its id (ADR-555)."""

    root = _training_project(tmp_path)
    _biped_progress(root, 239, state="done")
    _rewrite_record(root / "runs" / RUN, status="ok")
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        call = begin_activity(root, "evaluate", {}, now=time.time() - 65)
        page.wait_for("document.getElementById('overlay').dataset.stage === 'evaluating'", timeout=10)
        assert page.evaluate(OVERLAY)["line"] == "the agent's evaluate call is running · 1 min"
        # The evaluation's own directory appears; the call is still in flight.
        directory = root / "evaluations" / "dc0af1158165-d3a4c0ffee00"
        directory.mkdir(parents=True)
        (directory / "seed-1101-trace.json").write_text("{}")
        assert _json(server.url + "api/project")["stage"]["reason"] == "the agent's evaluate call is running"
        time.sleep(5)  # two of the page's polls with the directory on disk
        during = page.evaluate(OVERLAY)
        assert during["stage"] == "evaluating"
        assert during["line"] == "the agent's evaluate call is running · 1 min"
        assert "dc0af1158165" not in during["line"]
        # The call returns while the directory is still fresh: it alone reads without its id.
        append_activity(root, "evaluate", {}, ok=True, detail="evaluate: pass", ms=66000.0, call=call)
        page.wait_for("document.getElementById('overlay-line').textContent.indexOf('an evaluation is running') === 0",
                      timeout=10)
        assert "dc0af1158165" not in page.evaluate(OVERLAY)["line"]
    finally:
        server.shutdown()
        server.server_close()


def test_the_idle_threshold_here_is_the_pages():
    page = (Path(__file__).resolve().parents[1] / "cadex_cli" / "review_static" / "review.js").read_text()
    assert f"var ACTIVITY_IDLE_S = {ACTIVITY_IDLE_S}," in page
