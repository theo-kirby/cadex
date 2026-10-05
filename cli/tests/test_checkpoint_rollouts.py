# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Each checkpoint, rolled out while the run is still training (ADR-544).

The fixture is the orun3 biped's own exported model and task bundle
(``fixtures/orun3-biped/``, copied from its ``probe3`` run). Its checkpoints
are made here, by the engine suite's policy fixture -- random weights for
that bundle -- because a policy binary is never committed. The rollouts run
through the engine the suite resolves, and skip without one.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
import time

import pytest

from conftest import REPO_ROOT, SOURCE_MODULE_DIR

from cadex_cli import loop
from cadex_cli.__main__ import main
from cadex_cli.checkpoints import FAILURE_SUFFIX, TRACE_SUFFIX, CheckpointRollouts, rollout_paths
from cadex_cli.report import EXIT_USAGE
from cadex_cli.smoke import smoke_interpreter
from cadex_cli.train import run_trainer, trainer_flags

BIPED = Path(__file__).parent / "fixtures" / "orun3-biped"
MODEL = "reed_model-model.xml"
TASK = "reed_walk-task.json"
LINKS = ["ground_link", "torso_link", "thigh_l_link", "shin_l_link", "foot_l_link",
         "thigh_r_link", "shin_r_link", "foot_r_link"]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


_POLICIES = """
import hashlib, json, sys
sys.path[:0] = [{module_dir!r}, {tests_dir!r}]
import dynamics_policy_fixtures as pf
task = open(sys.argv[1], "rb").read()
prepared = {{"bundle": json.loads(task), "task_sha256": hashlib.sha256(task).hexdigest()}}
for seed in range(1, int(sys.argv[3]) + 1):
    made = pf.policy_container(prepared, seed=seed)
    open(sys.argv[2] + "/policy-%d.cxpolicy" % seed, "wb").write(made["blob"])
"""


def _policies(tmp_path: Path, count: int) -> list[bytes]:
    """``count`` distinct biped policies, as the trainer would write them."""

    source = tmp_path / "policies"
    source.mkdir()
    script = _POLICIES.format(module_dir=str(SOURCE_MODULE_DIR),
                              tests_dir=str(SOURCE_MODULE_DIR / "cadex_tests"))
    subprocess.run([sys.executable, "-c", script, str(BIPED / TASK), str(source), str(count)],
                   check=True, capture_output=True, text=True)
    return [(source / f"policy-{seed}.cxpolicy").read_bytes() for seed in range(1, count + 1)]


def _train_dir(tmp_path: Path) -> Path:
    train = tmp_path / "train"
    train.mkdir()
    for name in (MODEL, TASK):
        shutil.copyfile(BIPED / name, train / name)
    return train


def _watcher(engine, train: Path, **options) -> CheckpointRollouts:
    return CheckpointRollouts(train, output="walk", bundle=train / TASK, model=train / MODEL,
                              python=smoke_interpreter(engine), module_dir=engine.module_dir,
                              scan_s=0.0, **options)


def _progress(train: Path, rows: list[dict]) -> None:
    (train / "progress.json").write_text(json.dumps({"iteration": 0, "checkpoints": rows}))


def _row(tag: str, blob: bytes, iteration: int, reward: float) -> dict:
    return {"tag": tag, "iteration": iteration, "path": f"walk.{tag}.cxpolicy",
            "sha256": _sha(blob), "reward_per_step": reward}


def test_the_rollout_files_sit_beside_the_checkpoint_and_are_ignored_by_a_project() -> None:
    trace, failure = rollout_paths(Path("runs/r/train/walk.000040.cxpolicy"))
    assert trace == Path("runs/r/train/walk.000040" + TRACE_SUFFIX)
    assert failure == Path("runs/r/train/walk.000040" + FAILURE_SUFFIX)
    # ``*-trace.json`` is the pattern a project's own repository ignores.
    assert trace.name.endswith("-trace.json")


def test_a_negative_checkpoint_interval_is_a_usage_error(tmp_path, capsys) -> None:
    for command in ("train", "walk"):
        code = main([command, "--out", str(tmp_path / "out"), "--project", str(tmp_path / "p"),
                     "--checkpoint-every", "-1", "--json"])
        envelope = json.loads(capsys.readouterr().out)
        assert code == EXIT_USAGE and "--checkpoint-every" in envelope["error"], envelope
    assert trainer_flags(iterations=2, envs=3)[-1] != "--checkpoint-every"
    assert trainer_flags(iterations=2, envs=3, checkpoint_every=20)[-2:] == [
        "--checkpoint-every", "20"]


def test_each_numbered_checkpoint_becomes_a_tagged_biped_trace_newest_first(
        engine, tmp_path) -> None:
    first, second, best, final = _policies(tmp_path, 4)
    train = _train_dir(tmp_path)
    (train / "walk.000020.cxpolicy").write_bytes(first)
    (train / "walk.000040.cxpolicy").write_bytes(second)
    (train / "walk.best.cxpolicy").write_bytes(best)
    (train / "walk.cxpolicy").write_bytes(final)
    watcher = _watcher(engine, train)
    # The trainer writes a checkpoint before its progress names it: an
    # unlisted checkpoint waits, rather than being labelled with a guess.
    _progress(train, [_row("000020", first, 19, 0.7)])
    assert [row["tag"] for row in watcher.pending()] == ["000020"]
    _progress(train, [_row("000020", first, 19, 0.7), _row("000040", second, 39, 1.1),
                      _row("best", best, 35, 1.2)])
    assert [row["tag"] for row in watcher.pending()] == ["000040", "000020"]

    watcher.poll()
    started = watcher._child[1].name
    assert started == "walk.000040.cxpolicy"  # the newest goes first
    deadline = time.monotonic() + 60.0
    while (watcher.pending() or watcher._child) and time.monotonic() < deadline:
        watcher.poll()
        time.sleep(0.05)
    watcher.drain()
    assert watcher.summary() == {"written": 2, "failed": 0}
    assert sorted(path.name for path in train.glob("*-trace.json")) == [
        "walk.000020.rollout-trace.json", "walk.000040.rollout-trace.json"]

    for tag, blob, iteration, reward in (("000020", first, 19, 0.7), ("000040", second, 39, 1.1)):
        trace = json.loads(rollout_paths(train / f"walk.{tag}.cxpolicy")[0].read_text())
        assert trace["schema"] == "cadex-assembly-simulation-trace-v1"
        assert trace["simulation_output"] == "checkpoint"
        assert trace["component_outputs"] == LINKS
        assert trace["checkpoint"]["tag"] == tag and trace["checkpoint"]["iteration"] == iteration
        assert trace["checkpoint"]["reward_per_step"] == reward
        assert trace["checkpoint"]["sha256"] == _sha(blob) == trace["policy"]["policy_sha256"]
        assert trace["policy"]["task_sha256"] == _sha((BIPED / TASK).read_bytes())
        # The nominal episode: no seed, so every checkpoint plays the same one.
        assert trace["policy"]["seed"] is None and trace["parameters"]["frames_per_second"] == 25
        assert trace["frames"][0]["frame_kind"] == "input"
        assert len(trace["frames"]) >= 2
        assert all(set(frame["component_placements"]) == set(LINKS) for frame in trace["frames"])
    # ``best`` is rewritten in place and the final policy is the run's own.
    assert not rollout_paths(train / "walk.best.cxpolicy")[0].exists()
    assert not rollout_paths(train / "walk.cxpolicy")[0].exists()
    # Once done, a checkpoint is not rolled out again.
    assert watcher.pending(final=True) == []


def test_a_checkpoint_that_cannot_be_played_is_a_failure_with_its_reason(engine, tmp_path) -> None:
    train = _train_dir(tmp_path)
    (train / "walk.000020.cxpolicy").write_bytes(b"not a policy")
    watcher = _watcher(engine, train)
    # The trainer is gone and never listed it: the tag names the iteration,
    # and the reward is left unmeasured.
    assert watcher.pending() == []
    (row,) = watcher.pending(final=True)
    assert (row["iteration"], row["reward_per_step"]) == (19, None)
    watcher.drain()
    trace, failure = rollout_paths(train / "walk.000020.cxpolicy")
    assert not trace.exists()
    record = json.loads(failure.read_text())
    assert record["schema"] == "cadex-checkpoint-rollout-failure-v1"
    assert record["tag"] == "000020" and record["iteration"] == 19
    assert record["reason"] and record["error"]
    assert watcher.summary() == {"written": 0, "failed": 1}


def test_a_rollout_past_its_bound_is_killed_and_recorded(engine, tmp_path, monkeypatch) -> None:
    train = _train_dir(tmp_path)
    (train / "walk.000020.cxpolicy").write_bytes(_policies(tmp_path, 1)[0])
    slow = tmp_path / "slow.py"
    slow.write_text("import time; time.sleep(60)\n")
    monkeypatch.setattr("cadex_cli.checkpoints.RUNNER_SCRIPT", slow)
    watcher = _watcher(engine, train, timeout_s=0.5)
    began = time.monotonic()
    watcher.drain()
    assert time.monotonic() - began < 10.0
    record = json.loads(rollout_paths(train / "walk.000020.cxpolicy")[1].read_text())
    assert record["reason"] == "rollout_timeout"


#: A trainer with the real one's checkpoint contract: each checkpoint written
#: atomically, then named in ``progress.json`` with its digest. After each
#: one it **waits for that checkpoint's trace** before going on, so the test
#: holds only if the rollout happens while the trainer is still running.
CHECKPOINTING_TRAINER = textwrap.dedent(
    """
    import hashlib, json, sys, time
    from pathlib import Path
    argv = sys.argv[1:]
    out = Path(argv[argv.index("--out") + 1])
    source = Path(argv[argv.index("--source") + 1])
    rows = []
    blobs = sorted(source.glob("policy-*.cxpolicy"))
    for number, blob_path in enumerate(blobs[:-1], start=1):
        blob = blob_path.read_bytes()
        tag = "%06d" % (number * 20)
        path = out.with_name(f"{out.stem}.{tag}{out.suffix}")
        path.with_name(path.name + ".partial").write_bytes(blob)
        path.with_name(path.name + ".partial").replace(path)
        rows.append({"tag": tag, "iteration": number * 20 - 1, "path": path.name,
                     "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest(),
                     "reward_per_step": float(number)})
        (out.parent / "progress.json").write_text(json.dumps(
            {"iteration": number * 20 - 1, "total": 60, "checkpoints": rows}))
        trace = out.with_name(f"{out.stem}.{tag}.rollout-trace.json")
        deadline = time.monotonic() + 60
        while not trace.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        print(f"checkpoint {tag} seen={trace.exists()}", file=sys.stderr, flush=True)
    blob = blobs[-1].read_bytes()
    out.write_bytes(blob)
    print(json.dumps({"out": str(out), "bytes": len(blob),
                      "sha256": hashlib.sha256(blob).hexdigest(), "wall_time_s": 0.0}))
    """
)


def test_cadex_trains_rolled_out_checkpoints_arrive_while_the_trainer_runs(
        engine, tmp_path, capfd) -> None:
    """``cadex train``'s path: :func:`run_trainer` polling the watcher."""

    _policies(tmp_path, 3)
    train = _train_dir(tmp_path)
    script = tmp_path / "trainer.py"
    script.write_text(CHECKPOINTING_TRAINER)
    watcher = _watcher(engine, train)
    try:
        receipt = run_trainer([sys.executable, str(script), "--out", str(train / "walk.cxpolicy"),
                               "--source", str(tmp_path / "policies")], on_poll=watcher.poll)
    finally:
        watcher.drain()
    assert receipt["sha256"] == _sha((train / "walk.cxpolicy").read_bytes())
    said = capfd.readouterr().err
    assert "checkpoint 000020 seen=True" in said and "checkpoint 000040 seen=True" in said
    assert watcher.summary() == {"written": 2, "failed": 0}
    second = json.loads((train / "walk.000040.rollout-trace.json").read_text())
    assert (second["checkpoint"]["iteration"], second["checkpoint"]["reward_per_step"]) == (39, 2.0)


def test_the_supervisor_rolls_out_checkpoints_while_its_run_trains(engine, tmp_path, monkeypatch) -> None:
    """``train_start``'s path: the detached supervisor polling the watcher."""

    _policies(tmp_path, 3)
    run_dir = tmp_path / "project" / "runs" / "r1"
    train = run_dir / "train"
    train.mkdir(parents=True)
    for name in (MODEL, TASK):
        shutil.copyfile(BIPED / name, train / name)
    script = tmp_path / "trainer.py"
    script.write_text(CHECKPOINTING_TRAINER)
    registration = {
        "schema": loop.REGISTRATION_SCHEMA, "run": "r1", "registered_at": time.time(),
        "budget_s": 120.0, "task_output": "walk", "task_sha256": _sha((train / TASK).read_bytes()),
        "bundle": f"train/{TASK}", "model": f"train/{MODEL}", "policy": "train/walk.cxpolicy",
        "command": [sys.executable, str(script), "--out", str(train / "walk.cxpolicy"),
                    "--source", str(tmp_path / "policies"), "--checkpoint-every", "20"],
    }
    (run_dir / loop.REGISTRATION_NAME).write_text(json.dumps(registration))
    (run_dir / loop.STATUS_NAME).write_text(json.dumps(
        {"schema": loop.STATUS_SCHEMA, "run": "r1", "state": "registered"}))
    environment = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "cli"),
                   loop.MACHINE_LOCK_ENV: str(tmp_path / "slot.lock")}
    if engine.source != "dev-tree":
        environment["CADEX_ENGINE_ROOT"] = str(engine.root)
    subprocess.run([sys.executable, "-m", "cadex_cli.loop", str(run_dir)], env=environment,
                   check=True, timeout=180)
    status = json.loads((run_dir / loop.STATUS_NAME).read_text())
    assert status["state"] == "finished", status
    log = (train / loop.LOG_NAME).read_text()
    assert "checkpoint 000020 seen=True" in log and "checkpoint 000040 seen=True" in log
    assert sorted(path.name for path in train.glob("*-trace.json")) == [
        "walk.000020.rollout-trace.json", "walk.000040.rollout-trace.json"]
