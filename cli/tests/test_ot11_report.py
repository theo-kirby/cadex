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

import importlib.util
import json
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
    assert len(rows) == len(RUNS["runs"]) == 14
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
