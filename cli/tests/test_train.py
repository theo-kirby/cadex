# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``cadex train``: the dispatcher for the offboard trainer (ADR-191).

Pin trainer flags, receipts and the rebuild → bundle → train → policy leg.
Fake trainers cover dispatch contracts; real CPU tests skip without a venv.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import textwrap

import pytest

from cadex_cli import train as train_module
from cadex_cli.__main__ import main
from cadex_cli.export import ExportedOutput
from cadex_cli.report import EXIT_FAILURE, EXIT_OK, EXIT_REJECTED, EXIT_USAGE
from cadex_cli.train import (
    REMOTE_TRANSPORT_STEPS,
    TrainError,
    find_task,
    remote_trainer_command,
    resolve_bundle_model,
    resolve_trainer_python,
    run_trainer,
    trainer_command,
    verify_returned_policy,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
TRAINER_SOURCE = REPO_ROOT / "training" / "cadex_train.py"
REMOTE_SOURCE = REPO_ROOT / "training" / "remote_train.sh"

#: The smallest script that exports a training task: one revolute joint,
#: one motor, three observations. Lifted from the engine's lifecycle gate.
TASK_SCRIPT = """
plate = part.box(60, 60, 6)
arm = part.box(80, 8, 8)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin",
                                      offset={"position": [12, 0, 6],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}),
                   assembly.connector(swing, "origin",
                                      offset={"position": [0, 0, 0],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
motor = assembly.actuator(j, kind="motor", control_nmm="120*sin(2*pi*time)",
                          torque_limit_nmm=400)
model = assembly.mjcf(asm, [
    assembly.body(base, density_kg_m3=2700),
    assembly.body(swing, density_kg_m3=7850),
], actuators=[motor], observations=[
    assembly.observation(j, "position", name="angle"),
    assembly.observation(swing, "centre_of_mass", name="com"),
    assembly.observation(motor, "actuator_force", name="effort"),
])
job = assembly.task(model, actions=[motor],
                    reward=[assembly.reward("-(com_z - 60)^2", weight=1.0e-4,
                                            label="lift"),
                            assembly.reward("abs(effort)", weight=-1.0e-6,
                                            label="control_cost")],
                    episode_seconds=1.0, control_hz=50, label="lift")
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag, "model": model, "job": job}
"""

#: A trainer that checks it was handed a bundle, writes a policy and prints
#: a receipt shaped like the real one. It also echoes its argv into the
#: receipt so a test can see the flags it was called with.
FAKE_TRAINER = textwrap.dedent(
    """
    import hashlib, json, sys
    from pathlib import Path
    argv = sys.argv[1:]
    bundle = Path(argv[0])
    assert bundle.is_file(), bundle
    task = json.loads(bundle.read_text())
    out = Path(argv[argv.index("--out") + 1])
    blob = b"CXPOLICY-fake\\n" * 32
    out.write_bytes(blob)
    print("progress: pretending to train", file=sys.stderr)
    print("not the receipt")
    print(json.dumps({
        "out": str(out), "bytes": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
        "reward_per_step": 1.5, "wall_time_s": 0.01, "device": "fake",
        "task_sha256": task.get("sha256", ""), "argv": argv,
    }, sort_keys=True))
    """
)


@pytest.fixture
def fake_trainer(tmp_path, monkeypatch) -> Path:
    script = tmp_path / "fake_train.py"
    script.write_text(FAKE_TRAINER, encoding="utf-8")
    monkeypatch.setattr(train_module, "TRAINER_SCRIPT", script)
    return script


#: A stand-in for ``training/remote_train.sh train`` (ADR-200): the same
#: argv contract — ``train <bundle> <out> [--allow-cpu] -- <trainer flags>``
#: — and the same three steps with no box: it resolves the model the way
#: the real script does (beside the bundle, by name) and fails if it is
#: not there, writes the policy to ``out``, and prints what the real one
#: prints — the trainer's stdout with MuJoCo's ``warp`` noise ahead of the
#: receipt, then its own ``==>`` trailer lines after it. ``FAKE_REMOTE_MODE``
#: picks the failure: ``mismatch`` returns the wrong bytes, ``nofile``
#: returns nothing, ``cpu`` is the device refusal, exit 1 with the reason
#: on stdout, which is where the real script puts it.
FAKE_REMOTE = textwrap.dedent(
    """\
    #!/usr/bin/env bash
    set -eu
    exec "@PYTHON@" - "$@" <<'PY'
    import hashlib, json, os, pathlib, sys
    argv = sys.argv[1:]
    with open(os.environ["FAKE_REMOTE_LOG"], "a") as log:
        log.write(json.dumps(argv) + "\\n")
    assert argv[0] == "train", argv
    positional = [a for a in argv[1:argv.index("--")] if not a.startswith("--")]
    bundle, out = map(pathlib.Path, positional)
    allow_cpu = "--allow-cpu" in argv[:argv.index("--")]
    flags = argv[argv.index("--") + 1:]
    if not bundle.is_file():
        print(f"FAIL: {bundle} does not exist."); sys.exit(1)
    task = json.loads(bundle.read_text())
    relative = pathlib.Path(str(task["model"]["path"]))
    if not any(c.exists() for c in (bundle.parent.parent / relative, bundle.parent / relative.name)):
        print("FAIL: the model this bundle references is beside neither."); sys.exit(1)
    mode = os.environ.get("FAKE_REMOTE_MODE", "ok")
    device = "cpu" if mode == "cpu" else "gpu"
    blob = b"remote policy for " + bundle.read_bytes()
    sha = hashlib.sha256(blob).hexdigest()
    if mode == "mismatch":
        blob = b"something else"
    if mode != "nofile":
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(blob)
    print("Failed to import warp: No module named 'warp'")
    print(json.dumps({"out": "/work/" + bundle.stem + "-run/" + out.name, "bytes": len(blob),
                      "sha256": sha, "reward_per_step": 2.5, "wall_time_s": 0.02,
                      "device": device, "task_sha256": task.get("sha256", ""),
                      "argv": flags}, sort_keys=True))
    if device != "gpu" and not allow_cpu:
        print("FAIL: the run reports device 'cpu', not 'gpu'.")
        print("      A silent CPU fallback is the failure this exists to make loud.")
        sys.exit(1)
    print(f"==> {out}")
    print(f"==> sha256 {sha}   (device {device})")
    PY
    """
)


@pytest.fixture
def fake_remote(tmp_path, monkeypatch) -> Path:
    """``REMOTE_SCRIPT`` answered by :data:`FAKE_REMOTE`; returns its argv log."""

    script = tmp_path / "fake_remote_train.sh"
    script.write_text(FAKE_REMOTE.replace("@PYTHON@", sys.executable), encoding="utf-8")
    script.chmod(0o755)
    log = tmp_path / "remote.log"
    monkeypatch.setenv("FAKE_REMOTE_LOG", str(log))
    monkeypatch.delenv("FAKE_REMOTE_MODE", raising=False)
    monkeypatch.setattr(train_module, "REMOTE_SCRIPT", script)
    return log


def _run(capsys, *argv: str) -> tuple[int, dict]:
    code = main([*argv, "--json"])
    return code, json.loads(capsys.readouterr().out)


# -- the flags are the trainer's own ------------------------------------


def test_the_dispatcher_emits_flags_the_trainer_declares() -> None:
    """Read the trainer's argparse back out of its source: a flag renamed
    there fails here, instead of in a pipeline at two in the morning."""

    source = TRAINER_SOURCE.read_text(encoding="utf-8")
    declared = set(re.findall(r'add_argument\(\s*"(--[a-z-]+)"', source))
    command = trainer_command(
        "python", "b/t-task.json", "b/t.cxpolicy",
        iterations=3, envs=4, seed=7, label="x", init_from="p.cxpolicy",
        init_from_parent_task="b0/t-task.json",
        init_from_task_change="a harder band",
        script="train.py",
    )
    used = {item for item in command if item.startswith("--")}
    assert used <= declared, used - declared
    assert {"--init-from-parent-task", "--init-from-task-change"} <= used
    assert command[:3] == ["python", "train.py", "b/t-task.json"]
    assert command[command.index("--out") + 1] == "b/t.cxpolicy"
    assert command[command.index("--iterations") + 1] == "3"
    assert command[command.index("--envs") + 1] == "4"
    # The two flags the audit caught the agent guessing are not ours.
    assert "--num-envs" not in declared and "--output" not in declared


def test_the_default_script_is_the_repo_trainer() -> None:
    assert train_module.TRAINER_SCRIPT == TRAINER_SOURCE
    assert TRAINER_SOURCE.is_file()


# -- the remote leg (ADR-200) ----------------------------------------------


def test_the_remote_command_is_the_dispatcher_with_the_same_flags_after_the_dash() -> None:
    """``remote_train.sh train <bundle> <out> [--allow-cpu] -- <flags>``: the
    flags after ``--`` are byte-for-byte the local trainer's, so the two
    legs cannot drift apart; and the usage line is read back out of the
    script so a change to its contract fails here."""

    kwargs = dict(iterations=3, envs=4, seed=7, label="x")
    command = remote_trainer_command(
        "b/t-task.json", "b/t.cxpolicy", allow_cpu=True, script="remote.sh", **kwargs
    )
    assert command[:5] == ["remote.sh", "train", "b/t-task.json", "b/t.cxpolicy",
                           "--allow-cpu"]
    assert command[5] == "--"
    local = trainer_command("python", "b/t-task.json", "b/t.cxpolicy",
                            script="train.py", **kwargs)
    assert command[6:] == local[5:] == [
        "--iterations", "3", "--envs", "4", "--seed", "7", "--label", "x",
    ]
    cold = remote_trainer_command("b/t-task.json", "b/t.cxpolicy", script="r", **kwargs)
    assert "--allow-cpu" not in cold and cold[4] == "--"

    # The default is the repository's dispatcher, and its own usage line
    # is the contract this builds against.
    assert train_module.REMOTE_SCRIPT == REMOTE_SOURCE and REMOTE_SOURCE.is_file()
    source = REMOTE_SOURCE.read_text(encoding="utf-8")
    assert "train <bundle.json> <out.cxpolicy> [--allow-cpu] [--detach] [-- trainer args]" in source
    assert 'seen_dashdash' in source and '--allow-cpu) allow_cpu=1' in source

    # A warm start is refused here: the script carries two files out and
    # the --init-from policy is not one of them.
    with pytest.raises(TrainError, match="trains cold"):
        remote_trainer_command(
            "b/t-task.json", "b/t.cxpolicy", script="r", init_from="p.cxpolicy", **kwargs
        )


def test_a_returned_policy_is_verified_against_the_receipt(
    fake_remote, tmp_path, monkeypatch
) -> None:
    """The receipt is read past the dispatcher's trailer lines; the file
    that came back must hash to what the receipt claims; ``out`` becomes
    the local path and the box's path is kept beside it."""

    bundle = tmp_path / "run" / "job-task.json"
    bundle.parent.mkdir()
    bundle.write_text(json.dumps({"sha256": "abc", "model": {"path": "x/model-model.xml"}}))
    (tmp_path / "run" / "model-model.xml").write_text("<mujoco/>")
    out = tmp_path / "run" / "job.cxpolicy"
    command = remote_trainer_command(bundle, out, iterations=1, envs=2)

    receipt = run_trainer(command)
    assert receipt["device"] == "gpu"
    assert receipt["out"].startswith("/work/job-task-run/")
    verify_returned_policy(out, receipt)
    assert receipt["out"] == str(out)
    assert receipt["trainer_out"].startswith("/work/")
    assert receipt["sha256"] == hashlib.sha256(out.read_bytes()).hexdigest()
    (argv,) = [json.loads(line) for line in fake_remote.read_text().splitlines()]
    assert argv == ["train", str(bundle), str(out), "--", "--iterations", "1",
                    "--envs", "2", "--seed", "0"]

    # The wrong bytes at the right path: a refusal naming both digests.
    monkeypatch.setenv("FAKE_REMOTE_MODE", "mismatch")
    receipt = run_trainer(command)
    with pytest.raises(TrainError, match="hashes .*the trainer wrote"):
        verify_returned_policy(out, receipt)

    # Nothing came back at all.
    monkeypatch.setenv("FAKE_REMOTE_MODE", "nofile")
    out.unlink()
    receipt = run_trainer(command)
    with pytest.raises(TrainError, match="nothing came back"):
        verify_returned_policy(out, receipt)

    # The device refusal: the dispatcher exits 1 with its reason on stdout,
    # and the reason reaches the error rather than the bin.
    monkeypatch.setenv("FAKE_REMOTE_MODE", "cpu")
    with pytest.raises(TrainError, match=r"(?s)exited 1.*device 'cpu'") as caught:
        run_trainer(command)
    assert "silent CPU fallback" in str(caught.value)
    # ...and --allow-cpu is what accepts it.
    receipt = run_trainer(
        remote_trainer_command(bundle, out, allow_cpu=True, iterations=1, envs=2)
    )
    assert receipt["device"] == "cpu"
    verify_returned_policy(out, receipt)


# -- which interpreter ---------------------------------------------------


def test_the_interpreter_is_explicit_then_env_then_the_documented_venvs(
    tmp_path, monkeypatch
) -> None:
    explicit = tmp_path / "explicit"
    from_env = tmp_path / "from-env"
    venv = tmp_path / "venv" / "bin" / "python"
    for path in (explicit, from_env, venv):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    monkeypatch.setattr(train_module, "TRAINER_VENV_CANDIDATES", (venv,))
    monkeypatch.setenv(train_module.TRAINER_PYTHON_ENV, str(from_env))

    assert resolve_trainer_python(str(explicit)) == explicit
    assert resolve_trainer_python(None) == from_env
    monkeypatch.delenv(train_module.TRAINER_PYTHON_ENV)
    assert resolve_trainer_python(None) == venv

    with pytest.raises(TrainError, match="explicit-missing"):
        resolve_trainer_python(str(tmp_path / "explicit-missing"))
    monkeypatch.setattr(train_module, "TRAINER_VENV_CANDIDATES", ())
    with pytest.raises(TrainError, match="SETUP.md"):
        resolve_trainer_python(None)


# -- which task ----------------------------------------------------------


def _task(name: str) -> ExportedOutput:
    return ExportedOutput(
        name=name, kind=train_module.TASK_KIND,
        files={"json": f"/out/{name}-task.json"},
    )


def test_the_task_is_the_one_exported_or_the_one_named() -> None:
    brep = ExportedOutput(name="plate", kind="brep", files={"step": "/p.step"})
    skipped = ExportedOutput(name="job2", kind=train_module.TASK_KIND, skipped="x")
    assert find_task([brep, _task("job"), skipped]).name == "job"
    assert find_task([_task("a"), _task("b")], "b").name == "b"
    with pytest.raises(TrainError, match="more than one"):
        find_task([_task("a"), _task("b")])
    with pytest.raises(TrainError, match="no training task"):
        find_task([brep])
    with pytest.raises(TrainError, match="it has: a"):
        find_task([_task("a")], "zz")


# -- the receipt ---------------------------------------------------------


def test_the_receipt_is_the_last_json_line_and_nothing_else(
    fake_trainer, tmp_path
) -> None:
    bundle = tmp_path / "t-task.json"
    bundle.write_text(json.dumps({"sha256": "abc"}), encoding="utf-8")
    out = tmp_path / "t.cxpolicy"
    receipt = run_trainer(
        trainer_command(sys.executable, bundle, out, iterations=1, envs=1)
    )
    assert receipt["out"] == str(out)
    assert receipt["sha256"] == hashlib.sha256(out.read_bytes()).hexdigest()
    assert receipt["task_sha256"] == "abc"


def test_a_trainer_that_fails_or_hangs_is_a_failure_with_the_reason(
    tmp_path
) -> None:
    crash = tmp_path / "crash.py"
    crash.write_text("import sys; sys.exit(4)\n", encoding="utf-8")
    with pytest.raises(TrainError, match="exited 4"):
        run_trainer([sys.executable, str(crash)])

    silent = tmp_path / "silent.py"
    silent.write_text("print('no json here')\n", encoding="utf-8")
    with pytest.raises(TrainError, match="no receipt"):
        run_trainer([sys.executable, str(silent)])

    hang = tmp_path / "hang.py"
    hang.write_text("import time; time.sleep(30)\n", encoding="utf-8")
    with pytest.raises(TrainError, match="stopped after 0.5s"):
        run_trainer([sys.executable, str(hang)], timeout=0.5)


# -- the command, end to end ---------------------------------------------


def test_usage_errors_come_before_any_engine_or_trainer(tmp_path, capsys) -> None:
    project = tmp_path / "project"
    code, envelope = _run(capsys, "train", "--project", str(project))
    assert code == EXIT_USAGE and "--out" in envelope["error"], envelope
    code, envelope = _run(
        capsys, "train", "--project", str(project), "--out", str(tmp_path / "o"),
        "--iterations", "0",
    )
    assert code == EXIT_USAGE and "--iterations" in envelope["error"], envelope
    code, envelope = _run(
        capsys, "train", "--project", str(project), "--out", str(tmp_path / "o"),
        "--name", "walk.bin",
    )
    assert code == EXIT_USAGE and ".cxpolicy" in envelope["error"], envelope
    code, envelope = _run(
        capsys, "train", "--project", str(project), "--out", str(tmp_path / "o"),
        "--trainer-python", str(tmp_path / "nope"),
    )
    assert code == EXIT_FAILURE and "nope" in envelope["error"], envelope
    # The curriculum pair travels together, with --init-from (ADR-192).
    for apart in (
        ["--init-from-task-change", "why"],
        ["--init-from-parent-task", "t.json"],
        ["--init-from", "p.cxpolicy", "--init-from-task-change", "why"],
    ):
        code, envelope = _run(
            capsys, "train", "--project", str(project), "--out",
            str(tmp_path / "o"), *apart,
        )
        assert code == EXIT_USAGE, (apart, envelope)
        assert "--init-from-parent-task" in envelope["error"], envelope
    # --remote's company (ADR-200): the box has its own venv, --allow-cpu
    # is the dispatcher's flag, and a warm start is not carried out.
    for wrong, word in (
        (["--remote", "--trainer-python", sys.executable], "CADEX_TRAIN_VENV"),
        (["--allow-cpu"], "--remote"),
        (["--remote", "--init-from", "p.cxpolicy", "--init-from-parent-task", "t.json",
          "--init-from-task-change", "why"], "trains cold"),
    ):
        code, envelope = _run(
            capsys, "train", "--project", str(project), "--out",
            str(tmp_path / "o"), *wrong,
        )
        assert code == EXIT_USAGE, (wrong, envelope)
        assert word in envelope["error"], envelope
    assert not project.exists()


@pytest.fixture
def task_project(engine, tmp_path, capsys) -> Path:
    script = tmp_path / "task.py"
    script.write_text(TASK_SCRIPT, encoding="utf-8")
    root = tmp_path / "project"
    code, envelope = _run(capsys, "script", "--set", str(script), "--project", str(root))
    assert code == EXIT_OK, envelope
    return root


def test_the_leg_runs_as_one_command_and_the_policy_comes_home(
    task_project, fake_trainer, tmp_path, capsys
) -> None:
    out = tmp_path / "run1"
    code, envelope = _run(
        capsys, "train", "--project", str(task_project), "--out", str(out),
        "--trainer-python", sys.executable, "--iterations", "2", "--envs", "4",
        "--label", "toy", "--put",
    )
    assert code == EXIT_OK, envelope
    # The bundle went out under its staged names, beside the policy.
    assert (out / "job-task.json").is_file() and (out / "model-model.xml").is_file()
    assert (out / "job.cxpolicy").is_file()
    receipt = envelope["training"]
    assert receipt["out"] == str(out / "job.cxpolicy")
    assert receipt["argv"][0] == str(out / "job-task.json")
    assert receipt["argv"][receipt["argv"].index("--iterations") + 1] == "2"
    assert receipt["argv"][receipt["argv"].index("--envs") + 1] == "4"
    assert "--label" in receipt["argv"] and "--init-from" not in receipt["argv"]
    # ...and it is in the store, with the engine's digest matching the
    # trainer's.
    (stored,) = envelope["assets"]
    assert stored["name"] == "job.cxpolicy"
    assert stored["sha256"] == receipt["sha256"]
    assert (task_project / "assets" / "job.cxpolicy").read_bytes() == (
        out / "job.cxpolicy"
    ).read_bytes()
    assert envelope["digest"], envelope
    assert any("trained job" in note for note in envelope["notes"]), envelope


def test_the_remote_leg_lands_the_same_artifacts_as_the_local_one(
    task_project, fake_remote, tmp_path, capsys
) -> None:
    """``cadex train --remote --put`` (ADR-200) against the real engine and
    the fake dispatcher: the bundle and the model are exported where the
    dispatcher looks for them, the policy comes back to the path the local
    trainer would have written, and the store gets it under the same name
    with the receipt's digest — the project cannot tell the two apart."""

    out = tmp_path / "run-remote"
    code, envelope = _run(
        capsys, "train", "--project", str(task_project), "--out", str(out),
        "--remote", "--allow-cpu", "--iterations", "2", "--envs", "4",
        "--label", "toy", "--put",
    )
    assert code == EXIT_OK, envelope
    assert (out / "job-task.json").is_file() and (out / "model-model.xml").is_file()
    assert (out / "job.cxpolicy").is_file()
    receipt = envelope["training"]
    assert receipt["out"] == str(out / "job.cxpolicy")
    assert receipt["trainer_out"] == "/work/job-task-run/job.cxpolicy"
    assert receipt["device"] == "gpu"
    (argv,) = [json.loads(line) for line in fake_remote.read_text().splitlines()]
    assert argv[:4] == ["train", str(out / "job-task.json"), str(out / "job.cxpolicy"),
                        "--allow-cpu"]
    assert argv[4] == "--" and argv[5:] == [
        "--iterations", "2", "--envs", "4", "--seed", "0", "--label", "toy",
    ]
    (stored,) = envelope["assets"]
    assert stored["name"] == "job.cxpolicy" and stored["sha256"] == receipt["sha256"]
    assert (task_project / "assets" / "job.cxpolicy").read_bytes() == (
        out / "job.cxpolicy"
    ).read_bytes()
    assert any("trained job" in note for note in envelope["notes"]), envelope


def test_the_dry_run_plans_the_leg_in_both_modes_and_runs_neither(
    task_project, fake_trainer, fake_remote, tmp_path, capsys
) -> None:
    """``--dry-run`` (ADR-255) against the real engine: the export really
    happens, the trainer does not, and the local and remote plans name the
    same files. This is the offline half of the claim ADR-200 makes — that
    the box's leg lands what this machine's would — checked without a box.
    """

    out = tmp_path / "run-plan"
    common = (
        "train", "--project", str(task_project), "--out", str(out),
        "--iterations", "2", "--envs", "4", "--label", "toy", "--put",
        "--dry-run",
    )
    code, local = _run(capsys, *common, "--trainer-python", sys.executable)
    assert code == EXIT_OK, local
    code, remote = _run(capsys, *common, "--remote", "--allow-cpu")
    assert code == EXIT_OK, remote

    # The bundle and the model are on disk; the policy and the asset are not,
    # and neither trainer ran: the fake dispatcher never wrote its argv log.
    assert (out / "job-task.json").is_file() and (out / "model-model.xml").is_file()
    assert not (out / "job.cxpolicy").exists()
    assert not (task_project / "assets" / "job.cxpolicy").exists()
    assert not fake_remote.exists()
    assert "training" not in local and "training" not in remote

    plans = (local["training_plan"], remote["training_plan"])
    for plan in plans:
        assert plan["executed"] is False
        assert plan["artifacts"] == {
            "bundle": str(out / "job-task.json"),
            "model": str(out / "model-model.xml"),
            "policy": str(out / "job.cxpolicy"),
            "stored_asset": "job.cxpolicy",
        }
    # Same steps, plus the transport the box needs and nothing else.
    steps = [[str(step["step"]) for step in plan["steps"]] for plan in plans]
    assert steps[0] == ["export", "train", "verify", "store"]
    assert [name for name in steps[1] if name not in REMOTE_TRANSPORT_STEPS] == steps[0]
    assert set(steps[1]) - set(steps[0]) == set(REMOTE_TRANSPORT_STEPS)
    # ...and the trainer's own flags are the same wherever it runs.
    local_command, remote_command = (plan["command"] for plan in plans)
    assert local["training_plan"]["mode"] == "local"
    assert remote["training_plan"]["mode"] == "remote"
    assert remote_command[:4] == [
        remote["training_plan"]["runner"], "train",
        str(out / "job-task.json"), str(out / "job.cxpolicy"),
    ]
    assert local_command[local_command.index("--out") + 2:] == (
        remote_command[remote_command.index("--") + 1:]
    )


def test_a_bundle_whose_model_is_missing_is_a_planning_failure(tmp_path) -> None:
    """The model resolution the plan shares with ``remote_train.sh``: the
    recorded relative path, then the basename beside the bundle, then a
    refusal — a dispatch that would have failed after the copy started."""

    bundle = tmp_path / "run" / "job-task.json"
    bundle.parent.mkdir()
    bundle.write_text(json.dumps({"model": {"path": "model/model-model.xml"}}))
    with pytest.raises(TrainError) as refused:
        resolve_bundle_model(bundle)
    assert "beside neither" in str(refused.value)
    beside = bundle.parent / "model-model.xml"
    beside.write_text("<mujoco/>")
    assert resolve_bundle_model(bundle) == beside


def test_the_curriculum_pair_reaches_the_trainer_as_given(
    task_project, fake_trainer, tmp_path, capsys
) -> None:
    """``--init-from`` with the ADR-161 pair is passed through by name;
    the trainer owns the rule about which task keys may move."""

    parent = tmp_path / "parent-task.json"
    parent.write_text("{}", encoding="utf-8")
    warm = tmp_path / "warm.cxpolicy"
    warm.write_bytes(b"x")
    out = tmp_path / "run-curriculum"
    code, envelope = _run(
        capsys, "train", "--project", str(task_project), "--out", str(out),
        "--trainer-python", sys.executable, "--init-from", str(warm),
        "--init-from-parent-task", str(parent),
        "--init-from-task-change", "lift weight doubled",
    )
    assert code == EXIT_OK, envelope
    argv = envelope["training"]["argv"]
    assert argv[argv.index("--init-from") + 1] == str(warm)
    assert argv[argv.index("--init-from-parent-task") + 1] == str(parent)
    assert argv[argv.index("--init-from-task-change") + 1] == "lift weight doubled"


def test_without_put_nothing_reaches_the_store_and_name_is_honoured(
    task_project, fake_trainer, tmp_path, capsys
) -> None:
    out = tmp_path / "run2"
    code, envelope = _run(
        capsys, "train", "--project", str(task_project), "--out", str(out),
        "--trainer-python", sys.executable, "--name", "walk.cxpolicy",
    )
    assert code == EXIT_OK, envelope
    assert (out / "walk.cxpolicy").is_file()
    assert "assets" not in envelope
    assert not (task_project / "assets" / "walk.cxpolicy").exists()


def test_a_project_with_no_task_is_a_refusal_not_a_trainer_run(
    engine, fake_trainer, tmp_path, capsys
) -> None:
    script = tmp_path / "block.py"
    script.write_text('result = {"block": part.box(10, 10, 10)}\n', encoding="utf-8")
    root = tmp_path / "project"
    code, _ = _run(capsys, "script", "--set", str(script), "--project", str(root))
    assert code == EXIT_OK
    out = tmp_path / "run3"
    code, envelope = _run(
        capsys, "train", "--project", str(root), "--out", str(out),
        "--trainer-python", sys.executable,
    )
    assert code == EXIT_REJECTED, envelope
    assert "no training task" in envelope["error"], envelope
    assert not list(out.glob("*.cxpolicy"))


# -- the real trainer, in the real venv ----------------------------------


def _real_trainer_python() -> Path | None:
    try:
        python = resolve_trainer_python(None)
    except TrainError:
        return None
    probe = subprocess.run(
        [str(python), "-c", "import jax, mujoco, mujoco.mjx"],
        capture_output=True, text=True,
    )
    return python if probe.returncode == 0 else None


REAL_TRAINER_PYTHON = _real_trainer_python()


@pytest.mark.skipif(
    REAL_TRAINER_PYTHON is None,
    reason="No training venv with jax and mujoco (training/SETUP.md).",
)
def test_the_real_trainer_trains_the_toy_and_the_engine_digests_agree(
    task_project, tmp_path, capsys, cpu_training
) -> None:
    """Bounded CPU training: stored policy and trainer digests agree."""

    out = tmp_path / "real"
    code, envelope = _run(
        capsys, "train", "--project", str(task_project), "--out", str(out),
        "--iterations", "1", "--envs", "4", "--put", "--timeout", "600",
    )
    assert code == EXIT_OK, envelope
    receipt = envelope["training"]
    assert receipt["device"] == "cpu" and receipt["task_sha256"], receipt
    assert receipt["bytes"] == (out / "job.cxpolicy").stat().st_size
    (stored,) = envelope["assets"]
    assert stored["sha256"] == receipt["sha256"] == hashlib.sha256(
        (out / "job.cxpolicy").read_bytes()
    ).hexdigest()
    assert (out / "progress.json").is_file()
    assert json.loads((out / "progress.json").read_text())["state"] == "done"


# -- the iterate shape (ADR-192) -------------------------------------------

#: ``TASK_SCRIPT`` with the two things the iterate leg needs: a parameter
#: a sweep can move that changes what the network is trained AGAINST (a
#: reward weight — a curriculum key, ADR-161), and the trained policy
#: declared behind a numeric switch, so ``cadex params --set policy_on=0``
#: leaves the policy out and the sweep is accepted with a fresh bundle.
ITERATE_SCRIPT = TASK_SCRIPT.replace(
    "plate = part.box(60, 60, 6)\n",
    "p = params(policy_on=num(0.0, min=0.0, max=1.0, step=1.0),\n"
    "           lift_weight=num(1.0e-4, min=1.0e-5, max=1.0e-3, step=1.0e-5))\n"
    "plate = part.box(60, 60, 6)\n",
).replace(
    'assembly.reward("-(com_z - 60)^2", weight=1.0e-4,',
    'assembly.reward("-(com_z - 60)^2", weight=p.lift_weight,',
).replace(
    '          "j": j, "asm": asm, "diag": diag, "model": model, "job": job}\n',
    '          "j": j, "asm": asm, "diag": diag, "model": model, "job": job}\n'
    "if p.policy_on >= 0.5:\n"
    '    policy = assembly.policy(job, weights="@WEIGHTS@", sha256="@SHA@")\n'
    "    run = assembly.rollout(policy, frames_per_second=25, seed=3)\n"
    '    result["policy"] = policy\n'
    '    result["run"] = run\n',
)
assert "@SHA@" in ITERATE_SCRIPT and "p.lift_weight" in ITERATE_SCRIPT


def _iterate_script(tmp_path: Path, weights: str, sha256: str) -> Path:
    path = tmp_path / f"iterate-{weights}.py"
    path.write_text(
        ITERATE_SCRIPT.replace("@WEIGHTS@", weights).replace("@SHA@", sha256),
        encoding="utf-8",
    )
    return path


def _task_digest(bundle: Path) -> str:
    return hashlib.sha256(bundle.read_bytes()).hexdigest()


@pytest.mark.skipif(
    REAL_TRAINER_PYTHON is None,
    reason="No training venv with jax and mujoco (training/SETUP.md).",
)
def test_iterate_blanks_the_policy_retrains_across_the_change_and_redeclares(
    engine, tmp_path, capsys, cpu_training
) -> None:
    """Blank policy, sweep, warm retrain and re-declare (ADR-192).

    Two bounded 1 × 4 CPU runs verify the changed task and rollout.
    """

    root = tmp_path / "project"
    placeholder = "0" * 64
    code, envelope = _run(
        capsys, "script", "--set",
        str(_iterate_script(tmp_path, "job.cxpolicy", placeholder)),
        "--project", str(root),
    )
    assert code == EXIT_OK, envelope
    assert envelope["params"]["policy_on"] == 0.0

    # First policy: trained, stored, named, switched on.
    run1 = tmp_path / "run1"
    code, envelope = _run(
        capsys, "train", "--project", str(root), "--out", str(run1),
        "--iterations", "1", "--envs", "4", "--put", "--timeout", "600",
    )
    assert code == EXIT_OK, envelope
    assert envelope["training"]["device"] == "cpu"
    sha1 = envelope["training"]["sha256"]
    digest1 = _task_digest(run1 / "job-task.json")
    assert envelope["training"]["task_sha256"] == digest1
    code, envelope = _run(
        capsys, "script", "--set",
        str(_iterate_script(tmp_path, "job.cxpolicy", sha1)),
        "--project", str(root),
    )
    assert code == EXIT_OK, envelope
    # A stored parameter value outlives a script write: the switch is
    # still off, so naming the policy declared nothing yet.
    assert envelope["params"]["policy_on"] == 0.0
    assert not any(row["name"] == "policy" for row in envelope["outputs"])
    out1 = tmp_path / "out1"
    code, envelope = _run(
        capsys, "params", "--project", str(root), "--set", "policy_on=1",
        "--out", str(out1),
    )
    assert code == EXIT_OK, envelope
    trace1 = json.loads((out1 / "assembly-simulation-trace.json").read_text())
    assert trace1["policy"]["policy_sha256"] == sha1
    reward1 = float(trace1["policy"]["total_reward"])

    # Iterate: the change alone is refused, because the policy no longer
    # fits the task it would be declared against...
    code, envelope = _run(
        capsys, "params", "--project", str(root), "--set", "lift_weight=2.0e-4",
    )
    assert code == EXIT_REJECTED, envelope
    assert digest1 in envelope["error"], envelope
    # ...and with the switch blanked it is accepted, and exports the bundle
    # the retrain needs, with the digest the refusal named.
    sweep = tmp_path / "sweep"
    code, envelope = _run(
        capsys, "params", "--project", str(root), "--set", "policy_on=0",
        "--set", "lift_weight=2.0e-4", "--out", str(sweep),
    )
    assert code == EXIT_OK, envelope
    assert not any(row["name"] in ("policy", "run") for row in envelope["outputs"])
    digest2 = _task_digest(sweep / "job-task.json")
    assert digest2 != digest1

    # Retrain, warm-started across the change: the curriculum pair.
    run2 = tmp_path / "run2"
    code, envelope = _run(
        capsys, "train", "--project", str(root), "--out", str(run2),
        "--iterations", "1", "--envs", "4", "--put", "--timeout", "600",
        "--name", "job2.cxpolicy",
        "--init-from", str(run1 / "job.cxpolicy"),
        "--init-from-parent-task", str(run1 / "job-task.json"),
        "--init-from-task-change", "lift weight doubled",
    )
    assert code == EXIT_OK, envelope
    assert envelope["training"]["device"] == "cpu"
    sha2 = envelope["training"]["sha256"]
    assert sha2 != sha1
    assert envelope["training"]["task_sha256"] == digest2
    assert {row["name"] for row in envelope["assets"]} == {
        "job.cxpolicy", "job2.cxpolicy"
    }

    # Re-declare and switch back on: the rollout is the new policy's.
    code, envelope = _run(
        capsys, "script", "--set",
        str(_iterate_script(tmp_path, "job2.cxpolicy", sha2)),
        "--project", str(root),
    )
    assert code == EXIT_OK, envelope
    out2 = tmp_path / "out2"
    code, envelope = _run(
        capsys, "params", "--project", str(root), "--set", "policy_on=1",
        "--out", str(out2),
    )
    assert code == EXIT_OK, envelope
    assert envelope["params"] == {"policy_on": 1.0, "lift_weight": 2.0e-4}
    trace2 = json.loads((out2 / "assembly-simulation-trace.json").read_text())
    assert trace2["policy"]["policy_sha256"] == sha2
    reward2 = float(trace2["policy"]["total_reward"])
    # Both numbers exist and are the comparison; which is larger is the
    # toy's business after one iteration each, not this test's.
    assert reward1 == reward1 and reward2 == reward2  # not NaN
