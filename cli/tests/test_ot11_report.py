# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ot11 C1: the closing report's tables are their receipts.

``docs/probes/ot11/REPORT.md`` lists every ot11 training run with its
settings, budget and GPU time. ``runner/run_ledger.py`` collects those from
each project's run registrations and supervisor statuses into
``retained/ot11-runs.json``; the page's table must be that receipt, row for
row, so a number on the page cannot drift from the one the run wrote.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROBE = REPO / "docs" / "probes" / "ot11"
REPORT = (PROBE / "REPORT.md").read_text(encoding="utf-8")
RUNS = json.loads((PROBE / "retained" / "ot11-runs.json").read_text(encoding="utf-8"))
BEHAVIOUR = {"ot11-robin-1": "balance", "ot11-heron-1": "reach", "ot11-quad-1": "walk"}


def _load_ledger():
    spec = importlib.util.spec_from_file_location("run_ledger", PROBE / "runner" / "run_ledger.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _table(heading: str) -> list[list[str]]:
    """The first table under ``heading``, header and rule dropped."""

    section = REPORT.split(heading, 1)[1]
    rows = []
    for line in section.splitlines():
        if line.startswith("|"):
            rows.append(_cells(line))
        elif rows:
            break
    return rows[2:]


def _number(cell: str) -> float:
    return float(cell.replace(",", "").replace("*", ""))


def test_run_table_is_the_receipt():
    rows = _table("## Every training run")
    assert len(rows) == len(RUNS["runs"]) == 22
    for index, (row, run) in enumerate(zip(rows, RUNS["runs"]), 1):
        warm = run["init_from"].split("/")[1] if run["init_from"] else None
        assert row[0] == str(index)
        assert row[1] == BEHAVIOUR[run["project"]]
        assert row[2] == f"`{run['project']}`"
        assert row[3] == f"`{run['run']}`"
        assert row[4] == str(run["seed"])
        assert row[5] == f"{run['iterations']} it × {run['envs']} envs"
        assert row[6] == (f"`{warm}`" if warm else "—")
        assert _number(row[7]) == run["budget_s"]
        assert row[8] == f"`{run['state']}`"
        assert row[9] == str(run["iterations_run"])
        assert row[10] == f"{run['supervised_s']:,.2f}"
        assert row[11] == ("—" if run["trainer_s"] is None else f"{run['trainer_s']:,.1f}")


def test_totals_add_up():
    totals: dict[str, list[float]] = {}
    for run in RUNS["runs"]:
        totals.setdefault(BEHAVIOUR[run["project"]], []).append(run["supervised_s"])
    # This table's first line is its header, so the rule and the rows follow it.
    lines = REPORT.split("| behaviour | runs | GPU time, s |", 1)[1].splitlines()[2:]
    rows = {}
    for line in lines:
        if not line.startswith("|"):
            break
        cells = [cell.strip("*") for cell in _cells(line)]
        rows[cells[0]] = cells
    assert set(rows) == {*totals, "all"}
    for behaviour, times in totals.items():
        assert int(rows[behaviour][1]) == len(times)
        assert rows[behaviour][2] == f"{round(sum(times), 2):,.2f}"
    assert int(rows["all"][1]) == len(RUNS["runs"])
    assert _number(rows["all"][2]) == RUNS["supervised_s_total"]
    assert RUNS["supervised_s_total"] == round(sum(r["supervised_s"] for r in RUNS["runs"]), 2)


def test_receipt_and_page_carry_no_machine_path():
    text = (PROBE / "retained" / "ot11-runs.json").read_text(encoding="utf-8")
    for body in (text, REPORT):
        assert not re.search(r"/home/|/Users/|[A-Z]:\\\\", body)


def test_collector_reads_only_registration_and_status(tmp_path, monkeypatch):
    ledger = _load_ledger()
    project = tmp_path / "ot11-demo"
    for name, start, status in (
        ("b-second", 20.0, {"state": "budget_exhausted", "iterations_run": 3, "wall_time_s": 9.5}),
        ("a-first", 10.0, {"state": "finished", "iterations_run": 4, "wall_time_s": 8.25,
                           "receipt": {"wall_time_s": 7.0}, "policy": {"sha256": "ab" * 32}}),
    ):
        run = project / "runs" / name
        run.mkdir(parents=True)
        settings = {"seed": 5, "envs": 8, "iterations": 4}
        if name == "b-second":
            settings["init_from"] = str(project / "runs" / "a-first" / "train" / "t.cxpolicy")
        (run / "registration.json").write_text(json.dumps(
            {"run": name, "settings": settings, "budget_s": 12.0, "task_sha256": "cd" * 32}))
        (run / "training-status.json").write_text(json.dumps({"started_at": start, **status}))
    (project / "runs" / "w2-copied").mkdir()  # an inherited run with no registration is not ot11's
    out = tmp_path / "runs.json"
    monkeypatch.setattr(sys, "argv", ["run_ledger.py", "--out", str(out), str(project)])
    assert ledger.main() == 0
    receipt = json.loads(out.read_text())
    assert [row["run"] for row in receipt["runs"]] == ["a-first", "b-second"]
    first, second = receipt["runs"]
    assert (first["trainer_s"], first["policy_sha256"]) == (7.0, "ab" * 32)
    assert (second["trainer_s"], second["policy_sha256"]) == (None, None)
    assert second["init_from"] == "runs/a-first/train/t.cxpolicy"
    assert receipt["supervised_s_total"] == 17.75
    assert str(tmp_path) not in out.read_text()


def test_a_refused_start_is_no_attempt_and_a_live_run_is_not_counted(tmp_path, monkeypatch):
    """A trainer that exits before its first iteration was refused, not tried;
    a run whose supervisor has not ended has no time to report yet."""

    ledger = _load_ledger()
    project = tmp_path / "ot11-demo"
    for name, start, status in (
        ("a-first", 10.0, {"state": "finished", "iterations_run": 4, "wall_time_s": 8.25}),
        ("b-refused", 20.0, {"state": "failed", "iterations_run": 0, "wall_time_s": 1.5}),
        ("c-collapsed", 30.0, {"state": "collapsed", "iterations_run": 2, "wall_time_s": 3.0}),
        ("d-live", 40.0, {"state": "running"}),
    ):
        run = project / "runs" / name
        run.mkdir(parents=True)
        (run / "registration.json").write_text(json.dumps(
            {"run": name, "settings": {"seed": 5, "envs": 8, "iterations": 4}, "budget_s": 12.0}))
        (run / "training-status.json").write_text(json.dumps({"started_at": start, **status}))
    out = tmp_path / "runs.json"
    monkeypatch.setattr(sys, "argv", ["run_ledger.py", "--out", str(out), str(project)])
    assert ledger.main() == 0
    receipt = json.loads(out.read_text())
    assert [(row["run"], row["attempt"]) for row in receipt["runs"]] == [
        ("a-first", True), ("b-refused", False), ("c-collapsed", True)]
    assert receipt["attempts"] == 2
    assert receipt["in_progress"] == [{"project": "ot11-demo", "run": "d-live", "started_at": 40.0}]
    assert receipt["supervised_s_total"] == 12.75
    assert str(tmp_path) not in out.read_text()


EVALS = json.loads((PROBE / "retained" / "ot11-evaluations.json").read_text(encoding="utf-8"))
BEHAVIOUR_ALL = {**BEHAVIOUR, "ot11-w2-negative": "walk", "ot11-robin-negative": "balance"}
ORIGIN = {"ot11-w2-negative": "ot10 `w2-2`", "ot11-robin-negative": "ot9 `r3-ppo-1`"}


def _load_eval_ledger():
    spec = importlib.util.spec_from_file_location("eval_ledger", PROBE / "runner" / "eval_ledger.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_evaluation_table_is_the_receipt():
    rows = _table("## Every evaluation")
    assert len(rows) == len(EVALS["evaluations"]) == 28
    for index, (row, ev) in enumerate(zip(rows, EVALS["evaluations"]), 1):
        failing = ", ".join(f"{k} {v}" for k, v in ev["failing_predicates"].items()) or "—"
        assert row == [
            str(index),
            BEHAVIOUR_ALL[ev["project"]],
            f"`{ev['project']}`",
            f"`{ev['key']}`",
            f"`{ev['trained_by']}`" if ev["trained_by"] else ORIGIN[ev["project"]],
            ev["verdict"],
            f"{ev['passed']} of {ev['seeds']}",
            failing,
            ", ".join(f"{k} {v}" for k, v in ev["terminations"].items()),
            "yes" if ev["film"] == "ready" else "—",
        ]
        # A verdict is the pass rule over the seeds, and the failures add up.
        assert (ev["verdict"] == "pass") == (ev["passed"] == ev["seeds"])
        # A void seed has not passed, so it is counted among the failed too.
        assert ev["passed"] + ev["failed"] == ev["seeds"] and ev["void"] <= ev["failed"]
        # Every ot11 project's evaluated policy was trained by a registered run.
        assert (ev["trained_by"] is None) == (ev["project"] in ORIGIN)


def test_judge_table_is_the_receipt():
    rows = _table("## Every judge score")
    assert len(rows) == len(EVALS["judges"]) == 12
    for index, (row, judge) in enumerate(zip(rows, EVALS["judges"]), 1):
        m = judge["medians"]
        assert row == [
            str(index), f"`{judge['label']}`", judge["behaviour"], str(judge["seed"]),
            str(m["V1"]), str(m["V2"]), str(m["V3"]), str(m["V4"]), str(judge["total"]),
            "yes" if judge["meets_bar"] else "no", judge["verdict"],
        ]
        assert (judge["model"], judge["calls"]) == ("claude-opus-5-5", 3)
        bar = judge["bar"]
        meets = judge["total"] >= bar["total_min"] and min(m.values()) >= bar["trait_min"]
        assert judge["meets_bar"] == meets
        assert judge["total"] == sum(m.values())
        assert judge["evaluations"], "every judge score names the stored evaluation it judged"
        # The page's claim: judge and spec agree on every judged seed.
        assert judge["meets_bar"] == (judge["verdict"] == "pass")


def test_revisions_cite_the_evaluation_that_answered_them():
    rows = _table("## Every revision the agent made, and why")
    runs = {(run["run"]) for run in RUNS["runs"]}
    evaluations = EVALS["evaluations"]
    assert len(rows) == 21
    for row in rows:
        run = row[0].strip("`")
        assert run in runs
        ev = evaluations[int(row[3]) - 1]
        assert ev["trained_by"].split()[0] == run
        assert int(row[4]) == ev["passed"]


def test_failure_counts_are_the_receipts():
    section = REPORT.split("## Every failure", 1)[1]
    evaluations = EVALS["evaluations"]
    failed = [i for i, ev in enumerate(evaluations, 1) if ev["verdict"] == "fail"]
    passed = [i for i, ev in enumerate(evaluations, 1) if ev["verdict"] == "pass"]
    assert len(failed) == 24 and passed == [5, 6, 11, 12]
    assert "Twenty-four of 28 evaluations failed" in section
    assert "except 5, 6, 11\n  and 12" in section
    collapsed = [run["run"] for run in RUNS["runs"] if run["state"] == "collapsed"]
    assert collapsed == ["r1-clearance", "r7-relswing"]
    assert sum(run["state"] == "budget_exhausted" for run in RUNS["runs"]) == 7
    assert "Seven runs ended at their wall-clock budget" in section
    refused = [run["run"] for run in RUNS["runs"] if not run["attempt"]]
    assert refused == ["r9-steelfoot"] and RUNS["attempts"] == len(RUNS["runs"]) - 1 == 21
    assert "One start was refused, and is not an attempt" in section
    intro = REPORT.split("## Every training run", 1)[1].split("|", 1)[0]
    assert "Twenty-two runs" in intro and "twenty-one attempts" in intro


def test_evaluation_receipt_carries_no_machine_path():
    text = (PROBE / "retained" / "ot11-evaluations.json").read_text(encoding="utf-8")
    assert not re.search(r"/home/|/Users/|[A-Z]:\\\\", text)


def test_eval_collector_attributes_by_hash(tmp_path, monkeypatch):
    ledger = _load_eval_ledger()
    project = tmp_path / "ot11-demo"
    train = project / "runs" / "r1" / "train"
    train.mkdir(parents=True)
    (project / "runs" / "r1" / "registration.json").write_text("{}")
    (project / "runs" / "r1" / "training-status.json").write_text(json.dumps({"started_at": 5.0}))
    (train / "t.cxpolicy").write_bytes(b"final")
    (train / "t.000100.cxpolicy").write_bytes(b"ckpt")
    (train / "t.best.cxpolicy").write_bytes(b"ckpt")  # same bytes as it 100: the checkpoint wins
    unregistered = project / "runs" / "w2-copied" / "train"
    unregistered.mkdir(parents=True)
    (unregistered / "t.cxpolicy").write_bytes(b"inherited")

    def evaluation(key, policy, verdict, passed, written):
        folder = project / "evaluations" / key
        folder.mkdir(parents=True)
        path = folder / "evaluation.json"
        path.write_text(json.dumps({
            "label": "demo", "weights": "w.cxpolicy", "verdict": verdict,
            "policy_sha256": hashlib.sha256(policy).hexdigest(), "accepted_revision": key * 4,
            "summary": {"seeds": 2, "passed": [1] * passed, "failed": [2] * (2 - passed), "void": [],
                        "predicates": [{"id": "X1", "passed": passed}], "terminations": {"horizon": 2}},
        }))
        os.utime(path, (written, written))

    evaluation("bb", b"ckpt", "fail", 1, 200.0)
    evaluation("aa", b"final", "pass", 2, 300.0)
    evaluation("cc", b"inherited", "fail", 0, 100.0)
    judges = tmp_path / "retained"
    judges.mkdir()
    (judges / "judge-demo-seed-1.json").write_text(json.dumps({
        "label": "demo", "behaviour": "walk", "model": "m", "seed": 1, "calls": 3,
        "medians": {"V1": 3}, "total": 3, "bar": {}, "meets_bar": True,
        "evaluation": {"verdict": "pass", "accepted_revision": "aa" * 4,
                       "policy_sha256": hashlib.sha256(b"final").hexdigest()},
    }))
    out = tmp_path / "evals.json"
    monkeypatch.setattr(sys, "argv", ["eval_ledger.py", "--out", str(out), "--judges", str(judges), str(project)])
    assert ledger.main() == 0
    receipt = json.loads(out.read_text())
    rows = receipt["evaluations"]
    # The unattributed policy first (no run), then run r1's by write time.
    assert [(r["key"], r["trained_by"]) for r in rows] == [
        ("cc", None), ("bb", "r1 it 100"), ("aa", "r1 final")]
    assert rows[1]["failing_predicates"] == {"X1": 1}
    assert rows[2]["failing_predicates"] == {}
    assert receipt["judges"][0]["evaluations"] == ["ot11-demo/aa"]
    assert str(tmp_path) not in out.read_text()


def test_remaining_defects_cite_receipts_that_exist():
    section = REPORT.split("## Remaining defects", 1)[1]
    links = re.findall(r"\]\((retained/[^)]+)\)", section)
    assert len(links) >= 5
    for link in links:
        assert (PROBE / link).is_file(), link
    decisions = (REPO / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    for number in set(re.findall(r"ADR-(\d+)", section)):
        assert f"## ADR-{number} " in decisions, number
    walk = [ev for ev in json.loads(
        (PROBE / "retained" / "ot11-evaluations.json").read_text(encoding="utf-8"))["evaluations"]
        if ev["project"] == "ot11-quad-1"]
    if all(ev["passed"] == 0 for ev in walk):
        assert "**R1 is not met.**" in section


def test_the_margin_round_reads_its_w10_pass_as_the_margin():
    """Round 12's W10 pass rests on feet held above the floor, and the report says so."""

    receipt = json.loads((PROBE / "retained" / "p4-quad-1-r13-evaluation.json")
                         .read_text(encoding="utf-8"))
    assert receipt["evaluation"]["summary"]["pass"] is False
    w10 = next(p for p in receipt["evaluation"]["summary"]["predicates"] if p["id"] == "W10")
    assert w10["passed"] == 10
    rest = receipt["rest_height"]
    margin = rest["by_round"]["12 (r13-hovercost-margin)"]
    # Every foot's median settled height is above the stance threshold on every seed...
    assert all(foot["median_mm"][0] > rest["stance_mm"] for foot in margin.values())
    # ...where every foot that bore load in round 11 rested in the floor.
    assert max(rest["by_round"]["11 (r12-convex-sym)"][foot]["median_mm"][1]
               for foot in ("c_foot_fl", "c_foot_rr")) < 0.0
    section = REPORT.split("## Remaining defects", 1)[1]
    assert "**A foot contact margin moves what the gait predicates read.**" in section
    assert "The pass is not a fix." in section
