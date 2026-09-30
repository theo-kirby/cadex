# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``cadex evaluate``: the accepted policy against its task's success spec (ADR-457).

Three layers, each with less under it than the last. What the command reads
from a project is tested against a hand-built retained attempt and needs
nothing. The child is run for real against the engine's own fixtures, which
needs ``mujoco`` in this interpreter and no built engine. The command itself
-- a script accepted by a live engine, a policy it verified, one
``cadex evaluate`` -- needs a built engine and skips without one.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import textwrap
import tokenize

import pytest

from conftest import SOURCE_MODULE_DIR

from cadex_cli import evaluate as evaluate_module
from cadex_cli.__main__ import main
from cadex_cli.engine import Engine
from cadex_cli.evaluate import (
    EVALUATE_SCRIPT,
    REPORT_NAME,
    EvaluateError,
    EvaluateRefused,
    check_out,
    default_out,
    evaluation_cell,
    failing_predicates,
    human_lines,
    retained_inputs,
    run_evaluation,
)
from cadex_cli.report import EXIT_FAILURE, EXIT_OK, EXIT_REJECTED, EXIT_USAGE, RunReport
from cadex_cli.report import human_lines as report_lines
from cadex_cli.smoke import retained_attempt

HAS_MUJOCO = importlib.util.find_spec("mujoco") is not None
needs_mujoco = pytest.mark.skipif(not HAS_MUJOCO, reason="mujoco is not importable here")

REVISION = "a" * 64
DIGEST = "d" * 64


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# -- what the command reads from a project ----------------------------------

def _retained(root: Path, *, success: bool = True, policies=("pol",), weights=b"weights",
              recorded_weights: bytes | None = None) -> Path:
    """A project as the store leaves one: a pin, a result, and its artifacts."""

    staging = root / "script_artifacts" / REVISION / "attempt-1"
    (staging / "outputs").mkdir(parents=True)
    (staging / "assets").mkdir()
    model = b"<mujoco/>"
    task = {"label": "stand", "model": {"output": "model", "sha256": _sha(model)}}
    if success:
        task["success"] = {"seeds": [1101, 1102], "predicates": []}
    task_bytes = json.dumps(task).encode()
    outputs = [
        {"name": "brick", "artifact_kind": "brep", "artifact_path": "outputs/output-000.brep"},
        {"name": "model", "artifact_kind": "assembly_mjcf_xml",
         "artifact_path": "outputs/model-model.xml", "artifact_sha256": _sha(model),
         "assembly_data": {"component_outputs": ["block", "paddle"]}},
        {"name": "job", "artifact_kind": "assembly_training_task_json",
         "artifact_path": "outputs/job-task.json", "artifact_sha256": _sha(task_bytes)},
    ]
    (staging / "outputs" / "model-model.xml").write_bytes(model)
    (staging / "outputs" / "job-task.json").write_bytes(task_bytes)
    for name in policies:
        (staging / "assets" / f"{name}.cxpolicy").write_bytes(weights)
        receipt = json.dumps({
            "weights": f"{name}.cxpolicy", "task_output": "job", "task_sha256": _sha(task_bytes),
            "policy_sha256": _sha(weights if recorded_weights is None else recorded_weights),
        }).encode()
        (staging / "outputs" / f"{name}-policy.json").write_bytes(receipt)
        outputs.append({"name": name, "artifact_kind": "assembly_policy_receipt_json",
                        "artifact_path": f"outputs/{name}-policy.json",
                        "artifact_sha256": _sha(receipt)})
    (staging / "result.json").write_text(json.dumps(
        {"ok": True, "digest": DIGEST, "outputs": outputs}))
    (root / "script.json").write_text(json.dumps({
        "schema": "cadex-project-script-v1", "accepted_revision": REVISION,
        "accepted_digest": DIGEST,
        "accepted_attempt": {"revision": REVISION,
                             "staging": str(staging.relative_to(root))},
    }))
    return staging


def test_the_inputs_are_the_policy_the_accepted_revision_verified(tmp_path) -> None:
    staging = _retained(tmp_path)
    inputs = retained_inputs(tmp_path)

    assert inputs["accepted_revision"] == REVISION and inputs["accepted_digest"] == DIGEST
    assert (inputs["policy_output"], inputs["task_output"], inputs["model_output"]) == (
        "pol", "job", "model")
    assert inputs["policy"] == staging / "assets" / "pol.cxpolicy"
    assert inputs["policy_sha256"] == _sha(b"weights") and inputs["weights"] == "pol.cxpolicy"
    assert inputs["task"] == staging / "outputs" / "job-task.json"
    assert inputs["model"] == staging / "outputs" / "model-model.xml"
    assert inputs["components"] == ["block", "paddle"] and inputs["seeds"] == [1101, 1102]
    # One accepted revision and one policy are one evaluation.
    assert default_out(tmp_path, inputs) == tmp_path / "evaluations" / ("a" * 12 + "-" + _sha(b"weights")[:12])


def test_nothing_to_evaluate_is_a_refusal_that_says_what_to_declare(tmp_path) -> None:
    with pytest.raises(EvaluateRefused, match="retained accepted attempt"):
        retained_inputs(tmp_path / "empty")

    _retained(tmp_path / "bare", policies=())
    with pytest.raises(EvaluateRefused, match=r"declares no policy.*assembly\.policy"):
        retained_inputs(tmp_path / "bare")

    _retained(tmp_path / "unjudged", success=False)
    with pytest.raises(EvaluateRefused, match=r"declares no success spec.*assembly\.success"):
        retained_inputs(tmp_path / "unjudged")


def test_several_policies_are_a_choice_and_one_must_remain(tmp_path) -> None:
    _retained(tmp_path, policies=("first", "second"))
    with pytest.raises(EvaluateRefused, match="more than one declared policy.*first.*second"):
        retained_inputs(tmp_path)
    assert retained_inputs(tmp_path, policy_name="second")["policy_output"] == "second"
    with pytest.raises(EvaluateRefused, match="no declared policy matches"):
        retained_inputs(tmp_path, policy_name="third")
    with pytest.raises(EvaluateRefused, match="no declared policy matches"):
        retained_inputs(tmp_path, policy_name="first", task_name="other")


def test_the_weights_evaluated_are_the_weights_verified(tmp_path) -> None:
    _retained(tmp_path / "swapped", recorded_weights=b"what the engine verified")
    with pytest.raises(EvaluateError, match="not the file policy pol was verified with"):
        retained_inputs(tmp_path / "swapped")

    staging = _retained(tmp_path / "edited")
    (staging / "outputs" / "job-task.json").write_text("{}")
    with pytest.raises(EvaluateError, match="digest mismatch: job"):
        retained_inputs(tmp_path / "edited")


def test_out_never_lands_on_the_projects_own_state(tmp_path) -> None:
    for inside in ("", "assets", "script_artifacts/x", ".git/y"):
        with pytest.raises(EvaluateError, match="must not overwrite"):
            check_out(tmp_path, tmp_path / inside)
    assert check_out(tmp_path, tmp_path / "evaluations" / "e1") == tmp_path / "evaluations" / "e1"


# -- what it says -----------------------------------------------------------

REPORT = {
    "verdict": "fail", "policy_sha256": "7a4e8c23" + "0" * 56, "task_output": "walk_task",
    "summary": {
        "seeds": 10, "passed": [1101], "failed": list(range(1102, 1111)), "pass": False,
        "predicates": [
            {"id": "W1", "metric": "completed", "min": 1.0, "max": None, "passed": 10,
             "failed_seeds": [], "value": {"min": 1.0, "median": 1.0, "max": 1.0}},
            {"id": "W5", "metric": "step_share_min", "min": 0.7, "max": None, "passed": 1,
             "failed_seeds": list(range(1102, 1111)),
             "value": {"min": 0.0, "median": 0.1, "max": 0.71}},
            {"id": "W7", "metric": "slip_share_max", "min": None, "max": 0.15, "passed": 0,
             "failed_seeds": list(range(1101, 1111)),
             "value": {"min": 0.53, "median": 0.6, "max": 0.76}},
            {"id": "W6", "metric": "step_clearance_hip_heights_min", "min": 0.08, "max": None,
             "passed": 8, "failed_seeds": [1103, 1104], "value": None},
        ],
        "terminations": {"horizon": 8, "tipped": 2},
    },
}


def test_the_failing_predicates_are_named_worst_first() -> None:
    assert failing_predicates(REPORT) == ["W7 (10 of 10)", "W5 (9 of 10)", "W6 (2 of 10)"]
    assert evaluation_cell(REPORT) == (
        "evaluation fail 1/10 seeds: W7 (10 of 10); W5 (9 of 10); W6 (2 of 10)")
    passing = {"verdict": "pass", "summary": {"seeds": 3, "passed": [1, 2, 3], "predicates": [
        {"id": "a", "failed_seeds": []}]}}
    assert failing_predicates(passing) == []
    assert evaluation_cell(passing) == "evaluation pass 3/3 seeds"
    many = {"verdict": "fail", "summary": {"seeds": 2, "passed": [], "predicates": [
        {"id": f"p{i}", "failed_seeds": [1, 2]} for i in range(6)]}}
    assert evaluation_cell(many).endswith("p3 (2 of 2) (+2 more)")


def test_a_void_seed_leads_the_row_and_has_its_own_line() -> None:
    void = {**REPORT, "summary": {**REPORT["summary"], "void": [1104, 1108]}}
    assert evaluation_cell(void).startswith(
        "evaluation fail 1/10 seeds: unstable simulation (2 of 10); W7 (10 of 10)")
    assert failing_predicates(void)[0] == "unstable simulation (2 of 10)"
    assert human_lines(void)[-1] == "  void: the simulation went unstable on seed(s) 1104, 1108"


def test_the_prose_block_tallies_every_predicate_and_every_ending() -> None:
    lines = human_lines(REPORT)
    assert lines[0] == "evaluate fail  1 of 10 seeds pass  policy 7a4e8c230000  task walk_task"
    assert lines[1] == "  ok   W1 completed ≥ 1: 10 of 10  (1 … 1)"
    assert lines[2] == "  FAIL W5 step_share_min ≥ 0.7: 1 of 10  (0 … 0.71)"
    assert lines[3] == "  FAIL W7 slip_share_max ≤ 0.15: 0 of 10  (0.53 … 0.76)"
    assert lines[4].endswith("8 of 10  (not measured)")
    assert lines[5] == "  ended: horizon ×8, tipped ×2"
    report = RunReport(evaluation=REPORT)
    assert report.to_json()["evaluation"] == REPORT
    assert [line for line in report_lines(report) if line.startswith("evaluate ")] == [lines[0]]


# -- the child --------------------------------------------------------------

def _code(path: Path) -> str:
    """A module's code with its comments and docstrings taken out."""

    source = path.read_text(encoding="utf-8")
    tokens = [token for token in tokenize.generate_tokens(io.StringIO(source).readline)
              if token.type != tokenize.COMMENT]
    tree = ast.parse(tokenize.untokenize(tokens))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body and (
                isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            node.body = node.body[1:] or [ast.Pass()]
    return ast.unparse(tree)


def test_the_runner_imports_the_standard_library_and_the_engine_the_plan_names() -> None:
    """Run by path under the engine's interpreter: nothing from ``cadex_cli``,
    and the engine only through the module directory the plan names."""

    tree = ast.parse(EVALUATE_SCRIPT.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(str(node.module or "").split(".")[0])
    assert imported == {"__future__", "hashlib", "json", "math", "pathlib", "sys", "time",
                        "typing", "CadexDynamics"}, imported


def test_the_command_names_no_behaviour() -> None:
    """A walk, a reach and a balance are three specs through one path, so
    none of the three is a word in the code that evaluates them."""

    for path in (EVALUATE_SCRIPT, Path(evaluate_module.__file__)):
        assert not re.search(r"walk|gait|balanc|reach|feet|foot|quadruped|biped",
                             _code(path), re.IGNORECASE), path.name


#: Builds the engine suite's own fixture -- a free block with a flap, a task
#: with a balance spec on three seeds, a policy of zero weights -- and writes
#: the three files an evaluation reads. Its own process, so the engine's
#: test modules never enter this suite's.
_FIXTURE = """
import json, sys
sys.path[:0] = [{module_dir!r}, {tests_dir!r}]
import CadexDynamics as dyn
import test_evaluate_success_model as fixtures
from test_success_spec_model import BALANCE, spec

arguments = json.loads(sys.argv[2])
made = fixtures.prepared(spec(BALANCE + arguments.get("extra", []), episode_seconds=4.0),
                         training_seed=arguments.get("training_seed", 7))
out = sys.argv[1]
open(out + "/model.xml", "wb").write(made["xml"])
task = json.dumps(made["bundle"], indent=2, sort_keys=True).encode()
open(out + "/task.json", "wb").write(task)
header = dict(made["container"]["header"])
open(out + "/policy.cxpolicy", "wb").write(dyn.encode_policy(header, made["container"]["weights"]))
"""


def _inputs(tmp_path: Path, **arguments) -> dict:
    source = tmp_path / "inputs"
    source.mkdir(exist_ok=True)
    script = _FIXTURE.format(module_dir=str(SOURCE_MODULE_DIR),
                             tests_dir=str(SOURCE_MODULE_DIR / "cadex_tests"))
    subprocess.run([sys.executable, "-c", script, str(source), json.dumps(arguments)],
                   check=True, capture_output=True, text=True)
    return {
        "accepted_revision": REVISION, "accepted_digest": DIGEST, "policy_output": "pol",
        "task_output": "job", "model_output": "model", "weights": "policy.cxpolicy",
        "policy": source / "policy.cxpolicy",
        "policy_sha256": _sha((source / "policy.cxpolicy").read_bytes()),
        "trained_task_sha256": _sha((source / "task.json").read_bytes()),
        "task": source / "task.json", "model": source / "model.xml",
        "components": ["body", "flap"], "seeds": [1101, 1102, 1103],
    }


def _source_engine(tmp_path: Path) -> Engine:
    """The source tree's engine modules under this interpreter: no build."""

    return Engine(tmp_path / "bin" / "FreeCADCmd", SOURCE_MODULE_DIR, "dev-tree")


@needs_mujoco
def test_the_child_evaluates_every_seed_and_leaves_a_report_and_a_trace_each(tmp_path) -> None:
    inputs = _inputs(tmp_path)
    out = tmp_path / "evaluation"
    report = run_evaluation(_source_engine(tmp_path), inputs, out)

    assert report == json.loads((out / REPORT_NAME).read_text(encoding="utf-8"))
    assert report["schema"] == "cadex-evaluation-v1" and report["verdict"] == "pass"
    assert report["accepted_revision"] == REVISION and report["policy_output"] == "pol"
    assert report["policy_sha256"] == inputs["policy_sha256"]
    assert report["task_sha256"] == _sha(inputs["task"].read_bytes())
    assert report["model_sha256"] == _sha(inputs["model"].read_bytes())
    assert len(report["task_semantic_sha256"]) == 64
    assert report["summary"]["passed"] == [1101, 1102, 1103] and report["summary"]["pass"] is True
    assert report["summary"]["terminations"] == {"horizon": 3}
    assert [row["id"] for row in report["spec"]["predicates"]] == [
        "completes", "upright", "in_place", "recovers"]
    assert report["spec"]["episode"]["episode_seconds"] == 4.0
    assert report["spec"]["scale"]["com_height_mm"] == pytest.approx(report["rig"]["com_height_mm"])
    for row in report["seeds"]:
        assert row["pass"] is True and len(row["predicates"]) == 4
        assert [term["label"] for term in row["reward"]["terms"]] == ["height", "still"]
        assert row["episode"]["termination"] == "" and row["episode"]["duration_s"] == 4.0
        assert row["drawn"]["disturbance"][0]["label"] == "shove"
        trace = out / row["trace"]["file"]
        assert trace.name == f"seed-{row['seed']}-trace.json"
        assert _sha(trace.read_bytes()) == row["trace"]["sha256"]
        document = json.loads(trace.read_text(encoding="utf-8"))
        assert document["schema"] == "cadex-assembly-simulation-trace-v1"
        assert document["policy"]["policy_sha256"] == inputs["policy_sha256"]
        assert document["policy"]["seed"] == row["seed"]
        assert document["component_outputs"] == ["body", "flap"]
        assert len(document["frames"]) == row["frames"] + 1  # the untimed input frame
    assert sorted(path.name for path in out.iterdir()) == [
        REPORT_NAME, "seed-1101-trace.json", "seed-1102-trace.json", "seed-1103-trace.json"]

    # Frozen seeds: the same policy is the same episodes, byte for byte.
    again = run_evaluation(_source_engine(tmp_path), inputs, out)
    assert [row["trace"]["sha256"] for row in again["seeds"]] == [
        row["trace"]["sha256"] for row in report["seeds"]]
    assert again["seeds"] == report["seeds"] and again["summary"] == report["summary"]


@needs_mujoco
def test_a_failed_evaluation_is_a_verdict_and_names_the_predicate(tmp_path) -> None:
    inputs = _inputs(tmp_path, extra=[{"id": "brief", "metric": "duration_s", "max": 1.0}])
    report = run_evaluation(_source_engine(tmp_path), inputs, tmp_path / "evaluation")

    assert report["verdict"] == "fail" and report["summary"]["passed"] == []
    assert failing_predicates(report) == ["brief (3 of 3)"]
    assert evaluation_cell(report) == "evaluation fail 0/3 seeds: brief (3 of 3)"
    for row in report["seeds"]:
        assert row["failing"] == ["brief"]
        assert row["predicates"][-1]["why"] == "duration_s is 4, over 1"


@needs_mujoco
def test_an_engine_refusal_reaches_the_caller_with_its_correction(tmp_path) -> None:
    inputs = _inputs(tmp_path, training_seed=1102)
    out = tmp_path / "evaluation"
    with pytest.raises(EvaluateRefused) as raised:
        run_evaluation(_source_engine(tmp_path), inputs, out)
    assert "seed 1102, which is the seed it was trained with" in str(raised.value)
    assert "Evaluation seeds are never training seeds" in str(raised.value)
    # No report that looks complete, and nothing half-written beside it.
    assert list(out.iterdir()) == []


@needs_mujoco
def test_a_model_that_is_not_the_tasks_is_refused_before_any_rollout(tmp_path) -> None:
    inputs = _inputs(tmp_path)
    inputs["model"].write_bytes(inputs["model"].read_bytes() + b"\n")
    with pytest.raises(EvaluateRefused, match="not the one its bundle recorded"):
        run_evaluation(_source_engine(tmp_path), inputs, tmp_path / "evaluation")


def test_a_child_that_hangs_is_killed_at_the_bound(tmp_path, monkeypatch) -> None:
    def hang(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(evaluate_module.subprocess, "run", hang)
    inputs = {"model": "m", "task": "t", "policy": "p", "components": []}
    with pytest.raises(EvaluateError, match="past its bound of 5 s"):
        run_evaluation(_source_engine(tmp_path), inputs, tmp_path / "evaluation", timeout=5.0)
    assert not (tmp_path / "evaluation" / REPORT_NAME).exists()


# -- the command, against a built engine -------------------------------------

#: The engine suite's live success-spec fixture (``test_success_spec_live``),
#: as a policy is declared against it: a free block with a paddle, a task
#: that trains for 1 s under a light shove, and a spec that judges over 3 s
#: on three seeds under a harder one.
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
model = assembly.mjcf(asm, [
    assembly.body(block, density_kg_m3=2700,
                  collision=[assembly.collision(
                      "box", size_mm=[120, 60, 40],
                      offset={"position": [60, 30, 20]})]),
    assembly.body(paddle, density_kg_m3=2700),
], actuators=[motor], observations=[
    assembly.observation(block, "component_position", name="base"),
    assembly.observation(wrist, "position", name="angle"),
])
start = assembly.reset_variation(block, tilt_degrees=[0.0, 4.0],
                                 height_mm=[10.0, 13.0], label="start")
shove = assembly.disturbance(block, newtons=[2.0, 4.0],
                             at_seconds=[0.2, 0.5], duration_s=0.1,
                             label="shove")
harder = assembly.disturbance(block, newtons=[6.0, 8.0],
                              at_seconds=[1.0, 1.5], duration_s=0.1,
                              label="harder")
spec = assembly.success(
    [
        {"id": "completes", "metric": "completed", "min": 1},
        {"id": "upright", "metric": "max_tilt_deg", "max": 30},
        @EXTRA@
    ],
    seeds=[1101, 1102, 1103],
    episode_seconds=3.0,
    reset_variation=[],
    disturbance=[harder],
    label="stays up",
)
job = assembly.task(model, actions=[motor],
                    reward=[assembly.reward("base_z", weight=1.0e-3,
                                            label="height")],
                    episode_seconds=1.0, control_hz=50,
                    reset_variation=[start], disturbance=[shove],
                    @SUCCESS@ label="stand")
result = {"brick": brick, "tab": tab, "block": block, "paddle": paddle,
          "wrist": wrist, "asm": asm, "diag": diag, "model": model,
          "job": job}
"""

POLICY = """
pol = assembly.policy(job, weights="job.cxpolicy", sha256="@SHA@")
result["pol"] = pol
"""

#: A policy container for a retained task bundle, built by the engine
#: suite's own fixture (random weights, and a witness from its second
#: forward pass), so a live engine verifies it.
_POLICY_FIXTURE = """
import hashlib, json, sys
sys.path[:0] = [{module_dir!r}, {tests_dir!r}]
import dynamics_policy_fixtures as pf
task = open(sys.argv[1], "rb").read()
made = pf.policy_container({{"bundle": json.loads(task),
                            "task_sha256": hashlib.sha256(task).hexdigest()}})
open(sys.argv[2], "wb").write(made["blob"])
"""


def _run(capsys, *argv: str) -> tuple[int, dict]:
    code = main([*argv, "--json"])
    return code, json.loads(capsys.readouterr().out)


def _source(extra: str = "", success: str = "success=spec,") -> str:
    return SCRIPT.replace("@EXTRA@", extra).replace("@SUCCESS@", success)


def _project(tmp_path: Path, capsys, name: str, source: str, *, policy: bool = True) -> Path:
    """A project whose accepted revision declares a verified policy."""

    root = tmp_path / name
    script = tmp_path / f"{name}.py"
    script.write_text(source, encoding="utf-8")
    code, envelope = _run(capsys, "script", "--set", str(script), "--project", str(root))
    assert code == EXIT_OK, envelope
    if not policy:
        return root
    _state, staging, _result = retained_attempt(root)
    weights = tmp_path / "job.cxpolicy"
    fixture = _POLICY_FIXTURE.format(module_dir=str(SOURCE_MODULE_DIR),
                                     tests_dir=str(SOURCE_MODULE_DIR / "cadex_tests"))
    subprocess.run([sys.executable, "-c", fixture, str(staging / "outputs" / "job-task.json"),
                    str(weights)], check=True, capture_output=True, text=True)
    code, envelope = _run(capsys, "asset", "--put", str(weights), "--project", str(root))
    assert code == EXIT_OK, envelope
    script.write_text(source + POLICY.replace("@SHA@", _sha(weights.read_bytes())),
                      encoding="utf-8")
    code, envelope = _run(capsys, "script", "--set", str(script), "--project", str(root))
    assert code == EXIT_OK, envelope
    return root


def test_a_usage_error_comes_before_any_engine(tmp_path, capsys) -> None:
    project = tmp_path / "never"
    for timeout in ("0", "7201"):
        code, envelope = _run(capsys, "evaluate", "--project", str(project), "--timeout", timeout)
        assert code == EXIT_USAGE and "--timeout" in envelope["error"], envelope
    for flag, value in (("--detail-step", "0"), ("--detail-step", "-0.2"), ("--detail-start", "-1"),
                        ("--detail-start", "nan")):
        code, envelope = _run(capsys, "evaluate", "--project", str(project), flag, value)
        assert code == EXIT_USAGE and flag in envelope["error"], envelope
    assert not project.exists()


@needs_mujoco
def test_an_accepted_policy_is_evaluated_as_one_command(engine, tmp_path, capsys) -> None:
    project = _project(tmp_path, capsys, "stands", _source())
    before = (project / "script.json").read_bytes()
    code, envelope = _run(capsys, "evaluate", "--project", str(project))
    assert code == EXIT_OK, envelope

    evaluation = envelope["evaluation"]
    assert evaluation["verdict"] == "pass" and evaluation["label"] == "stays up"
    assert (evaluation["policy_output"], evaluation["task_output"]) == ("pol", "job")
    assert evaluation["summary"]["passed"] == [1101, 1102, 1103]
    state = json.loads(before)
    # It lands in the project, named for the revision and the policy.
    path = Path(evaluation["report"])
    assert path == project / "evaluations" / (
        f"{state['accepted_revision'][:12]}-{evaluation['policy_sha256'][:12]}") / REPORT_NAME
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["accepted_digest"] == envelope["digest"] == state["accepted_digest"]
    assert report["summary"] == evaluation["summary"]
    assert [row["seed"] for row in report["seeds"]] == [1101, 1102, 1103]
    for row in report["seeds"]:
        assert row["episode"]["duration_s"] == 3.0
        (push,) = row["drawn"]["disturbance"]
        assert push["label"] == "harder" and 6.0 <= push["newtons"] <= 8.0
        assert row["drawn"]["reset_variation"] == []
        assert (path.parent / row["trace"]["file"]).is_file()
        assert [term["label"] for term in row["reward"]["terms"]] == ["height"]
    # It read the accepted artifacts and accepted nothing.
    assert (project / "script.json").read_bytes() == before
    # The run is a row on the project with its verdict, and the report is in
    # the project's own history; the frames are not.
    progress = (project / "PROGRESS.md").read_text(encoding="utf-8")
    assert "evaluate pol on job → pass" in progress and "evaluation pass 3/3 seeds" in progress
    tracked = subprocess.run(["git", "-C", str(project), "ls-files", "evaluations"],
                             capture_output=True, text=True, check=True).stdout.split()
    # ...and neither is the film drawn from them (ADR-459): the sheets and
    # the video are on disk beside the report, and out of the history.
    assert tracked == [str(path.parent.relative_to(project) / ".gitignore"),
                       str(path.relative_to(project))]
    film = report_film = json.loads(path.read_text(encoding="utf-8"))["film"]
    assert film["state"] == "ready" and evaluation["film"]["state"] == "ready", report_film
    (filmed,) = film["seeds"]
    assert filmed["seed"] == 1101                    # a pass films its first seed
    for key in ("overview", "detail", "video"):
        assert (path.parent / filmed[key]["file"]).is_file(), key
        assert evaluation["film"]["seeds"][0][key] == str(path.parent / filmed[key]["file"])
    assert filmed["detail"]["start_source"] == "the seed's first disturbance"
    assert any(note.startswith("evaluation pass: 3 of 3 seeds pass") for note in envelope["notes"])


@needs_mujoco
def test_the_film_is_chosen_skipped_and_drawn_again_without_measuring(engine, tmp_path, capsys) -> None:
    """ADR-459: ``--film none`` measures and draws nothing; ``--film-only``
    draws another seed from the traces on disk and measures nothing; a film
    that cannot be drawn is a failure that leaves the measurement."""

    project = _project(tmp_path, capsys, "filmed", _source())
    code, envelope = _run(capsys, "evaluate", "--project", str(project), "--film-only")
    assert code == EXIT_REJECTED and "no evaluation in" in envelope["error"], envelope

    code, envelope = _run(capsys, "evaluate", "--project", str(project), "--film", "none")
    assert code == EXIT_OK and envelope["evaluation"]["film"] == {
        "state": "skipped", "error": None, "seeds": []}, envelope
    path = Path(envelope["evaluation"]["report"])
    measured = json.loads(path.read_text(encoding="utf-8"))
    assert measured["film"]["state"] == "skipped" and not list(path.parent.glob("*.png"))
    traces = {p.name: p.stat().st_mtime_ns for p in path.parent.glob("seed-*-trace.json")}
    assert len(traces) == 3

    code, envelope = _run(capsys, "evaluate", "--project", str(project), "--film-only",
                          "--film", "1102", "--no-video", "--detail-start", "0.5", "--detail-step", "0.1")
    assert code == EXIT_OK, envelope
    again = json.loads(path.read_text(encoding="utf-8"))
    assert {key: again[key] for key in measured if key != "film"} == {
        key: measured[key] for key in measured if key != "film"}
    assert {p.name: p.stat().st_mtime_ns for p in path.parent.glob("seed-*-trace.json")} == traces
    (filmed,) = again["film"]["seeds"]
    assert filmed["seed"] == 1102 and filmed["video"] is None
    assert (filmed["detail"]["start_s"], filmed["detail"]["step_s"]) == (0.5, 0.1)
    assert sorted(p.name for p in path.parent.glob("seed-1102-*.png")) == [
        "seed-1102-detail.png", "seed-1102-overview.png"]
    assert envelope["evaluation"]["film"]["seeds"] == [{
        "seed": 1102, "overview": str(path.parent / "seed-1102-overview.png"),
        "detail": str(path.parent / "seed-1102-detail.png")}]

    code, envelope = _run(capsys, "evaluate", "--project", str(project), "--film-only", "--film", "4242")
    assert code == EXIT_FAILURE, envelope
    assert envelope["error"].startswith("the evaluation was measured, and its film could not be drawn")
    assert "4242" in envelope["error"] and envelope["evaluation"]["verdict"] == "pass"
    failed = json.loads(path.read_text(encoding="utf-8"))
    assert failed["film"]["state"] == "failed" and failed["seeds"] == measured["seeds"]


@needs_mujoco
def test_a_policy_that_fails_its_spec_exits_zero_with_the_verdict(engine, tmp_path, capsys) -> None:
    extra = '{"id": "brief", "metric": "duration_s", "max": 1.0},'
    project = _project(tmp_path, capsys, "fails", _source(extra))
    out = project / "evaluations" / "named"
    code, envelope = _run(capsys, "evaluate", "--project", str(project), "--out", str(out),
                          "--policy", "pol", "--task", "job")
    # Reported, never refused: a failed evaluation is a measurement.
    assert code == EXIT_OK, envelope
    assert envelope["evaluation"]["verdict"] == "fail"
    assert envelope["evaluation"]["summary"]["failed"] == [1101, 1102, 1103]
    assert Path(envelope["evaluation"]["report"]) == out / REPORT_NAME
    progress = (project / "PROGRESS.md").read_text(encoding="utf-8")
    assert "evaluation fail 0/3 seeds: brief (3 of 3)" in progress


def test_nothing_to_evaluate_is_rejected_and_runs_no_child(engine, tmp_path, capsys,
                                                           monkeypatch) -> None:
    def never(*args, **kwargs):
        raise AssertionError("no evaluation may run without a policy and a spec")

    from cadex_cli import __main__ as commands

    unjudged = _project(tmp_path, capsys, "unjudged", _source(success=""))
    unpoliced = _project(tmp_path, capsys, "unpoliced", _source(), policy=False)
    monkeypatch.setattr(commands, "run_evaluation", never)
    for project, word in ((unjudged, "declares no success spec"),
                          (unpoliced, "declares no policy"),
                          (tmp_path / "empty", "retained")):
        code, envelope = _run(capsys, "evaluate", "--project", str(project))
        assert code == EXIT_REJECTED and word in envelope["error"], envelope
        assert not (project / "evaluations").exists()


@needs_mujoco
def test_evaluate_never_restores_or_accepts_an_edited_working_script(engine, tmp_path,
                                                                     capsys) -> None:
    project = _project(tmp_path, capsys, "retained", _source())
    changed = b'raise RuntimeError("the evaluate command must not execute me")\n'
    (project / "script.py").write_bytes(changed)
    before = (project / "script.json").read_bytes()
    code, envelope = _run(capsys, "evaluate", "--project", str(project))
    assert code == EXIT_OK and envelope["evaluation"]["verdict"] == "pass", envelope
    assert (project / "script.py").read_bytes() == changed
    assert (project / "script.json").read_bytes() == before


def test_the_report_block_is_documented() -> None:
    """``docs/CLI.md`` names the command, its schema and where it lands."""

    text = (SOURCE_MODULE_DIR.parents[2] / "docs" / "CLI.md").read_text(encoding="utf-8")
    for word in ("cadex evaluate", "cadex-evaluation-v1", "evaluations/", "evaluation.json"):
        assert word in text, word
    assert textwrap.dedent(evaluate_module.__doc__).strip().startswith("``cadex evaluate``")
