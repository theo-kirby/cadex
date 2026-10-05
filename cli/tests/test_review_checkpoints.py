# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Each checkpoint's rollout, played in the 3D viewport (ADR-545, orun3 V2).

``/api/project``'s ``stage.checkpoints`` lists the read run's rolled-out
checkpoints (ADR-544 writes them) and ``/api/playback/checkpoint/<run>/<stem>``
serves one through ``trace_playback``. The server half is pinned here with
hand-written traces and no engine. The browser half runs the biped's real
checkpoints through the real engine while a trainer is still running, and
watches the page follow them: the newest loops, a second replaces the first,
a picked one stays, and a failed rollout is shown with its reason.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys
import textwrap
import threading
import time

import pytest

from cadex_cli.checkpoints import CheckpointRollouts
from cadex_cli.review_record import write_run_record
from cadex_cli.review_server import CHECKPOINTS_LISTED, TRACE_SCHEMA, serve
from cadex_cli.smoke import smoke_interpreter
from cadex_cli.train import run_trainer
from test_checkpoint_rollouts import BIPED, LINKS, MODEL, TASK, _policies
from test_review_record import REVISION_B, _manifest, _project
from test_review_server import (_cube_stl, _get, _json, _model_state, _open, _stage_accepted,
                                browser, needs_browser)  # noqa: F401  (fixture)

RUN = "orun3-biped-train"
DIGEST = "d" * 64


def _training_run(root: Path) -> Path:
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


def _progress(train: Path, iteration: int, rows: list[dict], *, state: str = "training") -> None:
    payload = {"schema": "cadex-training-progress-v1", "state": state, "iteration": iteration,
               "total": 60, "updated_at": time.time(), "curve": [], "loss_curve": [],
               "episode_steps_curve": [], "checkpoints": rows, "error": "", "warning": ""}
    (train / "progress.json.partial").write_text(json.dumps(payload))
    (train / "progress.json.partial").replace(train / "progress.json")


def _trace(tag: str, iteration: int, reward: float, frames: int = 3) -> dict:
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


def _served(root: Path):
    server, _thread = serve(root, "127.0.0.1", 0)
    return server


# -- the server --------------------------------------------------------------


def test_the_stage_lists_the_read_runs_checkpoints_oldest_first_with_failures_and_pending(tmp_path):
    root = _project(tmp_path)
    _manifest(root, REVISION_B)
    train = _training_run(root) / "train"
    (train / "walk.000040.rollout-trace.json").write_text(json.dumps(_trace("000040", 39, 1.25)))
    (train / "walk.000020.rollout-trace.json").write_text(json.dumps(_trace("000020", 19, 0.5)))
    (train / "walk.000060.rollout-failed.json").write_text(json.dumps({
        "schema": "cadex-checkpoint-rollout-failure-v1", "checkpoint": "walk.000060.cxpolicy",
        "tag": "000060", "iteration": 59, "reason": "child_failed", "error": "the rollout exited 1"}))
    (train / "walk.000080.cxpolicy").write_bytes(b"not yet rolled out")
    # Neither is a numbered checkpoint's rollout.
    (train / "walk.best.cxpolicy").write_bytes(b"best")
    (train / "walk.cxpolicy").write_bytes(b"final")
    server = _served(root)
    try:
        stage = _json(server.url + "api/project")["stage"]
        assert stage["state"] == "training" and stage["run"] == RUN
        block = stage["checkpoints"]
        assert [(i["stem"], i["state"], i["iteration"]) for i in block["items"]] == [
            ("walk.000020", "ready", 19), ("walk.000040", "ready", 39), ("walk.000060", "failed", 59)]
        assert block["pending"] == 1 and block["listed_of"] == 3
        ready, failed = block["items"][1], block["items"][2]
        assert ready["reward_per_step"] == 1.25 and ready["duration_s"] == pytest.approx(0.08)
        assert ready["url"] == f"api/playback/checkpoint/{RUN}/walk.000040"
        assert failed["url"] is None
        assert (failed["reason"], failed["error"]) == ("child_failed", "the rollout exited 1")

        played = _json(server.url + ready["url"].lstrip("/"))
        assert played["available"] and played["stem"] == "walk.000040"
        assert played["checkpoint"]["iteration"] == 39
        assert played["times_s"] == pytest.approx([0.0, 0.04, 0.08])
        assert played["source"] == f"runs/{RUN}/train/walk.000040.rollout-trace.json"
        refused = _json(server.url + f"api/playback/checkpoint/{RUN}/walk.000060")
        assert refused["available"] is False and refused["reason"] == "child_failed: the rollout exited 1"
        # Only a rolled-out numbered checkpoint of a run in this project.
        for path in (f"{RUN}/walk.000080", f"{RUN}/walk.best", f"{RUN}/walk.000020.rollout-trace.json",
                     f"{RUN}/..%2Fwalk.000020", "elsewhere/walk.000020"):
            status, _headers, _body = _get(server.url + "api/playback/checkpoint/" + path)
            assert status == 404, path
    finally:
        server.shutdown()
        server.server_close()


def test_the_listing_is_bounded_and_a_reparse_needs_a_changed_trace(tmp_path, monkeypatch):
    root = _project(tmp_path)
    _manifest(root, REVISION_B)
    train = _training_run(root) / "train"
    for number in range(1, CHECKPOINTS_LISTED + 6):
        tag = "%06d" % (number * 5)
        (train / f"walk.{tag}.rollout-trace.json").write_text(json.dumps(_trace(tag, number * 5 - 1, 0.1)))
    from cadex_cli import review_server
    server = _served(root)
    try:
        block = _json(server.url + "api/project")["stage"]["checkpoints"]
        assert len(block["items"]) == CHECKPOINTS_LISTED and block["listed_of"] == CHECKPOINTS_LISTED + 5
        assert block["items"][-1]["tag"] == "%06d" % ((CHECKPOINTS_LISTED + 5) * 5)
        reads = []
        real = review_server._load_json
        monkeypatch.setattr(review_server, "_load_json",
                            lambda path, *a, **k: (reads.append(Path(path).name), real(path, *a, **k))[1])
        _json(server.url + "api/project")
        assert not [name for name in reads if name.endswith("rollout-trace.json")]
    finally:
        server.shutdown()
        server.server_close()


def test_a_run_with_no_checkpoints_says_so_and_a_project_with_no_runs_has_none(tmp_path):
    root = _project(tmp_path)
    _manifest(root, REVISION_B)
    server = _served(root)
    try:
        assert _json(server.url + "api/project")["stage"]["checkpoints"] is None
        _training_run(root)
        block = _json(server.url + "api/project")["stage"]["checkpoints"]
        assert block["items"] == [] and block["pending"] == 0
        assert block["reason"] == "no checkpoint rolled out yet"
    finally:
        server.shutdown()
        server.server_close()


# -- the page, against the real engine, while a trainer runs ------------------

#: A trainer with the real one's checkpoint contract (each checkpoint written
#: atomically, then named in ``progress.json`` with its digest) that the test
#: steps: after each checkpoint is rolled out (or has failed) it waits for
#: ``go-<n>``, and it ends only on ``finish``. Whatever the page shows
#: before ``finish`` it shows while the trainer is still running.
STEPPED_TRAINER = textwrap.dedent(
    """
    import hashlib, json, sys, time
    from pathlib import Path
    argv = sys.argv[1:]
    out = Path(argv[argv.index("--out") + 1])
    gate = Path(argv[argv.index("--gate") + 1])
    blobs = [Path(p).read_bytes() for p in argv[argv.index("--checkpoints") + 1].split(",")]
    final = Path(argv[argv.index("--final") + 1]).read_bytes()

    def wait(path):
        deadline = time.monotonic() + 120
        while not path.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        return path.exists()

    rows = []
    for number, blob in enumerate(blobs, start=1):
        tag = "%06d" % (number * 20)
        path = out.with_name(f"{out.stem}.{tag}{out.suffix}")
        path.with_name(path.name + ".partial").write_bytes(blob)
        path.with_name(path.name + ".partial").replace(path)
        rows.append({"tag": tag, "iteration": number * 20 - 1, "path": path.name,
                     "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest(),
                     "reward_per_step": 0.25 * number})
        progress = {"schema": "cadex-training-progress-v1", "state": "training",
                    "iteration": number * 20 - 1, "total": 60, "updated_at": time.time(),
                    "curve": [], "loss_curve": [], "episode_steps_curve": [],
                    "checkpoints": rows, "error": "", "warning": ""}
        (out.parent / "progress.json.partial").write_text(json.dumps(progress))
        (out.parent / "progress.json.partial").replace(out.parent / "progress.json")
        stem = f"{out.stem}.{tag}"
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline and not any(
                out.with_name(stem + suffix).exists()
                for suffix in (".rollout-trace.json", ".rollout-failed.json")):
            time.sleep(0.05)
        print(f"checkpoint {tag} rolled out", file=sys.stderr, flush=True)
        wait(gate / f"go-{number}")
    wait(gate / "finish")
    out.write_bytes(final)
    print(json.dumps({"out": str(out), "bytes": len(final),
                      "sha256": hashlib.sha256(final).hexdigest(), "wall_time_s": 0.0}))
    """
)

PLAYING = "(function(){var p=window.cadexReview.playback();return p&&p.playing&&p.looping?p.checkpoint:null;})()"


@needs_browser
def test_the_newest_checkpoint_loops_and_a_second_replaces_it_while_the_run_trains(
        engine, tmp_path, browser) -> None:
    good_1, good_2, good_3, final = _policies(tmp_path, 4)
    root = _project(tmp_path)
    _manifest(root, REVISION_B)
    _stage_accepted(root, REVISION_B)
    train = _training_run(root) / "train"
    blobs = tmp_path / "blobs"
    blobs.mkdir()
    # The third checkpoint is not a policy: its rollout fails in the engine.
    for name, data in (("c1", good_1), ("c2", good_2), ("c3", b"not a policy"), ("c4", good_3),
                       ("final", final)):
        (blobs / name).write_bytes(data)
    gate = tmp_path / "gate"
    gate.mkdir()
    script = tmp_path / "trainer.py"
    script.write_text(STEPPED_TRAINER)
    watcher = CheckpointRollouts(train, output="walk", bundle=train / TASK, model=train / MODEL,
                                 python=smoke_interpreter(engine), module_dir=engine.module_dir,
                                 scan_s=0.0)
    receipt: dict = {}

    def trainer() -> None:
        try:
            receipt.update(run_trainer(
                [sys.executable, str(script), "--out", str(train / "walk.cxpolicy"), "--gate", str(gate),
                 "--checkpoints", ",".join(str(blobs / n) for n in ("c1", "c2", "c3", "c4")),
                 "--final", str(blobs / "final")], on_poll=watcher.poll))
        finally:
            watcher.drain()

    server = _served(root)
    thread = threading.Thread(target=trainer, daemon=True)
    try:
        page = _open(browser, server.url)
        assert _model_state(page) == "loaded"
        assert page.evaluate("window.cadexReview.checkpoints().source") == "accepted"
        thread.start()
        # The first rollout lands: the viewport turns to the training run, on
        # its own frozen model, and loops it.
        page.wait_for(PLAYING + " === 'walk.000020'", timeout=90)
        seen = page.evaluate("window.cadexReview.checkpoints()")
        assert seen["source"] == "run:" + RUN and seen["pinned"] is None
        assert page.evaluate("window.cadexReview.state().model.available")
        first = page.evaluate("document.getElementById('checkpoint-label').textContent")
        assert first == "iteration 20 · reward 0.25 · 1/1 · newest", first
        assert page.evaluate("document.getElementById('checkpoints').dataset.follow") == "true"
        # Drawn on the run's frozen model: one solid per link the trace poses.
        assert page.evaluate("window.cadexReview.viewer().stats().components") == len(LINKS)

        (gate / "go-1").touch()
        page.wait_for(PLAYING + " === 'walk.000040'", timeout=90)
        assert thread.is_alive() and not (train / "walk.cxpolicy").exists()  # still training
        second = page.evaluate("window.cadexReview.checkpoints()")
        assert [i["stem"] for i in second["items"]] == ["walk.000020", "walk.000040"]
        assert page.evaluate("document.getElementById('checkpoint-label').textContent") == \
            "iteration 40 · reward 0.5 · 2/2 · newest"

        # Picked by hand, an older one stays while newer ones land.
        assert page.evaluate("window.cadexReview.pickCheckpoint(0)") == "walk.000020"
        page.wait_for(PLAYING + " === 'walk.000020'", timeout=10)
        (gate / "go-2").touch()
        page.wait_for("window.cadexReview.checkpoints().items.length === 3", timeout=90)
        page.evaluate("window.cadexReview.refresh()", await_promise=True)
        assert page.evaluate(PLAYING) == "walk.000020"
        assert page.evaluate("document.getElementById('checkpoints').dataset.follow") == "false"

        # Back at the newest end it follows again; the newest failed in the
        # engine, and the page says why instead of playing anything.
        assert page.evaluate("window.cadexReview.pickCheckpoint(2)") is None
        page.wait_for("document.getElementById('checkpoints').dataset.state === 'failed'", timeout=10)
        status = page.evaluate("document.getElementById('checkpoint-status').textContent")
        assert status == ("rollout failed: policy_not_a_container — the checkpoint does not begin "
                          "with the cadex-policy-v1 magic line."), status
        assert page.evaluate("window.cadexReview.playback()") is None
        assert page.evaluate("document.getElementById('playback').hidden")

        (gate / "go-3").touch()
        page.wait_for(PLAYING + " === 'walk.000080'", timeout=90)
        assert thread.is_alive()
        (gate / "go-4").touch()
        (gate / "finish").touch()
        thread.join(timeout=120)
        assert receipt["sha256"] == hashlib.sha256(final).hexdigest()
        assert watcher.summary() == {"written": 3, "failed": 1}
    finally:
        for name in ("go-1", "go-2", "go-3", "go-4", "finish"):
            (gate / name).touch()
        if thread.is_alive():
            thread.join(timeout=120)
        server.shutdown()
        server.server_close()


@needs_browser
def test_a_source_picked_by_hand_is_not_taken_over_by_training(tmp_path, browser) -> None:
    root = _project(tmp_path)
    _manifest(root, REVISION_B)
    _stage_accepted(root, REVISION_B)
    server = _served(root)
    try:
        page = _open(browser, server.url)
        assert _model_state(page) == "loaded"
        page.evaluate("window.cadexReview.setSource('accepted')", await_promise=True)
        train = _training_run(root) / "train"
        (train / "walk.000020.rollout-trace.json").write_text(json.dumps(_trace("000020", 19, 0.5)))
        page.evaluate("window.cadexReview.refresh()", await_promise=True)
        page.evaluate("window.cadexReview.refresh()", await_promise=True)
        assert page.evaluate("window.cadexReview.checkpoints().source") == "accepted"
        assert page.evaluate("document.getElementById('checkpoints').hidden")
        # Choosing the run shows its checkpoint.
        page.evaluate(f"window.cadexReview.setSource('run:{RUN}')", await_promise=True)
        page.wait_for(PLAYING + " === 'walk.000020'", timeout=10)
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
def test_a_never_reloaded_page_adds_the_final_policy_stop_when_the_walk_lands_its_rollout(
        tmp_path, browser) -> None:
    """ADR-554: the walk's own rollout lands after its last checkpoint, and
    the page that watched the checkpoints adds it as the newest stop on the
    next poll, without a reload (orun3 remaining defect 1)."""

    root = _project(tmp_path)
    _manifest(root, REVISION_B)
    _stage_accepted(root, REVISION_B)
    run = _training_run(root)
    train = run / "train"
    (train / "walk.000020.rollout-trace.json").write_text(json.dumps(_trace("000020", 19, 0.5)))
    server = _served(root)
    try:
        page = _open(browser, server.url)
        page.evaluate(f"window.cadexReview.setSource('run:{RUN}')", await_promise=True)
        page.wait_for(PLAYING + " === 'walk.000020'", timeout=10)
        label = "document.getElementById('checkpoint-label').textContent"
        assert page.evaluate(label) == "iteration 20 · reward 0.5 · 1/1 · newest"
        # Polls settle on the run's model before the walk finishes.
        page.evaluate("window.cadexReview.refresh()", await_promise=True)
        page.evaluate("window.cadexReview.refresh()", await_promise=True)
        page.wait_for(PLAYING + " === 'walk.000020'", timeout=10)
        assert page.evaluate(label) == "iteration 20 · reward 0.5 · 1/1 · newest"

        # The walk finishes: its rollout leg leaves a trace and the parts
        # beside it, and the record names the trace.
        rollout = run / "rollout"
        rollout.mkdir()
        (rollout / "torso.stl").write_text(_cube_stl(12.0))
        trace = _trace("final", 59, 1.0, frames=4)
        del trace["checkpoint"]
        trace["simulation_output"] = "rollout"
        (rollout / "trace.json").write_text(json.dumps(trace))
        _progress(train, 59, [], state="completed")
        view = json.loads((run / "training-view.json").read_text())
        view.update(project_docs={"dir": None, "files": {}, "skipped": [], "note": "not snapshotted"},
                    identity={"available": False})
        (run / "training-view.json").write_text(json.dumps(view))
        write_run_record(run, project_root=root, status="ok", mode="blocking",
                         accepted_revision=REVISION_B, digest=DIGEST,
                         requested={"iterations": 60, "seed": 7}, trace=rollout / "trace.json")

        page.evaluate("window.cadexReview.refresh()", await_promise=True)
        page.wait_for(label + " === 'final policy · 2/2 · newest'", timeout=10)
        page.wait_for(PLAYING + " === 'final'", timeout=10)
        assert page.evaluate("document.getElementById('checkpoints').dataset.follow") == "true"
        # The older checkpoint is still a stop.
        assert page.evaluate("window.cadexReview.pickCheckpoint(0)") == "walk.000020"
        page.wait_for(PLAYING + " === 'walk.000020'", timeout=10)
    finally:
        server.shutdown()
        server.server_close()


#: Each scrubber row at phone width: its slider, label and status, the
#: viewport, the expanded overlay, and the theme's tokens to compare against.
SCRUBBER = """(function (box) {
  function q(s) { return document.querySelector(s); }
  function rect(e) { var b = e.getBoundingClientRect(); return {x: b.x, y: b.y, right: b.right, bottom: b.bottom, w: b.width, h: b.height}; }
  function token(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  var row = q('#' + box), pick = row.querySelector('input[type="range"]'), label = row.querySelector('output'),
      status = row.querySelector('p'), name = row.querySelector('.timeline-name');
  return {theme: document.documentElement.dataset.theme, state: row.dataset.state, page_width: document.documentElement.scrollWidth,
          row: rect(row), pick: rect(pick), label: rect(label), name: rect(name), text: label.textContent,
          label_clipped: label.scrollWidth > label.clientWidth, label_color: getComputedStyle(label).color,
          status_color: status.hidden ? null : getComputedStyle(status).color,
          model: rect(q('#model')), overlay: rect(q('#overlay')),
          ink: token('--ink'), bad: token('--bad'), warn: token('--warn')};
})(%s)"""


#: ``--scrub``: the narrowest a scrubber's slider gets (docs/DASHBOARD.md §5).
SCRUB_PX = 160


def _phone(browser, url: str, theme: str):
    page = browser.page("about:blank")
    page.send("Emulation.setDeviceMetricsOverride",
              {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
    page.send("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 5})
    page.send("Page.navigate", {"url": url})
    page.wait_for("document.readyState === 'complete' && !!window.cadexReview")
    page.evaluate("window.cadexReview.ready", await_promise=True)
    page.evaluate(f"window.cadexTheme.set({json.dumps(theme)})")
    page.evaluate("window.cadexReview.setOverlayCollapsed(false)")
    return page


def _hex_rgb(value: str) -> str:
    return "rgb(%d, %d, %d)" % tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def _assert_scrubber(m: dict, status_token: str | None) -> None:
    """The row is in the viewport, under the overlay, its slider at least
    ``SCRUB_PX`` wide and a touch target tall, beside nothing it covers, and
    its words in the theme's own colours."""

    row, pick, label, name, model = m["row"], m["pick"], m["label"], m["name"], m["model"]
    assert m["page_width"] <= 390
    assert model["x"] <= row["x"] and row["right"] <= model["right"] and row["bottom"] <= model["bottom"]
    assert row["y"] >= m["overlay"]["bottom"], (row, m["overlay"])
    assert pick["w"] >= SCRUB_PX, (m["text"], pick)
    assert pick["h"] >= 32  # the touch --tool height
    assert pick["x"] >= name["right"] and pick["right"] <= row["right"]
    # The label sits after the slider on its row, or under it on the next.
    assert label["x"] >= pick["right"] or label["y"] >= pick["bottom"], (label, pick)
    assert label["right"] <= row["right"] and not m["label_clipped"]
    assert m["label_color"] == _hex_rgb(m["ink"])
    assert m["status_color"] == (None if status_token is None else _hex_rgb(m[status_token]))


@needs_browser
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_both_scrubbers_keep_their_width_at_390px_in_either_theme(tmp_path, browser, theme) -> None:
    """ADR-556: at 390 px a long checkpoint label once squeezed the slider to
    0 px, so a phone could not step back to an older checkpoint; the
    revision slider was 53 px. Each slider now keeps ``--scrub`` and the
    label wraps under it, in the light theme as in the dark."""

    from test_review_revisions import _biped_store

    root = _project(tmp_path)
    _manifest(root, REVISION_B)
    _stage_accepted(root, REVISION_B)
    train = _training_run(root) / "train"
    (train / "walk.000020.rollout-trace.json").write_text(json.dumps(_trace("000020", 19, 0.5)))
    (train / "walk.000040.rollout-trace.json").write_text(json.dumps(_trace("000040", 39, 1.25)))
    (train / "walk.000060.rollout-failed.json").write_text(json.dumps({
        "schema": "cadex-checkpoint-rollout-failure-v1", "checkpoint": "walk.000060.cxpolicy",
        "tag": "000060", "iteration": 59, "reason": "child_failed",
        "error": "the rollout exited 1: the policy's observation size does not match the task's"}))
    history = tmp_path / "orun3-biped-history"
    _biped_store(history)
    servers = [_served(root), _served(history)]
    page = None
    try:
        page = _phone(browser, servers[0].url, theme)
        page.evaluate(f"window.cadexReview.setSource('run:{RUN}')", await_promise=True)
        newest = "document.getElementById('checkpoint-label').textContent"
        page.wait_for(newest + " === 'iteration 60 · reward — · 3/3 · newest'", timeout=10)
        failed = page.evaluate(SCRUBBER % json.dumps("checkpoints"))
        assert failed["theme"] == theme and failed["state"] == "failed"
        _assert_scrubber(failed, "bad")
        assert page.evaluate("window.cadexReview.pickCheckpoint(1)") == "walk.000040"
        page.wait_for(PLAYING + " === 'walk.000040'", timeout=10)
        ready = page.evaluate(SCRUBBER % json.dumps("checkpoints"))
        _assert_scrubber(ready, None)
        # The playback row below it is still inside the viewport.
        play = page.evaluate("(function(){var b=document.getElementById('playback').getBoundingClientRect();"
                             "return [b.bottom, document.getElementById('model').getBoundingClientRect().bottom];})()")
        assert play[0] <= play[1]

        page = _phone(browser, servers[1].url, theme)
        page.evaluate("window.cadexReview.setSource('revisions')", await_promise=True)
        page.evaluate("window.cadexReview.pickRevision(0)")
        page.wait_for("document.getElementById('revision-timeline').dataset.state === 'missing'", timeout=10)
        missing = page.evaluate(SCRUBBER % json.dumps("revision-timeline"))
        _assert_scrubber(missing, "warn")
        page.evaluate("window.cadexReview.pickRevision(2)")
        page.wait_for("document.getElementById('revision-timeline').dataset.state === 'retained'", timeout=10)
        retained = page.evaluate(SCRUBBER % json.dumps("revision-timeline"))
        _assert_scrubber(retained, None)
        measured = {name: round(m["pick"]["w"]) for name, m in
                    (("checkpoint_failed", failed), ("checkpoint_ready", ready),
                     ("revision_missing", missing), ("revision_retained", retained))}
        print(json.dumps({"scrubbers_390": {"theme": theme, "slider_px": measured}}))
    finally:
        if page is not None:
            page.evaluate("window.cadexTheme.set('dark')")  # the module's browser is shared
        for server in servers:
            server.shutdown()
            server.server_close()
