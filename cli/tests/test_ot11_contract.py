# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The ot11 evaluation contract (P1), frozen before any ot11 training run.

``docs/probes/ot11/README.md`` freezes, for walk, reach and balance, a
success spec read from a rollout trace, ten evaluation seeds with their
conditions, the pass rule and a blind video judge; ``contract.json`` is its
machine-readable copy. The literals below are the freeze: changing a seed,
a condition range, a predicate, a threshold, the rubric or the judge's bar
is a recorded decision that re-evaluates every earlier ot11 policy, so it
has to move this test on purpose. The README is held to the same values so
the page and the file cannot drift.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OT11 = REPO / "docs/probes/ot11"
CONTRACT = json.loads((OT11 / "contract.json").read_text(encoding="utf-8"))
README = (OT11 / "README.md").read_text(encoding="utf-8")
FLAT = re.sub(r"\s+", " ", README)

SEEDS = [1101, 1102, 1103, 1104, 1105, 1106, 1107, 1108, 1109, 1110]
RUBRIC_SHA256 = "dc081807c28033ec7c729ff967d078a2dfdd884f088d8fa7cf130255048d83ed"

#: id -> (name, the limits the predicate carries)
WALK = {
    "W1": ("completes", {}),
    "W2": ("upright", {"max": 30.0}),
    "W3": ("tracks_speed", {"min": 0.75, "max": 1.25}),
    "W4": ("goes_straight", {"max": [0.25, 45.0]}),
    "W5": ("steps", {"min": [4, 0.70]}),
    "W6": ("foot_clearance", {"min": 0.08}),
    "W7": ("foot_slip", {"max": 0.15}),
    "W8": ("duty_factor", {"min": 0.40, "max": 0.85}),
    "W9": ("every_leg_works", {"max": 1.5}),
    "W10": ("on_the_floor_not_in_it", {"min": -0.05}),
}
REACH = {
    "Q1": ("completes", {}),
    "Q2": ("final_error", {"max": 0.05}),
    "Q3": ("time_to_target", {"max_s": 2.0}),
    "Q4": ("overshoot", {"max": 0.20}),
}
BALANCE = {
    "B1": ("completes", {}),
    "B2": ("upright", {"max": 30.0}),
    "B3": ("stays_in_place", {"max": 2.0}),
    "B4": ("keeps_heading", {"max": 20.0}),
    "B5": ("recovers", {"max_s": 2.0, "rest": {"tilt_deg_max": 10.0, "speed_com_heights_per_s_max": 1.0,
                                               "hold_s": 1.0}}),
}
LIMIT_KEYS = ("min", "max", "max_s", "rest")


def frozen(behaviour: str) -> dict[str, tuple[str, dict]]:
    return {row["id"]: (row["name"], {k: row[k] for k in LIMIT_KEYS if k in row})
            for row in CONTRACT["behaviours"][behaviour]["predicates"]}


def test_the_ten_evaluation_seeds_are_frozen_and_are_not_training_seeds() -> None:
    assert CONTRACT["evaluation_seeds"] == SEEDS and len(set(SEEDS)) == 10
    assert "**1101, 1102, 1103, 1104, 1105, 1106, 1107, 1108, 1109, 1110.**" in README
    assert "A trainer --seed may never be one of these ten values" in CONTRACT["seed_rule"]
    assert "**Evaluation seeds are never training seeds.**" in README


def test_every_seed_must_pass_every_predicate() -> None:
    assert CONTRACT["pass_rule"].startswith("A policy passes a behaviour only if every one of the ten seeds")
    assert "No per-seed rate is granted" in CONTRACT["pass_rule"]
    assert "**Every seed must pass every predicate.**" in README


def test_no_predicate_reads_the_reward() -> None:
    assert CONTRACT["reward_independence"].startswith("No predicate reads the task's reward")
    assert "**The reward never judges itself.**" in README
    for behaviour in ("walk", "reach", "balance"):
        for row in CONTRACT["behaviours"][behaviour]["predicates"]:
            text = json.dumps(row).lower()
            assert "reward" not in text and "return" not in text, row["id"]


def test_the_walk_spec_is_frozen() -> None:
    assert frozen("walk") == WALK
    walk = CONTRACT["behaviours"]["walk"]
    assert walk["episode_seconds"] == 10.0 and walk["settle_s"] == 1.0
    conditions = walk["conditions"]
    assert conditions["reset_variation"] == {"tilt_deg": [0.0, 3.0], "lift_above_clearing_mm": [0.0, 5.0]}
    assert conditions["goal"]["forward_hip_heights_per_s"] == [0.6, 1.0]
    (shove,) = conditions["disturbance"]
    assert (shove["force_weights"], shove["duration_s"], shove["at_s"]) == ([0.05, 0.20], 0.15, [3.0, 7.0])
    for phrase in ("**[0.6, 1.0] hip heights per second**", "**[0.05, 0.20] × weight** for 0.15 s",
                   "every foot: ≥ 4 steps and ≥ 0.70", "every foot: ≥ 0.08 hip heights",
                   "every foot: ≤ 0.15", "every foot: 0.40 to 0.85", "every foot: ≥ −0.05 hip heights",
                   "at most **1.0 mm**", "at least **0.10 s**", "at least **0.15 hip heights**"):
        assert phrase in FLAT, phrase


def test_the_reach_spec_is_frozen() -> None:
    assert frozen("reach") == REACH
    reach = CONTRACT["behaviours"]["reach"]
    assert reach["episode_seconds"] == 8.0
    goal = reach["conditions"]["goal"]
    assert goal["switch_at_s"] == 4.0 and goal["max_redraws"] == 100
    assert "central 80 %" in goal["sampling"] and "0.25 arm lengths" in goal["redraw_if"][2]
    assert "no training configuration may list them" in goal["held_out"]
    for phrase in ("**central 80 %**", "**0.25 arm lengths**", "≤ 0.05 arm lengths", "| ≤ 2.0 s |",
                   "| ≤ 0.20 |", "No training configuration may list them."):
        assert phrase in FLAT, phrase


def test_the_balance_spec_is_frozen() -> None:
    assert frozen("balance") == BALANCE
    balance = CONTRACT["behaviours"]["balance"]
    assert balance["episode_seconds"] == 10.0
    first, second = balance["conditions"]["disturbance"]
    assert first["force_weights"] == second["force_weights"] == [0.10, 0.25]
    assert first["duration_s"] == second["duration_s"] == 0.10
    assert (first["at_s"], second["at_s"]) == ([2.0, 3.0], [5.5, 6.5])
    for phrase in ("**two** horizontal shoves", "**[0.10, 0.25] × weight** for 0.10 s", "≤ 2.0 COM heights",
                   "| ≤ 20° |", "every shove: ≤ 2.0 s",
                   "Rest is tilt ≤ 10° and speed ≤ 1.0 COM heights per second."):
        assert phrase in FLAT, phrase


def test_the_intent_paragraphs_on_the_page_are_the_ones_the_judge_is_given() -> None:
    for behaviour in ("walk", "reach", "balance"):
        assert "**Intent.** " + CONTRACT["behaviours"][behaviour]["intent"] in FLAT, behaviour


def test_the_judge_is_blind_and_its_rubric_and_bar_are_frozen() -> None:
    judge = CONTRACT["judge"]
    start, end = "<!-- rubric:start -->\n", "<!-- rubric:end -->"
    block = README[README.index(start) + len(start):README.index(end)]
    assert hashlib.sha256(block.encode("utf-8")).hexdigest() == RUBRIC_SHA256 == judge["rubric_sha256"]
    assert [t for t in judge["traits"] if f"\n{t} " in block] == ["V1", "V2", "V3", "V4"] == judge["traits"]
    assert (judge["model"], judge["fallback"], judge["calls"]) == ("claude-opus-5-5", None, 3)
    assert judge["sees"] == ["the frozen rubric", "the behaviour's intent paragraph",
                             "the filmstrip frames of one seed"]
    assert judge["judged_seeds"] == [1101, 1105, 1110]
    assert set(judge["judged_seeds"]) <= set(SEEDS)
    assert judge["bar"] == {"total_min": 9, "total_max": 12, "trait_min": 2, "scope": "each judged seed"}
    assert judge["filmstrip"]["floor"] == "the dark prototype floor (ADR-444)"
    assert judge["filmstrip"]["overview"]["frames"] == judge["filmstrip"]["detail"]["frames"] == 12
    for phrase in ("a total of **at least 9 of 12**", "**no trait below 2**", "**1101, 1105 and 1110**",
                   "Three per seed.", "dark prototype floor (ADR-444)", "**Nothing else**"):
        assert phrase in FLAT, phrase


def test_the_known_negatives_fail_and_fail_for_the_stated_reasons() -> None:
    known = CONTRACT["known_negatives"]
    shuffle = known["walk_w2_2"]
    # The shuffle fails on stepping and on slip, not on staying up or heading.
    assert shuffle["failing"] == ["W3", "W5", "W7", "W9", "W10"]
    assert shuffle["failing_as_first_frozen"] == ["W3", "W5", "W7", "W9"]
    assert shuffle["passing"] == ["W1", "W2", "W4", "W6", "W8"]
    assert max(shuffle["step_share"]) < WALK["W5"][1]["min"][1]
    assert min(shuffle["slip_share"]) > WALK["W7"][1]["max"]
    assert shuffle["step_count_ratio"] > WALK["W9"][1]["max"]
    assert min(shuffle["lowest_height_mm"]) == -21.3
    seeds = known["walk_w2_2_ten_seeds"]
    assert seeds["seeds_failing"] == 10 and sorted(map(int, seeds["failing_by_seed"])) == SEEDS
    assert seeds["fail_on_every_seed"] == ["W5", "W7", "W9", "W10"]
    robin = known["balance_robin"]
    assert robin["failing_on_every_seed"] == ["B3", "B4"] and robin["not_measured"] == ["B1", "B5"]
    assert robin["max_drift_mm"][0] > robin["drift_limit_mm"] == 104.8
    assert robin["max_heading_deg"][0] > BALANCE["B4"][1]["max"]
    assert robin["max_tilt_deg"][1] < BALANCE["B2"][1]["max"]
    for phrase in ("| W5 share of path made in steps | 0.36 | 0.38 | 0.14 | 0.14 | ≥ 0.70 | **fail** |",
                   "| W7 stance slip share | 0.32 | 0.33 | 0.67 | 0.57 | ≤ 0.15 | **fail** |",
                   "| W10 lowest foot height, mm | −17.6 | −21.3 | −8.4 | −8.9 | ≥ −4.8 | **fail** |",
                   "829.4 mm to 850.8 mm", "130.9° to 131.6°", "it fails on **all ten**"):
        assert phrase in FLAT, phrase


def test_the_receipts_say_what_the_contract_says_and_carry_no_machine_path() -> None:
    known = CONTRACT["known_negatives"]
    shuffle = json.loads((OT11 / known["walk_w2_2"]["receipt"]).read_text(encoding="utf-8"))
    (trace,) = shuffle["traces"]
    assert trace["failing"] == known["walk_w2_2"]["failing"] and trace["pass"] is False
    assert trace["policy_sha256"] == known["walk_w2_2"]["policy_sha256"]
    seeds = json.loads((OT11 / known["walk_w2_2_ten_seeds"]["receipt"]).read_text(encoding="utf-8"))
    assert {str(t["seed"]): t["failing"] for t in seeds["traces"]} == known["walk_w2_2_ten_seeds"]["failing_by_seed"]
    robin = json.loads((OT11 / known["balance_robin"]["receipt"]).read_text(encoding="utf-8"))
    assert len(robin["traces"]) == 10
    assert all(t["failing"] == ["B3", "B4"] and t["pass"] is False for t in robin["traces"])
    for name in ("p1-w2-2.json", "p1-w2-2-seeds.json", "p1-robin.json"):
        text = (OT11 / "retained" / name).read_text(encoding="utf-8")
        assert "/home/" not in text and "/tmp/" not in text and "NaN" not in text, name


def test_the_one_change_since_the_freeze_is_recorded() -> None:
    (decision,) = CONTRACT["decisions"]
    assert decision["adr"] == "ADR-454" and "W10" in decision["change"]
    assert "### Decision: W10 was added after the freeze (ADR-454, 2026-09-30)" in README
    decisions = (REPO / "docs/DECISIONS.md").read_text(encoding="utf-8")
    assert "## ADR-454 — The ot11 evaluation contract" in decisions
