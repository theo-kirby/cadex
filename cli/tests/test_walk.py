# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``cadex walk``: the lifecycle walk as one command (ADR-199).

Offline tests pin digest edits, review parsing and orchestration. Real CPU walks
verify, iterate, fail after partial trainer output, then recover with preserved
artifacts and comparison history (one iteration × four environments per run).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
import signal
import subprocess
import sys
import textwrap
import time

import pytest

from cadex_cli.agent import CLI_OVERLAY
from cadex_cli import walk as walk_module
from cadex_cli.report import EXIT_FAILURE, EXIT_OK, EXIT_REJECTED, EXIT_USAGE
from cadex_cli.walk import (
    DEFAULT_LEG_TIMEOUT_S,
    EXIT_LEG_TIMEOUT,
    POLICY_SWITCH,
    REVIEW_FILENAME,
    SCRIPT_FILENAME,
    PENDING_FILENAME,
    WalkError,
    declare_policy,
    declared_note_subjects,
    motion_from_trace,
    review_from_outputs,
    train_leg_timeout,
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


def test_declare_refuses_the_constant_factored_script_and_takes_the_taught_one(
) -> None:
    """The refusal nt3's first walk from a prompt actually hit.

    The design turn wrote ``WEIGHTS = "…"`` above the call and passed the
    name by reference, which reads better and is refused: the edit is a
    literal rewrite. The overlay in ``cadex_cli.agent`` now teaches the
    inline form, so the example it teaches is rewritten here to prove the
    two halves agree.
    """

    factored = 'POLICY_WEIGHTS = "job.cxpolicy"\n' + TOY.replace(
        'weights="job.cxpolicy"', "weights=POLICY_WEIGHTS")
    with pytest.raises(WalkError, match="no weights="):
        declare_policy(factored, "job2.cxpolicy", "ab" * 32)
    factored_sha = f'POLICY_SHA = "{PLACEHOLDER}"\n' + TOY.replace(
        f'sha256="{PLACEHOLDER}"', "sha256=POLICY_SHA")
    with pytest.raises(WalkError, match="no sha256="):
        declare_policy(factored_sha, "job2.cxpolicy", "ab" * 32)

    # The example the authoring contract teaches is one this rewrite takes.
    call = re.search(r"assembly\.policy\(task,[^)]*\)", CLI_OVERLAY)
    assert call is not None, "the overlay no longer shows the policy call"
    taught = call.group(0)
    taught = walk_module._replace_keyword(taught, "weights", "job2.cxpolicy")
    taught = walk_module._replace_keyword(taught, "sha256", "ab" * 32)
    assert taught == 'assembly.policy(task, weights="job2.cxpolicy", ' \
        f'sha256="{"ab" * 32}")'


def test_the_review_is_the_trace_s_policy_block_or_nothing(tmp_path) -> None:
    trace = tmp_path / "assembly-simulation-trace.json"
    trace.write_text(json.dumps({"policy": {
        "total_reward": -1.5, "reward_totals": [{"label": "lift", "total": -1.5}],
        "policy_sha256": "ab" * 32, "steps": 50, "seed": 7,
    }}))
    (tmp_path / "plain.json").write_text("{}")
    outputs = [
        {"name": "arm", "files": {"step": str(tmp_path / "arm.step")}},
        {"name": "run", "files": {"json": str(tmp_path / "plain.json")}},
        {"name": "run", "files": {"trace": str(trace)}},
    ]
    review = review_from_outputs(outputs)
    assert review["rollout_seed"] == 7
    assert review["trace"] == str(trace)
    assert review["total_reward"] == -1.5 and review["steps"] == 50
    assert review_from_outputs(outputs[:2]) == {}


#: Frames lifted verbatim from the two documented example rollouts
#: (``examples/lifecycle/{hinged-arm,linear-carriage}``, as they reproduce
#: on a built engine): the first solved frame and the extreme one. Both
#: raw traces are 27 frames -- one ``input`` and 26 ``solver_output`` --
#: and the poses are absolute, which is why ``swing`` starts at
#: ``[12, 0, 6]`` rather than the origin.
def _frame(index, kind, seconds, places):
    return {"frame_index": index, "frame_kind": kind, "nominal_time_s": seconds,
            "component_placements": places}


_ARM_START = {"base": {"position_mm": [0.0, 0.0, 0.0],
                       "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]},
              "swing": {"position_mm": [12.0, 0.0, 6.0],
                        "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}}
_ARM_EXTREME = {"base": _ARM_START["base"],
                "swing": {"position_mm": [12.0, 0.0, 6.0],
                          "rotation_xyzw": [0.0, 0.9999481757173622, 0.0,
                                            0.010180662037381827]}}
_SLIDE_START = {"base": {"position_mm": [0.0, 0.0, 0.0],
                         "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]},
                "slide": {"position_mm": [12.0, 0.0, 40.0],
                          "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}}
_SLIDE_EXTREME = {"base": _SLIDE_START["base"],
                  "slide": {"position_mm": [12.0, 0.0, -4699.378322122887],
                            "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}}


@pytest.mark.parametrize("available", [True, False])
def test_section_misses_join_instances_and_both_motion_channels(tmp_path, available):
    motion = motion_from_trace({"frames": [
        _frame(1, "solver_output", 0.0, {**_ARM_START, "slide": _SLIDE_START["slide"]}),
        _frame(2, "solver_output", 0.5, {**_ARM_EXTREME, "slide": _SLIDE_EXTREME["slide"]}),
    ]})
    motion["available"] = available
    section = {"objects": {
        "base": {"status": "empty"}, "swing": {"status": "empty"},
        "slide": {"status": "unsupported"}, "cut": {"status": "ok"},
        # Labels and shared sources cannot identify which placed instance moved.
        "copy_a": {"status": "empty", "source": "swing", "label": "swing"},
        "copy_b": {"status": "empty", "source": "swing"},
    }}
    path = walk_module.write_review(tmp_path, review={"section": section, "motion": motion},
                                   legs=[], training={}, params={})
    misses = json.loads(path.read_text())["section"]["missed_objects"]
    assert set(misses) == {"base", "swing", "slide", "copy_a", "copy_b"}
    assert "missed_objects" not in section  # preserve the standalone section summary
    assert misses["copy_a"]["moved"] is None and misses["copy_b"]["moved"] is None
    assert misses["slide"]["section_status"] == "unsupported"
    if available:
        assert misses["base"]["moved"] is False
        assert misses["swing"]["moved"] is True
        assert misses["swing"]["max_displacement_mm"] == 0
        assert misses["swing"]["max_rotation_deg"] == pytest.approx(178.8334, abs=1e-4)
        assert misses["slide"]["moved"] is True
    else:
        assert all(row["moved"] is None and row["reason"] for row in misses.values())


@pytest.mark.parametrize("travel", [{}, {"max_displacement_mm": 0},
    {"max_displacement_mm": 0, "max_rotation_deg": float("nan")}])
def test_section_misses_incomplete_travel_is_unknown(travel):
    misses = walk_module.section_misses({"objects": {"arm": {"status": "empty"}}},
                                      {"available": True, "components": {"arm": travel}})
    assert misses["arm"]["moved"] is None


def test_travel_is_two_channels_because_the_hinged_arm_only_rotates() -> None:
    """The arm goes nowhere and turns 178.8°; a mm-only report is wrong."""

    motion = motion_from_trace({"frames": [
        _frame(0, "input", None, _ARM_START),
        _frame(1, "solver_output", 0.0, _ARM_START),
        _frame(9, "solver_output", 0.32, _ARM_EXTREME),
        _frame(26, "solver_output", 1.0, _ARM_START),
    ]})
    assert motion["available"] is True
    # Frame 0 is the pose the solver was given, not one it produced, and is
    # excluded -- so the count is one short of the raw frame list.
    assert (motion["frames_counted"], motion["frames_excluded"]) == (3, 1)
    assert motion["excluded_frame_kind"] == "input" and motion["duration_s"] == 1.0
    assert motion["components"]["swing"]["max_displacement_mm"] == 0.0
    assert motion["components"]["swing"]["position_range_mm"] == [0.0, 0.0, 0.0]
    assert motion["components"]["swing"]["max_rotation_deg"] == pytest.approx(178.8334, abs=1e-4)
    assert motion["largest_rotation"]["degrees"] == pytest.approx(178.8334, abs=1e-4)
    assert motion["largest_translation"]["millimetres"] == 0.0


def test_travel_reports_the_carriage_s_millimetres_and_no_rotation() -> None:
    """The other channel, on the other documented example."""

    motion = motion_from_trace({"frames": [
        _frame(0, "input", None, _SLIDE_START),
        _frame(1, "solver_output", 0.0, _SLIDE_START),
        _frame(26, "solver_output", 1.0, _SLIDE_EXTREME),
    ]})
    assert motion["largest_translation"] == {
        "component": "slide", "millimetres": pytest.approx(4739.3783, abs=1e-4)}
    assert motion["largest_rotation"]["degrees"] == 0.0
    assert motion["components"]["slide"]["position_range_mm"] == [
        0.0, 0.0, pytest.approx(4739.3783, abs=1e-4)]
    # Two examples' travels are not comparable and are never ranked: 4,739
    # mm of a carriage free-falling on an ideal guide is not "more motion"
    # than 178.8° of a swing arm doing its job.
    assert motion["ranking"].startswith("declined:")


def test_a_trace_that_never_moves_reports_zero_and_not_unavailable() -> None:
    """A mechanism that stood still is a measurement, not a missing one."""

    motion = motion_from_trace({"frames": [
        _frame(0, "input", None, _ARM_START),
        _frame(1, "solver_output", 0.0, _ARM_START),
        _frame(2, "solver_output", 0.5, _ARM_START),
    ]})
    assert motion["available"] is True and motion["frames_counted"] == 2
    assert motion["largest_translation"]["millimetres"] == 0.0
    assert motion["largest_rotation"]["degrees"] == 0.0
    assert all(component["max_displacement_mm"] == 0.0
               and component["max_rotation_deg"] == 0.0
               for component in motion["components"].values())


def test_a_trace_with_no_solved_frames_is_unavailable_with_a_reason() -> None:
    for payload, reason in (
        ({}, "exported no frames"),
        ({"frames": []}, "exported no frames"),
        ({"frames": [_frame(0, "input", None, _ARM_START)]}, "all of kind 'input'"),
        ({"frames": [_frame(0, "solver_output", 0.0, {})]}, "placed no components"),
    ):
        motion = motion_from_trace(payload)
        assert motion["available"] is False and reason in motion["reason"]


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
        bundle = out / "job-task.json"
        bundle.write_text(json.dumps({
            "schema": "s", "observations": [], "reward": [], "termination": [],
            "episode": {}, "functions": [], "actions": []}))
        task_sha = hashlib.sha256(bundle.read_bytes()).hexdigest()
        if "--detach" in argv:
            # The dispatcher's pending locator, and the run destination the
            # box mirrors into; no policy is written here at all.
            box = Path(os.environ["FAKE_BOX_DIR"])
            receipt = {"state": "pending", "run_id": "run-77",
                       "target": "box.invalid", "remote_dir": "/w/run-77",
                       "pid": 4242, "policy_name": name,
                       "destination": str(box), "receipt_path": str(out / "training-receipt.json")}
            (out / "training-receipt.json").write_text(json.dumps(receipt))
            envelope(training=receipt)
        else:
            (out / name).write_bytes(blob)
            sha = hashlib.sha256(blob).hexdigest()
            envelope(training={"sha256": sha, "out": str(out / name), "reward_per_step": 0.5,
                               "wall_time_s": 0.1, "device": "fake", "task_sha256": task_sha},
                     assets=[{"name": name, "sha256": sha, "bytes": len(blob)}])
    elif "asset" in argv:
        source = after("--put")
        blob = source.read_bytes()
        sha = hashlib.sha256(blob).hexdigest()
        store = project / "assets"; store.mkdir(parents=True, exist_ok=True)
        (store / source.name).write_bytes(blob)
        envelope(assets=[{"name": source.name, "sha256": sha, "bytes": len(blob)}])
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
            # Frames in the shape the engine writes them (ADR-259): frame 0
            # is the pre-solve input pose, placements are absolute world
            # poses, and this toy's one moving part rotates without
            # travelling -- the hinged arm's case, in miniature.
            def frame(index, kind, seconds, w, z):
                return {"frame_index": index, "frame_kind": kind,
                        "nominal_time_s": seconds,
                        "component_placements": {
                            "base": {"position_mm": [0.0, 0.0, 0.0],
                                     "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]},
                            "swing": {"position_mm": [12.0, 0.0, z],
                                      "rotation_xyzw": [0.0, w, 0.0,
                                                        (1.0 - w * w) ** 0.5]}}}
            trace.write_text(json.dumps({"policy": {
                "total_reward": -12.5,
                "reward_totals": [{"label": "lift", "total": -12.5}],
                "policy_sha256": "declared"},
                "frames": [frame(0, "input", None, 0.0, 6.0),
                           frame(1, "solver_output", 0.0, 0.0, 6.0),
                           frame(2, "solver_output", 0.5, 0.5, 6.0)]}))
            outputs.append({"name": "run", "files": {"trace": str(trace)}})
        envelope(params=params, outputs=outputs)
    else:
        sys.exit(2)
    """
)


@pytest.fixture
def fake_cadex(tmp_path, monkeypatch, request) -> Path:
    """The walk's legs answered by :data:`FAKE_CADEX`; returns the argv log."""

    script = tmp_path / "fake_cadex.py"
    script.write_text(FAKE_CADEX, encoding="utf-8")
    log = tmp_path / "legs.log"
    monkeypatch.setenv("FAKE_CADEX_LOG", str(log))
    monkeypatch.delenv("FAKE_CADEX_FAIL", raising=False)
    monkeypatch.setattr(walk_module, "cadex_command", lambda: [sys.executable, str(script)])
    from contextlib import contextmanager
    from cadex_cli import __main__ as main_module

    class InventoryClient:
        def request(self, op, args):
            if op == "rebuild":
                from test_render import buffer_reply
                reply = buffer_reply(tmp_path)
                reply.update(revision="r" * 64, accepted_revision="r" * 64, digest="d" * 64)
                failure = os.environ.get("FAKE_RENDER_FAIL")
                if failure in ("snapshot", "rollout"):
                    reply["accepted_revision"] = "z" * 64
                if failure == "rollout":
                    reply["revision"] = "z" * 64
                if failure == "digest":
                    reply["digest"] = "z" * 64
                return reply
            assert op == "inspect"
            if args["scope"] == "clearance":
                outcome = os.environ.get("FAKE_CLEARANCE", "")
                if outcome == "failure":
                    return {"ok": False, "error": "clearance inspection failed"}
                pairs = [{"first": "a", "second": "b", "distance_mm": None,
                          "common_volume_mm3": None, "error": "measurement failed"}] if outcome == "unknown" else []
                return {"ok": True, "value": {
                    "revision": "r" * 64, "assembly": getattr(request, "param", "asm"),
                    "available": bool(getattr(request, "param", "asm")), "pairs": pairs,
                }}
            assert args["scope"] == "inventory"
            return {"ok": True, "value": {"assembly": getattr(request, "param", "asm"), "components": [],
                                          "catalog_counts": {}}}

    @contextmanager
    def inventory_session(args, report, *, restore=True):
        assert restore is False
        yield None, InventoryClient()

    monkeypatch.setattr(main_module, "_engine_session", inventory_session)
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
    # No training bundle was exported here, so the model declares nothing and
    # the review reports no documentation finding rather than an empty one.
    assert on_disk["documentation"]["expected"] == []
    assert "model" not in on_disk["documentation"]
    # This toy walk publishes no assembly, so the review has nothing to
    # cross-check and says so (ADR-248) beside the walk's own note.
    assert envelope["notes"] == [
        "clearance bounds check: unavailable, 0 comparison(s) over 0 pair(s).",
        "motion: travel_mm 0 on swing, travel_deg 60 on swing over 2 solved frame(s).",
        "walk: job.cxpolicy ({:s}) verified; total_reward -12.5 over 3 legs.".format(sha[:12]),
    ]
    # The travel, in both channels and in the file: this toy rotates 60°
    # about Y and never leaves its start pose, so a millimetre-only report
    # would call a working mechanism motionless. Frame 0 is the solver's
    # input pose and is not one of the two counted.
    motion = on_disk["motion"]
    assert motion["available"] is True and motion["reference"] == "first solved frame"
    assert (motion["frames_counted"], motion["frames_excluded"]) == (2, 1)
    assert motion["excluded_frame_kind"] == "input"
    assert motion["duration_s"] == 0.5
    assert motion["largest_translation"] == {"component": "swing", "millimetres": 0.0}
    assert motion["largest_rotation"]["component"] == "swing"
    assert motion["largest_rotation"]["degrees"] == pytest.approx(60.0)
    assert motion["components"]["swing"]["position_range_mm"] == [0.0, 0.0, 0.0]
    assert motion["ranking"].startswith("declined:")
    # Labelled, not unit-suffixed, so a later walk of this project can read
    # the figure back and carry a delta (ADR-260). This is the project's
    # first walk, so there is nothing to compare against and no delta.
    assert "motion travel_mm 0 on swing, travel_deg 60 on swing over 2 solved frame(s)" in (
        toy_root / "PROGRESS.md").read_text()
    assert "(Δ " not in (toy_root / "PROGRESS.md").read_text().splitlines()[-1]


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

    # A warm start rides along with --remote (ADR-268): the triple reaches
    # the train leg beside --remote, and the dispatcher carries its two
    # files out. It is no longer a usage error.
    out2 = toy_root / "runs" / "walk-remote-warm"
    code, envelope = _run(
        capsys, "--project", str(toy_root), "walk", "--out", str(out2), "--remote",
        "--init-from", "p.cxpolicy", "--init-from-parent-task", "t.json",
        "--init-from-task-change", "why",
    )
    assert code == EXIT_OK, envelope
    train, read, declare, rollout = _legs(fake_cadex)[-4:]
    assert "--remote" in train
    for flag, value in (("--init-from", "p.cxpolicy"),
                        ("--init-from-parent-task", "t.json"),
                        ("--init-from-task-change", "why")):
        assert train[train.index(flag) + 1] == value, train
    for other in (read, declare, rollout):
        assert "--init-from" not in other


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


# -- the walk's own wall clock (ADR-261) --------------------------------------

#: A ``cadex`` that never answers, and that has spawned something of its own
#: which never answers either — the shape of every real leg, where the child
#: is a ``cadex`` command that has itself started the agent CLI or the
#: trainer. The grandchild writes its pid and inherits the captured stdout,
#: so a walk that killed only its direct child would still block draining
#: the pipe: this fake fails a timeout that is not a subtree kill.
HANGING_CADEX = textwrap.dedent(
    """
    import os, subprocess, sys, time

    subprocess.Popen([sys.executable, "-c",
        "import os, sys, time; "
        "open(sys.argv[1], 'w').write(str(os.getpid())); "
        "time.sleep(600)", os.environ["HANG_MARKER"]])
    time.sleep(600)
    """
)


def test_a_leg_that_runs_out_of_time_fails_the_walk_and_kills_its_subtree(
    toy_root, capsys, monkeypatch, tmp_path
) -> None:
    """The hazard the walk shipped with: a leg that hangs hangs the machine.

    ``run_leg`` had no bound at all, on any leg, and ``--timeout`` reached
    only the trainer's own internals — so an agent CLI that stalled rather
    than refusing left an unattended walk waiting forever with nothing to
    notice it. The bound ends the leg through the ordinary failure path.
    """

    script = tmp_path / "hanging_cadex.py"
    script.write_text(HANGING_CADEX, encoding="utf-8")
    marker = tmp_path / "grandchild.pid"
    monkeypatch.setenv("HANG_MARKER", str(marker))
    monkeypatch.setattr(walk_module, "cadex_command", lambda: [sys.executable, str(script)])

    out = toy_root / "runs" / "hang"
    started = time.monotonic()
    code, envelope = _run(
        capsys, "--project", str(toy_root), "walk", "--out", str(out),
        "--leg-timeout", "2",
    )
    elapsed = time.monotonic() - started

    assert code == EXIT_FAILURE, envelope
    assert "leg train" in envelope["error"] and "--leg-timeout" in envelope["error"]
    assert envelope["walk"]["legs"][-1]["exit"] == EXIT_LEG_TIMEOUT
    assert envelope["walk"]["leg_timeout_s"] == 2.0
    # It really stopped: well inside the fake's ten minutes, and nothing was
    # declared into the project.
    assert elapsed < 60.0
    assert PLACEHOLDER in (toy_root / "script.py").read_text()

    # ...and the grandchild went with it, rather than being orphaned onto a
    # machine nobody is watching.
    pid = int(marker.read_text())
    for _ in range(100):
        try:
            os.kill(pid, 0)
        except OSError:
            break
        time.sleep(0.1)
    else:  # pragma: no cover - only on a failure
        pytest.fail(f"the leg's grandchild {pid} outlived the walk")


#: The harder shape, and the one the first bound got wrong: the direct child
#: dies politely on ``SIGTERM`` while the grandchild ignores it and goes on
#: holding the inherited stdout. A walk that waits on the direct child alone
#: reports the leg as stopped, leaves the survivor on the machine, and then
#: blocks forever draining a pipe nobody will ever close. The grandchild
#: bounds its own life so this test fails slowly rather than hanging a suite.
STUBBORN_CADEX = textwrap.dedent(
    """
    import os, subprocess, sys, time

    subprocess.Popen([sys.executable, "-c",
        "import os, signal, sys, time; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "open(sys.argv[1], 'w').write(str(os.getpid())); "
        "time.sleep(120)", os.environ["HANG_MARKER"]])
    time.sleep(600)
    """
)


def test_a_stopped_leg_kills_the_grandchild_that_ignored_the_term(
    toy_root, capsys, monkeypatch, tmp_path
) -> None:
    """``SIGKILL`` reaches the group even when the direct child already died.

    The grace is for the leg that can close its engine session; it is not a
    reason to spare what is left. The group id is read while the child is
    certainly alive, so it is still addressable after the child has been
    reaped, and the final drain is bounded so a pipe held by something the
    kill could not reach cannot hang the walk either.
    """

    script = tmp_path / "stubborn_cadex.py"
    script.write_text(STUBBORN_CADEX, encoding="utf-8")
    marker = tmp_path / "stubborn.pid"
    monkeypatch.setenv("HANG_MARKER", str(marker))
    monkeypatch.setattr(walk_module, "cadex_command", lambda: [sys.executable, str(script)])

    out = toy_root / "runs" / "stubborn"
    started = time.monotonic()
    code, envelope = _run(
        capsys, "--project", str(toy_root), "walk", "--out", str(out),
        "--leg-timeout", "2",
    )
    elapsed = time.monotonic() - started

    assert code == EXIT_FAILURE, envelope
    assert envelope["walk"]["legs"][-1]["exit"] == EXIT_LEG_TIMEOUT
    # Promptly: the bound, the grace and the kill — not the grandchild's life.
    assert elapsed < 40.0, f"the walk waited {elapsed:.1f}s on a stopped leg"

    pid = int(marker.read_text())
    for _ in range(100):
        try:
            os.kill(pid, 0)
        except OSError:
            break
        time.sleep(0.1)
    else:  # pragma: no cover - only on a failure
        os.kill(pid, signal.SIGKILL)
        pytest.fail(f"the leg's stubborn grandchild {pid} outlived the walk")


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX process groups")
def test_stopped_leg_preserves_descendant_cleanup_grace(tmp_path, monkeypatch) -> None:
    """Reaping a fast parent must not cut short its descendant's cleanup."""

    ready = tmp_path / "ready"
    cleaned = tmp_path / "cleaned"
    descendant = tmp_path / "descendant.py"
    descendant.write_text(textwrap.dedent("""
        import signal, sys, time
        from pathlib import Path

        def cleanup(*_):
            time.sleep(0.3)
            Path(sys.argv[2]).write_text("cleanup complete")
            sys.exit(0)

        signal.signal(signal.SIGTERM, cleanup)
        Path(sys.argv[1]).touch()
        time.sleep(30)
    """))
    parent = subprocess.Popen(
        [sys.executable, "-c",
         "import subprocess, sys, time; "
         "subprocess.Popen(sys.argv[1:]); time.sleep(30)",
         sys.executable, str(descendant), str(ready), str(cleaned)],
        start_new_session=True,
    )
    monkeypatch.setattr(walk_module, "LEG_TERMINATION_GRACE_S", 1.0)
    try:
        deadline = time.monotonic() + 10
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.exists(), "descendant did not install its cleanup handler"
        started = time.monotonic()
        walk_module._stop_leg(parent, parent.pid)
        elapsed = time.monotonic() - started
        assert parent.returncode == -signal.SIGTERM
        assert cleaned.exists(), "group kill interrupted descendant cleanup"
        assert elapsed >= 1.0, "direct child exit shortened the group's grace"
    finally:
        try:
            os.killpg(parent.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        parent.wait(timeout=5)


def test_the_walk_reports_the_bound_it_ran_under_and_the_trainer_s_margin(
    fake_cadex, toy_root, capsys
) -> None:
    """A walk that finished says what it was measured against."""

    code, envelope = _run(
        capsys, "--project", str(toy_root), "walk",
        "--out", str(toy_root / "runs" / "bounded"), "--timeout", "30",
    )
    assert code == EXIT_OK, envelope
    assert envelope["walk"]["leg_timeout_s"] == DEFAULT_LEG_TIMEOUT_S
    assert envelope["walk"]["train_leg_timeout_s"] == DEFAULT_LEG_TIMEOUT_S


def test_the_train_leg_is_never_bounded_under_the_trainer_s_own_limit() -> None:
    """``--timeout`` is the trainer's; ``--leg-timeout`` is the walk's.

    A caller who asks for a long training run must not have it shot by a
    default they never typed, and a leg with no bound stays unbounded.
    """

    assert train_leg_timeout(3600.0, 0.0) == 3600.0
    assert train_leg_timeout(3600.0, 600.0) == 3600.0
    assert train_leg_timeout(3600.0, 7200.0) == 7200.0 + 300.0
    assert train_leg_timeout(0.0, 600.0) == 0.0


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
        (["--out", "o", "--seed", "-1"], "--seed must be"),
        (["--out", "o", "--seed", "4294967296"], "--seed must be"),
        (["--out", "o", "--leg-timeout", "-1"], "--leg-timeout must be"),
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


# -- what the model declares, against what the project documents (ADR-256) ---


DRIVEN_AND_OBSERVED = """\
<mujoco model="toy">
  <worldbody><body name="arm"><joint name="hinge" type="hinge"/>
    <geom type="box" size="1 1 1"/></body></worldbody>
  <actuator><motor name="hinge/motor" joint="hinge"/></actuator>
  <sensor><jointpos name="angle" joint="hinge"/></sensor>
</mujoco>
"""


def test_declared_note_subjects_reads_the_model_the_walk_trained_on(tmp_path) -> None:
    train = tmp_path / "train"
    train.mkdir()
    assert declared_note_subjects(train) == ([], None)  # nothing exported yet

    path = train / "job-model.xml"
    path.write_text(DRIVEN_AND_OBSERVED, encoding="utf-8")
    subjects, model = declared_note_subjects(train)
    assert subjects == ["actuators", "sensors"] and model == path

    # An empty section is not a declaration, and a file that is not MJCF is
    # not a finding: neither invents a subject for the project to document.
    path.write_text(
        DRIVEN_AND_OBSERVED.replace(
            '<sensor><jointpos name="angle" joint="hinge"/></sensor>', "<sensor/>"
        ),
        encoding="utf-8",
    )
    assert declared_note_subjects(train)[0] == ["actuators"]
    path.write_text("not xml at all", encoding="utf-8")
    assert declared_note_subjects(train) == ([], None)


# -- one entry point, no mechanism-specific path ------------------------------

#: The two repository-owned example mechanisms, and what makes them
#: different walks of the same loop: one turns, one slides, and their
#: actuators are declared in different units (ADR-203, ADR-260).
EXAMPLE_MECHANISMS = {
    "hinged-arm": "revolute joint, torque motor (N·mm)",
    "linear-carriage": "slider joint, force motor (N)",
}


def _example_script(name: str) -> str:
    path = Path(__file__).resolve().parents[2] / "examples/lifecycle" / name / "script.py"
    return path.read_text(encoding="utf-8")


def test_the_two_example_mechanisms_dispatch_the_identical_legs(
    fake_cadex, tmp_path, capsys
) -> None:
    """The dispatch is a function of the flags, never of the mechanism.

    The criterion the walk has to hold is "the same entry point, with no
    code change specific to the mechanism" — and the way that decays is
    not a rewrite, it is one ``if`` on the joint type. So this feeds
    ``command_walk`` the two real example recipes, which differ in joint
    (revolute against slider) and in actuator units, gives both the same
    flags, and requires the child ``cadex`` argv to come out **equal**
    once the project and output paths are substituted out. A branch on
    anything the script says — a joint kind, an actuator kind, a
    component count — changes a leg or its flags and fails here.
    """

    dispatched: dict[str, list[list[str]]] = {}
    for name in EXAMPLE_MECHANISMS:
        root = tmp_path / name / "project"
        root.mkdir(parents=True)
        (root / "script.py").write_text(_example_script(name), encoding="utf-8")
        before = len(_legs(fake_cadex)) if fake_cadex.exists() else 0
        code, envelope = _run(
            capsys, "--project", str(root), "walk", "--out", str(root / "runs/walk"),
            "--iterations", "1", "--envs", "4", "--seed", "0", "--timeout", "600",
        )
        assert code == EXIT_OK, envelope
        assert [leg["leg"] for leg in envelope["walk"]["legs"]] == [
            "train", "declare", "rollout"]
        dispatched[name] = [
            [argument.replace(str(root), "<project>") for argument in leg]
            for leg in _legs(fake_cadex)[before:]
        ]

    arm, carriage = (dispatched[name] for name in EXAMPLE_MECHANISMS)
    assert arm == carriage, "the walk dispatched differently for the two mechanisms"
    # ...and it really did dispatch the whole walk, so equality is not
    # two empty lists agreeing.
    assert [leg[2] for leg in arm] == ["train", "script", "script", "params"]


def test_the_digest_edit_treats_both_example_mechanisms_alike() -> None:
    """The one leg that reads the mechanism's source reads it the same way.

    ``declare_policy`` is where a mechanism-specific path would be
    cheapest to introduce, because it is the only place the walk opens a
    script it did not write. On both examples it rewrites the same two
    string literals and leaves every other byte alone.
    """

    sha = "ab" * 32
    for name, shape in EXAMPLE_MECHANISMS.items():
        source = _example_script(name)
        declared = declare_policy(source, "job2.cxpolicy", sha)
        assert f'weights="job2.cxpolicy"' in declared, shape
        assert f'sha256="{sha}"' in declared, shape
        undone = declared.replace("job2.cxpolicy", "job.cxpolicy").replace(sha, PLACEHOLDER)
        assert undone == source, name


# -- real lifecycle walks ---------------------------------------------------


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
    _assert_inventory(root, review)
    _assert_clearance(root, review, "clear")
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
    engine, tmp_path, capsys, cpu_training
) -> None:
    """Verify, iterate, fail, recover: real CPU legs preserve project history."""

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
    assert review1["training"]["device"] == "cpu"
    assert review1["comparison"]["training_seed"] == 0
    assert review1["comparison"]["rollout_seed"] == 3
    assert review1["comparison"]["objective_id"].startswith("v1:")
    assert review1["comparison"]["actions"]
    assert review1["sha256"] == sha1 == envelope["walk"]["review"]["policy_sha256"]
    reward1 = float(review1["total_reward"])
    assert reward1 == reward1  # not NaN
    assert {row["label"] for row in review1["reward_totals"]} == {"lift", "control_cost"}
    assert f'sha256="{sha1}"' in (root / "script.py").read_text()

    # The walk read the model it trained on against the project's notes:
    # the toy is driven and observed, and only docs/sensors.md is written.
    documentation = review1["documentation"]
    assert documentation["expected"] == ["actuators", "sensors"]
    assert documentation["notes"] == ["docs/sensors.md"]
    assert documentation["missing"] == ["actuators"]
    assert documentation["model"] == "train/" + next(
        (out1 / "train").glob("*-model.xml")
    ).name
    assert "docs notes 1, no actuators" in (root / "PROGRESS.md").read_text()
    assert any("no note for actuators" in note for note in envelope["notes"])

    # Track the policy and domain docs; exclude checkpoints and traces.
    subjects = _git(root, "log", "--format=%s").splitlines()
    assert subjects[0] == "cadex walk 1 it × 4 envs → runs/walk-1"
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
    sha2 = envelope["training"]["sha256"]
    assert sha2 != sha1
    review2 = json.loads((out2 / REVIEW_FILENAME).read_text())
    assert review2["training"]["device"] == "cpu"
    assert review2["weights"] == "job2.cxpolicy" and review2["sha256"] == sha2
    assert review2["params"] == envelope["params"] == {"policy_on": 1.0, "lift_weight": 2.0e-4}
    assert review2["training"]["task_sha256"] != review1["training"]["task_sha256"]
    assert review2["comparison"]["objective_id"] != review1["comparison"]["objective_id"]
    reward2 = float(review2["total_reward"])
    assert reward2 == reward2

    rows = [line for line in (root / "PROGRESS.md").read_text().splitlines()
            if line.startswith("| 2")]
    # The second walk's clearance finding count carries its delta against
    # the first (ADR-271): unchanged here, and a geometry iterate that
    # answers a finding is the case the delta exists for.
    assert ("clearance offending 1 (Δ ±0 vs " in rows[-1]
            and "at 1); unknown 0; pairs checked 1" in rows.pop())
    assert rows[-1].split(" | ")[1] == "params"
    assert f"total_reward {reward2:.1f} (Δ " in rows[-1] and f"at {reward1:.1f})" in rows[-1]

    # Both travel channels are comparable across walks (ADR-260). The first
    # walk had nothing to compare against; the second carries a delta on
    # each channel against it, so an iterate that held its travel while its
    # reward moved can say both in one row. Neither delta is a verdict.
    walk_rows = [line for line in (root / "PROGRESS.md").read_text().splitlines()
                 if line.startswith("| 2") and line.split(" | ")[1] == "walk"]
    assert len(walk_rows) == 2, walk_rows
    assert "; motion travel_mm " in walk_rows[0] and "(Δ " not in walk_rows[0]
    for label in ("travel_mm", "travel_deg"):
        assert re.search(
            label + r" -?[\d.]+(?:e[-+]?\d+)? \(Δ [-+±][\d.]+ vs [0-9a-f]{8} at ",
            walk_rows[1],
        ), walk_rows[1]
    # The row still fits PROGRESS_NUMBERS_LIMIT with both deltas on it: the
    # documentation finding is last in the cell and is what truncation eats.
    assert "…" not in walk_rows[1] and "docs notes 1, no actuators" in walk_rows[1]
    assert _git(root, "log", "-1", "--format=%s") == "cadex walk 1 it × 4 envs → runs/walk-2"
    assert {"assets/job2.cxpolicy", "runs/walk-2/review.json"} <= set(
        _git(root, "ls-files").splitlines()
    )

    # Fail under the current asset name, preserving both successful runs.
    preserved = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for folder in (out1, out2, root / "assets")
        for path in folder.rglob("*") if path.is_file()
    }
    source_before = (root / "script.py").read_bytes()
    progress_before = (root / "PROGRESS.md").read_text()
    head_before = _git(root, "rev-parse", "HEAD")
    failing_python = tmp_path / "failing-python"
    failing_python.write_text(
        f"#!{sys.executable}\n"
        "import sys\nfrom pathlib import Path\n"
        "Path(sys.argv[sys.argv.index('--out') + 1]).write_bytes(b'partial policy')\n"
        "print('injected retraining failure')\nraise SystemExit(7)\n"
    )
    failing_python.chmod(0o755)
    out3 = root / "runs" / "walk-failed"
    code, failed = _run(
        capsys, "--project", str(root), "walk", "--out", str(out3),
        "--set", "lift_weight=3e-4", "--name", "job2.cxpolicy",
        "--init-from", str(out2 / "train" / "job2.cxpolicy"),
        "--init-from-parent-task", str(out2 / "train" / "job-task.json"),
        "--init-from-task-change", "lift weight tripled",
        "--trainer-python", str(failing_python),
        "--iterations", "1", "--envs", "4", "--timeout", "30",
    )
    assert code == EXIT_FAILURE and failed["ok"] is False, failed
    assert "leg train" in failed["error"] and "trainer exited 7" in failed["error"]
    assert "injected retraining failure" in failed["error"]
    assert [leg["leg"] for leg in failed["walk"]["legs"]] == ["sweep", "train"]
    assert not failed["walk"].get("review")
    assert not any((out3 / name).exists() for name in (REVIEW_FILENAME, SCRIPT_FILENAME))
    assert (out3 / "train/job2.cxpolicy").read_bytes() == b"partial policy"
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == digest
               for path, digest in preserved.items())
    assert (root / "script.py").read_bytes() == source_before
    progress_after = (root / "PROGRESS.md").read_text()
    assert progress_after.startswith(progress_before)
    new_rows = [line for line in progress_after[len(progress_before):].splitlines()
                if line.startswith("| 2")]
    assert len(new_rows) == 1 and new_rows[0].split(" | ")[1] == "params"
    assert _git(root, "log", f"{head_before}..HEAD", "--format=%s") == (
        "cadex params lift_weight=0.0003, policy_on=0")
    assert json.loads((root / "script.json").read_text())["param_values"] == {
        "policy_on": 0.0, "lift_weight": 3.0e-4,
    }

    # Retry the retained sweep, without --set or the partial failed policy.
    recovered = root / "runs/walk-recovered"
    code, report = _run(
        capsys, "walk", "--project", str(root), "--out", str(recovered),
        "--name", "job3.cxpolicy", "--init-from", str(out2 / "train/job2.cxpolicy"),
        "--init-from-parent-task", str(out2 / "train/job-task.json"),
        "--init-from-task-change", "lift weight increased from 0.0002 to retained 0.0003",
        "--iterations", "1", "--envs", "4", "--timeout", "600",
    )
    assert code == EXIT_OK, report
    review = json.loads((recovered / REVIEW_FILENAME).read_text())
    assert review["training"]["device"] == "cpu"
    assert [(leg["leg"], leg["exit"]) for leg in review["legs"]] == [
        ("train", 0), ("declare", 0), ("rollout", 0),
    ]
    assert review["params"] == {"policy_on": 1.0, "lift_weight": 3.0e-4}
    assert review["weights"] == "job3.cxpolicy"
    assert review["sha256"] == report["walk"]["review"]["policy_sha256"] == hashlib.sha256(
        (root / "assets/job3.cxpolicy").read_bytes()).hexdigest()
    _assert_inventory(root, review)
    _assert_clearance(root, review, "below clearance")  # includes render and section
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == digest
               for path, digest in preserved.items())
    progress = (root / "PROGRESS.md").read_text()
    assert progress.startswith(progress_after)
    added = progress[len(progress_after):]
    for label in ("total_reward", "reward/step"):
        prior = next(line.split(" | ") for line in reversed(progress_before.splitlines())
                     if line.startswith("| 2") and label in line)
        value = re.search(rf"{label} ([^ ]+)", prior[5]).group(1)
        row = next(line for line in added.splitlines() if label in line)
        assert f"vs {prior[3]} at {value})" in row
    assert _git(root, "status", "--porcelain") == ""


@pytest.mark.skipif(
    REAL_TRAINER_PYTHON is None,
    reason="No training venv with jax and mujoco (training/SETUP.md).",
)
@pytest.mark.parametrize("mechanism", ["hinged-arm", "linear-carriage"])
def test_remote_walk_has_local_artifact_paths_with_a_cpu_dispatcher(
    engine, tmp_path, capsys, monkeypatch, mechanism, cpu_training
) -> None:
    """Real CPU legs through the pinned remote argv; no SSH or remote run."""
    from test_train import TRAINER_SOURCE

    dispatcher = tmp_path / "dispatch.py"
    dispatch_log = tmp_path / "dispatch.json"
    dispatcher.write_text(
        f"#!{sys.executable}\n"
        "import json, subprocess, sys\n"
        "from pathlib import Path\n"
        "args = sys.argv[1:]\n"
        "assert args[0] == 'train' and args[3:5] == ['--allow-cpu', '--'], args\n"
        f"Path({str(dispatch_log)!r}).write_text(json.dumps(args))\n"
        f"result = subprocess.run([{str(REAL_TRAINER_PYTHON)!r}, "
        f"{str(TRAINER_SOURCE)!r}, args[1], '--out', args[2], *args[5:]])\n"
        "if result.returncode: sys.exit(result.returncode)\n"
        "print('==> ' + args[2])\n",
        encoding="utf-8",
    )
    dispatcher.chmod(0o755)
    # Each leg is a fresh CLI process, so inject the stand-in there too.
    bootstrap = (
        "from pathlib import Path; from cadex_cli import train; "
        f"train.REMOTE_SCRIPT = Path({str(dispatcher)!r}); "
        "from cadex_cli.__main__ import main; raise SystemExit(main())"
    )
    monkeypatch.setattr(walk_module, "cadex_command",
                        lambda: [sys.executable, "-c", bootstrap])
    source = tmp_path / "toy.py"
    source.write_text((Path(__file__).resolve().parents[2] / f"examples/lifecycle/{mechanism}/script.py").read_text(), encoding="utf-8")
    paths = []
    reviews = []
    for mode in ("local", "remote"):
        root = tmp_path / mode
        code, report = _run(capsys, "script", "--set", str(source), "--project", str(root))
        assert code == EXIT_OK, report
        out = root / "runs/baseline"
        flags = ["--remote", "--allow-cpu"] if mode == "remote" else []
        code, report = _run(
            capsys, "walk", "--project", str(root), "--out", str(out),
            "--iterations", "1", "--envs", "4", "--seed", "0", "--timeout", "600",
            *flags,
        )
        assert code == EXIT_OK, report
        review = json.loads((out / REVIEW_FILENAME).read_text())
        assert review["training"]["device"] == "cpu"
        assert [leg["leg"] for leg in review["legs"]] == ["train", "declare", "rollout"]
        assert all(leg["exit"] == 0 for leg in review["legs"])
        assert review["sha256"] == report["walk"]["review"]["policy_sha256"]
        assert review["sha256"] == hashlib.sha256(
            (root / "assets/job.cxpolicy").read_bytes()).hexdigest()
        assert (out / "train/job.cxpolicy").read_bytes() == (root / "assets/job.cxpolicy").read_bytes()
        assert (out / review["trace"]).is_file()
        tracked = set(_git(root, "ls-files").splitlines())
        _assert_inventory(root, review)
        _assert_clearance(root, review, "below clearance" if mechanism == "hinged-arm" else "clear")
        expected = {"docs/inventory.md", "assets/job.cxpolicy", "runs/baseline/review.json",
                    "runs/baseline/train/job-task.json", "runs/baseline/script.py",
                    "ARCHITECTURE.md", "DECISIONS.md", "PROGRESS.md"}
        assert expected <= tracked
        assert _git(root, "status", "--porcelain") == ""
        progress = (root / "PROGRESS.md").read_text()
        row = next(line for line in progress.splitlines()
                   if "train 1 it × 4 envs" in line)
        assert ("(remote)" in row) == (mode == "remote")
        assert f'total_reward {review["total_reward"]:.1f}' in progress
        paths.append({str(p.relative_to(out)) for p in out.rglob("*") if p.is_file()})
        reviews.append(review)
    assert paths[0] == paths[1]
    assert reviews[0]["inventory"] == reviews[1]["inventory"]
    # Policy asset hashes (and thus accepted revisions) vary across training runs.
    assert all(review["clearance"]["revision"] for review in reviews)
    assert {k: v for k, v in reviews[0]["clearance"].items() if k != "revision"} == {
        k: v for k, v in reviews[1]["clearance"].items() if k != "revision"
    }
    from test_render import image_bytes
    for angle in ("front", "top", "right", "iso"):
        first, second = (review["render"] for review in reviews)
        assert image_bytes(tmp_path / "local" / first["views"][angle]["path"], first["revision"]) == image_bytes(
            tmp_path / "remote" / second["views"][angle]["path"], second["revision"])
    assert reviews[0]["render"]["limits"] == reviews[1]["render"]["limits"]
    for key in ("objects", "plane", "offset_mm", "status", "limits", "approximation"):
        assert reviews[0]["section"][key] == reviews[1]["section"][key]
    assert reviews[0]["trace"] == reviews[1]["trace"]
    assert reviews[0]["training"].keys() == reviews[1]["training"].keys()
    argv = json.loads(dispatch_log.read_text())
    assert argv[:5] == ["train", str(tmp_path / "remote/runs/baseline/train/job-task.json"),
                       str(tmp_path / "remote/runs/baseline/train/job.cxpolicy"),
                       "--allow-cpu", "--"]
    assert argv[5:] == ["--iterations", "1", "--envs", "4", "--seed", "0"]


def _assert_inventory(root, review):
    assert review["inventory"] == {
        "available": True, "component_count": 2, "catalogued_count": 0,
        "path": "docs/inventory.md",
    }
    text = (root / review["inventory"]["path"]).read_text()
    assert "2 component(s)" in text
    assert "docs/inventory.md" in _git(root, "ls-files").splitlines()


@pytest.mark.parametrize("fake_cadex", [""], indirect=True)
def test_walk_review_without_published_assembly(fake_cadex, toy_root, capsys):
    out = toy_root / "runs/empty-inventory"
    code, report = _run(capsys, "walk", "--project", str(toy_root), "--out", str(out))
    assert code == EXIT_OK, report
    review = json.loads((out / REVIEW_FILENAME).read_text())
    assert review["inventory"] == {
        "available": False, "component_count": 0, "catalogued_count": 0,
        "path": "docs/inventory.md",
    }
    assert "Inventory unavailable" in (toy_root / "docs/inventory.md").read_text()
    assert review["clearance"]["available"] is False
    assert review["clearance"]["pairs_checked"] is None
    assert review["clearance"]["offending_pair_count"] is None
    assert review["clearance"]["unknown_pair_count"] is None
    assert "Measurements unavailable" in (toy_root / "docs/clearance.md").read_text()
    # No published pair is nothing to cross-check, and nothing is not a pass.
    assert review["clearance"]["bounds_check"]["status"] == "unavailable"


def _assert_clearance(root, review, verdict):
    _assert_render(root, review)
    assert review["section"]["status"] == "ok"
    summary = review["clearance"]
    assert summary["available"] is True
    assert summary["pairs_checked"] == 1
    assert summary["unknown_pair_count"] == 0
    assert summary["offending_pair_count"] == int(verdict != "clear")
    assert summary["scope"] == "initial solved pose"
    assert summary["minimum_clearance_mm"] == 0.1
    assert summary["maximum_common_volume_mm3"] == 1e-6
    assert summary["path"] == "docs/clearance.md"
    text = (root / summary["path"]).read_text()
    assert verdict in text
    for row in summary["offending_pairs"]:
        assert row["status"] == verdict
        assert row["first_label"] in text and row["second_label"] in text
    assert "docs/clearance.md" in _git(root, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
    assert "clearance offending " + str(summary["offending_pair_count"]) in (root / "PROGRESS.md").read_text()
    # The review checks itself: the kernel's numbers against the render's
    # independently placed world bounds, two comparisons per measured pair.
    check = summary["bounds_check"]
    assert check["status"] == "pass", check
    assert (check["comparisons"], check["pairs_compared"]) == (2, 1)
    assert check["failures"] == [] and check["pairs_skipped"] == 0


@pytest.mark.parametrize("outcome", ["unknown", "failure"])
def test_walk_preserves_unknown_clearance_and_inspection_failures(
    fake_cadex, toy_root, capsys, monkeypatch, outcome,
):
    monkeypatch.setenv("FAKE_CLEARANCE", outcome)
    out = toy_root / "runs" / outcome
    code, report = _run(capsys, "walk", "--project", str(toy_root), "--out", str(out))
    if outcome == "failure":
        assert code != EXIT_OK
        assert "clearance inspection failed" in report["error"]
        assert not (out / REVIEW_FILENAME).exists()
        return
    assert code == EXIT_OK, report
    summary = json.loads((out / REVIEW_FILENAME).read_text())["clearance"]
    assert summary["available"] is True
    assert summary["unknown_pair_count"] == summary["pairs_checked"] == 1
    assert summary["offending_pair_count"] == 0
    assert summary["unknown_pairs"][0]["distance_mm"] is None
    assert summary["unknown_pairs"][0]["error"] == "measurement failed"
    assert "unknown" in (toy_root / "docs/clearance.md").read_text()


def _assert_render(root, review):
    from test_render import image_bytes
    summary = review["render"]
    assert summary["available"] is True
    assert summary["revision"] == review["clearance"]["revision"]
    assert summary["digest"] and summary["limits"] and summary["approximation"]
    assert set(summary["views"]) == {"front", "top", "right", "iso"}
    tracked = set(_git(root, "ls-tree", "-r", "--name-only", "HEAD").splitlines())
    assert summary["path"] not in tracked
    stored = json.loads((root / summary["path"]).read_text())
    assert stored["revision"] == summary["revision"]
    for view in summary["views"].values():
        assert view["path"] not in tracked
        assert view["covered_pixels"] > 0
        image_bytes(root / view["path"], summary["revision"])
    section = review["section"]
    assert section["revision"] == summary["revision"]
    assert section["digest"] == summary["digest"]
    # The review cuts where the geometry is, not at a constant (ADR-267).
    from cadex_cli.section import offset_candidates
    assert section["plane"] == "XZ" and section["offset_source"] == "derived"
    assert section["offset_mm"] == offset_candidates(summary, "XZ")[0]
    assert section["offset_candidates_mm"][0] == section["offset_mm"]
    assert section["units"] == "mm" and section["approximation"] and section["limits"]
    assert section["path"] not in tracked and section["summary_path"] not in tracked
    stored_section = json.loads((root / section["summary_path"]).read_text())
    assert stored_section == {k: v for k, v in section.items() if k not in {"summary_path", "missed_objects"}}
    assert section["acquisition_seconds"] == summary["acquisition_seconds"]
    import xml.etree.ElementTree as ET
    drawing = ET.parse(root / section["path"]).getroot()
    assert section["revision"] in drawing.find("{*}title").text
    if section["status"] == "ok":
        from test_section import area
        assert section["available"] is True
        assert len(drawing.findall("{*}path")) == 2
        assert all(area(loop) > 0 for obj in section["objects"].values() for loop in obj["contours_mm"])
    else:
        assert section["status"] in ("empty", "unsupported")
        assert section["available"] == (section["status"] == "empty")
    assert review["walk_seconds"] > summary["acquisition_seconds"] + summary["render_seconds"]


@pytest.mark.parametrize("failure", ["snapshot", "rollout", "digest"])
def test_walk_render_failure_cannot_reuse_old_success(fake_cadex, toy_root, capsys, monkeypatch, failure):
    out = toy_root / "runs/render-failure"
    code, report = _run(capsys, "walk", "--project", str(toy_root), "--out", str(out))
    assert code == EXIT_OK, report
    old = (out / REVIEW_FILENAME).read_bytes()
    monkeypatch.setenv("FAKE_RENDER_FAIL", failure)
    code, report = _run(capsys, "walk", "--project", str(toy_root), "--out", str(out))
    assert code != EXIT_OK
    assert ("accepted digest" if failure == "digest" else "accepted revision") in report["error"]
    assert (out / REVIEW_FILENAME).read_bytes() == old
    assert not report["walk"].get("review")


@pytest.mark.parametrize("outcome", ["empty", "unsupported", "write", "revision"])
def test_walk_section_status_and_failure_preserve_old_review(
    fake_cadex, toy_root, capsys, monkeypatch, outcome,
):
    from cadex_cli import __main__ as main_module
    from cadex_cli.section import write_section
    from cadex_cli.inventory import InventoryError
    out = toy_root / "runs/section-status"
    code, report = _run(capsys, "walk", "--project", str(toy_root), "--out", str(out))
    assert code == EXIT_OK, report
    old = (out / REVIEW_FILENAME).read_bytes()

    def section(client, root, **kwargs):
        # A second rebuild would replace the attempt backing the accepted buffers.
        class NoAcquisition:
            def request(self, *args):
                pytest.fail("section reacquired the shared snapshot")
        if outcome == "write":
            raise InventoryError("section: cannot write artifacts: injected failure")
        if outcome == "revision":
            kwargs["expected_revision"] = "wrong"
        elif outcome == "empty":
            kwargs["offset"] = 1000
        return write_section(NoAcquisition(), root, **kwargs)

    monkeypatch.setattr(main_module, "write_section", section)
    code, report = _run(capsys, "walk", "--project", str(toy_root), "--out", str(out))
    if outcome in ("write", "revision"):
        assert code != EXIT_OK and "section:" in report["error"]
        assert not report["walk"].get("review")
        assert (out / REVIEW_FILENAME).read_bytes() == old
    else:
        assert code == EXIT_OK, report
        review = json.loads((out / REVIEW_FILENAME).read_text())
        assert review["section"]["status"] == outcome
        assert review["section"]["available"] == (outcome == "empty")
        assert not any(o["contours_mm"] for o in review["section"]["objects"].values())


@pytest.mark.parametrize("status", ["match", "different", "unavailable"])
def test_walk_reports_engine_source_evidence_without_refusing(
    fake_cadex, toy_root, capsys, monkeypatch, tmp_path, status
):
    from cadex_cli import __main__ as main_module, engine as engine_module

    source = tmp_path / "source"
    installed = tmp_path / "prefix" / "Mod" / "cadex"
    source.mkdir()
    installed.mkdir(parents=True)
    (source / "CadexScriptedProcess.py").write_text("current")
    if status != "unavailable":
        (installed / "CadexScriptedProcess.py").write_text(
            "old" if status == "different" else "current")
    engine = engine_module.Engine(
        tmp_path / "prefix" / "bin" / "FreeCADCmd", source, "dev-tree")
    monkeypatch.setattr(engine_module, "DEV_MODULE_DIR", source)
    monkeypatch.setattr(main_module, "resolve_engine", lambda _: engine)
    code = main_module.main([
        "--project", str(toy_root), "walk", "--out", str(toy_root / "runs" / status),
        "--json",
    ])
    captured = capsys.readouterr()
    envelope = json.loads(captured.out)
    assert code == EXIT_OK, envelope
    evidence = envelope["walk"]["engine_source_comparison"]
    assert evidence["status"] == status
    assert evidence["comparison_dir"] == str(installed)
    assert json.dumps(evidence, sort_keys=True) in captured.err
    if status == "different":
        assert evidence["changed"] == ["CadexScriptedProcess.py"]


# -- the detached walk and its completion (ADR-282) ---------------------------


def _box(tmp_path, monkeypatch) -> Path:
    """Where the dispatcher would mirror a detached run's files."""

    box = tmp_path / "box-run-77"
    box.mkdir()
    monkeypatch.setenv("FAKE_BOX_DIR", str(box))
    return box


def _bring_home(box: Path, out: Path, *, state: str = "done",
                policy: bytes | None = None, task_sha256: str | None = None) -> bytes:
    """What `remote_train.sh pull` leaves in the run destination.

    The progress file the trainer rewrote, the box-side stdout with the
    trainer's receipt on its last JSON line, and the policy itself. Nothing
    here is written by the CLI, which is the point: the completion reads
    files another machine produced.
    """

    blob = policy if policy is not None else b"policy from the box"
    (box / "job.cxpolicy").write_bytes(blob)
    bundle = out / "train" / "job-task.json"
    digest = task_sha256 if task_sha256 is not None else hashlib.sha256(
        bundle.read_bytes()).hexdigest()
    (box / "training-progress.json").write_text(json.dumps({
        "schema": "cadex-training-progress-v1", "state": state,
        "out": "job.cxpolicy", "reward_per_step": 0.75, "error": "",
    }))
    (box / "train.log").write_text(
        "WARNING: some warp noise\n"
        + json.dumps({"out": "/w/run-77/job.cxpolicy", "bytes": len(blob),
                      "sha256": hashlib.sha256(blob).hexdigest(),
                      "task_sha256": digest, "reward_per_step": 0.75,
                      "wall_time_s": 61.0, "device": "cuda", "parameters": 12})
        + "\n==> trailer the dispatcher printed\n"
    )
    return blob


def test_a_detached_walk_stops_at_pending_and_declares_nothing(
    fake_cadex, toy_root, tmp_path, monkeypatch, capsys
) -> None:
    """Launch is not completion: the locator lands, and nothing else does."""

    _box(tmp_path, monkeypatch)
    out = toy_root / "runs" / "detached"
    before = (toy_root / "script.py").read_bytes()
    code, envelope = _run(
        capsys, "--project", str(toy_root), "walk", "--out", str(out),
        "--remote", "--detach", "--iterations", "2", "--envs", "3", "--seed", "5",
    )
    assert code == EXIT_OK, envelope
    assert envelope["walk"]["mode"] == "detach"
    assert [leg["leg"] for leg in envelope["walk"]["legs"]] == ["train"]
    assert envelope["training"]["state"] == "pending"
    assert envelope["training"]["run_id"] == "run-77"

    # The train leg was launched detached and was not asked to store.
    train_argv = [row for row in _legs(fake_cadex) if "train" in row][0]
    assert "--detach" in train_argv and "--put" not in train_argv

    pending = json.loads((out / PENDING_FILENAME).read_text())
    assert pending["schema"] == "cadex-walk-pending-v1"
    assert pending["training"]["run_id"] == "run-77"
    assert pending["training_seed"] == 5
    assert pending["task_sha256"] == hashlib.sha256(
        (out / "train" / "job-task.json").read_bytes()).hexdigest()
    assert any("remote_train.sh watch run-77" in line for line in pending["completion"])
    assert any("walk --complete" in line for line in pending["completion"])

    # Nothing a completed walk claims: no review, no policy, no declaration.
    assert not (out / REVIEW_FILENAME).exists()
    assert (toy_root / "script.py").read_bytes() == before
    assert not list(toy_root.glob("assets/*.cxpolicy"))
    row = (toy_root / "PROGRESS.md").read_text()
    assert "pending; no policy verified" in row


def test_complete_takes_the_pulled_policy_through_the_remaining_legs(
    fake_cadex, toy_root, tmp_path, monkeypatch, capsys
) -> None:
    """The second half runs the legs the blocking walk runs, and no others."""

    box = _box(tmp_path, monkeypatch)
    out = toy_root / "runs" / "detached"
    code, _ = _run(
        capsys, "--project", str(toy_root), "walk", "--out", str(out),
        "--remote", "--detach", "--iterations", "2", "--envs", "3", "--seed", "5",
    )
    assert code == EXIT_OK
    blob = _bring_home(box, out)

    code, envelope = _run(
        capsys, "--project", str(toy_root), "walk", "--out", str(out), "--complete",
    )
    assert code == EXIT_OK, envelope
    assert envelope["walk"]["mode"] == "complete"
    # The launch's leg is carried forward from the marker, then the rest.
    assert [leg["leg"] for leg in envelope["walk"]["legs"]] == [
        "train", "collect", "declare", "rollout",
    ]
    # No design turn and no trainer ran in this half.
    second = _legs(fake_cadex)[len([leg for leg in envelope["walk"]["legs"]]) - 4:]
    assert not any("train" in row and "--out" in row for row in second[1:])

    digest = hashlib.sha256(blob).hexdigest()
    assert envelope["training"]["sha256"] == digest
    # The trainer's `out` was a path on the box; the local file is what the
    # later legs read.
    assert envelope["training"]["out"] == str(box / "job.cxpolicy")
    assert envelope["training"]["trainer_out"] == "/w/run-77/job.cxpolicy"
    assert (toy_root / "assets" / "job.cxpolicy").read_bytes() == blob
    assert digest in (toy_root / "script.py").read_text()

    review = json.loads((out / REVIEW_FILENAME).read_text())
    assert review["sha256"] == digest and review["weights"] == "job.cxpolicy"
    assert review["total_reward"] == -12.5
    # The comparison a blocking walk lands, with the seed the launch used
    # rather than --complete's untyped default.
    assert review["comparison"]["training_seed"] == 5


@pytest.mark.parametrize("break_it,expected", [
    ("running", "reports state 'running'"),
    ("failed", "reports state 'failed'"),
    ("no-progress", "Bring the run home first"),
    ("foreign-task", "belongs to another run"),
    ("moved-bundle", "The script moved under the run"),
    ("wrong-bytes", "The transfer is wrong"),
])
def test_complete_refuses_what_it_cannot_honestly_declare(
    fake_cadex, toy_root, tmp_path, monkeypatch, capsys, break_it, expected
) -> None:
    """Each refusal has its own remedy, so each is its own message."""

    box = _box(tmp_path, monkeypatch)
    out = toy_root / "runs" / "detached"
    code, _ = _run(
        capsys, "--project", str(toy_root), "walk", "--out", str(out),
        "--remote", "--detach", "--iterations", "2", "--envs", "3",
    )
    assert code == EXIT_OK
    before = (toy_root / "script.py").read_bytes()

    if break_it in ("running", "failed"):
        _bring_home(box, out, state=break_it)
    elif break_it == "no-progress":
        pass
    elif break_it == "foreign-task":
        _bring_home(box, out, task_sha256="f" * 64)
    elif break_it == "moved-bundle":
        _bring_home(box, out)
        (out / "train" / "job-task.json").write_text('{"moved": true}')
    else:
        _bring_home(box, out)
        (box / "job.cxpolicy").write_bytes(b"a different policy entirely")

    code, envelope = _run(
        capsys, "--project", str(toy_root), "walk", "--out", str(out), "--complete",
    )
    assert code == EXIT_REJECTED, envelope
    assert expected in envelope["error"], envelope["error"]
    assert (toy_root / "script.py").read_bytes() == before
    assert not list(toy_root.glob("assets/*.cxpolicy"))


@pytest.mark.parametrize("flags,named", [
    (["--detach"], "--detach needs --remote."),
    (["--complete", "--remote"], "--remote"),
    (["--complete", "--prompt", "hello"], "--prompt"),
    (["--complete", "--set", "k=1"], "--set"),
])
def test_the_two_detached_modes_refuse_before_any_leg_runs(
    fake_cadex, toy_root, capsys, flags, named
) -> None:
    out = toy_root / "runs" / "usage"
    code, envelope = _run(
        capsys, "--project", str(toy_root), "walk", "--out", str(out), *flags,
    )
    assert code == EXIT_USAGE, envelope
    assert named in envelope["error"]
    assert not fake_cadex.exists(), "a leg ran before the usage error"
