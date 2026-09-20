# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The ot8 prompt freeze (ADR-399, ADR-400).

Every prompt a design turn may see in run ot8 is committed under
``docs/probes/ot8/prompts/`` before the first design turn, with its digest in
the README table; the arm's create prompt is byte-identical to ot7's, and so
to the ot6 receipt ot7 took it from; and every other prompt here names no
design, no part, no number and no defect. A changed byte anywhere here is a
new attempt, so this test is the freeze.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROMPTS = REPO / "docs/probes/ot8/prompts"
README = PROMPTS / "README.md"
OT7 = REPO / "docs/probes/ot7/prompts"
CREATE = ("heron",)
FIRST = ("rebuild", "resolve")
CONTINUATIONS = ("continue-1", "continue-2", "continue-3")

# The same vocabulary ot7 froze (ADR-339): the design names of this lineage
# and the part and defect words of its designs.
FORBIDDEN_WORDS = (
    "heron", "robin", "finch", "plover", "lark", "wren",
    "servo", "horn", "bearing", "screw", "bolt", "insert", "cheek", "tab", "stub",
    "window", "pocket", "slot", "spline", "plane", "floor", "bench", "wall", "stage",
    "overlap", "intersect", "gap", "distance", "volume", "mm", "degree", "angle",
)
RECEIPT_LIMIT = 16 * 1024

# What every design-agnostic ot8 prompt must forbid, in the same words for
# every design: the cheap ways past a failing behaviour check that the charter
# names and refuses.
INVARIANTS = (
    "every purchased part stays an unmodified catalog part",
    "nothing from the world enters the design",
    "nothing becomes fixed to the world that the design declares free",
    "no support appears that the machine does not have",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _readme_table() -> dict[str, tuple[int, str]]:
    rows = {}
    for line in README.read_text().splitlines():
        m = re.match(r"^\| `([a-z0-9.-]+\.prompt\.txt)` \| .* \| (\d+) \| `([0-9a-f]{64})` \|$", line)
        if m:
            rows[m.group(1)] = (int(m.group(2)), m.group(3))
    return rows


def test_every_prompt_is_pinned_to_the_readme_digest():
    rows = _readme_table()
    expected = {f"{n}.create.prompt.txt" for n in CREATE}
    expected |= {f"{n}.prompt.txt" for n in CONTINUATIONS + FIRST}
    assert set(rows) == expected
    on_disk = {p.name for p in PROMPTS.glob("*.txt")}
    assert on_disk == expected, "a prompt file with no README row, or a row with no file"
    for name, (size, digest) in rows.items():
        path = PROMPTS / name
        assert path.stat().st_size == size, name
        assert _sha256(path) == digest, name
        assert path.read_bytes().endswith(b"\n") and b"\r" not in path.read_bytes(), name
    assert README.stat().st_size <= RECEIPT_LIMIT


def test_the_arm_create_prompt_is_ot7s_byte_for_byte():
    """G2 measures the same ask against today's product, so the ask is unchanged."""
    assert (PROMPTS / "heron.create.prompt.txt").read_bytes() == \
        (OT7 / "heron.create.prompt.txt").read_bytes()


def test_the_continuations_are_ot8s_own_and_carry_the_three_kinds_of_evidence():
    """ot7's continuations point at fit alone; ot8's charter points at fit,
    inventory and smoke, which is what makes the arm's catalog gap visible."""
    for name in CONTINUATIONS:
        text = (PROMPTS / f"{name}.prompt.txt").read_text()
        assert text != (OT7 / f"{name}.prompt.txt").read_text(), name
        assert "fit report" in text and "inventory" in text and "smoke" in text, name
        assert "every joint's declared range" in text, name


def test_no_other_prompt_names_a_design_part_number_or_defect():
    for name in CONTINUATIONS + FIRST:
        text = (PROMPTS / f"{name}.prompt.txt").read_text()
        assert not re.search(r"\d", text), f"{name}: a number"
        words = set(re.findall(r"[a-z]+", text.lower()))
        hit = words & set(FORBIDDEN_WORDS)
        assert not hit, f"{name}: {sorted(hit)}"
        assert "Do not train" in text and "Do not ask questions." in text, name
    texts = [(PROMPTS / f"{n}.prompt.txt").read_text() for n in CONTINUATIONS + FIRST]
    assert len(set(texts)) == len(texts), "each prompt is its own text"


def test_every_correcting_prompt_forbids_the_cheap_way_past_a_failing_check():
    for name in CONTINUATIONS + ("resolve",):
        text = (PROMPTS / f"{name}.prompt.txt").read_text()
        for clause in INVARIANTS:
            assert clause in text, f"{name}: {clause}"
        assert "modelled printable part" in text, name
        # A declared rollout may not be shortened to make a check pass.
        assert ("rollout bound" in text
                or "the smoke stays exactly as long as the design declares it" in text), name


def test_the_rebuild_prompt_authorises_a_rebuild_and_nothing_else():
    text = (PROMPTS / "rebuild.prompt.txt").read_text()
    assert "Do not edit the script" in text and "do not change a parameter" in text
    assert "unchanged" in text and "normal acceptance" in text
    assert "still change nothing" in text


def test_the_resolve_prompt_gives_the_honest_answer_equal_standing():
    """G4 may not be an experiment the agent can only pass by cheating."""
    text = (PROMPTS / "resolve.prompt.txt").read_text()
    assert "a defect in the design, or the declared behaviour of the machine" in text
    assert "change nothing at all" in text
    assert "missing control contract" in text
    assert "Do not train. Do not write a controller." in text
    assert "no declared limit or task rule is weakened" in text
    assert "the smoke stays exactly as long as the design declares it" in text


def test_the_readme_states_the_limits_and_the_ot7_difference():
    text = README.read_text()
    for row in ("| G2 arm | `heron.create.prompt.txt`, in a new empty project | 3 |",
                "| G3 biped | `rebuild.prompt.txt`, on an independent copy of `ot7-plover-e` | 3 |",
                "| G4 balancer | `resolve.prompt.txt`, on an independent copy of `ot7-robin-c` | 3 |"):
        assert row in text
    assert "ADR-400" in text and re.search(r"never\s+prompted again", text)
    assert "The continuations are **not** ot7's" in text
