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


def test_the_proxies_measure_against_the_frozen_bars():
    from cadex_cli import render

    p1, p2, p3 = (CONTRACT["proxies"][key] for key in ("P1", "P2", "P3"))
    assert render.PROXY_BARS == {
        p1["name"]: {"max": p1["max"]},
        p2["name"]: {"max": p2["max"]},
        p3["name"]: {"min": p3["min"], "max": p3["max"]},
    }


def test_a5_cold_prompts_are_frozen_on_page_and_file():
    a5 = CONTRACT["a5"]
    assert (a5["model"], a5["effort"], a5["turns"]) == ("claude-opus-5-5", "medium", 1)
    assert a5["env"] == {"CADEX_EFFORT": "medium"}
    assert "--fallback-model" not in a5["argv"]
    assert a5["argv"][a5["argv"].index("--model") + 1] == "claude-opus-5-5"
    hex_prompt = ("Design a hexapod walking robot using MG90S servos from the catalog "
                  "(two per leg: hip yaw and knee), a printable body, and the hardware "
                  "to assemble it. Then declare a training task that teaches it to walk "
                  "forward on flat ground.")
    assert sorted(a5["prompts"]) == ["biped", "hexapod", "quadruped"]
    # The hexapod prompt is hex1-hex3's, word for word.
    assert a5["prompts"]["hexapod"] == hex_prompt
    for plan, prompt in a5["prompts"].items():
        assert f"| {plan} | {prompt} |" in README
        # Cold: nothing about looks reaches the product agent from the prompt.
        for word in ("shell", "face", "colour", "color", "palette", "look", "render"):
            assert word not in prompt.lower(), (plan, word)


def test_a5_hexapod_attempt_is_published_with_its_score():
    score = json.loads((OT10 / "ot10-hexapod-1-score.json").read_text(encoding="utf-8"))
    assert score["rubric_sha256"] == RUBRIC_SHA256 and score["model"] == "claude-opus-5-5"
    assert score["total"] == sum(score["medians"].values()) == 13
    assert len([r for r in score["raw"] if "scores" in r]) == 3
    # The frozen candidate order: the studio hero, then the five look views.
    files = ["ot10-hexapod-1-hero.png"] + [
        f"ot10-hexapod-1-look_{view}.png" for view in ("iso", "iso_back", "front", "right", "top")]
    for candidate, name in zip(score["candidates"], files, strict=True):
        path = OT10 / name
        assert path.stat().st_size <= 300 * 1024
        assert hashlib.sha256(path.read_bytes()).hexdigest() == candidate["sha256"]
    # A miss is published as a miss: 13 is under the frozen 14.
    assert score["total"] < CONTRACT["bar"]["total_min"]
    assert "| attempt 1, median | 2 | 3 | 1 | 1 | 2 | 2 | 2 | **13** |" in README


def test_a5_hexapod_attempt_2_is_published_with_its_score():
    score = json.loads((OT10 / "ot10-hexapod-2-score.json").read_text(encoding="utf-8"))
    assert score["rubric_sha256"] == RUBRIC_SHA256 and score["model"] == "claude-opus-5-5"
    assert score["total"] == sum(score["medians"].values()) == 14
    assert len([r for r in score["raw"] if "scores" in r]) == 3
    files = ["ot10-hexapod-2-hero.png"] + [
        f"ot10-hexapod-2-look_{view}.png" for view in ("iso", "iso_back", "front", "right", "top")]
    for candidate, name in zip(score["candidates"], files, strict=True):
        path = OT10 / name
        assert path.stat().st_size <= 300 * 1024
        assert hashlib.sha256(path.read_bytes()).hexdigest() == candidate["sha256"]
    # The judged half meets the frozen bar; the attempt still misses A5 on the
    # swept fit, and the README says so rather than rounding it to a pass.
    assert score["total"] >= CONTRACT["bar"]["total_min"]
    assert "| attempt 2, median | 2 | 3 | 1 | 2 | 2 | 2 | 2 | **14** |" in README
    assert "**Misses the bar on one count: the swept fit is incomplete.**" in README


def test_a5_quadruped_attempt_is_published_with_its_score():
    score = json.loads((OT10 / "ot10-quadruped-2-score.json").read_text(encoding="utf-8"))
    assert score["rubric_sha256"] == RUBRIC_SHA256 and score["model"] == "claude-opus-5-5"
    assert score["total"] == sum(score["medians"].values()) == 16
    assert len([r for r in score["raw"] if "scores" in r]) == 3
    files = ["ot10-quadruped-2-hero.png"] + [
        f"ot10-quadruped-2-look_{view}.png" for view in ("iso", "iso_back", "front", "right", "top")]
    for candidate, name in zip(score["candidates"], files, strict=True):
        path = OT10 / name
        assert path.stat().st_size <= 300 * 1024
        assert hashlib.sha256(path.read_bytes()).hexdigest() == candidate["sha256"]
    # The judged half meets the frozen bar; the swept fit is still missing, and
    # the README publishes the miss as a miss.
    assert score["total"] >= CONTRACT["bar"]["total_min"]
    assert "| quadruped, median | 2 | 3 | 3 | 1 | 2 | 3 | 2 | **16** |" in README
    section = README.partition("## A5 attempt: the quadruped (`ot10-quadruped-2`)")[2]
    assert section.startswith("\n\n**Misses the bar on one count: the swept fit is incomplete.**")


def test_a5_hexapod_attempt_3_is_published_with_its_score():
    score = json.loads((OT10 / "ot10-hexapod-3-score.json").read_text(encoding="utf-8"))
    assert score["rubric_sha256"] == RUBRIC_SHA256 and score["model"] == "claude-opus-5-5"
    assert score["total"] == sum(score["medians"].values()) == 13
    assert len([r for r in score["raw"] if "scores" in r]) == 3
    files = ["ot10-hexapod-3-hero.png"] + [
        f"ot10-hexapod-3-look_{view}.png" for view in ("iso", "iso_back", "front", "right", "top")]
    for candidate, name in zip(score["candidates"], files, strict=True):
        path = OT10 / name
        assert path.stat().st_size <= 300 * 1024
        assert hashlib.sha256(path.read_bytes()).hexdigest() == candidate["sha256"]
    # Every fit gate passes; the judged total does not, and a miss is
    # published as a miss.
    assert score["total"] < CONTRACT["bar"]["total_min"]
    assert "| attempt 3, median | 2 | 3 | 2 | 1 | 1 | 2 | 2 | **13** |" in README
    section = README.partition("## A5 attempt 3: the hexapod (`ot10-hexapod-3`)")[2]
    assert section.startswith(
        "\n\n**Misses the bar on one count: the judged total is 13 of 21, under the\nfrozen 14.**")


def test_a5_hexapod_attempt_4_is_published_with_its_score():
    score = json.loads((OT10 / "ot10-hexapod-4-score.json").read_text(encoding="utf-8"))
    assert score["rubric_sha256"] == RUBRIC_SHA256 and score["model"] == "claude-opus-5-5"
    assert score["total"] == sum(score["medians"].values()) == 12
    assert len([r for r in score["raw"] if "scores" in r]) == 3
    files = ["ot10-hexapod-4-hero.png"] + [
        f"ot10-hexapod-4-look_{view}.png" for view in ("iso", "iso_back", "front", "right", "top")]
    for candidate, name in zip(score["candidates"], files, strict=True):
        path = OT10 / name
        assert path.stat().st_size <= 300 * 1024
        assert hashlib.sha256(path.read_bytes()).hexdigest() == candidate["sha256"]
    # ADR-422's face rule moved T5 from 1 to 2; the total still misses.
    assert score["medians"]["T5"] == 2
    assert score["total"] < CONTRACT["bar"]["total_min"]
    assert "| attempt 4, median | 2 | 2 | 1 | 1 | 2 | 2 | 2 | **12** |" in README
    section = README.partition("## A5 attempt 4: the hexapod (`ot10-hexapod-4`)")[2]
    assert section.startswith(
        "\n\n**Misses the bar on one count: the judged total is 12 of 21, under the\nfrozen 14.**")


def test_a5_quadruped_attempt_3_is_published_with_its_score():
    score = json.loads((OT10 / "ot10-quadruped-3-score.json").read_text(encoding="utf-8"))
    assert score["rubric_sha256"] == RUBRIC_SHA256 and score["model"] == "claude-opus-5-5"
    assert score["total"] == sum(score["medians"].values()) == 15
    assert len([r for r in score["raw"] if "scores" in r]) == 3
    files = ["ot10-quadruped-3-hero.png"] + [
        f"ot10-quadruped-3-look_{view}.png" for view in ("iso", "iso_back", "front", "right", "top")]
    for candidate, name in zip(score["candidates"], files, strict=True):
        path = OT10 / name
        assert path.stat().st_size <= 300 * 1024
        assert hashlib.sha256(path.read_bytes()).hexdigest() == candidate["sha256"]
    # The judged half meets the frozen bar with no trait at 0, and the README
    # publishes the whole verdict, swept fit included, as a pass.
    assert score["total"] >= CONTRACT["bar"]["total_min"]
    assert min(score["medians"].values()) >= 1
    assert "| quadruped 3, median | 2 | 3 | 2 | 2 | 2 | 2 | 2 | **15** |" in README
    section = README.partition("## A5 attempt 3: the quadruped (`ot10-quadruped-3`)")[2]
    assert section.startswith("\n\n**Meets the bar on every item, the second A5 design in the run to do\nso")


def test_a5_hexapod_attempt_5_is_published_with_its_score():
    score = json.loads((OT10 / "ot10-hexapod-5-score.json").read_text(encoding="utf-8"))
    assert score["rubric_sha256"] == RUBRIC_SHA256 and score["model"] == "claude-opus-5-5"
    assert score["total"] == sum(score["medians"].values()) == 16
    assert len([r for r in score["raw"] if "scores" in r]) == 3
    files = ["ot10-hexapod-5-hero.png"] + [
        f"ot10-hexapod-5-look_{view}.png" for view in ("iso", "iso_back", "front", "right", "top")]
    for candidate, name in zip(score["candidates"], files, strict=True):
        path = OT10 / name
        assert path.stat().st_size <= 300 * 1024
        assert hashlib.sha256(path.read_bytes()).hexdigest() == candidate["sha256"]
    # The judged half clears the frozen bar, but the swept fit stopped at
    # 10 of 12 joints, so the README publishes the design as a miss.
    assert score["total"] >= CONTRACT["bar"]["total_min"]
    assert min(score["medians"].values()) >= 1
    assert "| attempt 5, median | 2 | 3 | 3 | 2 | 2 | 2 | 2 | **16** |" in README
    section = README.partition("## A5 attempt 5: the hexapod (`ot10-hexapod-5`)")[2]
    assert section.startswith(
        "\n\n**Misses the bar on one count: the swept fit is incomplete, 10 of 12\njoints.**")


def test_a5_hexapod_attempt_6_is_published_with_its_score():
    score = json.loads((OT10 / "ot10-hexapod-6-score.json").read_text(encoding="utf-8"))
    assert score["rubric_sha256"] == RUBRIC_SHA256 and score["model"] == "claude-opus-5-5"
    assert score["total"] == sum(score["medians"].values()) == 15
    assert len([r for r in score["raw"] if "scores" in r]) == 3
    files = ["ot10-hexapod-6-hero.png"] + [
        f"ot10-hexapod-6-look_{view}.png" for view in ("iso", "iso_back", "front", "right", "top")]
    for candidate, name in zip(score["candidates"], files, strict=True):
        path = OT10 / name
        assert path.stat().st_size <= 300 * 1024
        assert hashlib.sha256(path.read_bytes()).hexdigest() == candidate["sha256"]
    # The judged half clears the frozen bar, but the accepted revision's
    # sweep exceeded the pair budget on every joint, so it is a miss.
    assert score["total"] >= CONTRACT["bar"]["total_min"]
    assert min(score["medians"].values()) >= 1
    assert "| attempt 6, median | 2 | 3 | 2 | 2 | 2 | 2 | 2 | **15** |" in README
    section = README.partition("## A5 attempt 6: the hexapod (`ot10-hexapod-6`)")[2]
    assert section.startswith(
        "\n\n**Misses the bar: the accepted revision's swept fit is incomplete, 0 of\n12 joints,")


def test_a5_hexapod_attempt_7_is_published_with_its_score():
    score = json.loads((OT10 / "ot10-hexapod-7-score.json").read_text(encoding="utf-8"))
    assert score["rubric_sha256"] == RUBRIC_SHA256 and score["model"] == "claude-opus-5-5"
    assert score["total"] == sum(score["medians"].values()) == 13
    assert len([r for r in score["raw"] if "scores" in r]) == 3
    files = ["ot10-hexapod-7-hero.png"] + [
        f"ot10-hexapod-7-look_{view}.png" for view in ("iso", "iso_back", "front", "right", "top")]
    for candidate, name in zip(score["candidates"], files, strict=True):
        path = OT10 / name
        assert path.stat().st_size <= 300 * 1024
        assert hashlib.sha256(path.read_bytes()).hexdigest() == candidate["sha256"]
    # Static fit and sweep both pass, but the judged total is under the
    # frozen bar, so the README publishes the design as a miss.
    assert score["total"] < CONTRACT["bar"]["total_min"]
    assert "| attempt 7, median | 2 | 3 | 1 | 1 | 2 | 2 | 2 | **13** |" in README
    section = README.partition("## A5 attempt 7: the hexapod (`ot10-hexapod-7`)")[2]
    assert section.startswith(
        "\n\n**Misses the bar on one count: the judged total is 13 of 21, under the\nfrozen 14.**")


def test_a5_hexapod_attempt_8_is_published_with_its_score():
    score = json.loads((OT10 / "ot10-hexapod-8-score.json").read_text(encoding="utf-8"))
    assert score["rubric_sha256"] == RUBRIC_SHA256 and score["model"] == "claude-opus-5-5"
    assert score["total"] == sum(score["medians"].values()) == 8
    assert len([r for r in score["raw"] if "scores" in r]) == 3
    files = ["ot10-hexapod-8-hero.png"] + [
        f"ot10-hexapod-8-look_{view}.png" for view in ("iso", "iso_back", "front", "right", "top")]
    for candidate, name in zip(score["candidates"], files, strict=True):
        path = OT10 / name
        assert path.stat().st_size <= 300 * 1024
        assert hashlib.sha256(path.read_bytes()).hexdigest() == candidate["sha256"]
    # The turn wedged its live document and accepted a leg probe, so the
    # README publishes it as a miss rather than leaving it out.
    assert score["total"] < CONTRACT["bar"]["total_min"] and score["medians"]["T5"] == 0
    assert "| attempt 8, median | 1 | 1 | 2 | 1 | 0 | 1 | 2 | **8** |" in README
    section = README.partition("## A5 attempt 8: the hexapod (`ot10-hexapod-8`)")[2]
    assert section.startswith(
        "\n\n**Misses the bar on four counts: the judged total is 8 of 21, T5 is 0,")


def test_a5_hexapod_attempt_10_is_published_with_its_score():
    score = json.loads((OT10 / "ot10-hexapod-10-score.json").read_text(encoding="utf-8"))
    assert score["rubric_sha256"] == RUBRIC_SHA256 and score["model"] == "claude-opus-5-5"
    assert score["total"] == sum(score["medians"].values()) == 14
    assert len([r for r in score["raw"] if "scores" in r]) == 3
    files = ["ot10-hexapod-10-hero.png"] + [
        f"ot10-hexapod-10-look_{view}.png" for view in ("iso", "iso_back", "front", "right", "top")]
    for candidate, name in zip(score["candidates"], files, strict=True):
        path = OT10 / name
        assert path.stat().st_size <= 300 * 1024
        assert hashlib.sha256(path.read_bytes()).hexdigest() == candidate["sha256"]
    # The first hexapod to meet every bar item: the judged half clears the
    # frozen total with no zero trait, and the README records the fit gates.
    assert score["total"] >= CONTRACT["bar"]["total_min"]
    assert min(score["medians"].values()) >= 1
    assert "| attempt 10, median | 2 | 2 | 1 | 2 | 2 | 3 | 2 | **14** |" in README
    section = README.partition("## A5 attempt 10: the hexapod (`ot10-hexapod-10`)")[2]
    assert section.startswith(
        "\n\n**Meets the bar on every item, the first hexapod in the run to do so.**")
    assert "**Attempt 9 is not counted.**" in section


def test_a5_hexapod_attempt_11_the_confirmation_round_is_published_with_its_score():
    score = json.loads((OT10 / "ot10-hexapod-11-score.json").read_text(encoding="utf-8"))
    assert score["rubric_sha256"] == RUBRIC_SHA256 and score["model"] == "claude-opus-5-5"
    assert score["total"] == sum(score["medians"].values()) == 14
    assert len([r for r in score["raw"] if "scores" in r]) == 3
    files = ["ot10-hexapod-11-hero.png"] + [
        f"ot10-hexapod-11-look_{view}.png" for view in ("iso", "iso_back", "front", "right", "top")]
    for candidate, name in zip(score["candidates"], files, strict=True):
        path = OT10 / name
        assert path.stat().st_size <= 300 * 1024
        assert hashlib.sha256(path.read_bytes()).hexdigest() == candidate["sha256"]
    assert (OT10 / "ot10-hexapod-11-sheet.png").stat().st_size <= 300 * 1024
    assert score["total"] >= CONTRACT["bar"]["total_min"]
    assert min(score["medians"].values()) >= 1
    assert "| attempt 11, median | 2 | 3 | 1 | 2 | 2 | 2 | 2 | **14** |" in README
    # It follows the pre-registration, and the round's next turn is named.
    assert README.index("## A5 confirmation round, pre-registered") < README.index(
        "## A5 attempt 11: the hexapod (`ot10-hexapod-11`), confirmation round")
    section = README.partition(
        "## A5 attempt 11: the hexapod (`ot10-hexapod-11`), confirmation round")[2]
    assert section.startswith("\n\n**Meets the bar on every item. This is the confirmation round's")
    assert "at revision `4288ef42`" in section
    assert "`ot10-quadruped-4`, on the frozen quadruped" in section


# -- A4: the refusal census --------------------------------------------------

_rspec = importlib.util.spec_from_file_location("ot10_refusals", OT10 / "runner/refusals.py")
refusals = importlib.util.module_from_spec(_rspec)
_rspec.loader.exec_module(refusals)
CENSUS = json.loads((OT10 / "refusals.json").read_text(encoding="utf-8"))

# Every ot10 product-agent transcript: refused calls, and the CPU-limit share.
REFUSED = {
    "ot10-biped-1": ("counted", 7, 0),
    "ot10-hexapod-10": ("counted", 15, 6),
    "ot10-hexapod-11": ("counted", 12, 0),
    "ot10-quadruped-3": ("counted", 10, 0),
    "ot10-hexapod-1": ("failed_attempt", 33, 19),
    "ot10-hexapod-2": ("failed_attempt", 10, 3),
    "ot10-hexapod-3": ("failed_attempt", 20, 4),
    "ot10-hexapod-4": ("failed_attempt", 14, 8),
    "ot10-hexapod-5": ("failed_attempt", 20, 0),
    "ot10-hexapod-6": ("failed_attempt", 8, 0),
    "ot10-hexapod-7": ("failed_attempt", 9, 1),
    "ot10-hexapod-8": ("failed_attempt", 20, 3),
    "ot10-quadruped-2": ("failed_attempt", 11, 0),
    "ot10-hexapod-9": ("not_an_attempt", 4, 0),
    "ot10-quadruped-1": ("not_an_attempt", 2, 0),
}

# The refusal each class was named for, as hex2/hex3 met it and as the
# engine words it since ADR-416 -- and two texts that only look like one.
CLASS_TEXTS = [
    ("", "lib.servo.horn: style must be one of cross, double_arm, single_arm.", "horn_style"),
    ("", "lib.servo.horn: 'single' is not a horn style; style must be one of 'cross', "
         "'double_arm', 'single_arm'. Did you mean 'single_arm'?", "horn_style"),
    ("", "There is no project script to edit yet; use write_script.", "edit_before_script"),
    ("NO_PROJECT_SCRIPT", "There is no accepted project script to edit yet: the last "
     "write_script was refused and rolled back, and edit_script only edits an accepted "
     "source. Resend the whole corrected source with write_script and "
     "expected_revision=''.", "edit_before_script"),
    ("", "An Assembly program must return exactly one assembly and one solver_diagnostics "
         "output.", "assembly_output_count"),
    ("DOMAIN_CANDIDATE_FAILED", "An Assembly program must return exactly one assembly and "
     "one solver_diagnostics output; result returns 1 assembly ('hexapod') and 0 "
     "solver_diagnostics (none). Add `result['solve'] = assembly.solve(hexapod)`",
     "assembly_output_count"),
    ("", "Every joint listed in api.assembly must be returned exactly once, and no unlisted "
         "joint output is allowed.", "joint_listing"),
    ("", "Every component listed in api.assembly must be returned exactly once, and no "
         "unlisted component output is allowed. 2 component(s) listed in api.assembly are "
         "not returned in result", "joint_listing"),
    ("PROJECT_OUTPUTS_DROPPED", "This script drops outputs that the accepted revision "
     "declares: horn, servo. write_script replaces THE whole project script",
     "outputs_dropped"),
    ("DOMAIN_PUBLICATION_FAILED", "PUBLICATION_UNTAGGED_OBJECT: the document contains "
     "objects the project script does not own: ['Joints', 'Joints001'].", "other"),
]


@pytest.mark.parametrize("code, error, expected", CLASS_TEXTS)
def test_the_census_classifies_each_a4_refusal_by_its_engine_text(code, error, expected):
    assert refusals.classify(code, error) == expected


def test_the_refusal_census_is_pinned_and_rederives_from_its_file():
    assert CENSUS["schema"] == "ot10-refusals-v1"
    assert CENSUS["a4_classes"] == list(refusals.A4_CLASSES)
    assert CENSUS["classes"] == list(refusals.CLASSES)
    projects = CENSUS["projects"]
    assert {n: (p["status"], p["refused"], p["counts"]["cpu_limit"])
            for n, p in projects.items()} == REFUSED
    for name, row in projects.items():
        assert len(row["calls"]) == row["refused"] == sum(row["counts"].values())
        assert refusals.counts(row["calls"]) == row["counts"], name
        assert all(row["counts"][c] == 0 for c in refusals.A4_CLASSES), name
        assert len(row["transcript_sha256"]) == 64
    # The three designs the A5 criterion counts are all in the census.
    counted = sorted(n for n, p in projects.items() if p["status"] == "counted")
    assert counted == ["ot10-biped-1", "ot10-hexapod-10", "ot10-hexapod-11", "ot10-quadruped-3"]
    assert "/home/" not in (OT10 / "refusals.json").read_text(encoding="utf-8")


def test_the_census_table_is_published_equal_to_its_file():
    assert refusals.table(CENSUS) in README
    assert ("| **all** | 15 transcripts | **0** | **0** | **0** | **0** | 195 |"
            in README)


def test_refused_calls_reads_a_truncated_refusal_body(tmp_path):
    # A long refusal reaches the transcript with its middle cut by the agent
    # CLI; the class must still come from the engine's own fields.
    cut = ('{\n  "allowed_values": [],\n  "error": "There is no project script to edit '
           'yet; use write_script.",\n  "failure_code": "NO_PROJECT_SCRIPT",\n  "src": "a\tb'
           '\n\n... [9960 characters truncated] ...\n\n"\n}')
    lines = [
        {"message": {"content": [
            {"type": "tool_use", "id": "t1", "name": "mcp__cadex__edit_script"},
            {"type": "tool_use", "id": "t2", "name": "mcp__cadex__inspect"}]}},
        {"message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1", "is_error": True, "content": cut},
            {"type": "tool_result", "tool_use_id": "t2", "is_error": False, "content": "{}"},
            {"type": "tool_result", "tool_use_id": "t3", "is_error": True,
             "content": [{"type": "text", "text": json.dumps(
                 {"error": "JSON Pointer path does not exist: '/facts'.",
                  "failure_code": "INSPECTION_FAILED"})}]}]}},
    ]
    transcript = tmp_path / "s.jsonl"
    transcript.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")
    calls = refusals.refused_calls(transcript)
    assert [(c["tool"], c["failure_code"]) for c in calls] == [
        ("edit_script", "NO_PROJECT_SCRIPT"), ("?", "INSPECTION_FAILED")]
    assert refusals.counts(calls)["edit_before_script"] == 1
    assert refusals.counts(calls)["json_pointer"] == 1


def test_the_census_matches_the_local_transcripts_when_present():
    # Transcripts are never committed; on the machine that ran ot10 the
    # committed census must be what the counter derives from them today.
    root = Path.home() / ".claude/projects"
    checked = 0
    for name, row in CENSUS["projects"].items():
        found = [p for d in root.glob(f"*-{name}") for p in d.glob("*.jsonl")]
        match = [p for p in found
                 if hashlib.sha256(p.read_bytes()).hexdigest() == row["transcript_sha256"]]
        if not match:
            continue
        assert refusals.census(match[0], row["status"]) == row, name
        checked += 1
    if not checked:
        pytest.skip("no ot10 transcript on this machine")
