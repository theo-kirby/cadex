# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The training loop the product agent runs (ADR-464).

Three layers. The run registry and its supervisor are driven against a
hand-built retained attempt and a fake trainer, with the supervisor really
detached, and need nothing. The four bridge tools are driven the same way
through ``Bridge.call``. The whole round -- a task accepted by a live
engine, a run started in one ``cadex mcp`` session, its policy declared and
evaluated in the next -- goes through the session host the agent's tool
calls reach (ADR-538), and skips without a built engine.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import textwrap
import time

import pytest

from conftest import SOURCE_MODULE_DIR
from fake_cadexd import FakeCadexd

from cadex_cli import loop
from cadex_cli import train as train_module
from cadex_cli.__main__ import McpSession, build_parser
from cadex_cli.bridge import Bridge
from cadex_cli.guidance import OVERLAY
from cadex_cli.tools import BRIDGE_TOOLS

REPO_ROOT = Path(__file__).resolve().parents[2]
TRAINER_SOURCE = REPO_ROOT / "training" / "cadex_train.py"
HAS_MUJOCO = importlib.util.find_spec("mujoco") is not None
REVISION = "a" * 64
DIGEST = "d" * 64
REASON = "first run: no policy exists yet, so train the task as designed."


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _retained(root: Path, *, grounded: bool = True, tasks=("job",)) -> Path:
    """A project as the store leaves one: a pin, a result, a task and its model."""

    staging = root / "script_artifacts" / REVISION / "attempt-1"
    (staging / "outputs").mkdir(parents=True)
    model = b"<mujoco/>"
    outputs = [{"name": "model", "artifact_kind": "assembly_mjcf_xml",
                "artifact_path": "outputs/model-model.xml", "artifact_sha256": _sha(model)}]
    (staging / "outputs" / "model-model.xml").write_bytes(model)
    for name in tasks:
        task = json.dumps({
            "label": name,
            "model": {"output": "model", "path": "outputs/model-model.xml", "sha256": _sha(model)},
            "observations": [{"channels": ["angle"], "role": "policy",
                              **({"grounded_sensor": "encoder"} if grounded else {})}],
            "success": {"seeds": [1101, 1102], "predicates": []},
        }).encode()
        (staging / "outputs" / f"{name}-task.json").write_bytes(task)
        outputs.append({"name": name, "artifact_kind": "assembly_training_task_json",
                        "artifact_path": f"outputs/{name}-task.json",
                        "artifact_sha256": _sha(task)})
    (staging / "result.json").write_text(json.dumps(
        {"ok": True, "digest": DIGEST, "outputs": outputs}))
    (root / "script.json").write_text(json.dumps({
        "schema": "cadex-project-script-v1", "accepted_revision": REVISION,
        "accepted_digest": DIGEST,
        "accepted_attempt": {"revision": REVISION, "staging": str(staging.relative_to(root))},
    }))
    return staging


#: A trainer with the real one's contract -- a bundle, ``--out``, a
#: ``progress.json`` beside the policy, a receipt on the last stdout line --
#: and a mode, so a test can have it take its time, collapse or crash.
FAKE_TRAINER = textwrap.dedent(
    """
    import hashlib, json, os, sys, time
    from pathlib import Path
    argv = sys.argv[1:]
    bundle = Path(argv[0])
    out = Path(argv[argv.index("--out") + 1])
    total = int(argv[argv.index("--iterations") + 1])
    mode = os.environ.get("FAKE_TRAIN_MODE", "ok")

    def progress(iteration, **extra):
        payload = {"schema": "cadex-training-progress-v1", "state": "training",
                   "iteration": iteration, "total": total, "reward_per_step": 0.5 + iteration,
                   "episode_steps": 40.0, "curve": [[i, 0.5 + i] for i in range(iteration + 1)],
                   "checkpoints": [], "warning": "", "error": "", **extra}
        scratch = out.parent / "progress.json.tmp"
        scratch.write_text(json.dumps(payload))
        scratch.replace(out.parent / "progress.json")

    progress(0)
    print("iteration 0  reward/step +0.5", file=sys.stderr, flush=True)
    if mode == "slow":
        (out.parent / "best.cxpolicy").write_bytes(b"CXPOLICY-best")
        progress(0, checkpoints=[{"tag": "best", "iteration": 0, "path": "best.cxpolicy",
                                  "sha256": hashlib.sha256(b"CXPOLICY-best").hexdigest(),
                                  "reward_per_step": 0.5}])
        for _ in range(240):
            time.sleep(0.25)
    if mode == "collapse":
        progress(1, warning="the mean episode fell from 40 to 3 steps",
                 state="failed", error="SystemExit: Stopped at iteration 1: collapsed")
        raise SystemExit("Stopped at iteration 1: collapsed")
    if mode == "crash":
        raise RuntimeError("NotImplementedError: MJX cannot build this model")
    blob = b"CXPOLICY-fake\\n" * 32
    out.write_bytes(blob)
    progress(total - 1, state="done")
    print("not the receipt")
    print(json.dumps({
        "out": str(out), "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest(),
        "reward_per_step": 1.5, "wall_time_s": 0.01, "device": "fake",
        "task_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(), "argv": argv,
    }, sort_keys=True))
    """
)


@pytest.fixture
def project(tmp_path, monkeypatch) -> Path:
    """A retained project, the fake trainer, and a training slot of its own."""

    script = tmp_path / "fake_train.py"
    script.write_text(FAKE_TRAINER, encoding="utf-8")
    monkeypatch.setattr(train_module, "TRAINER_SCRIPT", script)
    monkeypatch.setenv(train_module.TRAINER_PYTHON_ENV, sys.executable)
    monkeypatch.setenv(loop.MACHINE_LOCK_ENV, str(tmp_path / "slot.lock"))
    monkeypatch.delenv("FAKE_TRAIN_MODE", raising=False)
    root = tmp_path / "project"
    root.mkdir()
    _retained(root)
    yield root
    # No supervisor outlives its test: ask every live run to stop. A run
    # only registered, with no supervisor holding its lock, gets the stop
    # file a late supervisor will read, and a short wait rather than 20 s.
    for run in loop.list_runs(root):
        if run["state"] in loop.LIVE_STATES:
            run_dir = Path(run["dir"])
            held = run["state"] == "running" or loop.lock_held(run_dir / loop.LOCK_NAME)
            loop.request_stop(run_dir, "the test ended", wait_s=20.0 if held else 2.0)


def _until(run_dir: Path, *, leaves=loop.LIVE_STATES, seconds: float = 30.0) -> dict:
    deadline = time.monotonic() + seconds
    run = loop.read_run(run_dir)
    while run["state"] in leaves and time.monotonic() < deadline:
        time.sleep(0.1)
        run = loop.read_run(run_dir)
    return run


def _register(root: Path, run: str = "r1", **overrides) -> Path:
    arguments = {"budget_s": 60.0, "reason": REASON,
                 "settings": {"iterations": 3, "envs": 4, "seed": 7}, **overrides}
    return loop.register(root, run=run, **arguments)


# -- the settings are the trainer's own ------------------------------------------


def test_every_setting_is_a_flag_the_trainer_declares(project) -> None:
    declared = set(re.findall(r'add_argument\(\s*"(--[a-z-]+)"',
                              TRAINER_SOURCE.read_text(encoding="utf-8")))
    assert {flag for flag, _kind in loop.EXTRA_SETTINGS.values()} | {"--hidden"} <= declared
    settings = {"iterations": 3, "envs": 4, "seed": 7, "hidden": [32, 32],
                **{key: 1 for key in loop.EXTRA_SETTINGS}}
    command = json.loads((_register(project, settings=settings) / loop.REGISTRATION_NAME)
                         .read_text())["command"]
    used = {item for item in command if item.startswith("--")}
    assert used <= declared, used - declared
    assert command[command.index("--hidden") + 1:command.index("--hidden") + 3] == ["32", "32"]
    # The tool's prose names every setting the registry takes, and no other.
    prose = BRIDGE_TOOLS["train_start"]["input_schema"]["properties"]["settings"]["description"]
    assert all(name in prose for name in loop.SETTING_NAMES)


# -- pre-registration ------------------------------------------------------------


def test_a_run_is_registered_whole_before_anything_is_launched(project) -> None:
    run_dir = _register(project)
    registration = json.loads((run_dir / loop.REGISTRATION_NAME).read_text())
    assert registration["schema"] == loop.REGISTRATION_SCHEMA
    assert registration["reason"] == REASON and registration["budget_s"] == 60.0
    assert registration["settings"] == {"iterations": 3, "envs": 4, "seed": 7}
    assert registration["accepted_revision"] == REVISION
    assert registration["task_output"] == "job" and registration["evaluation_seeds"] == [1101, 1102]
    assert "budget" in registration["stop_rule"] and "collapse" in registration["stop_rule"]
    # --stop-on-collapse is not a setting: it is always on.
    assert "--stop-on-collapse" in registration["command"]
    # The bundle the run trains on is the accepted one, copied with its model.
    bundle = run_dir / registration["bundle"]
    assert _sha(bundle.read_bytes()) == registration["task_sha256"]
    assert train_module.resolve_bundle_model(bundle) == run_dir / registration["model"]
    # Nothing ran: no progress, no log, no policy, and the slot is free.
    assert loop.read_run(run_dir)["state"] == "registered"
    assert sorted(path.name for path in (run_dir / "train").iterdir()) == [
        "job-task.json", "model-model.xml"]
    assert not loop.lock_held(loop.machine_lock_path())
    assert [row["kind"] for row in loop.read_ledger(project)] == ["train_registered"]


def test_the_slot_is_one_lock_for_the_supervisor_and_cadex_train(project) -> None:
    """``machine_slot`` (ADR-543) is the lock ``register`` and ``supervise``
    read: while ``cadex train`` holds it, ``train_start`` is refused, and
    a second holder is refused rather than queued."""

    with loop.machine_slot():
        assert loop.lock_held(loop.machine_lock_path())
        with pytest.raises(loop.LoopError, match=loop.SLOT_BUSY):
            with loop.machine_slot():
                pass
        with pytest.raises(loop.LoopError, match=loop.SLOT_BUSY):
            _register(project)
        assert not (project / "runs" / "r1").exists()
    assert not loop.lock_held(loop.machine_lock_path())
    with loop.machine_slot():  # released on the way out, even after a refusal
        pass
    _register(project)


@pytest.mark.parametrize("overrides, said", [
    ({"budget_s": None}, "budget_s must be a number"),
    ({"budget_s": 0}, "a run with no budget is not started"),
    ({"budget_s": loop.MAX_BUDGET_S + 1}, "budget_s must be within"),
    ({"reason": "try again"}, "measurement that motivated"),
    ({"run": "../escape"}, "run must be a short name"),
    ({"settings": {"seed": 1101}}, "an evaluation seed is never a training seed"),
    ({"settings": {"num_envs": 8}}, "unknown training setting(s): num_envs"),
    ({"settings": {"iterations": 0}}, "at least 1"),
    ({"settings": {"init_from_task_change": "harder"}}, "needs init_from"),
    ({"task_name": "walk"}, "declares no task 'walk'"),
])
def test_a_run_that_cannot_be_registered_says_why_and_leaves_nothing(project, overrides, said) -> None:
    with pytest.raises(loop.LoopError, match=re.escape(said)):
        _register(project, **overrides)
    assert not (project / "runs").exists() and loop.read_ledger(project) == []


def test_a_task_the_robot_cannot_read_is_not_trained(tmp_path, project) -> None:
    other = tmp_path / "ungrounded"
    other.mkdir()
    _retained(other, grounded=False)
    with pytest.raises(loop.LoopError, match="name no onboard sensor"):
        _register(other)


def test_several_tasks_are_a_choice(tmp_path, project) -> None:
    other = tmp_path / "two"
    other.mkdir()
    _retained(other, tasks=("reach", "balance"))
    with pytest.raises(loop.LoopError, match="more than one task; name one: reach, balance"):
        _register(other)
    run_dir = _register(other, task_name="balance")
    assert json.loads((run_dir / loop.REGISTRATION_NAME).read_text())["task_output"] == "balance"


# -- the supervisor --------------------------------------------------------------


def test_a_run_outlives_the_process_that_started_it_and_ends_with_a_verified_policy(
        project, monkeypatch) -> None:
    run_dir = _register(project)
    # Launched from a process that exits at once, the way a turn does.
    subprocess.run(
        [sys.executable, "-c",
         "import sys; from pathlib import Path; from cadex_cli import loop; "
         "loop.launch(Path(sys.argv[1]), wait_s=0.0)", str(run_dir)],
        check=True, env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "cli")}, timeout=30)
    run = _until(run_dir)
    assert run["state"] == "finished", run
    policy = run["status"]["policy"]
    assert Path(policy["path"]) == run_dir / "train" / "job.cxpolicy"
    assert _sha(Path(policy["path"]).read_bytes()) == policy["sha256"]
    assert run["status"]["receipt"]["task_sha256"] == run["registration"]["task_sha256"]
    assert run["status"]["iterations_run"] == 3 and run["status"]["exit"] == 0
    # The slot is free again, and the dashboard's record names the policy.
    assert not loop.lock_held(loop.machine_lock_path())
    record = json.loads((run_dir / "run.json").read_text())
    assert (record["mode"], record["status"]) == ("loop", "ok")
    assert record["policy"]["sha256"] == policy["sha256"]
    assert record["artifacts"]["progress"] == "train/progress.json"
    assert [row["kind"] for row in loop.read_ledger(project)] == ["train_registered", "train_ended"]
    view = loop.run_view(run)
    assert view["policy"] == policy and "put_asset" in view["next"] and "evaluate" in view["next"]
    # A run is launched once.
    assert loop.launch(run_dir, wait_s=1.0)["state"] == "finished"


def test_a_running_run_is_read_stopped_and_leaves_its_checkpoint(project, monkeypatch) -> None:
    monkeypatch.setenv("FAKE_TRAIN_MODE", "slow")
    run = loop.launch(_register(project))
    assert run["state"] == "running", run
    run_dir = Path(run["dir"])
    deadline = time.monotonic() + 20.0
    while not loop.read_run(run_dir)["progress"].get("checkpoints") and time.monotonic() < deadline:
        time.sleep(0.1)
    view = loop.run_view(loop.read_run(run_dir))
    assert view["progress"]["iteration"] == 0 and view["progress"]["total"] == 3
    assert view["next"].startswith("Call train_status")
    # One run at a time: on this project, and on this machine.
    with pytest.raises(loop.LoopError, match="run r1 of this project is still live"):
        _register(project, run="r2")
    stopped = loop.request_stop(run_dir, "the reward is flat")
    assert stopped["state"] == "stopped" and "the reward is flat" in stopped["reason"]
    assert stopped["status"]["iterations_run"] == 1
    view = loop.run_view(stopped)
    (checkpoint,) = view["checkpoints"]
    assert checkpoint["tag"] == "best" and Path(checkpoint["path"]).is_file()
    assert "policy" not in view and "checkpoint" in view["next"]
    assert view["log_tail"] == ["iteration 0  reward/step +0.5"]
    assert not loop.lock_held(loop.machine_lock_path())
    # A stop asked for is not a failure (ADR-559).
    record = json.loads((run_dir / "run.json").read_text())
    assert record["status"] == "stopped" and "the reward is flat" in record["error"]
    # Stopping a run that has ended changes nothing.
    assert loop.request_stop(run_dir, "again")["state"] == "stopped"
    assert [row["kind"] for row in loop.read_ledger(project)].count("train_stop_requested") == 1


def test_a_checkpoint_the_progress_never_listed_is_still_the_runs(project) -> None:
    """ot11 ``bal-1``: the budget ended the run after the trainer wrote its
    iteration-400 checkpoint and before it rewrote its progress, and the
    agent evaluated that checkpoint. The ledger said ``trained_by_run: []``.
    The files on disk are the authority, with their own digests -- including
    a ``best`` rewritten under a digest the progress names for an earlier
    iteration."""

    run_dir = _register(project)
    train = run_dir / "train"
    train.mkdir(parents=True, exist_ok=True)
    (train / "job.000050.cxpolicy").write_bytes(b"CXPOLICY-50")
    (train / "job.000100.cxpolicy").write_bytes(b"CXPOLICY-100")
    (train / "job.best.cxpolicy").write_bytes(b"CXPOLICY-best-now")
    (train / "progress.json").write_text(json.dumps({"iteration": 98, "checkpoints": [
        {"tag": "000050", "iteration": 49, "path": "job.000050.cxpolicy",
         "sha256": _sha(b"CXPOLICY-50"), "reward_per_step": 0.4},
        {"tag": "best", "iteration": 40, "path": "job.best.cxpolicy",
         "sha256": _sha(b"CXPOLICY-best-then"), "reward_per_step": 0.5}]}))
    view = loop.run_view(loop.read_run(run_dir))
    assert [(row["tag"], row["iteration"], row["sha256"], row["reward_per_step"])
            for row in view["checkpoints"]] == [
        ("000050", 49, _sha(b"CXPOLICY-50"), 0.4),
        ("000100", 99, _sha(b"CXPOLICY-100"), None),
        ("best", None, _sha(b"CXPOLICY-best-now"), None)]
    assert loop.runs_that_trained(project, _sha(b"CXPOLICY-100")) == ["r1"]
    assert loop.runs_that_trained(project, _sha(b"CXPOLICY-best-now")) == ["r1"]
    # A digest the run once wrote still names it; one it never wrote does not.
    assert loop.runs_that_trained(project, _sha(b"CXPOLICY-best-then")) == ["r1"]
    assert loop.runs_that_trained(project, _sha(b"someone else's")) == []
    assert loop.runs_that_trained(project, "") == []


def test_the_machine_trains_one_run_at_a_time(tmp_path, project, monkeypatch) -> None:
    monkeypatch.setenv("FAKE_TRAIN_MODE", "slow")
    assert loop.launch(_register(project))["state"] == "running"
    other = tmp_path / "other"
    other.mkdir()
    _retained(other)
    with pytest.raises(loop.LoopError, match="this machine's one training slot"):
        _register(other)


def test_a_run_past_its_budget_is_stopped_and_says_so(project, monkeypatch) -> None:
    monkeypatch.setenv("FAKE_TRAIN_MODE", "slow")
    run_dir = _register(project, budget_s=1.0)
    loop.launch(run_dir)
    run = _until(run_dir)
    assert run["state"] == "budget_exhausted" and "budget of 1 s" in run["reason"]
    assert 1.0 <= run["status"]["wall_time_s"] < 20.0


def test_a_collapse_and_a_crash_are_two_different_endings(project, monkeypatch) -> None:
    monkeypatch.setenv("FAKE_TRAIN_MODE", "collapse")
    run_dir = _register(project)
    loop.launch(run_dir)
    run = _until(run_dir)
    assert run["state"] == "collapsed" and "fell from 40 to 3" in run["reason"]

    monkeypatch.setenv("FAKE_TRAIN_MODE", "crash")
    run_dir = _register(project, run="r2")
    loop.launch(run_dir)
    run = _until(run_dir)
    assert run["state"] == "failed" and "the trainer exited 1" in run["reason"]
    assert "MJX cannot build this model" in run["reason"]
    assert any("MJX cannot build" in line for line in loop.run_view(run)["log_tail"])


def test_a_killed_supervisor_is_an_interruption_not_an_attempt(project, monkeypatch) -> None:
    monkeypatch.setenv("FAKE_TRAIN_MODE", "slow")
    run = loop.launch(_register(project))
    assert run["state"] == "running"
    run_dir = Path(run["dir"])
    # Told to terminate, the supervisor stops its trainer and says what happened.
    os.kill(int(run["status"]["supervisor_pid"]), signal.SIGTERM)
    ended = _until(run_dir)
    assert ended["state"] == "interrupted" and "not an attempt" in ended["reason"]
    assert ended["status"]["state"] == "interrupted"

    # Killed outright it can say nothing; the reader tells from the lock.
    run = loop.launch(_register(project, run="r2"))
    run_dir = Path(run["dir"])
    os.kill(int(run["status"]["supervisor_pid"]), signal.SIGKILL)
    ended = _until(run_dir, leaves=("running",))
    assert ended["state"] == "interrupted" and ended["status"]["state"] == "running"
    assert "not an attempt" in ended["reason"]
    assert not loop.lock_held(loop.machine_lock_path())
    # ...and an interrupted run does not hold the project's next run up.
    assert loop.live_run(project) == ""


# -- the four tools --------------------------------------------------------------


def test_the_agent_starts_watches_and_stops_runs_through_the_bridge(project, monkeypatch) -> None:
    with Bridge(FakeCadexd(), project_root=project) as bridge:
        started = bridge.call("train_start", {
            "run": "r1", "budget_s": 60, "reason": REASON,
            "settings": {"iterations": 3, "envs": 4, "seed": 7}})
        assert started["is_error"] is False, started
        assert _payload(started)["state"] in ("running", "finished")
        waited = _payload(bridge.call("train_status", {"run": "r1", "wait_s": 30}))
        assert waited["state"] == "finished" and waited["registered_for"] == REASON
        assert Path(waited["policy"]["path"]).is_file()
        # The model it trained is frozen beside it, as a walk's is, so the
        # dashboard can pose its checkpoint rollouts on it.
        view = json.loads((project / "runs" / "r1" / "training-view.json").read_text())
        assert view["schema"] == "cadex-training-view-v1"
        assert view["identity"]["revision"] == REVISION
        assert bridge.state.calls[-1].summary.startswith("r1  finished  iteration 3 of 3")

        monkeypatch.setenv("FAKE_TRAIN_MODE", "slow")
        second = {"run": "r2", "budget_s": 60, "settings": {"iterations": 3},
                  "reason": "evaluation failed B3 drift on 6 of 10 seeds; add a drift penalty."}
        assert _payload(bridge.call("train_start", second))["state"] == "running"
        stopped = _payload(bridge.call("train_stop", {"run": "r2", "reason": "wrong reward sign"}))
        assert stopped["state"] == "stopped"

        listing = _payload(bridge.call("train_status", {}))
        assert [(row["run"], row["state"]) for row in listing["runs"]] == [
            ("r1", "finished"), ("r2", "stopped")]
        assert listing["runs"][0]["policy_sha256"] == waited["policy"]["sha256"]
        assert [row["kind"] for row in listing["ledger"]] == [
            "train_registered", "train_ended", "train_registered", "train_stop_requested",
            "train_ended"]
        assert listing["ledger"][2]["reason"] == second["reason"]


def test_each_ending_of_a_started_run_reads_on_the_page_as_what_happened(
        project, monkeypatch) -> None:
    """Finished, stopped through ``train_stop``, killed, crashed: each run
    started through ``train_start`` is, in ``/api/project``'s stage, what
    happened to it. Before ADR-559 a stop read as failed, and a killed
    supervisor's run as training for ever."""

    from cadex_cli.review_record import read_run_record
    from cadex_cli.review_server import ReviewProject

    def shown(run: str) -> tuple[str, str, str]:
        # Records are stamped to the second, and the stage reads the newest:
        # the next run's must not tie with this one's.
        stage = ReviewProject(project).review()["stage"]
        time.sleep(1.1)
        assert stage["run"] == run, stage
        record = read_run_record(project / "runs" / run, project)
        return stage["state"], stage["reason"], record["status"]

    start = {"budget_s": 60, "reason": REASON, "settings": {"iterations": 3}}
    with Bridge(FakeCadexd(), project_root=project) as bridge:
        assert bridge.call("train_start", {"run": "done", **start})["is_error"] is False
        assert _payload(bridge.call("train_status", {"run": "done", "wait_s": 30}))["state"] == "finished"
        state, _reason, status = shown("done")
        assert status == "ok" and state not in ("stopped", "failed")

        monkeypatch.setenv("FAKE_TRAIN_MODE", "slow")
        assert _payload(bridge.call("train_start", {"run": "asked", **start}))["state"] == "running"
        assert _payload(bridge.call("train_stop", {"run": "asked", "reason": "the reward is flat"}))[
            "state"] == "stopped"
        state, reason, status = shown("asked")
        assert (state, status) == ("stopped", "stopped") and "the reward is flat" in reason

        assert _payload(bridge.call("train_start", {"run": "killed", **start}))["state"] == "running"
        os.kill(int(loop.read_run(project / "runs" / "killed")["status"]["supervisor_pid"]),
                signal.SIGKILL)
        _until(project / "runs" / "killed", leaves=("running",))
        state, reason, status = shown("killed")
        assert (state, status) == ("failed", "failed") and "killed or crashed" in reason

        monkeypatch.setenv("FAKE_TRAIN_MODE", "crash")
        bridge.call("train_start", {"run": "crashed", **start})
        assert _payload(bridge.call("train_status", {"run": "crashed", "wait_s": 30}))["state"] == "failed"
        state, reason, status = shown("crashed")
        assert (state, status) == ("failed", "failed") and "MJX cannot build this model" in reason


def test_a_refused_tool_call_is_an_error_the_agent_can_act_on(project, tmp_path) -> None:
    with Bridge(FakeCadexd(), project_root=project) as bridge:
        for tool, arguments, said in (
            ("train_start", {"run": "r1", "reason": REASON}, "budget_s must be a number"),
            ("train_start", {"run": "r1", "budget_s": 60, "reason": REASON, "walk": True},
             "train_start takes"),
            ("train_status", {"run": "nope"}, "no training run 'nope'"),
            ("train_status", {"run": "../x"}, "no training run"),
            ("train_stop", {"run": "nope", "reason": "x"}, "no training run"),
            # The accepted revision declares no policy yet, so there is
            # nothing to evaluate, and the refusal says what to declare.
            ("evaluate", {}, "declares no policy"),
        ):
            reply = bridge.call(tool, arguments)
            assert reply["is_error"] is True and said in _payload(reply)["error"], (tool, reply)
            assert bridge.state.calls[-1].ok is False
    with Bridge(FakeCadexd()) as bridge:
        reply = bridge.call("train_status", {})
        assert reply["is_error"] is True and "needs a project directory" in _payload(reply)["error"]


def test_the_loop_names_no_behaviour() -> None:
    """One loop for every behaviour: nothing in it, in its tools or in what
    the agent is told about it may know what is being trained."""

    paragraph = OVERLAY[OVERLAY.index("YOU TRAIN AND EVALUATE"):
                        OVERLAY.index("THE PROJECT IS A CODEBASE")]
    # The one sentence that lists behaviours does so to say none is special.
    assert "nothing in it knows which" in " ".join(paragraph.split())
    listing, rest = paragraph.split("nothing in it knows", 1)
    texts = [rest, Path(loop.__file__).read_text(encoding="utf-8")] + [
        json.dumps(BRIDGE_TOOLS[name]) for name in
        ("train_start", "train_status", "train_stop", "evaluate")]
    for text in texts:
        for word in ("walk", "gait", "foot", "feet", "leg", "quadruped", "biped", "reach",
                     "balanc", "arm ", "shove"):
            assert not re.search(rf"\b{word}", text.lower()), word


def test_the_lifecycle_walk_defers_to_the_spec_when_the_task_has_one(tmp_path) -> None:
    """`cadex walk` stays, as one scripted pass over the same legs (ADR-464).
    Its gait block knows one behaviour, so a task with a success spec is
    judged by the spec and the review says which reading has the authority."""

    from cadex_cli import walk

    assert walk.behaviour_authority({"success": {"seeds": [1101]}}) == {
        "authority": "success spec", "command": "cadex evaluate", "gait": "advisory"}
    legacy = walk.behaviour_authority({"label": "walk"})
    assert legacy["authority"] == "gait" and legacy["command"] is None
    for task, authority in (({"success": {}}, "success spec"), ({}, "gait")):
        path = walk.write_review(
            tmp_path, review={"behaviour": walk.behaviour_authority(task)}, legs=[],
            training={}, params={})
        assert json.loads(path.read_text())["behaviour"]["authority"] == authority
    # The loop itself never reads the gait block, or the walk.
    source = Path(loop.__file__).read_text(encoding="utf-8")
    assert "gait" not in source and "from .walk" not in source


# -- one whole round, through the product path -----------------------------------

#: The engine suite's success-spec fixture with what the loop asks of a task:
#: the one channel the policy reads is measured by an encoder.
SCRIPT = """
brick = part.box(120, 60, 40)
tab = part.box(50, 20, 6)
block = assembly.component(brick)
paddle = assembly.component(tab, placement=[0, 0, 60])
wrist = assembly.joint("revolute",
                       assembly.connector(block, "origin",
                                          offset={"position": [0, 0, 40],
                                                  "axis": [1, 0, 0],
                                                  "angle_degrees": 90}),
                       assembly.connector(paddle, "origin",
                                          offset={"position": [0, 0, 0],
                                                  "axis": [1, 0, 0],
                                                  "angle_degrees": 90}))
asm = assembly.assembly([block, paddle], [wrist])
diag = assembly.solve(asm)
motor = assembly.actuator(wrist, kind="motor", control_nmm="0",
                          torque_limit_nmm=2)
encoder = assembly.sensor(wrist, "joint_encoder", name="encoder")
model = assembly.mjcf(asm, [
    assembly.body(block, density_kg_m3=2700,
                  collision=[assembly.collision(
                      "box", size_mm=[120, 60, 40],
                      offset={"position": [60, 30, 20]})]),
    assembly.body(paddle, density_kg_m3=2700),
], actuators=[motor], observations=[
    assembly.observation(wrist, "position", name="angle", sensor=encoder),
])
harder = assembly.disturbance(block, newtons=[6.0, 8.0],
                              at_seconds=[1.0, 1.5], duration_s=0.1,
                              label="harder")
spec = assembly.success(
    [
        {"id": "completes", "metric": "completed", "min": 1},
        {"id": "upright", "metric": "max_tilt_deg", "max": 30},
        {"id": "still", "metric": "max_drift_mm", "max": 0.001},
    ],
    seeds=[1101, 1102],
    episode_seconds=2.0,
    reset_variation=[],
    disturbance=[harder],
    label="stays put",
)
job = assembly.task(model, actions=[motor],
                    reward=[assembly.reward("-(angle^2)", weight=1.0e-3,
                                            label="level")],
                    episode_seconds=1.0, control_hz=50,
                    success=spec, label="stand")
result = {"brick": brick, "tab": tab, "block": block, "paddle": paddle,
          "wrist": wrist, "asm": asm, "diag": diag, "model": model,
          "job": job}
"""

POLICY = """
pol = assembly.policy(job, weights="job.cxpolicy", sha256="@SHA@")
result["pol"] = pol
"""

#: A trainer that writes a policy a live engine verifies: the engine suite's
#: own container fixture, behind the real trainer's argv and receipt.
FIXTURE_TRAINER = """
import hashlib, json, sys
from pathlib import Path
sys.path[:0] = [{module_dir!r}, {tests_dir!r}]
import dynamics_policy_fixtures as pf
argv = sys.argv[1:]
task = Path(argv[0]).read_bytes()
out = Path(argv[argv.index("--out") + 1])
made = pf.policy_container({{"bundle": json.loads(task),
                            "task_sha256": hashlib.sha256(task).hexdigest()}})
out.write_bytes(made["blob"])
(out.parent / "progress.json").write_text(json.dumps({{
    "schema": "cadex-training-progress-v1", "state": "done", "iteration": 1, "total": 2,
    "reward_per_step": 0.04, "curve": [[0, 0.03], [1, 0.04]], "checkpoints": []}}))
print(json.dumps({{"out": str(out), "bytes": len(made["blob"]),
                  "sha256": hashlib.sha256(made["blob"]).hexdigest(),
                  "task_sha256": hashlib.sha256(task).hexdigest(), "device": "fixture"}}))
"""


def _session(root: Path) -> McpSession:
    """What ``cadex mcp --project ROOT`` answers tool calls with."""

    args = build_parser().parse_args(["mcp", "--project", str(root)])
    args.wait = True
    return McpSession(args)


def _payload(reply: dict) -> dict:
    return json.loads(reply["content"][0]["text"])


@pytest.mark.skipif(not HAS_MUJOCO, reason="mujoco is not importable here")
def test_one_round_of_the_loop_runs_through_the_product_path(engine, tmp_path, monkeypatch) -> None:
    """Design, train, evaluate: two agent sessions over a live engine. The
    run started in the first is read in the second, which declares its
    policy and evaluates it."""

    trainer = tmp_path / "fixture_train.py"
    trainer.write_text(FIXTURE_TRAINER.format(
        module_dir=str(SOURCE_MODULE_DIR), tests_dir=str(SOURCE_MODULE_DIR / "cadex_tests")),
        encoding="utf-8")
    monkeypatch.setattr(train_module, "TRAINER_SCRIPT", trainer)
    monkeypatch.setenv(train_module.TRAINER_PYTHON_ENV, sys.executable)
    monkeypatch.setenv(loop.MACHINE_LOCK_ENV, str(tmp_path / "slot.lock"))
    root = tmp_path / "project"

    session = _session(root)
    try:
        assert _payload(session.call("write_script", {"source": SCRIPT}))["ok"] is True
        started = _payload(session.call("train_start", {
            "run": "r1", "budget_s": 120, "reason": REASON,
            "settings": {"iterations": 2, "envs": 4, "seed": 3}}))
    finally:
        session.close()
    assert started["ok"] is True and started["task"] == "job", started
    # The session is over and its engine is gone; the run is not.
    run = _until(root / "runs" / "r1", seconds=60.0)
    assert run["state"] == "finished", run
    # It trained the revision the session accepted, from the store's own bundle.
    state = json.loads((root / "script.json").read_text())
    assert run["registration"]["accepted_revision"] == state["accepted_revision"]
    policy = run["status"]["policy"]

    session = _session(root)
    try:
        session.call("train_status", {"run": "r1"})
        put = _payload(session.call("put_asset", {"source_path": policy["path"]}))
        written = _payload(session.call(
            "write_script", {"source": SCRIPT + POLICY.replace("@SHA@", policy["sha256"])}))
        reply = session.call("evaluate", {})
        ledger = _payload(session.call("train_status", {}))["ledger"]
    finally:
        session.close()
    assert put["sha256"] == policy["sha256"]
    assert written["ok"] is True, written
    assert reply["is_error"] is False, reply
    text, *pictures = reply["content"]
    view = json.loads(text["text"])
    # The verdict is the spec's, per predicate and per seed: a block shoved
    # at 6 N completes and stays upright, and does not stay within a micron.
    assert view["verdict"] == "fail" and view["trained_by_run"] == ["r1"]
    assert view["failing"] == ["still (2 of 2)"]
    tally = {row["id"]: row["passed"] for row in view["summary"]["predicates"]}
    assert tally == {"completes": 2, "upright": 2, "still": 0}
    assert [(row["seed"], row["pass"], row["failing"]) for row in view["seeds"]] == [
        (1101, False, ["still"]), (1102, False, ["still"])]
    assert view["seeds"][0]["termination"] == "horizon"
    assert {"max_tilt_deg", "max_drift_mm"} <= set(view["seeds"][0]["metrics"])
    assert [term["label"] for term in view["summary"]["reward"]["terms"]] == ["level"]
    # ...and the film of the first failing seed comes back as two pictures.
    assert view["film"] == {"state": "ready", "error": None, "seeds": [1101]}
    assert [picture["type"] for picture in pictures] == ["image", "image"]
    assert all(base64.b64decode(picture["data"])[:4] == b"\x89PNG" for picture in pictures)
    assert len(text["text"]) < 21_500
    report = Path(view["report"])
    assert report.is_file() and report.is_relative_to(root / "evaluations")
    # The ledger is the round, in order, and the next session can read it.
    assert [row["kind"] for row in ledger] == ["train_registered", "train_ended", "evaluated"]
    assert ledger[-1]["verdict"] == "fail" and ledger[-1]["failing"] == ["still (2 of 2)"]
    assert ledger[-1]["policy_sha256"] == policy["sha256"]


def _real_trainer_python() -> Path | None:
    try:
        python = train_module.resolve_trainer_python(None)
    except train_module.TrainError:
        return None
    probe = subprocess.run([str(python), "-c", "import jax, mujoco, mujoco.mjx"],
                           capture_output=True, text=True)
    return python if probe.returncode == 0 else None


REAL_TRAINER_PYTHON = _real_trainer_python()


@pytest.mark.skipif(REAL_TRAINER_PYTHON is None,
                    reason="No training venv with jax and mujoco (training/SETUP.md).")
def test_the_real_trainer_runs_under_the_supervisor_and_the_engine_takes_its_policy(
        engine, tmp_path, monkeypatch, cpu_training) -> None:
    """The same round with nothing faked: the real trainer on
    CPU for two iterations, a checkpoint on the way, and a policy the live
    engine verifies by the digest the supervisor reported."""

    monkeypatch.setenv(loop.MACHINE_LOCK_ENV, str(tmp_path / "slot.lock"))
    root = tmp_path / "project"
    session = _session(root)
    try:
        session.call("write_script", {"source": SCRIPT})
        session.call("train_start", {
            "run": "real", "budget_s": 600, "reason": REASON,
            "settings": {"iterations": 2, "envs": 4, "seed": 5, "hidden": [8, 8],
                         "checkpoint_every": 1, "label": "loop-real"}})
        status = _payload(session.call("train_status", {"run": "real", "wait_s": 600}))
    finally:
        session.close()
    assert status["state"] == "finished", status
    assert status["progress"]["iteration"] == 1 and status["progress"]["total"] == 2
    assert status["progress"]["reward_per_step"] is not None
    assert len(status["progress"]["reward_curve"]) == 2
    assert {item["tag"] for item in status["checkpoints"]} >= {"best"}
    run = loop.read_run(root / "runs" / "real")
    assert run["status"]["receipt"]["task_sha256"] == run["registration"]["task_sha256"]

    session = _session(root)
    try:
        session.call("put_asset", {"source_path": status["policy"]["path"]})
        written = _payload(session.call(
            "write_script", {"source": SCRIPT + POLICY.replace("@SHA@", status["policy"]["sha256"])}))
    finally:
        session.close()
    assert written["ok"] is True


def test_a_run_names_its_task_bundle_so_a_warm_start_can_be_registered(project) -> None:
    """ot11 ``reach-r3``: the agent tried to warm-start from ``reach-r2`` and
    guessed five paths for ``init_from_parent_task``; ``train_status`` never
    named the parent run's bundle and neither did the refusal, so it trained
    from scratch. The view names the bundle with its digest -- the digest a
    policy's header carries -- and the refusal names every run's bundle."""

    parent = _register(project, run="r1")
    run = _until(Path(loop.launch(parent)["dir"]))
    assert run["state"] == "finished", run
    view = loop.run_view(run)
    bundle = view["task_bundle"]
    registration = json.loads((parent / loop.REGISTRATION_NAME).read_text())
    assert Path(bundle["path"]) == parent / registration["bundle"]
    assert Path(bundle["path"]).is_file()
    assert bundle["sha256"] == registration["task_sha256"] == _sha(Path(bundle["path"]).read_bytes())
    assert "init_from_parent_task" in view["warm_start"]
    policy = view["policy"]["path"]
    # A guessed path is refused with the real ones in the refusal.
    with pytest.raises(loop.LoopError) as refused:
        _register(project, run="r2", settings={
            "iterations": 3, "envs": 4, "seed": 9,
            "init_from": policy,
            "init_from_parent_task": "runs/r1/job-task.json",
            "init_from_task_change": "same task"})
    assert bundle["path"] in str(refused.value) and "r1" in str(refused.value)
    # The path read from the view is accepted as it stands, and nothing is left
    # behind by the refusal above.
    child = _register(project, run="r2", settings={
        "iterations": 3, "envs": 4, "seed": 8,
        "init_from": policy,
        "init_from_parent_task": bundle["path"], "init_from_task_change": "same task"})
    assert json.loads((child / loop.REGISTRATION_NAME).read_text())[
        "settings"]["init_from_parent_task"] == bundle["path"]
