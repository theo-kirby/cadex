# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The ot10 design-quality contract (A1), frozen before any A5 probe.

``docs/probes/ot10/README.md`` freezes a seven-trait rubric, three proxies,
the A5 bar and a blind judging procedure; ``contract.json`` is its
machine-readable copy and ``runner/judge.py`` is the procedure. The
literals below are the freeze: changing the rubric text, a proxy
threshold, the bar or the judge's isolation is a recorded decision that
re-scores every earlier probe, so it has to move this test on purpose.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
OT10 = REPO / "docs/probes/ot10"
CONTRACT = json.loads((OT10 / "contract.json").read_text(encoding="utf-8"))
README = (OT10 / "README.md").read_text(encoding="utf-8")
LANGUAGE = (REPO / "docs/DESIGN-LANGUAGE.md").read_text(encoding="utf-8")

_spec = importlib.util.spec_from_file_location("ot10_judge", OT10 / "runner/judge.py")
judge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(judge)

RUBRIC_SHA256 = "1c81caa2c5f6ac61e936d8cf99cbfe4a56649007fd83a7c5bc02824d16c1b08f"
TRAITS = ["T1", "T2", "T3", "T4", "T5", "T6", "T7"]
PROXIES = {
    "P1": {"name": "hardware_silhouette_share", "max": 0.20},
    "P2": {"name": "sharp_outside_edge_share", "max": 0.25},
    "P3": {"name": "material_count", "min": 2, "max": 3},
}
BAR = {"total_min": 14, "trait_min": 1, "above_baseline": True}
CORE = [
    "01-desktop-arm-product-finish.jpg",
    "04-jerboa-poster-orange-accent.jpg",
    "07-white-hood-quadruped-yellow-studio.jpg",
    "08-grey-cad-render-filleted-joints.jpg",
    "12-tan-folded-quadruped-chunky.jpg",
    "14-ibots-crab-white-shell-dark-visor.jpg",
    "26-white-frog-shell-dark-joints.jpg",
    "39-grey-wheel-leg-hexapod-product.jpg",
    "43-yellow-sphere-quadruped-dark-legs.jpg",
    "46-orange-spider-concept-sheet.jpg",
]


def test_rubric_is_frozen_and_the_contract_names_it():
    assert judge.rubric_sha256() == RUBRIC_SHA256 == CONTRACT["rubric_sha256"]
    block = judge.rubric()
    assert [t for t in TRAITS if f"\n{t} " in "\n" + block] == TRAITS
    assert CONTRACT["traits"] == TRAITS
    for trait in TRAITS:
        section = block.split(f"{trait} ", 1)[1]
        for score in "0123":
            assert f"\n{score}: " in section, (trait, score)


def test_proxies_and_bar_match_page_and_file():
    assert CONTRACT["proxies"] == PROXIES
    assert CONTRACT["bar"] == BAR
    assert "≤ 0.20" in README and "≤ 0.25" in README and "2 or 3" in README
    assert "Judged total ≥ 14 of 21" in README and "No trait scores 0" in README
    for proxy in PROXIES.values():
        assert f"`{proxy['name']}`" in README


def test_procedure_is_the_frozen_one():
    procedure = CONTRACT["procedure"]
    assert procedure == {"model": "claude-opus-5-5", "effort": "high", "calls": 3,
                         "aggregate": "median per trait", "references": CORE}
    assert (judge.MODEL, judge.EFFORT, judge.CALLS) == ("claude-opus-5-5", "high", 3)
    argv = judge.command("claude", "PROMPT", Path("/refs"), Path("/cand"))
    assert "--fallback-model" not in argv
    assert argv[argv.index("--model") + 1] == "claude-opus-5-5"
    assert argv[argv.index("--tools") + 1] == "Read"
    assert argv[argv.index("--setting-sources") + 1] == "project"
    assert "--strict-mcp-config" in argv and "--no-session-persistence" in argv
    assert [argv[i + 1] for i, a in enumerate(argv) if a == "--add-dir"] == ["/refs", "/cand"]
    # The judge's whole context: the pinned instructions, then the rubric.
    assert argv[argv.index("--system-prompt") + 1] == judge.INSTRUCTIONS + judge.rubric()


def test_the_judge_never_sees_the_language_or_a_name():
    prompt = judge.system_prompt() + judge.user_prompt(
        [Path("/r") / name for name in CORE], [Path("/c/candidate-1.png")])
    for leak in ("DESIGN-LANGUAGE", "hex3", "Cadex", "cadex", "iso_back", "look_", "`look`"):
        assert leak not in prompt


def test_parse_accepts_only_seven_integer_scores():
    good = {t: {"score": 2, "reason": "x"} for t in TRAITS}
    assert judge.parse("```json\n" + json.dumps(good) + "\n```")["T4"]["score"] == 2
    for bad in ({**good, "T3": {"score": 4}}, {**good, "T3": {"score": 1.5}},
                {k: v for k, v in good.items() if k != "T7"}, {**good, "T8": {"score": 1}}):
        with pytest.raises(judge.JudgeError):
            judge.parse(json.dumps(bad))
    with pytest.raises(judge.JudgeError):
        judge.parse("no scores here")


def test_aggregate_takes_the_median_per_trait():
    calls = [{t: {"score": s} for t in TRAITS} for s in (0, 3, 1)]
    assert judge.aggregate(calls) == {"medians": {t: 1 for t in TRAITS}, "total": 7}


def test_language_cites_core_references_by_filename_only():
    cited = {name for name in CORE if name in LANGUAGE}
    assert cited == set(CORE)
    # Filenames only: no path into the gitignored folder, no embedded image.
    assert "reference/images" not in LANGUAGE and "](" not in LANGUAGE.split("## 1.")[1].split("## 9.")[0]
    assert "![" not in LANGUAGE and "![" not in README


def test_baseline_is_scored_and_committed():
    baseline = CONTRACT["baseline"]
    assert baseline["project"] == "hex3"
    assert baseline["revision"].startswith("c1704bfcb631")
    score = json.loads((OT10 / baseline["score_file"]).read_text(encoding="utf-8"))
    assert score["rubric_sha256"] == RUBRIC_SHA256
    assert score["total"] == baseline["total"] == sum(score["medians"].values())
    assert len([r for r in score["raw"] if "scores" in r]) == 3
    for shot in baseline["renders"]:
        path = OT10 / shot["file"]
        assert path.stat().st_size <= 300 * 1024
        assert hashlib.sha256(path.read_bytes()).hexdigest() == shot["sha256"]
    assert [c["sha256"] for c in score["candidates"]] == [s["sha256"] for s in baseline["renders"]]
