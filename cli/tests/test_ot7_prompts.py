"""The ot7 prompt freeze (ADR-341, ADR-345).

Every prompt a design turn may see in run ot7 is committed under
``docs/probes/ot7/prompts/`` before the first design turn, with its digest in
the README table; the two ot6 create prompts are byte-identical to their ot6
receipts; and the continuation and repair prompts name no design, no part,
no number and no defect. A changed byte anywhere here is a new attempt, so
this test is the freeze.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROMPTS = REPO / "docs/probes/ot7/prompts"
README = PROMPTS / "README.md"
CREATE = ("heron", "robin", "plover")
CONTINUATIONS = ("continue-1", "continue-2", "continue-3")
REPAIR = "repair"

# Words a design-agnostic prompt may not contain: the ot6/ot7 design names and
# the part and defect vocabulary of the three ot6 designs (ADR-339).
FORBIDDEN_WORDS = (
    "heron", "robin", "finch", "plover", "lark", "wren",
    "servo", "horn", "bearing", "screw", "bolt", "insert", "cheek", "tab", "stub",
    "window", "pocket", "slot", "spline", "plane", "floor", "bench", "wall", "stage",
    "overlap", "intersect", "gap", "distance", "volume", "mm", "degree", "angle",
)
RECEIPT_LIMIT = 16 * 1024


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
    expected |= {f"{n}.prompt.txt" for n in CONTINUATIONS + (REPAIR,)}
    assert set(rows) == expected
    on_disk = {p.name for p in PROMPTS.glob("*.txt")}
    assert on_disk == expected, "a prompt file with no README row, or a row with no file"
    for name, (size, digest) in rows.items():
        path = PROMPTS / name
        assert path.stat().st_size == size, name
        assert _sha256(path) == digest, name
        assert path.read_bytes().endswith(b"\n") and b"\r" not in path.read_bytes(), name
    assert README.stat().st_size <= RECEIPT_LIMIT


def test_the_ot6_create_prompts_are_unchanged():
    heron = json.loads((REPO / "docs/probes/ot6/heron/design.json").read_text())
    assert _sha256(PROMPTS / "heron.create.prompt.txt") == heron["turns"][0]["prompt_sha256"]
    robin = REPO / "docs/probes/ot6/robin/create.prompt.txt"
    assert (PROMPTS / "robin.create.prompt.txt").read_bytes() == robin.read_bytes()
    for name in ("heron", "robin"):
        text = (PROMPTS / f"{name}.create.prompt.txt").read_text()
        assert text.startswith("Create a NEW parametric ")
        assert f"called {name.capitalize()} in this empty project" in text


def test_the_biped_prompt_asks_for_the_charter_machine():
    text = (PROMPTS / "plover.create.prompt.txt").read_text()
    assert text.startswith("Create a NEW parametric two-legged walking mechanism called Plover")
    assert text.count('lib.servo("mg90s")') >= 2 and "four `lib.servo(\"mg90s\")`" in text
    assert "hip pitch and knee pitch" in text
    assert 'horn("single_arm")' in text and 'lib.bearing("mr128")' in text
    assert 'lib.bolt("m2", 6.0)' in text and 'lib.bolt("m2", 16.0)' in text
    assert "hip_limit" in text and "knee_limit" in text
    assert "Nothing in the world is part of the design: no floor, slab, wall, bench or stage." in text
    assert "nothing is grounded" in text and "free base" in text
    assert "The pelvis, both thighs and both shins are printed." in text
    assert "measured fit checks your tools report" in text
    assert "Do not train anything in this turn." in text
    assert "policy_on" in text
    assert text.count("Plover") == 1, "the design's name appears once, in the create line"
    for other in ("Heron", "Robin", "Finch", "Lark", "Wren"):
        assert other not in text


def test_continuation_and_repair_prompts_name_no_design_part_number_or_defect():
    for name in CONTINUATIONS + (REPAIR,):
        text = (PROMPTS / f"{name}.prompt.txt").read_text()
        assert not re.search(r"\d", text), f"{name}: a number"
        words = set(re.findall(r"[a-z]+", text.lower()))
        hit = words & set(FORBIDDEN_WORDS)
        assert not hit, f"{name}: {sorted(hit)}"
        assert "measured fit report" in text
        assert "every joint's declared range" in text
        assert "Do not train." in text and "Do not ask questions." in text
        assert "re-accept" in text
    texts = [(PROMPTS / f"{n}.prompt.txt").read_text() for n in CONTINUATIONS + (REPAIR,)]
    assert len(set(texts)) == len(texts), "each continuation is its own prompt"


def test_the_readme_states_the_limits():
    text = README.read_text()
    for row in ("| F5 arm | `heron.create.prompt.txt` | 3 |",
                "| F6 balancer | `robin.create.prompt.txt` | 3 |",
                "| F7 biped | `plover.create.prompt.txt` | 3 |",
                "| 1 | `repair.prompt.txt` |"):
        assert row in text
    assert "ADR-345" in text and "never prompted again" in text
