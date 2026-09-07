# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``cadex walk``: the lifecycle walk as one command (ADR-199).

Three layers. The digest edit and the review reader, on strings. The
orchestration, against a **fake ``cadex``** that answers each leg in
envelopes and logs what it was asked — no engine, no trainer, so the leg
order, the flags carried to each leg and the refusals are pinned on any
machine. And the real thing: the repository's plate-and-arm toy through
the whole walk twice — the first from a placeholder digest to a verified
rollout, the second across a reward change with a warm start — with the
real engine and the real trainer, one iteration by four environments,
bounded far under the fifteen-minute rule.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

from cadex_cli import walk as walk_module
from cadex_cli.report import EXIT_OK, EXIT_REJECTED, EXIT_USAGE
from cadex_cli.walk import (
    POLICY_SWITCH,
    REVIEW_FILENAME,
    SCRIPT_FILENAME,
    WalkError,
    declare_policy,
    review_from_outputs,
)

from test_train import ITERATE_SCRIPT, REAL_TRAINER_PYTHON, _run

PLACEHOLDER = "0" * 64
TOY = ITERATE_SCRIPT.replace("@WEIGHTS@", "job.cxpolicy").replace("@SHA@", PLACEHOLDER)


# -- the digest edit ---------------------------------------------------------


def test_declare_rewrites_the_two_literals_and_nothing_else() -> None:
    sha = "ab" * 32
    source = declare_policy(TOY, "job2.cxpolicy", sha)
    assert 'weights="job2.cxpolicy"' in source and f'sha256="{sha}"' in source
    # Undo the two edits and the script is byte-for-byte what it was.
    assert source.replace("job2.cxpolicy", "job.cxpolicy").replace(sha, PLACEHOLDER) == TOY


def test_declare_refuses_a_script_without_the_iterate_convention() -> None:
    no_switch = TOY.replace(f"{POLICY_SWITCH}=num(0.0, min=0.0, max=1.0, step=1.0),\n", "")
    with pytest.raises(WalkError, match="ADR-192"):
        declare_policy(no_switch, "job.cxpolicy", "ab" * 32)
    twice = TOY + '\nother = assembly.policy(job, weights="x.cxpolicy", sha256="y")\n'
    with pytest.raises(WalkError, match="exactly one"):
        declare_policy(twice, "job.cxpolicy", "ab" * 32)
    no_sha = TOY.replace(f', sha256="{PLACEHOLDER}"', "")
    with pytest.raises(WalkError, match="sha256"):
        declare_policy(no_sha, "job.cxpolicy", "ab" * 32)


def test_the_review_is_the_trace_s_policy_block_or_nothing(tmp_path) -> None:
    trace = tmp_path / "assembly-simulation-trace.json"
    trace.write_text(json.dumps({"policy": {
        "total_reward": -1.5, "reward_totals": [{"label": "lift", "total": -1.5}],
        "policy_sha256": "ab" * 32, "steps": 50,
    }}))
    (tmp_path / "plain.json").write_text("{}")
    outputs = [
        {"name": "arm", "files": {"step": str(tmp_path / "arm.step")}},
        {"name": "run", "files": {"json": str(tmp_path / "plain.json")}},
        {"name": "run", "files": {"trace": str(trace)}},
    ]
    review = review_from_outputs(outputs)
    assert review["trace"] == str(trace)
    assert review["total_reward"] == -1.5 and review["steps"] == 50
    assert review_from_outputs(outputs[:2]) == {}


# -- the orchestration, against a fake cadex ----------------------------------

#: A ``cadex`` that answers every leg the walk runs, in the envelopes the
#: real one prints, and appends each argv it was given to a log. ``train``
#: writes a policy and reports its digest; ``script`` prints or replaces the
#: project's script; ``params`` with the switch on writes a trace with a
#: policy block. ``$FAKE_CADEX_FAIL`` names one leg that refuses at exit 3.
FAKE_CADEX = textwrap.dedent(
    """
    import hashlib, json, os, shutil, sys
    from pathlib import Path

    argv = sys.argv[1:]
    with open(os.environ["FAKE_CADEX_LOG"], "a") as log:
        log.write(json.dumps(argv) + "\\n")
    project = Path(argv[argv.index("--project") + 1])
    script = project / "script.py"

    def after(flag):
        return Path(argv[argv.index(flag) + 1]) if flag in argv else None

    def envelope(**fields):
        print(json.dumps({"schema": "cadex-cli-v1", "ok": True,
                          "accepted_revision": "r" * 64, "digest": "d" * 64,
                          **fields}))

    def refuse(leg):
        if os.environ.get("FAKE_CADEX_FAIL") == leg:
            print(json.dumps({"ok": False, "error": leg + " refused by the fake"}))
            sys.exit(3)

    if "-p" in argv:
        refuse("design")
        envelope(session_id="s1", notes=["fake turn"])
    elif "train" in argv:
        refuse("train")
        out = after("--out"); out.mkdir(parents=True, exist_ok=True)
        blob = b"policy for " + script.read_bytes()
        name = (after("--name") or Path("job.cxpolicy")).name
        (out / name).write_bytes(blob)
        sha = hashlib.sha256(blob).hexdigest()
        envelope(training={"sha256": sha, "out": str(out / name), "reward_per_step": 0.5,
                           "wall_time_s": 0.1, "device": "fake", "task_sha256": "t" * 64},
                 assets=[{"name": name, "sha256": sha, "bytes": len(blob)}])
    elif "script" in argv:
        source = after("--set")
        if source is None:
            sys.stdout.write(script.read_text())
        else:
            refuse("declare")
            shutil.copy(source, script)
            envelope(params={"policy_on": 0.0}, outputs=[])
    elif "params" in argv:
        sets = [argv[i + 1] for i, a in enumerate(argv) if a == "--set"]
        leg = "rollout" if "policy_on=1" in sets else "sweep"
        refuse(leg)
        out = after("--out"); out.mkdir(parents=True, exist_ok=True)
        outputs = []
        params = {"policy_on": 1.0 if leg == "rollout" else 0.0}
        if leg == "rollout":
            trace = out / "assembly-simulation-trace.json"
            trace.write_text(json.dumps({"policy": {
                "total_reward": -12.5,
                "reward_totals": [{"label": "lift", "total": -12.5}],
                "policy_sha256": "declared"}}))
            outputs.append({"name": "run", "files": {"trace": str(trace)}})
        envelope(params=params, outputs=outputs)
    else:
        sys.exit(2)
    """
)


@pytest.fixture
def fake_cadex(tmp_path, monkeypatch) -> Path:
    """The walk's legs answered by :data:`FAKE_CADEX`; returns the argv log."""

    script = tmp_path / "fake_cadex.py"
    script.write_text(FAKE_CADEX, encoding="utf-8")
    log = tmp_path / "legs.log"
    monkeypatch.setenv("FAKE_CADEX_LOG", str(log))
    monkeypatch.delenv("FAKE_CADEX_FAIL", raising=False)
    monkeypatch.setattr(walk_module, "cadex_command", lambda: [sys.executable, str(script)])
    return log


@pytest.fixture
def toy_root(tmp_path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "script.py").write_text(TOY, encoding="utf-8")
    return root


def _legs(log: Path) -> list[list[str]]:
    return [json.loads(line) for line in log.read_text().splitlines()]


def test_the_walk_runs_train_declare_rollout_and_lands_the_review(
    fake_cadex, toy_root, capsys
) -> None:
    out = toy_root / "runs" / "walk-1"
    code, envelope = _run(
        capsys, "--project", str(toy_root), "walk", "--out", str(out),
        "--iterations", "2", "--envs", "3", "--seed", "5", "--timeout", "30",
    )
    assert code == EXIT_OK, envelope
    assert [leg["leg"] for leg in envelope["walk"]["legs"]] == ["train", "declare", "rollout"]
    assert all(leg["exit"] == 0 for leg in envelope["walk"]["legs"])

    # The legs, as the fake saw them: train with the flags by name, the
    # script read, the re-declared script written, the switch turned on.
    train, read, declare, rollout = _legs(fake_cadex)
    assert train[:3] == ["--project", str(toy_root), "train"]
    for flag, value in (("--out", str(out / "train")), ("--iterations", "2"),
                        ("--envs", "3"), ("--seed", "5"), ("--timeout", "30.0")):
        assert train[train.index(flag) + 1] == value, train
    assert "--put" in train and "--json" in train
    assert read[-1] == "script"
    assert declare[-4:-1] == ["script", "--set", str(out / SCRIPT_FILENAME)]
    assert rollout[rollout.index("--set") + 1] == f"{POLICY_SWITCH}=1"
    assert rollout[rollout.index("--out") + 1] == str(out / "rollout")

    # The digest edit: the fake's policy digest is now in the project script.
    sha = envelope["training"]["sha256"]
    assert sha == hashlib.sha256(b"policy for " + TOY.encode()).hexdigest()
    assert f'sha256="{sha}"' in (toy_root / "script.py").read_text()
    assert 'weights="job.cxpolicy"' in (toy_root / "script.py").read_text()

    # The review: in the envelope and on disk under --out, paths relative.
    review = envelope["walk"]["review"]
    assert review["total_reward"] == -12.5 and review["sha256"] == sha
    assert envelope["walk"]["review_file"] == str(out / REVIEW_FILENAME)
    on_disk = json.loads((out / REVIEW_FILENAME).read_text())
    assert on_disk["schema"] == "cadex-walk-review-v1"
    assert on_disk["total_reward"] == -12.5
    assert on_disk["trace"] == "rollout/assembly-simulation-trace.json"
    assert on_disk["params"] == {"policy_on": 1.0}
    assert on_disk["training"]["reward_per_step"] == 0.5
    assert [leg["leg"] for leg in on_disk["legs"]] == ["train", "declare", "rollout"]
    assert "argv" not in on_disk["legs"][0]
    assert envelope["notes"] == [
        "walk: job.cxpolicy ({:s}) verified; total_reward -12.5 over 3 legs.".format(sha[:12])
    ]


def test_the_iterate_walk_sweeps_first_and_carries_the_warm_start(
    fake_cadex, toy_root, capsys
) -> None:
    out = toy_root / "runs" / "walk-2"
    code, envelope = _run(
        capsys, "--project", str(toy_root), "walk", "--out", str(out),
        "--set", "lift_weight=2e-4", "--name", "job2.cxpolicy",
        "--init-from", "prev/job.cxpolicy", "--init-from-parent-task", "prev/job-task.json",
        "--init-from-task-change", "lift weight doubled", "--label", "second",
        "--prompt", "make the arm longer", "--iterations", "1", "--envs", "1",
    )
    assert code == EXIT_OK, envelope
    assert [leg["leg"] for leg in envelope["walk"]["legs"]] == [
        "design", "sweep", "train", "declare", "rollout"
    ]
    design, sweep, train, _read, _declare, _rollout = _legs(fake_cadex)
    assert design[design.index("-p") + 1] == "make the arm longer" and "--resume" not in design
    sets = [sweep[i + 1] for i, flag in enumerate(sweep) if flag == "--set"]
    assert sets == [f"{POLICY_SWITCH}=0", "lift_weight=0.0002"]  # parsed, then spelled
    assert sweep[sweep.index("--out") + 1] == str(out / "sweep")
    for flag, value in (
        ("--name", "job2.cxpolicy"), ("--label", "second"),
        ("--init-from", "prev/job.cxpolicy"),
        ("--init-from-parent-task", "prev/job-task.json"),
        ("--init-from-task-change", "lift weight doubled"),
    ):
        assert train[train.index(flag) + 1] == value, train
    assert 'weights="job2.cxpolicy"' in (toy_root / "script.py").read_text()
    assert json.loads((out / REVIEW_FILENAME).read_text())["weights"] == "job2.cxpolicy"


def test_the_remote_walk_carries_the_flags_to_the_train_leg_only(
    fake_cadex, toy_root, capsys
) -> None:
    """``cadex walk --remote`` (ADR-200) is the same walk with ``--remote``
    (and ``--allow-cpu``) on the train leg and nowhere else; the artifacts
    under ``--out`` and the legs after training do not know."""

    out = toy_root / "runs" / "walk-remote"
    code, envelope = _run(
        capsys, "--project", str(toy_root), "walk", "--out", str(out),
        "--remote", "--allow-cpu", "--iterations", "1", "--envs", "2",
    )
    assert code == EXIT_OK, envelope
    train, read, declare, rollout = _legs(fake_cadex)
    assert "--remote" in train and "--allow-cpu" in train
    assert train[train.index("--out") + 1] == str(out / "train")
    for other in (read, declare, rollout):
        assert "--remote" not in other and "--allow-cpu" not in other
    assert [leg["leg"] for leg in envelope["walk"]["legs"]] == ["train", "declare", "rollout"]
    assert (out / REVIEW_FILENAME).is_file()

    # A warm start with --remote is a usage error before any leg runs.
    fake_cadex.unlink()
    code, envelope = _run(
        capsys, "--project", str(toy_root), "walk", "--out", str(out), "--remote",
        "--init-from", "p.cxpolicy", "--init-from-parent-task", "t.json",
        "--init-from-task-change", "why",
    )
    assert code == EXIT_USAGE and "trains cold" in envelope["error"], envelope
    assert not fake_cadex.exists()


def test_a_leg_that_refuses_stops_the_walk_there_with_its_name(
    fake_cadex, toy_root, capsys, monkeypatch
) -> None:
    out = toy_root / "runs" / "walk-3"
    monkeypatch.setenv("FAKE_CADEX_FAIL", "train")
    code, envelope = _run(capsys, "--project", str(toy_root), "walk", "--out", str(out))
    assert code == EXIT_REJECTED
    assert "leg train" in envelope["error"] and "refused by the fake" in envelope["error"]
    assert envelope["walk"]["legs"][-1]["leg"] == "train"
    assert not (out / REVIEW_FILENAME).exists()
    assert PLACEHOLDER in (toy_root / "script.py").read_text()  # nothing declared
    assert len(_legs(fake_cadex)) == 1  # nothing ran after the refusal


def test_a_script_without_the_convention_is_refused_after_training(
    fake_cadex, toy_root, capsys
) -> None:
    (toy_root / "script.py").write_text(
        TOY.replace(f"{POLICY_SWITCH}=num(0.0, min=0.0, max=1.0, step=1.0),\n", "")
    )
    code, envelope = _run(
        capsys, "--project", str(toy_root), "walk", "--out", str(toy_root / "runs" / "w"),
    )
    assert code == EXIT_REJECTED
    assert "ADR-192" in envelope["error"]
    assert [leg["leg"] for leg in envelope["walk"]["legs"]] == ["train", "script"]


@pytest.mark.parametrize(
    "argv, wording",
    [
        ([], "needs --out"),
        (["--out", "o", "--set", f"{POLICY_SWITCH}=1"], "owns the switch"),
        (["--out", "o", "--name", "job.txt"], ".cxpolicy"),
        (["--out", "o", "--iterations", "0"], "at least 1"),
        (["--out", "o", "--init-from-task-change", "why"], "--init-from POLICY"),
    ],
)
def test_usage_errors_are_refused_before_any_leg_runs(
    fake_cadex, toy_root, capsys, argv, wording
) -> None:
    code, envelope = _run(capsys, "--project", str(toy_root), "walk", *argv)
    assert code == EXIT_USAGE, envelope
    assert wording in envelope["error"]
    assert not fake_cadex.exists()


# -- the real thing: the toy, twice ------------------------------------------


@pytest.mark.skipif(
    REAL_TRAINER_PYTHON is None,
    reason="No training venv with jax and mujoco (training/SETUP.md).",
)
def test_the_same_walk_handles_a_linear_carriage(engine, tmp_path, capsys) -> None:
    """Exercise a translational DOF through the unchanged public entry point."""
    import math
    import xml.etree.ElementTree as ET

    source = Path(__file__).resolve().parents[2] / "examples/lifecycle/linear-carriage/script.py"
    root = tmp_path / "carriage"
    code, envelope = _run(capsys, "script", "--set", str(source), "--project", str(root))
    assert code == EXIT_OK, envelope
    out = root / "runs/baseline"
    code, envelope = _run(
        capsys, "walk", "--project", str(root), "--out", str(out),
        "--iterations", "1", "--envs", "4", "--seed", "0", "--timeout", "600",
    )
    assert code == EXIT_OK, envelope
    assert [leg["leg"] for leg in envelope["walk"]["legs"]] == ["train", "declare", "rollout"]
    assert all(leg["exit"] == 0 for leg in envelope["walk"]["legs"])
    model = ET.parse(next((out / "train").glob("*-model.xml")))
    assert [j.get("type") for j in model.findall(".//worldbody//joint")] == ["slide"]
    review = json.loads((out / REVIEW_FILENAME).read_text())
    assert review["sha256"] == envelope["walk"]["review"]["policy_sha256"]
    assert math.isfinite(review["total_reward"])
    assert {row["label"] for row in review["reward_totals"]} == {"lift", "control_cost"}
    progress = (root / "PROGRESS.md").read_text()
    assert "train 1 it × 4 envs" in progress and "total_reward" in progress


def _git(root: Path, *argv: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *argv], capture_output=True, text=True, check=True
    ).stdout.strip()


SENSORS_DOC = """\
# Sensors

The task observes three channels, all read back from the exported task
bundle's `observations` block: `angle` (the revolute joint, degrees),
`com` (the swing arm's centre of mass, mm), `effort` (the motor's
actuator force, N·mm). Written by the walk's caller, by the convention
`docs/CLI.md` §2 names.
"""


@pytest.mark.skipif(
    REAL_TRAINER_PYTHON is None,
    reason="No training venv with jax and mujoco (training/SETUP.md).",
)
def test_the_walk_takes_the_toy_to_a_verified_rollout_and_iterates(
    engine, tmp_path, capsys
) -> None:
    """The charter's walk on the repository's own toy: one command from a
    placeholder digest to a verified rollout, then one more across a reward
    change with a warm start. Everything lands under the project — the
    review as a file the walk commits, the numbers as `PROGRESS.md` rows
    with their deltas — and what a rebuild or a retrain re-makes stays
    out of the project's history."""

    root = tmp_path / "project"
    toy = tmp_path / "toy.py"
    toy.write_text(TOY, encoding="utf-8")
    code, envelope = _run(capsys, "script", "--set", str(toy), "--project", str(root))
    assert code == EXIT_OK, envelope
    (root / "docs").mkdir()
    (root / "docs" / "sensors.md").write_text(SENSORS_DOC, encoding="utf-8")

    out1 = root / "runs" / "walk-1"
    code, envelope = _run(
        capsys, "--project", str(root), "walk", "--out", str(out1),
        "--iterations", "1", "--envs", "4", "--timeout", "600",
    )
    assert code == EXIT_OK, envelope
    assert [leg["leg"] for leg in envelope["walk"]["legs"]] == ["train", "declare", "rollout"]
    sha1 = envelope["training"]["sha256"]
    review1 = json.loads((out1 / REVIEW_FILENAME).read_text())
    assert review1["sha256"] == sha1 == envelope["walk"]["review"]["policy_sha256"]
    reward1 = float(review1["total_reward"])
    assert reward1 == reward1  # not NaN
    assert {row["label"] for row in review1["reward_totals"]} == {"lift", "control_cost"}
    assert (root / "assets" / "job.cxpolicy").is_file()
    assert f'sha256="{sha1}"' in (root / "script.py").read_text()

    # The project's history: the legs' commits, then the walk's own for the
    # review; the policy in the store and the sensors doc tracked; the
    # training checkpoints, the policy copies and the trace not.
    subjects = _git(root, "log", "--format=%s").splitlines()
    assert subjects[0] == f"cadex walk 1 it × 4 envs → {out1}"
    assert subjects[1] == "cadex params policy_on=1"
    assert "cadex train 1 it × 4 envs → job.cxpolicy (stored)" in subjects
    tracked = set(_git(root, "ls-files").splitlines())
    assert {"assets/job.cxpolicy", "docs/sensors.md", "runs/walk-1/review.json",
            "runs/walk-1/train/job-task.json", "runs/walk-1/script.py"} <= tracked
    assert not [path for path in tracked
                if path.endswith(".cxpolicy") and not path.startswith("assets/")]
    assert not [path for path in tracked if path.endswith("-trace.json")]
    assert (out1 / "train" / "job.best.cxpolicy").is_file()  # on disk, untracked
    assert _git(root, "status", "--porcelain") == ""

    # Iterate: the reward weight doubled, the retrain warm across it.
    out2 = root / "runs" / "walk-2"
    code, envelope = _run(
        capsys, "--project", str(root), "walk", "--out", str(out2),
        "--set", "lift_weight=2e-4", "--name", "job2.cxpolicy",
        "--init-from", str(out1 / "train" / "job.cxpolicy"),
        "--init-from-parent-task", str(out1 / "train" / "job-task.json"),
        "--init-from-task-change", "lift weight doubled",
        "--iterations", "1", "--envs", "4", "--timeout", "600",
    )
    assert code == EXIT_OK, envelope
    assert [leg["leg"] for leg in envelope["walk"]["legs"]] == [
        "sweep", "train", "declare", "rollout"
    ]
    assert envelope["params"] == {"policy_on": 1.0, "lift_weight": 2.0e-4}
    sha2 = envelope["training"]["sha256"]
    assert sha2 != sha1
    review2 = json.loads((out2 / REVIEW_FILENAME).read_text())
    assert review2["weights"] == "job2.cxpolicy" and review2["sha256"] == sha2
    assert review2["params"] == {"policy_on": 1.0, "lift_weight": 2.0e-4}
    assert review2["training"]["task_sha256"] != review1["training"]["task_sha256"]
    reward2 = float(review2["total_reward"])
    assert reward2 == reward2

    # The comparison is one recorded row (ADR-194), and the walk's commit
    # is the last one.
    rows = [line for line in (root / "PROGRESS.md").read_text().splitlines()
            if line.startswith("| 2")]
    assert rows[-1].split(" | ")[1] == "params"
    assert f"total_reward {reward2:.1f} (Δ " in rows[-1] and f"at {reward1:.1f})" in rows[-1]
    assert _git(root, "log", "-1", "--format=%s") == f"cadex walk 1 it × 4 envs → {out2}"
    assert {"assets/job2.cxpolicy", "runs/walk-2/review.json"} <= set(
        _git(root, "ls-files").splitlines()
    )
