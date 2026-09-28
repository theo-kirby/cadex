# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ot10's closing report (C1) is held equal to its receipts.

``docs/probes/ot10/REPORT.md`` summarises every A5 attempt in one table.
Each row's judged medians and total must equal that attempt's committed
``*-score.json``. Its proxies and fit gates must equal the attempt's own
section of the probe log, ``README.md``. Its verdict must follow from the
frozen bar in ``contract.json``, never be written by hand. Every image the
report links must be committed, and each must be 300 KB or less.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OT10 = REPO / "docs/probes/ot10"
REPORT = (OT10 / "REPORT.md").read_text(encoding="utf-8")
README = (OT10 / "README.md").read_text(encoding="utf-8")
CONTRACT = json.loads((OT10 / "contract.json").read_text(encoding="utf-8"))
TRAITS = CONTRACT["traits"]
COLUMNS = ["project", "status", *TRAITS, "total", "P1", "P2", "P3",
           "static", "swept", "electronics", "verdict"]


def _rows():
    table = REPORT.split("<!-- attempts:start -->")[1].split("<!-- attempts:end -->")[0]
    lines = [line for line in table.strip().splitlines() if line.startswith("| `")]
    rows = {}
    for line in lines:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        row = dict(zip(COLUMNS, cells, strict=True))
        rows[row["project"].strip("`")] = row
    return rows


ROWS = _rows()


def _score_file(project):
    name = CONTRACT["baseline"]["score_file"] if project == "hex3" else f"{project}-score.json"
    return json.loads((OT10 / name).read_text(encoding="utf-8"))


def _section(project):
    """The probe log's own section for one attempt."""
    parts = re.split(r"^## ", README, flags=re.M)
    [section] = [p for p in parts if p.startswith("A5 attempt") and f"(`{project}`)" in p.splitlines()[0]]
    return section


def _gate(section, label):
    """The first number, and the yes/no verdict cell, of a row in a section's gate table."""
    [line] = [l for l in section.splitlines() if l.startswith(f"| {label} ")]
    cells = [c.strip() for c in line.strip("|").split("|")]
    number = re.search(r"\d+(?:\.\d+)?", cells[1].replace(",", "")).group()
    return number, cells[-1].replace("*", "").split(",")[-1].strip()


def test_every_scored_design_has_one_row_and_nothing_else_does():
    scored = {p.name.removesuffix("-score.json") for p in OT10.glob("ot10-*-score.json")}
    assert set(ROWS) == scored | {"hex3"}
    assert len(scored) == 12


def test_each_rows_scores_equal_its_score_file():
    for project, row in ROWS.items():
        score = _score_file(project)
        assert score["rubric_sha256"] == CONTRACT["rubric_sha256"], project
        assert [int(row[t]) for t in TRAITS] == [score["medians"][t] for t in TRAITS], project
        assert int(row["total"]) == score["total"] == sum(score["medians"].values()), project
    assert ROWS["hex3"]["total"] == str(CONTRACT["baseline"]["total"])


def test_each_rows_proxies_and_gates_equal_the_probe_log():
    for project, row in ROWS.items():
        if project == "hex3":
            continue
        section = _section(project)
        for label, proxy in (("P1 ≤ 0.20", "P1"), ("P2 ≤ 0.25", "P2"), ("P3 2 or 3", "P3")):
            number, _ = _gate(section, label)
            assert float(number) == float(row[proxy]), (project, proxy)
        for label, gate in (("static fit", "static"), ("swept fit", "swept"),
                            ("electronics", "electronics")):
            assert _gate(section, label)[1] == row[gate], (project, gate)
    # hex3's proxies were measured after its baseline score (ADR-414, ADR-424).
    assert "**0.373** (76,170 of 204,356 subsamples)" in README
    assert "**0.189** (3,181 of 16,856 mm" in README
    assert (ROWS["hex3"]["P1"], ROWS["hex3"]["P2"], ROWS["hex3"]["P3"]) == ("0.373", "0.189", "2")


def test_each_verdict_follows_from_the_frozen_bar():
    bar, proxies = CONTRACT["bar"], CONTRACT["proxies"]
    baseline = CONTRACT["baseline"]["total"]
    for project, row in ROWS.items():
        if project == "hex3":
            continue
        misses = []
        if int(row["total"]) < bar["total_min"] or int(row["total"]) <= baseline:
            misses.append("total")
        misses += [t for t in TRAITS if int(row[t]) < bar["trait_min"]]
        if float(row["P1"]) > proxies["P1"]["max"]:
            misses.append("P1")
        if float(row["P2"]) > proxies["P2"]["max"]:
            misses.append("P2")
        if not proxies["P3"]["min"] <= int(row["P3"]) <= proxies["P3"]["max"]:
            misses.append("P3")
        misses += [gate for gate in ("static", "swept", "electronics") if row[gate] != "yes"]
        if misses:
            assert row["verdict"] == "misses: " + ", ".join(misses), project
            assert row["status"] == "failed", project
        else:
            assert row["verdict"] == "**meets the bar**", project
            assert row["status"] == "counted", project
    counted = {p for p, r in ROWS.items() if r["status"] == "counted"}
    assert counted == {"ot10-biped-1", "ot10-quadruped-3", "ot10-hexapod-10"}


def test_the_report_names_the_census_and_the_walk_verdicts():
    census = json.loads((OT10 / "refusals.json").read_text(encoding="utf-8"))
    assert "0 of 183 refused calls" in REPORT and "all 14 ot10 transcripts" in REPORT
    assert len(census["projects"]) == 14
    assert sum(p["refused"] for p in census["projects"].values()) == 183
    assert "| `w2-1` | cold |" in REPORT and "`walked = false` |" in REPORT
    assert "**`walked = true`** |" in REPORT
    assert "`w2-2` | `84ff4c98adabb6e5` | `7a4e8c233214341e`" in README


def test_every_linked_image_is_committed_and_small():
    links = set(re.findall(r"\]\(([\w.-]+\.png)\)", REPORT))
    assert len(links) >= 12
    for name in links:
        path = OT10 / name
        assert path.is_file(), name
        assert path.stat().st_size <= 300 * 1024, name
