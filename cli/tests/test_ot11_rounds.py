# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ot11 P4: the runner that drives the product agent through the loop.

``docs/probes/ot11/runner/rounds.py`` runs one frozen first prompt and then
a frozen continuation for as long as the project's loop ledger says the loop
is not over; ``block_probe.py`` measures how long one tool call may block a
turn. Neither may know a behaviour, and the prompts a receipt names must be
the ones on disk.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import math
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROBE = REPO / "docs" / "probes" / "ot11"
RUNNER = PROBE / "runner"
RETAINED = PROBE / "retained"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, RUNNER / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ledger(root: Path, *rows: dict) -> None:
    (root / "loop-ledger.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_the_loop_is_over_on_a_pass_or_when_the_runs_are_spent(tmp_path: Path) -> None:
    rounds = _load("rounds")
    assert rounds.standing(tmp_path) == {
        "runs_registered": 0, "runs_ended": 0, "runs_this_session": 0,
        "settled_this_session": 0, "evaluations": 0, "passed": False}
    assert not rounds.over(rounds.standing(tmp_path), 4)

    def run(name: str, verdict: str) -> list[dict]:
        return [{"kind": "train_registered", "run": name},
                {"kind": "train_ended", "run": name, "state": "finished",
                 "policy_sha256": name},
                {"kind": "evaluated", "verdict": verdict, "policy_sha256": name}]

    _ledger(tmp_path, *run("a", "fail"))
    assert not rounds.over(rounds.standing(tmp_path), 4)
    _ledger(tmp_path, *run("a", "fail"), *run("b", "pass"))
    assert rounds.over(rounds.standing(tmp_path), 4)
    # An earlier pass followed by a failure is not a pass.
    _ledger(tmp_path, *run("a", "pass"), *run("b", "fail"))
    assert not rounds.over(rounds.standing(tmp_path), 4)
    # Spent: as many runs ended and evaluated as allowed, and nothing still training.
    spent = [row for name in "abcd" for row in run(name, "fail")]
    _ledger(tmp_path, *spent)
    assert rounds.over(rounds.standing(tmp_path), 4)
    _ledger(tmp_path, *spent, {"kind": "train_registered", "run": "e"})
    assert not rounds.over(rounds.standing(tmp_path), 4)
    # A run that ended with no policy is spent without an evaluation.
    _ledger(tmp_path, *spent[:9], {"kind": "train_registered", "run": "d"},
            {"kind": "train_ended", "run": "d", "state": "collapsed"})
    assert rounds.over(rounds.standing(tmp_path), 4)
    # A run that ended with a policy is not spent until that policy is evaluated.
    _ledger(tmp_path, *spent[:11])
    assert not rounds.over(rounds.standing(tmp_path), 4)


def test_a_re_evaluation_does_not_use_up_a_round(tmp_path: Path) -> None:
    """Walk session 6: the agent re-evaluated an earlier policy, the driver
    counted that evaluation as a run, and the session stopped one run early."""
    rounds = _load("rounds")
    earlier = [{"kind": "train_registered", "run": "old"},
               {"kind": "train_ended", "run": "old", "state": "finished", "policy_sha256": "old"},
               {"kind": "evaluated", "verdict": "fail", "policy_sha256": "old"}]
    again = {"kind": "evaluated", "verdict": "fail", "policy_sha256": "old"}
    new = [{"kind": "train_registered", "run": "new"},
           {"kind": "train_ended", "run": "new", "state": "finished", "policy_sha256": "new"},
           {"kind": "evaluated", "verdict": "fail", "policy_sha256": "new"}]
    _ledger(tmp_path, *earlier)
    before = rounds.standing(tmp_path)["runs_ended"]
    assert before == 1
    _ledger(tmp_path, *earlier, again, again, *new)
    state = rounds.standing(tmp_path, before)
    assert state["evaluations"] == 4 and state["settled_this_session"] == 1
    assert not rounds.over(state, 2)
    newer = [{**row, "policy_sha256": "newer"} for row in new]
    _ledger(tmp_path, *earlier, again, again, *new, *newer)
    assert rounds.over(rounds.standing(tmp_path, before), 2)


def test_a_transcript_reads_back_as_tool_calls_with_how_long_each_blocked(
        tmp_path: Path) -> None:
    rounds = _load("rounds")
    frames = [
        {"t": 10.0, "type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "a", "name": "mcp__cadex__train_status",
             "input": {"run": "r1", "wait_s": 600}}]}},
        {"t": 312.5, "type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "a", "content": "finished"}]}},
        {"t": 320.0, "type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "b", "name": "mcp__cadex__evaluate", "input": {}}]}},
        {"t": 395.0, "type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "b", "is_error": True, "content": "no"}]}},
        {"t": 396.0, "type": "result", "result": "done"},
    ]
    turn = tmp_path / "out" / "turn-1"
    turn.mkdir(parents=True)
    (turn / "transcript.jsonl").write_text(
        "".join(json.dumps(frame) + "\n" for frame in frames), encoding="utf-8")
    calls = rounds.tool_calls(turn / "transcript.jsonl")
    assert [(c["tool"], c["seconds"], c["is_error"]) for c in calls] == [
        ("train_status", 302.5, False), ("evaluate", 75.0, True)]

    project = tmp_path / "project"
    project.mkdir()
    summary = rounds.summarise(project, tmp_path / "out")
    assert summary["turns"][0]["by_tool"]["train_status"] == {
        "calls": 1, "errors": 0, "longest_s": 302.5}
    assert summary["project"] == "project" and summary["ledger"] == []


def test_a_session_may_name_its_own_continuation(tmp_path: Path, monkeypatch) -> None:
    rounds = _load("rounds")
    first, later = tmp_path / "first.txt", tmp_path / "later.txt"
    first.write_text("first", encoding="utf-8")
    later.write_text("later", encoding="utf-8")
    project, out = tmp_path / "project", tmp_path / "out"
    project.mkdir()
    seen: list[tuple[str, bool]] = []
    monkeypatch.setattr(rounds, "turn", lambda project, folder, prompt, *, resume:
                        seen.append((prompt.name, resume)) or 0)
    monkeypatch.setattr(rounds.sys, "argv", [
        "rounds.py", "--project", str(project), "--prompt", str(first), "--out", str(out),
        "--continue-prompt", str(later), "--max-turns", "2"])
    assert rounds.main() == 0
    assert seen == [("first.txt", False), ("later.txt", True)]
    registration = json.loads((out / "registration.json").read_text(encoding="utf-8"))
    assert registration["continue_prompt"] == {
        "file": "later.txt", "sha256": hashlib.sha256(b"later").hexdigest()}


def test_the_runner_names_no_behaviour_and_pins_the_model() -> None:
    source = (RUNNER / "rounds.py").read_text(encoding="utf-8")
    assert '"claude-opus-5-5"' in source and '"fallback": None' in source
    for word in ("walk", "gait", "foot", "reach", "balanc", "shove", "quadruped", "robin"):
        assert not re.search(word, source, re.IGNORECASE), word


def test_the_block_probe_serves_one_tool_that_waits(monkeypatch) -> None:
    probe = _load("block_probe")
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "block", "arguments": {"seconds": 0.05}}},
    ]
    out = io.StringIO()
    monkeypatch.setattr(probe.sys, "stdin",
                        io.StringIO("".join(json.dumps(r) + "\n" for r in requests)))
    monkeypatch.setattr(probe.sys, "stdout", out)
    assert probe.serve() == 0
    replies = [json.loads(line) for line in out.getvalue().splitlines()]
    assert [reply["id"] for reply in replies] == [1, 2, 3]
    assert [tool["name"] for tool in replies[1]["result"]["tools"]] == ["block"]
    assert replies[2]["result"]["content"][0]["text"].startswith("blocked 0.")


def test_the_retained_rounds_receipts_name_the_prompts_on_disk() -> None:
    receipts = sorted(RETAINED.glob("p4-*-registration.json"))
    assert receipts, "no P4 rounds session is retained"
    for path in receipts:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        assert receipt["model"] == "claude-opus-5-5" and receipt["fallback"] is None
        assert receipt["project"].startswith("ot11-")
        for key in ("first_prompt", "continue_prompt"):
            prompt = PROBE / "prompts" / receipt[key]["file"]
            assert hashlib.sha256(prompt.read_bytes()).hexdigest() == receipt[key]["sha256"]
        assert "/home/" not in path.read_text(encoding="utf-8")


def test_the_goal_drawer_names_no_behaviour() -> None:
    source = (RUNNER / "goals.py").read_text(encoding="utf-8")
    for word in ("walk", "gait", "foot", "reach", "balanc", "shove", "heron", "robin", "arm"):
        assert not re.search(rf"\b{word}", source, re.IGNORECASE), word


def test_the_reach_prompt_hands_over_the_frozen_reach_contract() -> None:
    contract = json.loads((PROBE / "contract.json").read_text(encoding="utf-8"))
    reach = contract["behaviours"]["reach"]
    prompt = (PROBE / "prompts" / "reach.loop.prompt.txt").read_text(encoding="utf-8")
    bounds = {p["id"]: p.get("max", p.get("max_s")) for p in reach["predicates"] if "id" in p}
    for identifier, metric in (("Q2", "final_error_arm_lengths_max"),
                               ("Q3", "time_to_target_s_max"), ("Q4", "overshoot_ratio_max")):
        assert f'{{"id": "{identifier}", "metric": "{metric}", "max": ' in prompt
        written = re.search(rf'"id": "{identifier}", "metric": "{metric}", "max": ([0-9.]+)',
                            prompt).group(1)
        assert float(written) == bounds[identifier], identifier
    assert '{"id": "Q1", "metric": "completed", "min": 1}' in prompt
    assert f"seeds={contract['evaluation_seeds']}" in prompt
    assert f"episode_seconds={reach['episode_seconds']}" in prompt
    assert f"resample_seconds={reach['conditions']['goal']['switch_at_s']}" in prompt
    assert "joint_fraction=0.8, min_z_mm=0.10 * ARM_MM" in prompt
    assert "min_separation_mm=0.25 * ARM_MM" in prompt
    assert "randomisation=[], reset_variation=[], disturbance=[]" in prompt


def test_the_held_out_reach_targets_were_drawn_by_the_contract_rules() -> None:
    receipt = json.loads((RETAINED / "r2-heron-1-targets.json").read_text(encoding="utf-8"))
    prompt = (PROBE / "prompts" / "reach.loop.prompt.txt").read_text(encoding="utf-8")
    end = 'label="ot11 reach contract",\n)'
    block = prompt[prompt.index("ARM_MM = "):prompt.index(end) + len(end)]
    assert hashlib.sha256(block.encode()).hexdigest() == receipt["spec_block"]["sha256"]
    assert f"ARM_MM = {receipt['arm_length_mm']}" in block
    contract = json.loads((PROBE / "contract.json").read_text(encoding="utf-8"))
    assert [row["seed"] for row in receipt["targets"]] == contract["evaluation_seeds"]
    arm = receipt["arm_length_mm"]
    for row in receipt["targets"]:
        a, b = row["target_a_mm"], row["target_b_mm"]
        assert min(a[2], b[2]) >= 0.10 * arm
        assert math.dist(a, receipt["tip_start_mm"]) >= 0.25 * arm
        assert math.dist(a, b) >= 0.25 * arm
    assert "/home/" not in json.dumps(receipt)
