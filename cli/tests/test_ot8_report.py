# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The ot8 closing report (G6).

G6 asks for one row per experiment — prompts, turns, model, accepted
identities, static and swept fit, inventory, smoke, before/after comparisons
and remaining defects — with the G1–G5 evidence linked, every call that was
not an attempt listed, and achieved success bars kept separate from the
control-blocked outcome. This test is the shape of that, and it is the sibling
of `test_ot7_report.py`: every relative link resolves to a committed file,
every record slug it cites exists in the record graph, every ADR it names
exists in the log, every prompt digest it prints matches the frozen prompt,
and the per-experiment, slot-ledger, non-attempt and evidence tables are
complete.

The one assertion that is not about shape is the one the run turns on: a
finished experiment is not a design success, so exactly two rows may read as a
success and the balancer's row may not.
"""

from __future__ import annotations

import hashlib
import re
import socket
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPORT = REPO / "docs/probes/ot8/REPORT.md"
RECORDS = REPO / ".hypergraph/graph/record"
PROMPTS = REPO / "docs/probes/ot8/prompts"
PRIVATE_ADDRESS = re.compile(r"\b(?:10|100|172|192)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
SECTIONS = (
    "## Achieved success bars, and the outcome that is not one",
    "## One row per experiment",
    "## The slot ledger",
    "## Every call that was not an attempt",
    "## Implemented checks and evidence for G1–G5",
    "## G6: what this run established, and what remains open",
)
# label, frozen first prompt, turns that reached the model, continuations used
DESIGNS = (
    ("Heron arm / G2", "heron.create.prompt.txt", 1, 0),
    ("Plover biped / G3", "rebuild.prompt.txt", 1, 0),
    ("Robin balancer / G4", "resolve.prompt.txt", 0, 0),
)


def _text() -> str:
    return REPORT.read_text()


def _row(text: str, label: str) -> list[str]:
    for line in text.splitlines():
        if line.startswith(f"| **{label}**") or line.startswith(f"| {label} |"):
            return [c.strip() for c in line.strip("|").split("|")]
    raise AssertionError(f"no table row for {label!r}")


def test_the_report_has_its_sections_and_a_verified_date():
    text = _text()
    assert re.search(r"^Verified against source: \d{4}-\d{2}-\d{2}\.", text, re.M)
    for section in SECTIONS:
        assert section in text, f"missing section {section!r}"
    assert not PRIVATE_ADDRESS.search(text)
    assert socket.gethostname() not in text


def test_one_row_per_experiment_carries_every_column_g6_asks_for():
    """Prompts, turns, model, accepted identity, fit, inventory, smoke, the
    before/after comparison and the remaining defects, for all three."""

    text = _text()
    header = _row(text, "Design / criterion")
    assert header[1] == "Outcome" and header[2].startswith("Prompts")
    assert header[3] == "Turns" and header[4] == "Model"
    assert header[5].startswith("Continuations") and header[6].startswith("Accepted identity")
    assert header[7].startswith("Static fit per turn")
    assert header[8] == "Final static" and header[9] == "Final swept"
    assert header[10] == "Smoke" and header[11] == "Inventory"
    assert header[12] == "Actor edits" and header[13].startswith("Remaining defects")
    assert header[14].startswith("ot7 comparison")
    for label, prompt, turns, continuations in DESIGNS:
        row = _row(text, label)
        assert len(row) == len(header), label
        digest = hashlib.sha256((PROMPTS / prompt).read_bytes()).hexdigest()
        assert prompt in row[2] and digest[:8] in row[2], label
        assert re.match(rf"^\*?\*?{turns}\*?\*?,", row[3]), label
        assert "claude-opus-5" in row[4], label
        assert re.match(rf"^\*\*{continuations} of 3\*\*$", row[5]), label
        assert row[6], label
        assert row[8].startswith("**pass, 0 of "), label
        assert row[9].startswith("**pass**"), label
        assert row[12] == "**0**", f"{label}: the run's rule is zero actor design edits"
        assert row[13] and row[14], label


def test_a_finished_experiment_is_not_a_design_success():
    """Two bars were met and one experiment is control-blocked; the report may
    never let the third read as a design success."""

    text = _text()
    outcomes = [_row(text, label)[1] for label, *_ in DESIGNS]
    assert sum(o.startswith("**success") for o in outcomes) == 2, outcomes
    blocked = _row(text, "Robin balancer / G4")
    assert blocked[1] == "**control-blocked — not a design success**"
    assert blocked[10].startswith("**fail**"), "the balancer's smoke still fails"
    smokes = [_row(text, label)[10] for label, *_ in DESIGNS]
    assert sum(s.startswith("**pass**") for s in smokes) == 2
    assert sum(s.startswith("**fail**") for s in smokes) == 1
    assert "**A finished experiment is not a design success.**" in text


def test_the_arms_remaining_defects_are_stated_against_ot7s_four_modified_parts():
    row = _row(_text(), "Heron arm / G2")
    assert "none against the bar" in row[13]
    assert "two modified servos and two modified horns" in row[13]
    assert "no `servo` row and no `servo_horn` row at all" in row[14]
    assert "servo/mg90s" in row[11] and "servo_horn/mg90s-single_arm" in row[11]


def test_the_slot_ledger_says_what_each_experiment_spent():
    text = _text()
    block = text.split("## The slot ledger", 1)[1].split("\n## ", 1)[0]
    assert _row(block, "G2")[3].startswith("1 —")
    assert "ADR-355" in _row(block, "G2")[4], "G2's void call is named as void"
    assert _row(block, "G3")[3].startswith("1 —")
    assert _row(block, "G4")[2] == "**0**", "G4 dispatched nothing"
    assert _row(block, "G4")[3].startswith("0 — nothing was dispatched")
    total = _row(block, "total")
    assert total[2] == "**3**" and total[3] == "**2**" and total[4] == "**1**"
    assert total[5] == "**0**" and total[6] == "**0**"
    for row in (_row(block, label) for label in ("G2", "G3", "G4")):
        assert row[7] == "**0**" and row[8] == "**3**"


def test_every_call_that_was_not_an_attempt_is_listed_with_its_receipt():
    text = _text()
    block = text.split("## Every call that was not an attempt", 1)[1].split("\n## ", 1)[0]
    rows = re.findall(r"^\| (\d+) \| (G\d) \| `([^`]+)` \| (\w+) \| .+ \| \[receipt\]\(([^)]+)\) \|$",
                      block, re.M)
    assert [int(n) for n, *_ in rows] == [1], "the list is numbered 1..1"
    assert {kind for *_, kind, _ in rows} == {"void"}
    for _n, _criterion, _project, _kind, receipt in rows:
        assert (REPORT.parent / receipt).is_file(), receipt
    assert "None spent a slot" in block


def test_the_g1_to_g5_table_has_a_row_per_criterion():
    text = _text()
    block = text.split("## Implemented checks and evidence for G1–G5", 1)[1].split("\n## ", 1)[0]
    for n in range(1, 6):
        assert re.search(rf"^\| G{n} \| ", block, re.M), f"G{n} has no evidence row"
        assert re.search(rf"^\| G{n} \| .*\]\(", block, re.M), f"G{n} links no evidence"


def test_what_remains_open_names_the_unfinished_work():
    text = _text()
    block = text.split("## G6: what this run established", 1)[1]
    assert "**What remains open.**" in block
    for item in ("unspent continuations", "The balancer still falls",
                 "needs a controller", "standing wheel compression",
                 "ot7's own open items"):
        assert item in block, item
    assert "**Done is claimed here**" in block


def test_ot8_is_distinguished_from_ot7_and_the_seeds_stayed_read_only():
    text = _text()
    assert "**ot8 is not ot7 and does not re-run it.**" in text
    assert "../ot7/REPORT.md" in text
    assert "comparison only" in text
    assert "hashed before and after" in text


def test_every_link_record_and_adr_the_report_cites_exists():
    text = _text()
    for link in re.findall(r"\]\(([^)#][^)]*)\)", text):
        target = (REPORT.parent / link.split("#")[0]).resolve()
        assert target.is_file() or target.is_dir(), link
    headings = {re.sub(r"[^a-z0-9 -]", "", h.lower()).replace(" ", "-")
                for h in re.findall(r"^#{2,3} (.+)$", text, re.M)}
    for anchor in re.findall(r"\]\(#([^)]+)\)", text):
        assert anchor in headings, anchor
    slugs = set(re.findall(r"record/([a-z]+-[a-z]+-\d{4})\.md", text))
    assert len(slugs) >= 6
    for slug in slugs:
        assert (RECORDS / f"{slug}.md").is_file(), slug
    decisions = (REPO / "docs/DECISIONS.md").read_text()
    adrs = set(re.findall(r"ADR-(\d{3})", text))
    assert {"355", "392", "395", "398", "399", "400", "401", "402"} <= adrs
    for adr in adrs:
        assert f"## ADR-{adr} " in decisions, adr


def test_the_report_prints_the_measured_regression_floor():
    text = _text()
    block = text.split("## G5: the regression floor, measured", 1)[1].split("\n## ", 1)[0]
    for number in ("2,196 passed, 53 skipped, 0 failed",
                   "903 passed, 1 skipped, 0 failed",
                   "23 passed, 0 skipped", "11 passed, 0 skipped"):
        assert number in block, number
    assert "ADR-398 repeated-restore retention" in block
    assert "**Every measured difference is explained**" in block
