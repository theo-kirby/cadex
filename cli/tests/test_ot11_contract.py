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

import pytest

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


def test_the_known_negatives_fail_on_the_contracts_conditions_through_the_product() -> None:
    """``cadex evaluate`` on the two ``ot11-*`` copies (ADR-457): the
    contract's seeds, shoves and horizon, declared as a success spec that
    states no randomisation, as the contract lists none (ADR-458)."""

    bounds = {"walk": {"W1": ("completed", 1, None), "W2": ("max_tilt_deg", None, 30),
                       "W4-heading": ("max_heading_deg", None, 45),
                       "W5-steps": ("steps_min", 4, None), "W5-share": ("step_share_min", 0.70, None),
                       "W6": ("step_clearance_hip_heights_min", 0.08, None),
                       "W7": ("slip_share_max", None, 0.15),
                       "W8-low": ("duty_factor_min", 0.40, None),
                       "W8-high": ("duty_factor_max", None, 0.85),
                       "W9": ("step_count_ratio", None, 1.5),
                       "W10": ("foot_lowest_hip_heights_min", -0.05, None)},
              "balance": {"B1": ("completed", 1, None), "B2": ("max_tilt_deg", None, 30),
                          "B3": ("max_drift_com_heights", None, 2.0),
                          "B4": ("max_heading_deg", None, 20), "B5": ("recovery_s_max", None, 2.0)}}
    expected = {
        "p2-w2-2-evaluation.json": ("walk", "7a4e8c23",
                                    ["W5-steps", "W5-share", "W7", "W9", "W10"],
                                    {"horizon": 8, "tipped": 2}),
        "p2-robin-evaluation.json": ("balance", "ef71f370", ["B3", "B4", "B5"],
                                     {"fallen": 6, "horizon": 4}),
    }
    for name, (behaviour, policy, on_every_seed, endings) in expected.items():
        text = (OT11 / "retained" / name).read_text(encoding="utf-8")
        assert "/home/" not in text and "/tmp/" not in text and "NaN" not in text, name
        report = json.loads(text)
        assert report["schema"] == "cadex-evaluation-v1" and report["verdict"] == "fail"
        assert report["policy_sha256"].startswith(policy) and report["project"].startswith("ot11-")
        # The spec the copy declares is the contract's: its seeds, its
        # horizon, and its bounds on the metrics the binding names.
        assert report["spec"]["seeds"] == SEEDS == [row["seed"] for row in report["seeds"]]
        assert report["spec"]["episode"]["episode_seconds"] == CONTRACT["behaviours"][behaviour][
            "episode_seconds"]
        assert {row["id"]: (row["metric"], row["min"], row["max"])
                for row in report["spec"]["predicates"]} == bounds[behaviour]
        # Contract conditions: the mechanism as built, on every seed.
        assert report["spec"]["randomisation"] == []
        assert all(row["drawn"]["randomisation"] == [] for row in report["seeds"])
        summary = report["summary"]
        assert summary["passed"] == [] and summary["void"] == []
        assert summary["terminations"] == endings
        assert [row["id"] for row in summary["predicates"] if row["passed"] == 0] == on_every_seed
        assert name in README
    walk = json.loads((OT11 / "retained" / "p2-w2-2-evaluation.json").read_text(encoding="utf-8"))
    (shove,) = walk["spec"]["disturbance"]
    weight = walk["spec"]["scale"]["weight_n"]
    assert shove["newtons_low"] == pytest.approx(0.05 * weight)
    assert shove["newtons_high"] == pytest.approx(0.20 * weight)
    assert (shove["at_low_s"], shove["at_high_s"], shove["duration_s"]) == (3.0, 7.0, 0.15)
    # The seed the reward liked best barely stepped.
    best = max(walk["seeds"], key=lambda row: row["reward"]["total"])
    assert best["seed"] == 1109 and best["metrics"]["steps_min"] == 1
    assert best["metrics"]["step_share_min"] < 0.03
    robin = json.loads((OT11 / "retained" / "p2-robin-evaluation.json").read_text(encoding="utf-8"))
    assert [(d["at_low_s"], d["at_high_s"], d["duration_s"]) for d in robin["spec"]["disturbance"]] == [
        (2.0, 3.0, 0.10), (5.5, 6.5, 0.10)]
    for push in robin["spec"]["disturbance"]:
        assert push["newtons_low"] == pytest.approx(0.10 * robin["spec"]["scale"]["weight_n"])
        assert push["newtons_high"] == pytest.approx(0.25 * robin["spec"]["scale"]["weight_n"])
    # B1 and B5 are measured now: every seed was shoved twice.
    assert all(len(row["drawn"]["disturbance"]) == 2 for row in robin["seeds"])
    assert sum(1 for row in robin["seeds"] if row["metrics"]["completed"] == 1.0) == 4


def test_both_negatives_are_filmed_on_the_contracts_filmstrip() -> None:
    """ADR-459: each receipt's film is the contract's filmstrip -- twelve
    overview frames over the episode and twelve detail frames on the
    behaviour's window, of the three judged seeds -- and the committed
    sheets are the ones it names, inside the charter's cap."""

    judged = CONTRACT["judge"]["judged_seeds"]
    assert judged == [1101, 1105, 1110]
    strip = CONTRACT["judge"]["filmstrip"]
    assert strip["overview"]["frames"] == strip["detail"]["frames"] == 12
    for name, stem, step in (("p2-w2-2-evaluation.json", "w2-2", strip["detail"]["walk"]["spacing_s"]),
                             ("p2-robin-evaluation.json", "robin", strip["detail"]["balance"]["spacing_s"])):
        report = json.loads((OT11 / "retained" / name).read_text(encoding="utf-8"))
        film = report["film"]
        assert film["schema"] == "cadex-evaluation-film-v1" and film["state"] == "ready"
        assert "dark prototype mat (ADR-444)" in film["floor"] and film["materials"]["declared"]
        assert [row["seed"] for row in film["seeds"]] == judged
        rows = {row["seed"]: row for row in report["seeds"]}
        for row in film["seeds"]:
            measured = rows[row["seed"]]
            assert row["trace_sha256"] == measured["trace"]["sha256"]
            assert row["floor_source"] == "the model's collision plane" and row["floor_z_mm"] == 0.0
            end = measured["episode"]["duration_s"]
            overview, detail = row["overview"], row["detail"]
            assert overview["frames"] == 12 and overview["times_s"][0] == 0.0
            assert overview["times_s"][-1] == end
            assert detail["frames"] == 12 and detail["step_s"] == step
            gaps = [b - a for a, b in zip(detail["times_s"], detail["times_s"][1:])]
            assert gaps == pytest.approx([step] * 11, abs=0.021)
            assert detail["times_s"][-1] <= end
            # "Side-on, following the base" (ADR-460): the base the evaluation measured.
            assert detail["follows"] == report["rig"]["base"] is not None
            assert detail["view"].startswith("side-on") and detail["view"].endswith("the window follows the base")
            for sheet in (overview, detail):
                assert (sheet["width"], sheet["height"]) == (1036, 776)
                assert sheet["bytes"] <= 300 * 1024
        first = film["seeds"][0]
        assert first["video"]["fps"] == 10 and all(row["video"] is None for row in film["seeds"][1:])
        if stem == "w2-2":
            # The walk's window: every 0.04 s from 5.0 s.
            assert all(row["detail"]["start_source"] == "given"
                       and row["detail"]["start_s"] == strip["detail"]["walk"]["from_s"] == 5.0
                       for row in film["seeds"])
        else:
            # The balance's: from the first shove's onset, or to the fall when that came first.
            for row in film["seeds"]:
                shove = min(item["start_s"] for item in rows[row["seed"]]["drawn"]["disturbance"])
                assert row["detail"]["start_source"] == "the seed's first disturbance"
                assert row["detail"]["requested_start_s"] == shove
                assert row["detail"]["start_s"] <= shove
            assert film["seeds"][2]["detail"]["times_s"][-1] == rows[1110]["episode"]["duration_s"] == 4.26
        for key in ("overview", "detail"):
            path = OT11 / f"film-{stem}-seed-1101-{key}.png"
            data = path.read_bytes()
            assert hashlib.sha256(data).hexdigest() == first[key]["sha256"], path.name
            assert len(data) <= 300 * 1024 and path.name in README
    committed = {path.suffix for path in OT11.rglob("*") if path.is_file()}
    assert not committed & {".webm", ".mp4"} and not list(OT11.rglob("*-trace.json"))


def test_the_film_is_the_frozen_filmstrip() -> None:
    """The two places the product's film once departed from the frozen text
    are both closed in the product, not in the contract: the detail follows
    the base (ADR-460) and a frame shows its target as a marker (ADR-463)."""

    strip = CONTRACT["judge"]["filmstrip"]
    assert strip["detail"]["view"] == "side-on, following the base"
    assert strip["labels"].endswith("a reach frame shows the target as a marker")
    assert "A reach frame shows the target as a marker." in FLAT
    assert "**The detail is side-on, following the base** (ADR-460)." in README
    assert "**A frame of an episode with a target shows it as a marker** (ADR-463)." in README
    assert "target marker is not drawn" not in FLAT
    assert "follows the centre of the whole design, and side-on" not in FLAT
    # The product's half is pinned where the film is: cli/tests/test_film.py.
    from cadex_cli import film

    assert film.MARKER_RADIUS * film.FRAME == 9 and film.MARKER_COLOUR == (111, 240, 240)


def test_every_decision_since_the_freeze_is_recorded() -> None:
    added, limit = CONTRACT["decisions"]
    assert added["adr"] == "ADR-454" and "W10" in added["change"]
    assert "### Decision: W10 was added after the freeze (ADR-454, 2026-09-30)" in README
    # The second changes no frozen item, and says that nothing is re-evaluated.
    assert limit["adr"] == "ADR-463" and "known limit" in limit["change"]
    assert limit["re_evaluated"].startswith("nothing: no seed, condition, predicate, threshold, rubric line")
    assert "### What the judge is for, and what it does not see (ADR-463, 2026-09-30)" in README
    assert "**Nothing frozen changed, so nothing is re-evaluated.**" in README
    decisions = (REPO / "docs/DECISIONS.md").read_text(encoding="utf-8")
    assert "## ADR-454 — The ot11 evaluation contract" in decisions
    assert "## ADR-463 — " in decisions


def test_the_judges_blind_spot_on_stepping_and_slip_is_a_known_limit_and_the_predicates_are_the_authority() -> None:
    """The owner's ruling of 2026-09-30, held against the receipts it rests
    on: the judge scored a shuffle's manner 2 on every call, the predicates
    failed the same seeds on stepping and slip, and the predicates win."""

    judge, scope = CONTRACT["judge"], CONTRACT["judge_scope"]
    assert scope["adr"] == "ADR-463" and "changing nothing in it" in scope["rule"]
    jobs = scope["jobs"]
    assert jobs["predicates"].startswith("Where a predicate measures a property")
    assert "the predicate is authoritative for it" in jobs["predicates"]
    assert "falling, flailing or the wrong motion" in jobs["judge"]
    assert jobs["bar"].startswith("The judge's bar still applies to every judged seed")
    assert jobs["contradiction"] == ("Where the judge contradicts a measured predicate, the predicate wins, "
                                     "and the disagreement is recorded.")
    (limit,) = scope["known_limits"]
    assert (limit["adr"], limit["trait"], limit["authoritative"]) == ("ADR-463", "V2", ["W5", "W7"])
    assert "does not block P1" in limit["status"] and "no further judge probe" in limit["status"]
    measured = limit["measured_on"]
    assert measured["seeds"] == [1101, 1110] and set(measured["seeds"]) <= set(judge["judged_seeds"])
    # Every call on those seeds, as judged and with floor marks, scored manner 2...
    scores = []
    for name in measured["as_judged"] + measured["with_floor_marks"]:
        receipt = json.loads((OT11 / name).read_text(encoding="utf-8"))
        assert receipt["label"].startswith("w2-2") and receipt["seed"] in measured["seeds"], name
        assert receipt["medians"]["V2"] == 2 >= judge["bar"]["trait_min"], name
        scores += [call["scores"]["V2"]["score"] for call in receipt["raw"]]
    assert len(scores) == measured["calls"] == 18
    assert scores.count(2) == measured["calls_scoring_manner_2"] == 18
    # ...while the predicates the contract trusts failed the same seeds on stepping and slip.
    report = json.loads((OT11 / measured["evaluation"]).read_text(encoding="utf-8"))
    rows = {row["seed"]: row["metrics"] for row in report["seeds"]}
    shares = [(round(100 * rows[seed]["step_share_min"], 1), round(100 * rows[seed]["slip_share_max"]))
              for seed in measured["seeds"]]
    assert shares == [(8.5, 60), (3.6, 81)]
    for seed in measured["seeds"]:
        assert rows[seed]["step_share_min"] < WALK["W5"][1]["min"][1]
        assert rows[seed]["slip_share_max"] > WALK["W7"][1]["max"]
    for phrase in ("**Where a predicate measures a property, the predicate is authoritative for it.**",
                   "**The judge's job is what no predicate measures**",
                   "**The judge's bar still applies** to every judged seed of R1, R2 and R3.",
                   "**Where the judge contradicts a measured predicate, the predicate wins**",
                   "**Known limit: the judge's manner score (V2) is not a reading of stepping or of foot slip.**",
                   "**all eighteen calls scored manner 2**", "8.5 % and 3.6 %", "60 % and 81 %",
                   "It does not block P1, and it calls for no further judge probe."):
        assert phrase in FLAT, phrase
    # Recording it moved nothing the freeze holds.
    assert judge["rubric_sha256"] == RUBRIC_SHA256
    assert judge["bar"] == {"total_min": 9, "total_max": 12, "trait_min": 2, "scope": "each judged seed"}
    assert CONTRACT["confirmation"].startswith(
        "A behaviour is met only when its pre-registered confirmation evaluation passes every predicate "
        "on all ten seeds and every judged seed meets the judge's bar.")
