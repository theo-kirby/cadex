# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The ot7 closing report (ADR-397).

F10 asks for one row per design — prompts, turns, continuations used, fit
failures per turn, final static and swept checks, smoke result and the ot6
comparison — plus the evidence for F1–F9, every call that was not an attempt,
and what remains open, "claiming nothing a record does not carry". This test
is the shape of that: every relative link resolves to a committed file, every
record slug it cites exists in the record graph, every ADR it names exists in
the log, every prompt digest it prints matches the frozen prompt, and the
per-design and non-attempt tables are complete.
"""

from __future__ import annotations

import hashlib
import re
import socket
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPORT = REPO / "docs/probes/ot7/REPORT.md"
RECORDS = REPO / ".hypergraph/graph/record"
PROMPTS = REPO / "docs/probes/ot7/prompts"
PRIVATE_ADDRESS = re.compile(r"\b(?:10|100|172|192)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
SECTIONS = (
    "## One row per design",
    "## Every call that was not an attempt",
    "## Implemented checks and evidence for F1–F9",
    "## F10: what this run established, and what remains open",
)
DESIGNS = (
    ("Heron repair / F4", "repair.prompt.txt", 4, 3),
    ("Heron arm / F5", "heron.create.prompt.txt", 4, 3),
    ("Robin balancer / F6", "robin.create.prompt.txt", 4, 3),
    ("Plover biped / F7", "plover.create.prompt.txt", 2, 1),
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


def test_one_row_per_design_carries_every_column_f10_asks_for():
    """Prompts, turns, continuations used, fit failures per turn, final static
    and swept checks, smoke and the ot6 comparison, for all four designs."""

    text = _text()
    header = _row(text, "Design / criterion")
    assert header[1].startswith("Prompts") and header[2] == "Turns"
    assert header[3].startswith("Continuations") and header[4].startswith("Static fit per turn")
    assert header[5] == "Final static" and header[6] == "Final swept"
    assert header[7] == "Smoke" and header[8] == "Inventory"
    assert header[9] == "Actor edits" and header[10].startswith("ot6 comparison")
    for label, prompt, turns, continuations in DESIGNS:
        row = _row(text, label)
        assert len(row) == len(header), label
        digest = hashlib.sha256((PROMPTS / prompt).read_bytes()).hexdigest()
        assert prompt in row[1] and digest[:8] in row[1], label
        assert row[2].startswith(str(turns)), label
        assert re.match(rf"^\*?\*?{continuations} of 3", row[3]), label
        assert "→" in row[4] and "of" in row[4], label
        assert row[5].startswith("**pass, 0 of "), label
        assert row[9] == "**0**", f"{label}: the run's rule is zero actor edits"
        assert row[10], label
    # Every design ends at zero failing static checks; only F4 is exempt from
    # a smoke, and exactly one design's smoke failed.
    smokes = [_row(text, label)[7] for label, *_ in DESIGNS]
    assert sum(s.startswith("**pass**") for s in smokes) == 2
    assert sum(s.startswith("**fail**") for s in smokes) == 1
    assert sum("not required" in s for s in smokes) == 1


def test_every_call_that_was_not_an_attempt_is_listed_with_its_receipt():
    text = _text()
    block = text.split("## Every call that was not an attempt", 1)[1].split("\n## ", 1)[0]
    rows = re.findall(r"^\| (\d+) \| (F\d) \| `([^`]+)` \| (\w+) \| .+ \| \[receipt\]\(([^)]+)\) \|$",
                      block, re.M)
    assert [int(n) for n, *_ in rows] == list(range(1, 15)), "the list is numbered 1..14"
    assert {kind for *_, kind, _ in rows} == {"void", "interrupted", "unreached"}
    for _n, _criterion, _project, _kind, receipt in rows:
        assert (REPORT.parent / receipt).is_file(), receipt
    # Every criterion that had one is represented, and no slot was spent.
    assert {c for _, c, *_ in rows} == {"F4", "F5", "F6", "F7"}
    assert "None spent a slot" in block


def test_the_f1_to_f9_table_has_a_row_per_criterion():
    text = _text()
    block = text.split("## Implemented checks and evidence for F1–F9", 1)[1].split("\n## ", 1)[0]
    for n in range(1, 10):
        assert re.search(rf"^\| F{n} \| ", block, re.M), f"F{n} has no evidence row"


def test_what_remains_open_names_the_unfinished_work():
    text = _text()
    block = text.split("## F10: what this run established", 1)[1]
    assert "**What remains open**" in block
    for item in ("unspent continuations", "uncatalogued servos and horns",
                 "needs a controller", "discrete", "unexecuted evidence"):
        assert item in block, item
    assert "**Done is claimed here**" in block


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
    assert len(slugs) >= 15
    for slug in slugs:
        assert (RECORDS / f"{slug}.md").is_file(), slug
    decisions = (REPO / "docs/DECISIONS.md").read_text()
    adrs = set(re.findall(r"ADR-(\d{3})", text))
    assert {"341", "355", "356", "386", "390", "393", "395", "396"} <= adrs
    for adr in adrs:
        assert f"## ADR-{adr} " in decisions, adr
